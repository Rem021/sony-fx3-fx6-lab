"""Comprehensive 4-mode test suite for Phase 359 (`156/156` Hardware Safety Gates):
Gate G155 (`[Area/Date/Time Setting]` 30 GMT Zones / `saylight_saving` Typo /
24h Soldered RTC vs FX6 `Clock Set`, plus `[Grid Line]` HDMI Pass-Through vs
`[Marker Display]` Zero-HDMI & 5-Item Reset-Resistance Firewall),
Gate G156 (`[Save/Load Settings]` `Slot 1` `EROFS=30` `CAMSET01..10.DAT` Vault /
`libSaveLoadSettings.so` / Zero `PRO/CAMERA` vs `1..3` & `M1..M4`, plus Zero
Physical `Sync Terminal` & `XLR-H1` vs `HVL-LBPC` MI-Shoe Exclusion / PMIC
`5V <= 900 mA` vs FX6 `TC IN/OUT` & Zero `GENLOCK` Firewall), and Unified
156-Gate Master Safety Preflight (`G01..G156`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True

SAFETY_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SAFETY_ROOT.parents[1]
if str(SAFETY_ROOT) not in sys.path:
    sys.path.insert(0, str(SAFETY_ROOT))

import fx3_safety  # noqa: E402
from fx3_safety import __main__ as safety_cli  # noqa: E402
from fx3_safety.realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_156gate_guard import (  # noqa: E402
    AREA_DATE_MENU_PATH_G155,
    AREA_DATE_RESETTABLE_BY_CAMSET_RESET_G155,
    AREA_GMT_30_ZONES_G155,
    AREA_GMT_HALF_HOUR_6_ZONES_G155,
    AUTO_SYNC_SEVER_ELF_TYPO_G155,
    CAMERA_SET_MEMORY_BODY_SLOTS_G156,
    CAMERA_SET_MEMORY_CARD_SLOTS_G156,
    CAMSET_MAX_CARD_SLOTS_G156,
    CAMSET_MAX_CLOUD_SLOTS_G156,
    CAMSET_MIN_FW_INCOMPAT_BOUNDARY_G156,
    DAYLIGHT_SAVINGS_DEFAULT_G155,
    DAYLIGHT_SAVINGS_ELF_TYPO_G155,
    DONOR_CHECK_MAX_SECONDS_PHASE359,
    EBUSY_ERRNO_PHASE359,
    EINVAL_ERRNO_PHASE359,
    ENV_CLEAN_ROOM_TEST_PHASE359,
    EOPNOTSUPP_ERRNO_PHASE359,
    EPERM_ERRNO_PHASE359,
    EROFS_ERRNO_PHASE359,
    EXACT_15_ASPECT_MARKER_RATIOS_G155,
    EXACT_20_CAMSET_EXCLUDED_ITEMS_G156,
    EXACT_3_DATE_FORMATS_G155,
    EXACT_3_FX6_VIDEO_LIGHT_MODES_G156,
    EXACT_3_GRID_LINE_TYPES_G155,
    EXACT_4_FX3_VIDEO_LIGHT_MODES_G156,
    EXACT_5_FX3_FLASH_MODES_G156,
    EXACT_5_MARKER_ITEMS_G155,
    FX3_CAMPR_PATH_TEMPLATE_G156,
    FX3_CAMSET_PATH_TEMPLATE_G156,
    FX3_DEFAULT_FW_VERSION_PHASE359,
    FX3_FLASH_MAX_TRIGGER_VOLTAGE_V_G156,
    FX3_FLASH_XSYNC_APSC_EFCS_DENOM_G156,
    FX3_FLASH_XSYNC_FF_EFCS_DENOM_G156,
    FX3_FLASH_XSYNC_MAX_DENOM_G156,
    FX3_FTPSET_PATH_TEMPLATE_G156,
    FX3_HELP_GUIDE_CODE_PHASE359,
    FX3_MODEL_ID_PHASE359,
    FX3_MODEL_NAME_PHASE359,
    FX3_PHYSICAL_SYNC_TERMINAL_PRESENT_G156,
    FX3_PRO_CAMERA_PATH_HITS_G156,
    FX3_RTC_BACKUP_CHARGE_MIN_HOURS_POWER_OFF_G155,
    FX3_SYNCHRO_TERMINAL_ELF_HITS_G156,
    FX3_USER_CR2032_SLOT_PRESENT_G155,
    FX6_ALL_FILE_MAX_SLOTS_G156,
    FX6_CLOCK_SET_DATE_MODES_G155,
    FX6_CLOCK_SET_DST_TOGGLE_EXPOSED_G155,
    FX6_CLOCK_SET_TIME_FORMATS_G155,
    FX6_CLOCK_SET_UTC_STEP_MINUTES_G155,
    FX6_DORMANT_GENLOCK_ELF_HITS_G156,
    FX6_NATIVE_3MODE_GRID_EXPOSED_G155,
    FX6_PHYSICAL_GENLOCK_BNC_PRESENT_G156,
    FX6_REFERENCE_FILE_ELF_HITS_G156,
    FX6_VIDEO_LIGHT_AUTO_SUPPORTED_G156,
    G155,
    G156,
    GRID_LINE_DISPLAY_DEFAULT_G155,
    GRID_LINE_RESETTABLE_BY_CAMSET_RESET_G155,
    GRID_LINE_TYPE_DEFAULT_G155,
    HDMI_MARKER_INJECTED_PIXELS_G155,
    ILC2210_STATES_3_MONTHS_RETENTION_G155,
    LIB_SAVE_LOAD_SETTINGS_BYTES_G156,
    LIB_SAVE_LOAD_SETTINGS_NAME_G156,
    MARKER_5ITEMS_RESETTABLE_BY_CAMSET_RESET_G155,
    MEDIA_SLOT_1_PHASE359,
    MEDIA_SLOT_2_PHASE359,
    PINNED_FX3_APPFW_SLICES_PHASE359,
    PINNED_FX6_APPFW_SLICES_PHASE359,
    PINNED_PHASE359_DONOR_SPECS,
    PMIC_5V_MAX_CURRENT_MA_G156,
    REALHW_156GATE_PREFLIGHT_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE359,
    RESET_ACTION_INITIALIZE_PHASE359,
    RESET_ACTION_NONE_PHASE359,
    SHOOT_MODE_MOVIE_PHASE359,
    SHOOT_MODE_SQ_PHASE359,
    SHOOT_MODE_STILL_PHASE359,
    STATUS_BLOCKED_G155_AREA_RTC_OR_GRID_MARKER_CLEANHDMI_RESET_VIOLATION,
    STATUS_BLOCKED_G155_DORMANT_CR2032_FX6_DST_OR_STILL_MARKER_EOPNOTSUPP,
    STATUS_BLOCKED_G155_TELEMETRY_INVALID,
    STATUS_BLOCKED_G156_CAMSET_COMPAT_FLASH_SHUTTER_OR_PMIC_VIOLATION,
    STATUS_BLOCKED_G156_DORMANT_SYNC_GENLOCK_SLOT2_MR_OR_REFFILE_EOPNOTSUPP,
    STATUS_BLOCKED_G156_MISHOE_XLRH1_EXCLUSION_EBUSY,
    STATUS_BLOCKED_G156_SLOT1_SAVELOAD_CAMSET_VAULT_EROFS,
    STATUS_BLOCKED_G156_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE359_DONOR_INTEGRITY,
    STATUS_VERIFIED_G155,
    STATUS_VERIFIED_G156,
    XLR_H1_TOP_SHOES_PASSIVE_COLD_ONLY_G156,
    audit_phase359_donor_contracts,
    compute_areadate_grid_cleanhdmi_matrix,
    compute_saveload_camset_mishoe_genlock_matrix,
    evaluate_156_master_safety_gates,
    evaluate_156gate_preflight,
    evaluate_g155_areadate_dst_grid_cleanhdmi_guard,
    evaluate_g156_saveload_camset_mishoe_genlock_guard,
    main as module_main,
    resolve_fx3_areadate_grid_cleanhdmi_state,
    resolve_fx3_saveload_camset_and_mishoe_state,
    run_156_gate_preflight,
    strip_elapsed_seconds_recursive_phase359,
    verify_areadate_dst_grid_cleanhdmi_guard,
    verify_areadate_dst_grid_cleanhdmi_guard_with_audit,
    verify_real_hardware_156gate_readiness,
    verify_saveload_camset_mishoe_genlock_guard,
    verify_saveload_camset_mishoe_genlock_guard_with_audit,
)


def _mock_paths_work_root_none(**_kwargs):
    return mock.MagicMock(work_root=None)


class TestPhase359AreaDateGridCleanHdmiSaveLoadCamsetMiShoe156GateGuard(
    unittest.TestCase
):
    """4-mode & comprehensive unit coverage for Phase 359 G155, G156, and 156-gate preflight."""

    # -----------------------------------------------------------------------
    # 1..12: Donor Integrity Audit & 4-Mode Clean-Room Fallback Contracts
    # -----------------------------------------------------------------------

    def test_01_donor_audit_runs_under_200ms_and_zero_leak(self) -> None:
        audit = audit_phase359_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_200ms)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE359)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(audit.errors), 0)

    def test_02_donor_audit_force_clean_room_arg(self) -> None:
        audit = audit_phase359_donor_contracts(repo_root=REPO_ROOT, force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_DISK_IO")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(len(audit.file_digests), len(PINNED_PHASE359_DONOR_SPECS))

    def test_03_donor_audit_env_fx3_clean_room_test(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE359: "1"}, clear=False):
            audit = audit_phase359_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_DISK_IO")

    def test_04_donor_audit_env_fx3_fx6_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            audit = audit_phase359_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_audit_absent_donor_work_root_none_mocked(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_156gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE359: ""},
                clear=False,
            ):
                audit = audit_phase359_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")
        self.assertGreater(len(audit.warnings), 0)

    def test_06_donor_audit_override_bad_sha_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tpath = Path(tmp) / "fake_donor.bin"
            tpath.write_bytes(b"FAKE_DONOR_PAYLOAD")
            bad_specs = {
                "fake_donor": (
                    "FX3",
                    "fake_donor.bin",
                    len(b"FAKE_DONOR_PAYLOAD"),
                    "0" * 64,
                    (b"FAKE_DONOR_PAYLOAD",),
                    "Fake test donor",
                )
            }
            audit = audit_phase359_donor_contracts(
                work_root=Path(tmp),
                force_clean_room=False,
                donor_specs_override=bad_specs,
            )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE359_DONOR_INTEGRITY)
        self.assertIn("fake_donor:sha256_mismatch", audit.missing_markers)

    def test_07_donor_audit_override_missing_file_and_work_root_none_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_specs = {
                "missing_donor": (
                    "FX3",
                    "does_not_exist.bin",
                    10,
                    "0" * 64,
                    (b"X",),
                    "Missing test donor",
                )
            }
            a1 = audit_phase359_donor_contracts(
                work_root=Path(tmp),
                force_clean_room=False,
                donor_specs_override=bad_specs,
            )
            a2 = audit_phase359_donor_contracts(
                work_root=None,
                force_clean_room=False,
                donor_specs_override=bad_specs,
            )
        self.assertFalse(a1.valid)
        self.assertFalse(a2.valid)
        self.assertEqual(a1.status, STATUS_BLOCKED_PHASE359_DONOR_INTEGRITY)
        self.assertEqual(a2.status, STATUS_BLOCKED_PHASE359_DONOR_INTEGRITY)

    def test_08_pinned_slices_count_and_no_raw_elf_bytes_in_json(self) -> None:
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE359), 26)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE359), 12)
        self.assertEqual(len(PINNED_PHASE359_DONOR_SPECS), 12)
        audit = audit_phase359_donor_contracts(repo_root=REPO_ROOT, force_clean_room=True)
        dumped = json.dumps(audit.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn('b"\\x7fELF', dumped)

    def test_09_strip_elapsed_seconds_recursive_phase359_determinism(self) -> None:
        sample = {
            "a": 1,
            "elapsed_seconds": 0.123,
            "nested": [{"elapsed_seconds": 0.456, "k": "v"}],
            "tup": ({"elapsed_seconds": 0.789, "ok": True},),
        }
        cleaned = strip_elapsed_seconds_recursive_phase359(sample)
        self.assertNotIn("elapsed_seconds", json.dumps(cleaned))
        self.assertEqual(cleaned["nested"][0]["k"], "v")
        self.assertEqual(cleaned["tup"][0]["ok"], True)

    def test_10_4mode_digest_equivalence_g155(self) -> None:
        _, r_clean = evaluate_g155_areadate_dst_grid_cleanhdmi_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE359: "1"}, clear=False):
            _, r_env1 = evaluate_g155_areadate_dst_grid_cleanhdmi_guard(repo_root=REPO_ROOT)
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            _, r_env2 = evaluate_g155_areadate_dst_grid_cleanhdmi_guard(repo_root=REPO_ROOT)
        with mock.patch(
            "fx3_safety.realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_156gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            _, r_absent = evaluate_g155_areadate_dst_grid_cleanhdmi_guard(repo_root=REPO_ROOT)

        d1 = strip_elapsed_seconds_recursive_phase359(r_clean.areadate_grid_cleanhdmi_guard)
        d2 = strip_elapsed_seconds_recursive_phase359(r_env1.areadate_grid_cleanhdmi_guard)
        d3 = strip_elapsed_seconds_recursive_phase359(r_env2.areadate_grid_cleanhdmi_guard)
        d4 = strip_elapsed_seconds_recursive_phase359(r_absent.areadate_grid_cleanhdmi_guard)
        self.assertEqual(d1, d2)
        self.assertEqual(d2, d3)
        self.assertEqual(d3, d4)

    def test_11_4mode_digest_equivalence_g156(self) -> None:
        _, r_clean = evaluate_g156_saveload_camset_mishoe_genlock_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE359: "1"}, clear=False):
            _, r_env1 = evaluate_g156_saveload_camset_mishoe_genlock_guard(repo_root=REPO_ROOT)
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            _, r_env2 = evaluate_g156_saveload_camset_mishoe_genlock_guard(repo_root=REPO_ROOT)
        with mock.patch(
            "fx3_safety.realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_156gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            _, r_absent = evaluate_g156_saveload_camset_mishoe_genlock_guard(repo_root=REPO_ROOT)

        d1 = strip_elapsed_seconds_recursive_phase359(r_clean.saveload_camset_mishoe_genlock_guard)
        d2 = strip_elapsed_seconds_recursive_phase359(r_env1.saveload_camset_mishoe_genlock_guard)
        d3 = strip_elapsed_seconds_recursive_phase359(r_env2.saveload_camset_mishoe_genlock_guard)
        d4 = strip_elapsed_seconds_recursive_phase359(r_absent.saveload_camset_mishoe_genlock_guard)
        self.assertEqual(d1, d2)
        self.assertEqual(d2, d3)
        self.assertEqual(d3, d4)

    def test_12_wrapper_with_audit_aliases(self) -> None:
        v1, r1 = verify_areadate_dst_grid_cleanhdmi_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        v2, r2 = verify_saveload_camset_mishoe_genlock_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v1.passed and r1.valid)
        self.assertTrue(v2.passed and r2.valid)
        self.assertEqual(v1.gate_id, G155)
        self.assertEqual(v2.gate_id, G156)

    # -----------------------------------------------------------------------
    # 13..42: Gate G155 — Area/Date 30-Zone RTC & Grid vs Marker Clean-HDMI
    # -----------------------------------------------------------------------

    def test_13_g155_baseline_verified_and_redlines_zero(self) -> None:
        res = verify_areadate_dst_grid_cleanhdmi_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G155)
        self.assertEqual(res.block_errno, 0)
        self.assertFalse(res.emmc_writes_authorized)
        self.assertFalse(res.cross_model_flash_authorized)
        self.assertEqual(res.usb_packets_transmitted, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_14_g155_30_gmt_zones_and_6_half_hour_zones_pinned(self) -> None:
        self.assertEqual(len(AREA_GMT_30_ZONES_G155), 30)
        self.assertEqual(len(set(AREA_GMT_30_ZONES_G155)), 30)
        self.assertEqual(len(AREA_GMT_HALF_HOUR_6_ZONES_G155), 6)
        for hz in AREA_GMT_HALF_HOUR_6_ZONES_G155:
            self.assertIn(hz, AREA_GMT_30_ZONES_G155)
            r = verify_areadate_dst_grid_cleanhdmi_guard(area_zone=hz)
            self.assertTrue(r.valid)
            self.assertEqual(r.effective_area_zone, hz)

    def test_15_g155_exact_3_date_formats_and_typos_pinned(self) -> None:
        self.assertEqual(EXACT_3_DATE_FORMATS_G155, ("Y-M-D", "M-D-Y", "D-M-Y"))
        self.assertEqual(
            DAYLIGHT_SAVINGS_ELF_TYPO_G155,
            "convert_setting_daylight_saving_to_saylight_saving",
        )
        self.assertEqual(
            AUTO_SYNC_SEVER_ELF_TYPO_G155,
            "BKID_APP_setting_auto_sync_sever_date_time",
        )
        for fmt in EXACT_3_DATE_FORMATS_G155:
            r = verify_areadate_dst_grid_cleanhdmi_guard(date_format=fmt)
            self.assertTrue(r.valid)
            self.assertEqual(r.effective_date_format, fmt)

    def test_16_g155_rejects_yyyy_mm_dd_or_invalid_zone(self) -> None:
        r1 = verify_areadate_dst_grid_cleanhdmi_guard(date_format="YYYY-MM-DD")
        r2 = verify_areadate_dst_grid_cleanhdmi_guard(area_zone="AREA_GMT_P_14_0")
        self.assertFalse(r1.valid)
        self.assertFalse(r2.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G155_TELEMETRY_INVALID)
        self.assertEqual(r2.status, STATUS_BLOCKED_G155_TELEMETRY_INVALID)
        self.assertEqual(r1.block_errno, EINVAL_ERRNO_PHASE359)

    def test_17_g155_area_date_reset_immune_and_init_retriggers_wizard(self) -> None:
        self.assertFalse(AREA_DATE_RESETTABLE_BY_CAMSET_RESET_G155)
        st_rst = resolve_fx3_areadate_grid_cleanhdmi_state(
            area_zone="AREA_GMT_M_05_0",
            daylight_savings="On",
            date_format="M-D-Y",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE359,
        )
        self.assertEqual(st_rst["effective_area_zone"], "AREA_GMT_M_05_0")
        self.assertEqual(st_rst["effective_daylight_savings"], "On")
        self.assertEqual(st_rst["effective_date_format"], "M-D-Y")
        self.assertFalse(st_rst["initial_setting_wizard_retriggered"])

        st_init = resolve_fx3_areadate_grid_cleanhdmi_state(
            area_zone="AREA_GMT_M_05_0",
            daylight_savings="On",
            date_format="M-D-Y",
            reset_action=RESET_ACTION_INITIALIZE_PHASE359,
        )
        self.assertIsNone(st_init["effective_area_zone"])
        self.assertEqual(st_init["effective_daylight_savings"], DAYLIGHT_SAVINGS_DEFAULT_G155)
        self.assertIsNone(st_init["effective_date_format"])
        self.assertTrue(st_init["initial_setting_wizard_retriggered"])

    def test_18_g155_camset_reset_clears_area_date_claim_blocked(self) -> None:
        r = verify_areadate_dst_grid_cleanhdmi_guard(
            claimed_camset_reset_clears_area_date=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE359)
        self.assertIn("AREA_DATE_RESET_IMMUNITY_VIOLATION", r.violation_codes)

    def test_19_g155_soldered_rtc_zero_cr2032_eopnotsupp_95(self) -> None:
        self.assertFalse(FX3_USER_CR2032_SLOT_PRESENT_G155)
        self.assertEqual(FX3_RTC_BACKUP_CHARGE_MIN_HOURS_POWER_OFF_G155, 24)
        self.assertFalse(ILC2210_STATES_3_MONTHS_RETENTION_G155)
        r = verify_areadate_dst_grid_cleanhdmi_guard(
            claimed_user_replaceable_cr2032_slot=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE359)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G155_DORMANT_CR2032_FX6_DST_OR_STILL_MARKER_EOPNOTSUPP,
        )

    def test_20_g155_ilc2210_3_months_claim_rejected(self) -> None:
        r = verify_areadate_dst_grid_cleanhdmi_guard(
            claimed_ilc2210_states_3_months_retention=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE359)
        self.assertIn("ILC2210_ZERO_3_MONTHS_CLAIM_VIOLATION", r.violation_codes)

    def test_21_g155_rtc_depleted_under_24h_blocks_timestamp_action(self) -> None:
        r_bad = verify_areadate_dst_grid_cleanhdmi_guard(
            rtc_battery_depleted=True,
            rtc_charge_hours_power_off=12.0,
            timestamp_dependent_action_requested=True,
        )
        self.assertFalse(r_bad.valid)
        self.assertFalse(r_bad.rtc_battery_charged)
        self.assertEqual(r_bad.block_errno, EINVAL_ERRNO_PHASE359)

        r_ok = verify_areadate_dst_grid_cleanhdmi_guard(
            rtc_battery_depleted=True,
            rtc_charge_hours_power_off=24.0,
            timestamp_dependent_action_requested=True,
        )
        self.assertTrue(r_ok.valid)
        self.assertTrue(r_ok.rtc_battery_charged)

    def test_22_g155_rtc_aged_dead_blocks_for_service_repair(self) -> None:
        r = verify_areadate_dst_grid_cleanhdmi_guard(rtc_battery_aged_dead=True)
        self.assertFalse(r.valid)
        self.assertFalse(r.rtc_battery_charged)
        self.assertIn("RTC_BATTERY_AGED_DEAD_REPAIR_REQUIRED", r.violation_codes)

    def test_23_g155_fx6_clock_set_zero_dst_toggle_eopnotsupp_95(self) -> None:
        self.assertFalse(FX6_CLOCK_SET_DST_TOGGLE_EXPOSED_G155)
        self.assertEqual(FX6_CLOCK_SET_UTC_STEP_MINUTES_G155, 30)
        self.assertEqual(FX6_CLOCK_SET_TIME_FORMATS_G155, ("12h", "24h"))
        self.assertEqual(FX6_CLOCK_SET_DATE_MODES_G155, ("YYMMDD", "MMDDYY", "DDMMYY"))
        r = verify_areadate_dst_grid_cleanhdmi_guard(
            requested_fx6_dormant_dst_toggle=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE359)
        self.assertIn("FX6_CLOCK_SET_ZERO_DST_TOGGLE_EOPNOTSUPP", r.violation_codes)

    def test_24_g155_grid_line_works_still_movie_sq_and_3_types(self) -> None:
        self.assertEqual(
            EXACT_3_GRID_LINE_TYPES_G155,
            ("Rule of 3rds Grid", "Square Grid", "Diag. + Square Grid"),
        )
        for sm in (SHOOT_MODE_STILL_PHASE359, SHOOT_MODE_MOVIE_PHASE359, SHOOT_MODE_SQ_PHASE359):
            for gt in EXACT_3_GRID_LINE_TYPES_G155:
                r = verify_areadate_dst_grid_cleanhdmi_guard(
                    shoot_mode=sm,
                    grid_line_display="On",
                    grid_line_type=gt,
                )
                self.assertTrue(r.valid)
                self.assertTrue(r.grid_rendered_on_monitor)

    def test_25_g155_grid_line_passes_out_hdmi_when_info_on_and_strips_on_clean_feed(self) -> None:
        st_pass = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            grid_line_display="On",
            hdmi_connected=True,
            hdmi_info_display="On",
            rec_media_dur_hdmi_output="On",
            raw_output="Off",
        )
        self.assertTrue(st_pass["grid_rendered_on_hdmi"])

        st_off_info = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            grid_line_display="On",
            hdmi_connected=True,
            hdmi_info_display="Off",
        )
        self.assertFalse(st_off_info["grid_rendered_on_hdmi"])
        self.assertTrue(st_off_info["clean_hdmi_feed_active"])

        st_hdmi_only = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            grid_line_display="On",
            hdmi_connected=True,
            hdmi_info_display="On",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
        )
        self.assertFalse(st_hdmi_only["grid_rendered_on_hdmi"])

        st_raw = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            grid_line_display="On",
            hdmi_connected=True,
            hdmi_info_display="On",
            raw_output="On",
        )
        self.assertFalse(st_raw["grid_rendered_on_hdmi"])

    def test_26_g155_marker_15_ratios_and_safety_zone_and_zero_hdmi(self) -> None:
        self.assertEqual(len(EXACT_15_ASPECT_MARKER_RATIOS_G155), 15)
        for ratio in EXACT_15_ASPECT_MARKER_RATIOS_G155:
            r = verify_areadate_dst_grid_cleanhdmi_guard(
                shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
                marker_display="On",
                aspect_marker=ratio,
                safety_zone="80%",
                guideframe="On",
                hdmi_connected=True,
                hdmi_info_display="On",
            )
            self.assertTrue(r.valid)
            self.assertTrue(r.marker_rendered_on_monitor)
            self.assertFalse(r.marker_rendered_on_hdmi)
            self.assertEqual(r.hdmi_marker_injected_pixels, 0)

    def test_27_g155_marker_claim_over_hdmi_rejected(self) -> None:
        r = verify_areadate_dst_grid_cleanhdmi_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            marker_display="On",
            guideframe="On",
            hdmi_connected=True,
            hdmi_info_display="On",
            claimed_marker_outputs_over_hdmi=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE359)
        self.assertIn("MARKER_DISPLAY_ZERO_HDMI_VIOLATION", r.violation_codes)

    def test_28_g155_marker_movie_and_sq_only_still_rejected_eopnotsupp_95(self) -> None:
        for kw in (
            {"marker_display": "On"},
            {"center_marker": "On"},
            {"aspect_marker": "2.39:1"},
            {"safety_zone": "90%"},
            {"guideframe": "On"},
        ):
            r = verify_areadate_dst_grid_cleanhdmi_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE359,
                **kw,
            )
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE359)
            self.assertIn("MARKER_DISPLAY_MOVIE_SQ_ONLY_EOPNOTSUPP", r.violation_codes)

    def test_29_g155_marker_hidden_during_focus_magnifier(self) -> None:
        st = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            marker_display="On",
            guideframe="On",
            focus_magnifier_active=True,
        )
        self.assertFalse(st["marker_rendered_on_monitor"])

        r_bad = verify_areadate_dst_grid_cleanhdmi_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            marker_display="On",
            guideframe="On",
            focus_magnifier_active=True,
            claimed_marker_visible_during_focus_magnifier=True,
        )
        self.assertFalse(r_bad.valid)
        self.assertIn("MARKER_FOCUS_MAGNIFIER_SUPPRESSION_VIOLATION", r_bad.violation_codes)

    def test_30_g155_all_grid_and_5_marker_items_reset_resistant(self) -> None:
        self.assertFalse(GRID_LINE_RESETTABLE_BY_CAMSET_RESET_G155)
        self.assertFalse(MARKER_5ITEMS_RESETTABLE_BY_CAMSET_RESET_G155)
        self.assertEqual(len(EXACT_5_MARKER_ITEMS_G155), 5)

        st_rst = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            grid_line_display="On",
            grid_line_type="Diag. + Square Grid",
            marker_display="On",
            center_marker="On",
            aspect_marker="16:9",
            safety_zone="90%",
            guideframe="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE359,
        )
        self.assertEqual(st_rst["effective_grid_line_display"], "On")
        self.assertEqual(st_rst["effective_grid_line_type"], "Diag. + Square Grid")
        self.assertEqual(st_rst["effective_marker_display"], "On")
        self.assertEqual(st_rst["effective_center_marker"], "On")
        self.assertEqual(st_rst["effective_aspect_marker"], "16:9")
        self.assertEqual(st_rst["effective_safety_zone"], "90%")
        self.assertEqual(st_rst["effective_guideframe"], "On")

        st_init = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            grid_line_display="On",
            grid_line_type="Square Grid",
            marker_display="On",
            guideframe="On",
            reset_action=RESET_ACTION_INITIALIZE_PHASE359,
        )
        self.assertEqual(st_init["effective_grid_line_display"], GRID_LINE_DISPLAY_DEFAULT_G155)
        self.assertEqual(st_init["effective_grid_line_type"], GRID_LINE_TYPE_DEFAULT_G155)
        self.assertEqual(st_init["effective_marker_display"], "Off")
        self.assertEqual(st_init["effective_guideframe"], "Off")

    def test_31_g155_camset_reset_clears_grid_or_marker_claim_blocked(self) -> None:
        r = verify_areadate_dst_grid_cleanhdmi_guard(
            claimed_camset_reset_clears_grid_or_marker=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE359)
        self.assertIn("GRID_AND_MARKER_5ITEMS_RESET_IMMUNITY_VIOLATION", r.violation_codes)

    def test_32_g155_retired_deleted_movie_grid_keys_and_fx6_3mode_grid_rejected(self) -> None:
        self.assertFalse(FX6_NATIVE_3MODE_GRID_EXPOSED_G155)
        r1 = verify_areadate_dst_grid_cleanhdmi_guard(
            requested_retired_deleted_movie_grid_key=True
        )
        r2 = verify_areadate_dst_grid_cleanhdmi_guard(
            requested_fx6_dormant_3mode_grid=True
        )
        self.assertFalse(r1.valid)
        self.assertFalse(r2.valid)
        self.assertEqual(r1.block_errno, EOPNOTSUPP_ERRNO_PHASE359)
        self.assertEqual(r2.block_errno, EOPNOTSUPP_ERRNO_PHASE359)

    def test_33_g155_sq_locks_rec_media_on_and_still_allows_grid_hdmi(self) -> None:
        st = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_SQ_PHASE359,
            grid_line_display="On",
            hdmi_connected=True,
            hdmi_info_display="On",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            raw_output="On",
        )
        self.assertTrue(st["grid_rendered_on_hdmi"])
        self.assertFalse(st["marker_rendered_on_hdmi"])

    def test_34_g155_fx6_center_marker_modes_1_to_4_admitted(self) -> None:
        for mode in ("Off", "1", "2", "3", "4"):
            r = verify_areadate_dst_grid_cleanhdmi_guard(fx6_center_marker_mode=mode)
            self.assertTrue(r.valid)
        r_bad = verify_areadate_dst_grid_cleanhdmi_guard(fx6_center_marker_mode="5")
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.status, STATUS_BLOCKED_G155_TELEMETRY_INVALID)

    def test_35_g155_matrix_384_states_exact(self) -> None:
        mat = compute_areadate_grid_cleanhdmi_matrix()
        self.assertEqual(mat["total_matrix_states"], 384)
        self.assertEqual(mat["area_reset_preserved_count"], 192)
        self.assertEqual(mat["grid_reset_preserved_count"], 192)
        self.assertEqual(mat["marker_reset_preserved_count"], 192)
        self.assertEqual(mat["grid_hdmi_passthrough_count"], 96)
        self.assertEqual(mat["marker_hdmi_leak_count"], 0)
        self.assertEqual(mat["still_marker_blocked_count"], 128)
        self.assertEqual(mat["focus_mag_marker_hidden_count"], 192)

    def test_36_g155_telemetry_validation_all_invalid_enum_and_bool_int_guards(self) -> None:
        for kw in (
            {"body_model_name": "ILCE-7SM3"},
            {"body_model_id": 0x9999},
            {"help_guide_code": "ilc/9999"},
            {"firmware_version": "bad"},
            {"daylight_savings": True},
            {"grid_line_display": 1},
            {"grid_line_type": "Golden Ratio"},
            {"safety_zone": "95%"},
            {"rtc_charge_hours_power_off": -1.0},
            {"rtc_charge_hours_power_off": True},
            {"reset_action": "Factory Wipe"},
        ):
            r = verify_areadate_dst_grid_cleanhdmi_guard(**kw)
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G155_TELEMETRY_INVALID)

    def test_37_g155_evaluate_returns_gate_verdict_and_result(self) -> None:
        v, r = evaluate_g155_areadate_dst_grid_cleanhdmi_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v.passed)
        self.assertTrue(r.valid)
        self.assertEqual(v.gate_id, G155)
        self.assertEqual(
            r.areadate_grid_cleanhdmi_guard["area_date_menu_path"],
            AREA_DATE_MENU_PATH_G155,
        )

    def test_38_g155_marker_off_master_hides_submarkers(self) -> None:
        st = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            marker_display="Off",
            center_marker="On",
            guideframe="On",
        )
        self.assertFalse(st["marker_rendered_on_monitor"])
        self.assertFalse(st["marker_rendered_on_hdmi"])

    def test_39_g155_marker_on_with_all_submarkers_off_renders_none(self) -> None:
        st = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            marker_display="On",
            center_marker="Off",
            aspect_marker="Off",
            safety_zone="Off",
            guideframe="Off",
        )
        self.assertFalse(st["marker_rendered_on_monitor"])

    def test_40_g155_grid_off_does_not_render_on_monitor_or_hdmi(self) -> None:
        st = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
            grid_line_display="Off",
            hdmi_connected=True,
            hdmi_info_display="On",
        )
        self.assertFalse(st["grid_rendered_on_monitor"])
        self.assertFalse(st["grid_rendered_on_hdmi"])

    def test_41_g155_marker_in_sq_renders_on_monitor_only(self) -> None:
        st = resolve_fx3_areadate_grid_cleanhdmi_state(
            shoot_mode=SHOOT_MODE_SQ_PHASE359,
            marker_display="On",
            safety_zone="80%",
            hdmi_connected=True,
            hdmi_info_display="On",
        )
        self.assertTrue(st["marker_rendered_on_monitor"])
        self.assertFalse(st["marker_rendered_on_hdmi"])

    def test_42_g155_reset_network_set_does_not_wipe_area_date_or_grid(self) -> None:
        st = resolve_fx3_areadate_grid_cleanhdmi_state(
            area_zone="AREA_GMT_P_05_5",
            grid_line_display="On",
            reset_action="Reset Network Set.",
        )
        self.assertEqual(st["effective_area_zone"], "AREA_GMT_P_05_5")
        self.assertEqual(st["effective_grid_line_display"], "On")

    # -----------------------------------------------------------------------
    # 43..74: Gate G156 — Save/Load Slot-1 EROFS=30 & MI-Shoe XLR-H1 / Sync / GENLOCK
    # -----------------------------------------------------------------------

    def test_43_g156_baseline_camset_load_verified_and_zero_writes(self) -> None:
        res = verify_saveload_camset_mishoe_genlock_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G156)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.lib_save_load_settings_name, LIB_SAVE_LOAD_SETTINGS_NAME_G156)
        self.assertEqual(res.lib_save_load_settings_bytes, LIB_SAVE_LOAD_SETTINGS_BYTES_G156)
        self.assertEqual(res.fx3_pro_camera_path_hits, FX3_PRO_CAMERA_PATH_HITS_G156)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertEqual(res.emmc_nflasha_write_count, 0)
        self.assertTrue(res.camset_auto_reboot_on_load)

    def test_44_g156_exact_card_path_templates_sdxc_vs_cfexpress(self) -> None:
        self.assertEqual(
            FX3_CAMSET_PATH_TEMPLATE_G156, "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
        )
        self.assertEqual(
            FX3_CAMPR_PATH_TEMPLATE_G156, "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT"
        )
        self.assertEqual(
            FX3_FTPSET_PATH_TEMPLATE_G156, "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT"
        )
        r_sd = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", card_type="SDXC", slot_index=10
        )
        r_cfa = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", card_type="CFexpress Type A", slot_index=1
        )
        self.assertTrue(r_sd.valid and r_cfa.valid)
        self.assertEqual(
            r_sd.resolved_setting_path, "/PRIVATE/SONY/SETTING/ILME-FX3/CAMSET/CAMSET10.DAT"
        )
        self.assertEqual(
            r_cfa.resolved_setting_path, "/SONY/SETTING/ILME-FX3/CAMSET/CAMSET01.DAT"
        )
        self.assertNotIn("PRO/CAMERA", r_sd.resolved_setting_path)

    def test_45_g156_slot1_erofs_30_blocks_camset_save_delete_ftpset_campr_and_write(self) -> None:
        for kw in (
            {"operation": "camset_save", "target_media": "Slot 1"},
            {"operation": "camset_delete", "target_media": "Slot 1"},
            {"operation": "ftpset_save", "target_media": "Slot 1"},
            {"operation": "camera_set_memory_card_save", "memory_recall_media": "Slot 1"},
            {"operation": "camset_load", "target_media": "Slot 1", "requested_write_operation": True},
        ):
            r = verify_saveload_camset_mishoe_genlock_guard(**kw)
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EROFS_ERRNO_PHASE359)
            self.assertEqual(r.status, STATUS_BLOCKED_G156_SLOT1_SAVELOAD_CAMSET_VAULT_EROFS)
            self.assertTrue(r.slot1_tier0_vault_firewall_blocked)
            self.assertEqual(r.slot1_data_sector_writes, 0)
            self.assertEqual(r.emmc_nflasha_write_count, 0)

    def test_46_g156_slot2_and_mediab_camset_rejected_eopnotsupp_95(self) -> None:
        for target in ("Slot 2", "Media(B)"):
            for op in ("camset_load", "camset_save", "camset_delete", "ftpset_save"):
                r = verify_saveload_camset_mishoe_genlock_guard(
                    operation=op, target_media=target
                )
                self.assertFalse(r.valid)
                self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE359)
                self.assertIn("SAVELOAD_SLOT1_ONLY_NO_SLOT2_EOPNOTSUPP", r.violation_codes)

    def test_47_g156_mr_recall_mode_disables_saveload_eopnotsupp_95(self) -> None:
        r = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", mr_recall_mode_active=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE359)
        self.assertIn("SAVELOAD_DISABLED_IN_MR_MODE_EOPNOTSUPP", r.violation_codes)

    def test_48_g156_libsaveload_rejects_cross_model_checksum_and_legacy_fw(self) -> None:
        self.assertEqual(CAMSET_MIN_FW_INCOMPAT_BOUNDARY_G156, 2.00)
        r_cross = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", source_body_model="ILME-FX30"
        )
        r_crc = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", checksum_valid=False
        )
        r_old_fw = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", source_fw_version="1.01", firmware_version="7.02"
        )
        for r in (r_cross, r_crc, r_old_fw):
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE359)
            self.assertEqual(
                r.status, STATUS_BLOCKED_G156_CAMSET_COMPAT_FLASH_SHUTTER_OR_PMIC_VIOLATION
            )

    def test_49_g156_camset_same_model_v2_plus_and_cloud_60_slots_admitted(self) -> None:
        self.assertEqual(CAMSET_MAX_CARD_SLOTS_G156, 10)
        self.assertEqual(CAMSET_MAX_CLOUD_SLOTS_G156, 60)
        r1 = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", source_fw_version="4.00", firmware_version="7.02"
        )
        r2 = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_save", target_media="Cloud(Private)", slot_index=60
        )
        r3 = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_save", target_media="Cloud(Share)", slot_index=1
        )
        self.assertTrue(r1.valid and r2.valid and r3.valid)
        self.assertEqual(r2.resolved_setting_path, "cloud://Cloud(Private)/CAMSET60.DAT")

    def test_50_g156_slot_bounds_card_10_cloud_60_body_3_campr_4(self) -> None:
        r_c11 = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", target_media="Slot 1", slot_index=11
        )
        r_cl61 = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", target_media="Cloud(Private)", slot_index=61
        )
        r_b4 = verify_saveload_camset_mishoe_genlock_guard(
            operation="camera_set_memory_body", slot_index=4
        )
        r_m5 = verify_saveload_camset_mishoe_genlock_guard(
            operation="camera_set_memory_card_recall", slot_index=5
        )
        for r in (r_c11, r_cl61, r_b4, r_m5):
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE359)

    def test_51_g156_camera_set_memory_body_1_to_3_and_slot2_m1_to_m4_admitted(self) -> None:
        self.assertEqual(CAMERA_SET_MEMORY_BODY_SLOTS_G156, (1, 2, 3))
        self.assertEqual(CAMERA_SET_MEMORY_CARD_SLOTS_G156, ("M1", "M2", "M3", "M4"))
        for idx in (1, 2, 3):
            rb = verify_saveload_camset_mishoe_genlock_guard(
                operation="camera_set_memory_body", slot_index=idx
            )
            self.assertTrue(rb.valid)
        for idx in (1, 2, 3, 4):
            rs2 = verify_saveload_camset_mishoe_genlock_guard(
                operation="camera_set_memory_card_save",
                memory_recall_media="Slot 2",
                slot_index=idx,
            )
            rr1 = verify_saveload_camset_mishoe_genlock_guard(
                operation="camera_set_memory_card_recall",
                memory_recall_media="Slot 1",
                slot_index=idx,
            )
            self.assertTrue(rs2.valid and rr1.valid)

    def test_52_g156_20_excluded_items_and_zero_pro_camera_enforced(self) -> None:
        self.assertEqual(len(EXACT_20_CAMSET_EXCLUDED_ITEMS_G156), 20)
        r1 = verify_saveload_camset_mishoe_genlock_guard(
            claimed_fx3_uses_pro_camera_path=True
        )
        r2 = verify_saveload_camset_mishoe_genlock_guard(
            claimed_camset_exports_excluded_item="IPTC Information"
        )
        self.assertFalse(r1.valid)
        self.assertFalse(r2.valid)
        self.assertEqual(r2.camset_excluded_items_leaked_count, 1)

    def test_53_g156_fx6_all_file_on_fx3_and_dormant_reference_file_eopnotsupp_95(self) -> None:
        self.assertEqual(FX6_ALL_FILE_MAX_SLOTS_G156, 64)
        self.assertEqual(FX6_REFERENCE_FILE_ELF_HITS_G156, 0)
        r1 = verify_saveload_camset_mishoe_genlock_guard(operation="fx6_all_file_load")
        r2 = verify_saveload_camset_mishoe_genlock_guard(
            requested_fx6_dormant_reference_file=True
        )
        self.assertFalse(r1.valid)
        self.assertFalse(r2.valid)
        self.assertEqual(r1.block_errno, EOPNOTSUPP_ERRNO_PHASE359)
        self.assertEqual(r2.block_errno, EOPNOTSUPP_ERRNO_PHASE359)

    def test_54_g156_zero_physical_sync_terminal_rejected_eopnotsupp_95(self) -> None:
        self.assertFalse(FX3_PHYSICAL_SYNC_TERMINAL_PRESENT_G156)
        self.assertEqual(FX3_SYNCHRO_TERMINAL_ELF_HITS_G156, 0)
        r = verify_saveload_camset_mishoe_genlock_guard(
            requested_pc_sync_terminal_or_dormant_flash_spd_prty=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE359)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G156_DORMANT_SYNC_GENLOCK_SLOT2_MR_OR_REFFILE_EOPNOTSUPP,
        )

    def test_55_g156_xlr_h1_vs_hvl_lbpc_and_mi_flash_mutual_exclusion_ebusy_16(self) -> None:
        self.assertTrue(XLR_H1_TOP_SHOES_PASSIVE_COLD_ONLY_G156)
        for dev in ("HVL-LBPC", "MI_FLASH"):
            r = verify_saveload_camset_mishoe_genlock_guard(
                xlr_h1_attached=True,
                mi_shoe_device=dev,
                pmic_5v_current_ma=650,
            )
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EBUSY_ERRNO_PHASE359)
            self.assertEqual(r.status, STATUS_BLOCKED_G156_MISHOE_XLRH1_EXCLUSION_EBUSY)
            self.assertTrue(r.mishoe_xlr_h1_exclusion_triggered)

        r_ok = verify_saveload_camset_mishoe_genlock_guard(
            xlr_h1_attached=False,
            mi_shoe_device="HVL-LBPC",
            video_light_mode="Auto",
            pmic_5v_current_ma=900,
        )
        self.assertTrue(r_ok.valid)

    def test_56_g156_xlr_h1_passive_cold_shoe_contact_claim_rejected(self) -> None:
        r = verify_saveload_camset_mishoe_genlock_guard(
            xlr_h1_attached=True,
            claimed_xlr_h1_shoe_has_mi_contacts=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE359)
        self.assertIn("XLR_H1_PASSIVE_COLD_SHOE_ONLY_VIOLATION", r.violation_codes)

    def test_57_g156_pmic_5v_900ma_overcurrent_firewall(self) -> None:
        self.assertEqual(PMIC_5V_MAX_CURRENT_MA_G156, 900)
        r_ok = verify_saveload_camset_mishoe_genlock_guard(
            mi_shoe_device="HVL-LBPC", pmic_5v_current_ma=900
        )
        r_bad = verify_saveload_camset_mishoe_genlock_guard(
            mi_shoe_device="HVL-LBPC", pmic_5v_current_ma=901
        )
        self.assertTrue(r_ok.valid)
        self.assertFalse(r_bad.valid)
        self.assertTrue(r_bad.pmic_5v_overcurrent_blocked)
        self.assertEqual(r_bad.block_errno, EINVAL_ERRNO_PHASE359)

    def test_58_g156_flash_xsync_250_vs_160_200_vs_320_and_silent_eshutter(self) -> None:
        self.assertEqual(FX3_FLASH_XSYNC_MAX_DENOM_G156, 250)
        self.assertEqual(FX3_FLASH_XSYNC_FF_EFCS_DENOM_G156, 160)
        self.assertEqual(FX3_FLASH_XSYNC_APSC_EFCS_DENOM_G156, 200)
        self.assertEqual(FX3_FLASH_MAX_TRIGGER_VOLTAGE_V_G156, 250.0)

        for denom in (160, 200, 250):
            r_ok = verify_saveload_camset_mishoe_genlock_guard(
                flash_fired=True, shutter_type="Mechanical", shutter_speed_denom=denom
            )
            self.assertTrue(r_ok.valid)

        for kw in (
            {"flash_fired": True, "shutter_type": "Electronic", "shutter_speed_denom": 125},
            {"flash_fired": True, "shutter_type": "Mechanical", "silent_mode": "On"},
            {"flash_fired": True, "shutter_type": "Mechanical", "shutter_speed_denom": 320},
            {"flash_fired": True, "shutter_type": "Mechanical", "flash_voltage_v": 250.0},
            {"flash_fired": True, "shutter_type": "Mechanical", "reverse_polarity": True},
        ):
            r_bad = verify_saveload_camset_mishoe_genlock_guard(**kw)
            self.assertFalse(r_bad.valid)
            self.assertEqual(r_bad.block_errno, EINVAL_ERRNO_PHASE359)

    def test_59_g156_fx6_video_light_zero_auto_zero_flash_and_zero_genlock_eopnotsupp(self) -> None:
        self.assertEqual(len(EXACT_4_FX3_VIDEO_LIGHT_MODES_G156), 4)
        self.assertEqual(len(EXACT_3_FX6_VIDEO_LIGHT_MODES_G156), 3)
        self.assertFalse(FX6_VIDEO_LIGHT_AUTO_SUPPORTED_G156)
        self.assertFalse(FX6_PHYSICAL_GENLOCK_BNC_PRESENT_G156)
        self.assertEqual(FX6_DORMANT_GENLOCK_ELF_HITS_G156, 107)

        for kw in (
            {"requested_fx6_video_light_auto": True},
            {"requested_fx6_still_flash_ui": True},
            {"requested_fx6_dormant_genlock_bnc": True},
        ):
            r = verify_saveload_camset_mishoe_genlock_guard(**kw)
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE359)
            self.assertTrue(r.dormant_or_cross_model_eopnotsupp_rejected)

    def test_60_g156_matrix_384_states_exact(self) -> None:
        mat = compute_saveload_camset_mishoe_genlock_matrix()
        self.assertEqual(mat["total_matrix_states"], 384)
        self.assertEqual(mat["slot1_erofs_blocked_count"], 128)
        self.assertEqual(mat["slot2_camset_rejected_count"], 192)
        self.assertEqual(mat["xlr_h1_mishoe_conflict_count"], 96)
        self.assertEqual(mat["pmic_overcurrent_blocked_count"], 192)
        self.assertEqual(mat["flash_xsync_rejected_count"], 288)
        self.assertEqual(mat["safe_camset_load_count"], 6)

    def test_61_g156_telemetry_validation_all_invalid_inputs(self) -> None:
        for kw in (
            {"body_model_name": "ILCE-7M4"},
            {"operation": "unknown_op"},
            {"target_media": "Slot 3"},
            {"target_media_slot": 9},
            {"card_type": "XQD"},
            {"slot_index": True},
            {"memory_recall_media": "Cloud"},
            {"video_light_mode": "Strobe"},
            {"flash_mode": "TTL"},
            {"shutter_type": "Auto"},
            {"silent_mode": True},
            {"shutter_speed_denom": 0},
            {"flash_voltage_v": -5.0},
            {"mi_shoe_device": "ECM-B1M"},
            {"pmic_5v_current_ma": -1},
            {"reset_action": "Wipe"},
        ):
            r = verify_saveload_camset_mishoe_genlock_guard(**kw)
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G156_TELEMETRY_INVALID)

    def test_62_g156_all_4_video_light_modes_and_5_flash_modes_admitted(self) -> None:
        for vlm in EXACT_4_FX3_VIDEO_LIGHT_MODES_G156:
            for fm in EXACT_5_FX3_FLASH_MODES_G156:
                r = verify_saveload_camset_mishoe_genlock_guard(
                    video_light_mode=vlm, flash_mode=fm
                )
                self.assertTrue(r.valid)

    def test_63_g156_initialize_restores_video_light_and_flash_defaults(self) -> None:
        st = resolve_fx3_saveload_camset_and_mishoe_state(
            video_light_mode="Auto",
            flash_mode="Rear Sync.",
            memory_recall_media="Slot 2",
            reset_action=RESET_ACTION_INITIALIZE_PHASE359,
        )
        self.assertEqual(st["effective_video_light_mode"], "Power Link")
        self.assertEqual(st["effective_flash_mode"], "Autoflash")
        self.assertEqual(st["effective_memory_recall_media"], "Slot 1")

    def test_64_g156_xlr_h1_alone_with_no_electrical_mishoe_light_passes(self) -> None:
        r = verify_saveload_camset_mishoe_genlock_guard(
            xlr_h1_attached=True,
            mi_shoe_device="None",
            pmic_5v_current_ma=450,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.mishoe_xlr_h1_exclusion_triggered)

    def test_65_g156_slot2_target_media_slot_int_maps_to_slot2(self) -> None:
        r = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", target_media_slot=MEDIA_SLOT_2_PHASE359
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE359)
        self.assertEqual(r.effective_target_media, "Slot 2")

    def test_66_g156_evaluate_returns_gate_verdict_and_result(self) -> None:
        v, r = evaluate_g156_saveload_camset_mishoe_genlock_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v.passed)
        self.assertTrue(r.valid)
        self.assertEqual(v.gate_id, G156)

    def test_67_g156_erofs_30_takes_precedence_over_ebusy_or_einval(self) -> None:
        r = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_save",
            target_media="Slot 1",
            xlr_h1_attached=True,
            mi_shoe_device="HVL-LBPC",
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EROFS_ERRNO_PHASE359)
        self.assertEqual(r.status, STATUS_BLOCKED_G156_SLOT1_SAVELOAD_CAMSET_VAULT_EROFS)

    def test_68_g156_ebusy_16_takes_precedence_over_eopnotsupp(self) -> None:
        r = verify_saveload_camset_mishoe_genlock_guard(
            xlr_h1_attached=True,
            mi_shoe_device="HVL-LBPC",
            requested_fx6_dormant_genlock_bnc=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EBUSY_ERRNO_PHASE359)
        self.assertEqual(r.status, STATUS_BLOCKED_G156_MISHOE_XLRH1_EXCLUSION_EBUSY)

    # -----------------------------------------------------------------------
    # 69..96: Unified 156-Gate Master Safety Preflight & CLI Tests
    # -----------------------------------------------------------------------

    def test_69_preflight_156_offline_153_of_156(self) -> None:
        rep = evaluate_156gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema_version, REALHW_156GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(rep.status, "VERIFIED_153_OF_156_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.summary["total_gates"], 156)
        self.assertEqual(rep.summary["verified_gates"], 153)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_153_gates_verified)
        self.assertFalse(rep.all_156_gates_verified)
        self.assertTrue(rep.g155_to_g156_all_passed)
        self.assertTrue(rep.g13_to_g156_all_passed)
        self.assertEqual(len(rep.gates), 156)

    def test_70_preflight_156_dry_run_156_of_156(self) -> None:
        rep = evaluate_156gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(
            rep.status, "VERIFIED_ALL_156_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertEqual(rep.summary["verified_gates"], 156)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_156_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_71_preflight_156_local_donor_mode_when_donors_present(self) -> None:
        rep_cr = evaluate_156gate_preflight(REPO_ROOT, force_clean_room=True)
        rep_norm = evaluate_156gate_preflight(REPO_ROOT)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIn(
            rep_norm.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        self.assertEqual(rep_norm.summary["verified_gates"], 153)

    def test_72_preflight_156_absent_donor_fallback_mocked_work_root_none(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_156gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE359: ""},
                clear=False,
            ):
                rep = evaluate_156gate_preflight(REPO_ROOT, dry_run_simulated=True)
        self.assertEqual(rep.summary["verified_gates"], 156)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_73_preflight_156_request_persistent_emmc_writes_fails_closed(self) -> None:
        rep = evaluate_156gate_preflight(
            REPO_ROOT, force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(rep.offline_153_gates_verified)
        self.assertFalse(rep.all_156_gates_verified)
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertEqual(
            rep.g156_result["status"],
            STATUS_BLOCKED_G156_SLOT1_SAVELOAD_CAMSET_VAULT_EROFS,
        )

    def test_74_preflight_156_fault_propagation_g155_failure(self) -> None:
        rep = evaluate_156gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            areadate_grid_cleanhdmi_kwargs={
                "claimed_marker_outputs_over_hdmi": True
            },
        )
        self.assertFalse(rep.g155_to_g156_all_passed)
        self.assertFalse(rep.g13_to_g156_all_passed)
        self.assertFalse(rep.offline_153_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G155_AREA_RTC_OR_GRID_MARKER_CLEANHDMI_RESET_VIOLATION,
        )

    def test_75_preflight_156_fault_propagation_g156_failure(self) -> None:
        rep = evaluate_156gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            saveload_camset_mishoe_genlock_kwargs={
                "xlr_h1_attached": True,
                "mi_shoe_device": "HVL-LBPC",
            },
        )
        self.assertFalse(rep.g155_to_g156_all_passed)
        self.assertFalse(rep.g13_to_g156_all_passed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G156_MISHOE_XLRH1_EXCLUSION_EBUSY
        )

    def test_76_preflight_156_fault_propagation_g156_slot1_erofs(self) -> None:
        rep = evaluate_156gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            saveload_camset_mishoe_genlock_kwargs={
                "operation": "camset_save",
                "target_media": "Slot 1",
            },
        )
        self.assertFalse(rep.g155_to_g156_all_passed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G156_SLOT1_SAVELOAD_CAMSET_VAULT_EROFS
        )

    def test_77_preflight_156_fault_propagation_m154_failure(self) -> None:
        rep = evaluate_156gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            recall_custom_hold_hdmi_reccontrol_kwargs={
                "requested_write_operation": True,
                "target_media_slot": MEDIA_SLOT_1_PHASE359,
            },
        )
        self.assertFalse(rep.g13_to_g156_all_passed)
        self.assertFalse(rep.offline_153_gates_verified)

    def test_78_preflight_156_all_redline_booleans_false_and_zero(self) -> None:
        rep = evaluate_156gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        for key in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "human_hardware_attach_token",
            "physical_flash_auto_exec_authorized",
            "cross_model_flash_authorized",
            "el3_payload_transmit_authorized",
            "spi_nor_write_authorized",
            "persistent_emmc_writes_authorized",
            "emmc_writes_authorized",
            "persistent_write_release",
        ):
            self.assertFalse(rep.summary[key], f"{key} must remain False")
        self.assertEqual(rep.summary["usb_packets_transmitted"], 0)
        self.assertEqual(rep.summary["physical_usb_packets_emitted"], 0)
        self.assertEqual(rep.summary["raw_firmware_bytes_leaked"], 0)

    def test_79_preflight_156_gate_sequence_g01_to_g156_contiguous(self) -> None:
        rep = evaluate_156gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        gate_ids = [g["gate_id"] for g in rep.gates]
        self.assertEqual(len(gate_ids), 156)
        self.assertEqual(gate_ids[-2], G155)
        self.assertEqual(gate_ids[-1], G156)
        self.assertEqual(len(set(gate_ids)), 156)

    def test_80_preflight_156_no_raw_bytes_repr_in_report_dict(self) -> None:
        rep = evaluate_156gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        dumped = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn('b"\\x7fELF', dumped)

    def test_81_preflight_156_report_has_master_154_and_g155_g156_dicts(self) -> None:
        rep = evaluate_156gate_preflight(REPO_ROOT, force_clean_room=True)
        d = rep.to_dict()
        self.assertIn("master_154_report", d)
        self.assertIn("g155_result", d)
        self.assertIn("g156_result", d)
        self.assertEqual(d["g155_result"]["gate_id"], G155)
        self.assertEqual(d["g156_result"]["gate_id"], G156)

    def test_82_backward_compatibility_154_152_150_148_gates(self) -> None:
        r154 = fx3_safety.evaluate_154gate_preflight(REPO_ROOT, force_clean_room=True)
        r152 = fx3_safety.evaluate_152gate_preflight(REPO_ROOT, force_clean_room=True)
        r150 = fx3_safety.evaluate_150gate_preflight(REPO_ROOT, force_clean_room=True)
        r148 = fx3_safety.evaluate_148gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertEqual(r154.summary["verified_gates"], 151)
        self.assertEqual(r152.summary["verified_gates"], 149)
        self.assertEqual(r150.summary["verified_gates"], 147)
        self.assertEqual(r148.summary["verified_gates"], 145)

    def test_83_simulate_bench_dry_run_alias_kwargs_and_wrapper_fns(self) -> None:
        r1 = evaluate_156_master_safety_gates(
            REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = run_156_gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        r3 = verify_real_hardware_156gate_readiness(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r1.summary["verified_gates"], 156)
        self.assertEqual(r2.summary["verified_gates"], 156)
        self.assertEqual(r3.summary["verified_gates"], 156)

    def test_84_forward_compatible_dynamic_discovery_export(self) -> None:
        nums = sorted(
            int(name[9:-14])
            for name in dir(fx3_safety)
            if name.startswith("evaluate_")
            and name.endswith("gate_preflight")
            and name[9:-14].isdigit()
        )
        self.assertIn(156, nums)
        self.assertGreaterEqual(max(nums), 156)

    def test_85_fx3_safety_package_exports_and_all(self) -> None:
        for sym in (
            "evaluate_156gate_preflight",
            "evaluate_156_master_safety_gates",
            "run_156_gate_preflight",
            "verify_real_hardware_156gate_readiness",
            "evaluate_g155_areadate_dst_grid_cleanhdmi_guard",
            "evaluate_g156_saveload_camset_mishoe_genlock_guard",
            "Master156GateReport",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing export {sym}")
            self.assertIn(sym, fx3_safety.__all__)

    def test_86_master_154_override_injection_works(self) -> None:
        m154 = fx3_safety.evaluate_154gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        rep = evaluate_156gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_154_override=m154,
        )
        self.assertEqual(rep.summary["verified_gates"], 156)

    def test_87_cli_verify_156_gates_text_offline_and_dry_run(self) -> None:
        rc1 = safety_cli.main(["verify-156-gates", "--clean-room"])
        rc2 = safety_cli.main(
            ["verify-156-gates", "--clean-room", "--simulate-bench-dry-run"]
        )
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)

    def test_88_cli_verify_156_gates_json_and_summary(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            rc = safety_cli.main(
                [
                    "verify-156-gates",
                    "--clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                    "--summary",
                ]
            )
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["summary"]["verified_gates"], 156)
        self.assertEqual(parsed["g155_status"], STATUS_VERIFIED_G155)
        self.assertEqual(parsed["g156_status"], STATUS_VERIFIED_G156)

    def test_89_cli_g155_and_g156_aliases_json_summary(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        for cmd in (
            [
                "verify-areadate-grid-cleanhdmi-guard",
                "--clean-room",
                "--json",
                "--summary",
            ],
            [
                "verify-g155-areadate-grid-cleanhdmi",
                "--clean-room",
                "--json",
                "--summary",
            ],
            ["verify-g155", "--clean-room"],
            [
                "verify-saveload-camset-mishoe-genlock-guard",
                "--clean-room",
                "--json",
                "--summary",
            ],
            [
                "verify-g156-saveload-camset-mishoe",
                "--clean-room",
                "--json",
                "--summary",
            ],
            ["verify-g156", "--clean-room"],
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = safety_cli.main(cmd)
            self.assertEqual(rc, 0)

    def test_90_module_main_entrypoint_g155_g156_and_156(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        for argv in (
            ["--clean-room", "--gate", "g155", "--json", "--summary"],
            ["--clean-room", "--gate", "g156", "--json", "--summary"],
            [
                "--clean-room",
                "--gate",
                "156",
                "--simulate-bench-dry-run",
                "--json",
                "--summary",
            ],
            ["--clean-room", "--gate", "156"],
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = module_main(argv)
            self.assertEqual(rc, 0)

    def test_91_cli_help_percent_escaping_clean(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            try:
                safety_cli.main(["--help"])
            except SystemExit as exc:
                self.assertEqual(exc.code, 0)
        help_out = buf.getvalue()
        self.assertIn("verify-156-gates", help_out)
        self.assertIn("verify-g155", help_out)
        self.assertIn("verify-g156", help_out)
        self.assertIn("80%/90%", help_out)
        self.assertIn("%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT", help_out)

    # -----------------------------------------------------------------------
    # 92..104: Extra Wave-68 Edge Cases & Cross-Model Negative Invariants
    # -----------------------------------------------------------------------

    def test_92_g155_hdmi_disconnected_prevents_grid_hdmi_passthrough(self) -> None:
        st = resolve_fx3_areadate_grid_cleanhdmi_state(
            grid_line_display="On",
            hdmi_connected=False,
            hdmi_info_display="On",
        )
        self.assertTrue(st["grid_rendered_on_monitor"])
        self.assertFalse(st["grid_rendered_on_hdmi"])

    def test_93_g155_all_6_half_hour_zones_have_exact_5_suffix(self) -> None:
        for z in AREA_GMT_HALF_HOUR_6_ZONES_G155:
            self.assertTrue(z.endswith("_5"))

    def test_94_g155_rtc_not_depleted_zero_hours_still_retains_charge(self) -> None:
        st = resolve_fx3_areadate_grid_cleanhdmi_state(
            rtc_battery_depleted=False,
            rtc_charge_hours_power_off=0.0,
        )
        self.assertTrue(st["rtc_battery_charged"])

    def test_95_g156_campr_path_formats_sdxc_vs_cfexpress(self) -> None:
        st_sd = resolve_fx3_saveload_camset_and_mishoe_state(
            operation="camera_set_memory_card_recall",
            card_type="SDXC",
            slot_index=2,
        )
        st_cfa = resolve_fx3_saveload_camset_and_mishoe_state(
            operation="camera_set_memory_card_save",
            card_type="CFexpress Type A",
            slot_index=4,
        )
        self.assertEqual(
            st_sd["resolved_setting_path"],
            "/PRIVATE/SONY/SETTING/ILME-FX3/CAMPR02A.DAT",
        )
        self.assertEqual(
            st_cfa["resolved_setting_path"],
            "/SONY/SETTING/ILME-FX3/CAMPR04A.DAT",
        )

    def test_96_g156_ftpset_path_template_verification(self) -> None:
        st = resolve_fx3_saveload_camset_and_mishoe_state(
            operation="ftpset_save", card_type="SDXC", slot_index=3
        )
        self.assertEqual(
            st["resolved_setting_path"],
            "/PRIVATE/SONY/SETTING/ILME-FX3/FTPSET/FTPSET03.DAT",
        )

    def test_97_g156_v101_onto_v200_rejected_while_v200_onto_v702_allowed(self) -> None:
        r_bad = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", source_fw_version="1.01", firmware_version="2.00"
        )
        r_ok = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load", source_fw_version="2.00", firmware_version="7.02"
        )
        self.assertFalse(r_bad.valid)
        self.assertTrue(r_ok.valid)

    def test_98_g156_flash_not_fired_does_not_trip_eshutter_xsync_guard(self) -> None:
        r = verify_saveload_camset_mishoe_genlock_guard(
            flash_fired=False,
            shutter_type="Electronic",
            silent_mode="On",
            shutter_speed_denom=8000,
        )
        self.assertTrue(r.valid)

    def test_99_g156_pmic_5v_boundary_0ma_and_900ma_safe(self) -> None:
        for ma in (0, 500, 900):
            r = verify_saveload_camset_mishoe_genlock_guard(
                mi_shoe_device="MI_FLASH", pmic_5v_current_ma=ma
            )
            self.assertTrue(r.valid)
            self.assertFalse(r.pmic_5v_overcurrent_blocked)

    def test_100_g156_negative_bool_invariants_remain_false(self) -> None:
        _, r155 = evaluate_g155_areadate_dst_grid_cleanhdmi_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        _, r156 = evaluate_g156_saveload_camset_mishoe_genlock_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        g155_d = r155.areadate_grid_cleanhdmi_guard
        g156_d = r156.saveload_camset_mishoe_genlock_guard
        self.assertFalse(g155_d["fx3_user_cr2032_slot_present"])
        self.assertFalse(g155_d["ilc2210_states_3_months_retention"])
        self.assertFalse(g155_d["fx6_clock_set_dst_toggle_exposed"])
        self.assertFalse(g155_d["marker_display_available_in_still"])
        self.assertFalse(g155_d["marker_rendered_on_hdmi"])
        self.assertFalse(g155_d["fx6_native_3mode_grid_exposed"])
        self.assertFalse(g156_d["slot1_tier0_vault_firewall_blocked"])
        self.assertFalse(g156_d["fx3_physical_sync_terminal_present"])
        self.assertFalse(g156_d["mishoe_xlr_h1_exclusion_triggered"])
        self.assertFalse(g156_d["fx6_video_light_auto_supported"])
        self.assertFalse(g156_d["fx6_physical_genlock_bnc_present"])

    def test_101_g155_g156_no_raw_bytes_repr_in_guard_dicts(self) -> None:
        _, g155_res = evaluate_g155_areadate_dst_grid_cleanhdmi_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        _, g156_res = evaluate_g156_saveload_camset_mishoe_genlock_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        for obj in (g155_res.to_dict(), g156_res.to_dict()):
            s = json.dumps(obj, ensure_ascii=False)
            self.assertNotIn("b'\\x7fELF", s)
            self.assertNotIn('b"\\x7fELF', s)

    def test_102_g155_safety_zone_80_and_90_pct_accepted(self) -> None:
        for sz in ("Off", "80%", "90%"):
            r = verify_areadate_dst_grid_cleanhdmi_guard(
                shoot_mode=SHOOT_MODE_MOVIE_PHASE359,
                marker_display="On",
                safety_zone=sz,
            )
            self.assertTrue(r.valid)
            self.assertEqual(r.effective_safety_zone, sz)

    def test_103_g156_zero_pro_camera_zero_ref_file_107_genlock_pinned(self) -> None:
        r = verify_saveload_camset_mishoe_genlock_guard()
        self.assertEqual(r.fx3_pro_camera_path_hits, 0)
        self.assertEqual(r.fx6_reference_file_elf_hits, 0)
        self.assertEqual(r.fx6_dormant_genlock_elf_hits, 107)

    def test_104_g156_camset_load_disabled_in_mr_even_on_cloud(self) -> None:
        r = verify_saveload_camset_mishoe_genlock_guard(
            operation="camset_load",
            target_media="Cloud(Private)",
            mr_recall_mode_active=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE359)


if __name__ == "__main__":
    unittest.main()
