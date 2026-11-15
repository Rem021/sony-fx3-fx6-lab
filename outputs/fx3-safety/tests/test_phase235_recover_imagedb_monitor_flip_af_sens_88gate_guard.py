"""Phase 235 Dual-Mode Unit Tests (`>=56` tests; 64 tests implemented) for
`fx3_safety.realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard`:

- Gate `G87`: `ILME-FX3` (`Ver. 7.02`) `[Recover Image DB]` (`MENU -> Shooting -> [Media]`)
  Depleted-Battery Refusal, Non-Deleting `AVF_INFO` Repair, Action-Item Reset Immunity
  & Unverified / `WP`-Locked Slot-1 Tier-0 Vault Read-Only Mutation Firewall.
- Gate `G88`: `ILME-FX3` (`Ver. 7.02`) `[Monitor Flip Direction]` `[Camera Settings Reset]`
  Survival + `[Horizontal Flip]` Playback Non-Inversion, Exact Full Menu String
  `[AF Subj. Shift Sensitivity]` (`1(Locked on)..5(Responsive)`) & `[AF Transition Speed]`
  (`1(Slow)..7(Fast)`) Movie/S&Q Reset Split, and `[Interval Shoot Func.]`
  (`1s..99m59s` start delay, `1s..60s` interval) Still-Image-Only Boundary.
- Unified 88-Gate Master Safety Preflight (`evaluate_88gate_preflight` /
  `verify-88-gates`): `85/88` offline awaiting physical Tier-0 receipt and
  `88/88` in `--simulate-bench-dry-run` with all hardware write/live-attach
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
from fx3_safety.realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard import (
    AF_KINEMATICS_SCOPE_MOVIE,
    AF_KINEMATICS_SCOPE_SQ,
    AF_SUBJ_SHIFT_SENSITIVITY_MENU_LABEL,
    AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT,
    AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_LABEL,
    AF_SUBJ_SHIFT_SENS_MAX,
    AF_SUBJ_SHIFT_SENS_MAX_LABEL,
    AF_SUBJ_SHIFT_SENS_MIN,
    AF_SUBJ_SHIFT_SENS_MIN_LABEL,
    AF_TRANSITION_SPEED_FACTORY_DEFAULT,
    AF_TRANSITION_SPEED_FACTORY_DEFAULT_LABEL,
    AF_TRANSITION_SPEED_MAX,
    AF_TRANSITION_SPEED_MAX_LABEL,
    AF_TRANSITION_SPEED_MENU_LABEL,
    AF_TRANSITION_SPEED_MIN,
    AF_TRANSITION_SPEED_MIN_LABEL,
    ALLOWED_AF_KINEMATICS_SCOPES,
    ALLOWED_AF_SUBJ_SHIFT_SENS_LABELS,
    ALLOWED_AF_TRANSITION_SPEED_LABELS,
    ALLOWED_INTERVAL_SHOOTING_MODES,
    ALLOWED_INTERVAL_STILL_FORMATS,
    ALLOWED_MONITOR_FLIP_DIRECTIONS,
    ALLOWED_RECOVER_IMAGE_DB_SLOTS,
    ALLOWED_RECOVER_IMAGE_DB_SYMPTOMS,
    ALLOWED_RESET_ACTIONS_PHASE235,
    DONOR_CHECK_MAX_SECONDS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FX3_DEFAULT_FW_VERSION_PHASE235,
    FX3_MIN_SUPPORTED_FW_TUPLE_PHASE235,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    G87,
    G87_GATE_CODE,
    G87_GATE_ID,
    G88,
    G88_GATE_CODE,
    G88_GATE_ID,
    GATE_G87_RECOVER_IMAGE_DB_DEPLETED_BATTERY_REFUSAL_NONDELETING_AND_SLOT1_TIER0_VAULT_FIREWALL,
    GATE_G88_MONITOR_FLIP_RESET_SURVIVAL_PLAYBACK_NONINVERSION_AF_SHIFT_SENS_AND_INTERVAL_STILL_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    INTERVAL_NUMBER_OF_SHOTS_MAX,
    INTERVAL_NUMBER_OF_SHOTS_MIN,
    INTERVAL_POST_ASSEMBLY_SOFTWARE,
    INTERVAL_SHOOTING_FACTORY_DEFAULT,
    INTERVAL_SHOOTING_INTERVAL_MAX_SECONDS,
    INTERVAL_SHOOTING_INTERVAL_MIN_SECONDS,
    INTERVAL_SHOOTING_OFF,
    INTERVAL_SHOOTING_ON,
    INTERVAL_START_TIME_MAX_SECONDS,
    INTERVAL_START_TIME_MIN_SECONDS,
    MONITOR_FLIP_AUTO,
    MONITOR_FLIP_FACTORY_DEFAULT,
    MONITOR_FLIP_HORIZONTAL,
    MONITOR_FLIP_OFF,
    MONITOR_FLIP_VERTICAL,
    NPFZ100_NOMINAL_MV_G87,
    NPFZ100_RECOVER_IMAGEDB_MIN_SAFE_MV,
    NPFZ100_RECOVER_IMAGEDB_MIN_SAFE_PCT,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PINNED_PHASE235_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_RECOVER_IMAGEDB_MONITOR_FLIP_AF_SENS_88GATE_SCHEMA,
    RECOVER_IMAGE_DB_SLOT_1,
    RECOVER_IMAGE_DB_SLOT_2,
    RECOVER_IMAGE_DB_SLOT_NONE,
    RECOVER_IMAGE_DB_SYMPTOM_DB_FILE_ERROR,
    RECOVER_IMAGE_DB_SYMPTOM_FALSE_ZERO_RECORDABLE,
    RECOVER_IMAGE_DB_SYMPTOM_NONE,
    RECOVER_IMAGE_DB_SYMPTOM_PC_EDITED_INCONSISTENCY,
    REJECTED_ABBREVIATED_AF_SUBJ_SHIFT_LABELS,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G87_RECOVER_IMAGEDB_ACTION_ITEM_RESET_CLAIM,
    STATUS_BLOCKED_G87_RECOVER_IMAGEDB_CLIP_DELETION_OR_AVF_REPAIR_MISMATCH,
    STATUS_BLOCKED_G87_RECOVER_IMAGEDB_DEPLETED_BATTERY_EXECUTION,
    STATUS_BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION,
    STATUS_BLOCKED_G87_TELEMETRY_INVALID,
    STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
    STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION,
    STATUS_BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G88_MONITOR_HORIZONTAL_FLIP_PLAYBACK_INVERSION,
    STATUS_BLOCKED_G88_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE235_DONOR_INTEGRITY,
    STATUS_VERIFIED_G87,
    STATUS_VERIFIED_G88,
    TIER0_VAULT_GUARDED_ARTIFACTS_G87,
    USB_PACKETS_TRANSMITTED,
    audit_phase235_donor_contracts,
    evaluate_88_master_safety_gates,
    evaluate_88gate_preflight,
    evaluate_g87_recover_imagedb_battery_and_tier0_vault_guard,
    evaluate_g88_monitor_flip_af_sens_and_interval_guard,
    main as module_main,
    parse_fx3_duration_seconds,
    resolve_fx3_af_transition_and_subj_shift_sensitivity,
    resolve_fx3_interval_shoot_func_boundary,
    resolve_fx3_monitor_flip_reset_and_playback,
    resolve_fx3_recover_imagedb_battery_and_vault_state,
    run_88_gate_preflight,
    verify_monitor_flip_playback_af_sens_and_interval_guard,
    verify_recover_imagedb_depleted_battery_and_tier0_vault_guard,
)


class TestPhase235RecoverImageDbMonitorFlipAfSens88GateGuard(unittest.TestCase):
    """Comprehensive dual-mode tests for Phase 235 Gates G87, G88 & 88-Gate Preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.offline_86 = fx3_safety.evaluate_86gate_preflight()
        cls.dryrun_86 = fx3_safety.evaluate_86gate_preflight(dry_run_simulated=True)
        cls.offline_88 = evaluate_88gate_preflight(master_86_override=cls.offline_86)
        cls.dryrun_88 = evaluate_88gate_preflight(
            simulate_bench_dry_run=True, master_86_override=cls.dryrun_86
        )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_86 = fx3_safety.evaluate_86gate_preflight(
                force_clean_room=True
            )
            cls.clean_dryrun_86 = fx3_safety.evaluate_86gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_88 = evaluate_88gate_preflight(
                force_clean_room=True, master_86_override=cls.clean_offline_86
            )
            cls.clean_dryrun_88 = evaluate_88gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_86_override=cls.clean_dryrun_86,
            )

    # ------------------------------------------------------------------
    # Section A: Package Exports & Bounded Donor Contract Audit (8 tests)
    # ------------------------------------------------------------------

    def test_01_public_package_exports_and_hard_redline_constants(self) -> None:
        self.assertEqual(G87, G87_GATE_ID)
        self.assertEqual(G88, G88_GATE_ID)
        self.assertEqual(
            GATE_G87_RECOVER_IMAGE_DB_DEPLETED_BATTERY_REFUSAL_NONDELETING_AND_SLOT1_TIER0_VAULT_FIREWALL,
            G87_GATE_CODE,
        )
        self.assertEqual(
            GATE_G88_MONITOR_FLIP_RESET_SURVIVAL_PLAYBACK_NONINVERSION_AF_SHIFT_SENS_AND_INTERVAL_STILL_GUARD,
            G88_GATE_CODE,
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
        self.assertIs(fx3_safety.evaluate_88gate_preflight, evaluate_88gate_preflight)
        self.assertIs(fx3_safety.run_88_gate_preflight, run_88_gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_88_master_safety_gates, evaluate_88_master_safety_gates
        )
        self.assertIn("evaluate_88gate_preflight", fx3_safety.__all__)
        self.assertIn(
            "realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard",
            fx3_safety.__all__,
        )
        self.assertIn("G87", fx3_safety.__all__)
        self.assertIn("G88", fx3_safety.__all__)

    def test_02_wave34_spec_constants_and_enums(self) -> None:
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE235, "7.02")
        self.assertEqual(FX3_MIN_SUPPORTED_FW_TUPLE_PHASE235, (1, 0))
        self.assertEqual(
            ALLOWED_RECOVER_IMAGE_DB_SLOTS,
            (RECOVER_IMAGE_DB_SLOT_NONE, RECOVER_IMAGE_DB_SLOT_1, RECOVER_IMAGE_DB_SLOT_2),
        )
        self.assertEqual(len(ALLOWED_RECOVER_IMAGE_DB_SYMPTOMS), 4)
        self.assertEqual(
            TIER0_VAULT_GUARDED_ARTIFACTS_G87,
            ("pnflasha", "cnflasha", "CAMSET01.DAT"),
        )
        self.assertEqual(
            ALLOWED_MONITOR_FLIP_DIRECTIONS,
            (
                MONITOR_FLIP_AUTO,
                MONITOR_FLIP_HORIZONTAL,
                MONITOR_FLIP_VERTICAL,
                MONITOR_FLIP_OFF,
            ),
        )
        self.assertEqual(MONITOR_FLIP_FACTORY_DEFAULT, "Auto")
        self.assertEqual(AF_SUBJ_SHIFT_SENSITIVITY_MENU_LABEL, "AF Subj. Shift Sensitivity")
        self.assertIn("AF Subj. Shift Sens.", REJECTED_ABBREVIATED_AF_SUBJ_SHIFT_LABELS)
        self.assertEqual((AF_SUBJ_SHIFT_SENS_MIN, AF_SUBJ_SHIFT_SENS_MAX), (1, 5))
        self.assertEqual(AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT, 5)
        self.assertEqual(AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_LABEL, "5(Responsive)")
        self.assertEqual(len(ALLOWED_AF_SUBJ_SHIFT_SENS_LABELS), 5)
        self.assertEqual(AF_TRANSITION_SPEED_MENU_LABEL, "AF Transition Speed")
        self.assertEqual((AF_TRANSITION_SPEED_MIN, AF_TRANSITION_SPEED_MAX), (1, 7))
        self.assertEqual(AF_TRANSITION_SPEED_FACTORY_DEFAULT, 5)
        self.assertEqual(AF_TRANSITION_SPEED_FACTORY_DEFAULT_LABEL, "5")
        self.assertEqual(len(ALLOWED_AF_TRANSITION_SPEED_LABELS), 7)
        self.assertEqual(
            ALLOWED_AF_KINEMATICS_SCOPES,
            (AF_KINEMATICS_SCOPE_MOVIE, AF_KINEMATICS_SCOPE_SQ),
        )
        self.assertEqual(
            ALLOWED_INTERVAL_SHOOTING_MODES,
            (INTERVAL_SHOOTING_OFF, INTERVAL_SHOOTING_ON),
        )
        self.assertEqual(INTERVAL_SHOOTING_FACTORY_DEFAULT, "Off")
        self.assertEqual(
            (INTERVAL_START_TIME_MIN_SECONDS, INTERVAL_START_TIME_MAX_SECONDS),
            (1, 5999),
        )
        self.assertEqual(
            (
                INTERVAL_SHOOTING_INTERVAL_MIN_SECONDS,
                INTERVAL_SHOOTING_INTERVAL_MAX_SECONDS,
            ),
            (1, 60),
        )
        self.assertEqual((INTERVAL_NUMBER_OF_SHOTS_MIN, INTERVAL_NUMBER_OF_SHOTS_MAX), (1, 9999))
        self.assertEqual(len(ALLOWED_INTERVAL_STILL_FORMATS), 5)
        self.assertEqual(len(ALLOWED_RESET_ACTIONS_PHASE235), 3)

    def test_03_donor_audit_clean_room_forced_via_flag(self) -> None:
        res = audit_phase235_donor_contracts(force_clean_room=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertEqual(res.files_inspected, 0)
        self.assertTrue(res.within_budget_150ms)
        self.assertLess(res.elapsed_seconds, DONOR_CHECK_MAX_SECONDS)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(res.checked_markers), len(PINNED_PHASE235_DONOR_SPECS))

    def test_04_donor_audit_clean_room_forced_via_env(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = audit_phase235_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_05_donor_audit_default_mode_fast_and_zero_leak(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            res = audit_phase235_donor_contracts()
        self.assertTrue(res.valid)
        self.assertIn(
            res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
        )
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertTrue(res.within_budget_150ms)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        dumped = json.dumps(res.to_dict())
        self.assertNotIn("\\x7fELF", dumped)

    def test_06_donor_audit_nonexistent_work_root_falls_back_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase235_donor_contracts(
                work_root=Path(tmp) / "missing_donor_tree", force_clean_room=False
            )
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)

    def test_07_donor_audit_corrupted_donor_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _key, (_body, rel, *_rest) in PINNED_PHASE235_DONOR_SPECS.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"CORRUPTED_STUB_DATA")
            res = audit_phase235_donor_contracts(work_root=root, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE235_DONOR_INTEGRITY)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertGreaterEqual(len(res.errors), 2)

    def test_08_donor_audit_zero_budget_fails_closed(self) -> None:
        res = audit_phase235_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE235_DONOR_INTEGRITY)

    # ------------------------------------------------------------------
    # Section B: Gate G87 — [Recover Image DB] Depleted-Battery Refusal,
    # Non-Deleting Repair & Slot-1 Tier-0 Vault Firewall (20 tests)
    # ------------------------------------------------------------------

    def test_09_g87_default_slot2_repair_passes_while_slot1_vault_guarded(self) -> None:
        res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G87)
        self.assertEqual(res.target_slot, RECOVER_IMAGE_DB_SLOT_2)
        self.assertTrue(res.recover_executed)
        self.assertEqual(res.recorded_clips_deleted, 0)
        self.assertEqual(res.recorded_clips_before, res.recorded_clips_after)
        self.assertTrue(res.avf_info_repaired)
        self.assertTrue(res.false_zero_recordable_cleared)
        self.assertTrue(res.slot1_recover_imagedb_hard_blocked)
        self.assertEqual(res.slot1_metadata_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)
        self.assertTrue(res.action_item_immune_to_camera_settings_reset)
        self.assertTrue(res.action_item_immune_to_initialize)

    def test_10_g87_all_media_symptoms_supported_non_deleting(self) -> None:
        for symptom in (
            RECOVER_IMAGE_DB_SYMPTOM_NONE,
            RECOVER_IMAGE_DB_SYMPTOM_DB_FILE_ERROR,
            RECOVER_IMAGE_DB_SYMPTOM_FALSE_ZERO_RECORDABLE,
            RECOVER_IMAGE_DB_SYMPTOM_PC_EDITED_INCONSISTENCY,
        ):
            res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
                media_symptom=symptom,
                recorded_clips_before=128,
            )
            self.assertTrue(res.valid, msg=symptom)
            self.assertEqual(res.recorded_clips_after, 128)
            self.assertEqual(res.recorded_clips_deleted, 0)

    def test_11_g87_idle_no_recover_requested_passes(self) -> None:
        res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            target_slot=RECOVER_IMAGE_DB_SLOT_NONE,
            recover_requested=False,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.recover_executed)
        self.assertTrue(res.slot1_recover_imagedb_hard_blocked)

    def test_12_g87_clip_deletion_violation_blocks_fail_closed(self) -> None:
        res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            recorded_clips_before=42,
            recorded_clips_after=41,
            recorded_clips_deleted=1,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G87_RECOVER_IMAGEDB_CLIP_DELETION_OR_AVF_REPAIR_MISMATCH,
        )

    def test_13_g87_clip_count_drift_without_deleted_counter_blocks(self) -> None:
        res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            recorded_clips_before=42,
            recorded_clips_after=40,
            recorded_clips_deleted=0,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G87_RECOVER_IMAGEDB_CLIP_DELETION_OR_AVF_REPAIR_MISMATCH,
            res.violation_codes,
        )

    def test_14_g87_executed_without_avf_repair_or_zero_clear_blocks(self) -> None:
        res1 = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            recover_executed=True,
            avf_info_repaired=False,
        )
        self.assertFalse(res1.valid)
        self.assertEqual(
            res1.status,
            STATUS_BLOCKED_G87_RECOVER_IMAGEDB_CLIP_DELETION_OR_AVF_REPAIR_MISMATCH,
        )
        res2 = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            recover_executed=True,
            false_zero_recordable_cleared=False,
        )
        self.assertFalse(res2.valid)
        self.assertEqual(
            res2.status,
            STATUS_BLOCKED_G87_RECOVER_IMAGEDB_CLIP_DELETION_OR_AVF_REPAIR_MISMATCH,
        )

    def test_15_g87_extremely_depleted_battery_flag_refuses_execution(self) -> None:
        state = resolve_fx3_recover_imagedb_battery_and_vault_state(
            battery_extremely_depleted=True,
            battery_soc_pct=50,
            battery_mv=7200,
        )
        self.assertTrue(state["hardware_refuses_for_depleted_battery"])
        self.assertFalse(state["expected_execution_permitted"])

        res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            battery_extremely_depleted=True,
            recover_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G87_RECOVER_IMAGEDB_DEPLETED_BATTERY_EXECUTION
        )

    def test_16_g87_battery_soc_threshold_boundary_9pct_vs_10pct(self) -> None:
        res_low = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            battery_soc_pct=NPFZ100_RECOVER_IMAGEDB_MIN_SAFE_PCT - 1,
            battery_mv=NPFZ100_NOMINAL_MV_G87,
        )
        self.assertFalse(res_low.valid)
        self.assertEqual(
            res_low.status,
            STATUS_BLOCKED_G87_RECOVER_IMAGEDB_DEPLETED_BATTERY_EXECUTION,
        )

        res_ok = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            battery_soc_pct=NPFZ100_RECOVER_IMAGEDB_MIN_SAFE_PCT,
            battery_mv=NPFZ100_NOMINAL_MV_G87,
        )
        self.assertTrue(res_ok.valid)

    def test_17_g87_battery_mv_threshold_boundary_6399mv_vs_6400mv(self) -> None:
        res_low = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            battery_soc_pct=25,
            battery_mv=NPFZ100_RECOVER_IMAGEDB_MIN_SAFE_MV - 1,
        )
        self.assertFalse(res_low.valid)
        self.assertEqual(
            res_low.status,
            STATUS_BLOCKED_G87_RECOVER_IMAGEDB_DEPLETED_BATTERY_EXECUTION,
        )

        res_ok = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            battery_soc_pct=25,
            battery_mv=NPFZ100_RECOVER_IMAGEDB_MIN_SAFE_MV,
        )
        self.assertTrue(res_ok.valid)

    def test_18_g87_action_item_immunity_rejects_false_reset_claims(self) -> None:
        for kw in (
            {"claimed_reset_by_camera_settings_reset": True},
            {"claimed_reset_by_initialize": True},
            {"claimed_persistent_toggle_state": True},
        ):
            res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertEqual(
                res.status, STATUS_BLOCKED_G87_RECOVER_IMAGEDB_ACTION_ITEM_RESET_CLAIM
            )

    def test_19_g87_slot1_active_tier0_vault_blocks_recover_imagedb(self) -> None:
        res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            target_slot=RECOVER_IMAGE_DB_SLOT_1,
            recover_requested=True,
            slot1_tier0_vault_active=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION
        )

    def test_20_g87_slot1_unverified_pnflasha_cnflasha_camset_blocks_even_if_unlocked(
        self,
    ) -> None:
        for artifact in ("pnflasha", "cnflasha", "CAMSET01.DAT"):
            res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
                target_slot=RECOVER_IMAGE_DB_SLOT_1,
                recover_requested=True,
                slot1_tier0_vault_active=False,
                slot1_sdxc_wp_locked=False,
                slot1_present_artifacts=(artifact,),
                slot1_off_camera_sha256_verified=False,
            )
            self.assertFalse(res.valid, msg=artifact)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION,
            )

    def test_21_g87_slot1_wp_locked_card_blocks_recover_imagedb(self) -> None:
        res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            target_slot=RECOVER_IMAGE_DB_SLOT_1,
            recover_requested=True,
            slot1_tier0_vault_active=False,
            slot1_present_artifacts=(),
            slot1_off_camera_sha256_verified=True,
            slot1_sdxc_wp_locked=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION
        )

    def test_22_g87_slot1_sneak_sector_write_or_avf_mutation_blocks(self) -> None:
        res_wr = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            target_slot=RECOVER_IMAGE_DB_SLOT_2,
            slot1_metadata_sector_writes=1,
        )
        self.assertFalse(res_wr.valid)
        self.assertEqual(
            res_wr.status, STATUS_BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION
        )

        res_mut = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            target_slot=RECOVER_IMAGE_DB_SLOT_2,
            slot1_avf_info_mutated=True,
        )
        self.assertFalse(res_mut.valid)
        self.assertEqual(
            res_mut.status, STATUS_BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION
        )

    def test_23_g87_slot1_normal_client_card_without_vault_allows_repair(self) -> None:
        res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            target_slot=RECOVER_IMAGE_DB_SLOT_1,
            recover_requested=True,
            slot1_tier0_vault_active=False,
            slot1_present_artifacts=(),
            slot1_off_camera_sha256_verified=False,
            slot1_sdxc_wp_locked=False,
            recorded_clips_before=15,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.slot1_recover_imagedb_hard_blocked)
        self.assertTrue(res.recover_executed)
        self.assertEqual(res.recorded_clips_after, 15)

    def test_24_g87_slot1_off_camera_verified_and_deactivated_vault_allows_repair(
        self,
    ) -> None:
        res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            target_slot=RECOVER_IMAGE_DB_SLOT_1,
            recover_requested=True,
            slot1_tier0_vault_active=False,
            slot1_present_artifacts=("CAMSET01.DAT",),
            slot1_off_camera_sha256_verified=True,
            slot1_sdxc_wp_locked=False,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.slot1_recover_imagedb_hard_blocked)

    def test_25_g87_invalid_body_or_firmware_blocks_telemetry(self) -> None:
        res_body = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            body_model_name="ILME-FX6V"
        )
        self.assertFalse(res_body.valid)
        self.assertEqual(res_body.status, STATUS_BLOCKED_G87_TELEMETRY_INVALID)

        res_fw = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
            firmware_version="bad_fw"
        )
        self.assertFalse(res_fw.valid)
        self.assertEqual(res_fw.status, STATUS_BLOCKED_G87_TELEMETRY_INVALID)

    def test_26_g87_invalid_slot_symptom_reset_or_battery_telemetry_blocks(
        self,
    ) -> None:
        for kw in (
            {"target_slot": "Slot 9"},
            {"target_slot": "NONE", "recover_requested": True},
            {"media_symptom": "fabricated_symptom"},
            {"reset_action": "bogus_reset"},
            {"battery_soc_pct": 105},
            {"battery_mv": 19500},
            {"recorded_clips_before": -1},
        ):
            res = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertIn(STATUS_BLOCKED_G87_TELEMETRY_INVALID, res.violation_codes)

    def test_27_g87_evaluator_dual_mode_pass(self) -> None:
        v_normal, r_normal = evaluate_g87_recover_imagedb_battery_and_tier0_vault_guard()
        self.assertTrue(v_normal.passed)
        self.assertTrue(r_normal.valid)
        self.assertEqual(r_normal.raw_firmware_bytes_leaked, 0)

        v_clean, r_clean = evaluate_g87_recover_imagedb_battery_and_tier0_vault_guard(
            force_clean_room=True
        )
        self.assertTrue(v_clean.passed)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_28_g87_evaluator_persistent_emmc_write_request_blocked(self) -> None:
        verdict, res = evaluate_g87_recover_imagedb_battery_and_tier0_vault_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    # ------------------------------------------------------------------
    # Section C: Gate G88 — [Monitor Flip Direction], Playback Non-Inversion,
    # [AF Subj. Shift Sensitivity] / [AF Transition Speed] & [Interval Shoot Func.]
    # (22 tests)
    # ------------------------------------------------------------------

    def test_29_g88_default_horizontal_flip_reset_split_and_interval_pass(self) -> None:
        res = verify_monitor_flip_playback_af_sens_and_interval_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G88)
        self.assertEqual(
            res.effective_post_reset_monitor_flip_direction, MONITOR_FLIP_HORIZONTAL
        )
        self.assertTrue(res.monitor_flip_survived_camera_settings_reset)
        self.assertTrue(res.live_shooting_horizontally_mirrored)
        self.assertFalse(res.playback_monitor_horizontally_inverted)
        self.assertFalse(res.playback_text_mirror_reversed)
        self.assertTrue(res.horizontal_flip_playback_noninversion_enforced)
        self.assertEqual(
            res.af_subj_shift_menu_label, AF_SUBJ_SHIFT_SENSITIVITY_MENU_LABEL
        )
        self.assertEqual(
            res.effective_post_reset_af_subj_shift_label,
            AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_LABEL,
        )
        self.assertEqual(
            res.effective_post_reset_af_transition_label,
            AF_TRANSITION_SPEED_FACTORY_DEFAULT_LABEL,
        )
        self.assertTrue(res.af_kinematics_reset_by_camera_settings_reset)
        self.assertTrue(res.monitor_flip_vs_af_reset_split_verified)
        self.assertFalse(res.in_camera_mp4_mxf_output_supported)
        self.assertTrue(res.interval_still_only_boundary_enforced)

    def test_30_g88_all_4_monitor_flip_directions_survive_camera_settings_reset(
        self,
    ) -> None:
        for direction in ALLOWED_MONITOR_FLIP_DIRECTIONS:
            res = verify_monitor_flip_playback_af_sens_and_interval_guard(
                pre_reset_monitor_flip_direction=direction,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            )
            self.assertTrue(res.valid, msg=direction)
            self.assertEqual(
                res.effective_post_reset_monitor_flip_direction, direction
            )
            self.assertTrue(res.monitor_flip_survived_camera_settings_reset)

    def test_31_g88_initialize_resets_monitor_flip_direction_to_auto(self) -> None:
        for direction in (
            MONITOR_FLIP_HORIZONTAL,
            MONITOR_FLIP_VERTICAL,
            MONITOR_FLIP_OFF,
        ):
            res = verify_monitor_flip_playback_af_sens_and_interval_guard(
                pre_reset_monitor_flip_direction=direction,
                reset_action=RESET_ACTION_INITIALIZE,
            )
            self.assertTrue(res.valid, msg=direction)
            self.assertEqual(
                res.effective_post_reset_monitor_flip_direction, MONITOR_FLIP_AUTO
            )
            self.assertFalse(res.monitor_flip_survived_camera_settings_reset)

    def test_32_g88_monitor_flip_falsely_reset_by_camera_settings_reset_blocks(
        self,
    ) -> None:
        res = verify_monitor_flip_playback_af_sens_and_interval_guard(
            pre_reset_monitor_flip_direction=MONITOR_FLIP_HORIZONTAL,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_monitor_flip_direction=MONITOR_FLIP_AUTO,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION,
        )

    def test_33_g88_invalid_monitor_flip_enum_blocks(self) -> None:
        res = verify_monitor_flip_playback_af_sens_and_interval_guard(
            pre_reset_monitor_flip_direction="Diagonal Flip"
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION,
        )

    def test_34_g88_horizontal_flip_playback_inversion_blocks_fail_closed(self) -> None:
        res_inv = verify_monitor_flip_playback_af_sens_and_interval_guard(
            pre_reset_monitor_flip_direction=MONITOR_FLIP_HORIZONTAL,
            observed_playback_monitor_horizontally_inverted=True,
        )
        self.assertFalse(res_inv.valid)
        self.assertEqual(
            res_inv.status, STATUS_BLOCKED_G88_MONITOR_HORIZONTAL_FLIP_PLAYBACK_INVERSION
        )

        res_txt = verify_monitor_flip_playback_af_sens_and_interval_guard(
            pre_reset_monitor_flip_direction=MONITOR_FLIP_HORIZONTAL,
            observed_playback_text_mirror_reversed=True,
        )
        self.assertFalse(res_txt.valid)
        self.assertEqual(
            res_txt.status, STATUS_BLOCKED_G88_MONITOR_HORIZONTAL_FLIP_PLAYBACK_INVERSION
        )

    def test_35_g88_abbreviated_af_subj_shift_sens_label_rejected(self) -> None:
        for bad_label in REJECTED_ABBREVIATED_AF_SUBJ_SHIFT_LABELS:
            res = verify_monitor_flip_playback_af_sens_and_interval_guard(
                af_subj_shift_menu_label=bad_label
            )
            self.assertFalse(res.valid, msg=bad_label)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
            )

    def test_36_g88_all_af_subj_shift_1_to_5_and_transition_1_to_7_levels_valid(
        self,
    ) -> None:
        for sens in (1, 2, 3, 4, 5, "1(Locked on)", "3", "5(Responsive)"):
            for speed in (1, 2, 3, 4, 5, 6, 7, "1(Slow)", "5", "7(Fast)"):
                res = verify_monitor_flip_playback_af_sens_and_interval_guard(
                    pre_reset_af_subj_shift_sensitivity=sens,
                    pre_reset_af_transition_speed=speed,
                    reset_action=RESET_ACTION_NONE,
                )
                self.assertTrue(res.valid, msg=f"sens={sens}, speed={speed}")

    def test_37_g88_af_kinematics_movie_and_sq_scopes_valid_still_scope_rejected(
        self,
    ) -> None:
        for scope in ("Movie", "S&Q"):
            res = verify_monitor_flip_playback_af_sens_and_interval_guard(
                af_kinematics_scope=scope
            )
            self.assertTrue(res.valid, msg=scope)

        res_still = verify_monitor_flip_playback_af_sens_and_interval_guard(
            af_kinematics_scope="Photo"
        )
        self.assertFalse(res_still.valid)
        self.assertEqual(
            res_still.status,
            STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
        )

    def test_38_g88_af_subj_shift_or_transition_out_of_range_blocks(self) -> None:
        for kw in (
            {"pre_reset_af_subj_shift_sensitivity": 0},
            {"pre_reset_af_subj_shift_sensitivity": 6},
            {"pre_reset_af_subj_shift_sensitivity": "3(Locked on)"},
            {"pre_reset_af_transition_speed": 0},
            {"pre_reset_af_transition_speed": 8},
            {"pre_reset_af_transition_speed": "4(Fast)"},
        ):
            res = verify_monitor_flip_playback_af_sens_and_interval_guard(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
            )

    def test_39_g88_af_kinematics_not_reset_by_camera_settings_reset_blocks(
        self,
    ) -> None:
        res_sens = verify_monitor_flip_playback_af_sens_and_interval_guard(
            pre_reset_af_subj_shift_sensitivity="1(Locked on)",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_af_subj_shift_sensitivity="1(Locked on)",
        )
        self.assertFalse(res_sens.valid)
        self.assertEqual(
            res_sens.status,
            STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
        )

        res_spd = verify_monitor_flip_playback_af_sens_and_interval_guard(
            pre_reset_af_transition_speed="1(Slow)",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_af_transition_speed="1(Slow)",
        )
        self.assertFalse(res_spd.valid)
        self.assertEqual(
            res_spd.status,
            STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
        )

    def test_40_g88_duration_parser_handles_seconds_minutes_and_rejects_malformed(
        self,
    ) -> None:
        self.assertEqual(parse_fx3_duration_seconds(1), 1)
        self.assertEqual(parse_fx3_duration_seconds("1s"), 1)
        self.assertEqual(parse_fx3_duration_seconds("60s"), 60)
        self.assertEqual(parse_fx3_duration_seconds("99m59s"), 5999)
        self.assertEqual(parse_fx3_duration_seconds("1m30s"), 90)
        self.assertEqual(parse_fx3_duration_seconds("99:59"), 5999)
        self.assertIsNone(parse_fx3_duration_seconds("1m60s"))
        self.assertIsNone(parse_fx3_duration_seconds(True))
        self.assertIsNone(parse_fx3_duration_seconds(""))

    def test_41_g88_interval_start_time_1s_to_99m59s_boundaries(self) -> None:
        res_min = verify_monitor_flip_playback_af_sens_and_interval_guard(
            shooting_start_time="1s"
        )
        self.assertTrue(res_min.valid)
        self.assertEqual(res_min.shooting_start_time_seconds, 1)

        res_max = verify_monitor_flip_playback_af_sens_and_interval_guard(
            shooting_start_time="99m59s"
        )
        self.assertTrue(res_max.valid)
        self.assertEqual(res_max.shooting_start_time_seconds, 5999)

        for bad_start in (0, 6000, "100m00s"):
            res_bad = verify_monitor_flip_playback_af_sens_and_interval_guard(
                shooting_start_time=bad_start
            )
            self.assertFalse(res_bad.valid, msg=str(bad_start))
            self.assertEqual(
                res_bad.status,
                STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION,
            )

    def test_42_g88_interval_step_1s_to_60s_and_shots_1_to_9999_boundaries(
        self,
    ) -> None:
        res_ok = verify_monitor_flip_playback_af_sens_and_interval_guard(
            shooting_interval="60s", number_of_shots=9999
        )
        self.assertTrue(res_ok.valid)
        self.assertEqual(res_ok.shooting_interval_seconds, 60)

        for kw in (
            {"shooting_interval": 0},
            {"shooting_interval": 61},
            {"shooting_interval": "2m00s"},
            {"number_of_shots": 0},
            {"number_of_shots": 10000},
        ):
            res_bad = verify_monitor_flip_playback_af_sens_and_interval_guard(**kw)
            self.assertFalse(res_bad.valid, msg=str(kw))
            self.assertEqual(
                res_bad.status,
                STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION,
            )

    def test_43_g88_interval_all_still_formats_valid(self) -> None:
        for fmt in ALLOWED_INTERVAL_STILL_FORMATS:
            res = verify_monitor_flip_playback_af_sens_and_interval_guard(
                interval_capture_format=fmt
            )
            self.assertTrue(res.valid, msg=fmt)
            self.assertEqual(res.interval_capture_format, fmt)

    def test_44_g88_interval_mp4_mxf_xavc_or_in_camera_movie_claim_rejected(
        self,
    ) -> None:
        for bad_fmt in ("XAVC S 4K .MP4", "XAVC-I .MXF", "MP4", "Interval Rec"):
            res = verify_monitor_flip_playback_af_sens_and_interval_guard(
                interval_capture_format=bad_fmt
            )
            self.assertFalse(res.valid, msg=bad_fmt)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION,
            )

        res_claim = verify_monitor_flip_playback_af_sens_and_interval_guard(
            interval_capture_format="JPEG",
            in_camera_interval_movie_claimed=True,
        )
        self.assertFalse(res_claim.valid)
        self.assertEqual(
            res_claim.status,
            STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION,
        )

    def test_45_g88_interval_reset_to_off_under_camera_settings_reset(self) -> None:
        res_bad = verify_monitor_flip_playback_af_sens_and_interval_guard(
            interval_shooting="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_interval_shooting="On",
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION,
        )

    def test_46_g88_resolver_helpers_return_canonical_dicts(self) -> None:
        m = resolve_fx3_monitor_flip_reset_and_playback(
            pre_reset_monitor_flip_direction="Horizontal Flip",
            reset_action="Camera Settings Reset",
        )
        self.assertEqual(m["expected_post_reset_direction"], "Horizontal Flip")
        self.assertFalse(m["expected_playback_horizontally_inverted"])

        af = resolve_fx3_af_transition_and_subj_shift_sensitivity(
            pre_reset_af_subj_shift_sensitivity=2,
            pre_reset_af_transition_speed=3,
            reset_action="NONE",
        )
        self.assertEqual((af["expected_post_sens_label"], af["expected_post_speed_label"]), ("2", "3"))

        iv = resolve_fx3_interval_shoot_func_boundary(
            shooting_start_time="99m59s", shooting_interval="60s"
        )
        self.assertTrue(iv["start_in_bounds"] and iv["interval_in_bounds"])
        self.assertEqual(iv["post_assembly_software"], INTERVAL_POST_ASSEMBLY_SOFTWARE)

    def test_47_g88_invalid_body_firmware_or_reset_action_blocks_telemetry(self) -> None:
        for kw in (
            {"body_model_name": "ILME-FX30"},
            {"body_model_id": 0x12345678},
            {"firmware_version": "invalid"},
            {"reset_action": "unknown_reset"},
        ):
            res = verify_monitor_flip_playback_af_sens_and_interval_guard(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertIn(STATUS_BLOCKED_G88_TELEMETRY_INVALID, res.violation_codes)

    def test_48_g88_live_shooting_flip_telemetry_mismatch_blocks(self) -> None:
        res = verify_monitor_flip_playback_af_sens_and_interval_guard(
            pre_reset_monitor_flip_direction=MONITOR_FLIP_HORIZONTAL,
            observed_live_shooting_horizontally_mirrored=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION,
        )

    def test_49_g88_evaluator_dual_mode_pass(self) -> None:
        v_normal, r_normal = evaluate_g88_monitor_flip_af_sens_and_interval_guard()
        self.assertTrue(v_normal.passed)
        self.assertTrue(r_normal.valid)
        self.assertEqual(r_normal.raw_firmware_bytes_leaked, 0)

        v_clean, r_clean = evaluate_g88_monitor_flip_af_sens_and_interval_guard(
            force_clean_room=True
        )
        self.assertTrue(v_clean.passed)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_50_g88_evaluator_persistent_emmc_write_request_blocked(self) -> None:
        verdict, res = evaluate_g88_monitor_flip_af_sens_and_interval_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    # ------------------------------------------------------------------
    # Section D: Unified 88-Gate Master Preflight & CLI (14 tests)
    # ------------------------------------------------------------------

    def test_51_master_88gate_offline_default_verifies_85_of_88(self) -> None:
        rep = self.offline_88
        self.assertEqual(
            rep.schema, REALHW_RECOVER_IMAGEDB_MONITOR_FLIP_AF_SENS_88GATE_SCHEMA
        )
        self.assertEqual(rep.summary["total_gates"], 88)
        self.assertEqual(rep.summary["verified_gates"], 85)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_85_gates_verified)
        self.assertFalse(rep.all_88_gates_verified)
        self.assertTrue(rep.g13_to_g88_all_passed)
        self.assertTrue(rep.g87_to_g88_all_passed)
        self.assertEqual(rep.status, "VERIFIED_85_OF_88_AWAITING_PHYSICAL_TIER0")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_52_master_88gate_simulate_bench_dry_run_verifies_88_of_88(self) -> None:
        rep = self.dryrun_88
        self.assertEqual(rep.summary["verified_gates"], 88)
        self.assertTrue(rep.offline_85_gates_verified)
        self.assertTrue(rep.all_88_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_88_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)

    def test_53_master_88gate_clean_room_offline_and_dry_run_parity(self) -> None:
        self.assertEqual(self.clean_offline_88.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(self.clean_offline_88.summary["verified_gates"], 85)
        self.assertTrue(self.clean_offline_88.offline_85_gates_verified)
        self.assertFalse(self.clean_offline_88.all_88_gates_verified)

        self.assertEqual(self.clean_dryrun_88.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(self.clean_dryrun_88.summary["verified_gates"], 88)
        self.assertTrue(self.clean_dryrun_88.all_88_gates_verified)
        self.assertFalse(self.clean_dryrun_88.overall_ready_for_hardware_attach)

    def test_54_master_88gate_delegates_g01_to_g86_and_appends_g87_g88(self) -> None:
        self.assertEqual(len(self.offline_88.gates), 88)
        self.assertEqual(self.offline_88.gates[-2]["gate_id"], G87_GATE_ID)
        self.assertEqual(self.offline_88.gates[-1]["gate_id"], G88_GATE_ID)
        self.assertEqual(
            [g["gate_id"] for g in self.offline_88.gates[:86]],
            [g["gate_id"] for g in self.offline_86.gates],
        )

    def test_55_master_88gate_g87_fault_propagates_fail_closed(self) -> None:
        rep = evaluate_88gate_preflight(
            force_clean_room=True,
            master_86_override=self.clean_offline_86,
            recover_imagedb_kwargs={
                "target_slot": "Slot 1",
                "recover_requested": True,
                "slot1_tier0_vault_active": True,
            },
        )
        self.assertEqual(rep.summary["verified_gates"], 84)
        self.assertFalse(rep.g87_to_g88_all_passed)
        self.assertFalse(rep.offline_85_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION
        )

    def test_56_master_88gate_g88_fault_propagates_fail_closed(self) -> None:
        rep = evaluate_88gate_preflight(
            force_clean_room=True,
            master_86_override=self.clean_offline_86,
            monitor_flip_af_interval_kwargs={
                "observed_playback_monitor_horizontally_inverted": True
            },
        )
        self.assertEqual(rep.summary["verified_gates"], 84)
        self.assertFalse(rep.g87_to_g88_all_passed)
        self.assertFalse(rep.offline_85_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G88_MONITOR_HORIZONTAL_FLIP_PLAYBACK_INVERSION
        )

    def test_57_master_88gate_persistent_emmc_write_request_blocks(self) -> None:
        rep = evaluate_88gate_preflight(
            force_clean_room=True,
            master_86_override=self.clean_dryrun_86,
            simulate_bench_dry_run=True,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_85_gates_verified)
        self.assertFalse(rep.all_88_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_58_cli_verify_g87_text_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-g87-recover-imagedb-battery-vault", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("slot1_vault_blocked=True", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g87-recover-imagedb-battery-vault", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        payload = json.loads(jbuf.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_59_cli_verify_g88_text_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-g88-monitor-flip-af-sens-interval", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("pb_inv=False", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g88-monitor-flip-af-sens-interval", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        payload = json.loads(jbuf.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(
            payload["monitor_flip_af_sens_interval_guard"]["af_subj_shift_menu_label"],
            "AF Subj. Shift Sensitivity",
        )

    def test_60_cli_verify_88_gates_offline_clean_room(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_88gate_preflight",
            return_value=self.clean_offline_88,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-88-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=85/88", buf.getvalue())
        self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

    def test_61_cli_verify_88_gates_simulate_bench_dry_run_json(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_88gate_preflight",
            return_value=self.clean_dryrun_88,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    ["verify-88-gates", "--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 88)
        self.assertTrue(payload["all_88_gates_verified"])
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_62_standalone_module_main_offline_and_dry_run(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.evaluate_88gate_preflight",
            return_value=self.clean_offline_88,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=85/88", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard.evaluate_88gate_preflight",
            return_value=self.clean_dryrun_88,
        ):
            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc2 = module_main(["--force-clean-room", "--simulate-bench-dry-run", "--json"])
        self.assertEqual(rc2, 0)
        self.assertEqual(json.loads(jbuf.getvalue())["summary"]["verified_gates"], 88)

    def test_63_master_88gate_end_to_end_live_delegation_without_override(self) -> None:
        rep = evaluate_88gate_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(rep.summary["verified_gates"], 88)
        self.assertTrue(rep.all_88_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_64_zero_raw_firmware_leak_in_serialized_master_88_report(self) -> None:
        serialized = json.dumps(self.dryrun_88.to_dict())
        self.assertNotIn("\\x7fELF", serialized)
        self.assertEqual(self.dryrun_88.raw_firmware_bytes_leaked, 0)


if __name__ == "__main__":
    unittest.main()
