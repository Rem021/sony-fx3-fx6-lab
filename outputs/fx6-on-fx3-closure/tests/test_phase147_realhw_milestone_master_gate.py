"""Phase 147 dual-mode unit tests for Milestone Phase 147 6-Pillar Real-Hardware Bench Readiness Master Gate."""

from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[3]
for _rel in (
    "outputs/fx3-safety",
    "outputs/fx3-recovery-adapter",
    "outputs/fx3-firmware-lab",
    "outputs/fx3-vm",
    "outputs/fx6-on-fx3-closure",
):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as fx6_cli_main  # noqa: E402
from fx6_closure.hardware_readiness_packet import _is_forced_clean_room  # noqa: E402
from fx6_closure.patcher import DEFAULT_FX3_MODULES_DIR, DEFAULT_FX6_DONOR_LIB_DIR  # noqa: E402
from fx6_closure.realhw_milestone147_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    DEFAULT_REPO_ROOT,
    FIRMWARE_LAB_28_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
    MILESTONE147_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_147_VERSION,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    REALHW_MILESTONE147_SCHEMA,
    RECOVERY_17_PILLAR_IDS,
    ROUND28_EXPECTED_SCHEMA,
    ROUND28_RUN_SPECS,
    ROUND28_SUMMARY_RELPATH,
    ROUND29_EXPECTED_SCHEMA,
    ROUND29_RUN_SPECS,
    ROUND29_SUMMARY_RELPATH,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    VM_COEMULATION_24_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    Milestone147PillarResult,
    RealHwMilestone147FaultInjection,
    RealHwMilestone147MasterGateReport,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _load_round28_or_29_summary,
    _worker_phase136,
    _worker_phase143,
    _worker_pillar_1,
    _worker_pillar_4,
    _worker_recovery_master,
    _worker_recovery_p8_p9_p10,
    _worker_recovery_p14_to_p16,
    _worker_recovery_p17,
    build_realhw_milestone147_master_gate_report,
    compute_milestone147_sha256,
    render_milestone147_markdown,
    verify_realhw_milestone147_master_gate,
)
from fx6_closure.stage_b_capstone_22gate_verifier import _worker_domain_2  # noqa: E402
from fx6_closure.stage_b_milestone110_master_gate import FIRMWARE_LAB_20_AUDITOR_KEYS  # noqa: E402
from fx6_closure.stage_b_milestone130_master_gate import (  # noqa: E402
    FIRMWARE_LAB_24_AUDITOR_KEYS,
    RECOVERY_13_PILLAR_IDS,
    VM_COEMULATION_21_STAGE_KEYS,
    _worker_recovery_p11_to_p13,
)
from fx6_closure.stage_b_release_dossier_v3 import _worker_pillar_b  # noqa: E402

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


def _make_clean_p1_raw(*, total_gates: int = 44, offline_verified: int = 41, sim_verified: int = 44) -> dict:
    return {
        "schema": "fx3-safety-44gate-preflight-v1",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "total_gates": total_gates,
        "offline_verified_gates": offline_verified,
        "offline_41_gates_verified": True,
        "offline_all_44_gates_verified": False,
        "offline_ready_for_hw": False,
        "sim_verified_gates": sim_verified,
        "sim_all_44_gates_verified": True,
        "sim_dry_run_rehearsal_only": True,
        "sim_ready_for_hw": False,
        "g13_to_g44_all_passed": True,
        "g43_to_g44_all_passed": True,
        "m42_g13_to_g42_all_passed": True,
        "m42_g41_to_g42_all_passed": True,
        "g41_passed": True,
        "g41_status": "SAFE_VP_LEDWALL_STROBE_GENLOCK",
        "g41_guard": {
            "valid": True,
            "arc_strobe_irradiance_safe": True,
            "multiterminal_genlock_safe": True,
            "ledwall_ecs_sync_safe": True,
        },
        "g42_passed": True,
        "g42_status": "SAFE_VEHICLERIG_IBIS_RESONANCE",
        "g42_guard": {
            "valid": True,
            "hardmount_wire_isolator_safe": True,
            "ibis_resonance_park_safe": True,
            "exterior_steel_tether_safe": True,
        },
        "g43_passed": True,
        "g43_status": "SAFE_JIRITSU_0X40_STAGE288_P0",
        "g43_guard": {
            "valid": True,
            "electrical_power_safe": True,
            "jbusy_precheck_safe": True,
            "wire_framing_and_opcodes_safe": True,
            "elf_alignment_and_selfdelete_safe": True,
            "p6_quota_and_cleanup_safe": True,
            "constructor_unlinkat_self_delete_enabled": True,
            "elf_pt_load_align_bytes": 65536,
            "p6_residual_files": 0,
        },
        "g44_passed": True,
        "g44_status": "SAFE_CNFLASHA15_DUALBOOT_ESCAPE",
        "g44_guard": {
            "valid": True,
            "tier0_cold_backup_safe": True,
            "spacc_boundary_and_flasher_safe": True,
            "sd_escape_hatch_safe": True,
            "p1_p3_mutex_and_uart_safe": True,
            "target_is_type5_flag1_encrypted": True,
            "target_block_device": "/dev/cnflasha15",
            "modify_p1_in_transaction": False,
            "modify_p3_in_transaction": False,
            "sd_escape_bypass_latency_us": 47.0,
        },
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "sim_errors": [],
        "g41_to_g44_errors": [],
    }


def _make_clean_p2_master_raw() -> dict:
    return {
        "schema": "fx3-recovery-master-suite-v1",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "all_passed": True,
        "status": "RECOVERY_MASTER_7PILLAR_VERIFIED_SAFE",
        "pillar_count": 7,
        "pillars_passed": 7,
        "pillar_statuses": {k: True for k in RECOVERY_13_PILLAR_IDS[:7]},
        "uart_scenarios_total": 10,
        "uart_scenarios_passed": 10,
        "uart_all_passed": True,
        "passive_tx_bytes_emitted": 0,
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "allow_boot_partition_targeting": False,
        "allow_destructive_fastboot": False,
        "recovery_master_sha256": "1" * 64,
        "errors": [],
    }


def _make_clean_p2_p8_p10_raw() -> dict:
    return {
        "p8_gpt_rpmb": {
            "schema": "fx3-gpt-rpmb-and-rescue-bundle-v1",
            "all_passed": True,
            "status": "VERIFIED_GPT_RPMB_RESCUE_SAFE",
            "gpt_heal_backup_ok": True,
            "gpt_heal_primary_ok": True,
            "rpmb_authenticated_write_passed": True,
            "sd_rescue_ok": True,
            "stage_b_zero_rpmb_ok": True,
            "otp_fuse_touches": 0,
            "rpmb_writes_emitted": 0,
            "passive_tx_bytes_emitted": 0,
            "physical_device_writes": 0,
            "persistent_emmc_writes_authorized": False,
            "suite_sha256": "2" * 64,
            "errors": [],
        },
        "p9_ramdisk_emmc_health": {
            "schema": "fx3-ramdisk-overlay-and-emmc-health-v1",
            "all_passed": True,
            "status": "VERIFIED_RAMDISK_OVERLAY_EMMC_HEALTH_SAFE",
            "stage_b_containment_ready": True,
            "cpio_reject_traversal_passed": True,
            "cpio_reject_setuid_passed": True,
            "emmc_reject_pre_eol_urgent_passed": True,
            "emmc_reject_lifetime_gt80_passed": True,
            "mount_reject_rw_mmcblk_passed": True,
            "otp_fuse_touches": 0,
            "passive_tx_bytes_emitted": 0,
            "physical_device_writes": 0,
            "persistent_emmc_writes_authorized": False,
            "suite_sha256": "3" * 64,
            "errors": [],
        },
        "p10_fdt_bootargs_kernel": {
            "schema": "fx3-fdt-bootargs-and-kernel-v1",
            "all_passed": True,
            "status": "VERIFIED_FDT_BOOTARGS_AND_KERNEL_SAFE",
            "stage_b_boot_gate_ready": True,
            "bootargs_reject_rw_emmc_passed": True,
            "bootargs_reject_nowatchdog_passed": True,
            "kernel_reject_fx6_transplant_passed": True,
            "otp_fuse_touches": 0,
            "passive_tx_bytes_emitted": 0,
            "physical_device_writes": 0,
            "persistent_emmc_writes_authorized": False,
            "suite_sha256": "4" * 64,
            "errors": [],
        },
    }


