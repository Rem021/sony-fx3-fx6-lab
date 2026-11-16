"""Phase 220 dual-mode tests: Pillar 32 (`[NTSC/PAL Selector]` Reset Asymmetry, Dual-Slot Media DB
Separation & `[Gamma Display Assist]` vs `[Display LUT]` Parity + Manual `[Pixel Mapping]` Auto-Restart
`H1 -> H2` & `cnflasha` Read-Only Sensor Defect-Table Vault) and Unified `32/32` Recovery Master.
"""

from __future__ import annotations

from dataclasses import replace
import io
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent

import fx3_recovery
from fx3_recovery import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_31_PILLAR_COUNT,
    MASTER_32_PILLAR_COUNT,
    MASTER_32_PILLAR_IDS,
    MASTER_32_PILLAR_SPECS,
    P220_BLOCKED_AUTO_PIXELMAP_POWEROFF_SHUTTER_HAZARD,
    P220_BLOCKED_CNFLASHA_DEFECT_TABLE_WRITE_ATTEMPT,
    P220_BLOCKED_GAMMA_ASSIST_DISPLAY_LUT_PARITY_DRIFT,
    P220_BLOCKED_GAMMA_ASSIST_HDMI_SCOPE_VIOLATION,
    P220_BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION,
    P220_BLOCKED_NTSCPAL_FRAMERATE_OR_DFNDF_MISMATCH,
    P220_BLOCKED_NTSCPAL_RESET_ASYMMETRY_VIOLATION,
    P220_BLOCKED_NTSCPAL_STARTUP_BANNER_DRIFT,
    P220_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P220_BLOCKED_PIXELMAP_OR_TIER0_LOW_BATTERY,
    P220_BLOCKED_PIXELMAP_RESTART_H0_H2_OVERLAY_RESIDUE,
    P220_BLOCKED_SAFETY_POLICY_VIOLATION,
    P220_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P220_CONCURRENT_CEILING_SECONDS,
    P220_DONOR_INSPECT_BUDGET_SECONDS,
    P220_FX3_FW_VERSION,
    P220_FX3_MODEL_NAME,
    P220_GAMMA_DISP_ASSIST_TYPES,
    P220_GAMMA_DISP_ASSIST_UNICODE_ALIAS,
    P220_NTSC_FRAME_RATES,
    P220_PAL_FRAME_RATES,
    P220_PAL_TC_FORMAT_LOCKED,
    P220_PILLAR_32A_SCENARIO_IDS,
    P220_PILLAR_32B_SCENARIO_IDS,
    P220_PROTECTED_CNFLASHA_SURFACES,
    P220_STATUS_FAIL_32OF32_AGGREGATOR,
    P220_STATUS_FAIL_PILLAR32_SUITE,
    P220_STATUS_VERIFIED_32OF32_AGGREGATOR,
    P220_STATUS_VERIFIED_PILLAR32_SUITE,
    P220_STATUS_VERIFIED_PILLAR_32A,
    P220_STATUS_VERIFIED_PILLAR_32B,
    NtscPalAndGammaDisplayLutVaultSpec,
    PixelMapAutoRestartAndCnflashaVaultSpec,
    SlotNtscPalDatabaseSpec,
    build_default_safe_ntscpal_gamma_vault_spec,
    build_default_safe_pixelmap_cnflasha_vault_spec,
    evaluate_22pillar_recovery_master,
    evaluate_24pillar_recovery_master,
    evaluate_26pillar_recovery_master,
    evaluate_27pillar_recovery_master,
    evaluate_28pillar_recovery_master,
    evaluate_29pillar_recovery_master,
    evaluate_30pillar_recovery_master,
    evaluate_31pillar_recovery_master,
    evaluate_32pillar_recovery_master,
    evaluate_ntscpal_persistence_and_gamma_displaylut_vault,
    evaluate_pixelmap_autorestart_and_cnflasha_vault,
    evaluate_realhw_32pillar_recovery_master,
    inspect_phase220_donors_readonly,
    realhw_32pillar_ntscpal_pixelmap_vault_verifier as p220,
    run_pillar32_standalone_suite,
    run_pillar32a_ntscpal_gamma_vault_6_scenario_suite,
    run_pillar32b_pixelmap_cnflasha_vault_6_scenario_suite,
    verify_32pillar_recovery_suite,
    verify_ntscpal_persistence_and_pixelmap_cnflasha_vault,
)
from fx3_recovery.__main__ import main as cli_main


def _assert_zero_raw_firmware_leaks(testcase: unittest.TestCase, payload_dict: dict) -> None:
    dumped = json.dumps(payload_dict, sort_keys=True)
    testcase.assertNotIn("\\x7fELF", dumped)
    testcase.assertNotIn("89554655", dumped)
    testcase.assertNotIn("424b3400", dumped)
    testcase.assertEqual(payload_dict.get("raw_firmware_bytes_leaked", 0), 0)
    testcase.assertEqual(payload_dict.get("physical_device_writes", 0), 0)
    testcase.assertFalse(payload_dict.get("persistent_emmc_writes_authorized", False))
    testcase.assertTrue(payload_dict.get("cnflasha_userspace_write_blocked", True))


