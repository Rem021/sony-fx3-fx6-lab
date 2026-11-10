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
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fx3_safety.brick_classifier import generate_failsafe_init2_overlay_hook
from fx3_safety.preflight import (
    BackupManifestAudit,
    WorkerSyscallAudit,
    audit_tier0_worker_syscalls,
    evaluate_12_safety_gates,
    verify_tier0_backup_manifest,
)

from .backup_bridge_verifier import (
    P7BackupBridgeAuditReport,
    verify_p7_backup_bridge,
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
from .patcher import (
    ALL_PHASE2_TARGET_SPECS,
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    PatchReceipt,
    RollbackReceipt,
    apply_patch_spec,
    generate_p1_lut_mount_snippet,
    resolve_donor_binary_path,
    rollback_patch_spec,
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
from .vfat_builder import (
    VfatAuditResult,
    VfatBuildReceipt,
    build_opelog_vfat_image,
    generate_p2_opelog_mount_snippet,
    verify_vfat_image,
)


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
COMPLETE_MATRIX_ITEMS: Tuple[str, ...] = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "Fan")


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
    tier0_worker_rc: int
    tier0_manifest_audit: BackupManifestAudit
    tier0_syscall_audit: WorkerSyscallAudit
    safety_gates_report: Dict[str, object]
    temp_dir_cleaned: bool


def run_offline_candidate_dry_run(
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    vfat_mode: str = "8m_ram",
    compiled_worker: Optional[CompiledWorkerArtifact] = None,
    precomputed_tier0_result: Optional[Tier0UnicornRunResult] = None,
    precomputed_rollback_drill: Optional[RollbackDrillReport] = None,
    skip_patch_spec_id: Optional[str] = None,
    corrupt_opelog_vfat: bool = False,
    corrupt_p5_p6_uipc: bool = False,
    corrupt_p7_backup_bridge: bool = False,
    corrupt_stage_a_cpio: bool = False,
    missing_manifest_item: Optional[str] = None,
    tamper_manifest_pass2_item: Optional[str] = None,
    inject_write_flag_syscall: bool = False,
    tamper_failsafe_hook: bool = False,
) -> CandidateDryRunReport:
    """Assemble and verify a complete P1..P9 + Fan FX6-on-FX3 candidate inside `TemporaryDirectory`."""
    repo_root = repo_root.resolve()

    patch_receipts: List[PatchReceipt] = []
    rollback_receipts: List[RollbackReceipt] = []

    with tempfile.TemporaryDirectory(prefix="fx6_candidate_dry_run_") as tmp_str:
        tmp_root = Path(tmp_str)
        adapted_dir = tmp_root / "adapted"
        scripts_dir = tmp_root / "scripts"
        adapted_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir.mkdir(parents=True, exist_ok=True)

        # 1. Stage adapted copies of all 7 binary targets (P1, P3, P4, P8, P9, Fan) & verify rollback
        adapted_blobs: Dict[str, bytes] = {}
        donor_blobs: Dict[str, bytes] = {}
        all_rollbacks_ok = True

        for spec in ALL_PHASE2_TARGET_SPECS:
            if skip_patch_spec_id is not None and spec.spec_id == skip_patch_spec_id:
                all_rollbacks_ok = False
                continue

            src_path = resolve_donor_binary_path(spec, fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
            raw = src_path.read_bytes()
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

        # 4. Run Unicorn instruction-level verification across P3, P4, P5, P6, P8, P9, and Fan
        rb_so = adapted_blobs.get(
            "libInfraAppRemoteBoard.so",
            apply_patch_spec(
                (fx6_lib_dir / "libInfraAppRemoteBoard.so").read_bytes(),
                ALL_PHASE2_TARGET_SPECS[3],
            )[0],
        )
        appfw_so = adapted_blobs.get(
            "appFw.so",
            apply_patch_spec(
                (fx6_lib_dir / "appFw.so").read_bytes(),
                ALL_PHASE2_TARGET_SPECS[5],
            )[0],
        )
        fan_so = adapted_blobs.get(
            "libfan.so",
            apply_patch_spec(
                (fx6_lib_dir / "libfan.so").read_bytes(),
                ALL_PHASE2_TARGET_SPECS[4],
            )[0],
        )
        upm_raw = donor_blobs.get("upm.ko") or (fx3_modules_dir / "upm.ko").read_bytes()
        upm_patched = adapted_blobs.get(
            "upm.ko",
            apply_patch_spec(upm_raw, ALL_PHASE2_TARGET_SPECS[6])[0],
        )

        p3_uni = run_p3_remoteboard_unicorn_check(rb_so)
        p4_mode_uni, p4_val_uni = run_p4_nd_unicorn_sweep(appfw_so, patched_label=True)
        p5_p6_uni = run_p5_p6_uipc_unicorn_audit(appfw_so)
        p7_audit = verify_p7_backup_bridge(contract_evidence_path=repo_root / "work" / "fx6-backup-contract-fix-20261107" / "contract-evidence.json")
        p8_uni = run_p8_appfw_unicorn_check(appfw_so)
        p9_uni = run_p9_upm_ko_unicorn_check(upm_raw, upm_patched)
        fan_uni = run_fan_libfan_unicorn_check(fan_so)

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
        p1_specs_present = {"P1_libInfraSetupFile", "P1_libInfraMediaCommon", "P1_libInfraMediaConfig", "P1_P4_P8_appFw_combined"}
        present_ids = {r.spec_id for r in patch_receipts}
        if p1_specs_present.issubset(present_ids) and all_rollbacks_ok:
            verified_matrix.append("P1")
        if vfat_audit.valid:
            verified_matrix.append("P2")
        if "P3_libInfraAppRemoteBoard" in present_ids and p3_uni.exec_rcv_msg_ret == 0 and p3_uni.main_thread_ret == 0:
            verified_matrix.append("P3")
        if "P1_P4_P8_appFw_combined" in present_ids and p4_mode_uni.assert_hit_count == 0 and p4_val_uni.assert_hit_count == 0:
            verified_matrix.append("P4")
        if p5_p6_ok:
            verified_matrix.extend(["P5", "P6"])
        if p7_ok:
            verified_matrix.append("P7")
        if "P1_P4_P8_appFw_combined" in present_ids and p8_uni.return_value == 0 and p8_uni.sp_preserved:
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
            len(patch_receipts) == len(ALL_PHASE2_TARGET_SPECS)
            and all_rollbacks_ok
            and vfat_audit.valid
            and unicorn_behavioral_ok
            and tuple(verified_matrix) == COMPLETE_MATRIX_ITEMS
            and stage_a_cpio_audit.valid
            and rollback_drill_res.all_scenarios_passed
            and rollback_drill_res.total_emmc_writes == 0
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
        tier0_worker_rc=tier0_res.return_code,
        tier0_manifest_audit=final_manifest_audit,
        tier0_syscall_audit=final_syscall_audit,
        safety_gates_report=gates_report,
        temp_dir_cleaned=temp_cleaned,
    )
