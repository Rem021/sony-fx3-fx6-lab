#!/usr/bin/env python3
"""Phase 99 Test Suite — Stage 16 65^3->33^3 .cube Tetrahedral 3D-LUT DMA Engine,
CEA-861-G HDMI AVI InfoFrame + HDMI-to-12G-SDI ST 2082 REC-Trigger Bridge,
& Sub-Zero (-20C) NP-FZ100 Arrhenius ESR / High-Altitude (5,200m) Thermal Derating HIL.

Exercises 36 fast unit, simulation, fail-closed sanitizer, Stage 16 suite integration,
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
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import lut3d_tetrahedral_subzero_sdi_emulator as p99  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p99.run_phase99_lut3d_subzero_sdi_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase99DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p99.inspect_lut3d_subzero_sdi_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 25)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p99.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p99.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p99.is_forced_clean_room(env))
        paths = p99.resolve_phase99_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p99.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p99.inspect_lut3d_subzero_sdi_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p99.is_forced_clean_room():
            audit = p99.inspect_lut3d_subzero_sdi_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p99.resolve_phase99_donor_paths()
        audit = p99.inspect_lut3d_subzero_sdi_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p99.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p99.ENV_MAC_WORK_ROOT: "/nonexistent_phase99_mac_work_root",
            p99.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase99_main_work_root",
        }
        audit = p99.inspect_lut3d_subzero_sdi_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_plating_zero_and_emmc_locked(self) -> None:
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
        self.assertEqual(red["null_gpio_derefs"], 0)
        self.assertEqual(red["mailbox_stalls"], 0)
        self.assertEqual(red["stock_cp_fault_count"], 0)
        self.assertEqual(red["sdi_transceiver_faults"], 0)
        self.assertEqual(red["lithium_plating_events"], 0)
        self.assertEqual(red["dropped_rec_triggers"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestCubeLutSanitizerAndTetrahedralDma(unittest.TestCase):
    """Verify .cube sanitization, 6-subtetrahedra 65^3/17^3 -> 33^3 resampling & IVSHMEM staging."""

    def test_06_parse_valid_17cube_and_33cube_with_input_range_and_comments(self) -> None:
        txt17 = "# Resolve Export\n" + p99.build_synthetic_cube_text(grid_size=17, title="A7_USER1")
        parsed17 = p99.parse_and_sanitize_cube_lut(txt17, source_name="A7_USER1.cube")
        self.assertEqual(parsed17.grid_size, 17)
        self.assertEqual(len(parsed17.entries), 17**3)
        self.assertEqual(parsed17.title, "A7_USER1")

        txt33 = (
            'TITLE "SLOG3_REC709_33"\n'
            "LUT_3D_SIZE 33\n"
            "LUT_3D_INPUT_RANGE 0.0 1.0\n"
            + "\n".join("0.500000 0.500000 0.500000" for _ in range(33**3))
            + "\n"
        )
        parsed33 = p99.parse_and_sanitize_cube_lut(txt33, source_name="SLOG3_REC709_33.cube")
        self.assertEqual(parsed33.grid_size, 33)
        self.assertEqual(len(parsed33.entries), 33**3)

    def test_07_fail_closed_blocks_nan_inf_1d_and_inverted_domain(self) -> None:
        bad_nan = "LUT_3D_SIZE 17\nNaN 0.0 0.0\n" + "0.1 0.2 0.3\n" * (17**3 - 1)
        bad_inf = "LUT_3D_SIZE 17\ninf 0.0 0.0\n" + "0.1 0.2 0.3\n" * (17**3 - 1)
        bad_1d = "LUT_1D_SIZE 1024\n0.0 0.0 0.0\n"
        bad_inv = (
            "LUT_3D_SIZE 17\nDOMAIN_MIN 1.0 0.0 0.0\nDOMAIN_MAX 0.0 1.0 1.0\n"
            + "0.5 0.5 0.5\n" * (17**3)
        )
        bad_range = "LUT_3D_SIZE 17\nLUT_3D_INPUT_RANGE 1.0 0.5\n" + "0.5 0.5 0.5\n" * (17**3)
        for bad in (bad_nan, bad_inf, bad_1d, bad_inv, bad_range):
            with self.assertRaises(p99.CubeLutSanitizationError):
                p99.parse_and_sanitize_cube_lut(bad, source_name="bad.cube")

    def test_08_fail_closed_blocks_count_mismatch_missing_header_and_unsafe_paths(self) -> None:
        with self.assertRaises(p99.CubeLutSanitizationError):
            p99.parse_and_sanitize_cube_lut("", source_name="empty.cube")
        with self.assertRaises(p99.CubeLutSanitizationError):
            p99.parse_and_sanitize_cube_lut("0.1 0.2 0.3\n", source_name="noheader.cube")
        with self.assertRaises(p99.CubeLutSanitizationError):
            p99.parse_and_sanitize_cube_lut("LUT_3D_SIZE 17\n0.1 0.2 0.3\n", source_name="short.cube")
        with self.assertRaises(p99.CubeLutSanitizationError):
            p99.parse_and_sanitize_cube_lut("LUT_3D_SIZE 129\n0.1 0.2 0.3\n", source_name="huge.cube")
        with self.assertRaises(p99.CubeLutSanitizationError):
            p99.parse_and_sanitize_cube_lut(
                "LUT_3D_SIZE 17\n",
                source_name="../../dev/nflasha15.cube",
            )
        with self.assertRaises(p99.CubeLutSanitizationError):
            p99.parse_and_sanitize_cube_lut(
                'TITLE "bk4://nflasha"\nLUT_3D_SIZE 17\n' + "0.5 0.5 0.5\n" * (17**3),
                source_name="safe.cube",
            )

    def test_09_fail_closed_blocks_oversized_payload_without_full_allocation(self) -> None:
        oversized = "LUT_3D_SIZE 17\n" + ("#" * (p99.MAX_SAFE_CUBE_FILE_BYTES + 32))
        with self.assertRaises(p99.CubeLutSanitizationError):
            p99.parse_and_sanitize_cube_lut(oversized, source_name="dos.cube")

    def test_10_all_6_subtetrahedra_t1_through_t6_exact_affine_and_neutral_axis(self) -> None:
        affine17 = p99.build_synthetic_cube_lattice(grid_size=17, curve="affine_matrix")
        probes = [
            ((0.73, 0.41, 0.19), "T1"),
            ((0.73, 0.19, 0.41), "T2"),
            ((0.41, 0.19, 0.73), "T3"),
            ((0.41, 0.73, 0.19), "T4"),
            ((0.19, 0.73, 0.41), "T5"),
            ((0.19, 0.41, 0.73), "T6"),
        ]
        seen = set()
        for (r, g, b), expected_tet in probes:
            or_, og_, ob_, tet = p99.tetrahedral_interpolate_rgb(affine17, r, g, b)
            seen.add(tet)
            self.assertEqual(tet, expected_tet)
            er, eg, eb = p99._eval_lut_curve_point(r, g, b, "affine_matrix")
            self.assertLess(max(abs(or_ - er), abs(og_ - eg), abs(ob_ - eb)), 1e-12)
        self.assertEqual(seen, set(p99.ALL_SUBTETRAHEDRA))

        filmic17 = p99.build_synthetic_cube_lattice(grid_size=17, curve="slog3_filmic")
        for g_val in (0.1, 0.33, 0.55, 0.87):
            nr, ng, nb, _ = p99.tetrahedral_interpolate_rgb(filmic17, g_val, g_val, g_val)
            self.assertLess(max(abs(nr - ng), abs(ng - nb)), 1e-12)

    def test_11_resample_65cube_and_17cube_to_exact_33cube_lattice(self) -> None:
        lut17 = p99.build_synthetic_cube_lattice(grid_size=17, curve="affine_matrix")
        res17 = p99.resample_cube_to_33_tetrahedral(lut17)
        self.assertEqual(len(res17), 35_937)
        # Verify corner & center accuracy against exact linear matrix
        r_mid, g_mid, b_mid = res17[16 * 33 * 33 + 16 * 33 + 16]
        er, eg, eb = p99._eval_lut_curve_point(0.5, 0.5, 0.5, "affine_matrix")
        self.assertLess(max(abs(r_mid - er), abs(g_mid - eg), abs(b_mid - eb)), 1e-12)

        lut65 = p99.build_synthetic_cube_lattice(grid_size=65, curve="slog3_filmic")
        res65 = p99.resample_cube_to_33_tetrahedral(lut65)
        self.assertEqual(len(res65), 35_937)
        self.assertEqual(res65[0], lut65.entries[0])
        self.assertEqual(res65[-1], lut65.entries[-1])
        # Stride 2 alignment check: (16, 16, 16) in 33^3 == (32, 32, 32) in 65^3
        self.assertEqual(
            res65[16 * 33 * 33 + 16 * 33 + 16],
            lut65.entries[32 * 65 * 65 + 32 * 65 + 32],
        )

    def test_12_pack_33cube_u8_u16_dma_and_ivshmem_0165_0166_packets(self) -> None:
        lut33 = p99.build_synthetic_cube_lattice(grid_size=33, curve="identity")
        res33 = p99.resample_cube_to_33_tetrahedral(lut33)
        u8 = p99.pack_33cube_dma_table(res33, bit_depth=8)
        u16 = p99.pack_33cube_dma_table(res33, bit_depth=16)
        self.assertEqual(len(u8), 107_812)
        self.assertGreater(len(u8), p99.LUT_DMA_SRAM_REG_THRESHOLD)
        self.assertEqual(u8[-1], 0)
        self.assertEqual(len(u16), 215_622)

        pkt_0165 = p99.build_ivshmem_0165_dma_packet(len(u8))
        pkt_0166 = p99.build_ivshmem_0166_toggle_packet(enable=True, slot_index=3)
        self.assertEqual(len(pkt_0165), 36)
        self.assertEqual(len(pkt_0166), 10)
        self.assertIn("65010000", pkt_0165.hex())
        self.assertIn("6601", pkt_0166.hex())

    def test_13_stage_65cube_into_volatile_ivshmem_and_routing_matrix(self) -> None:
        lut65 = p99.build_synthetic_cube_lattice(grid_size=65, curve="slog3_filmic")
        staged_clean = p99.stage_lut3d_into_volatile_ivshmem(
            lut65,
            source_name="Resolve_65.cube",
            bit_depth=8,
            main_slog3_clean=True,
            proxy_mlut_enabled=True,
            hdmi_clean_feed=True,
            hdmi_raw16_active=False,
        )
        self.assertTrue(staged_clean.passed)
        self.assertEqual(staged_clean.source_grid_size, 65)
        self.assertEqual(staged_clean.target_grid_size, 33)
        self.assertEqual(staged_clean.target_voxel_count, 35_937)
        self.assertEqual(staged_clean.subtetrahedra_exercised, p99.ALL_SUBTETRAHEDRA)
        self.assertTrue(staged_clean.uses_dram_dma_path)
        self.assertTrue(staged_clean.routing_main_slog3_clean)
        self.assertTrue(staged_clean.routing_proxy_mlut_enabled)
        self.assertTrue(staged_clean.routing_hdmi_clean_feed)
        self.assertFalse(staged_clean.routing_hdmi_mlut_applied)
        self.assertEqual(staged_clean.nvram_persistent_writes, 0)
        self.assertFalse(staged_clean.persistent_emmc_writes_authorized)

        # RAW16 overrides HDMI feed to force unbaked clean output even if hdmi_clean_feed=False
        staged_raw16 = p99.stage_lut3d_into_volatile_ivshmem(
            lut65,
            bit_depth=16,
            main_slog3_clean=True,
            proxy_mlut_enabled=True,
            hdmi_clean_feed=False,
            hdmi_raw16_active=True,
        )
        self.assertTrue(staged_raw16.passed)
        self.assertEqual(staged_raw16.dma_table_bytes, 215_622)
        self.assertTrue(staged_raw16.routing_hdmi_clean_feed)
        self.assertFalse(staged_raw16.routing_hdmi_mlut_applied)

        # Attempting to bake LUT into Main S-Log3 internal XAVC stream must fail closed
        with self.assertRaises(p99.CubeLutSanitizationError):
            p99.stage_lut3d_into_volatile_ivshmem(lut65, main_slog3_clean=False)

    def test_14_parse_real_65cube_text_lut_end_to_end(self) -> None:
        # Exercise full text parser on 65^3 (274,625 lines) within fast budget (~60ms)
        txt65 = p99.build_synthetic_cube_text(grid_size=65, title="RESOLVE_65_TEXT")
        parsed65 = p99.parse_and_sanitize_cube_lut(txt65, source_name="RESOLVE_65_TEXT.cube")
        self.assertEqual(parsed65.grid_size, 65)
        self.assertEqual(len(parsed65.entries), 65**3)
        res33 = p99.resample_cube_to_33_tetrahedral(parsed65)
        self.assertEqual(len(res33), 35_937)


class TestHdmiAviAnd12gSdiBridge(unittest.TestCase):
    """Verify CEA-861-G 17B AVI InfoFrame, S-Log3 TRS guard & HDMI->12G-SDI ST 2082 bridge."""

    def test_15_avi_infoframe_is_17_bytes_with_exact_mod256_zero_checksum(self) -> None:
        frame, audit = p99.build_hdmi_avi_infoframe(
            color_format="YCBCR_422",
            bit_depth=10,
            gamut="S_GAMUT3_CINE_SLOG3",
            quantization="LIMITED_LEGAL",
            vic=97,
        )
        self.assertEqual(len(frame), 17)
        self.assertEqual(frame[0], 0x82)
        self.assertEqual(frame[1], 0x02)
        self.assertEqual(frame[2], 0x0D)
        self.assertEqual(sum(frame) & 0xFF, 0)
        self.assertTrue(audit.valid)
        self.assertTrue(audit.checksum_mod256_zero)
        self.assertTrue(audit.slog3_quantization_guard_ok)
        self.assertEqual(audit.vic, 97)

        reparsed = p99.parse_and_verify_hdmi_avi_infoframe(frame)
        self.assertTrue(reparsed.valid)
        self.assertEqual(reparsed.color_format, "YCBCR_422")
        self.assertEqual(reparsed.quantization_label, "LIMITED_LEGAL")

    def test_16_avi_checksum_corruption_and_header_mismatch_raise_error(self) -> None:
        frame, _ = p99.build_hdmi_avi_infoframe()
        corrupt = bytearray(frame)
        corrupt[3] ^= 0x01
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.parse_and_verify_hdmi_avi_infoframe(bytes(corrupt))
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.parse_and_verify_hdmi_avi_infoframe(frame[:10])
        bad_hdr = bytearray(frame)
        bad_hdr[0] = 0x83
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.parse_and_verify_hdmi_avi_infoframe(bytes(bad_hdr))

    def test_17_slog3_quantization_guard_blocks_full_range_trs_collision(self) -> None:
        res_bad = p99.simulate_hdmi_to_12g_sdi_rec_bridge(
            fps_label="59.94p",
            resolution="3840x2160",
            gamut="S_GAMUT3_CINE_SLOG3",
            quantization="FULL_RANGE",
            rec_burst_frames=12,
            inject_illegal_trs_codes=True,
        )
        self.assertFalse(res_bad.passed)
        self.assertFalse(res_bad.slog3_quantization_guard_ok)
        self.assertGreater(res_bad.sdi_trs_collisions, 0)
        self.assertEqual(res_bad.status, "BLOCKED_SLOG3_QUANTIZATION_TRS_HAZARD")

        res_safe = p99.simulate_hdmi_to_12g_sdi_rec_bridge(
            fps_label="59.94p",
            resolution="3840x2160",
            gamut="S_GAMUT3_CINE_SLOG3",
            quantization="LIMITED_LEGAL",
            rec_burst_frames=12,
            inject_illegal_trs_codes=True,
        )
        self.assertTrue(res_safe.passed)
        self.assertTrue(res_safe.slog3_quantization_guard_ok)
        self.assertEqual(res_safe.sdi_trs_collisions, 0)

    def test_18_hdmi_to_12g_sdi_bridge_zero_dropped_rec_triggers_and_rp188_lock(self) -> None:
        for res_label, fps_lbl, exp_df, exp_std, exp_gbps in (
            ("3840x2160", "59.94p", True, "SMPTE_ST_2082_12G_SDI", 11.868),
            ("3840x2160", "29.97p", True, "SMPTE_ST_2081_6G_SDI", 5.934),
            ("3840x2160", "23.98p", False, "SMPTE_ST_2081_6G_SDI", 5.934),
            ("1920x1080", "23.98p", False, "SMPTE_ST_292_1_5G_SDI", 1.4835),
        ):
            res = p99.simulate_hdmi_to_12g_sdi_rec_bridge(
                fps_label=fps_lbl,
                resolution=res_label,
                rec_burst_frames=24,
            )
            self.assertTrue(res.passed, msg=f"Bridge failed for {fps_lbl}")
            self.assertEqual(res.drop_frame, exp_df)
            self.assertEqual(res.sdi_standard, exp_std)
            self.assertEqual(res.sdi_link_gbps, exp_gbps)
            self.assertEqual(res.rec_start_edges_detected, 1)
            self.assertEqual(res.rec_stop_edges_detected, 1)
            self.assertEqual(res.dropped_rec_triggers, 0)
            self.assertEqual(res.rp188_packets_emitted, 56)
            self.assertTrue(res.rp188_ltc_vitc_locked)
            self.assertEqual(res.ltc_vitc_frame_offset, 0)
            self.assertFalse(res.fx3_sdi_bnc_present)
            self.assertEqual(res.sdi_transceiver_faults, 0)

    def test_19_sony_vsif_and_rp188_packet_checksum_and_oui_order(self) -> None:
        vsif = p99.build_sony_rec_vsif_packet(
            rec_active=True,
            transition_edge="RISING_START",
            frame_seq=7,
            tc_hmsf=(1, 2, 3, 4),
            drop_frame=True,
        )
        self.assertEqual(vsif[0], p99.VSIF_INFOFRAME_TYPE_CODE)
        self.assertEqual(vsif[4:7], p99.VSIF_SONY_IEEE_OUI_WIRE)
        self.assertEqual(sum(vsif) & 0xFF, 0)

        rp_ltc = p99.build_rp188_hanc_packet(rec_active=True, tc_hmsf=(1, 2, 3, 4), drop_frame=False)
        rp_vitc = p99.build_rp188_hanc_packet(rec_active=True, tc_hmsf=(1, 2, 3, 4), drop_frame=False, is_vitc=True)
        self.assertEqual(rp_ltc[0], 0x60)
        self.assertEqual(rp_ltc[1], 0x60)
        self.assertEqual(rp_ltc[3], 0x00)
        self.assertEqual(rp_vitc[3], 0x01)
        self.assertEqual(rp_ltc[5:9], rp_vitc[5:9])
        self.assertEqual(sum(rp_ltc[:-1]) & 0xFF, rp_ltc[-1])

    def test_20_bridge_3g_sdi_1080p60_and_invalid_inputs_rejected(self) -> None:
        r_3g = p99.simulate_hdmi_to_12g_sdi_rec_bridge(fps_label="59.94p", resolution="1920x1080")
        self.assertTrue(r_3g.passed)
        self.assertEqual(r_3g.sdi_standard, "SMPTE_ST_424_3G_SDI")
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.simulate_hdmi_to_12g_sdi_rec_bridge(fps_label="99.0p")
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.simulate_hdmi_to_12g_sdi_rec_bridge(rec_burst_frames=1)
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.build_hdmi_avi_infoframe(vic=200)


class TestSubzeroEsrAndHighAltitudeHil(unittest.TestCase):
    """Verify -20C Arrhenius ESR USB-PD hot-handoff & 5,200m altitude convective derating HIL."""

    def test_21_arrhenius_esr_rises_sharply_at_minus_20c(self) -> None:
        esr_25c = p99.compute_arrhenius_esr_ohm(25.0)
        esr_0c = p99.compute_arrhenius_esr_ohm(0.0)
        esr_neg20c = p99.compute_arrhenius_esr_ohm(-20.0)
        self.assertAlmostEqual(esr_25c, 0.175, places=6)
        self.assertGreater(esr_0c, esr_25c * 2.0)
        self.assertGreater(esr_neg20c, 1.0)
        self.assertLess(esr_neg20c, 1.2)

    def test_22_subzero_minus20c_usbpd_9v3a_hot_handoff_prevents_uvlo_and_plating(self) -> None:
        res = p99.simulate_subzero_usbpd_hot_handoff(
            cell_temp_c=-20.0,
            battery_soc_pct=45.0,
            load_watts=8.5,
            usb_pd_9v3a_attached=True,
            request_liion_charge_at_subzero=True,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.would_cross_uvlo_unassisted)
        self.assertLess(res.unassisted_v_term_v, p99.NPFZ100_PMIC_UVLO_CUTOFF_V)
        self.assertTrue(res.hot_handoff_executed)
        self.assertGreater(res.min_bus_voltage_v, p99.NPFZ100_PMIC_UVLO_CUTOFF_V)
        self.assertEqual(res.pmic_uvlo_trips, 0)
        self.assertFalse(res.charging_enabled)
        self.assertTrue(res.charging_blocked_for_plating_prevention)
        self.assertEqual(res.lithium_plating_events, 0)
        self.assertEqual(res.dropped_frames, 0)
        self.assertEqual(res.emmc_corruptions, 0)

    def test_23_subzero_without_usbpd_triggers_graceful_rsv_salvage(self) -> None:
        res = p99.simulate_subzero_usbpd_hot_handoff(
            cell_temp_c=-20.0,
            battery_soc_pct=45.0,
            load_watts=8.5,
            usb_pd_9v3a_attached=False,
            request_liion_charge_at_subzero=True,
            active_recording_frames=240,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.rsv_salvage_triggered)
        self.assertEqual(res.rsv_salvageable_frames, 240)
        self.assertFalse(res.charging_enabled)
        self.assertEqual(res.lithium_plating_events, 0)
        self.assertEqual(res.emmc_corruptions, 0)

    def test_24_room_temp_allows_usbpd_charging_while_minus_1c_blocks(self) -> None:
        warm = p99.simulate_subzero_usbpd_hot_handoff(
            cell_temp_c=22.0,
            battery_soc_pct=45.0,
            load_watts=8.5,
            usb_pd_9v3a_attached=True,
            request_liion_charge_at_subzero=True,
        )
        cold = p99.simulate_subzero_usbpd_hot_handoff(
            cell_temp_c=-1.0,
            battery_soc_pct=45.0,
            load_watts=8.5,
            usb_pd_9v3a_attached=True,
            request_liion_charge_at_subzero=True,
        )
        self.assertTrue(warm.passed)
        self.assertTrue(warm.charging_enabled)
        self.assertFalse(warm.charging_blocked_for_plating_prevention)
        self.assertTrue(cold.passed)
        self.assertFalse(cold.charging_enabled)
        self.assertTrue(cold.charging_blocked_for_plating_prevention)

    def test_25_isa_atmosphere_at_5200m_derates_density_and_pressure(self) -> None:
        p0, rho0, r0 = p99.compute_isa_atmosphere(0.0)
        p52, rho52, r52 = p99.compute_isa_atmosphere(5200.0)
        self.assertAlmostEqual(p0, 101.325, places=3)
        self.assertAlmostEqual(r0, 1.0, places=6)
        self.assertLess(p52, 55.0)
        self.assertGreater(p52, 50.0)
        self.assertLess(rho52, 0.75)
        self.assertAlmostEqual(r52, rho52 / rho0, places=6)

    def test_26_5200m_altitude_boosts_sigma_pwm_and_sheds_ftps_before_t_warn(self) -> None:
        res = p99.simulate_high_altitude_thermal_derating_hil(
            altitude_m=5200.0,
            ambient_temp_c=15.0,
            workload_shooting_watts=5.8,
            ftps_background_watts=1.4,
            allow_ftps_shedding=True,
        )
        self.assertTrue(res.passed)
        self.assertGreater(res.boosted_pwm_pct, res.sea_level_pwm_pct)
        self.assertGreater(res.boosted_fan_rpm, 3000)
        self.assertTrue(res.ftps_background_shed)
        self.assertEqual(res.effective_thermal_watts, 5.8)
        self.assertFalse(res.thermal_warn_tripped)
        self.assertLess(res.cxd90057_peak_temp_c, p99.FX3_BK4_CXD90057_WARN_TEMP_C)
        self.assertEqual(res.dropped_recording_frames, 0)
        self.assertEqual(res.nvram_persistent_writes, 0)

    def test_27_5200m_without_ftps_shedding_in_warm_sunlight_trips_t_warn(self) -> None:
        res = p99.simulate_high_altitude_thermal_derating_hil(
            altitude_m=5200.0,
            ambient_temp_c=24.0,
            workload_shooting_watts=6.2,
            ftps_background_watts=2.4,
            allow_ftps_shedding=False,
        )
        self.assertFalse(res.passed)
        self.assertTrue(res.thermal_warn_tripped)
        self.assertEqual(res.status, "BLOCKED_CXD90057_OVERTEMP_WARN_REACHED")
        self.assertGreaterEqual(res.cxd90057_peak_temp_c, p99.FX3_BK4_CXD90057_WARN_TEMP_C)

    def test_28_invalid_hil_parameters_raise_domain_error(self) -> None:
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.compute_arrhenius_esr_ohm(-90.0)
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.compute_npfz100_ocv_v(105.0)
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.compute_isa_atmosphere(20_000.0)
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.simulate_subzero_usbpd_hot_handoff(load_watts=-1.0)
        with self.assertRaises(p99.Lut3dSubzeroSdiError):
            p99.simulate_high_altitude_thermal_derating_hil(ambient_temp_c=90.0)


class TestStage16SuiteIntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 16 suite integration, CLI flags, determinism & strict hygiene."""

    def test_29_clean_room_audit_digest_reproducible_and_no_bytes_repr(self) -> None:
        rep1 = p99.run_phase99_lut3d_subzero_sdi_audit(force_clean_room=True)
        rep2 = p99.run_phase99_lut3d_subzero_sdi_audit(force_clean_room=True)
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

    def test_30_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--lut-matrix"],
            ["--clean-room", "--sdi-matrix"],
            ["--clean-room", "--hil-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p99.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_31_suite_in_process_stage16_and_skip_phase99_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage16_phase99_lut3d_subzero_sdi", rep_on)
        self.assertTrue(rep_on["stage16_phase99_lut3d_subzero_sdi"]["all_checks_passed"])

        cfg_skip = suite.CoEmulationConfig(force_clean_room=True, include_phase99_lut3d_subzero_sdi=False)
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage16_phase99_lut3d_subzero_sdi", rep_skip)

    def test_32_suite_subprocess_summary_and_skip_phase99_flag(self) -> None:
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
        self.assertIn("lut3d_sdi_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase99",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("lut3d_sdi_hil=", proc_skip.stdout)

    def test_33_source_hygiene_o_rdonly_and_no_write_flags_or_port_8768(self) -> None:
        src = (FX3_VM_DIR / "lut3d_tetrahedral_subzero_sdi_emulator.py").read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("8768", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

    def test_34_terminal_voltage_quadratic_handles_brownout_overload(self) -> None:
        # At extreme overload where V_oc^2 <= 4*P*R, quadratic solver returns 0.0V (collapse)
        self.assertEqual(p99.solve_terminal_voltage_v(6.5, 1.5, 10.0), 0.0)
        self.assertAlmostEqual(p99.solve_terminal_voltage_v(7.5, 0.2, 0.0), 7.5, places=6)

    def test_35_solve_terminal_voltage_positive_under_normal_load(self) -> None:
        v_term = p99.solve_terminal_voltage_v(7.9, 0.175, 8.5)
        self.assertGreater(v_term, 7.6)
        self.assertLess(v_term, 7.9)

    def test_36_no_unexpected_files_or_raw_bytes_in_json_suite_payload(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))


if __name__ == "__main__":
    unittest.main()
