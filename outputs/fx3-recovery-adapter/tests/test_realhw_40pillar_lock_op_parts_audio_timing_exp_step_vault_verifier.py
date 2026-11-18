"""Phase 245 — Dual-mode unit tests for Milestone Pillar 40 (`[Lock Operation Parts]` survival across
`[Camera Settings Reset]`, `Fn` hold scope/banner, `MENU + Fn` 5s full-body lock chord vs destructive
`MENU + Delete` 2s Slot Full Format chord guard & `My Dial` temporary recall override; `[Audio Out Timing]`
`Live`/`Lip Sync` vs `[Audio signals]` Setup survival / `Silent Mode` hard lock & `[Exposure step]`
`0.3EV`/`0.5EV` vs `[Shutter Angle]` constant cine angle table immunity) and unified `40/40` Milestone
recovery master (`verify-40pillar-recovery` / `verify-lock-op-parts-audio-timing-exp-step-vault`)."""

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
from fx3_recovery import (
    realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier as p245,
)
from fx3_recovery.realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier import (
    MASTER_39_PILLAR_SPECS,
    Master39PillarRecoveryReport,
    evaluate_realhw_39pillar_recovery_master,
)
from fx3_recovery.realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_40_PILLAR_COUNT,
    MASTER_40_PILLAR_IDS,
    MASTER_40_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P245_AUDIO_OUT_TIMING_DEFAULT,
    P245_AUDIO_OUT_TIMING_MENU_PATH,
    P245_AUDIO_OUT_TIMING_MODES,
    P245_AUDIO_SIGNALS_DEFAULT,
    P245_AUDIO_SIGNALS_MENU_PATH,
    P245_BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
    P245_BLOCKED_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION,
    P245_BLOCKED_AUDIO_TIMING_OR_SIGNALS_RESET_ASYMMETRY_DRIFT,
    P245_BLOCKED_CAMSET_AUDIO_TIMING_OR_EXP_STEP_RESTORE_DRIFT,
    P245_BLOCKED_CAMSET_LOCK_OP_PARTS_RESTORE_DRIFT,
    P245_BLOCKED_DESTRUCTIVE_MENU_DELETE_FORMAT_CHORD_CONFUSION,
    P245_BLOCKED_EXPOSURE_STEP_RESET_OR_GOVERNED_TARGETS_MISMATCH,
    P245_BLOCKED_FN_HOLD_SCOPE_OR_BANNER_MISMATCH,
    P245_BLOCKED_INVALID_AUDIO_TIMING_OR_EXPOSURE_STEP_SPEC,
    P245_BLOCKED_INVALID_LOCK_OPERATION_PARTS_SPEC,
    P245_BLOCKED_LOCK_OP_PARTS_CAMERA_SETTINGS_RESET_DRIFT,
    P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH,
    P245_BLOCKED_MY_DIAL_TEMPORARY_OVERRIDE_MISMATCH,
    P245_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P245_BLOCKED_SAFETY_POLICY_VIOLATION,
    P245_BLOCKED_SHUTTER_ANGLE_EXPOSURE_STEP_COUPLED_DRIFT,
    P245_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P245_BLOCKED_UNATTENDED_TIER0_BENCH_UNLOCKED_CONTROLS,
    P245_CAMSET_FILENAMES,
    P245_CAPTURE_MODES,
    P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG,
    P245_DESTRUCTIVE_MENU_DELETE_2S_CHORD_KEYS,
    P245_DESTRUCTIVE_MENU_DELETE_CONFUSIONS,
    P245_DESTRUCTIVE_MENU_DELETE_FORMAT_HOLD_SECONDS,
    P245_DIAL_WHEEL_CONTROLS,
    P245_EXPOSURE_STEP_DEFAULT,
    P245_EXPOSURE_STEP_GOVERNED_TARGETS,
    P245_EXPOSURE_STEP_MENU_PATH,
    P245_EXPOSURE_STEP_MODES,
    P245_FN_HOLD_SCOPE_BY_MODE,
    P245_FX3_FW_VERSION,
    P245_FX3_HELPGUIDE_ID,
    P245_FX3_MODEL_ID,
    P245_FX3_MODEL_NAME,
    P245_FX3_SHUTTER_ANGLE_FW_VERSIONS,
    P245_FX3_SUPPORTED_FW_VERSIONS,
    P245_FX6_DONOR_FW_VERSION,
    P245_FX6_DONOR_MODEL_NAME,
    P245_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P245_LOCKED_OSD_MESSAGE,
    P245_LOCK_OPERATION_PARTS_DEFAULT,
    P245_LOCK_OPERATION_PARTS_MENU_PATH,
    P245_LOCK_OPERATION_PARTS_MODES,
    P245_MENU_FN_5S_CHORD_KEYS,
    P245_MENU_FN_5S_LOCKED_CONTROLS,
    P245_MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS,
    P245_PILLAR_40A_SCENARIO_IDS,
    P245_PILLAR_40B_SCENARIO_IDS,
    P245_PINNED_FX3_BACKUP_BIN_SHA256,
    P245_PINNED_FX3_LIBGPE_SO_BYTES,
    P245_PINNED_FX3_LIBGPE_SO_SHA256,
    P245_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
    P245_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
    P245_PINNED_FX6_LIBINFRAINPUT_SO_BYTES,
    P245_PINNED_FX6_LIBINFRAINPUT_SO_SHA256,
    P245_SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS,
    P245_SHUTTER_MODES,
    P245_SHUTTER_MODE_MENU_PATH,
    P245_SLOT1_VAULT_SLOT,
    P245_STATUS_FAIL_40OF40_AGGREGATOR,
    P245_STATUS_FAIL_PILLAR40_SUITE,
    P245_STATUS_VERIFIED_40OF40_AGGREGATOR,
    P245_STATUS_VERIFIED_PILLAR40_SUITE,
    P245_STATUS_VERIFIED_PILLAR_40A,
    P245_STATUS_VERIFIED_PILLAR_40B,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE245_SCHEMA,
    PHASE245_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    AudioOutTimingSignalsAndExpStepVaultSpec,
    LockOperationPartsBenchVaultSpec,
    Master40PillarRecoveryReport,
    build_default_safe_audio_timing_exp_step_vault_spec,
    build_default_safe_lock_op_parts_vault_spec,
    evaluate_40pillar_recovery_master,
    evaluate_audio_out_timing_signals_and_exp_step_vault,
    evaluate_lock_operation_parts_bench_vault,
    evaluate_realhw_40pillar_recovery_master,
    inspect_phase245_donors_readonly,
    run_pillar40_standalone_suite,
    run_pillar40a_lock_op_parts_vault_6_scenario_suite,
    run_pillar40b_audio_timing_exp_step_vault_6_scenario_suite,
    verify_40pillar_recovery_suite,
    verify_lock_op_parts_audio_timing_and_exp_step_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]

