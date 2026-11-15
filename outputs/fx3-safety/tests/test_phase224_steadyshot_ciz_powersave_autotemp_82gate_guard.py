"""Phase 224 Dual-Mode Unit Tests (60 tests, >=50 required):
Gates G81 (`G81_STEADYSHOT_ACTIVE_RAW_HFR_CUTOFF_AND_CIZ_CENTER_AF_MULTI_METERING_GUARD`),
G82 (`G82_POWER_SAVE_START_TIME_9COND_BYPASS_AND_AUTO_POWER_OFF_TEMP_TRIPOD_GUARD`),
and Unified 82-Gate Master Safety Preflight (`verify-82-gates`).
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
from fx3_safety.realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard import (
    ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G82,
    ALLOWED_FAN_CONTROL_MODES_G82,
    ALLOWED_METERING_MODES_G81,
    ALLOWED_POWER_SAVE_OPTIONS,
    ALLOWED_SHOOT_MODES_G81,
    ALLOWED_STEADYSHOT_MOVIE_MODES,
    ALLOWED_ZOOM_RANGE_SETTINGS,
    AUTO_POWER_OFF_TEMP_HIGH,
    AUTO_POWER_OFF_TEMP_STANDARD,
    CIZ_MAX_SCALE_4K,
    CIZ_MAX_SCALE_HD_OR_STILL,
    DIGITAL_ZOOM_MAX_SCALE,
    DONOR_CHECK_MAX_SECONDS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    G81,
    G81_GATE_CODE,
    G81_GATE_ID,
    G82,
    G82_GATE_CODE,
    G82_GATE_ID,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    METERING_MODE_MULTI,
    NON_OPTICAL_ZOOM_DOMAINS,
    NORMAL_HFR_DISQUALIFIED_RATES,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PINNED_PHASE224_DONOR_SPECS,
    POWER_SAVE_9_BYPASS_CONDITIONS,
    POWER_SAVE_FACTORY_DEFAULT_OPTION,
    POWER_SAVE_MENU_ITEM_EXACT,
    POWER_SAVE_OPTION_SECONDS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_STEADYSHOT_CIZ_POWERSAVE_AUTOTEMP_82GATE_SCHEMA,
    SHOOT_MODE_MOVIE,
    SHOOT_MODE_SQ,
    SHOOT_MODE_STILL,
    SPI_NOR_WRITE_AUTHORIZED,
    SQ_HFR_DISQUALIFIED_RATES,
    STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_4LOCK_AF_METERING_VIOLATION,
    STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN,
    STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_AOV_CROP_OR_LENS_VIOLATION,
    STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_RAW_OR_HFR_CUTOFF,
    STATUS_BLOCKED_G81_TELEMETRY_INVALID,
    STATUS_BLOCKED_G82_AIRGAPPED_NPFZ100_TIER0_SLEEP_HAZARD,
    STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_FAN_THERMAL_COUPLING_VIOLATION,
    STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_HIGH_HANDHELD_BURN_HAZARD,
    STATUS_BLOCKED_G82_POWER_SAVE_9COND_BYPASS_MISMATCH,
    STATUS_BLOCKED_G82_POWER_SAVE_MENU_ITEM_OR_OPTION_INVALID,
    STATUS_BLOCKED_G82_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE224_DONOR_INTEGRITY,
    STATUS_VERIFIED_G81,
    STATUS_VERIFIED_G82,
    STEADYSHOT_ACTIVE_MIN_CROP_FACTOR,
    STEADYSHOT_ACTIVE_NOMINAL_CROP_FACTOR,
    STEADYSHOT_FOCAL_LEN_MAX_MM,
    STEADYSHOT_FOCAL_LEN_MIN_MM,
    STEADYSHOT_MODE_ACTIVE,
    STEADYSHOT_MODE_OFF,
    STEADYSHOT_MODE_STANDARD,
    STILL_RAW_FILE_FORMATS,
    TIER0_P3_COLD_DUMP_MIB,
    TIER0_SAFE_AIRGAPPED_POWER_SAVE_OPTIONS,
    USB_PACKETS_TRANSMITTED,
    ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
    ZOOM_DOMAIN_DIGITAL_ZOOM,
    ZOOM_DOMAIN_OPTICAL,
    ZOOM_DOMAIN_SMART_ZOOM,
    ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
    ZOOM_RANGE_DIGITAL_ZOOM,
    ZOOM_RANGE_OPTICAL_ONLY,
    audit_phase224_donor_contracts,
    evaluate_82_master_safety_gates,
    evaluate_82gate_preflight,
    evaluate_g81_steadyshot_ciz_guard,
    evaluate_g82_powersave_autotemp_guard,
    main as module_main,
    resolve_fx3_auto_power_off_temp_and_fan,
    resolve_fx3_power_save_9cond_state,
    resolve_fx3_steadyshot_movie_state,
    resolve_fx3_zoom_and_4locks,
    run_82_gate_preflight,
    verify_powersave_9cond_and_autotemp_tripod_guard,
    verify_steadyshot_active_cutoff_and_ciz_4lock_guard,
)


class TestPhase224SteadyShotCizPowerSaveAutoTemp82GateGuard(unittest.TestCase):
    """Comprehensive dual-mode tests for Phase 224 Gates G81, G82 & 82-Gate Preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.offline_80 = fx3_safety.evaluate_80gate_preflight()
        cls.dryrun_80 = fx3_safety.evaluate_80gate_preflight(dry_run_simulated=True)
        cls.offline_82 = evaluate_82gate_preflight(master_80_override=cls.offline_80)
        cls.dryrun_82 = evaluate_82gate_preflight(
            simulate_bench_dry_run=True, master_80_override=cls.dryrun_80
        )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_80 = fx3_safety.evaluate_80gate_preflight(
                force_clean_room=True
            )
            cls.clean_dryrun_80 = fx3_safety.evaluate_80gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_82 = evaluate_82gate_preflight(
                force_clean_room=True, master_80_override=cls.clean_offline_80
            )
            cls.clean_dryrun_82 = evaluate_82gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_80_override=cls.clean_dryrun_80,
            )

    # ------------------------------------------------------------------
    # Section A: Package Exports & Bounded Donor Contract Audit (8 tests)
    # ------------------------------------------------------------------

    def test_01_public_package_exports_and_hard_redline_constants(self) -> None:
        self.assertEqual(G81, G81_GATE_CODE)
        self.assertEqual(G82, G82_GATE_CODE)
        self.assertEqual(
            G81_GATE_CODE,
            "G81_STEADYSHOT_ACTIVE_RAW_HFR_CUTOFF_AND_CIZ_CENTER_AF_MULTI_METERING_GUARD",
        )
        self.assertEqual(
            G82_GATE_CODE,
            "G82_POWER_SAVE_START_TIME_9COND_BYPASS_AND_AUTO_POWER_OFF_TEMP_TRIPOD_GUARD",
        )
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertIs(fx3_safety.evaluate_82gate_preflight, evaluate_82gate_preflight)
        self.assertIs(fx3_safety.run_82_gate_preflight, run_82_gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_82_master_safety_gates, evaluate_82_master_safety_gates
        )
        self.assertIn("evaluate_82gate_preflight", fx3_safety.__all__)
        self.assertIn("G81_GATE_CODE", fx3_safety.__all__)
        self.assertIn("G82_GATE_CODE", fx3_safety.__all__)

    def test_02_donor_audit_default_mode_under_150ms_zero_leak(self) -> None:
        res = audit_phase224_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertTrue(res.within_budget_150ms)
        self.assertLess(res.elapsed_seconds, DONOR_CHECK_MAX_SECONDS)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertIn(
            res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
        )

    def test_03_donor_audit_force_clean_room_argument(self) -> None:
        res = audit_phase224_donor_contracts(force_clean_room=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(res.checked_markers), len(PINNED_PHASE224_DONOR_SPECS))

    def test_04_donor_audit_env_var_clean_room_fallback(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = audit_phase224_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)

    def test_05_donor_audit_missing_work_root_falls_back_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase224_donor_contracts(
                work_root=Path(tmp) / "nonexistent_donor_dir",
                force_clean_room=False,
            )
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)

    def test_06_donor_audit_corrupted_local_donor_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _key, (_body, rel_path, *_rest) in PINNED_PHASE224_DONOR_SPECS.items():
                p = root / rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"CORRUPTED_DONOR_PAYLOAD")
            res = audit_phase224_donor_contracts(work_root=root, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE224_DONOR_INTEGRITY)
        self.assertGreater(len(res.errors), 0)

    def test_07_donor_audit_budget_exceeded_fails_closed(self) -> None:
        res = audit_phase224_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE224_DONOR_INTEGRITY)
        self.assertFalse(res.within_budget_150ms)

    def test_08_donor_audit_serialized_json_never_contains_raw_bytes(self) -> None:
        res = audit_phase224_donor_contracts()
        dumped = json.dumps(res.to_dict())
        self.assertNotIn("\\x7fELF", dumped)
        self.assertIn("sha256_by_artifact", dumped)
        self.assertEqual(res.to_dict()["raw_firmware_bytes_leaked"], 0)

    # ------------------------------------------------------------------
    # Section B: Gate G81 — [SteadyShot] Active & CIZ / Digital Zoom 4-Locks (18 tests)
    # ------------------------------------------------------------------

    def test_09_g81_default_steadyshot_active_2398p_optical_zoom_passes(self) -> None:
        res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G81)
        self.assertEqual(res.canonical_steadyshot_mode, STEADYSHOT_MODE_ACTIVE)
        self.assertFalse(res.steadyshot_active_disqualified)
        self.assertAlmostEqual(
            res.active_narrower_aov_crop_factor,
            STEADYSHOT_ACTIVE_NOMINAL_CROP_FACTOR,
        )
        self.assertFalse(res.non_optical_zoom_active)

    def test_10_g81_steadyshot_active_blocked_at_normal_movie_11988p_and_100p(
        self,
    ) -> None:
        for rate in ("119.88p", "100p", "120p"):
            res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                shoot_mode=SHOOT_MODE_MOVIE,
                rec_frame_rate=rate,
                steadyshot_mode=STEADYSHOT_MODE_ACTIVE,
            )
            self.assertFalse(res.valid, msg=f"Expected block at {rate}")
            self.assertIn(
                STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_RAW_OR_HFR_CUTOFF,
                res.violation_codes,
            )
            self.assertTrue(res.steadyshot_active_disqualified)

    def test_11_g81_steadyshot_active_blocked_at_sq_100_120_200_240fps(self) -> None:
        for sq in SQ_HFR_DISQUALIFIED_RATES:
            res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                shoot_mode=SHOOT_MODE_SQ,
                sq_frame_rate=sq,
                steadyshot_mode=STEADYSHOT_MODE_ACTIVE,
            )
            self.assertFalse(res.valid, msg=f"Expected block at S&Q {sq}")
            self.assertIn(
                STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_RAW_OR_HFR_CUTOFF,
                res.violation_codes,
            )
        # S&Q 60fps permits SteadyShot Active
        ok_60 = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            shoot_mode=SHOOT_MODE_SQ,
            sq_frame_rate="60fps",
            steadyshot_mode=STEADYSHOT_MODE_ACTIVE,
        )
        self.assertTrue(ok_60.valid)

    def test_12_g81_steadyshot_active_blocked_when_hdmi_raw_output_on(self) -> None:
        res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            shoot_mode=SHOOT_MODE_MOVIE,
            rec_frame_rate="23.98p",
            hdmi_raw_output_on=True,
            steadyshot_mode=STEADYSHOT_MODE_ACTIVE,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_RAW_OR_HFR_CUTOFF, res.violation_codes
        )
        self.assertIn("HDMI_RAW_OUTPUT_ON", res.steadyshot_active_disqualification_reasons)

    def test_13_g81_steadyshot_standard_and_off_allowed_under_raw_and_hfr(self) -> None:
        for mode in (STEADYSHOT_MODE_STANDARD, STEADYSHOT_MODE_OFF):
            res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                shoot_mode=SHOOT_MODE_MOVIE,
                rec_frame_rate="119.88p",
                hdmi_raw_output_on=True,
                steadyshot_mode=mode,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.steadyshot_active_disqualified)

    def test_14_g81_steadyshot_active_narrower_aov_crop_suppression_blocked(
        self,
    ) -> None:
        res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            steadyshot_mode=STEADYSHOT_MODE_ACTIVE,
            active_narrower_aov_crop_factor=1.00,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_AOV_CROP_OR_LENS_VIOLATION,
            res.violation_codes,
        )
        self.assertGreaterEqual(STEADYSHOT_ACTIVE_MIN_CROP_FACTOR, 1.08)

    def test_15_g81_manual_steadyshot_focal_length_8mm_to_1000mm_bounds(self) -> None:
        for valid_mm in (STEADYSHOT_FOCAL_LEN_MIN_MM, 35, STEADYSHOT_FOCAL_LEN_MAX_MM):
            ok = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                steadyshot_adjust_manual=True,
                steadyshot_focal_length_mm=valid_mm,
            )
            self.assertTrue(ok.valid)
        for bad_mm in (7, 0, 1001):
            bad = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                steadyshot_adjust_manual=True,
                steadyshot_focal_length_mm=bad_mm,
            )
            self.assertFalse(bad.valid)
            self.assertIn(
                STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_AOV_CROP_OR_LENS_VIOLATION,
                bad.violation_codes,
            )

    def test_16_g81_ciz_valid_with_all_4_state_locks_engaged(self) -> None:
        res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            zoom_range_setting=ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
            active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
            non_optical_zoom_scale=1.5,
            is_4k_movie_resolution=True,
            focus_area_setting_disabled=True,
            center_priority_af_active=True,
            effective_metering_mode=METERING_MODE_MULTI,
            face_eye_prior_in_af_enabled=False,
            face_priority_in_multi_metering_enabled=False,
            realtime_tracking_available=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.non_optical_zoom_active)
        self.assertTrue(res.all_4_non_optical_zoom_locks_enforced)

    def test_17_g81_non_optical_zoom_blocked_for_still_raw_file_formats(self) -> None:
        for fmt in STILL_RAW_FILE_FORMATS:
            res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                shoot_mode=SHOOT_MODE_STILL,
                still_file_format=fmt,
                zoom_range_setting=ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
                active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
                non_optical_zoom_scale=1.4,
            )
            self.assertFalse(res.valid, msg=f"Expected block for {fmt}")
            self.assertIn(
                STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN,
                res.violation_codes,
            )
        # Still JPEG/HEIF allows Clear Image Zoom up to 2.0x
        ok_heif = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            shoot_mode=SHOOT_MODE_STILL,
            still_file_format="HEIF",
            zoom_range_setting=ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
            active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
            non_optical_zoom_scale=2.0,
        )
        self.assertTrue(ok_heif.valid)

    def test_18_g81_non_optical_zoom_blocked_at_normal_11988p_100p_and_sq_hfr(
        self,
    ) -> None:
        for rate in NORMAL_HFR_DISQUALIFIED_RATES:
            bad = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                shoot_mode=SHOOT_MODE_MOVIE,
                rec_frame_rate=rate,
                steadyshot_mode=STEADYSHOT_MODE_OFF,
                zoom_range_setting=ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
                active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
                non_optical_zoom_scale=1.3,
            )
            self.assertFalse(bad.valid)
            self.assertIn(
                STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN,
                bad.violation_codes,
            )
        for sq in SQ_HFR_DISQUALIFIED_RATES:
            bad_sq = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                shoot_mode=SHOOT_MODE_SQ,
                sq_frame_rate=sq,
                steadyshot_mode=STEADYSHOT_MODE_OFF,
                zoom_range_setting=ZOOM_RANGE_DIGITAL_ZOOM,
                active_zoom_domain=ZOOM_DOMAIN_DIGITAL_ZOOM,
                non_optical_zoom_scale=2.5,
            )
            self.assertFalse(bad_sq.valid)
            self.assertIn(
                STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN,
                bad_sq.violation_codes,
            )

    def test_19_g81_ciz_4k_15x_vs_hd_20x_and_digital_40x_scale_ceilings(self) -> None:
        self.assertAlmostEqual(CIZ_MAX_SCALE_4K, 1.5)
        self.assertAlmostEqual(CIZ_MAX_SCALE_HD_OR_STILL, 2.0)
        self.assertAlmostEqual(DIGITAL_ZOOM_MAX_SCALE, 4.0)
        over_4k = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            zoom_range_setting=ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
            active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
            non_optical_zoom_scale=1.8,
            is_4k_movie_resolution=True,
        )
        self.assertFalse(over_4k.valid)
        ok_hd = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            zoom_range_setting=ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
            active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
            non_optical_zoom_scale=2.0,
            is_4k_movie_resolution=False,
        )
        self.assertTrue(ok_hd.valid)
        over_dig = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            zoom_range_setting=ZOOM_RANGE_DIGITAL_ZOOM,
            active_zoom_domain=ZOOM_DOMAIN_DIGITAL_ZOOM,
            non_optical_zoom_scale=4.5,
        )
        self.assertFalse(over_dig.valid)

    def test_20_g81_zoom_range_domain_mismatch_and_smart_zoom_movie_blocked(
        self,
    ) -> None:
        bad_opt_only = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            zoom_range_setting=ZOOM_RANGE_OPTICAL_ONLY,
            active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
            non_optical_zoom_scale=1.2,
        )
        self.assertFalse(bad_opt_only.valid)
        bad_dig_in_ciz = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            zoom_range_setting=ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
            active_zoom_domain=ZOOM_DOMAIN_DIGITAL_ZOOM,
            non_optical_zoom_scale=2.5,
        )
        self.assertFalse(bad_dig_in_ciz.valid)
        bad_smart_movie = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            shoot_mode=SHOOT_MODE_MOVIE,
            active_zoom_domain=ZOOM_DOMAIN_SMART_ZOOM,
            non_optical_zoom_scale=1.4,
        )
        self.assertFalse(bad_smart_movie.valid)

    def test_21_g81_lock1_focus_area_not_disabled_or_center_af_off_blocked(
        self,
    ) -> None:
        for kwargs in (
            {"focus_area_setting_disabled": False, "center_priority_af_active": True},
            {"focus_area_setting_disabled": True, "center_priority_af_active": False},
        ):
            res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                zoom_range_setting=ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
                active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
                non_optical_zoom_scale=1.3,
                **kwargs,
            )
            self.assertFalse(res.valid)
            self.assertIn(
                STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_4LOCK_AF_METERING_VIOLATION,
                res.violation_codes,
            )

    def test_22_g81_lock2_metering_mode_not_multi_blocked_under_ciz(self) -> None:
        for meter in ("CENTER", "SPOT", "ENTIRE_SCREEN_AVG", "HIGHLIGHT"):
            res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                zoom_range_setting=ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
                active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
                non_optical_zoom_scale=1.3,
                effective_metering_mode=meter,
            )
            self.assertFalse(res.valid, msg=f"Expected block for metering={meter}")
            self.assertIn(
                STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_4LOCK_AF_METERING_VIOLATION,
                res.violation_codes,
            )

    def test_23_g81_lock3_face_eye_prior_af_or_multi_metering_enabled_blocked(
        self,
    ) -> None:
        for kwargs in (
            {"face_eye_prior_in_af_enabled": True},
            {"face_priority_in_multi_metering_enabled": True},
        ):
            res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
                zoom_range_setting=ZOOM_RANGE_DIGITAL_ZOOM,
                active_zoom_domain=ZOOM_DOMAIN_DIGITAL_ZOOM,
                non_optical_zoom_scale=2.2,
                **kwargs,
            )
            self.assertFalse(res.valid)
            self.assertIn(
                STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_4LOCK_AF_METERING_VIOLATION,
                res.violation_codes,
            )

    def test_24_g81_lock4_realtime_tracking_available_blocked_under_ciz(self) -> None:
        res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            zoom_range_setting=ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
            active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
            non_optical_zoom_scale=1.4,
            realtime_tracking_available=True,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_4LOCK_AF_METERING_VIOLATION,
            res.violation_codes,
        )

    def test_25_g81_invalid_model_mode_or_scale_telemetry_rejected(self) -> None:
        res = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
            body_model_name="ILME-FX6",
            steadyshot_mode="DYNAMIC_ACTIVE_UNSUPPORTED",
            non_optical_zoom_scale=0.5,
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G81_TELEMETRY_INVALID, res.violation_codes)
        self.assertEqual(len(ALLOWED_STEADYSHOT_MOVIE_MODES), 3)
        self.assertEqual(len(ALLOWED_ZOOM_RANGE_SETTINGS), 3)
        self.assertEqual(len(ALLOWED_SHOOT_MODES_G81), 3)
        self.assertEqual(len(ALLOWED_METERING_MODES_G81), 5)
        self.assertEqual(len(NON_OPTICAL_ZOOM_DOMAINS), 3)

    def test_26_g81_dual_mode_evaluator_and_persistent_emmc_write_redline(self) -> None:
        v_norm, r_norm = evaluate_g81_steadyshot_ciz_guard()
        v_clean, r_clean = evaluate_g81_steadyshot_ciz_guard(force_clean_room=True)
        self.assertTrue(v_norm.passed)
        self.assertTrue(v_clean.passed)
        self.assertEqual(v_norm.gate_id, G81_GATE_ID)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        v_wr, r_wr = evaluate_g81_steadyshot_ciz_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_wr.passed)
        self.assertEqual(r_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(r_wr.persistent_emmc_writes_authorized)
        disq, reasons = resolve_fx3_steadyshot_movie_state(hdmi_raw_output_on=True)
        self.assertTrue(disq)
        self.assertEqual(reasons, ("HDMI_RAW_OUTPUT_ON",))
        engaged, locks = resolve_fx3_zoom_and_4locks(
            active_zoom_domain=ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM, non_optical_zoom_scale=1.3
        )
        self.assertTrue(engaged)
        self.assertEqual(locks["expected_metering_mode"], METERING_MODE_MULTI)

    # ------------------------------------------------------------------
    # Section C: Gate G82 — [Power Save Start Time] 9-Cond & [Auto Power OFF Temp.] (18 tests)
    # ------------------------------------------------------------------

    def test_27_g82_default_airgapped_tier0_power_save_off_standard_temp_passes(
        self,
    ) -> None:
        res = verify_powersave_9cond_and_autotemp_tripod_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G82)
        self.assertEqual(res.menu_item_label, POWER_SAVE_MENU_ITEM_EXACT)
        self.assertEqual(
            res.factory_default_power_save_option, POWER_SAVE_FACTORY_DEFAULT_OPTION
        )
        self.assertEqual(POWER_SAVE_FACTORY_DEFAULT_OPTION, "5 Min")
        self.assertEqual(res.configured_power_save_start_time, "Off")
        self.assertTrue(res.airgapped_tier0_sleep_safe)

    def test_28_g82_exact_menu_item_string_rejects_non_fx3_abbreviations(self) -> None:
        for wrong_label in ("Pwr Save Start Time", "Power Save", "Auto Power Off"):
            res = verify_powersave_9cond_and_autotemp_tripod_guard(
                menu_item_label=wrong_label
            )
            self.assertFalse(res.valid)
            self.assertIn(
                STATUS_BLOCKED_G82_POWER_SAVE_MENU_ITEM_OR_OPTION_INVALID,
                res.violation_codes,
            )

    def test_29_g82_all_6_power_save_options_mapped_and_invalid_rejected(self) -> None:
        self.assertEqual(
            ALLOWED_POWER_SAVE_OPTIONS,
            ("Off", "30 Min", "5 Min", "2 Min", "1 Min", "10 Sec"),
        )
        self.assertEqual(POWER_SAVE_OPTION_SECONDS["5 Min"], 300)
        self.assertEqual(POWER_SAVE_OPTION_SECONDS["30 Min"], 1800)
        self.assertEqual(POWER_SAVE_OPTION_SECONDS["10 Sec"], 10)
        bad = verify_powersave_9cond_and_autotemp_tripod_guard(
            power_save_start_time="15 Min", tier0_p3_75mib_dump_preflight=False
        )
        self.assertFalse(bad.valid)
        self.assertIn(
            STATUS_BLOCKED_G82_POWER_SAVE_MENU_ITEM_OR_OPTION_INVALID,
            bad.violation_codes,
        )

    def test_30_g82_each_of_9_automatic_deactivation_conditions_bypasses_sleep(
        self,
    ) -> None:
        self.assertEqual(len(POWER_SAVE_9_BYPASS_CONDITIONS), 9)
        for cond_name in POWER_SAVE_9_BYPASS_CONDITIONS:
            res = verify_powersave_9cond_and_autotemp_tripod_guard(
                power_save_start_time="5 Min",
                reported_power_save_deactivated=True,
                **{cond_name: True},
            )
            self.assertTrue(res.valid, msg=f"Condition {cond_name} should pass")
            self.assertTrue(res.power_save_auto_deactivated)
            self.assertEqual(res.active_9_bypass_conditions, (cond_name,))
            self.assertIsNone(res.effective_sleep_timeout_seconds)

    def test_31_g82_reported_deactivation_contradiction_blocked(self) -> None:
        # Claiming deactivated when all 9 conditions are False
        bad1 = verify_powersave_9cond_and_autotemp_tripod_guard(
            power_save_start_time="Off",
            reported_power_save_deactivated=True,
        )
        self.assertFalse(bad1.valid)
        self.assertIn(
            STATUS_BLOCKED_G82_POWER_SAVE_9COND_BYPASS_MISMATCH, bad1.violation_codes
        )
        # Claiming NOT deactivated when USB power supply is active
        bad2 = verify_powersave_9cond_and_autotemp_tripod_guard(
            power_save_start_time="5 Min",
            usb_power_supply=True,
            reported_power_save_deactivated=False,
        )
        self.assertFalse(bad2.valid)
        self.assertIn(
            STATUS_BLOCKED_G82_POWER_SAVE_9COND_BYPASS_MISMATCH, bad2.violation_codes
        )

    def test_32_g82_airgapped_npfz100_tier0_75mib_p3_dump_allows_off_and_30min(
        self,
    ) -> None:
        self.assertEqual(TIER0_P3_COLD_DUMP_MIB, 75)
        self.assertEqual(TIER0_SAFE_AIRGAPPED_POWER_SAVE_OPTIONS, ("Off", "30 Min"))
        for safe_opt in TIER0_SAFE_AIRGAPPED_POWER_SAVE_OPTIONS:
            res = verify_powersave_9cond_and_autotemp_tripod_guard(
                power_save_start_time=safe_opt,
                tier0_p3_75mib_dump_preflight=True,
                internal_npfz100_airgapped=True,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.airgapped_tier0_sleep_safe)

    def test_33_g82_airgapped_npfz100_tier0_blocks_default_5min_2min_1min_10sec(
        self,
    ) -> None:
        for unsafe_opt in ("5 Min", "2 Min", "1 Min", "10 Sec"):
            res = verify_powersave_9cond_and_autotemp_tripod_guard(
                power_save_start_time=unsafe_opt,
                tier0_p3_75mib_dump_preflight=True,
                internal_npfz100_airgapped=True,
            )
            self.assertFalse(res.valid, msg=f"Expected Tier-0 sleep block for {unsafe_opt}")
            self.assertIn(
                STATUS_BLOCKED_G82_AIRGAPPED_NPFZ100_TIER0_SLEEP_HAZARD,
                res.violation_codes,
            )
            self.assertFalse(res.airgapped_tier0_sleep_safe)

    def test_34_g82_non_tier0_normal_shooting_allows_factory_default_5min(
        self,
    ) -> None:
        res = verify_powersave_9cond_and_autotemp_tripod_guard(
            power_save_start_time="5 Min",
            tier0_p3_75mib_dump_preflight=False,
            internal_npfz100_airgapped=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_sleep_timeout_seconds, 300)

    def test_35_g82_bluetooth_and_ir_remote_ctrl_on_deactivate_power_save(
        self,
    ) -> None:
        canon, active, deact, eff = resolve_fx3_power_save_9cond_state(
            power_save_start_time="1 Min",
            ir_remote_ctrl_on=True,
            bluetooth_rmt_ctrl_on=True,
        )
        self.assertEqual(canon, "1 Min")
        self.assertEqual(active, ("ir_remote_ctrl_on", "bluetooth_rmt_ctrl_on"))
        self.assertTrue(deact)
        self.assertIsNone(eff)

    def test_36_g82_auto_power_off_temp_standard_allows_handheld_and_tripod(
        self,
    ) -> None:
        res = verify_powersave_9cond_and_autotemp_tripod_guard(
            auto_power_off_temp=AUTO_POWER_OFF_TEMP_STANDARD,
            tripod_mounted=False,
            handheld_prolonged_shooting=True,
        )
        self.assertTrue(res.valid)

    def test_37_g82_auto_power_off_temp_high_with_tripod_mounted_passes(self) -> None:
        res = verify_powersave_9cond_and_autotemp_tripod_guard(
            auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH,
            tripod_mounted=True,
            handheld_prolonged_shooting=False,
            fan_control_mode="Auto1",
            soc_temp_c=52.0,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.auto_power_off_temp, AUTO_POWER_OFF_TEMP_HIGH)
        self.assertTrue(res.tripod_mounted)

    def test_38_g82_auto_power_off_temp_high_blocks_unmounted_or_handheld_burn_hazard(
        self,
    ) -> None:
        for kwargs in (
            {"tripod_mounted": False, "handheld_prolonged_shooting": False},
            {"tripod_mounted": True, "handheld_prolonged_shooting": True},
        ):
            res = verify_powersave_9cond_and_autotemp_tripod_guard(
                auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH,
                **kwargs,
            )
            self.assertFalse(res.valid)
            self.assertIn(
                STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_HIGH_HANDHELD_BURN_HAZARD,
                res.violation_codes,
            )

    def test_39_g82_auto_power_off_temp_high_blocks_fan_control_always_off(
        self,
    ) -> None:
        res = verify_powersave_9cond_and_autotemp_tripod_guard(
            auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH,
            tripod_mounted=True,
            fan_control_mode="Always Off",
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_FAN_THERMAL_COUPLING_VIOLATION,
            res.violation_codes,
        )

    def test_40_g82_fan_off_in_rec_high_soc_and_teardown_ceiling_blocked(self) -> None:
        bad_rec = verify_powersave_9cond_and_autotemp_tripod_guard(
            movie_recording=True,
            fan_control_mode="Off in Rec",
            soc_temp_c=62.5,
        )
        self.assertFalse(bad_rec.valid)
        self.assertIn(
            STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_FAN_THERMAL_COUPLING_VIOLATION,
            bad_rec.violation_codes,
        )
        bad_ceil = verify_powersave_9cond_and_autotemp_tripod_guard(
            fan_control_mode="Auto1",
            soc_temp_c=90.5,
        )
        self.assertFalse(bad_ceil.valid)
        self.assertIn(
            STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_FAN_THERMAL_COUPLING_VIOLATION,
            bad_ceil.violation_codes,
        )

    def test_41_g82_resolve_auto_power_off_temp_and_fan_helper(self) -> None:
        tripod_ok, fan_ok, reasons = resolve_fx3_auto_power_off_temp_and_fan(
            auto_power_off_temp="High",
            tripod_mounted=False,
            fan_control_mode="Always Off",
        )
        self.assertFalse(tripod_ok)
        self.assertFalse(fan_ok)
        self.assertEqual(len(reasons), 2)

    def test_42_g82_invalid_auto_temp_fan_mode_or_soc_telemetry_rejected(self) -> None:
        self.assertEqual(ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G82, ("Standard", "High"))
        self.assertEqual(len(ALLOWED_FAN_CONTROL_MODES_G82), 5)
        bad = verify_powersave_9cond_and_autotemp_tripod_guard(
            auto_power_off_temp="EXTREME",
            fan_control_mode="TURBO_MAX",
            soc_temp_c=float("nan"),
        )
        self.assertFalse(bad.valid)
        self.assertIn(STATUS_BLOCKED_G82_TELEMETRY_INVALID, bad.violation_codes)

    def test_43_g82_dual_mode_evaluator_normal_and_clean_room(self) -> None:
        v_norm, r_norm = evaluate_g82_powersave_autotemp_guard()
        v_clean, r_clean = evaluate_g82_powersave_autotemp_guard(force_clean_room=True)
        self.assertTrue(v_norm.passed)
        self.assertTrue(v_clean.passed)
        self.assertEqual(v_norm.gate_id, G82_GATE_ID)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r_norm.raw_firmware_bytes_leaked, 0)

    def test_44_g82_persistent_emmc_write_redline_blocks_evaluator(self) -> None:
        v_wr, r_wr = evaluate_g82_powersave_autotemp_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_wr.passed)
        self.assertEqual(r_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(r_wr.persistent_emmc_writes_authorized)

    # ------------------------------------------------------------------
    # Section D: Unified 82-Gate Preflight, Compatibility & CLI (16 tests)
    # ------------------------------------------------------------------

    def test_45_preflight_82_offline_default_79_of_82_verified(self) -> None:
        rep = self.offline_82
        self.assertEqual(rep.schema, REALHW_STEADYSHOT_CIZ_POWERSAVE_AUTOTEMP_82GATE_SCHEMA)
        self.assertEqual(len(rep.gates), 82)
        self.assertEqual(rep.summary["total_gates"], 82)
        self.assertEqual(rep.summary["verified_gates"], 79)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_79_gates_verified)
        self.assertFalse(rep.all_82_gates_verified)
        self.assertTrue(rep.g81_to_g82_all_passed)
        self.assertTrue(rep.g13_to_g82_all_passed)
        self.assertEqual(rep.status, "VERIFIED_79_OF_82_AWAITING_PHYSICAL_TIER0")

    def test_46_preflight_82_offline_clean_room_79_of_82_verified(self) -> None:
        rep = self.clean_offline_82
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertEqual(rep.summary["verified_gates"], 79)
        self.assertTrue(rep.offline_79_gates_verified)
        self.assertFalse(rep.all_82_gates_verified)

    def test_47_preflight_82_simulate_bench_dry_run_82_of_82_verified(self) -> None:
        rep = self.dryrun_82
        self.assertEqual(rep.summary["verified_gates"], 82)
        self.assertTrue(rep.all_82_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_82_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_48_preflight_82_clean_room_simulate_bench_dry_run_82_of_82(self) -> None:
        rep = self.clean_dryrun_82
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.summary["verified_gates"], 82)
        self.assertTrue(rep.all_82_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)

    def test_49_preflight_82_hard_locks_all_hardware_safety_redlines(self) -> None:
        for rep in (
            self.offline_82,
            self.dryrun_82,
            self.clean_offline_82,
            self.clean_dryrun_82,
        ):
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertTrue(rep.agent_auto_flash_blocked)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_50_preflight_82_propagates_g81_violation(self) -> None:
        rep = evaluate_82gate_preflight(
            force_clean_room=True,
            master_80_override=self.clean_offline_80,
            steadyshot_ciz_kwargs={
                "steadyshot_mode": "ACTIVE",
                "hdmi_raw_output_on": True,
            },
        )
        self.assertFalse(rep.g81_to_g82_all_passed)
        self.assertFalse(rep.offline_79_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_RAW_OR_HFR_CUTOFF
        )
        self.assertEqual(rep.summary["verified_gates"], 78)

    def test_51_preflight_82_propagates_g82_violation(self) -> None:
        rep = evaluate_82gate_preflight(
            force_clean_room=True,
            master_80_override=self.clean_offline_80,
            powersave_autotemp_kwargs={
                "auto_power_off_temp": "High",
                "tripod_mounted": False,
            },
        )
        self.assertFalse(rep.g81_to_g82_all_passed)
        self.assertFalse(rep.offline_79_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_HIGH_HANDHELD_BURN_HAZARD
        )
        self.assertEqual(rep.summary["verified_gates"], 78)

    def test_52_preflight_82_blocks_persistent_emmc_write_request(self) -> None:
        rep = evaluate_82gate_preflight(
            force_clean_room=True,
            master_80_override=self.clean_dryrun_80,
            simulate_bench_dry_run=True,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_79_gates_verified)
        self.assertFalse(rep.all_82_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_53_preflight_82_gate_ordering_g01_through_g82(self) -> None:
        ids = [g["gate_id"] for g in self.offline_82.gates]
        self.assertEqual(len(ids), 82)
        self.assertTrue(ids[0].startswith("G01"))
        self.assertEqual(ids[-2], G81_GATE_ID)
        self.assertEqual(ids[-1], G82_GATE_ID)
        self.assertEqual(self.offline_82.gates[-2]["gate_code"], G81_GATE_CODE)
        self.assertEqual(self.offline_82.gates[-1]["gate_code"], G82_GATE_CODE)

    def test_54_backward_compatibility_across_58_to_80_gate_preflights(self) -> None:
        self.assertEqual(self.offline_80.summary["total_gates"], 80)
        self.assertEqual(self.offline_80.summary["verified_gates"], 77)
        self.assertEqual(self.dryrun_80.summary["verified_gates"], 80)
        for n in (58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80):
            fn = getattr(fx3_safety, f"evaluate_{n}gate_preflight")
            self.assertTrue(callable(fn), msg=f"Missing evaluate_{n}gate_preflight")

    def test_55_cli_verify_g81_steadyshot_ciz_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-g81-steadyshot-ciz", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("valid=True", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(["verify-g81-steadyshot-ciz", "--json"])
        self.assertEqual(rc_j, 0)
        payload = json.loads(jbuf.getvalue())
        self.assertTrue(payload["valid"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_56_cli_verify_g82_powersave_autotemp_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-g82-powersave-autotemp", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("valid=True", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(["verify-g82-powersave-autotemp", "--json"])
        self.assertEqual(rc_j, 0)
        payload = json.loads(jbuf.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_57_cli_verify_82_gates_offline_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_82gate_preflight",
            return_value=self.offline_82,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-82-gates"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=79/82", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(["verify-82-gates", "--json"])
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 79)

    def test_58_cli_verify_82_gates_simulate_bench_dry_run_82_of_82(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_82gate_preflight",
            return_value=self.dryrun_82,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-82-gates", "--simulate-bench-dry-run"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=82/82", buf.getvalue())
            self.assertIn("all_82_gates_verified=True", buf.getvalue())

    def test_59_module_main_entry_point_offline_and_dry_run(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.evaluate_82gate_preflight",
            return_value=self.clean_offline_82,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=79/82", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard.evaluate_82gate_preflight",
            return_value=self.clean_dryrun_82,
        ):
            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc2 = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc2, 0)
            self.assertEqual(json.loads(jbuf.getvalue())["summary"]["verified_gates"], 82)

    def test_60_dry_run_alias_flags_equivalent_in_evaluate_82gate_preflight(
        self,
    ) -> None:
        r1 = evaluate_82gate_preflight(
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_80_override=self.clean_dryrun_80,
        )
        self.assertTrue(r1.all_82_gates_verified)
        self.assertTrue(r1.dry_run_rehearsal_only)
        self.assertEqual(r1.summary["verified_gates"], 82)


if __name__ == "__main__":
    unittest.main()