def _make_clean_p2_p11_p13_raw() -> dict:
    return {
        "p11_ab_ota": {
            "schema": "fx3-ab-bank-and-interrupted-ota-v1",
            "all_passed": True,
            "status": "VERIFIED_AB_BANK_AND_OTA_SAFE",
            "otp_fuse_touches": 0,
            "passive_tx_bytes_emitted": 0,
            "physical_device_writes": 0,
            "persistent_emmc_writes_authorized": False,
            "allow_boot_partition_targeting": False,
            "allow_destructive_fastboot": False,
            "suite_sha256": "5" * 64,
            "errors": [],
        },
        "p12_squashfs_hibdrv_wbi": {
            "schema": "fx3-squashfs-and-hibdrv-wbi-v1",
            "all_passed": True,
            "status": "VERIFIED_SQUASHFS_AND_HIBDRV_WBI_SAFE",
            "otp_fuse_touches": 0,
            "passive_tx_bytes_emitted": 0,
            "physical_device_writes": 0,
            "wbi_partition_writes": 0,
            "persistent_emmc_writes_authorized": False,
            "allow_boot_partition_targeting": False,
            "allow_destructive_fastboot": False,
            "suite_sha256": "6" * 64,
            "errors": [],
        },
        "p13_bootrom_bootpart": {
            "schema": "fx3-bootrom-usb-and-emmc-bootpart-v1",
            "all_passed": True,
            "status": "VERIFIED_BOOTROM_USB_AND_BOOTPART_SAFE",
            "otp_fuse_touches": 0,
            "passive_tx_bytes_emitted": 0,
            "physical_device_writes": 0,
            "emmc_persistent_program_commands": 0,
            "persistent_emmc_writes_authorized": False,
            "allow_boot_partition_targeting": False,
            "allow_destructive_fastboot": False,
            "suite_sha256": "7" * 64,
            "errors": [],
        },
    }


def _make_clean_p2_p14_p16_raw() -> dict:
    base = {
        "all_passed": True,
        "otp_fuse_touches": 0,
        "otp_fuse_writes": 0,
        "passive_tx_bytes_emitted": 0,
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "allow_boot_partition_targeting": False,
        "allow_destructive_fastboot": False,
        "suite_sha256": "8" * 64,
    }
    return {
        "p14_factory_cal_ibis_nvs": {
            **base,
            "factory_cal_mutation_bytes": 0,
            "private_key_bytes_read": 0,
        },
        "p15_secureboot_partition_align": {
            **base,
            "secureboot_6_scenario_firewall": {"passed": True},
            "partition_align_6_scenario_firewall": {"passed": True},
            "spacc_key_reads": 0,
        },
        "p16_realhw_ext2_p1_rescue": {
            **base,
            "pillar_a_ext2_installer_6_scenarios": {"passed": True},
            "pillar_b_p1_rescue_6_scenarios": {"passed": True},
            "pillar_c_tier0_lock_4_scenarios": {"passed": True},
        },
    }


def _make_clean_p2_p17_raw() -> dict:
    return {
        "all_passed": True,
        "pillar_a_wire_and_preflight_7_scenarios": {"passed": True},
        "pillar_b_dual_path_backup_6_scenarios": {"passed": True},
        "pillar_c_fake_iokit_regression_5_scenarios": {"passed": True},
        "live_usb_iokit_transmit_enabled": False,
        "allow_persistent_jiritsu_writes": False,
        "allow_destructive_jiritsu_commands": False,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "allow_boot_partition_targeting": False,
        "allow_destructive_fastboot": False,
        "otp_fuse_touches": 0,
        "otp_fuse_writes": 0,
        "passive_tx_bytes_emitted": 0,
        "physical_device_writes": 0,
        "physical_usb_bytes_transmitted": 0,
        "suite_sha256": "9" * 64,
    }


def _make_clean_p2_antirollback_raw() -> dict:
    return {
        "schema": "fx3-antirollback-and-byof-guard-v1",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "all_passed": True,
        "status": "SAFE_TIER_A_NO_OTP_TOUCH",
        "otp_fuse_touches": 0,
        "rpmb_counter_increments": 0,
        "antirollback_brick_risk": "ZERO_BRICK_RISK",
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "allow_boot_partition_targeting": False,
        "allow_destructive_fastboot": False,
        "gold_pair_tier": "TIER_A_GOLD_VERIFIED",
        "gold_pair_compatible": True,
        "fx3_wbi2_sections": 11,
        "fx6_wbi2_sections": 11,
        "downgrade_v205_blocked_code": "BLOCKED_OTP_ROLLBACK",
        "downgrade_v600_blocked_code": "BLOCKED_OTP_ROLLBACK",
        "cross_sku_fx6_nbl_blocked_code": "BLOCKED_CROSS_SKU",
        "cross_sku_fx6_wbi2_blocked_code": "BLOCKED_CROSS_SKU",
        "ext_csd_clean_safe": True,
        "ext_csd_boot_perm_wp_status": "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP",
        "ext_csd_user_perm_wp_status": "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP",
        "mmc_perm_wp_cmd_status": "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP",
        "errors": [],
    }


def _make_clean_p2_tier0_raw() -> dict:
    return {
        "tier0_schema": "fx3-tier0-backup-parity-and-manifest-guard-v1",
        "tier0_all_passed": True,
        "anti_transplant_same_body_allowed": True,
        "anti_transplant_cross_body_blocked": True,
        "heal_1_erasure_passed": True,
        "heal_2_erasures_passed": True,
        "heal_1_silent_bitrot_passed": True,
        "reject_3_losses_passed": True,
        "tier0_physical_device_writes": 0,
        "tier0_persistent_emmc_writes_authorized": False,
        "tier0_donor_p1_sha256": "a" * 64,
        "tier0_donor_p5_wbi2_sha256": "b" * 64,
        "tier0_errors": [],
        "init2_schema": "fx3-init2-escape-watchdog-fat-verifier-v1",
        "init2_all_passed": True,
        "escape_sandbox_passed": True,
        "escape_drill_count": 7,
        "escape_drills_passed": 7,
        "watchdog_suite_passed": True,
        "watchdog_scenario_count": 5,
        "watchdog_scenarios_passed": 5,
        "fat12_audit_passed": True,
        "fat16_audit_passed": True,
        "fat12_atomic_swap_passed": True,
        "fat16_atomic_swap_passed": True,
        "init2_emmc_write_bytes": 0,
        "init2_physical_writes": 0,
        "init2_persistent_emmc_writes_authorized": False,
        "init2_errors": [],
        "cross_body_transplant_rejected_by_guard": False,
    }


