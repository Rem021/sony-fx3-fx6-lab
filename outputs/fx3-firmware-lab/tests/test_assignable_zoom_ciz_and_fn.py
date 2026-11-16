"""Unit tests for Phase 75 Assignable Buttons, Clear Image Zoom (CIZ), Touch AF + Anamorphic Desqueeze, and Big6/Fn Volatile BK4 Shadow Auditor.

Executes rapidly in BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes.
"""

from __future__ import annotations

import json
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
from fx3_firmware_lab.assignable_zoom_ciz_and_fn_auditor import (
    BIG6_DEFAULT_SLOTS,
    CINEMA_ASSIGNABLE_ACTION_SPECS,
    CIZ_MAX_MAG_BY_RESOLUTION,
    CP_SHARED_ZOOM_TOUCH_MARKERS,
    FN_MENU_DEFAULT_SLOTS,
    FX3_APPFW_ASSIGNABLE_MARKERS,
    FX3_APPFW_BIG6_FN_MARKERS,
    FX3_APPFW_CIZ_ZOOM_MARKERS,
    FX3_APPFW_TOUCH_AF_MARKERS,
    FX6_APPFW_ASSIGNABLE_MARKERS,
    FX6_APPFW_BIG6_FN_MARKERS,
    FX6_APPFW_CIZ_ZOOM_MARKERS,
    FX6_APPFW_TOUCH_AF_MARKERS,
    FX6_ASSIGNABLE_SLOTS,
    GPE0_TOUCH_HEIGHT,
    GPE0_TOUCH_WIDTH,
    IMX510_PDAF_COLS,
    IMX510_PDAF_ROWS,
    IMX510_PDAF_TOTAL_POINTS,
    LENS_COMM_SHARED_MARKERS,
    PHASE_75_SCHEMA,
    PHASE_75_VERSION,
    AssignableZoomCizAndFnReport,
    analyze_assignable_zoom_ciz_and_fn,
    assignable_zoom_ciz_and_fn_report_to_dict,
    build_and_verify_big6_fn_volatile_shadow,
    build_clean_room_assignable_ciz_fixtures,
    evaluate_assignable_button_mapping,
    evaluate_zoom_ciz_matrix,
    transform_gpe0_touch_to_imx510_pdaf,
)
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveAssignableZoomCizAndFn(unittest.TestCase):
    _active_report: Optional[AssignableZoomCizAndFnReport] = None
    _elapsed_sec: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.monotonic()
        cls._active_report = analyze_assignable_zoom_ciz_and_fn()
        cls._elapsed_sec = time.monotonic() - t0

    def test_01_active_mode_passes_o_rdonly_12_artifacts_and_sub_500ms(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertLess(self._elapsed_sec, 0.5)
        self.assertEqual(rep.schema_version, PHASE_75_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_75_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.bk4_persistent_nvram_writes, 0)
        self.assertEqual(rep.null_gpio_faults, 0)
        self.assertFalse(rep.icx1295_crashed)
        self.assertFalse(rep.libcamera_crashed)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 12)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 70_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 45_000_000)
            self.assertEqual(rep.donor_file_sizes["fx3_lens_comm"], 14_544)
            self.assertEqual(rep.donor_file_sizes["fx6_lens_comm"], 14_544)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = assignable_zoom_ciz_and_fn_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotRegex(encoded, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])

    def test_03_pillar_1_assignable_markers_lens_comm_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p1 = rep.pillar_1_assignable_catalog
        self.assertTrue(p1.passed)
        self.assertEqual(p1.fx3_appfw_markers, FX3_APPFW_ASSIGNABLE_MARKERS)
        self.assertEqual(p1.fx6_appfw_markers, FX6_APPFW_ASSIGNABLE_MARKERS)
        self.assertEqual(p1.lens_comm_shared_markers, LENS_COMM_SHARED_MARKERS)
        self.assertEqual(p1.null_gpio_faults, 0)
        self.assertGreaterEqual(p1.hardware_backed_count, 11)
        self.assertGreaterEqual(p1.absent_hardware_isolated_count, 5)
        self.assertEqual(p1.uxc_assignable_labels["fx3_custom_key_settings"], "Custom Key Settings")
        self.assertEqual(p1.uxc_assignable_labels["fx3_focus_hold"], "Focus Hold")
        self.assertEqual(p1.uxc_assignable_labels["fx6_assignable_button"], "Assignable Button")
        self.assertEqual(p1.uxc_assignable_labels["fx6_clear_image_zoom"], "On(Clear Image Zoom)")
        self.assertEqual(p1.uxc_assignable_labels["fx6_optical_zoom_only"], "Optical Zoom Only")

    def test_04_pillar_2_zoom_ciz_markers_and_no_crashes(self) -> None:
        rep = self._active_report
        assert rep is not None
        p2 = rep.pillar_2_zoom_ciz_matrix
        self.assertTrue(p2.passed)
        self.assertEqual(p2.fx3_ciz_markers, FX3_APPFW_CIZ_ZOOM_MARKERS)
        self.assertEqual(p2.fx6_ciz_markers, FX6_APPFW_CIZ_ZOOM_MARKERS)
        self.assertTrue(p2.ciz_4k_15x_eval.by_pixel_super_res_active)
        self.assertTrue(p2.ciz_4k_15x_eval.pdaf_627_active)
        self.assertTrue(p2.ciz_fhd_20x_eval.by_pixel_super_res_active)
        self.assertTrue(p2.hdmi_raw16_clamp_eval.ciz_clamped_by_mutual_exclusion)
        self.assertTrue(p2.sq_120fps_clamp_eval.ciz_clamped_by_mutual_exclusion)
        self.assertTrue(p2.sq_240fps_clamp_eval.ciz_clamped_by_mutual_exclusion)

    def test_05_pillar_3_and_4_touch_af_and_big6_fn_markers(self) -> None:
        rep = self._active_report
        assert rep is not None
        p3 = rep.pillar_3_touch_af_desqueeze
        p4 = rep.pillar_4_big6_fn_shadow
        self.assertTrue(p3.passed)
        self.assertEqual(p3.fx3_touch_af_markers, FX3_APPFW_TOUCH_AF_MARKERS)
        self.assertEqual(p3.fx6_touch_af_markers, FX6_APPFW_TOUCH_AF_MARKERS)
        self.assertEqual(p3.cp_touch_markers, CP_SHARED_ZOOM_TOUCH_MARKERS)
        self.assertTrue(p4.passed)
        self.assertEqual(p4.fx3_big6_fn_markers, FX3_APPFW_BIG6_FN_MARKERS)
        self.assertEqual(p4.fx6_big6_fn_markers, FX6_APPFW_BIG6_FN_MARKERS)
        self.assertTrue(p4.fx3_global_xdb_valid)
        self.assertTrue(p4.fx6_global_xdb_valid)
        self.assertEqual(p4.bk4_persistent_nvram_writes, 0)
        self.assertFalse(p4.persistent_emmc_writes_authorized)


