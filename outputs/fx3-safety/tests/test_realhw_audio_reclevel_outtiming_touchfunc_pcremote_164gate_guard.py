"""Comprehensive 4-mode test suite for Phase 382 (`164/164` Hardware Safety Gates, Wave-72):
Gate G163 (`[Audio Rec Level]` `0..31` def `26` `adj_audio_rec_level_defult`, `XLR-H1`
physical preemption & permanent Limiter vs FX6 6-mode `Limiter Mode` / 5-mode `Reference
Level`, `[Audio Out Timing]` `Live`/`Lip Sync`, anti-Reset `[Volume Settings]` & exact
5-item `[4ch Audio Monitoring]` `CH1/CH2`, `CH3/CH4`, `CH1+3/CH2+4`, `CH1/CH1`, `CH2/CH2`
vs FX6 7-item `Monitor CH` & zero `"MONITOR VOL +/-"` side keys),
Gate G164 (`[Touch Func. in Shooting]` 4 active anti-Reset sub-items vs 100% dormant
`[Touch Panel/Pad]`/`[Touch Pad (vertical)]`/`[Touch Shutter]`/`[Touch AE]` & FX6
`Touch Function in MF` / Ver. 6.00+ `BIG6` touch, `[Spot Metering Point]` anchor, and
`[Remote Shoot Setting]` `Destination Only` zero-card RAM vs default `Dest.+Camera` &
`Camera Only`, PTP `/dev/usb/sicd_*` & PTP-IP `15740`, Tier-0 `Slot 1` `EROFS=30` Firewall),
and Unified `164`-Gate Master Safety Preflight (`G01..G164`).
"""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
import hashlib
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
from fx3_safety.realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard import (  # noqa: E402
    ALLOWED_AUDIO_OUT_TIMING_MODES_G163,
    ALLOWED_FX3_HDMI_4CH_OUTPUT_MODES_G163,
    ALLOWED_PTP_TRANSPORTS_G164,
    ALLOWED_RAW_H_SAVE_IMAGE_G164,
    ALLOWED_RAW_J_SAVE_IMAGE_G164,
    ALLOWED_SAVE_IMAGE_SIZE_G164,
    ALLOWED_SPOT_METERING_POINTS_G164,
    ALLOWED_STILL_IMG_SAVE_DEST_G164,
    ALLOWED_SWIPE_UP_MODES_G164,
    ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES_G164,
    ALLOWED_TOUCH_OPERATION_MODES_G164,
    ALLOWED_TOUCH_SENSITIVITY_MODES_G164,
    ALLOWED_XLR_H1_ATT_DB_G163,
    ALLOWED_XLR_H1_GAIN_MODES_G163,
    AUDIO_MONITORING_4CH_DEFAULT_G163,
    AUDIO_MONITORING_4CH_F_RESID16_G163,
    AUDIO_MONITORING_4CH_MENU_PATH_G163,
    AUDIO_MONITORING_4CH_RESETTABLE_BY_CAMSET_RESET_G163,
    AUDIO_MON_CH13_CH24_F_RESID16_G163,
    AUDIO_MON_CH1_CH1_F_RESID16_G163,
    AUDIO_MON_CH1_CH2_F_RESID16_G163,
    AUDIO_MON_CH2_CH2_F_RESID16_G163,
    AUDIO_MON_CH3_CH4_F_RESID16_G163,
    AUDIO_OUT_TIMING_DEFAULT_G163,
    AUDIO_OUT_TIMING_F_RESID16_G163,
    AUDIO_OUT_TIMING_MENU_PATH_G163,
    AUDIO_OUT_TIMING_RESETTABLE_BY_CAMSET_RESET_G163,
    AUDIO_REC_LEVEL_DEFAULT_G163,
    AUDIO_REC_LEVEL_DELETE_KEY_RESETS_TO_G163,
    AUDIO_REC_LEVEL_ELF_TYPO_G163,
    AUDIO_REC_LEVEL_F_RESID16_G163,
    AUDIO_REC_LEVEL_MAX_G163,
    AUDIO_REC_LEVEL_MENU_PATH_G163,
    AUDIO_REC_LEVEL_MIN_G163,
    AUDIO_REC_LEVEL_RESETTABLE_BY_CAMSET_RESET_G163,
    AUDIO_REC_LEVEL_STEP_COUNT_G163,
    DONOR_CHECK_MAX_SECONDS_PHASE382,
    DORMANT_FX3_TOUCH_FEATURES_G164,
    DORMANT_TOUCH_AE_F_RESID16_G164,
    DORMANT_TOUCH_PAD_VERTICAL_F_RESID16_G164,
    DORMANT_TOUCH_PANEL_PAD_F_RESID16_G164,
    DORMANT_TOUCH_SHUTTER_F_RESID16_G164,
    EBUSY_ERRNO_PHASE382,
    EINVAL_ERRNO_PHASE382,
    ENV_CLEAN_ROOM_TEST_PHASE382,
    EOPNOTSUPP_ERRNO_PHASE382,
    EROFS_ERRNO_PHASE382,
    EXACT_4_FX3_TOUCH_OPERATION_SUBITEMS_G164,
    EXACT_4_REMOTE_SHOOT_SUBITEMS_G164,
    EXACT_5_FX3_4CH_AUDIO_MONITORING_MODES_G163,
    FABRICATED_4CH_MONITORING_LABELS_G163,
    FX3_BODY_LIMITER_PERMANENTLY_ACTIVE_G163,
    FX3_EVF_PRESENT_G164,
    FX3_HEADPHONE_MAX_DISCRETE_CH_G163,
    FX3_ILC2210_TOUCH_AE_HITS_G164,
    FX3_ILC2210_TOUCH_SHUTTER_HITS_G164,
    FX3_PTP_IP_TCP_PORT_G164,
    FX3_PTP_USB_DEVICE_NODES_G164,
    FX3_SPOT_METERING_FOLLOWS_MOVING_TRACK_BOX_G164,
    FX3_TOUCH_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164,
    FX6_HDMI_AUDIO_CHANNELS_G163,
    FX6_HEADPHONE_OUT_MODES_G163,
    FX6_INPUT_MIC_REFERENCE_6_STEPS_G163,
    FX6_LIMITER_MODE_6_STEPS_G163,
    FX6_LINE_INPUT_REFERENCE_4_STEPS_G163,
    FX6_MONITOR_CH_7_ITEMS_G163,
    FX6_MONITOR_VOL_PHYSICAL_KEY_HITS_G163,
    FX6_REFERENCE_LEVEL_5_STEPS_G163,
    FX6_SDI_AUDIO_CHANNELS_G163,
    FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED_G164,
    G163,
    G164,
    MEDIA_SLOT_1_PHASE382,
    MEDIA_SLOT_2_PHASE382,
    MEDIA_SLOT_NONE_PHASE382,
    Master164GateReport,
    PINNED_FX3_APPFW_SLICES_PHASE382,
    PINNED_FX6_APPFW_SLICES_PHASE382,
    PINNED_PHASE382_DONOR_SPECS,
    RAW_H_SAVE_IMAGE_DEFAULT_G164,
    RAW_J_SAVE_IMAGE_DEFAULT_G164,
    REALHW_164GATE_PREFLIGHT_SCHEMA,
    REMOTE_SHOOT_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164,
    REMOTE_SHOOT_SETTING_F_RESID16_G164,
    REMOTE_SHOOT_SETTING_MENU_PATH_G164,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
    RESET_ACTION_INITIALIZE_PHASE382,
    RESET_ACTION_NONE_PHASE382,
    RESET_ACTION_RESET_NETWORK_SET_PHASE382,
    SAVE_IMAGE_SIZE_DEFAULT_G164,
    SHOOT_MODE_MOVIE_PHASE382,
    SHOOT_MODE_SQ_PHASE382,
    SHOOT_MODE_STILL_PHASE382,
    SQ_LOCKED_AUDIO_CONTROLS_G163,
    STATUS_BLOCKED_G163_FABRICATED_4CH_BODY_LIMITER_OFF_OR_FX6_MONVOL_EOPNOTSUPP,
    STATUS_BLOCKED_G163_PREEMPTION_SQ_LOCK_RESET_OR_FX6_AUDIO_CONSTRAINT_VIOLATION,
    STATUS_BLOCKED_G163_TELEMETRY_INVALID,
    STATUS_BLOCKED_G164_CONNECTED_SAVE_DEST_MUTATION_EBUSY,
    STATUS_BLOCKED_G164_DORMANT_TOUCH_OR_FX6_SAVE_DEST_EOPNOTSUPP,
    STATUS_BLOCKED_G164_SLOT1_REMOTE_SHOOT_WRITE_EROFS,
    STATUS_BLOCKED_G164_TELEMETRY_INVALID,
    STATUS_BLOCKED_G164_TOUCH_SPOT_RESET_OR_PTP_CONSTRAINT_VIOLATION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE382_DONOR_INTEGRITY,
    STATUS_VERIFIED_G163,
    STATUS_VERIFIED_G164,
    STILL_IMG_SAVE_DEST_BENCH_SAFE_G164,
    STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164,
    SWIPE_UP_DEFAULT_G164,
    TOUCH_FUNC_IN_SHOOTING_DEFAULT_G164,
    TOUCH_OPERATION_DEFAULT_G164,
    TOUCH_OPERATION_MENU_PATH_G164,
    TOUCH_SENSITIVITY_DEFAULT_G164,
    VOLUME_SETTINGS_BASE_RESID16_G163,
    VOLUME_SETTINGS_DEFAULT_G163,
    VOLUME_SETTINGS_MAX_G163,
    VOLUME_SETTINGS_MENU_PATH_G163,
    VOLUME_SETTINGS_MIN_G163,
    VOLUME_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G163,
    XLR_H1_ATT_TO_DBU_G163,
    XLR_H1_LINE_FIXED_DBU_G163,
    audit_phase382_donor_contracts,
    compute_audio_reclevel_outtiming_matrix,
    compute_touchfunc_pcremote_matrix,
    evaluate_164_master_safety_gates,
    evaluate_164gate_preflight,
    evaluate_g163_audio_reclevel_outtiming_guard,
    evaluate_g164_touchfunc_pcremote_guard,
    main as guard_module_main,
    resolve_fx3_audio_reclevel_outtiming_state,
    resolve_fx3_touchfunc_pcremote_state,
    run_164_gate_preflight,
    strip_elapsed_seconds_recursive_phase382,
    verify_audio_reclevel_outtiming_guard,
    verify_audio_reclevel_outtiming_guard_with_audit,
    verify_real_hardware_164gate_readiness,
    verify_touchfunc_pcremote_guard,
    verify_touchfunc_pcremote_guard_with_audit,
)


