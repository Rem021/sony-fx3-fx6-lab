#!/usr/bin/env python3
"""Phase 45 Test Suite — IMX510 VSYNC, libmpr XAVC-I/S-I, RTMD 0xE304 & Dual Slot Simulator.

Exercises 28 unit, integration, fault-injection, CLI, and hygiene tests across
BOTH Local Donor (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes,
strictly offline and hardware-free (< 0.8s runtime).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import struct
import subprocess
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import imx510_xavc_cfexpress_pipeline_emulator as p45  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p45.run_phase45_pipeline_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestDonorAuditAndCodecTables(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and IMX510/libmpr tables."""

    def test_01_clean_room_donor_audit_verifies_all_five_marker_groups(self) -> None:
        audit = p45.inspect_recording_pipeline_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.fx6_mxf_mux_present)
        self.assertTrue(audit.fx3_mxf_mux_absent)
        self.assertTrue(audit.open_gate_5016x3344_encoder_absent)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(len(audit.marker_groups), 5)
        for grp in audit.marker_groups:
            self.assertTrue(grp.verified, msg=f"Group {grp.group_id} failed")
            self.assertEqual(grp.missing_markers, ())

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p45.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p45.is_forced_clean_room(env))
        paths = p45.resolve_phase45_donor_paths(env=env)
        for path in paths.values():
            self.assertIn(p45.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p45.inspect_recording_pipeline_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room_fallback(self) -> None:
        if p45.is_forced_clean_room():
            audit = p45.inspect_recording_pipeline_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p45.resolve_phase45_donor_paths()
        if not all(p.is_file() for p in paths.values()):
            audit = p45.inspect_recording_pipeline_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(audit.all_contracts_verified)
            return

        audit = p45.inspect_recording_pipeline_donors()
        self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 6)
        self.assertTrue(audit.fx6_mxf_mux_present)
        self.assertTrue(audit.fx3_mxf_mux_absent)
        self.assertTrue(audit.open_gate_5016x3344_encoder_absent)
        self.assertTrue(audit.all_contracts_verified)

    def test_04_missing_donor_root_falls_back_gracefully_to_clean_room(self) -> None:
        env = {
            p45.ENV_MAC_WORK_ROOT: "/nonexistent_phase45_work_root",
            p45.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase45_main_root",
        }
        audit = p45.inspect_recording_pipeline_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_05_xavc_i_and_xavc_si_share_h422ip_bitrates_and_diverge_at_muxer(self) -> None:
        for res in (p45.RES_DCI_4K, p45.RES_QFHD_4K):
            for fps in ("23.98p", "29.97p", "50p", "59.94p"):
                p_i = p45.resolve_xavc_profile(p45.CODEC_XAVC_I, res, fps)
                p_si = p45.resolve_xavc_profile(p45.CODEC_XAVC_S_I, res, fps)
                self.assertEqual(p_i.bitrate_mbps, p_si.bitrate_mbps)
                self.assertEqual(p_i.mpr_profile_symbol, p_si.mpr_profile_symbol)
                self.assertEqual(p_i.container, "MXF")
                self.assertEqual(p_i.muxer_module, "libXavcMxf")
                self.assertFalse(p_i.fx3_stock_supported)
                self.assertEqual(p_si.container, "MP4")
                self.assertEqual(p_si.muxer_module, "libXavcMp4")
                self.assertTrue(p_si.fx3_stock_supported)

    def test_06_imx510_rational_vsync_timebases_and_sq_hfr_readout(self) -> None:
        self.assertEqual(p45.FRAME_RATE_SPECS["23.98p"].vsync_period_us, 41708)
        self.assertEqual(p45.FRAME_RATE_SPECS["24.00p"].vsync_period_us, 41667)
        self.assertEqual(p45.FRAME_RATE_SPECS["29.97p"].vsync_period_us, 33367)
        self.assertEqual(p45.FRAME_RATE_SPECS["59.94p"].vsync_period_us, 16683)
        self.assertEqual(p45.FRAME_RATE_SPECS["120p"].vsync_period_us, 8342)
        self.assertEqual(p45.FRAME_RATE_SPECS["240p"].vsync_period_us, 4171)

        p_4k120 = p45.resolve_xavc_profile(p45.CODEC_XAVC_I, p45.RES_QFHD_4K, "120p")
        self.assertEqual(p_4k120.bitrate_mbps, 600)
        p_fhd240 = p45.resolve_xavc_profile(p45.CODEC_XAVC_I, p45.RES_FHD_1080P, "240p")
        self.assertEqual(p_fhd240.bitrate_mbps, 222)

    def test_07_invalid_codec_resolution_fps_rejected_cleanly(self) -> None:
        with self.assertRaises(p45.PipelineConfigError):
            p45.resolve_xavc_profile(p45.CODEC_XAVC_S, p45.RES_DCI_4K, "23.98p")
        with self.assertRaises(p45.PipelineConfigError):
            p45.resolve_xavc_profile(p45.CODEC_XAVC_I, p45.RES_DCI_4K, "240p")
        with self.assertRaises(p45.PipelineConfigError):
            p45.resolve_xavc_profile("X_OCN_LT", p45.RES_QFHD_4K, "24.00p")