def _make_clean_p3_auditors() -> dict:
    aud = {
        k: {"all_checks_passed": True, "report_sha256": "c" * 64}
        for k in FIRMWARE_LAB_20_AUDITOR_KEYS[:14]
    }
    aud["wb_color_matrix_and_look_audit"] = {
        "all_checks_passed": True,
        "calibration_mutation_bytes": 0,
        "cp_mutation_bytes": 0,
        "pillar_d_factory_calibration": {"passed": True},
        "report_sha256": "d" * 64,
    }
    aud["proxy_clipname_and_sidecar_audit"] = {
        "all_checks_passed": True,
        "internal_emmc_clip_writes": 0,
        "c2pa_rq_lic_preserved": True,
        "pillar_1_clipname_proxy": {"passed": True},
        "pillar_2_dual_slot_matrix": {"passed": True},
        "pillar_3_nrtm_xml_sidecar": {"passed": True},
        "report_sha256": "e" * 64,
    }
    aud["assignable_zoom_ciz_and_fn_audit"] = {
        "all_checks_passed": True,
        "bk4_persistent_nvram_writes": 0,
        "null_gpio_faults": 0,
        "persistent_emmc_writes_authorized": False,
        "icx1295_crashed": False,
        "libcamera_crashed": False,
        "pillar_1_assignable_catalog": {"passed": True},
        "pillar_2_zoom_ciz_matrix": {"passed": True},
        "pillar_3_touch_af_desqueeze": {"passed": True},
        "pillar_4_big6_fn_shadow": {"passed": True},
        "report_sha256": "f" * 64,
    }
    aud["falsecolor_lpcm_tc_ub_audit"] = {
        "schema": "fx3-falsecolor-lpcm-tc-ub-v1",
        "all_checks_passed": True,
        "calibration_mutation_bytes": 0,
        "int24_wrap_around_count": 0,
        "bus_contention_count": 0,
        "persistent_emmc_writes_authorized": False,
        "pillar_1_false_color_el_zone": {"passed": True},
        "pillar_2_lpcm_headroom_dsp": {"passed": True},
        "pillar_3_smpte_ub_direction": {"passed": True},
        "pillar_4_zero_mutation_proof": {"passed": True},
        "report_sha256": "1" * 64,
    }
    aud["playback_shotmark_and_ae_audit"] = {
        "schema": "fx3-playback-shotmark-and-ae-v1",
        "all_checks_passed": True,
        "calibration_mutation_bytes": 0,
        "p4_nd_motor_fault_attempts": 0,
        "internal_emmc_format_possible": False,
        "persistent_emmc_writes_authorized": False,
        "pillar_1_playback_thumbnail_firewall": {"passed": True},
        "pillar_2_shotmark_essencemark_xml": {"passed": True},
        "pillar_3_push_auto_iris_ae_shift": {"passed": True},
        "pillar_4_zero_mutation_proof": {"passed": True},
        "report_sha256": "2" * 64,
    }
    aud["metadata_gyro_catalyst_and_anamorphic_audit"] = {
        "schema": "fx3-metadata-gyro-catalyst-and-anamorphic-v1",
        "all_checks_passed": True,
        "imu_calibration_mutation_bytes": 0,
        "cp_mutation_bytes": 0,
        "persistent_emmc_writes_authorized": False,
        "report_sha256": "3" * 64,
    }
    aud["interval_cache_and_ftp_audit"] = {
        "schema": "fx3-interval-cache-and-ftp-v1",
        "all_checks_passed": True,
        "calibration_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "persistent_emmc_writes_authorized": False,
        "report_sha256": "4" * 64,
    }
    aud["lut3d_cube_tetrahedral_and_sdi_hdmi_audit"] = {
        "schema": "fx3-lut3d-cube-tetrahedral-and-sdi-hdmi-v1",
        "all_checks_passed": True,
        "calibration_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "persistent_emmc_writes_authorized": False,
        "report_sha256": "5" * 64,
    }
    aud["c2pa_lens_shading_and_mc_fleet_audit"] = {
        "schema": "fx3-c2pa-lens-shading-and-mc-fleet-v1",
        "all_checks_passed": True,
        "pillar_4_factory_shading_immutability": {
            "passed": True,
            "calibration_mutation_bytes": 0,
            "emmc_mutation_bytes": 0,
            "bit_exact_preservation_verified": True,
            "persistent_emmc_writes_authorized": False,
        },
        "report_sha256": "6" * 64,
    }
    aud["hdr_hlg_bt2100_and_display_assist_audit"] = {
        "schema": "fx3-hdr-hlg-bt2100-and-display-assist-v1",
        "all_checks_passed": True,
        "pillar_4_nrtm_smpte_ul_immutability": {
            "passed": True,
            "calibration_mutation_bytes": 0,
            "emmc_mutation_bytes": 0,
            "persistent_emmc_writes_authorized": False,
        },
        "report_sha256": "7" * 64,
    }
    aud["hdmi_raw_prores_breathing_and_mishoe_clock_audit"] = {
        "schema": "fx3-hdmi-raw-prores-breathing-mishoe-v1",
        "all_checks_passed": True,
        "pillar_4_ob_clamp_preservation": {
            "passed": True,
            "ob_clamp_calibration_mutation_bytes": 0,
            "emmc_mutation_bytes": 0,
            "persistent_emmc_writes_authorized": False,
        },
        "report_sha256": "8" * 64,
    }
    aud["usb_uvc_uac_srt_and_crsdk_ptp_audit"] = {
        "schema": "fx3-usb-uvc-uac-srt-crsdk-ptp-v1",
        "all_checks_passed": True,
        "pillar_4_zero_mutation_emmc_preservation": {
            "passed": True,
            "calibration_mutation_bytes": 0,
            "emmc_mutation_bytes": 0,
            "persistent_emmc_writes_authorized": False,
        },
        "report_sha256": "9" * 64,
    }
    aud["mxf_mp4_essence_ptpv2_and_tally_umd_audit"] = {
        "schema": "fx3-mxf-mp4-essence-ptpv2-tally-umd-v1",
        "all_checks_passed": True,
        "pillar_d_zero_mutation_emmc_guard": {
            "passed": True,
            "calibration_mutation_bytes": 0,
            "emmc_mutation_bytes": 0,
            "persistent_emmc_writes_authorized": False,
        },
        "report_sha256": "0" * 64,
    }
    aud["vp_ledwall_ecs_freed_and_artnet_audit"] = {
        "all_checks_passed": True,
        "pillar_d_zero_mutation_vp_guard": {
            "passed": True,
            "calibration_mutation_bytes": 0,
            "emmc_mutation_bytes": 0,
            "persistent_emmc_writes_authorized": False,
        },
        "report_sha256": "a" * 64,
    }
    aud["xavc_hevc_intra_aces_idt_and_fz100_audit"] = {
        "all_checks_passed": True,
        "pillar_d_zero_mutation_guard": {
            "passed": True,
            "calibration_mutation_bytes": 0,
            "emmc_mutation_bytes": 0,
            "persistent_emmc_writes_authorized": False,
        },
        "report_sha256": "b" * 64,
    }
    aud["realhw_cp_rtos_and_backup_bin_audit"] = {
        "all_checks_passed": True,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "pillar1_cp_rtos_divergence": {"prefix_128k_identical": True},
        "pillar3_backup_layout": {"passed": True},
        "pillar4_zero_flash_auth": {
            "calibration_mutation_bytes": 0,
            "emmc_mutation_bytes": 0,
            "spi_nor_mutation_bytes": 0,
        },
        "report_sha256": "c" * 64,
    }
    aud["realhw_mpr_dmm_rec_pipeline_bridge_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": False,
        "pillar1_libmpr_abi_diff": {
            "fx6_only_export_count": 15,
            "fx6_appfw_passthrough_count": 74,
            "fx6_appfw_shim_required_symbols": [f"sym_{i}" for i in range(15)],
            "direct_struct_dereference_blocked": True,
        },
        "pillar2_dmm_topology": {"fx3_dmmcfg": {"target_20_units_present": 20}},
        "pillar4_uipc_record_lock": {
            "calibration_mutation_bytes": 0,
            "emmc_mutation_bytes": 0,
        },
        "report_sha256": "d" * 64,
    }
    return aud


