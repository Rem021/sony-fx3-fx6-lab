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
import os
import struct
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
from fx6_closure.boot_selector_and_bank_verifier import (
    DEFAULT_FX3_BANK0_FA0080_PATH,
    DEFAULT_FX3_BANK1_FA0080_PATH,
    EXPECTED_BANK1_CALIBRATION_SHIFTS,
    LOADER_NOR_EXPECTED_BOOTMODES,
    LOADER_NOR_PINNED_INSNS,
    UD_SEND_LSI_DST_QUEUE_ID,
    UD_SEND_LSI_DST_QUEUE_LOW16,
    UD_SEND_LSI_OSAL_E_TMO,
    UD_SEND_LSI_PINNED_INSNS,
    UD_SEND_LSI_RCV_TIMEOUT_MS,
    UD_SEND_LSI_SRC_REPLY_QUEUE_ID,
    UP_SH_MODE_SPECS,
    audit_boot_selector_contract,
    audit_fa0080_bank_maps,
    parse_and_audit_fa0080_bank,
    run_boot_selector_and_bank_verification,
    verify_boot_selector_safety_contract,
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
from fx6_closure.kernel_dtb_compatibility_verifier import (
    DEFAULT_FX3_DTB_PATH,
    DEFAULT_FX6_P1_INITRD_DIR,
    EXPECTED_HOST_VERMAGIC,
    EXPECTED_KEMCO_MEMRSV_CARVEOUTS,
    EXPECTED_P1_UPDATER_VERMAGIC,
    FdtFormatError,
    KoModuleFormatError,
    PINNED_CXD90057_DTB_SHA256,
    PINNED_FX3_HOST_KO_SHA256,
    SYNTHETIC_MODULE_LAYOUT_CRC,
    audit_dtb_soc_compatibility,
    audit_kernel_module_compatibility,
    inject_synthetic_modversions_section,
    parse_and_audit_ko_module,
    parse_fdt_blob,
    run_kernel_dtb_verification,
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
from fx6_closure.storage_and_ram_budget_verifier import (
    DEFAULT_SAFE_STAGE_A_TMPFS_CEILING_BYTES,
    EXPECTED_FX3_END_SECTOR,
    EXPECTED_FX3_P15_BYTES,
    EXPECTED_FX6_END_SECTOR,
    EXPECTED_NFLASH15_ALIGNED_4K_BYTES,
    EXPECTED_NFLASH15_ENTRY_COUNT,
    EXPECTED_NFLASH15_EXT2_IMAGE_BYTES,
    EXPECTED_NFLASH15_RAW_BYTES,
    EXPECTED_NFLASH15_REGULAR_FILES,
    EXPECTED_NFLASH15_SYMLINKS,
    EXPECTED_NFLASH15_TOTAL_DIRS,
    EXPECTED_UDA_DELTA_SECTORS,
    audit_ddr_and_tmpfs_ram_budget,
    audit_p15_usr_footprint,
    audit_storage_topology_and_p15_budget,
    audit_zero_repartition_redline,
    parse_and_audit_pformat_config,
    run_storage_and_ram_budget_verification,
)
from fx6_closure.cp_rtos_compatibility_verifier import (
    CP_BANK1_BUS_LOAD_ADDR,
    CP_FIRST_BRANCH_TARGET,
    CP_LOCAL_LOAD_BASE,
    DEFAULT_FX3_RUNTIME_TOMCO_PATH,
    DEFAULT_FX3_UPDATER_CP_DIR,
    DEFAULT_FX6_NFLASHA8_DIR,
    EXPECTED_CP_ARM32_ENTRY_WORDS,
    EXPECTED_CP_IDENTICAL_PREFIX_BYTES,
    EXPECTED_FX3_CP_REF_BYTES,
    EXPECTED_FX3_CP_REF_SHA256,
    EXPECTED_FX6_NFLASHA8_ARTIFACTS,
    EXPECTED_RUNTIME_MEMCFG_SPEC,
    PINNED_FX6_CP_PERIPHERAL_MARKERS,
    REQUIRED_IDENTICAL_IPC_AND_TELEMETRY_KEYS,
    TOMCO_BANK1_BUS_LOAD_ADDR,
    TOMCO_BANK1_SPAN_BYTES,
    TomcoFormatError,
    compare_tomco_configs,
    parse_tomco_txt,
    run_cp_rtos_compatibility_verification,
    scan_fx6_cp_peripheral_markers,
    validate_candidate_cp_redline,
)
from fx6_closure.p1_recovery_bridge_verifier import (
    PINNED_FX6_P1_IMAGE_BYTES,
    PINNED_FX6_P1_IMAGE_SHA256,
    PINNED_FX6_P1_INITRD_BYTES,
    PINNED_FX6_P1_INITRD_SHA256,
    audit_worker_c_source_posture,
    run_p1_recovery_bridge_verification,
    verify_p1_container_and_u5_handoff,
    verify_tier0_fx3_recovery_alignment,
)
from fx6_closure.stage_a_boot_orchestrator import (
    EXPECTED_FX6_WBI_O_DATA_BYTES,
    EXPECTED_FX6_WBI_R_DATA_BYTES,
    EXPECTED_FX6_WBI_RESUME_VECTOR,
    EXPECTED_FX6_WBI_SECTION_COUNT,
    EXPECTED_INSMOD_DRV1_ORDER,
    EXPECTED_INSMOD_DRV2_TOTAL_COUNT,
    EXPECTED_INSMOD_DRV2_UPM_ONE_BASED_SLOT,
    EXPECTED_STAGE_A_FORWARD_STEP_IDS,
    EXPECTED_STAGE_A_LIFO_UNWIND_STEP_IDS,
    EXPECTED_WBIMEM_COLLISION_DELTA_BYTES,
    ORCHESTRATOR_CPIO_REL_PATH,
    PINNED_FX3_STOCK_WBI_SHA256,
    PINNED_FX6_WBI_NFLASH5_BYTES,
    PINNED_FX6_WBI_NFLASH5_SHA256,
    PINNED_INITRD_AND_BOOT_ARTIFACTS,
    audit_initrd_boot_chain_and_wbi_contracts,
    generate_stage_a_boot_orchestrator_script,
    parse_wbi2_header_bytes,
    run_stage_a_boot_orchestrator_verification,
    simulate_orchestrator_state_machine,
    validate_candidate_wbi_redline,
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
from fx6_closure.kmod_and_userland_abi_verifier import (
    build_synthetic_elf64_linkage_blob,
    classify_kmod_driver_matrix,
    classify_userland_dev_node,
    evaluate_elf64_linkage_closure,
    extract_dev_node_references_from_blob,
    parse_elf64_linkage_info,
    parse_insmod_script,
    run_kmod_and_userland_abi_verification,
)
from fx6_closure.patcher import LibraryPatchSpec, PatchSiteSpec
from fx6_closure.tier0_unicorn_verifier import _resolve_zig_binary
from fx6_closure.vfat_builder import (
    SECTOR_SIZE,
    build_opelog_vfat_image,
    generate_p2_opelog_mount_snippet,
    verify_vfat_image,
)

_CLEAN_ROOM_SKIP_REASON = "External BYOF Sony donor blobs unavailable or FX3_FX6_FORCE_CLEAN_ROOM=1"


def _is_clean_room_or_donor_missing() -> bool:
    if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes"):
        return True
    return not DEFAULT_FX6_DONOR_LIB_DIR.is_dir() or not DEFAULT_FX3_MODULES_DIR.is_dir()


class TestElf64Mapper(unittest.TestCase):
    """Validate strict ELF64 `PT_LOAD` and `ET_REL` section file-offset translation."""

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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
        try:
            import unicorn as _uc  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest(f"Unicorn not installed: {exc}")
        if not _resolve_zig_binary().is_file():
            raise unittest.SkipTest("Zig AArch64 cross-compiler not installed on host")
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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
        self.assertTrue(rep_ok.boot_selector_and_banks_ok)
        self.assertTrue(rep_ok.boot_selector_and_bank_audit.dimension_a_boot_selector.u5_closed)
        self.assertTrue(rep_ok.boot_selector_and_bank_audit.dimension_b_bank_maps.u3_advanced)
        self.assertTrue(rep_ok.kernel_dtb_ok)
        self.assertTrue(rep_ok.kernel_dtb_audit.all_checks_passed)
        self.assertTrue(rep_ok.kernel_dtb_audit.dimension_a_dtb.dtb_byte_identical)
        self.assertTrue(rep_ok.kernel_dtb_audit.dimension_b_ko.p9_upm_integrity.valid)
        self.assertTrue(rep_ok.storage_and_ram_budget_ok)
        self.assertTrue(rep_ok.storage_and_ram_budget_audit.all_checks_passed)
        self.assertTrue(rep_ok.storage_and_ram_budget_audit.edisx_repartition_forbidden)
        self.assertEqual(rep_ok.storage_and_ram_budget_audit.sector0_mutation_bytes, 0)
        self.assertTrue(rep_ok.storage_and_ram_budget_audit.p15_fits_stock_fx3)
        self.assertTrue(rep_ok.storage_and_ram_budget_audit.ram_budget_within_safe_bounds)
        self.assertTrue(rep_ok.cp_rtos_ok)
        self.assertTrue(rep_ok.cp_rtos_audit.all_checks_passed)
        self.assertTrue(rep_ok.cp_rtos_audit.u2_closed)
        self.assertTrue(rep_ok.cp_rtos_audit.p8_cp_mutation_forbidden)
        self.assertEqual(rep_ok.cp_rtos_audit.cp_mutation_bytes, 0)
        self.assertTrue(rep_ok.p1_recovery_bridge_ok)
        self.assertTrue(rep_ok.p1_recovery_bridge_audit.all_checks_passed)
        self.assertTrue(rep_ok.p1_recovery_bridge_audit.p1_recovery_bridge_ok)
        self.assertTrue(rep_ok.stage_a_orchestrator_ok)
        self.assertTrue(rep_ok.stage_a_orchestrator_audit.all_checks_passed)
        self.assertTrue(rep_ok.stage_a_orchestrator_audit.wbi_p5_write_and_hibernation_forbidden)
        self.assertEqual(rep_ok.stage_a_orchestrator_audit.wbi_mutation_bytes, 0)
        self.assertFalse(rep_ok.safety_gates_report["persistent_write_release"])

        drill_base = rep_ok.rollback_drill
        feat_base = rep_ok.feature_routing_audit
        bmt_base = rep_ok.backup_mount_tolerance_audit
        bsb_base = rep_ok.boot_selector_and_bank_audit
        kdtb_base = rep_ok.kernel_dtb_audit
        sram_base = rep_ok.storage_and_ram_budget_audit
        cp_base = rep_ok.cp_rtos_audit
        p1_bridge_base = rep_ok.p1_recovery_bridge_audit
        stage_a_orch_base = rep_ok.stage_a_orchestrator_audit

        # 2. Missing Tier-0 item -> immediately blocks G10, G11, and G12
        tier0_base = run_tier0_worker_in_unicorn(compiled_worker=self.compiled_worker)
        rep_missing = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
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
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
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
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
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
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
            corrupt_opelog_vfat=True,
        )
        self.assertFalse(rep_bad_vfat.candidate_ready)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_vfat.blocked_gate_ids)

        # 6. Corrupted P5/P6 UIPC, P7 Backup Sync100 bridge, Stage-A CPIO, 5-Feature Routing, U4/BK4, U5/U3, DTB/.ko, Storage/RAM Budget, CP RTOS, P1 Bridge, or Stage-A Orchestrator -> blocks G12
        rep_bad_uipc = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
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
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
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
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
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
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
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
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
            corrupt_backup_mount_tolerance=True,
        )
        self.assertFalse(rep_bad_bmt.candidate_ready)
        self.assertFalse(rep_bad_bmt.backup_mount_tolerance_ok)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_bmt.blocked_gate_ids)

        rep_bad_bsb = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
            corrupt_boot_selector_and_banks=True,
        )
        self.assertFalse(rep_bad_bsb.candidate_ready)
        self.assertFalse(rep_bad_bsb.boot_selector_and_banks_ok)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_bsb.blocked_gate_ids)

        rep_bad_kdtb = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
            corrupt_kernel_dtb=True,
        )
        self.assertFalse(rep_bad_kdtb.candidate_ready)
        self.assertFalse(rep_bad_kdtb.kernel_dtb_ok)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_kdtb.blocked_gate_ids)
        g12_kdtb = [
            g
            for g in rep_bad_kdtb.safety_gates_report["gates"]
            if g["gate_id"] == "G12_persistent_flash_write_authorization"
        ][0]
        self.assertEqual(g12_kdtb["status"], "BLOCKED_BY_KERNEL_OR_DTB_REDLINE")

        rep_bad_sram = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
            corrupt_storage_and_ram_budget=True,
        )
        self.assertFalse(rep_bad_sram.candidate_ready)
        self.assertFalse(rep_bad_sram.storage_and_ram_budget_ok)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_sram.blocked_gate_ids)
        g12_sram = [
            g
            for g in rep_bad_sram.safety_gates_report["gates"]
            if g["gate_id"] == "G12_persistent_flash_write_authorization"
        ][0]
        self.assertEqual(g12_sram["status"], "BLOCKED_BY_STORAGE_OR_RAM_BUDGET_REDLINE")

        rep_bad_cp = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
            corrupt_cp_rtos=True,
        )
        self.assertFalse(rep_bad_cp.candidate_ready)
        self.assertFalse(rep_bad_cp.cp_rtos_ok)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_cp.blocked_gate_ids)
        g12_cp = [
            g
            for g in rep_bad_cp.safety_gates_report["gates"]
            if g["gate_id"] == "G12_persistent_flash_write_authorization"
        ][0]
        self.assertEqual(g12_cp["status"], "BLOCKED_BY_CP_RTOS_REDLINE")

        rep_bad_p1_bridge = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
            corrupt_p1_recovery_bridge=True,
        )
        self.assertFalse(rep_bad_p1_bridge.candidate_ready)
        self.assertFalse(rep_bad_p1_bridge.p1_recovery_bridge_ok)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_p1_bridge.blocked_gate_ids)
        g12_p1b = [
            g
            for g in rep_bad_p1_bridge.safety_gates_report["gates"]
            if g["gate_id"] == "G12_persistent_flash_write_authorization"
        ][0]
        self.assertEqual(g12_p1b["status"], "BLOCKED_BY_P1_RECOVERY_BRIDGE_REDLINE")

        rep_bad_stage_a_orch = run_offline_candidate_dry_run(
            compiled_worker=self.compiled_worker,
            precomputed_tier0_result=tier0_base,
            precomputed_rollback_drill=drill_base,
            precomputed_feature_routing=feat_base,
            precomputed_backup_mount_tolerance=bmt_base,
            precomputed_boot_selector_and_banks=bsb_base,
            precomputed_kernel_dtb=kdtb_base,
            precomputed_storage_and_ram_budget=sram_base,
            precomputed_cp_rtos=cp_base,
            precomputed_p1_recovery_bridge=p1_bridge_base,
            precomputed_stage_a_orchestrator=stage_a_orch_base,
            corrupt_stage_a_orchestrator=True,
        )
        self.assertFalse(rep_bad_stage_a_orch.candidate_ready)
        self.assertFalse(rep_bad_stage_a_orch.stage_a_orchestrator_ok)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad_stage_a_orch.blocked_gate_ids)
        g12_orch = [
            g
            for g in rep_bad_stage_a_orch.safety_gates_report["gates"]
            if g["gate_id"] == "G12_persistent_flash_write_authorization"
        ][0]
        self.assertEqual(g12_orch["status"], "BLOCKED_BY_STAGE_A_ORCHESTRATOR_OR_WBI_REDLINE")

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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
        self.assertTrue(manifest["wbi_p5_write_and_hibernation_forbidden"])
        self.assertEqual(manifest["wbi_mutation_bytes"], 0)
        self.assertEqual(manifest["matrix_item_count"], 10)
        self.assertEqual(tuple(manifest["verified_matrix_ids"]), COMPLETE_MATRIX_ITEMS)
        self.assertEqual(len(manifest["sha256_check_list"]), 10)
        self.assertEqual(len(b1.staged_runtime_blobs), 10)

        # Verify required paths in CPIO (including 30-stage-a-orchestrator.sh)
        entry_names = tuple(e.name for e in b1.cpio_audit.entries)
        self.assertIn(ORCHESTRATOR_CPIO_REL_PATH, entry_names)
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
        bundle = build_stage_a_ram_overlay_package(synthetic_clean_room=_is_clean_room_or_donor_missing())
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_b_donor_setupfile_lut_mount_chain(self) -> None:
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
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


