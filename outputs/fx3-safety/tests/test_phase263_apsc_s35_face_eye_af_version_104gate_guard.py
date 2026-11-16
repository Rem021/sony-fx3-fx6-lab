"""Phase 263 Dual-Mode Unit Tests (68 tests, < 4s runtime) for
`fx3_safety.realhw_apsc_s35_face_eye_af_version_and_104gate_guard`:

- Gate `G103`: `ILME-FX3` (`Ver. 7.02`, `ilc/2210`, `12.1MP` sensor)
  `[APS-C S35 Shooting]` (`Auto` default / `On` ~`1.5x` / `Off`, resettable by
  `[Camera Settings Reset]`) strict `4K` movie (`XAVC HS 4K`, `XAVC S 4K`,
  `XAVC S-I 4K`) & `4264x2408` `HDMI RAW Output` lockout where Super 35mm movie
  capture operates ONLY in `HD` (`XAVC S HD` / `XAVC S-I HD`), AND `[Face/Eye AF]`
  (`MENU -> Focus -> [Face/Eye AF]`, rejecting dedicated AI-unit `[Subject Recog in AF]`:
  `[Face/Eye Prior. in AF]`, `[Face/Eye Subject]`, `[Right/Left Eye Select]`,
  `[Face/Eye Frame Disp.]` clean-HDMI isolation, and `[Face Memory]` surviving
  `[Camera Settings Reset]`).
- Gate `G104`: `ILME-FX3` (`Ver. 7.02`) `MENU -> Setup -> [Setup Option] -> [Version]`
  read-only Body / E-mount Lens / Mount Adaptor inspection (`version_dialog_flash_writes == 0`),
  `Ver. 6.00+`/`7.02` update notification badge suppression on zero-RF `Airplane Mode = On`
  bench (`passive_tx_bytes_emitted == 0`), and hard-blocked automated Slot-1
  `BODYDATA.DAT` flash guard (`bodydata_flash_attempts_blocked >= 1`,
  `slot1_bodydata_vault_mutation_bytes == 0`).
- Unified `104`-Gate Master Safety Preflight (`evaluate_104gate_preflight` /
  `verify-104-gates`): `101/104` offline and `104/104` in `--simulate-bench-dry-run`
  with all hardware write/live-attach redlines hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import functools
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_apsc_s35_face_eye_af_version_and_104gate_guard import (
    AIRPLANE_MODE_BENCH_REQUIRED_G104,
    AIRPLANE_MODE_OFF_G104,
    AIRPLANE_MODE_ON_G104,
    ALLOWED_AIRPLANE_MODE_SETTINGS_G104,
    ALLOWED_APSC_S35_SETTINGS_G103,
    ALLOWED_CAPTURE_DOMAINS_G103,
    ALLOWED_FACE_EYE_FRAME_DISP_SETTINGS_G103,
    ALLOWED_FACE_EYE_PRIOR_SETTINGS_G103,
    ALLOWED_FACE_EYE_SUBJECTS_G103,
    ALLOWED_LENS_COVERAGES_G103,
    ALLOWED_MOVIE_FILE_FORMATS_G103,
    ALLOWED_RESET_ACTIONS_PHASE263,
    ALLOWED_RIGHT_LEFT_EYE_SELECT_G103,
    ALLOWED_S35_HD_MOVIE_FORMATS_G103,
    APSC_S35_AUTO_G103,
    APSC_S35_FACTORY_DEFAULT_G103,
    APSC_S35_MENU_PATH_G103,
    APSC_S35_OFF_G103,
    APSC_S35_ON_G103,
    BODYDATA_FILENAME_G104,
    BODYDATA_SLOT1_MOUNT_PATH_G104,
    CAPTURE_DOMAIN_MOVIE_G103,
    CAPTURE_DOMAIN_STILL_G103,
    DEFAULT_LENS_VERSION_G104,
    DEFAULT_MOUNT_ADAPTOR_VERSION_G104,
    DISALLOWED_AI_UNIT_MENU_LABELS_G103,
    DONOR_CHECK_MAX_SECONDS_PHASE263,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FACE_EYE_AF_CANONICAL_MENU_LABEL_G103,
    FACE_EYE_AF_MENU_PATH_G103,
    FACE_EYE_FRAME_DISP_FACTORY_DEFAULT_G103,
    FACE_EYE_FRAME_DISP_OFF_G103,
    FACE_EYE_FRAME_DISP_ON_G103,
    FACE_EYE_PRIOR_FACTORY_DEFAULT_G103,
    FACE_EYE_PRIOR_OFF_G103,
    FACE_EYE_PRIOR_ON_G103,
    FACE_EYE_SUBJECT_ANIMAL_G103,
    FACE_EYE_SUBJECT_BIRD_G103,
    FACE_EYE_SUBJECT_FACTORY_DEFAULT_G103,
    FACE_EYE_SUBJECT_HUMAN_G103,
    FX3_APSC_S35_CROP_FACTOR_G103,
    FX3_BIRD_SUBJECT_MIN_FW_TUPLE_G103,
    FX3_DEFAULT_FW_VERSION_PHASE263,
    FX3_FULL_FRAME_CROP_FACTOR_G103,
    FX3_HDMI_RAW_OUTPUT_RES_G103,
    FX3_HELP_GUIDE_CODE_PHASE263,
    FX3_MIN_SUPPORTED_FW_TUPLE_PHASE263,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX3_SENSOR_EFFECTIVE_MP_G103,
    FX3_SENSOR_EFFECTIVE_STILL_RES_G103,
    FX3_SENSOR_NATIVE_4K_MOVIE_RES_G103,
    FX3_VERSION_BADGE_MIN_FW_TUPLE_G104,
    FX6_MODEL_NAME,
    G103,
    G103_GATE_CODE,
    G103_GATE_ID,
    G104,
    G104_GATE_CODE,
    G104_GATE_ID,
    GATE_G103_APSC_S35_12MP_4K_LOCKOUT_AND_FACE_EYE_AF_CLEAN_HDMI_GUARD,
    GATE_G104_VERSION_READONLY_AIRPLANE_BADGE_AND_BODYDATA_FLASH_BLOCK_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    HUMAN_MANUAL_MIN_BATTERY_BARS_G104,
    HUMAN_MANUAL_MIN_BATTERY_PCT_G104,
    LENS_COVERAGE_APSC_S35_G103,
    LENS_COVERAGE_FULL_FRAME_G103,
    LOCKED_4K_MOVIE_FORMATS_G103,
    MAX_FACE_MEMORY_REGISTRATIONS_G103,
    MOVIE_FORMAT_XAVC_HS_4K_G103,
    MOVIE_FORMAT_XAVC_SI_4K_G103,
    MOVIE_FORMAT_XAVC_SI_HD_G103,
    MOVIE_FORMAT_XAVC_S_4K_G103,
    MOVIE_FORMAT_XAVC_S_HD_G103,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE263_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_APSC_S35_FACE_EYE_AF_VERSION_104GATE_SCHEMA,
    REALHW_APSC_S35_FACE_EYE_AF_VERSION_104GATE_VERSION,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    RESET_ACTION_RESET_NETWORK_SET_PHASE263,
    RIGHT_LEFT_EYE_AUTO_G103,
    RIGHT_LEFT_EYE_FACTORY_DEFAULT_G103,
    RIGHT_LEFT_EYE_LEFT_G103,
    RIGHT_LEFT_EYE_RIGHT_G103,
    SENSOR_READOUT_FULL_FRAME_G103,
    SENSOR_READOUT_SUPER_35MM_G103,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G103_AI_UNIT_SUBJECT_RECOG_SPOOF_VIOLATION,
    STATUS_BLOCKED_G103_APSC_S35_4K_OR_RAW_BYPASS_VIOLATION,
    STATUS_BLOCKED_G103_HDMI_CLEAN_FEED_EYE_FRAME_BAKE_VIOLATION,
    STATUS_BLOCKED_G103_RESET_OR_FACE_MEMORY_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G103_TELEMETRY_INVALID,
    STATUS_BLOCKED_G104_BODYDATA_FLASH_EXECUTION_VIOLATION,
    STATUS_BLOCKED_G104_TELEMETRY_INVALID,
    STATUS_BLOCKED_G104_VERSION_DIALOG_FLASH_WRITE_VIOLATION,
    STATUS_BLOCKED_G104_ZERO_RF_UPDATE_BADGE_OR_TX_VIOLATION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE263_DONOR_INTEGRITY,
    STATUS_VERIFIED_G103,
    STATUS_VERIFIED_G104,
    USB_PACKETS_TRANSMITTED,
    VERSION_DIALOG_ACCESS_MODE_G104,
    VERSION_MENU_PATH_G104,
    _norm_apsc_s35_setting_g103,
    _norm_capture_domain_g103,
    _norm_face_eye_subject_g103,
    _norm_lens_coverage_g103,
    _norm_movie_file_format_g103,
    _norm_on_off_phase263,
    _norm_reset_action_phase263,
    _norm_right_left_eye_g103,
    _parse_fw_tuple,
    _read_file_o_rdonly,
    audit_phase263_donor_contracts,
    compute_apsc_s35_movie_format_lockout_matrix,
    evaluate_104_master_safety_gates,
    evaluate_104gate_preflight,
    evaluate_g103_apsc_s35_and_face_eye_af_guard,
    evaluate_g104_version_readonly_and_bodydata_flash_block_guard,
    main as module_main,
    resolve_fx3_apsc_s35_and_face_eye_af_state,
    resolve_fx3_version_readonly_and_bodydata_state,
    run_104_gate_preflight,
    verify_apsc_s35_and_face_eye_af_guard,
    verify_version_readonly_and_bodydata_flash_block_guard,
)


class TestPhase263ApscS35FaceEyeAfVersion104GateGuard(unittest.TestCase):
    """68 fast dual-mode tests covering Gates G103, G104, and unified 104-Gate preflight (< 4s)."""

    @classmethod
    def setUpClass(cls) -> None:
        # Cache upstream 102-gate and 104-gate preflight evaluations once so all 68
        # tests execute well under < 4s in both LOCAL_DONOR_O_RDONLY and
        # FX3_FX6_FORCE_CLEAN_ROOM=1 modes.
        cls.active_offline_102 = fx3_safety.evaluate_102gate_preflight()
        cls.active_offline_104 = evaluate_104gate_preflight(
            master_102_override=cls.active_offline_102
        )
        if cls.active_offline_102.clean_room_forced:
            cls.clean_offline_102 = cls.active_offline_102
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                cls.clean_dryrun_102 = fx3_safety.evaluate_102gate_preflight(
                    force_clean_room=True, dry_run_simulated=True
                )
        else:
            import dataclasses as _dc

            cls.clean_offline_102 = _dc.replace(
                cls.active_offline_102,
                verification_mode="CLEAN_ROOM_SYNTHETIC",
                clean_room_forced=True,
            )
            dry_gates = tuple(
                {**g, "passed": True} if idx < 12 else dict(g)
                for idx, g in enumerate(cls.active_offline_102.gates)
            )
            dry_summary = {
                **cls.active_offline_102.summary,
                "verified_gates": 102,
                "technical_gates_passed": 102,
                "blocked_or_pending_gates": 0,
                "g01_to_g12_verified": 12,
                "all_102_gates_verified": True,
                "dry_run_rehearsal_only": True,
            }
            cls.clean_dryrun_102 = _dc.replace(
                cls.active_offline_102,
                verification_mode="CLEAN_ROOM_SYNTHETIC",
                clean_room_forced=True,
                dry_run_rehearsal_only=True,
                all_102_gates_verified=True,
                status="VERIFIED_ALL_102_GATES_DRY_RUN_SIMULATED_BACKUP",
                technical_gates_passed=102,
                summary=dry_summary,
                gates=dry_gates,
            )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_104 = evaluate_104gate_preflight(
                force_clean_room=True, master_102_override=cls.clean_offline_102
            )
            cls.clean_dryrun_104 = evaluate_104gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_102_override=cls.clean_dryrun_102,
            )
        cls.active_dryrun_104 = evaluate_104gate_preflight(
            simulate_bench_dry_run=True,
            master_102_override=cls.clean_dryrun_102,
        )

    # ------------------------------------------------------------------
    # Section A: Schema, Exports & O_RDONLY / Clean-Room Donor Audit (01..12)
    # ------------------------------------------------------------------

    def test_01_schema_version_gate_ids_and_redline_constants(self) -> None:
        self.assertEqual(
            REALHW_APSC_S35_FACE_EYE_AF_VERSION_104GATE_SCHEMA,
            "realhw_apsc_s35_face_eye_af_version_and_104gate_guard_v1",
        )
        self.assertEqual(
            REALHW_APSC_S35_FACE_EYE_AF_VERSION_104GATE_VERSION, "1.0.0"
        )
        self.assertEqual(G103, G103_GATE_ID)
        self.assertEqual(G104, G104_GATE_ID)
        self.assertEqual(
            GATE_G103_APSC_S35_12MP_4K_LOCKOUT_AND_FACE_EYE_AF_CLEAN_HDMI_GUARD,
            G103_GATE_CODE,
        )
        self.assertEqual(
            GATE_G104_VERSION_READONLY_AIRPLANE_BADGE_AND_BODYDATA_FLASH_BLOCK_GUARD,
            G104_GATE_CODE,
        )
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX6_MODEL_NAME, "ILME-FX6")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE263, "7.02")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE263, "ilc/2210")
        self.assertEqual(FX3_SENSOR_EFFECTIVE_MP_G103, 12.1)
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

    def test_02_top_level_package_exports_all_phase263_symbols_unshadowed(self) -> None:
        mod = fx3_safety.realhw_apsc_s35_face_eye_af_version_and_104gate_guard
        self.assertEqual(fx3_safety.__all__.count(mod.__name__.split(".")[-1]), 1)
        for sym in (
            "G103",
            "G104",
            "G103_GATE_ID",
            "G104_GATE_ID",
            "Master104GateReport",
            "evaluate_104gate_preflight",
            "run_104_gate_preflight",
            "evaluate_104_master_safety_gates",
            "verify_apsc_s35_and_face_eye_af_guard",
            "verify_version_readonly_and_bodydata_flash_block_guard",
        ):
            self.assertEqual(fx3_safety.__all__.count(sym), 1)
            self.assertIs(getattr(fx3_safety, sym), getattr(mod, sym))

    def test_03_pinned_phase263_donor_specs_cover_fx3_and_fx6_contracts(self) -> None:
        self.assertEqual(len(PINNED_PHASE263_DONOR_SPECS), 6)
        bodies = {spec[0] for spec in PINNED_PHASE263_DONOR_SPECS.values()}
        self.assertEqual(bodies, {"FX3", "FX6"})
        self.assertLessEqual(DONOR_CHECK_MAX_SECONDS_PHASE263, 0.10)

    def test_04_donor_audit_active_mode_within_100ms_and_zero_leaked_bytes(
        self,
    ) -> None:
        audit = audit_phase263_donor_contracts()
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
        audit = audit_phase263_donor_contracts(force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(len(audit.checked_markers), 6)
        self.assertEqual(audit.missing_markers, ())

    def test_06_donor_audit_env_force_clean_room_toggle(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            audit = audit_phase263_donor_contracts()
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_missing_work_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = audit_phase263_donor_contracts(
                work_root=Path(tmp) / "nonexistent", force_clean_room=False
            )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_08_donor_audit_corrupted_sha256_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, _sz, _sha, markers, _lbl) in (
                PINNED_PHASE263_DONOR_SPECS.items()
            ):
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"".join(markers) + b"corrupt")
            audit = audit_phase263_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE263_DONOR_INTEGRITY)

    def test_09_donor_audit_missing_byte_marker_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, _sz, _sha, _markers, _lbl) in (
                PINNED_PHASE263_DONOR_SPECS.items()
            ):
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"NO_EXPECTED_MARKERS")
            audit = audit_phase263_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE263_DONOR_INTEGRITY)
            self.assertEqual(len(audit.missing_markers), 6)

    def test_10_donor_audit_budget_exceeded_blocks_fail_closed(self) -> None:
        audit = audit_phase263_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE263_DONOR_INTEGRITY)

    def test_11_read_file_o_rdonly_never_opens_with_write_flags(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"FX3_PHASE263_RDONLY_TEST")
            p = Path(tf.name)
        try:
            seen_flags = []
            orig_open = os.open

            def spy_open(path_str: str, flags: int, *args: object) -> int:
                seen_flags.append(flags)
                return orig_open(path_str, flags, *args)  # type: ignore[arg-type]

            with mock.patch("os.open", side_effect=spy_open):
                data = _read_file_o_rdonly(p)
            self.assertEqual(data, b"FX3_PHASE263_RDONLY_TEST")
            self.assertEqual(len(seen_flags), 1)
            self.assertEqual(seen_flags[0] & (os.O_WRONLY | os.O_RDWR), 0)
        finally:
            p.unlink(missing_ok=True)

    def test_12_normalization_helpers_cover_aliases_and_reject_garbage(self) -> None:
        self.assertEqual(_parse_fw_tuple("Ver. 7.02"), (7, 2))
        self.assertEqual(_parse_fw_tuple("v3.00"), (3, 0))
        self.assertIsNone(_parse_fw_tuple("invalid"))
        self.assertEqual(
            _norm_reset_action_phase263("[Camera Settings Reset]"),
            RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertEqual(
            _norm_reset_action_phase263("Reset Network Set."),
            RESET_ACTION_RESET_NETWORK_SET_PHASE263,
        )
        self.assertEqual(_norm_apsc_s35_setting_g103("[Auto]"), APSC_S35_AUTO_G103)
        self.assertEqual(_norm_apsc_s35_setting_g103("Super 35mm"), APSC_S35_ON_G103)
        self.assertEqual(_norm_capture_domain_g103("Still Image"), CAPTURE_DOMAIN_STILL_G103)
        self.assertEqual(_norm_lens_coverage_g103("Super 35"), LENS_COVERAGE_APSC_S35_G103)
        self.assertEqual(
            _norm_movie_file_format_g103("[XAVC S-I 4K]"), MOVIE_FORMAT_XAVC_SI_4K_G103
        )
        self.assertEqual(
            _norm_face_eye_subject_g103("[Bird]"), FACE_EYE_SUBJECT_BIRD_G103
        )
        self.assertEqual(
            _norm_right_left_eye_g103("[Right Eye]"), RIGHT_LEFT_EYE_RIGHT_G103
        )
        self.assertEqual(_norm_on_off_phase263("[On]"), "On")
        self.assertIsNone(_norm_movie_file_format_g103("ProRes 422 HQ"))


    # ------------------------------------------------------------------
    # Section B: Gate G103 — APS-C S35 4K Lockout & Face/Eye AF (13..34)
    # ------------------------------------------------------------------

    def test_13_g103_default_baseline_passes_with_4k_apsc_locked_off(self) -> None:
        res = verify_apsc_s35_and_face_eye_af_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G103)
        self.assertEqual(res.apsc_s35_menu_path, APSC_S35_MENU_PATH_G103)
        self.assertEqual(res.apsc_s35_factory_default, APSC_S35_AUTO_G103)
        self.assertTrue(res.is_4k_movie_format)
        self.assertTrue(res.apsc_s35_hardware_locked_to_off)
        self.assertEqual(res.effective_apsc_s35_state, APSC_S35_OFF_G103)
        self.assertEqual(res.effective_sensor_readout_mode, SENSOR_READOUT_FULL_FRAME_G103)
        self.assertEqual(res.effective_crop_factor, FX3_FULL_FRAME_CROP_FACTOR_G103)
        self.assertFalse(res.super35_movie_capture_active)
        self.assertEqual(res.apsc_s35_4k_or_raw_bypass_events, 0)
        self.assertEqual(res.ai_unit_subject_recog_spoof_events, 0)
        self.assertEqual(res.hdmi_clean_feed_eye_frame_baked_pixels, 0)

    def test_14_g103_exhaustive_60_state_apsc_s35_movie_lockout_matrix(self) -> None:
        matrix = compute_apsc_s35_movie_format_lockout_matrix()
        self.assertEqual(matrix["states_checked"], 60)
        self.assertEqual(matrix["apsc_s35_4k_or_raw_bypass_events"], 0)
        self.assertTrue(matrix["hd_only_super35_enforced"])
        # Only HD without HDMI RAW (2 formats x (On:2 lenses + Auto:1 APS-C lens) = 6 states)
        self.assertEqual(matrix["s35_active_states"], 6)
        self.assertEqual(matrix["locked_4k_or_raw_states"], 48)

    def test_15_g103_all_three_4k_movie_formats_force_apsc_s35_to_off(self) -> None:
        self.assertEqual(len(LOCKED_4K_MOVIE_FORMATS_G103), 3)
        for fmt in LOCKED_4K_MOVIE_FORMATS_G103:
            for setting in (APSC_S35_ON_G103, APSC_S35_AUTO_G103):
                res = verify_apsc_s35_and_face_eye_af_guard(
                    apsc_s35_setting=setting,
                    lens_coverage=LENS_COVERAGE_APSC_S35_G103,
                    movie_file_format=fmt,
                )
                self.assertTrue(res.valid)
                self.assertTrue(res.apsc_s35_hardware_locked_to_off)
                self.assertEqual(res.effective_apsc_s35_state, APSC_S35_OFF_G103)
                self.assertEqual(res.effective_crop_factor, 1.0)
                self.assertFalse(res.super35_movie_capture_active)

    def test_16_g103_4264x2408_hdmi_raw_forces_apsc_s35_off_even_in_hd_formats(
        self,
    ) -> None:
        for hd_fmt in ALLOWED_S35_HD_MOVIE_FORMATS_G103:
            res = verify_apsc_s35_and_face_eye_af_guard(
                apsc_s35_setting=APSC_S35_ON_G103,
                lens_coverage=LENS_COVERAGE_APSC_S35_G103,
                movie_file_format=hd_fmt,
                hdmi_raw_output_enabled=True,
                hdmi_raw_resolution=FX3_HDMI_RAW_OUTPUT_RES_G103,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.apsc_s35_hardware_locked_to_off)
            self.assertEqual(res.effective_apsc_s35_state, APSC_S35_OFF_G103)
            self.assertFalse(res.super35_movie_capture_active)

    def test_17_g103_hd_movie_without_raw_activates_1_5x_super35_when_on(self) -> None:
        for hd_fmt in (MOVIE_FORMAT_XAVC_S_HD_G103, MOVIE_FORMAT_XAVC_SI_HD_G103):
            res = verify_apsc_s35_and_face_eye_af_guard(
                apsc_s35_setting=APSC_S35_ON_G103,
                lens_coverage=LENS_COVERAGE_FULL_FRAME_G103,
                movie_file_format=hd_fmt,
                hdmi_raw_output_enabled=False,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.apsc_s35_hardware_locked_to_off)
            self.assertEqual(res.effective_sensor_readout_mode, SENSOR_READOUT_SUPER_35MM_G103)
            self.assertEqual(res.effective_crop_factor, FX3_APSC_S35_CROP_FACTOR_G103)
            self.assertTrue(res.super35_movie_capture_active)

    def test_18_g103_hd_movie_auto_switches_by_attached_lens_coverage(self) -> None:
        ff_res = verify_apsc_s35_and_face_eye_af_guard(
            apsc_s35_setting=APSC_S35_AUTO_G103,
            lens_coverage=LENS_COVERAGE_FULL_FRAME_G103,
            movie_file_format=MOVIE_FORMAT_XAVC_S_HD_G103,
        )
        s35_res = verify_apsc_s35_and_face_eye_af_guard(
            apsc_s35_setting=APSC_S35_AUTO_G103,
            lens_coverage=LENS_COVERAGE_APSC_S35_G103,
            movie_file_format=MOVIE_FORMAT_XAVC_S_HD_G103,
        )
        self.assertEqual(ff_res.effective_crop_factor, 1.0)
        self.assertFalse(ff_res.super35_movie_capture_active)
        self.assertEqual(s35_res.effective_crop_factor, 1.5)
        self.assertTrue(s35_res.super35_movie_capture_active)

    def test_19_g103_still_capture_domain_supports_apsc_s35_without_movie_lockout(
        self,
    ) -> None:
        res = verify_apsc_s35_and_face_eye_af_guard(
            capture_domain=CAPTURE_DOMAIN_STILL_G103,
            apsc_s35_setting=APSC_S35_ON_G103,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.sensor_effective_still_resolution, FX3_SENSOR_EFFECTIVE_STILL_RES_G103)
        self.assertFalse(res.apsc_s35_hardware_locked_to_off)
        self.assertEqual(res.effective_crop_factor, 1.5)
        self.assertFalse(res.super35_movie_capture_active)

    def test_20_g103_claimed_4k_or_raw_s35_bypass_blocks_fail_closed(self) -> None:
        res1 = verify_apsc_s35_and_face_eye_af_guard(
            apsc_s35_setting=APSC_S35_ON_G103,
            movie_file_format=MOVIE_FORMAT_XAVC_HS_4K_G103,
            claimed_effective_apsc_s35_active=True,
        )
        self.assertFalse(res1.valid)
        self.assertEqual(res1.status, STATUS_BLOCKED_G103_APSC_S35_4K_OR_RAW_BYPASS_VIOLATION)
        self.assertGreaterEqual(res1.apsc_s35_4k_or_raw_bypass_events, 1)

        res2 = verify_apsc_s35_and_face_eye_af_guard(
            apsc_s35_setting=APSC_S35_ON_G103,
            movie_file_format=MOVIE_FORMAT_XAVC_S_HD_G103,
            hdmi_raw_output_enabled=True,
            claimed_effective_crop_factor=1.5,
        )
        self.assertFalse(res2.valid)
        self.assertEqual(res2.status, STATUS_BLOCKED_G103_APSC_S35_4K_OR_RAW_BYPASS_VIOLATION)

    def test_21_g103_apsc_s35_reset_scope_across_three_reset_actions(self) -> None:
        self.assertEqual(len(ALLOWED_RESET_ACTIONS_PHASE263), 4)
        r_cam = verify_apsc_s35_and_face_eye_af_guard(
            apsc_s35_setting=APSC_S35_ON_G103,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        r_net = verify_apsc_s35_and_face_eye_af_guard(
            apsc_s35_setting=APSC_S35_ON_G103,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE263,
        )
        r_init = verify_apsc_s35_and_face_eye_af_guard(
            apsc_s35_setting=APSC_S35_OFF_G103,
            reset_action=RESET_ACTION_INITIALIZE,
        )
        self.assertEqual(r_cam.effective_post_reset_apsc_s35_setting, APSC_S35_AUTO_G103)
        self.assertEqual(r_net.effective_post_reset_apsc_s35_setting, APSC_S35_ON_G103)
        self.assertEqual(r_init.effective_post_reset_apsc_s35_setting, APSC_S35_AUTO_G103)

    def test_22_g103_bionz_xr_face_eye_af_rejects_ai_unit_subject_recog_spoofing(
        self,
    ) -> None:
        self.assertEqual(FACE_EYE_AF_MENU_PATH_G103, "MENU -> Focus -> [Face/Eye AF]")
        for spoof_label in DISALLOWED_AI_UNIT_MENU_LABELS_G103:
            res = verify_apsc_s35_and_face_eye_af_guard(
                face_eye_af_menu_label=spoof_label
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G103_AI_UNIT_SUBJECT_RECOG_SPOOF_VIOLATION
            )
            self.assertGreaterEqual(res.ai_unit_subject_recog_spoof_events, 1)

    def test_23_g103_face_eye_prior_locked_on_in_intelligent_auto(self) -> None:
        self.assertEqual(len(ALLOWED_FACE_EYE_PRIOR_SETTINGS_G103), 2)
        res = verify_apsc_s35_and_face_eye_af_guard(
            face_eye_prior_in_af=FACE_EYE_PRIOR_OFF_G103,
            shoot_mode_intelligent_auto=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_face_eye_prior_in_af, FACE_EYE_PRIOR_ON_G103)

    def test_24_g103_face_eye_subject_human_animal_and_v3_bird_gate(self) -> None:
        self.assertEqual(len(ALLOWED_FACE_EYE_SUBJECTS_G103), 3)
        self.assertEqual(FX3_BIRD_SUBJECT_MIN_FW_TUPLE_G103, (3, 0))
        for subj in ALLOWED_FACE_EYE_SUBJECTS_G103:
            ok = verify_apsc_s35_and_face_eye_af_guard(
                firmware_version="7.02", face_eye_subject=subj
            )
            self.assertTrue(ok.valid)
            self.assertEqual(ok.effective_post_reset_face_eye_subject, subj)
        old_fw = verify_apsc_s35_and_face_eye_af_guard(
            firmware_version="2.00", face_eye_subject=FACE_EYE_SUBJECT_BIRD_G103
        )
        self.assertFalse(old_fw.valid)
        self.assertEqual(old_fw.status, STATUS_BLOCKED_G103_TELEMETRY_INVALID)

    def test_25_g103_right_left_eye_select_and_switch_custom_key_toggle(self) -> None:
        self.assertEqual(len(ALLOWED_RIGHT_LEFT_EYE_SELECT_G103), 3)
        r1 = resolve_fx3_apsc_s35_and_face_eye_af_state(
            right_left_eye_select=RIGHT_LEFT_EYE_AUTO_G103,
            switch_right_left_eye_pressed=True,
        )
        r2 = resolve_fx3_apsc_s35_and_face_eye_af_state(
            right_left_eye_select=RIGHT_LEFT_EYE_RIGHT_G103,
            switch_right_left_eye_pressed=True,
        )
        r3 = resolve_fx3_apsc_s35_and_face_eye_af_state(
            right_left_eye_select=RIGHT_LEFT_EYE_LEFT_G103,
            switch_right_left_eye_pressed=True,
        )
        self.assertEqual(
            r1["effective_post_reset_right_left_eye_select"], RIGHT_LEFT_EYE_RIGHT_G103
        )
        self.assertEqual(
            r2["effective_post_reset_right_left_eye_select"], RIGHT_LEFT_EYE_LEFT_G103
        )
        self.assertEqual(
            r3["effective_post_reset_right_left_eye_select"], RIGHT_LEFT_EYE_RIGHT_G103
        )

    def test_26_g103_face_eye_frame_disp_lcd_and_af_area_auto_clear(self) -> None:
        self.assertEqual(len(ALLOWED_FACE_EYE_FRAME_DISP_SETTINGS_G103), 2)
        shown = verify_apsc_s35_and_face_eye_af_guard(
            face_eye_frame_disp=FACE_EYE_FRAME_DISP_ON_G103,
            af_area_auto_clear="Off",
            focus_locked=True,
        )
        cleared = verify_apsc_s35_and_face_eye_af_guard(
            face_eye_frame_disp=FACE_EYE_FRAME_DISP_ON_G103,
            af_area_auto_clear="On",
            focus_locked=True,
        )
        self.assertTrue(shown.lcd_eye_frame_overlay_rendered)
        self.assertFalse(cleared.lcd_eye_frame_overlay_rendered)

    def test_27_g103_clean_hdmi_isolation_never_renders_eye_frame_when_info_off_or_raw(
        self,
    ) -> None:
        clean_hdmi = verify_apsc_s35_and_face_eye_af_guard(
            face_eye_frame_disp=FACE_EYE_FRAME_DISP_ON_G103,
            hdmi_info_display="Off",
        )
        info_hdmi = verify_apsc_s35_and_face_eye_af_guard(
            face_eye_frame_disp=FACE_EYE_FRAME_DISP_ON_G103,
            hdmi_info_display="On",
            hdmi_raw_output_enabled=False,
        )
        raw_hdmi = verify_apsc_s35_and_face_eye_af_guard(
            face_eye_frame_disp=FACE_EYE_FRAME_DISP_ON_G103,
            hdmi_info_display="On",
            hdmi_raw_output_enabled=True,
        )
        self.assertTrue(clean_hdmi.lcd_eye_frame_overlay_rendered)
        self.assertFalse(clean_hdmi.hdmi_eye_frame_overlay_rendered)
        self.assertEqual(clean_hdmi.hdmi_clean_feed_eye_frame_baked_pixels, 0)
        self.assertTrue(info_hdmi.hdmi_eye_frame_overlay_rendered)
        self.assertFalse(raw_hdmi.hdmi_eye_frame_overlay_rendered)

    def test_28_g103_baked_eye_frame_pixels_on_clean_hdmi_blocks_fail_closed(
        self,
    ) -> None:
        res1 = verify_apsc_s35_and_face_eye_af_guard(
            face_eye_frame_disp=FACE_EYE_FRAME_DISP_ON_G103,
            hdmi_info_display="Off",
            claimed_hdmi_clean_feed_baked_pixels=120,
        )
        res2 = verify_apsc_s35_and_face_eye_af_guard(
            face_eye_frame_disp=FACE_EYE_FRAME_DISP_ON_G103,
            hdmi_info_display="Off",
            claimed_clean_hdmi_eye_frame_rendered=True,
        )
        self.assertFalse(res1.valid)
        self.assertEqual(
            res1.status, STATUS_BLOCKED_G103_HDMI_CLEAN_FEED_EYE_FRAME_BAKE_VIOLATION
        )
        self.assertFalse(res2.valid)
        self.assertEqual(
            res2.status, STATUS_BLOCKED_G103_HDMI_CLEAN_FEED_EYE_FRAME_BAKE_VIOLATION
        )

    def test_29_g103_face_memory_survives_camera_settings_reset_and_clears_on_delete_or_init(
        self,
    ) -> None:
        r_cam = verify_apsc_s35_and_face_eye_af_guard(
            registered_face_memory_count=5,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        r_net = verify_apsc_s35_and_face_eye_af_guard(
            registered_face_memory_count=5,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE263,
        )
        r_del = verify_apsc_s35_and_face_eye_af_guard(
            registered_face_memory_count=5,
            explicit_face_memory_delete=True,
        )
        r_init = verify_apsc_s35_and_face_eye_af_guard(
            registered_face_memory_count=5,
            reset_action=RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r_cam.face_memory_survives_camera_settings_reset)
        self.assertEqual(r_cam.effective_post_reset_registered_face_memory_count, 5)
        self.assertEqual(r_net.effective_post_reset_registered_face_memory_count, 5)
        self.assertEqual(r_del.effective_post_reset_registered_face_memory_count, 0)
        self.assertEqual(r_init.effective_post_reset_registered_face_memory_count, 0)

    def test_30_g103_face_eye_af_reset_vs_face_memory_mismatch_blocks_fail_closed(
        self,
    ) -> None:
        bad_mem = verify_apsc_s35_and_face_eye_af_guard(
            registered_face_memory_count=4,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            claimed_post_reset_face_memory_count=0,
        )
        bad_eye = verify_apsc_s35_and_face_eye_af_guard(
            right_left_eye_select=RIGHT_LEFT_EYE_LEFT_G103,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            claimed_post_reset_right_left_eye_select=RIGHT_LEFT_EYE_LEFT_G103,
        )
        self.assertFalse(bad_mem.valid)
        self.assertEqual(
            bad_mem.status,
            STATUS_BLOCKED_G103_RESET_OR_FACE_MEMORY_PERSISTENCE_VIOLATION,
        )
        self.assertFalse(bad_eye.valid)
        self.assertEqual(
            bad_eye.status,
            STATUS_BLOCKED_G103_RESET_OR_FACE_MEMORY_PERSISTENCE_VIOLATION,
        )

    def test_31_g103_invalid_model_sensor_or_face_memory_telemetry_blocks(self) -> None:
        self.assertEqual(MAX_FACE_MEMORY_REGISTRATIONS_G103, 8)
        self.assertEqual(FX3_SENSOR_NATIVE_4K_MOVIE_RES_G103, "3840x2160")
        b1 = verify_apsc_s35_and_face_eye_af_guard(body_model_name="ILME-FX30")
        b2 = verify_apsc_s35_and_face_eye_af_guard(sensor_effective_megapixels=26.0)
        b3 = verify_apsc_s35_and_face_eye_af_guard(registered_face_memory_count=9)
        b4 = verify_apsc_s35_and_face_eye_af_guard(
            hdmi_raw_output_enabled=True, hdmi_raw_resolution="3840x2160"
        )
        for bad in (b1, b2, b3, b4):
            self.assertFalse(bad.valid)
            self.assertEqual(bad.status, STATUS_BLOCKED_G103_TELEMETRY_INVALID)

    def test_32_evaluate_g103_passes_in_active_and_clean_room_modes(self) -> None:
        v_act, r_act = evaluate_g103_apsc_s35_and_face_eye_af_guard()
        v_cln, r_cln = evaluate_g103_apsc_s35_and_face_eye_af_guard(
            force_clean_room=True
        )
        self.assertTrue(v_act.passed)
        self.assertTrue(r_act.valid)
        self.assertEqual(v_act.gate_id, G103_GATE_ID)
        self.assertTrue(v_cln.passed)
        self.assertEqual(r_cln.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_33_evaluate_g103_blocks_when_persistent_emmc_writes_requested(self) -> None:
        verdict, res = evaluate_g103_apsc_s35_and_face_eye_af_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_34_evaluate_g103_propagates_donor_contract_integrity_failure(self) -> None:
        bad_audit = audit_phase263_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        verdict, res = evaluate_g103_apsc_s35_and_face_eye_af_guard(
            donor_audit=bad_audit
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE263_DONOR_INTEGRITY)

    # ------------------------------------------------------------------
    # Section C: Gate G104 — Version Read-Only, Badge & BODYDATA Block (35..52)
    # ------------------------------------------------------------------

    def test_35_g104_default_baseline_passes_readonly_zero_rf_and_bodydata_blocked(
        self,
    ) -> None:
        res = verify_version_readonly_and_bodydata_flash_block_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G104)
        self.assertEqual(res.version_menu_path, VERSION_MENU_PATH_G104)
        self.assertEqual(res.version_dialog_access_mode, VERSION_DIALOG_ACCESS_MODE_G104)
        self.assertEqual(res.formatted_body_version, "Ver. 7.02")
        self.assertEqual(res.lens_firmware_version, DEFAULT_LENS_VERSION_G104)
        self.assertEqual(
            res.mount_adaptor_firmware_version, DEFAULT_MOUNT_ADAPTOR_VERSION_G104
        )
        self.assertEqual(res.version_dialog_flash_writes, 0)
        self.assertEqual(res.airplane_mode, AIRPLANE_MODE_BENCH_REQUIRED_G104)
        self.assertTrue(res.update_notification_badge_suppressed)
        self.assertFalse(res.update_notification_badge_visible)
        self.assertEqual(res.passive_tx_bytes_emitted, 0)
        self.assertTrue(res.bodydata_flash_hard_blocked)
        self.assertGreaterEqual(res.bodydata_flash_attempts_blocked, 1)
        self.assertEqual(res.bodydata_flash_executions_permitted, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(res.slot1_bodydata_vault_mutation_bytes, 0)

    def test_36_g104_lens_and_mount_adaptor_versions_survive_all_resets(self) -> None:
        for rst in ALLOWED_RESET_ACTIONS_PHASE263:
            res = verify_version_readonly_and_bodydata_flash_block_guard(
                lens_firmware_version="Ver. 04",
                mount_adaptor_firmware_version="Ver. 01",
                reset_action=rst,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.version_survives_all_resets)
            self.assertEqual(res.lens_firmware_version, "Ver. 04")
            self.assertEqual(res.mount_adaptor_firmware_version, "Ver. 01")

    def test_37_g104_version_dialog_write_intent_or_flash_writes_block_fail_closed(
        self,
    ) -> None:
        b1 = verify_version_readonly_and_bodydata_flash_block_guard(
            version_dialog_access_mode="READ_WRITE"
        )
        b2 = verify_version_readonly_and_bodydata_flash_block_guard(
            claimed_version_dialog_flash_writes=1
        )
        self.assertFalse(b1.valid)
        self.assertEqual(b1.status, STATUS_BLOCKED_G104_VERSION_DIALOG_FLASH_WRITE_VIOLATION)
        self.assertFalse(b2.valid)
        self.assertEqual(b2.status, STATUS_BLOCKED_G104_VERSION_DIALOG_FLASH_WRITE_VIOLATION)

    def test_38_g104_mutated_post_reset_body_version_blocks_fail_closed(self) -> None:
        res = verify_version_readonly_and_bodydata_flash_block_guard(
            body_firmware_version="7.02",
            reset_action=RESET_ACTION_INITIALIZE,
            claimed_post_reset_body_version="Ver. 1.00",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G104_VERSION_DIALOG_FLASH_WRITE_VIOLATION)

    def test_39_g104_v6_v702_update_badge_suppressed_under_zero_rf_airplane_on(
        self,
    ) -> None:
        self.assertEqual(FX3_VERSION_BADGE_MIN_FW_TUPLE_G104, (6, 0))
        self.assertEqual(ALLOWED_AIRPLANE_MODE_SETTINGS_G104, (AIRPLANE_MODE_ON_G104, AIRPLANE_MODE_OFF_G104))
        for fw in ("6.00", "7.02"):
            res = verify_version_readonly_and_bodydata_flash_block_guard(
                body_firmware_version=fw, airplane_mode=AIRPLANE_MODE_ON_G104
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.fw_supports_v6_update_badge)
            self.assertTrue(res.update_notification_badge_suppressed)
            self.assertFalse(res.update_notification_badge_visible)

    def test_40_g104_airplane_mode_off_blocks_zero_rf_bench(self) -> None:
        res = verify_version_readonly_and_bodydata_flash_block_guard(
            airplane_mode=AIRPLANE_MODE_OFF_G104
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G104_ZERO_RF_UPDATE_BADGE_OR_TX_VIOLATION)
        self.assertTrue(res.update_notification_badge_visible)

    def test_41_g104_wifi_bluetooth_or_creators_cloud_polling_blocks(self) -> None:
        for kw in (
            {"wifi_enabled": True},
            {"bluetooth_enabled": True},
            {"creators_app_cloud_polling_enabled": True},
        ):
            res = verify_version_readonly_and_bodydata_flash_block_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G104_ZERO_RF_UPDATE_BADGE_OR_TX_VIOLATION
            )

    def test_42_g104_passive_tx_bytes_or_forced_badge_visibility_blocks(self) -> None:
        r1 = verify_version_readonly_and_bodydata_flash_block_guard(
            claimed_passive_tx_bytes_emitted=64
        )
        r2 = verify_version_readonly_and_bodydata_flash_block_guard(
            claimed_update_notification_badge_visible=True
        )
        self.assertFalse(r1.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G104_ZERO_RF_UPDATE_BADGE_OR_TX_VIOLATION)
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G104_ZERO_RF_UPDATE_BADGE_OR_TX_VIOLATION)

    def test_43_g104_multiple_automated_bodydata_flash_attempts_all_blocked(
        self,
    ) -> None:
        self.assertEqual(BODYDATA_SLOT1_MOUNT_PATH_G104, "/mnt/sd_slot1/BODYDATA.DAT")
        res = verify_version_readonly_and_bodydata_flash_block_guard(
            automated_bodydata_flash_attempts=5
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.bodydata_flash_attempts_blocked, 5)
        self.assertEqual(res.bodydata_flash_executions_permitted, 0)

    def test_44_g104_allow_automated_bodydata_flash_blocks_fail_closed(self) -> None:
        r1 = verify_version_readonly_and_bodydata_flash_block_guard(
            allow_automated_bodydata_flash=True
        )
        r2 = verify_version_readonly_and_bodydata_flash_block_guard(
            claimed_bodydata_flash_executions_permitted=1
        )
        self.assertFalse(r1.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G104_BODYDATA_FLASH_EXECUTION_VIOLATION)
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G104_BODYDATA_FLASH_EXECUTION_VIOLATION)


    def test_45_g104_slot1_vault_mutation_or_unsigned_bodydata_blocks(self) -> None:
        r1 = verify_version_readonly_and_bodydata_flash_block_guard(
            claimed_slot1_bodydata_vault_mutation_bytes=4096
        )
        r2 = verify_version_readonly_and_bodydata_flash_block_guard(
            slot1_bodydata_present=True, slot1_bodydata_sony_signed=False
        )
        self.assertFalse(r1.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G104_BODYDATA_FLASH_EXECUTION_VIOLATION)
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G104_BODYDATA_FLASH_EXECUTION_VIOLATION)

    def test_46_g104_human_manual_np_fz100_battery_advisory_never_authorizes_agent_flash(
        self,
    ) -> None:
        self.assertEqual(HUMAN_MANUAL_MIN_BATTERY_PCT_G104, 51)
        self.assertEqual(HUMAN_MANUAL_MIN_BATTERY_BARS_G104, 3)
        high_batt = verify_version_readonly_and_bodydata_flash_block_guard(
            battery_charge_pct=51, battery_bars=3
        )
        low_batt = verify_version_readonly_and_bodydata_flash_block_guard(
            battery_charge_pct=50, battery_bars=2
        )
        self.assertTrue(high_batt.valid)
        self.assertTrue(high_batt.human_manual_battery_prereq_met)
        self.assertTrue(high_batt.bodydata_flash_hard_blocked)
        self.assertFalse(high_batt.persistent_emmc_writes_authorized)
        self.assertTrue(low_batt.valid)
        self.assertFalse(low_batt.human_manual_battery_prereq_met)

    def test_47_g104_pre_v6_firmware_readonly_inspection_has_no_update_badge(
        self,
    ) -> None:
        res = verify_version_readonly_and_bodydata_flash_block_guard(
            body_firmware_version="5.00"
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.formatted_body_version, "Ver. 5.00")
        self.assertFalse(res.fw_supports_v6_update_badge)
        self.assertTrue(res.update_notification_badge_suppressed)

    def test_48_g104_invalid_filename_battery_or_attempt_count_telemetry_blocks(
        self,
    ) -> None:
        self.assertEqual(BODYDATA_FILENAME_G104, "BODYDATA.DAT")
        b1 = verify_version_readonly_and_bodydata_flash_block_guard(
            bodydata_filename="TAMPERED.DAT"
        )
        b2 = verify_version_readonly_and_bodydata_flash_block_guard(
            battery_charge_pct=105
        )
        b3 = verify_version_readonly_and_bodydata_flash_block_guard(
            automated_bodydata_flash_attempts=0
        )
        b4 = verify_version_readonly_and_bodydata_flash_block_guard(
            body_model_name="ILME-FX6"
        )
        for bad in (b1, b2, b3, b4):
            self.assertFalse(bad.valid)
            self.assertEqual(bad.status, STATUS_BLOCKED_G104_TELEMETRY_INVALID)

    def test_49_evaluate_g104_passes_in_active_and_clean_room_modes(self) -> None:
        v_act, r_act = evaluate_g104_version_readonly_and_bodydata_flash_block_guard()
        v_cln, r_cln = evaluate_g104_version_readonly_and_bodydata_flash_block_guard(
            force_clean_room=True
        )
        self.assertTrue(v_act.passed)
        self.assertTrue(r_act.valid)
        self.assertEqual(v_act.gate_id, G104_GATE_ID)
        self.assertTrue(v_cln.passed)
        self.assertEqual(r_cln.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_50_evaluate_g104_blocks_when_persistent_emmc_writes_requested(self) -> None:
        verdict, res = evaluate_g104_version_readonly_and_bodydata_flash_block_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_51_evaluate_g104_propagates_donor_contract_integrity_failure(self) -> None:
        bad_audit = audit_phase263_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        verdict, res = evaluate_g104_version_readonly_and_bodydata_flash_block_guard(
            donor_audit=bad_audit
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE263_DONOR_INTEGRITY)

    def test_52_g103_and_g104_results_roundtrip_json_cleanly(self) -> None:
        _, r103 = evaluate_g103_apsc_s35_and_face_eye_af_guard(force_clean_room=True)
        _, r104 = evaluate_g104_version_readonly_and_bodydata_flash_block_guard(
            force_clean_room=True
        )
        d103 = json.loads(json.dumps(r103.to_dict()))
        d104 = json.loads(json.dumps(r104.to_dict()))
        self.assertTrue(d103["valid"])
        self.assertTrue(d104["valid"])
        self.assertEqual(d103["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(d104["raw_firmware_bytes_leaked"], 0)

    # ------------------------------------------------------------------
    # Section D: Unified 104-Gate Master Preflight & CLI (53..68)
    # ------------------------------------------------------------------

    def test_53_master_104gate_active_offline_verifies_101_of_104(self) -> None:
        rep = self.active_offline_104
        self.assertEqual(rep.summary["total_gates"], 104)
        self.assertEqual(rep.summary["verified_gates"], 101)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_101_gates_verified)
        self.assertFalse(rep.all_104_gates_verified)
        self.assertTrue(rep.g13_to_g104_all_passed)
        self.assertTrue(rep.g103_to_g104_all_passed)
        self.assertEqual(rep.status, "VERIFIED_101_OF_104_AWAITING_PHYSICAL_TIER0")
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_54_master_104gate_clean_room_offline_verifies_101_of_104(self) -> None:
        rep = self.clean_offline_104
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertEqual(rep.summary["verified_gates"], 101)
        self.assertTrue(rep.offline_101_gates_verified)
        self.assertFalse(rep.all_104_gates_verified)

    def test_55_master_104gate_clean_room_dry_run_verifies_all_104_of_104(self) -> None:
        rep = self.clean_dryrun_104
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.summary["verified_gates"], 104)
        self.assertTrue(rep.all_104_gates_verified)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_104_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_56_master_104gate_active_dry_run_verifies_all_104_and_locks_redlines(
        self,
    ) -> None:
        rep = self.active_dryrun_104
        self.assertEqual(rep.summary["verified_gates"], 104)
        self.assertTrue(rep.all_104_gates_verified)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_104_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_57_master_104gate_aliases_and_gate_ordering(self) -> None:
        self.assertIs(run_104_gate_preflight, evaluate_104gate_preflight)
        self.assertIs(evaluate_104_master_safety_gates, evaluate_104gate_preflight)
        self.assertEqual(len(self.clean_offline_104.gates), 104)
        self.assertEqual(self.clean_offline_104.gates[-2]["gate_id"], G103_GATE_ID)
        self.assertEqual(self.clean_offline_104.gates[-1]["gate_id"], G104_GATE_ID)

    def test_58_master_104gate_fails_closed_when_g103_violated(self) -> None:
        rep = evaluate_104gate_preflight(
            force_clean_room=True,
            master_102_override=self.clean_offline_102,
            apsc_s35_face_eye_af_kwargs={
                "face_eye_af_menu_label": "Subject Recog in AF"
            },
        )
        self.assertFalse(rep.g103_to_g104_all_passed)
        self.assertFalse(rep.offline_101_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G103_AI_UNIT_SUBJECT_RECOG_SPOOF_VIOLATION
        )

    def test_59_master_104gate_fails_closed_when_g104_violated(self) -> None:
        rep = evaluate_104gate_preflight(
            force_clean_room=True,
            master_102_override=self.clean_offline_102,
            version_bodydata_kwargs={"allow_automated_bodydata_flash": True},
        )
        self.assertFalse(rep.g103_to_g104_all_passed)
        self.assertFalse(rep.offline_101_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G104_BODYDATA_FLASH_EXECUTION_VIOLATION
        )

    def test_60_master_104gate_blocks_when_persistent_emmc_writes_requested(
        self,
    ) -> None:
        rep = evaluate_104gate_preflight(
            force_clean_room=True,
            master_102_override=self.clean_offline_102,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep.offline_101_gates_verified)
        self.assertFalse(rep.all_104_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_61_cli_verify_g103_primary_and_alias_text_and_json(self) -> None:
        buf_txt = io.StringIO()
        with contextlib.redirect_stdout(buf_txt):
            rc1 = cli_main(["verify-apsc-s35-face-eye-af-guard", "--force-clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn(G103_GATE_ID, buf_txt.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = cli_main(
                ["verify-g103-apsc-s35-face-eye-af", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc2, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_G103)

    def test_62_cli_verify_g104_primary_and_alias_text_and_json(self) -> None:
        buf_txt = io.StringIO()
        with contextlib.redirect_stdout(buf_txt):
            rc1 = cli_main(
                [
                    "verify-version-readonly-bodydata-flash-block-guard",
                    "--force-clean-room",
                ]
            )
        self.assertEqual(rc1, 0)
        self.assertIn(G104_GATE_ID, buf_txt.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = cli_main(
                ["verify-g104-version-bodydata-block", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc2, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_G104)

    def test_63_cli_verify_104_gates_offline_and_dry_run_json(self) -> None:
        fast_off = functools.partial(
            evaluate_104gate_preflight, master_102_override=self.clean_offline_102
        )
        buf_off = io.StringIO()
        with (
            mock.patch(
                "fx3_safety.__main__.evaluate_104gate_preflight", side_effect=fast_off
            ),
            contextlib.redirect_stdout(buf_off),
        ):
            rc_off = cli_main(["verify-104-gates", "--force-clean-room"])
        self.assertEqual(rc_off, 0)
        self.assertIn("verified=101/104", buf_off.getvalue())

        fast_dry = functools.partial(
            evaluate_104gate_preflight, master_102_override=self.clean_dryrun_102
        )
        buf_dry = io.StringIO()
        with (
            mock.patch(
                "fx3_safety.__main__.evaluate_104gate_preflight", side_effect=fast_dry
            ),
            contextlib.redirect_stdout(buf_dry),
        ):
            rc_dry = cli_main(
                [
                    "verify-104-gates",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                ]
            )
        self.assertEqual(rc_dry, 0)
        payload = json.loads(buf_dry.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 104)
        self.assertTrue(payload["all_104_gates_verified"])

    def test_64_module_standalone_main_offline_and_dry_run(self) -> None:
        fast_off = functools.partial(
            evaluate_104gate_preflight, master_102_override=self.clean_offline_102
        )
        buf1 = io.StringIO()
        with (
            mock.patch(
                "fx3_safety.realhw_apsc_s35_face_eye_af_version_and_104gate_guard.evaluate_104gate_preflight",
                side_effect=fast_off,
            ),
            contextlib.redirect_stdout(buf1),
        ):
            rc1 = module_main(["--force-clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn("verified=101/104", buf1.getvalue())

        fast_dry = functools.partial(
            evaluate_104gate_preflight, master_102_override=self.clean_dryrun_102
        )
        buf2 = io.StringIO()
        with (
            mock.patch(
                "fx3_safety.realhw_apsc_s35_face_eye_af_version_and_104gate_guard.evaluate_104gate_preflight",
                side_effect=fast_dry,
            ),
            contextlib.redirect_stdout(buf2),
        ):
            rc2 = module_main(["--force-clean-room", "--simulate-bench-dry-run", "--json"])
        self.assertEqual(rc2, 0)
        self.assertEqual(json.loads(buf2.getvalue())["summary"]["verified_gates"], 104)

    def test_65_backward_compatibility_with_102_gate_preflight_baseline(self) -> None:
        self.assertEqual(self.clean_offline_102.summary["verified_gates"], 99)
        self.assertEqual(self.clean_dryrun_102.summary["verified_gates"], 102)
        self.assertTrue(self.clean_offline_102.offline_99_gates_verified)
        self.assertTrue(self.clean_dryrun_102.all_102_gates_verified)

    def test_66_backward_compatibility_58_through_102_gate_entrypoints_present(
        self,
    ) -> None:
        for n in range(58, 105, 2):
            fn = getattr(fx3_safety, f"evaluate_{n}gate_preflight", None)
            self.assertTrue(callable(fn), f"Missing evaluate_{n}gate_preflight")

    def test_67_dry_run_synonym_flags_produce_identical_104_of_104_verdict(
        self,
    ) -> None:
        r_a = evaluate_104gate_preflight(
            force_clean_room=True,
            dry_run_simulated=True,
            master_102_override=self.clean_dryrun_102,
        )
        r_b = evaluate_104gate_preflight(
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_102_override=self.clean_dryrun_102,
        )
        self.assertTrue(r_a.all_104_gates_verified)
        self.assertTrue(r_b.all_104_gates_verified)
        self.assertEqual(r_a.status, r_b.status)

    def test_68_master_104gate_report_json_serialization_and_redlines(self) -> None:
        d = json.loads(json.dumps(self.clean_dryrun_104.to_dict()))
        self.assertEqual(
            d["schema"], REALHW_APSC_S35_FACE_EYE_AF_VERSION_104GATE_SCHEMA
        )
        self.assertEqual(
            d["version"], REALHW_APSC_S35_FACE_EYE_AF_VERSION_104GATE_VERSION
        )
        self.assertEqual(d["summary"]["total_gates"], 104)
        self.assertEqual(d["summary"]["verified_gates"], 104)
        self.assertFalse(d["overall_ready_for_hardware_attach"])
        self.assertFalse(d["persistent_emmc_writes_authorized"])
        self.assertEqual(d["usb_packets_transmitted"], 0)
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)


if __name__ == "__main__":
    unittest.main()
