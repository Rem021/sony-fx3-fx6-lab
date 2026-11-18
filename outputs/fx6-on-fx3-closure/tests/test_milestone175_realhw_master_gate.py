"""Phase 175 dual-mode unit tests for Milestone Phase 175 6-Pillar Real-Hardware Master Gate."""

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
from fx3_recovery.realhw_22pillar_master_recovery_verifier import MASTER_22_PILLAR_IDS  # noqa: E402
from fx6_closure.realhw_milestone147_master_gate import (  # noqa: E402
    VM_COEMULATION_24_STAGE_KEYS,
    _worker_phase136,
)
from fx6_closure.realhw_milestone175_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    DEFAULT_REPO_ROOT,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FIRMWARE_LAB_36_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
    ISP_WRITE_AUTHORIZED,
    MILESTONE175_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_175_VERSION,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    REALHW_MILESTONE175_SCHEMA,
    RECOVERY_22_PILLAR_IDS,
    ROUND28_TO_34_SPECS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    VM_COEMULATION_30_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    Milestone175PillarResult,
    RealHwMilestone175FaultInjection,
    RealHwMilestone175MasterGateReport,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _load_round28_to_34_summary,
    _worker_phase143_and_154,
    _worker_recovery_22pillar,
    build_realhw_milestone175_master_gate_report,
    compute_milestone175_sha256,
    render_milestone175_markdown,
    verify_realhw_milestone175_master_gate,
)
from fx6_closure.stage_b_milestone110_master_gate import FIRMWARE_LAB_20_AUDITOR_KEYS  # noqa: E402

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


def _make_clean_p1_off(*, total_gates: int = 58, verified_gates: int = 55) -> dict:
    return {
        "schema": "fx3-safety-58gate-preflight-v1",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "total_gates": total_gates,
        "verified_gates": verified_gates,
        "offline_55_gates_verified": True,
        "all_58_gates_verified": False,
        "g13_to_g58_all_passed": True,
        "g57_to_g58_all_passed": True,
        "dry_run_rehearsal_only": False,
        "overall_ready_for_hardware_attach": False,
        "agent_auto_flash_blocked": True,
        "el3_payload_transmit_authorized": False,
        "spi_nor_write_authorized": False,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "nested_g45_to_g58_valid": {f"g{n}": True for n in range(45, 59)},
        "gates_45_to_58": [
            {"gate_id": f"G{n}", "gate_code": f"G{n}", "status": "PASS", "passed": True, "violation_codes": ()}
            for n in range(45, 59)
        ],
        "errors": [],
    }


def _make_clean_p1_sim(*, total_gates: int = 58, verified_gates: int = 58) -> dict:
    gates_45_58 = [
        {"gate_id": f"G{n}", "gate_code": f"G{n}", "status": "PASS", "passed": True, "violation_codes": ()}
        for n in range(45, 45 + max(14, total_gates - 44))
    ]
    return {
        "schema": "fx3-safety-58gate-preflight-v1",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "total_gates": total_gates,
        "verified_gates": verified_gates,
        "offline_55_gates_verified": True,
        "all_58_gates_verified": True,
        "g13_to_g58_all_passed": True,
        "g57_to_g58_all_passed": True,
        "dry_run_rehearsal_only": True,
        "overall_ready_for_hardware_attach": False,
        "agent_auto_flash_blocked": True,
        "el3_payload_transmit_authorized": False,
        "spi_nor_write_authorized": False,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "nested_g45_to_g58_valid": {f"g{n}": True for n in range(45, 59)},
        "gates_45_to_58": gates_45_58,
        "errors": [],
    }


def _make_clean_p2_22pillar() -> dict:
    return {
        "schema": "fx3-recovery-22pillar-master-v1",
        "version": "174.0.0",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "all_passed": True,
        "status": "RECOVERY_MASTER_22PILLAR_VERIFIED_SAFE",
        "pillar_count": len(RECOVERY_22_PILLAR_IDS),
        "pillars_passed": len(RECOVERY_22_PILLAR_IDS),
        "failed_pillars": [],
        "pillars": [
            {"pillar_id": pid, "passed": True, "errors": ()}
            for pid in RECOVERY_22_PILLAR_IDS
        ],
        "pillar22_a_dual_media": {"passed": True},
        "pillar22_b_gf256_scrub": {"passed": True},
        "master_22pillar_sha256": "a" * 64,
        "otp_fuse_touches": 0,
        "otp_fuse_writes": 0,
        "rpmb_counter_increments": 0,
        "passive_tx_bytes_emitted": 0,
        "physical_usb_packets_emitted": 0,
        "physical_device_writes": 0,
        "raw_firmware_bytes_leaked": 0,
        "el3_payload_transmit_authorized": False,
        "isp_write_authorized": False,
        "spi_nor_write_authorized": False,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "live_usb_iokit_transmit_enabled": False,
        "errors": [],
    }


def _make_clean_p3_36_auditors() -> dict:
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
            "persistent_emmc_writes_authorized": False,
        },
        "report_sha256": "d" * 64,
    }
    # Auditors #29 .. #36
    aud["realhw_lens_ibis_audio_hdmi_peripheral_bridge_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "p18_lens_writes_permitted": False,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "report_sha256": "e" * 64,
    }
    aud["realhw_physical_controls_tally_fan_and_power_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "report_sha256": "f" * 64,
    }
    aud["realhw_wifi_bt_usb_uvc_network_bridge_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "rf_nvs_p12_p13_writes_permitted": False,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "rf_nvs_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "report_sha256": "1" * 64,
    }
    aud["realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "sensor_cal_p2_writes_permitted": False,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "sensor_cal_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "report_sha256": "2" * 64,
    }
    aud["realhw_cfexpress_sdxc_exfat_rsv_ufu_coexistence_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "emmc_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "report_sha256": "3" * 64,
    }
    aud["realhw_cxd90057_cxd90058_sabin_codec_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "cxd90058_fw_mutation_bytes": 0,
        "cp_mutation_bytes": 0,
        "sabin_microcode_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "report_sha256": "4" * 64,
    }
    aud["realhw_c2pa_cert_vmcbncm1_tc_gyro_meta_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "c2pa_cert_mutation_bytes": 0,
        "cp_mutation_bytes": 0,
        "p18_lens_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "report_sha256": "5" * 64,
    }
    aud["realhw_wbi2_hibdrv_hibernation_isolation_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "wbi_save_inhibited": True,
        "stock_fx3_wbi2_preserved": True,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "wbi_mutation_bytes": 0,
        "report_sha256": "6" * 64,
    }
    return aud