class TestPhase7BootSelectorAndBankVerifier(unittest.TestCase):
    """Verify Phase 7 U5 Boot-Selector Single-Shot Contract & U3 0xfa0080 Bank 0/1 DDR Non-Overlap Verifier."""

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_a_u5_up_sh_ud_send_lsi_unicorn_and_loader_nor_contract(self) -> None:
        rep_a = audit_boot_selector_contract()
        self.assertTrue(rep_a.all_checks_passed)
        self.assertTrue(rep_a.u5_closed)
        self.assertTrue(rep_a.up_sh_sha256_verified)
        self.assertTrue(rep_a.common_src_sha256_verified)
        self.assertTrue(rep_a.ud_send_lsi_sha256_verified)
        self.assertTrue(rep_a.ud_send_lsi_pt_load_identical_across_models)
        self.assertEqual(rep_a.ud_send_lsi_comment_diff_bytes, 7)
        self.assertTrue(rep_a.loader_nor_sha256_verified)
        self.assertTrue(rep_a.ldr_bkup_list_65_keys_verified)
        self.assertTrue(rep_a.pformat_config_sha256_verified)
        self.assertTrue(rep_a.up_sh_modes_verified)
        self.assertTrue(rep_a.up_sh_iamupdater_early_exit_verified)
        self.assertEqual(rep_a.loader_nor_bootmodes, LOADER_NOR_EXPECTED_BOOTMODES)

        self.assertEqual(len(rep_a.ud_send_lsi_insns), len(UD_SEND_LSI_PINNED_INSNS))
        self.assertEqual(len(rep_a.loader_nor_insns), len(LOADER_NOR_PINNED_INSNS))
        for chk in rep_a.ud_send_lsi_insns + rep_a.loader_nor_insns:
            self.assertTrue(chk.matched, f"Instruction mismatch at {hex(chk.vma)}: {chk}")

        # Verify all 10 Unicorn AArch64 cases on `ud_send_lsi.elf`
        self.assertEqual(len(rep_a.unicorn_cases), 10)
        expected_hex = {
            0: "00000000",
            2: "02000000",
            3: "03000000",
            4: "04000000",
            5: "05000000",
            6: "06000000",
            7: "07000000",
        }
        for case, spec in zip(rep_a.unicorn_cases[:7], UP_SH_MODE_SPECS):
            mode_num = spec[1]
            self.assertFalse(case.abort_or_fault)
            self.assertFalse(case.exited_early)
            self.assertEqual(case.return_value, 0)
            self.assertTrue(case.uipc_allocated)
            self.assertTrue(case.uipc_sent)
            self.assertTrue(case.uipc_freed)
            self.assertEqual(case.observed_dst_queue, UD_SEND_LSI_DST_QUEUE_ID)
            self.assertEqual(case.observed_dst_queue & 0xFFFF, UD_SEND_LSI_DST_QUEUE_LOW16)
            self.assertEqual(case.observed_src_queue, UD_SEND_LSI_SRC_REPLY_QUEUE_ID)
            self.assertEqual(case.observed_timeout_ms, UD_SEND_LSI_RCV_TIMEOUT_MS)
            self.assertEqual(case.emitted_mode_u32, mode_num)
            self.assertEqual(case.emitted_payload_hex, expected_hex[mode_num])
            self.assertTrue(case.sp_preserved)

        # Case 7: p1 initrd binary + LSI_SUB=2 + OSAL_E_TMO (-0x3fe) tolerated cleanly
        sub_tmo = rep_a.unicorn_cases[7]
        self.assertEqual(sub_tmo.injected_lsi_type, 2)
        self.assertEqual(sub_tmo.injected_rcv_rc, UD_SEND_LSI_OSAL_E_TMO)
        self.assertEqual(sub_tmo.return_value, 0)
        self.assertEqual(sub_tmo.emitted_payload_hex, "00000000")
        self.assertTrue(sub_tmo.sp_preserved)

        # Case 8: cold factory seed 0x004b0000 = 3 -> skips UIPC cleanly with rc = 0
        cold_noop = rep_a.unicorn_cases[8]
        self.assertEqual(cold_noop.return_value, 0)
        self.assertFalse(cold_noop.uipc_allocated)
        self.assertFalse(cold_noop.uipc_sent)
        self.assertTrue(cold_noop.sp_preserved)

        # Case 9: argc != 2 -> exit(1) before touching UIPC
        bad_argc = rep_a.unicorn_cases[9]
        self.assertTrue(bad_argc.exited_early)
        self.assertEqual(bad_argc.exit_status, 1)
        self.assertFalse(bad_argc.uipc_sent)

        self.assertTrue(rep_a.stage_a_overlay_safety.valid)
        self.assertTrue(rep_a.p1_recovery_two_step_reset_ok.valid)

    def test_boot_selector_safety_rejects_incomplete_p1_exit_sticky_flags_and_byte8(self) -> None:
        # 1. Calling `up.sh` inside `/root/IAMUPDATER` without explicit `ud_send_lsi.elf 0` -> sticky ANK latch!
        bad_iam = verify_boot_selector_safety_contract(
            "BAD_P1_EXIT_UP_SH_ONLY",
            in_p1_updater_env=True,
            p1_partition_written=False,
            p2_updater_mode_files=(),
            up_sh_invoked_without_direct_lsi=True,
            direct_ud_send_lsi_payload=None,
            bk4_selector_byte8=0x00,
        )
        self.assertFalse(bad_iam.valid)
        self.assertTrue(bad_iam.sticky_updater_risk)
        self.assertFalse(bad_iam.iamupdater_bypass_handled)
        self.assertFalse(bad_iam.lsi_normal_packet_emitted)

        # 2. Sending `ud_send_lsi.elf 0` while leaving `/setting/updater/mode` on p2 -> sticky MMIO 0xFE170028!
        bad_p2 = verify_boot_selector_safety_contract(
            "BAD_P1_EXIT_LEFTOVER_P2_MODE_FILE",
            in_p1_updater_env=True,
            p1_partition_written=False,
            p2_updater_mode_files=("/setting/updater/mode",),
            up_sh_invoked_without_direct_lsi=False,
            direct_ud_send_lsi_payload=b"\x00\x00\x00\x00",
            bk4_selector_byte8=0x00,
        )
        self.assertFalse(bad_p2.valid)
        self.assertFalse(bad_p2.p2_updater_flags_cleared)

        # 3. Stage-A path writing p1 or sending non-zero mode packet or non-zero BK4 byte 8 -> rejected!
        bad_stage_a = verify_boot_selector_safety_contract(
            "BAD_STAGE_A_TOUCHES_P1_AND_MODE4",
            in_p1_updater_env=False,
            p1_partition_written=True,
            p2_updater_mode_files=(),
            up_sh_invoked_without_direct_lsi=False,
            direct_ud_send_lsi_payload=b"\x04\x00\x00\x00",
            bk4_selector_byte8=0x01,
        )
        self.assertFalse(bad_stage_a.valid)
        self.assertTrue(bad_stage_a.p1_touched)
        self.assertFalse(bad_stage_a.lsi_normal_packet_emitted)
        self.assertFalse(bad_stage_a.bk4_byte8_normal_ok)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_b_u3_bank0_bank1_non_overlap_and_calibration_shifts(self) -> None:
        rep_b = audit_fa0080_bank_maps()
        self.assertTrue(rep_b.all_checks_passed)
        self.assertTrue(rep_b.u3_advanced)
        self.assertTrue(rep_b.fx3_bank0_matches_seed_record0)
        self.assertTrue(rep_b.fx3_bank1_matches_seed_record1)

        self.assertTrue(rep_b.fx3_bank0_audit.valid)
        self.assertEqual(rep_b.fx3_bank0_audit.active_slot_count, 9)
        self.assertTrue(rep_b.fx3_bank0_audit.zero_overlap_verified)

        self.assertTrue(rep_b.fx3_bank1_audit.valid)
        self.assertEqual(rep_b.fx3_bank1_audit.active_slot_count, 11)
        self.assertTrue(rep_b.fx3_bank1_audit.zero_overlap_verified)
        self.assertEqual(sum(1 for iv in rep_b.fx3_bank1_audit.intervals if iv.is_dynamic_size_sentinel), 1)

        self.assertTrue(rep_b.fx6_bank0_audit.valid)
        self.assertEqual(rep_b.fx6_bank0_audit.active_slot_count, 5)
        self.assertTrue(rep_b.fx6_bank0_audit.zero_overlap_verified)

        self.assertTrue(rep_b.fx6_bank1_audit.valid)
        self.assertEqual(rep_b.fx6_bank1_audit.active_slot_count, 10)
        self.assertTrue(rep_b.fx6_bank1_audit.zero_overlap_verified)

        # Bank 0 shared AP descriptors: 0-byte shift across all 5 shared entries
        self.assertTrue(rep_b.bank0_shared_zero_shift_verified)
        self.assertEqual(len(rep_b.bank0_shifts), 5)
        for sh in rep_b.bank0_shifts:
            self.assertEqual(sh.delta_bytes, 0)

        # Bank 1 calibration shifts: exact +0xE0000 and +0x14000
        self.assertTrue(rep_b.bank1_calibration_shifts_verified)
        b1_map = {sh.path: sh.delta_bytes for sh in rep_b.bank1_shifts}
        self.assertEqual(b1_map, EXPECTED_BANK1_CALIBRATION_SHIFTS)
        self.assertEqual(b1_map["\\psd.bin"], 0xE0000)
        self.assertEqual(b1_map["\\lensfile.bin"], 0xE0000)
        self.assertEqual(b1_map["\\OldAmtCL.bin"], 0xE0000)
        self.assertEqual(b1_map["\\defdet.bin"], 0x14000)
        self.assertEqual(b1_map["\\DmmCfg.bin"], 0x14000)
        self.assertEqual(rep_b.fx3_only_bank1_paths, ("\\SysSound.bin", "\\cpImg.dat"))
        self.assertEqual(rep_b.fx6_only_bank1_paths, ("\\cmrbnb.bin",))

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_fa0080_bank_auditor_rejects_overlap_bad_partition_and_cli_subcommand(self) -> None:
        import struct as _st

        fx3_b0 = DEFAULT_FX3_BANK0_FA0080_PATH.read_bytes()
        fx3_b1 = DEFAULT_FX3_BANK1_FA0080_PATH.read_bytes()

        # 1. Inject 4 KiB DDR overlap in Bank 1 (`\lensfile.bin` moved down into `\psd.bin` [0x0808730000..0x0808c2ffff])
        base_b1_audit = parse_and_audit_fa0080_bank(fx3_b1, label="BASE_B1", bank_index=1)
        lens_slot = next(iv.slot_index for iv in base_b1_audit.intervals if iv.path == "\\lensfile.bin")
        overlap_b1 = bytearray(fx3_b1)
        _st.pack_into("<QQ", overlap_b1, lens_slot * 144, 0x0808C2F000, 0x0808CAFFFF)
        res_ov = parse_and_audit_fa0080_bank(bytes(overlap_b1), label="SYNTH_OVERLAP", bank_index=1)
        self.assertFalse(res_ov.valid)
        self.assertFalse(res_ov.zero_overlap_verified)
        self.assertEqual(len(res_ov.overlap_pairs), 1)
        self.assertIn("overlap by 0x1000 bytes", res_ov.overlap_pairs[0])

        # 2. Inject out-of-bounds partition index (`p31`) in Bank 0
        bad_part_b0 = bytearray(fx3_b0)
        _st.pack_into("<I", bad_part_b0, 0x10, 31)
        res_part = parse_and_audit_fa0080_bank(bytes(bad_part_b0), label="SYNTH_BAD_PART", bank_index=0)
        self.assertFalse(res_part.valid)
        self.assertFalse(res_part.partitions_in_bounds)

        # 3. Non-zero byte-8 selector (`0x01`) in Bank 0 -> rejected!
        res_b8 = parse_and_audit_fa0080_bank(fx3_b0, label="SYNTH_B0_BYTE8", bank_index=0, active_byte8=0x01)
        self.assertFalse(res_b8.valid)
        self.assertFalse(res_b8.selector_byte8_ok)

        # 4. Inverted DDR range (`end_addr < start_addr` on non-sentinel slot) -> rejected!
        inv_b0 = bytearray(fx3_b0)
        _st.pack_into("<QQ", inv_b0, 0, 0x0802200000, 0x0802100000)
        res_inv = parse_and_audit_fa0080_bank(bytes(inv_b0), label="SYNTH_INV_RANGE", bank_index=0)
        self.assertFalse(res_inv.valid)

        # 5. Truncated 0xfa0080 table -> rejected!
        self.assertFalse(parse_and_audit_fa0080_bank(fx3_b0[:-144], label="TRUNC", bank_index=0).valid)

        # 6. CLI `verify-boot-selector-banks` subcommand check
        full_rep = run_boot_selector_and_bank_verification()
        self.assertTrue(full_rep.all_checks_passed)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-boot-selector-banks"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "OK")
        self.assertTrue(payload["all_checks_passed"])
        self.assertTrue(payload["u5_closed"])
        self.assertTrue(payload["u3_advanced"])
        self.assertEqual(len(payload["dimension_a_boot_selector"]["unicorn_cases"]), 10)
        self.assertTrue(payload["dimension_b_bank_maps"]["fx3_bank0_audit"]["zero_overlap_verified"])
        self.assertTrue(payload["dimension_b_bank_maps"]["fx6_bank1_audit"]["zero_overlap_verified"])


