"""Comprehensive Unit Test Suite for `outputs/fx6-on-fx3-closure` (Phase 3 P1..P9 9/9 Closure).

Covers:
- ELF64 `ET_DYN` (`PT_LOAD`) & `ET_REL` (`.ko` section) mappers and negative boundary checks
- P1 (4-library equal-length `/dev/nflasha20` -> `/dev/nflasha30` adaptation & 100% SHA-256 rollback)
- P2 (`vfat_builder.py` 8 MiB / 16 MiB / 44.5 MiB VFAT image synthesis & BPB/FAT/directory audits)
- P3, P4, P8, P9 (`upm.ko` `.text+0x136b8`), and Fan (`libfan.so` `0x1dec`) adaptation, rollback & Unicorn checks
- P5 & P6 (`uipc_completion_verifier.py` UIPC 12B completion synthesis & Unicorn `send_and_wait_cmp_i` verification)
- P7 (`backup_bridge_verifier.py` dual-kernel `pcidma_transfer_async` 16B signature, Unicorn trampoline & `op=0x30` DMA contract)
- Tier-0 Read-Only Backup Worker (`tier0_unicorn_verifier.py`) positive & fault-injection runs
- End-to-End Offline Candidate Dry-Run & 12-Gate Safety Evaluator (`candidate_builder.py`) + CLI (`__main__.py`)
"""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import subprocess
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from fx3_safety.preflight import (
    TIER0_CANONICAL_SOURCES,
    TIER0_REQUIRED_BACKUPS,
    verify_failsafe_hook_script,
)

