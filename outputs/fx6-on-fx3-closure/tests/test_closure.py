"""Comprehensive Unit Test Suite for `outputs/fx6-on-fx3-closure` (Phase 2 Full Closure).

Covers:
- ELF64 `ET_DYN` (`PT_LOAD`) & `ET_REL` (`.ko` section) mappers and negative boundary checks
- P1 (4-library equal-length `/dev/nflasha20` -> `/dev/nflasha30` adaptation & 100% SHA-256 rollback)
- P2 (`vfat_builder.py` 8 MiB / 16 MiB / 44.5 MiB VFAT image synthesis & BPB/FAT/directory audits)
- P3, P4, P8, P9 (`upm.ko` `.text+0x136b8`), and Fan (`libfan.so` `0x1dec`) adaptation, rollback & Unicorn checks
- Tier-0 Read-Only Backup Worker (`tier0_unicorn_verifier.py`) positive & fault-injection runs
- End-to-End Offline Candidate Dry-Run & 12-Gate Safety Evaluator (`candidate_builder.py`) + CLI (`__main__.py`)
"""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from fx3_safety.preflight import TIER0_CANONICAL_SOURCES, TIER0_REQUIRED_BACKUPS

from fx6_closure.__main__ import main as cli_main
from fx6_closure.candidate_builder import run_offline_candidate_dry_run
from fx6_closure.elf_verify import (
    PF_R,
    PF_W,
    SHF_ALLOC,
    SHF_EXECINSTR,
    SHF_WRITE,
    ElfMappingError,
    parse_elf64_aarch64,
    parse_elf64_relocatable_aarch64,
    section_offset_to_file_offset,
    vma_to_file_offset,
)
from fx6_closure.nd_unicorn_verifier import (
    run_fan_libfan_unicorn_check,
    run_p3_remoteboard_unicorn_check,
    run_p4_nd_unicorn_sweep,
    run_p8_appfw_unicorn_check,
    run_p9_upm_ko_unicorn_check,
)
from fx6_closure.patcher import (
    ALL_P1_SPECS,
    ALL_PHASE2_TARGET_SPECS,
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FAN_LIBFAN_SPEC,
    P1_AND_P4_APPFW_COMBINED_SPEC,
    P1_P4_P8_APPFW_COMBINED_SPEC,
    P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC,
    P4_APPFW_ONLY_SPEC,
    P8_APPFW_ONLY_SPEC,
    P9_UPM_KO_SPEC,
    PatchVerificationError,
    apply_patch_spec,
    generate_p1_lut_mount_snippet,
    rollback_patch_spec,
)
from fx6_closure.tier0_unicorn_verifier import (
    CompiledWorkerArtifact,
    ERR_BK4_MAGIC,
    ERR_BOOT_SYMMETRY,
    ERR_DST_OPEN_EXCL_FAILED,
    ERR_REENTRANT_LOCK,
    ERR_SECTOR0_MAGIC,
    ERR_TWOPASS_SHA256_MISMATCH,
    WORKER_OK,
    compile_tier0_worker_shared_object,
    run_tier0_worker_in_unicorn,
)
from fx6_closure.vfat_builder import (
    SECTOR_SIZE,
    build_opelog_vfat_image,
    generate_p2_opelog_mount_snippet,
    verify_vfat_image,
)