_CACHED_MASTER40_DEFAULT: Master40PillarRecoveryReport | None = None
_CACHED_MASTER40_CLEAN_ROOM: Master40PillarRecoveryReport | None = None
_CACHED_MASTER39_CLEAN_ROOM: Master39PillarRecoveryReport | None = None


def _get_cached_master40_default() -> Master40PillarRecoveryReport:
    global _CACHED_MASTER40_DEFAULT
    if _CACHED_MASTER40_DEFAULT is None:
        _CACHED_MASTER40_DEFAULT = evaluate_realhw_40pillar_recovery_master()
    return _CACHED_MASTER40_DEFAULT


def _get_cached_master40_clean_room() -> Master40PillarRecoveryReport:
    global _CACHED_MASTER40_CLEAN_ROOM
    if _CACHED_MASTER40_CLEAN_ROOM is None:
        _CACHED_MASTER40_CLEAN_ROOM = evaluate_realhw_40pillar_recovery_master(force_clean_room=True)
    return _CACHED_MASTER40_CLEAN_ROOM


def _get_cached_master39_clean_room() -> Master39PillarRecoveryReport:
    global _CACHED_MASTER39_CLEAN_ROOM
    if _CACHED_MASTER39_CLEAN_ROOM is None:
        _CACHED_MASTER39_CLEAN_ROOM = evaluate_realhw_39pillar_recovery_master(force_clean_room=True)
    return _CACHED_MASTER39_CLEAN_ROOM


def _run_inprocess_cli(*cli_args: str) -> tuple[int, str]:
    buf = io.StringIO()
    with mock.patch.object(sys, "argv", ["fx3_recovery", *cli_args]):
        with redirect_stdout(buf):
            rc = cli_main.main()
    return rc, buf.getvalue()


