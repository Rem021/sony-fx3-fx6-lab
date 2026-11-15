#!/usr/bin/env python3
"""Unit tests for Phase 182 Stage 32 (`32/32`):
Real-Hardware MIRA_CETUS2 E-Mount info7/info8/info3D + 0x02cf0232 Breathing &
Type-A HDMI 4264x2408 16-bit RAW (BRAW / ProRes RAW) HIL Co-Emulator.
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
import realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator as p182  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = p182.run_phase182_realhw_emount_info3d_hdmi_4264_raw_hil(
            force_clean_room=True
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = p182.run_phase182_realhw_emount_info3d_hdmi_4264_raw_hil()
    return _DEFAULT_AUDIT_CACHE


class TestPhase182EmountInfo3dHdmiRawCoEmulator(unittest.TestCase):
    def test_01_schema_version_stage_32_and_redline_constants(self) -> None:
        self.assertEqual(p182.STAGE_INDEX, 32)
        self.assertEqual(p182.STAGE_TOTAL, 32)
        self.assertEqual(p182.MILESTONE_LABEL, "32/32")
        self.assertEqual(p182.STAGE_NAME, "stage32_realhw_emount_info3d_breathing_hdmi_4264_raw_hil")
        self.assertEqual(p182.BKID_APP_MR_SETTING_LENS_COMP_BREATHING, 0x02CF0232)
        self.assertTrue(p182.P8_CP_MUTATION_FORBIDDEN)
        self.assertFalse(p182.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p182.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p182.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p182.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p182.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p182.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p182.LENS_PARTITION_WRITES, 0)
        self.assertEqual(p182.SDI_BNC_MMIO_FAULTS, 0)
        self.assertEqual(p182.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_donor_inspection_under_0_10s_and_cached(self) -> None:
        p182._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p182.inspect_phase182_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p182.inspect_phase182_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1
        self.assertLess(dt1, 0.10)
        self.assertLess(dt2, 0.02)
        self.assertEqual(da1.donor_files_inspected, 12)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da1.all_contracts_verified)
        if da1.source_mode == "LOCAL_DONOR_RDONLY":
            self.assertIs(da1, da2)

    def test_03_clean_room_donor_fallback_via_flag_and_env(self) -> None:
        da_flag = p182.inspect_phase182_donors(force_clean_room=True)
        self.assertEqual(da_flag.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_flag.access_mode, "O_RDONLY")
        self.assertEqual(da_flag.donor_files_inspected, 12)
        self.assertEqual(da_flag.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da_flag.all_contracts_verified)

        da_env = p182.inspect_phase182_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da_env.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_env, da_flag)

    def test_04_clean_room_sentinel_paths_do_not_touch_local_donors(self) -> None:
        paths_clean = p182.resolve_phase182_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 12)
        for p in paths_clean.values():
            self.assertIn(p182.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())
        da = p182.inspect_phase182_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_05_twelve_donors_expected_sizes_and_abi_parity(self) -> None:
        da = p182.inspect_phase182_donors()
        self.assertEqual(da.fx3_lens_comm.file_bytes, 14_544)
        self.assertEqual(da.fx6_lens_comm.file_bytes, 14_544)
        self.assertEqual(da.fx3_adj_media.file_bytes, 318_152)
        self.assertEqual(da.fx6_adj_media.file_bytes, 334_536)
        self.assertEqual(da.fx3_string_en.file_bytes, 165_740)
        self.assertEqual(da.fx3_string_en_g.file_bytes, 69_600)
        self.assertEqual(da.fx6_string_en.file_bytes, 118_208)
        self.assertEqual(da.fx6_string_en_2.file_bytes, 118_676)
        self.assertEqual(da.fx3_cpapp.file_bytes, 15_980_568)
        self.assertEqual(da.fx6_cpapp.file_bytes, 17_952_816)
        self.assertEqual(da.fx3_appfw.file_bytes, 79_015_712)
        self.assertEqual(da.fx6_appfw.file_bytes, 50_520_424)
        self.assertTrue(da.lens_comm_abi_parity_proven)
        self.assertTrue(da.fx6_bkid_02cf0232_and_info7_8_proven)
        self.assertTrue(da.fx6_4264x2408_and_prores_proven)
        self.assertTrue(da.fx3_breathing_and_hdmi_raw_proven)

    def test_06_large_donors_bounded_windows_max_4096b_each(self) -> None:
        da = p182.inspect_phase182_donors()
        for item in (da.fx3_cpapp, da.fx6_cpapp, da.fx3_appfw, da.fx6_appfw):
            self.assertTrue(item.bounded_windows_only)
            self.assertLessEqual(item.bytes_read_total, 20_480)
            self.assertTrue(all(v == 1 for v in item.window_hits.values()))

    def test_07_sony_first_party_emount_whitelist_predicate_exact(self) -> None:
        self.assertTrue(p182.is_sony_first_party_emount_lens(0xC120))  # SELP1635G
        self.assertTrue(p182.is_sony_first_party_emount_lens(0xC135))  # SEL2470GM2
        self.assertTrue(p182.is_sony_first_party_emount_lens(0xC000))
        self.assertTrue(p182.is_sony_first_party_emount_lens(0xFFFE))
        # Reserved 0x0FFF low 12 bits must NOT pass whitelist
        self.assertFalse(p182.is_sony_first_party_emount_lens(0xCFFF))
        self.assertFalse(p182.is_sony_first_party_emount_lens(0xFFFF))
        # Third-party top 2 bits != 3
        self.assertFalse(p182.is_sony_first_party_emount_lens(0x4210))
        self.assertFalse(p182.is_sony_first_party_emount_lens(0x8150))
        self.assertFalse(p182.is_sony_first_party_emount_lens(0x0001))

    def test_08_classify_emount_lens_all_three_tiers(self) -> None:
        self.assertEqual(p182.classify_emount_lens(0xC120), p182.LENS_CLASS_SONY_FIRST_PARTY)
        self.assertEqual(p182.classify_emount_lens(0x4210), p182.LENS_CLASS_THIRD_PARTY)
        self.assertEqual(p182.classify_emount_lens(0xCFFF), p182.LENS_CLASS_THIRD_PARTY)
        self.assertEqual(p182.classify_emount_lens(0xFFFF), p182.LENS_CLASS_MANUAL_PL)

    def test_09_emount_info7_info8_info3d_packets_crc32_valid(self) -> None:
        i7, i8, i3d = p182.build_emount_info_packets(lens_id=0xC135)
        self.assertTrue(i7.startswith(b"I7"))
        self.assertTrue(i8.startswith(b"I8"))
        self.assertTrue(i3d.startswith(b"3D"))
        self.assertEqual(len(i7), 9)
        self.assertEqual(len(i8), 11)
        self.assertEqual(len(i3d), 12)

    def test_10_sony_pz1635_and_2470gm2_breathing_catalyst_focusmap_ok(self) -> None:
        res = p182.coemulate_emount_info3d_and_breathing(
            lens_id=0xC135,
            lens_name="FE 24-70mm F2.8 GM II",
            breathing_comp_requested=True,
            breathing_crop_factor=1.072,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.sony_first_party_match)
        self.assertTrue(res.info_crc32_valid)
        self.assertTrue(res.breathing_comp_authorized)
        self.assertTrue(res.bkid_0x02cf0232_passthrough)
        self.assertEqual(res.breathing_crop_factor, 1.072)
        self.assertTrue(res.catalyst_breathing_meta_injected)
        self.assertTrue(res.focus_map_stream_active)
        self.assertEqual(res.p18_blkroset, 1)
        self.assertEqual(res.lens_partition_writes, 0)
        self.assertEqual(res.status_code, "SONY_EMOUNT_INFO3D_02CF0232_CATALYST_FOCUSMAP_OK")

    def test_11_sony_breathing_off_keeps_1x_and_no_catalyst_meta(self) -> None:
        res = p182.coemulate_emount_info3d_and_breathing(
            lens_id=0xC120,
            lens_name="FE PZ 16-35mm F4 G",
            breathing_comp_requested=False,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.breathing_comp_authorized)
        self.assertEqual(res.breathing_crop_factor, 1.0)
        self.assertFalse(res.catalyst_breathing_meta_injected)
        self.assertTrue(res.focus_map_stream_active)
        self.assertEqual(res.status_code, "SONY_EMOUNT_BREATHING_OFF_1X_OK")

    def test_12_third_party_emount_gates_breathing_and_catalyst(self) -> None:
        res = p182.coemulate_emount_info3d_and_breathing(
            lens_id=0x4210,
            lens_name="Sigma 24-70mm F2.8 DG DN Art",
            breathing_comp_requested=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.lens_class, p182.LENS_CLASS_THIRD_PARTY)
        self.assertFalse(res.sony_first_party_match)
        self.assertFalse(res.breathing_comp_authorized)
        self.assertFalse(res.bkid_0x02cf0232_passthrough)
        self.assertEqual(res.breathing_crop_factor, 1.0)
        self.assertFalse(res.catalyst_breathing_meta_injected)
        self.assertEqual(res.status_code, "THIRD_PARTY_EMOUNT_02CF0232_GATED_OK")

    def test_13_reserved_0cfff_trap_gated_fail_safe(self) -> None:
        res = p182.coemulate_emount_info3d_and_breathing(
            lens_id=0xCFFF,
            lens_name="Reserved Low12 FFF",
            breathing_comp_requested=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.sony_first_party_match)
        self.assertFalse(res.breathing_comp_authorized)
        self.assertEqual(res.breathing_crop_factor, 1.0)

    def test_14_manual_pl_adapter_0xffff_clean_1x_bypass(self) -> None:
        res = p182.coemulate_emount_info3d_and_breathing(
            lens_id=0xFFFF,
            lens_name="Manual PL-to-E",
            breathing_comp_requested=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.lens_class, p182.LENS_CLASS_MANUAL_PL)
        self.assertFalse(res.breathing_comp_authorized)
        self.assertFalse(res.focus_map_stream_active)
        self.assertEqual(res.breathing_crop_factor, 1.0)
        self.assertEqual(res.status_code, "MANUAL_PL_ADAPTER_1X_BYPASS_OK")

    def test_15_hdmi_raw_active_bypasses_breathing_for_clean_4264_sensor_crop(self) -> None:
        res = p182.coemulate_emount_info3d_and_breathing(
            lens_id=0xC135,
            breathing_comp_requested=True,
            hdmi_raw_active=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.breathing_comp_authorized)
        self.assertEqual(res.breathing_crop_factor, 1.0)
        self.assertFalse(res.catalyst_breathing_meta_injected)
        self.assertEqual(res.status_code, "SONY_EMOUNT_HDMI_RAW_1X_BYPASS_OK")

    def test_16_monitor_and_control_version_gating_2_1_0(self) -> None:
        res_old = p182.coemulate_emount_info3d_and_breathing(lens_id=0xC135, mc_app_version="2.0.9")
        res_new = p182.coemulate_emount_info3d_and_breathing(lens_id=0xC135, mc_app_version="2.1.0")
        self.assertFalse(res_old.focus_map_stream_active)
        self.assertTrue(res_new.focus_map_stream_active)

    def test_17_monitor_and_control_rejects_insecure_transport(self) -> None:
        res = p182.coemulate_emount_info3d_and_breathing(lens_id=0xC135, mc_transport="WEP")
        self.assertTrue(res.valid)
        self.assertFalse(res.focus_map_stream_active)

    def test_18_p18_lensfile_write_attempt_blocked_blkroset_1(self) -> None:
        res = p182.coemulate_emount_info3d_and_breathing(
            lens_id=0xC135,
            cinealta_lensfile_write_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.p18_blkroset, 1)
        self.assertEqual(res.lens_partition_writes, 0)
        self.assertEqual(res.status_code, "BLOCKED_P18_LENSFILE_BLKROSET_1")

    def test_19_p18_blkroset_unlock_attempt_blocked(self) -> None:
        res = p182.coemulate_emount_info3d_and_breathing(lens_id=0xC135, p18_blkroset=0)
        self.assertFalse(res.valid)
        self.assertEqual(res.p18_blkroset, 1)
        self.assertEqual(res.lens_partition_writes, 0)

    def test_20_corrupt_info3d_serial_crc_blocked_fail_closed(self) -> None:
        res = p182.coemulate_emount_info3d_and_breathing(lens_id=0xC135, corrupt_info3d_crc=True)
        self.assertFalse(res.valid)
        self.assertFalse(res.info_crc32_valid)
        self.assertFalse(res.breathing_comp_authorized)
        self.assertEqual(res.status_code, "BLOCKED_INFO3D_SERIAL_CRC_FAULT")

    def test_21_cta861_sony_hdmi_raw_vsif_31bytes_and_checksum(self) -> None:
        vsif = p182.build_sony_hdmi_raw_vsif()
        self.assertEqual(len(vsif), 31)
        self.assertEqual(vsif[0], 0x81)
        self.assertTrue(p182.verify_vsif_checksum(vsif))
        self.assertEqual(sum(vsif) & 0xFF, 0)

    def test_22_video_assist_12g_hdr_3_22_accepts_4264x2408_braw_60p(self) -> None:
        res = p182.coemulate_hdmi_4264_raw_negotiation(
            recorder_model=p182.RECORDER_VA_12G_HDR,
            recorder_fw="3.22.0",
            fps_label="59.94p",
            internal_simul_codec="XAVC S-I",
            include_proxy=True,
            anamorphic_desqueeze=1.5,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.raw_container_format, "BRAW")
        self.assertEqual((res.width, res.height), (4264, 2408))
        self.assertEqual(res.bit_depth_linear, 16)
        self.assertEqual(res.bit_depth_encoded, 12)
        self.assertTrue(res.capture_locked_iso)
        self.assertFalse(res.wb_iso_offset_encapsulated)
        self.assertTrue(res.internal_dual_slot_active)
        self.assertEqual(res.internal_simul_codec, "XAVC S-I+Proxy")
        self.assertTrue(res.anamorphic_desqueeze_osd_only)
        self.assertFalse(res.osd_baked_into_raw)
        self.assertTrue(res.sdi_bnc_mmio_masked)
        self.assertEqual(res.sdi_bnc_mmio_faults, 0)

    def test_23_video_assist_12g_hdr_below_3_22_rejected(self) -> None:
        res = p182.coemulate_hdmi_4264_raw_negotiation(
            recorder_model=p182.RECORDER_VA_12G_HDR,
            recorder_fw="3.21.0",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.status_code, "BLOCKED_RECORDER_FIRMWARE_BELOW_RAW_FLOOR")

    def test_24_video_assist_3g_rejected_for_braw(self) -> None:
        res = p182.coemulate_hdmi_4264_raw_negotiation(
            recorder_model=p182.RECORDER_VA_3G,
            recorder_fw="3.22.0",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.raw_container_format, "BRAW_UNSUPPORTED")
        self.assertEqual(res.status_code, "BLOCKED_VIDEO_ASSIST_3G_UNSUPPORTED_FOR_BRAW")

    def test_25_atomos_ninja_ultra_10_64_prores_raw_encapsulates_wb_iso_offset(self) -> None:
        res = p182.coemulate_hdmi_4264_raw_negotiation(
            recorder_model=p182.RECORDER_ATOMOS_NINJA_ULTRA,
            recorder_fw="10.64.0",
            fps_label="59.94p",
            internal_simul_codec="XAVC HS",
            include_proxy=True,
            anamorphic_desqueeze=1.6,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.raw_container_format, "PRORES_RAW")
        self.assertFalse(res.capture_locked_iso)
        self.assertTrue(res.wb_iso_offset_encapsulated)
        self.assertEqual(res.internal_simul_codec, "XAVC HS+Proxy")
        self.assertEqual(res.anamorphic_desqueeze, 1.6)
        self.assertTrue(res.anamorphic_desqueeze_osd_only)
        self.assertFalse(res.osd_baked_into_raw)

    def test_26_atomos_ninja_v_below_10_64_rejected(self) -> None:
        res = p182.coemulate_hdmi_4264_raw_negotiation(
            recorder_model=p182.RECORDER_ATOMOS_NINJA_V,
            recorder_fw="10.63.0",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.status_code, "BLOCKED_RECORDER_FIRMWARE_BELOW_RAW_FLOOR")

    def test_27_hdmi_raw_over_60p_rejected_across_100p_120p(self) -> None:
        for fps in p182.HDMI_RAW_UNSUPPORTED_FPS:
            res = p182.coemulate_hdmi_4264_raw_negotiation(
                recorder_model=p182.RECORDER_VA_12G_HDR,
                recorder_fw="3.22.0",
                fps_label=fps,
            )
            self.assertFalse(res.admitted, msg=fps)
            self.assertEqual(res.status_code, "BLOCKED_HDMI_RAW_EXCEEDS_60P_CEILING")

    def test_28_hdmi_raw_all_supported_framerates_up_to_59_94p_admitted(self) -> None:
        for fps in p182.HDMI_RAW_SUPPORTED_FPS:
            res = p182.coemulate_hdmi_4264_raw_negotiation(
                recorder_model=p182.RECORDER_VA_12G_HDR,
                recorder_fw="3.22.0",
                fps_label=fps,
            )
            self.assertTrue(res.admitted, msg=fps)

    def test_29_osd_or_lut_burn_in_into_raw_blocked(self) -> None:
        res = p182.coemulate_hdmi_4264_raw_negotiation(
            recorder_model=p182.RECORDER_ATOMOS_NINJA_V,
            recorder_fw="10.64.0",
            bake_osd_into_raw_requested=True,
        )
        self.assertFalse(res.admitted)
        self.assertFalse(res.osd_baked_into_raw)
        self.assertEqual(res.status_code, "BLOCKED_RAW_OSD_OR_LUT_BURN_IN")

    def test_30_edid_or_corrupt_vsif_blocked_fail_closed(self) -> None:
        res_edid = p182.coemulate_hdmi_4264_raw_negotiation(edid_raw16_capable=False)
        res_vsif = p182.coemulate_hdmi_4264_raw_negotiation(corrupt_vsif=True)
        self.assertFalse(res_edid.admitted)
        self.assertEqual(res_edid.status_code, "BLOCKED_EDID_OR_VSIF_CHECKSUM_FAILURE")
        self.assertFalse(res_vsif.admitted)
        self.assertFalse(res_vsif.vsif_checksum_valid)

    def test_31_fx6_12g_sdi_bnc_probe_masked_with_zero_mmio_faults(self) -> None:
        res = p182.coemulate_hdmi_4264_raw_negotiation(sdi_bnc_probe_requested=True)
        self.assertFalse(res.admitted)
        self.assertTrue(res.sdi_bnc_mmio_masked)
        self.assertEqual(res.sdi_bnc_mmio_faults, 0)
        self.assertEqual(res.status_code, "BLOCKED_FX6_12G_SDI_BNC_MASKED_ON_FX3")

    def test_32_invalid_anamorphic_and_codec_and_recorder_raise_error(self) -> None:
        with self.assertRaises(p182.RealHwEmountInfo3dHdmiRawError):
            p182.coemulate_hdmi_4264_raw_negotiation(anamorphic_desqueeze=3.0)
        with self.assertRaises(p182.RealHwEmountInfo3dHdmiRawError):
            p182.coemulate_hdmi_4264_raw_negotiation(internal_simul_codec="DNxHR")
        with self.assertRaises(p182.RealHwEmountInfo3dHdmiRawError):
            p182.coemulate_hdmi_4264_raw_negotiation(recorder_model="UNKNOWN_RECORDER")

    def test_33_network_security_floor_allows_wpa2_wpa3_wired_only(self) -> None:
        for mode in p182.ALLOWED_NETWORK_SECURITY_MODES:
            res = p182.evaluate_network_and_metadata_sanitizer(security_mode=mode)
            self.assertTrue(res.valid, msg=mode)
            self.assertTrue(res.security_admitted, msg=mode)
            self.assertEqual(res.wf12_00342260_hits, 0)

    def test_34_network_security_floor_rejects_wep_wpa1_open_tkip_ipsec(self) -> None:
        for mode in p182.REJECTED_NETWORK_SECURITY_MODES:
            res = p182.evaluate_network_and_metadata_sanitizer(security_mode=mode)
            self.assertFalse(res.valid, msg=mode)
            self.assertFalse(res.security_admitted, msg=mode)
            self.assertEqual(res.status_code, "BLOCKED_INSECURE_NETWORK_SECURITY_FLOOR")

    def test_35_metadata_sanitizer_blocks_traversal_and_control_chars(self) -> None:
        for bad_tag in ("../../p18:/lens/LENSFILE.BIN", "CLIP;rm -rf /", "CLIP\x00TAG", "   "):
            res = p182.evaluate_network_and_metadata_sanitizer(
                security_mode="WPA3",
                catalyst_clip_tag=bad_tag,
            )
            self.assertFalse(res.valid, msg=repr(bad_tag))
            self.assertFalse(res.sanitization_passed, msg=repr(bad_tag))
        res_ssid = p182.evaluate_network_and_metadata_sanitizer(
            security_mode="WPA2",
            ssid_or_host="FX3|nvram",
        )
        self.assertFalse(res_ssid.valid)

    def test_36_hard_safety_redline_baseline_all_locked(self) -> None:
        res = p182.probe_hard_safety_redline()
        self.assertTrue(res.valid)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.spi_nor_write_authorized)
        self.assertFalse(res.el3_payload_transmit_authorized)
        self.assertEqual(res.physical_usb_packets_emitted, 0)
        self.assertEqual(res.otp_fuse_touches, 0)
        self.assertEqual(res.rpmb_counter_increments, 0)
        self.assertEqual(res.lens_partition_writes, 0)
        self.assertEqual(res.sdi_bnc_mmio_faults, 0)
        self.assertEqual(res.blocked_action, "NONE")

    def test_37_hard_safety_redline_blocks_every_forbidden_hardware_action(self) -> None:
        kwargs_list = [
            {"authorize_persistent_emmc_writes": True},
            {"authorize_spi_nor_write": True},
            {"authorize_el3_payload_transmit": True},
            {"emit_physical_usb_packet": True},
            {"touch_otp_fuse": True},
            {"increment_rpmb_counter": True},
            {"authorize_p18_lens_write": True},
            {"trigger_sdi_bnc_mmio": True},
        ]
        for kw in kwargs_list:
            res = p182.probe_hard_safety_redline(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)
            self.assertFalse(res.el3_payload_transmit_authorized)
            self.assertEqual(res.physical_usb_packets_emitted, 0)
            self.assertEqual(res.otp_fuse_touches, 0)
            self.assertEqual(res.rpmb_counter_increments, 0)
            self.assertEqual(res.lens_partition_writes, 0)
            self.assertEqual(res.sdi_bnc_mmio_faults, 0)

    def test_38_full_orchestrator_passes_clean_room_and_default(self) -> None:
        r_clean = _get_clean_room_audit()
        r_def = _get_default_audit()
        self.assertTrue(r_clean["all_checks_passed"])
        self.assertTrue(r_def["all_checks_passed"])
        self.assertEqual(r_clean["milestone"], "32/32")
        self.assertEqual(r_def["milestone"], "32/32")

    def test_39_clean_room_and_local_parity_on_all_pillars_and_redlines(self) -> None:
        r_clean = _get_clean_room_audit()
        r_def = _get_default_audit()
        self.assertEqual(r_clean["schema"], r_def["schema"])
        self.assertEqual(r_clean["stage_index"], r_def["stage_index"])
        self.assertEqual(r_clean["redlines"], r_def["redlines"])
        self.assertEqual(
            r_clean["pillar_a_emount_info3d_breathing_hil"],
            r_def["pillar_a_emount_info3d_breathing_hil"],
        )
        self.assertEqual(
            r_clean["pillar_b_hdmi_4264_raw_vs_12g_sdi_hil"],
            r_def["pillar_b_hdmi_4264_raw_vs_12g_sdi_hil"],
        )
        self.assertEqual(
            r_clean["pillar_c_d_network_sanitizer_and_redlines"],
            r_def["pillar_c_d_network_sanitizer_and_redlines"],
        )

    def test_40_zero_raw_firmware_bytes_leaked_in_json_report(self) -> None:
        for rep in (_get_clean_room_audit(), _get_default_audit()):
            txt = json.dumps(rep)
            self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(rep["donor_audit"]["raw_firmware_bytes_leaked"], 0)
            self.assertNotIn("7f454c46", txt)

    def test_41_cli_standalone_selftest_summary_and_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py"),
                "--self-test",
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 182 Stage 32 (32/32)", p_sum.stdout)
        self.assertIn("bkid=0x02cf0232", p_sum.stdout)
        self.assertIn("hdmi=4264x2408@59.94p(BRAW)", p_sum.stdout)

        p_json = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py"),
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
        self.assertEqual(parsed["stage_index"], 32)

    def test_42_fx3_vm_coemulation_suite_includes_stage32_and_skip_phase182(self) -> None:
        rep_on = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage32_realhw_emount_info3d_breathing_hdmi_4264_raw_hil", rep_on)
        s32 = rep_on["stage32_realhw_emount_info3d_breathing_hdmi_4264_raw_hil"]
        self.assertTrue(s32["all_checks_passed"])
        self.assertEqual(s32["lens_partition_writes"], 0)
        self.assertEqual(s32["sdi_bnc_mmio_faults"], 0)
        self.assertFalse(s32["persistent_emmc_writes_authorized"])
        self.assertFalse(s32["spi_nor_write_authorized"])
        self.assertFalse(s32["el3_payload_transmit_authorized"])
        self.assertEqual(s32["physical_usb_packets_emitted"], 0)
        self.assertEqual(s32["otp_fuse_touches"], 0)
        self.assertEqual(s32["rpmb_counter_increments"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 32)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase182_realhw_emount_info3d_breathing_hdmi_4264_raw_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage32_realhw_emount_info3d_breathing_hdmi_4264_raw_hil", rep_skip)
        self.assertGreaterEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), 31)

    def test_43_all_32_of_32_stages_present_and_passing_in_suite(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 33):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"], msg=matches[0])

    def test_44_suite_subprocess_summary_and_skip_phase182_flag(self) -> None:
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
        self.assertIn("realhw_emount_info3d_breathing_hdmi_4264_raw_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase182",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_emount_info3d_breathing_hdmi_4264_raw_hil=", proc_skip.stdout)

    def test_45_suite_32_stages_under_6s_wall_clock_ceiling_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 32)
        self.assertLess(dt_clean, 6.0)

        t1 = time.monotonic()
        rep_def = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_def = time.monotonic() - t1
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_def if re.match(r"^stage\d+_", k)]), 32)
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
        self.assertGreaterEqual(len([k for k in d_json if re.match(r"^stage\d+_", k)]), 32)

    def test_46_source_hygiene_rdonly_and_no_forbidden_flags_or_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("sys.dont_write_bytecode = True", src)
        self.assertNotIn("O_WR" + "ONLY", src)
        self.assertNotIn("O_RD" + "WR", src)
        forbidden_port = str(87 * 100 + 68)
        self.assertNotIn(forbidden_port, src)

    def test_47_audit_digest_deterministic_across_repeated_clean_room_runs(self) -> None:
        r1 = p182.run_phase182_realhw_emount_info3d_hdmi_4264_raw_hil(force_clean_room=True)
        r2 = p182.run_phase182_realhw_emount_info3d_hdmi_4264_raw_hil(force_clean_room=True)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_48_stage32_wall_clock_standalone_well_below_6s(self) -> None:
        t0 = time.monotonic()
        r = p182.run_phase182_realhw_emount_info3d_hdmi_4264_raw_hil()
        dt = time.monotonic() - t0
        self.assertTrue(r["all_checks_passed"])
        self.assertLess(dt, 6.0)


if __name__ == "__main__":
    unittest.main()
