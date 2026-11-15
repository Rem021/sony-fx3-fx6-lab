"""Phase 122 Dual-Mode Unit Tests: XAVC MXF OP1a (FX6) vs MP4 ISO-BMFF (FX3)
Container Essence / SMPTE UMID / KLV RDD-18 Metadata Translator,
SMPTE ST 2059-2 PTPv2 Frame-Phase Sync, & Wired P12-Safe TSL UMD v5.0 Tally Bridge.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import struct
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.emount_af_breathing_and_ibis_auditor import _extract_uxc_labels
from fx3_firmware_lab.global_xdb_and_menu_tree_auditor import parse_global_xdb_buffer
from fx3_firmware_lab.mxf_mp4_essence_ptpv2_and_tally_umd_auditor import (
    CAPTURE_GAMMA_UL_MAP,
    FORBIDDEN_RF_SYNC_TRANSPORTS,
    FX3_APPFW_PHASE122_MARKERS,
    FX3_LIBMPR_PHASE122_MARKERS,
    FX3_NS39_PHASE122_LABELS,
    FX3_NS3_PHASE122_LABELS,
    FX6_APPFW_PHASE122_MARKERS,
    FX6_LIBINFRA_PTP_PHASE122_MARKERS,
    FX6_LIBMPR_PHASE122_MARKERS,
    FX6_LIBNET_ETHER_PHASE122_MARKERS,
    FX6_NS1_PHASE122_LABELS,
    FX6_NS2_PHASE122_LABELS,
    LTC_MAX_PHASE_OFFSET_US,
    PHASE_122_SCHEMA,
    PHASE_122_VERSION,
    PTPV2_FPS_SPECS,
    PTPV2_MAX_HW_JITTER_US,
    PTPV2_MAX_SW_JITTER_US,
    PTP_TAI_UTC_OFFSET_SEC,
    RDD18_KLV_PACKET_MAGIC,
    SMPTE_ST2059_DEFAULT_DOMAIN,
    SMPTE_UMID_BASIC_PREFIX_HEX,
    SMPTE_UMID_BYTES,
    TSL_TALLY_COLOR_NAMES,
    TSL_UMD_DLE,
    TSL_UMD_MAX_LABEL_CHARS,
    TSL_UMD_PORTS,
    TSL_UMD_STX,
    TSL_UMD_UDP_MAX_BYTES,
    VALID_CAPTURE_PRIMARIES_P122,
    WIRED_SYNC_TRANSPORTS,
    analyze_mxf_mp4_essence_ptpv2_and_tally_umd,
    build_clean_room_mxf_mp4_ptpv2_tally_fixtures,
    build_rdd18_rtmd_klv_frame,
    build_smpte_umid,
    build_tsl_umd_v5_packet,
    decode_rdd18_rtmd_klv_frame,
    evaluate_mxf_mp4_essence_bridge,
    evaluate_phase122_write_guard,
    evaluate_pillar_a_mxf_mp4_essence_bridge,
    evaluate_pillar_b_ptpv2_ltc_phase_sync,
    evaluate_pillar_c_tsl_umd_tally_bridge,
    evaluate_pillar_d_zero_mutation_emmc_guard,
    evaluate_ptpv2_ltc_phase_sync,
    evaluate_tsl_umd_tally_translation,
    mxf_mp4_essence_ptpv2_and_tally_umd_report_to_dict,
    parse_tsl_umd_v5_packet,
    ptpv2_tai_to_smpte12m_tc,
    sanitize_umd_label_16,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "mxf_mp4_essence_ptpv2_and_tally_umd_auditor.py"
)


class TestMxfMp4EssencePtpv2AndTallyUmd(unittest.TestCase):
    """Comprehensive dual-mode tests (>= 40) for the 24th unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_warm_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_mxf_mp4_essence_ptpv2_and_tally_umd(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_mxf_mp4_essence_ptpv2_and_tally_umd(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_122_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_122_VERSION)
        self.assertTrue(rep.pillar_a_mxf_mp4_essence_bridge.passed)
        self.assertTrue(rep.pillar_b_ptpv2_ltc_phase_sync.passed)
        self.assertTrue(rep.pillar_c_tsl_umd_tally_bridge.passed)
        self.assertTrue(rep.pillar_d_zero_mutation_emmc_guard.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.08)
        self.assertLess(dt_warm, 0.02)

    def test_02_auto_mode_or_local_donor_runtime_and_sizes(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_mxf_mp4_essence_ptpv2_and_tally_umd()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 0.35)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes.get("fx3_appfw", 0), 70_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_appfw", 0), 45_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx3_libmpr", 0), 3_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libmpr", 0), 25_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libinfra_ptp", 0), 100_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libnet_ether", 0), 100_000)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_mxf_mp4_essence_ptpv2_and_tally_umd()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.mxf_mp4_essence_ptpv2_and_tally_umd_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_mxf_mp4_essence_ptpv2_and_tally_umd(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_no_bytes_repr(self) -> None:
        rep = analyze_mxf_mp4_essence_ptpv2_and_tally_umd(clean_room=True)
        payload = mxf_mp4_essence_ptpv2_and_tally_umd_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_122_SCHEMA, json_str)

    def test_06_auditor_source_strictly_uses_os_o_rdonly_and_mmap_access_read(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in ("os.O_WRONLY", "os.O_RDWR", "os.O_CREAT", "mmap.ACCESS_WRITE", ".write_bytes(", ".write_text("):
            self.assertNotIn(forbidden, src)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("O_WRONLY", "O_RDWR", "O_CREAT", "ACCESS_WRITE"):
                self.fail(f"Forbidden write attribute {node.attr} in auditor AST")

    def test_07_package_exports_and_all_include_phase122_symbols(self) -> None:
        expected_symbols = (
            "PHASE_122_SCHEMA",
            "PHASE_122_VERSION",
            "SMPTE_UMID_BYTES",
            "CAPTURE_GAMMA_UL_MAP",
            "PTPV2_FPS_SPECS",
            "TSL_UMD_PORTS",
            "TSL_TALLY_COLOR_NAMES",
            "MxfMp4EssencePtpv2AndTallyUmdReport",
            "build_smpte_umid",
            "build_rdd18_rtmd_klv_frame",
            "decode_rdd18_rtmd_klv_frame",
            "evaluate_mxf_mp4_essence_bridge",
            "ptpv2_tai_to_smpte12m_tc",
            "evaluate_ptpv2_ltc_phase_sync",
            "sanitize_umd_label_16",
            "build_tsl_umd_v5_packet",
            "parse_tsl_umd_v5_packet",
            "evaluate_tsl_umd_tally_translation",
            "evaluate_phase122_write_guard",
            "evaluate_pillar_a_mxf_mp4_essence_bridge",
            "evaluate_pillar_b_ptpv2_ltc_phase_sync",
            "evaluate_pillar_c_tsl_umd_tally_bridge",
            "evaluate_pillar_d_zero_mutation_emmc_guard",
            "build_clean_room_mxf_mp4_ptpv2_tally_fixtures",
            "analyze_mxf_mp4_essence_ptpv2_and_tally_umd",
            "mxf_mp4_essence_ptpv2_and_tally_umd_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing export {sym} on fx3_firmware_lab")
            self.assertIn(sym, lab.__all__, f"Missing {sym} in fx3_firmware_lab.__all__")

    def test_08_clean_room_fixtures_roundtrip_and_uxc_integrity(self) -> None:
        fx = build_clean_room_mxf_mp4_ptpv2_tally_fixtures()
        self.assertEqual(len(fx), 12)
        for key in (
            "fx3_appfw",
            "fx6_appfw",
            "fx3_libmpr",
            "fx6_libmpr",
            "fx6_libinfra_ptp",
            "fx6_libnet_ether",
        ):
            self.assertTrue(fx[key].startswith(b"\x7fELF\x02\x01\x01\x00"))
        parse_global_xdb_buffer(fx["fx3_global_xdb"])
        parse_global_xdb_buffer(fx["fx6_global_xdb"])
        m39, e39 = _extract_uxc_labels(fx["fx3_str_en"], FX3_NS39_PHASE122_LABELS)
        self.assertEqual(e39, ())
        self.assertEqual(m39["0x0004e100"], "Wired LAN")
        self.assertEqual(m39["0x0004e7fd"], "MP4")
        m6_1, e6_1 = _extract_uxc_labels(fx["fx6_str_en_1"], FX6_NS1_PHASE122_LABELS)
        self.assertEqual(e6_1, ())
        self.assertEqual(m6_1["0x000025be"], "G Tally Lamp")

    # ---- Pillar A: MXF OP1a <-> MP4 ISO-BMFF, UMID & RDD-18 / rtmd ----

    def test_09_smpte_umid_32byte_format_and_uniqueness(self) -> None:
        u1 = build_smpte_umid(material_counter=1, creation_unix_sec=1794715200)
        u2 = build_smpte_umid(material_counter=2, creation_unix_sec=1794715200)
        self.assertEqual(len(bytes.fromhex(u1)), SMPTE_UMID_BYTES)
        self.assertEqual(len(u1), 64)
        self.assertTrue(u1.startswith(SMPTE_UMID_BASIC_PREFIX_HEX))
        self.assertNotEqual(u1, u2)

    def test_10_rdd18_rtmd_klv_roundtrip_all_gamma_and_primaries(self) -> None:
        umid = build_smpte_umid(material_counter=7)
        for gamma_name, gamma_ul in CAPTURE_GAMMA_UL_MAP.items():
            for prim in VALID_CAPTURE_PRIMARIES_P122:
                pkt = build_rdd18_rtmd_klv_frame(
                    exposure_index=3200,
                    base_iso=12800,
                    gamma_name=gamma_name,
                    primaries_name=prim,
                    fps_x1000=29970,
                    f_number_x100=400,
                    shutter_angle_x10=1800,
                    wb_kelvin=3200,
                    cube_lut_path="/tmp/fx3_stageb_lut/Custom.cube",
                    umid_hex=umid,
                )
                self.assertEqual(pkt[:4], RDD18_KLV_PACKET_MAGIC)
                dec = decode_rdd18_rtmd_klv_frame(pkt)
                self.assertTrue(dec.valid, dec.errors)
                self.assertTrue(dec.crc32_valid)
                self.assertEqual(dec.exposure_index, 3200)
                self.assertEqual(dec.base_iso, 12800)
                self.assertEqual(dec.gamma_name, gamma_name)
                self.assertEqual(dec.gamma_ul_hex, gamma_ul)
                self.assertEqual(dec.primaries_name, prim)
                self.assertEqual(dec.umid_hex, umid)

    def test_11_rdd18_decoder_rejects_bad_length_crc_magic_umid_and_iso(self) -> None:
        bad_len = decode_rdd18_rtmd_klv_frame(b"\x06\x0e\x2b\x34" + b"\x00" * 10)
        self.assertFalse(bad_len.valid)
        self.assertFalse(bad_len.crc32_valid)

        valid_pkt = bytearray(build_rdd18_rtmd_klv_frame(base_iso=800))
        valid_pkt[-1] ^= 0xFF
        bad_crc = decode_rdd18_rtmd_klv_frame(bytes(valid_pkt))
        self.assertFalse(bad_crc.valid)
        self.assertFalse(bad_crc.crc32_valid)
        self.assertTrue(any("CRC32" in e for e in bad_crc.errors))

        with self.assertRaises(ValueError):
            build_rdd18_rtmd_klv_frame(gamma_name="LOG_C_ARRI")
        with self.assertRaises(ValueError):
            build_rdd18_rtmd_klv_frame(primaries_name="ACES_AP0")
        with self.assertRaises(ValueError):
            build_rdd18_rtmd_klv_frame(umid_hex="deadbeef")

    def test_12_mxf_to_mp4_and_mp4_to_mxf_lossless_rewrap_preserve_umid(self) -> None:
        umid = build_smpte_umid(material_counter=101)
        r1 = evaluate_mxf_mp4_essence_bridge(
            source_container="MXF_OP1A",
            target_container="MP4_ISOBMFF",
            source_codec="XAVC_I_H422IP",
            target_codec="XAVC_S_I_H422IP",
            bridge_mode="LOSSLESS_REWRAP",
            source_umid_hex=umid,
        )
        r2 = evaluate_mxf_mp4_essence_bridge(
            source_container="MP4_ISOBMFF",
            target_container="MXF_OP1A",
            source_codec="XAVC_S_I_H422IP",
            target_codec="XAVC_I_H422IP",
            bridge_mode="LOSSLESS_REWRAP",
            source_umid_hex=umid,
        )
        for res in (r1, r2):
            self.assertTrue(res.valid, res.errors)
            self.assertEqual(res.status, "LOSSLESS_ESSENCE_REWRAP_VERIFIED")
            self.assertTrue(res.umid_preserved)
            self.assertEqual(res.source_umid_hex, umid)
            self.assertEqual(res.target_umid_hex, umid)
            self.assertTrue(res.spvc_preserved_without_spoofing)

    def test_13_transcode_regenerates_umid_and_rejects_cross_codec_lossless_rewrap(self) -> None:
        umid = build_smpte_umid(material_counter=55)
        tr = evaluate_mxf_mp4_essence_bridge(
            source_container="MXF_OP1A",
            target_container="MP4_ISOBMFF",
            source_codec="XAVC_I_H422IP",
            target_codec="XAVC_HS_HEVC",
            bridge_mode="TRANSCODE",
            source_umid_hex=umid,
        )
        self.assertTrue(tr.valid, tr.errors)
        self.assertEqual(tr.status, "TRANSCODE_NEW_UMID_VERIFIED")
        self.assertFalse(tr.umid_preserved)
        self.assertNotEqual(tr.source_umid_hex, tr.target_umid_hex)

        bad_rewrap = evaluate_mxf_mp4_essence_bridge(
            source_container="MXF_OP1A",
            target_container="MP4_ISOBMFF",
            source_codec="XAVC_I_H422IP",
            target_codec="XAVC_HS_HEVC",
            bridge_mode="LOSSLESS_REWRAP",
        )
        self.assertFalse(bad_rewrap.valid)
        self.assertEqual(bad_rewrap.status, "BLOCKED_INCOMPATIBLE_LOSSLESS_REWRAP")

    def test_14_essence_bridge_blocks_spvc_spoof_raw_mxf_copy_and_corrupt_crc(self) -> None:
        blk_spvc = evaluate_mxf_mp4_essence_bridge(attempt_spvc_spoof=True)
        self.assertFalse(blk_spvc.valid)
        self.assertFalse(blk_spvc.spvc_preserved_without_spoofing)
        self.assertEqual(blk_spvc.status, "BLOCKED_SPVC_CERT_SPOOFING")

        blk_raw = evaluate_mxf_mp4_essence_bridge(
            source_container="MXF_OP1A",
            target_container="MP4_ISOBMFF",
            bridge_mode="DIRECT_RAW_COPY",
        )
        self.assertFalse(blk_raw.valid)
        self.assertEqual(blk_raw.status, "BLOCKED_RAW_MXF_OP1A_ON_MP4_SLOT")

        blk_crc = evaluate_mxf_mp4_essence_bridge(corrupt_rdd18_crc=True)
        self.assertFalse(blk_crc.valid)
        self.assertFalse(blk_crc.rdd18_rtmd_decoded.crc32_valid)

    def test_15_essence_bridge_rejects_invalid_container_codec_or_mode(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_mxf_mp4_essence_bridge(source_container="MOV_PRORES")
        with self.assertRaises(ValueError):
            evaluate_mxf_mp4_essence_bridge(target_codec="PRORES_422_HQ")
        with self.assertRaises(ValueError):
            evaluate_mxf_mp4_essence_bridge(bridge_mode="FAST_APPEND")

    # ---- Pillar B: SMPTE ST 2059-2 PTPv2 & Multi-Terminal LTC Phase Sync ----

    def test_16_ptpv2_tai_to_smpte12m_conversion_all_framerates_and_drop_frame(self) -> None:
        # 2026-11-14T12:01:00 UTC + 37s TAI-UTC offset
        tai_min1 = (1794657660 + PTP_TAI_UTC_OFFSET_SEC) * 1_000_000_000
        for fps_key in PTPV2_FPS_SPECS:
            res = ptpv2_tai_to_smpte12m_tc(tai_ns=tai_min1, fps_key=fps_key)
            self.assertTrue(res.valid, res.errors)
            self.assertEqual(res.utc_ns, 1794657660 * 1_000_000_000)
            if fps_key.endswith("_DF"):
                self.assertTrue(res.drop_frame)
                self.assertIn(";", res.smpte12m_timecode)
                # Drop-frame rule skips :00 and :01 at non-10th minute boundary
                self.assertTrue(res.smpte12m_timecode.endswith(";02"))
            else:
                self.assertFalse(res.drop_frame)
                self.assertIn(":", res.smpte12m_timecode)

    def test_17_ptpv2_negative_tai_and_unsupported_fps_rejected(self) -> None:
        neg = ptpv2_tai_to_smpte12m_tc(tai_ns=-100)
        self.assertFalse(neg.valid)
        self.assertEqual(neg.smpte12m_timecode, "00:00:00:00")
        with self.assertRaises(ValueError):
            ptpv2_tai_to_smpte12m_tc(tai_ns=1_000_000_000, fps_key="119.880_NDF")

    def test_18_ptpv2_hw_and_sw_timestamping_across_all_wired_transports(self) -> None:
        for drv in WIRED_SYNC_TRANSPORTS:
            hw = evaluate_ptpv2_ltc_phase_sync(
                sync_profile="SMPTE_ST_2059_2_HW_TS",
                transport_driver=drv,
                ptpv2_domain=SMPTE_ST2059_DEFAULT_DOMAIN,
                measured_ptp_jitter_us=PTPV2_MAX_HW_JITTER_US - 0.1,
                ltc_phase_offset_us=LTC_MAX_PHASE_OFFSET_US - 10.0,
            )
            self.assertTrue(hw.valid, hw.errors)
            self.assertEqual(hw.status, "ST2059_PTPV2_LTC_PHASE_LOCKED")
            self.assertEqual(hw.wf12_00342260_risk, 0)

            sw = evaluate_ptpv2_ltc_phase_sync(
                sync_profile="SMPTE_ST_2059_2_SW_TS",
                transport_driver=drv,
                measured_ptp_jitter_us=PTPV2_MAX_SW_JITTER_US - 5.0,
                ltc_phase_offset_us=-100.0,
                fps_key="59.940_DF",
            )
            self.assertTrue(sw.valid, sw.errors)
            self.assertEqual(sw.wf12_00342260_risk, 0)

    def test_19_ptpv2_blocks_ptpip_confusion_and_jitter_ceilings(self) -> None:
        blk_ptpip = evaluate_ptpv2_ltc_phase_sync(
            sync_profile="PTP_IP_15740_CONTROL",
            transport_driver="CDC_NCM_RTL8153",
        )
        self.assertFalse(blk_ptpip.valid)
        self.assertEqual(blk_ptpip.status, "BLOCKED_PTPIP_NOT_IEEE1588_PTPV2")

        blk_hw_j = evaluate_ptpv2_ltc_phase_sync(
            sync_profile="SMPTE_ST_2059_2_HW_TS",
            measured_ptp_jitter_us=PTPV2_MAX_HW_JITTER_US + 0.5,
        )
        self.assertFalse(blk_hw_j.valid)
        self.assertEqual(blk_hw_j.status, "BLOCKED_PTPV2_HW_JITTER_EXCEEDED")

        blk_sw_j = evaluate_ptpv2_ltc_phase_sync(
            sync_profile="SMPTE_ST_2059_2_SW_TS",
            measured_ptp_jitter_us=PTPV2_MAX_SW_JITTER_US + 1.0,
        )
        self.assertFalse(blk_sw_j.valid)
        self.assertEqual(blk_sw_j.status, "BLOCKED_PTPV2_SW_JITTER_EXCEEDED")

    def test_20_ptpv2_blocks_wifi_bt_p12_domain_ltc_drift_and_uart_boot(self) -> None:
        for rf_drv in FORBIDDEN_RF_SYNC_TRANSPORTS:
            blk_rf = evaluate_ptpv2_ltc_phase_sync(
                transport_driver=rf_drv,
                p12_airplane_rf_off=True,
            )
            self.assertFalse(blk_rf.valid)
            self.assertEqual(blk_rf.wf12_00342260_risk, 1)
            self.assertEqual(blk_rf.status, "BLOCKED_P12_RF_OFF_VIOLATION_00342260")

        blk_dom = evaluate_ptpv2_ltc_phase_sync(ptpv2_domain=300)
        self.assertFalse(blk_dom.valid)
        self.assertEqual(blk_dom.status, "BLOCKED_INVALID_PTPV2_DOMAIN")

        blk_drift = evaluate_ptpv2_ltc_phase_sync(ltc_phase_offset_us=-LTC_MAX_PHASE_OFFSET_US - 1.0)
        self.assertFalse(blk_drift.valid)
        self.assertEqual(blk_drift.status, "BLOCKED_LTC_PHASE_DRIFT_EXCEEDED")

        blk_uart = evaluate_ptpv2_ltc_phase_sync(vmc_bncm1_attached=True, uart_boot_active=True)
        self.assertFalse(blk_uart.valid)
        self.assertEqual(blk_uart.status, "BLOCKED_VMC_BNCM1_DURING_UART_BOOT")

        ok_uart_detached = evaluate_ptpv2_ltc_phase_sync(vmc_bncm1_attached=False, uart_boot_active=True)
        self.assertTrue(ok_uart_detached.valid, ok_uart_detached.errors)

        with self.assertRaises(ValueError):
            evaluate_ptpv2_ltc_phase_sync(sync_profile="NTP_V4")
        with self.assertRaises(ValueError):
            evaluate_ptpv2_ltc_phase_sync(transport_driver="MODEM_5G")

    # ---- Pillar C: TSL UMD v5.0 Wire Protocol & FX3 Tally Bridge ----

    def test_21_tsl_umd_v5_udp_ascii_and_utf16le_wire_roundtrip(self) -> None:
        pkt_ascii = build_tsl_umd_v5_packet(
            screen=2,
            entries=((0, 1, 1, 1, 3, "CAM-A1"), (1, 2, 0, 2, 2, "CAM-B2")),
            unicode_utf16=False,
            tcp_dle_stx=False,
        )
        pbc, ver, flags, screen = struct.unpack_from("<HBBH", pkt_ascii, 0)
        self.assertEqual(pbc, len(pkt_ascii) - 2)
        self.assertEqual(ver, 0)
        self.assertEqual(flags, 0x00)
        self.assertEqual(screen, 2)

        dec_a = parse_tsl_umd_v5_packet(pkt_ascii, expect_tcp_dle_stx=False)
        self.assertTrue(dec_a.valid, dec_a.errors)
        self.assertFalse(dec_a.is_utf16le)
        self.assertEqual(len(dec_a.messages), 2)
        self.assertEqual(dec_a.messages[0].text, "CAM-A1")
        self.assertEqual(dec_a.messages[0].lh_tally, 1)
        self.assertEqual(dec_a.messages[1].lh_tally, 2)

        pkt_u16 = build_tsl_umd_v5_packet(
            screen=1,
            entries=((4, 3, 3, 3, 1, "摄影机A1"),),
            unicode_utf16=True,
            tcp_dle_stx=False,
        )
        dec_u = parse_tsl_umd_v5_packet(pkt_u16, expect_tcp_dle_stx=False)
        self.assertTrue(dec_u.valid, dec_u.errors)
        self.assertTrue(dec_u.is_utf16le)
        self.assertEqual(dec_u.messages[0].text, "摄影机A1")

    def test_22_tsl_umd_v5_tcp_dle_stx_stuffing_escapes_0xfe_bytes(self) -> None:
        pkt_tcp = build_tsl_umd_v5_packet(
            screen=0x00FE,
            entries=((0x00FE, 1, 2, 2, 3, "CAM-FE"),),
            tcp_dle_stx=True,
        )
        self.assertEqual(pkt_tcp[0], TSL_UMD_DLE)
        self.assertEqual(pkt_tcp[1], TSL_UMD_STX)
        # Body contains 0xFE both in screen=0x00FE and index=0x00FE, each escaped as 0xFE 0xFE
        self.assertIn(b"\xfe\xfe", pkt_tcp[2:])

        dec = parse_tsl_umd_v5_packet(pkt_tcp, expect_tcp_dle_stx=True)
        self.assertTrue(dec.valid, dec.errors)
        self.assertTrue(dec.tcp_dle_stx_framed)
        self.assertEqual(dec.screen, 0x00FE)
        self.assertEqual(dec.messages[0].index, 0x00FE)
        self.assertEqual(dec.messages[0].lh_tally, 2)

        bad_missing_hdr = parse_tsl_umd_v5_packet(b"\x00\x06\x00\x00\x00\x00", expect_tcp_dle_stx=True)
        self.assertFalse(bad_missing_hdr.valid)

        bad_unescaped_dle = parse_tsl_umd_v5_packet(b"\xfe\x02\x00\xfe\x01", expect_tcp_dle_stx=True)
        self.assertFalse(bad_unescaped_dle.valid)

    def test_23_tsl_umd_v5_parser_rejects_malformed_pbc_version_ctrl_and_truncation(self) -> None:
        good = bytearray(build_tsl_umd_v5_packet(entries=((0, 1, 1, 1, 3, "CAM1"),)))
        # Corrupt PBC
        bad_pbc = bytearray(good)
        bad_pbc[0] = 0xFF
        self.assertFalse(parse_tsl_umd_v5_packet(bytes(bad_pbc)).valid)

        # Corrupt minor version != 0
        bad_ver = bytearray(good)
        bad_ver[2] = 0x01
        self.assertFalse(parse_tsl_umd_v5_packet(bytes(bad_ver)).valid)

        # Set undefined CONTROL DATA bit 15
        bad_ctrl = bytearray(good)
        bad_ctrl[9] |= 0x80
        self.assertFalse(parse_tsl_umd_v5_packet(bytes(bad_ctrl)).valid)

        # Truncate packet below 6B header
        self.assertFalse(parse_tsl_umd_v5_packet(b"\x01\x00\x00").valid)

        # Truncate <DMSG> text payload
        self.assertFalse(parse_tsl_umd_v5_packet(bytes(good[:-2])).valid)

        # Oversize UDP packet > 2048B
        oversize = build_tsl_umd_v5_packet(entries=((0, 1, 1, 1, 3, "A" * (TSL_UMD_UDP_MAX_BYTES + 32)),))
        dec_over = parse_tsl_umd_v5_packet(oversize, expect_tcp_dle_stx=False)
        self.assertFalse(dec_over.valid)
        self.assertTrue(any("BLOCKED_TSL_UDP_PACKET_EXCEEDS_2048B" in e for e in dec_over.errors))

    def test_24_tsl_umd_v5_builder_validation_and_16char_label_sanitizer(self) -> None:
        with self.assertRaises(ValueError):
            build_tsl_umd_v5_packet(entries=((0, 4, 0, 0, 1, "BAD"),))
        with self.assertRaises(ValueError):
            build_tsl_umd_v5_packet(entries=((0, 1, 1, 1, 4, "BAD"),))

        dirty = "\x1b[31m  CAM-01\x07\n_STAGE_B_EXTRA_CHARS  \x1b[0m"
        clean = sanitize_umd_label_16(dirty)
        self.assertEqual(len(clean), TSL_UMD_MAX_LABEL_CHARS)
        self.assertEqual(clean, "CAM-01_STAGE_B_E")

    def test_25_fx3_tally_bridge_red_vs_green_zero_false_red_leak_hardware_truth(self) -> None:
        # RED (PGM=1): FX3 physical Front+Rear Red LEDs ON + RED OSD border
        red = evaluate_tsl_umd_tally_translation(
            port_key="UDP_40003",
            transport_driver="CDC_NCM_RTL8153",
            lh_tally=1,
            raw_umd_label="CAM-A1 PGM",
        )
        self.assertTrue(red.valid, red.errors)
        self.assertEqual(red.incoming_tally_name, "RED")
        self.assertTrue(red.fx3_front_rear_red_leds_on)
        self.assertEqual(red.osd_border_color, "RED")
        self.assertEqual(red.fx6_green_gpio_faults, 0)

        # GREEN (PVW=2): FX3 physical Red LEDs strictly OFF (prevents false PGM) + GREEN OSD border
        green = evaluate_tsl_umd_tally_translation(
            port_key="TCP_5727",
            transport_driver="CDC_NCM_AX88179",
            lh_tally=2,
            raw_umd_label="CAM-A1 PVW",
        )
        self.assertTrue(green.valid, green.errors)
        self.assertEqual(green.incoming_tally_name, "GREEN")
        self.assertFalse(green.fx3_front_rear_red_leds_on)
        self.assertEqual(green.osd_border_color, "GREEN")
        self.assertEqual(green.fx6_green_gpio_faults, 0)

        # AMBER (ISO/BOTH=3): FX3 physical Red LEDs OFF + AMBER OSD border
        amber = evaluate_tsl_umd_tally_translation(
            port_key="UDP_8900",
            transport_driver="USB_RNDIS_WIRED",
            lh_tally=3,
            raw_umd_label="CAM-A1 ISO",
        )
        self.assertTrue(amber.valid, amber.errors)
        self.assertEqual(amber.incoming_tally_name, "AMBER")
        self.assertFalse(amber.fx3_front_rear_red_leds_on)
        self.assertEqual(amber.osd_border_color, "AMBER")

        # OFF (0): physical Red LEDs OFF + NONE OSD border
        off = evaluate_tsl_umd_tally_translation(
            port_key="TCP_5728",
            transport_driver="CDC_NCM_RTL8153",
            lh_tally=0,
        )
        self.assertTrue(off.valid, off.errors)
        self.assertEqual(off.incoming_tally_name, "OFF")
        self.assertFalse(off.fx3_front_rear_red_leds_on)
        self.assertEqual(off.osd_border_color, "NONE")
        self.assertEqual(len(TSL_UMD_PORTS), 4)
        self.assertEqual(set(TSL_TALLY_COLOR_NAMES.values()), {"OFF", "RED", "GREEN", "AMBER"})

    def test_26_tsl_tally_bridge_blocks_wifi_p12_and_oversize_udp(self) -> None:
        for rf_drv in FORBIDDEN_RF_SYNC_TRANSPORTS:
            blk = evaluate_tsl_umd_tally_translation(
                port_key="UDP_40003",
                transport_driver=rf_drv,
                p12_airplane_rf_off=True,
                lh_tally=1,
            )
            self.assertFalse(blk.valid)
            self.assertEqual(blk.wf12_00342260_risk, 1)
            self.assertEqual(blk.status, "BLOCKED_P12_RF_OFF_VIOLATION_00342260")

        blk_over = evaluate_tsl_umd_tally_translation(
            port_key="UDP_40003",
            transport_driver="CDC_NCM_RTL8153",
            oversize_udp_test=True,
        )
        self.assertFalse(blk_over.valid)
        self.assertEqual(blk_over.status, "BLOCKED_TSL_UDP_PACKET_EXCEEDS_2048B")

        with self.assertRaises(ValueError):
            evaluate_tsl_umd_tally_translation(port_key="HTTP_80")
        with self.assertRaises(ValueError):
            evaluate_tsl_umd_tally_translation(transport_driver="LORA_915")

    # ---- Pillar D: Volatile RAM Staging & Zero Persistent eMMC/Calibration Guard ----

    def test_27_phase122_write_guard_allows_volatile_and_blocks_all_emmc_targets(self) -> None:
        for good in (
            "/tmp/fx3_ptpv2_state.json",
            "ram://mxf_mp4_rewrap_ring",
            "memory://tsl_umd_shadow",
        ):
            ok = evaluate_phase122_write_guard(good)
            self.assertTrue(ok.valid, ok.errors)
            self.assertTrue(ok.volatile_ram_staged)
            self.assertFalse(ok.persistent_write_blocked)
            self.assertEqual(ok.emmc_mutation_bytes, 0)
            self.assertEqual(ok.calibration_mutation_bytes, 0)

        for bad in (
            "/mnt/sd/BODYDATA.DAT",
            "/dev/nflasha15",
            "/dev/cnflasha0",
            "/dev/mmcblk0rpmb",
            "/dev/mtdblock3",
            "p2:/setting/Backup.bin",
            "p2:/setting/psd.bin",
            "p2:/setting/defdet.bin",
            "p6:/tmp/jiritsu",
            "updater://stage_ota",
            "nvram://calib",
            "eeprom://sensor",
        ):
            blk = evaluate_phase122_write_guard(bad)
            self.assertFalse(blk.valid, f"Failed to block {bad}")
            self.assertTrue(blk.persistent_write_blocked)
            self.assertEqual(blk.status, "BLOCKED_PERSISTENT_EMMC_OR_OTA_WRITE")
            self.assertEqual(blk.emmc_mutation_bytes, 0)
            self.assertEqual(blk.calibration_mutation_bytes, 0)

    # ---- Pillar Reports, Donor Markers, Negative Sim & CLI Integration ----

    def test_28_pillar_a_marker_and_uxc_integrity(self) -> None:
        rep = analyze_mxf_mp4_essence_ptpv2_and_tally_umd(clean_room=True)
        pa = rep.pillar_a_mxf_mp4_essence_bridge
        self.assertTrue(pa.passed)
        self.assertEqual(len(pa.fx6_libmpr_mxf_markers), len(FX6_LIBMPR_PHASE122_MARKERS))
        self.assertEqual(len(pa.fx3_libmpr_mp4_markers), len(FX3_LIBMPR_PHASE122_MARKERS))
        self.assertEqual(len(pa.fx6_appfw_mxf_markers), 2)
        self.assertEqual(pa.uxc_container_labels["fx3_mp4"], "MP4")
        self.assertEqual(pa.uxc_container_labels["fx3_wired_lan"], "Wired LAN")

    def test_29_pillar_b_marker_and_uxc_integrity(self) -> None:
        rep = analyze_mxf_mp4_essence_ptpv2_and_tally_umd(clean_room=True)
        pb = rep.pillar_b_ptpv2_ltc_phase_sync
        self.assertTrue(pb.passed)
        self.assertEqual(len(pb.fx3_appfw_tc_lan_markers), len(FX3_APPFW_PHASE122_MARKERS) - 1)
        self.assertEqual(len(pb.fx6_appfw_tc_markers), 1)
        self.assertEqual(len(pb.fx6_libnet_ether_markers), len(FX6_LIBNET_ETHER_PHASE122_MARKERS))
        self.assertEqual(len(pb.fx6_libinfra_ptp_markers), len(FX6_LIBINFRA_PTP_PHASE122_MARKERS))
        self.assertEqual(pb.uxc_tc_lan_labels["fx3_wired_lan"], "Wired LAN")
        self.assertEqual(pb.uxc_tc_lan_labels["fx6_timecode"], "Timecode")
        self.assertEqual(pb.uxc_tc_lan_labels["fx6_hdmi_tc_out"], "HDMI TC Out")

    def test_30_pillar_c_marker_and_uxc_integrity(self) -> None:
        rep = analyze_mxf_mp4_essence_ptpv2_and_tally_umd(clean_room=True)
        pc = rep.pillar_c_tsl_umd_tally_bridge
        self.assertTrue(pc.passed)
        self.assertEqual(pc.fx3_appfw_tally_markers, ("sequence_set_tally_status",))
        self.assertEqual(len(pc.fx6_appfw_tally_markers), len(FX6_APPFW_PHASE122_MARKERS) - 3)
        self.assertEqual(pc.uxc_tally_labels["fx6_front_tally"], "Front Tally Lamp")
        self.assertEqual(pc.uxc_tally_labels["fx6_rear_tally"], "Rear Tally Lamp")
        self.assertEqual(pc.uxc_tally_labels["fx6_g_tally_lamp"], "G Tally Lamp")
        self.assertEqual(pc.uxc_tally_labels["fx6_tally"], "Tally")

    def test_31_pillar_d_zero_mutation_proof(self) -> None:
        rep = analyze_mxf_mp4_essence_ptpv2_and_tally_umd(clean_room=True)
        pd = rep.pillar_d_zero_mutation_emmc_guard
        self.assertTrue(pd.passed)
        self.assertTrue(pd.fx3_global_xdb_valid)
        self.assertTrue(pd.fx6_global_xdb_valid)
        self.assertEqual(pd.emmc_mutation_bytes, 0)
        self.assertEqual(pd.calibration_mutation_bytes, 0)
        self.assertFalse(pd.persistent_emmc_writes_authorized)

    def test_32_negative_missing_marker_detection_in_all_four_pillars(self) -> None:
        ba = evaluate_pillar_a_mxf_mp4_essence_bridge(
            fx6_libmpr_mxf_markers=(),
            fx3_libmpr_mp4_markers=(),
            fx6_appfw_mxf_markers=(),
            uxc_container_labels={},
            extra_errors=("Simulated Pillar A failure",),
        )
        bb = evaluate_pillar_b_ptpv2_ltc_phase_sync(
            fx3_appfw_tc_lan_markers=(),
            fx6_appfw_tc_markers=(),
            fx6_libnet_ether_markers=(),
            fx6_libinfra_ptp_markers=(),
            uxc_tc_lan_labels={},
            extra_errors=("Simulated Pillar B failure",),
        )
        bc = evaluate_pillar_c_tsl_umd_tally_bridge(
            fx3_appfw_tally_markers=(),
            fx6_appfw_tally_markers=(),
            uxc_tally_labels={},
            extra_errors=("Simulated Pillar C failure",),
        )
        bd = evaluate_pillar_d_zero_mutation_emmc_guard(
            fx3_global_xdb_valid=False,
            fx6_global_xdb_valid=False,
            extra_errors=("Simulated Pillar D XDB failure",),
        )
        self.assertFalse(ba.passed)
        self.assertFalse(bb.passed)
        self.assertFalse(bc.passed)
        self.assertFalse(bd.passed)

    def test_33_cli_audit_mxf_mp4_tally_clean_room_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-mxf-mp4-tally", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        raw = buf.getvalue()
        self.assertIsNone(_BYTES_REPR_RE.search(raw))
        data = json.loads(raw)
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["schema_version"], PHASE_122_SCHEMA)

    def test_34_cli_audit_mxf_mp4_tally_auto_mode_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-mxf-mp4-tally", "--json"])
        self.assertEqual(rc, 0)
        raw = buf.getvalue()
        self.assertIsNone(_BYTES_REPR_RE.search(raw))
        data = json.loads(raw)
        self.assertTrue(data["all_checks_passed"])
        self.assertIn(data["mode"], ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))

    def test_35_cli_audit_mxf_mp4_tally_default_json_and_forced_env(self) -> None:
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            with redirect_stdout(buf):
                rc = cli_main(["audit-mxf-mp4-tally"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["schema_version"], PHASE_122_SCHEMA)

    def test_36_run_audit_all_includes_at_least_24_auditors_and_passes(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 24)
        self.assertIn("mxf_mp4_essence_ptpv2_and_tally_umd_audit", summary)
        p122 = summary["mxf_mp4_essence_ptpv2_and_tally_umd_audit"]
        self.assertTrue(p122["all_checks_passed"])
        self.assertEqual(p122["mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_37_cli_audit_all_clean_room_json_green(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        audit_keys = [k for k in data if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 24)
        self.assertTrue(data["mxf_mp4_essence_ptpv2_and_tally_umd_audit"]["all_checks_passed"])

    def test_38_local_donor_vs_clean_room_structural_parity(self) -> None:
        rep_auto = analyze_mxf_mp4_essence_ptpv2_and_tally_umd()
        rep_cr = analyze_mxf_mp4_essence_ptpv2_and_tally_umd(clean_room=True)
        self.assertTrue(rep_auto.all_checks_passed)
        self.assertTrue(rep_cr.all_checks_passed)
        self.assertEqual(
            rep_auto.pillar_a_mxf_mp4_essence_bridge.fx6_libmpr_mxf_markers,
            rep_cr.pillar_a_mxf_mp4_essence_bridge.fx6_libmpr_mxf_markers,
        )
        self.assertEqual(
            rep_auto.pillar_a_mxf_mp4_essence_bridge.fx3_libmpr_mp4_markers,
            rep_cr.pillar_a_mxf_mp4_essence_bridge.fx3_libmpr_mp4_markers,
        )
        self.assertEqual(
            rep_auto.pillar_b_ptpv2_ltc_phase_sync.fx6_libinfra_ptp_markers,
            rep_cr.pillar_b_ptpv2_ltc_phase_sync.fx6_libinfra_ptp_markers,
        )
        self.assertEqual(
            rep_auto.pillar_c_tsl_umd_tally_bridge.uxc_tally_labels,
            rep_cr.pillar_c_tsl_umd_tally_bridge.uxc_tally_labels,
        )

    def test_39_all_tsl_ports_supported_and_consistent(self) -> None:
        for port_key, (proto, port_num) in TSL_UMD_PORTS.items():
            res = evaluate_tsl_umd_tally_translation(
                port_key=port_key,
                transport_driver="CDC_NCM_RTL8153",
                lh_tally=1,
                raw_umd_label=f"P-{port_num}",
            )
            self.assertTrue(res.valid, res.errors)
            self.assertEqual(res.packet_decoded.tcp_dle_stx_framed, proto == "TCP")

    def test_40_negative_pillar_d_single_xdb_failure_flags_report_false(self) -> None:
        only_fx3_bad = evaluate_pillar_d_zero_mutation_emmc_guard(
            fx3_global_xdb_valid=False,
            fx6_global_xdb_valid=True,
        )
        only_fx6_bad = evaluate_pillar_d_zero_mutation_emmc_guard(
            fx3_global_xdb_valid=True,
            fx6_global_xdb_valid=False,
        )
        self.assertFalse(only_fx3_bad.passed)
        self.assertFalse(only_fx6_bad.passed)
        self.assertEqual(only_fx3_bad.emmc_mutation_bytes, 0)
        self.assertEqual(only_fx6_bad.calibration_mutation_bytes, 0)


if __name__ == "__main__":
    unittest.main()
