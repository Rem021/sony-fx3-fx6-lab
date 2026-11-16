"""Phase 20 Dual-Mode Test Suite: Stage-B P10 Physical Button Keymap Builder Integration.

Verifies Stage-B (`P1+P4+P8+P10`) integration in `patcher.py` and `candidate_builder.py`:
- 100% backward compatibility with Stage-A (`ALL_PHASE2_TARGET_SPECS` / `STAGE_A_PATCH_SPECS`)
- Zero byte-range overlap across all 10 sites (41 B) of `P1`, `P4`, `P8`, and `P10`
- Deterministic Stage-B `appFw.so` SHA-256, forward commutativity & bit-exact rollback
- Combined-image Unicorn AArch64 execution proofs (`P4`, `P8`, `P5/P6`, 15 native 1:1 + 6 P10 keys)
- Dual-mode coverage: all 16 core/synthetic/dual-mode tests run under `FX3_FX6_FORCE_CLEAN_ROOM=1`
  and all 20 tests run against real read-only FX6/FX3 donor binaries when present.
"""

from __future__ import annotations

import hashlib
import inspect
import os
import struct
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

from fx6_closure.candidate_builder import (
    COMPLETE_MATRIX_ITEMS,
    EXPECTED_STAGE_B_NATIVE_KEYMAP,
    EXPECTED_STAGE_B_P10_KEYMAP,
    CandidateDryRunReport,
    StageBCombinedAppFwReport,
    _build_synthetic_stage_b_appfw_bundle,
    run_offline_candidate_dry_run,
    verify_combined_stage_b_appfw_contract,
)
from fx6_closure.donor_paths import (
    is_forced_clean_room,
    resolve_fx3_modules_dir,
    resolve_fx6_donor_lib_dir,
)
from fx6_closure.elf_verify import PF_R, PF_X
from fx6_closure.patcher import (
    ALL_PATCH_SPECS,
    ALL_PHASE2_TARGET_SPECS,
    FX6_APPFW_DONOR_SHA256,
    FX6_APPFW_P10_ONLY_SHA256,
    FX6_APPFW_STAGE_A_SHA256,
    FX6_APPFW_STAGE_B_SHA256,
    P1_APPFW_SITE,
    P1_P4_P8_APPFW_COMBINED_SPEC,
    P1_P4_P8_P10_APPFW_COMBINED_SPEC,
    P4_APPFW_MODE_SITE,
    P4_APPFW_VALUE_SITE,
    P8_APPFW_SITE,
    P10_KEYMAP_PATCH_SPEC,
    P10_KEYMAP_SITES,
    STAGE_A_PATCH_SPECS,
    STAGE_B_PATCH_SPECS,
    LibraryPatchSpec,
    PatchSiteSpec,
    PatchVerificationError,
    apply_patch_spec,
    build_stage_b_appfw_image,
    get_target_patch_specs,
    read_donor_bytes_readonly,
    rollback_patch_spec,
    verify_patch_sites_non_overlapping,
)
from fx6_closure.peripheral_ux_compatibility_verifier import (
    FX6_KEYMAP_PAIR_COUNT,
    P10_APPFW_KEYMAP_SPEC,
    _unicorn_lookup_synthetic_appfw,
)
from fx6_closure.uipc_completion_verifier import run_p5_p6_uipc_unicorn_audit


_CLEAN_ROOM_SKIP_REASON = "FX3_FX6_FORCE_CLEAN_ROOM=1 or read-only local donor binaries absent"


def _is_clean_room_or_donor_missing() -> bool:
    if is_forced_clean_room():
        return True
    fx6_dir = resolve_fx6_donor_lib_dir()
    fx3_dir = resolve_fx3_modules_dir()
    required = (
        fx6_dir / "appFw.so",
        fx6_dir / "libInfraSetupFile.so",
        fx6_dir / "libInfraMediaCommon.so",
        fx6_dir / "libInfraMediaConfig.so",
        fx6_dir / "libInfraAppRemoteBoard.so",
        fx6_dir / "libfan.so",
        fx3_dir / "upm.ko",
    )
    return any(not p.is_file() for p in required)


