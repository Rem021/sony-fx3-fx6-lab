"""Phase 128 Dual-Mode Unit Tests: Virtual Production LED-Volume Brompton/Megapixel
PWM Anti-Banding Fractional ECS Solver, Wired FreeD (D1 29-Byte) Lens/Camera Tracking
Telemetry -> Unreal LiveLink, & P12-Safe Art-Net 4 / sACN Lighting-Cue Shutter Sync.
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
from fx3_firmware_lab.vp_ledwall_ecs_freed_and_artnet_auditor import (
    ARTNET_HEADER,
    ARTNET_OPCODE_OPDMX,
    ARTNET_PROT_VER,
    ARTNET_UDP_PORT,
    ECS_FRACTIONAL_MAX_HZ,
    ECS_FRACTIONAL_MIN_HZ,
    EMOUNT_VP_LENS_PROFILES,
    FORBIDDEN_RF_VP_TRANSPORTS,
    FREED_D1_CHECKSUM_SEED,
    FREED_D1_MESSAGE_TYPE,
    FREED_D1_PACKET_BYTES,
    FREED_DEFAULT_UDP_PORT,
    FX3_APPFW_PHASE128_MARKERS,
    FX3_LENS_COMM_PHASE128_MARKERS,
    FX3_LIBMPR_PHASE128_MARKERS,
    FX3_NS39_PHASE128_LABELS,
    FX3_NS3_PHASE128_LABELS,
    FX6_APPFW_PHASE128_MARKERS,
    FX6_LIBMPR_PHASE128_MARKERS,
    FX6_LIBNET_ETHER_PHASE128_MARKERS,
    FX6_NS1_PHASE128_LABELS,
    FX6_NS2_PHASE128_LABELS,
    IMX510_VP_READOUT_MS_SPECS,
    PHASE_128_SCHEMA,
    PHASE_128_VERSION,
    SACN_ACN_PACKET_ID,
    SACN_PRIORITY_DEFAULT,
    SACN_UDP_PORT,
    WIRED_VP_TRANSPORTS,
    analyze_vp_ledwall_ecs_freed_and_artnet,
    build_artnet_opdmx_packet,
    build_clean_room_vp_ledwall_freed_fixtures,
    build_freed_d1_packet,
    build_sacn_e131_packet,
    compute_freed_d1_checksum,
    evaluate_artnet_sacn_shutter_sync,
    evaluate_freed_livelink_bridge,
    evaluate_phase128_write_guard,
    evaluate_pillar_a_vp_ledwall_ecs_solver,
    evaluate_pillar_b_freed_livelink_bridge,
    evaluate_pillar_c_artnet_sacn_shutter_sync,
    evaluate_pillar_d_zero_mutation_vp_guard,
    map_emount_fiz_to_freed_ticks,
    parse_and_verify_freed_d1_packet,
    parse_artnet_opdmx_packet,
    parse_sacn_e131_packet,
    sacn_universe_multicast_ip,
    solve_vp_ledwall_ecs_shutter,
    vp_ledwall_ecs_freed_and_artnet_report_to_dict,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "vp_ledwall_ecs_freed_and_artnet_auditor.py"
)


class TestVpLedwallEcsFreedAndArtnet(unittest.TestCase):
    """Comprehensive dual-mode tests (40 tests) for the 25th unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_warm_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_vp_ledwall_ecs_freed_and_artnet(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_vp_ledwall_ecs_freed_and_artnet(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_128_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_128_VERSION)
        self.assertTrue(rep.pillar_a_vp_ledwall_ecs_solver.passed)
        self.assertTrue(rep.pillar_b_freed_livelink_bridge.passed)
        self.assertTrue(rep.pillar_c_artnet_sacn_shutter_sync.passed)
        self.assertTrue(rep.pillar_d_zero_mutation_vp_guard.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.08)
        self.assertLess(dt_warm, 0.02)

    def test_02_auto_mode_or_local_donor_runtime_and_sizes(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_vp_ledwall_ecs_freed_and_artnet()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 0.35)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes.get("fx3_appfw", 0), 70_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_appfw", 0), 45_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx3_libmpr", 0), 3_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libmpr", 0), 25_000_000)
            self.assertEqual(rep.donor_file_sizes.get("fx3_lens_comm", 0), 14_544)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libnet_ether", 0), 100_000)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_vp_ledwall_ecs_freed_and_artnet()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.vp_ledwall_ecs_freed_and_artnet_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_vp_ledwall_ecs_freed_and_artnet(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_no_bytes_repr(self) -> None:
        rep = analyze_vp_ledwall_ecs_freed_and_artnet(clean_room=True)
        payload = vp_ledwall_ecs_freed_and_artnet_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_128_SCHEMA, json_str)

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

    def test_07_package_exports_and_all_include_phase128_symbols(self) -> None:
        expected_symbols = (
            "PHASE_128_SCHEMA",
            "PHASE_128_VERSION",
            "ECS_FRACTIONAL_MIN_HZ",
            "ECS_FRACTIONAL_MAX_HZ",
            "IMX510_VP_READOUT_MS_SPECS",
            "FREED_D1_PACKET_BYTES",
            "FREED_D1_MESSAGE_TYPE",
            "FREED_D1_CHECKSUM_SEED",
            "ARTNET_UDP_PORT",
            "SACN_UDP_PORT",
            "VpLedwallEcsFreedAndArtnetReport",
            "solve_vp_ledwall_ecs_shutter",
            "compute_freed_d1_checksum",
            "build_freed_d1_packet",
            "parse_and_verify_freed_d1_packet",
            "map_emount_fiz_to_freed_ticks",
            "evaluate_freed_livelink_bridge",
            "build_artnet_opdmx_packet",
            "parse_artnet_opdmx_packet",
            "sacn_universe_multicast_ip",
            "build_sacn_e131_packet",
            "parse_sacn_e131_packet",
            "evaluate_artnet_sacn_shutter_sync",
            "evaluate_phase128_write_guard",
            "evaluate_pillar_a_vp_ledwall_ecs_solver",
            "evaluate_pillar_b_freed_livelink_bridge",
            "evaluate_pillar_c_artnet_sacn_shutter_sync",
            "evaluate_pillar_d_zero_mutation_vp_guard",
            "build_clean_room_vp_ledwall_freed_fixtures",
            "analyze_vp_ledwall_ecs_freed_and_artnet",
            "vp_ledwall_ecs_freed_and_artnet_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing export {sym} on fx3_firmware_lab")
            self.assertIn(sym, lab.__all__, f"Missing {sym} in fx3_firmware_lab.__all__")

    def test_08_clean_room_fixtures_roundtrip_and_uxc_integrity(self) -> None:
        fx = build_clean_room_vp_ledwall_freed_fixtures()
        self.assertEqual(len(fx), 12)
        for key in (
            "fx3_appfw",
            "fx6_appfw",
            "fx3_libmpr",
            "fx6_libmpr",
            "fx3_lens_comm",
            "fx6_libnet_ether",
        ):
            self.assertTrue(fx[key].startswith(b"\x7fELF\x02\x01\x01"))
        parse_global_xdb_buffer(fx["fx3_global_xdb"])
        parse_global_xdb_buffer(fx["fx6_global_xdb"])
        lbl_en, err1 = _extract_uxc_labels(fx["fx3_str_en"], FX3_NS39_PHASE128_LABELS)
        lbl_g, err2 = _extract_uxc_labels(fx["fx3_str_en_g"], FX3_NS3_PHASE128_LABELS)
        lbl_1, err3 = _extract_uxc_labels(fx["fx6_str_en_1"], FX6_NS1_PHASE128_LABELS)
        lbl_2, err4 = _extract_uxc_labels(fx["fx6_str_en_2"], FX6_NS2_PHASE128_LABELS)
        self.assertEqual(err1 + err2 + err3 + err4, ())
        self.assertEqual(lbl_en["0x0004e116"], "Using the lens focal length")
        self.assertEqual(lbl_g["0x000060a8"], "\ue801Anti-flicker Tv Scan")
        self.assertEqual(lbl_1["0x00002077"], "ECS")
        self.assertEqual(lbl_2["0x00004d98"], "ECS Frequency")

    # ---- Pillar A: VP LED-Volume IMX510 & Fractional ECS Anti-Banding Solver ----

    def test_09_brompton_verona_7680hz_8_7ms_ecs_solver_passes(self) -> None:
        ev = solve_vp_ledwall_ecs_shutter(
            led_controller="BROMPTON_TESSERA_SX40",
            readout_mode="4K_24P_60P_FF",
            camera_fps=23.976,
            target_shutter_angle_deg=180.0,
            led_pwm_refresh_hz=7680.0,
            scan_multiplex_ratio=16,
            genlock_spg_locked=True,
        )
        self.assertTrue(ev.valid, ev.errors)
        self.assertEqual(ev.imx510_readout_ms, 8.70)
        self.assertEqual(ev.effective_mux_cycle_hz, 480.0)
        self.assertEqual(ev.harmonic_k_cycles, 10)
        self.assertEqual(ev.solved_ecs_hz, 48.0)
        self.assertEqual(ev.harmonic_error_pct, 0.0)

    def test_10_megapixel_helios_13_2ms_readout_ecs_solver_passes(self) -> None:
        ev = solve_vp_ledwall_ecs_shutter(
            led_controller="MEGAPIXEL_HELIOS",
            readout_mode="OVERSAMPLED_REF_13_2MS",
            camera_fps=24.0,
            target_shutter_angle_deg=180.0,
            led_pwm_refresh_hz=3840.0,
            scan_multiplex_ratio=8,
            genlock_spg_locked=True,
        )
        self.assertTrue(ev.valid, ev.errors)
        self.assertEqual(ev.imx510_readout_ms, 13.20)
        self.assertEqual(ev.effective_mux_cycle_hz, 480.0)
        self.assertEqual(ev.solved_ecs_hz, 48.0)

    def test_11_non_genlock_fractional_ecs_subharmonic_lock_passes(self) -> None:
        ev = solve_vp_ledwall_ecs_shutter(
            led_controller="GENERIC_NON_GENLOCK_LED",
            readout_mode="4K_24P_60P_FF",
            camera_fps=29.97,
            target_shutter_angle_deg=180.0,
            led_pwm_refresh_hz=1920.0,
            scan_multiplex_ratio=8,
            genlock_spg_locked=False,
            candidate_ecs_hz=60.0,
        )
        self.assertTrue(ev.valid, ev.errors)
        self.assertEqual(ev.beat_drift_hz, 0.0)

    def test_12_sub_multiplex_exposure_scanline_banding_blocked(self) -> None:
        ev = solve_vp_ledwall_ecs_shutter(
            led_controller="GENERIC_NON_GENLOCK_LED",
            readout_mode="4K_120P_SQ",
            camera_fps=59.94,
            target_shutter_angle_deg=45.0,
            led_pwm_refresh_hz=1920.0,
            scan_multiplex_ratio=16,
            genlock_spg_locked=False,
            candidate_ecs_hz=480.0,
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "BLOCKED_SUB_MUX_SCANLINE_BANDING")

    def test_13_harmonic_beat_banding_blocked_on_mismatched_ecs(self) -> None:
        ev = solve_vp_ledwall_ecs_shutter(
            led_controller="BROMPTON_TESSERA_SX40",
            readout_mode="4K_24P_60P_FF",
            camera_fps=23.976,
            target_shutter_angle_deg=180.0,
            led_pwm_refresh_hz=3840.0,
            scan_multiplex_ratio=16,
            genlock_spg_locked=True,
            candidate_ecs_hz=53.5,
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "BLOCKED_HARMONIC_BEAT_BANDING")

    def test_14_ecs_out_of_range_and_low_pwm_blocked(self) -> None:
        too_high = solve_vp_ledwall_ecs_shutter(candidate_ecs_hz=8500.0)
        too_low = solve_vp_ledwall_ecs_shutter(candidate_ecs_hz=12.0)
        low_pwm = solve_vp_ledwall_ecs_shutter(led_pwm_refresh_hz=480.0)
        self.assertFalse(too_high.valid)
        self.assertEqual(too_high.status, "BLOCKED_ECS_OUT_OF_RANGE")
        self.assertFalse(too_low.valid)
        self.assertEqual(too_low.status, "BLOCKED_ECS_OUT_OF_RANGE")
        self.assertFalse(low_pwm.valid)
        self.assertEqual(low_pwm.status, "BLOCKED_LED_PWM_OUT_OF_RANGE")

    def test_15_ecs_validation_rejects_bad_inputs(self) -> None:
        with self.assertRaises(ValueError):
            solve_vp_ledwall_ecs_shutter(led_controller="UNKNOWN")
        with self.assertRaises(ValueError):
            solve_vp_ledwall_ecs_shutter(readout_mode="8K_RAW")
        with self.assertRaises(ValueError):
            solve_vp_ledwall_ecs_shutter(scan_multiplex_ratio=12)

    def test_16_pillar_a_solver_report_embeds_real_markers(self) -> None:
        rep = analyze_vp_ledwall_ecs_freed_and_artnet(clean_room=True)
        pa = rep.pillar_a_vp_ledwall_ecs_solver
        self.assertEqual(set(pa.fx3_appfw_ecs_markers), set(FX3_APPFW_PHASE128_MARKERS[:3]))
        self.assertEqual(set(pa.fx6_appfw_ecs_markers), set(FX6_APPFW_PHASE128_MARKERS[:4]))
        self.assertEqual(set(pa.fx3_libmpr_ecs_markers), set(FX3_LIBMPR_PHASE128_MARKERS))
        self.assertEqual(set(pa.fx6_libmpr_ecs_markers), set(FX6_LIBMPR_PHASE128_MARKERS))

    # ---- Pillar B: Wired FreeD (0xD1 29-Byte) & E-Mount LiveLink Bridge ----

    def test_17_freed_d1_29byte_exact_wire_format_and_checksum(self) -> None:
        pkt = build_freed_d1_packet(
            camera_id=7,
            pan_deg=45.25,
            tilt_deg=-12.5,
            roll_deg=1.75,
            pos_x_mm=1250.5,
            pos_y_mm=-840.25,
            pos_z_mm=1820.0,
            zoom_ticks_24bit=0x123456,
            focus_ticks_24bit=0xABCDEF,
            iris_12bit=0x7A5,
            frame_counter_4bit=9,
        )
        self.assertEqual(len(pkt), FREED_D1_PACKET_BYTES)
        self.assertEqual(pkt[0], FREED_D1_MESSAGE_TYPE)
        self.assertEqual(pkt[1], 7)
        self.assertEqual(pkt[28], (FREED_D1_CHECKSUM_SEED - sum(pkt[:28])) & 0xFF)
        self.assertEqual(pkt[28], compute_freed_d1_checksum(pkt[:28]))

        dec = parse_and_verify_freed_d1_packet(pkt)
        self.assertTrue(dec.valid, dec.errors)
        self.assertAlmostEqual(dec.pan_deg, 45.25, places=3)
        self.assertAlmostEqual(dec.tilt_deg, -12.5, places=3)
        self.assertAlmostEqual(dec.roll_deg, 1.75, places=3)
        self.assertAlmostEqual(dec.pos_x_mm, 1250.5, places=1)
        self.assertAlmostEqual(dec.pos_y_mm, -840.25, places=1)
        self.assertAlmostEqual(dec.pos_z_mm, 1820.0, places=1)
        self.assertEqual(dec.zoom_ticks_24bit, 0x123456)
        self.assertEqual(dec.focus_ticks_24bit, 0xABCDEF)
        self.assertEqual(dec.iris_12bit, 0x7A5)
        self.assertEqual(dec.frame_counter_4bit, 9)

    def test_18_freed_d1_corrupt_checksum_length_and_type_blocked(self) -> None:
        bad_csum = build_freed_d1_packet(corrupt_checksum=True)
        d_csum = parse_and_verify_freed_d1_packet(bad_csum)
        self.assertFalse(d_csum.valid)
        self.assertIn("BLOCKED_FREED_D1_CHECKSUM_MISMATCH", d_csum.errors[0])

        d_short = parse_and_verify_freed_d1_packet(bad_csum[:20])
        self.assertFalse(d_short.valid)
        self.assertIn("BLOCKED_FREED_D1_LENGTH_MISMATCH", d_short.errors[0])

        wrong_type = bytes([0xD2]) + bad_csum[1:28]
        wrong_type += bytes([compute_freed_d1_checksum(wrong_type)])
        d_type = parse_and_verify_freed_d1_packet(wrong_type)
        self.assertFalse(d_type.valid)
        self.assertIn("BLOCKED_FREED_D1_MESSAGE_TYPE", d_type.errors[0])

    def test_19_freed_d1_negative_angles_and_positions_signed_24bit_roundtrip(self) -> None:
        pkt = build_freed_d1_packet(
            pan_deg=-179.999,
            tilt_deg=-89.5,
            roll_deg=-45.125,
            pos_x_mm=-50000.0,
            pos_y_mm=-12345.5,
            pos_z_mm=-200.0,
        )
        dec = parse_and_verify_freed_d1_packet(pkt)
        self.assertTrue(dec.valid, dec.errors)
        self.assertAlmostEqual(dec.pan_deg, -179.999, places=3)
        self.assertAlmostEqual(dec.tilt_deg, -89.5, places=3)
        self.assertAlmostEqual(dec.roll_deg, -45.125, places=3)
        self.assertAlmostEqual(dec.pos_x_mm, -50000.0, places=1)
        self.assertAlmostEqual(dec.pos_y_mm, -12345.5, places=1)
        self.assertAlmostEqual(dec.pos_z_mm, -200.0, places=1)

    def test_20_emount_fiz_mapping_monotone_for_zoom_focus_iris(self) -> None:
        z_wide, f_near, i_open = map_emount_fiz_to_freed_ticks(
            lens_id="SEL2470GM2", focal_length_mm=24.0, focus_distance_m=0.30, f_stop=2.8
        )
        z_tele, f_far, i_closed = map_emount_fiz_to_freed_ticks(
            lens_id="SEL2470GM2", focal_length_mm=70.0, focus_distance_m=20.0, f_stop=16.0
        )
        self.assertLess(z_wide, z_tele)
        self.assertLess(f_near, f_far)
        self.assertLess(i_open, i_closed)

    def test_21_freed_livelink_wired_transports_all_pass_with_zero_p12_risk(self) -> None:
        for drv in WIRED_VP_TRANSPORTS:
            ev = evaluate_freed_livelink_bridge(
                lens_id="SEL2470GM2",
                transport_driver=drv,
                p12_airplane_rf_off=True,
                udp_port=FREED_DEFAULT_UDP_PORT,
            )
            self.assertTrue(ev.valid, f"{drv} failed: {ev.errors}")
            self.assertEqual(ev.wf12_00342260_risk, 0)
            self.assertEqual(ev.decoded_packet.packet_bytes_len, 29)

    def test_22_freed_livelink_blocks_wifi_bt_and_unchipped_without_encoder(self) -> None:
        for rf in FORBIDDEN_RF_VP_TRANSPORTS:
            blk = evaluate_freed_livelink_bridge(
                lens_id="SEL2470GM2",
                transport_driver=rf,
                p12_airplane_rf_off=True,
            )
            self.assertFalse(blk.valid)
            self.assertEqual(blk.wf12_00342260_risk, 1)
            self.assertEqual(blk.status, "BLOCKED_P12_RF_OFF_VIOLATION_00342260")

        blk_pl = evaluate_freed_livelink_bridge(
            lens_id="MANUAL_PL_UNCHIPPED",
            external_fiz_encoder=False,
            transport_driver="CDC_NCM_RTL8153",
        )
        self.assertFalse(blk_pl.valid)
        self.assertEqual(blk_pl.status, "BLOCKED_UNCHIPPED_LENS_NO_FIZ_ENCODER")

        ok_pl = evaluate_freed_livelink_bridge(
            lens_id="MANUAL_PL_UNCHIPPED",
            external_fiz_encoder=True,
            transport_driver="CDC_NCM_RTL8153",
        )
        self.assertTrue(ok_pl.valid, ok_pl.errors)

    def test_23_pillar_b_freed_bridge_validates_lens_comm_and_ether_markers(self) -> None:
        rep = analyze_vp_ledwall_ecs_freed_and_artnet(clean_room=True)
        pb = rep.pillar_b_freed_livelink_bridge
        self.assertEqual(set(pb.fx3_lens_comm_markers), set(FX3_LENS_COMM_PHASE128_MARKERS))
        self.assertEqual(set(pb.fx6_libnet_ether_markers), set(FX6_LIBNET_ETHER_PHASE128_MARKERS))

    # ---- Pillar C: Art-Net 4 (UDP 6454) & sACN (E1.31 UDP 5568) Shutter Sync ----

    def test_24_artnet4_opdmx_packet_roundtrip_and_15bit_port_address(self) -> None:
        pkt = build_artnet_opdmx_packet(
            net=5,
            sub_uni=0xA3,
            sequence=42,
            physical=1,
            dmx_channels=(255, 180, 90, 12, 200),  # odd count padded to even 6 slots
        )
        dec = parse_artnet_opdmx_packet(pkt)
        self.assertTrue(dec.valid, dec.errors)
        self.assertEqual(dec.opcode, ARTNET_OPCODE_OPDMX)
        self.assertEqual(dec.protocol_version, ARTNET_PROT_VER)
        self.assertEqual(dec.net, 5)
        self.assertEqual(dec.sub_uni, 0xA3)
        self.assertEqual(dec.port_address_15bit, (5 << 8) | 0xA3)
        self.assertEqual(dec.dmx_length, 6)
        self.assertEqual(dec.dmx_first_4_channels, (255, 180, 90, 12))
        self.assertEqual(ARTNET_UDP_PORT, 6454)

    def test_25_artnet4_rejects_bad_magic_opcode_or_truncated_payload(self) -> None:
        pkt = bytearray(build_artnet_opdmx_packet(dmx_channels=(10, 20, 30, 40)))
        bad_magic = b"FakeNet\x00" + bytes(pkt[8:])
        self.assertFalse(parse_artnet_opdmx_packet(bad_magic).valid)

        bad_op = bytearray(pkt)
        struct.pack_into("<H", bad_op, 8, 0x2000)
        self.assertFalse(parse_artnet_opdmx_packet(bytes(bad_op)).valid)

        self.assertFalse(parse_artnet_opdmx_packet(bytes(pkt[:12])).valid)

    def test_26_sacn_e131_packet_roundtrip_and_multicast_ip(self) -> None:
        self.assertEqual(SACN_UDP_PORT, 5568)
        self.assertEqual(sacn_universe_multicast_ip(1), "239.255.0.1")
        self.assertEqual(sacn_universe_multicast_ip(258), "239.255.1.2")
        self.assertEqual(sacn_universe_multicast_ip(63999), "239.255.249.255")

        pkt = build_sacn_e131_packet(
            universe=513,
            priority=150,
            sequence=99,
            sync_universe=100,
            source_name="FX3-STAGEB-DMX",
            dmx_channels=(255, 128, 64, 32),
        )
        self.assertEqual(pkt[4:16], SACN_ACN_PACKET_ID)
        dec = parse_sacn_e131_packet(pkt)
        self.assertTrue(dec.valid, dec.errors)
        self.assertEqual(dec.universe, 513)
        self.assertEqual(dec.priority, 150)
        self.assertEqual(dec.sequence, 99)
        self.assertEqual(dec.sync_universe, 100)
        self.assertEqual(dec.multicast_ip, "239.255.2.1")
        self.assertEqual(dec.source_name, "FX3-STAGEB-DMX")
        self.assertEqual(dec.dmx_length, 4)
        self.assertEqual(dec.dmx_first_4_channels, (255, 128, 64, 32))

    def test_27_sacn_e131_validation_rejects_oob_universe_or_priority(self) -> None:
        with self.assertRaises(ValueError):
            sacn_universe_multicast_ip(0)
        with self.assertRaises(ValueError):
            sacn_universe_multicast_ip(64000)
        with self.assertRaises(ValueError):
            build_sacn_e131_packet(priority=201)
        self.assertFalse(parse_sacn_e131_packet(b"short").valid)

    def test_28_rolling_shutter_mid_readout_flash_tear_blocked(self) -> None:
        # 4.2ms cue phase lands inside 8.7ms IMX510 readout -> top/bottom frame split!
        tear_phase = evaluate_artnet_sacn_shutter_sync(
            protocol="ARTNET_4",
            transport_driver="CDC_NCM_RTL8153",
            readout_mode="4K_24P_60P_FF",
            camera_fps=23.976,
            cue_phase_offset_ms=4.2,
            cue_hold_duration_ms=55.0,
            frame_sync_latched=True,
        )
        self.assertFalse(tear_phase.valid)
        self.assertTrue(tear_phase.rolling_shutter_tear_risk)
        self.assertEqual(tear_phase.status, "BLOCKED_ROLLING_SHUTTER_FLASH_TEAR")

        # Hold shorter than frame_period + readout_ms also causes partial illumination tear
        tear_short = evaluate_artnet_sacn_shutter_sync(
            protocol="SACN_E131",
            transport_driver="CDC_NCM_RTL8153",
            readout_mode="OVERSAMPLED_REF_13_2MS",
            camera_fps=24.0,
            cue_phase_offset_ms=20.0,
            cue_hold_duration_ms=30.0,  # < 41.67 + 13.2 = 54.87ms
            frame_sync_latched=True,
        )
        self.assertFalse(tear_short.valid)
        self.assertTrue(tear_short.rolling_shutter_tear_risk)
        self.assertEqual(tear_short.status, "BLOCKED_ROLLING_SHUTTER_FLASH_TEAR")

    def test_29_unsynced_multi_universe_and_jitter_exceeded_blocked(self) -> None:
        unsynced = evaluate_artnet_sacn_shutter_sync(
            protocol="SACN_E131",
            transport_driver="CDC_NCM_RTL8153",
            cue_phase_offset_ms=20.0,
            cue_hold_duration_ms=55.0,
            frame_sync_latched=False,
            multi_universe_count=6,
        )
        self.assertFalse(unsynced.valid)
        self.assertEqual(unsynced.status, "BLOCKED_UNSYNCED_MULTI_UNIVERSE_DMX")

        jittery = evaluate_artnet_sacn_shutter_sync(
            protocol="ARTNET_4",
            transport_driver="CDC_NCM_RTL8153",
            cue_phase_offset_ms=20.0,
            cue_hold_duration_ms=55.0,
            frame_sync_latched=True,
            sync_jitter_ms=1.75,
        )
        self.assertFalse(jittery.valid)
        self.assertEqual(jittery.status, "BLOCKED_LIGHTING_SYNC_JITTER_EXCEEDED")

    def test_30_lighting_sync_enforces_p12_wifi_off_over_wired_usb_lan(self) -> None:
        for rf in FORBIDDEN_RF_VP_TRANSPORTS:
            blk = evaluate_artnet_sacn_shutter_sync(
                protocol="ARTNET_4",
                transport_driver=rf,
                p12_airplane_rf_off=True,
                cue_phase_offset_ms=20.0,
                cue_hold_duration_ms=55.0,
                frame_sync_latched=True,
            )
            self.assertFalse(blk.valid)
            self.assertEqual(blk.wf12_00342260_risk, 1)
            self.assertEqual(blk.status, "BLOCKED_P12_RF_OFF_VIOLATION_00342260")

    # ---- Pillar D: Volatile RAM Staging & Zero eMMC / Calibration Mutation Guard ----

    def test_31_write_guard_allows_volatile_and_blocks_all_persistent_targets(self) -> None:
        for ok_path in (
            "/tmp/fx3_stageb_vp_ecs.json",
            "ram://freed_d1_cache.bin",
            "memory://artnet_sync_ring",
        ):
            g = evaluate_phase128_write_guard(ok_path)
            self.assertTrue(g.valid, ok_path)
            self.assertEqual(g.emmc_mutation_bytes, 0)
            self.assertEqual(g.calibration_mutation_bytes, 0)

        for bad_path in (
            "/mnt/sd/BODYDATA.DAT",
            "/dev/nflasha15",
            "/dev/cnflasha0",
            "/dev/mmcblk0rpmb",
            "/dev/mtdblock0",
            "p2:/setting/Backup.bin",
            "p2:/setting/psd.bin",
            "p2:/setting/defdet.bin",
            "p6:/tmp/jiritsu",
            "updater://flash",
            "nvram://bk4",
            "eeprom://sensor",
        ):
            g = evaluate_phase128_write_guard(bad_path)
            self.assertFalse(g.valid, bad_path)
            self.assertTrue(g.persistent_write_blocked)
            self.assertEqual(g.emmc_mutation_bytes, 0)
            self.assertEqual(g.calibration_mutation_bytes, 0)

    def test_32_pillar_d_zero_mutation_proof_and_bad_xdb_rejection(self) -> None:
        pd_ok = evaluate_pillar_d_zero_mutation_vp_guard(
            fx3_global_xdb_valid=True,
            fx6_global_xdb_valid=True,
        )
        self.assertTrue(pd_ok.passed)
        self.assertEqual(pd_ok.emmc_mutation_bytes, 0)
        self.assertEqual(pd_ok.calibration_mutation_bytes, 0)
        self.assertFalse(pd_ok.persistent_emmc_writes_authorized)

        pd_bad = evaluate_pillar_d_zero_mutation_vp_guard(
            fx3_global_xdb_valid=False,
            fx6_global_xdb_valid=True,
        )
        self.assertFalse(pd_bad.passed)

    # ---- Negative Donor Integrity Checks ----

    def test_33_missing_elf_markers_fail_closed_per_pillar(self) -> None:
        pa = evaluate_pillar_a_vp_ledwall_ecs_solver(
            fx3_appfw_ecs_markers=(),
            fx6_appfw_ecs_markers=(),
            fx3_libmpr_ecs_markers=(),
            fx6_libmpr_ecs_markers=(),
            uxc_ecs_labels={},
            extra_errors=("Missing FX6 appFw ECS markers",),
        )
        pb = evaluate_pillar_b_freed_livelink_bridge(
            fx3_appfw_lens_markers=(),
            fx6_appfw_lens_markers=(),
            fx3_lens_comm_markers=(),
            fx6_libnet_ether_markers=(),
            uxc_lens_lan_labels={},
            extra_errors=("Missing FX3 LensCommunicator markers",),
        )
        pc = evaluate_pillar_c_artnet_sacn_shutter_sync(
            fx3_appfw_sync_markers=(),
            fx6_libnet_ether_markers=(),
            uxc_airplane_lan_labels={},
            extra_errors=("Missing FX3 appFw Sync markers",),
        )
        self.assertFalse(pa.passed)
        self.assertFalse(pb.passed)
        self.assertFalse(pc.passed)

    # ---- CLI & 25-Auditor Integration ----

    def test_34_cli_audit_vp_ledwall_freed_clean_room_in_process(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-vp-ledwall-freed", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["schema_version"], PHASE_128_SCHEMA)

    def test_35_cli_audit_vp_ledwall_freed_auto_mode_in_process(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-vp-ledwall-freed", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertIn(data["mode"], ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))

    def test_36_run_audit_all_includes_at_least_25_auditors_and_passes(self) -> None:
        summary_clean = run_audit_all(clean_room=True)
        self.assertTrue(summary_clean["all_checks_passed"])
        audit_keys = [k for k in summary_clean if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 25)
        self.assertIn("vp_ledwall_ecs_freed_and_artnet_audit", summary_clean)
        self.assertTrue(summary_clean["vp_ledwall_ecs_freed_and_artnet_audit"]["all_checks_passed"])

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        cli_summary = json.loads(buf.getvalue())
        self.assertTrue(cli_summary["all_checks_passed"])
        cli_audit_keys = [k for k in cli_summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(cli_audit_keys), 25)

    def test_37_imx510_readout_specs_cover_8_7ms_and_13_2ms(self) -> None:
        self.assertEqual(IMX510_VP_READOUT_MS_SPECS["4K_24P_60P_FF"], 8.70)
        self.assertEqual(IMX510_VP_READOUT_MS_SPECS["OVERSAMPLED_REF_13_2MS"], 13.20)
        self.assertEqual(IMX510_VP_READOUT_MS_SPECS["4K_120P_SQ"], 4.35)
        self.assertEqual(IMX510_VP_READOUT_MS_SPECS["FHD_240P_SQ"], 2.20)

    def test_38_ecs_range_constants_cover_23_98_to_7680_hz(self) -> None:
        self.assertEqual(ECS_FRACTIONAL_MIN_HZ, 23.98)
        self.assertEqual(ECS_FRACTIONAL_MAX_HZ, 7680.0)
        ev_min = solve_vp_ledwall_ecs_shutter(
            led_controller="BROMPTON_TESSERA_SX40",
            led_pwm_refresh_hz=7680.0,
            scan_multiplex_ratio=16,
            genlock_spg_locked=True,
            candidate_ecs_hz=24.0,
        )
        ev_max = solve_vp_ledwall_ecs_shutter(
            led_controller="BROMPTON_TESSERA_SX40",
            led_pwm_refresh_hz=7680.0,
            scan_multiplex_ratio=1,
            genlock_spg_locked=True,
            candidate_ecs_hz=7680.0,
        )
        self.assertTrue(ev_min.valid, ev_min.errors)
        self.assertTrue(ev_max.valid, ev_max.errors)

    def test_39_freed_d1_all_lens_profiles_and_max_24bit_clamping(self) -> None:
        for lens_id, (fmin, fmax, apmin, apmax, _chipped) in EMOUNT_VP_LENS_PROFILES.items():
            z, f, i = map_emount_fiz_to_freed_ticks(
                lens_id=lens_id,
                focal_length_mm=(fmin + fmax) * 0.5,
                focus_distance_m=3.0,
                f_stop=(apmin + apmax) * 0.5,
            )
            self.assertTrue(0 <= z <= 0xFFFFFF)
            self.assertTrue(0 <= f <= 0xFFFFFF)
            self.assertTrue(0 <= i <= 0xFFF)

    def test_40_artnet_and_sacn_input_bounds_raise_clean_value_errors(self) -> None:
        with self.assertRaises(ValueError):
            build_artnet_opdmx_packet(net=128)
        with self.assertRaises(ValueError):
            build_artnet_opdmx_packet(sub_uni=256)
        with self.assertRaises(ValueError):
            build_artnet_opdmx_packet(dmx_channels=[0] * 513)
        with self.assertRaises(ValueError):
            evaluate_artnet_sacn_shutter_sync(protocol="DMX_UNKNOWN")
        with self.assertRaises(ValueError):
            evaluate_freed_livelink_bridge(lens_id="UNKNOWN_LENS")
        with self.assertRaises(ValueError):
            evaluate_freed_livelink_bridge(transport_driver="ZIGBEE")


if __name__ == "__main__":
    unittest.main()
