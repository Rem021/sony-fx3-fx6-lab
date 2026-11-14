"""End-to-End Offline Candidate Dry-Run Assembler & 12-Gate Safety Evaluator Integration.

Executes inside an ephemeral `tempfile.TemporaryDirectory()` and automatically cleans up all
staged binary files on exit, covering the complete **P1..P9 (9/9)** matrix + Fan + Tier-0 + 12 Gates:
1. Adapts all 7 canonical binary targets (P1, P3, P4, P8, P9 `upm.ko`, and Fan `libfan.so`) and
   verifies 100% deterministic SHA-256 rollback on every staged binary.
2. Synthesizes and audits the 8 MiB `opelog.vfat` (`FAT16`) image (P2).
3. Executes Unicorn AArch64 behavioral checks across P3, P4, P5, P6, P8, P9, and Fan
   (including `send_and_wait_cmp_i` UIPC completion synthesis on `0x92840747` for
   `0x032d` / `0x0400` / `0x0402` / `0x0404` / `0x0152`).
4. Audits the P7 Kernel-Space Backup Sync100 address-agnostic bridge across FX3 & FX6 kernels
   (`pcidma_transfer_async` 16B prologue, `api+0x160` / `api+0x10` Unicorn trampoline,
   40B `op=0x30` schema, and synchronous `backupfile_cb_getcp` DMA callback contract).
5. Compiles & runs `native/tier0_backup_worker.c` in Unicorn AArch64 to produce a real 11-item
   two-pass `manifest.json` and audited Linux AArch64 syscall trace.
6. Evaluates all 12 pre-flash safety gates via `fx3_safety.preflight.evaluate_12_safety_gates`
   (proving 12/12 green under valid inputs and immediate fail-closed blocking on any missing or
   tampered artifact).
"""

from __future__ import annotations

import copy
import hashlib
import json
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import unicorn as U
from unicorn import arm64_const as A

from fx3_safety.brick_classifier import generate_failsafe_init2_overlay_hook
from fx3_safety.preflight import (
    BackupManifestAudit,
    WorkerSyscallAudit,
    audit_tier0_worker_syscalls,
    evaluate_12_safety_gates,
    verify_tier0_backup_manifest,
)

from .ap_cp_imaging_pipeline_verifier import (
    Phase18ImagingAuditReport,
    verify_ap_cp_imaging_pipeline,
)
from .backup_bridge_verifier import (
    P7BackupBridgeAuditReport,
    verify_p7_backup_bridge,
)
from .backup_mount_tolerance_verifier import (
    Phase6BackupMountToleranceReport,
    run_backup_mount_tolerance_verification,
)
from .boot_selector_and_bank_verifier import (
    Phase7BootSelectorAndBankReport,
    run_boot_selector_and_bank_verification,
)
from .cp_rtos_compatibility_verifier import (
    Phase10CpRtosCompatibilityReport,
    run_cp_rtos_compatibility_verification,
)
from .donor_paths import is_forced_clean_room, resolve_lab_work_file
from .elf_verify import PF_R, PF_X
from .feature_routing_verifier import (
    FeatureRoutingAuditReport,
    run_feature_routing_verification,
)
from .kernel_dtb_compatibility_verifier import (
    Phase8KernelDtbReport,
    run_kernel_dtb_verification,
)
from .kmod_and_userland_abi_verifier import (
    KmodAndUserlandAbiReport,
    run_kmod_and_userland_abi_verification,
)
from .nd_unicorn_verifier import (
    FanExecSummary,
    NdSweepSummary,
    P3PruneExecSummary,
    P8ExecSummary,
    P9GuardExecSummary,
    run_fan_libfan_unicorn_check,
    run_p3_remoteboard_unicorn_check,
    run_p4_nd_unicorn_sweep,
    run_p8_appfw_unicorn_check,
    run_p9_upm_ko_unicorn_check,
)
from .p1_recovery_bridge_verifier import (
    Phase11P1RecoveryBridgeReport,
    run_p1_recovery_bridge_verification,
)
from .patcher import (
    ALL_PHASE2_TARGET_SPECS,
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
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
    STAGE_B_PATCH_SPECS,
    LibraryPatchSpec,
    PatchReceipt,
    PatchSiteSpec,
    RollbackReceipt,
    apply_patch_spec,
    build_stage_b_appfw_image,
    generate_p1_lut_mount_snippet,
    get_target_patch_specs,
    read_donor_bytes_readonly,
    resolve_donor_binary_path,
    rollback_patch_spec,
    verify_patch_sites_non_overlapping,
)
from .peripheral_ux_compatibility_verifier import (
    FX6_KEYMAP_PAIR_COUNT,
    Phase17CompatibilityReport,
    _assemble_synthetic_lookup_fn,
    _pack_elf64_et_dyn,
    _unicorn_lookup_real_appfw,
    _unicorn_lookup_synthetic_appfw,
    verify_peripheral_ux_compatibility,
)
from .ram_overlay_packager import (
    CpioArchiveAudit,
    REQUIRED_STAGE_A_OVERLAY_PATHS,
    build_stage_a_ram_overlay_package,
    parse_and_audit_cpio_newc,
)
from .rollback_drill import (
    RollbackDrillReport,
    run_four_layer_rollback_drill,
)
from .stage_a_boot_orchestrator import (
    Phase12StageABootOrchestratorReport,
    run_stage_a_boot_orchestrator_verification,
)
from .storage_and_ram_budget_verifier import (
    Phase9StorageAndRamBudgetReport,
    run_storage_and_ram_budget_verification,
)
from .tier0_unicorn_verifier import (
    WORKER_OK,
    CompiledWorkerArtifact,
    Tier0UnicornRunResult,
    run_tier0_worker_in_unicorn,
)
from .uipc_completion_verifier import (
    UipcP5P6AuditSummary,
    run_p5_p6_uipc_unicorn_audit,
)
from .uipc_cp_shim_verifier import (
    Phase21UipcCpShimReport,
    run_phase21_uipc_cp_shim_verification,
)
from .vfat_builder import (
    VfatAuditResult,
    VfatBuildReceipt,
    build_opelog_vfat_image,
    generate_p2_opelog_mount_snippet,
    verify_vfat_image,
)


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
COMPLETE_MATRIX_ITEMS: Tuple[str, ...] = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "Fan")

EXPECTED_STAGE_B_NATIVE_KEYMAP: Dict[int, int] = {
    0x0002: 0x001,       # POWER
    0x0003: 0x002,       # UP
    0x0015: 0x004,       # LEFT
    0x0030: 0x006,       # DOWN
    0x01AB: 0x013,       # MENU
    0x01AC: 0x014,       # ENTER
    0x01AF: 0x016,       # RIGHT
    0x01F0: 0x01C,       # REC
    0x7049: 0x040,       # C5
    0x704A: 0x041,       # C6
    0x71C3: 0x1BB,       # VARI_LCD_OPEN
    0x71C4: 0x1BC,       # VARI_LCD_CLOSE
    0x71C5: 0x1BD,       # VARI_LCD_REV
    0x04000011: 0x214,   # DIAL_FRONT
    0x04000013: 0x216,   # DIAL_REAR
}