class TestPhase245SafetyLocksAndExports(unittest.TestCase):
    def test_01_hard_locked_safety_flags_and_counters_zero(self) -> None:
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
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(P245_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(P245_DESTRUCTIVE_MENU_DELETE_CONFUSIONS, 0)
        self.assertEqual(P245_SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_schema_version_and_fx3_fx6_identity_pins(self) -> None:
        self.assertEqual(
            PHASE245_SCHEMA,
            "realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier_v1",
        )
        self.assertEqual(PHASE245_VERSION, "1.0.0")
        self.assertEqual(P245_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P245_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P245_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P245_FX3_FW_VERSION, "7.02")
        self.assertIn("7.02", P245_FX3_SUPPORTED_FW_VERSIONS)
        self.assertIn("6.00", P245_FX3_SHUTTER_ANGLE_FW_VERSIONS)
        self.assertNotIn("5.00", P245_FX3_SHUTTER_ANGLE_FW_VERSIONS)
        self.assertEqual(P245_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P245_FX6_DONOR_FW_VERSION, "6.01")

    def test_03_master_40_pillar_specs_extend_39_cleanly(self) -> None:
        self.assertEqual(MASTER_40_PILLAR_COUNT, 40)
        self.assertEqual(len(MASTER_40_PILLAR_SPECS), 40)
        self.assertEqual(len(MASTER_40_PILLAR_IDS), 40)
        self.assertEqual(len(set(MASTER_40_PILLAR_IDS)), 40)
        self.assertEqual(MASTER_40_PILLAR_SPECS[:39], MASTER_39_PILLAR_SPECS)
        self.assertEqual([s[0] for s in MASTER_40_PILLAR_SPECS], list(range(1, 41)))
        self.assertEqual(
            MASTER_40_PILLAR_SPECS[39],
            (
                40,
                "pillar_40_lock_op_parts_audio_timing_exp_step_vault",
                "Phase 245",
                "fx3_recovery.realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier",
            ),
        )

    def test_04_wave38_menu_paths_key_chords_and_constant_angle_table(self) -> None:
        self.assertEqual(
            P245_LOCK_OPERATION_PARTS_MENU_PATH,
            ("MENU", "Setup", "Dial Customize", "Lock Operation Parts"),
        )
        self.assertEqual(P245_LOCK_OPERATION_PARTS_DEFAULT, "Off")
        self.assertEqual(
            P245_LOCK_OPERATION_PARTS_MODES,
            ("Off", "Multi-Selector Only", "Dial + Wheel", "All"),
        )
        self.assertEqual(P245_MENU_FN_5S_CHORD_KEYS, ("MENU", "Fn"))
        self.assertEqual(P245_DESTRUCTIVE_MENU_DELETE_2S_CHORD_KEYS, ("MENU", "Delete"))
        self.assertEqual(P245_MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS, 5.0)
        self.assertEqual(P245_DESTRUCTIVE_MENU_DELETE_FORMAT_HOLD_SECONDS, 2.0)
        self.assertEqual(P245_LOCKED_OSD_MESSAGE, "Locked.")
        self.assertEqual(
            P245_AUDIO_OUT_TIMING_MENU_PATH,
            ("MENU", "Shooting", "Audio Recording", "Audio Out Timing"),
        )
        self.assertEqual(P245_AUDIO_OUT_TIMING_DEFAULT, "Live")
        self.assertEqual(P245_AUDIO_OUT_TIMING_MODES, ("Live", "Lip Sync"))
        self.assertEqual(
            P245_AUDIO_SIGNALS_MENU_PATH,
            ("MENU", "Setup", "Sound Option", "Audio signals"),
        )
        self.assertEqual(P245_AUDIO_SIGNALS_DEFAULT, "On")
        self.assertEqual(
            P245_EXPOSURE_STEP_MENU_PATH,
            ("MENU", "Exposure/Color", "Exposure Comp.", "Exposure step"),
        )
        self.assertEqual(P245_EXPOSURE_STEP_DEFAULT, "0.3EV")
        self.assertEqual(P245_EXPOSURE_STEP_MODES, ("0.3EV", "0.5EV"))
        self.assertEqual(
            P245_EXPOSURE_STEP_GOVERNED_TARGETS,
            ("Shutter Speed", "Aperture", "Exposure Comp."),
        )
        self.assertEqual(P245_SHUTTER_MODES, ("Shutter Speed", "Shutter Angle"))
        self.assertEqual(P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG[0], 5.6)
        self.assertEqual(P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG[-1], 360.0)
        self.assertIn(180.0, P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG)
        self.assertEqual(len(P245_CAMSET_FILENAMES), 10)
        self.assertEqual(len(P245_PILLAR_40A_SCENARIO_IDS), 6)
        self.assertEqual(len(P245_PILLAR_40B_SCENARIO_IDS), 6)

    def test_05_package_init_exports_all_phase245_symbols_without_shadowing(self) -> None:
        self.assertIs(
            fx3_recovery.realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier,
            p245,
        )
        self.assertEqual(
            fx3_recovery.__all__.count("realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier"),
            1,
        )
        for sym in p245.__all__:
            with self.subTest(symbol=sym):
                self.assertIn(sym, fx3_recovery.__all__)
                self.assertEqual(fx3_recovery.__all__.count(sym), 1)
                self.assertTrue(hasattr(fx3_recovery, sym))

    def test_06_safety_invariant_tamper_triggers_fail_closed_errors(self) -> None:
        with mock.patch.object(p245, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            errs = p245._safety_invariant_errors()
            self.assertTrue(any("PERSISTENT_EMMC_WRITES_AUTHORIZED" in e for e in errs))
        with mock.patch.object(p245, "P245_DESTRUCTIVE_MENU_DELETE_CONFUSIONS", 1):
            errs2 = p245._safety_invariant_errors()
            self.assertTrue(any("P245_DESTRUCTIVE_MENU_DELETE_CONFUSIONS" in e for e in errs2))
        with mock.patch.object(p245, "P245_SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS", 1):
            errs3 = p245._safety_invariant_errors()
            self.assertTrue(any("P245_SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS" in e for e in errs3))


class TestPhase245DonorReadOnlyAndCleanRoomFallback(unittest.TestCase):
    def test_07_donor_inspection_force_clean_room_synthetic_parity(self) -> None:
        snap = inspect_phase245_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 10)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        for art in snap.artifacts:
            self.assertTrue(art.present)
            self.assertTrue(art.matches_pinned)
            self.assertEqual(art.read_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(len(art.digest_sha256), 64)

    def test_08_donor_inspection_env_force_clean_room_override(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase245_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 10)

    def test_09_donor_inspection_default_mode_local_or_clean_room(self) -> None:
        snap = inspect_phase245_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 10)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertLess(snap.elapsed_seconds, 2.0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
            if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
                for art in snap.artifacts:
                    self.assertEqual(art.read_mode, "O_RDONLY_NOFOLLOW_NONBLOCK")
                    self.assertTrue(art.matches_pinned, msg=art.artifact_id)

    def test_10_donor_snapshot_pins_dial_input_and_gpe_elf64_anchors(self) -> None:
        snap = inspect_phase245_donors_readonly()
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertIn("fx3_libgpe_so", by_id)
        self.assertIn("fx6_libinfradial_so", by_id)
        self.assertIn("fx6_libinfrainput_so", by_id)
        self.assertEqual(by_id["fx3_libgpe_so"].total_bytes, P245_PINNED_FX3_LIBGPE_SO_BYTES)
        self.assertEqual(by_id["fx3_libgpe_so"].digest_sha256, P245_PINNED_FX3_LIBGPE_SO_SHA256)
        self.assertEqual(by_id["fx6_libinfradial_so"].total_bytes, P245_PINNED_FX6_LIBINFRADIAL_SO_BYTES)
        self.assertEqual(by_id["fx6_libinfradial_so"].digest_sha256, P245_PINNED_FX6_LIBINFRADIAL_SO_SHA256)
        self.assertIn("set4KeyInh", by_id["fx6_libinfradial_so"].marker_summary)
        self.assertEqual(by_id["fx6_libinfrainput_so"].total_bytes, P245_PINNED_FX6_LIBINFRAINPUT_SO_BYTES)
        self.assertEqual(by_id["fx6_libinfrainput_so"].digest_sha256, P245_PINNED_FX6_LIBINFRAINPUT_SO_SHA256)
        self.assertIn("KeyConfigAlloc", by_id["fx6_libinfrainput_so"].marker_summary)

    def test_11_donor_inspection_missing_path_automatically_falls_back_to_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
            with mock.patch.object(p245, "resolve_donor_path", return_value=None):
                snap = inspect_phase245_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 10)

    def test_12_donor_open_uses_strictly_o_rdonly_without_write_flags(self) -> None:
        seen_flags: list[int] = []
        real_open = os.open

        def _spy_open(path: str, flags: int, *args: object) -> int:
            seen_flags.append(flags)
            return real_open(path, flags, *args)  # type: ignore[arg-type]

        with mock.patch.object(os, "open", side_effect=_spy_open):
            inspect_phase245_donors_readonly()
        for fl in seen_flags:
            self.assertEqual(fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)

    def test_13_elf64_aarch64_token_checker_rejects_non_elf_and_missing_tokens(self) -> None:
        ok1, msg1 = p245._check_elf64_aarch64_tokens(b"NOT_AN_ELF", (b"sym",))
        self.assertFalse(ok1)
        self.assertEqual(msg1, "NOT_ELF")
        fake_elf = bytearray(64)
        fake_elf[:4] = b"\x7fELF"
        fake_elf[4] = 2
        fake_elf[5] = 1
        fake_elf[18] = 183
        ok2, msg2 = p245._check_elf64_aarch64_tokens(bytes(fake_elf), (b"missing_symbol",))
        self.assertFalse(ok2)
        self.assertIn("MISSING_TOKENS", msg2)

    def test_14_bounded_donor_reader_handles_open_error_gracefully(self) -> None:
        with mock.patch.object(p245, "resolve_donor_path", return_value=Path("/nonexistent/fx3/donor.so")):
            ok, total_b, hdr_b, kind, sha, raw = p245._read_donor_readonly_bounded("fake/relpath.so")
        self.assertFalse(ok)
        self.assertEqual(total_b, 0)
        self.assertEqual(hdr_b, 0)
        self.assertEqual(kind, "OPEN_ERROR")
        self.assertEqual(sha, "")
        self.assertEqual(raw, b"")



class TestPillar40ALockOperationPartsAndMenuFn5sVault(unittest.TestCase):
    def test_15_default_safe_lock_op_parts_spec_passes(self) -> None:
        spec = build_default_safe_lock_op_parts_vault_spec()
        rep = evaluate_lock_operation_parts_bench_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P245_STATUS_VERIFIED_PILLAR_40A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.lock_op_parts_reset_survival_verified)
        self.assertTrue(rep.menu_fn_5s_full_body_chord_verified)
        self.assertTrue(rep.destructive_menu_delete_guard_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.destructive_menu_delete_confusions, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_16_lock_op_parts_survives_camera_settings_reset_across_all_4_modes_and_ui_alias(self) -> None:
        for mode in ("Off", "Multi-Selector Only", "Multi-Slct Only", "Dial + Wheel", "All"):
            with self.subTest(mode=mode):
                rep = evaluate_lock_operation_parts_bench_vault(
                    LockOperationPartsBenchVaultSpec(
                        pre_reset_lock_operation_parts=mode,
                        reset_action="Camera Settings Reset",
                        post_reset_lock_operation_parts=mode,
                        fn_hold_engaged=False,
                    )
                )
                self.assertTrue(rep.passed, msg=rep.errors)

    def test_17_rejects_lock_op_parts_wiped_by_camera_settings_reset(self) -> None:
        rep = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="Dial + Wheel",
                reset_action="Camera Settings Reset",
                post_reset_lock_operation_parts="Off",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_LOCK_OP_PARTS_CAMERA_SETTINGS_RESET_DRIFT)

    def test_18_initialize_resets_lock_op_parts_to_off_only(self) -> None:
        ok_rep = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="All",
                reset_action="Initialize",
                post_reset_lock_operation_parts="Off",
            )
        )
        self.assertTrue(ok_rep.passed)
        bad_rep = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="All",
                reset_action="Initialize",
                post_reset_lock_operation_parts="All",
            )
        )
        self.assertFalse(bad_rep.passed)
        self.assertEqual(bad_rep.block_code, P245_BLOCKED_LOCK_OP_PARTS_CAMERA_SETTINGS_RESET_DRIFT)

    def test_19_camset01_slot1_load_restores_lock_op_parts_and_rejects_slot2_or_drift(self) -> None:
        ok_rep = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=P245_SLOT1_VAULT_SLOT,
                camset_filename="CAMSET01.DAT",
                saved_lock_operation_parts="Multi-Selector Only",
                post_reset_lock_operation_parts="Multi-Selector Only",
            )
        )
        self.assertTrue(ok_rep.passed)

        bad_slot = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                camset_load_after_reset=True,
                camset_slot=2,
                saved_lock_operation_parts="All",
                post_reset_lock_operation_parts="All",
            )
        )
        self.assertFalse(bad_slot.passed)
        self.assertEqual(bad_slot.block_code, P245_BLOCKED_CAMSET_LOCK_OP_PARTS_RESTORE_DRIFT)

    def test_20_fn_hold_engages_exact_scope_and_locked_osd_banner(self) -> None:
        for mode, expected_controls in P245_FN_HOLD_SCOPE_BY_MODE.items():
            with self.subTest(mode=mode):
                osd = None if mode == "Off" else P245_LOCKED_OSD_MESSAGE
                rep = evaluate_lock_operation_parts_bench_vault(
                    LockOperationPartsBenchVaultSpec(
                        pre_reset_lock_operation_parts=mode,
                        reset_action="Camera Settings Reset",
                        post_reset_lock_operation_parts=mode,
                        fn_hold_engaged=True,
                        fn_hold_osd_message=osd,
                        fn_hold_locked_controls=expected_controls,
                    )
                )
                self.assertTrue(rep.passed, msg=rep.errors)

    def test_21_rejects_fn_hold_locking_when_off_or_missing_locked_banner(self) -> None:
        bad_off = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="Off",
                post_reset_lock_operation_parts="Off",
                fn_hold_engaged=True,
                fn_hold_osd_message="Locked.",
                fn_hold_locked_controls=("MULTI_SELECTOR",),
            )
        )
        self.assertFalse(bad_off.passed)
        self.assertEqual(bad_off.block_code, P245_BLOCKED_FN_HOLD_SCOPE_OR_BANNER_MISMATCH)

        bad_banner = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="All",
                post_reset_lock_operation_parts="All",
                fn_hold_engaged=True,
                fn_hold_osd_message=None,
                fn_hold_locked_controls=P245_FN_HOLD_SCOPE_BY_MODE["All"],
            )
        )
        self.assertFalse(bad_banner.passed)
        self.assertEqual(bad_banner.block_code, P245_BLOCKED_FN_HOLD_SCOPE_OR_BANNER_MISMATCH)

    def test_22_menu_fn_5s_chord_locks_all_except_shutter_and_rejects_sub_5s_or_shutter_lock(self) -> None:
        sub_5s = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                chord_keys_pressed=("MENU", "Fn"),
                chord_hold_seconds=4.5,
                menu_fn_5s_full_body_lock_engaged=True,
                unattended_tier0_dump_active=False,
            )
        )
        self.assertFalse(sub_5s.passed)
        self.assertEqual(sub_5s.block_code, P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH)

        shutter_locked = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                chord_keys_pressed=("MENU", "Fn"),
                chord_hold_seconds=5.0,
                menu_fn_5s_full_body_lock_engaged=True,
                shutter_button_remains_unlocked=False,
            )
        )
        self.assertFalse(shutter_locked.passed)
        self.assertEqual(
            shutter_locked.block_code,
            P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH,
        )

    def test_23_rejects_destructive_menu_delete_2s_format_chord_confusion(self) -> None:
        rep_chord = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                chord_keys_pressed=("MENU", "Delete"),
                chord_hold_seconds=2.0,
                menu_fn_5s_full_body_lock_engaged=False,
                menu_fn_locked_controls=(),
                unattended_tier0_dump_active=False,
            )
        )
        self.assertFalse(rep_chord.passed)
        self.assertEqual(
            rep_chord.block_code,
            P245_BLOCKED_DESTRUCTIVE_MENU_DELETE_FORMAT_CHORD_CONFUSION,
        )
        self.assertGreaterEqual(rep_chord.destructive_menu_delete_confusions, 1)

    def test_24_rejects_unattended_tier0_bench_dump_with_unlocked_controls(self) -> None:
        rep = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="Off",
                post_reset_lock_operation_parts="Off",
                fn_hold_engaged=False,
                chord_keys_pressed=(),
                chord_hold_seconds=0.0,
                menu_fn_5s_full_body_lock_engaged=False,
                menu_fn_locked_controls=(),
                unattended_tier0_dump_active=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_UNATTENDED_TIER0_BENCH_UNLOCKED_CONTROLS)

    def test_25_my_dial_temporary_recall_unlocks_assigned_dials_and_relocks_after_release(self) -> None:
        ok_rep = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="Dial + Wheel",
                post_reset_lock_operation_parts="Dial + Wheel",
                fn_hold_engaged=True,
                fn_hold_osd_message="Locked.",
                fn_hold_locked_controls=P245_DIAL_WHEEL_CONTROLS,
                my_dial_recall_active=True,
                my_dial_assigned_controls=("FRONT_DIAL", "CONTROL_WHEEL"),
                effective_unlocked_controls_during_my_dial=("FRONT_DIAL", "CONTROL_WHEEL"),
                post_my_dial_release_relocked=True,
            )
        )
        self.assertTrue(ok_rep.passed)

        perm_leak = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                my_dial_recall_active=False,
                effective_unlocked_controls_during_my_dial=("FRONT_DIAL",),
                post_my_dial_release_relocked=False,
            )
        )
        self.assertFalse(perm_leak.passed)
        self.assertEqual(perm_leak.block_code, P245_BLOCKED_MY_DIAL_TEMPORARY_OVERRIDE_MISMATCH)

    def test_26_rejects_invalid_model_menu_path_or_lock_mode_spec(self) -> None:
        bad_model = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(camera_model="ZV-E1")
        )
        self.assertFalse(bad_model.passed)
        self.assertEqual(bad_model.block_code, P245_BLOCKED_INVALID_LOCK_OPERATION_PARTS_SPEC)

        bad_mode = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="Touch Only",
                post_reset_lock_operation_parts="Touch Only",
            )
        )
        self.assertFalse(bad_mode.passed)
        self.assertEqual(bad_mode.block_code, P245_BLOCKED_INVALID_LOCK_OPERATION_PARTS_SPEC)

    def test_27_rejects_persistent_overlay_escape_in_pillar40a(self) -> None:
        rep = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(overlay_dir="/setting/lock_op_parts_escape")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_28_rejects_tier0_backup_bin_h0_h3_drift_in_pillar40a(self) -> None:
        rep = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(backup_bin_h3_sha256="0" * 64)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_29_rejects_persistent_write_unlock_in_pillar40a(self) -> None:
        rep = evaluate_lock_operation_parts_bench_vault(
            LockOperationPartsBenchVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_30_pillar40a_to_dict_serializable(self) -> None:
        rep = evaluate_lock_operation_parts_bench_vault(build_default_safe_lock_op_parts_vault_spec())
        d = rep.to_dict()
        self.assertEqual(d["status"], P245_STATUS_VERIFIED_PILLAR_40A)
        self.assertEqual(json.loads(json.dumps(d))["destructive_menu_delete_confusions"], 0)

    def test_31_pillar40a_canonical_6_scenario_suite_passes_6_of_6(self) -> None:
        suite = run_pillar40a_lock_op_parts_vault_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, P245_STATUS_VERIFIED_PILLAR_40A)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in suite.scenarios), P245_PILLAR_40A_SCENARIO_IDS)