class TestPillar1AssignableButtonCrossBodyCatalog(unittest.TestCase):
    def test_06_all_fx6_1_to_11_and_lens_hold_map_with_zero_null_gpio(self) -> None:
        self.assertEqual(len(FX6_ASSIGNABLE_SLOTS), 12)
        for slot in FX6_ASSIGNABLE_SLOTS:
            res = evaluate_assignable_button_mapping(fx6_slot=slot, fx6_action="ZEBRA")
            self.assertTrue(res.valid, msg=f"Slot {slot} failed: {res.errors}")
            self.assertEqual(res.null_gpio_faults, 0)
            self.assertTrue(res.xlr_h1_compatible)
            self.assertNotEqual(res.fx3_target, "INVALID")

    def test_07_hardware_backed_cinema_line_actions_all_resolve(self) -> None:
        hw_actions = (
            "ZEBRA",
            "PEAKING",
            "MARKER",
            "BASE_ISO_CINE_EI",
            "SQ_MOTION",
            "FOCUS_MAGNIFIER_X4",
            "AF_MF",
            "LUT_ON_OFF",
            "STATUS_CHECK",
            "BIG6_SHOOTING_SCREEN",
            "AUDIO_LEVEL_DISPLAY",
        )
        for idx, action in enumerate(hw_actions, start=1):
            slot = f"ASSIGN_{min(idx, 6)}"
            res = evaluate_assignable_button_mapping(fx6_slot=slot, fx6_action=action)
            self.assertTrue(res.valid)
            self.assertTrue(res.hardware_backed_on_fx3)
            self.assertEqual(res.resolution_policy, "DIRECT_MAPPED")
            self.assertTrue(res.gpio_access_attempted)
            self.assertEqual(res.null_gpio_faults, 0)

    def test_08_fx6_only_nd_and_vf_targets_grayed_out_without_gpio_fault(self) -> None:
        for absent_action in ("ND_PRESET", "AUTO_ND", "VF_ADJUST"):
            res = evaluate_assignable_button_mapping(fx6_slot="ASSIGN_1", fx6_action=absent_action)
            self.assertTrue(res.valid)
            self.assertFalse(res.hardware_backed_on_fx3)
            self.assertEqual(res.resolution_policy, "GRAYED_OUT_HARDWARE_ABSENT")
            self.assertEqual(res.fx3_action, "NONE_GRAYED_OUT")
            self.assertFalse(res.gpio_access_attempted)
            self.assertEqual(res.null_gpio_faults, 0)

    def test_09_fx6_push_auto_nd_sdi_hdmi_and_smart_grip_redirect_safely(self) -> None:
        r_iris = evaluate_assignable_button_mapping(fx6_slot="ASSIGN_2", fx6_action="PUSH_AUTO_ND_IRIS")
        self.assertTrue(r_iris.valid)
        self.assertEqual(r_iris.resolution_policy, "SAFE_REDIRECTED")
        self.assertEqual(r_iris.fx3_action, "PUSH_AUTO_IRIS")
        self.assertFalse(r_iris.gpio_access_attempted)

        r_rec = evaluate_assignable_button_mapping(fx6_slot="ASSIGN_3", fx6_action="SDI_HDMI_REC_CONTROL")
        self.assertTrue(r_rec.valid)
        self.assertEqual(r_rec.resolution_policy, "SAFE_REDIRECTED")
        self.assertEqual(r_rec.fx3_action, "HDMI_REC_CONTROL_ONLY")
        self.assertEqual(r_rec.null_gpio_faults, 0)

        r_grip = evaluate_assignable_button_mapping(fx6_slot="ASSIGN_7", fx6_action="SMART_GRIP_ASSIGN_7_9")
        self.assertTrue(r_grip.valid)
        self.assertEqual(r_grip.fx3_target, "JOYSTICK_CENTER")
        self.assertEqual(r_grip.resolution_policy, "SAFE_REDIRECTED")
        self.assertEqual(r_grip.fx3_action, "FX3_BODY_TW_LEVER_AND_JOYSTICK_FALLBACK")
        self.assertTrue(r_grip.xlr_h1_compatible)
        self.assertEqual(r_grip.null_gpio_faults, 0)

    def test_10_lens_focus_hold_and_handle_assign_7_9_redirects(self) -> None:
        r_lens = evaluate_assignable_button_mapping(fx6_slot="LENS_FOCUS_HOLD", fx6_action="AF_MF")
        self.assertTrue(r_lens.valid)
        self.assertEqual(r_lens.fx3_target, "LENS_FOCUS_HOLD")
        self.assertEqual(r_lens.resolution_policy, "DIRECT_MAPPED")
        self.assertTrue(r_lens.gpio_access_attempted)

        r_a8 = evaluate_assignable_button_mapping(fx6_slot="ASSIGN_8", fx6_action="AUDIO_LEVEL_DISPLAY")
        self.assertTrue(r_a8.valid)
        self.assertEqual(r_a8.fx3_target, "AF_ON")
        self.assertEqual(r_a8.resolution_policy, "SAFE_REDIRECTED")
        self.assertFalse(r_a8.gpio_access_attempted)

    def test_11_invalid_assignable_slot_or_action_rejected_cleanly(self) -> None:
        r_bad_slot = evaluate_assignable_button_mapping(fx6_slot="ASSIGN_99", fx6_action="ZEBRA")
        self.assertFalse(r_bad_slot.valid)
        self.assertEqual(r_bad_slot.resolution_policy, "BLOCKED_INVALID_ASSIGNABLE")
        self.assertEqual(r_bad_slot.null_gpio_faults, 0)

        r_bad_act = evaluate_assignable_button_mapping(fx6_slot="ASSIGN_1", fx6_action="UNKNOWN_ACT")
        self.assertFalse(r_bad_act.valid)
        self.assertEqual(r_bad_act.resolution_policy, "BLOCKED_INVALID_ASSIGNABLE")
        self.assertGreaterEqual(len(CINEMA_ASSIGNABLE_ACTION_SPECS), 17)


