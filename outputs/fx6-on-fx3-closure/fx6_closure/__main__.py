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


def _cmd_verify_milestone_209(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone209_master_gate import (
        build_realhw_milestone209_master_gate_report,
        render_milestone209_markdown,
        verify_realhw_milestone209_master_gate,
    )

    rep = build_realhw_milestone209_master_gate_report(
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
        markdown_out.write_text(render_milestone209_markdown(rep), encoding="utf-8")
    v_res = verify_realhw_milestone209_master_gate(rep.to_dict())
    ok = rep.all_pillars_milestone_ready and v_res.valid
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"status={'OK' if ok else 'FAILED'} "
                f"schema={rep.schema_version} "
                f"mode={rep.verification_mode} "
                f"pillars={rep.passed_pillar_count}/{rep.pillar_count} "
                f"gate72={rep.gate72_offline_verified}/{rep.gate72_simulated_verified} "
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
                f"p204_off={rep.p204_offline_go_no_go} "
                f"p204_sim={rep.p204_sim_go_no_go} "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"qemu={rep.qemu_rounds_verified}/13({rep.qemu_runs_verified}/39) "
                f"pngs={rep.qemu_png_receipts_verified}/26(max={rep.qemu_png_max_bytes}B) "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_tx={rep.physical_usb_packets_emitted} "
                f"leaked={rep.raw_firmware_bytes_leaked} "
                f"milestone209_sha256={rep.milestone209_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 1


def _cmd_preflight_hdmi_proxy_desqueeze_and_simult(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    desqueeze_ratio: str,
    hdmi_raw_output: bool,
    rec_media_dur_hdmi: str,
    require_internal_card_rec: bool,
    ack_hdmi_only_no_card_rec: bool,
    log_shooting_mode: str,
    picture_profile: str,
    hdmi_info_display: str,
    require_unblanked_lcd: bool,
    mc_focus_map_enabled: bool,
    mc_sensor_fps: float,
    simult_recording: bool,
    auto_switch_media: str,
    require_strict_vault_parity: bool,
    slot1_media_type: str,
    slot2_media_type: str,
    slot1_capacity_gb: int,
    slot2_capacity_gb: int,
    proxy_enabled: bool,
    proxy_format: str,
    rec_fps: float,
    sq_enabled: bool,
    sq_fps: float,
    file_name_format: str,
    file_number_mode: str,
    title_name: str,
    shoot_mode: str,
    tc_make: str,
    tc_run: str,
    vmc_bncm1_ext_lk_required: bool,
    rec_lamp_mode: str,
    silent_mode: bool,
    audio_signals: str,
    shockless_wb_mode: str,
    wb_kelvin_k: int,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_hdmi_proxy_desqueeze_and_simult_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        GO_NO_GO_HDMI_PROXY_DESQUEEZE_SIMULT_VERIFIED,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
        evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness,
        render_phase216_markdown,
        verify_phase216_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        desqueeze_ratio=desqueeze_ratio,
        hdmi_raw_output=hdmi_raw_output,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi,
        require_internal_card_recording=require_internal_card_rec,
        ack_hdmi_only_no_internal_card_rec=ack_hdmi_only_no_card_rec,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        hdmi_info_display=hdmi_info_display,
        require_unblanked_camera_lcd=require_unblanked_lcd,
        mc_external_focus_map_enabled=mc_focus_map_enabled,
        mc_sensor_fps=mc_sensor_fps,
        simult_recording_enabled=simult_recording,
        auto_switch_media=auto_switch_media,
        require_strict_dual_vault_parity=require_strict_vault_parity,
        slot1_media_type=slot1_media_type,
        slot2_media_type=slot2_media_type,
        slot1_capacity_gb=slot1_capacity_gb,
        slot2_capacity_gb=slot2_capacity_gb,
        proxy_recording_enabled=proxy_enabled,
        proxy_file_format=proxy_format,
        rec_frame_rate_fps=rec_fps,
        sq_mode_enabled=sq_enabled,
        sq_frame_rate_fps=sq_fps,
        file_name_format=file_name_format,
        file_number_mode=file_number_mode,
        title_name=title_name,
        shoot_mode=shoot_mode,
        tc_make=tc_make,
        tc_run=tc_run,
        vmc_bncm1_ext_lk_required=vmc_bncm1_ext_lk_required,
        rec_lamp_mode=rec_lamp_mode,
        silent_mode_enabled=silent_mode,
        audio_signals_mode=audio_signals,
        shockless_wb_mode=shockless_wb_mode,
        wb_kelvin_k=wb_kelvin_k,
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
        markdown_out.write_text(render_phase216_markdown(rep), encoding="utf-8")
    v_res = verify_phase216_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        GO_NO_GO_HDMI_PROXY_DESQUEEZE_SIMULT_VERIFIED,
    )
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"checklists={rep.checklists_passed}/{rep.checklist_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 1


def _cmd_verify_milestone_221(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone221_master_gate import (
        evaluate_realhw_milestone221_master_gate,
        render_milestone221_markdown,
        verify_realhw_milestone221_master_gate,
    )

    rep = evaluate_realhw_milestone221_master_gate(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=True if force_clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone221_markdown(rep), encoding="utf-8")
    v_res = verify_realhw_milestone221_master_gate(rep.to_dict())
    ok = rep.all_pillars_milestone_ready and v_res.valid
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"status={'OK' if ok else 'FAILED'} "
                f"schema={rep.schema} "
                f"mode={rep.verification_mode} "
                f"pillars={rep.passed_pillar_count}/{rep.pillar_count} "
                f"gate78={rep.gate78_offline_verified}/{rep.gate78_simulated_verified} "
                f"recovery={rep.recovery_pillars_passed}/{rep.recovery_pillar_count} "
                f"otp={rep.otp_fuse_writes} "
                f"rpmb={rep.rpmb_writes} "
                f"passive_tx={rep.passive_tx_bytes} "
                f"auditors={rep.auditors_passed}/{rep.auditors_total} "
                f"vm_stages={rep.vm_stages_passed}/{rep.vm_stages_total} "
                f"p186_off={rep.p186_offline_go_no_go} "
                f"p186_sim={rep.p186_sim_go_no_go} "
                f"p204_off={rep.p204_offline_go_no_go} "
                f"p204_sim={rep.p204_sim_go_no_go} "
                f"p216_off={rep.p216_offline_go_no_go} "
                f"p216_sim={rep.p216_sim_go_no_go} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/16 "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"qemu={rep.qemu_rounds_verified}/15({rep.qemu_runs_verified}/45) "
                f"pngs={rep.qemu_png_receipts_verified}/30(max={rep.qemu_png_max_bytes}B) "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_tx={rep.usb_packets_transmitted} "
                f"leaked={rep.raw_firmware_bytes_leaked} "
                f"milestone221_sha256={rep.milestone221_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 1


def _cmd_verify_milestone_233(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone233_master_gate import (
        evaluate_realhw_milestone233_master_gate,
        render_milestone233_markdown,
        verify_realhw_milestone233_master_gate,
    )

    rep = evaluate_realhw_milestone233_master_gate(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=True if force_clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone233_markdown(rep), encoding="utf-8")
    v_res = verify_realhw_milestone233_master_gate(rep.to_dict())
    ok = rep.all_pillars_milestone_ready and v_res.valid
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"status={'OK' if ok else 'FAILED'} "
                f"schema={rep.schema} "
                f"mode={rep.verification_mode} "
                f"pillars={rep.passed_pillar_count}/{rep.pillar_count} "
                f"gate90={rep.gate90_offline_verified}/{rep.gate90_simulated_verified} "
                f"recovery={rep.recovery_pillars_passed}/{rep.recovery_pillar_count} "
                f"cnflasha_ro={rep.cnflasha_userspace_write_blocked} "
                f"otp={rep.otp_fuse_touches} "
                f"rpmb={rep.rpmb_counter_increments} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"auditors={rep.auditors_passed}/{rep.auditors_total} "
                f"vm_stages={rep.vm_stages_passed}/{rep.vm_stages_total} "
                f"p186_off={rep.p186_offline_go_no_go} "
                f"p186_sim={rep.p186_sim_go_no_go} "
                f"p204_off={rep.p204_offline_go_no_go} "
                f"p204_sim={rep.p204_sim_go_no_go} "
                f"p216_off={rep.p216_offline_go_no_go} "
                f"p216_sim={rep.p216_sim_go_no_go} "
                f"p227_off={rep.p227_offline_go_no_go} "
                f"p227_sim={rep.p227_sim_go_no_go} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/16 "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"qemu={rep.qemu_rounds_verified}/{rep.qemu_rounds_total}({rep.qemu_runs_verified}/{rep.qemu_runs_total}) "
                f"pngs={rep.qemu_png_receipts_verified}/{rep.qemu_png_receipts_total}(max={rep.qemu_png_max_bytes}B) "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_tx={rep.usb_packets_transmitted} "
                f"leaked={rep.raw_firmware_bytes_leaked} "
                f"milestone233_sha256={rep.milestone233_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 1


def _cmd_preflight_pixelmap_ntscpal_powersave_and_autotemp(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    auto_pixel_mapping: str,
    days_since_pixel_mapping: int,
    manual_pixel_mapping: bool,
    battery_soc_pct: float,
    tier0_dump_active: bool,
    unguarded_calibration: bool,
    ntsc_pal_selector: str,
    regional_default_system: str,
    rec_fps: float,
    tc_format: str,
    reset_action: str,
    log_shooting_mode: str,
    gamma_display_assist: str,
    gamma_disp_assist_type: str,
    display_lut: str,
    expect_gamma_assist_hdmi: bool,
    file_name_format: str,
    file_number_mode: str,
    title_name: str,
    cam_id: str,
    reel_number: int,
    slot1_media_type: str,
    slot2_media_type: str,
    custom_folder_requested: bool,
    clip_container_format: str,
    shot_mark1_count: int,
    shot_mark2_count: int,
    image_jump_setting: str,
    shoot_mode: str,
    simult_recording: bool,
    tc_make: str,
    tc_run: str,
    tc_regen_slot: int,
    external_tc_jam_was_active: bool,
    vmc_bncm1_ext_lk_required: bool,
    rec_lamp_mode: str,
    xlr_h1_attached: bool,
    silent_mode: bool,
    audio_signals: str,
    power_save_start_time: str,
    power_source: str,
    usb_power_supply_active: Optional[bool],
    slideshow_active: bool,
    ftp_transfer_active: bool,
    movie_recording_active: bool,
    computer_connection_active: bool,
    hdmi_tv_connection_active: bool,
    ir_remote_ctrl_on: bool,
    bluetooth_rmt_ctrl_on: bool,
    streaming_or_cloud_active: bool,
    p3_75mib_cold_dump_active: bool,
    auto_power_off_temp: str,
    tripod_mounted: bool,
    handheld_active: bool,
    fan_control_mode: str,
    body_temp_c: float,
    steadyshot_mode: str,
    steadyshot_focal_mm: int,
    sq_enabled: bool,
    sq_fps: float,
    hdmi_raw_output: bool,
    zoom_mode: str,
    zoom_scale: float,
    video_resolution_class: str,
    still_file_format: str,
    ciz_focus_area_center_locked: bool,
    ciz_metering_mode: str,
    ciz_face_eye_disabled: bool,
    ciz_tracking_disabled: bool,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        GO_NO_GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_VERIFIED,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
        evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness,
        render_phase227_markdown,
        verify_phase227_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        auto_pixel_mapping=auto_pixel_mapping,
        days_since_manual_pixel_mapping=days_since_pixel_mapping,
        manual_pixel_mapping_requested=manual_pixel_mapping,
        battery_soc_pct=battery_soc_pct,
        tier0_dump_active=tier0_dump_active,
        unguarded_calibration_attempt=unguarded_calibration,
        ntsc_pal_selector=ntsc_pal_selector,
        regional_default_system=regional_default_system,
        rec_frame_rate_fps=rec_fps,
        tc_format=tc_format,
        reset_action=reset_action,
        log_shooting_mode=log_shooting_mode,
        gamma_display_assist=gamma_display_assist,
        gamma_disp_assist_type=gamma_disp_assist_type,
        display_lut=display_lut,
        expect_gamma_assist_on_external_hdmi=expect_gamma_assist_hdmi,
        file_name_format=file_name_format,
        file_number_mode=file_number_mode,
        title_name=title_name,
        cam_id=cam_id,
        reel_number=reel_number,
        slot1_media_type=slot1_media_type,
        slot2_media_type=slot2_media_type,
        custom_folder_name_requested=custom_folder_requested,
        clip_container_format=clip_container_format,
        shot_mark1_count=shot_mark1_count,
        shot_mark2_count=shot_mark2_count,
        image_jump_setting=image_jump_setting,
        shoot_mode=shoot_mode,
        simult_recording_enabled=simult_recording,
        tc_make=tc_make,
        tc_run=tc_run,
        tc_regenerate_reference_slot=tc_regen_slot,
        external_tc_jam_was_active=external_tc_jam_was_active,
        vmc_bncm1_ext_lk_required=vmc_bncm1_ext_lk_required,
        rec_lamp_mode=rec_lamp_mode,
        xlr_h1_attached=xlr_h1_attached,
        silent_mode_enabled=silent_mode,
        audio_signals_mode=audio_signals,
        power_save_start_time=power_save_start_time,
        power_source=power_source,
        usb_power_supply_active=usb_power_supply_active,
        slideshow_playback_active=slideshow_active,
        ftp_transfer_active=ftp_transfer_active,
        movie_recording_active=movie_recording_active,
        computer_connection_active=computer_connection_active,
        hdmi_tv_connection_active=hdmi_tv_connection_active,
        ir_remote_ctrl_on=ir_remote_ctrl_on,
        bluetooth_rmt_ctrl_on=bluetooth_rmt_ctrl_on,
        streaming_or_cloud_active=streaming_or_cloud_active,
        p3_75mib_cold_dump_active=p3_75mib_cold_dump_active,
        auto_power_off_temp=auto_power_off_temp,
        tripod_mounted=tripod_mounted,
        handheld_operation_active=handheld_active,
        fan_control_mode=fan_control_mode,
        body_temp_c=body_temp_c,
        steadyshot_mode=steadyshot_mode,
        steadyshot_manual_focal_mm=steadyshot_focal_mm,
        sq_mode_enabled=sq_enabled,
        sq_frame_rate_fps=sq_fps,
        hdmi_raw_output=hdmi_raw_output,
        zoom_mode=zoom_mode,
        zoom_scale=zoom_scale,
        video_resolution_class=video_resolution_class,
        still_file_format=still_file_format,
        ciz_focus_area_center_locked=ciz_focus_area_center_locked,
        ciz_metering_mode=ciz_metering_mode,
        ciz_face_eye_priority_disabled=ciz_face_eye_disabled,
        ciz_realtime_tracking_disabled=ciz_tracking_disabled,
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
        markdown_out.write_text(render_phase227_markdown(rep), encoding="utf-8")
    v_res = verify_phase227_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        GO_NO_GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_VERIFIED,
    )
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 1


def _cmd_preflight_imagedb_touch_shoeaudio_and_lockop(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    recover_image_db_requested: bool,
    recover_image_db_slot: int,
    battery_soc_pct: float,
    low_battery_warning: bool,
    slot1_contains_tier0_dump: bool,
    slot1_tier0_sha256_verified: bool,
    slot1_wp_locked: bool,
    monitor_flip_direction: str,
    reset_action: str,
    expect_playback_inverted_hflip: bool,
    af_transition_speed: int,
    af_subj_shift_sensitivity: int,
    touch_operation: str,
    touch_sensitivity: str,
    swipe_up: str,
    touch_func_in_shooting: str,
    unattended_tier0_dump_active: bool,
    emphasized_rec_display: str,
    grid_line_display: str,
    grid_line_type: str,
    rec_media_dur_hdmi_output: str,
    hdmi_raw_output: bool,
    hdmi_info_display: str,
    indoor_bench_environment: bool,
    monitor_brightness_mode: str,
    monitor_brightness_level: int,
    display_quality: str,
    bluetooth_rmt_ctrl: str,
    bluetooth_function: str,
    airplane_mode: str,
    expect_ir_remote_usable: bool,
    display_from_my_menu: str,
    shoe_audio_set: str,
    audio_recording: str,
    sq_mode_enabled: bool,
    body_35mm_mic_plugged: bool,
    xlr_h1_attached: bool,
    xlr_h1_mode_switch: str,
    xlr_h1_low_cut_switch: str,
    wind_noise_reduct: str,
    expect_wind_reduct_ext_mic: bool,
    indoor_calm_bench_audio: bool,
    saveload_operation: str,
    saveload_target: str,
    camset_slot_index: int,
    camset_model_code: str,
    camset_contains_excluded: bool,
    lock_operation_parts: str,
    active_key_chord: str,
    lock_chord_hold_seconds: float,
    destructive_format_chord: bool,
    power_source: str,
    usb_power_supply: str,
    usb_power_terminal: str,
    usb_lun_setting: str,
    np_fz100_battery_inserted: bool,
    dc_c1_coupler_inserted: bool,
    battery_removed_under_usb_power: bool,
    exposure_step: str,
    shutter_mode: str,
    shutter_angle_deg: float,
    expect_exp_step_alters_angle: bool,
    audio_out_timing: str,
    silent_mode_enabled: bool,
    audio_signals_mode: str,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_imagedb_touch_shoeaudio_and_lockop_verifier import (
        GO_NO_GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_VERIFIED,
        evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness,
        render_phase248_markdown,
        verify_phase248_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        recover_image_db_requested=recover_image_db_requested,
        recover_image_db_target_slot=recover_image_db_slot,
        battery_soc_pct=battery_soc_pct,
        low_battery_warning_active=low_battery_warning,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_tier0_sha256_verified_off_camera=slot1_tier0_sha256_verified,
        slot1_wp_locked=slot1_wp_locked,
        monitor_flip_direction=monitor_flip_direction,
        reset_action=reset_action,
        expect_playback_inverted_under_horizontal_flip=expect_playback_inverted_hflip,
        af_transition_speed=af_transition_speed,
        af_subj_shift_sensitivity=af_subj_shift_sensitivity,
        touch_operation=touch_operation,
        touch_sensitivity=touch_sensitivity,
        swipe_up=swipe_up,
        touch_func_in_shooting=touch_func_in_shooting,
        unattended_tier0_dump_active=unattended_tier0_dump_active,
        emphasized_rec_display=emphasized_rec_display,
        grid_line_display=grid_line_display,
        grid_line_type=grid_line_type,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        hdmi_raw_output=hdmi_raw_output,
        hdmi_info_display=hdmi_info_display,
        indoor_bench_environment=indoor_bench_environment,
        monitor_brightness_mode=monitor_brightness_mode,
        monitor_brightness_manual_level=monitor_brightness_level,
        display_quality=display_quality,
        bluetooth_rmt_ctrl=bluetooth_rmt_ctrl,
        bluetooth_function=bluetooth_function,
        airplane_mode=airplane_mode,
        expect_ir_remote_usable=expect_ir_remote_usable,
        display_from_my_menu=display_from_my_menu,
        shoe_audio_set=shoe_audio_set,
        audio_recording=audio_recording,
        sq_mode_enabled=sq_mode_enabled,
        body_35mm_mic_plugged=body_35mm_mic_plugged,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_mode_switch=xlr_h1_mode_switch,
        xlr_h1_low_cut_switch=xlr_h1_low_cut_switch,
        wind_noise_reduct=wind_noise_reduct,
        expect_wind_noise_reduct_on_external_mic=expect_wind_reduct_ext_mic,
        indoor_calm_bench_audio=indoor_calm_bench_audio,
        saveload_operation=saveload_operation,
        saveload_target=saveload_target,
        camset_slot_index=camset_slot_index,
        camset_model_code=camset_model_code,
        camset_payload_contains_excluded_items=camset_contains_excluded,
        lock_operation_parts=lock_operation_parts,
        active_key_chord=active_key_chord,
        lock_chord_hold_seconds=lock_chord_hold_seconds,
        destructive_slot_full_format_chord_invoked=destructive_format_chord,
        power_source=power_source,
        usb_power_supply=usb_power_supply,
        usb_power_terminal=usb_power_terminal,
        usb_lun_setting=usb_lun_setting,
        np_fz100_battery_inserted=np_fz100_battery_inserted,
        dc_c1_coupler_inserted=dc_c1_coupler_inserted,
        battery_removed_under_usb_power=battery_removed_under_usb_power,
        exposure_step=exposure_step,
        shutter_mode=shutter_mode,
        shutter_angle_deg=shutter_angle_deg,
        expect_exposure_step_alters_shutter_angle=expect_exp_step_alters_angle,
        audio_out_timing=audio_out_timing,
        silent_mode_enabled=silent_mode_enabled,
        audio_signals_mode=audio_signals_mode,
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
        markdown_out.write_text(render_phase248_markdown(rep), encoding="utf-8")
    v_res = verify_phase248_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        GO_NO_GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_VERIFIED,
    )
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 1


def _cmd_verify_milestone_254(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone254_master_gate import verify_milestone_254_cli

    return verify_milestone_254_cli(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=True if force_clean_room else None,
        json_output=json_output,
        markdown_out=markdown_out,
        output_path=output_path,
    )


def _cmd_verify_milestone_264(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone264_master_gate import verify_milestone_264_cli

    return verify_milestone_264_cli(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=True if force_clean_room else None,
        json_output=json_output,
        markdown_out=markdown_out,
        output_path=output_path,
    )


def _cmd_verify_milestone_295(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone295_master_gate import verify_milestone_295_cli

    return verify_milestone_295_cli(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=True if force_clean_room else None,
        json_output=json_output,
        markdown_out=markdown_out,
        output_path=output_path,
    )


def _cmd_verify_milestone_311(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone311_master_gate import verify_milestone_311_cli

    return verify_milestone_311_cli(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=True if force_clean_room else None,
        simulate_bench_dry_run=simulate_bench_dry_run,
        json_output=json_output,
        markdown_out=markdown_out,
        output_path=output_path,
    )


def _cmd_verify_milestone_324(
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
) -> int:
    from .realhw_milestone324_master_gate import verify_milestone_324_cli

    return verify_milestone_324_cli(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=True if force_clean_room else None,
        simulate_bench_dry_run=simulate_bench_dry_run,
        json_output=json_output,
        markdown_out=markdown_out,
        output_path=output_path,
    )


def _cmd_preflight_diffset_customkey_autoslow_and_apsc(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    reset_action: str,
    diff_set_transition: str,
    diff_set_shutter_checked: bool,
    movie_shutter_mode: str,
    expect_cwb_movie_copy: bool,
    expect_angle_merge: bool,
    rear_dial_assignment: str,
    slot1_contains_tier0_dump: bool,
    slot1_wp_locked: bool,
    slot1_custom_key_access: str,
    remain_shoot_display: str,
    expect_remain_movie_time: bool,
    expect_builtin_evf: bool,
    auto_slow_shutter: str,
    exposure_ctrl_type: str,
    exposure_mode: str,
    flexible_shutter_mode: str,
    iso_mode: str,
    log_shooting_mode: str,
    sq_mode_enabled: bool,
    expect_auto_slow_active: bool,
    expect_auto_slow_angle_overlap: bool,
    hdmi_time_code_output: str,
    hdmi_rec_control: str,
    hdmi_4ch_audio_output: str,
    mi_shoe_4ch_audio_active: bool,
    rec_media_dur_hdmi_output: str,
    breathing_comp: str,
    breathing_comp_compliant_lens: bool,
    hdmi_raw_output: bool,
    sq_240p_or_200p_active: bool,
    expect_breathing_still: bool,
    apsc_s35_shooting: str,
    movie_file_format: str,
    expect_apsc_in_4k_or_raw: bool,
    face_eye_prior_in_af: str,
    face_eye_subject: str,
    right_left_eye_select: str,
    face_eye_frame_disp: str,
    expect_ai_subject_recog_menu: bool,
    hdmi_info_display: str,
    expect_eye_frame_clean_hdmi: bool,
    airplane_mode: str,
    slot1_bodydata_flash_requested: bool,
    release_wo_card: str,
    release_wo_lens: str,
    card_inserted_for_movie_rec: bool,
    movie_internal_rec_requested: bool,
    expect_movie_rec_without_card: bool,
    production_shoot_mode: bool,
    body_only_or_pl_adapter_bench: bool,
    audio_rec_level: int,
    disp_audio_meter_enabled: bool,
    expect_v1_audio_level_menu: bool,
    write_copyright_info: str,
    photographer_text: str,
    copyright_text: str,
    clean_room_pii_hygiene: bool,
    expect_copyright_movies: bool,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_diffset_customkey_autoslow_and_apsc_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
        evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness,
        render_phase261_markdown,
        verify_phase261_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        reset_action=reset_action,
        diff_set_shutter_speed_checked=diff_set_shutter_checked,
        diff_set_transition=diff_set_transition,
        expect_custom_wb_copied_to_movie_on_common_to_separate=expect_cwb_movie_copy,
        movie_shutter_mode=movie_shutter_mode,
        expect_common_shutter_merges_movie_shutter_angle=expect_angle_merge,
        rear_dial_assignment=rear_dial_assignment,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_camset_custom_key_access_mode=slot1_custom_key_access,
        remain_shoot_display=remain_shoot_display,
        expect_remain_shoot_displays_movie_card_time=expect_remain_movie_time,
        expect_builtin_evf_or_finder_monitor_switch=expect_builtin_evf,
        auto_slow_shutter=auto_slow_shutter,
        exposure_ctrl_type=exposure_ctrl_type,
        exposure_mode=exposure_mode,
        flexible_shutter_mode=flexible_shutter_mode,
        iso_mode=iso_mode,
        log_shooting_mode=log_shooting_mode,
        sq_mode_enabled=sq_mode_enabled,
        expect_auto_slow_shutter_active=expect_auto_slow_active,
        expect_auto_slow_shutter_with_shutter_angle=expect_auto_slow_angle_overlap,
        hdmi_time_code_output=hdmi_time_code_output,
        hdmi_rec_control=hdmi_rec_control,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        mi_shoe_4ch_audio_active=mi_shoe_4ch_audio_active,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        breathing_comp=breathing_comp,
        breathing_comp_compliant_lens=breathing_comp_compliant_lens,
        hdmi_raw_output=hdmi_raw_output,
        sq_240p_or_200p_active=sq_240p_or_200p_active,
        expect_breathing_comp_in_still_image=expect_breathing_still,
        apsc_s35_shooting=apsc_s35_shooting,
        movie_file_format=movie_file_format,
        expect_apsc_s35_active_in_4k_or_raw=expect_apsc_in_4k_or_raw,
        face_eye_prior_in_af=face_eye_prior_in_af,
        face_eye_subject=face_eye_subject,
        right_left_eye_select=right_left_eye_select,
        face_eye_frame_disp=face_eye_frame_disp,
        expect_dedicated_ai_subject_recog_menu=expect_ai_subject_recog_menu,
        hdmi_info_display=hdmi_info_display,
        expect_eye_frame_baked_on_clean_hdmi_or_raw=expect_eye_frame_clean_hdmi,
        airplane_mode=airplane_mode,
        slot1_bodydata_flash_requested=slot1_bodydata_flash_requested,
        release_wo_card=release_wo_card,
        release_wo_lens=release_wo_lens,
        card_inserted_for_movie_rec=card_inserted_for_movie_rec,
        movie_internal_rec_requested=movie_internal_rec_requested,
        expect_movie_internal_rec_without_card=expect_movie_rec_without_card,
        production_shoot_mode=production_shoot_mode,
        body_only_or_pl_adapter_bench=body_only_or_pl_adapter_bench,
        audio_rec_level=audio_rec_level,
        disp_screen_disp_audio_meter_enabled=disp_audio_meter_enabled,
        expect_standalone_v1_audio_level_display_menu=expect_v1_audio_level_menu,
        write_copyright_info=write_copyright_info,
        photographer_text=photographer_text,
        copyright_text=copyright_text,
        clean_room_pii_hygiene_enforced=clean_room_pii_hygiene,
        expect_copyright_exif_written_to_movies=expect_copyright_movies,
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
        markdown_out.write_text(render_phase261_markdown(rep), encoding="utf-8")
    v_res = verify_phase261_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED,
    )
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"e_nd_uart={rep.e_nd_uart_bytes_transmitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_file_settings_gamma_assist_focus_mag_and_videolight(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    reset_action: str,
    movie_file_number: str,
    movie_file_name_format: str,
    camera_id: str,
    reel_number: int,
    camera_position: str,
    title_name: str,
    custom_movie_folder_requested: bool,
    still_file_number: str,
    still_file_prefix: str,
    still_folder_name: str,
    slot1_contains_tier0_dump: bool,
    still_forced_file_number_reset_slot: Optional[int],
    still_create_new_folder_slot: Optional[int],
    auto_review: str,
    tc_format: str,
    rec_frame_rate_fps: float,
    video_system: str,
    tc_run: str,
    tc_make: str,
    tcub_disp_setting: str,
    log_shooting_mode: str,
    gamma_display_assist: str,
    gamma_disp_assist_type: str,
    display_lut: str,
    select_lut: str,
    auto_magnifier_in_mf: str,
    focus_magnif_time: str,
    initial_focus_mag_still: str,
    initial_focus_mag_movie: str,
    af_in_focus_mag: str,
    hdmi_raw_output: bool,
    focus_magnifier_active: bool,
    peaking_display: str,
    peaking_level: str,
    peaking_color: str,
    af_illuminator: str,
    shoot_mode: str,
    focus_mode: str,
    creators_app_location_linkage: str,
    airplane_mode: str,
    bluetooth_function: str,
    video_light_mode: str,
    mi_shoe_5v_current_ma: int,
    hdmi_resolution: str,
    rec_media_dur_hdmi_output: str,
    power_save_start_time: str,
    auto_power_off_temp: str,
    power_source: str,
    air_gapped_battery_bench: bool,
    power_save_deactivation_conditions: List[str],
    headless_monitor_power_linkage_mode: str,
    selected_lang: str,
    volume_settings: int,
    xlr_h1_attached: bool,
    four_ch_audio_monitoring: str,
    delete_confirm: str,
    delete_pressing_twice: str,
    slot1_delete_requested: bool,
    slot1_format_requested: bool,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier import (
        P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED,
        evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness,
        render_phase275_markdown,
        verify_phase275_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        reset_action=reset_action,
        movie_file_number=movie_file_number,
        movie_file_name_format=movie_file_name_format,
        camera_id=camera_id,
        reel_number=reel_number,
        camera_position=camera_position,
        title_name=title_name,
        custom_movie_folder_requested=custom_movie_folder_requested,
        still_file_number=still_file_number,
        still_file_prefix=still_file_prefix,
        still_folder_name=still_folder_name,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        still_forced_file_number_reset_slot=still_forced_file_number_reset_slot,
        still_create_new_folder_slot=still_create_new_folder_slot,
        auto_review=auto_review,
        tc_format=tc_format,
        rec_frame_rate_fps=rec_frame_rate_fps,
        video_system=video_system,
        tc_run=tc_run,
        tc_make=tc_make,
        tcub_disp_setting=tcub_disp_setting,
        log_shooting_mode=log_shooting_mode,
        gamma_display_assist=gamma_display_assist,
        gamma_disp_assist_type=gamma_disp_assist_type,
        display_lut=display_lut,
        select_lut=select_lut,
        auto_magnifier_in_mf=auto_magnifier_in_mf,
        focus_magnif_time=focus_magnif_time,
        initial_focus_mag_still=initial_focus_mag_still,
        initial_focus_mag_movie=initial_focus_mag_movie,
        af_in_focus_mag=af_in_focus_mag,
        hdmi_raw_output=hdmi_raw_output,
        focus_magnifier_active=focus_magnifier_active,
        peaking_display=peaking_display,
        peaking_level=peaking_level,
        peaking_color=peaking_color,
        af_illuminator=af_illuminator,
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        creators_app_location_linkage=creators_app_location_linkage,
        airplane_mode=airplane_mode,
        bluetooth_function=bluetooth_function,
        video_light_mode=video_light_mode,
        mi_shoe_5v_current_ma=mi_shoe_5v_current_ma,
        hdmi_resolution=hdmi_resolution,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        power_save_start_time=power_save_start_time,
        auto_power_off_temp=auto_power_off_temp,
        power_source=power_source,
        air_gapped_battery_bench=air_gapped_battery_bench,
        power_save_deactivation_conditions=tuple(power_save_deactivation_conditions),
        headless_monitor_power_linkage_mode=headless_monitor_power_linkage_mode,
        selected_lang=selected_lang,
        volume_settings=volume_settings,
        xlr_h1_attached=xlr_h1_attached,
        four_ch_audio_monitoring=four_ch_audio_monitoring,
        delete_confirm=delete_confirm,
        delete_pressing_twice=delete_pressing_twice,
        slot1_delete_requested=slot1_delete_requested,
        slot1_format_requested=slot1_format_requested,
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
        markdown_out.write_text(render_phase275_markdown(rep), encoding="utf-8")
    v_res = verify_phase275_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED,
    )
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_usb_mode_hdmi_info_protect_and_network_reset(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    reset_action: str,
    usb_connection_mode: str,
    expect_usb_streaming_uvc: bool,
    usb_streaming_exposed_in_fx3_ui: bool,
    dormant_uvc_kmod_insmodded: bool,
    air_gapped_bench: bool,
    usb_data_lines_physically_isolated: bool,
    host_usb_data_enumeration_active: bool,
    usb_lun_setting: str,
    usb_power_supply: str,
    power_source: str,
    usb_power_terminal: str,
    np_fz100_battery_inserted: bool,
    hdmi_info_display: str,
    require_clean_hdmi_feed: bool,
    require_unblanked_lcd: bool,
    allow_lcd_blanking_and_osd: bool,
    expect_touch_focus_active_when_hdmi_info_on: bool,
    expect_full_raster_clean_feed_when_hdmi_info_on: bool,
    rec_media_dur_hdmi_output: str,
    hdmi_raw_output: bool,
    shoot_mode: str,
    log_shooting_mode: str,
    picture_profile: str,
    hdmi_output_resolution: str,
    expect_4k_hdmi_during_internal_log_or_pplut: bool,
    expect_hdmi_info_on_during_raw_or_hdmi_only: bool,
    expect_sq_allows_hdmi_only_or_raw: bool,
    protect_scope_selected: str,
    protected_items_block_delete: bool,
    expect_copy_preserves_protect: bool,
    expect_movie_key_mark_without_menu: bool,
    slot1_contains_tier0_dump: bool,
    slot1_wp_locked: bool,
    slot1_format_hard_locked: bool,
    slot1_vault_write_firewall_enforced: bool,
    slot1_format_mode: str,
    slot1_delete_requested: bool,
    expect_protect_blocks_format: bool,
    expect_format_preserves_m1_m4_camset: bool,
    reset_network_set_executed: bool,
    auto_reboot_triggered_on_network_reset: bool,
    post_reboot_airplane_mode: str,
    require_post_reboot_airplane_on: bool,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier import (
        P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED,
        evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness,
        render_phase279_markdown,
        verify_phase279_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        reset_action=reset_action,
        usb_connection_mode=usb_connection_mode,
        expect_usb_streaming_uvc=expect_usb_streaming_uvc,
        usb_streaming_exposed_in_fx3_ui=usb_streaming_exposed_in_fx3_ui,
        dormant_uvc_kmod_insmodded=dormant_uvc_kmod_insmodded,
        air_gapped_bench=air_gapped_bench,
        usb_data_lines_physically_isolated=usb_data_lines_physically_isolated,
        host_usb_data_enumeration_active=host_usb_data_enumeration_active,
        usb_lun_setting=usb_lun_setting,
        usb_power_supply=usb_power_supply,
        power_source=power_source,
        usb_power_terminal=usb_power_terminal,
        np_fz100_battery_inserted=np_fz100_battery_inserted,
        hdmi_info_display=hdmi_info_display,
        require_clean_hdmi_feed=require_clean_hdmi_feed,
        require_unblanked_lcd=require_unblanked_lcd,
        allow_lcd_blanking_and_osd=allow_lcd_blanking_and_osd,
        expect_touch_focus_active_when_hdmi_info_on=expect_touch_focus_active_when_hdmi_info_on,
        expect_full_raster_clean_feed_when_hdmi_info_on=expect_full_raster_clean_feed_when_hdmi_info_on,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        hdmi_raw_output=hdmi_raw_output,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        hdmi_output_resolution=hdmi_output_resolution,
        expect_4k_hdmi_during_internal_log_or_pplut=expect_4k_hdmi_during_internal_log_or_pplut,
        expect_hdmi_info_on_during_raw_or_hdmi_only=expect_hdmi_info_on_during_raw_or_hdmi_only,
        expect_sq_allows_hdmi_only_or_raw=expect_sq_allows_hdmi_only_or_raw,
        protect_scope_selected=protect_scope_selected,
        protected_items_block_delete=protected_items_block_delete,
        expect_copy_preserves_protect=expect_copy_preserves_protect,
        expect_movie_key_mark_without_menu=expect_movie_key_mark_without_menu,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_format_hard_locked=slot1_format_hard_locked,
        slot1_vault_write_firewall_enforced=slot1_vault_write_firewall_enforced,
        slot1_format_mode=slot1_format_mode,
        slot1_delete_requested=slot1_delete_requested,
        expect_protect_blocks_format=expect_protect_blocks_format,
        expect_format_preserves_m1_m4_camset=expect_format_preserves_m1_m4_camset,
        reset_network_set_executed=reset_network_set_executed,
        auto_reboot_triggered_on_network_reset=auto_reboot_triggered_on_network_reset,
        post_reboot_airplane_mode=post_reboot_airplane_mode,
        require_post_reboot_airplane_on=require_post_reboot_airplane_on,
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
        markdown_out.write_text(render_phase279_markdown(rep), encoding="utf-8")
    v_res = verify_phase279_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED,
    )
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_pp_scinetone_wb_metering_and_shutter_type(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    reset_action: str,
    different_set_pp_checked: bool,
    shoot_mode: str,
    log_shooting_mode: str,
    picture_profile: str,
    movie_picture_profile: Optional[str],
    still_picture_profile: Optional[str],
    creative_look: str,
    dro_mode: str,
    hlg_still_image: str,
    movie_gamma_display_assist: str,
    internal_recording_active: bool,
    hdmi_output_resolution: str,
    expect_creative_look_or_dro_active_with_pp_or_log: bool,
    expect_pplut_in_still: bool,
    pp1_11_custom_params_modified: bool,
    pp_individual_reset_executed: bool,
    claimed_pp1_11_internal_params_wiped: bool,
    claimed_diff_set_checkmarks_wiped: bool,
    claimed_pp_active_selector_remains_non_pp11_after_camera_reset: bool,
    wb_mode: str,
    wb_kelvin_k: int,
    wb_ab_shift: int,
    wb_gm_shift: int,
    priority_set_in_awb: str,
    shutter_awb_lock: str,
    shockless_wb: str,
    custom_wb_setup_requested: bool,
    custom_wb_survives_camera_reset: bool,
    custom_wb_excluded_from_camset: bool,
    shutter_awb_lock_survives_camera_reset: bool,
    claimed_custom_wb_saved_in_camset: bool,
    claimed_custom_wb_wiped_by_camera_reset: bool,
    metering_mode: str,
    desqueeze_display: str,
    face_priority_in_multi_metering: str,
    spot_metering_point: str,
    ael_with_shutter: str,
    ael_with_shutter_survives_camera_reset: bool,
    cine_ei_base_iso: int,
    expect_metering_changes_cine_ei_iso: bool,
    raw_file_type: str,
    lossless_comp_exposed_in_fx3_ui: bool,
    expect_lossless_comp_raw: bool,
    jh_file_type: str,
    still_file_format: str,
    exposure_mode: str,
    dro_bracket_active: bool,
    color_space: str,
    still_file_prefix: str,
    expected_dcf_sample_filename: str,
    shutter_type: str,
    shutter_type_auto_exposed_in_fx3_ui: bool,
    expect_shutter_type_auto: bool,
    silent_mode: str,
    audio_signals: str,
    e_front_curtain_shutter: str,
    e_front_curtain_survives_camera_reset: bool,
    flash_sync_denominator: int,
    flash_enabled: bool,
    long_exposure_nr: str,
    bulb_enabled: bool,
    anti_flicker_shoot: str,
    high_iso_nr: str,
    expect_high_iso_nr_applies_to_raw: bool,
    drive_mode: str,
    cont_fps: int,
    aperture_f_number: float,
    expect_af_tracks_all_frames_above_f11: bool,
    expect_10fps_with_uncompressed_or_flash: bool,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_pp_scinetone_wb_metering_and_shutter_type_verifier import (
        P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED,
        evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness,
        render_phase284_markdown,
        verify_phase284_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        reset_action=reset_action,
        different_set_pp_checked=different_set_pp_checked,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        movie_picture_profile=movie_picture_profile,
        still_picture_profile=still_picture_profile,
        creative_look=creative_look,
        dro_mode=dro_mode,
        hlg_still_image=hlg_still_image,
        movie_gamma_display_assist=movie_gamma_display_assist,
        internal_recording_active=internal_recording_active,
        hdmi_output_resolution=hdmi_output_resolution,
        expect_creative_look_or_dro_active_with_pp_or_log=expect_creative_look_or_dro_active_with_pp_or_log,
        expect_pplut_in_still=expect_pplut_in_still,
        pp1_11_custom_params_modified=pp1_11_custom_params_modified,
        pp_individual_reset_executed=pp_individual_reset_executed,
        claimed_pp1_11_internal_params_wiped=claimed_pp1_11_internal_params_wiped,
        claimed_diff_set_checkmarks_wiped=claimed_diff_set_checkmarks_wiped,
        claimed_pp_active_selector_remains_non_pp11_after_camera_reset=claimed_pp_active_selector_remains_non_pp11_after_camera_reset,
        wb_mode=wb_mode,
        wb_kelvin_k=wb_kelvin_k,
        wb_ab_shift=wb_ab_shift,
        wb_gm_shift=wb_gm_shift,
        priority_set_in_awb=priority_set_in_awb,
        shutter_awb_lock=shutter_awb_lock,
        shockless_wb=shockless_wb,
        custom_wb_setup_requested=custom_wb_setup_requested,
        custom_wb_survives_camera_reset=custom_wb_survives_camera_reset,
        custom_wb_excluded_from_camset=custom_wb_excluded_from_camset,
        shutter_awb_lock_survives_camera_reset=shutter_awb_lock_survives_camera_reset,
        claimed_custom_wb_saved_in_camset=claimed_custom_wb_saved_in_camset,
        claimed_custom_wb_wiped_by_camera_reset=claimed_custom_wb_wiped_by_camera_reset,
        metering_mode=metering_mode,
        desqueeze_display=desqueeze_display,
        face_priority_in_multi_metering=face_priority_in_multi_metering,
        spot_metering_point=spot_metering_point,
        ael_with_shutter=ael_with_shutter,
        ael_with_shutter_survives_camera_reset=ael_with_shutter_survives_camera_reset,
        cine_ei_base_iso=cine_ei_base_iso,
        expect_metering_changes_cine_ei_iso=expect_metering_changes_cine_ei_iso,
        raw_file_type=raw_file_type,
        lossless_comp_exposed_in_fx3_ui=lossless_comp_exposed_in_fx3_ui,
        expect_lossless_comp_raw=expect_lossless_comp_raw,
        jh_file_type=jh_file_type,
        still_file_format=still_file_format,
        exposure_mode=exposure_mode,
        dro_bracket_active=dro_bracket_active,
        color_space=color_space,
        still_file_prefix=still_file_prefix,
        expected_dcf_sample_filename=expected_dcf_sample_filename,
        shutter_type=shutter_type,
        shutter_type_auto_exposed_in_fx3_ui=shutter_type_auto_exposed_in_fx3_ui,
        expect_shutter_type_auto=expect_shutter_type_auto,
        silent_mode=silent_mode,
        audio_signals=audio_signals,
        e_front_curtain_shutter=e_front_curtain_shutter,
        e_front_curtain_survives_camera_reset=e_front_curtain_survives_camera_reset,
        flash_sync_denominator=flash_sync_denominator,
        flash_enabled=flash_enabled,
        long_exposure_nr=long_exposure_nr,
        bulb_enabled=bulb_enabled,
        anti_flicker_shoot=anti_flicker_shoot,
        high_iso_nr=high_iso_nr,
        expect_high_iso_nr_applies_to_raw=expect_high_iso_nr_applies_to_raw,
        drive_mode=drive_mode,
        cont_fps=cont_fps,
        aperture_f_number=aperture_f_number,
        expect_af_tracks_all_frames_above_f11=expect_af_tracks_all_frames_above_f11,
        expect_10fps_with_uncompressed_or_flash=expect_10fps_with_uncompressed_or_flash,
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
        markdown_out.write_text(render_phase284_markdown(rep), encoding="utf-8")
    v_res = verify_phase284_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED,
    )
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_focus_area_zoom_dci4k_and_sensor_cleaning(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    summary_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    reset_action: str,
    shoot_mode: str,
    focus_area: str,
    expect_tracking_focus_area_in_movie: bool,
    focus_area_limit_selected_count: int,
    switch_vh_af_area: str,
    expect_switch_vh_in_movie: bool,
    focus_area_color: str,
    circ_of_focus_point: str,
    af_area_registration_label: str,
    xlr_h1_zoom_lever_present: bool,
    xlr_h1_rec_button_present: bool,
    xlr_h1_zoom_hold_switch_present: bool,
    fx6_smart_handle_zero_to_99_is_speed_scale: bool,
    zoom_range: str,
    zoom_lever_stby_speed: int,
    zoom_lever_rec_speed: int,
    custom_key_zoom_stby_speed: int,
    custom_key_zoom_rec_speed: int,
    remote_zoom_speed_type: str,
    remote_zoom_fixed_stby_speed: int,
    remote_zoom_fixed_rec_speed: int,
    iso_range_limit_min: int,
    iso_range_limit_max: int,
    iso_auto_min: int,
    iso_auto_max: int,
    exposure_mode: str,
    iso_mode: str,
    iso_auto_min_ss: str,
    iso_auto_min_ss_active: bool,
    expect_iso_auto_min_ss_in_movie_or_manual_iso: bool,
    log_shooting_mode: str,
    cine_ei_base_iso: int,
    expect_iso_variable_in_cine_ei: bool,
    shutter_type: str,
    silent_mode: str,
    flash_mode: str,
    flash_firing_enabled: bool,
    flash_comp_ev: float,
    exp_comp_set: str,
    video_light_mode: str,
    mi_shoe_5v_current_ma: int,
    movie_file_format: str,
    movie_resolution_wh: str,
    rec_frame_rate: str,
    stage_b_volatile_tmp_overlay_active: bool,
    ack_24p_reboot_wipes_tmp_overlay: bool,
    expect_24p_no_reboot: bool,
    hdmi_raw_output: bool,
    sq_dci4k_fps: int,
    bitrate_mbps: int,
    media_speed_grade: str,
    still_aspect_ratio: str,
    apsc_s35_on: bool,
    still_jpeg_heif_size: str,
    hlg_still_image: str,
    camset_card_path: str,
    memory_recall_media_slot: str,
    fx3_uses_private_sony_pro_camera: bool,
    photo_capture_requested: bool,
    photo_capture_slot: int,
    slot1_contains_tier0_dump: bool,
    enlarge_initial_mag: str,
    enlarge_initial_position: str,
    sensor_cleaning_requested: bool,
    battery_soc_pct: float,
    mandatory_power_off_after_cleaning: bool,
    unattended_tier0_dump_active: bool,
    fx6_sensor_cleaning_supported_claimed: bool,
    fx3_has_built_in_end_filter: bool,
    exposure_comp_ev: float,
    exposure_step: str,
    legacy_reset_ev_comp_claimed: bool,
    focus_mode: str,
    priority_set_in_af: str,
    af_illuminator: str,
    view_mode: str,
    image_index_mode: str,
    display_as_group: str,
    display_rotation: str,
    playback_media_slot: int,
    playback_rotate_requested: bool,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier import (
        P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED,
        evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness,
        render_phase291_markdown,
        verify_phase291_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        focus_area=focus_area,
        expect_tracking_focus_area_in_movie=expect_tracking_focus_area_in_movie,
        focus_area_limit_selected_count=focus_area_limit_selected_count,
        switch_vh_af_area=switch_vh_af_area,
        expect_switch_vh_in_movie=expect_switch_vh_in_movie,
        focus_area_color=focus_area_color,
        circ_of_focus_point=circ_of_focus_point,
        af_area_registration_label=af_area_registration_label,
        xlr_h1_zoom_lever_present=xlr_h1_zoom_lever_present,
        xlr_h1_rec_button_present=xlr_h1_rec_button_present,
        xlr_h1_zoom_hold_switch_present=xlr_h1_zoom_hold_switch_present,
        fx6_smart_handle_zero_to_99_is_speed_scale=fx6_smart_handle_zero_to_99_is_speed_scale,
        zoom_range=zoom_range,
        zoom_lever_stby_speed=zoom_lever_stby_speed,
        zoom_lever_rec_speed=zoom_lever_rec_speed,
        custom_key_zoom_stby_speed=custom_key_zoom_stby_speed,
        custom_key_zoom_rec_speed=custom_key_zoom_rec_speed,
        remote_zoom_speed_type=remote_zoom_speed_type,
        remote_zoom_fixed_stby_speed=remote_zoom_fixed_stby_speed,
        remote_zoom_fixed_rec_speed=remote_zoom_fixed_rec_speed,
        iso_range_limit_min=iso_range_limit_min,
        iso_range_limit_max=iso_range_limit_max,
        iso_auto_min=iso_auto_min,
        iso_auto_max=iso_auto_max,
        exposure_mode=exposure_mode,
        iso_mode=iso_mode,
        iso_auto_min_ss=iso_auto_min_ss,
        iso_auto_min_ss_active=iso_auto_min_ss_active,
        expect_iso_auto_min_ss_in_movie_or_manual_iso=expect_iso_auto_min_ss_in_movie_or_manual_iso,
        log_shooting_mode=log_shooting_mode,
        cine_ei_base_iso=cine_ei_base_iso,
        expect_iso_variable_in_cine_ei=expect_iso_variable_in_cine_ei,
        shutter_type=shutter_type,
        silent_mode=silent_mode,
        flash_mode=flash_mode,
        flash_firing_enabled=flash_firing_enabled,
        flash_comp_ev=flash_comp_ev,
        exp_comp_set=exp_comp_set,
        video_light_mode=video_light_mode,
        mi_shoe_5v_current_ma=mi_shoe_5v_current_ma,
        movie_file_format=movie_file_format,
        movie_resolution_wh=movie_resolution_wh,
        rec_frame_rate=rec_frame_rate,
        stage_b_volatile_tmp_overlay_active=stage_b_volatile_tmp_overlay_active,
        ack_24p_reboot_wipes_tmp_overlay=ack_24p_reboot_wipes_tmp_overlay,
        expect_24p_no_reboot=expect_24p_no_reboot,
        hdmi_raw_output=hdmi_raw_output,
        sq_dci4k_fps=sq_dci4k_fps,
        bitrate_mbps=bitrate_mbps,
        media_speed_grade=media_speed_grade,
        still_aspect_ratio=still_aspect_ratio,
        apsc_s35_on=apsc_s35_on,
        still_jpeg_heif_size=still_jpeg_heif_size,
        hlg_still_image=hlg_still_image,
        camset_card_path=camset_card_path,
        memory_recall_media_slot=memory_recall_media_slot,
        fx3_uses_private_sony_pro_camera=fx3_uses_private_sony_pro_camera,
        photo_capture_requested=photo_capture_requested,
        photo_capture_slot=photo_capture_slot,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        enlarge_initial_mag=enlarge_initial_mag,
        enlarge_initial_position=enlarge_initial_position,
        sensor_cleaning_requested=sensor_cleaning_requested,
        battery_soc_pct=battery_soc_pct,
        mandatory_power_off_after_cleaning=mandatory_power_off_after_cleaning,
        unattended_tier0_dump_active=unattended_tier0_dump_active,
        fx6_sensor_cleaning_supported_claimed=fx6_sensor_cleaning_supported_claimed,
        fx3_has_built_in_end_filter=fx3_has_built_in_end_filter,
        exposure_comp_ev=exposure_comp_ev,
        exposure_step=exposure_step,
        legacy_reset_ev_comp_claimed=legacy_reset_ev_comp_claimed,
        focus_mode=focus_mode,
        priority_set_in_af=priority_set_in_af,
        af_illuminator=af_illuminator,
        view_mode=view_mode,
        image_index_mode=image_index_mode,
        display_as_group=display_as_group,
        display_rotation=display_rotation,
        playback_media_slot=playback_media_slot,
        playback_rotate_requested=playback_rotate_requested,
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
        markdown_out.write_text(render_phase291_markdown(rep), encoding="utf-8")
    v_res = verify_phase291_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED,
    )
    try:
        if json_output and not summary_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash={rep.cross_model_flash_authorized} "
                f"xlr_h1_zoom_lever={rep.xlr_h1_zoom_lever_present} "
                f"fx3_pro_camera={rep.fx3_private_sony_pro_camera_used} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_lens_comp_af_illuminator_copy_slot_and_evf_absence(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    summary_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    reset_action: str,
    shoot_mode: str,
    focus_mode: str,
    exposure_mode: str,
    shading_comp: str,
    dormant_shading_auto_low_requested: bool,
    chromatic_aberration_comp: str,
    distortion_comp: str,
    steadyshot_mode: str,
    lens_distortion_comp_locked_auto: bool,
    unchipped_manual_lens_attached: bool,
    expect_lens_comp_active_on_manual_lens: bool,
    breathing_comp: str,
    breathing_comp_compliant_lens: bool,
    hdmi_raw_output: bool,
    claimed_static_lens_comp_wiped_by_camera_reset: bool,
    fx6_lens_comp_in_scene_file_claimed: bool,
    fx3_builtin_af_illuminator_present: bool,
    fx6_builtin_af_illuminator_present: bool,
    af_illuminator: str,
    af_illuminator_firing_requested: bool,
    af_illuminator_distance_m: float,
    focus_magnifier_active: bool,
    mount_adaptor_attached: bool,
    af_transition_speed: int,
    af_subj_shift_sensitivity: int,
    af_assist: str,
    af_assist_compatible_lens: bool,
    aperture_drive_in_af: str,
    af_with_shutter: str,
    pre_af: str,
    lens_pre_af_supported: bool,
    circ_of_focus_point: str,
    expect_diagonal_focus_wrap: bool,
    focus_area_color: str,
    claimed_af_five_params_wiped_by_camera_reset: bool,
    fx6_aperture_drive_in_af_claimed: bool,
    still_folder_name_mode: str,
    select_rec_folder_enabled_claimed: bool,
    still_file_number_mode: str,
    still_file_prefix: str,
    still_folder_image_count: int,
    slot1_contains_tier0_dump: bool,
    slot1_wp_locked: bool,
    create_new_folder_requested: bool,
    create_new_folder_slot: int,
    forced_file_number_reset_requested: bool,
    forced_file_number_reset_slot: int,
    playback_media_slot: int,
    playback_rating_requested: bool,
    rating_stars: int,
    add_rating_requested: bool,
    target_image_already_rated: bool,
    digital_zoom_active: bool,
    switch_vh_af_area: str,
    body_roll_orientation: str,
    fx6_switch_vh_af_area_claimed: bool,
    focus_area_limit_selected_count: int,
    dormant_focus_area_requested: str,
    fx6_focus_area_limit_claimed: bool,
    exposure_std_adjust_metering_mode: str,
    exposure_std_adjust_ev: float,
    expect_std_adjust_changes_exif_exposure_comp: bool,
    claimed_exposure_std_adjust_wiped_by_camera_reset: bool,
    fx6_exposure_std_adjust_claimed: bool,
    bracket_selftimer: str,
    bracket_order: str,
    bracket_settings_active_in_movie_claimed: bool,
    video_system: str,
    rec_frame_rate: str,
    tc_format: str,
    user_bit_time_rec: str,
    tcub_disp_setting: str,
    fx3_builtin_bnc_tc_in_out_switch_claimed: bool,
    claimed_tcub_6items_wiped_by_camera_reset: bool,
    playback_copy_requested: bool,
    copy_battery_ok: bool,
    copy_target_media_speed_ok: bool,
    copy_dest_slot_present: bool,
    expect_copy_preserves_group_or_protect: bool,
    fx6_in_camera_copy_clip_claimed: bool,
    slide_show_requested: bool,
    slide_show_repeat: str,
    slide_show_interval_sec: int,
    slide_show_view_mode: str,
    touch_operation: str,
    touch_sensitivity: str,
    touch_func_in_shooting: str,
    swipe_up: str,
    dormant_touch_trap_requested: str,
    touch_panel_pad_present_claimed: bool,
    footer_icon_touch_enabled_claimed: bool,
    claimed_touch_4items_wiped_by_camera_reset: bool,
    fx3_builtin_evf_present: bool,
    fx3_eye_sensor_present: bool,
    fx3_select_finder_monitor_present: bool,
    fx3_graphic_display_present: bool,
    activate_dormant_evf_finder_mode: bool,
    finder_monitor_key_claimed: bool,
    graphic_display_claimed: bool,
    monitor_off_evf_trap_claimed: bool,
    for_viewfinder_disp_claimed: bool,
    fx6_detachable_evf_loupe_claimed: bool,
    claimed_disp_modes_wiped_by_camera_reset: bool,
    ael_with_shutter: str,
    ael_with_shutter_in_movie_claimed: bool,
    claimed_ael_with_shutter_wiped_by_camera_reset: bool,
    exp_comp_set: str,
    wireless_flash: str,
    external_flash_set_requested: bool,
    mi_shoe_external_flash_attached: bool,
    fx6_still_ael_or_wireless_flash_claimed: bool,
    interval_play_speed: int,
    interval_play_speed_capped_at_5_claimed: bool,
    in_camera_interval_to_video_render_claimed: bool,
    dormant_beauty_effect_requested: bool,
    dormant_trimming_requested: bool,
    playback_photo_capture_requested: bool,
    playback_rotate_requested: bool,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier import (
        P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED,
        evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness,
        render_phase302_markdown,
        verify_phase302_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    rep = evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        exposure_mode=exposure_mode,
        shading_comp=shading_comp,
        dormant_shading_auto_low_requested=dormant_shading_auto_low_requested,
        chromatic_aberration_comp=chromatic_aberration_comp,
        distortion_comp=distortion_comp,
        steadyshot_mode=steadyshot_mode,
        lens_distortion_comp_locked_auto=lens_distortion_comp_locked_auto,
        unchipped_manual_lens_attached=unchipped_manual_lens_attached,
        expect_lens_comp_active_on_manual_lens=expect_lens_comp_active_on_manual_lens,
        breathing_comp=breathing_comp,
        breathing_comp_compliant_lens=breathing_comp_compliant_lens,
        hdmi_raw_output=hdmi_raw_output,
        claimed_static_lens_comp_wiped_by_camera_reset=claimed_static_lens_comp_wiped_by_camera_reset,
        fx6_lens_comp_in_scene_file_claimed=fx6_lens_comp_in_scene_file_claimed,
        fx3_builtin_af_illuminator_present=fx3_builtin_af_illuminator_present,
        fx6_builtin_af_illuminator_present=fx6_builtin_af_illuminator_present,
        af_illuminator=af_illuminator,
        af_illuminator_firing_requested=af_illuminator_firing_requested,
        af_illuminator_distance_m=af_illuminator_distance_m,
        focus_magnifier_active=focus_magnifier_active,
        mount_adaptor_attached=mount_adaptor_attached,
        af_transition_speed=af_transition_speed,
        af_subj_shift_sensitivity=af_subj_shift_sensitivity,
        af_assist=af_assist,
        af_assist_compatible_lens=af_assist_compatible_lens,
        aperture_drive_in_af=aperture_drive_in_af,
        af_with_shutter=af_with_shutter,
        pre_af=pre_af,
        lens_pre_af_supported=lens_pre_af_supported,
        circ_of_focus_point=circ_of_focus_point,
        expect_diagonal_focus_wrap=expect_diagonal_focus_wrap,
        focus_area_color=focus_area_color,
        claimed_af_five_params_wiped_by_camera_reset=claimed_af_five_params_wiped_by_camera_reset,
        fx6_aperture_drive_in_af_claimed=fx6_aperture_drive_in_af_claimed,
        still_folder_name_mode=still_folder_name_mode,
        select_rec_folder_enabled_claimed=select_rec_folder_enabled_claimed,
        still_file_number_mode=still_file_number_mode,
        still_file_prefix=still_file_prefix,
        still_folder_image_count=still_folder_image_count,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        create_new_folder_requested=create_new_folder_requested,
        create_new_folder_slot=create_new_folder_slot,
        forced_file_number_reset_requested=forced_file_number_reset_requested,
        forced_file_number_reset_slot=forced_file_number_reset_slot,
        playback_media_slot=playback_media_slot,
        playback_rating_requested=playback_rating_requested,
        rating_stars=rating_stars,
        add_rating_requested=add_rating_requested,
        target_image_already_rated=target_image_already_rated,
        digital_zoom_active=digital_zoom_active,
        switch_vh_af_area=switch_vh_af_area,
        body_roll_orientation=body_roll_orientation,
        fx6_switch_vh_af_area_claimed=fx6_switch_vh_af_area_claimed,
        focus_area_limit_selected_count=focus_area_limit_selected_count,
        dormant_focus_area_requested=dormant_focus_area_requested,
        fx6_focus_area_limit_claimed=fx6_focus_area_limit_claimed,
        exposure_std_adjust_metering_mode=exposure_std_adjust_metering_mode,
        exposure_std_adjust_ev=exposure_std_adjust_ev,
        expect_std_adjust_changes_exif_exposure_comp=expect_std_adjust_changes_exif_exposure_comp,
        claimed_exposure_std_adjust_wiped_by_camera_reset=claimed_exposure_std_adjust_wiped_by_camera_reset,
        fx6_exposure_std_adjust_claimed=fx6_exposure_std_adjust_claimed,
        bracket_selftimer=bracket_selftimer,
        bracket_order=bracket_order,
        bracket_settings_active_in_movie_claimed=bracket_settings_active_in_movie_claimed,
        video_system=video_system,
        rec_frame_rate=rec_frame_rate,
        tc_format=tc_format,
        user_bit_time_rec=user_bit_time_rec,
        tcub_disp_setting=tcub_disp_setting,
        fx3_builtin_bnc_tc_in_out_switch_claimed=fx3_builtin_bnc_tc_in_out_switch_claimed,
        claimed_tcub_6items_wiped_by_camera_reset=claimed_tcub_6items_wiped_by_camera_reset,
        playback_copy_requested=playback_copy_requested,
        copy_battery_ok=copy_battery_ok,
        copy_target_media_speed_ok=copy_target_media_speed_ok,
        copy_dest_slot_present=copy_dest_slot_present,
        expect_copy_preserves_group_or_protect=expect_copy_preserves_group_or_protect,
        fx6_in_camera_copy_clip_claimed=fx6_in_camera_copy_clip_claimed,
        slide_show_requested=slide_show_requested,
        slide_show_repeat=slide_show_repeat,
        slide_show_interval_sec=slide_show_interval_sec,
        slide_show_view_mode=slide_show_view_mode,
        touch_operation=touch_operation,
        touch_sensitivity=touch_sensitivity,
        touch_func_in_shooting=touch_func_in_shooting,
        swipe_up=swipe_up,
        dormant_touch_trap_requested=dormant_touch_trap_requested,
        touch_panel_pad_present_claimed=touch_panel_pad_present_claimed,
        footer_icon_touch_enabled_claimed=footer_icon_touch_enabled_claimed,
        claimed_touch_4items_wiped_by_camera_reset=claimed_touch_4items_wiped_by_camera_reset,
        fx3_builtin_evf_present=fx3_builtin_evf_present,
        fx3_eye_sensor_present=fx3_eye_sensor_present,
        fx3_select_finder_monitor_present=fx3_select_finder_monitor_present,
        fx3_graphic_display_present=fx3_graphic_display_present,
        activate_dormant_evf_finder_mode=activate_dormant_evf_finder_mode,
        finder_monitor_key_claimed=finder_monitor_key_claimed,
        graphic_display_claimed=graphic_display_claimed,
        monitor_off_evf_trap_claimed=monitor_off_evf_trap_claimed,
        for_viewfinder_disp_claimed=for_viewfinder_disp_claimed,
        fx6_detachable_evf_loupe_claimed=fx6_detachable_evf_loupe_claimed,
        claimed_disp_modes_wiped_by_camera_reset=claimed_disp_modes_wiped_by_camera_reset,
        ael_with_shutter=ael_with_shutter,
        ael_with_shutter_in_movie_claimed=ael_with_shutter_in_movie_claimed,
        claimed_ael_with_shutter_wiped_by_camera_reset=claimed_ael_with_shutter_wiped_by_camera_reset,
        exp_comp_set=exp_comp_set,
        wireless_flash=wireless_flash,
        external_flash_set_requested=external_flash_set_requested,
        mi_shoe_external_flash_attached=mi_shoe_external_flash_attached,
        fx6_still_ael_or_wireless_flash_claimed=fx6_still_ael_or_wireless_flash_claimed,
        interval_play_speed=interval_play_speed,
        interval_play_speed_capped_at_5_claimed=interval_play_speed_capped_at_5_claimed,
        in_camera_interval_to_video_render_claimed=in_camera_interval_to_video_render_claimed,
        dormant_beauty_effect_requested=dormant_beauty_effect_requested,
        dormant_trimming_requested=dormant_trimming_requested,
        playback_photo_capture_requested=playback_photo_capture_requested,
        playback_rotate_requested=playback_rotate_requested,
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
        markdown_out.write_text(render_phase302_markdown(rep), encoding="utf-8")
    v_res = verify_phase302_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED,
    )
    try:
        if json_output and not summary_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash={rep.cross_model_flash_authorized} "
                f"builtin_evf={rep.builtin_evf_present} "
                f"fx6_af_illum={rep.fx6_builtin_af_illuminator_present} "
                f"slot1_mutated={rep.slot1_tier0_vault_mutated} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_dial_customize_lut_embed_steadyshot_and_streaming(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    summary_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    sony_help_guide_id: str,
    reset_action: str,
    shoot_mode: str,
    exposed_dial_customize_items: Optional[str],
    dormant_dial_setup_or_wheel_lock_requested: bool,
    av_tv_rotate: str,
    function_ring_lens: str,
    lock_operation_parts: str,
    claimed_dial_customize_wiped_by_camera_reset: bool,
    fx6_dial_topology_claimed: bool,
    exposed_physical_dials: Optional[str],
    fx3_four_dial_rear_lr_present: bool,
    dormant_rear_dial_lr_requested: bool,
    my_dial_slot: int,
    my_dial_active_recalled: bool,
    expect_lock_blocks_recalled_my_dial: bool,
    fn_menu_still_slots: int,
    fn_menu_movie_slots: int,
    fn_menu_all_not_set_claimed: bool,
    exposed_live_view_subitems: Optional[str],
    live_view_display: str,
    exposure_effect: str,
    frame_rate_low_limit: str,
    bright_monitoring_active: bool,
    expect_setting_effect_on_during_bright_monitoring: bool,
    claimed_live_view_two_items_wiped_by_camera_reset: bool,
    grid_line_display: str,
    grid_line_type: str,
    hdmi_info_display: str,
    hdmi_raw_output: bool,
    rec_media_dur_hdmi_output: str,
    expect_grid_line_on_clean_hdmi: bool,
    dormant_fx6_custom_png_grid_requested: bool,
    user_lut_slot: int,
    user_lut_import_requested: bool,
    user_lut_source_media_type: str,
    user_lut_source_dir: str,
    user_lut_filename: str,
    user_lut_cube_size: int,
    user_lut_config_writeback_to_slot1: bool,
    log_shooting_mode: str,
    embed_lut_file: str,
    embed_lut_media_type: str,
    claimed_embed_lut_under_color_tone: bool,
    expect_embed_lut_bakes_pixels: bool,
    picture_profile: str,
    expect_pplut_preserves_unbaked_slog3: bool,
    claimed_pplut_survives_reset: bool,
    slot1_contains_tier0_dump: bool,
    slot1_wp_locked: bool,
    embed_lut_or_pplut_rec_requested: bool,
    rec_target_slot: int,
    steadyshot_mode: str,
    dormant_dynamic_active_requested: bool,
    steadyshot_adjust: str,
    steadyshot_focal_mm: int,
    exposed_focal_length_table: Optional[str],
    rec_fps: float,
    sq_mode_enabled: bool,
    sq_fps: float,
    desqueeze_display: str,
    distortion_comp: str,
    fx3_builtin_5axis_ibis_present: bool,
    fx6_builtin_ibis_claimed: bool,
    dormant_movie_selftimer_requested: bool,
    still_drive_mode: str,
    front_led8_selftimer_blink_expected: bool,
    silent_mode: str,
    audio_signals: str,
    dormant_audio_signal_volume_requested: bool,
    claimed_audio_signals_wiped_by_camera_reset: bool,
    fx6_picture_cache_or_interval_rec_in_fx3_claimed: bool,
    zebra_display: str,
    zebra_preset: str,
    zebra_custom_slot: str,
    zebra_custom_type: str,
    zebra_level_ire: int,
    zebra_range_plus_minus: int,
    peaking_display: str,
    peaking_level: str,
    peaking_color: str,
    expect_zebra_or_peaking_on_clean_hdmi: bool,
    fx6_zebra_both_mode_claimed: bool,
    claimed_zebra_peaking_wiped_by_camera_reset: bool,
    streaming_protocol: str,
    streaming_resolution: str,
    streaming_fps: float,
    movie_rec_during_streaming: str,
    internal_rec_resolution_class: str,
    internal_rec_fps: float,
    movie_rec_during_streaming_slot: int,
    fx6_builtin_rtmp_srt_claimed: bool,
    ftp_transfer_func: str,
    ftp_active_mode_requested: bool,
    ftp_slot1_write_requested: bool,
    claimed_network_wiped_by_camera_reset: bool,
    claimed_network_survives_reset_network_set: bool,
    airplane_mode: str,
    network_transport: str,
    wireless_streaming_requested: bool,
    wireless_ftp_requested: bool,
    wireless_rf_packets_emitted: int,
    rf_nvs_p12_p13_writes_requested: bool,
    simulated_passive_tx_bytes: int,
    simulated_h0_h3_drifted_surfaces: int,
    claim_hardware_live_attach_authorized: bool,
    claim_persistent_emmc_writes_authorized: bool,
    claim_cross_model_flash_authorized: bool,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_dial_customize_lut_embed_steadyshot_and_streaming_verifier import (
        P307_DIAL_CUSTOMIZE_FIVE_ITEMS,
        P307_FX3_THREE_PHYSICAL_DIALS,
        P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED,
        P307_LIVE_VIEW_DISPLAY_SUBITEMS,
        P307_STEADYSHOT_47_FOCAL_LENGTHS_MM,
        evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness,
        render_phase307_markdown,
        verify_phase307_report,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    dial_items = (
        tuple(x.strip() for x in exposed_dial_customize_items.split(",") if x.strip())
        if exposed_dial_customize_items is not None
        else P307_DIAL_CUSTOMIZE_FIVE_ITEMS
    )
    physical_dials = (
        tuple(x.strip() for x in exposed_physical_dials.split(",") if x.strip())
        if exposed_physical_dials is not None
        else P307_FX3_THREE_PHYSICAL_DIALS
    )
    liveview_items = (
        tuple(x.strip() for x in exposed_live_view_subitems.split(",") if x.strip())
        if exposed_live_view_subitems is not None
        else P307_LIVE_VIEW_DISPLAY_SUBITEMS
    )
    focal_table = (
        tuple(int(x.strip()) for x in exposed_focal_length_table.split(",") if x.strip())
        if exposed_focal_length_table is not None
        else P307_STEADYSHOT_47_FOCAL_LENGTHS_MM
    )

    rep = evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        exposed_dial_customize_items=dial_items,
        dormant_dial_setup_or_wheel_lock_requested=dormant_dial_setup_or_wheel_lock_requested,
        av_tv_rotate=av_tv_rotate,
        function_ring_lens=function_ring_lens,
        lock_operation_parts=lock_operation_parts,
        claimed_dial_customize_wiped_by_camera_reset=claimed_dial_customize_wiped_by_camera_reset,
        fx6_dial_topology_claimed=fx6_dial_topology_claimed,
        exposed_physical_dials=physical_dials,
        fx3_four_dial_rear_lr_present=fx3_four_dial_rear_lr_present,
        dormant_rear_dial_lr_requested=dormant_rear_dial_lr_requested,
        my_dial_slot=my_dial_slot,
        my_dial_active_recalled=my_dial_active_recalled,
        expect_lock_blocks_recalled_my_dial=expect_lock_blocks_recalled_my_dial,
        fn_menu_still_slots=fn_menu_still_slots,
        fn_menu_movie_slots=fn_menu_movie_slots,
        fn_menu_all_not_set_claimed=fn_menu_all_not_set_claimed,
        exposed_live_view_subitems=liveview_items,
        live_view_display=live_view_display,
        exposure_effect=exposure_effect,
        frame_rate_low_limit=frame_rate_low_limit,
        bright_monitoring_active=bright_monitoring_active,
        expect_setting_effect_on_during_bright_monitoring=expect_setting_effect_on_during_bright_monitoring,
        claimed_live_view_two_items_wiped_by_camera_reset=claimed_live_view_two_items_wiped_by_camera_reset,
        grid_line_display=grid_line_display,
        grid_line_type=grid_line_type,
        hdmi_info_display=hdmi_info_display,
        hdmi_raw_output=hdmi_raw_output,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        expect_grid_line_on_clean_hdmi=expect_grid_line_on_clean_hdmi,
        dormant_fx6_custom_png_grid_requested=dormant_fx6_custom_png_grid_requested,
        user_lut_slot=user_lut_slot,
        user_lut_import_requested=user_lut_import_requested,
        user_lut_source_media_type=user_lut_source_media_type,
        user_lut_source_dir=user_lut_source_dir,
        user_lut_filename=user_lut_filename,
        user_lut_cube_size=user_lut_cube_size,
        user_lut_config_writeback_to_slot1=user_lut_config_writeback_to_slot1,
        log_shooting_mode=log_shooting_mode,
        embed_lut_file=embed_lut_file,
        embed_lut_media_type=embed_lut_media_type,
        claimed_embed_lut_under_color_tone=claimed_embed_lut_under_color_tone,
        expect_embed_lut_bakes_pixels=expect_embed_lut_bakes_pixels,
        picture_profile=picture_profile,
        expect_pplut_preserves_unbaked_slog3=expect_pplut_preserves_unbaked_slog3,
        claimed_pplut_survives_reset=claimed_pplut_survives_reset,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        embed_lut_or_pplut_rec_requested=embed_lut_or_pplut_rec_requested,
        rec_target_slot=rec_target_slot,
        steadyshot_mode=steadyshot_mode,
        dormant_dynamic_active_requested=dormant_dynamic_active_requested,
        steadyshot_adjust=steadyshot_adjust,
        steadyshot_focal_mm=steadyshot_focal_mm,
        exposed_focal_length_table=focal_table,
        rec_fps=rec_fps,
        sq_mode_enabled=sq_mode_enabled,
        sq_fps=sq_fps,
        desqueeze_display=desqueeze_display,
        distortion_comp=distortion_comp,
        fx3_builtin_5axis_ibis_present=fx3_builtin_5axis_ibis_present,
        fx6_builtin_ibis_claimed=fx6_builtin_ibis_claimed,
        dormant_movie_selftimer_requested=dormant_movie_selftimer_requested,
        still_drive_mode=still_drive_mode,
        front_led8_selftimer_blink_expected=front_led8_selftimer_blink_expected,
        silent_mode=silent_mode,
        audio_signals=audio_signals,
        dormant_audio_signal_volume_requested=dormant_audio_signal_volume_requested,
        claimed_audio_signals_wiped_by_camera_reset=claimed_audio_signals_wiped_by_camera_reset,
        fx6_picture_cache_or_interval_rec_in_fx3_claimed=fx6_picture_cache_or_interval_rec_in_fx3_claimed,
        zebra_display=zebra_display,
        zebra_preset=zebra_preset,
        zebra_custom_slot=zebra_custom_slot,
        zebra_custom_type=zebra_custom_type,
        zebra_level_ire=zebra_level_ire,
        zebra_range_plus_minus=zebra_range_plus_minus,
        peaking_display=peaking_display,
        peaking_level=peaking_level,
        peaking_color=peaking_color,
        expect_zebra_or_peaking_on_clean_hdmi=expect_zebra_or_peaking_on_clean_hdmi,
        fx6_zebra_both_mode_claimed=fx6_zebra_both_mode_claimed,
        claimed_zebra_peaking_wiped_by_camera_reset=claimed_zebra_peaking_wiped_by_camera_reset,
        streaming_protocol=streaming_protocol,
        streaming_resolution=streaming_resolution,
        streaming_fps=streaming_fps,
        movie_rec_during_streaming=movie_rec_during_streaming,
        internal_rec_resolution_class=internal_rec_resolution_class,
        internal_rec_fps=internal_rec_fps,
        movie_rec_during_streaming_slot=movie_rec_during_streaming_slot,
        fx6_builtin_rtmp_srt_claimed=fx6_builtin_rtmp_srt_claimed,
        ftp_transfer_func=ftp_transfer_func,
        ftp_active_mode_requested=ftp_active_mode_requested,
        ftp_slot1_write_requested=ftp_slot1_write_requested,
        claimed_network_wiped_by_camera_reset=claimed_network_wiped_by_camera_reset,
        claimed_network_survives_reset_network_set=claimed_network_survives_reset_network_set,
        airplane_mode=airplane_mode,
        network_transport=network_transport,
        wireless_streaming_requested=wireless_streaming_requested,
        wireless_ftp_requested=wireless_ftp_requested,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        rf_nvs_p12_p13_writes_requested=rf_nvs_p12_p13_writes_requested,
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=claim_cross_model_flash_authorized,
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
        markdown_out.write_text(render_phase307_markdown(rep), encoding="utf-8")
    v_res = verify_phase307_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED,
    )
    try:
        if json_output and not summary_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash={rep.cross_model_flash_authorized} "
                f"rear_lr={rep.fx3_four_dial_rear_lr_present} "
                f"movie_selftimer={rep.fx3_movie_selftimer_present} "
                f"fx6_ibis={rep.fx6_builtin_ibis_present} "
                f"slot1_mutated={rep.slot1_tier0_vault_mutated} "
                f"rf_pkts={rep.wireless_rf_packets_emitted} "
                f"slot1_writes={rep.slot1_data_sector_writes} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_bright_monitoring_shot_mark_big6_home_and_ssh_auth(
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    force_clean_room: bool,
    simulate_bench_dry_run: bool,
    json_output: bool,
    summary_output: bool,
    markdown_out: Optional[Path],
    output_path: Optional[Path],
    sony_help_guide_id: str,
    reset_action: str,
    shoot_mode: str,
    exposure_mode: str,
    focus_mode: str,
    bright_monitoring_active: bool,
    bright_monitoring_in_shoot_menu_claimed: bool,
    live_view_display: str,
    expect_setting_effect_on_during_bright_monitoring: bool,
    expect_bright_monitoring_blocks_focus_magnifier: bool,
    claimed_bright_monitoring_persists_after_power_cycle: bool,
    monitor_brightness_mode: str,
    monitor_brightness_level: int,
    dormant_lcd_brightness_mode_requested: bool,
    claimed_monitor_brightness_wiped_by_camera_reset: bool,
    fx6_backlight_is_lcd_brightness_claimed: bool,
    fx6_vf_brightness_1_15_in_fx3_claimed: bool,
    dormant_divide_or_extract_requested: bool,
    dormant_ftp_cut_15_30_60s_requested: bool,
    shot_mark_write_requested: bool,
    shot_mark_slot: int,
    clip_flag: str,
    clip_flag_write_requested: bool,
    clip_flag_slot: int,
    photo_capture_requested: bool,
    photo_capture_slot: int,
    create_divider_frame_requested: bool,
    divider_frame_slot: int,
    edit_write_requested: bool,
    edit_write_slot: int,
    slot1_contains_tier0_dump: bool,
    slot1_wp_locked: bool,
    bulb_enabled: bool,
    shutter_type: str,
    still_drive_mode: str,
    anti_flicker_shoot: str,
    expect_bulb_in_electronic_or_cont_or_interval: bool,
    dro_mode: str,
    dro_bracket_mode: str,
    picture_profile: str,
    log_shooting_mode: str,
    hlg_still_image: str,
    expect_dro_active_with_pp_or_hlg: bool,
    dormant_bulb_timer_requested: bool,
    dormant_auto_hdr_requested: bool,
    dormant_bt_tc_link_requested: bool,
    fx3_bt_tc_link_present_claimed: bool,
    fx6_bt_tc_link_claimed: bool,
    fx3_builtin_bnc_tc_in_out_switch_claimed: bool,
    vmc_bncm1_ext_lk_active: bool,
    tc_make: str,
    tc_run: str,
    wifi_sku: str,
    wifi_band_5ghz_requested: bool,
    outdoor_5ghz_w52_requested: bool,
    wifi_security_protocol: str,
    dormant_legacy_wifi_sec_requested: bool,
    wifi_enabled: bool,
    usb_lan_cnct_launch: str,
    network_transport: str,
    multi_micro_usb_device_attached: bool,
    exposed_usb_lan_kmods: Optional[str],
    airplane_mode: str,
    bluetooth_enabled: bool,
    wireless_rf_packets_emitted: int,
    rf_nvs_p12_p13_writes_requested: bool,
    claimed_airplane_wiped_by_reset: bool,
    mode_settings: str,
    big6_home_screen_active: bool,
    home_trigger_method: str,
    exposed_big6_tiles: Optional[str],
    home_lower_left_mode: str,
    fx3_physical_e_nd_claimed: bool,
    e_nd_actuator_tx_count: int,
    expect_big6_displays_pp_during_log: bool,
    expect_big6_displays_variable_iso_in_cine_ei: bool,
    claimed_menu_fn_do_not_exit_home: bool,
    framing_enabled: str,
    framing_rec_stream_area: str,
    framing_hdmi_area: str,
    apsc_s35_on: bool,
    rec_fps: float,
    sq_fps: float,
    active_rec_or_stream_during_framing_toggle: bool,
    dormant_auto_framing_requested: bool,
    fx3_auto_framing_present_claimed: bool,
    interval_shooting_active: bool,
    exposed_interval_params: Optional[str],
    interval_start_sec: int,
    interval_sec: int,
    interval_num_shots: int,
    interval_ae_tracking: str,
    interval_shutter_type: str,
    interval_shoot_priority: str,
    interval_target_slot: int,
    claimed_interval_7params_survive_camera_reset: bool,
    fx3_interval_outputs_single_mxf_claimed: bool,
    simult_recording: bool,
    tc_regen_source_slot: int,
    claimed_tc_make_run_wiped_by_camera_reset: bool,
    fx3_has_clock_tc_mode_claimed: bool,
    hdmi_tc_output: str,
    hdmi_rec_control: str,
    rec_media_dur_hdmi_output: str,
    streaming_active: bool,
    hdmi_4ch_audio_output: str,
    access_authen: str,
    access_authen_protocol: str,
    dormant_http_https_camera_auth_claimed: bool,
    claimed_access_authen_wiped_by_camera_reset: bool,
    expect_root_cert_authenticates_inbound_http_server: bool,
    fx3_fan_control: str,
    fx6_fan_control: str,
    dormant_fan_control_max_requested: bool,
    auto_power_off_temp: str,
    handheld_bare_skin_unacknowledged: bool,
    claimed_fan_or_autotemp_wiped_by_camera_reset: bool,
    simulated_passive_tx_bytes: int,
    simulated_h0_h3_drifted_surfaces: int,
    claim_hardware_live_attach_authorized: bool,
    claim_persistent_emmc_writes_authorized: bool,
    claim_cross_model_flash_authorized: bool,
    receipt_a: Optional[Path],
    receipt_b: Optional[Path],
    model_id: Optional[str],
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
) -> int:
    from .realhw_bright_mon_shotmark_big6_home_and_ssh_auth_verifier import (
        P316_BIG6_SIX_TILES,
        P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED,
        P316_INTERVAL_SHOOT_7_PARAMS,
        P316_USB_LAN_KERNEL_MODULES,
        evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight,
        render_phase316_markdown,
        verify_phase316_report,
    )
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )

    parsed_model_id = int(model_id, 0) if model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (receipt_a is not None or receipt_b is not None) and body_serial and emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
        h0_b = dict(h0_a)

    usblan_kmods = (
        tuple(x.strip() for x in exposed_usb_lan_kmods.split(",") if x.strip())
        if exposed_usb_lan_kmods is not None
        else P316_USB_LAN_KERNEL_MODULES
    )
    big6_tiles = (
        tuple(x.strip() for x in exposed_big6_tiles.split(",") if x.strip())
        if exposed_big6_tiles is not None
        else P316_BIG6_SIX_TILES
    )
    interval_params = (
        tuple(x.strip() for x in exposed_interval_params.split(",") if x.strip())
        if exposed_interval_params is not None
        else P316_INTERVAL_SHOOT_7_PARAMS
    )

    rep = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
        simulate_bench_dry_run=simulate_bench_dry_run,
        force_clean_room=True if force_clean_room else None,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        focus_mode=focus_mode,
        bright_monitoring_active=bright_monitoring_active,
        bright_monitoring_in_shoot_menu_claimed=bright_monitoring_in_shoot_menu_claimed,
        live_view_display=live_view_display,
        expect_setting_effect_on_during_bright_monitoring=expect_setting_effect_on_during_bright_monitoring,
        expect_bright_monitoring_blocks_focus_magnifier=expect_bright_monitoring_blocks_focus_magnifier,
        claimed_bright_monitoring_persists_after_power_cycle=claimed_bright_monitoring_persists_after_power_cycle,
        monitor_brightness_mode=monitor_brightness_mode,
        monitor_brightness_level=monitor_brightness_level,
        dormant_lcd_brightness_mode_requested=dormant_lcd_brightness_mode_requested,
        claimed_monitor_brightness_wiped_by_camera_reset=claimed_monitor_brightness_wiped_by_camera_reset,
        fx6_backlight_is_lcd_brightness_claimed=fx6_backlight_is_lcd_brightness_claimed,
        fx6_vf_brightness_1_15_in_fx3_claimed=fx6_vf_brightness_1_15_in_fx3_claimed,
        dormant_divide_or_extract_requested=dormant_divide_or_extract_requested,
        dormant_ftp_cut_15_30_60s_requested=dormant_ftp_cut_15_30_60s_requested,
        shot_mark_write_requested=shot_mark_write_requested,
        shot_mark_slot=shot_mark_slot,
        clip_flag=clip_flag,
        clip_flag_write_requested=clip_flag_write_requested,
        clip_flag_slot=clip_flag_slot,
        photo_capture_requested=photo_capture_requested,
        photo_capture_slot=photo_capture_slot,
        create_divider_frame_requested=create_divider_frame_requested,
        divider_frame_slot=divider_frame_slot,
        edit_write_requested=edit_write_requested,
        edit_write_slot=edit_write_slot,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        bulb_enabled=bulb_enabled,
        shutter_type=shutter_type,
        still_drive_mode=still_drive_mode,
        anti_flicker_shoot=anti_flicker_shoot,
        expect_bulb_in_electronic_or_cont_or_interval=expect_bulb_in_electronic_or_cont_or_interval,
        dro_mode=dro_mode,
        dro_bracket_mode=dro_bracket_mode,
        picture_profile=picture_profile,
        log_shooting_mode=log_shooting_mode,
        hlg_still_image=hlg_still_image,
        expect_dro_active_with_pp_or_hlg=expect_dro_active_with_pp_or_hlg,
        dormant_bulb_timer_requested=dormant_bulb_timer_requested,
        dormant_auto_hdr_requested=dormant_auto_hdr_requested,
        dormant_bt_tc_link_requested=dormant_bt_tc_link_requested,
        fx3_bt_tc_link_present_claimed=fx3_bt_tc_link_present_claimed,
        fx6_bt_tc_link_claimed=fx6_bt_tc_link_claimed,
        fx3_builtin_bnc_tc_in_out_switch_claimed=fx3_builtin_bnc_tc_in_out_switch_claimed,
        vmc_bncm1_ext_lk_active=vmc_bncm1_ext_lk_active,
        tc_make=tc_make,
        tc_run=tc_run,
        wifi_sku=wifi_sku,
        wifi_band_5ghz_requested=wifi_band_5ghz_requested,
        outdoor_5ghz_w52_requested=outdoor_5ghz_w52_requested,
        wifi_security_protocol=wifi_security_protocol,
        dormant_legacy_wifi_sec_requested=dormant_legacy_wifi_sec_requested,
        wifi_enabled=wifi_enabled,
        usb_lan_cnct_launch=usb_lan_cnct_launch,
        network_transport=network_transport,
        multi_micro_usb_device_attached=multi_micro_usb_device_attached,
        exposed_usb_lan_kmods=usblan_kmods,
        airplane_mode=airplane_mode,
        bluetooth_enabled=bluetooth_enabled,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        rf_nvs_p12_p13_writes_requested=rf_nvs_p12_p13_writes_requested,
        claimed_airplane_wiped_by_reset=claimed_airplane_wiped_by_reset,
        mode_settings=mode_settings,
        big6_home_screen_active=big6_home_screen_active,
        home_trigger_method=home_trigger_method,
        exposed_big6_tiles=big6_tiles,
        home_lower_left_mode=home_lower_left_mode,
        fx3_physical_e_nd_claimed=fx3_physical_e_nd_claimed,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        expect_big6_displays_pp_during_log=expect_big6_displays_pp_during_log,
        expect_big6_displays_variable_iso_in_cine_ei=expect_big6_displays_variable_iso_in_cine_ei,
        claimed_menu_fn_do_not_exit_home=claimed_menu_fn_do_not_exit_home,
        framing_enabled=framing_enabled,
        framing_rec_stream_area=framing_rec_stream_area,
        framing_hdmi_area=framing_hdmi_area,
        apsc_s35_on=apsc_s35_on,
        rec_fps=rec_fps,
        sq_fps=sq_fps,
        active_rec_or_stream_during_framing_toggle=active_rec_or_stream_during_framing_toggle,
        dormant_auto_framing_requested=dormant_auto_framing_requested,
        fx3_auto_framing_present_claimed=fx3_auto_framing_present_claimed,
        interval_shooting_active=interval_shooting_active,
        exposed_interval_params=interval_params,
        interval_start_sec=interval_start_sec,
        interval_sec=interval_sec,
        interval_num_shots=interval_num_shots,
        interval_ae_tracking=interval_ae_tracking,
        interval_shutter_type=interval_shutter_type,
        interval_shoot_priority=interval_shoot_priority,
        interval_target_slot=interval_target_slot,
        claimed_interval_7params_survive_camera_reset=claimed_interval_7params_survive_camera_reset,
        fx3_interval_outputs_single_mxf_claimed=fx3_interval_outputs_single_mxf_claimed,
        simult_recording=simult_recording,
        tc_regen_source_slot=tc_regen_source_slot,
        claimed_tc_make_run_wiped_by_camera_reset=claimed_tc_make_run_wiped_by_camera_reset,
        fx3_has_clock_tc_mode_claimed=fx3_has_clock_tc_mode_claimed,
        hdmi_tc_output=hdmi_tc_output,
        hdmi_rec_control=hdmi_rec_control,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        streaming_active=streaming_active,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        access_authen=access_authen,
        access_authen_protocol=access_authen_protocol,
        dormant_http_https_camera_auth_claimed=dormant_http_https_camera_auth_claimed,
        claimed_access_authen_wiped_by_camera_reset=claimed_access_authen_wiped_by_camera_reset,
        expect_root_cert_authenticates_inbound_http_server=expect_root_cert_authenticates_inbound_http_server,
        fx3_fan_control=fx3_fan_control,
        fx6_fan_control=fx6_fan_control,
        dormant_fan_control_max_requested=dormant_fan_control_max_requested,
        auto_power_off_temp=auto_power_off_temp,
        handheld_bare_skin_unacknowledged=handheld_bare_skin_unacknowledged,
        claimed_fan_or_autotemp_wiped_by_camera_reset=claimed_fan_or_autotemp_wiped_by_camera_reset,
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=claim_cross_model_flash_authorized,
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
        markdown_out.write_text(render_phase316_markdown(rep), encoding="utf-8")
    v_res = verify_phase316_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED,
    )
    try:
        if json_output and not summary_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash={rep.cross_model_flash_authorized} "
                f"bt_tclink={rep.fx3_bt_tc_link_present} "
                f"auto_framing={rep.fx3_auto_framing_present} "
                f"bulb_timer={rep.fx3_bulb_timer_present} "
                f"auto_hdr={rep.fx3_auto_hdr_present} "
                f"e_nd={rep.fx3_physical_e_nd_present} "
                f"fan_max={rep.fx3_fan_control_max_present}/{rep.fx6_fan_control_max_present} "
                f"slot1_mutated={rep.slot1_tier0_vault_mutated} "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"rf_pkts={rep.wireless_rf_packets_emitted} "
                f"slot1_writes={rep.slot1_data_sector_writes} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes(args: argparse.Namespace) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_verifier import (
        P321_ASPECT_MARKER_16_STATES,
        P321_GO_NO_GO_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED,
        render_phase321_markdown,
        run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight,
        verify_phase321_report,
    )

    parsed_model_id = int(args.model_id, 0) if args.model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (args.receipt_a is not None or args.receipt_b is not None) and args.body_serial and args.emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=args.body_serial, emmc_cid=args.emmc_cid)
        h0_b = dict(h0_a)

    exposed_markers = (
        tuple(x.strip() for x in args.exposed_aspect_markers.split(",") if x.strip())
        if args.exposed_aspect_markers
        else P321_ASPECT_MARKER_16_STATES
    )

    rep = run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
        simulate_bench_dry_run=args.simulate_bench_dry_run,
        force_clean_room=True if args.force_clean_room else None,
        fx6_lib_dir=args.fx6_lib_dir,
        fx3_modules_dir=args.fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=args.body_fw,
        sony_help_guide_id=args.sony_help_guide_id,
        reset_action=args.reset_action,
        shoot_mode=args.shoot_mode,
        recording_media=args.recording_media,
        auto_switch_media=args.auto_switch_media,
        dormant_prioritize_rec_media_requested=args.dormant_prioritize_rec_media_requested,
        fx3_prioritize_rec_media_present_claimed=args.fx3_prioritize_rec_media_present_claimed,
        fx3_movie_sort_recording_present_claimed=args.fx3_movie_sort_recording_present_claimed,
        claimed_auto_switch_wiped_by_camera_reset=args.claimed_auto_switch_wiped_by_camera_reset,
        slot1_fs=args.slot1_fs,
        slot2_fs=args.slot2_fs,
        slot1_contains_tier0_dump=args.slot1_contains_tier0_dump,
        slot1_wp_locked=args.slot1_wp_locked,
        slot1_rec_write_requested=args.slot1_rec_write_requested,
        slot1_data_sector_writes=args.slot1_data_sector_writes,
        fx3_independent_rec_button_slot_set_claimed=args.fx3_independent_rec_button_slot_set_claimed,
        fx6_relay_with_proxy_streaming_chunk_claimed=args.fx6_relay_with_proxy_streaming_chunk_claimed,
        media_speed_grade=args.media_speed_grade,
        movie_file_format=args.movie_file_format,
        movie_bitrate_mbps=args.movie_bitrate_mbps,
        rec_fps=args.rec_fps,
        sq_enabled=args.sq_enabled,
        sq_fps=args.sq_fps,
        proxy_recording=args.proxy_recording,
        proxy_file_format=args.proxy_file_format,
        proxy_record_setting=args.proxy_record_setting,
        dormant_proxy_8bit_fhd_requested=args.dormant_proxy_8bit_fhd_requested,
        vpg400_caution_acknowledged=args.vpg400_caution_acknowledged,
        claimed_sdhc_no_4gb_split=args.claimed_sdhc_no_4gb_split,
        claimed_proxy_blocked_on_dci4k_60p=args.claimed_proxy_blocked_on_dci4k_60p,
        claimed_proxy_resists_camera_reset=args.claimed_proxy_resists_camera_reset,
        proxy_slot1_write_or_coupled_delete_requested=args.proxy_slot1_write_or_coupled_delete_requested,
        claimed_fx3_has_fx6_chunk_upload=args.claimed_fx3_has_fx6_chunk_upload,
        cloud_connection=args.cloud_connection,
        c3_portal_enabled=args.c3_portal_enabled,
        clip_flag_filter=args.clip_flag_filter,
        claimed_cloud_wiped_by_camera_reset=args.claimed_cloud_wiped_by_camera_reset,
        claimed_cloud_wiped_by_initialize=args.claimed_cloud_wiped_by_initialize,
        claimed_c3_portal_before_v400=args.claimed_c3_portal_before_v400,
        claimed_fx3_cloud_does_not_exclude_ftp=args.claimed_fx3_cloud_does_not_exclude_ftp,
        airplane_mode=args.airplane_mode,
        cnct_while_power_off=args.cnct_while_power_off,
        bluetooth_function=args.bluetooth_function,
        wifi_enabled=args.wifi_enabled,
        wireless_rf_packets_emitted=args.wireless_rf_packets_emitted,
        rf_nvs_p12_p13_writes_requested=args.rf_nvs_p12_p13_writes_requested,
        claimed_cnct_while_power_off_wiped_by_camera_reset=args.claimed_cnct_while_power_off_wiped_by_camera_reset,
        fx6_has_bluetooth_claimed=args.fx6_has_bluetooth_claimed,
        mymenu_pages=args.mymenu_pages,
        mymenu_slots_per_page=args.mymenu_slots_per_page,
        mymenu_total_slots=args.mymenu_total_slots,
        fx3_mymenu_30_or_36_slots_only_claimed=args.fx3_mymenu_30_or_36_slots_only_claimed,
        mymenu_playback_item_requested=args.mymenu_playback_item_requested,
        claimed_mymenu_wiped_by_camera_reset=args.claimed_mymenu_wiped_by_camera_reset,
        fx6_user_menu_pin=args.fx6_user_menu_pin,
        claimed_fx3_has_pin_user_menu_with_lock=args.claimed_fx3_has_pin_user_menu_with_lock,
        claimed_fx6_user_menu_pin_included_in_all_file=args.claimed_fx6_user_menu_pin_included_in_all_file,
        ftp_transfer_func=args.ftp_transfer_func,
        ftp_server_slot=args.ftp_server_slot,
        ftp_protocol=args.ftp_protocol,
        ftp_transfer_mode=args.ftp_transfer_mode,
        ftp_active_mode_requested=args.ftp_active_mode_requested,
        fx3_sftp_present_claimed=args.fx3_sftp_present_claimed,
        fx3_ftp_active_mode_present_claimed=args.fx3_ftp_active_mode_present_claimed,
        dormant_transfer_jpeg_heif_size_requested=args.dormant_transfer_jpeg_heif_size_requested,
        fx3_transfer_jpeg_heif_size_present_claimed=args.fx3_transfer_jpeg_heif_size_present_claimed,
        claimed_fx3_uses_certification_pem_slot_b=args.claimed_fx3_uses_certification_pem_slot_b,
        claimed_fx3_ftp_limited_to_3_servers=args.claimed_fx3_ftp_limited_to_3_servers,
        ftp_slot1_write_or_transfer_list_requested=args.ftp_slot1_write_or_transfer_list_requested,
        cacert_pem_size_bytes=args.cacert_pem_size_bytes,
        cacert_write_to_slot1_requested=args.cacert_write_to_slot1_requested,
        usb_lan_tethering=args.usb_lan_tethering,
        usb_lan_cnct_launch=args.usb_lan_cnct_launch,
        network_transport=args.network_transport,
        claimed_airplane_mode_blocks_usb_lan=args.claimed_airplane_mode_blocks_usb_lan,
        wb_mode=args.wb_mode,
        wb_kelvin_k=args.wb_kelvin_k,
        wb_ab_shift=args.wb_ab_shift,
        wb_gm_shift=args.wb_gm_shift,
        log_shooting_mode=args.log_shooting_mode,
        picture_profile=args.picture_profile,
        custom_wb_setup_requested=args.custom_wb_setup_requested,
        claimed_custom_wb_saved_in_camset=args.claimed_custom_wb_saved_in_camset,
        claimed_custom_wb_wiped_by_camera_reset=args.claimed_custom_wb_wiped_by_camera_reset,
        priority_set_in_awb=args.priority_set_in_awb,
        shutter_awb_lock=args.shutter_awb_lock,
        shockless_wb=args.shockless_wb,
        claimed_shutter_awb_lock_wiped_by_camera_reset=args.claimed_shutter_awb_lock_wiped_by_camera_reset,
        claimed_shockless_wb_resists_camera_reset=args.claimed_shockless_wb_resists_camera_reset,
        claimed_fx3_has_atw_speed_or_memory_ah=args.claimed_fx3_has_atw_speed_or_memory_ah,
        af_transition_speed=args.af_transition_speed,
        af_subj_shift_sens=args.af_subj_shift_sens,
        fx3_af_subj_shift_7_levels_claimed=args.fx3_af_subj_shift_7_levels_claimed,
        fx6_af_subj_shift_7_levels_claimed=args.fx6_af_subj_shift_7_levels_claimed,
        af_assist=args.af_assist,
        lens_model=args.lens_model,
        claimed_af_assist_resists_camera_reset=args.claimed_af_assist_resists_camera_reset,
        in_body_focus_map_requested=args.in_body_focus_map_requested,
        fx3_in_body_focus_map_present_claimed=args.fx3_in_body_focus_map_present_claimed,
        fx3_uvc_streaming_present_claimed=args.fx3_uvc_streaming_present_claimed,
        mc_focus_map_enabled=args.mc_focus_map_enabled,
        mc_focus_map_fps=args.mc_focus_map_fps,
        mc_focus_map_over_wifi_requested=args.mc_focus_map_over_wifi_requested,
        playback_control_active=args.playback_control_active,
        lens_pdaf_capable=args.lens_pdaf_capable,
        auto_framing_claimed=args.auto_framing_claimed,
        usb_remote_or_uvc_active=args.usb_remote_or_uvc_active,
        claimed_mc_focus_map_blocked_at_120p=args.claimed_mc_focus_map_blocked_at_120p,
        aspect_marker=args.aspect_marker,
        exposed_aspect_markers=exposed_markers,
        safety_zone=args.safety_zone,
        peaking_display=args.peaking_display,
        peaking_level=args.peaking_level,
        peaking_color=args.peaking_color,
        focus_magnifier_active=args.focus_magnifier_active,
        expect_marker_or_peaking_on_hdmi=args.expect_marker_or_peaking_on_hdmi,
        expect_marker_visible_during_focus_magnifier=args.expect_marker_visible_during_focus_magnifier,
        claimed_marker_or_peaking_wiped_by_camera_reset=args.claimed_marker_or_peaking_wiped_by_camera_reset,
        claimed_fx3_has_user_box_or_925_95_safety_or_bw_peaking=args.claimed_fx3_has_user_box_or_925_95_safety_or_bw_peaking,
        e_nd_actuator_tx_count=args.e_nd_actuator_tx_count,
        usb_packets_transmitted=args.usb_packets_transmitted,
        simulated_passive_tx_bytes=args.simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=args.simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=args.claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=args.claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=args.claim_cross_model_flash_authorized,
        receipt_a_path=args.receipt_a,
        receipt_b_path=args.receipt_b,
        body_serial=args.body_serial,
        emmc_cid=args.emmc_cid,
        h0_baselines_a=h0_a,
        h0_baselines_b=h0_b,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_phase321_markdown(rep), encoding="utf-8")
    v_res = verify_phase321_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P321_GO_NO_GO_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED,
    )
    try:
        if args.json and not args.summary:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash={rep.cross_model_flash_authorized} "
                f"prioritize_rec={rep.fx3_prioritize_rec_media_present} "
                f"movie_sort={rep.fx3_movie_sort_recording_present} "
                f"mymenu_42={rep.check_group_b.mymenu_total_slots} "
                f"sftp={rep.fx3_ftp_sftp_present} "
                f"inbody_fmap={rep.fx3_in_body_focus_map_present} "
                f"slot1_mutated={rep.slot1_tier0_vault_mutated} "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"rf_pkts={rep.rf_packets_transmitted} "
                f"slot1_writes={rep.slot1_data_sector_writes} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter(
    args: argparse.Namespace,
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier import (
        P329_GO_NO_GO_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_VERIFIED,
        P329_HDMI_SETTINGS_EXACT_EIGHT_ITEMS,
        P329_TARGET_FUNCTION_EXACT_TWO_ITEMS,
        render_phase329_markdown,
        run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight,
        verify_phase329_report,
    )

    parsed_model_id = int(args.model_id, 0) if args.model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (args.receipt_a is not None or args.receipt_b is not None) and args.body_serial and args.emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=args.body_serial, emmc_cid=args.emmc_cid)
        h0_b = dict(h0_a)

    exposed_target = (
        tuple(x.strip() for x in args.exposed_target_function_items.split(",") if x.strip())
        if args.exposed_target_function_items is not None
        else P329_TARGET_FUNCTION_EXACT_TWO_ITEMS
    )
    exposed_hdmi = (
        tuple(x.strip() for x in args.exposed_hdmi_settings_items.split(",") if x.strip())
        if args.exposed_hdmi_settings_items is not None
        else P329_HDMI_SETTINGS_EXACT_EIGHT_ITEMS
    )

    rep = run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
        simulate_bench_dry_run=args.simulate_bench_dry_run,
        force_clean_room=True if args.force_clean_room else None,
        fx6_lib_dir=args.fx6_lib_dir,
        fx3_modules_dir=args.fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=args.body_fw,
        sony_help_guide_id=args.sony_help_guide_id,
        reset_action=args.reset_action,
        shoot_mode=args.shoot_mode,
        exposure_mode=args.exposure_mode,
        # Group A
        audio_recording=args.audio_recording,
        audio_out_timing=args.audio_out_timing,
        claimed_audio_out_timing_under_setup_sound_option=args.claimed_audio_out_timing_under_setup_sound_option,
        audio_out_timing_active_in_sq_claimed=args.audio_out_timing_active_in_sq_claimed,
        audio_recording_in_sq_claimed=args.audio_recording_in_sq_claimed,
        claimed_audio_out_timing_resists_reset=args.claimed_audio_out_timing_resists_reset,
        dormant_audio_level_display_requested=args.dormant_audio_level_display_requested,
        fx3_audio_level_display_menu_present_claimed=args.fx3_audio_level_display_menu_present_claimed,
        audio_rec_level=args.audio_rec_level,
        fx3_disable_builtin_limiter_requested=args.fx3_disable_builtin_limiter_requested,
        fx3_limiter_6step_present_claimed=args.fx3_limiter_6step_present_claimed,
        fx3_32bit_float_audio_claimed=args.fx3_32bit_float_audio_claimed,
        four_ch_audio_monitoring=args.four_ch_audio_monitoring,
        shoe_audio_set=args.shoe_audio_set,
        movie_file_format=args.movie_file_format,
        rec_fps=args.rec_fps,
        sq_enabled=args.sq_enabled,
        sq_fps=args.sq_fps,
        proxy_recording=args.proxy_recording,
        claimed_shoe_4ch_unsupported_on_xavc_codec=args.claimed_shoe_4ch_unsupported_on_xavc_codec,
        expect_proxy_4ch_24bit_audio=args.expect_proxy_4ch_24bit_audio,
        expect_proxy_active_at_100p_plus=args.expect_proxy_active_at_100p_plus,
        mic_35mm_inserted=args.mic_35mm_inserted,
        expect_shoe_audio_active_with_35mm_mic=args.expect_shoe_audio_active_with_35mm_mic,
        xlr_h1_attached=args.xlr_h1_attached,
        xlr_h1_handle_audio=args.xlr_h1_handle_audio,
        xlr_h1_dig_analog=args.xlr_h1_dig_analog,
        xlr_h1_input_select=args.xlr_h1_input_select,
        expect_xlr_h1_audio_active_when_handle_off=args.expect_xlr_h1_audio_active_when_handle_off,
        wind_noise_reduct=args.wind_noise_reduct,
        expect_wind_noise_applies_to_xlr_or_35mm=args.expect_wind_noise_applies_to_xlr_or_35mm,
        face_eye_prior_in_af=args.face_eye_prior_in_af,
        face_eye_subject=args.face_eye_subject,
        dormant_subject_requested=args.dormant_subject_requested,
        fx3_bird_insect_car_airplane_present_claimed=args.fx3_bird_insect_car_airplane_present_claimed,
        fx3_animal_eye_af_in_movie_present_claimed=args.fx3_animal_eye_af_in_movie_present_claimed,
        expect_animal_eye_af_in_movie=args.expect_animal_eye_af_in_movie,
        right_left_eye_select=args.right_left_eye_select,
        face_eye_frame_disp=args.face_eye_frame_disp,
        expect_face_eye_frame_on_clean_hdmi=args.expect_face_eye_frame_on_clean_hdmi,
        face_memory_count=args.face_memory_count,
        regist_faces_priority=args.regist_faces_priority,
        claimed_face_memory_wiped_by_camera_reset=args.claimed_face_memory_wiped_by_camera_reset,
        claimed_face_memory_exported_in_camset=args.claimed_face_memory_exported_in_camset,
        expect_regist_faces_priority_active_in_animal=args.expect_regist_faces_priority_active_in_animal,
        fx6_has_animal_or_bird_subject_claimed=args.fx6_has_animal_or_bird_subject_claimed,
        fx6_has_persistent_face_memory_claimed=args.fx6_has_persistent_face_memory_claimed,
        # Group B
        silent_mode=args.silent_mode,
        audio_signals=args.audio_signals,
        shutter_type=args.shutter_type,
        flash_enabled=args.flash_enabled,
        long_exposure_nr=args.long_exposure_nr,
        e_front_curtain_shut=args.e_front_curtain_shut,
        bulb_enabled=args.bulb_enabled,
        anti_flicker_shoot=args.anti_flicker_shoot,
        claimed_silent_mode_auto_disables_af_illuminator=args.claimed_silent_mode_auto_disables_af_illuminator,
        claimed_silent_mode_is_single_bool_toggle=args.claimed_silent_mode_is_single_bool_toggle,
        exposed_target_function_items=exposed_target,
        target_aperture_drive_in_af=args.target_aperture_drive_in_af,
        target_auto_pixel_mapping=args.target_auto_pixel_mapping,
        expect_aperture_drive_silent_in_movie=args.expect_aperture_drive_silent_in_movie,
        cnflasha_write_on_poweroff_allowed=args.cnflasha_write_on_poweroff_allowed,
        dormant_shutter_when_pwr_off_requested=args.dormant_shutter_when_pwr_off_requested,
        fx3_shutter_when_pwr_off_present_claimed=args.fx3_shutter_when_pwr_off_present_claimed,
        fx6_shutter_when_pwr_off_present_claimed=args.fx6_shutter_when_pwr_off_present_claimed,
        airplane_mode=args.airplane_mode,
        wifi_enabled=args.wifi_enabled,
        wireless_rf_packets_emitted=args.wireless_rf_packets_emitted,
        version_update_badge_active=args.version_update_badge_active,
        slot1_contains_tier0_dump=args.slot1_contains_tier0_dump,
        slot1_bodydata_stage_requested=args.slot1_bodydata_stage_requested,
        software_update_trigger_requested=args.software_update_trigger_requested,
        slot1_bodydata_writes=args.slot1_bodydata_writes,
        cross_model_flash_requested=args.cross_model_flash_requested,
        bodydata_in_slot2_claimed=args.bodydata_in_slot2_claimed,
        source_fw_for_update_audit=args.source_fw_for_update_audit,
        stepping_stone_v204_v205_completed=args.stepping_stone_v204_v205_completed,
        direct_v202_to_v702_flash_claimed=args.direct_v202_to_v702_flash_claimed,
        battery_soc_pct=args.battery_soc_pct,
        fx6_update_slot_claimed=args.fx6_update_slot_claimed,
        fx6_battery_only_update_claimed=args.fx6_battery_only_update_claimed,
        # Group C
        log_shooting_mode=args.log_shooting_mode,
        picture_profile=args.picture_profile,
        exposed_hdmi_settings_items=exposed_hdmi,
        dormant_color_gamut_for_raw_requested=args.dormant_color_gamut_for_raw_requested,
        fx3_color_gamut_for_raw_present_claimed=args.fx3_color_gamut_for_raw_present_claimed,
        claimed_hdmi_settings_wiped_by_camera_reset=args.claimed_hdmi_settings_wiped_by_camera_reset,
        rec_media_dur_hdmi_output=args.rec_media_dur_hdmi_output,
        recording_media=args.recording_media,
        slot1_wp_locked=args.slot1_wp_locked,
        slot1_data_sector_writes=args.slot1_data_sector_writes,
        internal_co_rec_write_to_slot1_requested=args.internal_co_rec_write_to_slot1_requested,
        expect_internal_writes_during_hdmi_only=args.expect_internal_writes_during_hdmi_only,
        hdmi_output_resolution=args.hdmi_output_resolution,
        expect_4k_hdmi_with_rec_on_during_log_or_pplut=args.expect_4k_hdmi_with_rec_on_during_log_or_pplut,
        hdmi_4k_setting=args.hdmi_4k_setting,
        dormant_4k_24p_8bit_requested=args.dormant_4k_24p_8bit_requested,
        fx3_4k_24p_8bit_present_claimed=args.fx3_4k_24p_8bit_present_claimed,
        expect_24p_no_reboot=args.expect_24p_no_reboot,
        hdmi_raw_output=args.hdmi_raw_output,
        raw_output_setting=args.raw_output_setting,
        hdmi_time_code_output=args.hdmi_time_code_output,
        hdmi_rec_control=args.hdmi_rec_control,
        hdmi_4ch_audio_output=args.hdmi_4ch_audio_output,
        hdmi_info_display=args.hdmi_info_display,
        allow_lcd_blanking_for_hdmi_info=args.allow_lcd_blanking_for_hdmi_info,
        expect_fx3_lcd_stays_on_when_hdmi_info_on=args.expect_fx3_lcd_stays_on_when_hdmi_info_on,
        fx6_sdi_raw_allows_4k_hdmi_claimed=args.fx6_sdi_raw_allows_4k_hdmi_claimed,
        fx6_hdmi_raw_supports_24_00p_claimed=args.fx6_hdmi_raw_supports_24_00p_claimed,
        fx6_remote_if_syncs_internal_card_claimed=args.fx6_remote_if_syncs_internal_card_claimed,
        desqueeze_display=args.desqueeze_display,
        dormant_desqueeze_1_8x_requested=args.dormant_desqueeze_1_8x_requested,
        fx3_desqueeze_1_8x_present_claimed=args.fx3_desqueeze_1_8x_present_claimed,
        claimed_desqueeze_wiped_by_camera_reset=args.claimed_desqueeze_wiped_by_camera_reset,
        desqueeze_1_6x_executed_factor=args.desqueeze_1_6x_executed_factor,
        focus_mode=args.focus_mode,
        focus_area=args.focus_area,
        steadyshot_mode=args.steadyshot_mode,
        face_priority_in_multi_metering=args.face_priority_in_multi_metering,
        expect_desqueeze_active_in_still=args.expect_desqueeze_active_in_still,
        expect_desqueeze_bakes_internal_file=args.expect_desqueeze_bakes_internal_file,
        expect_desqueeze_applied_during_bypass=args.expect_desqueeze_applied_during_bypass,
        claimed_desqueeze_locks_out_focus_mag_or_bright_mon=args.claimed_desqueeze_locks_out_focus_mag_or_bright_mon,
        fx6_desqueeze_has_1_6x_or_sdi_claimed=args.fx6_desqueeze_has_1_6x_or_sdi_claimed,
        # Group D
        rec_lamp_mode=args.rec_lamp_mode,
        dormant_tally_light_menu_requested=args.dormant_tally_light_menu_requested,
        fx3_tally_light_menu_present_claimed=args.fx3_tally_light_menu_present_claimed,
        dormant_rec_lamp_only_one_requested=args.dormant_rec_lamp_only_one_requested,
        claimed_rec_lamp_wiped_by_camera_reset=args.claimed_rec_lamp_wiped_by_camera_reset,
        expect_top_rec_ring_off_with_rear_on=args.expect_top_rec_ring_off_with_rear_on,
        claimed_silent_mode_turns_off_rec_lamp=args.claimed_silent_mode_turns_off_rec_lamp,
        emphasized_rec_display=args.emphasized_rec_display,
        claimed_emph_rec_resists_camera_reset=args.claimed_emph_rec_resists_camera_reset,
        expect_emph_rec_on_clean_hdmi=args.expect_emph_rec_on_clean_hdmi,
        remain_shoot_display=args.remain_shoot_display,
        claimed_remain_shoot_wiped_by_camera_reset=args.claimed_remain_shoot_wiped_by_camera_reset,
        expect_remain_shoot_shows_movie_time=args.expect_remain_shoot_shows_movie_time,
        auto_review=args.auto_review,
        interval_shooting_active=args.interval_shooting_active,
        expect_auto_review_in_interval=args.expect_auto_review_in_interval,
        claimed_auto_review_wiped_by_camera_reset=args.claimed_auto_review_wiped_by_camera_reset,
        dormant_var_shutter_requested=args.dormant_var_shutter_requested,
        fx3_var_shutter_present_claimed=args.fx3_var_shutter_present_claimed,
        fx6_ecs_freq_hz=args.fx6_ecs_freq_hz,
        fx3_has_ecs_mode_claimed=args.fx3_has_ecs_mode_claimed,
        apsc_s35_shooting=args.apsc_s35_shooting,
        hdmi_4k_only_active=args.hdmi_4k_only_active,
        still_image_size=args.still_image_size,
        expect_apsc_4k_or_raw=args.expect_apsc_4k_or_raw,
        claimed_apsc_wiped_by_camera_reset=args.claimed_apsc_wiped_by_camera_reset,
        claimed_apsc_still_size_4_2m=args.claimed_apsc_still_size_4_2m,
        e_nd_actuator_tx_count=args.e_nd_actuator_tx_count,
        usb_packets_transmitted=args.usb_packets_transmitted,
        simulated_passive_tx_bytes=args.simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=args.simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=args.claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=args.claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=args.claim_cross_model_flash_authorized,
        receipt_a_path=args.receipt_a,
        receipt_b_path=args.receipt_b,
        body_serial=args.body_serial,
        emmc_cid=args.emmc_cid,
        h0_baselines_a=h0_a,
        h0_baselines_b=h0_b,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_phase329_markdown(rep), encoding="utf-8")
    v_res = verify_phase329_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P329_GO_NO_GO_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_VERIFIED,
    )
    try:
        if args.json and not args.summary:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash={rep.cross_model_flash_authorized} "
                f"audio_lvl_disp={rep.fx3_audio_level_display_menu_present} "
                f"bird_etc={rep.fx3_bird_insect_car_airplane_present} "
                f"pwr_off_shut={rep.fx3_shutter_when_pwr_off_present} "
                f"raw_gamut={rep.fx3_color_gamut_for_raw_output_menu_present} "
                f"desq_18x={rep.fx3_desqueeze_1_8x_present} "
                f"tally_menu={rep.fx3_tally_light_menu_present} "
                f"var_shutter={rep.fx3_var_shutter_present} "
                f"apsc_reset={rep.fx3_apsc_resets_via_camera_settings_reset} "
                f"slot1_mutated={rep.slot1_tier0_vault_mutated} "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"rf_pkts={rep.rf_packets_transmitted} "
                f"slot1_writes={rep.slot1_data_sector_writes} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun(
    args: argparse.Namespace,
) -> int:
    from .realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier import (
        P334_COPYRIGHT_EXACT_FOUR_ITEMS,
        P334_GO_NO_GO_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED,
        P334_POWER_OPTION_EXACT_TWO_ITEMS,
        render_phase334_markdown,
        run_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight,
        verify_phase334_report,
    )
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )

    parsed_model_id = int(args.model_id, 0) if args.model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (args.receipt_a is not None or args.receipt_b is not None) and args.body_serial and args.emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=args.body_serial, emmc_cid=args.emmc_cid)
        h0_b = dict(h0_a)

    exposed_copyright = (
        tuple(x.strip() for x in args.exposed_copyright_items.split(",") if x.strip())
        if args.exposed_copyright_items is not None
        else P334_COPYRIGHT_EXACT_FOUR_ITEMS
    )
    exposed_power = (
        tuple(x.strip() for x in args.exposed_power_option_items.split(",") if x.strip())
        if args.exposed_power_option_items is not None
        else P334_POWER_OPTION_EXACT_TWO_ITEMS
    )
    bypass_conds = tuple(args.power_save_bypass_condition or ())

    rep = run_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
        simulate_bench_dry_run=args.simulate_bench_dry_run,
        force_clean_room=True if args.force_clean_room else None,
        fx6_lib_dir=args.fx6_lib_dir,
        fx3_modules_dir=args.fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=args.body_fw,
        sony_help_guide_id=args.sony_help_guide_id,
        reset_action=args.reset_action,
        shoot_mode=args.shoot_mode,
        exposure_mode=args.exposure_mode,
        # Group A
        breathing_comp=args.breathing_comp,
        rec_fps=args.rec_fps,
        sq_enabled=args.sq_enabled,
        sq_fps=args.sq_fps,
        hdmi_raw_output=args.hdmi_raw_output,
        zoom_range=args.zoom_range,
        auto_framing_claimed=args.auto_framing_claimed,
        non_compliant_or_teleconverter_lens=args.non_compliant_or_teleconverter_lens,
        claimed_breathing_comp_resists_camera_reset=args.claimed_breathing_comp_resists_camera_reset,
        claimed_static_lens_comp_reset_by_camera_reset=args.claimed_static_lens_comp_reset_by_camera_reset,
        claimed_fx3_blocks_breathing_below_100fps_sq=args.claimed_fx3_blocks_breathing_below_100fps_sq,
        fx6_breathing_allows_sq_or_distortion_off_or_raw_claimed=args.fx6_breathing_allows_sq_or_distortion_off_or_raw_claimed,
        post_breathing_comp_requested=args.post_breathing_comp_requested,
        catalyst_app=args.catalyst_app,
        distortion_comp=args.distortion_comp,
        claimed_catalyst_browse_supports_breathing_comp=args.claimed_catalyst_browse_supports_breathing_comp,
        file_number_mode=args.file_number_mode,
        series_counter_reset_slot=args.series_counter_reset_slot,
        movie_file_counter_write_slot=args.movie_file_counter_write_slot,
        file_name_format=args.file_name_format,
        camera_id=args.camera_id,
        reel_number=args.reel_number,
        camera_position=args.camera_position,
        title_name=args.title_name,
        claimed_movie_file_settings_reset_by_camera_reset=args.claimed_movie_file_settings_reset_by_camera_reset,
        claimed_custom_movie_folder_supported=args.claimed_custom_movie_folder_supported,
        claimed_file_number_reset_resets_reel=args.claimed_file_number_reset_resets_reel,
        expect_rollover_mutates_cam_id_menu=args.expect_rollover_mutates_cam_id_menu,
        claimed_cam_id_reel_uses_yyyymmdd_date=args.claimed_cam_id_reel_uses_yyyymmdd_date,
        fx6_clip_naming_uses_project_menu_or_37char_claimed=args.fx6_clip_naming_uses_project_menu_or_37char_claimed,
        recording_media=args.recording_media,
        slot1_media_type=args.slot1_media_type,
        slot2_media_type=args.slot2_media_type,
        slot1_fs=args.slot1_fs,
        slot2_fs=args.slot2_fs,
        slot1_contains_tier0_dump=args.slot1_contains_tier0_dump,
        slot1_data_sector_writes=args.slot1_data_sector_writes,
        claimed_sdhc_no_4gb_split=args.claimed_sdhc_no_4gb_split,
        # Group B
        exposed_copyright_items=exposed_copyright,
        write_copyright_info=args.write_copyright_info,
        set_photographer=args.set_photographer,
        set_copyright=args.set_copyright,
        disp_copyright_info_requested=args.disp_copyright_info_requested,
        write_serial_number=args.write_serial_number,
        claimed_copyright_wiped_by_camera_reset=args.claimed_copyright_wiped_by_camera_reset,
        claimed_write_serial_wiped_by_camera_reset=args.claimed_write_serial_wiped_by_camera_reset,
        claimed_write_serial_still_only_in_v702=args.claimed_write_serial_still_only_in_v702,
        claimed_copyright_saved_in_camset=args.claimed_copyright_saved_in_camset,
        claimed_write_serial_excluded_from_camset=args.claimed_write_serial_excluded_from_camset,
        fx6_has_copyright_info_menu_claimed=args.fx6_has_copyright_info_menu_claimed,
        exposed_power_option_items=exposed_power,
        power_save_start_time=args.power_save_start_time,
        dormant_power_save_timer_requested=args.dormant_power_save_timer_requested,
        power_save_active_bypass_conditions=bypass_conds,
        power_save_sleep_expected_during_bypass=args.power_save_sleep_expected_during_bypass,
        claimed_power_save_ignores_9_conditions=args.claimed_power_save_ignores_9_conditions,
        auto_power_off_temp=args.auto_power_off_temp,
        handheld_bare_skin_unacknowledged=args.handheld_bare_skin_unacknowledged,
        dormant_power_save_by_monitor_requested=args.dormant_power_save_by_monitor_requested,
        fx3_power_save_by_monitor_present_claimed=args.fx3_power_save_by_monitor_present_claimed,
        fx3_builtin_evf_present=args.fx3_builtin_evf_present,
        claimed_power_option_wiped_by_camera_reset=args.claimed_power_option_wiped_by_camera_reset,
        video_system=args.video_system,
        ntsc_pal_switch_requested=args.ntsc_pal_switch_requested,
        expect_ntsc_pal_no_reboot=args.expect_ntsc_pal_no_reboot,
        expect_cross_system_playback_without_switch=args.expect_cross_system_playback_without_switch,
        claimed_ntsc_pal_wiped_by_camera_reset=args.claimed_ntsc_pal_wiped_by_camera_reset,
        fx6_has_ntsc_pal_selector_claimed=args.fx6_has_ntsc_pal_selector_claimed,
        slot1_wp_locked=args.slot1_wp_locked,
        slot1_format_requested=args.slot1_format_requested,
        # Group C
        flexible_shutter_mode=args.flexible_shutter_mode,
        shutter_mode=args.shutter_mode,
        zoom_scale=args.zoom_scale,
        zoom_ring_rotate=args.zoom_ring_rotate,
        zoom_lever_stby_speed=args.zoom_lever_stby_speed,
        zoom_lever_rec_speed=args.zoom_lever_rec_speed,
        zoom_lever_2nd_speed=args.zoom_lever_2nd_speed,
        custom_key_zoom_stby_speed=args.custom_key_zoom_stby_speed,
        custom_key_zoom_rec_speed=args.custom_key_zoom_rec_speed,
        remote_zoom_speed_type=args.remote_zoom_speed_type,
        remote_zoom_fixed_stby_speed=args.remote_zoom_fixed_stby_speed,
        remote_zoom_fixed_rec_speed=args.remote_zoom_fixed_rec_speed,
        still_file_format=args.still_file_format,
        focus_area=args.focus_area,
        metering_mode=args.metering_mode,
        face_eye_prior_in_af=args.face_eye_prior_in_af,
        tracking_af_active=args.tracking_af_active,
        claimed_zoom_range_wiped_by_camera_reset=args.claimed_zoom_range_wiped_by_camera_reset,
        claimed_zoom_ring_rotate_wiped_by_camera_reset=args.claimed_zoom_ring_rotate_wiped_by_camera_reset,
        claimed_zoom_speeds_resist_camera_reset=args.claimed_zoom_speeds_resist_camera_reset,
        expect_smart_zoom_in_movie=args.expect_smart_zoom_in_movie,
        fx6_has_digital_zoom_claimed=args.fx6_has_digital_zoom_claimed,
        auto_slow_shutter=args.auto_slow_shutter,
        expect_auto_slow_shutter_active=args.expect_auto_slow_shutter_active,
        claimed_auto_slow_shutter_resists_reset=args.claimed_auto_slow_shutter_resists_reset,
        iso_mode=args.iso_mode,
        log_shooting_mode=args.log_shooting_mode,
        iso_range_limit_min=args.iso_range_limit_min,
        iso_range_limit_max=args.iso_range_limit_max,
        claimed_iso_range_limit_wiped_by_camera_reset=args.claimed_iso_range_limit_wiped_by_camera_reset,
        expect_iso_range_limit_caps_iso_auto=args.expect_iso_range_limit_caps_iso_auto,
        iso_auto_min_ss=args.iso_auto_min_ss,
        flash_enabled=args.flash_enabled,
        expect_iso_auto_min_ss_in_movie_or_sq=args.expect_iso_auto_min_ss_in_movie_or_sq,
        expect_iso_auto_min_ss_active_with_flash=args.expect_iso_auto_min_ss_active_with_flash,
        claimed_iso_auto_min_ss_resists_reset=args.claimed_iso_auto_min_ss_resists_reset,
        gamma_base_profile=args.gamma_base_profile,
        dual_base_iso_low=args.dual_base_iso_low,
        dual_base_iso_high=args.dual_base_iso_high,
        claimed_base_iso_menu_outside_cine_ei=args.claimed_base_iso_menu_outside_cine_ei,
        fx3_has_fx6_agc_claimed=args.fx3_has_fx6_agc_claimed,
        # Group D
        raw_file_type=args.raw_file_type,
        dormant_lossless_comp_requested=args.dormant_lossless_comp_requested,
        fx3_lossless_comp_present_claimed=args.fx3_lossless_comp_present_claimed,
        claimed_raw_file_type_resists_reset=args.claimed_raw_file_type_resists_reset,
        jh_file_type=args.jh_file_type,
        hlg_still_image=args.hlg_still_image,
        auto_switch_media=args.auto_switch_media,
        auto_switch_failover_to_slot1_requested=args.auto_switch_failover_to_slot1_requested,
        usb_connection_mode=args.usb_connection_mode,
        usb_lun_setting=args.usb_lun_setting,
        claimed_usb_lun_single_exposes_slot2=args.claimed_usb_lun_single_exposes_slot2,
        host_msc_isolated=args.host_msc_isolated,
        host_spotlight_fseventsd_fsck_unblocked=args.host_spotlight_fseventsd_fsck_unblocked,
        air_gapped_bench=args.air_gapped_bench,
        claimed_usb_settings_wiped_by_camera_reset=args.claimed_usb_settings_wiped_by_camera_reset,
        usb_power_supply=args.usb_power_supply,
        usb_power_terminal=args.usb_power_terminal,
        power_source=args.power_source,
        np_fz100_inserted=args.np_fz100_inserted,
        dc_c1_coupler_inserted=args.dc_c1_coupler_inserted,
        dc_c1_pd_watts=args.dc_c1_pd_watts,
        dc_c1_cable_amps=args.dc_c1_cable_amps,
        expect_batteryless_usb_pd_without_dc_c1=args.expect_batteryless_usb_pd_without_dc_c1,
        dormant_uvc_streaming_requested=args.dormant_uvc_streaming_requested,
        fx3_native_uvc_present_claimed=args.fx3_native_uvc_present_claimed,
        fx6_native_uvc_present_claimed=args.fx6_native_uvc_present_claimed,
        streaming_protocol=args.streaming_protocol,
        movie_rec_during_streaming=args.movie_rec_during_streaming,
        rec_media_dur_hdmi_output=args.rec_media_dur_hdmi_output,
        rec_target_slot=args.rec_target_slot,
        e_nd_actuator_tx_count=args.e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=args.wireless_rf_packets_emitted,
        usb_packets_transmitted=args.usb_packets_transmitted,
        simulated_passive_tx_bytes=args.simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=args.simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=args.claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=args.claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=args.claim_cross_model_flash_authorized,
        receipt_a_path=args.receipt_a,
        receipt_b_path=args.receipt_b,
        body_serial=args.body_serial,
        emmc_cid=args.emmc_cid,
        h0_baselines_a=h0_a,
        h0_baselines_b=h0_b,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_phase334_markdown(rep), encoding="utf-8")
    v_res = verify_phase334_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P334_GO_NO_GO_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED,
    )
    try:
        if args.json and not args.summary:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash={rep.cross_model_flash_authorized} "
                f"pwr_save_mon={rep.fx3_power_save_by_monitor_present} "
                f"lossless_raw={rep.fx3_lossless_comp_raw_present} "
                f"fx3_uvc={rep.fx3_native_uvc_present} "
                f"fx6_uvc={rep.fx6_native_uvc_present} "
                f"fx6_dig_zoom={rep.fx6_digital_zoom_present} "
                f"copy_reset={rep.fx3_copyright_resets_via_camera_settings_reset} "
                f"serial_reset={rep.fx3_write_serial_resets_via_camera_settings_reset} "
                f"slot1_mutated={rep.slot1_tier0_vault_mutated} "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"rf_pkts={rep.rf_packets_transmitted} "
                f"slot1_writes={rep.slot1_data_sector_writes} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc(
    args: argparse.Namespace,
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier import (
        P338_GO_NO_GO_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_VERIFIED,
        P338_MONITOR_EXACT_THREE_ITEMS,
        P338_RECALL_CUSTOM_HOLD_EXACT_ELEVEN_SLOTS,
        render_phase338_markdown,
        run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight,
        verify_phase338_report,
    )

    parsed_model_id = int(args.model_id, 0) if args.model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (args.receipt_a is not None or args.receipt_b is not None) and args.body_serial and args.emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=args.body_serial, emmc_cid=args.emmc_cid)
        h0_b = dict(h0_a)

    exposed_monitor = (
        tuple(x.strip() for x in args.exposed_monitor_items.split(",") if x.strip())
        if args.exposed_monitor_items is not None
        else P338_MONITOR_EXACT_THREE_ITEMS
    )
    hold_eleven_slots = (
        tuple(x.strip() for x in args.recall_custom_hold_eleven_slots.split(",") if x.strip())
        if args.recall_custom_hold_eleven_slots is not None
        else P338_RECALL_CUSTOM_HOLD_EXACT_ELEVEN_SLOTS
    )

    rep = run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
        simulate_bench_dry_run=args.simulate_bench_dry_run,
        force_clean_room=True if args.force_clean_room else None,
        fx6_lib_dir=args.fx6_lib_dir,
        fx3_modules_dir=args.fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=args.body_fw,
        sony_help_guide_id=args.sony_help_guide_id,
        reset_action=args.reset_action,
        shoot_mode=args.shoot_mode,
        exposure_mode=args.exposure_mode,
        # Group A
        drive_mode=args.drive_mode,
        cont_speed_tier=args.cont_speed_tier,
        aperture_f_number=args.aperture_f_number,
        still_file_format=args.still_file_format,
        raw_file_type=args.raw_file_type,
        flash_enabled=args.flash_enabled,
        self_timer_sec=args.self_timer_sec,
        self_timer_cont_images=args.self_timer_cont_images,
        hlg_still_image=args.hlg_still_image,
        picture_profile=args.picture_profile,
        log_shooting_mode=args.log_shooting_mode,
        interval_shutter_type=args.interval_shutter_type,
        expect_af_tracks_all_frames_above_f11=args.expect_af_tracks_all_frames_above_f11,
        expect_full_cont_fps_with_uncompressed_raw_or_flash=args.expect_full_cont_fps_with_uncompressed_raw_or_flash,
        claimed_drive_mode_active_in_movie_or_sq=args.claimed_drive_mode_active_in_movie_or_sq,
        claimed_drive_mode_resists_camera_reset=args.claimed_drive_mode_resists_camera_reset,
        claimed_interval_default_mech_shutter=args.claimed_interval_default_mech_shutter,
        fx6_has_still_drive_mode_menu_claimed=args.fx6_has_still_drive_mode_menu_claimed,
        dormant_focus_bracket_requested=args.dormant_focus_bracket_requested,
        fx3_focus_bracket_present_claimed=args.fx3_focus_bracket_present_claimed,
        fx6_focus_bracket_present_claimed=args.fx6_focus_bracket_present_claimed,
        claimed_focus_bracket_in_ilc2210=args.claimed_focus_bracket_in_ilc2210,
        shutter_type=args.shutter_type,
        silent_mode=args.silent_mode,
        dormant_shutter_type_auto_requested=args.dormant_shutter_type_auto_requested,
        fx3_shutter_type_auto_present_claimed=args.fx3_shutter_type_auto_present_claimed,
        flash_sync_denominator=args.flash_sync_denominator,
        claimed_1_320_xsync_supported=args.claimed_1_320_xsync_supported,
        e_front_curtain_shutter=args.e_front_curtain_shutter,
        efcs_active_claimed=args.efcs_active_claimed,
        claimed_efcs_wiped_by_camera_reset=args.claimed_efcs_wiped_by_camera_reset,
        long_exposure_nr=args.long_exposure_nr,
        shutter_seconds=args.shutter_seconds,
        bulb_enabled=args.bulb_enabled,
        anti_flicker_shoot=args.anti_flicker_shoot,
        claimed_long_exp_nr_active_below_1s=args.claimed_long_exp_nr_active_below_1s,
        claimed_long_exp_nr_resists_reset=args.claimed_long_exp_nr_resists_reset,
        high_iso_nr=args.high_iso_nr,
        expect_high_iso_nr_modifies_arw_raw=args.expect_high_iso_nr_modifies_arw_raw,
        dormant_high_iso_nr_high_option_requested=args.dormant_high_iso_nr_high_option_requested,
        claimed_high_iso_nr_resists_reset=args.claimed_high_iso_nr_resists_reset,
        fx6_noise_suppression_uses_still_nr_menu_claimed=args.fx6_noise_suppression_uses_still_nr_menu_claimed,
        # Group B
        creative_look_shoot_mode=args.creative_look_shoot_mode,
        creative_look_slot=args.creative_look_slot,
        creative_look_contrast=args.creative_look_contrast,
        creative_look_highlights=args.creative_look_highlights,
        creative_look_shadows=args.creative_look_shadows,
        creative_look_fade=args.creative_look_fade,
        creative_look_saturation=args.creative_look_saturation,
        creative_look_sharpness=args.creative_look_sharpness,
        creative_look_sharpness_range=args.creative_look_sharpness_range,
        creative_look_clarity=args.creative_look_clarity,
        creative_look_saturation_adjusted=args.creative_look_saturation_adjusted,
        creative_look_sharpness_range_adjusted=args.creative_look_sharpness_range_adjusted,
        expect_creative_look_active_under_pp_log_hlg_iauto=args.expect_creative_look_active_under_pp_log_hlg_iauto,
        claimed_creative_look_fade_sharpness_clarity_accept_negative=args.claimed_creative_look_fade_sharpness_clarity_accept_negative,
        claimed_creative_look_resists_camera_reset=args.claimed_creative_look_resists_camera_reset,
        dormant_soft_skin_requested=args.dormant_soft_skin_requested,
        fx3_soft_skin_present_claimed=args.fx3_soft_skin_present_claimed,
        fx6_soft_skin_present_claimed=args.fx6_soft_skin_present_claimed,
        delete_scope=args.delete_scope,
        delete_confirm=args.delete_confirm,
        delete_pressing_twice=args.delete_pressing_twice,
        protect_scope=args.protect_scope,
        delete_write_requested=args.delete_write_requested,
        delete_write_slot=args.delete_write_slot,
        protect_write_requested=args.protect_write_requested,
        protect_write_slot=args.protect_write_slot,
        protected_item_delete_attempted=args.protected_item_delete_attempted,
        slot_format_executed=args.slot_format_executed,
        claimed_delete_confirm_wiped_by_camera_reset=args.claimed_delete_confirm_wiped_by_camera_reset,
        claimed_delete_twice_wiped_by_camera_reset=args.claimed_delete_twice_wiped_by_camera_reset,
        expect_copy_preserves_protect=args.expect_copy_preserves_protect,
        recover_image_db_requested=args.recover_image_db_requested,
        recover_image_db_slot=args.recover_image_db_slot,
        battery_soc_pct=args.battery_soc_pct,
        low_battery_warning=args.low_battery_warning,
        claimed_recover_db_wiped_by_reset_or_init=args.claimed_recover_db_wiped_by_reset_or_init,
        claimed_display_media_info_mutates_media=args.claimed_display_media_info_mutates_media,
        claimed_display_media_info_cap_not_40000=args.claimed_display_media_info_cap_not_40000,
        slot1_contains_tier0_dump=args.slot1_contains_tier0_dump,
        slot1_data_sector_writes=args.slot1_data_sector_writes,
        # Group C
        auto_pixel_mapping=args.auto_pixel_mapping,
        days_since_pixel_mapping=args.days_since_pixel_mapping,
        manual_pixel_mapping_requested=args.manual_pixel_mapping_requested,
        lens_cap_attached=args.lens_cap_attached,
        expect_manual_pm_without_reboot=args.expect_manual_pm_without_reboot,
        claimed_auto_pm_wiped_by_camera_reset=args.claimed_auto_pm_wiped_by_camera_reset,
        claimed_usb_streaming_blocks_pixel_mapping_prm_haita=args.claimed_usb_streaming_blocks_pixel_mapping_prm_haita,
        tier0_dump_active=args.tier0_dump_active,
        unguarded_pm_calibration=args.unguarded_pm_calibration,
        silent_auto_pixel_mapping=args.silent_auto_pixel_mapping,
        expect_zero_shutter_sound_with_silent_auto_pm_on=args.expect_zero_shutter_sound_with_silent_auto_pm_on,
        claimed_silent_auto_pm_resists_camera_reset=args.claimed_silent_auto_pm_resists_camera_reset,
        fx6_uses_setup_auto_pixel_mapping_instead_of_apr_claimed=args.fx6_uses_setup_auto_pixel_mapping_instead_of_apr_claimed,
        fx6_auto_black_balance_menu_present_claimed=args.fx6_auto_black_balance_menu_present_claimed,
        exposed_monitor_items=exposed_monitor,
        monitor_brightness_mode=args.monitor_brightness_mode,
        monitor_brightness_level=args.monitor_brightness_level,
        display_quality=args.display_quality,
        body_temp_elevated=args.body_temp_elevated,
        expect_high_display_quality_unclamped_under_thermal=args.expect_high_display_quality_unclamped_under_thermal,
        monitor_flip_direction=args.monitor_flip_direction,
        claimed_monitor_3items_wiped_by_camera_reset=args.claimed_monitor_3items_wiped_by_camera_reset,
        claimed_bright_monitoring_in_setup_monitor=args.claimed_bright_monitoring_in_setup_monitor,
        fx3_finder_monitor_menu_present_claimed=args.fx3_finder_monitor_menu_present_claimed,
        fx3_builtin_evf_present_claimed=args.fx3_builtin_evf_present_claimed,
        dormant_evf_menu_requested=args.dormant_evf_menu_requested,
        fx6_vf_adjust_four_subitems_present_claimed=args.fx6_vf_adjust_four_subitems_present_claimed,
        # Group D
        recall_custom_hold_active=args.recall_custom_hold_active,
        recall_custom_hold_slot=args.recall_custom_hold_slot,
        recall_custom_hold_eleven_slots=hold_eleven_slots,
        recall_custom_hold_standalone_wb_requested=args.recall_custom_hold_standalone_wb_requested,
        fx3_recall_custom_hold_standalone_wb_present_claimed=args.fx3_recall_custom_hold_standalone_wb_present_claimed,
        claimed_recall_custom_hold_wiped_by_camera_reset=args.claimed_recall_custom_hold_wiped_by_camera_reset,
        tracking_on_custom_key_focus_mode=args.tracking_on_custom_key_focus_mode,
        tracking_on_custom_key_active=args.tracking_on_custom_key_active,
        fx6_push_af_agc_allowed_in_cine_ei_or_bokeh_claimed=args.fx6_push_af_agc_allowed_in_cine_ei_or_bokeh_claimed,
        hdmi_resolution=args.hdmi_resolution,
        rec_media_dur_hdmi_output=args.rec_media_dur_hdmi_output,
        hdmi_output_resolution=args.hdmi_output_resolution,
        hdmi_4k_output_rate=args.hdmi_4k_output_rate,
        hdmi_raw_output=args.hdmi_raw_output,
        hdmi_tc_output=args.hdmi_tc_output,
        hdmi_rec_control=args.hdmi_rec_control,
        hdmi_4ch_audio_output=args.hdmi_4ch_audio_output,
        hdmi_info_display=args.hdmi_info_display,
        ctrl_for_hdmi=args.ctrl_for_hdmi,
        expect_2400p_no_reboot_or_mixed_playback=args.expect_2400p_no_reboot_or_mixed_playback,
        expect_hdmi_info_display_active_with_raw_or_hdmi_only=args.expect_hdmi_info_display_active_with_raw_or_hdmi_only,
        claimed_external_output_wiped_by_camera_reset=args.claimed_external_output_wiped_by_camera_reset,
        dormant_4k_2k_or_24p_60p_requested=args.dormant_4k_2k_or_24p_60p_requested,
        fx3_4k_2k_output_present_claimed=args.fx3_4k_2k_output_present_claimed,
        fx3_24p_60p_output_present_claimed=args.fx3_24p_60p_output_present_claimed,
        recording_media=args.recording_media,
        rec_target_slot=args.rec_target_slot,
        emmc_write_count=args.emmc_write_count,
        e_nd_actuator_tx_count=args.e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=args.wireless_rf_packets_emitted,
        usb_packets_transmitted=args.usb_packets_transmitted,
        simulated_passive_tx_bytes=args.simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=args.simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=args.claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=args.claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=args.claim_cross_model_flash_authorized,
        receipt_a_path=args.receipt_a,
        receipt_b_path=args.receipt_b,
        body_serial=args.body_serial,
        emmc_cid=args.emmc_cid,
        h0_baselines_a=h0_a,
        h0_baselines_b=h0_b,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_phase338_markdown(rep), encoding="utf-8")
    v_res = verify_phase338_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P338_GO_NO_GO_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_VERIFIED,
    )
    try:
        if args.json and not args.summary:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash={rep.cross_model_flash_authorized} "
                f"focus_bracket={rep.fx3_focus_bracket_present}/{rep.fx6_focus_bracket_present} "
                f"shutter_auto={rep.fx3_shutter_type_auto_present} "
                f"soft_skin={rep.fx3_soft_skin_effect_present}/{rep.fx6_soft_skin_effect_present} "
                f"evf={rep.fx3_builtin_evf_present} "
                f"recall_hold_wb={rep.fx3_recall_custom_hold_standalone_wb_present} "
                f"hdmi_4k2k={rep.fx3_4k_2k_output_present} "
                f"slot1_mutated={rep.slot1_tier0_vault_mutated} "
                f"emmc_write_count={rep.emmc_write_count} "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"rf_pkts={rep.rf_packets_transmitted} "
                f"slot1_writes={rep.slot1_data_sector_writes} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec(
    args: argparse.Namespace,
) -> int:
    from .realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier import (
        P341_AREA_GMT_THIRTY_ZONES,
        P341_GO_NO_GO_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_VERIFIED,
        render_phase341_markdown,
        run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight,
        verify_phase341_report,
    )
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )

    parsed_model_id = int(args.model_id, 0) if args.model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (args.receipt_a is not None or args.receipt_b is not None) and args.body_serial and args.emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=args.body_serial, emmc_cid=args.emmc_cid)
        h0_b = dict(h0_a)

    exposed_zones = (
        tuple(x.strip() for x in args.exposed_area_gmt_zones.split(",") if x.strip())
        if args.exposed_area_gmt_zones is not None
        else P341_AREA_GMT_THIRTY_ZONES
    )

    rep = run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
        simulate_bench_dry_run=args.simulate_bench_dry_run,
        force_clean_room=True if args.force_clean_room else None,
        fx6_lib_dir=args.fx6_lib_dir,
        fx3_modules_dir=args.fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=args.body_fw,
        sony_help_guide_id=args.sony_help_guide_id,
        reset_action=args.reset_action,
        shoot_mode=args.shoot_mode,
        exposure_mode=args.exposure_mode,
        # Group A
        area_zone=args.area_zone,
        exposed_area_gmt_zones=exposed_zones,
        daylight_savings=args.daylight_savings,
        date_format=args.date_format,
        rtc_backup_charge_hours=args.rtc_backup_charge_hours,
        rtc_initialized=args.rtc_initialized,
        claimed_user_replaceable_cr2032_present=args.claimed_user_replaceable_cr2032_present,
        rtc_discharge_without_24h_charge_claimed=args.rtc_discharge_without_24h_charge_claimed,
        claimed_area_date_wiped_by_camera_reset=args.claimed_area_date_wiped_by_camera_reset,
        claimed_fx6_has_standalone_dst_switch=args.claimed_fx6_has_standalone_dst_switch,
        expect_area_date_uses_legacy_name_only=args.expect_area_date_uses_legacy_name_only,
        grid_line_display=args.grid_line_display,
        grid_line_type=args.grid_line_type,
        hdmi_info_display=args.hdmi_info_display,
        hdmi_raw_output=args.hdmi_raw_output,
        rec_media_dur_hdmi_output=args.rec_media_dur_hdmi_output,
        marker_display=args.marker_display,
        center_marker=args.center_marker,
        aspect_marker=args.aspect_marker,
        safety_zone=args.safety_zone,
        guideframe=args.guideframe,
        focus_magnifier_active=args.focus_magnifier_active,
        expect_marker_outputs_over_hdmi=args.expect_marker_outputs_over_hdmi,
        expect_grid_passes_hdmi_when_info_off_or_raw=args.expect_grid_passes_hdmi_when_info_off_or_raw,
        expect_marker_active_in_still_mode=args.expect_marker_active_in_still_mode,
        expect_marker_visible_during_focus_magnifier=args.expect_marker_visible_during_focus_magnifier,
        claimed_grid_or_marker_wiped_by_camera_reset=args.claimed_grid_or_marker_wiped_by_camera_reset,
        claimed_fx6_has_3mode_static_grid_line_menu=args.claimed_fx6_has_3mode_static_grid_line_menu,
        # Group B
        camset_action=args.camset_action,
        camset_slot=args.camset_slot,
        camset_file_index=args.camset_file_index,
        camset_media_type=args.camset_media_type,
        camset_card_template=args.camset_card_template,
        camset_fw_version=args.camset_fw_version,
        claimed_camset_allows_slot2=args.claimed_camset_allows_slot2,
        claimed_camset_uses_pro_camera_path=args.claimed_camset_uses_pro_camera_path,
        claimed_camset_includes_excluded_items=args.claimed_camset_includes_excluded_items,
        claimed_ftpset_shares_camset_dir=args.claimed_ftpset_shares_camset_dir,
        campr_action=args.campr_action,
        campr_slot=args.campr_slot,
        memory_recall_media_slot=args.memory_recall_media_slot,
        claimed_campr_includes_custom_key_or_program_shift=args.claimed_campr_includes_custom_key_or_program_shift,
        ftpset_action=args.ftpset_action,
        ftpset_slot=args.ftpset_slot,
        claimed_fx6_reference_file_present=args.claimed_fx6_reference_file_present,
        slot1_contains_tier0_dump=args.slot1_contains_tier0_dump,
        slot1_data_sector_writes=args.slot1_data_sector_writes,
        pc_sync_terminal_requested=args.pc_sync_terminal_requested,
        claimed_fx3_sync_terminal_present=args.claimed_fx3_sync_terminal_present,
        xlr_h1_attached=args.xlr_h1_attached,
        hvl_lbpc_direct_mount_requested=args.hvl_lbpc_direct_mount_requested,
        video_light_mode=args.video_light_mode,
        mi_shoe_5v_draw_ma=args.mi_shoe_5v_draw_ma,
        flash_mode=args.flash_mode,
        flash_xsync_denominator=args.flash_xsync_denominator,
        flash_trigger_voltage_v=args.flash_trigger_voltage_v,
        claimed_fx6_video_light_has_auto_mode=args.claimed_fx6_video_light_has_auto_mode,
        claimed_fx6_genlock_bnc_present=args.claimed_fx6_genlock_bnc_present,
        fx6_genlock_requested=args.fx6_genlock_requested,
        # Group C
        playback_magnify_requested=args.playback_magnify_requested,
        playback_media_kind=args.playback_media_kind,
        enlarge_initial_mag=args.enlarge_initial_mag,
        enlarge_initial_pos=args.enlarge_initial_pos,
        claimed_playback_magnify_works_on_movies=args.claimed_playback_magnify_works_on_movies,
        claimed_playback_magnify_wiped_by_camera_reset=args.claimed_playback_magnify_wiped_by_camera_reset,
        claimed_fx6_has_playback_enlarge=args.claimed_fx6_has_playback_enlarge,
        anti_flicker_shoot=args.anti_flicker_shoot,
        still_shutter_type=args.still_shutter_type,
        silent_mode=args.silent_mode,
        bulb_enabled=args.bulb_enabled,
        claimed_anti_flicker_effective_on_high_freq_led=args.claimed_anti_flicker_effective_on_high_freq_led,
        claimed_anti_flicker_shoot_resists_camera_reset=args.claimed_anti_flicker_shoot_resists_camera_reset,
        dormant_var_shutter_requested=args.dormant_var_shutter_requested,
        dormant_anti_flicker_set_requested=args.dormant_anti_flicker_set_requested,
        dormant_anti_flicker_tv_scan_requested=args.dormant_anti_flicker_tv_scan_requested,
        claimed_fx3_var_shutter_present=args.claimed_fx3_var_shutter_present,
        claimed_fx3_anti_flicker_tv_scan_present=args.claimed_fx3_anti_flicker_tv_scan_present,
        claimed_fx3_anti_flicker_set_present=args.claimed_fx3_anti_flicker_set_present,
        fx6_ecs_enabled=args.fx6_ecs_enabled,
        fx6_ecs_freq_hz=args.fx6_ecs_freq_hz,
        claimed_fx6_lacks_ecs=args.claimed_fx6_lacks_ecs,
        # Group D
        wifi_sku=args.wifi_sku,
        wifi_connect=args.wifi_connect,
        wifi_frequency_band=args.wifi_frequency_band,
        wifi_security_protocol=args.wifi_security_protocol,
        access_point_set_requested=args.access_point_set_requested,
        claimed_ww558244_supports_5ghz=args.claimed_ww558244_supports_5ghz,
        claimed_ver700_supports_wep_wpa_ipsec=args.claimed_ver700_supports_wep_wpa_ipsec,
        claimed_reset_network_wipes_airplane_mode=args.claimed_reset_network_wipes_airplane_mode,
        claimed_camera_reset_wipes_network=args.claimed_camera_reset_wipes_network,
        claimed_fx6_uses_single_wifi_sku=args.claimed_fx6_uses_single_wifi_sku,
        airplane_mode=args.airplane_mode,
        rf_nvs_p12_p13_readonly=args.rf_nvs_p12_p13_readonly,
        rf_nvs_mutation_bytes=args.rf_nvs_mutation_bytes,
        claim_rf_nvs_write_authorized=args.claim_rf_nvs_write_authorized,
        camera_revision=args.camera_revision,
        ir_remote_ctrl=args.ir_remote_ctrl,
        ir_sensor_front_index=args.ir_sensor_front_index,
        bluetooth_rmt_ctrl=args.bluetooth_rmt_ctrl,
        expect_power_save_sleeps_during_ir=args.expect_power_save_sleeps_during_ir,
        claimed_ir_sensor_is_front_8=args.claimed_ir_sensor_is_front_8,
        claimed_fx3a_keeps_ir_sensor=args.claimed_fx3a_keeps_ir_sensor,
        claimed_fx3_has_2_5mm_lanc=args.claimed_fx3_has_2_5mm_lanc,
        ctrl_for_hdmi=args.ctrl_for_hdmi,
        hdmi_bench_attached=args.hdmi_bench_attached,
        claimed_ctrl_for_hdmi_factory_default_is_off=args.claimed_ctrl_for_hdmi_factory_default_is_off,
        claimed_ir_or_cec_wiped_by_camera_reset=args.claimed_ir_or_cec_wiped_by_camera_reset,
        claimed_cec_has_rec_key=args.claimed_cec_has_rec_key,
        emmc_write_count=args.emmc_write_count,
        e_nd_actuator_tx_count=args.e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=args.wireless_rf_packets_emitted,
        usb_packets_transmitted=args.usb_packets_transmitted,
        simulated_passive_tx_bytes=args.simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=args.simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=args.claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=args.claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=args.claim_cross_model_flash_authorized,
        receipt_a_path=args.receipt_a,
        receipt_b_path=args.receipt_b,
        body_serial=args.body_serial,
        emmc_cid=args.emmc_cid,
        h0_baselines_a=h0_a,
        h0_baselines_b=h0_b,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_phase341_markdown(rep), encoding="utf-8")
    v_res = verify_phase341_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P341_GO_NO_GO_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_VERIFIED,
    )
    try:
        if args.json and not args.summary:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash={rep.cross_model_flash_authorized} "
                f"sync_term={rep.fx3_sync_terminal_present} "
                f"fx6_genlock={rep.fx6_genlock_bnc_present} "
                f"var_shutter={rep.fx3_var_shutter_present} "
                f"lanc={rep.fx3_2_5mm_lanc_present} "
                f"marker_hdmi={rep.fx3_marker_outputs_to_hdmi} "
                f"slot1_mutated={rep.slot1_tier0_vault_mutated} "
                f"emmc_write_count={rep.emmc_write_count} "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"rf_pkts={rep.rf_packets_transmitted} "
                f"rf_nvs_mut={rep.rf_nvs_mutation_bytes} "
                f"slot1_writes={rep.slot1_data_sector_writes} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def _cmd_preflight_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether(
    args: argparse.Namespace,
) -> int:
    from .realhw_card_insert_readiness_verifier import (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        TARGET_MODEL_ID_INT,
        build_default_h0_baselines,
    )
    from .realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier import (
        P342_AUDIO_RECORDING_EXACT_FIVE_ITEMS,
        P342_FOCUS_ASSISTANT_EXACT_FIVE_ITEMS,
        P342_GO_NO_GO_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_VERIFIED,
        render_phase342_markdown,
        run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight,
        verify_phase342_report,
    )

    parsed_model_id = int(args.model_id, 0) if args.model_id else TARGET_MODEL_ID_INT
    h0_a = None
    h0_b = None
    if (args.receipt_a is not None or args.receipt_b is not None) and args.body_serial and args.emmc_cid:
        h0_a = build_default_h0_baselines(body_serial=args.body_serial, emmc_cid=args.emmc_cid)
        h0_b = dict(h0_a)

    exposed_audio_items = (
        tuple(x.strip() for x in args.exposed_audio_recording_items.split(",") if x.strip())
        if args.exposed_audio_recording_items is not None
        else P342_AUDIO_RECORDING_EXACT_FIVE_ITEMS
    )
    exposed_focus_items = (
        tuple(x.strip() for x in args.exposed_focus_assistant_items.split(",") if x.strip())
        if args.exposed_focus_assistant_items is not None
        else P342_FOCUS_ASSISTANT_EXACT_FIVE_ITEMS
    )

    rep = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
        simulate_bench_dry_run=args.simulate_bench_dry_run,
        force_clean_room=True if args.force_clean_room else None,
        fx6_lib_dir=args.fx6_lib_dir,
        fx3_modules_dir=args.fx3_modules_dir,
        body_model_id=parsed_model_id,
        body_fw=args.body_fw,
        sony_help_guide_id=args.sony_help_guide_id,
        reset_action=args.reset_action,
        shoot_mode=args.shoot_mode,
        focus_mode=args.focus_mode,
        log_shooting_mode=args.log_shooting_mode,
        # Group A
        peaking_display=args.peaking_display,
        peaking_level=args.peaking_level,
        peaking_color=args.peaking_color,
        hdmi_info_display=args.hdmi_info_display,
        hdmi_raw_output=args.hdmi_raw_output,
        focus_magnifier_active=args.focus_magnifier_active,
        expect_peaking_outputs_over_hdmi=args.expect_peaking_outputs_over_hdmi,
        claimed_peaking_blocks_focus_magnifier=args.claimed_peaking_blocks_focus_magnifier,
        claimed_peaking_disabled_in_movie_af=args.claimed_peaking_disabled_in_movie_af,
        claimed_peaking_wiped_by_camera_reset=args.claimed_peaking_wiped_by_camera_reset,
        in_body_focus_map_requested=args.in_body_focus_map_requested,
        claimed_fx3_has_in_body_focus_map=args.claimed_fx3_has_in_body_focus_map,
        claimed_mc_focus_map_works_over_usb=args.claimed_mc_focus_map_works_over_usb,
        fx6_peaking_type_or_freq_requested=args.fx6_peaking_type_or_freq_requested,
        claimed_fx6_has_peaking_type_or_freq=args.claimed_fx6_has_peaking_type_or_freq,
        claimed_fx6_peaking_has_white_not_bw=args.claimed_fx6_peaking_has_white_not_bw,
        exposed_audio_recording_items=exposed_audio_items,
        audio_recording=args.audio_recording,
        audio_rec_level=args.audio_rec_level,
        audio_out_timing=args.audio_out_timing,
        wind_noise_reduct=args.wind_noise_reduct,
        shoe_audio_set=args.shoe_audio_set,
        mic_35mm_inserted=args.mic_35mm_inserted,
        xlr_h1_attached=args.xlr_h1_attached,
        xlr_h1_handle_audio=args.xlr_h1_handle_audio,
        mi_shoe_mic_attached=args.mi_shoe_mic_attached,
        dormant_audio_level_display_requested=args.dormant_audio_level_display_requested,
        claimed_fx3_has_audio_level_display_menu=args.claimed_fx3_has_audio_level_display_menu,
        claimed_audio_recording_resists_camera_reset=args.claimed_audio_recording_resists_camera_reset,
        claimed_audio_out_timing_under_setup_sound_option=args.claimed_audio_out_timing_under_setup_sound_option,
        fx3_disable_builtin_limiter_requested=args.fx3_disable_builtin_limiter_requested,
        dormant_wind_noise_auto_requested=args.dormant_wind_noise_auto_requested,
        claimed_fx3_wind_noise_has_auto=args.claimed_fx3_wind_noise_has_auto,
        expect_wind_noise_applies_to_external_mic=args.expect_wind_noise_applies_to_external_mic,
        expect_wind_noise_active_in_sq=args.expect_wind_noise_active_in_sq,
        claimed_fx6_handle_has_physical_low_cut_switch=args.claimed_fx6_handle_has_physical_low_cut_switch,
        claimed_fx3_has_fx6_6step_limiter=args.claimed_fx3_has_fx6_6step_limiter,
        # Group B
        usb_power_supply=args.usb_power_supply,
        usb_power_terminal=args.usb_power_terminal,
        camera_power_state=args.camera_power_state,
        usb_pd_supply_active=args.usb_pd_supply_active,
        usb_pd_watts=args.usb_pd_watts,
        usb_c_cable_amps=args.usb_c_cable_amps,
        np_fz100_inserted=args.np_fz100_inserted,
        battery_soc_pct=args.battery_soc_pct,
        dc_c1_coupler_attached=args.dc_c1_coupler_attached,
        charge_led_active_while_on=args.charge_led_active_while_on,
        expect_battery_charges_while_camera_on=args.expect_battery_charges_while_camera_on,
        claimed_multi_micro_usb_powers_camera=args.claimed_multi_micro_usb_powers_camera,
        claimed_fx3_supports_batteryless_usb_pd_boot=args.claimed_fx3_supports_batteryless_usb_pd_boot,
        claimed_np_fz100_hot_swap_under_usb_pd=args.claimed_np_fz100_hot_swap_under_usb_pd,
        claimed_usb_power_supply_wiped_by_camera_reset=args.claimed_usb_power_supply_wiped_by_camera_reset,
        fx6_dc_in_volts=args.fx6_dc_in_volts,
        fx6_dc_in_hot_replug_during_rec=args.fx6_dc_in_hot_replug_during_rec,
        claimed_fx6_usb_c_powers_body=args.claimed_fx6_usb_c_powers_body,
        claimed_fx6_lacks_batteryless_dc_in_boot=args.claimed_fx6_lacks_batteryless_dc_in_boot,
        ntsc_pal_sku=args.ntsc_pal_sku,
        video_system=args.video_system,
        ntsc_pal_switch_requested=args.ntsc_pal_switch_requested,
        ntsc_pal_reboot_acknowledged=args.ntsc_pal_reboot_acknowledged,
        ntsc_pal_avf_info_write_requested=args.ntsc_pal_avf_info_write_requested,
        ntsc_pal_avf_target_slot=args.ntsc_pal_avf_target_slot,
        slot1_format_requested=args.slot1_format_requested,
        slot1_contains_tier0_dump=args.slot1_contains_tier0_dump,
        slot1_data_sector_writes=args.slot1_data_sector_writes,
        claimed_j1_supports_pal_selector=args.claimed_j1_supports_pal_selector,
        expect_non_default_system_lacks_banner=args.expect_non_default_system_lacks_banner,
        claimed_xavc_requires_mandatory_card_format=args.claimed_xavc_requires_mandatory_card_format,
        expect_cross_system_playback_allowed=args.expect_cross_system_playback_allowed,
        claimed_ntsc_pal_wiped_by_camera_reset=args.claimed_ntsc_pal_wiped_by_camera_reset,
        claimed_fx6_shows_running_on_ntsc_pal_banner=args.claimed_fx6_shows_running_on_ntsc_pal_banner,
        claimed_fx6_thumbnail_shows_all_freq_simultaneously=args.claimed_fx6_thumbnail_shows_all_freq_simultaneously,
        # Group C
        apsc_s35_shooting=args.apsc_s35_shooting,
        dormant_anti_dust_function_requested=args.dormant_anti_dust_function_requested,
        dormant_shutter_when_pwr_off_requested=args.dormant_shutter_when_pwr_off_requested,
        claimed_fx3_shutter_when_pwr_off_present=args.claimed_fx3_shutter_when_pwr_off_present,
        claimed_fx3_shutter_closes_on_power_off=args.claimed_fx3_shutter_closes_on_power_off,
        sensor_cleaning_requested=args.sensor_cleaning_requested,
        sensor_cleaning_power_off_completed=args.sensor_cleaning_power_off_completed,
        claimed_fx6_has_shutter_when_pwr_off_or_ibis_cleaning=args.claimed_fx6_has_shutter_when_pwr_off_or_ibis_cleaning,
        claimed_fx3_has_e_nd_or_apr=args.claimed_fx3_has_e_nd_or_apr,
        exposed_focus_assistant_items=exposed_focus_items,
        focus_magnif_time=args.focus_magnif_time,
        initial_focus_mag_x=args.initial_focus_mag_x,
        requested_focus_mag_x=args.requested_focus_mag_x,
        af_in_focus_mag=args.af_in_focus_mag,
        auto_magnifier_in_mf=args.auto_magnifier_in_mf,
        dormant_high_mp_focus_mag_scale_requested=args.dormant_high_mp_focus_mag_scale_requested,
        expect_af_in_focus_mag_or_auto_mag_in_movie=args.expect_af_in_focus_mag_or_auto_mag_in_movie,
        claimed_movie_rec_cancels_focus_mag=args.claimed_movie_rec_cancels_focus_mag,
        expect_focus_mag_crops_hdmi_or_internal_rec=args.expect_focus_mag_crops_hdmi_or_internal_rec,
        claimed_focus_assistant_wiped_by_camera_reset=args.claimed_focus_assistant_wiped_by_camera_reset,
        claimed_fx6_hdmi_focus_mag_is_3x_6x=args.claimed_fx6_hdmi_focus_mag_is_3x_6x,
        claimed_fx6_vf_focus_mag_is_2_1x_4_1x=args.claimed_fx6_vf_focus_mag_is_2_1x_4_1x,
        # Group D
        exp_std_adjust_metering_mode=args.exp_std_adjust_metering_mode,
        exp_std_adjust_sixths=args.exp_std_adjust_sixths,
        exp_std_nonzero_acknowledged=args.exp_std_nonzero_acknowledged,
        dormant_1_8_ev_step_requested=args.dormant_1_8_ev_step_requested,
        expect_exp_std_adjust_modifies_exif_bias=args.expect_exp_std_adjust_modifies_exif_bias,
        expect_exp_std_changes_cine_ei_iso=args.expect_exp_std_changes_cine_ei_iso,
        claimed_exp_std_adjust_wiped_by_camera_reset=args.claimed_exp_std_adjust_wiped_by_camera_reset,
        claimed_exp_std_adjust_resets_exposure_comp=args.claimed_exp_std_adjust_resets_exposure_comp,
        fx6_ae_level_ev=args.fx6_ae_level_ev,
        claimed_fx6_ae_level_limited_to_2ev=args.claimed_fx6_ae_level_limited_to_2ev,
        usb_connection_mode=args.usb_connection_mode,
        usb_lun_setting=args.usb_lun_setting,
        usb_lan_tethering=args.usb_lan_tethering,
        usb_lan_cnct_launch=args.usb_lan_cnct_launch,
        usb_lan_service=args.usb_lan_service,
        airplane_mode=args.airplane_mode,
        dual_usb_typec_and_multi_simultaneous=args.dual_usb_typec_and_multi_simultaneous,
        slot1_host_usb_write_requested=args.slot1_host_usb_write_requested,
        claimed_airplane_mode_blocks_usb_lan=args.claimed_airplane_mode_blocks_usb_lan,
        claimed_creators_app_allows_guided_live_over_usb=args.claimed_creators_app_allows_guided_live_over_usb,
        claimed_usb_streaming_uvc_active_on_fx3=args.claimed_usb_streaming_uvc_active_on_fx3,
        claimed_reset_network_preserves_airplane_mode=args.claimed_reset_network_preserves_airplane_mode,
        claimed_camera_reset_wipes_usb_tethering=args.claimed_camera_reset_wipes_usb_tethering,
        claimed_fx3_links_cusbgadgetiap=args.claimed_fx3_links_cusbgadgetiap,
        claimed_fx6_lacks_cusbgadgetiap=args.claimed_fx6_lacks_cusbgadgetiap,
        emmc_write_count=args.emmc_write_count,
        e_nd_actuator_tx_count=args.e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=args.wireless_rf_packets_emitted,
        usb_packets_transmitted=args.usb_packets_transmitted,
        simulated_passive_tx_bytes=args.simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=args.simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=args.claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=args.claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=args.claim_cross_model_flash_authorized,
        receipt_a_path=args.receipt_a,
        receipt_b_path=args.receipt_b,
        body_serial=args.body_serial,
        emmc_cid=args.emmc_cid,
        h0_baselines_a=h0_a,
        h0_baselines_b=h0_b,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_phase342_markdown(rep), encoding="utf-8")
    v_res = verify_phase342_report(rep.to_dict())
    ok = v_res.valid and rep.go_no_go in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P342_GO_NO_GO_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_VERIFIED,
    )
    try:
        if args.json and not args.summary:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"OVERALL={rep.overall_status} "
                f"go_no_go={rep.go_no_go} "
                f"mode={rep.verification_mode} "
                f"simulate_dry_run={rep.simulate_bench_dry_run} "
                f"check_groups={rep.check_groups_passed}/{rep.check_group_count} "
                f"tier0={rep.tier0_receipt_verified} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/{rep.h0_h3_surface_count} "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash={rep.cross_model_flash_authorized} "
                f"peaking_hdmi={rep.fx3_peaking_outputs_to_hdmi} "
                f"wind_auto={rep.fx3_wind_noise_auto_present} "
                f"shutter_pwroff={rep.fx3_shutter_when_pwr_off_present} "
                f"focus_mag_hdmi={rep.fx3_focus_mag_outputs_to_hdmi} "
                f"slot1_mutated={rep.slot1_tier0_vault_mutated} "
                f"emmc_write_count={rep.emmc_write_count} "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"rf_pkts={rep.rf_packets_transmitted} "
                f"slot1_writes={rep.slot1_data_sector_writes} "
                f"usb_pkts={rep.usb_packets_transmitted} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"leaked_bytes={rep.raw_firmware_bytes_leaked} "
                f"report_sha256={rep.report_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 2


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fx6_closure",
        description="FX6-on-FX3 Phase 324/295/264/254/233/221/209/193/175/147 Real-Hardware Master Gates, Phase 342/341/338/334/329/321/316/307/302/291/284/279/275/261/248/227/216/204/186/154 Bench & Pre-Shoot Readiness Verifiers, Phase 130/110/90 Milestone Master Gates, U1-U6 Blueprint Closure, p1 Recovery Bridge, Atomic Stage-A/B Boot Orchestrator, Stage-A Kmod/Dev/ELF64 ABI Closure, Peripheral UX/Audio Closure, AP<->Stock-CP Imaging/IBIS Closure, Unified Stage-B Candidate Integrator, Post-Trial Forensic Auditor, Stage-B R0..R6 Rehearsal, Unified Stage-B Release Dossier v3 & Capstone 22-Gate Verifier CLI",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    for cmd_name, help_msg in (
        ("verify-donors", "Verify ELF64 offsets, context, adaptation, 100%% SHA-256 rollback, and P7 kernel signatures"),
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
        ("verify-milestone-130", "Verify Phase 130 6-Pillar Master Gate (40-Gate + >=13 Recovery + >=24 Auditors + >=21 VM + R14/17/19/R20..24 UI Closures, stage_b_milestone130_master_gate_v1)"),
        ("verify-realhw-jiritsu-tier0", "Verify Phase 136 Stage-288 libJiritsu.so SET_FILE2 P0 hardening, U4/U5/U6 disassembly closures & Tier-0 cold-backup stop-gate"),
        ("verify-sd-stageb-bundle-uninstaller", "Verify Phase 143 BYOF SD-Card Stage-B bundle builder, im.elf escape-hatch launcher & H0==H3 16-surface atomic uninstaller"),
        ("verify-milestone-147", "Verify Milestone Phase 147 6-Pillar Real-Hardware Bench Readiness Master Gate (44-Gate + >=17 Recovery + >=28 Auditors + >=24 VM + Ph136/143 U4/U5/U6/H0==H3 + FX3 7.02 QEMU R28/R29, realhw_milestone147_master_gate_v1)"),
        ("preflight-realhw-bench", "Run Phase 154 100%% passive zero-USB-packet physical bench preflight, ioreg USB mode classifier, SD staging verifier & dual-copy FX3RCPT1 Go/No-Go receipt generator"),
        ("verify-milestone-175", "Verify Milestone Phase 175 Grand Unified 6-Pillar Real-Hardware Final Pre-Bench Master Gate (58-Gate + >=22 Recovery + >=36 Auditors + >=30 VM + Ph136/143/154 + FX3 7.02 QEMU R28..R34, realhw_milestone175_master_gate_v1)"),
        ("preflight-card-insert", "Run Phase 186 host-side final card-insert preflight (Slot-1/2 ExFAT geometry & hygiene, dual-media FX3RCPT1 binding, NP-FZ100/thermal/cable interlock, and EH1..EH3 + H0..H3 dry-run)"),
        ("verify-milestone-193", "Verify Grand Milestone Phase 193 Unified 6-Pillar Real-Hardware ILME-FX3 Ver. 7.02 Pre-Bench Master Gate (66-Gate + >=26 Recovery + >=40 Auditors + >=33 VM + Ph136/143/154/186 + FX3 7.02 QEMU R28..R37, realhw_milestone193_master_gate_v1)"),
        ("preflight-bench-cable-fan-slot1", "Run Phase 204 real-hardware operator pre-bench power/cable (DC-C1 / NP-FZ100 / VMC-BNCM1), 4-mode fan thermal (Always Off block) & Slot-1 CAMSET/.cube vault readiness verifier"),
        ("verify-milestone-209", "Verify Grand Milestone Phase 209 Unified 6-Pillar Real-Hardware ILME-FX3 Ver. 7.02 Pre-Bench Master Gate (>=72-Gate + >=28 Recovery + >=42 Auditors + >=36 VM + preflight-card-insert/preflight-bench-cable-fan-slot1 + FX3 7.02 QEMU R28..R40, realhw_milestone209_master_gate_v1)"),
        ("preflight-hdmi-proxy-desqueeze-and-simult", "Run Phase 216 real-hardware pre-shoot bench & media readiness verifier (De-Squeeze 1.6x=1.65x & M&C Focus Map <150fps, HDMI Log 1080p vs Off(HDMI Only) 4K & Blank LCD, Dual-Slot Simult + Px Proxy Coupled Vault, File Settings/SDHC/ShotMark/TC Slot-1, and Coupled REC Lamp/Shockless WB/Tier-0 gate)"),
        ("verify-milestone-221", "Verify Grand Milestone Phase 221 6-Pillar Real-Hardware ILME-FX3 Ver. 7.02 Master Gate (>=78-Gate + >=31 Recovery + >=44 Auditors + >=38 VM + Triple Bench Preflights Ph186/Ph204/Ph216 + FX3 7.02 QEMU R28..R42, realhw_milestone221_master_gate_v1)"),
        ("preflight-pixelmap-ntscpal-powersave-and-autotemp", "Run Phase 227 physical bench & pre-shoot media readiness verifier (Pixel Mapping cnflasha O_RDONLY/reboot & NTSC/PAL reset persistence + Gamma Assist vs Display LUT, File Settings 37-char/SDHC/ShotMark MP4-only/TC Regenerate Slot-1 & Coupled Body+XLR-H1 REC Lamp, and Power Save 9-condition bypass/Auto Power OFF Temp. tripod/SteadyShot Active & CIZ locks)"),
        ("verify-milestone-233", "Verify Grand Milestone Phase 233 6-Pillar Real-Hardware ILME-FX3 Ver. 7.02 Master Gate (>=90-Gate + >=38 Recovery + >=45 Auditors + >=44 VM + Quad Bench Preflights Ph186/Ph204/Ph216/Ph227 + FX3 7.02 QEMU R28..R47+, realhw_milestone233_master_gate_v1)"),
        ("preflight-imagedb-touch-shoeaudio-and-lockop", "Run Phase 248 5th physical bench & pre-shoot media/audio/vault readiness verifier (Recover Image DB battery & Slot-1 Tier-0 vault guard + Monitor Flip playback non-inversion, Touch Operation 4-item guard & Off(HDMI Only)/RAW clean-feed + indoor Sunny Weather/Display Quality=Standard conservation, Shoe Audio 48kHz/24bit 4ch 3-lockout + Wind Noise Reduct. built-in-only + Save/Load C3 exclusions & Slot-1 firewall, and Lock Operation Parts MENU+Fn 5s chord + USB Power NP-FZ100 + Exposure step vs Shutter Angle)"),
        ("verify-milestone-254", "Verify Grand Milestone Phase 254 6-Pillar Real-Hardware ILME-FX3 Ver. 7.02 Master Gate (>=96-Gate + >=41 Recovery + >=45 Auditors + >=47 VM + Quintuple Bench Preflights Ph186/Ph204/Ph216/Ph227/Ph248 + FX3 7.02 QEMU R28..R50+, realhw_milestone254_master_gate_v1)"),
        ("preflight-diffset-customkey-autoslow-and-apsc", "Run Phase 261 6th physical bench & pre-shoot readiness verifier (Waves 40-43 ilc/2210: Different Set 8-item transitions & Shutter Angle override + Custom Key 3-domain ISO/EI Slot-1 O_RDONLY firewall & EVF-less FX3, Auto Slow Shutter 6-lockout & HDMI REC Control <- TC Output + Breathing Comp., APS-C S35 12.1MP 4K/RAW lockout + Face/Eye AF clean-HDMI & Version read-only, and Release w/o Card/Lens zero-E-ND + v7.02 Audio 5-item DISP meter + Copyright 46-char PII hygiene)"),
        ("verify-milestone-264", "Verify Grand Milestone Phase 264 6-Pillar Real-Hardware ILME-FX3 Ver. 7.02 Master Gate (>=102-Gate + >=44 Recovery + >=45 Auditors + >=50 VM + Sextuple Bench Preflights Ph186/Ph204/Ph216/Ph227/Ph248/Ph261 + FX3 7.02 QEMU R28..R52+, realhw_milestone264_master_gate_v1)"),
        ("preflight-file-settings-gamma-assist-focus-mag-and-videolight", "Run Phase 275 7th physical bench readiness verifier (Waves 44-46 ilc/2210: Movie CamID+Reel# 37-char & Still 3-char DSC prefix / Auto Review Off / 6-item TC/UB persistence, Gamma Display Assist Log lockout & LCD-only clean-HDMI vs Display LUT + Select LUT User1..16, 4.0x Auto Magnifier in MF / Peaking / AF Illuminator / Zero-RF Area/Date/Time / MI-Shoe 5V <= 900mA Video Light / Log 1080p HDMI Resolution, and 2-item Power Setting Option vs appFw Power Save by Monitor 4-mode split / BK_LANG 0x02cf019c 34 vs 29 / Volume 0..15 & 5-route 4ch Monitoring / Delete confirm. Cancel-first + Slot-1 vault guard)"),
        ("preflight-usb-mode-hdmi-info-protect-and-network-reset", "Run Phase 279 8th physical bench readiness verifier (Wave 47 ilc/2210: 4-mode [USB Connection Mode] vs dormant NOUVC usb_f_uvc.ko & data-isolated Type-C USB PD + NP-FZ100 + LUN Multi/Single, [HDMI Info. Display] LCD-blanking/touch-focus lockout vs clean-feed & internal Log/PPLUT 1080p clamp vs Off(HDMI Only)/RAW 4K forced-Off, [Protect] 4 scopes vs [Format] 0xe449 M1..M4 override + dual-layer Slot-1 WP + format hard-lock, and [Reset Network Set.] auto-reboot 0x65d3 3-way reset boundary + post-reboot [Airplane Mode]=On zero-RF & 16/16 H0==H3 Tier-0 gate)"),
        ("preflight-pp-scinetone-wb-metering-and-shutter-type", "Run Phase 284 9th physical bench readiness verifier (Waves 48-49 ilc/2210: Stock PP11 S-Cinetone & [Different Set] vs Creative Look/DRO/Log lockout + PPLUT1..4 1080p clamp + PP1..11 reset trap, WB Cine EI restrictions + Custom 1..3 reset survival / CAMSET exclusion + 6-mode Metering M.M. & Face Priority/De-Squeeze, 2-option Still RAW vs dormant Lossless Comp 0x6b56 + HLG Still HEIF P/A/S/M + DCF 2.0 AdobeRGB _DSC, and 2-option Shutter Type no-Auto + 1/250 s flash sync + Electronic 5-lockout + Hi+ 10fps / >F11 AF-lock + Tier-0 gate)"),
        ("preflight-focus-area-zoom-dci4k-and-sensor-cleaning", "Run Phase 291 10th physical bench readiness verifier (Waves 50-52 ilc/2210: Still-only 7 Tracking Focus Areas & AF Area Registration vs handle-less XLR-H1 + body W/T zoom 1..8 + ISO Range Limit/Still P/A ISO AUTO Min. SS vs Cine EI + Flash Mech-Still gate, XAVC S-I DCI 4K 4096x2160 + 24.00p reboot quarantine + 4-mode Aspect Ratio + 11 Hold checkboxes + SONY/SETTING/FX3 path + Photo Capture DCI 4K/Slot-1 firewall, Sensor Cleaning >=51%% & mandatory OFF vs FX6 e-ND + EV Comp. Cine EI lockout + Focus Mode 5-vs-2 + 9/25 Image Index & Slot-1 Rotate firewall, and Tier-0 16/16 H0==H3 redlines)"),
        ("preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence", "Run Phase 302 11th physical bench readiness verifier (Waves 53-55 ilc/2210: 2-option Shading Auto/Off vs dormant 0x6c9c Auto:Low EOPNOTSUPP=95 + built-in FX3 AF illuminator LED #8 vs FX6 absence + 5 Initialize-only AF params + Slot-1 Folder/Rating EROFS=30 firewall, Switch V/H AF Area Still AF-C + 14-item Focus Area Limit + 5-mode Exposure Std. Adjust + TC Format NDF/PAL + CRITICAL Playback [Copy] Slot 2->1 Tier-0 reverse-write EROFS=30 firewall, 3-mode Touch Func. in Shooting + 4-mode Monitor DISP & CRITICAL Zero-EVF Black-Screen Lockout Firewall + Still AEL/Wireless Flash + Interval Play Speed 1..9 & dormant Edit trap rejection, and 16/16 H0==H3 Tier-0 gate)"),
        ("preflight-dial-customize-lut-embed-steadyshot-and-streaming", "Run Phase 307 12th physical bench readiness verifier (Waves 56-57 ilc/2210: 5-item [Dial Customize] & 3-dial truth vs dormant Rear Dial L/R 0x6a5c/0x680d + My Dial Lock override + 12+12 Fn Menu split, 3-item [Live View Display Set.] & clean-HDMI [Grid Line], O_RDONLY [Manage User LUTs] vs [Embed LUT File] SDHC lock 0x61a0 vs PPLUT1..4 + Slot-1 EROFS=30 firewall, 4-lock Movie [SteadyShot]=Active vs dormant Dynamic active 0x741c + 47-entry Focal Length & IBIS-less FX6 split, dormant Movie Self-timer 0x7192 rejection + LED #8/Audio signals, Custom 1/2 Zebra 0..109%% +-1..10%% + 4-color Peaking, and CRITICAL Zero-RF [Airplane Mode]=On + Slot-1 [Network Streaming]/[FTP] EROFS=30 firewall + 16/16 H0==H3 Tier-0 gate)"),
        ("preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth", "Run Phase 316 13th physical bench readiness verifier (Waves 58-59 ilc/2210: Custom-key-only [Bright Monitoring] 0x701f Setting Effect OFF & Focus Magnifier + [Monitor Brightness] Manual/Sunny Weather vs dormant AUTO/BRIGHT/NORMAL & FX6 VF/Backlight + zero in-camera Divide/Extract & Shot Mark/Clip Flag/Photo Capture/Divider Slot-1 EROFS=30 + Mech-Still BULB/DRO vs dormant Bulb Timer 0x630f/Auto HDR 0xe49d, Zero-BT Timecode Link vs wired VMC-BNCM1 EXT-LK + dual-SKU Wi-Fi WPA2/WPA3 & USB-LAN CDC-NCM + Zero-RF Airplane Mode, BIG6 HOME Fixed/Var Manual ND zero e-ND + manual Framing vs dormant Auto Framing + 9,999-shot Still Interval Slot-1 Vault, and TC Regenerate Rec Run + HDMI REC Control/4ch Audio + SSH Access Authen. vs zero HTTPS auth + zero Fan Control=Max thermal myth-bust & 16/16 H0==H3 Tier-0 gate)"),
        ("preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes", "Run Phase 321 14th physical bench readiness verifier (Waves 60-61 ilc/2210: Dormant Prioritize Rec. Media 0x719e + Slot-2->Slot-1 Overflow Trap Dual Lock [Recording Media]=Slot 2 & [Auto Switch Media]=Off + VPG200/VPG400 0xe224 card-speed gates + [Proxy Settings] >=100p cutoff / DCI 4K<=59.94p allowed / M4ROOT/SUB/*S03.MP4 Slot-1 EROFS=30, [Cloud Connection *] Reset/Init persistence & FTP mutual exclusion + Zero-RF [Cnct. while Power OFF]=Off 0x6ab3 BLE guard + exact 6x7=42 [My Menu] slots vs FX6 20-item PIN User Menu, Passive-only FTP/FTPES 0x6553 Server 1..9 Zero SFTP/JPEG Size + Slot-1 AVF_INFO/cacert.pem EROFS=30 + CRITICAL USB-LAN Airplane-Mode Bypass Firewall + WB 2500..9900K/Cine EI/Custom 1..3 CAMSET exclusion, and Both FX3/FX6 1..7 AF Transition & 1..5 AF Subj. Shift Sens. + Zero in-body Focus Map / external M&C <150fps + 16-state Aspect Marker & 4-color Peaking + 16/16 H0==H3 Tier-0 gate)"),
        ("preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter", "Run Phase 329 15th physical bench readiness verifier (Waves 62-63 ilc/2210: [Audio Out Timing] Live/Lip Sync & removed 0x7a36 [Audio Level Display] + [Shoe Audio Set.] 48kHz/24bit 4ch vs Proxy AAC-LC 2ch & >=100p cutoff + [Face/Eye Subject] ONLY Human/Animal + Wave-42 Bird errata + 8-face [Face Memory], [Silent Mode Settings] 5-lockout + 2-item [Target Function Settings] + dormant 0x709f [Shutter When Pwr OFF] + Zero-RF [Version] + HARD NO-GO BODYDATA.DAT flash firewall, 8-item [HDMI Output Settings] 16-bit 4264x2408 RAW co-rec Slot-1 EROFS=30 & removed 0x6bdc [Color Gamut for RAW] + Ver.7.00+ [De-Squeeze Display] 1.3x/1.5x/1.6x[1.65x]/2.0x w/ zero 1.8x & 4 lockouts + 6 auto-bypasses, and 3-lamp [REC Lamp] + dormant 0x6831 [Var. Shutter] vs FX6 ECS + Wave-42 Reset Errata on Initialize-only [APS-C S35 Shooting] 4K lockout & M:5.1M + 16/16 H0==H3 Tier-0 gate)"),
        ("preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun", "Run Phase 334 16th physical bench readiness verifier (Waves 64-65 ilc/2210: Resettable [Breathing Comp.] 120p/100p lockout & Catalyst Prepare/Plugin + Auto Distortion Comp vs FX6 S&Q/RAW lock + Movie [File Settings] Cam ID+Reel# 37-char & SDHC 4GB split/exFAT Simult block/Slot-1 EROFS=30, Round-57 Errata 4-item [Copyright Info] 46-char & Still+Movie [Write Serial Number] Camera-Reset immune + 2-item [Power Setting Option] 9-cond bypass & dormant [Power Save by Monitor] EOPNOTSUPP=95 + [NTSC/PAL Selector] base.uxc Slot-1 Format Guard, [Zoom Range] CIZ 1.5x/2x & Digital 4x vs FX6 zero Digital Zoom + 8-step speeds + [Auto Slow Shutter] 6-lockout + Dual Base ISO 800/12800 & 100/2000 & 80/1600, and dormant [Lossless Comp] RAW 0x6b56 + [HLG Still Image] HEIF + CRITICAL [USB LUN Setting]=Single Slot-1 ONLY hazard + NP-FZ100 PD gate + dormant UVC 0x755b + 16/16 H0==H3 Tier-0 gate)"),
        ("preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc", "Run Phase 338 17th physical bench readiness verifier (Waves 66-67 ilc/2210: Still [Drive Mode] Hi+ 10fps / >F11 1st-frame AF lock & 100%% dormant [Focus Bracket] EOPNOTSUPP=95 + 2-option [Shutter Type] no-Auto & 1/250 s X-Sync + Reset-immune [e-Front Curtain Shut.] front_curtaion_shutter + [Long Exposure NR] >=1s & [High ISO NR] JPEG/HEIF-only, [Creative Look] 10 presets + Custom 1..6 + asymmetric 0..9 Fade/Sharpness/Clarity + dormant [Soft Skin Effect] + [Recover Image DB] AVF_INFO Slot-1 EROFS=30 firewall & 40,000 cap, [Auto Pixel Mapping] & manual reboot/lens cap/typos pixel_mappinng/excuted + Silent Mode shutdown shutter click + 3-item Reset-immune Setup->[Monitor] thermal clamp & dormant EVF, and Still P/A/S/M-only [Recall Custom hold 1-3] 11 slots w/ zero standalone WB + [External Output] 24.00p reboot / REC Control<-TC Output / ctrl_for_hmdi / dormant 4K/2K & 24p/60p + Slot-1 EROFS=30 + 16/16 H0==H3 Tier-0 gate)"),
        ("preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec", "Run Phase 341 18th physical bench readiness verifier (Waves 68-69 ilc/2210: Reset-immune Setup->[Area/Date/Time Setting] 30 AREA_GMT_* zones + 6 half-hours + typo convert_setting_daylight_saving_to_saylight_saving + soldered >=24h RTC vs FX6 Clock Set, Clean-HDMI [Grid Line Display] 3 types vs Reset-immune [Marker Display] 0px HDMI, Slot-1 [Save/Load Settings] CAMSET/FTPSET/CAMPR EROFS=30 firewall + zero FX3 PC Flash Sync + XLR-H1 passive cold shoe + zero FX6 GENLOCK BNC, Still-only Playback [Magnification] playback_zoom_maginify_by_pinch & [Anti-flicker Shoot.] 100/120Hz vs 100%% dormant [Var. Shutter]/[Anti-flicker Tv Scan] EOPNOTSUPP=95, and Dual-SKU Wi-Fi WW728473 vs WW558244 5GHz gate + WPA2/WPA3 + p12/p13 MS_RDONLY + front #5 [IR Remote Ctrl] FX3A removal + factory-On [CTRL FOR HDMI] ctrl_for_hmdi 41 CEC bench hijack firewall + 16/16 H0==H3 Tier-0 gate)"),
        ("preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether", "Run Phase 342 19th physical bench readiness verifier (Waves 70-71 ilc/2210: Reset-immune [Peaking Display] 0px HDMI + Focus Magnifier coexist + body-dormant Focus Map vs debunking FX6 Peaking Type/Freq myth, Ver.2.00+ [Audio Level Display] removal + 5 Resettable [Audio Recording] items & debunking [Wind Noise Reduct.] Auto myth vs FX6 CH1..4 Wind Filter & 6-step Limiter, [USB Power Supply] 9V/3A Type-C PD + mandatory NP-FZ100 law + zero charging ON + DC-C1 65W/5A vs FX6 19.5V DC IN, [NTSC/PAL Selector] J1/CE/U2 banners + XAVC no-format + Slot-1 EROFS=30 vs FX6 Thumbnail filter, dormant [Anti-Dust Function]/[Shutter When Pwr OFF] OPEN shutter park + [Sensor Cleaning] >=51%% vs FX6 e-ND/APR + [Focus Assistant] FF 1.0/2.1/4.1, APS-C 1.0/1.5/3.0, Movie 1.0/4.0, [Exposure Std. Adjust] -1..+1 EV 1/6 step Reset-immune trap vs FX6 -3.0..+3.0 0.25 step myth-bust, wired [USB-LAN/Tethering] Airplane Mode=On Zero-RF + usbgmscif_setReadOnly Slot-1 EROFS=30 vs FX6 usbg_iap.ko + 16/16 H0==H3 Tier-0 gate)"),
        ("verify-milestone-295", "Verify Grand Milestone Phase 295 6-Pillar Real-Hardware ILME-FX3 Ver. 7.02 Master Gate (>=124-Gate + >=50 Recovery + >=45 Auditors + >=58 VM + Decuple 10/10 Bench Preflights Ph186..Ph291 + FX3 7.02 QEMU R28..R58+, realhw_milestone295_master_gate_v1)"),
        ("verify-milestone-311", "Verify Grand Milestone Phase 311 Forward-Compatible 6-Pillar Real-Hardware ILME-FX3 Ver. 7.02 Master Gate (>=134-Gate + >=54 Recovery + 45/45 Auditors + >=62 VM + Dodecuple 12/12 Bench Preflights Ph186..Ph307 + >=35 FX3 7.02 QEMU Rounds R28..R62+, realhw_milestone311_master_gate_v1)"),
        ("verify-milestone-324", "Verify Grand Milestone Phase 324 Forward-Compatible 6-Pillar Real-Hardware ILME-FX3 Ver. 7.02 Master Gate (>=142-Gate + >=56 Recovery + >=45 Auditors + >=66 VM + Tetradecuple 14/14 Bench Preflights Ph186..Ph321 + >=38 FX3 7.02 QEMU Rounds R28..R65+, realhw_milestone324_master_gate_v1)"),
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
        if cmd_name in ("dry-run-candidate", "verify-p1-recovery-bridge", "build-readiness-packet", "build-stage-b-readiness-packet", "run-stage-b-lifecycle-drill", "verify-stage-b-candidate", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-milestone-147", "verify-milestone-175", "verify-milestone-193", "verify-milestone-209", "verify-milestone-221", "verify-milestone-233", "verify-milestone-254", "verify-milestone-264", "verify-milestone-295", "verify-milestone-311", "verify-milestone-324"):
            p.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
        if cmd_name in ("verify-peripheral-ux", "verify-ap-cp-imaging", "verify-stage-b-p10", "verify-uipc-cp-shim", "verify-wireless-guard", "verify-stage-b-ram-overlay", "verify-stage-b-candidate", "audit-stage-b-post-trial", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-realhw-jiritsu-tier0", "verify-sd-stageb-bundle-uninstaller", "verify-milestone-147", "preflight-realhw-bench", "verify-milestone-175"):
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write audit report")
            p.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic offline verification mode")
        if cmd_name in ("verify-milestone-193", "verify-milestone-209", "verify-milestone-221", "verify-milestone-233"):
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write Milestone master report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force clean-room synthetic offline verification mode")
        if cmd_name in ("verify-milestone-254", "verify-milestone-264", "verify-milestone-295", "verify-milestone-311", "verify-milestone-324"):
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Milestone master report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force clean-room synthetic offline verification mode")
        if cmd_name == "verify-milestone-311":
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize simulated dry-run Tier-0 physical bench receipts for G10..G12 and Ph186..Ph307 without authorizing live hardware attachment")
        if cmd_name == "verify-milestone-324":
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize simulated dry-run Tier-0 physical bench receipts for G10..G12 and Ph186..Ph321 without authorizing live hardware attachment")
        if cmd_name in ("verify-stage-b-ram-overlay", "verify-stage-b-candidate", "rehearse-stage-b-closed-loop", "verify-sd-stageb-bundle-uninstaller"):
            p.add_argument("--lang", default="en", choices=["en", "schinese", "tchinese", "japanese"], help="Select Stage-B BK_LANG (0x02cf019c) shadow language")
        if cmd_name in ("verify-stage-b-ram-overlay", "verify-stage-b-candidate", "audit-stage-b-post-trial", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-realhw-jiritsu-tier0", "verify-sd-stageb-bundle-uninstaller", "verify-milestone-147", "preflight-realhw-bench", "verify-milestone-175", "preflight-card-insert", "verify-milestone-193", "preflight-bench-cable-fan-slot1", "verify-milestone-209", "preflight-hdmi-proxy-desqueeze-and-simult", "verify-milestone-221", "preflight-pixelmap-ntscpal-powersave-and-autotemp", "verify-milestone-233", "preflight-imagedb-touch-shoeaudio-and-lockop", "verify-milestone-254", "preflight-diffset-customkey-autoslow-and-apsc", "verify-milestone-264", "preflight-file-settings-gamma-assist-focus-mag-and-videolight", "preflight-usb-mode-hdmi-info-protect-and-network-reset", "preflight-pp-scinetone-wb-metering-and-shutter-type", "preflight-focus-area-zoom-dci4k-and-sensor-cleaning", "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence", "preflight-dial-customize-lut-embed-steadyshot-and-streaming", "preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth", "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes", "preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter", "preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun", "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc", "preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec", "preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether", "verify-milestone-295", "verify-milestone-311", "verify-milestone-324"):
            p.add_argument("--json", action="store_true", help="Emit full deterministic JSON report to stdout")
        if cmd_name in ("rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-milestone-147", "preflight-realhw-bench", "verify-milestone-175", "preflight-card-insert", "verify-milestone-193", "preflight-bench-cable-fan-slot1", "verify-milestone-209", "preflight-hdmi-proxy-desqueeze-and-simult", "verify-milestone-221", "preflight-pixelmap-ntscpal-powersave-and-autotemp", "verify-milestone-233", "preflight-imagedb-touch-shoeaudio-and-lockop", "verify-milestone-254", "preflight-diffset-customkey-autoslow-and-apsc", "verify-milestone-264", "preflight-file-settings-gamma-assist-focus-mag-and-videolight", "preflight-usb-mode-hdmi-info-protect-and-network-reset", "preflight-pp-scinetone-wb-metering-and-shutter-type", "preflight-focus-area-zoom-dci4k-and-sensor-cleaning", "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence", "preflight-dial-customize-lut-embed-steadyshot-and-streaming", "preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth", "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes", "preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter", "preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun", "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc", "preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec", "preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether", "verify-milestone-295", "verify-milestone-311", "verify-milestone-324"):
            p.add_argument("--markdown-out", type=Path, default=None, help="Optional Markdown report path to write certificate/dossier")
        if cmd_name == "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 321 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--summary", action="store_true", help="Emit compact one-line summary to stdout even when --json is passed")
            p.add_argument("--sony-help-guide-id", default="ilc/2210", help="Official Sony Help Guide identifier (must remain ilc/2210)")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            # Group A (Wave 60 secs 1-2)
            p.add_argument("--recording-media", default="SLOT_2", help="[Recording Media]: SLOT_1, SLOT_2, SIMULTANEOUS_RECORDING, SORT_RECORDING (Still-only)")
            p.add_argument("--auto-switch-media", default="OFF", help="[Auto Switch Media]: OFF or ON (0x6dd9, Initialize-only; bench requires OFF)")
            p.add_argument("--dormant-prioritize-rec-media-requested", action="store_true", help="Request dormant [Prioritize Rec. Media] (_f 0x719e, 0 hits -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-prioritize-rec-media-present-claimed", action="store_true", help="Claim FX3 exposes dormant [Prioritize Rec. Media] (invalid)")
            p.add_argument("--fx3-movie-sort-recording-present-claimed", action="store_true", help="Claim FX3 supports Movie [Sort Recording] (invalid: Still-only)")
            p.add_argument("--claimed-auto-switch-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [Auto Switch Media] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--slot1-fs", default="EXFAT", help="Slot 1 filesystem: EXFAT or FAT32")
            p.add_argument("--slot2-fs", default="EXFAT", help="Slot 2 filesystem: EXFAT or FAT32")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 recovery vault")
            p.add_argument("--no-slot1-wp-locked", dest="slot1_wp_locked", action="store_false", help="Indicate Slot 1 physical write-protect switch is unlocked")
            p.add_argument("--slot1-rec-write-requested", action="store_true", help="Attempt recording write onto Slot-1 Tier-0 vault (blocked EROFS=30)")
            p.add_argument("--slot1-data-sector-writes", type=int, default=0, help="Slot-1 data sector writes (must remain 0)")
            p.add_argument("--fx3-independent-rec-button-slot-set-claimed", action="store_true", help="Claim FX3 has FX6 independent [Rec Button Set] Slot A/B (invalid)")
            p.add_argument("--fx6-relay-with-proxy-streaming-chunk-claimed", action="store_true", help="Claim FX6 allows Relay Rec simultaneously with LAN/Streaming/Proxy/Chunk (invalid)")
            p.add_argument("--media-speed-grade", default="CFEXPRESS_A_VPG200", help="Card speed grade: CFEXPRESS_A_VPG400, CFEXPRESS_A_VPG200, SDXC_V90, SDXC_V60, SDXC_V30, SDHC_U3")
            p.add_argument("--movie-file-format", default="XAVC_S_I_4K", help="Movie file format: XAVC_S_I_DCI_4K, XAVC_S_I_4K, XAVC_S_I_HD, XAVC_S_4K, XAVC_HS_4K, XAVC_S_HD")
            p.add_argument("--movie-bitrate-mbps", type=int, default=240, help="Movie bitrate in Mbps (e.g. 240, 280, 600, 890, 1200)")
            p.add_argument("--rec-fps", type=float, default=23.98, help="Recording frame rate in fps (proxy blocked >= 100.0p)")
            p.add_argument("--sq-enabled", action="store_true", help="Enable S&Q Motion shooting")
            p.add_argument("--sq-fps", type=float, default=60.0, help="S&Q frame rate in fps (proxy blocked >= 100.0 fps)")
            p.add_argument("--proxy-recording", default="OFF", help="[Proxy Recording]: OFF or ON")
            p.add_argument("--proxy-file-format", default="XAVC_S_HD", help="Proxy [File Format]: XAVC_S_HD or XAVC_HS_HD")
            p.add_argument("--proxy-record-setting", default="1280x720_6M_8BIT", help="Proxy [Record Setting]: 1280x720_6M_8BIT, 1920x1080_9M_10BIT, 1920x1080_16M_10BIT")
            p.add_argument("--dormant-proxy-8bit-fhd-requested", action="store_true", help="Request dormant 8-bit FHD Proxy (_f 0x6b8f -> EOPNOTSUPP=95)")
            p.add_argument("--no-vpg400-caution-acknowledged", dest="vpg400_caution_acknowledged", action="store_false", help="Simulate unacknowledged base.uxc 0xe224 VPG400 CFexpress Type A caution")
            p.add_argument("--claimed-sdhc-no-4gb-split", action="store_true", help="Claim SDHC FAT32 clips do not split at 4 GB (invalid)")
            p.add_argument("--claimed-proxy-blocked-on-dci4k-60p", action="store_true", help="Claim Proxy Recording is directly disabled on XAVC S-I DCI 4K <= 59.94p (invalid)")
            p.add_argument("--claimed-proxy-resists-camera-reset", action="store_true", help="Claim Proxy Settings resist Camera Settings Reset (invalid)")
            p.add_argument("--proxy-slot1-write-or-coupled-delete-requested", action="store_true", help="Attempt M4ROOT/SUB/*S03.MP4 coupled delete/protect/write on Slot 1 (blocked EROFS=30)")
            p.add_argument("--claimed-fx3-has-fx6-chunk-upload", action="store_true", help="Claim FX3 supports FX6 Chunk Proxy + Slot B recording (invalid)")
            # Group B (Wave 60 secs 3-4)
            p.add_argument("--cloud-connection", default="OFF", help="[Cloud Connection *]: OFF or ON (mutually exclusive with FTP)")
            p.add_argument("--c3-portal-enabled", action="store_true", help="Enable Ver. 4.00+ [C3 Portal] LUT/settings sync (blocked under Zero-RF)")
            p.add_argument("--clip-flag-filter", default="NONE", help="Ver. 7.00+ Cloud Clip Flag filter: NONE, OK, NG, KEEP")
            p.add_argument("--claimed-cloud-wiped-by-camera-reset", action="store_true", help="Claim [Cloud Connection *] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-cloud-wiped-by-initialize", action="store_true", help="Claim [Cloud Connection *] was wiped by Initialize (invalid: * persistence)")
            p.add_argument("--claimed-c3-portal-before-v400", action="store_true", help="Claim [C3 Portal] shipped prior to FX3 Ver. 4.00 (invalid)")
            p.add_argument("--claimed-fx3-cloud-does-not-exclude-ftp", action="store_true", help="Claim FX3 Cloud Connection and FTP operate concurrently (invalid)")
            p.add_argument("--airplane-mode", default="ON", help="[Airplane Mode]: ON or OFF (bench requires ON)")
            p.add_argument("--cnct-while-power-off", default="OFF", help="[Cnct. while Power OFF] (0x6ab3): OFF or ON (bench requires OFF for Zero-RF BLE)")
            p.add_argument("--bluetooth-function", default="OFF", help="[Bluetooth Function]: OFF or ON (bench requires OFF)")
            p.add_argument("--wifi-enabled", action="store_true", help="Indicate Wi-Fi radio is enabled (blocked on Zero-RF bench)")
            p.add_argument("--wireless-rf-packets-emitted", type=int, default=0, help="Wireless RF packets emitted (must remain 0)")
            p.add_argument("--rf-nvs-p12-p13-writes-requested", action="store_true", help="Attempt write to RF NVRAM p12/p13 (blocked)")
            p.add_argument("--claimed-cnct-while-power-off-wiped-by-camera-reset", action="store_true", help="Claim [Cnct. while Power OFF] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx6-has-bluetooth-claimed", action="store_true", help="Claim ILME-FX6 has Bluetooth hardware (invalid)")
            p.add_argument("--mymenu-pages", type=int, default=6, help="[My Menu] page count (must be 6)")
            p.add_argument("--mymenu-slots-per-page", type=int, default=7, help="[My Menu] slots per page (must be 7)")
            p.add_argument("--mymenu-total-slots", type=int, default=42, help="[My Menu] total NVRAM slots (exact 6 x 7 = 42)")
            p.add_argument("--fx3-mymenu-30-or-36-slots-only-claimed", action="store_true", help="Claim FX3 My Menu is capped at 30 or 36 slots instead of 42 (invalid)")
            p.add_argument("--mymenu-playback-item-requested", action="store_true", help="Request registering (Playback) item into FX3 [My Menu] (disallowed)")
            p.add_argument("--claimed-mymenu-wiped-by-camera-reset", action="store_true", help="Claim [My Menu] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx6-user-menu-pin", default="0000", help="ILME-FX6 4-digit User Menu with Lock PIN (0000..9999)")
            p.add_argument("--claimed-fx3-has-pin-user-menu-with-lock", action="store_true", help="Claim FX3 has FX6 4-digit PIN User Menu with Lock (invalid)")
            p.add_argument("--claimed-fx6-user-menu-pin-included-in-all-file", action="store_true", help="Claim FX6 User Menu PIN is included in All File backup (invalid: excluded)")
            # Group C (Wave 61 secs 1-2)
            p.add_argument("--ftp-transfer-func", default="OFF", help="[FTP Transfer Func.]: OFF or ON")
            p.add_argument("--ftp-server-slot", type=int, default=1, help="FX3 FTP Server index (1..9)")
            p.add_argument("--ftp-protocol", default="FTPES", help="FTP protocol: FTPES (0x6553), FTP, NONE (SFTP rejected EOPNOTSUPP=95)")
            p.add_argument("--ftp-transfer-mode", default="PASSIVE", help="FTP transfer mode: PASSIVE (ACTIVE rejected EOPNOTSUPP=95)")
            p.add_argument("--ftp-active-mode-requested", action="store_true", help="Request FTP Active Mode on FX3 (rejected EOPNOTSUPP=95)")
            p.add_argument("--fx3-sftp-present-claimed", action="store_true", help="Claim FX3 supports SFTP (invalid)")
            p.add_argument("--fx3-ftp-active-mode-present-claimed", action="store_true", help="Claim FX3 supports FTP Active Mode (invalid)")
            p.add_argument("--dormant-transfer-jpeg-heif-size-requested", action="store_true", help="Request dormant [Transfer JPEG/HEIF Size] (rejected EOPNOTSUPP=95)")
            p.add_argument("--fx3-transfer-jpeg-heif-size-present-claimed", action="store_true", help="Claim FX3 exposes [Transfer JPEG/HEIF Size] (invalid)")
            p.add_argument("--claimed-fx3-uses-certification-pem-slot-b", action="store_true", help="Claim FX3 uses FX6 certification.pem on Slot B instead of cacert.pem on Slot 1 (invalid)")
            p.add_argument("--claimed-fx3-ftp-limited-to-3-servers", action="store_true", help="Claim FX3 FTP is capped at FX6 3 servers instead of 9 (invalid)")
            p.add_argument("--ftp-slot1-write-or-transfer-list-requested", action="store_true", help="Attempt AVF_INFO FTP transfer-list write onto Slot 1 (blocked EROFS=30)")
            p.add_argument("--cacert-pem-size-bytes", type=int, default=2048, help="Root certificate cacert.pem size in bytes (1..1048576)")
            p.add_argument("--cacert-write-to-slot1-requested", action="store_true", help="Attempt cacert.pem write onto Slot-1 Tier-0 vault (blocked EROFS=30)")
            p.add_argument("--usb-lan-tethering", default="OFF", help="[USB-LAN/Tethering]: OFF or ON (Airplane Mode does NOT block wired USB-LAN!)")
            p.add_argument("--usb-lan-cnct-launch", default="OFF", help="[USB-LAN Cnct. Launch]: OFF or ON (bench requires OFF)")
            p.add_argument("--network-transport", default="NONE", help="Active network transport: NONE, USB_LAN, WIRELESS_RF (bench requires NONE)")
            p.add_argument("--claimed-airplane-mode-blocks-usb-lan", action="store_true", help="Claim [Airplane Mode]=On automatically disables wired USB-LAN FTP (invalid bypass trap)")
            p.add_argument("--wb-mode", default="C_TEMP_FILTER", help="[White Balance]: AUTO, C_TEMP_FILTER, CUSTOM_1..3, UNDERWATER_AUTO, DAYLIGHT, etc.")
            p.add_argument("--wb-kelvin-k", type=int, default=5600, help="Color temperature Kelvin (2500..9900 in 100K steps)")
            p.add_argument("--wb-ab-shift", type=int, default=0, help="Amber-Blue fine shift (-7..+7)")
            p.add_argument("--wb-gm-shift", type=int, default=0, help="Green-Magenta fine shift (-7..+7)")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, FLEXIBLE_ISO, CINE_EI_QUICK, CINE_EI")
            p.add_argument("--picture-profile", default="OFF", help="[Picture Profile]: OFF, PP1..PP11, PPLUT1..PPLUT4")
            p.add_argument("--custom-wb-setup-requested", action="store_true", help="Request Custom WB [Custom Setup] (0x63ac; error 0x0220 under Log/S-Log3/PPLUT)")
            p.add_argument("--claimed-custom-wb-saved-in-camset", action="store_true", help="Claim Custom WB 1..3 is saved into CAMSET*.DAT (invalid: excluded)")
            p.add_argument("--claimed-custom-wb-wiped-by-camera-reset", action="store_true", help="Claim Custom WB 1..3 is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--priority-set-in-awb", default="STANDARD", help="[Priority Set in AWB]: STANDARD, AMBIENCE, WHITE")
            p.add_argument("--shutter-awb-lock", default="OFF", help="Still [Shutter AWB Lock]: OFF, SHUT_HALF_DOWN, CONT_SHOOTING, BOTH")
            p.add_argument("--shockless-wb", default="1_FAST", help="Movie [Shockless WB]: OFF, 1_FAST, 2, 3_SLOW")
            p.add_argument("--claimed-shutter-awb-lock-wiped-by-camera-reset", action="store_true", help="Claim Still [Shutter AWB Lock] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-shockless-wb-resists-camera-reset", action="store_true", help="Claim Movie [Shockless WB] resists Camera Settings Reset (invalid)")
            p.add_argument("--claimed-fx3-has-atw-speed-or-memory-ah", action="store_true", help="Claim FX3 exposes FX6 WHT BAL ATW Speed 1..5 or Memory A..H (invalid)")
            # Group D (Wave 61 secs 3-4 + Tier-0)
            p.add_argument("--af-transition-speed", type=int, default=5, help="[AF Transition Speed] (1..7, default 5 on both FX3 & FX6)")
            p.add_argument("--af-subj-shift-sens", type=int, default=5, help="[AF Subj. Shift Sens.] (1..5, default 5 on both FX3 & FX6; never 1..7)")
            p.add_argument("--fx3-af-subj-shift-7-levels-claimed", action="store_true", help="Claim FX3 [AF Subj. Shift Sens.] has 7 levels (invalid: 1..5)")
            p.add_argument("--fx6-af-subj-shift-7-levels-claimed", action="store_true", help="Claim FX6 [AF Subj. Shift Sens.] has 7 levels (invalid: 1..5)")
            p.add_argument("--af-assist", default="OFF", help="[AF Assist]: ON or OFF (incompatible w/ SELP1650/SEL18200LE; resets on Camera Settings Reset)")
            p.add_argument("--lens-model", default="SEL2470GM2", help="Attached lens model (e.g. SEL2470GM2, SELP1650, SEL18200LE)")
            p.add_argument("--claimed-af-assist-resists-camera-reset", action="store_true", help="Claim [AF Assist] resists Camera Settings Reset (invalid)")
            p.add_argument("--in-body-focus-map-requested", action="store_true", help="Request in-body FX3 [Focus Map] (0 hits -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-in-body-focus-map-present-claimed", action="store_true", help="Claim FX3 has in-body Focus Map like FX6 (invalid)")
            p.add_argument("--fx3-uvc-streaming-present-claimed", action="store_true", help="Claim FX3 has UVC streaming (invalid: NOUVC)")
            p.add_argument("--mc-focus-map-enabled", action="store_true", help="Enable Ver. 6.00+ external Monitor & Control Focus Map")
            p.add_argument("--mc-focus-map-fps", type=float, default=23.98, help="External M&C Focus Map frame rate (blocked at >= 150.0 fps)")
            p.add_argument("--mc-focus-map-over-wifi-requested", action="store_true", help="Request external M&C Focus Map over Wi-Fi on Zero-RF bench (blocked)")
            p.add_argument("--playback-control-active", action="store_true", help="Indicate Playback control is active (blocks M&C Focus Map)")
            p.add_argument("--no-lens-pdaf-capable", dest="lens_pdaf_capable", action="store_false", help="Indicate lens lacks PDAF support (blocks M&C Focus Map)")
            p.add_argument("--auto-framing-claimed", action="store_true", help="Claim Auto Framing is active alongside M&C Focus Map (invalid on FX3)")
            p.add_argument("--usb-remote-or-uvc-active", action="store_true", help="Indicate USB remote or UVC active (blocks M&C Focus Map)")
            p.add_argument("--claimed-mc-focus-map-blocked-at-120p", action="store_true", help="Claim M&C Focus Map is blocked below 150fps e.g. at 119.88p (invalid)")
            p.add_argument("--aspect-marker", default="OFF", help="[Aspect Marker] 16-state value (OFF or one of 15 ratios e.g. 9:16, 16:9, 2.39:1)")
            p.add_argument("--exposed-aspect-markers", default=None, help="Comma-separated exposed [Aspect Marker] states override (must match 16 states)")
            p.add_argument("--safety-zone", default="OFF", help="[Safety Zone]: OFF, 80PCT (80%%), 90PCT (90%%)")
            p.add_argument("--peaking-display", default="OFF", help="[Peaking Display]: OFF or ON")
            p.add_argument("--peaking-level", default="MID", help="[Peaking Level]: HIGH, MID, LOW")
            p.add_argument("--peaking-color", default="WHITE", help="[Peaking Color]: RED, YELLOW, BLUE, WHITE (4 colors only)")
            p.add_argument("--focus-magnifier-active", action="store_true", help="Indicate Focus Magnifier is active (hides Marker Display)")
            p.add_argument("--expect-marker-or-peaking-on-hdmi", action="store_true", help="Claim Aspect Marker / Peaking leaks onto HDMI output (invalid)")
            p.add_argument("--expect-marker-visible-during-focus-magnifier", action="store_true", help="Claim Marker Display stays visible during Focus Magnifier (invalid)")
            p.add_argument("--claimed-marker-or-peaking-wiped-by-camera-reset", action="store_true", help="Claim 8 Initialize-only Marker/Peaking items were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-fx3-has-user-box-or-925-95-safety-or-bw-peaking", action="store_true", help="Claim FX3 has FX6 pixel User Box, 92.5%%/95%% Safety Zone, or B&W Peaking (invalid)")
            p.add_argument("--e-nd-actuator-tx-count", type=int, default=0, help="e-ND I2C actuator TX count (must remain 0)")
            p.add_argument("--usb-packets-transmitted", type=int, default=0, help="USB packets transmitted (must remain 0)")
            p.add_argument("--simulated-passive-tx-bytes", type=int, default=0, help="Simulated passive UART TX bytes emitted (must remain 0)")
            p.add_argument("--simulated-h0-h3-drifted-surfaces", type=int, default=0, help="Simulated H0 vs H3 drifted surfaces (must remain 0)")
            p.add_argument("--claim-hardware-live-attach-authorized", action="store_true", help="Claim live hardware attachment is authorized offline (fail-closed rejection)")
            p.add_argument("--claim-persistent-emmc-writes-authorized", action="store_true", help="Claim persistent eMMC writes are authorized (fail-closed rejection)")
            p.add_argument("--claim-cross-model-flash-authorized", action="store_true", help="Claim cross-model partition flashing is authorized (fail-closed rejection)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 334 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--summary", action="store_true", help="Emit compact one-line summary to stdout even when --json is passed")
            p.add_argument("--sony-help-guide-id", default="ilc/2210", help="Official Sony Help Guide identifier (must remain ilc/2210)")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--exposure-mode", default="MANUAL_EXPOSURE", help="[Exposure Mode]: MANUAL_EXPOSURE, PROGRAM_AUTO, APERTURE_PRIORITY, SHUTTER_PRIORITY, INTELLIGENT_AUTO, FLEXIBLE_EXP")
            # Group A (Wave 64 secs 1-2)
            p.add_argument("--breathing-comp", default="OFF", help="[Breathing Comp.] (0x79fd): OFF or ON (Resettable)")
            p.add_argument("--rec-fps", type=float, default=23.98, help="Recording frame rate in fps (100p/120p locks Breathing Comp. & CIZ)")
            p.add_argument("--sq-enabled", action="store_true", help="Enable S&Q Motion shooting")
            p.add_argument("--sq-fps", type=float, default=60.0, help="S&Q frame rate in fps (>=100/120 locks Breathing Comp. & CIZ)")
            p.add_argument("--hdmi-raw-output", default="OFF", help="HDMI [RAW Output]: ON or OFF")
            p.add_argument("--zoom-range", default="OPTICAL_ONLY", help="[Zoom Range]: OPTICAL_ONLY, CLEAR_IMAGE_ZOOM, DIGITAL_ZOOM")
            p.add_argument("--auto-framing-claimed", action="store_true", help="Claim Auto Framing active (invalid: dormant on FX3)")
            p.add_argument("--non-compliant-or-teleconverter-lens", action="store_true", help="Indicate macro SEL100F28GM 0.57-1.0m / teleconverter / 3rd-party / manual lens attached")
            p.add_argument("--claimed-breathing-comp-resists-camera-reset", action="store_true", help="Claim [Breathing Comp.] resists Camera Settings Reset (invalid: Resettable)")
            p.add_argument("--claimed-static-lens-comp-reset-by-camera-reset", action="store_true", help="Claim Shading/Chromatic/Distortion Comp. reset via Camera Settings Reset (invalid)")
            p.add_argument("--claimed-fx3-blocks-breathing-below-100fps-sq", action="store_true", help="Claim FX3 blocks Breathing Comp. below 100fps S&Q (invalid: allowed <100fps)")
            p.add_argument("--fx6-breathing-allows-sq-or-distortion-off-or-raw-claimed", action="store_true", help="Claim FX6 allows Breathing Comp. with S&Q=On, Distortion Comp=Off, or RAW (invalid)")
            p.add_argument("--post-breathing-comp-requested", action="store_true", help="Request post-production metadata breathing compensation workflow")
            p.add_argument("--catalyst-app", default="NONE", help="Post-production Catalyst tool: NONE, CATALYST_PREPARE, CATALYST_PREPARE_PLUGIN, CATALYST_BROWSE")
            p.add_argument("--distortion-comp", default="AUTO", help="[Distortion Comp.]: AUTO or OFF")
            p.add_argument("--claimed-catalyst-browse-supports-breathing-comp", action="store_true", help="Claim free Catalyst Browse supports metadata breathing compensation (invalid)")
            p.add_argument("--file-number-mode", default="SERIES", help="Movie [File Number]: SERIES or RESET")
            p.add_argument("--series-counter-reset-slot", type=int, default=0, help="Target slot for [Series Counter Reset] (_f 0x6a52) (1 blocked EROFS=30)")
            p.add_argument("--movie-file-counter-write-slot", type=int, default=0, help="Target slot for Movie file/reel counter write (1 blocked EROFS=30)")
            p.add_argument("--file-name-format", default="STANDARD", help="Movie [File Name Format]: STANDARD, CAM_ID_PLUS_REEL, TITLE, DATE_PLUS_TITLE, TITLE_PLUS_DATE")
            p.add_argument("--camera-id", default="A", help="Movie [Camera ID]: A..Z")
            p.add_argument("--reel-number", type=int, default=1, help="Movie [Reel Number]: 1..999")
            p.add_argument("--camera-position", default="C", help="Movie [Camera Position]: C, L, R")
            p.add_argument("--title-name", default="C", help="Movie [Title Name Settings] <= 37 ASCII chars (default C)")
            p.add_argument("--claimed-movie-file-settings-reset-by-camera-reset", action="store_true", help="Claim Initialize-only Movie [File Settings] reset by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-custom-movie-folder-supported", action="store_true", help="Claim custom Movie folder outside PRIVATE/M4ROOT/CLIP (invalid)")
            p.add_argument("--claimed-file-number-reset-resets-reel", action="store_true", help="Claim File Number=Reset resets Reel Number (invalid)")
            p.add_argument("--expect-rollover-mutates-cam-id-menu", action="store_true", help="Claim C999->D001 rollover mutates Camera ID menu setting (invalid)")
            p.add_argument("--claimed-cam-id-reel-uses-yyyymmdd-date", action="store_true", help="Claim Cam ID + Reel# uses YYYYMMDD instead of YYMMDD (invalid)")
            p.add_argument("--fx6-clip-naming-uses-project-menu-or-37char-claimed", action="store_true", help="Claim FX6 uses Shooting > File Settings or 37-char Title (invalid: TC/Media 4..46)")
            p.add_argument("--recording-media", default="SLOT_2", help="[Recording Media]: SLOT_1, SLOT_2, SIMULTANEOUS_RECORDING, SORT_RECORDING")
            p.add_argument("--slot1-media-type", default="CFEXPRESS_A", help="Slot 1 media type: CFEXPRESS_A, SDXC, SDHC")
            p.add_argument("--slot2-media-type", default="CFEXPRESS_A", help="Slot 2 media type: CFEXPRESS_A, SDXC, SDHC")
            p.add_argument("--slot1-fs", default="EXFAT", help="Slot 1 filesystem: EXFAT or FAT32")
            p.add_argument("--slot2-fs", default="EXFAT", help="Slot 2 filesystem: EXFAT or FAT32")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 recovery vault")
            p.add_argument("--slot1-data-sector-writes", type=int, default=0, help="Slot-1 data sector writes (must remain 0)")
            p.add_argument("--claimed-sdhc-no-4gb-split", action="store_true", help="Claim SDHC FAT32 clips do not split at 4 GB (invalid)")
            # Group B (Wave 64 secs 3-4)
            p.add_argument("--exposed-copyright-items", default=None, help="Comma-separated 4 [Copyright Info] items override")
            p.add_argument("--write-copyright-info", default="OFF", help="[Write Copyright Info]: OFF or ON")
            p.add_argument("--set-photographer", default="", help="[Set Photographer] <= 46 ASCII chars (Round-57 Reset-immune)")
            p.add_argument("--set-copyright", default="", help="[Set Copyright] <= 46 ASCII chars (Round-57 Reset-immune)")
            p.add_argument("--disp-copyright-info-requested", action="store_true", help="Inspect [Disp. Copyright Info]")
            p.add_argument("--write-serial-number", default="OFF", help="[Write Serial Number] (Still+Movie BKID): OFF or ON (Round-57 Reset-immune)")
            p.add_argument("--claimed-copyright-wiped-by-camera-reset", action="store_true", help="Claim [Copyright Info] was wiped by Camera Settings Reset (Round-57 Errata: invalid)")
            p.add_argument("--claimed-write-serial-wiped-by-camera-reset", action="store_true", help="Claim [Write Serial Number] was wiped by Camera Settings Reset (Round-57 Errata: invalid)")
            p.add_argument("--claimed-write-serial-still-only-in-v702", action="store_true", help="Claim [Write Serial Number] is Still-only in Ver. 7.02 (invalid: Still+Movie)")
            p.add_argument("--claimed-copyright-saved-in-camset", action="store_true", help="Claim [Copyright Info] is saved in CAMSET*.DAT (invalid: excluded)")
            p.add_argument("--claimed-write-serial-excluded-from-camset", action="store_true", help="Claim [Write Serial Number] boolean is excluded from CAMSET*.DAT (invalid: included)")
            p.add_argument("--fx6-has-copyright-info-menu-claimed", action="store_true", help="Claim ILME-FX6 exposes [Copyright Info] menu (invalid)")
            p.add_argument("--exposed-power-option-items", default=None, help="Comma-separated 2 [Power Setting Option] items override")
            p.add_argument("--power-save-start-time", default="5_MIN", help="[Power Save Start Time]: OFF, 30_MIN, 5_MIN, 2_MIN, 1_MIN, 10_SEC")
            p.add_argument("--dormant-power-save-timer-requested", default="NONE", help="Request dormant Power Save timer (e.g. 5_SEC, 15_MIN -> EOPNOTSUPP=95)")
            p.add_argument("--power-save-bypass-condition", action="append", default=[], help="Active [Power Save Start Time] bypass condition from the 9 documented conditions")
            p.add_argument("--power-save-sleep-expected-during-bypass", action="store_true", help="Claim Power Save triggers during an active 9-condition bypass (invalid)")
            p.add_argument("--claimed-power-save-ignores-9-conditions", action="store_true", help="Claim Power Save ignores the 9 documented bypass conditions (invalid)")
            p.add_argument("--auto-power-off-temp", default="STANDARD", help="[Auto Power OFF Temp.]: STANDARD or HIGH (HIGH tripod-only)")
            p.add_argument("--handheld-bare-skin-unacknowledged", action="store_true", help="Simulate HIGH thermal setting handheld without tripod acknowledgment")
            p.add_argument("--dormant-power-save-by-monitor-requested", action="store_true", help="Request dormant [Power Save by Monitor] (_f 0x6f2d..0x6f31 -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-power-save-by-monitor-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 exposes [Power Save by Monitor] (invalid)")
            p.add_argument("--fx3-builtin-evf-present", action="store_true", help="Claim FX3 has a built-in EVF (invalid)")
            p.add_argument("--claimed-power-option-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [Power Setting Option] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--video-system", default="NTSC", help="[NTSC/PAL Selector]: NTSC or PAL")
            p.add_argument("--ntsc-pal-switch-requested", action="store_true", help="Request [NTSC/PAL Selector] system switch (triggers reboot)")
            p.add_argument("--expect-ntsc-pal-no-reboot", action="store_true", help="Claim [NTSC/PAL Selector] switches without reboot (invalid)")
            p.add_argument("--expect-cross-system-playback-without-switch", action="store_true", help="Claim NTSC/PAL cross-system playback works without switching selector (invalid)")
            p.add_argument("--claimed-ntsc-pal-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [NTSC/PAL Selector] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx6-has-ntsc-pal-selector-claimed", action="store_true", help="Claim FX6 uses Setup > [NTSC/PAL Selector] instead of System > Frequency (invalid)")
            p.add_argument("--no-slot1-wp-locked", dest="slot1_wp_locked", action="store_false", help="Indicate Slot 1 physical write-protect switch is unlocked")
            p.add_argument("--slot1-format-requested", action="store_true", help="Attempt base.uxc Format prompt onto Slot-1 Tier-0 Vault (blocked EROFS=30)")
            # Group C (Wave 65 secs 1-2)
            p.add_argument("--flexible-shutter-mode", default="MANUAL", help="Flexible Exposure Shutter mode: AUTO or MANUAL")
            p.add_argument("--shutter-mode", default="SHUTTER_SPEED", help="[Shutter Mode]: SHUTTER_SPEED or SHUTTER_ANGLE")
            p.add_argument("--zoom-scale", type=float, default=1.0, help="Requested digital/CIZ zoom scale (1.0..4.0)")
            p.add_argument("--zoom-ring-rotate", default="LEFT_W_RIGHT_T", help="[Zoom Ring Rotate]: LEFT_W_RIGHT_T or RIGHT_W_LEFT_T")
            p.add_argument("--zoom-lever-stby-speed", type=int, default=3, help="Zoom lever 1st-step Standby speed (1..8, def 3)")
            p.add_argument("--zoom-lever-rec-speed", type=int, default=3, help="Zoom lever 1st-step Rec speed (1..8, def 3)")
            p.add_argument("--zoom-lever-2nd-speed", type=int, default=8, help="Zoom lever 2nd-step speed (1..8, def 8)")
            p.add_argument("--custom-key-zoom-stby-speed", type=int, default=3, help="[Custom Key Z. Speed] Standby (1..8, def 3)")
            p.add_argument("--custom-key-zoom-rec-speed", type=int, default=3, help="[Custom Key Z. Speed] Rec (1..8, def 3)")
            p.add_argument("--remote-zoom-speed-type", default="VARIABLE", help="[Remote Zoom Speed] Speed Type: VARIABLE or FIXED")
            p.add_argument("--remote-zoom-fixed-stby-speed", type=int, default=3, help="[Remote Zoom Speed] Fixed Standby speed (1..8, def 3)")
            p.add_argument("--remote-zoom-fixed-rec-speed", type=int, default=3, help="[Remote Zoom Speed] Fixed Rec speed (1..8, def 3)")
            p.add_argument("--still-file-format", default="RAW", help="Still [File Format]: RAW, RAW_AND_JPEG, RAW_AND_HEIF, JPEG, HEIF")
            p.add_argument("--focus-area", default="WIDE", help="[Focus Area]: WIDE, ZONE, CENTER_FIX, SPOT_S, SPOT_M, SPOT_L, EXPAND_SPOT")
            p.add_argument("--metering-mode", default="MULTI", help="[Metering Mode]: MULTI, CENTER, SPOT, ENTIRE_SCREEN_AVG, HIGHLIGHT")
            p.add_argument("--face-eye-prior-in-af", default="ON", help="[Face/Eye Prior. in AF]: ON or OFF")
            p.add_argument("--tracking-af-active", action="store_true", help="Indicate Tracking AF is active (locked out under CIZ/Digital Zoom)")
            p.add_argument("--claimed-zoom-range-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [Zoom Range] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-zoom-ring-rotate-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [Zoom Ring Rotate] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-zoom-speeds-resist-camera-reset", action="store_true", help="Claim Resettable 8-step zoom speeds resist Camera Settings Reset (invalid)")
            p.add_argument("--expect-smart-zoom-in-movie", action="store_true", help="Claim Smart Zoom operates in Movie mode (invalid: Still JPEG/HEIF only)")
            p.add_argument("--fx6-has-digital-zoom-claimed", action="store_true", help="Claim ILME-FX6 exposes Digital Zoom beyond Clear Image Zoom (invalid)")
            p.add_argument("--auto-slow-shutter", default="ON", help="[Auto Slow Shutter]: ON or OFF (Resettable)")
            p.add_argument("--expect-auto-slow-shutter-active", action="store_true", help="Assert [Auto Slow Shutter] is actively engaged")
            p.add_argument("--claimed-auto-slow-shutter-resists-reset", action="store_true", help="Claim [Auto Slow Shutter] resists Camera Settings Reset (invalid)")
            p.add_argument("--iso-mode", default="CINE_EI_BASE", help="[ISO]: ISO_AUTO, MANUAL_ISO, CINE_EI_BASE")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, FLEXIBLE_ISO, CINE_EI_QUICK, CINE_EI")
            p.add_argument("--iso-range-limit-min", type=int, default=80, help="[ISO Range Limit] Minimum ISO (80..409600)")
            p.add_argument("--iso-range-limit-max", type=int, default=102400, help="[ISO Range Limit] Maximum ISO (80..409600)")
            p.add_argument("--claimed-iso-range-limit-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [ISO Range Limit] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--expect-iso-range-limit-caps-iso-auto", action="store_true", help="Claim [ISO Range Limit] caps ISO AUTO min/max bounds (invalid: manual ISO only)")
            p.add_argument("--iso-auto-min-ss", default="STD", help="Still [ISO AUTO Min. SS]: SLOWER, SLOW, STD, FAST, FASTER, or manual shutter")
            p.add_argument("--flash-enabled", action="store_true", help="Enable Flash firing (locks Still [ISO AUTO Min. SS] to 1/60s)")
            p.add_argument("--expect-iso-auto-min-ss-in-movie-or-sq", action="store_true", help="Claim [ISO AUTO Min. SS] operates in Movie/S&Q (invalid: Still P/A only)")
            p.add_argument("--expect-iso-auto-min-ss-active-with-flash", action="store_true", help="Claim [ISO AUTO Min. SS] overrides 1/60s flash clamp (invalid)")
            p.add_argument("--claimed-iso-auto-min-ss-resists-reset", action="store_true", help="Claim [ISO AUTO Min. SS] resists Camera Settings Reset (invalid)")
            p.add_argument("--gamma-base-profile", default="CINE_EI", help="Dual Base ISO profile: CINE_EI, FLEXIBLE_ISO, PP11_S_CINETONE, HLG, PP_OFF")
            p.add_argument("--dual-base-iso-low", type=int, default=800, help="Low base ISO for selected profile (800/100/80)")
            p.add_argument("--dual-base-iso-high", type=int, default=12800, help="High base ISO for selected profile (12800/2000/1600)")
            p.add_argument("--claimed-base-iso-menu-outside-cine-ei", action="store_true", help="Claim explicit [Base ISO] switch menu exists outside Cine EI (invalid)")
            p.add_argument("--fx3-has-fx6-agc-claimed", action="store_true", help="Claim FX3 exposes FX6 AGC (Auto Gain Control) menu (invalid)")
            # Group D (Wave 65 secs 3-4 + Tier-0)
            p.add_argument("--raw-file-type", default="COMPRESSED", help="Still [RAW File Type]: COMPRESSED or UNCOMPRESSED (Resettable)")
            p.add_argument("--dormant-lossless-comp-requested", action="store_true", help="Request dormant [Lossless Comp] RAW (_f 0x6b56 -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-lossless-comp-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 exposes [Lossless Comp] RAW (invalid)")
            p.add_argument("--claimed-raw-file-type-resists-reset", action="store_true", help="Claim [RAW File Type] resists Camera Settings Reset (invalid)")
            p.add_argument("--jh-file-type", default="JPEG", help="[JPEG/HEIF Switch]: JPEG or HEIF")
            p.add_argument("--hlg-still-image", default="OFF", help="[HLG Still Image]: ON or OFF (requires HEIF + P/A/S/M)")
            p.add_argument("--auto-switch-media", default="OFF", help="[Auto Switch Media]: OFF or ON")
            p.add_argument("--auto-switch-failover-to-slot1-requested", action="store_true", help="Attempt [Auto Switch Media] / [Sort Recording] failover onto Slot-1 Tier-0 Vault (blocked EROFS=30)")
            p.add_argument("--usb-connection-mode", default="SEL_WHEN_CONNECT", help="[USB Connection Mode]: SEL_WHEN_CONNECT, MASS_STORAGE, MTP, REMOTE_SHOOTING")
            p.add_argument("--usb-lun-setting", default="MULTI", help="[USB LUN Setting]: MULTI or SINGLE (SINGLE exposes Slot 1 ONLY!)")
            p.add_argument("--claimed-usb-lun-single-exposes-slot2", action="store_true", help="Claim [USB LUN Setting]=Single exposes Slot 2 instead of Slot 1 (invalid: Slot 1 ONLY hazard!)")
            p.add_argument("--no-host-msc-isolated", dest="host_msc_isolated", action="store_false", help="Indicate host USB Mass Storage class is NOT isolated")
            p.add_argument("--host-spotlight-fseventsd-fsck-unblocked", action="store_true", help="Indicate host Spotlight/fseventsd/fsck auto-write is NOT blocked during MSC LUN")
            p.add_argument("--non-airgapped-bench", dest="air_gapped_bench", action="store_false", help="Indicate bench is not air-gapped")
            p.add_argument("--claimed-usb-settings-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only USB settings were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--usb-power-supply", default="ON", help="[USB Power Supply]: ON or OFF")
            p.add_argument("--usb-power-terminal", default="USB_TYPE_C", help="USB power terminal: USB_TYPE_C or MULTI_MICRO_USB")
            p.add_argument("--power-source", default="INTERNAL_NP_FZ100", help="Power source: INTERNAL_NP_FZ100, USB_PD_BODY, DC_C1_COUPLER")
            p.add_argument("--no-np-fz100-inserted", dest="np_fz100_inserted", action="store_false", help="Indicate NP-FZ100 battery is NOT inserted (blocks USB PD unless DC-C1)")
            p.add_argument("--dc-c1-coupler-inserted", action="store_true", help="Indicate DC-C1 coupler is seated in battery bay")
            p.add_argument("--dc-c1-pd-watts", type=float, default=0.0, help="DC-C1 USB-PD source wattage (>= 65.0W required when DC-C1 used)")
            p.add_argument("--dc-c1-cable-amps", type=float, default=0.0, help="DC-C1 USB-C cable rating in amps (>= 5.0A required when DC-C1 used)")
            p.add_argument("--expect-batteryless-usb-pd-without-dc-c1", action="store_true", help="Claim FX3 supports batteryless USB PD without NP-FZ100 or DC-C1 (invalid)")
            p.add_argument("--dormant-uvc-streaming-requested", action="store_true", help="Request dormant native [USB Streaming] UVC/UAC (_f 0x755b -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-native-uvc-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 exposes native [USB Streaming] UVC/UAC (invalid)")
            p.add_argument("--fx6-native-uvc-present-claimed", action="store_true", help="Claim ILME-FX6 Ver. 6.01 exposes native USB-C UVC/UAC webcam (invalid)")
            p.add_argument("--streaming-protocol", default="DISABLED", help="[Network Streaming] protocol: DISABLED, RTMP, RTMPS, SRT")
            p.add_argument("--movie-rec-during-streaming", default="DISABLE", help="[Movie Rec During Streaming]: ENABLE or DISABLE")
            p.add_argument("--rec-media-dur-hdmi-output", default="ON", help="[Rec. Media dur HDMI Output]: ON or OFF_HDMI_ONLY")
            p.add_argument("--rec-target-slot", type=int, default=2, help="Target recording slot (Slot 1 blocked EROFS=30 on Tier-0 vault)")
            p.add_argument("--e-nd-actuator-tx-count", type=int, default=0, help="e-ND I2C actuator TX count (must remain 0)")
            p.add_argument("--wireless-rf-packets-emitted", type=int, default=0, help="Wireless RF packets emitted (must remain 0)")
            p.add_argument("--usb-packets-transmitted", type=int, default=0, help="USB packets transmitted (must remain 0)")
            p.add_argument("--simulated-passive-tx-bytes", type=int, default=0, help="Simulated passive UART TX bytes emitted (must remain 0)")
            p.add_argument("--simulated-h0-h3-drifted-surfaces", type=int, default=0, help="Simulated H0 vs H3 drifted surfaces (must remain 0)")
            p.add_argument("--claim-hardware-live-attach-authorized", action="store_true", help="Claim live hardware attachment is authorized offline (fail-closed rejection)")
            p.add_argument("--claim-persistent-emmc-writes-authorized", action="store_true", help="Claim persistent eMMC writes are authorized (fail-closed rejection)")
            p.add_argument("--claim-cross-model-flash-authorized", action="store_true", help="Claim cross-model partition flashing is authorized (fail-closed rejection)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 341 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--summary", action="store_true", help="Emit compact one-line summary to stdout even when --json is passed")
            p.add_argument("--sony-help-guide-id", default="ilc/2210", help="Official Sony Help Guide identifier (must remain ilc/2210)")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--exposure-mode", default="MANUAL_EXPOSURE", help="[Exposure Mode]: PROGRAM_AUTO, APERTURE_PRIORITY, SHUTTER_PRIORITY, MANUAL_EXPOSURE, INTELLIGENT_AUTO, FLEXIBLE_EXP, MEMORY_RECALL")
            # Group A (Wave 68 §§1-2)
            p.add_argument("--area-zone", default="AREA_GMT_P_09_0", help="Area timezone from 30 AREA_GMT_* zones (including 6 half-hour zones)")
            p.add_argument("--exposed-area-gmt-zones", default=None, help="Comma-separated 30 AREA_GMT_* zones override")
            p.add_argument("--daylight-savings", default="OFF", help="[Daylight Savings] (0xe917, typo convert_setting_daylight_saving_to_saylight_saving): ON or OFF")
            p.add_argument("--date-format", default="Y_M_D", help="[Date Format] (0x670d): Y_M_D, M_D_Y, D_M_Y")
            p.add_argument("--rtc-backup-charge-hours", type=float, default=24.0, help="Powered-OFF internal RTC charge hours with charged NP-FZ100 (>= 24.0h when uninitialized)")
            p.add_argument("--no-rtc-initialized", dest="rtc_initialized", action="store_false", help="Indicate internal RTC backup battery was depleted/uninitialized")
            p.add_argument("--claimed-user-replaceable-cr2032-present", action="store_true", help="Claim FX3 has a user-replaceable CR2032 coin-cell slot (invalid)")
            p.add_argument("--rtc-discharge-without-24h-charge-claimed", action="store_true", help="Claim depleted internal RTC does not require >=24h powered-OFF charge (invalid)")
            p.add_argument("--claimed-area-date-wiped-by-camera-reset", action="store_true", help="Claim [Area/Date/Time Setting] is wiped by Camera Settings Reset (invalid: Reset-immune)")
            p.add_argument("--claimed-fx6-has-standalone-dst-switch", action="store_true", help="Claim FX6 exposes a standalone Daylight Savings UI switch (invalid)")
            p.add_argument("--expect-area-date-uses-legacy-name-only", action="store_true", help="Claim FX3 Ver. 7.02 ilc/2210 still names menu Date/Time Setup 0xe87f (invalid)")
            p.add_argument("--grid-line-display", default="OFF", help="[Grid Line Display] (0x6f9d): ON or OFF (passes over HDMI when HDMI Info. Display=On)")
            p.add_argument("--grid-line-type", default="RULE_OF_3RDS", help="[Grid Line Type] (0x69c9): RULE_OF_3RDS, SQUARE, DIAG_PLUS_SQUARE")
            p.add_argument("--hdmi-info-display", default="ON", help="[HDMI Info. Display]: ON or OFF")
            p.add_argument("--hdmi-raw-output", default="OFF", help="HDMI [RAW Output]: ON or OFF")
            p.add_argument("--rec-media-dur-hdmi-output", default="ON", help="[Rec. Media dur HDMI Output]: ON or OFF_HDMI_ONLY")
            p.add_argument("--marker-display", default="OFF", help="[Marker Display] (0x6803): ON or OFF (0px over HDMI)")
            p.add_argument("--center-marker", default="OFF", help="[Center Marker]: ON or OFF")
            p.add_argument("--aspect-marker", default="OFF", help="[Aspect Marker] (15 ratios + OFF)")
            p.add_argument("--safety-zone", default="OFF", help="[Safety Zone]: OFF, 80PCT (80%%), 90PCT (90%%)")
            p.add_argument("--guideframe", default="OFF", help="[Guideframe] (0x62f9): ON or OFF")
            p.add_argument("--focus-magnifier-active", action="store_true", help="Indicate Focus Magnifier is active (hides Marker Display)")
            p.add_argument("--expect-marker-outputs-over-hdmi", action="store_true", help="Claim [Marker Display]/[Guideframe] outputs over HDMI (invalid: 0px)")
            p.add_argument("--expect-grid-passes-hdmi-when-info-off-or-raw", action="store_true", help="Claim [Grid Line] overlays HDMI when HDMI Info. Display=Off or RAW Output=On (invalid)")
            p.add_argument("--expect-marker-active-in-still-mode", action="store_true", help="Claim [Marker Display] operates in Still mode (invalid: Movie/S&Q only)")
            p.add_argument("--expect-marker-visible-during-focus-magnifier", action="store_true", help="Claim [Marker Display] stays visible during Focus Magnifier (invalid)")
            p.add_argument("--claimed-grid-or-marker-wiped-by-camera-reset", action="store_true", help="Claim Grid Line or Marker Display is wiped by Camera Settings Reset (invalid: Reset-immune)")
            p.add_argument("--claimed-fx6-has-3mode-static-grid-line-menu", action="store_true", help="Claim FX6 exposes FX3 3-mode static Grid Line menu (invalid)")
            # Group B (Wave 68 §§3-4)
            p.add_argument("--camset-action", default="NONE", help="[Save/Load Settings] (0x6254): NONE, SAVE, LOAD, DELETE")
            p.add_argument("--camset-slot", type=int, default=1, help="[Save/Load Settings] slot (must be locked to Slot 1)")
            p.add_argument("--camset-file-index", type=int, default=1, help="CAMSET file index (1..10 for CAMSET01..CAMSET10.DAT)")
            p.add_argument("--camset-media-type", default="CFEXPRESS_A", help="CAMSET card media type: CFEXPRESS_A, SDXC, SDHC")
            p.add_argument("--camset-card-template", default="%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT", help="CAMSET card path template (must match %%c:%%s/SONY/SETTING/%%s/CAMSET/%%s.DAT)")
            p.add_argument("--camset-fw-version", default="7.02", help="CAMSET file firmware version (<= 1.01 rejected on Load)")
            p.add_argument("--claimed-camset-allows-slot2", action="store_true", help="Claim [Save/Load Settings] allows Slot 2 on FX3 (invalid: Slot 1 only)")
            p.add_argument("--claimed-camset-uses-pro-camera-path", action="store_true", help="Claim FX3 CAMSET uses PRO/CAMERA/*.ALL path (invalid: 0 hits)")
            p.add_argument("--claimed-camset-includes-excluded-items", action="store_true", help="Claim CAMSET includes Copyright/Custom WB/Network/Area/Date (invalid)")
            p.add_argument("--claimed-ftpset-shares-camset-dir", action="store_true", help="Claim [Save/Load FTP Settings] shares CAMSET/ instead of FTPSET/%%s.DAT (invalid)")
            p.add_argument("--campr-action", default="NONE", help="[Camera Set. Memory]: NONE, SAVE, RECALL")
            p.add_argument("--campr-slot", default="M1", help="[Camera Set. Memory] slot: 1..3 (body) or M1..M4 (card CAMPR%%02d%%c.DAT)")
            p.add_argument("--memory-recall-media-slot", type=int, default=2, help="[Memory/Recall Media] slot: 1 or 2")
            p.add_argument("--claimed-campr-includes-custom-key-or-program-shift", action="store_true", help="Claim Camera Set. Memory includes Custom Key/Dial Set. or Program Shift (invalid)")
            p.add_argument("--ftpset-action", default="NONE", help="[Save/Load FTP Settings]: NONE, SAVE, LOAD")
            p.add_argument("--ftpset-slot", type=int, default=2, help="FTPSET slot: 1 or 2")
            p.add_argument("--claimed-fx6-reference-file-present", action="store_true", help="Claim FX6 [Reference File] exists in appFw.so (invalid: 0 hits dormant)")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 recovery vault")
            p.add_argument("--slot1-data-sector-writes", type=int, default=0, help="Slot-1 data sector writes (must remain 0)")
            p.add_argument("--pc-sync-terminal-requested", action="store_true", help="Request FX3 physical PC Flash Sync terminal (0 SYNCHRO_TERMINAL* hits -> EOPNOTSUPP=95)")
            p.add_argument("--claimed-fx3-sync-terminal-present", action="store_true", help="Claim FX3 has a physical PC Flash Sync terminal (invalid)")
            p.add_argument("--no-xlr-h1-attached", dest="xlr_h1_attached", action="store_false", help="Indicate XLR-H1 top handle is detached")
            p.add_argument("--hvl-lbpc-direct-mount-requested", action="store_true", help="Attempt direct mount of HVL-LBPC on XLR-H1 cold shoe or MI Shoe")
            p.add_argument("--video-light-mode", default="POWER_LINK", help="[Video Light Mode] (0x6211): POWER_LINK, REC_LINK, REC_LINK_AND_STBY, AUTO")
            p.add_argument("--mi-shoe-5v-draw-ma", type=int, default=0, help="MI Shoe PMIC 5V draw in mA (<= 900 mA)")
            p.add_argument("--flash-mode", default="OFF", help="[Flash Mode]: OFF, AUTO_FLASH, FILL_FLASH, SLOW_SYNC, REAR_SYNC")
            p.add_argument("--flash-xsync-denominator", type=int, default=250, help="Flash X-Sync ceiling denominator (must be 250 for 1/250 s)")
            p.add_argument("--flash-trigger-voltage-v", type=float, default=0.0, help="Trigger voltage in Volts (must be 0 <= V < 250V)")
            p.add_argument("--claimed-fx6-video-light-has-auto-mode", action="store_true", help="Claim FX6 Technical > Video Light Set exposes Auto mode (invalid: 3 modes only)")
            p.add_argument("--claimed-fx6-genlock-bnc-present", action="store_true", help="Claim FX6 has physical GENLOCK BNC (invalid despite 107 dormant symbols)")
            p.add_argument("--fx6-genlock-requested", action="store_true", help="Request FX6 GENLOCK BNC sync input (invalid: only TC IN/OUT BNC)")
            # Group C (Wave 69 §§1-2)
            p.add_argument("--playback-magnify-requested", action="store_true", help="Trigger Playback [Enlarge Image] (0xe8cb, strictly Still-only)")
            p.add_argument("--playback-media-kind", default="STILL", help="Playback item kind: STILL or MOVIE (MOVIE -> EOPNOTSUPP=95)")
            p.add_argument("--enlarge-initial-mag", default="STANDARD_MAG", help="[Enlarge Initial Mag.] (0x6b6e): STANDARD_MAG or PREVIOUS_MAG")
            p.add_argument("--enlarge-initial-pos", default="FOCUSED_POSITION", help="[Enlarge Initial Position] (0x781f): FOCUSED_POSITION or CENTER")
            p.add_argument("--claimed-playback-magnify-works-on-movies", action="store_true", help="Claim Playback [Enlarge Image] works on movie clips (invalid)")
            p.add_argument("--claimed-playback-magnify-wiped-by-camera-reset", action="store_true", help="Claim Playback [Magnification] settings are wiped by Camera Settings Reset (invalid: Reset-immune)")
            p.add_argument("--claimed-fx6-has-playback-enlarge", action="store_true", help="Claim FX6 exposes Playback still enlarge (invalid)")
            p.add_argument("--anti-flicker-shoot", default="OFF", help="[Anti-flicker Shoot.] (0x623d): ON or OFF (Still mechanical shutter 100/120Hz)")
            p.add_argument("--still-shutter-type", default="MECHANICAL_SHUTTER", help="[Shutter Type]: MECHANICAL_SHUTTER or ELECTRONIC_SHUTTER")
            p.add_argument("--silent-mode", default="OFF", help="[Silent Mode]: ON or OFF")
            p.add_argument("--bulb-enabled", action="store_true", help="Indicate BULB exposure active (locks out Anti-flicker Shoot.)")
            p.add_argument("--claimed-anti-flicker-effective-on-high-freq-led", action="store_true", help="Claim [Anti-flicker Shoot.] handles high-frequency PWM LED flicker (invalid)")
            p.add_argument("--claimed-anti-flicker-shoot-resists-camera-reset", action="store_true", help="Claim [Anti-flicker Shoot.] resists Camera Settings Reset (invalid: Resettable)")
            p.add_argument("--dormant-var-shutter-requested", action="store_true", help="Request dormant [Var. Shutter] (0x6831 -> EOPNOTSUPP=95)")
            p.add_argument("--dormant-anti-flicker-set-requested", action="store_true", help="Request dormant [Anti-flicker Set.] (0x68e7 -> EOPNOTSUPP=95)")
            p.add_argument("--dormant-anti-flicker-tv-scan-requested", action="store_true", help="Request dormant [Anti-flicker Tv Scan] (0x63c0 -> EOPNOTSUPP=95)")
            p.add_argument("--claimed-fx3-var-shutter-present", action="store_true", help="Claim FX3 exposes [Var. Shutter] (invalid: 100%% dormant)")
            p.add_argument("--claimed-fx3-anti-flicker-tv-scan-present", action="store_true", help="Claim FX3 exposes [Anti-flicker Tv Scan] (invalid: 100%% dormant)")
            p.add_argument("--claimed-fx3-anti-flicker-set-present", action="store_true", help="Claim FX3 exposes [Anti-flicker Set.] (invalid: 100%% dormant)")
            p.add_argument("--fx6-ecs-enabled", action="store_true", help="Enable FX6 ECS (Extended Clear Scan 23.99..8000 Hz)")
            p.add_argument("--fx6-ecs-freq-hz", type=float, default=60.0, help="FX6 ECS frequency in Hz (23.99..8000.0)")
            p.add_argument("--claimed-fx6-lacks-ecs", action="store_true", help="Claim FX6 lacks ECS shutter frequency control (invalid)")
            # Group D (Wave 69 §§3-4 + Tier-0)
            p.add_argument("--wifi-sku", default="WW728473", help="Wireless SKU: WW728473 (2.4+5GHz), WW558244 (2.4GHz-only), NONE")
            p.add_argument("--wifi-connect", default="OFF", help="[Wi-Fi Connect]: ON or OFF (bench requires OFF)")
            p.add_argument("--wifi-frequency-band", default="2_4_GHZ", help="[Wi-Fi Frequency Band] (0x66c3): 2_4_GHZ or 5_GHZ")
            p.add_argument("--wifi-security-protocol", default="WPA2_PSK", help="Wi-Fi security: WPA2_PSK, WPA3_SAE, OPEN_MANUAL_AP, NONE (WEP/WPA_PSK/IPSEC removed)")
            p.add_argument("--access-point-set-requested", action="store_true", help="Request [Access Point Set.] (requires [Wi-Fi Connect]=On)")
            p.add_argument("--claimed-ww558244-supports-5ghz", action="store_true", help="Claim WW558244 supports 5 GHz Wi-Fi (invalid)")
            p.add_argument("--claimed-ver700-supports-wep-wpa-ipsec", action="store_true", help="Claim FX3 Ver. 7.00+ retains WEP/WPA-PSK/IPsec (invalid)")
            p.add_argument("--claimed-reset-network-wipes-airplane-mode", action="store_true", help="Claim [Reset Network Set.] wipes [Airplane Mode]=On (invalid)")
            p.add_argument("--claimed-camera-reset-wipes-network", action="store_true", help="Claim [Camera Settings Reset] resets Network menus (invalid)")
            p.add_argument("--claimed-fx6-uses-single-wifi-sku", action="store_true", help="Claim FX6 uses a single Wi-Fi SKU instead of FX6V vs FX6T (invalid)")
            p.add_argument("--airplane-mode", default="ON", help="[Airplane Mode]: ON (mandatory Zero-RF bench) or OFF")
            p.add_argument("--no-rf-nvs-readonly", dest="rf_nvs_p12_p13_readonly", action="store_false", help="Indicate p12/p13 RF NVS is NOT MS_RDONLY (fail-closed rejection)")
            p.add_argument("--rf-nvs-mutation-bytes", type=int, default=0, help="p12/p13 RF NVS mutation bytes (must remain 0)")
            p.add_argument("--claim-rf-nvs-write-authorized", action="store_true", help="Claim p12/p13 RF NVS write is authorized (fail-closed rejection)")
            p.add_argument("--camera-revision", default="ILME_FX3", help="Hardware revision: ILME_FX3 or ILME_FX3A (FX3A removed #5 IR sensor)")
            p.add_argument("--ir-remote-ctrl", default="OFF", help="[IR Remote Ctrl] (0x61a6): ON or OFF (Reset-immune)")
            p.add_argument("--ir-sensor-front-index", type=int, default=5, help="Front sensor index for IR receiver (must be 5, not #8 AF lamp)")
            p.add_argument("--bluetooth-rmt-ctrl", default="OFF", help="[Bluetooth Rmt Ctrl]: ON or OFF (mutually exclusive with IR Remote Ctrl)")
            p.add_argument("--expect-power-save-sleeps-during-ir", action="store_true", help="Claim Power Save triggers while [IR Remote Ctrl]=On (invalid: bypasses Power Save)")
            p.add_argument("--claimed-ir-sensor-is-front-8", action="store_true", help="Claim FX3 IR receiver is front #8 instead of front #5 (invalid)")
            p.add_argument("--claimed-fx3a-keeps-ir-sensor", action="store_true", help="Claim ILME-FX3A retains physical IR remote receiver (invalid)")
            p.add_argument("--claimed-fx3-has-2-5mm-lanc", action="store_true", help="Claim FX3 has 2.5mm LANC terminal like FX6 (invalid)")
            p.add_argument("--ctrl-for-hdmi", default="OFF", help="[CTRL FOR HDMI] (0xe41f, BKID_APP_setting_ctrl_for_hmdi): OFF (mandatory HDMI bench) or ON (factory def)")
            p.add_argument("--no-hdmi-bench-attached", dest="hdmi_bench_attached", action="store_false", help="Indicate no HDMI monitor/switcher bench is attached")
            p.add_argument("--claimed-ctrl-for-hdmi-factory-default-is-off", action="store_true", help="Claim [CTRL FOR HDMI] ships factory-default OFF (invalid: factory default is ON)")
            p.add_argument("--claimed-ir-or-cec-wiped-by-camera-reset", action="store_true", help="Claim [IR Remote Ctrl] or [CTRL FOR HDMI] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-cec-has-rec-key", action="store_true", help="Claim 41 EVENT_INPUT_KEY_CEC_* events include a CEC_REC key (invalid)")
            p.add_argument("--emmc-write-count", type=int, default=0, help="eMMC write count (must remain 0)")
            p.add_argument("--e-nd-actuator-tx-count", type=int, default=0, help="e-ND I2C actuator TX count (must remain 0)")
            p.add_argument("--wireless-rf-packets-emitted", type=int, default=0, help="Wireless RF packets emitted (must remain 0)")
            p.add_argument("--usb-packets-transmitted", type=int, default=0, help="USB packets transmitted (must remain 0)")
            p.add_argument("--simulated-passive-tx-bytes", type=int, default=0, help="Simulated passive UART TX bytes emitted (must remain 0)")
            p.add_argument("--simulated-h0-h3-drifted-surfaces", type=int, default=0, help="Simulated H0 vs H3 drifted surfaces (must remain 0)")
            p.add_argument("--claim-hardware-live-attach-authorized", action="store_true", help="Claim live hardware attachment is authorized offline (fail-closed rejection)")
            p.add_argument("--claim-persistent-emmc-writes-authorized", action="store_true", help="Claim persistent eMMC writes are authorized (fail-closed rejection)")
            p.add_argument("--claim-cross-model-flash-authorized", action="store_true", help="Claim cross-model partition flashing is authorized (fail-closed rejection)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 342 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--summary", action="store_true", help="Emit compact one-line summary to stdout even when --json is passed")
            p.add_argument("--sony-help-guide-id", default="ilc/2210", help="Official Sony Help Guide identifier (must remain ilc/2210)")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--focus-mode", default="MF", help="[Focus Mode]: AF_S, AF_C, DMF, MF")
            p.add_argument("--log-shooting-mode", default="OFF", help="[Log Shooting]: OFF, FLEXIBLE_ISO, CINE_EI_QUICK, CINE_EI")
            # Group A (Wave 70 secs 1-2)
            p.add_argument("--peaking-display", default="OFF", help="[Peaking Display] (0x7615): ON or OFF (Reset-immune; 0px over HDMI)")
            p.add_argument("--peaking-level", default="MID", help="[Peaking Level]: HIGH, MID, LOW (Reset-immune)")
            p.add_argument("--peaking-color", default="WHITE", help="[Peaking Color]: RED, YELLOW, BLUE, WHITE (Reset-immune)")
            p.add_argument("--hdmi-info-display", default="ON", help="[HDMI Info. Display]: ON or OFF")
            p.add_argument("--hdmi-raw-output", default="OFF", help="HDMI [RAW Output]: ON or OFF")
            p.add_argument("--focus-magnifier-active", action="store_true", help="Indicate Focus Magnifier is active (coexists with Peaking)")
            p.add_argument("--expect-peaking-outputs-over-hdmi", action="store_true", help="Claim Peaking outputs over HDMI (invalid: 0px)")
            p.add_argument("--claimed-peaking-blocks-focus-magnifier", action="store_true", help="Claim Peaking disables Focus Magnifier (invalid: coexists)")
            p.add_argument("--claimed-peaking-disabled-in-movie-af", action="store_true", help="Claim Peaking is disabled in Movie AF (invalid: active in MF/AF)")
            p.add_argument("--claimed-peaking-wiped-by-camera-reset", action="store_true", help="Claim Peaking 3 items are wiped by Camera Settings Reset (invalid: Reset-immune)")
            p.add_argument("--in-body-focus-map-requested", action="store_true", help="Request body-dormant Focus Map (EOPNOTSUPP=95; wireless M&C only)")
            p.add_argument("--claimed-fx3-has-in-body-focus-map", action="store_true", help="Claim FX3 renders Focus Map on body LCD/HDMI (invalid)")
            p.add_argument("--claimed-mc-focus-map-works-over-usb", action="store_true", help="Claim Monitor & Control Focus Map works over wired USB (invalid: wireless only)")
            p.add_argument("--fx6-peaking-type-or-freq-requested", action="store_true", help="Request debunked FX6 Peaking Type/Freq menu (0 hits in FX6 appFw.so)")
            p.add_argument("--claimed-fx6-has-peaking-type-or-freq", action="store_true", help="Claim FX6 exposes Peaking Type or Freq menus (invalid myth)")
            p.add_argument("--claimed-fx6-peaking-has-white-not-bw", action="store_true", help="Claim FX6 Peaking Color uses White instead of B&W (invalid)")
            p.add_argument("--exposed-audio-recording-items", default=None, help="Comma-separated exact 5 Resettable [Audio Recording] items override")
            p.add_argument("--audio-recording", default="ON", help="[Audio Recording]: ON or OFF (disabled in S&Q)")
            p.add_argument("--audio-rec-level", type=int, default=26, help="[Audio Rec Level] (0..31, default 26 per adj_audio_rec_level_defult)")
            p.add_argument("--audio-out-timing", default="LIVE", help="[Audio Out Timing]: LIVE or LIP_SYNC")
            p.add_argument("--wind-noise-reduct", default="OFF", help="[Wind Noise Reduct.] (0x6f96): ON or OFF only (NO Auto; internal mic only)")
            p.add_argument("--shoe-audio-set", default="48KHZ_16BIT_2CH", help="[Shoe Audio Set.]: 48KHZ_24BIT_4CH, 48KHZ_24BIT_2CH, 48KHZ_16BIT_2CH")
            p.add_argument("--mic-35mm-inserted", action="store_true", help="Indicate 3.5mm external mic is inserted (bypasses Wind Noise Reduct.)")
            p.add_argument("--no-xlr-h1-attached", dest="xlr_h1_attached", action="store_false", help="Indicate XLR-H1 top handle is detached")
            p.add_argument("--xlr-h1-handle-audio", default="OFF", help="XLR-H1 HANDLE AUDIO switch: ON or OFF (ON bypasses Wind Noise Reduct.)")
            p.add_argument("--mi-shoe-mic-attached", action="store_true", help="Indicate MI Shoe digital mic is attached (bypasses Wind Noise Reduct.)")
            p.add_argument("--dormant-audio-level-display-requested", action="store_true", help="Request Ver. 2.00+ removed [Audio Level Display] (0x7a36 -> EOPNOTSUPP=95)")
            p.add_argument("--claimed-fx3-has-audio-level-display-menu", action="store_true", help="Claim FX3 Ver. 7.02 retains standalone [Audio Level Display] menu (invalid)")
            p.add_argument("--claimed-audio-recording-resists-camera-reset", action="store_true", help="Claim [Audio Recording] 5 items resist Camera Settings Reset (invalid: all 5 Resettable)")
            p.add_argument("--claimed-audio-out-timing-under-setup-sound-option", action="store_true", help="Claim [Audio Out Timing] lives under Setup -> Sound Option (invalid)")
            p.add_argument("--fx3-disable-builtin-limiter-requested", action="store_true", help="Attempt disabling non-disableable FX3 built-in audio limiter (rejected)")
            p.add_argument("--dormant-wind-noise-auto-requested", action="store_true", help="Request dormant [Wind Noise Reduct.]=Auto (EOPNOTSUPP=95)")
            p.add_argument("--claimed-fx3-wind-noise-has-auto", action="store_true", help="Claim FX3 [Wind Noise Reduct.] has Auto mode like consumer Alpha bodies (invalid)")
            p.add_argument("--expect-wind-noise-applies-to-external-mic", action="store_true", help="Claim [Wind Noise Reduct.] filters 3.5mm/XLR-H1/MI Shoe mics (invalid)")
            p.add_argument("--expect-wind-noise-active-in-sq", action="store_true", help="Claim [Wind Noise Reduct.] works in S&Q Motion (invalid)")
            p.add_argument("--claimed-fx6-handle-has-physical-low-cut-switch", action="store_true", help="Claim FX6 Smart Handle has physical LOW CUT hardware switches like XLR-H1 (invalid)")
            p.add_argument("--claimed-fx3-has-fx6-6step-limiter", action="store_true", help="Claim FX3 exposes FX6 6-step Limiter Mode (invalid)")
            # Group B (Wave 70 secs 3-4)
            p.add_argument("--usb-power-supply", default="ON", help="[USB Power Supply] (0x785b): ON or OFF (Reset-immune)")
            p.add_argument("--usb-power-terminal", default="USB_TYPE_C", help="USB power terminal: USB_TYPE_C or MULTI_MICRO_USB (Multi blocked)")
            p.add_argument("--camera-power-state", default="ON", help="Camera power state: ON or OFF (NO battery charging while ON)")
            p.add_argument("--no-usb-pd-supply-active", dest="usb_pd_supply_active", action="store_false", help="Indicate USB PD external power is disconnected")
            p.add_argument("--usb-pd-watts", type=float, default=27.0, help="USB Type-C PD negotiated wattage (recommend >= 27W 9V/3A; >= 65W for DC-C1)")
            p.add_argument("--usb-c-cable-amps", type=int, default=3, help="USB Type-C cable e-marker current rating in Amps (5A required for DC-C1)")
            p.add_argument("--no-np-fz100-inserted", dest="np_fz100_inserted", action="store_false", help="Indicate NP-FZ100 battery is removed (blocked by libUsbBusPower.so!)")
            p.add_argument("--battery-soc-pct", type=int, default=85, help="NP-FZ100 battery SoC percentage (0..100%%)")
            p.add_argument("--dc-c1-coupler-attached", action="store_true", help="Indicate Sony DC-C1 DC Coupler is installed (requires >= 65W PD + 5A cable)")
            p.add_argument("--charge-led-active-while-on", action="store_true", help="Simulate amber CHARGE LED active while camera power is ON (invalid)")
            p.add_argument("--expect-battery-charges-while-camera-on", action="store_true", help="Claim NP-FZ100 charges while camera is powered ON (invalid)")
            p.add_argument("--claimed-multi-micro-usb-powers-camera", action="store_true", help="Claim Multi/Micro USB terminal supplies camera operating power (invalid)")
            p.add_argument("--claimed-fx3-supports-batteryless-usb-pd-boot", action="store_true", help="Claim FX3 boots via USB PD without an inserted NP-FZ100 (invalid)")
            p.add_argument("--claimed-np-fz100-hot-swap-under-usb-pd", action="store_true", help="Claim NP-FZ100 can be hot-swapped under USB PD without power loss (invalid)")
            p.add_argument("--claimed-usb-power-supply-wiped-by-camera-reset", action="store_true", help="Claim Reset-immune [USB Power Supply] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx6-dc-in-volts", type=float, default=19.5, help="FX6 EIAJ RC-5320A DC IN voltage (19.5V nominal)")
            p.add_argument("--fx6-dc-in-hot-replug-during-rec", action="store_true", help="Attempt FX6 DC IN hot-replug during active REC (instant power cut hazard!)")
            p.add_argument("--claimed-fx6-usb-c-powers-body", action="store_true", help="Claim FX6 USB Type-C powers body operation or charging (invalid)")
            p.add_argument("--claimed-fx6-lacks-batteryless-dc-in-boot", action="store_true", help="Claim FX6 cannot boot battery-less from 19.5V EIAJ DC IN (invalid)")
            p.add_argument("--ntsc-pal-sku", default="CE", help="[NTSC/PAL Selector] regional SKU: CE, E33, U2, J1")
            p.add_argument("--video-system", default="PAL", help="Video system: NTSC or PAL (J1 locked to NTSC)")
            p.add_argument("--ntsc-pal-switch-requested", action="store_true", help="Simulate executing [NTSC/PAL Selector] switch (requires reboot)")
            p.add_argument("--no-ntsc-pal-reboot-acknowledged", dest="ntsc_pal_reboot_acknowledged", action="store_false", help="Indicate NTSC/PAL switch reboot was NOT acknowledged")
            p.add_argument("--ntsc-pal-avf-info-write-requested", action="store_true", help="Trigger post-switch AVF_INFO Create? database write (blocked on Slot 1 EROFS=30)")
            p.add_argument("--ntsc-pal-avf-target-slot", type=int, default=2, help="Target slot for AVF_INFO Create? after NTSC/PAL switch (Slot 1 blocked)")
            p.add_argument("--slot1-format-requested", action="store_true", help="Attempt formatting Slot 1 Tier-0 recovery vault (HARD NO-GO EROFS=30)")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 recovery vault")
            p.add_argument("--slot1-data-sector-writes", type=int, default=0, help="Slot-1 data sector writes (must remain 0)")
            p.add_argument("--claimed-j1-supports-pal-selector", action="store_true", help="Claim J1 domestic SKU exposes [NTSC/PAL Selector] PAL option (invalid)")
            p.add_argument("--expect-non-default-system-lacks-banner", action="store_true", help="Claim non-default NTSC/PAL boot omits Running on NTSC./PAL. banner (invalid)")
            p.add_argument("--claimed-xavc-requires-mandatory-card-format", action="store_true", help="Claim switching XAVC NTSC/PAL forces mandatory card Format instead of AVF_INFO Create? (invalid)")
            p.add_argument("--expect-cross-system-playback-allowed", action="store_true", help="Claim NTSC clips play under PAL without warning/filter (invalid)")
            p.add_argument("--claimed-ntsc-pal-wiped-by-camera-reset", action="store_true", help="Claim Reset-immune [NTSC/PAL Selector] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-fx6-shows-running-on-ntsc-pal-banner", action="store_true", help="Claim FX6 displays FX3 Running on NTSC./PAL. power-on banner (invalid)")
            p.add_argument("--claimed-fx6-thumbnail-shows-all-freq-simultaneously", action="store_true", help="Claim FX6 Thumbnail displays clips from other System Frequencies simultaneously (invalid)")
            # Group C (Wave 71 secs 1-2)
            p.add_argument("--apsc-s35-shooting", default="OFF", help="[APS-C S35 Shooting]: ON, AUTO, or OFF")
            p.add_argument("--dormant-anti-dust-function-requested", action="store_true", help="Request dormant [Anti-Dust Function] 0x7495 (0 hits -> EOPNOTSUPP=95)")
            p.add_argument("--dormant-shutter-when-pwr-off-requested", action="store_true", help="Request dormant [Shutter When Pwr OFF] 0x709f ALCIN_UUD (EOPNOTSUPP=95)")
            p.add_argument("--claimed-fx3-shutter-when-pwr-off-present", action="store_true", help="Claim FX3 Ver. 7.02 exposes [Shutter When Pwr OFF] (invalid)")
            p.add_argument("--claimed-fx3-shutter-closes-on-power-off", action="store_true", help="Claim FX3 mechanical shutter closes on power-off (invalid: parks OPEN)")
            p.add_argument("--sensor-cleaning-requested", action="store_true", help="Execute Setup -> [Sensor Cleaning] (>= 51%% SOC + mandatory power OFF)")
            p.add_argument("--no-sensor-cleaning-power-off-completed", dest="sensor_cleaning_power_off_completed", action="store_false", help="Indicate post-[Sensor Cleaning] mandatory power OFF was skipped")
            p.add_argument("--claimed-fx6-has-shutter-when-pwr-off-or-ibis-cleaning", action="store_true", help="Claim FX6 has [Shutter When Pwr OFF] or IBIS ultrasonic [Sensor Cleaning] (invalid)")
            p.add_argument("--claimed-fx3-has-e-nd-or-apr", action="store_true", help="Claim FX3 has FX6 sealed e-ND optical filter or Technical > APR (invalid)")
            p.add_argument("--exposed-focus-assistant-items", default=None, help="Comma-separated exact 5 Reset-immune [Focus Assistant] items override")
            p.add_argument("--focus-magnif-time", default="NO_LIMIT", help="[Focus Magnif. Time]: 2_SEC, 5_SEC, NO_LIMIT (Reset-immune)")
            p.add_argument("--initial-focus-mag-x", type=float, default=1.0, help="[Initial Focus Mag.] (Still 1.0/4.0, Movie 1.0/4.0)")
            p.add_argument("--requested-focus-mag-x", type=float, default=1.0, help="Requested Focus Magnifier cycle step (FF 1.0/2.1/4.1, APS-C 1.0/1.5/3.0, Movie 1.0/4.0)")
            p.add_argument("--af-in-focus-mag", default="ON", help="[AF in Focus Mag.]: ON or OFF (Still-only)")
            p.add_argument("--auto-magnifier-in-mf", default="ON", help="[Auto Magnifier in MF]: ON or OFF (Still-only)")
            p.add_argument("--dormant-high-mp-focus-mag-scale-requested", action="store_true", help="Request dormant high-MP 5.3x/6.2x/8.3x/16.5x Focus Mag scales (EOPNOTSUPP=95)")
            p.add_argument("--expect-af-in-focus-mag-or-auto-mag-in-movie", action="store_true", help="Claim [AF in Focus Mag.] or [Auto Magnifier in MF] operates in Movie/S&Q (invalid: Still-only)")
            p.add_argument("--claimed-movie-rec-cancels-focus-mag", action="store_true", help="Claim pressing REC cancels active Movie Focus Magnifier (invalid: persists during REC)")
            p.add_argument("--expect-focus-mag-crops-hdmi-or-internal-rec", action="store_true", help="Claim Focus Magnifier zoom crops Clean HDMI output or internal XAVC clip (invalid)")
            p.add_argument("--claimed-focus-assistant-wiped-by-camera-reset", action="store_true", help="Claim Reset-immune [Focus Assistant] 5 items are wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-fx6-hdmi-focus-mag-is-3x-6x", action="store_true", help="Claim FX6 Ver. 6.0+ HDMI Focus Magnifier outputs x3/x6 instead of x2/x4 (invalid)")
            p.add_argument("--claimed-fx6-vf-focus-mag-is-2-1x-4-1x", action="store_true", help="Claim FX6 VF Focus Magnifier uses FX3 x2.1/x4.1 instead of x3/x6 (invalid)")
            # Group D (Wave 71 secs 3-4 + Tier-0)
            p.add_argument("--exp-std-adjust-metering-mode", default="MULTI", help="[Exposure Std. Adjust] metering mode: MULTI, CENTER, SPOT, ENTIRE_SCR_AVG, HIGHLIGHT")
            p.add_argument("--exp-std-adjust-sixths", type=int, default=0, help="[Exposure Std. Adjust] offset in 1/6 EV sixths (-6..+6 == -1.0..+1.0 EV, Reset-immune trap!)")
            p.add_argument("--exp-std-nonzero-acknowledged", action="store_true", help="Acknowledge non-zero [Exposure Std. Adjust] operator calibration offset")
            p.add_argument("--dormant-1-8-ev-step-requested", action="store_true", help="Request dormant 1/8 EV calibration step (0 hits -> EOPNOTSUPP=95)")
            p.add_argument("--expect-exp-std-adjust-modifies-exif-bias", action="store_true", help="Claim [Exposure Std. Adjust] writes ExposureBiasValue EXIF tag (invalid: M.M. 0 shift only)")
            p.add_argument("--expect-exp-std-changes-cine-ei-iso", action="store_true", help="Claim [Exposure Std. Adjust] shifts locked Cine EI Base ISO (invalid)")
            p.add_argument("--claimed-exp-std-adjust-wiped-by-camera-reset", action="store_true", help="Claim Reset-immune [Exposure Std. Adjust] is cleared by Camera Settings Reset (invalid: Reset-immune trap!)")
            p.add_argument("--claimed-exp-std-adjust-resets-exposure-comp", action="store_true", help="Claim changing [Exposure Std. Adjust] auto-zeros Exposure Comp. dial (invalid)")
            p.add_argument("--fx6-ae-level-ev", type=float, default=0.0, help="FX6 Auto Exposure > Level target EV (-3.0..+3.0 in 0.25 step, 25 steps)")
            p.add_argument("--claimed-fx6-ae-level-limited-to-2ev", action="store_true", help="Claim debunked FX6 Auto Exposure > Level is capped at +/-2.0 EV (invalid myth: -3.0..+3.0 EV)")
            p.add_argument("--usb-connection-mode", default="SEL_WHEN_CONNECT", help="[USB Connection Mode]: SEL_WHEN_CONNECT, MASS_STORAGE, MTP, REMOTE_SHOOTING, USB_STREAMING")
            p.add_argument("--usb-lun-setting", default="MULTI", help="[USB LUN Setting]: MULTI or SINGLE (SINGLE mounts Slot 1 ONLY!)")
            p.add_argument("--usb-lan-tethering", default="OFF", help="Wired smartphone [USB-LAN/Tethering]: ON or OFF")
            p.add_argument("--usb-lan-cnct-launch", default="OFF", help="[USB-LAN Cnct Launch]: ON or OFF")
            p.add_argument("--usb-lan-service", default="NONE", help="Active USB-LAN network service: NONE, RTMP, RTMPS, SRT, FTP, MONITOR_AND_CONTROL")
            p.add_argument("--airplane-mode", default="ON", help="[Airplane Mode]: ON (mandatory Zero-RF) or OFF")
            p.add_argument("--dual-usb-typec-and-multi-simultaneous", action="store_true", help="Attempt simultaneous USB Type-C + Multi/Micro USB connection (blocked)")
            p.add_argument("--slot1-host-usb-write-requested", action="store_true", help="Attempt host write via MTP/MSC onto Slot 1 Tier-0 vault (blocked EROFS=30 + usbgmscif_setReadOnly)")
            p.add_argument("--claimed-airplane-mode-blocks-usb-lan", action="store_true", help="Claim [Airplane Mode]=On blocks wired USB-LAN tethering RTMP/SRT/FTP (invalid: works Zero-RF!)")
            p.add_argument("--claimed-creators-app-allows-guided-live-over-usb", action="store_true", help="Claim Creators' App supports full live guided workflow over wired USB-LAN (invalid)")
            p.add_argument("--claimed-usb-streaming-uvc-active-on-fx3", action="store_true", help="Claim USB Streaming UVC/UAC runs active on FX3 Ver. 7.02 (invalid: dormant usb_f_uvc.ko)")
            p.add_argument("--claimed-reset-network-preserves-airplane-mode", action="store_true", help="Claim [Reset Network Set.] keeps [Airplane Mode]=On without rebooting to OFF (invalid)")
            p.add_argument("--claimed-camera-reset-wipes-usb-tethering", action="store_true", help="Claim Camera Settings Reset wipes Network [USB-LAN/Tethering] (invalid: Reset Network Set. / Initialize only)")
            p.add_argument("--claimed-fx3-links-cusbgadgetiap", action="store_true", help="Claim FX3 links Apple iAP2 CUsbGadgetIAP / usbg_iap.ko (invalid: 0 hits)")
            p.add_argument("--claimed-fx6-lacks-cusbgadgetiap", action="store_true", help="Claim FX6 lacks usbg_iap.ko / CUsbGadgetIAP (invalid)")
            p.add_argument("--emmc-write-count", type=int, default=0, help="Persistent eMMC write count (must remain 0)")
            p.add_argument("--e-nd-actuator-tx-count", type=int, default=0, help="e-ND I2C actuator TX count (must remain 0)")
            p.add_argument("--wireless-rf-packets-emitted", type=int, default=0, help="Wireless RF packets emitted (must remain 0)")
            p.add_argument("--usb-packets-transmitted", type=int, default=0, help="USB packets transmitted (must remain 0)")
            p.add_argument("--simulated-passive-tx-bytes", type=int, default=0, help="Simulated passive UART TX bytes emitted (must remain 0)")
            p.add_argument("--simulated-h0-h3-drifted-surfaces", type=int, default=0, help="Simulated H0 vs H3 drifted surfaces (must remain 0)")
            p.add_argument("--claim-hardware-live-attach-authorized", action="store_true", help="Claim live hardware attachment is authorized offline (fail-closed rejection)")
            p.add_argument("--claim-persistent-emmc-writes-authorized", action="store_true", help="Claim persistent eMMC writes are authorized (fail-closed rejection)")
            p.add_argument("--claim-cross-model-flash-authorized", action="store_true", help="Claim cross-model partition flashing is authorized (fail-closed rejection)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 338 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--summary", action="store_true", help="Emit compact one-line summary to stdout even when --json is passed")
            p.add_argument("--sony-help-guide-id", default="ilc/2210", help="Official Sony Help Guide identifier (must remain ilc/2210)")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--shoot-mode", default="PHOTO", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--exposure-mode", default="MANUAL_EXPOSURE", help="[Exposure Mode]: PROGRAM_AUTO, APERTURE_PRIORITY, SHUTTER_PRIORITY, MANUAL_EXPOSURE, INTELLIGENT_AUTO, FLEXIBLE_EXP")
            # Group A (Wave 66 §§1-2)
            p.add_argument("--drive-mode", default="SINGLE_SHOOTING", help="Still [Drive Mode] (0x7228): SINGLE_SHOOTING, CONT_SHOOTING, SELF_TIMER_SINGLE, SELF_TIMER_CONT, CONT_BRACKET, SINGLE_BRACKET, WB_BRACKET, DRO_BRACKET")
            p.add_argument("--cont-speed-tier", default="HI_PLUS", help="[Cont. Shooting] speed tier: HI_PLUS (10fps), HI (8fps), MID (6fps), LO (3fps)")
            p.add_argument("--aperture-f-number", type=float, default=2.8, help="Aperture F-number (> F11 locks AF on 1st frame in Hi+/Hi/Mid)")
            p.add_argument("--still-file-format", default="RAW", help="Still [File Format]: RAW, RAW_AND_JPEG, RAW_AND_HEIF, JPEG, HEIF")
            p.add_argument("--raw-file-type", default="COMPRESSED", help="[RAW File Type]: COMPRESSED or UNCOMPRESSED")
            p.add_argument("--flash-enabled", action="store_true", help="Enable Flash firing (drops burst rate & locked out on Electronic Shutter)")
            p.add_argument("--self-timer-sec", type=int, default=10, help="Self-timer seconds: 10, 5, or 2")
            p.add_argument("--self-timer-cont-images", type=int, default=3, help="Self-timer(Cont) image count: 3 or 5")
            p.add_argument("--hlg-still-image", default="OFF", help="[HLG Still Image]: ON or OFF")
            p.add_argument("--picture-profile", default="OFF", help="[Picture Profile]: OFF, PP1..PP11, PPLUT1..4")
            p.add_argument("--log-shooting-mode", default="OFF", help="[Log Shooting]: OFF, FLEXIBLE_ISO, CINE_EI_QUICK, CINE_EI")
            p.add_argument("--interval-shutter-type", default="ELECTRONIC_SHUTTER", help="[Interval Shoot Func.] Shutter Type in Interval: ELECTRONIC_SHUTTER (def) or MECHANICAL_SHUTTER")
            p.add_argument("--expect-af-tracks-all-frames-above-f11", action="store_true", help="Claim AF tracks every frame above F11 in Cont. Shooting Hi+/Hi/Mid (invalid)")
            p.add_argument("--expect-full-cont-fps-with-uncompressed-raw-or-flash", action="store_true", help="Claim Uncompressed RAW or Flash maintains full Hi+ 10fps burst speed (invalid)")
            p.add_argument("--claimed-drive-mode-active-in-movie-or-sq", action="store_true", help="Claim Still [Drive Mode] operates in Movie or S&Q mode (invalid: EOPNOTSUPP=95)")
            p.add_argument("--claimed-drive-mode-resists-camera-reset", action="store_true", help="Claim [Drive Mode] resists Camera Settings Reset (invalid: Resettable)")
            p.add_argument("--claimed-interval-default-mech-shutter", action="store_true", help="Claim [Shutter Type in Interval] defaults to Mechanical Shutter (invalid: Electronic)")
            p.add_argument("--fx6-has-still-drive-mode-menu-claimed", action="store_true", help="Claim ILME-FX6 exposes Still [Drive Mode] menu (invalid)")
            p.add_argument("--dormant-focus-bracket-requested", action="store_true", help="Request 100%% dormant [Focus Bracket] (0x7563/0x6915 -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-focus-bracket-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 exposes [Focus Bracket] in user menus (invalid)")
            p.add_argument("--fx6-focus-bracket-present-claimed", action="store_true", help="Claim FX6 Ver. 6.01 exposes [Focus Bracket] in user menus (invalid)")
            p.add_argument("--claimed-focus-bracket-in-ilc2210", action="store_true", help="Claim Sony ilc/2210 Help Guide documents [Focus Bracket] (invalid: 0 hits)")
            p.add_argument("--shutter-type", default="MECHANICAL_SHUTTER", help="[Shutter Type] (0x63db): MECHANICAL_SHUTTER or ELECTRONIC_SHUTTER (NO Auto)")
            p.add_argument("--silent-mode", default="OFF", help="[Silent Mode]: ON or OFF")
            p.add_argument("--dormant-shutter-type-auto-requested", action="store_true", help="Request dormant [Shutter Type]=Auto (0x66b8 -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-shutter-type-auto-present-claimed", action="store_true", help="Claim FX3 exposes 3-option [Shutter Type] with Auto (invalid)")
            p.add_argument("--flash-sync-denominator", type=int, default=250, help="Flash X-Sync denominator (FX3 single ceiling is 250 for 1/250 s)")
            p.add_argument("--claimed-1-320-xsync-supported", action="store_true", help="Claim FX3 supports 1/320 s APS-C flash X-Sync (invalid: 0 hits)")
            p.add_argument("--e-front-curtain-shutter", default="ON", help="[e-Front Curtain Shut.] (0x64c6, BKID_APP_setting_front_curtaion_shutter): ON or OFF (Reset-immune)")
            p.add_argument("--efcs-active-claimed", action="store_true", help="Claim [e-Front Curtain Shut.] remains active under Electronic Shutter or Silent Mode=ON (invalid)")
            p.add_argument("--claimed-efcs-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [e-Front Curtain Shut.] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--long-exposure-nr", default="ON", help="[Long Exposure NR] (0x6465): ON or OFF (Resettable, active >= 1 s)")
            p.add_argument("--shutter-seconds", type=float, default=0.01, help="Exposure shutter duration in seconds (>= 1.0 triggers Long Exposure NR)")
            p.add_argument("--bulb-enabled", action="store_true", help="Enable Still BULB exposure (locked out under Electronic Shutter / Silent Mode)")
            p.add_argument("--anti-flicker-shoot", action="store_true", help="Enable [Anti-flicker Shoot.] (locked out under Electronic Shutter / Silent Mode)")
            p.add_argument("--claimed-long-exp-nr-active-below-1s", action="store_true", help="Claim [Long Exposure NR] triggers on shutter speeds < 1 s (invalid)")
            p.add_argument("--claimed-long-exp-nr-resists-reset", action="store_true", help="Claim [Long Exposure NR] resists Camera Settings Reset (invalid)")
            p.add_argument("--high-iso-nr", default="NORMAL", help="[High ISO NR] (0x650b): NORMAL, LOW, OFF (Resettable)")
            p.add_argument("--expect-high-iso-nr-modifies-arw-raw", action="store_true", help="Claim [High ISO NR] modifies .ARW RAW sensor data (invalid: JPEG/HEIF only)")
            p.add_argument("--dormant-high-iso-nr-high-option-requested", action="store_true", help="Request dormant [High ISO NR]=HIGH ELF enum (invalid)")
            p.add_argument("--claimed-high-iso-nr-resists-reset", action="store_true", help="Claim [High ISO NR] resists Camera Settings Reset (invalid)")
            p.add_argument("--fx6-noise-suppression-uses-still-nr-menu-claimed", action="store_true", help="Claim FX6 uses Still Long Exp/High ISO NR instead of Noise Suppression & APR (invalid)")
            # Group B (Wave 66 §§3-4)
            p.add_argument("--creative-look-shoot-mode", default=None, help="Optional [Creative Look] mode override: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--creative-look-slot", default="ST", help="[Creative Look] (0x6823): ST..SE (10 presets) or CUSTOM_1..CUSTOM_6 (look0..look15)")
            p.add_argument("--creative-look-contrast", type=int, default=0, help="[Creative Look] Contrast (-9..+9)")
            p.add_argument("--creative-look-highlights", type=int, default=0, help="[Creative Look] Highlights (-9..+9)")
            p.add_argument("--creative-look-shadows", type=int, default=0, help="[Creative Look] Shadows (-9..+9)")
            p.add_argument("--creative-look-fade", type=int, default=0, help="[Creative Look] Fade (asymmetric 0..9)")
            p.add_argument("--creative-look-saturation", type=int, default=0, help="[Creative Look] Saturation (-9..+9; locked on BW/SE)")
            p.add_argument("--creative-look-sharpness", type=int, default=0, help="[Creative Look] Sharpness (asymmetric 0..9)")
            p.add_argument("--creative-look-sharpness-range", type=int, default=3, help="[Creative Look] Sharpness Range (1..5; locked in Movie/S&Q)")
            p.add_argument("--creative-look-clarity", type=int, default=0, help="[Creative Look] Clarity (asymmetric 0..9)")
            p.add_argument("--creative-look-saturation-adjusted", action="store_true", help="Indicate Saturation was adjusted (blocked on BW/SE)")
            p.add_argument("--creative-look-sharpness-range-adjusted", action="store_true", help="Indicate Sharpness Range was adjusted (blocked in Movie/S&Q)")
            p.add_argument("--expect-creative-look-active-under-pp-log-hlg-iauto", action="store_true", help="Claim [Creative Look] remains active instead of [-] under PP!=Off, Log!=Off, HLG Still=On, or iAuto (invalid)")
            p.add_argument("--claimed-creative-look-fade-sharpness-clarity-accept-negative", action="store_true", help="Claim Fade/Sharpness/Clarity support -9..+9 negative values (invalid: 0..9)")
            p.add_argument("--claimed-creative-look-resists-camera-reset", action="store_true", help="Claim [Creative Look] resists Camera Settings Reset (invalid)")
            p.add_argument("--dormant-soft-skin-requested", action="store_true", help="Request dormant [Soft Skin Effect] (0x76d9 -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-soft-skin-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 exposes [Soft Skin Effect] (invalid)")
            p.add_argument("--fx6-soft-skin-present-claimed", action="store_true", help="Claim FX6 Ver. 6.01 exposes [Soft Skin Effect] (invalid)")
            p.add_argument("--delete-scope", default="THIS_IMAGE", help="Playback [Delete] (0xe504) scope: THIS_IMAGE, ALL_OTHER_IMAGES, MULTIPLE_IMAGES, ALL_IN_THIS_FOLDER, ALL_WITH_THIS_DATE")
            p.add_argument("--delete-confirm", default="CANCEL_FIRST", help="[Delete confirm.]: CANCEL_FIRST or DELETE_FIRST (Reset-immune)")
            p.add_argument("--delete-pressing-twice", default="OFF", help="[Delete pressing twice]: ON or OFF (Reset-immune)")
            p.add_argument("--protect-scope", default="THIS_IMAGE", help="Playback [Protect] (0xe2c9) scope")
            p.add_argument("--delete-write-requested", action="store_true", help="Simulate Playback [Delete] write operation")
            p.add_argument("--delete-write-slot", type=int, default=2, help="Target slot for [Delete] (Slot 1 blocked EROFS=30)")
            p.add_argument("--protect-write-requested", action="store_true", help="Simulate Playback [Protect] write operation")
            p.add_argument("--protect-write-slot", type=int, default=2, help="Target slot for [Protect] (Slot 1 blocked EROFS=30)")
            p.add_argument("--protected-item-delete-attempted", action="store_true", help="Attempt deleting protected files via [Delete] without [Format] (rejected)")
            p.add_argument("--slot-format-executed", action="store_true", help="Indicate [Format] executed (only Format deletes protected files)")
            p.add_argument("--claimed-delete-confirm-wiped-by-camera-reset", action="store_true", help="Claim [Delete confirm.] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-delete-twice-wiped-by-camera-reset", action="store_true", help="Claim [Delete pressing twice] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--expect-copy-preserves-protect", action="store_true", help="Claim Playback [Copy] preserves [Protect] status (invalid)")
            p.add_argument("--recover-image-db-requested", action="store_true", help="Request [Recover Image DB] (0x711b AVF_INFO rewrite; Slot 1 blocked EROFS=30)")
            p.add_argument("--recover-image-db-slot", type=int, default=2, help="Target slot for [Recover Image DB] (Slot 1 blocked EROFS=30)")
            p.add_argument("--battery-soc-pct", type=int, default=85, help="NP-FZ100 battery state-of-charge percentage (0..100%%)")
            p.add_argument("--low-battery-warning", action="store_true", help="Indicate low battery warning active (blocks Recover Image DB / Pixel Mapping)")
            p.add_argument("--claimed-recover-db-wiped-by-reset-or-init", action="store_true", help="Claim [Recover Image DB] AVF_INFO DB repair is undone by Reset or Initialize (invalid)")
            p.add_argument("--claimed-display-media-info-mutates-media", action="store_true", help="Claim [Display Media Info.] mutates media (invalid: read-only)")
            p.add_argument("--claimed-display-media-info-cap-not-40000", action="store_true", help="Claim [Display Media Info.] still cap differs from 40,000 (invalid)")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 recovery vault")
            p.add_argument("--slot1-data-sector-writes", type=int, default=0, help="Slot-1 data sector writes (must remain 0)")
            # Group C (Wave 67 §§1-2)
            p.add_argument("--auto-pixel-mapping", default="ON", help="Setup -> [Setup Option] -> [Auto Pixel Mapping] (0x7734): ON or OFF (Reset-immune)")
            p.add_argument("--days-since-pixel-mapping", type=int, default=1, help="Days since last Pixel Mapping (>3 triggers advisory when Auto=OFF)")
            p.add_argument("--manual-pixel-mapping-requested", action="store_true", help="Execute manual [Pixel Mapping] (0x61f7; lens cap + battery + mandatory reboot)")
            p.add_argument("--no-lens-cap-attached", dest="lens_cap_attached", action="store_false", help="Indicate lens cap is NOT attached (blocks Pixel Mapping)")
            p.add_argument("--expect-manual-pm-without-reboot", action="store_true", help="Claim manual [Pixel Mapping] completes without camera reboot (invalid)")
            p.add_argument("--claimed-auto-pm-wiped-by-camera-reset", action="store_true", help="Claim Setup -> [Auto Pixel Mapping] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-usb-streaming-blocks-pixel-mapping-prm-haita", action="store_true", help="Claim appFw.so documents a USB/streaming PRM_HAITA block table for Pixel Mapping (invalid)")
            p.add_argument("--no-tier0-dump-active", dest="tier0_dump_active", action="store_false", help="Indicate Tier-0 dump session is NOT active")
            p.add_argument("--unguarded-pm-calibration", action="store_true", help="Attempt unguarded Pixel Mapping calibration during active Tier-0 dump (blocked)")
            p.add_argument("--silent-auto-pixel-mapping", default="OFF", help="Silent Mode -> Target Function Settings -> [Auto Pixel Mapping]: OFF (def, Resettable) or ON")
            p.add_argument("--expect-zero-shutter-sound-with-silent-auto-pm-on", action="store_true", help="Claim Silent Mode + Target [Auto Pixel Mapping]=ON suppresses shutdown mechanical shutter click (invalid)")
            p.add_argument("--claimed-silent-auto-pm-resists-camera-reset", action="store_true", help="Claim Silent Mode Target [Auto Pixel Mapping] resists Camera Settings Reset (invalid)")
            p.add_argument("--fx6-uses-setup-auto-pixel-mapping-instead-of-apr-claimed", action="store_true", help="Claim FX6 uses Setup -> Auto Pixel Mapping instead of Technical > APR (invalid)")
            p.add_argument("--fx6-auto-black-balance-menu-present-claimed", action="store_true", help="Claim FX6 exposes CMOS auto_black_balance menu item (invalid)")
            p.add_argument("--exposed-monitor-items", default=None, help="Comma-separated Setup -> [Monitor] 3 items override")
            p.add_argument("--monitor-brightness-mode", default="MANUAL", help="[Monitor Brightness]: MANUAL or SUNNY_WEATHER")
            p.add_argument("--monitor-brightness-level", type=int, default=0, help="[Monitor Brightness] Manual level (-2..+2)")
            p.add_argument("--display-quality", default="STANDARD", help="[Display Quality]: STANDARD or HIGH (thermal clamp High->Standard)")
            p.add_argument("--body-temp-elevated", action="store_true", help="Simulate elevated body temperature triggering Display Quality thermal clamp")
            p.add_argument("--expect-high-display-quality-unclamped-under-thermal", action="store_true", help="Claim [Display Quality]=HIGH stays unclamped under elevated body temperature (invalid)")
            p.add_argument("--monitor-flip-direction", default="AUTO", help="[Monitor Flip Direction]: AUTO, HORIZONTAL_FLIP, DEGREE_180_FLIP, NO_FLIP")
            p.add_argument("--claimed-monitor-3items-wiped-by-camera-reset", action="store_true", help="Claim Reset-immune Setup -> [Monitor] 3 items are wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-bright-monitoring-in-setup-monitor", action="store_true", help="Claim [Bright Monitoring] lives under Setup -> [Monitor] (invalid)")
            p.add_argument("--fx3-finder-monitor-menu-present-claimed", action="store_true", help="Claim FX3 exposes [Finder/Monitor] instead of [Monitor] (invalid)")
            p.add_argument("--fx3-builtin-evf-present-claimed", action="store_true", help="Claim FX3 has a built-in EVF (invalid)")
            p.add_argument("--dormant-evf-menu-requested", default="NONE", help="Request dormant EVF menu item: NONE, FINDER_MONITOR_SEL, VIEWFINDER_BRIGHT, VIEWFINDER_COLOR_TEMP, FINDER_FRAME_RATE")
            p.add_argument("--fx6-vf-adjust-four-subitems-present-claimed", action="store_true", help="Claim FX6 exposes 4-subitem VF Adjust (Backlight/Contrast/Chroma/Color Temp) menu (invalid)")
            # Group D (Wave 67 §§3-4 + Tier-0)
            p.add_argument("--recall-custom-hold-active", action="store_true", help="Activate [Recall Custom hold 1-3] (Still P/A/S/M only)")
            p.add_argument("--recall-custom-hold-slot", type=int, default=1, help="[Recall Custom hold] slot: 1, 2, or 3")
            p.add_argument("--recall-custom-hold-eleven-slots", default=None, help="Comma-separated 11 [Recall Custom hold] slots (is_checked_recall_custom_hold0..10)")
            p.add_argument("--recall-custom-hold-standalone-wb-requested", action="store_true", help="Request standalone White Balance checkbox in [Recall Custom hold] (invalid: 0 hits)")
            p.add_argument("--fx3-recall-custom-hold-standalone-wb-present-claimed", action="store_true", help="Claim [Recall Custom hold 1-3] exposes standalone White Balance checkbox (invalid)")
            p.add_argument("--claimed-recall-custom-hold-wiped-by-camera-reset", action="store_true", help="Claim [Recall Custom hold 1-3] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--tracking-on-custom-key-focus-mode", default="AF_C", help="Focus Mode while pressing [Tracking On] hold key: AF_C, AF_S, DMF, MF")
            p.add_argument("--tracking-on-custom-key-active", action="store_true", help="Activate [Tracking On] Hold Custom Key (Still AF-C only)")
            p.add_argument("--fx6-push-af-agc-allowed-in-cine-ei-or-bokeh-claimed", action="store_true", help="Claim FX6 Push AF/AGC works in Cine EI/Quick or Bokeh Control=On (invalid)")
            p.add_argument("--hdmi-resolution", default="AUTO", help="Setup -> [External Output] -> [HDMI Resolution]: AUTO, 2160P, 1080P, 1080I")
            p.add_argument("--rec-media-dur-hdmi-output", default="ON", help="[Rec. Media dur HDMI Output]: ON or OFF_HDMI_ONLY (locked ON in S&Q)")
            p.add_argument("--hdmi-output-resolution", default="1080P", help="[HDMI Output Settings] -> [Output Resolution]: AUTO, 2160P, 1080P, 1080I")
            p.add_argument("--hdmi-4k-output-rate", default="23_98P", help="[4K Output Set.(HDMI Only)]: 59_94P, 50P, 29_97P, 25P, 23_98P, 24_00P (24.00p reboots)")
            p.add_argument("--hdmi-raw-output", default="OFF", help="[RAW Output]: ON or OFF (locked OFF in S&Q)")
            p.add_argument("--hdmi-tc-output", default="OFF", help="[Time Code Output]: ON or OFF (disabled in S&Q)")
            p.add_argument("--hdmi-rec-control", default="OFF", help="[REC Control]: ON or OFF (requires Time Code Output=ON)")
            p.add_argument("--hdmi-4ch-audio-output", default="CH1_CH2", help="[4ch Audio Output]: CH1_CH2 or CH3_CH4")
            p.add_argument("--hdmi-info-display", default="ON", help="[HDMI Info. Display]: ON or OFF")
            p.add_argument("--ctrl-for-hdmi", default="ON", help="[CTRL FOR HDMI] (BKID_APP_setting_ctrl_for_hmdi): ON or OFF")
            p.add_argument("--expect-2400p-no-reboot-or-mixed-playback", action="store_true", help="Claim 24.00p HDMI Output Set. runs without reboot or mixes playback (invalid)")
            p.add_argument("--expect-hdmi-info-display-active-with-raw-or-hdmi-only", action="store_true", help="Claim [HDMI Info. Display] stays active during Off(HDMI Only) or RAW Output=ON (invalid)")
            p.add_argument("--claimed-external-output-wiped-by-camera-reset", action="store_true", help="Claim Reset-immune [External Output] settings are wiped by Camera Settings Reset (invalid)")
            p.add_argument("--dormant-4k-2k-or-24p-60p-requested", action="store_true", help="Request dormant [4K/2K Output] or [24p/60p Output] (0 hits -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-4k-2k-output-present-claimed", action="store_true", help="Claim FX3 exposes [4K/2K Output] menu (invalid)")
            p.add_argument("--fx3-24p-60p-output-present-claimed", action="store_true", help="Claim FX3 exposes [24p/60p Output] menu (invalid)")
            p.add_argument("--recording-media", default="SLOT_2", help="[Recording Media]: SLOT_1, SLOT_2, SIMULTANEOUS_RECORDING, SORT_RECORDING")
            p.add_argument("--rec-target-slot", type=int, default=2, help="Target recording slot (Slot 1 blocked EROFS=30 when Rec. Media dur HDMI=ON)")
            p.add_argument("--emmc-write-count", type=int, default=0, help="Persistent eMMC write count (must remain 0)")
            p.add_argument("--e-nd-actuator-tx-count", type=int, default=0, help="e-ND I2C actuator TX count (must remain 0)")
            p.add_argument("--wireless-rf-packets-emitted", type=int, default=0, help="Wireless RF packets emitted (must remain 0)")
            p.add_argument("--usb-packets-transmitted", type=int, default=0, help="USB packets transmitted (must remain 0)")
            p.add_argument("--simulated-passive-tx-bytes", type=int, default=0, help="Simulated passive UART TX bytes emitted (must remain 0)")
            p.add_argument("--simulated-h0-h3-drifted-surfaces", type=int, default=0, help="Simulated H0 vs H3 drifted surfaces (must remain 0)")
            p.add_argument("--claim-hardware-live-attach-authorized", action="store_true", help="Claim live hardware attachment is authorized offline (fail-closed rejection)")
            p.add_argument("--claim-persistent-emmc-writes-authorized", action="store_true", help="Claim persistent eMMC writes are authorized (fail-closed rejection)")
            p.add_argument("--claim-cross-model-flash-authorized", action="store_true", help="Claim cross-model partition flashing is authorized (fail-closed rejection)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 329 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--summary", action="store_true", help="Emit compact one-line summary to stdout even when --json is passed")
            p.add_argument("--sony-help-guide-id", default="ilc/2210", help="Official Sony Help Guide identifier (must remain ilc/2210)")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--exposure-mode", default="MANUAL_EXPOSURE", help="[Exposure Mode]: MANUAL_EXPOSURE, PROGRAM_AUTO, APERTURE_PRIORITY, SHUTTER_PRIORITY, INTELLIGENT_AUTO, FLEXIBLE_EXP")
            # Group A (Wave 62 secs 1-2)
            p.add_argument("--audio-recording", default="ON", help="[Audio Recording]: ON or OFF (disabled in S&Q)")
            p.add_argument("--audio-out-timing", default="LIVE", help="[Audio Out Timing] (0x6bc2): LIVE or LIP_SYNC (Shooting -> Audio Recording; disabled in S&Q)")
            p.add_argument("--claimed-audio-out-timing-under-setup-sound-option", action="store_true", help="Claim [Audio Out Timing] lives under Setup -> [Sound Option] (invalid)")
            p.add_argument("--audio-out-timing-active-in-sq-claimed", action="store_true", help="Claim [Audio Out Timing] stays active in S&Q Motion (invalid)")
            p.add_argument("--audio-recording-in-sq-claimed", action="store_true", help="Claim [Audio Recording] operates in S&Q Motion (invalid)")
            p.add_argument("--claimed-audio-out-timing-resists-reset", action="store_true", help="Claim [Audio Out Timing] resists Camera Settings Reset (invalid)")
            p.add_argument("--dormant-audio-level-display-requested", action="store_true", help="Request Ver. 2.00+ removed [Audio Level Display] (_f 0x7a36 -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-audio-level-display-menu-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 still exposes [Audio Level Display] menu item (invalid)")
            p.add_argument("--audio-rec-level", type=int, default=26, help="[Audio Rec Level] (0..31, default 26, non-disableable limiter)")
            p.add_argument("--fx3-disable-builtin-limiter-requested", action="store_true", help="Attempt disabling non-disableable built-in audio limiter (rejected)")
            p.add_argument("--fx3-limiter-6step-present-claimed", action="store_true", help="Claim FX3 exposes FX6 6-step Limiter Mode (invalid)")
            p.add_argument("--fx3-32bit-float-audio-claimed", action="store_true", help="Claim FX3 or FX6 records 32-bit float audio (invalid)")
            p.add_argument("--four-ch-audio-monitoring", default="CH1_CH2", help="[4ch Audio Monitoring]: CH1_CH2, CH3_CH4, CH1_3_CH2_4, CH1_CH1, CH2_CH2")
            p.add_argument("--shoe-audio-set", default="48KHZ_24BIT_4CH", help="[Shoe Audio Set.] (0x77f6): 48KHZ_24BIT_4CH, 48KHZ_24BIT_2CH, 48KHZ_16BIT_2CH")
            p.add_argument("--movie-file-format", default="XAVC_S_I_4K", help="Movie [File Format]: XAVC_HS_4K, XAVC_S_4K, XAVC_S_HD, XAVC_S_I_4K, XAVC_S_I_HD, XAVC_S_I_DCI_4K")
            p.add_argument("--rec-fps", type=float, default=23.98, help="Recording frame rate in fps (Proxy cut off >= 100.0p)")
            p.add_argument("--sq-enabled", action="store_true", help="Enable S&Q Motion shooting")
            p.add_argument("--sq-fps", type=float, default=60.0, help="S&Q frame rate in fps")
            p.add_argument("--proxy-recording", default="OFF", help="[Proxy Recording]: OFF or ON (forced MPEG4_AAC_LC_2CH_128KBPS; cut off >= 100.0p)")
            p.add_argument("--claimed-shoe-4ch-unsupported-on-xavc-codec", action="store_true", help="Claim Shoe Audio 48kHz/24bit 4ch is blocked on one of the 6 main XAVC codecs (invalid)")
            p.add_argument("--expect-proxy-4ch-24bit-audio", action="store_true", help="Claim Proxy files carry 4ch 24-bit LPCM instead of 2ch AAC-LC 128kbps (invalid)")
            p.add_argument("--expect-proxy-active-at-100p-plus", action="store_true", help="Claim Proxy recording stays enabled at 100p/120p (invalid)")
            p.add_argument("--mic-35mm-inserted", action="store_true", help="Indicate 3.5mm MIC plug is inserted (hardware-overrides and grays out [Shoe Audio Set.])")
            p.add_argument("--expect-shoe-audio-active-with-35mm-mic", action="store_true", help="Claim [Shoe Audio Set.] stays active while 3.5mm MIC plug is inserted (invalid)")
            p.add_argument("--xlr-h1-attached", action="store_true", help="Indicate XLR-H1 Top Handle is attached to Multi Interface Shoe")
            p.add_argument("--xlr-h1-handle-audio", default="OFF", help="XLR-H1 HANDLE AUDIO switch: ON or OFF (OFF falls back to internal mic)")
            p.add_argument("--xlr-h1-dig-analog", default="DIGITAL", help="XLR-H1 DIG/ANALOG switch: DIGITAL or ANALOG (ANALOG caps at 16bit 2ch)")
            p.add_argument("--xlr-h1-input-select", default="IN1_IN2", help="XLR-H1 INPUT SELECT: IN1_IN2 or IN1")
            p.add_argument("--expect-xlr-h1-audio-active-when-handle-off", action="store_true", help="Claim XLR-H1 XLR audio stays active when HANDLE AUDIO=OFF (invalid)")
            p.add_argument("--wind-noise-reduct", default="OFF", help="[Wind Noise Reduct.]: ON or OFF (built-in internal mic only)")
            p.add_argument("--expect-wind-noise-applies-to-xlr-or-35mm", action="store_true", help="Claim [Wind Noise Reduct.] applies to XLR-H1 or 3.5mm external mics (invalid)")
            p.add_argument("--face-eye-prior-in-af", default="ON", help="[Face/Eye Prior. in AF]: ON or OFF")
            p.add_argument("--face-eye-subject", default="HUMAN", help="[Face/Eye Subject] (0x70fa): ONLY HUMAN or ANIMAL")
            p.add_argument("--dormant-subject-requested", default="NONE", help="Request dormant AI subject: NONE, BIRD, ANIMAL_BIRD, INSECT, CAR_TRAIN, AIRPLANE (EOPNOTSUPP=95)")
            p.add_argument("--fx3-bird-insect-car-airplane-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 exposes Bird/Animal-Bird/Insect/Car-Train/Airplane (Wave-42 Bird errata)")
            p.add_argument("--fx3-animal-eye-af-in-movie-present-claimed", action="store_true", help="Claim FX3 supports Animal Eye AF in Movie/S&Q (invalid: Still-only)")
            p.add_argument("--expect-animal-eye-af-in-movie", action="store_true", help="Attempt enabling Animal Eye AF inside Movie or S&Q (EOPNOTSUPP=95)")
            p.add_argument("--right-left-eye-select", default="AUTO", help="[Right/Left Eye Select]: AUTO, RIGHT_EYE, LEFT_EYE")
            p.add_argument("--face-eye-frame-disp", default="OFF", help="[Face/Eye Frame Disp.]: ON or OFF (never leaked to clean HDMI)")
            p.add_argument("--expect-face-eye-frame-on-clean-hdmi", action="store_true", help="Claim [Face/Eye Frame Disp.] appears on clean HDMI output (invalid)")
            p.add_argument("--face-memory-count", type=int, default=0, help="Registered [Face Memory] count (0..8, survives Reset, excluded from CAMSET*.DAT)")
            p.add_argument("--regist-faces-priority", default="ON", help="[Regist. Faces Priority]: ON or OFF (Human-only)")
            p.add_argument("--claimed-face-memory-wiped-by-camera-reset", action="store_true", help="Claim [Face Memory] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-face-memory-exported-in-camset", action="store_true", help="Claim [Face Memory] is exported into CAMSET*.DAT (invalid: excluded)")
            p.add_argument("--expect-regist-faces-priority-active-in-animal", action="store_true", help="Claim [Regist. Faces Priority] applies when Subject=Animal (invalid: Human-only)")
            p.add_argument("--fx6-has-animal-or-bird-subject-claimed", action="store_true", help="Claim ILME-FX6 supports Animal or Bird Eye AF (invalid)")
            p.add_argument("--fx6-has-persistent-face-memory-claimed", action="store_true", help="Claim ILME-FX6 stores 8-face persistent Face Memory (invalid)")
            # Group B (Wave 62 secs 3-4)
            p.add_argument("--silent-mode", default="ON", help="[Silent Mode]: ON or OFF")
            p.add_argument("--audio-signals", default="OFF", help="[Audio signals]: ON, OFF_SHUTTER_ONLY, OFF (forced OFF when Silent Mode=On)")
            p.add_argument("--shutter-type", default="ELECTRONIC_SHUTTER", help="Still [Shutter Type]: MECHANICAL_SHUTTER or ELECTRONIC_SHUTTER")
            p.add_argument("--flash-enabled", action="store_true", help="Enable Flash shooting (locked out under Silent Mode=On)")
            p.add_argument("--long-exposure-nr", default="OFF", help="[Long Exposure NR]: ON or OFF (locked out under Silent Mode=On)")
            p.add_argument("--e-front-curtain-shut", default="OFF", help="[e-Front Curtain Shut.]: ON or OFF (locked out under Silent Mode=On)")
            p.add_argument("--bulb-enabled", action="store_true", help="Enable Still BULB exposure (locked out under Silent Mode=On)")
            p.add_argument("--anti-flicker-shoot", default="OFF", help="[Anti-flicker Shoot.]: ON or OFF (locked out under Silent Mode=On and Movie/S&Q)")
            p.add_argument("--claimed-silent-mode-auto-disables-af-illuminator", action="store_true", help="Claim [Silent Mode]=On automatically disables AF Illuminator (invalid)")
            p.add_argument("--claimed-silent-mode-is-single-bool-toggle", action="store_true", help="Claim [Silent Mode Settings] is a single flat boolean toggle instead of 2-level submenu (invalid)")
            p.add_argument("--exposed-target-function-items", default=None, help="Comma-separated [Target Function Settings] override (must be exact 2 items: APERTURE_DRIVE_IN_AF,AUTO_PIXEL_MAPPING)")
            p.add_argument("--target-aperture-drive-in-af", default="NOT_TARGET", help="[Target Function Settings] Aperture Drive in AF: STANDARD, SILENT_PRIORITY, NOT_TARGET")
            p.add_argument("--target-auto-pixel-mapping", default="OFF", help="[Target Function Settings] Auto Pixel Mapping: OFF or NOT_TARGET (OFF blocks power-off cnflasha writes)")
            p.add_argument("--expect-aperture-drive-silent-in-movie", action="store_true", help="Claim Silent Priority Aperture Drive in AF operates in Movie mode (invalid: Still-only)")
            p.add_argument("--cnflasha-write-on-poweroff-allowed", action="store_true", help="Allow Auto Pixel Mapping cnflasha write on power-off (blocked on Tier-0 bench)")
            p.add_argument("--dormant-shutter-when-pwr-off-requested", action="store_true", help="Request dormant [Shutter When Pwr OFF] (_f 0x709f -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-shutter-when-pwr-off-present-claimed", action="store_true", help="Claim FX3 has mechanical sensor shield [Shutter When Pwr OFF] (invalid)")
            p.add_argument("--fx6-shutter-when-pwr-off-present-claimed", action="store_true", help="Claim FX6 has mechanical [Shutter When Pwr OFF] (invalid)")
            p.add_argument("--airplane-mode", default="ON", help="[Airplane Mode]: ON or OFF (bench requires ON)")
            p.add_argument("--wifi-enabled", action="store_true", help="Indicate Wi-Fi radio is enabled (blocked on Zero-RF bench)")
            p.add_argument("--wireless-rf-packets-emitted", type=int, default=0, help="Wireless RF packets emitted (must remain 0)")
            p.add_argument("--version-update-badge-active", action="store_true", help="Simulate active Ver. 6.00+ [Version] 0x6516 update badge (blocked under Zero-RF Airplane Mode=On)")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 recovery vault")
            p.add_argument("--slot1-bodydata-stage-requested", action="store_true", help="Attempt staging BODYDATA.DAT on Slot 1 Tier-0 Vault (HARD NO-GO EROFS=30)")
            p.add_argument("--software-update-trigger-requested", action="store_true", help="Attempt triggering in-camera [Software Update] (HARD NO-GO EPERM=1)")
            p.add_argument("--slot1-bodydata-writes", type=int, default=0, help="Slot-1 BODYDATA.DAT write count (must remain 0)")
            p.add_argument("--cross-model-flash-requested", action="store_true", help="Attempt cross-model BODYDATA.DAT / partition flash (HARD NO-GO)")
            p.add_argument("--bodydata-in-slot2-claimed", action="store_true", help="Claim FX3 can flash BODYDATA.DAT from Slot 2 (invalid: Slot 1 only)")
            p.add_argument("--source-fw-for-update-audit", default="7.02", help="Source FX3 firmware version for stepping-stone audit (e.g. 2.02, 2.04, 7.02)")
            p.add_argument("--no-stepping-stone-v204-v205-completed", dest="stepping_stone_v204_v205_completed", action="store_false", help="Indicate <= Ver. 2.02 camera has NOT completed Ver. 2.04/2.05 stepping-stone")
            p.add_argument("--direct-v202-to-v702-flash-claimed", action="store_true", help="Claim direct <= Ver. 2.02 to Ver. 7.02 flash without Ver. 2.04/2.05 stepping-stone (invalid)")
            p.add_argument("--battery-soc-pct", type=float, default=88.0, help="NP-FZ100 battery SOC%% (>= 51.0%% required for any update audit)")
            p.add_argument("--fx6-update-slot-claimed", default="SLOT_B", help="ILME-FX6 update slot claim (must be SLOT_B)")
            p.add_argument("--fx6-battery-only-update-claimed", action="store_true", help="Claim FX6 allows firmware update on battery without AC Adaptor (invalid)")
            # Group C (Wave 63 secs 1-2)
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, FLEXIBLE_ISO, CINE_EI_QUICK, CINE_EI")
            p.add_argument("--picture-profile", default="OFF", help="[Picture Profile]: OFF, PP1..PP11, PPLUT1..PPLUT4")
            p.add_argument("--exposed-hdmi-settings-items", default=None, help="Comma-separated 8 [HDMI Output Settings] items override")
            p.add_argument("--dormant-color-gamut-for-raw-requested", action="store_true", help="Request Ver. 2.00+ removed [Color Gamut for RAW Output] (_f 0x6bdc -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-color-gamut-for-raw-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 exposes [Color Gamut for RAW Output] (invalid)")
            p.add_argument("--claimed-hdmi-settings-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only 8 [HDMI Output Settings] were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--rec-media-dur-hdmi-output", default="ON", help="[Rec. Media dur HDMI Output]: ON or OFF_HDMI_ONLY")
            p.add_argument("--recording-media", default="SLOT_2", help="[Recording Media]: SLOT_1, SLOT_2, SIMULTANEOUS_RECORDING, SORT_RECORDING")
            p.add_argument("--no-slot1-wp-locked", dest="slot1_wp_locked", action="store_false", help="Indicate Slot 1 physical write-protect switch is unlocked")
            p.add_argument("--slot1-data-sector-writes", type=int, default=0, help="Slot-1 data sector writes (must remain 0)")
            p.add_argument("--internal-co-rec-write-to-slot1-requested", action="store_true", help="Attempt HDMI RAW co-recording write onto Slot 1 Tier-0 Vault (blocked EROFS=30)")
            p.add_argument("--expect-internal-writes-during-hdmi-only", action="store_true", help="Claim internal card writes occur under Off(HDMI Only) (invalid)")
            p.add_argument("--hdmi-output-resolution", default="1080P", help="HDMI [Output Resolution]: AUTO, 2160P, 1080P, 1080I")
            p.add_argument("--expect-4k-hdmi-with-rec-on-during-log-or-pplut", action="store_true", help="Claim 4K HDMI outputs when Rec. Media=On during Log Shooting or PPLUT1..4 (invalid: 1080p clamp)")
            p.add_argument("--hdmi-4k-setting", default="23.98P_10BIT", help="[4K Output Set.(HDMI Only)]: 59.94P_10BIT, 50P_10BIT, 29.97P_10BIT, 25P_10BIT, 23.98P_10BIT, 24.00P_10BIT")
            p.add_argument("--dormant-4k-24p-8bit-requested", action="store_true", help="Request dormant [4K Output Set.(HDMI Only)] 24.00p 8bit (_f 0x748a -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-4k-24p-8bit-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 exposes 8-bit 4K HDMI output options (invalid: 10-bit only)")
            p.add_argument("--expect-24p-no-reboot", action="store_true", help="Claim switching to 24.00p works without full reboot (invalid)")
            p.add_argument("--hdmi-raw-output", default="OFF", help="[RAW Output]: ON or OFF (4264x2408 16-bit)")
            p.add_argument("--raw-output-setting", default="23.98P", help="[RAW Output Setting]: 59.94P, 50P, 29.97P, 25P, 23.98P, 24.00P")
            p.add_argument("--hdmi-time-code-output", default="OFF", help="HDMI [Time Code Output]: ON or OFF")
            p.add_argument("--hdmi-rec-control", default="OFF", help="HDMI [REC Control]: ON or OFF (requires Time Code Output=On)")
            p.add_argument("--hdmi-4ch-audio-output", default="CH1_CH2", help="HDMI [4ch Audio Output]: CH1_CH2 or CH3_CH4")
            p.add_argument("--hdmi-info-display", default="OFF", help="[HDMI Info. Display]: ON or OFF (ON blanks FX3 LCD)")
            p.add_argument("--allow-lcd-blanking-for-hdmi-info", action="store_true", help="Explicitly allow FX3 LCD blanking when [HDMI Info. Display]=On")
            p.add_argument("--expect-fx3-lcd-stays-on-when-hdmi-info-on", action="store_true", help="Claim FX3 LCD remains active while [HDMI Info. Display]=On (invalid)")
            p.add_argument("--fx6-sdi-raw-allows-4k-hdmi-claimed", action="store_true", help="Claim FX6 12G-SDI RAW allows simultaneous 4K HDMI output (invalid: HDMI <= 1080p)")
            p.add_argument("--fx6-hdmi-raw-supports-24-00p-claimed", action="store_true", help="Claim FX6 RAW(HDMI) 4240x2392 supports True 24Hz (invalid)")
            p.add_argument("--fx6-remote-if-syncs-internal-card-claimed", action="store_true", help="Claim FX6 SDI/HDMI Remote I/F acts as Parallel Rec syncing internal card (invalid)")
            p.add_argument("--desqueeze-display", default="OFF", help="[De-Squeeze Display]: OFF, 1.3X, 1.5X, 1.6X (executes 1.65x), 2.0X")
            p.add_argument("--dormant-desqueeze-1-8x-requested", action="store_true", help="Request absent 1.8x De-Squeeze ratio on FX3 Ver. 7.02 (EOPNOTSUPP=95)")
            p.add_argument("--fx3-desqueeze-1-8x-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 exposes 1.8x De-Squeeze ratio (invalid)")
            p.add_argument("--claimed-desqueeze-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [De-Squeeze Display] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--desqueeze-1-6x-executed-factor", type=float, default=1.65, help="Executed stretch factor for [1.6x] UI label (must be 1.65 per _f 0x7d0c)")
            p.add_argument("--focus-mode", default="MF", help="[Focus Mode]: MF, AF_C, AF_S, AF_A, DMF")
            p.add_argument("--focus-area", default="WIDE", help="[Focus Area]: WIDE, ZONE, CENTER_FIX, SPOT_S, SPOT_M, SPOT_L, EXPAND_SPOT")
            p.add_argument("--steadyshot-mode", default="OFF", help="[SteadyShot]: OFF, STANDARD, ACTIVE (De-Squeeze requires OFF)")
            p.add_argument("--face-priority-in-multi-metering", default="OFF", help="[Face Priority in Multi Metering]: ON or OFF (De-Squeeze requires OFF)")
            p.add_argument("--expect-desqueeze-active-in-still", action="store_true", help="Claim [De-Squeeze Display] is selectable in Still PHOTO mode (invalid)")
            p.add_argument("--expect-desqueeze-bakes-internal-file", action="store_true", help="Claim [De-Squeeze Display] bakes stretched pixels into recorded MP4/XAVC (invalid)")
            p.add_argument("--expect-desqueeze-applied-during-bypass", action="store_true", help="Claim De-Squeeze remains applied during 6 bypass conditions (invalid)")
            p.add_argument("--claimed-desqueeze-locks-out-focus-mag-or-bright-mon", action="store_true", help="Claim De-Squeeze locks out [Focus Magnifier] or [Bright Monitoring] (invalid: both coexist)")
            p.add_argument("--fx6-desqueeze-has-1-6x-or-sdi-claimed", action="store_true", help="Claim FX6 De-Squeeze includes 1.6x or applies over SDI output (invalid: VF/HDMI 1.3x/1.5x/2.0x)")
            # Group D (Wave 63 secs 3-4 + Tier-0)
            p.add_argument("--rec-lamp-mode", default="ALL_ON", help="3-lamp [REC Lamp] (0x6e62): ALL_ON, ONLY_FRONT_OFF, ALL_OFF")
            p.add_argument("--dormant-tally-light-menu-requested", action="store_true", help="Request FX6-style [Tally Light] menu on FX3 (EOPNOTSUPP=95)")
            p.add_argument("--fx3-tally-light-menu-present-claimed", action="store_true", help="Claim FX3 exposes [Tally Light] menu name (invalid: [REC Lamp])")
            p.add_argument("--dormant-rec-lamp-only-one-requested", action="store_true", help="Request dormant [Only 1 REC Lamp] (_f 0x743e -> EOPNOTSUPP=95)")
            p.add_argument("--claimed-rec-lamp-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [REC Lamp] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--expect-top-rec-ring-off-with-rear-on", action="store_true", help="Claim ONLY_FRONT_OFF leaves top/rear lamps off/on independently (invalid: only front LED #8 off)")
            p.add_argument("--claimed-silent-mode-turns-off-rec-lamp", action="store_true", help="Claim [Silent Mode]=On automatically turns off [REC Lamp] (invalid: independent)")
            p.add_argument("--emphasized-rec-display", default="ON", help="[Emphasized REC Display] (0x68cf): ON or OFF (Resettable)")
            p.add_argument("--claimed-emph-rec-resists-camera-reset", action="store_true", help="Claim [Emphasized REC Display] resists Camera Settings Reset (invalid: Resettable)")
            p.add_argument("--expect-emph-rec-on-clean-hdmi", action="store_true", help="Claim [Emphasized REC Display] red border leaks onto clean HDMI output (invalid)")
            p.add_argument("--remain-shoot-display", default="ALWAYS_DISPLAY", help="[Remain Shoot Display] (0x604d): NOT_DISPLAYED, ALWAYS_DISPLAY, SHOOT_ONLY_DISPLAY")
            p.add_argument("--claimed-remain-shoot-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [Remain Shoot Display] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--expect-remain-shoot-shows-movie-time", action="store_true", help="Claim [Remain Shoot Display] displays Movie remaining minutes (invalid: Still shot count only)")
            p.add_argument("--auto-review", default="OFF", help="Still [Auto Review]: OFF, 2_SEC, 5_SEC, 10_SEC")
            p.add_argument("--interval-shooting-active", action="store_true", help="Indicate Still Interval Shooting is active (auto-bypasses Auto Review)")
            p.add_argument("--expect-auto-review-in-interval", action="store_true", help="Claim [Auto Review] runs during Still Interval Shooting (invalid)")
            p.add_argument("--claimed-auto-review-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [Auto Review] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--dormant-var-shutter-requested", action="store_true", help="Request dormant [Var. Shutter] (high_res_ss _f 0x6831 -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-var-shutter-present-claimed", action="store_true", help="Claim FX3 Ver. 7.02 exposes [Var. Shutter] (invalid: dormant 0x6831)")
            p.add_argument("--fx6-ecs-freq-hz", type=float, default=60.0, help="ILME-FX6 ECS frequency reference (23.99..8000.0 Hz)")
            p.add_argument("--fx3-has-ecs-mode-claimed", action="store_true", help="Claim FX3 exposes FX6 ECS (Extended Clear Scan) (invalid)")
            p.add_argument("--apsc-s35-shooting", default="OFF", help="[APS-C S35 Shooting]: AUTO, ON, OFF (Initialize-only / Wave-42 Reset Errata!)")
            p.add_argument("--hdmi-4k-only-active", action="store_true", help="Indicate 4K HDMI-only output active (locked out under APS-C S35=On)")
            p.add_argument("--still-image-size", default="L_12M", help="Still [Image Size]: L_12M, M_5_1M, S_3_0M (APS-C forces M_5_1M 2768x1848)")
            p.add_argument("--expect-apsc-4k-or-raw", action="store_true", help="Claim 4K/DCI 4K/HDMI 4K/HDMI RAW work under [APS-C S35 Shooting]=On (invalid)")
            p.add_argument("--claimed-apsc-wiped-by-camera-reset", action="store_true", help="Claim [APS-C S35 Shooting] resets on Camera Settings Reset (Wave-42 errata: Initialize-only!)")
            p.add_argument("--claimed-apsc-still-size-4-2m", action="store_true", help="Claim APS-C S35 Still max image size is M:4.2M instead of M:5.1M (2768x1848) (invalid)")
            p.add_argument("--e-nd-actuator-tx-count", type=int, default=0, help="e-ND I2C actuator TX count (must remain 0)")
            p.add_argument("--usb-packets-transmitted", type=int, default=0, help="USB packets transmitted (must remain 0)")
            p.add_argument("--simulated-passive-tx-bytes", type=int, default=0, help="Simulated passive UART TX bytes emitted (must remain 0)")
            p.add_argument("--simulated-h0-h3-drifted-surfaces", type=int, default=0, help="Simulated H0 vs H3 drifted surfaces (must remain 0)")
            p.add_argument("--claim-hardware-live-attach-authorized", action="store_true", help="Claim live hardware attachment is authorized offline (fail-closed rejection)")
            p.add_argument("--claim-persistent-emmc-writes-authorized", action="store_true", help="Claim persistent eMMC writes are authorized (fail-closed rejection)")
            p.add_argument("--claim-cross-model-flash-authorized", action="store_true", help="Claim cross-model partition flashing is authorized (fail-closed rejection)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-dial-customize-lut-embed-steadyshot-and-streaming":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 307 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--summary", action="store_true", help="Emit compact one-line summary to stdout even when --json is passed")
            p.add_argument("--sony-help-guide-id", default="ilc/2210", help="Official Sony Help Guide identifier (must remain ilc/2210)")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--exposed-dial-customize-items", default=None, help="Comma-separated [Dial Customize] 5 menu items override")
            p.add_argument("--dormant-dial-setup-or-wheel-lock-requested", action="store_true", help="Request Ver. 1.xx legacy [Dial Setup] / [Dial / Wheel Lock] (rejected with EOPNOTSUPP=95)")
            p.add_argument("--av-tv-rotate", default="NORMAL", help="[Av/Tv Rotate]: NORMAL or REVERSE")
            p.add_argument("--function-ring-lens", default="POWER_FOCUS", help="[Function Ring(Lens)]: POWER_FOCUS or APSC_S35_FF")
            p.add_argument("--lock-operation-parts", default="OFF", help="[Lock Operation Parts]: OFF, MULTISELECTOR_ONLY, DIAL_PLUS_WHEEL, ALL")
            p.add_argument("--claimed-dial-customize-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [Dial Customize] items were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx6-dial-topology-claimed", action="store_true", help="Claim FX3 adopts FX6 Multi Function / Grip / Handle / HOLD topology (invalid)")
            p.add_argument("--exposed-physical-dials", default=None, help="Comma-separated FX3 3 physical dials override")
            p.add_argument("--fx3-four-dial-rear-lr-present", action="store_true", help="Claim FX3 carries 4 physical dials with Rear Dial L/R (invalid)")
            p.add_argument("--dormant-rear-dial-lr-requested", action="store_true", help="Request dormant Alpha Rear Dial L/R bindings (_f.uxc 0x6a5c/0x680d, rejected with EOPNOTSUPP=95)")
            p.add_argument("--my-dial-slot", type=int, default=1, help="[My Dial Settings] bank index (1..3)")
            p.add_argument("--my-dial-active-recalled", action="store_true", help="Indicate My Dial 1..3 bank is actively recalled")
            p.add_argument("--expect-lock-blocks-recalled-my-dial", action="store_true", help="Claim Lock Operation Parts blocks an actively recalled My Dial (invalid: My Dial temporarily overrides lock)")
            p.add_argument("--fn-menu-still-slots", type=int, default=12, help="[Fn Menu Settings] Still slot count (must be 12)")
            p.add_argument("--fn-menu-movie-slots", type=int, default=12, help="[Fn Menu Settings] Movie slot count (must be 12)")
            p.add_argument("--fn-menu-all-not-set-claimed", action="store_true", help="Claim all 12 Fn slots are Not set (_f.uxc 0x6220 error trap)")
            p.add_argument("--exposed-live-view-subitems", default=None, help="Comma-separated [Live View Display Set.] 3 sub-items override")
            p.add_argument("--live-view-display", default="SETTING_EFFECT_ON", help="[Live View Display]: SETTING_EFFECT_ON or SETTING_EFFECT_OFF")
            p.add_argument("--exposure-effect", default="EXPOSURE_SET_AND_FLASH", help="[Exposure Effect]: EXPOSURE_SET_AND_FLASH or EXPOSURE_SETTING_ONLY")
            p.add_argument("--frame-rate-low-limit", default="OFF", help="[Frame Rate Low Limit]: ON or OFF")
            p.add_argument("--bright-monitoring-active", action="store_true", help="Indicate [Bright Monitoring] is active (forces Setting Effect OFF)")
            p.add_argument("--expect-setting-effect-on-during-bright-monitoring", action="store_true", help="Claim Setting Effect ON remains active during Bright Monitoring (invalid)")
            p.add_argument("--claimed-live-view-two-items-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only Live View Display / Exposure Effect were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--grid-line-display", default="OFF", help="[Grid Line Display]: ON or OFF")
            p.add_argument("--grid-line-type", default="RULE_OF_3RDS", help="[Grid Line Type]: RULE_OF_3RDS, SQUARE_GRID, DIAG_SQUARE_GRID")
            p.add_argument("--hdmi-info-display", default="OFF", help="[HDMI Info. Display]: ON or OFF")
            p.add_argument("--hdmi-raw-output", action="store_true", help="Enable HDMI RAW Output (locks out SteadyShot Active)")
            p.add_argument("--rec-media-dur-hdmi-output", default="ON", help="[Rec. Media dur HDMI Output]: ON or OFF_HDMI_ONLY")
            p.add_argument("--expect-grid-line-on-clean-hdmi", action="store_true", help="Claim [Grid Line] overlays leak onto clean HDMI output (invalid)")
            p.add_argument("--dormant-fx6-custom-png-grid-requested", action="store_true", help="Request FX6 dormant custom PNG grid line (rejected with EOPNOTSUPP=95)")
            p.add_argument("--user-lut-slot", type=int, default=1, help="[Manage User LUTs] slot index (1..16)")
            p.add_argument("--user-lut-import-requested", action="store_true", help="Simulate O_RDONLY [Manage User LUTs] .cube import")
            p.add_argument("--user-lut-source-media-type", default="CFEXPRESS_A", help="User LUT source card type: CFEXPRESS_A, SDXC, SDHC")
            p.add_argument("--user-lut-source-dir", default="/Sony/PRO/LUT", help="User LUT source directory (/Private/Sony/PRO/LUT on SD or /Sony/PRO/LUT on CFexpress)")
            p.add_argument("--user-lut-filename", default="FX3_BENCH_S709.cube", help="User LUT filename (<= 63 chars ending in .cube)")
            p.add_argument("--user-lut-cube-size", type=int, default=33, help="3D LUT cube dimension (17 or 33)")
            p.add_argument("--user-lut-config-writeback-to-slot1", action="store_true", help="Attempt LUT config writeback onto Slot-1 Tier-0 Vault (blocked with EROFS=30)")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, FLEXIBLE_ISO, CINE_EI_QUICK, CINE_EI")
            p.add_argument("--embed-lut-file", default="ON", help="[Embed LUT File] under [Log Shooting Setting]: ON or OFF")
            p.add_argument("--embed-lut-media-type", default="CFEXPRESS_A", help="Recording media for [Embed LUT File]: CFEXPRESS_A, SDXC, SDHC (locked Off on SDHC)")
            p.add_argument("--claimed-embed-lut-under-color-tone", action="store_true", help="Claim [Embed LUT File] lives under [Color/Tone] instead of [Log Shooting Setting] (invalid)")
            p.add_argument("--expect-embed-lut-bakes-pixels", action="store_true", help="Claim [Embed LUT File]=On bakes pixels instead of embedding container metadata (invalid)")
            p.add_argument("--picture-profile", default="OFF", help="[Picture Profile]: OFF, PP1..PP11, PPLUT1..PPLUT4")
            p.add_argument("--expect-pplut-preserves-unbaked-slog3", action="store_true", help="Claim PPLUT1..4 leaves unbaked S-Log3 pixels (invalid: irreversible pixel bake)")
            p.add_argument("--claimed-pplut-survives-reset", action="store_true", help="Claim PPLUT1..4 survives Camera Settings Reset / Initialize (invalid)")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 recovery vault")
            p.add_argument("--no-slot1-wp-locked", dest="slot1_wp_locked", action="store_false", help="Indicate Slot 1 physical write-protect switch is not locked")
            p.add_argument("--embed-lut-or-pplut-rec-requested", action="store_true", help="Attempt recording with Embed LUT / PPLUT onto rec_target_slot")
            p.add_argument("--rec-target-slot", type=int, default=2, help="Target recording slot for LUT/PPLUT rec (1 blocked when Slot 1 holds Tier-0 vault)")
            p.add_argument("--steadyshot-mode", default="STANDARD", help="Movie [SteadyShot]: ACTIVE, STANDARD, OFF")
            p.add_argument("--dormant-dynamic-active-requested", action="store_true", help="Request dormant [Dynamic active] (_f.uxc 0x741c, rejected with EOPNOTSUPP=95)")
            p.add_argument("--steadyshot-adjust", default="AUTO", help="[SteadyShot Adjust.]: AUTO or MANUAL")
            p.add_argument("--steadyshot-focal-mm", type=int, default=8, help="Manual SteadyShot [Focal Length] from exact 47-entry 8..1000mm table")
            p.add_argument("--exposed-focal-length-table", default=None, help="Comma-separated 47 focal lengths override")
            p.add_argument("--rec-fps", type=float, default=23.98, help="Movie [Rec Frame Rate] fps (119.88/100p locks out SteadyShot Active)")
            p.add_argument("--sq-mode-enabled", action="store_true", help="Enable S&Q motion shoot mode")
            p.add_argument("--sq-fps", type=float, default=60.0, help="S&Q frame rate (>= 100/120fps locks out SteadyShot Active)")
            p.add_argument("--desqueeze-display", default="OFF", help="[De-Squeeze Display]: OFF, 1.3x, 1.5x, 1.6x, 1.8x, 2.0x")
            p.add_argument("--distortion-comp", default="OFF", help="[Distortion Comp.]: AUTO or OFF (forced AUTO under SteadyShot Active)")
            p.add_argument("--no-fx3-builtin-5axis-ibis", dest="fx3_builtin_5axis_ibis_present", action="store_false", help="Claim FX3 lacks built-in 5-axis IBIS (invalid)")
            p.add_argument("--fx6-builtin-ibis-claimed", action="store_true", help="Claim ILME-FX6 has built-in IBIS (invalid: TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED)")
            p.add_argument("--dormant-movie-selftimer-requested", action="store_true", help="Request dormant Movie [Self-timer] (_f.uxc 0x7192 Rec Start delay, rejected)")
            p.add_argument("--still-drive-mode", default="SINGLE_SHOOTING", help="Still [Drive Mode]: SINGLE_SHOOTING, CONT_HI_PLUS, CONT_HI, CONT_MID, CONT_LO, SELF_TIMER_SINGLE, SELF_TIMER_CONT, BRACKET")
            p.add_argument("--front-led8-selftimer-blink-expected", action="store_true", help="Expect front LED #8 blinking during Still Self-timer countdown")
            p.add_argument("--silent-mode", default="OFF", help="[Silent Mode]: ON or OFF (suppresses Audio signals when ON)")
            p.add_argument("--audio-signals", default="ON", help="[Audio signals]: ON or OFF (Initialize-only)")
            p.add_argument("--dormant-audio-signal-volume-requested", action="store_true", help="Request dormant [Audio Signal Volume] slider (_f.uxc 0x7af6, rejected)")
            p.add_argument("--claimed-audio-signals-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [Audio signals] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx6-picture-cache-or-interval-rec-in-fx3-claimed", action="store_true", help="Claim FX6 Picture Cache Rec / Interval Rec exists on FX3 (invalid)")
            p.add_argument("--zebra-display", default="OFF", help="[Zebra Display]: ON or OFF")
            p.add_argument("--zebra-preset", default="70", help="[Zebra Level] preset: 70, 75, 80, 85, 90, 95, 100, 100+, CUSTOM_1, CUSTOM_2")
            p.add_argument("--zebra-custom-slot", default="CUSTOM_1", help="Zebra custom slot: CUSTOM_1 or CUSTOM_2")
            p.add_argument("--zebra-custom-type", default="STD_RANGE", help="Zebra custom type: STD_RANGE or LOWER_LIMIT")
            p.add_argument("--zebra-level-ire", type=int, default=70, help="Zebra IRE base/lower limit (0..109%%)")
            p.add_argument("--zebra-range-plus-minus", type=int, default=5, help="Zebra Custom Std+Range tolerance (+-1..10%%)")
            p.add_argument("--peaking-display", default="OFF", help="[Peaking Display]: ON or OFF")
            p.add_argument("--peaking-level", default="MID", help="[Peaking Level]: HIGH, MID, LOW")
            p.add_argument("--peaking-color", default="WHITE", help="[Peaking Color]: RED, YELLOW, BLUE, WHITE (vs FX6 B&W)")
            p.add_argument("--expect-zebra-or-peaking-on-clean-hdmi", action="store_true", help="Claim Zebra/Peaking overlays leak onto clean HDMI output (invalid)")
            p.add_argument("--fx6-zebra-both-mode-claimed", action="store_true", help="Claim FX6 supports simultaneous Both Zebra1+Zebra2 overlay (invalid)")
            p.add_argument("--claimed-zebra-peaking-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only Zebra/Peaking were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--streaming-protocol", default="DISABLED", help="[Network Streaming] protocol: DISABLED, RTMP, RTMPS, SRT")
            p.add_argument("--streaming-resolution", default="HD_1080P", help="[Output Img. Quality Set] resolution: 4K_2160P, 2K_1440P, HD_1080P, HD_720P")
            p.add_argument("--streaming-fps", type=float, default=29.97, help="Streaming fps: 59.94, 50.0, 29.97, 25.0 (23.98/24.00 forbidden)")
            p.add_argument("--movie-rec-during-streaming", default="DISABLE", help="[Movie Rec During Streaming]: ENABLE or DISABLE")
            p.add_argument("--internal-rec-resolution-class", default="HD", help="Internal rec resolution class during streaming: HD or 4K")
            p.add_argument("--internal-rec-fps", type=float, default=29.97, help="Internal rec fps during streaming (must match streaming_fps)")
            p.add_argument("--movie-rec-during-streaming-slot", type=int, default=2, help="Target slot for [Movie Rec During Streaming] (Slot 1 blocked EROFS=30 on Tier-0 vault)")
            p.add_argument("--fx6-builtin-rtmp-srt-claimed", action="store_true", help="Claim FX6 exposes built-in RTMP/SRT Network Streaming menu (invalid)")
            p.add_argument("--ftp-transfer-func", default="OFF", help="[FTP Transfer Func.]: OFF or ON (Passive mode only)")
            p.add_argument("--ftp-active-mode-requested", action="store_true", help="Request FTP Active mode (rejected with EOPNOTSUPP=95)")
            p.add_argument("--ftp-slot1-write-requested", action="store_true", help="Attempt FTP write onto Slot 1 Tier-0 Vault (blocked with EROFS=30)")
            p.add_argument("--claimed-network-wiped-by-camera-reset", action="store_true", help="Claim (Network) settings were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-network-survives-reset-network-set", action="store_true", help="Claim streaming/FTP settings survive Reset Network Set. (invalid)")
            p.add_argument("--airplane-mode", default="ON", help="[Airplane Mode]: ON or OFF (mandatory ON for zero-RF physical bench)")
            p.add_argument("--network-transport", default="NONE", help="Network transport: NONE, USB_LAN_CDC_NCM, WIRELESS_RF")
            p.add_argument("--wireless-streaming-requested", action="store_true", help="Attempt wireless streaming over Wi-Fi (blocked by Zero-RF bench firewall)")
            p.add_argument("--wireless-ftp-requested", action="store_true", help="Attempt wireless FTP transfer (blocked by Zero-RF bench firewall)")
            p.add_argument("--wireless-rf-packets-emitted", type=int, default=0, help="Measured/simulated RF packets emitted (must remain 0)")
            p.add_argument("--rf-nvs-p12-p13-writes-requested", action="store_true", help="Attempt write to p12/p13 RF NVRAM partitions (blocked)")
            p.add_argument("--simulated-passive-tx-bytes", type=int, default=0, help="Simulated passive UART TX bytes emitted (must remain 0)")
            p.add_argument("--simulated-h0-h3-drifted-surfaces", type=int, default=0, help="Simulated H0 vs H3 drifted surfaces (must remain 0)")
            p.add_argument("--claim-hardware-live-attach-authorized", action="store_true", help="Claim live hardware attachment is authorized offline (fail-closed rejection)")
            p.add_argument("--claim-persistent-emmc-writes-authorized", action="store_true", help="Claim persistent eMMC writes are authorized (fail-closed rejection)")
            p.add_argument("--claim-cross-model-flash-authorized", action="store_true", help="Claim cross-model partition flashing is authorized (fail-closed rejection)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 316 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--summary", action="store_true", help="Emit compact one-line summary to stdout even when --json is passed")
            p.add_argument("--sony-help-guide-id", default="ilc/2210", help="Official Sony Help Guide identifier (must remain ilc/2210)")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--exposure-mode", default="MANUAL_EXPOSURE", help="[Exposure Mode]: MANUAL_EXPOSURE, PROGRAM_AUTO, APERTURE_PRIORITY, SHUTTER_PRIORITY, INTELLIGENT_AUTO, FLEXIBLE_EXP")
            p.add_argument("--focus-mode", default="MF", help="[Focus Mode]: MF, AF_S, AF_A, AF_C, DMF")
            # Group A (Wave 58 §§1,2,4)
            p.add_argument("--bright-monitoring-active", action="store_true", help="Activate Custom-Key-only [Bright Monitoring] (0x701f, forces Setting Effect OFF, P/A/S/M + MF)")
            p.add_argument("--bright-monitoring-in-shoot-menu-claimed", action="store_true", help="Claim [Bright Monitoring] exists as a selectable shooting menu entry instead of Custom Key only (invalid)")
            p.add_argument("--live-view-display", default="SETTING_EFFECT_ON", help="[Live View Display]: SETTING_EFFECT_ON or SETTING_EFFECT_OFF")
            p.add_argument("--expect-setting-effect-on-during-bright-monitoring", action="store_true", help="Claim Setting Effect ON remains active during [Bright Monitoring] (invalid)")
            p.add_argument("--expect-bright-monitoring-blocks-focus-magnifier", action="store_true", help="Claim [Bright Monitoring] blocks [Focus Magnifier] / [Auto Magnifier in MF] on Ver. 7.00+ (invalid)")
            p.add_argument("--claimed-bright-monitoring-persists-after-power-cycle", action="store_true", help="Claim [Bright Monitoring] persists across power cycle (invalid: transient Custom Key toggle)")
            p.add_argument("--monitor-brightness-mode", default="MANUAL", help="[Monitor Brightness]: MANUAL or SUNNY_WEATHER")
            p.add_argument("--monitor-brightness-level", type=int, default=0, help="[Monitor Brightness] Manual level (-2..+2, default 0)")
            p.add_argument("--dormant-lcd-brightness-mode-requested", action="store_true", help="Request dormant [Monitor Brightness] AUTO/BRIGHT/NORMAL mode (rejected with EOPNOTSUPP=95)")
            p.add_argument("--claimed-monitor-brightness-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only [Monitor Brightness] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx6-backlight-is-lcd-brightness-claimed", action="store_true", help="Claim FX6 AE [Backlight] is equivalent to LCD [Monitor Brightness] (invalid)")
            p.add_argument("--fx6-vf-brightness-1-15-in-fx3-claimed", action="store_true", help="Claim FX3 exposes FX6 [VF Setting > Brightness] 1..15 range (invalid)")
            p.add_argument("--dormant-divide-or-extract-requested", action="store_true", help="Request dormant in-camera [Divide] / [Extract] (rejected with EOPNOTSUPP=95)")
            p.add_argument("--dormant-ftp-cut-15-30-60s-requested", action="store_true", help="Request dormant FTP 15/30/60s cut (rejected with EOPNOTSUPP=95)")
            p.add_argument("--shot-mark-write-requested", action="store_true", help="Attempt [Shot Mark 1/2] *M01.XML + AVF_INFO write onto shot_mark_slot")
            p.add_argument("--shot-mark-slot", type=int, default=2, help="Target slot for [Shot Mark 1/2] write (Slot 1 blocked EROFS=30 on Tier-0 vault)")
            p.add_argument("--clip-flag", default="NONE", help="Ver. 7.00+ [Clip Flag]: NONE, OK, NG, KEEP")
            p.add_argument("--clip-flag-write-requested", action="store_true", help="Attempt [Clip Flag] metadata write onto clip_flag_slot")
            p.add_argument("--clip-flag-slot", type=int, default=2, help="Target slot for [Clip Flag] write (Slot 1 blocked EROFS=30 on Tier-0 vault)")
            p.add_argument("--photo-capture-requested", action="store_true", help="Attempt [Photo Capture] Still extraction onto photo_capture_slot")
            p.add_argument("--photo-capture-slot", type=int, default=2, help="Target slot for [Photo Capture] (Slot 1 blocked EROFS=30 on Tier-0 vault)")
            p.add_argument("--create-divider-frame-requested", action="store_true", help="Attempt [Create Divider Frame] write onto divider_frame_slot")
            p.add_argument("--divider-frame-slot", type=int, default=2, help="Target slot for [Create Divider Frame] (Slot 1 blocked EROFS=30 on Tier-0 vault)")
            p.add_argument("--edit-write-requested", action="store_true", help="Attempt generic playback edit write onto edit_write_slot")
            p.add_argument("--edit-write-slot", type=int, default=2, help="Target slot for edit write (Slot 1 blocked EROFS=30 on Tier-0 vault)")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 recovery vault")
            p.add_argument("--no-slot1-wp-locked", dest="slot1_wp_locked", action="store_false", help="Indicate Slot 1 physical write-protect switch is not locked")
            p.add_argument("--bulb-enabled", action="store_true", help="Enable Still [BULB] exposure (Mechanical Shutter + Single Shooting + M mode only)")
            p.add_argument("--shutter-type", default="MECHANICAL_SHUTTER", help="Still [Shutter Type]: MECHANICAL_SHUTTER or ELECTRONIC_SHUTTER")
            p.add_argument("--still-drive-mode", default="SINGLE_SHOOTING", help="Still [Drive Mode]: SINGLE_SHOOTING, CONT_HI_PLUS, CONT_HI, CONT_MID, CONT_LO, INTERVAL, ...")
            p.add_argument("--anti-flicker-shoot", default="OFF", help="[Anti-flicker Shoot.]: ON or OFF (locks out BULB)")
            p.add_argument("--expect-bulb-in-electronic-or-cont-or-interval", action="store_true", help="Claim BULB works without 30s clamp under Electronic Shutter / Cont. / Interval (invalid)")
            p.add_argument("--dro-mode", default="OFF", help="[D-Range Optimizer]: OFF, AUTO, LV1..LV5")
            p.add_argument("--dro-bracket-mode", default="OFF", help="[DRO Bracket]: OFF, DRO_BRK_LO_1..3, DRO_BRK_HI_1|3|5")
            p.add_argument("--picture-profile", default="OFF", help="[Picture Profile]: OFF, PP1..PP11, PPLUT1..PPLUT4")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, FLEXIBLE_ISO, CINE_EI_QUICK, CINE_EI")
            p.add_argument("--hlg-still-image", default="OFF", help="[HLG Still Image]: ON or OFF")
            p.add_argument("--expect-dro-active-with-pp-or-hlg", action="store_true", help="Claim DRO stays active when Picture Profile / Log / HLG Still is enabled (invalid)")
            p.add_argument("--dormant-bulb-timer-requested", action="store_true", help="Request dormant [Bulb Timer] (_f 0x630f, rejected with EOPNOTSUPP=95)")
            p.add_argument("--dormant-auto-hdr-requested", action="store_true", help="Request dormant [Auto HDR] (0xe49d, rejected with EOPNOTSUPP=95)")
            # Group B (Wave 58 §3)
            p.add_argument("--dormant-bt-tc-link-requested", action="store_true", help="Request dormant Bluetooth [Timecode Link] / UltraSync (rejected with EOPNOTSUPP=95)")
            p.add_argument("--fx3-bt-tc-link-present-claimed", action="store_true", help="Claim FX3 supports Bluetooth [Timecode Link] (invalid: 0 hits)")
            p.add_argument("--fx6-bt-tc-link-claimed", action="store_true", help="Claim FX6 has Bluetooth or Bluetooth [Timecode Link] (invalid: zero-BT)")
            p.add_argument("--fx3-builtin-bnc-tc-in-out-switch-claimed", action="store_true", help="Claim FX3 has FX6 physical BNC TC IN/OUT switch (invalid: VMC-BNCM1 only)")
            p.add_argument("--vmc-bncm1-ext-lk-active", action="store_true", help="Indicate wired VMC-BNCM1 LTC EXT-LK is active (requires PRESET + FREE_RUN)")
            p.add_argument("--tc-make", default="PRESET", help="[Time Code Make]: PRESET or REGENERATE")
            p.add_argument("--tc-run", default="FREE_RUN", help="[Time Code Run]: FREE_RUN or REC_RUN")
            p.add_argument("--wifi-sku", default="WW728473", help="FX3 Wi-Fi SKU: NONE, WW728473 (2.4/5GHz), WW558244 (2.4GHz-only)")
            p.add_argument("--wifi-band-5ghz-requested", action="store_true", help="Request 5GHz Wi-Fi band (blocked on WW558244 SKU)")
            p.add_argument("--outdoor-5ghz-w52-requested", action="store_true", help="Request outdoor 5GHz W52 channel (indoor-only 0x6953)")
            p.add_argument("--wifi-security-protocol", default="WPA3_SAE", help="Wi-Fi security protocol: NONE, WPA2_PSK, WPA3_SAE")
            p.add_argument("--dormant-legacy-wifi-sec-requested", action="store_true", help="Request Ver. 7.00+ removed WEP/WPA-PSK/IPsec (rejected with EOPNOTSUPP=95)")
            p.add_argument("--wifi-enabled", action="store_true", help="Enable Wi-Fi RF radio (blocked by physical bench Zero-RF lock)")
            p.add_argument("--usb-lan-cnct-launch", default="OFF", help="[USB-LAN Cnct. Launch] (0x7d2a): ON or OFF")
            p.add_argument("--network-transport", default="NONE", help="Network transport: NONE, USB_LAN, WIRELESS_RF")
            p.add_argument("--multi-micro-usb-device-attached", action="store_true", help="Indicate Multi/Micro USB device is attached (mutually exclusive with USB-LAN)")
            p.add_argument("--exposed-usb-lan-kmods", default=None, help="Comma-separated USB-LAN kernel modules override (default cdc_ncm.ko,r8152.ko,asix.ko,...)")
            p.add_argument("--airplane-mode", default="ON", help="[Airplane Mode]: ON or OFF (mandatory ON for Zero-RF physical bench)")
            p.add_argument("--bluetooth-enabled", action="store_true", help="Enable Bluetooth RF radio (blocked by physical bench Zero-RF lock)")
            p.add_argument("--wireless-rf-packets-emitted", type=int, default=0, help="Measured/simulated wireless RF packets emitted (must remain 0)")
            p.add_argument("--rf-nvs-p12-p13-writes-requested", action="store_true", help="Attempt write to p12/p13 RF NVRAM partitions (blocked)")
            p.add_argument("--claimed-airplane-wiped-by-reset", action="store_true", help="Claim [Airplane Mode] was wiped by Reset Network Set. (invalid)")
            # Group C (Wave 59 §§1-2)
            p.add_argument("--mode-settings", default="FIXED_VARIABLE", help="[Mode Settings]: FIXED_VARIABLE or LEGACY")
            p.add_argument("--big6-home-screen-active", action="store_true", help="Activate Ver. 7.00+ BIG6 HOME screen (gated on FIXED_VARIABLE)")
            p.add_argument("--home-trigger-method", default="NONE", help="BIG6 HOME trigger method: NONE, CUSTOM_KEY_HOME, SWIPE_DOWN")
            p.add_argument("--exposed-big6-tiles", default=None, help="Comma-separated BIG6 6 dynamic tiles override")
            p.add_argument("--home-lower-left-mode", default="APERTURE", help="BIG6 lower-left tile mode: APERTURE or ND_FILTER")
            p.add_argument("--fx3-physical-e-nd-claimed", action="store_true", help="Claim FX3 has a physical e-ND actuator like FX6 (invalid: ZERO e-ND)")
            p.add_argument("--e-nd-actuator-tx-count", type=int, default=0, help="Physical e-ND actuator TX packets emitted (must remain 0)")
            p.add_argument("--expect-big6-displays-pp-during-log", action="store_true", help="Claim BIG6 lower-middle displays PP instead of Select LUT during Log Shooting (invalid)")
            p.add_argument("--expect-big6-displays-variable-iso-in-cine-ei", action="store_true", help="Claim BIG6 displays variable ISO instead of Base ISO + EI in Cine EI (invalid)")
            p.add_argument("--claimed-menu-fn-do-not-exit-home", action="store_true", help="Claim MENU/Fn buttons do not exit BIG6 HOME screen (invalid)")
            p.add_argument("--framing-enabled", default="OFF", help="Manual [Framing Settings] > [Framing]: ON or OFF")
            p.add_argument("--framing-rec-stream-area", default="FULL", help="[Framing] Recording/Streaming area: FULL or CROP")
            p.add_argument("--framing-hdmi-area", default="CROP", help="[Framing] HDMI area: FULL or CROP")
            p.add_argument("--apsc-s35-on", action="store_true", help="Indicate APS-C S35 Shooting is active (disabled by manual Framing)")
            p.add_argument("--rec-fps", type=float, default=23.98, help="Movie [Rec Frame Rate] fps (100/120p locks out Framing)")
            p.add_argument("--sq-fps", type=float, default=60.0, help="S&Q frame rate (100/120fps locks out Framing)")
            p.add_argument("--active-rec-or-stream-during-framing-toggle", action="store_true", help="Attempt toggling [Framing] during active recording/streaming (locked)")
            p.add_argument("--dormant-auto-framing-requested", action="store_true", help="Request dormant AI [Auto Framing] (TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY -> EOPNOTSUPP=95)")
            p.add_argument("--fx3-auto-framing-present-claimed", action="store_true", help="Claim FX3 exposes AI [Auto Framing] like ZV-E1/FX2/alpha7R V (invalid)")
            p.add_argument("--interval-shooting-active", action="store_true", help="Activate Still [Interval Shoot Func.] (up to 9,999 shots / 19,998 RAW+J/H files)")
            p.add_argument("--exposed-interval-params", default=None, help="Comma-separated Still [Interval Shoot Func.] 7 parameters override")
            p.add_argument("--interval-start-sec", type=int, default=1, help="Interval [Shooting Start Time] in seconds (1..5999)")
            p.add_argument("--interval-sec", type=int, default=3, help="Interval [Shooting Interval] in seconds (1..60)")
            p.add_argument("--interval-num-shots", type=int, default=30, help="Interval [Number of Shots] (1..9999)")
            p.add_argument("--interval-ae-tracking", default="MID", help="Interval [AE Tracking Sensitivity]: HIGH, MID, LOW")
            p.add_argument("--interval-shutter-type", default="ELECTRONIC", help="Interval [Shutter Type in Interval]: ELECTRONIC or MECHANICAL")
            p.add_argument("--interval-shoot-priority", default="OFF", help="Interval [Shoot Interval Priority]: ON or OFF")
            p.add_argument("--interval-target-slot", type=int, default=2, help="Interval burst write target slot (Slot 1 blocked EROFS=30 on Tier-0 vault)")
            p.add_argument("--claimed-interval-7params-survive-camera-reset", action="store_true", help="Claim Interval Shoot 7 parameters survive Camera Settings Reset (invalid)")
            p.add_argument("--fx3-interval-outputs-single-mxf-claimed", action="store_true", help="Claim FX3 Interval Shoot outputs FX6-style single MXF movie (invalid)")
            # Group D (Wave 59 §§3-4 + Tier-0)
            p.add_argument("--simult-recording", action="store_true", help="Enable Dual-Slot Simultaneous Recording (TC Regenerate reads Slot 1)")
            p.add_argument("--tc-regen-source-slot", type=int, default=1, help="Source slot read by [Time Code Make]=Regenerate during Simult. Recording (must be 1)")
            p.add_argument("--claimed-tc-make-run-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only TC Make/Run were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx3-has-clock-tc-mode-claimed", action="store_true", help="Claim FX3 exposes FX6 [Clock] TC Make mode (invalid: Preset/Regen only)")
            p.add_argument("--hdmi-tc-output", default="OFF", help="[Time Code Output] (HDMI): ON or OFF (gates HDMI REC Control)")
            p.add_argument("--hdmi-rec-control", default="OFF", help="[REC Control] (HDMI): ON or OFF")
            p.add_argument("--rec-media-dur-hdmi-output", default="ON", help="[Rec. Media dur HDMI Output]: ON or OFF_HDMI_ONLY")
            p.add_argument("--streaming-active", action="store_true", help="Indicate active Network Streaming (blocks HDMI REC Control)")
            p.add_argument("--hdmi-4ch-audio-output", default="CH1_CH2", help="[4ch Audio Output] (HDMI): CH1_CH2 or CH3_CH4")
            p.add_argument("--access-authen", default="ON", help="[Access Authen.]: ON or OFF (Ver. 7.00+ SSH only)")
            p.add_argument("--access-authen-protocol", default="SSH", help="[Access Authen.] protocol: SSH (HTTPS/HTTP_DIGEST/BASIC_AUTH=EOPNOTSUPP=95)")
            p.add_argument("--dormant-http-https-camera-auth-claimed", action="store_true", help="Claim FX3 Ver. 7.00+ [Access Authen.] uses HTTPS / HTTP Digest / Basic Auth instead of SSH (invalid)")
            p.add_argument("--claimed-access-authen-wiped-by-camera-reset", action="store_true", help="Claim [Access Authen.] was wiped by Camera Settings Reset instead of Reset Network Set./Initialize (invalid)")
            p.add_argument("--expect-root-cert-authenticates-inbound-http-server", action="store_true", help="Claim [Import Root Certificate] authenticates an inbound camera HTTP server (invalid: outbound FTPS/RTMPS/Cloud TLS only)")
            p.add_argument("--fx3-fan-control", default="AUTO", help="FX3 [Fan Control]: AUTO, MINIMUM, OFF_IN_REC, ALWAYS_OFF (zero Max)")
            p.add_argument("--fx6-fan-control", default="AUTO", help="FX6 [Fan Control]: AUTO, MINIMUM, OFF_IN_REC (Always Off dormant; zero Max)")
            p.add_argument("--dormant-fan-control-max-requested", action="store_true", help="Request mythical [Fan Control]=Max on FX3 or FX6 (0 hits -> EINVAL=22 / EOPNOTSUPP=95)")
            p.add_argument("--auto-power-off-temp", default="HIGH", help="[Auto Power OFF Temp.]: STANDARD or HIGH (tripod thermal guard)")
            p.add_argument("--handheld-bare-skin-unacknowledged", action="store_true", help="Simulate Auto Power OFF Temp.=High without tripod/bare-skin safety acknowledgment")
            p.add_argument("--claimed-fan-or-autotemp-wiped-by-camera-reset", action="store_true", help="Claim Initialize-only Fan Control / Auto Power OFF Temp. were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--simulated-passive-tx-bytes", type=int, default=0, help="Simulated passive UART TX bytes emitted (must remain 0)")
            p.add_argument("--simulated-h0-h3-drifted-surfaces", type=int, default=0, help="Simulated H0 vs H3 drifted surfaces (must remain 0)")
            p.add_argument("--claim-hardware-live-attach-authorized", action="store_true", help="Claim live hardware attachment is authorized offline (fail-closed rejection)")
            p.add_argument("--claim-persistent-emmc-writes-authorized", action="store_true", help="Claim persistent eMMC writes are authorized (fail-closed rejection)")
            p.add_argument("--claim-cross-model-flash-authorized", action="store_true", help="Claim cross-model partition flashing is authorized (fail-closed rejection)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 302 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--summary", action="store_true", help="Emit compact one-line summary to stdout even when --json is passed")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--focus-mode", default="MF", help="[Focus Mode]: AF_S, AF_A, AF_C, DMF, MF")
            p.add_argument("--exposure-mode", default="MANUAL_EXPOSURE", help="[Exposure Mode]: PROGRAM_AUTO, APERTURE_PRIORITY, SHUTTER_PRIORITY, MANUAL_EXPOSURE, INTELLIGENT_AUTO, FLEXIBLE_EXP")
            p.add_argument("--shading-comp", default="AUTO", help="[Shading Comp.] (2 options only: AUTO, OFF; Auto: Low 0x6c9c dormant)")
            p.add_argument("--dormant-shading-auto-low-requested", action="store_true", help="Request dormant Shading Comp.=Auto: Low (0x6c9c rejected with EOPNOTSUPP=95)")
            p.add_argument("--chromatic-aberration-comp", default="AUTO", help="[Chromatic Aberration Comp.]: AUTO or OFF")
            p.add_argument("--distortion-comp", default="OFF", help="[Distortion Comp.]: AUTO or OFF")
            p.add_argument("--steadyshot-mode", default="STANDARD", help="[SteadyShot]: OFF, STANDARD, ACTIVE")
            p.add_argument("--lens-distortion-comp-locked-auto", action="store_true", help="Indicate mounted E-mount lens locks [Distortion Comp.]=Auto")
            p.add_argument("--unchipped-manual-lens-attached", action="store_true", help="Indicate unchipped manual/PL lens without electrical contacts is mounted")
            p.add_argument("--expect-lens-comp-active-on-manual-lens", action="store_true", help="Claim lens compensation stays active on unchipped manual lens (invalid)")
            p.add_argument("--breathing-comp", default="OFF", help="[Breathing Comp.] (Movie-only): OFF or ON")
            p.add_argument("--no-breathing-comp-compliant-lens", dest="breathing_comp_compliant_lens", action="store_false", help="Indicate mounted lens is not Breathing Comp. compliant")
            p.add_argument("--hdmi-raw-output", action="store_true", help="Enable HDMI RAW Output (locks out Breathing Comp.)")
            p.add_argument("--claimed-static-lens-comp-wiped-by-camera-reset", action="store_true", help="Claim 3 static lens comps were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx6-lens-comp-in-scene-file-claimed", action="store_true", help="Claim FX6 stores static Lens Compensation inside Scene Files (invalid)")
            p.add_argument("--no-fx3-builtin-af-illuminator", dest="fx3_builtin_af_illuminator_present", action="store_false", help="Claim FX3 lacks front built-in AF illuminator LED #8 (invalid)")
            p.add_argument("--fx6-builtin-af-illuminator-present", action="store_true", help="Claim ILME-FX6 has a built-in front AF illuminator LED (invalid: ZERO)")
            p.add_argument("--af-illuminator", default="AUTO", help="[AF Illuminator]: AUTO or OFF")
            p.add_argument("--af-illuminator-firing-requested", action="store_true", help="Simulate physical AF illuminator LED firing (Still AF-S/AF-A only)")
            p.add_argument("--af-illuminator-distance-m", type=float, default=1.5, help="AF illuminator subject distance in meters (0.3..3.0 m)")
            p.add_argument("--focus-magnifier-active", action="store_true", help="Indicate Focus Magnifier is active (locks out AF Illuminator & Switch V/H AF)")
            p.add_argument("--mount-adaptor-attached", action="store_true", help="Indicate Mount Adaptor (e.g. LA-EA*) is attached (locks out AF Illuminator)")
            p.add_argument("--af-transition-speed", type=int, default=5, help="[AF Transition Speed] (1..7, default 5)")
            p.add_argument("--af-subj-shift-sensitivity", type=int, default=5, help="[AF Subj. Shift Sensitivity] (1..5, default 5)")
            p.add_argument("--af-assist", default="OFF", help="[AF Assist]: OFF or ON (Movie/S&Q AF-C only)")
            p.add_argument("--no-af-assist-compatible-lens", dest="af_assist_compatible_lens", action="store_false", help="Indicate lens does not support [AF Assist]")
            p.add_argument("--aperture-drive-in-af", default="STANDARD", help="[Aperture Drive in AF]: FOCUS_PRIORITY, STANDARD, SILENT_PRIORITY")
            p.add_argument("--af-with-shutter", default="ON", help="[AF w/ Shutter]: ON or OFF")
            p.add_argument("--pre-af", default="OFF", help="[Pre-AF]: ON or OFF")
            p.add_argument("--no-lens-pre-af-supported", dest="lens_pre_af_supported", action="store_false", help="Indicate mounted lens does not support Pre-AF")
            p.add_argument("--circ-of-focus-point", default="DOES_NOT_CIRCULATE", help="[Circ. of Focus Point]: DOES_NOT_CIRCULATE or CIRCULATE")
            p.add_argument("--expect-diagonal-focus-wrap", action="store_true", help="Claim [Circ. of Focus Point] wraps diagonally (invalid: orthogonal only)")
            p.add_argument("--focus-area-color", default="WHITE", help="[Focus Area Color]: WHITE or RED")
            p.add_argument("--claimed-af-five-params-wiped-by-camera-reset", action="store_true", help="Claim 5 Initialize-only AF params were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx6-aperture-drive-in-af-claimed", action="store_true", help="Claim ILME-FX6 exposes ILME-FX3 [Aperture Drive in AF] (invalid)")
            p.add_argument("--still-folder-name-mode", default="STANDARD_FORM", help="Still [Folder Name]: STANDARD_FORM or DATE_FORM")
            p.add_argument("--select-rec-folder-enabled-claimed", action="store_true", help="Claim [Select REC Folder] stays enabled under Date Form (invalid)")
            p.add_argument("--still-file-number-mode", default="SERIES", help="Still [File Number]: SERIES or RESET")
            p.add_argument("--still-file-prefix", default="DSC", help="Still [Set File Name] 3-char prefix (no leading '_')")
            p.add_argument("--still-folder-image-count", type=int, default=10, help="Images in current DCIM still folder (<= 4000)")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 recovery vault")
            p.add_argument("--no-slot1-wp-locked", dest="slot1_wp_locked", action="store_false", help="Indicate Slot 1 hardware WP switch is not locked")
            p.add_argument("--create-new-folder-requested", action="store_true", help="Request [Create New Folder] on target slot")
            p.add_argument("--create-new-folder-slot", type=int, default=2, help="Target slot for [Create New Folder] (1 blocked if Tier-0 vault present)")
            p.add_argument("--forced-file-number-reset-requested", action="store_true", help="Request [Forced File Number Reset] on target slot")
            p.add_argument("--forced-file-number-reset-slot", type=int, default=2, help="Target slot for [Forced File Number Reset] (1 blocked if Tier-0 vault present)")
            p.add_argument("--playback-media-slot", type=int, default=1, help="[Select Playback Media] slot (1 or 2; NOTE: [Copy] reverses write onto Slot 1 when == 2!)")
            p.add_argument("--playback-rating-requested", action="store_true", help="Request Playback [Rating] EXIF mutation (blocked on read-only Slot 1 Tier-0 Vault)")
            p.add_argument("--rating-stars", type=int, default=3, help="Playback [Rating] star count (1..5)")
            p.add_argument("--add-rating-requested", action="store_true", help="Request [Add Rating] shortcut")
            p.add_argument("--target-image-already-rated", action="store_true", help="Indicate target image already carries a rating")
            p.add_argument("--digital-zoom-active", action="store_true", help="Indicate Digital Zoom / CIZ is active (locks out Switch V/H AF Area)")
            p.add_argument("--switch-vh-af-area", default="OFF", help="[Switch V/H AF Area] (Still AF-C): OFF, AF_POINT_ONLY, AF_POINT_AND_AF_AREA")
            p.add_argument("--body-roll-orientation", default="0_DEGREES", help="Camera orientation: 0_DEGREES, 90_DEGREES, 270_DEGREES, INVALID_VERTICAL_PITCH")
            p.add_argument("--fx6-switch-vh-af-area-claimed", action="store_true", help="Claim ILME-FX6 exposes ILME-FX3 [Switch V/H AF Area] (invalid)")
            p.add_argument("--focus-area-limit-selected-count", type=int, default=14, help="[Focus Area Limit] active checkbox count (2..14)")
            p.add_argument("--dormant-focus-area-requested", default="NONE", help="Request dormant focus area: NONE, SPOT_XL, SPOT_XS, CUSTOM_1, CUSTOM_2, CUSTOM_3")
            p.add_argument("--fx6-focus-area-limit-claimed", action="store_true", help="Claim ILME-FX6 exposes 14-item [Focus Area Limit] (invalid)")
            p.add_argument("--exposure-std-adjust-metering-mode", default="MULTI", help="[Exposure Std. Adjust] metering mode: MULTI, CENTER, SPOT, ENTIRE_SCREEN_AVG, HIGHLIGHT")
            p.add_argument("--exposure-std-adjust-ev", type=float, default=0.0, help="[Exposure Std. Adjust] offset (-1.0..+1.0 EV in 1/6 EV steps)")
            p.add_argument("--expect-std-adjust-changes-exif-exposure-comp", action="store_true", help="Claim [Exposure Std. Adjust] modifies EXIF ExposureBiasValue (invalid)")
            p.add_argument("--claimed-exposure-std-adjust-wiped-by-camera-reset", action="store_true", help="Claim [Exposure Std. Adjust] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx6-exposure-std-adjust-claimed", action="store_true", help="Claim ILME-FX6 has Alpha [Exposure Std. Adjust] (invalid)")
            p.add_argument("--bracket-selftimer", default="OFF", help="[Selftimer during Brkt]: OFF, 2_SEC, 5_SEC, 10_SEC")
            p.add_argument("--bracket-order", default="0_MINUS_PLUS", help="[Bracket order]: 0_MINUS_PLUS, MINUS_0_PLUS")
            p.add_argument("--bracket-settings-active-in-movie-claimed", action="store_true", help="Claim [Bracket Settings] operates in Movie/S&Q (invalid: Still-only)")
            p.add_argument("--video-system", default="NTSC", help="[NTSC/PAL Selector]: NTSC or PAL")
            p.add_argument("--rec-frame-rate", default="23.98P", help="[Rec Frame Rate]: 23.98P, 24.00P, 25P, 29.97P, 50P, 59.94P")
            p.add_argument("--tc-format", default="NDF", help="[Time Code Format]: DF or NDF (locked NDF in 23.98p/24.00p; hidden in PAL)")
            p.add_argument("--user-bit-time-rec", default="OFF", help="[User Bit Time Rec]: ON or OFF")
            p.add_argument("--tcub-disp-setting", default="TC", help="[TC/UB Disp. Setting]: COUNTER, TC, U_BIT")
            p.add_argument("--fx3-builtin-bnc-tc-in-out-switch-claimed", action="store_true", help="Claim ILME-FX3 has FX6 physical BNC TC IN/TC OUT switch (invalid)")
            p.add_argument("--claimed-tcub-6items-wiped-by-camera-reset", action="store_true", help="Claim 6 Initialize-only TC/UB settings were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--playback-copy-requested", action="store_true", help="Request Playback [Copy] (BLOCKED fail-closed if playback_media_slot==2 and Slot 1 holds Tier-0 Vault!)")
            p.add_argument("--no-copy-battery-ok", dest="copy_battery_ok", action="store_false", help="Simulate insufficient battery for Playback [Copy]")
            p.add_argument("--no-copy-target-media-speed-ok", dest="copy_target_media_speed_ok", action="store_false", help="Simulate destination card speed grade insufficient for Playback [Copy]")
            p.add_argument("--no-copy-dest-slot-present", dest="copy_dest_slot_present", action="store_false", help="Simulate missing destination card for Playback [Copy]")
            p.add_argument("--expect-copy-preserves-group-or-protect", action="store_true", help="Claim Playback [Copy] preserves group/protect attributes (invalid: resets)")
            p.add_argument("--fx6-in-camera-copy-clip-claimed", action="store_true", help="Claim ILME-FX6 supports dual-slot in-camera Copy Clip (invalid: FX3-only)")
            p.add_argument("--slide-show-requested", action="store_true", help="Request Playback [Slide Show]")
            p.add_argument("--slide-show-repeat", default="OFF", help="[Slide Show] Repeat: ON or OFF")
            p.add_argument("--slide-show-interval-sec", type=int, default=3, help="[Slide Show] Interval seconds: 1, 3, 5, 10, 30")
            p.add_argument("--slide-show-view-mode", default="DATE_VIEW", help="[Slide Show] View Mode: DATE_VIEW or FOLDER_VIEW_STILL (MOVIE_VIEW rejected)")
            p.add_argument("--touch-operation", default="OFF", help="[Touch Operation]: ON, ON_PLAYBACK_ONLY, OFF")
            p.add_argument("--touch-sensitivity", default="STANDARD", help="[Touch Sensitivity]: STANDARD or SENSITIVE (not Responsive)")
            p.add_argument("--touch-func-in-shooting", default="TOUCH_TRACKING", help="[Touch Func. in Shooting]: TOUCH_FOCUS, TOUCH_TRACKING, OFF")
            p.add_argument("--swipe-up", default="OPEN_THE_FN_MENU", help="[Swipe Up]: OPEN_THE_FN_MENU or OFF")
            p.add_argument("--dormant-touch-trap-requested", default="NONE", help="Request dormant touch trap: NONE, TOUCH_SHUTTER, TOUCH_AE, TOUCH_PANEL_PAD, FOOTER_ICON_TOUCH, RESPONSIVE, SWIPE_LEFT_RIGHT")
            p.add_argument("--touch-panel-pad-present-claimed", action="store_true", help="Claim ILME-FX3 exposes [Touch Panel/Pad] (invalid: EVF-less)")
            p.add_argument("--footer-icon-touch-enabled-claimed", action="store_true", help="Claim ILME-FX3 exposes [Footer Icon Touch] (invalid: dormant)")
            p.add_argument("--claimed-touch-4items-wiped-by-camera-reset", action="store_true", help="Claim 4 Initialize-only touch settings were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--fx3-builtin-evf-present", action="store_true", help="Claim ILME-FX3 has a built-in EVF (invalid: ZERO EVF hardware)")
            p.add_argument("--fx3-eye-sensor-present", action="store_true", help="Claim ILME-FX3 has an EVF eye sensor (invalid: ZERO eye sensor)")
            p.add_argument("--fx3-select-finder-monitor-present", action="store_true", help="Claim ILME-FX3 has [Select Finder/Monitor] (invalid: ZERO EVF)")
            p.add_argument("--fx3-graphic-display-present", action="store_true", help="Claim ILME-FX3 exposes [Graphic Display] DISP mode (invalid)")
            p.add_argument("--activate-dormant-evf-finder-mode", action="store_true", help="Attempt to activate dormant EVF/finder DISP mode (CRITICAL black-screen lockout trap)")
            p.add_argument("--finder-monitor-key-claimed", action="store_true", help="Claim Custom Key [Finder/Monitor Sel.] exists on ILME-FX3 (invalid)")
            p.add_argument("--graphic-display-claimed", action="store_true", help="Claim [Graphic Display] checkbox exists under DISP Set (invalid)")
            p.add_argument("--monitor-off-evf-trap-claimed", action="store_true", help="Claim Monitor Off/Auto-EVF switch exists on ILME-FX3 (invalid: black-screen trap)")
            p.add_argument("--for-viewfinder-disp-claimed", action="store_true", help="Claim [For Viewfinder] DISP mode exists on ILME-FX3 (invalid)")
            p.add_argument("--fx6-detachable-evf-loupe-claimed", action="store_true", help="Claim ILME-FX6 removable LCD hood/loupe is a built-in EVF or exists on FX3 (invalid)")
            p.add_argument("--claimed-disp-modes-wiped-by-camera-reset", action="store_true", help="Claim DISP Set modes were wiped by Camera Settings Reset (invalid)")
            p.add_argument("--ael-with-shutter", default="AUTO", help="[AEL w/ Shutter] (Still-only): AUTO, ON, OFF")
            p.add_argument("--ael-with-shutter-in-movie-claimed", action="store_true", help="Claim [AEL w/ Shutter] operates in Movie/S&Q (invalid: Still-only)")
            p.add_argument("--claimed-ael-with-shutter-wiped-by-camera-reset", action="store_true", help="Claim [AEL w/ Shutter] was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--exp-comp-set", default="AMBIENT_AND_FLASH", help="[Exp.comp.set]: AMBIENT_AND_FLASH or AMBIENT_ONLY")
            p.add_argument("--wireless-flash", default="OFF", help="[Wireless Flash]: ON or OFF")
            p.add_argument("--external-flash-set-requested", action="store_true", help="Request [External Flash Set.] (requires MI-Shoe compatible flash in Still)")
            p.add_argument("--mi-shoe-external-flash-attached", action="store_true", help="Indicate compatible Sony MI-Shoe external flash is attached")
            p.add_argument("--fx6-still-ael-or-wireless-flash-claimed", action="store_true", help="Claim ILME-FX6 exposes Still [AEL w/ Shutter]/[Wireless Flash]/[External Flash Set.] (invalid)")
            p.add_argument("--interval-play-speed", type=int, default=5, help="Playback [Play Speed for Interval] (1..9, default 5)")
            p.add_argument("--interval-play-speed-capped-at-5-claimed", action="store_true", help="Claim [Play Speed for Interval] stops at 5 instead of 1..9 (invalid)")
            p.add_argument("--in-camera-interval-to-video-render-claimed", action="store_true", help="Claim ILME-FX3 renders Interval Shooting stills to in-camera video (invalid)")
            p.add_argument("--dormant-beauty-effect-requested", action="store_true", help="Request dormant Playback [Beauty Effect] (rejected with EOPNOTSUPP=95)")
            p.add_argument("--dormant-trimming-requested", action="store_true", help="Request dormant Playback [Trimming] (rejected with EOPNOTSUPP=95)")
            p.add_argument("--playback-photo-capture-requested", action="store_true", help="Request Playback [Photo Capture] (blocked on Slot 1 Tier-0 Vault)")
            p.add_argument("--playback-rotate-requested", action="store_true", help="Request Playback [Rotate] (blocked on Slot 1 Tier-0 Vault)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-focus-area-zoom-dci4k-and-sensor-cleaning":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 291 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--summary", action="store_true", help="Emit compact one-line summary to stdout even when --json is passed")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--focus-area", default="WIDE", help="[Focus Area]: WIDE, ZONE, CENTER_FIX, SPOT_S/M/L, EXPAND_SPOT, TRACKING_* (Still-only)")
            p.add_argument("--expect-tracking-focus-area-in-movie", action="store_true", help="Claim Tracking Focus Areas are selectable in Movie/S&Q (invalid: Touch Tracking only)")
            p.add_argument("--focus-area-limit-selected-count", type=int, default=14, help="[Focus Area Limit] enabled checkbox count (2..14)")
            p.add_argument("--switch-vh-af-area", default="OFF", help="[Switch V/H AF Area] (Still-only): OFF, AF_POINT_ONLY, AF_POINT_AND_AF_AREA")
            p.add_argument("--expect-switch-vh-in-movie", action="store_true", help="Claim [Switch V/H AF Area] operates in Movie/S&Q (invalid: Still-only)")
            p.add_argument("--focus-area-color", default="WHITE", help="[Focus Area Color]: WHITE or RED (not resettable via Camera Settings Reset)")
            p.add_argument("--circ-of-focus-point", default="DOES_NOT_CIRCULATE", help="[Circ. of Focus Point]: DOES_NOT_CIRCULATE or CIRCULATE")
            p.add_argument("--af-area-registration-label", default="AF Area Registration", help="Exact ilc/2210 label ('AF Area Registration', not legacy 'AF Area Regist.')")
            p.add_argument("--xlr-h1-zoom-lever-present", action="store_true", help="Claim FX3 XLR-H1 handle carries a physical zoom lever (invalid: hardware absent)")
            p.add_argument("--xlr-h1-rec-button-present", action="store_true", help="Claim FX3 XLR-H1 handle carries a REC button (invalid: hardware absent)")
            p.add_argument("--xlr-h1-zoom-hold-switch-present", action="store_true", help="Claim FX3 XLR-H1 handle carries a ZOOM HOLD switch (invalid: hardware absent)")
            p.add_argument("--fx6-smart-handle-zero-to-99-is-speed-scale", action="store_true", help="Claim FX6 0..99 indicator is Fixed zoom speed scale (invalid: Zoom Position Display)")
            p.add_argument("--zoom-range", default="OPTICAL_ONLY", help="[Zoom Range]: OPTICAL_ONLY, CLEAR_IMAGE_ZOOM, DIGITAL_ZOOM")
            p.add_argument("--zoom-lever-stby-speed", type=int, default=3, help="Body W/T [Zoom Lever Speed] Standby (1..8, default 3)")
            p.add_argument("--zoom-lever-rec-speed", type=int, default=8, help="Body W/T [Zoom Lever Speed] REC (1..8, default 8)")
            p.add_argument("--custom-key-zoom-stby-speed", type=int, default=3, help="[Custom Key Z. Speed] Standby (1..8, default 3)")
            p.add_argument("--custom-key-zoom-rec-speed", type=int, default=3, help="[Custom Key Z. Speed] REC (1..8, default 3)")
            p.add_argument("--remote-zoom-speed-type", default="VARIABLE", help="[Remote Zoom Speed] Speed Type: VARIABLE or FIXED")
            p.add_argument("--remote-zoom-fixed-stby-speed", type=int, default=3, help="[Remote Zoom Speed] Fixed Standby (1..8, default 3)")
            p.add_argument("--remote-zoom-fixed-rec-speed", type=int, default=3, help="[Remote Zoom Speed] Fixed REC (1..8, default 3)")
            p.add_argument("--iso-range-limit-min", type=int, default=50, help="[ISO Range Limit] Minimum (50..409600)")
            p.add_argument("--iso-range-limit-max", type=int, default=409600, help="[ISO Range Limit] Maximum (50..409600)")
            p.add_argument("--iso-auto-min", type=int, default=100, help="[ISO AUTO Minimum]")
            p.add_argument("--iso-auto-max", type=int, default=12800, help="[ISO AUTO Maximum]")
            p.add_argument("--exposure-mode", default="MANUAL_EXPOSURE", help="Exposure mode: PROGRAM_AUTO, APERTURE_PRIORITY, SHUTTER_PRIORITY, MANUAL_EXPOSURE, INTELLIGENT_AUTO, FLEXIBLE_EXP")
            p.add_argument("--iso-mode", default="CINE_EI_BASE", help="ISO mode: CINE_EI_BASE, ISO_AUTO, MANUAL_ISO")
            p.add_argument("--iso-auto-min-ss", default="STANDARD", help="[ISO AUTO Min. SS] (Still P/A + ISO AUTO): SLOWER, SLOW, STANDARD, FAST, FASTER")
            p.add_argument("--iso-auto-min-ss-active", action="store_true", help="Indicate [ISO AUTO Min. SS] is actively controlling shutter threshold")
            p.add_argument("--expect-iso-auto-min-ss-in-movie-or-manual-iso", action="store_true", help="Claim [ISO AUTO Min. SS] operates in Movie/S&Q or manual fixed ISO (invalid)")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, FLEXIBLE_ISO, CINE_EI_QUICK, CINE_EI")
            p.add_argument("--cine-ei-base-iso", type=int, default=800, help="Cine EI Base ISO (800 or 12800)")
            p.add_argument("--expect-iso-variable-in-cine-ei", action="store_true", help="Claim variable ISO operates under Cine EI / Cine EI Quick (invalid: locked to 800/12800)")
            p.add_argument("--shutter-type", default="MECHANICAL_SHUTTER", help="[Shutter Type]: MECHANICAL_SHUTTER or ELECTRONIC_SHUTTER")
            p.add_argument("--silent-mode", default="OFF", help="[Silent Mode]: OFF or ON")
            p.add_argument("--flash-mode", default="FLASH_OFF", help="[Flash Mode] (Mechanical Still only): AUTOFLASH, FILL_FLASH, SLOW_SYNC, REAR_SYNC, FLASH_OFF")
            p.add_argument("--flash-firing-enabled", action="store_true", help="Enable MI-Shoe flash firing (gated to Mechanical-Shutter Still)")
            p.add_argument("--flash-comp-ev", type=float, default=0.0, help="[Flash Comp.] (-3.0..+3.0 EV)")
            p.add_argument("--exp-comp-set", default="AMBIENT_AND_FLASH", help="[Exp.comp.set]: AMBIENT_AND_FLASH or AMBIENT_ONLY")
            p.add_argument("--video-light-mode", default="POWER_LINK", help="[Video Light Mode]: POWER_LINK, REC_LINK, REC_LINK_AND_STBY, AUTO")
            p.add_argument("--mi-shoe-5v-current-ma", type=int, default=0, help="MI-Shoe 5V DC load in mA (<= 900 mA)")
            p.add_argument("--movie-file-format", default="XAVC_S_I_DCI_4K", help="[File Format]: XAVC_S_I_DCI_4K, XAVC_S_I_4K, XAVC_S_4K, XAVC_HS_4K, XAVC_S_I_HD, XAVC_S_HD")
            p.add_argument("--movie-resolution-wh", default="4096x2160", help="Internal movie resolution WxH (4096x2160 for XAVC S-I DCI 4K; 3840x2160 for UHD)")
            p.add_argument("--rec-frame-rate", default="23.98P", help="[Rec Frame Rate]: 23.98P, 24.00P, 25P, 29.97P, 50P, 59.94P, 100P, 119.88P")
            p.add_argument("--stage-b-volatile-tmp-overlay-active", action="store_true", help="Indicate volatile /tmp Stage-B RAM overlay is active")
            p.add_argument("--ack-24p-reboot-wipes-tmp-overlay", action="store_true", help="Acknowledge 24.00p reboot wipes volatile /tmp Stage-B overlays")
            p.add_argument("--expect-24p-no-reboot", action="store_true", help="Claim switching to 24.00p does not reboot ILME-FX3 (invalid: reboot required)")
            p.add_argument("--hdmi-raw-output", action="store_true", help="Enable Type-A HDMI 4264x2408 RAW Output")
            p.add_argument("--sq-dci4k-fps", type=int, default=24, help="S&Q frame rate in XAVC S-I DCI 4K (1..48 fps; 100/120fps locked out)")
            p.add_argument("--bitrate-mbps", type=int, default=240, help="XAVC S-I DCI 4K bitrate in Mbps (240, 250, 300, 500, 600)")
            p.add_argument("--media-speed-grade", default="CFEXPRESS_A_VPG200", help="Card speed grade: CFEXPRESS_A_VPG200, SDXC_V90, SDXC_V60")
            p.add_argument("--still-aspect-ratio", default="3:2", help="Still [Aspect Ratio]: 3:2, 4:3, 16:9, 1:1")
            p.add_argument("--apsc-s35-on", action="store_true", help="Enable [APS-C S35 Shooting]=On (forces JPEG/HEIF L->M step-down)")
            p.add_argument("--still-jpeg-heif-size", default="L", help="Still JPEG/HEIF size: L, M, S")
            p.add_argument("--hlg-still-image", default="OFF", help="[HLG Still Image]: OFF or ON")
            p.add_argument("--camset-card-path", default="/PRIVATE/SONY/SETTING/FX3/CAMSET01.DAT", help="FX3 CAMSET/M1..M4 card path (%%c:%%s/SONY/SETTING/%%s/...; zero PRIVATE/SONY/PRO/CAMERA)")
            p.add_argument("--memory-recall-media-slot", default="SLOT_1", help="[Memory/Recall Media]: SLOT_1 or SLOT_2 (resets to SLOT_1 on Camera Settings Reset)")
            p.add_argument("--fx3-uses-private-sony-pro-camera", action="store_true", help="Claim FX3 writes PRIVATE/SONY/PRO/CAMERA (invalid: FX6-only)")
            p.add_argument("--photo-capture-requested", action="store_true", help="Attempt [Playback] [Photo Capture] (8.3M/2.1M) frame grab")
            p.add_argument("--photo-capture-slot", type=int, default=2, help="Target slot for [Photo Capture] (1 blocked if Tier-0 vault present)")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 forensic dump")
            p.add_argument("--enlarge-initial-mag", default="STANDARD_MAG", help="[Enlarge Initial Mag.]: STANDARD_MAG or PREVIOUS_MAG")
            p.add_argument("--enlarge-initial-position", default="FOCUSED_POSITION", help="[Enlarge Initial Position]: FOCUSED_POSITION or CENTER")
            p.add_argument("--sensor-cleaning-requested", action="store_true", help="Request [Sensor Cleaning] (requires NP-FZ100 >= 51%% + mandatory power OFF)")
            p.add_argument("--battery-soc-pct", type=float, default=88.0, help="NP-FZ100 remaining charge percentage (%%)")
            p.add_argument("--no-mandatory-power-off-after-cleaning", dest="mandatory_power_off_after_cleaning", action="store_false", help="Omit mandatory physical power OFF after [Sensor Cleaning] (blocked)")
            p.add_argument("--unattended-tier0-dump-active", action="store_true", help="Indicate unattended Tier-0 dump is active (blocks [Sensor Cleaning])")
            p.add_argument("--fx6-sensor-cleaning-supported-claimed", action="store_true", help="Claim ILME-FX6 supports ILME-FX3 ultrasonic [Sensor Cleaning] (invalid: e-ND + APR only)")
            p.add_argument("--fx3-has-built-in-end-filter", action="store_true", help="Claim ILME-FX3 has FX6 built-in electronic ND filter (invalid)")
            p.add_argument("--exposure-comp-ev", type=float, default=0.0, help="[Exposure Comp.] EV bias (±5.0 Still / ±2.0 Movie)")
            p.add_argument("--exposure-step", default="0.3EV", help="[Exposure step]: 0.3EV or 0.5EV")
            p.add_argument("--legacy-reset-ev-comp-claimed", action="store_true", help="Claim omitted Alpha [Reset EV Comp.] menu exists in FX3 ilc/2210 UI (invalid)")
            p.add_argument("--focus-mode", default="MF", help="[Focus Mode]: Still 5 (AF-S, AF-A, AF-C, DMF, MF) vs Movie/S&Q 2 (AF-C, MF)")
            p.add_argument("--priority-set-in-af", default="BALANCED_EMPHASIS", help="[Priority Set in AF-S/AF-C]: AF, RELEASE, BALANCED_EMPHASIS")
            p.add_argument("--af-illuminator", default="AUTO", help="[AF Illuminator] (Still-only non-AF-C): AUTO or OFF")
            p.add_argument("--view-mode", default="DATE_VIEW", help="[View Mode]: DATE_VIEW, FOLDER_VIEW_STILL, MOVIE_VIEW")
            p.add_argument("--image-index-mode", default="9_IMAGES", help="[Image Index]: 9_IMAGES or 25_IMAGES (no dormant 12/30)")
            p.add_argument("--display-as-group", default="OFF", help="[Display as Group]: OFF or ON")
            p.add_argument("--display-rotation", default="AUTO", help="[Display Rotation]: AUTO, MANUAL, OFF")
            p.add_argument("--playback-media-slot", type=int, default=1, help="[Select Playback Media] slot (1 or 2)")
            p.add_argument("--playback-rotate-requested", action="store_true", help="Attempt [Playback] [Rotate] EXIF mutation (blocked on read-only Slot 1 Tier-0 Vault)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-pp-scinetone-wb-metering-and-shutter-type":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 284 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--different-set-pp-checked", action="store_true", help="Enable [Different Set for Still/Mv] Picture Profile decoupling (0x62ee)")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, CINE_EI_QUICK, CINE_EI, FLEXIBLE_ISO")
            p.add_argument("--picture-profile", default="OFF", help="[Picture Profile]: OFF, PP1..PP11, PPLUT1..4")
            p.add_argument("--movie-picture-profile", default=None, help="Movie-specific [Picture Profile] when Different Set is checked")
            p.add_argument("--still-picture-profile", default=None, help="Still-specific [Picture Profile] when Different Set is checked")
            p.add_argument("--creative-look", default="-", help="[Creative Look]: '-' (locked), ST, PT, NT, VV, VV2, FL, IN, SH, BW, SE")
            p.add_argument("--dro-mode", default="OFF", help="[D-Range Optimizer]: OFF, AUTO, LV1..LV5")
            p.add_argument("--hlg-still-image", default="OFF", help="[HLG Still Image]: OFF or ON (requires HEIF-only + P/A/S/M)")
            p.add_argument("--movie-gamma-display-assist", default="OFF", help="Movie [Gamma Display Assist]: OFF or ON")
            p.add_argument("--no-internal-recording-active", dest="internal_recording_active", action="store_false", help="Indicate internal card recording is inactive")
            p.add_argument("--hdmi-output-resolution", default="1080P", help="HDMI [Output Resolution]: AUTO, 2160P, 1080P, 1080I")
            p.add_argument("--expect-creative-look-or-dro-active-with-pp-or-log", action="store_true", help="Claim Creative Look/DRO stay active under PP!=Off or Log!=Off (invalid)")
            p.add_argument("--expect-pplut-in-still", action="store_true", help="Claim PPLUT1..4 are available in Still mode (invalid: Movie-only)")
            p.add_argument("--no-pp1-11-custom-params-modified", dest="pp1_11_custom_params_modified", action="store_false", help="Indicate PP1..11 internal params were not customized")
            p.add_argument("--pp-individual-reset-executed", action="store_true", help="Indicate per-profile Picture Profile [Reset] was executed")
            p.add_argument("--claimed-pp1-11-internal-params-wiped", action="store_true", help="Claim Camera Settings Reset/Initialize wiped PP1..11 internal params (invalid)")
            p.add_argument("--claimed-diff-set-checkmarks-wiped", action="store_true", help="Claim Initialize wiped [Different Set] check marks (invalid)")
            p.add_argument("--claimed-pp-active-selector-remains-non-pp11-after-camera-reset", action="store_true", help="Claim active PP selector stayed non-PP11 after Camera Settings Reset (invalid)")
            p.add_argument("--wb-mode", default="C_TEMP_FILTER", help="[White Balance]: AUTO, DAYLIGHT, SHADE, CLOUDY, INCANDESCENT, FLUORESCENT_*, FLASH, UNDERWATER_AUTO, C_TEMP_FILTER, CUSTOM_1, CUSTOM_2, CUSTOM_3")
            p.add_argument("--wb-kelvin-k", type=int, default=5600, help="Color temperature in Kelvin (2500..9900 in 100K steps)")
            p.add_argument("--wb-ab-shift", type=int, default=0, help="Amber-Blue fine shift (-7..+7, A7..B7)")
            p.add_argument("--wb-gm-shift", type=int, default=0, help="Green-Magenta fine shift (-7..+7, G7..M7)")
            p.add_argument("--priority-set-in-awb", default="STANDARD", help="[Priority Set in AWB]: STANDARD, AMBIENCE, WHITE")
            p.add_argument("--shutter-awb-lock", default="OFF", help="[Shutter AWB Lock]: OFF, SHUT_HALF_DOWN, CONT_SHOOTING, BOTH")
            p.add_argument("--shockless-wb", default="1", help="[Shockless WB]: OFF, 1, 2, 3")
            p.add_argument("--custom-wb-setup-requested", action="store_true", help="Request Custom WB [Custom Setup] calibration (blocked under Log/S-Log3/PPLUT)")
            p.add_argument("--no-custom-wb-survives-camera-reset", dest="custom_wb_survives_camera_reset", action="store_false", help="Claim Custom 1..3 is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--no-custom-wb-excluded-from-camset", dest="custom_wb_excluded_from_camset", action="store_false", help="Claim Custom 1..3 is included in CAMSET (invalid)")
            p.add_argument("--no-shutter-awb-lock-survives-camera-reset", dest="shutter_awb_lock_survives_camera_reset", action="store_false", help="Claim [Shutter AWB Lock] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--claimed-custom-wb-saved-in-camset", action="store_true", help="Claim Custom 1..3 was saved into CAMSET .DAT (invalid)")
            p.add_argument("--claimed-custom-wb-wiped-by-camera-reset", action="store_true", help="Claim Custom 1..3 was wiped by Camera Settings Reset (invalid)")
            p.add_argument("--metering-mode", default="MULTI", help="[Metering Mode]: MULTI, CENTER, SPOT_STANDARD, SPOT_LARGE, ENTIRE_SCREEN_AVG, HIGHLIGHT")
            p.add_argument("--desqueeze-display", default="OFF", help="[De-Squeeze Display]: OFF, 1.3x, 1.5x, 1.6x, 1.8x, 2.0x")
            p.add_argument("--face-priority-in-multi-metering", default="ON", help="[Face Prty in Mlti Mtr]: ON or OFF (forced OFF under De-Squeeze!=Off)")
            p.add_argument("--spot-metering-point", default="CENTER", help="[Spot Metering Point]: CENTER or FOCUS_POINT_LINK")
            p.add_argument("--ael-with-shutter", default="AUTO", help="[AEL w/ Shutter]: AUTO, ON, OFF")
            p.add_argument("--no-ael-with-shutter-survives-camera-reset", dest="ael_with_shutter_survives_camera_reset", action="store_false", help="Claim [AEL w/ Shutter] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--cine-ei-base-iso", type=int, default=800, help="Cine EI Base ISO (800 or 12800)")
            p.add_argument("--expect-metering-changes-cine-ei-iso", action="store_true", help="Claim Metering Mode changes Cine EI Base ISO (invalid: M.M. only)")
            p.add_argument("--raw-file-type", default="COMPRESSED", help="Still [RAW File Type]: COMPRESSED or UNCOMPRESSED (stock FX3 2-option)")
            p.add_argument("--lossless-comp-exposed-in-fx3-ui", action="store_true", help="Claim dormant Lossless Comp 0x6b56 is exposed in stock FX3 UI (rejected)")
            p.add_argument("--expect-lossless-comp-raw", action="store_true", help="Request dormant Lossless Comp RAW (rejected on stock ILME-FX3)")
            p.add_argument("--jh-file-type", default="JPEG", help="[JPEG/HEIF Switch]: JPEG or HEIF")
            p.add_argument("--still-file-format", default="RAW", help="Still [File Format]: RAW, RAW_AND_JH, JH")
            p.add_argument("--exposure-mode", default="MANUAL_EXPOSURE", help="Exposure mode: PROGRAM_AUTO, APERTURE_PRIORITY, SHUTTER_PRIORITY, MANUAL_EXPOSURE, INTELLIGENT_AUTO, FLEXIBLE_EXP")
            p.add_argument("--dro-bracket-active", action="store_true", help="Enable DRO Bracketing (locked out by HLG Still Image=On)")
            p.add_argument("--color-space", default="SRGB", help="[Color Space]: SRGB or ADOBERGB")
            p.add_argument("--still-file-prefix", default="DSC", help="Still [Set File Name] 3-char prefix (no leading '_')")
            p.add_argument("--expected-dcf-sample-filename", default="DSC00001.ARW", help="Expected DCF 2.0 sample filename (DSC00001.* for sRGB, _DSC0001.* for AdobeRGB)")
            p.add_argument("--shutter-type", default="MECHANICAL_SHUTTER", help="[Shutter Type]: MECHANICAL_SHUTTER or ELECTRONIC_SHUTTER (no Auto)")
            p.add_argument("--shutter-type-auto-exposed-in-fx3-ui", action="store_true", help="Claim [Shutter Type]=Auto is exposed in FX3 UI (rejected)")
            p.add_argument("--expect-shutter-type-auto", action="store_true", help="Request [Shutter Type]=Auto (rejected on ILME-FX3)")
            p.add_argument("--silent-mode", default="OFF", help="[Silent Mode]: OFF or ON")
            p.add_argument("--audio-signals", default="ON", help="[Audio signals]: ON, OFF_SHUTTER_ONLY, OFF")
            p.add_argument("--e-front-curtain-shutter", default="ON", help="[e-Front Curtain Shut.]: ON or OFF")
            p.add_argument("--no-e-front-curtain-survives-camera-reset", dest="e_front_curtain_survives_camera_reset", action="store_false", help="Claim [e-Front Curtain Shut.] is wiped by Camera Settings Reset (invalid)")
            p.add_argument("--flash-sync-denominator", type=int, default=250, help="Mechanical flash sync denominator (>=250 for <=1/250 s)")
            p.add_argument("--flash-enabled", action="store_true", help="Enable flash firing (locked out by Electronic Shutter/Silent Mode)")
            p.add_argument("--long-exposure-nr", default="ON", help="[Long Exposure NR]: ON or OFF (locked out by Electronic Shutter)")
            p.add_argument("--bulb-enabled", action="store_true", help="Enable BULB exposure (locked out by Electronic Shutter/Silent Mode)")
            p.add_argument("--anti-flicker-shoot", default="OFF", help="[Anti-flicker Shoot.]: OFF or ON (locked out by Electronic Shutter)")
            p.add_argument("--high-iso-nr", default="NORMAL", help="[High ISO NR]: NORMAL, LOW, OFF")
            p.add_argument("--expect-high-iso-nr-applies-to-raw", action="store_true", help="Claim High ISO NR applies to RAW files (invalid)")
            p.add_argument("--drive-mode", default="SINGLE_SHOOTING", help="[Drive Mode]: SINGLE_SHOOTING, CONT_HI_PLUS, CONT_HI, CONT_MID, CONT_LO, SELF_TIMER, SELF_TIMER_CONT, BRACKET")
            p.add_argument("--cont-fps", type=int, default=10, help="Continuous shooting fps (Hi+ ceiling 10 fps)")
            p.add_argument("--aperture-f-number", type=float, default=2.8, help="Aperture F-number (Hi+/Hi/Mid locks AF above F11)")
            p.add_argument("--expect-af-tracks-all-frames-above-f11", action="store_true", help="Claim AF tracks all frames in Hi+ above F11 (invalid)")
            p.add_argument("--expect-10fps-with-uncompressed-or-flash", action="store_true", help="Claim Hi+ stays 10 fps with Uncompressed RAW or Flash (invalid)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-usb-mode-hdmi-info-protect-and-network-reset":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 279 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--usb-mode", dest="usb_connection_mode", default="SEL_WHEN_CONNECT", help="[USB Connection Mode]: SEL_WHEN_CONNECT, MASS_STORAGE, MTP, REMOTE_SHOOT, USB_LAN")
            p.add_argument("--expect-usb-streaming-uvc", action="store_true", help="Claim FX3 UI exposes [USB Streaming] UVC/UAC (rejected: NOUVC)")
            p.add_argument("--usb-streaming-exposed-in-fx3-ui", action="store_true", help="Mark [USB Streaming] UVC/UAC exposed in stock FX3 UI (rejected)")
            p.add_argument("--dormant-uvc-kmod-insmodded", action="store_true", help="Indicate dormant usb_f_uvc.ko was insmodded (blocked)")
            p.add_argument("--non-airgapped-bench", dest="air_gapped_bench", action="store_false", help="Indicate bench is not air-gapped")
            p.add_argument("--usb-data-lines-not-isolated", dest="usb_data_lines_physically_isolated", action="store_false", help="Indicate USB D+/D-/SS data lines are not physically isolated")
            p.add_argument("--host-usb-data-enumeration-active", action="store_true", help="Indicate host USB data enumeration is active (blocked on air-gapped bench)")
            p.add_argument("--usb-lun-setting", default="MULTI", help="[USB LUN Setting]: MULTI or SINGLE")
            p.add_argument("--usb-power-supply", default="ON", help="[USB Power Supply]: ON or OFF")
            p.add_argument("--power-source", default="USB_PD_BODY", help="Power source: USB_PD_BODY, INTERNAL_NP_FZ100, DC_C1_COUPLER")
            p.add_argument("--usb-power-terminal", default="USB_TYPE_C", help="USB power terminal: USB_TYPE_C (MULTI_MICRO_USB forbidden)")
            p.add_argument("--no-np-fz100-inserted", dest="np_fz100_battery_inserted", action="store_false", help="Indicate NP-FZ100 battery is NOT inserted (blocks USB PD)")
            p.add_argument("--hdmi-info-display", default="OFF", help="[HDMI Info. Display]: OFF (clean feed) or ON (LCD-blanking)")
            p.add_argument("--no-require-clean-hdmi-feed", dest="require_clean_hdmi_feed", action="store_false", help="Do not require clean HDMI feed")
            p.add_argument("--allow-blank-camera-lcd", dest="require_unblanked_lcd", action="store_false", help="Allow built-in camera LCD to blank")
            p.add_argument("--allow-lcd-blanking-and-osd", action="store_true", help="Explicitly permit LCD blanking and letterboxed OSD under [HDMI Info. Display]=On")
            p.add_argument("--expect-touch-focus-active-when-hdmi-info-on", action="store_true", help="Claim touch-focus stays active when [HDMI Info. Display]=On (invalid)")
            p.add_argument("--expect-full-raster-clean-feed-when-hdmi-info-on", action="store_true", help="Claim full-raster clean feed when [HDMI Info. Display]=On (invalid)")
            p.add_argument("--rec-media-dur-hdmi", dest="rec_media_dur_hdmi_output", default="ON", help="[Rec. Media dur HDMI Output]: ON, OFF, OFF_HDMI_ONLY")
            p.add_argument("--hdmi-raw-output", action="store_true", help="Enable HDMI RAW Output (4K 16-bit RAW & forces [HDMI Info. Display]=Off)")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, CINE_EI_QUICK, CINE_EI, FLEXIBLE_ISO")
            p.add_argument("--picture-profile", default="OFF", help="[Picture Profile]: OFF, PPLUT1..4, PP1..PP11")
            p.add_argument("--hdmi-output-resolution", default="AUTO", help="[Output Resolution]: AUTO, 2160P, 1080P, 1080I")
            p.add_argument("--expect-4k-hdmi-during-internal-log-or-pplut", action="store_true", help="Expect 4K HDMI output during internal Log/PPLUT1..4 recording (invalid: 1080 clamp)")
            p.add_argument("--expect-hdmi-info-on-during-raw-or-hdmi-only", action="store_true", help="Expect [HDMI Info. Display]=On during RAW or Off(HDMI Only) (invalid: forced Off)")
            p.add_argument("--expect-sq-allows-hdmi-only-or-raw", action="store_true", help="Expect S&Q allows Off(HDMI Only) or RAW Output (invalid)")
            p.add_argument("--protect-scope-selected", default="ALL_IN_THIS_FOLDER", help="[Protect] scope: SINGLE_MULTIPLE_IMG, ALL_IN_THIS_FOLDER, ALL_WITH_THIS_DATE, ALL_IMAGES_IN_THIS_GROUP")
            p.add_argument("--no-protected-items-block-delete", dest="protected_items_block_delete", action="store_false", help="Claim protected items do not block [Delete] (invalid)")
            p.add_argument("--expect-copy-preserves-protect", action="store_true", help="Claim file copy preserves [Protect] state (invalid)")
            p.add_argument("--expect-movie-key-mark-without-menu", action="store_true", help="Claim movie Protect key works without menu playback mark (invalid)")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 forensic dump")
            p.add_argument("--slot1-wp-unlocked", dest="slot1_wp_locked", action="store_false", help="Indicate Slot-1 SD physical WP switch is UNLOCKED (blocked)")
            p.add_argument("--no-slot1-format-hard-locked", dest="slot1_format_hard_locked", action="store_false", help="Indicate Slot-1 Format is NOT hard-locked (blocked)")
            p.add_argument("--no-slot1-vault-firewall", dest="slot1_vault_write_firewall_enforced", action="store_false", help="Disable Slot-1 vault write firewall (blocked)")
            p.add_argument("--slot1-format-mode", default="NONE", help="Slot-1 [Format] mode attempted: NONE (allowed), QUICK, FULL")
            p.add_argument("--slot1-delete-requested", action="store_true", help="Attempt Slot-1 Tier-0 vault file delete (hard-blocked)")
            p.add_argument("--expect-protect-blocks-format", action="store_true", help="Claim [Protect] prevents [Format] from erasing files (invalid)")
            p.add_argument("--expect-format-preserves-m1-m4-camset", action="store_true", help="Claim [Format] preserves M1..M4 card settings (invalid)")
            p.add_argument("--no-reset-network-executed", dest="reset_network_set_executed", action="store_false", help="Indicate [Reset Network Set.] was not executed")
            p.add_argument("--no-auto-reboot-on-network-reset", dest="auto_reboot_triggered_on_network_reset", action="store_false", help="Claim [Reset Network Set.] does not trigger auto-reboot (invalid)")
            p.add_argument("--post-reboot-airplane-mode", default="ON", help="Post-reboot [Airplane Mode]: ON (required for zero-RF) or OFF")
            p.add_argument("--no-require-post-reboot-airplane-on", dest="require_post_reboot_airplane_on", action="store_false", help="Do not require post-reboot [Airplane Mode]=On")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-file-settings-gamma-assist-focus-mag-and-videolight":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 275 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--movie-file-number", default="SERIES", help="Movie [File Number]: SERIES or RESET")
            p.add_argument("--movie-file-name-format", default="CAM_ID_PLUS_REEL", help="Movie [File Name Format]: STANDARD, CAM_ID_PLUS_REEL, TITLE, DATE_PLUS_TITLE, TITLE_PLUS_DATE")
            p.add_argument("--camera-id", default="A", help="Movie [Camera ID]: A..Z")
            p.add_argument("--reel-number", type=int, default=1, help="Movie [Reel Number]: 1..999")
            p.add_argument("--camera-position", default="C", help="Movie [Camera Position]: C, L, R")
            p.add_argument("--title-name", default="C", help="Movie [Title Name Settings] <= 37 ASCII chars (default C)")
            p.add_argument("--custom-movie-folder-requested", action="store_true", help="Request custom movie folder outside PRIVATE/M4ROOT/CLIP (blocked)")
            p.add_argument("--still-file-number", default="SERIES", help="Still [File Number]: SERIES or RESET")
            p.add_argument("--still-file-prefix", default="DSC", help="Still 3-char prefix (leading _ rejected, default DSC)")
            p.add_argument("--still-folder-name", default="STANDARD_FORM", help="Still [Folder Name]: STANDARD_FORM or DATE_FORM")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 forensic dump")
            p.add_argument("--still-forced-file-number-reset-slot", type=int, default=None, help="Target slot for [Forced File Number Reset] (1 blocked when Slot-1 holds vault)")
            p.add_argument("--still-create-new-folder-slot", type=int, default=None, help="Target slot for [Create New Folder] (1 blocked when Slot-1 holds vault)")
            p.add_argument("--auto-review", default="OFF", help="[Auto Review]: OFF, 2_SEC, 5_SEC, 10_SEC")
            p.add_argument("--tc-format", default="NDF", help="[TC Format]: NDF or DF (NDF forced on 24.00p/PAL)")
            p.add_argument("--rec-fps", dest="rec_frame_rate_fps", type=float, default=23.98, help="Recording frame rate in fps (default 23.98)")
            p.add_argument("--video-system", default="NTSC", help="Video system: NTSC or PAL")
            p.add_argument("--tc-run", default="FREE_RUN", help="[Time Code Run]: FREE_RUN or REC_RUN")
            p.add_argument("--tc-make", default="PRESET", help="[Time Code Make]: PRESET or REGENERATE")
            p.add_argument("--tcub-disp-setting", default="TC", help="[TC/UB Disp. Setting]: TC or UB")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, CINE_EI_QUICK, CINE_EI, FLEXIBLE_ISO")
            p.add_argument("--gamma-display-assist", default="OFF", help="[Gamma Display Assist]: OFF or ON (locked OFF under Log Shooting)")
            p.add_argument("--gamma-disp-assist-type", default="AUTO", help="[Gamma Disp. Assist Typ.]: AUTO, S_LOG3_TO_709_800PCT, HLG_BT2020, HLG_709")
            p.add_argument("--display-lut", default="ON", help="[Display LUT]: ON or OFF")
            p.add_argument("--select-lut", default="s709", help="[Select LUT]: S-Log3, s709, 709(800%%), User1..User16")
            p.add_argument("--auto-magnifier-in-mf", default="ON", help="[Auto Magnifier in MF]: ON or OFF")
            p.add_argument("--focus-magnif-time", default="NO_LIMIT", help="[Focus Magnif. Time]: NO_LIMIT, 2_SEC, 5_SEC")
            p.add_argument("--initial-focus-mag-still", default="X1_0", help="Still [Initial Focus Mag.]: X1_0 or X4_0")
            p.add_argument("--initial-focus-mag-movie", default="X1_0", help="Movie [Initial Focus Mag.]: X1_0 or X4_0")
            p.add_argument("--af-in-focus-mag", default="ON", help="[AF in Focus Mag.]: ON or OFF")
            p.add_argument("--hdmi-raw-output", action="store_true", help="Enable HDMI RAW Output (locks out Focus Magnifier & 2160P)")
            p.add_argument("--focus-magnifier-active", action="store_true", help="Simulate Focus Magnifier actively engaged")
            p.add_argument("--peaking-display", default="OFF", help="[Peaking Display]: OFF or ON")
            p.add_argument("--peaking-level", default="MID", help="[Peaking Level]: HIGH, MID, LOW")
            p.add_argument("--peaking-color", default="WHITE", help="[Peaking Color]: RED, YELLOW, BLUE, WHITE")
            p.add_argument("--af-illuminator", default="AUTO", help="[AF Illuminator]: AUTO or OFF (still-only)")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: PHOTO, MOVIE, S_AND_Q")
            p.add_argument("--focus-mode", default="MF", help="[Focus Mode]: AF_S, AF_C, DMF, MF")
            p.add_argument("--creators-app-location-linkage", default="OFF", help="Creators' App [Location Information Linkage]: OFF or ON")
            p.add_argument("--airplane-mode", default="ON", help="[Airplane Mode]: ON or OFF")
            p.add_argument("--bluetooth-function", default="OFF", help="[Bluetooth Function]: OFF or ON")
            p.add_argument("--video-light-mode", default="POWER_LINK", help="[Video Light Mode]: POWER_LINK, REC_LINK, REC_LINK_AND_STBY, AUTO")
            p.add_argument("--mi-shoe-5v-current-ma", type=int, default=0, help="MI-Shoe 5V load current in mA (<= 900mA)")
            p.add_argument("--hdmi-resolution", default="AUTO", help="[HDMI Resolution]: AUTO, 2160P, 1080P, 1080I")
            p.add_argument("--rec-media-dur-hdmi", dest="rec_media_dur_hdmi_output", default="ON", help="[Rec. Media dur HDMI Output]: ON, OFF, OFF_HDMI_ONLY")
            p.add_argument("--power-save-start-time", default="OFF", help="[Power Save Start Time]: OFF, 30_MIN, 5_MIN, 2_MIN, 1_MIN, 10_SEC")
            p.add_argument("--auto-power-off-temp", default="HIGH", help="[Auto Power OFF Temp.]: STANDARD or HIGH")
            p.add_argument("--power-source", default="INTERNAL_NP_FZ100", help="Power source: INTERNAL_NP_FZ100, USB_PD_BODY, DC_C1_COUPLER")
            p.add_argument("--non-airgapped-bench", dest="air_gapped_battery_bench", action="store_false", help="Indicate bench is not air-gapped on battery")
            p.add_argument("--power-save-deactivation", dest="power_save_deactivation_conditions", action="append", default=[], help="Active [Power Save Start Time] deactivation condition from the 9 documented conditions")
            p.add_argument("--headless-monitor-power-linkage-mode", default="DOES_NOT_LINK", help="appFw [Power Save by Monitor] headless mode: DOES_NOT_LINK or OPEN_RETURN")
            p.add_argument("--lang", dest="selected_lang", default="en", choices=["en", "japanese", "tchinese", "schinese"], help="BK_LANG (0x02cf019c) language selection")
            p.add_argument("--volume-settings", type=int, default=7, help="[Volume Settings] 0..15 (default 7)")
            p.add_argument("--xlr-h1-attached", action="store_true", help="Indicate XLR-H1 top handle is attached")
            p.add_argument("--four-ch-audio-monitoring", default="CH1_CH2", help="[4ch Audio Monitoring]: CH1_CH2, CH3_CH4, CH1_3_CH2_4, CH1_CH1, CH2_CH2")
            p.add_argument("--delete-confirm", default="CANCEL_FIRST", help="[Delete confirm.]: CANCEL_FIRST or DELETE_FIRST")
            p.add_argument("--delete-pressing-twice", default="OFF", help="[Delete Pressing Twice]: OFF or ON")
            p.add_argument("--slot1-delete-requested", action="store_true", help="Attempt Slot-1 Tier-0 vault file delete (hard-blocked)")
            p.add_argument("--slot1-format-requested", action="store_true", help="Attempt Slot-1 Tier-0 vault format (hard-blocked)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-diffset-customkey-autoslow-and-apsc":
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Phase 261 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--diff-set-transition", default="COMMON_TO_SEPARATE", help="[Different Set for Still/Mv] transition: NONE, COMMON_TO_SEPARATE, SEPARATE_TO_COMMON")
            p.add_argument("--diff-set-shutter-checked", action="store_true", help="Mark Shutter Speed checked in [Different Set for Still/Mv]")
            p.add_argument("--movie-shutter-mode", default="SHUTTER_ANGLE", help="Movie [Shutter Mode]: SHUTTER_ANGLE or SHUTTER_SPEED")
            p.add_argument("--expect-cwb-movie-copy", action="store_true", help="Flag invalid expectation that Custom WB copies to Movie on Common->Separate")
            p.add_argument("--expect-angle-merge", action="store_true", help="Flag invalid expectation that unchecked Shutter Speed merges movie [Shutter Angle]")
            p.add_argument("--rear-dial-assignment", default="ISO/EI", help="[Custom Key/Dial Set.] Rear dial assignment (default ISO/EI)")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 forensic dump")
            p.add_argument("--slot1-wp-unlocked", dest="slot1_wp_locked", action="store_false", help="Indicate Slot 1 SDXC WP physical switch is unlocked")
            p.add_argument("--slot1-custom-key-access", default="O_RDONLY", help="Slot 1 CAMSET01.DAT custom-key access mode: NONE, O_RDONLY, WRITE")
            p.add_argument("--remain-shoot-display", default="NOT_DISPLAYED", help="[Remain Shoot Display]: NOT_DISPLAYED, ALWAYS_DISPLAY, SHOOT_ONLY_DISPLAY")
            p.add_argument("--expect-remain-movie-time", action="store_true", help="Flag invalid expectation that [Remain Shoot Display] shows movie card time")
            p.add_argument("--expect-builtin-evf", action="store_true", help="Flag invalid expectation of built-in EVF or [Finder/Monitor] on ILME-FX3")
            p.add_argument("--auto-slow-shutter", default="ON", help="[Auto Slow Shutter]: ON or OFF")
            p.add_argument("--exposure-ctrl-type", default="FLEXIBLE_EXP_MODE", help="[Exposure Ctrl Type]: P_A_S_M_MODE or FLEXIBLE_EXP_MODE")
            p.add_argument("--exposure-mode", default="MANUAL_EXPOSURE", help="Exposure mode: PROGRAM_AUTO, APERTURE_PRIORITY, SHUTTER_PRIORITY, MANUAL_EXPOSURE, INTELLIGENT_AUTO")
            p.add_argument("--flexible-shutter-mode", default="MANUAL", help="Flexible Exp. shutter mode: AUTO or MANUAL")
            p.add_argument("--iso-mode", default="CINE_EI_BASE", help="ISO mode: ISO_AUTO or manual/Cine EI fixed ISO")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, CINE_EI_QUICK, CINE_EI, FLEXIBLE_ISO")
            p.add_argument("--sq-enabled", dest="sq_mode_enabled", action="store_true", help="Enable S&Q Motion shooting")
            p.add_argument("--expect-auto-slow-active", action="store_true", help="Assert [Auto Slow Shutter] is actively governing exposure")
            p.add_argument("--expect-auto-slow-angle-overlap", action="store_true", help="Flag invalid overlap between [Auto Slow Shutter] and [Shutter Angle]")
            p.add_argument("--hdmi-time-code-output", default="ON", help="[HDMI Output Settings] -> [Time Code Output]: ON or OFF")
            p.add_argument("--hdmi-rec-control", default="OFF", help="[HDMI Output Settings] -> [REC Control]: OFF or ON (requires Time Code Output=ON)")
            p.add_argument("--hdmi-4ch-audio-output", default="CH1_CH2", help="[HDMI Output Settings] -> [4ch Audio Output]: CH1_CH2 or CH3_CH4")
            p.add_argument("--no-mi-shoe-4ch-audio", dest="mi_shoe_4ch_audio_active", action="store_false", help="Indicate 4ch MI-shoe digital audio is inactive")
            p.add_argument("--rec-media-dur-hdmi", dest="rec_media_dur_hdmi_output", default="OFF_HDMI_ONLY", help="[Rec. Media dur HDMI Output]: ON, OFF, OFF_HDMI_ONLY")
            p.add_argument("--breathing-comp", default="OFF", help="[Breathing Comp.]: OFF or ON")
            p.add_argument("--non-compliant-breathing-lens", dest="breathing_comp_compliant_lens", action="store_false", help="Simulate non-compliant lens for [Breathing Comp.]")
            p.add_argument("--hdmi-raw-output", action="store_true", help="Enable 4264x2408 16-bit HDMI RAW Output")
            p.add_argument("--sq-240p-active", dest="sq_240p_or_200p_active", action="store_true", help="Enable S&Q 239.76p/200p high-frame-rate mode")
            p.add_argument("--expect-breathing-still", action="store_true", help="Flag invalid expectation of [Breathing Comp.] on still images")
            p.add_argument("--apsc-s35-shooting", default="AUTO", help="[APS-C S35 Shooting]: AUTO, ON, OFF (locked OFF in 4K/RAW)")
            p.add_argument("--movie-file-format", default="XAVC_S_I_4K", help="Movie file format: XAVC_HS_4K, XAVC_S_4K, XAVC_S_I_4K, XAVC_S_HD, XAVC_S_I_HD")
            p.add_argument("--expect-apsc-in-4k-or-raw", action="store_true", help="Flag invalid expectation of APS-C S35 crop in 4K or HDMI RAW")
            p.add_argument("--face-eye-prior", dest="face_eye_prior_in_af", default="ON", help="[Face/Eye Prior. in AF]: ON or OFF")
            p.add_argument("--face-eye-subject", default="HUMAN", help="[Face/Eye Subject]: HUMAN, ANIMAL, BIRD")
            p.add_argument("--right-left-eye-select", default="AUTO", help="[Right/Left Eye Select]: AUTO, RIGHT_EYE, LEFT_EYE")
            p.add_argument("--face-eye-frame-disp", default="ON", help="[Face/Eye Frame Disp.]: ON or OFF")
            p.add_argument("--expect-ai-subject-recog-menu", action="store_true", help="Flag invalid dedicated AI-unit [Subject Recog in AF] menu expectation")
            p.add_argument("--hdmi-info-display", default="OFF", help="[HDMI Info. Display]: OFF or ON")
            p.add_argument("--expect-eye-frame-clean-hdmi", action="store_true", help="Flag invalid expectation of Face/Eye frame baked onto clean HDMI or RAW")
            p.add_argument("--airplane-mode", default="ON", help="[Airplane Mode]: ON or OFF")
            p.add_argument("--slot1-bodydata-flash-requested", action="store_true", help="Attempt hard-blocked Slot-1 BODYDATA.DAT firmware flash")
            p.add_argument("--release-wo-card", default="DISABLE", help="[Release w/o Card]: DISABLE or ENABLE")
            p.add_argument("--release-wo-lens", default="ENABLE", help="[Release w/o Lens]: ENABLE or DISABLE")
            p.add_argument("--card-inserted-for-movie-rec", action="store_true", help="Indicate writable card inserted for internal movie recording")
            p.add_argument("--movie-internal-rec-requested", action="store_true", help="Request internal movie recording")
            p.add_argument("--expect-movie-rec-without-card", action="store_true", help="Flag invalid expectation of internal movie recording without card")
            p.add_argument("--production-shoot-mode", action="store_true", help="Enforce production shoot [Release w/o Card]=DISABLE guard")
            p.add_argument("--electronic-emount-lens-attached", dest="body_only_or_pl_adapter_bench", action="store_false", help="Indicate electronic E-mount lens attached instead of body-only bench")
            p.add_argument("--audio-rec-level", type=int, default=16, help="[Audio Rec Level] 0..31")
            p.add_argument("--no-disp-audio-meter", dest="disp_audio_meter_enabled", action="store_false", help="Disable audio level meter in DISP (Screen Disp) Set")
            p.add_argument("--expect-v1-audio-level-menu", action="store_true", help="Flag legacy Ver. 1.x standalone [Audio Level Display] menu expectation")
            p.add_argument("--write-copyright-info", default="OFF", help="[Write Copyright Info]: OFF or ON")
            p.add_argument("--photographer-text", default="", help="[Set Photographer] <= 46 ASCII chars")
            p.add_argument("--copyright-text", default="", help="[Set Copyright] <= 46 ASCII chars")
            p.add_argument("--allow-custom-copyright-pii", dest="clean_room_pii_hygiene", action="store_false", help="Disable clean-room zero-PII enforcement")
            p.add_argument("--expect-copyright-movies", action="store_true", help="Flag invalid expectation that [Copyright Info] writes to movies")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-imagedb-touch-shoeaudio-and-lockop":
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write Phase 248 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--recover-image-db", dest="recover_image_db_requested", action="store_true", help="Request [Recover Image DB] repair execution check")
            p.add_argument("--recover-image-db-slot", type=int, default=2, help="Target slot for [Recover Image DB]: 1 or 2")
            p.add_argument("--battery-soc", dest="battery_soc_pct", type=float, default=88.0, help="NP-FZ100 battery SOC percentage (>=20.0%% required for [Recover Image DB])")
            p.add_argument("--low-battery-warning", action="store_true", help="Flag low-battery warning active (blocks [Recover Image DB])")
            p.add_argument("--no-slot1-tier0-dump", dest="slot1_contains_tier0_dump", action="store_false", help="Indicate Slot 1 does NOT hold a Tier-0 forensic dump")
            p.add_argument("--slot1-tier0-unverified", dest="slot1_tier0_sha256_verified", action="store_false", help="Indicate Slot 1 Tier-0 SHA-256 has NOT been verified off-camera")
            p.add_argument("--slot1-wp-unlocked", dest="slot1_wp_locked", action="store_false", help="Indicate Slot 1 SDXC WP physical switch is unlocked")
            p.add_argument("--monitor-flip-direction", default="AUTO", help="[Monitor Flip Direction]: AUTO, HORIZONTAL_FLIP, VERTICAL_FLIP, OFF")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, RESET_NETWORK_SET, INITIALIZE")
            p.add_argument("--expect-playback-inverted-hflip", action="store_true", help="Flag invalid expectation of inverted playback display under [Horizontal Flip]")
            p.add_argument("--af-transition-speed", type=int, default=5, help="[AF Transition Speed] 1..7")
            p.add_argument("--af-subj-shift-sensitivity", type=int, default=5, help="[AF Subj. Shift Sensitivity] 1..5")
            p.add_argument("--touch-operation", default="OFF", help="[Touch Operation]: OFF, ON_PLAYBACK_ONLY, ON")
            p.add_argument("--touch-sensitivity", default="STANDARD", help="[Touch Sensitivity]: STANDARD or SENSITIVE")
            p.add_argument("--swipe-up", default="OPEN_THE_FN_MENU", help="[Swipe Up]: OPEN_THE_FN_MENU or OFF")
            p.add_argument("--touch-func-in-shooting", default="OFF", help="[Touch Func. in Shooting]: OFF, TOUCH_TRACKING, TOUCH_FOCUS")
            p.add_argument("--no-unattended-tier0-dump", dest="unattended_tier0_dump_active", action="store_false", help="Indicate unattended Tier-0 dump is inactive")
            p.add_argument("--emphasized-rec-display", default="ON", help="[Emphasized REC Display]: ON or OFF")
            p.add_argument("--grid-line-display", default="OFF", help="[Grid Line Display]: OFF or ON")
            p.add_argument("--grid-line-type", default="RULE_OF_3RDS_GRID", help="[Grid Line Type]: RULE_OF_3RDS_GRID, SQUARE_GRID, DIAG_PLUS_SQUARE_GRID")
            p.add_argument("--rec-media-dur-hdmi", dest="rec_media_dur_hdmi_output", default="ON", help="[Rec. Media dur HDMI Output]: ON or OFF_HDMI_ONLY")
            p.add_argument("--hdmi-raw-output", action="store_true", help="Enable HDMI RAW output (forces [HDMI Info. Display]=OFF)")
            p.add_argument("--hdmi-info-display", default="OFF", help="[HDMI Info. Display]: OFF or ON")
            p.add_argument("--outdoor-environment", dest="indoor_bench_environment", action="store_false", help="Indicate outdoor daylight rather than indoor bench")
            p.add_argument("--monitor-brightness-mode", default="MANUAL", help="[Monitor Brightness]: MANUAL or SUNNY_WEATHER")
            p.add_argument("--monitor-brightness-level", type=int, default=0, help="[Monitor Brightness] manual level -2..+2")
            p.add_argument("--display-quality", default="STANDARD", help="[Display Quality]: STANDARD or HIGH")
            p.add_argument("--bluetooth-rmt-ctrl", default="OFF", help="[Bluetooth Rmt Ctrl]: OFF or ON")
            p.add_argument("--bluetooth-function", default="OFF", help="[Bluetooth Function]: OFF or ON")
            p.add_argument("--airplane-mode", default="ON", help="[Airplane Mode]: ON or OFF")
            p.add_argument("--expect-ir-remote-usable", action="store_true", help="Flag expectation that IR remote works while [Bluetooth Rmt Ctrl]=ON")
            p.add_argument("--display-from-my-menu", default="OFF", help="[Display From My Menu]: OFF or ON")
            p.add_argument("--shoe-audio-set", default="48KHZ_24BIT_4CH", help="[Shoe Audio Set.]: 48KHZ_16BIT_2CH, 48KHZ_24BIT_2CH, 48KHZ_24BIT_4CH")
            p.add_argument("--audio-recording", default="ON", help="[Audio Recording]: ON or OFF")
            p.add_argument("--sq-enabled", dest="sq_mode_enabled", action="store_true", help="Enable S&Q Motion mode (disables audio & locks out Shoe Audio / Audio Out Timing)")
            p.add_argument("--body-35mm-mic-plugged", action="store_true", help="Indicate body 3.5mm MIC plug is inserted (locks out digital Shoe Audio)")
            p.add_argument("--no-xlr-h1", dest="xlr_h1_attached", action="store_false", help="Indicate XLR-H1 handle is detached")
            p.add_argument("--xlr-h1-mode-switch", default="DIGITAL", help="XLR-H1 [DIGITAL/ANALOG] switch: DIGITAL or ANALOG")
            p.add_argument("--xlr-h1-low-cut-switch", default="OFF", help="XLR-H1 hardware [LOW CUT] switch: OFF, 100HZ, 300HZ")
            p.add_argument("--wind-noise-reduct", default="OFF", help="[Wind Noise Reduct.]: OFF or ON (built-in mic only)")
            p.add_argument("--expect-wind-reduct-ext-mic", action="store_true", help="Flag invalid expectation of [Wind Noise Reduct.] with external mic")
            p.add_argument("--outdoor-windy-audio", dest="indoor_calm_bench_audio", action="store_false", help="Indicate outdoor windy conditions rather than calm indoor bench")
            p.add_argument("--saveload-operation", default="NONE", help="[Save/Load Settings] action: NONE, LOAD, SAVE")
            p.add_argument("--saveload-target", default="SLOT_2", help="[Save/Load Settings] target: SLOT_1, SLOT_2, CLOUD_PRIVATE, CLOUD_SHARE")
            p.add_argument("--camset-slot-index", type=int, default=1, help="CAMSET slot index 1..10")
            p.add_argument("--camset-model-code", default="ILME-FX3", help="CAMSET model identifier (must be ILME-FX3)")
            p.add_argument("--camset-contains-excluded", action="store_true", help="Simulate excluded secrets/calibration inside CAMSET payload")
            p.add_argument("--lock-operation-parts", default="ALL", help="[Lock Operation Parts]: OFF, MULTI_SELECTOR_ONLY, DIAL_PLUS_WHEEL, ALL")
            p.add_argument("--active-key-chord", default="MENU_PLUS_FN_5S", help="Key chord: NONE, FN_HOLD_TOGGLE, MENU_PLUS_FN_5S, MENU_PLUS_DELETE_2S")
            p.add_argument("--lock-chord-hold-seconds", type=float, default=5.0, help="Hold duration in seconds (>=5.0s for MENU+Fn full-body lock)")
            p.add_argument("--destructive-format-chord", action="store_true", help="Simulate destructive MENU+Delete 2s Slot Full Format chord (hard-blocked)")
            p.add_argument("--power-source", default="USB_PD_BODY", help="Power source: INTERNAL_NP_FZ100, USB_PD_BODY, DC_C1_COUPLER")
            p.add_argument("--usb-power-supply", default="ON", help="[USB Power Supply]: ON or OFF")
            p.add_argument("--usb-power-terminal", default="USB_TYPE_C", help="USB power terminal: USB_TYPE_C, MULTI_MICRO_USB, NONE")
            p.add_argument("--usb-lun-setting", default="MULTI", help="[USB LUN Setting]: MULTI or SINGLE")
            p.add_argument("--no-np-fz100-inserted", dest="np_fz100_battery_inserted", action="store_false", help="Simulate missing NP-FZ100 battery pack (blocks power-on / USB PD)")
            p.add_argument("--dc-c1-coupler-inserted", action="store_true", help="Indicate DC-C1 coupler is seated in battery bay")
            p.add_argument("--battery-removed-under-usb-power", action="store_true", help="Simulate removing NP-FZ100 under USB wall power (immediate power-off)")
            p.add_argument("--exposure-step", default="0.3EV", help="[Exposure step]: 0.3EV or 0.5EV")
            p.add_argument("--shutter-mode", default="SHUTTER_ANGLE", help="[Shutter Mode]: SHUTTER_ANGLE or SHUTTER_SPEED")
            p.add_argument("--shutter-angle-deg", type=float, default=180.0, help="[Shutter Angle] in degrees from constant cine table (5.6..360.0)")
            p.add_argument("--expect-exp-step-alters-angle", action="store_true", help="Flag invalid expectation that [Exposure step] alters [Shutter Angle]")
            p.add_argument("--audio-out-timing", default="LIVE", help="[Audio Out Timing]: LIVE or LIP_SYNC")
            p.add_argument("--silent-mode", dest="silent_mode_enabled", action="store_true", help="Enable [Silent Mode] (hard-locks [Audio signals]=OFF)")
            p.add_argument("--audio-signals", dest="audio_signals_mode", default="ON", help="[Audio signals]: ON, OFF_SHUTTER_ONLY, OFF")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-pixelmap-ntscpal-powersave-and-autotemp":
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write Phase 227 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--auto-pixel-mapping", default="ON", help="[Auto Pixel Mapping]: ON or OFF")
            p.add_argument("--days-since-pixel-mapping", type=int, default=0, help="Days since manual [Pixel Mapping] when [Auto Pixel Mapping]=[Off] (<=3 days)")
            p.add_argument("--manual-pixel-mapping", action="store_true", help="Request manual [Pixel Mapping] execution check")
            p.add_argument("--battery-soc", dest="battery_soc_pct", type=float, default=88.0, help="NP-FZ100 battery SOC percentage (>=20.0%% required for [Pixel Mapping])")
            p.add_argument("--tier0-dump-active", action="store_true", help="Indicate active Tier-0 cold dump (blocks [Pixel Mapping])")
            p.add_argument("--unguarded-calibration", action="store_true", help="Flag unguarded cnflasha calibration write attempt (blocked by O_RDONLY firewall)")
            p.add_argument("--ntsc-pal-selector", default="NTSC", help="[NTSC/PAL Selector]: NTSC or PAL")
            p.add_argument("--regional-default-system", default="NTSC", help="Regional factory video system restored only by [Initialize]: NTSC or PAL")
            p.add_argument("--rec-fps", type=float, default=23.98, help="Recording frame rate (e.g. 23.98/29.97/59.94/119.88 NTSC or 25/50/100 PAL)")
            p.add_argument("--tc-format", default="NDF", help="[TC Format]: DF/NDF on NTSC or UNAVAILABLE/PAL_FIXED_25FPS on PAL")
            p.add_argument("--reset-action", default="NONE", help="Reset operation modeled: NONE, CAMERA_SETTINGS_RESET, INITIALIZE")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, ON, CINE_EI, CINE_EI_QUICK, FLEXIBLE_ISO")
            p.add_argument("--gamma-display-assist", default="OFF", help="[Gamma Display Assist]: OFF or ON (locked OFF when Log Shooting is active)")
            p.add_argument("--gamma-disp-assist-type", default="AUTO", help="[Gamma Disp. Assist Typ.]: AUTO, S_LOG3_TO_709_800PCT, HLG_BT2020, HLG_709")
            p.add_argument("--display-lut", default="ON", help="[Display LUT]: ON or OFF")
            p.add_argument("--expect-gamma-assist-hdmi", action="store_true", help="Flag invalid expectation of [Gamma Display Assist] on external HDMI")
            p.add_argument("--file-name-format", default="CAM_ID_PLUS_REEL", help="[File Name Format]: STANDARD, CAM_ID_PLUS_REEL, TITLE, DATE_PLUS_TITLE, TITLE_PLUS_DATE")
            p.add_argument("--file-number-mode", default="SERIES", help="[File Number]: SERIES or RESET")
            p.add_argument("--title-name", default="FX3_BENCH_P227", help="[Title Name Settings] <= 37 ASCII chars")
            p.add_argument("--cam-id", default="A", help="[Cam ID] single uppercase letter A..Z")
            p.add_argument("--reel-number", type=int, default=1, help="[Reel#] 1..999")
            p.add_argument("--slot1-media-type", default="CFEXPRESS_A", help="Slot-1 media type: CFEXPRESS_A, SDXC, SDHC, NONE")
            p.add_argument("--slot2-media-type", default="CFEXPRESS_A", help="Slot-2 media type: CFEXPRESS_A, SDXC, SDHC, NONE")
            p.add_argument("--custom-folder-requested", action="store_true", help="Request custom movie folder name (blocked on SDHC)")
            p.add_argument("--clip-container-format", default="XAVC_S_I_4K", help="Clip container format for Shot Mark1/2 check (MP4/XAVC only)")
            p.add_argument("--shot-mark1-count", type=int, default=1, help="Shot Mark1 count (>=0)")
            p.add_argument("--shot-mark2-count", type=int, default=1, help="Shot Mark2 count (>=0)")
            p.add_argument("--image-jump-setting", default="SHOT_MARK_ONLY", help="[Image Jump Setting] playback filter mode")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: MOVIE, S_AND_Q, PHOTO")
            p.add_argument("--no-simult-recording", dest="simult_recording", action="store_false", help="Disable Dual-Slot Simult. Recording")
            p.add_argument("--tc-make", default="PRESET", help="[Time Code Make]: PRESET or REGENERATE")
            p.add_argument("--tc-run", default="FREE_RUN", help="[Time Code Run]: FREE_RUN or REC_RUN")
            p.add_argument("--tc-regen-slot", type=int, default=1, help="Reference slot for [Time Code Make]=[Regenerate] (must be Slot 1)")
            p.add_argument("--external-tc-jam-was-active", action="store_true", help="Indicate prior external VMC-BNCM1 EXT-LK jam was active")
            p.add_argument("--vmc-bncm1-ext-lk-required", action="store_true", help="Require external VMC-BNCM1 EXT-LK lock (Movie + Preset + Free Run)")
            p.add_argument("--rec-lamp-mode", default="ONLY_FRONT_OFF", help="[REC Lamp]: ALL_ON, ONLY_FRONT_OFF, OFF, ALL_OFF")
            p.add_argument("--no-xlr-h1", dest="xlr_h1_attached", action="store_false", help="Indicate XLR-H1 top handle is detached")
            p.add_argument("--silent-mode", action="store_true", help="Enable [Silent Mode] (requires [Audio signals]=OFF)")
            p.add_argument("--audio-signals", default="ON", help="[Audio signals]: ON, OFF_SHUTTER_ONLY, OFF")
            p.add_argument("--power-save-start-time", default="OFF", help="[Power Save Start Time]: OFF, 30_MIN, 5_MIN, 2_MIN, 1_MIN, 10_SEC")
            p.add_argument("--power-source", default="INTERNAL_NP_FZ100", help="Power source: INTERNAL_NP_FZ100, USB_PD_BODY, DC_C1_COUPLER")
            p.add_argument("--usb-power-supply-active", dest="usb_power_supply_active", action="store_true", default=None, help="Bypass Condition #1: USB Power Supply active")
            p.add_argument("--slideshow-active", action="store_true", help="Bypass Condition #2: Slideshow Playback active")
            p.add_argument("--ftp-transfer-active", action="store_true", help="Bypass Condition #3: FTP Transfer active")
            p.add_argument("--movie-recording-active", action="store_true", help="Bypass Condition #4: Movie Recording active")
            p.add_argument("--computer-connection-active", action="store_true", help="Bypass Condition #5: Computer USB Connection active")
            p.add_argument("--hdmi-tv-connection-active", action="store_true", help="Bypass Condition #6: TV/HDMI Connection active")
            p.add_argument("--ir-remote-ctrl-on", action="store_true", help="Bypass Condition #7: [IR Remote Ctrl]=[On]")
            p.add_argument("--bluetooth-rmt-ctrl-on", action="store_true", help="Bypass Condition #8: [Bluetooth Rmt Ctrl]=[On]")
            p.add_argument("--streaming-or-cloud-active", action="store_true", help="Bypass Condition #9: Streaming / Creators' Cloud Upload active")
            p.add_argument("--no-p3-cold-dump", dest="p3_75mib_cold_dump_active", action="store_false", help="Indicate 75 MiB p3 Tier-0 cold dump is inactive")
            p.add_argument("--auto-power-off-temp", default="HIGH", help="[Auto Power OFF Temp.]: HIGH or STANDARD")
            p.add_argument("--no-tripod-mounted", dest="tripod_mounted", action="store_false", help="Indicate camera is NOT tripod-mounted")
            p.add_argument("--handheld-active", action="store_true", help="Indicate handheld shooting is active (blocked under Auto Power OFF Temp.=HIGH)")
            p.add_argument("--fan-mode", dest="fan_control_mode", default="AUTO", help="[Fan Control]: AUTO, MINIMUM, OFF_IN_REC, ALWAYS_OFF")
            p.add_argument("--body-temp-c", type=float, default=29.5, help="Camera body temperature in Celsius (< 45.0C)")
            p.add_argument("--steadyshot-mode", default="STANDARD", help="Movie [SteadyShot]: OFF, STANDARD, ACTIVE")
            p.add_argument("--steadyshot-focal-mm", type=int, default=35, help="Manual SteadyShot focal length in mm (8..1000)")
            p.add_argument("--sq-enabled", action="store_true", help="Enable S&Q mode")
            p.add_argument("--sq-fps", type=float, default=60.0, help="S&Q frame rate")
            p.add_argument("--hdmi-raw-output", action="store_true", help="Enable HDMI RAW Output (disables SteadyShot Active)")
            p.add_argument("--zoom-mode", default="OPTICAL_ONLY", help="Zoom mode: OPTICAL_ONLY, CLEAR_IMAGE_ZOOM, DIGITAL_ZOOM")
            p.add_argument("--zoom-scale", type=float, default=1.0, help="Zoom scale factor (1.0 optical; <=1.5x 4K CIZ; <=2.0x HD CIZ; <=4.0x Digital)")
            p.add_argument("--video-resolution-class", default="4K", help="Video resolution class: 4K or HD")
            p.add_argument("--still-file-format", default="NONE", help="Still file format: NONE, JPEG, HEIF, RAW, ARW")
            p.add_argument("--ciz-focus-area-unlocked", dest="ciz_focus_area_center_locked", action="store_false", help="Simulate Focus Area not center-locked under CIZ")
            p.add_argument("--ciz-metering-mode", default="MULTI", help="Metering mode under CIZ (must be MULTI)")
            p.add_argument("--ciz-face-eye-enabled", dest="ciz_face_eye_disabled", action="store_false", help="Simulate Face/Eye Priority still enabled under CIZ")
            p.add_argument("--ciz-tracking-enabled", dest="ciz_tracking_disabled", action="store_false", help="Simulate Real-time Tracking still enabled under CIZ")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-hdmi-proxy-desqueeze-and-simult":
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write Phase 216 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-bench-dry-run", "--simulate-ready-bench", dest="simulate_bench_dry_run", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--desqueeze-ratio", default="OFF", help="Anamorphic De-Squeeze Display ratio: Off, 1.3x, 1.5x, 1.6x, 1.8x, 2.0x")
            p.add_argument("--hdmi-raw-output", action="store_true", help="Indicate HDMI 16-bit RAW output is enabled")
            p.add_argument("--rec-media-dur-hdmi", default="ON", help="[Rec. Media dur HDMI Output]: ON or OFF_HDMI_ONLY")
            p.add_argument("--no-require-internal-card-rec", dest="require_internal_card_rec", action="store_false", help="Allow external-only HDMI capture when acknowledged")
            p.add_argument("--ack-hdmi-only-no-card-rec", action="store_true", help="Acknowledge that [Off(HDMI Only)] disables internal card recording")
            p.add_argument("--log-shooting-mode", default="CINE_EI", help="[Log Shooting]: OFF, CINE_EI, CINE_EI_QUICK, FLEXIBLE_ISO")
            p.add_argument("--picture-profile", default="OFF", help="[Picture Profile], e.g. OFF or PPLUT1..PPLUT4")
            p.add_argument("--hdmi-info-display", default="OFF", help="[HDMI Info. Display]: OFF or ON (ON blanks built-in camera LCD)")
            p.add_argument("--allow-blank-camera-lcd", dest="require_unblanked_lcd", action="store_false", help="Allow built-in camera LCD blanking when [HDMI Info. Display]=[On]")
            p.add_argument("--mc-focus-map-enabled", action="store_true", help="Enable external Monitor & Control Focus Map (<150fps ceiling)")
            p.add_argument("--mc-sensor-fps", type=float, default=23.98, help="Sensor frame rate for external Monitor & Control Focus Map (<150fps)")
            p.add_argument("--no-simult-recording", dest="simult_recording", action="store_false", help="Disable Dual-Slot Simult. Recording")
            p.add_argument("--auto-switch-media", default="OFF", help="[Auto Switch Media]: OFF (strict 1:1 dual vault) or ON")
            p.add_argument("--allow-auto-switch-rollover", dest="require_strict_vault_parity", action="store_false", help="Allow single-card rollover under Auto Switch Media=ON")
            p.add_argument("--slot1-media-type", default="CFEXPRESS_A", help="Slot-1 media type: CFEXPRESS_A, SDXC, SDHC, NONE")
            p.add_argument("--slot2-media-type", default="CFEXPRESS_A", help="Slot-2 media type: CFEXPRESS_A, SDXC, SDHC, NONE")
            p.add_argument("--slot1-capacity-gb", type=int, default=160, help="Slot-1 capacity in GB")
            p.add_argument("--slot2-capacity-gb", type=int, default=160, help="Slot-2 capacity in GB")
            p.add_argument("--no-proxy-enabled", dest="proxy_enabled", action="store_false", help="Disable Px proxy recording")
            p.add_argument("--proxy-format", default="XAVC_HS_HD", help="Px proxy format: XAVC_HS_HD or XAVC_S_HD")
            p.add_argument("--rec-fps", type=float, default=23.98, help="Main recording frame rate (<100p required for Px proxy)")
            p.add_argument("--sq-enabled", action="store_true", help="Enable S&Q mode")
            p.add_argument("--sq-fps", type=float, default=60.0, help="S&Q sensor frame rate (<100fps required for Px proxy)")
            p.add_argument("--file-name-format", default="CAM_ID_PLUS_REEL", help="[File Name Format]: STANDARD, CAM_ID_PLUS_REEL, TITLE, DATE_PLUS_TITLE, TITLE_PLUS_DATE")
            p.add_argument("--file-number-mode", default="SERIES", help="[File Number]: SERIES or RESET")
            p.add_argument("--title-name", default="FX3_BENCH_A", help="[Title Name Settings] <= 37 ASCII chars")
            p.add_argument("--shoot-mode", default="MOVIE", help="[Shoot Mode]: MOVIE, S_AND_Q, PHOTO")
            p.add_argument("--tc-make", default="PRESET", help="[Time Code Make]: PRESET or REGENERATE")
            p.add_argument("--tc-run", default="FREE_RUN", help="[Time Code Run]: FREE_RUN or REC_RUN")
            p.add_argument("--vmc-bncm1-ext-lk-required", action="store_true", help="Require VMC-BNCM1 EXT-LK lock (Movie + Preset + Free Run)")
            p.add_argument("--rec-lamp-mode", default="ONLY_FRONT_OFF", help="[REC Lamp]: ALL_ON, ONLY_FRONT_OFF, ALL_OFF")
            p.add_argument("--silent-mode", action="store_true", help="Enable [Silent Mode] (requires [Audio signals]=OFF)")
            p.add_argument("--audio-signals", default="ON", help="[Audio signals]: ON, OFF_SHUTTER_ONLY, OFF")
            p.add_argument("--shockless-wb-mode", default="1", help="[Shockless WB]: OFF, 1, 2, 3")
            p.add_argument("--wb-kelvin-k", type=int, default=5600, help="White balance color temperature (2500..9900K)")
            p.add_argument("--receipt-a", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy A")
            p.add_argument("--receipt-b", type=Path, default=None, help="Path to Tier-0 528-byte FX3RCPT1 receipt Copy B (distinct st_dev)")
            p.add_argument("--model-id", default=None, help="Expected Sony PRODUCT_MODEL hex/int (default 0x91030080)")
            p.add_argument("--body-fw", default="7.02", help="Target FX3 body firmware version (7.02)")
            p.add_argument("--body-serial", default=None, help="Target FX3 body serial identifier")
            p.add_argument("--emmc-cid", default=None, help="Target FX3 128-bit eMMC CID hex identifier")
        if cmd_name == "preflight-bench-cable-fan-slot1":
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write Phase 204 preflight report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force deterministic clean-room synthetic verification mode")
            p.add_argument("--simulate-ready-bench", action="store_true", help="Synthesize deterministic dry-run Tier-0 dual-media receipts without authorizing live hardware attachment")
            p.add_argument("--power-source", default="USB_PD_BODY", help="Bench power mode: USB_PD_BODY or DC_C1_COUPLER")
            p.add_argument("--battery-soc", type=float, default=88.0, help="NP-FZ100 battery state-of-charge percentage (>= 51.0%% for USB_PD_BODY)")
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
    if args.cmd == "verify-milestone-209":
        return _cmd_verify_milestone_209(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "preflight-hdmi-proxy-desqueeze-and-simult":
        return _cmd_preflight_hdmi_proxy_desqueeze_and_simult(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.markdown_out,
            args.output,
            args.desqueeze_ratio,
            args.hdmi_raw_output,
            args.rec_media_dur_hdmi,
            args.require_internal_card_rec,
            args.ack_hdmi_only_no_card_rec,
            args.log_shooting_mode,
            args.picture_profile,
            args.hdmi_info_display,
            args.require_unblanked_lcd,
            args.mc_focus_map_enabled,
            args.mc_sensor_fps,
            args.simult_recording,
            args.auto_switch_media,
            args.require_strict_vault_parity,
            args.slot1_media_type,
            args.slot2_media_type,
            args.slot1_capacity_gb,
            args.slot2_capacity_gb,
            args.proxy_enabled,
            args.proxy_format,
            args.rec_fps,
            args.sq_enabled,
            args.sq_fps,
            args.file_name_format,
            args.file_number_mode,
            args.title_name,
            args.shoot_mode,
            args.tc_make,
            args.tc_run,
            args.vmc_bncm1_ext_lk_required,
            args.rec_lamp_mode,
            args.silent_mode,
            args.audio_signals,
            args.shockless_wb_mode,
            args.wb_kelvin_k,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "verify-milestone-221":
        return _cmd_verify_milestone_221(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "preflight-pixelmap-ntscpal-powersave-and-autotemp":
        return _cmd_preflight_pixelmap_ntscpal_powersave_and_autotemp(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.markdown_out,
            args.output,
            args.auto_pixel_mapping,
            args.days_since_pixel_mapping,
            args.manual_pixel_mapping,
            args.battery_soc_pct,
            args.tier0_dump_active,
            args.unguarded_calibration,
            args.ntsc_pal_selector,
            args.regional_default_system,
            args.rec_fps,
            args.tc_format,
            args.reset_action,
            args.log_shooting_mode,
            args.gamma_display_assist,
            args.gamma_disp_assist_type,
            args.display_lut,
            args.expect_gamma_assist_hdmi,
            args.file_name_format,
            args.file_number_mode,
            args.title_name,
            args.cam_id,
            args.reel_number,
            args.slot1_media_type,
            args.slot2_media_type,
            args.custom_folder_requested,
            args.clip_container_format,
            args.shot_mark1_count,
            args.shot_mark2_count,
            args.image_jump_setting,
            args.shoot_mode,
            args.simult_recording,
            args.tc_make,
            args.tc_run,
            args.tc_regen_slot,
            args.external_tc_jam_was_active,
            args.vmc_bncm1_ext_lk_required,
            args.rec_lamp_mode,
            args.xlr_h1_attached,
            args.silent_mode,
            args.audio_signals,
            args.power_save_start_time,
            args.power_source,
            args.usb_power_supply_active,
            args.slideshow_active,
            args.ftp_transfer_active,
            args.movie_recording_active,
            args.computer_connection_active,
            args.hdmi_tv_connection_active,
            args.ir_remote_ctrl_on,
            args.bluetooth_rmt_ctrl_on,
            args.streaming_or_cloud_active,
            args.p3_75mib_cold_dump_active,
            args.auto_power_off_temp,
            args.tripod_mounted,
            args.handheld_active,
            args.fan_control_mode,
            args.body_temp_c,
            args.steadyshot_mode,
            args.steadyshot_focal_mm,
            args.sq_enabled,
            args.sq_fps,
            args.hdmi_raw_output,
            args.zoom_mode,
            args.zoom_scale,
            args.video_resolution_class,
            args.still_file_format,
            args.ciz_focus_area_center_locked,
            args.ciz_metering_mode,
            args.ciz_face_eye_disabled,
            args.ciz_tracking_disabled,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "verify-milestone-233":
        return _cmd_verify_milestone_233(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "preflight-imagedb-touch-shoeaudio-and-lockop":
        return _cmd_preflight_imagedb_touch_shoeaudio_and_lockop(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.markdown_out,
            args.output,
            args.recover_image_db_requested,
            args.recover_image_db_slot,
            args.battery_soc_pct,
            args.low_battery_warning,
            args.slot1_contains_tier0_dump,
            args.slot1_tier0_sha256_verified,
            args.slot1_wp_locked,
            args.monitor_flip_direction,
            args.reset_action,
            args.expect_playback_inverted_hflip,
            args.af_transition_speed,
            args.af_subj_shift_sensitivity,
            args.touch_operation,
            args.touch_sensitivity,
            args.swipe_up,
            args.touch_func_in_shooting,
            args.unattended_tier0_dump_active,
            args.emphasized_rec_display,
            args.grid_line_display,
            args.grid_line_type,
            args.rec_media_dur_hdmi_output,
            args.hdmi_raw_output,
            args.hdmi_info_display,
            args.indoor_bench_environment,
            args.monitor_brightness_mode,
            args.monitor_brightness_level,
            args.display_quality,
            args.bluetooth_rmt_ctrl,
            args.bluetooth_function,
            args.airplane_mode,
            args.expect_ir_remote_usable,
            args.display_from_my_menu,
            args.shoe_audio_set,
            args.audio_recording,
            args.sq_mode_enabled,
            args.body_35mm_mic_plugged,
            args.xlr_h1_attached,
            args.xlr_h1_mode_switch,
            args.xlr_h1_low_cut_switch,
            args.wind_noise_reduct,
            args.expect_wind_reduct_ext_mic,
            args.indoor_calm_bench_audio,
            args.saveload_operation,
            args.saveload_target,
            args.camset_slot_index,
            args.camset_model_code,
            args.camset_contains_excluded,
            args.lock_operation_parts,
            args.active_key_chord,
            args.lock_chord_hold_seconds,
            args.destructive_format_chord,
            args.power_source,
            args.usb_power_supply,
            args.usb_power_terminal,
            args.usb_lun_setting,
            args.np_fz100_battery_inserted,
            args.dc_c1_coupler_inserted,
            args.battery_removed_under_usb_power,
            args.exposure_step,
            args.shutter_mode,
            args.shutter_angle_deg,
            args.expect_exp_step_alters_angle,
            args.audio_out_timing,
            args.silent_mode_enabled,
            args.audio_signals_mode,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "verify-milestone-254":
        return _cmd_verify_milestone_254(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "preflight-diffset-customkey-autoslow-and-apsc":
        return _cmd_preflight_diffset_customkey_autoslow_and_apsc(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.markdown_out,
            args.output,
            args.reset_action,
            args.diff_set_transition,
            args.diff_set_shutter_checked,
            args.movie_shutter_mode,
            args.expect_cwb_movie_copy,
            args.expect_angle_merge,
            args.rear_dial_assignment,
            args.slot1_contains_tier0_dump,
            args.slot1_wp_locked,
            args.slot1_custom_key_access,
            args.remain_shoot_display,
            args.expect_remain_movie_time,
            args.expect_builtin_evf,
            args.auto_slow_shutter,
            args.exposure_ctrl_type,
            args.exposure_mode,
            args.flexible_shutter_mode,
            args.iso_mode,
            args.log_shooting_mode,
            args.sq_mode_enabled,
            args.expect_auto_slow_active,
            args.expect_auto_slow_angle_overlap,
            args.hdmi_time_code_output,
            args.hdmi_rec_control,
            args.hdmi_4ch_audio_output,
            args.mi_shoe_4ch_audio_active,
            args.rec_media_dur_hdmi_output,
            args.breathing_comp,
            args.breathing_comp_compliant_lens,
            args.hdmi_raw_output,
            args.sq_240p_or_200p_active,
            args.expect_breathing_still,
            args.apsc_s35_shooting,
            args.movie_file_format,
            args.expect_apsc_in_4k_or_raw,
            args.face_eye_prior_in_af,
            args.face_eye_subject,
            args.right_left_eye_select,
            args.face_eye_frame_disp,
            args.expect_ai_subject_recog_menu,
            args.hdmi_info_display,
            args.expect_eye_frame_clean_hdmi,
            args.airplane_mode,
            args.slot1_bodydata_flash_requested,
            args.release_wo_card,
            args.release_wo_lens,
            args.card_inserted_for_movie_rec,
            args.movie_internal_rec_requested,
            args.expect_movie_rec_without_card,
            args.production_shoot_mode,
            args.body_only_or_pl_adapter_bench,
            args.audio_rec_level,
            args.disp_audio_meter_enabled,
            args.expect_v1_audio_level_menu,
            args.write_copyright_info,
            args.photographer_text,
            args.copyright_text,
            args.clean_room_pii_hygiene,
            args.expect_copyright_movies,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "verify-milestone-264":
        return _cmd_verify_milestone_264(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "verify-milestone-295":
        return _cmd_verify_milestone_295(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "verify-milestone-311":
        return _cmd_verify_milestone_311(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "verify-milestone-324":
        return _cmd_verify_milestone_324(
            args.repo_root,
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.markdown_out,
            args.output,
        )
    if args.cmd == "preflight-file-settings-gamma-assist-focus-mag-and-videolight":
        return _cmd_preflight_file_settings_gamma_assist_focus_mag_and_videolight(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.markdown_out,
            args.output,
            args.reset_action,
            args.movie_file_number,
            args.movie_file_name_format,
            args.camera_id,
            args.reel_number,
            args.camera_position,
            args.title_name,
            args.custom_movie_folder_requested,
            args.still_file_number,
            args.still_file_prefix,
            args.still_folder_name,
            args.slot1_contains_tier0_dump,
            args.still_forced_file_number_reset_slot,
            args.still_create_new_folder_slot,
            args.auto_review,
            args.tc_format,
            args.rec_frame_rate_fps,
            args.video_system,
            args.tc_run,
            args.tc_make,
            args.tcub_disp_setting,
            args.log_shooting_mode,
            args.gamma_display_assist,
            args.gamma_disp_assist_type,
            args.display_lut,
            args.select_lut,
            args.auto_magnifier_in_mf,
            args.focus_magnif_time,
            args.initial_focus_mag_still,
            args.initial_focus_mag_movie,
            args.af_in_focus_mag,
            args.hdmi_raw_output,
            args.focus_magnifier_active,
            args.peaking_display,
            args.peaking_level,
            args.peaking_color,
            args.af_illuminator,
            args.shoot_mode,
            args.focus_mode,
            args.creators_app_location_linkage,
            args.airplane_mode,
            args.bluetooth_function,
            args.video_light_mode,
            args.mi_shoe_5v_current_ma,
            args.hdmi_resolution,
            args.rec_media_dur_hdmi_output,
            args.power_save_start_time,
            args.auto_power_off_temp,
            args.power_source,
            args.air_gapped_battery_bench,
            args.power_save_deactivation_conditions,
            args.headless_monitor_power_linkage_mode,
            args.selected_lang,
            args.volume_settings,
            args.xlr_h1_attached,
            args.four_ch_audio_monitoring,
            args.delete_confirm,
            args.delete_pressing_twice,
            args.slot1_delete_requested,
            args.slot1_format_requested,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "preflight-usb-mode-hdmi-info-protect-and-network-reset":
        return _cmd_preflight_usb_mode_hdmi_info_protect_and_network_reset(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.markdown_out,
            args.output,
            args.reset_action,
            args.usb_connection_mode,
            args.expect_usb_streaming_uvc,
            args.usb_streaming_exposed_in_fx3_ui,
            args.dormant_uvc_kmod_insmodded,
            args.air_gapped_bench,
            args.usb_data_lines_physically_isolated,
            args.host_usb_data_enumeration_active,
            args.usb_lun_setting,
            args.usb_power_supply,
            args.power_source,
            args.usb_power_terminal,
            args.np_fz100_battery_inserted,
            args.hdmi_info_display,
            args.require_clean_hdmi_feed,
            args.require_unblanked_lcd,
            args.allow_lcd_blanking_and_osd,
            args.expect_touch_focus_active_when_hdmi_info_on,
            args.expect_full_raster_clean_feed_when_hdmi_info_on,
            args.rec_media_dur_hdmi_output,
            args.hdmi_raw_output,
            args.shoot_mode,
            args.log_shooting_mode,
            args.picture_profile,
            args.hdmi_output_resolution,
            args.expect_4k_hdmi_during_internal_log_or_pplut,
            args.expect_hdmi_info_on_during_raw_or_hdmi_only,
            args.expect_sq_allows_hdmi_only_or_raw,
            args.protect_scope_selected,
            args.protected_items_block_delete,
            args.expect_copy_preserves_protect,
            args.expect_movie_key_mark_without_menu,
            args.slot1_contains_tier0_dump,
            args.slot1_wp_locked,
            args.slot1_format_hard_locked,
            args.slot1_vault_write_firewall_enforced,
            args.slot1_format_mode,
            args.slot1_delete_requested,
            args.expect_protect_blocks_format,
            args.expect_format_preserves_m1_m4_camset,
            args.reset_network_set_executed,
            args.auto_reboot_triggered_on_network_reset,
            args.post_reboot_airplane_mode,
            args.require_post_reboot_airplane_on,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "preflight-pp-scinetone-wb-metering-and-shutter-type":
        return _cmd_preflight_pp_scinetone_wb_metering_and_shutter_type(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.markdown_out,
            args.output,
            args.reset_action,
            args.different_set_pp_checked,
            args.shoot_mode,
            args.log_shooting_mode,
            args.picture_profile,
            args.movie_picture_profile,
            args.still_picture_profile,
            args.creative_look,
            args.dro_mode,
            args.hlg_still_image,
            args.movie_gamma_display_assist,
            args.internal_recording_active,
            args.hdmi_output_resolution,
            args.expect_creative_look_or_dro_active_with_pp_or_log,
            args.expect_pplut_in_still,
            args.pp1_11_custom_params_modified,
            args.pp_individual_reset_executed,
            args.claimed_pp1_11_internal_params_wiped,
            args.claimed_diff_set_checkmarks_wiped,
            args.claimed_pp_active_selector_remains_non_pp11_after_camera_reset,
            args.wb_mode,
            args.wb_kelvin_k,
            args.wb_ab_shift,
            args.wb_gm_shift,
            args.priority_set_in_awb,
            args.shutter_awb_lock,
            args.shockless_wb,
            args.custom_wb_setup_requested,
            args.custom_wb_survives_camera_reset,
            args.custom_wb_excluded_from_camset,
            args.shutter_awb_lock_survives_camera_reset,
            args.claimed_custom_wb_saved_in_camset,
            args.claimed_custom_wb_wiped_by_camera_reset,
            args.metering_mode,
            args.desqueeze_display,
            args.face_priority_in_multi_metering,
            args.spot_metering_point,
            args.ael_with_shutter,
            args.ael_with_shutter_survives_camera_reset,
            args.cine_ei_base_iso,
            args.expect_metering_changes_cine_ei_iso,
            args.raw_file_type,
            args.lossless_comp_exposed_in_fx3_ui,
            args.expect_lossless_comp_raw,
            args.jh_file_type,
            args.still_file_format,
            args.exposure_mode,
            args.dro_bracket_active,
            args.color_space,
            args.still_file_prefix,
            args.expected_dcf_sample_filename,
            args.shutter_type,
            args.shutter_type_auto_exposed_in_fx3_ui,
            args.expect_shutter_type_auto,
            args.silent_mode,
            args.audio_signals,
            args.e_front_curtain_shutter,
            args.e_front_curtain_survives_camera_reset,
            args.flash_sync_denominator,
            args.flash_enabled,
            args.long_exposure_nr,
            args.bulb_enabled,
            args.anti_flicker_shoot,
            args.high_iso_nr,
            args.expect_high_iso_nr_applies_to_raw,
            args.drive_mode,
            args.cont_fps,
            args.aperture_f_number,
            args.expect_af_tracks_all_frames_above_f11,
            args.expect_10fps_with_uncompressed_or_flash,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "preflight-focus-area-zoom-dci4k-and-sensor-cleaning":
        return _cmd_preflight_focus_area_zoom_dci4k_and_sensor_cleaning(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.summary,
            args.markdown_out,
            args.output,
            args.reset_action,
            args.shoot_mode,
            args.focus_area,
            args.expect_tracking_focus_area_in_movie,
            args.focus_area_limit_selected_count,
            args.switch_vh_af_area,
            args.expect_switch_vh_in_movie,
            args.focus_area_color,
            args.circ_of_focus_point,
            args.af_area_registration_label,
            args.xlr_h1_zoom_lever_present,
            args.xlr_h1_rec_button_present,
            args.xlr_h1_zoom_hold_switch_present,
            args.fx6_smart_handle_zero_to_99_is_speed_scale,
            args.zoom_range,
            args.zoom_lever_stby_speed,
            args.zoom_lever_rec_speed,
            args.custom_key_zoom_stby_speed,
            args.custom_key_zoom_rec_speed,
            args.remote_zoom_speed_type,
            args.remote_zoom_fixed_stby_speed,
            args.remote_zoom_fixed_rec_speed,
            args.iso_range_limit_min,
            args.iso_range_limit_max,
            args.iso_auto_min,
            args.iso_auto_max,
            args.exposure_mode,
            args.iso_mode,
            args.iso_auto_min_ss,
            args.iso_auto_min_ss_active,
            args.expect_iso_auto_min_ss_in_movie_or_manual_iso,
            args.log_shooting_mode,
            args.cine_ei_base_iso,
            args.expect_iso_variable_in_cine_ei,
            args.shutter_type,
            args.silent_mode,
            args.flash_mode,
            args.flash_firing_enabled,
            args.flash_comp_ev,
            args.exp_comp_set,
            args.video_light_mode,
            args.mi_shoe_5v_current_ma,
            args.movie_file_format,
            args.movie_resolution_wh,
            args.rec_frame_rate,
            args.stage_b_volatile_tmp_overlay_active,
            args.ack_24p_reboot_wipes_tmp_overlay,
            args.expect_24p_no_reboot,
            args.hdmi_raw_output,
            args.sq_dci4k_fps,
            args.bitrate_mbps,
            args.media_speed_grade,
            args.still_aspect_ratio,
            args.apsc_s35_on,
            args.still_jpeg_heif_size,
            args.hlg_still_image,
            args.camset_card_path,
            args.memory_recall_media_slot,
            args.fx3_uses_private_sony_pro_camera,
            args.photo_capture_requested,
            args.photo_capture_slot,
            args.slot1_contains_tier0_dump,
            args.enlarge_initial_mag,
            args.enlarge_initial_position,
            args.sensor_cleaning_requested,
            args.battery_soc_pct,
            args.mandatory_power_off_after_cleaning,
            args.unattended_tier0_dump_active,
            args.fx6_sensor_cleaning_supported_claimed,
            args.fx3_has_built_in_end_filter,
            args.exposure_comp_ev,
            args.exposure_step,
            args.legacy_reset_ev_comp_claimed,
            args.focus_mode,
            args.priority_set_in_af,
            args.af_illuminator,
            args.view_mode,
            args.image_index_mode,
            args.display_as_group,
            args.display_rotation,
            args.playback_media_slot,
            args.playback_rotate_requested,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence":
        return _cmd_preflight_lens_comp_af_illuminator_copy_slot_and_evf_absence(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.summary,
            args.markdown_out,
            args.output,
            args.reset_action,
            args.shoot_mode,
            args.focus_mode,
            args.exposure_mode,
            args.shading_comp,
            args.dormant_shading_auto_low_requested,
            args.chromatic_aberration_comp,
            args.distortion_comp,
            args.steadyshot_mode,
            args.lens_distortion_comp_locked_auto,
            args.unchipped_manual_lens_attached,
            args.expect_lens_comp_active_on_manual_lens,
            args.breathing_comp,
            args.breathing_comp_compliant_lens,
            args.hdmi_raw_output,
            args.claimed_static_lens_comp_wiped_by_camera_reset,
            args.fx6_lens_comp_in_scene_file_claimed,
            args.fx3_builtin_af_illuminator_present,
            args.fx6_builtin_af_illuminator_present,
            args.af_illuminator,
            args.af_illuminator_firing_requested,
            args.af_illuminator_distance_m,
            args.focus_magnifier_active,
            args.mount_adaptor_attached,
            args.af_transition_speed,
            args.af_subj_shift_sensitivity,
            args.af_assist,
            args.af_assist_compatible_lens,
            args.aperture_drive_in_af,
            args.af_with_shutter,
            args.pre_af,
            args.lens_pre_af_supported,
            args.circ_of_focus_point,
            args.expect_diagonal_focus_wrap,
            args.focus_area_color,
            args.claimed_af_five_params_wiped_by_camera_reset,
            args.fx6_aperture_drive_in_af_claimed,
            args.still_folder_name_mode,
            args.select_rec_folder_enabled_claimed,
            args.still_file_number_mode,
            args.still_file_prefix,
            args.still_folder_image_count,
            args.slot1_contains_tier0_dump,
            args.slot1_wp_locked,
            args.create_new_folder_requested,
            args.create_new_folder_slot,
            args.forced_file_number_reset_requested,
            args.forced_file_number_reset_slot,
            args.playback_media_slot,
            args.playback_rating_requested,
            args.rating_stars,
            args.add_rating_requested,
            args.target_image_already_rated,
            args.digital_zoom_active,
            args.switch_vh_af_area,
            args.body_roll_orientation,
            args.fx6_switch_vh_af_area_claimed,
            args.focus_area_limit_selected_count,
            args.dormant_focus_area_requested,
            args.fx6_focus_area_limit_claimed,
            args.exposure_std_adjust_metering_mode,
            args.exposure_std_adjust_ev,
            args.expect_std_adjust_changes_exif_exposure_comp,
            args.claimed_exposure_std_adjust_wiped_by_camera_reset,
            args.fx6_exposure_std_adjust_claimed,
            args.bracket_selftimer,
            args.bracket_order,
            args.bracket_settings_active_in_movie_claimed,
            args.video_system,
            args.rec_frame_rate,
            args.tc_format,
            args.user_bit_time_rec,
            args.tcub_disp_setting,
            args.fx3_builtin_bnc_tc_in_out_switch_claimed,
            args.claimed_tcub_6items_wiped_by_camera_reset,
            args.playback_copy_requested,
            args.copy_battery_ok,
            args.copy_target_media_speed_ok,
            args.copy_dest_slot_present,
            args.expect_copy_preserves_group_or_protect,
            args.fx6_in_camera_copy_clip_claimed,
            args.slide_show_requested,
            args.slide_show_repeat,
            args.slide_show_interval_sec,
            args.slide_show_view_mode,
            args.touch_operation,
            args.touch_sensitivity,
            args.touch_func_in_shooting,
            args.swipe_up,
            args.dormant_touch_trap_requested,
            args.touch_panel_pad_present_claimed,
            args.footer_icon_touch_enabled_claimed,
            args.claimed_touch_4items_wiped_by_camera_reset,
            args.fx3_builtin_evf_present,
            args.fx3_eye_sensor_present,
            args.fx3_select_finder_monitor_present,
            args.fx3_graphic_display_present,
            args.activate_dormant_evf_finder_mode,
            args.finder_monitor_key_claimed,
            args.graphic_display_claimed,
            args.monitor_off_evf_trap_claimed,
            args.for_viewfinder_disp_claimed,
            args.fx6_detachable_evf_loupe_claimed,
            args.claimed_disp_modes_wiped_by_camera_reset,
            args.ael_with_shutter,
            args.ael_with_shutter_in_movie_claimed,
            args.claimed_ael_with_shutter_wiped_by_camera_reset,
            args.exp_comp_set,
            args.wireless_flash,
            args.external_flash_set_requested,
            args.mi_shoe_external_flash_attached,
            args.fx6_still_ael_or_wireless_flash_claimed,
            args.interval_play_speed,
            args.interval_play_speed_capped_at_5_claimed,
            args.in_camera_interval_to_video_render_claimed,
            args.dormant_beauty_effect_requested,
            args.dormant_trimming_requested,
            args.playback_photo_capture_requested,
            args.playback_rotate_requested,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "preflight-dial-customize-lut-embed-steadyshot-and-streaming":
        return _cmd_preflight_dial_customize_lut_embed_steadyshot_and_streaming(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.summary,
            args.markdown_out,
            args.output,
            args.sony_help_guide_id,
            args.reset_action,
            args.shoot_mode,
            args.exposed_dial_customize_items,
            args.dormant_dial_setup_or_wheel_lock_requested,
            args.av_tv_rotate,
            args.function_ring_lens,
            args.lock_operation_parts,
            args.claimed_dial_customize_wiped_by_camera_reset,
            args.fx6_dial_topology_claimed,
            args.exposed_physical_dials,
            args.fx3_four_dial_rear_lr_present,
            args.dormant_rear_dial_lr_requested,
            args.my_dial_slot,
            args.my_dial_active_recalled,
            args.expect_lock_blocks_recalled_my_dial,
            args.fn_menu_still_slots,
            args.fn_menu_movie_slots,
            args.fn_menu_all_not_set_claimed,
            args.exposed_live_view_subitems,
            args.live_view_display,
            args.exposure_effect,
            args.frame_rate_low_limit,
            args.bright_monitoring_active,
            args.expect_setting_effect_on_during_bright_monitoring,
            args.claimed_live_view_two_items_wiped_by_camera_reset,
            args.grid_line_display,
            args.grid_line_type,
            args.hdmi_info_display,
            args.hdmi_raw_output,
            args.rec_media_dur_hdmi_output,
            args.expect_grid_line_on_clean_hdmi,
            args.dormant_fx6_custom_png_grid_requested,
            args.user_lut_slot,
            args.user_lut_import_requested,
            args.user_lut_source_media_type,
            args.user_lut_source_dir,
            args.user_lut_filename,
            args.user_lut_cube_size,
            args.user_lut_config_writeback_to_slot1,
            args.log_shooting_mode,
            args.embed_lut_file,
            args.embed_lut_media_type,
            args.claimed_embed_lut_under_color_tone,
            args.expect_embed_lut_bakes_pixels,
            args.picture_profile,
            args.expect_pplut_preserves_unbaked_slog3,
            args.claimed_pplut_survives_reset,
            args.slot1_contains_tier0_dump,
            args.slot1_wp_locked,
            args.embed_lut_or_pplut_rec_requested,
            args.rec_target_slot,
            args.steadyshot_mode,
            args.dormant_dynamic_active_requested,
            args.steadyshot_adjust,
            args.steadyshot_focal_mm,
            args.exposed_focal_length_table,
            args.rec_fps,
            args.sq_mode_enabled,
            args.sq_fps,
            args.desqueeze_display,
            args.distortion_comp,
            args.fx3_builtin_5axis_ibis_present,
            args.fx6_builtin_ibis_claimed,
            args.dormant_movie_selftimer_requested,
            args.still_drive_mode,
            args.front_led8_selftimer_blink_expected,
            args.silent_mode,
            args.audio_signals,
            args.dormant_audio_signal_volume_requested,
            args.claimed_audio_signals_wiped_by_camera_reset,
            args.fx6_picture_cache_or_interval_rec_in_fx3_claimed,
            args.zebra_display,
            args.zebra_preset,
            args.zebra_custom_slot,
            args.zebra_custom_type,
            args.zebra_level_ire,
            args.zebra_range_plus_minus,
            args.peaking_display,
            args.peaking_level,
            args.peaking_color,
            args.expect_zebra_or_peaking_on_clean_hdmi,
            args.fx6_zebra_both_mode_claimed,
            args.claimed_zebra_peaking_wiped_by_camera_reset,
            args.streaming_protocol,
            args.streaming_resolution,
            args.streaming_fps,
            args.movie_rec_during_streaming,
            args.internal_rec_resolution_class,
            args.internal_rec_fps,
            args.movie_rec_during_streaming_slot,
            args.fx6_builtin_rtmp_srt_claimed,
            args.ftp_transfer_func,
            args.ftp_active_mode_requested,
            args.ftp_slot1_write_requested,
            args.claimed_network_wiped_by_camera_reset,
            args.claimed_network_survives_reset_network_set,
            args.airplane_mode,
            args.network_transport,
            args.wireless_streaming_requested,
            args.wireless_ftp_requested,
            args.wireless_rf_packets_emitted,
            args.rf_nvs_p12_p13_writes_requested,
            args.simulated_passive_tx_bytes,
            args.simulated_h0_h3_drifted_surfaces,
            args.claim_hardware_live_attach_authorized,
            args.claim_persistent_emmc_writes_authorized,
            args.claim_cross_model_flash_authorized,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth":
        return _cmd_preflight_bright_monitoring_shot_mark_big6_home_and_ssh_auth(
            args.fx6_lib_dir,
            args.fx3_modules_dir,
            args.force_clean_room,
            args.simulate_bench_dry_run,
            args.json,
            args.summary,
            args.markdown_out,
            args.output,
            args.sony_help_guide_id,
            args.reset_action,
            args.shoot_mode,
            args.exposure_mode,
            args.focus_mode,
            args.bright_monitoring_active,
            args.bright_monitoring_in_shoot_menu_claimed,
            args.live_view_display,
            args.expect_setting_effect_on_during_bright_monitoring,
            args.expect_bright_monitoring_blocks_focus_magnifier,
            args.claimed_bright_monitoring_persists_after_power_cycle,
            args.monitor_brightness_mode,
            args.monitor_brightness_level,
            args.dormant_lcd_brightness_mode_requested,
            args.claimed_monitor_brightness_wiped_by_camera_reset,
            args.fx6_backlight_is_lcd_brightness_claimed,
            args.fx6_vf_brightness_1_15_in_fx3_claimed,
            args.dormant_divide_or_extract_requested,
            args.dormant_ftp_cut_15_30_60s_requested,
            args.shot_mark_write_requested,
            args.shot_mark_slot,
            args.clip_flag,
            args.clip_flag_write_requested,
            args.clip_flag_slot,
            args.photo_capture_requested,
            args.photo_capture_slot,
            args.create_divider_frame_requested,
            args.divider_frame_slot,
            args.edit_write_requested,
            args.edit_write_slot,
            args.slot1_contains_tier0_dump,
            args.slot1_wp_locked,
            args.bulb_enabled,
            args.shutter_type,
            args.still_drive_mode,
            args.anti_flicker_shoot,
            args.expect_bulb_in_electronic_or_cont_or_interval,
            args.dro_mode,
            args.dro_bracket_mode,
            args.picture_profile,
            args.log_shooting_mode,
            args.hlg_still_image,
            args.expect_dro_active_with_pp_or_hlg,
            args.dormant_bulb_timer_requested,
            args.dormant_auto_hdr_requested,
            args.dormant_bt_tc_link_requested,
            args.fx3_bt_tc_link_present_claimed,
            args.fx6_bt_tc_link_claimed,
            args.fx3_builtin_bnc_tc_in_out_switch_claimed,
            args.vmc_bncm1_ext_lk_active,
            args.tc_make,
            args.tc_run,
            args.wifi_sku,
            args.wifi_band_5ghz_requested,
            args.outdoor_5ghz_w52_requested,
            args.wifi_security_protocol,
            args.dormant_legacy_wifi_sec_requested,
            args.wifi_enabled,
            args.usb_lan_cnct_launch,
            args.network_transport,
            args.multi_micro_usb_device_attached,
            args.exposed_usb_lan_kmods,
            args.airplane_mode,
            args.bluetooth_enabled,
            args.wireless_rf_packets_emitted,
            args.rf_nvs_p12_p13_writes_requested,
            args.claimed_airplane_wiped_by_reset,
            args.mode_settings,
            args.big6_home_screen_active,
            args.home_trigger_method,
            args.exposed_big6_tiles,
            args.home_lower_left_mode,
            args.fx3_physical_e_nd_claimed,
            args.e_nd_actuator_tx_count,
            args.expect_big6_displays_pp_during_log,
            args.expect_big6_displays_variable_iso_in_cine_ei,
            args.claimed_menu_fn_do_not_exit_home,
            args.framing_enabled,
            args.framing_rec_stream_area,
            args.framing_hdmi_area,
            args.apsc_s35_on,
            args.rec_fps,
            args.sq_fps,
            args.active_rec_or_stream_during_framing_toggle,
            args.dormant_auto_framing_requested,
            args.fx3_auto_framing_present_claimed,
            args.interval_shooting_active,
            args.exposed_interval_params,
            args.interval_start_sec,
            args.interval_sec,
            args.interval_num_shots,
            args.interval_ae_tracking,
            args.interval_shutter_type,
            args.interval_shoot_priority,
            args.interval_target_slot,
            args.claimed_interval_7params_survive_camera_reset,
            args.fx3_interval_outputs_single_mxf_claimed,
            args.simult_recording,
            args.tc_regen_source_slot,
            args.claimed_tc_make_run_wiped_by_camera_reset,
            args.fx3_has_clock_tc_mode_claimed,
            args.hdmi_tc_output,
            args.hdmi_rec_control,
            args.rec_media_dur_hdmi_output,
            args.streaming_active,
            args.hdmi_4ch_audio_output,
            args.access_authen,
            args.access_authen_protocol,
            args.dormant_http_https_camera_auth_claimed,
            args.claimed_access_authen_wiped_by_camera_reset,
            args.expect_root_cert_authenticates_inbound_http_server,
            args.fx3_fan_control,
            args.fx6_fan_control,
            args.dormant_fan_control_max_requested,
            args.auto_power_off_temp,
            args.handheld_bare_skin_unacknowledged,
            args.claimed_fan_or_autotemp_wiped_by_camera_reset,
            args.simulated_passive_tx_bytes,
            args.simulated_h0_h3_drifted_surfaces,
            args.claim_hardware_live_attach_authorized,
            args.claim_persistent_emmc_writes_authorized,
            args.claim_cross_model_flash_authorized,
            args.receipt_a,
            args.receipt_b,
            args.model_id,
            args.body_fw,
            args.body_serial,
            args.emmc_cid,
        )
    if args.cmd == "preflight-rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes":
        return _cmd_preflight_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes(args)
    if args.cmd == "preflight-shoe-audio-4ch-subject-recog-hdmi-raw-desqueeze-and-varshutter":
        return _cmd_preflight_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter(args)
    if args.cmd == "preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun":
        return _cmd_preflight_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun(args)
    if args.cmd == "preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc":
        return _cmd_preflight_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc(args)
    if args.cmd == "preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec":
        return _cmd_preflight_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec(args)
    if args.cmd == "preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether":
        return _cmd_preflight_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
