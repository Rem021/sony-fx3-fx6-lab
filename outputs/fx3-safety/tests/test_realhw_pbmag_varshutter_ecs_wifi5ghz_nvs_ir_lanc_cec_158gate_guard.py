"""Comprehensive 4-mode test suite for Phase 363 (`158/158` Hardware Safety Gates):
Gate G157 (Still-Only `Playback -> [Magnification]` / `maginify` Typo / Zero Movie
Playback Zoom vs FX6 `Thumbnail`/`Rec Review`/`Focus Magnifier`, plus Still
`[Anti-flicker Shoot.]` `100/120Hz` vs Dormant `[Var. Shutter]` / `[Anti-flicker
Tv Scan]` `EOPNOTSUPP=95` vs FX6 `ECS 23.99..8000 Hz`),
Gate G158 (`Wi-Fi` `WW728473`/`WW558244` 5GHz SKU Lock + `WPA2/WPA3`-Only +
`[Airplane Mode]` Survives `[Reset Network Set.]` + `p12/p13` `MS_RDONLY` RF NVS
Firewall, plus Front `#5` `[IR Remote Ctrl]` vs `FX3A` Removal & `[CTRL FOR HDMI]`
`ctrl_for_hmdi` Default-`On` 41-Key CEC Bench Hijack Firewall / Zero `LANC` vs FX6
`2.5mm LANC` & `3.5mm Grip`), and Unified 158-Gate Master Safety Preflight (`G01..G158`).
"""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
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
from fx3_safety.realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard import (  # noqa: E402
    AIRPLANE_MODE_SURVIVES_RESET_NETWORK_G158,
    ANTI_FLICKER_MAINS_FREQS_HZ_G157,
    ANTI_FLICKER_SHOOT_DEFAULT_G157,
    ANTI_FLICKER_SHOOT_MENU_PATH_G157,
    ANTI_FLICKER_SHOOT_RESETTABLE_BY_CAMSET_RESET_G157,
    CTRL_FOR_HDMI_ELF_TYPO_G158,
    CTRL_FOR_HDMI_FACTORY_DEFAULT_G158,
    CTRL_FOR_HDMI_MENU_PATH_G158,
    CTRL_FOR_HDMI_RESETTABLE_BY_CAMSET_RESET_G158,
    DONOR_CHECK_MAX_SECONDS_PHASE363,
    EBUSY_ERRNO_PHASE363,
    EINVAL_ERRNO_PHASE363,
    ENLARGE_INITIAL_MAG_DEFAULT_G157,
    ENLARGE_INITIAL_POS_DEFAULT_G157,
    ENV_CLEAN_ROOM_TEST_PHASE363,
    EOPNOTSUPP_ERRNO_PHASE363,
    EROFS_ERRNO_PHASE363,
    EXACT_3_PLAYBACK_MAGNIFY_ITEMS_G157,
    EXACT_41_FX3_CEC_KEY_EVENTS_G158,
    EXACT_6_WIFI_MENU_ITEMS_G158,
    FX3A_MODEL_NAME_PHASE363,
    FX3A_PHYSICAL_IR_SENSOR_PRESENT_G158,
    FX3_ACTIVE_LANC_BKID_HITS_G158,
    FX3_AF_ILLUMINATOR_SENSOR_NUM_G158,
    FX3_ANTI_FLICKER_SET_EXPOSED_G157,
    FX3_ANTI_FLICKER_TV_SCAN_EXPOSED_G157,
    FX3_CEC_REC_EVENT_COUNT_G158,
    FX3_DEFAULT_FW_VERSION_PHASE363,
    FX3_HELP_GUIDE_CODE_PHASE363,
    FX3_IR_FRONT_SENSOR_NUM_G158,
    FX3_MODEL_ID_PHASE363,
    FX3_MODEL_NAME_PHASE363,
    FX3_PHYSICAL_GRIP_REMOTE_35MM_PRESENT_G158,
    FX3_PHYSICAL_LANC_25MM_PRESENT_G158,
    FX3_SC_TV_SCAN_0X60A8_EMPTY_STRING_G157,
    FX3_VAR_SHUTTER_EXPOSED_G157,
    FX3_WIFI_SKU_WW558244_G158,
    FX3_WIFI_SKU_WW728473_G158,
    FX6_ECS_6_FRAME_RATE_PRESETS_G157,
    FX6_ECS_FREQ_MAX_HZ_G157,
    FX6_ECS_FREQ_MIN_HZ_G157,
    FX6_EXPOSED_IR_OR_CEC_MENUS_G158,
    FX6_GRIP_REMOTE_35MM_POLES_G158,
    FX6_LANC_25MM_PORT_NUM_G158,
    FX6_STILL_OR_PB_ENLARGE_SUPPORTED_G157,
    FX6_WIFI_SKU_24GHZ_G158,
    FX6_WIFI_SKU_5GHZ_G158,
    G157,
    G158,
    IR_REMOTE_CTRL_DEFAULT_G158,
    IR_REMOTE_CTRL_MENU_PATH_G158,
    IR_REMOTE_CTRL_RESETTABLE_BY_CAMSET_RESET_G158,
    MOVIE_PLAYBACK_ZOOM_SUPPORTED_G157,
    Master158GateReport,
    P12_CERT_SIZE_MIB_G158,
    P12_P13_MS_RDONLY_ENFORCED_G158,
    P13_RF_NVS_SIZE_MIB_G158,
    PINNED_FX3_APPFW_SLICES_PHASE363,
    PINNED_FX6_APPFW_SLICES_PHASE363,
    PINNED_PHASE363_DONOR_SPECS,
    PLAYBACK_MAGNIFICATION_MENU_PATH_G157,
    PLAYBACK_MAGNIFY_RESETTABLE_BY_CAMSET_RESET_G157,
    PLAYBACK_ZOOM_INHIBITION_TEXT_G157,
    PLAYBACK_ZOOM_MAGINIFY_ELF_TYPO_G157,
    REALHW_158GATE_PREFLIGHT_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE363,
    RESET_ACTION_INITIALIZE_PHASE363,
    RESET_ACTION_NONE_PHASE363,
    RESET_ACTION_RESET_NETWORK_SET_PHASE363,
    RF_NVS_MUTATION_BYTES_G158,
    RF_TX_PACKETS_AIRPLANE_G158,
    SHOOT_MODE_MOVIE_PHASE363,
    SHOOT_MODE_SQ_PHASE363,
    SHOOT_MODE_STILL_PHASE363,
    STATUS_BLOCKED_G157_MOVIE_ZOOM_OR_DORMANT_VAR_SHUTTER_EOPNOTSUPP,
    STATUS_BLOCKED_G157_PBMAG_RESET_OR_ANTI_FLICKER_CONSTRAINT_VIOLATION,
    STATUS_BLOCKED_G157_TELEMETRY_INVALID,
    STATUS_BLOCKED_G158_AIRPLANE_RF_OR_CTRL_FOR_HDMI_CEC_HIJACK_VIOLATION,
    STATUS_BLOCKED_G158_BT_IR_OR_FX6_WLAN_MUTEX_EBUSY,
    STATUS_BLOCKED_G158_P12_P13_RF_NVS_MS_RDONLY_EROFS,
    STATUS_BLOCKED_G158_SKU_LEGACY_SEC_FX3A_IR_OR_LANC_EOPNOTSUPP,
    STATUS_BLOCKED_G158_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE363_DONOR_INTEGRITY,
    STATUS_VERIFIED_G157,
    STATUS_VERIFIED_G158,
    VER7_ALLOWED_WIFI_SECURITY_PROTOCOLS_G158,
    VER7_REMOVED_WIFI_SECURITY_PROTOCOLS_G158,
    WIFI_MENU_PATH_G158,
    WIFI_SKU_GATE_FN_G158,
    audit_phase363_donor_contracts,
    compute_pbmag_varshutter_ecs_matrix,
    compute_wifi5ghz_nvs_ir_lanc_cec_matrix,
    evaluate_158_master_safety_gates,
    evaluate_158gate_preflight,
    evaluate_g157_pbmag_varshutter_ecs_guard,
    evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard,
    main as guard_module_main,
    resolve_fx3_pbmag_varshutter_ecs_state,
    resolve_fx3_wifi5ghz_nvs_ir_lanc_cec_state,
    run_158_gate_preflight,
    strip_elapsed_seconds_recursive_phase363,
    verify_pbmag_varshutter_ecs_guard,
    verify_pbmag_varshutter_ecs_guard_with_audit,
    verify_real_hardware_158gate_readiness,
    verify_wifi5ghz_nvs_ir_lanc_cec_guard,
    verify_wifi5ghz_nvs_ir_lanc_cec_guard_with_audit,
)


