"""Phase 265 (Grand Milestone `45/45` Recovery Pillars) — Dual-mode unit tests for Pillar 45
(`[Release w/o Card]` Still-only scope vs Movie/`S&Q` internal media gate & cardless bench vs
production `[Disable]` safety; `[Release w/o Lens]` Still + Movie + `S&Q` scope with zero built-in
E-ND & zero E-mount lens UART traffic on body-only/PL/telescope bench; `Ver. 2.00+` / `Ver. 7.02`
(`ilc/2210`) exact 5-item `[Audio Recording]` menu vs `Ver. 1.x` (`ilc/2035`) `[Audio Level Display]`
spoof rejection & `DISP (Screen Disp) Set` 2ch/4ch audio meter; plus `[Copyright Info]` `<= 46`-char
printable ASCII bounds, Still-JPEG/HEIF EXIF-only scope vs XAVC/RAW movie isolation,
`[Camera Settings Reset]` string survival vs `[Initialize]` wipe, `CAMSET` excluded-items firewall,
Slot-1 Tier-0 vault write lock, and clean-room operator PII zeroing) and unified `45/45` recovery
master (`verify-45pillar-recovery` / `verify-release-wo-card-lens-audio-meter-copyright-vault`)."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import (
    realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier as p265,
)
from fx3_recovery.realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier import (
    MASTER_44_PILLAR_SPECS,
    Master44PillarRecoveryReport,
)
from fx3_recovery.realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_45_PILLAR_COUNT,
    MASTER_45_PILLAR_IDS,
    MASTER_45_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P265_AUDIO_OUT_TIMING_DEFAULT,
    P265_AUDIO_OUT_TIMING_MODES,
    P265_AUDIO_RECORDING_DEFAULT,
    P265_AUDIO_RECORDING_EXACT_5_ITEMS,
    P265_AUDIO_RECORDING_MENU_PATH,
    P265_AUDIO_RECORDING_MODES,
    P265_AUDIO_REC_LEVEL_DEFAULT,
    P265_AUDIO_REC_LEVEL_MAX,
    P265_AUDIO_REC_LEVEL_MIN,
    P265_BENCH_POSTURES,
    P265_BLOCKED_COPYRIGHT_46CHAR_OR_ASCII_OVERFLOW,
    P265_BLOCKED_COPYRIGHT_CLEAN_ROOM_PII_OR_SLOT1_VAULT_LEAK,
    P265_BLOCKED_COPYRIGHT_MOVIE_STREAM_OR_EXIF_SCOPE_VIOLATION,
    P265_BLOCKED_COPYRIGHT_RESET_VS_INITIALIZE_SCOPE_DRIFT,
    P265_BLOCKED_DISP_AUDIO_METER_OR_RESET_SCOPE_DRIFT,
    P265_BLOCKED_INVALID_COPYRIGHT_INFO_SPEC,
    P265_BLOCKED_INVALID_RELEASE_WO_OR_AUDIO_METER_SPEC,
    P265_BLOCKED_LEGACY_V1_AUDIO_MENU_SPOOF_OR_SPEC_DRIFT,
    P265_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P265_BLOCKED_RELEASE_WO_CARD_MOVIE_OR_BENCH_VIOLATION,
    P265_BLOCKED_RELEASE_WO_LENS_OR_END_UART_VIOLATION,
    P265_BLOCKED_SAFETY_POLICY_VIOLATION,
    P265_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P265_CAMSET_FILENAMES,
    P265_CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS,
    P265_COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS,
    P265_COPYRIGHT_INFO_EXACT_4_ITEMS,
    P265_COPYRIGHT_INFO_MENU_PATH,
    P265_COPYRIGHT_MAX_CHARS,
    P265_DISP_SCREEN_SET_MENU_PATH,
    P265_ENV_CLEAN_ROOM_TEST,
    P265_E_ND_ACTUATOR_TX_COUNT,
    P265_FORBIDDEN_LEGACY_V1_AUDIO_ITEM,
    P265_FORBIDDEN_LEGACY_V1_FW_VERSIONS,
    P265_FORBIDDEN_LEGACY_V1_HELPGUIDE_ID,
    P265_FX3_FW_VERSION,
    P265_FX3_HAS_BUILTIN_END_FILTER,
    P265_FX3_HELPGUIDE_ID,
    P265_FX3_MODEL_ID,
    P265_FX3_MODEL_NAME,
    P265_FX3_SUPPORTED_FW_VERSIONS,
    P265_FX6_DONOR_FW_VERSION,
    P265_FX6_DONOR_MODEL_NAME,
    P265_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P265_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS,
    P265_LENS_ATTACHMENT_KINDS,
    P265_MOVIE_STREAM_FORMATS,
    P265_PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES,
    P265_PILLAR_45A_SCENARIO_IDS,
    P265_PILLAR_45B_SCENARIO_IDS,
    P265_PINNED_FX3_APPFW_702_BYTES,
    P265_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P265_PINNED_FX3_BACKUP_BIN_BYTES,
    P265_PINNED_FX3_BACKUP_BIN_SHA256,
    P265_PINNED_FX3_BODYDATA_BYTES,
    P265_PINNED_FX3_BODYDATA_HDR4K_SHA256,
    P265_PINNED_FX3_LIBINFRAIPTC_SO_BYTES,
    P265_PINNED_FX3_LIBINFRAIPTC_SO_SHA256,
    P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
    P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
    P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
    P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
    P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
    P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256,
    P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES,
    P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256,
    P265_PINNED_FX6_APPFW_601_BYTES,
    P265_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
    P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
    P265_REC_MEDIA_DUR_HDMI_MODES,
    P265_RELEASE_WO_CARD_DEFAULT,
    P265_RELEASE_WO_CARD_MENU_PATH,
    P265_RELEASE_WO_LENS_DEFAULT,
    P265_RELEASE_WO_LENS_MENU_PATH,
    P265_RELEASE_WO_MODES,
    P265_RESET_ACTIONS,
    P265_SHOE_AUDIO_SET_DEFAULT,
    P265_SHOE_AUDIO_SET_MODES,
    P265_SHOOTING_DOMAINS,
    P265_SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES,
    P265_SLOT1_VAULT_SLOT,
    P265_STAGE_B_VOLATILE_OVERLAY_DIR,
    P265_STATUS_FAIL_45OF45_AGGREGATOR,
    P265_STATUS_FAIL_PILLAR45_SUITE,
    P265_STATUS_REJECTED_PILLAR_45A,
    P265_STATUS_REJECTED_PILLAR_45B,
    P265_STATUS_VERIFIED_45OF45_AGGREGATOR,
    P265_STATUS_VERIFIED_PILLAR45_SUITE,
    P265_STATUS_VERIFIED_PILLAR_45A,
    P265_STATUS_VERIFIED_PILLAR_45B,
    P265_STILL_IMAGE_FORMATS,
    P265_TIER0_SURFACE_COUNT,
    P265_WIND_NOISE_REDUCT_DEFAULT,
    P265_WIND_NOISE_REDUCT_MODES,
    P265_WRITE_COPYRIGHT_DEFAULT,
    P265_WRITE_COPYRIGHT_MODES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE265_MILESTONE_NUMBER,
    PHASE265_SCHEMA,
    PHASE265_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    CopyrightInfo46CharExifVaultSpec,
    Master45PillarRecoveryReport,
    ReleaseWoCardLensAndAudioMeterVaultSpec,
    build_default_safe_copyright_info_46char_exif_vault_spec,
    build_default_safe_release_wo_card_lens_audio_meter_vault_spec,
    compute_expected_copyright_info_state,
    compute_expected_disp_audio_meter_state,
    compute_expected_release_wo_card_and_lens_gate,
    evaluate_45pillar_recovery_master,
    evaluate_copyright_info_46char_exif_vault,
    evaluate_realhw_45pillar_recovery_master,
    evaluate_release_wo_card_lens_and_audio_meter_vault,
    inspect_phase265_donors_readonly,
    run_pillar45_standalone_suite,
    run_pillar45a_release_wo_card_lens_audio_meter_vault_6_scenario_suite,
    run_pillar45b_copyright_info_46char_exif_vault_6_scenario_suite,
    verify_45pillar_recovery_suite,
    verify_release_wo_card_lens_audio_meter_and_copyright_vault,
    verify_release_wo_card_lens_audio_meter_copyright_vault,
)


class TestRealHw45PillarReleaseWoCardLensAudioMeterCopyrightVaultVerifier(unittest.TestCase):
    """70 fast dual-mode tests for Phase 265 Grand Milestone `45/45` Pillar 45 & `verify-45pillar-recovery`."""

    master45_default: Master45PillarRecoveryReport
    master45_clean_room: Master45PillarRecoveryReport
    master44_clean_room: Master44PillarRecoveryReport

    @classmethod
    def setUpClass(cls) -> None:
        cls.master45_default = evaluate_realhw_45pillar_recovery_master()
        captured_m44 = []
        orig_m44 = p265.evaluate_realhw_44pillar_recovery_master

        def _spy_m44(**kwargs):
            res = orig_m44(**kwargs)
            captured_m44.append(res)
            return res

        with mock.patch.object(p265, "evaluate_realhw_44pillar_recovery_master", side_effect=_spy_m44):
            cls.master45_clean_room = evaluate_realhw_45pillar_recovery_master(force_clean_room=True)
        cls.master44_clean_room = captured_m44[0]

    # ------------------------------------------------------------------
    # 1. Safety Invariants, Schema, Package Exports & Donor Verification
    # ------------------------------------------------------------------

    def test_01_hard_locked_zero_write_and_wave43_safety_constants(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
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
        self.assertFalse(P265_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(P265_FX3_HAS_BUILTIN_END_FILTER)
        self.assertEqual(P265_E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(P265_CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS, 0)
        self.assertEqual(P265_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS, 0)
        self.assertEqual(P265_PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES, 0)
        self.assertEqual(P265_COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS, 0)
        self.assertEqual(P265_SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_schema_version_milestone_265_and_master_45_pillar_specs(self) -> None:
        self.assertEqual(
            PHASE265_SCHEMA,
            "realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier_v1",
        )
        self.assertEqual(PHASE265_VERSION, "1.0.0")
        self.assertEqual(PHASE265_MILESTONE_NUMBER, 265)
        self.assertEqual(MASTER_45_PILLAR_COUNT, 45)
        self.assertEqual(len(MASTER_45_PILLAR_SPECS), 45)
        self.assertEqual(len(MASTER_45_PILLAR_IDS), 45)
        self.assertEqual(MASTER_45_PILLAR_SPECS[:44], MASTER_44_PILLAR_SPECS)
        self.assertEqual([s[0] for s in MASTER_45_PILLAR_SPECS], list(range(1, 46)))
        self.assertEqual(
            MASTER_45_PILLAR_IDS[-1],
            "pillar_45_release_wo_card_lens_audio_meter_copyright_vault",
        )
        self.assertIn("45/45", MASTER_45_PILLAR_SPECS[-1][2])

    def test_03_package_top_level_exports_non_shadowing_and_pillars_22_to_44_intact(self) -> None:
        for sym in (
            "PHASE265_SCHEMA",
            "PHASE265_VERSION",
            "PHASE265_MILESTONE_NUMBER",
            "MASTER_45_PILLAR_COUNT",
            "MASTER_45_PILLAR_SPECS",
            "MASTER_45_PILLAR_IDS",
            "P265_RELEASE_WO_CARD_MENU_PATH",
            "P265_RELEASE_WO_LENS_MENU_PATH",
            "P265_AUDIO_RECORDING_EXACT_5_ITEMS",
            "P265_COPYRIGHT_INFO_EXACT_4_ITEMS",
            "P265_COPYRIGHT_MAX_CHARS",
            "evaluate_release_wo_card_lens_and_audio_meter_vault",
            "evaluate_copyright_info_46char_exif_vault",
            "evaluate_realhw_45pillar_recovery_master",
            "evaluate_45pillar_recovery_master",
            "verify_45pillar_recovery_suite",
            "verify_release_wo_card_lens_audio_meter_and_copyright_vault",
            "verify_release_wo_card_lens_audio_meter_copyright_vault",
            # Backward-compatibility across Pillars 22..44
            "evaluate_realhw_44pillar_recovery_master",
            "evaluate_realhw_43pillar_recovery_master",
            "evaluate_realhw_42pillar_recovery_master",
            "evaluate_realhw_35pillar_recovery_master",
            "evaluate_22pillar_recovery_master",
            "verify_22pillar_recovery_suite",
        ):
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing package export: {sym}")
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertEqual(fx3_recovery.__all__.count(sym), 1)

    def test_04_pinned_wave43_fx3_702_and_fx6_601_donor_constants(self) -> None:
        self.assertEqual(P265_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P265_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P265_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P265_FX3_FW_VERSION, "7.02")
        self.assertEqual(P265_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P265_FX6_DONOR_FW_VERSION, "6.01")
        self.assertEqual(P265_PINNED_FX3_BODYDATA_BYTES, 811876768)
        self.assertEqual(len(P265_PINNED_FX3_BODYDATA_HDR4K_SHA256), 64)
        self.assertEqual(P265_PINNED_FX3_APPFW_702_BYTES, 79015712)
        self.assertEqual(len(P265_PINNED_FX3_APPFW_702_HDR4K_SHA256), 64)
        self.assertEqual(P265_PINNED_FX6_APPFW_601_BYTES, 50520424)
        self.assertEqual(len(P265_PINNED_FX6_APPFW_601_HDR4K_SHA256), 64)
        self.assertEqual(P265_PINNED_FX3_BACKUP_BIN_BYTES, 2229740)
        self.assertEqual(
            P265_PINNED_FX3_BACKUP_BIN_SHA256,
            "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        )
        self.assertEqual(P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES, 14544)
        self.assertEqual(len(P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256), 64)
        self.assertEqual(P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES, 52312)
        self.assertEqual(len(P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256), 64)
        self.assertEqual(P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES, 98224)
        self.assertEqual(len(P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256), 64)
        self.assertEqual(P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES, 23048)
        self.assertEqual(len(P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256), 64)
        self.assertEqual(P265_PINNED_FX3_LIBINFRAIPTC_SO_BYTES, 68712)
        self.assertEqual(len(P265_PINNED_FX3_LIBINFRAIPTC_SO_SHA256), 64)
        self.assertEqual(P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES, 47808)
        self.assertEqual(len(P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256), 64)

    def test_05_donor_snapshot_default_mode_15_artifacts_under_0_15s_zero_raw_leak(self) -> None:
        snap = inspect_phase265_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 15)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        for art in snap.artifacts:
            self.assertTrue(art.present)
            self.assertTrue(art.matches_pinned)
            self.assertEqual(len(art.digest_sha256), 64)

    def test_06_donor_snapshot_forced_clean_room_and_missing_donor_fallback(self) -> None:
        snap_cr = inspect_phase265_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_cr.all_donors_present)
        self.assertEqual(snap_cr.donor_files_inspected, 15)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap_cr.artifacts))

        with mock.patch.object(p265, "resolve_donor_path", return_value=None):
            snap_fb = inspect_phase265_donors_readonly(force_clean_room=False)
        self.assertEqual(snap_fb.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_fb.all_donors_present)
        self.assertEqual(snap_fb.donor_files_inspected, 15)

    def test_07_clean_room_env_honors_both_fx3_clean_room_test_and_fx3_fx6_force_clean_room(self) -> None:
        self.assertEqual(P265_ENV_CLEAN_ROOM_TEST, "FX3_CLEAN_ROOM_TEST")
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1", "FX3_FX6_FORCE_CLEAN_ROOM": ""}, clear=False):
            self.assertTrue(p265._is_clean_room_forced(None))
            snap1 = inspect_phase265_donors_readonly()
            self.assertEqual(snap1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "", "FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            self.assertTrue(p265._is_clean_room_forced(None))
            snap2 = inspect_phase265_donors_readonly()
            self.assertEqual(snap2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_08_elf64_aarch64_token_checker_valid_and_negative_branches(self) -> None:
        hdr = bytearray(64)
        hdr[0:4] = b"\x7fELF"
        hdr[4] = 2  # ELFCLASS64
        hdr[5] = 1  # ELFDATA2LSB
        struct.pack_into("<H", hdr, 18, 183)  # EM_AARCH64
        valid_blob = bytes(hdr) + b"\x00InfraIPTC\x00_ZTV9InfraIPTC\x00"
        ok, summary = p265._check_elf64_aarch64_tokens(valid_blob, (b"InfraIPTC", b"_ZTV9InfraIPTC"))
        self.assertTrue(ok)
        self.assertIn("ELF64_AARCH64:", summary)

        ok_not_elf, s_not_elf = p265._check_elf64_aarch64_tokens(b"NOT_AN_ELF", (b"Tok",))
        self.assertFalse(ok_not_elf)
        self.assertEqual(s_not_elf, "NOT_ELF")

        bad_mach = bytearray(hdr)
        struct.pack_into("<H", bad_mach, 18, 62)  # x86_64
        ok_mach, s_mach = p265._check_elf64_aarch64_tokens(bytes(bad_mach), ())
        self.assertFalse(ok_mach)
        self.assertIn("BAD_ELF64_AARCH64", s_mach)

        ok_miss, s_miss = p265._check_elf64_aarch64_tokens(valid_blob, (b"MissingSym",))
        self.assertFalse(ok_miss)
        self.assertEqual(s_miss, "MISSING_TOKENS:MissingSym")

    def test_09_read_donor_readonly_bounded_missing_open_error_not_regular_and_4k_cap(self) -> None:
        with mock.patch.object(p265, "resolve_donor_path", return_value=None):
            res_m = p265._read_donor_readonly_bounded("missing.bin")
        self.assertEqual(res_m[:4], (False, 0, 0, "MISSING"))

        with mock.patch.object(p265, "resolve_donor_path", return_value=Path("/nonexistent/p265_no_file")):
            res_oe = p265._read_donor_readonly_bounded("err.bin")
        self.assertEqual(res_oe[:4], (False, 0, 0, "OPEN_ERROR"))

        fake_dir_stat = mock.Mock()
        fake_dir_stat.st_mode = stat.S_IFDIR | 0o755
        with (
            mock.patch.object(p265, "resolve_donor_path", return_value=Path("/tmp")),
            mock.patch("os.open", return_value=999),
            mock.patch("os.fstat", return_value=fake_dir_stat),
            mock.patch("os.close"),
        ):
            res_nr = p265._read_donor_readonly_bounded("dir")
        self.assertEqual(res_nr[:4], (False, 0, 0, "NOT_REGULAR"))

        with tempfile.TemporaryDirectory() as td:
            big_file = Path(td) / "big.bin"
            big_file.write_bytes(b"A" * 8192)
            with mock.patch.object(p265, "resolve_donor_path", return_value=big_file):
                ok_h, tot_b, read_b, dkind, dsha, slc = p265._read_donor_readonly_bounded(
                    "big.bin", max_full_bytes=4096
                )
            self.assertTrue(ok_h)
            self.assertEqual(tot_b, 8192)
            self.assertEqual(read_b, 4096)
            self.assertEqual(dkind, "HEADER4K_SHA256")
            self.assertEqual(len(slc), 4096)
            self.assertEqual(len(dsha), 64)

    def test_10_safety_invariant_mutation_fails_closed(self) -> None:
        with mock.patch.object(p265, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            errs = p265._safety_invariant_errors()
            self.assertTrue(any("PERSISTENT_EMMC_WRITES_AUTHORIZED" in e for e in errs))
            rep_a = evaluate_release_wo_card_lens_and_audio_meter_vault(
                ReleaseWoCardLensAndAudioMeterVaultSpec()
            )
            self.assertFalse(rep_a.passed)
            self.assertEqual(rep_a.block_code, P265_BLOCKED_SAFETY_POLICY_VIOLATION)
            rep_b = evaluate_copyright_info_46char_exif_vault(CopyrightInfo46CharExifVaultSpec())
            self.assertFalse(rep_b.passed)
            self.assertEqual(rep_b.block_code, P265_BLOCKED_SAFETY_POLICY_VIOLATION)
            with self.assertRaises(ValueError):
                evaluate_realhw_45pillar_recovery_master(force_clean_room=True)

    # ------------------------------------------------------------------
    # 2. Pillar 45A — [Release w/o Card], [Release w/o Lens] & Ver. 7.02 Audio/DISP
    # ------------------------------------------------------------------

    def test_11_default_safe_pillar45a_cardless_body_only_bench_spec_passes(self) -> None:
        spec = build_default_safe_release_wo_card_lens_audio_meter_vault_spec()
        rep = evaluate_release_wo_card_lens_and_audio_meter_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P265_STATUS_VERIFIED_PILLAR_45A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.reset_and_camset_scope_verified)
        self.assertTrue(rep.release_wo_card_still_vs_movie_gate_verified)
        self.assertTrue(rep.release_wo_lens_and_zero_end_uart_verified)
        self.assertTrue(rep.v702_audio_5item_and_disp_meter_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertFalse(rep.fx3_has_builtin_end_filter)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.emount_lens_uart_tx_bytes, 0)
        self.assertEqual(rep.cardless_unrecorded_production_violations, 0)
        self.assertEqual(rep.legacy_v1_audio_level_menu_spoof_events, 0)
        self.assertEqual(rep.audio_meter_channels_rendered, 2)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_12_exhaustive_cartesian_release_wo_card_and_lens_gate_768_states(self) -> None:
        checked = 0
        for domain in P265_SHOOTING_DOMAINS:
            for wo_card in P265_RELEASE_WO_MODES:
                for wo_lens in P265_RELEASE_WO_MODES:
                    for s1 in (False, True):
                        for s2 in (False, True):
                            for lkind in P265_LENS_ATTACHMENT_KINDS:
                                for hdmi in (False, True):
                                    for rec_dur in P265_REC_MEDIA_DUR_HDMI_MODES:
                                        checked += 1
                                        st_ok, mv_ok, ext_ok = compute_expected_release_wo_card_and_lens_gate(
                                            shooting_domain=domain,
                                            release_wo_card=wo_card,
                                            release_wo_lens=wo_lens,
                                            slot1_card_inserted=s1,
                                            slot2_card_inserted=s2,
                                            lens_attachment_kind=lkind,
                                            hdmi_connected=hdmi,
                                            rec_media_dur_hdmi_output=rec_dur,
                                        )
                                        any_card = s1 or s2
                                        lens_ok = (lkind == "EMOUNT_ELECTRONIC_LENS") or (wo_lens == "Enable")
                                        if not any_card:
                                            self.assertFalse(mv_ok)
                                        if not lens_ok:
                                            self.assertEqual((st_ok, mv_ok, ext_ok), (False, False, False))
                                        if domain == "Still":
                                            self.assertFalse(mv_ok)
                                            self.assertFalse(ext_ok)
                                            self.assertEqual(st_ok, lens_ok and (any_card or wo_card == "Enable"))
                                        else:
                                            self.assertFalse(st_ok)
                                            self.assertEqual(
                                                mv_ok,
                                                lens_ok and any_card and ((not hdmi) or rec_dur == "On"),
                                            )
                                            self.assertEqual(ext_ok, lens_ok and hdmi)
        self.assertEqual(checked, 768)

    def test_13_release_wo_card_still_only_actuation_vs_movie_internal_media_block(self) -> None:
        rep_safe_mv = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                shooting_domain="Movie",
                slot1_card_inserted=False,
                slot2_card_inserted=False,
                still_shutter_actuated=False,
                movie_internal_recording_started=False,
                hdmi_connected=True,
                external_hdmi_capture_allowed=True,
            )
        )
        self.assertTrue(rep_safe_mv.passed)

        rep_bad_mv = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                shooting_domain="Movie",
                slot1_card_inserted=False,
                slot2_card_inserted=False,
                still_shutter_actuated=False,
                movie_internal_recording_started=True,
            )
        )
        self.assertFalse(rep_bad_mv.passed)
        self.assertEqual(rep_bad_mv.block_code, P265_BLOCKED_RELEASE_WO_CARD_MOVIE_OR_BENCH_VIOLATION)

    def test_14_production_shoot_requires_release_wo_card_disable_anti_unrecorded_hazard(self) -> None:
        self.assertEqual(P265_BENCH_POSTURES, ("CARDLESS_DIAGNOSTIC_BENCH", "PRODUCTION_SHOOT"))
        self.assertEqual(P265_RELEASE_WO_CARD_DEFAULT, "Enable")
        rep_prod_ok = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                bench_posture="PRODUCTION_SHOOT",
                pre_release_wo_card="Disable",
                post_release_wo_card="Disable",
                slot1_card_inserted=False,
                slot2_card_inserted=False,
                shooting_domain="Still",
                still_shutter_actuated=False,
                still_images_saved_to_card=0,
            )
        )
        self.assertTrue(rep_prod_ok.passed)
        self.assertEqual(rep_prod_ok.cardless_unrecorded_production_violations, 0)

        rep_prod_bad = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                bench_posture="PRODUCTION_SHOOT",
                pre_release_wo_card="Enable",
                post_release_wo_card="Enable",
                slot1_card_inserted=True,
                shooting_domain="Still",
                still_shutter_actuated=True,
                still_images_saved_to_card=1,
            )
        )
        self.assertFalse(rep_prod_bad.passed)
        self.assertEqual(rep_prod_bad.block_code, P265_BLOCKED_RELEASE_WO_CARD_MOVIE_OR_BENCH_VIOLATION)
        self.assertGreaterEqual(rep_prod_bad.cardless_unrecorded_production_violations, 1)

    def test_15_release_wo_lens_across_still_movie_sq_and_body_only_pl_telescope_zero_uart(self) -> None:
        self.assertEqual(P265_RELEASE_WO_LENS_DEFAULT, "Enable")
        for kind in ("BODY_ONLY_CAP", "PL_MOUNT_MECHANICAL_ADAPTER", "TELESCOPE_T_MOUNT"):
            for domain in P265_SHOOTING_DOMAINS:
                with self.subTest(kind=kind, domain=domain):
                    meter_vis = domain != "S&Q"
                    meter_ch = 2 if meter_vis else 0
                    rep = evaluate_release_wo_card_lens_and_audio_meter_vault(
                        ReleaseWoCardLensAndAudioMeterVaultSpec(
                            bench_posture="PRODUCTION_SHOOT",
                            pre_release_wo_card="Disable",
                            post_release_wo_card="Disable",
                            pre_release_wo_lens="Enable",
                            post_release_wo_lens="Enable",
                            shooting_domain=domain,
                            slot2_card_inserted=True,
                            lens_attachment_kind=kind,
                            attached_lens_model=kind,
                            e_nd_actuator_tx_count=0,
                            emount_lens_uart_tx_bytes=0,
                            still_shutter_actuated=(domain == "Still"),
                            still_images_saved_to_card=(1 if domain == "Still" else 0),
                            movie_internal_recording_started=(domain in ("Movie", "S&Q")),
                            audio_meter_visible_on_disp=meter_vis,
                            audio_meter_channels_rendered=meter_ch,
                        )
                    )
                    self.assertTrue(rep.passed)

    def test_16_rejects_release_wo_lens_disable_release_or_nonzero_end_or_body_only_uart(self) -> None:
        for bad_kw in (
            {
                "pre_release_wo_lens": "Disable",
                "post_release_wo_lens": "Disable",
                "lens_attachment_kind": "BODY_ONLY_CAP",
                "still_shutter_actuated": True,
            },
            {"fx3_has_builtin_end_filter": True},
            {"e_nd_actuator_tx_count": 1},
            {"lens_attachment_kind": "PL_MOUNT_MECHANICAL_ADAPTER", "emount_lens_uart_tx_bytes": 32},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_release_wo_card_lens_and_audio_meter_vault(
                    ReleaseWoCardLensAndAudioMeterVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P265_BLOCKED_RELEASE_WO_LENS_OR_END_UART_VIOLATION)

    def test_17_electronic_emount_lens_allows_lens_uart_even_when_release_wo_lens_disable(self) -> None:
        rep = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                bench_posture="PRODUCTION_SHOOT",
                pre_release_wo_card="Disable",
                post_release_wo_card="Disable",
                pre_release_wo_lens="Disable",
                post_release_wo_lens="Disable",
                slot2_card_inserted=True,
                lens_attachment_kind="EMOUNT_ELECTRONIC_LENS",
                attached_lens_model="SEL2470GM2",
                e_nd_actuator_tx_count=0,
                emount_lens_uart_tx_bytes=256,
                shooting_domain="Movie",
                still_shutter_actuated=False,
                still_images_saved_to_card=0,
                movie_internal_recording_started=True,
            )
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.emount_lens_uart_tx_bytes, 256)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)

    def test_18_ver_702_exact_5_item_audio_recording_menu_and_level_0_to_31_bounds(self) -> None:
        self.assertEqual(P265_AUDIO_RECORDING_MENU_PATH, ("MENU", "Shooting", "Audio Recording"))
        self.assertEqual(
            P265_AUDIO_RECORDING_EXACT_5_ITEMS,
            (
                "Audio Recording",
                "Audio Rec Level",
                "Audio Out Timing",
                "Wind Noise Reduct.",
                "Shoe Audio Set.",
            ),
        )
        self.assertEqual(
            (P265_AUDIO_REC_LEVEL_MIN, P265_AUDIO_REC_LEVEL_MAX, P265_AUDIO_REC_LEVEL_DEFAULT),
            (0, 31, 26),
        )
        for valid_lvl in (0, 1, 26, 31):
            with self.subTest(valid_lvl=valid_lvl):
                rep = evaluate_release_wo_card_lens_and_audio_meter_vault(
                    ReleaseWoCardLensAndAudioMeterVaultSpec(
                        reset_action="NONE",
                        pre_audio_rec_level=valid_lvl,
                        post_audio_rec_level=valid_lvl,
                    )
                )
                self.assertTrue(rep.passed)

    def test_19_rejects_ver_1x_ilc2035_standalone_audio_level_display_spoof_and_level_overflow(self) -> None:
        self.assertEqual(P265_FORBIDDEN_LEGACY_V1_HELPGUIDE_ID, "ilc/2035")
        self.assertEqual(P265_FORBIDDEN_LEGACY_V1_FW_VERSIONS, ("1.00", "1.01"))
        self.assertEqual(P265_FORBIDDEN_LEGACY_V1_AUDIO_ITEM, "Audio Level Display")
        for bad_kw in (
            {"helpguide_id": "ilc/2035"},
            {"fw_version": "1.01"},
            {"audio_recording_menu_items": P265_AUDIO_RECORDING_EXACT_5_ITEMS + ("Audio Level Display",)},
            {"audio_recording_menu_items": P265_AUDIO_RECORDING_EXACT_5_ITEMS[:4]},
            {"legacy_v1_audio_level_menu_spoof_events": 1},
            {"reset_action": "NONE", "pre_audio_rec_level": -1, "post_audio_rec_level": -1},
            {"reset_action": "NONE", "pre_audio_rec_level": 32, "post_audio_rec_level": 32},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_release_wo_card_lens_and_audio_meter_vault(
                    ReleaseWoCardLensAndAudioMeterVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P265_BLOCKED_LEGACY_V1_AUDIO_MENU_SPOOF_OR_SPEC_DRIFT)

    def test_20_exhaustive_cartesian_disp_audio_meter_state_72_combinations(self) -> None:
        self.assertEqual(
            P265_DISP_SCREEN_SET_MENU_PATH,
            ("MENU", "Setup", "Operation Customize", "DISP (Screen Disp) Set"),
        )
        checked = 0
        for domain in P265_SHOOTING_DOMAINS:
            for aud_rec in P265_AUDIO_RECORDING_MODES:
                for shoe in P265_SHOE_AUDIO_SET_MODES:
                    for mi4 in (False, True):
                        for disp_chk in (False, True):
                            checked += 1
                            vis, ch = compute_expected_disp_audio_meter_state(
                                shooting_domain=domain,
                                audio_recording=aud_rec,
                                shoe_audio_set=shoe,
                                mi_shoe_digital_4ch_attached=mi4,
                                disp_screen_audio_level_checked=disp_chk,
                            )
                            if domain == "S&Q" or (domain == "Movie" and aud_rec == "Off") or not disp_chk:
                                self.assertEqual((vis, ch), (False, 0))
                            elif mi4 and shoe == "48kHz/24bit 4ch":
                                self.assertEqual((vis, ch), (True, 4))
                            else:
                                self.assertEqual((vis, ch), (True, 2))
        self.assertEqual(checked, 72)

    def test_21_disp_audio_meter_4ch_mi_shoe_and_sq_suppression_enforcement(self) -> None:
        rep_4ch = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                reset_action="NONE",
                pre_shoe_audio_set="48kHz/24bit 4ch",
                post_shoe_audio_set="48kHz/24bit 4ch",
                mi_shoe_digital_4ch_attached=True,
                audio_meter_visible_on_disp=True,
                audio_meter_channels_rendered=4,
            )
        )
        self.assertTrue(rep_4ch.passed)
        self.assertEqual(rep_4ch.audio_meter_channels_rendered, 4)

        rep_sq_bad = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                shooting_domain="S&Q",
                still_shutter_actuated=False,
                movie_internal_recording_started=False,
                audio_meter_visible_on_disp=True,
                audio_meter_channels_rendered=2,
            )
        )
        self.assertFalse(rep_sq_bad.passed)
        self.assertEqual(rep_sq_bad.block_code, P265_BLOCKED_DISP_AUDIO_METER_OR_RESET_SCOPE_DRIFT)

    def test_22_pillar45a_reset_scope_survival_vs_initialize_and_ordonly_camset01_roundtrip(self) -> None:
        rep_csr = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                bench_posture="PRODUCTION_SHOOT",
                pre_release_wo_card="Disable",
                pre_release_wo_lens="Disable",
                pre_disp_screen_audio_level_checked=False,
                pre_audio_recording="Off",
                pre_audio_rec_level=10,
                pre_audio_out_timing="Lip Sync",
                pre_wind_noise_reduct="On",
                pre_shoe_audio_set="48kHz/24bit 4ch",
                reset_action="Camera Settings Reset",
                post_release_wo_card="Disable",
                post_release_wo_lens="Disable",
                post_disp_screen_audio_level_checked=False,
                post_audio_recording=P265_AUDIO_RECORDING_DEFAULT,
                post_audio_rec_level=P265_AUDIO_REC_LEVEL_DEFAULT,
                post_audio_out_timing=P265_AUDIO_OUT_TIMING_DEFAULT,
                post_wind_noise_reduct=P265_WIND_NOISE_REDUCT_DEFAULT,
                post_shoe_audio_set=P265_SHOE_AUDIO_SET_DEFAULT,
                lens_attachment_kind="EMOUNT_ELECTRONIC_LENS",
                attached_lens_model="SEL50F12GM",
                slot2_card_inserted=True,
                still_shutter_actuated=True,
                still_images_saved_to_card=1,
                audio_meter_visible_on_disp=False,
                audio_meter_channels_rendered=0,
            )
        )
        self.assertTrue(rep_csr.passed)

        rep_init = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                pre_release_wo_card="Disable",
                pre_release_wo_lens="Disable",
                pre_disp_screen_audio_level_checked=False,
                reset_action="Initialize",
                post_release_wo_card="Enable",
                post_release_wo_lens="Enable",
                post_disp_screen_audio_level_checked=True,
            )
        )
        self.assertTrue(rep_init.passed)

        rep_drift = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                pre_audio_rec_level=12,
                reset_action="Camera Settings Reset",
                post_audio_rec_level=12,
            )
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P265_BLOCKED_DISP_AUDIO_METER_OR_RESET_SCOPE_DRIFT)

    def test_23_pillar45a_rejects_overlay_escape_tier0_drift_unlock_and_invalid_spec(self) -> None:
        r_unl = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(r_unl.passed)
        self.assertEqual(r_unl.block_code, P265_BLOCKED_SAFETY_POLICY_VIOLATION)

        r_ov = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(overlay_dir="/setting/leak")
        )
        self.assertFalse(r_ov.passed)
        self.assertEqual(r_ov.block_code, P265_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        r_h3 = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(r_h3.passed)
        self.assertEqual(r_h3.block_code, P265_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        r_inv = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(camera_model="ILME-FX6")
        )
        self.assertFalse(r_inv.passed)
        self.assertEqual(r_inv.block_code, P265_BLOCKED_INVALID_RELEASE_WO_OR_AUDIO_METER_SPEC)

        r_camset_bad = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                camset_load_after_reset=True,
                camset_source_model="ILME-FX6",
            )
        )
        self.assertFalse(r_camset_bad.passed)
        self.assertEqual(r_camset_bad.block_code, P265_BLOCKED_INVALID_RELEASE_WO_OR_AUDIO_METER_SPEC)

    def test_24_pillar45a_6_scenario_suite_passes_all_6_scenarios(self) -> None:
        res = run_pillar45a_release_wo_card_lens_audio_meter_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P265_STATUS_VERIFIED_PILLAR_45A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P265_PILLAR_45A_SCENARIO_IDS)
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])

    # ------------------------------------------------------------------
    # 3. Pillar 45B — [Copyright Info] <= 46-Char Still EXIF & PII Hygiene
    # ------------------------------------------------------------------

    def test_25_default_safe_pillar45b_clean_room_initialize_spec_passes(self) -> None:
        spec = build_default_safe_copyright_info_46char_exif_vault_spec()
        rep = evaluate_copyright_info_46char_exif_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P265_STATUS_VERIFIED_PILLAR_45B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.char_46_ascii_and_disp_readonly_verified)
        self.assertTrue(rep.reset_survival_vs_initialize_wipe_verified)
        self.assertTrue(rep.still_exif_only_movie_isolation_verified)
        self.assertTrue(rep.clean_room_pii_and_slot1_vault_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.photographer_char_length, 0)
        self.assertEqual(rep.copyright_char_length, 0)
        self.assertEqual(rep.photographer_copyright_pii_leaked_bytes, 0)
        self.assertEqual(rep.copyright_char_overflow_or_movie_mutation_events, 0)
        self.assertEqual(rep.slot1_copyright_vault_mutation_bytes, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_26_copyright_info_exact_4_item_menu_path_and_46_char_constant(self) -> None:
        self.assertEqual(P265_COPYRIGHT_INFO_MENU_PATH, ("MENU", "Shooting", "File", "Copyright Info"))
        self.assertEqual(
            P265_COPYRIGHT_INFO_EXACT_4_ITEMS,
            (
                "Write Copyright Info",
                "Set Photographer",
                "Set Copyright",
                "Disp. Copyright Info",
            ),
        )
        self.assertEqual(P265_WRITE_COPYRIGHT_MODES, ("Off", "On"))
        self.assertEqual(P265_WRITE_COPYRIGHT_DEFAULT, "Off")
        self.assertEqual(P265_COPYRIGHT_MAX_CHARS, 46)

    def test_27_printable_ascii_46_char_boundary_0_1_45_and_exact_46_pass(self) -> None:
        for n in (0, 1, 23, 45, 46):
            s = ("A1_b-C.d/E:2026 (c) FX3 Bench! #99+~*=@?[]{}^" * 2)[:n]
            with self.subTest(length=n):
                self.assertEqual(len(s), n)
                rep = evaluate_copyright_info_46char_exif_vault(
                    CopyrightInfo46CharExifVaultSpec(
                        pre_write_copyright_info="Off",
                        pre_photographer_text=s,
                        pre_copyright_text=s,
                        reset_action="NONE",
                        post_write_copyright_info="Off",
                        post_photographer_text=s,
                        post_copyright_text=s,
                        displayed_photographer_preview=s,
                        displayed_copyright_preview=s,
                        copyright_c_icon_shown_on_screen=False,
                        shooting_domain="Still",
                        target_media_slot=2,
                        still_exif_copyright_written=False,
                        clean_room_pii_hygiene_enforced=False,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertEqual(rep.photographer_char_length, n)
                self.assertEqual(rep.copyright_char_length, n)

    def test_28_rejects_47_char_overflow_control_bytes_and_non_ascii_utf8(self) -> None:
        for bad_str in (
            "X" * 47,
            "Y" * 100,
            "NULL\x00BYTE",
            "BEL\x07CTRL",
            "TAB\tCHAR",
            "DEL\x7fCHAR",
            "NON_ASCII_\u00a9_SYMBOL",
            "CJK_\u6444\u5f71\u5e08",
        ):
            with self.subTest(bad_str=bad_str):
                rep = evaluate_copyright_info_46char_exif_vault(
                    CopyrightInfo46CharExifVaultSpec(pre_photographer_text=bad_str)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P265_BLOCKED_COPYRIGHT_46CHAR_OR_ASCII_OVERFLOW)
                self.assertGreaterEqual(rep.copyright_char_overflow_or_movie_mutation_events, 1)

    def test_29_disp_copyright_info_requires_ordonly_and_zero_flash_writes(self) -> None:
        for bad_kw in (
            {"disp_copyright_info_open_mode": "O_RDWR"},
            {"disp_copyright_info_flash_writes": 1},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_copyright_info_46char_exif_vault(
                    CopyrightInfo46CharExifVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P265_BLOCKED_INVALID_COPYRIGHT_INFO_SPEC)

    def test_30_exhaustive_compute_expected_copyright_info_state_across_all_reset_actions(self) -> None:
        photog = "SYNTH_BENCH_UNIT_A"
        copy_t = "SYNTH_LAB_2026"
        for wr in P265_WRITE_COPYRIGHT_MODES:
            self.assertEqual(
                compute_expected_copyright_info_state(
                    pre_write_copyright_info=wr,
                    pre_photographer_text=photog,
                    pre_copyright_text=copy_t,
                    reset_action="NONE",
                ),
                (wr, photog, copy_t),
            )
            self.assertEqual(
                compute_expected_copyright_info_state(
                    pre_write_copyright_info=wr,
                    pre_photographer_text=photog,
                    pre_copyright_text=copy_t,
                    reset_action="Reset Network Set.",
                ),
                (wr, photog, copy_t),
            )
            self.assertEqual(
                compute_expected_copyright_info_state(
                    pre_write_copyright_info=wr,
                    pre_photographer_text=photog,
                    pre_copyright_text=copy_t,
                    reset_action="Camera Settings Reset",
                ),
                ("Off", photog, copy_t),
            )
            self.assertEqual(
                compute_expected_copyright_info_state(
                    pre_write_copyright_info=wr,
                    pre_photographer_text=photog,
                    pre_copyright_text=copy_t,
                    reset_action="Initialize",
                ),
                ("Off", "", ""),
            )

    def test_31_camera_settings_reset_preserves_46char_strings_while_turning_write_off(self) -> None:
        s46 = "SYNTH_BENCH_CAMERA_UNIT_01_46CHAR_BOUNDARY_OK!"
        self.assertEqual(len(s46), 46)
        rep = evaluate_copyright_info_46char_exif_vault(
            CopyrightInfo46CharExifVaultSpec(
                pre_write_copyright_info="On",
                pre_photographer_text=s46,
                pre_copyright_text=s46,
                reset_action="Camera Settings Reset",
                post_write_copyright_info="Off",
                post_photographer_text=s46,
                post_copyright_text=s46,
                displayed_photographer_preview=s46,
                displayed_copyright_preview=s46,
                copyright_c_icon_shown_on_screen=False,
                shooting_domain="Still",
                target_media_slot=2,
                still_exif_copyright_written=False,
                clean_room_pii_hygiene_enforced=False,
            )
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.photographer_char_length, 46)
        self.assertEqual(rep.copyright_char_length, 46)

    def test_32_rejects_camera_settings_reset_wiping_strings_or_initialize_leaving_strings(self) -> None:
        r_csr_wiped = evaluate_copyright_info_46char_exif_vault(
            CopyrightInfo46CharExifVaultSpec(
                pre_write_copyright_info="On",
                pre_photographer_text="SYNTH_PHOTOG",
                pre_copyright_text="SYNTH_COPY",
                reset_action="Camera Settings Reset",
                post_write_copyright_info="Off",
                post_photographer_text="",
                post_copyright_text="",
                displayed_photographer_preview="",
                displayed_copyright_preview="",
                clean_room_pii_hygiene_enforced=False,
            )
        )
        self.assertFalse(r_csr_wiped.passed)
        self.assertEqual(r_csr_wiped.block_code, P265_BLOCKED_COPYRIGHT_RESET_VS_INITIALIZE_SCOPE_DRIFT)

        r_init_left = evaluate_copyright_info_46char_exif_vault(
            CopyrightInfo46CharExifVaultSpec(
                pre_write_copyright_info="On",
                pre_photographer_text="SYNTH_PHOTOG",
                pre_copyright_text="SYNTH_COPY",
                reset_action="Initialize",
                post_write_copyright_info="Off",
                post_photographer_text="SYNTH_PHOTOG",
                post_copyright_text="",
                displayed_photographer_preview="SYNTH_PHOTOG",
                displayed_copyright_preview="",
                clean_room_pii_hygiene_enforced=False,
            )
        )
        self.assertFalse(r_init_left.passed)
        self.assertEqual(r_init_left.block_code, P265_BLOCKED_COPYRIGHT_RESET_VS_INITIALIZE_SCOPE_DRIFT)

    def test_33_still_exif_copyright_written_across_jpeg_heif_raw_on_slot2_when_write_on(self) -> None:
        for fmt in P265_STILL_IMAGE_FORMATS:
            with self.subTest(still_format=fmt):
                rep = evaluate_copyright_info_46char_exif_vault(
                    CopyrightInfo46CharExifVaultSpec(
                        pre_write_copyright_info="On",
                        pre_photographer_text="SYNTH_BENCH_UNIT",
                        pre_copyright_text="SYNTH_BENCH_LAB",
                        reset_action="NONE",
                        post_write_copyright_info="On",
                        post_photographer_text="SYNTH_BENCH_UNIT",
                        post_copyright_text="SYNTH_BENCH_LAB",
                        displayed_photographer_preview="SYNTH_BENCH_UNIT",
                        displayed_copyright_preview="SYNTH_BENCH_LAB",
                        copyright_c_icon_shown_on_screen=True,
                        shooting_domain="Still",
                        still_image_format=fmt,
                        target_media_slot=2,
                        still_exif_copyright_written=True,
                        movie_xavc_or_raw_copyright_mutated=False,
                        clean_room_pii_hygiene_enforced=False,
                    )
                )
                self.assertTrue(rep.passed)

    def test_34_movie_and_sq_xavc_and_hdmi_raw_never_mutated_even_when_write_copyright_on(self) -> None:
        for domain in ("Movie", "S&Q"):
            for mfmt in P265_MOVIE_STREAM_FORMATS:
                with self.subTest(domain=domain, movie_format=mfmt):
                    rep = evaluate_copyright_info_46char_exif_vault(
                        CopyrightInfo46CharExifVaultSpec(
                            pre_write_copyright_info="On",
                            pre_photographer_text="SYNTH_BENCH_UNIT",
                            pre_copyright_text="SYNTH_BENCH_LAB",
                            reset_action="NONE",
                            post_write_copyright_info="On",
                            post_photographer_text="SYNTH_BENCH_UNIT",
                            post_copyright_text="SYNTH_BENCH_LAB",
                            displayed_photographer_preview="SYNTH_BENCH_UNIT",
                            displayed_copyright_preview="SYNTH_BENCH_LAB",
                            copyright_c_icon_shown_on_screen=True,
                            shooting_domain=domain,
                            movie_stream_format=mfmt,
                            target_media_slot=2,
                            still_exif_copyright_written=False,
                            movie_xavc_or_raw_copyright_mutated=False,
                            clean_room_pii_hygiene_enforced=False,
                        )
                    )
                    self.assertTrue(rep.passed)

    def test_35_rejects_movie_stream_mutation_or_exif_written_when_write_off(self) -> None:
        r_mv = evaluate_copyright_info_46char_exif_vault(
            CopyrightInfo46CharExifVaultSpec(
                shooting_domain="Movie",
                movie_stream_format="HDMI RAW 4264x2408",
                movie_xavc_or_raw_copyright_mutated=True,
            )
        )
        self.assertFalse(r_mv.passed)
        self.assertEqual(r_mv.block_code, P265_BLOCKED_COPYRIGHT_MOVIE_STREAM_OR_EXIF_SCOPE_VIOLATION)

        r_off_written = evaluate_copyright_info_46char_exif_vault(
            CopyrightInfo46CharExifVaultSpec(
                shooting_domain="Still",
                still_exif_copyright_written=True,  # post_write_copyright_info is Off after Initialize!
            )
        )
        self.assertFalse(r_off_written.passed)
        self.assertEqual(r_off_written.block_code, P265_BLOCKED_COPYRIGHT_MOVIE_STREAM_OR_EXIF_SCOPE_VIOLATION)

    def test_36_clean_room_operator_pii_zeroing_rejects_pii_leak_or_residual_strings(self) -> None:
        for bad_kw in (
            {"contains_operator_pii": True},
            {"photographer_copyright_pii_leaked_bytes": 16},
            {
                "pre_write_copyright_info": "On",
                "pre_photographer_text": "RESIDUAL_OP_NAME",
                "pre_copyright_text": "",
                "reset_action": "NONE",
                "post_write_copyright_info": "On",
                "post_photographer_text": "RESIDUAL_OP_NAME",
                "post_copyright_text": "",
                "displayed_photographer_preview": "RESIDUAL_OP_NAME",
                "displayed_copyright_preview": "",
                "copyright_c_icon_shown_on_screen": True,
                "shooting_domain": "Still",
                "target_media_slot": 2,
                "still_exif_copyright_written": True,
                "clean_room_pii_hygiene_enforced": True,
            },
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_copyright_info_46char_exif_vault(
                    CopyrightInfo46CharExifVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P265_BLOCKED_COPYRIGHT_CLEAN_ROOM_PII_OR_SLOT1_VAULT_LEAK)
                self.assertGreaterEqual(rep.photographer_copyright_pii_leaked_bytes, 1)

    def test_37_camset_excluded_items_firewall_rejects_copyright_export_or_fx6_donor_camset(self) -> None:
        self.assertEqual(len(P265_CAMSET_FILENAMES), 10)
        self.assertEqual((P265_CAMSET_FILENAMES[0], P265_CAMSET_FILENAMES[-1]), ("CAMSET01.DAT", "CAMSET10.DAT"))
        for bad_kw in (
            {"camset_exported_copyright_pii_bytes": 32},
            {"camset_overwrote_inbody_copyright": True},
            {"camset_load_after_reset": True, "camset_read_only_load": False},
            {"camset_load_after_reset": True, "camset_source_model": "ILME-FX6"},
            {"camset_load_after_reset": True, "camset_filename": "CAMSET99.DAT"},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_copyright_info_46char_exif_vault(
                    CopyrightInfo46CharExifVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P265_BLOCKED_COPYRIGHT_CLEAN_ROOM_PII_OR_SLOT1_VAULT_LEAK)

    def test_38_slot1_tier0_vault_guard_overlay_escape_tier0_drift_and_invalid_spec(self) -> None:
        self.assertEqual(P265_SLOT1_VAULT_SLOT, 1)
        self.assertEqual(P265_TIER0_SURFACE_COUNT, 16)
        self.assertTrue(P265_STAGE_B_VOLATILE_OVERLAY_DIR.startswith("/tmp/"))
        for vault_kw in (
            {"slot1_tier0_vault_active": True, "target_media_slot": 1},
            {"slot1_tier0_vault_active": True, "slot1_save_or_exif_write_attempted": True},
            {"slot1_tier0_vault_active": True, "slot1_sdxc_wp_locked": False},
            {"slot1_copyright_vault_mutation_bytes": 64},
        ):
            with self.subTest(vault_kw=vault_kw):
                rep = evaluate_copyright_info_46char_exif_vault(
                    CopyrightInfo46CharExifVaultSpec(**vault_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P265_BLOCKED_COPYRIGHT_CLEAN_ROOM_PII_OR_SLOT1_VAULT_LEAK)
                self.assertGreaterEqual(rep.slot1_copyright_vault_mutation_bytes, 1)

        r_ov = evaluate_copyright_info_46char_exif_vault(
            CopyrightInfo46CharExifVaultSpec(overlay_dir="/dev/cnflasha")
        )
        self.assertFalse(r_ov.passed)
        self.assertEqual(r_ov.block_code, P265_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        r_h3 = evaluate_copyright_info_46char_exif_vault(
            CopyrightInfo46CharExifVaultSpec(tier0_surfaces_h0_h3_matched=14)
        )
        self.assertFalse(r_h3.passed)
        self.assertEqual(r_h3.block_code, P265_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        r_inv = evaluate_copyright_info_46char_exif_vault(
            CopyrightInfo46CharExifVaultSpec(copyright_info_subitems=("OnlyOneItem",))
        )
        self.assertFalse(r_inv.passed)
        self.assertEqual(r_inv.block_code, P265_BLOCKED_INVALID_COPYRIGHT_INFO_SPEC)

    def test_39_pillar45b_6_scenario_suite_passes_all_6_scenarios(self) -> None:
        res = run_pillar45b_copyright_info_46char_exif_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P265_STATUS_VERIFIED_PILLAR_45B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P265_PILLAR_45B_SCENARIO_IDS)
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])

    # ------------------------------------------------------------------
    # 4. Combined Verifier & Standalone Pillar 45 Suite
    # ------------------------------------------------------------------

    def test_40_combined_verifier_and_symmetry_alias_pass_dual_mode_and_serialize(self) -> None:
        r_ok = verify_release_wo_card_lens_audio_meter_and_copyright_vault()
        r_alias = verify_release_wo_card_lens_audio_meter_copyright_vault(force_clean_room=True)
        self.assertTrue(r_ok.all_passed)
        self.assertTrue(r_ok.passed)
        self.assertEqual(r_ok.status, P265_STATUS_VERIFIED_PILLAR45_SUITE)
        self.assertFalse(r_ok.fx3_has_builtin_end_filter)
        self.assertEqual(r_ok.e_nd_actuator_tx_count, 0)
        self.assertEqual(r_ok.cardless_unrecorded_production_violations, 0)
        self.assertEqual(r_ok.legacy_v1_audio_level_menu_spoof_events, 0)
        self.assertEqual(r_ok.photographer_copyright_pii_leaked_bytes, 0)
        self.assertEqual(r_ok.copyright_char_overflow_or_movie_mutation_events, 0)
        self.assertEqual(r_ok.slot1_copyright_vault_mutation_bytes, 0)
        self.assertTrue(r_alias.all_passed)
        self.assertEqual(r_alias.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        d = r_alias.to_dict()
        self.assertEqual(d["schema"], PHASE265_SCHEMA)
        self.assertTrue(d["cnflasha_userspace_write_blocked"])

    def test_41_combined_verifier_propagates_pillar45a_pillar45b_and_donor_failures(self) -> None:
        r_bad_a = verify_release_wo_card_lens_audio_meter_and_copyright_vault(
            release_audio_spec=ReleaseWoCardLensAndAudioMeterVaultSpec(e_nd_actuator_tx_count=3),
            force_clean_room=True,
        )
        self.assertFalse(r_bad_a.all_passed)
        self.assertEqual(r_bad_a.status, P265_STATUS_FAIL_PILLAR45_SUITE)
        self.assertEqual(r_bad_a.e_nd_actuator_tx_count, 3)

        r_bad_b = verify_release_wo_card_lens_audio_meter_and_copyright_vault(
            copyright_spec=CopyrightInfo46CharExifVaultSpec(photographer_copyright_pii_leaked_bytes=12),
            force_clean_room=True,
        )
        self.assertFalse(r_bad_b.all_passed)
        self.assertEqual(r_bad_b.status, P265_STATUS_FAIL_PILLAR45_SUITE)
        self.assertEqual(r_bad_b.photographer_copyright_pii_leaked_bytes, 12)

        bad_snap = replace(
            inspect_phase265_donors_readonly(force_clean_room=True),
            all_donors_present=False,
            under_0_15s_budget=False,
        )
        with mock.patch.object(p265, "inspect_phase265_donors_readonly", return_value=bad_snap):
            r_bad_d = verify_release_wo_card_lens_audio_meter_and_copyright_vault(force_clean_room=True)
        self.assertFalse(r_bad_d.all_passed)
        self.assertGreaterEqual(len(r_bad_d.errors), 2)

    def test_42_standalone_pillar45_suite_deterministic_sha256_in_default_and_clean_room(self) -> None:
        rep_d1 = run_pillar45_standalone_suite()
        rep_d2 = run_pillar45_standalone_suite()
        self.assertTrue(rep_d1.all_passed)
        self.assertEqual(rep_d1.status, P265_STATUS_VERIFIED_PILLAR45_SUITE)
        self.assertEqual(rep_d1.suite_sha256, rep_d2.suite_sha256)
        self.assertEqual(len(rep_d1.suite_sha256), 64)

        rep_cr1 = run_pillar45_standalone_suite(force_clean_room=True)
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            rep_cr2 = run_pillar45_standalone_suite()
        self.assertTrue(rep_cr1.all_passed)
        self.assertEqual(rep_cr1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_cr2.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_cr1.suite_sha256, rep_cr2.suite_sha256)

    def test_43_standalone_pillar45_suite_fails_closed_on_subsuite_failure(self) -> None:
        bad_a = replace(
            run_pillar45a_release_wo_card_lens_audio_meter_vault_6_scenario_suite(),
            passed=False,
            status=P265_STATUS_REJECTED_PILLAR_45A,
        )
        with mock.patch.object(
            p265, "run_pillar45a_release_wo_card_lens_audio_meter_vault_6_scenario_suite", return_value=bad_a
        ):
            rep = run_pillar45_standalone_suite(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P265_STATUS_FAIL_PILLAR45_SUITE)
        self.assertEqual(rep.e_nd_actuator_tx_count, 1)

    # ------------------------------------------------------------------
    # 5. Unified 45/45 Recovery Master Aggregator & Fault Injection
    # ------------------------------------------------------------------

    def test_44_master45_default_passes_all_45_pillars_within_latency_budgets(self) -> None:
        rep = self.master45_default
        self.assertEqual(rep.schema, PHASE265_SCHEMA)
        self.assertEqual(rep.version, PHASE265_VERSION)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P265_STATUS_VERIFIED_45OF45_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 45)
        self.assertEqual(rep.pillars_passed, 45)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertTrue(rep.under_6s_budget)
        self.assertEqual([p.pillar_number for p in rep.pillars], list(range(1, 46)))
        self.assertEqual(tuple(p.pillar_id for p in rep.pillars), MASTER_45_PILLAR_IDS)

    def test_45_master45_clean_room_passes_all_45_pillars_with_64hex_digest(self) -> None:
        rep = self.master45_clean_room
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.status, P265_STATUS_VERIFIED_45OF45_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 45)
        self.assertEqual(rep.pillars_passed, 45)
        self.assertEqual(rep.failed_pillars, ())
        self.assertEqual(len(rep.master_45pillar_sha256), 64)
        self.assertTrue(all(p.passed for p in rep.pillars))

    def test_46_fx3_clean_room_test_env_propagates_to_44pillar_and_matches_clean_room_digest(self) -> None:
        seen_kwargs = []

        def _mock_m44(**kwargs):
            seen_kwargs.append(kwargs)
            return self.master44_clean_room

        with (
            mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False),
            mock.patch.object(p265, "evaluate_realhw_44pillar_recovery_master", side_effect=_mock_m44),
        ):
            rep_env = evaluate_realhw_45pillar_recovery_master()
        self.assertEqual(seen_kwargs, [{"force_clean_room": True}])
        self.assertEqual(rep_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_env.master_45pillar_sha256, self.master45_clean_room.master_45pillar_sha256)

    def test_47_master45_hard_locked_zero_write_safety_telemetry(self) -> None:
        for rep in (self.master45_default, self.master45_clean_room):
            self.assertTrue(rep.cnflasha_userspace_write_blocked)
            self.assertEqual(rep.otp_fuse_touches, 0)
            self.assertEqual(rep.otp_fuse_writes, 0)
            self.assertEqual(rep.rpmb_counter_increments, 0)
            self.assertEqual(rep.passive_tx_bytes_emitted, 0)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertFalse(rep.isp_write_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.persistent_write_release)
            self.assertFalse(rep.allow_boot_partition_targeting)
            self.assertFalse(rep.allow_destructive_fastboot)
            self.assertFalse(rep.live_usb_iokit_transmit_enabled)
            self.assertFalse(rep.hardware_live_attachment_authorized)

    def test_48_master45_wave43_and_preserved_pillars_1_to_44_rollup_metrics(self) -> None:
        rep = self.master45_clean_room
        self.assertFalse(rep.fx3_has_builtin_end_filter)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.cardless_unrecorded_production_violations, 0)
        self.assertEqual(rep.legacy_v1_audio_level_menu_spoof_events, 0)
        self.assertEqual(rep.photographer_copyright_pii_leaked_bytes, 0)
        self.assertEqual(rep.copyright_char_overflow_or_movie_mutation_events, 0)
        self.assertEqual(rep.slot1_copyright_vault_mutation_bytes, 0)
        self.assertEqual(rep.apsc_s35_4k_or_raw_bypass_events, 0)
        self.assertEqual(rep.ai_unit_subject_recog_spoof_events, 0)
        self.assertEqual(rep.hdmi_clean_feed_eye_frame_baked_pixels, 0)
        self.assertEqual(rep.version_dialog_flash_writes, 0)
        self.assertGreaterEqual(rep.bodydata_flash_attempts_blocked, 1)
        self.assertEqual(rep.slot1_bodydata_vault_mutation_bytes, 0)
        self.assertEqual(rep.auto_slow_shutter_lockout_bypass_events, 0)
        self.assertEqual(rep.auto_slow_shutter_angle_overlap_events, 0)
        self.assertEqual(rep.breathing_comp_raw_or_240p_bypass_events, 0)
        self.assertEqual(rep.hdmi_rec_ctrl_without_tc_violations, 0)
        self.assertEqual(rep.slot1_hdmi_rec_vault_mutation_bytes, 0)
        self.assertEqual(rep.diff_set_transition_corruption_events, 0)
        self.assertEqual(rep.shutter_angle_common_bleed_events, 0)
        self.assertEqual(rep.slot1_custom_key_vault_mutation_bytes, 0)
        self.assertFalse(rep.fx3_has_builtin_evf)
        self.assertEqual(rep.evf_finder_monitor_spoof_events, 0)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertEqual(rep.unbuffered_battery_pull_events, 0)

    def test_49_master45_pillar45_entry_key_metrics_and_donor_count(self) -> None:
        p45_entry = self.master45_clean_room.pillars[-1]
        self.assertEqual(p45_entry.pillar_number, 45)
        self.assertEqual(
            p45_entry.pillar_id,
            "pillar_45_release_wo_card_lens_audio_meter_copyright_vault",
        )
        self.assertTrue(p45_entry.passed)
        self.assertEqual(
            p45_entry.key_metrics["pillar_45a_release_wo_card_lens_audio_meter_vault"],
            "6/6",
        )
        self.assertEqual(
            p45_entry.key_metrics["pillar_45b_copyright_info_46char_exif_vault"],
            "6/6",
        )
        self.assertEqual(p45_entry.key_metrics["donor_files_inspected"], 15)
        self.assertEqual(len(p45_entry.digest_sha256), 64)

    def test_50_evaluate_45pillar_and_verify_45pillar_suite_aliases_match_master(self) -> None:
        with mock.patch.object(
            p265, "evaluate_realhw_44pillar_recovery_master", return_value=self.master44_clean_room
        ):
            r1 = evaluate_45pillar_recovery_master(force_clean_room=True)
            r2 = verify_45pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_45pillar_sha256, self.master45_clean_room.master_45pillar_sha256)
        self.assertEqual(r2.master_45pillar_sha256, self.master45_clean_room.master_45pillar_sha256)

    def test_51_master45_to_dict_json_roundtrip_clean_and_zero_raw_firmware_bytes(self) -> None:
        raw_json = json.dumps(self.master45_clean_room.to_dict(), sort_keys=True)
        parsed = json.loads(raw_json)
        self.assertEqual(parsed["schema"], PHASE265_SCHEMA)
        self.assertEqual(parsed["pillar_count"], 45)
        self.assertEqual(parsed["pillars_passed"], 45)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(parsed["photographer_copyright_pii_leaked_bytes"], 0)

    def test_52_fault_injection_pillar_01_fails_closed_44_of_45(self) -> None:
        pid = MASTER_45_PILLAR_IDS[0]
        with mock.patch.object(
            p265, "evaluate_realhw_44pillar_recovery_master", return_value=self.master44_clean_room
        ):
            rep = evaluate_realhw_45pillar_recovery_master(
                force_clean_room=True, fault_inject_pillar=pid
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P265_STATUS_FAIL_45OF45_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 44)
        self.assertEqual(rep.failed_pillars, (pid,))

    def test_53_fault_injection_pillar_22_fails_closed_44_of_45(self) -> None:
        pid = MASTER_45_PILLAR_IDS[21]
        with mock.patch.object(
            p265, "evaluate_realhw_44pillar_recovery_master", return_value=self.master44_clean_room
        ):
            rep = evaluate_realhw_45pillar_recovery_master(
                force_clean_room=True, fault_inject_pillar=pid
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 44)
        self.assertEqual(rep.failed_pillars, (pid,))

    def test_54_fault_injection_pillar_44_fails_closed_44_of_45(self) -> None:
        pid = MASTER_45_PILLAR_IDS[43]
        with mock.patch.object(
            p265, "evaluate_realhw_44pillar_recovery_master", return_value=self.master44_clean_room
        ):
            rep = evaluate_realhw_45pillar_recovery_master(
                force_clean_room=True, fault_inject_pillar=pid
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 44)
        self.assertEqual(rep.failed_pillars, (pid,))

    def test_55_fault_injection_pillar_45_fails_closed_44_of_45(self) -> None:
        pid = MASTER_45_PILLAR_IDS[44]
        with mock.patch.object(
            p265, "evaluate_realhw_44pillar_recovery_master", return_value=self.master44_clean_room
        ):
            rep = evaluate_realhw_45pillar_recovery_master(
                force_clean_room=True, fault_inject_pillar=pid
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 44)
        self.assertEqual(rep.failed_pillars, (pid,))
        self.assertIn(f"FAULT_INJECTED:{pid}", rep.pillars[44].errors)

    def test_56_exhaustive_fault_injection_across_all_45_pillars(self) -> None:
        with mock.patch.object(
            p265, "evaluate_realhw_44pillar_recovery_master", return_value=self.master44_clean_room
        ):
            for idx, pid in enumerate(MASTER_45_PILLAR_IDS):
                rep = evaluate_realhw_45pillar_recovery_master(
                    force_clean_room=True, fault_inject_pillar=pid
                )
                self.assertFalse(rep.all_passed)
                self.assertEqual(rep.pillars_passed, 44)
                self.assertEqual(rep.failed_pillars, (pid,))
                self.assertFalse(rep.pillars[idx].passed)

    def test_57_unknown_fault_inject_pillar_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_45pillar_recovery_master(
                force_clean_room=True, fault_inject_pillar="pillar_99_nonexistent"
            )

    def test_58_master45_fails_closed_when_44pillar_rollup_violates_safety_counter(self) -> None:
        bad_m44 = replace(
            self.master44_clean_room,
            otp_fuse_touches=1,
            bodydata_flash_attempts_blocked=0,
            apsc_s35_4k_or_raw_bypass_events=1,
        )
        with mock.patch.object(p265, "evaluate_realhw_44pillar_recovery_master", return_value=bad_m44):
            rep = evaluate_realhw_45pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P265_STATUS_FAIL_45OF45_AGGREGATOR)
        self.assertGreaterEqual(len(rep.errors), 3)

    def test_59_master45_fails_closed_when_pillar45_violates_wave43_safety_counter(self) -> None:
        bad_p45 = replace(
            run_pillar45_standalone_suite(force_clean_room=True),
            photographer_copyright_pii_leaked_bytes=12,
            legacy_v1_audio_level_menu_spoof_events=1,
        )
        with (
            mock.patch.object(
                p265, "evaluate_realhw_44pillar_recovery_master", return_value=self.master44_clean_room
            ),
            mock.patch.object(p265, "run_pillar45_standalone_suite", return_value=bad_p45),
        ):
            rep = evaluate_realhw_45pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P265_STATUS_FAIL_45OF45_AGGREGATOR)
        self.assertTrue(any("photographer_copyright_pii_leaked_bytes" in e for e in rep.errors))
        self.assertTrue(any("legacy_v1_audio_level_menu_spoof_events" in e for e in rep.errors))

    def test_60_preserved_44pillar_master_remains_intact_at_44_of_44(self) -> None:
        self.assertTrue(self.master44_clean_room.all_passed)
        self.assertEqual(self.master44_clean_room.pillar_count, 44)
        self.assertEqual(self.master44_clean_room.pillars_passed, 44)
        self.assertEqual(self.master44_clean_room.status, "VERIFIED_44OF44_PILLAR_RECOVERY_MASTER")

    # ------------------------------------------------------------------
    # 6. CLI Subcommands & Firmware Version Matrix
    # ------------------------------------------------------------------

    @staticmethod
    def _run_inprocess_cli(*argv: str):
        import sys as _sys

        buf = io.StringIO()
        with (
            mock.patch.object(_sys, "argv", ["fx3_recovery", *argv]),
            redirect_stdout(buf),
        ):
            rc = cli_main.main()
        return rc, buf.getvalue()

    def test_61_cli_verify_release_wo_card_lens_audio_meter_copyright_vault_json(self) -> None:
        rc, out = self._run_inprocess_cli(
            "verify-release-wo-card-lens-audio-meter-copyright-vault", "--json"
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P265_STATUS_VERIFIED_PILLAR45_SUITE)
        self.assertEqual(payload["e_nd_actuator_tx_count"], 0)
        self.assertEqual(payload["photographer_copyright_pii_leaked_bytes"], 0)

    def test_62_cli_verify_release_wo_card_lens_audio_meter_copyright_vault_clean_room_text(self) -> None:
        rc, out = self._run_inprocess_cli(
            "verify-release-wo-card-lens-audio-meter-copyright-vault", "--clean-room"
        )
        self.assertEqual(rc, 0)
        self.assertIn(f"status={P265_STATUS_VERIFIED_PILLAR45_SUITE}", out)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", out)
        self.assertIn("pillar_45a=6/6", out)
        self.assertIn("pillar_45b=6/6", out)

    def test_63_cli_verify_release_wo_card_lens_audio_meter_copyright_vault_out_file(self) -> None:
        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p265_p45_{os.getpid()}"
        rep_file = out_dir / "pillar45-release-wo-card-lens-audio-meter-copyright-vault-report.json"
        if rep_file.is_file():
            rep_file.unlink()
        if out_dir.is_dir():
            out_dir.rmdir()
        try:
            rc, _ = self._run_inprocess_cli(
                "verify-release-wo-card-lens-audio-meter-copyright-vault",
                "--force-clean-room",
                "--out",
                str(out_dir),
            )
            self.assertEqual(rc, 0)
            self.assertTrue(rep_file.is_file())
            saved = json.loads(rep_file.read_text(encoding="utf-8"))
            self.assertTrue(saved["all_passed"])
            self.assertEqual(saved["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        finally:
            if rep_file.is_file():
                rep_file.unlink()
            if out_dir.is_dir():
                out_dir.rmdir()

    def test_64_cli_verify_release_wo_card_lens_audio_meter_copyright_vault_exit_2_on_failure(self) -> None:
        bad_suite = replace(
            run_pillar45_standalone_suite(force_clean_room=True),
            all_passed=False,
            status=P265_STATUS_FAIL_PILLAR45_SUITE,
        )
        with mock.patch.object(cli_main, "run_pillar45_standalone_suite", return_value=bad_suite):
            rc, out = self._run_inprocess_cli(
                "verify-release-wo-card-lens-audio-meter-copyright-vault", "--clean-room"
            )
        self.assertEqual(rc, 2)
        self.assertIn(f"status={P265_STATUS_FAIL_PILLAR45_SUITE}", out)

    def test_65_cli_verify_45pillar_recovery_clean_room_json_end_to_end(self) -> None:
        with mock.patch.object(
            p265, "evaluate_realhw_44pillar_recovery_master", return_value=self.master44_clean_room
        ):
            rc, out = self._run_inprocess_cli("verify-45pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillar_count"], 45)
        self.assertEqual(payload["pillars_passed"], 45)
        self.assertEqual(payload["status"], P265_STATUS_VERIFIED_45OF45_AGGREGATOR)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_66_cli_verify_45pillar_recovery_force_clean_room_human_summary(self) -> None:
        with mock.patch.object(
            cli_main, "verify_45pillar_recovery_suite", return_value=self.master45_clean_room
        ) as mocked_suite:
            rc, out = self._run_inprocess_cli("verify-45pillar-recovery", "--force-clean-room")
        self.assertEqual(rc, 0)
        mocked_suite.assert_called_once_with(force_clean_room=True)
        self.assertIn("status=VERIFIED_45OF45_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("pillars=45/45", out)
        self.assertIn("pillar45_a=6/6", out)
        self.assertIn("pillar45_b=6/6", out)

    def test_67_cli_verify_45pillar_recovery_out_file_serialization(self) -> None:
        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p265_m45_{os.getpid()}"
        rep_file = out_dir / "45pillar-recovery-master-report.json"
        if rep_file.is_file():
            rep_file.unlink()
        if out_dir.is_dir():
            out_dir.rmdir()
        try:
            with mock.patch.object(
                cli_main,
                "verify_45pillar_recovery_suite",
                return_value=self.master45_clean_room,
            ):
                rc, _ = self._run_inprocess_cli(
                    "verify-45pillar-recovery", "--json", "--out", str(out_dir)
                )
            self.assertEqual(rc, 0)
            self.assertTrue(rep_file.is_file())
            saved = json.loads(rep_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["pillar_count"], 45)
            self.assertEqual(saved["master_45pillar_sha256"], self.master45_clean_room.master_45pillar_sha256)
        finally:
            if rep_file.is_file():
                rep_file.unlink()
            if out_dir.is_dir():
                out_dir.rmdir()

    def test_68_cli_verify_45pillar_recovery_returns_2_when_failed(self) -> None:
        bad_master = replace(
            self.master45_clean_room,
            all_passed=False,
            status=P265_STATUS_FAIL_45OF45_AGGREGATOR,
            pillars_passed=44,
            failed_pillars=(MASTER_45_PILLAR_IDS[-1],),
        )
        with mock.patch.object(cli_main, "verify_45pillar_recovery_suite", return_value=bad_master):
            rc, out = self._run_inprocess_cli("verify-45pillar-recovery")
        self.assertEqual(rc, 2)
        self.assertIn("status=FAIL_45OF45_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("pillars=44/45", out)

    def test_69_cli_dispatches_phase265_and_preserves_44pillar_subcommand_routing(self) -> None:
        with mock.patch.object(
            cli_main, "verify_44pillar_recovery_suite", return_value=self.master44_clean_room
        ) as m44_fn:
            rc44, out44 = self._run_inprocess_cli("verify-44pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc44, 0)
        m44_fn.assert_called_once_with(force_clean_room=True)
        self.assertEqual(json.loads(out44)["pillar_count"], 44)

    def test_70_supported_fx3_fw_versions_200_through_702_pass_and_unknown_fw_rejected(self) -> None:
        for fw in P265_FX3_SUPPORTED_FW_VERSIONS:
            with self.subTest(fw=fw):
                ra = evaluate_release_wo_card_lens_and_audio_meter_vault(
                    ReleaseWoCardLensAndAudioMeterVaultSpec(fw_version=fw)
                )
                rb = evaluate_copyright_info_46char_exif_vault(
                    CopyrightInfo46CharExifVaultSpec(fw_version=fw)
                )
                self.assertTrue(ra.passed)
                self.assertTrue(rb.passed)

        ra_bad = evaluate_release_wo_card_lens_and_audio_meter_vault(
            ReleaseWoCardLensAndAudioMeterVaultSpec(fw_version="9.99")
        )
        rb_bad = evaluate_copyright_info_46char_exif_vault(
            CopyrightInfo46CharExifVaultSpec(fw_version="9.99")
        )
        self.assertFalse(ra_bad.passed)
        self.assertEqual(ra_bad.block_code, P265_BLOCKED_INVALID_RELEASE_WO_OR_AUDIO_METER_SPEC)
        self.assertFalse(rb_bad.passed)
        self.assertEqual(rb_bad.block_code, P265_BLOCKED_INVALID_COPYRIGHT_INFO_SPEC)


if __name__ == "__main__":
    unittest.main()
