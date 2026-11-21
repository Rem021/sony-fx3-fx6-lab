#!/usr/bin/env python3
"""Unit tests for Phase 383 (Stage 88 — 88/88 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-78 HIL:
- 88A: `[Exposure Ctrl Type]` anti-Reset (`G86` closure), `[Auto/Manual Swt.
  Set.]`, `[Shutter Mode]` Angle (`5.6°..360.0°` & `2F..64F`, `BK4` Split,
  unaffected by `[Exposure step]`, forces Still/Movie separation), Still-only
  `[Anti-flicker Shoot.]`, dormant `Var. Shutter`/`HIGH_RES_SS` blocked vs FX6
  physical `IRIS/ISO-GAIN/SHUTTER/FULL AUTO` + 4-mode `Angle/Speed/ECS/Off`,
- 88B: `[Image Stabilization]` (`Active ~1.104x` forcing `[Distortion Comp.]
  = Auto`, ALL 4 hard lockouts, `G81` Ver. 2.00+ `200mm` note removal, dormant
  `Dynamic active`/`Intelligent Active`/`Super Active` blocked, `47`-step
  `[Focal Length]` `8..1000mm`, `Catalyst` gyro `RTMD` `Off`/`Active` only,
  NOT `Standard`, zero in `S&Q` & `119.88p/100p`) vs FX6 zero body IBIS + OSS
  3-mode `Active/Standard/Off` + Catalyst OSS `OFF`,
- 88C: `Playback -> [Photo Capture]` (`8.3M`/`2.1M`, DCI 4K hard block,
  anti-Reset Playback `[JPEG/HEIF Switch]`, HLG->HLG HEIF), 3-item `[View
  Mode]` (`G126` closure, dormant `MP4`/`AVCHD`/`XAVC_S` blocked), `[Rating]`
  `1..5` stars + FTP/Smartphone filter hooks, Tier-0 `Slot 1 EROFS=30` vs FX6
  zero Photo Capture + `Clip Flag` (`OK`/`NG`/`KEEP`),
- 88D: Double debunk `[USB Streaming]` (UVC/UAC) on `FX3`/`FX3A`/`A7S3`,
  4-mode `[USB Connection Mode]`, dormant `4K_12_5P/15P` (no `4K 30p/25p/24p`),
  `[Network Streaming]` (`RTMP`/`RTMPS`/`SRT Caller`-only, zero `SRT Listener`,
  BLE `Creators' App`, `59.94p/50p/29.97p/25p`, `<= 38 Mbps`, `[Movie Rec
  During Streaming]` 4K lock + `Slot 1 EROFS=30`, Airplane Mode zero-RF) vs
  FX6 zero native UVC/RTMP/SRT/QoS + `CBK-WA100`/`CBK-RPU7`/`PDT-FP1` (112
  four-mode forward-compatible tests).
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
import realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulator as p383  # noqa: E402


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..87 for Stage 88 isolation."""
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
]