def _mock_paths_work_root_none(**_kwargs):
    return mock.MagicMock(work_root=None)


class TestPhase363HardwareSafety158Gates(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Integrity & 4-Mode Checks (01..12)
    # ------------------------------------------------------------------

    def test_01_donor_specs_pin_15_artifacts_and_fast_budget(self) -> None:
        self.assertEqual(len(PINNED_PHASE363_DONOR_SPECS), 15)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE363), 26)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE363), 11)
        audit = audit_phase363_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_200ms)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE363)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_02_donor_audit_normal_mode_matches_expected(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE363: ""},
            clear=False,
        ):
            audit = audit_phase363_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertIn(
            audit.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        if audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(audit.files_inspected, 15)
            self.assertEqual(audit.access_mode, "STRICT_OS_O_RDONLY_PREAD")

    def test_03_donor_audit_fx3_clean_room_test_env_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ENV_CLEAN_ROOM_TEST_PHASE363: "1", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            clear=False,
        ):
            audit = audit_phase363_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_DISK_IO")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_04_donor_audit_force_clean_room_env_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1", ENV_CLEAN_ROOM_TEST_PHASE363: ""},
            clear=False,
        ):
            audit = audit_phase363_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.files_inspected, 0)

    def test_05_donor_audit_mocked_work_root_none_fallback(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE363: ""},
                clear=False,
            ):
                audit = audit_phase363_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_donor_audit_absent_temp_work_root_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = audit_phase363_donor_contracts(
                repo_root=REPO_ROOT,
                work_root=Path(tmpdir),
                force_clean_room=False,
            )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")

    def test_07_donor_audit_override_detects_missing_or_corrupt_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_spec = {
                "tiny": (
                    "FX3",
                    "missing.bin",
                    16,
                    "0" * 64,
                    (b"NEEDLE",),
                    "test missing",
                )
            }
            audit = audit_phase363_donor_contracts(
                work_root=Path(tmpdir),
                force_clean_room=False,
                donor_specs_override=bad_spec,
            )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE363_DONOR_INTEGRITY)
        self.assertIn("tiny:file_missing", audit.missing_markers)

    def test_08_donor_audit_override_detects_sha256_and_token_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "blob.bin"
            p.write_bytes(b"INVALID_CONTENT")
            bad_spec = {
                "blob": (
                    "FX3",
                    "blob.bin",
                    15,
                    "f" * 64,
                    (b"EXPECTED_TOKEN",),
                    "tampered",
                )
            }
            audit = audit_phase363_donor_contracts(
                work_root=Path(tmpdir),
                force_clean_room=False,
                donor_specs_override=bad_spec,
            )
        self.assertFalse(audit.valid)
        self.assertIn("blob:sha256_mismatch", audit.missing_markers)
        self.assertIn("blob:token_missing_idx_0", audit.missing_markers)

    def test_09_strip_elapsed_seconds_recursive_phase363_determinism(self) -> None:
        a = {
            "elapsed_seconds": 0.011,
            "nested": [{"elapsed_seconds": 0.022, "val": 1}],
            "tuple_val": ({"elapsed_seconds": 0.033, "ok": True},),
        }
        b = {
            "elapsed_seconds": 0.999,
            "nested": [{"elapsed_seconds": 0.888, "val": 1}],
            "tuple_val": ({"elapsed_seconds": 0.777, "ok": True},),
        }
        self.assertEqual(
            strip_elapsed_seconds_recursive_phase363(a),
            strip_elapsed_seconds_recursive_phase363(b),
        )
        self.assertNotIn("elapsed_seconds", strip_elapsed_seconds_recursive_phase363(a))

    def test_10_clean_room_vs_local_donor_file_digests_match(self) -> None:
        cr = audit_phase363_donor_contracts(repo_root=REPO_ROOT, force_clean_room=True)
        norm = audit_phase363_donor_contracts(repo_root=REPO_ROOT, force_clean_room=False)
        self.assertEqual(cr.file_digests, norm.file_digests)

    def test_11_preflight_158_passes_across_all_4_modes(self) -> None:
        # Mode 1: normal
        r1 = evaluate_158gate_preflight(REPO_ROOT, dry_run_simulated=True)
        # Mode 2: FX3_CLEAN_ROOM_TEST=1
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE363: "1"}, clear=False):
            r2 = evaluate_158gate_preflight(REPO_ROOT, dry_run_simulated=True)
        # Mode 3: FX3_FX6_FORCE_CLEAN_ROOM=1
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            r3 = evaluate_158gate_preflight(REPO_ROOT, dry_run_simulated=True)
        # Mode 4: mocked work_root=None
        with mock.patch(
            "fx3_safety.realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE363: ""},
                clear=False,
            ):
                r4 = evaluate_158gate_preflight(REPO_ROOT, dry_run_simulated=True)
        for rep in (r1, r2, r3, r4):
            self.assertTrue(rep.all_158_gates_verified)
            self.assertEqual(rep.summary["verified_gates"], 158)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_12_four_mode_g157_g158_canonical_digest_equivalence(self) -> None:
        d1 = strip_elapsed_seconds_recursive_phase363(
            evaluate_g157_pbmag_varshutter_ecs_guard(
                repo_root=REPO_ROOT, force_clean_room=True
            )[1].donor_audit["file_digests"]
        )
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE363: "1"}, clear=False):
            d2 = strip_elapsed_seconds_recursive_phase363(
                evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard(
                    repo_root=REPO_ROOT
                )[1].donor_audit["file_digests"]
            )
        self.assertEqual(d1, d2)

    # ------------------------------------------------------------------
    # Gate G157 Tests: Playback [Magnification] & [Anti-flicker Shoot.] vs
    #                  Dormant [Var. Shutter] / [Anti-flicker Tv Scan] / FX6 ECS (13..42)
    # ------------------------------------------------------------------

    def test_13_g157_default_baseline_passes(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G157)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.playback_magnify_items_count, 3)
        self.assertFalse(res.movie_playback_zoom_supported)
        self.assertFalse(res.fx3_var_shutter_exposed)
        self.assertFalse(res.fx3_anti_flicker_tv_scan_exposed)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_14_g157_pinned_contracts_and_typos(self) -> None:
        self.assertEqual(len(EXACT_3_PLAYBACK_MAGNIFY_ITEMS_G157), 3)
        self.assertEqual(PLAYBACK_ZOOM_MAGINIFY_ELF_TYPO_G157, "playback_zoom_maginify_by_pinch")
        self.assertEqual(PLAYBACK_ZOOM_INHIBITION_TEXT_G157, "Unable to magnify.")
        self.assertFalse(PLAYBACK_MAGNIFY_RESETTABLE_BY_CAMSET_RESET_G157)
        self.assertTrue(ANTI_FLICKER_SHOOT_RESETTABLE_BY_CAMSET_RESET_G157)
        self.assertTrue(FX3_SC_TV_SCAN_0X60A8_EMPTY_STRING_G157)
        self.assertEqual(ANTI_FLICKER_MAINS_FREQS_HZ_G157, (100, 120))
        self.assertEqual(len(FX6_ECS_6_FRAME_RATE_PRESETS_G157), 6)

    def test_15_g157_still_enlarge_wt_lever_and_standard_mag(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard(
            playback_media_kind="still",
            playback_operation="wt_lever",
            enlarge_initial_mag="Standard. Mag.",
            requested_mag_factor=3.5,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_mag_factor, 3.5)
        self.assertEqual(res.effective_enlarge_initial_mag, "Standard. Mag.")

    def test_16_g157_still_previous_mag_uses_previous_factor(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard(
            playback_media_kind="still",
            playback_operation="enlarge_image",
            enlarge_initial_mag="Previous Mag.",
            previous_mag_factor=5.0,
            requested_mag_factor=2.0,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_mag_factor, 5.0)

    def test_17_g157_focused_position_falls_back_to_center_when_no_af_point(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard(
            playback_media_kind="still",
            enlarge_initial_position="Focused Position",
            focus_position_available=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.focused_fallback_to_center)
        self.assertEqual(res.effective_enlarge_initial_position, "Center")

    def test_18_g157_dial_step_retains_zoom_across_photos(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard(
            playback_media_kind="still",
            playback_operation="dial_step_photo",
            previous_mag_factor=4.0,
            enlarge_initial_mag="Previous Mag.",
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.zoom_preserved_across_photo_step)
        self.assertEqual(res.effective_mag_factor, 4.0)

    def test_19_g157_pinch_and_double_tap_allowed_with_touch_operation_on(self) -> None:
        for op in ("pinch_zoom", "double_tap"):
            res = verify_pbmag_varshutter_ecs_guard(
                playback_media_kind="still",
                playback_operation=op,
                touch_operation="On",
            )
            self.assertTrue(res.valid, f"Expected pass for {op} with touch=On")

    def test_20_g157_pinch_and_double_tap_blocked_when_touch_operation_off(self) -> None:
        for op in ("pinch_zoom", "double_tap"):
            res = verify_pbmag_varshutter_ecs_guard(
                playback_media_kind="still",
                playback_operation=op,
                touch_operation="Off",
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE363)
            self.assertIn("PINCH_OR_DOUBLETAP_REQUIRES_TOUCH_OPERATION_ON", res.violation_codes)

    def test_21_g157_playback_magnification_survives_camera_settings_reset(self) -> None:
        st = resolve_fx3_pbmag_varshutter_ecs_state(
            enlarge_initial_mag="Previous Mag.",
            enlarge_initial_position="Center",
            anti_flicker_shoot="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE363,
        )
        self.assertEqual(st["effective_enlarge_initial_mag"], "Previous Mag.")
        self.assertEqual(st["effective_enlarge_initial_position"], "Center")
        self.assertEqual(st["effective_anti_flicker_shoot"], "Off")

    def test_22_g157_initialize_clears_both_playback_mag_and_anti_flicker(self) -> None:
        st = resolve_fx3_pbmag_varshutter_ecs_state(
            enlarge_initial_mag="Previous Mag.",
            enlarge_initial_position="Center",
            anti_flicker_shoot="On",
            reset_action=RESET_ACTION_INITIALIZE_PHASE363,
        )
        self.assertEqual(st["effective_enlarge_initial_mag"], ENLARGE_INITIAL_MAG_DEFAULT_G157)
        self.assertEqual(st["effective_enlarge_initial_position"], ENLARGE_INITIAL_POS_DEFAULT_G157)
        self.assertEqual(st["effective_anti_flicker_shoot"], ANTI_FLICKER_SHOOT_DEFAULT_G157)

    def test_23_g157_claimed_camset_reset_clears_playback_magnify_blocked(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard(
            claimed_camset_reset_clears_playback_magnify=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE363)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G157_PBMAG_RESET_OR_ANTI_FLICKER_CONSTRAINT_VIOLATION
        )

    def test_24_g157_movie_playback_zoom_hard_prohibited_eopnotsupp(self) -> None:
        for op in ("enlarge_image", "wt_lever", "pinch_zoom", "double_tap", "dial_step_photo"):
            res = verify_pbmag_varshutter_ecs_guard(
                playback_media_kind="movie",
                playback_operation=op,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE363)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G157_MOVIE_ZOOM_OR_DORMANT_VAR_SHUTTER_EOPNOTSUPP,
            )
            self.assertIn("MOVIE_PLAYBACK_ZOOM_PROHIBITED_EOPNOTSUPP", res.violation_codes)

    def test_25_g157_movie_menu_exit_safe(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard(
            playback_media_kind="movie",
            playback_operation="menu_exit",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_mag_factor, 1.0)

    def test_26_g157_fx6_still_or_pb_enlarge_claim_rejected_eopnotsupp(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard(
            requested_fx6_still_or_playback_enlarge=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE363)
        self.assertFalse(res.fx6_still_or_pb_enlarge_supported)

    def test_27_g157_still_mechanical_anti_flicker_shoot_100hz_120hz_allowed(self) -> None:
        for hz in (100, 120):
            res = verify_pbmag_varshutter_ecs_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE363,
                shutter_type="Mechanical",
                silent_mode="Off",
                bulb_mode=False,
                anti_flicker_shoot="On",
                mains_hz=hz,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.anti_flicker_shoot_enabled_allowed)
            self.assertTrue(res.anti_flicker_effective_for_mains_hz)

    def test_28_g157_anti_flicker_on_blocked_in_movie_and_sq(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE363, SHOOT_MODE_SQ_PHASE363):
            res = verify_pbmag_varshutter_ecs_guard(
                shoot_mode=sm,
                anti_flicker_shoot="On",
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE363)
            self.assertIn("ANTI_FLICKER_SHOOT_MODE_OR_SHUTTER_INHIBITED", res.violation_codes)

    def test_29_g157_anti_flicker_on_blocked_in_eshutter_silent_and_bulb(self) -> None:
        for kw in (
            {"shutter_type": "Electronic"},
            {"silent_mode": "On"},
            {"bulb_mode": True},
        ):
            res = verify_pbmag_varshutter_ecs_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE363,
                anti_flicker_shoot="On",
                **kw,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE363)
            self.assertFalse(res.anti_flicker_shoot_enabled_allowed)

    def test_30_g157_dormant_var_shutter_set_and_tv_scan_blocked_eopnotsupp(self) -> None:
        for kw in (
            {"requested_dormant_anti_flicker_set": True},
            {"requested_dormant_var_shutter": True},
            {"requested_dormant_var_shutter_set": True},
            {"requested_dormant_anti_flicker_tv_scan": True},
            {"requested_fx6_ecs_on_fx3": True},
        ):
            res = verify_pbmag_varshutter_ecs_guard(**kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE363)
            self.assertTrue(res.dormant_or_cross_model_eopnotsupp_rejected)

    def test_31_g157_claimed_anti_flicker_reset_immune_rejected(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard(
            claimed_anti_flicker_reset_immune=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE363)

    def test_32_g157_fx6_ecs_frequency_range_bounds_enforced(self) -> None:
        self.assertTrue(verify_pbmag_varshutter_ecs_guard(fx6_ecs_freq_hz=FX6_ECS_FREQ_MIN_HZ_G157).valid)
        self.assertTrue(verify_pbmag_varshutter_ecs_guard(fx6_ecs_freq_hz=FX6_ECS_FREQ_MAX_HZ_G157).valid)
        self.assertFalse(verify_pbmag_varshutter_ecs_guard(fx6_ecs_freq_hz=23.98).valid)
        self.assertFalse(verify_pbmag_varshutter_ecs_guard(fx6_ecs_freq_hz=8000.01).valid)

    def test_33_g157_fx6_ecs_6_frame_rate_presets_resolve_correctly(self) -> None:
        for fps, expected_hz in FX6_ECS_6_FRAME_RATE_PRESETS_G157.items():
            res = verify_pbmag_varshutter_ecs_guard(fx6_ecs_frame_rate=fps)
            self.assertTrue(res.valid)
            self.assertEqual(res.fx6_ecs_freq_hz, expected_hz)

    def test_34_g157_telemetry_invalid_inputs_rejected(self) -> None:
        for bad_kw in (
            {"body_model_name": "ILCE-7SM3"},
            {"body_model_id": 0x9999},
            {"help_guide_code": "ilc/9999"},
            {"firmware_version": "not_a_ver"},
            {"playback_media_kind": "raw"},
            {"playback_operation": "telephoto"},
            {"enlarge_initial_mag": "x100"},
            {"enlarge_initial_position": "TopLeft"},
            {"touch_operation": "Maybe"},
            {"previous_mag_factor": 0.5},
            {"requested_mag_factor": 0.1},
            {"shoot_mode": "Panorama"},
            {"shutter_type": "Auto"},
            {"silent_mode": "1"},
            {"anti_flicker_shoot": "Auto"},
            {"mains_hz": 0},
            {"fx6_ecs_frame_rate": "120P"},
            {"fx6_flicker_reduce_mode": "Always"},
            {"fx6_flicker_reduce_freq": "75Hz"},
            {"reset_action": "Wipe"},
        ):
            res = verify_pbmag_varshutter_ecs_guard(**bad_kw)
            self.assertFalse(res.valid, f"Expected invalid for {bad_kw}")
            self.assertEqual(res.status, STATUS_BLOCKED_G157_TELEMETRY_INVALID)

    def test_35_g157_strict_int_rejects_booleans_for_mains_hz_and_model_id(self) -> None:
        res1 = verify_pbmag_varshutter_ecs_guard(mains_hz=True)
        res2 = verify_pbmag_varshutter_ecs_guard(body_model_id=True)
        self.assertFalse(res1.valid)
        self.assertFalse(res2.valid)
        self.assertEqual(res1.status, STATUS_BLOCKED_G157_TELEMETRY_INVALID)

    def test_36_g157_384_state_combinatoric_matrix(self) -> None:
        m = compute_pbmag_varshutter_ecs_matrix()
        self.assertEqual(m["total_matrix_states"], 384)
        self.assertEqual(m["movie_zoom_blocked_count"], 192)
        self.assertEqual(m["playback_magnify_reset_preserved_count"], 192)
        self.assertEqual(m["anti_flicker_reset_cleared_count"], 96)
        self.assertEqual(m["anti_flicker_eligible_count"], 32)
        self.assertEqual(m["anti_flicker_disabled_blocked_count"], 176)

    def test_37_g157_menu_paths_and_flags_preserved(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard()
        self.assertEqual(res.playback_magnification_menu_path, PLAYBACK_MAGNIFICATION_MENU_PATH_G157)
        self.assertEqual(res.anti_flicker_shoot_menu_path, ANTI_FLICKER_SHOOT_MENU_PATH_G157)
        self.assertFalse(res.emmc_writes_authorized)
        self.assertFalse(res.cross_model_flash_authorized)
        self.assertEqual(res.usb_packets_transmitted, 0)

    def test_38_g157_evaluate_wrapper_and_with_audit_clean_room(self) -> None:
        v1, r1 = evaluate_g157_pbmag_varshutter_ecs_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        v2, r2 = verify_pbmag_varshutter_ecs_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v1.passed and r1.valid)
        self.assertTrue(v2.passed and r2.valid)
        self.assertEqual(v1.gate_id, G157)
        self.assertEqual(r1.status, STATUS_VERIFIED_G157)

    def test_39_g157_evaluate_propagates_fault_to_verdict(self) -> None:
        v, r = evaluate_g157_pbmag_varshutter_ecs_guard(
            repo_root=REPO_ROOT,
            force_clean_room=True,
            requested_dormant_var_shutter=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertEqual(
            v.status, STATUS_BLOCKED_G157_MOVIE_ZOOM_OR_DORMANT_VAR_SHUTTER_EOPNOTSUPP
        )

    def test_40_g157_anti_flicker_mains_non_100_120hz_not_effective(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE363,
            anti_flicker_shoot="On",
            mains_hz=50,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.anti_flicker_effective_for_mains_hz)

    def test_41_g157_fx6_inactive_vars_remain_false(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard()
        self.assertFalse(res.fx3_var_shutter_exposed)
        self.assertFalse(res.fx3_anti_flicker_set_exposed)
        self.assertFalse(res.fx3_anti_flicker_tv_scan_exposed)
        self.assertFalse(FX6_STILL_OR_PB_ENLARGE_SUPPORTED_G157)

    def test_42_g157_movie_playback_zoom_claim_rejected(self) -> None:
        res = verify_pbmag_varshutter_ecs_guard(
            claimed_movie_playback_zoom_supported=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE363)

    # ------------------------------------------------------------------
    # Gate G158 Tests: Wi-Fi 5GHz SKU / p12-p13 NVS & IR / CTRL FOR HDMI / Zero LANC (43..76)
    # ------------------------------------------------------------------

    def test_43_g158_default_baseline_passes(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G158)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.cec_key_events_count, 41)
        self.assertEqual(res.cec_rec_event_count, 0)
        self.assertTrue(res.p12_p13_ms_readonly_enforced)
        self.assertEqual(res.rf_nvs_mutation_bytes, 0)
        self.assertFalse(res.fx3_physical_lanc_25mm_present)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_44_g158_pinned_contracts_and_typos(self) -> None:
        self.assertEqual(len(EXACT_6_WIFI_MENU_ITEMS_G158), 6)
        self.assertEqual(len(EXACT_41_FX3_CEC_KEY_EVENTS_G158), 41)
        self.assertEqual(FX3_CEC_REC_EVENT_COUNT_G158, 0)
        self.assertEqual(CTRL_FOR_HDMI_ELF_TYPO_G158, "BKID_APP_setting_ctrl_for_hmdi")
        self.assertEqual(CTRL_FOR_HDMI_FACTORY_DEFAULT_G158, "On")
        self.assertFalse(CTRL_FOR_HDMI_RESETTABLE_BY_CAMSET_RESET_G158)
        self.assertFalse(IR_REMOTE_CTRL_RESETTABLE_BY_CAMSET_RESET_G158)
        self.assertTrue(AIRPLANE_MODE_SURVIVES_RESET_NETWORK_G158)
        self.assertEqual(P12_CERT_SIZE_MIB_G158, 40)
        self.assertEqual(P13_RF_NVS_SIZE_MIB_G158, 4)
        self.assertEqual(WIFI_SKU_GATE_FN_G158, "lib::backup_get_wi_fi_frequency_band_dst")

    def test_45_g158_ww728473_allows_24ghz_and_5ghz_indoor(self) -> None:
        for band in ("2.4GHz", "5GHz"):
            res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
                wifi_sku_code=FX3_WIFI_SKU_WW728473_G158,
                requested_band=band,
                outdoor_5ghz_restricted=False,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.wifi_available_bands, ("2.4GHz", "5GHz"))
            self.assertEqual(res.effective_wifi_band, band)

    def test_46_g158_ww558244_blocks_5ghz_eopnotsupp(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            wifi_sku_code=FX3_WIFI_SKU_WW558244_G158,
            requested_band="5GHz",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE363)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G158_SKU_LEGACY_SEC_FX3A_IR_OR_LANC_EOPNOTSUPP
        )
        self.assertEqual(res.wifi_available_bands, ("2.4GHz",))
        self.assertEqual(res.effective_wifi_band, "2.4GHz")

    def test_47_g158_ww558244_allows_24ghz(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            wifi_sku_code=FX3_WIFI_SKU_WW558244_G158,
            requested_band="2.4GHz",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_wifi_band, "2.4GHz")

    def test_48_g158_outdoor_5ghz_restricted_blocks_and_forces_24ghz(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            wifi_sku_code=FX3_WIFI_SKU_WW728473_G158,
            requested_band="5GHz",
            outdoor_5ghz_restricted=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE363)
        self.assertEqual(res.effective_wifi_band, "2.4GHz")

    def test_49_g158_ver7_allows_wpa2_psk_and_wpa3_sae_only(self) -> None:
        for proto in VER7_ALLOWED_WIFI_SECURITY_PROTOCOLS_G158:
            res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
                wifi_security=proto,
                access_authen="On",
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_wifi_security, proto)

    def test_50_g158_ver7_rejects_deprecated_wep_wpa_ipsec_open(self) -> None:
        for proto in VER7_REMOVED_WIFI_SECURITY_PROTOCOLS_G158:
            res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(wifi_security=proto)
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE363)
            self.assertIn("WIFI_DEPRECATED_SECURITY_REMOVED_EOPNOTSUPP", res.violation_codes)

    def test_51_g158_ver7_requires_access_authen_on(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            firmware_version="7.02",
            access_authen="Off",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE363)
        self.assertIn("VER7_ACCESS_AUTHEN_ON_MANDATORY", res.violation_codes)

    def test_52_g158_ap_connect_requires_wifi_connect_on(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            wifi_operation="ap_connect",
            wifi_connect="Off",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE363)
        self.assertIn("AP_CONNECT_REQUIRES_WIFI_CONNECT_ON", res.violation_codes)

    def test_53_g158_airplane_mode_survives_reset_network_set_only_initialize_clears(self) -> None:
        st_net = resolve_fx3_wifi5ghz_nvs_ir_lanc_cec_state(
            airplane_mode="On",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE363,
        )
        st_cam = resolve_fx3_wifi5ghz_nvs_ir_lanc_cec_state(
            airplane_mode="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE363,
        )
        st_init = resolve_fx3_wifi5ghz_nvs_ir_lanc_cec_state(
            airplane_mode="On",
            reset_action=RESET_ACTION_INITIALIZE_PHASE363,
        )
        self.assertEqual(st_net["effective_airplane_mode"], "On")
        self.assertEqual(st_cam["effective_airplane_mode"], "On")
        self.assertEqual(st_init["effective_airplane_mode"], "Off")

    def test_54_g158_airplane_mode_blocks_rf_tx_and_rejects_reset_network_myth(self) -> None:
        res_tx = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            airplane_mode="On",
            rf_tx_requested=True,
        )
        res_myth = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            claimed_reset_network_clears_airplane=True,
        )
        self.assertFalse(res_tx.valid)
        self.assertEqual(res_tx.rf_tx_packets, 0)
        self.assertEqual(res_tx.block_errno, EINVAL_ERRNO_PHASE363)
        self.assertFalse(res_myth.valid)

    def test_55_g158_p12_and_p13_ms_rdonly_blocks_writes_with_erofs_30(self) -> None:
        for kw in (
            {"target_partition": "p12_cert"},
            {"target_partition": "p13_rfnvs"},
            {"wifi_operation": "rf_nvs_write_attempt"},
            {"requested_p12_p13_write": True},
        ):
            res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(**kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE363)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G158_P12_P13_RF_NVS_MS_RDONLY_EROFS
            )
            self.assertEqual(res.rf_nvs_mutation_bytes, 0)
            self.assertEqual(res.emmc_nflasha_write_count, 0)

    def test_56_g158_ir_remote_ctrl_front_pin5_and_power_save_bypass(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            fx3_body_variant=FX3_MODEL_NAME_PHASE363,
            ir_remote_ctrl="On",
            bluetooth_rmt_ctrl="Off",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.fx3_ir_front_sensor_num, 5)
        self.assertEqual(res.fx3_af_illuminator_sensor_num, 8)
        self.assertTrue(res.power_save_bypassed_by_ir)

    def test_57_g158_fx3a_physically_removed_ir_sensor_blocks_ir_on_eopnotsupp(self) -> None:
        res_on = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            fx3_body_variant=FX3A_MODEL_NAME_PHASE363,
            ir_remote_ctrl="On",
        )
        res_off = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            fx3_body_variant=FX3A_MODEL_NAME_PHASE363,
            ir_remote_ctrl="Off",
        )
        self.assertFalse(res_on.valid)
        self.assertEqual(res_on.block_errno, EOPNOTSUPP_ERRNO_PHASE363)
        self.assertIsNone(res_on.fx3_ir_front_sensor_num)
        self.assertFalse(FX3A_PHYSICAL_IR_SENSOR_PRESENT_G158)
        self.assertTrue(res_off.valid)

    def test_58_g158_bt_remote_and_ir_remote_mutual_exclusion_ebusy_16(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            ir_remote_ctrl="On",
            bluetooth_rmt_ctrl="On",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EBUSY_ERRNO_PHASE363)
        self.assertEqual(res.status, STATUS_BLOCKED_G158_BT_IR_OR_FX6_WLAN_MUTEX_EBUSY)
        self.assertTrue(res.bt_ir_mutex_triggered)

    def test_59_g158_ir_and_ctrl_for_hdmi_survive_camset_reset_initialize_restores_defaults(self) -> None:
        st_rst = resolve_fx3_wifi5ghz_nvs_ir_lanc_cec_state(
            ir_remote_ctrl="On",
            ctrl_for_hdmi="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE363,
        )
        st_init = resolve_fx3_wifi5ghz_nvs_ir_lanc_cec_state(
            ir_remote_ctrl="On",
            ctrl_for_hdmi="Off",
            reset_action=RESET_ACTION_INITIALIZE_PHASE363,
        )
        self.assertEqual(st_rst["effective_ir_remote_ctrl"], "On")
        self.assertEqual(st_rst["effective_ctrl_for_hdmi"], "Off")
        self.assertEqual(st_init["effective_ir_remote_ctrl"], "Off")
        self.assertEqual(st_init["effective_ctrl_for_hdmi"], "On")

    def test_60_g158_ctrl_for_hdmi_on_blocks_external_hdmi_gear_attach(self) -> None:
        res_danger = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            ctrl_for_hdmi="On",
            external_hdmi_gear_attaching=True,
        )
        res_safe = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            ctrl_for_hdmi="Off",
            external_hdmi_gear_attaching=True,
        )
        self.assertFalse(res_danger.valid)
        self.assertFalse(res_danger.hil_bench_safe_for_hdmi_attach)
        self.assertEqual(
            res_danger.status,
            STATUS_BLOCKED_G158_AIRPLANE_RF_OR_CTRL_FOR_HDMI_CEC_HIJACK_VIOLATION,
        )
        self.assertTrue(res_safe.valid)
        self.assertTrue(res_safe.hil_bench_safe_for_hdmi_attach)

    def test_61_g158_initialize_re_enables_ctrl_for_hdmi_on_caught_before_attach(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            ctrl_for_hdmi="Off",
            external_hdmi_gear_attaching=True,
            reset_action=RESET_ACTION_INITIALIZE_PHASE363,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.effective_ctrl_for_hdmi, "On")
        self.assertIn("CTRL_FOR_HDMI_ON_BENCH_CEC_HIJACK_RISK", res.violation_codes)

    def test_62_g158_cec_rec_absent_and_41_cec_keys_guarded(self) -> None:
        self.assertEqual(len(EXACT_41_FX3_CEC_KEY_EVENTS_G158), 41)
        self.assertNotIn("EVENT_INPUT_KEY_CEC_REC", EXACT_41_FX3_CEC_KEY_EVENTS_G158)
        res_rec = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            cec_key_event="EVENT_INPUT_KEY_CEC_REC"
        )
        self.assertFalse(res_rec.valid)
        self.assertEqual(res_rec.block_errno, EOPNOTSUPP_ERRNO_PHASE363)
        res_inj = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            ctrl_for_hdmi="On",
            external_hdmi_gear_attaching=True,
            cec_key_event="EVENT_INPUT_KEY_CEC_STANDBY_ON",
        )
        self.assertFalse(res_inj.valid)
        self.assertIn("CEC_KEY_INJECTION_BLOCKED_ON_BENCH", res_inj.violation_codes)

    def test_63_g158_zero_fx3_25mm_lanc_and_35mm_grip_eopnotsupp(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            requested_fx3_25mm_lanc_or_35mm_grip=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE363)
        self.assertFalse(res.fx3_physical_lanc_25mm_present)
        self.assertFalse(res.fx3_physical_grip_remote_35mm_present)
        self.assertEqual(res.fx3_active_lanc_bkid_hits, 0)

    def test_64_g158_fx6_dormant_ir_cec_and_nfc_rejected_eopnotsupp(self) -> None:
        res_ir = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            requested_fx6_dormant_ir_or_cec_menu=True
        )
        res_nfc = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            requested_fx6_dormant_nfc=True
        )
        self.assertFalse(res_ir.valid)
        self.assertFalse(res_nfc.valid)
        self.assertEqual(res_ir.block_errno, EOPNOTSUPP_ERRNO_PHASE363)
        self.assertEqual(res_nfc.block_errno, EOPNOTSUPP_ERRNO_PHASE363)

    def test_65_g158_fx6_wlan_mutex_with_wired_lan_or_simul_rec_ebusy(self) -> None:
        for kw in ({"fx6_wired_lan_on": True}, {"fx6_simul_rec_on": True}):
            res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
                wifi_operation="fx6_wireless_lan",
                **kw,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EBUSY_ERRNO_PHASE363)
            self.assertEqual(res.status, STATUS_BLOCKED_G158_BT_IR_OR_FX6_WLAN_MUTEX_EBUSY)

    def test_66_g158_fx6t_vs_fx6v_5ghz_sku_gate(self) -> None:
        res_t = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            wifi_operation="fx6_wireless_lan",
            wifi_sku_code=FX6_WIFI_SKU_24GHZ_G158,
            requested_band="5GHz",
        )
        res_v = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            wifi_operation="fx6_wireless_lan",
            wifi_sku_code=FX6_WIFI_SKU_5GHZ_G158,
            requested_band="5GHz",
        )
        self.assertFalse(res_t.valid)
        self.assertEqual(res_t.block_errno, EOPNOTSUPP_ERRNO_PHASE363)
        self.assertTrue(res_v.valid)

    def test_67_g158_claimed_camset_reset_clears_ir_or_cec_rejected(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            claimed_camset_reset_clears_ir_or_cec=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE363)

    def test_68_g158_telemetry_invalid_inputs_rejected(self) -> None:
        for bad_kw in (
            {"body_model_name": "FX9"},
            {"body_model_id": 0},
            {"help_guide_code": "bad"},
            {"firmware_version": ""},
            {"fx3_body_variant": "FX30"},
            {"wifi_operation": "ad_hoc"},
            {"wifi_sku_code": "WW000000"},
            {"requested_band": "6GHz"},
            {"wifi_security": "TKIP"},
            {"access_authen": "Yes"},
            {"wifi_connect": "Maybe"},
            {"airplane_mode": "1"},
            {"target_partition": "p8_cp"},
            {"fx6_wlan_mode": "Mesh"},
            {"ir_remote_ctrl": "Auto"},
            {"bluetooth_rmt_ctrl": "Auto"},
            {"ctrl_for_hdmi": "Auto"},
            {"reset_action": "Reboot"},
        ):
            res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(**bad_kw)
            self.assertFalse(res.valid, f"Expected invalid for {bad_kw}")
            self.assertEqual(res.status, STATUS_BLOCKED_G158_TELEMETRY_INVALID)

    def test_69_g158_384_state_combinatoric_matrix(self) -> None:
        m = compute_wifi5ghz_nvs_ir_lanc_cec_matrix()
        self.assertEqual(m["total_matrix_states"], 384)
        self.assertEqual(m["airplane_survived_reset_network_count"], 64)
        self.assertEqual(m["airplane_cleared_by_initialize_count"], 64)
        self.assertEqual(m["ww558244_5ghz_blocked_count"], 96)
        self.assertEqual(m["outdoor_5ghz_blocked_count"], 96)
        self.assertEqual(m["bt_ir_mutex_blocked_count"], 64)
        self.assertEqual(m["cec_bench_hazard_flagged_count"], 256)

    def test_70_g158_menu_paths_and_fx6_lanc_contracts(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard()
        self.assertEqual(res.wifi_menu_path, WIFI_MENU_PATH_G158)
        self.assertEqual(res.ir_remote_ctrl_menu_path, IR_REMOTE_CTRL_MENU_PATH_G158)
        self.assertEqual(res.ctrl_for_hdmi_menu_path, CTRL_FOR_HDMI_MENU_PATH_G158)
        self.assertEqual(res.fx6_lanc_25mm_port_num, FX6_LANC_25MM_PORT_NUM_G158)
        self.assertEqual(res.fx6_grip_remote_35mm_poles, FX6_GRIP_REMOTE_35MM_POLES_G158)
        self.assertFalse(FX6_EXPOSED_IR_OR_CEC_MENUS_G158)

    def test_71_g158_evaluate_wrapper_and_with_audit_clean_room(self) -> None:
        v1, r1 = evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        v2, r2 = verify_wifi5ghz_nvs_ir_lanc_cec_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v1.passed and r1.valid)
        self.assertTrue(v2.passed and r2.valid)
        self.assertEqual(v1.gate_id, G158)
        self.assertEqual(r1.status, STATUS_VERIFIED_G158)

    def test_72_g158_evaluate_propagates_p12_p13_erofs_fault(self) -> None:
        v, r = evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard(
            repo_root=REPO_ROOT,
            force_clean_room=True,
            target_partition="p13_rfnvs",
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertEqual(v.status, STATUS_BLOCKED_G158_P12_P13_RF_NVS_MS_RDONLY_EROFS)

    def test_73_g158_cec_off_allows_benign_inspection_when_hdmi_attaching(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            ctrl_for_hdmi="Off",
            external_hdmi_gear_attaching=True,
            cec_key_event="EVENT_INPUT_KEY_CEC_ROOT_MENU_ON",
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.hil_bench_safe_for_hdmi_attach)

    def test_74_g158_unknown_cec_event_rejected_even_with_ctrl_off(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            ctrl_for_hdmi="Off",
            cec_key_event="EVENT_INPUT_KEY_CEC_NONEXISTENT",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE363)

    def test_75_g158_reset_network_set_keeps_airplane_off_when_already_off(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            wifi_operation="reset_network_set",
            airplane_mode="Off",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE363,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_airplane_mode, "Off")

    def test_76_g158_negative_bool_and_counter_invariants(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard()
        self.assertFalse(res.emmc_writes_authorized)
        self.assertFalse(res.cross_model_flash_authorized)
        self.assertEqual(res.usb_packets_transmitted, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertEqual(res.rf_nvs_mutation_bytes, 0)
        self.assertEqual(res.rf_tx_packets, 0)
        self.assertEqual(res.emmc_nflasha_write_count, 0)

    # ------------------------------------------------------------------
    # Unified 158-Gate Master Preflight & CLI Tests (77..104)
    # ------------------------------------------------------------------

    def test_77_preflight_158_offline_returns_155_of_158(self) -> None:
        rep = evaluate_158gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertIsInstance(rep, Master158GateReport)
        self.assertEqual(rep.schema_version, REALHW_158GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(rep.status, "VERIFIED_155_OF_158_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.summary["total_gates"], 158)
        self.assertEqual(rep.summary["verified_gates"], 155)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_155_gates_verified)
        self.assertFalse(rep.all_158_gates_verified)
        self.assertTrue(rep.g157_to_g158_all_passed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_78_preflight_158_dry_run_simulated_returns_158_of_158(self) -> None:
        rep = evaluate_158gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(rep.status, "VERIFIED_ALL_158_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(rep.summary["verified_gates"], 158)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_158_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_79_preflight_158_local_donor_mode_when_donors_present(self) -> None:
        rep_cr = evaluate_158gate_preflight(REPO_ROOT, force_clean_room=True)
        rep_norm = evaluate_158gate_preflight(REPO_ROOT)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIn(
            rep_norm.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        self.assertEqual(rep_norm.summary["verified_gates"], 155)

    def test_80_preflight_158_absent_donor_fallback_mocked_work_root_none(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE363: ""},
                clear=False,
            ):
                rep = evaluate_158gate_preflight(REPO_ROOT, dry_run_simulated=True)
        self.assertEqual(rep.summary["verified_gates"], 158)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_81_preflight_158_request_persistent_emmc_writes_fails_closed(self) -> None:
        rep = evaluate_158gate_preflight(
            REPO_ROOT, force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(rep.offline_155_gates_verified)
        self.assertFalse(rep.all_158_gates_verified)
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertEqual(
            rep.g158_result["status"],
            STATUS_BLOCKED_G158_P12_P13_RF_NVS_MS_RDONLY_EROFS,
        )

    def test_82_preflight_158_fault_propagation_g157_failure(self) -> None:
        rep = evaluate_158gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            pbmag_varshutter_ecs_kwargs={"requested_dormant_var_shutter": True},
        )
        self.assertFalse(rep.g157_to_g158_all_passed)
        self.assertFalse(rep.g13_to_g158_all_passed)
        self.assertFalse(rep.offline_155_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G157_MOVIE_ZOOM_OR_DORMANT_VAR_SHUTTER_EOPNOTSUPP,
        )

    def test_83_preflight_158_fault_propagation_g158_cec_hijack(self) -> None:
        rep = evaluate_158gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            wifi5ghz_nvs_ir_lanc_cec_kwargs={
                "ctrl_for_hdmi": "On",
                "external_hdmi_gear_attaching": True,
            },
        )
        self.assertFalse(rep.g157_to_g158_all_passed)
        self.assertFalse(rep.g13_to_g158_all_passed)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G158_AIRPLANE_RF_OR_CTRL_FOR_HDMI_CEC_HIJACK_VIOLATION,
        )

    def test_84_preflight_158_fault_propagation_g158_p12_p13_erofs(self) -> None:
        rep = evaluate_158gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            wifi5ghz_nvs_ir_lanc_cec_kwargs={"target_partition": "p12_cert"},
        )
        self.assertFalse(rep.g157_to_g158_all_passed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G158_P12_P13_RF_NVS_MS_RDONLY_EROFS
        )

    def test_85_preflight_158_fault_propagation_m156_failure(self) -> None:
        rep = evaluate_158gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            areadate_grid_cleanhdmi_kwargs={
                "claimed_marker_outputs_over_hdmi": True
            },
        )
        self.assertFalse(rep.g13_to_g158_all_passed)
        self.assertFalse(rep.offline_155_gates_verified)

    def test_86_preflight_158_all_redline_booleans_false_and_zero(self) -> None:
        rep = evaluate_158gate_preflight(
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

    def test_87_preflight_158_gate_sequence_g01_to_g158_contiguous(self) -> None:
        rep = evaluate_158gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        gate_ids = [g["gate_id"] for g in rep.gates]
        self.assertEqual(len(gate_ids), 158)
        self.assertEqual(gate_ids[-2], G157)
        self.assertEqual(gate_ids[-1], G158)
        self.assertEqual(len(set(gate_ids)), 158)

    def test_88_preflight_158_no_raw_bytes_repr_in_report_dict(self) -> None:
        rep = evaluate_158gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        dumped = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn('b"\\x7fELF', dumped)

    def test_89_preflight_158_report_has_master_156_and_g157_g158_dicts(self) -> None:
        rep = evaluate_158gate_preflight(REPO_ROOT, force_clean_room=True)
        d = rep.to_dict()
        self.assertIn("master_156_report", d)
        self.assertIn("g157_result", d)
        self.assertIn("g158_result", d)
        self.assertEqual(d["g157_result"]["gate_id"], G157)
        self.assertEqual(d["g158_result"]["gate_id"], G158)

    def test_90_backward_compatibility_156_154_152_150_148_gates(self) -> None:
        r156 = fx3_safety.evaluate_156gate_preflight(REPO_ROOT, force_clean_room=True)
        r154 = fx3_safety.evaluate_154gate_preflight(REPO_ROOT, force_clean_room=True)
        r152 = fx3_safety.evaluate_152gate_preflight(REPO_ROOT, force_clean_room=True)
        r150 = fx3_safety.evaluate_150gate_preflight(REPO_ROOT, force_clean_room=True)
        r148 = fx3_safety.evaluate_148gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertEqual(r156.summary["verified_gates"], 153)
        self.assertEqual(r154.summary["verified_gates"], 151)
        self.assertEqual(r152.summary["verified_gates"], 149)
        self.assertEqual(r150.summary["verified_gates"], 147)
        self.assertEqual(r148.summary["verified_gates"], 145)

    def test_91_simulate_bench_dry_run_alias_kwargs_and_wrapper_fns(self) -> None:
        r1 = evaluate_158_master_safety_gates(
            REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = run_158_gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        r3 = verify_real_hardware_158gate_readiness(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r1.summary["verified_gates"], 158)
        self.assertEqual(r2.summary["verified_gates"], 158)
        self.assertEqual(r3.summary["verified_gates"], 158)

    def test_92_forward_compatible_dynamic_discovery_export(self) -> None:
        nums = sorted(
            int(name[9:-14])
            for name in dir(fx3_safety)
            if name.startswith("evaluate_")
            and name.endswith("gate_preflight")
            and name[9:-14].isdigit()
        )
        self.assertIn(158, nums)
        self.assertGreaterEqual(max(nums), 158)

    def test_93_fx3_safety_package_exports_and_all(self) -> None:
        for sym in (
            "evaluate_158gate_preflight",
            "evaluate_158_master_safety_gates",
            "run_158_gate_preflight",
            "verify_real_hardware_158gate_readiness",
            "evaluate_g157_pbmag_varshutter_ecs_guard",
            "evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard",
            "Master158GateReport",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing export {sym}")
            self.assertIn(sym, fx3_safety.__all__)

    def test_94_master_156_override_injection_works(self) -> None:
        m156 = fx3_safety.evaluate_156gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        rep = evaluate_158gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_156_override=m156,
        )
        self.assertEqual(rep.summary["verified_gates"], 158)

    def test_95_cli_verify_158_gates_text_offline_and_dry_run(self) -> None:
        buf1 = StringIO()
        with redirect_stdout(buf1):
            rc1 = safety_cli.main(["verify-158-gates", "--clean-room"])
        buf2 = StringIO()
        with redirect_stdout(buf2):
            rc2 = safety_cli.main(
                ["verify-158-gates", "--clean-room", "--simulate-bench-dry-run"]
            )
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)
        self.assertIn("verified=155/158", buf1.getvalue())
        self.assertIn("verified=158/158", buf2.getvalue())

    def test_96_cli_verify_158_gates_json_and_summary(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = safety_cli.main(
                [
                    "verify-158-gates",
                    "--clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                    "--summary",
                ]
            )
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["summary"]["verified_gates"], 158)
        self.assertEqual(parsed["g157_status"], STATUS_VERIFIED_G157)
        self.assertEqual(parsed["g158_status"], STATUS_VERIFIED_G158)

    def test_97_cli_g157_and_g158_aliases_json_summary(self) -> None:
        for cmd_list in (
            ["verify-pbmag-varshutter-ecs-guard", "--clean-room", "--json", "--summary"],
            ["verify-g157-pbmag-varshutter-ecs", "--clean-room", "--json", "--summary"],
            ["verify-g157", "--clean-room"],
            ["verify-wifi5ghz-nvs-ir-lanc-cec-guard", "--clean-room", "--json", "--summary"],
            ["verify-g158-wifi5ghz-nvs-ir-lanc-cec", "--clean-room", "--json", "--summary"],
            ["verify-g158", "--clean-room"],
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = safety_cli.main(cmd_list)
            self.assertEqual(rc, 0, f"Command failed: {cmd_list}")

    def test_98_module_main_entrypoint_g157_g158_and_158(self) -> None:
        for argv in (
            ["--clean-room", "--gate", "g157", "--json", "--summary"],
            ["--clean-room", "--gate", "g158", "--json", "--summary"],
            ["--clean-room", "--gate", "158", "--simulate-bench-dry-run", "--json", "--summary"],
            ["--clean-room", "--gate", "158"],
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = guard_module_main(argv)
            self.assertEqual(rc, 0, f"Module CLI failed for {argv}")

    def test_99_cli_main_help_formatting_no_percent_typeerror(self) -> None:
        buf = StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(buf):
                safety_cli.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        help_out = buf.getvalue()
        self.assertIn("verify-158-gates", help_out)
        self.assertIn("verify-g157", help_out)
        self.assertIn("verify-g158", help_out)

    def test_100_g157_g158_negative_bool_invariants_remain_false(self) -> None:
        _, r157 = evaluate_g157_pbmag_varshutter_ecs_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        _, r158 = evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        g157_d = r157.pbmag_varshutter_ecs_guard
        g158_d = r158.wifi5ghz_nvs_ir_lanc_cec_guard
        self.assertFalse(g157_d["movie_playback_zoom_supported"])
        self.assertFalse(g157_d["playback_magnify_resettable_by_camset_reset"])
        self.assertFalse(g157_d["fx3_var_shutter_exposed"])
        self.assertFalse(g157_d["fx3_anti_flicker_set_exposed"])
        self.assertFalse(g157_d["fx3_anti_flicker_tv_scan_exposed"])
        self.assertFalse(g158_d["fx3_physical_lanc_25mm_present"])
        self.assertFalse(g158_d["fx3_physical_grip_remote_35mm_present"])
        self.assertFalse(g158_d["fx6_exposed_ir_or_cec_menus"])
        self.assertFalse(g158_d["ir_remote_resettable_by_camset_reset"])
        self.assertFalse(g158_d["ctrl_for_hdmi_resettable_by_camset_reset"])

    def test_101_g157_g158_no_raw_bytes_repr_in_guard_dicts(self) -> None:
        _, g157_res = evaluate_g157_pbmag_varshutter_ecs_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        _, g158_res = evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        for obj in (g157_res.to_dict(), g158_res.to_dict()):
            dumped = json.dumps(obj, ensure_ascii=False)
            self.assertNotIn("b'\\x7fELF", dumped)
            self.assertNotIn('b"\\x7fELF', dumped)

    def test_102_g157_h0_h1_trial_entry_allowed_and_auto_flash_blocked(self) -> None:
        rep_off = evaluate_158gate_preflight(REPO_ROOT, force_clean_room=True)
        rep_fail = evaluate_158gate_preflight(
            REPO_ROOT, force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertTrue(rep_off.h0_h1_trial_entry_allowed)
        self.assertTrue(rep_off.agent_auto_flash_blocked)
        self.assertFalse(rep_fail.h0_h1_trial_entry_allowed)

    def test_103_g158_all_4_modes_report_digest_consistency_after_strip(self) -> None:
        r_cr = evaluate_158gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE363: "1"}, clear=False):
            r_env = evaluate_158gate_preflight(REPO_ROOT, dry_run_simulated=True)
        s_cr = strip_elapsed_seconds_recursive_phase363(r_cr.g157_result["pbmag_varshutter_ecs_guard"])
        s_env = strip_elapsed_seconds_recursive_phase363(r_env.g157_result["pbmag_varshutter_ecs_guard"])
        self.assertEqual(s_cr, s_env)

    def test_104_g158_ctrl_for_hdmi_off_safe_on_bench_even_with_41_cec_vectors(self) -> None:
        res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
            ctrl_for_hdmi="Off",
            external_hdmi_gear_attaching=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.cec_key_events_count, 41)
        self.assertEqual(res.cec_rec_event_count, 0)
        self.assertTrue(res.hil_bench_safe_for_hdmi_attach)


if __name__ == "__main__":
    unittest.main()
