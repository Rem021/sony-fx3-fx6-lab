"""Phase 212 dual-mode tests: Pillar 30 (`Px` Atomic Main+Proxy Coupled Vault &
`[Off(HDMI Only)]` Zero-Card Interlock) and Unified `30/30` Milestone Recovery Master.
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
    MASTER_30_PILLAR_COUNT,
    MASTER_30_PILLAR_IDS,
    MASTER_30_PILLAR_SPECS,
    P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH,
    P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK,
    P212_BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT,
    P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD,
    P212_BLOCKED_ORPHANED_SUB_OR_MISSING_PX_PROXY,
    P212_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION,
    P212_BLOCKED_PROXY_PLAYBACK_ASSUMPTION_FORBIDDEN,
    P212_BLOCKED_SAFETY_POLICY_VIOLATION,
    P212_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P212_DONOR_INSPECT_BUDGET_SECONDS,
    P212_FX3_FW_VERSION,
    P212_FX3_MODEL_NAME,
    P212_HDMI_ONLY_4K_FORMATS,
    P212_LOG_SHOOTING_MODES,
    P212_PPLUT_PROFILES,
    P212_PROXY_FORMAT_XAVC_HS_HD,
    P212_PROXY_FORMAT_XAVC_S_HD,
    P212_REC_MEDIA_HDMI_OFF_ONLY,
    P212_REC_MEDIA_HDMI_ON,
    P212_STATUS_FAIL_30OF30_AGGREGATOR,
    P212_STATUS_VERIFIED_30OF30_AGGREGATOR,
    P212_STATUS_VERIFIED_PILLAR30_SUITE,
    P212_STATUS_VERIFIED_PILLAR_30A,
    P212_STATUS_VERIFIED_PILLAR_30B,
    CoupledClipPairSpec,
    HdmiOnlyAndInterlockSpec,
    ProxyCoupledVaultSpec,
    build_default_safe_hdmi_interlock_spec,
    build_default_safe_proxy_vault_spec,
    evaluate_22pillar_recovery_master,
    evaluate_24pillar_recovery_master,
    evaluate_26pillar_recovery_master,
    evaluate_27pillar_recovery_master,
    evaluate_28pillar_recovery_master,
    evaluate_29pillar_recovery_master,
    evaluate_30pillar_recovery_master,
    evaluate_hdmi_only_zero_card_and_interlocks,
    evaluate_proxy_coupled_vault,
    evaluate_realhw_30pillar_recovery_master,
    inspect_phase212_donors_readonly,
    realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier as p212,
    run_pillar30_standalone_suite,
    run_pillar30a_proxy_coupled_vault_6_scenario_suite,
    run_pillar30b_hdmi_only_interlock_6_scenario_suite,
    verify_30pillar_recovery_suite,
    verify_proxy_coupled_and_hdmi_only_vault,
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


class TestPhase212Pillar30ProxyHdmiVaultAnd30Of30Master(unittest.TestCase):
    # -----------------------------------------------------------------------
    # Group 0: Safety invariants, exports, donor check & clean-room fallback
    # -----------------------------------------------------------------------

    def test_01_hardlocked_safety_policy_constants(self) -> None:
        self.assertFalse(p212.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p212.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p212.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p212.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p212.PERSISTENT_WRITE_RELEASE)
        self.assertFalse(p212.ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(p212.ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(p212.ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(p212.ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(p212.LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertTrue(p212.READ_ONLY_DONOR_ACCESS)
        self.assertEqual(p212.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p212.OTP_FUSE_WRITES, 0)
        self.assertEqual(p212.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p212.PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(p212.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p212.PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(p212.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_package_exports_and_zero_symbol_shadowing(self) -> None:
        for sym in (
            "MASTER_30_PILLAR_COUNT",
            "MASTER_30_PILLAR_IDS",
            "MASTER_30_PILLAR_SPECS",
            "verify_proxy_coupled_and_hdmi_only_vault",
            "evaluate_realhw_30pillar_recovery_master",
            "evaluate_30pillar_recovery_master",
            "verify_30pillar_recovery_suite",
            "run_pillar30_standalone_suite",
            "P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD",
            "P212_BLOCKED_ORPHANED_SUB_OR_MISSING_PX_PROXY",
        ):
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym))
        # Ensure safety constants in package root were not mutated or shadowed
        self.assertFalse(fx3_recovery.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(fx3_recovery.SPI_NOR_WRITE_AUTHORIZED)
        self.assertEqual(fx3_recovery.PHYSICAL_DEVICE_WRITES, 0)

    def test_03_master_30_pillar_registry_integrity(self) -> None:
        self.assertEqual(MASTER_30_PILLAR_COUNT, 30)
        self.assertEqual(len(MASTER_30_PILLAR_SPECS), 30)
        self.assertEqual(len(MASTER_30_PILLAR_IDS), 30)
        self.assertEqual(len(set(MASTER_30_PILLAR_IDS)), 30)
        self.assertEqual(MASTER_30_PILLAR_SPECS[-1][0], 30)
        self.assertEqual(MASTER_30_PILLAR_SPECS[-1][1], "pillar_30_proxy_coupled_hdmi_only_vault")

    def test_04_donor_inspection_readonly_bounded_and_under_budget(self) -> None:
        snap = inspect_phase212_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 6)
        self.assertLess(snap.elapsed_seconds, P212_DONOR_INSPECT_BUDGET_SECONDS)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        for art in snap.artifacts:
            self.assertTrue(art.matches_pinned)
            self.assertEqual(len(art.digest_sha256), 64)

    def test_05_forced_clean_room_synthetic_fallback(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase212_donors_readonly()
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(snap.all_donors_present)
            self.assertEqual(snap.donor_files_inspected, 6)
            self.assertLess(snap.elapsed_seconds, P212_DONOR_INSPECT_BUDGET_SECONDS)
            self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_06_missing_local_donor_gracefully_falls_back_to_clean_room(self) -> None:
        with patch.object(p212, "resolve_donor_path", return_value=Path("/nonexistent/fx3/donor/missing.bin")):
            snap = inspect_phase212_donors_readonly(force_clean_room=False)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(snap.all_donors_present)
            self.assertEqual(snap.donor_files_inspected, 6)

    def test_07_donor_read_uses_strict_readonly_nonblock_flags(self) -> None:
        opened_flags: list[int] = []
        real_open = os.open

        def _spy_open(path, flags, *args, **kwargs):
            opened_flags.append(flags)
            return real_open(path, flags, *args, **kwargs)

        with patch("fx3_recovery.realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.os.open", side_effect=_spy_open):
            snap = inspect_phase212_donors_readonly(force_clean_room=False)
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            expected_mask = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            self.assertTrue(len(opened_flags) >= 6)
            for fl in opened_flags:
                self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)
                self.assertEqual(fl & expected_mask, expected_mask)

    def test_08_standalone_suite_determinism_clean_room(self) -> None:
        r1 = run_pillar30_standalone_suite(force_clean_room=True)
        r2 = run_pillar30_standalone_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertEqual(r1.status, P212_STATUS_VERIFIED_PILLAR30_SUITE)

    def test_09_json_serialization_has_zero_raw_bytes_and_valid_json(self) -> None:
        rep = verify_proxy_coupled_and_hdmi_only_vault(force_clean_room=True)
        d = rep.to_dict()
        _assert_zero_raw_firmware_leaks(self, d)
        parsed = json.loads(json.dumps(d, allow_nan=False))
        self.assertEqual(parsed["status"], P212_STATUS_VERIFIED_PILLAR30_SUITE)

    def test_10_default_specs_build_clean_and_pass(self) -> None:
        pr = evaluate_proxy_coupled_vault(build_default_safe_proxy_vault_spec())
        hr = evaluate_hdmi_only_zero_card_and_interlocks(build_default_safe_hdmi_interlock_spec())
        self.assertTrue(pr.passed)
        self.assertEqual(pr.status, P212_STATUS_VERIFIED_PILLAR_30A)
        self.assertTrue(hr.passed)
        self.assertEqual(hr.status, P212_STATUS_VERIFIED_PILLAR_30B)

    # -----------------------------------------------------------------------
    # Group A: Pillar 30A — Px Atomic Main+Proxy Coupled Vault (Slot 1 & Slot 2)
    # -----------------------------------------------------------------------

    def test_11_p30a_slot1_slot2_xavc_hs_and_s_hd_coupled_vault_passes(self) -> None:
        rep = evaluate_proxy_coupled_vault(build_default_safe_proxy_vault_spec())
        self.assertTrue(rep.passed)
        self.assertEqual(rep.slots_audited, (1, 2))
        self.assertEqual(rep.coupled_pairs_audited, 2)
        self.assertEqual(rep.protected_pairs_verified, 1)
        self.assertEqual(rep.orphaned_sub_count, 0)
        self.assertEqual(rep.missing_px_proxy_count, 0)
        self.assertEqual(rep.protect_or_delete_parity_drifts, 0)

    def test_12_p30a_xavc_hs_hd_16m_and_9m_variants_allowed(self) -> None:
        for br in ("16M", "9M"):
            clip = CoupledClipPairSpec(
                stem="20261115_C0010",
                slot=1,
                main_relpath="/M4ROOT/CLIP/20261115_C0010.MP4",
                xml_relpath="/M4ROOT/CLIP/20261115_C0010M01.XML",
                proxy_relpath="/M4ROOT/SUB/20261115_C0010S03.MP4",
                px_metadata_bit=True,
                main_protected=False,
                proxy_protected=False,
                main_codec="XAVC_S_I",
                proxy_format=P212_PROXY_FORMAT_XAVC_HS_HD,
                proxy_resolution="1920x1080",
                proxy_bitrate=br,
                proxy_bit_depth=10,
            )
            rep = evaluate_proxy_coupled_vault(ProxyCoupledVaultSpec(clips=(clip,)))
            self.assertTrue(rep.passed, msg=f"Failed for XAVC HS HD {br}: {rep.errors}")

    def test_13_p30a_xavc_s_hd_720p_8bit_6m_atomic_protect_and_delete(self) -> None:
        prot_clip = CoupledClipPairSpec(
            stem="C0101",
            slot=2,
            main_relpath="/M4ROOT/CLIP/C0101.MP4",
            xml_relpath="/M4ROOT/CLIP/C0101M01.XML",
            proxy_relpath="/M4ROOT/SUB/C0101S03.MP4",
            px_metadata_bit=True,
            main_protected=True,
            proxy_protected=True,
            main_codec="XAVC_S",
            proxy_format=P212_PROXY_FORMAT_XAVC_S_HD,
            proxy_resolution="1280x720",
            proxy_bitrate="6M",
            proxy_bit_depth=8,
            coupled_operation="PROTECT",
        )
        del_clip = CoupledClipPairSpec(
            stem="C0102",
            slot=2,
            main_relpath="/M4ROOT/CLIP/C0102.MP4",
            xml_relpath="/M4ROOT/CLIP/C0102M01.XML",
            proxy_relpath=None,
            px_metadata_bit=False,
            main_protected=False,
            proxy_protected=False,
            main_present=False,
            xml_present=True,
            proxy_present=False,
            coupled_operation="DELETE",
        )
        rep = evaluate_proxy_coupled_vault(ProxyCoupledVaultSpec(clips=(prot_clip, del_clip)))
        self.assertTrue(rep.passed)
        self.assertEqual(rep.protected_pairs_verified, 1)

    def test_14_p30a_reject_orphaned_sub_without_main_clip(self) -> None:
        orphan = replace(
            build_default_safe_proxy_vault_spec().clips[0],
            main_present=False,
            proxy_present=True,
        )
        rep = evaluate_proxy_coupled_vault(ProxyCoupledVaultSpec(clips=(orphan,)))
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P212_BLOCKED_ORPHANED_SUB_OR_MISSING_PX_PROXY)
        self.assertEqual(rep.orphaned_sub_count, 1)

    def test_15_p30a_reject_missing_sub_when_px_bit_set(self) -> None:
        missing_sub = replace(
            build_default_safe_proxy_vault_spec().clips[0],
            px_metadata_bit=True,
            proxy_present=False,
        )
        rep = evaluate_proxy_coupled_vault(ProxyCoupledVaultSpec(clips=(missing_sub,)))
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P212_BLOCKED_ORPHANED_SUB_OR_MISSING_PX_PROXY)
        self.assertEqual(rep.missing_px_proxy_count, 1)

    def test_16_p30a_reject_sub_present_without_px_bit(self) -> None:
        no_px_bit = replace(
            build_default_safe_proxy_vault_spec().clips[0],
            px_metadata_bit=False,
            proxy_present=True,
        )
        rep = evaluate_proxy_coupled_vault(ProxyCoupledVaultSpec(clips=(no_px_bit,)))
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P212_BLOCKED_ORPHANED_SUB_OR_MISSING_PX_PROXY)

    def test_17_p30a_reject_protect_attribute_drift(self) -> None:
        drift = replace(
            build_default_safe_proxy_vault_spec().clips[0],
            main_protected=True,
            proxy_protected=False,
            coupled_operation="PROTECT",
        )
        rep = evaluate_proxy_coupled_vault(ProxyCoupledVaultSpec(clips=(drift,)))
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH)
        self.assertGreaterEqual(rep.protect_or_delete_parity_drifts, 1)

    def test_18_p30a_reject_single_sided_action_and_partial_delete(self) -> None:
        single = replace(build_default_safe_proxy_vault_spec().clips[0], single_sided_action_requested=True)
        rep1 = evaluate_proxy_coupled_vault(ProxyCoupledVaultSpec(clips=(single,)))
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH)

        partial_del = replace(
            build_default_safe_proxy_vault_spec().clips[0],
            main_present=False,
            proxy_present=True,
            coupled_operation="DELETE",
        )
        rep2 = evaluate_proxy_coupled_vault(ProxyCoupledVaultSpec(clips=(partial_del,)))
        self.assertFalse(rep2.passed)

    def test_19_p30a_reject_119_88p_100p_normal_and_sq_ge_100fps_proxy_cutoff(self) -> None:
        for rate in ("119.88p", "100p"):
            rep = evaluate_proxy_coupled_vault(
                replace(build_default_safe_proxy_vault_spec(), normal_rec_frame_rate=rate)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION)
            self.assertFalse(rep.zero_proxy_cutoff_enforced)

        for fps in (100, 120, 200, 240):
            rep_sq = evaluate_proxy_coupled_vault(
                replace(build_default_safe_proxy_vault_spec(), sq_mode_active=True, sq_sensor_fps=fps)
            )
            self.assertFalse(rep_sq.passed)
            self.assertEqual(rep_sq.block_code, P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION)

    def test_20_p30a_reject_proxy_under_off_hdmi_only(self) -> None:
        rep = evaluate_proxy_coupled_vault(
            replace(build_default_safe_proxy_vault_spec(), rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION)

    def test_21_p30a_reject_on_camera_proxy_playback_assumption(self) -> None:
        rep = evaluate_proxy_coupled_vault(
            replace(build_default_safe_proxy_vault_spec(), proxy_playback_on_camera_assumed=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P212_BLOCKED_PROXY_PLAYBACK_ASSUMPTION_FORBIDDEN)
        self.assertFalse(rep.on_camera_proxy_playback_forbidden)

    def test_22_p30a_reject_invalid_proxy_codec_matrix_and_missing_s03_suffix(self) -> None:
        bad_matrix = replace(
            build_default_safe_proxy_vault_spec().clips[0],
            proxy_format=P212_PROXY_FORMAT_XAVC_S_HD,
            proxy_resolution="1920x1080",  # should be 1280x720 for XAVC S HD
            proxy_bitrate="6M",
            proxy_bit_depth=8,
        )
        rep1 = evaluate_proxy_coupled_vault(ProxyCoupledVaultSpec(clips=(bad_matrix,)))
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION)

        bad_name = replace(
            build_default_safe_proxy_vault_spec().clips[0],
            proxy_relpath="/M4ROOT/SUB/C0001.MP4",
        )
        rep2 = evaluate_proxy_coupled_vault(ProxyCoupledVaultSpec(clips=(bad_name,)))
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH)

    def test_23_p30a_reject_persistent_overlay_h0_h3_drift_and_write_unlock(self) -> None:
        rep_ov = evaluate_proxy_coupled_vault(replace(build_default_safe_proxy_vault_spec(), overlay_dir="p2:/setting"))
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P212_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h0 = evaluate_proxy_coupled_vault(
            replace(build_default_safe_proxy_vault_spec(), backup_bin_h3_sha256="deadbeef" * 8)
        )
        self.assertFalse(rep_h0.passed)
        self.assertEqual(rep_h0.block_code, P212_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        rep_wr = evaluate_proxy_coupled_vault(
            replace(build_default_safe_proxy_vault_spec(), persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep_wr.passed)
        self.assertEqual(rep_wr.block_code, P212_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_24_pillar30a_6_scenario_suite_passes_6_of_6(self) -> None:
        s30a = run_pillar30a_proxy_coupled_vault_6_scenario_suite()
        self.assertTrue(s30a.passed)
        self.assertEqual(s30a.scenarios_passed, 6)
        self.assertEqual(s30a.scenarios_total, 6)
        self.assertEqual(len(s30a.scenarios), 6)

    # -----------------------------------------------------------------------
    # Group B: Pillar 30B — Off(HDMI Only) Zero-Card, Log 1080p Downshift & FocusMag x BrightMon
    # -----------------------------------------------------------------------

    def test_25_p30b_off_hdmi_only_explicit_4k_monitor_allowed(self) -> None:
        for fmt in P212_HDMI_ONLY_4K_FORMATS:
            spec = HdmiOnlyAndInterlockSpec(
                operation_context="PRE_SHOOT_MEDIA_VAULT_CHECK",
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY,
                hdmi_only_4k_output_set=fmt,
                internal_card_recording_active=False,
                operator_assumes_internal_card_recording=False,
                hdmi_info_display=False,
                hdmi_desqueeze_active=False,
            )
            rep = evaluate_hdmi_only_zero_card_and_interlocks(spec)
            self.assertTrue(rep.passed, msg=f"Expected pass for {fmt}: {rep.errors}")
            self.assertEqual(rep.effective_hdmi_resolution, "2160p_10bit_HDMI_ONLY")
            self.assertFalse(rep.internal_card_recording_active)
            self.assertTrue(rep.hdmi_info_display_suppressed)

    def test_26_p30b_block_off_hdmi_only_zero_card_operator_hazard(self) -> None:
        base = HdmiOnlyAndInterlockSpec(
            operation_context="PRE_SHOOT_MEDIA_VAULT_CHECK",
            rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY,
            hdmi_only_4k_output_set="23.98p 10bit",
            internal_card_recording_active=False,
            operator_assumes_internal_card_recording=True,
        )
        rep = evaluate_hdmi_only_zero_card_and_interlocks(base)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD)
        self.assertTrue(rep.zero_card_hazard_detected)

    def test_27_p30b_block_off_hdmi_only_internal_active_or_prebackup_tier0(self) -> None:
        r_int = evaluate_hdmi_only_zero_card_and_interlocks(
            HdmiOnlyAndInterlockSpec(
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY,
                hdmi_only_4k_output_set="24.00p 10bit",
                internal_card_recording_active=True,
                operator_assumes_internal_card_recording=False,
            )
        )
        self.assertFalse(r_int.passed)
        self.assertEqual(r_int.block_code, P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD)

        r_bak = evaluate_hdmi_only_zero_card_and_interlocks(
            HdmiOnlyAndInterlockSpec(
                operation_context="PRE_BACKUP_TIER0",
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY,
                hdmi_only_4k_output_set="59.94p 10bit",
                internal_card_recording_active=False,
                operator_assumes_internal_card_recording=False,
            )
        )
        self.assertFalse(r_bak.passed)
        self.assertEqual(r_bak.block_code, P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD)

    def test_28_p30b_off_hdmi_only_rejects_invalid_4k_set_or_unsuppressed_info_desqueeze(self) -> None:
        r_bad_fmt = evaluate_hdmi_only_zero_card_and_interlocks(
            HdmiOnlyAndInterlockSpec(
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY,
                hdmi_only_4k_output_set="119.88p 10bit",
                internal_card_recording_active=False,
                operator_assumes_internal_card_recording=False,
            )
        )
        self.assertFalse(r_bad_fmt.passed)
        self.assertEqual(r_bad_fmt.block_code, P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD)

        r_info = evaluate_hdmi_only_zero_card_and_interlocks(
            HdmiOnlyAndInterlockSpec(
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY,
                hdmi_only_4k_output_set="29.97p 10bit",
                internal_card_recording_active=False,
                operator_assumes_internal_card_recording=False,
                hdmi_info_display=True,
            )
        )
        self.assertFalse(r_info.passed)
        self.assertEqual(r_info.block_code, P212_BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT)

    def test_29_p30b_rec_media_on_log_and_pplut_force_1080p_downshift(self) -> None:
        for mode in P212_LOG_SHOOTING_MODES:
            rep = evaluate_hdmi_only_zero_card_and_interlocks(
                HdmiOnlyAndInterlockSpec(
                    rec_media_hdmi_output=P212_REC_MEDIA_HDMI_ON,
                    log_shooting_mode=mode,
                    hdmi_output_resolution="1080p",
                    raw_output_enabled=False,
                )
            )
            self.assertTrue(rep.passed)
            self.assertTrue(rep.hdmi_log_pplut_1080p_downshift_active)
            self.assertEqual(rep.effective_hdmi_resolution, "1080p")

        for pp in P212_PPLUT_PROFILES:
            rep_pp = evaluate_hdmi_only_zero_card_and_interlocks(
                HdmiOnlyAndInterlockSpec(
                    rec_media_hdmi_output=P212_REC_MEDIA_HDMI_ON,
                    picture_profile=pp,
                    hdmi_output_resolution="2160p",  # should be rejected without 1080p downshift
                    raw_output_enabled=False,
                )
            )
            self.assertFalse(rep_pp.passed)
            self.assertEqual(rep_pp.block_code, P212_BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT)

    def test_30_p30b_raw_output_forces_hdmi_info_off_and_desqueeze_off(self) -> None:
        rep_ok = evaluate_hdmi_only_zero_card_and_interlocks(
            HdmiOnlyAndInterlockSpec(
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_ON,
                raw_output_enabled=True,
                hdmi_info_display=False,
                hdmi_desqueeze_active=False,
            )
        )
        self.assertTrue(rep_ok.passed)
        self.assertEqual(rep_ok.effective_hdmi_resolution, "4264x2408_RAW16")

        rep_bad = evaluate_hdmi_only_zero_card_and_interlocks(
            HdmiOnlyAndInterlockSpec(
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_ON,
                raw_output_enabled=True,
                hdmi_desqueeze_active=True,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P212_BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT)

    def test_31_p30b_hdmi_info_display_on_requires_lcd_panel_blanked(self) -> None:
        rep_ok = evaluate_hdmi_only_zero_card_and_interlocks(
            HdmiOnlyAndInterlockSpec(
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_ON,
                hdmi_info_display=True,
                lcd_panel_blanked=True,
            )
        )
        self.assertTrue(rep_ok.passed)

        rep_bad = evaluate_hdmi_only_zero_card_and_interlocks(
            HdmiOnlyAndInterlockSpec(
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_ON,
                hdmi_info_display=True,
                lcd_panel_blanked=False,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P212_BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT)

    def test_32_p30b_focus_magnifier_x1_x4_and_reject_invalid_scales_or_auto_mf(self) -> None:
        for sc in ("x1.0", "x4.0"):
            rep = evaluate_hdmi_only_zero_card_and_interlocks(
                replace(build_default_safe_hdmi_interlock_spec(), focus_magnifier_active=True, focus_magnifier_scale=sc)
            )
            self.assertTrue(rep.passed)

        rep_bad_sc = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(build_default_safe_hdmi_interlock_spec(), focus_magnifier_active=True, focus_magnifier_scale="x5.9")
        )
        self.assertFalse(rep_bad_sc.passed)
        self.assertEqual(rep_bad_sc.block_code, P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK)

        rep_auto = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(build_default_safe_hdmi_interlock_spec(), auto_magnifier_in_mf_movie_enabled=True)
        )
        self.assertFalse(rep_auto.passed)
        self.assertEqual(rep_auto.block_code, P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK)

    def test_33_p30b_focus_magnifier_marker_suppression_and_bright_monitoring_lockout(self) -> None:
        rep_marker = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(
                build_default_safe_hdmi_interlock_spec(),
                focus_magnifier_active=True,
                marker_display_visible_during_mag=True,
            )
        )
        self.assertFalse(rep_marker.passed)
        self.assertEqual(rep_marker.block_code, P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK)

        rep_bm_leak = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(
                build_default_safe_hdmi_interlock_spec(),
                focus_magnifier_active=True,
                bright_monitoring_toggle_attempted_while_mag=True,
                bright_monitoring_toggle_accepted=True,
            )
        )
        self.assertFalse(rep_bm_leak.passed)
        self.assertEqual(rep_bm_leak.block_code, P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK)

    def test_34_p30b_bright_monitoring_requires_pasm_mf_and_setting_effect_off(self) -> None:
        for exp in ("P", "A", "S", "M"):
            rep_ok = evaluate_hdmi_only_zero_card_and_interlocks(
                replace(
                    build_default_safe_hdmi_interlock_spec(),
                    bright_monitoring_active=True,
                    exposure_mode=exp,
                    focus_mode="MF",
                    live_view_display="Setting Effect OFF",
                )
            )
            self.assertTrue(rep_ok.passed)

        rep_af = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(
                build_default_safe_hdmi_interlock_spec(),
                bright_monitoring_active=True,
                exposure_mode="M",
                focus_mode="AF-C",
            )
        )
        self.assertFalse(rep_af.passed)
        self.assertEqual(rep_af.block_code, P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK)

        rep_effect_on = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(
                build_default_safe_hdmi_interlock_spec(),
                bright_monitoring_active=True,
                live_view_display="Setting Effect ON",
            )
        )
        self.assertFalse(rep_effect_on.passed)
        self.assertEqual(rep_effect_on.block_code, P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK)

    def test_35_p30b_stage_b_tmpfs_overlay_wipe_and_p2_blkroset_enforced(self) -> None:
        r_dir = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(build_default_safe_hdmi_interlock_spec(), stage_b_overlay_dir="/setting/hdmi_overlay")
        )
        self.assertFalse(r_dir.passed)
        self.assertEqual(r_dir.block_code, P212_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        r_wipe = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(build_default_safe_hdmi_interlock_spec(), stage_b_overlay_wiped_on_reset=False)
        )
        self.assertFalse(r_wipe.passed)
        self.assertEqual(r_wipe.block_code, P212_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        r_blk = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(build_default_safe_hdmi_interlock_spec(), p2_blkroset_locked=False)
        )
        self.assertFalse(r_blk.passed)
        self.assertEqual(r_blk.block_code, P212_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_36_p30b_backup_bin_writes_and_16_surface_h0_h3_drift_blocked(self) -> None:
        r_wr = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(build_default_safe_hdmi_interlock_spec(), stage_b_backup_bin_writes=1)
        )
        self.assertFalse(r_wr.passed)
        self.assertEqual(r_wr.block_code, P212_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        r_15 = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(build_default_safe_hdmi_interlock_spec(), tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(r_15.passed)
        self.assertEqual(r_15.block_code, P212_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)
        self.assertFalse(r_15.h0_equals_h3_verified)

    def test_37_p30b_unsupported_host_and_write_unlock_rejected(self) -> None:
        r_host = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(build_default_safe_hdmi_interlock_spec(), camera_model="ILME-FX3A")
        )
        self.assertFalse(r_host.passed)
        self.assertEqual(r_host.block_code, P212_BLOCKED_SAFETY_POLICY_VIOLATION)

        r_unlock = evaluate_hdmi_only_zero_card_and_interlocks(
            replace(build_default_safe_hdmi_interlock_spec(), persistent_write_unlock_requested=True)
        )
        self.assertFalse(r_unlock.passed)
        self.assertEqual(r_unlock.block_code, P212_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_38_pillar30b_6_scenario_suite_passes_6_of_6(self) -> None:
        s30b = run_pillar30b_hdmi_only_interlock_6_scenario_suite()
        self.assertTrue(s30b.passed)
        self.assertEqual(s30b.scenarios_passed, 6)
        self.assertEqual(s30b.scenarios_total, 6)
        self.assertEqual(len(s30b.scenarios), 6)

    def test_39_safety_invariant_tamper_monkeypatch_fails_closed(self) -> None:
        with patch.object(p212, "PHYSICAL_DEVICE_WRITES", 1):
            rep = evaluate_proxy_coupled_vault(build_default_safe_proxy_vault_spec())
            self.assertFalse(rep.passed)
            self.assertTrue(any("PHYSICAL_DEVICE_WRITES" in e for e in rep.errors))

    # -----------------------------------------------------------------------
    # Group C: Unified Pillar 30, 30/30 Milestone Master & 22..29 Backward Compat
    # -----------------------------------------------------------------------

    def test_40_verify_proxy_coupled_and_hdmi_only_vault_clean_and_fault(self) -> None:
        ok_rep = verify_proxy_coupled_and_hdmi_only_vault(force_clean_room=True)
        self.assertTrue(ok_rep.all_passed)
        self.assertTrue(ok_rep.passed)
        self.assertEqual(ok_rep.status, P212_STATUS_VERIFIED_PILLAR30_SUITE)

        bad_hdmi = HdmiOnlyAndInterlockSpec(
            rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY,
            hdmi_only_4k_output_set="23.98p 10bit",
            internal_card_recording_active=False,
            operator_assumes_internal_card_recording=True,
        )
        bad_rep = verify_proxy_coupled_and_hdmi_only_vault(hdmi_spec=bad_hdmi, force_clean_room=True)
        self.assertFalse(bad_rep.all_passed)
        self.assertEqual(bad_rep.hdmi_report.block_code, P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD)

    def test_41_evaluate_30pillar_recovery_master_normal_mode(self) -> None:
        rep = evaluate_realhw_30pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P212_STATUS_VERIFIED_30OF30_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 30)
        self.assertEqual(rep.pillars_passed, 30)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, 6.0)
        self.assertTrue(rep.under_6s_budget)
        _assert_zero_raw_firmware_leaks(self, rep.to_dict())

    def test_42_evaluate_30pillar_recovery_master_clean_room_mode(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_30pillar_recovery_master()
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.pillars_passed, 30)
            self.assertEqual(rep.pillar_count, 30)
            self.assertLess(rep.elapsed_seconds, 6.0)
            _assert_zero_raw_firmware_leaks(self, rep.to_dict())

    def test_43_evaluate_30pillar_master_determinism_and_aliases(self) -> None:
        r1 = evaluate_30pillar_recovery_master(force_clean_room=True)
        r2 = verify_30pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_30pillar_sha256, r2.master_30pillar_sha256)
        self.assertEqual(len(r1.pillars), 30)
        self.assertEqual(tuple(p.pillar_id for p in r1.pillars), MASTER_30_PILLAR_IDS)

    def test_44_master_fault_inject_pillar_15_and_pillar_30(self) -> None:
        r15 = evaluate_realhw_30pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_30_PILLAR_IDS[14],
        )
        self.assertFalse(r15.all_passed)
        self.assertEqual(r15.status, P212_STATUS_FAIL_30OF30_AGGREGATOR)
        self.assertEqual(r15.pillars_passed, 29)
        self.assertIn(MASTER_30_PILLAR_IDS[14], r15.failed_pillars)

        r30 = evaluate_realhw_30pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_30_proxy_coupled_hdmi_only_vault",
        )
        self.assertFalse(r30.all_passed)
        self.assertEqual(r30.status, P212_STATUS_FAIL_30OF30_AGGREGATOR)
        self.assertEqual(r30.pillars_passed, 29)
        self.assertIn("pillar_30_proxy_coupled_hdmi_only_vault", r30.failed_pillars)

    def test_45_backward_compat_22pillar_and_24pillar_masters(self) -> None:
        m22 = evaluate_22pillar_recovery_master(force_clean_room=True)
        m24 = evaluate_24pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m22.all_passed)
        self.assertEqual(m22.pillars_passed, 22)
        self.assertTrue(m24.all_passed)
        self.assertEqual(m24.pillars_passed, 24)

    def test_46_backward_compat_26pillar_and_27pillar_masters(self) -> None:
        m26 = evaluate_26pillar_recovery_master(force_clean_room=True)
        m27 = evaluate_27pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m26.all_passed)
        self.assertEqual(m26.pillars_passed, 26)
        self.assertTrue(m27.all_passed)
        self.assertEqual(m27.pillars_passed, 27)

    def test_47_backward_compat_28pillar_and_29pillar_masters(self) -> None:
        m28 = evaluate_28pillar_recovery_master(force_clean_room=True)
        m29 = evaluate_29pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m28.all_passed)
        self.assertEqual(m28.pillars_passed, 28)
        self.assertTrue(m29.all_passed)
        self.assertEqual(m29.pillars_passed, 29)

    def test_48_concurrent_budget_under_nominal_or_ceiling(self) -> None:
        rep = evaluate_realhw_30pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.under_6s_budget)
        self.assertLess(rep.elapsed_seconds, p212.P212_CONCURRENT_CEILING_SECONDS)

    # -----------------------------------------------------------------------
    # Group D: CLI Subcommands (Normal, Clean-Room, --json, --out & Compat)
    # -----------------------------------------------------------------------

    def _run_cli(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        old_argv = sys.argv
        old_stdout = sys.stdout
        try:
            sys.argv = ["fx3_recovery"] + argv
            sys.stdout = buf
            rc = cli_main()
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout
        return rc, buf.getvalue().strip()

    def test_49_cli_verify_proxy_coupled_hdmi_vault_normal_and_clean_json(self) -> None:
        rc1, out1 = self._run_cli(["verify-proxy-coupled-hdmi-vault", "--json"])
        self.assertEqual(rc1, 0)
        d1 = json.loads(out1)
        self.assertEqual(d1["status"], P212_STATUS_VERIFIED_PILLAR30_SUITE)
        _assert_zero_raw_firmware_leaks(self, d1)

        rc2, out2 = self._run_cli(["verify-proxy-coupled-hdmi-vault", "--force-clean-room", "--json"])
        self.assertEqual(rc2, 0)
        d2 = json.loads(out2)
        self.assertEqual(d2["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(d2["all_passed"])

    def test_50_cli_verify_proxy_coupled_hdmi_vault_summary_text(self) -> None:
        rc, out = self._run_cli(["verify-proxy-coupled-hdmi-vault", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("status=VERIFIED_PILLAR30_PROXY_HDMI_ONLY_VAULT", out)
        self.assertIn("pillar_30a=6/6", out)
        self.assertIn("pillar_30b=6/6", out)
        self.assertIn("physical_device_writes=0", out)

    def test_51_cli_verify_30pillar_recovery_normal_and_clean_json(self) -> None:
        rc1, out1 = self._run_cli(["verify-30pillar-recovery", "--json"])
        self.assertEqual(rc1, 0)
        d1 = json.loads(out1)
        self.assertEqual(d1["status"], P212_STATUS_VERIFIED_30OF30_AGGREGATOR)
        self.assertEqual(d1["pillars_passed"], 30)
        self.assertEqual(d1["pillar_count"], 30)
        _assert_zero_raw_firmware_leaks(self, d1)

        rc2, out2 = self._run_cli(["verify-30pillar-recovery", "--force-clean-room", "--json"])
        self.assertEqual(rc2, 0)
        d2 = json.loads(out2)
        self.assertEqual(d2["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(d2["pillars_passed"], 30)

    def test_52_cli_verify_30pillar_recovery_summary_text(self) -> None:
        rc, out = self._run_cli(["verify-30pillar-recovery", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("status=VERIFIED_30OF30_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("pillars=30/30", out)
        self.assertIn("pillar30_a=6/6", out)
        self.assertIn("pillar30_b=6/6", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

    def test_53_cli_out_writes_json_reports_exclusively(self) -> None:
        out_p30 = HERE / f"_tmp_p212_p30_{os.getpid()}"
        out_m30 = HERE / f"_tmp_p212_m30_{os.getpid()}"
        for d in (out_p30, out_m30):
            if d.exists():
                shutil.rmtree(d)
        try:
            rc1, _ = self._run_cli(["verify-proxy-coupled-hdmi-vault", "--force-clean-room", "--out", str(out_p30), "--json"])
            self.assertEqual(rc1, 0)
            p30_file = out_p30 / "pillar30-proxy-coupled-hdmi-vault-report.json"
            self.assertTrue(p30_file.is_file())

            rc2, _ = self._run_cli(["verify-30pillar-recovery", "--force-clean-room", "--out", str(out_m30), "--json"])
            self.assertEqual(rc2, 0)
            m30_file = out_m30 / "30pillar-recovery-master-report.json"
            self.assertTrue(m30_file.is_file())
            loaded = json.loads(m30_file.read_text(encoding="utf-8"))
            self.assertEqual(loaded["pillars_passed"], 30)
        finally:
            for d in (out_p30, out_m30):
                if d.exists():
                    shutil.rmtree(d)

    def test_54_cli_backward_compat_29pillar_recovery(self) -> None:
        rc, out = self._run_cli(["verify-29pillar-recovery", "--force-clean-room", "--json"])
        self.assertEqual(rc, 0)
        d = json.loads(out)
        self.assertEqual(d["pillars_passed"], 29)
        self.assertEqual(d["pillar_count"], 29)


if __name__ == "__main__":
    unittest.main()