class TestPillar40BAudioTimingSignalsAndExpStepShutterAngleVault(unittest.TestCase):
    def test_32_default_safe_audio_timing_exp_step_spec_passes(self) -> None:
        spec = build_default_safe_audio_timing_exp_step_vault_spec()
        rep = evaluate_audio_out_timing_signals_and_exp_step_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P245_STATUS_VERIFIED_PILLAR_40B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.audio_timing_and_signals_reset_asymmetry_verified)
        self.assertTrue(rep.audio_out_timing_sq_and_audio_off_lockout_verified)
        self.assertTrue(rep.audio_signals_silent_mode_lock_verified)
        self.assertTrue(rep.exposure_step_reset_and_targets_verified)
        self.assertTrue(rep.shutter_angle_constant_table_immunity_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.shutter_angle_exposure_step_drift_events, 0)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_33_asymmetric_camera_settings_reset_vs_initialize_for_audio_timing_and_signals(self) -> None:
        csr_rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_audio_out_timing="Lip Sync",
                pre_reset_audio_signals="Off",
                pre_reset_exposure_step="0.5EV",
                reset_action="Camera Settings Reset",
                post_reset_audio_out_timing="Live",
                post_reset_audio_signals="Off",
                post_reset_exposure_step="0.3EV",
                effective_audio_signals="Off",
            )
        )
        self.assertTrue(csr_rep.passed)

        init_rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_audio_out_timing="Lip Sync",
                pre_reset_audio_signals="Off",
                pre_reset_exposure_step="0.5EV",
                reset_action="Initialize",
                post_reset_audio_out_timing="Live",
                post_reset_audio_signals="On",
                post_reset_exposure_step="0.3EV",
                effective_audio_signals="On",
            )
        )
        self.assertTrue(init_rep.passed)

    def test_34_rejects_audio_signals_wiped_by_camera_settings_reset(self) -> None:
        rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_audio_signals="Off",
                reset_action="Camera Settings Reset",
                post_reset_audio_signals="On",
                effective_audio_signals="On",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_AUDIO_TIMING_OR_SIGNALS_RESET_ASYMMETRY_DRIFT)

    def test_35_rejects_audio_out_timing_not_reset_to_live_on_camera_settings_reset(self) -> None:
        rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_audio_out_timing="Lip Sync",
                reset_action="Camera Settings Reset",
                post_reset_audio_out_timing="Lip Sync",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_AUDIO_TIMING_OR_SIGNALS_RESET_ASYMMETRY_DRIFT)

    def test_36_audio_out_timing_locked_out_in_sq_motion_and_audio_recording_off(self) -> None:
        ok_sq = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                capture_mode="S&Q Motion",
                audio_recording="On",
                audio_out_timing_available=False,
            )
        )
        self.assertTrue(ok_sq.passed)

        ok_aoff = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                capture_mode="Movie",
                audio_recording="Off",
                audio_out_timing_available=False,
            )
        )
        self.assertTrue(ok_aoff.passed)

        bad_sq = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                capture_mode="S&Q Motion",
                audio_recording="On",
                audio_out_timing_available=True,
            )
        )
        self.assertFalse(bad_sq.passed)
        self.assertEqual(bad_sq.block_code, P245_BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION)

    def test_37_rejects_audio_out_timing_claimed_available_when_audio_recording_off_or_still(self) -> None:
        bad_off = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                capture_mode="Movie",
                audio_recording="Off",
                audio_out_timing_available=True,
            )
        )
        self.assertFalse(bad_off.passed)
        self.assertEqual(bad_off.block_code, P245_BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION)

        bad_still = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                capture_mode="Still",
                audio_recording="On",
                audio_out_timing_available=True,
                shutter_mode="Shutter Speed",
            )
        )
        self.assertFalse(bad_still.passed)
        self.assertEqual(
            bad_still.block_code,
            P245_BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
        )

    def test_38_silent_mode_on_hard_locks_audio_signals_off_and_restores_on_exit(self) -> None:
        ok_silent = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_audio_signals="On",
                reset_action="Camera Settings Reset",
                post_reset_audio_signals="On",
                silent_mode="On",
                effective_audio_signals="Off",
                audio_signals_locked_by_silent_mode=True,
            )
        )
        self.assertTrue(ok_silent.passed)

        bad_silent = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_audio_signals="On",
                reset_action="Camera Settings Reset",
                post_reset_audio_signals="On",
                silent_mode="On",
                effective_audio_signals="On",
                audio_signals_locked_by_silent_mode=False,
            )
        )
        self.assertFalse(bad_silent.passed)
        self.assertEqual(bad_silent.block_code, P245_BLOCKED_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION)

    def test_39_exposure_step_governs_speed_aperture_comp_and_resets_to_03ev(self) -> None:
        bad_reset = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_exposure_step="0.5EV",
                reset_action="Camera Settings Reset",
                post_reset_exposure_step="0.5EV",
            )
        )
        self.assertFalse(bad_reset.passed)
        self.assertEqual(bad_reset.block_code, P245_BLOCKED_EXPOSURE_STEP_RESET_OR_GOVERNED_TARGETS_MISMATCH)

        bad_targets = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                exposure_step_governed_targets=("Shutter Speed", "Shutter Angle", "Aperture", "Exposure Comp.")
            )
        )
        self.assertFalse(bad_targets.passed)
        self.assertEqual(
            bad_targets.block_code,
            P245_BLOCKED_EXPOSURE_STEP_RESET_OR_GOVERNED_TARGETS_MISMATCH,
        )

    def test_40_shutter_angle_constant_table_immunity_across_03ev_and_05ev(self) -> None:
        for exp_step in ("0.3EV", "0.5EV"):
            for angle in P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG:
                with self.subTest(exp_step=exp_step, angle=angle):
                    rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
                        AudioOutTimingSignalsAndExpStepVaultSpec(
                            pre_reset_audio_out_timing="Live",
                            pre_reset_audio_signals="Off",
                            pre_reset_exposure_step=exp_step,
                            reset_action="NONE",
                            post_reset_audio_out_timing="Live",
                            post_reset_audio_signals="Off",
                            post_reset_exposure_step=exp_step,
                            shutter_mode="Shutter Angle",
                            shutter_angle_deg=angle,
                            active_shutter_angle_table_deg=P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG,
                            shutter_angle_affected_by_exposure_step=False,
                            shutter_angle_exposure_step_drift_events=0,
                        )
                    )
                    self.assertTrue(rep.passed, msg=rep.errors)

    def test_41_rejects_shutter_angle_table_drift_or_non_constant_angle_on_05ev(self) -> None:
        rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_audio_out_timing="Live",
                pre_reset_audio_signals="Off",
                pre_reset_exposure_step="0.5EV",
                reset_action="NONE",
                post_reset_audio_out_timing="Live",
                post_reset_audio_signals="Off",
                post_reset_exposure_step="0.5EV",
                shutter_mode="Shutter Angle",
                shutter_angle_deg=172.8,
                shutter_angle_affected_by_exposure_step=True,
                shutter_angle_exposure_step_drift_events=2,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_SHUTTER_ANGLE_EXPOSURE_STEP_COUPLED_DRIFT)
        self.assertEqual(rep.shutter_angle_exposure_step_drift_events, 2)

    def test_42_rejects_shutter_angle_mode_on_pre_600_firmware(self) -> None:
        rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                fw_version="5.00",
                shutter_mode="Shutter Angle",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_INVALID_AUDIO_TIMING_OR_EXPOSURE_STEP_SPEC)

    def test_43_camset01_slot1_restores_audio_timing_signals_exp_step_and_shutter_angle(self) -> None:
        ok_rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET10.DAT",
                saved_audio_out_timing="Lip Sync",
                saved_audio_signals="Off",
                saved_exposure_step="0.5EV",
                saved_shutter_mode="Shutter Angle",
                saved_shutter_angle_deg=172.8,
                post_reset_audio_out_timing="Lip Sync",
                post_reset_audio_signals="Off",
                post_reset_exposure_step="0.5EV",
                effective_audio_signals="Off",
                shutter_mode="Shutter Angle",
                shutter_angle_deg=172.8,
            )
        )
        self.assertTrue(ok_rep.passed)

        bad_rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(
                camset_load_after_reset=True,
                saved_exposure_step="0.5EV",
                post_reset_exposure_step="0.3EV",
            )
        )
        self.assertFalse(bad_rep.passed)
        self.assertEqual(bad_rep.block_code, P245_BLOCKED_CAMSET_AUDIO_TIMING_OR_EXP_STEP_RESTORE_DRIFT)

    def test_44_rejects_persistent_overlay_escape_in_pillar40b(self) -> None:
        rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(overlay_dir="/dev/cnflasha12")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_45_rejects_tier0_backup_bin_h0_h3_drift_in_pillar40b(self) -> None:
        rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_46_rejects_persistent_write_unlock_in_pillar40b(self) -> None:
        rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            AudioOutTimingSignalsAndExpStepVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P245_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_47_pillar40b_to_dict_serializable(self) -> None:
        rep = evaluate_audio_out_timing_signals_and_exp_step_vault(
            build_default_safe_audio_timing_exp_step_vault_spec()
        )
        d = rep.to_dict()
        self.assertEqual(d["status"], P245_STATUS_VERIFIED_PILLAR_40B)
        self.assertEqual(json.loads(json.dumps(d))["shutter_angle_exposure_step_drift_events"], 0)

    def test_48_pillar40b_canonical_6_scenario_suite_passes_6_of_6(self) -> None:
        suite = run_pillar40b_audio_timing_exp_step_vault_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, P245_STATUS_VERIFIED_PILLAR_40B)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in suite.scenarios), P245_PILLAR_40B_SCENARIO_IDS)



