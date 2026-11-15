"""Unit tests for Phase 85 Playback/Thumbnail Presenter (`icx1295`) + `p1` Media Firewall, `ShotMark1/2` (`EssenceMark` XML), and `Push Auto Iris / AE Shift` + `P4` Auto-ND Redirection Auditor.

Executes rapidly in BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.playback_shotmark_and_ae_auditor import (
    AE_SHIFT_MAX_EV,
    AE_SHIFT_MIN_EV,
    CINE_EI_BASE_ISOS,
    CINE_EI_LOCKED_SHUTTER_ANGLE_DEG,
    CUE_REVIEW_SPEEDS,
    FX3_APPFW_AE_IRIS_MARKERS,
    FX3_APPFW_PLAYBACK_FORMAT_MARKERS,
    FX3_APPFW_SHOTMARK_MARKERS,
    FX3_CP_AE_IRIS_MARKERS,
    FX3_LIBMPR_PLAYBACK_MARKERS,
    FX3_LIBMPR_SHOTMARK_MARKERS,
    FX6_APPFW_AE_IRIS_MARKERS,
    FX6_APPFW_PLAYBACK_FORMAT_MARKERS,
    FX6_APPFW_SHOTMARK_MARKERS,
    FX6_CP_AE_IRIS_MARKERS,
    FX6_LIBMPR_PLAYBACK_MARKERS,
    FX6_LIBMPR_SHOTMARK_MARKERS,
    IRIS_EIGHTH_STOP_EV,
    LENS_COMM_AE_IRIS_MARKERS,
    NRTM_NAMESPACE_V220,
    PHASE_85_SCHEMA,
    PHASE_85_VERSION,
    SHOT_MARK_MAX_PER_CLIP,
    SHOT_MARK_SUPPORTED_FPS,
    SLOG3_HIGHLIGHT_CLIP_IRE,
    TARGET_NLE_CONSUMERS,
    VALID_PHOTOMETRY_MODES,
    VALID_SHOT_MARK_TYPES,
    PlaybackShotmarkAndAeReport,
    ShotMarkEntry,
    analyze_playback_shotmark_and_ae,
    apply_shotmark_operations,
    build_clean_room_playback_shotmark_ae_fixtures,
    evaluate_media_format_and_delete_firewall,
    evaluate_playback_shuttle_and_thumbnail,
    evaluate_push_auto_iris_and_ae_shift,
    frame_offset_to_timecode,
    parse_and_verify_essencemark_nrtm_xml,
    playback_shotmark_and_ae_report_to_dict,
    synthesize_essencemark_nrtm_xml,
    verify_zero_calibration_and_emmc_immutability,
)


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActivePlaybackShotmarkAndAe(unittest.TestCase):
    _active_report: Optional[PlaybackShotmarkAndAeReport] = None
    _elapsed_sec: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.monotonic()
        cls._active_report = analyze_playback_shotmark_and_ae()
        cls._elapsed_sec = time.monotonic() - t0

    def test_01_active_mode_passes_o_rdonly_14_artifacts_and_sub_500ms(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertLess(self._elapsed_sec, 0.5)
        self.assertEqual(rep.schema_version, PHASE_85_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_85_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.internal_emmc_format_possible)
        self.assertEqual(rep.calibration_mutation_bytes, 0)
        self.assertEqual(rep.p4_nd_motor_fault_attempts, 0)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 14)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 70_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 45_000_000)
            self.assertGreater(rep.donor_file_sizes["fx3_libmpr"], 3_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_libmpr"], 20_000_000)
            self.assertEqual(rep.donor_file_sizes["fx3_lens_comm"], 14_544)
            self.assertEqual(rep.donor_file_sizes["fx6_lens_comm"], 14_544)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = playback_shotmark_and_ae_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotRegex(encoded, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])

    def test_03_pillar_1_playback_thumbnail_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p1 = rep.pillar_1_playback_thumbnail_firewall
        self.assertTrue(p1.passed)
        self.assertEqual(p1.fx3_appfw_markers, FX3_APPFW_PLAYBACK_FORMAT_MARKERS)
        self.assertEqual(p1.fx6_appfw_markers, FX6_APPFW_PLAYBACK_FORMAT_MARKERS)
        self.assertEqual(p1.fx3_libmpr_markers, FX3_LIBMPR_PLAYBACK_MARKERS)
        self.assertEqual(p1.fx6_libmpr_markers, FX6_LIBMPR_PLAYBACK_MARKERS)
        self.assertFalse(p1.internal_emmc_format_possible)
        self.assertFalse(p1.internal_emmc_delete_possible)
        self.assertEqual(p1.uxc_playback_labels["fx3_protect"], "Protect")
        self.assertEqual(p1.uxc_playback_labels["fx6_thumbnail"], "Thumbnail")
        self.assertEqual(p1.uxc_playback_labels["fx6_format_a"], "Format Media (A)")
        self.assertEqual(p1.uxc_playback_labels["fx6_delete_clip"], "Delete Clip?")

    def test_04_pillar_2_shotmark_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p2 = rep.pillar_2_shotmark_essencemark_xml
        self.assertTrue(p2.passed)
        self.assertEqual(p2.fx3_appfw_markers, FX3_APPFW_SHOTMARK_MARKERS)
        self.assertEqual(p2.fx6_appfw_markers, FX6_APPFW_SHOTMARK_MARKERS)
        self.assertEqual(p2.fx3_libmpr_markers, FX3_LIBMPR_SHOTMARK_MARKERS)
        self.assertEqual(p2.fx6_libmpr_markers, FX6_LIBMPR_SHOTMARK_MARKERS)
        self.assertEqual(p2.uxc_shotmark_labels["fx3_shotmark1"], "Shot Mark1")
        self.assertEqual(p2.uxc_shotmark_labels["fx3_shotmark2"], "Shot Mark2")
        self.assertEqual(p2.uxc_shotmark_labels["fx6_set_shot_mark"], "Set Shot Mark")

    def test_05_pillar_3_and_4_ae_iris_markers_and_zero_mutation(self) -> None:
        rep = self._active_report
        assert rep is not None
        p3 = rep.pillar_3_push_auto_iris_ae_shift
        p4 = rep.pillar_4_zero_mutation_proof
        self.assertTrue(p3.passed)
        self.assertEqual(p3.fx3_appfw_markers, FX3_APPFW_AE_IRIS_MARKERS)
        self.assertEqual(p3.fx6_appfw_markers, FX6_APPFW_AE_IRIS_MARKERS)
        self.assertEqual(p3.fx3_cp_markers, FX3_CP_AE_IRIS_MARKERS)
        self.assertEqual(p3.fx6_cp_markers, FX6_CP_AE_IRIS_MARKERS)
        self.assertEqual(p3.lens_comm_markers, LENS_COMM_AE_IRIS_MARKERS)
        self.assertEqual(p3.p4_nd_motor_fault_attempts, 0)
        self.assertEqual(p3.uxc_ae_iris_labels["fx3_metering_mode"], "Metering Mode")
        self.assertEqual(p3.uxc_ae_iris_labels["fx6_auto_iris"], "Auto Iris")
        self.assertTrue(p4.passed)
        self.assertTrue(p4.fx3_global_xdb_valid)
        self.assertTrue(p4.fx6_global_xdb_valid)
        self.assertEqual(p4.calibration_mutation_bytes, 0)
        self.assertFalse(p4.internal_emmc_format_possible)
        self.assertFalse(p4.persistent_emmc_writes_authorized)


class TestPillar1PlaybackThumbnailAndP1Firewall(unittest.TestCase):
    def test_06_cue_review_shuttle_speeds_1x_2x_5x_15x(self) -> None:
        self.assertEqual(CUE_REVIEW_SPEEDS, (1, 2, 5, 15))
        for direction in ("CUE", "REVIEW"):
            for speed in CUE_REVIEW_SPEEDS:
                res = evaluate_playback_shuttle_and_thumbnail(
                    clip_index=10,
                    total_clips=24,
                    direction=direction,
                    shuttle_speed_x=speed,
                    thumbnail_page_size=9,
                )
                self.assertTrue(res.valid, msg=f"Failed {direction} {speed}x: {res.errors}")
                self.assertEqual(res.thumbnail_page_index, 1)

    def test_07_shuttle_invalid_speed_direction_or_bounds_rejected(self) -> None:
        self.assertFalse(evaluate_playback_shuttle_and_thumbnail(shuttle_speed_x=30).valid)
        self.assertFalse(evaluate_playback_shuttle_and_thumbnail(direction="WARP").valid)
        self.assertFalse(evaluate_playback_shuttle_and_thumbnail(clip_index=20, total_clips=10).valid)
        self.assertFalse(evaluate_playback_shuttle_and_thumbnail(thumbnail_page_size=7).valid)

    def test_08_external_slot_a_and_slot_b_format_and_delete_allowed(self) -> None:
        for slot, dev in (
            ("SLOT_A", "/dev/mmcblk1p1"),
            ("SLOT_A", "/dev/nvme0n1p1"),
            ("SLOT_B", "/dev/mmcblk2p1"),
            ("SLOT_B", "/dev/nvme1n1p1"),
        ):
            fmt = evaluate_media_format_and_delete_firewall(
                operation="FORMAT_QUICK", target_slot=slot, target_device=dev
            )
            self.assertTrue(fmt.valid, msg=f"Errors: {fmt.errors}")
            self.assertTrue(fmt.is_external_media)
            self.assertFalse(fmt.is_internal_emmc_target)
            self.assertFalse(fmt.internal_emmc_format_possible)

            dlt = evaluate_media_format_and_delete_firewall(
                operation="DELETE_CLIP",
                target_slot=slot,
                target_device=dev,
                clip_basename="A001C001_261114_FX30",
            )
            self.assertTrue(dlt.valid, msg=f"Errors: {dlt.errors}")
            self.assertFalse(dlt.internal_emmc_delete_possible)

    def test_09_internal_emmc_p1_blocked_from_format_and_delete(self) -> None:
        for bad_slot, bad_dev in (
            ("INTERNAL_P1", "/dev/mmcblk0p1"),
            ("SLOT_A", "/dev/mmcblk0p1"),
            ("p1:", "/dev/mmcblk0"),
            ("SLOT_B", "/dev/cnflasha1"),
            ("EMMC_INTERNAL", "/dev/nflasha15"),
        ):
            for op in ("FORMAT_QUICK", "FORMAT_FULL", "DELETE_CLIP"):
                res = evaluate_media_format_and_delete_firewall(
                    operation=op,
                    target_slot=bad_slot,
                    target_device=bad_dev,
                    clip_basename="A001C001_261114_FX30",
                )
                self.assertFalse(res.valid, msg=f"{op} on {bad_slot}/{bad_dev} should block")
                self.assertEqual(res.status, "BLOCKED_INTERNAL_EMMC_P1_FIREWALL")
                self.assertTrue(res.is_internal_emmc_target)
                self.assertFalse(res.internal_emmc_format_possible)
                self.assertFalse(res.internal_emmc_delete_possible)
                self.assertEqual(res.emmc_mutation_bytes, 0)

    def test_10_clip_protect_lock_blocks_delete_and_sd_lock_blocks_format(self) -> None:
        prot = evaluate_media_format_and_delete_firewall(
            operation="DELETE_CLIP",
            target_slot="SLOT_A",
            target_device="/dev/mmcblk1p1",
            clip_basename="A001C005_261114_FX30",
            clip_protected=True,
        )
        self.assertFalse(prot.valid)
        self.assertEqual(prot.status, "BLOCKED_CLIP_PROTECT_LOCK_ACTIVE")

        wp = evaluate_media_format_and_delete_firewall(
            operation="FORMAT_FULL",
            target_slot="SLOT_B",
            target_device="/dev/mmcblk2p1",
            media_write_protected=True,
        )
        self.assertFalse(wp.valid)
        self.assertEqual(wp.status, "BLOCKED_MEDIA_WRITE_PROTECTED")


class TestPillar2ShotMarkAndEssenceMarkXml(unittest.TestCase):
    def test_11_frame_offset_to_timecode_across_all_5_framerates(self) -> None:
        self.assertEqual(frame_offset_to_timecode(0, "23.98p", start_tc_frames=86400), "01:00:00:00")
        self.assertEqual(frame_offset_to_timecode(24, "23.98p", start_tc_frames=86400), "01:00:01:00")
        self.assertEqual(frame_offset_to_timecode(25, "25.00p", start_tc_frames=0), "00:00:01:00")
        self.assertEqual(frame_offset_to_timecode(30, "29.97p", start_tc_frames=0), "00:00:01:00")
        self.assertEqual(frame_offset_to_timecode(60, "59.94p", start_tc_frames=0), "00:00:01:00")
        with self.assertRaises(ValueError):
            frame_offset_to_timecode(-1, "24.00p")
        with self.assertRaises(ValueError):
            frame_offset_to_timecode(10, "120.00p")

    def test_12_in_rec_and_in_play_shotmark_add_remove_all_types(self) -> None:
        self.assertEqual(VALID_SHOT_MARK_TYPES, ("_ShotMark1", "_ShotMark2", "OK", "KEEP"))
        ops = (
            {"action": "ADD", "mark_type": "_ShotMark1", "frame_offset": 100, "capture_mode": "IN_REC"},
            {"action": "ADD", "mark_type": "_ShotMark2", "frame_offset": 200, "capture_mode": "IN_REC"},
            {"action": "ADD", "mark_type": "OK", "frame_offset": 300, "capture_mode": "IN_PLAY"},
            {"action": "ADD", "mark_type": "KEEP", "frame_offset": 400, "capture_mode": "IN_PLAY"},
            {"action": "REMOVE", "mark_type": "_ShotMark2", "frame_offset": 200, "capture_mode": "IN_PLAY"},
        )
        res = apply_shotmark_operations(ops, fps_label="24.00p", clip_duration_frames=5000)
        self.assertTrue(res.valid, msg=f"Errors: {res.errors}")
        self.assertEqual(res.mark_count, 3)
        self.assertEqual([e.mark_type for e in res.entries], ["_ShotMark1", "OK", "KEEP"])

    def test_13_shotmark_100_max_capacity_and_bounds_enforced(self) -> None:
        max_ops = [
            {"action": "ADD", "mark_type": "_ShotMark1", "frame_offset": i * 2, "capture_mode": "IN_REC"}
            for i in range(SHOT_MARK_MAX_PER_CLIP)
        ]
        ok_100 = apply_shotmark_operations(max_ops, clip_duration_frames=1000)
        self.assertTrue(ok_100.valid)
        self.assertEqual(ok_100.mark_count, 100)

        over_ops = max_ops + [
            {"action": "ADD", "mark_type": "_ShotMark2", "frame_offset": 500, "capture_mode": "IN_PLAY"}
        ]
        bad_101 = apply_shotmark_operations(over_ops, clip_duration_frames=1000)
        self.assertFalse(bad_101.valid)
        self.assertEqual(bad_101.status, "BLOCKED_SHOT_MARK_CAPACITY_EXCEEDED")

        bad_oob = apply_shotmark_operations(
            [{"action": "ADD", "mark_type": "_ShotMark1", "frame_offset": 1000, "capture_mode": "IN_REC"}],
            clip_duration_frames=1000,
        )
        self.assertFalse(bad_oob.valid)

    def test_14_essencemark_xml_roundtrip_all_5_framerates(self) -> None:
        self.assertEqual(SHOT_MARK_SUPPORTED_FPS, ("23.98p", "24.00p", "25.00p", "29.97p", "59.94p"))
        ops = (
            {"action": "ADD", "mark_type": "_ShotMark1", "frame_offset": 12, "capture_mode": "IN_REC"},
            {"action": "ADD", "mark_type": "_ShotMark2", "frame_offset": 75, "capture_mode": "IN_REC"},
            {"action": "ADD", "mark_type": "OK", "frame_offset": 180, "capture_mode": "IN_PLAY"},
            {"action": "ADD", "mark_type": "KEEP", "frame_offset": 360, "capture_mode": "IN_PLAY"},
        )
        for fps in SHOT_MARK_SUPPORTED_FPS:
            ledger = apply_shotmark_operations(ops, fps_label=fps, clip_duration_frames=7200)
            xml_txt = synthesize_essencemark_nrtm_xml(
                ledger.entries, fps_label=fps, clip_duration_frames=7200
            )
            self.assertIn(NRTM_NAMESPACE_V220, xml_txt)
            self.assertIn("<KlvPacketTable", xml_txt)
            self.assertIn("<EssenceMark", xml_txt)
            self.assertIn('start="75"', xml_txt)
            rt = parse_and_verify_essencemark_nrtm_xml(
                xml_txt, expected_entries=ledger.entries, fps_label=fps, clip_duration_frames=7200
            )
            self.assertTrue(rt.valid, msg=f"Roundtrip failed for {fps}: {rt.errors}")
            self.assertTrue(rt.roundtrip_exact)
            self.assertEqual(rt.klv_packet_count, 4)
            self.assertEqual(rt.essence_mark_count, 4)
            self.assertEqual(rt.nle_consumers, TARGET_NLE_CONSUMERS)

    def test_15_essencemark_xml_rejects_tamper_and_malformed_xml(self) -> None:
        ledger = apply_shotmark_operations(
            ({"action": "ADD", "mark_type": "_ShotMark1", "frame_offset": 48, "capture_mode": "IN_REC"},),
            fps_label="23.98p",
            clip_duration_frames=7200,
        )
        xml_txt = synthesize_essencemark_nrtm_xml(ledger.entries, fps_label="23.98p", clip_duration_frames=7200)
        tampered = xml_txt.replace('start="48"', 'start="49"')
        rt_bad = parse_and_verify_essencemark_nrtm_xml(
            tampered, expected_entries=ledger.entries, fps_label="23.98p", clip_duration_frames=7200
        )
        self.assertFalse(rt_bad.valid)
        self.assertFalse(rt_bad.roundtrip_exact)

        malformed = parse_and_verify_essencemark_nrtm_xml(
            "<NonRealTimeMeta><broken", expected_entries=ledger.entries, fps_label="23.98p"
        )
        self.assertFalse(malformed.valid)
        self.assertEqual(malformed.status, "BLOCKED_MALFORMED_NRTM_XML")


class TestPillar3PushAutoIrisAeShiftAndPhotometry(unittest.TestCase):
    def test_16_cine_ei_redirects_p4_auto_nd_to_push_auto_iris_with_zero_nd_faults(self) -> None:
        for base_iso in CINE_EI_BASE_ISOS:
            ev = evaluate_push_auto_iris_and_ae_shift(
                target_body="ILME-FX3",
                shooting_mode="CINE_EI",
                base_iso_ei=base_iso,
                shutter_angle_deg=CINE_EI_LOCKED_SHUTTER_ANGLE_DEG,
                photometry_mode="MULTI",
                ae_shift_ev=0.0,
                current_f_stop=2.8,
                scene_ev_error=2.0,
                push_auto_requested=True,
                auto_nd_requested=True,
            )
            self.assertTrue(ev.valid, msg=f"Errors: {ev.errors}")
            self.assertEqual(ev.status, "P4_AUTO_ND_REDIRECTED_TO_PUSH_AUTO_IRIS")
            self.assertEqual(ev.ae_actuator, "EMOUNT_PUSH_AUTO_IRIS_1_8_STOP")
            self.assertTrue(ev.p4_auto_nd_redirected)
            self.assertEqual(ev.p4_nd_motor_fault_attempts, 0)
            self.assertTrue(ev.iso_locked)
            self.assertTrue(ev.shutter_angle_locked)
            self.assertAlmostEqual(ev.target_f_stop, 5.6, places=2)
            self.assertEqual(ev.iris_steps_eighth_stop, -16)

    def test_17_eighth_stop_iris_quantization_and_lens_aperture_clamp(self) -> None:
        # 1/8-stop = 0.125 EV step
        ev = evaluate_push_auto_iris_and_ae_shift(
            current_f_stop=2.0,
            min_f_stop=2.0,
            max_f_stop=16.0,
            ae_shift_ev=0.125,
            scene_ev_error=0.0,
        )
        self.assertTrue(ev.valid)
        # Cannot open wider than F2.0 -> clamped cleanly
        self.assertEqual(ev.target_f_stop, 2.0)
        self.assertEqual(ev.iris_steps_eighth_stop, 0)
        self.assertAlmostEqual(ev.residual_ev_error, IRIS_EIGHTH_STOP_EV, places=4)

        step1 = evaluate_push_auto_iris_and_ae_shift(
            current_f_stop=4.0,
            min_f_stop=1.4,
            max_f_stop=22.0,
            ae_shift_ev=-0.125,
            scene_ev_error=0.0,
        )
        self.assertTrue(step1.valid)
        self.assertEqual(step1.iris_steps_eighth_stop, -1)
        self.assertAlmostEqual(step1.applied_ev_delta, -0.125, places=3)

    def test_18_ae_shift_bounds_minus2_to_plus2_ev_and_out_of_range_blocked(self) -> None:
        for shift in (AE_SHIFT_MIN_EV, -1.0, -0.25, 0.0, 0.5, 1.25, AE_SHIFT_MAX_EV):
            ev = evaluate_push_auto_iris_and_ae_shift(ae_shift_ev=shift, current_f_stop=4.0)
            self.assertTrue(ev.valid, msg=f"AE Shift {shift} failed: {ev.errors}")

        for bad_shift in (-2.25, 2.25, 3.0, float("nan"), float("inf")):
            ev = evaluate_push_auto_iris_and_ae_shift(ae_shift_ev=bad_shift)
            self.assertFalse(ev.valid)
            self.assertEqual(ev.status, "BLOCKED_AE_SHIFT_OUT_OF_RANGE")

    def test_19_all_5_photometry_modes_supported_and_invalid_rejected(self) -> None:
        self.assertEqual(
            VALID_PHOTOMETRY_MODES,
            ("MULTI", "CENTER", "SPOT", "ENTIRE_SCREEN_AVG", "HIGHLIGHT"),
        )
        for mode in VALID_PHOTOMETRY_MODES:
            ev = evaluate_push_auto_iris_and_ae_shift(photometry_mode=mode)
            self.assertTrue(ev.valid, msg=f"Photometry {mode} failed: {ev.errors}")
        self.assertFalse(evaluate_push_auto_iris_and_ae_shift(photometry_mode="MATRIX_V2").valid)

    def test_20_highlight_metering_protects_94_ire_slog3_ceiling(self) -> None:
        hl = evaluate_push_auto_iris_and_ae_shift(
            photometry_mode="HIGHLIGHT",
            current_f_stop=2.8,
            ae_shift_ev=0.0,
            scene_ev_error=0.0,
            peak_highlight_ire=102.0,
        )
        self.assertTrue(hl.valid)
        self.assertTrue(hl.highlight_clip_protected)
        self.assertLessEqual(hl.peak_highlight_ire_after, SLOG3_HIGHLIGHT_CLIP_IRE)
        self.assertGreater(hl.target_f_stop, 2.8)

    def test_21_face_eye_priority_in_multi_metering(self) -> None:
        on = evaluate_push_auto_iris_and_ae_shift(
            photometry_mode="MULTI",
            face_eye_detected=True,
            face_eye_priority_in_multi=True,
        )
        self.assertTrue(on.valid)
        self.assertTrue(on.face_eye_priority_active)

        off_spot = evaluate_push_auto_iris_and_ae_shift(
            photometry_mode="SPOT",
            face_eye_detected=True,
            face_eye_priority_in_multi=True,
        )
        self.assertTrue(off_spot.valid)
        self.assertFalse(off_spot.face_eye_priority_active)

    def test_22_cine_ei_enforces_locked_base_iso_and_180_shutter_angle(self) -> None:
        bad_iso = evaluate_push_auto_iris_and_ae_shift(shooting_mode="CINE_EI", base_iso_ei=1600)
        self.assertFalse(bad_iso.valid)

        bad_ang = evaluate_push_auto_iris_and_ae_shift(
            shooting_mode="CINE_EI", base_iso_ei=800, shutter_angle_deg=90.0
        )
        self.assertFalse(bad_ang.valid)

        flex = evaluate_push_auto_iris_and_ae_shift(
            shooting_mode="FLEXIBLE_ISO", base_iso_ei=1600, shutter_angle_deg=90.0
        )
        self.assertTrue(flex.valid)


class TestPillar4ZeroMutationAndCliIntegration(unittest.TestCase):
    def test_23_volatile_shadow_allowed_with_zero_calibration_mutation(self) -> None:
        for p in ("/tmp/fx3_stageb_phase85_shadow.json", "ram://phase85_overlay.json"):
            res = verify_zero_calibration_and_emmc_immutability(
                target_path=p, persistent_emmc_writes_authorized=False
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.volatile_shadow_only)
            self.assertEqual(res.calibration_mutation_bytes, 0)
            self.assertFalse(res.internal_emmc_format_possible)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_24_forbidden_emmc_and_calibration_paths_hard_blocked(self) -> None:
        for bad in (
            "/dev/mmcblk0p1",
            "p1:/boot/kernel",
            "/dev/cnflasha1/cal.bin",
            "/dev/nflasha2/Backup.bin",
            "p2:/psd.bin",
            "p6:Jiritsu",
            "nvram://bk4",
        ):
            res = verify_zero_calibration_and_emmc_immutability(
                target_path=bad, persistent_emmc_writes_authorized=False
            )
            self.assertFalse(res.valid, msg=f"{bad} should be blocked")
            self.assertEqual(res.calibration_mutation_bytes, 0)
            self.assertFalse(res.internal_emmc_format_possible)

        bad_flag = verify_zero_calibration_and_emmc_immutability(
            target_path="/tmp/fx3_stageb_phase85_shadow.json",
            persistent_emmc_writes_authorized=True,
        )
        self.assertFalse(bad_flag.valid)

    def test_25_clean_room_fixtures_complete_and_deterministic(self) -> None:
        fx = build_clean_room_playback_shotmark_ae_fixtures()
        self.assertEqual(len(fx), 14)
        r1 = analyze_playback_shotmark_and_ae(clean_room=True)
        r2 = analyze_playback_shotmark_and_ae(clean_room=True)
        self.assertTrue(r1.all_checks_passed, msg=f"Errors: {r1.errors}")
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_26_missing_donors_gracefully_fall_back_to_clean_room(self) -> None:
        with patch("fx3_firmware_lab.playback_shotmark_and_ae_auditor.resolve_donor_file", return_value=None):
            rep = analyze_playback_shotmark_and_ae()
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_27_cli_in_process_clean_room_and_active(self) -> None:
        buf_cr = StringIO()
        with redirect_stdout(buf_cr):
            rc_cr = cli_main(["audit-playback-shotmark-ae", "--clean-room", "--json"])
        self.assertEqual(rc_cr, 0)
        d_cr = json.loads(buf_cr.getvalue())
        self.assertTrue(d_cr["all_checks_passed"])
        self.assertEqual(d_cr["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")

        buf_act = StringIO()
        with redirect_stdout(buf_act):
            rc_act = cli_main(["audit-playback-shotmark-ae", "--json"])
        self.assertEqual(rc_act, 0)
        d_act = json.loads(buf_act.getvalue())
        self.assertTrue(d_act["all_checks_passed"])

    def test_28_cli_subprocess_deterministic_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-playback-shotmark-ae", "--clean-room", "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
            check=True,
        )
        proc2 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-playback-shotmark-ae", "--clean-room", "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
            check=True,
        )
        self.assertEqual(proc1.stdout, proc2.stdout)
        self.assertTrue(json.loads(proc1.stdout)["all_checks_passed"])

    def test_29_run_audit_all_includes_16_auditors_with_playback_shotmark_ae(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        self.assertIn("playback_shotmark_and_ae_audit", summary)
        self.assertTrue(summary["playback_shotmark_and_ae_audit"]["all_checks_passed"])
        expected_16 = (
            "ufu_container_audit",
            "haita_bk4_feature_audit",
            "uxc_ldec_asset_audit",
            "uxc_multilang_and_font_audit",
            "sensor_codec_compatibility_audit",
            "cube_lut_and_rtmd_audit",
            "wbi_hibdrv_and_elf_abi_audit",
            "global_xdb_and_menu_tree_audit",
            "audio_tc_hdmi_sdi_routing_audit",
            "emount_af_breathing_and_ibis_audit",
            "shutter_ecs_sq_and_tally_audit",
            "wb_color_matrix_and_look_audit",
            "proxy_clipname_and_sidecar_audit",
            "assignable_zoom_ciz_and_fn_audit",
            "falsecolor_lpcm_tc_ub_audit",
            "playback_shotmark_and_ae_audit",
        )
        for key in expected_16:
            self.assertIn(key, summary)

    def test_30_package_exports_present(self) -> None:
        import fx3_firmware_lab

        for sym in (
            "PHASE_85_SCHEMA",
            "PHASE_85_VERSION",
            "CUE_REVIEW_SPEEDS",
            "SHOT_MARK_MAX_PER_CLIP",
            "AE_SHIFT_MIN_EV",
            "AE_SHIFT_MAX_EV",
            "IRIS_EIGHTH_STOP_EV",
            "analyze_playback_shotmark_and_ae",
            "apply_shotmark_operations",
            "evaluate_media_format_and_delete_firewall",
            "evaluate_playback_shuttle_and_thumbnail",
            "evaluate_push_auto_iris_and_ae_shift",
            "parse_and_verify_essencemark_nrtm_xml",
            "synthesize_essencemark_nrtm_xml",
        ):
            self.assertTrue(hasattr(fx3_firmware_lab, sym), msg=f"Missing export {sym}")

    def test_31_static_source_hygiene_o_rdonly_and_zero_secrets(self) -> None:
        src = (PKG_ROOT / "fx3_firmware_lab" / "playback_shotmark_and_ae_auditor.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in ("os.O_WRONLY", "os.O_RDWR", "subprocess", "socket", "CXD90057_k8"):
            self.assertNotIn(forbidden, src)

    def test_32_pillar_evaluators_reject_corrupted_marker_maps(self) -> None:
        from fx3_firmware_lab.playback_shotmark_and_ae_auditor import (
            evaluate_pillar_1_playback_thumbnail_firewall,
            evaluate_pillar_2_shotmark_essencemark,
            evaluate_pillar_3_push_auto_iris_ae,
        )

        empty_map = {
            "fx3_appfw_playback": (),
            "fx6_appfw_playback": (),
            "fx3_libmpr_playback": (),
            "fx6_libmpr_playback": (),
            "fx3_appfw_shotmark": (),
            "fx6_appfw_shotmark": (),
            "fx3_libmpr_shotmark": (),
            "fx6_libmpr_shotmark": (),
            "fx3_appfw_ae_iris": (),
            "fx6_appfw_ae_iris": (),
            "fx3_cp_ae_iris": (),
            "fx6_cp_ae_iris": (),
            "lens_comm_ae_iris": (),
        }
        self.assertFalse(evaluate_pillar_1_playback_thumbnail_firewall(empty_map, {}).passed)
        self.assertFalse(evaluate_pillar_2_shotmark_essencemark(empty_map, {}).passed)
        self.assertFalse(evaluate_pillar_3_push_auto_iris_ae(empty_map, {}).passed)

    def test_33_shotmark_duplicate_and_missing_remove_rejected(self) -> None:
        dup = apply_shotmark_operations(
            (
                {"action": "ADD", "mark_type": "_ShotMark1", "frame_offset": 50, "capture_mode": "IN_REC"},
                {"action": "ADD", "mark_type": "_ShotMark1", "frame_offset": 50, "capture_mode": "IN_PLAY"},
            )
        )
        self.assertFalse(dup.valid)

        missing_rm = apply_shotmark_operations(
            ({"action": "REMOVE", "mark_type": "OK", "frame_offset": 50, "capture_mode": "IN_PLAY"},)
        )
        self.assertFalse(missing_rm.valid)

    def test_34_fx6_body_vs_fx3_body_p4_nd_redirection_asymmetry(self) -> None:
        fx3_res = evaluate_push_auto_iris_and_ae_shift(
            target_body="ILME-FX3", shooting_mode="CINE_EI", auto_nd_requested=True
        )
        fx6_res = evaluate_push_auto_iris_and_ae_shift(
            target_body="ILME-FX6", shooting_mode="CINE_EI", auto_nd_requested=True
        )
        self.assertTrue(fx3_res.p4_auto_nd_redirected)
        self.assertEqual(fx3_res.ae_actuator, "EMOUNT_PUSH_AUTO_IRIS_1_8_STOP")
        self.assertFalse(fx6_res.p4_auto_nd_redirected)
        self.assertEqual(fx6_res.ae_actuator, "FX6_AUTO_ND_THEN_IRIS")


if __name__ == "__main__":
    unittest.main()