def _make_clean_p4_vm_raw() -> dict:
    vm = {
        "schema": "fx3-vm-coemulation-suite-v1",
        "all_checks_passed": True,
        "audit_digest_sha256": "1" * 64,
        "redlines": {
            "p8_cp_mutation_forbidden": True,
            "cp_mutation_bytes": 0,
            "wbi_mutation_bytes": 0,
            "nvram_persistent_writes": 0,
            "physical_device_writes": 0,
        },
    }
    for sk in VM_COEMULATION_24_STAGE_KEYS:
        vm[sk] = {"all_checks_passed": True}
    vm["stage9_phase67_tc_lens_paint"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "phase67_audit_digest_sha256": "9" * 64,
    }
    vm["stage10_phase71_dualslot_ups_salvage"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "rsv_salvageable_frames": 114,
        "rsv_committed_frames": 114,
        "c2pa_license_untouched": True,
        "phase71_audit_digest_sha256": "a" * 64,
        "dualslot_proxy_pipeline": {
            "dram_elastic_fifo_mib": 256,
            "relay_auto_switch": {"dropped_frames": 0, "main_stalled": False},
        },
    }
    vm["stage11_phase78_touchaf_ciz_assignable"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "bk4_persistent_nvram_writes": 0,
        "null_gpio_derefs": 0,
        "mailbox_stalls": 0,
        "persistent_emmc_writes_authorized": False,
        "phase78_audit_digest_sha256": "b" * 64,
    }
    vm["stage12_phase82_camset_lpcm_tcub"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "bk4_persistent_nvram_writes": 0,
        "uart_boot_contention_events": 0,
        "persistent_emmc_writes_authorized": False,
        "phase82_audit_digest_sha256": "c" * 64,
    }
    vm["stage13_phase87_playback_shotmark_dewpoint"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "bk4_persistent_nvram_writes": 0,
        "p1_emmc_mutations": 0,
        "internal_emmc_writes": 0,
        "p4_nd_motor_faults": 0,
        "internal_emmc_format_blocked": True,
        "c2pa_license_untouched": True,
        "persistent_emmc_writes_authorized": False,
        "phase87_audit_digest_sha256": "d" * 64,
    }
    vm["stage14_phase91_gyroflow_rtmd_anamorphic"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "stock_cp_fault_count": 0,
        "phase91_audit_digest_sha256": "e" * 64,
    }
    vm["stage15_phase96_interval_cache_ftp_fan"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "wf12_00342260_hits": 0,
        "emmc_partition_mutations": 0,
        "phase96_audit_digest_sha256": "f" * 64,
    }
    vm["stage16_phase99_lut3d_subzero_sdi"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "lithium_plating_events": 0,
        "sdi_transceiver_faults": 0,
        "dropped_rec_triggers": 0,
        "phase99_audit_digest_sha256": "0" * 64,
    }
    vm["stage17_phase103_emi_exfat_endurance"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "emmc_sector_writes": 0,
        "emmc_wear_level_increments": 0,
        "cxd90057_gpio_damage_events": 0,
        "phase103_audit_digest_sha256": "1" * 64,
    }
    vm["stage18_phase107_c2pa_shading_mcfleet_ovp"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cnflasha_mutation_bytes": 0,
        "private_key_reads": 0,
        "private_key_exports": 0,
        "wf12_00342260_hits": 0,
        "cxd90057_pmic_damage_events": 0,
        "emount_flange_damage_events": 0,
        "persistent_emmc_writes_authorized": False,
        "phase107_audit_digest_sha256": "2" * 64,
    }
    vm["stage19_phase112_hdr_hlg_fiz_gimbal"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "nvram_persistent_writes": 0,
        "bk4_persistent_nvram_writes": 0,
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "display_assist_burn_in_frames": 0,
        "xavc_clean_feed_leakage_events": 0,
        "fiz_gear_strip_events": 0,
        "ibis_coil_saturation_events": 0,
        "duct_salt_haze_ingestion_damage_events": 0,
        "phase112_audit_digest_sha256": "3" * 64,
    }
    vm["stage20_proresraw_breathing_mishoe_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "nvram_persistent_writes": 0,
        "bk4_persistent_nvram_writes": 0,
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "raw_lut_burn_in_frames": 0,
        "pl_breathing_stale_crop_frames": 0,
        "audio_pop_click_frames": 0,
        "sy1129_hdmi_fuse_damage_events": 0,
        "cfexpress_fat_corruption_events": 0,
        "phase117_audit_digest_sha256": "4" * 64,
    }
    vm["stage21_uvc_srt_crsdk_usbpd_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "nvram_persistent_writes": 0,
        "bk4_persistent_nvram_writes": 0,
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "emmc_flash_mutation_bytes": 0,
        "wf12_00342260_hits": 0,
        "cxd90057_pad_damage_events": 0,
        "uvc_osd_burn_in_frames": 0,
        "srt_dropped_gops": 0,
        "uart_tx_bytes": 0,
        "phase121_audit_digest_sha256": "5" * 64,
    }
    vm["stage22_mxf_ptpv2_tally_monsoon_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "nvram_persistent_writes": 0,
        "bk4_persistent_nvram_writes": 0,
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "wf12_00342260_hits": 0,
        "phase127_audit_digest_sha256": "6" * 64,
    }
    vm["stage23_vp_ledwall_freed_artnet_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "nvram_persistent_writes": 0,
        "bk4_persistent_nvram_writes": 0,
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "wf12_00342260_hits": 0,
        "flash_split_band_frames": 0,
        "cxd90057_pin_damage_events": 0,
        "imx510_sensor_burn_events": 0,
        "ibis_endstop_slam_events": 0,
        "ibis_coil_thermal_runaway_events": 0,
        "phase132_audit_digest_sha256": "7" * 64,
    }
    vm["stage24_realhw_preflash_dualboot_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "nvram_persistent_writes": 0,
        "bk4_persistent_nvram_writes": 0,
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "spi_nor_mutation_bytes": 0,
        "sector0_mutation_bytes": 0,
        "rsv_orphan_count": 0,
        "wf12_00342260_hits": 0,
        "phase141_audit_digest_sha256": "8" * 64,
    }
    return vm