class TestPhase220Pillar32NtscPalPixelMapVaultAnd32Of32Master(unittest.TestCase):
    # -----------------------------------------------------------------------
    # Group 0: Safety invariants, exports, donor check & clean-room fallback
    # -----------------------------------------------------------------------

    def test_01_hardlocked_safety_policy_constants(self) -> None:
        self.assertFalse(p220.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p220.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p220.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p220.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p220.PERSISTENT_WRITE_RELEASE)
        self.assertFalse(p220.ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(p220.ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(p220.ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(p220.ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(p220.LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertTrue(p220.READ_ONLY_DONOR_ACCESS)
        self.assertTrue(p220.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p220.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p220.OTP_FUSE_WRITES, 0)
        self.assertEqual(p220.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p220.PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(p220.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p220.PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(p220.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_package_exports_and_zero_symbol_shadowing(self) -> None:
        for sym in (
            "CNFLASHA_USERSPACE_WRITE_BLOCKED",
            "MASTER_32_PILLAR_COUNT",
            "MASTER_32_PILLAR_IDS",
            "MASTER_32_PILLAR_SPECS",
            "verify_ntscpal_persistence_and_pixelmap_cnflasha_vault",
            "evaluate_realhw_32pillar_recovery_master",
            "evaluate_32pillar_recovery_master",
            "verify_32pillar_recovery_suite",
            "run_pillar32_standalone_suite",
            "P220_BLOCKED_NTSCPAL_RESET_ASYMMETRY_VIOLATION",
            "P220_BLOCKED_CNFLASHA_DEFECT_TABLE_WRITE_ATTEMPT",
        ):
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym))
        self.assertFalse(fx3_recovery.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertTrue(fx3_recovery.READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(MASTER_31_PILLAR_COUNT, 31)
        self.assertEqual(MASTER_32_PILLAR_COUNT, 32)

    def test_03_master_32_pillar_registry_completeness(self) -> None:
        self.assertEqual(len(MASTER_32_PILLAR_SPECS), 32)
        self.assertEqual(len(MASTER_32_PILLAR_IDS), 32)
        self.assertEqual(len(set(MASTER_32_PILLAR_IDS)), 32)
        self.assertEqual([spec[0] for spec in MASTER_32_PILLAR_SPECS], list(range(1, 33)))
        self.assertEqual(MASTER_32_PILLAR_SPECS[31][1], "pillar_32_ntscpal_pixelmap_cnflasha_vault")
        self.assertEqual(MASTER_32_PILLAR_SPECS[31][2], "Phase 220")

    def test_04_bounded_readonly_donor_inspection_under_0_15s(self) -> None:
        snap = inspect_phase220_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 6)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertLess(snap.elapsed_seconds, P220_DONOR_INSPECT_BUDGET_SECONDS)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        for art in snap.artifacts:
            self.assertTrue(art.matches_pinned)
            if art.digest_kind == "HEADER4K_SHA256":
                self.assertEqual(art.header_bytes_read, 4096)

    def test_05_donor_open_uses_strict_o_rdonly_nofollow_nonblock(self) -> None:
        seen_flags: list[int] = []
        real_open = os.open

        def _spy_open(path_arg: str, flags: int, *args: object) -> int:
            seen_flags.append(flags)
            return real_open(path_arg, flags, *args)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}, clear=False):
            with patch(
                "fx3_recovery.realhw_32pillar_ntscpal_pixelmap_vault_verifier.os.open",
                side_effect=_spy_open,
            ):
                snap = inspect_phase220_donors_readonly(force_clean_room=False)
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(len(seen_flags), 6)
            for fl in seen_flags:
                self.assertEqual(fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
                if hasattr(os, "O_NOFOLLOW"):
                    self.assertNotEqual(fl & os.O_NOFOLLOW, 0)
                if hasattr(os, "O_NONBLOCK"):
                    self.assertNotEqual(fl & os.O_NONBLOCK, 0)

    def test_06_env_force_clean_room_synthetic_fallback(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            snap = inspect_phase220_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 6)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))

    def test_07_missing_local_donor_falls_back_cleanly_to_synthetic(self) -> None:
        with patch(
            "fx3_recovery.realhw_32pillar_ntscpal_pixelmap_vault_verifier.resolve_donor_path",
            return_value=Path("/nonexistent/fx3/donor.bin"),
        ):
            snap = inspect_phase220_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    # -----------------------------------------------------------------------
    # Group A: Pillar 32A — NTSC/PAL Persistence, Dual-Slot DB & Gamma/Display LUT
    # -----------------------------------------------------------------------

    def test_08_pillar32a_default_safe_ntsc_spec_passes(self) -> None:
        rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(
            build_default_safe_ntscpal_gamma_vault_spec()
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P220_STATUS_VERIFIED_PILLAR_32A)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.effective_ntsc_pal_region, "NTSC")
        self.assertTrue(rep.reset_asymmetry_verified)
        self.assertTrue(rep.startup_banner_verified)
        self.assertTrue(rep.framerate_dfndf_table_verified)
        self.assertEqual(rep.slots_audited, (1, 2))
        self.assertTrue(rep.dual_slot_db_separation_verified)
        self.assertTrue(rep.gamma_displaylut_parity_verified)
        self.assertTrue(rep.gamma_hdmi_lcd_only_scope_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_09_pillar32a_camera_settings_reset_preserves_switched_ntscpal_and_banner(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        pal_spec = replace(
            base,
            factory_default_region="NTSC",
            pre_reset_ntsc_pal_selector="PAL",
            reset_operation="Camera Settings Reset",
            post_reset_ntsc_pal_selector="PAL",
            startup_banner_observed="Running on PAL.",
            configured_frame_rate="25p",
            tc_format_available=False,
            configured_tc_format=P220_PAL_TC_FORMAT_LOCKED,
            restored_backup_ntsc_pal="PAL",
            slot_databases=(
                SlotNtscPalDatabaseSpec(slot=1, card_db_region="PAL", cold_backup_verified=True),
                SlotNtscPalDatabaseSpec(slot=2, card_db_region="PAL", cold_backup_verified=True),
            ),
        )
        rep_pal = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(pal_spec)
        self.assertTrue(rep_pal.passed)
        self.assertEqual(rep_pal.effective_ntsc_pal_region, "PAL")

        ntsc_on_pal_body = replace(
            base,
            factory_default_region="PAL",
            pre_reset_ntsc_pal_selector="NTSC",
            reset_operation="Camera Settings Reset",
            post_reset_ntsc_pal_selector="NTSC",
            startup_banner_observed="Running on NTSC.",
            configured_frame_rate="29.97p",
            tc_format_available=True,
            configured_tc_format="DF",
            restored_backup_ntsc_pal="NTSC",
        )
        rep_ntsc = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(ntsc_on_pal_body)
        self.assertTrue(rep_ntsc.passed)
        self.assertEqual(rep_ntsc.effective_ntsc_pal_region, "NTSC")

    def test_10_pillar32a_full_initialize_restores_factory_region_and_clears_banner(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        init_ntsc = replace(
            base,
            factory_default_region="NTSC",
            pre_reset_ntsc_pal_selector="PAL",
            reset_operation="Initialize",
            post_reset_ntsc_pal_selector="NTSC",
            startup_banner_observed="",
            configured_frame_rate="23.98p",
            tc_format_available=True,
            configured_tc_format="NDF",
            restored_backup_ntsc_pal="NTSC",
        )
        self.assertTrue(evaluate_ntscpal_persistence_and_gamma_displaylut_vault(init_ntsc).passed)

        init_pal = replace(
            base,
            factory_default_region="PAL",
            pre_reset_ntsc_pal_selector="NTSC",
            reset_operation="Initialize",
            post_reset_ntsc_pal_selector="PAL",
            startup_banner_observed="",
            configured_frame_rate="50p",
            tc_format_available=False,
            configured_tc_format=P220_PAL_TC_FORMAT_LOCKED,
            restored_backup_ntsc_pal="PAL",
            slot_databases=(
                SlotNtscPalDatabaseSpec(slot=1, card_db_region="PAL", cold_backup_verified=True),
                SlotNtscPalDatabaseSpec(slot=2, card_db_region="PAL", cold_backup_verified=True),
            ),
        )
        self.assertTrue(evaluate_ntscpal_persistence_and_gamma_displaylut_vault(init_pal).passed)

    def test_11_pillar32a_rejects_reset_asymmetry_violation(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        cases = (
            replace(base, camera_settings_reset_clears_ntscpal_assumed=True),
            replace(
                base,
                pre_reset_ntsc_pal_selector="PAL",
                reset_operation="Camera Settings Reset",
                post_reset_ntsc_pal_selector="NTSC",
            ),
            replace(
                base,
                factory_default_region="NTSC",
                pre_reset_ntsc_pal_selector="PAL",
                reset_operation="Initialize",
                post_reset_ntsc_pal_selector="PAL",
                startup_banner_observed="Running on PAL.",
            ),
            replace(base, reset_operation="InvalidReset"),
        )
        for bad in cases:
            rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_NTSCPAL_RESET_ASYMMETRY_VIOLATION)

    def test_12_pillar32a_rejects_startup_banner_drift(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        bad_banner_default = replace(base, startup_banner_observed="Running on NTSC.")
        rep1 = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(bad_banner_default)
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P220_BLOCKED_NTSCPAL_STARTUP_BANNER_DRIFT)

        missing_switched_banner = replace(
            base,
            factory_default_region="PAL",
            pre_reset_ntsc_pal_selector="NTSC",
            post_reset_ntsc_pal_selector="NTSC",
            startup_banner_observed="",
        )
        rep2 = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(missing_switched_banner)
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P220_BLOCKED_NTSCPAL_STARTUP_BANNER_DRIFT)

    def test_13_pillar32a_ntsc_framerate_and_df_ndf_table_enforced(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        for fr in P220_NTSC_FRAME_RATES:
            for tc_fmt in ("DF", "NDF"):
                ok_rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(
                    replace(base, configured_frame_rate=fr, tc_format_available=True, configured_tc_format=tc_fmt)
                )
                self.assertTrue(ok_rep.passed, msg=f"NTSC {fr} {tc_fmt} should pass")

        for bad_kw in (
            {"configured_frame_rate": "25p"},
            {"configured_frame_rate": "50p"},
            {"tc_format_available": False},
            {"configured_tc_format": P220_PAL_TC_FORMAT_LOCKED},
        ):
            rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(replace(base, **bad_kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_NTSCPAL_FRAMERATE_OR_DFNDF_MISMATCH)

    def test_14_pillar32a_pal_locks_out_2398p_and_df_ndf(self) -> None:
        pal_base = replace(
            build_default_safe_ntscpal_gamma_vault_spec(),
            factory_default_region="PAL",
            pre_reset_ntsc_pal_selector="PAL",
            post_reset_ntsc_pal_selector="PAL",
            startup_banner_observed="",
            configured_frame_rate="25p",
            tc_format_available=False,
            configured_tc_format=P220_PAL_TC_FORMAT_LOCKED,
            restored_backup_ntsc_pal="PAL",
            slot_databases=(
                SlotNtscPalDatabaseSpec(slot=1, card_db_region="PAL", cold_backup_verified=True),
                SlotNtscPalDatabaseSpec(slot=2, card_db_region="PAL", cold_backup_verified=True),
            ),
        )
        for fr in P220_PAL_FRAME_RATES:
            self.assertTrue(
                evaluate_ntscpal_persistence_and_gamma_displaylut_vault(
                    replace(pal_base, configured_frame_rate=fr)
                ).passed
            )

        for bad_kw in (
            {"configured_frame_rate": "23.98p"},
            {"configured_frame_rate": "24.00p"},
            {"configured_frame_rate": "29.97p"},
            {"tc_format_available": True, "configured_tc_format": "NDF"},
            {"configured_tc_format": "DF"},
        ):
            rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(replace(pal_base, **bad_kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_NTSCPAL_FRAMERATE_OR_DFNDF_MISMATCH)

    def test_15_pillar32a_rejects_unbacked_cross_region_dual_slot_db_collision(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        unbacked_pal_card_in_ntsc = replace(
            base,
            slot_databases=(
                SlotNtscPalDatabaseSpec(
                    slot=1,
                    card_db_region="PAL",
                    unbacked_clips_count=8,
                    cold_backup_verified=False,
                    cross_region_card_isolated=False,
                ),
                SlotNtscPalDatabaseSpec(slot=2, card_db_region="NTSC", cold_backup_verified=True),
            ),
        )
        rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(unbacked_pal_card_in_ntsc)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P220_BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION)

        unbacked_backup_bin_region_flip = replace(
            base,
            restored_backup_ntsc_pal="PAL",
            slot_databases=(
                SlotNtscPalDatabaseSpec(
                    slot=1,
                    card_db_region="NTSC",
                    unbacked_clips_count=3,
                    cold_backup_verified=False,
                    cross_region_card_isolated=True,
                ),
            ),
        )
        rep2 = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(unbacked_backup_bin_region_flip)
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P220_BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION)

    def test_16_pillar32a_rejects_destructive_reregister_or_invalid_slot_db_path(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        cases = (
            SlotNtscPalDatabaseSpec(slot=1, card_db_region="NTSC", destructive_reregister_attempted=True),
            SlotNtscPalDatabaseSpec(slot=3, card_db_region="NTSC"),
            SlotNtscPalDatabaseSpec(slot=1, card_db_region="SECAM"),
            SlotNtscPalDatabaseSpec(slot=2, card_db_region="NTSC", m4root_db_relpath="/CLIP/BAD.XML"),
            SlotNtscPalDatabaseSpec(slot=2, card_db_region="NTSC", private_avchd_db_relpath="/AVCHD/BAD.BDM"),
        )
        for bad_slot in cases:
            rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(
                replace(base, slot_databases=(bad_slot,))
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION)

    def test_17_pillar32a_allows_empty_or_isolated_cold_backed_cross_region_card(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        safe_slots = (
            SlotNtscPalDatabaseSpec(
                slot=1,
                card_present=True,
                card_db_region="PAL",
                unbacked_clips_count=12,
                cold_backup_verified=True,
                cross_region_card_isolated=True,
            ),
            SlotNtscPalDatabaseSpec(
                slot=2,
                card_present=True,
                card_db_region="EMPTY_UNINITIALIZED",
            ),
        )
        rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(
            replace(base, slot_databases=safe_slots)
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.dual_slot_db_separation_verified)

    def test_18_pillar32a_supports_all_4_gamma_disp_assist_types_and_unicode_alias(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        for gtype in (*P220_GAMMA_DISP_ASSIST_TYPES, P220_GAMMA_DISP_ASSIST_UNICODE_ALIAS):
            spec = replace(
                base,
                log_shooting_mode="Off",
                gamma_display_assist="On",
                gamma_disp_assist_type=gtype,
                display_lut="Off",
                restored_backup_log_shooting_mode="Off",
                restored_backup_gamma_display_assist="On",
                restored_backup_gamma_disp_assist_type=gtype,
                restored_backup_display_lut="Off",
            )
            rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(spec)
            self.assertTrue(rep.passed, msg=f"Gamma Disp. Assist Typ. {gtype!r} should pass")

    def test_19_pillar32a_log_shooting_hardlocks_gamma_assist_off(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        for log_mode in ("Cine EI", "Cine EI Quick", "Flexible ISO"):
            bad = replace(
                base,
                log_shooting_mode=log_mode,
                gamma_display_assist="On",
                restored_backup_log_shooting_mode=log_mode,
                restored_backup_gamma_display_assist="On",
            )
            rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_GAMMA_ASSIST_DISPLAY_LUT_PARITY_DRIFT)

    def test_20_pillar32a_rejects_gamma_assist_hdmi_external_scope_assumption(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(
            replace(base, gamma_assist_applied_to_hdmi_assumed=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P220_BLOCKED_GAMMA_ASSIST_HDMI_SCOPE_VIOLATION)
        self.assertFalse(rep.gamma_hdmi_lcd_only_scope_verified)

    def test_21_pillar32a_rejects_backup_bin_gamma_or_display_lut_parity_drift(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        for kw in (
            {"restored_backup_log_shooting_mode": "Flexible ISO"},
            {"restored_backup_gamma_display_assist": "On"},
            {"restored_backup_gamma_disp_assist_type": "HLG(709)"},
            {"restored_backup_display_lut": "Off"},
            {"gamma_disp_assist_type": "InvalidGammaType"},
        ):
            rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_GAMMA_ASSIST_DISPLAY_LUT_PARITY_DRIFT)

    def test_22_pillar32a_rejects_persistent_overlay_escape_and_tier0_drift(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        for bad_ov in (
            {"overlay_dir": "/setting/ntscpal_escape"},
            {"overlay_dir": "/dev/cnflasha/defect"},
            {"overlay_wiped_on_reset": False},
        ):
            rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(replace(base, **bad_ov))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        for bad_t0 in (
            {"p2_blkroset_locked": False},
            {"stage_b_backup_bin_writes": 1},
            {"backup_bin_h3_sha256": "deadbeef" * 8},
            {"tier0_surfaces_h0_h3_matched": 15},
        ):
            rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(replace(base, **bad_t0))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_23_pillar32a_rejects_write_unlock_or_wrong_camera(self) -> None:
        base = build_default_safe_ntscpal_gamma_vault_spec()
        for kw in (
            {"persistent_write_unlock_requested": True},
            {"camera_model": "ILME-FX6"},
            {"fw_version": "6.00"},
        ):
            rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_24_pillar32a_6_scenario_suite_passes_all_6(self) -> None:
        suite = run_pillar32a_ntscpal_gamma_vault_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, P220_STATUS_VERIFIED_PILLAR_32A)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in suite.scenarios), P220_PILLAR_32A_SCENARIO_IDS)

    # -----------------------------------------------------------------------
    # Group B: Pillar 32B — Pixel Mapping Auto-Restart (H1->H2) & cnflasha RO Vault
    # -----------------------------------------------------------------------

    def test_25_pillar32b_default_safe_pixelmap_cnflasha_spec_passes(self) -> None:
        rep = evaluate_pixelmap_autorestart_and_cnflasha_vault(
            build_default_safe_pixelmap_cnflasha_vault_spec()
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P220_STATUS_VERIFIED_PILLAR_32B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.low_battery_lockout_verified)
        self.assertTrue(rep.pixelmap_autorestart_h1_to_h2_verified)
        self.assertTrue(rep.h0_equals_h2_verified)
        self.assertTrue(rep.auto_pixelmap_poweroff_darkframe_verified)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertTrue(rep.cnflasha_defect_table_intact)
        self.assertEqual(rep.tier0_surfaces_intact, 16)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_26_pillar32b_rejects_low_battery_before_manual_pixel_mapping(self) -> None:
        base = replace(build_default_safe_pixelmap_cnflasha_vault_spec(), tier0_cold_backup_requested=False)
        for kw in (
            {"battery_pct": 19},
            {"battery_pct": 25, "battery_low_warning": True},
        ):
            rep = evaluate_pixelmap_autorestart_and_cnflasha_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_PIXELMAP_OR_TIER0_LOW_BATTERY)

    def test_27_pillar32b_rejects_low_battery_before_tier0_cold_backup(self) -> None:
        base = build_default_safe_pixelmap_cnflasha_vault_spec()
        for kw in (
            {"battery_pct": 50, "tier0_cold_backup_requested": True},
            {"battery_pct": 105},
            {"battery_pct": -1},
        ):
            rep = evaluate_pixelmap_autorestart_and_cnflasha_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_PIXELMAP_OR_TIER0_LOW_BATTERY)

    def test_28_pillar32b_rejects_missing_autorestart_or_h1_overlay_residue(self) -> None:
        base = build_default_safe_pixelmap_cnflasha_vault_spec()
        for kw in (
            {"camera_operations_blocked_during_calibration": False},
            {"auto_restart_triggered_after_pixelmap": False},
            {"volatile_tmp_overlay_wiped_on_restart": False},
            {"post_restart_state": "H1_STAGE_B_VOLATILE"},
            {"pre_restart_state": "UNKNOWN_STATE"},
            {"post_restart_h2_sha256": "cafe0000" * 8},
            {"tier0_surfaces_h0_h2_matched": 14},
        ):
            rep = evaluate_pixelmap_autorestart_and_cnflasha_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_PIXELMAP_RESTART_H0_H2_OVERLAY_RESIDUE)

    def test_29_pillar32b_auto_pixelmap_silent_mode_poweroff_darkframe_safety(self) -> None:
        base = build_default_safe_pixelmap_cnflasha_vault_spec()
        for kw in (
            {"poweroff_darkframe_battery_pull_attempted": True},
            {"silent_mode_poweroff_shutter_fault_misclassified": True},
            {"auto_pixel_mapping_mode": "On", "silent_mode_enabled": True, "poweroff_shutter_darkframe_sound_expected": False},
            {"auto_pixel_mapping_mode": "InvalidMode"},
        ):
            rep = evaluate_pixelmap_autorestart_and_cnflasha_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_AUTO_PIXELMAP_POWEROFF_SHUTTER_HAZARD)

    def test_30_pillar32b_auto_pixelmap_off_enforces_3day_manual_cadence(self) -> None:
        base = build_default_safe_pixelmap_cnflasha_vault_spec()
        within_3d = replace(base, auto_pixel_mapping_mode="Off", days_since_last_manual_pixelmap=3)
        self.assertTrue(evaluate_pixelmap_autorestart_and_cnflasha_vault(within_3d).passed)

        acked_5d = replace(
            base,
            auto_pixel_mapping_mode="Off",
            days_since_last_manual_pixelmap=5,
            manual_3day_cadence_acknowledged=True,
        )
        self.assertTrue(evaluate_pixelmap_autorestart_and_cnflasha_vault(acked_5d).passed)

        overdue_unacked = replace(
            base,
            auto_pixel_mapping_mode="Off",
            days_since_last_manual_pixelmap=4,
            manual_3day_cadence_acknowledged=False,
        )
        rep = evaluate_pixelmap_autorestart_and_cnflasha_vault(overdue_unacked)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P220_BLOCKED_AUTO_PIXELMAP_POWEROFF_SHUTTER_HAZARD)

    def test_31_pillar32b_strictly_blocks_cnflasha_defect_table_userspace_writes(self) -> None:
        base = build_default_safe_pixelmap_cnflasha_vault_spec()
        for surface in P220_PROTECTED_CNFLASHA_SURFACES:
            rep = evaluate_pixelmap_autorestart_and_cnflasha_vault(
                replace(base, cnflasha_target_partition=surface, cnflasha_userspace_write_attempted=True)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_CNFLASHA_DEFECT_TABLE_WRITE_ATTEMPT)
            self.assertFalse(rep.cnflasha_defect_table_intact)

        rep_mut = evaluate_pixelmap_autorestart_and_cnflasha_vault(
            replace(base, cnflasha_defect_table_mutation_bytes=64)
        )
        self.assertFalse(rep_mut.passed)
        self.assertEqual(rep_mut.block_code, P220_BLOCKED_CNFLASHA_DEFECT_TABLE_WRITE_ATTEMPT)

    def test_32_pillar32b_rejects_persistent_overlay_escape_or_tier0_ro_drift(self) -> None:
        base = build_default_safe_pixelmap_cnflasha_vault_spec()
        rep_ov = evaluate_pixelmap_autorestart_and_cnflasha_vault(
            replace(base, stage_b_overlay_dir="p2:/setting/pixelmap")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P220_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        for kw in ({"p2_blkroset_locked": False}, {"stage_b_backup_bin_writes": 2}):
            rep_t0 = evaluate_pixelmap_autorestart_and_cnflasha_vault(replace(base, **kw))
            self.assertFalse(rep_t0.passed)
            self.assertEqual(rep_t0.block_code, P220_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_33_pillar32b_rejects_write_unlock_or_wrong_camera(self) -> None:
        base = build_default_safe_pixelmap_cnflasha_vault_spec()
        for kw in (
            {"persistent_write_unlock_requested": True},
            {"camera_model": "ILCE-7SM3"},
            {"fw_version": "7.00"},
        ):
            rep = evaluate_pixelmap_autorestart_and_cnflasha_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P220_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_34_monkeypatched_safety_or_cnflasha_constant_immediately_caught(self) -> None:
        with patch.object(p220, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            rep_a = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(
                build_default_safe_ntscpal_gamma_vault_spec()
            )
            rep_b = evaluate_pixelmap_autorestart_and_cnflasha_vault(
                build_default_safe_pixelmap_cnflasha_vault_spec()
            )
            self.assertFalse(rep_a.passed)
            self.assertFalse(rep_b.passed)
            with self.assertRaises(ValueError):
                evaluate_realhw_32pillar_recovery_master(force_clean_room=True)

        with patch.object(p220, "CNFLASHA_USERSPACE_WRITE_BLOCKED", False):
            rep_b2 = evaluate_pixelmap_autorestart_and_cnflasha_vault(
                build_default_safe_pixelmap_cnflasha_vault_spec()
            )
            self.assertFalse(rep_b2.passed)
            with self.assertRaises(ValueError):
                verify_ntscpal_persistence_and_pixelmap_cnflasha_vault(force_clean_room=True)

    def test_35_camera_target_constants_pinned_to_fx3_7_02(self) -> None:
        self.assertEqual(P220_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P220_FX3_FW_VERSION, "7.02")
        self.assertEqual(p220.P220_FX3_MODEL_ID, 0x91030080)

    def test_36_pillar32b_6_scenario_suite_passes_all_6(self) -> None:
        suite = run_pillar32b_pixelmap_cnflasha_vault_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, P220_STATUS_VERIFIED_PILLAR_32B)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in suite.scenarios), P220_PILLAR_32B_SCENARIO_IDS)

    # -----------------------------------------------------------------------
    # Group C: Combined Verifier, 32/32 Master, Fault Injection & Compat
    # -----------------------------------------------------------------------

    def test_37_verify_ntscpal_persistence_and_pixelmap_cnflasha_vault_passes_and_fails_cleanly(self) -> None:
        ok_rep = verify_ntscpal_persistence_and_pixelmap_cnflasha_vault(force_clean_room=True)
        self.assertTrue(ok_rep.all_passed)
        self.assertTrue(ok_rep.passed)
        self.assertEqual(ok_rep.status, P220_STATUS_VERIFIED_PILLAR32_SUITE)
        self.assertTrue(ok_rep.cnflasha_userspace_write_blocked)
        _assert_zero_raw_firmware_leaks(self, ok_rep.to_dict())

        bad_pm = replace(
            build_default_safe_pixelmap_cnflasha_vault_spec(),
            cnflasha_userspace_write_attempted=True,
        )
        fail_rep = verify_ntscpal_persistence_and_pixelmap_cnflasha_vault(
            pixelmap_spec=bad_pm,
            force_clean_room=True,
        )
        self.assertFalse(fail_rep.all_passed)
        self.assertEqual(fail_rep.status, P220_STATUS_FAIL_PILLAR32_SUITE)

    def test_38_run_pillar32_standalone_suite_default_mode(self) -> None:
        rep = run_pillar32_standalone_suite()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P220_STATUS_VERIFIED_PILLAR32_SUITE)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.pillar_32a_ntscpal_gamma_vault.scenarios_passed, 6)
        self.assertEqual(rep.pillar_32b_pixelmap_cnflasha_vault.scenarios_passed, 6)
        _assert_zero_raw_firmware_leaks(self, rep.to_dict())

    def test_39_run_pillar32_standalone_suite_clean_room_mode(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = run_pillar32_standalone_suite()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.cnflasha_userspace_write_blocked)

    def test_40_evaluate_realhw_32pillar_recovery_master_default_mode(self) -> None:
        rep = evaluate_realhw_32pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P220_STATUS_VERIFIED_32OF32_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 32)
        self.assertEqual(rep.pillars_passed, 32)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertLess(rep.elapsed_seconds, P220_CONCURRENT_CEILING_SECONDS)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        _assert_zero_raw_firmware_leaks(self, rep.to_dict())

    def test_41_evaluate_realhw_32pillar_recovery_master_clean_room_mode(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = evaluate_realhw_32pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 32)
        self.assertEqual(rep.pillars_passed, 32)
        self.assertTrue(all(p.verification_mode == "CLEAN_ROOM_SYNTHETIC" for p in rep.pillars))

    def test_42_master_32pillar_deterministic_sha256_and_aliases(self) -> None:
        r1 = evaluate_realhw_32pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_32pillar_recovery_master(force_clean_room=True)
        r3 = verify_32pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_32pillar_sha256, r2.master_32pillar_sha256)
        self.assertEqual(r1.master_32pillar_sha256, r3.master_32pillar_sha256)

    def test_43_fault_injection_on_pillar_32_drops_to_31_of_32(self) -> None:
        rep = evaluate_realhw_32pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_32_ntscpal_pixelmap_cnflasha_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P220_STATUS_FAIL_32OF32_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 32)
        self.assertEqual(rep.pillars_passed, 31)
        self.assertEqual(rep.failed_pillars, ("pillar_32_ntscpal_pixelmap_cnflasha_vault",))

    def test_44_fault_injection_on_earlier_pillar_and_unknown_pillar_error(self) -> None:
        earlier_id = MASTER_32_PILLAR_IDS[30]
        rep = evaluate_realhw_32pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=earlier_id,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 31)
        self.assertEqual(rep.failed_pillars, (earlier_id,))
        with self.assertRaises(ValueError):
            evaluate_realhw_32pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_99_nonexistent",
            )

    def test_45_backward_compatibility_22_24_26_27_28_29_30_31_pillar_masters(self) -> None:
        expected_suites = (
            (evaluate_22pillar_recovery_master, 22),
            (evaluate_24pillar_recovery_master, 24),
            (evaluate_26pillar_recovery_master, 26),
            (evaluate_27pillar_recovery_master, 27),
            (evaluate_28pillar_recovery_master, 28),
            (evaluate_29pillar_recovery_master, 29),
            (evaluate_30pillar_recovery_master, 30),
            (evaluate_31pillar_recovery_master, 31),
        )
        for fn, count in expected_suites:
            rep = fn(force_clean_room=True)
            self.assertTrue(rep.all_passed, msg=f"{count}-pillar suite regressed")
            self.assertEqual(rep.pillar_count, count)
            self.assertEqual(rep.pillars_passed, count)

    def test_46_master_32pillar_statuses_numbered_1_through_32_in_order(self) -> None:
        rep = evaluate_realhw_32pillar_recovery_master(force_clean_room=True)
        self.assertEqual([p.pillar_number for p in rep.pillars], list(range(1, 33)))
        self.assertEqual(tuple(p.pillar_id for p in rep.pillars), MASTER_32_PILLAR_IDS)
        p32 = rep.pillars[-1]
        self.assertEqual(p32.key_metrics["pillar_32a_ntscpal_gamma_vault"], "6/6")
        self.assertEqual(p32.key_metrics["pillar_32b_pixelmap_cnflasha_vault"], "6/6")
        self.assertTrue(p32.key_metrics["cnflasha_userspace_write_blocked"])

    def test_47_master_32pillar_json_roundtrip_integrity(self) -> None:
        rep = evaluate_realhw_32pillar_recovery_master(force_clean_room=True)
        parsed = json.loads(json.dumps(rep.to_dict()))
        self.assertEqual(parsed["schema"], "fx3-realhw-32pillar-recovery-master-verifier-v1")
        self.assertEqual(parsed["pillar_count"], 32)
        self.assertEqual(parsed["pillars_passed"], 32)
        self.assertEqual(len(parsed["pillars"]), 32)

    def test_48_pillar32_combined_report_json_roundtrip_integrity(self) -> None:
        rep = verify_ntscpal_persistence_and_pixelmap_cnflasha_vault(force_clean_room=True)
        parsed = json.loads(json.dumps(rep.to_dict()))
        self.assertEqual(parsed["schema"], "fx3-realhw-32pillar-recovery-master-verifier-v1")
        self.assertTrue(parsed["all_passed"])
        self.assertTrue(parsed["cnflasha_userspace_write_blocked"])

    # -----------------------------------------------------------------------
    # Group D: CLI Subcommands (`verify-ntscpal-pixelmap-vault`, `verify-32pillar-recovery`)
    # -----------------------------------------------------------------------

    def _run_cli(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with patch.object(sys, "argv", ["fx3_recovery", *argv]), patch.object(sys, "stdout", buf):
            rc = cli_main()
        return rc, buf.getvalue()

    def test_49_cli_verify_ntscpal_pixelmap_vault_json_normal_mode(self) -> None:
        rc, out = self._run_cli(["verify-ntscpal-pixelmap-vault", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P220_STATUS_VERIFIED_PILLAR32_SUITE)
        self.assertTrue(payload["cnflasha_userspace_write_blocked"])
        _assert_zero_raw_firmware_leaks(self, payload)

    def test_50_cli_verify_ntscpal_pixelmap_vault_clean_room_summary(self) -> None:
        rc, out = self._run_cli(["verify-ntscpal-pixelmap-vault", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("VERIFIED_PILLAR32_NTSCPAL_PIXELMAP_CNFLASHA_VAULT", out)
        self.assertIn("CLEAN_ROOM_SYNTHETIC", out)
        self.assertIn("cnflasha_userspace_write_blocked=True", out)
        self.assertIn("6/6", out)

    def test_51_cli_verify_ntscpal_pixelmap_vault_clean_room_json(self) -> None:
        rc, out = self._run_cli(["verify-ntscpal-pixelmap-vault", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(payload["all_passed"])

    def test_52_cli_verify_32pillar_recovery_json_normal_mode(self) -> None:
        rc, out = self._run_cli(["verify-32pillar-recovery", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillar_count"], 32)
        self.assertEqual(payload["pillars_passed"], 32)
        self.assertEqual(payload["status"], P220_STATUS_VERIFIED_32OF32_AGGREGATOR)
        self.assertTrue(payload["cnflasha_userspace_write_blocked"])
        _assert_zero_raw_firmware_leaks(self, payload)

    def test_53_cli_verify_32pillar_recovery_clean_room_summary(self) -> None:
        rc, out = self._run_cli(["verify-32pillar-recovery", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("VERIFIED_32OF32_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("32/32", out)
        self.assertIn("CLEAN_ROOM_SYNTHETIC", out)
        self.assertIn("cnflasha_userspace_write_blocked=True", out)

    def test_54_cli_verify_32pillar_recovery_clean_room_json(self) -> None:
        rc, out = self._run_cli(["verify-32pillar-recovery", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["pillars_passed"], 32)

    def test_55_cli_verify_32pillar_recovery_exclusive_out_directory(self) -> None:
        out_dir = HERE / f"_tmp_p220_m32_{os.getpid()}"
        out_dir_p32 = HERE / f"_tmp_p220_p32_{os.getpid()}"
        for d in (out_dir, out_dir_p32):
            if d.exists():
                shutil.rmtree(d)
        try:
            rc, _ = self._run_cli(["verify-32pillar-recovery", "--clean-room", "--out", str(out_dir), "--json"])
            self.assertEqual(rc, 0)
            report_file = out_dir / "32pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["pillars_passed"], 32)

            rc_dup, _ = self._run_cli(["verify-32pillar-recovery", "--clean-room", "--out", str(out_dir), "--json"])
            self.assertEqual(rc_dup, 2)

            rc2, _ = self._run_cli(
                ["verify-ntscpal-pixelmap-vault", "--clean-room", "--out", str(out_dir_p32), "--json"]
            )
            self.assertEqual(rc2, 0)
            self.assertTrue((out_dir_p32 / "pillar32-ntscpal-pixelmap-vault-report.json").is_file())
        finally:
            for d in (out_dir, out_dir_p32):
                if d.exists():
                    shutil.rmtree(d)

    def test_56_cli_backward_compat_verify_31pillar_recovery_still_passes(self) -> None:
        rc, out = self._run_cli(["verify-31pillar-recovery", "--force-clean-room", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillar_count"], 31)
        self.assertEqual(payload["pillars_passed"], 31)


if __name__ == "__main__":
    unittest.main()