class TestElf64Mapper(unittest.TestCase):
    """Validate strict ELF64 `PT_LOAD` and `ET_REL` section file-offset translation."""

    def test_elf64_pt_load_and_nobits_or_permission_rejection(self) -> None:
        raw = (DEFAULT_FX6_DONOR_LIB_DIR / "libInfraSetupFile.so").read_bytes()
        elf = parse_elf64_aarch64(raw)
        self.assertGreaterEqual(len(elf.load_segments), 2)

        foff, seg = vma_to_file_offset(elf, 0x25E9C, size=1, required_flags=PF_R)
        self.assertEqual(foff, 0x25E9C)
        self.assertEqual(seg.index, 0)

        with self.assertRaises(ElfMappingError):
            vma_to_file_offset(elf, 0x25E9C, size=1, required_flags=PF_W)

        with self.assertRaises(ElfMappingError):
            vma_to_file_offset(elf, 0x7FFF0000, size=4)

        rw_bss_segs = [s for s in elf.load_segments if s.p_memsz > s.p_filesz]
        self.assertTrue(len(rw_bss_segs) >= 1)
        bss_vma = rw_bss_segs[0].p_vaddr + rw_bss_segs[0].p_filesz
        with self.assertRaises(ElfMappingError) as ctx:
            vma_to_file_offset(elf, bss_vma, size=1)
        self.assertIn("NOBITS", str(ctx.exception))

        with self.assertRaises(ElfMappingError):
            parse_elf64_aarch64(b"NOT_ELF!" + raw[8:])

    def test_elf64_relocatable_ko_section_mapper(self) -> None:
        upm_raw = (DEFAULT_FX3_MODULES_DIR / "upm.ko").read_bytes()
        elf_rel = parse_elf64_relocatable_aarch64(upm_raw)
        foff, sec = section_offset_to_file_offset(
            elf_rel,
            ".text",
            0x136B8,
            size=4,
            required_sh_flags=SHF_ALLOC | SHF_EXECINSTR,
        )
        self.assertEqual(foff, 0x13720)
        self.assertEqual(sec.name, ".text")

        # Requiring SHF_WRITE on .text or querying .bss (SHT_NOBITS) must fail closed
        with self.assertRaises(ElfMappingError):
            section_offset_to_file_offset(elf_rel, ".text", 0x136B8, size=4, required_sh_flags=SHF_WRITE)
        with self.assertRaises(ElfMappingError):
            section_offset_to_file_offset(elf_rel, ".bss", 0, size=4)


class TestP1LutPathAdaptationAndRollback(unittest.TestCase):
    """Verify P1 4-library equal-length `/dev/nflasha20` -> `/dev/nflasha30` adaptation & rollback."""

    def test_p1_all_four_donor_libraries_patch_and_byte_exact_rollback(self) -> None:
        self.assertEqual(len(ALL_P1_SPECS), 4)

        with tempfile.TemporaryDirectory(prefix="p1_donor_copy_test_") as tmp_dir:
            tmp_root = Path(tmp_dir)
            for spec in ALL_P1_SPECS:
                donor_path = DEFAULT_FX6_DONOR_LIB_DIR / spec.library_name
                raw = donor_path.read_bytes()
                self.assertEqual(len(raw), spec.expected_size)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), spec.donor_sha256)

                work_copy = tmp_root / spec.library_name
                work_copy.write_bytes(raw)
                patched, patch_rec = apply_patch_spec(work_copy.read_bytes(), spec)
                work_copy.write_bytes(patched)

                self.assertEqual(len(patched), len(raw))
                self.assertEqual(patch_rec.changed_byte_count, 1)
                site_off = patch_rec.resolutions[0].file_offset
                self.assertEqual(patched[site_off - 12 : site_off + 3], b"/dev/nflasha30\x00")

                restored, rb_rec = rollback_patch_spec(work_copy.read_bytes(), spec)
                self.assertTrue(rb_rec.donor_sha256_matched)
                self.assertEqual(rb_rec.restored_sha256, spec.donor_sha256)
                self.assertEqual(restored, raw)

    def test_patcher_rejects_tampered_context_or_double_patch(self) -> None:
        spec = ALL_P1_SPECS[0]
        raw = (DEFAULT_FX6_DONOR_LIB_DIR / spec.library_name).read_bytes()
        patched, _ = apply_patch_spec(raw, spec)

        with self.assertRaises(PatchVerificationError):
            apply_patch_spec(patched, spec, verify_donor_sha256=False)

        tampered = bytearray(raw)
        tampered[spec.sites[0].expected_file_offset - 2] ^= 0xFF
        with self.assertRaises(PatchVerificationError):
            apply_patch_spec(bytes(tampered), spec, verify_donor_sha256=False)

    def test_p1_idempotent_mount_snippet(self) -> None:
        snippet = generate_p1_lut_mount_snippet()
        self.assertIn("rm -f /dev/nflasha20 /dev/cnflasha20 /dev/pnflasha20", snippet)
        self.assertIn('ln -s "/dev/cnflasha30" /dev/nflasha20', snippet)
        self.assertIn('mkdir -p "/usr/data/lut"', snippet)


