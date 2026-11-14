"""Unit tests for Phase 55 Sony E-Mount PZ, 627-Pt PDAF, Focus Breathing & 5-Axis IBIS/OSS Auditor.

Designed to execute rapidly in BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes while keeping the full `fx3-firmware-lab`
suite (>=211 tests) well under 8 seconds.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.emount_af_breathing_and_ibis_auditor import (
    AF_SUBJ_SHIFT_SENS_MAX,
    AF_SUBJ_SHIFT_SENS_MIN,
    AF_TRANSITION_SPEED_MAX,
    AF_TRANSITION_SPEED_MIN,
    CP_SHARED_AF_MARKERS,
    CP_SHARED_BREATHING_MARKERS,
    CP_SHARED_ZOOM_MARKERS,
    EXPECTED_LENS_COMM_BYTES,
    FX3_ACTIVE_IBIS_AP_MARKER,
    FX3_APPFW_AF_EXTRA_MARKERS,
    FX3_APPFW_BREATHING_EXTRA_MARKERS,
    FX3_APPFW_ZOOM_EXTRA_MARKERS,
    FX3_CP_CALIBRATION_FILES,
    FX3_CP_IBIS_SERVO_AND_CALIB_MARKERS,
    FX6_APPFW_AF_EXTRA_MARKERS,
    FX6_APPFW_BREATHING_EXTRA_MARKERS,
    FX6_APPFW_HANDLE_ZOOM_MARKERS,
    FX6_CP_FORBIDDEN_BODY_IBIS_MARKERS,
    FX6_CP_GYRO_ONLY_MARKERS,
    FX6_MPR_UDAM_BREATHING_EXTRA_MARKERS,
    FX6_RIGID_CMOS_MARKER,
    IBIS_CENTER_LOCK_COMPLETION_OPCODE,
    IBIS_CENTER_LOCK_OPCODE,
    MAX_LENS_COMM_COMMENT_DIFF_BYTES,
    MPR_SHARED_GYRO_UDAM_MARKERS,
    MPR_SHARED_UDAM_BREATHING_MARKERS,
    PDAF_POINT_COUNT,
    PHASE_55_SCHEMA,
    PHASE_55_VERSION,
    POWER_ZOOM_SPEED_MAX,
    POWER_ZOOM_SPEED_MIN,
    SHARED_APPFW_AF_MARKERS,
    SHARED_APPFW_BREATHING_MARKERS,
    SHARED_APPFW_STEADYSHOT_MARKERS,
    SHARED_APPFW_ZOOM_MARKERS,
    EmountAfBreathingAndIbisReport,
    analyze_emount_af_breathing_and_ibis,
    build_0x0400_steadyshot_uipc_packet,
    build_clean_room_emount_af_breathing_ibis_fixtures,
    compare_lens_comm_elf64,
    emount_af_breathing_and_ibis_report_to_dict,
    evaluate_emount_power_zoom_routing,
    evaluate_focus_breathing_compensation,
    evaluate_ibis_oss_coordination,
    evaluate_pdaf_af_contract,
)
from fx3_firmware_lab.audio_tc_hdmi_sdi_routing_auditor import (
    FX6_HOTSHOE_MARKERS,
    LIBINFRAHOTSHOE_TMO_SAFE_RC,
    P11_SMART_HANDLE_ATTACHED_EVT,
    P11_SMART_HANDLE_DETACHED_EVT,
)
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveEmountAfBreathingAndIbis(unittest.TestCase):
    _active_report: Optional[EmountAfBreathingAndIbisReport] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._active_report = analyze_emount_af_breathing_and_ibis()

    def test_01_active_mode_passes_with_o_rdonly_and_14_artifacts(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.schema_version, PHASE_55_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_55_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 14)
        self.assertEqual(rep.global_xdb_magics_hex["fx3_global_xdb"], "75786107")
        self.assertEqual(rep.global_xdb_magics_hex["fx6_global_xdb"], "75786107")
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 70_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 45_000_000)
            self.assertEqual(rep.donor_file_sizes["fx3_lens_comm"], EXPECTED_LENS_COMM_BYTES)
            self.assertEqual(rep.donor_file_sizes["fx6_lens_comm"], EXPECTED_LENS_COMM_BYTES)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = emount_af_breathing_and_ibis_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotIn("b'", encoded)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])

    def test_03_pillar_a_zoom_markers_and_smart_grip_absent_safety(self) -> None:
        rep = self._active_report
        assert rep is not None
        pa = rep.pillar_a_power_zoom
        self.assertTrue(pa.passed)
        self.assertTrue(pa.zero_crash_when_smart_grip_absent)
        self.assertEqual(pa.shared_appfw_zoom_markers, SHARED_APPFW_ZOOM_MARKERS)
        self.assertEqual(pa.fx3_appfw_zoom_extra_markers, FX3_APPFW_ZOOM_EXTRA_MARKERS)
        self.assertEqual(pa.fx6_appfw_handle_zoom_markers, FX6_APPFW_HANDLE_ZOOM_MARKERS)
        self.assertEqual(pa.fx6_hotshoe_markers, FX6_HOTSHOE_MARKERS)
        self.assertEqual(pa.handle_absent_tw_fallback_eval.smart_grip_absent_crash_count, 0)
        self.assertEqual(
            pa.handle_absent_tw_fallback_eval.status,
            "SMART_GRIP_ABSENT_FALLBACK_TO_FX3_TW_LEVER",
        )
        self.assertEqual(len(pa.matrix), 4)
        self.assertTrue(all(e.p10_keymap_safe for e in pa.matrix))

    def test_04_pillar_b_lens_comm_elf64_and_pdaf_markers(self) -> None:
        rep = self._active_report
        assert rep is not None
        pb = rep.pillar_b_fast_hybrid_pdaf
        self.assertTrue(pb.passed)
        self.assertEqual(pb.pdaf_point_count, PDAF_POINT_COUNT)
        self.assertTrue(pb.lens_comm_diff.passed)
        self.assertEqual(pb.lens_comm_diff.fx3_bytes, EXPECTED_LENS_COMM_BYTES if rep.mode == "LOCAL_DONOR_VERIFIED" else pb.lens_comm_diff.fx6_bytes)
        self.assertEqual(pb.lens_comm_diff.loadable_segment_diff_bytes, 0)
        self.assertLessEqual(pb.lens_comm_diff.comment_diff_bytes, MAX_LENS_COMM_COMMENT_DIFF_BYTES)
        self.assertEqual(len(pb.lens_comm_diff.text_sha256), 64)
        self.assertEqual(pb.fx3_shared_af_markers, SHARED_APPFW_AF_MARKERS)
        self.assertEqual(pb.fx6_shared_af_markers, SHARED_APPFW_AF_MARKERS)
        self.assertEqual(pb.fx3_extra_af_markers, FX3_APPFW_AF_EXTRA_MARKERS)
        self.assertEqual(pb.fx6_extra_af_markers, FX6_APPFW_AF_EXTRA_MARKERS)
        self.assertEqual(pb.fx3_cp_af_markers, CP_SHARED_AF_MARKERS)
        self.assertEqual(pb.fx6_cp_af_markers, CP_SHARED_AF_MARKERS)
        self.assertEqual(pb.uxc_af_labels_verified["fx6_af_transition_speed"], "AF Transition Speed")
        self.assertEqual(pb.uxc_af_labels_verified["fx6_af_subj_shift_sens"], "AF Subj. Shift Sens.")
        self.assertEqual(pb.uxc_af_labels_verified["fx6_face_eye_af"], "Face/Eye Detection AF")
        self.assertEqual(pb.uxc_af_labels_verified["fx6_focus_map"], "Focus Map")
        self.assertEqual(pb.uxc_af_labels_verified["fx6_focus_magnifier_x4"], "Focus Magnifier ×4")

    def test_05_pillar_c_breathing_comp_udam_and_rtmd_markers(self) -> None:
        rep = self._active_report
        assert rep is not None
        pc = rep.pillar_c_focus_breathing
        self.assertTrue(pc.passed)
        self.assertEqual(pc.fx3_shared_breathing_markers, SHARED_APPFW_BREATHING_MARKERS)
        self.assertEqual(pc.fx6_shared_breathing_markers, SHARED_APPFW_BREATHING_MARKERS)
        self.assertEqual(pc.fx3_extra_breathing_markers, FX3_APPFW_BREATHING_EXTRA_MARKERS)
        self.assertEqual(pc.fx6_extra_breathing_markers, FX6_APPFW_BREATHING_EXTRA_MARKERS)
        self.assertEqual(pc.fx3_cp_breathing_markers, CP_SHARED_BREATHING_MARKERS)
        self.assertEqual(pc.fx6_cp_breathing_markers, CP_SHARED_BREATHING_MARKERS)
        self.assertEqual(pc.fx3_mpr_udam_markers, MPR_SHARED_UDAM_BREATHING_MARKERS)
        self.assertEqual(pc.fx6_mpr_udam_markers, MPR_SHARED_UDAM_BREATHING_MARKERS)
        self.assertEqual(pc.fx6_mpr_udam_extra_markers, FX6_MPR_UDAM_BREATHING_EXTRA_MARKERS)
        self.assertEqual(pc.uxc_breathing_labels_verified["fx6_breathing_compensation"], "Breathing Compensation")
        self.assertEqual(pc.uxc_breathing_labels_verified["fx6_breathing_comp_short"], "Breathing Comp.")
        self.assertTrue(pc.breathing_on_eval.udam_breathing_applied)
        self.assertFalse(pc.breathing_off_eval.udam_breathing_applied)
        self.assertFalse(pc.unsupported_lens_eval.valid)

    def test_06_pillar_d_ibis_oss_and_gyro_calibration_immutability(self) -> None:
        rep = self._active_report
        assert rep is not None
        pd = rep.pillar_d_ibis_oss_calibration
        self.assertTrue(pd.passed)
        self.assertTrue(pd.fx6_rigid_cmos_marker_present)
        self.assertTrue(pd.fx3_rigid_cmos_marker_absent)
        self.assertTrue(pd.fx3_active_ibis_ap_marker_present)
        self.assertTrue(pd.fx6_active_ibis_ap_marker_absent)
        self.assertEqual(pd.calibration_mutation_bytes, 0)
        self.assertEqual(pd.cp_mutation_bytes, 0)
        self.assertEqual(FX3_CP_CALIBRATION_FILES, ("p2:/Backup.bin", "p2:/psd.bin", "p6:Jiritsu"))
        self.assertEqual(pd.fx3_cp_ibis_servo_markers, FX3_CP_IBIS_SERVO_AND_CALIB_MARKERS)
        self.assertEqual(pd.fx6_cp_gyro_only_markers, FX6_CP_GYRO_ONLY_MARKERS)
        self.assertEqual(pd.fx6_cp_unexpected_body_ibis_markers, ())
        self.assertEqual(pd.fx3_mpr_gyro_udam_markers, MPR_SHARED_GYRO_UDAM_MARKERS)
        self.assertEqual(pd.fx6_mpr_gyro_udam_markers, MPR_SHARED_GYRO_UDAM_MARKERS)
        self.assertGreaterEqual(pd.fx3_cp_0x1400_movw_hits, 1)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(pd.fx3_cp_0x1400_movw_hits, 36)
        self.assertEqual(
            pd.uxc_ibis_labels_verified["fx6_steadyshot_fixed_notice"],
            "The SteadyShot mechanism is fixed.",
        )


class TestPillarAPowerZoomContract(unittest.TestCase):
    def test_07_selp_and_tw_lever_valid_speeds_1_to_8(self) -> None:
        for spd in (POWER_ZOOM_SPEED_MIN, 4, POWER_ZOOM_SPEED_MAX):
            res = evaluate_emount_power_zoom_routing(
                zoom_source="SELP_LENS_ROCKER",
                zoom_speed=spd,
                smart_grip_attached=False,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.zoom_speed, spd)
            self.assertEqual(res.active_zoom_control, "EMOUNT_SELP_POWER_ZOOM_LEVER")
            self.assertEqual(res.smart_grip_absent_crash_count, 0)

    def test_08_ciz_limits_4k_15x_and_fhd_20x(self) -> None:
        ok_4k = evaluate_emount_power_zoom_routing(
            zoom_source="CLEAR_IMAGE_ZOOM",
            ciz_enabled=True,
            ciz_magnification=1.5,
            recording_format="4K",
        )
        self.assertTrue(ok_4k.valid)
        self.assertEqual(ok_4k.status, "EMOUNT_PZ_AND_CIZ_READY")

        ok_fhd = evaluate_emount_power_zoom_routing(
            zoom_source="CLEAR_IMAGE_ZOOM",
            ciz_enabled=True,
            ciz_magnification=2.0,
            recording_format="FHD",
        )
        self.assertTrue(ok_fhd.valid)

        bad_4k = evaluate_emount_power_zoom_routing(
            zoom_source="CLEAR_IMAGE_ZOOM",
            ciz_enabled=True,
            ciz_magnification=1.6,
            recording_format="4K",
        )
        self.assertFalse(bad_4k.valid)

        bad_off = evaluate_emount_power_zoom_routing(
            ciz_enabled=False,
            ciz_magnification=1.2,
        )
        self.assertFalse(bad_off.valid)

    def test_09_invalid_zoom_speed_spoofed_handle_and_bad_tmo_rejected(self) -> None:
        bad_spd0 = evaluate_emount_power_zoom_routing(zoom_speed=0)
        self.assertFalse(bad_spd0.valid)
        bad_spd9 = evaluate_emount_power_zoom_routing(zoom_speed=9)
        self.assertFalse(bad_spd9.valid)

        spoofed = evaluate_emount_power_zoom_routing(
            zoom_source="FX6_HANDLE_ROCKER",
            smart_grip_attached=False,
            p11_smart_handle_event_cmd=P11_SMART_HANDLE_ATTACHED_EVT,
        )
        self.assertFalse(spoofed.valid)
        self.assertEqual(spoofed.smart_grip_absent_crash_count, 1)

        bad_tmo = evaluate_emount_power_zoom_routing(hotshoe_tmo_rc=0xFFFF)
        self.assertFalse(bad_tmo.valid)
        self.assertEqual(
            evaluate_emount_power_zoom_routing(
                smart_grip_attached=False,
                p11_smart_handle_event_cmd=P11_SMART_HANDLE_DETACHED_EVT,
                hotshoe_tmo_rc=LIBINFRAHOTSHOE_TMO_SAFE_RC,
            ).smart_grip_absent_crash_count,
            0,
        )


class TestPillarBPdafAndLensCommContract(unittest.TestCase):
    def test_10_pdaf_transition_1_to_7_and_subj_shift_1_to_5(self) -> None:
        ok = evaluate_pdaf_af_contract(
            af_transition_speed=AF_TRANSITION_SPEED_MIN,
            af_subj_shift_sensitivity=AF_SUBJ_SHIFT_SENS_MIN,
            face_eye_mode="FACE_EYE_PRIORITY_AF",
            focus_magnifier="X4",
            peaking_level="HIGH",
            peaking_color="RED",
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.pdaf_points, 627)

        ok_max = evaluate_pdaf_af_contract(
            af_transition_speed=AF_TRANSITION_SPEED_MAX,
            af_subj_shift_sensitivity=AF_SUBJ_SHIFT_SENS_MAX,
            face_eye_mode="FACE_EYE_ONLY_AF",
            focus_magnifier="X6",
            peaking_level="LOW",
            peaking_color="WHITE",
        )
        self.assertTrue(ok_max.valid)

        self.assertFalse(evaluate_pdaf_af_contract(af_transition_speed=0).valid)
        self.assertFalse(evaluate_pdaf_af_contract(af_transition_speed=8).valid)
        self.assertFalse(evaluate_pdaf_af_contract(af_subj_shift_sensitivity=0).valid)
        self.assertFalse(evaluate_pdaf_af_contract(af_subj_shift_sensitivity=6).valid)

    def test_11_pdaf_blocks_stock_cp_mutation_and_invalid_modes(self) -> None:
        bad_cp = evaluate_pdaf_af_contract(cp_mutation_bytes=4)
        self.assertFalse(bad_cp.valid)
        self.assertEqual(bad_cp.status, "BLOCKED_PDAF_OR_CP_MUTATION")
        self.assertTrue(any("cp_mutation_bytes" in e for e in bad_cp.errors))

        self.assertFalse(evaluate_pdaf_af_contract(face_eye_mode="INVALID_EYE").valid)
        self.assertFalse(evaluate_pdaf_af_contract(focus_magnifier="X99").valid)
        self.assertFalse(evaluate_pdaf_af_contract(peaking_level="EXTREME").valid)
        self.assertFalse(evaluate_pdaf_af_contract(peaking_color="GREEN").valid)

    def test_12_compare_lens_comm_elf64_detects_text_mutation(self) -> None:
        fx = build_clean_room_emount_af_breathing_ibis_fixtures(mutate_lens_comm_text=True)
        diff = compare_lens_comm_elf64(fx["fx3_lens_comm"], fx["fx6_lens_comm"])
        self.assertFalse(diff.passed)
        self.assertGreater(diff.loadable_segment_diff_bytes, 0)

        bad_elf = compare_lens_comm_elf64(b"NOT_AN_ELF", fx["fx6_lens_comm"])
        self.assertFalse(bad_elf.passed)


class TestPillarCBreathingCompContract(unittest.TestCase):
    def test_13_breathing_comp_on_calculates_even_cutout_and_udam(self) -> None:
        res = evaluate_focus_breathing_compensation(
            breathing_comp_enabled=True,
            lens_breathing_supported=True,
            active_scan_mode="4K_DCI_4096x2160",
            nominal_fov_crop_factor=1.07,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, "BREATHING_COMP_ACTIVE_UDAM_LOGGED")
        self.assertEqual(res.cut_out_width % 2, 0)
        self.assertEqual(res.cut_out_height % 2, 0)
        self.assertLess(res.cut_out_width, 4096)
        self.assertTrue(res.udam_breathing_applied)
        self.assertTrue(res.udam_distortion_applied)
        self.assertEqual(res.rtmd_klv_tag_count, 7)

    def test_14_breathing_comp_off_and_unsupported_lens_gating(self) -> None:
        off = evaluate_focus_breathing_compensation(
            breathing_comp_enabled=False,
            lens_breathing_supported=True,
            active_scan_mode="IMX510_4264X2408",
            nominal_fov_crop_factor=1.0,
        )
        self.assertTrue(off.valid)
        self.assertEqual(off.status, "BREATHING_COMP_OFF_FULL_FOV")
        self.assertEqual((off.cut_out_width, off.cut_out_height), (4264, 2408))
        self.assertFalse(off.udam_breathing_applied)

        unsup = evaluate_focus_breathing_compensation(
            breathing_comp_enabled=True,
            lens_breathing_supported=False,
        )
        self.assertFalse(unsup.valid)
        self.assertIn("BREATHING_CORRECTION_LENS_TYPE_NOT_SUPPORT", unsup.errors[0])

        bad_crop = evaluate_focus_breathing_compensation(
            breathing_comp_enabled=True,
            lens_breathing_supported=True,
            nominal_fov_crop_factor=1.50,
        )
        self.assertFalse(bad_crop.valid)


class TestPillarDIbisOssCalibrationContract(unittest.TestCase):
    def test_15_0x0400_uipc_packet_encoding_and_opcodes(self) -> None:
        self.assertEqual(IBIS_CENTER_LOCK_OPCODE, 0x0400)
        self.assertEqual(IBIS_CENTER_LOCK_COMPLETION_OPCODE, 0x1400)
        pkt_on = build_0x0400_steadyshot_uipc_packet(is_on=True)
        pkt_off = build_0x0400_steadyshot_uipc_packet(is_on=False)
        self.assertEqual(len(pkt_on), 10)
        self.assertEqual(pkt_on.hex(), "0d2000040a0001800100")
        self.assertEqual(pkt_off.hex(), "0d2000040a0001800000")

    def test_16_fx3_ibis_modes_and_off_center_lock_energized(self) -> None:
        for mode in ("Off", "Standard", "Active"):
            res = evaluate_ibis_oss_coordination(
                target_body="ILME-FX3",
                requested_mode=mode,
                lens_has_oss=True,
                lens_oss_switch_on=True,
                ap_active_extension_enabled=(mode == "Active"),
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.center_lock_energized)
            self.assertFalse(res.floating_sensor_hazard)
            self.assertTrue(res.oss_coordinated)
            self.assertEqual(res.cp_mutation_bytes, 0)
            self.assertEqual(res.calibration_mutation_bytes, 0)
            if mode == "Off":
                self.assertEqual(res.effective_cp_mode, "CenterLock_Energized_IS_Off")
                self.assertEqual(res.opcode_0x0400_packet_hex, "0d2000040a0001800000")

    def test_17_fx6_gyro_metadata_only_and_calibration_immutability_redlines(self) -> None:
        fx6_ok = evaluate_ibis_oss_coordination(
            target_body="ILME-FX6",
            requested_mode="Off",
            physical_5axis_ibis_requested=False,
        )
        self.assertTrue(fx6_ok.valid)
        self.assertEqual(fx6_ok.effective_cp_mode, "FX6_GYRO_METADATA_ONLY_WITH_LENS_OSS")

        fx6_bad = evaluate_ibis_oss_coordination(
            target_body="ILME-FX6",
            requested_mode="Standard",
            physical_5axis_ibis_requested=True,
        )
        self.assertFalse(fx6_bad.valid)

        calib_bad = evaluate_ibis_oss_coordination(calibration_mutation_bytes=16)
        self.assertFalse(calib_bad.valid)
        self.assertEqual(calib_bad.status, "BLOCKED_IBIS_CALIBRATION_OR_STAGE_FAULT")

        cp_bad = evaluate_ibis_oss_coordination(cp_mutation_bytes=2)
        self.assertFalse(cp_bad.valid)


class TestCleanRoomFaultInjectionAndCli(unittest.TestCase):
    def test_18_forced_clean_room_deterministic_equivalence(self) -> None:
        r1 = analyze_emount_af_breathing_and_ibis(clean_room=True)
        r2 = analyze_emount_af_breathing_and_ibis(clean_room=True)
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r1.all_checks_passed, msg=f"Errors: {r1.errors}")
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(len(r1.donor_file_sizes), 14)

    def test_19_env_force_clean_room_and_missing_donor_fallback(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep_env = analyze_emount_af_breathing_and_ibis()
        self.assertEqual(rep_env.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(rep_env.all_checks_passed)

        with patch(
            "fx3_firmware_lab.emount_af_breathing_and_ibis_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep_missing = analyze_emount_af_breathing_and_ibis()
        self.assertEqual(rep_missing.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(rep_missing.all_checks_passed)

    def test_20_fault_drop_fx3_power_zoom_and_fx6_handle_zoom(self) -> None:
        fx_pz = build_clean_room_emount_af_breathing_ibis_fixtures(drop_fx3_power_zoom=True)
        rep_pz = analyze_emount_af_breathing_and_ibis(clean_room=True, synthetic_overrides=fx_pz)
        self.assertFalse(rep_pz.all_checks_passed)
        self.assertFalse(rep_pz.pillar_a_power_zoom.passed)

        fx_hz = build_clean_room_emount_af_breathing_ibis_fixtures(drop_fx6_handle_zoom=True)
        rep_hz = analyze_emount_af_breathing_and_ibis(clean_room=True, synthetic_overrides=fx_hz)
        self.assertFalse(rep_hz.all_checks_passed)
        self.assertFalse(rep_hz.pillar_a_power_zoom.passed)

    def test_21_fault_lens_comm_text_mutation_and_pdaf_drop(self) -> None:
        fx_lc = build_clean_room_emount_af_breathing_ibis_fixtures(mutate_lens_comm_text=True)
        rep_lc = analyze_emount_af_breathing_and_ibis(clean_room=True, synthetic_overrides=fx_lc)
        self.assertFalse(rep_lc.all_checks_passed)
        self.assertFalse(rep_lc.pillar_b_fast_hybrid_pdaf.passed)

        fx_af = build_clean_room_emount_af_breathing_ibis_fixtures(drop_pdaf_transition_subj=True)
        rep_af = analyze_emount_af_breathing_and_ibis(clean_room=True, synthetic_overrides=fx_af)
        self.assertFalse(rep_af.all_checks_passed)
        self.assertFalse(rep_af.pillar_b_fast_hybrid_pdaf.passed)

    def test_22_fault_drop_breathing_udam(self) -> None:
        fx = build_clean_room_emount_af_breathing_ibis_fixtures(drop_breathing_udam=True)
        rep = analyze_emount_af_breathing_and_ibis(clean_room=True, synthetic_overrides=fx)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar_c_focus_breathing.passed)

    def test_23_fault_inject_fx6_physical_ibis_and_drop_fx3_restore(self) -> None:
        fx_inj = build_clean_room_emount_af_breathing_ibis_fixtures(inject_fx6_physical_ibis=True)
        rep_inj = analyze_emount_af_breathing_and_ibis(clean_room=True, synthetic_overrides=fx_inj)
        self.assertFalse(rep_inj.all_checks_passed)
        self.assertFalse(rep_inj.pillar_d_ibis_oss_calibration.passed)

        fx_rst = build_clean_room_emount_af_breathing_ibis_fixtures(drop_fx3_cp_ibis_restore=True)
        rep_rst = analyze_emount_af_breathing_and_ibis(clean_room=True, synthetic_overrides=fx_rst)
        self.assertFalse(rep_rst.all_checks_passed)
        self.assertFalse(rep_rst.pillar_d_ibis_oss_calibration.passed)

    def test_24_fault_corrupt_fx6_uxc_labels(self) -> None:
        fx = build_clean_room_emount_af_breathing_ibis_fixtures(corrupt_fx6_uxc_labels=True)
        rep = analyze_emount_af_breathing_and_ibis(clean_room=True, synthetic_overrides=fx)
        self.assertFalse(rep.all_checks_passed)
        self.assertTrue(any("0x0000050d" in e for e in rep.errors))

    def test_25_run_audit_all_contains_10_unified_auditors(self) -> None:
        payload = run_audit_all(clean_room=True)
        self.assertTrue(payload["all_checks_passed"])
        expected_auditors = {
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
        }
        self.assertEqual(len(expected_auditors), 10)
        self.assertTrue(expected_auditors.issubset(set(payload.keys())))
        emount_block = payload["emount_af_breathing_and_ibis_audit"]
        assert isinstance(emount_block, dict)
        self.assertTrue(emount_block["all_checks_passed"])
        self.assertEqual(emount_block["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_26_cli_audit_emount_af_clean_room_in_process(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-emount-af", "--clean-room"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(parsed["schema_version"], PHASE_55_SCHEMA)

    def test_27_cli_audit_emount_af_subprocess_clean_room(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-emount-af", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(len(data["report_sha256"]), 64)

    def test_28_module_uses_strict_o_rdonly_and_contains_zero_secrets_or_subprocesses(self) -> None:
        src = (PKG_ROOT / "fx3_firmware_lab" / "emount_af_breathing_and_ibis_auditor.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("subprocess", src)
        self.assertNotIn("socket", src)
        self.assertNotIn("CXD90057_k8", src)
        self.assertNotIn("PRIVATE KEY", src)


if __name__ == "__main__":
    unittest.main()