def _make_clean_p4_30_vm() -> dict:
    vm: dict = {
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
    # Stages 25 .. 30
    vm["stage25_realhw_mpr_dmm_rec"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "appfw_crashes": 0,
        "rsv_orphan_count": 0,
        "wf12_00342260_hits": 0,
        "phase145_audit_digest_sha256": "5" * 64,
    }
    vm["stage26_realhw_body_peripheral_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "p18_lens_writes_permitted": False,
        "persistent_emmc_writes_authorized": False,
        "p18_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "appfw_crashes": 0,
        "wf12_00342260_hits": 0,
        "phase150_audit_digest_sha256": "6" * 64,
    }
    vm["stage27_realhw_imx510_network_usb_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "psd_defdet_writes_permitted": False,
        "rf_nvs_p12_p13_writes_permitted": False,
        "bt_hci_blocking_wait_eliminated": True,
        "usb_msc_0da1_recovery_intact": True,
        "persistent_emmc_writes_authorized": False,
        "sensor_cal_mutation_bytes": 0,
        "rf_nvs_p12_p13_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "wf12_00342260_hits": 0,
        "phase157_audit_digest_sha256": "7" * 64,
    }
    vm["stage28_realhw_cfexpress_ufu_5tier_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "el3_payload_transmit_authorized": False,
        "user_media_clips_intact": True,
        "emmc_mutation_bytes": 0,
        "spi_nor_mutation_bytes": 0,
        "wf12_00342260_hits": 0,
        "phase162_audit_digest_sha256": "8" * 64,
    }
    vm["stage29_realhw_cxd90058_sabin_seal_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "cxd90058_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "spi_nor_mutation_bytes": 0,
        "otp_write_count": 0,
        "rpmb_write_count": 0,
        "orig_residual_count": 0,
        "tmp_jiritsu_residual_count": 0,
        "p6_chunk_residual_count": 0,
        "ipc_deadlocks": 0,
        "wf12_00342260_hits": 0,
        "phase167_audit_digest_sha256": "9" * 64,
    }
    vm["stage30_realhw_c2pa_tc_gyro_prebench_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "c2pa_cert_mutation_bytes": 0,
        "p2_mutation_bytes": 0,
        "p18_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "spi_nor_mutation_bytes": 0,
        "otp_write_count": 0,
        "rpmb_write_count": 0,
        "uart_contention_damage_events": 0,
        "over_voltage_damage_events": 0,
        "wf12_00342260_hits": 0,
        "phase172_audit_digest_sha256": "0" * 64,
    }
    return vm


class TestMilestone175RealHwMasterGate(unittest.TestCase):
    """48 dual-mode unit tests for Milestone Phase 175 6-Pillar Master Gate."""

    report_clean: RealHwMilestone175MasterGateReport
    clean_elapsed_s: float
    report_primary: RealHwMilestone175MasterGateReport
    primary_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.perf_counter()
        cls.report_clean = build_realhw_milestone175_master_gate_report(
            synthetic_clean_room=True
        )
        cls.clean_elapsed_s = time.perf_counter() - t0

        if _is_forced_clean_room():
            cls.report_primary = cls.report_clean
            cls.primary_elapsed_s = cls.clean_elapsed_s
        else:
            t1 = time.perf_counter()
            cls.report_primary = build_realhw_milestone175_master_gate_report(
                synthetic_clean_room=False
            )
            cls.primary_elapsed_s = time.perf_counter() - t1

    # ------------------------------------------------------------------
    # 1. Constants, Exports, E2E Modes, Repeatability & Markdown
    # ------------------------------------------------------------------

    def test_01_constants_and_package_exports(self) -> None:
        self.assertEqual(REALHW_MILESTONE175_SCHEMA, "realhw_milestone175_master_gate_v1")
        self.assertEqual(MILESTONE175_SCHEMA_VERSION, REALHW_MILESTONE175_SCHEMA)
        self.assertEqual(PHASE_175_VERSION, "175.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertEqual(len(RECOVERY_22_PILLAR_IDS), 22)
        self.assertEqual(len(FIRMWARE_LAB_36_AUDITOR_KEYS), 36)
        self.assertEqual(len(VM_COEMULATION_30_STAGE_KEYS), 30)
        self.assertEqual(len(ROUND28_TO_34_SPECS), 7)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        self.assertEqual(CP_MUTATION_BYTES, 0)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(USB_OR_CAMERA_OPERATIONS, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertTrue(len(HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS) >= 1)
        self.assertIs(
            fx6_closure.build_realhw_milestone175_master_gate_report,
            build_realhw_milestone175_master_gate_report,
        )
        self.assertIs(
            fx6_closure.verify_realhw_milestone175_master_gate,
            verify_realhw_milestone175_master_gate,
        )
        self.assertEqual(fx6_closure.MILESTONE175_PILLAR_IDS, PILLAR_IDS)

    def test_02_clean_room_end_to_end_and_timing_budget(self) -> None:
        rep = self.report_clean
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready, msg=f"errors={rep.errors}")
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        ver = verify_realhw_milestone175_master_gate(rep)
        self.assertTrue(ver.valid, msg=f"verify errors={ver.errors}")
        self.assertLess(self.clean_elapsed_s, 30.0)

    def test_03_primary_mode_end_to_end_and_timing_budget(self) -> None:
        rep = self.report_primary
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if _is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.verification_mode, expected_mode)
        self.assertTrue(rep.all_pillars_milestone_ready, msg=f"errors={rep.errors}")
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertTrue(verify_realhw_milestone175_master_gate(rep).valid)
        self.assertLess(self.primary_elapsed_s, 30.0)

    def test_04_deterministic_repeatability_and_zero_raw_bytes_repr(self) -> None:
        rep_a = self.report_clean
        rep_b = build_realhw_milestone175_master_gate_report(synthetic_clean_room=True)
        self.assertEqual(rep_a.milestone175_sha256, rep_b.milestone175_sha256)
        self.assertEqual(rep_a.to_deterministic_json(), rep_b.to_deterministic_json())
        self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rep_a.to_deterministic_json()))

    def test_05_markdown_renderer_bilingual_highlights(self) -> None:
        md = render_milestone175_markdown(self.report_clean)
        for token in (
            "Milestone Phase 175",
            "MILESTONE_175_PREBENCH_MASTER_VERIFIED",
            "6/6",
            "persistent_emmc_writes_authorized = False",
            "spi_nor_write_authorized = False",
            "el3_payload_transmit_authorized = False",
            "hardware_live_attachment_authorized = False",
            "58-Gate Preflight",
            "Rounds 28..34",
            "Phase154 bench_go=True",
        ):
            self.assertIn(token, md)

    # ------------------------------------------------------------------
    # 2. Pillar 1 — 58-Gate Safety Master Preflight
    # ------------------------------------------------------------------

    def test_06_p1_nominal_58gate_offline_55_vs_sim_58_redlines(self) -> None:
        p1 = next(p for p in self.report_primary.pillars if p.pillar_id == "P1")
        self.assertTrue(p1.passed, msg=f"errors={p1.errors}")
        self.assertGreaterEqual(p1.evidence["total_gates"], 58)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 55)
        self.assertLess(p1.evidence["offline_verified_gates"], p1.evidence["total_gates"])
        self.assertEqual(p1.evidence["simulated_verified_gates"], p1.evidence["total_gates"])
        self.assertFalse(p1.evidence["offline_ready_for_hardware_attach"])
        self.assertFalse(p1.evidence["simulated_ready_for_hardware_attach"])
        self.assertFalse(p1.evidence["persistent_emmc_writes_authorized"])
        self.assertFalse(p1.evidence["spi_nor_write_authorized"])
        self.assertFalse(p1.evidence["el3_payload_transmit_authorized"])
        self.assertTrue(all(p1.evidence["nested_g45_to_g58_valid"].values()))

    def test_07_p1_fault_offline_all_58_or_sim_not_all_58_fails(self) -> None:
        raw_off_bad = _make_clean_p1_off()
        raw_off_bad["all_58_gates_verified"] = True
        raw_off_bad["overall_ready_for_hardware_attach"] = True
        p1_a = _evaluate_pillar_1(raw_off_bad, _make_clean_p1_sim())
        self.assertFalse(p1_a.passed)

        raw_sim_bad = _make_clean_p1_sim(total_gates=58, verified_gates=57)
        p1_b = _evaluate_pillar_1(_make_clean_p1_off(), raw_sim_bad)
        self.assertFalse(p1_b.passed)

    def test_08_p1_fault_nested_g45_to_g58_or_write_auth_breach(self) -> None:
        for gnum in (45, 51, 57, 58):
            sim = _make_clean_p1_sim()
            sim["nested_g45_to_g58_valid"][f"g{gnum}"] = False
            p1 = _evaluate_pillar_1(_make_clean_p1_off(), sim)
            self.assertFalse(p1.passed, msg=f"nested g{gnum}=False should fail")

        for redline_key, bad_val in (
            ("persistent_emmc_writes_authorized", True),
            ("persistent_write_release", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("agent_auto_flash_blocked", False),
        ):
            sim = _make_clean_p1_sim()
            sim[redline_key] = bad_val
            p1 = _evaluate_pillar_1(_make_clean_p1_off(), sim)
            self.assertFalse(p1.passed, msg=f"{redline_key}={bad_val} should fail")

    def test_09_p1_forward_compat_59_gates_passes(self) -> None:
        off = _make_clean_p1_off(total_gates=59, verified_gates=56)
        sim = _make_clean_p1_sim(total_gates=59, verified_gates=59)
        p1 = _evaluate_pillar_1(off, sim)
        self.assertTrue(p1.passed, msg=f"errors={p1.errors}")

    def test_10_p1_live_fault_request_persistent_writes_fails_closed(self) -> None:
        rep = build_realhw_milestone175_master_gate_report(
            synthetic_clean_room=True,
            faults=RealHwMilestone175FaultInjection(p1_request_persistent_writes=True),
        )
        self.assertFalse(rep.all_pillars_milestone_ready)
        self.assertEqual(rep.status, STATUS_FAIL_CLOSED)
        self.assertIn("P1", rep.failed_pillar_ids)
        self.assertFalse(verify_realhw_milestone175_master_gate(rep).valid)

    # ------------------------------------------------------------------
    # 3. Pillar 2 — >= 22-Pillar Recovery Vault & 5-Tier Escalation
    # ------------------------------------------------------------------

    def test_11_p2_nominal_22_recovery_pillars_and_zero_touch(self) -> None:
        p2 = next(p for p in self.report_primary.pillars if p.pillar_id == "P2")
        self.assertTrue(p2.passed, msg=f"errors={p2.errors}")
        self.assertGreaterEqual(p2.evidence["recovery_pillar_count"], 22)
        self.assertEqual(p2.evidence["recovery_pillars_passed"], p2.evidence["recovery_pillar_count"])
        for pid in RECOVERY_22_PILLAR_IDS:
            self.assertTrue(p2.evidence["pillar_statuses"].get(pid), msg=f"missing/failed {pid}")
        self.assertEqual(p2.evidence["otp_fuse_touches"], 0)
        self.assertEqual(p2.evidence["rpmb_counter_increments"], 0)
        self.assertEqual(p2.evidence["passive_tx_bytes_emitted"], 0)
        self.assertEqual(p2.evidence["physical_usb_packets_emitted"], 0)
        self.assertFalse(p2.evidence["el3_payload_transmit_authorized"])
        self.assertFalse(p2.evidence["isp_write_authorized"])

    def test_12_p2_fault_recovery_pillar_18_to_22_fails_closed(self) -> None:
        for idx, pid in enumerate(RECOVERY_22_PILLAR_IDS[17:], start=18):
            raw = _make_clean_p2_22pillar()
            raw["pillars"][idx - 1]["passed"] = False
            p2, _ = _evaluate_pillar_2(raw, RealHwMilestone175FaultInjection())
            self.assertFalse(p2.passed, msg=f"Pillar {pid} failure must fail P2 closed")

        raw_worker_fault = _worker_recovery_22pillar((True, MASTER_22_PILLAR_IDS[-1]))
        p2_w, _ = _evaluate_pillar_2(raw_worker_fault, RealHwMilestone175FaultInjection())
        self.assertFalse(p2_w.passed)

    def test_13_p2_fault_otp_rpmb_tx_usb_or_el3_write_auth_breach(self) -> None:
        for fault in (
            RealHwMilestone175FaultInjection(p2_otp_fuse_touches_override=1),
            RealHwMilestone175FaultInjection(p2_rpmb_increments_override=1),
            RealHwMilestone175FaultInjection(p2_passive_tx_bytes_override=1),
            RealHwMilestone175FaultInjection(p2_physical_usb_packets_override=1),
            RealHwMilestone175FaultInjection(p2_physical_device_writes_override=1),
            RealHwMilestone175FaultInjection(p2_raw_firmware_bytes_leaked_override=1),
        ):
            p2, _ = _evaluate_pillar_2(_make_clean_p2_22pillar(), fault)
            self.assertFalse(p2.passed)

        for key in (
            "el3_payload_transmit_authorized",
            "isp_write_authorized",
            "spi_nor_write_authorized",
            "persistent_emmc_writes_authorized",
            "live_usb_iokit_transmit_enabled",
        ):
            raw = _make_clean_p2_22pillar()
            raw[key] = True
            p2, _ = _evaluate_pillar_2(raw, RealHwMilestone175FaultInjection())
            self.assertFalse(p2.passed, msg=f"{key}=True must fail P2 closed")

    def test_14_p2_forward_compat_23_recovery_pillars(self) -> None:
        raw = _make_clean_p2_22pillar()
        raw["pillars"].append({"pillar_id": "future_pillar_23", "passed": True, "errors": ()})
        p2_ok, meta_ok = _evaluate_pillar_2(raw, RealHwMilestone175FaultInjection())
        self.assertTrue(p2_ok.passed, msg=f"errors={p2_ok.errors}")
        self.assertEqual(meta_ok["recovery_pillar_count"], 23)

        raw["pillars"][-1]["passed"] = False
        p2_bad, _ = _evaluate_pillar_2(raw, RealHwMilestone175FaultInjection())
        self.assertFalse(p2_bad.passed)

    # ------------------------------------------------------------------
    # 4. Pillar 3 — >= 36 Real-Binary Firmware-Lab Auditors
    # ------------------------------------------------------------------

    def test_15_p3_nominal_36_auditors_zero_cal_and_wbi_mutation(self) -> None:
        p3 = next(p for p in self.report_primary.pillars if p.pillar_id == "P3")
        self.assertTrue(p3.passed, msg=f"errors={p3.errors}")
        self.assertGreaterEqual(p3.evidence["auditor_count"], 36)
        self.assertEqual(p3.evidence["passed_auditor_count"], p3.evidence["auditor_count"])
        for ak in FIRMWARE_LAB_36_AUDITOR_KEYS:
            self.assertTrue(p3.evidence["auditor_statuses"].get(ak), msg=f"missing/failed {ak}")
        self.assertEqual(p3.evidence["calibration_mutation_bytes"], 0)
        self.assertEqual(p3.evidence["wbi2_hibdrv_mutation_bytes"], 0)
        self.assertEqual(p3.evidence["c2pa_cert_mutation_bytes"], 0)
        self.assertEqual(p3.evidence["cxd90058_sabin_mutation_bytes"], 0)

    def test_16_p3_fault_core_calibration_cp_and_mpr_bridge_regression(self) -> None:
        for fault in (
            RealHwMilestone175FaultInjection(p3_calibration_mutation_bytes=1),
            RealHwMilestone175FaultInjection(p3_realhw_cp_spi_mutation_bytes=1),
            RealHwMilestone175FaultInjection(p3_realhw_mpr_bridge_emmc_mutation_bytes=4),
        ):
            p3, _ = _evaluate_pillar_3(_make_clean_p3_36_auditors(), fault)
            self.assertFalse(p3.passed)

    def test_17_p3_fault_auditor29_peripheral_p18(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_36_auditors(),
            RealHwMilestone175FaultInjection(p3_peripheral_p18_emmc_mutation_bytes=1),
        )
        self.assertFalse(p3.passed)

        aud = _make_clean_p3_36_auditors()
        aud["realhw_lens_ibis_audio_hdmi_peripheral_bridge_audit"]["p18_lens_writes_permitted"] = True
        p3_b, _ = _evaluate_pillar_3(aud, RealHwMilestone175FaultInjection())
        self.assertFalse(p3_b.passed)

    def test_18_p3_fault_auditor30_controls_fan(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_36_auditors(),
            RealHwMilestone175FaultInjection(p3_controls_fan_emmc_mutation_bytes=1),
        )
        self.assertFalse(p3.passed)

    def test_19_p3_fault_auditor31_wifi_rfnvs(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_36_auditors(),
            RealHwMilestone175FaultInjection(p3_wifi_rfnvs_mutation_bytes=1),
        )
        self.assertFalse(p3.passed)

        aud = _make_clean_p3_36_auditors()
        aud["realhw_wifi_bt_usb_uvc_network_bridge_audit"]["rf_nvs_p12_p13_writes_permitted"] = True
        p3_b, _ = _evaluate_pillar_3(aud, RealHwMilestone175FaultInjection())
        self.assertFalse(p3_b.passed)

    def test_20_p3_fault_auditor32_imx510_sensor_cal(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_36_auditors(),
            RealHwMilestone175FaultInjection(p3_imx510_sensor_cal_mutation_bytes=1),
        )
        self.assertFalse(p3.passed)

        aud = _make_clean_p3_36_auditors()
        aud["realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_audit"]["sensor_cal_p2_writes_permitted"] = True
        p3_b, _ = _evaluate_pillar_3(aud, RealHwMilestone175FaultInjection())
        self.assertFalse(p3_b.passed)

    def test_21_p3_fault_auditor33_cfexpress_ufu(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_36_auditors(),
            RealHwMilestone175FaultInjection(p3_cfexpress_ufu_emmc_mutation_bytes=1),
        )
        self.assertFalse(p3.passed)

        aud = _make_clean_p3_36_auditors()
        aud["realhw_cfexpress_sdxc_exfat_rsv_ufu_coexistence_audit"]["spi_nor_write_authorized"] = True
        p3_b, _ = _evaluate_pillar_3(aud, RealHwMilestone175FaultInjection())
        self.assertFalse(p3_b.passed)

    def test_22_p3_fault_auditor34_cxd90058_sabin(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_36_auditors(),
            RealHwMilestone175FaultInjection(p3_cxd90058_sabin_mutation_bytes=1),
        )
        self.assertFalse(p3.passed)

    def test_23_p3_fault_auditor35_c2pa_tc_gyro(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_36_auditors(),
            RealHwMilestone175FaultInjection(p3_c2pa_cert_mutation_bytes=1),
        )
        self.assertFalse(p3.passed)

    def test_24_p3_fault_auditor36_wbi2_hibdrv(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_36_auditors(),
            RealHwMilestone175FaultInjection(p3_wbi2_hibdrv_mutation_bytes=1),
        )
        self.assertFalse(p3.passed)

        aud = _make_clean_p3_36_auditors()
        aud["realhw_wbi2_hibdrv_hibernation_isolation_audit"]["wbi_save_inhibited"] = False
        p3_b, _ = _evaluate_pillar_3(aud, RealHwMilestone175FaultInjection())
        self.assertFalse(p3_b.passed)

    def test_25_p3_forward_compat_37_auditors(self) -> None:
        aud = _make_clean_p3_36_auditors()
        aud["future_auditor_37"] = {"all_checks_passed": True, "report_sha256": "e" * 64}
        p3_ok, meta_ok = _evaluate_pillar_3(aud, RealHwMilestone175FaultInjection())
        self.assertTrue(p3_ok.passed, msg=f"errors={p3_ok.errors}")
        self.assertEqual(meta_ok["auditor_count"], 37)

        aud["future_auditor_37"] = {"all_checks_passed": False}
        p3_bad, _ = _evaluate_pillar_3(aud, RealHwMilestone175FaultInjection())
        self.assertFalse(p3_bad.passed)

    # ------------------------------------------------------------------
    # 5. Pillar 4 — >= 30-Stage VM HIL Co-Emulation
    # ------------------------------------------------------------------

    def test_26_p4_nominal_30_stages_zero_emmc_corruptions(self) -> None:
        p4 = next(p for p in self.report_primary.pillars if p.pillar_id == "P4")
        self.assertTrue(p4.passed, msg=f"errors={p4.errors}")
        self.assertGreaterEqual(p4.evidence["stage_count"], 30)
        self.assertEqual(p4.evidence["passed_stage_count"], p4.evidence["stage_count"])
        for sk in VM_COEMULATION_30_STAGE_KEYS:
            self.assertTrue(p4.evidence["stage_statuses"].get(sk), msg=f"missing/failed {sk}")
        self.assertEqual(p4.evidence["emmc_corruptions"], 0)
        self.assertEqual(p4.evidence["wf12_00342260_hits"], 0)

    def test_27_p4_fault_stage25_mpr_dmm_redlines(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_30_vm(),
            RealHwMilestone175FaultInjection(p4_stage25_emmc_mutation_bytes=1),
        )
        self.assertFalse(p4.passed)

        vm = _make_clean_p4_30_vm()
        vm["stage25_realhw_mpr_dmm_rec"]["rsv_orphan_count"] = 1
        p4_b, _ = _evaluate_pillar_4(vm, RealHwMilestone175FaultInjection())
        self.assertFalse(p4_b.passed)

    def test_28_p4_fault_stage26_body_peripheral_p18_redlines(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_30_vm(),
            RealHwMilestone175FaultInjection(p4_stage26_p18_mutation_bytes=1),
        )
        self.assertFalse(p4.passed)

        vm = _make_clean_p4_30_vm()
        vm["stage26_realhw_body_peripheral_hil"]["p18_lens_writes_permitted"] = True
        p4_b, _ = _evaluate_pillar_4(vm, RealHwMilestone175FaultInjection())
        self.assertFalse(p4_b.passed)

    def test_29_p4_fault_stage27_imx510_network_usb_redlines(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_30_vm(),
            RealHwMilestone175FaultInjection(p4_stage27_sensor_or_rfnvs_mutation_bytes=1),
        )
        self.assertFalse(p4.passed)

        for key, bad_val in (
            ("bt_hci_blocking_wait_eliminated", False),
            ("usb_msc_0da1_recovery_intact", False),
            ("psd_defdet_writes_permitted", True),
        ):
            vm = _make_clean_p4_30_vm()
            vm["stage27_realhw_imx510_network_usb_hil"][key] = bad_val
            p4_b, _ = _evaluate_pillar_4(vm, RealHwMilestone175FaultInjection())
            self.assertFalse(p4_b.passed, msg=f"Stage 27 {key}={bad_val} must fail")

    def test_30_p4_fault_stage28_cfexpress_ufu_5tier_redlines(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_30_vm(),
            RealHwMilestone175FaultInjection(p4_stage28_spi_or_emmc_mutation_bytes=1),
        )
        self.assertFalse(p4.passed)

        for key, bad_val in (
            ("el3_payload_transmit_authorized", True),
            ("spi_nor_write_authorized", True),
            ("user_media_clips_intact", False),
        ):
            vm = _make_clean_p4_30_vm()
            vm["stage28_realhw_cfexpress_ufu_5tier_hil"][key] = bad_val
            p4_b, _ = _evaluate_pillar_4(vm, RealHwMilestone175FaultInjection())
            self.assertFalse(p4_b.passed)

    def test_31_p4_fault_stage29_cxd90058_sabin_seal_redlines(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_30_vm(),
            RealHwMilestone175FaultInjection(p4_stage29_cxd90058_or_residual_count=1),
        )
        self.assertFalse(p4.passed)

        vm = _make_clean_p4_30_vm()
        vm["stage29_realhw_cxd90058_sabin_seal_hil"]["orig_residual_count"] = 1
        p4_b, _ = _evaluate_pillar_4(vm, RealHwMilestone175FaultInjection())
        self.assertFalse(p4_b.passed)

    def test_32_p4_fault_stage30_c2pa_tc_gyro_voltage_redlines(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_30_vm(),
            RealHwMilestone175FaultInjection(p4_stage30_c2pa_or_voltage_events=1),
        )
        self.assertFalse(p4.passed)

        vm = _make_clean_p4_30_vm()
        vm["stage30_realhw_c2pa_tc_gyro_prebench_hil"]["over_voltage_damage_events"] = 1
        p4_b, _ = _evaluate_pillar_4(vm, RealHwMilestone175FaultInjection())
        self.assertFalse(p4_b.passed)

    def test_33_p4_forward_compat_31_vm_stages(self) -> None:
        vm = _make_clean_p4_30_vm()
        vm["stage31_future_realhw_hil"] = {"all_checks_passed": True}
        p4_ok, meta_ok = _evaluate_pillar_4(vm, RealHwMilestone175FaultInjection())
        self.assertTrue(p4_ok.passed, msg=f"errors={p4_ok.errors}")
        self.assertEqual(meta_ok["stage_count"], 31)

        vm["stage31_future_realhw_hil"] = {"all_checks_passed": False}
        p4_bad, _ = _evaluate_pillar_4(vm, RealHwMilestone175FaultInjection())
        self.assertFalse(p4_bad.passed)

    # ------------------------------------------------------------------
    # 6. Pillar 5 — Closure Ph136 (U4/U5/U6) + Ph143 (BYOF SD & H0==H3) + Ph154
    # ------------------------------------------------------------------

    def test_34_p5_nominal_p136_p143_and_p154_bench_preflight(self) -> None:
        p5 = next(p for p in self.report_primary.pillars if p.pillar_id == "P5")
        self.assertTrue(p5.passed, msg=f"errors={p5.errors}")
        self.assertGreaterEqual(p5.evidence["p136_u6_command_count"], 19)
        self.assertTrue(p5.evidence["p136_u4_u5_u6_closed"])
        self.assertLessEqual(p5.evidence["p143_eh1_observed_latency_us"], 50)
        self.assertEqual(p5.evidence["p143_h0_equals_h3_count"], 16)
        self.assertEqual(p5.evidence["p143_h0_h3_surface_count"], 16)
        self.assertGreaterEqual(p5.evidence["p143_power_loss_drills_passed"], 5)
        self.assertTrue(p5.evidence["p154_bench_go"])
        self.assertEqual(p5.evidence["p154_usb_packets_emitted"], 0)
        self.assertEqual(p5.evidence["p154_iokit_handles_opened"], 0)

    def test_35_p5_fault_p136_u4_u5_u6(self) -> None:
        raw_p136 = _worker_phase136(True)
        raw_p143, raw_p154 = _worker_phase143_and_154(
            (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, True)
        )
        p5, _ = _evaluate_pillar_5(
            raw_p136,
            raw_p143,
            raw_p154,
            RealHwMilestone175FaultInjection(p5_inject_p136_u4_u5_u6_fault=True),
        )
        self.assertFalse(p5.passed)

    def test_36_p5_fault_p143_eh1_over_50us_or_h0_h3_drift(self) -> None:
        raw_p136 = _worker_phase136(True)
        raw_p143, raw_p154 = _worker_phase143_and_154(
            (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, True)
        )
        p5_a, _ = _evaluate_pillar_5(
            raw_p136,
            raw_p143,
            raw_p154,
            RealHwMilestone175FaultInjection(p5_inject_p143_escape_hatch_over_budget_us=10),
        )
        self.assertFalse(p5_a.passed)

        p5_b, _ = _evaluate_pillar_5(
            raw_p136,
            raw_p143,
            raw_p154,
            RealHwMilestone175FaultInjection(p5_inject_p143_h0_h3_drift=True),
        )
        self.assertFalse(p5_b.passed)

    def test_37_p5_fault_p154_no_go_or_usb_packets_nonzero(self) -> None:
        raw_p136 = _worker_phase136(True)
        raw_p143, raw_p154_nogo = _worker_phase143_and_154(
            (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, False)
        )
        p5_nogo, _ = _evaluate_pillar_5(
            raw_p136,
            raw_p143,
            raw_p154_nogo,
            RealHwMilestone175FaultInjection(p5_inject_p154_no_go_fault=True),
        )
        self.assertFalse(p5_nogo.passed)

        _, raw_p154_go = _worker_phase143_and_154(
            (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, True)
        )
        p5_pkt, _ = _evaluate_pillar_5(
            raw_p136,
            raw_p143,
            raw_p154_go,
            RealHwMilestone175FaultInjection(p5_inject_p154_usb_packets_override=1),
        )
        self.assertFalse(p5_pkt.passed)

    # ------------------------------------------------------------------
    # 7. Pillar 6 — Live FX3 7.02 Kernel QEMU Rounds 28..34 Receipts (21/21)
    # ------------------------------------------------------------------

    def test_38_p6_committed_rounds_28_to_34_receipts_o_rdonly(self) -> None:
        for spec in ROUND28_TO_34_SPECS:
            data, src = _load_round28_to_34_summary(spec, repo_root=REPO_ROOT, use_clean_room=False)
            self.assertEqual(src, "REPO_SUMMARY_O_RDONLY")
            self.assertEqual(data["schema"], spec.expected_schema)
            self.assertIn("4.9.337-scel+", data["kernel_version"])
            self.assertEqual(len(spec.run_specs), 3)

    def test_39_p6_clean_room_fallback_all_7_rounds_when_reports_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p6, meta6 = _evaluate_pillar_6(
                repo_root=Path(tmp),
                use_clean_room=True,
                faults=RealHwMilestone175FaultInjection(),
                p1_meta={
                    "persistent_emmc_writes_authorized": False,
                    "spi_nor_write_authorized": False,
                    "el3_payload_transmit_authorized": False,
                    "simulated_ready_for_hardware_attach": False,
                },
                p2_meta={
                    "otp_fuse_touches": 0,
                    "rpmb_counter_increments": 0,
                    "passive_tx_bytes_emitted": 0,
                    "physical_usb_packets_emitted": 0,
                },
                p3_meta={"calibration_mutation_bytes": 0, "wbi_mutation_bytes": 0},
                p4_meta={
                    "cp_mutation_bytes": 0,
                    "bk4_persistent_nvram_writes": 0,
                    "wf12_00342260_hits": 0,
                    "emmc_corruptions": 0,
                },
                p5_meta={
                    "h0_equals_h3_count": 16,
                    "p154_bench_go": True,
                    "p154_usb_packets_emitted": 0,
                },
            )
        self.assertTrue(p6.passed, msg=f"errors={p6.errors}")
        self.assertEqual(meta6["qemu_rounds_verified"], 7)
        self.assertEqual(meta6["qemu_runs_verified"], 21)
        for rnum in range(28, 35):
            self.assertEqual(p6.evidence["round_sources"][f"r{rnum}"], "CLEAN_ROOM_SYNTHETIC")

    def test_40_p6_missing_reports_without_clean_room_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for spec in ROUND28_TO_34_SPECS:
                with self.assertRaises(FileNotFoundError):
                    _load_round28_to_34_summary(spec, repo_root=Path(tmp), use_clean_room=False)

    def test_41_p6_fault_rounds_28_to_34_nop_crash_emmc_or_schema_tamper(self) -> None:
        base_kw = dict(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            p1_meta={
                "persistent_emmc_writes_authorized": False,
                "spi_nor_write_authorized": False,
                "el3_payload_transmit_authorized": False,
                "simulated_ready_for_hardware_attach": False,
            },
            p2_meta={
                "otp_fuse_touches": 0,
                "rpmb_counter_increments": 0,
                "passive_tx_bytes_emitted": 0,
                "physical_usb_packets_emitted": 0,
            },
            p3_meta={"calibration_mutation_bytes": 0, "wbi_mutation_bytes": 0},
            p4_meta={
                "cp_mutation_bytes": 0,
                "bk4_persistent_nvram_writes": 0,
                "wf12_00342260_hits": 0,
                "emmc_corruptions": 0,
            },
            p5_meta={
                "h0_equals_h3_count": 16,
                "p154_bench_go": True,
                "p154_usb_packets_emitted": 0,
            },
        )
        for rnum in (28, 29, 30, 31, 32, 33, 34):
            for fault in (
                RealHwMilestone175FaultInjection(
                    p6_round_nop_override_num=rnum, p6_round_nop_count_override=1
                ),
                RealHwMilestone175FaultInjection(
                    p6_round_crash_override_num=rnum, p6_round_crashes_override=1
                ),
                RealHwMilestone175FaultInjection(
                    p6_round_emmc_override_num=rnum, p6_round_emmc_writes_override=1
                ),
                RealHwMilestone175FaultInjection(p6_tamper_schema_round_num=rnum),
            ):
                p6, _ = _evaluate_pillar_6(faults=fault, **base_kw)
                self.assertFalse(p6.passed, msg=f"Round {rnum} fault {fault} must fail P6 closed")

    def test_42_p6_cross_pillar_redline_breach_rejected(self) -> None:
        clean_args = dict(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone175FaultInjection(),
            p1_meta={
                "persistent_emmc_writes_authorized": False,
                "spi_nor_write_authorized": False,
                "el3_payload_transmit_authorized": False,
                "simulated_ready_for_hardware_attach": False,
            },
            p2_meta={
                "otp_fuse_touches": 0,
                "rpmb_counter_increments": 0,
                "passive_tx_bytes_emitted": 0,
                "physical_usb_packets_emitted": 0,
            },
            p3_meta={"calibration_mutation_bytes": 0, "wbi_mutation_bytes": 0},
            p4_meta={
                "cp_mutation_bytes": 0,
                "bk4_persistent_nvram_writes": 0,
                "wf12_00342260_hits": 0,
                "emmc_corruptions": 0,
            },
            p5_meta={
                "h0_equals_h3_count": 16,
                "p154_bench_go": True,
                "p154_usb_packets_emitted": 0,
            },
        )
        for block, key, val in (
            ("p1_meta", "el3_payload_transmit_authorized", True),
            ("p2_meta", "physical_usb_packets_emitted", 1),
            ("p3_meta", "wbi_mutation_bytes", 1),
            ("p4_meta", "emmc_corruptions", 1),
            ("p5_meta", "p154_bench_go", False),
        ):
            kw = copy.deepcopy(clean_args)
            kw[block][key] = val
            p6, _ = _evaluate_pillar_6(**kw)
            self.assertFalse(p6.passed, msg=f"Breached {block}[{key}]={val} must fail P6")

    # ------------------------------------------------------------------
    # 8. Tamper-Evident Verifier & CLI Subcommand Tests
    # ------------------------------------------------------------------

    def test_43_verifier_rejects_non_mapping_bad_schema_and_tampered_sha256(self) -> None:
        res_bad_type = verify_realhw_milestone175_master_gate(["not", "a", "dict"])
        self.assertFalse(res_bad_type.valid)

        d = self.report_clean.to_dict()
        d["schema_version"] = "wrong-schema"
        d["milestone175_sha256"] = compute_milestone175_sha256(d)
        res_bad_schema = verify_realhw_milestone175_master_gate(d)
        self.assertFalse(res_bad_schema.valid)
        self.assertFalse(res_bad_schema.schema_ok)

        d2 = self.report_clean.to_dict()
        d2["qemu_runs_verified"] = 20
        res_mut = verify_realhw_milestone175_master_gate(d2)
        self.assertFalse(res_mut.valid)
        self.assertFalse(res_mut.digest_matched)

    def test_44_verifier_rejects_all_breached_hardware_redlines(self) -> None:
        for key, bad_val in (
            ("persistent_emmc_writes_authorized", True),
            ("persistent_write_release", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("isp_write_authorized", True),
            ("hardware_live_attachment_authorized", True),
            ("physical_usb_packets_emitted", 1),
            ("otp_fuse_touches", 1),
            ("rpmb_counter_increments", 1),
            ("passive_tx_bytes_emitted", 1),
            ("p154_usb_packets_emitted", 1),
            ("p154_iokit_handles_opened", 1),
        ):
            d = copy.deepcopy(self.report_clean.to_dict())
            d[key] = bad_val
            d["milestone175_sha256"] = compute_milestone175_sha256(d)
            res = verify_realhw_milestone175_master_gate(d)
            self.assertFalse(res.valid, msg=f"Should reject breached {key}={bad_val}")
            self.assertFalse(res.safety_redlines_ok)

    def test_45_verifier_forward_compat_and_below_threshold_counts(self) -> None:
        d_high = copy.deepcopy(self.report_clean.to_dict())
        d_high["gate58_total_gates"] = 60
        d_high["gate58_offline_verified"] = 57
        d_high["gate58_simulated_verified"] = 60
        d_high["recovery_pillar_count"] = 23
        d_high["recovery_pillars_passed"] = 23
        d_high["firmware_lab_auditor_count"] = 37
        d_high["firmware_lab_auditors_passed"] = 37
        d_high["vm_coemulation_stage_count"] = 31
        d_high["vm_coemulation_stages_passed"] = 31
        d_high["milestone175_sha256"] = compute_milestone175_sha256(d_high)
        res_high = verify_realhw_milestone175_master_gate(d_high)
        self.assertTrue(res_high.valid, msg=f"errors={res_high.errors}")

        for key, bad_val in (
            ("gate58_total_gates", 57),
            ("gate58_offline_verified", 54),
            ("recovery_pillar_count", 21),
            ("firmware_lab_auditor_count", 35),
            ("vm_coemulation_stage_count", 29),
            ("qemu_rounds_verified", 6),
            ("qemu_runs_verified", 20),
        ):
            d_low = copy.deepcopy(self.report_clean.to_dict())
            d_low[key] = bad_val
            d_low["milestone175_sha256"] = compute_milestone175_sha256(d_low)
            res_low = verify_realhw_milestone175_master_gate(d_low)
            self.assertFalse(res_low.valid, msg=f"Should fail below-threshold {key}={bad_val}")

    def test_46_verifier_rejects_raw_bytes_repr_in_serialized_payload(self) -> None:
        d = copy.deepcopy(self.report_clean.to_dict())
        d["errors"] = ["leaked b'rawbytes' repr"]
        d["milestone175_sha256"] = compute_milestone175_sha256(d)
        res = verify_realhw_milestone175_master_gate(d)
        self.assertFalse(res.valid)

    def test_47_cli_clean_room_json_output_and_markdown_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "m175.json"
            md_path = Path(tmp) / "m175.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-175",
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
            self.assertEqual(parsed["schema_version"], REALHW_MILESTONE175_SCHEMA)
            self.assertTrue(verify_realhw_milestone175_master_gate(parsed).valid)
            self.assertIn("MILESTONE_175_PREBENCH_MASTER_VERIFIED", md_path.read_text(encoding="utf-8"))

    def test_48_cli_clean_room_human_summary_line(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = fx6_cli_main(["verify-milestone-175", "--clean-room"])
        self.assertEqual(rc, 0)
        line = buf.getvalue().strip()
        for token in (
            "status=OK",
            "schema=realhw_milestone175_master_gate_v1",
            "pillars=6/6",
            "otp=0",
            "rpmb=0",
            "passive_tx=0",
            "h0_eq_h3=16/16",
            "p154_go=True",
            "qemu=7/7(21/21)",
            "emmc_writes_auth=False",
            "spi_nor_auth=False",
            "el3_tx_auth=False",
            "usb_tx=0",
        ):
            self.assertIn(token, line)


if __name__ == "__main__":
    unittest.main()
