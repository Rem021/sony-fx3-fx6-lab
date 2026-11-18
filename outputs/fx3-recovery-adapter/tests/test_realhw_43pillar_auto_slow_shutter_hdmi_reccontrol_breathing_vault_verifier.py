"""Phase 255 — Dual-mode unit tests for Pillar 43 (`[Auto Slow Shutter]` 6-condition hardware lockout,
`[Camera Settings Reset]` reset vs `[Reset Network Set.]` survival, and `Ver. 7.02`
`[Shutter Mode]=[Angle]` strict disjointness; `[Lens Compensation]` -> `[Breathing Comp.]` movie-only
compliant Sony E-mount crop and `4264x2408` `RAW Output` / `S&Q` `239.76p`/`200p` lockout; plus
`[HDMI Output Settings]` survival across `[Camera Settings Reset]` & `[Reset Network Set.]`,
`[REC Control]` <- `[Time Code Output]=[On]` mandatory prerequisite, `[4ch Audio Output]`
`CH1/CH2` vs `CH3/CH4` routing, `[Rec. Media dur HDMI Output]=[Off]` Slot-1/Slot-2 & Proxy guard, and
`O_RDONLY` Slot-1 `CAMSET01.DAT` round-trip) and unified `43/43` recovery master
(`verify-43pillar-recovery` / `verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault`)."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import (
    realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier as p255,
)
from fx3_recovery.realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier import (
    MASTER_42_PILLAR_SPECS,
    Master42PillarRecoveryReport,
    evaluate_realhw_42pillar_recovery_master,
)
from fx3_recovery.realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_43_PILLAR_COUNT,
    MASTER_43_PILLAR_IDS,
    MASTER_43_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P255_AUTO_SLOW_SHUTTER_6_LOCKOUT_CONDITIONS,
    P255_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS,
    P255_AUTO_SLOW_SHUTTER_DEFAULT,
    P255_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS,
    P255_AUTO_SLOW_SHUTTER_MENU_PATH,
    P255_AUTO_SLOW_SHUTTER_MODES,
    P255_BLOCKED_AUTO_SLOW_OR_BREATHING_RESET_DRIFT,
    P255_BLOCKED_AUTO_SLOW_SHUTTER_6LOCKOUT_BYPASS,
    P255_BLOCKED_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP,
    P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS,
    P255_BLOCKED_HDMI_4CH_AUDIO_ROUTING_MISMATCH,
    P255_BLOCKED_HDMI_REC_CTRL_WITHOUT_TC_OUTPUT,
    P255_BLOCKED_HDMI_SETTINGS_RESET_SURVIVAL_DRIFT,
    P255_BLOCKED_INVALID_AUTO_SLOW_OR_BREATHING_SPEC,
    P255_BLOCKED_INVALID_HDMI_OUTPUT_SETTINGS_SPEC,
    P255_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P255_BLOCKED_SAFETY_POLICY_VIOLATION,
    P255_BLOCKED_SLOT1_HDMI_REC_VAULT_MUTATION_OR_CAMSET_DRIFT,
    P255_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P255_BREATHING_COMP_DEFAULT,
    P255_BREATHING_COMP_LOCKOUT_SQ_RATES,
    P255_BREATHING_COMP_MENU_PATH,
    P255_BREATHING_COMP_MODES,
    P255_BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS,
    P255_CAMSET_FILENAMES,
    P255_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG,
    P255_EXPOSURE_MODES,
    P255_FLEXIBLE_EXP_SHUTTER_CTRL_MODES,
    P255_FX3_BREATHING_COMP_MIN_FW_VERSIONS,
    P255_FX3_FW_VERSION,
    P255_FX3_HELPGUIDE_ID,
    P255_FX3_MODEL_ID,
    P255_FX3_MODEL_NAME,
    P255_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS,
    P255_FX3_SUPPORTED_FW_VERSIONS,
    P255_FX6_DONOR_FW_VERSION,
    P255_FX6_DONOR_MODEL_NAME,
    P255_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P255_HDMI_4CH_AUDIO_OUTPUT_DEFAULT,
    P255_HDMI_4CH_AUDIO_OUTPUT_MODES,
    P255_HDMI_CH1_CH2_PAIR,
    P255_HDMI_CH3_CH4_PAIR,
    P255_HDMI_OUTPUT_SETTINGS_MENU_PATH,
    P255_HDMI_RAW_4264X2408_RESOLUTION,
    P255_HDMI_RAW_OUTPUT_MODES,
    P255_HDMI_REC_CONTROL_DEFAULT,
    P255_HDMI_REC_CONTROL_MODES,
    P255_HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS,
    P255_ISO_AUTO_TOKEN,
    P255_LOG_CINE_EI_LOCKOUT_MODES,
    P255_LOG_SHOOTING_MODES,
    P255_MOVIE_AND_SQ_FRAME_RATES,
    P255_MOVIE_SHUTTER_MODES,
    P255_MOVIE_SHUTTER_MODE_DEFAULT,
    P255_PILLAR_43A_SCENARIO_IDS,
    P255_PILLAR_43B_SCENARIO_IDS,
    P255_PINNED_FX3_BACKUP_BIN_SHA256,
    P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
    P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
    P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
    P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
    P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
    P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
    P255_REC_MEDIA_DUR_HDMI_DEFAULT,
    P255_REC_MEDIA_DUR_HDMI_MODES,
    P255_RESET_ACTIONS,
    P255_SHOOTING_DOMAINS,
    P255_SHUTTER_MODE_MENU_PATH,
    P255_SLOT1_HDMI_REC_VAULT_MUTATION_BYTES,
    P255_SLOT1_VAULT_SLOT,
    P255_STATUS_FAIL_43OF43_AGGREGATOR,
    P255_STATUS_FAIL_PILLAR43_SUITE,
    P255_STATUS_VERIFIED_43OF43_AGGREGATOR,
    P255_STATUS_VERIFIED_PILLAR43_SUITE,
    P255_STATUS_VERIFIED_PILLAR_43A,
    P255_STATUS_VERIFIED_PILLAR_43B,
    P255_TIME_CODE_OUTPUT_DEFAULT,
    P255_TIME_CODE_OUTPUT_MODES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE255_SCHEMA,
    PHASE255_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    AutoSlowShutterAndBreathingCompVaultSpec,
    HdmiRecControl4chAudioAndMediaVaultSpec,
    Master43PillarRecoveryReport,
    build_default_safe_auto_slow_shutter_breathing_vault_spec,
    build_default_safe_hdmi_reccontrol_4chaudio_vault_spec,
    compute_expected_auto_slow_shutter_lockouts,
    evaluate_43pillar_recovery_master,
    evaluate_auto_slow_shutter_and_breathing_comp_vault,
    evaluate_hdmi_reccontrol_4chaudio_and_media_vault,
    evaluate_realhw_43pillar_recovery_master,
    inspect_phase255_donors_readonly,
    run_pillar43_standalone_suite,
    run_pillar43a_auto_slow_shutter_breathing_vault_6_scenario_suite,
    run_pillar43b_hdmi_reccontrol_4chaudio_vault_6_scenario_suite,
    verify_43pillar_recovery_suite,
    verify_auto_slow_shutter_hdmi_reccontrol_and_breathing_vault,
    verify_auto_slow_shutter_hdmi_reccontrol_breathing_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]


def _run_inprocess_cli(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with mock.patch.object(sys, "argv", ["fx3_recovery", *argv]), redirect_stdout(buf):
        rc = cli_main.main()
    return rc, buf.getvalue()


class TestPhase255Pillar43And43PillarRecoveryMaster(unittest.TestCase):
    """68 fast dual-mode tests covering Pillar 43A, Pillar 43B, O_RDONLY donors, CLI & 43/43 master."""

    master43_default: Master43PillarRecoveryReport
    master43_clean_room: Master43PillarRecoveryReport
    master42_clean_room: Master42PillarRecoveryReport

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.master43_default = evaluate_realhw_43pillar_recovery_master()
        cls.master43_clean_room = evaluate_realhw_43pillar_recovery_master(force_clean_room=True)
        cls.master42_clean_room = evaluate_realhw_42pillar_recovery_master(force_clean_room=True)

    def test_01_hard_locked_zero_write_safety_constants(self) -> None:
        self.assertEqual(
            PHASE255_SCHEMA,
            "realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier_v1",
        )
        self.assertEqual(PHASE255_VERSION, "1.0.0")
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
        self.assertFalse(P255_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(P255_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS, 0)
        self.assertEqual(P255_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS, 0)
        self.assertEqual(P255_BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS, 0)
        self.assertEqual(P255_HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS, 0)
        self.assertEqual(P255_SLOT1_HDMI_REC_VAULT_MUTATION_BYTES, 0)

    def test_02_wave41_menu_paths_6lockouts_hdmi_and_breathing_constants(self) -> None:
        self.assertEqual(P255_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P255_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P255_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P255_FX3_FW_VERSION, "7.02")
        self.assertEqual(P255_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P255_FX6_DONOR_FW_VERSION, "6.01")
        self.assertEqual(
            P255_AUTO_SLOW_SHUTTER_MENU_PATH,
            ("MENU", "Exposure/Color", "Exposure", "Auto Slow Shutter"),
        )
        self.assertEqual(P255_AUTO_SLOW_SHUTTER_DEFAULT, "On")
        self.assertEqual(P255_AUTO_SLOW_SHUTTER_MODES, ("On", "Off"))
        self.assertEqual(
            P255_AUTO_SLOW_SHUTTER_6_LOCKOUT_CONDITIONS,
            (
                "S&Q_MOTION",
                "SHUTTER_PRIORITY_S",
                "MANUAL_EXPOSURE_M",
                "NON_AUTO_ISO",
                "FLEXIBLE_EXP_MANUAL_SHUTTER",
                "LOG_CINE_EI_OR_CINE_EI_QUICK",
            ),
        )
        self.assertEqual(
            P255_BREATHING_COMP_MENU_PATH,
            ("MENU", "Shooting", "Image Quality/Rec", "Lens Compensation", "Breathing Comp."),
        )
        self.assertEqual(P255_BREATHING_COMP_DEFAULT, "Off")
        self.assertEqual(P255_BREATHING_COMP_MODES, ("Off", "On"))
        self.assertEqual(P255_HDMI_RAW_4264X2408_RESOLUTION, "4264x2408")
        self.assertEqual(P255_BREATHING_COMP_LOCKOUT_SQ_RATES, ("200p", "239.76p"))
        self.assertEqual(
            P255_HDMI_OUTPUT_SETTINGS_MENU_PATH,
            ("MENU", "Setup", "External Output", "HDMI Output Settings"),
        )
        self.assertEqual(P255_REC_MEDIA_DUR_HDMI_DEFAULT, "On")
        self.assertEqual(P255_REC_MEDIA_DUR_HDMI_MODES, ("On", "Off"))
        self.assertEqual(P255_TIME_CODE_OUTPUT_DEFAULT, "Off")
        self.assertEqual(P255_HDMI_REC_CONTROL_DEFAULT, "Off")
        self.assertEqual(P255_HDMI_4CH_AUDIO_OUTPUT_DEFAULT, "CH1/CH2")
        self.assertEqual(P255_HDMI_4CH_AUDIO_OUTPUT_MODES, ("CH1/CH2", "CH3/CH4"))

    def test_03_package_exports_complete_and_free_of_duplicates_or_shadowing(self) -> None:
        all_exports = fx3_recovery.__all__
        self.assertEqual(len(p255.__all__), len(set(p255.__all__)))
        self.assertEqual(
            all_exports.count("realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier"),
            1,
        )
        shared_safety_syms = {
            "ALLOW_BOOT_PARTITION_TARGETING",
            "ALLOW_DESTRUCTIVE_FASTBOOT",
            "ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS",
            "ALLOW_PERSISTENT_JIRITSU_WRITES",
            "CNFLASHA_USERSPACE_WRITE_BLOCKED",
            "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
            "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
            "ISP_WRITE_AUTHORIZED",
            "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
            "OTP_FUSE_TOUCHES",
            "OTP_FUSE_WRITES",
            "PASSIVE_TX_BYTES_EMITTED",
            "PERSISTENT_EMMC_WRITES_AUTHORIZED",
            "PERSISTENT_WRITE_RELEASE",
            "PHYSICAL_DEVICE_WRITES",
            "PHYSICAL_USB_PACKETS_EMITTED",
            "RAW_FIRMWARE_BYTES_LEAKED",
            "READ_ONLY_DONOR_ACCESS",
            "RPMB_COUNTER_INCREMENTS",
            "SPI_NOR_WRITE_AUTHORIZED",
        }
        for sym in p255.__all__:
            self.assertIn(sym, all_exports)
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing {sym} on fx3_recovery")
            if sym not in shared_safety_syms:
                self.assertEqual(all_exports.count(sym), 1, f"Duplicate Phase 255 export {sym}")
                self.assertIs(getattr(fx3_recovery, sym), getattr(p255, sym))

    def test_04_donor_inspection_default_mode_under_0_15s_zero_leak(self) -> None:
        snap = inspect_phase255_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 12)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertLess(snap.elapsed_seconds, 2.0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_inspection_forced_clean_room_synthetic_12_artifacts(self) -> None:
        snap = inspect_phase255_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 12)
        self.assertTrue(all(a.matches_pinned for a in snap.artifacts))
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(
            by_id["fx3_libinfralenscommunicator_so"].total_bytes,
            P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
        )
        self.assertEqual(
            by_id["fx3_libinfralenscommunicator_so"].digest_sha256,
            P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
        )
        self.assertEqual(
            by_id["fx3_libinframediaconfig_so"].total_bytes,
            P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
        )
        self.assertEqual(
            by_id["fx3_libinframediaconfig_so"].digest_sha256,
            P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
        )
        self.assertEqual(
            by_id["fx6_libinfrahotshoe_so"].total_bytes,
            P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
        )
        self.assertEqual(
            by_id["fx6_libinfrahotshoe_so"].digest_sha256,
            P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
        )

    def test_06_donor_inspection_falls_back_cleanly_when_donor_missing(self) -> None:
        with mock.patch.object(
            p255, "_read_donor_readonly_bounded", return_value=(False, 0, 0, "MISSING", "", b"")
        ):
            snap = inspect_phase255_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 12)

    def test_07_elf64_aarch64_token_helper_validates_magic_machine_and_symbols(self) -> None:
        ok_bad_magic, msg_bad = p255._check_elf64_aarch64_tokens(b"NOT_AN_ELF", (b"LensCommunicator",))
        self.assertFalse(ok_bad_magic)
        self.assertEqual(msg_bad, "NOT_ELF")

        hdr = bytearray(128)
        hdr[:4] = b"\x7fELF"
        hdr[4] = 2
        hdr[5] = 1
        struct.pack_into("<H", hdr, 18, 183)
        hdr[64:80] = b"LensCommunicator"
        ok_good, msg_good = p255._check_elf64_aarch64_tokens(bytes(hdr), (b"LensCommunicator",))
        self.assertTrue(ok_good)
        self.assertEqual(msg_good, "ELF64_AARCH64:LensCommunicator")

        ok_miss, msg_miss = p255._check_elf64_aarch64_tokens(bytes(hdr), (b"InfraHotshoe",))
        self.assertFalse(ok_miss)
        self.assertIn("MISSING_TOKENS:InfraHotshoe", msg_miss)

    def test_08_pillar43a_default_safe_spec_passes_all_invariants(self) -> None:
        spec = build_default_safe_auto_slow_shutter_breathing_vault_spec()
        rep = evaluate_auto_slow_shutter_and_breathing_comp_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P255_STATUS_VERIFIED_PILLAR_43A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.reset_scope_verified)
        self.assertTrue(rep.six_lockout_rules_verified)
        self.assertTrue(rep.shutter_angle_disjointness_verified)
        self.assertTrue(rep.breathing_comp_boundary_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.active_lockout_conditions, ())
        self.assertEqual(rep.auto_slow_shutter_lockout_bypass_events, 0)
        self.assertEqual(rep.auto_slow_shutter_angle_overlap_events, 0)
        self.assertEqual(rep.breathing_comp_raw_or_240p_bypass_events, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_09_pillar43a_auto_slow_shutter_active_in_p_a_and_flexible_auto_shutter(self) -> None:
        for exp_mode, flex_ctrl in (("P", "Auto"), ("A", "Auto"), ("Flexible Exp. Mode", "Auto")):
            for log_mode in ("Off", "Flexible ISO"):
                with self.subTest(exp_mode=exp_mode, log_mode=log_mode):
                    spec = AutoSlowShutterAndBreathingCompVaultSpec(
                        shooting_domain="Movie",
                        exposure_mode=exp_mode,
                        flexible_exp_shutter_ctrl=flex_ctrl,
                        iso_setting="ISO AUTO",
                        log_shooting_mode=log_mode,
                        reported_lockout_conditions=(),
                        auto_slow_shutter_effectively_active=True,
                    )
                    rep = evaluate_auto_slow_shutter_and_breathing_comp_vault(spec)
                    self.assertTrue(rep.passed)

    def test_10_pillar43a_camera_settings_reset_and_initialize_reset_while_network_reset_preserves(
        self,
    ) -> None:
        for rst in ("Camera Settings Reset", "Initialize"):
            with self.subTest(reset_action=rst):
                spec = AutoSlowShutterAndBreathingCompVaultSpec(
                    pre_reset_auto_slow_shutter="Off",
                    pre_reset_breathing_comp="On",
                    reset_action=rst,
                    post_reset_auto_slow_shutter="On",
                    post_reset_breathing_comp="Off",
                    auto_slow_shutter_effectively_active=True,
                    breathing_comp_effectively_active=False,
                    fov_crop_applied=False,
                )
                self.assertTrue(evaluate_auto_slow_shutter_and_breathing_comp_vault(spec).passed)

        spec_net = AutoSlowShutterAndBreathingCompVaultSpec(
            pre_reset_auto_slow_shutter="Off",
            pre_reset_breathing_comp="On",
            reset_action="Reset Network Set.",
            post_reset_auto_slow_shutter="Off",
            post_reset_breathing_comp="On",
            auto_slow_shutter_effectively_active=False,
            breathing_comp_effectively_active=True,
            fov_crop_applied=True,
        )
        self.assertTrue(evaluate_auto_slow_shutter_and_breathing_comp_vault(spec_net).passed)

    def test_11_pillar43a_ordonly_camset01_load_restores_saved_auto_slow_and_breathing_comp(self) -> None:
        spec = AutoSlowShutterAndBreathingCompVaultSpec(
            pre_reset_auto_slow_shutter="On",
            pre_reset_breathing_comp="Off",
            reset_action="Initialize",
            camset_load_after_reset=True,
            camset_slot=1,
            camset_filename="CAMSET01.DAT",
            camset_source_model="ILME-FX3",
            camset_read_only_load=True,
            saved_auto_slow_shutter="Off",
            saved_breathing_comp="On",
            post_reset_auto_slow_shutter="Off",
            post_reset_breathing_comp="On",
            auto_slow_shutter_effectively_active=False,
            breathing_comp_effectively_active=True,
            fov_crop_applied=True,
        )
        self.assertTrue(evaluate_auto_slow_shutter_and_breathing_comp_vault(spec).passed)

    def test_12_pillar43a_individual_lockouts_1_sq_2_shutter_priority_3_manual_exposure(self) -> None:
        single_cases = (
            ("S&Q_MOTION", {"shooting_domain": "S&Q"}),
            ("SHUTTER_PRIORITY_S", {"exposure_mode": "S"}),
            ("MANUAL_EXPOSURE_M", {"exposure_mode": "M"}),
        )
        for lock_id, kw in single_cases:
            with self.subTest(lock_id=lock_id):
                safe = AutoSlowShutterAndBreathingCompVaultSpec(
                    reported_lockout_conditions=(lock_id,),
                    auto_slow_shutter_effectively_active=False,
                    **kw,
                )
                self.assertTrue(evaluate_auto_slow_shutter_and_breathing_comp_vault(safe).passed)

                bypass = replace(safe, auto_slow_shutter_effectively_active=True)
                rep_bad = evaluate_auto_slow_shutter_and_breathing_comp_vault(bypass)
                self.assertFalse(rep_bad.passed)
                self.assertEqual(rep_bad.block_code, P255_BLOCKED_AUTO_SLOW_SHUTTER_6LOCKOUT_BYPASS)

    def test_13_pillar43a_individual_lockouts_4_manual_iso_5_flex_manual_shutter_6_cine_ei(self) -> None:
        single_cases = (
            ("NON_AUTO_ISO", {"iso_setting": "ISO 800"}),
            (
                "FLEXIBLE_EXP_MANUAL_SHUTTER",
                {"exposure_mode": "Flexible Exp. Mode", "flexible_exp_shutter_ctrl": "Manual"},
            ),
            ("LOG_CINE_EI_OR_CINE_EI_QUICK", {"log_shooting_mode": "Cine EI Quick"}),
            ("LOG_CINE_EI_OR_CINE_EI_QUICK", {"log_shooting_mode": "Cine EI"}),
        )
        for lock_id, kw in single_cases:
            with self.subTest(lock_id=lock_id, kw=kw):
                safe = AutoSlowShutterAndBreathingCompVaultSpec(
                    reported_lockout_conditions=(lock_id,),
                    auto_slow_shutter_effectively_active=False,
                    **kw,
                )
                self.assertTrue(evaluate_auto_slow_shutter_and_breathing_comp_vault(safe).passed)

                bypass = replace(safe, auto_slow_shutter_effectively_active=True)
                rep_bad = evaluate_auto_slow_shutter_and_breathing_comp_vault(bypass)
                self.assertFalse(rep_bad.passed)
                self.assertEqual(rep_bad.block_code, P255_BLOCKED_AUTO_SLOW_SHUTTER_6LOCKOUT_BYPASS)

    def test_14_pillar43a_cartesian_state_space_proves_auto_slow_and_shutter_angle_zero_overlap(
        self,
    ) -> None:
        overlap_states = 0
        checked_states = 0
        for domain in P255_SHOOTING_DOMAINS:
            for exp_mode in P255_EXPOSURE_MODES:
                for flex_ctrl in P255_FLEXIBLE_EXP_SHUTTER_CTRL_MODES:
                    for iso in ("ISO AUTO", "ISO 800"):
                        for log_m in P255_LOG_SHOOTING_MODES:
                            for s_mode in P255_MOVIE_SHUTTER_MODES:
                                checked_states += 1
                                lockouts = compute_expected_auto_slow_shutter_lockouts(
                                    shooting_domain=domain,
                                    exposure_mode=exp_mode,
                                    flexible_exp_shutter_ctrl=flex_ctrl,
                                    iso_setting=iso,
                                    log_shooting_mode=log_m,
                                )
                                auto_slow_on = domain == "Movie" and len(lockouts) == 0
                                angle_on = (
                                    s_mode == "Angle"
                                    and domain in ("Movie", "S&Q")
                                    and (
                                        exp_mode in ("S", "M")
                                        or (exp_mode == "Flexible Exp. Mode" and flex_ctrl == "Manual")
                                    )
                                )
                                if auto_slow_on and angle_on:
                                    overlap_states += 1
        self.assertGreaterEqual(checked_states, 480)
        self.assertEqual(overlap_states, 0)

    def test_15_pillar43a_rejects_shutter_angle_overlap_or_invalid_angle_governance(self) -> None:
        bad_overlap = AutoSlowShutterAndBreathingCompVaultSpec(
            shooting_domain="Movie",
            exposure_mode="M",
            reported_lockout_conditions=("MANUAL_EXPOSURE_M",),
            auto_slow_shutter_effectively_active=True,
            movie_shutter_mode="Angle",
            shutter_angle_effectively_active=True,
            auto_slow_shutter_angle_overlap_events=1,
        )
        rep1 = evaluate_auto_slow_shutter_and_breathing_comp_vault(bad_overlap)
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P255_BLOCKED_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP)

        bad_fw_angle = AutoSlowShutterAndBreathingCompVaultSpec(
            fw_version="5.00",
            exposure_mode="M",
            reported_lockout_conditions=("MANUAL_EXPOSURE_M",),
            auto_slow_shutter_effectively_active=False,
            movie_shutter_mode="Angle",
            shutter_angle_effectively_active=True,
        )
        rep2 = evaluate_auto_slow_shutter_and_breathing_comp_vault(bad_fw_angle)
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P255_BLOCKED_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP)

    def test_16_pillar43a_rejects_reset_drift_across_camera_reset_and_network_reset(self) -> None:
        bad_cam_rst = AutoSlowShutterAndBreathingCompVaultSpec(
            pre_reset_auto_slow_shutter="Off",
            reset_action="Camera Settings Reset",
            post_reset_auto_slow_shutter="Off",
            auto_slow_shutter_effectively_active=False,
        )
        rep1 = evaluate_auto_slow_shutter_and_breathing_comp_vault(bad_cam_rst)
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P255_BLOCKED_AUTO_SLOW_OR_BREATHING_RESET_DRIFT)

        bad_net_rst = AutoSlowShutterAndBreathingCompVaultSpec(
            pre_reset_breathing_comp="On",
            reset_action="Reset Network Set.",
            post_reset_breathing_comp="Off",
            breathing_comp_effectively_active=False,
            fov_crop_applied=False,
        )
        rep2 = evaluate_auto_slow_shutter_and_breathing_comp_vault(bad_net_rst)
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P255_BLOCKED_AUTO_SLOW_OR_BREATHING_RESET_DRIFT)

    def test_17_pillar43a_breathing_comp_active_with_crop_across_24p_to_120p_movie_and_sq(self) -> None:
        for fps in ("23.98p", "24.00p", "25p", "29.97p", "50p", "59.94p", "100p", "119.88p"):
            with self.subTest(fps=fps):
                spec = AutoSlowShutterAndBreathingCompVaultSpec(
                    active_frame_rate=fps,
                    pre_reset_breathing_comp="On",
                    post_reset_breathing_comp="On",
                    lens_breathing_comp_compliant=True,
                    hdmi_raw_output_4264x2408="Off",
                    breathing_comp_effectively_active=True,
                    fov_crop_applied=True,
                )
                self.assertTrue(evaluate_auto_slow_shutter_and_breathing_comp_vault(spec).passed)

    def test_18_pillar43a_rejects_breathing_comp_bypass_in_raw_4264x2408_or_sq_240p_200p(self) -> None:
        raw_bypass = AutoSlowShutterAndBreathingCompVaultSpec(
            hdmi_raw_output_4264x2408="On",
            breathing_comp_effectively_active=True,
            fov_crop_applied=True,
        )
        rep_raw = evaluate_auto_slow_shutter_and_breathing_comp_vault(raw_bypass)
        self.assertFalse(rep_raw.passed)
        self.assertEqual(rep_raw.block_code, P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS)

        for sq_fps in ("200p", "239.76p"):
            with self.subTest(sq_fps=sq_fps):
                sq_bypass = AutoSlowShutterAndBreathingCompVaultSpec(
                    shooting_domain="S&Q",
                    reported_lockout_conditions=("S&Q_MOTION",),
                    auto_slow_shutter_effectively_active=False,
                    active_frame_rate=sq_fps,
                    breathing_comp_effectively_active=True,
                    fov_crop_applied=True,
                )
                rep_sq = evaluate_auto_slow_shutter_and_breathing_comp_vault(sq_bypass)
                self.assertFalse(rep_sq.passed)
                self.assertEqual(rep_sq.block_code, P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS)

    def test_19_pillar43a_rejects_breathing_comp_in_still_noncompliant_lens_or_crop_mismatch(self) -> None:
        still_bad = AutoSlowShutterAndBreathingCompVaultSpec(
            shooting_domain="Still",
            auto_slow_shutter_effectively_active=False,
            breathing_comp_effectively_active=True,
            fov_crop_applied=True,
        )
        self.assertEqual(
            evaluate_auto_slow_shutter_and_breathing_comp_vault(still_bad).block_code,
            P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS,
        )

        lens_bad = AutoSlowShutterAndBreathingCompVaultSpec(
            lens_breathing_comp_compliant=False,
            breathing_comp_effectively_active=True,
            fov_crop_applied=True,
        )
        self.assertEqual(
            evaluate_auto_slow_shutter_and_breathing_comp_vault(lens_bad).block_code,
            P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS,
        )

        crop_bad = AutoSlowShutterAndBreathingCompVaultSpec(
            breathing_comp_effectively_active=True,
            fov_crop_applied=False,
        )
        self.assertEqual(
            evaluate_auto_slow_shutter_and_breathing_comp_vault(crop_bad).block_code,
            P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS,
        )

    def test_20_pillar43a_rejects_invalid_spec_tokens_and_cross_model_camset(self) -> None:
        for bad_kw in (
            {"camera_model": "ILME-FX6"},
            {"auto_slow_shutter_menu_path": ("MENU", "Shooting", "Auto Slow Shutter")},
            {"reported_lockout_conditions": ("S&Q_MOTION", "S&Q_MOTION")},
            {"camset_load_after_reset": True, "camset_source_model": "ILME-FX6"},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_auto_slow_shutter_and_breathing_comp_vault(
                    AutoSlowShutterAndBreathingCompVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P255_BLOCKED_INVALID_AUTO_SLOW_OR_BREATHING_SPEC)

    def test_21_pillar43a_rejects_persistent_overlay_escape_and_write_unlock(self) -> None:
        rep_ov = evaluate_auto_slow_shutter_and_breathing_comp_vault(
            AutoSlowShutterAndBreathingCompVaultSpec(overlay_dir="/setting/escaped")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P255_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_unlk = evaluate_auto_slow_shutter_and_breathing_comp_vault(
            AutoSlowShutterAndBreathingCompVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep_unlk.passed)
        self.assertEqual(rep_unlk.block_code, P255_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_22_pillar43a_rejects_tier0_backup_bin_h0_h3_parity_drift(self) -> None:
        rep = evaluate_auto_slow_shutter_and_breathing_comp_vault(
            AutoSlowShutterAndBreathingCompVaultSpec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P255_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_23_pillar43a_6_scenario_suite_passes_all_6_with_expected_codes(self) -> None:
        res = run_pillar43a_auto_slow_shutter_breathing_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P255_STATUS_VERIFIED_PILLAR_43A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P255_PILLAR_43A_SCENARIO_IDS)
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])


    def test_24_pillar43b_default_safe_spec_passes_all_invariants(self) -> None:
        spec = build_default_safe_hdmi_reccontrol_4chaudio_vault_spec()
        rep = evaluate_hdmi_reccontrol_4chaudio_and_media_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P255_STATUS_VERIFIED_PILLAR_43B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.hdmi_reset_survival_verified)
        self.assertTrue(rep.rec_ctrl_tc_prerequisite_verified)
        self.assertTrue(rep.hdmi_4ch_audio_routing_verified)
        self.assertTrue(rep.rec_media_off_vault_guard_verified)
        self.assertTrue(rep.camset_ordonly_roundtrip_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.hdmi_rec_ctrl_without_tc_violations, 0)
        self.assertEqual(rep.slot1_hdmi_rec_vault_mutation_bytes, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_25_pillar43b_hdmi_output_settings_survive_camera_settings_reset_and_network_reset(
        self,
    ) -> None:
        for rst in ("NONE", "Camera Settings Reset", "Reset Network Set."):
            with self.subTest(reset_action=rst):
                spec = HdmiRecControl4chAudioAndMediaVaultSpec(reset_action=rst)
                self.assertTrue(evaluate_hdmi_reccontrol_4chaudio_and_media_vault(spec).passed)

    def test_26_pillar43b_initialize_resets_hdmi_output_settings_to_factory_defaults(self) -> None:
        spec = HdmiRecControl4chAudioAndMediaVaultSpec(
            pre_rec_media_dur_hdmi="Off",
            pre_time_code_output="On",
            pre_hdmi_rec_control="On",
            pre_4ch_audio_output="CH3/CH4",
            reset_action="Initialize",
            post_rec_media_dur_hdmi="On",
            post_time_code_output="Off",
            post_hdmi_rec_control="Off",
            post_4ch_audio_output="CH1/CH2",
            external_recorder_rec_trigger_enabled=False,
            hdmi_routed_audio_pair=P255_HDMI_CH1_CH2_PAIR,
            hdmi_connected=True,
            internal_slot1_slot2_clip_rec_inhibited=False,
            proxy_recording_inhibited=False,
            slot1_tier0_vault_active=False,
        )
        self.assertTrue(evaluate_hdmi_reccontrol_4chaudio_and_media_vault(spec).passed)

    def test_27_pillar43b_ordonly_slot1_camset01_roundtrip_restores_hdmi_settings_after_initialize(
        self,
    ) -> None:
        spec = HdmiRecControl4chAudioAndMediaVaultSpec(
            pre_rec_media_dur_hdmi="On",
            pre_time_code_output="Off",
            pre_hdmi_rec_control="Off",
            pre_4ch_audio_output="CH1/CH2",
            reset_action="Initialize",
            camset_load_after_reset=True,
            camset_slot=1,
            camset_filename="CAMSET01.DAT",
            camset_source_model="ILME-FX3",
            camset_read_only_load=True,
            saved_rec_media_dur_hdmi="Off",
            saved_time_code_output="On",
            saved_hdmi_rec_control="On",
            saved_4ch_audio_output="CH3/CH4",
            post_rec_media_dur_hdmi="Off",
            post_time_code_output="On",
            post_hdmi_rec_control="On",
            post_4ch_audio_output="CH3/CH4",
            external_recorder_rec_trigger_enabled=True,
            mi_shoe_4ch_audio_active=True,
            shoe_audio_set_mode="48kHz/24bit 4ch",
            hdmi_routed_audio_pair=P255_HDMI_CH3_CH4_PAIR,
            hdmi_connected=True,
            internal_slot1_slot2_clip_rec_inhibited=True,
            proxy_recording_inhibited=True,
            slot1_tier0_vault_active=True,
            slot1_sdxc_wp_locked=True,
        )
        self.assertTrue(evaluate_hdmi_reccontrol_4chaudio_and_media_vault(spec).passed)

    def test_28_pillar43b_rejects_hdmi_settings_wiped_by_camera_settings_reset_or_network_reset(
        self,
    ) -> None:
        for rst in ("Camera Settings Reset", "Reset Network Set."):
            with self.subTest(reset_action=rst):
                bad = HdmiRecControl4chAudioAndMediaVaultSpec(
                    pre_rec_media_dur_hdmi="Off",
                    pre_time_code_output="On",
                    pre_hdmi_rec_control="On",
                    pre_4ch_audio_output="CH3/CH4",
                    reset_action=rst,
                    post_rec_media_dur_hdmi="On",
                    post_time_code_output="Off",
                    post_hdmi_rec_control="Off",
                    post_4ch_audio_output="CH1/CH2",
                    external_recorder_rec_trigger_enabled=False,
                    hdmi_routed_audio_pair=P255_HDMI_CH1_CH2_PAIR,
                    internal_slot1_slot2_clip_rec_inhibited=False,
                    proxy_recording_inhibited=False,
                    slot1_tier0_vault_active=False,
                )
                rep = evaluate_hdmi_reccontrol_4chaudio_and_media_vault(bad)
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P255_BLOCKED_HDMI_SETTINGS_RESET_SURVIVAL_DRIFT)

    def test_29_pillar43b_rejects_rec_control_on_without_time_code_output_on(self) -> None:
        for bad in (
            HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_time_code_output="Off",
                pre_hdmi_rec_control="On",
                post_time_code_output="Off",
                post_hdmi_rec_control="On",
            ),
            HdmiRecControl4chAudioAndMediaVaultSpec(
                camset_load_after_reset=True,
                saved_time_code_output="Off",
                saved_hdmi_rec_control="On",
                post_time_code_output="Off",
                post_hdmi_rec_control="On",
            ),
            HdmiRecControl4chAudioAndMediaVaultSpec(
                external_recorder_rec_trigger_enabled=False,
            ),
        ):
            rep = evaluate_hdmi_reccontrol_4chaudio_and_media_vault(bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P255_BLOCKED_HDMI_REC_CTRL_WITHOUT_TC_OUTPUT)
            self.assertGreaterEqual(rep.hdmi_rec_ctrl_without_tc_violations, 1)

    def test_30_pillar43b_time_code_output_on_with_rec_control_off_is_valid(self) -> None:
        spec = HdmiRecControl4chAudioAndMediaVaultSpec(
            pre_time_code_output="On",
            pre_hdmi_rec_control="Off",
            post_time_code_output="On",
            post_hdmi_rec_control="Off",
            external_recorder_rec_trigger_enabled=False,
        )
        self.assertTrue(evaluate_hdmi_reccontrol_4chaudio_and_media_vault(spec).passed)

    def test_31_pillar43b_4ch_audio_output_ch1_ch2_vs_ch3_ch4_routing(self) -> None:
        ch12_2ch = HdmiRecControl4chAudioAndMediaVaultSpec(
            pre_4ch_audio_output="CH1/CH2",
            post_4ch_audio_output="CH1/CH2",
            mi_shoe_4ch_audio_active=False,
            shoe_audio_set_mode="48kHz/16bit 2ch",
            hdmi_routed_audio_pair=P255_HDMI_CH1_CH2_PAIR,
        )
        self.assertTrue(evaluate_hdmi_reccontrol_4chaudio_and_media_vault(ch12_2ch).passed)

        ch12_4ch = replace(
            ch12_2ch,
            mi_shoe_4ch_audio_active=True,
            shoe_audio_set_mode="48kHz/24bit 4ch",
        )
        self.assertTrue(evaluate_hdmi_reccontrol_4chaudio_and_media_vault(ch12_4ch).passed)

        ch34_4ch = HdmiRecControl4chAudioAndMediaVaultSpec(
            pre_4ch_audio_output="CH3/CH4",
            post_4ch_audio_output="CH3/CH4",
            mi_shoe_4ch_audio_active=True,
            shoe_audio_set_mode="48kHz/24bit 4ch",
            hdmi_routed_audio_pair=P255_HDMI_CH3_CH4_PAIR,
        )
        self.assertTrue(evaluate_hdmi_reccontrol_4chaudio_and_media_vault(ch34_4ch).passed)

    def test_32_pillar43b_rejects_4ch_audio_pair_mismatch_or_ch3_ch4_without_4ch_mi_shoe(self) -> None:
        for bad in (
            HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_4ch_audio_output="CH1/CH2",
                post_4ch_audio_output="CH1/CH2",
                hdmi_routed_audio_pair=P255_HDMI_CH3_CH4_PAIR,
            ),
            HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_4ch_audio_output="CH3/CH4",
                post_4ch_audio_output="CH3/CH4",
                mi_shoe_4ch_audio_active=True,
                shoe_audio_set_mode="48kHz/24bit 4ch",
                hdmi_routed_audio_pair=P255_HDMI_CH1_CH2_PAIR,
            ),
            HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_4ch_audio_output="CH3/CH4",
                post_4ch_audio_output="CH3/CH4",
                mi_shoe_4ch_audio_active=False,
                shoe_audio_set_mode="48kHz/24bit 2ch",
                hdmi_routed_audio_pair=P255_HDMI_CH3_CH4_PAIR,
            ),
        ):
            rep = evaluate_hdmi_reccontrol_4chaudio_and_media_vault(bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P255_BLOCKED_HDMI_4CH_AUDIO_ROUTING_MISMATCH)

    def test_33_pillar43b_rec_media_dur_hdmi_off_inhibits_clip_and_proxy_while_on_allows_non_vault(
        self,
    ) -> None:
        non_vault_on = HdmiRecControl4chAudioAndMediaVaultSpec(
            pre_rec_media_dur_hdmi="On",
            post_rec_media_dur_hdmi="On",
            hdmi_connected=True,
            internal_slot1_slot2_clip_rec_inhibited=False,
            proxy_recording_inhibited=False,
            slot1_tier0_vault_active=False,
        )
        self.assertTrue(evaluate_hdmi_reccontrol_4chaudio_and_media_vault(non_vault_on).passed)

    def test_34_pillar43b_rejects_slot1_vault_write_hazards_and_cross_model_camset(self) -> None:
        for bad in (
            HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_rec_media_dur_hdmi="On",
                post_rec_media_dur_hdmi="On",
                hdmi_connected=True,
                internal_slot1_slot2_clip_rec_inhibited=False,
                proxy_recording_inhibited=False,
                slot1_tier0_vault_active=True,
            ),
            HdmiRecControl4chAudioAndMediaVaultSpec(
                slot1_tier0_vault_active=True,
                slot1_sdxc_wp_locked=False,
            ),
            HdmiRecControl4chAudioAndMediaVaultSpec(
                slot1_tier0_vault_active=True,
                camset_save_to_slot1_attempted=True,
            ),
            HdmiRecControl4chAudioAndMediaVaultSpec(
                slot1_hdmi_rec_vault_mutation_bytes=512,
            ),
            HdmiRecControl4chAudioAndMediaVaultSpec(
                camset_load_after_reset=True,
                camset_source_model="ILME-FX6",
            ),
            HdmiRecControl4chAudioAndMediaVaultSpec(
                camset_load_after_reset=True,
                camset_read_only_load=False,
            ),
        ):
            rep = evaluate_hdmi_reccontrol_4chaudio_and_media_vault(bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P255_BLOCKED_SLOT1_HDMI_REC_VAULT_MUTATION_OR_CAMSET_DRIFT)

    def test_35_pillar43b_rejects_invalid_spec_overlay_escape_h0_h3_drift_and_write_unlock(self) -> None:
        self.assertEqual(
            evaluate_hdmi_reccontrol_4chaudio_and_media_vault(
                HdmiRecControl4chAudioAndMediaVaultSpec(camera_model="ILME-FX6")
            ).block_code,
            P255_BLOCKED_INVALID_HDMI_OUTPUT_SETTINGS_SPEC,
        )
        self.assertEqual(
            evaluate_hdmi_reccontrol_4chaudio_and_media_vault(
                HdmiRecControl4chAudioAndMediaVaultSpec(overlay_dir="/dev/mmcblk0p2")
            ).block_code,
            P255_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
        )
        self.assertEqual(
            evaluate_hdmi_reccontrol_4chaudio_and_media_vault(
                HdmiRecControl4chAudioAndMediaVaultSpec(backup_bin_h3_sha256="0" * 64)
            ).block_code,
            P255_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
        )
        self.assertEqual(
            evaluate_hdmi_reccontrol_4chaudio_and_media_vault(
                HdmiRecControl4chAudioAndMediaVaultSpec(persistent_write_unlock_requested=True)
            ).block_code,
            P255_BLOCKED_SAFETY_POLICY_VIOLATION,
        )

    def test_36_pillar43b_6_scenario_suite_passes_all_6_with_expected_codes(self) -> None:
        res = run_pillar43b_hdmi_reccontrol_4chaudio_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P255_STATUS_VERIFIED_PILLAR_43B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P255_PILLAR_43B_SCENARIO_IDS)
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])

    def test_37_combined_verifier_and_symmetry_alias_pass_dual_mode_and_propagate_failures(self) -> None:
        r_def = verify_auto_slow_shutter_hdmi_reccontrol_and_breathing_vault()
        r_cr = verify_auto_slow_shutter_hdmi_reccontrol_breathing_vault(force_clean_room=True)
        self.assertTrue(r_def.all_passed)
        self.assertTrue(r_cr.all_passed)
        self.assertEqual(r_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r_cr.status, P255_STATUS_VERIFIED_PILLAR43_SUITE)
        self.assertIsInstance(r_cr.to_dict(), dict)

        r_bad = verify_auto_slow_shutter_hdmi_reccontrol_and_breathing_vault(
            hdmi_spec=HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_time_code_output="Off",
                pre_hdmi_rec_control="On",
                post_time_code_output="Off",
                post_hdmi_rec_control="On",
            ),
            force_clean_room=True,
        )
        self.assertFalse(r_bad.all_passed)
        self.assertEqual(r_bad.status, P255_STATUS_FAIL_PILLAR43_SUITE)
        self.assertGreaterEqual(r_bad.hdmi_rec_ctrl_without_tc_violations, 1)

    def test_38_standalone_suite_deterministic_digest_in_default_and_clean_room_modes(self) -> None:
        rep_d1 = run_pillar43_standalone_suite()
        rep_d2 = run_pillar43_standalone_suite()
        self.assertTrue(rep_d1.all_passed)
        self.assertEqual(rep_d1.suite_sha256, rep_d2.suite_sha256)

        rep_cr1 = run_pillar43_standalone_suite(force_clean_room=True)
        rep_cr2 = run_pillar43_standalone_suite(force_clean_room=True)
        self.assertTrue(rep_cr1.all_passed)
        self.assertEqual(rep_cr1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_cr1.suite_sha256, rep_cr2.suite_sha256)
        self.assertEqual(len(rep_cr1.suite_sha256), 64)

    def test_39_compute_expected_auto_slow_shutter_lockouts_deterministic_ordering(self) -> None:
        combined = compute_expected_auto_slow_shutter_lockouts(
            shooting_domain="S&Q",
            exposure_mode="Flexible Exp. Mode",
            flexible_exp_shutter_ctrl="Manual",
            iso_setting="ISO 3200",
            log_shooting_mode="Cine EI",
        )
        self.assertEqual(
            combined,
            (
                "S&Q_MOTION",
                "NON_AUTO_ISO",
                "FLEXIBLE_EXP_MANUAL_SHUTTER",
                "LOG_CINE_EI_OR_CINE_EI_QUICK",
            ),
        )
        self.assertEqual(P255_LOG_CINE_EI_LOCKOUT_MODES, ("Cine EI Quick", "Cine EI"))

    def test_40_master_43_pillar_specs_extend_master_42_cleanly(self) -> None:
        self.assertEqual(MASTER_43_PILLAR_COUNT, 43)
        self.assertEqual(len(MASTER_43_PILLAR_SPECS), 43)
        self.assertEqual(len(MASTER_43_PILLAR_IDS), 43)
        self.assertEqual(len(set(MASTER_43_PILLAR_IDS)), 43)
        self.assertEqual(MASTER_43_PILLAR_SPECS[:42], MASTER_42_PILLAR_SPECS)
        self.assertEqual(
            MASTER_43_PILLAR_SPECS[42],
            (
                43,
                "pillar_43_auto_slow_shutter_hdmi_reccontrol_breathing_vault",
                "Phase 255",
                "fx3_recovery.realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier",
            ),
        )

    def test_41_master_43pillar_default_mode_43_of_43_verified_under_budget(self) -> None:
        rep = self.master43_default
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P255_STATUS_VERIFIED_43OF43_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 43)
        self.assertEqual(rep.pillars_passed, 43)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertLess(rep.elapsed_seconds, 4.0)

    def test_42_master_43pillar_clean_room_mode_43_of_43_verified(self) -> None:
        rep = self.master43_clean_room
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.status, P255_STATUS_VERIFIED_43OF43_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 43)
        self.assertEqual(rep.pillars_passed, 43)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)

    def test_43_master_43pillar_zero_write_and_wave41_plus_upstream_invariants_preserved(self) -> None:
        rep = self.master43_default
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

    def test_44_master_43pillar_individual_pillar_numbering_and_status(self) -> None:
        rep = self.master43_clean_room
        self.assertEqual([p.pillar_number for p in rep.pillars], list(range(1, 44)))
        self.assertTrue(all(p.passed for p in rep.pillars))
        p43 = rep.pillars[42]
        self.assertEqual(p43.pillar_number, 43)
        self.assertEqual(p43.pillar_id, "pillar_43_auto_slow_shutter_hdmi_reccontrol_breathing_vault")
        self.assertEqual(p43.phase_label, "Phase 255")
        self.assertEqual(p43.key_metrics["pillar_43a_auto_slow_shutter_breathing_vault"], "6/6")
        self.assertEqual(p43.key_metrics["pillar_43b_hdmi_reccontrol_4chaudio_vault"], "6/6")
        self.assertEqual(p43.key_metrics["auto_slow_shutter_lockout_bypass_events"], 0)
        self.assertEqual(p43.key_metrics["auto_slow_shutter_angle_overlap_events"], 0)
        self.assertEqual(p43.key_metrics["breathing_comp_raw_or_240p_bypass_events"], 0)
        self.assertEqual(p43.key_metrics["hdmi_rec_ctrl_without_tc_violations"], 0)
        self.assertEqual(p43.key_metrics["slot1_hdmi_rec_vault_mutation_bytes"], 0)
        self.assertEqual(p43.key_metrics["donor_files_inspected"], 12)

    def test_45_master_43pillar_json_serializable_without_nan(self) -> None:
        rep = self.master43_clean_room
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(encoded)
        self.assertEqual(parsed["schema"], PHASE255_SCHEMA)
        self.assertEqual(parsed["pillar_count"], 43)
        self.assertEqual(parsed["pillars_passed"], 43)
        self.assertEqual(len(parsed["master_43pillar_sha256"]), 64)

    def test_46_master_43pillar_fault_injection_on_pillar_43_marks_42_of_43(self) -> None:
        with mock.patch.object(
            p255, "evaluate_realhw_42pillar_recovery_master", return_value=self.master42_clean_room
        ):
            rep = evaluate_realhw_43pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_43_auto_slow_shutter_hdmi_reccontrol_breathing_vault",
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P255_STATUS_FAIL_43OF43_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 43)
        self.assertEqual(rep.pillars_passed, 42)
        self.assertEqual(
            rep.failed_pillars,
            ("pillar_43_auto_slow_shutter_hdmi_reccontrol_breathing_vault",),
        )

    def test_47_master_43pillar_fault_injection_on_upstream_pillar_1_and_42_marks_42_of_43(self) -> None:
        for pid in (MASTER_43_PILLAR_IDS[0], MASTER_43_PILLAR_IDS[41]):
            with self.subTest(pillar_id=pid):
                with mock.patch.object(
                    p255, "evaluate_realhw_42pillar_recovery_master", return_value=self.master42_clean_room
                ):
                    rep = evaluate_realhw_43pillar_recovery_master(
                        force_clean_room=True,
                        fault_inject_pillar=pid,
                    )
                self.assertFalse(rep.all_passed)
                self.assertEqual(rep.pillars_passed, 42)
                self.assertEqual(rep.failed_pillars, (pid,))


    def test_48_master_43pillar_rejects_unknown_fault_inject_pillar(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_43pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_999",
            )

    def test_49_master_43pillar_aliases_forward_cleanly(self) -> None:
        cached = self.master43_clean_room
        with mock.patch.object(
            p255, "evaluate_realhw_43pillar_recovery_master", return_value=cached
        ) as mocked_eval:
            r1 = evaluate_43pillar_recovery_master(force_clean_room=True)
            r2 = verify_43pillar_recovery_suite(force_clean_room=True)
        self.assertIs(r1, cached)
        self.assertIs(r2, cached)
        self.assertEqual(mocked_eval.call_count, 2)

    def test_50_safety_invariant_tamper_detection_blocks_master(self) -> None:
        with mock.patch.object(p255, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            with self.assertRaises(ValueError):
                evaluate_realhw_43pillar_recovery_master(force_clean_room=True)

    def test_51_safety_invariant_tamper_detection_blocks_standalone_and_combined(self) -> None:
        with mock.patch.object(p255, "PASSIVE_TX_BYTES_EMITTED", 1):
            rep_sa = run_pillar43_standalone_suite(force_clean_room=True)
            rep_cb = verify_auto_slow_shutter_hdmi_reccontrol_and_breathing_vault(force_clean_room=True)
        self.assertFalse(rep_sa.all_passed)
        self.assertEqual(rep_sa.status, P255_STATUS_FAIL_PILLAR43_SUITE)
        self.assertTrue(any("PASSIVE_TX_BYTES_EMITTED" in e for e in rep_sa.errors))
        self.assertFalse(rep_cb.all_passed)
        self.assertTrue(any("PASSIVE_TX_BYTES_EMITTED" in e for e in rep_cb.errors))

    def test_52_master_43pillar_detects_upstream_m42_safety_or_domain_violation(self) -> None:
        for field_name, bad_val in (
            ("shutter_angle_common_bleed_events", 1),
            ("diff_set_transition_corruption_events", 1),
            ("fx3_has_builtin_evf", True),
            ("physical_device_writes", 1),
        ):
            with self.subTest(field=field_name):
                m42_bad = replace(self.master42_clean_room, **{field_name: bad_val})
                with mock.patch.object(
                    p255, "evaluate_realhw_42pillar_recovery_master", return_value=m42_bad
                ):
                    rep = evaluate_realhw_43pillar_recovery_master(force_clean_room=True)
                self.assertFalse(rep.all_passed)
                self.assertTrue(any(field_name in e for e in rep.errors))

    def test_53_master_43pillar_detects_p43_domain_counter_violations(self) -> None:
        base_p43 = run_pillar43_standalone_suite(force_clean_room=True)
        for field_name, bad_val in (
            ("auto_slow_shutter_lockout_bypass_events", 1),
            ("auto_slow_shutter_angle_overlap_events", 1),
            ("breathing_comp_raw_or_240p_bypass_events", 1),
            ("hdmi_rec_ctrl_without_tc_violations", 1),
            ("slot1_hdmi_rec_vault_mutation_bytes", 256),
            ("hardware_live_attachment_authorized", True),
        ):
            with self.subTest(field=field_name):
                p43_bad = replace(base_p43, **{field_name: bad_val})
                with (
                    mock.patch.object(
                        p255,
                        "evaluate_realhw_42pillar_recovery_master",
                        return_value=self.master42_clean_room,
                    ),
                    mock.patch.object(p255, "run_pillar43_standalone_suite", return_value=p43_bad),
                ):
                    rep = evaluate_realhw_43pillar_recovery_master(force_clean_room=True)
                self.assertFalse(rep.all_passed)
                self.assertTrue(any(field_name in e for e in rep.errors))

    def test_54_all_shutter_angle_fx3_firmware_versions_6_00_to_7_02_accepted(self) -> None:
        self.assertIn("7.02", P255_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS)
        for ver in P255_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS:
            with self.subTest(fw_version=ver):
                spec = AutoSlowShutterAndBreathingCompVaultSpec(
                    fw_version=ver,
                    exposure_mode="M",
                    reported_lockout_conditions=("MANUAL_EXPOSURE_M",),
                    auto_slow_shutter_effectively_active=False,
                    movie_shutter_mode="Angle",
                    movie_shutter_angle_deg=180.0,
                    shutter_angle_effectively_active=True,
                )
                self.assertTrue(evaluate_auto_slow_shutter_and_breathing_comp_vault(spec).passed)

    def test_55_breathing_comp_firmware_boundary_3_00_plus_on_vs_2_xx_off(self) -> None:
        for ver in P255_FX3_BREATHING_COMP_MIN_FW_VERSIONS:
            with self.subTest(fw_version=ver):
                self.assertTrue(
                    evaluate_auto_slow_shutter_and_breathing_comp_vault(
                        AutoSlowShutterAndBreathingCompVaultSpec(fw_version=ver)
                    ).passed
                )
        for pre_ver in ("2.00", "2.01", "2.02"):
            with self.subTest(pre_ver=pre_ver):
                ok_off = AutoSlowShutterAndBreathingCompVaultSpec(
                    fw_version=pre_ver,
                    pre_reset_breathing_comp="Off",
                    post_reset_breathing_comp="Off",
                    breathing_comp_effectively_active=False,
                    fov_crop_applied=False,
                )
                self.assertTrue(evaluate_auto_slow_shutter_and_breathing_comp_vault(ok_off).passed)
                bad_on = AutoSlowShutterAndBreathingCompVaultSpec(fw_version=pre_ver)
                rep_bad = evaluate_auto_slow_shutter_and_breathing_comp_vault(bad_on)
                self.assertFalse(rep_bad.passed)
                self.assertEqual(rep_bad.block_code, P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS)

    def test_56_all_supported_fx3_firmware_versions_accepted_for_pillar43b_hdmi_settings(self) -> None:
        for ver in P255_FX3_SUPPORTED_FW_VERSIONS:
            with self.subTest(fw_version=ver):
                self.assertTrue(
                    evaluate_hdmi_reccontrol_4chaudio_and_media_vault(
                        HdmiRecControl4chAudioAndMediaVaultSpec(fw_version=ver)
                    ).passed
                )

    def test_57_all_10_camset_filenames_across_slots_1_and_2_accepted_in_pillar43a_and_43b(self) -> None:
        self.assertEqual(len(P255_CAMSET_FILENAMES), 10)
        for slot in (1, 2):
            for fname in P255_CAMSET_FILENAMES:
                with self.subTest(slot=slot, fname=fname):
                    self.assertTrue(
                        evaluate_auto_slow_shutter_and_breathing_comp_vault(
                            AutoSlowShutterAndBreathingCompVaultSpec(
                                camset_load_after_reset=True,
                                camset_slot=slot,
                                camset_filename=fname,
                                camset_read_only_load=True,
                            )
                        ).passed
                    )
                    self.assertTrue(
                        evaluate_hdmi_reccontrol_4chaudio_and_media_vault(
                            HdmiRecControl4chAudioAndMediaVaultSpec(
                                camset_load_after_reset=True,
                                camset_slot=slot,
                                camset_filename=fname,
                                camset_read_only_load=True,
                            )
                        ).passed
                    )

    def test_58_hdmi_disconnected_keeps_external_rec_trigger_and_media_inhibition_inactive(self) -> None:
        spec = HdmiRecControl4chAudioAndMediaVaultSpec(
            hdmi_connected=False,
            external_recorder_rec_trigger_enabled=False,
            internal_slot1_slot2_clip_rec_inhibited=False,
            proxy_recording_inhibited=False,
        )
        self.assertTrue(evaluate_hdmi_reccontrol_4chaudio_and_media_vault(spec).passed)

    def test_59_tier0_backup_bin_pinned_sha256_and_wave41_defaults_consistent(self) -> None:
        self.assertEqual(
            P255_PINNED_FX3_BACKUP_BIN_SHA256,
            "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        )
        self.assertEqual(P255_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG, 180.0)
        self.assertEqual(P255_MOVIE_SHUTTER_MODE_DEFAULT, "Shutter Speed")
        self.assertEqual(P255_ISO_AUTO_TOKEN, "ISO AUTO")
        self.assertEqual(P255_SLOT1_VAULT_SLOT, 1)
        self.assertEqual(P255_SHUTTER_MODE_MENU_PATH, ("MENU", "Shooting", "Shutter/Silent", "Shutter Mode"))
        self.assertEqual(P255_HDMI_RAW_OUTPUT_MODES, ("Off", "On"))
        self.assertEqual(P255_TIME_CODE_OUTPUT_MODES, ("Off", "On"))
        self.assertEqual(P255_HDMI_REC_CONTROL_MODES, ("Off", "On"))
        self.assertEqual(P255_RESET_ACTIONS, ("NONE", "Camera Settings Reset", "Reset Network Set.", "Initialize"))
        self.assertIn("239.76p", P255_MOVIE_AND_SQ_FRAME_RATES)

    def test_60_donor_bounded_reader_handles_missing_and_open_errors_gracefully(self) -> None:
        with mock.patch.object(p255, "resolve_donor_path", return_value=None):
            ok, total_b, read_b, kind, digest, raw = p255._read_donor_readonly_bounded("nonexistent.bin")
        self.assertFalse(ok)
        self.assertEqual((total_b, read_b, kind, digest, raw), (0, 0, "MISSING", "", b""))

        with (
            mock.patch.object(p255, "resolve_donor_path", return_value=Path("/nonexistent_phase255_file")),
            mock.patch.object(os, "open", side_effect=OSError("ENOENT")),
        ):
            ok2, _, _, kind2, _, _ = p255._read_donor_readonly_bounded("err.bin")
        self.assertFalse(ok2)
        self.assertEqual(kind2, "OPEN_ERROR")

    def test_61_donor_snapshot_failure_or_budget_overrun_propagates_to_reports(self) -> None:
        good_snap = inspect_phase255_donors_readonly(force_clean_room=True)
        bad_snap = replace(good_snap, all_donors_present=False, under_0_15s_budget=False, elapsed_seconds=0.25)
        with mock.patch.object(p255, "inspect_phase255_donors_readonly", return_value=bad_snap):
            sa = run_pillar43_standalone_suite(force_clean_room=True)
            cb = verify_auto_slow_shutter_hdmi_reccontrol_and_breathing_vault(force_clean_room=True)
        self.assertFalse(sa.all_passed)
        self.assertTrue(any("donor verification failed" in e for e in sa.errors))
        self.assertTrue(any("exceeded 2.0s budget" in e for e in sa.errors))
        self.assertFalse(cb.all_passed)

    def test_62_backward_compatibility_callable_exports_22_to_42(self) -> None:
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
        ):
            with self.subTest(pillars=count):
                self.assertTrue(callable(getattr(fx3_recovery, attr_name)))
        self.assertEqual([p.pillar_number for p in self.master43_clean_room.pillars], list(range(1, 44)))

    def test_63_cli_verify_auto_slow_shutter_hdmi_reccontrol_breathing_vault_summary_and_json(self) -> None:
        rc_txt, out_txt = _run_inprocess_cli("verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault")
        self.assertEqual(rc_txt, 0)
        self.assertIn(
            "status=VERIFIED_PILLAR43_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_VAULT",
            out_txt,
        )
        self.assertIn("pillar_43a=6/6", out_txt)
        self.assertIn("pillar_43b=6/6", out_txt)
        self.assertIn("auto_slow_shutter_lockout_bypass_events=0", out_txt)
        self.assertIn("auto_slow_shutter_angle_overlap_events=0", out_txt)
        self.assertIn("breathing_comp_raw_or_240p_bypass_events=0", out_txt)
        self.assertIn("hdmi_rec_ctrl_without_tc_violations=0", out_txt)
        self.assertIn("slot1_hdmi_rec_vault_mutation_bytes=0", out_txt)
        self.assertIn("hardware_live_attachment_authorized=False", out_txt)

        rc_js, out_js = _run_inprocess_cli(
            "verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault", "--json"
        )
        self.assertEqual(rc_js, 0)
        payload = json.loads(out_js)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["schema"], PHASE255_SCHEMA)

    def test_64_cli_verify_auto_slow_shutter_hdmi_reccontrol_breathing_vault_force_clean_room(self) -> None:
        rc, out = _run_inprocess_cli(
            "verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault",
            "--force-clean-room",
            "--json",
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["auto_slow_shutter_lockout_bypass_events"], 0)
        self.assertEqual(payload["auto_slow_shutter_angle_overlap_events"], 0)
        self.assertEqual(payload["breathing_comp_raw_or_240p_bypass_events"], 0)
        self.assertEqual(payload["hdmi_rec_ctrl_without_tc_violations"], 0)
        self.assertEqual(payload["slot1_hdmi_rec_vault_mutation_bytes"], 0)
        self.assertFalse(payload["hardware_live_attachment_authorized"])

    def test_65_cli_verify_auto_slow_shutter_hdmi_reccontrol_breathing_vault_subprocess_smoke(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault",
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

    def test_66_cli_verify_43pillar_recovery_summary_json_and_clean_room_forwarding(self) -> None:
        with mock.patch.object(
            cli_main, "verify_43pillar_recovery_suite", return_value=self.master43_default
        ):
            rc_txt, out_txt = _run_inprocess_cli("verify-43pillar-recovery")
            self.assertEqual(rc_txt, 0)
            self.assertIn("status=VERIFIED_43OF43_PILLAR_RECOVERY_MASTER", out_txt)
            self.assertIn("pillars=43/43", out_txt)
            self.assertIn("pillar43_a=6/6", out_txt)
            self.assertIn("pillar43_b=6/6", out_txt)

            rc_js, out_js = _run_inprocess_cli("verify-43pillar-recovery", "--json")
            self.assertEqual(rc_js, 0)
            payload = json.loads(out_js)
            self.assertEqual(payload["pillar_count"], 43)
            self.assertEqual(payload["pillars_passed"], 43)

        with mock.patch.object(
            cli_main, "verify_43pillar_recovery_suite", return_value=self.master43_clean_room
        ) as mocked_suite:
            rc_cr, out_cr = _run_inprocess_cli("verify-43pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc_cr, 0)
        mocked_suite.assert_called_once_with(force_clean_room=True)
        self.assertEqual(json.loads(out_cr)["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_67_cli_out_creates_exclusive_directories_for_pillar43_and_43pillar_master(self) -> None:
        here = Path(__file__).resolve().parent
        out_p43 = here / f"_tmp_p255_p43_{os.getpid()}"
        rep_p43 = out_p43 / "pillar43-auto-slow-shutter-hdmi-reccontrol-breathing-vault-report.json"
        out_m43 = here / f"_tmp_p255_m43_{os.getpid()}"
        rep_m43 = out_m43 / "43pillar-recovery-master-report.json"
        for f, d in ((rep_p43, out_p43), (rep_m43, out_m43)):
            if f.is_file():
                f.unlink()
            if d.is_dir():
                d.rmdir()
        try:
            rc1, _ = _run_inprocess_cli(
                "verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault",
                "--force-clean-room",
                "--out",
                str(out_p43),
            )
            self.assertEqual(rc1, 0)
            self.assertTrue(rep_p43.is_file())
            self.assertEqual(json.loads(rep_p43.read_text(encoding="utf-8"))["schema"], PHASE255_SCHEMA)

            with mock.patch.object(
                cli_main, "verify_43pillar_recovery_suite", return_value=self.master43_clean_room
            ):
                rc2, _ = _run_inprocess_cli("verify-43pillar-recovery", "--out", str(out_m43))
            self.assertEqual(rc2, 0)
            self.assertTrue(rep_m43.is_file())
            self.assertEqual(json.loads(rep_m43.read_text(encoding="utf-8"))["pillar_count"], 43)
        finally:
            for f, d in ((rep_p43, out_p43), (rep_m43, out_m43)):
                if f.is_file():
                    f.unlink()
                if d.is_dir():
                    d.rmdir()

    def test_68_cli_returns_nonzero_exit_code_2_when_pillar43_or_master43_fails(self) -> None:
        bad_p43 = replace(
            run_pillar43_standalone_suite(force_clean_room=True),
            all_passed=False,
            status=P255_STATUS_FAIL_PILLAR43_SUITE,
        )
        with mock.patch.object(cli_main, "run_pillar43_standalone_suite", return_value=bad_p43):
            rc1, _ = _run_inprocess_cli(
                "verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault", "--json"
            )
        self.assertEqual(rc1, 2)

        bad_m43 = replace(
            self.master43_clean_room,
            all_passed=False,
            status=P255_STATUS_FAIL_43OF43_AGGREGATOR,
        )
        with mock.patch.object(cli_main, "verify_43pillar_recovery_suite", return_value=bad_m43):
            rc2, _ = _run_inprocess_cli("verify-43pillar-recovery", "--json")
        self.assertEqual(rc2, 2)


if __name__ == "__main__":
    unittest.main()