def _mock_paths_work_root_none(**_kwargs):
    return mock.MagicMock(work_root=None)


class TestPhase382HardwareSafety164Gates(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Integrity & 4-Mode Checks (01..12)
    # ------------------------------------------------------------------

    def test_01_donor_specs_pin_23_artifacts_and_bounded_budget(self) -> None:
        self.assertGreaterEqual(len(PINNED_PHASE382_DONOR_SPECS), 23)
        self.assertGreaterEqual(len(PINNED_FX3_APPFW_SLICES_PHASE382), 36)
        self.assertGreaterEqual(len(PINNED_FX6_APPFW_SLICES_PHASE382), 24)
        audit = audit_phase382_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_2s)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE382)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_02_donor_audit_normal_mode_matches_expected(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE382: ""},
            clear=False,
        ):
            audit = audit_phase382_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertTrue(audit.ptp_transport_libs_verified)
        self.assertTrue(audit.zero_fx6_monitor_vol_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertIn(
            audit.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        if audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(audit.files_inspected, len(PINNED_PHASE382_DONOR_SPECS))
            self.assertEqual(
                audit.access_mode, "STRICT_OS_O_RDONLY_NOFOLLOW_NONBLOCK_PREAD"
            )

    def test_03_donor_audit_fx3_clean_room_test_env_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ENV_CLEAN_ROOM_TEST_PHASE382: "1", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            clear=False,
        ):
            audit = audit_phase382_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_DISK_IO")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_04_donor_audit_force_clean_room_env_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1", ENV_CLEAN_ROOM_TEST_PHASE382: ""},
            clear=False,
        ):
            audit = audit_phase382_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.files_inspected, 0)

    def test_05_donor_audit_mocked_work_root_none_fallback(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE382: ""},
                clear=False,
            ):
                audit = audit_phase382_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_donor_audit_absent_temp_work_root_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = audit_phase382_donor_contracts(
                repo_root=REPO_ROOT,
                work_root=Path(tmpdir),
                force_clean_room=False,
            )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")

    def test_07_donor_audit_override_detects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_spec = {
                "tiny": ("FX3", "missing.bin", 4, "0" * 64, (b"ABCD",), "missing file")
            }
            audit = audit_phase382_donor_contracts(
                work_root=Path(tmpdir),
                force_clean_room=False,
                donor_specs_override=bad_spec,
            )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE382_DONOR_INTEGRITY)

    def test_08_donor_audit_override_detects_size_sha_and_token_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "sample.bin"
            p.write_bytes(b"ABCD1234")
            bad_spec = {
                "sample": (
                    "FX3",
                    "sample.bin",
                    99,
                    "f" * 64,
                    (b"ABCD", b"MISSING_TOK"),
                    "tampered",
                )
            }
            audit = audit_phase382_donor_contracts(
                work_root=Path(tmpdir),
                force_clean_room=False,
                donor_specs_override=bad_spec,
            )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE382_DONOR_INTEGRITY)
        self.assertTrue(any("size_mismatch" in e for e in audit.errors))
        self.assertTrue(any("sha256_mismatch" in e for e in audit.errors))
        self.assertTrue(any("token_missing" in e for e in audit.errors))

    def test_09_donor_audit_override_valid_synthetic_file_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = b"\x7fELF_WAVE72_AUDIO_PTP_OK"
            p = Path(tmpdir) / "ok.bin"
            p.write_bytes(payload)
            sha = hashlib.sha256(payload).hexdigest()
            spec = {
                "ok": (
                    "FX3",
                    "ok.bin",
                    len(payload),
                    sha,
                    (b"\x7fELF", b"WAVE72"),
                    "ok synthetic",
                )
            }
            audit = audit_phase382_donor_contracts(
                work_root=Path(tmpdir),
                force_clean_room=False,
                donor_specs_override=spec,
            )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.files_inspected, 1)
        self.assertEqual(audit.file_digests["ok"], sha)

    def test_10_donor_audit_clean_room_digest_deterministic_recursive_strip(self) -> None:
        a1 = strip_elapsed_seconds_recursive_phase382(
            {
                "audit": audit_phase382_donor_contracts(force_clean_room=True).to_dict(),
                "nested": [{"elapsed_ms": 1.23, "elapsed_seconds": 0.001, "k": "v"}],
            }
        )
        a2 = strip_elapsed_seconds_recursive_phase382(
            {
                "audit": audit_phase382_donor_contracts(force_clean_room=True).to_dict(),
                "nested": [{"elapsed_ms": 9.87, "elapsed_seconds": 0.009, "k": "v"}],
            }
        )
        self.assertEqual(a1, a2)
        self.assertNotIn("elapsed_seconds", a1["audit"])
        self.assertNotIn("elapsed_ms", a1["nested"][0])

    def test_11_source_module_strictly_o_rdonly_nofollow_nonblock_and_no_writes(self) -> None:
        src_path = (
            SAFETY_ROOT
            / "fx3_safety"
            / "realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard.py"
        )
        text = src_path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        self.assertIsNotNone(tree)
        self.assertIn("os.O_RDONLY", text)
        self.assertIn("O_NOFOLLOW", text)
        self.assertIn("O_NONBLOCK", text)
        self.assertNotIn("os.O_RDWR", text)
        self.assertNotIn("os.O_CREAT", text)
        self.assertNotIn("write_bytes(", text)

    def test_12_pinned_constants_match_empirical_wave72_baseline(self) -> None:
        self.assertEqual(AUDIO_REC_LEVEL_MIN_G163, 0)
        self.assertEqual(AUDIO_REC_LEVEL_MAX_G163, 31)
        self.assertEqual(AUDIO_REC_LEVEL_STEP_COUNT_G163, 32)
        self.assertEqual(AUDIO_REC_LEVEL_DEFAULT_G163, 26)
        self.assertEqual(AUDIO_REC_LEVEL_ELF_TYPO_G163, "adj_audio_rec_level_defult")
        self.assertTrue(AUDIO_REC_LEVEL_RESETTABLE_BY_CAMSET_RESET_G163)
        self.assertTrue(FX3_BODY_LIMITER_PERMANENTLY_ACTIVE_G163)
        self.assertTrue(AUDIO_OUT_TIMING_RESETTABLE_BY_CAMSET_RESET_G163)
        self.assertFalse(VOLUME_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G163)
        self.assertFalse(AUDIO_MONITORING_4CH_RESETTABLE_BY_CAMSET_RESET_G163)
        self.assertEqual(len(EXACT_5_FX3_4CH_AUDIO_MONITORING_MODES_G163), 5)
        self.assertEqual(len(FX6_INPUT_MIC_REFERENCE_6_STEPS_G163), 6)
        self.assertEqual(len(FX6_LINE_INPUT_REFERENCE_4_STEPS_G163), 4)
        self.assertEqual(len(FX6_REFERENCE_LEVEL_5_STEPS_G163), 5)
        self.assertEqual(len(FX6_LIMITER_MODE_6_STEPS_G163), 6)
        self.assertEqual(len(FX6_MONITOR_CH_7_ITEMS_G163), 7)
        self.assertEqual(FX6_MONITOR_VOL_PHYSICAL_KEY_HITS_G163, 0)
        self.assertEqual(len(EXACT_4_FX3_TOUCH_OPERATION_SUBITEMS_G164), 4)
        self.assertFalse(FX3_TOUCH_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164)
        self.assertEqual(len(DORMANT_FX3_TOUCH_FEATURES_G164), 4)
        self.assertFalse(FX3_EVF_PRESENT_G164)
        self.assertEqual(FX3_ILC2210_TOUCH_SHUTTER_HITS_G164, 0)
        self.assertEqual(FX3_ILC2210_TOUCH_AE_HITS_G164, 0)
        self.assertEqual(len(EXACT_4_REMOTE_SHOOT_SUBITEMS_G164), 4)
        self.assertFalse(REMOTE_SHOOT_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164)
        self.assertEqual(STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164, "Dest.+Camera")
        self.assertEqual(FX3_PTP_IP_TCP_PORT_G164, 15740)
        self.assertFalse(FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED_G164)

    # ------------------------------------------------------------------
    # Gate G163: [Audio Rec Level], XLR-H1 Preemption, Limiter (13..32)
    # ------------------------------------------------------------------

    def test_13_g163_default_safe_baseline_passes(self) -> None:
        res = verify_audio_reclevel_outtiming_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G163)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.active_audio_source, "internal_stereo_mic")
        self.assertEqual(res.active_audio_channels, 2)
        self.assertEqual(res.effective_audio_rec_level, 26)
        self.assertTrue(res.body_limiter_permanently_active)
        self.assertEqual(res.effective_audio_out_timing, "Live")
        self.assertEqual(res.effective_volume_settings, 7)
        self.assertEqual(res.effective_4ch_audio_monitoring, "CH1/CH2")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_14_g163_all_32_audio_rec_level_steps_0_to_31_valid(self) -> None:
        for lvl in range(AUDIO_REC_LEVEL_MIN_G163, AUDIO_REC_LEVEL_MAX_G163 + 1):
            res = verify_audio_reclevel_outtiming_guard(audio_rec_level=lvl)
            self.assertTrue(res.valid, f"level {lvl} failed: {res.errors}")
            self.assertEqual(res.effective_audio_rec_level, lvl)

    def test_15_g163_audio_rec_level_out_of_range_blocked(self) -> None:
        for bad_lvl in (-1, 32, 99):
            res = verify_audio_reclevel_outtiming_guard(audio_rec_level=bad_lvl)
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE382)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G163_PREEMPTION_SQ_LOCK_RESET_OR_FX6_AUDIO_CONSTRAINT_VIOLATION,
            )

    def test_16_g163_delete_key_resets_audio_rec_level_to_26(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            audio_rec_level=12, delete_key_pressed=True
        )
        self.assertTrue(res.valid)
        self.assertEqual(
            res.effective_audio_rec_level, AUDIO_REC_LEVEL_DELETE_KEY_RESETS_TO_G163
        )

    def test_17_g163_blocks_disabling_permanent_body_limiter_eopnotsupp(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(request_disable_body_limiter=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE382)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G163_FABRICATED_4CH_BODY_LIMITER_OFF_OR_FX6_MONVOL_EOPNOTSUPP,
        )

    def test_18_g163_35mm_mic_preempts_mishoe_grays_shoe_audio_and_bypasses_wind(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            mic_35mm_inserted=True,
            xlr_h1_attached=True,
            xlr_h1_handle_audio_on=True,
            attempt_body_rec_level_write=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.active_audio_source, "body_35mm_mic")
        self.assertEqual(res.active_audio_channels, 2)
        self.assertTrue(res.audio_rec_level_available)
        self.assertTrue(res.shoe_audio_set_grayed)
        self.assertTrue(res.wind_noise_reduct_bypassed)
        self.assertFalse(res.xlr_h1_controls_active)

    def test_19_g163_blocks_claim_35mm_keeps_shoe_audio_active(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            mic_35mm_inserted=True, claim_35mm_keeps_shoe_audio_active=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE382)

    def test_20_g163_xlrh1_handle_audio_on_preempts_body_audio_rec_level(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            mic_35mm_inserted=False,
            xlr_h1_attached=True,
            xlr_h1_handle_audio_on=True,
            xlr_h1_4ch_mode=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.active_audio_source, "xlr_h1_mishoe")
        self.assertEqual(res.active_audio_channels, 4)
        self.assertTrue(res.xlr_h1_controls_active)
        self.assertFalse(res.audio_rec_level_available)

        r_blk = verify_audio_reclevel_outtiming_guard(
            mic_35mm_inserted=False,
            xlr_h1_attached=True,
            xlr_h1_handle_audio_on=True,
            attempt_body_rec_level_write=True,
        )
        self.assertFalse(r_blk.valid)
        self.assertEqual(r_blk.block_errno, EINVAL_ERRNO_PHASE382)

    def test_21_g163_xlrh1_line_locked_plus_4dbu_and_blocks_att_override(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            xlr_h1_attached=True,
            xlr_h1_handle_audio_on=True,
            xlr_h1_input_type="LINE",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.xlr_h1_effective_ref_dbu, XLR_H1_LINE_FIXED_DBU_G163)
        self.assertFalse(res.xlr_h1_att_active)

        r_blk = verify_audio_reclevel_outtiming_guard(
            xlr_h1_attached=True,
            xlr_h1_handle_audio_on=True,
            xlr_h1_input_type="LINE",
            attempt_xlr_att_override_on_line=True,
        )
        self.assertFalse(r_blk.valid)
        self.assertEqual(r_blk.block_errno, EINVAL_ERRNO_PHASE382)

    def test_22_g163_xlrh1_mic_and_mic48v_att_0_10_20db_maps_to_neg60_50_40dbu(self) -> None:
        for inp in ("MIC", "MIC+48V"):
            for att_db in ALLOWED_XLR_H1_ATT_DB_G163:
                for gmode in ALLOWED_XLR_H1_GAIN_MODES_G163:
                    res = verify_audio_reclevel_outtiming_guard(
                        xlr_h1_attached=True,
                        xlr_h1_handle_audio_on=True,
                        xlr_h1_input_type=inp,
                        xlr_h1_att_db=att_db,
                        xlr_h1_gain_mode=gmode,
                    )
                    self.assertTrue(res.valid, f"{inp}/{att_db}/{gmode}: {res.errors}")
                    self.assertEqual(
                        res.xlr_h1_effective_ref_dbu, XLR_H1_ATT_TO_DBU_G163[att_db]
                    )
                    self.assertTrue(res.xlr_h1_att_active)

    def test_23_g163_xlrh1_handle_audio_off_falls_back_to_internal_mic(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            xlr_h1_attached=True,
            xlr_h1_handle_audio_on=False,
            attempt_body_rec_level_write=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.active_audio_source, "internal_stereo_mic")
        self.assertTrue(res.audio_rec_level_available)

    def test_24_g163_sq_motion_forces_0ch_and_locks_all_4_recording_controls(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(shoot_mode=SHOOT_MODE_SQ_PHASE382)
        self.assertTrue(res.valid)
        self.assertEqual(res.active_audio_source, "sq_silent_0ch")
        self.assertEqual(res.active_audio_channels, 0)
        self.assertFalse(res.audio_rec_level_available)
        self.assertFalse(res.audio_out_timing_available)
        self.assertEqual(len(res.sq_locked_audio_controls), 4)
        self.assertEqual(res.sq_locked_audio_controls, SQ_LOCKED_AUDIO_CONTROLS_G163)

        r1 = verify_audio_reclevel_outtiming_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE382, attempt_body_rec_level_write=True
        )
        r2 = verify_audio_reclevel_outtiming_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE382, attempt_audio_out_timing_write=True
        )
        r3 = verify_audio_reclevel_outtiming_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE382, claim_sq_records_audio=True
        )
        for r in (r1, r2, r3):
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE382)

    # ------------------------------------------------------------------
    # Gate G163: [Audio Out Timing], [Volume], 5-Item [4ch Mon] & FX6 (25..48)
    # ------------------------------------------------------------------

    def test_25_g163_audio_out_timing_live_and_lip_sync_valid(self) -> None:
        for mode in ALLOWED_AUDIO_OUT_TIMING_MODES_G163:
            res = verify_audio_reclevel_outtiming_guard(audio_out_timing=mode)
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_audio_out_timing, mode)
            if mode == "Lip Sync":
                self.assertTrue(any("Lip Sync" in w for w in res.warnings))

    def test_26_g163_all_16_volume_settings_0_to_15_valid_and_out_of_range_blocked(self) -> None:
        for v in range(VOLUME_SETTINGS_MIN_G163, VOLUME_SETTINGS_MAX_G163 + 1):
            res = verify_audio_reclevel_outtiming_guard(volume_settings=v)
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_volume_settings, v)
        for bad_v in (-1, 16, 50):
            res = verify_audio_reclevel_outtiming_guard(volume_settings=bad_v)
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE382)

    def test_27_g163_xlrh1_high_speaker_volume_emits_feedback_warning(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            xlr_h1_attached=True,
            xlr_h1_handle_audio_on=True,
            volume_settings=12,
        )
        self.assertTrue(res.valid)
        self.assertTrue(any("feedback" in w for w in res.warnings))

    def test_28_g163_exact_5_item_4ch_audio_monitoring_enum_all_valid(self) -> None:
        self.assertEqual(
            EXACT_5_FX3_4CH_AUDIO_MONITORING_MODES_G163,
            ("CH1/CH2", "CH3/CH4", "CH1+3/CH2+4", "CH1/CH1", "CH2/CH2"),
        )
        for mon in EXACT_5_FX3_4CH_AUDIO_MONITORING_MODES_G163:
            res = verify_audio_reclevel_outtiming_guard(audio_monitoring_4ch=mon)
            self.assertTrue(res.valid, mon)
            self.assertEqual(res.effective_4ch_audio_monitoring, mon)
            self.assertEqual(res.audio_monitoring_4ch_enum_count, 5)

    def test_29_g163_fabricated_4ch_monitoring_labels_rejected_eopnotsupp95(self) -> None:
        for bad_mon in FABRICATED_4CH_MONITORING_LABELS_G163:
            res = verify_audio_reclevel_outtiming_guard(audio_monitoring_4ch=bad_mon)
            self.assertFalse(res.valid, bad_mon)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE382)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G163_FABRICATED_4CH_BODY_LIMITER_OFF_OR_FX6_MONVOL_EOPNOTSUPP,
            )

    def test_30_g163_35mm_headphone_limited_to_2ch_and_independent_from_hdmi_4ch(self) -> None:
        for h_out in ALLOWED_FX3_HDMI_4CH_OUTPUT_MODES_G163:
            res = verify_audio_reclevel_outtiming_guard(
                audio_monitoring_4ch="CH1+3/CH2+4",
                hdmi_4ch_audio_output=h_out,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_hdmi_4ch_audio_output, h_out)
            self.assertEqual(
                res.headphone_max_discrete_channels, FX3_HEADPHONE_MAX_DISCRETE_CH_G163
            )

        r_hp = verify_audio_reclevel_outtiming_guard(
            request_4ch_discrete_35mm_headphone=True
        )
        self.assertFalse(r_hp.valid)
        self.assertEqual(r_hp.block_errno, EOPNOTSUPP_ERRNO_PHASE382)

        r_cpl = verify_audio_reclevel_outtiming_guard(
            claim_4ch_mon_couples_hdmi_4ch_output=True
        )
        self.assertFalse(r_cpl.valid)
        self.assertEqual(r_cpl.block_errno, EINVAL_ERRNO_PHASE382)

    def test_31_g163_reset_split_shooting_resets_vs_setup_sound_option_resists(self) -> None:
        st_rst = resolve_fx3_audio_reclevel_outtiming_state(
            audio_rec_level=14,
            audio_out_timing="Lip Sync",
            volume_settings=13,
            audio_monitoring_4ch="CH2/CH2",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
        )
        self.assertEqual(st_rst["effective_audio_rec_level"], 26)
        self.assertEqual(st_rst["effective_audio_out_timing"], "Live")
        self.assertEqual(st_rst["effective_volume_settings"], 13)
        self.assertEqual(st_rst["effective_4ch_audio_monitoring"], "CH2/CH2")

        st_init = resolve_fx3_audio_reclevel_outtiming_state(
            audio_rec_level=14,
            audio_out_timing="Lip Sync",
            volume_settings=13,
            audio_monitoring_4ch="CH2/CH2",
            reset_action=RESET_ACTION_INITIALIZE_PHASE382,
        )
        self.assertEqual(st_init["effective_audio_rec_level"], 26)
        self.assertEqual(st_init["effective_audio_out_timing"], "Live")
        self.assertEqual(st_init["effective_volume_settings"], 7)
        self.assertEqual(st_init["effective_4ch_audio_monitoring"], "CH1/CH2")

    def test_32_g163_blocks_false_reset_claims_for_sound_option_and_audio_rec(self) -> None:
        r1 = verify_audio_reclevel_outtiming_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
            claim_camset_reset_clears_sound_option=True,
        )
        r2 = verify_audio_reclevel_outtiming_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
            claim_camset_reset_preserves_audio_recording=True,
        )
        for r in (r1, r2):
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE382)

    def test_33_g163_fx6_3tier_reference_6mic_4line_5reflevel_all_valid(self) -> None:
        for mref in FX6_INPUT_MIC_REFERENCE_6_STEPS_G163:
            res = verify_audio_reclevel_outtiming_guard(fx6_mic_reference=mref)
            self.assertTrue(res.valid, mref)
        for lref in FX6_LINE_INPUT_REFERENCE_4_STEPS_G163:
            res = verify_audio_reclevel_outtiming_guard(fx6_line_reference=lref)
            self.assertTrue(res.valid, lref)
        for rlvl in FX6_REFERENCE_LEVEL_5_STEPS_G163:
            res = verify_audio_reclevel_outtiming_guard(fx6_reference_level=rlvl)
            self.assertTrue(res.valid, rlvl)
            self.assertEqual(res.fx6_reference_level_step_count, 5)

    def test_34_g163_fx6_6mode_limiter_and_debunk_4mode_3reflevel_myths(self) -> None:
        for lim in FX6_LIMITER_MODE_6_STEPS_G163:
            res = verify_audio_reclevel_outtiming_guard(fx6_limiter_mode=lim)
            self.assertTrue(res.valid, lim)
            self.assertEqual(res.fx6_limiter_mode_count, 6)
        r1 = verify_audio_reclevel_outtiming_guard(claim_fx6_limiter_only_4_modes=True)
        r2 = verify_audio_reclevel_outtiming_guard(claim_fx6_ref_level_only_3_modes=True)
        self.assertFalse(r1.valid)
        self.assertFalse(r2.valid)

    def test_35_g163_fx6_7item_monitor_ch_headphone_out_and_volume_0_to_50(self) -> None:
        for mch in FX6_MONITOR_CH_7_ITEMS_G163:
            for hp in FX6_HEADPHONE_OUT_MODES_G163:
                res = verify_audio_reclevel_outtiming_guard(
                    fx6_monitor_ch=mch, fx6_headphone_out=hp, fx6_volume=50
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.fx6_monitor_ch_count, 7)
        r_bad = verify_audio_reclevel_outtiming_guard(fx6_volume=51)
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.block_errno, EINVAL_ERRNO_PHASE382)

    def test_36_g163_fx6_zero_monitor_vol_physical_side_keys_eopnotsupp95(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            request_fx6_monitor_vol_physical_keys=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE382)
        self.assertEqual(res.fx6_monitor_vol_physical_key_hits, 0)

    def test_37_g163_fx6_sdi_4ch_vs_hdmi_2ch_pair_enforced(self) -> None:
        r_ok = verify_audio_reclevel_outtiming_guard()
        self.assertEqual(r_ok.fx6_sdi_audio_channels, FX6_SDI_AUDIO_CHANNELS_G163)
        self.assertEqual(r_ok.fx6_hdmi_audio_channels, FX6_HDMI_AUDIO_CHANNELS_G163)
        r_bad = verify_audio_reclevel_outtiming_guard(claim_fx6_hdmi_carries_4ch=True)
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.block_errno, EINVAL_ERRNO_PHASE382)

    def test_38_g163_telemetry_rejects_bad_identity_enums_and_types(self) -> None:
        r1 = verify_audio_reclevel_outtiming_guard(body_model_name="ILME-FX6")
        r2 = verify_audio_reclevel_outtiming_guard(audio_out_timing="ZeroDelay")
        r3 = verify_audio_reclevel_outtiming_guard(xlr_h1_att_db=15)
        r4 = verify_audio_reclevel_outtiming_guard(audio_rec_level=True)  # type: ignore[arg-type]
        r5 = verify_audio_reclevel_outtiming_guard(fx6_limiter_mode="-20dB")
        for r in (r1, r2, r3, r4, r5):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G163_TELEMETRY_INVALID)

    def test_39_g163_480_state_matrix_invariants(self) -> None:
        mat = compute_audio_reclevel_outtiming_matrix()
        self.assertEqual(mat["total_states"], 480)
        self.assertTrue(mat["body_limiter_all_verified"])
        self.assertEqual(mat["sq_zero_ch_count"], 160)
        self.assertEqual(mat["mic35_preempt_shoe_count"], 80)
        self.assertEqual(mat["xlrh1_preempt_rec_level_count"], 160)
        self.assertEqual(mat["camset_reset_rec_level_count"], 120)
        self.assertEqual(mat["camset_reset_sound_option_survived_count"], 120)
        self.assertEqual(mat["initialize_sound_option_reset_count"], 120)

    def test_40_g163_evaluate_with_audit_wrapper_and_alias(self) -> None:
        v1, r1 = evaluate_g163_audio_reclevel_outtiming_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        v2, r2 = verify_audio_reclevel_outtiming_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v1.passed)
        self.assertTrue(r1.valid)
        self.assertEqual(v1.gate_id, G163)
        self.assertEqual(r1.status, r2.status)
        self.assertFalse(r1.persistent_emmc_writes_authorized)
        self.assertFalse(r1.cross_model_flash_authorized)
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)

    def test_41_g163_eopnotsupp_takes_priority_over_constraint_violations(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            audio_monitoring_4ch="CH1/CH2 mono mix",
            audio_rec_level=99,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE382)

    def test_42_g163_still_mode_supports_internal_mic_and_body_rec_level(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE382, audio_rec_level=20
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_audio_rec_level, 20)

    def test_43_g163_xlrh1_2ch_mode_reports_2_active_channels(self) -> None:
        res = verify_audio_reclevel_outtiming_guard(
            xlr_h1_attached=True,
            xlr_h1_handle_audio_on=True,
            xlr_h1_4ch_mode=False,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.active_audio_channels, 2)

    def test_44_g163_network_reset_does_not_reset_audio_rec_level_or_volume(self) -> None:
        st = resolve_fx3_audio_reclevel_outtiming_state(
            audio_rec_level=19,
            audio_out_timing="Lip Sync",
            volume_settings=11,
            audio_monitoring_4ch="CH1/CH1",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE382,
        )
        self.assertEqual(st["effective_audio_rec_level"], 19)
        self.assertEqual(st["effective_audio_out_timing"], "Lip Sync")
        self.assertEqual(st["effective_volume_settings"], 11)
        self.assertEqual(st["effective_4ch_audio_monitoring"], "CH1/CH1")

    def test_45_g163_uxc_resid16_anchors_and_menu_paths_match_wave72(self) -> None:
        self.assertEqual(AUDIO_REC_LEVEL_F_RESID16_G163, 0x63B9)
        self.assertEqual(AUDIO_OUT_TIMING_F_RESID16_G163, 0x6BC2)
        self.assertEqual(VOLUME_SETTINGS_BASE_RESID16_G163, 0xE8C9)
        self.assertEqual(AUDIO_MONITORING_4CH_F_RESID16_G163, 0x70DD)
        self.assertEqual(AUDIO_MON_CH1_CH2_F_RESID16_G163, 0x713B)
        self.assertEqual(AUDIO_MON_CH3_CH4_F_RESID16_G163, 0x6BF6)
        self.assertEqual(AUDIO_MON_CH13_CH24_F_RESID16_G163, 0x6C2E)
        self.assertEqual(AUDIO_MON_CH1_CH1_F_RESID16_G163, 0x6F9C)
        self.assertEqual(AUDIO_MON_CH2_CH2_F_RESID16_G163, 0x7A26)
        self.assertEqual(
            AUDIO_REC_LEVEL_MENU_PATH_G163,
            "Shooting -> [Audio Recording] -> [Audio Rec Level]",
        )
        self.assertEqual(
            AUDIO_OUT_TIMING_MENU_PATH_G163,
            "Shooting -> [Audio Recording] -> [Audio Out Timing]",
        )
        self.assertEqual(
            VOLUME_SETTINGS_MENU_PATH_G163,
            "Setup -> [Sound Option] -> [Volume Settings]",
        )
        self.assertEqual(
            AUDIO_MONITORING_4CH_MENU_PATH_G163,
            "Setup -> [Sound Option] -> [4ch Audio Monitoring]",
        )

    # ------------------------------------------------------------------
    # Gate G164: Touch 4 Active vs Dormant Pad/Shutter/AE & Spot Link (46..66)
    # ------------------------------------------------------------------

    def test_46_g164_default_safe_baseline_passes(self) -> None:
        res = verify_touchfunc_pcremote_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G164)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.fx3_touch_active_subitems_count, 4)
        self.assertEqual(res.effective_still_img_save_dest, "Destination Only")
        self.assertTrue(res.ram_only_zero_card_write_active)
        self.assertTrue(res.cardless_remote_shoot_allowed)
        self.assertEqual(res.slot1_writes, 0)
        self.assertEqual(res.usb_tx, 0)
        self.assertFalse(res.cross_model_flash_authorized)
        self.assertFalse(res.live_attach_authorized)
        self.assertEqual(res.rf_tx_packets, 0)

    def test_47_g164_all_4_active_touch_subitem_enums_valid_across_still_movie_sq(self) -> None:
        for sm in (
            SHOOT_MODE_STILL_PHASE382,
            SHOOT_MODE_MOVIE_PHASE382,
            SHOOT_MODE_SQ_PHASE382,
        ):
            for top in ALLOWED_TOUCH_OPERATION_MODES_G164:
                for sens in ALLOWED_TOUCH_SENSITIVITY_MODES_G164:
                    for tf in ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES_G164:
                        for sw in ALLOWED_SWIPE_UP_MODES_G164:
                            res = verify_touchfunc_pcremote_guard(
                                shoot_mode=sm,
                                touch_operation=top,
                                touch_sensitivity=sens,
                                touch_func_in_shooting=tf,
                                swipe_up=sw,
                            )
                            self.assertTrue(res.valid, f"{sm}/{top}/{sens}/{tf}/{sw}")

    def test_48_g164_mf_disables_touch_tracking_availability(self) -> None:
        res = verify_touchfunc_pcremote_guard(focus_mode="MF")
        self.assertTrue(res.valid)
        self.assertFalse(res.touch_tracking_available_in_focus_mode)

    def test_49_g164_blocks_all_4_dormant_touch_features_eopnotsupp95(self) -> None:
        for kw in (
            {"request_dormant_touch_panel_pad": True},
            {"request_dormant_touch_pad_vertical": True},
            {"request_dormant_touch_shutter": True},
            {"request_dormant_touch_ae": True},
            {"touch_func_in_shooting": "Touch Panel/Pad"},
            {"touch_func_in_shooting": "Touch Pad (vertical)"},
            {"touch_func_in_shooting": "Touch Shutter"},
            {"touch_func_in_shooting": "Touch AE"},
        ):
            res = verify_touchfunc_pcremote_guard(**kw)
            self.assertFalse(res.valid, str(kw))
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE382)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G164_DORMANT_TOUCH_OR_FX6_SAVE_DEST_EOPNOTSUPP,
            )

    def test_50_g164_touch_4items_resist_camset_reset_and_reset_only_on_initialize(self) -> None:
        st_rst = resolve_fx3_touchfunc_pcremote_state(
            touch_operation="Off",
            touch_sensitivity="Sensitive",
            touch_func_in_shooting="Touch Focus",
            swipe_up="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
        )
        self.assertEqual(st_rst["effective_touch_operation"], "Off")
        self.assertEqual(st_rst["effective_touch_sensitivity"], "Sensitive")
        self.assertEqual(st_rst["effective_touch_func_in_shooting"], "Touch Focus")
        self.assertEqual(st_rst["effective_swipe_up"], "Off")

        st_net = resolve_fx3_touchfunc_pcremote_state(
            touch_operation="Off",
            touch_sensitivity="Sensitive",
            touch_func_in_shooting="Touch Focus",
            swipe_up="Off",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE382,
        )
        self.assertEqual(st_net["effective_touch_operation"], "Off")

        st_init = resolve_fx3_touchfunc_pcremote_state(
            touch_operation="Off",
            touch_sensitivity="Sensitive",
            touch_func_in_shooting="Touch Focus",
            swipe_up="Off",
            reset_action=RESET_ACTION_INITIALIZE_PHASE382,
        )
        self.assertEqual(st_init["effective_touch_operation"], TOUCH_OPERATION_DEFAULT_G164)
        self.assertEqual(
            st_init["effective_touch_sensitivity"], TOUCH_SENSITIVITY_DEFAULT_G164
        )
        self.assertEqual(
            st_init["effective_touch_func_in_shooting"],
            TOUCH_FUNC_IN_SHOOTING_DEFAULT_G164,
        )
        self.assertEqual(st_init["effective_swipe_up"], SWIPE_UP_DEFAULT_G164)

    def test_51_g164_blocks_claim_camset_reset_clears_touch_4items(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
            claim_touch_4items_reset_by_camset_reset=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE382)

    def test_52_g164_spot_metering_point_anchored_at_initial_point_not_moving_track(self) -> None:
        r_link = verify_touchfunc_pcremote_guard(
            spot_metering_point="Focus Point Link",
            focus_area_category="Tracking: Spot",
        )
        self.assertTrue(r_link.valid)
        self.assertTrue(r_link.spot_metering_linked_to_initial_point)
        self.assertFalse(r_link.spot_metering_follows_moving_track_box)

        r_wide = verify_touchfunc_pcremote_guard(
            spot_metering_point="Focus Point Link",
            focus_area_category="Wide",
        )
        self.assertTrue(r_wide.valid)
        self.assertFalse(r_wide.spot_metering_linked_to_initial_point)
        self.assertTrue(any("Center" in w for w in r_wide.warnings))

        r_bad = verify_touchfunc_pcremote_guard(
            spot_metering_point="Focus Point Link",
            claim_spot_metering_follows_moving_track=True,
        )
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.block_errno, EINVAL_ERRNO_PHASE382)

    def test_53_g164_fx6_touch_function_in_mf_spot_focus_lockouts_enforced(self) -> None:
        r_ok = verify_touchfunc_pcremote_guard(
            fx6_touch_func_in_mf="Spot Focus",
            invoke_fx6_spot_focus_in_mf=True,
        )
        self.assertTrue(r_ok.valid)
        self.assertTrue(r_ok.fx6_spot_focus_in_mf_available)

        for lock_kw in (
            {"fx6_mf_lens_attached": True},
            {"fx6_desqueeze_mode": "1.3x"},
            {"fx6_focus_magnifier_active": True},
        ):
            r_blk = verify_touchfunc_pcremote_guard(
                fx6_touch_func_in_mf="Spot Focus",
                invoke_fx6_spot_focus_in_mf=True,
                **lock_kw,
            )
            self.assertFalse(r_blk.valid, str(lock_kw))
            self.assertEqual(r_blk.block_errno, EINVAL_ERRNO_PHASE382)

    def test_54_g164_fx6_big6_touch_requires_ver6_and_blocks_fx6_touch_shutter_ae(self) -> None:
        r_ok = verify_touchfunc_pcremote_guard(
            fx6_firmware_version="6.01", invoke_fx6_big6_touch=True
        )
        self.assertTrue(r_ok.valid)
        self.assertTrue(r_ok.fx6_big6_touch_available)

        r_old = verify_touchfunc_pcremote_guard(
            fx6_firmware_version="5.00", invoke_fx6_big6_touch=True
        )
        self.assertFalse(r_old.valid)
        self.assertEqual(r_old.block_errno, EOPNOTSUPP_ERRNO_PHASE382)

        r_ts = verify_touchfunc_pcremote_guard(request_fx6_touch_shutter_or_ae=True)
        self.assertFalse(r_ts.valid)
        self.assertEqual(r_ts.block_errno, EOPNOTSUPP_ERRNO_PHASE382)

    # ------------------------------------------------------------------
    # Gate G164: [Remote Shoot Setting], PTP/PTP-IP & Slot 1 EROFS=30 (55..78)
    # ------------------------------------------------------------------

    def test_55_g164_destination_only_cardless_ram_shoot_passes_zero_writes(self) -> None:
        for tr in ("ptp_usb", "ptp_ip_usblan", "ptp_ip_wired_lan"):
            res = verify_touchfunc_pcremote_guard(
                still_img_save_dest="Destination Only",
                ptp_transport=tr,
                ptp_ip_tcp_port=15740,
                pc_remote_connected=True,
                card_inserted=False,
                release_wo_card="Disable",
                remote_shutter_release_requested=True,
                target_media_slot=MEDIA_SLOT_1_PHASE382,
            )
            self.assertTrue(res.valid, f"{tr}: {res.errors}")
            self.assertTrue(res.ram_only_zero_card_write_active)
            self.assertTrue(res.cardless_remote_shoot_allowed)
            self.assertFalse(res.slot1_write_attempted)
            self.assertEqual(res.slot1_writes, 0)
            self.assertEqual(res.rf_tx_packets, 0)

    def test_56_g164_default_dest_plus_camera_on_slot1_blocked_erofs30(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            still_img_save_dest=STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164,
            card_inserted=True,
            target_media_slot=MEDIA_SLOT_1_PHASE382,
            remote_shutter_release_requested=True,
            slot1_tier0_protected=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE382)
        self.assertEqual(res.status, STATUS_BLOCKED_G164_SLOT1_REMOTE_SHOOT_WRITE_EROFS)
        self.assertEqual(res.slot1_writes, 0)
        self.assertEqual(res.usb_tx, 0)

    def test_57_g164_camera_only_on_slot1_blocked_erofs30(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            still_img_save_dest="Camera Only",
            card_inserted=True,
            target_media_slot=MEDIA_SLOT_1_PHASE382,
            remote_shutter_release_requested=True,
            slot1_tier0_protected=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE382)
        self.assertEqual(res.slot1_writes, 0)

    def test_58_g164_connected_dest_plus_camera_targeting_slot1_blocked_erofs30_preemptively(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            still_img_save_dest="Dest.+Camera",
            pc_remote_connected=True,
            target_media_slot=MEDIA_SLOT_1_PHASE382,
            remote_shutter_release_requested=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE382)

    def test_59_g164_dest_plus_camera_on_slot2_with_card_allowed_with_warning(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            still_img_save_dest="Dest.+Camera",
            card_inserted=True,
            target_media_slot=MEDIA_SLOT_2_PHASE382,
            remote_shutter_release_requested=True,
            slot1_tier0_protected=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.slot1_writes, 0)
        self.assertTrue(any("Dest.+Camera" in w for w in res.warnings))

    def test_60_g164_dest_plus_camera_cardless_rejected_even_if_release_wo_card_enable(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            still_img_save_dest="Dest.+Camera",
            card_inserted=False,
            release_wo_card="Enable",
            target_media_slot=MEDIA_SLOT_2_PHASE382,
            remote_shutter_release_requested=True,
            slot1_tier0_protected=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE382)

    def test_61_g164_changing_save_dest_while_pc_remote_connected_blocked_ebusy16(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            pc_remote_connected=True,
            attempt_change_save_dest_while_connected=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EBUSY_ERRNO_PHASE382)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G164_CONNECTED_SAVE_DEST_MUTATION_EBUSY
        )

    def test_62_g164_remote_shoot_4items_reset_matrix_camset_vs_init_vs_netreset(self) -> None:
        st_cam = resolve_fx3_touchfunc_pcremote_state(
            still_img_save_dest="Destination Only",
            save_image_size="Original",
            raw_j_save_image="RAW & JPEG",
            raw_h_save_image="RAW Only",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
        )
        self.assertEqual(st_cam["effective_still_img_save_dest"], "Destination Only")
        self.assertEqual(st_cam["effective_save_image_size"], "Original")
        self.assertEqual(st_cam["effective_raw_j_save_image"], "RAW & JPEG")
        self.assertEqual(st_cam["effective_raw_h_save_image"], "RAW Only")

        for rst in (
            RESET_ACTION_INITIALIZE_PHASE382,
            RESET_ACTION_RESET_NETWORK_SET_PHASE382,
        ):
            st_r = resolve_fx3_touchfunc_pcremote_state(
                still_img_save_dest="Destination Only",
                save_image_size="Original",
                raw_j_save_image="RAW & JPEG",
                raw_h_save_image="RAW Only",
                reset_action=rst,
            )
            self.assertEqual(
                st_r["effective_still_img_save_dest"],
                STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164,
            )
            self.assertEqual(st_r["effective_save_image_size"], SAVE_IMAGE_SIZE_DEFAULT_G164)
            self.assertEqual(
                st_r["effective_raw_j_save_image"], RAW_J_SAVE_IMAGE_DEFAULT_G164
            )
            self.assertEqual(
                st_r["effective_raw_h_save_image"], RAW_H_SAVE_IMAGE_DEFAULT_G164
            )

    def test_63_g164_reset_network_set_reverts_to_dest_plus_camera_triggering_slot1_erofs(self) -> None:
        # Subtle bench trap: after Reset Network Set., Still Img. Save Dest. reverts to Dest.+Camera!
        res = verify_touchfunc_pcremote_guard(
            still_img_save_dest="Destination Only",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE382,
            pc_remote_connected=True,
            target_media_slot=MEDIA_SLOT_1_PHASE382,
            remote_shutter_release_requested=True,
            slot1_tier0_protected=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE382)
        self.assertEqual(res.effective_still_img_save_dest, "Dest.+Camera")

    def test_64_g164_blocks_claim_camset_reset_clears_remote_shoot_settings(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
            claim_remote_shoot_reset_by_camset_reset=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE382)

    def test_65_g164_ptp_ip_requires_port_15740_and_zero_rf_airplane_mode(self) -> None:
        r_port = verify_touchfunc_pcremote_guard(
            ptp_transport="ptp_ip_usblan", ptp_ip_tcp_port=8080
        )
        self.assertFalse(r_port.valid)
        self.assertEqual(r_port.block_errno, EINVAL_ERRNO_PHASE382)

        r_wifi = verify_touchfunc_pcremote_guard(
            ptp_transport="ptp_ip_wifi", airplane_mode="On"
        )
        self.assertFalse(r_wifi.valid)
        self.assertEqual(r_wifi.block_errno, EINVAL_ERRNO_PHASE382)

        r_air = verify_touchfunc_pcremote_guard(airplane_mode="Off")
        self.assertFalse(r_air.valid)
        self.assertEqual(r_air.block_errno, EINVAL_ERRNO_PHASE382)

    def test_66_g164_fx6_still_img_save_dest_ui_rejected_eopnotsupp95(self) -> None:
        res = verify_touchfunc_pcremote_guard(request_fx6_still_img_save_dest_ui=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE382)
        self.assertFalse(res.fx6_still_img_save_dest_ui_exposed)

    def test_67_g164_erofs_takes_priority_over_ebusy_and_eopnotsupp(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            still_img_save_dest="Dest.+Camera",
            target_media_slot=MEDIA_SLOT_1_PHASE382,
            remote_shutter_release_requested=True,
            attempt_change_save_dest_while_connected=True,
            request_dormant_touch_shutter=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE382)

    def test_68_g164_ebusy_takes_priority_over_eopnotsupp(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            pc_remote_connected=True,
            attempt_change_save_dest_while_connected=True,
            request_dormant_touch_ae=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EBUSY_ERRNO_PHASE382)

    def test_69_g164_all_save_image_size_and_raw_jh_enums_valid(self) -> None:
        for sz in ALLOWED_SAVE_IMAGE_SIZE_G164:
            for rj in ALLOWED_RAW_J_SAVE_IMAGE_G164:
                for rh in ALLOWED_RAW_H_SAVE_IMAGE_G164:
                    res = verify_touchfunc_pcremote_guard(
                        save_image_size=sz,
                        raw_j_save_image=rj,
                        raw_h_save_image=rh,
                    )
                    self.assertTrue(res.valid)

    def test_70_g164_ptp_usb_sicd_device_nodes_verified(self) -> None:
        res = verify_touchfunc_pcremote_guard(ptp_transport="ptp_usb")
        self.assertTrue(res.valid)
        self.assertEqual(
            res.ptp_usb_device_nodes,
            ("/dev/usb/sicd_core", "/dev/usb/sicd_data", "/dev/usb/sicd_event"),
        )

    def test_71_g164_telemetry_rejects_bad_enums_and_types(self) -> None:
        r1 = verify_touchfunc_pcremote_guard(touch_operation="Always")
        r2 = verify_touchfunc_pcremote_guard(still_img_save_dest="Cloud")
        r3 = verify_touchfunc_pcremote_guard(ptp_ip_tcp_port=99999)
        r4 = verify_touchfunc_pcremote_guard(pc_remote_connected="yes")  # type: ignore[arg-type]
        r5 = verify_touchfunc_pcremote_guard(target_media_slot=3)
        for r in (r1, r2, r3, r4, r5):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G164_TELEMETRY_INVALID)

    def test_72_g164_432_state_matrix_invariants(self) -> None:
        mat = compute_touchfunc_pcremote_matrix()
        self.assertEqual(mat["total_states"], 432)
        self.assertEqual(mat["touch_camset_survived_count"], 108)
        self.assertEqual(mat["touch_init_reset_count"], 108)
        self.assertEqual(mat["remote_camset_survived_count"], 108)
        self.assertEqual(mat["remote_netreset_reverted_default_count"], 108)
        self.assertEqual(mat["dest_only_zero_card_count"], 72)
        self.assertEqual(mat["slot1_write_detected_count"], 180)
        self.assertTrue(mat["zero_rf_wired_all_verified"])

    def test_73_g164_evaluate_with_audit_wrapper_and_alias(self) -> None:
        v1, r1 = evaluate_g164_touchfunc_pcremote_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        v2, r2 = verify_touchfunc_pcremote_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v1.passed)
        self.assertTrue(r1.valid)
        self.assertEqual(v1.gate_id, G164)
        self.assertEqual(r1.status, r2.status)
        self.assertFalse(r1.persistent_emmc_writes_authorized)
        self.assertFalse(r1.cross_model_flash_authorized)
        self.assertFalse(r1.hardware_live_attachment_authorized)

    def test_74_g164_uxc_resid16_anchors_and_menu_paths_match_wave72(self) -> None:
        self.assertEqual(DORMANT_TOUCH_PANEL_PAD_F_RESID16_G164, 0x76EC)
        self.assertEqual(DORMANT_TOUCH_PAD_VERTICAL_F_RESID16_G164, 0x7312)
        self.assertEqual(DORMANT_TOUCH_SHUTTER_F_RESID16_G164, 0x6A80)
        self.assertEqual(DORMANT_TOUCH_AE_F_RESID16_G164, 0x702A)
        self.assertEqual(REMOTE_SHOOT_SETTING_F_RESID16_G164, 0x7BA4)
        self.assertEqual(TOUCH_OPERATION_MENU_PATH_G164, "Setup -> [Touch Operation]")
        self.assertEqual(
            REMOTE_SHOOT_SETTING_MENU_PATH_G164,
            "Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]",
        )

    def test_75_g164_disconnected_save_dest_change_allowed(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            pc_remote_connected=False,
            attempt_change_save_dest_while_connected=True,
        )
        self.assertTrue(res.valid)

    def test_76_g164_spot_metering_modes_both_valid(self) -> None:
        for smp in ALLOWED_SPOT_METERING_POINTS_G164:
            res = verify_touchfunc_pcremote_guard(spot_metering_point=smp)
            self.assertTrue(res.valid)

    def test_77_g164_fx6_tracking_af_in_mf_remains_available_with_mf_lens(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            fx6_touch_func_in_mf="Tracking AF",
            fx6_mf_lens_attached=True,
            invoke_fx6_spot_focus_in_mf=False,
        )
        self.assertTrue(res.valid)

    def test_78_g164_ptp_transport_none_allowed_when_disconnected(self) -> None:
        res = verify_touchfunc_pcremote_guard(
            ptp_transport="none", pc_remote_connected=False
        )
        self.assertTrue(res.valid)

    # ------------------------------------------------------------------
    # Unified 164-Gate Master Preflight, 4-Mode, CLI & Redlines (79..110)
    # ------------------------------------------------------------------

    def test_79_master_164gate_offline_nogo_161_of_164_clean_room(self) -> None:
        rep = evaluate_164gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertIsInstance(rep, Master164GateReport)
        self.assertEqual(rep.schema_version, REALHW_164GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(rep.status, "VERIFIED_161_OF_164_AWAITING_PHYSICAL_TIER0")
        self.assertGreaterEqual(rep.summary["total_gates"], 164)
        self.assertEqual(rep.summary["total_gates"], 164)
        self.assertEqual(rep.summary["verified_gates"], 161)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(len(rep.gates), 164)
        self.assertTrue(rep.offline_161_gates_verified)
        self.assertFalse(rep.all_164_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_80_master_164gate_simulated_dry_run_164_of_164_clean_room(self) -> None:
        rep = evaluate_164gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(rep.status, "VERIFIED_ALL_164_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(rep.summary["verified_gates"], 164)
        self.assertTrue(rep.all_164_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertTrue(rep.g163_to_g164_all_passed)
        self.assertTrue(rep.g13_to_g164_all_passed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_81_master_164gate_normal_mode_local_donor_or_fallback(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE382: ""},
            clear=False,
        ):
            rep = evaluate_164gate_preflight(REPO_ROOT)
        self.assertEqual(rep.summary["verified_gates"], 161)
        self.assertTrue(rep.offline_161_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_82_master_164gate_fx3_clean_room_test_env_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ENV_CLEAN_ROOM_TEST_PHASE382: "1", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            clear=False,
        ):
            rep = evaluate_164gate_preflight(REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.summary["verified_gates"], 161)

    def test_83_master_164gate_work_root_none_donorless_fallback(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE382: ""},
                clear=False,
            ):
                rep = evaluate_164gate_preflight(REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.summary["verified_gates"], 161)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_84_master_164gate_aliases_return_equivalent_reports(self) -> None:
        base_m162 = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        r1 = evaluate_164_master_safety_gates(
            REPO_ROOT, force_clean_room=True, master_162_override=base_m162
        )
        r2 = run_164_gate_preflight(
            REPO_ROOT, force_clean_room=True, master_162_override=base_m162
        )
        r3 = verify_real_hardware_164gate_readiness(
            REPO_ROOT, force_clean_room=True, master_162_override=base_m162
        )
        self.assertEqual(r1.status, r2.status)
        self.assertEqual(r2.status, r3.status)
        self.assertEqual(r3.summary["total_gates"], 164)

    def test_85_master_164gate_blocks_g163_failure_propagation(self) -> None:
        base_m162 = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_164gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            master_162_override=base_m162,
            audio_reclevel_outtiming_kwargs={"audio_monitoring_4ch": "CH1/CH2 mono mix"},
        )
        self.assertFalse(rep.g163_to_g164_all_passed)
        self.assertFalse(rep.offline_161_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G163_FABRICATED_4CH_BODY_LIMITER_OFF_OR_FX6_MONVOL_EOPNOTSUPP,
        )
        self.assertEqual(rep.summary["verified_gates"], 160)

    def test_86_master_164gate_blocks_g164_slot1_erofs_propagation(self) -> None:
        base_m162 = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_164gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            master_162_override=base_m162,
            touchfunc_pcremote_kwargs={
                "still_img_save_dest": "Dest.+Camera",
                "target_media_slot": MEDIA_SLOT_1_PHASE382,
                "remote_shutter_release_requested": True,
            },
        )
        self.assertFalse(rep.g163_to_g164_all_passed)
        self.assertFalse(rep.offline_161_gates_verified)
        self.assertEqual(rep.status, STATUS_BLOCKED_G164_SLOT1_REMOTE_SHOOT_WRITE_EROFS)
        self.assertEqual(rep.summary["verified_gates"], 160)

    def test_87_master_164gate_blocks_persistent_emmc_write_request(self) -> None:
        base_m162 = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_164gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            master_162_override=base_m162,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_161_gates_verified)
        self.assertFalse(rep.all_164_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_88_master_164gate_gate_ids_contiguous_g01_to_g164(self) -> None:
        base_m162 = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_164gate_preflight(
            REPO_ROOT, force_clean_room=True, master_162_override=base_m162
        )
        ids = [g["gate_id"] for g in rep.gates]
        self.assertEqual(len(ids), 164)
        self.assertEqual(ids[-2], G163)
        self.assertEqual(ids[-1], G164)
        self.assertEqual(len(set(ids)), 164)

    def test_89_master_164gate_simulate_bench_dry_run_kwarg_alias(self) -> None:
        base_m162_sim = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        rep = evaluate_164gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_162_override=base_m162_sim,
        )
        self.assertTrue(rep.all_164_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.summary["verified_gates"], 164)

    def test_90_master_164gate_dry_run_simulated_backup_kwarg_alias(self) -> None:
        base_m162_sim = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        rep = evaluate_164gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_162_override=base_m162_sim,
        )
        self.assertTrue(rep.all_164_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 164)

    def test_91_master_164gate_json_serializable_no_raw_bytes(self) -> None:
        base_m162 = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_164gate_preflight(
            REPO_ROOT, force_clean_room=True, master_162_override=base_m162
        )
        encoded = json.dumps(rep.to_dict(), ensure_ascii=False)
        parsed = json.loads(encoded)
        self.assertGreaterEqual(parsed["summary"]["total_gates"], 164)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_92_package_exports_include_164gate_entrypoints(self) -> None:
        for sym in (
            "G163",
            "G164",
            "Master164GateReport",
            "evaluate_164gate_preflight",
            "evaluate_164_master_safety_gates",
            "run_164_gate_preflight",
            "verify_real_hardware_164gate_readiness",
            "evaluate_g163_audio_reclevel_outtiming_guard",
            "evaluate_g164_touchfunc_pcremote_guard",
            "verify_audio_reclevel_outtiming_guard",
            "verify_touchfunc_pcremote_guard",
            "audit_phase382_donor_contracts",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing export: {sym}")
            self.assertIn(sym, fx3_safety.__all__, f"Missing in __all__: {sym}")

    def test_93_module_cli_g163_and_g164_summary_and_json(self) -> None:
        for gate_arg in ("g163", "g164"):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = guard_module_main(
                    ["--gate", gate_arg, "--force-clean-room", "--summary", "--json"]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_94_module_cli_164_json_dry_run(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = guard_module_main(
                [
                    "--gate",
                    "164",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--summary",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 164)
        self.assertEqual(
            payload["status"], "VERIFIED_ALL_164_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_95_module_cli_g163_g164_text_output(self) -> None:
        for gate_arg, expected in (("g163", "gate=G163"), ("g164", "gate=G164")):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = guard_module_main(["--gate", gate_arg, "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn(expected, buf.getvalue())

    def test_96_safety_cli_verify_g163_and_aliases(self) -> None:
        for subcmd in (
            "verify-audio-reclevel-outtiming-guard",
            "verify-g163-audio-reclevel-outtiming",
            "verify-g163",
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = safety_cli.main(
                    [subcmd, "--force-clean-room", "--summary", "--json"]
                )
            self.assertEqual(rc, 0, subcmd)
            data = json.loads(buf.getvalue())
            self.assertEqual(data["gate"], G163)
            self.assertTrue(data["valid"])
            self.assertEqual(data["effective_audio_rec_level"], 26)
            self.assertEqual(data["effective_4ch_audio_monitoring"], "CH1/CH2")
            self.assertEqual(data["fx6_monitor_vol_physical_key_hits"], 0)

    def test_97_safety_cli_verify_g164_and_aliases(self) -> None:
        for subcmd in (
            "verify-touchfunc-pcremote-guard",
            "verify-g164-touchfunc-pcremote",
            "verify-g164",
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = safety_cli.main(
                    [subcmd, "--force-clean-room", "--summary", "--json"]
                )
            self.assertEqual(rc, 0, subcmd)
            data = json.loads(buf.getvalue())
            self.assertEqual(data["gate"], G164)
            self.assertTrue(data["valid"])
            self.assertEqual(data["fx3_touch_active_subitems_count"], 4)
            self.assertEqual(data["effective_still_img_save_dest"], "Destination Only")
            self.assertEqual(data["ptp_ip_tcp_port"], 15740)
            self.assertEqual(data["slot1_writes"], 0)

    def test_98_safety_cli_verify_164_gates_offline_text_and_json(self) -> None:
        buf_txt = StringIO()
        with redirect_stdout(buf_txt):
            rc = safety_cli.main(["verify-164-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        out = buf_txt.getvalue()
        self.assertIn("verified=161/164", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)

        buf_json = StringIO()
        with redirect_stdout(buf_json):
            rc2 = safety_cli.main(
                ["verify-164-gates", "--force-clean-room", "--summary", "--json"]
            )
        self.assertEqual(rc2, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 161)
        self.assertEqual(payload["g163_status"], STATUS_VERIFIED_G163)
        self.assertEqual(payload["g164_status"], STATUS_VERIFIED_G164)

    def test_99_safety_cli_verify_164_gates_dry_run_164_of_164(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = safety_cli.main(
                [
                    "verify-164-gates",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--summary",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 164)
        self.assertTrue(payload["summary"]["all_164_gates_verified"])
        self.assertFalse(payload["summary"]["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["summary"]["cross_model_flash_authorized"])
        self.assertEqual(payload["summary"]["usb_packets_transmitted"], 0)

    def test_100_readme_documents_phase382_164_gates_and_cli(self) -> None:
        readme_text = (SAFETY_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Phase 382", readme_text)
        self.assertIn("verify-164-gates", readme_text)
        self.assertIn("G163", readme_text)
        self.assertIn("G164", readme_text)
        self.assertIn("164/164", readme_text)

    def test_101_safety_cli_text_output_for_g163_and_g164(self) -> None:
        buf1 = StringIO()
        with redirect_stdout(buf1):
            rc1 = safety_cli.main(["verify-g163", "--force-clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn("gate=G163", buf1.getvalue())
        self.assertIn("rec_lvl=26", buf1.getvalue())
        self.assertIn("mon4ch=CH1/CH2", buf1.getvalue())

        buf2 = StringIO()
        with redirect_stdout(buf2):
            rc2 = safety_cli.main(["verify-g164", "--force-clean-room"])
        self.assertEqual(rc2, 0)
        self.assertIn("gate=G164", buf2.getvalue())
        self.assertIn("save_dest=Destination Only", buf2.getvalue())
        self.assertIn("s1_writes=0", buf2.getvalue())

    def test_102_cli_main_help_formatting_no_percent_error(self) -> None:
        for argv in (
            ["--help"],
            ["verify-g163", "--help"],
            ["verify-g164", "--help"],
            ["verify-164-gates", "--help"],
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    safety_cli.main(argv)
            self.assertEqual(cm.exception.code, 0, argv)
            self.assertGreater(len(buf.getvalue()), 20)

    def test_103_no_pyc_artifacts_created_during_suite(self) -> None:
        pycache_dirs = list((SAFETY_ROOT / "fx3_safety").rglob("__pycache__")) + list(
            (SAFETY_ROOT / "tests").rglob("__pycache__")
        )
        pyc_files = [
            p
            for d in pycache_dirs
            for p in d.rglob("*.pyc")
            if "164gate" in p.name
        ]
        self.assertEqual(pyc_files, [])

    def test_104_fx3_vs_fx6_wave72_contrast_invariants_locked(self) -> None:
        self.assertEqual(len(FX6_INPUT_MIC_REFERENCE_6_STEPS_G163), 6)
        self.assertEqual(len(FX6_LINE_INPUT_REFERENCE_4_STEPS_G163), 4)
        self.assertEqual(len(FX6_REFERENCE_LEVEL_5_STEPS_G163), 5)
        self.assertEqual(len(FX6_LIMITER_MODE_6_STEPS_G163), 6)
        self.assertEqual(len(FX6_MONITOR_CH_7_ITEMS_G163), 7)
        self.assertEqual(FX6_SDI_AUDIO_CHANNELS_G163, 4)
        self.assertEqual(FX6_HDMI_AUDIO_CHANNELS_G163, 2)
        self.assertEqual(FX6_MONITOR_VOL_PHYSICAL_KEY_HITS_G163, 0)
        self.assertFalse(FX3_EVF_PRESENT_G164)
        self.assertFalse(FX3_SPOT_METERING_FOLLOWS_MOVING_TRACK_BOX_G164)
        self.assertFalse(FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED_G164)
        self.assertEqual(len(FX3_PTP_USB_DEVICE_NODES_G164), 3)
        self.assertEqual(len(ALLOWED_PTP_TRANSPORTS_G164), 5)

    def test_105_master_164gate_deterministic_clean_room_canonical_equality(self) -> None:
        base_m162 = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        r1 = strip_elapsed_seconds_recursive_phase382(
            evaluate_164gate_preflight(
                REPO_ROOT, force_clean_room=True, master_162_override=base_m162
            ).to_dict()
        )
        r2 = strip_elapsed_seconds_recursive_phase382(
            evaluate_164gate_preflight(
                REPO_ROOT, force_clean_room=True, master_162_override=base_m162
            ).to_dict()
        )
        r1.pop("evaluated_utc", None)
        r2.pop("evaluated_utc", None)
        self.assertEqual(r1, r2)

    def test_106_donor_audit_work_root_none_with_override_reports_error(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            audit = audit_phase382_donor_contracts(
                force_clean_room=False,
                donor_specs_override={
                    "x": ("FX3", "x.bin", 4, "0" * 64, (b"ABCD",), "override")
                },
            )
        self.assertFalse(audit.valid)
        self.assertTrue(any("work_root_none" in m for m in audit.missing_markers))

    def test_107_master_164gate_redlines_all_hard_locked_false_and_zero(self) -> None:
        base_m162 = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_164gate_preflight(
            REPO_ROOT, force_clean_room=True, master_162_override=base_m162
        )
        self.assertTrue(rep.agent_auto_flash_blocked)
        self.assertFalse(rep.human_hardware_attach_token)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.physical_flash_auto_exec_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_108_master_164gate_upstream_162_failure_propagates(self) -> None:
        bad_m162 = fx3_safety.evaluate_162gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            antidust_focusmag_kwargs={"request_dormant_antidust_function": True},
        )
        rep = evaluate_164gate_preflight(
            REPO_ROOT, force_clean_room=True, master_162_override=bad_m162
        )
        self.assertFalse(rep.g13_to_g164_all_passed)
        self.assertFalse(rep.offline_161_gates_verified)
        self.assertEqual(rep.status, bad_m162.status)


if __name__ == "__main__":
    unittest.main()