class TestPhase8KernelDtbCompatibilityVerifier(unittest.TestCase):
    """Verify Phase 8 cxd90057.dtb FDT SoC Compatibility Auditor & .ko vermagic/__versions CRC Verifier."""

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_a_fdt_parser_and_fx3_vs_fx6_cxd90057_dtb_soc_audit(self) -> None:
        rep_a = audit_dtb_soc_compatibility()
        self.assertTrue(rep_a.all_checks_passed)
        self.assertTrue(rep_a.fx3_dtb_sha256_verified)
        self.assertTrue(rep_a.fx6_dtb_sha256_verified)
        self.assertTrue(rep_a.dtb_byte_identical)
        self.assertEqual(rep_a.fdt_node_count, 68)
        self.assertEqual(rep_a.fdt_property_count, 493)
        self.assertEqual(rep_a.node_or_property_diff_count, 0)
        self.assertTrue(rep_a.loadaddr_txt_identical)
        self.assertEqual(
            rep_a.loadaddr_quad,
            (0x400080000, 0x408000000, 0x400001000, 0x400002000),
        )

        soc = rep_a.soc_summary
        self.assertEqual(soc.root_compatible, ("cxd,cxd90057",))
        self.assertEqual(soc.root_model, "CXD90057")
        self.assertEqual(soc.chosen_stdout_path, "serial0:460800n8")
        self.assertFalse(soc.chosen_has_inline_bootargs)
        self.assertEqual(soc.memory_base_addr, 0x400000000)
        self.assertEqual(soc.memory_size_bytes, 0x200000000)
        self.assertFalse(soc.has_reserved_memory_node)
        self.assertEqual(len(soc.static_iomap_regions), 3)
        self.assertEqual(soc.pcie_ep_dummy_carveout, (0x7, 0x400000000, 0x1000))
        self.assertEqual(soc.cpu_count, 4)
        self.assertIn("arm,cortex-a35", soc.cpu_compatible)
        self.assertIn("arm,gic-400", soc.gic_compatible)
        self.assertEqual(len(soc.gic_mmio_windows), 4)
        self.assertEqual(len(soc.uart_nodes), 5)
        self.assertEqual(soc.emmc_compatible, ("arasan,sdhci",))
        self.assertEqual(len(soc.pcie_rc_nodes), 5)
        self.assertEqual(len(soc.pcie_ep_ipc_nodes), 5)

        self.assertTrue(rep_a.fx3_kemco_audit.valid)
        self.assertTrue(rep_a.fx6_p1_kemco_audit.valid)
        self.assertTrue(rep_a.kemco_memrsv_identical)
        self.assertEqual(len(rep_a.fx3_kemco_audit.memrsv_entries), len(EXPECTED_KEMCO_MEMRSV_CARVEOUTS))
        self.assertEqual(rep_a.fx3_kemco_audit.ramdisk_size_kib, 16384)
        self.assertEqual(rep_a.fx6_p1_kemco_audit.ramdisk_size_kib, 8192)
        self.assertEqual(rep_a.kemco_diff_keys, ("ramdisk_size", "initrd"))

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_a_fdt_parser_rejects_bad_magic_truncation_unaligned_unterminated_and_oob_strings(self) -> None:
        import struct as _st

        dtb_raw = DEFAULT_FX3_DTB_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(dtb_raw).hexdigest(), PINNED_CXD90057_DTB_SHA256)
        parsed = parse_fdt_blob(dtb_raw)
        self.assertEqual(parsed.header.version, 17)
        self.assertEqual(parsed.header.last_comp_version, 16)
        self.assertEqual(len(parsed.nodes), 68)

        # 1. Corrupted magic (`!= 0xd00dfeed`) -> rejected
        bad_magic = bytearray(dtb_raw)
        _st.pack_into(">I", bad_magic, 0, 0xDEADBEEF)
        with self.assertRaises(FdtFormatError):
            parse_fdt_blob(bytes(bad_magic))

        # 2. Truncated `totalsize` (file shorter than header `totalsize`) -> rejected
        with self.assertRaises(FdtFormatError):
            parse_fdt_blob(dtb_raw[:-16])

        # 3. Unaligned `off_dt_struct` (not 4-byte aligned) -> rejected
        bad_align = bytearray(dtb_raw)
        _st.pack_into(">I", bad_align, 8, 57)
        with self.assertRaises(FdtFormatError):
            parse_fdt_blob(bytes(bad_align))

        # 4. Unterminated `FDT_END` (`0x00000009` replaced with `FDT_NOP` `0x00000004`) -> rejected
        no_end = bytearray(dtb_raw)
        end_pos = parsed.header.off_dt_struct + parsed.header.size_dt_struct - 4
        self.assertEqual(_st.unpack_from(">I", no_end, end_pos)[0], 0x00000009)
        _st.pack_into(">I", no_end, end_pos, 0x00000004)
        with self.assertRaises(FdtFormatError):
            parse_fdt_blob(bytes(no_end))

        # 5. Out-of-bounds `nameoff` in first `FDT_PROP` -> rejected
        oob_str = bytearray(dtb_raw)
        # Root FDT_BEGIN_NODE is at off_dt_struct (56): token(4B) + ""\0 padded(4B) = 64; first FDT_PROP at 64
        self.assertEqual(_st.unpack_from(">I", oob_str, 64)[0], 0x00000003)
        _st.pack_into(">I", oob_str, 72, parsed.header.size_dt_strings + 64)
        with self.assertRaises(FdtFormatError):
            parse_fdt_blob(bytes(oob_str))

        # 6. Unterminated `/memreserve/` block -> rejected
        bad_rsv = bytearray(dtb_raw)
        _st.pack_into(">QQ", bad_rsv, parsed.header.off_mem_rsvmap, 0x400000000, 0x1000)
        with self.assertRaises(FdtFormatError):
            parse_fdt_blob(bytes(bad_rsv))

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_b_ko_vermagic_modversions_p9_integrity_and_cross_kernel_abi(self) -> None:
        rep_b = audit_kernel_module_compatibility()
        self.assertTrue(rep_b.all_checks_passed)
        self.assertEqual(rep_b.fx3_host_module_count, 9)
        self.assertEqual(rep_b.fx3_host_module_count, len(PINNED_FX3_HOST_KO_SHA256))
        self.assertTrue(rep_b.fx3_all_sha256_verified)
        self.assertTrue(rep_b.fx3_uniform_vermagic_verified)
        self.assertTrue(rep_b.fx3_depends_dag_closed)
        self.assertFalse(rep_b.sony_config_modversions_enabled)

        p9 = rep_b.p9_upm_integrity
        self.assertTrue(p9.valid)
        self.assertTrue(p9.rollback_sha256_matched)
        self.assertTrue(p9.vermagic_preserved)
        self.assertTrue(p9.modinfo_sha256_preserved)
        self.assertTrue(p9.this_module_sha256_preserved)
        self.assertTrue(p9.undef_symbols_preserved)
        self.assertTrue(p9.exported_symbols_preserved)
        self.assertTrue(p9.native_modversions_preserved)
        self.assertEqual(p9.synthetic_modversions_count, 61)
        self.assertTrue(p9.synthetic_modversions_100pct_preserved)

        # Quantify cross-kernel comparison: 7/9 ABI-identical, 2/9 (`backup.ko`, `upm.ko`) divergent, 8/9 p1 vermagic mismatch
        self.assertEqual(rep_b.identical_abi_module_count, 7)
        self.assertEqual(rep_b.divergent_abi_modules, ("backup.ko", "upm.ko"))
        self.assertEqual(rep_b.p1_vermagic_mismatch_count, 8)
        by_name = {c.module_filename: c for c in rep_b.cross_kernel_comparisons}
        self.assertEqual(
            by_name["backup.ko"].only_fx6_exports,
            ("Backup_sync_subsystem_for_senser_local",),
        )
        self.assertIn(
            "Backup_sync_subsystem_for_senser_local",
            by_name["upm.ko"].only_fx6_undef,
        )
        self.assertIn(
            "pcie_link_width_check_dev_state_ch0",
            by_name["upm.ko"].only_fx6_undef,
        )
        self.assertIn(
            "pcie_get_link_speed",
            by_name["upm.ko"].only_fx3_undef,
        )

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_b_ko_auditor_rejects_vermagic_mismatch_tampered_crc_malformed_modinfo_and_cli(self) -> None:
        upm_raw = (DEFAULT_FX3_MODULES_DIR / "upm.ko").read_bytes()
        p1_uipc_raw = (DEFAULT_FX6_P1_INITRD_DIR / "usr" / "kmod" / "osal_uipc.ko").read_bytes()

        # 1. Mismatched `vermagic` (`4.9.186-scel` vs `4.9.337-scel+`) -> rejected with KoModuleFormatError
        p1_audit = parse_and_audit_ko_module(p1_uipc_raw, "FX6_p1:osal_uipc.ko")
        self.assertEqual(p1_audit.vermagic, EXPECTED_P1_UPDATER_VERMAGIC)
        with self.assertRaises(KoModuleFormatError):
            parse_and_audit_ko_module(
                p1_uipc_raw,
                "FX6_p1:osal_uipc.ko",
                expected_vermagic=EXPECTED_HOST_VERMAGIC,
            )

        # 2. Tampered `module_layout` CRC in 64B `struct modversion_info` -> rejected
        modver_ko = inject_synthetic_modversions_section(
            upm_raw,
            [("module_layout", SYNTHETIC_MODULE_LAYOUT_CRC), ("printk", 0x1B7D4074)],
        )
        ok_mv = parse_and_audit_ko_module(
            modver_ko,
            "synth_modver.ko",
            expected_module_layout_crc=SYNTHETIC_MODULE_LAYOUT_CRC,
        )
        self.assertEqual(ok_mv.module_layout_crc, SYNTHETIC_MODULE_LAYOUT_CRC)
        self.assertEqual(len(ok_mv.modversions), 2)

        tampered_crc_ko = inject_synthetic_modversions_section(
            upm_raw,
            [("module_layout", SYNTHETIC_MODULE_LAYOUT_CRC ^ 0xFFFFFFFF), ("printk", 0x1B7D4074)],
        )
        with self.assertRaises(KoModuleFormatError):
            parse_and_audit_ko_module(
                tampered_crc_ko,
                "tampered_crc.ko",
                expected_module_layout_crc=SYNTHETIC_MODULE_LAYOUT_CRC,
            )

        # 3. Missing mandatory `module_layout` entry in `__versions` -> rejected
        no_layout_ko = inject_synthetic_modversions_section(
            upm_raw,
            [("printk", 0x1B7D4074)],
        )
        with self.assertRaises(KoModuleFormatError):
            parse_and_audit_ko_module(no_layout_ko, "no_layout.ko")

        # 4. Unaligned `__versions` section size (`65 B`, not a multiple of 64 B) -> rejected
        unaligned_ver_ko = inject_synthetic_modversions_section(
            upm_raw,
            [],
            raw_versions_override=b"\x00" * 65,
        )
        with self.assertRaises(KoModuleFormatError):
            parse_and_audit_ko_module(unaligned_ver_ko, "unaligned_versions.ko")

        # 5. Malformed `.modinfo` (corrupt `=` in `vermagic=` entry) -> rejected
        bad_modinfo = bytearray(upm_raw)
        vm_pos = bad_modinfo.find(b"vermagic=")
        self.assertGreater(vm_pos, 0)
        bad_modinfo[vm_pos + 8] = ord(":")  # replaces '=' with ':'
        with self.assertRaises(KoModuleFormatError):
            parse_and_audit_ko_module(bytes(bad_modinfo), "bad_modinfo.ko")

        # 6. End-to-end `run_kernel_dtb_verification()` & CLI `verify-kernel-dtb` subcommand
        full_rep = run_kernel_dtb_verification()
        self.assertTrue(full_rep.all_checks_passed)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-kernel-dtb"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "OK")
        self.assertTrue(payload["all_checks_passed"])
        self.assertTrue(payload["dtb_byte_identical"])
        self.assertTrue(payload["p9_upm_integrity_valid"])
        self.assertEqual(payload["dimension_a_dtb"]["fdt_node_count"], 68)
        self.assertEqual(payload["dimension_b_ko"]["fx3_host_module_count"], 9)