class TestP2OpelogVfatBuilder(unittest.TestCase):
    """Verify P2 deterministic 8 MiB / 16 MiB / 44.5 MiB VFAT image builder & BPB auditor."""

    def test_8mib_and_16mib_and_44_5mib_vfat_images(self) -> None:
        expected_modes = {
            "8m_ram": (8 * 1024 * 1024, "FAT16"),
            "16m_log": (16 * 1024 * 1024, "FAT16"),
            "44.5m_log": (91136 * SECTOR_SIZE, "FAT16"),
            "44.5m_fat32": (91136 * SECTOR_SIZE, "FAT32"),
        }

        for mode, (exp_bytes, exp_fat) in expected_modes.items():
            img1, rec1 = build_opelog_vfat_image(mode=mode)
            img2, rec2 = build_opelog_vfat_image(mode=mode)

            self.assertEqual(rec1.sha256, rec2.sha256)
            self.assertEqual(img1, img2)
            self.assertEqual(len(img1), exp_bytes)
            self.assertEqual(rec1.fat_type, exp_fat)

            audit = verify_vfat_image(img1, require_opelog_dirs=True)
            self.assertTrue(audit.valid, audit.errors)
            self.assertEqual(audit.fat_type, exp_fat)
            self.assertEqual(audit.bytes_per_sector, 512)
            self.assertEqual(audit.num_fats, 2)
            self.assertTrue(audit.fats_identical)
            self.assertEqual(audit.discovered_dirs, ("/OPE", "/OPE/00", "/OPE/01"))

    def test_vfat_auditor_detects_bpb_fat_and_directory_corruptions(self) -> None:
        good_img, rec = build_opelog_vfat_image(mode="8m_ram")

        bad_sig = bytearray(good_img)
        bad_sig[510:512] = b"\x00\x00"
        self.assertFalse(verify_vfat_image(bytes(bad_sig)).valid)

        bad_fat2 = bytearray(good_img)
        fat2_off = (rec.reserved_sectors + rec.sectors_per_fat) * SECTOR_SIZE
        bad_fat2[fat2_off + 4] ^= 0xFF
        aud_fat2 = verify_vfat_image(bytes(bad_fat2))
        self.assertFalse(aud_fat2.valid)
        self.assertFalse(aud_fat2.fats_identical)

        bad_dir = bytearray(good_img)
        first_data_sec = rec.reserved_sectors + rec.num_fats * rec.sectors_per_fat + 32
        ope_clus_off = first_data_sec * SECTOR_SIZE
        bad_dir[ope_clus_off + 96] = 0xE5
        aud_dir = verify_vfat_image(bytes(bad_dir), require_opelog_dirs=True)
        self.assertFalse(aud_dir.valid)
        self.assertTrue(any("/OPE/01" in e for e in aud_dir.errors))

    def test_p2_idempotent_loopback_snippet(self) -> None:
        snippet = generate_p2_opelog_mount_snippet()
        self.assertIn('busybox losetup -d "/dev/loop7"', snippet)
        self.assertIn('ln -s "/dev/loop7" /dev/nflasha21', snippet)
        self.assertIn('mkdir -p "/etc/opelog/ope/00" "/etc/opelog/ope/01"', snippet)