class TestPhase383Stage88FlexExpShutterAngleActiveIbisCatalystPhotoCapSrt(unittest.TestCase):
    # =========================================================================
    # Tests 01..16: Schema, Stage 88 (88/88), Tier-0 Redlines & 4-Mode Donors
    # =========================================================================

    def test_01_schema_phase_and_stage88_constants(self) -> None:
        self.assertEqual(
            p383.SCHEMA_ID,
            "phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation_v1",
        )
        self.assertEqual(p383.PHASE_NUMBER, 383)
        self.assertEqual(p383.STAGE_INDEX, 88)
        self.assertEqual(p383.STAGE_TOTAL, 88)
        self.assertEqual(p383.MILESTONE_LABEL, "88/88")
        self.assertFalse(p383.READY_FOR_LIVE_CAMERA_ATTACH)
        self.assertFalse(p383.LIVE_ATTACH_AUTHORIZED)
        self.assertFalse(p383.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p383.SLOT1_WRITE_AUTHORIZED)
        self.assertEqual(p383.SLOT1_WRITES, 0)

    def test_02_orchestrator_returns_stage88_and_all_zero_redlines(self) -> None:
        rep = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["phase_number"], 383)
        self.assertEqual(rep["stage_index"], 88)
        self.assertEqual(rep["stage_total"], 88)
        self.assertEqual(rep["milestone"], "88/88")
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

    def test_03_donors_count_is_23_with_20_compact_and_3_window(self) -> None:
        self.assertEqual(len(p383.PHASE383_COMPACT_DONORS), 20)
        self.assertEqual(len(p383.PHASE383_WINDOW_DONORS), 3)
        info = p383.inspect_phase383_wave78_donors(force_clean_room=True)
        self.assertEqual(info["compact_donors_count"], 20)
        self.assertEqual(info["window_donors_count"], 3)
        self.assertEqual(info["total_donors_count"], 23)
        self.assertTrue(info["all_donors_verified"])
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)

    def test_04_donor_mode_normal_env_and_bounded_latency(self) -> None:
        t0 = time.monotonic()
        info = p383.inspect_phase383_wave78_donors()
        dt = time.monotonic() - t0
        self.assertLessEqual(dt, 2.0)
        self.assertTrue(info["all_donors_verified"])
        self.assertIn(info["source_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(info["total_donors_count"], 23)
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)

    def test_05_donor_mode_fx3_clean_room_test_env(self) -> None:
        info = p383.inspect_phase383_wave78_donors(env={"FX3_CLEAN_ROOM_TEST": "1"})
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(info["forced_clean_room"])
        self.assertTrue(info["all_donors_verified"])

    def test_06_donor_mode_fx3_fx6_force_clean_room_env(self) -> None:
        info = p383.inspect_phase383_wave78_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(info["forced_clean_room"])
        self.assertTrue(info["all_donors_verified"])

    def test_07_donor_mode_work_root_none_and_sentinel(self) -> None:
        info_none = p383.inspect_phase383_wave78_donors(work_root=None)
        self.assertEqual(info_none["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(info_none["work_root_available"])
        info_sent = p383.inspect_phase383_wave78_donors(
            env={"FX3_FX6_MAC_WORK_ROOT": p383._DONOR_DISABLED_SENTINEL}
        )
        self.assertEqual(info_sent["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(info_sent["work_root_available"])

    def test_08_donor_mode_nonexistent_work_root_graceful_clean_room(self) -> None:
        info = p383.inspect_phase383_wave78_donors(
            work_root="/nonexistent/phase383_stage88_missing_dir",
            force_clean_room=False,
        )
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(info["all_donors_verified"])

    def test_09_open_flags_include_o_rdonly_nofollow_nonblock(self) -> None:
        self.assertEqual(p383._DONOR_OPEN_FLAGS & os.O_RDONLY, os.O_RDONLY)
        if hasattr(os, "O_NOFOLLOW"):
            self.assertTrue(bool(p383._DONOR_OPEN_FLAGS & os.O_NOFOLLOW))
        if hasattr(os, "O_NONBLOCK"):
            self.assertTrue(bool(p383._DONOR_OPEN_FLAGS & os.O_NONBLOCK))

    def test_10_resolve_mac_work_root_and_is_forced_clean_room_helpers(self) -> None:
        self.assertIsNone(p383.resolve_mac_work_root(work_root=None))
        self.assertIsNone(p383.resolve_mac_work_root(work_root=""))
        self.assertIsNone(p383.resolve_mac_work_root(work_root=p383._DONOR_DISABLED_SENTINEL))
        self.assertEqual(
            p383.resolve_mac_work_root(work_root="/tmp/demo_stage88"), Path("/tmp/demo_stage88")
        )
        self.assertIsNone(p383.resolve_mac_work_root(env={"FX3_FX6_MAC_WORK_ROOT": ""}))
        self.assertTrue(p383.is_forced_clean_room({"FX3_CLEAN_ROOM_TEST": "1"}))
        self.assertTrue(p383.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": "1"}))
        self.assertFalse(p383.is_forced_clean_room({}))

    def test_11_bounded_window_rejects_oversized_read_request(self) -> None:
        with self.assertRaises(p383.Stage88Phase383Error):
            p383._read_bounded_window_o_rdonly(Path(__file__), 0, 4097)

    def test_12_compact_reader_rejects_file_over_1mib(self) -> None:
        fake_stat = unittest.mock.MagicMock(st_size=2 * 1024 * 1024)
        with unittest.mock.patch("os.open", return_value=99), \
             unittest.mock.patch("os.fstat", return_value=fake_stat), \
             unittest.mock.patch("os.close"):
            with self.assertRaises(p383.Stage88Phase383Error):
                p383._read_full_compact_o_rdonly(Path("/fake/huge.bin"))

    def test_13_lib_infra_srt_spec_forbids_srt_listener(self) -> None:
        spec = next(
            s for s in p383.PHASE383_COMPACT_DONORS
            if s.name == "fx3_lib_infra_srt_live_streaming"
        )
        self.assertIn(b"InfraSrtLiveStreaming", spec.required_tokens)
        self.assertIn(b"AES128", spec.required_tokens)
        self.assertIn(b"AES256", spec.required_tokens)
        self.assertIn(b"SRT_LISTENER", spec.absent_tokens)
        self.assertIn(b"srt_listen", spec.absent_tokens)

    def test_14_fx3_appfw_window_spec_forbids_uvc_4k_30p_25p_24p_and_srt_listener(self) -> None:
        wspec = next(w for w in p383.PHASE383_WINDOW_DONORS if w.name == "fx3_appfw")
        absent_needles = {needle for _, _, needle in wspec.absent_windows}
        self.assertIn(b"OUTPUT_FORMAT_4K_30P", absent_needles)
        self.assertIn(b"OUTPUT_FORMAT_4K_25P", absent_needles)
        self.assertIn(b"OUTPUT_FORMAT_4K_24P", absent_needles)
        self.assertIn(b"SRT_LISTENER", absent_needles)

    def test_15_fx6_appfw_window_spec_forbids_user_menu_srt_rtmp_qos(self) -> None:
        wspec = next(w for w in p383.PHASE383_WINDOW_DONORS if w.name == "fx6_appfw")
        absent_needles = {needle for _, _, needle in wspec.absent_windows}
        self.assertIn(b"BKID_APP_USER_MENU_SRT", absent_needles)
        self.assertIn(b"BKID_APP_USER_MENU_RTMP", absent_needles)
        self.assertIn(b"BKID_APP_USER_MENU_QOS", absent_needles)

    def test_16_recursive_strip_wall_clock_removes_elapsed_seconds_and_ms(self) -> None:
        sample = {
            "a": 1,
            "elapsed_seconds": 0.123,
            "nested": {
                "elapsed_ms": 12.3,
                "items": [{"elapsed_seconds": 9.9, "keep": True}],
            },
        }
        cleaned = p383._strip_wall_clock(sample)
        self.assertEqual(cleaned, {"a": 1, "nested": {"items": [{"keep": True}]}})

    # =========================================================================
    # Tests 17..39: Sub-Model 88A — Exposure Ctrl Type (G86), Shutter Mode Angle
    # =========================================================================

    def test_17_88a_g86_exposure_ctrl_type_resists_camera_settings_reset(self) -> None:
        res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
            shoot_mode="Movie",
            exposure_ctrl_type="P/A/S/M Mode",
            av_mode="Auto",
            tv_mode="Auto",
            iso_mode="Auto",
            auto_slow_shutter="Off",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.exposure_ctrl_type, "P/A/S/M Mode")
        self.assertTrue(res.exposure_ctrl_type_survived_cam_reset)
        self.assertFalse(res.exposure_ctrl_type_reset_on_init)
        self.assertTrue(res.g86_erratum_reconciled)
        self.assertEqual(res.av_mode, "Manual")
        self.assertEqual(res.tv_mode, "Manual")
        self.assertEqual(res.iso_mode, "Manual")
        self.assertEqual(res.auto_slow_shutter, "On")

    def test_18_88a_g86_exposure_ctrl_type_resets_only_on_initialize(self) -> None:
        res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
            shoot_mode="S&Q",
            exposure_ctrl_type="P/A/S/M Mode",
            av_mode="Auto",
            tv_mode="Auto",
            iso_mode="Auto",
            auto_slow_shutter="Off",
            initialize_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.exposure_ctrl_type, "Flexible Exp. Mode")
        self.assertTrue(res.exposure_ctrl_type_reset_on_init)
        self.assertEqual(res.av_mode, "Manual")
        self.assertEqual(res.tv_mode, "Manual")
        self.assertEqual(res.iso_mode, "Manual")
        self.assertEqual(res.auto_slow_shutter, "On")

    def test_19_88a_exposure_ctrl_type_blocked_in_still_mode(self) -> None:
        res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
            shoot_mode="Still",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)

    def test_20_88a_auto_manual_swt_requires_flexible_exp_mode(self) -> None:
        ok = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
            exposure_ctrl_type="Flexible Exp. Mode",
            av_mode="Auto",
            auto_manual_switch_requested=True,
        )
        self.assertTrue(ok.allowed)

        blk = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
            exposure_ctrl_type="P/A/S/M Mode",
            auto_manual_switch_requested=True,
        )
        self.assertFalse(blk.allowed)
        self.assertEqual(blk.errno, p383.EOPNOTSUPP_ERRNO)

    def test_21_88a_invalid_exposure_ctrl_or_axis_state_einval(self) -> None:
        bad1 = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
            exposure_ctrl_type="Cinema Auto",
        )
        self.assertEqual(bad1.errno, p383.EINVAL_ERRNO)

        bad2 = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
            iso_mode="Semi-Auto",
        )
        self.assertEqual(bad2.errno, p383.EINVAL_ERRNO)

    def test_22_88a_shutter_mode_angle_all_19_standard_steps_allowed(self) -> None:
        self.assertEqual(len(p383.FX3_SHUTTER_ANGLE_STANDARD_STEPS), 19)
        for ang in p383.FX3_SHUTTER_ANGLE_STANDARD_STEPS:
            res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
                operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
                shoot_mode="Movie",
                shutter_mode="Angle",
                shutter_angle=ang,
            )
            self.assertTrue(res.allowed, f"Failed standard angle {ang}")
            self.assertEqual(res.shutter_angle, ang)

    def test_23_88a_shutter_mode_angle_all_10_multiframe_steps_at_2398p(self) -> None:
        self.assertEqual(len(p383.FX3_SHUTTER_ANGLE_MULTIFRAME_STEPS), 10)
        for mf in p383.FX3_SHUTTER_ANGLE_MULTIFRAME_STEPS:
            res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
                operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
                shoot_mode="Movie",
                shutter_mode="Angle",
                shutter_angle=mf,
                rec_frame_rate="23.98p",
            )
            self.assertTrue(res.allowed, f"Failed multiframe angle {mf}")

    def test_24_88a_shutter_angle_multiframe_2f_64f_clamped_at_high_fps(self) -> None:
        for mf in ("2F", "8F", "64F"):
            r_mv = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
                operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
                shoot_mode="Movie",
                shutter_mode="Angle",
                shutter_angle=mf,
                rec_frame_rate="119.88p",
            )
            self.assertFalse(r_mv.allowed)
            self.assertEqual(r_mv.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertTrue(r_mv.multiframe_angle_clamped)

            r_sq = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
                operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
                shoot_mode="S&Q",
                shutter_mode="Angle",
                shutter_angle=mf,
                sq_frame_rate_fps=120,
            )
            self.assertFalse(r_sq.allowed)
            self.assertEqual(r_sq.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertTrue(r_sq.multiframe_angle_clamped)

    def test_25_88a_shutter_mode_angle_strictly_movie_and_sq_only(self) -> None:
        res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
            shoot_mode="Still",
            shutter_mode="Angle",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)

    def test_26_88a_shutter_mode_can_be_reset_to_speed(self) -> None:
        res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
            shoot_mode="Movie",
            shutter_mode="Angle",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.shutter_mode, "Speed")
        self.assertTrue(res.shutter_mode_can_be_reset)

    def test_27_88a_bk4_slot_split_0x01120024_vs_0x01120028(self) -> None:
        r_spd = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
            shutter_mode="Speed",
            shutter_speed="1/100",
            shutter_angle="180.0",
        )
        r_ang = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
            shutter_mode="Angle",
            shutter_speed="1/100",
            shutter_angle="172.8",
        )
        self.assertEqual(r_spd.bk4_speed_slot_hex, "0x01120024")
        self.assertEqual(r_ang.bk4_angle_slot_hex, "0x01120028")
        self.assertTrue(r_ang.bk4_slots_disjoint)
        self.assertEqual(r_ang.shutter_speed, "1/100")

    def test_28_88a_exposure_step_does_not_affect_shutter_angle(self) -> None:
        for step in ("0.3 EV", "0.5 EV"):
            res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
                operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
                shutter_mode="Angle",
                shutter_angle="172.8",
                exposure_step=step,
            )
            self.assertTrue(res.allowed)
            self.assertFalse(res.exposure_step_affects_angle)

    def test_29_88a_shutter_angle_forces_still_movie_shutter_separation(self) -> None:
        res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
            shutter_mode="Angle",
            shutter_angle="180.0",
            diff_set_shutter_checked=False,
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.forces_still_movie_shutter_separation)

    def test_30_88a_flexexp_tv_auto_blocks_manual_angle_adjust(self) -> None:
        res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
            exposure_ctrl_type="Flexible Exp. Mode",
            tv_mode="Auto",
            shutter_mode="Angle",
            manual_angle_adjust_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EBUSY_ERRNO)

    def test_31_88a_invalid_shutter_mode_angle_or_exp_step_einval(self) -> None:
        r1 = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
            shutter_mode="ECS",
        )
        self.assertEqual(r1.errno, p383.EINVAL_ERRNO)
        r2 = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
            shutter_mode="Angle",
            shutter_angle="185.0",
        )
        self.assertEqual(r2.errno, p383.EINVAL_ERRNO)
        r3 = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
            exposure_step="1.0 EV",
        )
        self.assertEqual(r3.errno, p383.EINVAL_ERRNO)

    def test_32_88a_antiflicker_still_only_and_resettable(self) -> None:
        ok = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_antiflicker_still_only_and_dormant_var_shutter_block",
            shoot_mode="Still",
            anti_flicker_shoot="On",
        )
        self.assertTrue(ok.allowed)

        rst = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_antiflicker_still_only_and_dormant_var_shutter_block",
            shoot_mode="Still",
            anti_flicker_shoot="On",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(rst.allowed)
        self.assertEqual(rst.anti_flicker_shoot, "Off")

        for mode in ("Movie", "S&Q"):
            blk = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
                operation="fx3_antiflicker_still_only_and_dormant_var_shutter_block",
                shoot_mode=mode,
                anti_flicker_shoot="On",
            )
            self.assertFalse(blk.allowed)
            self.assertEqual(blk.errno, p383.EOPNOTSUPP_ERRNO)

    def test_33_88a_dormant_var_shutter_blocked_all_modes(self) -> None:
        for item in p383.FX3_DORMANT_VAR_SHUTTER_ITEMS:
            for mode in ("Still", "Movie", "S&Q"):
                res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
                    operation="fx3_antiflicker_still_only_and_dormant_var_shutter_block",
                    shoot_mode=mode,
                    var_shutter_item=item,
                )
                self.assertFalse(res.allowed)
                self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
                self.assertTrue(res.dormant_var_shutter_blocked)

    def test_34_88a_fx6_physical_exposure_keys_and_4mode_shutter_modes(self) -> None:
        for mode in ("Angle", "Speed", "ECS", "Off"):
            res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
                operation="fx6_physical_exposure_keys_and_4mode_shutter_ecs",
                body_model=p383.BODY_MODEL_FX6,
                fx6_shutter_mode=mode,
                fx6_ecs_frequency_hz=120.0,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(
                res.fx6_physical_exposure_keys,
                ("IRIS", "ISO/GAIN", "SHUTTER", "FULL AUTO"),
            )

    def test_35_88a_fx6_ecs_frequency_range_validation(self) -> None:
        low = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx6_physical_exposure_keys_and_4mode_shutter_ecs",
            body_model=p383.BODY_MODEL_FX6,
            fx6_shutter_mode="ECS",
            fx6_ecs_frequency_hz=10.0,
        )
        self.assertEqual(low.errno, p383.EINVAL_ERRNO)
        high = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx6_physical_exposure_keys_and_4mode_shutter_ecs",
            body_model=p383.BODY_MODEL_FX6,
            fx6_shutter_mode="ECS",
            fx6_ecs_frequency_hz=9000.0,
        )
        self.assertEqual(high.errno, p383.EINVAL_ERRNO)

    def test_36_88a_fx6_invalid_shutter_mode_einval(self) -> None:
        res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx6_physical_exposure_keys_and_4mode_shutter_ecs",
            body_model=p383.BODY_MODEL_FX6,
            fx6_shutter_mode="VarShutter",
        )
        self.assertEqual(res.errno, p383.EINVAL_ERRNO)

    def test_37_88a_invalid_operation_body_or_mode_raises(self) -> None:
        with self.assertRaises(p383.Stage88Phase383Error):
            p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(operation="bad")
        with self.assertRaises(p383.Stage88Phase383Error):
            p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
                operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
                body_model="FX9",
            )
        with self.assertRaises(p383.Stage88Phase383Error):
            p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
                operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
                shoot_mode="Timelapse",
            )

    def test_38_88a_to_dict_serializes_cleanly(self) -> None:
        res = p383.simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
            operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
            shutter_mode="Angle",
        )
        s = json.dumps(res.to_dict())
        self.assertIn("0x01120028", s)

    def test_39_88a_orchestrator_metrics_alignment(self) -> None:
        rep = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            work_root=None
        )
        s = rep["submodel_88a_flexexp_shutterangle_varshutter_fx6_ecs"]
        self.assertTrue(s["passed"])
        self.assertTrue(s["fx3_g86_exposure_ctrl_type_reset_erratum_reconciled"])
        self.assertEqual(s["fx3_shutter_angle_standard_steps_count"], 19)
        self.assertEqual(s["fx3_shutter_angle_multiframe_steps_count"], 10)
        self.assertEqual(s["fx3_dormant_var_shutter_exposed_events"], 0)
        self.assertEqual(s["fx6_shutter_modes_count"], 4)

    # =========================================================================
    # Tests 40..62: Sub-Model 88B — SteadyShot 4-Lock, 47-Focal & Catalyst Gyro
    # =========================================================================

    def test_40_88b_active_steadyshot_1_104x_forces_distortion_comp_auto(self) -> None:
        res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_4locks_and_dormant_block",
            steadyshot_mode="Active",
            rec_frame_rate="23.98p",
        )
        self.assertTrue(res.allowed)
        self.assertAlmostEqual(res.active_crop_factor, 1.104, places=3)
        self.assertEqual(res.distortion_comp_forced, "Auto")

    def test_41_88b_active_lockout_1_119_88p_and_100p(self) -> None:
        for fps in ("119.88p", "100p"):
            res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_active_4locks_and_dormant_block",
                steadyshot_mode="Active",
                rec_frame_rate=fps,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertIn("REC_FRAME_RATE_119_88P_100P", res.active_lockouts_triggered)

    def test_42_88b_active_lockout_2_sq_ge_100fps(self) -> None:
        for sq_fps in (100, 120, 200, 240):
            res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_active_4locks_and_dormant_block",
                shoot_mode="S&Q",
                steadyshot_mode="Active",
                sq_frame_rate_fps=sq_fps,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertIn("SQ_FRAME_RATE_GE_100FPS", res.active_lockouts_triggered)

        ok_60 = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_4locks_and_dormant_block",
            shoot_mode="S&Q",
            steadyshot_mode="Active",
            sq_frame_rate_fps=60,
        )
        self.assertTrue(ok_60.allowed)

    def test_43_88b_active_lockout_3_hdmi_raw_output_on(self) -> None:
        res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_4locks_and_dormant_block",
            steadyshot_mode="Active",
            hdmi_raw_output_on=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
        self.assertIn("HDMI_RAW_OUTPUT_ON", res.active_lockouts_triggered)

    def test_44_88b_active_lockout_4_desqueeze_display_not_off(self) -> None:
        for ratio in ("1.3x", "1.5x", "1.6x", "1.8x", "2.0x"):
            res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_active_4locks_and_dormant_block",
                steadyshot_mode="Active",
                desqueeze_display=ratio,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertIn("DESQUEEZE_DISPLAY_NOT_OFF", res.active_lockouts_triggered)

    def test_45_88b_active_all_4_lockouts_reported_together(self) -> None:
        res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_4locks_and_dormant_block",
            shoot_mode="S&Q",
            steadyshot_mode="Active",
            rec_frame_rate="119.88p",
            sq_frame_rate_fps=120,
            hdmi_raw_output_on=True,
            desqueeze_display="1.3x",
        )
        self.assertEqual(len(res.active_lockouts_triggered), 4)
        self.assertEqual(set(res.active_lockouts_triggered), set(p383.FX3_ACTIVE_4_LOCKOUT_IDS))

    def test_46_88b_g81_ver2_plus_removed_200mm_note_allows_active_at_200mm_and_400mm(self) -> None:
        for fl in (200, 400):
            res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_active_4locks_and_dormant_block",
                steadyshot_mode="Active",
                lens_focal_length_mm=fl,
            )
            self.assertTrue(res.allowed)
            self.assertTrue(res.g81_200mm_legacy_note_removed)

    def test_47_88b_dormant_dynamic_intelligent_super_active_blocked(self) -> None:
        for mode in p383.FX3_DORMANT_STEADYSHOT_MODES:
            res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_active_4locks_and_dormant_block",
                steadyshot_mode=mode,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.dormant_steadyshot_blocked)

    def test_48_88b_all_4_is_settings_can_be_reset_by_cam_reset(self) -> None:
        res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_4locks_and_dormant_block",
            steadyshot_mode="Active",
            steadyshot_adjust="Manual",
            focal_length_mm=50,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.steadyshot_mode, "Standard")
        self.assertEqual(res.steadyshot_adjust, "Auto")
        self.assertEqual(res.focal_length_mm, 8)
        self.assertTrue(res.is_4settings_can_be_reset)

    def test_49_88b_lens_oss_physical_switch_off_forces_body_steadyshot_off(self) -> None:
        res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_4locks_and_dormant_block",
            steadyshot_mode="Standard",
            lens_oss_physical_switch_off=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EBUSY_ERRNO)
        self.assertEqual(res.steadyshot_mode, "Off")

    def test_50_88b_exact_47_step_focal_length_table_8mm_to_1000mm(self) -> None:
        self.assertEqual(len(p383.FX3_FOCAL_LENGTH_47_STEPS_MM), 47)
        self.assertEqual(p383.FX3_FOCAL_LENGTH_47_STEPS_MM[0], 8)
        self.assertEqual(p383.FX3_FOCAL_LENGTH_47_STEPS_MM[-1], 1000)
        for fl in p383.FX3_FOCAL_LENGTH_47_STEPS_MM:
            res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_adjust_and_47step_focal_length",
                steadyshot_adjust="Manual",
                focal_length_mm=fl,
            )
            self.assertTrue(res.allowed, f"Focal length {fl}mm failed")

    def test_51_88b_invalid_focal_length_step_rejected_einval(self) -> None:
        for bad_fl in (7, 22, 23, 26, 33, 501, 1200):
            res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_adjust_and_47step_focal_length",
                steadyshot_adjust="Manual",
                focal_length_mm=bad_fl,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EINVAL_ERRNO)

    def test_52_88b_steadyshot_adjust_auto_locks_manual_focal_edit(self) -> None:
        res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_adjust_and_47step_focal_length",
            steadyshot_adjust="Auto",
            manual_focal_edit_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EBUSY_ERRNO)

    def test_53_88b_catalyst_gyro_usable_only_with_off_or_active(self) -> None:
        for ss in ("Off", "Active"):
            res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx3_catalyst_gyro_rtmd_eligibility",
                steadyshot_mode=ss,
                electronic_contact_lens=True,
            )
            self.assertTrue(res.allowed)
            self.assertTrue(res.catalyst_gyro_usable)

        std = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_catalyst_gyro_rtmd_eligibility",
            steadyshot_mode="Standard",
            electronic_contact_lens=True,
        )
        self.assertFalse(std.allowed)
        self.assertEqual(std.errno, p383.EOPNOTSUPP_ERRNO)
        self.assertFalse(std.catalyst_gyro_usable)

    def test_54_88b_catalyst_gyro_zero_usable_in_sq_and_119_88p_100p(self) -> None:
        sq = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_catalyst_gyro_rtmd_eligibility",
            shoot_mode="S&Q",
            steadyshot_mode="Off",
        )
        self.assertFalse(sq.allowed)
        self.assertFalse(sq.catalyst_gyro_usable)

        for fps in ("119.88p", "100p"):
            hi = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx3_catalyst_gyro_rtmd_eligibility",
                rec_frame_rate=fps,
                steadyshot_mode="Off",
            )
            self.assertFalse(hi.allowed)
            self.assertFalse(hi.catalyst_gyro_usable)

    def test_55_88b_catalyst_gyro_requires_electronic_lens_and_internal_xavc(self) -> None:
        no_elec = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_catalyst_gyro_rtmd_eligibility",
            steadyshot_mode="Off",
            electronic_contact_lens=False,
        )
        self.assertEqual(no_elec.errno, p383.EOPNOTSUPP_ERRNO)

        hdmi_ext = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_catalyst_gyro_rtmd_eligibility",
            steadyshot_mode="Off",
            external_hdmi_recording=True,
        )
        self.assertEqual(hdmi_ext.errno, p383.EOPNOTSUPP_ERRNO)

    def test_56_88b_fx6_zero_body_ibis_and_oss_3mode_active_standard_off(self) -> None:
        for mode in ("Active", "Standard", "Off"):
            res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx6_zero_ibis_oss_3mode_and_catalyst",
                body_model=p383.BODY_MODEL_FX6,
                fx6_oss_lens_attached=True,
                fx6_lens_oss_switch_on=True,
                fx6_oss_mode=mode,
            )
            self.assertTrue(res.allowed)
            self.assertFalse(res.fx6_has_body_ibis)
            self.assertEqual(res.fx6_ibis_message, "The SteadyShot mechanism is fixed.")

    def test_57_88b_fx6_blocks_dormant_dynamic_active_and_manual_ibis_focal(self) -> None:
        dyn = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_3mode_and_catalyst",
            body_model=p383.BODY_MODEL_FX6,
            fx6_oss_mode="Dynamic Active",
        )
        self.assertEqual(dyn.errno, p383.EOPNOTSUPP_ERRNO)
        self.assertTrue(dyn.dormant_steadyshot_blocked)

        fl = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_3mode_and_catalyst",
            body_model=p383.BODY_MODEL_FX6,
            fx6_manual_ibis_focal_requested=True,
        )
        self.assertEqual(fl.errno, p383.EOPNOTSUPP_ERRNO)

    def test_58_88b_fx6_oss_active_requires_oss_lens_and_switch_on(self) -> None:
        no_oss = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_3mode_and_catalyst",
            body_model=p383.BODY_MODEL_FX6,
            fx6_oss_lens_attached=False,
            fx6_oss_mode="Active",
        )
        self.assertEqual(no_oss.errno, p383.EOPNOTSUPP_ERRNO)

    def test_59_88b_fx6_catalyst_requires_oss_off_and_le_60p_non_sq(self) -> None:
        ok = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_3mode_and_catalyst",
            body_model=p383.BODY_MODEL_FX6,
            fx6_lens_oss_switch_on=False,
            fx6_oss_mode="Off",
            rec_frame_rate="59.94p",
            fx6_catalyst_requested=True,
        )
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.catalyst_gyro_usable)

        oss_on = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_3mode_and_catalyst",
            body_model=p383.BODY_MODEL_FX6,
            fx6_lens_oss_switch_on=True,
            fx6_oss_mode="Off",
            fx6_catalyst_requested=True,
        )
        self.assertEqual(oss_on.errno, p383.EOPNOTSUPP_ERRNO)

        hi_fps = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_3mode_and_catalyst",
            body_model=p383.BODY_MODEL_FX6,
            fx6_lens_oss_switch_on=False,
            fx6_oss_mode="Off",
            rec_frame_rate="119.88p",
            fx6_catalyst_requested=True,
        )
        self.assertEqual(hi_fps.errno, p383.EOPNOTSUPP_ERRNO)

    def test_60_88b_invalid_operation_or_mode_raises(self) -> None:
        with self.assertRaises(p383.Stage88Phase383Error):
            p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(operation="bad")
        with self.assertRaises(p383.Stage88Phase383Error):
            p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_active_4locks_and_dormant_block",
                body_model="FX9",
            )

    def test_61_88b_steadyshot_adjust_reset_to_auto_8mm(self) -> None:
        res = p383.simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_adjust_and_47step_focal_length",
            steadyshot_adjust="Manual",
            focal_length_mm=300,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.steadyshot_adjust, "Auto")
        self.assertEqual(res.focal_length_mm, 8)

    def test_62_88b_orchestrator_metrics_alignment(self) -> None:
        rep = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            work_root=None
        )
        s = rep["submodel_88b_steadyshot_4locks_47focal_catalyst_fx6_oss"]
        self.assertTrue(s["passed"])
        self.assertEqual(s["fx3_active_lockouts_count"], 4)
        self.assertAlmostEqual(s["fx3_active_crop_factor"], 1.104, places=3)
        self.assertEqual(s["fx3_focal_length_steps_count"], 47)
        self.assertEqual(s["fx3_dormant_steadyshot_exposed_events"], 0)
        self.assertFalse(s["fx6_has_body_ibis"])
        self.assertEqual(s["fx6_oss_modes_count"], 3)

    # =========================================================================
    # Tests 63..84: Sub-Model 88C — Photo Capture, View Mode (G126) & Rating
    # =========================================================================

    def test_63_88c_photo_capture_4k_uhd_8_3m_and_hd_2_1m(self) -> None:
        for fmt in p383.FX3_PHOTO_CAPTURE_4K_UHD_FORMATS:
            r4 = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
                operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
                source_file_format=fmt,
                target_slot="Slot 2",
                simulated_sandbox=True,
            )
            self.assertTrue(r4.allowed)
            self.assertEqual(r4.photo_capture_resolution, "3840x2160")
            self.assertAlmostEqual(r4.photo_capture_mp, 8.3, places=1)
            self.assertEqual(r4.slot1_writes, 0)

        for fmt in p383.FX3_PHOTO_CAPTURE_HD_FORMATS:
            r2 = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
                operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
                source_file_format=fmt,
                target_slot="Slot 2",
                simulated_sandbox=True,
            )
            self.assertTrue(r2.allowed)
            self.assertEqual(r2.photo_capture_resolution, "1920x1080")
            self.assertAlmostEqual(r2.photo_capture_mp, 2.1, places=1)

    def test_64_88c_photo_capture_hard_blocks_xavc_si_dci_4k(self) -> None:
        res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
            source_file_format="XAVC S-I DCI 4K",
            target_slot="Slot 2",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.dci4k_photo_capture_blocked)

    def test_65_88c_photo_capture_hlg_to_hlg_heif_vs_sdr_jpeg(self) -> None:
        for heif in ("HEIF(4:2:0)", "HEIF(4:2:2)"):
            r = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
                operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
                source_file_format="XAVC HS 4K",
                source_is_hlg=True,
                playback_jpeg_heif_switch=heif,
                target_slot="Slot 2",
            )
            self.assertTrue(r.allowed)
            self.assertTrue(r.output_is_hlg_heif)

        rj = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
            source_file_format="XAVC HS 4K",
            source_is_hlg=True,
            playback_jpeg_heif_switch="JPEG",
            target_slot="Slot 2",
        )
        self.assertTrue(rj.allowed)
        self.assertFalse(rj.output_is_hlg_heif)

    def test_66_88c_playback_jpeg_heif_resists_cam_reset_unlike_shooting_side(self) -> None:
        rst = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
            playback_jpeg_heif_switch="HEIF(4:2:2)",
            shooting_jpeg_heif_switch="HEIF(4:2:0)",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(rst.allowed)
        self.assertEqual(rst.playback_jpeg_heif_switch, "HEIF(4:2:2)")
        self.assertTrue(rst.playback_jpeg_heif_survived_cam_reset)
        self.assertEqual(rst.shooting_jpeg_heif_switch, "JPEG")
        self.assertTrue(rst.shooting_jpeg_heif_reset_on_cam_reset)

        init = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
            playback_jpeg_heif_switch="HEIF(4:2:2)",
            shooting_jpeg_heif_switch="HEIF(4:2:0)",
            initialize_triggered=True,
        )
        self.assertEqual(init.playback_jpeg_heif_switch, "JPEG")
        self.assertEqual(init.shooting_jpeg_heif_switch, "JPEG")

    def test_67_88c_photo_capture_slot1_hard_blocked_erofs_30(self) -> None:
        res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
            source_file_format="XAVC S 4K",
            target_slot="Slot 1",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EROFS_ERRNO)
        self.assertTrue(res.slot1_erofs_blocked)
        self.assertEqual(res.slot1_writes, 0)
        self.assertEqual(res.slot1_sector_writes, 0)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_68_88c_photo_capture_non_sandbox_slot2_blocked_erofs(self) -> None:
        res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
            source_file_format="XAVC S 4K",
            target_slot="Slot 2",
            simulated_sandbox=False,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EROFS_ERRNO)

    def test_69_88c_g126_view_mode_exact_3_exposed_states(self) -> None:
        self.assertEqual(len(p383.FX3_VIEW_MODE_EXPOSED_3_STATES), 3)
        for vm in ("Date View", "Folder View(Still)", "Movie View"):
            res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
                operation="fx3_view_mode_3item_g126_and_dormant_block",
                view_mode=vm,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.view_mode, vm)
            self.assertEqual(res.view_mode_exposed_count, 3)
            self.assertTrue(res.g126_erratum_reconciled)

    def test_70_88c_g126_view_mode_dormant_mp4_avchd_xavcs_blocked(self) -> None:
        for bad_vm in p383.FX3_DORMANT_VIEW_MODES:
            res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
                operation="fx3_view_mode_3item_g126_and_dormant_block",
                view_mode=bad_vm,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.dormant_view_mode_blocked)

    def test_71_88c_g126_view_mode_resists_cam_reset_and_resets_on_init(self) -> None:
        rst = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_view_mode_3item_g126_and_dormant_block",
            view_mode="Movie View",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(rst.allowed)
        self.assertEqual(rst.view_mode, "Movie View")
        self.assertTrue(rst.view_mode_survived_cam_reset)

        init = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_view_mode_3item_g126_and_dormant_block",
            view_mode="Movie View",
            initialize_triggered=True,
        )
        self.assertTrue(init.allowed)
        self.assertEqual(init.view_mode, "Date View")

    def test_72_88c_rating_1_to_5_stars_and_ftp_smartphone_filter_hooks(self) -> None:
        for star in (1, 2, 3, 4, 5):
            res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
                operation="fx3_rating_1to5_ftp_filter_and_slot1_erofs",
                rating_stars=star,
                ftp_filter_stars=(5,),
                smartphone_filter_stars=(4, 5),
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.ftp_rating_filter_matched, star == 5)
            self.assertEqual(res.smartphone_rating_filter_matched, star in (4, 5))

    def test_73_88c_rating_set_custom_key_resists_cam_reset(self) -> None:
        rst = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_rating_1to5_ftp_filter_and_slot1_erofs",
            rating_stars=5,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(rst.allowed)
        self.assertTrue(rst.rating_set_survived_cam_reset)

        init = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_rating_1to5_ftp_filter_and_slot1_erofs",
            rating_stars=5,
            initialize_triggered=True,
        )
        self.assertFalse(init.rating_set_survived_cam_reset)

    def test_74_88c_rating_slot1_xmp_avf_mutation_hard_blocked_erofs_30(self) -> None:
        res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_rating_1to5_ftp_filter_and_slot1_erofs",
            rating_stars=4,
            rating_write_requested=True,
            target_slot="Slot 1",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EROFS_ERRNO)
        self.assertTrue(res.slot1_erofs_blocked)
        self.assertEqual(res.slot1_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_75_88c_rating_sandbox_slot2_write_allowed_and_non_sandbox_blocked(self) -> None:
        ok = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_rating_1to5_ftp_filter_and_slot1_erofs",
            rating_stars=5,
            rating_write_requested=True,
            target_slot="Slot 2",
            simulated_sandbox=True,
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.slot1_writes, 0)

        blk = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_rating_1to5_ftp_filter_and_slot1_erofs",
            rating_stars=5,
            rating_write_requested=True,
            target_slot="Slot 2",
            simulated_sandbox=False,
        )
        self.assertEqual(blk.errno, p383.EROFS_ERRNO)

    def test_76_88c_rating_out_of_range_einval(self) -> None:
        for bad in (-1, 6):
            res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
                operation="fx3_rating_1to5_ftp_filter_and_slot1_erofs",
                rating_stars=bad,
            )
            self.assertEqual(res.errno, p383.EINVAL_ERRNO)

    def test_77_88c_fx6_zero_in_camera_photo_capture_blocked(self) -> None:
        res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx6_zero_photo_capture_and_clip_flag_ok_ng_keep",
            body_model=p383.BODY_MODEL_FX6,
            fx6_photo_capture_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.fx6_has_in_camera_photo_capture)

    def test_78_88c_fx6_clip_flag_ok_ng_keep_and_delete(self) -> None:
        for flag in ("OK", "NG", "KEEP"):
            res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
                operation="fx6_zero_photo_capture_and_clip_flag_ok_ng_keep",
                body_model=p383.BODY_MODEL_FX6,
                fx6_clip_flag=flag,
                target_slot="Slot 2",
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.fx6_clip_flag, flag)

        d = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx6_zero_photo_capture_and_clip_flag_ok_ng_keep",
            body_model=p383.BODY_MODEL_FX6,
            fx6_delete_clip_flag_requested=True,
            target_slot="Slot 2",
        )
        self.assertTrue(d.allowed)
        self.assertEqual(d.fx6_clip_flag, "")

    def test_79_88c_fx6_clip_flag_invalid_and_slot1_erofs(self) -> None:
        bad = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx6_zero_photo_capture_and_clip_flag_ok_ng_keep",
            body_model=p383.BODY_MODEL_FX6,
            fx6_clip_flag="5STAR",
            target_slot="Slot 2",
        )
        self.assertEqual(bad.errno, p383.EINVAL_ERRNO)

        s1 = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx6_zero_photo_capture_and_clip_flag_ok_ng_keep",
            body_model=p383.BODY_MODEL_FX6,
            fx6_clip_flag="OK",
            target_slot="Slot 1",
        )
        self.assertEqual(s1.errno, p383.EROFS_ERRNO)

    def test_80_88c_invalid_jpeg_heif_or_view_mode_einval(self) -> None:
        r1 = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
            playback_jpeg_heif_switch="RAW",
        )
        self.assertEqual(r1.errno, p383.EINVAL_ERRNO)

        r2 = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_view_mode_3item_g126_and_dormant_block",
            view_mode="Unknown View",
        )
        self.assertEqual(r2.errno, p383.EINVAL_ERRNO)

    def test_81_88c_invalid_source_format_or_slot_einval(self) -> None:
        r1 = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
            source_file_format="AVCHD",
            target_slot="Slot 2",
        )
        self.assertEqual(r1.errno, p383.EINVAL_ERRNO)

        r2 = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
            target_slot="Slot 3",
        )
        self.assertEqual(r2.errno, p383.EINVAL_ERRNO)

    def test_82_88c_invalid_operation_or_body_raises(self) -> None:
        with self.assertRaises(p383.Stage88Phase383Error):
            p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(operation="bad")
        with self.assertRaises(p383.Stage88Phase383Error):
            p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
                operation="fx3_view_mode_3item_g126_and_dormant_block",
                body_model="FX9",
            )

    def test_83_88c_to_dict_serializes_cleanly(self) -> None:
        res = p383.simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
            operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
            source_file_format="XAVC S-I DCI 4K",
        )
        self.assertIn("PHOTO_CAPTURE_HARD_BLOCKED_FOR_XAVC_SI_DCI_4K", json.dumps(res.to_dict()))

    def test_84_88c_orchestrator_metrics_alignment(self) -> None:
        rep = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            work_root=None
        )
        s = rep["submodel_88c_photocap_viewmode_g126_rating_erofs_fx6_clipflag"]
        self.assertTrue(s["passed"])
        self.assertEqual(s["fx3_view_mode_exposed_count"], 3)
        self.assertTrue(s["fx3_g126_view_mode_3item_erratum_reconciled"])
        self.assertEqual(s["fx3_dormant_view_mode_exposed_events"], 0)
        self.assertEqual(s["fx3_dci4k_photo_capture_bypass_events"], 0)
        self.assertFalse(s["fx6_has_in_camera_photo_capture"])
        self.assertEqual(s["fx6_clip_flag_options_count"], 3)

    # =========================================================================
    # Tests 85..104: Sub-Model 88D — UVC Debunk vs Network Streaming SRT Caller
    # =========================================================================

    def test_85_88d_uvc_double_debunk_on_fx3_fx3a_and_a7sm3(self) -> None:
        for body in p383.FX3_UVC_UNSUPPORTED_BODIES:
            res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_usb_streaming_uvc_debunk_and_4mode_usb",
                body_model=body,
                uvc_streaming_requested=True,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.uvc_streaming_blocked)
            self.assertFalse(res.fx3_native_uvc_supported)

    def test_86_88d_usb_connection_mode_exposes_exact_4_items(self) -> None:
        self.assertEqual(len(p383.FX3_USB_CONNECTION_EXPOSED_4_MODES), 4)
        for mode in p383.FX3_USB_CONNECTION_EXPOSED_4_MODES:
            res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_usb_streaming_uvc_debunk_and_4mode_usb",
                usb_connection_mode=mode,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.usb_exposed_modes_count, 4)

        blk = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_usb_streaming_uvc_debunk_and_4mode_usb",
            usb_connection_mode="USB Streaming",
        )
        self.assertEqual(blk.errno, p383.EOPNOTSUPP_ERRNO)

    def test_87_88d_dormant_and_nonexistent_uvc_output_formats_blocked(self) -> None:
        for fmt in p383.FX3_DORMANT_UVC_ELF_FORMATS + p383.FX3_NONEXISTENT_UVC_4K_FORMATS:
            res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_usb_streaming_uvc_debunk_and_4mode_usb",
                uvc_output_format_requested=fmt,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.uvc_streaming_blocked)

    def test_88_88d_movie_rec_during_streaming_belongs_100pct_to_network_streaming(self) -> None:
        res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_usb_streaming_uvc_debunk_and_4mode_usb",
            movie_rec_under_usb_streaming_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.movie_rec_during_streaming_owner, "Network Streaming")

    def test_89_88d_network_streaming_rtmp_rtmps_h264_and_cert_check(self) -> None:
        rtmp = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            streaming_protocol="RTMP",
            video_codec="H.264",
            stream_resolution="HD (1080p)",
            stream_fps="59.94p",
            stream_bitrate_mbps=9.0,
        )
        self.assertTrue(rtmp.allowed)
        self.assertEqual(rtmp.audio_spec, "AAC-LC 48kHz 16-bit 2ch")

        rtmps_ok = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            streaming_protocol="RTMPS",
            video_codec="H.264",
            root_cert_valid=True,
        )
        self.assertTrue(rtmps_ok.allowed)

        rtmps_bad_cert = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            streaming_protocol="RTMPS",
            video_codec="H.264",
            root_cert_valid=False,
        )
        self.assertFalse(rtmps_bad_cert.allowed)
        self.assertEqual(rtmps_bad_cert.errno, p383.EACCES_ERRNO)

        rtmp_h265 = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            streaming_protocol="RTMP",
            video_codec="H.265",
        )
        self.assertEqual(rtmp_h265.errno, p383.EOPNOTSUPP_ERRNO)

    def test_90_88d_srt_caller_h265_h264_and_aes128_256(self) -> None:
        for codec in ("H.264", "H.265"):
            for enc in ("None", "AES-128", "AES-256"):
                res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                    operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
                    streaming_protocol="SRT",
                    srt_mode="Caller",
                    video_codec=codec,
                    srt_encryption=enc,
                    stream_resolution="4K (2160p)",
                    stream_fps="29.97p",
                    stream_bitrate_mbps=34.0,
                )
                self.assertTrue(res.allowed)
                self.assertEqual(res.srt_mode, "Caller")
                self.assertTrue(res.g134_srt_caller_only_reconciled)

    def test_91_88d_g134_srt_listener_and_rendezvous_hard_blocked(self) -> None:
        for bad_mode in p383.FX3_SRT_BLOCKED_MODES:
            res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
                streaming_protocol="SRT",
                srt_mode=bad_mode,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.srt_listener_blocked)

    def test_92_88d_streaming_fps_locked_to_4_rates_and_blocks_2398p_24p_120p_sq(self) -> None:
        for ok_fps in p383.FX3_STREAMING_ALLOWED_FPS:
            res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
                stream_resolution="HD (1080p)",
                stream_fps=ok_fps,
                stream_bitrate_mbps=6.0,
            )
            self.assertTrue(res.allowed, f"FPS {ok_fps} should pass")

        for bad_fps in p383.FX3_STREAMING_BLOCKED_FPS:
            res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
                stream_fps=bad_fps,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)

        sq = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            shoot_mode="S&Q",
        )
        self.assertEqual(sq.errno, p383.EOPNOTSUPP_ERRNO)

    def test_93_88d_all_8_bitrate_buckets_and_38mbps_ceiling(self) -> None:
        self.assertEqual(len(p383.FX3_STREAMING_BITRATE_8_BUCKETS), 8)
        for (res_lbl, fps_grp), spec in p383.FX3_STREAMING_BITRATE_8_BUCKETS.items():
            fps = "59.94p" if fps_grp == "60p_50p" else "29.97p"
            ok = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
                stream_resolution=res_lbl,
                stream_fps=fps,
                stream_bitrate_mbps=spec["default_mbps"],
            )
            self.assertTrue(ok.allowed, f"Bucket {res_lbl} {fps} default failed")

            over = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
                stream_resolution=res_lbl,
                stream_fps=fps,
                stream_bitrate_mbps=spec["max_mbps"] + 1.0,
            )
            self.assertFalse(over.allowed)
            self.assertEqual(over.errno, p383.EINVAL_ERRNO)

    def test_94_88d_creators_app_ble_provisioning_and_url_syntax_guard(self) -> None:
        no_app = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            creators_app_provisioned=False,
        )
        self.assertEqual(no_app.errno, p383.EAGAIN_ERRNO)

        kbd = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            manual_in_camera_url_entry=True,
        )
        self.assertEqual(kbd.errno, p383.EOPNOTSUPP_ERRNO)

        for bad_url in ("srt.example.invalid:9000", "srt.example.invalid?streamid=live"):
            res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
                server_url=bad_url,
            )
            self.assertEqual(res.errno, p383.EINVAL_ERRNO)

    def test_95_88d_airplane_mode_zero_rf_hard_block(self) -> None:
        res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            airplane_mode_on=True,
            transport="Wi-Fi",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p383.EPERM_ERRNO)
        self.assertTrue(res.airplane_zero_rf_blocked)
        self.assertEqual(res.rf_tx_packets, 0)
        self.assertEqual(res.rf_packets_transmitted, 0)

    def test_96_88d_network_streaming_resists_cam_reset_vs_network_reset(self) -> None:
        rst = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(rst.allowed)
        self.assertTrue(rst.network_streaming_survived_cam_reset)

        nrst = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            movie_rec_during_streaming="Enable",
            reset_network_set_triggered=True,
        )
        self.assertTrue(nrst.allowed)
        self.assertEqual(nrst.movie_rec_during_streaming, "Disable")

    def test_97_88d_movie_rec_during_streaming_blocks_4k_on_4k_and_2k_60p_50p(self) -> None:
        for res_lbl, fps in (
            ("4K (2160p)", "59.94p"),
            ("4K (2160p)", "29.97p"),
            ("2K (1440p)", "59.94p"),
            ("2K (1440p)", "50p"),
        ):
            r = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_movie_rec_during_streaming_and_slot1_erofs",
                movie_rec_during_streaming="Enable",
                stream_resolution=res_lbl,
                stream_fps=fps,
                internal_rec_resolution="4K (2160p)",
                target_slot="Slot 2",
            )
            self.assertFalse(r.allowed, f"Expected 4K rec blocked for {res_lbl} {fps}")
            self.assertEqual(r.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.internal_4k_rec_blocked)

        ok_2k30 = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_movie_rec_during_streaming_and_slot1_erofs",
            movie_rec_during_streaming="Enable",
            stream_resolution="2K (1440p)",
            stream_fps="29.97p",
            internal_rec_resolution="4K (2160p)",
            internal_rec_fps="29.97p",
            target_slot="Slot 2",
        )
        self.assertTrue(ok_2k30.allowed)

    def test_98_88d_movie_rec_during_streaming_fps_lock_and_slot1_erofs(self) -> None:
        mismatch = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_movie_rec_during_streaming_and_slot1_erofs",
            movie_rec_during_streaming="Enable",
            stream_resolution="HD (1080p)",
            stream_fps="59.94p",
            internal_rec_resolution="HD (1080p)",
            internal_rec_fps="29.97p",
            target_slot="Slot 2",
        )
        self.assertEqual(mismatch.errno, p383.EINVAL_ERRNO)

        s1 = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_movie_rec_during_streaming_and_slot1_erofs",
            movie_rec_during_streaming="Enable",
            stream_resolution="HD (1080p)",
            stream_fps="59.94p",
            internal_rec_resolution="HD (1080p)",
            target_slot="Slot 1",
        )
        self.assertFalse(s1.allowed)
        self.assertEqual(s1.errno, p383.EROFS_ERRNO)
        self.assertTrue(s1.slot1_erofs_blocked)
        self.assertEqual(s1.slot1_writes, 0)

    def test_99_88d_movie_rec_during_streaming_disable_default_zero_writes(self) -> None:
        res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_movie_rec_during_streaming_and_slot1_erofs",
            movie_rec_during_streaming="Disable",
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.slot1_writes, 0)

    def test_100_88d_fx6_zero_native_uvc_rtmp_rtmps_srt_qos_blocked(self) -> None:
        for proto in p383.FX6_DORMANT_STREAMING_PROTOCOLS:
            res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx6_zero_native_uvc_rtmp_srt_qos_and_external_adapters",
                body_model=p383.BODY_MODEL_FX6,
                fx6_native_protocol_requested=proto,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p383.EOPNOTSUPP_ERRNO)
            self.assertFalse(res.fx6_native_uvc_supported)
            self.assertFalse(res.fx6_native_network_streaming_supported)

    def test_101_88d_fx6_external_adapters_cbk_wa100_cbk_rpu7_pdt_fp1(self) -> None:
        for adapter in p383.FX6_EXTERNAL_STREAMING_ADAPTERS:
            res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx6_zero_native_uvc_rtmp_srt_qos_and_external_adapters",
                body_model=p383.BODY_MODEL_FX6,
                fx6_external_adapter=adapter,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.rf_tx_packets, 0)
            self.assertEqual(res.usb_tx_packets, 0)

        bad = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx6_zero_native_uvc_rtmp_srt_qos_and_external_adapters",
            body_model=p383.BODY_MODEL_FX6,
            fx6_external_adapter="UNKNOWN-BOX",
        )
        self.assertEqual(bad.errno, p383.EINVAL_ERRNO)

    def test_102_88d_invalid_operation_or_body_raises(self) -> None:
        with self.assertRaises(p383.Stage88Phase383Error):
            p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(operation="bad")
        with self.assertRaises(p383.Stage88Phase383Error):
            p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
                operation="fx3_usb_streaming_uvc_debunk_and_4mode_usb",
                body_model="FX9",
            )

    def test_103_88d_to_dict_serializes_cleanly(self) -> None:
        res = p383.simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
            operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
            streaming_protocol="SRT",
            srt_mode="Listener",
        )
        self.assertIn("G134_FX3_SRT_CALLER_ONLY", json.dumps(res.to_dict()))

    def test_104_88d_orchestrator_metrics_alignment(self) -> None:
        rep = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            work_root=None
        )
        s = rep["submodel_88d_uvc_debunk_network_streaming_srt_caller_fx6"]
        self.assertTrue(s["passed"])
        self.assertFalse(s["fx3_native_uvc_supported"])
        self.assertEqual(s["fx3_usb_connection_exposed_modes_count"], 4)
        self.assertEqual(s["fx3_streaming_bitrate_buckets_count"], 8)
        self.assertEqual(s["fx3_streaming_max_bitrate_mbps"], 38.0)
        self.assertEqual(s["fx3_srt_listener_exposed_events"], 0)
        self.assertTrue(s["fx3_g134_srt_caller_only_reconciled"])
        self.assertFalse(s["fx6_native_uvc_supported"])
        self.assertFalse(s["fx6_native_network_streaming_supported"])

    # =========================================================================
    # Tests 105..112: 4-Mode Determinism, Portability, CLI & Suite 88/88 Wiring
    # =========================================================================

    def test_105_clean_room_digest_determinism_and_source_mode_distinction(self) -> None:
        r_f1 = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            force_clean_room=True
        )
        r_f2 = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        r_f3 = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertEqual(r_f1["phase383_audit_digest_sha256"], r_f2["phase383_audit_digest_sha256"])
        self.assertEqual(r_f1["phase383_audit_digest_sha256"], r_f3["phase383_audit_digest_sha256"])

        r_dl1 = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            work_root=None
        )
        r_dl2 = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            work_root="/nonexistent/phase383_stage88_test"
        )
        self.assertEqual(r_dl1["phase383_audit_digest_sha256"], r_dl2["phase383_audit_digest_sha256"])

        r_norm = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation()
        if r_norm["source_mode"] == "LOCAL_DONOR_O_RDONLY":
            self.assertNotEqual(
                r_norm["phase383_audit_digest_sha256"],
                r_f1["phase383_audit_digest_sha256"],
            )
            self.assertNotEqual(
                r_norm["phase383_audit_digest_sha256"],
                r_dl1["phase383_audit_digest_sha256"],
            )

    def test_106_portability_no_hardcoded_usr_bin_python_and_dont_write_bytecode(self) -> None:
        forbidden = "/" + "usr/bin/" + "python"
        for src in (Path(p383.__file__).resolve(), Path(__file__).resolve()):
            txt = src.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, txt)
            self.assertIn("sys.dont_write_bytecode = True", txt)

    def test_107_standalone_cli_self_test_summary_json_help_and_subprocess(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc = p383.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 383 Stage 88 (88/88)", buf_sum.getvalue())
        self.assertIn("CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p383.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "88/88")
        self.assertTrue(parsed["all_checks_passed"])

        buf_help = io.StringIO()
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stdout(buf_help):
                p383.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("88/88", buf_help.getvalue())

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(p383.__file__).resolve()),
                "--clean-room",
                "--summary",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        self.assertIn("Phase 383 Stage 88 (88/88)", proc.stdout)

    def test_108_suite_default_config_and_forward_compatible_stage88_keys(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.include_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_hil
        )
        self.assertTrue(default_cfg.include_stage88)
        self.assertTrue(
            default_cfg.stage88_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_hil
        )

        fast_cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(fast_cfg)
        self.assertTrue(rep["all_checks_passed"])
        s88 = rep["stage88_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_hil"]
        self.assertTrue(s88["all_checks_passed"])
        self.assertEqual(s88["phase_number"], 383)
        self.assertEqual(s88["milestone"], "88/88")
        self.assertEqual(s88["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(s88["slot1_writes"], 0)
        self.assertEqual(s88["slot1_data_sector_writes"], 0)
        self.assertEqual(s88["usb_tx_packets"], 0)
        self.assertEqual(s88["rf_tx_packets"], 0)

        stage_keys = [
            f
            for f in suite.CoEmulationConfig.__dataclass_fields__
            if re.match(r"^include_phase\d+_", f)
        ]
        # Forward-compatible assertion: Base 3 stages + optional phase flags >= 88
        self.assertGreaterEqual(len(stage_keys) + 3, 88)

    def test_109_suite_cli_summary_and_skip_flags(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn(
            "realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_hil=",
            buf.getvalue(),
        )
        self.assertIn("m88=88/88", buf.getvalue())

        for skip_flag in ("--skip-stage88", "--no-include-stage88", "--skip-phase383"):
            buf_skip = io.StringIO()
            with contextlib.redirect_stdout(buf_skip):
                rc_skip = suite.main([*_FAST_CLI_FLAGS, skip_flag, "--json"])
            self.assertEqual(rc_skip, 0)
            rep_skip = json.loads(buf_skip.getvalue())
            self.assertNotIn(
                "stage88_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_hil",
                rep_skip,
            )

    def test_110_suite_tamper_detection_fails_on_wrong_milestone(self) -> None:
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        real = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            force_clean_room=True
        )
        with unittest.mock.patch.object(
            p383,
            "run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation",
            return_value={**real, "milestone": "87/87"},
        ):
            rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
            self.assertFalse(rep_bad["all_checks_passed"])

    def test_111_suite_tamper_detection_fails_on_redline_or_invariant_breach(self) -> None:
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        real = p383.run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
            force_clean_room=True
        )
        for bad_key, bad_val in (
            ("slot1_write_authorized", True),
            ("cross_model_flash_authorized", True),
            ("live_attach_authorized", True),
            ("fx3_g86_exposure_ctrl_type_reset_erratum_reconciled", False),
            ("fx3_dormant_var_shutter_exposed_events", 1),
            ("fx3_dormant_steadyshot_exposed_events", 1),
            ("fx3_view_mode_exposed_count", 4),
            ("fx3_dormant_view_mode_exposed_events", 1),
            ("fx3_native_uvc_supported", True),
            ("fx3_srt_listener_exposed_events", 1),
            ("rf_tx_packets", 1),
            ("usb_tx_packets", 1),
        ):
            with unittest.mock.patch.object(
                p383,
                "run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation",
                return_value={**real, bad_key: bad_val},
            ):
                rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
                self.assertFalse(
                    rep_bad["all_checks_passed"],
                    f"Expected tamper fail for {bad_key}",
                )

    def test_112_run_self_test_wrapper_passes_clean_room_and_donorless(self) -> None:
        r_cr = p383.run_self_test(force_clean_room=True)
        self.assertTrue(r_cr["all_checks_passed"])
        self.assertEqual(r_cr["source_mode"], "CLEAN_ROOM_SYNTHETIC")

        r_dl = p383.run_self_test(work_root=None)
        self.assertTrue(r_dl["all_checks_passed"])
        self.assertEqual(r_dl["source_mode"], "CLEAN_ROOM_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
