#!/usr/bin/env python3
"""Unit tests for Phase 207 Stage 37 (`37/37` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `Ver. 7.02`) `[De-Squeeze Display]` (`Off/1.3x/2.0x/1.5x/1.6x=1.65x`
4-Setting Lock & 5-Mode HDMI RAW / Clean-HDMI Bypass), External-Only `Monitor & Control` `[Focus Map]`
(Zero In-Body FX3 Menu & `>=150fps` Cutoff vs `1..6fps` Allowed), and Dual-Slot `[Simult. Recording]` +
`[Auto Switch Media]` / `[Shockless WB]` HIL Co-Emulator.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import io
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
import realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator as p207  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None
_CLEAN_SUITE_ELAPSED = None
_DEFAULT_SUITE_CACHE = None
_DEFAULT_SUITE_ELAPSED = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = (
            p207.run_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil(
                force_clean_room=True
            )
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = (
            p207.run_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil()
        )
    return _DEFAULT_AUDIT_CACHE


def _get_clean_room_suite():
    global _CLEAN_SUITE_CACHE, _CLEAN_SUITE_ELAPSED
    if _CLEAN_SUITE_CACHE is None:
        t0 = time.monotonic()
        _CLEAN_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        _CLEAN_SUITE_ELAPSED = time.monotonic() - t0
    return _CLEAN_SUITE_CACHE, float(_CLEAN_SUITE_ELAPSED)


def _get_default_suite():
    global _DEFAULT_SUITE_CACHE, _DEFAULT_SUITE_ELAPSED
    if _DEFAULT_SUITE_CACHE is None:
        t0 = time.monotonic()
        _DEFAULT_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        _DEFAULT_SUITE_ELAPSED = time.monotonic() - t0
    return _DEFAULT_SUITE_CACHE, float(_DEFAULT_SUITE_ELAPSED)


class TestPhase207Desqueeze165xFocusMapSimultShocklessWbCoEmulator(unittest.TestCase):
    def test_01_schema_version_stage_37_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p207.PHASE_207_SCHEMA,
            "phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator_v1",
        )
        self.assertEqual(p207.PHASE_207_VERSION, "207.0.0")
        self.assertEqual(p207.STAGE_INDEX, 37)
        self.assertEqual(p207.STAGE_TOTAL, 37)
        self.assertEqual(p207.MILESTONE_LABEL, "37/37")
        self.assertEqual(
            p207.STAGE_NAME,
            "stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil",
        )
        self.assertEqual(p207.FX3_MODEL_ID, 0x91030080)
        self.assertFalse(p207.FX3_HAS_INBODY_FOCUS_MAP_MENU)
        self.assertTrue(p207.P8_CP_MUTATION_FORBIDDEN)
        self.assertFalse(p207.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p207.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p207.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p207.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p207.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p207.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p207.DESQUEEZE_BAKED_INTO_RAW_OR_XAVC_FRAMES, 0)
        self.assertEqual(p207.INBODY_FX3_FOCUS_MAP_OVERLAY_FRAMES, 0)
        self.assertEqual(p207.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_donor_inspection_under_0_10s_and_cached(self) -> None:
        p207._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p207.inspect_phase207_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p207.inspect_phase207_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1
        self.assertLess(dt1, 0.10)
        self.assertLess(dt2, 0.02)
        self.assertEqual(da1.donor_files_inspected, 12)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        if da1.source_mode == "LOCAL_DONOR_RDONLY":
            self.assertIs(da1, da2)

    def test_03_clean_room_donor_fallback_via_flag_and_env(self) -> None:
        da_flag = p207.inspect_phase207_donors(force_clean_room=True)
        self.assertEqual(da_flag.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_flag.access_mode, "O_RDONLY")
        self.assertEqual(da_flag.donor_files_inspected, 12)
        self.assertEqual(da_flag.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da_flag.all_contracts_verified)

        da_env = p207.inspect_phase207_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da_env.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIs(da_env, da_flag)

    def test_04_clean_room_sentinel_paths_do_not_touch_local_donors(self) -> None:
        paths_clean = p207.resolve_phase207_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 12)
        for p in paths_clean.values():
            self.assertIn(p207.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())
        da = p207.inspect_phase207_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_05_twelve_donors_expected_sizes_and_contracts(self) -> None:
        da = p207.inspect_phase207_donors()
        self.assertEqual(da.fx3_lens_comm.file_bytes, 14_544)
        self.assertEqual(da.fx6_lens_comm.file_bytes, 14_544)
        self.assertEqual(da.fx3_media_cfg.file_bytes, 52_312)
        self.assertEqual(da.fx3_ptp_ctrl.file_bytes, 165_320)
        self.assertEqual(da.fx3_string_en_f.file_bytes, 373_820)
        self.assertEqual(da.fx6_string_en.file_bytes, 118_208)
        self.assertEqual(da.fx3_appfw.file_bytes, 79_015_712)
        self.assertEqual(da.fx6_appfw.file_bytes, 50_520_424)
        self.assertEqual(da.fx3_cpapp.file_bytes, 15_980_568)
        self.assertEqual(da.fx6_cpapp.file_bytes, 17_952_816)
        self.assertEqual(da.fx3_libmpr.file_bytes, 3_517_008)
        self.assertEqual(da.fx6_libmpr.file_bytes, 28_921_824)
        self.assertTrue(da.desqueeze_165x_and_4locks_proven)
        self.assertTrue(da.external_focus_map_and_lens_pdaf_proven)
        self.assertTrue(da.simult_autoswitch_and_shockless_wb_proven)

    def test_06_string_uxc_proves_desqueeze_4locks_focusmap_simult_and_shockless_tokens(self) -> None:
        da = p207.inspect_phase207_donors()
        uxc = da.fx3_string_en_f
        self.assertTrue(uxc.uxd_container_ok)
        for tok in (
            "De-Squeeze Display",
            "1.3x",
            "2.0x",
            "1.5x",
            "1.6x",
            "Manual Focus",
            "Focus Mode",
            "Focus Area",
            "SteadyShot",
            "Face Priority in Multi Metering",
            "RAW Output",
            "Off(HDMI Only)",
            "HDMI Info. Display",
            "Log Shooting",
            "Focus Map",
            "Simult. Recording",
            "Auto Switch Media",
            "Shockless WB",
            "C.Temp./Filter",
        ):
            self.assertEqual(uxc.marker_hits[tok], 1, msg=tok)

    def test_07_large_donors_use_strictly_bounded_windows_only_and_prove_165_scale(self) -> None:
        da = p207.inspect_phase207_donors()
        self.assertEqual(da.fx6_appfw.window_hits["SCALE_1_65"], 1)
        for large in (
            da.fx3_appfw,
            da.fx6_appfw,
            da.fx3_cpapp,
            da.fx6_cpapp,
            da.fx3_libmpr,
            da.fx6_libmpr,
        ):
            self.assertTrue(large.bounded_windows_only)
            self.assertGreater(large.file_bytes, large.bytes_read_total)
            self.assertLessEqual(
                large.bytes_read_total,
                p207.BOUNDED_WINDOW_MAX_BYTES
                * (len(p207.LARGE_DONOR_WINDOWS[large.artifact_key]) + 1),
            )
            self.assertTrue(all(large.window_hits.values()), msg=large.artifact_key)

    def test_08_pillar_a_desqueeze_menu_options_and_165x_scale_constants(self) -> None:
        self.assertEqual(
            p207.DESQUEEZE_MENU_PATH,
            "MENU -> Setup -> [Display Option] -> [De-Squeeze Display]",
        )
        self.assertEqual(
            p207.VALID_DESQUEEZE_OPTIONS,
            ("Off", "1.3x", "2.0x", "1.5x", "1.6x"),
        )
        self.assertEqual(p207.DESQUEEZE_HORIZONTAL_SCALE_MAP["1.6x"], 1.65)
        self.assertEqual(
            dict(p207.DESQUEEZE_FOUR_LOCKED_SETTINGS),
            {
                "Focus Mode": "Manual Focus",
                "Focus Area": "Wide",
                "SteadyShot": "Off",
                "Face Priority in Multi Metering": "Off",
            },
        )

    def test_09_pillar_a_desqueeze_off_preserves_af_ibis_and_spherical_1_0x(self) -> None:
        res = p207.probe_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_option="Off",
            requested_focus_mode="AF-C",
            requested_focus_area="Tracking: Spot M",
            requested_steadyshot="Active",
            requested_face_priority_multi_metering="On",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.display_desqueeze_active)
        self.assertFalse(res.four_locks_enforced)
        self.assertEqual(res.applied_horizontal_scale, 1.0)
        self.assertEqual(res.effective_focus_mode, "AF-C")
        self.assertEqual(res.effective_focus_area, "Tracking: Spot M")
        self.assertEqual(res.effective_steadyshot, "Active")
        self.assertEqual(res.effective_face_priority_multi_metering, "On")
        self.assertEqual(res.errno_code, 0)

    def test_10_pillar_a_desqueeze_1_6x_applies_1_65x_cinemascope_and_locks_4_settings(self) -> None:
        res = p207.probe_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_option="1.6x",
            requested_focus_mode="AF-C",
            requested_focus_area="Zone",
            requested_steadyshot="Active",
            requested_face_priority_multi_metering="On",
            log_shooting="Cine EI",
            capture_mode="Movie",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.display_desqueeze_active)
        self.assertAlmostEqual(res.nominal_ratio_value, 1.6)
        self.assertAlmostEqual(res.applied_horizontal_scale, 1.65)
        self.assertTrue(res.cinemascope_165x_active)
        self.assertEqual(res.output_aspect_label, "2.39:1 CinemaScope")
        self.assertTrue(res.four_locks_enforced)
        self.assertEqual(res.effective_focus_mode, "Manual Focus")
        self.assertEqual(res.effective_focus_area, "Wide")
        self.assertEqual(res.effective_steadyshot, "Off")
        self.assertEqual(res.effective_face_priority_multi_metering, "Off")
        self.assertEqual(res.desqueeze_baked_into_raw_or_xavc_frames, 0)

    def test_11_pillar_a_desqueeze_1_3x_1_5x_2_0x_scales_and_4locks(self) -> None:
        expected = (("1.3x", 1.30), ("1.5x", 1.50), ("2.0x", 2.00))
        for opt, scale in expected:
            res = p207.probe_desqueeze_display_4locks_and_bypass_hil(
                desqueeze_option=opt,
                log_shooting="Flexible ISO",
                capture_mode="S&Q",
            )
            self.assertTrue(res.admitted, msg=opt)
            self.assertTrue(res.display_desqueeze_active, msg=opt)
            self.assertAlmostEqual(res.applied_horizontal_scale, scale, msg=opt)
            self.assertFalse(res.cinemascope_165x_active, msg=opt)
            self.assertTrue(res.four_locks_enforced, msg=opt)
            self.assertEqual(res.effective_focus_mode, "Manual Focus")
            self.assertEqual(res.effective_focus_area, "Wide")
            self.assertEqual(res.effective_steadyshot, "Off")
            self.assertEqual(res.effective_face_priority_multi_metering, "Off")

    def test_12_pillar_a_blocks_override_of_4_locked_settings_with_eopnotsupp(self) -> None:
        for opt in ("1.3x", "1.5x", "1.6x", "2.0x"):
            res = p207.probe_desqueeze_display_4locks_and_bypass_hil(
                desqueeze_option=opt,
                attempt_override_locked_setting=True,
            )
            self.assertFalse(res.admitted, msg=opt)
            self.assertTrue(res.lock_override_rejected, msg=opt)
            self.assertTrue(res.four_locks_enforced, msg=opt)
            self.assertEqual(res.errno_code, p207.EOPNOTSUPP_ERRNO, msg=opt)
            self.assertEqual(
                res.status_code,
                "BLOCKED_DESQUEEZE_4LOCK_SETTING_OVERRIDE_EOPNOTSUPP",
                msg=opt,
            )

    def test_13_pillar_a_suppresses_desqueeze_under_hdmi_raw_and_off_hdmi_only(self) -> None:
        raw_on = p207.probe_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_option="1.6x",
            hdmi_raw_output="On",
        )
        self.assertTrue(raw_on.admitted)
        self.assertFalse(raw_on.display_desqueeze_active)
        self.assertEqual(raw_on.applied_horizontal_scale, 1.0)
        self.assertIn("HDMI_RAW_OUTPUT_ON", raw_on.suppression_reasons)
        self.assertEqual(raw_on.desqueeze_baked_into_raw_or_xavc_frames, 0)

        clean_hdmi = p207.probe_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_option="2.0x",
            rec_media_dur_hdmi="Off(HDMI Only)",
            requested_hdmi_info_display="On",
        )
        self.assertTrue(clean_hdmi.admitted)
        self.assertFalse(clean_hdmi.display_desqueeze_active)
        self.assertEqual(clean_hdmi.applied_horizontal_scale, 1.0)
        self.assertEqual(clean_hdmi.effective_hdmi_info_display, "Off")
        self.assertIn("REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY", clean_hdmi.suppression_reasons)

    def test_14_pillar_a_suppresses_desqueeze_under_log_off_remote_shooting_and_photo(self) -> None:
        log_off = p207.probe_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_option="1.5x",
            log_shooting="Off",
        )
        self.assertTrue(log_off.admitted)
        self.assertFalse(log_off.display_desqueeze_active)
        self.assertIn("LOG_SHOOTING_OFF", log_off.suppression_reasons)

        remote = p207.probe_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_option="1.6x",
            remote_shooting_active=True,
        )
        self.assertTrue(remote.admitted)
        self.assertFalse(remote.display_desqueeze_active)
        self.assertIn("REMOTE_SHOOTING_ACTIVE", remote.suppression_reasons)

        photo = p207.probe_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_option="1.3x",
            capture_mode="Photo",
        )
        self.assertTrue(photo.admitted)
        self.assertFalse(photo.display_desqueeze_active)
        self.assertIn("STILL_PHOTO_CAPTURE_MODE", photo.suppression_reasons)

    def test_15_pillar_a_rejects_invalid_desqueeze_option_and_validates_inputs(self) -> None:
        for bad_opt in ("1.8x", "1.65x", "1.33x", "Auto", ""):
            res = p207.probe_desqueeze_display_4locks_and_bypass_hil(desqueeze_option=bad_opt)
            self.assertFalse(res.admitted, msg=bad_opt)
            self.assertEqual(res.errno_code, p207.EINVAL_ERRNO, msg=bad_opt)

        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_desqueeze_display_4locks_and_bypass_hil(hdmi_raw_output="16bit")
        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_desqueeze_display_4locks_and_bypass_hil(rec_media_dur_hdmi="Invalid")
        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_desqueeze_display_4locks_and_bypass_hil(requested_hdmi_info_display="Auto")
        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_desqueeze_display_4locks_and_bypass_hil(log_shooting="S-Gamut3")
        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_desqueeze_display_4locks_and_bypass_hil(capture_mode="Interval")

    def test_16_pillar_a_evaluator_matrix_passes_100pct(self) -> None:
        pa = p207.evaluate_pillar_a_desqueeze_165x_4locks_and_bypass_hil()
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["ratio_matrix"]), 5)

    def test_17_pillar_b_cpapp_emount_pdaf_16bit_whitelist_predicate(self) -> None:
        for valid_id in (0xC000, 0xC124, 0xCFFE, 0xD001, 0xE500, 0xFFFE):
            self.assertTrue(p207.is_cpapp_emount_pdaf_lens_id(valid_id), msg=hex(valid_id))
        for invalid_id in (0x0000, 0x4210, 0x8000, 0xCFFF, 0xDFFF, 0xFFFF, -1, 0x10000):
            self.assertFalse(p207.is_cpapp_emount_pdaf_lens_id(invalid_id), msg=hex(invalid_id))

    def test_18_pillar_b_rejects_inbody_fx3_focus_map_menu_and_stage_b_overlay_eopnotsupp(self) -> None:
        inbody = p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(
            attempt_inbody_fx3_focus_map_menu_toggle=True
        )
        self.assertFalse(inbody.admitted)
        self.assertFalse(inbody.fx3_has_inbody_focus_map_menu)
        self.assertTrue(inbody.inbody_menu_toggle_rejected_eopnotsupp)
        self.assertEqual(inbody.inbody_fx3_focus_map_overlay_frames, 0)
        self.assertEqual(inbody.errno_code, p207.EOPNOTSUPP_ERRNO)
        self.assertEqual(
            inbody.status_code,
            "BLOCKED_FX3_HAS_NO_INBODY_FOCUS_MAP_MENU_EOPNOTSUPP",
        )

        stage_b_ovl = p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(
            attempt_stage_b_local_focus_map_overlay_inject=True
        )
        self.assertFalse(stage_b_ovl.admitted)
        self.assertTrue(stage_b_ovl.stage_b_local_overlay_rejected_eopnotsupp)
        self.assertEqual(stage_b_ovl.inbody_fx3_focus_map_overlay_frames, 0)
        self.assertEqual(stage_b_ovl.errno_code, p207.EOPNOTSUPP_ERRNO)

    def test_19_pillar_b_allows_fx3_1_to_6fps_sq_and_up_to_120fps_on_external_mc(self) -> None:
        for low_fps in (1.0, 2.0, 4.0, 6.0):
            res = p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(sensor_fps=low_fps)
            self.assertTrue(res.admitted, msg=str(low_fps))
            self.assertTrue(res.fx3_low_fps_1_to_6_allowed, msg=str(low_fps))
            self.assertTrue(res.external_mc_pdaf_depth_streaming, msg=str(low_fps))
            self.assertFalse(res.blocked_ge_150fps_cutoff, msg=str(low_fps))
            self.assertEqual(res.errno_code, 0)

        for std_fps in (23.98, 24.0, 25.0, 29.97, 50.0, 59.94, 100.0, 119.88, 120.0, 149.9):
            res = p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(sensor_fps=std_fps)
            self.assertTrue(res.admitted, msg=str(std_fps))
            self.assertFalse(res.fx3_low_fps_1_to_6_allowed, msg=str(std_fps))
            self.assertTrue(res.external_mc_pdaf_depth_streaming, msg=str(std_fps))
            self.assertEqual(res.errno_code, 0)

    def test_20_pillar_b_blocks_ge_150fps_cutoff_including_200_and_240fps(self) -> None:
        for hfr_fps in (150.0, 180.0, 200.0, 239.76, 240.0):
            res = p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(sensor_fps=hfr_fps)
            self.assertFalse(res.admitted, msg=str(hfr_fps))
            self.assertTrue(res.blocked_ge_150fps_cutoff, msg=str(hfr_fps))
            self.assertFalse(res.external_mc_pdaf_depth_streaming, msg=str(hfr_fps))
            self.assertEqual(res.errno_code, p207.EOPNOTSUPP_ERRNO, msg=str(hfr_fps))
            self.assertEqual(
                res.status_code,
                "BLOCKED_EXTERNAL_FOCUS_MAP_FPS_GE_150_CUTOFF_EOPNOTSUPP",
                msg=str(hfr_fps),
            )

    def test_21_pillar_b_blocks_mount_adapter_manual_non_pdaf_and_no_lens(self) -> None:
        for bad_lens in (
            p207.LENS_TYPE_MOUNT_ADAPTER,
            p207.LENS_TYPE_NON_PDAF_MANUAL,
            p207.LENS_TYPE_NO_LENS,
        ):
            res = p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(
                lens_type=bad_lens,
                lens_id=0xFFFF,
            )
            self.assertFalse(res.admitted, msg=bad_lens)
            self.assertFalse(res.cpapp_emount_pdaf_valid, msg=bad_lens)
            self.assertFalse(res.external_mc_pdaf_depth_streaming, msg=bad_lens)
            self.assertEqual(res.errno_code, p207.EOPNOTSUPP_ERRNO)

        bad_id = p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(
            lens_type=p207.LENS_TYPE_SONY_EMOUNT_PDAF,
            lens_id=0x4210,
        )
        self.assertFalse(bad_id.admitted)
        self.assertEqual(bad_id.errno_code, p207.EOPNOTSUPP_ERRNO)

    def test_22_pillar_b_blocks_uvc_streaming_and_clip_playback_and_handles_idle_mc(self) -> None:
        uvc = p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(
            operating_state=p207.OP_STATE_UVC_STREAMING
        )
        self.assertFalse(uvc.admitted)
        self.assertEqual(uvc.errno_code, p207.EOPNOTSUPP_ERRNO)
        self.assertEqual(uvc.status_code, "BLOCKED_EXTERNAL_FOCUS_MAP_DURING_UVC_EOPNOTSUPP")

        pb = p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(
            operating_state=p207.OP_STATE_CLIP_PLAYBACK
        )
        self.assertFalse(pb.admitted)
        self.assertEqual(pb.errno_code, p207.EOPNOTSUPP_ERRNO)
        self.assertEqual(pb.status_code, "BLOCKED_EXTERNAL_FOCUS_MAP_DURING_PLAYBACK_EOPNOTSUPP")

        idle = p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(mc_client_connected=False)
        self.assertTrue(idle.admitted)
        self.assertFalse(idle.external_mc_pdaf_depth_streaming)
        self.assertEqual(idle.status_code, "ADMITTED_IDLE_NO_EXTERNAL_MC_CLIENT")

    def test_23_pillar_b_validates_invalid_parameters_and_evaluator_passes(self) -> None:
        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(operating_state="MENU")
        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(lens_type="PL_CINE")
        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_external_mc_focus_map_and_150fps_cutoff_hil(sensor_fps=0.0)

        pb = p207.evaluate_pillar_b_external_mc_focus_map_and_150fps_cutoff_hil()
        self.assertTrue(pb["passed"])

    def test_24_pillar_c_simult_recording_both_slots_healthy_redundant(self) -> None:
        res = p207.probe_simult_recording_auto_switch_hil(
            auto_switch_media="On",
            slot1_free_mb=65_536,
            slot2_free_mb=65_536,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.recording_continues)
        self.assertEqual(res.active_recording_slots, (1, 2))
        self.assertTrue(res.dual_card_redundant)
        self.assertFalse(res.single_card_continuation_active)
        self.assertEqual(res.dropped_frames, 0)
        self.assertEqual(res.rsv_orphan_count, 0)

    def test_25_pillar_c_simult_auto_switch_on_single_card_continuation_slot1_or_slot2_full(self) -> None:
        s1_full = p207.probe_simult_recording_auto_switch_hil(
            auto_switch_media="On",
            slot1_free_mb=0,
            slot2_free_mb=32_768,
        )
        self.assertTrue(s1_full.recording_continues)
        self.assertEqual(s1_full.active_recording_slots, (2,))
        self.assertTrue(s1_full.single_card_continuation_active)
        self.assertFalse(s1_full.dual_card_redundant)
        self.assertEqual(s1_full.dropped_frames, 0)
        self.assertEqual(s1_full.rsv_orphan_count, 0)

        s2_full = p207.probe_simult_recording_auto_switch_hil(
            auto_switch_media="On",
            slot1_free_mb=32_768,
            slot2_free_mb=0,
        )
        self.assertTrue(s2_full.recording_continues)
        self.assertEqual(s2_full.active_recording_slots, (1,))
        self.assertTrue(s2_full.single_card_continuation_active)

    def test_26_pillar_c_simult_auto_switch_on_resumes_dual_slot_after_fresh_card_swap(self) -> None:
        resumed = p207.probe_simult_recording_auto_switch_hil(
            auto_switch_media="On",
            slot1_free_mb=0,
            slot2_free_mb=32_768,
            fresh_card_reinserted=True,
        )
        self.assertTrue(resumed.recording_continues)
        self.assertEqual(resumed.active_recording_slots, (1, 2))
        self.assertTrue(resumed.dual_card_redundant)
        self.assertTrue(resumed.resumed_dual_slot_after_card_swap)
        self.assertEqual(resumed.dropped_frames, 0)
        self.assertEqual(resumed.rsv_orphan_count, 0)

    def test_27_pillar_c_simult_auto_switch_off_enforces_strict_dual_parity_halt(self) -> None:
        for s1_mb, s2_mb in ((0, 65_536), (65_536, 0)):
            halted = p207.probe_simult_recording_auto_switch_hil(
                auto_switch_media="Off",
                slot1_free_mb=s1_mb,
                slot2_free_mb=s2_mb,
            )
            self.assertTrue(halted.admitted)
            self.assertFalse(halted.recording_continues)
            self.assertEqual(halted.active_recording_slots, ())
            self.assertTrue(halted.strict_dual_parity_halted)
            self.assertFalse(halted.single_card_continuation_active)
            self.assertEqual(halted.rsv_orphan_count, 0)
            self.assertEqual(
                halted.status_code,
                "HALTED_STRICT_DUAL_BACKUP_PARITY_AUTO_SWITCH_OFF",
            )

    def test_28_pillar_c_simult_both_slots_full_halts_cleanly_and_validates_inputs(self) -> None:
        for mode in ("On", "Off"):
            both_full = p207.probe_simult_recording_auto_switch_hil(
                auto_switch_media=mode,
                slot1_free_mb=0,
                slot2_free_mb=0,
            )
            self.assertFalse(both_full.recording_continues)
            self.assertTrue(both_full.both_slots_full_halted)
            self.assertEqual(both_full.active_recording_slots, ())
            self.assertEqual(both_full.rsv_orphan_count, 0)

        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_simult_recording_auto_switch_hil(auto_switch_media="Relay")
        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_simult_recording_auto_switch_hil(slot1_free_mb=-1)

    def test_29_pillar_d_shockless_wb_off_and_1_2_3_smooth_ramps_across_24p_to_240fps(self) -> None:
        off_res = p207.probe_shockless_wb_and_kelvin_bypass_hil(
            shockless_wb_setting="Off",
            sensor_fps=24.0,
            transition_trigger=p207.WB_TRIGGER_PRESET_SWITCH,
        )
        self.assertTrue(off_res.admitted)
        self.assertEqual(off_res.transition_frames, 0)
        self.assertTrue(off_res.immediate_zero_frame_applied)

        for fps in (1.0, 23.98, 24.0, 59.94, 119.88, 200.0, 240.0):
            s1 = p207.probe_shockless_wb_and_kelvin_bypass_hil(
                shockless_wb_setting="1",
                sensor_fps=fps,
            )
            s2 = p207.probe_shockless_wb_and_kelvin_bypass_hil(
                shockless_wb_setting="2",
                sensor_fps=fps,
            )
            s3 = p207.probe_shockless_wb_and_kelvin_bypass_hil(
                shockless_wb_setting="3",
                sensor_fps=fps,
            )
            self.assertTrue(s1.all_framerates_supported)
            self.assertGreaterEqual(s1.transition_frames, 1)
            self.assertLessEqual(s1.transition_frames, s2.transition_frames)
            self.assertLessEqual(s2.transition_frames, s3.transition_frames)

    def test_30_pillar_d_shockless_wb_exact_frame_counts_at_24p_and_240fps(self) -> None:
        s3_24 = p207.probe_shockless_wb_and_kelvin_bypass_hil(
            shockless_wb_setting="3",
            sensor_fps=24.0,
        )
        self.assertEqual(s3_24.transition_frames, 48)
        self.assertAlmostEqual(s3_24.ramp_duration_seconds, 2.0)

        s1_240 = p207.probe_shockless_wb_and_kelvin_bypass_hil(
            shockless_wb_setting="1",
            sensor_fps=240.0,
        )
        self.assertEqual(s1_240.transition_frames, 120)
        self.assertAlmostEqual(s1_240.ramp_duration_seconds, 0.5)

    def test_31_pillar_d_ctemp_filter_kelvin_edit_bypasses_shockless_wb_in_0_frames(self) -> None:
        for step in ("1", "2", "3"):
            res = p207.probe_shockless_wb_and_kelvin_bypass_hil(
                shockless_wb_setting=step,
                sensor_fps=59.94,
                transition_trigger=p207.WB_TRIGGER_CTEMP_KELVIN_EDIT,
                from_kelvin=5600,
                to_kelvin=3200,
            )
            self.assertTrue(res.admitted, msg=step)
            self.assertTrue(res.bypassed_shockless_smoothing, msg=step)
            self.assertTrue(res.immediate_zero_frame_applied, msg=step)
            self.assertEqual(res.transition_frames, 0, msg=step)
            self.assertEqual(res.ramp_duration_seconds, 0.0, msg=step)
            self.assertEqual(
                res.status_code,
                "ADMITTED_CTEMP_KELVIN_EDIT_IMMEDIATE_0_FRAME_BYPASS",
            )

    def test_32_pillar_d_ab_gm_fine_grid_shift_bypasses_shockless_wb_in_0_frames(self) -> None:
        for step in ("1", "2", "3"):
            res = p207.probe_shockless_wb_and_kelvin_bypass_hil(
                shockless_wb_setting=step,
                sensor_fps=119.88,
                transition_trigger=p207.WB_TRIGGER_AB_GM_FINE_GRID,
                ab_gm_grid_offset="A3 M2",
            )
            self.assertTrue(res.admitted, msg=step)
            self.assertTrue(res.bypassed_shockless_smoothing, msg=step)
            self.assertTrue(res.immediate_zero_frame_applied, msg=step)
            self.assertEqual(res.transition_frames, 0, msg=step)
            self.assertEqual(
                res.status_code,
                "ADMITTED_AB_GM_FINE_GRID_IMMEDIATE_0_FRAME_BYPASS",
            )

    def test_33_pillar_d_shockless_wb_rejects_invalid_step_and_validates_bounds(self) -> None:
        for bad_step in ("4", "Fast", "Slow", "Auto", ""):
            res = p207.probe_shockless_wb_and_kelvin_bypass_hil(shockless_wb_setting=bad_step)
            self.assertFalse(res.admitted, msg=bad_step)
            self.assertEqual(res.errno_code, p207.EINVAL_ERRNO, msg=bad_step)

        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_shockless_wb_and_kelvin_bypass_hil(transition_trigger="UNKNOWN")
        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_shockless_wb_and_kelvin_bypass_hil(sensor_fps=300.0)
        with self.assertRaises(p207.RealHwDesqueezeFocusMapSimultShocklessWbError):
            p207.probe_shockless_wb_and_kelvin_bypass_hil(from_kelvin=2000)

    def test_34_pillar_d_hard_safety_redline_baseline_and_all_8_forbidden_actions(self) -> None:
        base = p207.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.spi_nor_write_authorized)
        self.assertFalse(base.el3_payload_transmit_authorized)
        self.assertEqual(base.physical_usb_packets_emitted, 0)
        self.assertEqual(base.otp_fuse_touches, 0)
        self.assertEqual(base.rpmb_counter_increments, 0)
        self.assertEqual(base.desqueeze_baked_into_raw_or_xavc_frames, 0)
        self.assertEqual(base.inbody_fx3_focus_map_overlay_frames, 0)

        for flag_name in (
            "authorize_persistent_emmc_writes",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "bake_desqueeze_into_raw_or_xavc",
            "inject_inbody_fx3_focus_map_overlay",
        ):
            bad = p207.probe_hard_safety_redline(**{flag_name: True})
            self.assertFalse(bad.valid, msg=flag_name)
            self.assertFalse(bad.persistent_emmc_writes_authorized)
            self.assertFalse(bad.spi_nor_write_authorized)
            self.assertFalse(bad.el3_payload_transmit_authorized)
            self.assertEqual(bad.physical_usb_packets_emitted, 0)
            self.assertEqual(bad.otp_fuse_touches, 0)
            self.assertEqual(bad.rpmb_counter_increments, 0)
            self.assertTrue(bad.status_code.startswith("FAIL_CLOSED_REDLINE_BLOCKED:"))

    def test_35_pillar_d_combined_multi_redline_violation_blocked(self) -> None:
        combo = p207.probe_hard_safety_redline(
            authorize_persistent_emmc_writes=True,
            bake_desqueeze_into_raw_or_xavc=True,
            inject_inbody_fx3_focus_map_overlay=True,
        )
        self.assertFalse(combo.valid)
        self.assertIn("PERSISTENT_EMMC_WRITE", combo.blocked_action)
        self.assertIn("BAKE_DESQUEEZE_INTO_MASTER_RAW_OR_XAVC", combo.blocked_action)
        self.assertIn("INBODY_FX3_FOCUS_MAP_OVERLAY_INJECT", combo.blocked_action)

    def test_36_pillar_c_d_evaluator_matrix_passes_100pct(self) -> None:
        pcd = p207.evaluate_pillar_c_d_simult_autoswitch_shockless_wb_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["blocked_redline_probes"]), 8)

    def test_37_clean_room_audit_deterministic_digest_and_zero_leaks(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p207.run_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil(
            force_clean_room=True
        )
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1["stage_index"], 37)
        self.assertEqual(r1["stage_total"], 37)
        self.assertEqual(r1["milestone"], "37/37")
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r1["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(r1["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_38_default_mode_audit_passes_all_pillars_and_redlines(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(rep["pillar_a_desqueeze_165x_4locks_and_bypass_hil"]["passed"])
        self.assertTrue(rep["pillar_b_external_mc_focus_map_and_150fps_cutoff_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_simult_autoswitch_shockless_wb_and_redlines"]["passed"])
        self.assertFalse(rep["redlines"]["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["redlines"]["spi_nor_write_authorized"])
        self.assertFalse(rep["redlines"]["el3_payload_transmit_authorized"])
        self.assertEqual(rep["redlines"]["physical_usb_packets_emitted"], 0)
        self.assertEqual(rep["redlines"]["otp_fuse_touches"], 0)
        self.assertEqual(rep["redlines"]["rpmb_counter_increments"], 0)
        self.assertEqual(rep["redlines"]["desqueeze_baked_into_raw_or_xavc_frames"], 0)
        self.assertEqual(rep["redlines"]["inbody_fx3_focus_map_overlay_frames"], 0)

    def test_39_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py"
                ),
                "--self-test",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 207 Stage 37 (37/37)", p_sum.stdout)

        p_json = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py"
                ),
                "--self-test",
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
        self.assertEqual(parsed["stage_index"], 37)
        self.assertEqual(parsed["milestone"], "37/37")

    def test_40_inprocess_main_summary_and_clean_room_exit_zero(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p207.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 207 Stage 37 (37/37)", buf.getvalue())

    def test_41_fx3_vm_coemulation_suite_includes_stage37_and_skip_phase207(self) -> None:
        rep_on, _dt = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil", rep_on)
        s37 = rep_on["stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil"]
        self.assertTrue(s37["all_checks_passed"])
        self.assertFalse(s37["persistent_emmc_writes_authorized"])
        self.assertFalse(s37["spi_nor_write_authorized"])
        self.assertFalse(s37["el3_payload_transmit_authorized"])
        self.assertEqual(s37["physical_usb_packets_emitted"], 0)
        self.assertEqual(s37["otp_fuse_touches"], 0)
        self.assertEqual(s37["rpmb_counter_increments"], 0)
        self.assertEqual(s37["desqueeze_baked_into_raw_or_xavc_frames"], 0)
        self.assertEqual(s37["inbody_fx3_focus_map_overlay_frames"], 0)
        self.assertEqual(s37["raw_firmware_bytes_leaked"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 37)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil", rep_skip)
        self.assertGreaterEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), 36)

    def test_42_all_37_of_37_stages_present_and_passing_in_suite(self) -> None:
        rep, _dt = _get_clean_room_suite()
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 38):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"], msg=matches[0])

    def test_43_suite_subprocess_summary_and_skip_phase207_flag(self) -> None:
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
        self.assertIn(
            "realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil=CLEAN_ROOM_SYNTHETIC",
            proc.stdout,
        )

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase207",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn(
            "realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil=",
            proc_skip.stdout,
        )

    def test_44_suite_37_stages_under_6s_wall_clock_ceiling_and_json_cli(self) -> None:
        rep_clean, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 37)
        self.assertLess(dt_clean, 6.0)

        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_def if re.match(r"^stage\d+_", k)]), 37)
        self.assertLess(dt_def, 6.0)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_json = suite.main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn("stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil", parsed)

    def test_45_source_hygiene_rdonly_only_and_no_forbidden_write_flags_or_ports(self) -> None:
        src = (
            FX3_VM_DIR / "realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py"
        ).read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("O_WR" + "ONLY", src)
        self.assertNotIn("O_RD" + "WR", src)
        self.assertNotIn("87" + "68", src)

    def test_46_is_forced_clean_room_truthy_and_falsy_values(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on", " 1 "):
            self.assertTrue(
                p207.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": truthy}),
                msg=truthy,
            )
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(
                p207.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": falsy}),
                msg=falsy,
            )

    def test_47_missing_work_root_gracefully_falls_back_to_clean_room_synthetic(self) -> None:
        non_existent = str(REPO_ROOT / "work" / "__nonexistent_phase207_donor_root__")
        env_missing = {
            "FX3_FX6_FORCE_CLEAN_ROOM": "0",
            "FX3_FX6_MAC_WORK_ROOT": non_existent,
        }
        paths = p207.resolve_phase207_donor_paths(env=env_missing)
        self.assertEqual(len(paths), 12)
        da = p207.inspect_phase207_donors(force_clean_room=True, env=env_missing)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_48_multi_reason_desqueeze_suppression_combines_all_active_bypasses(self) -> None:
        multi = p207.probe_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_option="1.6x",
            hdmi_raw_output="On",
            rec_media_dur_hdmi="Off(HDMI Only)",
            log_shooting="Off",
            remote_shooting_active=True,
            capture_mode="Photo",
        )
        self.assertTrue(multi.admitted)
        self.assertFalse(multi.display_desqueeze_active)
        self.assertEqual(multi.applied_horizontal_scale, 1.0)
        self.assertEqual(
            multi.suppression_reasons,
            (
                "HDMI_RAW_OUTPUT_ON",
                "REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY",
                "LOG_SHOOTING_OFF",
                "REMOTE_SHOOTING_ACTIVE",
                "STILL_PHOTO_CAPTURE_MODE",
            ),
        )


if __name__ == "__main__":
    unittest.main()