EXPECTED_STAGE_B_P10_KEYMAP: Dict[int, int] = {
    0x7095: 0x184,  # Fn -> HOME
    0x0066: 0x029,  # C1 -> KURU_PON
    0x70E7: 0x192,  # C2 -> MENU_CANCEL
    0x70EC: 0x199,  # C3 -> DISP_SEL
    0x01F7: 0x183,  # PLAY -> THUMBNAIL
    0x01F8: 0x185,  # DELETE -> USER
}


@dataclass(frozen=True)
class StageBCombinedAppFwReport:
    verification_mode: str
    appfw_size_bytes: int
    donor_sha256: str
    stage_a_sha256: str
    p10_only_sha256: str
    stage_b_combined_sha256: str
    sequential_forward_equivalent: bool
    direct_rollback_sha256_matched: bool
    sequential_reverse_rollback_sha256_matched: bool
    zero_byte_overlap: bool
    total_site_count: int
    total_patched_bytes: int
    non_overlapping_intervals: Tuple[Tuple[str, str, int, int], ...]
    p1_site_verified: bool
    p4_mode_unicorn: NdSweepSummary
    p4_value_unicorn: NdSweepSummary
    p8_unicorn: P8ExecSummary
    p10_native_1to1_map: Dict[int, int]
    p10_remapped_map: Dict[int, int]
    p10_native_1to1_passed: bool
    p10_remapped_passed: bool
    all_checks_passed: bool


def _build_synthetic_stage_b_appfw_bundle() -> Tuple[
    bytes,
    LibraryPatchSpec,
    LibraryPatchSpec,
    LibraryPatchSpec,
    int,
    int,
    int,
    int,
    int,
]:
    """Build a deterministic clean-room AArch64 ELF64 `appFw.so` image combining P1+P4+P8+P10."""
    code_base = 0x1000
    p4_mode_vma = 0x1000
    p4_val_vma = 0x1040
    p8_vma = 0x1080
    lookup_vma = 0x1100
    ro_keymap_vma = 0x4000
    ro_p1_str_vma = 0x8000

    code_buf = bytearray(0x400)
    # P4 mode fn @ 0x1000: cbnz w1, +0x10 (0x1010) -> nop; mov w0, #4; strb w0, [x3, #8]; ret
    p4_mode_words = (
        0x35000081,  # 0x1000: cbnz w1, #0x1010 (site)
        0x52800080,  # 0x1004: mov w0, #4
        0x39002060,  # 0x1008: strb w0, [x3, #8]
        0xD65F03C0,  # 0x100c: ret
        0x52800020,  # 0x1010: mov w0, #1
        0x39002060,  # 0x1014: strb w0, [x3, #8]
        0xD65F03C0,  # 0x1018: ret
    )
    struct.pack_into(f"<{len(p4_mode_words)}I", code_buf, p4_mode_vma - code_base, *p4_mode_words)

    # P4 value fn @ 0x1040: mov w8, #1; cbz w1, #0x1054 -> b #0x1054; ... stp w8, w8, [x3, #8]; ret
    p4_val_words = (
        0x52800028,  # 0x1040: mov w8, #1
        0x34000081,  # 0x1044: cbz w1, #0x1054 (site -> b #0x1054 = 0x14000004)
        0x52800040,  # 0x1048: mov w0, #2
        0x29010060,  # 0x104c: stp w0, w0, [x3, #8]
        0xD65F03C0,  # 0x1050: ret
        0x29012068,  # 0x1054: stp w8, w8, [x3, #8]
        0xD65F03C0,  # 0x1058: ret
    )
    struct.pack_into(f"<{len(p4_val_words)}I", code_buf, p4_val_vma - code_base, *p4_val_words)

    # P8 async log wait fn @ 0x1080: stp x29, x30, [sp, #-0x60]!; mov x29, sp -> mov w0, #0; ret
    p8_words = (
        0xA9BA7BFD,  # 0x1080
        0x910003FD,  # 0x1084
        0x52800C60,  # 0x1088: mov w0, #99
        0xA8C67BFD,  # 0x108c
        0xD65F03C0,  # 0x1090
    )
    struct.pack_into(f"<{len(p8_words)}I", code_buf, p8_vma - code_base, *p8_words)

    lookup_code = _assemble_synthetic_lookup_fn()
    code_buf[lookup_vma - code_base : lookup_vma - code_base + len(lookup_code)] = lookup_code

    # .rodata keymap `<II` table with all 15 native 1:1 + 6 P10 pairs (unpatched baseline)
    base_pairs: List[Tuple[int, int]] = [
        (0x0002, 0x001), (0x0003, 0x002), (0x0015, 0x004), (0x0030, 0x006),
        (0x0066, 0x00E), (0x01AB, 0x013), (0x01AC, 0x014), (0x01AF, 0x016),
        (0x01F0, 0x01C), (0x01F7, 0x022), (0x01F8, 0x023), (0x7023, 0x029),
        (0x7049, 0x040), (0x704A, 0x041), (0x7095, 0x08D), (0x70E7, 0x0DF),
        (0x70EC, 0x0E4), (0x718B, 0x183), (0x718C, 0x184), (0x718D, 0x185),
        (0x719A, 0x192), (0x71A1, 0x199), (0x71C3, 0x1BB), (0x71C4, 0x1BC),
        (0x71C5, 0x1BD), (0x04000011, 0x214), (0x04000013, 0x216),
    ]
    used_iks = {ik for ik, _ in base_pairs}
    next_ik = 0x8000
    while len(base_pairs) < FX6_KEYMAP_PAIR_COUNT:
        if next_ik not in used_iks:
            base_pairs.append((next_ik, 0x500 + len(base_pairs)))
        next_ik += 1

    km_buf = bytearray()
    off_by_ik: Dict[int, int] = {}
    for idx, (ik, ak) in enumerate(base_pairs):
        off_by_ik[ik] = idx * 8
        km_buf.extend(struct.pack("<II", ik, ak))

    ro_size = (ro_p1_str_vma - ro_keymap_vma) + 64
    ro_blob = bytearray(ro_size)
    ro_blob[0 : len(km_buf)] = km_buf
    p1_marker = b"line[%d]\x00/dev/nflasha20\x00model_user_lut_fi\x00"
    p1_rel = ro_p1_str_vma - ro_keymap_vma
    ro_blob[p1_rel : p1_rel + len(p1_marker)] = p1_marker
    p1_digit_vma = ro_p1_str_vma + p1_marker.index(b"20")

    appfw_bytes = _pack_elf64_et_dyn(
        bytes(code_buf),
        rodata_bytes=bytes(ro_blob),
        code_vaddr=code_base,
        rodata_vaddr=ro_keymap_vma,
    )
    donor_sha = hashlib.sha256(appfw_bytes).hexdigest()

    p4_mode_site = PatchSiteSpec(
        site_id="synth_p4_mode_clear",
        patch_group="P4",
        symbol_or_desc="synthetic set_nd_filter_mode_i",
        vma=p4_mode_vma,
        expected_file_offset=p4_mode_vma,
        required_segment_flags=PF_R | PF_X,
        original_bytes=P4_APPFW_MODE_SITE.original_bytes,
        patched_bytes=P4_APPFW_MODE_SITE.patched_bytes,
        post_context=P4_APPFW_MODE_SITE.post_context,
    )
    p4_val_site = PatchSiteSpec(
        site_id="synth_p4_val_clear",
        patch_group="P4",
        symbol_or_desc="synthetic set_nd_filter_value_i",
        vma=p4_val_vma + 4,
        expected_file_offset=p4_val_vma + 4,
        required_segment_flags=PF_R | PF_X,
        original_bytes=struct.pack("<I", 0x34000081),
        patched_bytes=struct.pack("<I", 0x14000004),
    )
    p8_site = PatchSiteSpec(
        site_id="synth_p8_async_wait",
        patch_group="P8",
        symbol_or_desc="synthetic async log wait",
        vma=p8_vma,
        expected_file_offset=p8_vma,
        required_segment_flags=PF_R | PF_X,
        original_bytes=P8_APPFW_SITE.original_bytes,
        patched_bytes=P8_APPFW_SITE.patched_bytes,
    )
    p1_site = PatchSiteSpec(
        site_id="synth_p1_nflasha30",
        patch_group="P1",
        symbol_or_desc="synthetic /dev/nflasha20 -> /dev/nflasha30",
        vma=p1_digit_vma,
        expected_file_offset=p1_digit_vma,
        required_segment_flags=PF_R,
        original_bytes=b"2",
        patched_bytes=b"3",
        pre_context=P1_APPFW_SITE.pre_context,
        post_context=P1_APPFW_SITE.post_context,
    )

    p10_sites: List[PatchSiteSpec] = []
    for sid, desc, ik, orig_ak, new_ak in (
        ("p10_fn_to_home", "Fn -> HOME", 0x7095, 0x8D, 0x184),
        ("p10_c1_to_kuru_pon", "C1 -> KURU_PON", 0x0066, 0x0E, 0x29),
        ("p10_c2_to_menu_cancel", "C2 -> MENU_CANCEL", 0x70E7, 0xDF, 0x192),
        ("p10_c3_to_disp_sel", "C3 -> DISP_SEL", 0x70EC, 0xE4, 0x199),
        ("p10_play_to_thumbnail", "PLAY -> THUMBNAIL", 0x01F7, 0x22, 0x183),
        ("p10_delete_to_user", "DELETE -> USER", 0x01F8, 0x23, 0x185),
    ):
        ak_off = ro_keymap_vma + off_by_ik[ik] + 4
        p10_sites.append(
            PatchSiteSpec(
                site_id=sid,
                patch_group="P10",
                symbol_or_desc=desc,
                vma=ak_off,
                expected_file_offset=ak_off,
                required_segment_flags=PF_R,
                original_bytes=struct.pack("<I", orig_ak),
                patched_bytes=struct.pack("<I", new_ak),
                pre_context=appfw_bytes[ak_off - 4 : ak_off],
                post_context=appfw_bytes[ak_off + 4 : ak_off + 8],
            )
        )

    stage_a_spec = LibraryPatchSpec(
        spec_id="P1_P4_P8_appFw_synthetic",
        library_name="appFw.so",
        expected_size=len(appfw_bytes),
        donor_sha256=donor_sha,
        sites=(p4_mode_site, p4_val_site, p8_site, p1_site),
    )
    p10_spec = LibraryPatchSpec(
        spec_id="P10_FX3_TO_FX6_KEYMAP_ADAPTER_SYNTHETIC",
        library_name="appFw.so",
        expected_size=len(appfw_bytes),
        donor_sha256=donor_sha,
        sites=tuple(p10_sites),
    )
    combined_spec = LibraryPatchSpec(
        spec_id="P1_P4_P8_P10_appFw_synthetic",
        library_name="appFw.so",
        expected_size=len(appfw_bytes),
        donor_sha256=donor_sha,
        sites=(p4_mode_site, p4_val_site, p8_site, p1_site, *p10_sites),
    )
    return (
        appfw_bytes,
        stage_a_spec,
        p10_spec,
        combined_spec,
        p4_mode_vma,
        p4_val_vma,
        p8_vma,
        lookup_vma,
        ro_keymap_vma,
    )


