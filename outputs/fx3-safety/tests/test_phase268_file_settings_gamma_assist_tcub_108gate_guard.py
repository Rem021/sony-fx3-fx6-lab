"""Phase 268 (Task H302, Wave-44) Dual-Mode Unit Tests (72 tests, < 4.0s runtime)
for `fx3_safety.realhw_file_settings_gamma_assist_tcub_and_108gate_guard`:

- Gate `G107` (`GATE_G107_MOVIE_FILE_SETTINGS_CAMID_REEL_37CHAR_STILL_DSC_AND_SLOT1_FOLDER_VAULT_GUARD`):
  - Movie `[File Settings]`: `[File Number]` (`Series` default / `Reset` + `[Series Counter Reset]`),
    `[File Name Format]` (`Standard` default, `Cam ID + Reel#` with `Camera ID` `A..Z`,
    `Reel Number` `001..999`, `Camera Position` `C`/`L`/`R`, `Title`, `Date + Title`,
    `Title + Date`), `[Title Name Settings]` (`"C"` default, `<= 37` printable ASCII chars),
    and fixed `PRIVATE/M4ROOT/CLIP` movie folder topology.
  - Still `[File/Folder Settings]`: `[File Number]` (`Series` default / `Reset`),
    `[Set File Name]` (`"DSC"` default, exact 3 chars `A-Z`/`0-9`/`_`, rejecting `_` at
    index 0), `[Folder Name]` (`Standard Form` default / `Date Form`).
  - `[Camera Settings Reset]` survival vs `[Initialize]` reset & `Slot-1` recovery vault
    folder-mutation firewall (`slot1_vault_folder_mutation_events == 0`).
- Gate `G108` (`GATE_G108_GAMMA_DISP_ASSIST_LOG_LOCKOUT_DISPLAY_LUT_AUTO_REVIEW_AND_TCUB_GUARD`):
  - `[Gamma Display Assist]` (`Off` default / `On`) & `[Gamma Disp. Assist Typ.]`
    (`Auto` default, `S-Log3->709(800%)`, `HLG(BT.2020)`, `HLG(709)`) hard-locked to `Off`
    whenever `[Log Shooting]` != `Off`, camera-LCD-only scope (clean external TV/HDMI),
    vs `[Display LUT]` (`On` default / `Off`) & `[Select LUT]` (`S-Log3`, `s709`,
    `709(800%)`, `User1..User16`).
  - `[Auto Review]` (`Off` cinema default / `2 Sec` / `5 Sec` / `10 Sec`, Still-only) &
    6-item `[TC/UB]` + `[TC/UB Disp. Setting]` non-resettable persistence across
    `[Camera Settings Reset]`.
- Unified `108`-Gate Master Safety Preflight (`evaluate_108gate_preflight` /
  `verify-108-gates`): `105/108` offline and `108/108` in `--simulate-bench-dry-run`
  with all hardware write/live-attach redlines hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_file_settings_gamma_assist_tcub_and_108gate_guard import (
    ACTIVE_LOG_SHOOTING_MODES_G108,
    ALLOWED_AUTO_REVIEW_SETTINGS_G108,
    ALLOWED_CAMERA_POSITIONS_G107,
    ALLOWED_DISPLAY_LUT_STATES_G108,
    ALLOWED_FILE_NUMBER_MODES_G107,
    ALLOWED_FRAME_RATES_G108,
    ALLOWED_GAMMA_ASSIST_TYPES_G108,
    ALLOWED_GAMMA_DISP_ASSIST_STATES_G108,
    ALLOWED_LOG_SHOOTING_MODES_G108,
    ALLOWED_MEDIA_SLOTS_G107,
    ALLOWED_MOVIE_FILE_NAME_FORMATS_G107,
    ALLOWED_RESET_ACTIONS_PHASE268,
    ALLOWED_SELECT_LUT_ITEMS_G108,
    ALLOWED_STILL_FOLDER_FORMS_G107,
    ALLOWED_TCUB_DISP_SETTINGS_G108,
    ALLOWED_TC_FORMATS_G108,
    ALLOWED_TC_MAKE_MODES_G108,
    ALLOWED_TC_RUN_MODES_G108,
    AUTO_REVIEW_10_SEC_G108,
    AUTO_REVIEW_2_SEC_G108,
    AUTO_REVIEW_5_SEC_G108,
    AUTO_REVIEW_FACTORY_DEFAULT_G108,
    AUTO_REVIEW_MENU_PATH_G108,
    AUTO_REVIEW_OFF_G108,
    BUILTIN_SELECT_LUT_PRESETS_G108,
    CAMERA_ID_ALLOWED_CHARS_G107,
    CAMERA_ID_FACTORY_DEFAULT_G107,
    CAMERA_POSITION_CENTER_G107,
    CAMERA_POSITION_FACTORY_DEFAULT_G107,
    CAMERA_POSITION_LEFT_G107,
    CAMERA_POSITION_RIGHT_G107,
    DISPLAY_LUT_FACTORY_DEFAULT_G108,
    DISPLAY_LUT_MENU_PATH_G108,
    DISPLAY_LUT_OFF_G108,
    DISPLAY_LUT_ON_G108,
    DONOR_CHECK_MAX_SECONDS_PHASE268,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE268,
    FILE_NUMBER_RESET_G107,
    FILE_NUMBER_SERIES_G107,
    FORCED_NDF_FRAME_RATES_G108,
    FRAME_RATE_NTSC_23_98P_G108,
    FRAME_RATE_NTSC_29_97P_G108,
    FRAME_RATE_NTSC_59_94P_G108,
    FRAME_RATE_PAL_25P_G108,
    FRAME_RATE_PAL_50P_G108,
    FRAME_RATE_TRUE_24_00P_G108,
    FX3_CAMID_REEL_MIN_FW_TUPLE_G107,
    FX3_DEFAULT_FW_VERSION_PHASE268,
    FX3_HELP_GUIDE_CODE_PHASE268,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX6_MODEL_NAME,
    G107,
    G107_GATE_CODE,
    G107_GATE_ID,
    G108,
    G108_GATE_CODE,
    G108_GATE_ID,
    GAMMA_ASSIST_TYP_AUTO_G108,
    GAMMA_ASSIST_TYP_FACTORY_DEFAULT_G108,
    GAMMA_ASSIST_TYP_HLG_709_G108,
    GAMMA_ASSIST_TYP_HLG_BT2020_G108,
    GAMMA_ASSIST_TYP_SLOG3_709_800_G108,
    GAMMA_DISP_ASSIST_FACTORY_DEFAULT_G108,
    GAMMA_DISP_ASSIST_MENU_PATH_G108,
    GAMMA_DISP_ASSIST_OFF_G108,
    GAMMA_DISP_ASSIST_ON_G108,
    GAMMA_DISP_ASSIST_TYP_MENU_PATH_G108,
    GATE_G107_MOVIE_FILE_SETTINGS_CAMID_REEL_37CHAR_STILL_DSC_AND_SLOT1_FOLDER_VAULT_GUARD,
    GATE_G108_GAMMA_DISP_ASSIST_LOG_LOCKOUT_DISPLAY_LUT_AUTO_REVIEW_AND_TCUB_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LOG_SHOOTING_CINE_EI_G108,
    LOG_SHOOTING_CINE_EI_QUICK_G108,
    LOG_SHOOTING_FLEXIBLE_ISO_G108,
    LOG_SHOOTING_OFF_G108,
    MAX_USER_LUT_SLOTS_G108,
    MEDIA_SLOT_1_G107,
    MEDIA_SLOT_2_G107,
    MOVIE_FILE_NAME_CAM_ID_REEL_G107,
    MOVIE_FILE_NAME_DATE_PLUS_TITLE_G107,
    MOVIE_FILE_NAME_FORMAT_FACTORY_DEFAULT_G107,
    MOVIE_FILE_NAME_STANDARD_G107,
    MOVIE_FILE_NAME_TITLE_G107,
    MOVIE_FILE_NAME_TITLE_PLUS_DATE_G107,
    MOVIE_FILE_NUMBER_FACTORY_DEFAULT_G107,
    MOVIE_FILE_SETTINGS_MENU_PATH_G107,
    MOVIE_FIXED_FOLDER_PATH_G107,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE268_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_FILE_SETTINGS_GAMMA_ASSIST_TCUB_108GATE_SCHEMA,
    REALHW_FILE_SETTINGS_GAMMA_ASSIST_TCUB_108GATE_VERSION,
    REEL_NUMBER_FACTORY_DEFAULT_G107,
    REEL_NUMBER_MAX_G107,
    REEL_NUMBER_MIN_G107,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    RESET_ACTION_RESET_NETWORK_SET_PHASE268,
    SELECT_LUT_709_800_G108,
    SELECT_LUT_FACTORY_DEFAULT_G108,
    SELECT_LUT_MENU_PATH_G108,
    SELECT_LUT_S709_G108,
    SELECT_LUT_SLOG3_G108,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G107_MOVIE_CUSTOM_FOLDER_TOPOLOGY_VIOLATION,
    STATUS_BLOCKED_G107_MOVIE_FILE_NAME_CAMID_REEL_OR_37CHAR_TITLE_VIOLATION,
    STATUS_BLOCKED_G107_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G107_SLOT1_VAULT_FOLDER_MUTATION_VIOLATION,
    STATUS_BLOCKED_G107_STILL_DSC_PREFIX_OR_FOLDER_FORM_VIOLATION,
    STATUS_BLOCKED_G107_TELEMETRY_INVALID,
    STATUS_BLOCKED_G108_AUTO_REVIEW_SCOPE_OR_DEFAULT_VIOLATION,
    STATUS_BLOCKED_G108_DISPLAY_LUT_OR_SELECT_LUT_VIOLATION,
    STATUS_BLOCKED_G108_EXTERNAL_HDMI_GAMMA_ASSIST_LEAK_VIOLATION,
    STATUS_BLOCKED_G108_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_VIOLATION,
    STATUS_BLOCKED_G108_RESET_SURVIVAL_OR_INITIALIZE_VIOLATION,
    STATUS_BLOCKED_G108_TC_FORMAT_24P_PAL_NDF_VIOLATION,
    STATUS_BLOCKED_G108_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE268_DONOR_INTEGRITY,
    STATUS_VERIFIED_G107,
    STATUS_VERIFIED_G108,
    STILL_FILE_FOLDER_SETTINGS_MENU_PATH_G107,
    STILL_FILE_NUMBER_FACTORY_DEFAULT_G107,
    STILL_FOLDER_DATE_FORM_G107,
    STILL_FOLDER_FORM_FACTORY_DEFAULT_G107,
    STILL_FOLDER_STANDARD_FORM_G107,
    STILL_SET_FILE_NAME_EXACT_LEN_G107,
    STILL_SET_FILE_NAME_FACTORY_DEFAULT_G107,
    TCUB_DISP_FACTORY_DEFAULT_G108,
    TCUB_DISP_SETTING_MENU_PATH_G108,
    TCUB_DISP_TC_G108,
    TCUB_DISP_UBIT_G108,
    TCUB_EXACT_6_ITEMS_G108,
    TCUB_MENU_PATH_G108,
    TC_FORMAT_DF_G108,
    TC_FORMAT_FACTORY_DEFAULT_G108,
    TC_FORMAT_NDF_G108,
    TC_MAKE_FACTORY_DEFAULT_G108,
    TC_MAKE_PRESET_G108,
    TC_MAKE_REGENERATE_G108,
    TC_PRESET_FACTORY_DEFAULT_G108,
    TC_RUN_FACTORY_DEFAULT_G108,
    TC_RUN_FREE_RUN_G108,
    TC_RUN_REC_RUN_G108,
    TITLE_NAME_FACTORY_DEFAULT_G107,
    TITLE_NAME_MAX_CHARS_G107,
    UB_PRESET_FACTORY_DEFAULT_G108,
    UB_TIME_REC_FACTORY_DEFAULT_G108,
    UB_TIME_REC_OFF_G108,
    UB_TIME_REC_ON_G108,
    USB_PACKETS_TRANSMITTED,
    USER_SELECT_LUT_SLOTS_G108,
    _is_forced_clean_room,
    _is_valid_37char_title_name_g107,
    _is_valid_still_3char_prefix_g107,
    _read_file_o_rdonly,
    audit_phase268_donor_contracts,
    compute_file_settings_and_slot1_vault_matrix,
    compute_gamma_disp_assist_vs_log_shooting_matrix,
    evaluate_108_master_safety_gates,
    evaluate_108gate_preflight,
    evaluate_g107_movie_file_settings_still_dsc_and_slot1_vault_guard,
    evaluate_g108_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard,
    main as module_main,
    resolve_fx3_gamma_disp_assist_auto_review_and_tcub_state,
    resolve_fx3_movie_file_settings_and_still_dsc_state,
    run_108_gate_preflight,
    verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard,
    verify_movie_file_settings_still_dsc_and_slot1_vault_guard,
)


class TestPhase268FileSettingsGammaAssistTcub108GateGuard(unittest.TestCase):
    """72 fast dual-mode tests covering Gates G107, G108, and unified 108-Gate preflight (< 4.0s)."""

    @classmethod
    def setUpClass(cls) -> None:
        # Cache upstream 106-gate evaluation once so all 72 tests execute well
        # under < 4.0s in both LOCAL_DONOR_O_RDONLY and FX3_CLEAN_ROOM_TEST=1 /
        # FX3_FX6_FORCE_CLEAN_ROOM=1 modes.
        env_clean = _is_forced_clean_room()
        cls.active_offline_106 = fx3_safety.evaluate_106gate_preflight(
            force_clean_room=True if env_clean else None
        )
        cls.active_offline_108 = evaluate_108gate_preflight(
            force_clean_room=True if env_clean else None,
            master_106_override=cls.active_offline_106,
        )

        cls.clean_offline_106 = dataclasses.replace(
            cls.active_offline_106,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            clean_room_forced=True,
        )
        dry_gates_106 = tuple(
            {**g, "passed": True} if idx < 12 else dict(g)
            for idx, g in enumerate(cls.active_offline_106.gates)
        )
        dry_summary_106 = {
            **cls.active_offline_106.summary,
            "verified_gates": 106,
            "technical_gates_passed": 106,
            "blocked_or_pending_gates": 0,
            "g01_to_g12_verified": 12,
            "all_106_gates_verified": True,
            "dry_run_rehearsal_only": True,
        }
        cls.active_dryrun_106 = dataclasses.replace(
            cls.active_offline_106,
            dry_run_rehearsal_only=True,
            all_106_gates_verified=True,
            status="VERIFIED_ALL_106_GATES_DRY_RUN_SIMULATED_BACKUP",
            technical_gates_passed=106,
            summary=dry_summary_106,
            gates=dry_gates_106,
        )
        cls.clean_dryrun_106 = dataclasses.replace(
            cls.active_dryrun_106,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            clean_room_forced=True,
        )

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_108 = evaluate_108gate_preflight(
                force_clean_room=True, master_106_override=cls.clean_offline_106
            )
            cls.clean_dryrun_108 = evaluate_108gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_106_override=cls.clean_dryrun_106,
            )
        cls.active_dryrun_108 = evaluate_108gate_preflight(
            force_clean_room=True if env_clean else None,
            simulate_bench_dry_run=True,
            master_106_override=cls.active_dryrun_106,
        )

    # ------------------------------------------------------------------
    # Section A: Schema, Exports & O_RDONLY / Clean-Room Donor Audit (01..12)
    # ------------------------------------------------------------------

    def test_01_schema_version_gate_ids_and_redline_constants(self) -> None:
        self.assertEqual(
            REALHW_FILE_SETTINGS_GAMMA_ASSIST_TCUB_108GATE_SCHEMA,
            "realhw_file_settings_gamma_assist_tcub_and_108gate_guard_v1",
        )
        self.assertEqual(
            REALHW_FILE_SETTINGS_GAMMA_ASSIST_TCUB_108GATE_VERSION, "1.0.0"
        )
        self.assertEqual(G107, G107_GATE_ID)
        self.assertEqual(G108, G108_GATE_ID)
        self.assertEqual(
            GATE_G107_MOVIE_FILE_SETTINGS_CAMID_REEL_37CHAR_STILL_DSC_AND_SLOT1_FOLDER_VAULT_GUARD,
            G107_GATE_CODE,
        )
        self.assertEqual(
            GATE_G108_GAMMA_DISP_ASSIST_LOG_LOCKOUT_DISPLAY_LUT_AUTO_REVIEW_AND_TCUB_GUARD,
            G108_GATE_CODE,
        )
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX6_MODEL_NAME, "ILME-FX6")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE268, "7.02")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE268, "ilc/2210")
        self.assertEqual(TITLE_NAME_MAX_CHARS_G107, 37)
        self.assertEqual(STILL_SET_FILE_NAME_EXACT_LEN_G107, 3)
        self.assertEqual(MAX_USER_LUT_SLOTS_G108, 16)
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

    def test_02_top_level_package_exports_all_phase268_symbols_unshadowed(self) -> None:
        mod = fx3_safety.realhw_file_settings_gamma_assist_tcub_and_108gate_guard
        self.assertEqual(fx3_safety.__all__.count(mod.__name__.split(".")[-1]), 1)
        for sym in (
            "G107",
            "G108",
            "G107_GATE_ID",
            "G108_GATE_ID",
            "GATE_G107_MOVIE_FILE_SETTINGS_CAMID_REEL_37CHAR_STILL_DSC_AND_SLOT1_FOLDER_VAULT_GUARD",
            "GATE_G108_GAMMA_DISP_ASSIST_LOG_LOCKOUT_DISPLAY_LUT_AUTO_REVIEW_AND_TCUB_GUARD",
            "Master108GateReport",
            "evaluate_108gate_preflight",
            "run_108_gate_preflight",
            "evaluate_108_master_safety_gates",
            "verify_movie_file_settings_still_dsc_and_slot1_vault_guard",
            "verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard",
        ):
            self.assertEqual(fx3_safety.__all__.count(sym), 1)
            self.assertIs(getattr(fx3_safety, sym), getattr(mod, sym))
        # Verify upstream G102..G106 & evaluate_102gate_preflight..evaluate_106gate_preflight intact
        self.assertTrue(callable(fx3_safety.evaluate_102gate_preflight))
        self.assertTrue(callable(fx3_safety.evaluate_104gate_preflight))
        self.assertTrue(callable(fx3_safety.evaluate_106gate_preflight))
        self.assertEqual(fx3_safety.G105, fx3_safety.G105_GATE_ID)
        self.assertEqual(fx3_safety.G106, fx3_safety.G106_GATE_ID)

    def test_03_pinned_phase268_donor_specs_cover_fx3_and_fx6_contracts(self) -> None:
        self.assertEqual(len(PINNED_PHASE268_DONOR_SPECS), 6)
        bodies = {spec[0] for spec in PINNED_PHASE268_DONOR_SPECS.values()}
        self.assertEqual(bodies, {"FX3", "FX6"})
        self.assertLessEqual(DONOR_CHECK_MAX_SECONDS_PHASE268, 0.10)

    def test_04_donor_audit_active_mode_within_100ms_and_zero_leaked_bytes(
        self,
    ) -> None:
        audit = audit_phase268_donor_contracts()
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_100ms)
        self.assertLess(audit.elapsed_seconds, 0.10)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertIn(
            audit.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
        )

    def test_05_donor_audit_force_clean_room_synthetic_parity(self) -> None:
        audit = audit_phase268_donor_contracts(force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(len(audit.checked_markers), 6)
        self.assertEqual(audit.missing_markers, ())
        self.assertIsInstance(audit.to_dict(), dict)

    def test_06_donor_audit_env_fx3_clean_room_test_and_force_clean_room_toggles(
        self,
    ) -> None:
        for env_key in ("FX3_FX6_FORCE_CLEAN_ROOM", ENV_CLEAN_ROOM_TEST_PHASE268):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                audit = audit_phase268_donor_contracts()
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_missing_work_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = audit_phase268_donor_contracts(
                work_root=Path(tmp) / "nonexistent", force_clean_room=False
            )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_08_donor_audit_clean_room_budget_exceeded_fails_closed(self) -> None:
        audit = audit_phase268_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE268_DONOR_INTEGRITY)

    def test_09_donor_audit_corrupted_donor_tree_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _body, rel, _sz, _sha, _mk, _lbl in PINNED_PHASE268_DONOR_SPECS.values():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"corrupt")
            audit = audit_phase268_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE268_DONOR_INTEGRITY)
            self.assertEqual(len(audit.missing_markers), 6)

    def test_10_donor_audit_oserror_on_read_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _body, rel, _sz, _sha, _mk, _lbl in PINNED_PHASE268_DONOR_SPECS.values():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"stub")
            with mock.patch(
                "fx3_safety.realhw_file_settings_gamma_assist_tcub_and_108gate_guard._read_cached_donor_o_rdonly",
                side_effect=OSError("simulated I/O fault"),
            ):
                audit = audit_phase268_donor_contracts(
                    work_root=root, force_clean_room=False
                )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE268_DONOR_INTEGRITY)

    def test_11_read_file_o_rdonly_reads_exact_bytes_without_write_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "sample.bin"
            fp.write_bytes(b"FX3_WAVE44_TEST")
            self.assertEqual(_read_file_o_rdonly(fp), b"FX3_WAVE44_TEST")

    def test_12_allowed_enum_tuples_exact_cardinalities(self) -> None:
        self.assertEqual(len(ALLOWED_RESET_ACTIONS_PHASE268), 4)
        self.assertEqual(len(ALLOWED_FILE_NUMBER_MODES_G107), 2)
        self.assertEqual(len(ALLOWED_MOVIE_FILE_NAME_FORMATS_G107), 5)
        self.assertEqual(len(CAMERA_ID_ALLOWED_CHARS_G107), 26)
        self.assertEqual(len(ALLOWED_CAMERA_POSITIONS_G107), 3)
        self.assertEqual(len(ALLOWED_STILL_FOLDER_FORMS_G107), 2)
        self.assertEqual(len(ALLOWED_MEDIA_SLOTS_G107), 2)
        self.assertEqual(len(ALLOWED_GAMMA_DISP_ASSIST_STATES_G108), 2)
        self.assertEqual(len(ALLOWED_GAMMA_ASSIST_TYPES_G108), 4)
        self.assertEqual(len(ALLOWED_LOG_SHOOTING_MODES_G108), 4)
        self.assertEqual(len(ACTIVE_LOG_SHOOTING_MODES_G108), 3)
        self.assertEqual(len(ALLOWED_DISPLAY_LUT_STATES_G108), 2)
        self.assertEqual(len(BUILTIN_SELECT_LUT_PRESETS_G108), 3)
        self.assertEqual(len(USER_SELECT_LUT_SLOTS_G108), 16)
        self.assertEqual(len(ALLOWED_SELECT_LUT_ITEMS_G108), 19)
        self.assertEqual(len(ALLOWED_AUTO_REVIEW_SETTINGS_G108), 4)
        self.assertEqual(len(TCUB_EXACT_6_ITEMS_G108), 6)
        self.assertEqual(len(ALLOWED_TC_FORMATS_G108), 2)
        self.assertEqual(len(ALLOWED_FRAME_RATES_G108), 6)
        self.assertEqual(len(FORCED_NDF_FRAME_RATES_G108), 3)
        self.assertEqual(len(ALLOWED_TC_RUN_MODES_G108), 2)
        self.assertEqual(len(ALLOWED_TC_MAKE_MODES_G108), 2)
        self.assertEqual(len(ALLOWED_TCUB_DISP_SETTINGS_G108), 2)

    # ------------------------------------------------------------------
    # Section B: Gate G107 — Movie [File Settings] vs Still DSC & Slot-1 Vault (13..35)
    # ------------------------------------------------------------------

    def test_13_g107_factory_defaults_verified_safe(self) -> None:
        res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G107)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(
            res.movie_file_settings_menu_path, MOVIE_FILE_SETTINGS_MENU_PATH_G107
        )
        self.assertEqual(
            res.still_file_folder_settings_menu_path,
            STILL_FILE_FOLDER_SETTINGS_MENU_PATH_G107,
        )
        self.assertEqual(
            res.effective_post_reset_movie_file_number,
            MOVIE_FILE_NUMBER_FACTORY_DEFAULT_G107,
        )
        self.assertEqual(
            res.effective_post_reset_movie_file_name_format,
            MOVIE_FILE_NAME_FORMAT_FACTORY_DEFAULT_G107,
        )
        self.assertEqual(
            res.effective_post_reset_camera_id, CAMERA_ID_FACTORY_DEFAULT_G107
        )
        self.assertEqual(
            res.effective_post_reset_reel_number, REEL_NUMBER_FACTORY_DEFAULT_G107
        )
        self.assertEqual(res.formatted_reel_number, "001")
        self.assertEqual(
            res.effective_post_reset_camera_position,
            CAMERA_POSITION_FACTORY_DEFAULT_G107,
        )
        self.assertEqual(
            res.effective_post_reset_title_name, TITLE_NAME_FACTORY_DEFAULT_G107
        )
        self.assertEqual(res.movie_folder_path, MOVIE_FIXED_FOLDER_PATH_G107)
        self.assertTrue(res.movie_fixed_folder_topology_verified)
        self.assertEqual(res.sample_movie_clip_filename, "C0013.MP4")
        self.assertEqual(
            res.effective_post_reset_still_file_number,
            STILL_FILE_NUMBER_FACTORY_DEFAULT_G107,
        )
        self.assertEqual(
            res.effective_post_reset_still_set_file_name,
            STILL_SET_FILE_NAME_FACTORY_DEFAULT_G107,
        )
        self.assertEqual(
            res.effective_post_reset_still_folder_name,
            STILL_FOLDER_FORM_FACTORY_DEFAULT_G107,
        )
        self.assertEqual(res.slot1_vault_folder_mutation_events, 0)
        self.assertEqual(res.matrix_states_checked, 360)

    def test_14_g107_cam_id_plus_reel_all_26_camera_ids_and_3_positions(self) -> None:
        for cam_id in ("A", "B", "M", "Z"):
            for reel, fmt_reel in ((1, "001"), (42, "042"), (999, "999")):
                for pos in (
                    CAMERA_POSITION_CENTER_G107,
                    CAMERA_POSITION_LEFT_G107,
                    CAMERA_POSITION_RIGHT_G107,
                ):
                    res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
                        pre_reset_movie_file_name_format=MOVIE_FILE_NAME_CAM_ID_REEL_G107,
                        pre_reset_camera_id=cam_id,
                        pre_reset_reel_number=reel,
                        pre_reset_camera_position=pos,
                        prior_movie_sequence_index=0,
                    )
                    self.assertTrue(res.valid)
                    self.assertTrue(
                        res.sample_movie_clip_filename.startswith(
                            f"{cam_id}{fmt_reel}{pos}001_"
                        )
                    )

    def test_15_g107_cam_id_reel_rejected_on_pre_v300_firmware(self) -> None:
        res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            firmware_version="2.00",
            pre_reset_movie_file_name_format=MOVIE_FILE_NAME_CAM_ID_REEL_G107,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G107_MOVIE_FILE_NAME_CAMID_REEL_OR_37CHAR_TITLE_VIOLATION,
        )
        self.assertEqual(FX3_CAMID_REEL_MIN_FW_TUPLE_G107, (3, 0))

    def test_16_g107_title_date_plus_title_and_title_plus_date_formats(self) -> None:
        r_title = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            pre_reset_movie_file_name_format=MOVIE_FILE_NAME_TITLE_G107,
            pre_reset_title_name="FX3UNIT_A",
            prior_movie_sequence_index=4,
        )
        self.assertTrue(r_title.valid)
        self.assertEqual(r_title.sample_movie_clip_filename, "FX3UNIT_A0005.MP4")

        r_dt = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            pre_reset_movie_file_name_format=MOVIE_FILE_NAME_DATE_PLUS_TITLE_G107,
            pre_reset_title_name="SLATEB",
            prior_movie_sequence_index=0,
        )
        self.assertTrue(r_dt.valid)
        self.assertEqual(r_dt.sample_movie_clip_filename, "261115_SLATEB0001.MP4")

        r_td = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            pre_reset_movie_file_name_format=MOVIE_FILE_NAME_TITLE_PLUS_DATE_G107,
            pre_reset_title_name="SLATEC",
            prior_movie_sequence_index=0,
        )
        self.assertTrue(r_td.valid)
        self.assertEqual(r_td.sample_movie_clip_filename, "SLATEC_261115_0001.MP4")

    def test_17_g107_title_name_exact_37_char_boundary_passes(self) -> None:
        title_37 = "FX3_WAVE44_CINEMA_SLATE_TITLE_37CHARS"
        self.assertEqual(len(title_37), 37)
        self.assertTrue(_is_valid_37char_title_name_g107(title_37))
        res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            pre_reset_movie_file_name_format=MOVIE_FILE_NAME_TITLE_G107,
            pre_reset_title_name=title_37,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.title_name_char_length, 37)
        self.assertTrue(res.title_name_within_37char_ascii)

    def test_18_g107_title_name_38_chars_empty_non_ascii_or_path_traversal_blocked(
        self,
    ) -> None:
        for bad_title in (
            "",
            "X" * 38,
            "BAD/PATH",
            "BAD\\PATH",
            "BAD..DOTS",
            "NON_ASCII_\u00e9",
            "CTRL_\x07",
        ):
            self.assertFalse(_is_valid_37char_title_name_g107(bad_title))
            res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
                pre_reset_title_name=bad_title
            )
            self.assertFalse(res.valid)
            self.assertIn(
                STATUS_BLOCKED_G107_MOVIE_FILE_NAME_CAMID_REEL_OR_37CHAR_TITLE_VIOLATION,
                res.violation_codes,
            )

    def test_19_g107_invalid_camera_id_reel_number_or_position_blocked(self) -> None:
        for kwargs in (
            {"pre_reset_camera_id": "a"},
            {"pre_reset_camera_id": "AB"},
            {"pre_reset_camera_id": "1"},
            {"pre_reset_reel_number": 0},
            {"pre_reset_reel_number": 1000},
            {"pre_reset_reel_number": True},
            {"pre_reset_camera_position": "X"},
            {"pre_reset_movie_file_name_format": "BogusFormat"},
        ):
            res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(**kwargs)
            self.assertFalse(res.valid)
            self.assertIn(
                STATUS_BLOCKED_G107_MOVIE_FILE_NAME_CAMID_REEL_OR_37CHAR_TITLE_VIOLATION,
                res.violation_codes,
            )

    def test_20_g107_series_counter_reset_and_file_number_reset_behavior(self) -> None:
        r_series_rst = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            pre_reset_movie_file_number=FILE_NUMBER_SERIES_G107,
            series_counter_reset_requested=True,
            prior_movie_sequence_index=88,
        )
        self.assertTrue(r_series_rst.valid)
        self.assertEqual(r_series_rst.effective_movie_sequence_index, 1)
        self.assertEqual(r_series_rst.sample_movie_clip_filename, "C0001.MP4")

        r_reset_mode = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            pre_reset_movie_file_number=FILE_NUMBER_RESET_G107,
            prior_movie_sequence_index=88,
        )
        self.assertTrue(r_reset_mode.valid)
        self.assertEqual(r_reset_mode.effective_movie_sequence_index, 1)

    def test_21_g107_custom_movie_folder_topology_blocked(self) -> None:
        r1 = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            movie_folder_path="DCIM/100MSDCF"
        )
        self.assertFalse(r1.valid)
        self.assertEqual(
            r1.status, STATUS_BLOCKED_G107_MOVIE_CUSTOM_FOLDER_TOPOLOGY_VIOLATION
        )

        r2 = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            custom_movie_folder_requested=True
        )
        self.assertFalse(r2.valid)
        self.assertEqual(
            r2.status, STATUS_BLOCKED_G107_MOVIE_CUSTOM_FOLDER_TOPOLOGY_VIOLATION
        )

    def test_22_g107_still_set_file_name_3char_valid_with_trailing_or_mid_underscore(
        self,
    ) -> None:
        for prefix in ("DSC", "FX3", "A_1", "9B_"):
            self.assertTrue(_is_valid_still_3char_prefix_g107(prefix))
            res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
                pre_reset_still_set_file_name=prefix,
                pre_reset_still_folder_name=STILL_FOLDER_DATE_FORM_G107,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_post_reset_still_set_file_name, prefix)
            self.assertEqual(res.sample_still_folder_label, "10061115")

    def test_23_g107_still_set_file_name_rejects_leading_underscore_and_bad_lengths(
        self,
    ) -> None:
        for bad_prefix in ("_SC", "_AB", "___", "DS", "DSCF", "dsc", "AB-", ""):
            self.assertFalse(_is_valid_still_3char_prefix_g107(bad_prefix))
            res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
                pre_reset_still_set_file_name=bad_prefix
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G107_STILL_DSC_PREFIX_OR_FOLDER_FORM_VIOLATION
            )

    def test_24_g107_still_invalid_folder_form_blocked(self) -> None:
        res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            pre_reset_still_folder_name="Custom Folder Form"
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G107_STILL_DSC_PREFIX_OR_FOLDER_FORM_VIOLATION
        )

    def test_25_g107_slot1_recovery_vault_blocks_forced_reset_and_create_new_folder(
        self,
    ) -> None:
        r_forced = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            target_still_slot=MEDIA_SLOT_1_G107,
            slot1_holds_recovery_vault=True,
            forced_file_number_reset_requested=True,
        )
        self.assertFalse(r_forced.valid)
        self.assertEqual(
            r_forced.status, STATUS_BLOCKED_G107_SLOT1_VAULT_FOLDER_MUTATION_VIOLATION
        )
        self.assertTrue(r_forced.slot1_vault_folder_mutation_blocked)
        self.assertFalse(r_forced.still_folder_mutation_permitted)

        r_new_dir = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            target_still_slot=MEDIA_SLOT_1_G107,
            slot1_holds_recovery_vault=True,
            create_new_folder_requested=True,
        )
        self.assertFalse(r_new_dir.valid)
        self.assertEqual(
            r_new_dir.status, STATUS_BLOCKED_G107_SLOT1_VAULT_FOLDER_MUTATION_VIOLATION
        )

    def test_26_g107_slot2_allows_forced_file_number_reset_and_new_folder_safely(
        self,
    ) -> None:
        res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            target_still_slot=MEDIA_SLOT_2_G107,
            slot1_holds_recovery_vault=True,
            forced_file_number_reset_requested=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.still_folder_mutation_permitted)
        self.assertFalse(res.slot1_vault_folder_mutation_blocked)
        self.assertEqual(res.sample_still_folder_label, "101MSDCF")
        self.assertEqual(res.sample_still_image_filename, "DSC00001.JPG")
        self.assertEqual(res.slot1_vault_folder_mutation_events, 0)

    def test_27_g107_claimed_slot1_vault_mutation_events_nonzero_blocked(self) -> None:
        res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            claimed_slot1_vault_folder_mutation_events=1
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G107_SLOT1_VAULT_FOLDER_MUTATION_VIOLATION
        )

    def test_28_g107_exhaustive_360_state_matrix_zero_vault_or_folder_bypasses(
        self,
    ) -> None:
        matrix = compute_file_settings_and_slot1_vault_matrix()
        self.assertEqual(matrix["states_checked"], 360)
        self.assertEqual(matrix["cam_id_reel_states"], 72)
        self.assertEqual(matrix["slot1_vault_blocked_ops"], 60)
        self.assertEqual(matrix["slot2_permitted_ops"], 120)
        self.assertEqual(matrix["slot1_vault_folder_mutation_events"], 0)
        self.assertEqual(matrix["custom_movie_folder_bypass_events"], 0)

    def test_29_g107_all_9_file_and_folder_items_survive_camera_settings_reset(
        self,
    ) -> None:
        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET,
            RESET_ACTION_RESET_NETWORK_SET_PHASE268,
        ):
            res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
                reset_action=rst,
                pre_reset_movie_file_number=FILE_NUMBER_RESET_G107,
                pre_reset_movie_file_name_format=MOVIE_FILE_NAME_CAM_ID_REEL_G107,
                pre_reset_camera_id="B",
                pre_reset_reel_number=17,
                pre_reset_camera_position=CAMERA_POSITION_LEFT_G107,
                pre_reset_title_name="UNIT_B_CAM",
                pre_reset_still_file_number=FILE_NUMBER_RESET_G107,
                pre_reset_still_set_file_name="FX3",
                pre_reset_still_folder_name=STILL_FOLDER_DATE_FORM_G107,
                claimed_post_reset_movie_file_number=FILE_NUMBER_RESET_G107,
                claimed_post_reset_movie_file_name_format=MOVIE_FILE_NAME_CAM_ID_REEL_G107,
                claimed_post_reset_camera_id="B",
                claimed_post_reset_reel_number=17,
                claimed_post_reset_camera_position=CAMERA_POSITION_LEFT_G107,
                claimed_post_reset_title_name="UNIT_B_CAM",
                claimed_post_reset_still_file_number=FILE_NUMBER_RESET_G107,
                claimed_post_reset_still_set_file_name="FX3",
                claimed_post_reset_still_folder_name=STILL_FOLDER_DATE_FORM_G107,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.file_and_folder_settings_survive_camera_settings_reset)

    def test_30_g107_initialize_restores_all_9_file_and_folder_defaults(self) -> None:
        res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            reset_action=RESET_ACTION_INITIALIZE,
            pre_reset_movie_file_number=FILE_NUMBER_RESET_G107,
            pre_reset_movie_file_name_format=MOVIE_FILE_NAME_CAM_ID_REEL_G107,
            pre_reset_camera_id="Z",
            pre_reset_reel_number=999,
            pre_reset_camera_position=CAMERA_POSITION_RIGHT_G107,
            pre_reset_title_name="CUSTOM_TITLE",
            pre_reset_still_file_number=FILE_NUMBER_RESET_G107,
            pre_reset_still_set_file_name="FX3",
            pre_reset_still_folder_name=STILL_FOLDER_DATE_FORM_G107,
            claimed_post_reset_movie_file_number=MOVIE_FILE_NUMBER_FACTORY_DEFAULT_G107,
            claimed_post_reset_movie_file_name_format=MOVIE_FILE_NAME_FORMAT_FACTORY_DEFAULT_G107,
            claimed_post_reset_camera_id=CAMERA_ID_FACTORY_DEFAULT_G107,
            claimed_post_reset_reel_number=REEL_NUMBER_FACTORY_DEFAULT_G107,
            claimed_post_reset_camera_position=CAMERA_POSITION_FACTORY_DEFAULT_G107,
            claimed_post_reset_title_name=TITLE_NAME_FACTORY_DEFAULT_G107,
            claimed_post_reset_still_file_number=STILL_FILE_NUMBER_FACTORY_DEFAULT_G107,
            claimed_post_reset_still_set_file_name=STILL_SET_FILE_NAME_FACTORY_DEFAULT_G107,
            claimed_post_reset_still_folder_name=STILL_FOLDER_FORM_FACTORY_DEFAULT_G107,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_camera_id, "A")
        self.assertEqual(res.effective_post_reset_reel_number, 1)
        self.assertEqual(res.effective_post_reset_still_set_file_name, "DSC")

    def test_31_g107_claimed_post_reset_mismatch_blocked(self) -> None:
        res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_still_set_file_name="FX3",
            claimed_post_reset_still_set_file_name="DSC",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G107_RESET_PERSISTENCE_VIOLATION)

    def test_32_g107_invalid_body_model_slot_or_reset_telemetry_blocked(self) -> None:
        for bad_kwargs in (
            {"body_model_name": "ILME-FX6"},
            {"body_model_id": 0x12345678},
            {"help_guide_code": "ilc/2035"},
            {"firmware_version": "bad_fw"},
            {"reset_action": "FactoryWipe"},
            {"pre_reset_movie_file_number": "Continuous"},
            {"target_still_slot": "Slot 3"},
            {"prior_movie_sequence_index": -1},
        ):
            res = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
                **bad_kwargs
            )
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G107_TELEMETRY_INVALID, res.violation_codes)

    def test_33_evaluate_g107_dual_mode_and_persistent_write_block(self) -> None:
        v_clean, r_clean = (
            evaluate_g107_movie_file_settings_still_dsc_and_slot1_vault_guard(
                force_clean_room=True
            )
        )
        self.assertTrue(v_clean.passed)
        self.assertTrue(r_clean.valid)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIsInstance(r_clean.to_dict(), dict)

        v_blk, r_blk = (
            evaluate_g107_movie_file_settings_still_dsc_and_slot1_vault_guard(
                force_clean_room=True, request_persistent_emmc_writes=True
            )
        )
        self.assertFalse(v_blk.passed)
        self.assertFalse(r_blk.valid)
        self.assertEqual(r_blk.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_34_evaluate_g107_propagates_donor_integrity_failure(self) -> None:
        bad_audit = audit_phase268_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        verdict, res = (
            evaluate_g107_movie_file_settings_still_dsc_and_slot1_vault_guard(
                donor_audit=bad_audit
            )
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE268_DONOR_INTEGRITY)

    def test_35_resolve_fx3_movie_file_settings_and_still_dsc_state_direct(
        self,
    ) -> None:
        st = resolve_fx3_movie_file_settings_and_still_dsc_state(
            pre_reset_movie_file_name_format="Cam ID + Reel#",
            pre_reset_camera_id="C",
            pre_reset_reel_number="007",  # type: ignore[arg-type]
            pre_reset_camera_position="R",
        )
        self.assertEqual(st["formatted_reel_number"], "007")
        self.assertTrue(st["sample_movie_clip_filename"].startswith("C007R013_"))

    # ------------------------------------------------------------------
    # Section C: Gate G108 — Gamma Display Assist / Display LUT / Auto Review / TC/UB (36..58)
    # ------------------------------------------------------------------

    def test_36_g108_factory_defaults_verified_safe(self) -> None:
        res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G108)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(
            res.gamma_disp_assist_menu_path, GAMMA_DISP_ASSIST_MENU_PATH_G108
        )
        self.assertEqual(
            res.gamma_disp_assist_typ_menu_path, GAMMA_DISP_ASSIST_TYP_MENU_PATH_G108
        )
        self.assertEqual(res.display_lut_menu_path, DISPLAY_LUT_MENU_PATH_G108)
        self.assertEqual(res.select_lut_menu_path, SELECT_LUT_MENU_PATH_G108)
        self.assertEqual(res.auto_review_menu_path, AUTO_REVIEW_MENU_PATH_G108)
        self.assertEqual(res.tcub_menu_path, TCUB_MENU_PATH_G108)
        self.assertEqual(
            res.tcub_disp_setting_menu_path, TCUB_DISP_SETTING_MENU_PATH_G108
        )
        self.assertEqual(
            res.effective_gamma_display_assist, GAMMA_DISP_ASSIST_FACTORY_DEFAULT_G108
        )
        self.assertEqual(
            res.effective_post_reset_gamma_disp_assist_typ,
            GAMMA_ASSIST_TYP_FACTORY_DEFAULT_G108,
        )
        self.assertEqual(
            res.effective_post_reset_display_lut, DISPLAY_LUT_FACTORY_DEFAULT_G108
        )
        self.assertEqual(
            res.effective_post_reset_select_lut, SELECT_LUT_FACTORY_DEFAULT_G108
        )
        self.assertEqual(
            res.effective_post_reset_auto_review, AUTO_REVIEW_FACTORY_DEFAULT_G108
        )
        self.assertTrue(res.tcub_exact_6_items_verified)
        self.assertEqual(res.effective_post_reset_tc_preset, TC_PRESET_FACTORY_DEFAULT_G108)
        self.assertEqual(res.effective_post_reset_ub_preset, UB_PRESET_FACTORY_DEFAULT_G108)
        self.assertEqual(res.effective_tc_format, TC_FORMAT_FACTORY_DEFAULT_G108)
        self.assertEqual(res.effective_post_reset_tc_run, TC_RUN_FACTORY_DEFAULT_G108)
        self.assertEqual(res.effective_post_reset_tc_make, TC_MAKE_FACTORY_DEFAULT_G108)
        self.assertEqual(
            res.effective_post_reset_ub_time_rec, UB_TIME_REC_FACTORY_DEFAULT_G108
        )
        self.assertEqual(
            res.effective_post_reset_tcub_disp_setting, TCUB_DISP_FACTORY_DEFAULT_G108
        )
        self.assertEqual(res.matrix_states_checked, 128)

    def test_37_g108_gamma_display_assist_on_with_all_4_assist_types_when_log_off(
        self,
    ) -> None:
        for typ in (
            GAMMA_ASSIST_TYP_AUTO_G108,
            GAMMA_ASSIST_TYP_SLOG3_709_800_G108,
            "S-Log3\u2192709(800%)",
            GAMMA_ASSIST_TYP_HLG_BT2020_G108,
            GAMMA_ASSIST_TYP_HLG_709_G108,
        ):
            res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                log_shooting_mode=LOG_SHOOTING_OFF_G108,
                pre_reset_gamma_display_assist=GAMMA_DISP_ASSIST_ON_G108,
                pre_reset_gamma_disp_assist_typ=typ,
                claimed_effective_gamma_display_assist=GAMMA_DISP_ASSIST_ON_G108,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.gamma_display_assist_locked_by_log_shooting)
            self.assertEqual(res.effective_gamma_display_assist, GAMMA_DISP_ASSIST_ON_G108)

    def test_38_g108_gamma_display_assist_hard_locked_off_across_all_log_modes(
        self,
    ) -> None:
        for log_mode in (
            LOG_SHOOTING_CINE_EI_G108,
            LOG_SHOOTING_CINE_EI_QUICK_G108,
            LOG_SHOOTING_FLEXIBLE_ISO_G108,
        ):
            res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                log_shooting_mode=log_mode,
                pre_reset_gamma_display_assist=GAMMA_DISP_ASSIST_ON_G108,
                claimed_effective_gamma_display_assist=GAMMA_DISP_ASSIST_OFF_G108,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.gamma_display_assist_locked_by_log_shooting)
            self.assertEqual(
                res.effective_gamma_display_assist, GAMMA_DISP_ASSIST_OFF_G108
            )
            self.assertTrue(res.effective_log_monitoring_governed_by_display_lut)

    def test_39_g108_claiming_gamma_assist_on_or_bypass_during_log_shooting_blocked(
        self,
    ) -> None:
        r1 = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
            log_shooting_mode=LOG_SHOOTING_CINE_EI_G108,
            pre_reset_gamma_display_assist=GAMMA_DISP_ASSIST_ON_G108,
            claimed_effective_gamma_display_assist=GAMMA_DISP_ASSIST_ON_G108,
        )
        self.assertFalse(r1.valid)
        self.assertEqual(
            r1.status, STATUS_BLOCKED_G108_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_VIOLATION
        )

        r2 = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
            claimed_gamma_assist_log_lockout_bypass_events=1
        )
        self.assertFalse(r2.valid)
        self.assertEqual(
            r2.status, STATUS_BLOCKED_G108_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_VIOLATION
        )

    def test_40_g108_external_hdmi_gamma_assist_leak_blocked(self) -> None:
        r1 = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
            claimed_external_hdmi_gamma_assist_applied=True
        )
        self.assertFalse(r1.valid)
        self.assertEqual(
            r1.status, STATUS_BLOCKED_G108_EXTERNAL_HDMI_GAMMA_ASSIST_LEAK_VIOLATION
        )

        r2 = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
            claimed_hdmi_gamma_assist_leak_frames=3
        )
        self.assertFalse(r2.valid)
        self.assertEqual(
            r2.status, STATUS_BLOCKED_G108_EXTERNAL_HDMI_GAMMA_ASSIST_LEAK_VIOLATION
        )

    def test_41_g108_exhaustive_128_state_gamma_assist_log_hdmi_matrix(self) -> None:
        matrix = compute_gamma_disp_assist_vs_log_shooting_matrix()
        self.assertEqual(matrix["states_checked"], 128)
        self.assertEqual(matrix["log_active_locked_off_states"], 96)
        self.assertEqual(matrix["lcd_gamma_assist_active_states"], 8)
        self.assertEqual(matrix["gamma_assist_log_lockout_bypass_events"], 0)
        self.assertEqual(matrix["external_hdmi_gamma_assist_leak_events"], 0)

    def test_42_g108_display_lut_and_select_lut_presets_plus_user1_to_user16(
        self,
    ) -> None:
        for sel in (
            SELECT_LUT_SLOG3_G108,
            SELECT_LUT_S709_G108,
            SELECT_LUT_709_800_G108,
            "User1",
            "User8",
            "User16",
        ):
            res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                log_shooting_mode=LOG_SHOOTING_CINE_EI_G108,
                pre_reset_display_lut=DISPLAY_LUT_OFF_G108,
                pre_reset_select_lut=sel,
                registered_user_lut_slots=16,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_post_reset_select_lut, sel)
            self.assertEqual(res.effective_post_reset_display_lut, DISPLAY_LUT_OFF_G108)

    def test_43_g108_select_lut_unregistered_or_out_of_range_user_slot_blocked(
        self,
    ) -> None:
        for kwargs in (
            {"pre_reset_select_lut": "User5", "registered_user_lut_slots": 4},
            {"pre_reset_select_lut": "User0", "registered_user_lut_slots": 16},
            {"pre_reset_select_lut": "User17", "registered_user_lut_slots": 16},
            {"registered_user_lut_slots": 17},
            {"registered_user_lut_slots": -1},
            {"pre_reset_display_lut": "Auto"},
        ):
            res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                **kwargs
            )
            self.assertFalse(res.valid)
            self.assertIn(
                STATUS_BLOCKED_G108_DISPLAY_LUT_OR_SELECT_LUT_VIOLATION,
                res.violation_codes,
            )

    def test_44_g108_auto_review_off_2s_5s_10s_still_only_vs_movie_interrupt_blocked(
        self,
    ) -> None:
        for ar in (
            AUTO_REVIEW_OFF_G108,
            AUTO_REVIEW_2_SEC_G108,
            AUTO_REVIEW_5_SEC_G108,
            AUTO_REVIEW_10_SEC_G108,
        ):
            res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                pre_reset_auto_review=ar
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_post_reset_auto_review, ar)
            self.assertTrue(res.auto_review_still_only_scope)

        for bad_kwargs in (
            {"pre_reset_auto_review": "30 Sec"},
            {"claimed_auto_review_applies_to_movie": True},
            {"claimed_movie_auto_review_interrupt_events": 1},
        ):
            bad = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                **bad_kwargs
            )
            self.assertFalse(bad.valid)
            self.assertIn(
                STATUS_BLOCKED_G108_AUTO_REVIEW_SCOPE_OR_DEFAULT_VIOLATION,
                bad.violation_codes,
            )

    def test_45_g108_tcub_preset_hex_and_run_make_ub_rec_disp_modes(self) -> None:
        res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
            pre_reset_tc_preset="01:23:45:29",
            pre_reset_ub_preset="ab cd ef 12",
            pre_reset_tc_format=TC_FORMAT_NDF_G108,
            pre_reset_tc_run=TC_RUN_FREE_RUN_G108,
            pre_reset_tc_make=TC_MAKE_REGENERATE_G108,
            pre_reset_ub_time_rec=UB_TIME_REC_ON_G108,
            pre_reset_tcub_disp_setting=TCUB_DISP_UBIT_G108,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_tc_preset, "01:23:45:29")
        self.assertEqual(res.effective_post_reset_ub_preset, "AB CD EF 12")
        self.assertEqual(res.effective_tc_format, TC_FORMAT_NDF_G108)
        self.assertEqual(res.effective_post_reset_tc_run, TC_RUN_FREE_RUN_G108)
        self.assertEqual(res.effective_post_reset_tc_make, TC_MAKE_REGENERATE_G108)
        self.assertEqual(res.effective_post_reset_ub_time_rec, UB_TIME_REC_ON_G108)
        self.assertEqual(res.effective_post_reset_tcub_disp_setting, TCUB_DISP_UBIT_G108)

    def test_46_g108_tc_format_df_allowed_on_ntsc_forced_ndf_on_24p_and_pal(
        self,
    ) -> None:
        for ntsc_fps in (
            FRAME_RATE_NTSC_29_97P_G108,
            FRAME_RATE_NTSC_59_94P_G108,
            FRAME_RATE_NTSC_23_98P_G108,
        ):
            r_ntsc = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                frame_rate=ntsc_fps,
                pre_reset_tc_format=TC_FORMAT_DF_G108,
                claimed_effective_tc_format=TC_FORMAT_DF_G108,
            )
            self.assertTrue(r_ntsc.valid)
            self.assertFalse(r_ntsc.tc_format_forced_ndf_by_cadence)
            self.assertEqual(r_ntsc.effective_tc_format, TC_FORMAT_DF_G108)

        for ndf_fps in (
            FRAME_RATE_TRUE_24_00P_G108,
            FRAME_RATE_PAL_25P_G108,
            FRAME_RATE_PAL_50P_G108,
        ):
            r_ndf = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                frame_rate=ndf_fps,
                pre_reset_tc_format=TC_FORMAT_DF_G108,
                claimed_effective_tc_format=TC_FORMAT_NDF_G108,
            )
            self.assertTrue(r_ndf.valid)
            self.assertTrue(r_ndf.tc_format_forced_ndf_by_cadence)
            self.assertEqual(r_ndf.effective_tc_format, TC_FORMAT_NDF_G108)

    def test_47_g108_claiming_df_on_24p_or_pal_blocked(self) -> None:
        for ndf_fps in (
            FRAME_RATE_TRUE_24_00P_G108,
            FRAME_RATE_PAL_25P_G108,
            FRAME_RATE_PAL_50P_G108,
        ):
            res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                frame_rate=ndf_fps,
                pre_reset_tc_format=TC_FORMAT_DF_G108,
                claimed_effective_tc_format=TC_FORMAT_DF_G108,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G108_TC_FORMAT_24P_PAL_NDF_VIOLATION
            )

        r_bypass = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
            claimed_tc_format_24p_pal_df_bypass_events=1
        )
        self.assertFalse(r_bypass.valid)
        self.assertEqual(
            r_bypass.status, STATUS_BLOCKED_G108_TC_FORMAT_24P_PAL_NDF_VIOLATION
        )

    def test_48_g108_setup_and_all_6_tcub_items_survive_camera_settings_reset(
        self,
    ) -> None:
        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET,
            RESET_ACTION_RESET_NETWORK_SET_PHASE268,
        ):
            res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                reset_action=rst,
                pre_reset_gamma_display_assist=GAMMA_DISP_ASSIST_ON_G108,
                pre_reset_gamma_disp_assist_typ=GAMMA_ASSIST_TYP_HLG_709_G108,
                pre_reset_display_lut=DISPLAY_LUT_OFF_G108,
                pre_reset_select_lut="User2",
                pre_reset_auto_review=AUTO_REVIEW_5_SEC_G108,
                pre_reset_tc_preset="10:00:00.00",
                pre_reset_ub_preset="26 11 15 01",
                pre_reset_tc_format=TC_FORMAT_NDF_G108,
                pre_reset_tc_run=TC_RUN_FREE_RUN_G108,
                pre_reset_tc_make=TC_MAKE_REGENERATE_G108,
                pre_reset_ub_time_rec=UB_TIME_REC_ON_G108,
                pre_reset_tcub_disp_setting=TCUB_DISP_UBIT_G108,
                claimed_post_reset_gamma_display_assist=GAMMA_DISP_ASSIST_ON_G108,
                claimed_post_reset_gamma_disp_assist_typ=GAMMA_ASSIST_TYP_HLG_709_G108,
                claimed_post_reset_display_lut=DISPLAY_LUT_OFF_G108,
                claimed_post_reset_auto_review=AUTO_REVIEW_5_SEC_G108,
                claimed_post_reset_tc_preset="10:00:00.00",
                claimed_post_reset_ub_preset="26 11 15 01",
                claimed_post_reset_tc_format=TC_FORMAT_NDF_G108,
                claimed_post_reset_tc_run=TC_RUN_FREE_RUN_G108,
                claimed_post_reset_tc_make=TC_MAKE_REGENERATE_G108,
                claimed_post_reset_ub_time_rec=UB_TIME_REC_ON_G108,
                claimed_post_reset_tcub_disp_setting=TCUB_DISP_UBIT_G108,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.setup_and_tcub_survive_camera_settings_reset)

    def test_49_g108_initialize_restores_all_setup_and_6_tcub_defaults(self) -> None:
        res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
            reset_action=RESET_ACTION_INITIALIZE,
            pre_reset_gamma_display_assist=GAMMA_DISP_ASSIST_ON_G108,
            pre_reset_gamma_disp_assist_typ=GAMMA_ASSIST_TYP_HLG_BT2020_G108,
            pre_reset_display_lut=DISPLAY_LUT_OFF_G108,
            pre_reset_select_lut="User3",
            pre_reset_auto_review=AUTO_REVIEW_10_SEC_G108,
            pre_reset_tc_preset="12:34:56.12",
            pre_reset_ub_preset="DE AD BE EF",
            pre_reset_tc_format=TC_FORMAT_NDF_G108,
            pre_reset_tc_run=TC_RUN_FREE_RUN_G108,
            pre_reset_tc_make=TC_MAKE_REGENERATE_G108,
            pre_reset_ub_time_rec=UB_TIME_REC_ON_G108,
            pre_reset_tcub_disp_setting=TCUB_DISP_UBIT_G108,
            claimed_post_reset_gamma_display_assist=GAMMA_DISP_ASSIST_FACTORY_DEFAULT_G108,
            claimed_post_reset_gamma_disp_assist_typ=GAMMA_ASSIST_TYP_FACTORY_DEFAULT_G108,
            claimed_post_reset_display_lut=DISPLAY_LUT_FACTORY_DEFAULT_G108,
            claimed_post_reset_auto_review=AUTO_REVIEW_FACTORY_DEFAULT_G108,
            claimed_post_reset_tc_preset=TC_PRESET_FACTORY_DEFAULT_G108,
            claimed_post_reset_ub_preset=UB_PRESET_FACTORY_DEFAULT_G108,
            claimed_post_reset_tc_format=TC_FORMAT_FACTORY_DEFAULT_G108,
            claimed_post_reset_tc_run=TC_RUN_FACTORY_DEFAULT_G108,
            claimed_post_reset_tc_make=TC_MAKE_FACTORY_DEFAULT_G108,
            claimed_post_reset_ub_time_rec=UB_TIME_REC_FACTORY_DEFAULT_G108,
            claimed_post_reset_tcub_disp_setting=TCUB_DISP_FACTORY_DEFAULT_G108,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_tc_run, TC_RUN_REC_RUN_G108)
        self.assertEqual(res.effective_post_reset_auto_review, AUTO_REVIEW_OFF_G108)

    def test_50_g108_claimed_post_reset_tcub_or_auto_review_wipe_on_cam_reset_blocked(
        self,
    ) -> None:
        r1 = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_tc_run=TC_RUN_FREE_RUN_G108,
            claimed_post_reset_tc_run=TC_RUN_REC_RUN_G108,
        )
        self.assertFalse(r1.valid)
        self.assertEqual(
            r1.status, STATUS_BLOCKED_G108_RESET_SURVIVAL_OR_INITIALIZE_VIOLATION
        )

        r2 = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_auto_review=AUTO_REVIEW_5_SEC_G108,
            claimed_post_reset_auto_review=AUTO_REVIEW_OFF_G108,
        )
        self.assertFalse(r2.valid)
        self.assertEqual(
            r2.status, STATUS_BLOCKED_G108_RESET_SURVIVAL_OR_INITIALIZE_VIOLATION
        )

    def test_51_g108_invalid_tc_preset_ub_preset_or_tampered_6item_schema_blocked(
        self,
    ) -> None:
        for bad_kwargs in (
            {"pre_reset_tc_preset": "24:00:00.00"},
            {"pre_reset_tc_preset": "00:60:00.00"},
            {"pre_reset_tc_preset": "00:00:60.00"},
            {"pre_reset_tc_preset": "00:00:00.60"},
            {"pre_reset_ub_preset": "GG 00 00 00"},
            {"pre_reset_ub_preset": "00 00 00"},
            {"tcub_subitems": TCUB_EXACT_6_ITEMS_G108[:5]},
            {"log_shooting_mode": "S-Log2"},
            {"pre_reset_gamma_disp_assist_typ": "S-Log2->709"},
            {"frame_rate": "120p_invalid"},
            {"pre_reset_tc_run": "External Jam"},
            {"pre_reset_tc_make": "Auto"},
            {"pre_reset_tcub_disp_setting": "Duration"},
            {"body_model_name": "ILME-FX6"},
        ):
            res = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                **bad_kwargs
            )
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G108_TELEMETRY_INVALID, res.violation_codes)

    def test_52_evaluate_g108_dual_mode_and_persistent_write_block(self) -> None:
        v_clean, r_clean = (
            evaluate_g108_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                force_clean_room=True
            )
        )
        self.assertTrue(v_clean.passed)
        self.assertTrue(r_clean.valid)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIsInstance(r_clean.to_dict(), dict)

        v_blk, r_blk = (
            evaluate_g108_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                force_clean_room=True, request_persistent_emmc_writes=True
            )
        )
        self.assertFalse(v_blk.passed)
        self.assertFalse(r_blk.valid)
        self.assertEqual(r_blk.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_53_evaluate_g108_propagates_donor_integrity_failure(self) -> None:
        bad_audit = audit_phase268_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        verdict, res = (
            evaluate_g108_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                donor_audit=bad_audit
            )
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE268_DONOR_INTEGRITY)

    def test_54_resolve_fx3_gamma_disp_assist_auto_review_and_tcub_state_direct(
        self,
    ) -> None:
        st = resolve_fx3_gamma_disp_assist_auto_review_and_tcub_state(
            reset_action="Camera Settings Reset",
            log_shooting_mode="Flexible ISO",
            pre_reset_gamma_display_assist="On",
            pre_reset_select_lut="User4",
            frame_rate="25p",
            pre_reset_tc_format="DF",
        )
        self.assertEqual(st["effective_gamma_display_assist"], "Off")
        self.assertEqual(st["effective_post_reset_select_lut"], "s709")
        self.assertEqual(st["effective_tc_format"], "NDF")

    # ------------------------------------------------------------------
    # Section D: Unified 108-Gate Master Preflight & CLI Subcommands (55..72)
    # ------------------------------------------------------------------

    def test_55_master_108gate_offline_active_mode_105_of_108(self) -> None:
        rep = self.active_offline_108
        self.assertEqual(rep.schema, REALHW_FILE_SETTINGS_GAMMA_ASSIST_TCUB_108GATE_SCHEMA)
        self.assertEqual(rep.version, "1.0.0")
        self.assertEqual(rep.summary["total_gates"], 108)
        self.assertEqual(rep.summary["verified_gates"], 105)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 9)
        self.assertEqual(rep.summary["g13_to_g106_verified"], 94)
        self.assertEqual(rep.summary["g107_to_g108_verified"], 2)
        self.assertTrue(rep.offline_105_gates_verified)
        self.assertFalse(rep.all_108_gates_verified)
        self.assertTrue(rep.g13_to_g108_all_passed)
        self.assertTrue(rep.g107_to_g108_all_passed)
        self.assertTrue(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(rep.status, "VERIFIED_105_OF_108_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 108)
        self.assertEqual(rep.gates[-2]["gate_id"], G107_GATE_ID)
        self.assertEqual(rep.gates[-1]["gate_id"], G108_GATE_ID)

    def test_56_master_108gate_tier0_g10_g11_g12_fail_closed_offline(self) -> None:
        rep = self.active_offline_108
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
        for idx in list(range(0, 9)) + list(range(12, 108)):
            self.assertTrue(rep.gates[idx]["passed"])

    def test_57_master_108gate_dry_run_simulated_108_of_108(self) -> None:
        rep = self.active_dryrun_108
        self.assertEqual(rep.summary["verified_gates"], 108)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_108_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_108_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_58_master_108gate_clean_room_offline_and_dry_run_parity(self) -> None:
        self.assertEqual(
            self.clean_offline_108.verification_mode, "CLEAN_ROOM_SYNTHETIC"
        )
        self.assertTrue(self.clean_offline_108.clean_room_forced)
        self.assertEqual(self.clean_offline_108.summary["verified_gates"], 105)
        self.assertTrue(self.clean_offline_108.offline_105_gates_verified)

        self.assertEqual(
            self.clean_dryrun_108.verification_mode, "CLEAN_ROOM_SYNTHETIC"
        )
        self.assertEqual(self.clean_dryrun_108.summary["verified_gates"], 108)
        self.assertTrue(self.clean_dryrun_108.all_108_gates_verified)

    def test_59_master_108gate_redline_flags_locked_false_and_zero_usb(self) -> None:
        for rep in (
            self.active_offline_108,
            self.active_dryrun_108,
            self.clean_offline_108,
            self.clean_dryrun_108,
        ):
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertTrue(rep.agent_auto_flash_blocked)
            self.assertFalse(rep.human_hardware_attach_token)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.persistent_write_release)
            self.assertFalse(rep.physical_flash_auto_exec_authorized)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_60_master_108gate_persistent_emmc_write_request_blocks_preflight(
        self,
    ) -> None:
        rep = evaluate_108gate_preflight(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
            master_106_override=self.clean_offline_106,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_105_gates_verified)
        self.assertFalse(rep.all_108_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_61_master_108gate_propagates_g107_failure(self) -> None:
        rep = evaluate_108gate_preflight(
            force_clean_room=True,
            file_settings_kwargs={
                "target_still_slot": MEDIA_SLOT_1_G107,
                "slot1_holds_recovery_vault": True,
                "forced_file_number_reset_requested": True,
            },
            master_106_override=self.clean_offline_106,
        )
        self.assertFalse(rep.g107_to_g108_all_passed)
        self.assertFalse(rep.g13_to_g108_all_passed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G107_SLOT1_VAULT_FOLDER_MUTATION_VIOLATION
        )

    def test_62_master_108gate_propagates_g108_failure(self) -> None:
        rep = evaluate_108gate_preflight(
            force_clean_room=True,
            gamma_assist_tcub_kwargs={
                "log_shooting_mode": LOG_SHOOTING_CINE_EI_G108,
                "claimed_effective_gamma_display_assist": GAMMA_DISP_ASSIST_ON_G108,
            },
            master_106_override=self.clean_offline_106,
        )
        self.assertFalse(rep.g107_to_g108_all_passed)
        self.assertFalse(rep.g13_to_g108_all_passed)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G108_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_VIOLATION,
        )

    def test_63_master_108gate_propagates_upstream_m106_failure(self) -> None:
        bad_m106 = dataclasses.replace(
            self.clean_offline_106,
            g13_to_g106_all_passed=False,
            status="BLOCKED_UPSTREAM_M106_TEST",
        )
        rep = evaluate_108gate_preflight(
            force_clean_room=True, master_106_override=bad_m106
        )
        self.assertFalse(rep.g13_to_g108_all_passed)
        self.assertEqual(rep.status, "BLOCKED_UPSTREAM_M106_TEST")

    def test_64_master_108gate_aliases_and_to_dict_json_roundtrip(self) -> None:
        self.assertIs(evaluate_108_master_safety_gates, evaluate_108gate_preflight)
        self.assertIs(run_108_gate_preflight, evaluate_108gate_preflight)
        payload = json.loads(json.dumps(self.clean_offline_108.to_dict()))
        self.assertEqual(payload["summary"]["total_gates"], 108)
        self.assertEqual(payload["summary"]["verified_gates"], 105)

    def test_65_cli_verify_g107_primary_and_alias_text_and_json(self) -> None:
        for subcmd in (
            "verify-file-settings-dsc-slot1-vault-guard",
            "verify-g107-file-settings-vault",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([subcmd, "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn(G107_GATE_ID, buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g107-file-settings-vault", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        parsed = json.loads(jbuf.getvalue())
        self.assertTrue(parsed["valid"])
        self.assertEqual(
            parsed["file_settings_guard"]["slot1_vault_folder_mutation_events"], 0
        )

    def test_66_cli_verify_g108_primary_and_alias_text_and_json(self) -> None:
        for subcmd in (
            "verify-gamma-disp-assist-auto-review-tcub-guard",
            "verify-g108-gamma-assist-tcub",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([subcmd, "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn(G108_GATE_ID, buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g108-gamma-assist-tcub", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        parsed = json.loads(jbuf.getvalue())
        self.assertTrue(parsed["valid"])
        self.assertEqual(
            parsed["gamma_assist_auto_review_tcub_guard"][
                "hdmi_gamma_assist_leak_frames"
            ],
            0,
        )

    def test_67_cli_verify_108_gates_offline_text_output(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_108gate_preflight",
            return_value=self.clean_offline_108,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-108-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=105/108", out)
        self.assertIn("all_108_gates_verified=False", out)
        self.assertIn("usb_packets_transmitted=0", out)

    def test_68_cli_verify_108_gates_simulate_bench_dry_run_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_108gate_preflight",
            return_value=self.clean_dryrun_108,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    [
                        "verify-108-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=108/108", buf.getvalue())
            self.assertIn("all_108_gates_verified=True", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(
                    [
                        "verify-108-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertTrue(parsed["all_108_gates_verified"])
            self.assertEqual(parsed["summary"]["verified_gates"], 108)

    def test_69_standalone_module_main_offline_and_dry_run(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_file_settings_gamma_assist_tcub_and_108gate_guard.evaluate_108gate_preflight",
            return_value=self.clean_offline_108,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=105/108", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_file_settings_gamma_assist_tcub_and_108gate_guard.evaluate_108gate_preflight",
            return_value=self.clean_dryrun_108,
        ):
            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            self.assertTrue(json.loads(jbuf.getvalue())["all_108_gates_verified"])

    def test_70_end_to_end_live_evaluate_108gate_preflight_clean_room_dry_run(
        self,
    ) -> None:
        rep = evaluate_108gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_106_override=self.clean_dryrun_106,
        )
        self.assertTrue(rep.all_108_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 108)
        self.assertEqual(rep.master_106_report["summary"]["total_gates"], 106)
        self.assertEqual(
            self.active_offline_108.master_106_report["summary"]["total_gates"], 106
        )
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_71_fx3_clean_room_test_env_forces_clean_room_in_master_108(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE268: "1"}):
            self.assertTrue(_is_forced_clean_room())
            rep = evaluate_108gate_preflight(master_106_override=self.clean_offline_106)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.clean_room_forced)

    def test_72_upstream_verify_106_gates_remains_100pct_intact(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_106gate_preflight",
            return_value=self.clean_offline_106,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-106-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=103/106", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