class TestP3P4P8P9AndFanUnicornVerification(unittest.TestCase):
    """Verify P3, P4, P8, P9 (`upm.ko`), and Fan (`libfan.so`) patching, rollback & Unicorn execution."""

    def test_p3_remoteboard_patch_rollback_and_unicorn_execution(self) -> None:
        raw = (DEFAULT_FX6_DONOR_LIB_DIR / "libInfraAppRemoteBoard.so").read_bytes()
        patched, p_rec = apply_patch_spec(raw, P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC)
        self.assertEqual(p_rec.changed_byte_count, 16)

        exec_summary = run_p3_remoteboard_unicorn_check(patched)
        self.assertEqual(exec_summary.exec_rcv_msg_ret, 0)
        self.assertEqual(exec_summary.main_thread_ret, 0)
        self.assertEqual(exec_summary.instructions_executed, 4)

        restored, rb_rec = rollback_patch_spec(patched, P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC)
        self.assertTrue(rb_rec.donor_sha256_matched)
        self.assertEqual(restored, raw)

    def test_p4_p8_and_combined_appfw_unicorn_verification(self) -> None:
        appfw_raw = (DEFAULT_FX6_DONOR_LIB_DIR / "appFw.so").read_bytes()

        u_mode, u_val = run_p4_nd_unicorn_sweep(appfw_raw, patched_label=False)
        self.assertEqual(u_mode.assert_hit_count, 300)
        self.assertEqual(u_val.assert_hit_count, 312)

        # Standalone P4, P8, P1+P4, and combined P1+P4+P8 specs all round-trip 100%
        for spec, exp_bytes in (
            (P4_APPFW_ONLY_SPEC, 8),
            (P8_APPFW_ONLY_SPEC, 8),
            (P1_AND_P4_APPFW_COMBINED_SPEC, 9),
            (P1_P4_P8_APPFW_COMBINED_SPEC, 17),
        ):
            adapted, rec = apply_patch_spec(appfw_raw, spec)
            self.assertEqual(rec.changed_byte_count, exp_bytes)
            restored, rb = rollback_patch_spec(adapted, spec)
            self.assertTrue(rb.donor_sha256_matched)
            self.assertEqual(restored, appfw_raw)

        appfw_full, _ = apply_patch_spec(appfw_raw, P1_P4_P8_APPFW_COMBINED_SPEC)
        p_mode, p_val = run_p4_nd_unicorn_sweep(appfw_full, patched_label=True)
        self.assertEqual(p_mode.clear_output_count, 576)
        self.assertEqual(p_mode.assert_hit_count, 0)
        self.assertEqual(p_val.clear_output_count, 576)
        self.assertEqual(p_val.assert_hit_count, 0)

        p8_res = run_p8_appfw_unicorn_check(appfw_full)
        self.assertEqual(p8_res.return_value, 0)
        self.assertEqual(p8_res.instructions_executed, 2)
        self.assertTrue(p8_res.sp_preserved)

    def test_p9_upm_ko_relocatable_patch_rollback_and_unicorn_guard(self) -> None:
        upm_raw = (DEFAULT_FX3_MODULES_DIR / "upm.ko").read_bytes()
        upm_patched, rec = apply_patch_spec(upm_raw, P9_UPM_KO_SPEC)
        self.assertEqual(rec.changed_byte_count, 4)
        self.assertEqual(rec.resolutions[0].file_offset, 0x13720)
        self.assertEqual(rec.resolutions[0].section_name, ".text")

        p9_res = run_p9_upm_ko_unicorn_check(upm_raw, upm_patched)
        self.assertTrue(p9_res.unpatched_null_callback_faulted)
        self.assertTrue(p9_res.patched_completed_cleanly)
        self.assertEqual(p9_res.patched_return_value, 0)

        restored, rb = rollback_patch_spec(upm_patched, P9_UPM_KO_SPEC)
        self.assertTrue(rb.donor_sha256_matched)
        self.assertEqual(restored, upm_raw)

    def test_fan_libfan_patch_rollback_and_unicorn_return_one(self) -> None:
        fan_raw = (DEFAULT_FX6_DONOR_LIB_DIR / "libfan.so").read_bytes()
        fan_patched, rec = apply_patch_spec(fan_raw, FAN_LIBFAN_SPEC)
        self.assertEqual(rec.changed_byte_count, 8)
        self.assertEqual(rec.resolutions[0].file_offset, 0x1DEC)

        fan_res = run_fan_libfan_unicorn_check(fan_patched)
        self.assertEqual(fan_res.return_value, 1)
        self.assertEqual(fan_res.instructions_executed, 2)
        self.assertTrue(fan_res.sp_preserved)

        restored, rb = rollback_patch_spec(fan_patched, FAN_LIBFAN_SPEC)
        self.assertTrue(rb.donor_sha256_matched)
        self.assertEqual(restored, fan_raw)
        self.assertEqual(len(ALL_PHASE2_TARGET_SPECS), 7)