class TestRtmdE304PacketizerAndOpticalNdLock(unittest.TestCase):
    """Verify SMPTE RDD 18 / Sony RTMD 0xE304+0xE305 packetizer and P4 ND-Clear lock."""

    def test_08_per_frame_rtmd_roundtrip_iso800_lut_active_nd_clear(self) -> None:
        meta = p45.PerFrameRtmdInput(
            frame_index=5,
            vsync_timestamp_us=83415,
            pts_90khz=7507,
            imx510_readout_us=8600,
            base_iso=800,
            ei_index=1600,
            shutter_angle_deg=180.0,
            lut_active=True,
            lut_name="S-Cinetone",
            steadyshot_mode="Active",
            shift_um_xy=(12, -6),
            roll_mdeg=15,
        )
        pkt = p45.build_per_frame_rtmd_packet(meta)
        ver = p45.parse_and_verify_per_frame_rtmd_packet(pkt)
        self.assertTrue(ver.valid)
        self.assertEqual(ver.ul_hex, p45.RTMD_RDD18_ACQUISITION_UL.hex())
        self.assertEqual(ver.frame_index, 5)
        self.assertEqual(ver.vsync_timestamp_us, 83415)
        self.assertEqual(ver.pts_90khz, 7507)
        self.assertEqual(ver.imx510_readout_us, 8600)
        self.assertEqual(ver.base_iso, 800)
        self.assertEqual(ver.ei_index, 1600)
        self.assertAlmostEqual(ver.ei_gain_db, 6.02, places=2)
        self.assertTrue(ver.lut_active)
        self.assertEqual(ver.lut_name, "S-Cinetone")
        self.assertEqual(ver.nd_filter_state, "ND=Clear")
        self.assertTrue(ver.nd_clear_locked)
        self.assertEqual(ver.steadyshot_mode, "Active")
        self.assertTrue(ver.center_lock_energized)
        self.assertFalse(ver.floating_sensor_hazard)
        self.assertEqual(ver.coherence_flags, p45.RTMD_COHERENCE_ALL_OK)
        self.assertEqual(ver.shift_um_xy, (12, -6))
        self.assertEqual(ver.roll_mdeg, 15)

    def test_09_rtmd_high_base_12800_and_lut_bypass(self) -> None:
        meta = p45.PerFrameRtmdInput(
            frame_index=0,
            vsync_timestamp_us=0,
            pts_90khz=0,
            imx510_readout_us=4200,
            base_iso=12800,
            ei_index=6400,
            shutter_angle_deg=90.0,
            lut_active=False,
            lut_name="Bypass",
            steadyshot_mode="Standard",
        )
        ver = p45.parse_and_verify_per_frame_rtmd_packet(p45.build_per_frame_rtmd_packet(meta))
        self.assertTrue(ver.valid)
        self.assertEqual(ver.base_iso, 12800)
        self.assertEqual(ver.ei_index, 6400)
        self.assertAlmostEqual(ver.ei_gain_db, -6.02, places=2)
        self.assertFalse(ver.lut_active)
        self.assertEqual(ver.lut_name, "Bypass")

    def test_10_p4_nd_clear_lock_rejects_non_clear_state(self) -> None:
        with self.assertRaises(p45.OpticalNdLockError):
            p45.validate_p4_nd_clear_lock("ND=1/16", 4, (1, 1))
        with self.assertRaises(p45.OpticalNdLockError):
            p45.validate_p4_nd_clear_lock("ND=Clear", 2, (1, 1))
        with self.assertRaises(p45.OpticalNdLockError):
            p45.RecordingPipelineConfig(nd_filter_state="ND=1/8").validate()

    def test_11_rtmd_rejects_floating_sensor_hazard_and_bad_iso(self) -> None:
        with self.assertRaises(p45.RtmdPacketError):
            p45.build_per_frame_rtmd_packet(
                p45.PerFrameRtmdInput(
                    frame_index=0,
                    vsync_timestamp_us=0,
                    pts_90khz=0,
                    imx510_readout_us=8600,
                    base_iso=800,
                    ei_index=800,
                    shutter_angle_deg=180.0,
                    lut_active=True,
                    lut_name="s709",
                    steadyshot_mode="Active",
                    floating_sensor_hazard=True,
                )
            )
        with self.assertRaises(p45.RtmdPacketError):
            p45.build_per_frame_rtmd_packet(
                p45.PerFrameRtmdInput(
                    frame_index=0,
                    vsync_timestamp_us=0,
                    pts_90khz=0,
                    imx510_readout_us=8600,
                    base_iso=3200,
                    ei_index=3200,
                    shutter_angle_deg=180.0,
                    lut_active=True,
                    lut_name="s709",
                    steadyshot_mode="Active",
                )
            )

    def test_12_rtmd_parser_rejects_corrupt_ul_ber_and_tampered_e304(self) -> None:
        meta = p45.PerFrameRtmdInput(
            frame_index=1,
            vsync_timestamp_us=16683,
            pts_90khz=1502,
            imx510_readout_us=8600,
            base_iso=800,
            ei_index=800,
            shutter_angle_deg=180.0,
            lut_active=True,
            lut_name="User1",
            steadyshot_mode="Active",
        )
        pkt = p45.build_per_frame_rtmd_packet(meta)
        with self.assertRaises(p45.RtmdPacketError):
            p45.parse_and_verify_per_frame_rtmd_packet(b"\x00" * 20)
        with self.assertRaises(p45.RtmdPacketError):
            p45.parse_and_verify_per_frame_rtmd_packet(pkt[:-2])

        # Flip floating_sensor_hazard byte in 0xE304 payload -> invalid verification
        bad_pkt = bytearray(pkt)
        e304_marker = struct.pack(">HH", p45.RTMD_TAG_IMX510_IBIS_GYRO_E304, p45.RTMD_E304_PAYLOAD_BYTES)
        idx = bytes(bad_pkt).find(e304_marker)
        self.assertGreater(idx, 0)
        bad_pkt[idx + 4 + 2] = 1  # floating_sensor_hazard = 1
        ver = p45.parse_and_verify_per_frame_rtmd_packet(bytes(bad_pkt))
        self.assertFalse(ver.valid)
        self.assertTrue(ver.floating_sensor_hazard)


