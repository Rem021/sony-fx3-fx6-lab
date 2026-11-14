"""Unit tests for Phase 37 `.cube` (`17^3`/`33^3`) 3D LUT Sanitizer, P1/P11 Packer & Sony RTMD (`0xE304`) Verifier.

Runs in BOTH Local Donor mode (`O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` mode,
keeping the combined `fx3-firmware-lab` test suite (103 tests) under 5 seconds.
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.cube_lut_and_rtmd_verifier import (
    BKID_APP_SELECT_LUT,
    BKID_USER_LUT_FLAG_END,
    BKID_USER_LUT_FLAG_START,
    CubeLutAndRtmdReport,
    CubeLutSanitizationError,
    LUT_8BIT_ALIGNED_BYTES,
    LUT_12BIT_U16_BYTES,
    MAX_SAFE_CUBE_FILE_BYTES,
    MPR_SET_LUT_DESCRIPTOR_BYTES,
    PHASE_37_SCHEMA,
    RTMD_E304_PAYLOAD_BYTES,
    RTMD_RDD18_ACQUISITION_UL,
    RTMD_TAG_IMX510_IBIS_GYRO_E304,
    RtmdFrameMetadata,
    RtmdProtocolError,
    SMPTE_KLV_UL_PREFIX,
    UIPC_BB_MAGIC,
    UIPC_BB_OPCODE_LUT_DMA,
    UIPC_BB_OPCODE_LUT_TOGGLE,
    analyze_cube_lut_and_rtmd,
    audit_cube_lut_text,
    build_clean_room_lut_rtmd_fixtures,
    build_identity_cube_lut,
    build_p11_0165_lut_dma_packet,
    build_p11_0166_lut_toggle_packet,
    build_p11_lut_hardware_bundle,
    build_rtmd_klv_packet,
    decode_ber_length,
    encode_ber_length,
    evaluate_p1_nflasha30_storage_budget,
    generate_bk4_lut_slot_properties,
    pack_cube_to_dma_table,
    parse_and_sanitize_cube_lut,
    parse_and_verify_rtmd_klv_packet,
    trilinear_sample_cube,
    upsample_cube_17_to_33,
    verify_slog3_identity_ramp,
)
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveCubeLutAndRtmdAudit(unittest.TestCase):
    _active_report: Optional[CubeLutAndRtmdReport] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._active_report = analyze_cube_lut_and_rtmd()

    def test_active_mode_passes_with_deterministic_sha256(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.schema_version, PHASE_37_SCHEMA)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_profiles), 4)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_profiles["fx3_appfw"].file_bytes, 50_000_000)
            self.assertGreater(rep.donor_profiles["fx6_appfw"].file_bytes, 40_000_000)
            self.assertGreater(rep.donor_profiles["fx3_libmpr"].file_bytes, 3_000_000)
            self.assertGreater(rep.donor_profiles["fx6_libmpr"].file_bytes, 20_000_000)
            self.assertGreater(rep.donor_profiles["fx3_libmpr"].smpte_ul_prefix_hits, 0)
            self.assertGreater(rep.donor_profiles["fx6_libmpr"].smpte_ul_prefix_hits, 0)

    def test_active_donor_markers_for_nflasha30_and_rdd18(self) -> None:
        rep = self._active_report
        assert rep is not None
        for key, prof in rep.donor_profiles.items():
            self.assertEqual(prof.missing_markers, (), msg=f"{key} missing {prof.missing_markers}")
        self.assertIn("/dev/nflasha30", rep.donor_profiles["fx3_appfw"].matched_markers)
        self.assertIn(
            "_ZN3mpr12KlvConverter18Rdd18KeyCameraUnitE",
            rep.donor_profiles["fx6_libmpr"].matched_markers,
        )
        self.assertIn(
            "_ZN3mpr12KlvConverter21UDAMSetGyroscopeValueE",
            rep.donor_profiles["fx3_libmpr"].matched_markers,
        )


class TestCubeLutSanitizerAndTrilinearPacker(unittest.TestCase):
    _id_17_txt: str = ""

    @classmethod
    def setUpClass(cls) -> None:
        cls._id_17_txt = build_identity_cube_lut(17, title="SONY_IDENTITY_17")

    def test_valid_17_and_33_cube_parse(self) -> None:
        p17 = parse_and_sanitize_cube_lut(self._id_17_txt)
        self.assertEqual(p17.grid_size, 17)
        self.assertEqual(len(p17.entries), 17 ** 3)
        self.assertEqual(p17.title, "SONY_IDENTITY_17")

        txt33 = build_identity_cube_lut(33, title="SONY_IDENTITY_33")
        p33 = parse_and_sanitize_cube_lut(txt33)
        self.assertEqual(p33.grid_size, 33)
        self.assertEqual(len(p33.entries), 33 ** 3)

    def test_rejects_nan_and_inf_entries(self) -> None:
        bad_nan = self._id_17_txt.replace("0.000000 0.000000 0.000000", "NaN 0.000000 0.000000", 1)
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(bad_nan)

        bad_inf = self._id_17_txt.replace("1.000000 1.000000 1.000000", "1.000000 inf 1.000000", 1)
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(bad_inf)

    def test_rejects_wrong_grid_counts_and_unsupported_sizes(self) -> None:
        # Missing final line
        lines = self._id_17_txt.splitlines()
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut("\n".join(lines[:-1]))
        # Extra triplet line
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(self._id_17_txt + "0.5 0.5 0.5\n")
        # Unsupported size 65
        bad_size = self._id_17_txt.replace("LUT_3D_SIZE 17", "LUT_3D_SIZE 65", 1)
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(bad_size)

    def test_rejects_non_monotonic_domain_min_ge_max(self) -> None:
        bad_eq = self._id_17_txt.replace("DOMAIN_MIN 0.000000 0.000000 0.000000", "DOMAIN_MIN 0.000000 1.000000 0.000000", 1)
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(bad_eq)

        bad_inv = self._id_17_txt.replace("DOMAIN_MIN 0.000000 0.000000 0.000000", "DOMAIN_MIN 1.500000 0.000000 0.000000", 1)
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(bad_inv)

    def test_rejects_lut_1d_size_mismatch_and_control_chars(self) -> None:
        bad_1d = 'TITLE "BAD_1D"\nLUT_1D_SIZE 1024\n0.0 0.0 0.0\n'
        res = audit_cube_lut_text(bad_1d)
        self.assertFalse(res.valid)
        self.assertIn("LUT_1D_SIZE", res.errors[0])

        bad_title = self._id_17_txt.replace('TITLE "SONY_IDENTITY_17"', 'TITLE "../etc/passwd"', 1)
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(bad_title)

        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(self._id_17_txt.encode("utf-8") + b"\x00")

    def test_rejects_oversized_v601_crash_and_nflasha30_overflow(self) -> None:
        oversized = ("# pad\n" * 100) + ("0.000000 0.000000 0.000000\n" * 10)
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(oversized, max_file_bytes=512)
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(self._id_17_txt, max_lines=100)

        # Confirm standard MAX_SAFE_CUBE_FILE_BYTES is 2 MiB
        self.assertEqual(MAX_SAFE_CUBE_FILE_BYTES, 2 * 1024 * 1024)

    def test_trilinear_17_to_33_upsample_exact_linear_and_affine(self) -> None:
        # Build an affine 17^3 LUT: out = (0.8*r + 0.1, 0.6*g + 0.2, 0.5*b + 0.25)
        lines = ['TITLE "AFFINE_17"', "LUT_3D_SIZE 17"]
        for bi in range(17):
            b = bi / 16.0
            for gi in range(17):
                g = gi / 16.0
                for ri in range(17):
                    r = ri / 16.0
                    lines.append(f"{0.8 * r + 0.1:.6f} {0.6 * g + 0.2:.6f} {0.5 * b + 0.25:.6f}")
        lut17 = parse_and_sanitize_cube_lut("\n".join(lines))
        lut33 = upsample_cube_17_to_33(lut17)
        self.assertEqual(lut33.grid_size, 33)
        self.assertEqual(len(lut33.entries), 35_937)

        # Test arbitrary non-lattice coordinate
        sr, sg, sb = trilinear_sample_cube(lut33, 0.37, 0.61, 0.83)
        self.assertAlmostEqual(sr, 0.8 * 0.37 + 0.1, places=5)
        self.assertAlmostEqual(sg, 0.6 * 0.61 + 0.2, places=5)
        self.assertAlmostEqual(sb, 0.5 * 0.83 + 0.25, places=5)

    def test_pack_dma_table_u12_u16_and_u8(self) -> None:
        lut17 = parse_and_sanitize_cube_lut(self._id_17_txt)
        dma_u12 = pack_cube_to_dma_table(lut17, bit_depth=12)
        self.assertEqual(len(dma_u12), LUT_12BIT_U16_BYTES)
        # First voxel (0,0,0) -> (0,0,0), last voxel (32,32,32) -> (4095,4095,4095)
        self.assertEqual(struct.unpack_from("<HHH", dma_u12, 0), (0, 0, 0))
        self.assertEqual(struct.unpack_from("<HHH", dma_u12, len(dma_u12) - 6), (4095, 4095, 4095))

        dma_u16 = pack_cube_to_dma_table(lut17, bit_depth=16)
        self.assertEqual(len(dma_u16), LUT_12BIT_U16_BYTES)
        self.assertEqual(struct.unpack_from("<HHH", dma_u16, len(dma_u16) - 6), (65535, 65535, 65535))

        dma_u8 = pack_cube_to_dma_table(lut17, bit_depth=8)
        self.assertEqual(len(dma_u8), LUT_8BIT_ALIGNED_BYTES)

    def test_slog3_identity_ramp_within_one_lsb(self) -> None:
        lut17 = parse_and_sanitize_cube_lut(self._id_17_txt)
        proof_u12 = verify_slog3_identity_ramp(lut17, bit_depth=12, samples=256)
        self.assertTrue(proof_u12.passed)
        self.assertLessEqual(proof_u12.max_lsb_error, 1)
        self.assertLess(proof_u12.max_float_error, 1e-6)

        proof_u16 = verify_slog3_identity_ramp(lut17, bit_depth=16, samples=128)
        self.assertTrue(proof_u16.passed)
        self.assertLessEqual(proof_u16.max_lsb_error, 1)

    def test_p11_set_lut_data_0165_0166_and_bk4_slot_flags(self) -> None:
        lut17 = parse_and_sanitize_cube_lut(self._id_17_txt)
        bundle = build_p11_lut_hardware_bundle(
            lut17,
            slot_name="User3",
            populated_user_slots=(1, 3, 16),
            bit_depth=12,
            base_iso=12800,
            ei_index=12800,
        )
        self.assertEqual(bundle.select_lut_code, 0x05)  # User1=0x03, User3=0x05
        self.assertEqual(bundle.cube_path, "/usr/data/lut/LUT003.cube")
        self.assertEqual(bundle.mpr_descriptor_bytes, MPR_SET_LUT_DESCRIPTOR_BYTES)
        self.assertTrue(bundle.uses_dram_dma_path)
        self.assertTrue(bundle.bk4_record_valid)
        self.assertEqual(bundle.bk4_select_lut_hex, "05")
        self.assertEqual(bundle.bk4_user_flags_hex[f"0x{BKID_USER_LUT_FLAG_START:08x}"], "01")
        self.assertEqual(bundle.bk4_user_flags_hex[f"0x{BKID_USER_LUT_FLAG_START + 1:08x}"], "00")
        self.assertEqual(bundle.bk4_user_flags_hex[f"0x{BKID_USER_LUT_FLAG_START + 2:08x}"], "01")
        self.assertEqual(bundle.bk4_user_flags_hex[f"0x{BKID_USER_LUT_FLAG_END:08x}"], "01")

        # Verify 164B SetLutData binary layout
        desc = bytes.fromhex(bundle.mpr_descriptor_hex)
        self.assertEqual(struct.unpack_from("<IB", desc, 0), (164, 1))
        self.assertIn(b"/usr/data/lut/LUT003.cube\x00", desc[0x1F:0x5F])

        # Verify 36B 0x0165 & 10B 0x0166 headers
        p0165 = bytes.fromhex(bundle.dma_packet_0165_hex)
        self.assertEqual(len(p0165), 36)
        self.assertEqual(struct.unpack_from("<HHHH", p0165, 0), (UIPC_BB_MAGIC, UIPC_BB_OPCODE_LUT_DMA, 36, 0x8001))
        p0166 = bytes.fromhex(bundle.toggle_packet_0166_hex)
        self.assertEqual(len(p0166), 10)
        self.assertEqual(struct.unpack_from("<HHHHH", p0166, 0), (UIPC_BB_MAGIC, UIPC_BB_OPCODE_LUT_TOGGLE, 10, 0x8001, 1))

        # Verify inline (< 48000 B) vs DRAM (> 48000 B) threshold on 0x0165 and 0x0166 off
        p_inline = build_p11_0165_lut_dma_packet(data_size=1024)
        self.assertEqual(struct.unpack_from("<IIIII", p_inline, 16), (1024, 0, 0, 0, 0))
        p_off = build_p11_0166_lut_toggle_packet(enable=False)
        self.assertEqual(struct.unpack_from("<H", p_off, 8)[0], 0)

    def test_bk4_slot_consistency_guard_and_p1_storage_budget(self) -> None:
        # Active User5 without marking slot 5 populated must fail
        with self.assertRaises(CubeLutSanitizationError):
            generate_bk4_lut_slot_properties(active_slot_name="User5", populated_user_slots=(1,))
        self.assertEqual(BKID_APP_SELECT_LUT, 0x02CF1453)

        # 16 full 1.1 MiB User LUTs fit inside /dev/nflasha30 (48 MiB)
        ok_budget = evaluate_p1_nflasha30_storage_budget([1_100_000] * 16)
        self.assertTrue(ok_budget.passed)
        self.assertGreater(ok_budget.remaining_bytes, 30_000_000)

        # > 16 slots or > 2 MiB per slot fails deterministically
        bad_slots = evaluate_p1_nflasha30_storage_budget([1_000_000] * 17)
        self.assertFalse(bad_slots.passed)
        bad_size = evaluate_p1_nflasha30_storage_budget([MAX_SAFE_CUBE_FILE_BYTES + 1])
        self.assertFalse(bad_size.passed)

    def test_domain_input_range_directive_and_trilinear_normalization(self) -> None:
        txt = self._id_17_txt.replace(
            "DOMAIN_MIN 0.000000 0.000000 0.000000\nDOMAIN_MAX 1.000000 1.000000 1.000000",
            "LUT_3D_INPUT_RANGE 0.100000 0.900000",
            1,
        )
        lut = parse_and_sanitize_cube_lut(txt)
        self.assertEqual(lut.domain_min, (0.1, 0.1, 0.1))
        self.assertEqual(lut.domain_max, (0.9, 0.9, 0.9))
        # Midpoint of [0.1, 0.9] is 0.5 -> maps to 0.5 in identity lattice
        sr, sg, sb = trilinear_sample_cube(lut, 0.5, 0.5, 0.5)
        self.assertAlmostEqual(sr, 0.5, places=6)
        self.assertAlmostEqual(sg, 0.5, places=6)
        self.assertAlmostEqual(sb, 0.5, places=6)

    def test_rejects_triplet_before_size_and_duplicate_directives(self) -> None:
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut("0.0 0.0 0.0\nLUT_3D_SIZE 17\n")
        dup_size = self._id_17_txt.replace("LUT_3D_SIZE 17", "LUT_3D_SIZE 17\nLUT_3D_SIZE 17", 1)
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(dup_size)
        bad_cols = self._id_17_txt.replace("0.000000 0.000000 0.000000", "0.000000 0.000000", 1)
        with self.assertRaises(CubeLutSanitizationError):
            parse_and_sanitize_cube_lut(bad_cols)

    def test_pack_33_passthrough_and_invalid_bit_depth_guard(self) -> None:
        lut33 = parse_and_sanitize_cube_lut(build_identity_cube_lut(33, title="ID_33"))
        dma = pack_cube_to_dma_table(lut33, bit_depth=12)
        self.assertEqual(len(dma), LUT_12BIT_U16_BYTES)
        with self.assertRaises(CubeLutSanitizationError):
            pack_cube_to_dma_table(lut33, bit_depth=10)

    def test_builtin_lut_slots_and_p11_disable_descriptor(self) -> None:
        for name, expected_code in (("S709", 0x00), ("R709", 0x01), ("S-Log3", 0x02)):
            code, props = generate_bk4_lut_slot_properties(
                active_slot_name=name, populated_user_slots=()
            )
            self.assertEqual(code, expected_code)
            self.assertEqual(props[BKID_APP_SELECT_LUT], bytes((expected_code,)))
        from fx3_firmware_lab.cube_lut_and_rtmd_verifier import build_p11_mpr_set_lut_descriptor

        off_desc = build_p11_mpr_set_lut_descriptor(
            enable=False, cube_path="", lut_payload_bytes=0
        )
        self.assertEqual(len(off_desc), MPR_SET_LUT_DESCRIPTOR_BYTES)
        self.assertEqual(off_desc[4], 0)


class TestSonyRtmdAndCleanRoomGuards(unittest.TestCase):
    def test_ber_length_short_and_long_roundtrip(self) -> None:
        for val in (0, 64, 127, 128, 255, 1024, 65536):
            enc = encode_ber_length(val)
            dec, next_off = decode_ber_length(enc + b"\xaa", 0)
            self.assertEqual(dec, val)
            self.assertEqual(next_off, len(enc))

    def test_rtmd_kvl_packet_build_and_verify_both_base_isos_and_ibis_modes(self) -> None:
        for base_iso, ei, mode, lut in (
            (800, 800, "Off", "S-Cinetone"),
            (800, 1600, "Standard", "User1"),
            (12800, 12800, "Active", "User16"),
        ):
            meta = RtmdFrameMetadata(
                imx510_readout_us=8600,
                base_iso=base_iso,
                ei_index=ei,
                shutter_angle_deg=180.0,
                active_lut_name=lut,
                steadyshot_mode=mode,
                center_lock_energized=True,
                floating_sensor_hazard=False,
                gyro_sample_hz=1000,
                gyro_xyz_mrad_s=(-15, 22, 3),
                accel_xyz_mg=(4, -9, 980),
            )
            pkt = build_rtmd_klv_packet(meta)
            self.assertTrue(pkt.startswith(SMPTE_KLV_UL_PREFIX))
            self.assertEqual(pkt[:16], RTMD_RDD18_ACQUISITION_UL)
            res = parse_and_verify_rtmd_klv_packet(pkt)
            self.assertTrue(res.valid)
            self.assertTrue(res.catalyst_and_gyroflow_coherent)
            self.assertIn(f"0x{RTMD_TAG_IMX510_IBIS_GYRO_E304:04x}", res.parsed_tags_hex)
            self.assertEqual(res.base_iso, base_iso)
            self.assertEqual(res.ei_index, ei)
            self.assertAlmostEqual(res.shutter_angle_deg, 180.0)
            self.assertEqual(res.active_lut_name, lut)
            self.assertEqual(res.steadyshot_mode, mode)
            self.assertTrue(res.center_lock_energized)
            self.assertFalse(res.floating_sensor_hazard)
            self.assertEqual(res.gyro_xyz_mrad_s, (-15, 22, 3))
            self.assertEqual(res.accel_xyz_mg, (4, -9, 980))

    def test_rtmd_rejects_floating_sensor_hazard_and_bad_params(self) -> None:
        with self.assertRaises(RtmdProtocolError):
            build_rtmd_klv_packet(
                RtmdFrameMetadata(
                    imx510_readout_us=8600,
                    base_iso=800,
                    ei_index=800,
                    shutter_angle_deg=180.0,
                    active_lut_name="S-Cinetone",
                    steadyshot_mode="Off",
                    center_lock_energized=False,
                    floating_sensor_hazard=True,
                )
            )
        with self.assertRaises(RtmdProtocolError):
            build_rtmd_klv_packet(
                RtmdFrameMetadata(
                    imx510_readout_us=8600,
                    base_iso=6400,  # Not 800/12800
                    ei_index=6400,
                    shutter_angle_deg=180.0,
                    active_lut_name="S-Cinetone",
                    steadyshot_mode="Standard",
                )
            )

    def test_rtmd_tampered_e304_or_missing_tag_detected(self) -> None:
        pkt = bytearray(
            build_rtmd_klv_packet(
                RtmdFrameMetadata(
                    imx510_readout_us=8600,
                    base_iso=800,
                    ei_index=800,
                    shutter_angle_deg=180.0,
                    active_lut_name="User1",
                    steadyshot_mode="Standard",
                )
            )
        )
        # Flip center_lock_energized byte (offset -31 inside 32B 0xE304 payload) to 0
        pkt[len(pkt) - RTMD_E304_PAYLOAD_BYTES + 1] = 0
        res = parse_and_verify_rtmd_klv_packet(bytes(pkt))
        self.assertFalse(res.valid)
        self.assertFalse(res.catalyst_and_gyroflow_coherent)
        self.assertIn("0xe304 center_lock_energized is False", res.errors)

        # Corrupt SMPTE UL prefix
        bad_ul = b"\x00\x00\x00\x00" + bytes(pkt[4:])
        with self.assertRaises(RtmdProtocolError):
            parse_and_verify_rtmd_klv_packet(bad_ul)

    def test_rtmd_rejects_truncated_ber_and_missing_e304_tag(self) -> None:
        # Packet with UL + 1B length + single 0x3219 tag (missing 0xE304 and others)
        body = struct.pack(">HHI", 0x3219, 4, 8600)
        partial_pkt = RTMD_RDD18_ACQUISITION_UL + encode_ber_length(len(body)) + body
        res = parse_and_verify_rtmd_klv_packet(partial_pkt)
        self.assertFalse(res.valid)
        self.assertFalse(res.catalyst_and_gyroflow_coherent)
        self.assertIn("Missing mandatory RTMD tag 0xe304", res.errors)

        with self.assertRaises(RtmdProtocolError):
            parse_and_verify_rtmd_klv_packet(partial_pkt[:-2])

    def test_rtmd_rejects_invalid_shutter_angle_and_readout_bounds(self) -> None:
        for bad_angle in (0.0, -45.0, 360.5, float("nan")):
            with self.assertRaises(RtmdProtocolError):
                build_rtmd_klv_packet(
                    RtmdFrameMetadata(
                        imx510_readout_us=8600,
                        base_iso=800,
                        ei_index=800,
                        shutter_angle_deg=bad_angle,
                        active_lut_name="S-Cinetone",
                        steadyshot_mode="Standard",
                    )
                )
        for bad_readout in (500, 75000):
            with self.assertRaises(RtmdProtocolError):
                build_rtmd_klv_packet(
                    RtmdFrameMetadata(
                        imx510_readout_us=bad_readout,
                        base_iso=800,
                        ei_index=800,
                        shutter_angle_deg=180.0,
                        active_lut_name="S-Cinetone",
                        steadyshot_mode="Standard",
                    )
                )

    def test_clean_room_forced_deterministic_without_donors(self) -> None:
        r1 = analyze_cube_lut_and_rtmd(clean_room=True)
        r2 = analyze_cube_lut_and_rtmd(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(r2.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r1.all_checks_passed)
        self.assertEqual(r1.report_sha256, r2.report_sha256)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r_env = analyze_cube_lut_and_rtmd()
            self.assertEqual(r_env.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
            self.assertLess(r_env.donor_profiles["fx3_appfw"].file_bytes, 4096)

    def test_fault_injection_missing_nflasha30_and_rdd18(self) -> None:
        bad1 = build_clean_room_lut_rtmd_fixtures(drop_fx3_nflasha30=True)
        rep1 = analyze_cube_lut_and_rtmd(synthetic_overrides=bad1)
        self.assertFalse(rep1.all_checks_passed)
        self.assertIn("/dev/nflasha30", rep1.donor_profiles["fx3_appfw"].missing_markers)

        bad2 = build_clean_room_lut_rtmd_fixtures(drop_libmpr_rdd18=True)
        rep2 = analyze_cube_lut_and_rtmd(synthetic_overrides=bad2)
        self.assertFalse(rep2.all_checks_passed)
        self.assertGreater(len(rep2.donor_profiles["fx6_libmpr"].missing_markers), 0)

    def test_source_read_only_compliance_and_no_embedded_keys(self) -> None:
        src_path = PKG_ROOT / "fx3_firmware_lab" / "cube_lut_and_rtmd_verifier.py"
        src = src_path.read_text(encoding="utf-8")
        for forbidden in ("O_WRONLY", "O_RDWR", '"wb"', "'wb'", "CXD90057_k8", "BEGIN RSA PRIVATE KEY"):
            self.assertNotIn(forbidden, src)

    def test_cli_audit_lut_rtmd_and_audit_all_deterministic(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        p1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-lut-rtmd", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        parsed = json.loads(p1.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")

        buf1 = StringIO()
        with redirect_stdout(buf1):
            rc1 = cli_main(["audit-lut-rtmd", "--clean-room"])
        buf2 = StringIO()
        with redirect_stdout(buf2):
            rc2 = cli_main(["audit-lut-rtmd", "--clean-room"])
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)
        self.assertEqual(buf1.getvalue(), buf2.getvalue())
        self.assertEqual(buf1.getvalue(), p1.stdout)

        all_res = run_audit_all(clean_room=True)
        self.assertTrue(all_res["all_checks_passed"])
        self.assertIn("cube_lut_and_rtmd_audit", all_res)


if __name__ == "__main__":
    unittest.main()
