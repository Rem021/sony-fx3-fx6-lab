"""Phase 251 — Dual-mode unit tests for Pillar 42 (`[Different Set for Still/Mv]` 8-item asymmetric
Common->Separate / Separate->Common transitions, `[Camera Settings Reset]` & `[Reset Network Set.]`
survival, and `Ver. 7.02` `[Shutter Mode]=[Angle]` independent split; `[Custom Key/Dial Set.]`
Still/Movie/Playback 3-domain keymaps, factory Cinema-Line `Aperture` / `ISO/EI` / `Shutter Speed`
dials, `[Follow Custom]`, `[My Dial 1..3]`, and `O_RDONLY` Slot-1 `CAMSET01.DAT` round-trip; plus
`[Remain Shoot Display]` still-buffer-only scope and EVF-less `ILME-FX3` `ilc/2210` topology) and
unified `42/42` recovery master (`verify-42pillar-recovery` /
`verify-diff-set-still-mv-custom-key-remain-shoot-vault`)."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import (
    realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier as p251,
)
from fx3_recovery.realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier import (
    MASTER_41_PILLAR_SPECS,
    Master41PillarRecoveryReport,
    evaluate_realhw_41pillar_recovery_master,
)
from fx3_recovery.realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_42_PILLAR_COUNT,
    MASTER_42_PILLAR_IDS,
    MASTER_42_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P251_ASSIGNABLE_CUSTOM_CONTROLS,
    P251_BLOCKED_CUSTOM_KEY_OR_REMAIN_SHOOT_RESET_DRIFT,
    P251_BLOCKED_DIAL_ISO_EI_OR_FOLLOW_CUSTOM_MISMATCH,
    P251_BLOCKED_DIFF_SET_COMMON_TO_SEPARATE_DRIFT,
    P251_BLOCKED_DIFF_SET_RESET_SURVIVAL_DRIFT,
    P251_BLOCKED_DIFF_SET_SEPARATE_TO_COMMON_DRIFT,
    P251_BLOCKED_INVALID_CUSTOM_KEY_OR_REMAIN_SHOOT_SPEC,
    P251_BLOCKED_INVALID_DIFF_SET_SPEC,
    P251_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P251_BLOCKED_REMAIN_SHOOT_SCOPE_OR_EVF_TOPOLOGY_SPOOF,
    P251_BLOCKED_SAFETY_POLICY_VIOLATION,
    P251_BLOCKED_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION,
    P251_BLOCKED_SLOT1_CUSTOM_KEY_VAULT_MUTATION_OR_CAMSET_DRIFT,
    P251_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P251_CAMSET_FILENAMES,
    P251_COMMON_TO_SEPARATE_STILL_ONLY_EXCEPTION,
    P251_CONTROL_WHEEL_DEFAULT,
    P251_CUSTOM_KEY_3_DOMAINS,
    P251_CUSTOM_KEY_DIAL_MENU_PATH,
    P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES,
    P251_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG,
    P251_DEFAULT_STILL_CUSTOM_WB_REGISTER,
    P251_DIFF_SET_8_ITEMS,
    P251_DIFF_SET_FACTORY_CHECKED_ITEMS,
    P251_DIFF_SET_FACTORY_PARAM_DEFAULTS,
    P251_DIFF_SET_MENU_PATH,
    P251_DIFF_SET_TRANSITION_CORRUPTION_EVENTS,
    P251_DIFF_SET_TRANSITION_KINDS,
    P251_EVF_FINDER_MONITOR_SPOOF_EVENTS,
    P251_FACTORY_DIAL_DEFAULTS,
    P251_FACTORY_MOVIE_KEYMAP,
    P251_FACTORY_PLAYBACK_KEYMAP,
    P251_FACTORY_STILL_KEYMAP,
    P251_FOLLOW_CUSTOM_TOKEN,
    P251_FRONT_DIAL_DEFAULT,
    P251_FX3_FW_VERSION,
    P251_FX3_HAS_BUILTIN_EVF,
    P251_FX3_HELPGUIDE_ID,
    P251_FX3_MODEL_ID,
    P251_FX3_MODEL_NAME,
    P251_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS,
    P251_FX3_SUPPORTED_FW_VERSIONS,
    P251_FX6_DONOR_FW_VERSION,
    P251_FX6_DONOR_MODEL_NAME,
    P251_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P251_MOVIE_CUSTOM_WB_STILL_ONLY_SENTINEL,
    P251_MOVIE_SHUTTER_MODES,
    P251_MOVIE_SHUTTER_MODE_DEFAULT,
    P251_MY_DIAL_SLOTS,
    P251_PILLAR_42A_SCENARIO_IDS,
    P251_PILLAR_42B_SCENARIO_IDS,
    P251_PINNED_FX3_BACKUP_BIN_SHA256,
    P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
    P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
    P251_PINNED_FX3_LIBGPE_SO_BYTES,
    P251_PINNED_FX3_LIBGPE_SO_SHA256,
    P251_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
    P251_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
    P251_PINNED_FX6_LIBINFRAINPUT_SO_BYTES,
    P251_PINNED_FX6_LIBINFRAINPUT_SO_SHA256,
    P251_REAR_DIAL_DEFAULT,
    P251_RECALL_CUSTOM_HOLD_SLOTS,
    P251_REMAIN_SHOOT_DISPLAY_DEFAULT,
    P251_REMAIN_SHOOT_DISPLAY_MENU_PATH,
    P251_REMAIN_SHOOT_DISPLAY_MODES,
    P251_RESET_ACTIONS,
    P251_SEPARATE_TO_COMMON_STILL_RETAINED_EXCEPTIONS,
    P251_SHOOTING_EXPOSURE_MODES,
    P251_SHUTTER_ANGLE_COMMON_BLEED_EVENTS,
    P251_SHUTTER_MODE_MENU_PATH,
    P251_SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES,
    P251_SLOT1_VAULT_SLOT,
    P251_STATUS_FAIL_42OF42_AGGREGATOR,
    P251_STATUS_FAIL_PILLAR42_SUITE,
    P251_STATUS_VERIFIED_42OF42_AGGREGATOR,
    P251_STATUS_VERIFIED_PILLAR42_SUITE,
    P251_STATUS_VERIFIED_PILLAR_42A,
    P251_STATUS_VERIFIED_PILLAR_42B,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE251_SCHEMA,
    PHASE251_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    CustomKeyDialAndRemainShootVaultSpec,
    DiffSetStillMvAndShutterAngleVaultSpec,
    Master42PillarRecoveryReport,
    build_default_safe_custom_key_remain_shoot_vault_spec,
    build_default_safe_diff_set_still_mv_vault_spec,
    evaluate_42pillar_recovery_master,
    evaluate_custom_key_dial_and_remain_shoot_vault,
    evaluate_diff_set_still_mv_and_shutter_angle_vault,
    evaluate_realhw_42pillar_recovery_master,
    inspect_phase251_donors_readonly,
    run_pillar42_standalone_suite,
    run_pillar42a_diff_set_still_mv_vault_6_scenario_suite,
    run_pillar42b_custom_key_remain_shoot_vault_6_scenario_suite,
    verify_42pillar_recovery_suite,
    verify_diff_set_still_mv_custom_key_and_remain_shoot_vault,
    verify_diff_set_still_mv_custom_key_remain_shoot_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]


def _run_inprocess_cli(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with mock.patch.object(sys, "argv", ["fx3_recovery", *argv]), redirect_stdout(buf):
        rc = cli_main.main()
    return rc, buf.getvalue()


def _replace_8item_pair(
    pairs: tuple[tuple[str, str], ...],
    **overrides: str,
) -> tuple[tuple[str, str], ...]:
    d = dict(pairs)
    d.update(overrides)
    return tuple((k, d[k]) for k, _ in pairs)


class TestPhase251Pillar42And42PillarRecoveryMaster(unittest.TestCase):
    """68 fast dual-mode tests covering Pillar 42A, Pillar 42B, O_RDONLY donors, CLI & 42/42 master."""

    master42_default: Master42PillarRecoveryReport
    master42_clean_room: Master42PillarRecoveryReport
    master41_clean_room: Master41PillarRecoveryReport

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.master42_default = evaluate_realhw_42pillar_recovery_master()
        cls.master42_clean_room = evaluate_realhw_42pillar_recovery_master(force_clean_room=True)
        cls.master41_clean_room = evaluate_realhw_41pillar_recovery_master(force_clean_room=True)

    def test_01_hard_locked_zero_write_safety_constants(self) -> None:
        self.assertEqual(
            PHASE251_SCHEMA,
            "realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier_v1",
        )
        self.assertEqual(PHASE251_VERSION, "1.0.0")
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
        self.assertFalse(P251_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(P251_DIFF_SET_TRANSITION_CORRUPTION_EVENTS, 0)
        self.assertEqual(P251_SHUTTER_ANGLE_COMMON_BLEED_EVENTS, 0)
        self.assertEqual(P251_SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES, 0)
        self.assertFalse(P251_FX3_HAS_BUILTIN_EVF)
        self.assertEqual(P251_EVF_FINDER_MONITOR_SPOOF_EVENTS, 0)

    def test_02_wave40_menu_paths_8items_dials_and_remain_shoot_constants(self) -> None:
        self.assertEqual(P251_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P251_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P251_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P251_FX3_FW_VERSION, "7.02")
        self.assertEqual(P251_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P251_FX6_DONOR_FW_VERSION, "6.01")
        self.assertEqual(
            P251_DIFF_SET_MENU_PATH,
            ("MENU", "Setup", "Operation Customize", "Different Set for Still/Mv"),
        )
        self.assertEqual(
            P251_DIFF_SET_8_ITEMS,
            (
                "Aperture",
                "Shutter Speed",
                "ISO",
                "Exposure Comp.",
                "Metering Mode",
                "White Balance",
                "Picture Profile",
                "Focus Mode",
            ),
        )
        self.assertEqual(P251_COMMON_TO_SEPARATE_STILL_ONLY_EXCEPTION, "Custom White Balance")
        self.assertEqual(
            P251_SEPARATE_TO_COMMON_STILL_RETAINED_EXCEPTIONS,
            ("Aperture", "Shutter Speed", "Custom White Balance"),
        )
        self.assertEqual(
            P251_SHUTTER_MODE_MENU_PATH,
            ("MENU", "Shooting", "Shutter/Silent", "Shutter Mode"),
        )
        self.assertEqual(P251_MOVIE_SHUTTER_MODES, ("Shutter Speed", "Angle"))
        self.assertEqual(P251_MOVIE_SHUTTER_MODE_DEFAULT, "Shutter Speed")
        self.assertEqual(
            P251_CUSTOM_KEY_DIAL_MENU_PATH,
            ("MENU", "Setup", "Operation Customize", "Custom Key/Dial Set."),
        )
        self.assertEqual(P251_CUSTOM_KEY_3_DOMAINS, ("Still", "Movie", "Playback"))
        self.assertEqual(
            P251_FACTORY_DIAL_DEFAULTS,
            (("Front dial", "Aperture"), ("Rear dial", "ISO/EI"), ("Control Wheel", "Shutter Speed")),
        )
        self.assertEqual(
            P251_REMAIN_SHOOT_DISPLAY_MENU_PATH,
            ("MENU", "Setup", "Display Option", "Remain Shoot Display"),
        )
        self.assertEqual(P251_REMAIN_SHOOT_DISPLAY_DEFAULT, "Not Displayed")
        self.assertEqual(
            P251_REMAIN_SHOOT_DISPLAY_MODES,
            ("Not Displayed", "Always Display", "Shoot-Only Display"),
        )

    def test_03_package_exports_complete_and_free_of_duplicates_or_shadowing(self) -> None:
        all_exports = fx3_recovery.__all__
        self.assertEqual(len(p251.__all__), len(set(p251.__all__)))
        self.assertEqual(
            all_exports.count("realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier"),
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
        for sym in p251.__all__:
            self.assertIn(sym, all_exports)
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing {sym} on fx3_recovery")
            if sym not in shared_safety_syms:
                self.assertEqual(all_exports.count(sym), 1, f"Duplicate Phase 251 export {sym}")
                self.assertIs(getattr(fx3_recovery, sym), getattr(p251, sym))

    def test_04_donor_inspection_default_mode_under_0_15s_zero_leak(self) -> None:
        snap = inspect_phase251_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 11)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertLess(snap.elapsed_seconds, 0.15)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_inspection_force_clean_room_synthetic_11_artifacts(self) -> None:
        snap = inspect_phase251_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 11)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(
            by_id["fx3_cameraondemandsaver_so"].total_bytes,
            P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
        )
        self.assertEqual(
            by_id["fx3_cameraondemandsaver_so"].digest_sha256,
            P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
        )
        self.assertEqual(by_id["fx6_libinfradial_so"].total_bytes, P251_PINNED_FX6_LIBINFRADIAL_SO_BYTES)
        self.assertEqual(
            by_id["fx6_libinfradial_so"].digest_sha256,
            P251_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
        )
        self.assertEqual(by_id["fx6_libinfrainput_so"].total_bytes, P251_PINNED_FX6_LIBINFRAINPUT_SO_BYTES)
        self.assertEqual(
            by_id["fx6_libinfrainput_so"].digest_sha256,
            P251_PINNED_FX6_LIBINFRAINPUT_SO_SHA256,
        )
        self.assertEqual(by_id["fx3_libgpe_so"].total_bytes, P251_PINNED_FX3_LIBGPE_SO_BYTES)
        self.assertEqual(by_id["fx3_libgpe_so"].digest_sha256, P251_PINNED_FX3_LIBGPE_SO_SHA256)

    def test_06_donor_inspection_automatic_clean_room_fallback_when_donors_missing(self) -> None:
        with mock.patch.object(p251, "resolve_donor_path", return_value=None):
            snap = inspect_phase251_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 11)

    def test_07_elf64_aarch64_token_helper_validates_headers_and_symbols(self) -> None:
        ok_bad, msg_bad = p251._check_elf64_aarch64_tokens(b"NOT_ELF_DATA", ())
        self.assertFalse(ok_bad)
        self.assertEqual(msg_bad, "NOT_ELF")
        hdr = bytearray(64)
        hdr[:4] = b"\x7fELF"
        hdr[4] = 2
        hdr[5] = 1
        hdr[18:20] = (183).to_bytes(2, "little")
        blob = bytes(hdr) + b"\x00InfraDial\x00ApiGetKeySta\x00CameraOnDemandSaver\x00"
        ok_good, msg_good = p251._check_elf64_aarch64_tokens(
            blob, (b"InfraDial", b"ApiGetKeySta", b"CameraOnDemandSaver")
        )
        self.assertTrue(ok_good)
        self.assertIn("InfraDial", msg_good)
        ok_miss, msg_miss = p251._check_elf64_aarch64_tokens(blob, (b"MissingSym",))
        self.assertFalse(ok_miss)
        self.assertIn("MISSING_TOKENS:MissingSym", msg_miss)

    def test_08_default_safe_diff_set_still_mv_spec_passes(self) -> None:
        spec = build_default_safe_diff_set_still_mv_vault_spec()
        rep = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P251_STATUS_VERIFIED_PILLAR_42A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.eight_items_catalog_verified)
        self.assertTrue(rep.diff_set_reset_survival_verified)
        self.assertTrue(rep.common_to_separate_transition_verified)
        self.assertTrue(rep.shutter_angle_independence_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.diff_set_transition_corruption_events, 0)
        self.assertEqual(rep.shutter_angle_common_bleed_events, 0)

    def test_09_diff_set_exact_8_items_catalog_enforced(self) -> None:
        spec_missing = DiffSetStillMvAndShutterAngleVaultSpec(
            configurable_8_items=P251_DIFF_SET_8_ITEMS[:7]
        )
        rep_missing = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_missing)
        self.assertFalse(rep_missing.passed)
        self.assertEqual(rep_missing.block_code, P251_BLOCKED_INVALID_DIFF_SET_SPEC)

        spec_bogus_checked = DiffSetStillMvAndShutterAngleVaultSpec(
            post_transition_checked_items=("Aperture", "Drive Mode"),
            post_reset_checked_items=("Aperture", "Drive Mode"),
        )
        rep_bogus = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_bogus_checked)
        self.assertFalse(rep_bogus.passed)
        self.assertEqual(rep_bogus.block_code, P251_BLOCKED_INVALID_DIFF_SET_SPEC)

    def test_10_common_to_separate_copies_non_custom_wb_items_to_both_still_and_movie(self) -> None:
        common_vals = _replace_8item_pair(
            P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES,
            ISO="1600",
            Aperture="F2.0",
        )
        spec_ok = DiffSetStillMvAndShutterAngleVaultSpec(
            pre_checked_items=(),
            transition_kind="COMMON_TO_SEPARATE",
            post_transition_checked_items=P251_DIFF_SET_8_ITEMS,
            pre_still_values=common_vals,
            pre_movie_values=common_vals,
            post_still_values=common_vals,
            post_movie_values=common_vals,
            post_reset_checked_items=P251_DIFF_SET_8_ITEMS,
        )
        self.assertTrue(evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_ok).passed)

        dropped_movie = _replace_8item_pair(common_vals, ISO="Auto")
        spec_dropped = replace(spec_ok, post_movie_values=dropped_movie)
        rep_drop = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_dropped)
        self.assertFalse(rep_drop.passed)
        self.assertEqual(rep_drop.block_code, P251_BLOCKED_DIFF_SET_COMMON_TO_SEPARATE_DRIFT)
        self.assertGreaterEqual(rep_drop.diff_set_transition_corruption_events, 1)

    def test_11_common_to_separate_custom_wb_exception_stays_still_only_and_rejects_movie_copy(self) -> None:
        cwb_pre = _replace_8item_pair(
            P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES,
            **{"White Balance": "Custom 1"},
        )
        cwb_post_movie = _replace_8item_pair(cwb_pre, **{"White Balance": "AWB"})
        spec_ok = DiffSetStillMvAndShutterAngleVaultSpec(
            pre_checked_items=(),
            transition_kind="COMMON_TO_SEPARATE",
            post_transition_checked_items=P251_DIFF_SET_8_ITEMS,
            pre_still_values=cwb_pre,
            pre_movie_values=cwb_pre,
            post_still_values=cwb_pre,
            post_movie_values=cwb_post_movie,
            custom_wb_copied_to_movie=False,
            post_movie_custom_wb=P251_MOVIE_CUSTOM_WB_STILL_ONLY_SENTINEL,
            post_reset_checked_items=P251_DIFF_SET_8_ITEMS,
        )
        self.assertTrue(evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_ok).passed)

        spec_bad_copy = replace(spec_ok, post_movie_values=cwb_pre, custom_wb_copied_to_movie=True)
        rep_bad = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_bad_copy)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P251_BLOCKED_DIFF_SET_COMMON_TO_SEPARATE_DRIFT)

    def test_12_separate_to_common_resets_standard_items_while_retaining_still_aperture_shutter_custom_wb(
        self,
    ) -> None:
        pre_still = (
            ("Aperture", "F1.8"),
            ("Shutter Speed", "1/250"),
            ("ISO", "6400"),
            ("Exposure Comp.", "+0.7EV"),
            ("Metering Mode", "Highlight"),
            ("White Balance", "Shade"),
            ("Picture Profile", "PP11 (S-Cinetone)"),
            ("Focus Mode", "MF"),
        )
        pre_movie = (
            ("Aperture", "F8.0"),
            ("Shutter Speed", "1/50"),
            ("ISO", "12800"),
            ("Exposure Comp.", "-1.0EV"),
            ("Metering Mode", "Center"),
            ("White Balance", "Tungsten"),
            ("Picture Profile", "PP8 (S-Log3)"),
            ("Focus Mode", "AF-C"),
        )
        post_common = (
            ("Aperture", "F1.8"),
            ("Shutter Speed", "1/250"),
            ("ISO", "Auto"),
            ("Exposure Comp.", "0.0EV"),
            ("Metering Mode", "Multi"),
            ("White Balance", "AWB"),
            ("Picture Profile", "Off"),
            ("Focus Mode", "AF-C"),
        )
        spec = DiffSetStillMvAndShutterAngleVaultSpec(
            pre_checked_items=P251_DIFF_SET_8_ITEMS,
            transition_kind="SEPARATE_TO_COMMON",
            post_transition_checked_items=(),
            pre_still_values=pre_still,
            pre_movie_values=pre_movie,
            post_still_values=post_common,
            post_movie_values=post_common,
            pre_still_custom_wb="Custom 3 (5000K_G+2)",
            post_still_custom_wb="Custom 3 (5000K_G+2)",
            movie_shutter_mode="Shutter Speed",
            shutter_speed_and_angle_independent=False,
            reset_action="NONE",
            post_reset_checked_items=(),
        )
        rep = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.separate_to_common_transition_verified)

    def test_13_separate_to_common_rejects_wiping_still_aperture_shutter_or_custom_wb(self) -> None:
        res_42a = run_pillar42a_diff_set_still_mv_vault_6_scenario_suite()
        self.assertTrue(res_42a.scenarios[4].passed)
        self.assertEqual(res_42a.scenarios[4].block_code, P251_BLOCKED_DIFF_SET_SEPARATE_TO_COMMON_DRIFT)

        # Wiping Still Custom White Balance during Separate -> Common
        pre_still = _replace_8item_pair(P251_DIFF_SET_FACTORY_PARAM_DEFAULTS, Aperture="F2.0")
        post_common = _replace_8item_pair(P251_DIFF_SET_FACTORY_PARAM_DEFAULTS, Aperture="F2.0")
        spec_wiped_cwb = DiffSetStillMvAndShutterAngleVaultSpec(
            pre_checked_items=("Aperture", "White Balance"),
            transition_kind="SEPARATE_TO_COMMON",
            post_transition_checked_items=(),
            pre_still_values=pre_still,
            pre_movie_values=P251_DIFF_SET_FACTORY_PARAM_DEFAULTS,
            post_still_values=post_common,
            post_movie_values=post_common,
            pre_still_custom_wb="Custom 1 (4400K)",
            post_still_custom_wb="FACTORY_WIPED",
            movie_shutter_mode="Angle",
            shutter_speed_and_angle_independent=True,
            post_reset_checked_items=(),
        )
        rep = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_wiped_cwb)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P251_BLOCKED_DIFF_SET_SEPARATE_TO_COMMON_DRIFT)

    def test_14_separate_to_common_rejects_retaining_separate_iso_pp_or_focus_mode(self) -> None:
        pre_still = _replace_8item_pair(
            P251_DIFF_SET_FACTORY_PARAM_DEFAULTS,
            ISO="3200",
            **{"Picture Profile": "PP11 (S-Cinetone)", "Focus Mode": "MF"},
        )
        # Falsely keeps ISO=3200 instead of resetting to Auto
        bad_post = _replace_8item_pair(P251_DIFF_SET_FACTORY_PARAM_DEFAULTS, ISO="3200")
        spec = DiffSetStillMvAndShutterAngleVaultSpec(
            pre_checked_items=("ISO", "Picture Profile", "Focus Mode"),
            transition_kind="SEPARATE_TO_COMMON",
            post_transition_checked_items=(),
            pre_still_values=pre_still,
            pre_movie_values=P251_DIFF_SET_FACTORY_PARAM_DEFAULTS,
            post_still_values=bad_post,
            post_movie_values=bad_post,
            movie_shutter_mode="Angle",
            shutter_speed_and_angle_independent=True,
            post_reset_checked_items=(),
        )
        rep = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P251_BLOCKED_DIFF_SET_SEPARATE_TO_COMMON_DRIFT)

    def test_15_shutter_mode_angle_override_keeps_movie_angle_independent_even_when_shutter_unchecked_common(
        self,
    ) -> None:
        still_fast = _replace_8item_pair(
            P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES,
            **{"Shutter Speed": "1/1000"},
        )
        movie_reg = _replace_8item_pair(
            P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES,
            **{"Shutter Speed": "1/48"},
        )
        spec = DiffSetStillMvAndShutterAngleVaultSpec(
            pre_checked_items=(),
            transition_kind="NONE",
            post_transition_checked_items=(),
            pre_still_values=still_fast,
            pre_movie_values=movie_reg,
            post_still_values=still_fast,
            post_movie_values=movie_reg,
            movie_shutter_mode="Angle",
            movie_shutter_angle_deg=172.8,
            post_movie_shutter_angle_deg=172.8,
            shutter_speed_and_angle_independent=True,
            reset_action="NONE",
            post_reset_checked_items=(),
        )
        rep = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.shutter_angle_independence_verified)
        self.assertEqual(rep.shutter_angle_common_bleed_events, 0)

    def test_16_shutter_mode_angle_rejects_bleed_or_coupling_when_shutter_unchecked(self) -> None:
        for kw in (
            {"shutter_speed_and_angle_independent": False},
            {"movie_shutter_angle_deg": 180.0, "post_movie_shutter_angle_deg": 90.0},
            {"shutter_angle_common_bleed_events": 2},
        ):
            with self.subTest(kw=kw):
                spec = DiffSetStillMvAndShutterAngleVaultSpec(
                    pre_checked_items=(),
                    transition_kind="NONE",
                    post_transition_checked_items=(),
                    movie_shutter_mode="Angle",
                    post_reset_checked_items=(),
                    **kw,
                )
                rep = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec)
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P251_BLOCKED_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION)
                self.assertGreaterEqual(rep.shutter_angle_common_bleed_events, 1)

    def test_17_shutter_mode_shutter_speed_common_requires_matching_still_and_movie_shutter(self) -> None:
        spec_common_ok = DiffSetStillMvAndShutterAngleVaultSpec(
            pre_checked_items=(),
            transition_kind="NONE",
            post_transition_checked_items=(),
            movie_shutter_mode="Shutter Speed",
            shutter_speed_and_angle_independent=False,
            post_reset_checked_items=(),
        )
        self.assertTrue(evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_common_ok).passed)

        mismatched_mv = _replace_8item_pair(
            P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES,
            **{"Shutter Speed": "1/60"},
        )
        spec_mismatch = replace(spec_common_ok, post_movie_values=mismatched_mv)
        rep_m = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_mismatch)
        self.assertFalse(rep_m.passed)
        self.assertEqual(rep_m.block_code, P251_BLOCKED_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION)

    def test_18_shutter_mode_angle_requires_fw_6_00_or_newer_rejects_5_00(self) -> None:
        self.assertEqual(
            P251_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS,
            ("6.00", "6.02", "7.00", "7.01", "7.02"),
        )
        rep_old = evaluate_diff_set_still_mv_and_shutter_angle_vault(
            DiffSetStillMvAndShutterAngleVaultSpec(fw_version="5.00", movie_shutter_mode="Angle")
        )
        self.assertFalse(rep_old.passed)
        self.assertEqual(rep_old.block_code, P251_BLOCKED_INVALID_DIFF_SET_SPEC)

    def test_19_diff_set_survives_both_camera_settings_reset_and_reset_network_set(self) -> None:
        for action in ("NONE", "Camera Settings Reset", "Reset Network Set."):
            with self.subTest(reset_action=action):
                spec = DiffSetStillMvAndShutterAngleVaultSpec(
                    reset_action=action,
                    post_transition_checked_items=P251_DIFF_SET_8_ITEMS,
                    post_reset_checked_items=P251_DIFF_SET_8_ITEMS,
                )
                self.assertTrue(evaluate_diff_set_still_mv_and_shutter_angle_vault(spec).passed)

                spec_wiped = replace(spec, post_reset_checked_items=())
                rep_w = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_wiped)
                self.assertFalse(rep_w.passed)
                self.assertEqual(rep_w.block_code, P251_BLOCKED_DIFF_SET_RESET_SURVIVAL_DRIFT)

    def test_20_diff_set_initialize_restores_factory_unchecked_and_camset01_restores_checked(self) -> None:
        self.assertEqual(P251_DIFF_SET_FACTORY_CHECKED_ITEMS, ())
        spec_init = DiffSetStillMvAndShutterAngleVaultSpec(
            reset_action="Initialize",
            post_transition_checked_items=P251_DIFF_SET_8_ITEMS,
            post_reset_checked_items=(),
        )
        self.assertTrue(evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_init).passed)

        spec_init_not_cleared = replace(spec_init, post_reset_checked_items=("Aperture",))
        rep_nc = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_init_not_cleared)
        self.assertFalse(rep_nc.passed)
        self.assertEqual(rep_nc.block_code, P251_BLOCKED_DIFF_SET_RESET_SURVIVAL_DRIFT)

        spec_camset = DiffSetStillMvAndShutterAngleVaultSpec(
            reset_action="Initialize",
            camset_load_after_reset=True,
            saved_checked_items=("Aperture", "ISO", "Picture Profile"),
            post_reset_checked_items=("Aperture", "ISO", "Picture Profile"),
        )
        self.assertTrue(evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_camset).passed)

    def test_21_pillar42a_rejects_overlay_escape_h0_h3_drift_and_unlock_request(self) -> None:
        rep_esc = evaluate_diff_set_still_mv_and_shutter_angle_vault(
            DiffSetStillMvAndShutterAngleVaultSpec(overlay_dir="/setting/diffset")
        )
        self.assertFalse(rep_esc.passed)
        self.assertEqual(rep_esc.block_code, P251_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h = evaluate_diff_set_still_mv_and_shutter_angle_vault(
            DiffSetStillMvAndShutterAngleVaultSpec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(rep_h.passed)
        self.assertEqual(rep_h.block_code, P251_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        rep_unlock = evaluate_diff_set_still_mv_and_shutter_angle_vault(
            DiffSetStillMvAndShutterAngleVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep_unlock.passed)
        self.assertEqual(rep_unlock.block_code, P251_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_22_pillar42a_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar42a_diff_set_still_mv_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P251_STATUS_VERIFIED_PILLAR_42A)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P251_PILLAR_42A_SCENARIO_IDS)
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])

    def test_23_default_safe_custom_key_remain_shoot_spec_passes(self) -> None:
        spec = build_default_safe_custom_key_remain_shoot_vault_spec()
        rep = evaluate_custom_key_dial_and_remain_shoot_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P251_STATUS_VERIFIED_PILLAR_42B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.three_domain_keymap_and_dials_verified)
        self.assertTrue(rep.iso_ei_and_follow_custom_verified)
        self.assertTrue(rep.non_resettable_survival_verified)
        self.assertTrue(rep.remain_shoot_still_buffer_scope_verified)
        self.assertTrue(rep.evfless_fx3_topology_verified)
        self.assertTrue(rep.slot1_vault_zero_mutation_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.slot1_custom_key_vault_mutation_bytes, 0)
        self.assertFalse(rep.fx3_has_builtin_evf)
        self.assertEqual(rep.evf_finder_monitor_spoof_events, 0)

    def test_24_factory_cinema_line_dials_aperture_iso_ei_shutter_speed_verified(self) -> None:
        self.assertEqual(P251_FRONT_DIAL_DEFAULT, "Aperture")
        self.assertEqual(P251_REAR_DIAL_DEFAULT, "ISO/EI")
        self.assertEqual(P251_CONTROL_WHEEL_DEFAULT, "Shutter Speed")
        self.assertEqual(len(P251_ASSIGNABLE_CUSTOM_CONTROLS), 8)
        self.assertEqual(len(P251_FACTORY_STILL_KEYMAP), 8)
        self.assertEqual(len(P251_FACTORY_MOVIE_KEYMAP), 8)
        self.assertGreaterEqual(len(P251_FACTORY_PLAYBACK_KEYMAP), 3)

    def test_25_rear_dial_iso_ei_adapts_between_iso_and_cine_ei_exposure_index(self) -> None:
        self.assertEqual(P251_SHOOTING_EXPOSURE_MODES, ("Flexible ISO", "Cine EI", "Cine EI Quick"))
        spec_flex = CustomKeyDialAndRemainShootVaultSpec(
            pre_reset_rear_dial="ISO/EI",
            shooting_exposure_mode="Flexible ISO",
            rear_dial_effective_target="ISO",
        )
        self.assertTrue(evaluate_custom_key_dial_and_remain_shoot_vault(spec_flex).passed)

        for cine_mode in ("Cine EI", "Cine EI Quick"):
            with self.subTest(mode=cine_mode):
                spec_ei = CustomKeyDialAndRemainShootVaultSpec(
                    pre_reset_rear_dial="ISO/EI",
                    shooting_exposure_mode=cine_mode,
                    rear_dial_effective_target="Exposure Index (EI)",
                )
                self.assertTrue(evaluate_custom_key_dial_and_remain_shoot_vault(spec_ei).passed)

                spec_wrong = replace(spec_ei, rear_dial_effective_target="ISO")
                rep_w = evaluate_custom_key_dial_and_remain_shoot_vault(spec_wrong)
                self.assertFalse(rep_w.passed)
                self.assertEqual(rep_w.block_code, P251_BLOCKED_DIAL_ISO_EI_OR_FOLLOW_CUSTOM_MISMATCH)

    def test_26_movie_follow_custom_inherits_still_keymap_and_rejects_broken_inheritance(self) -> None:
        self.assertEqual(P251_FOLLOW_CUSTOM_TOKEN, "Follow Custom")
        custom_still = (
            ("Custom Button 1", "HOME (BIG6)"),
            ("Custom Button 2", "Base ISO Switch"),
            ("Custom Button 3", "Focus Mode"),
            ("Custom Button 4", "Touch Operation"),
            ("Custom Button 5", "Zebra Display"),
            ("Custom Button 6", "Peaking Display"),
            ("Multi-Selector Center", "Focus Standard"),
            ("Lens Focus Hold Button", "Recall Custom hold 2"),
        )
        spec_ok = CustomKeyDialAndRemainShootVaultSpec(
            pre_reset_still_keymap=custom_still,
            post_reset_still_keymap=custom_still,
            resolved_movie_follow_custom_map=(
                ("Custom Button 1", "HOME (BIG6)"),
                ("Custom Button 2", "Base ISO Switch"),
                ("Lens Focus Hold Button", "Recall Custom hold 2"),
            ),
        )
        self.assertTrue(evaluate_custom_key_dial_and_remain_shoot_vault(spec_ok).passed)

        spec_stale_follow = replace(
            spec_ok,
            resolved_movie_follow_custom_map=(
                ("Custom Button 1", "White Balance"),
                ("Custom Button 2", "Focus Area"),
                ("Lens Focus Hold Button", "Focus Hold"),
            ),
        )
        rep_stale = evaluate_custom_key_dial_and_remain_shoot_vault(spec_stale_follow)
        self.assertFalse(rep_stale.passed)
        self.assertEqual(rep_stale.block_code, P251_BLOCKED_DIAL_ISO_EI_OR_FOLLOW_CUSTOM_MISMATCH)

    def test_27_still_and_playback_keymaps_reject_follow_custom_token(self) -> None:
        bad_still = list(P251_FACTORY_STILL_KEYMAP)
        bad_still[0] = ("Custom Button 1", "Follow Custom")
        rep_s = evaluate_custom_key_dial_and_remain_shoot_vault(
            CustomKeyDialAndRemainShootVaultSpec(
                pre_reset_still_keymap=tuple(bad_still),
                post_reset_still_keymap=tuple(bad_still),
            )
        )
        self.assertFalse(rep_s.passed)
        self.assertEqual(rep_s.block_code, P251_BLOCKED_INVALID_CUSTOM_KEY_OR_REMAIN_SHOOT_SPEC)

        bad_pb = (("Custom Button 1", "Follow Custom"),)
        rep_pb = evaluate_custom_key_dial_and_remain_shoot_vault(
            CustomKeyDialAndRemainShootVaultSpec(
                pre_reset_playback_keymap=bad_pb,
                post_reset_playback_keymap=bad_pb,
            )
        )
        self.assertFalse(rep_pb.passed)
        self.assertEqual(rep_pb.block_code, P251_BLOCKED_INVALID_CUSTOM_KEY_OR_REMAIN_SHOOT_SPEC)

    def test_28_my_dial_1_to_3_and_recall_custom_hold_1_to_3_supported(self) -> None:
        self.assertEqual(P251_MY_DIAL_SLOTS, ("NONE", "My Dial 1", "My Dial 2", "My Dial 3"))
        self.assertEqual(
            P251_RECALL_CUSTOM_HOLD_SLOTS,
            ("Recall Custom hold 1", "Recall Custom hold 2", "Recall Custom hold 3"),
        )
        for slot in P251_MY_DIAL_SLOTS:
            with self.subTest(my_dial=slot):
                self.assertTrue(
                    evaluate_custom_key_dial_and_remain_shoot_vault(
                        CustomKeyDialAndRemainShootVaultSpec(active_my_dial_slot=slot)
                    ).passed
                )
        rep_bad_dial = evaluate_custom_key_dial_and_remain_shoot_vault(
            CustomKeyDialAndRemainShootVaultSpec(active_my_dial_slot="My Dial 4")
        )
        self.assertFalse(rep_bad_dial.passed)
        self.assertEqual(rep_bad_dial.block_code, P251_BLOCKED_INVALID_CUSTOM_KEY_OR_REMAIN_SHOOT_SPEC)

    def test_29_custom_key_and_remain_shoot_survive_camera_settings_reset_and_reset_network_set(self) -> None:
        for action in ("NONE", "Camera Settings Reset", "Reset Network Set."):
            with self.subTest(reset_action=action):
                spec = CustomKeyDialAndRemainShootVaultSpec(
                    reset_action=action,
                    pre_reset_front_dial="Exposure Comp.",
                    post_reset_front_dial="Exposure Comp.",
                    pre_reset_remain_shoot_display="Shoot-Only Display",
                    post_reset_remain_shoot_display="Shoot-Only Display",
                )
                self.assertTrue(evaluate_custom_key_dial_and_remain_shoot_vault(spec).passed)

                spec_wiped = replace(
                    spec,
                    post_reset_front_dial="Aperture",
                    post_reset_remain_shoot_display="Not Displayed",
                )
                rep_w = evaluate_custom_key_dial_and_remain_shoot_vault(spec_wiped)
                self.assertFalse(rep_w.passed)
                self.assertEqual(rep_w.block_code, P251_BLOCKED_CUSTOM_KEY_OR_REMAIN_SHOOT_RESET_DRIFT)

    def test_30_initialize_resets_custom_key_dials_and_remain_shoot_to_factory_defaults(self) -> None:
        spec_init = CustomKeyDialAndRemainShootVaultSpec(
            reset_action="Initialize",
            pre_reset_front_dial="Exposure Comp.",
            pre_reset_remain_shoot_display="Always Display",
            post_reset_still_keymap=P251_FACTORY_STILL_KEYMAP,
            post_reset_movie_keymap=P251_FACTORY_MOVIE_KEYMAP,
            post_reset_playback_keymap=P251_FACTORY_PLAYBACK_KEYMAP,
            post_reset_front_dial="Aperture",
            post_reset_rear_dial="ISO/EI",
            post_reset_control_wheel="Shutter Speed",
            post_reset_remain_shoot_display="Not Displayed",
        )
        self.assertTrue(evaluate_custom_key_dial_and_remain_shoot_vault(spec_init).passed)

        spec_not_reset = replace(spec_init, post_reset_remain_shoot_display="Always Display")
        rep_bad = evaluate_custom_key_dial_and_remain_shoot_vault(spec_not_reset)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P251_BLOCKED_CUSTOM_KEY_OR_REMAIN_SHOOT_RESET_DRIFT)

    def test_31_camset01_ordonly_load_roundtrips_3domain_keymaps_and_remain_shoot_losslessly(self) -> None:
        spec = CustomKeyDialAndRemainShootVaultSpec(
            reset_action="Initialize",
            camset_load_after_reset=True,
            camset_slot=P251_SLOT1_VAULT_SLOT,
            camset_filename="CAMSET01.DAT",
            camset_source_model="ILME-FX3",
            camset_read_only_load=True,
            saved_front_dial="Exposure Comp.",
            saved_remain_shoot_display="Shoot-Only Display",
            post_reset_front_dial="Exposure Comp.",
            post_reset_remain_shoot_display="Shoot-Only Display",
        )
        rep = evaluate_custom_key_dial_and_remain_shoot_vault(spec)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.camset_slot1_roundtrip_verified)
        self.assertEqual(rep.slot1_custom_key_vault_mutation_bytes, 0)

        spec_drift = replace(spec, post_reset_remain_shoot_display="Not Displayed")
        rep_d = evaluate_custom_key_dial_and_remain_shoot_vault(spec_drift)
        self.assertFalse(rep_d.passed)
        self.assertEqual(rep_d.block_code, P251_BLOCKED_SLOT1_CUSTOM_KEY_VAULT_MUTATION_OR_CAMSET_DRIFT)

    def test_32_slot1_tier0_custom_key_vault_blocks_save_overwrite_unlocked_wp_or_fx6_import(self) -> None:
        for kw in (
            {"camset_save_to_slot1_attempted": True},
            {"slot1_sdxc_wp_locked": False},
            {"camset_load_after_reset": True, "camset_read_only_load": False},
            {"slot1_custom_key_vault_mutation_bytes": 512},
            {
                "camset_load_after_reset": True,
                "camset_source_model": "ILME-FX6",
                "saved_remain_shoot_display": "Always Display",
                "post_reset_remain_shoot_display": "Always Display",
            },
        ):
            with self.subTest(kw=kw):
                rep = evaluate_custom_key_dial_and_remain_shoot_vault(
                    CustomKeyDialAndRemainShootVaultSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code,
                    P251_BLOCKED_SLOT1_CUSTOM_KEY_VAULT_MUTATION_OR_CAMSET_DRIFT,
                )

    def test_33_remain_shoot_display_modes_and_still_buffer_only_boundary_enforced(self) -> None:
        for mode in P251_REMAIN_SHOOT_DISPLAY_MODES:
            with self.subTest(mode=mode):
                spec = CustomKeyDialAndRemainShootVaultSpec(
                    pre_reset_remain_shoot_display=mode,
                    post_reset_remain_shoot_display=mode,
                )
                self.assertTrue(evaluate_custom_key_dial_and_remain_shoot_vault(spec).passed)

        for bad_kw in (
            {"remain_shoot_applies_to_still_buffer_only": False},
            {"remain_shoot_displays_movie_card_time": True},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_custom_key_dial_and_remain_shoot_vault(
                    CustomKeyDialAndRemainShootVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P251_BLOCKED_REMAIN_SHOOT_SCOPE_OR_EVF_TOPOLOGY_SPOOF)

    def test_34_evfless_ilme_fx3_ilc_2210_topology_blocks_builtin_evf_and_finder_monitor_spoof(self) -> None:
        for spoof_kw in (
            {"fx3_has_builtin_evf": True},
            {"finder_monitor_switch_present": True},
            {"eye_sensor_present": True},
            {"evf_finder_monitor_spoof_events": 1},
        ):
            with self.subTest(spoof_kw=spoof_kw):
                rep = evaluate_custom_key_dial_and_remain_shoot_vault(
                    CustomKeyDialAndRemainShootVaultSpec(**spoof_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P251_BLOCKED_REMAIN_SHOOT_SCOPE_OR_EVF_TOPOLOGY_SPOOF)
                self.assertGreaterEqual(rep.evf_finder_monitor_spoof_events, 1)

    def test_35_pillar42b_rejects_overlay_escape_h0_h3_drift_and_unlock_request(self) -> None:
        rep_esc = evaluate_custom_key_dial_and_remain_shoot_vault(
            CustomKeyDialAndRemainShootVaultSpec(overlay_dir="/dev/cnflasha")
        )
        self.assertFalse(rep_esc.passed)
        self.assertEqual(rep_esc.block_code, P251_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h = evaluate_custom_key_dial_and_remain_shoot_vault(
            CustomKeyDialAndRemainShootVaultSpec(tier0_surfaces_h0_h3_matched=14)
        )
        self.assertFalse(rep_h.passed)
        self.assertEqual(rep_h.block_code, P251_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        rep_unlock = evaluate_custom_key_dial_and_remain_shoot_vault(
            CustomKeyDialAndRemainShootVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep_unlock.passed)
        self.assertEqual(rep_unlock.block_code, P251_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_36_pillar42b_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar42b_custom_key_remain_shoot_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P251_STATUS_VERIFIED_PILLAR_42B)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P251_PILLAR_42B_SCENARIO_IDS)
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])

    def test_37_combined_verify_diff_set_still_mv_custom_key_and_remain_shoot_vault_dual_mode(self) -> None:
        for force_cr in (None, True):
            with self.subTest(force_clean_room=force_cr):
                rep = verify_diff_set_still_mv_custom_key_and_remain_shoot_vault(force_clean_room=force_cr)
                self.assertTrue(rep.all_passed)
                self.assertTrue(rep.passed)
                self.assertEqual(rep.status, P251_STATUS_VERIFIED_PILLAR42_SUITE)
                self.assertEqual(rep.diff_set_transition_corruption_events, 0)
                self.assertEqual(rep.shutter_angle_common_bleed_events, 0)
                self.assertEqual(rep.slot1_custom_key_vault_mutation_bytes, 0)
                self.assertFalse(rep.fx3_has_builtin_evf)
                self.assertEqual(rep.evf_finder_monitor_spoof_events, 0)
                self.assertFalse(rep.hardware_live_attachment_authorized)
                self.assertTrue(rep.cnflasha_userspace_write_blocked)
                self.assertFalse(rep.persistent_emmc_writes_authorized)
                self.assertEqual(rep.passive_tx_bytes_emitted, 0)
                self.assertEqual(rep.physical_usb_packets_emitted, 0)
                self.assertEqual(rep.physical_device_writes, 0)
                self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
                d = rep.to_dict()
                self.assertEqual(d["schema"], PHASE251_SCHEMA)

    def test_38_combined_verify_symmetry_alias_and_failure_propagation(self) -> None:
        rep_alias = verify_diff_set_still_mv_custom_key_remain_shoot_vault(force_clean_room=True)
        self.assertTrue(rep_alias.all_passed)

        rep_fail_a = verify_diff_set_still_mv_custom_key_and_remain_shoot_vault(
            diff_set_spec=DiffSetStillMvAndShutterAngleVaultSpec(
                shutter_angle_common_bleed_events=1,
            ),
            force_clean_room=True,
        )
        self.assertFalse(rep_fail_a.all_passed)
        self.assertEqual(rep_fail_a.status, P251_STATUS_FAIL_PILLAR42_SUITE)

        rep_fail_b = verify_diff_set_still_mv_custom_key_and_remain_shoot_vault(
            custom_key_spec=CustomKeyDialAndRemainShootVaultSpec(
                camset_save_to_slot1_attempted=True,
            ),
            force_clean_room=True,
        )
        self.assertFalse(rep_fail_b.all_passed)
        self.assertEqual(rep_fail_b.status, P251_STATUS_FAIL_PILLAR42_SUITE)

    def test_39_standalone_pillar42_suite_dual_mode_deterministic_digest(self) -> None:
        rep_default = run_pillar42_standalone_suite()
        self.assertTrue(rep_default.all_passed)
        self.assertEqual(rep_default.status, P251_STATUS_VERIFIED_PILLAR42_SUITE)
        self.assertEqual(rep_default.pillar_42a_diff_set_still_mv_vault.scenarios_passed, 6)
        self.assertEqual(rep_default.pillar_42b_custom_key_remain_shoot_vault.scenarios_passed, 6)

        rep_cr1 = run_pillar42_standalone_suite(force_clean_room=True)
        rep_cr2 = run_pillar42_standalone_suite(force_clean_room=True)
        self.assertTrue(rep_cr1.all_passed)
        self.assertEqual(rep_cr1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_cr1.suite_sha256, rep_cr2.suite_sha256)
        self.assertEqual(len(rep_cr1.suite_sha256), 64)

    def test_40_master_42_pillar_specs_extend_master_41_cleanly(self) -> None:
        self.assertEqual(MASTER_42_PILLAR_COUNT, 42)
        self.assertEqual(len(MASTER_42_PILLAR_SPECS), 42)
        self.assertEqual(len(MASTER_42_PILLAR_IDS), 42)
        self.assertEqual(len(set(MASTER_42_PILLAR_IDS)), 42)
        self.assertEqual(MASTER_42_PILLAR_SPECS[:41], MASTER_41_PILLAR_SPECS)
        self.assertEqual(
            MASTER_42_PILLAR_SPECS[41],
            (
                42,
                "pillar_42_diff_set_still_mv_custom_key_remain_shoot_vault",
                "Phase 251",
                "fx3_recovery.realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier",
            ),
        )

    def test_41_master_42pillar_default_mode_42_of_42_verified_under_budget(self) -> None:
        rep = self.master42_default
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P251_STATUS_VERIFIED_42OF42_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 42)
        self.assertEqual(rep.pillars_passed, 42)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertLess(rep.elapsed_seconds, 4.0)

    def test_42_master_42pillar_clean_room_mode_42_of_42_verified(self) -> None:
        rep = self.master42_clean_room
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.status, P251_STATUS_VERIFIED_42OF42_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 42)
        self.assertEqual(rep.pillars_passed, 42)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)

    def test_43_master_42pillar_zero_write_and_wave40_domain_invariants_preserved(self) -> None:
        rep = self.master42_default
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

    def test_44_master_42pillar_individual_pillar_numbering_and_status(self) -> None:
        rep = self.master42_clean_room
        self.assertEqual([p.pillar_number for p in rep.pillars], list(range(1, 43)))
        self.assertTrue(all(p.passed for p in rep.pillars))
        p42 = rep.pillars[41]
        self.assertEqual(p42.pillar_number, 42)
        self.assertEqual(p42.pillar_id, "pillar_42_diff_set_still_mv_custom_key_remain_shoot_vault")
        self.assertEqual(p42.phase_label, "Phase 251")
        self.assertEqual(p42.key_metrics["pillar_42a_diff_set_still_mv_vault"], "6/6")
        self.assertEqual(p42.key_metrics["pillar_42b_custom_key_remain_shoot_vault"], "6/6")
        self.assertEqual(p42.key_metrics["diff_set_transition_corruption_events"], 0)
        self.assertEqual(p42.key_metrics["shutter_angle_common_bleed_events"], 0)
        self.assertEqual(p42.key_metrics["slot1_custom_key_vault_mutation_bytes"], 0)
        self.assertFalse(p42.key_metrics["fx3_has_builtin_evf"])
        self.assertEqual(p42.key_metrics["evf_finder_monitor_spoof_events"], 0)
        self.assertEqual(p42.key_metrics["donor_files_inspected"], 11)

    def test_45_master_42pillar_json_serializable_without_nan(self) -> None:
        rep = self.master42_clean_room
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(encoded)
        self.assertEqual(parsed["schema"], PHASE251_SCHEMA)
        self.assertEqual(parsed["pillar_count"], 42)
        self.assertEqual(parsed["pillars_passed"], 42)
        self.assertEqual(len(parsed["master_42pillar_sha256"]), 64)

    def test_46_master_42pillar_fault_injection_on_pillar_42_marks_41_of_42(self) -> None:
        with mock.patch.object(
            p251, "evaluate_realhw_41pillar_recovery_master", return_value=self.master41_clean_room
        ):
            rep = evaluate_realhw_42pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_42_diff_set_still_mv_custom_key_remain_shoot_vault",
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P251_STATUS_FAIL_42OF42_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 42)
        self.assertEqual(rep.pillars_passed, 41)
        self.assertEqual(
            rep.failed_pillars,
            ("pillar_42_diff_set_still_mv_custom_key_remain_shoot_vault",),
        )

    def test_47_master_42pillar_fault_injection_on_upstream_pillar_1_marks_41_of_42(self) -> None:
        first_id = MASTER_42_PILLAR_IDS[0]
        with mock.patch.object(
            p251, "evaluate_realhw_41pillar_recovery_master", return_value=self.master41_clean_room
        ):
            rep = evaluate_realhw_42pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar=first_id,
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 41)
        self.assertEqual(rep.failed_pillars, (first_id,))

    def test_48_master_42pillar_rejects_unknown_fault_inject_pillar(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_42pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_999",
            )

    def test_49_master_42pillar_aliases_forward_cleanly(self) -> None:
        cached = self.master42_clean_room
        with mock.patch.object(
            p251, "evaluate_realhw_42pillar_recovery_master", return_value=cached
        ) as mocked_eval:
            r1 = evaluate_42pillar_recovery_master(force_clean_room=True)
            r2 = verify_42pillar_recovery_suite(force_clean_room=True)
        self.assertIs(r1, cached)
        self.assertIs(r2, cached)
        self.assertEqual(mocked_eval.call_count, 2)

    def test_50_safety_invariant_tamper_detection_blocks_master(self) -> None:
        with mock.patch.object(p251, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            with self.assertRaises(ValueError):
                evaluate_realhw_42pillar_recovery_master(force_clean_room=True)

    def test_51_safety_invariant_tamper_detection_blocks_standalone_suite(self) -> None:
        with mock.patch.object(p251, "PASSIVE_TX_BYTES_EMITTED", 1):
            rep = run_pillar42_standalone_suite(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P251_STATUS_FAIL_PILLAR42_SUITE)
        self.assertTrue(any("PASSIVE_TX_BYTES_EMITTED" in e for e in rep.errors))

    def test_52_master_42pillar_detects_upstream_m41_safety_violation(self) -> None:
        m41_bad = replace(self.master41_clean_room, bt_rmt_ir_lockout_violations=1)
        with mock.patch.object(p251, "evaluate_realhw_41pillar_recovery_master", return_value=m41_bad):
            rep = evaluate_realhw_42pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertTrue(any("bt_rmt_ir_lockout_violations" in e for e in rep.errors))

    def test_53_master_42pillar_detects_p42_domain_counter_and_evf_spoof_violations(self) -> None:
        base_p42 = run_pillar42_standalone_suite(force_clean_room=True)
        for field_name, bad_val in (
            ("diff_set_transition_corruption_events", 1),
            ("shutter_angle_common_bleed_events", 1),
            ("slot1_custom_key_vault_mutation_bytes", 128),
            ("fx3_has_builtin_evf", True),
            ("evf_finder_monitor_spoof_events", 1),
        ):
            with self.subTest(field=field_name):
                p42_bad = replace(base_p42, **{field_name: bad_val})
                with (
                    mock.patch.object(
                        p251,
                        "evaluate_realhw_41pillar_recovery_master",
                        return_value=self.master41_clean_room,
                    ),
                    mock.patch.object(p251, "run_pillar42_standalone_suite", return_value=p42_bad),
                ):
                    rep = evaluate_realhw_42pillar_recovery_master(force_clean_room=True)
                self.assertFalse(rep.all_passed)
                self.assertTrue(any(field_name in e for e in rep.errors))

    def test_54_all_shutter_angle_fx3_firmware_versions_6_00_to_7_02_accepted(self) -> None:
        self.assertIn("7.02", P251_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS)
        for ver in P251_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS:
            with self.subTest(fw_version=ver):
                self.assertTrue(
                    evaluate_diff_set_still_mv_and_shutter_angle_vault(
                        DiffSetStillMvAndShutterAngleVaultSpec(fw_version=ver, movie_shutter_mode="Angle")
                    ).passed
                )

    def test_55_all_supported_fx3_firmware_versions_accepted_for_shutter_speed_mode_and_pillar42b(
        self,
    ) -> None:
        for ver in P251_FX3_SUPPORTED_FW_VERSIONS:
            with self.subTest(fw_version=ver):
                self.assertTrue(
                    evaluate_diff_set_still_mv_and_shutter_angle_vault(
                        DiffSetStillMvAndShutterAngleVaultSpec(
                            fw_version=ver,
                            movie_shutter_mode="Shutter Speed",
                            shutter_speed_and_angle_independent=True,
                        )
                    ).passed
                )
                self.assertTrue(
                    evaluate_custom_key_dial_and_remain_shoot_vault(
                        CustomKeyDialAndRemainShootVaultSpec(fw_version=ver)
                    ).passed
                )

    def test_56_all_10_camset_slots_accepted_for_ordonly_loads_in_pillar42a_and_42b(self) -> None:
        self.assertEqual(len(P251_CAMSET_FILENAMES), 10)
        for slot in range(1, 11):
            fname = f"CAMSET{slot:02d}.DAT"
            with self.subTest(slot=slot):
                rep_a = evaluate_diff_set_still_mv_and_shutter_angle_vault(
                    DiffSetStillMvAndShutterAngleVaultSpec(
                        camset_load_after_reset=True,
                        camset_slot=slot,
                        camset_filename=fname,
                        camset_read_only_load=True,
                    )
                )
                self.assertTrue(rep_a.passed)
                rep_b = evaluate_custom_key_dial_and_remain_shoot_vault(
                    CustomKeyDialAndRemainShootVaultSpec(
                        camset_load_after_reset=True,
                        camset_slot=slot,
                        camset_filename=fname,
                        camset_read_only_load=True,
                        saved_remain_shoot_display="Always Display",
                        post_reset_remain_shoot_display="Always Display",
                    )
                )
                self.assertTrue(rep_b.passed)

    def test_57_steady_state_none_transition_enforces_common_item_equality(self) -> None:
        diverged_mv = _replace_8item_pair(P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES, ISO="12800")
        spec_bad = DiffSetStillMvAndShutterAngleVaultSpec(
            pre_checked_items=(),
            transition_kind="NONE",
            post_transition_checked_items=(),
            post_movie_values=diverged_mv,
            movie_shutter_mode="Angle",
            shutter_speed_and_angle_independent=True,
            post_reset_checked_items=(),
        )
        rep = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec_bad)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P251_BLOCKED_DIFF_SET_COMMON_TO_SEPARATE_DRIFT)

    def test_58_custom_non_iso_ei_rear_dial_assignment_supported(self) -> None:
        spec_ok = CustomKeyDialAndRemainShootVaultSpec(
            pre_reset_rear_dial="Exposure Comp.",
            post_reset_rear_dial="Exposure Comp.",
            rear_dial_effective_target="CUSTOM_NON_ISO_EI",
        )
        self.assertTrue(evaluate_custom_key_dial_and_remain_shoot_vault(spec_ok).passed)

        spec_bad = replace(spec_ok, rear_dial_effective_target="ISO")
        rep_bad = evaluate_custom_key_dial_and_remain_shoot_vault(spec_bad)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P251_BLOCKED_DIAL_ISO_EI_OR_FOLLOW_CUSTOM_MISMATCH)

    def test_59_tier0_backup_bin_pinned_sha256_consistent_with_16_surface_h0_h3(self) -> None:
        self.assertEqual(
            P251_PINNED_FX3_BACKUP_BIN_SHA256,
            "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        )
        self.assertEqual(
            P251_DEFAULT_STILL_CUSTOM_WB_REGISTER,
            "Custom 1 (4300K_G+1)",
        )
        self.assertEqual(P251_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG, 180.0)
        self.assertEqual(P251_DIFF_SET_TRANSITION_KINDS, ("NONE", "COMMON_TO_SEPARATE", "SEPARATE_TO_COMMON"))
        self.assertEqual(P251_RESET_ACTIONS, ("NONE", "Camera Settings Reset", "Reset Network Set.", "Initialize"))

    def test_60_donor_bounded_reader_handles_missing_and_non_regular_gracefully(self) -> None:
        with mock.patch.object(p251, "resolve_donor_path", return_value=None):
            ok, total_b, read_b, kind, digest, raw = p251._read_donor_readonly_bounded("nonexistent.bin")
        self.assertFalse(ok)
        self.assertEqual((total_b, read_b, kind, digest, raw), (0, 0, "MISSING", "", b""))

    def test_61_pairs_to_ordered_dict_accepts_mapping_and_rejects_duplicate_or_empty_keys(self) -> None:
        self.assertEqual(p251._pairs_to_ordered_dict({"A": "1", "B": "2"}), {"A": "1", "B": "2"})
        self.assertIsNone(p251._pairs_to_ordered_dict((("A", "1"), ("A", "2"))))
        self.assertIsNone(p251._pairs_to_ordered_dict((("", "1"),)))
        self.assertIsNone(p251._pairs_to_ordered_dict({"A": "   "}))

    def test_62_backward_compatibility_callable_exports_22_to_41(self) -> None:
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
        ):
            with self.subTest(pillars=count):
                self.assertTrue(callable(getattr(fx3_recovery, attr_name)))
        self.assertEqual([p.pillar_number for p in self.master42_clean_room.pillars], list(range(1, 43)))

    def test_63_cli_verify_diff_set_still_mv_custom_key_remain_shoot_vault_summary_and_json(self) -> None:
        rc_txt, out_txt = _run_inprocess_cli("verify-diff-set-still-mv-custom-key-remain-shoot-vault")
        self.assertEqual(rc_txt, 0)
        self.assertIn(
            "status=VERIFIED_PILLAR42_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_VAULT",
            out_txt,
        )
        self.assertIn("pillar_42a=6/6", out_txt)
        self.assertIn("pillar_42b=6/6", out_txt)
        self.assertIn("diff_set_transition_corruption_events=0", out_txt)
        self.assertIn("shutter_angle_common_bleed_events=0", out_txt)
        self.assertIn("slot1_custom_key_vault_mutation_bytes=0", out_txt)
        self.assertIn("fx3_has_builtin_evf=False", out_txt)
        self.assertIn("evf_finder_monitor_spoof_events=0", out_txt)
        self.assertIn("hardware_live_attachment_authorized=False", out_txt)

        rc_js, out_js = _run_inprocess_cli(
            "verify-diff-set-still-mv-custom-key-remain-shoot-vault", "--json"
        )
        self.assertEqual(rc_js, 0)
        payload = json.loads(out_js)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["schema"], PHASE251_SCHEMA)

    def test_64_cli_verify_diff_set_still_mv_custom_key_remain_shoot_vault_force_clean_room(self) -> None:
        rc, out = _run_inprocess_cli(
            "verify-diff-set-still-mv-custom-key-remain-shoot-vault",
            "--force-clean-room",
            "--json",
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["diff_set_transition_corruption_events"], 0)
        self.assertEqual(payload["shutter_angle_common_bleed_events"], 0)
        self.assertEqual(payload["slot1_custom_key_vault_mutation_bytes"], 0)
        self.assertFalse(payload["fx3_has_builtin_evf"])
        self.assertEqual(payload["evf_finder_monitor_spoof_events"], 0)
        self.assertFalse(payload["hardware_live_attachment_authorized"])

    def test_65_cli_verify_diff_set_still_mv_custom_key_remain_shoot_vault_subprocess_smoke(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-diff-set-still-mv-custom-key-remain-shoot-vault",
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

    def test_66_cli_verify_42pillar_recovery_summary_json_and_clean_room_forwarding(self) -> None:
        with mock.patch.object(
            cli_main, "verify_42pillar_recovery_suite", return_value=self.master42_default
        ):
            rc_txt, out_txt = _run_inprocess_cli("verify-42pillar-recovery")
            self.assertEqual(rc_txt, 0)
            self.assertIn("status=VERIFIED_42OF42_PILLAR_RECOVERY_MASTER", out_txt)
            self.assertIn("pillars=42/42", out_txt)
            self.assertIn("pillar42_a=6/6", out_txt)
            self.assertIn("pillar42_b=6/6", out_txt)

            rc_js, out_js = _run_inprocess_cli("verify-42pillar-recovery", "--json")
            self.assertEqual(rc_js, 0)
            payload = json.loads(out_js)
            self.assertEqual(payload["pillar_count"], 42)
            self.assertEqual(payload["pillars_passed"], 42)

        with mock.patch.object(
            cli_main, "verify_42pillar_recovery_suite", return_value=self.master42_clean_room
        ) as mocked_suite:
            rc_cr, out_cr = _run_inprocess_cli("verify-42pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc_cr, 0)
        mocked_suite.assert_called_once_with(force_clean_room=True)
        self.assertEqual(json.loads(out_cr)["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_67_cli_out_creates_exclusive_directories_for_pillar42_and_42pillar_master(self) -> None:
        here = Path(__file__).resolve().parent
        out_p42 = here / f"_tmp_p251_p42_{os.getpid()}"
        rep_p42 = out_p42 / "pillar42-diff-set-still-mv-custom-key-remain-shoot-vault-report.json"
        out_m42 = here / f"_tmp_p251_m42_{os.getpid()}"
        rep_m42 = out_m42 / "42pillar-recovery-master-report.json"
        for f, d in ((rep_p42, out_p42), (rep_m42, out_m42)):
            if f.is_file():
                f.unlink()
            if d.is_dir():
                d.rmdir()
        try:
            rc1, _ = _run_inprocess_cli(
                "verify-diff-set-still-mv-custom-key-remain-shoot-vault",
                "--force-clean-room",
                "--out",
                str(out_p42),
            )
            self.assertEqual(rc1, 0)
            self.assertTrue(rep_p42.is_file())
            self.assertEqual(
                json.loads(rep_p42.read_text(encoding="utf-8"))["schema"],
                PHASE251_SCHEMA,
            )

            with mock.patch.object(
                cli_main, "verify_42pillar_recovery_suite", return_value=self.master42_clean_room
            ):
                rc2, _ = _run_inprocess_cli(
                    "verify-42pillar-recovery",
                    "--force-clean-room",
                    "--out",
                    str(out_m42),
                )
            self.assertEqual(rc2, 0)
            self.assertTrue(rep_m42.is_file())
            self.assertEqual(
                json.loads(rep_m42.read_text(encoding="utf-8"))["pillar_count"],
                42,
            )
        finally:
            for f, d in ((rep_p42, out_p42), (rep_m42, out_m42)):
                if f.is_file():
                    f.unlink()
                if d.is_dir():
                    d.rmdir()

    def test_68_cli_out_refuses_preexisting_directory_overwrite_guard(self) -> None:
        here = Path(__file__).resolve().parent
        existing_dir = here / f"_tmp_p251_exist_{os.getpid()}"
        existing_dir.mkdir(exist_ok=True)
        try:
            rc, out = _run_inprocess_cli(
                "verify-diff-set-still-mv-custom-key-remain-shoot-vault",
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
