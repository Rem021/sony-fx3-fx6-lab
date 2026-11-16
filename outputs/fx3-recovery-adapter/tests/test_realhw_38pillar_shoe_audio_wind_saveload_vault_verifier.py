"""Phase 240 — Dual-mode unit tests for Pillar 38 (`[Shoe Audio Set.]` `48kHz/24bit 4ch` recovery,
3-condition hardware lockouts, `CH1..CH4` meter coupling & `[Wind Noise Reduct.]` built-in-mic-only
post-reset `[Off]` baseline; `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` same-model lock,
8-category privacy/calibration exclusions firewall & Slot-1 Tier-0 vault write lock) and unified
`38/38` recovery master (`verify-38pillar-recovery` / `verify-shoe-audio-wind-saveload-vault`)."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import realhw_38pillar_shoe_audio_wind_saveload_vault_verifier as p240
from fx3_recovery.realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier import (
    Master37PillarRecoveryReport,
    evaluate_realhw_37pillar_recovery_master,
)
from fx3_recovery.realhw_38pillar_shoe_audio_wind_saveload_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_38_PILLAR_COUNT,
    MASTER_38_PILLAR_IDS,
    MASTER_38_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P240_AUDIO_LEVEL_DISPLAY_MODES,
    P240_AUDIO_RECORDING_MODES,
    P240_BLOCKED_C3_PORTAL_VERSION_OR_AUTH_VIOLATION,
    P240_BLOCKED_CAMSET_FILENAME_OR_10FILE_CAP_VIOLATION,
    P240_BLOCKED_CAMSET_SHOE_AUDIO_OR_WIND_RESTORE_DRIFT,
    P240_BLOCKED_CLOUD_SYNC_DURING_AIRGAP_TIER0_VAULT,
    P240_BLOCKED_CROSS_MODEL_FX6_DAT_REJECTED,
    P240_BLOCKED_INVALID_SAVELOAD_OR_CLOUD_SPEC,
    P240_BLOCKED_INVALID_SHOE_AUDIO_OR_WIND_SPEC,
    P240_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P240_BLOCKED_SAFETY_POLICY_VIOLATION,
    P240_BLOCKED_SAVELOAD_EXCLUDED_PRIVACY_OR_CAL_LEAK,
    P240_BLOCKED_SHOE_AUDIO_35MM_JACK_OVERRIDE_VIOLATION,
    P240_BLOCKED_SHOE_AUDIO_4CH_METER_COUPLING_MISMATCH,
    P240_BLOCKED_SHOE_AUDIO_OR_WIND_RESET_DRIFT,
    P240_BLOCKED_SHOE_AUDIO_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
    P240_BLOCKED_SHOE_AUDIO_XLRH1_ANALOG_SWITCH_FALLBACK_VIOLATION,
    P240_BLOCKED_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN,
    P240_BLOCKED_SLOT1_WP_LOCKED_SAVE_DENIED,
    P240_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P240_BLOCKED_WIND_NOISE_EXTERNAL_MIC_EXCLUSIVITY_VIOLATION,
    P240_BLOCKED_WIND_NOISE_INDOOR_BENCH_LOW_FREQ_ATTENUATION,
    P240_C3_PORTAL_MIN_FW_VERSION,
    P240_C3_PORTAL_SUPPORTED_FW_VERSIONS,
    P240_CAMSET_FILENAMES,
    P240_CAMSET_MAX_FILES_PER_CARD,
    P240_CAMSET_MEDIA_DIR,
    P240_CH1_CH2_METERS,
    P240_CH1_TO_CH4_METERS,
    P240_CLOUD_STORAGE_TARGETS,
    P240_DIGITAL_4CH_SHOE_ATTACHMENTS,
    P240_EXCLUDED_PRIVACY_AND_CALIBRATION_CATEGORIES,
    P240_FX3_MODEL_ID,
    P240_FX3_MODEL_NAME,
    P240_FX3_SUPPORTED_FW_VERSIONS,
    P240_FX6_DONOR_FW_VERSION,
    P240_FX6_DONOR_MODEL_NAME,
    P240_PILLAR_38A_SCENARIO_IDS,
    P240_PILLAR_38B_SCENARIO_IDS,
    P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
    P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
    P240_PINNED_FX6_APPFW_601_BYTES,
    P240_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P240_PINNED_HOTSHOE_SO_BYTES,
    P240_PINNED_HOTSHOE_SO_SHA256,
    P240_SAVE_LOAD_OPERATIONS,
    P240_SAVE_LOAD_SETTINGS_MENU_PATH,
    P240_SAVE_LOAD_STORAGE_TARGETS,
    P240_SHOE_ATTACHMENTS,
    P240_SHOE_AUDIO_SET_DEFAULT,
    P240_SHOE_AUDIO_SET_MENU_PATH,
    P240_SHOE_AUDIO_SET_MODES,
    P240_SLOT1_VAULT_SLOT,
    P240_SLOT2_SCRATCH_SLOT,
    P240_STATUS_FAIL_38OF38_AGGREGATOR,
    P240_STATUS_VERIFIED_38OF38_AGGREGATOR,
    P240_STATUS_VERIFIED_PILLAR38_SUITE,
    P240_STATUS_VERIFIED_PILLAR_38A,
    P240_STATUS_VERIFIED_PILLAR_38B,
    P240_WIND_NOISE_REDUCT_DEFAULT,
    P240_WIND_NOISE_REDUCT_MENU_PATH,
    P240_WIND_NOISE_REDUCT_MODES,
    P240_XLRH1_HARDWARE_LOW_CUT_MODES,
    P240_XLRH1_SWITCH_MODES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE240_SCHEMA,
    PHASE240_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    Master38PillarRecoveryReport,
    SaveLoadC3ExclusionsAndSlot1VaultSpec,
    ShoeAudio4chAndWindNoiseVaultSpec,
    build_default_safe_saveload_c3_vault_spec,
    build_default_safe_shoe_audio_wind_vault_spec,
    evaluate_38pillar_recovery_master,
    evaluate_realhw_38pillar_recovery_master,
    evaluate_saveload_c3_exclusions_and_slot1_vault_firewall,
    evaluate_shoe_audio_4ch_and_wind_noise_vault,
    inspect_phase240_donors_readonly,
    run_pillar38_standalone_suite,
    run_pillar38a_shoe_audio_wind_vault_6_scenario_suite,
    run_pillar38b_saveload_c3_vault_6_scenario_suite,
    verify_38pillar_recovery_suite,
    verify_shoe_audio_wind_and_saveload_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]

_CACHED_MASTER38_DEFAULT: Master38PillarRecoveryReport | None = None
_CACHED_MASTER38_CLEAN_ROOM: Master38PillarRecoveryReport | None = None
_CACHED_MASTER37_CLEAN_ROOM: Master37PillarRecoveryReport | None = None


def _get_cached_master38_default() -> Master38PillarRecoveryReport:
    global _CACHED_MASTER38_DEFAULT
    if _CACHED_MASTER38_DEFAULT is None:
        _CACHED_MASTER38_DEFAULT = evaluate_realhw_38pillar_recovery_master()
    return _CACHED_MASTER38_DEFAULT


def _get_cached_master38_clean_room() -> Master38PillarRecoveryReport:
    global _CACHED_MASTER38_CLEAN_ROOM
    if _CACHED_MASTER38_CLEAN_ROOM is None:
        _CACHED_MASTER38_CLEAN_ROOM = evaluate_realhw_38pillar_recovery_master(force_clean_room=True)
    return _CACHED_MASTER38_CLEAN_ROOM


def _get_cached_master37_clean_room() -> Master37PillarRecoveryReport:
    global _CACHED_MASTER37_CLEAN_ROOM
    if _CACHED_MASTER37_CLEAN_ROOM is None:
        _CACHED_MASTER37_CLEAN_ROOM = evaluate_realhw_37pillar_recovery_master(force_clean_room=True)
    return _CACHED_MASTER37_CLEAN_ROOM


def _run_inprocess_cli(*cli_args: str) -> tuple[int, str]:
    buf = io.StringIO()
    with mock.patch.object(sys, "argv", ["fx3_recovery", *cli_args]), redirect_stdout(buf):
        rc = cli_main.main()
    return rc, buf.getvalue().strip()


class TestPhase240SafetyAndExports(unittest.TestCase):
    def test_01_hard_locked_safety_constants(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_package_exports_and_non_shadowing(self) -> None:
        for sym in (
            "realhw_38pillar_shoe_audio_wind_saveload_vault_verifier",
            "MASTER_38_PILLAR_COUNT",
            "MASTER_38_PILLAR_IDS",
            "MASTER_38_PILLAR_SPECS",
            "PHASE240_SCHEMA",
            "PHASE240_VERSION",
            "ShoeAudio4chAndWindNoiseVaultSpec",
            "ShoeAudio4chAndWindNoiseVaultReport",
            "SaveLoadC3ExclusionsAndSlot1VaultSpec",
            "SaveLoadC3ExclusionsAndSlot1VaultReport",
            "ShoeAudioWindAndSaveLoadVaultReport",
            "Pillar38StandaloneReport",
            "Master38PillarRecoveryReport",
            "evaluate_shoe_audio_4ch_and_wind_noise_vault",
            "evaluate_saveload_c3_exclusions_and_slot1_vault_firewall",
            "verify_shoe_audio_wind_and_saveload_vault",
            "run_pillar38_standalone_suite",
            "evaluate_realhw_38pillar_recovery_master",
            "evaluate_38pillar_recovery_master",
            "verify_38pillar_recovery_suite",
            # Prior phase exports remain unshadowed:
            "MASTER_37_PILLAR_COUNT",
            "PHASE238_SCHEMA",
            "evaluate_realhw_37pillar_recovery_master",
            "MASTER_36_PILLAR_COUNT",
            "PHASE234_SCHEMA",
            "MASTER_35_PILLAR_COUNT",
            "PHASE231_SCHEMA",
        ):
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertEqual(fx3_recovery.__all__.count(sym), 1)
            self.assertTrue(hasattr(fx3_recovery, sym))
        self.assertEqual(fx3_recovery.MASTER_37_PILLAR_COUNT, 37)
        self.assertEqual(fx3_recovery.MASTER_38_PILLAR_COUNT, 38)

    def test_03_master_38_pillar_specs_registry_and_schema(self) -> None:
        self.assertEqual(PHASE240_SCHEMA, "realhw_38pillar_shoe_audio_wind_saveload_vault_verifier_v1")
        self.assertEqual(PHASE240_VERSION, "1.0.0")
        self.assertEqual(MASTER_38_PILLAR_COUNT, 38)
        self.assertEqual(len(MASTER_38_PILLAR_SPECS), 38)
        self.assertEqual(len(MASTER_38_PILLAR_IDS), 38)
        self.assertEqual(len(set(MASTER_38_PILLAR_IDS)), 38)
        self.assertEqual([spec[0] for spec in MASTER_38_PILLAR_SPECS], list(range(1, 39)))
        self.assertEqual(
            MASTER_38_PILLAR_SPECS[37],
            (
                38,
                "pillar_38_shoe_audio_wind_saveload_vault",
                "Phase 240",
                "fx3_recovery.realhw_38pillar_shoe_audio_wind_saveload_vault_verifier",
            ),
        )

    def test_04_wave36_menu_paths_modes_and_camset_constants(self) -> None:
        self.assertEqual(P240_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P240_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P240_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P240_FX6_DONOR_FW_VERSION, "6.01")
        self.assertIn("7.02", P240_FX3_SUPPORTED_FW_VERSIONS)
        self.assertEqual(P240_C3_PORTAL_MIN_FW_VERSION, "4.00")
        self.assertNotIn("3.00", P240_C3_PORTAL_SUPPORTED_FW_VERSIONS)
        self.assertIn("4.00", P240_C3_PORTAL_SUPPORTED_FW_VERSIONS)
        self.assertEqual(
            P240_SHOE_AUDIO_SET_MENU_PATH,
            ("MENU", "Shooting", "Audio Recording", "Shoe Audio Set."),
        )
        self.assertEqual(P240_SHOE_AUDIO_SET_DEFAULT, "48kHz/16bit 2ch")
        self.assertEqual(
            P240_SHOE_AUDIO_SET_MODES,
            ("48kHz/16bit 2ch", "48kHz/24bit 2ch", "48kHz/24bit 4ch"),
        )
        self.assertEqual(
            P240_WIND_NOISE_REDUCT_MENU_PATH,
            ("MENU", "Shooting", "Audio Recording", "Wind Noise Reduct."),
        )
        self.assertEqual(P240_WIND_NOISE_REDUCT_DEFAULT, "Off")
        self.assertEqual(P240_WIND_NOISE_REDUCT_MODES, ("Off", "On"))
        self.assertEqual(P240_AUDIO_RECORDING_MODES, ("On", "Off"))
        self.assertEqual(P240_AUDIO_LEVEL_DISPLAY_MODES, ("On", "Off"))
        self.assertEqual(P240_SHOE_ATTACHMENTS, ("NONE", "XLR-H1", "ECM-M1", "ANALOG_MI_MIC"))
        self.assertEqual(P240_DIGITAL_4CH_SHOE_ATTACHMENTS, ("XLR-H1", "ECM-M1"))
        self.assertEqual(P240_XLRH1_SWITCH_MODES, ("DIGITAL", "ANALOG"))
        self.assertEqual(P240_XLRH1_HARDWARE_LOW_CUT_MODES, ("Off", "100Hz", "300Hz"))
        self.assertEqual(
            P240_SAVE_LOAD_SETTINGS_MENU_PATH,
            ("MENU", "Setup", "Reset/Save Settings", "Save/Load Settings"),
        )
        self.assertEqual(P240_SAVE_LOAD_OPERATIONS, ("Load", "Save"))
        self.assertEqual(
            P240_SAVE_LOAD_STORAGE_TARGETS,
            ("Media", "Cloud(Private)", "Cloud(Share)"),
        )
        self.assertEqual(P240_CLOUD_STORAGE_TARGETS, ("Cloud(Private)", "Cloud(Share)"))
        self.assertEqual(P240_CAMSET_MEDIA_DIR, "/PRIVATE/SONY/PRO/CAMERA/ILME-FX3")
        self.assertEqual(P240_CAMSET_MAX_FILES_PER_CARD, 10)
        self.assertEqual(len(P240_CAMSET_FILENAMES), 10)
        self.assertEqual(P240_CAMSET_FILENAMES[0], "CAMSET01.DAT")
        self.assertEqual(P240_CAMSET_FILENAMES[-1], "CAMSET10.DAT")
        self.assertEqual(len(P240_EXCLUDED_PRIVACY_AND_CALIBRATION_CATEGORIES), 8)


class TestPhase240DonorInspection(unittest.TestCase):
    def test_05_donor_inspection_default_mode_under_0_15s_zero_leak(self) -> None:
        snap = inspect_phase240_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 8)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertIn("fx3_libsaveloadsettings_so", by_id)
        self.assertIn("donor_libinfrahotshoe_so", by_id)
        self.assertIn("fx6_appfw_601_so", by_id)
        self.assertEqual(
            by_id["fx3_libsaveloadsettings_so"].total_bytes,
            P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
        )
        self.assertEqual(
            by_id["fx3_libsaveloadsettings_so"].digest_sha256,
            P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
        )
        self.assertEqual(
            by_id["donor_libinfrahotshoe_so"].total_bytes,
            P240_PINNED_HOTSHOE_SO_BYTES,
        )
        self.assertEqual(
            by_id["donor_libinfrahotshoe_so"].digest_sha256,
            P240_PINNED_HOTSHOE_SO_SHA256,
        )
        self.assertEqual(
            by_id["fx6_appfw_601_so"].total_bytes,
            P240_PINNED_FX6_APPFW_601_BYTES,
        )
        self.assertEqual(
            by_id["fx6_appfw_601_so"].digest_sha256,
            P240_PINNED_FX6_APPFW_601_HDR4K_SHA256,
        )
        for art in snap.artifacts:
            self.assertTrue(art.present)
            self.assertTrue(art.matches_pinned)

    def test_06_donor_inspection_explicit_force_clean_room_parity(self) -> None:
        snap = inspect_phase240_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 8)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        for art in snap.artifacts:
            self.assertEqual(art.read_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(art.matches_pinned)

    def test_07_donor_inspection_env_var_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase240_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 8)

    def test_08_donor_inspection_missing_donor_path_auto_clean_room_fallback(self) -> None:
        with mock.patch.object(p240, "resolve_donor_path", return_value=None):
            snap = inspect_phase240_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 8)


class TestPillar38AShoeAudioAndWindNoiseVault(unittest.TestCase):
    def test_09_default_safe_shoe_audio_and_wind_noise_reset_spec_passes(self) -> None:
        spec = build_default_safe_shoe_audio_wind_vault_spec()
        rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P240_STATUS_VERIFIED_PILLAR_38A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.shoe_audio_and_wind_reset_verified)
        self.assertTrue(rep.camset_restore_verified)
        self.assertTrue(rep.shoe_audio_3lockouts_and_4ch_meters_verified)
        self.assertTrue(rep.wind_noise_builtin_mic_exclusivity_verified)
        self.assertTrue(rep.indoor_bench_wind_off_baseline_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_10_initialize_resets_shoe_audio_to_16bit_2ch_and_wind_to_off(self) -> None:
        rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                pre_reset_shoe_audio_set="48kHz/24bit 4ch",
                pre_reset_wind_noise_reduct="On",
                reset_action="Initialize",
                post_reset_shoe_audio_set="48kHz/16bit 2ch",
                post_reset_wind_noise_reduct="Off",
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.shoe_audio_and_wind_reset_verified)

    def test_11_xlrh1_digital_24bit_4ch_camset01_restore_expands_ch1_to_ch4_meters(self) -> None:
        rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="DIGITAL",
                xlrh1_hardware_low_cut="100Hz",
                reset_action="Camera Settings Reset",
                camset_load_after_reset=True,
                camset_slot=P240_SLOT1_VAULT_SLOT,
                camset_filename="CAMSET01.DAT",
                saved_shoe_audio_set="48kHz/24bit 4ch",
                saved_wind_noise_reduct="Off",
                post_reset_shoe_audio_set="48kHz/24bit 4ch",
                post_reset_wind_noise_reduct="Off",
                shoe_audio_set_available=True,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=4,
                effective_audio_bit_depth=24,
                audio_level_display="On",
                audio_level_display_meters=P240_CH1_TO_CH4_METERS,
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=False,
                indoor_bench_recovery_rehearsal=True,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.shoe_audio_3lockouts_and_4ch_meters_verified)

    def test_12_ecmm1_digital_24bit_2ch_and_16bit_2ch_render_ch1_ch2_meters(self) -> None:
        for mode, exp_bits in (("48kHz/24bit 2ch", 24), ("48kHz/16bit 2ch", 16)):
            with self.subTest(mode=mode):
                rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(
                    ShoeAudio4chAndWindNoiseVaultSpec(
                        shoe_attachment="ECM-M1",
                        xlrh1_digital_analog_switch="DIGITAL",
                        reset_action="NONE",
                        pre_reset_shoe_audio_set=mode,
                        pre_reset_wind_noise_reduct="Off",
                        post_reset_shoe_audio_set=mode,
                        post_reset_wind_noise_reduct="Off",
                        shoe_audio_set_available=True,
                        effective_audio_source="MI_SHOE_DIGITAL",
                        effective_recorded_audio_channels=2,
                        effective_audio_bit_depth=exp_bits,
                        audio_level_display="On",
                        audio_level_display_meters=P240_CH1_CH2_METERS,
                        wind_noise_reduct_available=False,
                        wind_noise_reduct_effective_dsp_active=False,
                    )
                )
                self.assertTrue(rep.passed)

    def test_13_audio_level_display_off_hides_meters_cleanly_in_digital_4ch(self) -> None:
        rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="DIGITAL",
                reset_action="NONE",
                pre_reset_shoe_audio_set="48kHz/24bit 4ch",
                pre_reset_wind_noise_reduct="Off",
                post_reset_shoe_audio_set="48kHz/24bit 4ch",
                post_reset_wind_noise_reduct="Off",
                shoe_audio_set_available=True,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=4,
                effective_audio_bit_depth=24,
                audio_level_display="Off",
                audio_level_display_meters=(),
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=False,
            )
        )
        self.assertTrue(rep.passed)

    def test_14_lockout1_audio_recording_off_disables_shoe_audio_wind_and_meters(self) -> None:
        rep_safe = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                audio_recording="Off",
                shoe_attachment="XLR-H1",
                shoe_audio_set_available=False,
                effective_audio_source="DISABLED",
                effective_recorded_audio_channels=0,
                effective_audio_bit_depth=0,
                audio_level_display_meters=(),
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=False,
            )
        )
        self.assertTrue(rep_safe.passed)

        rep_bad = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                audio_recording="Off",
                shoe_attachment="XLR-H1",
                shoe_audio_set_available=True,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=4,
                effective_audio_bit_depth=24,
                audio_level_display_meters=P240_CH1_TO_CH4_METERS,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P240_BLOCKED_SHOE_AUDIO_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION)

    def test_15_lockout1_sq_motion_disables_shoe_audio_4ch_and_audio_capture(self) -> None:
        rep_safe = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shooting_mode="S&Q Motion",
                shoe_attachment="XLR-H1",
                shoe_audio_set_available=False,
                effective_audio_source="DISABLED",
                effective_recorded_audio_channels=0,
                effective_audio_bit_depth=0,
                audio_level_display_meters=(),
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=False,
            )
        )
        self.assertTrue(rep_safe.passed)

        rep_bad = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shooting_mode="S&Q Motion",
                shoe_attachment="XLR-H1",
                shoe_audio_set_available=False,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=2,
                effective_audio_bit_depth=16,
                audio_level_display_meters=P240_CH1_CH2_METERS,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P240_BLOCKED_SHOE_AUDIO_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION)

    def test_16_lockout2_body_35mm_mic_plug_in_overrides_mi_shoe_to_2ch_16bit_analog(self) -> None:
        rep_safe = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="DIGITAL",
                body_35mm_mic_plugged_in=True,
                shoe_audio_set_available=False,
                effective_audio_source="BODY_35MM_ANALOG_MIC",
                effective_recorded_audio_channels=2,
                effective_audio_bit_depth=16,
                audio_level_display="On",
                audio_level_display_meters=P240_CH1_CH2_METERS,
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=False,
            )
        )
        self.assertTrue(rep_safe.passed)

        rep_bad = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="DIGITAL",
                body_35mm_mic_plugged_in=True,
                shoe_audio_set_available=True,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=4,
                effective_audio_bit_depth=24,
                audio_level_display_meters=P240_CH1_TO_CH4_METERS,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P240_BLOCKED_SHOE_AUDIO_35MM_JACK_OVERRIDE_VIOLATION)

    def test_17_lockout3_xlrh1_analog_switch_falls_back_to_2ch_16bit_analog(self) -> None:
        rep_safe = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="ANALOG",
                shoe_audio_set_available=False,
                effective_audio_source="MI_SHOE_ANALOG_2CH",
                effective_recorded_audio_channels=2,
                effective_audio_bit_depth=16,
                audio_level_display="On",
                audio_level_display_meters=P240_CH1_CH2_METERS,
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=False,
            )
        )
        self.assertTrue(rep_safe.passed)

        rep_bad = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="ANALOG",
                shoe_audio_set_available=True,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=4,
                effective_audio_bit_depth=24,
                audio_level_display_meters=P240_CH1_TO_CH4_METERS,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P240_BLOCKED_SHOE_AUDIO_XLRH1_ANALOG_SWITCH_FALLBACK_VIOLATION)

    def test_18_analog_mi_shoe_mic_falls_back_to_2ch_16bit_without_digital_4ch(self) -> None:
        rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="ANALOG_MI_MIC",
                shoe_audio_set_available=False,
                effective_audio_source="MI_SHOE_ANALOG_2CH",
                effective_recorded_audio_channels=2,
                effective_audio_bit_depth=16,
                audio_level_display_meters=P240_CH1_CH2_METERS,
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=False,
            )
        )
        self.assertTrue(rep.passed)

    def test_19_reject_4ch_mode_reporting_only_2ch_audio_meters(self) -> None:
        rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="DIGITAL",
                reset_action="NONE",
                pre_reset_shoe_audio_set="48kHz/24bit 4ch",
                pre_reset_wind_noise_reduct="Off",
                post_reset_shoe_audio_set="48kHz/24bit 4ch",
                post_reset_wind_noise_reduct="Off",
                shoe_audio_set_available=True,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=4,
                effective_audio_bit_depth=24,
                audio_level_display="On",
                audio_level_display_meters=P240_CH1_CH2_METERS,
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P240_BLOCKED_SHOE_AUDIO_4CH_METER_COUPLING_MISMATCH)

    def test_20_reject_shoe_audio_or_wind_noise_reset_drift_under_camera_settings_reset(self) -> None:
        rep_shoe = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                pre_reset_shoe_audio_set="48kHz/24bit 4ch",
                reset_action="Camera Settings Reset",
                post_reset_shoe_audio_set="48kHz/24bit 4ch",
            )
        )
        self.assertFalse(rep_shoe.passed)
        self.assertEqual(rep_shoe.block_code, P240_BLOCKED_SHOE_AUDIO_OR_WIND_RESET_DRIFT)

        rep_wind = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                pre_reset_wind_noise_reduct="On",
                reset_action="Camera Settings Reset",
                post_reset_wind_noise_reduct="On",
            )
        )
        self.assertFalse(rep_wind.passed)
        self.assertEqual(rep_wind.block_code, P240_BLOCKED_SHOE_AUDIO_OR_WIND_RESET_DRIFT)

    def test_21_reject_camset_load_slot_or_profile_drift_in_pillar_38a(self) -> None:
        rep_slot = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(camset_slot=2)
        )
        self.assertFalse(rep_slot.passed)
        self.assertEqual(rep_slot.block_code, P240_BLOCKED_CAMSET_SHOE_AUDIO_OR_WIND_RESTORE_DRIFT)

        rep_drift = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                camset_load_after_reset=True,
                saved_shoe_audio_set="48kHz/24bit 4ch",
                saved_wind_noise_reduct="Off",
                post_reset_shoe_audio_set="48kHz/16bit 2ch",
                post_reset_wind_noise_reduct="Off",
            )
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P240_BLOCKED_CAMSET_SHOE_AUDIO_OR_WIND_RESTORE_DRIFT)

    def test_22_reject_wind_noise_reduct_claimed_active_with_35mm_external_mic(self) -> None:
        rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                body_35mm_mic_plugged_in=True,
                shoe_audio_set_available=False,
                effective_audio_source="BODY_35MM_ANALOG_MIC",
                effective_recorded_audio_channels=2,
                effective_audio_bit_depth=16,
                audio_level_display_meters=P240_CH1_CH2_METERS,
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P240_BLOCKED_WIND_NOISE_EXTERNAL_MIC_EXCLUSIVITY_VIOLATION)

    def test_23_reject_wind_noise_reduct_claimed_active_with_xlrh1_digital_or_analog(self) -> None:
        rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="DIGITAL",
                reset_action="NONE",
                pre_reset_shoe_audio_set="48kHz/24bit 4ch",
                pre_reset_wind_noise_reduct="On",
                post_reset_shoe_audio_set="48kHz/24bit 4ch",
                post_reset_wind_noise_reduct="On",
                shoe_audio_set_available=True,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=4,
                effective_audio_bit_depth=24,
                audio_level_display_meters=P240_CH1_TO_CH4_METERS,
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=True,
                indoor_bench_recovery_rehearsal=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P240_BLOCKED_WIND_NOISE_EXTERNAL_MIC_EXCLUSIVITY_VIOLATION)

    def test_24_outdoor_builtin_mic_allows_wind_noise_on_whereas_indoor_bench_blocks_attenuation(self) -> None:
        rep_outdoor = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="NONE",
                reset_action="NONE",
                pre_reset_shoe_audio_set="48kHz/16bit 2ch",
                pre_reset_wind_noise_reduct="On",
                post_reset_shoe_audio_set="48kHz/16bit 2ch",
                post_reset_wind_noise_reduct="On",
                shoe_audio_set_available=False,
                effective_audio_source="BUILT_IN_STEREO_MIC",
                effective_recorded_audio_channels=2,
                effective_audio_bit_depth=16,
                audio_level_display_meters=P240_CH1_CH2_METERS,
                wind_noise_reduct_available=True,
                wind_noise_reduct_effective_dsp_active=True,
                indoor_bench_recovery_rehearsal=False,
                indoor_low_freq_attenuation_hazard=False,
            )
        )
        self.assertTrue(rep_outdoor.passed)

        rep_indoor = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="NONE",
                reset_action="NONE",
                pre_reset_shoe_audio_set="48kHz/16bit 2ch",
                pre_reset_wind_noise_reduct="On",
                post_reset_shoe_audio_set="48kHz/16bit 2ch",
                post_reset_wind_noise_reduct="On",
                shoe_audio_set_available=False,
                effective_audio_source="BUILT_IN_STEREO_MIC",
                effective_recorded_audio_channels=2,
                effective_audio_bit_depth=16,
                audio_level_display_meters=P240_CH1_CH2_METERS,
                wind_noise_reduct_available=True,
                wind_noise_reduct_effective_dsp_active=True,
                indoor_bench_recovery_rehearsal=True,
                indoor_low_freq_attenuation_hazard=True,
            )
        )
        self.assertFalse(rep_indoor.passed)
        self.assertEqual(rep_indoor.block_code, P240_BLOCKED_WIND_NOISE_INDOOR_BENCH_LOW_FREQ_ATTENUATION)

    def test_25_reject_invalid_spec_overlay_escape_h0_h3_drift_and_write_unlock_38a(self) -> None:
        rep_inv = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(post_reset_shoe_audio_set="96kHz/32bit 8ch")
        )
        self.assertFalse(rep_inv.passed)
        self.assertEqual(rep_inv.block_code, P240_BLOCKED_INVALID_SHOE_AUDIO_OR_WIND_SPEC)

        rep_ov = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(overlay_dir="/setting/audio_escape")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P240_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(stage_b_backup_bin_writes=1)
        )
        self.assertFalse(rep_h.passed)
        self.assertEqual(rep_h.block_code, P240_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        rep_unlock = evaluate_shoe_audio_4ch_and_wind_noise_vault(
            ShoeAudio4chAndWindNoiseVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep_unlock.passed)
        self.assertEqual(rep_unlock.block_code, P240_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_26_pillar38a_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar38a_shoe_audio_wind_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P240_STATUS_VERIFIED_PILLAR_38A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P240_PILLAR_38A_SCENARIO_IDS)


class TestPillar38BSaveLoadExclusionsAndSlot1Vault(unittest.TestCase):
    def test_27_default_safe_slot1_ordonly_camset01_load_passes(self) -> None:
        spec = build_default_safe_saveload_c3_vault_spec()
        rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P240_STATUS_VERIFIED_PILLAR_38B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.same_model_fx3_lock_verified)
        self.assertTrue(rep.media_10file_and_c3_cloud_target_verified)
        self.assertTrue(rep.excluded_items_privacy_cal_firewall_verified)
        self.assertTrue(rep.slot1_tier0_vault_write_firewall_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.excluded_secret_or_cal_leak_count, 0)
        self.assertEqual(rep.slot1_unverified_camset_save_mutations, 0)
        self.assertEqual(rep.tier0_surfaces_intact, 16)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_28_slot2_scratch_camset01_to_camset10_save_passes_with_zero_slot1_mutations(self) -> None:
        for idx, fname in ((1, "CAMSET01.DAT"), (5, "CAMSET05.DAT"), (10, "CAMSET10.DAT")):
            with self.subTest(camset=fname):
                rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
                    SaveLoadC3ExclusionsAndSlot1VaultSpec(
                        operation="Save",
                        storage_target="Media",
                        media_slot=P240_SLOT2_SCRATCH_SLOT,
                        camset_filename=fname,
                        card_camset_file_count=idx,
                        card_read_only_access=False,
                        card_sectors_mutated=4,
                        slot1_unverified_camset_save_mutations=0,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertEqual(rep.slot1_unverified_camset_save_mutations, 0)

    def test_29_c3_portal_cloud_private_and_cloud_share_ver400_plus_pass_when_not_airgap(self) -> None:
        for target in ("Cloud(Private)", "Cloud(Share)"):
            for fw in ("4.00", "7.02"):
                with self.subTest(target=target, fw=fw):
                    rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
                        SaveLoadC3ExclusionsAndSlot1VaultSpec(
                            fw_version=fw,
                            operation="Save",
                            storage_target=target,
                            c3_portal_authenticated=True,
                            airgap_tier0_vault_active=False,
                            excluded_secret_or_cal_leak_count=0,
                        )
                    )
                    self.assertTrue(rep.passed)

    def test_30_reject_c3_portal_cloud_sync_below_ver400_or_unauthenticated(self) -> None:
        rep_fw = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                fw_version="3.00",
                operation="Load",
                storage_target="Cloud(Private)",
                c3_portal_authenticated=True,
                airgap_tier0_vault_active=False,
            )
        )
        self.assertFalse(rep_fw.passed)
        self.assertEqual(rep_fw.block_code, P240_BLOCKED_C3_PORTAL_VERSION_OR_AUTH_VIOLATION)

        rep_unauth = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                fw_version="7.02",
                operation="Save",
                storage_target="Cloud(Share)",
                c3_portal_authenticated=False,
                airgap_tier0_vault_active=False,
            )
        )
        self.assertFalse(rep_unauth.passed)
        self.assertEqual(rep_unauth.block_code, P240_BLOCKED_C3_PORTAL_VERSION_OR_AUTH_VIOLATION)

    def test_31_reject_c3_portal_cloud_sync_during_active_airgap_tier0_vault_session(self) -> None:
        rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                fw_version="7.02",
                operation="Load",
                storage_target="Cloud(Private)",
                c3_portal_authenticated=True,
                airgap_tier0_vault_active=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P240_BLOCKED_CLOUD_SYNC_DURING_AIRGAP_TIER0_VAULT)

    def test_32_reject_cross_model_fx6_fx30_fx3a_and_a7sm3_dat_profiles(self) -> None:
        for foreign_model in ("ILME-FX6", "ILME-FX30", "ILME-FX3A", "ILCE-7SM3"):
            with self.subTest(foreign_model=foreign_model):
                rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
                    SaveLoadC3ExclusionsAndSlot1VaultSpec(profile_model_name=foreign_model)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P240_BLOCKED_CROSS_MODEL_FX6_DAT_REJECTED)
                self.assertFalse(rep.same_model_fx3_lock_verified)

    def test_33_reject_camset11_filename_wrong_media_dir_or_over_10_files_per_card(self) -> None:
        rep_name = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(camset_filename="CAMSET11.DAT")
        )
        self.assertFalse(rep_name.passed)
        self.assertEqual(rep_name.block_code, P240_BLOCKED_CAMSET_FILENAME_OR_10FILE_CAP_VIOLATION)

        rep_cap = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(card_camset_file_count=11)
        )
        self.assertFalse(rep_cap.passed)
        self.assertEqual(rep_cap.block_code, P240_BLOCKED_CAMSET_FILENAME_OR_10FILE_CAP_VIOLATION)

        rep_dir = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                camset_media_dir="/PRIVATE/SONY/PRO/CAMERA/ILME-FX6"
            )
        )
        self.assertFalse(rep_dir.passed)
        self.assertEqual(rep_dir.block_code, P240_BLOCKED_CAMSET_FILENAME_OR_10FILE_CAP_VIOLATION)

    def test_34_reject_iptc_or_copyright_leak_on_save_or_load(self) -> None:
        rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                iptc_or_copyright_exported_or_overwritten=True,
                leaked_excluded_categories=("IPTC_INFORMATION", "COPYRIGHT_INFO"),
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P240_BLOCKED_SAVELOAD_EXCLUDED_PRIVACY_OR_CAL_LEAK)
        self.assertGreaterEqual(rep.excluded_secret_or_cal_leak_count, 2)

    def test_35_reject_custom_wb_1_to_3_or_face_memory_biometric_overwrite(self) -> None:
        rep_wb = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(custom_wb_1_to_3_exported_or_overwritten=True)
        )
        self.assertFalse(rep_wb.passed)
        self.assertEqual(rep_wb.block_code, P240_BLOCKED_SAVELOAD_EXCLUDED_PRIVACY_OR_CAL_LEAK)

        rep_face = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(face_memory_biometrics_exported_or_overwritten=True)
        )
        self.assertFalse(rep_face.passed)
        self.assertEqual(rep_face.block_code, P240_BLOCKED_SAVELOAD_EXCLUDED_PRIVACY_OR_CAL_LEAK)

    def test_36_reject_network_ftp_rtmp_srt_wifi_tls_credentials_leak(self) -> None:
        rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                network_ftp_rtmp_srt_wifi_tls_credentials_exported_or_overwritten=True,
                leaked_excluded_categories=(
                    "FTP_TRANSFER_CREDENTIALS",
                    "STREAMING_RTMP_SRT_KEYS",
                    "WIFI_SSID_PASSPHRASE",
                    "STATIC_IP_AND_TLS_CERTS",
                ),
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P240_BLOCKED_SAVELOAD_EXCLUDED_PRIVACY_OR_CAL_LEAK)
        self.assertEqual(rep.excluded_secret_or_cal_leak_count, 4)

    def test_37_reject_slot1_save_when_sdxc_wp_switch_is_locked(self) -> None:
        rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                operation="Save",
                storage_target="Media",
                media_slot=P240_SLOT1_VAULT_SLOT,
                slot1_tier0_vault_present=True,
                slot1_sdxc_wp_switch_locked=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P240_BLOCKED_SLOT1_WP_LOCKED_SAVE_DENIED)
        self.assertEqual(rep.slot1_unverified_camset_save_mutations, 0)

    def test_38_reject_slot1_save_on_unverified_or_baseline_protected_tier0_vault_card(self) -> None:
        rep_unver = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                operation="Save",
                storage_target="Media",
                media_slot=P240_SLOT1_VAULT_SLOT,
                camset_filename="CAMSET02.DAT",
                slot1_tier0_vault_present=True,
                slot1_sdxc_wp_switch_locked=False,
                slot1_offcamera_sha256_verified=False,
                slot1_scratch_save_authorized_after_vault_verify=True,
            )
        )
        self.assertFalse(rep_unver.passed)
        self.assertEqual(rep_unver.block_code, P240_BLOCKED_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN)
        self.assertGreaterEqual(rep_unver.slot1_unverified_camset_save_mutations, 1)

        rep_camset01 = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                operation="Save",
                storage_target="Media",
                media_slot=P240_SLOT1_VAULT_SLOT,
                camset_filename="CAMSET01.DAT",
                slot1_tier0_vault_present=True,
                slot1_sdxc_wp_switch_locked=False,
                slot1_offcamera_sha256_verified=True,
                slot1_scratch_save_authorized_after_vault_verify=True,
                preserve_baseline_camset01_dat=True,
            )
        )
        self.assertFalse(rep_camset01.passed)
        self.assertEqual(rep_camset01.block_code, P240_BLOCKED_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN)

    def test_39_post_sha256_verified_slot1_scratch_save_to_camset02_allowed_only_when_authorized(self) -> None:
        rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                operation="Save",
                storage_target="Media",
                media_slot=P240_SLOT1_VAULT_SLOT,
                camset_filename="CAMSET02.DAT",
                card_camset_file_count=2,
                slot1_tier0_vault_present=True,
                slot1_sdxc_wp_switch_locked=False,
                slot1_offcamera_sha256_verified=True,
                slot1_scratch_save_authorized_after_vault_verify=True,
                preserve_baseline_camset01_dat=True,
                card_read_only_access=False,
                card_sectors_mutated=4,
            )
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.slot1_unverified_camset_save_mutations, 0)

    def test_40_reject_slot1_load_that_mutates_sectors_or_drops_ordonly_flag(self) -> None:
        rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                operation="Load",
                storage_target="Media",
                media_slot=P240_SLOT1_VAULT_SLOT,
                card_read_only_access=False,
                card_sectors_mutated=1,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P240_BLOCKED_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN)

    def test_41_reject_invalid_saveload_spec_overlay_escape_h0_h3_drift_and_write_unlock_38b(self) -> None:
        rep_inv = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(operation="DeleteAll")
        )
        self.assertFalse(rep_inv.passed)
        self.assertEqual(rep_inv.block_code, P240_BLOCKED_INVALID_SAVELOAD_OR_CLOUD_SPEC)

        rep_drift = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(action_entry_stateful_reset_drift=True)
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P240_BLOCKED_INVALID_SAVELOAD_OR_CLOUD_SPEC)

        rep_ov = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(stage_b_overlay_dir="/dev/cnflasha1")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P240_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(stage_b_backup_bin_writes=1)
        )
        self.assertFalse(rep_h.passed)
        self.assertEqual(rep_h.block_code, P240_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        rep_unlock = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
            SaveLoadC3ExclusionsAndSlot1VaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep_unlock.passed)
        self.assertEqual(rep_unlock.block_code, P240_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_42_pillar38b_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar38b_saveload_c3_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P240_STATUS_VERIFIED_PILLAR_38B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P240_PILLAR_38B_SCENARIO_IDS)


class TestCombinedVerifierAndMaster38Aggregator(unittest.TestCase):
    def test_43_combined_verifier_default_and_clean_room_modes(self) -> None:
        rep_def = verify_shoe_audio_wind_and_saveload_vault()
        rep_cr = verify_shoe_audio_wind_and_saveload_vault(force_clean_room=True)
        for rep in (rep_def, rep_cr):
            self.assertTrue(rep.all_passed)
            self.assertTrue(rep.passed)
            self.assertEqual(rep.status, P240_STATUS_VERIFIED_PILLAR38_SUITE)
            self.assertEqual(rep.excluded_secret_or_cal_leak_count, 0)
            self.assertEqual(rep.slot1_unverified_camset_save_mutations, 0)
            self.assertTrue(rep.cnflasha_userspace_write_blocked)
            self.assertEqual(rep.otp_fuse_touches, 0)
            self.assertEqual(rep.rpmb_counter_increments, 0)
            self.assertEqual(rep.passive_tx_bytes_emitted, 0)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_44_combined_verifier_propagates_38a_and_38b_failures(self) -> None:
        rep_a = verify_shoe_audio_wind_and_saveload_vault(
            shoe_audio_wind_spec=ShoeAudio4chAndWindNoiseVaultSpec(
                indoor_low_freq_attenuation_hazard=True
            ),
            force_clean_room=True,
        )
        self.assertFalse(rep_a.all_passed)
        self.assertGreaterEqual(len(rep_a.errors), 1)

        rep_b = verify_shoe_audio_wind_and_saveload_vault(
            saveload_c3_vault_spec=SaveLoadC3ExclusionsAndSlot1VaultSpec(
                profile_model_name="ILME-FX6"
            ),
            force_clean_room=True,
        )
        self.assertFalse(rep_b.all_passed)
        self.assertGreaterEqual(len(rep_b.errors), 1)

    def test_45_standalone_pillar38_suite_default_and_clean_room(self) -> None:
        rep_def = run_pillar38_standalone_suite()
        rep_cr = run_pillar38_standalone_suite(force_clean_room=True)
        for rep in (rep_def, rep_cr):
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.schema, PHASE240_SCHEMA)
            self.assertEqual(rep.version, PHASE240_VERSION)
            self.assertEqual(rep.pillar_38a_shoe_audio_wind_vault.scenarios_passed, 6)
            self.assertEqual(rep.pillar_38b_saveload_c3_exclusion_vault.scenarios_passed, 6)
            self.assertEqual(rep.excluded_secret_or_cal_leak_count, 0)
            self.assertEqual(rep.slot1_unverified_camset_save_mutations, 0)
            self.assertEqual(len(rep.suite_sha256), 64)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_46_standalone_pillar38_deterministic_sha256_in_clean_room(self) -> None:
        r1 = run_pillar38_standalone_suite(force_clean_room=True)
        r2 = run_pillar38_standalone_suite(force_clean_room=True)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)

    def test_47_master_38pillar_default_mode_38_of_38_under_6s(self) -> None:
        rep = _get_cached_master38_default()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P240_STATUS_VERIFIED_38OF38_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 38)
        self.assertEqual(rep.pillars_passed, 38)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertEqual(rep.excluded_secret_or_cal_leak_count, 0)
        self.assertEqual(rep.slot1_unverified_camset_save_mutations, 0)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_48_master_38pillar_clean_room_end_to_end_and_deterministic_sha256(self) -> None:
        r1 = _get_cached_master38_clean_room()
        m37 = _get_cached_master37_clean_room()
        with mock.patch.object(p240, "evaluate_realhw_37pillar_recovery_master", return_value=m37):
            r2 = evaluate_realhw_38pillar_recovery_master(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.pillar_count, 38)
        self.assertEqual(r1.pillars_passed, 38)
        self.assertEqual(r1.master_38pillar_sha256, r2.master_38pillar_sha256)
        self.assertEqual(len(r1.master_38pillar_sha256), 64)

    def test_49_master_38pillar_env_force_clean_room_invariants(self) -> None:
        m37 = _get_cached_master37_clean_room()
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            with mock.patch.object(p240, "evaluate_realhw_37pillar_recovery_master", return_value=m37):
                rep = evaluate_realhw_38pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 38)
        self.assertEqual(rep.pillars_passed, 38)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_50_master_38pillar_symmetry_aliases(self) -> None:
        m37 = _get_cached_master37_clean_room()
        with mock.patch.object(p240, "evaluate_realhw_37pillar_recovery_master", return_value=m37):
            r_alias = evaluate_38pillar_recovery_master(force_clean_room=True)
            r_cli = verify_38pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r_alias.master_38pillar_sha256, r_cli.master_38pillar_sha256)
        self.assertEqual(r_alias.pillars_passed, 38)

    def test_51_master_38pillar_fault_injection_pillar_38(self) -> None:
        m37 = _get_cached_master37_clean_room()
        with mock.patch.object(p240, "evaluate_realhw_37pillar_recovery_master", return_value=m37):
            rep = evaluate_realhw_38pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_38_shoe_audio_wind_saveload_vault",
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P240_STATUS_FAIL_38OF38_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 37)
        self.assertEqual(rep.failed_pillars, ("pillar_38_shoe_audio_wind_saveload_vault",))

    def test_52_master_38pillar_fault_injection_pillar_37(self) -> None:
        m37 = _get_cached_master37_clean_room()
        with mock.patch.object(p240, "evaluate_realhw_37pillar_recovery_master", return_value=m37):
            rep = evaluate_realhw_38pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_37_touch_recframe_hdmi_sunny_vault",
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 37)
        self.assertEqual(rep.failed_pillars, ("pillar_37_touch_recframe_hdmi_sunny_vault",))

    def test_53_master_38pillar_fault_injection_pillar_1(self) -> None:
        m37 = _get_cached_master37_clean_room()
        first_id = MASTER_38_PILLAR_IDS[0]
        with mock.patch.object(p240, "evaluate_realhw_37pillar_recovery_master", return_value=m37):
            rep = evaluate_realhw_38pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar=first_id,
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 37)
        self.assertEqual(rep.failed_pillars, (first_id,))

    def test_54_master_38pillar_unknown_fault_inject_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_38pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_55_master_38pillar_pillar38_entry_key_metrics_verified(self) -> None:
        rep = _get_cached_master38_clean_room()
        p38_entry = rep.pillars[37]
        self.assertEqual(p38_entry.pillar_number, 38)
        self.assertEqual(p38_entry.pillar_id, "pillar_38_shoe_audio_wind_saveload_vault")
        self.assertTrue(p38_entry.passed)
        self.assertEqual(p38_entry.key_metrics["pillar_38a_shoe_audio_wind_vault"], "6/6")
        self.assertEqual(p38_entry.key_metrics["pillar_38b_saveload_c3_exclusion_vault"], "6/6")
        self.assertEqual(p38_entry.key_metrics["excluded_secret_or_cal_leak_count"], 0)
        self.assertEqual(p38_entry.key_metrics["slot1_unverified_camset_save_mutations"], 0)
        self.assertEqual(p38_entry.key_metrics["donor_files_inspected"], 8)

    def test_56_json_serialization_roundtrip_master_and_reports(self) -> None:
        rep = _get_cached_master38_clean_room()
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["status"], P240_STATUS_VERIFIED_38OF38_AGGREGATOR)
        self.assertEqual(decoded["pillar_count"], 38)
        self.assertEqual(decoded["pillars_passed"], 38)
        p38_comb = verify_shoe_audio_wind_and_saveload_vault(force_clean_room=True)
        self.assertTrue(json.loads(json.dumps(p38_comb.to_dict(), sort_keys=True))["all_passed"])


class TestBackwardCompatibilityAndCli(unittest.TestCase):
    def test_57_backward_compatibility_with_37pillar_master(self) -> None:
        rep37 = _get_cached_master37_clean_room()
        self.assertTrue(rep37.all_passed)
        self.assertEqual(rep37.pillar_count, 37)
        self.assertEqual(rep37.pillars_passed, 37)

    def test_58_backward_compatibility_callable_exports_22_to_37(self) -> None:
        for count, attr_name in (
            (22, "evaluate_22pillar_recovery_master"),
            (24, "evaluate_24pillar_recovery_master"),
            (26, "evaluate_26pillar_recovery_master"),
            (27, "evaluate_27pillar_recovery_master"),
            (28, "evaluate_28pillar_recovery_master"),
            (29, "evaluate_29pillar_recovery_master"),
            (30, "evaluate_realhw_30pillar_recovery_master"),
            (31, "evaluate_realhw_31pillar_recovery_master"),
            (32, "evaluate_realhw_32pillar_recovery_master"),
            (33, "evaluate_realhw_33pillar_recovery_master"),
            (34, "evaluate_realhw_34pillar_recovery_master"),
            (35, "evaluate_realhw_35pillar_recovery_master"),
            (36, "evaluate_realhw_36pillar_recovery_master"),
            (37, "evaluate_realhw_37pillar_recovery_master"),
        ):
            with self.subTest(pillars=count):
                self.assertTrue(callable(getattr(fx3_recovery, attr_name)))
        rep_m = _get_cached_master38_clean_room()
        self.assertEqual([p.pillar_number for p in rep_m.pillars], list(range(1, 39)))

    def test_59_cli_verify_shoe_audio_wind_saveload_vault_summary_and_json(self) -> None:
        rc_txt, out_txt = _run_inprocess_cli("verify-shoe-audio-wind-saveload-vault")
        self.assertEqual(rc_txt, 0)
        self.assertIn("status=VERIFIED_PILLAR38_SHOE_AUDIO_WIND_SAVELOAD_VAULT", out_txt)
        self.assertIn("pillar_38a=6/6", out_txt)
        self.assertIn("pillar_38b=6/6", out_txt)
        self.assertIn("excluded_secret_or_cal_leak_count=0", out_txt)
        self.assertIn("slot1_unverified_camset_save_mutations=0", out_txt)

        rc_js, out_js = _run_inprocess_cli("verify-shoe-audio-wind-saveload-vault", "--json")
        self.assertEqual(rc_js, 0)
        payload = json.loads(out_js)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["schema"], PHASE240_SCHEMA)

    def test_60_cli_verify_shoe_audio_wind_saveload_vault_force_clean_room(self) -> None:
        rc, out = _run_inprocess_cli(
            "verify-shoe-audio-wind-saveload-vault", "--force-clean-room", "--json"
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["excluded_secret_or_cal_leak_count"], 0)
        self.assertEqual(payload["slot1_unverified_camset_save_mutations"], 0)

    def test_61_cli_verify_shoe_audio_wind_saveload_vault_subprocess_smoke(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "verify-shoe-audio-wind-saveload-vault", "--json"],
            cwd=str(ADAPTER_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(payload["physical_device_writes"], 0)

    def test_62_cli_verify_38pillar_recovery_summary_and_json_modes(self) -> None:
        cached = _get_cached_master38_default()
        with mock.patch.object(cli_main, "verify_38pillar_recovery_suite", return_value=cached):
            rc_txt, out_txt = _run_inprocess_cli("verify-38pillar-recovery")
            self.assertEqual(rc_txt, 0)
            self.assertIn("status=VERIFIED_38OF38_PILLAR_RECOVERY_MASTER", out_txt)
            self.assertIn("pillars=38/38", out_txt)
            self.assertIn("pillar38_a=6/6", out_txt)
            self.assertIn("pillar38_b=6/6", out_txt)

            rc_js, out_js = _run_inprocess_cli("verify-38pillar-recovery", "--json")
            self.assertEqual(rc_js, 0)
            payload = json.loads(out_js)
            self.assertEqual(payload["pillar_count"], 38)
            self.assertEqual(payload["pillars_passed"], 38)

    def test_63_cli_verify_38pillar_recovery_clean_room_flag_forwarding(self) -> None:
        cached_cr = _get_cached_master38_clean_room()
        with mock.patch.object(
            cli_main, "verify_38pillar_recovery_suite", return_value=cached_cr
        ) as mocked_suite:
            rc, out = _run_inprocess_cli("verify-38pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc, 0)
        mocked_suite.assert_called_once_with(force_clean_room=True)
        payload = json.loads(out)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_64_cli_out_creates_exclusive_directory_for_pillar38_report(self) -> None:
        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p240_p38_{os.getpid()}"
        report_file = out_dir / "pillar38-shoe-audio-wind-saveload-vault-report.json"
        if report_file.is_file():
            report_file.unlink()
        if out_dir.is_dir():
            out_dir.rmdir()
        try:
            rc, _ = _run_inprocess_cli(
                "verify-shoe-audio-wind-saveload-vault",
                "--force-clean-room",
                "--out",
                str(out_dir),
            )
            self.assertEqual(rc, 0)
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema"], PHASE240_SCHEMA)
        finally:
            if report_file.is_file():
                report_file.unlink()
            if out_dir.is_dir():
                out_dir.rmdir()

    def test_65_cli_out_creates_exclusive_directory_for_38pillar_master_report(self) -> None:
        cached_cr = _get_cached_master38_clean_room()
        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p240_m38_{os.getpid()}"
        report_file = out_dir / "38pillar-recovery-master-report.json"
        if report_file.is_file():
            report_file.unlink()
        if out_dir.is_dir():
            out_dir.rmdir()
        try:
            with mock.patch.object(cli_main, "verify_38pillar_recovery_suite", return_value=cached_cr):
                rc, _ = _run_inprocess_cli(
                    "verify-38pillar-recovery",
                    "--force-clean-room",
                    "--out",
                    str(out_dir),
                )
            self.assertEqual(rc, 0)
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["pillar_count"], 38)
        finally:
            if report_file.is_file():
                report_file.unlink()
            if out_dir.is_dir():
                out_dir.rmdir()

    def test_66_cli_out_refuses_preexisting_directory_overwrite_guard(self) -> None:
        here = Path(__file__).resolve().parent
        existing_dir = here / f"_tmp_p240_exist_{os.getpid()}"
        existing_dir.mkdir(exist_ok=True)
        try:
            rc, out = _run_inprocess_cli(
                "verify-shoe-audio-wind-saveload-vault",
                "--force-clean-room",
                "--out",
                str(existing_dir),
            )
            self.assertEqual(rc, 2)
            err_payload = json.loads(out)
            self.assertEqual(err_payload["status"], "REJECTED")
        finally:
            if existing_dir.is_dir():
                existing_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