class TestPillar2ZoomLeverAndCizMutualExclusion(unittest.TestCase):
    def test_12_tw_zoom_lever_8_step_speed_valid_and_bounds(self) -> None:
        for spd in range(1, 9):
            res = evaluate_zoom_ciz_matrix(
                requested_zoom_mode="CLEAR_IMAGE_ZOOM",
                requested_magnification=1.25,
                resolution_mode="QFHD_3840x2160",
                zoom_lever_speed=spd,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.zoom_lever_speed, spd)

        for bad_spd in (0, 9, -1, True):
            res = evaluate_zoom_ciz_matrix(
                requested_zoom_mode="OPTICAL_ZOOM_ONLY",
                requested_magnification=1.0,
                zoom_lever_speed=bad_spd,  # type: ignore[arg-type]
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, "BLOCKED_INVALID_ZOOM_PARAM")

    def test_13_ciz_4k_dci_and_qfhd_15x_retains_pdaf_and_face_eye_tracking(self) -> None:
        for res_mode in ("DCI_4K_4096x2160", "QFHD_3840x2160"):
            res = evaluate_zoom_ciz_matrix(
                requested_zoom_mode="CLEAR_IMAGE_ZOOM",
                requested_magnification=1.50,
                resolution_mode=res_mode,
                zoom_lever_speed=5,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.status, "CIZ_BY_PIXEL_SUPER_RES_VERIFIED")
            self.assertEqual(res.effective_magnification, 1.5)
            self.assertEqual(res.max_allowed_ciz_magnification, 1.5)
            self.assertTrue(res.by_pixel_super_res_active)
            self.assertTrue(res.pdaf_627_active)
            self.assertTrue(res.face_eye_tracking_retained)
            self.assertEqual(res.focus_area_mode, "CENTER_WIDE_PDAF_RETAINED")

    def test_14_ciz_fhd_20x_retains_pdaf_and_exceeds_4k_cap_correctly(self) -> None:
        fhd_ok = evaluate_zoom_ciz_matrix(
            requested_zoom_mode="CLEAR_IMAGE_ZOOM",
            requested_magnification=2.00,
            resolution_mode="FHD_1920x1080",
            zoom_lever_speed=8,
        )
        self.assertTrue(fhd_ok.valid)
        self.assertEqual(fhd_ok.effective_magnification, 2.0)
        self.assertTrue(fhd_ok.by_pixel_super_res_active)
        self.assertTrue(fhd_ok.pdaf_627_active)

        qfhd_over = evaluate_zoom_ciz_matrix(
            requested_zoom_mode="CLEAR_IMAGE_ZOOM",
            requested_magnification=1.60,
            resolution_mode="QFHD_3840x2160",
        )
        self.assertFalse(qfhd_over.valid)
        self.assertEqual(qfhd_over.status, "BLOCKED_INVALID_ZOOM_PARAM")

        fhd_over = evaluate_zoom_ciz_matrix(
            requested_zoom_mode="CLEAR_IMAGE_ZOOM",
            requested_magnification=2.10,
            resolution_mode="FHD_1920x1080",
        )
        self.assertFalse(fhd_over.valid)
        self.assertEqual(CIZ_MAX_MAG_BY_RESOLUTION["FHD_1920x1080"], 2.0)

    def test_15_digital_zoom_up_to_4x_disables_by_pixel_sr_and_pdaf(self) -> None:
        dz = evaluate_zoom_ciz_matrix(
            requested_zoom_mode="DIGITAL_ZOOM",
            requested_magnification=4.00,
            resolution_mode="FHD_1920x1080",
        )
        self.assertTrue(dz.valid)
        self.assertEqual(dz.status, "DIGITAL_ZOOM_VERIFIED")
        self.assertFalse(dz.by_pixel_super_res_active)
        self.assertFalse(dz.pdaf_627_active)
        self.assertFalse(dz.face_eye_tracking_retained)
        self.assertEqual(dz.focus_area_mode, "CENTER_CONTRAST_ONLY")

        dz_over = evaluate_zoom_ciz_matrix(
            requested_zoom_mode="DIGITAL_ZOOM",
            requested_magnification=4.10,
            resolution_mode="FHD_1920x1080",
        )
        self.assertFalse(dz_over.valid)

    def test_16_hdmi_raw16_deterministically_clamps_ciz_to_optical_1x(self) -> None:
        res = evaluate_zoom_ciz_matrix(
            requested_zoom_mode="CLEAR_IMAGE_ZOOM",
            requested_magnification=1.50,
            resolution_mode="DCI_4K_4096x2160",
            hdmi_raw16_enabled=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, "CIZ_CLAMPED_TO_OPTICAL_1X_SAFE")
        self.assertEqual(res.effective_zoom_mode, "OPTICAL_ZOOM_ONLY")
        self.assertEqual(res.effective_magnification, 1.0)
        self.assertTrue(res.ciz_clamped_by_mutual_exclusion)
        self.assertEqual(res.mutual_exclusion_reason, "HDMI_RAW16_ACTIVE")
        self.assertFalse(res.icx1295_crashed)
        self.assertFalse(res.libcamera_crashed)

    def test_17_sq_120fps_and_240fps_clamp_ciz_while_sq_60fps_allows_ciz(self) -> None:
        for hfr in (100.0, 120.0, 240.0):
            clamped = evaluate_zoom_ciz_matrix(
                requested_zoom_mode="CLEAR_IMAGE_ZOOM",
                requested_magnification=1.50,
                resolution_mode="QFHD_3840x2160",
                sq_active=True,
                sq_fps=hfr,
            )
            self.assertTrue(clamped.valid)
            self.assertTrue(clamped.ciz_clamped_by_mutual_exclusion)
            self.assertEqual(clamped.effective_magnification, 1.0)
            self.assertEqual(clamped.mutual_exclusion_reason, "SQ_HFR_120_240FPS_ACTIVE")
            self.assertFalse(clamped.icx1295_crashed)
            self.assertFalse(clamped.libcamera_crashed)

        sq60 = evaluate_zoom_ciz_matrix(
            requested_zoom_mode="CLEAR_IMAGE_ZOOM",
            requested_magnification=1.50,
            resolution_mode="QFHD_3840x2160",
            sq_active=True,
            sq_fps=60.0,
        )
        self.assertTrue(sq60.valid)
        self.assertFalse(sq60.ciz_clamped_by_mutual_exclusion)
        self.assertEqual(sq60.effective_magnification, 1.5)