class TestPhase20P10StageBIntegration(unittest.TestCase):
    """Dual-mode positive and negative tests for Phase 20 Stage-B P10 integration."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.synth_report = verify_combined_stage_b_appfw_contract(force_synthetic=True)

    def test_01_stage_a_backward_compatibility_specs_unchanged(self) -> None:
        """Stage-A tuple and `include_p10_keymap=False` preserve original 7-target contract."""
        self.assertEqual(ALL_PATCH_SPECS, ALL_PHASE2_TARGET_SPECS)
        self.assertEqual(STAGE_A_PATCH_SPECS, ALL_PHASE2_TARGET_SPECS)
        self.assertEqual(get_target_patch_specs(include_p10_keymap=False), ALL_PHASE2_TARGET_SPECS)
        self.assertEqual(len(ALL_PHASE2_TARGET_SPECS), 7)
        appfw_stage_a = next(s for s in STAGE_A_PATCH_SPECS if s.library_name == "appFw.so")
        self.assertEqual(appfw_stage_a, P1_P4_P8_APPFW_COMBINED_SPEC)
        self.assertEqual(len(appfw_stage_a.sites), 4)
        self.assertEqual(sum(site.size for site in appfw_stage_a.sites), 17)

    def test_02_stage_b_specs_integrate_p10_with_7_unique_targets(self) -> None:
        """Stage-B replaces `appFw.so` spec with combined 10-site 41 B P1+P4+P8+P10 spec."""
        self.assertEqual(get_target_patch_specs(include_p10_keymap=True), STAGE_B_PATCH_SPECS)
        self.assertEqual(len(STAGE_B_PATCH_SPECS), 7)
        self.assertEqual(len({s.library_name for s in STAGE_B_PATCH_SPECS}), 7)
        appfw_stage_b = next(s for s in STAGE_B_PATCH_SPECS if s.library_name == "appFw.so")
        self.assertEqual(appfw_stage_b, P1_P4_P8_P10_APPFW_COMBINED_SPEC)
        self.assertEqual(len(appfw_stage_b.sites), 10)
        self.assertEqual(sum(site.size for site in appfw_stage_b.sites), 41)

    def test_03_p10_keymap_spec_parity_with_phase17_definition(self) -> None:
        """`P10_KEYMAP_PATCH_SPEC` matches Phase 17 `P10_APPFW_KEYMAP_SPEC` bit-for-bit."""
        self.assertEqual(P10_KEYMAP_PATCH_SPEC, P10_APPFW_KEYMAP_SPEC)
        self.assertEqual(len(P10_KEYMAP_SITES), 6)
        self.assertEqual(sum(site.size for site in P10_KEYMAP_SITES), 24)
        for site in P10_KEYMAP_SITES:
            self.assertEqual(site.patch_group, "P10")
            self.assertEqual(site.required_segment_flags, PF_R)
            self.assertGreaterEqual(site.expected_file_offset, 0x2245A10)
            self.assertLess(site.expected_file_offset, 0x2247CE8)

    def test_04_verify_patch_sites_non_overlapping_positive_and_negative(self) -> None:
        """Zero byte overlap verified across all 10 sites; overlaps & cross-lib fail closed."""
        intervals = verify_patch_sites_non_overlapping(
            P1_P4_P8_APPFW_COMBINED_SPEC, P10_KEYMAP_PATCH_SPEC
        )
        self.assertEqual(len(intervals), 10)
        self.assertEqual(sum(end - start for _, _, start, end in intervals), 41)
        for idx in range(len(intervals) - 1):
            self.assertLessEqual(intervals[idx][3], intervals[idx + 1][2])

        overlapping_spec = LibraryPatchSpec(
            spec_id="overlap_test",
            library_name="appFw.so",
            expected_size=50520424,
            donor_sha256=FX6_APPFW_DONOR_SHA256,
            sites=(
                PatchSiteSpec(
                    site_id="overlap_site",
                    patch_group="TEST",
                    symbol_or_desc="overlaps p10_fn_to_home by 2 bytes",
                    vma=0x2245E7E,
                    expected_file_offset=0x2245E7E,
                    required_segment_flags=PF_R,
                    original_bytes=b"\x00\x00\x96\x70",
                    patched_bytes=b"\x01\x00\x96\x70",
                ),
            ),
        )
        with self.assertRaises(PatchVerificationError):
            verify_patch_sites_non_overlapping(P10_KEYMAP_PATCH_SPEC, overlapping_spec)

        with self.assertRaises(PatchVerificationError):
            verify_patch_sites_non_overlapping(
                P10_KEYMAP_PATCH_SPEC, ALL_PHASE2_TARGET_SPECS[0]
            )

    def test_05_read_donor_bytes_readonly_and_safety_defaults(self) -> None:
        """Confirm `O_RDONLY` usage and zero persistent write flag creep."""
        patcher_src = (
            Path(__file__).resolve().parents[1] / "fx6_closure" / "patcher.py"
        ).read_text(encoding="utf-8")
        cb_src = (
            Path(__file__).resolve().parents[1] / "fx6_closure" / "candidate_builder.py"
        ).read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", patcher_src)
        self.assertIn("read_donor_bytes_readonly", cb_src)
        self.assertIn("allow_dry_run_gate12=True", cb_src)

    def test_06_synthetic_combined_stage_b_contract_passes_all_checks(self) -> None:
        """Clean-room synthetic Stage-B combined contract verifies P1+P4+P8+P10 end-to-end."""
        rep = self.synth_report
        self.assertIsInstance(rep, StageBCombinedAppFwReport)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(rep.all_checks_passed)
        self.assertTrue(rep.zero_byte_overlap)
        self.assertEqual(rep.total_site_count, 10)
        self.assertEqual(rep.total_patched_bytes, 41)
        self.assertTrue(rep.sequential_forward_equivalent)
        self.assertTrue(rep.direct_rollback_sha256_matched)
        self.assertTrue(rep.sequential_reverse_rollback_sha256_matched)
        self.assertTrue(rep.p1_site_verified)

    def test_07_synthetic_combined_unicorn_proves_p4_p8_and_all_21_keys(self) -> None:
        """Unicorn on single synthetic Stage-B image proves P4, P8, 15 native 1:1 & 6 P10 keys."""
        rep = self.synth_report
        self.assertEqual(rep.p4_mode_unicorn.assert_hit_count, 0)
        self.assertEqual(rep.p4_mode_unicorn.clear_output_count, rep.p4_mode_unicorn.total_combinations)
        self.assertEqual(rep.p4_value_unicorn.assert_hit_count, 0)
        self.assertEqual(rep.p4_value_unicorn.clear_output_count, rep.p4_value_unicorn.total_combinations)
        self.assertEqual(rep.p8_unicorn.return_value, 0)
        self.assertTrue(rep.p8_unicorn.sp_preserved)
        self.assertTrue(rep.p10_native_1to1_passed)
        self.assertTrue(rep.p10_remapped_passed)
        self.assertEqual(rep.p10_native_1to1_map, EXPECTED_STAGE_B_NATIVE_KEYMAP)
        self.assertEqual(rep.p10_remapped_map, EXPECTED_STAGE_B_P10_KEYMAP)

    def test_08_synthetic_combined_tampered_p10_site_fails_rollback_and_lookup(self) -> None:
        """Mutating a P10 byte breaks both rollback verification and Unicorn key dispatch."""
        (
            donor_bytes,
            _stage_a_spec,
            _p10_spec,
            combined_spec,
            _p4_mode_vma,
            _p4_val_vma,
            _p8_vma,
            lookup_vma,
            keymap_vma,
        ) = _build_synthetic_stage_b_appfw_bundle()
        stage_b_bytes, _ = build_stage_b_appfw_image(
            donor_bytes,
            verify_donor_sha256=False,
            combined_spec=combined_spec,
        )
        fn_site = next(s for s in combined_spec.sites if s.site_id == "p10_fn_to_home")
        mutated = bytearray(stage_b_bytes)
        struct.pack_into("<I", mutated, fn_site.expected_file_offset, 0x00000999)
        tampered = bytes(mutated)

        with self.assertRaises(PatchVerificationError):
            rollback_patch_spec(tampered, combined_spec, enforce_size=False)

        res = _unicorn_lookup_synthetic_appfw(
            tampered,
            lookup_fn_vma=lookup_vma,
            keymap_vma=keymap_vma,
            keymap_count=FX6_KEYMAP_PAIR_COUNT,
            probe_keys=(0x7095,),
        )
        self.assertNotEqual(res[0x7095], 0x184)

    def test_09_synthetic_combined_pre_context_mismatch_fails_closed(self) -> None:
        """Corrupted pre-context before any combined patch site raises `PatchVerificationError`."""
        donor_bytes, _, _, combined_spec, *_ = _build_synthetic_stage_b_appfw_bundle()
        p1_site = next(s for s in combined_spec.sites if s.patch_group == "P1")
        corrupted = bytearray(donor_bytes)
        corrupted[p1_site.expected_file_offset - 1] ^= 0xFF
        with self.assertRaises(PatchVerificationError):
            build_stage_b_appfw_image(
                bytes(corrupted),
                verify_donor_sha256=False,
                combined_spec=combined_spec,
            )

    def test_10_synthetic_reverse_sequential_rollback_stage_b_to_stage_a_to_donor(self) -> None:
        """Reverse sequential rollback (`Stage-B -> Stage-A -> Donor`) restores exact hashes."""
        donor_bytes, stage_a_spec, p10_spec, combined_spec, *_ = _build_synthetic_stage_b_appfw_bundle()
        donor_sha = hashlib.sha256(donor_bytes).hexdigest()
        stage_a_bytes, stage_a_rec = apply_patch_spec(donor_bytes, stage_a_spec, verify_donor_sha256=False)
        stage_b_bytes, _ = build_stage_b_appfw_image(
            donor_bytes, verify_donor_sha256=False, combined_spec=combined_spec
        )

        back_to_a, rec_a = rollback_patch_spec(
            stage_b_bytes,
            p10_spec,
            expected_original_sha256=stage_a_rec.after_sha256,
            enforce_size=False,
        )
        self.assertTrue(rec_a.donor_sha256_matched)
        self.assertEqual(back_to_a, stage_a_bytes)

        back_to_donor, rec_donor = rollback_patch_spec(
            back_to_a,
            stage_a_spec,
            expected_original_sha256=donor_sha,
            enforce_size=False,
        )
        self.assertTrue(rec_donor.donor_sha256_matched)
        self.assertEqual(back_to_donor, donor_bytes)

    def test_11_dual_mode_verify_combined_stage_b_appfw_contract(self) -> None:
        """`verify_combined_stage_b_appfw_contract()` runs cleanly in active CI/donor mode."""
        rep = verify_combined_stage_b_appfw_contract()
        expected_mode = (
            "CLEAN_ROOM_SYNTHETIC_VERIFIED"
            if _is_clean_room_or_donor_missing()
            else "LOCAL_DONOR_AND_UNICORN_VERIFIED"
        )
        self.assertEqual(rep.verification_mode, expected_mode)
        self.assertTrue(rep.all_checks_passed)
        self.assertTrue(rep.p10_native_1to1_passed)
        self.assertTrue(rep.p10_remapped_passed)

    def test_12_candidate_dry_run_report_safe_defaults_and_signature(self) -> None:
        """`CandidateDryRunReport` provides safe defaults and defaults to `include_p10_keymap=True`."""
        sig = inspect.signature(run_offline_candidate_dry_run)
        self.assertTrue(sig.parameters["include_p10_keymap"].default)
        self.assertFalse(sig.parameters["corrupt_stage_b_p10"].default)

        fields = CandidateDryRunReport.__dataclass_fields__
        self.assertEqual(fields["stage_b_p10_keymap_enabled"].default, False)
        self.assertEqual(fields["stage_b_appfw_sha256"].default, "")
        self.assertEqual(fields["stage_b_combined_appfw_verified"].default, False)
        self.assertIsNone(fields["stage_b_p10_summary"].default)

    def test_13_p10_sites_disjoint_from_p1_p4_p8_and_segment_flags_correct(self) -> None:
        """All P10 sites live in `PF_R` `.rodata` completely disjoint from P4/P8 `PF_R|PF_X` & P1."""
        p4_p8_p1_ranges = [
            (s.expected_file_offset, s.expected_file_offset + s.size)
            for s in (P4_APPFW_MODE_SITE, P4_APPFW_VALUE_SITE, P8_APPFW_SITE, P1_APPFW_SITE)
        ]
        for site in P10_KEYMAP_SITES:
            self.assertEqual(site.required_segment_flags, PF_R)
            s0, s1 = site.expected_file_offset, site.expected_file_offset + site.size
            for o0, o1 in p4_p8_p1_ranges:
                self.assertTrue(s1 <= o0 or s0 >= o1)
        self.assertEqual(P4_APPFW_MODE_SITE.required_segment_flags, PF_R | PF_X)
        self.assertEqual(P4_APPFW_VALUE_SITE.required_segment_flags, PF_R | PF_X)
        self.assertEqual(P8_APPFW_SITE.required_segment_flags, PF_R | PF_X)
        self.assertEqual(P1_APPFW_SITE.required_segment_flags, PF_R)

    def test_14_p10_rodata_range_disjoint_from_unicorn_p4_assert_and_p8_pages(self) -> None:
        """Verify 4 KiB pages mapped by P10 table do not alias P4/P8 executable pages."""
        p10_pages = {s.expected_file_offset & ~0xFFF for s in P10_KEYMAP_SITES}
        exec_pages = {
            P4_APPFW_MODE_SITE.expected_file_offset & ~0xFFF,
            P4_APPFW_VALUE_SITE.expected_file_offset & ~0xFFF,
            P8_APPFW_SITE.expected_file_offset & ~0xFFF,
            0x2167000,  # assert page
        }
        self.assertTrue(p10_pages.isdisjoint(exec_pages))

    def test_15_build_stage_b_appfw_image_rejects_custom_overlapping_spec(self) -> None:
        """`build_stage_b_appfw_image` validates non-overlap before touching payload bytes."""
        donor_bytes, _, _, combined_spec, *_ = _build_synthetic_stage_b_appfw_bundle()
        dup_site = combined_spec.sites[0]
        bad_spec = LibraryPatchSpec(
            spec_id="bad_dup",
            library_name="appFw.so",
            expected_size=len(donor_bytes),
            donor_sha256=combined_spec.donor_sha256,
            sites=(dup_site, dup_site),
        )
        with self.assertRaises(PatchVerificationError):
            build_stage_b_appfw_image(
                donor_bytes, verify_donor_sha256=False, combined_spec=bad_spec
            )

    def test_16_stage_a_target_spec_still_excludes_p10_for_cpio_determinism(self) -> None:
        """Stage-A spec tuple remains unchanged so Stage-A CPIO hash stays deterministic."""
        appfw_stage_a = next(s for s in ALL_PHASE2_TARGET_SPECS if s.library_name == "appFw.so")
        self.assertEqual(appfw_stage_a.spec_id, "P1_P4_P8_appFw_combined")
        groups = {site.patch_group for site in appfw_stage_a.sites}
        self.assertEqual(groups, {"P1", "P4", "P8"})

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_17_local_donor_stage_b_deterministic_sha256_and_rollback(self) -> None:
        """On real FX6 `appFw.so`, Stage-A/P10-only/Stage-B SHA-256 and reverse rollback match pins."""
        fx6_dir = resolve_fx6_donor_lib_dir()
        donor = read_donor_bytes_readonly(fx6_dir / "appFw.so")
        self.assertEqual(len(donor), 50_520_424)
        self.assertEqual(hashlib.sha256(donor).hexdigest(), FX6_APPFW_DONOR_SHA256)

        stage_a, rec_a = build_stage_b_appfw_image(donor, include_p10_keymap=False)
        self.assertEqual(rec_a.changed_byte_count, 17)
        self.assertEqual(rec_a.after_sha256, FX6_APPFW_STAGE_A_SHA256)

        p10_only, rec_p10 = apply_patch_spec(donor, P10_KEYMAP_PATCH_SPEC)
        self.assertEqual(rec_p10.changed_byte_count, 24)
        self.assertEqual(rec_p10.after_sha256, FX6_APPFW_P10_ONLY_SHA256)

        stage_b, rec_b = build_stage_b_appfw_image(donor, include_p10_keymap=True)
        self.assertEqual(rec_b.changed_byte_count, 41)
        self.assertEqual(rec_b.after_sha256, FX6_APPFW_STAGE_B_SHA256)

        # Sequential equivalence
        a_then_p10, _ = apply_patch_spec(stage_a, P10_KEYMAP_PATCH_SPEC, verify_donor_sha256=False)
        p10_then_a, _ = apply_patch_spec(p10_only, P1_P4_P8_APPFW_COMBINED_SPEC, verify_donor_sha256=False)
        self.assertEqual(a_then_p10, stage_b)
        self.assertEqual(p10_then_a, stage_b)

        # Reverse rollback: Stage-B -> Stage-A -> Donor
        back_to_a, _ = rollback_patch_spec(stage_b, P10_KEYMAP_PATCH_SPEC, expected_original_sha256=FX6_APPFW_STAGE_A_SHA256)
        back_to_donor, rb = rollback_patch_spec(back_to_a, P1_P4_P8_APPFW_COMBINED_SPEC)
        self.assertTrue(rb.donor_sha256_matched)
        self.assertEqual(back_to_donor, donor)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_18_local_donor_stage_b_combined_unicorn_p4_p8_p5_p6_and_all_21_keys(self) -> None:
        """Execute P4, P8, P5/P6 UIPC, and C++ std::unordered_map keymap on single real Stage-B image."""
        fx6_dir = resolve_fx6_donor_lib_dir()
        donor = read_donor_bytes_readonly(fx6_dir / "appFw.so")
        stage_b, _ = build_stage_b_appfw_image(donor, include_p10_keymap=True)

        rep = verify_combined_stage_b_appfw_contract(fx6_lib_dir=fx6_dir, appfw_raw=donor)
        self.assertEqual(rep.verification_mode, "LOCAL_DONOR_AND_UNICORN_VERIFIED")
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.stage_b_combined_sha256, FX6_APPFW_STAGE_B_SHA256)
        self.assertEqual(rep.p4_mode_unicorn.clear_output_count, 576)
        self.assertEqual(rep.p4_value_unicorn.clear_output_count, 576)
        self.assertEqual(rep.p8_unicorn.return_value, 0)
        self.assertTrue(rep.p8_unicorn.sp_preserved)
        self.assertEqual(rep.p10_native_1to1_map, EXPECTED_STAGE_B_NATIVE_KEYMAP)
        self.assertEqual(rep.p10_remapped_map, EXPECTED_STAGE_B_P10_KEYMAP)

        uipc = run_p5_p6_uipc_unicorn_audit(stage_b)
        self.assertTrue(uipc.all_positive_passed)
        self.assertTrue(uipc.all_negative_captured)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_19_local_donor_candidate_dry_run_stage_b_and_stage_a_compat(self) -> None:
        """Dry-run passes 12/12 gates in both Stage-B (default) and Stage-A (`include_p10_keymap=False`)."""
        rep_b = run_offline_candidate_dry_run(include_p10_keymap=True)
        self.assertTrue(rep_b.candidate_ready)
        self.assertTrue(rep_b.all_12_gates_verified)
        self.assertEqual(rep_b.verified_gate_count, 12)
        self.assertEqual(rep_b.verified_matrix_items, COMPLETE_MATRIX_ITEMS)
        self.assertEqual(len(rep_b.patch_receipts), 7)
        self.assertTrue(rep_b.stage_b_p10_keymap_enabled)
        self.assertTrue(rep_b.stage_b_combined_appfw_verified)
        self.assertEqual(rep_b.stage_b_appfw_sha256, FX6_APPFW_STAGE_B_SHA256)
        self.assertIsNotNone(rep_b.stage_b_p10_summary)
        assert rep_b.stage_b_p10_summary is not None
        self.assertTrue(rep_b.stage_b_p10_summary.all_checks_passed)

        precomputed = dict(
            precomputed_rollback_drill=rep_b.rollback_drill,
            precomputed_feature_routing=rep_b.feature_routing_audit,
            precomputed_backup_mount_tolerance=rep_b.backup_mount_tolerance_audit,
            precomputed_boot_selector_and_banks=rep_b.boot_selector_and_bank_audit,
            precomputed_kernel_dtb=rep_b.kernel_dtb_audit,
            precomputed_storage_and_ram_budget=rep_b.storage_and_ram_budget_audit,
            precomputed_cp_rtos=rep_b.cp_rtos_audit,
            precomputed_p1_recovery_bridge=rep_b.p1_recovery_bridge_audit,
            precomputed_stage_a_orchestrator=rep_b.stage_a_orchestrator_audit,
            precomputed_kmod_userland_abi=rep_b.kmod_userland_abi_audit,
            precomputed_peripheral_ux=rep_b.peripheral_ux_audit,
            precomputed_ap_cp_imaging=rep_b.ap_cp_imaging_audit,
        )
        rep_a = run_offline_candidate_dry_run(include_p10_keymap=False, **precomputed)
        self.assertTrue(rep_a.candidate_ready)
        self.assertTrue(rep_a.all_12_gates_verified)
        self.assertEqual(rep_a.verified_gate_count, 12)
        self.assertEqual(len(rep_a.patch_receipts), 7)
        self.assertFalse(rep_a.stage_b_p10_keymap_enabled)
        self.assertFalse(rep_a.stage_b_combined_appfw_verified)
        self.assertEqual(rep_a.stage_b_appfw_sha256, FX6_APPFW_STAGE_A_SHA256)
        self.assertIsNone(rep_a.stage_b_p10_summary)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_20_local_donor_corrupt_stage_b_p10_blocks_gate_g12(self) -> None:
        """Fault injection: `corrupt_stage_b_p10=True` immediately blocks Gate G12."""
        rep_ok = run_offline_candidate_dry_run(include_p10_keymap=True)
        rep_bad = run_offline_candidate_dry_run(
            include_p10_keymap=True,
            corrupt_stage_b_p10=True,
            precomputed_rollback_drill=rep_ok.rollback_drill,
            precomputed_feature_routing=rep_ok.feature_routing_audit,
            precomputed_backup_mount_tolerance=rep_ok.backup_mount_tolerance_audit,
            precomputed_boot_selector_and_banks=rep_ok.boot_selector_and_bank_audit,
            precomputed_kernel_dtb=rep_ok.kernel_dtb_audit,
            precomputed_storage_and_ram_budget=rep_ok.storage_and_ram_budget_audit,
            precomputed_cp_rtos=rep_ok.cp_rtos_audit,
            precomputed_p1_recovery_bridge=rep_ok.p1_recovery_bridge_audit,
            precomputed_stage_a_orchestrator=rep_ok.stage_a_orchestrator_audit,
            precomputed_kmod_userland_abi=rep_ok.kmod_userland_abi_audit,
            precomputed_peripheral_ux=rep_ok.peripheral_ux_audit,
            precomputed_ap_cp_imaging=rep_ok.ap_cp_imaging_audit,
            precomputed_stage_b_appfw=rep_ok.stage_b_p10_summary,
        )
        self.assertFalse(rep_bad.candidate_ready)
        self.assertFalse(rep_bad.stage_b_combined_appfw_verified)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad.blocked_gate_ids)
        self.assertTrue(rep_bad.temp_dir_cleaned)


if __name__ == "__main__":
    unittest.main()