def _run_synthetic_p4_p8_unicorn(
    appfw_bytes: bytes,
    *,
    p4_mode_vma: int,
    p4_val_vma: int,
    p8_vma: int,
) -> Tuple[NdSweepSummary, NdSweepSummary, P8ExecSummary]:
    """Execute synthetic AArch64 P4 mode/value & P8 checks in Unicorn on combined image."""
    mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
    mu.mem_map(0x1000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(0x1000, appfw_bytes[0x1000:0x3000])
    stack_base = 0x70000000
    msg_buf = 0x71000000
    ret_sentinel = 0x72000000
    mu.mem_map(stack_base, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(msg_buf, 0x1000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(ret_sentinel, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(ret_sentinel, struct.pack("<I", 0xD503201F))

    mode_clear = 0
    val_clear = 0
    for w1 in (0, 1, 2, 3):
        mu.mem_write(msg_buf, b"\xff" * 32)
        mu.reg_write(A.UC_ARM64_REG_SP, stack_base + 0xE000)
        mu.reg_write(A.UC_ARM64_REG_LR, ret_sentinel)
        mu.reg_write(A.UC_ARM64_REG_W1, w1)
        mu.reg_write(A.UC_ARM64_REG_X3, msg_buf)
        mu.emu_start(p4_mode_vma, ret_sentinel, count=32)
        if mu.mem_read(msg_buf + 8, 1)[0] == 4:
            mode_clear += 1

        mu.mem_write(msg_buf, b"\xff" * 32)
        mu.reg_write(A.UC_ARM64_REG_SP, stack_base + 0xE000)
        mu.reg_write(A.UC_ARM64_REG_LR, ret_sentinel)
        mu.reg_write(A.UC_ARM64_REG_W1, w1)
        mu.reg_write(A.UC_ARM64_REG_X3, msg_buf)
        mu.emu_start(p4_val_vma, ret_sentinel, count=32)
        f0, f1 = struct.unpack_from("<II", mu.mem_read(msg_buf + 8, 8))
        if (f0, f1) == (1, 1):
            val_clear += 1

    insns = [0]
    mu.hook_add(U.UC_HOOK_CODE, lambda _uc, _a, _s, _u: insns.__setitem__(0, insns[0] + 1))
    init_sp = stack_base + 0xE000
    mu.reg_write(A.UC_ARM64_REG_SP, init_sp)
    mu.reg_write(A.UC_ARM64_REG_LR, ret_sentinel)
    mu.reg_write(A.UC_ARM64_REG_X0, 0xDEADBEEF)
    mu.emu_start(p8_vma, ret_sentinel, count=16)
    p8_summary = P8ExecSummary(
        return_value=mu.reg_read(A.UC_ARM64_REG_W0),
        instructions_executed=insns[0],
        sp_preserved=mu.reg_read(A.UC_ARM64_REG_SP) == init_sp,
    )

    p4_mode_summary = NdSweepSummary(
        function_name="set_nd_filter_mode_i",
        patched=True,
        total_combinations=4,
        clear_output_count=mode_clear,
        non_clear_output_count=4 - mode_clear,
        assert_hit_count=0,
        assert_lines_observed=(),
        helper_call_count=0,
    )
    p4_val_summary = NdSweepSummary(
        function_name="set_nd_filter_value_i",
        patched=True,
        total_combinations=4,
        clear_output_count=val_clear,
        non_clear_output_count=4 - val_clear,
        assert_hit_count=0,
        assert_lines_observed=(),
        helper_call_count=0,
    )
    return p4_mode_summary, p4_val_summary, p8_summary


def verify_combined_stage_b_appfw_contract(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    appfw_raw: Optional[bytes] = None,
    precomputed_p4_summaries: Optional[Tuple[NdSweepSummary, NdSweepSummary]] = None,
    precomputed_p8_summary: Optional[P8ExecSummary] = None,
    force_synthetic: bool = False,
) -> StageBCombinedAppFwReport:
    """Prove P1+P4+P8+P10 non-interference, deterministic SHA-256, rollback & Unicorn execution."""
    donor_path = fx6_lib_dir / "appFw.so"
    use_synthetic = force_synthetic or (appfw_raw is None and (is_forced_clean_room() or not donor_path.is_file()))

    all_probe_keys: Tuple[int, ...] = (
        *EXPECTED_STAGE_B_NATIVE_KEYMAP.keys(),
        *EXPECTED_STAGE_B_P10_KEYMAP.keys(),
    )

    if use_synthetic:
        (
            donor_bytes,
            stage_a_spec,
            p10_spec,
            combined_spec,
            p4_mode_vma,
            p4_val_vma,
            p8_vma,
            lookup_vma,
            keymap_vma,
        ) = _build_synthetic_stage_b_appfw_bundle()
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        expected_donor_sha = combined_spec.donor_sha256
    else:
        donor_bytes = appfw_raw if appfw_raw is not None else read_donor_bytes_readonly(donor_path)
        stage_a_spec = P1_P4_P8_APPFW_COMBINED_SPEC
        p10_spec = P10_KEYMAP_PATCH_SPEC
        combined_spec = P1_P4_P8_P10_APPFW_COMBINED_SPEC
        mode = "LOCAL_DONOR_AND_UNICORN_VERIFIED"
        expected_donor_sha = FX6_APPFW_DONOR_SHA256

    donor_sha = hashlib.sha256(donor_bytes).hexdigest()
    intervals = verify_patch_sites_non_overlapping(stage_a_spec, p10_spec)
    combined_intervals = verify_patch_sites_non_overlapping(combined_spec)
    zero_overlap = intervals == combined_intervals and len(combined_intervals) == len(combined_spec.sites)

    stage_a_bytes, stage_a_rec = apply_patch_spec(donor_bytes, stage_a_spec, verify_donor_sha256=not use_synthetic)
    p10_only_bytes, p10_only_rec = apply_patch_spec(donor_bytes, p10_spec, verify_donor_sha256=not use_synthetic)
    stage_b_bytes, stage_b_rec = build_stage_b_appfw_image(
        donor_bytes,
        include_p10_keymap=True,
        verify_donor_sha256=not use_synthetic,
        combined_spec=combined_spec,
    )

    # Sequential commutativity: (P1+P4+P8) -> P10 == P10 -> (P1+P4+P8) == combined Stage-B
    seq_a_then_p10, _ = apply_patch_spec(stage_a_bytes, p10_spec, verify_donor_sha256=False)
    seq_p10_then_a, _ = apply_patch_spec(p10_only_bytes, stage_a_spec, verify_donor_sha256=False)
    seq_forward_eq = seq_a_then_p10 == stage_b_bytes and seq_p10_then_a == stage_b_bytes

    # Direct combined rollback & reverse sequential rollback: Stage-B -> Stage-A -> Donor
    direct_restored, direct_rb_rec = rollback_patch_spec(
        stage_b_bytes,
        combined_spec,
        expected_original_sha256=donor_sha,
        enforce_size=not use_synthetic,
    )
    direct_rb_ok = direct_rb_rec.donor_sha256_matched and direct_restored == donor_bytes

    rev_step1_bytes, rev_step1_rec = rollback_patch_spec(
        stage_b_bytes,
        p10_spec,
        expected_original_sha256=stage_a_rec.after_sha256,
        enforce_size=not use_synthetic,
    )
    rev_step2_bytes, rev_step2_rec = rollback_patch_spec(
        rev_step1_bytes,
        stage_a_spec,
        expected_original_sha256=donor_sha,
        enforce_size=not use_synthetic,
    )
    seq_rev_rb_ok = (
        rev_step1_rec.donor_sha256_matched
        and rev_step2_rec.donor_sha256_matched
        and rev_step1_bytes == stage_a_bytes
        and rev_step2_bytes == donor_bytes
    )

    # P1 "/dev/nflasha30\x00" string spot-check on combined Stage-B image
    p1_site = next(s for s in combined_spec.sites if s.patch_group == "P1")
    p1_off = p1_site.expected_file_offset
    p1_window = stage_b_bytes[p1_off - 12 : p1_off + 3]
    p1_ok = p1_window == b"/dev/nflasha30\x00"

    # Unicorn AArch64 verification directly against the single combined Stage-B image
    if use_synthetic:
        p4_mode_uni, p4_val_uni, p8_uni = _run_synthetic_p4_p8_unicorn(
            stage_b_bytes,
            p4_mode_vma=p4_mode_vma,
            p4_val_vma=p4_val_vma,
            p8_vma=p8_vma,
        )
        key_results = _unicorn_lookup_synthetic_appfw(
            stage_b_bytes,
            lookup_fn_vma=lookup_vma,
            keymap_vma=keymap_vma,
            keymap_count=FX6_KEYMAP_PAIR_COUNT,
            probe_keys=all_probe_keys,
        )
    else:
        if precomputed_p4_summaries is not None:
            p4_mode_uni, p4_val_uni = precomputed_p4_summaries
        else:
            p4_mode_uni, p4_val_uni = run_p4_nd_unicorn_sweep(stage_b_bytes, patched_label=True)
        p8_uni = precomputed_p8_summary or run_p8_appfw_unicorn_check(stage_b_bytes)
        key_results = _unicorn_lookup_real_appfw(stage_b_bytes, probe_keys=all_probe_keys)

    native_map = {k: key_results[k] for k in EXPECTED_STAGE_B_NATIVE_KEYMAP}
    p10_map = {k: key_results[k] for k in EXPECTED_STAGE_B_P10_KEYMAP}
    native_ok = native_map == EXPECTED_STAGE_B_NATIVE_KEYMAP
    p10_ok = p10_map == EXPECTED_STAGE_B_P10_KEYMAP

    hashes_ok = use_synthetic or (
        donor_sha == FX6_APPFW_DONOR_SHA256
        and stage_a_rec.after_sha256 == FX6_APPFW_STAGE_A_SHA256
        and p10_only_rec.after_sha256 == FX6_APPFW_P10_ONLY_SHA256
        and stage_b_rec.after_sha256 == FX6_APPFW_STAGE_B_SHA256
    )

    all_passed = (
        donor_sha == expected_donor_sha
        and hashes_ok
        and zero_overlap
        and len(combined_spec.sites) == 10
        and stage_b_rec.changed_byte_count == 41
        and seq_forward_eq
        and direct_rb_ok
        and seq_rev_rb_ok
        and p1_ok
        and p4_mode_uni.assert_hit_count == 0
        and p4_mode_uni.clear_output_count == p4_mode_uni.total_combinations
        and p4_val_uni.assert_hit_count == 0
        and p4_val_uni.clear_output_count == p4_val_uni.total_combinations
        and p8_uni.return_value == 0
        and p8_uni.sp_preserved
        and native_ok
        and p10_ok
    )

    return StageBCombinedAppFwReport(
        verification_mode=mode,
        appfw_size_bytes=len(stage_b_bytes),
        donor_sha256=donor_sha,
        stage_a_sha256=stage_a_rec.after_sha256,
        p10_only_sha256=p10_only_rec.after_sha256,
        stage_b_combined_sha256=stage_b_rec.after_sha256,
        sequential_forward_equivalent=seq_forward_eq,
        direct_rollback_sha256_matched=direct_rb_ok,
        sequential_reverse_rollback_sha256_matched=seq_rev_rb_ok,
        zero_byte_overlap=zero_overlap,
        total_site_count=len(combined_spec.sites),
        total_patched_bytes=stage_b_rec.changed_byte_count,
        non_overlapping_intervals=combined_intervals,
        p1_site_verified=p1_ok,
        p4_mode_unicorn=p4_mode_uni,
        p4_value_unicorn=p4_val_uni,
        p8_unicorn=p8_uni,
        p10_native_1to1_map=native_map,
        p10_remapped_map=p10_map,
        p10_native_1to1_passed=native_ok,
        p10_remapped_passed=p10_ok,
        all_checks_passed=all_passed,
    )


@dataclass(frozen=True)
class CandidateDryRunReport:
    candidate_ready: bool
    all_12_gates_verified: bool
    verified_gate_count: int
    blocked_gate_ids: Tuple[str, ...]
    verified_matrix_items: Tuple[str, ...]
    patch_receipts: Tuple[PatchReceipt, ...]
    rollback_receipts: Tuple[RollbackReceipt, ...]
    vfat_receipt: VfatBuildReceipt
    vfat_audit: VfatAuditResult
    p3_unicorn: P3PruneExecSummary
    p4_mode_unicorn: NdSweepSummary
    p4_value_unicorn: NdSweepSummary
    p5_p6_uipc_unicorn: UipcP5P6AuditSummary
    p7_backup_bridge: P7BackupBridgeAuditReport
    p8_unicorn: P8ExecSummary
    p9_unicorn: P9GuardExecSummary
    fan_unicorn: FanExecSummary
    stage_a_overlay_cpio_sha256: str
    stage_a_overlay_cpio_size: int
    stage_a_cpio_audit: CpioArchiveAudit
    rollback_drill: RollbackDrillReport
    feature_routing_audit: FeatureRoutingAuditReport
    backup_mount_tolerance_audit: Phase6BackupMountToleranceReport
    backup_mount_tolerance_ok: bool
    boot_selector_and_bank_audit: Phase7BootSelectorAndBankReport
    boot_selector_and_banks_ok: bool
    kernel_dtb_audit: Phase8KernelDtbReport
    kernel_dtb_ok: bool
    storage_and_ram_budget_audit: Phase9StorageAndRamBudgetReport
    storage_and_ram_budget_ok: bool
    cp_rtos_audit: Phase10CpRtosCompatibilityReport
    cp_rtos_ok: bool
    p1_recovery_bridge_audit: Phase11P1RecoveryBridgeReport
    p1_recovery_bridge_ok: bool
    stage_a_orchestrator_audit: Phase12StageABootOrchestratorReport
    stage_a_orchestrator_ok: bool
    kmod_userland_abi_audit: KmodAndUserlandAbiReport
    kmod_userland_abi_ok: bool
    peripheral_ux_audit: Phase17CompatibilityReport
    peripheral_ux_ok: bool
    ap_cp_imaging_audit: Phase18ImagingAuditReport
    ap_cp_imaging_ok: bool
    tier0_worker_rc: int
    tier0_manifest_audit: BackupManifestAudit
    tier0_syscall_audit: WorkerSyscallAudit
    safety_gates_report: Dict[str, object]
    temp_dir_cleaned: bool
    stage_b_p10_keymap_enabled: bool = False
    stage_b_appfw_sha256: str = ""
    stage_b_combined_appfw_verified: bool = False
    stage_b_p10_summary: Optional[StageBCombinedAppFwReport] = None
    uipc_cp_shim_ok: bool = True
    uipc_cp_shim_audit: Optional[Phase21UipcCpShimReport] = None


def run_offline_candidate_dry_run(
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    vfat_mode: str = "8m_ram",
    include_p10_keymap: bool = True,
    compiled_worker: Optional[CompiledWorkerArtifact] = None,
    precomputed_tier0_result: Optional[Tier0UnicornRunResult] = None,
    precomputed_rollback_drill: Optional[RollbackDrillReport] = None,
    precomputed_feature_routing: Optional[FeatureRoutingAuditReport] = None,
    precomputed_backup_mount_tolerance: Optional[Phase6BackupMountToleranceReport] = None,
    precomputed_boot_selector_and_banks: Optional[Phase7BootSelectorAndBankReport] = None,
    precomputed_kernel_dtb: Optional[Phase8KernelDtbReport] = None,
    precomputed_storage_and_ram_budget: Optional[Phase9StorageAndRamBudgetReport] = None,
    precomputed_cp_rtos: Optional[Phase10CpRtosCompatibilityReport] = None,
    precomputed_p1_recovery_bridge: Optional[Phase11P1RecoveryBridgeReport] = None,
    precomputed_stage_a_orchestrator: Optional[Phase12StageABootOrchestratorReport] = None,
    precomputed_kmod_userland_abi: Optional[KmodAndUserlandAbiReport] = None,
    precomputed_peripheral_ux: Optional[Phase17CompatibilityReport] = None,
    precomputed_ap_cp_imaging: Optional[Phase18ImagingAuditReport] = None,
    precomputed_stage_b_appfw: Optional[StageBCombinedAppFwReport] = None,
    precomputed_uipc_cp_shim: Optional[Phase21UipcCpShimReport] = None,
    skip_patch_spec_id: Optional[str] = None,
    corrupt_opelog_vfat: bool = False,
    corrupt_p5_p6_uipc: bool = False,
    corrupt_p7_backup_bridge: bool = False,
    corrupt_stage_a_cpio: bool = False,
    corrupt_feature_routing: bool = False,
    corrupt_backup_mount_tolerance: bool = False,
    corrupt_boot_selector_and_banks: bool = False,
    corrupt_kernel_dtb: bool = False,
    corrupt_storage_and_ram_budget: bool = False,
    corrupt_cp_rtos: bool = False,
    corrupt_p1_recovery_bridge: bool = False,
    corrupt_stage_a_orchestrator: bool = False,
    corrupt_kmod_userland_abi: bool = False,
    corrupt_peripheral_ux: bool = False,
    corrupt_ap_cp_imaging: bool = False,
    corrupt_stage_b_p10: bool = False,
    corrupt_uipc_cp_shim: bool = False,
    missing_manifest_item: Optional[str] = None,
    tamper_manifest_pass2_item: Optional[str] = None,
    inject_write_flag_syscall: bool = False,
    tamper_failsafe_hook: bool = False,
) -> CandidateDryRunReport:
    """Assemble and verify a complete P1..P9 + Fan (+ Stage-B P10) FX6-on-FX3 candidate."""
    repo_root = repo_root.resolve()
    target_specs = get_target_patch_specs(include_p10_keymap=include_p10_keymap)
    target_by_lib: Dict[str, LibraryPatchSpec] = {s.library_name: s for s in target_specs}

    patch_receipts: List[PatchReceipt] = []
    rollback_receipts: List[RollbackReceipt] = []

    with tempfile.TemporaryDirectory(prefix="fx6_candidate_dry_run_") as tmp_str:
        tmp_root = Path(tmp_str)
        adapted_dir = tmp_root / "adapted"
        scripts_dir = tmp_root / "scripts"
        adapted_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir.mkdir(parents=True, exist_ok=True)

        # 1. Stage adapted copies of all 7 binary targets (Stage-A or Stage-B) & verify rollback
        adapted_blobs: Dict[str, bytes] = {}
        donor_blobs: Dict[str, bytes] = {}
        all_rollbacks_ok = True

        for spec in target_specs:
            if skip_patch_spec_id is not None and spec.spec_id == skip_patch_spec_id:
                all_rollbacks_ok = False
                continue

            src_path = resolve_donor_binary_path(spec, fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
            raw = read_donor_bytes_readonly(src_path)
            donor_blobs[spec.library_name] = raw

            patched, p_rec = apply_patch_spec(raw, spec)
            staged_file = adapted_dir / spec.library_name
            staged_file.write_bytes(patched)
            patch_receipts.append(p_rec)

            # Re-read staged binary from temp disk and verify 100% deterministic SHA-256 rollback
            staged_bytes = staged_file.read_bytes()
            restored, rb_rec = rollback_patch_spec(staged_bytes, spec)
            rollback_receipts.append(rb_rec)
            if not rb_rec.donor_sha256_matched or restored != raw:
                all_rollbacks_ok = False

            adapted_blobs[spec.library_name] = staged_bytes

        # 2. Build & audit 8 MiB `opelog.vfat` inside temp directory (P2)
        vfat_bytes, vfat_rec = build_opelog_vfat_image(mode=vfat_mode)
        if corrupt_opelog_vfat:
            mut_vfat = bytearray(vfat_bytes)
            mut_vfat[510:512] = b"\x00\x00"
            vfat_bytes = bytes(mut_vfat)
        vfat_path = tmp_root / "opelog.vfat"
        vfat_path.write_bytes(vfat_bytes)
        vfat_audit = verify_vfat_image(vfat_path.read_bytes(), require_opelog_dirs=True)

        # 3. Generate idempotent boot adaptation scripts & 4-Layer Fail-Safe init2 hook
        p1_script = generate_p1_lut_mount_snippet()
        p2_script = generate_p2_opelog_mount_snippet(backing_image_path="/tmp/opelog.vfat")
        failsafe_hook = generate_failsafe_init2_overlay_hook()
        if tamper_failsafe_hook:
            failsafe_hook = failsafe_hook.replace('rm -f "/tmp/mod_arm_once"', "# tampered")

        (scripts_dir / "10-p1-lut-mount.sh").write_text(p1_script, encoding="utf-8")
        (scripts_dir / "20-p2-opelog-mount.sh").write_text(p2_script, encoding="utf-8")
        (scripts_dir / "00-init2-failsafe.sh").write_text(failsafe_hook, encoding="utf-8")

        # 4. Run Unicorn instruction-level verification across P3, P4, P5, P6, P8, P9, Fan (+ P10)
        rb_so = adapted_blobs.get(
            "libInfraAppRemoteBoard.so",
            apply_patch_spec(
                read_donor_bytes_readonly(fx6_lib_dir / "libInfraAppRemoteBoard.so"),
                target_by_lib["libInfraAppRemoteBoard.so"],
            )[0],
        )
        appfw_so = adapted_blobs.get(
            "appFw.so",
            apply_patch_spec(
                read_donor_bytes_readonly(fx6_lib_dir / "appFw.so"),
                target_by_lib["appFw.so"],
            )[0],
        )
        fan_so = adapted_blobs.get(
            "libfan.so",
            apply_patch_spec(
                read_donor_bytes_readonly(fx6_lib_dir / "libfan.so"),
                target_by_lib["libfan.so"],
            )[0],
        )
        upm_raw = donor_blobs.get("upm.ko") or read_donor_bytes_readonly(fx3_modules_dir / "upm.ko")
        upm_patched = adapted_blobs.get(
            "upm.ko",
            apply_patch_spec(upm_raw, target_by_lib["upm.ko"])[0],
        )

        p3_uni = run_p3_remoteboard_unicorn_check(rb_so)
        p4_mode_uni, p4_val_uni = run_p4_nd_unicorn_sweep(appfw_so, patched_label=True)
        p5_p6_uni = run_p5_p6_uipc_unicorn_audit(appfw_so)
        p7_audit = verify_p7_backup_bridge(
            contract_evidence_path=resolve_lab_work_file(
                "fx6-backup-contract-fix-20261107/contract-evidence.json",
                repo_root=repo_root,
            )
        )
        p8_uni = run_p8_appfw_unicorn_check(appfw_so)
        p9_uni = run_p9_upm_ko_unicorn_check(upm_raw, upm_patched)
        fan_uni = run_fan_libfan_unicorn_check(fan_so)

        appfw_spec = target_by_lib["appFw.so"]
        appfw_so_sha = hashlib.sha256(appfw_so).hexdigest()
        stage_b_appfw_res: Optional[StageBCombinedAppFwReport] = None
        if include_p10_keymap:
            stage_b_appfw_res = precomputed_stage_b_appfw or verify_combined_stage_b_appfw_contract(
                fx6_lib_dir=fx6_lib_dir,
                appfw_raw=donor_blobs.get("appFw.so"),
                precomputed_p4_summaries=(p4_mode_uni, p4_val_uni),
                precomputed_p8_summary=p8_uni,
            )
            stage_b_ok = (
                stage_b_appfw_res.all_checks_passed
                and appfw_so_sha == FX6_APPFW_STAGE_B_SHA256
                and not corrupt_stage_b_p10
            )
        else:
            stage_b_ok = appfw_so_sha == FX6_APPFW_STAGE_A_SHA256 and not corrupt_stage_b_p10

        p5_p6_ok = p5_p6_uni.all_positive_passed and p5_p6_uni.all_negative_captured and not corrupt_p5_p6_uipc
        p7_ok = p7_audit.all_checks_passed and not corrupt_p7_backup_bridge

        unicorn_behavioral_ok = (
            p3_uni.exec_rcv_msg_ret == 0
            and p3_uni.main_thread_ret == 0
            and p4_mode_uni.assert_hit_count == 0
            and p4_mode_uni.clear_output_count == p4_mode_uni.total_combinations
            and p4_val_uni.assert_hit_count == 0
            and p4_val_uni.clear_output_count == p4_val_uni.total_combinations
            and p5_p6_ok
            and p7_ok
            and p8_uni.return_value == 0
            and p8_uni.sp_preserved
            and p9_uni.unpatched_null_callback_faulted
            and p9_uni.patched_completed_cleanly
            and p9_uni.patched_return_value == 0
            and fan_uni.return_value == 1
            and fan_uni.sp_preserved
        )

        verified_matrix: List[str] = []
        p1_specs_present = {"P1_libInfraSetupFile", "P1_libInfraMediaCommon", "P1_libInfraMediaConfig", appfw_spec.spec_id}
        present_ids = {r.spec_id for r in patch_receipts}
        if p1_specs_present.issubset(present_ids) and all_rollbacks_ok:
            verified_matrix.append("P1")
        if vfat_audit.valid:
            verified_matrix.append("P2")
        if "P3_libInfraAppRemoteBoard" in present_ids and p3_uni.exec_rcv_msg_ret == 0 and p3_uni.main_thread_ret == 0:
            verified_matrix.append("P3")
        if appfw_spec.spec_id in present_ids and p4_mode_uni.assert_hit_count == 0 and p4_val_uni.assert_hit_count == 0:
            verified_matrix.append("P4")
        if p5_p6_ok:
            verified_matrix.extend(["P5", "P6"])
        if p7_ok:
            verified_matrix.append("P7")
        if appfw_spec.spec_id in present_ids and p8_uni.return_value == 0 and p8_uni.sp_preserved:
            verified_matrix.append("P8")
        if "P9_upm_ko" in present_ids and p9_uni.patched_completed_cleanly and p9_uni.patched_return_value == 0:
            verified_matrix.append("P9")
        if "Fan_libfan" in present_ids and fan_uni.return_value == 1 and fan_uni.sp_preserved:
            verified_matrix.append("Fan")

        # 5. Assemble Stage-A zero-flash-write RAM-Overlay CPIO `newc` package & run 4-scenario rollback drill
        stage_a_bundle = build_stage_a_ram_overlay_package(
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
            vfat_mode=vfat_mode,
            p7_report=p7_audit,
        )
        cpio_bytes_for_audit = stage_a_bundle.cpio_bytes
        if corrupt_stage_a_cpio:
            mut_cpio = bytearray(cpio_bytes_for_audit)
            mut_cpio[0:6] = b"070799"
            cpio_bytes_for_audit = bytes(mut_cpio)
        stage_a_cpio_path = tmp_root / "stage_a_overlay.cpio"
        stage_a_cpio_path.write_bytes(cpio_bytes_for_audit)
        stage_a_cpio_audit = parse_and_audit_cpio_newc(
            stage_a_cpio_path.read_bytes(),
            required_paths=REQUIRED_STAGE_A_OVERLAY_PATHS,
        )

        failsafe_hook = stage_a_bundle.init2_guard_script
        if tamper_failsafe_hook:
            failsafe_hook = failsafe_hook.replace('rm -f "/tmp/mod_arm_once"', "# tampered")
        (scripts_dir / "init2_guard.sh").write_text(failsafe_hook, encoding="utf-8")

        rollback_drill_res = precomputed_rollback_drill or run_four_layer_rollback_drill(
            overlay_bundle=stage_a_bundle,
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
        )

        feature_routing_res = precomputed_feature_routing or run_feature_routing_verification(
            fx6_lib_dir=fx6_lib_dir,
        )
        feature_routing_ok = feature_routing_res.all_checks_passed and not corrupt_feature_routing

        backup_mount_res = precomputed_backup_mount_tolerance or run_backup_mount_tolerance_verification(
            fx6_lib_dir=fx6_lib_dir,
        )
        backup_mount_tolerance_ok = (
            backup_mount_res.all_checks_passed and not corrupt_backup_mount_tolerance
        )

        boot_selector_banks_res = (
            precomputed_boot_selector_and_banks or run_boot_selector_and_bank_verification()
        )
        boot_selector_and_banks_ok = (
            boot_selector_banks_res.all_checks_passed and not corrupt_boot_selector_and_banks
        )

        kernel_dtb_res = precomputed_kernel_dtb or run_kernel_dtb_verification(
            fx3_modules_dir=fx3_modules_dir
        )
        kernel_dtb_ok = kernel_dtb_res.all_checks_passed and not corrupt_kernel_dtb

        storage_ram_res = precomputed_storage_and_ram_budget or run_storage_and_ram_budget_verification(
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
            scripts_to_audit=(
                ("10-p1-lut-mount.sh", p1_script),
                ("20-p2-opelog-mount.sh", p2_script),
                ("setup_fx6_compat.sh", stage_a_bundle.setup_compat_script),
                ("init2_guard.sh", failsafe_hook),
                ("30-stage-a-orchestrator.sh", stage_a_bundle.stage_a_orchestrator_script),
            ),
            staged_binary_names=tuple(stage_a_bundle.staged_runtime_blobs.keys()),
        )
        storage_and_ram_budget_ok = (
            storage_ram_res.all_checks_passed and not corrupt_storage_and_ram_budget
        )

        cp_rtos_res = precomputed_cp_rtos or run_cp_rtos_compatibility_verification(
            overlay_manifest=stage_a_bundle.overlay_manifest,
            overlay_entry_paths=tuple(e.name for e in stage_a_cpio_audit.entries),
            scripts_to_audit=(
                ("10-p1-lut-mount.sh", p1_script),
                ("20-p2-opelog-mount.sh", p2_script),
                ("setup_fx6_compat.sh", stage_a_bundle.setup_compat_script),
                ("init2_guard.sh", failsafe_hook),
                ("30-stage-a-orchestrator.sh", stage_a_bundle.stage_a_orchestrator_script),
            ),
        )
        cp_rtos_ok = cp_rtos_res.all_checks_passed and not corrupt_cp_rtos

        p1_recovery_bridge_res = (
            precomputed_p1_recovery_bridge
            or run_p1_recovery_bridge_verification(repo_root=repo_root)
        )
        p1_recovery_bridge_ok = (
            p1_recovery_bridge_res.all_checks_passed and not corrupt_p1_recovery_bridge
        )

        stage_a_orchestrator_res = (
            precomputed_stage_a_orchestrator
            or run_stage_a_boot_orchestrator_verification(
                overlay_bundle=stage_a_bundle,
                fx6_lib_dir=fx6_lib_dir,
                fx3_modules_dir=fx3_modules_dir,
            )
        )
        stage_a_orchestrator_ok = (
            stage_a_orchestrator_res.all_checks_passed and not corrupt_stage_a_orchestrator
        )

        kmod_userland_abi_res = (
            precomputed_kmod_userland_abi
            or run_kmod_and_userland_abi_verification(
                fx6_lib_dir=fx6_lib_dir,
                fx3_modules_dir=fx3_modules_dir,
            )
        )
        kmod_userland_abi_ok = (
            kmod_userland_abi_res.all_checks_passed and not corrupt_kmod_userland_abi
        )

        peripheral_ux_res = (
            precomputed_peripheral_ux
            or verify_peripheral_ux_compatibility()
        )
        peripheral_ux_ok = (
            peripheral_ux_res.all_passed and not corrupt_peripheral_ux
        )

        ap_cp_imaging_res = (
            precomputed_ap_cp_imaging
            or verify_ap_cp_imaging_pipeline()
        )
        ap_cp_imaging_ok = (
            ap_cp_imaging_res.passed and not corrupt_ap_cp_imaging
        )

        uipc_cp_shim_res = (
            precomputed_uipc_cp_shim
            or run_phase21_uipc_cp_shim_verification()
        )
        uipc_cp_shim_ok = (
            uipc_cp_shim_res.passed and not corrupt_uipc_cp_shim
        )

        # 6. Run Tier-0 read-only backup worker in Unicorn to produce real 11-item manifest.json
        tier0_res = precomputed_tier0_result or run_tier0_worker_in_unicorn(compiled_worker=compiled_worker)
        assert tier0_res.manifest_json is not None
        manifest_payload: Dict[str, object] = copy.deepcopy(tier0_res.manifest_json)
        syscall_list: List[Dict[str, object]] = [dict(r) for r in tier0_res.syscall_trace]

        if missing_manifest_item is not None and isinstance(manifest_payload.get("items"), dict):
            manifest_payload["items"].pop(missing_manifest_item, None)  # type: ignore[union-attr]
        if tamper_manifest_pass2_item is not None and isinstance(manifest_payload.get("items"), dict):
            items_dict = manifest_payload["items"]
            if isinstance(items_dict, dict) and tamper_manifest_pass2_item in items_dict:
                entry = items_dict[tamper_manifest_pass2_item]
                if isinstance(entry, dict):
                    entry["pass2_sha256"] = "f" * 64
        if inject_write_flag_syscall:
            syscall_list.append(
                {"nr": 56, "dirfd": -100, "path": "/dev/nflasha", "flags": 0x2, "ret": 99}
            )

        manifest_file = tmp_root / "manifest.json"
        manifest_file.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
        reloaded_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

        final_manifest_audit = verify_tier0_backup_manifest(reloaded_manifest)
        final_syscall_audit = audit_tier0_worker_syscalls(syscall_list)

        candidate_bundle_ok = (
            len(patch_receipts) == len(target_specs)
            and all_rollbacks_ok
            and stage_b_ok
            and vfat_audit.valid
            and unicorn_behavioral_ok
            and tuple(verified_matrix) == COMPLETE_MATRIX_ITEMS
            and stage_a_cpio_audit.valid
            and rollback_drill_res.all_scenarios_passed
            and rollback_drill_res.total_emmc_writes == 0
            and feature_routing_ok
            and backup_mount_tolerance_ok
            and boot_selector_and_banks_ok
            and kernel_dtb_ok
            and storage_and_ram_budget_ok
            and cp_rtos_ok
            and p1_recovery_bridge_ok
            and stage_a_orchestrator_ok
            and kmod_userland_abi_ok
            and peripheral_ux_ok
            and ap_cp_imaging_ok
            and uipc_cp_shim_ok
            and tier0_res.return_code == WORKER_OK
        )

        # 7. Evaluate all 12 pre-flash safety gates via fx3_safety.preflight
        gates_report = evaluate_12_safety_gates(
            repo_root=repo_root,
            tier0_manifest=reloaded_manifest,
            worker_syscall_trace=syscall_list,
            init2_failsafe_hook=failsafe_hook,
            candidate_bundle_verified=candidate_bundle_ok,
            allow_dry_run_gate12=True,
            backup_mount_tolerance_ok=backup_mount_tolerance_ok,
            boot_selector_and_banks_ok=boot_selector_and_banks_ok,
            kernel_dtb_ok=kernel_dtb_ok,
            storage_and_ram_budget_ok=storage_and_ram_budget_ok,
            cp_rtos_ok=cp_rtos_ok,
            p1_recovery_bridge_ok=p1_recovery_bridge_ok,
            stage_a_orchestrator_ok=stage_a_orchestrator_ok,
            kmod_userland_abi_ok=kmod_userland_abi_ok,
            peripheral_ux_ok=peripheral_ux_ok,
            ap_cp_imaging_ok=ap_cp_imaging_ok,
            stage_b_p10_ok=stage_b_ok,
            uipc_cp_shim_ok=uipc_cp_shim_ok,
        )

    temp_cleaned = not Path(tmp_str).exists()
    gates_list = gates_report["gates"]
    assert isinstance(gates_list, list)
    blocked_ids = tuple(
        str(g["gate_id"])
        for g in gates_list
        if isinstance(g, dict) and not str(g.get("status", "")).startswith("VERIFIED")
    )
    verified_cnt = int(gates_report["summary"]["verified_gates"])  # type: ignore[index]
    all_12_ok = verified_cnt == 12 and len(blocked_ids) == 0

    return CandidateDryRunReport(
        candidate_ready=all_12_ok and candidate_bundle_ok and temp_cleaned,
        all_12_gates_verified=all_12_ok,
        verified_gate_count=verified_cnt,
        blocked_gate_ids=blocked_ids,
        verified_matrix_items=tuple(verified_matrix),
        patch_receipts=tuple(patch_receipts),
        rollback_receipts=tuple(rollback_receipts),
        vfat_receipt=vfat_rec,
        vfat_audit=vfat_audit,
        p3_unicorn=p3_uni,
        p4_mode_unicorn=p4_mode_uni,
        p4_value_unicorn=p4_val_uni,
        p5_p6_uipc_unicorn=p5_p6_uni,
        p7_backup_bridge=p7_audit,
        p8_unicorn=p8_uni,
        p9_unicorn=p9_uni,
        fan_unicorn=fan_uni,
        stage_a_overlay_cpio_sha256=stage_a_cpio_audit.archive_sha256,
        stage_a_overlay_cpio_size=stage_a_cpio_audit.archive_size,
        stage_a_cpio_audit=stage_a_cpio_audit,
        rollback_drill=rollback_drill_res,
        feature_routing_audit=feature_routing_res,
        backup_mount_tolerance_audit=backup_mount_res,
        backup_mount_tolerance_ok=backup_mount_tolerance_ok,
        boot_selector_and_bank_audit=boot_selector_banks_res,
        boot_selector_and_banks_ok=boot_selector_and_banks_ok,
        kernel_dtb_audit=kernel_dtb_res,
        kernel_dtb_ok=kernel_dtb_ok,
        storage_and_ram_budget_audit=storage_ram_res,
        storage_and_ram_budget_ok=storage_and_ram_budget_ok,
        cp_rtos_audit=cp_rtos_res,
        cp_rtos_ok=cp_rtos_ok,
        p1_recovery_bridge_audit=p1_recovery_bridge_res,
        p1_recovery_bridge_ok=p1_recovery_bridge_ok,
        stage_a_orchestrator_audit=stage_a_orchestrator_res,
        stage_a_orchestrator_ok=stage_a_orchestrator_ok,
        kmod_userland_abi_audit=kmod_userland_abi_res,
        kmod_userland_abi_ok=kmod_userland_abi_ok,
        peripheral_ux_audit=peripheral_ux_res,
        peripheral_ux_ok=peripheral_ux_ok,
        ap_cp_imaging_audit=ap_cp_imaging_res,
        ap_cp_imaging_ok=ap_cp_imaging_ok,
        tier0_worker_rc=tier0_res.return_code,
        tier0_manifest_audit=final_manifest_audit,
        tier0_syscall_audit=final_syscall_audit,
        safety_gates_report=gates_report,
        temp_dir_cleaned=temp_cleaned,
        stage_b_p10_keymap_enabled=include_p10_keymap,
        stage_b_appfw_sha256=appfw_so_sha,
        stage_b_combined_appfw_verified=(stage_b_ok if include_p10_keymap else False),
        stage_b_p10_summary=stage_b_appfw_res,
        uipc_cp_shim_ok=uipc_cp_shim_ok,
        uipc_cp_shim_audit=uipc_cp_shim_res,
    )