from fx6_closure.__main__ import main as cli_main
from fx6_closure.backup_bridge_verifier import (
    BackupBridgeError,
    FALLBACK_NONZERO_REL_OFFSET,
    FALLBACK_ZERO_REL_OFFSET,
    FX3_PCIDMA_API_VA,
    FX6_PCIDMA_API_VA,
    PINNED_ENTRY16_WORDS,
    SYNC100_DST_QUEUE,
    build_canonical_sync100_op30_envelope,
    build_synthetic_kernel_image_for_base,
    validate_sync100_op30_request,
    verify_kernel_pcidma_entry_signature,
    verify_p7_backup_bridge,
)
from fx6_closure.backup_mount_tolerance_verifier import (
    FX6_DUAL_SLOT_MEDIA_IDS,
    KEY_DUAL_SLOT_MEDIA_SHADOW,
    KEY_FA0080_BOOT_DESC,
    KEY_FIXED_AREA_SIZE,
    KEY_FIXED_AREA_TOP,
    KIKILOG_PINNED_INSNS,
    SETUPFILE_PINNED_INSNS,
    audit_cross_model_backup_contracts,
    audit_ram_shadow_bk4,
    audit_storage_mount_tolerance,
    build_canonical_fa0080_normal_boot_table,
    read_bk4_property_bytes,
    run_backup_mount_tolerance_verification,
    synthesize_ram_shadow_bk4,
)
from fx6_closure.candidate_builder import COMPLETE_MATRIX_ITEMS, run_offline_candidate_dry_run
from fx6_closure.feature_routing_verifier import (
    CORE_CAMERA_FEATURE_LIBRARIES,
    FX3_P30_TOTAL_BYTES,
    MEDIA_ID_SLOT_A,
    MEDIA_ID_SLOT_B,
    MEDIA_ID_UNINITIALIZED,
    audit_core_elf_symbol_closure,
    generate_sony_cube_3d_lut,
    run_feature_routing_verification,
    validate_sony_cube_3d_lut,
    verify_cine_ei_af_and_dual_slot_contracts,
    verify_p30_lut_capacity_budget,
    verify_setupfile_lut_mount_chain,
)
from fx6_closure.ram_overlay_packager import (
    CPIO_NEWC_MAGIC,
    CpioEntrySpec,
    CpioFormatError,
    REQUIRED_STAGE_A_OVERLAY_PATHS,
    S_IFDIR,
    S_IFREG,
    build_cpio_newc_archive,
    build_stage_a_ram_overlay_package,
    parse_and_audit_cpio_newc,
)
from fx6_closure.rollback_drill import (
    SIMULATED_EMMC_PARTITIONS,
    run_four_layer_rollback_drill,
    simulate_failsafe_state_machine,
)
from fx6_closure.uipc_completion_verifier import (
    P5_CANONICAL_CMP_HEX,
    P5_CANONICAL_REQ_HEX,
    UIPC_BB_TARGET_QUEUE,
    UIPC_P5_P6_RULES,
    UipcProtocolError,
    run_p5_p6_uipc_unicorn_audit,
    synthesize_uipc_completion,
)
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
        # 1. Valid candidate dry-run: full P1..P9 (9/9) + Fan + 8 MiB VFAT + Tier-0 -> 12/12 gates green
        rep_ok = run_offline_candidate_dry_run(compiled_worker=self.compiled_worker)
        self.assertTrue(rep_ok.candidate_ready)
        self.assertTrue(rep_ok.all_12_gates_verified)
        self.assertEqual(rep_ok.verified_gate_count, 12)
        self.assertEqual(rep_ok.blocked_gate_ids, ())
        self.assertEqual(rep_ok.verified_matrix_items, COMPLETE_MATRIX_ITEMS)
        self.assertTrue(rep_ok.temp_dir_cleaned)
        self.assertEqual(len(rep_ok.patch_receipts), 7)
        self.assertEqual(rep_ok.vfat_receipt.total_bytes, 8 * 1024 * 1024)
        self.assertTrue(rep_ok.vfat_audit.valid)
        self.assertTrue(rep_ok.p5_p6_uipc_unicorn.all_positive_passed)
        self.assertTrue(rep_ok.p5_p6_uipc_unicorn.all_negative_captured)
        self.assertTrue(rep_ok.p7_backup_bridge.all_checks_passed)
        self.assertEqual(rep_ok.fan_unicorn.return_value, 1)
        self.assertEqual(rep_ok.p8_unicorn.return_value, 0)
        self.assertTrue(rep_ok.p9_unicorn.patched_completed_cleanly)
        self.assertTrue(rep_ok.stage_a_cpio_audit.valid)
        self.assertTrue(rep_ok.rollback_drill.all_scenarios_passed)
        self.assertEqual(rep_ok.rollback_drill.total_emmc_writes, 0)
        self.assertTrue(rep_ok.feature_routing_audit.all_checks_passed)
        self.assertTrue(rep_ok.backup_mount_tolerance_ok)
        self.assertTrue(rep_ok.backup_mount_tolerance_audit.dimension_a_mount_tolerance.u4_closed)
        self.assertFalse(rep_ok.safety_gates_report["persistent_write_release"])

        drill_base = rep_ok.rollback_drill
        feat_base = rep_ok.feature_routing_audit
        bmt_base = rep_ok.backup_mount_tolerance_audit

        # 2. Missing Tier-0 item -> immediately blocks G10, G11, and G12
        tier0_base = run_tier0_worker_in_unicorn(compiled_worker=self.compiled_worker)
        rep_missing = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
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
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            inject_write_flag_syscall=True,
        )
        self.assertFalse(rep_bad_sc.candidate_ready)
        self.assertIn("G10_same_body_tier0_full_backup_checkpoint", rep_bad_sc.blocked_gate_ids)

        # 4. Tampered fail-safe init2 hook -> blocks G11 and G12
        rep_bad_hook = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            tamper_failsafe_hook=True,
        )
        self.assertFalse(rep_bad_hook.candidate_ready)
        self.assertIn("G11_independent_hardware_recovery_readiness", rep_bad_hook.blocked_gate_ids)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_hook.blocked_gate_ids)

        # 5. Corrupted 8 MiB opelog.vfat -> blocks G12 candidate release
        rep_bad_vfat = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            corrupt_opelog_vfat=True,
        )
        self.assertFalse(rep_bad_vfat.candidate_ready)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_vfat.blocked_gate_ids)

        # 6. Corrupted P5/P6 UIPC, P7 Backup Sync100 bridge, Stage-A CPIO, 5-Feature Routing, or U4/BK4 -> blocks G12
        rep_bad_uipc = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            corrupt_p5_p6_uipc=True,
        )
        self.assertFalse(rep_bad_uipc.candidate_ready)
        self.assertNotIn("P5", rep_bad_uipc.verified_matrix_items)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_uipc.blocked_gate_ids)

        rep_bad_p7 = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            corrupt_p7_backup_bridge=True,
        )
        self.assertFalse(rep_bad_p7.candidate_ready)
        self.assertNotIn("P7", rep_bad_p7.verified_matrix_items)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_p7.blocked_gate_ids)

        rep_bad_cpio = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            corrupt_stage_a_cpio=True,
        )
        self.assertFalse(rep_bad_cpio.candidate_ready)
        self.assertFalse(rep_bad_cpio.stage_a_cpio_audit.valid)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_cpio.blocked_gate_ids)

        rep_bad_feat = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            corrupt_feature_routing=True,
        )
        self.assertFalse(rep_bad_feat.candidate_ready)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_feat.blocked_gate_ids)

        rep_bad_bmt = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            corrupt_backup_mount_tolerance=True,
        )
        self.assertFalse(rep_bad_bmt.candidate_ready)
        self.assertFalse(rep_bad_bmt.backup_mount_tolerance_ok)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_bmt.blocked_gate_ids)

    def test_cli_verify_donors_and_rollback_drill_subcommands(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-donors"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["status"], "OK")
        self.assertEqual(parsed["verified_targets"], 7)
        self.assertTrue(parsed["p7_dual_kernel_signature_verified"])

        buf_drill = io.StringIO()
        with redirect_stdout(buf_drill):
            rc_drill = cli_main(["run-rollback-drill"])
        self.assertEqual(rc_drill, 0)
        parsed_drill = json.loads(buf_drill.getvalue())
        self.assertEqual(parsed_drill["status"], "OK")
        self.assertEqual(parsed_drill["matrix_item_count"], 10)
        self.assertTrue(parsed_drill["failsafe_hook_audit"]["valid"])
        self.assertTrue(parsed_drill["rollback_drill"]["all_scenarios_passed"])
        self.assertEqual(parsed_drill["rollback_drill"]["total_emmc_writes"], 0)


class TestP5P6UipcCompletionAndUnicorn(unittest.TestCase):
    """Verify P5 & P6 UIPC completion synthesis and Unicorn `send_and_wait_cmp_i` execution."""

    def test_p5_and_p6_exact_byte_codec_and_schema_rejections(self) -> None:
        p5_cmp = synthesize_uipc_completion(UIPC_BB_TARGET_QUEUE, bytes.fromhex(P5_CANONICAL_REQ_HEX))
        self.assertEqual(p5_cmp.hex(), P5_CANONICAL_CMP_HEX)

        for opcode, rule in UIPC_P5_P6_RULES.items():
            pkt = synthesize_uipc_completion(UIPC_BB_TARGET_QUEUE, bytes.fromhex(rule.canonical_request_hex))
            self.assertEqual(len(pkt), 12)
            self.assertEqual(pkt.hex(), rule.canonical_completion_hex)

        # Wrong queue, wrong magic, wrong length, or unknown opcode must raise UipcProtocolError
        with self.assertRaises(UipcProtocolError):
            synthesize_uipc_completion(0x9058003F, bytes.fromhex(P5_CANONICAL_REQ_HEX))
        with self.assertRaises(UipcProtocolError):
            synthesize_uipc_completion(UIPC_BB_TARGET_QUEUE, bytes.fromhex("0e202d030a0001800000"))
        with self.assertRaises(UipcProtocolError):
            synthesize_uipc_completion(UIPC_BB_TARGET_QUEUE, bytes.fromhex("0d202d030c0001800000"))
        with self.assertRaises(UipcProtocolError):
            synthesize_uipc_completion(UIPC_BB_TARGET_QUEUE, bytes.fromhex("0d2099090a0001800000"))

    def test_send_and_wait_cmp_i_unicorn_zero_asserts_and_fault_capture(self) -> None:
        appfw_raw = (DEFAULT_FX6_DONOR_LIB_DIR / "appFw.so").read_bytes()
        summary = run_p5_p6_uipc_unicorn_audit(appfw_raw)
        self.assertTrue(summary.all_positive_passed)
        self.assertTrue(summary.all_negative_captured)
        self.assertEqual(len(summary.positive_direct_cases), 5)
        self.assertEqual(len(summary.positive_wrapper_cases), 5)

        for case in summary.positive_direct_cases:
            self.assertTrue(case.completed_normally)
            self.assertFalse(case.hit_assert_1075_vma)
            self.assertFalse(case.assert_hit)
            self.assertEqual(case.osal_alloc_count, 2)
            self.assertEqual(case.osal_free_count, 2)

        for wcase in summary.positive_wrapper_cases:
            self.assertEqual(wcase.mapped_ap_status, 0)
            self.assertFalse(wcase.status_error_branch_hit)

        # Negative assertions: osal_snd_msg != 0 & strict bad status jump to 0x20ef7b4 (line 1075)
        self.assertTrue(summary.snd_error_case.hit_assert_1075_vma)
        self.assertTrue(summary.snd_error_case.assert_hit)
        self.assertEqual(summary.snd_error_case.assert_line, 1075)

        self.assertTrue(summary.strict_bad_status_case.hit_assert_1075_vma)
        self.assertEqual(summary.strict_bad_status_case.assert_line, 1075)

        # Raw -1 completion status jumps to 0x20ede04 error branch and maps to 0x6f
        self.assertTrue(summary.raw_bad_status_wrapper_case.status_error_branch_hit)
        self.assertEqual(summary.raw_bad_status_wrapper_case.mapped_ap_status, 0x6F)


class TestP7BackupSync100BridgeVerifier(unittest.TestCase):
    """Verify P7 dual-kernel `pcidma_transfer_async` signature, Unicorn trampoline & Sync100 contract."""

    def test_p7_dual_kernel_signature_trampoline_and_dma_contract(self) -> None:
        rep = verify_p7_backup_bridge()
        self.assertTrue(rep.all_checks_passed)
        self.assertTrue(rep.dual_kernel_first32_identical)
        self.assertEqual(rep.fx6_live_kernel_audit.entry16_words, PINNED_ENTRY16_WORDS)
        self.assertEqual(rep.fx3_pinned_kernel_audit.entry16_words, PINNED_ENTRY16_WORDS)
        self.assertEqual(
            rep.fx6_live_kernel_audit.fallback_zero_va,
            FX6_PCIDMA_API_VA + FALLBACK_ZERO_REL_OFFSET,
        )
        self.assertEqual(
            rep.fx6_live_kernel_audit.fallback_nonzero_va,
            FX6_PCIDMA_API_VA + FALLBACK_NONZERO_REL_OFFSET,
        )
        self.assertEqual(
            rep.fx3_pinned_kernel_audit.fallback_zero_va,
            FX3_PCIDMA_API_VA + FALLBACK_ZERO_REL_OFFSET,
        )
        self.assertEqual(
            rep.fx3_pinned_kernel_audit.fallback_nonzero_va,
            FX3_PCIDMA_API_VA + FALLBACK_NONZERO_REL_OFFSET,
        )
        self.assertEqual(rep.transaction_audit.callback_invocations, 1)
        self.assertEqual(rep.transaction_audit.callback_args, ((0, 0),))
        self.assertTrue(rep.libbackup_sha256_matched)
        self.assertTrue(rep.chaplin_four_ids_verified)

    def test_p7_rejects_tampered_kernel_prologue_or_invalid_op30_envelope(self) -> None:
        import struct as _st

        valid_first32 = _st.pack("<IIII", *PINNED_ENTRY16_WORDS) + (b"\x00" * 16)
        good_img = build_synthetic_kernel_image_for_base(FX3_PCIDMA_API_VA, valid_first32)
        audit = verify_kernel_pcidma_entry_signature(good_img, FX3_PCIDMA_API_VA)
        self.assertTrue(audit.hook_restore_verified)

        # Tamper word 0 of prologue -> must reject
        bad_first32 = _st.pack("<IIII", 0xD503201F, *PINNED_ENTRY16_WORDS[1:]) + (b"\x00" * 16)
        bad_img = build_synthetic_kernel_image_for_base(FX3_PCIDMA_API_VA, bad_first32)
        with self.assertRaises(BackupBridgeError):
            verify_kernel_pcidma_entry_signature(bad_img, FX3_PCIDMA_API_VA)

        # Unknown base VA -> must reject
        with self.assertRaises(BackupBridgeError):
            verify_kernel_pcidma_entry_signature(good_img, 0xFFFFFF8008322100)

        # Valid vs tampered 40B op=0x30 envelope
        env = build_canonical_sync100_op30_envelope(origin_q=0x803E090B, mode=3)
        q, mode = validate_sync100_op30_request(SYNC100_DST_QUEUE, env)
        self.assertEqual((q, mode), (0x803E090B, 3))

        bad_tail = env[:-4] + b"\x00\x00\x00\x00"
        with self.assertRaises(BackupBridgeError):
            validate_sync100_op30_request(SYNC100_DST_QUEUE, bad_tail)


class TestStageARamOverlayPackager(unittest.TestCase):
    """Verify deterministic CPIO `newc` (`070701`) builder, parser/auditor, and Stage-A bundle."""

    def test_stage_a_cpio_reproducibility_alignment_and_manifest_contract(self) -> None:
        b1 = build_stage_a_ram_overlay_package()
        b2 = build_stage_a_ram_overlay_package()
        self.assertEqual(b1.cpio_sha256, b2.cpio_sha256)
        self.assertEqual(b1.cpio_bytes, b2.cpio_bytes)
        self.assertEqual(b1.cpio_size % 4, 0)
        self.assertEqual(b1.cpio_bytes[:6], CPIO_NEWC_MAGIC)
        self.assertTrue(b1.temp_dir_cleaned)
        self.assertTrue(b1.cpio_audit.valid, b1.cpio_audit.errors)
        self.assertTrue(b1.cpio_audit.trailer_found)
        self.assertTrue(b1.failsafe_hook_audit.valid, b1.failsafe_hook_audit.errors)

        # Independently verify init2_guard.sh via fx3_safety.preflight.verify_failsafe_hook_script
        ext_hook_audit = verify_failsafe_hook_script(b1.init2_guard_script)
        self.assertTrue(ext_hook_audit.valid, ext_hook_audit.errors)

        # Verify all 10 matrix items and 10 runtime SHA-256 checklist entries in overlay_manifest.json
        manifest = b1.overlay_manifest
        self.assertEqual(manifest["persistent_flash_writes"], 0)
        self.assertEqual(manifest["matrix_item_count"], 10)
        self.assertEqual(tuple(manifest["verified_matrix_ids"]), COMPLETE_MATRIX_ITEMS)
        self.assertEqual(len(manifest["sha256_check_list"]), 10)
        self.assertEqual(len(b1.staged_runtime_blobs), 10)

        # Verify required paths in CPIO
        entry_names = tuple(e.name for e in b1.cpio_audit.entries)
        for req in REQUIRED_STAGE_A_OVERLAY_PATHS:
            self.assertIn(req, entry_names)

    def test_cpio_newc_rejects_bad_magic_padding_traversal_and_missing_trailer(self) -> None:
        with self.assertRaises(CpioFormatError):
            build_cpio_newc_archive([CpioEntrySpec(name="/etc/passwd", mode=S_IFREG | 0o644, data=b"x")])
        with self.assertRaises(CpioFormatError):
            build_cpio_newc_archive([CpioEntrySpec(name="etc/../evil", mode=S_IFREG | 0o644, data=b"x")])
        with self.assertRaises(CpioFormatError):
            build_cpio_newc_archive([CpioEntrySpec(name="etc", mode=S_IFDIR | 0o755, data=b"not_empty")])
        with self.assertRaises(CpioFormatError):
            build_cpio_newc_archive(
                [
                    CpioEntrySpec(name="etc/a", mode=S_IFREG | 0o644, data=b"1"),
                    CpioEntrySpec(name="etc/a", mode=S_IFREG | 0o644, data=b"2"),
                ]
            )

        valid_arc = build_cpio_newc_archive(
            [
                CpioEntrySpec(name="etc", mode=S_IFDIR | 0o755),
                CpioEntrySpec(name="etc/hello.txt", mode=S_IFREG | 0o644, data=b"abc"),  # 3B -> 1B pad
            ]
        )
        ok_audit = parse_and_audit_cpio_newc(valid_arc, required_paths=("etc", "etc/hello.txt"))
        self.assertTrue(ok_audit.valid, ok_audit.errors)

        # Corrupt magic (`070707` odc instead of `070701` newc)
        bad_magic = b"070707" + valid_arc[6:]
        self.assertFalse(parse_and_audit_cpio_newc(bad_magic).valid)

        # Corrupt 1-byte payload alignment pad on 3-byte file `etc/hello.txt`
        # Entry 0 (`etc`): 110 + 4 = 114 -> +2 pad = 116 bytes.
        # Entry 1 (`etc/hello.txt`): 110 + 14 = 124 -> +0 head_pad, 3B data -> 1B data_pad at 116+124+3 = 243.
        bad_pad = bytearray(valid_arc)
        bad_pad[243] = 0xFF
        pad_audit = parse_and_audit_cpio_newc(bytes(bad_pad))
        self.assertFalse(pad_audit.valid)
        self.assertTrue(any("alignment padding" in err for err in pad_audit.errors))

        # Strip TRAILER!!! sentinel (last 124 bytes)
        no_trailer = valid_arc[:-124]
        tr_audit = parse_and_audit_cpio_newc(no_trailer)
        self.assertFalse(tr_audit.valid)
        self.assertFalse(tr_audit.trailer_found)


class TestFourLayerRollbackDrill(unittest.TestCase):
    """Verify deterministic 4-Layer Fail-Safe state machine and sandboxed POSIX `sh` drills."""

    def test_formal_state_machine_and_all_four_sandboxed_sh_scenarios(self) -> None:
        # 1. Direct state-machine branch assertions
        sm1 = simulate_failsafe_state_machine(arm_once_present=False)
        self.assertEqual(sm1.boot_branch, "STOCK_FX3")
        self.assertEqual(sm1.active_overlay_mounts, 0)

        sm2 = simulate_failsafe_state_machine(arm_once_present=True)
        self.assertEqual(sm2.boot_branch, "ADAPTED_FX6_OVERLAY")
        self.assertFalse(sm2.token_present_after)
        self.assertEqual(sm2.active_overlay_mounts, 3)

        sm3 = simulate_failsafe_state_machine(arm_once_present=True, manifest_sha256_valid=False)
        self.assertEqual(sm3.boot_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sm3.active_overlay_mounts, 0)

        sm4 = simulate_failsafe_state_machine(arm_once_present=True, child_timed_out=True)
        self.assertEqual(sm4.boot_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sm4.diag_code_prefix, "ERR_WATCHDOG_TIMEOUT_FALLBACK")

        # 2. Full 4-scenario POSIX `/bin/sh` sandbox execution
        bundle = build_stage_a_ram_overlay_package()
        rep = run_four_layer_rollback_drill(overlay_bundle=bundle)
        self.assertTrue(rep.all_scenarios_passed)
        self.assertEqual(rep.scenario_count, 4)
        self.assertEqual(rep.total_emmc_writes, 0)
        self.assertEqual(rep.total_sandbox_violations, 0)
        self.assertEqual(rep.emmc_partitions_verified, SIMULATED_EMMC_PARTITIONS)
        self.assertTrue(rep.temp_dir_cleaned)

        s1, s2, s3, s4 = rep.scenarios
        self.assertEqual(s1.runs[0].boot_branch, "STOCK_FX3")
        self.assertEqual(s1.runs[0].active_overlay_mount_count, 0)

        self.assertEqual(s2.runs[0].boot_branch, "ADAPTED_FX6_OVERLAY")
        self.assertTrue(s2.runs[0].token_cleared_before_exec)
        self.assertTrue(s2.runs[0].child_observed_token_absent)
        self.assertEqual(s2.runs[1].boot_branch, "STOCK_FX3")
        self.assertEqual(s2.runs[1].active_overlay_mount_count, 0)

        self.assertTrue(s3.runs[0].diag_code.startswith("ERR_MANIFEST_SHA256_MISMATCH:"))
        self.assertTrue(s3.runs[1].diag_code.startswith("ERR_MANIFEST_COMPONENT_MISSING:"))
        self.assertEqual(s3.runs[0].active_overlay_mount_count, 0)
        self.assertEqual(s3.runs[1].active_overlay_mount_count, 0)

        self.assertEqual(s4.runs[0].diag_code, "ERR_CHILD_NONZERO_FALLBACK:139")
        self.assertEqual(s4.runs[1].diag_code, "ERR_WATCHDOG_TIMEOUT_FALLBACK")
        self.assertEqual(s4.runs[0].active_overlay_mount_count, 0)
        self.assertEqual(s4.runs[1].active_overlay_mount_count, 0)

        # 3. Verify host-OS safety lock refuses execution if PREFIX is empty on macOS/host
        with tempfile.TemporaryDirectory(prefix="fx6_host_guard_test_") as tmp_dir:
            guard_p = Path(tmp_dir) / "init2_guard.sh"
            guard_p.write_text(bundle.init2_guard_script, encoding="utf-8")
            proc = subprocess.run(
                ["/bin/sh", str(guard_p)],
                env={"PATH": "/usr/bin:/bin"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 97)
            self.assertIn("ERR_SANDBOX_PREFIX_REQUIRED_ON_HOST", proc.stderr)


class TestPhase5CoreFeatureRoutingVerifier(unittest.TestCase):
    """Verify Phase 5 Blueprint §3 5-Feature Routing & Cross-Model ELF Dynamic Symbol Closure."""

    def test_dimension_a_elf64_dt_needed_and_dynsym_symbol_closure(self) -> None:
        rep = audit_core_elf_symbol_closure()
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.core_library_count, 10)
        self.assertEqual(tuple(a.library_name for a in rep.libraries), CORE_CAMERA_FEATURE_LIBRARIES)
        self.assertEqual(rep.transitive_closure_count, 43)
        self.assertEqual(rep.missing_transitive_needed, ())
        self.assertEqual(rep.strict_zero_unresolved_lib_count, 8)
        self.assertGreater(rep.total_core_exports, 10000)
        self.assertTrue(rep.required_imports_verified)
        self.assertEqual(len(rep.key_symbols), 19)
        for kv in rep.key_symbols:
            self.assertTrue(kv.verified, f"Unverified key symbol: {kv}")
            self.assertEqual(kv.actual_vma, kv.expected_vma)
            self.assertIsNotNone(kv.file_offset)

        # Negative check: omitting initrd base `/lib` leaves libc/libpthread DT_NEEDED unresolved
        with tempfile.TemporaryDirectory(prefix="fx6_empty_initrd_") as empty_dir:
            bad_rep = audit_core_elf_symbol_closure(fx6_initrd_lib_dir=Path(empty_dir))
            self.assertFalse(bad_rep.all_checks_passed)
            self.assertGreater(len(bad_rep.missing_transitive_needed), 0)

    def test_dimension_b_sony_cube_3d_lut_generator_validator_and_p30_budget(self) -> None:
        lut_17 = generate_sony_cube_3d_lut(grid_size=17, title="FX6_SLog3_17", gamma=0.9)
        val_17 = validate_sony_cube_3d_lut(lut_17)
        self.assertTrue(val_17.valid, val_17.errors)
        self.assertEqual(val_17.grid_size, 17)
        self.assertEqual(val_17.actual_triple_count, 17 ** 3)
        self.assertEqual(val_17.title, "FX6_SLog3_17")

        lut_33 = generate_sony_cube_3d_lut(grid_size=33, title="FX6_SLog3_33", gamma=1.1)
        val_33 = validate_sony_cube_3d_lut(lut_33)
        self.assertTrue(val_33.valid, val_33.errors)
        self.assertEqual(val_33.grid_size, 33)
        self.assertEqual(val_33.actual_triple_count, 33 ** 3)

        # Strict negative .cube syntax & domain rejections
        with self.assertRaises(ValueError):
            generate_sony_cube_3d_lut(grid_size=25)
        self.assertFalse(validate_sony_cube_3d_lut("LUT_3D_SIZE 25\n0.0 0.0 0.0\n").valid)
        self.assertFalse(validate_sony_cube_3d_lut("LUT_1D_SIZE 1024\n0.0 0.0 0.0\n").valid)
        self.assertFalse(validate_sony_cube_3d_lut(lut_17.rsplit("\n", 3)[0] + "\n").valid)
        self.assertFalse(
            validate_sony_cube_3d_lut(lut_17.replace("0.000000 0.000000 0.000000", "1.500000 0.0 0.0", 1)).valid
        )
        self.assertFalse(
            validate_sony_cube_3d_lut(
                lut_17.replace("DOMAIN_MIN 0.000000 0.000000 0.000000", "DOMAIN_MIN 1.0 0.0 0.0")
            ).valid
        )
        self.assertFalse(validate_sony_cube_3d_lut(lut_17.replace('TITLE "FX6_SLog3_17"', "TITLE UNQUOTED")).valid)

        # FX3 p30 (48 MiB) VFAT cluster allocation math for 16x 33^3 .cube files
        cap = verify_p30_lut_capacity_budget(max_user_luts=16, cluster_size_bytes=8192)
        self.assertTrue(cap.fits_in_fx3_p30)
        self.assertEqual(cap.partition_bytes, FX3_P30_TOTAL_BYTES)
        self.assertGreater(cap.canonical_free_ratio, 0.65)
        self.assertGreater(cap.worst_case_free_ratio, 0.50)

        # libInfraSetupFile.so SetupFile::RcvThread (0x196c8..0x196e0) /usr/data/lut/ mount chain
        setup_raw = (DEFAULT_FX6_DONOR_LIB_DIR / "libInfraSetupFile.so").read_bytes()
        mnt = verify_setupfile_lut_mount_chain(setup_raw)
        self.assertTrue(mnt.verified)
        self.assertEqual(mnt.rcv_thread_vma, 0x19650)
        self.assertEqual(mnt.mount_plt_vma, 0x144F0)
        self.assertEqual(mnt.fstype_literal, "vfat")
        self.assertEqual(mnt.mount_opts_literal, "posix_attr")
        self.assertEqual(mnt.target_dir_literal, "/usr/data/lut/")
        self.assertEqual(mnt.donor_device_literal, "/dev/nflasha20")
        self.assertEqual(mnt.adapted_device_literal, "/dev/nflasha30")

        # Tampering `bl mount@plt` at 0x196e0 must fail verification
        tampered_setup = bytearray(setup_raw)
        tampered_setup[0x196E0:0x196E4] = b"\x1f\x20\x03\xd5"  # nop
        self.assertFalse(verify_setupfile_lut_mount_chain(bytes(tampered_setup)).verified)

    def test_dimension_c_cine_ei_af_contracts_and_libmpr_dual_slot_unicorn(self) -> None:
        rep_c = verify_cine_ei_af_and_dual_slot_contracts()
        self.assertTrue(rep_c.all_checks_passed)
        self.assertTrue(rep_c.appfw_imports_mpr_set_lut_data)
        self.assertTrue(rep_c.lens_communicator_verified)
        self.assertEqual(len(rep_c.appfw_contracts), 4)
        for c in rep_c.appfw_contracts:
            self.assertTrue(c.verified, f"Failed appFw contract: {c}")

        # Eye-AF Unicorn cases (0 -> 1, 1 -> 0, 2 -> assert)
        e0, e1, e2 = rep_c.eye_af_unicorn_cases
        self.assertFalse(e0.assert_hit)
        self.assertEqual(e0.out_byte_at_offset_8, 1)
        self.assertFalse(e1.assert_hit)
        self.assertEqual(e1.out_byte_at_offset_8, 0)
        self.assertTrue(e2.assert_hit)
        self.assertIn("set_eye_af_mode_i", e2.assert_func or "")

        # Dual-Slot libmpr.so `libXavcMxfGetSlotTypeFromMediaId` (+0x53c850) Unicorn cases
        by_id = {c.media_id: c for c in rep_c.dual_slot_unicorn_cases}
        slot_a = by_id[MEDIA_ID_SLOT_A]
        slot_b = by_id[MEDIA_ID_SLOT_B]
        slot_0 = by_id[MEDIA_ID_UNINITIALIZED]

        self.assertFalse(slot_a.assert_hit)
        self.assertEqual(slot_a.raw_slot_type_enum, 1)
        self.assertEqual(slot_a.slot_index, 0)
        self.assertTrue(slot_a.sp_preserved)

        self.assertFalse(slot_b.assert_hit)
        self.assertEqual(slot_b.raw_slot_type_enum, 2)
        self.assertEqual(slot_b.slot_index, 1)
        self.assertTrue(slot_b.sp_preserved)

        self.assertTrue(slot_0.assert_hit)
        self.assertEqual(slot_0.assert_file, "libXavcMxf.cpp")
        self.assertEqual(slot_0.assert_line, 274)
        self.assertIn("libXavcMxfGetSlotTypeFromMediaId", slot_0.assert_func or "")

    def test_cli_verify_feature_routing_subcommand(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-feature-routing"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "OK")
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["dimension_a_symbol_closure"]["core_library_count"], 10)
        self.assertEqual(payload["dimension_a_symbol_closure"]["transitive_closure_count"], 43)
        self.assertTrue(payload["dimension_b_lut_capacity"]["fits_in_fx3_p30"])
        self.assertTrue(payload["dimension_b_setupfile_mount"]["verified"])
        self.assertTrue(payload["dimension_c_contracts_unicorn"]["all_checks_passed"])


class TestPhase6BackupMountToleranceVerifier(unittest.TestCase):
    """Verify Phase 6 U4 Storage Mount-Tolerance Audit & RAM-Shadow BK4\\0 Schema Synthesizer."""

    def test_dimension_a_u4_storage_mount_tolerance_static_and_unicorn(self) -> None:
        rep_a = audit_storage_mount_tolerance()
        self.assertTrue(rep_a.all_checks_passed)
        self.assertTrue(rep_a.u4_closed)
        self.assertTrue(rep_a.setupfile_sha256_verified)
        self.assertTrue(rep_a.kikilog_sha256_verified)
        self.assertEqual(len(rep_a.setupfile_pinned_insns), len(SETUPFILE_PINNED_INSNS))
        self.assertEqual(len(rep_a.kikilog_pinned_insns), len(KIKILOG_PINNED_INSNS))
        for chk in rep_a.setupfile_pinned_insns + rep_a.kikilog_pinned_insns:
            self.assertTrue(chk.matched, f"Instruction mismatch at {hex(chk.vma)}: {chk}")

        # Verify SetupFile::RcvThread Unicorn cases (mount_rc == 0 vs -1 ENOENT / EINVAL)
        sf_ok, sf_enoent, sf_einval = rep_a.setupfile_unicorn_cases
        self.assertEqual(sf_ok.observed_mount_source, "/dev/nflasha30")
        self.assertEqual(sf_ok.observed_mount_target, "/usr/data/lut/")
        self.assertEqual(sf_ok.observed_mount_flags, 0xC0ED0480)
        self.assertFalse(sf_ok.error_branch_entered)
        self.assertEqual(sf_ok.error_log_calls, 0)
        self.assertTrue(sf_ok.reached_msg_loop)
        self.assertEqual(sf_ok.observed_queue_id, 0x01DE05A5)
        self.assertFalse(sf_ok.abort_or_fault)

        for err_case in (sf_enoent, sf_einval):
            self.assertEqual(err_case.observed_mount_source, "/dev/nflasha20")
            self.assertTrue(err_case.error_branch_entered)
            self.assertEqual(err_case.error_log_calls, 1)
            self.assertEqual(err_case.logged_func_name, "RcvThread")
            self.assertEqual(err_case.logged_line, 304)
            self.assertTrue(err_case.reached_msg_loop)
            self.assertFalse(err_case.abort_or_fault)

        # Verify KikiLogGenerator_init_ope -> KikiLogGenerator_res_ope Unicorn cases
        kl_ok, kl_enoent, kl_einval = rep_a.kikilog_unicorn_cases
        self.assertEqual(kl_ok.observed_mount_source, "/dev/nflasha21")
        self.assertEqual(kl_ok.observed_mount_target, "/etc/opelog/")
        self.assertEqual(kl_ok.observed_mount_flags, 0xC0ED0490)
        self.assertFalse(kl_ok.mount_rc_checked_by_caller)
        self.assertFalse(kl_ok.early_exit_on_logs_mkdir)
        self.assertEqual(
            kl_ok.subdirs_created,
            ("/etc/opelog/logs/000/", "/etc/opelog/logs/001/", "/etc/opelog/logs/002/"),
        )
        self.assertTrue(kl_ok.sp_preserved)
        self.assertFalse(kl_ok.abort_or_fault)

        for err_kl in (kl_enoent, kl_einval):
            self.assertTrue(err_kl.early_exit_on_logs_mkdir)
            self.assertEqual(err_kl.subdirs_created, ())
            self.assertTrue(err_kl.sp_preserved)
            self.assertFalse(err_kl.abort_or_fault)

    def test_dimension_b_cross_model_backup_audit_and_ram_shadow_bk4_synthesizer(self) -> None:
        rep_b = audit_cross_model_backup_contracts()
        self.assertTrue(rep_b.all_checks_passed)
        self.assertTrue(rep_b.fx6_libbackup_sha256_verified)
        self.assertTrue(rep_b.fx6_libbackup_manager_sha256_verified)
        self.assertTrue(rep_b.fx3_libbackup_sha256_verified)
        self.assertEqual(rep_b.fx6_backup_export_count, 56)
        self.assertEqual(rep_b.fx3_backup_export_count, 58)
        self.assertTrue(rep_b.fx3_exports_superset_of_fx6)
        self.assertTrue(rep_b.backup_section_receipt_verified)
        self.assertTrue(rep_b.backup_key_values_receipt_verified)
        self.assertEqual(rep_b.fx6_template_subsystems, 840)
        self.assertEqual(rep_b.fx3_seed_subsystems, 819)
        self.assertEqual(rep_b.fx3_extra_slot2_media_id, 0x1002)

        # Deterministic in-RAM synthesis check
        b1 = synthesize_ram_shadow_bk4(flash_write_allowed=False)
        b2 = synthesize_ram_shadow_bk4(flash_write_allowed=False)
        self.assertEqual(b1.sha256, b2.sha256)
        self.assertEqual(b1.bk4_bytes, b2.bk4_bytes)
        self.assertFalse(b1.flash_write_allowed)
        self.assertEqual(b1.target_backing, "RAM_TMPFS_SHADOW_ONLY")
        self.assertEqual(b1.active_byte8_selector, 0x00)

        audit = audit_ram_shadow_bk4(b1.bk4_bytes, flash_write_allowed=False)
        self.assertTrue(audit.valid, audit.errors)
        self.assertTrue(audit.flash_write_prohibited)
        self.assertTrue(audit.bk4_header_valid)
        self.assertTrue(audit.selector_byte8_zero_ok)
        self.assertTrue(audit.strict_loader_unselectable_ok)
        self.assertTrue(audit.checksum32_ok)
        self.assertTrue(audit.all_property_crc16_ok)
        self.assertTrue(audit.fixed_area_keys_ok)
        self.assertTrue(audit.fa0080_normal_boot_p3_ok)
        self.assertTrue(audit.dual_slot_media_ids_ok)
        self.assertTrue(audit.boot_screen_enum_ok)
        self.assertEqual(audit.observed_slot_media_ids, FX6_DUAL_SLOT_MEDIA_IDS)

        # Verify direct key extraction from synthesized BK4\0 container
        self.assertEqual(len(read_bk4_property_bytes(b1.bk4_bytes, KEY_FIXED_AREA_TOP) or b""), 8)
        self.assertEqual(len(read_bk4_property_bytes(b1.bk4_bytes, KEY_FIXED_AREA_SIZE) or b""), 8)
        self.assertEqual(len(read_bk4_property_bytes(b1.bk4_bytes, KEY_FA0080_BOOT_DESC) or b""), 9216)
        self.assertEqual(len(read_bk4_property_bytes(b1.bk4_bytes, KEY_DUAL_SLOT_MEDIA_SHADOW) or b""), 16)

    def test_ram_shadow_bk4_rejects_flash_write_corrupted_magic_truncation_byte8_and_bad_slots(self) -> None:
        import struct as _st

        with self.assertRaises(ValueError):
            synthesize_ram_shadow_bk4(flash_write_allowed=True)

        good = synthesize_ram_shadow_bk4(flash_write_allowed=False)
        self.assertFalse(audit_ram_shadow_bk4(good.bk4_bytes, flash_write_allowed=True).valid)

        # 1. Corrupted BK4\0 magic
        bad_magic = bytearray(good.bk4_bytes)
        bad_magic[0x0C:0x10] = b"BK9\x00"
        res_magic = audit_ram_shadow_bk4(bytes(bad_magic))
        self.assertFalse(res_magic.valid)
        self.assertFalse(res_magic.bk4_header_valid)

        # 2. Truncated payload
        res_trunc = audit_ram_shadow_bk4(good.bk4_bytes[:-64])
        self.assertFalse(res_trunc.valid)

        # 3. Non-zero byte-8 boot/record selector (even with valid 32-bit BK4 checksum!)
        bad_b8 = synthesize_ram_shadow_bk4(active_byte8=0x01)
        res_b8 = audit_ram_shadow_bk4(bad_b8.bk4_bytes)
        self.assertFalse(res_b8.valid)
        self.assertTrue(res_b8.checksum32_ok)
        self.assertFalse(res_b8.selector_byte8_zero_ok)
        self.assertFalse(res_b8.strict_loader_unselectable_ok)

        # 4. Corrupted 16-bit per-property CRC16 (while recomputing outer 32-bit BK4 checksum!)
        bad_crc16 = bytearray(good.bk4_bytes)
        bad_crc16[-4] ^= 0xFF
        new_sum32 = (sum(bad_crc16[0:0x20]) + sum(bad_crc16[0x24:])) & 0xFFFFFFFF
        _st.pack_into("<I", bad_crc16, 0x20, new_sum32)
        res_crc16 = audit_ram_shadow_bk4(bytes(bad_crc16))
        self.assertFalse(res_crc16.valid)
        self.assertTrue(res_crc16.checksum32_ok)
        self.assertFalse(res_crc16.all_property_crc16_ok)

        # 5. Violated 0x00fa0080 Normal Boot p3 invariant (partition mutated 3 -> 1)
        bad_fa = bytearray(build_canonical_fa0080_normal_boot_table())
        _st.pack_into("<I", bad_fa, 0x10, 1)  # Slot 0 (\av-cam.bin) pointed at p1 instead of p3
        bad_p3_bundle = synthesize_ram_shadow_bk4(fa0080_table=bytes(bad_fa))
        res_p3 = audit_ram_shadow_bk4(bad_p3_bundle.bk4_bytes)
        self.assertFalse(res_p3.valid)
        self.assertFalse(res_p3.fa0080_normal_boot_p3_ok)

        # 6. Invalid MediaConfig slot ID (`0x1002` instead of `0x1010`)
        bad_slots_bundle = synthesize_ram_shadow_bk4(slot_a_media_id=0x1000, slot_b_media_id=0x1002)
        res_slots = audit_ram_shadow_bk4(bad_slots_bundle.bk4_bytes)
        self.assertFalse(res_slots.valid)
        self.assertFalse(res_slots.dual_slot_media_ids_ok)

        # 7. Invalid FX3 boot-screen enum (`0x16` instead of `{0, 1}`)
        bad_enum_bundle = synthesize_ram_shadow_bk4(boot_screen_214=0x16)
        res_enum = audit_ram_shadow_bk4(bad_enum_bundle.bk4_bytes)
        self.assertFalse(res_enum.valid)
        self.assertFalse(res_enum.boot_screen_enum_ok)

    def test_cli_verify_backup_mount_contracts_subcommand(self) -> None:
        full_rep = run_backup_mount_tolerance_verification()
        self.assertTrue(full_rep.all_checks_passed)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-backup-mount-contracts"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "OK")
        self.assertTrue(payload["all_checks_passed"])
        self.assertTrue(payload["u4_closed"])
        self.assertTrue(payload["dimension_b_backup_contracts"]["ram_shadow_audit"]["valid"])


if __name__ == "__main__":
    unittest.main()
