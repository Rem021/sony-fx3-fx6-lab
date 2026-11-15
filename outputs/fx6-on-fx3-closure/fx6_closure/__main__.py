"""CLI entrypoint for `python3 -m fx6_closure` (Phase 10 Blueprint U1-U5 Closure: CP RTOS U2, Storage/p15 & DDR/tmpfs Budget, DTB/.ko & U5/U3/U4 CLI)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from .backup_bridge_verifier import verify_p7_backup_bridge
from .backup_mount_tolerance_verifier import run_backup_mount_tolerance_verification
from .boot_selector_and_bank_verifier import run_boot_selector_and_bank_verification
from .candidate_builder import DEFAULT_REPO_ROOT, run_offline_candidate_dry_run
from .cp_rtos_compatibility_verifier import run_cp_rtos_compatibility_verification
from .feature_routing_verifier import (
    DEFAULT_FX6_DONOR_BIN_DIR,
    DEFAULT_FX6_INITRD_LIB_DIR,
    run_feature_routing_verification,
)
from .kernel_dtb_compatibility_verifier import run_kernel_dtb_verification
from .nd_unicorn_verifier import (
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
    FAN_LIBFAN_SPEC,
    P1_P4_P8_APPFW_COMBINED_SPEC,
    P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC,
    P9_UPM_KO_SPEC,
    apply_patch_spec,
    resolve_donor_binary_path,
    rollback_patch_spec,
)
from .ram_overlay_packager import build_stage_a_ram_overlay_package
from .rollback_drill import run_four_layer_rollback_drill
from .storage_and_ram_budget_verifier import run_storage_and_ram_budget_verification
from .tier0_unicorn_verifier import run_tier0_worker_in_unicorn
from .uipc_completion_verifier import run_p5_p6_uipc_unicorn_audit


def _cmd_verify_donors(fx6_lib_dir: Path, fx3_modules_dir: Path) -> int:
    records = []
    for spec in ALL_PHASE2_TARGET_SPECS:
        src = resolve_donor_binary_path(spec, fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        raw = src.read_bytes()
        patched, p_rec = apply_patch_spec(raw, spec)
        restored, rb_rec = rollback_patch_spec(patched, spec)
        if restored != raw or not rb_rec.donor_sha256_matched:
            raise RuntimeError(f"Rollback mismatch on {spec.library_name}")
        records.append(
            {
                "spec_id": spec.spec_id,
                "library_name": spec.library_name,
                "elf_kind": spec.elf_kind,
                "file_size": p_rec.file_size,
                "donor_sha256": p_rec.before_sha256,
                "adapted_sha256": p_rec.after_sha256,
                "restored_sha256": rb_rec.restored_sha256,
                "changed_byte_count": p_rec.changed_byte_count,
                "sites": [asdict(r) for r in p_rec.resolutions],
            }
        )
    p7_res = verify_p7_backup_bridge()
    payload = {
        "status": "OK" if p7_res.all_checks_passed else "FAILED",
        "verified_targets": len(records),
        "targets": records,
        "p7_dual_kernel_signature_verified": p7_res.all_checks_passed,
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if p7_res.all_checks_passed else 1


def _cmd_run_unicorn_audit(fx6_lib_dir: Path, fx3_modules_dir: Path) -> int:
    rb_raw = (fx6_lib_dir / "libInfraAppRemoteBoard.so").read_bytes()
    rb_patched, _ = apply_patch_spec(rb_raw, P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC)
    p3_res = run_p3_remoteboard_unicorn_check(rb_patched)

    appfw_raw = (fx6_lib_dir / "appFw.so").read_bytes()
    u_mode, u_val = run_p4_nd_unicorn_sweep(appfw_raw, patched_label=False)
    appfw_patched, _ = apply_patch_spec(appfw_raw, P1_P4_P8_APPFW_COMBINED_SPEC)
    p_mode, p_val = run_p4_nd_unicorn_sweep(appfw_patched, patched_label=True)
    p5_p6_res = run_p5_p6_uipc_unicorn_audit(appfw_patched)
    p7_res = verify_p7_backup_bridge()
    p8_res = run_p8_appfw_unicorn_check(appfw_patched)

    upm_raw = (fx3_modules_dir / "upm.ko").read_bytes()
    upm_patched, _ = apply_patch_spec(upm_raw, P9_UPM_KO_SPEC)
    p9_res = run_p9_upm_ko_unicorn_check(upm_raw, upm_patched)

    fan_raw = (fx6_lib_dir / "libfan.so").read_bytes()
    fan_patched, _ = apply_patch_spec(fan_raw, FAN_LIBFAN_SPEC)
    fan_res = run_fan_libfan_unicorn_check(fan_patched)

    tier0_res = run_tier0_worker_in_unicorn(invoke_reentrant_second_call=True)

    ok = (
        p3_res.exec_rcv_msg_ret == 0
        and p3_res.main_thread_ret == 0
        and p_mode.assert_hit_count == 0
        and p_val.assert_hit_count == 0
        and p5_p6_res.all_positive_passed
        and p5_p6_res.all_negative_captured
        and p7_res.all_checks_passed
        and p8_res.return_value == 0
        and p9_res.patched_completed_cleanly
        and p9_res.patched_return_value == 0
        and fan_res.return_value == 1
        and tier0_res.return_code == 0
        and tier0_res.manifest_audit is not None
        and tier0_res.manifest_audit.valid
        and tier0_res.syscall_audit.valid
    )
    payload = {
        "status": "OK" if ok else "FAILED",
        "p3_remoteboard": asdict(p3_res),
        "p4_unpatched_mode": asdict(u_mode),
        "p4_unpatched_value": asdict(u_val),
        "p4_adapted_mode": asdict(p_mode),
        "p4_adapted_value": asdict(p_val),
        "p5_p6_uipc_completion": asdict(p5_p6_res),
        "p7_backup_sync100_bridge": asdict(p7_res),
        "p8_async_log_wait": asdict(p8_res),
        "p9_upm_null_guard": asdict(p9_res),
        "fan_bkup_valid": asdict(fan_res),
        "tier0_backup_worker": {
            "return_code": tier0_res.return_code,
            "reentrant_second_return_code": tier0_res.reentrant_second_return_code,
            "manifest_audit": asdict(tier0_res.manifest_audit) if tier0_res.manifest_audit else None,
            "syscall_audit": asdict(tier0_res.syscall_audit),
        },
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if ok else 1


def _cmd_run_rollback_drill(fx6_lib_dir: Path, fx3_modules_dir: Path, vfat_mode: str) -> int:
    bundle = build_stage_a_ram_overlay_package(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        vfat_mode=vfat_mode,
    )
    drill = run_four_layer_rollback_drill(
        overlay_bundle=bundle,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )
    ok = (
        bundle.cpio_audit.valid
        and bundle.failsafe_hook_audit.valid
        and drill.all_scenarios_passed
        and drill.total_emmc_writes == 0
        and drill.temp_dir_cleaned
    )
    payload = {
        "status": "OK" if ok else "FAILED",
        "stage_a_cpio_sha256": bundle.cpio_sha256,
        "stage_a_cpio_size": bundle.cpio_size,
        "stage_a_cpio_entries": [e.name for e in bundle.cpio_audit.entries],
        "failsafe_hook_audit": asdict(bundle.failsafe_hook_audit),
        "matrix_item_count": bundle.overlay_manifest["matrix_item_count"],
        "verified_matrix_ids": bundle.overlay_manifest["verified_matrix_ids"],
        "rollback_drill": asdict(drill),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if ok else 1


def _cmd_verify_feature_routing(
    fx6_lib_dir: Path,
    fx6_initrd_lib_dir: Path,
    fx6_bin_dir: Path,
) -> int:
    rep = run_feature_routing_verification(
        fx6_lib_dir=fx6_lib_dir,
        fx6_initrd_lib_dir=fx6_initrd_lib_dir,
        fx6_bin_dir=fx6_bin_dir,
    )
    payload = {
        "status": "OK" if rep.all_checks_passed else "FAILED",
        "all_checks_passed": rep.all_checks_passed,
        "dimension_a_symbol_closure": asdict(rep.dimension_a_symbol_closure),
        "dimension_b_lut_capacity": asdict(rep.dimension_b_lut_capacity),
        "dimension_b_setupfile_mount": asdict(rep.dimension_b_setupfile_mount),
        "dimension_c_contracts_unicorn": asdict(rep.dimension_c_contracts_unicorn),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rep.all_checks_passed else 1


def _cmd_verify_backup_mount_contracts(fx6_lib_dir: Path) -> int:
    rep = run_backup_mount_tolerance_verification(fx6_lib_dir=fx6_lib_dir)
    payload = {
        "status": "OK" if rep.all_checks_passed else "FAILED",
        "all_checks_passed": rep.all_checks_passed,
        "u4_closed": rep.dimension_a_mount_tolerance.u4_closed,
        "dimension_a_mount_tolerance": asdict(rep.dimension_a_mount_tolerance),
        "dimension_b_backup_contracts": asdict(rep.dimension_b_backup_contracts),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rep.all_checks_passed else 1


def _cmd_verify_boot_selector_banks() -> int:
    rep = run_boot_selector_and_bank_verification()
    payload = {
        "status": "OK" if rep.all_checks_passed else "FAILED",
        "all_checks_passed": rep.all_checks_passed,
        "u5_closed": rep.dimension_a_boot_selector.u5_closed,
        "u3_advanced": rep.dimension_b_bank_maps.u3_advanced,
        "dimension_a_boot_selector": asdict(rep.dimension_a_boot_selector),
        "dimension_b_bank_maps": asdict(rep.dimension_b_bank_maps),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rep.all_checks_passed else 1


def _cmd_verify_kernel_dtb(fx3_modules_dir: Path) -> int:
    rep = run_kernel_dtb_verification(fx3_modules_dir=fx3_modules_dir)
    payload = {
        "status": "OK" if rep.all_checks_passed else "FAILED",
        "all_checks_passed": rep.all_checks_passed,
        "dtb_byte_identical": rep.dimension_a_dtb.dtb_byte_identical,
        "p9_upm_integrity_valid": rep.dimension_b_ko.p9_upm_integrity.valid,
        "dimension_a_dtb": asdict(rep.dimension_a_dtb),
        "dimension_b_ko": asdict(rep.dimension_b_ko),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rep.all_checks_passed else 1


def _cmd_verify_storage_ram_budget(fx6_lib_dir: Path, fx3_modules_dir: Path) -> int:
    rep = run_storage_and_ram_budget_verification(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )
    payload = {
        "status": "OK" if rep.all_checks_passed else "FAILED",
        "all_checks_passed": rep.all_checks_passed,
        "edisx_repartition_forbidden": rep.edisx_repartition_forbidden,
        "sector0_mutation_bytes": rep.sector0_mutation_bytes,
        "p15_fits_stock_fx3": rep.p15_fits_stock_fx3,
        "ram_budget_within_safe_bounds": rep.ram_budget_within_safe_bounds,
        "dimension_a_storage": asdict(rep.dimension_a_storage),
        "dimension_b_ddr_tmpfs": asdict(rep.dimension_b_ddr_tmpfs),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rep.all_checks_passed else 1


def _cmd_verify_cp_rtos() -> int:
    rep = run_cp_rtos_compatibility_verification()
    payload = {
        "status": "OK" if rep.all_checks_passed else "FAILED",
        "all_checks_passed": rep.all_checks_passed,
        "u2_closed": rep.u2_closed,
        "p8_cp_mutation_forbidden": rep.p8_cp_mutation_forbidden,
        "cp_mutation_bytes": rep.cp_mutation_bytes,
        "fx3_udtrcp_verified": rep.fx3_udtrcp_verified,
        "nflasha8_artifacts": [asdict(a) for a in rep.nflasha8_artifacts],
        "tomco_audit": asdict(rep.tomco_audit),
        "arm32_startup_audit": asdict(rep.arm32_startup_audit),
        "peripheral_marker_audit": asdict(rep.peripheral_marker_audit),
        "candidate_redline_audit": asdict(rep.candidate_redline_audit),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rep.all_checks_passed else 1


def _cmd_verify_p1_recovery_bridge(repo_root: Path) -> int:
    from .p1_recovery_bridge_verifier import run_p1_recovery_bridge_verification

    rep = run_p1_recovery_bridge_verification(repo_root=repo_root)
    payload = {
        "status": "OK" if rep.all_checks_passed else "FAILED",
        "all_checks_passed": rep.all_checks_passed,
        "p1_recovery_bridge_ok": rep.p1_recovery_bridge_ok,
        "tier0_alignment": asdict(rep.tier0_alignment),
        "p1_container_and_u5_handoff": asdict(rep.p1_container_and_u5_handoff),
        "errors": list(rep.errors),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rep.all_checks_passed else 1


def _cmd_verify_stage_a_orchestrator(fx6_lib_dir: Path, fx3_modules_dir: Path) -> int:
    from .stage_a_boot_orchestrator import run_stage_a_boot_orchestrator_verification

    rep = run_stage_a_boot_orchestrator_verification(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )
    payload = {
        "status": "OK" if rep.all_checks_passed else "FAILED",
        "all_checks_passed": rep.all_checks_passed,
        "stage_a_orchestrator_ok": rep.stage_a_orchestrator_ok,
        "wbi_p5_write_and_hibernation_forbidden": rep.wbi_p5_write_and_hibernation_forbidden,
        "wbi_mutation_bytes": rep.wbi_mutation_bytes,
        "orchestrator_script_sha256": rep.orchestrator_script_sha256,
        "orchestrator_script_bytes": rep.orchestrator_script_bytes,
        "dimension_a_boot_chain_and_wbi": asdict(rep.dimension_a_boot_chain_and_wbi),
        "candidate_wbi_redline": asdict(rep.candidate_wbi_redline),
        "scenario_count": rep.scenario_count,
        "total_sandbox_runs": rep.total_sandbox_runs,
        "total_emmc_writes": rep.total_emmc_writes,
        "total_wbi_writes": rep.total_wbi_writes,
        "total_lingering_mounts": rep.total_lingering_mounts,
        "scenarios": [asdict(s) for s in rep.scenarios],
        "errors": list(rep.errors),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rep.all_checks_passed else 1


def _cmd_verify_kmod_userland_abi(fx6_lib_dir: Path, fx3_modules_dir: Path) -> int:
    from .kmod_and_userland_abi_verifier import run_kmod_and_userland_abi_verification

    rep = run_kmod_and_userland_abi_verification(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )
    payload = {
        "status": "OK" if rep.all_checks_passed else "FAILED",
        "all_checks_passed": rep.all_checks_passed,
        "kmod_userland_abi_ok": rep.kmod_userland_abi_ok,
        "kmod_mutation_count": rep.kmod_mutation_count,
        "fx6_kmod_loaded_count": rep.fx6_kmod_loaded_count,
        "unaccounted_dev_node_count": rep.unaccounted_dev_node_count,
        "unresolved_required_symbols": rep.unresolved_required_symbols,
        "unsatisfied_verneed_count": rep.unsatisfied_verneed_count,
        "missing_dt_needed_count": rep.missing_dt_needed_count,
        "surface_a_kmod_matrix": {
            "all_checks_passed": rep.surface_a_kmod_matrix.all_checks_passed,
            "insmod_drv1_sha256": rep.surface_a_kmod_matrix.insmod_drv1_sha256,
            "insmod_drv2_sha256": rep.surface_a_kmod_matrix.insmod_drv2_sha256,
            "fx3_fx6_insmod_drv1_identical": rep.surface_a_kmod_matrix.fx3_fx6_insmod_drv1_identical,
            "fx3_fx6_insmod_drv2_identical": rep.surface_a_kmod_matrix.fx3_fx6_insmod_drv2_identical,
            "drv1_load_count": rep.surface_a_kmod_matrix.drv1_load_count,
            "drv2_load_count": rep.surface_a_kmod_matrix.drv2_load_count,
            "common_shared_kmod_count": rep.surface_a_kmod_matrix.common_shared_kmod_count,
            "fx3_exclusive_kmod_count": rep.surface_a_kmod_matrix.fx3_exclusive_kmod_count,
            "fx6_exclusive_kmod_names": list(rep.surface_a_kmod_matrix.fx6_exclusive_kmod_names),
            "kmod_mutation_count": rep.surface_a_kmod_matrix.kmod_mutation_count,
            "fx6_kmod_loaded_count": rep.surface_a_kmod_matrix.fx6_kmod_loaded_count,
        },
        "surface_b_dev_nodes": {
            "all_checks_passed": rep.surface_b_dev_nodes.all_checks_passed,
            "scanned_binary_count": rep.surface_b_dev_nodes.scanned_binary_count,
            "unique_dev_path_count": rep.surface_b_dev_nodes.unique_dev_path_count,
            "kernel_devtmpfs_count": rep.surface_b_dev_nodes.kernel_devtmpfs_count,
            "initrd_nflash_count": rep.surface_b_dev_nodes.initrd_nflash_count,
            "drv2_shared_kmod_count": rep.surface_b_dev_nodes.drv2_shared_kmod_count,
            "p1_p2_adapted_partition_count": rep.surface_b_dev_nodes.p1_p2_adapted_partition_count,
            "unaccounted_dev_nodes": list(rep.surface_b_dev_nodes.unaccounted_dev_nodes),
            "p1_patched_zero_nflasha20_verified": rep.surface_b_dev_nodes.p1_patched_zero_nflasha20_verified,
        },
        "surface_c_elf_linkage": {
            "all_checks_passed": rep.surface_c_elf_linkage.all_checks_passed,
            "audited_root_binary_count": rep.surface_c_elf_linkage.audited_root_binary_count,
            "transitive_closure_count": rep.surface_c_elf_linkage.transitive_closure_count,
            "missing_dt_needed_count": rep.surface_c_elf_linkage.missing_dt_needed_count,
            "unresolved_required_symbols": rep.surface_c_elf_linkage.unresolved_required_symbols,
            "patched_aux_unresolved_plt_symbols": rep.surface_c_elf_linkage.patched_aux_unresolved_plt_symbols,
            "appfw_stock_omitted_lazy_plt_count": rep.surface_c_elf_linkage.appfw_stock_omitted_lazy_plt_count,
            "total_verneed_checks": rep.surface_c_elf_linkage.total_verneed_checks,
            "unsatisfied_verneed_count": rep.surface_c_elf_linkage.unsatisfied_verneed_count,
            "glibc_cxxabi_glibcxx_gcc_verified": rep.surface_c_elf_linkage.glibc_cxxabi_glibcxx_gcc_verified,
            "fx3_base_runtime_abi_parity_verified": rep.surface_c_elf_linkage.fx3_base_runtime_abi_parity_verified,
        },
        "errors": list(rep.errors),
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rep.all_checks_passed else 1


def _cmd_dry_run_candidate(repo_root: Path, fx6_lib_dir: Path, fx3_modules_dir: Path, vfat_mode: str) -> int:
    rep = run_offline_candidate_dry_run(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        vfat_mode=vfat_mode,
    )
    payload = {
        "candidate_ready": rep.candidate_ready,
        "all_12_gates_verified": rep.all_12_gates_verified,
        "verified_gate_count": rep.verified_gate_count,
        "blocked_gate_ids": list(rep.blocked_gate_ids),
        "verified_matrix_items": list(rep.verified_matrix_items),
        "temp_dir_cleaned": rep.temp_dir_cleaned,
        "adapted_targets": [r.spec_id for r in rep.patch_receipts],
        "p5_p6_uipc_ok": rep.p5_p6_uipc_unicorn.all_positive_passed and rep.p5_p6_uipc_unicorn.all_negative_captured,
        "p7_backup_bridge_ok": rep.p7_backup_bridge.all_checks_passed,
        "feature_routing_ok": rep.feature_routing_audit.all_checks_passed,
        "backup_mount_tolerance_ok": rep.backup_mount_tolerance_ok,
        "u4_closed": rep.backup_mount_tolerance_audit.dimension_a_mount_tolerance.u4_closed,
        "ram_shadow_bk4_sha256": rep.backup_mount_tolerance_audit.dimension_b_backup_contracts.ram_shadow_bundle_sha256,
        "boot_selector_and_banks_ok": rep.boot_selector_and_banks_ok,
        "u5_closed": rep.boot_selector_and_bank_audit.dimension_a_boot_selector.u5_closed,
        "u3_advanced": rep.boot_selector_and_bank_audit.dimension_b_bank_maps.u3_advanced,
        "kernel_dtb_ok": rep.kernel_dtb_ok,
        "dtb_byte_identical": rep.kernel_dtb_audit.dimension_a_dtb.dtb_byte_identical,
        "p9_ko_integrity_ok": rep.kernel_dtb_audit.dimension_b_ko.p9_upm_integrity.valid,
        "storage_and_ram_budget_ok": rep.storage_and_ram_budget_ok,
        "edisx_repartition_forbidden": rep.storage_and_ram_budget_audit.edisx_repartition_forbidden,
        "sector0_mutation_bytes": rep.storage_and_ram_budget_audit.sector0_mutation_bytes,
        "p15_fits_stock_fx3": rep.storage_and_ram_budget_audit.p15_fits_stock_fx3,
        "ram_budget_within_safe_bounds": rep.storage_and_ram_budget_audit.ram_budget_within_safe_bounds,
        "cp_rtos_ok": rep.cp_rtos_ok,
        "u2_closed": rep.cp_rtos_audit.u2_closed,
        "p8_cp_mutation_forbidden": rep.cp_rtos_audit.p8_cp_mutation_forbidden,
        "cp_mutation_bytes": rep.cp_rtos_audit.cp_mutation_bytes,
        "p1_recovery_bridge_ok": rep.p1_recovery_bridge_ok,
        "stage_a_orchestrator_ok": rep.stage_a_orchestrator_ok,
        "wbi_p5_write_and_hibernation_forbidden": rep.stage_a_orchestrator_audit.wbi_p5_write_and_hibernation_forbidden,
        "wbi_mutation_bytes": rep.stage_a_orchestrator_audit.wbi_mutation_bytes,
        "stage_a_orchestrator_scenarios_passed": rep.stage_a_orchestrator_audit.scenario_count,
        "kmod_userland_abi_ok": rep.kmod_userland_abi_ok,
        "kmod_mutation_count": rep.kmod_userland_abi_audit.kmod_mutation_count,
        "fx6_kmod_loaded_count": rep.kmod_userland_abi_audit.fx6_kmod_loaded_count,
        "unaccounted_dev_node_count": rep.kmod_userland_abi_audit.unaccounted_dev_node_count,
        "unresolved_required_symbols": rep.kmod_userland_abi_audit.unresolved_required_symbols,
        "unsatisfied_verneed_count": rep.kmod_userland_abi_audit.unsatisfied_verneed_count,
        "peripheral_ux_ok": rep.peripheral_ux_ok,
        "p10_keymap_rollback_verified": rep.peripheral_ux_audit.input_audit.p10_rollback_receipt.donor_sha256_matched,
        "ap_cp_imaging_ok": rep.ap_cp_imaging_ok,
        "ap_cp_matched_0x92840747_opcodes": rep.ap_cp_imaging_audit.uipc_queue_scan.total_0x92840747_opcodes_matched_in_fx3_cp,
        "ibis_center_lock_verified": rep.ap_cp_imaging_audit.ibis_safety.center_lock_mechanism_verified,
        "stage_b_p10_keymap_enabled": rep.stage_b_p10_keymap_enabled,
        "stage_b_appfw_sha256": rep.stage_b_appfw_sha256,
        "stage_b_combined_appfw_verified": rep.stage_b_combined_appfw_verified,
        "uipc_cp_shim_ok": rep.uipc_cp_shim_ok,
        "stage_b_p12_wireless_guard_enabled": rep.stage_b_p12_wireless_guard_enabled,
        "stage_b_wlan_rsrc_sha256": rep.stage_b_wlan_rsrc_sha256,
        "wireless_fault_isolation_ok": rep.wireless_fault_isolation_ok,
        "stage_a_overlay_cpio_sha256": rep.stage_a_overlay_cpio_sha256,
        "stage_a_overlay_cpio_size": rep.stage_a_overlay_cpio_size,
        "stage_a_cpio_valid": rep.stage_a_cpio_audit.valid,
        "rollback_drill_passed": rep.rollback_drill.all_scenarios_passed,
        "rollback_drill_emmc_writes": rep.rollback_drill.total_emmc_writes,
        "vfat": asdict(rep.vfat_receipt),
        "tier0_manifest_valid": rep.tier0_manifest_audit.valid,
        "tier0_syscall_valid": rep.tier0_syscall_audit.valid,
        "safety_gates_summary": rep.safety_gates_report["summary"],
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rep.candidate_ready else 1


def _cmd_verify_peripheral_ux(clean_room: bool, output_path: Optional[Path]) -> int:
    from .peripheral_ux_compatibility_verifier import verify_peripheral_ux_compatibility

    rep = verify_peripheral_ux_compatibility(
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = json.dumps(asdict(rep), indent=2) + "\n"
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if rep.all_passed else 1


def _cmd_verify_ap_cp_imaging(clean_room: bool, output_path: Optional[Path]) -> int:
    from .ap_cp_imaging_pipeline_verifier import verify_ap_cp_imaging_pipeline

    rep = verify_ap_cp_imaging_pipeline(
        clean_room_overrides={} if clean_room else None,
    )
    rendered = json.dumps(asdict(rep), indent=2) + "\n"
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if rep.passed else 1


def _cmd_verify_stage_b_p10(fx6_lib_dir: Path, clean_room: bool, output_path: Optional[Path]) -> int:
    from .candidate_builder import verify_combined_stage_b_appfw_contract

    rep = verify_combined_stage_b_appfw_contract(
        fx6_lib_dir=fx6_lib_dir,
        force_synthetic=bool(clean_room),
    )
    rendered = json.dumps(asdict(rep), indent=2) + "\n"
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if rep.all_checks_passed else 1


def _cmd_verify_uipc_cp_shim(clean_room: bool, output_path: Optional[Path]) -> int:
    from .uipc_cp_shim_verifier import run_phase21_uipc_cp_shim_verification

    rep = run_phase21_uipc_cp_shim_verification(
        synthetic_mode=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if rep.passed else 1


def _cmd_verify_wireless_guard(clean_room: bool, output_path: Optional[Path]) -> int:
    from .wireless_fault_isolation_verifier import run_phase22_wireless_fault_isolation_verification

    rep = run_phase22_wireless_fault_isolation_verification(
        synthetic_mode=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if rep.passed else 1


def _cmd_build_readiness_packet(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    tier0_bundle_dir: Optional[Path],
    output_path: Optional[Path],
    clean_room: bool,
) -> int:
    from .hardware_readiness_packet import build_stage_a_hardware_readiness_packet

    pkt = build_stage_a_hardware_readiness_packet(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        tier0_bundle_dir=tier0_bundle_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = pkt.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    ok = pkt.offline_engineering_complete and len(pkt.errors) == 0
    if tier0_bundle_dir is not None:
        ok = ok and pkt.real_tier0_hardware_backup_verified
    return 0 if ok else 1


def _cmd_verify_post_trial(
    h0_bundle_dir: Path,
    h2_bundle_dir: Path,
    h1_log_path: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .stage_a_post_trial_auditor import verify_post_trial_zero_mutation

    receipt = verify_post_trial_zero_mutation(
        h0_bundle_dir=h0_bundle_dir,
        h2_bundle_dir=h2_bundle_dir,
        h1_telemetry_log_path=h1_log_path,
    )
    rendered = receipt.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if receipt.all_checks_passed else 1


def _cmd_run_h0_h1_h2_drill(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    output_path: Optional[Path],
    clean_room: bool,
) -> int:
    from .stage_a_post_trial_auditor import run_h0_h1_h2_lifecycle_drill

    rep = run_h0_h1_h2_lifecycle_drill(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if rep.all_checks_passed else 1


def _cmd_run_stage_b_lifecycle_drill(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    output_path: Optional[Path],
    clean_room: bool,
) -> int:
    from .stage_b_lifecycle_verifier import run_stage_b_lifecycle_drill

    rep = run_stage_b_lifecycle_drill(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if rep.all_checks_passed else 1


def _cmd_build_stage_b_readiness_packet(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    tier0_bundle_dir: Optional[Path],
    output_path: Optional[Path],
    clean_room: bool,
    json_output: bool,
    include_full_dry_run: bool,
) -> int:
    from .stage_b_master_readiness_packet import (
        build_stage_b_master_readiness_packet,
        verify_stage_b_master_readiness_packet,
    )

    pkt = build_stage_b_master_readiness_packet(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        tier0_bundle_dir=tier0_bundle_dir,
        synthetic_clean_room=True if clean_room else None,
        include_full_candidate_dry_run=include_full_dry_run,
    )
    rendered = pkt.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if json_output:
        sys.stdout.write(rendered)
    else:
        sys.stdout.write(rendered)
    v_res = verify_stage_b_master_readiness_packet(pkt.to_dict())
    ok = (
        pkt.offline_engineering_complete
        and len(pkt.errors) == 0
        and v_res.valid
        and (tier0_bundle_dir is None or pkt.real_tier0_hardware_backup_verified)
    )
    return 0 if ok else 1


def _cmd_verify_stage_b_ram_overlay(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    lang: str,
    json_output: bool,
    output_path: Optional[Path],
) -> int:
    from .stage_b_ram_overlay_packager import verify_stage_b_ram_overlay_v2

    rep = verify_stage_b_ram_overlay_v2(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        lang=lang,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"status={'OK' if rep.all_checks_passed else 'FAILED'} "
            f"mode={rep.verification_mode} "
            f"lang={rep.lang}({rep.bk_lang_spec.bk_lang_value:#04x}) "
            f"lock_table={rep.lock_table_count}/13 "
            f"tmpfs_mib={rep.tmpfs_budget_audit.volatile_tmpfs_overlay_mib:.2f}/48.00 "
            f"sandbox={rep.sandbox_drill.passed_count}/{rep.sandbox_drill.scenario_count} "
            f"cpio_sha256={rep.cpio_sha256[:16]}... "
            f"report_sha256={rep.report_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if rep.all_checks_passed else 1


def _cmd_verify_stage_b_candidate(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    lang: str,
    json_output: bool,
    output_path: Optional[Path],
) -> int:
    from .stage_b_candidate_integrator import (
        build_stage_b_integrated_dossier,
        verify_stage_b_integrated_dossier,
    )

    dossier = build_stage_b_integrated_dossier(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        lang=lang,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = dossier.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    v_res = verify_stage_b_integrated_dossier(dossier.to_dict())
    ok = dossier.all_5_pillars_passed and dossier.candidate_ready and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        p2 = dossier.phase48_stage_b_ram_overlay_v2
        p3 = dossier.phase47_unbrick_ladder_and_capsule
        p5 = dossier.phase39_stage_b_master_readiness
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={dossier.schema} "
            f"mode={dossier.verification_mode} "
            f"lang={dossier.selected_lang} "
            f"pillars={dossier.passed_pillar_count}/{dossier.pillar_count} "
            f"16gate={'PASS' if v_res.phase50_16gate_ok else 'FAIL'} "
            f"ram_overlay_mib={p2['tmpfs_budget_audit']['volatile_tmpfs_overlay_mib']:.2f}/48.00 "
            f"unbrick={p3['scenarios_passed']}/{p3['scenario_count']} "
            f"lifecycle={p5['phase35_lifecycle']['passed_scenario_count']}/{p5['phase35_lifecycle']['scenario_count']} "
            f"dossier_sha256={dossier.dossier_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_audit_stage_b_post_trial(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    json_output: bool,
    output_path: Optional[Path],
    h0_bundle_dir: Optional[Path] = None,
    h2_bundle_dir: Optional[Path] = None,
) -> int:
    from .stage_b_post_trial_auditor import (
        run_stage_b_post_trial_forensic_audit,
        verify_stage_b_post_trial_report,
        verify_stage_b_post_trial_zero_persistence,
    )

    if (h0_bundle_dir is None) ^ (h2_bundle_dir is None):
        sys.stderr.write("Both --h0-bundle-dir and --h2-bundle-dir must be specified together\n")
        return 2

    if h0_bundle_dir is not None and h2_bundle_dir is not None:
        rec = verify_stage_b_post_trial_zero_persistence(
            h0_bundle_dir,
            h2_bundle_dir,
            synthetic_clean_room=True if clean_room else None,
        )
        rendered = rec.to_deterministic_json(indent=2)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
        ok = rec.all_checks_passed and rec.zero_persistence_verified
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"status={'OK' if ok else 'FAILED'} "
                f"schema={rec.schema} "
                f"mode={rec.verification_mode} "
                f"classification={rec.classification} "
                f"matched={rec.matched_item_count}/{rec.audited_item_count} "
                f"mutated_bytes={rec.persistent_bytes_mutated} "
                f"wbi_mut={rec.wbi_mutation_bytes} "
                f"cp_mut={rec.cp_mutation_bytes} "
                f"cal_mut={rec.calibration_mutation_bytes} "
                f"c2pa_untouched={rec.c2pa_keystore_untouched} "
                f"exfat_clean={rec.p1_exfat_audit.exfat_media_clean} "
                f"peak_soc_c={rec.serial_thermal_post_mortem.peak_soc_c:.1f} "
                f"receipt_sha256={rec.receipt_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        return 0 if ok else 1

    rep = run_stage_b_post_trial_forensic_audit(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    v_res = verify_stage_b_post_trial_report(rep.to_dict())
    ok = rep.all_checks_passed and rep.all_10_scenarios_passed and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        nom = rep.nominal_receipt
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema} "
            f"mode={rep.verification_mode} "
            f"scenarios={rep.passed_scenario_count}/{rep.scenario_count} "
            f"items={nom.matched_item_count}/{nom.audited_item_count} "
            f"wbi_mut={rep.wbi_mutation_bytes} "
            f"cp_mut={rep.cp_mutation_bytes} "
            f"cal_mut={rep.calibration_mutation_bytes} "
            f"c2pa_untouched={nom.c2pa_keystore_untouched} "
            f"exfat_clean={nom.p1_exfat_audit.exfat_media_clean} "
            f"peak_soc_c={nom.serial_thermal_post_mortem.peak_soc_c:.1f} "
            f"report_sha256={rep.report_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_rehearse_stage_b_closed_loop(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    lang: str,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .stage_b_rehearsal_orchestrator import (
        render_stage_b_rehearsal_markdown,
        run_stage_b_closed_loop_rehearsal,
        verify_stage_b_rehearsal_certificate,
    )

    rep = run_stage_b_closed_loop_rehearsal(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        lang=lang,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_stage_b_rehearsal_markdown(rep), encoding="utf-8")
    v_res = verify_stage_b_rehearsal_certificate(rep.to_dict())
    ok = rep.rehearsal_passed and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema_version} "
            f"mode={rep.verification_mode} "
            f"lang={rep.selected_lang} "
            f"stages={rep.passed_stage_count}/{rep.stage_count} "
            f"h0_surfaces={rep.h0_surface_count} "
            f"h2_drifted={rep.h2_drifted_surface_count} "
            f"4lang_pairs={rep.round13_4lang_pairs_verified}/6 "
            f"tamper_drills={rep.negative_tamper_drills_passed}/10 "
            f"live_attach_auth={rep.hardware_live_attachment_authorized} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"rehearsal_digest_sha256={rep.rehearsal_digest_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_build_stage_b_dossier_v3(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .stage_b_release_dossier_v3 import (
        build_stage_b_release_dossier_v3,
        render_dossier_v3_markdown,
        verify_stage_b_release_dossier_v3,
    )

    dossier = build_stage_b_release_dossier_v3(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = dossier.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_dossier_v3_markdown(dossier), encoding="utf-8")
    v_res = verify_stage_b_release_dossier_v3(dossier.to_dict())
    ok = dossier.all_pillars_simulation_ready and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={dossier.schema_version} "
            f"mode={dossier.verification_mode} "
            f"pillars={dossier.passed_pillar_count}/{dossier.pillar_count} "
            f"gate20={dossier.gate20_offline_verified}/{dossier.gate20_simulated_verified} "
            f"auditors={dossier.firmware_lab_auditors_passed}/{dossier.firmware_lab_auditor_count} "
            f"vm_stages={dossier.vm_coemulation_stages_passed}/{dossier.vm_coemulation_stage_count} "
            f"round14_pairs={dossier.round14_positive_pairs}/18 "
            f"h0_h2_drifted={dossier.drifted_surface_count}/{dossier.h0_surface_count} "
            f"live_attach_auth={dossier.hardware_live_attachment_authorized} "
            f"emmc_writes_auth={dossier.persistent_emmc_writes_authorized} "
            f"dossier_v3_sha256={dossier.dossier_v3_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_verify_stage_b_capstone(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .stage_b_capstone_22gate_verifier import (
        build_stage_b_capstone_22gate_report,
        render_capstone_22gate_markdown,
        verify_stage_b_capstone_22gate,
    )

    rep = build_stage_b_capstone_22gate_report(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_capstone_22gate_markdown(rep), encoding="utf-8")
    v_res = verify_stage_b_capstone_22gate(rep.to_dict())
    ok = rep.all_domains_capstone_ready and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema_version} "
            f"mode={rep.verification_mode} "
            f"domains={rep.passed_domain_count}/{rep.domain_count} "
            f"gate22={rep.gate22_offline_verified}/{rep.gate22_simulated_verified} "
            f"otp={rep.otp_fuse_touches} "
            f"rpmb={rep.rpmb_counter_increments} "
            f"auditors={rep.firmware_lab_auditors_passed}/{rep.firmware_lab_auditor_count} "
            f"vm_stages={rep.vm_coemulation_stages_passed}/{rep.vm_coemulation_stage_count} "
            f"round14_pairs={rep.round14_positive_pairs}/18 "
            f"round15_tabs={rep.round15_tabs_verified}/3 "
            f"round15_runs={rep.round15_runs_verified}/4 "
            f"h0_h2_drifted={rep.drifted_surface_count}/{rep.h0_surface_count} "
            f"live_attach_auth={rep.hardware_live_attachment_authorized} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"capstone_sha256={rep.capstone_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_verify_milestone_90(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .stage_b_milestone90_master_gate import (
        build_stage_b_milestone90_master_gate_report,
        render_milestone90_markdown,
        verify_stage_b_milestone90_master_gate,
    )

    rep = build_stage_b_milestone90_master_gate_report(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone90_markdown(rep), encoding="utf-8")
    v_res = verify_stage_b_milestone90_master_gate(rep.to_dict())
    ok = rep.all_pillars_milestone_ready and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema_version} "
            f"mode={rep.verification_mode} "
            f"pillars={rep.passed_pillar_count}/{rep.pillar_count} "
            f"gate24={rep.gate24_offline_verified}/{rep.gate24_simulated_verified} "
            f"otp={rep.otp_fuse_touches} "
            f"rpmb={rep.rpmb_counter_increments} "
            f"auditors={rep.firmware_lab_auditors_passed}/{rep.firmware_lab_auditor_count} "
            f"vm_stages={rep.vm_coemulation_stages_passed}/{rep.vm_coemulation_stage_count} "
            f"round14_pairs={rep.round14_positive_pairs}/18 "
            f"round16_tabs={rep.round16_tabs_verified}/5 "
            f"round16_pairs={rep.round16_pairwise_deltas_verified}/10 "
            f"round16_runs={rep.round16_runs_verified}/4 "
            f"h0_h2_drifted={rep.drifted_surface_count}/{rep.h0_surface_count} "
            f"live_attach_auth={rep.hardware_live_attachment_authorized} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"milestone90_sha256={rep.milestone90_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_verify_milestone_110(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .stage_b_milestone110_master_gate import (
        build_stage_b_milestone110_master_gate_report,
        render_milestone110_markdown,
        verify_stage_b_milestone110_master_gate,
    )

    rep = build_stage_b_milestone110_master_gate_report(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone110_markdown(rep), encoding="utf-8")
    v_res = verify_stage_b_milestone110_master_gate(rep.to_dict())
    ok = rep.all_pillars_milestone_ready and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema_version} "
            f"mode={rep.verification_mode} "
            f"pillars={rep.passed_pillar_count}/{rep.pillar_count} "
            f"gate32={rep.gate32_offline_verified}/{rep.gate32_simulated_verified} "
            f"recovery={rep.recovery_pillars_passed}/{rep.recovery_pillar_count} "
            f"otp={rep.otp_fuse_touches} "
            f"rpmb={rep.rpmb_counter_increments} "
            f"passive_tx={rep.passive_tx_bytes_emitted} "
            f"auditors={rep.firmware_lab_auditors_passed}/{rep.firmware_lab_auditor_count} "
            f"vm_stages={rep.vm_coemulation_stages_passed}/{rep.vm_coemulation_stage_count} "
            f"round14_pairs={rep.round14_positive_pairs}/18 "
            f"round17_tabs={rep.round17_tabs_verified}/10 "
            f"round17_pairs={rep.round17_pairwise_deltas_verified}/45 "
            f"round19_cats={rep.round19_categories_verified}/11 "
            f"round19_pairs={rep.round19_pairwise_deltas_verified}/55 "
            f"h0_h2_drifted={rep.drifted_surface_count}/{rep.h0_surface_count} "
            f"live_attach_auth={rep.hardware_live_attachment_authorized} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"milestone110_sha256={rep.milestone110_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_verify_milestone_130(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .stage_b_milestone130_master_gate import (
        build_stage_b_milestone130_master_gate_report,
        render_milestone130_markdown,
        verify_stage_b_milestone130_master_gate,
    )

    rep = build_stage_b_milestone130_master_gate_report(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone130_markdown(rep), encoding="utf-8")
    v_res = verify_stage_b_milestone130_master_gate(rep.to_dict())
    ok = rep.all_pillars_milestone_ready and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema_version} "
            f"mode={rep.verification_mode} "
            f"pillars={rep.passed_pillar_count}/{rep.pillar_count} "
            f"gate40={rep.gate40_offline_verified}/{rep.gate40_simulated_verified} "
            f"recovery={rep.recovery_pillars_passed}/{rep.recovery_pillar_count} "
            f"otp={rep.otp_fuse_touches} "
            f"rpmb={rep.rpmb_counter_increments} "
            f"passive_tx={rep.passive_tx_bytes_emitted} "
            f"auditors={rep.firmware_lab_auditors_passed}/{rep.firmware_lab_auditor_count} "
            f"vm_stages={rep.vm_coemulation_stages_passed}/{rep.vm_coemulation_stage_count} "
            f"round14_pairs={rep.round14_positive_pairs}/18 "
            f"round17_tabs={rep.round17_tabs_verified}/10 "
            f"round17_pairs={rep.round17_pairwise_deltas_verified}/45 "
            f"round19_cats={rep.round19_categories_verified}/11 "
            f"round19_pairs={rep.round19_pairwise_deltas_verified}/55 "
            f"round20_24={rep.round20_to_24_rounds_verified}/5({rep.round20_to_24_positive_pairs}/60) "
            f"h0_h2_drifted={rep.drifted_surface_count}/{rep.h0_surface_count} "
            f"live_attach_auth={rep.hardware_live_attachment_authorized} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"milestone130_sha256={rep.milestone130_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_verify_realhw_jiritsu_tier0(
    clean_room: bool,
    json_output: bool,
    output_path: Optional[Path],
    tier0_bundle_dir: Optional[Path],
) -> int:
    from .realhw_jiritsu_and_tier0_dumper_auditor import (
        run_phase136_realhw_jiritsu_tier0_audit,
        verify_phase136_report,
    )

    rep = run_phase136_realhw_jiritsu_tier0_audit(
        tier0_bundle_dir=tier0_bundle_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    v_res = verify_phase136_report(rep.to_dict())
    ok = rep.all_checks_passed and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        p1 = rep.pillar1_jiritsu_stage288
        p2 = rep.pillar2_u4_zero_sector0
        p3 = rep.pillar3_u5_p1_fallback
        p4 = rep.pillar4_tier0_stop_gate
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema} "
            f"mode={rep.verification_mode} "
            f"decoder={p1.decoder_backend} "
            f"u6_cmds={p1.u6_command_count}(direct_nflasha={len(p1.u6_direct_setting_or_nflasha_opcodes)}) "
            f"stage288_p0={p1.stage288_hardening.all_p0_items_closed} "
            f"u4_closed={p2.u4_closed}(strategy_a={p2.strategy_a_bridge.valid}) "
            f"u5_closed={p3.u5_closed} "
            f"tier0_ok={p4.all_checks_passed}(neg={p4.negative_gate_drills_passed}/5) "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"usb_attach={rep.usb_device_attach_executed} "
            f"report_sha256={rep.report_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_verify_sd_stageb_bundle_uninstaller(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    lang: str,
    json_output: bool,
    output_path: Optional[Path],
) -> int:
    from .realhw_sd_stageb_bundle_and_uninstaller import (
        run_phase143_sd_stageb_bundle_uninstaller_audit,
        verify_phase143_report,
    )

    rep = run_phase143_sd_stageb_bundle_uninstaller_audit(
        lang=lang,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    v_res = verify_phase143_report(rep.to_dict())
    ok = rep.all_checks_passed and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        p1 = rep.pillar1_bundle_builder
        p2 = rep.pillar2_escape_hatch_launcher
        p3 = rep.pillar3_atomic_uninstaller_h0_h3
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema} "
            f"mode={rep.verification_mode} "
            f"lang={rep.lang} "
            f"sd_entries={p1.sd_entry_count} "
            f"tmpfs_mib={p1.ram_tmpfs_mib:.3f} "
            f"eh_scenarios={p2.passed_scenario_count}/{p2.scenario_count} "
            f"eh1_us={p2.eh1_observed_latency_us} "
            f"h0_eq_h3={p3.h0_equals_h3_count}/{p3.surface_count} "
            f"power_loss={p3.power_loss_drills_passed}/{p3.power_loss_drill_count} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"sd_written={rep.sd_physical_media_written} "
            f"report_sha256={rep.report_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_verify_milestone_147(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone147_master_gate import (
        build_realhw_milestone147_master_gate_report,
        render_milestone147_markdown,
        verify_realhw_milestone147_master_gate,
    )

    rep = build_realhw_milestone147_master_gate_report(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone147_markdown(rep), encoding="utf-8")
    v_res = verify_realhw_milestone147_master_gate(rep.to_dict())
    ok = rep.all_pillars_milestone_ready and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema_version} "
            f"mode={rep.verification_mode} "
            f"pillars={rep.passed_pillar_count}/{rep.pillar_count} "
            f"gate44={rep.gate44_offline_verified}/{rep.gate44_simulated_verified} "
            f"recovery={rep.recovery_pillars_passed}/{rep.recovery_pillar_count} "
            f"otp={rep.otp_fuse_touches} "
            f"rpmb={rep.rpmb_counter_increments} "
            f"passive_tx={rep.passive_tx_bytes_emitted} "
            f"auditors={rep.firmware_lab_auditors_passed}/{rep.firmware_lab_auditor_count} "
            f"vm_stages={rep.vm_coemulation_stages_passed}/{rep.vm_coemulation_stage_count} "
            f"p136_u456={rep.p136_u4_u5_u6_closed} "
            f"p143_eh1_us={rep.p143_sd_escape_absent_us} "
            f"h0_eq_h3={rep.p143_h0_equals_h3_count}/{rep.p143_h0_h3_surface_count} "
            f"r28={rep.r28_runs_verified}/3 "
            f"r29={rep.r29_runs_verified}/3 "
            f"live_attach_auth={rep.hardware_live_attachment_authorized} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"spi_nor_auth={rep.spi_nor_write_authorized} "
            f"usb_tx={rep.physical_usb_packets_emitted} "
            f"milestone147_sha256={rep.milestone147_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_verify_milestone_175(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone175_master_gate import (
        build_realhw_milestone175_master_gate_report,
        render_milestone175_markdown,
        verify_realhw_milestone175_master_gate,
    )

    rep = build_realhw_milestone175_master_gate_report(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone175_markdown(rep), encoding="utf-8")
    v_res = verify_realhw_milestone175_master_gate(rep.to_dict())
    ok = rep.all_pillars_milestone_ready and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema_version} "
            f"mode={rep.verification_mode} "
            f"pillars={rep.passed_pillar_count}/{rep.pillar_count} "
            f"gate58={rep.gate58_offline_verified}/{rep.gate58_simulated_verified} "
            f"recovery={rep.recovery_pillars_passed}/{rep.recovery_pillar_count} "
            f"otp={rep.otp_fuse_touches} "
            f"rpmb={rep.rpmb_counter_increments} "
            f"passive_tx={rep.passive_tx_bytes_emitted} "
            f"auditors={rep.firmware_lab_auditors_passed}/{rep.firmware_lab_auditor_count} "
            f"vm_stages={rep.vm_coemulation_stages_passed}/{rep.vm_coemulation_stage_count} "
            f"p136_u456={rep.p136_u4_u5_u6_closed} "
            f"p143_eh1_us={rep.p143_sd_escape_absent_us} "
            f"h0_eq_h3={rep.p143_h0_equals_h3_count}/{rep.p143_h0_h3_surface_count} "
            f"p154_go={rep.p154_bench_go} "
            f"qemu={rep.qemu_rounds_verified}/7({rep.qemu_runs_verified}/21) "
            f"live_attach_auth={rep.hardware_live_attachment_authorized} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"spi_nor_auth={rep.spi_nor_write_authorized} "
            f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
            f"usb_tx={rep.physical_usb_packets_emitted} "
            f"milestone175_sha256={rep.milestone175_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_verify_milestone_193(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone193_master_gate import (
        build_realhw_milestone193_master_gate_report,
        render_milestone193_markdown,
        verify_realhw_milestone193_master_gate,
    )

    rep = build_realhw_milestone193_master_gate_report(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if force_clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone193_markdown(rep), encoding="utf-8")
    v_res = verify_realhw_milestone193_master_gate(rep.to_dict())
    ok = rep.all_pillars_milestone_ready and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"status={'OK' if ok else 'FAILED'} "
            f"schema={rep.schema_version} "
            f"mode={rep.verification_mode} "
            f"pillars={rep.passed_pillar_count}/{rep.pillar_count} "
            f"gate66={rep.gate66_offline_verified}/{rep.gate66_simulated_verified} "
            f"recovery={rep.recovery_pillars_passed}/{rep.recovery_pillar_count} "
            f"otp={rep.otp_fuse_touches} "
            f"rpmb={rep.rpmb_counter_increments} "
            f"passive_tx={rep.passive_tx_bytes_emitted} "
            f"auditors={rep.firmware_lab_auditors_passed}/{rep.firmware_lab_auditor_count} "
            f"vm_stages={rep.vm_coemulation_stages_passed}/{rep.vm_coemulation_stage_count} "
            f"p136_u456={rep.p136_u4_u5_u6_closed} "
            f"p143_eh1_us={rep.p143_sd_escape_absent_us} "
            f"h0_eq_h3={rep.p143_h0_equals_h3_count}/{rep.p143_h0_h3_surface_count} "
            f"p154_go={rep.p154_bench_go} "
            f"p186_off={rep.p186_offline_go_no_go} "
            f"p186_sim={rep.p186_sim_go_no_go} "
            f"qemu={rep.qemu_rounds_verified}/10({rep.qemu_runs_verified}/30) "
            f"pngs={rep.qemu_png_receipts_verified}/20(max={rep.qemu_png_max_bytes}B) "
            f"live_attach_auth={rep.hardware_live_attachment_authorized} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"spi_nor_auth={rep.spi_nor_write_authorized} "
            f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
            f"usb_tx={rep.physical_usb_packets_emitted} "
            f"leaked={rep.raw_firmware_bytes_leaked} "
            f"milestone193_sha256={rep.milestone193_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_preflight_realhw_bench(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    usb_snapshot: Optional[Path],
    probe_host_usb: bool,
    sd_dir: Optional[Path],
    sd_free_bytes: Optional[int],
    sd_receipt: Optional[Path],
    vault_receipt: Optional[Path],
    camera_cid_sha256: Optional[str],
    simulate_ready_bench: bool,
) -> int:
    from .realhw_bench_preflight_and_usb_classifier import (
        render_phase154_markdown,
        run_realhw_bench_preflight,
        verify_phase154_report,
    )

    rep = run_realhw_bench_preflight(
        usb_snapshot_path=usb_snapshot,
        probe_host_usb=probe_host_usb,
        sd_dir=sd_dir,
        sd_free_bytes_override=sd_free_bytes,
        sd_receipt_path=sd_receipt,
        vault_receipt_path=vault_receipt,
        expected_camera_cid_sha256=camera_cid_sha256,
        simulate_ready_bench=simulate_ready_bench,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=True if clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_phase154_markdown(rep), encoding="utf-8")
    v_res = verify_phase154_report(rep.to_dict())
    ok = rep.bench_go and v_res.valid
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"verdict={rep.verdict} "
            f"status={rep.status} "
            f"mode={rep.verification_mode} "
            f"bench_go={rep.bench_go} "
            f"usb_state={rep.usb_classification.usb_state} "
            f"usb_pkts={rep.usb_packets_emitted} "
            f"iokit_handles={rep.iokit_handles_opened} "
            f"sd_ok={rep.sd_staging_audit.passed} "
            f"locks_13={rep.sd_staging_audit.stage_b_13_locks_verified}/13 "
            f"rcpt_ok={rep.dual_copy_receipt_audit.passed} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"report_sha256={rep.report_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_preflight_card_insert(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    dry_run_simulated: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    sd_dir: Optional[Path],
    exfat_vbr: Optional[Path],
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: Optional[str],
    body_serial: Optional[str],
    emmc_cid: Optional[str],
    battery_soc: float,
    battery_voltage: float,
    body_temp_c: float,
    uart_1v8_attached: bool,
    vmc_bncm1_attached: bool,
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        build_default_h0_baselines,
        render_phase186_markdown,
        run_card_insert_preflight,
        verify_phase186_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else None
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = run_card_insert_preflight(
        dry_run_simulated=dry_run_simulated,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        slot1_exfat_vbr_path=exfat_vbr,
        sd_dir=sd_dir,
        receipt_a_path=receipt_a,
        receipt_b_path=receipt_b,
        model_id=parsed_model_id,
        body_fw=body_fw,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_a,
        h0_baselines_b=h0_b,
        np_fz100_soc_pct=battery_soc,
        np_fz100_voltage_v=battery_voltage,
        body_temp_c=body_temp_c,
        uart_rx_1v8_attached=uart_1v8_attached,
        vmc_bncm1_ltc_attached=vmc_bncm1_attached,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_phase186_markdown(rep), encoding="utf-8")
    v_res = verify_phase186_report(rep.to_dict())
    ok = v_res.valid and (
        (rep.simulated_dry_run and rep.all_4_gates_passed)
        or rep.card_insert_authorized
    )
    if json_output:
        sys.stdout.write(rendered)
    else:
        summary = (
            f"go_no_go={rep.go_no_go} "
            f"mode={rep.verification_mode} "
            f"dry_run={rep.simulated_dry_run} "
            f"gates={rep.gates_passed}/{rep.gate_count} "
            f"card_insert_auth={rep.card_insert_authorized} "
            f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
            f"spi_nor_auth={rep.spi_nor_write_authorized} "
            f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
            f"usb_pkts={rep.physical_usb_packets_emitted} "
            f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
            f"report_sha256={rep.report_sha256[:16]}...\n"
        )
        sys.stdout.write(summary)
    return 0 if ok else 1


def _cmd_preflight_bench_cable_fan_slot1(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_ready_bench: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    power_source: str,
    battery_soc: float,
    battery_voltage: float,
    dc_c1_watts: float,
    dc_c1_cable_amps: float,
    dc_c1_emarked_5a: bool,
    usb_mode: str,
    expect_usb_streaming_uvc: bool,
    vmc_bncm1_attached: bool,
    vmc_bncm1_port: str,
    vmc_bncm1_direction: str,
    uart_1v8_attached: bool,
    fan_mode: str,
    auto_power_off_temp: str,
    body_temp_c: float,
    big6_lower_left: str,
    slot1_media_type: str,
    lut_dir_path: Optional[str],
    camset_dir_path: Optional[str],
    slot1_dir: Optional[Path],
    camset_slot: int,
    exposure_mode: str,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_bench_cable_fan_and_slot1_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        GO_NO_GO_READONLY_BENCH_PREFLIGHT_VERIFIED,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
        render_phase204_markdown,
        run_bench_cable_fan_and_slot1_preflight,
        verify_phase204_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = run_bench_cable_fan_and_slot1_preflight(
        simulate_ready_bench=simulate_ready_bench,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        power_source=power_source,
        np_fz100_soc_pct=battery_soc,
        np_fz100_voltage_v=battery_voltage,
        dc_c1_pd_watts=dc_c1_watts,
        dc_c1_cable_amps=dc_c1_cable_amps,
        dc_c1_emarked_5a=dc_c1_emarked_5a,
        usb_connection_mode=usb_mode,
        expect_usb_streaming_uvc=expect_usb_streaming_uvc,
        vmc_bncm1_attached=vmc_bncm1_attached,
        vmc_bncm1_port=vmc_bncm1_port,
        vmc_bncm1_direction=vmc_bncm1_direction,
        uart_rx_1v8_attached=uart_1v8_attached,
        fan_mode=fan_mode,
        auto_power_off_temp=auto_power_off_temp,
        body_temp_c=body_temp_c,
        big6_home_lower_left=big6_lower_left,
        slot1_media_type=slot1_media_type,
        lut_dir_path=lut_dir_path,
        camset_dir_path=camset_dir_path,
        slot1_dir=slot1_dir,
        camset_target_slot=camset_slot,
        camera_exposure_mode=exposure_mode,
        receipt_a_path=receipt_a,
        receipt_b_path=receipt_b,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_a,
        h0_baselines_b=h0_b,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_phase204_markdown(rep), encoding="utf-8")
    v_res = verify_phase204_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        GO_NO_GO_READONLY_BENCH_PREFLIGHT_VERIFIED,
    )
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_ready={rep.simulate_ready_bench} "
                f"groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_pkts={rep.physical_usb_packets_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fx6_closure",
        description="FX6-on-FX3 Phase 204 Operator Pre-Bench Power/Cable/Fan/Slot-1 Verifier, Phase 193/175/147 Real-Hardware Master Gates, Phase 186 Card-Insert Preflight, Phase 154 Bench Preflight & Passive USB Classifier, Phase 130/110/90 Milestone Master Gates, U1-U6 Blueprint Closure, p1 Recovery Bridge, Atomic Stage-A/B Boot Orchestrator, Stage-A Kmod/Dev/ELF64 ABI Closure, Peripheral UX/Audio Closure, AP<->Stock-CP Imaging/IBIS Closure, Unified Stage-B Candidate Integrator, Post-Trial Forensic Auditor, Stage-B R0..R6 Rehearsal, Unified Stage-B Release Dossier v3 & Capstone 22-Gate Verifier CLI",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    for cmd_name, help_msg in (
        ("verify-donors", "Verify ELF64 offsets, context, adaptation, 100% SHA-256 rollback, and P7 kernel signatures"),
        ("run-unicorn-audit", "Run Unicorn AArch64 audits across P3, P4, P5, P6, P7, P8, P9, Fan, and Tier-0"),
        ("run-rollback-drill", "Build Stage-A CPIO newc RAM-Overlay and execute 4-Layer Fail-Safe rollback drill"),
        ("verify-feature-routing", "Verify 5 core camera feature routing, ELF64 symbol closure, 16x .cube LUT budget, and dual-slot Unicorn contracts"),
        ("verify-backup-mount-contracts", "Verify U4 storage mount-failure tolerance in Unicorn and synthesize/audit RAM-shadow BK4\\0 contracts"),
        ("verify-boot-selector-banks", "Verify U5 boot-selector (up.sh, ud_send_lsi.elf Unicorn, loader_nor.bin) and U3 Bank 0/1 DDR maps"),
        ("verify-kernel-dtb", "Verify cxd90057.dtb FDT (0xd00dfeed) SoC MMIO/carveout compatibility and .ko vermagic/__versions CRC integrity"),
        ("verify-storage-ram-budget", "Verify 30-partition zero-repartition mapping, edisx redline, p15 /usr budget, and Linux DDR/tmpfs RAM-overlay budget"),
        ("verify-cp-rtos", "Verify U2 CP RTOS (cpapp-b.bin / nflasha8 & tomco.txt) compatibility and Stage-A stock-CP redline"),
        ("verify-p1-recovery-bridge", "Verify Phase 11 cross-package p1 recovery <-> Tier-0 capture alignment and U5 Bank 0 exit handoff"),
        ("verify-stage-a-orchestrator", "Verify Phase 12 nflasha3-initrd startup chain, WBI (p5) hibernation safety redline, and 6-scenario atomic Stage-A boot orchestrator"),
        ("verify-kmod-userland-abi", "Verify Phase 14 Stage-A insmod_drv1/drv2 .ko matrix, userland /dev/* nodes, and ELF64 DT_NEEDED/DYNSYM/VERNEED linkage closure"),
        ("verify-peripheral-ux", "Verify Phase 17 FX3 physical controls (P10 keymap), touch panel, LCD/HDMI OSD routing, and XLR-H1 audio compatibility"),
        ("verify-ap-cp-imaging", "Verify Phase 18 FX6 AP <-> FX3 Stock-CP UIPC queues/opcodes, 3D LUT/Cine EI/Dual ISO, XAVC/AF, and 5-axis IBIS center-lock"),
        ("verify-stage-b-p10", "Verify Phase 20 Stage-B combined P1+P4+P8+P10 appFw.so patch non-overlap, Unicorn 21-key dispatch, and SHA-256 rollback"),
        ("verify-uipc-cp-shim", "Verify Phase 21 P11 AP-side dual-blocking UIPC synthesizer (0x92d2091c RTC & 0x91db059b Smart Handle) and Cine EI/LUT/IBIS bridge"),
        ("verify-wireless-guard", "Verify Phase 22/26 P12 libWlanResource.so 0x70d4 guard, BK4\\0 cold-boot Airplane-Mode RAM shadow, and WF-12 fault isolation"),
        ("dry-run-candidate", "Assemble full P1..P9 + Fan + Stage-B P10 + P11 UIPC Shim + P12 Wireless Guard + U1..U5 CPIO candidate and evaluate 12 safety gates"),
        ("build-readiness-packet", "Build deterministic Stage-A non-persistent hardware readiness packet (stage_a_readiness_packet_v1) and optionally validate a physical FX3 Tier-0 capture bundle"),
        ("build-stage-b-readiness-packet", "Build deterministic Phase 39 Stage-B (P1..P12+Fan) Master Hardware Readiness Packet (stage_b_readiness_packet_v2) unifying Phase 17..38 safety closures"),
        ("verify-post-trial", "Verify Phase H2 post-power-cycle zero-mutation parity (stage_a_post_trial_receipt_v1) between H0 and H2 Tier-0 bundles plus optional H1 orchestrator telemetry"),
        ("run-h0-h1-h2-drill", "Execute full offline Phase H0 -> Phase H1 (/bin/sh orchestrator) -> Phase H2 zero-mutation lifecycle drill + 10-case negative fault-injection suite"),
        ("run-stage-b-lifecycle-drill", "Execute Phase 35 complete Stage-B (P1..P12+Fan) 10-scenario H0 -> H1 -> H2 lifecycle, serial_fault_detector_v2 & cryptographic zero-drift verification"),
        ("verify-stage-b-ram-overlay", "Build deterministic Phase 48 Stage-B (P1..P12+Fan, 13/13) CPIO newc RAM-overlay v2 with BK4 language/Airplane shadow and run 9-scenario init2 sandbox drill"),
        ("verify-stage-b-candidate", "Compose and verify Phase 52 Unified Stage-B End-to-End Candidate Dossier (stage_b_integrated_dossier_v1) across Phase 35..50 pillars"),
        ("audit-stage-b-post-trial", "Run Phase 62 Stage-B H0-vs-H2 Post-Trial Zero-Persistence Forensic Differ & 10-Scenario Anomaly Classifier (stage_b_post_trial_forensic_audit_v1)"),
        ("rehearse-stage-b-closed-loop", "Execute Phase 68 7-stage zero-write Stage-B R0..R6 closed-loop hardware rehearsal (stage_b_closed_loop_rehearsal_v1)"),
        ("build-stage-b-dossier-v3", "Build and verify Phase 76 6-Pillar Unified Stage-B Release Dossier v3 (stage_b_release_dossier_v3)"),
        ("verify-stage-b-capstone", "Verify Phase 83 7-Domain Stage-B Capstone 22-Gate + OTP/RPMB Anti-Rollback + 11-Stage VM + Round 15 Multi-Tab UI Certificate (stage_b_capstone_22gate_v1)"),
        ("verify-milestone-90", "Verify Phase 90 6-Pillar Unified 24-Gate + OTP/RPMB/Tier-0 + 16-Auditor + 13-Stage VM + Round 16 Master Gate (stage_b_milestone90_master_gate_v1)"),
        ("verify-milestone-110", "Verify Phase 110 6-Pillar Century+10 Master Gate (32-Gate + 10-Pillar Recovery + >=20 Auditors + >=18 VM + R14/R17/R19 UI Closures, stage_b_milestone110_master_gate_v1)"),
        ("verify-milestone-130", "Verify Phase 130 6-Pillar Master Gate (40-Gate + >=13 Recovery + >=24 Auditors + >=21 VM + R14/R17/R19/R20..24 UI Closures, stage_b_milestone130_master_gate_v1)"),
        ("verify-realhw-jiritsu-tier0", "Verify Phase 136 Stage-288 libJiritsu.so SET_FILE2 P0 hardening, U4/U5/U6 disassembly closures & Tier-0 cold-backup stop-gate"),
        ("verify-sd-stageb-bundle-uninstaller", "Verify Phase 143 BYOF SD-Card Stage-B bundle builder, im.elf escape-hatch launcher & H0==H3 16-surface atomic uninstaller"),
        ("verify-milestone-147", "Verify Milestone Phase 147 6-Pillar Real-Hardware Bench Readiness Master Gate (44-Gate + >=17 Recovery + >=28 Auditors + >=24 VM + Ph136/143 U4/U5/U6/H0==H3 + FX3 7.02 QEMU R28/R29, realhw_milestone147_master_gate_v1)"),
        ("preflight-realhw-bench", "Run Phase 154 100% passive zero-USB-packet physical bench preflight, ioreg USB mode classifier, SD staging verifier & dual-copy FX3RCPT1 Go/No-Go receipt generator"),
        ("verify-milestone-175", "Verify Milestone Phase 175 Grand Unified 6-Pillar Real-Hardware Final Pre-Bench Master Gate (58-Gate + >=22 Recovery + >=36 Auditors + >=30 VM + Ph136/143/154 + FX3 7.02 QEMU R28..R34, realhw_milestone175_master_gate_v1)"),
        ("preflight-card-insert", "Run Phase 186 host-side final card-insert preflight (Slot-1/2 ExFAT geometry & hygiene, dual-media FX3RCPT1 binding, NP-FZ100/thermal/cable interlock, and EH1..EH3 + H0..H3 dry-run)"),
        ("verify-milestone-193", "Verify Grand Milestone Phase 193 Unified 6-Pillar Real-Hardware ILME-FX3 Ver. 7.02 Pre-Bench Master Gate (66-Gate + >=26 Recovery + >=40 Auditors + >=33 VM + Ph136/143/154/186 + FX3 7.02 QEMU R28..R37, realhw_milestone193_master_gate_v1)"),
        ("preflight-bench-cable-fan-slot1", "Run Phase 204 real-hardware operator pre-bench power/cable (DC-C1 / NP-FZ100 / VMC-BNCM1), 4-mode fan thermal (Always Off block) & Slot-1 CAMSET/.cube vault readiness verifier"),
    ):
        p = sub.add_parser(cmd_name, help=help_msg)
        if cmd_name not in ("verify-post-trial", "verify-realhw-jiritsu-tier0"):
            p.add_argument("--fx6-lib-dir", type=Path, default=DEFAULT_FX6_DONOR_LIB_DIR)
            p.add_argument("--fx3-modules-dir", type=Path, default=DEFAULT_FX3_MODULES_DIR)
        if cmd_name == "verify-feature-routing":
            p.add_argument("--fx6-initrd-lib-dir", type=Path, default=DEFAULT_FX6_INITRD_LIB_DIR)
            p.add_argument("--fx6-bin-dir", type=Path, default=DEFAULT_FX6_DONOR_BIN_DIR)
        if cmd_name in ("dry-run-candidate", "run-rollback-drill"):
            p.add_argument("--vfat-mode", default="8m_ram", choices=["8m_ram", "16m_log", "44.5m_log", "44.5m_fat32"])
        if cmd_name in ("dry-run-candidate", "verify-p1-recovery-bridge", "build-readiness-packet", "build-stage-b-readiness-packet", "run-stage-b-lifecycle-drill", "verify-stage-b-candidate", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-milestone-147", "verify-milestone-175", "verify-milestone-193"):
            p.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
        if cmd_name in ("verify-peripheral-ux", "verify-ap-cp-imaging", "verify-stage-b-p10", "verify-uipc-cp-shim", "verify-wireless-guard", "verify-stage-b-ram-overlay", "verify-stage-b-candidate", "audit-stage-b-post-trial", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-realhw-jiritsu-tier0", "verify-sd-stageb-bundle-uninstaller", "verify-milestone-147", "preflight-realhw-bench", "verify-milestone-175"):
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write audit report")
            p.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic offline verification mode")
        if cmd_name == "verify-milestone-193":
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write Milestone 193 master report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force clean-room synthetic offline verification mode")
        if cmd_name in ("verify-stage-b-ram-overlay", "verify-stage-b-candidate", "rehearse-stage-b-closed-loop", "verify-sd-stageb-bundle-uninstaller"):
            p.add_argument("--lang", default="en", choices=["en", "schinese", "tchinese", "japanese"], help="Select Stage-B BK_LANG (0x02cf019c) shadow language")
        if cmd_name in ("verify-stage-b-ram-overlay", "verify-stage-b-candidate", "audit-stage-b-post-trial", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-realhw-jiritsu-tier0", "verify-sd-stageb-bundle-uninstaller", "verify-milestone-147", "preflight-realhw-bench", "verify-milestone-175", "preflight-card-insert", "verify-milestone-193", "preflight-bench-cable-fan-slot1"):
            p.add_argument("--json", action="store_true", help="Emit full deterministic JSON report to stdout")
        if cmd_name in ("rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-milestone-147", "preflight-realhw-bench", "verify-milestone-175", "preflight-card-insert", "verify-milestone-193", "preflight-bench-cable-fan-slot1"):
            p.add_argument("--markdown-out", type=Path, default=None, help="Optional Markdown report path to write certificate/dossier")
        if cmd_name == "preflight-bench-cable-fan-slot1":
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write Phase 204 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-ready-bench", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--power-source", default="USB_PD_BODY", help="Bench power mode: USB_PD_BODY or DC_C1_COUPLER")
            p.add_argument("--battery-soc", type=float, default=88.0, help="NP-FZ100 battery state-of-charge percentage (>= 51.0% for USB_PD_BODY)")
            p.add_argument("--battery-voltage", type=float, default=8.00, help="NP-FZ100 battery voltage in Volts (7.20V..8.50V)")
            p.add_argument("--dc-c1-watts", type=float, default=65.0, help="DC-C1 USB-PD adapter rated wattage (>= 65.0W)")
            p.add_argument("--dc-c1-cable-amps", type=float, default=5.0, help="DC-C1 USB-C cable current rating in Amps (>= 5.0A)")
            p.add_argument("--no-dc-c1-emarked-5a", dest="dc_c1_emarked_5a", action="store_false", help="Indicate USB-C cable lacks 5A e-Marker")
            p.add_argument("--usb-mode", default="MASS_STORAGE", help="Camera USB connection mode (rejects USB_STREAMING/UVC on ILME-FX3)")
            p.add_argument("--expect-usb-streaming-uvc", action="store_true", help="Test/flag UVC [USB Streaming] expectation (rejected on ILME-FX3 0x91030080)")
            p.add_argument("--vmc-bncm1-attached", action="store_true", help="Indicate VMC-BNCM1 (A-5051-506-A) BNC timecode cable is attached")
            p.add_argument("--vmc-bncm1-port", default="DISCONNECTED", help="Port where VMC-BNCM1 is connected (BODY_MULTI_MICRO_USB or DISCONNECTED)")
            p.add_argument("--vmc-bncm1-direction", default="NONE", help="BNC timecode direction (TC_IN or NONE; reverse TC_OUT rejected)")
            p.add_argument("--uart-1v8-attached", action="store_true", help="Indicate 1.8V passive UART RX triage is attached on Multi-USB Pins 8/9/10")
            p.add_argument("--fan-mode", default="Auto", help="FX3 4-mode [Fan Control]: Auto, Minimum, Off in Rec, Always Off")
            p.add_argument("--auto-power-off-temp", default="High", help="FX3 [Auto Power OFF Temp.]: Standard or High")
            p.add_argument("--body-temp-c", type=float, default=29.5, help="Camera body start temperature in Celsius (< 45.0C)")
            p.add_argument("--big6-lower-left", default="Aperture", help="BIG6 [Home (Lower Left)] setting: Aperture or ND Filter")
            p.add_argument("--slot1-media-type", default="SDXC", help="Slot-1 media type: SDXC or CFEXPRESS_A")
            p.add_argument("--lut-dir-path", default=None, help="Optional Slot-1 .cube LUT directory path to validate")
            p.add_argument("--camset-dir-path", default=None, help="Optional Slot-1 CAMSET .DAT directory path to validate")
            p.add_argument("--slot1-dir", type=Path, default=None, help="Optional Slot-1 directory to scan O_RDONLY for symlinks/._*/BODYDATA.DAT")
            p.add_argument("--camset-slot", type=int, default=1, help="Target CAMSET slot number (must be 1)")
            p.add_argument("--exposure-mode", default="Flexible Exposure", help="Current camera exposure mode (CAMSET disabled in MR mode)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-card-insert":
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write Phase 186 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--dry-run-simulated", action="store_true", help="Run full simulated pre-card-insert gates C1..C4 dry-run without authorizing physical card insert")
            p.add_argument("--sd-dir", type=Path, default=None, help="Candidate Slot-1 ExFAT SD/CFexpress staging root directory to inspect O_RDONLY")
            p.add_argument("--exfat-vbr", type=Path, default=None, help="Optional path to 512B/6KiB Slot-1 ExFAT boot sector image to audit O_RDONLY")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A (e.g., Host Vault)")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (separate physical device st_dev_b)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default=None, help="Target FX3 body firmware version (must be 7.02, >= 2.04 floor)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
            p.add_argument("--battery-soc", type=float, default=92.0, help="NP-FZ100 battery state-of-charge percentage (must be >= 80.0)")
            p.add_argument("--battery-voltage", type=float, default=8.05, help="NP-FZ100 battery voltage in Volts (must be >= 7.6V and <= 8.5V)")
            p.add_argument("--body-temp-c", type=float, default=29.5, help="Camera body start temperature in Celsius (must be < 45.0C)")
            p.add_argument("--uart-1v8-attached", action="store_true", help="Indicate 1.8V UART RX triage is attached on Multi-Terminal")
            p.add_argument("--vmc-bncm1-attached", action="store_true", help="Indicate VMC-BNCM1 LTC cable is attached on Multi-Terminal (blocked if 1.8V UART attached)")
        if cmd_name == "preflight-realhw-bench":
            p.add_argument("--usb-snapshot", type=Path, default=None, help="Path to passive ioreg -p IOUSB -l -w 0 text or XML plist snapshot")
            p.add_argument("--probe-host-usb", action="store_true", help="Run read-only macOS ioreg subprocess capture (zero IOKit handles or USB packets)")
            p.add_argument("--sd-dir", type=Path, default=None, help="Candidate ExFAT SD card staging root directory to audit O_RDONLY")
            p.add_argument("--sd-free-bytes", type=int, default=None, help="Optional deterministic free-space override (bytes) for SD staging audit")
            p.add_argument("--sd-receipt", type=Path, default=None, help="Path to SD ExFAT 528-byte FX3RCPT1 cold-backup receipt")
            p.add_argument("--vault-receipt", type=Path, default=None, help="Path to Mac Host Vault 528-byte FX3RCPT1 cold-backup receipt")
            p.add_argument("--camera-cid-sha256", default=None, help="Optional expected 64-hex lowercase camera eMMC CID SHA-256")
            p.add_argument("--simulate-ready-bench", action="store_true", help="Synthesize ephemeral offline READY bench fixtures (MSC 054C:0DA1 + Stage-B SD + dual FX3RCPT1) in TemporaryDirectory")
        if cmd_name == "audit-stage-b-post-trial":
            p.add_argument("--h0-bundle-dir", type=Path, default=None, help="Optional archived Phase H0 pre-trial Tier-0 capture directory")
            p.add_argument("--h2-bundle-dir", type=Path, default=None, help="Optional Phase H2 post-power-cycle Tier-0 readback directory")
        if cmd_name in ("build-readiness-packet", "build-stage-b-readiness-packet"):
            p.add_argument("--tier0-bundle-dir", type=Path, default=None, help="Optional path to physical FX3 Tier-0 capture directory")
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write deterministic readiness packet")
            p.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic offline verification mode")
        if cmd_name == "verify-realhw-jiritsu-tier0":
            p.add_argument("--tier0-bundle-dir", type=Path, default=None, help="Optional path to physical FX3 Tier-0 cold-backup bundle directory")
        if cmd_name == "build-stage-b-readiness-packet":
            p.add_argument("--json", action="store_true", help="Emit deterministic JSON packet to stdout")
            p.add_argument("--include-full-dry-run", action="store_true", help="Include slow 165s full candidate dry-run verification")
        if cmd_name == "verify-post-trial":
            p.add_argument("--h0-bundle-dir", type=Path, required=True, help="Path to archived Phase H0 pre-trial Tier-0 capture directory")
            p.add_argument("--h2-bundle-dir", type=Path, required=True, help="Path to Phase H2 post-power-cycle Tier-0 readback directory")
            p.add_argument("--h1-log", type=Path, default=None, help="Optional path to Phase H1 orchestrator telemetry JSON/log or sandbox directory")
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write stage_a_post_trial_receipt_v1")
        if cmd_name in ("run-h0-h1-h2-drill", "run-stage-b-lifecycle-drill"):
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write lifecycle drill report")
            p.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic offline verification mode")

    args = parser.parse_args(argv)
    if args.cmd == "verify-donors":
        return _cmd_verify_donors(args.fx6_lib_dir, args.fx3_modules_dir)
    if args.cmd == "run-unicorn-audit":
        return _cmd_run_unicorn_audit(args.fx6_lib_dir, args.fx3_modules_dir)
    if args.cmd == "run-rollback-drill":
        return _cmd_run_rollback_drill(args.fx6_lib_dir, args.fx3_modules_dir, args.vfat_mode)
    if args.cmd == "verify-feature-routing":
        return _cmd_verify_feature_routing(args.fx6_lib_dir, args.fx6_initrd_lib_dir, args.fx6_bin_dir)
    if args.cmd == "verify-backup-mount-contracts":
        return _cmd_verify_backup_mount_contracts(args.fx6_lib_dir)
    if args.cmd == "verify-boot-selector-banks":
        return _cmd_verify_boot_selector_banks()
    if args.cmd == "verify-kernel-dtb":
        return _cmd_verify_kernel_dtb(args.fx3_modules_dir)
    if args.cmd == "verify-storage-ram-budget":
        return _cmd_verify_storage_ram_budget(args.fx6_lib_dir, args.fx3_modules_dir)
    if args.cmd == "verify-cp-rtos":
        return _cmd_verify_cp_rtos()
    if args.cmd == "verify-p1-recovery-bridge":
        return _cmd_verify_p1_recovery_bridge(args.repo_root)
    if args.cmd == "verify-stage-a-orchestrator":
        return _cmd_verify_stage_a_orchestrator(args.fx6_lib_dir, args.fx3_modules_dir)
    if args.cmd == "verify-kmod-userland-abi":
        return _cmd_verify_kmod_userland_abi(args.fx6_lib_dir, args.fx3_modules_dir)
    if args.cmd == "verify-peripheral-ux":
        return _cmd_verify_peripheral_ux(args.clean_room, args.output)
    if args.cmd == "verify-ap-cp-imaging":
        return _cmd_verify_ap_cp_imaging(args.clean_room, args.output)
    if args.cmd == "verify-stage-b-p10":
        return _cmd_verify_stage_b_p10(args.fx6_lib_dir, args.clean_room, args.output)
    if args.cmd == "verify-uipc-cp-shim":
        return _cmd_verify_uipc_cp_shim(args.clean_room, args.output)
    if args.cmd == "verify-wireless-guard":
        return _cmd_verify_wireless_guard(args.clean_room, args.output)
    if args.cmd == "dry-run-candidate":
        return _cmd_dry_run_candidate(args.repo_root, args.fx6_lib_dir, args.fx3_modules_dir, args.vfat_mode)
    if args.cmd == "build-readiness-packet":
        return _cmd_build_readiness_packet(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.tier0_bundle_dir,
            args.output,
            args.clean_room,
        )
    if args.cmd == "build-stage-b-readiness-packet":
        return _cmd_build_stage_b_readiness_packet(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.tier0_bundle_dir,
            args.output,
            args.clean_room,
            args.json,
            args.include_full_dry_run,
        )
    if args.cmd == "verify-post-trial":
        return _cmd_verify_post_trial(
            args.h0_bundle_dir,
            args.h2_bundle_dir,
            args.h1_log,
            args.output,
        )
    if args.cmd == "run-h0-h1-h2-drill":
        return _cmd_run_h0_h1_h2_drill(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.output,
            args.clean_room,
        )
    if args.cmd == "run-stage-b-lifecycle-drill":
        return _cmd_run_stage_b_lifecycle_drill(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.output,
            args.clean_room,
        )
    if args.cmd == "verify-stage-b-ram-overlay":
        return _cmd_verify_stage_b_ram_overlay(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.lang,
            args.json,
            args.output,
        )
    if args.cmd == "verify-stage-b-candidate":
        return _cmd_verify_stage_b_candidate(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.lang,
            args.json,
            args.output,
        )
    if args.cmd == "audit-stage-b-post-trial":
        return _cmd_audit_stage_b_post_trial(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.json,
            args.output,
            args.h0_bundle_dir,
            args.h2_bundle_dir,
        )
    if args.cmd == "rehearse-stage-b-closed-loop":
        return _cmd_rehearse_stage_b_closed_loop(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.lang,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "build-stage-b-dossier-v3":
        return _cmd_build_stage_b_dossier_v3(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "verify-stage-b-capstone":
        return _cmd_verify_stage_b_capstone(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "verify-milestone-90":
        return _cmd_verify_milestone_90(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "verify-milestone-110":
        return _cmd_verify_milestone_110(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "verify-milestone-130":
        return _cmd_verify_milestone_130(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "verify-realhw-jiritsu-tier0":
        return _cmd_verify_realhw_jiritsu_tier0(
            args.clean_room,
            args.json,
            args.output,
            args.tier0_bundle_dir,
        )
    if args.cmd == "verify-sd-stageb-bundle-uninstaller":
        return _cmd_verify_sd_stageb_bundle_uninstaller(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.lang,
            args.json,
            args.output,
        )
    if args.cmd == "verify-milestone-147":
        return _cmd_verify_milestone_147(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "preflight-realhw-bench":
        return _cmd_preflight_realhw_bench(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.json,
            args.markdown_out,
            args.output,
            args.usb_snapshot,
            args.probe_host_usb,
            args.sd_dir,
            args.sd_free_bytes,
            args.sd_receipt,
            args.vault_receipt,
            args.camera_cid_sha256,
            args.simulate_ready_bench,
        )
    if args.cmd == "verify-milestone-175":
        return _cmd_verify_milestone_175(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "preflight-card-insert":
        return _cmd_preflight_card_insert(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.dry_run_simulated,
            args.json,
            args.markdown_out,
            args.output,
            args.sd_dir,
            args.exfat_vbr,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
            args.battery_soc,
            args.battery_voltage,
            args.body_temp_c,
            args.uart_1v8_attached,
            args.vmc_bncm1_attached,
        )
    if args.cmd == "verify-milestone-193":
        return _cmd_verify_milestone_193(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "preflight-bench-cable-fan-slot1":
        return _cmd_preflight_bench_cable_fan_slot1(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_ready_bench,
            args.json,
            args.markdown_out,
            args.output,
            args.power_source,
            args.battery_soc,
            args.battery_voltage,
            args.dc_c1_watts,
            args.dc_c1_cable_amps,
            args.dc_c1_emarked_5a,
            args.usb_mode,
            args.expect_usb_streaming_uvc,
            args.vmc_bncm1_attached,
            args.vmc_bncm1_port,
            args.vmc_bncm1_direction,
            args.uart_1v8_attached,
            args.fan_mode,
            args.auto_power_off_temp,
            args.body_temp_c,
            args.big6_lower_left,
            args.slot1_media_type,
            args.lut_dir_path,
            args.camset_dir_path,
            args.slot1_dir,
            args.camset_slot,
            args.exposure_mode,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