class TestPhase9StorageAndRamBudgetVerifier(unittest.TestCase):
    """Verify Phase 9 30-Partition Zero-Repartition Storage/p15 Footprint & Linux DDR/tmpfs Budget Verifier."""

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_a_30_partition_zero_repartition_mapping_spi_nor_and_p15_footprint(self) -> None:
        rep_a = audit_storage_topology_and_p15_budget()
        self.assertTrue(rep_a.all_checks_passed, rep_a.errors)
        self.assertTrue(rep_a.fx3_partinf_sha256_verified)
        self.assertTrue(rep_a.fx6_partinf_sha256_verified)
        self.assertTrue(rep_a.fx3_sector0_audit.valid)
        self.assertEqual(rep_a.fx3_sector0_audit.layout_profile, "FX3_PARTINF_205")
        self.assertTrue(rep_a.fx6_sector0_audit.valid)
        self.assertEqual(rep_a.fx6_sector0_audit.layout_profile, "FX6_PARTINF_601")

        # Exact UDA sector & MiB topology delta: 0x35E000 (1,724.00 MiB) vs 0x384400 (1,800.50 MiB, +76.50 MiB)
        self.assertEqual(rep_a.fx3_end_sector, EXPECTED_FX3_END_SECTOR)
        self.assertEqual(rep_a.fx3_total_uda_mib, 1724.0)
        self.assertEqual(rep_a.fx6_end_sector, EXPECTED_FX6_END_SECTOR)
        self.assertEqual(rep_a.fx6_total_uda_mib, 1800.5)
        self.assertEqual(rep_a.uda_delta_sectors, EXPECTED_UDA_DELTA_SECTORS)
        self.assertEqual(rep_a.uda_delta_mib, 76.5)
        self.assertEqual(rep_a.identical_prefix_partition_count, 11)
        self.assertEqual(len(rep_a.partition_mappings), 30)
        self.assertTrue(rep_a.all_30_partitions_mapped_zero_repartition)

        by_idx = {m.index: m for m in rep_a.partition_mappings}
        self.assertEqual(by_idx[15].mapping_strategy, "INDEX_MOUNTED_SAME_SIZE_500MIB")
        self.assertEqual(by_idx[18].mapping_strategy, "PRESERVE_FX3_STOCK_TIER0_LENS")
        self.assertEqual(by_idx[20].mapping_strategy, "REMAPPED_TO_FX3_P30_VIA_P1")
        self.assertEqual(by_idx[21].mapping_strategy, "REMAPPED_TO_TMPFS_VFAT_LOOPBACK_VIA_P2")
        self.assertEqual(by_idx[30].mapping_strategy, "ACTIVE_LUT_TARGET_FOR_FX6_P20")
        self.assertGreater(rep_a.p20_to_p30_lut_headroom_mib, 32.0)
        self.assertEqual(rep_a.p21_tmpfs_vfat_8m_bytes, 8 * 1024 * 1024)
        self.assertEqual(rep_a.p21_tmpfs_vfat_16m_bytes, 16 * 1024 * 1024)

        # Octal-SPI NOR pformat_config.txt & edisx.elf redline verification
        self.assertTrue(rep_a.spi_nor_audit.valid)
        self.assertEqual(len(rep_a.spi_nor_audit.entries), 6)
        self.assertFalse(rep_a.spi_nor_audit.has_overlaps)
        self.assertEqual(rep_a.spi_nor_audit.spi_nor_mutation_bytes, 0)
        self.assertTrue(rep_a.redline_audit.valid)
        self.assertTrue(rep_a.redline_audit.edisx_repartition_forbidden)
        self.assertTrue(rep_a.redline_audit.edisx_donor_sha256_verified)
        self.assertTrue(rep_a.redline_audit.edisx_identical_across_models)
        self.assertTrue(rep_a.redline_audit.edisx_has_blkrrpart_signature)
        self.assertEqual(rep_a.redline_audit.sector0_mutation_bytes, 0)

        # p15 (/usr) exact manifest, walk, and 4 KiB-block headroom checks against 500.00 MiB (524,288,000 B)
        p15 = rep_a.p15_footprint
        self.assertTrue(p15.valid)
        self.assertTrue(p15.manifest_sha256_verified)
        self.assertEqual(p15.manifest_entry_count, EXPECTED_NFLASH15_ENTRY_COUNT)
        self.assertEqual(p15.regular_file_count, EXPECTED_NFLASH15_REGULAR_FILES)
        self.assertEqual(p15.symlink_count, EXPECTED_NFLASH15_SYMLINKS)
        self.assertEqual(p15.total_directory_count, EXPECTED_NFLASH15_TOTAL_DIRS)
        self.assertTrue(p15.walk_cross_check_matched)
        self.assertEqual(p15.raw_payload_bytes, EXPECTED_NFLASH15_RAW_BYTES)
        self.assertEqual(p15.aligned_4k_payload_bytes, EXPECTED_NFLASH15_ALIGNED_4K_BYTES)
        self.assertEqual(p15.fx3_stock_p15_bytes, EXPECTED_FX3_P15_BYTES)
        self.assertTrue(p15.donor_ext2_image_present)
        self.assertTrue(p15.donor_ext2_magic_ok)
        self.assertEqual(p15.donor_ext2_image_bytes, EXPECTED_NFLASH15_EXT2_IMAGE_BYTES)
        self.assertGreater(p15.raw_headroom_bytes, 145_000_000)
        self.assertGreater(p15.squashfs_upper_headroom_bytes, 143_000_000)
        self.assertGreater(p15.ext4_ro_headroom_bytes, 130_000_000)
        self.assertGreater(p15.donor_ext2_image_headroom_bytes, 78_000_000)
        self.assertTrue(p15.p15_fits_stock_fx3)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_a_rejects_edisx_repartition_sector0_writes_and_over_budget_p15(self) -> None:
        # 1. Script invoking `edisx.elf /dev/nflasha partinf.conf` -> rejected immediately
        bad_edisx = audit_zero_repartition_redline(
            scripts=(("bad_mkfs.sh", "#!/bin/sh\nedisx.elf /dev/nflasha /tmp/partinf.conf\n"),)
        )
        self.assertFalse(bad_edisx.valid)
        self.assertIn("bad_mkfs.sh:edisx.elf", bad_edisx.forbidden_script_hits)

        # 2. Raw whole-eMMC `/dev/nflasha` `dd` write or staged `edisx.elf` binary -> rejected
        bad_dd = audit_zero_repartition_redline(
            scripts=(("bad_dd.sh", "dd if=/tmp/s0.bin of=/dev/nflasha bs=512 count=1\n"),),
            staged_binary_names=("bin/edisx.elf", "lib/appFw.so"),
        )
        self.assertFalse(bad_dd.valid)
        self.assertGreater(len(bad_dd.forbidden_script_hits), 0)
        self.assertEqual(bad_dd.forbidden_binary_hits, ("bin/edisx.elf",))

        # 3. Non-zero Sector-0 or SPI NOR mutation byte count -> rejected
        self.assertFalse(audit_zero_repartition_redline(sector0_mutation_bytes=512).valid)
        self.assertFalse(parse_and_audit_pformat_config(spi_nor_mutation_bytes=4096).valid)

        # 4. Over-budget `p15` payload (+150 MiB pushing total > 500.00 MiB) -> rejected
        over_p15 = audit_p15_usr_footprint(additional_payload_bytes=150 * 1024 * 1024)
        self.assertFalse(over_p15.valid)
        self.assertFalse(over_p15.p15_fits_stock_fx3)
        self.assertLess(over_p15.raw_headroom_bytes, 0)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_b_cxd90057_linux_ddr_pool_and_stage_a_tmpfs_ram_overlay_budgets(self) -> None:
        rep_b = audit_ddr_and_tmpfs_ram_budget()
        self.assertTrue(rep_b.all_checks_passed, rep_b.errors)
        self.assertEqual(rep_b.soc_dtb_memory_base, 0x400000000)
        self.assertEqual(rep_b.soc_dtb_total_ddr_bytes, 8 * 1024 * 1024 * 1024)
        self.assertEqual(rep_b.kemco_mem_limit_bytes, 2 * 1024 * 1024 * 1024)
        self.assertEqual(rep_b.kemco_carveout_count, 7)
        self.assertEqual(rep_b.total_memrsv_carveout_bytes, 136_712_192)
        self.assertEqual(rep_b.net_linux_managed_ddr_bytes, 2_010_771_456)
        self.assertEqual(rep_b.ram_shadow_bk4_bytes, 20_588)
        self.assertEqual(rep_b.safe_stage_a_tmpfs_ceiling_bytes, DEFAULT_SAFE_STAGE_A_TMPFS_CEILING_BYTES)
        self.assertTrue(rep_b.ram_budget_within_safe_bounds)

        # Verify all 11 required Stage-A overlay components are accounted for
        self.assertEqual(len(rep_b.components_8m), 11)
        comp_names = {c.name for c in rep_b.components_8m}
        for req_name in (
            "lib/appFw.so",
            "lib/libInfraSetupFile.so",
            "lib/libInfraMediaCommon.so",
            "lib/libInfraMediaConfig.so",
            "lib/libInfraKikiLogGenerator.so",
            "lib/libInfraAppRemoteBoard.so",
            "lib/libfan.so",
            "modules/upm.ko",
            "images/opelog.vfat",
            "nvram/Backup_ram_shadow.bin",
            "etc/fx6_overlay/stage_a_control.cpio",
        ):
            self.assertIn(req_name, comp_names)

        # Verify both streaming unpack and peak-buffer unpack across 8 MiB & 16 MiB VFAT modes
        by_sc = {sc.scenario_id: sc for sc in rep_b.scenarios}
        self.assertEqual(len(by_sc), 4)
        s8_stream = by_sc["STAGE_A_8M_STREAMING"]
        s8_peak = by_sc["STAGE_A_8M_PEAK_BUFFER"]
        s16_stream = by_sc["STAGE_A_16M_STREAMING"]
        s16_peak = by_sc["STAGE_A_16M_PEAK_BUFFER"]

        for sc in rep_b.scenarios:
            self.assertTrue(sc.within_safe_bounds)
            self.assertGreater(sc.headroom_vs_safe_ceiling_bytes, 120 * 1024 * 1024)
            self.assertLess(sc.share_of_linux_memtotal_pct, 8.0)

        self.assertLess(s8_stream.peak_tmpfs_bytes, s8_peak.peak_tmpfs_bytes)
        self.assertLess(s16_stream.peak_tmpfs_bytes, s16_peak.peak_tmpfs_bytes)
        self.assertEqual(
            s16_stream.steady_state_tmpfs_bytes - s8_stream.steady_state_tmpfs_bytes,
            8 * 1024 * 1024,
        )

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_b_rejects_over_budget_tmpfs_overlay_cli_and_clean_room_hygiene_runner(self) -> None:
        import importlib.util

        # 1. Injecting +200 MiB overlay payload causes peak-buffer (and streaming) to exceed 256 MiB safe tmpfs ceiling
        over_ram = audit_ddr_and_tmpfs_ram_budget(extra_overlay_bytes=200 * 1024 * 1024)
        self.assertFalse(over_ram.all_checks_passed)
        self.assertFalse(over_ram.ram_budget_within_safe_bounds)

        # 2. Full Phase 9 end-to-end report & `verify-storage-ram-budget` CLI subcommand
        full_rep = run_storage_and_ram_budget_verification()
        self.assertTrue(full_rep.all_checks_passed)
        self.assertTrue(full_rep.edisx_repartition_forbidden)
        self.assertEqual(full_rep.sector0_mutation_bytes, 0)
        self.assertTrue(full_rep.p15_fits_stock_fx3)
        self.assertTrue(full_rep.ram_budget_within_safe_bounds)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-storage-ram-budget"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "OK")
        self.assertTrue(payload["all_checks_passed"])
        self.assertTrue(payload["edisx_repartition_forbidden"])
        self.assertEqual(payload["sector0_mutation_bytes"], 0)
        self.assertTrue(payload["p15_fits_stock_fx3"])
        self.assertTrue(payload["ram_budget_within_safe_bounds"])
        self.assertEqual(len(payload["dimension_a_storage"]["partition_mappings"]), 30)
        self.assertEqual(len(payload["dimension_b_ddr_tmpfs"]["scenarios"]), 4)

        # 3. Verify `scripts/run_all_lab_tests.py` clean-room porcelain parser & live repo hygiene
        repo_root = Path(__file__).resolve().parents[3]
        runner_path = repo_root / "scripts" / "run_all_lab_tests.py"
        spec = importlib.util.spec_from_file_location("run_all_lab_tests", runner_path)
        assert spec is not None and spec.loader is not None
        runner_mod = importlib.util.module_from_spec(spec)
        import sys as _sys
        _sys.modules["run_all_lab_tests"] = runner_mod
        spec.loader.exec_module(runner_mod)

        synth_porcelain = (
            " M scripts/export_orca_conversations.mjs\n"
            "?? outputs/fx6-on-fx3-closure/fx6_closure/new_mod.py\n"
            "?? outputs/fx6-on-fx3-closure/leaked.so\n"
            "?? tmp_overlay.cpio\n"
            "A  staged_module.ko\n"
            "?? __pycache__/foo.cpython-39.pyc\n"
        )
        hits = runner_mod.parse_git_porcelain_for_forbidden_artifacts(synth_porcelain)
        self.assertEqual(
            hits,
            (
                "__pycache__/foo.cpython-39.pyc",
                "outputs/fx6-on-fx3-closure/leaked.so",
                "staged_module.ko",
                "tmp_overlay.cpio",
            ),
        )
        live_hygiene = runner_mod.audit_clean_room_hygiene(repo_root=repo_root)
        self.assertTrue(live_hygiene.clean, live_hygiene.errors)


