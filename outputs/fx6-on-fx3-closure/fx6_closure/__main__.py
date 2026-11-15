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


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fx6_closure",
        description="FX6-on-FX3 Phase 130, Phase 110 & Phase 90 Milestone Master Gates, U1-U5 Blueprint Closure, p1 Recovery Bridge, Atomic Stage-A/B Boot Orchestrator, Stage-A Kmod/Dev/ELF64 ABI Closure, Peripheral UX/Audio Closure, AP<->Stock-CP Imaging/IBIS Closure, Unified Stage-B Candidate Integrator, Post-Trial Forensic Auditor, Stage-B R0..R6 Rehearsal, Unified Stage-B Release Dossier v3 & Capstone 22-Gate Verifier CLI",
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
    ):
        p = sub.add_parser(cmd_name, help=help_msg)
        if cmd_name != "verify-post-trial":
            p.add_argument("--fx6-lib-dir", type=Path, default=DEFAULT_FX6_DONOR_LIB_DIR)
            p.add_argument("--fx3-modules-dir", type=Path, default=DEFAULT_FX3_MODULES_DIR)
        if cmd_name == "verify-feature-routing":
            p.add_argument("--fx6-initrd-lib-dir", type=Path, default=DEFAULT_FX6_INITRD_LIB_DIR)
            p.add_argument("--fx6-bin-dir", type=Path, default=DEFAULT_FX6_DONOR_BIN_DIR)
        if cmd_name in ("dry-run-candidate", "run-rollback-drill"):
            p.add_argument("--vfat-mode", default="8m_ram", choices=["8m_ram", "16m_log", "44.5m_log", "44.5m_fat32"])
        if cmd_name in ("dry-run-candidate", "verify-p1-recovery-bridge", "build-readiness-packet", "build-stage-b-readiness-packet", "run-stage-b-lifecycle-drill", "verify-stage-b-candidate", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130"):
            p.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
        if cmd_name in ("verify-peripheral-ux", "verify-ap-cp-imaging", "verify-stage-b-p10", "verify-uipc-cp-shim", "verify-wireless-guard", "verify-stage-b-ram-overlay", "verify-stage-b-candidate", "audit-stage-b-post-trial", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130"):
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write audit report")
            p.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic offline verification mode")
        if cmd_name in ("verify-stage-b-ram-overlay", "verify-stage-b-candidate", "rehearse-stage-b-closed-loop"):
            p.add_argument("--lang", default="en", choices=["en", "schinese", "tchinese", "japanese"], help="Select Stage-B BK_LANG (0x02cf019c) shadow language")
        if cmd_name in ("verify-stage-b-ram-overlay", "verify-stage-b-candidate", "audit-stage-b-post-trial", "rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130"):
            p.add_argument("--json", action="store_true", help="Emit full deterministic JSON report to stdout")
        if cmd_name in ("rehearse-stage-b-closed-loop", "build-stage-b-dossier-v3", "verify-stage-b-capstone", "verify-milestone-90", "verify-milestone-110", "verify-milestone-130"):
            p.add_argument("--markdown-out", type=Path, default=None, help="Optional Markdown report path to write certificate/dossier")
        if cmd_name == "audit-stage-b-post-trial":
            p.add_argument("--h0-bundle-dir", type=Path, default=None, help="Optional archived Phase H0 pre-trial Tier-0 capture directory")
            p.add_argument("--h2-bundle-dir", type=Path, default=None, help="Optional Phase H2 post-power-cycle Tier-0 readback directory")
        if cmd_name in ("build-readiness-packet", "build-stage-b-readiness-packet"):
            p.add_argument("--tier0-bundle-dir", type=Path, default=None, help="Optional path to physical FX3 Tier-0 capture directory")
            p.add_argument("--output", type=Path, default=None, help="Optional JSON file path to write deterministic readiness packet")
            p.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic offline verification mode")
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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
