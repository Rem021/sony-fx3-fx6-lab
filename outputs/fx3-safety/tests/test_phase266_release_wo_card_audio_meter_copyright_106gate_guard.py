"""Phase 266 (Task H300 Milestone, Wave-43) Dual-Mode Unit Tests (70 tests, < 4.0s runtime)
for `fx3_safety.realhw_release_wo_card_audio_meter_copyright_and_106gate_guard`:

- Gate `G105` (`GATE_G105_RELEASE_WO_CARD_LENS_AND_V702_AUDIO_DISP_METER_GUARD`):
  - `[Release w/o Card]` (`Enable` default / `Disable`, Still-only scope vs Movie
    internal media gate across all 96 states; production `[Disable]` anti-unrecorded-shoot
    protection vs cardless diagnostic bench `[Enable]` with 0 sector writes; external
    HDMI capture governed by `[Rec. Media dur HDMI Output]`).
  - `[Release w/o Lens]` (`Enable` default / `Disable`, Still + Movie + `S&Q` scope
    with `e_nd_actuator_tx_count == 0` and 0 E-mount lens UART bytes on body-only bench).
  - `Ver. 2.00+`/`7.02` (`ilc/2210`) exact 5-item `[Audio Recording]` menu vs `Ver. 1.x`
    (`ilc/2035`) standalone `[Audio Level Display]` removal (`legacy_v1_audio_level_menu_spoof_events == 0`),
    verifying 2ch/4ch audio meter visibility (suppressed during `S&Q`) under
    `Setup > Operation Customize > [DISP (Screen Disp) Set]`.
- Gate `G106` (`GATE_G106_COPYRIGHT_INFO_46CHAR_STILL_EXIF_AND_PII_HYGIENE_GUARD`):
  - `[Copyright Info]` (`Write Copyright Info` `Off` default / `On`, `Set Photographer`
    `<= 46` ASCII chars, `Set Copyright` `<= 46` ASCII chars, read-only `Disp. Copyright Info`),
    Still-JPEG/HEIF/ARW EXIF-only scope (never mutating XAVC/RAW movie streams or `Slot-1`
    recovery vault), `[Camera Settings Reset]` string survival vs `[Initialize]` wipe,
    `[Save/Load Settings]` exclusion, and clean-room bench PII hygiene
    (`photographer_copyright_pii_leaked_bytes == 0`).
- Unified `106`-Gate Master Safety Preflight (`evaluate_106gate_preflight` /
  `verify-106-gates`): `103/106` offline and `106/106` in `--simulate-bench-dry-run`
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
from fx3_safety.realhw_release_wo_card_audio_meter_copyright_and_106gate_guard import (
    ALLOWED_AUDIO_OUT_TIMING_G105,
    ALLOWED_BENCH_POSTURES_G105,
    ALLOWED_CAPTURE_MODES_G105,
    ALLOWED_HDMI_REC_MEDIA_SETTINGS_G105,
    ALLOWED_LENS_MOUNT_STATES_G105,
    ALLOWED_RELEASE_ENABLE_DISABLE_G105,
    ALLOWED_RESET_ACTIONS_PHASE266,
    ALLOWED_SHOE_AUDIO_SETTINGS_G105,
    ALLOWED_TARGET_CONTAINERS_G106,
    ALLOWED_WRITE_COPYRIGHT_SETTINGS_G106,
    AUDIO_OUT_TIMING_FACTORY_DEFAULT_G105,
    AUDIO_OUT_TIMING_LIP_SYNC_G105,
    AUDIO_OUT_TIMING_LIVE_G105,
    AUDIO_RECORDING_FACTORY_DEFAULT_G105,
    AUDIO_RECORDING_MENU_PATH_G105,
    AUDIO_RECORDING_OFF_G105,
    AUDIO_RECORDING_ON_G105,
    AUDIO_REC_LEVEL_FACTORY_DEFAULT_G105,
    AUDIO_REC_LEVEL_MAX_G105,
    AUDIO_REC_LEVEL_MIN_G105,
    BENCH_POSTURE_CARDLESS_DIAGNOSTIC_G105,
    BENCH_POSTURE_PRODUCTION_SHOOT_G105,
    CAPTURE_MODE_MOVIE_G105,
    CAPTURE_MODE_SQ_G105,
    CAPTURE_MODE_STILL_G105,
    CONTAINER_HDMI_RAW_STREAM_G106,
    CONTAINER_MOVIE_XAVC_HS_MP4_G106,
    CONTAINER_MOVIE_XAVC_SI_MP4_G106,
    CONTAINER_MOVIE_XAVC_S_MP4_G106,
    CONTAINER_STILL_ARW_G106,
    CONTAINER_STILL_HEIF_G106,
    CONTAINER_STILL_JPEG_G106,
    COPYRIGHT_INFO_EXACT_4_SUBITEMS_G106,
    COPYRIGHT_INFO_MAX_CHARS_G106,
    COPYRIGHT_INFO_MENU_PATH_G106,
    DISALLOWED_V1_AUDIO_MENU_ITEMS_G105,
    DISP_SCREEN_DISP_SET_MENU_PATH_G105,
    DONOR_CHECK_MAX_SECONDS_PHASE266,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE266,
    EXIF_TAG_ARTIST_HEX_G106,
    EXIF_TAG_COPYRIGHT_HEX_G106,
    FX3_DEFAULT_FW_VERSION_PHASE266,
    FX3_HELP_GUIDE_CODE_PHASE266,
    FX3_LEGACY_V1_HELP_GUIDE_CODE_G105,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX3_V2_AUDIO_DISP_MIN_FW_TUPLE_G105,
    FX6_MODEL_NAME,
    G105,
    G105_GATE_CODE,
    G105_GATE_ID,
    G106,
    G106_GATE_CODE,
    G106_GATE_ID,
    GATE_G105_RELEASE_WO_CARD_LENS_AND_V702_AUDIO_DISP_METER_GUARD,
    GATE_G106_COPYRIGHT_INFO_46CHAR_STILL_EXIF_AND_PII_HYGIENE_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_REC_MEDIA_OFF_G105,
    HDMI_REC_MEDIA_ON_G105,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LENS_MOUNT_BODY_ONLY_BENCH_G105,
    LENS_MOUNT_ELECTRONIC_EMOUNT_G105,
    LENS_MOUNT_PL_MECHANICAL_ADAPTER_G105,
    MAX_COPYRIGHT_CHARS_G106,
    MAX_PHOTOGRAPHER_CHARS_G106,
    MOVIE_AND_RAW_CONTAINERS_G106,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE266_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_RELEASE_WO_CARD_AUDIO_METER_COPYRIGHT_106GATE_SCHEMA,
    REALHW_RELEASE_WO_CARD_AUDIO_METER_COPYRIGHT_106GATE_VERSION,
    RELEASE_DISABLE_G105,
    RELEASE_ENABLE_G105,
    RELEASE_WO_CARD_FACTORY_DEFAULT_G105,
    RELEASE_WO_CARD_MENU_PATH_G105,
    RELEASE_WO_LENS_FACTORY_DEFAULT_G105,
    RELEASE_WO_LENS_MENU_PATH_G105,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    RESET_ACTION_RESET_NETWORK_SET_PHASE266,
    SHOE_AUDIO_48K_16B_2CH_G105,
    SHOE_AUDIO_48K_24B_2CH_G105,
    SHOE_AUDIO_48K_24B_4CH_G105,
    SHOE_AUDIO_FACTORY_DEFAULT_G105,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G105_DISP_AUDIO_METER_OR_SQ_SUPPRESSION_VIOLATION,
    STATUS_BLOCKED_G105_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_VIOLATION,
    STATUS_BLOCKED_G105_MOVIE_CARDLESS_INTERNAL_REC_BYPASS_VIOLATION,
    STATUS_BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION,
    STATUS_BLOCKED_G105_RELEASE_WO_LENS_OR_END_UART_VIOLATION,
    STATUS_BLOCKED_G105_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G105_TELEMETRY_INVALID,
    STATUS_BLOCKED_G106_BENCH_PII_HYGIENE_LEAK_VIOLATION,
    STATUS_BLOCKED_G106_COPYRIGHT_46CHAR_OR_ASCII_BOUND_VIOLATION,
    STATUS_BLOCKED_G106_MOVIE_STREAM_OR_SLOT1_VAULT_MUTATION_VIOLATION,
    STATUS_BLOCKED_G106_RESET_SURVIVAL_OR_INITIALIZE_WIPE_VIOLATION,
    STATUS_BLOCKED_G106_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE266_DONOR_INTEGRITY,
    STATUS_VERIFIED_G105,
    STATUS_VERIFIED_G106,
    STILL_EXIF_ELIGIBLE_CONTAINERS_G106,
    USB_PACKETS_TRANSMITTED,
    V702_AUDIO_RECORDING_EXACT_5_ITEMS_G105,
    WIND_NOISE_REDUCT_FACTORY_DEFAULT_G105,
    WIND_NOISE_REDUCT_OFF_G105,
    WIND_NOISE_REDUCT_ON_G105,
    WRITE_COPYRIGHT_INFO_BENCH_DEFAULT_G106,
    WRITE_COPYRIGHT_INFO_FACTORY_DEFAULT_G106,
    WRITE_COPYRIGHT_INFO_OFF_G106,
    WRITE_COPYRIGHT_INFO_ON_G106,
    _is_forced_clean_room,
    _is_valid_46char_printable_ascii_g106,
    _norm_audio_out_timing_g105,
    _norm_bench_posture_g105,
    _norm_capture_mode_g105,
    _norm_enable_disable_g105,
    _norm_lens_mount_state_g105,
    _norm_on_off_phase266,
    _norm_reset_action_phase266,
    _norm_shoe_audio_set_g105,
    _norm_target_container_g106,
    _parse_fw_tuple,
    _read_file_o_rdonly,
    audit_phase266_donor_contracts,
    compute_release_wo_card_and_lens_scope_matrix,
    evaluate_106_master_safety_gates,
    evaluate_106gate_preflight,
    evaluate_g105_release_wo_card_lens_and_v702_audio_disp_guard,
    evaluate_g106_copyright_info_46char_still_exif_and_pii_hygiene_guard,
    main as module_main,
    resolve_fx3_copyright_info_46char_still_exif_state,
    resolve_fx3_release_wo_card_lens_and_v702_audio_disp_state,
    run_106_gate_preflight,
    verify_copyright_info_46char_still_exif_and_pii_hygiene_guard,
    verify_release_wo_card_lens_and_v702_audio_disp_guard,
)


class TestPhase266ReleaseWoCardAudioMeterCopyright106GateGuard(unittest.TestCase):
    """70 fast dual-mode tests covering Gates G105, G106, and unified 106-Gate preflight (< 4.0s)."""

    @classmethod
    def setUpClass(cls) -> None:
        # Cache upstream 104-gate evaluation once so all 70 tests execute well
        # under < 4.0s in both LOCAL_DONOR_O_RDONLY and FX3_CLEAN_ROOM_TEST=1 /
        # FX3_FX6_FORCE_CLEAN_ROOM=1 modes.
        env_clean = _is_forced_clean_room()
        cls.active_offline_104 = fx3_safety.evaluate_104gate_preflight(
            force_clean_room=True if env_clean else None
        )
        cls.active_offline_106 = evaluate_106gate_preflight(
            force_clean_room=True if env_clean else None,
            master_104_override=cls.active_offline_104,
        )

        cls.clean_offline_104 = dataclasses.replace(
            cls.active_offline_104,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            clean_room_forced=True,
        )
        dry_gates_104 = tuple(
            {**g, "passed": True} if idx < 12 else dict(g)
            for idx, g in enumerate(cls.active_offline_104.gates)
        )
        dry_summary_104 = {
            **cls.active_offline_104.summary,
            "verified_gates": 104,
            "technical_gates_passed": 104,
            "blocked_or_pending_gates": 0,
            "g01_to_g12_verified": 12,
            "all_104_gates_verified": True,
            "dry_run_rehearsal_only": True,
        }
        cls.active_dryrun_104 = dataclasses.replace(
            cls.active_offline_104,
            dry_run_rehearsal_only=True,
            all_104_gates_verified=True,
            status="VERIFIED_ALL_104_GATES_DRY_RUN_SIMULATED_BACKUP",
            technical_gates_passed=104,
            summary=dry_summary_104,
            gates=dry_gates_104,
        )
        cls.clean_dryrun_104 = dataclasses.replace(
            cls.active_dryrun_104,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            clean_room_forced=True,
        )

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_106 = evaluate_106gate_preflight(
                force_clean_room=True, master_104_override=cls.clean_offline_104
            )
            cls.clean_dryrun_106 = evaluate_106gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_104_override=cls.clean_dryrun_104,
            )
        cls.active_dryrun_106 = evaluate_106gate_preflight(
            force_clean_room=True if env_clean else None,
            simulate_bench_dry_run=True,
            master_104_override=cls.active_dryrun_104,
        )

    # ------------------------------------------------------------------
    # Section A: Schema, Exports & O_RDONLY / Clean-Room Donor Audit (01..12)
    # ------------------------------------------------------------------

    def test_01_schema_version_gate_ids_and_redline_constants(self) -> None:
        self.assertEqual(
            REALHW_RELEASE_WO_CARD_AUDIO_METER_COPYRIGHT_106GATE_SCHEMA,
            "realhw_release_wo_card_audio_meter_copyright_and_106gate_guard_v1",
        )
        self.assertEqual(
            REALHW_RELEASE_WO_CARD_AUDIO_METER_COPYRIGHT_106GATE_VERSION, "1.0.0"
        )
        self.assertEqual(G105, G105_GATE_ID)
        self.assertEqual(G106, G106_GATE_ID)
        self.assertEqual(
            GATE_G105_RELEASE_WO_CARD_LENS_AND_V702_AUDIO_DISP_METER_GUARD,
            G105_GATE_CODE,
        )
        self.assertEqual(
            GATE_G106_COPYRIGHT_INFO_46CHAR_STILL_EXIF_AND_PII_HYGIENE_GUARD,
            G106_GATE_CODE,
        )
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX6_MODEL_NAME, "ILME-FX6")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE266, "7.02")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE266, "ilc/2210")
        self.assertEqual(FX3_LEGACY_V1_HELP_GUIDE_CODE_G105, "ilc/2035")
        self.assertEqual(COPYRIGHT_INFO_MAX_CHARS_G106, 46)
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

    def test_02_top_level_package_exports_all_phase266_symbols_unshadowed(self) -> None:
        mod = fx3_safety.realhw_release_wo_card_audio_meter_copyright_and_106gate_guard
        self.assertEqual(fx3_safety.__all__.count(mod.__name__.split(".")[-1]), 1)
        for sym in (
            "G105",
            "G106",
            "G105_GATE_ID",
            "G106_GATE_ID",
            "GATE_G105_RELEASE_WO_CARD_LENS_AND_V702_AUDIO_DISP_METER_GUARD",
            "GATE_G106_COPYRIGHT_INFO_46CHAR_STILL_EXIF_AND_PII_HYGIENE_GUARD",
            "Master106GateReport",
            "evaluate_106gate_preflight",
            "run_106_gate_preflight",
            "evaluate_106_master_safety_gates",
            "verify_release_wo_card_lens_and_v702_audio_disp_guard",
            "verify_copyright_info_46char_still_exif_and_pii_hygiene_guard",
        ):
            self.assertEqual(fx3_safety.__all__.count(sym), 1)
            self.assertIs(getattr(fx3_safety, sym), getattr(mod, sym))
        # Upstream G103/G104 & evaluate_102gate_preflight / evaluate_104gate_preflight intact
        self.assertTrue(callable(fx3_safety.evaluate_102gate_preflight))
        self.assertTrue(callable(fx3_safety.evaluate_104gate_preflight))
        self.assertEqual(fx3_safety.G103, fx3_safety.G103_GATE_ID)
        self.assertEqual(fx3_safety.G104, fx3_safety.G104_GATE_ID)

    def test_03_pinned_phase266_donor_specs_cover_fx3_and_fx6_contracts(self) -> None:
        self.assertEqual(len(PINNED_PHASE266_DONOR_SPECS), 6)
        bodies = {spec[0] for spec in PINNED_PHASE266_DONOR_SPECS.values()}
        self.assertEqual(bodies, {"FX3", "FX6"})
        self.assertLessEqual(DONOR_CHECK_MAX_SECONDS_PHASE266, 0.10)

    def test_04_donor_audit_active_mode_within_100ms_and_zero_leaked_bytes(
        self,
    ) -> None:
        audit = audit_phase266_donor_contracts()
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
        audit = audit_phase266_donor_contracts(force_clean_room=True)
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
        for env_key in ("FX3_FX6_FORCE_CLEAN_ROOM", ENV_CLEAN_ROOM_TEST_PHASE266):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                audit = audit_phase266_donor_contracts()
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_missing_work_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = audit_phase266_donor_contracts(
                work_root=Path(tmp) / "nonexistent", force_clean_room=False
            )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_08_donor_audit_corrupted_sha256_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, _sz, _sha, markers, _lbl) in (
                PINNED_PHASE266_DONOR_SPECS.items()
            ):
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"".join(markers) + b"corrupt")
            audit = audit_phase266_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE266_DONOR_INTEGRITY)

    def test_09_donor_audit_missing_byte_marker_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, exp_sz, _sha, _markers, _lbl) in (
                PINNED_PHASE266_DONOR_SPECS.items()
            ):
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"X" * min(exp_sz, 256))
            audit = audit_phase266_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE266_DONOR_INTEGRITY)

    def test_10_donor_audit_budget_exceeded_blocks_fail_closed(self) -> None:
        audit = audit_phase266_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        self.assertFalse(audit.valid)
        self.assertFalse(audit.within_budget_100ms)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE266_DONOR_INTEGRITY)

    def test_11_read_file_o_rdonly_reads_exact_bytes(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"FX3_PHASE266_ORDONLY")
            tmp_path = Path(tf.name)
        try:
            self.assertEqual(_read_file_o_rdonly(tmp_path), b"FX3_PHASE266_ORDONLY")
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_12_normalization_helpers_accept_canonical_and_reject_invalid(self) -> None:
        self.assertEqual(_parse_fw_tuple("Ver. 7.02"), (7, 2))
        self.assertEqual(_parse_fw_tuple("v2.00"), (2, 0))
        self.assertIsNone(_parse_fw_tuple("invalid"))
        self.assertEqual(
            _norm_reset_action_phase266("[Camera Settings Reset]"),
            RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertEqual(
            _norm_reset_action_phase266("Reset Network Set."),
            RESET_ACTION_RESET_NETWORK_SET_PHASE266,
        )
        self.assertIsNone(_norm_reset_action_phase266("Factory Wipe"))
        self.assertEqual(_norm_on_off_phase266("[On]"), "On")
        self.assertEqual(_norm_on_off_phase266("OFF"), "Off")
        self.assertIsNone(_norm_on_off_phase266("Maybe"))
        self.assertEqual(_norm_enable_disable_g105("[Enable]"), RELEASE_ENABLE_G105)
        self.assertEqual(_norm_enable_disable_g105("disable"), RELEASE_DISABLE_G105)
        self.assertIsNone(_norm_enable_disable_g105("Auto"))
        self.assertEqual(_norm_capture_mode_g105("Still Image"), CAPTURE_MODE_STILL_G105)
        self.assertEqual(_norm_capture_mode_g105("S&Q Motion"), CAPTURE_MODE_SQ_G105)
        self.assertIsNone(_norm_capture_mode_g105("Time-lapse"))
        self.assertEqual(
            _norm_bench_posture_g105("production"), BENCH_POSTURE_PRODUCTION_SHOOT_G105
        )
        self.assertEqual(
            _norm_lens_mount_state_g105("PL_ADAPTER"),
            LENS_MOUNT_PL_MECHANICAL_ADAPTER_G105,
        )
        self.assertEqual(
            _norm_audio_out_timing_g105("Lip Sync"), AUDIO_OUT_TIMING_LIP_SYNC_G105
        )
        self.assertEqual(
            _norm_shoe_audio_set_g105("48kHz/24bit 4ch"), SHOE_AUDIO_48K_24B_4CH_G105
        )
        self.assertEqual(
            _norm_target_container_g106("HEIF"), CONTAINER_STILL_HEIF_G106
        )

    # ------------------------------------------------------------------
    # Section B: Gate G105 — Release w/o Card & w/o Lens + Ver. 7.02 Audio/DISP (13..34)
    # ------------------------------------------------------------------

    def test_13_exhaustive_96_state_release_wo_card_and_lens_scope_matrix(self) -> None:
        matrix = compute_release_wo_card_and_lens_scope_matrix()
        self.assertEqual(matrix["states_checked"], 96)
        self.assertEqual(matrix["movie_cardless_internal_rec_bypass_events"], 0)
        self.assertEqual(matrix["cardless_still_enabled_count"], 6)
        self.assertEqual(matrix["cardless_still_blocked_count"], 6)
        self.assertEqual(matrix["lensless_blocked_across_all_modes_count"], 24)

    def test_14_g105_default_cardless_body_only_bench_passes_cleanly(self) -> None:
        res = verify_release_wo_card_lens_and_v702_audio_disp_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G105)
        self.assertEqual(res.release_wo_card_menu_path, RELEASE_WO_CARD_MENU_PATH_G105)
        self.assertEqual(res.release_wo_lens_menu_path, RELEASE_WO_LENS_MENU_PATH_G105)
        self.assertTrue(res.cardless_bench_active)
        self.assertTrue(res.still_shutter_release_allowed)
        self.assertFalse(res.still_image_saved_to_card)
        self.assertEqual(res.cardless_media_sector_writes, 0)
        self.assertEqual(res.e_nd_actuator_tx_count, 0)
        self.assertEqual(res.emount_lens_uart_tx_bytes, 0)
        self.assertEqual(res.release_scope_matrix_states_checked, 96)
        self.assertTrue(res.v702_audio_menu_exact_5_items_verified)
        self.assertEqual(res.legacy_v1_audio_level_menu_spoof_events, 0)
        self.assertTrue(res.effective_audio_meter_visible)
        self.assertEqual(res.effective_audio_meter_channels, 2)
        self.assertIsInstance(res.to_dict(), dict)

    def test_15_g105_release_wo_card_disable_blocks_cardless_still_release(
        self,
    ) -> None:
        res = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            pre_reset_release_wo_card=RELEASE_DISABLE_G105,
            slot1_card_inserted=False,
            slot2_card_inserted=False,
            capture_mode=CAPTURE_MODE_STILL_G105,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.still_shutter_release_allowed)
        self.assertFalse(res.still_image_saved_to_card)
        self.assertFalse(res.effective_release_permitted)

    def test_16_g105_production_shoot_requires_release_wo_card_disable(self) -> None:
        blocked = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            bench_posture=BENCH_POSTURE_PRODUCTION_SHOOT_G105,
            pre_reset_release_wo_card=RELEASE_ENABLE_G105,
            slot1_card_inserted=True,
        )
        self.assertFalse(blocked.valid)
        self.assertEqual(
            blocked.status,
            STATUS_BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION,
        )

        safe = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            bench_posture=BENCH_POSTURE_PRODUCTION_SHOOT_G105,
            pre_reset_release_wo_card=RELEASE_DISABLE_G105,
            slot1_card_inserted=True,
        )
        self.assertTrue(safe.valid)
        self.assertTrue(safe.still_shutter_release_allowed)
        self.assertTrue(safe.still_image_saved_to_card)

    def test_17_g105_cardless_diagnostic_bench_rejects_inserted_card_or_sector_writes(
        self,
    ) -> None:
        with_card = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            bench_posture=BENCH_POSTURE_CARDLESS_DIAGNOSTIC_G105,
            slot1_card_inserted=True,
        )
        self.assertFalse(with_card.valid)
        self.assertEqual(
            with_card.status,
            STATUS_BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION,
        )

        with_writes = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            claimed_cardless_media_sector_writes=4,
        )
        self.assertFalse(with_writes.valid)
        self.assertEqual(
            with_writes.status,
            STATUS_BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION,
        )

    def test_18_g105_movie_internal_recording_blocked_when_both_slots_empty_even_if_release_wo_card_enable(
        self,
    ) -> None:
        res = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            capture_mode=CAPTURE_MODE_MOVIE_G105,
            pre_reset_release_wo_card=RELEASE_ENABLE_G105,
            slot1_card_inserted=False,
            slot2_card_inserted=False,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.movie_internal_rec_allowed)
        self.assertFalse(res.external_hdmi_rec_allowed)
        self.assertFalse(res.effective_release_permitted)

        bypass = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            capture_mode=CAPTURE_MODE_MOVIE_G105,
            pre_reset_release_wo_card=RELEASE_ENABLE_G105,
            slot1_card_inserted=False,
            slot2_card_inserted=False,
            claimed_movie_internal_rec_allowed=True,
        )
        self.assertFalse(bypass.valid)
        self.assertEqual(
            bypass.status,
            STATUS_BLOCKED_G105_MOVIE_CARDLESS_INTERNAL_REC_BYPASS_VIOLATION,
        )
        self.assertGreaterEqual(bypass.movie_cardless_internal_rec_bypass_events, 1)

    def test_19_g105_external_hdmi_capture_governed_by_rec_media_dur_hdmi_output(
        self,
    ) -> None:
        # Cardless bench + external HDMI recorder connected -> internal blocked, external allowed
        ext_only_cardless = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            capture_mode=CAPTURE_MODE_MOVIE_G105,
            slot1_card_inserted=False,
            slot2_card_inserted=False,
            hdmi_external_capture_connected=True,
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_G105,
        )
        self.assertTrue(ext_only_cardless.valid)
        self.assertFalse(ext_only_cardless.movie_internal_rec_allowed)
        self.assertTrue(ext_only_cardless.external_hdmi_rec_allowed)
        self.assertTrue(ext_only_cardless.effective_release_permitted)

        # Production card inserted + HDMI connected + Rec. Media dur HDMI Output = Off -> internal inhibited
        inhibited = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            bench_posture=BENCH_POSTURE_PRODUCTION_SHOOT_G105,
            pre_reset_release_wo_card=RELEASE_DISABLE_G105,
            capture_mode=CAPTURE_MODE_MOVIE_G105,
            slot2_card_inserted=True,
            hdmi_external_capture_connected=True,
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_G105,
        )
        self.assertTrue(inhibited.valid)
        self.assertFalse(inhibited.movie_internal_rec_allowed)
        self.assertTrue(inhibited.external_hdmi_rec_allowed)

        # Production card inserted + HDMI connected + Rec. Media dur HDMI Output = On -> both allowed
        simult = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            bench_posture=BENCH_POSTURE_PRODUCTION_SHOOT_G105,
            pre_reset_release_wo_card=RELEASE_DISABLE_G105,
            capture_mode=CAPTURE_MODE_MOVIE_G105,
            slot2_card_inserted=True,
            hdmi_external_capture_connected=True,
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_ON_G105,
        )
        self.assertTrue(simult.valid)
        self.assertTrue(simult.movie_internal_rec_allowed)
        self.assertTrue(simult.external_hdmi_rec_allowed)

    def test_20_g105_release_wo_lens_disable_blocks_still_movie_and_sq_without_electronic_lens(
        self,
    ) -> None:
        for mode in ALLOWED_CAPTURE_MODES_G105:
            res = verify_release_wo_card_lens_and_v702_audio_disp_guard(
                bench_posture=BENCH_POSTURE_PRODUCTION_SHOOT_G105,
                pre_reset_release_wo_card=RELEASE_DISABLE_G105,
                slot1_card_inserted=True,
                capture_mode=mode,
                lens_mount_state=LENS_MOUNT_PL_MECHANICAL_ADAPTER_G105,
                pre_reset_release_wo_lens=RELEASE_DISABLE_G105,
                hdmi_external_capture_connected=True,
                rec_media_dur_hdmi_output=HDMI_REC_MEDIA_ON_G105,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.lens_gate_permits_release)
            self.assertFalse(res.effective_release_permitted)

    def test_21_g105_electronic_emount_lens_permits_release_even_when_release_wo_lens_disable(
        self,
    ) -> None:
        res = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            bench_posture=BENCH_POSTURE_PRODUCTION_SHOOT_G105,
            pre_reset_release_wo_card=RELEASE_DISABLE_G105,
            slot1_card_inserted=True,
            capture_mode=CAPTURE_MODE_MOVIE_G105,
            lens_mount_state=LENS_MOUNT_ELECTRONIC_EMOUNT_G105,
            pre_reset_release_wo_lens=RELEASE_DISABLE_G105,
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_ON_G105,
            claimed_emount_lens_uart_tx_bytes=64,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.electronic_emount_lens_attached)
        self.assertTrue(res.lens_gate_permits_release)
        self.assertTrue(res.movie_internal_rec_allowed)

    def test_22_g105_blocks_any_end_actuator_tx_or_body_only_lens_uart_traffic(
        self,
    ) -> None:
        end_spoof = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            claimed_e_nd_actuator_tx_count=1
        )
        self.assertFalse(end_spoof.valid)
        self.assertEqual(
            end_spoof.status, STATUS_BLOCKED_G105_RELEASE_WO_LENS_OR_END_UART_VIOLATION
        )

        uart_leak = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            lens_mount_state=LENS_MOUNT_BODY_ONLY_BENCH_G105,
            claimed_emount_lens_uart_tx_bytes=12,
        )
        self.assertFalse(uart_leak.valid)
        self.assertEqual(
            uart_leak.status, STATUS_BLOCKED_G105_RELEASE_WO_LENS_OR_END_UART_VIOLATION
        )

    def test_23_g105_claimed_still_or_lens_release_contradiction_blocks(self) -> None:
        bad_still = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            pre_reset_release_wo_card=RELEASE_DISABLE_G105,
            claimed_still_shutter_release_allowed=True,
        )
        self.assertFalse(bad_still.valid)
        self.assertEqual(
            bad_still.status,
            STATUS_BLOCKED_G105_RELEASE_WO_CARD_SCOPE_OR_PRODUCTION_VIOLATION,
        )

        bad_lens = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            pre_reset_release_wo_lens=RELEASE_DISABLE_G105,
            lens_mount_state=LENS_MOUNT_BODY_ONLY_BENCH_G105,
            claimed_lens_gate_permits_release=True,
        )
        self.assertFalse(bad_lens.valid)
        self.assertEqual(
            bad_lens.status, STATUS_BLOCKED_G105_RELEASE_WO_LENS_OR_END_UART_VIOLATION
        )

    def test_24_g105_v702_audio_recording_exact_5_items_verified(self) -> None:
        self.assertEqual(
            V702_AUDIO_RECORDING_EXACT_5_ITEMS_G105,
            (
                "Audio Recording",
                "Audio Rec Level",
                "Audio Out Timing",
                "Wind Noise Reduct.",
                "Shoe Audio Set.",
            ),
        )
        res = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            pre_reset_audio_rec_level=0,
            pre_reset_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC_G105,
            pre_reset_wind_noise_reduct=WIND_NOISE_REDUCT_ON_G105,
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24B_2CH_G105,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_audio_rec_level, 0)
        self.assertEqual(
            res.effective_post_reset_audio_out_timing, AUDIO_OUT_TIMING_LIP_SYNC_G105
        )
        self.assertEqual(
            res.effective_post_reset_wind_noise_reduct, WIND_NOISE_REDUCT_ON_G105
        )

    def test_25_g105_blocks_legacy_v1_standalone_audio_level_display_menu_item(
        self,
    ) -> None:
        for spoof_item in DISALLOWED_V1_AUDIO_MENU_ITEMS_G105:
            res = verify_release_wo_card_lens_and_v702_audio_disp_guard(
                audio_recording_menu_items=list(V702_AUDIO_RECORDING_EXACT_5_ITEMS_G105)
                + [spoof_item]
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G105_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_VIOLATION,
            )
            self.assertGreaterEqual(res.legacy_v1_audio_level_menu_spoof_events, 1)

    def test_26_g105_blocks_legacy_v1_ilc2035_or_pre_v200_firmware(self) -> None:
        v1_guide = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            help_guide_code=FX3_LEGACY_V1_HELP_GUIDE_CODE_G105
        )
        self.assertFalse(v1_guide.valid)
        self.assertEqual(
            v1_guide.status,
            STATUS_BLOCKED_G105_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_VIOLATION,
        )

        v1_fw = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            firmware_version="1.01"
        )
        self.assertFalse(v1_fw.valid)
        self.assertEqual(
            v1_fw.status, STATUS_BLOCKED_G105_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_VIOLATION
        )

    def test_27_g105_disp_screen_disp_set_governs_2ch_and_4ch_audio_meter(self) -> None:
        # Unchecked in DISP (Screen Disp) Set -> hidden
        hidden = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            pre_reset_disp_audio_level_checked=False
        )
        self.assertTrue(hidden.valid)
        self.assertFalse(hidden.effective_audio_meter_visible)
        self.assertEqual(hidden.effective_audio_meter_channels, 0)

        # Checked + 48kHz/24bit 4ch + digital MI-shoe 4ch -> 4ch meter
        meter_4ch = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            pre_reset_disp_audio_level_checked=True,
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24B_4CH_G105,
            digital_mi_shoe_4ch_attached=True,
        )
        self.assertTrue(meter_4ch.valid)
        self.assertTrue(meter_4ch.effective_audio_meter_visible)
        self.assertEqual(meter_4ch.effective_audio_meter_channels, 4)

        # Checked + 48kHz/24bit 4ch WITHOUT digital MI-shoe 4ch -> 2ch fallback
        meter_2ch = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            pre_reset_disp_audio_level_checked=True,
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24B_4CH_G105,
            digital_mi_shoe_4ch_attached=False,
        )
        self.assertTrue(meter_2ch.valid)
        self.assertEqual(meter_2ch.effective_audio_meter_channels, 2)

    def test_28_g105_audio_meter_suppressed_in_sq_and_when_audio_recording_off(
        self,
    ) -> None:
        sq = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            capture_mode=CAPTURE_MODE_SQ_G105,
            pre_reset_disp_audio_level_checked=True,
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24B_4CH_G105,
            digital_mi_shoe_4ch_attached=True,
        )
        self.assertTrue(sq.valid)
        self.assertTrue(sq.sq_audio_meter_suppressed)
        self.assertFalse(sq.effective_audio_meter_visible)
        self.assertEqual(sq.effective_audio_meter_channels, 0)

        audio_off = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            capture_mode=CAPTURE_MODE_MOVIE_G105,
            pre_reset_audio_recording=AUDIO_RECORDING_OFF_G105,
            pre_reset_disp_audio_level_checked=True,
        )
        self.assertTrue(audio_off.valid)
        self.assertFalse(audio_off.effective_audio_meter_visible)
        self.assertEqual(audio_off.effective_audio_meter_channels, 0)

    def test_29_g105_blocks_claimed_audio_meter_visibility_or_channel_mismatch(
        self,
    ) -> None:
        sq_spoof = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            capture_mode=CAPTURE_MODE_SQ_G105,
            claimed_audio_meter_visible=True,
        )
        self.assertFalse(sq_spoof.valid)
        self.assertEqual(
            sq_spoof.status,
            STATUS_BLOCKED_G105_DISP_AUDIO_METER_OR_SQ_SUPPRESSION_VIOLATION,
        )

        ch_spoof = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            claimed_audio_meter_channels=4
        )
        self.assertFalse(ch_spoof.valid)
        self.assertEqual(
            ch_spoof.status,
            STATUS_BLOCKED_G105_DISP_AUDIO_METER_OR_SQ_SUPPRESSION_VIOLATION,
        )

    def test_30_g105_reset_persistence_split_camera_settings_reset_vs_initialize(
        self,
    ) -> None:
        cam_reset = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            bench_posture=BENCH_POSTURE_PRODUCTION_SHOOT_G105,
            slot1_card_inserted=True,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_release_wo_card=RELEASE_DISABLE_G105,
            pre_reset_release_wo_lens=RELEASE_DISABLE_G105,
            pre_reset_audio_rec_level=12,
            pre_reset_disp_audio_level_checked=False,
        )
        self.assertTrue(cam_reset.valid)
        self.assertEqual(
            cam_reset.effective_post_reset_release_wo_card, RELEASE_DISABLE_G105
        )
        self.assertEqual(
            cam_reset.effective_post_reset_release_wo_lens, RELEASE_DISABLE_G105
        )
        self.assertEqual(
            cam_reset.effective_post_reset_audio_rec_level,
            AUDIO_REC_LEVEL_FACTORY_DEFAULT_G105,
        )
        self.assertFalse(cam_reset.effective_post_reset_disp_audio_level_checked)

        init_reset = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            reset_action=RESET_ACTION_INITIALIZE,
            pre_reset_release_wo_card=RELEASE_DISABLE_G105,
            pre_reset_release_wo_lens=RELEASE_DISABLE_G105,
            pre_reset_audio_rec_level=5,
            pre_reset_disp_audio_level_checked=False,
        )
        self.assertTrue(init_reset.valid)
        self.assertEqual(
            init_reset.effective_post_reset_release_wo_card, RELEASE_ENABLE_G105
        )
        self.assertEqual(
            init_reset.effective_post_reset_release_wo_lens, RELEASE_ENABLE_G105
        )
        self.assertTrue(init_reset.effective_post_reset_disp_audio_level_checked)

    def test_31_g105_reset_network_set_leaves_all_shooting_and_disp_items_intact(
        self,
    ) -> None:
        net_reset = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE266,
            pre_reset_audio_rec_level=31,
            pre_reset_disp_audio_level_checked=False,
        )
        self.assertTrue(net_reset.valid)
        self.assertEqual(net_reset.effective_post_reset_audio_rec_level, 31)
        self.assertFalse(net_reset.effective_post_reset_disp_audio_level_checked)

    def test_32_g105_blocks_post_reset_persistence_drift(self) -> None:
        drift = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_release_wo_card=RELEASE_DISABLE_G105,
            bench_posture=BENCH_POSTURE_PRODUCTION_SHOOT_G105,
            slot1_card_inserted=True,
            claimed_post_reset_release_wo_card=RELEASE_ENABLE_G105,
        )
        self.assertFalse(drift.valid)
        self.assertEqual(drift.status, STATUS_BLOCKED_G105_RESET_PERSISTENCE_VIOLATION)

    def test_33_g105_blocks_invalid_audio_rec_level_or_body_model_telemetry(
        self,
    ) -> None:
        out_of_range = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            pre_reset_audio_rec_level=32
        )
        self.assertFalse(out_of_range.valid)
        self.assertEqual(out_of_range.status, STATUS_BLOCKED_G105_TELEMETRY_INVALID)

        wrong_model = verify_release_wo_card_lens_and_v702_audio_disp_guard(
            body_model_name=FX6_MODEL_NAME
        )
        self.assertFalse(wrong_model.valid)
        self.assertEqual(wrong_model.status, STATUS_BLOCKED_G105_TELEMETRY_INVALID)

    def test_34_evaluate_g105_blocks_persistent_emmc_write_request_and_supports_clean_room(
        self,
    ) -> None:
        verdict_clean, res_clean = (
            evaluate_g105_release_wo_card_lens_and_v702_audio_disp_guard(
                force_clean_room=True
            )
        )
        self.assertTrue(verdict_clean.passed)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIsInstance(res_clean.to_dict(), dict)

        verdict_blk, res_blk = (
            evaluate_g105_release_wo_card_lens_and_v702_audio_disp_guard(
                force_clean_room=True, request_persistent_emmc_writes=True
            )
        )
        self.assertFalse(verdict_blk.passed)
        self.assertEqual(verdict_blk.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_blk.valid)

    # ------------------------------------------------------------------
    # Section C: Gate G106 — Copyright Info 46-Char Still EXIF & PII Hygiene (35..54)
    # ------------------------------------------------------------------

    def test_35_g106_default_clean_room_bench_hygiene_passes_with_zero_pii_leaked(
        self,
    ) -> None:
        res = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G106)
        self.assertEqual(res.copyright_info_menu_path, COPYRIGHT_INFO_MENU_PATH_G106)
        self.assertEqual(
            res.copyright_info_subitems, COPYRIGHT_INFO_EXACT_4_SUBITEMS_G106
        )
        self.assertEqual(res.copyright_max_chars, 46)
        self.assertEqual(
            res.effective_post_reset_write_copyright_info, WRITE_COPYRIGHT_INFO_OFF_G106
        )
        self.assertEqual(res.photographer_copyright_pii_leaked_bytes, 0)
        self.assertEqual(res.movie_or_raw_exif_mutation_bytes, 0)
        self.assertEqual(res.slot1_recovery_vault_mutation_bytes, 0)
        self.assertTrue(res.excluded_from_camset_saveload)
        self.assertIsInstance(res.to_dict(), dict)

    def test_36_g106_exact_46_char_printable_ascii_accepted_in_customer_still_exif_mode(
        self,
    ) -> None:
        p46 = "A" * 46
        c46 = "(C) 2026 SONY FX3 CINEMA LAB UNIT 0123456789AB"
        self.assertEqual(len(c46), 46)
        self.assertTrue(_is_valid_46char_printable_ascii_g106(p46))
        self.assertTrue(_is_valid_46char_printable_ascii_g106(c46))

        res = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=False,
            pre_reset_write_copyright_info=WRITE_COPYRIGHT_INFO_ON_G106,
            pre_reset_photographer=p46,
            pre_reset_copyright=c46,
            target_container=CONTAINER_STILL_JPEG_G106,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.photographer_char_length, 46)
        self.assertEqual(res.copyright_char_length, 46)
        self.assertTrue(res.still_exif_tags_written)
        self.assertEqual(res.exif_artist_tag_hex, EXIF_TAG_ARTIST_HEX_G106)
        self.assertEqual(res.exif_copyright_tag_hex, EXIF_TAG_COPYRIGHT_HEX_G106)

    def test_37_g106_blocks_47_char_photographer_or_copyright_overflow(self) -> None:
        over_photo = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=False,
            pre_reset_photographer="P" * 47,
        )
        self.assertFalse(over_photo.valid)
        self.assertEqual(
            over_photo.status,
            STATUS_BLOCKED_G106_COPYRIGHT_46CHAR_OR_ASCII_BOUND_VIOLATION,
        )

        over_copy = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=False,
            pre_reset_copyright="C" * 47,
        )
        self.assertFalse(over_copy.valid)
        self.assertEqual(
            over_copy.status,
            STATUS_BLOCKED_G106_COPYRIGHT_46CHAR_OR_ASCII_BOUND_VIOLATION,
        )

    def test_38_g106_blocks_non_printable_ascii_or_multibyte_utf8_bytes(self) -> None:
        nul_byte = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=False,
            pre_reset_photographer="LAB\x00USER",
        )
        self.assertFalse(nul_byte.valid)
        self.assertEqual(
            nul_byte.status,
            STATUS_BLOCKED_G106_COPYRIGHT_46CHAR_OR_ASCII_BOUND_VIOLATION,
        )

        non_ascii = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=False,
            pre_reset_copyright="© 2026 FX3",
        )
        self.assertFalse(non_ascii.valid)
        self.assertEqual(
            non_ascii.status,
            STATUS_BLOCKED_G106_COPYRIGHT_46CHAR_OR_ASCII_BOUND_VIOLATION,
        )

    def test_39_g106_still_jpeg_heif_arw_write_exif_when_enabled_but_movies_never_do(
        self,
    ) -> None:
        for still_c in STILL_EXIF_ELIGIBLE_CONTAINERS_G106:
            res = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
                clean_room_bench_hygiene_required=False,
                pre_reset_write_copyright_info=WRITE_COPYRIGHT_INFO_ON_G106,
                pre_reset_photographer="SYNTHETIC UNIT",
                target_container=still_c,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.is_still_exif_container)
            self.assertTrue(res.still_exif_tags_written)

        for mv_c in MOVIE_AND_RAW_CONTAINERS_G106:
            res = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
                clean_room_bench_hygiene_required=False,
                pre_reset_write_copyright_info=WRITE_COPYRIGHT_INFO_ON_G106,
                pre_reset_photographer="SYNTHETIC UNIT",
                target_container=mv_c,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.is_still_exif_container)
            self.assertFalse(res.still_exif_tags_written)
            self.assertEqual(res.movie_or_raw_exif_mutation_bytes, 0)

    def test_40_g106_blocks_movie_stream_exif_mutation_or_slot1_vault_mutation(
        self,
    ) -> None:
        mv_mut = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            target_container=CONTAINER_MOVIE_XAVC_SI_MP4_G106,
            claimed_movie_or_raw_exif_mutation_bytes=128,
        )
        self.assertFalse(mv_mut.valid)
        self.assertEqual(
            mv_mut.status,
            STATUS_BLOCKED_G106_MOVIE_STREAM_OR_SLOT1_VAULT_MUTATION_VIOLATION,
        )

        slot1_mut = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            claimed_slot1_recovery_vault_mutation_bytes=512
        )
        self.assertFalse(slot1_mut.valid)
        self.assertEqual(
            slot1_mut.status,
            STATUS_BLOCKED_G106_MOVIE_STREAM_OR_SLOT1_VAULT_MUTATION_VIOLATION,
        )

    def test_41_g106_disp_copyright_info_must_remain_strictly_readonly(self) -> None:
        disp_mut = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            disp_copyright_info_readonly=False,
            claimed_disp_copyright_info_media_writes=1,
        )
        self.assertFalse(disp_mut.valid)
        self.assertEqual(
            disp_mut.status,
            STATUS_BLOCKED_G106_MOVIE_STREAM_OR_SLOT1_VAULT_MUTATION_VIOLATION,
        )

    def test_42_g106_strings_survive_camera_settings_reset_while_write_flag_resets_off(
        self,
    ) -> None:
        res = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=False,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_write_copyright_info=WRITE_COPYRIGHT_INFO_ON_G106,
            pre_reset_photographer="UNIT LAB A",
            pre_reset_copyright="SONY LAB 2026",
        )
        self.assertTrue(res.valid)
        self.assertEqual(
            res.effective_post_reset_write_copyright_info, WRITE_COPYRIGHT_INFO_OFF_G106
        )
        self.assertEqual(res.effective_post_reset_photographer, "UNIT LAB A")
        self.assertEqual(res.effective_post_reset_copyright, "SONY LAB 2026")
        self.assertFalse(res.still_exif_tags_written)

    def test_43_g106_initialize_wipes_photographer_and_copyright_strings_clean_for_bench(
        self,
    ) -> None:
        # Even if operator left strings & Write=On prior to Initialize, Initialize wipes them clean!
        res = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=True,
            reset_action=RESET_ACTION_INITIALIZE,
            pre_reset_write_copyright_info=WRITE_COPYRIGHT_INFO_ON_G106,
            pre_reset_photographer="OLD OPERATOR",
            pre_reset_copyright="OLD STUDIO",
        )
        self.assertTrue(res.valid)
        self.assertEqual(
            res.effective_post_reset_write_copyright_info, WRITE_COPYRIGHT_INFO_OFF_G106
        )
        self.assertEqual(res.effective_post_reset_photographer, "")
        self.assertEqual(res.effective_post_reset_copyright, "")
        self.assertEqual(res.photographer_copyright_pii_leaked_bytes, 0)

    def test_44_g106_reset_network_set_preserves_write_flag_and_strings(self) -> None:
        res = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=False,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE266,
            pre_reset_write_copyright_info=WRITE_COPYRIGHT_INFO_ON_G106,
            pre_reset_photographer="NET RESET KEEP",
            pre_reset_copyright="KEEP 2026",
        )
        self.assertTrue(res.valid)
        self.assertEqual(
            res.effective_post_reset_write_copyright_info, WRITE_COPYRIGHT_INFO_ON_G106
        )
        self.assertEqual(res.effective_post_reset_photographer, "NET RESET KEEP")
        self.assertEqual(res.effective_post_reset_copyright, "KEEP 2026")

    def test_45_g106_blocks_reset_survival_contradiction_or_camset_export_leak(
        self,
    ) -> None:
        wiped_wrongly = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=False,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_photographer="SURVIVES RESET",
            claimed_post_reset_photographer="",
        )
        self.assertFalse(wiped_wrongly.valid)
        self.assertEqual(
            wiped_wrongly.status,
            STATUS_BLOCKED_G106_RESET_SURVIVAL_OR_INITIALIZE_WIPE_VIOLATION,
        )

        survived_init = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            reset_action=RESET_ACTION_INITIALIZE,
            pre_reset_copyright="MUST WIPE",
            claimed_post_reset_copyright="MUST WIPE",
        )
        self.assertFalse(survived_init.valid)
        self.assertEqual(
            survived_init.status,
            STATUS_BLOCKED_G106_RESET_SURVIVAL_OR_INITIALIZE_WIPE_VIOLATION,
        )

        camset_leak = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            claimed_camset_copyright_export_bytes=46
        )
        self.assertFalse(camset_leak.valid)
        self.assertEqual(
            camset_leak.status,
            STATUS_BLOCKED_G106_RESET_SURVIVAL_OR_INITIALIZE_WIPE_VIOLATION,
        )

    def test_46_g106_clean_room_bench_blocks_write_on_or_residual_operator_pii(
        self,
    ) -> None:
        write_on_bench = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=True,
            pre_reset_write_copyright_info=WRITE_COPYRIGHT_INFO_ON_G106,
        )
        self.assertFalse(write_on_bench.valid)
        self.assertEqual(
            write_on_bench.status, STATUS_BLOCKED_G106_BENCH_PII_HYGIENE_LEAK_VIOLATION
        )
        self.assertGreaterEqual(
            write_on_bench.photographer_copyright_pii_leaked_bytes, 1
        )

        residual_pii = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            clean_room_bench_hygiene_required=True,
            pre_reset_write_copyright_info=WRITE_COPYRIGHT_INFO_OFF_G106,
            pre_reset_photographer="JANE DOE",
        )
        self.assertFalse(residual_pii.valid)
        self.assertEqual(
            residual_pii.status, STATUS_BLOCKED_G106_BENCH_PII_HYGIENE_LEAK_VIOLATION
        )
        self.assertEqual(residual_pii.photographer_copyright_pii_leaked_bytes, 8)

    def test_47_g106_blocks_claimed_pii_leaked_bytes_on_bench(self) -> None:
        leaked = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            claimed_photographer_copyright_pii_leaked_bytes=16
        )
        self.assertFalse(leaked.valid)
        self.assertEqual(
            leaked.status, STATUS_BLOCKED_G106_BENCH_PII_HYGIENE_LEAK_VIOLATION
        )

    def test_48_g106_blocks_invalid_subitems_container_or_model_telemetry(self) -> None:
        bad_sub = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            copyright_info_subitems=("Write Copyright Info", "Set Photographer")
        )
        self.assertFalse(bad_sub.valid)
        self.assertEqual(bad_sub.status, STATUS_BLOCKED_G106_TELEMETRY_INVALID)

        bad_cont = verify_copyright_info_46char_still_exif_and_pii_hygiene_guard(
            target_container="UNKNOWN_CONTAINER"
        )
        self.assertFalse(bad_cont.valid)
        self.assertEqual(bad_cont.status, STATUS_BLOCKED_G106_TELEMETRY_INVALID)

    def test_49_evaluate_g106_blocks_persistent_emmc_write_request_and_supports_clean_room(
        self,
    ) -> None:
        verdict_clean, res_clean = (
            evaluate_g106_copyright_info_46char_still_exif_and_pii_hygiene_guard(
                force_clean_room=True
            )
        )
        self.assertTrue(verdict_clean.passed)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIsInstance(res_clean.to_dict(), dict)

        verdict_blk, res_blk = (
            evaluate_g106_copyright_info_46char_still_exif_and_pii_hygiene_guard(
                force_clean_room=True, request_persistent_emmc_writes=True
            )
        )
        self.assertFalse(verdict_blk.passed)
        self.assertEqual(verdict_blk.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_blk.valid)

    def test_50_resolvers_handle_default_and_fallback_inputs_deterministically(
        self,
    ) -> None:
        s105 = resolve_fx3_release_wo_card_lens_and_v702_audio_disp_state()
        self.assertTrue(s105["fw_is_v2_or_later"])
        self.assertEqual(s105["effective_audio_meter_channels"], 2)
        s106 = resolve_fx3_copyright_info_46char_still_exif_state()
        self.assertEqual(s106["bench_pii_leaked_bytes"], 0)
        self.assertFalse(s106["still_exif_tags_written"])

    # ------------------------------------------------------------------
    # Section D: Unified 106-Gate Master Preflight & CLI Subcommands (51..70)
    # ------------------------------------------------------------------

    def test_51_master_106gate_offline_active_mode_verifies_103_of_106_gates(
        self,
    ) -> None:
        r = self.active_offline_106
        self.assertEqual(
            r.schema, REALHW_RELEASE_WO_CARD_AUDIO_METER_COPYRIGHT_106GATE_SCHEMA
        )
        self.assertEqual(r.summary["total_gates"], 106)
        self.assertEqual(r.summary["verified_gates"], 103)
        self.assertEqual(r.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(r.summary["g01_to_g12_verified"], 9)
        self.assertEqual(r.summary["g13_to_g104_verified"], 92)
        self.assertEqual(r.summary["g105_to_g106_verified"], 2)
        self.assertTrue(r.offline_103_gates_verified)
        self.assertFalse(r.all_106_gates_verified)
        self.assertTrue(r.g13_to_g106_all_passed)
        self.assertTrue(r.g105_to_g106_all_passed)
        self.assertEqual(r.status, "VERIFIED_103_OF_106_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(r.gates), 106)

    def test_52_master_106gate_offline_clean_room_verifies_103_of_106_gates(
        self,
    ) -> None:
        r = self.clean_offline_106
        self.assertEqual(r.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r.clean_room_forced)
        self.assertEqual(r.summary["verified_gates"], 103)
        self.assertTrue(r.offline_103_gates_verified)
        self.assertFalse(r.all_106_gates_verified)

    def test_53_master_106gate_simulated_dry_run_verifies_all_106_of_106_gates(
        self,
    ) -> None:
        for r in (self.active_dryrun_106, self.clean_dryrun_106):
            self.assertEqual(r.summary["verified_gates"], 106)
            self.assertEqual(r.summary["blocked_or_pending_gates"], 0)
            self.assertTrue(r.all_106_gates_verified)
            self.assertTrue(r.dry_run_rehearsal_only)
            self.assertEqual(
                r.status, "VERIFIED_ALL_106_GATES_DRY_RUN_SIMULATED_BACKUP"
            )

    def test_54_master_106gate_hard_locks_all_hardware_write_and_usb_redlines(
        self,
    ) -> None:
        for r in (
            self.active_offline_106,
            self.clean_offline_106,
            self.active_dryrun_106,
            self.clean_dryrun_106,
        ):
            self.assertFalse(r.overall_ready_for_hardware_attach)
            self.assertFalse(r.hardware_live_attachment_authorized)
            self.assertFalse(r.human_hardware_attach_token)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.persistent_write_release)
            self.assertFalse(r.physical_flash_auto_exec_authorized)
            self.assertTrue(r.agent_auto_flash_blocked)
            self.assertEqual(r.usb_packets_transmitted, 0)
            self.assertEqual(r.physical_usb_packets_emitted, 0)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_55_master_106gate_tier0_receipt_gates_g10_g12_fail_closed_offline(
        self,
    ) -> None:
        g10_to_g12 = self.active_offline_106.gates[9:12]
        self.assertEqual(len(g10_to_g12), 3)
        for gate in g10_to_g12:
            self.assertFalse(gate["passed"])

    def test_56_master_106gate_tail_gates_are_g105_and_g106(self) -> None:
        g105_entry = self.active_offline_106.gates[104]
        g106_entry = self.active_offline_106.gates[105]
        self.assertEqual(g105_entry["gate_id"], G105_GATE_ID)
        self.assertEqual(g105_entry["gate_code"], G105_GATE_CODE)
        self.assertTrue(g105_entry["passed"])
        self.assertEqual(g106_entry["gate_id"], G106_GATE_ID)
        self.assertEqual(g106_entry["gate_code"], G106_GATE_CODE)
        self.assertTrue(g106_entry["passed"])

    def test_57_master_106gate_aliases_point_to_evaluate_106gate_preflight(
        self,
    ) -> None:
        self.assertIs(evaluate_106_master_safety_gates, evaluate_106gate_preflight)
        self.assertIs(run_106_gate_preflight, evaluate_106gate_preflight)

    def test_58_master_106gate_blocks_when_persistent_emmc_writes_requested(
        self,
    ) -> None:
        r = evaluate_106gate_preflight(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
            master_104_override=self.clean_offline_104,
        )
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(r.offline_103_gates_verified)
        self.assertFalse(r.all_106_gates_verified)
        self.assertFalse(r.h0_h1_trial_entry_allowed)

    def test_59_master_106gate_propagates_g105_failure_fail_closed(self) -> None:
        r = evaluate_106gate_preflight(
            force_clean_room=True,
            master_104_override=self.clean_offline_104,
            release_audio_disp_kwargs={"claimed_e_nd_actuator_tx_count": 3},
        )
        self.assertFalse(r.g105_to_g106_all_passed)
        self.assertFalse(r.offline_103_gates_verified)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G105_RELEASE_WO_LENS_OR_END_UART_VIOLATION
        )

    def test_60_master_106gate_propagates_g106_failure_fail_closed(self) -> None:
        r = evaluate_106gate_preflight(
            force_clean_room=True,
            master_104_override=self.clean_offline_104,
            copyright_info_kwargs={
                "pre_reset_write_copyright_info": WRITE_COPYRIGHT_INFO_ON_G106
            },
        )
        self.assertFalse(r.g105_to_g106_all_passed)
        self.assertFalse(r.offline_103_gates_verified)
        self.assertEqual(r.status, STATUS_BLOCKED_G106_BENCH_PII_HYGIENE_LEAK_VIOLATION)

    def test_61_master_106gate_propagates_upstream_g13_to_g104_failure(self) -> None:
        broken_104 = dataclasses.replace(
            self.clean_offline_104,
            g13_to_g104_all_passed=False,
            offline_101_gates_verified=False,
            status="BLOCKED_UPSTREAM_G104_TEST",
        )
        r = evaluate_106gate_preflight(
            force_clean_room=True, master_104_override=broken_104
        )
        self.assertFalse(r.g13_to_g106_all_passed)
        self.assertFalse(r.offline_103_gates_verified)
        self.assertEqual(r.status, "BLOCKED_UPSTREAM_G104_TEST")

    def test_62_master_106gate_propagates_core_g01_g09_failure(self) -> None:
        bad_gates = list(self.clean_offline_104.gates)
        bad_gates[0] = {**bad_gates[0], "passed": False}
        broken_core = dataclasses.replace(
            self.clean_offline_104, gates=tuple(bad_gates)
        )
        r = evaluate_106gate_preflight(
            force_clean_room=True, master_104_override=broken_core
        )
        self.assertFalse(r.offline_103_gates_verified)
        self.assertEqual(r.status, "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING")

    def test_63_master_106gate_json_serializable_roundtrip(self) -> None:
        payload = json.loads(json.dumps(self.clean_offline_106.to_dict()))
        self.assertEqual(
            payload["schema"],
            REALHW_RELEASE_WO_CARD_AUDIO_METER_COPYRIGHT_106GATE_SCHEMA,
        )
        self.assertEqual(payload["summary"]["total_gates"], 106)
        self.assertEqual(len(payload["gates"]), 106)

    def test_64_cli_verify_g105_text_and_json_modes(self) -> None:
        buf_txt = io.StringIO()
        with contextlib.redirect_stdout(buf_txt):
            rc_txt = cli_main(
                ["verify-release-wo-card-lens-audio-disp-guard", "--force-clean-room"]
            )
        self.assertEqual(rc_txt, 0)
        self.assertIn("rel_wo_card=Enable", buf_txt.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = cli_main(
                ["verify-g105-release-wo-card-audio-disp", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["status"], STATUS_VERIFIED_G105)

    def test_65_cli_verify_g106_text_and_json_modes(self) -> None:
        buf_txt = io.StringIO()
        with contextlib.redirect_stdout(buf_txt):
            rc_txt = cli_main(
                ["verify-copyright-info-46char-exif-hygiene-guard", "--force-clean-room"]
            )
        self.assertEqual(rc_txt, 0)
        self.assertIn("write_copyright=Off", buf_txt.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = cli_main(
                ["verify-g106-copyright-info-hygiene", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["status"], STATUS_VERIFIED_G106)

    def test_66_cli_verify_106_gates_offline_text_mode(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_106gate_preflight",
            return_value=self.clean_offline_106,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-106-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=103/106", out)
        self.assertIn("g105_to_g106_all_passed=True", out)
        self.assertIn("usb_packets_transmitted=0", out)

    def test_67_cli_verify_106_gates_simulated_dry_run_json_mode(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_106gate_preflight",
            return_value=self.clean_dryrun_106,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    [
                        "verify-106-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["summary"]["verified_gates"], 106)
        self.assertTrue(parsed["all_106_gates_verified"])

    def test_68_module_main_offline_and_dry_run_exit_codes(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.evaluate_106gate_preflight",
            return_value=self.clean_offline_106,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=103/106", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_release_wo_card_audio_meter_copyright_and_106gate_guard.evaluate_106gate_preflight",
            return_value=self.clean_dryrun_106,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
        self.assertEqual(rc_j, 0)
        self.assertTrue(json.loads(buf_j.getvalue())["all_106_gates_verified"])

    def test_69_allowed_enum_tuples_match_sony_v702_help_guide_spec(self) -> None:
        self.assertEqual(ALLOWED_RELEASE_ENABLE_DISABLE_G105, ("Enable", "Disable"))
        self.assertEqual(ALLOWED_CAPTURE_MODES_G105, ("Still", "Movie", "S&Q"))
        self.assertEqual(ALLOWED_AUDIO_OUT_TIMING_G105, ("Live", "Lip Sync"))
        self.assertEqual(len(ALLOWED_SHOE_AUDIO_SETTINGS_G105), 3)
        self.assertEqual(len(ALLOWED_BENCH_POSTURES_G105), 2)
        self.assertEqual(len(ALLOWED_LENS_MOUNT_STATES_G105), 3)
        self.assertEqual(len(ALLOWED_HDMI_REC_MEDIA_SETTINGS_G105), 2)
        self.assertEqual(len(ALLOWED_RESET_ACTIONS_PHASE266), 4)
        self.assertEqual(len(ALLOWED_TARGET_CONTAINERS_G106), 7)
        self.assertEqual(len(ALLOWED_WRITE_COPYRIGHT_SETTINGS_G106), 2)
        self.assertEqual(AUDIO_REC_LEVEL_MIN_G105, 0)
        self.assertEqual(AUDIO_REC_LEVEL_MAX_G105, 31)
        self.assertEqual(MAX_PHOTOGRAPHER_CHARS_G106, 46)
        self.assertEqual(MAX_COPYRIGHT_CHARS_G106, 46)
        self.assertEqual(FX3_V2_AUDIO_DISP_MIN_FW_TUPLE_G105, (2, 0))
        self.assertEqual(RELEASE_WO_CARD_FACTORY_DEFAULT_G105, "Enable")
        self.assertEqual(RELEASE_WO_LENS_FACTORY_DEFAULT_G105, "Enable")
        self.assertEqual(AUDIO_RECORDING_FACTORY_DEFAULT_G105, "On")
        self.assertEqual(AUDIO_OUT_TIMING_FACTORY_DEFAULT_G105, "Live")
        self.assertEqual(WIND_NOISE_REDUCT_FACTORY_DEFAULT_G105, "Off")
        self.assertEqual(SHOE_AUDIO_FACTORY_DEFAULT_G105, "48kHz/16bit 2ch")
        self.assertEqual(WRITE_COPYRIGHT_INFO_FACTORY_DEFAULT_G106, "Off")
        self.assertEqual(WRITE_COPYRIGHT_INFO_BENCH_DEFAULT_G106, "Off")
        self.assertEqual(AUDIO_RECORDING_MENU_PATH_G105, "MENU -> Shooting -> [Audio Recording]")
        self.assertEqual(
            DISP_SCREEN_DISP_SET_MENU_PATH_G105,
            "MENU -> Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]",
        )
        self.assertIn(AUDIO_RECORDING_ON_G105, ("On", "Off"))
        self.assertIn(AUDIO_OUT_TIMING_LIVE_G105, ALLOWED_AUDIO_OUT_TIMING_G105)
        self.assertIn(WIND_NOISE_REDUCT_OFF_G105, ("On", "Off"))
        self.assertIn(SHOE_AUDIO_48K_16B_2CH_G105, ALLOWED_SHOE_AUDIO_SETTINGS_G105)
        self.assertIn(CONTAINER_STILL_ARW_G106, STILL_EXIF_ELIGIBLE_CONTAINERS_G106)
        self.assertIn(CONTAINER_MOVIE_XAVC_HS_MP4_G106, MOVIE_AND_RAW_CONTAINERS_G106)
        self.assertIn(CONTAINER_MOVIE_XAVC_S_MP4_G106, MOVIE_AND_RAW_CONTAINERS_G106)
        self.assertIn(CONTAINER_HDMI_RAW_STREAM_G106, MOVIE_AND_RAW_CONTAINERS_G106)

    def test_70_end_to_end_uncached_clean_room_106gate_delegation_integrity(
        self,
    ) -> None:
        # Verify real uncached delegation evaluate_106gate_preflight -> evaluate_104gate_preflight
        r = evaluate_106gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_104_override=self.clean_dryrun_104,
        )
        self.assertTrue(r.all_106_gates_verified)
        self.assertEqual(r.technical_gates_passed, 106)
        self.assertEqual(r.master_104_report["summary"]["total_gates"], 104)


if __name__ == "__main__":
    unittest.main()