class TestPhase10CpRtosCompatibilityVerifier(unittest.TestCase):
    """Verify Phase 10 Blueprint `U2` CP RTOS (`cpapp-b.bin`) & `nflasha8` (`tomco.txt`) Compatibility Verifier."""

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_a_tomco_cross_model_shared_memcfg_and_ipc_contract(self) -> None:
        fx3_rt_raw = DEFAULT_FX3_RUNTIME_TOMCO_PATH.read_bytes()
        fx6_rt_raw = (DEFAULT_FX6_NFLASHA8_DIR / "tomco.txt").read_bytes()
        fx3_up_raw = (DEFAULT_FX3_UPDATER_CP_DIR / "tomco.txt").read_bytes()

        tomco_audit = compare_tomco_configs(
            fx3_runtime_bytes=fx3_rt_raw,
            fx6_runtime_bytes=fx6_rt_raw,
            fx3_updater_bytes=fx3_up_raw,
        )
        self.assertTrue(tomco_audit.valid, tomco_audit.errors)
        self.assertTrue(tomco_audit.runtime_memcfg_identical)
        self.assertTrue(tomco_audit.shared_ipc_telemetry_keys_identical)
        self.assertEqual(tomco_audit.identical_key_count, 20)
        self.assertEqual(len(REQUIRED_IDENTICAL_IPC_AND_TELEMETRY_KEYS), 20)
        self.assertEqual(len(tomco_audit.fx3_runtime.memcfg_regions), 4)
        self.assertEqual(len(tomco_audit.fx6_runtime.memcfg_regions), 4)
        self.assertEqual(tomco_audit.fx3_runtime.total_memcfg_bytes, 1_807_745_024)
        self.assertEqual(tomco_audit.fx6_runtime.total_memcfg_bytes, 1_807_745_024)
        self.assertTrue(tomco_audit.fx3_runtime.memcfg_pairwise_non_overlapping)
        self.assertTrue(tomco_audit.fx6_runtime.memcfg_pairwise_non_overlapping)
        self.assertEqual(
            tuple((r.base_addr, r.size_bytes, r.cache_attr) for r in tomco_audit.fx6_runtime.memcfg_regions),
            EXPECTED_RUNTIME_MEMCFG_SPEC,
        )
        self.assertEqual(
            tomco_audit.fx6_only_keys,
            ("exception_reboot", "mpcp_exception_stop", "xreset_req_port_bit", "xreset_req_port_ch"),
        )
        self.assertIn("reset_req_int_cfg", tomco_audit.fx3_only_keys)
        self.assertIn("snapshotdbg_addr", tomco_audit.fx3_only_keys)
        self.assertTrue(tomco_audit.updater_memcfg_delta_documented)

        # Malformed or overlapping [TOMCO] input must fail closed with TomcoFormatError
        with self.assertRaises(TomcoFormatError):
            parse_tomco_txt(b"memcfg=0x400000@0x04C00000:uc\n", source_label="missing_header")
        with self.assertRaises(TomcoFormatError):
            parse_tomco_txt(
                b"[TOMCO]\nmemcfg=0x400000@0x04C00000:uc\nmemcfg=0x100000@0x04F00000:uc\n",
                source_label="overlapping_memcfg",
            )
        with self.assertRaises(TomcoFormatError):
            parse_tomco_txt(
                b"[TOMCO]\nwdt_on=1\nwdt_on=0\nmemcfg=0x400000@0x04C00000:uc\n",
                source_label="conflicting_duplicate_key",
            )

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_b_nflasha8_artifacts_arm32_startup_and_bank1_spi_nor_contracts(self) -> None:
        rep = run_cp_rtos_compatibility_verification()
        self.assertTrue(rep.all_checks_passed)
        self.assertTrue(rep.u2_closed)
        self.assertTrue(rep.fx3_udtrcp_verified)
        self.assertEqual(len(rep.nflasha8_artifacts), 9)
        self.assertEqual(len(EXPECTED_FX6_NFLASHA8_ARTIFACTS), 9)
        for rec in rep.nflasha8_artifacts:
            self.assertTrue(rec.matched, f"Mismatch on nflasha8/{rec.name}")

        arm = rep.arm32_startup_audit
        self.assertTrue(arm.valid, arm.errors)
        self.assertEqual(
            arm.entry_words_hex,
            tuple(f"0x{w:08x}" for w in EXPECTED_CP_ARM32_ENTRY_WORDS),
        )
        self.assertEqual(arm.derived_load_base, f"0x{CP_LOCAL_LOAD_BASE:08x}")
        self.assertEqual(arm.first_branch_target, f"0x{CP_FIRST_BRANCH_TARGET:08x}")
        self.assertTrue(arm.embedded_vector_pointers_in_range)
        self.assertEqual(arm.fx3_cp_ref_bytes, EXPECTED_FX3_CP_REF_BYTES)
        self.assertEqual(arm.fx3_cp_ref_sha256, EXPECTED_FX3_CP_REF_SHA256)
        self.assertEqual(arm.cp_size_delta_bytes, 1_972_248)
        self.assertEqual(arm.identical_prefix_bytes, EXPECTED_CP_IDENTICAL_PREFIX_BYTES)
        self.assertTrue(arm.bank1_tomco_addr_matched)
        self.assertTrue(arm.bank1_cpapp_addr_matched)
        self.assertTrue(arm.spi_nor_cpapp_offset_matched)
        self.assertEqual(CP_BANK1_BUS_LOAD_ADDR, TOMCO_BANK1_BUS_LOAD_ADDR + TOMCO_BANK1_SPAN_BYTES)
        self.assertEqual(arm.fx3_dmmcfg_bytes, 43_320)
        self.assertEqual(arm.fx6_dmmcfg_bytes, 41_552)
        self.assertEqual(arm.dmmcfg_size_delta_bytes, -1_768)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_c_fx6_cpapp_peripheral_hazard_markers_and_stock_cp_rationale(self) -> None:
        fx6_cp_raw = (DEFAULT_FX6_NFLASHA8_DIR / "cpapp-b.bin").read_bytes()
        markers_audit = scan_fx6_cp_peripheral_markers(fx6_cp_raw)
        self.assertTrue(markers_audit.valid, markers_audit.errors)
        self.assertEqual(markers_audit.total_pinned_markers, len(PINNED_FX6_CP_PERIPHERAL_MARKERS))
        self.assertEqual(markers_audit.verified_marker_count, 13)
        self.assertEqual(markers_audit.fx6_exclusive_hazard_count, 8)
        self.assertEqual(markers_audit.category_counts["darwin_electronic_nd"], 4)
        self.assertEqual(markers_audit.category_counts["mew_sdi_genlock_fpga"], 4)
        self.assertEqual(markers_audit.category_counts["fan_thermal_control"], 2)
        self.assertEqual(markers_audit.category_counts["toppers_fmp_rtos"], 1)
        self.assertEqual(markers_audit.category_counts["uipc_dmm_backup_ipc"], 2)

        # Mutating one byte at a pinned Darwin ND marker offset must fail closed
        corrupted_cp = bytearray(fx6_cp_raw)
        corrupted_cp[0xE7F83A] ^= 0xFF
        bad_scan = scan_fx6_cp_peripheral_markers(bytes(corrupted_cp))
        self.assertFalse(bad_scan.valid)
        self.assertEqual(bad_scan.verified_marker_count, 12)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_d_stage_a_stock_cp_redline_rejections_and_cli_subcommand(self) -> None:
        # 1. Valid Stage-A bundle passes Stock-CP Redline (`p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`)
        bundle = build_stage_a_ram_overlay_package()
        ok_redline = validate_candidate_cp_redline(
            overlay_manifest=bundle.overlay_manifest,
            overlay_entry_paths=tuple(e.name for e in bundle.cpio_audit.entries),
            scripts_to_audit=(
                ("setup_fx6_compat.sh", bundle.setup_compat_script),
                ("init2_guard.sh", bundle.init2_guard_script),
            ),
        )
        self.assertTrue(ok_redline.valid, ok_redline.violations)
        self.assertTrue(ok_redline.p8_cp_mutation_forbidden)
        self.assertEqual(ok_redline.cp_mutation_bytes, 0)

        # 2. Candidate manifest targeting `p8` / `nflasha8` or disabling `p8_cp_mutation_forbidden` -> rejected!
        bad_manifest_1 = validate_candidate_cp_redline(
            overlay_manifest={"target_flash_partitions": ["p8"], "cp_mutation_bytes": 17952816}
        )
        self.assertFalse(bad_manifest_1.valid)
        self.assertFalse(bad_manifest_1.p8_cp_mutation_forbidden)
        self.assertGreaterEqual(len(bad_manifest_1.violations), 2)

        bad_manifest_2 = validate_candidate_cp_redline(
            overlay_manifest={"p8_cp_mutation_forbidden": False}
        )
        self.assertFalse(bad_manifest_2.valid)

        # 3. Overlay archive staging `/cp/cpapp-b.bin` or `/cp/tomco.txt` -> rejected!
        bad_paths = validate_candidate_cp_redline(
            overlay_entry_paths=("lib/appFw.so", "cp/cpapp-b.bin", "cp/tomco.txt")
        )
        self.assertFalse(bad_paths.valid)
        self.assertEqual(len(bad_paths.violations), 2)

        # 4. Active script attempting `dd` or `mount --bind` on `/dev/nflasha8` or `cpapp-b.bin` -> rejected!
        bad_script = validate_candidate_cp_redline(
            scripts_to_audit=(
                ("bad_cp_flash.sh", "#!/bin/sh\n# safe comment\ndd if=/tmp/cpapp-b.bin of=/dev/nflasha8 bs=4096\n"),
            )
        )
        self.assertFalse(bad_script.valid)
        self.assertGreaterEqual(len(bad_script.violations), 2)

        # 5. CLI `verify-cp-rtos` subcommand check
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-cp-rtos"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "OK")
        self.assertTrue(payload["all_checks_passed"])
        self.assertTrue(payload["u2_closed"])
        self.assertTrue(payload["p8_cp_mutation_forbidden"])
        self.assertEqual(payload["cp_mutation_bytes"], 0)
        self.assertEqual(len(payload["nflasha8_artifacts"]), 9)
        self.assertTrue(payload["tomco_audit"]["runtime_memcfg_identical"])
        self.assertEqual(payload["peripheral_marker_audit"]["verified_marker_count"], 13)