class TestDualSlotRecordingModesAndSpeedClassReject(unittest.TestCase):
    """Verify SIMULTANEOUS, RELAY_AUTO_SWITCH, SORT_PROXY_MAIN & fail-closed SPEED_CLASS_REJECT."""

    def test_13_simultaneous_cfexpress_4k120_xavc_i_600mbps_parity(self) -> None:
        cfg = p45.RecordingPipelineConfig(
            resolution_mode=p45.RES_QFHD_4K,
            fps_label="120p",
            codec_family=p45.CODEC_XAVC_I,
            recording_mode=p45.REC_MODE_SIMULTANEOUS,
            frame_count=10,
            slot_a=p45.SlotConfig("Slot A", p45.SLOT_A_MEDIA_ID, p45.CARD_CFEXPRESS_TYPE_A),
            slot_b=p45.SlotConfig("Slot B", p45.SLOT_B_MEDIA_ID, p45.CARD_CFEXPRESS_TYPE_A),
            force_clean_room=True,
        )
        res = p45.run_recording_pipeline(cfg)
        self.assertTrue(res["recording_accepted"])
        self.assertEqual(res["status"], "RECORDING_OK")
        self.assertEqual(res["xavc_stream"]["bitrate_mbps"], 600)
        self.assertEqual(res["xavc_stream"]["container"], "MXF")
        self.assertEqual(res["frames_recorded"], 10)
        self.assertEqual(res["dropped_frames"], 0)
        self.assertTrue(res["rtmd_all_packets_valid"])
        self.assertTrue(res["simultaneous_slot_parity_ok"])
        self.assertEqual(res["slot_a"]["stream_sha256"], res["slot_b"]["stream_sha256"])
        self.assertEqual(res["slot_a"]["bytes_written"], res["slot_b"]["bytes_written"])
        self.assertEqual(res["redlines"]["cp_mutation_bytes"], 0)
        self.assertEqual(res["redlines"]["physical_device_writes"], 0)

    def test_14_speed_class_reject_4k120_xavc_i_600mbps_on_v30_without_crash(self) -> None:
        cfg = p45.RecordingPipelineConfig(
            resolution_mode=p45.RES_QFHD_4K,
            fps_label="120p",
            codec_family=p45.CODEC_XAVC_I,
            recording_mode=p45.REC_MODE_SIMULTANEOUS,
            frame_count=10,
            slot_a=p45.SlotConfig("Slot A", p45.SLOT_A_MEDIA_ID, p45.CARD_SDXC_V30),
            slot_b=p45.SlotConfig("Slot B", p45.SLOT_B_MEDIA_ID, p45.CARD_CFEXPRESS_TYPE_A),
            force_clean_room=True,
        )
        res = p45.run_recording_pipeline(cfg)
        self.assertFalse(res["recording_accepted"])
        self.assertTrue(res["rejected"])
        self.assertEqual(res["status"], "SPEED_CLASS_REJECT")
        self.assertFalse(res["appfw_crashed"])
        self.assertEqual(res["wdt_resets"], 0)
        self.assertEqual(res["frames_recorded"], 0)
        self.assertEqual(res["slot_a"]["bytes_written"], 0)
        self.assertEqual(res["slot_b"]["bytes_written"], 0)
        self.assertIn("600MBPS_MEDIA_SLOT1", res["caution_id"])
        self.assertEqual(res["redlines"]["cp_mutation_bytes"], 0)
        self.assertEqual(res["redlines"]["wbi_mutation_bytes"], 0)
        self.assertEqual(res["redlines"]["physical_device_writes"], 0)

    def test_15_speed_class_reject_on_v60_slot_b_for_4k_500mbps_xavc_si(self) -> None:
        cfg = p45.RecordingPipelineConfig(
            resolution_mode=p45.RES_DCI_4K,
            fps_label="50p",
            codec_family=p45.CODEC_XAVC_S_I,
            recording_mode=p45.REC_MODE_SIMULTANEOUS,
            frame_count=6,
            slot_a=p45.SlotConfig("Slot A", p45.SLOT_A_MEDIA_ID, p45.CARD_CFEXPRESS_TYPE_A),
            slot_b=p45.SlotConfig("Slot B", p45.SLOT_B_MEDIA_ID, p45.CARD_SDXC_V60),
            force_clean_room=True,
        )
        res = p45.run_recording_pipeline(cfg)
        self.assertEqual(res["status"], "SPEED_CLASS_REJECT")
        self.assertFalse(res["appfw_crashed"])
        self.assertIn("MEDIA_SLOT2", res["caution_id"])

    def test_16_relay_auto_switch_zero_dropped_frames_and_continuous_vsync(self) -> None:
        cfg = p45.RecordingPipelineConfig(
            resolution_mode=p45.RES_DCI_4K,
            fps_label="24.00p",
            codec_family=p45.CODEC_XAVC_I,
            recording_mode=p45.REC_MODE_RELAY_AUTO_SWITCH,
            frame_count=10,
            slot_a=p45.SlotConfig(
                "Slot A",
                p45.SLOT_A_MEDIA_ID,
                p45.CARD_CFEXPRESS_TYPE_A,
                free_bytes=55_000_000,
                relay_low_watermark_bytes=50_000_000,
            ),
            slot_b=p45.SlotConfig("Slot B", p45.SLOT_B_MEDIA_ID, p45.CARD_SDXC_V90),
            force_clean_room=True,
        )
        res = p45.run_recording_pipeline(cfg)
        self.assertTrue(res["recording_accepted"])
        self.assertTrue(res["relay_switched"])
        self.assertGreater(res["relay_switch_frame_index"], 0)
        self.assertGreater(res["slot_a"]["frames_written"], 0)
        self.assertGreater(res["slot_b"]["frames_written"], 0)
        self.assertEqual(res["slot_a"]["frames_written"] + res["slot_b"]["frames_written"], 10)
        self.assertEqual(res["dropped_frames"], 0)
        # Verify monotonic VSYNC timestamps across the relay switch boundary
        ts = [f["vsync_timestamp_us"] for f in res["frames"]]
        self.assertEqual(ts, [i * 41667 for i in range(10)])

    def test_17_relay_starts_on_slot_b_when_slot_a_empty(self) -> None:
        cfg = p45.RecordingPipelineConfig(
            resolution_mode=p45.RES_QFHD_4K,
            fps_label="29.97p",
            codec_family=p45.CODEC_XAVC_S,
            recording_mode=p45.REC_MODE_RELAY_AUTO_SWITCH,
            frame_count=4,
            slot_a=p45.SlotConfig("Slot A", p45.SLOT_A_MEDIA_ID, p45.CARD_EMPTY),
            slot_b=p45.SlotConfig("Slot B", p45.SLOT_B_MEDIA_ID, p45.CARD_SDXC_V60),
            force_clean_room=True,
        )
        res = p45.run_recording_pipeline(cfg)
        self.assertTrue(res["recording_accepted"])
        self.assertTrue(res["relay_switched"])
        self.assertEqual(res["relay_switch_frame_index"], 0)
        self.assertEqual(res["slot_a"]["frames_written"], 0)
        self.assertEqual(res["slot_b"]["frames_written"], 4)

    def test_18_sort_proxy_main_allows_cfexpress_main_plus_v30_proxy(self) -> None:
        cfg = p45.RecordingPipelineConfig(
            resolution_mode=p45.RES_QFHD_4K,
            fps_label="59.94p",
            codec_family=p45.CODEC_XAVC_I,
            recording_mode=p45.REC_MODE_SORT_PROXY_MAIN,
            frame_count=8,
            slot_a=p45.SlotConfig("Slot A", p45.SLOT_A_MEDIA_ID, p45.CARD_CFEXPRESS_TYPE_A),
            slot_b=p45.SlotConfig("Slot B", p45.SLOT_B_MEDIA_ID, p45.CARD_SDXC_V30),
            force_clean_room=True,
        )
        res = p45.run_recording_pipeline(cfg)
        self.assertTrue(res["recording_accepted"])
        self.assertEqual(res["slot_a"]["stream_role"], "MAIN")
        self.assertEqual(res["slot_b"]["stream_role"], "PROXY_HEVC_16MBPS")
        self.assertEqual(res["slot_a"]["frames_written"], 8)
        self.assertEqual(res["slot_b"]["frames_written"], 8)
        self.assertGreater(res["slot_a"]["bytes_written"], res["slot_b"]["bytes_written"])

    def test_19_empty_card_rejects_cleanly_as_no_card_reject(self) -> None:
        cfg = p45.RecordingPipelineConfig(
            recording_mode=p45.REC_MODE_SIMULTANEOUS,
            slot_a=p45.SlotConfig("Slot A", p45.SLOT_A_MEDIA_ID, p45.CARD_CFEXPRESS_TYPE_A),
            slot_b=p45.SlotConfig("Slot B", p45.SLOT_B_MEDIA_ID, p45.CARD_EMPTY),
            force_clean_room=True,
        )
        res = p45.run_recording_pipeline(cfg)
        self.assertFalse(res["recording_accepted"])
        self.assertEqual(res["status"], "NO_CARD_REJECT")
        self.assertFalse(res["appfw_crashed"])
        self.assertEqual(res["caution_id"], "CAUTION_ID_MOVIE_NO_CARD_FACTOR_MEDIA_SLOT2")

    def test_20_xavc_hs_hevc_and_xavc_s_long_gop_modes(self) -> None:
        for codec, expected_sym in (
            (p45.CODEC_XAVC_HS, "HEVC_3840_2160_M42210P"),
            (p45.CODEC_XAVC_S, "AVC200_3840_2160_H422P"),
        ):
            cfg = p45.RecordingPipelineConfig(
                resolution_mode=p45.RES_QFHD_4K,
                fps_label="59.94p",
                codec_family=codec,
                recording_mode=p45.REC_MODE_SIMULTANEOUS,
                frame_count=4,
                slot_a=p45.SlotConfig("Slot A", p45.SLOT_A_MEDIA_ID, p45.CARD_SDXC_V60),
                slot_b=p45.SlotConfig("Slot B", p45.SLOT_B_MEDIA_ID, p45.CARD_SDXC_V60),
                force_clean_room=True,
            )
            res = p45.run_recording_pipeline(cfg)
            self.assertTrue(res["recording_accepted"], msg=f"{codec} failed")
            self.assertEqual(res["xavc_stream"]["mpr_profile_symbol"], expected_sym)
            self.assertEqual(res["xavc_stream"]["container"], "MP4")

    def test_21_fhd_240p_sq_and_smpte_timecode_drop_non_drop(self) -> None:
        res_240 = p45.run_recording_pipeline(
            p45.RecordingPipelineConfig(
                resolution_mode=p45.RES_FHD_1080P,
                fps_label="240p",
                codec_family=p45.CODEC_XAVC_I,
                frame_count=4,
                force_clean_room=True,
            )
        )
        self.assertTrue(res_240["recording_accepted"])
        self.assertEqual(res_240["imx510"]["imx510_readout_us"], 2100)
        self.assertTrue(res_240["imx510"]["is_sq_hfr"])
        self.assertEqual(res_240["frames"][3]["timecode"], "00:00:00;03")

        res_25 = p45.run_recording_pipeline(
            p45.RecordingPipelineConfig(
                resolution_mode=p45.RES_DCI_4K,
                fps_label="25p",
                codec_family=p45.CODEC_XAVC_I,
                frame_count=4,
                force_clean_room=True,
            )
        )
        self.assertEqual(res_25["frames"][3]["timecode"], "00:00:00:03")


