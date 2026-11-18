"""Phase 271 (Task H306, Milestone 110/110 Safety Gates, Wave-45) Dual-Mode Unit
Tests (74 tests, < 4.0s runtime) for
`fx3_safety.realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard`:

- Gate `G109` (`GATE_G109_FOCUS_MAGNIFIER_AUTO_MAG_MF_INITIAL_X10_PEAKING_AND_STILL_AF_ILLUMINATOR_GUARD`):
  - `ILME-FX3 Ver. 7.02` (`ilc/2210`) `[Focus Assistant]` exact nomenclature:
    `[Auto Magnifier in MF] = [On]` default (rejecting legacy `"MF Assist"`
    spoofing), `[Focus Magnifier]` on `Custom Button 5`, `[Focus Magnif. Time] =
    [No Limit]` default (`2 Sec` / `5 Sec` / `No Limit`), separate Still & Movie
    `[Initial Focus Mag.]` registers both defaulting to `[x1.0]` (`x1.0` /
    `x4.0`), Still-only `[AF in Focus Mag.] = [On]` default.
  - `[Peaking Display]` (`Off` default, `[Peaking Level] = [Mid]`,
    `[Peaking Color] = [White]`, `Control Wheel Right`) clean-HDMI isolation
    (`hdmi_clean_feed_focus_mag_or_peaking_leak_pixels == 0`) & `[AF Illuminator]`
    (`Auto` default / `Off`) strictly Still-only
    (`movie_sq_af_illuminator_fire_events == 0`).
- Gate `G110` (`GATE_G110_AREA_DATETIME_ZERO_RF_VIDEO_LIGHT_POWER_LINK_AND_HDMI_RES_LOG_OVERRIDE_GUARD`):
  - `MENU -> Setup -> [Area/Date] -> [Area/Date/Time Setting]` (rejecting legacy
    `"Date/Time Setup"` spoofing), `[Daylight Savings] = [Off]` default, survival
    across `[Camera Settings Reset]` (cleared only by `[Initialize]` or RTC
    battery loss), and Creators' App `[Auto Time Correction]` /
    `[Auto Area Adjustment]` suppression under zero-RF bench posture
    (`[Airplane Mode] = [On]`, `passive_tx_bytes_emitted == 0`,
    `unsolicited_rtc_timezone_jump_events == 0`).
  - `[Video Light Mode]` (`[Power Link]` default / `[REC Link]` /
    `[REC Link & STBY]` / `[Auto]`) survival across `[Camera Settings Reset]` &
    MI-Shoe `5V <= 900 mA` (`G24`) rail budget enforcement, plus `[HDMI Resolution]`
    (`[Auto]` default / `2160p` / `1080p` / `1080i`) survival & Log internal-rec
    `1080p` downshift override when `Rec. Media dur HDMI Output = On`.
- Unified `110`-Gate Master Safety Preflight (`evaluate_110gate_preflight` /
  `verify-110-gates`): `107/110` offline and `110/110` in
  `--simulate-bench-dry-run` with all hardware write/live-attach redlines
  hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard import (
    ACTIVE_LOG_SHOOTING_MODES_G110,
    AF_ILLUMINATOR_AUTO_G109,
    AF_ILLUMINATOR_FACTORY_DEFAULT_G109,
    AF_ILLUMINATOR_MENU_PATH_G109,
    AF_ILLUMINATOR_OFF_G109,
    AF_IN_FOCUS_MAG_FACTORY_DEFAULT_G109,
    AIRPLANE_MODE_MENU_PATH_G110,
    AIRPLANE_MODE_OFF_G110,
    AIRPLANE_MODE_ON_G110,
    ALLOWED_AF_ILLUMINATOR_MODES_G109,
    ALLOWED_AIRPLANE_MODES_G110,
    ALLOWED_DATE_FORMATS_G110,
    ALLOWED_DAYLIGHT_SAVINGS_STATES_G110,
    ALLOWED_FOCUS_MAG_TIMES_G109,
    ALLOWED_FOCUS_MODES_G109,
    ALLOWED_HDMI_FEED_MODES_G109,
    ALLOWED_HDMI_RESOLUTIONS_G110,
    ALLOWED_INITIAL_FOCUS_MAGS_G109,
    ALLOWED_LOG_SHOOTING_MODES_G110,
    ALLOWED_ON_OFF_STATES_G109,
    ALLOWED_PEAKING_COLORS_G109,
    ALLOWED_PEAKING_LEVELS_G109,
    ALLOWED_REC_MEDIA_DUR_HDMI_STATES_G110,
    ALLOWED_RESET_ACTIONS_PHASE271,
    ALLOWED_SHOOT_MODES_G109,
    ALLOWED_VIDEO_LIGHT_MODES_G110,
    AREA_DATETIME_EXACT_4_SUBITEMS_G110,
    AREA_DATE_TIME_MENU_PATH_G110,
    AREA_SETTING_UNCONFIGURED_DEFAULT_G110,
    AUTO_MAG_IN_MF_FACTORY_DEFAULT_G109,
    CANONICAL_AREA_DATETIME_LABEL_G110,
    CANONICAL_AUTO_MAG_IN_MF_LABEL_G109,
    DATE_FORMAT_DMY_G110,
    DATE_FORMAT_FACTORY_DEFAULT_G110,
    DATE_FORMAT_MDY_G110,
    DATE_FORMAT_YMD_G110,
    DAYLIGHT_SAVINGS_FACTORY_DEFAULT_G110,
    DAYLIGHT_SAVINGS_OFF_G110,
    DAYLIGHT_SAVINGS_ON_G110,
    DEFAULT_REPO_ROOT,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE271,
    DONOR_CHECK_MAX_SECONDS_PHASE271,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE271,
    FOCUS_ASSISTANT_MENU_PATH_G109,
    FOCUS_MAG_CUSTOM_BUTTON_DEFAULT_G109,
    FOCUS_MAG_TIME_2_SEC_G109,
    FOCUS_MAG_TIME_5_SEC_G109,
    FOCUS_MAG_TIME_FACTORY_DEFAULT_G109,
    FOCUS_MAG_TIME_NO_LIMIT_G109,
    FOCUS_MODE_AF_C_G109,
    FOCUS_MODE_AF_S_G109,
    FOCUS_MODE_DMF_G109,
    FOCUS_MODE_MF_G109,
    FX3_DEFAULT_FW_VERSION_PHASE271,
    FX3_HELP_GUIDE_CODE_PHASE271,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX6_MODEL_NAME,
    G109,
    G109_GATE_CODE,
    G109_GATE_ID,
    G110,
    G110_GATE_CODE,
    G110_GATE_ID,
    GATE_G109_FOCUS_MAGNIFIER_AUTO_MAG_MF_INITIAL_X10_PEAKING_AND_STILL_AF_ILLUMINATOR_GUARD,
    GATE_G110_AREA_DATETIME_ZERO_RF_VIDEO_LIGHT_POWER_LINK_AND_HDMI_RES_LOG_OVERRIDE_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_FEED_INFO_OFF_G109,
    HDMI_FEED_INFO_ON_G109,
    HDMI_FEED_RAW_G109,
    HDMI_INFO_DISPLAY_MENU_PATH_G109,
    HDMI_RESOLUTION_MENU_PATH_G110,
    HDMI_RES_1080I_G110,
    HDMI_RES_1080P_G110,
    HDMI_RES_2160P_G110,
    HDMI_RES_AUTO_G110,
    HDMI_RES_FACTORY_DEFAULT_G110,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    INITIAL_FOCUS_MAG_MOVIE_FACTORY_DEFAULT_G109,
    INITIAL_FOCUS_MAG_STILL_FACTORY_DEFAULT_G109,
    INITIAL_FOCUS_MAG_X1_0_G109,
    INITIAL_FOCUS_MAG_X4_0_G109,
    LEGACY_SPOOF_DATETIME_SETUP_LABEL_G110,
    LEGACY_SPOOF_MF_ASSIST_LABEL_G109,
    LOG_SHOOTING_CINE_EI_G110,
    LOG_SHOOTING_CINE_EI_QUICK_G110,
    LOG_SHOOTING_FLEXIBLE_ISO_G110,
    LOG_SHOOTING_OFF_G110,
    MISHOE_5V_MAX_BUDGET_MA_G110,
    OFF_G109,
    ON_G109,
    PEAKING_COLOR_BLUE_G109,
    PEAKING_COLOR_FACTORY_DEFAULT_G109,
    PEAKING_COLOR_RED_G109,
    PEAKING_COLOR_WHITE_G109,
    PEAKING_COLOR_YELLOW_G109,
    PEAKING_DISPLAY_FACTORY_DEFAULT_G109,
    PEAKING_DISPLAY_MENU_PATH_G109,
    PEAKING_LEVEL_FACTORY_DEFAULT_G109,
    PEAKING_LEVEL_HIGH_G109,
    PEAKING_LEVEL_LOW_G109,
    PEAKING_LEVEL_MID_G109,
    PEAKING_SELECT_DEFAULT_BUTTON_G109,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE271_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_110GATE_SCHEMA,
    REALHW_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_110GATE_VERSION,
    REC_MEDIA_DUR_HDMI_OFF_G110,
    REC_MEDIA_DUR_HDMI_ON_G110,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    RESET_ACTION_RESET_NETWORK_SET_PHASE271,
    SHOOT_MODE_MOVIE_G109,
    SHOOT_MODE_SQ_G109,
    SHOOT_MODE_STILL_G109,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G109_FOCUS_MAG_DEFAULTS_OR_CUSTOM_BTN5_VIOLATION,
    STATUS_BLOCKED_G109_HDMI_CLEAN_FEED_OVERLAY_LEAK_VIOLATION,
    STATUS_BLOCKED_G109_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF_VIOLATION,
    STATUS_BLOCKED_G109_RESET_BEHAVIOR_VIOLATION,
    STATUS_BLOCKED_G109_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG_VIOLATION,
    STATUS_BLOCKED_G109_TELEMETRY_INVALID,
    STATUS_BLOCKED_G110_HDMI_RES_LOG_1080P_OVERRIDE_VIOLATION,
    STATUS_BLOCKED_G110_LEGACY_DATETIME_SETUP_SPOOF_VIOLATION,
    STATUS_BLOCKED_G110_MISHOE_5V_OVERCURRENT_VIOLATION,
    STATUS_BLOCKED_G110_SETUP_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G110_TELEMETRY_INVALID,
    STATUS_BLOCKED_G110_ZERO_RF_CREATORS_APP_SYNC_VIOLATION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY,
    STATUS_VERIFIED_G109,
    STATUS_VERIFIED_G110,
    USB_PACKETS_TRANSMITTED,
    VIDEO_LIGHT_AUTO_G110,
    VIDEO_LIGHT_MODE_FACTORY_DEFAULT_G110,
    VIDEO_LIGHT_MODE_MENU_PATH_G110,
    VIDEO_LIGHT_POWER_LINK_G110,
    VIDEO_LIGHT_REC_LINK_G110,
    VIDEO_LIGHT_REC_LINK_STBY_G110,
    _is_forced_clean_room,
    _read_file_o_rdonly,
    audit_phase271_donor_contracts,
    compute_area_datetime_videolight_hdmires_matrix,
    compute_focus_mag_peaking_af_illuminator_matrix,
    evaluate_110_master_safety_gates,
    evaluate_110gate_preflight,
    evaluate_g109_focus_mag_peaking_af_illuminator_guard,
    evaluate_g110_area_datetime_videolight_hdmires_guard,
    main as module_main,
    resolve_fx3_area_datetime_videolight_and_hdmires_state,
    resolve_fx3_focus_mag_peaking_and_af_illuminator_state,
    run_110_gate_preflight,
    verify_area_datetime_videolight_hdmires_guard,
    verify_focus_mag_peaking_af_illuminator_guard,
)


class TestPhase271FocusMagDateTimeVideoLightHdmiRes110GateGuard(unittest.TestCase):
    """74 fast dual-mode tests covering Gates G109, G110, and unified 110-Gate preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        env_clean = _is_forced_clean_room()
        cls.active_offline_108 = fx3_safety.evaluate_108gate_preflight(
            force_clean_room=True if env_clean else None
        )
        cls.active_offline_110 = evaluate_110gate_preflight(
            force_clean_room=True if env_clean else None,
            master_108_override=cls.active_offline_108,
        )

        cls.clean_offline_108 = dataclasses.replace(
            cls.active_offline_108,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            clean_room_forced=True,
        )
        dry_gates_108 = tuple(
            {**g, "passed": True} if idx < 12 else dict(g)
            for idx, g in enumerate(cls.active_offline_108.gates)
        )
        dry_summary_108 = {
            **cls.active_offline_108.summary,
            "verified_gates": 108,
            "technical_gates_passed": 108,
            "blocked_or_pending_gates": 0,
            "g01_to_g12_verified": 12,
            "all_108_gates_verified": True,
            "dry_run_rehearsal_only": True,
        }
        cls.active_dryrun_108 = dataclasses.replace(
            cls.active_offline_108,
            dry_run_rehearsal_only=True,
            all_108_gates_verified=True,
            status="VERIFIED_ALL_108_GATES_DRY_RUN_SIMULATED_BACKUP",
            technical_gates_passed=108,
            summary=dry_summary_108,
            gates=dry_gates_108,
        )
        cls.clean_dryrun_108 = dataclasses.replace(
            cls.active_dryrun_108,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            clean_room_forced=True,
        )

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_110 = evaluate_110gate_preflight(
                force_clean_room=True, master_108_override=cls.clean_offline_108
            )
            cls.clean_dryrun_110 = evaluate_110gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_108_override=cls.clean_dryrun_108,
            )
        cls.active_dryrun_110 = evaluate_110gate_preflight(
            force_clean_room=True if env_clean else None,
            simulate_bench_dry_run=True,
            master_108_override=cls.active_dryrun_108,
        )

    # ------------------------------------------------------------------
    # Section A: Schema, Exports & O_RDONLY / Clean-Room Donor Audit (01..14)
    # ------------------------------------------------------------------

    def test_01_schema_version_gate_ids_and_redline_constants(self) -> None:
        self.assertEqual(
            REALHW_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_110GATE_SCHEMA,
            "realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard_v1",
        )
        self.assertEqual(
            REALHW_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_110GATE_VERSION, "1.0.0"
        )
        self.assertEqual(G109, G109_GATE_ID)
        self.assertEqual(G110, G110_GATE_ID)
        self.assertEqual(
            GATE_G109_FOCUS_MAGNIFIER_AUTO_MAG_MF_INITIAL_X10_PEAKING_AND_STILL_AF_ILLUMINATOR_GUARD,
            G109_GATE_CODE,
        )
        self.assertEqual(
            GATE_G110_AREA_DATETIME_ZERO_RF_VIDEO_LIGHT_POWER_LINK_AND_HDMI_RES_LOG_OVERRIDE_GUARD,
            G110_GATE_CODE,
        )
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX6_MODEL_NAME, "ILME-FX6")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE271, "7.02")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE271, "ilc/2210")
        self.assertEqual(MISHOE_5V_MAX_BUDGET_MA_G110, 900)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_top_level_package_exports_all_phase271_symbols_unshadowed(self) -> None:
        mod = fx3_safety.realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard
        self.assertEqual(fx3_safety.__all__.count(mod.__name__.split(".")[-1]), 1)
        for sym in (
            "G109",
            "G110",
            "G109_GATE_ID",
            "G110_GATE_ID",
            "GATE_G109_FOCUS_MAGNIFIER_AUTO_MAG_MF_INITIAL_X10_PEAKING_AND_STILL_AF_ILLUMINATOR_GUARD",
            "GATE_G110_AREA_DATETIME_ZERO_RF_VIDEO_LIGHT_POWER_LINK_AND_HDMI_RES_LOG_OVERRIDE_GUARD",
            "Master110GateReport",
            "evaluate_110gate_preflight",
            "run_110_gate_preflight",
            "evaluate_110_master_safety_gates",
            "verify_focus_mag_peaking_af_illuminator_guard",
            "verify_area_datetime_videolight_hdmires_guard",
        ):
            self.assertEqual(fx3_safety.__all__.count(sym), 1)
            self.assertIs(getattr(fx3_safety, sym), getattr(mod, sym))
        # Verify upstream G01..G108 evaluators and gate IDs remain unshadowed
        self.assertTrue(callable(fx3_safety.evaluate_104gate_preflight))
        self.assertTrue(callable(fx3_safety.evaluate_106gate_preflight))
        self.assertTrue(callable(fx3_safety.evaluate_108gate_preflight))
        self.assertEqual(fx3_safety.G107, fx3_safety.G107_GATE_ID)
        self.assertEqual(fx3_safety.G108, fx3_safety.G108_GATE_ID)

    def test_03_pinned_phase271_donor_specs_cover_fx3_and_fx6_contracts(self) -> None:
        self.assertEqual(len(PINNED_PHASE271_DONOR_SPECS), 6)
        bodies = {spec[0] for spec in PINNED_PHASE271_DONOR_SPECS.values()}
        self.assertEqual(bodies, {"FX3", "FX6"})
        self.assertLessEqual(DONOR_CHECK_MAX_SECONDS_PHASE271, 0.10)
        self.assertGreaterEqual(
            DONOR_CHECK_CI_MAX_SECONDS_PHASE271, DONOR_CHECK_MAX_SECONDS_PHASE271
        )

    def test_04_donor_audit_active_mode_within_budget_and_zero_leaked_bytes(
        self,
    ) -> None:
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE271
            if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"
            else DONOR_CHECK_MAX_SECONDS_PHASE271
        )
        audit = audit_phase271_donor_contracts()
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_100ms)
        self.assertLess(audit.elapsed_seconds, budget)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertIn(
            audit.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
        )

    def test_05_donor_audit_ci_github_actions_headroom(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            audit = audit_phase271_donor_contracts(force_clean_room=True)
            self.assertTrue(audit.valid)
            self.assertTrue(audit.within_budget_100ms)

    def test_06_donor_audit_force_clean_room_synthetic_parity(self) -> None:
        audit = audit_phase271_donor_contracts(force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(len(audit.checked_markers), 6)
        self.assertEqual(audit.missing_markers, ())
        self.assertIsInstance(audit.to_dict(), dict)

    def test_07_donor_audit_dual_env_toggles_force_clean_room(self) -> None:
        for env_key in ("FX3_FX6_FORCE_CLEAN_ROOM", ENV_CLEAN_ROOM_TEST_PHASE271):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                audit = audit_phase271_donor_contracts()
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_08_donor_audit_missing_work_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = audit_phase271_donor_contracts(
                work_root=Path(tmp) / "nonexistent", force_clean_room=False
            )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_09_donor_audit_clean_room_budget_exceeded_fails_closed(self) -> None:
        audit = audit_phase271_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY)

    def test_10_donor_audit_corrupted_donor_tree_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _body, rel, _sz, _sha, _mk, _lbl in PINNED_PHASE271_DONOR_SPECS.values():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"corrupt")
            audit = audit_phase271_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY)
            self.assertEqual(len(audit.missing_markers), 6)

    def test_11_donor_audit_oserror_on_read_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _body, rel, _sz, _sha, _mk, _lbl in PINNED_PHASE271_DONOR_SPECS.values():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"stub")
            with mock.patch(
                "fx3_safety.realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard._read_cached_donor_o_rdonly",
                side_effect=OSError("simulated O_RDONLY error"),
            ):
                audit = audit_phase271_donor_contracts(
                    work_root=root, force_clean_room=False
                )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY)

    def test_12_donor_audit_local_o_rdonly_budget_exceeded_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _body, rel, _sz, _sha, _mk, _lbl in PINNED_PHASE271_DONOR_SPECS.values():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"stub")
            audit = audit_phase271_donor_contracts(
                work_root=root, force_clean_room=False, max_budget_seconds=-1.0
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY)

    def test_13_read_file_o_rdonly_reads_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "sample.bin"
            fp.write_bytes(b"FX3_WAVE45_TEST_BYTES")
            self.assertEqual(_read_file_o_rdonly(fp), b"FX3_WAVE45_TEST_BYTES")

    def test_14_allowed_enum_tuples_exact_cardinalities(self) -> None:
        self.assertEqual(len(ALLOWED_RESET_ACTIONS_PHASE271), 4)
        self.assertEqual(len(ALLOWED_SHOOT_MODES_G109), 3)
        self.assertEqual(len(ALLOWED_FOCUS_MODES_G109), 4)
        self.assertEqual(len(ALLOWED_ON_OFF_STATES_G109), 2)
        self.assertEqual(len(ALLOWED_FOCUS_MAG_TIMES_G109), 3)
        self.assertEqual(len(ALLOWED_INITIAL_FOCUS_MAGS_G109), 2)
        self.assertEqual(len(ALLOWED_PEAKING_LEVELS_G109), 3)
        self.assertEqual(len(ALLOWED_PEAKING_COLORS_G109), 4)
        self.assertEqual(len(ALLOWED_AF_ILLUMINATOR_MODES_G109), 2)
        self.assertEqual(len(ALLOWED_HDMI_FEED_MODES_G109), 3)
        self.assertEqual(len(AREA_DATETIME_EXACT_4_SUBITEMS_G110), 4)
        self.assertEqual(len(ALLOWED_DAYLIGHT_SAVINGS_STATES_G110), 2)
        self.assertEqual(len(ALLOWED_DATE_FORMATS_G110), 3)
        self.assertEqual(len(ALLOWED_AIRPLANE_MODES_G110), 2)
        self.assertEqual(len(ALLOWED_VIDEO_LIGHT_MODES_G110), 4)
        self.assertEqual(len(ALLOWED_HDMI_RESOLUTIONS_G110), 4)
        self.assertEqual(len(ALLOWED_LOG_SHOOTING_MODES_G110), 4)
        self.assertEqual(len(ACTIVE_LOG_SHOOTING_MODES_G110), 3)
        self.assertEqual(len(ALLOWED_REC_MEDIA_DUR_HDMI_STATES_G110), 2)

    # ------------------------------------------------------------------
    # Section B: Gate G109 — [Focus Assistant], [Peaking] & [AF Illuminator] (15..37)
    # ------------------------------------------------------------------

    def test_15_g109_factory_defaults_verified_safe(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G109)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.focus_assistant_menu_path, FOCUS_ASSISTANT_MENU_PATH_G109)
        self.assertEqual(res.peaking_display_menu_path, PEAKING_DISPLAY_MENU_PATH_G109)
        self.assertEqual(res.af_illuminator_menu_path, AF_ILLUMINATOR_MENU_PATH_G109)
        self.assertEqual(res.hdmi_info_display_menu_path, HDMI_INFO_DISPLAY_MENU_PATH_G109)
        self.assertEqual(res.auto_mag_menu_label, CANONICAL_AUTO_MAG_IN_MF_LABEL_G109)
        self.assertEqual(res.legacy_mf_assist_spoof_events, 0)
        self.assertEqual(
            res.effective_post_reset_auto_mag_in_mf,
            AUTO_MAG_IN_MF_FACTORY_DEFAULT_G109,
        )
        self.assertEqual(
            res.focus_magnifier_custom_button, FOCUS_MAG_CUSTOM_BUTTON_DEFAULT_G109
        )
        self.assertEqual(
            res.effective_post_reset_focus_mag_time, FOCUS_MAG_TIME_FACTORY_DEFAULT_G109
        )
        self.assertEqual(
            res.effective_post_reset_still_initial_focus_mag,
            INITIAL_FOCUS_MAG_STILL_FACTORY_DEFAULT_G109,
        )
        self.assertEqual(
            res.effective_post_reset_movie_initial_focus_mag,
            INITIAL_FOCUS_MAG_MOVIE_FACTORY_DEFAULT_G109,
        )
        self.assertEqual(
            res.effective_post_reset_af_in_focus_mag,
            AF_IN_FOCUS_MAG_FACTORY_DEFAULT_G109,
        )
        self.assertEqual(
            res.effective_post_reset_peaking_display,
            PEAKING_DISPLAY_FACTORY_DEFAULT_G109,
        )
        self.assertEqual(res.peaking_select_button, PEAKING_SELECT_DEFAULT_BUTTON_G109)
        self.assertEqual(
            res.effective_post_reset_peaking_level, PEAKING_LEVEL_FACTORY_DEFAULT_G109
        )
        self.assertEqual(
            res.effective_post_reset_peaking_color, PEAKING_COLOR_FACTORY_DEFAULT_G109
        )
        self.assertEqual(
            res.effective_post_reset_af_illuminator, AF_ILLUMINATOR_FACTORY_DEFAULT_G109
        )
        self.assertEqual(res.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels, 0)
        self.assertEqual(res.movie_sq_af_illuminator_fire_events, 0)
        self.assertEqual(res.matrix_states_checked, 144)

    def test_16_g109_rejects_legacy_mf_assist_label_spoof(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            claimed_auto_mag_menu_label=LEGACY_SPOOF_MF_ASSIST_LABEL_G109
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G109_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF_VIOLATION
        )
        self.assertGreaterEqual(res.legacy_mf_assist_spoof_events, 1)

    def test_17_g109_rejects_nonzero_legacy_mf_assist_spoof_events(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            claimed_legacy_mf_assist_spoof_events=2
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G109_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF_VIOLATION
        )

    def test_18_g109_rejects_wrong_custom_button_default(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            focus_magnifier_custom_button="Custom Button 1"
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G109_FOCUS_MAG_DEFAULTS_OR_CUSTOM_BTN5_VIOLATION
        )

    def test_19_g109_rejects_wrong_peaking_select_button_default(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            peaking_select_button="Control Wheel Left"
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G109_FOCUS_MAG_DEFAULTS_OR_CUSTOM_BTN5_VIOLATION
        )

    def test_20_g109_focus_mag_time_options_2s_5s_nolimit_valid(self) -> None:
        for t in (
            FOCUS_MAG_TIME_2_SEC_G109,
            FOCUS_MAG_TIME_5_SEC_G109,
            FOCUS_MAG_TIME_NO_LIMIT_G109,
        ):
            res = verify_focus_mag_peaking_af_illuminator_guard(
                pre_reset_focus_mag_time=t
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_post_reset_focus_mag_time, t)

    def test_21_g109_separate_still_and_movie_initial_mag_registers_independent(
        self,
    ) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            pre_reset_still_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0_G109,
            pre_reset_movie_initial_focus_mag=INITIAL_FOCUS_MAG_X1_0_G109,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.still_movie_initial_mag_registers_independent)
        self.assertEqual(
            res.effective_post_reset_still_initial_focus_mag,
            INITIAL_FOCUS_MAG_X4_0_G109,
        )
        self.assertEqual(
            res.effective_post_reset_movie_initial_focus_mag,
            INITIAL_FOCUS_MAG_X1_0_G109,
        )

    def test_22_g109_movie_x4_still_x1_independent_valid(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            pre_reset_still_initial_focus_mag=INITIAL_FOCUS_MAG_X1_0_G109,
            pre_reset_movie_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0_G109,
        )
        self.assertTrue(res.valid)
        self.assertEqual(
            res.effective_post_reset_still_initial_focus_mag,
            INITIAL_FOCUS_MAG_X1_0_G109,
        )
        self.assertEqual(
            res.effective_post_reset_movie_initial_focus_mag,
            INITIAL_FOCUS_MAG_X4_0_G109,
        )

    def test_23_g109_af_in_focus_mag_armed_in_still_suppressed_in_movie_sq(
        self,
    ) -> None:
        st = verify_focus_mag_peaking_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_STILL_G109, pre_reset_af_in_focus_mag=ON_G109
        )
        self.assertTrue(st.valid)
        self.assertTrue(st.af_in_focus_mag_still_only_armed)
        for m in (SHOOT_MODE_MOVIE_G109, SHOOT_MODE_SQ_G109):
            mv = verify_focus_mag_peaking_af_illuminator_guard(
                shoot_mode=m, pre_reset_af_in_focus_mag=ON_G109
            )
            self.assertTrue(mv.valid)
            self.assertFalse(mv.af_in_focus_mag_still_only_armed)

    def test_24_g109_rejects_movie_af_in_focus_mag_events(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_MOVIE_G109,
            claimed_movie_af_in_focus_mag_events=1,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G109_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG_VIOLATION,
        )

    def test_25_g109_peaking_levels_and_colors_all_valid(self) -> None:
        for lvl in (
            PEAKING_LEVEL_HIGH_G109,
            PEAKING_LEVEL_MID_G109,
            PEAKING_LEVEL_LOW_G109,
        ):
            for clr in (
                PEAKING_COLOR_RED_G109,
                PEAKING_COLOR_YELLOW_G109,
                PEAKING_COLOR_BLUE_G109,
                PEAKING_COLOR_WHITE_G109,
            ):
                res = verify_focus_mag_peaking_af_illuminator_guard(
                    pre_reset_peaking_display=ON_G109,
                    pre_reset_peaking_level=lvl,
                    pre_reset_peaking_color=clr,
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.effective_post_reset_peaking_level, lvl)
                self.assertEqual(res.effective_post_reset_peaking_color, clr)

    def test_26_g109_clean_hdmi_and_hdmi_raw_isolate_focus_mag_and_peaking(
        self,
    ) -> None:
        for h_mode in (HDMI_FEED_INFO_OFF_G109, HDMI_FEED_RAW_G109, HDMI_FEED_INFO_ON_G109):
            res = verify_focus_mag_peaking_af_illuminator_guard(
                hdmi_feed_mode=h_mode,
                pre_reset_peaking_display=ON_G109,
                pre_reset_still_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0_G109,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels, 0)

    def test_27_g109_rejects_hdmi_clean_feed_overlay_leak_pixels(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            hdmi_feed_mode=HDMI_FEED_INFO_OFF_G109,
            pre_reset_peaking_display=ON_G109,
            claimed_hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=512,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G109_HDMI_CLEAN_FEED_OVERLAY_LEAK_VIOLATION
        )

    def test_28_g109_rejects_external_hdmi_raw_focus_mag_or_peaking_applied(
        self,
    ) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            hdmi_feed_mode=HDMI_FEED_RAW_G109,
            claimed_external_hdmi_focus_mag_or_peaking_applied=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G109_HDMI_CLEAN_FEED_OVERLAY_LEAK_VIOLATION
        )

    def test_29_g109_af_illuminator_still_only_armed_vs_movie_sq_suppressed(
        self,
    ) -> None:
        st = verify_focus_mag_peaking_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_STILL_G109,
            focus_mode=FOCUS_MODE_AF_S_G109,
            pre_reset_af_illuminator=AF_ILLUMINATOR_AUTO_G109,
        )
        self.assertTrue(st.valid)
        self.assertTrue(st.af_illuminator_still_only_armed)
        for m in (SHOOT_MODE_MOVIE_G109, SHOOT_MODE_SQ_G109):
            mv = verify_focus_mag_peaking_af_illuminator_guard(
                shoot_mode=m,
                focus_mode=FOCUS_MODE_AF_C_G109,
                pre_reset_af_illuminator=AF_ILLUMINATOR_AUTO_G109,
            )
            self.assertTrue(mv.valid)
            self.assertFalse(mv.af_illuminator_still_only_armed)

    def test_30_g109_rejects_movie_sq_af_illuminator_fire_events(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_SQ_G109,
            claimed_movie_sq_af_illuminator_fire_events=1,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G109_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG_VIOLATION,
        )

    def test_31_g109_reset_camera_settings_and_initialize_restore_defaults(
        self,
    ) -> None:
        for r_act in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
            res = verify_focus_mag_peaking_af_illuminator_guard(
                reset_action=r_act,
                pre_reset_auto_mag_in_mf=OFF_G109,
                pre_reset_focus_mag_time=FOCUS_MAG_TIME_2_SEC_G109,
                pre_reset_still_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0_G109,
                pre_reset_movie_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0_G109,
                pre_reset_af_in_focus_mag=OFF_G109,
                pre_reset_peaking_display=ON_G109,
                pre_reset_peaking_level=PEAKING_LEVEL_HIGH_G109,
                pre_reset_peaking_color=PEAKING_COLOR_RED_G109,
                pre_reset_af_illuminator=AF_ILLUMINATOR_OFF_G109,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_post_reset_auto_mag_in_mf, ON_G109)
            self.assertEqual(
                res.effective_post_reset_focus_mag_time, FOCUS_MAG_TIME_NO_LIMIT_G109
            )
            self.assertEqual(
                res.effective_post_reset_still_initial_focus_mag,
                INITIAL_FOCUS_MAG_X1_0_G109,
            )
            self.assertEqual(
                res.effective_post_reset_movie_initial_focus_mag,
                INITIAL_FOCUS_MAG_X1_0_G109,
            )
            self.assertEqual(res.effective_post_reset_af_in_focus_mag, ON_G109)
            self.assertEqual(res.effective_post_reset_peaking_display, OFF_G109)
            self.assertEqual(
                res.effective_post_reset_peaking_level, PEAKING_LEVEL_MID_G109
            )
            self.assertEqual(
                res.effective_post_reset_peaking_color, PEAKING_COLOR_WHITE_G109
            )
            self.assertEqual(
                res.effective_post_reset_af_illuminator, AF_ILLUMINATOR_AUTO_G109
            )

    def test_32_g109_reset_network_set_preserves_focus_and_peaking(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE271,
            pre_reset_peaking_display=ON_G109,
            pre_reset_peaking_color=PEAKING_COLOR_YELLOW_G109,
            pre_reset_still_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0_G109,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_peaking_display, ON_G109)
        self.assertEqual(
            res.effective_post_reset_peaking_color, PEAKING_COLOR_YELLOW_G109
        )
        self.assertEqual(
            res.effective_post_reset_still_initial_focus_mag,
            INITIAL_FOCUS_MAG_X4_0_G109,
        )

    def test_33_g109_rejects_claimed_reset_persistence_mismatch(self) -> None:
        res = verify_focus_mag_peaking_af_illuminator_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_peaking_display=ON_G109,
            claimed_post_reset_peaking_display=ON_G109,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G109_RESET_BEHAVIOR_VIOLATION)

    def test_34_g109_rejects_invalid_model_and_invalid_enum_telemetry(self) -> None:
        bad_body = verify_focus_mag_peaking_af_illuminator_guard(
            body_model_name=FX6_MODEL_NAME
        )
        self.assertFalse(bad_body.valid)
        self.assertEqual(bad_body.status, STATUS_BLOCKED_G109_TELEMETRY_INVALID)

        bad_enum = verify_focus_mag_peaking_af_illuminator_guard(
            pre_reset_still_initial_focus_mag="x8.0"
        )
        self.assertFalse(bad_enum.valid)
        self.assertEqual(bad_enum.status, STATUS_BLOCKED_G109_TELEMETRY_INVALID)

    def test_35_g109_matrix_144_states_all_invariants_hold(self) -> None:
        m = compute_focus_mag_peaking_af_illuminator_matrix()
        self.assertEqual(m["states_checked"], 144)
        self.assertEqual(m["hdmi_clean_feed_leaks"], 0)
        self.assertEqual(m["movie_sq_af_illuminator_fires"], 0)
        self.assertEqual(m["still_movie_initial_mag_couplings"], 0)
        self.assertTrue(m["all_invariants_hold"])

    def test_36_g109_resolve_state_dmf_and_af_s_modes(self) -> None:
        st = resolve_fx3_focus_mag_peaking_and_af_illuminator_state(
            shoot_mode=SHOOT_MODE_STILL_G109,
            focus_mode=FOCUS_MODE_DMF_G109,
            hdmi_feed_mode=HDMI_FEED_INFO_OFF_G109,
        )
        self.assertTrue(st["hdmi_clean_feed_active"])
        self.assertTrue(st["af_in_focus_mag_still_only_armed"])
        self.assertTrue(st["af_illuminator_still_only_armed"])

    def test_37_g109_evaluate_blocks_persistent_emmc_writes_and_donor_failure(
        self,
    ) -> None:
        verdict, res = evaluate_g109_focus_mag_peaking_af_illuminator_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

        bad_audit = dataclasses.replace(
            audit_phase271_donor_contracts(force_clean_room=True),
            valid=False,
            status=STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY,
        )
        v2, r2 = evaluate_g109_focus_mag_peaking_af_illuminator_guard(
            donor_audit=bad_audit
        )
        self.assertFalse(v2.passed)
        self.assertEqual(r2.status, STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY)

    # ------------------------------------------------------------------
    # Section C: Gate G110 — [Area/Date/Time], Zero-RF, [Video Light], [HDMI Res] (38..59)
    # ------------------------------------------------------------------

    def test_38_g110_factory_defaults_verified_safe(self) -> None:
        res = verify_area_datetime_videolight_hdmires_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G110)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.area_date_time_menu_path, AREA_DATE_TIME_MENU_PATH_G110)
        self.assertEqual(res.video_light_mode_menu_path, VIDEO_LIGHT_MODE_MENU_PATH_G110)
        self.assertEqual(res.hdmi_resolution_menu_path, HDMI_RESOLUTION_MENU_PATH_G110)
        self.assertEqual(res.airplane_mode_menu_path, AIRPLANE_MODE_MENU_PATH_G110)
        self.assertEqual(res.area_datetime_menu_label, CANONICAL_AREA_DATETIME_LABEL_G110)
        self.assertEqual(res.legacy_datetime_setup_spoof_events, 0)
        self.assertEqual(res.area_datetime_subitems, AREA_DATETIME_EXACT_4_SUBITEMS_G110)
        self.assertEqual(
            res.effective_post_reset_area_setting,
            AREA_SETTING_UNCONFIGURED_DEFAULT_G110,
        )
        self.assertEqual(
            res.effective_post_reset_daylight_savings,
            DAYLIGHT_SAVINGS_FACTORY_DEFAULT_G110,
        )
        self.assertEqual(
            res.effective_post_reset_date_format, DATE_FORMAT_FACTORY_DEFAULT_G110
        )
        self.assertEqual(res.airplane_mode, AIRPLANE_MODE_ON_G110)
        self.assertTrue(res.zero_rf_bench_enforced)
        self.assertEqual(res.effective_auto_time_correction, "Off")
        self.assertEqual(res.effective_auto_area_adjustment, "Off")
        self.assertEqual(res.passive_tx_bytes_emitted, 0)
        self.assertEqual(res.unsolicited_rtc_timezone_jump_events, 0)
        self.assertEqual(
            res.effective_post_reset_video_light_mode,
            VIDEO_LIGHT_MODE_FACTORY_DEFAULT_G110,
        )
        self.assertEqual(res.mishoe_5v_budget_ma, 900)
        self.assertEqual(res.mishoe_5v_overcurrent_events, 0)
        self.assertEqual(
            res.effective_post_reset_hdmi_resolution, HDMI_RES_FACTORY_DEFAULT_G110
        )
        self.assertEqual(res.effective_hdmi_output_resolution, HDMI_RES_AUTO_G110)
        self.assertEqual(res.hdmi_res_log_internal_rec_2160p_bypass_events, 0)
        self.assertEqual(res.matrix_states_checked, 256)

    def test_39_g110_rejects_legacy_datetime_setup_label_spoof(self) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            claimed_area_datetime_menu_label=LEGACY_SPOOF_DATETIME_SETUP_LABEL_G110
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G110_LEGACY_DATETIME_SETUP_SPOOF_VIOLATION
        )
        self.assertGreaterEqual(res.legacy_datetime_setup_spoof_events, 1)

    def test_40_g110_rejects_nonzero_legacy_datetime_spoof_events(self) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            claimed_legacy_datetime_setup_spoof_events=1
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G110_LEGACY_DATETIME_SETUP_SPOOF_VIOLATION
        )

    def test_41_g110_setup_items_survive_camera_settings_reset_and_network_reset(
        self,
    ) -> None:
        for r_act in (
            RESET_ACTION_CAMERA_SETTINGS_RESET,
            RESET_ACTION_RESET_NETWORK_SET_PHASE271,
        ):
            res = verify_area_datetime_videolight_hdmires_guard(
                reset_action=r_act,
                pre_reset_area_setting="Asia/Tokyo",
                pre_reset_daylight_savings=DAYLIGHT_SAVINGS_ON_G110,
                pre_reset_datetime_value="2026-11-17 18:00:00",
                pre_reset_date_format=DATE_FORMAT_DMY_G110,
                pre_reset_video_light_mode=VIDEO_LIGHT_REC_LINK_STBY_G110,
                pre_reset_hdmi_resolution=HDMI_RES_1080P_G110,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_post_reset_area_setting, "Asia/Tokyo")
            self.assertEqual(
                res.effective_post_reset_daylight_savings, DAYLIGHT_SAVINGS_ON_G110
            )
            self.assertEqual(
                res.effective_post_reset_datetime_value, "2026-11-17 18:00:00"
            )
            self.assertEqual(
                res.effective_post_reset_date_format, DATE_FORMAT_DMY_G110
            )
            self.assertEqual(
                res.effective_post_reset_video_light_mode,
                VIDEO_LIGHT_REC_LINK_STBY_G110,
            )
            self.assertEqual(
                res.effective_post_reset_hdmi_resolution, HDMI_RES_1080P_G110
            )
            self.assertFalse(res.datetime_reprompt_required)

    def test_42_g110_initialize_clears_all_setup_items_and_requires_reprompt(
        self,
    ) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            reset_action=RESET_ACTION_INITIALIZE,
            pre_reset_area_setting="America/Los_Angeles",
            pre_reset_daylight_savings=DAYLIGHT_SAVINGS_ON_G110,
            pre_reset_date_format=DATE_FORMAT_MDY_G110,
            pre_reset_video_light_mode=VIDEO_LIGHT_REC_LINK_G110,
            pre_reset_hdmi_resolution=HDMI_RES_2160P_G110,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.datetime_reprompt_required)
        self.assertEqual(
            res.effective_post_reset_area_setting,
            AREA_SETTING_UNCONFIGURED_DEFAULT_G110,
        )
        self.assertEqual(
            res.effective_post_reset_daylight_savings, DAYLIGHT_SAVINGS_OFF_G110
        )
        self.assertEqual(
            res.effective_post_reset_date_format, DATE_FORMAT_YMD_G110
        )
        self.assertEqual(
            res.effective_post_reset_video_light_mode, VIDEO_LIGHT_POWER_LINK_G110
        )
        self.assertEqual(res.effective_post_reset_hdmi_resolution, HDMI_RES_AUTO_G110)

    def test_43_g110_rtc_backup_battery_loss_clears_datetime_and_reprompts_only(
        self,
    ) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            reset_action=RESET_ACTION_NONE,
            rtc_backup_battery_lost=True,
            pre_reset_area_setting="Europe/London",
            pre_reset_daylight_savings=DAYLIGHT_SAVINGS_ON_G110,
            pre_reset_video_light_mode=VIDEO_LIGHT_AUTO_G110,
            pre_reset_hdmi_resolution=HDMI_RES_1080I_G110,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.datetime_reprompt_required)
        self.assertEqual(
            res.effective_post_reset_area_setting,
            AREA_SETTING_UNCONFIGURED_DEFAULT_G110,
        )
        self.assertEqual(
            res.effective_post_reset_video_light_mode, VIDEO_LIGHT_AUTO_G110
        )
        self.assertEqual(
            res.effective_post_reset_hdmi_resolution, HDMI_RES_1080I_G110
        )

    def test_44_g110_rejects_claimed_setup_reset_persistence_corruption(self) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_video_light_mode=VIDEO_LIGHT_REC_LINK_G110,
            claimed_post_reset_video_light_mode=VIDEO_LIGHT_POWER_LINK_G110,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G110_SETUP_RESET_PERSISTENCE_VIOLATION
        )

    def test_45_g110_zero_rf_hard_suppresses_creators_app_auto_time_and_area(
        self,
    ) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            airplane_mode=AIRPLANE_MODE_ON_G110,
            requested_auto_time_correction="On",
            requested_auto_area_adjustment="On",
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.zero_rf_bench_enforced)
        self.assertEqual(res.effective_auto_time_correction, "Off")
        self.assertEqual(res.effective_auto_area_adjustment, "Off")
        self.assertEqual(res.passive_tx_bytes_emitted, 0)
        self.assertEqual(res.unsolicited_rtc_timezone_jump_events, 0)

    def test_46_g110_rejects_airplane_off_on_zero_rf_bench(self) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            airplane_mode=AIRPLANE_MODE_OFF_G110, zero_rf_bench_required=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G110_ZERO_RF_CREATORS_APP_SYNC_VIOLATION
        )

    def test_47_g110_rejects_active_creators_app_sync_or_tx_or_rtc_jump(self) -> None:
        r1 = verify_area_datetime_videolight_hdmires_guard(
            claimed_effective_auto_time_correction="On"
        )
        self.assertEqual(
            r1.status, STATUS_BLOCKED_G110_ZERO_RF_CREATORS_APP_SYNC_VIOLATION
        )
        r2 = verify_area_datetime_videolight_hdmires_guard(
            claimed_effective_auto_area_adjustment="On"
        )
        self.assertEqual(
            r2.status, STATUS_BLOCKED_G110_ZERO_RF_CREATORS_APP_SYNC_VIOLATION
        )
        r3 = verify_area_datetime_videolight_hdmires_guard(
            claimed_passive_tx_bytes_emitted=12
        )
        self.assertEqual(
            r3.status, STATUS_BLOCKED_G110_ZERO_RF_CREATORS_APP_SYNC_VIOLATION
        )
        r4 = verify_area_datetime_videolight_hdmires_guard(
            claimed_unsolicited_rtc_timezone_jump_events=1
        )
        self.assertEqual(
            r4.status, STATUS_BLOCKED_G110_ZERO_RF_CREATORS_APP_SYNC_VIOLATION
        )

    def test_48_g110_video_light_all_4_modes_valid_within_900ma_budget(self) -> None:
        for mode in ALLOWED_VIDEO_LIGHT_MODES_G110:
            res = verify_area_datetime_videolight_hdmires_guard(
                pre_reset_video_light_mode=mode, mishoe_5v_draw_ma=900
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_post_reset_video_light_mode, mode)
            self.assertEqual(res.mishoe_5v_overcurrent_events, 0)

    def test_49_g110_rejects_mishoe_5v_overcurrent_exceeding_900ma(self) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            pre_reset_video_light_mode=VIDEO_LIGHT_REC_LINK_G110,
            mishoe_5v_draw_ma=901,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G110_MISHOE_5V_OVERCURRENT_VIOLATION
        )
        self.assertGreaterEqual(res.mishoe_5v_overcurrent_events, 1)

    def test_50_g110_rejects_explicit_mishoe_overcurrent_events(self) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            claimed_mishoe_5v_overcurrent_events=1
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G110_MISHOE_5V_OVERCURRENT_VIOLATION
        )

    def test_51_g110_hdmi_res_log_internal_rec_forces_1080p_downshift(self) -> None:
        for log_mode in ACTIVE_LOG_SHOOTING_MODES_G110:
            for req_res in (HDMI_RES_AUTO_G110, HDMI_RES_2160P_G110):
                res = verify_area_datetime_videolight_hdmires_guard(
                    pre_reset_hdmi_resolution=req_res,
                    log_shooting_mode=log_mode,
                    internal_recording_active=True,
                    rec_media_dur_hdmi=REC_MEDIA_DUR_HDMI_ON_G110,
                )
                self.assertTrue(res.valid)
                self.assertTrue(res.log_internal_rec_1080p_downshift_active)
                self.assertEqual(
                    res.effective_hdmi_output_resolution, HDMI_RES_1080P_G110
                )

    def test_52_g110_hdmi_res_log_hdmi_only_off_permits_2160p(self) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            pre_reset_hdmi_resolution=HDMI_RES_2160P_G110,
            log_shooting_mode=LOG_SHOOTING_CINE_EI_G110,
            internal_recording_active=False,
            rec_media_dur_hdmi=REC_MEDIA_DUR_HDMI_OFF_G110,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.log_internal_rec_1080p_downshift_active)
        self.assertEqual(res.effective_hdmi_output_resolution, HDMI_RES_2160P_G110)

    def test_53_g110_rejects_2160p_bypass_during_log_internal_recording(self) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            pre_reset_hdmi_resolution=HDMI_RES_2160P_G110,
            log_shooting_mode=LOG_SHOOTING_FLEXIBLE_ISO_G110,
            internal_recording_active=True,
            rec_media_dur_hdmi=REC_MEDIA_DUR_HDMI_ON_G110,
            claimed_effective_hdmi_output_resolution=HDMI_RES_2160P_G110,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G110_HDMI_RES_LOG_1080P_OVERRIDE_VIOLATION
        )
        self.assertGreaterEqual(res.hdmi_res_log_internal_rec_2160p_bypass_events, 1)

    def test_54_g110_rejects_explicit_log_2160p_bypass_counter(self) -> None:
        res = verify_area_datetime_videolight_hdmires_guard(
            claimed_hdmi_res_log_internal_rec_2160p_bypass_events=1
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G110_HDMI_RES_LOG_1080P_OVERRIDE_VIOLATION
        )

    def test_55_g110_rejects_invalid_model_and_invalid_subitems_or_enums(self) -> None:
        bad_body = verify_area_datetime_videolight_hdmires_guard(
            body_model_name=FX6_MODEL_NAME
        )
        self.assertEqual(bad_body.status, STATUS_BLOCKED_G110_TELEMETRY_INVALID)

        bad_sub = verify_area_datetime_videolight_hdmires_guard(
            area_datetime_subitems=("Area Setting", "Date/Time")
        )
        self.assertEqual(bad_sub.status, STATUS_BLOCKED_G110_TELEMETRY_INVALID)

        bad_hres = verify_area_datetime_videolight_hdmires_guard(
            pre_reset_hdmi_resolution="4320p"
        )
        self.assertEqual(bad_hres.status, STATUS_BLOCKED_G110_TELEMETRY_INVALID)

    def test_56_g110_matrix_256_states_all_invariants_hold(self) -> None:
        m = compute_area_datetime_videolight_hdmires_matrix()
        self.assertEqual(m["states_checked"], 256)
        self.assertEqual(m["zero_rf_creators_app_leaks"], 0)
        self.assertEqual(m["log_internal_rec_2160p_bypasses"], 0)
        self.assertEqual(m["setup_reset_corruptions"], 0)
        self.assertTrue(m["all_invariants_hold"])

    def test_57_g110_date_formats_all_3_options_valid(self) -> None:
        for dfmt in ALLOWED_DATE_FORMATS_G110:
            res = verify_area_datetime_videolight_hdmires_guard(
                pre_reset_date_format=dfmt
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_post_reset_date_format, dfmt)

    def test_58_g110_resolve_state_non_zero_rf_diagnostic_behavior(self) -> None:
        st = resolve_fx3_area_datetime_videolight_and_hdmires_state(
            airplane_mode=AIRPLANE_MODE_OFF_G110,
            requested_auto_time_correction="On",
            requested_auto_area_adjustment="On",
        )
        self.assertEqual(st["effective_auto_time_correction"], "On")
        self.assertEqual(st["effective_auto_area_adjustment"], "On")

    def test_59_g110_evaluate_blocks_persistent_emmc_writes_and_donor_failure(
        self,
    ) -> None:
        verdict, res = evaluate_g110_area_datetime_videolight_hdmires_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

        bad_audit = dataclasses.replace(
            audit_phase271_donor_contracts(force_clean_room=True),
            valid=False,
            status=STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY,
        )
        v2, r2 = evaluate_g110_area_datetime_videolight_hdmires_guard(
            donor_audit=bad_audit
        )
        self.assertFalse(v2.passed)
        self.assertEqual(r2.status, STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY)

    # ------------------------------------------------------------------
    # Section D: Unified 110-Gate Master Preflight & CLI (60..74)
    # ------------------------------------------------------------------

    def test_60_master_110gate_offline_default_107_of_110_awaiting_tier0(self) -> None:
        rep = self.active_offline_110
        self.assertEqual(rep.schema, REALHW_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_110GATE_SCHEMA)
        self.assertEqual(rep.version, REALHW_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_110GATE_VERSION)
        self.assertEqual(rep.status, "VERIFIED_107_OF_110_AWAITING_PHYSICAL_TIER0")
        self.assertTrue(rep.offline_107_gates_verified)
        self.assertFalse(rep.all_110_gates_verified)
        self.assertTrue(rep.g109_to_g110_all_passed)
        self.assertTrue(rep.g13_to_g110_all_passed)
        self.assertEqual(len(rep.gates), 110)
        self.assertEqual(rep.summary["total_gates"], 110)
        self.assertEqual(rep.summary["verified_gates"], 107)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 9)
        self.assertEqual(rep.summary["g13_to_g108_verified"], 96)
        self.assertEqual(rep.summary["g109_to_g110_verified"], 2)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_61_master_110gate_dry_run_rehearsal_110_of_110_and_redlines_locked(
        self,
    ) -> None:
        rep = self.active_dryrun_110
        self.assertEqual(rep.status, "VERIFIED_ALL_110_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertTrue(rep.all_110_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 110)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_62_master_110gate_blocks_persistent_emmc_write_request(self) -> None:
        rep = evaluate_110gate_preflight(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
            master_108_override=self.clean_offline_108,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_107_gates_verified)
        self.assertFalse(rep.all_110_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_63_master_110gate_propagates_g109_failure(self) -> None:
        rep = evaluate_110gate_preflight(
            force_clean_room=True,
            focus_mag_peaking_kwargs={
                "claimed_auto_mag_menu_label": LEGACY_SPOOF_MF_ASSIST_LABEL_G109
            },
            master_108_override=self.clean_offline_108,
        )
        self.assertFalse(rep.g109_to_g110_all_passed)
        self.assertFalse(rep.g13_to_g110_all_passed)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G109_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF_VIOLATION,
        )

    def test_64_master_110gate_propagates_g110_failure(self) -> None:
        rep = evaluate_110gate_preflight(
            force_clean_room=True,
            area_datetime_videolight_hdmires_kwargs={"mishoe_5v_draw_ma": 1200},
            master_108_override=self.clean_offline_108,
        )
        self.assertFalse(rep.g109_to_g110_all_passed)
        self.assertFalse(rep.g13_to_g110_all_passed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G110_MISHOE_5V_OVERCURRENT_VIOLATION
        )

    def test_65_master_110gate_propagates_upstream_m108_failure(self) -> None:
        bad_m108 = dataclasses.replace(
            self.clean_offline_108,
            g13_to_g108_all_passed=False,
            status="BLOCKED_UPSTREAM_M108_TEST",
        )
        rep = evaluate_110gate_preflight(
            force_clean_room=True, master_108_override=bad_m108
        )
        self.assertFalse(rep.g13_to_g110_all_passed)
        self.assertEqual(rep.status, "BLOCKED_UPSTREAM_M108_TEST")

    def test_66_master_110gate_aliases_and_to_dict_json_roundtrip(self) -> None:
        self.assertIs(evaluate_110_master_safety_gates, evaluate_110gate_preflight)
        self.assertIs(run_110_gate_preflight, evaluate_110gate_preflight)
        payload = json.loads(json.dumps(self.clean_offline_110.to_dict()))
        self.assertEqual(payload["summary"]["total_gates"], 110)
        self.assertEqual(payload["summary"]["verified_gates"], 107)

    def test_67_cli_verify_g109_primary_and_alias_text_and_json(self) -> None:
        for subcmd in (
            "verify-focus-mag-peaking-af-illuminator-guard",
            "verify-g109-focus-mag-peaking",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([subcmd, "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn(G109_GATE_ID, buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g109-focus-mag-peaking", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        parsed = json.loads(jbuf.getvalue())
        self.assertTrue(parsed["valid"])
        self.assertEqual(
            parsed["focus_mag_peaking_guard"]["legacy_mf_assist_spoof_events"], 0
        )

    def test_68_cli_verify_g110_primary_and_alias_text_and_json(self) -> None:
        for subcmd in (
            "verify-area-datetime-videolight-hdmires-guard",
            "verify-g110-datetime-videolight-hdmires",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([subcmd, "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn(G110_GATE_ID, buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                [
                    "verify-g110-datetime-videolight-hdmires",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc_j, 0)
        parsed = json.loads(jbuf.getvalue())
        self.assertTrue(parsed["valid"])
        self.assertEqual(
            parsed["area_datetime_videolight_hdmires_guard"][
                "mishoe_5v_overcurrent_events"
            ],
            0,
        )

    def test_69_cli_verify_110_gates_offline_text_output(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_110gate_preflight",
            return_value=self.clean_offline_110,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-110-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=107/110", out)
        self.assertIn("all_110_gates_verified=False", out)
        self.assertIn("usb_packets_transmitted=0", out)

    def test_70_cli_verify_110_gates_simulate_bench_dry_run_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_110gate_preflight",
            return_value=self.clean_dryrun_110,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    [
                        "verify-110-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=110/110", buf.getvalue())
            self.assertIn("all_110_gates_verified=True", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(
                    [
                        "verify-110-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertTrue(parsed["all_110_gates_verified"])
            self.assertEqual(parsed["summary"]["verified_gates"], 110)

    def test_71_standalone_module_main_offline_and_dry_run(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.evaluate_110gate_preflight",
            return_value=self.clean_offline_110,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=107/110", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard.evaluate_110gate_preflight",
            return_value=self.clean_dryrun_110,
        ):
            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            self.assertTrue(json.loads(jbuf.getvalue())["all_110_gates_verified"])

    def test_72_subprocess_cli_verify_g109_g110_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-g109-focus-mag-peaking",
                "--force-clean-room",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_G109)

    def test_73_fx3_clean_room_test_and_force_clean_room_env_in_master_110(
        self,
    ) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE271, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                rep = evaluate_110gate_preflight(
                    master_108_override=self.clean_offline_108
                )
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep.clean_room_forced)

    def test_74_upstream_verify_108_gates_remains_100pct_intact(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_108gate_preflight",
            return_value=self.clean_offline_108,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-108-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=105/108", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
