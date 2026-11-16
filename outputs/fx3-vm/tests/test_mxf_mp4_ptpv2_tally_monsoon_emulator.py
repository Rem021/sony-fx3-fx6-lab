#!/usr/bin/env python3
"""Phase 127 Test Suite — Stage 22 XAVC MXF OP1a <-> MP4 RDD-18/UMID Essence &
Sidecar Bridge, SMPTE ST 2059-2 PTPv2 Sub-Microsecond vs LTC Phase Sync, Wired
P12-Safe TSL UMD v5.0 Studio Tally, and G39/G40 Monsoon MI-Shoe / Cage-Twist FFD HIL.

Exercises 40 fast unit, protocol, fail-closed guard, Stage 22 suite integration,
CLI, and source-hygiene tests across BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import mxf_mp4_ptpv2_tally_monsoon_emulator as p127  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p127.run_phase127_mxf_ptpv2_tally_monsoon_audit(
            force_clean_room=True
        )
    return _AUDIT_CACHE["clean_room"]


class TestPhase127DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_16_artifacts_and_sha256(self) -> None:
        audit = p127.inspect_phase127_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 38)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p127.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p127.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p127.is_forced_clean_room(env))
        paths = p127.resolve_phase127_donor_paths(env=env)
        self.assertEqual(len(paths), 16)
        for path in paths.values():
            self.assertIn(p127.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p127.inspect_phase127_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p127.is_forced_clean_room():
            audit = p127.inspect_phase127_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p127.resolve_phase127_donor_paths()
        audit = p127.inspect_phase127_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 16)
            for key, (expected_bytes, expected_sha) in p127.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p127.ENV_MAC_WORK_ROOT: "/nonexistent_phase127_mac_work_root",
            p127.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase127_main_work_root",
        }
        audit = p127.inspect_phase127_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_wf12_and_zero_damage(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["guest_code_modification_bytes"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["emmc_mutation_bytes"], 0)
        self.assertEqual(red["dropped_klv_tags"], 0)
        self.assertEqual(red["frame_essence_reencode_loss"], 0)
        self.assertEqual(red["wf12_00342260_hits"], 0)
        self.assertEqual(red["fx6_green_gpio_faults"], 0)
        self.assertEqual(red["mishoe_rail_corrosion_events"], 0)
        self.assertEqual(red["chassis_damage_events"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestPillarAMxfMp4Rdd18UmidBridge(unittest.TestCase):
    """Verify XAVC MXF OP1a <-> FX3 MP4 ISO-BMFF RDD-18/UMID/XML/.CUBE bridge."""

    def test_06_smpte330_umid_32byte_prefix_and_determinism(self) -> None:
        u1 = p127.build_smpte330_umid_hex()
        u2 = p127.build_smpte330_umid_hex()
        self.assertEqual(u1, u2)
        self.assertEqual(len(bytes.fromhex(u1)), 32)
        self.assertTrue(u1.startswith(p127.SMPTE_UMID_BASIC_PREFIX_HEX))

    def test_07_rdd18_rtmd_klv_roundtrip_all_tags_and_crc32(self) -> None:
        pkt = p127.encode_rdd18_rtmd_klv_packet(
            exposure_index=12800,
            base_iso=12800,
            gamma_name="S-LOG3",
            primaries_name="S-GAMUT3.CINE",
            fps_x1000=59940,
            f_number_x100=140,
            shutter_angle_x10=1800,
            wb_kelvin=3200,
            cube_lut_path="/tmp/fx3_stageb_lut/Custom_SLog3_33.CUBE",
        )
        dec = p127.decode_rdd18_rtmd_klv_packet(pkt)
        self.assertTrue(dec["valid"])
        self.assertTrue(dec["crc32_valid"])
        self.assertEqual(dec["exposure_index"], 12800)
        self.assertEqual(dec["base_iso"], 12800)
        self.assertEqual(dec["gamma_name"], "S-LOG3")
        self.assertEqual(dec["primaries_name"], "S-GAMUT3.CINE")
        self.assertEqual(dec["klv_tags_present"], len(p127.RDD18_KLV_TAG_NAMES))
        self.assertTrue(str(dec["cube_lut_path"]).endswith(".CUBE"))

    def test_08_rdd18_corrupt_crc_bad_length_and_bad_cube_rejected(self) -> None:
        pkt = p127.encode_rdd18_rtmd_klv_packet()
        bad_crc = bytearray.fromhex(pkt)
        bad_crc[20] ^= 0xFF
        r_crc = p127.decode_rdd18_rtmd_klv_packet(bad_crc.hex())
        self.assertFalse(r_crc["valid"])
        self.assertIn("BLOCKED_RDD18_CRC_MISMATCH", r_crc["violation_codes"])

        r_len = p127.decode_rdd18_rtmd_klv_packet(pkt[:-8])
        self.assertFalse(r_len["valid"])
        self.assertEqual(r_len["violation_code"], "BLOCKED_RDD18_BAD_LENGTH")

        bad_lut = p127.encode_rdd18_rtmd_klv_packet(cube_lut_path="/tmp/not_a_lut.txt")
        r_lut = p127.decode_rdd18_rtmd_klv_packet(bad_lut)
        self.assertFalse(r_lut["valid"])
        self.assertIn("BLOCKED_RDD18_INVALID_CUBE_LUT_PATH", r_lut["violation_codes"])

    def test_09_bidirectional_mxf_to_mp4_and_mp4_to_mxf_lossless_rewrap(self) -> None:
        r1 = p127.bridge_mxf_mp4_essence_and_sidecar(
            source_container="MXF_OP1A",
            target_container="MP4_ISOBMFF",
            source_codec="XAVC_I_H422IP",
            target_codec="XAVC_S_I_H422IP",
            bridge_mode="LOSSLESS_REWRAP",
        )
        self.assertTrue(r1.passed)
        self.assertTrue(r1.umid_preserved)
        self.assertTrue(r1.essence_sha256_preserved)
        self.assertEqual(r1.dropped_klv_tags, 0)
        self.assertEqual(r1.frame_essence_reencode_loss, 0)

        r2 = p127.bridge_mxf_mp4_essence_and_sidecar(
            source_container="MP4_ISOBMFF",
            target_container="MXF_OP1A",
            source_codec="XAVC_S_I_H422IP",
            target_codec="XAVC_I_H422IP",
            bridge_mode="LOSSLESS_REWRAP",
            source_umid_hex=r1.target_umid_hex,
        )
        self.assertTrue(r2.passed)
        self.assertEqual(r2.target_umid_hex, r1.source_umid_hex)
        self.assertTrue(r2.essence_sha256_preserved)
        self.assertEqual(r2.dropped_klv_tags, 0)
        self.assertEqual(r2.frame_essence_reencode_loss, 0)

    def test_10_xml_nonrealtimemeta_sidecar_valid_and_contains_umid_gamma_lut(self) -> None:
        umid = p127.build_smpte330_umid_hex()
        xml_txt = p127.build_non_realtime_meta_xml(
            umid_hex=umid,
            exposure_index=800,
            base_iso=800,
            gamma_name="S-LOG3-CINE",
            primaries_name="S-GAMUT3.CINE",
            codec="XAVC_S_I_H422IP",
            cube_lut_path="/tmp/fx3_stageb_lut/S709_33.cube",
        )
        root = ET.fromstring(xml_txt)
        self.assertTrue(root.tag.endswith("NonRealTimeMeta"))
        self.assertIn(umid, xml_txt)
        self.assertIn("S-LOG3-CINE", xml_txt)
        self.assertIn("S709_33.cube", xml_txt)

    def test_11_transcode_regenerates_umid_while_raw_mxf_and_spvc_spoof_blocked(self) -> None:
        tr = p127.bridge_mxf_mp4_essence_and_sidecar(
            source_codec="XAVC_I_H422IP",
            target_codec="XAVC_HS_HEVC",
            bridge_mode="TRANSCODE",
        )
        self.assertTrue(tr.passed)
        self.assertFalse(tr.umid_preserved)

        raw = p127.bridge_mxf_mp4_essence_and_sidecar(
            source_container="MXF_OP1A",
            target_container="MP4_ISOBMFF",
            source_codec="XAVC_I_H422IP",
            target_codec="XAVC_I_H422IP",
            bridge_mode="DIRECT_RAW_COPY",
        )
        self.assertFalse(raw.passed)
        self.assertIn("BLOCKED_RAW_MXF_OP1A_ON_MP4_SLOT", raw.violation_codes)

        spoof = p127.bridge_mxf_mp4_essence_and_sidecar(spoof_spvc_cert=True)
        self.assertFalse(spoof.passed)
        self.assertIn("BLOCKED_SPVC_CERT_SPOOFING", spoof.violation_codes)

    def test_12_klv_drop_and_reencode_loss_faults_and_cross_codec_rewrap_blocked(self) -> None:
        drop_fault = p127.bridge_mxf_mp4_essence_and_sidecar(inject_dropped_klv_tags=1)
        self.assertFalse(drop_fault.passed)
        self.assertIn("BLOCKED_RDD18_KLV_TAG_DROP", drop_fault.violation_codes)

        loss_fault = p127.bridge_mxf_mp4_essence_and_sidecar(inject_essence_reencode_loss=2)
        self.assertFalse(loss_fault.passed)
        self.assertIn("BLOCKED_FRAME_ESSENCE_REENCODE_LOSS", loss_fault.violation_codes)

        cross = p127.bridge_mxf_mp4_essence_and_sidecar(
            source_codec="XAVC_I_H422IP",
            target_codec="XAVC_HS_HEVC",
            bridge_mode="LOSSLESS_REWRAP",
        )
        self.assertFalse(cross.passed)
        self.assertIn("BLOCKED_CROSS_CODEC_REWRAP_REQUIRES_TRANSCODE", cross.violation_codes)


class TestPillarBPtpv2LtcPhaseSync(unittest.TestCase):
    """Verify SMPTE ST 2059-2 PTPv2 (<0.5us RMS) & 8h LTC (<0.05 frame slip) servo."""

    def test_13_hw_and_sw_st2059_ptpv2_servo_sub_0p5us_rms_wired_p12_safe(self) -> None:
        hw = p127.simulate_st2059_ptpv2_ltc_servo(
            sync_profile="SMPTE_ST_2059_2_HW_TS",
            transport_driver="CDC_NCM_RTL8153",
            ptpv2_rms_offset_us=0.184,
        )
        self.assertTrue(hw.passed)
        self.assertTrue(hw.ptpv2_locked)
        self.assertLess(hw.ptpv2_rms_offset_us, p127.PTPV2_MAX_RMS_OFFSET_US)
        self.assertEqual(hw.messages_exchanged, ("Announce", "Sync", "Follow_Up", "Delay_Req", "Delay_Resp"))
        self.assertEqual(hw.wf12_00342260_hits, 0)

        sw = p127.simulate_st2059_ptpv2_ltc_servo(
            sync_profile="SMPTE_ST_2059_2_SW_TS",
            transport_driver="CDC_NCM_AX88179",
            ptpv2_rms_offset_us=0.342,
            fps_key="29.970_DF",
        )
        self.assertTrue(sw.passed)
        self.assertLess(sw.ptpv2_rms_offset_us, p127.PTPV2_MAX_RMS_OFFSET_US)
        self.assertIn(";", sw.smpte12m_timecode)

    def test_14_ltc_multi_terminal_8h_fallback_holdover_under_0p05_frame_slip(self) -> None:
        hold = p127.simulate_st2059_ptpv2_ltc_servo(
            ptpv2_link_lost=True,
            ltc_multi_terminal_attached=True,
            holdover_hours=8.0,
            tcxo_drift_ppm=0.025,
            fps_key="23.976_NDF",
        )
        self.assertTrue(hold.passed)
        self.assertTrue(hold.ptpv2_link_lost_fallback_active)
        self.assertTrue(hold.glitch_free_switchover)
        self.assertEqual(hold.dropped_frames, 0)
        self.assertLess(hold.holdover_phase_slip_frames, p127.LTC_MAX_8H_HOLDOVER_SLIP_FRAMES)

    def test_15_ptp_rms_ge_0p5us_and_8h_ltc_slip_ge_0p05_frames_blocked(self) -> None:
        bad_rms = p127.simulate_st2059_ptpv2_ltc_servo(ptpv2_rms_offset_us=0.55)
        self.assertFalse(bad_rms.passed)
        self.assertIn("BLOCKED_PTPV2_RMS_OFFSET_EXCEEDED", bad_rms.violation_codes)

        bad_slip = p127.simulate_st2059_ptpv2_ltc_servo(
            ptpv2_link_lost=True,
            holdover_hours=8.0,
            tcxo_drift_ppm=0.25,
        )
        self.assertFalse(bad_slip.passed)
        self.assertGreaterEqual(bad_slip.holdover_phase_slip_frames, p127.LTC_MAX_8H_HOLDOVER_SLIP_FRAMES)
        self.assertIn("BLOCKED_LTC_HOLDOVER_PHASE_SLIP_EXCEEDED", bad_slip.violation_codes)

    def test_16_ptpip_confusion_wifi_rf_and_uart_boot_bnc_blocked(self) -> None:
        ptpip = p127.simulate_st2059_ptpv2_ltc_servo(sync_profile="PTP_IP_15740_CONTROL")
        self.assertFalse(ptpip.passed)
        self.assertIn("BLOCKED_PTPIP_NOT_ST2059_PTPV2", ptpip.violation_codes)

        for rf in ("WIFI_WLAN0", "BT_PAN", "WIFI_DIRECT_P2P"):
            r = p127.simulate_st2059_ptpv2_ltc_servo(transport_driver=rf)
            self.assertFalse(r.passed)
            self.assertIn("BLOCKED_P12_RF_OFF_VIOLATION_00342260", r.violation_codes)
            self.assertEqual(r.wf12_00342260_hits, 0)

        uart = p127.simulate_st2059_ptpv2_ltc_servo(uart_boot_active=True, ltc_multi_terminal_attached=True)
        self.assertFalse(uart.passed)
        self.assertIn("BLOCKED_VMC_BNCM1_DURING_UART_BOOT", uart.violation_codes)

    def test_17_tai_ns_to_smpte12m_tc_drop_frame_and_ndf_parity(self) -> None:
        tc_ndf = p127.convert_tai_ns_to_smpte12m_tc(1_794_715_237_500_000_000, "23.976_NDF")
        tc_df = p127.convert_tai_ns_to_smpte12m_tc(1_794_715_237_500_000_000, "59.940_DF")
        self.assertRegex(tc_ndf, r"^\d{2}:\d{2}:\d{2}:\d{2}$")
        self.assertRegex(tc_df, r"^\d{2}:\d{2}:\d{2};\d{2}$")


class TestPillarCTslUmdV5TallyBridge(unittest.TestCase):
    """Verify wired P12-safe TSL UMD v5.0 PGM/PVW Tally, 16-char label & Stealth OFF."""

    def test_18_tsl_umd_v5_udp_and_tcp_dle_stx_roundtrip_with_0xfe_escaping(self) -> None:
        pkt_udp = p127.encode_tsl_umd_v5_packet(screen=1, index=2, lh_tally=1, text="FX3-PGM-A")
        dec_udp = p127.decode_tsl_umd_v5_packet(pkt_udp, tcp_dle_stx_framing=False)
        self.assertTrue(dec_udp["valid"])
        self.assertEqual(dec_udp["tally_name"], "RED")
        self.assertEqual(dec_udp["text"], "FX3-PGM-A")

        pkt_tcp = p127.encode_tsl_umd_v5_packet(
            screen=0x00FE,
            index=0x00FE,
            lh_tally=2,
            text="FX3-PVW-B",
            use_utf16le=True,
            tcp_dle_stx_framing=True,
        )
        self.assertTrue(pkt_tcp.startswith("fe02"))
        dec_tcp = p127.decode_tsl_umd_v5_packet(pkt_tcp, tcp_dle_stx_framing=True)
        self.assertTrue(dec_tcp["valid"])
        self.assertEqual(dec_tcp["screen"], 0x00FE)
        self.assertEqual(dec_tcp["index"], 0x00FE)
        self.assertEqual(dec_tcp["tally_name"], "GREEN")
        self.assertEqual(dec_tcp["text"], "FX3-PVW-B")

    def test_19_pgm_red_drives_front_top_rear_leds_and_16char_label(self) -> None:
        res = p127.bridge_tsl_umd_v5_tally(
            transport_driver="CDC_NCM_RTL8153",
            lh_tally=1,
            text="FX3-MAIN-PGM-CAM01-OVERFLOW",
            stealth_tally_off_override=False,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.fx3_front_led_on)
        self.assertTrue(res.fx3_top_led_on)
        self.assertTrue(res.fx3_rear_led_on)
        self.assertEqual(res.osd_tally_border_color, "RED")
        self.assertEqual(res.sanitized_16char_label, "FX3-MAIN-PGM-CAM")
        self.assertEqual(len(res.sanitized_16char_label), 16)
        self.assertEqual(res.wf12_00342260_hits, 0)

    def test_20_pvw_green_keeps_red_leds_off_with_green_osd_and_zero_fx6_gpio_fault(self) -> None:
        res = p127.bridge_tsl_umd_v5_tally(
            transport_driver="CDC_NCM_AX88179",
            lh_tally=2,
            text="FX3-PVW-CAM2",
            stealth_tally_off_override=False,
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.fx3_front_led_on)
        self.assertFalse(res.fx3_top_led_on)
        self.assertFalse(res.fx3_rear_led_on)
        self.assertEqual(res.osd_tally_border_color, "GREEN")
        self.assertEqual(res.fx6_green_gpio_faults, 0)

    def test_21_stealth_off_override_suppresses_all_tally_leds_even_on_pgm_red(self) -> None:
        res = p127.bridge_tsl_umd_v5_tally(
            transport_driver="CDC_NCM_RTL8153",
            lh_tally=1,
            text="\x1b[31mSTEALTH-CAM\x1b[0m",
            stealth_tally_off_override=True,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.stealth_tally_off_override)
        self.assertFalse(res.fx3_front_led_on)
        self.assertFalse(res.fx3_top_led_on)
        self.assertFalse(res.fx3_rear_led_on)
        self.assertEqual(res.osd_tally_border_color, "NONE_STEALTH_OFF")
        self.assertEqual(res.sanitized_16char_label, "STEALTH-CAM")

    def test_22_utf8_label_clamp_and_p12_wifi_off_and_udp_oversize_blocked(self) -> None:
        utf8 = p127.bridge_tsl_umd_v5_tally(
            transport_driver="USB_RNDIS_WIRED",
            lh_tally=3,
            text="机位A-主摄FX3-TALLY-TEST",
        )
        self.assertTrue(utf8.passed)
        self.assertLessEqual(len(utf8.sanitized_16char_label), 16)
        self.assertEqual(utf8.osd_tally_border_color, "AMBER")

        wifi = p127.bridge_tsl_umd_v5_tally(transport_driver="WIFI_WLAN0", lh_tally=1)
        self.assertFalse(wifi.passed)
        self.assertIn("BLOCKED_P12_RF_OFF_VIOLATION_00342260", wifi.violation_codes)
        self.assertEqual(wifi.wf12_00342260_hits, 0)

        oversize = p127.encode_tsl_umd_v5_packet(text="X" * 2060)
        dec_over = p127.decode_tsl_umd_v5_packet(oversize)
        self.assertFalse(dec_over["valid"])
        self.assertEqual(dec_over["violation_code"], "BLOCKED_TSL_UDP_OVER_2048_BYTES")


class TestPillarDG39G40MonsoonCageTwistHil(unittest.TestCase):
    """Verify G39 Monsoon wet 24-pin MI-Shoe & G40 XLR-H1 / Cage-Twist FFD HIL."""

    def test_23_g39_dry_or_gasketed_monsoon_passes_with_zero_corrosion(self) -> None:
        safe = p127.simulate_g39_monsoon_mishoe_hil(
            precipitation_mm_hr=25.0,
            mi_shoe_contact_resistance_kohm=950.0,
            mi_shoe_accessory_attached=True,
            mi_shoe_silicone_gasket_sealed=True,
            open_side_port_flaps_count=0,
        )
        self.assertTrue(safe.passed)
        self.assertFalse(safe.load_switch_tripped)
        self.assertEqual(safe.mishoe_rail_corrosion_events, 0)
        self.assertEqual(safe.chassis_damage_events, 0)

    def test_24_g39_wet_mishoe_under_50kohm_trips_under_25us_isolating_3v15_and_5v(self) -> None:
        wet = p127.simulate_g39_monsoon_mishoe_hil(
            precipitation_mm_hr=35.0,
            mi_shoe_contact_resistance_kohm=12.5,
            mi_shoe_accessory_attached=False,
            mi_shoe_weather_cap_installed=False,
        )
        self.assertFalse(wet.passed)
        self.assertIn("BLOCKED_G39_WET_MISHOE_GALVANIC_SHORT_TRIPPED", wet.violation_codes)
        self.assertTrue(wet.load_switch_tripped)
        self.assertGreater(wet.load_switch_trip_us, 0.0)
        self.assertLess(wet.load_switch_trip_us, p127.G39_LOAD_SWITCH_MAX_TRIP_US)
        self.assertTrue(wet.rail_3v15_isolated)
        self.assertTrue(wet.rail_5v0_isolated)
        self.assertEqual(wet.mishoe_rail_corrosion_events, 0)
        self.assertEqual(wet.chassis_damage_events, 0)

    def test_25_g39_open_side_flap_and_nongasketed_accessory_blocked(self) -> None:
        flap = p127.simulate_g39_monsoon_mishoe_hil(
            precipitation_mm_hr=10.0,
            mi_shoe_contact_resistance_kohm=800.0,
            mi_shoe_accessory_attached=False,
            mi_shoe_weather_cap_installed=True,
            open_side_port_flaps_count=1,
            weather_sealed_gland_or_slicker=False,
        )
        self.assertFalse(flap.passed)
        self.assertIn("BLOCKED_G39_OPEN_PORT_FLAP_CAPILLARY_INGRESS", flap.violation_codes)

        acc = p127.simulate_g39_monsoon_mishoe_hil(
            precipitation_mm_hr=5.0,
            mi_shoe_contact_resistance_kohm=500.0,
            mi_shoe_accessory_attached=True,
            mi_shoe_silicone_gasket_sealed=False,
            rain_cover_installed=False,
        )
        self.assertFalse(acc.passed)
        self.assertIn("BLOCKED_G39_NONGASKETED_MISHOE_IN_MONSOON", acc.violation_codes)

    def test_26_g40_nominal_shimmed_and_nato_reinforced_heavy_pass(self) -> None:
        nom = p127.simulate_g40_xlrh1_cagetwist_ffd_hil(
            xlr_h1_installed=True,
            xlr_h1_suspended_mass_kg=1.85,
            xlr_h1_moment_nm=2.1,
            quarter20_torque_nm=2.4,
            cage_multi_point_locked=True,
            unshimmed_side_gap_mm=0.05,
        )
        self.assertTrue(nom.passed)
        self.assertEqual(nom.emount_nominal_ffd_mm, 18.00)
        self.assertLessEqual(nom.estimated_ffd_tilt_um, p127.G40_EMOUNT_FFD_TILT_MAX_UM)
        self.assertEqual(nom.chassis_damage_events, 0)

        nato = p127.simulate_g40_xlrh1_cagetwist_ffd_hil(
            xlr_h1_installed=True,
            xlr_h1_suspended_mass_kg=3.6,
            xlr_h1_moment_nm=3.9,
            nato_cage_reinforcement=True,
            quarter20_torque_nm=2.8,
            unshimmed_side_gap_mm=0.08,
        )
        self.assertTrue(nato.passed)
        self.assertFalse(nato.xlr_h1_whip_shear_warning)

    def test_27_g40_xlrh1_gt_2p8kg_whip_shear_warning_and_quarter20_strip_blocked(self) -> None:
        whip = p127.simulate_g40_xlrh1_cagetwist_ffd_hil(
            xlr_h1_installed=True,
            xlr_h1_suspended_mass_kg=3.4,
            xlr_h1_moment_nm=3.5,
            nato_cage_reinforcement=False,
        )
        self.assertFalse(whip.passed)
        self.assertTrue(whip.xlr_h1_whip_shear_warning)
        self.assertIn("BLOCKED_G40_XLR_H1_WHIP_SHEAR_WARNING", whip.violation_codes)
        self.assertEqual(whip.chassis_damage_events, 0)

        strip = p127.simulate_g40_xlrh1_cagetwist_ffd_hil(quarter20_torque_nm=4.6)
        self.assertFalse(strip.passed)
        self.assertIn("BLOCKED_G40_QUARTER20_THREAD_STRIP", strip.violation_codes)

    def test_28_g40_asymmetric_cagetwist_gt_12um_ffd_warpage_interlock(self) -> None:
        twist = p127.simulate_g40_xlrh1_cagetwist_ffd_hil(
            xlr_h1_installed=True,
            xlr_h1_suspended_mass_kg=1.5,
            quarter20_torque_nm=2.5,
            cage_multi_point_locked=True,
            unshimmed_side_gap_mm=0.35,
        )
        self.assertFalse(twist.passed)
        self.assertTrue(twist.ffd_warpage_interlock_tripped)
        self.assertGreater(twist.estimated_ffd_tilt_um, p127.G40_EMOUNT_FFD_TILT_MAX_UM)
        self.assertIn("BLOCKED_G40_CAGE_TWIST_FFD_WARPAGE_INTERLOCK", twist.violation_codes)
        self.assertEqual(twist.chassis_damage_events, 0)

    def test_29_g39_g40_negative_telemetry_raises_error(self) -> None:
        with self.assertRaises(p127.MxfPtpv2TallyMonsoonError):
            p127.simulate_g39_monsoon_mishoe_hil(mi_shoe_contact_resistance_kohm=-5.0)
        with self.assertRaises(p127.MxfPtpv2TallyMonsoonError):
            p127.simulate_g40_xlrh1_cagetwist_ffd_hil(xlr_h1_suspended_mass_kg=-0.5)


class TestStage22SuiteIntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 22 suite integration, CLI flags, runtime budgets & strict hygiene."""

    def test_30_pillar_a_b_c_d_evaluators_all_pass_independently(self) -> None:
        self.assertTrue(p127.evaluate_pillar_a_mxf_mp4_bridge()["passed"])
        self.assertTrue(p127.evaluate_pillar_b_ptpv2_ltc_servo()["passed"])
        self.assertTrue(p127.evaluate_pillar_c_tsl_umd_tally()["passed"])
        self.assertTrue(p127.evaluate_pillar_d_g39_g40_hil()["passed"])

    def test_31_clean_room_audit_digest_reproducible_and_no_bytes_repr(self) -> None:
        rep1 = p127.run_phase127_mxf_ptpv2_tally_monsoon_audit(force_clean_room=True)
        rep2 = p127.run_phase127_mxf_ptpv2_tally_monsoon_audit(force_clean_room=True)
        self.assertTrue(rep1["all_checks_passed"])
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_32_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--mxf-matrix"],
            ["--clean-room", "--ptpv2-matrix"],
            ["--clean-room", "--tally-matrix"],
            ["--clean-room", "--hil-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p127.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_33_standalone_json_cli_matches_run_audit(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p127.main(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], p127.PHASE_127_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])

    def test_34_suite_in_process_stage22_ge22_stages_and_skip_phase127_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage22_mxf_ptpv2_tally_monsoon_hil", rep_on)
        self.assertTrue(rep_on["stage22_mxf_ptpv2_tally_monsoon_hil"]["all_checks_passed"])

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 22)

        cfg_skip = suite.CoEmulationConfig(
            force_clean_room=True,
            include_phase127_mxf_ptpv2_tally_monsoon_hil=False,
        )
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage22_mxf_ptpv2_tally_monsoon_hil", rep_skip)

    def test_35_suite_subprocess_summary_and_skip_phase127_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
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
        self.assertIn("mxf_ptpv2_tally_monsoon=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase127",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("mxf_ptpv2_tally_monsoon=", proc_skip.stdout)

    def test_36_22_stage_suite_clean_room_and_local_runtime_under_budget(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        elapsed_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertLess(elapsed_clean, 0.70)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        elapsed_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertLess(elapsed_mode, 1.80)

    def test_37_invalid_bridge_and_ptp_inputs_raise_domain_error(self) -> None:
        with self.assertRaises(p127.MxfPtpv2TallyMonsoonError):
            p127.bridge_mxf_mp4_essence_and_sidecar(source_container="AVI_BAD")
        with self.assertRaises(p127.MxfPtpv2TallyMonsoonError):
            p127.bridge_mxf_mp4_essence_and_sidecar(bridge_mode="MAGIC_REWRAP")
        with self.assertRaises(p127.MxfPtpv2TallyMonsoonError):
            p127.simulate_st2059_ptpv2_ltc_servo(sync_profile="NTP_BAD")
        with self.assertRaises(p127.MxfPtpv2TallyMonsoonError):
            p127.convert_tai_ns_to_smpte12m_tc(1000, "120.000_BAD")

    def test_38_stages_1_to_21_remain_intact_in_22_stage_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 23):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"])

    def test_39_tsl_bad_hex_and_bad_tcp_framing_rejected_gracefully(self) -> None:
        bad_hex = p127.decode_tsl_umd_v5_packet("zzzz")
        self.assertFalse(bad_hex["valid"])
        self.assertEqual(bad_hex["violation_code"], "BLOCKED_TSL_INVALID_HEX")

        bad_tcp = p127.decode_tsl_umd_v5_packet("00112233", tcp_dle_stx_framing=True)
        self.assertFalse(bad_tcp["valid"])
        self.assertEqual(bad_tcp["violation_code"], "BLOCKED_TSL_TCP_BAD_DLE_STX")

    def test_40_source_hygiene_o_rdonly_and_no_write_flags_or_port_8768_or_raw_bytes(self) -> None:
        src = (FX3_VM_DIR / "mxf_mp4_ptpv2_tally_monsoon_emulator.py").read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))


if __name__ == "__main__":
    unittest.main()
