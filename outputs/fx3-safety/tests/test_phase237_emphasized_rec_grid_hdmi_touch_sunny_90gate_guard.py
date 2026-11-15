"""Phase 237 (`90/90` Milestone) Dual-Mode Unit Tests (`>=58` tests; 66 tests
implemented) for
`fx3_safety.realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard`:

- Gate `G89`: `ILME-FX3` (`Ver. 7.02`) `[Emphasized REC Display]` (`On` default,
  resettable via `[Camera Settings Reset]`) & `[Grid Line Display]` /
  `[Grid Line Type]` (`Off` / `Rule of 3rds Grid` default, NOT reset by
  `[Camera Settings Reset]`) HDMI Info Routing vs Local-LCD-Only Assist Overlays
  (`Marker` / `Zebra` / `Peaking`) and Forced `[Off(HDMI Only)]` / `RAW`
  Clean-Feed Suppression.
- Gate `G90`: `ILME-FX3` (`Ver. 7.02`) `[Touch Operation]` 4-Item Setup
  `[Camera Settings Reset]` Survival + Unattended Tier-0 Bench Capacitive Tap
  Lock & `[Monitor Brightness]` (`Manual` `-2..+2` vs `Sunny Weather`) Reset
  Survival + Indoor `NP-FZ100` Bench Guard.
- Unified `90/90` Milestone Master Safety Preflight (`evaluate_90gate_preflight` /
  `verify-90-gates`): `87/90` offline awaiting physical Tier-0 receipt and
  `90/90` in `--simulate-bench-dry-run` with all hardware write/live-attach
  redlines hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard import (
    ACTIVE_MOVIE_OR_SQ_REC_STATES,
    ALLOWED_EMPHASIZED_REC_MODES,
    ALLOWED_GRID_LINE_DISPLAY_MODES,
    ALLOWED_GRID_LINE_TYPES,
    ALLOWED_HDMI_INFO_DISPLAY_MODES,
    ALLOWED_HDMI_RAW_OUTPUT_MODES,
    ALLOWED_MONITOR_BRIGHTNESS_MANUAL_LEVELS,
    ALLOWED_MONITOR_BRIGHTNESS_MODES,
    ALLOWED_REC_MEDIA_DUR_HDMI_MODES,
    ALLOWED_RESET_ACTIONS_PHASE237,
    ALLOWED_SHOOTING_STATES_G89,
    ALLOWED_SWIPE_UP_MODES,
    ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES,
    ALLOWED_TOUCH_OPERATION_MODES,
    ALLOWED_TOUCH_SENSITIVITY_MODES,
    DONOR_CHECK_MAX_SECONDS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMPHASIZED_REC_DISPLAY_MENU_PATH,
    EMPHASIZED_REC_FACTORY_DEFAULT,
    EMPHASIZED_REC_OFF,
    EMPHASIZED_REC_ON,
    FX3_DEFAULT_FW_VERSION_PHASE237,
    FX3_MIN_SUPPORTED_FW_TUPLE_PHASE237,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    G89,
    G89_GATE_CODE,
    G89_GATE_ID,
    G90,
    G90_GATE_CODE,
    G90_GATE_ID,
    GATE_G89_EMPHASIZED_REC_AND_GRID_LINE_HDMI_INFO_ROUTING_VS_FORCED_HDMIONLY_RAW_SUPPRESSION_GUARD,
    GATE_G90_TOUCH_OPERATION_4ITEM_RESET_SURVIVAL_BENCH_TAP_LOCK_AND_SUNNY_WEATHER_INDOOR_GUARD,
    GRID_LINE_DISPLAY_FACTORY_DEFAULT,
    GRID_LINE_DISPLAY_OFF,
    GRID_LINE_DISPLAY_ON,
    GRID_LINE_TYPE_DIAG_PLUS_SQUARE,
    GRID_LINE_TYPE_FACTORY_DEFAULT,
    GRID_LINE_TYPE_RULE_OF_3RDS,
    GRID_LINE_TYPE_SQUARE,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_INFO_FACTORY_DEFAULT,
    HDMI_INFO_OFF,
    HDMI_INFO_ON,
    HDMI_RAW_OUTPUT_OFF,
    HDMI_RAW_OUTPUT_ON,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LOCAL_LCD_ONLY_ASSIST_OVERLAYS_G89,
    MONITOR_BRIGHTNESS_FACTORY_DEFAULT_MODE,
    MONITOR_BRIGHTNESS_MANUAL,
    MONITOR_BRIGHTNESS_MANUAL_FACTORY_DEFAULT_LEVEL,
    MONITOR_BRIGHTNESS_MANUAL_MAX,
    MONITOR_BRIGHTNESS_MANUAL_MIN,
    MONITOR_BRIGHTNESS_SUNNY_WEATHER,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PINNED_PHASE237_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_EMPHASIZED_REC_GRID_HDMI_TOUCH_SUNNY_90GATE_SCHEMA,
    REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
    REC_MEDIA_DUR_HDMI_ON,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    SAFE_BENCH_UNATTENDED_TOUCH_OPERATION_MODES,
    SHOOTING_STATE_MOVIE_REC,
    SHOOTING_STATE_SQ_REC,
    SHOOTING_STATE_STANDBY,
    SHOOTING_STATE_STILL,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION,
    STATUS_BLOCKED_G89_FORCED_HDMIONLY_OR_RAW_CLEANFEED_CLAMP_LEAK,
    STATUS_BLOCKED_G89_HDMI_INFO_ROUTING_OR_LCD_BLANKING_MISMATCH,
    STATUS_BLOCKED_G89_LOCAL_LCD_ONLY_ASSIST_HDMI_LEAK,
    STATUS_BLOCKED_G89_TELEMETRY_INVALID,
    STATUS_BLOCKED_G90_BENCH_UNATTENDED_TOUCH_SHOOTING_LIVE_HAZARD,
    STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G90_SUNNY_WEATHER_INDOOR_BENCH_BRIGHTNESS_OR_POWER_HAZARD,
    STATUS_BLOCKED_G90_TELEMETRY_INVALID,
    STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE237_DONOR_INTEGRITY,
    STATUS_VERIFIED_G89,
    STATUS_VERIFIED_G90,
    SWIPE_UP_FACTORY_DEFAULT,
    SWIPE_UP_OFF,
    SWIPE_UP_OPEN_FN_MENU,
    TOUCH_FUNC_IN_SHOOTING_FACTORY_DEFAULT,
    TOUCH_FUNC_SHOOTING_FOCUS,
    TOUCH_FUNC_SHOOTING_OFF,
    TOUCH_FUNC_SHOOTING_TRACKING,
    TOUCH_OPERATION_4_SETUP_ITEMS,
    TOUCH_OPERATION_FACTORY_DEFAULT,
    TOUCH_OP_OFF,
    TOUCH_OP_ON,
    TOUCH_OP_PLAYBACK_ONLY,
    TOUCH_SENSITIVITY_FACTORY_DEFAULT,
    TOUCH_SENSITIVITY_SENSITIVE,
    TOUCH_SENSITIVITY_STANDARD,
    USB_PACKETS_TRANSMITTED,
    audit_phase237_donor_contracts,
    evaluate_90_master_safety_gates,
    evaluate_90gate_preflight,
    evaluate_g89_emphasized_rec_and_grid_hdmi_guard,
    evaluate_g90_touch_op_reset_and_sunny_weather_guard,
    main as module_main,
    resolve_fx3_emphasized_rec_and_grid_hdmi_routing,
    resolve_fx3_monitor_brightness_reset_and_sunny_guard,
    resolve_fx3_touch_op_4item_reset_and_bench_lock,
    run_90_gate_preflight,
    verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard,
    verify_touch_op_reset_and_sunny_weather_bench_guard,
)


class TestPhase237EmphasizedRecGridHdmiTouchSunny90GateGuard(unittest.TestCase):
    """66 dual-mode tests covering Gates G89, G90, and unified 90/90 Milestone preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.offline_88 = fx3_safety.evaluate_88gate_preflight()
        cls.dryrun_88 = fx3_safety.evaluate_88gate_preflight(dry_run_simulated=True)
        cls.offline_90 = evaluate_90gate_preflight(master_88_override=cls.offline_88)
        cls.dryrun_90 = evaluate_90gate_preflight(
            simulate_bench_dry_run=True, master_88_override=cls.dryrun_88
        )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_88 = fx3_safety.evaluate_88gate_preflight(
                force_clean_room=True
            )
            cls.clean_dryrun_88 = fx3_safety.evaluate_88gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_90 = evaluate_90gate_preflight(
                force_clean_room=True, master_88_override=cls.clean_offline_88
            )
            cls.clean_dryrun_90 = evaluate_90gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_88_override=cls.clean_dryrun_88,
            )

    # ------------------------------------------------------------------
    # Section A: Package Exports & Bounded Donor Contract Audit (8 tests)
    # ------------------------------------------------------------------

    def test_01_public_package_exports_and_hard_redline_constants(self) -> None:
        self.assertEqual(G89, G89_GATE_ID)
        self.assertEqual(G90, G90_GATE_ID)
        self.assertEqual(
            GATE_G89_EMPHASIZED_REC_AND_GRID_LINE_HDMI_INFO_ROUTING_VS_FORCED_HDMIONLY_RAW_SUPPRESSION_GUARD,
            G89_GATE_CODE,
        )
        self.assertEqual(
            GATE_G90_TOUCH_OPERATION_4ITEM_RESET_SURVIVAL_BENCH_TAP_LOCK_AND_SUNNY_WEATHER_INDOOR_GUARD,
            G90_GATE_CODE,
        )
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertIs(fx3_safety.evaluate_90gate_preflight, evaluate_90gate_preflight)
        self.assertIs(fx3_safety.run_90_gate_preflight, run_90_gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_90_master_safety_gates, evaluate_90_master_safety_gates
        )
        self.assertIn("evaluate_90gate_preflight", fx3_safety.__all__)
        self.assertIn(
            "realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard",
            fx3_safety.__all__,
        )
        self.assertIn("G89", fx3_safety.__all__)
        self.assertIn("G90", fx3_safety.__all__)

    def test_02_wave35_spec_constants_and_enums(self) -> None:
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE237, "7.02")
        self.assertEqual(FX3_MIN_SUPPORTED_FW_TUPLE_PHASE237, (1, 0))
        self.assertEqual(EMPHASIZED_REC_FACTORY_DEFAULT, "On")
        self.assertEqual(GRID_LINE_DISPLAY_FACTORY_DEFAULT, "Off")
        self.assertEqual(GRID_LINE_TYPE_FACTORY_DEFAULT, "Rule of 3rds Grid")
        self.assertEqual(
            ALLOWED_GRID_LINE_TYPES,
            ("Rule of 3rds Grid", "Square Grid", "Diag. + Square Grid"),
        )
        self.assertEqual(
            LOCAL_LCD_ONLY_ASSIST_OVERLAYS_G89,
            ("Marker Display", "Zebra Display", "Peaking Display"),
        )
        self.assertEqual(len(TOUCH_OPERATION_4_SETUP_ITEMS), 4)
        self.assertEqual(TOUCH_OPERATION_FACTORY_DEFAULT, "On")
        self.assertEqual(TOUCH_SENSITIVITY_FACTORY_DEFAULT, "Standard")
        self.assertEqual(SWIPE_UP_FACTORY_DEFAULT, "Open the Fn Menu")
        self.assertEqual(TOUCH_FUNC_IN_SHOOTING_FACTORY_DEFAULT, "Touch Tracking")
        self.assertEqual(MONITOR_BRIGHTNESS_FACTORY_DEFAULT_MODE, "Manual")
        self.assertEqual(ALLOWED_MONITOR_BRIGHTNESS_MANUAL_LEVELS, (-2, -1, 0, 1, 2))

    def test_03_donor_audit_ambient_mode_within_150ms_budget(self) -> None:
        audit = audit_phase237_donor_contracts()
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_150ms)
        self.assertLess(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 4)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() in (
            "1",
            "true",
            "TRUE",
            "yes",
            "YES",
        ):
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(
                audit.verification_mode,
                ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
            )

    def test_04_donor_audit_force_clean_room_argument(self) -> None:
        audit = audit_phase237_donor_contracts(force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_05_donor_audit_env_var_clean_room_override(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            audit = audit_phase237_donor_contracts()
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.files_inspected, 0)

    def test_06_donor_audit_missing_work_root_falls_back_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            audit = audit_phase237_donor_contracts(
                work_root=Path(td), force_clean_room=False
            )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_tampered_file_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for _k, (_body, rel, *_rest) in PINNED_PHASE237_DONOR_SPECS.items():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"corrupted_stub_without_markers")
            audit = audit_phase237_donor_contracts(
                work_root=root, force_clean_room=False
            )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE237_DONOR_INTEGRITY)
        self.assertEqual(audit.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertGreater(len(audit.errors), 0)

    def test_08_donor_audit_budget_overflow_blocks_fail_closed(self) -> None:
        audit = audit_phase237_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE237_DONOR_INTEGRITY)

    # ------------------------------------------------------------------
    # Section B: Gate G89 — Emphasized REC & Grid Line HDMI Routing vs
    #            Forced Off(HDMI Only) / RAW Clean-Feed Clamps (22 tests)
    # ------------------------------------------------------------------

    def test_09_g89_default_safe_rehearsal_passes(self) -> None:
        res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G89)
        self.assertEqual(res.effective_post_reset_emphasized_rec_display, "On")
        self.assertTrue(res.emphasized_rec_reset_by_camera_settings_reset)
        self.assertEqual(res.effective_post_reset_grid_line_display, "On")
        self.assertEqual(res.effective_post_reset_grid_line_type, "Diag. + Square Grid")
        self.assertTrue(res.grid_line_survived_camera_settings_reset)
        self.assertTrue(res.emphasized_rec_vs_grid_reset_split_verified)
        self.assertTrue(res.forced_off_by_hdmi_only_clamp)
        self.assertTrue(res.hdmi_clean_feed_clamp_active)
        self.assertEqual(res.effective_hdmi_info_display, "Off")
        self.assertEqual(res.hdmi_baked_overlay_pixels, 0)
        self.assertFalse(res.hdmi_emphasized_rec_rendered)
        self.assertFalse(res.hdmi_grid_line_rendered)
        self.assertEqual(res.emphasized_rec_menu_path, EMPHASIZED_REC_DISPLAY_MENU_PATH)

    def test_10_g89_emphasized_rec_factory_default_on_enforced(self) -> None:
        res_bad = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            claimed_emphasized_rec_factory_default="Off"
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION,
        )

    def test_11_g89_emphasized_rec_reset_by_camera_settings_reset_and_initialize(
        self,
    ) -> None:
        res_none = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            pre_reset_emphasized_rec_display=EMPHASIZED_REC_OFF,
            reset_action=RESET_ACTION_NONE,
        )
        self.assertTrue(res_none.valid)
        self.assertEqual(res_none.effective_post_reset_emphasized_rec_display, "Off")
        self.assertFalse(res_none.emphasized_rec_reset_by_camera_settings_reset)

        for rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
            res_rst = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
                pre_reset_emphasized_rec_display=EMPHASIZED_REC_OFF,
                reset_action=rst,
            )
            self.assertTrue(res_rst.valid, msg=rst)
            self.assertEqual(res_rst.effective_post_reset_emphasized_rec_display, "On")

        res_stuck = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            pre_reset_emphasized_rec_display=EMPHASIZED_REC_OFF,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_emphasized_rec_display="Off",
        )
        self.assertFalse(res_stuck.valid)
        self.assertEqual(
            res_stuck.status,
            STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION,
        )

    def test_12_g89_all_three_grid_line_types_survive_camera_settings_reset(
        self,
    ) -> None:
        for gtype in ALLOWED_GRID_LINE_TYPES:
            res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
                pre_reset_grid_line_display=GRID_LINE_DISPLAY_ON,
                pre_reset_grid_line_type=gtype,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            )
            self.assertTrue(res.valid, msg=gtype)
            self.assertEqual(res.effective_post_reset_grid_line_display, "On")
            self.assertEqual(res.effective_post_reset_grid_line_type, gtype)
            self.assertTrue(res.grid_line_survived_camera_settings_reset)

    def test_13_g89_grid_line_falsely_reset_by_camera_settings_reset_blocks(
        self,
    ) -> None:
        res_disp = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            pre_reset_grid_line_display=GRID_LINE_DISPLAY_ON,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_grid_line_display="Off",
        )
        self.assertFalse(res_disp.valid)
        self.assertEqual(
            res_disp.status,
            STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION,
        )

        res_type = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            pre_reset_grid_line_display=GRID_LINE_DISPLAY_ON,
            pre_reset_grid_line_type=GRID_LINE_TYPE_SQUARE,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_grid_line_type=GRID_LINE_TYPE_RULE_OF_3RDS,
        )
        self.assertFalse(res_type.valid)
        self.assertEqual(
            res_type.status,
            STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION,
        )

    def test_14_g89_grid_line_restored_to_factory_defaults_only_by_initialize(
        self,
    ) -> None:
        res_init = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            pre_reset_grid_line_display=GRID_LINE_DISPLAY_ON,
            pre_reset_grid_line_type=GRID_LINE_TYPE_DIAG_PLUS_SQUARE,
            reset_action=RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(res_init.valid)
        self.assertEqual(res_init.effective_post_reset_grid_line_display, "Off")
        self.assertEqual(
            res_init.effective_post_reset_grid_line_type, "Rule of 3rds Grid"
        )
        self.assertFalse(res_init.grid_line_survived_camera_settings_reset)

        res_not_cleared = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            pre_reset_grid_line_display=GRID_LINE_DISPLAY_ON,
            pre_reset_grid_line_type=GRID_LINE_TYPE_SQUARE,
            reset_action=RESET_ACTION_INITIALIZE,
            observed_post_reset_grid_line_display="On",
        )
        self.assertFalse(res_not_cleared.valid)
        self.assertEqual(
            res_not_cleared.status,
            STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION,
        )

    def test_15_g89_hdmi_info_on_routes_emphasized_rec_and_grid_to_hdmi_and_blanks_lcd(
        self,
    ) -> None:
        res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            pre_reset_emphasized_rec_display=EMPHASIZED_REC_ON,
            pre_reset_grid_line_display=GRID_LINE_DISPLAY_ON,
            pre_reset_grid_line_type=GRID_LINE_TYPE_SQUARE,
            reset_action=RESET_ACTION_NONE,
            shooting_state=SHOOTING_STATE_MOVIE_REC,
            configured_hdmi_info_display=HDMI_INFO_ON,
            rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
            hdmi_raw_output=HDMI_RAW_OUTPUT_OFF,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.hdmi_clean_feed_clamp_active)
        self.assertEqual(res.effective_hdmi_info_display, "On")
        self.assertTrue(res.camera_lcd_blanked_by_hdmi_info)
        self.assertFalse(res.local_lcd_emphasized_rec_rendered)
        self.assertFalse(res.local_lcd_grid_line_rendered)
        self.assertTrue(res.hdmi_emphasized_rec_rendered)
        self.assertTrue(res.hdmi_grid_line_rendered)
        self.assertTrue(res.hdmi_status_osd_rendered)
        self.assertFalse(res.hdmi_local_only_marker_rendered)
        self.assertFalse(res.hdmi_local_only_zebra_rendered)
        self.assertFalse(res.hdmi_local_only_peaking_rendered)

    def test_16_g89_sq_recording_routes_red_rec_frame_and_grid_to_hdmi(self) -> None:
        res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            pre_reset_emphasized_rec_display=EMPHASIZED_REC_ON,
            pre_reset_grid_line_display=GRID_LINE_DISPLAY_ON,
            pre_reset_grid_line_type=GRID_LINE_TYPE_RULE_OF_3RDS,
            reset_action=RESET_ACTION_NONE,
            shooting_state=SHOOTING_STATE_SQ_REC,
            configured_hdmi_info_display=HDMI_INFO_ON,
            rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
            hdmi_raw_output=HDMI_RAW_OUTPUT_OFF,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.movie_or_sq_recording_active)
        self.assertTrue(res.hdmi_emphasized_rec_rendered)
        self.assertTrue(res.hdmi_grid_line_rendered)

    def test_17_g89_standby_and_still_suppress_red_rec_frame_while_keeping_grid(
        self,
    ) -> None:
        for state in (SHOOTING_STATE_STANDBY, SHOOTING_STATE_STILL):
            res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
                pre_reset_emphasized_rec_display=EMPHASIZED_REC_ON,
                pre_reset_grid_line_display=GRID_LINE_DISPLAY_ON,
                reset_action=RESET_ACTION_NONE,
                shooting_state=state,
                configured_hdmi_info_display=HDMI_INFO_ON,
                rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
                hdmi_raw_output=HDMI_RAW_OUTPUT_OFF,
            )
            self.assertTrue(res.valid, msg=state)
            self.assertFalse(res.movie_or_sq_recording_active)
            self.assertFalse(res.hdmi_emphasized_rec_rendered)
            self.assertTrue(res.hdmi_grid_line_rendered)

    def test_18_g89_hdmi_info_off_renders_on_local_lcd_and_keeps_hdmi_clean(
        self,
    ) -> None:
        res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            pre_reset_emphasized_rec_display=EMPHASIZED_REC_ON,
            pre_reset_grid_line_display=GRID_LINE_DISPLAY_ON,
            reset_action=RESET_ACTION_NONE,
            shooting_state=SHOOTING_STATE_MOVIE_REC,
            configured_hdmi_info_display=HDMI_INFO_OFF,
            rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
            hdmi_raw_output=HDMI_RAW_OUTPUT_OFF,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_hdmi_info_display, "Off")
        self.assertFalse(res.camera_lcd_blanked_by_hdmi_info)
        self.assertTrue(res.local_lcd_emphasized_rec_rendered)
        self.assertTrue(res.local_lcd_grid_line_rendered)
        self.assertFalse(res.hdmi_emphasized_rec_rendered)
        self.assertFalse(res.hdmi_grid_line_rendered)
        self.assertEqual(res.hdmi_baked_overlay_pixels, 0)

    def test_19_g89_clamp1_off_hdmi_only_forces_hdmi_info_off_and_blocks_any_leak(
        self,
    ) -> None:
        for leak_kw in (
            {"observed_effective_hdmi_info_display": "On"},
            {"observed_hdmi_emphasized_rec_rendered": True},
            {"observed_hdmi_grid_line_rendered": True},
            {"observed_hdmi_status_osd_rendered": True},
            {"observed_hdmi_baked_overlay_pixels": 64},
        ):
            res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
                configured_hdmi_info_display=HDMI_INFO_ON,
                rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
                hdmi_raw_output=HDMI_RAW_OUTPUT_OFF,
                **leak_kw,
            )
            self.assertFalse(res.valid, msg=str(leak_kw))
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G89_FORCED_HDMIONLY_OR_RAW_CLEANFEED_CLAMP_LEAK,
            )

    def test_20_g89_clamp2_hdmi_raw_output_forces_hdmi_info_off_and_blocks_any_leak(
        self,
    ) -> None:
        res_clean = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            configured_hdmi_info_display=HDMI_INFO_ON,
            rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
            hdmi_raw_output=HDMI_RAW_OUTPUT_ON,
        )
        self.assertTrue(res_clean.valid)
        self.assertTrue(res_clean.forced_off_by_hdmi_raw_clamp)
        self.assertFalse(res_clean.forced_off_by_hdmi_only_clamp)
        self.assertEqual(res_clean.effective_hdmi_info_display, "Off")
        self.assertEqual(res_clean.hdmi_baked_overlay_pixels, 0)

        res_leak = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            configured_hdmi_info_display=HDMI_INFO_ON,
            rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
            hdmi_raw_output=HDMI_RAW_OUTPUT_ON,
            observed_hdmi_emphasized_rec_rendered=True,
        )
        self.assertFalse(res_leak.valid)
        self.assertEqual(
            res_leak.status,
            STATUS_BLOCKED_G89_FORCED_HDMIONLY_OR_RAW_CLEANFEED_CLAMP_LEAK,
        )

    def test_21_g89_both_cleanfeed_clamps_simultaneously_active(self) -> None:
        res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            configured_hdmi_info_display=HDMI_INFO_ON,
            rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
            hdmi_raw_output=HDMI_RAW_OUTPUT_ON,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.forced_off_by_hdmi_only_clamp)
        self.assertTrue(res.forced_off_by_hdmi_raw_clamp)
        self.assertTrue(res.hdmi_clean_feed_clamp_active)
        self.assertEqual(res.effective_hdmi_info_display, "Off")

    def test_22_g89_local_lcd_only_marker_zebra_peaking_leak_to_hdmi_blocks(
        self,
    ) -> None:
        for leak_kw in (
            {"observed_hdmi_local_only_marker_rendered": True},
            {"observed_hdmi_local_only_zebra_rendered": True},
            {"observed_hdmi_local_only_peaking_rendered": True},
        ):
            res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
                configured_hdmi_info_display=HDMI_INFO_ON,
                rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
                hdmi_raw_output=HDMI_RAW_OUTPUT_OFF,
                **leak_kw,
            )
            self.assertFalse(res.valid, msg=str(leak_kw))
            self.assertEqual(
                res.status, STATUS_BLOCKED_G89_LOCAL_LCD_ONLY_ASSIST_HDMI_LEAK
            )

    def test_23_g89_lcd_blanking_or_routing_mismatch_when_hdmi_info_on_blocks(
        self,
    ) -> None:
        for bad_kw in (
            {"observed_camera_lcd_blanked_by_hdmi_info": False},
            {"observed_local_lcd_emphasized_rec_rendered": True},
            {"observed_hdmi_emphasized_rec_rendered": False},
            {"observed_hdmi_grid_line_rendered": False},
        ):
            res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
                pre_reset_emphasized_rec_display=EMPHASIZED_REC_ON,
                pre_reset_grid_line_display=GRID_LINE_DISPLAY_ON,
                reset_action=RESET_ACTION_NONE,
                shooting_state=SHOOTING_STATE_MOVIE_REC,
                configured_hdmi_info_display=HDMI_INFO_ON,
                rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
                hdmi_raw_output=HDMI_RAW_OUTPUT_OFF,
                **bad_kw,
            )
            self.assertFalse(res.valid, msg=str(bad_kw))
            self.assertEqual(
                res.status, STATUS_BLOCKED_G89_HDMI_INFO_ROUTING_OR_LCD_BLANKING_MISMATCH
            )

    def test_24_g89_nonzero_baked_pixels_when_hdmi_info_configured_off_blocks(
        self,
    ) -> None:
        res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
            configured_hdmi_info_display=HDMI_INFO_OFF,
            rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
            hdmi_raw_output=HDMI_RAW_OUTPUT_OFF,
            observed_hdmi_baked_overlay_pixels=4,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G89_HDMI_INFO_ROUTING_OR_LCD_BLANKING_MISMATCH
        )

    def test_25_g89_invalid_emphasized_rec_or_grid_enums_block(self) -> None:
        for kw in (
            {"pre_reset_emphasized_rec_display": "Blinking"},
            {"pre_reset_grid_line_display": "Auto"},
            {"pre_reset_grid_line_type": "Golden Spiral"},
        ):
            res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION,
            )

    def test_26_g89_invalid_telemetry_fields_block(self) -> None:
        for kw in (
            {"body_model_name": "ILME-FX6"},
            {"body_model_id": 0x99999999},
            {"firmware_version": "bad_fw"},
            {"reset_action": "Factory Wipe"},
            {"shooting_state": "Burst"},
            {"configured_hdmi_info_display": "Auto"},
            {"rec_media_dur_hdmi_output": "InvalidMode"},
            {"hdmi_raw_output": "12bit"},
            {"observed_hdmi_baked_overlay_pixels": -1},
            {"observed_hdmi_baked_overlay_pixels": True},
            {"observed_effective_hdmi_info_display": "Maybe"},
        ):
            res = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertIn(STATUS_BLOCKED_G89_TELEMETRY_INVALID, res.violation_codes)

    def test_27_g89_resolver_normalizes_bracketed_and_case_variants(self) -> None:
        st = resolve_fx3_emphasized_rec_and_grid_hdmi_routing(
            pre_reset_emphasized_rec_display="[Off]",
            pre_reset_grid_line_display="[On]",
            pre_reset_grid_line_type="[Diag. + Square Grid]",
            reset_action="[Camera Settings Reset]",
            shooting_state="S&Q",
            configured_hdmi_info_display="[On]",
            rec_media_dur_hdmi_output="[Off(HDMI Only)]",
            hdmi_raw_output="[Off]",
        )
        self.assertEqual(st["expected_post_emphasized_rec"], "On")
        self.assertEqual(st["expected_post_grid_display"], "On")
        self.assertEqual(st["expected_post_grid_type"], "Diag. + Square Grid")
        self.assertEqual(st["canonical_shooting_state"], "S&Q Recording")
        self.assertEqual(st["expected_effective_hdmi_info_display"], "Off")

    def test_28_g89_evaluator_dual_mode_and_json_serializable(self) -> None:
        v_n, r_n = evaluate_g89_emphasized_rec_and_grid_hdmi_guard()
        self.assertTrue(v_n.passed)
        self.assertTrue(r_n.valid)
        self.assertEqual(r_n.raw_firmware_bytes_leaked, 0)
        self.assertIn("emphasized_rec_grid_hdmi_guard", json.loads(json.dumps(r_n.to_dict())))

        v_c, r_c = evaluate_g89_emphasized_rec_and_grid_hdmi_guard(
            force_clean_room=True
        )
        self.assertTrue(v_c.passed)
        self.assertEqual(r_c.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_29_g89_evaluator_persistent_emmc_write_request_blocked(self) -> None:
        v, r = evaluate_g89_emphasized_rec_and_grid_hdmi_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r.violation_codes)
        self.assertFalse(r.persistent_emmc_writes_authorized)

    def test_30_g89_evaluator_propagates_donor_failure_fail_closed(self) -> None:
        bad_audit = audit_phase237_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        v, r = evaluate_g89_emphasized_rec_and_grid_hdmi_guard(donor_audit=bad_audit)
        self.assertFalse(v.passed)
        self.assertEqual(r.status, STATUS_BLOCKED_PHASE237_DONOR_INTEGRITY)

    # ------------------------------------------------------------------
    # Section C: Gate G90 — Touch Operation 4-Item Reset Survival, Bench
    #            Tap Lock & Monitor Brightness Sunny Weather Guard (20 tests)
    # ------------------------------------------------------------------

    def test_31_g90_default_safe_rehearsal_passes(self) -> None:
        res = verify_touch_op_reset_and_sunny_weather_bench_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G90)
        self.assertEqual(res.effective_post_reset_touch_operation, "Off")
        self.assertEqual(res.effective_post_reset_touch_sensitivity, "Sensitive")
        self.assertEqual(res.effective_post_reset_swipe_up, "Open the Fn Menu")
        self.assertEqual(res.effective_post_reset_touch_func_in_shooting, "Touch Focus")
        self.assertTrue(res.all_4_touch_items_survived_camera_settings_reset)
        self.assertTrue(res.shooting_capacitive_touch_locked)
        self.assertTrue(res.bench_touch_tap_lock_enforced)
        self.assertEqual(res.effective_post_reset_monitor_brightness_mode, "Manual")
        self.assertEqual(res.effective_post_reset_manual_brightness_level, 0)
        self.assertTrue(res.monitor_brightness_survived_camera_settings_reset)
        self.assertTrue(res.sunny_weather_indoor_blocked)

    def test_32_g90_all_4_touch_items_survive_camera_settings_reset_matrix(
        self,
    ) -> None:
        for top in SAFE_BENCH_UNATTENDED_TOUCH_OPERATION_MODES:
            for sens in ALLOWED_TOUCH_SENSITIVITY_MODES:
                for sw in ALLOWED_SWIPE_UP_MODES:
                    for fn in ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES:
                        res = verify_touch_op_reset_and_sunny_weather_bench_guard(
                            pre_reset_touch_operation=top,
                            pre_reset_touch_sensitivity=sens,
                            pre_reset_swipe_up=sw,
                            pre_reset_touch_func_in_shooting=fn,
                            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                            bench_unattended_tier0_active=True,
                        )
                        self.assertTrue(res.valid, msg=f"{top}/{sens}/{sw}/{fn}")
                        self.assertEqual(res.effective_post_reset_touch_operation, top)
                        self.assertEqual(
                            res.effective_post_reset_touch_sensitivity, sens
                        )
                        self.assertEqual(res.effective_post_reset_swipe_up, sw)
                        self.assertEqual(
                            res.effective_post_reset_touch_func_in_shooting, fn
                        )

    def test_33_g90_initialize_restores_all_4_touch_items_to_factory_defaults(
        self,
    ) -> None:
        res_att = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_touch_operation=TOUCH_OP_OFF,
            pre_reset_touch_sensitivity=TOUCH_SENSITIVITY_SENSITIVE,
            pre_reset_swipe_up=SWIPE_UP_OFF,
            pre_reset_touch_func_in_shooting=TOUCH_FUNC_SHOOTING_OFF,
            reset_action=RESET_ACTION_INITIALIZE,
            bench_unattended_tier0_active=False,
        )
        self.assertTrue(res_att.valid)
        self.assertEqual(res_att.effective_post_reset_touch_operation, "On")
        self.assertEqual(res_att.effective_post_reset_touch_sensitivity, "Standard")
        self.assertEqual(res_att.effective_post_reset_swipe_up, "Open the Fn Menu")
        self.assertEqual(
            res_att.effective_post_reset_touch_func_in_shooting, "Touch Tracking"
        )
        self.assertFalse(res_att.all_4_touch_items_survived_camera_settings_reset)

    def test_34_g90_initialize_without_relocking_touch_on_unattended_bench_blocks(
        self,
    ) -> None:
        res = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_touch_operation=TOUCH_OP_OFF,
            reset_action=RESET_ACTION_INITIALIZE,
            bench_unattended_tier0_active=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G90_BENCH_UNATTENDED_TOUCH_SHOOTING_LIVE_HAZARD
        )

    def test_35_g90_any_touch_item_falsely_reset_by_camera_settings_reset_blocks(
        self,
    ) -> None:
        for bad_kw in (
            {"observed_post_reset_touch_operation": "On"},
            {"observed_post_reset_touch_sensitivity": "Standard"},
            {"pre_reset_swipe_up": "Off", "observed_post_reset_swipe_up": "Open the Fn Menu"},
            {"observed_post_reset_touch_func_in_shooting": "Touch Tracking"},
        ):
            res = verify_touch_op_reset_and_sunny_weather_bench_guard(
                pre_reset_touch_operation=TOUCH_OP_OFF,
                pre_reset_touch_sensitivity=TOUCH_SENSITIVITY_SENSITIVE,
                pre_reset_touch_func_in_shooting=TOUCH_FUNC_SHOOTING_FOCUS,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                **bad_kw,
            )
            self.assertFalse(res.valid, msg=str(bad_kw))
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION,
            )

    def test_36_g90_any_touch_item_not_restored_by_initialize_blocks(self) -> None:
        for bad_kw in (
            {"observed_post_reset_touch_operation": "Off"},
            {"observed_post_reset_touch_sensitivity": "Sensitive"},
            {"observed_post_reset_swipe_up": "Off"},
            {"observed_post_reset_touch_func_in_shooting": "Touch Focus"},
        ):
            res = verify_touch_op_reset_and_sunny_weather_bench_guard(
                pre_reset_touch_operation=TOUCH_OP_OFF,
                pre_reset_touch_sensitivity=TOUCH_SENSITIVITY_SENSITIVE,
                pre_reset_swipe_up=SWIPE_UP_OFF,
                pre_reset_touch_func_in_shooting=TOUCH_FUNC_SHOOTING_FOCUS,
                reset_action=RESET_ACTION_INITIALIZE,
                bench_unattended_tier0_active=False,
                **bad_kw,
            )
            self.assertFalse(res.valid, msg=str(bad_kw))
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION,
            )

    def test_37_g90_invalid_touch_4item_values_block(self) -> None:
        for kw in (
            {"pre_reset_touch_operation": "Gesture Only"},
            {"pre_reset_touch_sensitivity": "Ultra"},
            {"pre_reset_swipe_up": "Open Main Menu"},
            {"pre_reset_touch_func_in_shooting": "Touch Shutter"},
        ):
            res = verify_touch_op_reset_and_sunny_weather_bench_guard(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION,
            )

    def test_38_g90_playback_only_touch_permitted_on_unattended_tier0_bench(
        self,
    ) -> None:
        res = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_touch_operation=TOUCH_OP_PLAYBACK_ONLY,
            bench_unattended_tier0_active=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.shooting_capacitive_touch_locked)
        self.assertEqual(res.effective_post_reset_touch_operation, "On: Playback Only")

    def test_39_g90_touch_on_during_unattended_tier0_bench_blocks(self) -> None:
        res = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_touch_operation=TOUCH_OP_ON,
            bench_unattended_tier0_active=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G90_BENCH_UNATTENDED_TOUCH_SHOOTING_LIVE_HAZARD
        )

    def test_40_g90_attended_shooting_allows_touch_on_with_tracking_focus_off(
        self,
    ) -> None:
        for fn in ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES:
            res = verify_touch_op_reset_and_sunny_weather_bench_guard(
                pre_reset_touch_operation=TOUCH_OP_ON,
                pre_reset_touch_func_in_shooting=fn,
                bench_unattended_tier0_active=False,
            )
            self.assertTrue(res.valid, msg=fn)
            self.assertFalse(res.shooting_capacitive_touch_locked)

    def test_41_g90_accidental_fn_swipe_or_touch_tracking_trigger_blocks(self) -> None:
        for kw in (
            {"observed_accidental_fn_swipe_triggered": True},
            {"observed_accidental_touch_tracking_triggered": True},
        ):
            res = verify_touch_op_reset_and_sunny_weather_bench_guard(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G90_BENCH_UNATTENDED_TOUCH_SHOOTING_LIVE_HAZARD,
            )

    def test_42_g90_monitor_brightness_manual_minus2_to_plus2_survives_reset(
        self,
    ) -> None:
        for lvl in (-2, -1, 0, 1, 2, "+2", "-2"):
            res = verify_touch_op_reset_and_sunny_weather_bench_guard(
                pre_reset_monitor_brightness_mode=MONITOR_BRIGHTNESS_MANUAL,
                pre_reset_manual_brightness_level=lvl,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                indoor_bench_environment=True,
            )
            self.assertTrue(res.valid, msg=str(lvl))
            self.assertEqual(res.effective_post_reset_monitor_brightness_mode, "Manual")
            self.assertEqual(res.effective_post_reset_manual_brightness_level, int(lvl))
            self.assertTrue(res.monitor_brightness_survived_camera_settings_reset)

    def test_43_g90_monitor_brightness_manual_out_of_range_blocks(self) -> None:
        for bad_lvl in (-3, 3, True, "max", "2.5"):
            res = verify_touch_op_reset_and_sunny_weather_bench_guard(
                pre_reset_manual_brightness_level=bad_lvl
            )
            self.assertFalse(res.valid, msg=str(bad_lvl))
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION,
            )

    def test_44_g90_monitor_brightness_falsely_reset_by_camera_settings_reset_blocks(
        self,
    ) -> None:
        res_lvl = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_monitor_brightness_mode=MONITOR_BRIGHTNESS_MANUAL,
            pre_reset_manual_brightness_level=-2,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_manual_brightness_level=0,
        )
        self.assertFalse(res_lvl.valid)
        self.assertEqual(
            res_lvl.status,
            STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION,
        )

        res_mode = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_monitor_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            indoor_bench_environment=False,
            observed_post_reset_monitor_brightness_mode="Manual",
        )
        self.assertFalse(res_mode.valid)
        self.assertEqual(
            res_mode.status,
            STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION,
        )

    def test_45_g90_monitor_brightness_restored_to_manual_0_by_initialize(
        self,
    ) -> None:
        res_init = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_monitor_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER,
            pre_reset_manual_brightness_level=2,
            reset_action=RESET_ACTION_INITIALIZE,
            bench_unattended_tier0_active=False,
            indoor_bench_environment=True,
        )
        self.assertTrue(res_init.valid)
        self.assertEqual(res_init.effective_post_reset_monitor_brightness_mode, "Manual")
        self.assertEqual(res_init.effective_post_reset_manual_brightness_level, 0)
        self.assertFalse(res_init.monitor_brightness_survived_camera_settings_reset)

        res_not_cleared = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_monitor_brightness_mode=MONITOR_BRIGHTNESS_MANUAL,
            pre_reset_manual_brightness_level=2,
            reset_action=RESET_ACTION_INITIALIZE,
            bench_unattended_tier0_active=False,
            observed_post_reset_manual_brightness_level=2,
        )
        self.assertFalse(res_not_cleared.valid)
        self.assertEqual(
            res_not_cleared.status,
            STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION,
        )

    def test_46_g90_sunny_weather_blocked_on_indoor_npfz100_bench(self) -> None:
        res = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_monitor_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            indoor_bench_environment=True,
            npfz100_internal_battery_active=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.sunny_weather_indoor_blocked)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G90_SUNNY_WEATHER_INDOOR_BENCH_BRIGHTNESS_OR_POWER_HAZARD,
        )

    def test_47_g90_sunny_weather_permitted_outdoors_and_survives_reset(self) -> None:
        res = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_monitor_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            indoor_bench_environment=False,
        )
        self.assertTrue(res.valid)
        self.assertEqual(
            res.effective_post_reset_monitor_brightness_mode, "Sunny Weather"
        )
        self.assertTrue(res.monitor_brightness_survived_camera_settings_reset)

    def test_48_g90_invalid_monitor_brightness_mode_or_telemetry_blocks(self) -> None:
        res_mode = verify_touch_op_reset_and_sunny_weather_bench_guard(
            pre_reset_monitor_brightness_mode="Auto Ambient"
        )
        self.assertFalse(res_mode.valid)
        self.assertEqual(
            res_mode.status,
            STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION,
        )

        for kw in (
            {"body_model_name": "ILME-FX30"},
            {"body_model_id": 0x11111111},
            {"firmware_version": "0.99"},
            {"reset_action": "Soft Reset"},
        ):
            res_t = verify_touch_op_reset_and_sunny_weather_bench_guard(**kw)
            self.assertFalse(res_t.valid, msg=str(kw))
            self.assertIn(STATUS_BLOCKED_G90_TELEMETRY_INVALID, res_t.violation_codes)

    def test_49_g90_resolvers_normalize_bracketed_inputs(self) -> None:
        t = resolve_fx3_touch_op_4item_reset_and_bench_lock(
            pre_reset_touch_operation="[On: Playback Only]",
            pre_reset_touch_sensitivity="[Sensitive]",
            pre_reset_swipe_up="[Open the Fn Menu]",
            pre_reset_touch_func_in_shooting="[Touch Tracking]",
            reset_action="[Camera Settings Reset]",
        )
        self.assertEqual(t["expected_post_touch_operation"], "On: Playback Only")
        self.assertTrue(t["shooting_capacitive_touch_locked"])

        b = resolve_fx3_monitor_brightness_reset_and_sunny_guard(
            pre_reset_monitor_brightness_mode="[Sunny Weather]",
            reset_action="Camera Settings Reset",
            indoor_bench_environment=True,
        )
        self.assertTrue(b["sunny_weather_indoor_violation"])
        self.assertFalse(b["sunny_weather_indoor_blocked"])

    def test_50_g90_evaluator_dual_mode_and_write_request_block(self) -> None:
        v_n, r_n = evaluate_g90_touch_op_reset_and_sunny_weather_guard()
        self.assertTrue(v_n.passed)
        self.assertTrue(r_n.valid)
        self.assertEqual(r_n.raw_firmware_bytes_leaked, 0)

        v_c, r_c = evaluate_g90_touch_op_reset_and_sunny_weather_guard(
            force_clean_room=True
        )
        self.assertTrue(v_c.passed)
        self.assertEqual(r_c.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_w, r_w = evaluate_g90_touch_op_reset_and_sunny_weather_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_w.passed)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r_w.violation_codes)

        bad_audit = audit_phase237_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        v_d, r_d = evaluate_g90_touch_op_reset_and_sunny_weather_guard(
            donor_audit=bad_audit
        )
        self.assertFalse(v_d.passed)
        self.assertEqual(r_d.status, STATUS_BLOCKED_PHASE237_DONOR_INTEGRITY)

    # ------------------------------------------------------------------
    # Section D: Unified 90/90 Milestone Master Preflight & CLI (16 tests)
    # ------------------------------------------------------------------

    def test_51_master_90gate_offline_default_verifies_87_of_90(self) -> None:
        rep = self.offline_90
        self.assertEqual(
            rep.schema, REALHW_EMPHASIZED_REC_GRID_HDMI_TOUCH_SUNNY_90GATE_SCHEMA
        )
        self.assertEqual(rep.summary["total_gates"], 90)
        self.assertEqual(rep.summary["verified_gates"], 87)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_87_gates_verified)
        self.assertFalse(rep.all_90_gates_verified)
        self.assertTrue(rep.g13_to_g90_all_passed)
        self.assertTrue(rep.g89_to_g90_all_passed)
        self.assertEqual(rep.status, "VERIFIED_87_OF_90_AWAITING_PHYSICAL_TIER0")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_52_master_90gate_simulate_bench_dry_run_verifies_90_of_90(self) -> None:
        rep = self.dryrun_90
        self.assertEqual(rep.summary["verified_gates"], 90)
        self.assertTrue(rep.offline_87_gates_verified)
        self.assertTrue(rep.all_90_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_90_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)

    def test_53_master_90gate_dry_run_flag_aliases_parity(self) -> None:
        rep_a = evaluate_90gate_preflight(
            force_clean_room=True,
            dry_run_simulated=True,
            master_88_override=self.clean_dryrun_88,
        )
        rep_b = evaluate_90gate_preflight(
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_88_override=self.clean_dryrun_88,
        )
        self.assertTrue(rep_a.all_90_gates_verified)
        self.assertTrue(rep_b.all_90_gates_verified)
        self.assertEqual(rep_a.status, rep_b.status)

    def test_54_master_90gate_clean_room_offline_and_dry_run_parity(self) -> None:
        self.assertEqual(
            self.clean_offline_90.verification_mode, "CLEAN_ROOM_SYNTHETIC"
        )
        self.assertEqual(self.clean_offline_90.summary["verified_gates"], 87)
        self.assertTrue(self.clean_offline_90.offline_87_gates_verified)
        self.assertFalse(self.clean_offline_90.all_90_gates_verified)

        self.assertEqual(
            self.clean_dryrun_90.verification_mode, "CLEAN_ROOM_SYNTHETIC"
        )
        self.assertEqual(self.clean_dryrun_90.summary["verified_gates"], 90)
        self.assertTrue(self.clean_dryrun_90.all_90_gates_verified)
        self.assertFalse(self.clean_dryrun_90.overall_ready_for_hardware_attach)

    def test_55_master_90gate_delegates_g01_to_g88_and_appends_g89_g90(self) -> None:
        self.assertEqual(len(self.offline_90.gates), 90)
        self.assertEqual(self.offline_90.gates[-2]["gate_id"], G89_GATE_ID)
        self.assertEqual(self.offline_90.gates[-1]["gate_id"], G90_GATE_ID)
        self.assertEqual(
            [g["gate_id"] for g in self.offline_90.gates[:88]],
            [g["gate_id"] for g in self.offline_88.gates],
        )

    def test_56_master_90gate_g89_cleanfeed_fault_propagates_fail_closed(self) -> None:
        rep = evaluate_90gate_preflight(
            force_clean_room=True,
            master_88_override=self.clean_offline_88,
            emphasized_rec_grid_hdmi_kwargs={
                "configured_hdmi_info_display": "On",
                "rec_media_dur_hdmi_output": "Off(HDMI Only)",
                "observed_hdmi_baked_overlay_pixels": 12,
            },
        )
        self.assertEqual(rep.summary["verified_gates"], 86)
        self.assertFalse(rep.g89_to_g90_all_passed)
        self.assertFalse(rep.offline_87_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G89_FORCED_HDMIONLY_OR_RAW_CLEANFEED_CLAMP_LEAK
        )

    def test_57_master_90gate_g90_touch_bench_fault_propagates_fail_closed(
        self,
    ) -> None:
        rep = evaluate_90gate_preflight(
            force_clean_room=True,
            master_88_override=self.clean_offline_88,
            touch_op_sunny_weather_kwargs={
                "pre_reset_touch_operation": "On",
                "bench_unattended_tier0_active": True,
            },
        )
        self.assertEqual(rep.summary["verified_gates"], 86)
        self.assertFalse(rep.g89_to_g90_all_passed)
        self.assertFalse(rep.offline_87_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G90_BENCH_UNATTENDED_TOUCH_SHOOTING_LIVE_HAZARD
        )

    def test_58_master_90gate_g90_sunny_weather_fault_propagates_fail_closed(
        self,
    ) -> None:
        rep = evaluate_90gate_preflight(
            force_clean_room=True,
            master_88_override=self.clean_offline_88,
            touch_op_sunny_weather_kwargs={
                "pre_reset_monitor_brightness_mode": "Sunny Weather",
                "indoor_bench_environment": True,
            },
        )
        self.assertEqual(rep.summary["verified_gates"], 86)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G90_SUNNY_WEATHER_INDOOR_BENCH_BRIGHTNESS_OR_POWER_HAZARD,
        )

    def test_59_master_90gate_upstream_g88_failure_preserved_fail_closed(self) -> None:
        faulted_88 = fx3_safety.evaluate_88gate_preflight(
            force_clean_room=True,
            master_86_override=fx3_safety.evaluate_86gate_preflight(
                force_clean_room=True
            ),
            monitor_flip_af_interval_kwargs={
                "observed_playback_monitor_horizontally_inverted": True
            },
        )
        rep = evaluate_90gate_preflight(
            force_clean_room=True, master_88_override=faulted_88
        )
        self.assertFalse(rep.g13_to_g90_all_passed)
        self.assertEqual(rep.status, faulted_88.status)

    def test_60_master_90gate_persistent_emmc_write_request_blocks(self) -> None:
        rep = evaluate_90gate_preflight(
            force_clean_room=True,
            master_88_override=self.clean_dryrun_88,
            simulate_bench_dry_run=True,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_87_gates_verified)
        self.assertFalse(rep.all_90_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_61_cli_verify_g89_text_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-g89-emphasized-rec-grid-hdmi", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("clamp=True,baked_px=0", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g89-emphasized-rec-grid-hdmi", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        payload = json.loads(jbuf.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_62_cli_verify_g90_text_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-g90-touch-op-sunny-weather", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("bench_locked=True", buf.getvalue())
        self.assertIn("sunny_blocked=True", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g90-touch-op-sunny-weather", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        payload = json.loads(jbuf.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_63_cli_verify_90_gates_offline_clean_room(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_90gate_preflight",
            return_value=self.clean_offline_90,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-90-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=87/90", buf.getvalue())
        self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

    def test_64_cli_verify_90_gates_simulate_bench_dry_run_json(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_90gate_preflight",
            return_value=self.clean_dryrun_90,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    [
                        "verify-90-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 90)
        self.assertTrue(payload["all_90_gates_verified"])
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_65_standalone_module_main_offline_and_dry_run(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.evaluate_90gate_preflight",
            return_value=self.clean_offline_90,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=87/90", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard.evaluate_90gate_preflight",
            return_value=self.clean_dryrun_90,
        ):
            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertEqual(data["summary"]["verified_gates"], 90)
        self.assertTrue(data["all_90_gates_verified"])

    def test_66_unmocked_end_to_end_evaluate_90gate_preflight_smoke(self) -> None:
        rep = evaluate_90gate_preflight(force_clean_room=True)
        self.assertEqual(rep.summary["total_gates"], 90)
        self.assertEqual(rep.summary["verified_gates"], 87)
        self.assertTrue(rep.offline_87_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)


if __name__ == "__main__":
    unittest.main()