class TestPillar3TouchAfAndAnamorphicDesqueeze(unittest.TestCase):
    def test_18_gpe0_center_touch_maps_to_center_imx510_pdaf(self) -> None:
        res = transform_gpe0_touch_to_imx510_pdaf(
            touch_x_px=GPE0_TOUCH_WIDTH / 2.0,
            touch_y_px=GPE0_TOUCH_HEIGHT / 2.0,
            touch_function="TOUCH_TRACKING",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, "TOUCH_AF_COORD_TRANSFORM_VERIFIED")
        self.assertAlmostEqual(res.sensor_norm_x, 0.5, places=5)
        self.assertAlmostEqual(res.sensor_norm_y, 0.5, places=5)
        self.assertEqual(res.pdaf_col, IMX510_PDAF_COLS // 2)
        self.assertEqual(res.pdaf_row, IMX510_PDAF_ROWS // 2)
        self.assertEqual(res.pdaf_total_points, IMX510_PDAF_TOTAL_POINTS)

    def test_19_anamorphic_13x_15x_16x_20x_inverse_x_transform(self) -> None:
        # 2.0x desqueeze: display u=0.90 (x=864px) -> sensor u = 0.5 + (0.90-0.5)/2.0 = 0.70
        r20 = transform_gpe0_touch_to_imx510_pdaf(
            touch_x_px=864.0,
            touch_y_px=216.0,
            desqueeze_ratio=2.0,
        )
        self.assertTrue(r20.valid)
        self.assertAlmostEqual(r20.display_norm_x, 0.90, places=5)
        self.assertAlmostEqual(r20.sensor_norm_x, 0.70, places=5)
        self.assertAlmostEqual(r20.sensor_norm_y, 0.40, places=5)

        # 1.3x desqueeze: display u=0.63 (x=604.8px) -> sensor u = 0.5 + 0.13/1.3 = 0.60
        r13 = transform_gpe0_touch_to_imx510_pdaf(
            touch_x_px=604.8,
            touch_y_px=270.0,
            desqueeze_ratio=1.3,
        )
        self.assertTrue(r13.valid)
        self.assertAlmostEqual(r13.sensor_norm_x, 0.60, places=5)

        # 1.5x & 1.6x also supported
        for ratio in (1.5, 1.6):
            r = transform_gpe0_touch_to_imx510_pdaf(
                touch_x_px=480.0 + 192.0,  # u_disp = 0.70
                touch_y_px=270.0,
                desqueeze_ratio=ratio,
            )
            self.assertTrue(r.valid)
            self.assertAlmostEqual(r.sensor_norm_x, 0.5 + 0.2 / ratio, places=4)

    def test_20_focus_magnifier_4x_crop_plus_2x_desqueeze_composition(self) -> None:
        # 4.0x crop centered at (0.5, 0.5) spans [0.375..0.625]^2.
        # Touching x=720 (u_disp=0.75) -> u_view = 0.5625 -> with 2.0x desqueeze -> 0.53125
        r = transform_gpe0_touch_to_imx510_pdaf(
            touch_x_px=720.0,
            touch_y_px=270.0,
            touch_function="TOUCH_FOCUS",
            desqueeze_ratio=2.0,
            focus_magnifier_factor=4.0,
            magnifier_center_norm=(0.5, 0.5),
        )
        self.assertTrue(r.valid)
        self.assertAlmostEqual(r.sensor_norm_x, 0.53125, places=5)
        self.assertAlmostEqual(r.sensor_norm_y, 0.50, places=5)

    def test_21_magnifier_4x_clamps_center_when_near_sensor_edge(self) -> None:
        r = transform_gpe0_touch_to_imx510_pdaf(
            touch_x_px=0.0,
            touch_y_px=0.0,
            desqueeze_ratio=1.0,
            focus_magnifier_factor=4.0,
            magnifier_center_norm=(0.01, 0.01),
        )
        self.assertTrue(r.valid)
        # half_span = 0.125 -> clamped center (0.125, 0.125) -> top-left = (0.0, 0.0)
        self.assertAlmostEqual(r.sensor_norm_x, 0.0, places=5)
        self.assertAlmostEqual(r.sensor_norm_y, 0.0, places=5)
        self.assertEqual(r.pdaf_point_index, 0)

    def test_22_touch_shutter_blocked_in_cine_mode_but_allowed_in_stills(self) -> None:
        blocked = transform_gpe0_touch_to_imx510_pdaf(
            touch_x_px=480.0,
            touch_y_px=270.0,
            touch_function="TOUCH_SHUTTER",
            cine_mode=True,
        )
        self.assertFalse(blocked.valid)
        self.assertEqual(blocked.status, "BLOCKED_TOUCH_SHUTTER_DISABLED_IN_CINE")
        self.assertTrue(blocked.touch_shutter_disabled_in_cine)

        stills_ok = transform_gpe0_touch_to_imx510_pdaf(
            touch_x_px=480.0,
            touch_y_px=270.0,
            touch_function="TOUCH_SHUTTER",
            cine_mode=False,
        )
        self.assertTrue(stills_ok.valid)
        self.assertFalse(stills_ok.touch_shutter_disabled_in_cine)

    def test_23_invalid_touch_coords_or_desqueeze_ratio_rejected(self) -> None:
        for kwargs in (
            {"touch_x_px": -1.0, "touch_y_px": 270.0},
            {"touch_x_px": 961.0, "touch_y_px": 270.0},
            {"touch_x_px": 480.0, "touch_y_px": 541.0},
            {"touch_x_px": 480.0, "touch_y_px": 270.0, "desqueeze_ratio": 1.8},
            {"touch_x_px": 480.0, "touch_y_px": 270.0, "focus_magnifier_factor": 8.0},
        ):
            r = transform_gpe0_touch_to_imx510_pdaf(**kwargs)  # type: ignore[arg-type]
            self.assertFalse(r.valid)
            self.assertEqual(r.status, "BLOCKED_INVALID_TOUCH_COORD")


class TestPillar4Big6AndFnVolatileShadow(unittest.TestCase):
    def test_24_default_6_big6_and_12_fn_slots_camset_json_roundtrip(self) -> None:
        res = build_and_verify_big6_fn_volatile_shadow()
        self.assertTrue(res.valid, msg=f"Errors: {res.errors}")
        self.assertEqual(res.status, "VOLATILE_BIG6_FN_CAMSET_SHADOW_VERIFIED")
        self.assertEqual(res.big6_slot_count, 6)
        self.assertEqual(res.fn_slot_count, 12)
        self.assertTrue(res.big6_available)
        self.assertTrue(res.volatile_shadow_only)
        self.assertEqual(res.bk4_persistent_nvram_writes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(len(res.camset_shadow_sha256), 64)
        parsed = json.loads(res.camset_shadow_json)
        self.assertEqual(len(parsed["big6_slots"]), 6)
        self.assertEqual(len(parsed["fn_slots"]), 12)
        self.assertEqual(parsed["bk4_persistent_nvram_writes"], 0)

    def test_25_home_lower_left_aperture_vs_nd_filter_and_ram_prefix(self) -> None:
        for ll_mode, prefix in (("APERTURE", "ram://shadow.json"), ("ND_FILTER", "memory://shadow.json")):
            res = build_and_verify_big6_fn_volatile_shadow(
                home_lower_left_mode=ll_mode,
                shadow_path=prefix,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.home_lower_left_mode, ll_mode)
            self.assertTrue(res.volatile_shadow_only)
            self.assertEqual(res.bk4_persistent_nvram_writes, 0)

    def test_26_legacy_sq_mode_blocks_big6_availability(self) -> None:
        res = build_and_verify_big6_fn_volatile_shadow(sq_mode_settings="LEGACY_SQ_MODE")
        self.assertFalse(res.valid)
        self.assertFalse(res.big6_available)
        self.assertEqual(res.status, "BLOCKED_BIG6_REQUIRES_FIXED_VARIABLE_SQ")
        self.assertEqual(res.bk4_persistent_nvram_writes, 0)

    def test_27_persistent_nvram_paths_and_emmc_write_flag_hard_blocked(self) -> None:
        for bad_path in (
            "/dev/nflasha30/camset.bin",
            "/dev/cnflasha1/bk4.bin",
            "bk4://persistent/big6",
            "p2:/Backup.bin",
        ):
            res = build_and_verify_big6_fn_volatile_shadow(shadow_path=bad_path)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, "BLOCKED_PERSISTENT_BK4_NVRAM_WRITE")
            self.assertFalse(res.volatile_shadow_only)
            self.assertEqual(res.bk4_persistent_nvram_writes, 0)

        emmc_auth = build_and_verify_big6_fn_volatile_shadow(
            persistent_emmc_writes_authorized=True,
        )
        self.assertFalse(emmc_auth.valid)
        self.assertEqual(emmc_auth.bk4_persistent_nvram_writes, 0)

    def test_28_wrong_big6_or_fn_slot_counts_or_duplicates_rejected(self) -> None:
        bad_b6 = build_and_verify_big6_fn_volatile_shadow(big6_slots=BIG6_DEFAULT_SLOTS[:5])
        self.assertFalse(bad_b6.valid)

        bad_fn = build_and_verify_big6_fn_volatile_shadow(fn_slots=FN_MENU_DEFAULT_SLOTS[:11])
        self.assertFalse(bad_fn.valid)

        dup_fn = list(FN_MENU_DEFAULT_SLOTS)
        dup_fn[1] = dict(dup_fn[0])
        bad_dup = build_and_verify_big6_fn_volatile_shadow(fn_slots=dup_fn)
        self.assertFalse(bad_dup.valid)


class TestDualModeCleanRoomCliAndHygiene(unittest.TestCase):
    def test_29_clean_room_mode_passes_deterministically(self) -> None:
        r1 = analyze_assignable_zoom_ciz_and_fn(clean_room=True)
        r2 = analyze_assignable_zoom_ciz_and_fn(clean_room=True)
        self.assertTrue(r1.all_checks_passed, msg=f"Errors: {r1.errors}")
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(len(r1.donor_file_sizes), 12)
        self.assertEqual(r1.bk4_persistent_nvram_writes, 0)
        self.assertEqual(r1.null_gpio_faults, 0)

    def test_30_missing_donor_root_falls_back_to_clean_room_automatically(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": ""}, clear=False), patch(
            "fx3_firmware_lab.assignable_zoom_ciz_and_fn_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_assignable_zoom_ciz_and_fn(
                repo_root=Path("/tmp/nonexistent_fx3_fx6_donor_root_phase75")
            )
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_31_clean_room_fixtures_dict_contains_all_12_artifacts(self) -> None:
        fixtures = build_clean_room_assignable_ciz_fixtures()
        self.assertEqual(len(fixtures), 12)
        for key in (
            "fx3_appfw",
            "fx6_appfw",
            "fx3_cpapp",
            "fx6_cpapp",
            "fx3_lens_comm",
            "fx6_lens_comm",
            "fx3_global_xdb",
            "fx6_global_xdb",
            "fx3_str_en",
            "fx3_str_en_g",
            "fx6_str_en_1",
            "fx6_str_en_2",
        ):
            self.assertIn(key, fixtures)
            self.assertGreater(len(fixtures[key]), 0)

    def test_32_cli_audit_assignable_ciz_inprocess_and_subprocess(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-assignable-ciz", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["schema_version"], PHASE_75_SCHEMA)
        self.assertEqual(payload["bk4_persistent_nvram_writes"], 0)
        self.assertNotRegex(buf.getvalue(), r'(?<![0-9A-Za-z_/.-])b[\'"]')

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-assignable-ciz", "--clean-room", "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        sub_payload = json.loads(proc.stdout)
        self.assertEqual(sub_payload["report_sha256"], payload["report_sha256"])

    def test_33_run_audit_all_includes_14_auditors_with_assignable_ciz(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        self.assertIn("assignable_zoom_ciz_and_fn_audit", summary)
        self.assertTrue(summary["assignable_zoom_ciz_and_fn_audit"]["all_checks_passed"])

    def test_34_static_source_hygiene_o_rdonly_and_zero_secrets(self) -> None:
        src = (PKG_ROOT / "fx3_firmware_lab" / "assignable_zoom_ciz_and_fn_auditor.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in ("os.O_WRONLY", "os.O_RDWR", "subprocess", "socket", "CXD90057_k8"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