class TestPhase11P1RecoveryBridgeAndByofManifest(unittest.TestCase):
    """Phase 11: Cross-package `p1` recovery & Tier-0 bridge + BYOF SHA-256 manifest auditor."""

    def test_dimension_a_tier0_and_fx3_recovery_readonly_alignment(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        dim_a = verify_tier0_fx3_recovery_alignment(repo_root=repo_root)
        self.assertTrue(dim_a.valid, dim_a.errors)
        self.assertEqual(dim_a.boot_unit_bytes, 131_072)
        self.assertEqual(dim_a.boot_max_bytes, 33_423_360)
        self.assertEqual(dim_a.boot_major_minor_b0, (252, 126))
        self.assertEqual(dim_a.boot_major_minor_b1, (252, 127))
        self.assertEqual(dim_a.p1_exact_bytes, 25_100_288)
        self.assertEqual(dim_a.p1_chunk_count, 383)
        self.assertEqual(dim_a.p1_window_counts, (128, 128, 127))
        self.assertTrue(dim_a.devno_ko_profile_hash_matched)
        self.assertTrue(dim_a.cnflasha1_nflasha1_symlink_contract_verified)
        self.assertEqual(dim_a.twopass_capture_local_sha256, dim_a.assembled_p1_worker_sha256)
        self.assertTrue(dim_a.tier0_manifest_11_items_valid)
        self.assertTrue(dim_a.tier0_syscall_trace_valid)
        self.assertTrue(dim_a.non_deployment_flags_aligned)
        self.assertEqual(len(dim_a.workers_audited), 3)
        for cw in dim_a.workers_audited:
            self.assertTrue(cw.valid)
            self.assertEqual(cw.chunk_bytes, 65_536)
            self.assertTrue(cw.rd_is_strictly_readonly)
            self.assertTrue(cw.rd_carries_nofollow_and_cloexec)
            self.assertTrue(cw.wr_carries_creat_excl_no_trunc)
            self.assertTrue(cw.kstat_128b_assert_present)

        # Fail-closed anomaly 1: Tier-0 / fx3_recovery p1 size mismatch
        bad_size = verify_tier0_fx3_recovery_alignment(
            repo_root=repo_root,
            inject_tier0_size_mismatch=True,
        )
        self.assertFalse(bad_size.valid)
        self.assertFalse(bad_size.tier0_manifest_11_items_valid)

        # Fail-closed anomaly 2: Source write flag on /dev/cnflasha1 rejected by Tier-0 syscall auditor
        bad_flag = verify_tier0_fx3_recovery_alignment(
            repo_root=repo_root,
            inject_worker_write_flag=True,
        )
        self.assertFalse(bad_flag.valid)
        self.assertFalse(bad_flag.tier0_syscall_trace_valid)

        # Fail-closed anomaly 3: C worker source carrying O_RDWR (0x2) or O_TRUNC (0x200) rejected
        with tempfile.TemporaryDirectory(prefix="bad_c_worker_") as tmp_s:
            bad_c = Path(tmp_s) / "bad_worker.c"
            bad_c.write_text(
                "enum { AT_FDCWD = -100, RD = 0xA0002, NEW = 0xA02C1, BLOCK = 65536 };\n"
                "int check_kstat[sizeof(struct kstat) == 128 ? 1 : -1];\n",
                encoding="utf-8",
            )
            bad_c_audit = audit_worker_c_source_posture(
                "bad_worker",
                bad_c,
                rd_const_name="RD",
                wr_const_name="NEW",
                chunk_const_name="BLOCK",
                repo_root=Path(tmp_s),
            )
            self.assertFalse(bad_c_audit.valid)
            self.assertFalse(bad_c_audit.rd_is_strictly_readonly)
            self.assertFalse(bad_c_audit.wr_carries_creat_excl_no_trunc)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_dimension_b_fx6_p1_vfat_squashfs_checksum_and_u5_sticky_free_exit(self) -> None:
        dim_b = verify_p1_container_and_u5_handoff()
        self.assertTrue(dim_b.valid, dim_b.errors)
        self.assertEqual(dim_b.fat_sector_bytes, 512)
        self.assertEqual(dim_b.fat_cluster_sectors, 32)
        self.assertEqual(dim_b.fat_clusters, 1015)
        self.assertTrue(dim_b.p1chksum_md5_verified)
        self.assertTrue(dim_b.dtb_matches_fx3_canonical)
        self.assertTrue(dim_b.loadaddr_matches_fx3_canonical)
        self.assertEqual(dim_b.squashfs_inodes, 342)
        self.assertEqual(dim_b.squashfs_fragments, 45)
        self.assertEqual(dim_b.squashfs_block_size, 131_072)
        self.assertTrue(dim_b.iamupdater_marker_present)
        self.assertTrue(dim_b.fx3_profile_rejected_on_fx6_p1)
        self.assertTrue(dim_b.shared_updatercorecommon_matched)
        self.assertTrue(dim_b.common_src_matched_u5)
        self.assertTrue(dim_b.up_sh_matched_u5)
        self.assertTrue(dim_b.ud_send_lsi_matched_u5)
        self.assertTrue(dim_b.setup_nflash_symlink_script_verified)
        self.assertTrue(dim_b.teardown_scripts_verified)
        self.assertEqual(dim_b.ud_send_lsi_mode0_main_case.return_value, 0)
        self.assertEqual(dim_b.ud_send_lsi_mode0_main_case.emitted_payload_hex, "00000000")
        self.assertTrue(dim_b.partial_mode_only_sticky_detected)
        self.assertTrue(dim_b.partial_lsi_only_sticky_detected)
        self.assertTrue(dim_b.full_two_step_bank0_handoff.valid)
        self.assertFalse(dim_b.full_two_step_bank0_handoff.sticky_updater_risk)

        # Fail-closed anomaly 1: Corrupted /p1chksum rejected by fx3_recovery.engine.checksum_pair
        bad_chk = verify_p1_container_and_u5_handoff(tamper_p1_checksum=True)
        self.assertFalse(bad_chk.valid)
        self.assertFalse(bad_chk.p1chksum_md5_verified)

        # Fail-closed anomaly 2: Incomplete U5 teardown (sticky mode file left behind) rejected
        bad_u5 = verify_p1_container_and_u5_handoff(incomplete_u5_teardown=True)
        self.assertFalse(bad_u5.valid)
        self.assertTrue(bad_u5.full_two_step_bank0_handoff.sticky_updater_risk)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_cli_verify_p1_recovery_bridge_subcommand(self) -> None:
        rep = run_p1_recovery_bridge_verification()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertTrue(rep.p1_recovery_bridge_ok)
        self.assertTrue(rep.tier0_alignment.valid)
        self.assertTrue(rep.p1_container_and_u5_handoff.valid)

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-p1-recovery-bridge"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "OK")
        self.assertTrue(payload["all_checks_passed"])
        self.assertTrue(payload["p1_recovery_bridge_ok"])
        self.assertTrue(payload["tier0_alignment"]["valid"])
        self.assertTrue(payload["p1_container_and_u5_handoff"]["valid"])

    def test_phase11_byof_manifest_verifier_live_clean_room_and_tamper_detection(self) -> None:
        import importlib.util
        import sys as _sys

        repo_root = Path(__file__).resolve().parents[3]
        script_path = repo_root / "scripts" / "verify_byof_manifest.py"
        spec = importlib.util.spec_from_file_location("verify_byof_manifest", script_path)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        byof_mod = importlib.util.module_from_spec(spec)
        _sys.modules["verify_byof_manifest"] = byof_mod
        spec.loader.exec_module(byof_mod)

        # 1. Clean-room clone simulation (zero Sony firmware required) -> CLEAN_ROOM_SCHEMA_VERIFIED (rc=0)
        clean_rep = byof_mod.verify_byof_manifest(
            repo_root=repo_root,
            simulate_clean_clone=True,
        )
        self.assertTrue(clean_rep.all_checks_passed, clean_rep.errors)
        self.assertEqual(clean_rep.verification_mode, "CLEAN_ROOM_SCHEMA_VERIFIED")
        self.assertEqual(clean_rep.en_entry_count, 57)
        self.assertEqual(clean_rep.zh_entry_count, 57)
        self.assertTrue(clean_rep.en_zh_parity_ok)
        self.assertTrue(clean_rep.code_constants_ok)
        self.assertGreaterEqual(clean_rep.code_constants_checked, 46)
        self.assertTrue(clean_rep.zero_stage_reference_ok)

        # 2. Live donor verification when local donor tree exists on workstation
        live_rep = byof_mod.verify_byof_manifest(repo_root=repo_root)
        self.assertTrue(live_rep.all_checks_passed, live_rep.errors)
        if live_rep.donor_root_present:
            self.assertEqual(live_rep.verification_mode, "LOCAL_DONOR_VERIFIED")
            self.assertEqual(live_rep.live_donor_files_verified, 54)
        else:
            self.assertEqual(live_rep.verification_mode, "CLEAN_ROOM_SCHEMA_VERIFIED")

        # 3. Fail-closed detection on tampered BYOF markdown (EN/ZH drift, bad hex, stage* leak)
        good_md = (repo_root / "docs" / "BYOF-REPRODUCTION.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="byof_manifest_test_") as tmp_s:
            tmp_dir = Path(tmp_s)

            # 3a. Corrupt only the first occurrence of libfan.so SHA-256 -> EN/ZH mismatch + constant drift
            drift_md = good_md.replace(
                "d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850",
                "0" * 64,
                1,
            )
            drift_doc = tmp_dir / "drift.md"
            drift_doc.write_text(drift_md, encoding="utf-8")
            drift_rep = byof_mod.verify_byof_manifest(
                doc_path=drift_doc,
                repo_root=repo_root,
                simulate_clean_clone=True,
            )
            self.assertFalse(drift_rep.all_checks_passed)
            self.assertFalse(drift_rep.en_zh_parity_ok)
            self.assertFalse(drift_rep.code_constants_ok)

            # 3b. Inject invalid SHA-256 syntax & forbidden `stage47` reference -> rejected!
            bad_syntax_md = good_md.replace(
                "b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357",
                "NOT_A_VALID_SHA256",
            ) + "\nForbidden reference: stage47-leak\n"
            bad_doc = tmp_dir / "bad.md"
            bad_doc.write_text(bad_syntax_md, encoding="utf-8")
            bad_rep = byof_mod.verify_byof_manifest(
                doc_path=bad_doc,
                repo_root=repo_root,
                simulate_clean_clone=True,
            )
            self.assertFalse(bad_rep.all_checks_passed)
            self.assertFalse(bad_rep.zero_stage_reference_ok)


class TestPhase12StageABootOrchestratorAndWbiRedline(unittest.TestCase):
    """Verify Phase 12 `nflasha3-initrd` boot-chain audit, WBI (`p5`) redline, and 6-scenario `/bin/sh` orchestrator."""

    def test_dimension_a_initrd_boot_chain_and_wbi2_header_audit_live_and_clean_room(self) -> None:
        # 1. Live donor mode (or automatic pinned fallback)
        live_audit = audit_initrd_boot_chain_and_wbi_contracts()
        self.assertTrue(live_audit.valid, live_audit.errors)
        self.assertEqual(len(live_audit.artifacts), len(PINNED_INITRD_AND_BOOT_ARTIFACTS))
        self.assertEqual(live_audit.insmod_drv1_modules, EXPECTED_INSMOD_DRV1_ORDER)
        self.assertEqual(live_audit.insmod_drv2_module_count, EXPECTED_INSMOD_DRV2_TOTAL_COUNT)
        self.assertEqual(live_audit.upm_ko_insmod_drv2_slot, EXPECTED_INSMOD_DRV2_UPM_ONE_BASED_SLOT)
        self.assertTrue(live_audit.upm_ko_absent_from_initrd)
        self.assertTrue(live_audit.p15_usr_mounted_readonly)
        self.assertTrue(live_audit.p5_wbi_absent_from_fstab)
        self.assertTrue(live_audit.tmp_wbshd_tmpfs_mounted)
        self.assertTrue(live_audit.bis_mode_formats_p11_log)
        self.assertTrue(live_audit.bootin_hands_off_to_im_elf)
        self.assertTrue(live_audit.im_elf_references_sys_power_state)
        self.assertTrue(live_audit.fx3_uses_p7_setup_rootfs_pivot)
        self.assertTrue(live_audit.fx6_runs_init2_from_ram0)

        wbi = live_audit.wbi2_header
        self.assertTrue(wbi.valid, wbi.errors)
        self.assertEqual(wbi.magic_ascii, "WBI2")
        self.assertEqual(wbi.image_bytes, PINNED_FX6_WBI_NFLASH5_BYTES)
        self.assertEqual(wbi.image_sha256, PINNED_FX6_WBI_NFLASH5_SHA256)
        self.assertEqual(wbi.section_count, EXPECTED_FX6_WBI_SECTION_COUNT)
        self.assertEqual(wbi.resume_vector_hex, hex(EXPECTED_FX6_WBI_RESUME_VECTOR))
        self.assertEqual(wbi.r_data_bytes, EXPECTED_FX6_WBI_R_DATA_BYTES)
        self.assertEqual(wbi.o_data_bytes, EXPECTED_FX6_WBI_O_DATA_BYTES)
        self.assertEqual(wbi.wbimem_collision_delta_bytes, EXPECTED_WBIMEM_COLLISION_DELTA_BYTES)
        self.assertEqual(wbi.fx3_stock_wbi_sha256, PINNED_FX3_STOCK_WBI_SHA256)

        # 2. Clean-room simulation mode (zero proprietary Sony firmware required)
        clean_audit = audit_initrd_boot_chain_and_wbi_contracts(simulate_clean_room=True)
        self.assertTrue(clean_audit.valid, clean_audit.errors)
        self.assertEqual(clean_audit.verification_mode, "CLEAN_ROOM_PINNED_CONTRACT")
        self.assertEqual(clean_audit.artifact_count_verified, len(PINNED_INITRD_AND_BOOT_ARTIFACTS))
        self.assertTrue(all(not a.live_present for a in clean_audit.artifacts))

        # 3. WBI2 header binary parser negative rejections (invalid `"invl"` magic, truncated header, oversize image)
        import struct as _st

        canonical_hdr88 = _st.pack(
            "<4sI10Q",
            b"WBI2",
            0,
            EXPECTED_FX6_WBI_SECTION_COUNT,
            0,
            EXPECTED_FX6_WBI_RESUME_VECTOR,
            0x20060224,
            512,
            EXPECTED_FX6_WBI_R_DATA_BYTES,
            0,
            0,
            0x15400,
            EXPECTED_FX6_WBI_O_DATA_BYTES,
        )
        ok_hdr = parse_wbi2_header_bytes(
            canonical_hdr88,
            image_bytes=PINNED_FX6_WBI_NFLASH5_BYTES,
            image_sha256=PINNED_FX6_WBI_NFLASH5_SHA256,
        )
        self.assertTrue(ok_hdr.valid, ok_hdr.errors)

        invl_hdr = b"invl" + canonical_hdr88[4:]
        self.assertFalse(
            parse_wbi2_header_bytes(
                invl_hdr,
                image_bytes=PINNED_FX6_WBI_NFLASH5_BYTES,
                image_sha256=PINNED_FX6_WBI_NFLASH5_SHA256,
            ).valid
        )
        self.assertFalse(
            parse_wbi2_header_bytes(
                canonical_hdr88[:40],
                image_bytes=PINNED_FX6_WBI_NFLASH5_BYTES,
                image_sha256=PINNED_FX6_WBI_NFLASH5_SHA256,
            ).valid
        )

    def test_wbi_p5_hibernation_safety_redline_positive_and_hazard_rejections(self) -> None:
        orch_script = generate_stage_a_boot_orchestrator_script()
        bundle = build_stage_a_ram_overlay_package(synthetic_clean_room=_is_clean_room_or_donor_missing())
        cpio_entry_names = tuple(e.name for e in bundle.cpio_audit.entries)

        ok_redline = validate_candidate_wbi_redline(
            overlay_manifest=bundle.overlay_manifest,
            overlay_entry_paths=cpio_entry_names,
            scripts_to_audit=(
                ("setup_fx6_compat.sh", bundle.setup_compat_script),
                ("init2_guard.sh", bundle.init2_guard_script),
                ("30-stage-a-orchestrator.sh", orch_script),
            ),
        )
        self.assertTrue(ok_redline.valid, ok_redline.violations)
        self.assertTrue(ok_redline.wbi_p5_write_and_hibernation_forbidden)
        self.assertEqual(ok_redline.wbi_mutation_bytes, 0)

        # Reject 1: Forbidden `ud_wbi_drop` or `nflasha5` in CPIO paths
        bad_cpio = validate_candidate_wbi_redline(
            overlay_manifest=bundle.overlay_manifest,
            overlay_entry_paths=cpio_entry_names + ("usr/bin/ud_wbi_drop.elf",),
            scripts_to_audit=(("30-stage-a-orchestrator.sh", orch_script),),
        )
        self.assertFalse(bad_cpio.valid)

        # Reject 2: Direct `/dev/nflasha5` dd write or `/sys/power/state` hibernation trigger
        bad_script = validate_candidate_wbi_redline(
            overlay_manifest=bundle.overlay_manifest,
            overlay_entry_paths=cpio_entry_names,
            scripts_to_audit=(
                (
                    "30-stage-a-orchestrator.sh",
                    orch_script + "\necho disk > /sys/power/state\ndd if=/dev/zero of=/dev/nflasha5 bs=512 count=1\n",
                ),
            ),
        )
        self.assertFalse(bad_script.valid)

        # Reject 3: `setup_bis` `mkdosfs /dev/nflasha11` or `warm.mode=2` cross-session resume
        bad_bis = validate_candidate_wbi_redline(
            overlay_manifest=bundle.overlay_manifest,
            overlay_entry_paths=cpio_entry_names,
            scripts_to_audit=(("evil.sh", "mkdosfs /dev/nflasha11\nwarm.mode=2\n"),),
        )
        self.assertFalse(bad_bis.valid)

    def test_formal_state_machine_and_all_six_sandbox_scenarios(self) -> None:
        # 1. Deterministic state-machine transitions across all 6 branches
        sm_cold = simulate_orchestrator_state_machine(arm_token_present=False)
        self.assertEqual(sm_cold.boot_branch, "STOCK_FX3")
        self.assertEqual(sm_cold.lingering_mounts, 0)

        sm_reentry = simulate_orchestrator_state_machine(arm_token_present=True, reentry_lock_present=True)
        self.assertEqual(sm_reentry.boot_branch, "REENTRY_BLOCKED")
        self.assertEqual(sm_reentry.diag_code_prefix, "ERR_IDEMPOTENT_REENTRY_BLOCKED")
        self.assertTrue(sm_reentry.double_mount_prevented)

        sm_bis = simulate_orchestrator_state_machine(arm_token_present=True, upm_bootmode="BIS")
        self.assertEqual(sm_bis.boot_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sm_bis.diag_code_prefix, "ERR_WBI_BIS_MODE_FORBIDDEN")
        self.assertEqual(sm_bis.forward_steps_executed, ())

        sm_sha = simulate_orchestrator_state_machine(arm_token_present=True, payload_sha256_valid=False)
        self.assertEqual(sm_sha.boot_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sm_sha.forward_steps_executed, ())

        sm_mid = simulate_orchestrator_state_machine(
            arm_token_present=True, fail_at_step_id="06_bind_ro_libInfraMediaConfig_so"
        )
        self.assertEqual(sm_mid.boot_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sm_mid.forward_steps_executed, EXPECTED_STAGE_A_FORWARD_STEP_IDS[:5])
        self.assertEqual(sm_mid.unwind_steps_executed, tuple(reversed(EXPECTED_STAGE_A_FORWARD_STEP_IDS[:5])))
        self.assertEqual(sm_mid.lingering_mounts, 0)

        sm_ok = simulate_orchestrator_state_machine(arm_token_present=True)
        self.assertEqual(sm_ok.boot_branch, "STAGE_A_ADAPTED_CLEAN_EXIT")
        self.assertEqual(sm_ok.forward_steps_executed, EXPECTED_STAGE_A_FORWARD_STEP_IDS)
        self.assertEqual(sm_ok.unwind_steps_executed, EXPECTED_STAGE_A_LIFO_UNWIND_STEP_IDS)
        self.assertEqual(sm_ok.lingering_mounts, 0)
        self.assertEqual(sm_ok.emmc_writes, 0)
        self.assertEqual(sm_ok.wbi_writes, 0)

        # 2. Full 6-scenario `/bin/sh` sandbox verification inside TemporaryDirectory
        is_cr = _is_clean_room_or_donor_missing()
        cr_bundle = build_stage_a_ram_overlay_package(synthetic_clean_room=True) if is_cr else None
        rep = run_stage_a_boot_orchestrator_verification(
            overlay_bundle=cr_bundle,
            simulate_clean_room_initrd=is_cr,
        )
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertTrue(rep.stage_a_orchestrator_ok)
        self.assertEqual(rep.scenario_count, 6)
        self.assertEqual(rep.total_sandbox_runs, 10)
        self.assertEqual(rep.total_emmc_writes, 0)
        self.assertEqual(rep.total_wbi_writes, 0)
        self.assertEqual(rep.total_lingering_mounts, 0)
        self.assertEqual(rep.total_sandbox_violations, 0)
        self.assertTrue(rep.temp_dir_cleaned)

        s1, s2, s3, s4, s5, s6 = rep.scenarios
        self.assertEqual(s1.runs[0].forward_steps, EXPECTED_STAGE_A_FORWARD_STEP_IDS)
        self.assertEqual(s1.runs[0].unwind_steps, EXPECTED_STAGE_A_LIFO_UNWIND_STEP_IDS)

        for r in s2.runs:
            self.assertEqual(r.forward_steps, ())
            self.assertEqual(r.lingering_mount_count, 0)

        self.assertEqual(s3.runs[0].forward_steps, EXPECTED_STAGE_A_FORWARD_STEP_IDS[:2])
        self.assertEqual(s3.runs[0].unwind_steps, tuple(reversed(EXPECTED_STAGE_A_FORWARD_STEP_IDS[:2])))
        self.assertEqual(s3.runs[1].forward_steps, EXPECTED_STAGE_A_FORWARD_STEP_IDS[:8])
        self.assertEqual(s3.runs[1].unwind_steps, tuple(reversed(EXPECTED_STAGE_A_FORWARD_STEP_IDS[:8])))

        self.assertEqual(s4.runs[0].diag_code, "ERR_WBI_BIS_MODE_FORBIDDEN")
        self.assertEqual(s4.runs[1].diag_code, "ERR_WBI_P5_ALREADY_MOUNTED")
        self.assertEqual(s4.runs[2].wbi_trigger_blocked_count, 1)
        self.assertTrue(s5.runs[0].double_mount_prevented)
        self.assertEqual(s5.runs[0].diag_code, "ERR_IDEMPOTENT_REENTRY_BLOCKED")
        self.assertEqual(s6.runs[0].boot_branch, "STOCK_FX3")
        self.assertEqual(s6.runs[0].forward_steps, ())

        # 3. Host safety lock refuses execution if PREFIX is unset on host OS
        with tempfile.TemporaryDirectory(prefix="stage_a_host_lock_") as tmp_s:
            orch_p = Path(tmp_s) / "30-stage-a-orchestrator.sh"
            orch_p.write_text(generate_stage_a_boot_orchestrator_script(), encoding="utf-8")
            proc = subprocess.run(
                ["/bin/sh", str(orch_p)],
                env={"PATH": "/usr/bin:/bin"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 97)
            self.assertIn("ERR_SANDBOX_PREFIX_REQUIRED_ON_HOST", proc.stderr)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_cli_verify_stage_a_orchestrator_subcommand(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-stage-a-orchestrator"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "OK")
        self.assertTrue(payload["all_checks_passed"])
        self.assertTrue(payload["stage_a_orchestrator_ok"])
        self.assertTrue(payload["wbi_p5_write_and_hibernation_forbidden"])
        self.assertEqual(payload["wbi_mutation_bytes"], 0)
        self.assertEqual(payload["scenario_count"], 6)
        self.assertEqual(payload["total_emmc_writes"], 0)
        self.assertEqual(payload["total_wbi_writes"], 0)
        self.assertEqual(payload["total_lingering_mounts"], 0)


class TestPhase14KmodAndUserlandAbiVerifier(unittest.TestCase):
    """Verify Phase 14 `insmod_drv1`/`insmod_drv2` `.ko` matrix, `/dev/*` nodes, ELF64 `DT_NEEDED`/`DYNSYM`/`VERNEED` closure, and synthetic patcher."""

    def test_clean_room_synthetic_elf64_patcher_and_mapper_roundtrip(self) -> None:
        # Build a synthetic ELF64 AArch64 ET_DYN image with a "/dev/nflasha20\0" literal inside PT_LOAD
        base_blob = bytearray(
            build_synthetic_elf64_linkage_blob(
                soname="libsynth_lut.so",
                exports=("synth_open_lut",),
            )
        )
        marker_pre = b"OPEN:"
        marker_orig = b"/dev/nflasha20\x00"
        marker_pat = b"/dev/nflasha30\x00"
        marker_post = b":END"
        inject_off = 64 + 2 * 56  # Inside mapped PT_LOAD
        payload = marker_pre + marker_orig + marker_post
        # Construct clean minimal ELF64 AArch64 ET_DYN buffer with 1 PT_LOAD (PF_R) covering [0, 512)
        raw_elf = bytearray(512)
        struct.pack_into(
            "<4sBBBB8xHHIQQQIHHHHHH",
            raw_elf,
            0,
            b"\x7fELF",
            2,
            1,
            1,
            0,
            3,  # ET_DYN
            183,  # EM_AARCH64
            1,
            0,
            64,
            0,
            0,
            64,
            56,
            1,
            64,
            0,
            0,
        )
        struct.pack_into("<IIQQQQQQ", raw_elf, 64, 1, PF_R, 0, 0x10000, 0x10000, 512, 512, 0x1000)
        raw_elf[inject_off : inject_off + len(payload)] = payload
        donor_bytes = bytes(raw_elf)
        donor_sha = hashlib.sha256(donor_bytes).hexdigest()
        target_off = inject_off + len(marker_pre) + 12  # '2' in nflasha20

        spec = LibraryPatchSpec(
            spec_id="SYNTH_P1_LUT",
            library_name="libsynth_lut.so",
            expected_size=len(donor_bytes),
            donor_sha256=donor_sha,
            sites=(
                PatchSiteSpec(
                    site_id="synth_lut_2_to_3",
                    patch_group="P1",
                    symbol_or_desc="Synthetic /dev/nflasha20 -> /dev/nflasha30",
                    vma=0x10000 + target_off,
                    expected_file_offset=target_off,
                    required_segment_flags=PF_R,
                    original_bytes=b"2",
                    patched_bytes=b"3",
                    pre_context=b"/dev/nflasha",
                    post_context=b"0\x00",
                ),
            ),
        )
        self.assertGreater(len(base_blob), 128)
        patched, p_rec = apply_patch_spec(donor_bytes, spec)
        self.assertEqual(p_rec.changed_byte_count, 1)
        self.assertIn(marker_pat, patched)
        with self.assertRaises(PatchVerificationError):
            apply_patch_spec(patched, spec, verify_donor_sha256=False)
        restored, rb_rec = rollback_patch_spec(patched, spec)
        self.assertTrue(rb_rec.donor_sha256_matched)
        self.assertEqual(restored, donor_bytes)

    def test_clean_room_insmod_dev_node_and_synthetic_elf64_linkage_closure(self) -> None:
        # 1. Surface A: `parse_insmod_script` & `classify_kmod_driver_matrix`
        drv1_txt = "# early storage\ninsmod /kmod/devno.ko\ninsmod /kmod/emmc.ko mode=1\n"
        drv2_txt = "insmod /usr/kmod/osal_uipc.ko\ninsmod /usr/kmod/upm.ko\ninsmod /usr/kmod/emg.ko\n"
        d1 = parse_insmod_script(drv1_txt)
        d2 = parse_insmod_script(drv2_txt)
        self.assertEqual([e.ko_name for e in d1], ["devno.ko", "emmc.ko"])
        self.assertEqual(d1[1].params, "mode=1")
        self.assertEqual([e.ko_name for e in d2], ["osal_uipc.ko", "upm.ko", "emg.ko"])

        matrix = classify_kmod_driver_matrix(
            drv1_entries=d1,
            drv2_entries=d2,
            fx3_initrd_kmods=("devno.ko", "emmc.ko"),
            fx6_initrd_kmods=("devno.ko", "emmc.ko"),
            fx3_usr_kmods=("osal_uipc.ko", "upm.ko"),
            fx6_usr_kmods=("osal_uipc.ko", "upm.ko", "emg.ko"),
        )
        by_ko = {m.ko_name: m for m in matrix}
        self.assertEqual(by_ko["osal_uipc.ko"].category, "common_shared_cxd90057")
        self.assertEqual(by_ko["upm.ko"].stage_a_disposition, "retained_stock_fx3_ko_with_ram_p9_null_guard")
        self.assertEqual(by_ko["emg.ko"].category, "fx6_specific_omitted")

        # 2. Surface B: `/dev/*` extraction & Stage-A classification
        sample_blob = b"\x00/dev/nflasha20\x00/dev/nflasha21\x00/dev/stream2\x00foo/dev/fake\x00/dev/unknown_xyz99\x00"
        extracted = extract_dev_node_references_from_blob(sample_blob)
        self.assertEqual(extracted, ("/dev/nflasha20", "/dev/nflasha21", "/dev/stream2", "/dev/unknown_xyz99"))
        self.assertEqual(classify_userland_dev_node("/dev/nflasha20")[0], "p1_p2_adapted_partition_node")
        self.assertTrue(classify_userland_dev_node("/dev/nflasha20")[1])
        self.assertEqual(classify_userland_dev_node("/dev/stream2")[0], "drv2_shared_cxd90057_kmod")
        self.assertFalse(classify_userland_dev_node("/dev/unknown_xyz99")[1])

        # 3. Surface C: Synthetic ELF64 `PT_DYNAMIC` + `DYNSYM` + `VERNEED`/`VERDEF` positive & negative closure
        libc_info = parse_elf64_linkage_info(
            build_synthetic_elf64_linkage_blob(
                soname="libc.so.6",
                exports=("puts", "malloc"),
                verdefs=("GLIBC_2.17",),
            ),
            file_name="libc.so.6",
        )
        libstd_info = parse_elf64_linkage_info(
            build_synthetic_elf64_linkage_blob(
                soname="libstdc++.so.6",
                dt_needed=("libc.so.6", "libgcc_s.so.1"),
                exports=("_Znwm", "__cxa_throw"),
                eager_undefs=("malloc",),
                verneeds=(("libc.so.6", ("GLIBC_2.17",)), ("libgcc_s.so.1", ("GCC_3.0",))),
                verdefs=("GLIBCXX_3.4", "CXXABI_1.3"),
            ),
            file_name="libstdc++.so.6",
        )
        libgcc_info = parse_elf64_linkage_info(
            build_synthetic_elf64_linkage_blob(
                soname="libgcc_s.so.1",
                exports=("_Unwind_Resume",),
                verdefs=("GCC_3.0",),
            ),
            file_name="libgcc_s.so.1",
        )
        app_info = parse_elf64_linkage_info(
            build_synthetic_elf64_linkage_blob(
                soname="libInfraSynth.so",
                dt_needed=("libstdc++.so.6", "libc.so.6"),
                exports=("infra_entry",),
                eager_undefs=("_Znwm", "__cxa_throw"),
                lazy_plt_undefs=("puts",),
                weak_undefs=("__gmon_start__",),
                verneeds=(
                    ("libc.so.6", ("GLIBC_2.17",)),
                    ("libstdc++.so.6", ("GLIBCXX_3.4", "CXXABI_1.3")),
                ),
            ),
            file_name="libInfraSynth.so",
        )
        self.assertTrue(app_info.parsed_via_pt_dynamic)
        providers = {
            "libc.so.6": libc_info,
            "libstdc++.so.6": libstd_info,
            "libgcc_s.so.1": libgcc_info,
            "libInfraSynth.so": app_info,
        }
        universe = set()
        for p_inf in providers.values():
            universe.update(p_inf.exported_symbols)

        ok_closure = evaluate_elf64_linkage_closure(
            root_infos=((app_info, True),),
            provider_index=providers,
            universe_exports=universe,
            allowed_appfw_lazy_omitted=(),
            patch_symbol_table_delta_count=0,
            fx3_base_runtime_abi_parity_verified=True,
        )
        self.assertTrue(ok_closure.all_checks_passed, ok_closure.errors)
        self.assertEqual(ok_closure.transitive_closure_count, 4)
        self.assertEqual(ok_closure.missing_dt_needed_count, 0)
        self.assertEqual(ok_closure.unresolved_required_symbols, 0)
        self.assertEqual(ok_closure.unsatisfied_verneed_count, 0)
        self.assertTrue(ok_closure.glibc_cxxabi_glibcxx_gcc_verified)

        # Negative Fault 1: Missing DT_NEEDED shared library -> fail closed
        bad_needed_info = parse_elf64_linkage_info(
            build_synthetic_elf64_linkage_blob(
                soname="libBadNeeded.so",
                dt_needed=("libnonexistent_fx6_only.so",),
            ),
            file_name="libBadNeeded.so",
        )
        bad_needed_rep = evaluate_elf64_linkage_closure(
            root_infos=((app_info, True), (bad_needed_info, True)),
            provider_index={**providers, "libBadNeeded.so": bad_needed_info},
            universe_exports=universe,
            allowed_appfw_lazy_omitted=(),
        )
        self.assertFalse(bad_needed_rep.all_checks_passed)
        self.assertIn("libBadNeeded.so->libnonexistent_fx6_only.so", bad_needed_rep.missing_dt_needed)

        # Negative Fault 2: Unresolved non-weak STB_GLOBAL SHN_UNDEF symbol -> fail closed
        bad_sym_info = parse_elf64_linkage_info(
            build_synthetic_elf64_linkage_blob(
                soname="libBadSym.so",
                dt_needed=("libc.so.6",),
                eager_undefs=("missing_strong_symbol_xyz",),
            ),
            file_name="libBadSym.so",
        )
        bad_sym_rep = evaluate_elf64_linkage_closure(
            root_infos=((app_info, True), (bad_sym_info, True)),
            provider_index={**providers, "libBadSym.so": bad_sym_info},
            universe_exports=universe,
            allowed_appfw_lazy_omitted=(),
        )
        self.assertFalse(bad_sym_rep.all_checks_passed)
        self.assertGreater(bad_sym_rep.unresolved_required_symbols, 0)

        # Negative Fault 3: Unsatisfied GLIBCXX_3.4.99 VERNEED -> fail closed
        bad_vn_info = parse_elf64_linkage_info(
            build_synthetic_elf64_linkage_blob(
                soname="libBadVerneed.so",
                dt_needed=("libstdc++.so.6",),
                verneeds=(("libstdc++.so.6", ("GLIBCXX_3.4.99",)),),
            ),
            file_name="libBadVerneed.so",
        )
        bad_vn_rep = evaluate_elf64_linkage_closure(
            root_infos=((app_info, True), (bad_vn_info, True)),
            provider_index={**providers, "libBadVerneed.so": bad_vn_info},
            universe_exports=universe,
            allowed_appfw_lazy_omitted=(),
        )
        self.assertFalse(bad_vn_rep.all_checks_passed)
        self.assertGreater(bad_vn_rep.unsatisfied_verneed_count, 0)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_live_donor_kmod_dev_nodes_elf64_abi_and_gate12_redline(self) -> None:
        rep = run_kmod_and_userland_abi_verification()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertTrue(rep.kmod_userland_abi_ok)
        self.assertEqual(rep.kmod_mutation_count, 0)
        self.assertEqual(rep.fx6_kmod_loaded_count, 0)
        self.assertEqual(rep.unaccounted_dev_node_count, 0)
        self.assertEqual(rep.missing_dt_needed_count, 0)
        self.assertEqual(rep.unresolved_required_symbols, 0)
        self.assertEqual(rep.unsatisfied_verneed_count, 0)

        sa = rep.surface_a_kmod_matrix
        self.assertEqual(sa.drv1_load_count, 4)
        self.assertEqual(sa.drv2_load_count, 39)
        self.assertEqual(sa.common_shared_kmod_count, 126)
        self.assertEqual(sa.fx3_exclusive_kmod_count, 0)
        self.assertEqual(sa.fx6_exclusive_kmod_names, ("emg.ko",))

        sb = rep.surface_b_dev_nodes
        self.assertTrue(sb.p1_patched_zero_nflasha20_verified)
        self.assertEqual(sb.unaccounted_dev_nodes, ())
        self.assertGreaterEqual(sb.unique_dev_path_count, 130)

        sc = rep.surface_c_elf_linkage
        self.assertEqual(sc.transitive_closure_count, 60)
        self.assertEqual(sc.patch_symbol_table_delta_count, 0)
        self.assertTrue(sc.fx3_base_runtime_abi_parity_verified)

        # CLI `verify-kmod-userland-abi` check
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-kmod-userland-abi"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "OK")
        self.assertTrue(payload["kmod_userland_abi_ok"])
        self.assertEqual(payload["kmod_mutation_count"], 0)
        self.assertEqual(payload["unresolved_required_symbols"], 0)

        # End-to-end Gate G12 `BLOCKED_BY_KMOD_USERLAND_ABI_REDLINE` fault injection
        bad_dry = run_offline_candidate_dry_run(
            precomputed_kmod_userland_abi=rep,
            corrupt_kmod_userland_abi=True,
        )
        self.assertFalse(bad_dry.candidate_ready)
        self.assertFalse(bad_dry.kmod_userland_abi_ok)
        self.assertEqual(bad_dry.blocked_gate_ids, ("G12_persistent_flash_write_authorization",))
        g12 = [
            g for g in bad_dry.safety_gates_report["gates"] if g["gate_id"] == "G12_persistent_flash_write_authorization"
        ][0]
        self.assertEqual(g12["status"], "BLOCKED_BY_KMOD_USERLAND_ABI_REDLINE")


if __name__ == "__main__":
    unittest.main()