class TestTier0ReadOnlyBackupWorkerAndCandidateDryRun(unittest.TestCase):
    """Verify Tier-0 backup worker in Unicorn AND full 12-Gate offline candidate dry-run."""

    compiled_worker: CompiledWorkerArtifact

    @classmethod
    def setUpClass(cls) -> None:
        cls.compiled_worker = compile_tier0_worker_shared_object()

    def test_freestanding_shared_object_has_zero_external_imports(self) -> None:
        self.assertEqual(self.compiled_worker.undefined_imports, ())
        self.assertIn("tier0_backup_worker_run", self.compiled_worker.exported_symbols)
        self.assertIn("tier0_backup_worker_init", self.compiled_worker.exported_symbols)

    def test_positive_11_item_twopass_manifest_and_syscall_redlines(self) -> None:
        res = run_tier0_worker_in_unicorn(
            compiled_worker=self.compiled_worker,
            invoke_reentrant_second_call=True,
        )
        self.assertEqual(res.return_code, WORKER_OK)
        self.assertEqual(res.reentrant_second_return_code, ERR_REENTRANT_LOCK)
        self.assertTrue(res.libjit_unlinked)
        self.assertTrue(res.manifest_created)
        assert res.manifest_audit is not None
        self.assertTrue(res.manifest_audit.valid, res.manifest_audit.errors)
        self.assertEqual(len(res.manifest_audit.verified_items), len(TIER0_REQUIRED_BACKUPS))

        self.assertTrue(res.syscall_audit.valid, res.syscall_audit.errors)
        self.assertTrue(res.syscall_audit.first_path_op_unlink_libjit)
        self.assertEqual(res.syscall_audit.dev_write_open_count, 0)
        self.assertEqual(res.syscall_audit.source_fd_write_count, 0)

        assert res.manifest_json is not None
        manifest_items = res.manifest_json["items"]
        assert isinstance(manifest_items, dict)
        for key, src_meta in TIER0_CANONICAL_SOURCES.items():
            out_path = f"/mnt/fx3_tier0_backup/{src_meta['output_name']}"
            out_rec = res.written_outputs[out_path]
            expected_sha = res.source_expected_sha256[key]
            self.assertEqual(out_rec.sha256, expected_sha)
            self.assertEqual(manifest_items[key]["pass1_sha256"], expected_sha)
            self.assertEqual(manifest_items[key]["pass2_sha256"], expected_sha)

    def test_tier0_worker_anomaly_detection_paths(self) -> None:
        res_flip = run_tier0_worker_in_unicorn(
            compiled_worker=self.compiled_worker,
            pass2_bitflip_item="boot0",
            pass2_bitflip_offset=65540,
        )
        self.assertEqual(res_flip.return_code, ERR_TWOPASS_SHA256_MISMATCH)
        self.assertFalse(res_flip.manifest_created)

        res_s0 = run_tier0_worker_in_unicorn(
            compiled_worker=self.compiled_worker,
            corrupt_sector0_magic=True,
        )
        self.assertEqual(res_s0.return_code, ERR_SECTOR0_MAGIC)
        self.assertEqual(len(res_s0.written_outputs), 0)

        res_bk4 = run_tier0_worker_in_unicorn(
            compiled_worker=self.compiled_worker,
            corrupt_bk4_magic=True,
        )
        self.assertEqual(res_bk4.return_code, ERR_BK4_MAGIC)
        self.assertFalse(res_bk4.manifest_created)

        res_sym = run_tier0_worker_in_unicorn(
            compiled_worker=self.compiled_worker,
            boot1_size_override=262144,
        )
        self.assertEqual(res_sym.return_code, ERR_BOOT_SYMMETRY)
        self.assertFalse(res_sym.manifest_created)

        res_excl = run_tier0_worker_in_unicorn(
            compiled_worker=self.compiled_worker,
            preexisting_output_file="/mnt/fx3_tier0_backup/sector0.bin",
        )
        self.assertEqual(res_excl.return_code, ERR_DST_OPEN_EXCL_FAILED)
        self.assertFalse(res_excl.manifest_created)

    def test_end_to_end_candidate_dry_run_12_gates_pass_and_tamper_blocks(self) -> None:
        # 1. Valid candidate dry-run: all 7 targets + 8 MiB VFAT + Tier-0 manifest -> 12/12 gates green
        rep_ok = run_offline_candidate_dry_run(compiled_worker=self.compiled_worker)
        self.assertTrue(rep_ok.candidate_ready)
        self.assertTrue(rep_ok.all_12_gates_verified)
        self.assertEqual(rep_ok.verified_gate_count, 12)
        self.assertEqual(rep_ok.blocked_gate_ids, ())
        self.assertTrue(rep_ok.temp_dir_cleaned)
        self.assertEqual(len(rep_ok.patch_receipts), 7)
        self.assertEqual(rep_ok.vfat_receipt.total_bytes, 8 * 1024 * 1024)
        self.assertTrue(rep_ok.vfat_audit.valid)
        self.assertEqual(rep_ok.fan_unicorn.return_value, 1)
        self.assertEqual(rep_ok.p8_unicorn.return_value, 0)
        self.assertTrue(rep_ok.p9_unicorn.patched_completed_cleanly)
        self.assertFalse(rep_ok.safety_gates_report["persistent_write_release"])

        # 2. Missing Tier-0 item -> immediately blocks G10, G11, and G12
        tier0_base = run_tier0_worker_in_unicorn(compiled_worker=self.compiled_worker)
        rep_missing = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            missing_manifest_item="p12_cert",
        )
        self.assertFalse(rep_missing.candidate_ready)
        self.assertFalse(rep_missing.all_12_gates_verified)
        self.assertIn("G10_same_body_tier0_full_backup_checkpoint", rep_missing.blocked_gate_ids)
        self.assertIn("G12_persistent_flash_write_authorization", rep_missing.blocked_gate_ids)
        self.assertTrue(rep_missing.temp_dir_cleaned)

        # 3. Injected source write-flag syscall -> blocks G10, G11, and G12
        rep_bad_sc = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            inject_write_flag_syscall=True,
        )
        self.assertFalse(rep_bad_sc.candidate_ready)
        self.assertIn("G10_same_body_tier0_full_backup_checkpoint", rep_bad_sc.blocked_gate_ids)

        # 4. Tampered fail-safe init2 hook -> blocks G11 and G12
        rep_bad_hook = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            tamper_failsafe_hook=True,
        )
        self.assertFalse(rep_bad_hook.candidate_ready)
        self.assertIn("G11_independent_hardware_recovery_readiness", rep_bad_hook.blocked_gate_ids)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_hook.blocked_gate_ids)

        # 5. Corrupted 8 MiB opelog.vfat -> blocks G12 candidate release
        rep_bad_vfat = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            corrupt_opelog_vfat=True,
        )
        self.assertFalse(rep_bad_vfat.candidate_ready)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_vfat.blocked_gate_ids)

    def test_cli_verify_donors_subcommand(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-donors"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["status"], "OK")
        self.assertEqual(parsed["verified_targets"], 7)


if __name__ == "__main__":
    unittest.main()