class TestCombinedPillar40AndMaster40PillarAggregator(unittest.TestCase):
    def test_49_combined_verifier_default_and_clean_room_pass(self) -> None:
        r_def = verify_lock_op_parts_audio_timing_and_exp_step_vault()
        self.assertTrue(r_def.all_passed)
        self.assertTrue(r_def.passed)
        self.assertEqual(r_def.status, P245_STATUS_VERIFIED_PILLAR40_SUITE)
        self.assertEqual(r_def.destructive_menu_delete_confusions, 0)
        self.assertEqual(r_def.shutter_angle_exposure_step_drift_events, 0)
        self.assertFalse(r_def.hardware_live_attachment_authorized)
        self.assertEqual(r_def.physical_usb_packets_emitted, 0)
        self.assertEqual(r_def.physical_device_writes, 0)
        self.assertEqual(r_def.raw_firmware_bytes_leaked, 0)

        r_cr = verify_lock_op_parts_audio_timing_and_exp_step_vault(force_clean_room=True)
        self.assertTrue(r_cr.all_passed)
        self.assertEqual(r_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_50_combined_verifier_propagates_40a_and_40b_failures(self) -> None:
        bad_40a = verify_lock_op_parts_audio_timing_and_exp_step_vault(
            lock_spec=LockOperationPartsBenchVaultSpec(
                destructive_menu_delete_attempted=True,
                destructive_menu_delete_confusions=1,
            ),
            force_clean_room=True,
        )
        self.assertFalse(bad_40a.all_passed)
        self.assertEqual(bad_40a.status, P245_STATUS_FAIL_PILLAR40_SUITE)
        self.assertEqual(bad_40a.destructive_menu_delete_confusions, 1)

        bad_40b = verify_lock_op_parts_audio_timing_and_exp_step_vault(
            audio_exp_spec=AudioOutTimingSignalsAndExpStepVaultSpec(
                shutter_angle_affected_by_exposure_step=True,
                shutter_angle_exposure_step_drift_events=1,
            ),
            force_clean_room=True,
        )
        self.assertFalse(bad_40b.all_passed)
        self.assertEqual(bad_40b.status, P245_STATUS_FAIL_PILLAR40_SUITE)
        self.assertEqual(bad_40b.shutter_angle_exposure_step_drift_events, 1)

    def test_51_standalone_pillar40_suite_dual_mode_determinism(self) -> None:
        s_def = run_pillar40_standalone_suite()
        s_cr1 = run_pillar40_standalone_suite(force_clean_room=True)
        s_cr2 = run_pillar40_standalone_suite(force_clean_room=True)
        self.assertTrue(s_def.all_passed)
        self.assertTrue(s_cr1.all_passed)
        self.assertEqual(s_cr1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(s_cr1.suite_sha256, s_cr2.suite_sha256)
        self.assertEqual(s_cr1.pillar_40a_lock_op_parts_vault.scenarios_passed, 6)
        self.assertEqual(s_cr1.pillar_40b_audio_timing_exp_step_vault.scenarios_passed, 6)
        self.assertEqual(s_cr1.destructive_menu_delete_confusions, 0)
        self.assertEqual(s_cr1.shutter_angle_exposure_step_drift_events, 0)
        self.assertFalse(s_cr1.hardware_live_attachment_authorized)

    def test_52_master_40pillar_default_mode_passes_40_of_40_under_budget(self) -> None:
        rep = _get_cached_master40_default()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P245_STATUS_VERIFIED_40OF40_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 40)
        self.assertEqual(rep.pillars_passed, 40)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertEqual(rep.destructive_menu_delete_confusions, 0)
        self.assertEqual(rep.shutter_angle_exposure_step_drift_events, 0)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertEqual(rep.unbuffered_battery_pull_events, 0)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_53_master_40pillar_clean_room_determinism(self) -> None:
        r1 = _get_cached_master40_clean_room()
        m39 = _get_cached_master39_clean_room()
        with mock.patch.object(p245, "evaluate_realhw_39pillar_recovery_master", return_value=m39):
            r2 = evaluate_realhw_40pillar_recovery_master(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.master_40pillar_sha256, r2.master_40pillar_sha256)
        self.assertEqual(len(r1.master_40pillar_sha256), 64)

    def test_54_master_40pillar_env_force_clean_room_invariants(self) -> None:
        m39 = _get_cached_master39_clean_room()
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            with mock.patch.object(p245, "evaluate_realhw_39pillar_recovery_master", return_value=m39):
                rep = evaluate_realhw_40pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 40)
        self.assertEqual(rep.pillars_passed, 40)
        self.assertEqual(rep.destructive_menu_delete_confusions, 0)
        self.assertEqual(rep.shutter_angle_exposure_step_drift_events, 0)

    def test_55_master_40pillar_symmetry_aliases(self) -> None:
        m39 = _get_cached_master39_clean_room()
        with mock.patch.object(p245, "evaluate_realhw_39pillar_recovery_master", return_value=m39):
            r_alias = evaluate_40pillar_recovery_master(force_clean_room=True)
            r_cli = verify_40pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r_alias.master_40pillar_sha256, r_cli.master_40pillar_sha256)
        self.assertEqual(r_alias.pillars_passed, 40)

    def test_56_master_40pillar_fault_injection_pillar_40(self) -> None:
        m39 = _get_cached_master39_clean_room()
        with mock.patch.object(p245, "evaluate_realhw_39pillar_recovery_master", return_value=m39):
            rep = evaluate_realhw_40pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_40_lock_op_parts_audio_timing_exp_step_vault",
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P245_STATUS_FAIL_40OF40_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 39)
        self.assertEqual(rep.failed_pillars, ("pillar_40_lock_op_parts_audio_timing_exp_step_vault",))

    def test_57_master_40pillar_fault_injection_pillar_39_and_pillar_1(self) -> None:
        m39 = _get_cached_master39_clean_room()
        first_id = MASTER_40_PILLAR_IDS[0]
        for target_id in ("pillar_39_framing_usbpower_lun_antiflicker_vault", first_id):
            with self.subTest(fault_pillar=target_id):
                with mock.patch.object(p245, "evaluate_realhw_39pillar_recovery_master", return_value=m39):
                    rep = evaluate_realhw_40pillar_recovery_master(
                        force_clean_room=True,
                        fault_inject_pillar=target_id,
                    )
                self.assertFalse(rep.all_passed)
                self.assertEqual(rep.pillars_passed, 39)
                self.assertEqual(rep.failed_pillars, (target_id,))

    def test_58_master_40pillar_unknown_fault_inject_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_40pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_59_master_40pillar_pillar40_entry_key_metrics_verified(self) -> None:
        rep = _get_cached_master40_clean_room()
        p40_entry = rep.pillars[39]
        self.assertEqual(p40_entry.pillar_number, 40)
        self.assertEqual(p40_entry.pillar_id, "pillar_40_lock_op_parts_audio_timing_exp_step_vault")
        self.assertTrue(p40_entry.passed)
        self.assertEqual(p40_entry.key_metrics["pillar_40a_lock_op_parts_vault"], "6/6")
        self.assertEqual(p40_entry.key_metrics["pillar_40b_audio_timing_exp_step_vault"], "6/6")
        self.assertEqual(p40_entry.key_metrics["destructive_menu_delete_confusions"], 0)
        self.assertEqual(p40_entry.key_metrics["shutter_angle_exposure_step_drift_events"], 0)
        self.assertIs(p40_entry.key_metrics["hardware_live_attachment_authorized"], False)
        self.assertEqual(p40_entry.key_metrics["donor_files_inspected"], 10)

    def test_60_json_serialization_roundtrip_master_and_reports(self) -> None:
        rep = _get_cached_master40_clean_room()
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["status"], P245_STATUS_VERIFIED_40OF40_AGGREGATOR)
        self.assertEqual(decoded["pillar_count"], 40)
        self.assertEqual(decoded["pillars_passed"], 40)
        p40_comb = verify_lock_op_parts_audio_timing_and_exp_step_vault(force_clean_room=True)
        self.assertTrue(json.loads(json.dumps(p40_comb.to_dict(), sort_keys=True))["all_passed"])


