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


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fx6_closure",
        description="FX6-on-FX3 Phase 264/254/233/221/209/193/175/147 Real-Hardware Master Gates, Phase 261/248/227/216/204/186/154 Bench & Pre-Shoot Readiness Verifiers, Phase 130/110/90 Milestone Master Gates, U1-U6 Blueprint Closure, p1 Recovery Bridge, Atomic Stage-A/B Boot Orchestrator, Stage-A Kmod/Dev/ELF64 ABI Closure, Peripheral UX/Audio Closure, AP<->Stock-CP Imaging/IBIS Closure, Unified Stage-B Candidate Integrator, Post-Trial Forensic Auditor, Stage-B R0..R6 Rehearsal, Unified Stage-B Release Dossier v3 & Capstone 22-Gate Verifier CLI",
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
        ("verify-milestone-130", "Verify Phase 130 6-Pillar Master Gate (40-Gate + >=13 Recovery + >=24 Auditors + >=21 VM + R14/17/19/R20..24 UI Closures, stage_b_milestone130_master_gate_v1)"),
        ("verify-realhw-jiritsu-tier0", "Verify Phase 136 Stage-288 libJiritsu.so SET_FILE2 P0 hardening, U4/U5/U6 disassembly closures & Tier-0 cold-backup stop-gate"),
        ("verify-sd-stageb-bundle-uninstaller", "Verify Phase 143 BYOF SD-Card Stage-B bundle builder, im.elf escape-hatch launcher & H0==H3 16-surface atomic uninstaller"),
        ("verify-milestone-147", "Verify Milestone Phase 147 6-Pillar Real-Hardware Bench Readiness Master Gate (44-Gate + >=17 Recovery + >=28 Auditors + >=24 VM + Ph136/143 U4/U5/U6/H0==H3 + FX3 7.02 QEMU R28/R29, realhw_milestone147_master_gate_v1)"),
        ("preflight-realhw-bench", "Run Phase 154 100% passive zero-USB-packet physical bench preflight, ioreg USB mode classifier, SD staging verifier & dual-copy FX3RCPT1 Go/No-Go receipt generator"),
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
        if cmd_name in ("dry-run-candidate", "verify-p1-recovery-bridge", "build-readiness-packet", "build-stage-b-readiness-packet", "run-stage-b-lifecycle-drill", "verify-stage-b-candidate", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-milestone-147", "verify-milestone-175", "verify-milestone-193", "verify-milestone-209", "verify-milestone-221", "verify-milestone-233", "verify-milestone-254", "verify-milestone-264"):
            p.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
        if cmd_name in ("verify-peripheral-ux", "verify-ap-cp-imaging", "verify-stage-b-p10", "verify-uipc-cp-shim", "verify-wireless-guard", "verify-stage-b-ram-overlay", "verify-stage-b-candidate", "audit-stage-b-post-trial", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-realhw-jiritsu-tier0", "verify-sd-stageb-bundle-uninstaller", "verify-milestone-147", "preflight-realhw-bench", "verify-milestone-175"):
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write audit report")
            p.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic offline verification mode")
        if cmd_name in ("verify-milestone-193", "verify-milestone-209", "verify-milestone-221", "verify-milestone-233"):
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write Milestone master report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force clean-room synthetic offline verification mode")
        if cmd_name in ("verify-milestone-254", "verify-milestone-264"):
            p.add_argument("--output", "--out", dest="output", type=Path, default=None, help="Optional JSON file path to write Milestone master report")
            p.add_argument("--force-clean-room", "--clean-room", dest="force_clean_room", action="store_true", help="Force clean-room synthetic offline verification mode")
        if cmd_name in ("verify-stage-b-ram-overlay", "verify-stage-b-candidate", "rehearse-stage-b-closed-loop", "verify-sd-stageb-bundle-uninstaller"):
            p.add_argument("--lang", default="en", choices=["en", "schinese", "tchinese", "japanese"], help="Select Stage-B BK_LANG (0x02cf019c) shadow language")
        if cmd_name in ("verify-stage-b-ram-overlay", "verify-stage-b-candidate", "audit-stage-b-post-trial", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-realhw-jiritsu-tier0", "verify-sd-stageb-bundle-uninstaller", "verify-milestone-147", "preflight-realhw-bench", "verify-milestone-175", "preflight-card-insert", "verify-milestone-193", "preflight-bench-cable-fan-slot1", "verify-milestone-209", "preflight-hdmi-proxy-desqueeze-and-simult", "verify-milestone-221", "preflight-pixelmap-ntscpal-powersave-and-autotemp", "verify-milestone-233", "preflight-imagedb-touch-shoeaudio-and-lockop", "verify-milestone-254", "preflight-diffset-customkey-autoslow-and-apsc", "verify-milestone-264"):
            p.add_argument("--json", action="store_true", help="Emit full deterministic JSON report to stdout")
        if cmd_name in ("rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130", "verify-milestone-147", "preflight-realhw-bench", "verify-milestone-175", "preflight-card-insert", "verify-milestone-193", "preflight-bench-cable-fan-slot1", "verify-milestone-209", "preflight-hdmi-proxy-desqueeze-and-simult", "verify-milestone-221", "preflight-pixelmap-ntscpal-powersave-and-autotemp", "verify-milestone-233", "preflight-imagedb-touch-shoeaudio-and-lockop", "verify-milestone-254", "preflight-diffset-customkey-autoslow-and-apsc", "verify-milestone-264"):
            p.add_argument("--markdown-out", type=Path, default=None, help="Optional Markdown report path to write certificate/dossier")
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
            p.add_argument("--battery-soc", dest="battery_soc_pct", type=float, default=88.0, help="NP-FZ100 battery SOC percentage (>=20.0% required for [Recover Image DB])")
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
            p.add_argument("--battery-soc", dest="battery_soc_pct", type=float, default=88.0, help="NP-FZ100 battery SOC percentage (>=20.0% required for [Pixel Mapping])")
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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
