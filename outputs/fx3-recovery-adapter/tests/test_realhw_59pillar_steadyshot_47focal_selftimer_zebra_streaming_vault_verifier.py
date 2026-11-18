"""Phase 332 (Pillar 59 & 59/59 Master) unit tests (Wave-57 SteadyShot 47-Focal & 4 Lockouts / Dormant Movie Self-Timer vs Still Self-Timer #8 LED & Audio / Zebra Custom1-2 & Peaking Clean-HDMI / RTMP-RTMPS-SRT Streaming Zero-RF & Slot-1 EROFS=30 Vault Firewall)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_ROOT = Path(__file__).resolve().parents[1]
if str(ADAPTER_ROOT) not in sys.path:
    sys.path.insert(0, str(ADAPTER_ROOT))

import fx3_recovery as fr  # noqa: E402
from fx3_recovery import (  # noqa: E402
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    MASTER_59_PILLAR_COUNT,
    MASTER_59_PILLAR_IDS,
    MASTER_59_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P332_ACTIVE_CROP_FACTOR_APPROX,
    P332_ACTIVE_LOCKOUT_CONDITIONS,
    P332_AIRPLANE_MODE_FORCED_ON,
    P332_AUDIO_SIGNALS_MODES,
    P332_BLOCKED_FX6_IBIS_OR_SELFTIMER_SPOOF,
    P332_BLOCKED_INVALID_PILLAR59A_SPEC,
    P332_BLOCKED_INVALID_PILLAR59B_SPEC,
    P332_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P332_BLOCKED_SELFTIMER_DORMANT_OR_LED8_AUDIO_DRIFT,
    P332_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT,
    P332_BLOCKED_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT,
    P332_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P332_BLOCKED_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT,
    P332_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
    P332_BRACKET_SELFTIMER_OPTIONS,
    P332_CONCURRENT_CEILING_SECONDS,
    P332_DE_SQUEEZE_OPTIONS,
    P332_DORMANT_SELFTIMER_SYMBOLS,
    P332_DRIVE_MODE_SELFTIMER_TYPES,
    P332_EINVAL_ERRNO,
    P332_EOPNOTSUPP_ERRNO,
    P332_EROFS_ERRNO,
    P332_FAST_CLI_BUDGET_SECONDS,
    P332_FRONT_LAMP_8_FUNCTION,
    P332_FRONT_LAMP_8_ID,
    P332_FX3_FW_VERSION,
    P332_FX3_HAS_5AXIS_IBIS,
    P332_FX3_HAS_MOVIE_SELF_TIMER,
    P332_FX3_MODEL_NAME,
    P332_FX6_ALT_REC_FEATURES,
    P332_FX6_DONOR_FW_VERSION,
    P332_FX6_DONOR_MODEL_NAME,
    P332_FX6_DORMANT_STREAMING_SYMBOLS,
    P332_FX6_HAS_6AXIS_GYRO_METADATA,
    P332_FX6_HAS_IBIS,
    P332_FX6_HAS_STILL_SELF_TIMER,
    P332_FX6_IBIS_UNSUPPORTED_SYMBOL,
    P332_FX6_PEAKING_COLORS,
    P332_FX6_ZEBRA_MODES,
    P332_IMAGE_STABILIZATION_4_ITEMS,
    P332_IMAGE_STABILIZATION_ITEM_COUNT,
    P332_MOVIE_REC_DURING_STREAMING_MODES,
    P332_MOVIE_STEADYSHOT_MODES,
    P332_NOMINAL_BUDGET_SECONDS,
    P332_PEAKING_COLORS,
    P332_PEAKING_COLOR_DEFAULT,
    P332_PILLAR_59A_SCENARIO_IDS,
    P332_PILLAR_59B_SCENARIO_IDS,
    P332_RF_PACKETS_TRANSMITTED,
    P332_SELFTIMER_CONT_COMBOS,
    P332_SELFTIMER_CONT_COMBO_COUNT,
    P332_SELFTIMER_SINGLE_DELAYS_SEC,
    P332_SLOG3_18_GRAY_IRE,
    P332_SLOG3_90_WHITE_IRE,
    P332_SLOG3_CLIP_IRE,
    P332_SLOT1_DATA_SECTOR_WRITES,
    P332_SLOT1_FORMAT_HARD_LOCKED,
    P332_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P332_SRT_ENCRYPTION_MODES,
    P332_STATUS_VERIFIED_59OF59_AGGREGATOR,
    P332_STATUS_VERIFIED_PILLAR59_SUITE,
    P332_STATUS_VERIFIED_PILLAR_59A,
    P332_STATUS_VERIFIED_PILLAR_59B,
    P332_STEADYSHOT_47_FOCAL_LENGTHS_MM,
    P332_STEADYSHOT_ADJUST_MODES,
    P332_STEADYSHOT_FOCAL_LENGTH_COUNT,
    P332_STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM,
    P332_STILL_STEADYSHOT_MODES,
    P332_STREAMING_ALLOWED_FPS,
    P332_STREAMING_DISALLOWED_FPS,
    P332_STREAMING_MENU_PATH,
    P332_STREAMING_PROTOCOLS,
    P332_STREAMING_VIDEO_CODECS_BY_PROTOCOL,
    P332_TIER0_SURFACE_COUNT,
    P332_ZEBRA_LEVEL_OPTIONS,
    P332_ZEBRA_PRESET_LEVELS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PHASE332_MASTER_SCHEMA,
    PHASE332_PHASE_NUMBER,
    PHASE332_SCHEMA,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_steadyshot_47focal_selftimer_vault_spec,
    build_default_safe_zebra_peaking_streaming_vault_spec,
    compute_expected_steadyshot_selftimer_state,
    compute_expected_zebra_peaking_streaming_vault_state,
    evaluate_59pillar_recovery_master,
    evaluate_realhw_59pillar_recovery_master,
    evaluate_steadyshot_47focal_selftimer_vault,
    evaluate_zebra_peaking_streaming_vault,
    inspect_phase332_donors_readonly,
    run_pillar59_standalone_suite,
    run_pillar59a_steadyshot_47focal_selftimer_6_scenario_suite,
    run_pillar59b_zebra_peaking_streaming_vault_6_scenario_suite,
    verify_59pillar_recovery_suite,
    verify_steadyshot_47focal_selftimer_zebra_streaming_and_vault,
    verify_steadyshot_47focal_selftimer_zebra_streaming_vault,
)
from fx3_recovery import (  # noqa: E402
    realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier as p59_mod,
)


class Phase332Pillar59VerifierTests(unittest.TestCase):
    """Comprehensive unit tests for Phase 332 Pillar 59 & 59/59 Master."""

    def test_01_safety_policy_flags_hard_locked(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(P332_RF_PACKETS_TRANSMITTED, 0)
        self.assertEqual(P332_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertTrue(P332_AIRPLANE_MODE_FORCED_ON)
        self.assertTrue(P332_SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(P332_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)

    def test_02_schema_and_pillar_metadata(self) -> None:
        self.assertEqual(PHASE332_PHASE_NUMBER, 332)
        self.assertEqual(PHASE332_SCHEMA, "realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier_v1")
        self.assertEqual(PHASE332_MASTER_SCHEMA, "realhw_59pillar_recovery_master_v1")
        self.assertEqual(MASTER_59_PILLAR_COUNT, 59)
        self.assertEqual(len(MASTER_59_PILLAR_IDS), 59)
        self.assertEqual(len(MASTER_59_PILLAR_SPECS), 59)
        self.assertEqual(MASTER_59_PILLAR_IDS[-1], "pillar59_steadyshot_47focal_selftimer_zebra_streaming_vault")

    def test_03_steadyshot_4_items_and_47_focal_table(self) -> None:
        self.assertEqual(P332_IMAGE_STABILIZATION_ITEM_COUNT, 4)
        self.assertEqual(
            P332_IMAGE_STABILIZATION_4_ITEMS,
            ("SteadyShot (Movie)", "SteadyShot (Still)", "SteadyShot Adjust.", "Focal Length"),
        )
        self.assertEqual(P332_STEADYSHOT_FOCAL_LENGTH_COUNT, 47)
        self.assertEqual(len(P332_STEADYSHOT_47_FOCAL_LENGTHS_MM), 47)
        self.assertEqual(P332_STEADYSHOT_47_FOCAL_LENGTHS_MM[0], 8)
        self.assertEqual(P332_STEADYSHOT_47_FOCAL_LENGTHS_MM[-1], 1000)
        self.assertEqual(P332_STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM, 8)
        self.assertNotIn(42, P332_STEADYSHOT_47_FOCAL_LENGTHS_MM)
        self.assertIn(85, P332_STEADYSHOT_47_FOCAL_LENGTHS_MM)
        self.assertIn(135, P332_STEADYSHOT_47_FOCAL_LENGTHS_MM)

    def test_04_steadyshot_modes_and_lockout_constants(self) -> None:
        self.assertEqual(P332_MOVIE_STEADYSHOT_MODES, ("Active", "Standard", "Off"))
        self.assertEqual(P332_STILL_STEADYSHOT_MODES, ("On", "Off"))
        self.assertEqual(P332_STEADYSHOT_ADJUST_MODES, ("Auto", "Manual"))
        self.assertAlmostEqual(P332_ACTIVE_CROP_FACTOR_APPROX, 1.104, places=3)
        self.assertEqual(len(P332_ACTIVE_LOCKOUT_CONDITIONS), 4)
        self.assertEqual(P332_DE_SQUEEZE_OPTIONS, ("Off", "1.3x", "1.5x", "1.65x", "1.8x", "2.0x"))

    def test_05_selftimer_led8_and_audio_constants(self) -> None:
        self.assertFalse(P332_FX3_HAS_MOVIE_SELF_TIMER)
        self.assertTrue(P332_FX3_HAS_5AXIS_IBIS)
        self.assertEqual(P332_SELFTIMER_SINGLE_DELAYS_SEC, (10, 5, 2))
        self.assertEqual(P332_SELFTIMER_CONT_COMBO_COUNT, 6)
        self.assertEqual(len(P332_SELFTIMER_CONT_COMBOS), 6)
        self.assertEqual(P332_BRACKET_SELFTIMER_OPTIONS, ("Off", "2 Sec", "5 Sec", "10 Sec"))
        self.assertEqual(P332_FRONT_LAMP_8_ID, 8)
        self.assertIn("Self-timer", P332_FRONT_LAMP_8_FUNCTION)
        self.assertEqual(P332_AUDIO_SIGNALS_MODES, ("On", "Off"))
        self.assertEqual(len(P332_DORMANT_SELFTIMER_SYMBOLS), 4)

    def test_06_fx6_ibis_selftimer_zebra_peaking_streaming_constants(self) -> None:
        self.assertFalse(P332_FX6_HAS_IBIS)
        self.assertTrue(P332_FX6_HAS_6AXIS_GYRO_METADATA)
        self.assertFalse(P332_FX6_HAS_STILL_SELF_TIMER)
        self.assertEqual(P332_FX6_IBIS_UNSUPPORTED_SYMBOL, "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED")
        self.assertEqual(P332_FX6_ALT_REC_FEATURES, ("Picture Cache Rec", "Interval Rec"))
        self.assertEqual(P332_FX6_ZEBRA_MODES, ("Off", "Zebra1", "Zebra2"))
        self.assertEqual(P332_FX6_PEAKING_COLORS, ("B&W", "Red", "Yellow", "Blue"))
        self.assertEqual(
            P332_FX6_DORMANT_STREAMING_SYMBOLS,
            ("RTMP", "RTMPS", "SRT", "QoS Streaming", "Intelligent QoS"),
        )

    def test_07_zebra_peaking_and_streaming_constants(self) -> None:
        self.assertEqual(len(P332_ZEBRA_PRESET_LEVELS), 8)
        self.assertEqual(len(P332_ZEBRA_LEVEL_OPTIONS), 10)
        self.assertEqual(P332_SLOG3_18_GRAY_IRE, 41)
        self.assertEqual(P332_SLOG3_90_WHITE_IRE, 61)
        self.assertEqual(P332_SLOG3_CLIP_IRE, 94)
        self.assertEqual(P332_PEAKING_COLORS, ("Red", "Yellow", "Blue", "White"))
        self.assertEqual(P332_PEAKING_COLOR_DEFAULT, "White")
        self.assertEqual(P332_STREAMING_MENU_PATH, ("Network", "Streaming", "Network Streaming"))
        self.assertEqual(P332_STREAMING_PROTOCOLS, ("RTMP", "RTMPS", "SRT"))
        self.assertEqual(P332_STREAMING_ALLOWED_FPS, ("59.94p", "50p", "29.97p", "25p"))
        self.assertEqual(P332_STREAMING_DISALLOWED_FPS, ("23.98p", "24p", "24.00p"))
        self.assertEqual(P332_STREAMING_VIDEO_CODECS_BY_PROTOCOL["RTMP"], ("H.264",))
        self.assertEqual(P332_STREAMING_VIDEO_CODECS_BY_PROTOCOL["RTMPS"], ("H.264",))
        self.assertEqual(P332_STREAMING_VIDEO_CODECS_BY_PROTOCOL["SRT"], ("H.265", "H.264"))
        self.assertEqual(P332_SRT_ENCRYPTION_MODES, ("None", "AES-128", "AES-256"))
        self.assertEqual(P332_MOVIE_REC_DURING_STREAMING_MODES, ("Disable", "Enable"))

    def test_08_errno_and_scenario_id_constants(self) -> None:
        self.assertEqual(P332_EINVAL_ERRNO, 22)
        self.assertEqual(P332_EROFS_ERRNO, 30)
        self.assertEqual(P332_EOPNOTSUPP_ERRNO, 95)
        self.assertEqual(len(P332_PILLAR_59A_SCENARIO_IDS), 6)
        self.assertEqual(len(P332_PILLAR_59B_SCENARIO_IDS), 6)
        self.assertEqual(P332_TIER0_SURFACE_COUNT, 16)

    def test_09_donor_inspection_normal_mode(self) -> None:
        snap = inspect_phase332_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(len(snap.artifacts), 17)
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap.under_0_20s_budget)
        self.assertTrue(snap.elapsed_seconds <= snap.budget_seconds_applied + 0.5)
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(all(a.present and a.matches_pinned for a in snap.artifacts))

    def test_10_donor_inspection_force_clean_room_true(self) -> None:
        snap = inspect_phase332_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))
        self.assertTrue(snap.all_donors_present)

    def test_11_donor_inspection_env_clean_room_test(self) -> None:
        with patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}):
            snap = inspect_phase332_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertTrue(snap.all_donors_present)

    def test_12_donor_inspection_env_force_clean_room(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase332_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertTrue(snap.all_donors_present)

    def test_13_donorless_work_root_none_guard_no_typeerror(self) -> None:
        with patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "", "FX3_FX6_FORCE_CLEAN_ROOM": ""}):
            self.assertIsNone(p59_mod._resolve_phase332_donor_path("work/missing.bin", work_roots=(None,)))
            with patch.object(p59_mod, "_iter_work_roots", return_value=(None,)):
                snap = inspect_phase332_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertTrue(snap.all_donors_present)

    def test_14_donor_inspection_contains_fx3_and_fx6_counts(self) -> None:
        snap = inspect_phase332_donors_readonly(force_clean_room=True)
        fx3_count = sum(1 for a in snap.artifacts if a.artifact_id.startswith("fx3_"))
        fx6_count = sum(1 for a in snap.artifacts if a.artifact_id.startswith("fx6_"))
        self.assertEqual(fx3_count, 14)
        self.assertEqual(fx6_count, 3)

    def test_15_donor_snapshot_to_dict_serializable(self) -> None:
        snap = inspect_phase332_donors_readonly(force_clean_room=True)
        d = snap.to_dict()
        payload = json.dumps(d)
        self.assertIn("CLEAN_ROOM_SYNTHETIC", payload)
        self.assertEqual(d["donor_files_inspected"], 17)

    # ------------------------------------------------------------------
    # Pillar 59A State Helper & Evaluator Tests (16..50)
    # ------------------------------------------------------------------

    def _default_59a_state(self, **overrides: object) -> dict:
        kw = dict(
            camera_model=P332_FX3_MODEL_NAME,
            shooting_domain="Movie",
            movie_steadyshot="Standard",
            still_steadyshot="On",
            steadyshot_adjust="Auto",
            focal_length_mm=8,
            movie_fps=23.98,
            sq_fps=23.98,
            hdmi_raw_on=False,
            de_squeeze="Off",
            distortion_comp="Off",
            clear_image_zoom="Optical zoom only",
            still_raw_active=False,
            drive_mode_selftimer_type="None",
            selftimer_bracket="Off",
            requested_dormant_selftimer_symbols=(),
            silent_mode="Off",
            movie_hdmi_audio_active=False,
            audio_signals="On",
            reset_action="None",
        )
        kw.update(overrides)
        return compute_expected_steadyshot_selftimer_state(**kw)

    def test_16_state_59a_default_movie_standard(self) -> None:
        st = self._default_59a_state()
        self.assertEqual(st["effective_movie_steadyshot"], "Standard")
        self.assertIsNone(st["active_lockout_errno"])
        self.assertEqual(st["effective_crop_factor"], 1.0)
        self.assertIsNone(st["focal_length_errno"])

    def test_17_state_59a_movie_active_crop_and_distortion_auto(self) -> None:
        st = self._default_59a_state(movie_steadyshot="Active", distortion_comp="Off")
        self.assertEqual(st["effective_movie_steadyshot"], "Active")
        self.assertAlmostEqual(st["effective_crop_factor"], 1.104, places=3)
        self.assertEqual(st["forced_distortion_comp"], "Auto")

    def test_18_state_59a_active_lockout_movie_100p(self) -> None:
        st = self._default_59a_state(movie_steadyshot="Active", movie_fps=119.88)
        self.assertEqual(st["effective_movie_steadyshot"], "Standard")
        self.assertEqual(st["active_lockout_errno"], P332_EOPNOTSUPP_ERRNO)
        self.assertEqual(st["effective_crop_factor"], 1.0)

    def test_19_state_59a_active_lockout_sq_120fps(self) -> None:
        st = self._default_59a_state(movie_steadyshot="Active", sq_fps=120.0)
        self.assertEqual(st["effective_movie_steadyshot"], "Standard")
        self.assertEqual(st["active_lockout_errno"], P332_EOPNOTSUPP_ERRNO)

    def test_20_state_59a_active_lockout_hdmi_raw(self) -> None:
        st = self._default_59a_state(movie_steadyshot="Active", hdmi_raw_on=True)
        self.assertEqual(st["effective_movie_steadyshot"], "Standard")
        self.assertEqual(st["active_lockout_errno"], P332_EOPNOTSUPP_ERRNO)

    def test_21_state_59a_active_lockout_de_squeeze_non_off(self) -> None:
        for opt in ("1.3x", "2.0x"):
            st = self._default_59a_state(movie_steadyshot="Active", de_squeeze=opt)
            self.assertEqual(st["effective_movie_steadyshot"], "Standard")
            self.assertEqual(st["active_lockout_errno"], P332_EOPNOTSUPP_ERRNO)

    def test_22_state_59a_dormant_dynamic_active_eopnotsupp(self) -> None:
        st = self._default_59a_state(movie_steadyshot="Dynamic active")
        self.assertEqual(st["dormant_dynamic_active_errno"], P332_EOPNOTSUPP_ERRNO)
        self.assertEqual(st["effective_movie_steadyshot"], "Standard")

    def test_23_state_59a_all_47_focal_lengths_valid(self) -> None:
        for mm in P332_STEADYSHOT_47_FOCAL_LENGTHS_MM:
            st = self._default_59a_state(steadyshot_adjust="Manual", focal_length_mm=mm)
            self.assertIsNone(st["focal_length_errno"], f"mm={mm}")

    def test_24_state_59a_invalid_focal_length_einval22(self) -> None:
        for mm in (7, 42, 43, 999, 1001):
            st = self._default_59a_state(steadyshot_adjust="Manual", focal_length_mm=mm)
            self.assertEqual(st["focal_length_errno"], P332_EINVAL_ERRNO, f"mm={mm}")

    def test_25_state_59a_clear_image_zoom_lockouts_and_metering_multi(self) -> None:
        st_ok = self._default_59a_state(movie_steadyshot="Active", clear_image_zoom="Clear Image Zoom")
        self.assertIsNone(st_ok["ciz_errno"])
        self.assertTrue(st_ok["ciz_forces_metering_multi"])
        self.assertTrue(st_ok["active_ciz_crop_stacked"])
        st_raw = self._default_59a_state(
            shooting_domain="Still", still_raw_active=True, clear_image_zoom="Clear Image Zoom"
        )
        self.assertEqual(st_raw["ciz_errno"], P332_EOPNOTSUPP_ERRNO)
        st_120 = self._default_59a_state(movie_fps=100.0, clear_image_zoom="Clear Image Zoom")
        self.assertEqual(st_120["ciz_errno"], P332_EOPNOTSUPP_ERRNO)

    def test_26_state_59a_camera_settings_reset_resets_4_ibis_and_still_selftimer_preserves_audio(self) -> None:
        st = self._default_59a_state(
            shooting_domain="Still",
            movie_steadyshot="Active",
            still_steadyshot="Off",
            steadyshot_adjust="Manual",
            focal_length_mm=85,
            drive_mode_selftimer_type="Self-timer(Cont)",
            selftimer_bracket="10s",
            audio_signals="Off",
            reset_action="Camera Settings Reset",
        )
        self.assertEqual(st["post_movie_steadyshot"], "Standard")
        self.assertEqual(st["post_still_steadyshot"], "On")
        self.assertEqual(st["post_steadyshot_adjust"], "Auto")
        self.assertEqual(st["post_focal_length_mm"], 8)
        self.assertEqual(st["post_drive_mode_selftimer_type"], "None")
        self.assertEqual(st["post_selftimer_bracket"], "Off")
        self.assertEqual(st["post_audio_signals"], "Off")  # Initialize-only!

    def test_27_state_59a_initialize_resets_audio_signals_to_on(self) -> None:
        st = self._default_59a_state(audio_signals="Off", reset_action="Initialize")
        self.assertEqual(st["post_audio_signals"], "On")

    def test_28_state_59a_still_selftimer_led8_and_audio_beep(self) -> None:
        st = self._default_59a_state(
            shooting_domain="Still",
            drive_mode_selftimer_type="Self-timer(Single)",
            audio_signals="On",
        )
        self.assertTrue(st["led8_flashes"])
        self.assertTrue(st["audio_beep_audible"])
        self.assertIsNone(st["dormant_selftimer_errno"])

    def test_29_state_59a_silent_mode_mutes_audio_signals_but_keeps_led8(self) -> None:
        st = self._default_59a_state(
            shooting_domain="Still",
            drive_mode_selftimer_type="Self-timer(Cont)",
            silent_mode="On",
            audio_signals="On",
        )
        self.assertTrue(st["led8_flashes"])
        self.assertFalse(st["audio_beep_audible"])

    def test_30_state_59a_movie_selftimer_dormant_eopnotsupp(self) -> None:
        st = self._default_59a_state(
            shooting_domain="Movie",
            drive_mode_selftimer_type="Self-timer(Single)",
            requested_dormant_selftimer_symbols=("BKID_APP_setting_movie_self_timer",),
        )
        self.assertEqual(st["dormant_selftimer_errno"], P332_EOPNOTSUPP_ERRNO)
        self.assertFalse(st["led8_flashes"])

    def test_31_state_59a_fx6_zero_ibis(self) -> None:
        st = self._default_59a_state(camera_model=P332_FX6_DONOR_MODEL_NAME)
        self.assertEqual(st["effective_movie_steadyshot"], "Unsupported_Fixed")
        self.assertEqual(st["active_lockout_errno"], P332_EOPNOTSUPP_ERRNO)

    def test_32_eval_59a_default_safe_spec_passes(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec()
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P332_STATUS_VERIFIED_PILLAR_59A)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_33_eval_59a_active_50mm_distortion_auto_and_ciz_passes(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                movie_steadyshot="Active",
                steadyshot_adjust="Manual",
                focal_length_mm=50,
                clear_image_zoom="Clear Image Zoom",
                reported_effective_movie_steadyshot="Active",
                reported_effective_crop_factor=P332_ACTIVE_CROP_FACTOR_APPROX,
                reported_forced_distortion_comp="Auto",
                reported_ciz_forces_metering_multi=True,
                post_movie_steadyshot="Active",
                post_steadyshot_adjust="Manual",
                post_focal_length_mm=50,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_34_eval_59a_rejects_invalid_camera_model(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(camera_model="ILCE-7SM3")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_INVALID_PILLAR59A_SPEC)

    def test_35_eval_59a_rejects_active_under_120p_without_lockout(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                movie_steadyshot="Active",
                movie_fps=119.88,
                reported_effective_movie_steadyshot="Active",
                reported_active_lockout_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT)

    def test_36_eval_59a_rejects_active_under_desqueeze_without_lockout(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                movie_steadyshot="Active",
                de_squeeze="1.3x",
                reported_effective_movie_steadyshot="Active",
                reported_active_lockout_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT)

    def test_37_eval_59a_rejects_active_under_hdmi_raw_without_lockout(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                movie_steadyshot="Active",
                hdmi_raw_on=True,
                reported_effective_movie_steadyshot="Active",
                reported_active_lockout_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT)

    def test_38_eval_59a_rejects_dormant_dynamic_active(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                movie_steadyshot="Dynamic active",
                reported_dormant_dynamic_active_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT)

    def test_39_eval_59a_rejects_non_47_focal_length(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                focal_length_mm=42,
                reported_focal_length_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT)

    def test_40_eval_59a_rejects_46_focal_count_drift(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                reported_focal_length_steps_count=46,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT)

    def test_41_eval_59a_rejects_dormant_movie_selftimer_symbol(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                requested_dormant_selftimer_symbols=("Rec Start delay",),
                reported_dormant_selftimer_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_SELFTIMER_DORMANT_OR_LED8_AUDIO_DRIFT)

    def test_42_eval_59a_rejects_tally_conflation_with_led8(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                front_lamp_distinct_from_tally_rec=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_SELFTIMER_DORMANT_OR_LED8_AUDIO_DRIFT)

    def test_43_eval_59a_rejects_audio_signals_wiped_by_camera_reset(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                audio_signals="Off",
                reset_action="Camera Settings Reset",
                post_audio_signals="On",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_SELFTIMER_DORMANT_OR_LED8_AUDIO_DRIFT)

    def test_44_eval_59a_accepts_fx6_zero_ibis_boundary(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                camera_model=P332_FX6_DONOR_MODEL_NAME,
                fw_version=P332_FX6_DONOR_FW_VERSION,
                reported_effective_movie_steadyshot="Unsupported_Fixed",
                reported_active_lockout_errno=P332_EOPNOTSUPP_ERRNO,
                post_movie_steadyshot="Standard",
                post_still_steadyshot="On",
                post_steadyshot_adjust="Auto",
                post_focal_length_mm=8,
                post_drive_mode_selftimer_type="None",
                post_selftimer_bracket="Off",
                post_audio_signals="On",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_45_eval_59a_rejects_fx6_ibis_spoof(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                camera_model=P332_FX6_DONOR_MODEL_NAME,
                fw_version=P332_FX6_DONOR_FW_VERSION,
                reported_effective_movie_steadyshot="Unsupported_Fixed",
                reported_active_lockout_errno=P332_EOPNOTSUPP_ERRNO,
                fx6_has_ibis=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_FX6_IBIS_OR_SELFTIMER_SPOOF)

    def test_46_eval_59a_rejects_slot1_format_quick(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
                slot1_vault_mutation_bytes=4096,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_47_eval_59a_rejects_persistent_overlay_escape(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(overlay_dir="/setting/bad")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_48_eval_59a_rejects_backup_bin_h0_h3_drift(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(backup_bin_h3_sha256="f" * 64)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_49_eval_59a_allows_slot2_read_only_or_safe_audit(self) -> None:
        rep = evaluate_steadyshot_47focal_selftimer_vault(
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                requested_vault_slot=2, requested_vault_action="READ_ONLY_AUDIT"
            )
        )
        self.assertTrue(rep.passed)

    def test_50_eval_59a_still_selftimer_cont_6_combos_all_trigger_led8(self) -> None:
        for combo in P332_SELFTIMER_CONT_COMBOS:
            rep = evaluate_steadyshot_47focal_selftimer_vault(
                build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                    shooting_domain="Still",
                    drive_mode_selftimer_type="Self-timer(Cont)",
                    selftimer_cont_combo=combo,
                    reported_led8_flashes=True,
                    reported_audio_beep_audible=True,
                    post_drive_mode_selftimer_type="Self-timer(Cont)",
                )
            )
            self.assertTrue(rep.passed, f"combo={combo}: {rep.errors}")

    # ------------------------------------------------------------------
    # Pillar 59B State Helper & Evaluator Tests (51..78)
    # ------------------------------------------------------------------

    def _default_59b_state(self, **overrides: object) -> dict:
        kw = dict(
            camera_model=P332_FX3_MODEL_NAME,
            zebra_display="Off",
            zebra_level="70",
            zebra_custom1_type="Std+Range",
            zebra_custom1_std=41,
            zebra_custom1_range=2,
            zebra_custom2_type="Lower Limit",
            zebra_custom2_lower_limit=94,
            display_lut_on=False,
            peaking_display="Off",
            peaking_level="Mid",
            peaking_color="White",
            fx6_zebra_mode="Zebra1",
            fx6_peaking_color="B&W",
            streaming_enabled="Off",
            streaming_protocol="SRT",
            streaming_codec="H.265",
            srt_encryption="AES-256",
            streaming_resolution="1080p",
            streaming_fps="59.94p",
            movie_rec_during_streaming="Disable",
            internal_rec_resolution="1080p",
            ftp_transfer_func="Off",
            airplane_mode="On",
            network_transport="USB-LAN (CDC-NCM)",
            requested_fx6_dormant_streaming_symbols=(),
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="READ_ONLY_AUDIT",
            movie_rec_during_streaming_targets_slot1=False,
            make_ftp_or_stream_dir_on_slot1=False,
            reset_action="None",
        )
        kw.update(overrides)
        return compute_expected_zebra_peaking_streaming_vault_state(**kw)

    def test_51_state_59b_zebra_custom1_and_custom2_bounds(self) -> None:
        st_ok = self._default_59b_state(zebra_custom1_std=0, zebra_custom1_range=1, zebra_custom2_lower_limit=109)
        self.assertTrue(st_ok["custom1_valid"])
        self.assertTrue(st_ok["custom2_valid"])
        st_bad_std = self._default_59b_state(zebra_custom1_std=110)
        self.assertFalse(st_bad_std["custom1_valid"])
        st_bad_rng = self._default_59b_state(zebra_custom1_range=11)
        self.assertFalse(st_bad_rng["custom1_valid"])
        st_bad_ll = self._default_59b_state(zebra_custom2_lower_limit=110)
        self.assertFalse(st_bad_ll["custom2_valid"])

    def test_52_state_59b_display_lut_shifts_zebra_post_lut(self) -> None:
        st_off = self._default_59b_state(display_lut_on=False)
        st_on = self._default_59b_state(display_lut_on=True)
        self.assertFalse(st_off["zebra_measures_post_lut"])
        self.assertTrue(st_on["zebra_measures_post_lut"])

    def test_53_state_59b_zebra_peaking_initialize_only_reset(self) -> None:
        st_cam = self._default_59b_state(
            zebra_display="On",
            zebra_level="Custom1",
            peaking_display="On",
            peaking_level="High",
            peaking_color="Blue",
            reset_action="Camera Settings Reset",
        )
        self.assertEqual(st_cam["post_zebra_display"], "On")
        self.assertEqual(st_cam["post_zebra_level"], "Custom1")
        self.assertEqual(st_cam["post_peaking_display"], "On")
        self.assertEqual(st_cam["post_peaking_level"], "High")
        self.assertEqual(st_cam["post_peaking_color"], "Blue")

        st_init = self._default_59b_state(
            zebra_display="On",
            zebra_level="Custom1",
            peaking_display="On",
            peaking_level="High",
            peaking_color="Blue",
            reset_action="Initialize",
        )
        self.assertEqual(st_init["post_zebra_display"], "Off")
        self.assertEqual(st_init["post_zebra_level"], "70")
        self.assertEqual(st_init["post_peaking_display"], "Off")
        self.assertEqual(st_init["post_peaking_level"], "Mid")
        self.assertEqual(st_init["post_peaking_color"], "White")

    def test_54_state_59b_fx6_zebra_both_rejected_and_peaking_bw_supported(self) -> None:
        st_both = self._default_59b_state(camera_model=P332_FX6_DONOR_MODEL_NAME, fx6_zebra_mode="Both")
        self.assertEqual(st_both["fx6_zebra_both_errno"], P332_EOPNOTSUPP_ERRNO)
        st_bw = self._default_59b_state(camera_model=P332_FX6_DONOR_MODEL_NAME, fx6_peaking_color="B&W")
        self.assertTrue(st_bw["fx6_peaking_color_valid"])
        st_white = self._default_59b_state(camera_model=P332_FX6_DONOR_MODEL_NAME, fx6_peaking_color="White")
        self.assertFalse(st_white["fx6_peaking_color_valid"])

    def test_55_state_59b_streaming_fps_2398p_24p_eopnotsupp(self) -> None:
        for fps in P332_STREAMING_ALLOWED_FPS:
            st = self._default_59b_state(streaming_fps=fps)
            self.assertTrue(st["fps_allowed"])
            self.assertIsNone(st["streaming_fps_errno"])
        for fps in P332_STREAMING_DISALLOWED_FPS:
            st = self._default_59b_state(streaming_fps=fps)
            self.assertFalse(st["fps_allowed"])
            self.assertEqual(st["streaming_fps_errno"], P332_EOPNOTSUPP_ERRNO)

    def test_56_state_59b_streaming_protocol_codecs_and_srt_aes(self) -> None:
        self.assertTrue(self._default_59b_state(streaming_protocol="RTMP", streaming_codec="H.264")["codec_allowed"])
        self.assertFalse(self._default_59b_state(streaming_protocol="RTMP", streaming_codec="H.265")["codec_allowed"])
        self.assertFalse(self._default_59b_state(streaming_protocol="RTMPS", streaming_codec="H.265")["codec_allowed"])
        self.assertTrue(self._default_59b_state(streaming_protocol="SRT", streaming_codec="H.265", srt_encryption="AES-128")["srt_enc_allowed"])
        self.assertTrue(self._default_59b_state(streaming_protocol="SRT", streaming_codec="H.265", srt_encryption="AES-256")["srt_enc_allowed"])

    def test_57_state_59b_movie_rec_during_streaming_4k_and_2k60_lockout(self) -> None:
        st_4k = self._default_59b_state(
            streaming_resolution="4K", streaming_fps="29.97p", movie_rec_during_streaming="Enable"
        )
        self.assertTrue(st_4k["blocks_internal_4k"])
        self.assertFalse(st_4k["internal_4k_rec_allowed"])
        st_2k60 = self._default_59b_state(
            streaming_resolution="2K", streaming_fps="59.94p", movie_rec_during_streaming="Enable"
        )
        self.assertTrue(st_2k60["blocks_internal_4k"])
        self.assertFalse(st_2k60["internal_4k_rec_allowed"])
        st_2k30 = self._default_59b_state(
            streaming_resolution="2K", streaming_fps="29.97p", movie_rec_during_streaming="Enable"
        )
        self.assertFalse(st_2k30["blocks_internal_4k"])
        self.assertTrue(st_2k30["internal_4k_rec_allowed"])

    def test_58_state_59b_reset_network_set_preserves_airplane_mode_on(self) -> None:
        st = self._default_59b_state(
            streaming_enabled="On",
            movie_rec_during_streaming="Enable",
            ftp_transfer_func="On",
            airplane_mode="On",
            reset_action="Reset Network Set.",
        )
        self.assertEqual(st["post_streaming_enabled"], "Off")
        self.assertEqual(st["post_movie_rec_during_streaming"], "Disable")
        self.assertEqual(st["post_ftp_transfer_func"], "Off")
        self.assertEqual(st["post_airplane_mode"], "On")

    def test_59_state_59b_slot1_vault_erofs_blocks_streaming_rec_and_ftp_mkdir(self) -> None:
        st_rec = self._default_59b_state(
            requested_vault_slot=1,
            requested_vault_action="READ_ONLY_AUDIT",
            movie_rec_during_streaming_targets_slot1=True,
        )
        self.assertFalse(st_rec["action_allowed"])
        self.assertEqual(st_rec["firewall_errno"], "EROFS")
        st_ftp = self._default_59b_state(
            requested_vault_slot=1,
            requested_vault_action="FTP_WRITE_TARGET",
            make_ftp_or_stream_dir_on_slot1=True,
        )
        self.assertFalse(st_ftp["action_allowed"])
        self.assertEqual(st_ftp["firewall_errno"], "EROFS")

    def test_60_eval_59b_default_safe_spec_passes(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(build_default_safe_zebra_peaking_streaming_vault_spec())
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P332_STATUS_VERIFIED_PILLAR_59B)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.rf_packets_transmitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_61_eval_59b_rejects_invalid_spec_params(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(streaming_protocol="RTSP")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_INVALID_PILLAR59B_SPEC)

    def test_62_eval_59b_rejects_peaking_hdmi_leak(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(
                peaking_display="On",
                peaking_color="Red",
                reported_hdmi_zebra_or_peaking_leaked=True,
                post_peaking_display="On",
                post_peaking_color="Red",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT)

    def test_63_eval_59b_rejects_camera_reset_wiping_zebra_or_peaking(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(
                zebra_display="On",
                reset_action="Camera Settings Reset",
                post_zebra_display="Off",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT)

    def test_64_eval_59b_rejects_custom1_std_over_109(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(zebra_custom1_std=110)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT)

    def test_65_eval_59b_rejects_fx6_zebra_both_without_eopnotsupp(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(
                camera_model=P332_FX6_DONOR_MODEL_NAME,
                fw_version=P332_FX6_DONOR_FW_VERSION,
                fx6_zebra_mode="Both",
                reported_fx6_zebra_both_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT)

    def test_66_eval_59b_rejects_fx6_dormant_streaming_symbol(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(
                camera_model=P332_FX6_DONOR_MODEL_NAME,
                fw_version=P332_FX6_DONOR_FW_VERSION,
                requested_fx6_dormant_streaming_symbols=("RTMP", "SRT"),
                reported_fx6_dormant_streaming_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT)

    def test_67_eval_59b_rejects_streaming_2398p_or_24p(self) -> None:
        for fps in ("23.98p", "24p"):
            rep = evaluate_zebra_peaking_streaming_vault(
                build_default_safe_zebra_peaking_streaming_vault_spec(
                    streaming_fps=fps, reported_streaming_fps_errno=None
                )
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P332_BLOCKED_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT)

    def test_68_eval_59b_rejects_rtmp_h265_codec_mismatch(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(
                streaming_protocol="RTMP", streaming_codec="H.265"
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT)

    def test_69_eval_59b_rejects_internal_4k_rec_during_4k_stream(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(
                streaming_resolution="4K",
                streaming_fps="29.97p",
                movie_rec_during_streaming="Enable",
                internal_rec_resolution="4K",
                reported_internal_4k_rec_allowed=True,
                reported_forced_internal_rec_fps="29.97p",
                post_movie_rec_during_streaming="Enable",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT)

    def test_70_eval_59b_rejects_reset_network_clearing_airplane_mode(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(
                reset_action="Reset Network Set.",
                post_airplane_mode="Off",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT)

    def test_71_eval_59b_rejects_wifi_or_rf_packets_transmitted(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(
                airplane_mode="Off",
                post_airplane_mode="Off",
                network_transport="Wi-Fi",
                rf_packets_transmitted=4,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL)

    def test_72_eval_59b_rejects_slot1_streaming_or_ftp_write(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="FTP_WRITE_TARGET",
                movie_rec_during_streaming_targets_slot1=True,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL)

    def test_73_eval_59b_allows_slot2_streaming_rec_with_slot1_untouched(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(
                streaming_enabled="On",
                streaming_protocol="RTMPS",
                streaming_codec="H.264",
                streaming_resolution="1080p",
                streaming_fps="29.97p",
                movie_rec_during_streaming="Enable",
                internal_rec_resolution="1080p",
                reported_internal_4k_rec_allowed=True,
                reported_forced_internal_rec_fps="29.97p",
                reported_streaming_locks_out_ftp_menu_pb=True,
                post_streaming_enabled="On",
                post_movie_rec_during_streaming="Enable",
                requested_vault_slot=2,
                requested_vault_action="MOVIE_REC_DURING_STREAMING_RECORD",
                reported_vault_action_allowed=True,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_74_eval_59b_rejects_persistent_overlay_escape(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(overlay_dir="/setting/59b")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_75_eval_59b_rejects_backup_bin_h0_h3_mismatch(self) -> None:
        rep = evaluate_zebra_peaking_streaming_vault(
            build_default_safe_zebra_peaking_streaming_vault_spec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P332_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_76_eval_59b_all_4_peaking_colors_accepted(self) -> None:
        for col in P332_PEAKING_COLORS:
            rep = evaluate_zebra_peaking_streaming_vault(
                build_default_safe_zebra_peaking_streaming_vault_spec(
                    peaking_display="On",
                    peaking_color=col,
                    post_peaking_display="On",
                    post_peaking_color=col,
                )
            )
            self.assertTrue(rep.passed, f"color={col}: {rep.errors}")

    def test_77_eval_59b_all_10_zebra_levels_accepted(self) -> None:
        for lvl in P332_ZEBRA_LEVEL_OPTIONS:
            rep = evaluate_zebra_peaking_streaming_vault(
                build_default_safe_zebra_peaking_streaming_vault_spec(
                    zebra_display="On",
                    zebra_level=lvl,
                    post_zebra_display="On",
                    post_zebra_level=lvl,
                )
            )
            self.assertTrue(rep.passed, f"level={lvl}: {rep.errors}")

    def test_78_combined_single_shot_verifier_and_alias(self) -> None:
        rep1 = verify_steadyshot_47focal_selftimer_zebra_streaming_and_vault(force_clean_room=True)
        rep2 = verify_steadyshot_47focal_selftimer_zebra_streaming_vault(force_clean_room=True)
        self.assertTrue(rep1.all_passed)
        self.assertTrue(rep2.all_passed)
        self.assertEqual(rep1.donor_snapshot.donor_files_inspected, 17)
        self.assertEqual(rep1.steadyshot_selftimer_report.status, P332_STATUS_VERIFIED_PILLAR_59A)
        self.assertEqual(rep1.zebra_peaking_streaming_report.status, P332_STATUS_VERIFIED_PILLAR_59B)

    # ------------------------------------------------------------------
    # Standalone Suite, 59/59 Master, CLI & Auto-Discovery Tests (79..97)
    # ------------------------------------------------------------------

    def test_79_pillar59a_6_scenario_suite_passes(self) -> None:
        res = run_pillar59a_steadyshot_47focal_selftimer_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P332_STATUS_VERIFIED_PILLAR_59A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)

    def test_80_pillar59b_6_scenario_suite_passes(self) -> None:
        res = run_pillar59b_zebra_peaking_streaming_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P332_STATUS_VERIFIED_PILLAR_59B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)

    def test_81_standalone_suite_normal_and_clean_room(self) -> None:
        rep_norm = run_pillar59_standalone_suite()
        self.assertTrue(rep_norm.all_passed)
        self.assertEqual(rep_norm.status, P332_STATUS_VERIFIED_PILLAR59_SUITE)
        self.assertEqual(rep_norm.rf_packets_transmitted, 0)
        self.assertEqual(rep_norm.slot1_data_sector_writes, 0)

        rep_cr = run_pillar59_standalone_suite(force_clean_room=True)
        self.assertTrue(rep_cr.all_passed)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_cr.pillar_59a_steadyshot_47focal_selftimer_vault.scenarios_passed, 6)
        self.assertEqual(rep_cr.pillar_59b_zebra_peaking_streaming_vault.scenarios_passed, 6)

    def test_82_master_59pillar_recovery_normal_mode(self) -> None:
        rep = evaluate_realhw_59pillar_recovery_master()
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P332_STATUS_VERIFIED_59OF59_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 59)
        self.assertEqual(rep.pillars_passed, 59)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertEqual(rep.rf_packets_transmitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_83_master_59pillar_recovery_clean_room_mode(self) -> None:
        rep = evaluate_59pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillars_passed, 59)
        self.assertEqual(rep.fx3_steadyshot_47_focal_count, 47)
        self.assertEqual(rep.fx3_image_stabilization_item_count, 4)
        self.assertEqual(rep.fx3_selftimer_cont_combo_count, 6)
        self.assertEqual(rep.fx3_front_lamp_8_id, 8)
        self.assertFalse(rep.fx3_has_movie_self_timer)
        self.assertFalse(rep.fx6_has_ibis)
        self.assertTrue(rep.fx6_has_6axis_gyro_metadata)
        self.assertFalse(rep.fx6_has_still_self_timer)

    def test_84_verify_59pillar_recovery_suite_alias(self) -> None:
        rep = verify_59pillar_recovery_suite(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 59)
        self.assertEqual(rep.fx3_zebra_preset_count, 8)
        self.assertEqual(rep.fx3_peaking_color_count, 4)
        self.assertEqual(rep.fx3_streaming_protocol_count, 3)

    def test_85_master_59pillar_rollup_carries_p58_and_p59_metrics(self) -> None:
        rep = evaluate_realhw_59pillar_recovery_master(force_clean_room=True)
        self.assertEqual(rep.fx3_dial_customize_item_count, 5)
        self.assertEqual(rep.fx3_fn_menu_still_slots, 12)
        self.assertEqual(rep.fx3_fn_menu_movie_slots, 12)
        self.assertEqual(rep.steadyshot_47focal_or_lockout_drift_events, 0)
        self.assertEqual(rep.selftimer_dormant_or_led8_audio_drift_events, 0)
        self.assertEqual(rep.fx6_ibis_or_selftimer_spoof_events, 0)
        self.assertEqual(rep.zebra_custom_ire_or_peaking_clean_hdmi_drift_events, 0)
        self.assertEqual(rep.streaming_24p_rec_or_network_reset_drift_events, 0)
        self.assertEqual(rep.zero_rf_or_slot1_vault_bypass_events, 0)

    def test_86_fault_inject_pillar_59_fails_closed(self) -> None:
        rep = evaluate_realhw_59pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar59_steadyshot_47focal_selftimer_zebra_streaming_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 58)
        self.assertIn("pillar59_steadyshot_47focal_selftimer_zebra_streaming_vault", rep.failed_pillars)

    def test_87_fault_inject_earlier_pillar_58_propagates(self) -> None:
        rep = evaluate_realhw_59pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_58_dial_customize_mydial_fn12x2_liveview_lut_embed_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 58)
        self.assertIn("pillar_58_dial_customize_mydial_fn12x2_liveview_lut_embed_vault", rep.failed_pillars)

    def test_88_fault_inject_unknown_pillar_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_59pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_999",
            )

    def test_89_cli_verify_59pillar_recovery_json_normal_and_clean_room(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for args in (
            ["verify-59pillar-recovery", "--json"],
            ["verify-59pillar-recovery", "--force-clean-room", "--json"],
        ):
            proc = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "fx3_recovery", *args],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["pillars_passed"], 59)
            self.assertEqual(payload["pillar_count"], 59)
            self.assertLess(payload["elapsed_seconds"], P332_CONCURRENT_CEILING_SECONDS)

    def test_90_cli_verify_pillar59_aliases_and_text_output(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for subcmd in (
            "verify-pillar59-recovery",
            "verify-pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault",
        ):
            proc_txt = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "fx3_recovery", subcmd, "--force-clean-room"],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_txt.returncode, 0, proc_txt.stderr or proc_txt.stdout)
            self.assertIn("VERIFIED_PILLAR59_STEADYSHOT_47FOCAL_SELFTIMER_ZEBRA_STREAMING_VAULT", proc_txt.stdout)

            proc_json = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "fx3_recovery", subcmd, "--json"],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_json.returncode, 0, proc_json.stderr or proc_json.stdout)
            payload = json.loads(proc_json.stdout)
            self.assertTrue(payload["all_passed"])

    def test_91_cli_out_writes_master_and_standalone_reports(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        tag = f"p332_cli_out_{os.getpid()}"
        out_master_path = work_tests / f"{tag}_master"
        out_p59_path = work_tests / f"{tag}_p59"
        try:
            proc1 = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "fx3_recovery", "verify-59pillar-recovery", "--force-clean-room", "--out", str(out_master_path)],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc1.returncode, 0, proc1.stderr or proc1.stdout)
            master_report = out_master_path / "59pillar-recovery-master-report.json"
            self.assertTrue(master_report.exists())

            proc2 = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "fx3_recovery", "verify-pillar59-recovery", "--force-clean-room", "--out", str(out_p59_path)],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc2.returncode, 0, proc2.stderr or proc2.stdout)
            p59_report = out_p59_path / "pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault-report.json"
            self.assertTrue(p59_report.exists())
        finally:
            for d in (out_master_path, out_p59_path):
                if d.exists():
                    for child in d.iterdir():
                        if child.is_file() or child.is_symlink():
                            child.unlink()
                    d.rmdir()

    def test_92_cli_backward_compat_verify_58pillar_recovery(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        proc = subprocess.run(
            ["/usr/bin/python3", "-B", "-m", "fx3_recovery", "verify-58pillar-recovery", "--force-clean-room", "--json"],
            cwd=str(REPO_ROOT),
            env=env_base,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillars_passed"], 58)

    def test_93_milestone311_auto_discovery_forward_compatible_ge_59(self) -> None:
        closure_root = str(REPO_ROOT / "outputs/fx6-on-fx3-closure")
        sys.path.insert(0, closure_root)
        try:
            from fx6_closure import realhw_milestone311_master_gate as m311
        finally:
            if closure_root in sys.path:
                sys.path.remove(closure_root)
        count, fn, ids = m311._discover_highest_recovery_master()
        self.assertGreaterEqual(count, 59)
        self.assertTrue(callable(fn))
        self.assertGreaterEqual(len(ids), 59)

    def test_94_milestone324_auto_discovery_forward_compatible_ge_59(self) -> None:
        closure_root = str(REPO_ROOT / "outputs/fx6-on-fx3-closure")
        sys.path.insert(0, closure_root)
        try:
            from fx6_closure import realhw_milestone324_master_gate as m324
        finally:
            if closure_root in sys.path:
                sys.path.remove(closure_root)
        count, fn, ids = m324._discover_highest_recovery_master(fr)
        self.assertGreaterEqual(count, 59)
        self.assertTrue(callable(fn))
        self.assertGreaterEqual(len(ids), 59)

    def test_95_master_59pillar_report_to_dict_roundtrip_json(self) -> None:
        rep = evaluate_realhw_59pillar_recovery_master(force_clean_room=True)
        d = rep.to_dict()
        raw = json.dumps(d, ensure_ascii=False, sort_keys=True, allow_nan=False)
        parsed = json.loads(raw)
        self.assertEqual(parsed["pillar_count"], 59)
        self.assertEqual(parsed["pillars_passed"], 59)

    def test_96_exports_accessible_from_package_root(self) -> None:
        for sym in (
            "MASTER_59_PILLAR_COUNT",
            "MASTER_59_PILLAR_IDS",
            "MASTER_59_PILLAR_SPECS",
            "Master59PillarRecoveryReport",
            "evaluate_realhw_59pillar_recovery_master",
            "evaluate_59pillar_recovery_master",
            "verify_59pillar_recovery_suite",
            "run_pillar59_standalone_suite",
        ):
            self.assertTrue(hasattr(fr, sym), sym)

    def test_97_donorless_ci_mock_master59_and_cli_exit_zero(self) -> None:
        from contextlib import redirect_stdout
        import io
        from fx3_recovery import __main__ as cli_main
        from fx3_recovery import files as files_mod

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            for mock_roots in ((None,), (Path("/nonexistent-donor-root"),)):
                with patch.object(files_mod, "iter_donor_work_roots", return_value=mock_roots):
                    rep = evaluate_realhw_59pillar_recovery_master()
                    self.assertTrue(rep.all_passed, rep.errors)
                    self.assertEqual(rep.pillars_passed, 59)
                    self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                    buf = io.StringIO()
                    with patch.object(sys, "argv", ["fx3_recovery", "verify-59pillar-recovery", "--json"]), redirect_stdout(buf):
                        rc = cli_main.main()
                    self.assertEqual(rc, 0, buf.getvalue())
                    payload = json.loads(buf.getvalue())
                    self.assertTrue(payload["all_passed"])
                    self.assertEqual(payload["pillars_passed"], 59)
                    self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