class TestStage5CoEmulationIntegrationCliAndHygiene(unittest.TestCase):
    """Verify full Stage 5 audit, co-emulation suite wiring, CLI, and redline hygiene."""

    def test_22_phase45_audit_determinism_and_digest(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p45.run_phase45_pipeline_audit(force_clean_room=True)
        self.assertEqual(r1, r2)
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["redlines"]["cp_mutation_bytes"], 0)
        self.assertEqual(r1["redlines"]["wbi_mutation_bytes"], 0)
        self.assertEqual(r1["redlines"]["physical_device_writes"], 0)

        copy_rep = dict(r1)
        recorded = copy_rep.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy_rep, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_23_coemulation_suite_wires_stage5_and_allows_skip(self) -> None:
        rep_with = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_bt_containment_matrix=False,
                include_phase41_dtb_mhlx=False,
            )
        )
        self.assertTrue(rep_with["all_checks_passed"])
        self.assertIn("stage5_phase45_imx510_xavc", rep_with)
        s5 = rep_with["stage5_phase45_imx510_xavc"]
        self.assertTrue(s5["all_checks_passed"])
        self.assertEqual(s5["cp_mutation_bytes"], 0)
        self.assertEqual(s5["wbi_mutation_bytes"], 0)
        self.assertEqual(s5["physical_device_writes"], 0)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_bt_containment_matrix=False,
                include_phase41_dtb_mhlx=False,
                include_phase45_imx510_xavc=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage5_phase45_imx510_xavc", rep_skip)

    def test_24_coemulation_config_rejects_invalid_recording_or_xavc_combo(self) -> None:
        with self.assertRaises(suite.CoEmulationSuiteError):
            suite.CoEmulationConfig(recording_mode="BAD_MODE").validate()
        with self.assertRaises(suite.CoEmulationSuiteError):
            suite.CoEmulationConfig(
                xavc_codec=p45.CODEC_XAVC_S,
                xavc_resolution=p45.RES_DCI_4K,
                xavc_fps="23.98p",
            ).validate()

    def test_25_suite_cli_skip_phase45_and_xavc_flags(self) -> None:
        buf_skip = io.StringIO()
        with contextlib.redirect_stdout(buf_skip):
            rc = suite.main(["--clean-room", "--skip-phase41", "--skip-phase45", "--json"])
        self.assertEqual(rc, 0)
        rep_skip = json.loads(buf_skip.getvalue())
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage5_phase45_imx510_xavc", rep_skip)

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main(
                [
                    "--clean-room",
                    "--skip-phase41",
                    "--xavc-resolution",
                    "DCI_4K",
                    "--xavc-fps",
                    "23.98p",
                    "--summary",
                ]
            )
        self.assertEqual(rc_sum, 0)
        self.assertIn("xavc=CLEAN_ROOM_SYNTHETIC(XAVC-I@23.98p)", buf_sum.getvalue())

    def test_26_module_cli_subprocess_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "imx510_xavc_cfexpress_pipeline_emulator.py"),
                "--self-test",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema"], p45.PHASE_45_SCHEMA)
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["redlines"]["cp_mutation_bytes"], 0)
        self.assertEqual(payload["redlines"]["physical_device_writes"], 0)

    def test_27_module_cli_summary_and_local_or_clean_mode(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p45.main(["--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 45 IMX510+XAVC+RTMD+SlotA/B", out)
        self.assertIn("rtmd=0xE304", out)
        self.assertIn("nd=ND=Clear", out)
        self.assertIn("v30_reject=SPEED_CLASS_REJECT", out)

    def test_28_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        mod_src = (FX3_VM_DIR / "imx510_xavc_cfexpress_pipeline_emulator.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("os.O_RDONLY", mod_src)
        self.assertNotIn("os.O_WRONLY", mod_src)
        self.assertNotIn("os.O_RDWR", mod_src)
        self.assertNotIn(forbidden_port, mod_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertNotIn("pkill", mod_src)
        self.assertNotIn("killall", mod_src)
        self.assertIn("CP_MUTATION_BYTES = 0", mod_src)
        self.assertIn("WBI_MUTATION_BYTES = 0", mod_src)
        self.assertIn("NVRAM_PERSISTENT_WRITES = 0", mod_src)
        self.assertIn("PHYSICAL_DEVICE_WRITES = 0", mod_src)


if __name__ == "__main__":
    unittest.main()
