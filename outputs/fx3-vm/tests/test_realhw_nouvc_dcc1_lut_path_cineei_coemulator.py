#!/usr/bin/env python3
"""Unit tests for Phase 194 Stage 34 (`34/34`):
Real-Hardware `ILME-FX3` (`0x91030080`) No-UVC USB Gadget Firewall, `USB-PD` (`NP-FZ100`
Mandatory) vs `DC-C1` (`>=65W / 5A`) Power Budget, Dual-Media `.cube` LUT Path-Asymmetry,
`Cine EI` (`800/12800`) & `RMT-P1BT` BT/IR HIL Co-Emulator.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json
import os
from pathlib import Path
import re
import subprocess
import time
import unittest

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_nouvc_dcc1_lut_path_cineei_coemulator as p194  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = p194.run_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil(
            force_clean_room=True
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = p194.run_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil()
    return _DEFAULT_AUDIT_CACHE


def _get_clean_room_suite():
    global _CLEAN_SUITE_CACHE
    if _CLEAN_SUITE_CACHE is None:
        _CLEAN_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
    return _CLEAN_SUITE_CACHE


class TestPhase194NoUvcDcc1LutPathCineEiCoEmulator(unittest.TestCase):
    def test_01_schema_version_stage_34_and_redline_constants(self) -> None:
        self.assertEqual(p194.STAGE_INDEX, 34)
        self.assertEqual(p194.STAGE_TOTAL, 34)
        self.assertEqual(p194.MILESTONE_LABEL, "34/34")
        self.assertEqual(p194.STAGE_NAME, "stage34_realhw_nouvc_dcc1_lut_path_cineei_hil")
        self.assertTrue(p194.P8_CP_MUTATION_FORBIDDEN)
        self.assertFalse(p194.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p194.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p194.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p194.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p194.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p194.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p194.USB_PHY_HANG_EVENTS, 0)
        self.assertEqual(p194.POWER_CUT_BROWNOUT_EVENTS, 0)
        self.assertEqual(p194.SENSOR_ANALOG_GAIN_CONTAMINATION_EVENTS, 0)
        self.assertEqual(p194.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_donor_inspection_under_0_10s_and_cached(self) -> None:
        p194._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p194.inspect_phase194_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p194.inspect_phase194_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1
        self.assertLess(dt1, 0.10)
        self.assertLess(dt2, 0.02)
        self.assertEqual(da1.donor_files_inspected, 12)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da1.all_contracts_verified)
        if da1.source_mode == "LOCAL_DONOR_RDONLY":
            self.assertIs(da1, da2)

    def test_03_clean_room_donor_fallback_via_flag_and_env(self) -> None:
        da_flag = p194.inspect_phase194_donors(force_clean_room=True)
        self.assertEqual(da_flag.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_flag.access_mode, "O_RDONLY")
        self.assertEqual(da_flag.donor_files_inspected, 12)
        self.assertEqual(da_flag.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da_flag.all_contracts_verified)

        da_env = p194.inspect_phase194_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da_env.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_env, da_flag)

    def test_04_clean_room_sentinel_paths_do_not_touch_local_donors(self) -> None:
        paths_clean = p194.resolve_phase194_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 12)
        for p in paths_clean.values():
            self.assertIn(p194.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())
        da = p194.inspect_phase194_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_05_twelve_donors_expected_sizes_and_contracts(self) -> None:
        da = p194.inspect_phase194_donors()
        self.assertEqual(da.fx3_usb_ctrl.file_bytes, 135_424)
        self.assertEqual(da.fx6_usb_ctrl.file_bytes, 135_424)
        self.assertEqual(da.fx3_cdc_ncm.file_bytes, 32_208)
        self.assertEqual(da.fx3_rndis_host.file_bytes, 14_064)
        self.assertEqual(da.fx3_bt_core.file_bytes, 267_592)
        self.assertEqual(da.fx3_string_en_f.file_bytes, 373_820)
        self.assertEqual(da.fx3_appfw.file_bytes, 79_015_712)
        self.assertEqual(da.fx6_appfw.file_bytes, 50_520_424)
        self.assertEqual(da.fx3_cpapp.file_bytes, 15_980_568)
        self.assertEqual(da.fx6_cpapp.file_bytes, 17_952_816)
        self.assertEqual(da.fx3_libmpr.file_bytes, 3_517_008)
        self.assertEqual(da.fx6_libmpr.file_bytes, 28_921_824)
        self.assertTrue(da.usb_mode_and_usblan_proven)
        self.assertTrue(da.network_streaming_and_power_proven)
        self.assertTrue(da.cube_lut_and_cine_ei_proven)
        self.assertTrue(da.bt_sircs_mutex_proven)

    def test_06_large_donors_use_strictly_bounded_windows_only(self) -> None:
        da = p194.inspect_phase194_donors()
        for large in (
            da.fx3_appfw,
            da.fx6_appfw,
            da.fx3_cpapp,
            da.fx6_cpapp,
            da.fx3_libmpr,
            da.fx6_libmpr,
        ):
            self.assertTrue(large.bounded_windows_only)
            self.assertGreater(large.file_bytes, large.bytes_read_total)
            self.assertLessEqual(
                large.bytes_read_total,
                p194.BOUNDED_WINDOW_MAX_BYTES * (len(p194.LARGE_DONOR_WINDOWS[large.artifact_key]) + 1),
            )
            self.assertTrue(all(large.window_hits.values()))

    def test_07_pillar_a_fx3_rejects_uvc_streaming_with_eopnotsupp(self) -> None:
        res = p194.probe_usb_nouvc_gadget_firewall(
            model_name=p194.MODEL_ILME_FX3,
            requested_usb_mode=p194.USB_MODE_STREAMING_UVC,
            uvc_composite_descriptor_pushed=True,
            live_output_route=p194.LIVE_OUT_UVC_COMPOSITE_GADGET,
        )
        self.assertFalse(res.admitted)
        self.assertFalse(res.native_uvc_supported)
        self.assertEqual(res.model_id_hex, "0x91030080")
        self.assertTrue(res.uvc_gadget_rejected_eopnotsupp)
        self.assertEqual(res.errno_code, p194.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.usb_phy_hang_events, 0)
        self.assertEqual(res.appfw_crashes, 0)

    def test_08_pillar_a_fx3a_also_rejects_uvc_streaming_with_eopnotsupp(self) -> None:
        res = p194.probe_usb_nouvc_gadget_firewall(
            model_name=p194.MODEL_ILME_FX3A,
            requested_usb_mode=p194.USB_MODE_STREAMING_UVC,
            uvc_composite_descriptor_pushed=True,
        )
        self.assertFalse(res.admitted)
        self.assertFalse(res.native_uvc_supported)
        self.assertEqual(res.model_id_hex, "0x9103008a")
        self.assertTrue(res.uvc_gadget_rejected_eopnotsupp)
        self.assertEqual(res.errno_code, p194.EOPNOTSUPP_ERRNO)

    def test_09_pillar_a_valid_usb_connection_modes_admitted(self) -> None:
        for mode in p194.VALID_FX3_USB_CONNECTION_MODES:
            res = p194.probe_usb_nouvc_gadget_firewall(
                model_name=p194.MODEL_ILME_FX3,
                requested_usb_mode=mode,
                live_output_route=p194.LIVE_OUT_TYPE_A_HDMI,
            )
            self.assertTrue(res.admitted, msg=mode)
            self.assertEqual(res.errno_code, 0)
            self.assertFalse(res.uvc_gadget_rejected_eopnotsupp)

    def test_10_pillar_a_usblan_cdc_ncm_power_on_auto_connect_srt_38mbps(self) -> None:
        res = p194.probe_usb_nouvc_gadget_firewall(
            model_name=p194.MODEL_ILME_FX3,
            requested_usb_mode=p194.USB_MODE_SEL_WHEN_CONNECT,
            usb_lan_enabled=True,
            usb_lan_protocol=p194.USB_LAN_PROTO_CDC_NCM,
            usb_lan_power_on_auto_connect=True,
            live_output_route=p194.LIVE_OUT_NETWORK_STREAMING,
            streaming_protocol="SRT",
            streaming_codec="HEVC",
            resolution="3840x2160",
            fps_label="59.94p",
            bitrate_mbps=38.0,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.usb_lan_enabled)
        self.assertEqual(res.usb_lan_protocol, "CDC-NCM")
        self.assertTrue(res.usb_lan_power_on_auto_connect)
        self.assertEqual(res.bitrate_mbps, 38.0)
        self.assertTrue(res.audio_enabled)

    def test_11_pillar_a_usblan_rndis_rtmp_rtmps_admitted(self) -> None:
        for proto in ("RTMP", "RTMPS"):
            res = p194.probe_usb_nouvc_gadget_firewall(
                model_name=p194.MODEL_ILME_FX3,
                requested_usb_mode=p194.USB_MODE_MTP,
                usb_lan_enabled=True,
                usb_lan_protocol=p194.USB_LAN_PROTO_RNDIS,
                usb_lan_power_on_auto_connect=True,
                live_output_route=p194.LIVE_OUT_NETWORK_STREAMING,
                streaming_protocol=proto,
                streaming_codec="AVC",
                bitrate_mbps=25.0,
            )
            self.assertTrue(res.admitted, msg=proto)
            self.assertEqual(res.streaming_protocol, proto)

    def test_12_pillar_a_network_streaming_gt38mbps_rejected(self) -> None:
        res = p194.probe_usb_nouvc_gadget_firewall(
            model_name=p194.MODEL_ILME_FX3,
            usb_lan_enabled=True,
            usb_lan_protocol=p194.USB_LAN_PROTO_CDC_NCM,
            live_output_route=p194.LIVE_OUT_NETWORK_STREAMING,
            streaming_protocol="SRT",
            streaming_codec="HEVC",
            bitrate_mbps=38.1,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.status_code, "BLOCKED_NETWORK_STREAMING_BUDGET_OR_PROTO")

    def test_13_pillar_a_invalid_usblan_protocol_and_streaming_proto_rejected(self) -> None:
        bad_lan = p194.probe_usb_nouvc_gadget_firewall(
            usb_lan_enabled=True,
            usb_lan_protocol="PPP",
        )
        self.assertFalse(bad_lan.admitted)
        self.assertEqual(bad_lan.status_code, "BLOCKED_INVALID_USB_LAN_PROTOCOL")

        bad_stream = p194.probe_usb_nouvc_gadget_firewall(
            live_output_route=p194.LIVE_OUT_NETWORK_STREAMING,
            streaming_protocol="RTSP",
            streaming_codec="VP9",
            bitrate_mbps=15.0,
        )
        self.assertFalse(bad_stream.admitted)

    def test_14_pillar_a_legacy_imaging_edge_webcam_remote_shooting_576p_no_audio(self) -> None:
        res_ok = p194.probe_usb_nouvc_gadget_firewall(
            requested_usb_mode=p194.USB_MODE_REMOTE_SHOOTING,
            live_output_route=p194.LIVE_OUT_IMAGING_EDGE_WEBCAM_REMOTE,
        )
        self.assertTrue(res_ok.admitted)
        self.assertEqual(res_ok.resolution, "1024x576")
        self.assertFalse(res_ok.audio_enabled)

        res_bad = p194.probe_usb_nouvc_gadget_firewall(
            requested_usb_mode=p194.USB_MODE_MSC,
            live_output_route=p194.LIVE_OUT_IMAGING_EDGE_WEBCAM_REMOTE,
        )
        self.assertFalse(res_bad.admitted)
        self.assertEqual(res_bad.status_code, "BLOCKED_WEBCAM_REQUIRES_REMOTE_SHOOTING_MODE")

    def test_15_pillar_a_type_a_hdmi_clean_4k5994_live_output(self) -> None:
        res = p194.probe_usb_nouvc_gadget_firewall(
            requested_usb_mode=p194.USB_MODE_MSC,
            live_output_route=p194.LIVE_OUT_TYPE_A_HDMI,
            resolution="3840x2160",
            fps_label="59.94p",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.audio_enabled)
        self.assertEqual(res.status_code, "TYPE_A_HDMI_CLEAN_LIVE_OUTPUT_OK")

    def test_16_pillar_a_invalid_model_or_route_raises(self) -> None:
        with self.assertRaises(p194.RealHwNoUvcDcc1LutCineEiError):
            p194.probe_usb_nouvc_gadget_firewall(model_name="INVALID-BODY")
        with self.assertRaises(p194.RealHwNoUvcDcc1LutCineEiError):
            p194.probe_usb_nouvc_gadget_firewall(live_output_route="INVALID_ROUTE")

    def test_17_pillar_b_body_usb_pd_requires_npfz100_and_pauses_charge_while_on(self) -> None:
        on_res = p194.probe_power_supply_budget(
            power_path=p194.POWER_PATH_BODY_USB_PD,
            npfz100_inserted=True,
            usb_power_supply_menu_on=True,
            camera_powered_off=False,
        )
        self.assertTrue(on_res.admitted)
        self.assertTrue(on_res.npfz100_inserted)
        self.assertFalse(on_res.internal_battery_charging_active)
        self.assertFalse(on_res.instant_power_cut_hazard)

        off_res = p194.probe_power_supply_budget(
            power_path=p194.POWER_PATH_BODY_USB_PD,
            npfz100_inserted=True,
            usb_power_supply_menu_on=True,
            camera_powered_off=True,
        )
        self.assertTrue(off_res.admitted)
        self.assertTrue(off_res.internal_battery_charging_active)
        self.assertTrue(off_res.power_off_charging_resumed)

    def test_18_pillar_b_npfz100_hot_pull_triggers_instant_power_cut_hazard(self) -> None:
        res = p194.probe_power_supply_budget(
            power_path=p194.POWER_PATH_BODY_USB_PD,
            npfz100_inserted=False,
            usb_power_supply_menu_on=True,
        )
        self.assertFalse(res.admitted)
        self.assertTrue(res.instant_power_cut_hazard)
        self.assertTrue(res.brownout_guard_tripped)
        self.assertEqual(res.power_cut_brownout_events, 0)
        self.assertEqual(res.appfw_crashes, 0)

    def test_19_pillar_b_micro_usb_power_strictly_rejected(self) -> None:
        res = p194.probe_power_supply_budget(power_path=p194.POWER_PATH_MICRO_USB)
        self.assertFalse(res.admitted)
        self.assertEqual(res.status_code, "REJECTED_MICRO_USB_POWER_NOT_SUPPORTED")

    def test_20_pillar_b_dcc1_65w_5a_emarked_frees_type_c_and_locks_lcd_max(self) -> None:
        res = p194.probe_power_supply_budget(
            power_path=p194.POWER_PATH_DC_C1_COUPLER,
            pd_adapter_watts=65,
            cable_rated_amps=5,
            cable_emarker_present=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.body_type_c_freed_for_data)
        self.assertTrue(res.lcd_max_brightness_locked)
        self.assertFalse(res.dc_c1_led_blinking_alarm)
        self.assertFalse(res.brownout_guard_tripped)

    def test_21_pillar_b_dcc1_lt65w_trips_blinking_led_brownout_guard(self) -> None:
        res = p194.probe_power_supply_budget(
            power_path=p194.POWER_PATH_DC_C1_COUPLER,
            pd_adapter_watts=45,
            cable_rated_amps=5,
            cable_emarker_present=True,
        )
        self.assertFalse(res.admitted)
        self.assertTrue(res.dc_c1_led_blinking_alarm)
        self.assertTrue(res.brownout_guard_tripped)
        self.assertEqual(res.power_cut_brownout_events, 0)

    def test_22_pillar_b_dcc1_3a_or_unmarked_cable_trips_blinking_led_guard(self) -> None:
        res_3a = p194.probe_power_supply_budget(
            power_path=p194.POWER_PATH_DC_C1_COUPLER,
            pd_adapter_watts=100,
            cable_rated_amps=3,
            cable_emarker_present=True,
        )
        self.assertFalse(res_3a.admitted)
        self.assertTrue(res_3a.dc_c1_led_blinking_alarm)

        res_no_emark = p194.probe_power_supply_budget(
            power_path=p194.POWER_PATH_DC_C1_COUPLER,
            pd_adapter_watts=100,
            cable_rated_amps=5,
            cable_emarker_present=False,
        )
        self.assertFalse(res_no_emark.admitted)
        self.assertTrue(res_no_emark.dc_c1_led_blinking_alarm)

    def test_23_pillar_b_battery_only_and_usb_supply_off_states(self) -> None:
        bat_ok = p194.probe_power_supply_budget(
            power_path=p194.POWER_PATH_BATTERY_ONLY,
            npfz100_inserted=True,
        )
        self.assertTrue(bat_ok.admitted)
        bat_miss = p194.probe_power_supply_budget(
            power_path=p194.POWER_PATH_BATTERY_ONLY,
            npfz100_inserted=False,
        )
        self.assertFalse(bat_miss.admitted)
        with self.assertRaises(p194.RealHwNoUvcDcc1LutCineEiError):
            p194.probe_power_supply_budget(power_path="INVALID_POWER")

    def test_24_pillar_c_sd_requires_private_prefix_and_cfexpress_forbids_private(self) -> None:
        sd_ok = p194.validate_dual_media_cube_lut_path(
            media_type=p194.MEDIA_SD_SDXC,
            directory_path="/Private/Sony/PRO/LUT/",
            filename="Sony_Rec709_33.cube",
            lut_points=33,
        )
        self.assertTrue(sd_ok.admitted)
        self.assertEqual(sd_ok.p2_setting_slots_max, 16)
        self.assertFalse(sd_ok.persistent_emmc_writes_authorized)

        cf_ok = p194.validate_dual_media_cube_lut_path(
            media_type=p194.MEDIA_CFEXPRESS_A,
            directory_path="/Sony/PRO/LUT/",
            filename="Sony_Cine_17.cube",
            lut_points=17,
        )
        self.assertTrue(cf_ok.admitted)

        cf_bad = p194.validate_dual_media_cube_lut_path(
            media_type=p194.MEDIA_CFEXPRESS_A,
            directory_path="/Private/Sony/PRO/LUT/",
            filename="Sony_Rec709_33.cube",
            lut_points=33,
        )
        self.assertFalse(cf_bad.admitted)
        self.assertEqual(cf_bad.status_code, "REJECTED_DUAL_MEDIA_LUT_PATH_ASYMMETRY_MISMATCH")

        sd_bad = p194.validate_dual_media_cube_lut_path(
            media_type=p194.MEDIA_SD_SDXC,
            directory_path="/Sony/PRO/LUT/",
            filename="Sony_Rec709_33.cube",
            lut_points=33,
        )
        self.assertFalse(sd_bad.admitted)
        self.assertEqual(sd_bad.status_code, "REJECTED_DUAL_MEDIA_LUT_PATH_ASYMMETRY_MISMATCH")

    def test_25_pillar_c_cube_grid_65pt_rejected_and_17pt_33pt_accepted(self) -> None:
        for pts in (17, 33):
            res = p194.validate_dual_media_cube_lut_path(
                media_type=p194.MEDIA_SD_SDXC,
                directory_path="/Private/Sony/PRO/LUT/",
                filename=f"Lut_{pts}.cube",
                lut_points=pts,
            )
            self.assertTrue(res.admitted, msg=pts)

        bad_65 = p194.validate_dual_media_cube_lut_path(
            media_type=p194.MEDIA_SD_SDXC,
            directory_path="/Private/Sony/PRO/LUT/",
            filename="Lut_65.cube",
            lut_points=65,
        )
        self.assertFalse(bad_65.admitted)
        self.assertEqual(bad_65.status_code, "REJECTED_UNSUPPORTED_CUBE_LUT_GRID_SIZE")

    def test_26_pillar_c_cube_filename_max_63_bytes_ascii_only(self) -> None:
        ok_63 = p194.validate_dual_media_cube_lut_path(
            filename=("A" * 58) + ".cube",  # 58 + 5 = 63B
        )
        self.assertTrue(ok_63.admitted)
        self.assertEqual(ok_63.filename_bytes, 63)

        bad_64 = p194.validate_dual_media_cube_lut_path(
            filename=("A" * 59) + ".cube",  # 64B > 63B
        )
        self.assertFalse(bad_64.admitted)
        self.assertEqual(bad_64.status_code, "REJECTED_CUBE_FILENAME_GT63B_OR_NON_ALNUM")

        bad_trav = p194.validate_dual_media_cube_lut_path(
            filename="../evil.cube",
        )
        self.assertFalse(bad_trav.admitted)

    def test_27_pillar_c_16_user_lut_slots_and_0_to_2ev_ae_offset(self) -> None:
        for slot in (1, 16):
            for ev in (0.0, 0.3, 1.0, 2.0):
                res = p194.validate_dual_media_cube_lut_path(
                    user_slot_index=slot,
                    ae_level_offset_ev=ev,
                )
                self.assertTrue(res.admitted, msg=(slot, ev))

        bad_slot = p194.validate_dual_media_cube_lut_path(user_slot_index=17)
        self.assertFalse(bad_slot.admitted)
        bad_ev = p194.validate_dual_media_cube_lut_path(ae_level_offset_ev=-0.3)
        self.assertFalse(bad_ev.admitted)
        bad_ev_hi = p194.validate_dual_media_cube_lut_path(ae_level_offset_ev=2.3)
        self.assertFalse(bad_ev_hi.admitted)

    def test_28_pillar_c_cine_ei_800_and_12800_zero_analog_gain_contamination(self) -> None:
        r_800_low = p194.evaluate_cine_ei_exposure(base_iso=800, ei_index=200)
        self.assertTrue(r_800_low.admitted)
        self.assertEqual(r_800_low.sensor_analog_gain_locked_iso, 800)
        self.assertEqual(r_800_low.lut_gain_offset_ev, -2.0)
        self.assertEqual(r_800_low.sensor_analog_gain_contamination_events, 0)

        r_12800_3200 = p194.evaluate_cine_ei_exposure(base_iso=12800, ei_index=3200)
        self.assertTrue(r_12800_3200.admitted)
        self.assertEqual(r_12800_3200.sensor_analog_gain_locked_iso, 12800)
        self.assertEqual(r_12800_3200.lut_gain_offset_ev, -2.0)

        r_12800_51200 = p194.evaluate_cine_ei_exposure(base_iso=12800, ei_index=51200)
        self.assertTrue(r_12800_51200.admitted)
        self.assertEqual(r_12800_51200.sensor_analog_gain_locked_iso, 12800)
        self.assertEqual(r_12800_51200.lut_gain_offset_ev, 2.0)

    def test_29_pillar_c_cine_ei_out_of_range_rejected_and_invalid_base_raises(self) -> None:
        bad_ei = p194.evaluate_cine_ei_exposure(base_iso=12800, ei_index=64000)
        self.assertFalse(bad_ei.admitted)
        self.assertEqual(bad_ei.status_code, "REJECTED_CINE_EI_INDEX_OUT_OF_RANGE")
        with self.assertRaises(p194.RealHwNoUvcDcc1LutCineEiError):
            p194.evaluate_cine_ei_exposure(base_iso=3200, ei_index=3200)

    def test_30_pillar_d_rmtp1bt_bt_on_disables_ir_and_smartphone_gps_linkage(self) -> None:
        res = p194.probe_rmtp1bt_and_clip_flag_mutex(
            model_name=p194.MODEL_ILME_FX3,
            bluetooth_rmt_ctrl_on=True,
            rmtp1bt_bt42_paired=True,
            requested_ir_command=True,
            clip_flag_filter="OK",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.rmtp1bt_bt42_paired)
        self.assertTrue(res.ir_hw_present)
        self.assertTrue(res.nfc_hw_present)
        self.assertFalse(res.ir_receiver_enabled)
        self.assertFalse(res.gps_location_linkage_enabled)
        self.assertTrue(res.ir_command_ignored)
        self.assertEqual(res.filtered_clip_ids, ("C0001", "C0004"))
        self.assertTrue(res.h0_equals_h3)

    def test_31_pillar_d_rmtp1bt_bt_off_enables_ir_on_fx3_but_fx3a_lacks_ir_nfc(self) -> None:
        fx3_ir = p194.probe_rmtp1bt_and_clip_flag_mutex(
            model_name=p194.MODEL_ILME_FX3,
            bluetooth_rmt_ctrl_on=False,
            requested_ir_command=True,
            clip_flag_filter="KEEP",
        )
        self.assertTrue(fx3_ir.ir_receiver_enabled)
        self.assertTrue(fx3_ir.gps_location_linkage_enabled)
        self.assertFalse(fx3_ir.ir_command_ignored)
        self.assertEqual(fx3_ir.filtered_clip_ids, ("C0003",))

        fx3a = p194.probe_rmtp1bt_and_clip_flag_mutex(
            model_name=p194.MODEL_ILME_FX3A,
            bluetooth_rmt_ctrl_on=False,
            requested_ir_command=True,
            clip_flag_filter="NG",
        )
        self.assertFalse(fx3a.ir_hw_present)
        self.assertFalse(fx3a.nfc_hw_present)
        self.assertFalse(fx3a.ir_receiver_enabled)
        self.assertTrue(fx3a.ir_command_ignored)
        self.assertEqual(fx3a.filtered_clip_ids, ("C0002",))

    def test_32_pillar_d_clip_flag_filter_none_and_invalid_raises(self) -> None:
        res_all = p194.probe_rmtp1bt_and_clip_flag_mutex(clip_flag_filter="NONE")
        self.assertEqual(len(res_all.filtered_clip_ids), 4)
        with self.assertRaises(p194.RealHwNoUvcDcc1LutCineEiError):
            p194.probe_rmtp1bt_and_clip_flag_mutex(clip_flag_filter="INVALID")
        with self.assertRaises(p194.RealHwNoUvcDcc1LutCineEiError):
            p194.probe_rmtp1bt_and_clip_flag_mutex(model_name="ILME-FX6")

    def test_33_hard_safety_redlines_reject_all_nine_forbidden_actions(self) -> None:
        base = p194.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.spi_nor_write_authorized)
        self.assertFalse(base.el3_payload_transmit_authorized)
        self.assertEqual(base.physical_usb_packets_emitted, 0)
        self.assertEqual(base.otp_fuse_touches, 0)
        self.assertEqual(base.rpmb_counter_increments, 0)

        for kw in (
            {"authorize_persistent_emmc_writes": True},
            {"authorize_spi_nor_write": True},
            {"authorize_el3_payload_transmit": True},
            {"emit_physical_usb_packet": True},
            {"touch_otp_fuse": True},
            {"increment_rpmb_counter": True},
            {"trigger_usb_phy_hang": True},
            {"trigger_power_cut_brownout": True},
            {"contaminate_sensor_analog_gain": True},
        ):
            r = p194.probe_hard_safety_redline(**kw)
            self.assertFalse(r.valid, msg=kw)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertEqual(r.physical_usb_packets_emitted, 0)
            self.assertEqual(r.otp_fuse_touches, 0)
            self.assertEqual(r.rpmb_counter_increments, 0)

    def test_34_pillar_a_evaluator_all_passed(self) -> None:
        pa = p194.evaluate_pillar_a_nouvc_usb_gadget_firewall()
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["uvc_composite_rejected_eopnotsupp"]["errno_code"], 95)

    def test_35_pillar_b_evaluator_all_passed(self) -> None:
        pb = p194.evaluate_pillar_b_usb_pd_vs_dcc1_power_budget()
        self.assertTrue(pb["passed"])
        self.assertTrue(pb["npfz100_pulled_instant_power_cut_hazard"]["instant_power_cut_hazard"])
        self.assertTrue(pb["dcc1_45w_blinking_led_blocked"]["dc_c1_led_blinking_alarm"])

    def test_36_pillar_cd_evaluator_all_passed(self) -> None:
        pcd = p194.evaluate_pillar_c_d_lut_cineei_rmtp1bt_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["blocked_redline_probes"]), 9)

    def test_37_unified_phase194_clean_room_no_raw_elf_bytes_leaked(self) -> None:
        rep = _get_clean_room_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep["stage_index"], 34)
        self.assertEqual(rep["stage_total"], 34)
        self.assertEqual(rep["milestone"], "34/34")
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)
        dumped = json.dumps(rep)
        self.assertNotIn("7f454c46", dumped.lower())

    def test_38_unified_phase194_default_mode_passes_with_all_pillars(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(rep["pillar_a_nouvc_usb_gadget_firewall_hil"]["passed"])
        self.assertTrue(rep["pillar_b_usb_pd_vs_dcc1_power_budget_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_lut_path_cineei_rmtp1bt_and_redlines"]["passed"])
        self.assertEqual(rep["redlines"]["emmc_nflasha_write_count"], 0)
        self.assertEqual(rep["redlines"]["usb_phy_hang_events"], 0)
        self.assertEqual(rep["redlines"]["power_cut_brownout_events"], 0)
        self.assertEqual(rep["redlines"]["sensor_analog_gain_contamination_events"], 0)

    def test_39_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "realhw_nouvc_dcc1_lut_path_cineei_coemulator.py"),
                "--self-test",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 194 Stage 34 (34/34)", p_sum.stdout)

        p_json = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "realhw_nouvc_dcc1_lut_path_cineei_coemulator.py"),
                "--self-test",
                "--clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        parsed = json.loads(p_json.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["stage_index"], 34)

    def test_40_fx3_vm_coemulation_suite_includes_stage34_and_skip_phase194(self) -> None:
        rep_on = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage34_realhw_nouvc_dcc1_lut_path_cineei_hil", rep_on)
        s34 = rep_on["stage34_realhw_nouvc_dcc1_lut_path_cineei_hil"]
        self.assertTrue(s34["all_checks_passed"])
        self.assertFalse(s34["persistent_emmc_writes_authorized"])
        self.assertFalse(s34["spi_nor_write_authorized"])
        self.assertFalse(s34["el3_payload_transmit_authorized"])
        self.assertEqual(s34["physical_usb_packets_emitted"], 0)
        self.assertEqual(s34["otp_fuse_touches"], 0)
        self.assertEqual(s34["rpmb_counter_increments"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 34)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage34_realhw_nouvc_dcc1_lut_path_cineei_hil", rep_skip)
        self.assertGreaterEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), 33)

    def test_41_all_34_of_34_stages_present_and_passing_in_suite(self) -> None:
        rep = _get_clean_room_suite()
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 35):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"], msg=matches[0])

    def test_42_suite_subprocess_summary_and_skip_phase194_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("realhw_nouvc_dcc1_lut_path_cineei_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase194",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_nouvc_dcc1_lut_path_cineei_hil=", proc_skip.stdout)

    def test_43_suite_34_stages_under_6s_wall_clock_ceiling_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 34)
        self.assertLess(dt_clean, 6.0)

        t1 = time.monotonic()
        rep_def = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_def = time.monotonic() - t1
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_def if re.match(r"^stage\d+_", k)]), 34)
        self.assertLess(dt_def, 6.0)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_json = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        d_json = json.loads(p_json.stdout)
        self.assertTrue(d_json["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in d_json if re.match(r"^stage\d+_", k)]), 34)

    def test_44_source_hygiene_rdonly_and_no_forbidden_flags_or_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_nouvc_dcc1_lut_path_cineei_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("sys.dont_write_bytecode = True", src)
        self.assertNotIn("O_WR" + "ONLY", src)
        self.assertNotIn("O_RD" + "WR", src)
        forbidden_port = str(87 * 100 + 68)
        self.assertNotIn(forbidden_port, src)

    def test_45_audit_digest_deterministic_across_repeated_clean_room_runs(self) -> None:
        r1 = p194.run_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil(force_clean_room=True)
        r2 = p194.run_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil(force_clean_room=True)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_46_stage34_wall_clock_standalone_well_below_6s(self) -> None:
        t0 = time.monotonic()
        r = p194.run_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil()
        dt = time.monotonic() - t0
        self.assertTrue(r["all_checks_passed"])
        self.assertLess(dt, 6.0)

    def test_47_dual_media_lut_invalid_media_raises_and_slash_normalization(self) -> None:
        sd_noslash = p194.validate_dual_media_cube_lut_path(
            media_type=p194.MEDIA_SD_SDXC,
            directory_path="/Private/Sony/PRO/LUT",
            filename="Norm_17.cube",
            lut_points=17,
        )
        self.assertTrue(sd_noslash.admitted)
        with self.assertRaises(p194.RealHwNoUvcDcc1LutCineEiError):
            p194.validate_dual_media_cube_lut_path(media_type="NVME")

    def test_48_usb_connection_mode_unknown_string_blocked_eopnotsupp(self) -> None:
        res = p194.probe_usb_nouvc_gadget_firewall(
            model_name=p194.MODEL_ILME_FX3,
            requested_usb_mode="VendorCustomGadget",
        )
        self.assertFalse(res.admitted)
        self.assertTrue(res.uvc_gadget_rejected_eopnotsupp)
        self.assertEqual(res.errno_code, p194.EOPNOTSUPP_ERRNO)


if __name__ == "__main__":
    unittest.main()
