#!/usr/bin/env python3
"""Unit tests for Phase 242 Stage 45 (`45/45` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `Ver. 2.00..7.02`) Wave-35 `[Emphasized REC Display]`
& `[Grid Line Display]` HDMI Info Routing vs Forced `[Off(HDMI Only)]` / `RAW` Clean-Feed Lock,
`[Touch Operation]` 4-Item `[Camera Settings Reset]` Survival & Unattended Bench Tap Guard, and
`[Monitor Brightness]` `[Manual]` (`-2..+2`) vs `[Sunny Weather]` Indoor Over-Brightness &
`NP-FZ100` Power Guard HIL Co-Emulator.
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
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator as p242  # noqa: E402


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
            p242.run_phase242_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil(
                force_clean_room=True
            )
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = (
            p242.run_phase242_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil()
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


class TestPhase242EmphasizedRecGridHdmiTouchSunnyCoEmulator(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 1: Schema, Milestone 45/45 & O_RDONLY Donor Inspection (10)
    # ------------------------------------------------------------------
    def test_01_schema_version_stage_45_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p242.SCHEMA_ID,
            "realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator_v1",
        )
        self.assertEqual(p242.PHASE_242_SCHEMA, p242.SCHEMA_ID)
        self.assertEqual(p242.PHASE_242_VERSION, "242.0.0")
        self.assertEqual(p242.STAGE_INDEX, 45)
        self.assertEqual(p242.STAGE_TOTAL, 45)
        self.assertEqual(p242.MILESTONE_LABEL, "45/45")
        self.assertEqual(
            p242.STAGE_NAME,
            "stage45_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil",
        )
        self.assertEqual(p242.FX3_MODEL_ID, 0x91030080)
        self.assertTrue(p242.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p242.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p242.CNFLASHA_MUTATION_BYTES, 0)
        self.assertEqual(p242.PHYSICAL_DEVICE_WRITES, 0)
        self.assertFalse(p242.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p242.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p242.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p242.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p242.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p242.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p242.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p242.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p242.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p242.HDMI_ONLY_OR_RAW_BAKED_RECFRAME_OR_GRID_FRAMES, 0)
        self.assertEqual(p242.HDMI_LOCAL_ONLY_MARKER_ZEBRA_PEAKING_LEAKED_PIXELS, 0)
        self.assertEqual(p242.UNATTENDED_BENCH_ACCIDENTAL_TOUCH_EVENTS, 0)
        self.assertEqual(p242.INDOOR_SUNNY_WEATHER_UNCLAMPED_EVENTS, 0)
        self.assertEqual(p242.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p242.DONOR_ACCESS_MODE, "O_RDONLY")

    def test_02_donor_inspection_fast_sub_100ms_bounded_and_cached(self) -> None:
        p242._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p242.inspect_phase242_donors()
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p242.inspect_phase242_donors()
        dt2 = time.monotonic() - t1

        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        self.assertEqual(da1.donor_files_inspected, 14)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(da1.access_mode, "O_RDONLY")
        self.assertIn(da1.source_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(da1, da2)
        self.assertLess(dt1, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.1)
        self.assertLess(dt2, 0.25 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.02)

    def test_03_clean_room_donor_inspection_synthetic_parity(self) -> None:
        da = p242.inspect_phase242_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertTrue(da.emphasized_rec_and_grid_hdmi_cleanfeed_proven)
        self.assertTrue(da.touch_operation_4item_reset_survival_proven)
        self.assertTrue(da.monitor_brightness_manual_vs_sunny_weather_proven)
        self.assertEqual(da.donor_files_inspected, 14)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_04_env_force_clean_room_flag_variants(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on"):
            self.assertTrue(p242.is_forced_clean_room({p242.ENV_FORCE_CLEAN_ROOM: truthy}))
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(p242.is_forced_clean_room({p242.ENV_FORCE_CLEAN_ROOM: falsy}))

    def test_05_env_clean_room_sentinel_paths_never_touch_local_donors(self) -> None:
        paths = p242.resolve_phase242_donor_paths(env={p242.ENV_FORCE_CLEAN_ROOM: "1"})
        self.assertEqual(len(paths), 14)
        for p in paths.values():
            self.assertIn(p242.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_06_nonexistent_donor_paths_fall_back_cleanly_to_synthetic(self) -> None:
        missing_paths = {
            k: Path("/nonexistent_phase242_work_root_xyz") / rel
            for k, rel in p242.DONOR_RELPATHS.items()
        }
        with unittest.mock.patch.object(
            p242, "resolve_phase242_donor_paths", return_value=missing_paths
        ):
            da = p242.inspect_phase242_donors(force_clean_room=False)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_07_compact_donor_tokens_verified_for_emphasized_rec_grid_touch_and_brightness(
        self,
    ) -> None:
        da = p242.inspect_phase242_donors()
        for tok in (
            "Emphasized REC Display",
            "Grid Line Display",
            "Grid Line Type",
            "Rule of 3rds Grid",
            "Square Grid",
            "Diag. + Square Grid",
            "HDMI Info. Display",
            "Rec. Media dur HDMI Output",
            "Off(HDMI Only)",
            "RAW Output",
            "Touch Operation",
            "On: Playback Only",
            "Touch Sensitivity",
            "Swipe Up",
            "Open the Fn Menu",
            "Touch Func. in Shooting",
            "Touch Tracking",
            "Touch Focus",
            "Brightness",
            "Manual",
            "Sunny Weather",
            "Camera Settings Reset",
            "Initialize",
        ):
            self.assertEqual(da.fx3_string_en_f.marker_hits.get(tok), 1, msg=tok)

    def test_08_large_donors_use_bounded_4kib_windows_only(self) -> None:
        da = p242.inspect_phase242_donors()
        for attr in (
            "fx3_appfw",
            "fx6_appfw",
            "fx3_cpapp",
            "fx6_cpapp",
            "fx3_libmpr",
            "fx6_libmpr",
            "fx3_bk4",
            "fx6_bk4",
        ):
            summary = getattr(da, attr)
            self.assertTrue(summary.bounded_windows_only, msg=attr)
            max_expected = (len(p242.LARGE_DONOR_WINDOWS[attr]) + 1) * p242.BOUNDED_WINDOW_MAX_BYTES
            self.assertLessEqual(summary.bytes_read_total, max_expected, msg=attr)
            self.assertEqual(summary.file_bytes, p242.EXPECTED_DONOR_BYTES[attr], msg=attr)

    def test_09_active_mode_awareness_matches_environment_flag(self) -> None:
        forced = p242.is_forced_clean_room(os.environ)
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        if forced:
            self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(
                rep["source_mode"],
                ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
            )

    def test_10_all_8_fx3_firmware_versions_200_through_702_supported(self) -> None:
        self.assertEqual(len(p242.VALID_FX3_FIRMWARE_VERSIONS), 8)
        for ver in p242.VALID_FX3_FIRMWARE_VERSIONS:
            res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(firmware_version=ver)
            self.assertTrue(res.admitted, msg=ver)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 45A — [Emphasized REC Display] & [Grid Line Display]
    #          HDMI Info Routing vs [Off(HDMI Only)] / RAW Clean-Feed Lock (20)
    # ------------------------------------------------------------------
    def test_11_emphasized_rec_default_on_and_reset_by_camera_settings_reset(self) -> None:
        self.assertEqual(p242.DEFAULT_EMPHASIZED_REC_DISPLAY, "On")
        res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_emphasized_rec_display="Off",
            configured_grid_line_display="On",
            configured_grid_line_type="Square Grid",
            reset_action="Camera Settings Reset",
            shooting_state=p242.SHOOTING_STATE_MOVIE_REC,
            configured_hdmi_info_display="Off",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_emphasized_rec_display, "On")
        self.assertTrue(res.emphasized_rec_reset_by_camera_settings_reset)
        self.assertTrue(res.local_lcd_emphasized_rec_rendered)

    def test_12_grid_line_display_and_all_3_types_survive_camera_settings_reset(self) -> None:
        self.assertEqual(
            p242.VALID_GRID_LINE_TYPES,
            ("Rule of 3rds Grid", "Square Grid", "Diag. + Square Grid"),
        )
        for gtype in p242.VALID_GRID_LINE_TYPES:
            res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
                configured_emphasized_rec_display="Off",
                configured_grid_line_display="On",
                configured_grid_line_type=gtype,
                reset_action="Camera Settings Reset",
                shooting_state=p242.SHOOTING_STATE_MOVIE_REC,
                configured_hdmi_info_display="Off",
            )
            self.assertTrue(res.admitted, msg=gtype)
            self.assertTrue(res.grid_line_reset_only_by_initialize, msg=gtype)
            self.assertTrue(res.grid_line_survived_camera_settings_reset, msg=gtype)
            self.assertTrue(res.emphasized_rec_vs_grid_reset_split_verified, msg=gtype)
            self.assertEqual(res.effective_grid_line_display, "On", msg=gtype)
            self.assertEqual(res.effective_grid_line_type, gtype, msg=gtype)

    def test_13_initialize_resets_both_emphasized_rec_to_on_and_grid_line_to_off_rule_of_3rds(
        self,
    ) -> None:
        res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_emphasized_rec_display="Off",
            configured_grid_line_display="On",
            configured_grid_line_type="Diag. + Square Grid",
            reset_action="Initialize",
            shooting_state=p242.SHOOTING_STATE_MOVIE_REC,
            configured_hdmi_info_display="Off",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_emphasized_rec_display, "On")
        self.assertEqual(res.effective_grid_line_display, "Off")
        self.assertEqual(res.effective_grid_line_type, "Rule of 3rds Grid")

    def test_14_movie_rec_and_sq_rec_activate_red_border_when_emphasized_rec_on(self) -> None:
        for state in (p242.SHOOTING_STATE_MOVIE_REC, p242.SHOOTING_STATE_SQ_REC):
            res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
                configured_emphasized_rec_display="On",
                configured_grid_line_display="Off",
                shooting_state=state,
                configured_hdmi_info_display="Off",
            )
            self.assertTrue(res.admitted, msg=state)
            self.assertTrue(res.movie_or_sq_recording_active, msg=state)
            self.assertTrue(res.local_lcd_emphasized_rec_rendered, msg=state)

    def test_15_standby_and_still_never_render_emphasized_rec_red_border(self) -> None:
        for state in (p242.SHOOTING_STATE_STANDBY, p242.SHOOTING_STATE_STILL):
            res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
                configured_emphasized_rec_display="On",
                configured_grid_line_display="On",
                shooting_state=state,
                configured_hdmi_info_display="On",
            )
            self.assertTrue(res.admitted, msg=state)
            self.assertFalse(res.movie_or_sq_recording_active, msg=state)
            self.assertFalse(res.local_lcd_emphasized_rec_rendered, msg=state)
            self.assertFalse(res.hdmi_emphasized_rec_rendered, msg=state)
            self.assertTrue(res.hdmi_grid_line_rendered, msg=state)

    def test_16_forcing_emphasized_rec_red_border_in_standby_or_still_blocked_eopnotsupp(
        self,
    ) -> None:
        for state in (p242.SHOOTING_STATE_STANDBY, p242.SHOOTING_STATE_STILL):
            res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
                shooting_state=state,
                attempt_force_rec_frame_in_standby_or_still=True,
            )
            self.assertFalse(res.admitted, msg=state)
            self.assertEqual(res.errno_code, p242.EOPNOTSUPP_ERRNO, msg=state)

    def test_17_hdmi_info_on_routes_both_emphasized_rec_and_grid_line_while_blanking_lcd(
        self,
    ) -> None:
        res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_emphasized_rec_display="On",
            configured_grid_line_display="On",
            configured_grid_line_type="Rule of 3rds Grid",
            shooting_state=p242.SHOOTING_STATE_MOVIE_REC,
            hdmi_connected=True,
            configured_hdmi_info_display="On",
            rec_media_dur_hdmi_output="On",
            hdmi_raw_output="Off",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_hdmi_info_display, "On")
        self.assertTrue(res.camera_lcd_blanked_by_hdmi_info)
        self.assertFalse(res.local_lcd_emphasized_rec_rendered)
        self.assertFalse(res.local_lcd_grid_line_rendered)
        self.assertTrue(res.hdmi_emphasized_rec_rendered)
        self.assertTrue(res.hdmi_grid_line_rendered)
        self.assertTrue(res.hdmi_status_osd_rendered)
        self.assertGreater(res.hdmi_baked_overlay_pixels, 0)

    def test_18_local_lcd_only_marker_zebra_peaking_never_route_to_hdmi_even_when_hdmi_info_on(
        self,
    ) -> None:
        res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_emphasized_rec_display="On",
            configured_grid_line_display="On",
            configured_hdmi_info_display="On",
            local_marker_display_on=True,
            local_zebra_display_on=True,
            local_peaking_display_on=True,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.hdmi_local_only_marker_rendered)
        self.assertFalse(res.hdmi_local_only_zebra_rendered)
        self.assertFalse(res.hdmi_local_only_peaking_rendered)
        self.assertEqual(res.hdmi_local_only_marker_zebra_peaking_leaked_pixels, 0)

    def test_19_attempt_to_route_local_only_assist_to_hdmi_blocked_eopnotsupp(self) -> None:
        res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_hdmi_info_display="On",
            attempt_route_local_only_assist_to_hdmi=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p242.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.hdmi_local_only_marker_zebra_peaking_leaked_pixels, 0)

    def test_20_hdmi_info_off_keeps_clean_hdmi_and_renders_rec_frame_and_grid_on_local_lcd(
        self,
    ) -> None:
        res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_emphasized_rec_display="On",
            configured_grid_line_display="On",
            shooting_state=p242.SHOOTING_STATE_MOVIE_REC,
            hdmi_connected=True,
            configured_hdmi_info_display="Off",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_hdmi_info_display, "Off")
        self.assertFalse(res.camera_lcd_blanked_by_hdmi_info)
        self.assertTrue(res.local_lcd_emphasized_rec_rendered)
        self.assertTrue(res.local_lcd_grid_line_rendered)
        self.assertFalse(res.hdmi_emphasized_rec_rendered)
        self.assertFalse(res.hdmi_grid_line_rendered)
        self.assertEqual(res.hdmi_baked_overlay_pixels, 0)

    def test_21_hdmi_disconnected_renders_locally_with_zero_hdmi_pixels(self) -> None:
        res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_emphasized_rec_display="On",
            configured_grid_line_display="On",
            shooting_state=p242.SHOOTING_STATE_MOVIE_REC,
            hdmi_connected=False,
            configured_hdmi_info_display="On",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_hdmi_info_display, "Off")
        self.assertFalse(res.camera_lcd_blanked_by_hdmi_info)
        self.assertTrue(res.local_lcd_emphasized_rec_rendered)
        self.assertTrue(res.local_lcd_grid_line_rendered)
        self.assertEqual(res.hdmi_baked_overlay_pixels, 0)

    def test_22_off_hdmi_only_automatically_forces_hdmi_info_off_zero_baked_frames(self) -> None:
        res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_emphasized_rec_display="On",
            configured_grid_line_display="On",
            configured_grid_line_type="Diag. + Square Grid",
            shooting_state=p242.SHOOTING_STATE_MOVIE_REC,
            hdmi_connected=True,
            configured_hdmi_info_display="On",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            hdmi_raw_output="Off",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.forced_off_by_hdmi_only_clamp)
        self.assertFalse(res.forced_off_by_hdmi_raw_clamp)
        self.assertTrue(res.hdmi_clean_feed_clamp_active)
        self.assertEqual(res.effective_hdmi_info_display, "Off")
        self.assertFalse(res.camera_lcd_blanked_by_hdmi_info)
        self.assertTrue(res.local_lcd_emphasized_rec_rendered)
        self.assertTrue(res.local_lcd_grid_line_rendered)
        self.assertFalse(res.hdmi_emphasized_rec_rendered)
        self.assertFalse(res.hdmi_grid_line_rendered)
        self.assertEqual(res.hdmi_baked_overlay_pixels, 0)
        self.assertEqual(res.hdmi_only_or_raw_baked_recframe_or_grid_frames, 0)

    def test_23_hdmi_raw_output_automatically_forces_hdmi_info_off_zero_baked_frames(self) -> None:
        res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_emphasized_rec_display="On",
            configured_grid_line_display="On",
            configured_grid_line_type="Square Grid",
            shooting_state=p242.SHOOTING_STATE_MOVIE_REC,
            hdmi_connected=True,
            configured_hdmi_info_display="On",
            rec_media_dur_hdmi_output="On",
            hdmi_raw_output="On",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.forced_off_by_hdmi_only_clamp)
        self.assertTrue(res.forced_off_by_hdmi_raw_clamp)
        self.assertTrue(res.hdmi_clean_feed_clamp_active)
        self.assertEqual(res.effective_hdmi_info_display, "Off")
        self.assertFalse(res.hdmi_emphasized_rec_rendered)
        self.assertFalse(res.hdmi_grid_line_rendered)
        self.assertEqual(res.hdmi_baked_overlay_pixels, 0)
        self.assertEqual(res.hdmi_only_or_raw_baked_recframe_or_grid_frames, 0)

    def test_24_off_hdmi_only_plus_raw_dual_clamp_forces_hdmi_info_off(self) -> None:
        res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_emphasized_rec_display="On",
            configured_grid_line_display="On",
            shooting_state=p242.SHOOTING_STATE_SQ_REC,
            hdmi_connected=True,
            configured_hdmi_info_display="On",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            hdmi_raw_output="On",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.forced_off_by_hdmi_only_clamp)
        self.assertTrue(res.forced_off_by_hdmi_raw_clamp)
        self.assertEqual(res.effective_hdmi_info_display, "Off")
        self.assertEqual(res.hdmi_baked_overlay_pixels, 0)

    def test_25_attempt_to_bypass_hdmi_only_or_raw_cleanfeed_clamp_blocked_eopnotsupp(
        self,
    ) -> None:
        for kw in (
            {"rec_media_dur_hdmi_output": "Off(HDMI Only)", "hdmi_raw_output": "Off"},
            {"rec_media_dur_hdmi_output": "On", "hdmi_raw_output": "On"},
        ):
            res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
                configured_hdmi_info_display="On",
                attempt_bypass_hdmi_only_or_raw_cleanfeed_clamp=True,
                **kw,
            )
            self.assertFalse(res.admitted, msg=str(kw))
            self.assertEqual(res.errno_code, p242.EOPNOTSUPP_ERRNO, msg=str(kw))
            self.assertEqual(res.hdmi_only_or_raw_baked_recframe_or_grid_frames, 0)

    def test_26_slot1_camset01_to_10_restores_emphasized_rec_with_zero_nvram_writes(self) -> None:
        for slot_idx in (1, 5, 10):
            fname = f"CAMSET{slot_idx:02d}.DAT"
            res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
                configured_emphasized_rec_display="Off",
                reset_action="Camera Settings Reset",
                restore_from_slot1_camset=fname,
                saved_camset_emphasized_rec_display="Off",
                configured_hdmi_info_display="Off",
            )
            self.assertTrue(res.admitted, msg=fname)
            self.assertEqual(res.effective_emphasized_rec_display, "Off", msg=fname)
            self.assertEqual(res.bk4_persistent_nvram_writes, 0, msg=fname)

    def test_27_invalid_camset_filenames_or_saved_values_rejected_einval(self) -> None:
        for bad_camset in ("CAMSET00.DAT", "CAMSET11.DAT", "ALLCAM01.DAT", "../CAMSET01.DAT"):
            res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
                restore_from_slot1_camset=bad_camset
            )
            self.assertFalse(res.admitted, msg=bad_camset)
            self.assertEqual(res.errno_code, p242.EINVAL_ERRNO, msg=bad_camset)

        res_val = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            restore_from_slot1_camset="CAMSET01.DAT",
            saved_camset_emphasized_rec_display="Auto",
        )
        self.assertFalse(res_val.admitted)
        self.assertEqual(res_val.errno_code, p242.EINVAL_ERRNO)

    def test_28_emphasized_rec_vs_grid_line_3step_reset_lifecycle(self) -> None:
        lc = p242.simulate_emphasized_rec_vs_grid_line_reset_lifecycle()
        self.assertTrue(lc["lifecycle_verified"])
        self.assertEqual(lc["step1_configured"]["effective_emphasized_rec_display"], "Off")
        self.assertEqual(lc["step2_camera_settings_reset_split"]["effective_emphasized_rec_display"], "On")
        self.assertEqual(lc["step2_camera_settings_reset_split"]["effective_grid_line_display"], "On")
        self.assertEqual(
            lc["step2_camera_settings_reset_split"]["effective_grid_line_type"],
            "Diag. + Square Grid",
        )
        self.assertEqual(lc["step3_initialize_full_clear"]["effective_grid_line_display"], "Off")
        self.assertEqual(
            lc["step3_initialize_full_clear"]["effective_grid_line_type"],
            "Rule of 3rds Grid",
        )

    def test_29_submodel_45a_invalid_parameters_rejected_einval(self) -> None:
        for kw in (
            {"firmware_version": "1.00"},
            {"configured_emphasized_rec_display": "Blink"},
            {"configured_grid_line_display": "Auto"},
            {"configured_grid_line_type": "Golden Spiral"},
            {"reset_action": "Soft Reboot"},
            {"shooting_state": "interval_rec"},
            {"configured_hdmi_info_display": "Partial"},
            {"rec_media_dur_hdmi_output": "SDI Only"},
            {"hdmi_raw_output": "16bit"},
        ):
            res = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(**kw)
            self.assertFalse(res.admitted, msg=str(kw))
            self.assertEqual(res.errno_code, p242.EINVAL_ERRNO, msg=str(kw))

    def test_30_evaluate_pillar_a_summary_passes_all_invariants(self) -> None:
        pa = p242.evaluate_pillar_a_emphasized_rec_and_grid_hdmi_cleanfeed_hil()
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["grid_3type_hdmi_info_routed_matrix"]), 3)
        self.assertEqual(
            pa["local_lcd_only_assist_overlays"],
            ["Marker Display", "Zebra Display", "Peaking Display"],
        )

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 45B — [Touch Operation] 4-Item [Camera Settings Reset]
    #          Survival & Unattended Bench Tap Guard (12)
    # ------------------------------------------------------------------
    def test_31_all_4_touch_setup_items_and_factory_defaults(self) -> None:
        self.assertEqual(
            p242.ALL_4_TOUCH_SETUP_ITEMS,
            (
                "Touch Operation",
                "Touch Sensitivity",
                "Swipe Up",
                "Touch Func. in Shooting",
            ),
        )
        self.assertEqual(p242.DEFAULT_TOUCH_OPERATION, "On")
        self.assertEqual(p242.DEFAULT_TOUCH_SENSITIVITY, "Standard")
        self.assertEqual(p242.DEFAULT_SWIPE_UP, "Open the Fn Menu")
        self.assertEqual(p242.DEFAULT_TOUCH_FUNC_IN_SHOOTING, "Touch Tracking")

    def test_32_all_4_touch_items_survive_camera_settings_reset_intact(self) -> None:
        res = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation="Off",
            configured_touch_sensitivity="Sensitive",
            configured_swipe_up="Off",
            configured_touch_func_in_shooting="Touch Focus",
            reset_action="Camera Settings Reset",
            bench_unattended_rehearsal_active=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.reset_only_by_initialize)
        self.assertTrue(res.all_4_items_survived_camera_settings_reset)
        self.assertEqual(res.effective_touch_operation, "Off")
        self.assertEqual(res.effective_touch_sensitivity, "Sensitive")
        self.assertEqual(res.effective_swipe_up, "Off")
        self.assertEqual(res.effective_touch_func_in_shooting, "Touch Focus")

    def test_33_initialize_restores_all_4_touch_items_to_factory_defaults(self) -> None:
        res = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation="Off",
            configured_touch_sensitivity="Sensitive",
            configured_swipe_up="Off",
            configured_touch_func_in_shooting="Off",
            reset_action="Initialize",
            bench_unattended_rehearsal_active=False,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.cleared_to_defaults_by_initialize)
        self.assertEqual(res.effective_touch_operation, "On")
        self.assertEqual(res.effective_touch_sensitivity, "Standard")
        self.assertEqual(res.effective_swipe_up, "Open the Fn Menu")
        self.assertEqual(res.effective_touch_func_in_shooting, "Touch Tracking")

    def test_34_unattended_bench_touch_off_blocks_swipe_up_fn_menu_and_touch_tracking(
        self,
    ) -> None:
        res = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation="Off",
            configured_touch_sensitivity="Sensitive",
            configured_swipe_up="Open the Fn Menu",
            configured_touch_func_in_shooting="Touch Tracking",
            reset_action="Camera Settings Reset",
            screen_view="shooting",
            bench_unattended_rehearsal_active=True,
            simulated_capacitive_screen_brush=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.shooting_capacitive_touch_locked)
        self.assertFalse(res.fn_menu_opened_by_swipe_up)
        self.assertFalse(res.shooting_touch_tracking_or_focus_triggered)
        self.assertEqual(res.unattended_bench_accidental_touch_events, 0)

    def test_35_touch_on_playback_only_locks_shooting_taps_while_permitting_playback(
        self,
    ) -> None:
        shoot_res = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation="On: Playback Only",
            configured_swipe_up="Open the Fn Menu",
            configured_touch_func_in_shooting="Touch Focus",
            reset_action="Camera Settings Reset",
            screen_view="shooting",
            bench_unattended_rehearsal_active=True,
            simulated_capacitive_screen_brush=True,
        )
        self.assertTrue(shoot_res.admitted)
        self.assertTrue(shoot_res.shooting_capacitive_touch_locked)
        self.assertFalse(shoot_res.fn_menu_opened_by_swipe_up)
        self.assertFalse(shoot_res.shooting_touch_tracking_or_focus_triggered)
        self.assertEqual(shoot_res.unattended_bench_accidental_touch_events, 0)

        pb_res = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation="On: Playback Only",
            reset_action="Camera Settings Reset",
            screen_view="playback",
            bench_unattended_rehearsal_active=True,
            simulated_capacitive_screen_brush=True,
        )
        self.assertTrue(pb_res.admitted)
        self.assertTrue(pb_res.playback_touch_active)
        self.assertEqual(pb_res.unattended_bench_accidental_touch_events, 0)

    def test_36_unattended_bench_with_touch_operation_on_blocked_fail_closed_ebusy(
        self,
    ) -> None:
        res = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation="On",
            reset_action="Camera Settings Reset",
            screen_view="shooting",
            bench_unattended_rehearsal_active=True,
            simulated_capacitive_screen_brush=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p242.EBUSY_ERRNO)
        self.assertEqual(res.unattended_bench_accidental_touch_events, 0)

    def test_37_interactive_handheld_touch_on_dispatches_swipe_up_and_touch_focus_or_tracking(
        self,
    ) -> None:
        for tfunc in ("Touch Tracking", "Touch Focus"):
            res = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
                configured_touch_operation="On",
                configured_touch_sensitivity="Sensitive",
                configured_swipe_up="Open the Fn Menu",
                configured_touch_func_in_shooting=tfunc,
                screen_view="shooting",
                bench_unattended_rehearsal_active=False,
                simulated_capacitive_screen_brush=True,
            )
            self.assertTrue(res.admitted, msg=tfunc)
            self.assertFalse(res.shooting_capacitive_touch_locked, msg=tfunc)
            self.assertTrue(res.fn_menu_opened_by_swipe_up, msg=tfunc)
            self.assertTrue(res.shooting_touch_tracking_or_focus_triggered, msg=tfunc)

    def test_38_interactive_touch_func_off_and_swipe_up_off_suppress_shooting_gestures(
        self,
    ) -> None:
        res = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation="On",
            configured_swipe_up="Off",
            configured_touch_func_in_shooting="Off",
            screen_view="shooting",
            bench_unattended_rehearsal_active=False,
            simulated_capacitive_screen_brush=True,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.fn_menu_opened_by_swipe_up)
        self.assertFalse(res.shooting_touch_tracking_or_focus_triggered)

    def test_39_forcing_touch_dispatch_when_touch_operation_off_blocked_eopnotsupp(
        self,
    ) -> None:
        res = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation="Off",
            attempt_force_touch_when_touch_operation_off=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p242.EOPNOTSUPP_ERRNO)

    def test_40_touch_operation_4item_3step_reset_lifecycle(self) -> None:
        lc = p242.simulate_touch_operation_4item_reset_lifecycle()
        self.assertTrue(lc["lifecycle_verified"])
        self.assertEqual(
            lc["step2_camera_settings_reset_4item_survived"]["effective_touch_operation"],
            "Off",
        )
        self.assertEqual(
            lc["step3_initialize_restored_defaults"]["effective_touch_operation"],
            "On",
        )

    def test_41_submodel_45b_invalid_parameters_rejected_einval(self) -> None:
        for kw in (
            {"firmware_version": "9.99"},
            {"configured_touch_operation": "Multi-Touch"},
            {"configured_touch_sensitivity": "High"},
            {"configured_swipe_up": "Open Main Menu"},
            {"configured_touch_func_in_shooting": "Touch Shutter"},
            {"reset_action": "Factory Wipe"},
            {"screen_view": "evf_finder"},
        ):
            res = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(**kw)
            self.assertFalse(res.admitted, msg=str(kw))
            self.assertEqual(res.errno_code, p242.EINVAL_ERRNO, msg=str(kw))

    def test_42_evaluate_pillar_b_summary_passes_all_invariants(self) -> None:
        pb = p242.evaluate_pillar_b_touch_operation_4item_reset_and_bench_tap_guard_hil()
        self.assertTrue(pb["passed"])
        self.assertEqual(len(pb["all_4_touch_setup_items"]), 4)
        self.assertEqual(len(pb["touch_op_3mode_csr_survival_matrix"]), 3)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 45C — [Monitor Brightness] [Manual] (-2..+2) vs
    #          [Sunny Weather] Indoor Over-Brightness & NP-FZ100 Power Guard (11)
    # ------------------------------------------------------------------
    def test_43_monitor_brightness_manual_5steps_minus2_to_plus2_and_power_ladder(
        self,
    ) -> None:
        self.assertEqual(p242.VALID_MONITOR_BRIGHTNESS_MANUAL_LEVELS, (-2, -1, 0, 1, 2))
        prev_mw = 0
        for lvl in p242.VALID_MONITOR_BRIGHTNESS_MANUAL_LEVELS:
            res = p242.probe_monitor_brightness_sunny_weather_and_power_guard_hil(
                configured_brightness_mode="Manual",
                configured_manual_brightness_level=lvl,
                reset_action="Camera Settings Reset",
                indoor_bench_environment=True,
                npfz100_internal_battery_active=True,
            )
            self.assertTrue(res.admitted, msg=str(lvl))
            self.assertTrue(res.survived_camera_settings_reset, msg=str(lvl))
            self.assertTrue(res.reset_only_by_initialize, msg=str(lvl))
            self.assertEqual(res.effective_brightness_mode, "Manual", msg=str(lvl))
            self.assertEqual(res.effective_manual_brightness_level, lvl, msg=str(lvl))
            self.assertGreater(res.lcd_backlight_power_mw, prev_mw, msg=str(lvl))
            self.assertEqual(res.indoor_sunny_weather_unclamped_events, 0, msg=str(lvl))
            prev_mw = res.lcd_backlight_power_mw

    def test_44_outdoor_daylight_sunny_weather_admitted_and_survives_camera_settings_reset(
        self,
    ) -> None:
        res = p242.probe_monitor_brightness_sunny_weather_and_power_guard_hil(
            configured_brightness_mode="Sunny Weather",
            configured_manual_brightness_level=0,
            reset_action="Camera Settings Reset",
            indoor_bench_environment=False,
            npfz100_internal_battery_active=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.survived_camera_settings_reset)
        self.assertEqual(res.effective_brightness_mode, "Sunny Weather")
        self.assertEqual(res.lcd_backlight_power_mw, p242.SUNNY_WEATHER_BACKLIGHT_MW)
        self.assertGreater(res.lcd_backlight_power_mw, 540)

    def test_45_indoor_bench_sunny_weather_flagged_and_blocked_ebusy(self) -> None:
        res = p242.probe_monitor_brightness_sunny_weather_and_power_guard_hil(
            configured_brightness_mode="Sunny Weather",
            configured_manual_brightness_level=0,
            reset_action=p242.RESET_ACTION_NONE,
            indoor_bench_environment=True,
            npfz100_internal_battery_active=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p242.EBUSY_ERRNO)
        self.assertTrue(res.sunny_weather_indoor_hazard_flagged)
        self.assertTrue(res.indoor_sunny_weather_blocked)
        self.assertEqual(res.indoor_sunny_weather_unclamped_events, 0)

    def test_46_indoor_bench_sunny_weather_persisting_after_csr_still_blocked_ebusy(
        self,
    ) -> None:
        res = p242.probe_monitor_brightness_sunny_weather_and_power_guard_hil(
            configured_brightness_mode="Sunny Weather",
            reset_action="Camera Settings Reset",
            indoor_bench_environment=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p242.EBUSY_ERRNO)
        self.assertTrue(res.sunny_weather_indoor_hazard_flagged)
        self.assertEqual(res.indoor_sunny_weather_unclamped_events, 0)

    def test_47_initialize_clears_sunny_weather_back_to_manual_zero_on_indoor_bench(
        self,
    ) -> None:
        res = p242.probe_monitor_brightness_sunny_weather_and_power_guard_hil(
            configured_brightness_mode="Sunny Weather",
            configured_manual_brightness_level=2,
            reset_action="Initialize",
            indoor_bench_environment=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.cleared_to_manual_zero_by_initialize)
        self.assertEqual(res.effective_brightness_mode, "Manual")
        self.assertEqual(res.effective_manual_brightness_level, 0)
        self.assertEqual(res.lcd_backlight_power_mw, 450)

    def test_48_attempt_to_bypass_indoor_sunny_weather_guard_blocked_eopnotsupp(self) -> None:
        res = p242.probe_monitor_brightness_sunny_weather_and_power_guard_hil(
            configured_brightness_mode="Sunny Weather",
            indoor_bench_environment=True,
            attempt_bypass_indoor_sunny_weather_guard=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p242.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.sunny_weather_indoor_hazard_flagged)
        self.assertEqual(res.indoor_sunny_weather_unclamped_events, 0)

    def test_49_manual_brightness_out_of_range_or_bool_rejected_einval(self) -> None:
        for bad_lvl in (-3, 3, 10, True, False):
            res = p242.probe_monitor_brightness_sunny_weather_and_power_guard_hil(
                configured_brightness_mode="Manual",
                configured_manual_brightness_level=bad_lvl,  # type: ignore[arg-type]
            )
            self.assertFalse(res.admitted, msg=repr(bad_lvl))
            self.assertEqual(res.errno_code, p242.EINVAL_ERRNO, msg=repr(bad_lvl))

    def test_50_submodel_45c_invalid_mode_firmware_or_reset_rejected_einval(self) -> None:
        for kw in (
            {"firmware_version": "0.99"},
            {"configured_brightness_mode": "Auto Brightness"},
            {"reset_action": "Erase NVRAM"},
        ):
            res = p242.probe_monitor_brightness_sunny_weather_and_power_guard_hil(**kw)
            self.assertFalse(res.admitted, msg=str(kw))
            self.assertEqual(res.errno_code, p242.EINVAL_ERRNO, msg=str(kw))

    def test_51_monitor_brightness_3step_reset_lifecycle(self) -> None:
        lc = p242.simulate_monitor_brightness_reset_lifecycle()
        self.assertTrue(lc["lifecycle_verified"])
        self.assertEqual(
            lc["step2_camera_settings_reset_survived"]["effective_manual_brightness_level"],
            -1,
        )
        self.assertEqual(
            lc["step3_initialize_restored_manual_0"]["effective_brightness_mode"],
            "Manual",
        )
        self.assertEqual(
            lc["step3_initialize_restored_manual_0"]["effective_manual_brightness_level"],
            0,
        )

    def test_52_evaluate_pillar_c_d_summary_passes_all_invariants(self) -> None:
        pcd = p242.evaluate_pillar_c_d_monitor_brightness_sunny_weather_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["manual_5step_indoor_csr_matrix"]), 5)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 11)

    def test_53_coupled_wave35_reset_asymmetry_rec_resets_while_grid_touch_brightness_survive(
        self,
    ) -> None:
        rec_grid = p242.probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
            configured_emphasized_rec_display="Off",
            configured_grid_line_display="On",
            configured_grid_line_type="Square Grid",
            reset_action="Camera Settings Reset",
            configured_hdmi_info_display="Off",
        )
        touch = p242.probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation="Off",
            configured_touch_sensitivity="Sensitive",
            configured_swipe_up="Off",
            configured_touch_func_in_shooting="Touch Focus",
            reset_action="Camera Settings Reset",
            bench_unattended_rehearsal_active=True,
        )
        bright = p242.probe_monitor_brightness_sunny_weather_and_power_guard_hil(
            configured_brightness_mode="Manual",
            configured_manual_brightness_level=-2,
            reset_action="Camera Settings Reset",
            indoor_bench_environment=True,
        )
        self.assertEqual(rec_grid.effective_emphasized_rec_display, "On")
        self.assertEqual(rec_grid.effective_grid_line_display, "On")
        self.assertEqual(rec_grid.effective_grid_line_type, "Square Grid")
        self.assertEqual(touch.effective_touch_operation, "Off")
        self.assertEqual(bright.effective_manual_brightness_level, -2)

    # ------------------------------------------------------------------
    # Group 5: Hard Safety Redlines, Digest, CLI, Suite Stage 45 & Hygiene (11)
    # ------------------------------------------------------------------
    def test_54_hard_safety_redline_guard_baseline_and_all_11_violations_blocked(self) -> None:
        ok = p242.probe_hard_safety_redline()
        self.assertTrue(ok.valid)
        self.assertFalse(ok.persistent_emmc_writes_authorized)
        self.assertFalse(ok.hardware_live_attachment_authorized)
        self.assertFalse(ok.overall_ready_for_hardware_attach)
        self.assertFalse(ok.isp_write_authorized)
        self.assertFalse(ok.spi_nor_write_authorized)
        self.assertFalse(ok.el3_payload_transmit_authorized)
        self.assertTrue(ok.cnflasha_userspace_write_blocked)

        flags = (
            "persistent_emmc_writes_authorized",
            "hardware_live_attachment_authorized",
            "overall_ready_for_hardware_attach",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "isp_write_authorized",
            "cnflasha_userspace_write_attempt",
            "bypass_hdmi_only_or_raw_cleanfeed_clamp",
            "leak_local_only_assist_to_hdmi",
            "bypass_unattended_bench_touch_lock",
            "bypass_indoor_sunny_weather_guard",
        )
        for flg in flags:
            blk = p242.probe_hard_safety_redline(**{flg: True})
            self.assertFalse(blk.valid, msg=flg)
            self.assertIn(flg, blk.blocked_action)
            self.assertFalse(blk.persistent_emmc_writes_authorized)
            self.assertFalse(blk.hardware_live_attachment_authorized)
            self.assertFalse(blk.overall_ready_for_hardware_attach)
            self.assertFalse(blk.isp_write_authorized)
            self.assertEqual(blk.cnflasha_mutation_bytes, 0)
            self.assertEqual(blk.physical_device_writes, 0)
            self.assertEqual(blk.hdmi_only_or_raw_baked_recframe_or_grid_frames, 0)
            self.assertEqual(blk.unattended_bench_accidental_touch_events, 0)
            self.assertEqual(blk.indoor_sunny_weather_unclamped_events, 0)

    def test_55_multi_redline_violations_joined_deterministically(self) -> None:
        blk = p242.probe_hard_safety_redline(
            persistent_emmc_writes_authorized=True,
            bypass_hdmi_only_or_raw_cleanfeed_clamp=True,
            bypass_unattended_bench_touch_lock=True,
            bypass_indoor_sunny_weather_guard=True,
        )
        self.assertFalse(blk.valid)
        self.assertEqual(
            blk.blocked_action,
            "persistent_emmc_writes_authorized+bypass_hdmi_only_or_raw_cleanfeed_clamp+"
            "bypass_unattended_bench_touch_lock+bypass_indoor_sunny_weather_guard",
        )

    def test_56_deterministic_audit_digest_in_both_donor_and_clean_room_modes(self) -> None:
        c1 = _get_clean_room_audit()
        c2 = p242.run_phase242_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil(
            force_clean_room=True
        )
        self.assertEqual(c1["audit_digest_sha256"], c2["audit_digest_sha256"])
        self.assertEqual(c1["milestone"], "45/45")

        d1 = _get_default_audit()
        d2 = p242.run_phase242_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil()
        self.assertEqual(d1["audit_digest_sha256"], d2["audit_digest_sha256"])
        self.assertEqual(d1["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_57_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        script_path = str(
            FX3_VM_DIR / "realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator.py"
        )
        p_sum = subprocess.run(
            [sys.executable, "-B", script_path, "--self-test", "--summary"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 242 Stage 45 (45/45)", p_sum.stdout)

        p_json = subprocess.run(
            [sys.executable, "-B", script_path, "--self-test", "--clean-room", "--json"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        parsed = json.loads(p_json.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema"], p242.SCHEMA_ID)
        self.assertEqual(parsed["stage_index"], 45)
        self.assertEqual(parsed["stage_total"], 45)
        self.assertEqual(parsed["milestone"], "45/45")

    def test_58_inprocess_main_summary_and_json_exit_zero(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p242.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 242 Stage 45 (45/45)", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p242.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        data = json.loads(buf_json.getvalue())
        self.assertEqual(data["source_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_59_fx3_vm_coemulation_suite_includes_stage45_and_45_stage_milestone(self) -> None:
        rep_on, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertLess(dt_clean, 4.0)
        self.assertIn(
            "stage45_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil",
            rep_on,
        )
        s45 = rep_on["stage45_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil"]
        self.assertTrue(s45["all_checks_passed"])
        self.assertEqual(s45["schema"], p242.SCHEMA_ID)
        self.assertEqual(s45["milestone"], "45/45")
        self.assertFalse(s45["persistent_emmc_writes_authorized"])
        self.assertFalse(s45["hardware_live_attachment_authorized"])
        self.assertFalse(s45["overall_ready_for_hardware_attach"])
        self.assertFalse(s45["isp_write_authorized"])
        self.assertFalse(s45["spi_nor_write_authorized"])
        self.assertFalse(s45["el3_payload_transmit_authorized"])
        self.assertTrue(s45["cnflasha_userspace_write_blocked"])
        self.assertEqual(s45["cnflasha_mutation_bytes"], 0)
        self.assertEqual(s45["physical_device_writes"], 0)
        self.assertEqual(s45["hdmi_only_or_raw_baked_recframe_or_grid_frames"], 0)
        self.assertEqual(s45["hdmi_local_only_marker_zebra_peaking_leaked_pixels"], 0)
        self.assertEqual(s45["unattended_bench_accidental_touch_events"], 0)
        self.assertEqual(s45["indoor_sunny_weather_unclamped_events"], 0)
        self.assertEqual(s45["raw_firmware_bytes_leaked"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 45)

    def test_60_fx3_vm_coemulation_suite_skip_stage45_and_skip_phase242_config(self) -> None:
        rep_skip_p242 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase242_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil=False,
            )
        )
        self.assertTrue(rep_skip_p242["all_checks_passed"])
        self.assertNotIn(
            "stage45_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil",
            rep_skip_p242,
        )

        rep_skip_s45 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_stage45=False,
            )
        )
        self.assertTrue(rep_skip_s45["all_checks_passed"])
        self.assertNotIn(
            "stage45_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil",
            rep_skip_s45,
        )

    def test_61_fx3_vm_coemulation_suite_default_mode_and_include_stage45_cli(self) -> None:
        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertLess(dt_def, 8.0)
        s45 = rep_def["stage45_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil"]
        self.assertTrue(s45["all_checks_passed"])
        stage_keys = [k for k in rep_def if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 45)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--include-stage45", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_emphasized_rec_grid_hdmi_touch_sunny_hil=CLEAN_ROOM_SYNTHETIC("
            "grid=3t,baked=0,touch=4i,tap_ev=0,sunny_ev=0,emmc_wr=0)",
            out,
        )

    def test_62_fx3_vm_coemulation_suite_cli_skip_phase242_and_skip_stage45(self) -> None:
        for flag in ("--skip-phase242", "--skip-stage45", "--no-include-stage45"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(["--clean-room", flag, "--summary"])
            self.assertEqual(rc, 0, msg=flag)
            self.assertNotIn(
                "realhw_emphasized_rec_grid_hdmi_touch_sunny_hil=",
                buf.getvalue(),
                msg=flag,
            )

    def test_63_source_hygiene_no_write_flags_no_port_8768_and_readme_documented(self) -> None:
        src = (
            FX3_VM_DIR / "realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator.py"
        ).read_text(encoding="utf-8")
        forbidden_wronly = "O_" + "WRONLY"
        forbidden_rdwr = "O_" + "RDWR"
        forbidden_port = "87" + "68"
        self.assertNotIn(forbidden_wronly, src)
        self.assertNotIn(forbidden_rdwr, src)
        self.assertNotIn(forbidden_port, src)
        self.assertIn("os.O_RDONLY", src)

        readme = (FX3_VM_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator.py",
            readme,
        )
        self.assertIn("45/45", readme)
        self.assertIn("--include-stage45", readme)
        self.assertIn("--skip-phase242", readme)

    def test_64_zero_pyc_bytecode_artifacts_in_fx3_vm(self) -> None:
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
