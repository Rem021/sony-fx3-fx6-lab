"""Phase 260 (`260th` Phase Milestone) — Dual-mode unit tests for Pillar 44 (`[APS-C S35 Shooting]`
`12.1MP` sensor `4K` movie & `4264x2408` `HDMI RAW Output` lockout, `[Camera Settings Reset]` vs
`[Reset Network Set.]` scope; `[Face/Eye AF]` BIONZ XR hierarchy vs dedicated AI-unit
`[Subject Recog in AF]` spoof rejection, `[Face/Eye Prior. in AF]` `[Intelligent Auto]` lock,
`[Face/Eye Subject]` `Ver. 3.00+` `Bird` gate, `[Right/Left Eye Select]` & `[Switch Right/Left Eye]`
custom key toggle, `[Face/Eye Frame Disp.]` Clean-HDMI isolation & `[Face Memory]` survival; plus
`[Version]` strictly `O_RDONLY` Body/Lens/Mount-Adaptor inspection, zero-RF `Airplane Mode = On`
update badge suppression, hard-blocked Slot-1 `BODYDATA.DAT` flash vault guard, and `O_RDONLY`
`CAMSET01.DAT` round-trip) and unified `44/44` recovery master (`verify-44pillar-recovery` /
`verify-apsc-s35-face-eye-af-version-vault`)."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import (
    realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier as p260,
)
from fx3_recovery.realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier import (
    MASTER_43_PILLAR_SPECS,
    Master43PillarRecoveryReport,
    evaluate_realhw_43pillar_recovery_master,
)
from fx3_recovery.realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_44_PILLAR_COUNT,
    MASTER_44_PILLAR_IDS,
    MASTER_44_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P260_AF_AREA_AUTO_CLEAR_MODES,
    P260_AI_UNIT_SUBJECT_RECOG_SPOOF_EVENTS,
    P260_AIRPLANE_MODES,
    P260_AIRPLANE_MODE_MENU_PATH,
    P260_APSC_S35_4K_OR_RAW_BYPASS_EVENTS,
    P260_APSC_S35_DEFAULT,
    P260_APSC_S35_MENU_PATH,
    P260_APSC_S35_MODES,
    P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT,
    P260_BLOCKED_APSC_OR_FACE_MEMORY_RESET_SCOPE_DRIFT,
    P260_BLOCKED_APSC_S35_4K_OR_RAW_LOCKOUT_BYPASS,
    P260_BLOCKED_AUTOMATED_BODYDATA_FLASH_EXECUTION,
    P260_BLOCKED_HDMI_CLEAN_FEED_EYE_FRAME_LEAK,
    P260_BLOCKED_INVALID_APSC_S35_OR_FACE_EYE_AF_SPEC,
    P260_BLOCKED_INVALID_VERSION_OR_BODYDATA_VAULT_SPEC,
    P260_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P260_BLOCKED_SAFETY_POLICY_VIOLATION,
    P260_BLOCKED_SLOT1_BODYDATA_VAULT_MUTATION_OR_CAMSET_DRIFT,
    P260_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P260_BLOCKED_UNSUPPRESSED_UPDATE_BADGE_OR_RF_LEAK,
    P260_BLOCKED_VERSION_DIALOG_WRITE_OR_IMMUTABILITY_DRIFT,
    P260_BODYDATA_FILENAME,
    P260_CAMSET_FILENAMES,
    P260_DEFAULT_BODYDATA_FLASH_ATTEMPTS_BLOCKED,
    P260_EFFECTIVE_ANGLE_OF_VIEW_MODES,
    P260_FACE_EYE_AF_MENU_PATH,
    P260_FACE_EYE_FRAME_DISP_DEFAULT,
    P260_FACE_EYE_FRAME_DISP_MODES,
    P260_FACE_EYE_PRIOR_DEFAULT,
    P260_FACE_EYE_PRIOR_MODES,
    P260_FACE_EYE_SUBJECTS,
    P260_FACE_EYE_SUBJECT_DEFAULT,
    P260_FORBIDDEN_AI_UNIT_MENU_NAME,
    P260_FORBIDDEN_AI_UNIT_SUBJECTS,
    P260_FX3_BIRD_EYE_MIN_FW_VERSIONS,
    P260_FX3_FW_VERSION,
    P260_FX3_HELPGUIDE_ID,
    P260_FX3_MODEL_ID,
    P260_FX3_MODEL_NAME,
    P260_FX3_MOVIE_4K_READOUT_RES,
    P260_FX3_SENSOR_EFFECTIVE_MP,
    P260_FX3_STILL_FULLFRAME_RES,
    P260_FX3_SUPPORTED_FW_VERSIONS,
    P260_FX3_UPDATE_BADGE_MIN_FW_VERSIONS,
    P260_FX6_DONOR_FW_VERSION,
    P260_FX6_DONOR_MODEL_NAME,
    P260_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P260_HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS,
    P260_HDMI_INFO_DISPLAY_MODES,
    P260_HDMI_RAW_4264X2408_RESOLUTION,
    P260_HDMI_RAW_OUTPUT_MODES,
    P260_HUMAN_BENCH_MIN_BATTERY_BARS,
    P260_HUMAN_BENCH_MIN_BATTERY_PCT,
    P260_LENS_IMAGE_CIRCLE_TYPES,
    P260_MAX_FACE_MEMORY_ENTRIES,
    P260_MOVIE_FILE_FORMATS,
    P260_MOVIE_FILE_FORMATS_4K,
    P260_MOVIE_FILE_FORMATS_HD,
    P260_NON_FX3_S35_4K_MODELS,
    P260_PILLAR_44A_SCENARIO_IDS,
    P260_PILLAR_44B_SCENARIO_IDS,
    P260_PINNED_FX3_BACKUP_BIN_SHA256,
    P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
    P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
    P260_PINNED_FX3_LIBINFRAGETVERSION_SO_BYTES,
    P260_PINNED_FX3_LIBINFRAGETVERSION_SO_SHA256,
    P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
    P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
    P260_PINNED_FX3_LIBUPDATERMEDIA_SO_BYTES,
    P260_PINNED_FX3_LIBUPDATERMEDIA_SO_SHA256,
    P260_RESET_ACTIONS,
    P260_RIGHT_LEFT_EYE_SELECT_DEFAULT,
    P260_RIGHT_LEFT_EYE_SELECT_MODES,
    P260_SHOOTING_DOMAINS,
    P260_SHOOTING_EXPOSURE_PROFILES,
    P260_SLOT1_BODYDATA_VAULT_MUTATION_BYTES,
    P260_SLOT1_VAULT_SLOT,
    P260_STATUS_FAIL_44OF44_AGGREGATOR,
    P260_STATUS_FAIL_PILLAR44_SUITE,
    P260_STATUS_VERIFIED_44OF44_AGGREGATOR,
    P260_STATUS_VERIFIED_PILLAR44_SUITE,
    P260_STATUS_VERIFIED_PILLAR_44A,
    P260_STATUS_VERIFIED_PILLAR_44B,
    P260_VERSION_DIALOG_FLASH_WRITES,
    P260_VERSION_MENU_PATH,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE260_MILESTONE_NUMBER,
    PHASE260_SCHEMA,
    PHASE260_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    ApscS35AndFaceEyeAfVaultSpec,
    Master44PillarRecoveryReport,
    VersionReadOnlyAndBodydataVaultSpec,
    build_default_safe_apsc_s35_face_eye_af_vault_spec,
    build_default_safe_version_readonly_bodydata_vault_spec,
    compute_expected_apsc_s35_movie_or_still_state,
    evaluate_44pillar_recovery_master,
    evaluate_apsc_s35_and_face_eye_af_vault,
    evaluate_realhw_44pillar_recovery_master,
    evaluate_version_readonly_and_bodydata_vault,
    inspect_phase260_donors_readonly,
    run_pillar44_standalone_suite,
    run_pillar44a_apsc_s35_face_eye_af_vault_6_scenario_suite,
    run_pillar44b_version_readonly_bodydata_vault_6_scenario_suite,
    verify_44pillar_recovery_suite,
    verify_apsc_s35_face_eye_af_and_version_vault,
    verify_apsc_s35_face_eye_af_version_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]


def _run_inprocess_cli(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with mock.patch.object(sys, "argv", ["fx3_recovery", *argv]), redirect_stdout(buf):
        rc = cli_main.main()
    return rc, buf.getvalue()


class TestPhase260Pillar44And44PillarRecoveryMaster(unittest.TestCase):
    """68 fast dual-mode tests covering Pillar 44A, Pillar 44B, O_RDONLY donors, CLI & 44/44 master."""

    master44_default: Master44PillarRecoveryReport
    master44_clean_room: Master44PillarRecoveryReport
    master43_clean_room: Master43PillarRecoveryReport

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.master44_default = evaluate_realhw_44pillar_recovery_master()
        cls.master44_clean_room = evaluate_realhw_44pillar_recovery_master(force_clean_room=True)
        cls.master43_clean_room = evaluate_realhw_43pillar_recovery_master(force_clean_room=True)

    def test_01_hard_locked_safety_and_zero_write_constants(self) -> None:
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
        self.assertFalse(P260_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(P260_APSC_S35_4K_OR_RAW_BYPASS_EVENTS, 0)
        self.assertEqual(P260_AI_UNIT_SUBJECT_RECOG_SPOOF_EVENTS, 0)
        self.assertEqual(P260_HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS, 0)
        self.assertEqual(P260_VERSION_DIALOG_FLASH_WRITES, 0)
        self.assertGreaterEqual(P260_DEFAULT_BODYDATA_FLASH_ATTEMPTS_BLOCKED, 1)
        self.assertEqual(P260_SLOT1_BODYDATA_VAULT_MUTATION_BYTES, 0)

    def test_02_schema_milestone_260_and_wave42_hardware_constants(self) -> None:
        self.assertEqual(
            PHASE260_SCHEMA,
            "realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier_v1",
        )
        self.assertEqual(PHASE260_VERSION, "1.0.0")
        self.assertEqual(PHASE260_MILESTONE_NUMBER, 260)
        self.assertEqual(P260_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P260_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P260_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P260_FX3_FW_VERSION, "7.02")
        self.assertEqual(P260_FX3_SENSOR_EFFECTIVE_MP, "12.1MP")
        self.assertEqual(P260_FX3_STILL_FULLFRAME_RES, "4240x2832")
        self.assertEqual(P260_FX3_MOVIE_4K_READOUT_RES, "3840x2160")
        self.assertEqual(P260_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P260_FX6_DONOR_FW_VERSION, "6.01")

    def test_03_package_reexports_all_phase260_symbols_cleanly(self) -> None:
        self.assertIs(
            fx3_recovery.realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier,
            p260,
        )
        for name in p260.__all__:
            self.assertTrue(hasattr(fx3_recovery, name), f"Missing {name} on fx3_recovery")
        self.assertIn("evaluate_realhw_44pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("verify_44pillar_recovery_suite", fx3_recovery.__all__)
        self.assertIn("verify_apsc_s35_face_eye_af_version_vault", fx3_recovery.__all__)

    def test_04_donor_inspection_readonly_13_artifacts_under_budget(self) -> None:
        snap = inspect_phase260_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 13)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertLess(snap.elapsed_seconds, 2.0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(
            by_id["fx3_libinfragetversion_so"].total_bytes,
            P260_PINNED_FX3_LIBINFRAGETVERSION_SO_BYTES,
        )
        self.assertEqual(
            by_id["fx3_libinfragetversion_so"].digest_sha256,
            P260_PINNED_FX3_LIBINFRAGETVERSION_SO_SHA256,
        )
        self.assertIn("InfraGetVersion", by_id["fx3_libinfragetversion_so"].marker_summary)
        self.assertEqual(
            by_id["fx3_libinfraairplanemode_so"].total_bytes,
            P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
        )
        self.assertEqual(
            by_id["fx3_libinfraairplanemode_so"].digest_sha256,
            P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
        )
        self.assertEqual(
            by_id["fx3_libupdatermedia_so"].total_bytes,
            P260_PINNED_FX3_LIBUPDATERMEDIA_SO_BYTES,
        )
        self.assertEqual(
            by_id["fx3_libupdatermedia_so"].digest_sha256,
            P260_PINNED_FX3_LIBUPDATERMEDIA_SO_SHA256,
        )
        self.assertEqual(
            by_id["fx3_libinfralenscommunicator_so"].total_bytes,
            P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
        )
        self.assertEqual(
            by_id["fx3_libinfralenscommunicator_so"].digest_sha256,
            P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
        )

    def test_05_clean_room_synthetic_and_missing_donor_fallback_parity(self) -> None:
        snap_cr = inspect_phase260_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_cr.all_donors_present)
        self.assertEqual(snap_cr.donor_files_inspected, 13)
        self.assertTrue(all(a.matches_pinned for a in snap_cr.artifacts))

        with mock.patch.object(p260, "resolve_donor_path", return_value=None):
            snap_fb = inspect_phase260_donors_readonly(force_clean_room=False)
        self.assertEqual(snap_fb.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap_fb.donor_files_inspected, 13)
        self.assertTrue(snap_fb.all_donors_present)

    def test_06_elf64_aarch64_token_helper_rejects_malformed_headers_and_missing_tokens(self) -> None:
        ok0, msg0 = p260._check_elf64_aarch64_tokens(b"NOT_AN_ELF", (b"InfraGetVersion",))
        self.assertFalse(ok0)
        self.assertEqual(msg0, "NOT_ELF")

        bad_mach = bytearray(64)
        bad_mach[:4] = b"\x7fELF"
        bad_mach[4] = 2
        bad_mach[5] = 1
        struct.pack_into("<H", bad_mach, 18, 62)  # x86_64 instead of 183 AArch64
        ok1, msg1 = p260._check_elf64_aarch64_tokens(bytes(bad_mach), ())
        self.assertFalse(ok1)
        self.assertIn("BAD_ELF64_AARCH64", msg1)

        good_hdr = bytearray(64)
        good_hdr[:4] = b"\x7fELF"
        good_hdr[4] = 2
        good_hdr[5] = 1
        struct.pack_into("<H", good_hdr, 18, 183)
        ok2, msg2 = p260._check_elf64_aarch64_tokens(bytes(good_hdr) + b"InfraGetVersion", (b"MissingTok",))
        self.assertFalse(ok2)
        self.assertIn("MISSING_TOKENS:MissingTok", msg2)

    def test_07_default_safe_pillar44a_spec_passes_all_invariants(self) -> None:
        spec = build_default_safe_apsc_s35_face_eye_af_vault_spec()
        rep = evaluate_apsc_s35_and_face_eye_af_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P260_STATUS_VERIFIED_PILLAR_44A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.reset_and_face_memory_scope_verified)
        self.assertTrue(rep.apsc_s35_12mp_4k_raw_lockout_verified)
        self.assertTrue(rep.face_eye_af_bionz_xr_rules_verified)
        self.assertTrue(rep.clean_hdmi_eye_frame_isolation_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertFalse(rep.apsc_s35_locked_off)
        self.assertEqual(rep.effective_angle_of_view, "Super35_1.5x")
        self.assertEqual(rep.apsc_s35_4k_or_raw_bypass_events, 0)
        self.assertEqual(rep.ai_unit_subject_recog_spoof_events, 0)
        self.assertEqual(rep.hdmi_clean_feed_eye_frame_baked_pixels, 0)

    def test_08_exhaustive_12_1mp_apsc_s35_cartesian_state_space_lockout_proof(self) -> None:
        combos = 0
        for domain in P260_SHOOTING_DOMAINS:
            for fmt in P260_MOVIE_FILE_FORMATS:
                for raw_out in P260_HDMI_RAW_OUTPUT_MODES:
                    for cfg in P260_APSC_S35_MODES:
                        for circle in P260_LENS_IMAGE_CIRCLE_TYPES:
                            combos += 1
                            locked, eff_mode, fov = compute_expected_apsc_s35_movie_or_still_state(
                                shooting_domain=domain,
                                movie_file_format=fmt,
                                hdmi_raw_output_4264x2408=raw_out,
                                configured_apsc_s35=cfg,
                                lens_image_circle=circle,
                            )
                            if domain in ("Movie", "S&Q") and (
                                fmt in P260_MOVIE_FILE_FORMATS_4K or raw_out == "On"
                            ):
                                self.assertTrue(locked)
                                self.assertEqual(eff_mode, "Off")
                                self.assertEqual(fov, "Full-Frame_1.0x")
                            else:
                                self.assertFalse(locked)
                                self.assertEqual(eff_mode, cfg)
                                if cfg == "On" or (cfg == "Auto" and circle == "APS-C"):
                                    self.assertEqual(fov, "Super35_1.5x")
                                else:
                                    self.assertEqual(fov, "Full-Frame_1.0x")
        self.assertEqual(combos, 180)

    def test_09_rejects_apsc_s35_bypass_in_all_three_4k_movie_formats(self) -> None:
        for fmt_4k in P260_MOVIE_FILE_FORMATS_4K:
            with self.subTest(fmt=fmt_4k):
                rep = evaluate_apsc_s35_and_face_eye_af_vault(
                    ApscS35AndFaceEyeAfVaultSpec(
                        shooting_domain="Movie",
                        movie_file_format=fmt_4k,
                        hdmi_raw_output_4264x2408="Off",
                        apsc_s35_locked_off=False,
                        effective_apsc_s35_mode="On",
                        effective_angle_of_view="Super35_1.5x",
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P260_BLOCKED_APSC_S35_4K_OR_RAW_LOCKOUT_BYPASS)
                self.assertGreaterEqual(rep.apsc_s35_4k_or_raw_bypass_events, 1)

    def test_10_rejects_apsc_s35_bypass_during_4264x2408_hdmi_raw_output_even_in_hd_format(self) -> None:
        rep = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                shooting_domain="Movie",
                movie_file_format="XAVC S HD",
                hdmi_raw_output_4264x2408="On",
                apsc_s35_locked_off=False,
                effective_apsc_s35_mode="On",
                effective_angle_of_view="Super35_1.5x",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P260_BLOCKED_APSC_S35_4K_OR_RAW_LOCKOUT_BYPASS)

    def test_11_rejects_cross_model_fx30_and_oversampled_alpha_s35_4k_spoofing(self) -> None:
        for non_fx3 in P260_NON_FX3_S35_4K_MODELS:
            with self.subTest(camera_model=non_fx3):
                rep = evaluate_apsc_s35_and_face_eye_af_vault(
                    ApscS35AndFaceEyeAfVaultSpec(camera_model=non_fx3)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P260_BLOCKED_APSC_S35_4K_OR_RAW_LOCKOUT_BYPASS)

    def test_12_still_domain_apsc_s35_auto_on_off_with_ff_and_apsc_lenses(self) -> None:
        r_auto_apsc = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                pre_reset_apsc_s35="Auto",
                post_reset_apsc_s35="Auto",
                shooting_domain="Still",
                movie_file_format="XAVC S-I 4K",
                lens_mount_model="SEL1655G",
                lens_image_circle="APS-C",
                apsc_s35_locked_off=False,
                effective_apsc_s35_mode="Auto",
                effective_angle_of_view="Super35_1.5x",
            )
        )
        self.assertTrue(r_auto_apsc.passed)

        r_auto_ff = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                pre_reset_apsc_s35="Auto",
                post_reset_apsc_s35="Auto",
                shooting_domain="Still",
                lens_image_circle="FF",
                apsc_s35_locked_off=False,
                effective_apsc_s35_mode="Auto",
                effective_angle_of_view="Full-Frame_1.0x",
            )
        )
        self.assertTrue(r_auto_ff.passed)

    def test_13_face_eye_af_rejects_ai_unit_subject_recog_menu_and_subjects(self) -> None:
        self.assertEqual(P260_FACE_EYE_AF_MENU_PATH, ("MENU", "Focus", "Face/Eye AF"))
        self.assertEqual(P260_FORBIDDEN_AI_UNIT_MENU_NAME, "Subject Recog in AF")
        r_menu = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                face_eye_af_menu_path=("MENU", "Focus", "Subject Recog in AF")
            )
        )
        self.assertFalse(r_menu.passed)
        self.assertEqual(r_menu.block_code, P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT)
        self.assertGreaterEqual(r_menu.ai_unit_subject_recog_spoof_events, 1)

        for ai_subj in P260_FORBIDDEN_AI_UNIT_SUBJECTS:
            with self.subTest(ai_subj=ai_subj):
                r_subj = evaluate_apsc_s35_and_face_eye_af_vault(
                    ApscS35AndFaceEyeAfVaultSpec(
                        pre_face_eye_subject=ai_subj,
                        post_face_eye_subject=ai_subj,
                    )
                )
                self.assertFalse(r_subj.passed)
                self.assertEqual(
                    r_subj.block_code,
                    P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT,
                )

    def test_14_face_eye_subject_bird_firmware_boundary_3_00_plus_vs_2_xx(self) -> None:
        for ver in P260_FX3_BIRD_EYE_MIN_FW_VERSIONS:
            with self.subTest(fw_version=ver):
                self.assertTrue(
                    evaluate_apsc_s35_and_face_eye_af_vault(
                        ApscS35AndFaceEyeAfVaultSpec(fw_version=ver)
                    ).passed
                )
        for pre_ver in ("2.00", "2.01", "2.02"):
            with self.subTest(pre_ver=pre_ver):
                r_bad_bird = evaluate_apsc_s35_and_face_eye_af_vault(
                    ApscS35AndFaceEyeAfVaultSpec(fw_version=pre_ver)
                )
                self.assertFalse(r_bad_bird.passed)
                self.assertEqual(
                    r_bad_bird.block_code,
                    P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT,
                )
                r_ok_animal = evaluate_apsc_s35_and_face_eye_af_vault(
                    ApscS35AndFaceEyeAfVaultSpec(
                        fw_version=pre_ver,
                        pre_face_eye_subject="Animal",
                        saved_face_eye_subject="Animal",
                        post_face_eye_subject="Animal",
                    )
                )
                self.assertTrue(r_ok_animal.passed)

    def test_15_intelligent_auto_locks_face_eye_prior_in_af_to_on(self) -> None:
        r_ok = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                exposure_profile="Intelligent Auto",
                pre_face_eye_prior_in_af="Off",
                post_face_eye_prior_in_af="On",
            )
        )
        self.assertTrue(r_ok.passed)

        r_bad = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                exposure_profile="Intelligent Auto",
                pre_face_eye_prior_in_af="Off",
                post_face_eye_prior_in_af="Off",
                lcd_eye_frame_rendered_before_lock=False,
                lcd_eye_frame_visible_after_lock=False,
            )
        )
        self.assertFalse(r_bad.passed)
        self.assertEqual(r_bad.block_code, P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT)

    def test_16_right_left_eye_select_and_switch_custom_key_toggle_rules(self) -> None:
        self.assertEqual(P260_RIGHT_LEFT_EYE_SELECT_MODES, ("Auto", "Right Eye", "Left Eye"))
        self.assertEqual(P260_RIGHT_LEFT_EYE_SELECT_DEFAULT, "Auto")
        for start_eye, toggled_eye in (
            ("Right Eye", "Left Eye"),
            ("Left Eye", "Right Eye"),
            ("Auto", "Right Eye"),
        ):
            with self.subTest(start_eye=start_eye):
                r_ok = evaluate_apsc_s35_and_face_eye_af_vault(
                    ApscS35AndFaceEyeAfVaultSpec(
                        pre_right_left_eye_select=start_eye,
                        post_right_left_eye_select=start_eye,
                        switch_right_left_eye_custom_key_pressed=True,
                        active_eye_target_after_custom_key=toggled_eye,
                    )
                )
                self.assertTrue(r_ok.passed)

        r_bad_toggle = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                pre_right_left_eye_select="Right Eye",
                post_right_left_eye_select="Right Eye",
                switch_right_left_eye_custom_key_pressed=True,
                active_eye_target_after_custom_key="Right Eye",
            )
        )
        self.assertFalse(r_bad_toggle.passed)
        self.assertEqual(
            r_bad_toggle.block_code,
            P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT,
        )

    def test_17_face_eye_frame_disp_and_af_area_auto_clear_after_focus_lock(self) -> None:
        self.assertEqual(P260_AF_AREA_AUTO_CLEAR_MODES, ("Off", "On"))
        r_clear = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                af_area_auto_clear="On",
                focus_locked=True,
                lcd_eye_frame_rendered_before_lock=True,
                lcd_eye_frame_visible_after_lock=False,
            )
        )
        self.assertTrue(r_clear.passed)

        r_bad_clear = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                af_area_auto_clear="On",
                focus_locked=True,
                lcd_eye_frame_rendered_before_lock=True,
                lcd_eye_frame_visible_after_lock=True,
            )
        )
        self.assertFalse(r_bad_clear.passed)
        self.assertEqual(
            r_bad_clear.block_code,
            P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT,
        )

    def test_18_clean_hdmi_isolation_vs_hdmi_info_display_on_mirroring(self) -> None:
        self.assertEqual(P260_HDMI_INFO_DISPLAY_MODES, ("On", "Off"))
        r_info_on = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                hdmi_connected=True,
                hdmi_info_display="On",
                hdmi_raw_output_4264x2408="Off",
                hdmi_eye_frame_rendered=True,
                hdmi_clean_feed_eye_frame_baked_pixels=0,
            )
        )
        self.assertTrue(r_info_on.passed)

        r_raw_on = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                hdmi_connected=True,
                hdmi_info_display="On",
                hdmi_raw_output_4264x2408="On",
                apsc_s35_locked_off=True,
                effective_apsc_s35_mode="Off",
                effective_angle_of_view="Full-Frame_1.0x",
                hdmi_eye_frame_rendered=False,
                hdmi_clean_feed_eye_frame_baked_pixels=0,
            )
        )
        self.assertTrue(r_raw_on.passed)

    def test_19_rejects_eye_frame_overlay_baked_into_clean_hdmi_or_raw_output(self) -> None:
        r_leak = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                hdmi_connected=True,
                hdmi_info_display="Off",
                hdmi_eye_frame_rendered=True,
                hdmi_clean_feed_eye_frame_baked_pixels=640,
            )
        )
        self.assertFalse(r_leak.passed)
        self.assertEqual(r_leak.block_code, P260_BLOCKED_HDMI_CLEAN_FEED_EYE_FRAME_LEAK)
        self.assertEqual(r_leak.hdmi_clean_feed_eye_frame_baked_pixels, 640)

    def test_20_camera_settings_reset_resets_menu_items_while_preserving_face_memory(self) -> None:
        self.assertEqual(P260_APSC_S35_DEFAULT, "Auto")
        self.assertEqual(P260_FACE_EYE_PRIOR_DEFAULT, "On")
        self.assertEqual(P260_FACE_EYE_SUBJECT_DEFAULT, "Human")
        self.assertEqual(P260_FACE_EYE_FRAME_DISP_DEFAULT, "Off")
        self.assertEqual(P260_MAX_FACE_MEMORY_ENTRIES, 8)
        r_csr = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                pre_reset_apsc_s35="On",
                pre_face_eye_prior_in_af="Off",
                pre_face_eye_subject="Bird",
                pre_right_left_eye_select="Left Eye",
                pre_face_eye_frame_disp="On",
                pre_face_memory_registered_count=6,
                reset_action="Camera Settings Reset",
                post_reset_apsc_s35="Auto",
                post_face_eye_prior_in_af="On",
                post_face_eye_subject="Human",
                post_right_left_eye_select="Auto",
                post_face_eye_frame_disp="Off",
                post_face_memory_registered_count=6,
                effective_apsc_s35_mode="Auto",
                effective_angle_of_view="Full-Frame_1.0x",
                active_eye_target_after_custom_key="Auto",
                lcd_eye_frame_rendered_before_lock=False,
                lcd_eye_frame_visible_after_lock=False,
            )
        )
        self.assertTrue(r_csr.passed)

    def test_21_initialize_and_explicit_delete_clear_face_memory_to_zero(self) -> None:
        r_init = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                pre_face_memory_registered_count=5,
                reset_action="Initialize",
                post_reset_apsc_s35="Auto",
                post_face_eye_prior_in_af="On",
                post_face_eye_subject="Human",
                post_right_left_eye_select="Auto",
                post_face_eye_frame_disp="Off",
                post_face_memory_registered_count=0,
                effective_apsc_s35_mode="Auto",
                effective_angle_of_view="Full-Frame_1.0x",
                active_eye_target_after_custom_key="Auto",
                lcd_eye_frame_rendered_before_lock=False,
                lcd_eye_frame_visible_after_lock=False,
            )
        )
        self.assertTrue(r_init.passed)

        r_del = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                pre_face_memory_registered_count=5,
                explicit_face_memory_delete=True,
                post_face_memory_registered_count=0,
            )
        )
        self.assertTrue(r_del.passed)

    def test_22_rejects_camera_settings_reset_wiping_face_memory_or_keeping_stale_apsc(self) -> None:
        r_wiped = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(
                pre_face_memory_registered_count=4,
                reset_action="Camera Settings Reset",
                post_reset_apsc_s35="Auto",
                post_face_eye_prior_in_af="On",
                post_face_eye_subject="Human",
                post_right_left_eye_select="Auto",
                post_face_eye_frame_disp="Off",
                post_face_memory_registered_count=0,
                effective_apsc_s35_mode="Auto",
                effective_angle_of_view="Full-Frame_1.0x",
                active_eye_target_after_custom_key="Auto",
                lcd_eye_frame_rendered_before_lock=False,
                lcd_eye_frame_visible_after_lock=False,
            )
        )
        self.assertFalse(r_wiped.passed)
        self.assertEqual(r_wiped.block_code, P260_BLOCKED_APSC_OR_FACE_MEMORY_RESET_SCOPE_DRIFT)

    def test_23_pillar44a_rejects_persistent_overlay_escape_and_unlock_request(self) -> None:
        r_ov = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(overlay_dir="/setting/apsc_escape")
        )
        self.assertFalse(r_ov.passed)
        self.assertEqual(r_ov.block_code, P260_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        r_ul = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(r_ul.passed)
        self.assertEqual(r_ul.block_code, P260_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_24_pillar44a_rejects_tier0_backup_bin_drift_and_invalid_spec_tokens(self) -> None:
        r_h3 = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(backup_bin_h3_sha256="0" * 64)
        )
        self.assertFalse(r_h3.passed)
        self.assertEqual(r_h3.block_code, P260_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        r_inv = evaluate_apsc_s35_and_face_eye_af_vault(
            ApscS35AndFaceEyeAfVaultSpec(apsc_s35_menu_path=("MENU", "Wrong", "Path"))
        )
        self.assertFalse(r_inv.passed)
        self.assertEqual(r_inv.block_code, P260_BLOCKED_INVALID_APSC_S35_OR_FACE_EYE_AF_SPEC)

    def test_25_pillar44a_6_scenario_suite_passes_all_6_scenarios(self) -> None:
        res = run_pillar44a_apsc_s35_face_eye_af_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P260_STATUS_VERIFIED_PILLAR_44A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P260_PILLAR_44A_SCENARIO_IDS)
        self.assertEqual(
            [s.expected_allowed for s in res.scenarios],
            [True, True, False, False, False, False],
        )

    def test_26_default_safe_pillar44b_spec_passes_all_invariants(self) -> None:
        spec = build_default_safe_version_readonly_bodydata_vault_spec()
        rep = evaluate_version_readonly_and_bodydata_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P260_STATUS_VERIFIED_PILLAR_44B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.version_readonly_and_immutability_verified)
        self.assertTrue(rep.zero_rf_update_badge_suppression_verified)
        self.assertTrue(rep.bodydata_flash_hard_block_verified)
        self.assertTrue(rep.slot1_vault_and_camset_roundtrip_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.version_dialog_flash_writes, 0)
        self.assertGreaterEqual(rep.bodydata_flash_attempts_blocked, 1)
        self.assertEqual(rep.slot1_bodydata_vault_mutation_bytes, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_27_version_readonly_body_lens_and_mount_adaptor_immutability_across_all_resets(self) -> None:
        self.assertEqual(P260_VERSION_MENU_PATH, ("MENU", "Setup", "Setup Option", "Version"))
        for rst in P260_RESET_ACTIONS:
            with self.subTest(reset_action=rst):
                rep = evaluate_version_readonly_and_bodydata_vault(
                    VersionReadOnlyAndBodydataVaultSpec(
                        attached_lens_model="SEL70200GM2",
                        attached_lens_fw_version="04",
                        displayed_lens_fw_version="04",
                        post_reset_lens_fw_version="04",
                        attached_mount_adaptor_model="LA-EA5",
                        attached_mount_adaptor_fw_version="02",
                        displayed_mount_adaptor_fw_version="02",
                        post_reset_mount_adaptor_fw_version="02",
                        reset_action=rst,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertEqual(rep.version_dialog_flash_writes, 0)

    def test_28_rejects_version_dialog_flash_writes_ordwr_mode_or_fw_reset_mutation(self) -> None:
        for kw in (
            {"version_dialog_open_mode": "O_RDWR"},
            {"version_dialog_flash_writes": 1},
            {"displayed_body_fw_version": "6.00"},
            {"displayed_lens_fw_version": "99"},
            {"post_reset_body_fw_version": "2.00"},
            {"post_reset_mount_adaptor_fw_version": "01"},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_version_readonly_and_bodydata_vault(
                    VersionReadOnlyAndBodydataVaultSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code,
                    P260_BLOCKED_VERSION_DIALOG_WRITE_OR_IMMUTABILITY_DRIFT,
                )
                self.assertGreaterEqual(rep.version_dialog_flash_writes, 1)

    def test_29_zero_rf_airplane_mode_suppresses_update_badge_across_6_00_to_7_02(self) -> None:
        self.assertEqual(P260_AIRPLANE_MODE_MENU_PATH, ("MENU", "Network", "Network Option", "Airplane Mode"))
        self.assertEqual(P260_AIRPLANE_MODES, ("On", "Off"))
        self.assertEqual(P260_FX3_UPDATE_BADGE_MIN_FW_VERSIONS, ("6.00", "6.02", "7.00", "7.01", "7.02"))
        for ver in P260_FX3_UPDATE_BADGE_MIN_FW_VERSIONS:
            with self.subTest(fw_version=ver):
                rep = evaluate_version_readonly_and_bodydata_vault(
                    VersionReadOnlyAndBodydataVaultSpec(
                        fw_version=ver,
                        displayed_body_fw_version=ver,
                        post_reset_body_fw_version=ver,
                        airplane_mode="On",
                        rf_interfaces_disabled=True,
                        update_notification_badge_suppressed=True,
                        red_update_badge_displayed=False,
                        version_dialog_passive_tx_bytes=0,
                    )
                )
                self.assertTrue(rep.passed)

    def test_30_rejects_unsuppressed_update_badge_airplane_off_or_passive_rf_probe(self) -> None:
        for kw in (
            {"airplane_mode": "Off"},
            {"rf_interfaces_disabled": False},
            {"update_notification_badge_suppressed": False},
            {"red_update_badge_displayed": True},
            {"version_dialog_passive_tx_bytes": 128},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_version_readonly_and_bodydata_vault(
                    VersionReadOnlyAndBodydataVaultSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P260_BLOCKED_UNSUPPRESSED_UPDATE_BADGE_OR_RF_LEAK)

    def test_31_hard_blocks_multiple_automated_slot1_bodydata_flash_attempts(self) -> None:
        self.assertEqual(P260_BODYDATA_FILENAME, "BODYDATA.DAT")
        for blocked_cnt in (1, 2, 5):
            with self.subTest(blocked_cnt=blocked_cnt):
                rep = evaluate_version_readonly_and_bodydata_vault(
                    VersionReadOnlyAndBodydataVaultSpec(
                        automated_bodydata_update_requested=True,
                        automated_bodydata_update_hard_blocked=True,
                        bodydata_flash_executed=False,
                        bodydata_flash_attempts_blocked=blocked_cnt,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertEqual(rep.bodydata_flash_attempts_blocked, blocked_cnt)

    def test_32_rejects_automated_bodydata_flash_execution_or_unblocked_update(self) -> None:
        for kw in (
            {"bodydata_flash_executed": True},
            {"automated_bodydata_update_hard_blocked": False},
            {"automated_bodydata_update_requested": True, "bodydata_flash_attempts_blocked": 0},
            {"slot1_bodydata_filename": "WRONGNAME.DAT"},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_version_readonly_and_bodydata_vault(
                    VersionReadOnlyAndBodydataVaultSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P260_BLOCKED_AUTOMATED_BODYDATA_FLASH_EXECUTION)

    def test_33_human_bench_precheck_boundary_np_fz100_3bars_51pct_and_sony_signature(self) -> None:
        self.assertEqual(P260_HUMAN_BENCH_MIN_BATTERY_BARS, 3)
        self.assertEqual(P260_HUMAN_BENCH_MIN_BATTERY_PCT, 51)
        # Exactly 3 bars / 51% passes human precheck claim while automated flash remains blocked
        r_min_ok = evaluate_version_readonly_and_bodydata_vault(
            VersionReadOnlyAndBodydataVaultSpec(
                np_fz100_battery_bars=3,
                np_fz100_battery_pct=51,
                human_bench_precheck_claimed_ready=True,
            )
        )
        self.assertTrue(r_min_ok.passed)

        # Low battery (2 bars or 50%), FX6 cross-model BODYDATA.DAT, or broken signature cannot claim ready
        for bad_kw in (
            {"np_fz100_battery_bars": 2, "np_fz100_battery_pct": 80, "human_bench_precheck_claimed_ready": True},
            {"np_fz100_battery_bars": 3, "np_fz100_battery_pct": 50, "human_bench_precheck_claimed_ready": True},
            {"bodydata_target_model": "ILME-FX6", "human_bench_precheck_claimed_ready": True},
            {"bodydata_sony_signature_intact": False, "human_bench_precheck_claimed_ready": True},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_version_readonly_and_bodydata_vault(
                    VersionReadOnlyAndBodydataVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P260_BLOCKED_AUTOMATED_BODYDATA_FLASH_EXECUTION)

    def test_34_slot1_vault_guard_rejects_mutation_wp_unlock_save_or_fx6_camset(self) -> None:
        for bad_kw in (
            {"slot1_bodydata_vault_mutation_bytes": 512},
            {"slot1_tier0_vault_active": True, "slot1_sdxc_wp_locked": False},
            {"slot1_tier0_vault_active": True, "camset_save_to_slot1_attempted": True},
            {"camset_load_after_reset": True, "camset_read_only_load": False},
            {"camset_load_after_reset": True, "camset_source_model": "ILME-FX6"},
            {"camset_load_after_reset": True, "camset_roundtrip_restored_ok": False},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_version_readonly_and_bodydata_vault(
                    VersionReadOnlyAndBodydataVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code,
                    P260_BLOCKED_SLOT1_BODYDATA_VAULT_MUTATION_OR_CAMSET_DRIFT,
                )

    def test_35_pillar44b_rejects_overlay_escape_tier0_drift_and_invalid_spec(self) -> None:
        r_ov = evaluate_version_readonly_and_bodydata_vault(
            VersionReadOnlyAndBodydataVaultSpec(overlay_dir="/dev/nflasha15")
        )
        self.assertFalse(r_ov.passed)
        self.assertEqual(r_ov.block_code, P260_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        r_h3 = evaluate_version_readonly_and_bodydata_vault(
            VersionReadOnlyAndBodydataVaultSpec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(r_h3.passed)
        self.assertEqual(r_h3.block_code, P260_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        r_inv = evaluate_version_readonly_and_bodydata_vault(
            VersionReadOnlyAndBodydataVaultSpec(version_menu_path=("MENU", "Wrong", "Version"))
        )
        self.assertFalse(r_inv.passed)
        self.assertEqual(r_inv.block_code, P260_BLOCKED_INVALID_VERSION_OR_BODYDATA_VAULT_SPEC)

    def test_36_pillar44b_6_scenario_suite_passes_all_6_scenarios(self) -> None:
        res = run_pillar44b_version_readonly_bodydata_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P260_STATUS_VERIFIED_PILLAR_44B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P260_PILLAR_44B_SCENARIO_IDS)
        self.assertEqual(
            [s.expected_allowed for s in res.scenarios],
            [True, True, False, False, False, False],
        )

    def test_37_combined_verifier_and_symmetry_alias_dual_mode_and_failure_propagation(self) -> None:
        r_ok = verify_apsc_s35_face_eye_af_and_version_vault()
        r_alias = verify_apsc_s35_face_eye_af_version_vault(force_clean_room=True)
        self.assertTrue(r_ok.all_passed)
        self.assertTrue(r_ok.passed)
        self.assertEqual(r_ok.status, P260_STATUS_VERIFIED_PILLAR44_SUITE)
        self.assertEqual(r_ok.apsc_s35_4k_or_raw_bypass_events, 0)
        self.assertEqual(r_ok.ai_unit_subject_recog_spoof_events, 0)
        self.assertEqual(r_ok.hdmi_clean_feed_eye_frame_baked_pixels, 0)
        self.assertEqual(r_ok.version_dialog_flash_writes, 0)
        self.assertGreaterEqual(r_ok.bodydata_flash_attempts_blocked, 1)
        self.assertEqual(r_ok.slot1_bodydata_vault_mutation_bytes, 0)
        self.assertTrue(r_alias.all_passed)
        self.assertEqual(r_alias.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        r_bad = verify_apsc_s35_face_eye_af_and_version_vault(
            version_bodydata_spec=VersionReadOnlyAndBodydataVaultSpec(version_dialog_flash_writes=2),
            force_clean_room=True,
        )
        self.assertFalse(r_bad.all_passed)
        self.assertEqual(r_bad.status, P260_STATUS_FAIL_PILLAR44_SUITE)
        self.assertEqual(r_bad.version_dialog_flash_writes, 2)

    def test_38_standalone_suite_deterministic_digest_in_default_and_clean_room_modes(self) -> None:
        rep_d1 = run_pillar44_standalone_suite()
        rep_d2 = run_pillar44_standalone_suite()
        self.assertTrue(rep_d1.all_passed)
        self.assertEqual(rep_d1.suite_sha256, rep_d2.suite_sha256)
        self.assertGreaterEqual(rep_d1.bodydata_flash_attempts_blocked, 1)

        rep_cr1 = run_pillar44_standalone_suite(force_clean_room=True)
        rep_cr2 = run_pillar44_standalone_suite(force_clean_room=True)
        self.assertTrue(rep_cr1.all_passed)
        self.assertEqual(rep_cr1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_cr1.suite_sha256, rep_cr2.suite_sha256)
        self.assertEqual(len(rep_cr1.suite_sha256), 64)

    def test_39_compute_expected_apsc_s35_movie_or_still_state_hd_vs_4k_formats(self) -> None:
        self.assertEqual(P260_MOVIE_FILE_FORMATS_HD, ("XAVC S HD", "XAVC S-I HD"))
        self.assertEqual(P260_EFFECTIVE_ANGLE_OF_VIEW_MODES, ("Full-Frame_1.0x", "Super35_1.5x"))
        self.assertEqual(
            compute_expected_apsc_s35_movie_or_still_state(
                shooting_domain="Movie",
                movie_file_format="XAVC S HD",
                hdmi_raw_output_4264x2408="Off",
                configured_apsc_s35="On",
                lens_image_circle="FF",
            ),
            (False, "On", "Super35_1.5x"),
        )
        self.assertEqual(
            compute_expected_apsc_s35_movie_or_still_state(
                shooting_domain="S&Q",
                movie_file_format="XAVC S 4K",
                hdmi_raw_output_4264x2408="Off",
                configured_apsc_s35="On",
                lens_image_circle="APS-C",
            ),
            (True, "Off", "Full-Frame_1.0x"),
        )

    def test_40_master_44_pillar_specs_extend_master_43_cleanly_at_milestone_260(self) -> None:
        self.assertEqual(MASTER_44_PILLAR_COUNT, 44)
        self.assertEqual(len(MASTER_44_PILLAR_SPECS), 44)
        self.assertEqual(len(MASTER_44_PILLAR_IDS), 44)
        self.assertEqual(len(set(MASTER_44_PILLAR_IDS)), 44)
        self.assertEqual(MASTER_44_PILLAR_SPECS[:43], MASTER_43_PILLAR_SPECS)
        self.assertEqual(
            MASTER_44_PILLAR_SPECS[43],
            (
                44,
                "pillar_44_apsc_s35_face_eye_af_version_vault",
                "Phase 260 (260th Milestone)",
                "fx3_recovery.realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier",
            ),
        )

    def test_41_master_44pillar_default_mode_44_of_44_verified_under_budget(self) -> None:
        rep = self.master44_default
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P260_STATUS_VERIFIED_44OF44_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 44)
        self.assertEqual(rep.pillars_passed, 44)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertLess(rep.elapsed_seconds, 4.0)

    def test_42_master_44pillar_clean_room_mode_44_of_44_verified(self) -> None:
        rep = self.master44_clean_room
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.status, P260_STATUS_VERIFIED_44OF44_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 44)
        self.assertEqual(rep.pillars_passed, 44)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)

    def test_43_master_44pillar_zero_write_and_wave42_plus_upstream_invariants_preserved(self) -> None:
        rep = self.master44_default
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
        self.assertEqual(rep.tier0_battery_high_display_violations, 0)
        self.assertEqual(rep.bt_rmt_ir_lockout_violations, 0)
        self.assertEqual(rep.slot1_mymenu_vault_mutation_bytes, 0)
        self.assertEqual(rep.destructive_menu_delete_confusions, 0)
        self.assertEqual(rep.shutter_angle_exposure_step_drift_events, 0)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertEqual(rep.unbuffered_battery_pull_events, 0)
        self.assertFalse(rep.hardware_live_attachment_authorized)
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
        self.assertEqual(rep.errors, ())

    def test_44_master_44pillar_individual_pillar_numbering_and_status(self) -> None:
        rep = self.master44_clean_room
        self.assertEqual([p.pillar_number for p in rep.pillars], list(range(1, 45)))
        self.assertTrue(all(p.passed for p in rep.pillars))
        p44 = rep.pillars[43]
        self.assertEqual(p44.pillar_number, 44)
        self.assertEqual(p44.pillar_id, "pillar_44_apsc_s35_face_eye_af_version_vault")
        self.assertEqual(p44.phase_label, "Phase 260 (260th Milestone)")
        self.assertEqual(p44.key_metrics["pillar_44a_apsc_s35_face_eye_af_vault"], "6/6")
        self.assertEqual(p44.key_metrics["pillar_44b_version_readonly_bodydata_vault"], "6/6")
        self.assertEqual(p44.key_metrics["apsc_s35_4k_or_raw_bypass_events"], 0)
        self.assertEqual(p44.key_metrics["ai_unit_subject_recog_spoof_events"], 0)
        self.assertEqual(p44.key_metrics["hdmi_clean_feed_eye_frame_baked_pixels"], 0)
        self.assertEqual(p44.key_metrics["version_dialog_flash_writes"], 0)
        self.assertGreaterEqual(p44.key_metrics["bodydata_flash_attempts_blocked"], 1)
        self.assertEqual(p44.key_metrics["slot1_bodydata_vault_mutation_bytes"], 0)
        self.assertEqual(p44.key_metrics["donor_files_inspected"], 13)

    def test_45_master_44pillar_json_serializable_without_nan(self) -> None:
        rep = self.master44_clean_room
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(encoded)
        self.assertEqual(parsed["schema"], PHASE260_SCHEMA)
        self.assertEqual(parsed["pillar_count"], 44)
        self.assertEqual(parsed["pillars_passed"], 44)
        self.assertEqual(len(parsed["master_44pillar_sha256"]), 64)

    def test_46_master_44pillar_fault_injection_on_pillar_44_marks_43_of_44(self) -> None:
        with mock.patch.object(
            p260, "evaluate_realhw_43pillar_recovery_master", return_value=self.master43_clean_room
        ):
            rep = evaluate_realhw_44pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_44_apsc_s35_face_eye_af_version_vault",
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P260_STATUS_FAIL_44OF44_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 44)
        self.assertEqual(rep.pillars_passed, 43)
        self.assertEqual(
            rep.failed_pillars,
            ("pillar_44_apsc_s35_face_eye_af_version_vault",),
        )

    def test_47_master_44pillar_fault_injection_on_upstream_pillar_1_and_43_marks_43_of_44(self) -> None:
        for pid in (MASTER_44_PILLAR_IDS[0], MASTER_44_PILLAR_IDS[42]):
            with self.subTest(pillar_id=pid):
                with mock.patch.object(
                    p260, "evaluate_realhw_43pillar_recovery_master", return_value=self.master43_clean_room
                ):
                    rep = evaluate_realhw_44pillar_recovery_master(
                        force_clean_room=True,
                        fault_inject_pillar=pid,
                    )
                self.assertFalse(rep.all_passed)
                self.assertEqual(rep.pillars_passed, 43)
                self.assertEqual(rep.failed_pillars, (pid,))

    def test_48_master_44pillar_rejects_unknown_fault_inject_pillar(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_44pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_999",
            )

    def test_49_master_44pillar_aliases_forward_cleanly(self) -> None:
        cached = self.master44_clean_room
        with mock.patch.object(
            p260, "evaluate_realhw_44pillar_recovery_master", return_value=cached
        ) as mocked_eval:
            r1 = evaluate_44pillar_recovery_master(force_clean_room=True)
            r2 = verify_44pillar_recovery_suite(force_clean_room=True)
        self.assertIs(r1, cached)
        self.assertIs(r2, cached)
        self.assertEqual(mocked_eval.call_count, 2)

    def test_50_safety_invariant_tamper_detection_blocks_master(self) -> None:
        with mock.patch.object(p260, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            with self.assertRaises(ValueError):
                evaluate_realhw_44pillar_recovery_master(force_clean_room=True)
        with mock.patch.object(p260, "P260_DEFAULT_BODYDATA_FLASH_ATTEMPTS_BLOCKED", 0):
            with self.assertRaises(ValueError):
                evaluate_realhw_44pillar_recovery_master(force_clean_room=True)

    def test_51_safety_invariant_tamper_detection_blocks_standalone_and_combined(self) -> None:
        with mock.patch.object(p260, "PASSIVE_TX_BYTES_EMITTED", 1):
            rep_sa = run_pillar44_standalone_suite(force_clean_room=True)
            rep_cb = verify_apsc_s35_face_eye_af_and_version_vault(force_clean_room=True)
        self.assertFalse(rep_sa.all_passed)
        self.assertEqual(rep_sa.status, P260_STATUS_FAIL_PILLAR44_SUITE)
        self.assertTrue(any("PASSIVE_TX_BYTES_EMITTED" in e for e in rep_sa.errors))
        self.assertFalse(rep_cb.all_passed)
        self.assertTrue(any("PASSIVE_TX_BYTES_EMITTED" in e for e in rep_cb.errors))

    def test_52_master_44pillar_detects_upstream_m43_safety_or_domain_violation(self) -> None:
        for field_name, bad_val in (
            ("auto_slow_shutter_lockout_bypass_events", 1),
            ("hdmi_rec_ctrl_without_tc_violations", 1),
            ("fx3_has_builtin_evf", True),
            ("physical_device_writes", 1),
        ):
            with self.subTest(field=field_name):
                m43_bad = replace(self.master43_clean_room, **{field_name: bad_val})
                with mock.patch.object(
                    p260, "evaluate_realhw_43pillar_recovery_master", return_value=m43_bad
                ):
                    rep = evaluate_realhw_44pillar_recovery_master(force_clean_room=True)
                self.assertFalse(rep.all_passed)
                self.assertTrue(any(field_name in e for e in rep.errors))

    def test_53_master_44pillar_detects_p44_domain_counter_violations(self) -> None:
        base_p44 = run_pillar44_standalone_suite(force_clean_room=True)
        for field_name, bad_val in (
            ("apsc_s35_4k_or_raw_bypass_events", 1),
            ("ai_unit_subject_recog_spoof_events", 1),
            ("hdmi_clean_feed_eye_frame_baked_pixels", 64),
            ("version_dialog_flash_writes", 1),
            ("bodydata_flash_attempts_blocked", 0),
            ("slot1_bodydata_vault_mutation_bytes", 256),
            ("hardware_live_attachment_authorized", True),
        ):
            with self.subTest(field=field_name):
                p44_bad = replace(base_p44, **{field_name: bad_val})
                with (
                    mock.patch.object(
                        p260,
                        "evaluate_realhw_43pillar_recovery_master",
                        return_value=self.master43_clean_room,
                    ),
                    mock.patch.object(p260, "run_pillar44_standalone_suite", return_value=p44_bad),
                ):
                    rep = evaluate_realhw_44pillar_recovery_master(force_clean_room=True)
                self.assertFalse(rep.all_passed)
                self.assertTrue(any(field_name in e for e in rep.errors))

    def test_54_all_supported_fx3_firmware_versions_accepted_for_human_and_animal_face_eye_af(self) -> None:
        self.assertIn("7.02", P260_FX3_SUPPORTED_FW_VERSIONS)
        for ver in P260_FX3_SUPPORTED_FW_VERSIONS:
            for subj in ("Human", "Animal"):
                with self.subTest(fw_version=ver, subj=subj):
                    spec = ApscS35AndFaceEyeAfVaultSpec(
                        fw_version=ver,
                        pre_face_eye_subject=subj,
                        saved_face_eye_subject=subj,
                        post_face_eye_subject=subj,
                    )
                    self.assertTrue(evaluate_apsc_s35_and_face_eye_af_vault(spec).passed)

    def test_55_all_supported_fx3_firmware_versions_accepted_for_pillar44b_version_readonly(self) -> None:
        for ver in P260_FX3_SUPPORTED_FW_VERSIONS:
            with self.subTest(fw_version=ver):
                self.assertTrue(
                    evaluate_version_readonly_and_bodydata_vault(
                        VersionReadOnlyAndBodydataVaultSpec(
                            fw_version=ver,
                            displayed_body_fw_version=ver,
                            post_reset_body_fw_version=ver,
                        )
                    ).passed
                )

    def test_56_all_10_camset_filenames_across_slots_1_and_2_accepted_in_pillar44a_and_44b(self) -> None:
        self.assertEqual(len(P260_CAMSET_FILENAMES), 10)
        for slot in (1, 2):
            for fname in P260_CAMSET_FILENAMES:
                with self.subTest(slot=slot, fname=fname):
                    self.assertTrue(
                        evaluate_apsc_s35_and_face_eye_af_vault(
                            ApscS35AndFaceEyeAfVaultSpec(
                                camset_load_after_reset=True,
                                camset_slot=slot,
                                camset_filename=fname,
                                camset_read_only_load=True,
                            )
                        ).passed
                    )
                    self.assertTrue(
                        evaluate_version_readonly_and_bodydata_vault(
                            VersionReadOnlyAndBodydataVaultSpec(
                                camset_load_after_reset=True,
                                camset_slot=slot,
                                camset_filename=fname,
                                camset_read_only_load=True,
                            )
                        ).passed
                    )

    def test_57_pillar44a_camset01_ordonly_load_restores_saved_apsc_and_face_eye_profile(self) -> None:
        spec = ApscS35AndFaceEyeAfVaultSpec(
            pre_reset_apsc_s35="Off",
            pre_face_eye_prior_in_af="Off",
            pre_face_eye_subject="Human",
            pre_right_left_eye_select="Auto",
            pre_face_eye_frame_disp="Off",
            reset_action="Camera Settings Reset",
            camset_load_after_reset=True,
            camset_slot=1,
            camset_filename="CAMSET01.DAT",
            camset_source_model="ILME-FX3",
            camset_read_only_load=True,
            saved_apsc_s35="On",
            saved_face_eye_prior_in_af="On",
            saved_face_eye_subject="Bird",
            saved_right_left_eye_select="Left Eye",
            saved_face_eye_frame_disp="On",
            post_reset_apsc_s35="On",
            post_face_eye_prior_in_af="On",
            post_face_eye_subject="Bird",
            post_right_left_eye_select="Left Eye",
            post_face_eye_frame_disp="On",
            active_eye_target_after_custom_key="Left Eye",
        )
        self.assertTrue(evaluate_apsc_s35_and_face_eye_af_vault(spec).passed)

    def test_58_pillar44b_unrequested_automated_update_zero_blocked_count_consistency(self) -> None:
        ok_idle = evaluate_version_readonly_and_bodydata_vault(
            VersionReadOnlyAndBodydataVaultSpec(
                automated_bodydata_update_requested=False,
                automated_bodydata_update_hard_blocked=True,
                bodydata_flash_executed=False,
                bodydata_flash_attempts_blocked=0,
            )
        )
        self.assertTrue(ok_idle.passed)

        bad_idle = evaluate_version_readonly_and_bodydata_vault(
            VersionReadOnlyAndBodydataVaultSpec(
                automated_bodydata_update_requested=False,
                automated_bodydata_update_hard_blocked=True,
                bodydata_flash_executed=False,
                bodydata_flash_attempts_blocked=3,
            )
        )
        self.assertFalse(bad_idle.passed)
        self.assertEqual(bad_idle.block_code, P260_BLOCKED_AUTOMATED_BODYDATA_FLASH_EXECUTION)

    def test_59_tier0_backup_bin_pinned_sha256_and_wave42_constants_consistent(self) -> None:
        self.assertEqual(
            P260_PINNED_FX3_BACKUP_BIN_SHA256,
            "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        )
        self.assertEqual(
            P260_APSC_S35_MENU_PATH,
            ("MENU", "Shooting", "Image Quality/Rec", "APS-C S35 Shooting"),
        )
        self.assertEqual(P260_HDMI_RAW_4264X2408_RESOLUTION, "4264x2408")
        self.assertEqual(P260_SLOT1_VAULT_SLOT, 1)
        self.assertEqual(P260_FACE_EYE_PRIOR_MODES, ("On", "Off"))
        self.assertEqual(P260_FACE_EYE_SUBJECTS, ("Human", "Animal", "Bird"))
        self.assertEqual(P260_FACE_EYE_FRAME_DISP_MODES, ("On", "Off"))
        self.assertIn("Intelligent Auto", P260_SHOOTING_EXPOSURE_PROFILES)

    def test_60_donor_bounded_reader_handles_missing_open_error_and_non_regular_files(self) -> None:
        with mock.patch.object(p260, "resolve_donor_path", return_value=None):
            ok, total_b, read_b, kind, digest, raw = p260._read_donor_readonly_bounded("nonexistent.bin")
        self.assertFalse(ok)
        self.assertEqual((total_b, read_b, kind, digest, raw), (0, 0, "MISSING", "", b""))

        with (
            mock.patch.object(p260, "resolve_donor_path", return_value=Path("/nonexistent_phase260_file")),
            mock.patch.object(os, "open", side_effect=OSError("ENOENT")),
        ):
            ok2, _, _, kind2, _, _ = p260._read_donor_readonly_bounded("err.bin")
        self.assertFalse(ok2)
        self.assertEqual(kind2, "OPEN_ERROR")

        fake_st = mock.Mock(st_mode=stat.S_IFDIR)
        with (
            mock.patch.object(p260, "resolve_donor_path", return_value=Path("/tmp")),
            mock.patch.object(os, "open", return_value=999),
            mock.patch.object(os, "fstat", return_value=fake_st),
            mock.patch.object(os, "close") as mock_close,
        ):
            ok3, _, _, kind3, _, _ = p260._read_donor_readonly_bounded("dir_entry")
        self.assertFalse(ok3)
        self.assertEqual(kind3, "NOT_REGULAR")
        mock_close.assert_called_once_with(999)

    def test_61_donor_snapshot_failure_or_budget_overrun_propagates_to_reports(self) -> None:
        good_snap = inspect_phase260_donors_readonly(force_clean_room=True)
        bad_snap = replace(good_snap, all_donors_present=False, under_0_15s_budget=False, elapsed_seconds=0.25)
        with mock.patch.object(p260, "inspect_phase260_donors_readonly", return_value=bad_snap):
            sa = run_pillar44_standalone_suite(force_clean_room=True)
            cb = verify_apsc_s35_face_eye_af_and_version_vault(force_clean_room=True)
        self.assertFalse(sa.all_passed)
        self.assertTrue(any("donor verification failed" in e for e in sa.errors))
        self.assertTrue(any("exceeded 2.0s budget" in e for e in sa.errors))
        self.assertFalse(cb.all_passed)

    def test_62_backward_compatibility_callable_exports_22_to_43(self) -> None:
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
            (40, "evaluate_realhw_40pillar_recovery_master"),
            (41, "evaluate_realhw_41pillar_recovery_master"),
            (42, "evaluate_realhw_42pillar_recovery_master"),
            (43, "evaluate_realhw_43pillar_recovery_master"),
        ):
            with self.subTest(pillars=count):
                self.assertTrue(callable(getattr(fx3_recovery, attr_name)))
        self.assertEqual([p.pillar_number for p in self.master44_clean_room.pillars], list(range(1, 45)))

    def test_63_cli_verify_apsc_s35_face_eye_af_version_vault_summary_and_json(self) -> None:
        rc_txt, out_txt = _run_inprocess_cli("verify-apsc-s35-face-eye-af-version-vault")
        self.assertEqual(rc_txt, 0)
        self.assertIn(
            "status=VERIFIED_PILLAR44_APSC_S35_FACE_EYE_AF_VERSION_VAULT",
            out_txt,
        )
        self.assertIn("pillar_44a=6/6", out_txt)
        self.assertIn("pillar_44b=6/6", out_txt)
        self.assertIn("apsc_s35_4k_or_raw_bypass_events=0", out_txt)
        self.assertIn("ai_unit_subject_recog_spoof_events=0", out_txt)
        self.assertIn("hdmi_clean_feed_eye_frame_baked_pixels=0", out_txt)
        self.assertIn("version_dialog_flash_writes=0", out_txt)
        self.assertIn("bodydata_flash_attempts_blocked=2", out_txt)
        self.assertIn("slot1_bodydata_vault_mutation_bytes=0", out_txt)
        self.assertIn("hardware_live_attachment_authorized=False", out_txt)

        rc_js, out_js = _run_inprocess_cli("verify-apsc-s35-face-eye-af-version-vault", "--json")
        self.assertEqual(rc_js, 0)
        payload = json.loads(out_js)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["schema"], PHASE260_SCHEMA)

    def test_64_cli_verify_apsc_s35_face_eye_af_version_vault_force_clean_room(self) -> None:
        rc, out = _run_inprocess_cli(
            "verify-apsc-s35-face-eye-af-version-vault",
            "--force-clean-room",
            "--json",
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["apsc_s35_4k_or_raw_bypass_events"], 0)
        self.assertEqual(payload["ai_unit_subject_recog_spoof_events"], 0)
        self.assertEqual(payload["hdmi_clean_feed_eye_frame_baked_pixels"], 0)
        self.assertEqual(payload["version_dialog_flash_writes"], 0)
        self.assertGreaterEqual(payload["bodydata_flash_attempts_blocked"], 1)
        self.assertEqual(payload["slot1_bodydata_vault_mutation_bytes"], 0)
        self.assertFalse(payload["hardware_live_attachment_authorized"])

    def test_65_cli_verify_apsc_s35_face_eye_af_version_vault_subprocess_smoke(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-apsc-s35-face-eye-af-version-vault",
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
        self.assertEqual(payload["passive_tx_bytes_emitted"], 0)

    def test_66_cli_verify_44pillar_recovery_summary_json_and_clean_room_forwarding(self) -> None:
        with mock.patch.object(
            cli_main, "verify_44pillar_recovery_suite", return_value=self.master44_default
        ):
            rc_txt, out_txt = _run_inprocess_cli("verify-44pillar-recovery")
            self.assertEqual(rc_txt, 0)
            self.assertIn("status=VERIFIED_44OF44_PILLAR_RECOVERY_MASTER", out_txt)
            self.assertIn("pillars=44/44", out_txt)
            self.assertIn("pillar44_a=6/6", out_txt)
            self.assertIn("pillar44_b=6/6", out_txt)

            rc_js, out_js = _run_inprocess_cli("verify-44pillar-recovery", "--json")
            self.assertEqual(rc_js, 0)
            payload = json.loads(out_js)
            self.assertEqual(payload["pillar_count"], 44)
            self.assertEqual(payload["pillars_passed"], 44)

        with mock.patch.object(
            cli_main, "verify_44pillar_recovery_suite", return_value=self.master44_clean_room
        ) as mocked_suite:
            rc_cr, out_cr = _run_inprocess_cli("verify-44pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc_cr, 0)
        mocked_suite.assert_called_once_with(force_clean_room=True)
        self.assertEqual(json.loads(out_cr)["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_67_cli_out_creates_exclusive_directories_for_pillar44_and_44pillar_master(self) -> None:
        here = Path(__file__).resolve().parent
        out_p44 = here / f"_tmp_p260_p44_{os.getpid()}"
        rep_p44 = out_p44 / "pillar44-apsc-s35-face-eye-af-version-vault-report.json"
        out_m44 = here / f"_tmp_p260_m44_{os.getpid()}"
        rep_m44 = out_m44 / "44pillar-recovery-master-report.json"
        for f, d in ((rep_p44, out_p44), (rep_m44, out_m44)):
            if f.is_file():
                f.unlink()
            if d.is_dir():
                d.rmdir()
        try:
            rc1, _ = _run_inprocess_cli(
                "verify-apsc-s35-face-eye-af-version-vault",
                "--force-clean-room",
                "--out",
                str(out_p44),
            )
            self.assertEqual(rc1, 0)
            self.assertTrue(rep_p44.is_file())
            self.assertTrue(json.loads(rep_p44.read_text(encoding="utf-8"))["all_passed"])

            with mock.patch.object(
                cli_main, "verify_44pillar_recovery_suite", return_value=self.master44_clean_room
            ):
                rc2, _ = _run_inprocess_cli(
                    "verify-44pillar-recovery",
                    "--force-clean-room",
                    "--out",
                    str(out_m44),
                )
            self.assertEqual(rc2, 0)
            self.assertTrue(rep_m44.is_file())
            self.assertEqual(json.loads(rep_m44.read_text(encoding="utf-8"))["pillar_count"], 44)
        finally:
            for f, d in ((rep_p44, out_p44), (rep_m44, out_m44)):
                if f.is_file():
                    f.unlink()
                if d.is_dir():
                    d.rmdir()

    def test_68_cli_returns_nonzero_exit_code_when_pillar44_or_44pillar_master_fails(self) -> None:
        bad_sa = replace(run_pillar44_standalone_suite(force_clean_room=True), all_passed=False)
        with mock.patch.object(cli_main, "run_pillar44_standalone_suite", return_value=bad_sa):
            rc1, _ = _run_inprocess_cli("verify-apsc-s35-face-eye-af-version-vault", "--json")
        self.assertEqual(rc1, 2)

        bad_m44 = replace(self.master44_clean_room, all_passed=False)
        with mock.patch.object(cli_main, "verify_44pillar_recovery_suite", return_value=bad_m44):
            rc2, _ = _run_inprocess_cli("verify-44pillar-recovery", "--json")
        self.assertEqual(rc2, 2)


if __name__ == "__main__":
    unittest.main()