class TestPhase147RealHwMilestoneMasterGate(unittest.TestCase):
    report_clean: RealHwMilestone147MasterGateReport
    clean_elapsed_s: float
    report_primary: RealHwMilestone147MasterGateReport
    primary_elapsed_s: float
    use_clean_room: bool

    @classmethod
    def setUpClass(cls) -> None:
        cls.use_clean_room = _is_forced_clean_room()
        t0 = time.monotonic()
        cls.report_clean = build_realhw_milestone147_master_gate_report(synthetic_clean_room=True)
        cls.clean_elapsed_s = time.monotonic() - t0
        if cls.use_clean_room:
            cls.report_primary = cls.report_clean
            cls.primary_elapsed_s = cls.clean_elapsed_s
        else:
            t1 = time.monotonic()
            cls.report_primary = build_realhw_milestone147_master_gate_report(synthetic_clean_room=False)
            cls.primary_elapsed_s = time.monotonic() - t1

    # ------------------------------------------------------------------
    # 1. Exports, Constants & Dual-Mode End-to-End Readiness
    # ------------------------------------------------------------------

    def test_01_public_exports_and_hard_locked_constants(self) -> None:
        self.assertEqual(REALHW_MILESTONE147_SCHEMA, "realhw_milestone147_master_gate_v1")
        self.assertEqual(MILESTONE147_SCHEMA_VERSION, "realhw_milestone147_master_gate_v1")
        self.assertEqual(PHASE_147_VERSION, "147.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertGreaterEqual(len(RECOVERY_17_PILLAR_IDS), 17)
        self.assertGreaterEqual(len(FIRMWARE_LAB_28_AUDITOR_KEYS), 28)
        self.assertGreaterEqual(len(VM_COEMULATION_24_STAGE_KEYS), 24)
        self.assertIs(PERSISTENT_EMMC_WRITES_AUTHORIZED, False)
        self.assertIs(PERSISTENT_WRITE_RELEASE, False)
        self.assertIs(SPI_NOR_WRITE_AUTHORIZED, False)
        self.assertIs(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(CP_MUTATION_BYTES, 0)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(USB_OR_CAMERA_OPERATIONS, 0)
        self.assertIs(P8_CP_MUTATION_FORBIDDEN, True)
        self.assertIs(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN, True)
        for sym in (
            "MILESTONE147_PILLAR_IDS",
            "MILESTONE147_PILLAR_SPECS",
            "MILESTONE147_SCHEMA_VERSION",
            "PHASE_147_VERSION",
            "PHYSICAL_USB_PACKETS_EMITTED",
            "REALHW_MILESTONE147_SCHEMA",
            "RECOVERY_17_PILLAR_IDS",
            "FIRMWARE_LAB_28_AUDITOR_KEYS",
            "VM_COEMULATION_24_STAGE_KEYS",
            "SPI_NOR_WRITE_AUTHORIZED",
            "STATUS_MILESTONE147_FAIL_CLOSED",
            "STATUS_MILESTONE147_READY",
            "Milestone147PillarResult",
            "RealHwMilestone147FaultInjection",
            "RealHwMilestone147MasterGateReport",
            "RealHwMilestone147VerifyResult",
            "build_realhw_milestone147_master_gate_report",
            "compute_milestone147_sha256",
            "render_milestone147_markdown",
            "verify_realhw_milestone147_master_gate",
        ):
            self.assertTrue(hasattr(fx6_closure, sym), f"Missing package export: {sym}")

    def test_02_clean_room_end_to_end_milestone147(self) -> None:
        rep = self.report_clean
        self.assertLessEqual(self.clean_elapsed_s, 20.0)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready, msg=f"errors={rep.errors}")
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        self.assertGreaterEqual(rep.gate44_total_gates, 44)
        self.assertGreaterEqual(rep.gate44_offline_verified, 41)
        self.assertLess(rep.gate44_offline_verified, rep.gate44_total_gates)
        self.assertGreaterEqual(rep.gate44_simulated_verified, 44)
        self.assertEqual(rep.gate44_simulated_verified, rep.gate44_total_gates)
        self.assertGreaterEqual(rep.recovery_pillar_count, 17)
        self.assertEqual(rep.recovery_pillars_passed, rep.recovery_pillar_count)
        self.assertGreaterEqual(rep.firmware_lab_auditor_count, 28)
        self.assertEqual(rep.firmware_lab_auditors_passed, rep.firmware_lab_auditor_count)
        self.assertGreaterEqual(rep.vm_coemulation_stage_count, 24)
        self.assertEqual(rep.vm_coemulation_stages_passed, rep.vm_coemulation_stage_count)
        self.assertEqual(rep.vm_emmc_corruptions, 0)
        self.assertEqual(rep.vm_wf12_00342260_hits, 0)
        self.assertGreaterEqual(rep.p136_u6_command_count, 19)
        self.assertTrue(rep.p136_u4_u5_u6_closed)
        self.assertLessEqual(rep.p143_sd_escape_absent_us, 50)
        self.assertEqual(rep.p143_h0_equals_h3_count, 16)
        self.assertEqual(rep.p143_h0_h3_surface_count, 16)
        self.assertEqual(rep.r28_runs_verified, 3)
        self.assertEqual(rep.r29_runs_verified, 3)
        self.assertEqual(rep.qemu_real_kernel_nop_count, 0)
        self.assertEqual(rep.qemu_real_kernel_crashes, 0)
        self.assertEqual(rep.qemu_real_kernel_emmc_writes, 0)
        v = verify_realhw_milestone147_master_gate(rep)
        self.assertTrue(v.valid, msg=f"verify errors={v.errors}")

    def test_03_primary_or_local_donor_end_to_end_milestone147(self) -> None:
        rep = self.report_primary
        self.assertLessEqual(self.primary_elapsed_s, 20.0)
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if self.use_clean_room else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.verification_mode, expected_mode)
        self.assertTrue(rep.all_pillars_milestone_ready, msg=f"errors={rep.errors}")
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertGreaterEqual(rep.gate44_total_gates, 44)
        self.assertGreaterEqual(rep.recovery_pillars_passed, 17)
        self.assertGreaterEqual(rep.firmware_lab_auditors_passed, 28)
        self.assertGreaterEqual(rep.vm_coemulation_stages_passed, 24)
        self.assertIs(rep.persistent_emmc_writes_authorized, False)
        self.assertIs(rep.spi_nor_write_authorized, False)
        self.assertIs(rep.hardware_live_attachment_authorized, False)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        v = verify_realhw_milestone147_master_gate(rep.to_dict())
        self.assertTrue(v.valid, msg=f"verify errors={v.errors}")

    def test_04_deterministic_repeatability_and_zero_raw_bytes_repr(self) -> None:
        rep_a = self.report_clean
        rep_b = build_realhw_milestone147_master_gate_report(synthetic_clean_room=True)
        self.assertEqual(rep_a.milestone147_sha256, rep_b.milestone147_sha256)
        rendered = rep_a.to_deterministic_json(indent=2)
        self.assertEqual(rendered, rep_b.to_deterministic_json(indent=2))
        self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rendered))

    def test_05_markdown_rendering_bilingual(self) -> None:
        md = render_milestone147_markdown(self.report_clean)
        self.assertIn("realhw_milestone147_master_gate_v1", md)
        self.assertIn("persistent_emmc_writes_authorized = False", md)
        self.assertIn("spi_nor_write_authorized = False", md)
        self.assertIn("physical_usb_packets_emitted = 0", md)
        self.assertIn("4.9.337-scel+", md)
        self.assertIn("H0 == H3", md)
        self.assertIn("六大支柱总览", md)
        for pid in PILLAR_IDS:
            self.assertIn(f"`{pid}`", md)

    # ------------------------------------------------------------------
    # 2. Pillar 1 — 44-Gate Hardware Safety Preflight
    # ------------------------------------------------------------------

    def test_06_p1_nominal_and_sub_guards(self) -> None:
        p1 = next(p for p in self.report_primary.pillars if p.pillar_id == "P1")
        self.assertTrue(p1.passed)
        self.assertGreaterEqual(p1.evidence["total_gates"], 44)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 41)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 44)
        self.assertTrue(p1.evidence["g41_passed"])
        self.assertTrue(p1.evidence["g42_passed"])
        self.assertTrue(p1.evidence["g43_passed"])
        self.assertTrue(p1.evidence["g44_passed"])
        self.assertIs(p1.evidence["persistent_emmc_writes_authorized"], False)

    def test_07_p1_fault_persistent_writes_requested_fail_closed(self) -> None:
        raw = _worker_pillar_1(
            (str(DEFAULT_REPO_ROOT), True, {"p1_request_persistent_writes": True})
        )
        p1 = _evaluate_pillar_1(raw)
        self.assertFalse(p1.passed)
        self.assertEqual(p1.status, STATUS_FAIL_CLOSED)

    def test_08_p1_fault_g43_unaligned_elf_fail_closed(self) -> None:
        raw = _worker_pillar_1(
            (str(DEFAULT_REPO_ROOT), True, {"p1_jiritsu_service_kwargs": {"elf_pt_load_align_bytes": 4096}})
        )
        p1 = _evaluate_pillar_1(raw)
        self.assertFalse(p1.passed)

    def test_09_p1_fault_g44_pnflasha_or_modify_p1_fail_closed(self) -> None:
        raw = _worker_pillar_1(
            (str(DEFAULT_REPO_ROOT), True, {"p1_cnflasha_dualboot_kwargs": {"target_block_device": "/dev/pnflasha15"}})
        )
        p1 = _evaluate_pillar_1(raw)
        self.assertFalse(p1.passed)

    def test_10_p1_fault_g41_or_g42_blocked(self) -> None:
        raw_g41 = _worker_pillar_1(
            (
                str(DEFAULT_REPO_ROOT),
                True,
                {
                    "p1_vp_strobe_genlock_kwargs": {
                        "bnc_sync_signal_type": "TRILEVEL_GENLOCK",
                        "connected_to_fx3_multiterminal": True,
                    }
                },
            )
        )
        raw_g42 = _worker_pillar_1(
            (
                str(DEFAULT_REPO_ROOT),
                True,
                {
                    "p1_vehiclerig_ibis_kwargs": {
                        "vehicle_or_aerial_exterior_mount": True,
                        "secondary_steel_safety_cable_rated_kg": 0.0,
                    }
                },
            )
        )
        self.assertFalse(_evaluate_pillar_1(raw_g41).passed)
        self.assertFalse(_evaluate_pillar_1(raw_g42).passed)

    def test_11_p1_forward_compat_45_gates(self) -> None:
        raw_45 = _make_clean_p1_raw(total_gates=45, offline_verified=42, sim_verified=45)
        p1 = _evaluate_pillar_1(raw_45)
        self.assertTrue(p1.passed, msg=f"errors={p1.errors}")
        self.assertEqual(p1.evidence["total_gates"], 45)

    # ------------------------------------------------------------------
    # 3. Pillar 2 — >= 17 Recovery Pillars & Streaming Cold Backup
    # ------------------------------------------------------------------

    def test_12_p2_nominal_17_pillars_and_zero_touches(self) -> None:
        p2 = next(p for p in self.report_primary.pillars if p.pillar_id == "P2")
        self.assertTrue(p2.passed)
        self.assertGreaterEqual(p2.evidence["recovery_pillar_count"], 17)
        self.assertEqual(p2.evidence["recovery_pillars_passed"], p2.evidence["recovery_pillar_count"])
        for key in RECOVERY_17_PILLAR_IDS:
            self.assertTrue(p2.evidence["pillar_statuses"].get(key), msg=f"missing/failed {key}")
        self.assertEqual(p2.evidence["otp_fuse_touches"], 0)
        self.assertEqual(p2.evidence["rpmb_counter_increments"], 0)
        self.assertEqual(p2.evidence["passive_tx_bytes_emitted"], 0)
        self.assertEqual(p2.evidence["physical_device_writes"], 0)
        self.assertEqual(p2.evidence["physical_usb_bytes_transmitted"], 0)

    def test_13_p2_fault_factory_cal_ibis_nvs(self) -> None:
        p2, _ = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_p11_p13_raw(),
            _make_clean_p2_p14_p16_raw(),
            _make_clean_p2_p17_raw(),
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            RealHwMilestone147FaultInjection(p2_inject_factory_cal_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_14_p2_fault_secureboot_partition_align(self) -> None:
        p2, _ = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_p11_p13_raw(),
            _make_clean_p2_p14_p16_raw(),
            _make_clean_p2_p17_raw(),
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            RealHwMilestone147FaultInjection(p2_inject_secureboot_align_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_15_p2_fault_ext2_p1_rescue(self) -> None:
        p2, _ = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_p11_p13_raw(),
            _make_clean_p2_p14_p16_raw(),
            _make_clean_p2_p17_raw(),
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            RealHwMilestone147FaultInjection(p2_inject_ext2_p1_rescue_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_16_p2_fault_adjustcontrol_streaming(self) -> None:
        p2, _ = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_p11_p13_raw(),
            _make_clean_p2_p14_p16_raw(),
            _make_clean_p2_p17_raw(),
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            RealHwMilestone147FaultInjection(p2_inject_adjustcontrol_streaming_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_17_p2_fault_physical_usb_packets_emitted(self) -> None:
        p2, _ = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_p11_p13_raw(),
            _make_clean_p2_p14_p16_raw(),
            _make_clean_p2_p17_raw(),
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            RealHwMilestone147FaultInjection(p2_physical_usb_packets_override=64),
        )
        self.assertFalse(p2.passed)

    def test_18_p2_fault_otp_rpmb_or_passive_tx_nonzero(self) -> None:
        for fault in (
            RealHwMilestone147FaultInjection(p2_otp_fuse_touches_override=1),
            RealHwMilestone147FaultInjection(p2_rpmb_increments_override=1),
            RealHwMilestone147FaultInjection(p2_passive_tx_bytes_override=1),
        ):
            p2, _ = _evaluate_pillar_2(
                _make_clean_p2_master_raw(),
                _make_clean_p2_p8_p10_raw(),
                _make_clean_p2_p11_p13_raw(),
                _make_clean_p2_p14_p16_raw(),
                _make_clean_p2_p17_raw(),
                _make_clean_p2_antirollback_raw(),
                _make_clean_p2_tier0_raw(),
                fault,
            )
            self.assertFalse(p2.passed)

    def test_19_p2_forward_compat_18_pillars(self) -> None:
        p14_16 = _make_clean_p2_p14_p16_raw()
        p14_16["p18_future_recovery"] = {"all_passed": True}
        p2_ok, meta_ok = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_p11_p13_raw(),
            p14_16,
            _make_clean_p2_p17_raw(),
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            RealHwMilestone147FaultInjection(),
        )
        self.assertTrue(p2_ok.passed, msg=f"errors={p2_ok.errors}")
        self.assertEqual(meta_ok["recovery_pillar_count"], 18)

        p14_16["p18_future_recovery"] = {"all_passed": False}
        p2_bad, _ = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_p11_p13_raw(),
            p14_16,
            _make_clean_p2_p17_raw(),
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            RealHwMilestone147FaultInjection(),
        )
        self.assertFalse(p2_bad.passed)

    # ------------------------------------------------------------------
    # 4. Pillar 3 — >= 28 Firmware-Lab Real-Binary Auditors
    # ------------------------------------------------------------------

    def test_20_p3_nominal_28_auditors_u2_u3_libmpr_dmmcfg(self) -> None:
        p3 = next(p for p in self.report_primary.pillars if p.pillar_id == "P3")
        self.assertTrue(p3.passed)
        self.assertGreaterEqual(p3.evidence["auditor_count"], 28)
        self.assertEqual(p3.evidence["passed_auditor_count"], p3.evidence["auditor_count"])
        for key in FIRMWARE_LAB_28_AUDITOR_KEYS:
            self.assertTrue(p3.evidence["auditor_statuses"].get(key), msg=f"missing/failed {key}")
        self.assertTrue(p3.evidence["phase137_u2_u3_cp_backup_ok"])
        self.assertTrue(p3.evidence["phase140_mpr_dmm_rec_bridge_ok"])
        self.assertEqual(p3.evidence["calibration_mutation_bytes"], 0)
        self.assertIs(p3.evidence["spi_nor_write_authorized"], False)

    def test_21_p3_fault_vp_ledwall_emmc_mutation(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_auditors(),
            RealHwMilestone147FaultInjection(p3_vp_ledwall_emmc_mutation_bytes=1),
        )
        self.assertFalse(p3.passed)

    def test_22_p3_fault_xavc_fz100_emmc_mutation(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_auditors(),
            RealHwMilestone147FaultInjection(p3_xavc_fz100_emmc_mutation_bytes=1),
        )
        self.assertFalse(p3.passed)

    def test_23_p3_fault_realhw_cp_spi_nor_mutation(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_auditors(),
            RealHwMilestone147FaultInjection(p3_realhw_cp_spi_mutation_bytes=4),
        )
        self.assertFalse(p3.passed)

    def test_24_p3_fault_realhw_mpr_bridge_emmc_mutation(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_auditors(),
            RealHwMilestone147FaultInjection(p3_realhw_mpr_bridge_emmc_mutation_bytes=4),
        )
        self.assertFalse(p3.passed)

    def test_25_p3_forward_compat_29_auditors(self) -> None:
        aud = _make_clean_p3_auditors()
        aud["future_auditor_29"] = {"all_checks_passed": True, "report_sha256": "e" * 64}
        p3_ok, meta_ok = _evaluate_pillar_3(aud, RealHwMilestone147FaultInjection())
        self.assertTrue(p3_ok.passed, msg=f"errors={p3_ok.errors}")
        self.assertEqual(meta_ok["auditor_count"], 29)

        aud["future_auditor_29"] = {"all_checks_passed": False}
        p3_bad, _ = _evaluate_pillar_3(aud, RealHwMilestone147FaultInjection())
        self.assertFalse(p3_bad.passed)

    # ------------------------------------------------------------------
    # 5. Pillar 4 — >= 24 Stage VM HIL Co-Emulation
    # ------------------------------------------------------------------

    def test_26_p4_nominal_24_stages_zero_emmc_corruptions(self) -> None:
        p4 = next(p for p in self.report_primary.pillars if p.pillar_id == "P4")
        self.assertTrue(p4.passed)
        self.assertGreaterEqual(p4.evidence["stage_count"], 24)
        self.assertEqual(p4.evidence["passed_stage_count"], p4.evidence["stage_count"])
        for sk in VM_COEMULATION_24_STAGE_KEYS:
            self.assertTrue(p4.evidence["stage_statuses"].get(sk), msg=f"missing/failed {sk}")
        self.assertEqual(p4.evidence["emmc_corruptions"], 0)
        self.assertEqual(p4.evidence["wf12_00342260_hits"], 0)

    def test_27_p4_fault_stage22_emmc_mutation(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_vm_raw(),
            RealHwMilestone147FaultInjection(p4_stage22_emmc_mutation_bytes=1),
        )
        self.assertFalse(p4.passed)

    def test_28_p4_fault_stage23_emmc_mutation(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_vm_raw(),
            RealHwMilestone147FaultInjection(p4_stage23_emmc_mutation_bytes=1),
        )
        self.assertFalse(p4.passed)

    def test_29_p4_fault_stage24_redlines(self) -> None:
        for fault in (
            RealHwMilestone147FaultInjection(p4_stage24_emmc_mutation_bytes=1),
            RealHwMilestone147FaultInjection(p4_stage24_spi_nor_mutation_bytes=1),
            RealHwMilestone147FaultInjection(p4_stage24_sector0_mutation_bytes=1),
            RealHwMilestone147FaultInjection(p4_stage24_rsv_orphan_count=1),
        ):
            p4, _ = _evaluate_pillar_4(_make_clean_p4_vm_raw(), fault)
            self.assertFalse(p4.passed)

    def test_30_p4_forward_compat_25_stages(self) -> None:
        vm = _make_clean_p4_vm_raw()
        vm["stage25_future_realhw_hil"] = {"all_checks_passed": True}
        p4_ok, meta_ok = _evaluate_pillar_4(vm, RealHwMilestone147FaultInjection())
        self.assertTrue(p4_ok.passed, msg=f"errors={p4_ok.errors}")
        self.assertEqual(meta_ok["stage_count"], 25)

        vm["stage25_future_realhw_hil"] = {"all_checks_passed": False}
        p4_bad, _ = _evaluate_pillar_4(vm, RealHwMilestone147FaultInjection())
        self.assertFalse(p4_bad.passed)

    # ------------------------------------------------------------------
    # 6. Pillar 5 — Closure U4/U5/U6 & BYOF SD Stage-B + H0 == H3
    # ------------------------------------------------------------------

    def test_31_p5_nominal_u4_u5_u6_eh1_and_h0_eq_h3_16(self) -> None:
        p5 = next(p for p in self.report_primary.pillars if p.pillar_id == "P5")
        self.assertTrue(p5.passed)
        self.assertGreaterEqual(p5.evidence["p136_u6_command_count"], 19)
        self.assertTrue(p5.evidence["p136_u4_u5_u6_closed"])
        self.assertLessEqual(p5.evidence["p143_eh1_observed_latency_us"], 50)
        self.assertEqual(p5.evidence["p143_h0_equals_h3_count"], 16)
        self.assertEqual(p5.evidence["p143_h0_h3_surface_count"], 16)
        self.assertGreaterEqual(p5.evidence["p143_power_loss_drills_passed"], 5)

    def test_32_p5_fault_p136_u4_u5_u6(self) -> None:
        raw_5a = _worker_phase136(True)
        raw_5b = _worker_phase143((str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True))
        p5, _ = _evaluate_pillar_5(
            raw_5a,
            raw_5b,
            RealHwMilestone147FaultInjection(p5_inject_p136_u4_u5_u6_fault=True),
        )
        self.assertFalse(p5.passed)

    def test_33_p5_fault_p143_escape_hatch_over_50us(self) -> None:
        raw_5a = _worker_phase136(True)
        raw_5b = _worker_phase143((str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True))
        p5, _ = _evaluate_pillar_5(
            raw_5a,
            raw_5b,
            RealHwMilestone147FaultInjection(p5_inject_p143_escape_hatch_over_budget_us=10),
        )
        self.assertFalse(p5.passed)

    def test_34_p5_fault_p143_h0_h3_drift(self) -> None:
        raw_5a = _worker_phase136(True)
        raw_5b = _worker_phase143((str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True))
        p5, _ = _evaluate_pillar_5(
            raw_5a,
            raw_5b,
            RealHwMilestone147FaultInjection(p5_inject_p143_h0_h3_drift=True),
        )
        self.assertFalse(p5.passed)

    # ------------------------------------------------------------------
    # 7. Pillar 6 — Live FX3 7.02 Kernel QEMU Round 28 & 29 Receipts
    # ------------------------------------------------------------------

    def test_35_p6_committed_r28_r29_receipts_o_rdonly(self) -> None:
        r28_data, r28_src = _load_round28_or_29_summary(28, repo_root=REPO_ROOT, use_clean_room=False)
        r29_data, r29_src = _load_round28_or_29_summary(29, repo_root=REPO_ROOT, use_clean_room=False)
        self.assertEqual(r28_src, "REPO_SUMMARY_O_RDONLY")
        self.assertEqual(r29_src, "REPO_SUMMARY_O_RDONLY")
        self.assertEqual(r28_data["schema"], ROUND28_EXPECTED_SCHEMA)
        self.assertEqual(r29_data["schema"], ROUND29_EXPECTED_SCHEMA)

    def test_36_p6_clean_room_fallback_when_reports_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p6, meta6 = _evaluate_pillar_6(
                repo_root=Path(tmp),
                use_clean_room=True,
                faults=RealHwMilestone147FaultInjection(),
                p1_meta={"persistent_emmc_writes_authorized": False, "simulated_ready_for_hardware_attach": False},
                p2_meta={"otp_fuse_touches": 0, "rpmb_counter_increments": 0, "passive_tx_bytes_emitted": 0, "physical_usb_bytes_transmitted": 0},
                p3_meta={"calibration_mutation_bytes": 0},
                p4_meta={"cp_mutation_bytes": 0, "bk4_persistent_nvram_writes": 0, "wf12_00342260_hits": 0, "emmc_corruptions": 0},
                p5_meta={"h0_equals_h3_count": 16},
            )
        self.assertTrue(p6.passed, msg=f"errors={p6.errors}")
        self.assertEqual(p6.evidence["r28_source"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(p6.evidence["r29_source"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(meta6["r28_runs_verified"], 3)
        self.assertEqual(meta6["r29_runs_verified"], 3)

    def test_37_p6_missing_reports_without_clean_room_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                _load_round28_or_29_summary(28, repo_root=Path(tmp), use_clean_room=False)

    def test_38_p6_fault_r28_nop_crash_or_emmc_nonzero(self) -> None:
        base_kw = dict(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            p1_meta={"persistent_emmc_writes_authorized": False, "simulated_ready_for_hardware_attach": False},
            p2_meta={"otp_fuse_touches": 0, "rpmb_counter_increments": 0, "passive_tx_bytes_emitted": 0, "physical_usb_bytes_transmitted": 0},
            p3_meta={"calibration_mutation_bytes": 0},
            p4_meta={"cp_mutation_bytes": 0, "bk4_persistent_nvram_writes": 0, "wf12_00342260_hits": 0, "emmc_corruptions": 0},
            p5_meta={"h0_equals_h3_count": 16},
        )
        for fault in (
            RealHwMilestone147FaultInjection(p6_r28_nop_count_override=1),
            RealHwMilestone147FaultInjection(p6_r28_crashes_override=1),
            RealHwMilestone147FaultInjection(p6_r28_emmc_writes_override=1),
        ):
            p6, _ = _evaluate_pillar_6(faults=fault, **base_kw)
            self.assertFalse(p6.passed)

    def test_39_p6_fault_r29_nop_crash_emmc_or_tamper_schema(self) -> None:
        base_kw = dict(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            p1_meta={"persistent_emmc_writes_authorized": False, "simulated_ready_for_hardware_attach": False},
            p2_meta={"otp_fuse_touches": 0, "rpmb_counter_increments": 0, "passive_tx_bytes_emitted": 0, "physical_usb_bytes_transmitted": 0},
            p3_meta={"calibration_mutation_bytes": 0},
            p4_meta={"cp_mutation_bytes": 0, "bk4_persistent_nvram_writes": 0, "wf12_00342260_hits": 0, "emmc_corruptions": 0},
            p5_meta={"h0_equals_h3_count": 16},
        )
        for fault in (
            RealHwMilestone147FaultInjection(p6_r29_nop_count_override=1),
            RealHwMilestone147FaultInjection(p6_r29_crashes_override=1),
            RealHwMilestone147FaultInjection(p6_r29_emmc_writes_override=1),
            RealHwMilestone147FaultInjection(p6_r29_tamper_schema=True),
        ):
            p6, _ = _evaluate_pillar_6(faults=fault, **base_kw)
            self.assertFalse(p6.passed)

    # ------------------------------------------------------------------
    # 8. Tamper-Evident Verifier & CLI Subcommand Tests
    # ------------------------------------------------------------------

    def test_40_verifier_rejects_non_mapping_and_bad_schema(self) -> None:
        res_bad_type = verify_realhw_milestone147_master_gate(["not", "a", "dict"])
        self.assertFalse(res_bad_type.valid)
        d = self.report_clean.to_dict()
        d["schema_version"] = "wrong-schema"
        d["milestone147_sha256"] = compute_milestone147_sha256(d)
        res_bad_schema = verify_realhw_milestone147_master_gate(d)
        self.assertFalse(res_bad_schema.valid)
        self.assertFalse(res_bad_schema.schema_ok)

    def test_41_verifier_rejects_tampered_sha256_and_mutated_field(self) -> None:
        d = self.report_clean.to_dict()
        d["r28_runs_verified"] = 2
        res_mut = verify_realhw_milestone147_master_gate(d)
        self.assertFalse(res_mut.valid)
        self.assertFalse(res_mut.digest_matched)

    def test_42_verifier_rejects_breached_hardware_redlines(self) -> None:
        for key, bad_val in (
            ("persistent_emmc_writes_authorized", True),
            ("spi_nor_write_authorized", True),
            ("hardware_live_attachment_authorized", True),
            ("physical_usb_packets_emitted", 1),
            ("otp_fuse_touches", 1),
            ("rpmb_counter_increments", 1),
            ("passive_tx_bytes_emitted", 1),
        ):
            d = copy.deepcopy(self.report_clean.to_dict())
            d[key] = bad_val
            d["milestone147_sha256"] = compute_milestone147_sha256(d)
            res = verify_realhw_milestone147_master_gate(d)
            self.assertFalse(res.valid, msg=f"Should reject breached {key}={bad_val}")
            self.assertFalse(res.safety_redlines_ok)

    def test_43_verifier_forward_compat_and_below_threshold_counts(self) -> None:
        # Higher forward-compatible counts (45 gates, 18 recovery, 29 auditors, 25 VM stages) must pass
        d_high = copy.deepcopy(self.report_clean.to_dict())
        d_high["gate44_total_gates"] = 45
        d_high["gate44_offline_verified"] = 42
        d_high["gate44_simulated_verified"] = 45
        d_high["recovery_pillar_count"] = 18
        d_high["recovery_pillars_passed"] = 18
        d_high["firmware_lab_auditor_count"] = 29
        d_high["firmware_lab_auditors_passed"] = 29
        d_high["vm_coemulation_stage_count"] = 25
        d_high["vm_coemulation_stages_passed"] = 25
        d_high["milestone147_sha256"] = compute_milestone147_sha256(d_high)
        res_high = verify_realhw_milestone147_master_gate(d_high)
        self.assertTrue(res_high.valid, msg=f"errors={res_high.errors}")

        # Below-threshold counts must fail closed
        for key, bad_val in (
            ("gate44_total_gates", 43),
            ("recovery_pillar_count", 16),
            ("firmware_lab_auditor_count", 27),
            ("vm_coemulation_stage_count", 23),
        ):
            d_low = copy.deepcopy(self.report_clean.to_dict())
            d_low[key] = bad_val
            d_low["milestone147_sha256"] = compute_milestone147_sha256(d_low)
            res_low = verify_realhw_milestone147_master_gate(d_low)
            self.assertFalse(res_low.valid, msg=f"Should fail below-threshold {key}={bad_val}")

    def test_44_verifier_rejects_raw_bytes_repr_in_serialized_payload(self) -> None:
        d = copy.deepcopy(self.report_clean.to_dict())
        d["errors"] = ["leaked b'rawbytes' repr"]
        d["milestone147_sha256"] = compute_milestone147_sha256(d)
        res = verify_realhw_milestone147_master_gate(d)
        self.assertFalse(res.valid)

    def test_45_cli_clean_room_json_output_and_markdown_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "m147.json"
            md_path = Path(tmp) / "m147.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-147",
                        "--clean-room",
                        "--json",
                        "--output",
                        str(json_path),
                        "--markdown-out",
                        str(md_path),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed["schema_version"], REALHW_MILESTONE147_SCHEMA)
            self.assertTrue(verify_realhw_milestone147_master_gate(parsed).valid)
            self.assertIn("MILESTONE_147_BENCH_READINESS_VERIFIED", md_path.read_text(encoding="utf-8"))

    def test_46_cli_clean_room_human_summary_line(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = fx6_cli_main(["verify-milestone-147", "--clean-room"])
        self.assertEqual(rc, 0)
        line = buf.getvalue().strip()
        self.assertIn("status=OK", line)
        self.assertIn("schema=realhw_milestone147_master_gate_v1", line)
        self.assertIn("pillars=6/6", line)
        self.assertIn("h0_eq_h3=16/16", line)
        self.assertIn("r28=3/3", line)
        self.assertIn("r29=3/3", line)
        self.assertIn("emmc_writes_auth=False", line)
        self.assertIn("spi_nor_auth=False", line)
        self.assertIn("usb_tx=0", line)


if __name__ == "__main__":
    unittest.main()