class TestBackwardCompatibilityAndCli(unittest.TestCase):
    def test_61_backward_compatibility_with_39pillar_master(self) -> None:
        rep39 = _get_cached_master39_clean_room()
        self.assertTrue(rep39.all_passed)
        self.assertEqual(rep39.pillar_count, 39)
        self.assertEqual(rep39.pillars_passed, 39)

    def test_62_backward_compatibility_callable_exports_22_to_39(self) -> None:
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
            (38, "evaluate_realhw_38pillar_recovery_master"),
            (39, "evaluate_realhw_39pillar_recovery_master"),
        ):
            with self.subTest(pillars=count):
                self.assertTrue(callable(getattr(fx3_recovery, attr_name)))
        rep_m = _get_cached_master40_clean_room()
        self.assertEqual([p.pillar_number for p in rep_m.pillars], list(range(1, 41)))

    def test_63_cli_verify_lock_op_parts_audio_timing_exp_step_vault_summary_and_json(self) -> None:
        rc_txt, out_txt = _run_inprocess_cli("verify-lock-op-parts-audio-timing-exp-step-vault")
        self.assertEqual(rc_txt, 0)
        self.assertIn("status=VERIFIED_PILLAR40_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_VAULT", out_txt)
        self.assertIn("pillar_40a=6/6", out_txt)
        self.assertIn("pillar_40b=6/6", out_txt)
        self.assertIn("destructive_menu_delete_confusions=0", out_txt)
        self.assertIn("shutter_angle_exposure_step_drift_events=0", out_txt)
        self.assertIn("hardware_live_attachment_authorized=False", out_txt)

        rc_js, out_js = _run_inprocess_cli("verify-lock-op-parts-audio-timing-exp-step-vault", "--json")
        self.assertEqual(rc_js, 0)
        payload = json.loads(out_js)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["schema"], PHASE245_SCHEMA)

    def test_64_cli_verify_lock_op_parts_audio_timing_exp_step_vault_force_clean_room(self) -> None:
        rc, out = _run_inprocess_cli(
            "verify-lock-op-parts-audio-timing-exp-step-vault", "--force-clean-room", "--json"
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["destructive_menu_delete_confusions"], 0)
        self.assertEqual(payload["shutter_angle_exposure_step_drift_events"], 0)
        self.assertFalse(payload["hardware_live_attachment_authorized"])

    def test_65_cli_verify_lock_op_parts_audio_timing_exp_step_vault_subprocess_smoke(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-lock-op-parts-audio-timing-exp-step-vault",
                "--json",
            ],
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
        self.assertEqual(payload["physical_usb_packets_emitted"], 0)

    def test_66_cli_verify_40pillar_recovery_summary_json_and_clean_room_forwarding(self) -> None:
        cached = _get_cached_master40_default()
        with mock.patch.object(cli_main, "verify_40pillar_recovery_suite", return_value=cached):
            rc_txt, out_txt = _run_inprocess_cli("verify-40pillar-recovery")
            self.assertEqual(rc_txt, 0)
            self.assertIn("status=VERIFIED_40OF40_PILLAR_RECOVERY_MASTER", out_txt)
            self.assertIn("pillars=40/40", out_txt)
            self.assertIn("pillar40_a=6/6", out_txt)
            self.assertIn("pillar40_b=6/6", out_txt)

            rc_js, out_js = _run_inprocess_cli("verify-40pillar-recovery", "--json")
            self.assertEqual(rc_js, 0)
            payload = json.loads(out_js)
            self.assertEqual(payload["pillar_count"], 40)
            self.assertEqual(payload["pillars_passed"], 40)

        cached_cr = _get_cached_master40_clean_room()
        with mock.patch.object(
            cli_main, "verify_40pillar_recovery_suite", return_value=cached_cr
        ) as mocked_suite:
            rc_cr, out_cr = _run_inprocess_cli("verify-40pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc_cr, 0)
        mocked_suite.assert_called_once_with(force_clean_room=True)
        self.assertEqual(json.loads(out_cr)["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_67_cli_out_creates_exclusive_directories_for_pillar40_and_40pillar_master(self) -> None:
        here = Path(__file__).resolve().parent
        out_p40 = here / f"_tmp_p245_p40_{os.getpid()}"
        rep_p40 = out_p40 / "pillar40-lock-op-parts-audio-timing-exp-step-vault-report.json"
        out_m40 = here / f"_tmp_p245_m40_{os.getpid()}"
        rep_m40 = out_m40 / "40pillar-recovery-master-report.json"
        for f, d in ((rep_p40, out_p40), (rep_m40, out_m40)):
            if f.is_file():
                f.unlink()
            if d.is_dir():
                d.rmdir()
        try:
            rc1, _ = _run_inprocess_cli(
                "verify-lock-op-parts-audio-timing-exp-step-vault",
                "--force-clean-room",
                "--out",
                str(out_p40),
            )
            self.assertEqual(rc1, 0)
            self.assertTrue(rep_p40.is_file())
            self.assertEqual(
                json.loads(rep_p40.read_text(encoding="utf-8"))["schema"],
                PHASE245_SCHEMA,
            )

            cached_cr = _get_cached_master40_clean_room()
            with mock.patch.object(cli_main, "verify_40pillar_recovery_suite", return_value=cached_cr):
                rc2, _ = _run_inprocess_cli(
                    "verify-40pillar-recovery",
                    "--force-clean-room",
                    "--out",
                    str(out_m40),
                )
            self.assertEqual(rc2, 0)
            self.assertTrue(rep_m40.is_file())
            self.assertEqual(
                json.loads(rep_m40.read_text(encoding="utf-8"))["pillar_count"],
                40,
            )
        finally:
            for f, d in ((rep_p40, out_p40), (rep_m40, out_m40)):
                if f.is_file():
                    f.unlink()
                if d.is_dir():
                    d.rmdir()

    def test_68_cli_out_refuses_preexisting_directory_overwrite_guard(self) -> None:
        here = Path(__file__).resolve().parent
        existing_dir = here / f"_tmp_p245_exist_{os.getpid()}"
        existing_dir.mkdir(exist_ok=True)
        try:
            rc, out = _run_inprocess_cli(
                "verify-lock-op-parts-audio-timing-exp-step-vault",
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
