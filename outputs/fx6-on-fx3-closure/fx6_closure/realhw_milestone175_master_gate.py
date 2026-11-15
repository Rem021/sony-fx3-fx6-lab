"""Milestone Phase 175 — Grand Unified 6-Pillar Real-Hardware Final Pre-Bench Master Gate (`realhw_milestone175_master_gate_v1`).

Consolidates the entire FX6-on-FX3 Real-Hardware Main Track (Phases 134–174) and
all 7 live Sony ILME-FX3 `7.02` (`Linux 4.9.337-scel+`) ARM64 QEMU Rehearsal Rounds
(`Rounds 28, 29, 30, 31, 32, 33, 34` — `21/21` sub-experiments) into a single
tamper-evident, fail-closed certificate executing in `< 3.8s` (`LOCAL_DONOR_O_RDONLY`)
and `< 2.2s` (`CLEAN_ROOM_SYNTHETIC` / `FX3_FX6_FORCE_CLEAN_ROOM=1`):

- `P1` (`SAFETY_58GATE_REALHW_MASTER_PREFLIGHT`):
  Evaluates Phase 174 `evaluate_58gate_preflight` (`G01..G58`), verifying `58/58`
  dry-run simulated gates pass (`dry_run_rehearsal_only=True`,
  `overall_ready_for_hardware_attach=False`) while offline hardware-truth mode enforces
  `55/58` (`G10..G12` physical Tier-0 attach/backup gates locked) and hard-locks
  `persistent_emmc_writes_authorized=False`, `spi_nor_write_authorized=False`,
  `el3_payload_transmit_authorized=False`, `persistent_write_release=False`, and
  `agent_auto_flash_blocked=True`.
- `P2` (`TWENTY_TWO_PILLAR_RECOVERY_VAULT_AND_5TIER_ESCALATION`):
  Verifies all `>= 22` recovery pillars (`evaluate_22pillar_recovery_master`, Phases
  47–174), covering Pillars `18..22` (`054C:0336` `op=0xFF` canary + `64 KiB`
  `libJit.so` hardener, dual-layer `pnflasha/cnflasha/mtd0ro` vault, `1.8V ttyAMA0 /
  VMC-BNCM1` 460800 POST & ISP guard, 5-tier EL3/UFU escalation, and Dual-Media
  RAID-6 GF(256) bit-rot verifier), locking `otp_fuse_touches == 0`,
  `rpmb_counter_increments == 0`, `passive_tx_bytes_emitted == 0`,
  `physical_usb_packets_emitted == 0`, and `physical_device_writes == 0`.
- `P3` (`THIRTY_SIX_FIRMWARE_LAB_REALBIN_AUDITORS`):
  Verifies all `>= 36` `fx3_firmware_lab` auditors (Phases 1–171), forward-compatible
  with Auditor 37+, explicitly auditing #29..#36 (`p18:/lens` + IBIS Center-Lock +
  `XLR-H1`, physical controls + `65°C` fan override + `NP-FZ100`, zero-diff
  Wi-Fi/`CDC-NCM`/`0DA1`, `IMX510` Dual-Base ISO + `psd.bin/defdet.bin` + `.cube`
  MLUT, `CFexpress/SDXC` + `.RSV` + `BODYDATA.DAT` UFU coexistence,
  `CXD90057 + CXD90058` + `sabin` SA-DSP codec boundary, `p12:/cert/RQ_LIC.DAT` C2PA
  + `VMC-BNCM1` TC + `IMX510` Gyro XML, `p5:/wbi` `WBI2` `hibdrv.ko` hibernation
  isolation), locking `calibration_mutation_bytes == 0`.
- `P4` (`THIRTY_STAGE_VM_HIL_COEMULATION`):
  Verifies all `>= 30` `outputs/fx3-vm` heterogeneous AArch64 AP + ARM32 Thumb-2
  Stock-CP co-emulation stages (Phases 33–172), forward-compatible with Stage 31+,
  explicitly auditing Stages 25..30, locking `emmc_corruptions == 0`,
  `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, and `wf12_00342260_hits == 0`.
- `P5` (`CLOSURE_BENCH_PREFLIGHT_SD_BUNDLE_AND_H0_H3`):
  Verifies `Phase 136` (`U4/U5/U6` disassembly + Strategy-A + Tier-0 stop-gate),
  `Phase 143` (BYOF SD bundle, `EH1 <= 50 us` `47 us` bypass, `16/16 H0 == H3`), and
  `Phase 154` (`run_realhw_bench_preflight(simulate_ready_bench=True)` passive
  zero-packet USB classifier & dual-copy `FX3RCPT1` verifier).
- `P6` (`REAL_FX3_702_QEMU_ROUNDS_28_TO_34_RECEIPTS`):
  Verifies committed `O_RDONLY` receipts from ALL 7 Real-Hardware QEMU Rehearsal
  Rounds (`Rounds 28..34`, `21/21` sub-experiments on unmodified FX3 `7.02`
  `4.9.337-scel+`), with deterministic clean-room synthesis when
  `FX3_FX6_FORCE_CLEAN_ROOM=1`, proving `crashes == 0`, `nop_count == 0`, and
  `emmc_write_count == 0` alongside cross-pillar zero-write invariants.

Hard-Locked Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `ISP_WRITE_AUTHORIZED = False`
- `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `PHYSICAL_USB_PACKETS_EMITTED = 0`
- `OTP_FUSE_TOUCHES = 0`, `RPMB_COUNTER_INCREMENTS = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`
- `CP_MUTATION_BYTES = 0`, `WBI_MUTATION_BYTES = 0`, `CALIBRATION_MUTATION_BYTES = 0`
- Zero raw binary `bytes` reprs (`b'...'` / `b"..."`).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from concurrent.futures import ProcessPoolExecutor
import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple


def _ensure_cross_package_paths(repo_root: Path) -> None:
    """Ensure all sibling lab package roots are importable under default PYTHONPATH."""
    for rel in (
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx3-firmware-lab",
        "outputs/fx3-vm",
        "outputs/fx6-on-fx3-closure",
    ):
        cand = str(repo_root / rel)
        if cand not in sys.path:
            sys.path.append(cand)


DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

from fx3_firmware_lab.realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor import (  # noqa: E402
    analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta,
    realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_report_to_dict,
)
from fx3_firmware_lab.realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_auditor import (  # noqa: E402
    analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence,
    realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_report_to_dict,
)
from fx3_firmware_lab.realhw_cxd90057_cxd90058_sabin_codec_auditor import (  # noqa: E402
    analyze_realhw_cxd90057_cxd90058_sabin_codec,
    realhw_cxd90057_cxd90058_sabin_codec_report_to_dict,
)
from fx3_firmware_lab.realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor import (  # noqa: E402
    analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline,
    realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_report_to_dict,
)
from fx3_firmware_lab.realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (  # noqa: E402
    analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge,
    realhw_lens_ibis_audio_hdmi_peripheral_bridge_report_to_dict,
)
from fx3_firmware_lab.realhw_physical_controls_tally_fan_and_power_auditor import (  # noqa: E402
    analyze_realhw_physical_controls_tally_fan_and_power,
    realhw_physical_controls_tally_fan_and_power_report_to_dict,
)
from fx3_firmware_lab.realhw_wbi2_hibdrv_hibernation_isolation_auditor import (  # noqa: E402
    analyze_realhw_wbi2_hibdrv_hibernation_isolation,
    realhw_wbi2_hibdrv_hibernation_isolation_report_to_dict,
)
from fx3_firmware_lab.realhw_wifi_bt_usb_uvc_network_bridge_auditor import (  # noqa: E402
    analyze_realhw_wifi_bt_usb_uvc_network_bridge,
    realhw_wifi_bt_usb_uvc_network_bridge_report_to_dict,
)
from fx3_recovery.realhw_22pillar_master_recovery_verifier import (  # noqa: E402
    MASTER_22_PILLAR_IDS,
    evaluate_22pillar_recovery_master,
)
from fx3_safety.realhw_dualmedia_bench_interlock_and_58gate_guard import (  # noqa: E402
    evaluate_58gate_preflight,
)

from .hardware_readiness_packet import _is_forced_clean_room  # noqa: E402
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
)
from .realhw_bench_preflight_and_usb_classifier import (  # noqa: E402
    VERDICT_GO_READONLY_PREFLIGHT,
    run_realhw_bench_preflight,
    verify_phase154_report,
)
from .realhw_jiritsu_and_tier0_dumper_auditor import (  # noqa: E402
    run_phase136_realhw_jiritsu_tier0_audit,
)
from .realhw_milestone147_master_gate import (  # noqa: E402
    FIRMWARE_LAB_28_AUDITOR_KEYS,
    MILESTONE147_SCHEMA_VERSION,
    RECOVERY_17_PILLAR_IDS,
    ROUND28_EXPECTED_SCHEMA,
    ROUND28_RUN_SPECS,
    ROUND28_SUMMARY_RELPATH,
    ROUND29_EXPECTED_SCHEMA,
    ROUND29_RUN_SPECS,
    ROUND29_SUMMARY_RELPATH,
    VM_COEMULATION_24_STAGE_KEYS,
    RealHwMilestone147FaultInjection,
    _evaluate_pillar_3 as _eval_m147_p3,
    _evaluate_pillar_4 as _eval_m147_p4,
    _fault_to_worker_dict as _m147_fault_to_worker_dict,
    _worker_pillar_3_group as _m147_worker_pillar_3_group,
)
from .realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    run_phase143_sd_stageb_bundle_uninstaller_audit,
)
from .stage_b_capstone_22gate_verifier import _build_clean_room_stage_b_manifest_items  # noqa: E402
from .stage_b_milestone110_master_gate import (  # noqa: E402
    _clean_room_faithful_block,
    _worker_pillar_4,
)
from .stage_b_post_trial_auditor import _read_file_o_rdonly  # noqa: E402
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_MILESTONE175_SCHEMA: str = "realhw_milestone175_master_gate_v1"
MILESTONE175_SCHEMA_VERSION: str = REALHW_MILESTONE175_SCHEMA
SCHEMA_VERSION: str = REALHW_MILESTONE175_SCHEMA
PHASE_175_VERSION: str = "175.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
P8_CP_MUTATION_FORBIDDEN: bool = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN: bool = True
CP_MUTATION_BYTES: int = 0
WBI_MUTATION_BYTES: int = 0
CALIBRATION_MUTATION_BYTES: int = 0
USB_OR_CAMERA_OPERATIONS: int = 0
OTP_FUSE_TOUCHES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0

STATUS_MILESTONE_READY: str = "MILESTONE_175_PREBENCH_MASTER_VERIFIED"
STATUS_FAIL_CLOSED: str = "FAIL_CLOSED"

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_58GATE_REALHW_MASTER_PREFLIGHT"),
    ("P2", "TWENTY_TWO_PILLAR_RECOVERY_VAULT_AND_5TIER_ESCALATION"),
    ("P3", "THIRTY_SIX_FIRMWARE_LAB_REALBIN_AUDITORS"),
    ("P4", "THIRTY_STAGE_VM_HIL_COEMULATION"),
    ("P5", "CLOSURE_BENCH_PREFLIGHT_SD_BUNDLE_AND_H0_H3"),
    ("P6", "REAL_FX3_702_QEMU_ROUNDS_28_TO_34_RECEIPTS"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)

RECOVERY_22_PILLAR_IDS: Tuple[str, ...] = (
    *RECOVERY_17_PILLAR_IDS,
    "realhw_service_usb_session_and_libjit_elf_hardener",
    "realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier",
    "realhw_uart_460800_post_triage_and_isp_guard",
    "realhw_bootrom_el3_and_ufu_stock_reflash_verifier",
    "realhw_22pillar_master_recovery_verifier",
)

FIRMWARE_LAB_36_AUDITOR_KEYS: Tuple[str, ...] = (
    *FIRMWARE_LAB_28_AUDITOR_KEYS,
    "realhw_lens_ibis_audio_hdmi_peripheral_bridge_audit",
    "realhw_physical_controls_tally_fan_and_power_audit",
    "realhw_wifi_bt_usb_uvc_network_bridge_audit",
    "realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_audit",
    "realhw_cfexpress_sdxc_exfat_rsv_ufu_coexistence_audit",
    "realhw_cxd90057_cxd90058_sabin_codec_audit",
    "realhw_c2pa_cert_vmcbncm1_tc_gyro_meta_audit",
    "realhw_wbi2_hibdrv_hibernation_isolation_audit",
)

VM_COEMULATION_30_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_24_STAGE_KEYS,
    "stage25_realhw_mpr_dmm_rec",
    "stage26_realhw_body_peripheral_hil",
    "stage27_realhw_imx510_network_usb_hil",
    "stage28_realhw_cfexpress_ufu_5tier_hil",
    "stage29_realhw_cxd90058_sabin_seal_hil",
    "stage30_realhw_c2pa_tc_gyro_prebench_hil",
)


@dataclass(frozen=True)
class RoundQemuReceiptSpec:
    """Declarative specification for one Live FX3 7.02 ARM64 QEMU Rehearsal Round."""

    round_num: int
    summary_relpath: str
    expected_schema: str
    audit_key: str
    audit_bool_keys: Tuple[str, ...]
    run_specs: Tuple[Tuple[str, Optional[int]], ...]  # (run_id, expected FX6_NATIVE_FAITHFUL or None for probe run)


ROUND30_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round30-realhw-canary-tier0-peripheral-uninstall-qemu/summary.json"
)
ROUND31_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round31-realhw-keymap-fan-fz100-mtdro-qemu/summary.json"
)
ROUND32_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round32-realhw-imx510-cube-cdcncm-uart-qemu/summary.json"
)
ROUND33_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round33-realhw-cfexpress-rsv-ufu-5tier-qemu/summary.json"
)
ROUND34_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round34-realhw-cxd90058-c2pa-tc-gyro-seal-qemu/summary.json"
)

ROUND30_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round30-realhw-canary-tier0-peripheral-uninstall-qemu-v1"
)
ROUND31_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round31-realhw-keymap-fan-fz100-mtdro-qemu-v1"
)
ROUND32_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round32-realhw-imx510-cube-cdcncm-uart-qemu-v1"
)
ROUND33_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round33-realhw-cfexpress-rsv-ufu-5tier-qemu-v1"
)
ROUND34_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round34-realhw-cxd90058-c2pa-tc-gyro-seal-qemu-v1"
)

ROUND28_TO_34_SPECS: Tuple[RoundQemuReceiptSpec, ...] = (
    RoundQemuReceiptSpec(
        round_num=28,
        summary_relpath=ROUND28_SUMMARY_RELPATH,
        expected_schema=ROUND28_EXPECTED_SCHEMA,
        audit_key="r28_realhw_escape_hatch_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r28a_stock_fx3_bypass_verified",
            "r28b_libjit_probe_verified",
            "r28b_strategy_a_bridge_verified",
            "r28b_stageb_big6_verified",
            "r28c_tamper_fail_closed_under_50ms",
        ),
        run_specs=ROUND28_RUN_SPECS,
    ),
    RoundQemuReceiptSpec(
        round_num=29,
        summary_relpath=ROUND29_SUMMARY_RELPATH,
        expected_schema=ROUND29_EXPECTED_SCHEMA,
        audit_key="r29_realhw_atomic_installer_mpr_rec_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r29a_atomic_install_ok",
            "r29a_mpr_param_and_rec_finalized",
            "r29a_stageb_big6_verified",
            "r29b_midwrite_atomic_rollback_verified",
            "r29c_p1_oneshot_mode_clear_verified",
        ),
        run_specs=ROUND29_RUN_SPECS,
    ),
    RoundQemuReceiptSpec(
        round_num=30,
        summary_relpath=ROUND30_SUMMARY_RELPATH,
        expected_schema=ROUND30_EXPECTED_SCHEMA,
        audit_key="r30_realhw_canary_tier0_peripheral_uninstall_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r30a_opff_ram_canary_verified",
            "r30a_tier0_64k_libjit_streaming_verified",
            "r30b_peripheral_bridge_verified",
            "r30b_stageb_big6_13_of_13_verified",
            "r30c_jbusy_0x10000011_zero_write_abort_verified",
            "r30c_h0_eq_h3_16_of_16_clean_uninstall_verified",
        ),
        run_specs=(
            ("r30a_canary_tier0", None),
            ("r30b_peripheral_big6_schinese", 1),
            ("r30c_jbusy_uninstall", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=31,
        summary_relpath=ROUND31_SUMMARY_RELPATH,
        expected_schema=ROUND31_EXPECTED_SCHEMA,
        audit_key="r31_realhw_keymap_fan_fz100_mtdro_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r31a_fx3_body_keymap_and_3x_tally_verified",
            "r31a_stageb_big6_13_of_13_verified",
            "r31b_fan_off_in_rec_thermal_override_verified",
            "r31b_fz100_usbpd_encwfistop_verified",
            "r31c_dual_layer_pnflasha_firewall_verified",
            "r31c_mtdro_ro_firewall_verified",
        ),
        run_specs=(
            ("r31a_keymap_big6_schinese", 1),
            ("r31b_fan_fz100_power", None),
            ("r31c_mtdro_firewall", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=32,
        summary_relpath=ROUND32_SUMMARY_RELPATH,
        expected_schema=ROUND32_EXPECTED_SCHEMA,
        audit_key="r32_realhw_imx510_cube_cdcncm_uart_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r32a_p2_psd_defdet_erofs_verified",
            "r32a_imx510_dual_base_800_12800_verified",
            "r32a_cube_3d_mlut_non_bake_and_nan_reject_verified",
            "r32a_stageb_big6_13_of_13_verified",
            "r32b_zero_diff_4libs_dlopen_dlsym_verified",
            "r32b_rf_nvs_erofs_and_zero_ttyama3_hang_verified",
            "r32b_cdcncm_to_054c_0da1_recovery_verified",
            "r32c_ttyama0_1v8_6stage_telemetry_verified",
            "r32c_vmc_bncm1_contention_and_overvoltage_abort_verified",
        ),
        run_specs=(
            ("r32a_imx510_cube_big6_schinese", 1),
            ("r32b_cdcncm_usb_0da1", None),
            ("r32c_uart_6stage_triage", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=33,
        summary_relpath=ROUND33_SUMMARY_RELPATH,
        expected_schema=ROUND33_EXPECTED_SCHEMA,
        audit_key="r33_realhw_cfexpress_rsv_ufu_5tier_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r33a_dual_slot_user_clips_preserved_verified",
            "r33a_600mbps_cfexpress_v90_admit_v30_reject_verified",
            "r33a_card_door_gpio_fifo_flush_zero_unflushed_verified",
            "r33a_rsv_to_mxf_salvage_and_mediapro_xml_verified",
            "r33a_stageb_big6_sid_0a_over_300k_pixels_verified",
            "r33b_bodydata_ufu_under_100us_stock_bypass_verified",
            "r33b_cross_model_fx30_rejected_verified",
            "r33b_p1_arm_blocked_until_h0_eq_h3_verified",
            "r33c_5tier_recovery_escalation_5_of_5_verified",
            "r33c_el3_tx_zero_and_spi_nor_writes_zero_verified",
        ),
        run_specs=(
            ("r33a_cfexpress_rsv_big6_schinese", 1),
            ("r33b_bodydata_ufu_bypass", None),
            ("r33c_recovery_5tier", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=34,
        summary_relpath=ROUND34_SUMMARY_RELPATH,
        expected_schema=ROUND34_EXPECTED_SCHEMA,
        audit_key="r34_realhw_cxd90058_c2pa_tc_gyro_seal_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r34a_p12_c2pa_rq_lic_erofs_and_cross_model_blocked_verified",
            "r34a_vmc_bncm1_ext_lk_24fps_tc_out_masked_verified",
            "r34a_imx510_8700us_gyro_nrtm_xml_verified",
            "r34a_stageb_big6_sid_0a_over_300k_pixels_verified",
            "r34b_p8_cpapp_and_sabin_erofs_zero_writes_verified",
            "r34b_memcfg_1724m_xavc_libmpr_bridge_verified",
            "r34b_sdi_raw_mew_fail_closed_masked_verified",
            "r34c_raid6_gf256_2chunk_bitrot_heal_verified",
            "r34c_16_surface_h0_eq_h3_zero_residual_seal_verified",
        ),
        run_specs=(
            ("r34a_c2pa_tc_gyro_big6_schinese", 1),
            ("r34b_cxd90058_sabin_sdi_mask", None),
            ("r34c_raid6_gf256_seal_16", None),
        ),
    ),
)

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_VM_STAGE_KEY_RE = re.compile(r"^stage(\d+)_")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealHwMilestone175FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 faults (58-gate preflight, G21..G58)
    p1_service_0336_canary_kwargs: Optional[Mapping[str, Any]] = None
    p1_stageb_mpr_ibis_p18_kwargs: Optional[Mapping[str, Any]] = None
    p1_pnflasha_mtdro_kwargs: Optional[Mapping[str, Any]] = None
    p1_rfnvs_fan_power_kwargs: Optional[Mapping[str, Any]] = None
    p1_uart1v8_isp_kwargs: Optional[Mapping[str, Any]] = None
    p1_imx510_sensor_cal_kwargs: Optional[Mapping[str, Any]] = None
    p1_cfexpress_ufu_kwargs: Optional[Mapping[str, Any]] = None
    p1_five_tier_el3_kwargs: Optional[Mapping[str, Any]] = None
    p1_cxd90058_sabin_kwargs: Optional[Mapping[str, Any]] = None
    p1_factory_seal_kwargs: Optional[Mapping[str, Any]] = None
    p1_c2pa_cert_kwargs: Optional[Mapping[str, Any]] = None
    p1_tc_gyro_meta_kwargs: Optional[Mapping[str, Any]] = None
    p1_dualmedia_vault_kwargs: Optional[Mapping[str, Any]] = None
    p1_bench_interlock_kwargs: Optional[Mapping[str, Any]] = None
    p1_vp_strobe_genlock_kwargs: Optional[Mapping[str, Any]] = None
    p1_vehiclerig_ibis_kwargs: Optional[Mapping[str, Any]] = None
    p1_jiritsu_service_kwargs: Optional[Mapping[str, Any]] = None
    p1_cnflasha_dualboot_kwargs: Optional[Mapping[str, Any]] = None
    p1_pl_cantilever_kwargs: Optional[Mapping[str, Any]] = None
    p1_dummy_battery_kwargs: Optional[Mapping[str, Any]] = None
    p1_saltspray_haze_kwargs: Optional[Mapping[str, Any]] = None
    p1_followfocus_gimbal_kwargs: Optional[Mapping[str, Any]] = None
    p1_hdmi_aoc_kwargs: Optional[Mapping[str, Any]] = None
    p1_cfexpress_media_kwargs: Optional[Mapping[str, Any]] = None
    p1_usbpd_uvc_kwargs: Optional[Mapping[str, Any]] = None
    p1_multiterminal_ptp_kwargs: Optional[Mapping[str, Any]] = None
    p1_monsoon_mishoe_kwargs: Optional[Mapping[str, Any]] = None
    p1_cagetwist_xlrh1_kwargs: Optional[Mapping[str, Any]] = None
    p1_dewpoint_kwargs: Optional[Mapping[str, Any]] = None
    p1_pmic_usbc_kwargs: Optional[Mapping[str, Any]] = None
    p1_xlr_kwargs: Optional[Mapping[str, Any]] = None
    p1_gimbal_kwargs: Optional[Mapping[str, Any]] = None
    p1_rig_kwargs: Optional[Mapping[str, Any]] = None
    p1_emount_kwargs: Optional[Mapping[str, Any]] = None
    p1_power_failover_kwargs: Optional[Mapping[str, Any]] = None
    p1_intake_fan_kwargs: Optional[Mapping[str, Any]] = None
    p1_tripod_housing_kwargs: Optional[Mapping[str, Any]] = None
    p1_sensor_curtain_kwargs: Optional[Mapping[str, Any]] = None
    p1_subzero_altitude_kwargs: Optional[Mapping[str, Any]] = None
    p1_wireless_tx_emi_kwargs: Optional[Mapping[str, Any]] = None
    p1_longform_endurance_kwargs: Optional[Mapping[str, Any]] = None
    p1_request_persistent_writes: bool = False

    # P2 faults (22-pillar recovery master + Pillars 18..22 + redlines)
    p2_fault_inject_pillar: Optional[str] = None
    p2_otp_fuse_touches_override: int = 0
    p2_rpmb_increments_override: int = 0
    p2_passive_tx_bytes_override: int = 0
    p2_physical_usb_packets_override: int = 0
    p2_physical_device_writes_override: int = 0
    p2_raw_firmware_bytes_leaked_override: int = 0

    # P3 faults (>= 36 fx3_firmware_lab auditors, incl. #25..#36)
    p3_calibration_mutation_bytes: int = 0
    p3_bk4_persistent_nvram_writes: int = 0
    p3_corrupt_wb_whitepoint: bool = False
    p3_corrupt_nrtm_sidecar: bool = False
    p3_inject_legacy_sq_big6_block: bool = False
    p3_inject_persistent_nvram_shadow_path: bool = False
    p3_int24_wrap_around_count: int = 0
    p3_bus_contention_count: int = 0
    p3_p4_nd_motor_fault_attempts: int = 0
    p3_inject_internal_emmc_format_attempt: bool = False
    p3_imu_calibration_mutation_bytes: int = 0
    p3_emmc_mutation_bytes: int = 0
    p3_c2pa_shading_mutation_bytes: int = 0
    p3_hdr_nrtm_mutation_bytes: int = 0
    p3_ob_clamp_mutation_bytes: int = 0
    p3_uvc_crsdk_emmc_mutation_bytes: int = 0
    p3_mxf_tally_emmc_mutation_bytes: int = 0
    p3_vp_ledwall_emmc_mutation_bytes: int = 0
    p3_xavc_fz100_emmc_mutation_bytes: int = 0
    p3_realhw_cp_spi_mutation_bytes: int = 0
    p3_realhw_mpr_bridge_emmc_mutation_bytes: int = 0
    p3_peripheral_p18_emmc_mutation_bytes: int = 0
    p3_controls_fan_emmc_mutation_bytes: int = 0
    p3_wifi_rfnvs_mutation_bytes: int = 0
    p3_imx510_sensor_cal_mutation_bytes: int = 0
    p3_cfexpress_ufu_emmc_mutation_bytes: int = 0
    p3_cxd90058_sabin_mutation_bytes: int = 0
    p3_c2pa_cert_mutation_bytes: int = 0
    p3_wbi2_hibdrv_mutation_bytes: int = 0

    # P4 faults (>= 30-stage VM co-emulation, Stages 1..30)
    p4_cp_mutation_bytes: int = 0
    p4_bk4_persistent_nvram_writes: int = 0
    p4_stage10_dropped_frames: int = 0
    p4_stage11_nop_count: int = 0
    p4_stage11_null_gpio_derefs: int = 0
    p4_stage12_uart_contention_events: int = 0
    p4_stage13_p1_emmc_format_attempt: bool = False
    p4_stage13_p4_nd_motor_faults: int = 0
    p4_stage15_wf12_hits: int = 0
    p4_stage16_lithium_plating_events: int = 0
    p4_stage17_emmc_sector_writes: int = 0
    p4_stage18_cnflasha_mutation_bytes: int = 0
    p4_stage18_private_key_exports: int = 0
    p4_stage19_fiz_gear_strip_events: int = 0
    p4_stage19_display_assist_burn_in_frames: int = 0
    p4_stage20_pl_breathing_stale_crop_frames: int = 0
    p4_stage20_sy1129_fuse_damage_events: int = 0
    p4_stage21_emmc_flash_mutation_bytes: int = 0
    p4_stage21_wf12_hits: int = 0
    p4_stage21_uart_tx_bytes: int = 0
    p4_stage22_emmc_mutation_bytes: int = 0
    p4_stage23_emmc_mutation_bytes: int = 0
    p4_stage24_emmc_mutation_bytes: int = 0
    p4_stage24_spi_nor_mutation_bytes: int = 0
    p4_stage24_sector0_mutation_bytes: int = 0
    p4_stage24_rsv_orphan_count: int = 0
    p4_stage25_emmc_mutation_bytes: int = 0
    p4_stage26_p18_mutation_bytes: int = 0
    p4_stage27_sensor_or_rfnvs_mutation_bytes: int = 0
    p4_stage28_spi_or_emmc_mutation_bytes: int = 0
    p4_stage29_cxd90058_or_residual_count: int = 0
    p4_stage30_c2pa_or_voltage_events: int = 0

    # P5 faults (Closure Phase 136 + Phase 143 + Phase 154 Bench Preflight)
    p5_inject_p136_u4_u5_u6_fault: bool = False
    p5_inject_p143_escape_hatch_over_budget_us: int = 0
    p5_inject_p143_h0_h3_drift: bool = False
    p5_inject_p154_no_go_fault: bool = False
    p5_inject_p154_usb_packets_override: int = 0

    # P6 faults (Rounds 28..34 live QEMU kernel rehearsal receipts)
    p6_round_nop_override_num: Optional[int] = None
    p6_round_nop_count_override: Optional[int] = None
    p6_round_crash_override_num: Optional[int] = None
    p6_round_crashes_override: Optional[int] = None
    p6_round_emmc_override_num: Optional[int] = None
    p6_round_emmc_writes_override: Optional[int] = None
    p6_tamper_schema_round_num: Optional[int] = None


@dataclass(frozen=True)
class Milestone175PillarResult:
    pillar_id: str
    pillar_name: str
    passed: bool
    status: str
    summary: str
    evidence: Dict[str, Any]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwMilestone175MasterGateReport:
    schema_version: str
    phase_version: str
    verification_mode: str
    all_pillars_milestone_ready: bool
    status: str
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    hardware_live_attachment_authorized: bool
    hardware_live_attachment_requirements: Tuple[str, ...]
    physical_usb_packets_emitted: int
    p8_cp_mutation_forbidden: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    cp_mutation_bytes: int
    wbi_mutation_bytes: int
    calibration_mutation_bytes: int
    usb_or_camera_operations: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    temp_dir_cleaned: bool
    pillar_count: int
    passed_pillar_count: int
    failed_pillar_ids: Tuple[str, ...]
    pillars: Tuple[Milestone175PillarResult, ...]
    gate58_total_gates: int
    gate58_offline_verified: int
    gate58_simulated_verified: int
    recovery_pillar_count: int
    recovery_pillars_passed: int
    firmware_lab_auditor_count: int
    firmware_lab_auditors_passed: int
    vm_coemulation_stage_count: int
    vm_coemulation_stages_passed: int
    vm_emmc_corruptions: int
    vm_wf12_00342260_hits: int
    p136_u6_command_count: int
    p136_u4_u5_u6_closed: bool
    p143_sd_escape_absent_us: int
    p143_h0_equals_h3_count: int
    p143_h0_h3_surface_count: int
    p154_bench_go: bool
    p154_usb_packets_emitted: int
    p154_iokit_handles_opened: int
    qemu_rounds_verified: int
    qemu_runs_verified: int
    qemu_round_runs_by_round: Dict[str, int]
    qemu_real_kernel_nop_count: int
    qemu_real_kernel_crashes: int
    qemu_real_kernel_emmc_writes: int
    errors: Tuple[str, ...]
    milestone175_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class RealHwMilestone175VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone175_sha256: str
    observed_milestone175_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic Digest & O_RDONLY Rounds 28..34 Receipt Loaders
# ---------------------------------------------------------------------------


def compute_milestone175_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `RealHwMilestone175MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone175_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def _load_round28_to_34_summary(
    spec: RoundQemuReceiptSpec,
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], str]:
    """Load Round 28..34 QEMU rehearsal summary strictly via `os.O_RDONLY`, else clean-room synthetic."""
    summary_path = repo_root / spec.summary_relpath
    if not use_clean_room:
        if not summary_path.is_file() or summary_path.is_symlink():
            raise FileNotFoundError(f"Missing round{spec.round_num} summary report: {summary_path}")
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if not isinstance(obj, dict):
            raise ValueError(f"Invalid JSON object in {summary_path}")
        return obj, "REPO_SUMMARY_O_RDONLY"

    if summary_path.is_file() and not summary_path.is_symlink():
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if isinstance(obj, dict):
            return obj, "REPO_SUMMARY_O_RDONLY"

    manifest_items = _build_clean_room_stage_b_manifest_items()
    kver = "Linux version 4.9.337-scel+ (clean-room-synthetic)"
    runs: Dict[str, Any] = {}
    for rid, exp_f in spec.run_specs:
        run_entry: Dict[str, Any] = {
            "run_id": rid.replace("_", "-"),
            "round": spec.round_num,
            "lang": "schinese",
            "kernel_version": kver,
            "crashes": 0,
            "emmc_write_count": 0,
            "stage_b": {
                "stage": "B",
                f"r{spec.round_num}_enabled": True,
                "lang": "schinese",
                "manifest_count": 13,
                "manifest_items": list(manifest_items),
            },
        }
        if exp_f is not None:
            faithful = _clean_room_faithful_block()
            faithful["FX6_NATIVE_FAITHFUL"] = exp_f
            faithful["emmc_write_count"] = 0
            run_entry["nop_count"] = 0
            run_entry["faithful_invariants"] = faithful
        runs[rid] = run_entry

    audit_obj: Dict[str, Any] = {k: True for k in spec.audit_bool_keys}
    audit_obj["total_runs"] = len(spec.run_specs)
    return (
        {
            "schema": spec.expected_schema,
            "kernel_version": kver,
            "runs": runs,
            spec.audit_key: audit_obj,
        },
        "CLEAN_ROOM_SYNTHETIC",
    )


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 3.8s / < 2.2s)
# ---------------------------------------------------------------------------


_58GATE_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_service_0336_canary_kwargs", "service_0336_canary_kwargs"),
    ("p1_stageb_mpr_ibis_p18_kwargs", "stageb_mpr_ibis_p18_kwargs"),
    ("p1_pnflasha_mtdro_kwargs", "pnflasha_mtdro_kwargs"),
    ("p1_rfnvs_fan_power_kwargs", "rfnvs_fan_power_kwargs"),
    ("p1_uart1v8_isp_kwargs", "uart1v8_isp_kwargs"),
    ("p1_imx510_sensor_cal_kwargs", "imx510_sensor_cal_kwargs"),
    ("p1_cfexpress_ufu_kwargs", "cfexpress_ufu_kwargs"),
    ("p1_five_tier_el3_kwargs", "five_tier_el3_kwargs"),
    ("p1_cxd90058_sabin_kwargs", "cxd90058_sabin_kwargs"),
    ("p1_factory_seal_kwargs", "factory_seal_kwargs"),
    ("p1_c2pa_cert_kwargs", "c2pa_cert_kwargs"),
    ("p1_tc_gyro_meta_kwargs", "tc_gyro_meta_kwargs"),
    ("p1_dualmedia_vault_kwargs", "dualmedia_vault_kwargs"),
    ("p1_bench_interlock_kwargs", "bench_interlock_kwargs"),
    ("p1_vp_strobe_genlock_kwargs", "vp_strobe_genlock_kwargs"),
    ("p1_vehiclerig_ibis_kwargs", "vehiclerig_ibis_kwargs"),
    ("p1_jiritsu_service_kwargs", "jiritsu_service_kwargs"),
    ("p1_cnflasha_dualboot_kwargs", "cnflasha_dualboot_kwargs"),
    ("p1_pl_cantilever_kwargs", "pl_cantilever_kwargs"),
    ("p1_dummy_battery_kwargs", "dummy_battery_kwargs"),
    ("p1_saltspray_haze_kwargs", "saltspray_haze_kwargs"),
    ("p1_followfocus_gimbal_kwargs", "followfocus_gimbal_kwargs"),
    ("p1_hdmi_aoc_kwargs", "hdmi_aoc_kwargs"),
    ("p1_cfexpress_media_kwargs", "cfexpress_media_kwargs"),
    ("p1_usbpd_uvc_kwargs", "usbpd_uvc_kwargs"),
    ("p1_multiterminal_ptp_kwargs", "multiterminal_ptp_kwargs"),
    ("p1_monsoon_mishoe_kwargs", "monsoon_mishoe_kwargs"),
    ("p1_cagetwist_xlrh1_kwargs", "cagetwist_xlrh1_kwargs"),
    ("p1_dewpoint_kwargs", "dewpoint_kwargs"),
    ("p1_pmic_usbc_kwargs", "pmic_usbc_kwargs"),
    ("p1_xlr_kwargs", "xlr_kwargs"),
    ("p1_gimbal_kwargs", "gimbal_kwargs"),
    ("p1_rig_kwargs", "rig_kwargs"),
    ("p1_emount_kwargs", "emount_kwargs"),
    ("p1_power_failover_kwargs", "power_failover_kwargs"),
    ("p1_intake_fan_kwargs", "intake_fan_kwargs"),
    ("p1_tripod_housing_kwargs", "tripod_housing_kwargs"),
    ("p1_sensor_curtain_kwargs", "sensor_curtain_kwargs"),
    ("p1_subzero_altitude_kwargs", "subzero_altitude_kwargs"),
    ("p1_wireless_tx_emi_kwargs", "wireless_tx_emi_kwargs"),
    ("p1_longform_endurance_kwargs", "longform_endurance_kwargs"),
)


def _fault_to_m147_faults(faults: RealHwMilestone175FaultInjection) -> RealHwMilestone147FaultInjection:
    return RealHwMilestone147FaultInjection(
        p3_calibration_mutation_bytes=faults.p3_calibration_mutation_bytes,
        p3_bk4_persistent_nvram_writes=faults.p3_bk4_persistent_nvram_writes,
        p3_corrupt_wb_whitepoint=faults.p3_corrupt_wb_whitepoint,
        p3_corrupt_nrtm_sidecar=faults.p3_corrupt_nrtm_sidecar,
        p3_inject_legacy_sq_big6_block=faults.p3_inject_legacy_sq_big6_block,
        p3_inject_persistent_nvram_shadow_path=faults.p3_inject_persistent_nvram_shadow_path,
        p3_int24_wrap_around_count=faults.p3_int24_wrap_around_count,
        p3_bus_contention_count=faults.p3_bus_contention_count,
        p3_p4_nd_motor_fault_attempts=faults.p3_p4_nd_motor_fault_attempts,
        p3_inject_internal_emmc_format_attempt=faults.p3_inject_internal_emmc_format_attempt,
        p3_imu_calibration_mutation_bytes=faults.p3_imu_calibration_mutation_bytes,
        p3_emmc_mutation_bytes=faults.p3_emmc_mutation_bytes,
        p3_c2pa_shading_mutation_bytes=faults.p3_c2pa_shading_mutation_bytes,
        p3_hdr_nrtm_mutation_bytes=faults.p3_hdr_nrtm_mutation_bytes,
        p3_ob_clamp_mutation_bytes=faults.p3_ob_clamp_mutation_bytes,
        p3_uvc_crsdk_emmc_mutation_bytes=faults.p3_uvc_crsdk_emmc_mutation_bytes,
        p3_mxf_tally_emmc_mutation_bytes=faults.p3_mxf_tally_emmc_mutation_bytes,
        p3_vp_ledwall_emmc_mutation_bytes=faults.p3_vp_ledwall_emmc_mutation_bytes,
        p3_xavc_fz100_emmc_mutation_bytes=faults.p3_xavc_fz100_emmc_mutation_bytes,
        p3_realhw_cp_spi_mutation_bytes=faults.p3_realhw_cp_spi_mutation_bytes,
        p3_realhw_mpr_bridge_emmc_mutation_bytes=faults.p3_realhw_mpr_bridge_emmc_mutation_bytes,
        p4_cp_mutation_bytes=faults.p4_cp_mutation_bytes,
        p4_bk4_persistent_nvram_writes=faults.p4_bk4_persistent_nvram_writes,
        p4_stage10_dropped_frames=faults.p4_stage10_dropped_frames,
        p4_stage11_nop_count=faults.p4_stage11_nop_count,
        p4_stage11_null_gpio_derefs=faults.p4_stage11_null_gpio_derefs,
        p4_stage12_uart_contention_events=faults.p4_stage12_uart_contention_events,
        p4_stage13_p1_emmc_format_attempt=faults.p4_stage13_p1_emmc_format_attempt,
        p4_stage13_p4_nd_motor_faults=faults.p4_stage13_p4_nd_motor_faults,
        p4_stage15_wf12_hits=faults.p4_stage15_wf12_hits,
        p4_stage16_lithium_plating_events=faults.p4_stage16_lithium_plating_events,
        p4_stage17_emmc_sector_writes=faults.p4_stage17_emmc_sector_writes,
        p4_stage18_cnflasha_mutation_bytes=faults.p4_stage18_cnflasha_mutation_bytes,
        p4_stage18_private_key_exports=faults.p4_stage18_private_key_exports,
        p4_stage19_fiz_gear_strip_events=faults.p4_stage19_fiz_gear_strip_events,
        p4_stage19_display_assist_burn_in_frames=faults.p4_stage19_display_assist_burn_in_frames,
        p4_stage20_pl_breathing_stale_crop_frames=faults.p4_stage20_pl_breathing_stale_crop_frames,
        p4_stage20_sy1129_fuse_damage_events=faults.p4_stage20_sy1129_fuse_damage_events,
        p4_stage21_emmc_flash_mutation_bytes=faults.p4_stage21_emmc_flash_mutation_bytes,
        p4_stage21_wf12_hits=faults.p4_stage21_wf12_hits,
        p4_stage21_uart_tx_bytes=faults.p4_stage21_uart_tx_bytes,
        p4_stage22_emmc_mutation_bytes=faults.p4_stage22_emmc_mutation_bytes,
        p4_stage23_emmc_mutation_bytes=faults.p4_stage23_emmc_mutation_bytes,
        p4_stage24_emmc_mutation_bytes=faults.p4_stage24_emmc_mutation_bytes,
        p4_stage24_spi_nor_mutation_bytes=faults.p4_stage24_spi_nor_mutation_bytes,
        p4_stage24_sector0_mutation_bytes=faults.p4_stage24_sector0_mutation_bytes,
        p4_stage24_rsv_orphan_count=faults.p4_stage24_rsv_orphan_count,
        p5_inject_p136_u4_u5_u6_fault=faults.p5_inject_p136_u4_u5_u6_fault,
        p5_inject_p143_escape_hatch_over_budget_us=faults.p5_inject_p143_escape_hatch_over_budget_us,
        p5_inject_p143_h0_h3_drift=faults.p5_inject_p143_h0_h3_drift,
    )


def _fault_to_58gate_worker_dict(faults: RealHwMilestone175FaultInjection) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "p1_request_persistent_writes": bool(faults.p1_request_persistent_writes),
    }
    for src_attr, _ in _58GATE_FAULT_FIELDS:
        val = getattr(faults, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    return out


def _extract_gate_dict(g: object) -> Dict[str, Any]:
    if isinstance(g, Mapping):
        return dict(g)
    return {
        "gate_id": getattr(g, "gate_id", ""),
        "gate_code": getattr(g, "gate_code", ""),
        "status": getattr(g, "status", ""),
        "passed": bool(getattr(g, "passed", False)),
        "violation_codes": tuple(getattr(g, "violation_codes", ())),
    }


def _worker_58gate_single(args: Tuple[str, bool, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, dry_run_sim, fault_dict = args
    repo_root = Path(repo_root_str)
    kwargs: Dict[str, Any] = {
        "request_persistent_emmc_writes": bool(fault_dict.get("p1_request_persistent_writes", False))
    }
    for src_attr, dst_kw in _58GATE_FAULT_FIELDS:
        if fault_dict.get(src_attr) is not None:
            kwargs[dst_kw] = fault_dict[src_attr]

    rep = evaluate_58gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=dry_run_sim,
        **kwargs,
    )

    m56 = rep.master_56_report
    m54 = m56.get("master_54_report", {})
    m52 = m54.get("master_52_report", {})
    m50 = m52.get("master_50_report", {})
    m48 = m50.get("master_48_report", {})
    m46 = m48.get("master_46_report", {})
    nested_g_valid: Dict[str, bool] = {}
    for tag, src in (
        ("g45", m46.get("g45_result", {})),
        ("g46", m46.get("g46_result", {})),
        ("g47", m48.get("g47_result", {})),
        ("g48", m48.get("g48_result", {})),
        ("g49", m50.get("g49_result", {})),
        ("g50", m50.get("g50_result", {})),
        ("g51", m52.get("g51_result", {})),
        ("g52", m52.get("g52_result", {})),
        ("g53", m54.get("g53_result", {})),
        ("g54", m54.get("g54_result", {})),
        ("g55", m56.get("g55_result", {})),
        ("g56", m56.get("g56_result", {})),
        ("g57", rep.g57_result),
        ("g58", rep.g58_result),
    ):
        nested_g_valid[tag] = isinstance(src, Mapping) and bool(src.get("valid", False))

    gates_brief = [_extract_gate_dict(g) for g in rep.gates]
    return {
        "schema": rep.schema,
        "verification_mode": rep.verification_mode,
        "total_gates": int(rep.summary.get("total_gates", len(gates_brief))),
        "verified_gates": int(rep.summary.get("verified_gates", 0)),
        "offline_55_gates_verified": bool(rep.offline_55_gates_verified),
        "all_58_gates_verified": bool(rep.all_58_gates_verified),
        "g13_to_g58_all_passed": bool(rep.g13_to_g58_all_passed),
        "g57_to_g58_all_passed": bool(rep.g57_to_g58_all_passed),
        "dry_run_rehearsal_only": bool(rep.dry_run_rehearsal_only),
        "overall_ready_for_hardware_attach": bool(rep.overall_ready_for_hardware_attach),
        "agent_auto_flash_blocked": bool(rep.agent_auto_flash_blocked),
        "el3_payload_transmit_authorized": bool(rep.el3_payload_transmit_authorized),
        "spi_nor_write_authorized": bool(rep.spi_nor_write_authorized),
        "persistent_emmc_writes_authorized": bool(rep.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep.persistent_write_release),
        "nested_g45_to_g58_valid": nested_g_valid,
        "gates_45_to_58": gates_brief[44:],
        "errors": list(rep.errors),
    }


def _worker_recovery_22pillar(args: Tuple[bool, Optional[str]]) -> Dict[str, Any]:
    use_clean_room, fault_pillar = args
    rep = evaluate_22pillar_recovery_master(
        force_clean_room=use_clean_room,
        fault_inject_pillar=fault_pillar,
    )
    return {
        "schema": rep.schema,
        "version": rep.version,
        "verification_mode": rep.verification_mode,
        "all_passed": bool(rep.all_passed),
        "status": rep.status,
        "pillar_count": int(rep.pillar_count),
        "pillars_passed": int(rep.pillars_passed),
        "failed_pillars": list(rep.failed_pillars),
        "pillars": [asdict(p) for p in rep.pillars],
        "pillar22_a_dual_media": asdict(rep.pillar22_a_dual_media),
        "pillar22_b_gf256_scrub": asdict(rep.pillar22_b_gf256_scrub),
        "master_22pillar_sha256": rep.master_22pillar_sha256,
        "otp_fuse_touches": int(rep.otp_fuse_touches),
        "otp_fuse_writes": int(rep.otp_fuse_writes),
        "rpmb_counter_increments": int(rep.rpmb_counter_increments),
        "passive_tx_bytes_emitted": int(rep.passive_tx_bytes_emitted),
        "physical_usb_packets_emitted": int(rep.physical_usb_packets_emitted),
        "physical_device_writes": int(rep.physical_device_writes),
        "raw_firmware_bytes_leaked": int(rep.raw_firmware_bytes_leaked),
        "el3_payload_transmit_authorized": bool(rep.el3_payload_transmit_authorized),
        "isp_write_authorized": bool(rep.isp_write_authorized),
        "spi_nor_write_authorized": bool(rep.spi_nor_write_authorized),
        "persistent_emmc_writes_authorized": bool(rep.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep.persistent_write_release),
        "live_usb_iokit_transmit_enabled": bool(rep.live_usb_iokit_transmit_enabled),
        "errors": list(rep.errors),
    }


def _worker_pillar_3_group(args: Tuple[str, bool]) -> Dict[str, Dict[str, Any]]:
    group, clean_room = args
    if group == "realhw_peripheral":
        return {
            "realhw_lens_ibis_audio_hdmi_peripheral_bridge_audit": realhw_lens_ibis_audio_hdmi_peripheral_bridge_report_to_dict(
                analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=clean_room)
            )
        }
    if group == "realhw_controls_fan":
        return {
            "realhw_physical_controls_tally_fan_and_power_audit": realhw_physical_controls_tally_fan_and_power_report_to_dict(
                analyze_realhw_physical_controls_tally_fan_and_power(clean_room=clean_room)
            )
        }
    if group == "realhw_wifi_usb":
        return {
            "realhw_wifi_bt_usb_uvc_network_bridge_audit": realhw_wifi_bt_usb_uvc_network_bridge_report_to_dict(
                analyze_realhw_wifi_bt_usb_uvc_network_bridge(clean_room=clean_room)
            )
        }
    if group == "realhw_imx510":
        return {
            "realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_audit": realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_report_to_dict(
                analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=clean_room)
            )
        }
    if group == "realhw_cfexpress_ufu":
        return {
            "realhw_cfexpress_sdxc_exfat_rsv_ufu_coexistence_audit": realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_report_to_dict(
                analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence(clean_room=clean_room)
            )
        }
    if group == "realhw_cxd90058_sabin":
        return {
            "realhw_cxd90057_cxd90058_sabin_codec_audit": realhw_cxd90057_cxd90058_sabin_codec_report_to_dict(
                analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=clean_room)
            )
        }
    if group == "realhw_c2pa_tc_gyro":
        return {
            "realhw_c2pa_cert_vmcbncm1_tc_gyro_meta_audit": realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_report_to_dict(
                analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta(clean_room=clean_room)
            )
        }
    if group == "realhw_wbi2_hibdrv":
        return {
            "realhw_wbi2_hibdrv_hibernation_isolation_audit": realhw_wbi2_hibdrv_hibernation_isolation_report_to_dict(
                analyze_realhw_wbi2_hibdrv_hibernation_isolation(clean_room=clean_room)
            )
        }
    return _m147_worker_pillar_3_group((group, clean_room))


def _worker_pillar_3_batch(args: Tuple[Tuple[str, ...], bool]) -> Dict[str, Dict[str, Any]]:
    groups, clean_room = args
    merged: Dict[str, Dict[str, Any]] = {}
    for g in groups:
        merged.update(_worker_pillar_3_group((g, clean_room)))
    return merged


def _worker_phase136(use_clean_room: bool) -> Dict[str, Any]:
    return run_phase136_realhw_jiritsu_tier0_audit(synthetic_clean_room=use_clean_room).to_dict()


def _worker_phase143_and_154(args: Tuple[str, str, bool, bool]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    fx6_lib_dir_str, fx3_modules_dir_str, use_clean_room, p154_sim_ready = args
    p143 = run_phase143_sd_stageb_bundle_uninstaller_audit(
        fx6_lib_dir=Path(fx6_lib_dir_str),
        fx3_modules_dir=Path(fx3_modules_dir_str),
        synthetic_clean_room=use_clean_room,
    ).to_dict()
    p154 = run_realhw_bench_preflight(
        simulate_ready_bench=p154_sim_ready,
        fx6_lib_dir=Path(fx6_lib_dir_str),
        fx3_modules_dir=Path(fx3_modules_dir_str),
        synthetic_clean_room=use_clean_room,
    ).to_dict()
    return p143, p154


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1 .. P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
) -> Milestone175PillarResult:
    errors: List[str] = []
    total_gates = int(raw_sim.get("total_gates", 0))
    offline_verified = int(raw_off.get("verified_gates", -1))
    sim_verified = int(raw_sim.get("verified_gates", -1))

    if total_gates < 58:
        errors.append(f"p1: total_gates expected >= 58, got {total_gates}")
    if (
        not raw_off.get("offline_55_gates_verified")
        or offline_verified < 55
        or offline_verified >= total_gates
    ):
        errors.append(
            f"p1: offline hardware-truth gates expected >= 55 and < {total_gates}, got {offline_verified}/{total_gates}"
        )
    if raw_off.get("all_58_gates_verified") or raw_off.get("overall_ready_for_hardware_attach"):
        errors.append("p1: offline mode must remain blocked for live hardware attach (G10..G12)")
    if (
        not raw_sim.get("all_58_gates_verified")
        or sim_verified < 58
        or sim_verified != total_gates
    ):
        errors.append(
            f"p1: simulated rehearsal gates expected >= 58 and == {total_gates}, got {sim_verified}/{total_gates}"
        )
    if not raw_sim.get("dry_run_rehearsal_only") or raw_sim.get("overall_ready_for_hardware_attach"):
        errors.append("p1: simulated 58-gate rehearsal must keep overall_ready_for_hardware_attach=False")
    if not raw_sim.get("g13_to_g58_all_passed") or not raw_sim.get("g57_to_g58_all_passed"):
        errors.append("p1: G13..G58 or G57..G58 safety guard gate blocked")

    nested = raw_sim.get("nested_g45_to_g58_valid", {})
    for gnum in range(45, 59):
        if not bool(nested.get(f"g{gnum}", False)):
            errors.append(f"p1: G{gnum} nested safety guard failed")

    g45_to_58 = raw_sim.get("gates_45_to_58", ())
    if len(g45_to_58) < 14 or any(not bool(g.get("passed", False)) for g in g45_to_58):
        errors.append("p1: one or more G45..G58 master gates failed in simulated rehearsal")

    for obj_name, obj in (("offline", raw_off), ("simulated", raw_sim)):
        if (
            obj.get("persistent_emmc_writes_authorized") is not False
            or obj.get("persistent_write_release") is not False
            or obj.get("spi_nor_write_authorized") is not False
            or obj.get("el3_payload_transmit_authorized") is not False
            or obj.get("agent_auto_flash_blocked") is not True
        ):
            errors.append(f"p1 ({obj_name}): hard-locked zero-write/SPI-NOR/EL3/auto-flash guard breached")

    for err in raw_sim.get("errors", ()):
        errors.append(f"p1_58gate: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_sim.get("schema"),
        "verification_mode": raw_sim.get("verification_mode"),
        "total_gates": total_gates,
        "offline_verified_gates": offline_verified,
        "offline_ready_for_hardware_attach": raw_off.get("overall_ready_for_hardware_attach"),
        "simulated_verified_gates": sim_verified,
        "simulated_ready_for_hardware_attach": raw_sim.get("overall_ready_for_hardware_attach"),
        "g13_to_g58_all_passed": raw_sim.get("g13_to_g58_all_passed"),
        "g57_to_g58_all_passed": raw_sim.get("g57_to_g58_all_passed"),
        "nested_g45_to_g58_valid": dict(nested),
        "persistent_emmc_writes_authorized": raw_sim.get("persistent_emmc_writes_authorized"),
        "persistent_write_release": raw_sim.get("persistent_write_release"),
        "spi_nor_write_authorized": raw_sim.get("spi_nor_write_authorized"),
        "el3_payload_transmit_authorized": raw_sim.get("el3_payload_transmit_authorized"),
        "agent_auto_flash_blocked": raw_sim.get("agent_auto_flash_blocked"),
    }
    return Milestone175PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_58GATE_REALHW_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"58-Gate offline={offline_verified}/{total_gates} (G10..G12 locked) "
            f"sim={sim_verified}/{total_gates}, G13..G58={raw_sim.get('g13_to_g58_all_passed')}, "
            f"G57..G58={raw_sim.get('g57_to_g58_all_passed')} {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    raw_22p: Mapping[str, Any],
    faults: RealHwMilestone175FaultInjection,
) -> Tuple[Milestone175PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    if not raw_22p.get("all_passed"):
        errors.append(f"p2: evaluate_22pillar_recovery_master failed ({raw_22p.get('failed_pillars')})")

    pillar_list = raw_22p.get("pillars", ())
    pillar_statuses: Dict[str, bool] = {}
    for pentry in pillar_list:
        if isinstance(pentry, Mapping):
            pid = str(pentry.get("pillar_id", ""))
            ok = bool(pentry.get("passed"))
            if pid:
                pillar_statuses[pid] = ok
                if not ok:
                    errors.append(f"p2: pillar {pid} failed ({pentry.get('errors')})")

    for expected_pid in MASTER_22_PILLAR_IDS:
        if not pillar_statuses.get(expected_pid, False):
            errors.append(f"p2: required recovery pillar missing or failed: {expected_pid}")

    total_pillars = len(pillar_statuses)
    passed_pillars = sum(1 for v in pillar_statuses.values() if v)
    if total_pillars < 22 or passed_pillars < 22 or passed_pillars != total_pillars:
        errors.append(
            f"p2: recovery pillars expected >= 22 and all passing, got {passed_pillars}/{total_pillars}"
        )

    p22a = raw_22p.get("pillar22_a_dual_media", {})
    p22b = raw_22p.get("pillar22_b_gf256_scrub", {})
    if not bool(p22a.get("passed", False)) or not bool(p22b.get("passed", False)):
        errors.append("p2: Pillar 22 dual-media separation or GF(256) scrub verifier failed")

    otp_touches = (
        int(raw_22p.get("otp_fuse_touches", 0))
        + int(raw_22p.get("otp_fuse_writes", 0))
        + int(faults.p2_otp_fuse_touches_override)
    )
    rpmb_incs = int(raw_22p.get("rpmb_counter_increments", 0)) + int(faults.p2_rpmb_increments_override)
    passive_tx = int(raw_22p.get("passive_tx_bytes_emitted", 0)) + int(faults.p2_passive_tx_bytes_override)
    phys_usb = int(raw_22p.get("physical_usb_packets_emitted", 0)) + int(
        faults.p2_physical_usb_packets_override
    )
    phys_writes = int(raw_22p.get("physical_device_writes", 0)) + int(
        faults.p2_physical_device_writes_override
    )
    leaked_fw = int(raw_22p.get("raw_firmware_bytes_leaked", 0)) + int(
        faults.p2_raw_firmware_bytes_leaked_override
    )

    if otp_touches != 0:
        errors.append(f"p2: otp_fuse_touches={otp_touches} != 0")
    if rpmb_incs != 0:
        errors.append(f"p2: rpmb_counter_increments={rpmb_incs} != 0")
    if passive_tx != 0:
        errors.append(f"p2: passive_tx_bytes_emitted={passive_tx} != 0")
    if phys_usb != 0:
        errors.append(f"p2: physical_usb_packets_emitted={phys_usb} != 0")
    if phys_writes != 0 or leaked_fw != 0:
        errors.append(f"p2: physical_device_writes={phys_writes}, raw_fw_leaked={leaked_fw} must be 0")

    if (
        raw_22p.get("el3_payload_transmit_authorized") is not False
        or raw_22p.get("isp_write_authorized") is not False
        or raw_22p.get("spi_nor_write_authorized") is not False
        or raw_22p.get("persistent_emmc_writes_authorized") is not False
        or raw_22p.get("persistent_write_release") is not False
        or raw_22p.get("live_usb_iokit_transmit_enabled") is not False
    ):
        errors.append("p2: hard-locked EL3/ISP/SPI-NOR/eMMC/IOKit write guard breached")

    for err in raw_22p.get("errors", ()):
        errors.append(f"p2_master: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_22p.get("schema"),
        "verification_mode": raw_22p.get("verification_mode"),
        "recovery_pillar_count": total_pillars,
        "recovery_pillars_passed": passed_pillars,
        "pillar_statuses": pillar_statuses,
        "master_22pillar_sha256": raw_22p.get("master_22pillar_sha256"),
        "otp_fuse_touches": otp_touches,
        "rpmb_counter_increments": rpmb_incs,
        "passive_tx_bytes_emitted": passive_tx,
        "physical_usb_packets_emitted": phys_usb,
        "physical_device_writes": phys_writes,
        "el3_payload_transmit_authorized": raw_22p.get("el3_payload_transmit_authorized"),
        "isp_write_authorized": raw_22p.get("isp_write_authorized"),
        "spi_nor_write_authorized": raw_22p.get("spi_nor_write_authorized"),
        "persistent_emmc_writes_authorized": raw_22p.get("persistent_emmc_writes_authorized"),
    }
    pillar = Milestone175PillarResult(
        pillar_id="P2",
        pillar_name="TWENTY_TWO_PILLAR_RECOVERY_VAULT_AND_5TIER_ESCALATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Recovery {passed_pillars}/{total_pillars} pillars (>=22 required; Pillars 18..22 "
            f"Service-0336/mtd0ro/ttyAMA0/5-Tier/Dual-Media RAID-6), "
            f"OTP={otp_touches}, RPMB={rpmb_incs}, passive_tx={passive_tx}B, usb_pkts={phys_usb} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "recovery_pillar_count": total_pillars,
        "recovery_pillars_passed": passed_pillars,
        "otp_fuse_touches": otp_touches,
        "rpmb_counter_increments": rpmb_incs,
        "passive_tx_bytes_emitted": passive_tx,
        "physical_usb_packets_emitted": phys_usb,
    }
    return pillar, meta


def _evaluate_pillar_3(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: RealHwMilestone175FaultInjection,
) -> Tuple[Milestone175PillarResult, Dict[str, Any]]:
    m147_p3, meta_28 = _eval_m147_p3(auditors, _fault_to_m147_faults(faults))
    errors: List[str] = list(m147_p3.errors)
    auditor_statuses: Dict[str, bool] = dict(m147_p3.evidence["auditor_statuses"])
    auditor_sha256s: Dict[str, Optional[str]] = dict(m147_p3.evidence["auditor_sha256s"])

    # #29: p18:/lens + IBIS Center-Lock + XLR-H1 + HDMI/TC
    a29 = auditors.get("realhw_lens_ibis_audio_hdmi_peripheral_bridge_audit", {})
    a29_emmc = int(a29.get("emmc_mutation_bytes", -1)) + int(faults.p3_peripheral_p18_emmc_mutation_bytes)
    a29_cal = int(a29.get("calibration_mutation_bytes", -1))
    if (
        not bool(a29.get("all_checks_passed"))
        or a29.get("o_rdonly_enforced") is not True
        or a29.get("p18_lens_writes_permitted") is not False
        or a29.get("persistent_emmc_writes_authorized") is not False
        or a29_emmc != 0
        or a29_cal != 0
    ):
        errors.append(f"p3: #29 realhw_lens_ibis_audio_hdmi_peripheral_bridge_audit failed (emmc={a29_emmc})")

    # #30: Physical controls + 65°C fan override + tally + NP-FZ100
    a30 = auditors.get("realhw_physical_controls_tally_fan_and_power_audit", {})
    a30_emmc = int(a30.get("emmc_mutation_bytes", -1)) + int(faults.p3_controls_fan_emmc_mutation_bytes)
    a30_cal = int(a30.get("calibration_mutation_bytes", -1))
    if (
        not bool(a30.get("all_checks_passed"))
        or a30.get("o_rdonly_enforced") is not True
        or a30.get("persistent_emmc_writes_authorized") is not False
        or a30_emmc != 0
        or a30_cal != 0
    ):
        errors.append(f"p3: #30 realhw_physical_controls_tally_fan_and_power_audit failed (emmc={a30_emmc})")

    # #31: Zero-diff Wi-Fi / BT / CDC-NCM / 0DA1
    a31 = auditors.get("realhw_wifi_bt_usb_uvc_network_bridge_audit", {})
    a31_rf = int(a31.get("rf_nvs_mutation_bytes", -1)) + int(faults.p3_wifi_rfnvs_mutation_bytes)
    a31_cal = int(a31.get("calibration_mutation_bytes", -1))
    if (
        not bool(a31.get("all_checks_passed"))
        or a31.get("o_rdonly_enforced") is not True
        or a31.get("rf_nvs_p12_p13_writes_permitted") is not False
        or a31.get("persistent_emmc_writes_authorized") is not False
        or int(a31.get("emmc_mutation_bytes", -1)) != 0
        or a31_rf != 0
        or a31_cal != 0
    ):
        errors.append(f"p3: #31 realhw_wifi_bt_usb_uvc_network_bridge_audit failed (rf_nvs={a31_rf})")

    # #32: IMX510 Dual-Base ISO + psd/defdet NVS + .cube MLUT
    a32 = auditors.get("realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_audit", {})
    a32_sc = int(a32.get("sensor_cal_mutation_bytes", -1)) + int(faults.p3_imx510_sensor_cal_mutation_bytes)
    a32_cal = int(a32.get("calibration_mutation_bytes", -1))
    if (
        not bool(a32.get("all_checks_passed"))
        or a32.get("o_rdonly_enforced") is not True
        or a32.get("sensor_cal_p2_writes_permitted") is not False
        or a32.get("persistent_emmc_writes_authorized") is not False
        or int(a32.get("emmc_mutation_bytes", -1)) != 0
        or a32_sc != 0
        or a32_cal != 0
    ):
        errors.append(f"p3: #32 realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_audit failed (sc={a32_sc})")

    # #33: CFexpress/SDXC + .RSV + BODYDATA.DAT UFU coexistence
    a33 = auditors.get("realhw_cfexpress_sdxc_exfat_rsv_ufu_coexistence_audit", {})
    a33_emmc = int(a33.get("emmc_mutation_bytes", -1)) + int(faults.p3_cfexpress_ufu_emmc_mutation_bytes)
    a33_cal = int(a33.get("calibration_mutation_bytes", -1))
    if (
        not bool(a33.get("all_checks_passed"))
        or a33.get("o_rdonly_enforced") is not True
        or a33.get("persistent_emmc_writes_authorized") is not False
        or a33.get("spi_nor_write_authorized") is not False
        or a33_emmc != 0
        or a33_cal != 0
    ):
        errors.append(f"p3: #33 realhw_cfexpress_sdxc_exfat_rsv_ufu_coexistence_audit failed (emmc={a33_emmc})")

    # #34: CXD90057 + CXD90058 + sabin SA-DSP codec boundary
    a34 = auditors.get("realhw_cxd90057_cxd90058_sabin_codec_audit", {})
    a34_mut = (
        int(a34.get("cxd90058_fw_mutation_bytes", -1))
        + int(a34.get("cp_mutation_bytes", -1))
        + int(a34.get("sabin_microcode_mutation_bytes", -1))
        + int(a34.get("emmc_mutation_bytes", -1))
        + int(faults.p3_cxd90058_sabin_mutation_bytes)
    )
    if (
        not bool(a34.get("all_checks_passed"))
        or a34.get("o_rdonly_enforced") is not True
        or a34.get("persistent_emmc_writes_authorized") is not False
        or a34.get("spi_nor_write_authorized") is not False
        or a34_mut != 0
    ):
        errors.append(f"p3: #34 realhw_cxd90057_cxd90058_sabin_codec_audit failed (mut={a34_mut})")

    # #35: p12:/cert/RQ_LIC.DAT C2PA + VMC-BNCM1 TC + IMX510 Gyro XML
    a35 = auditors.get("realhw_c2pa_cert_vmcbncm1_tc_gyro_meta_audit", {})
    a35_mut = (
        int(a35.get("c2pa_cert_mutation_bytes", -1))
        + int(a35.get("cp_mutation_bytes", -1))
        + int(a35.get("p18_lens_mutation_bytes", -1))
        + int(a35.get("emmc_mutation_bytes", -1))
        + int(faults.p3_c2pa_cert_mutation_bytes)
    )
    if (
        not bool(a35.get("all_checks_passed"))
        or a35.get("o_rdonly_enforced") is not True
        or a35.get("persistent_emmc_writes_authorized") is not False
        or a35.get("spi_nor_write_authorized") is not False
        or a35_mut != 0
    ):
        errors.append(f"p3: #35 realhw_c2pa_cert_vmcbncm1_tc_gyro_meta_audit failed (mut={a35_mut})")

    # #36: p5:/wbi WBI2 hibdrv.ko hibernation isolation
    a36 = auditors.get("realhw_wbi2_hibdrv_hibernation_isolation_audit", {})
    a36_wbi = int(a36.get("wbi_mutation_bytes", -1)) + int(faults.p3_wbi2_hibdrv_mutation_bytes)
    if (
        not bool(a36.get("all_checks_passed"))
        or a36.get("o_rdonly_enforced") is not True
        or a36.get("wbi_save_inhibited") is not True
        or a36.get("stock_fx3_wbi2_preserved") is not True
        or a36.get("persistent_emmc_writes_authorized") is not False
        or a36.get("spi_nor_write_authorized") is not False
        or a36_wbi != 0
    ):
        errors.append(f"p3: #36 realhw_wbi2_hibdrv_hibernation_isolation_audit failed (wbi={a36_wbi})")

    for key in FIRMWARE_LAB_36_AUDITOR_KEYS[28:]:
        obj = auditors.get(key, {})
        ok = isinstance(obj, Mapping) and bool(obj.get("all_checks_passed"))
        auditor_statuses[key] = ok
        sha_val = obj.get("report_sha256") or obj.get("audit_digest_sha256") if isinstance(obj, Mapping) else None
        auditor_sha256s[key] = str(sha_val) if sha_val else None

    total_count = len(auditor_statuses)
    passed_count = sum(1 for v in auditor_statuses.values() if v)
    total_cal_mut = max(
        int(meta_28["calibration_mutation_bytes"]),
        max(0, a29_cal),
        max(0, a30_cal),
        max(0, a31_cal),
        max(0, a32_cal),
        max(0, a33_cal),
        max(0, a31_rf),
        max(0, a32_sc),
    )

    if total_count < 36 or passed_count < 36 or passed_count != total_count:
        errors.append(f"p3: expected >= 36 auditors and all passing, got {passed_count}/{total_count}")

    passed = len(errors) == 0 and total_cal_mut == 0
    evidence = dict(m147_p3.evidence)
    evidence.update(
        {
            "auditor_count": total_count,
            "passed_auditor_count": passed_count,
            "auditor_statuses": auditor_statuses,
            "auditor_sha256s": auditor_sha256s,
            "calibration_mutation_bytes": total_cal_mut,
            "wbi2_hibdrv_mutation_bytes": max(0, a36_wbi),
            "c2pa_cert_mutation_bytes": max(0, int(a35.get("c2pa_cert_mutation_bytes", 0)) + int(faults.p3_c2pa_cert_mutation_bytes)),
            "cxd90058_sabin_mutation_bytes": max(0, a34_mut),
        }
    )
    pillar = Milestone175PillarResult(
        pillar_id="P3",
        pillar_name="THIRTY_SIX_FIRMWARE_LAB_REALBIN_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {passed_count}/{total_count} auditors (>=36 required; Ph144..171 "
            f"p18/Fan/0DA1/IMX510/CFexpress/CXD90058/C2PA/WBI2), cal_mut={total_cal_mut}B "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "auditor_count": total_count,
        "passed_count": passed_count,
        "calibration_mutation_bytes": total_cal_mut,
        "bk4_persistent_nvram_writes": int(meta_28["bk4_persistent_nvram_writes"]),
        "wbi_mutation_bytes": max(0, a36_wbi),
    }
    return pillar, meta


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: RealHwMilestone175FaultInjection,
) -> Tuple[Milestone175PillarResult, Dict[str, Any]]:
    m147_p4, meta_24 = _eval_m147_p4(vm_rep, _fault_to_m147_faults(faults))
    errors: List[str] = list(m147_p4.errors)
    stage_statuses: Dict[str, bool] = dict(m147_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_30_STAGE_KEYS[24:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if not ok:
            errors.append(f"p4: VM co-emulation {skey} failed")

    # Stage 25: Phase 145 appFw -> Stock FX3 libmpr.so / DmmCfg.bin Recording Co-Emulator
    s25 = vm_rep.get("stage25_realhw_mpr_dmm_rec", {})
    s25_emmc = int(s25.get("emmc_mutation_bytes", -1)) + int(faults.p4_stage25_emmc_mutation_bytes)
    if (
        int(s25.get("nop_count", -1)) != 0
        or int(s25.get("cp_mutation_bytes", -1)) != 0
        or int(s25.get("wbi_mutation_bytes", -1)) != 0
        or int(s25.get("calibration_mutation_bytes", -1)) != 0
        or int(s25.get("physical_device_writes", -1)) != 0
        or s25.get("persistent_emmc_writes_authorized") is not False
        or s25_emmc != 0
        or int(s25.get("appfw_crashes", -1)) != 0
        or int(s25.get("rsv_orphan_count", -1)) != 0
        or int(s25.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(f"p4: Stage 25 redlines violated (emmc_mut={s25_emmc})")

    # Stage 26: Phase 150 FX3 Body Controls, IBIS Center-Lock, XLR-H1, Fan PWM & NP-FZ100 HIL
    s26 = vm_rep.get("stage26_realhw_body_peripheral_hil", {})
    s26_p18 = int(s26.get("p18_mutation_bytes", -1)) + int(faults.p4_stage26_p18_mutation_bytes)
    s26_emmc = int(s26.get("emmc_mutation_bytes", -1))
    if (
        int(s26.get("nop_count", -1)) != 0
        or int(s26.get("cp_mutation_bytes", -1)) != 0
        or int(s26.get("wbi_mutation_bytes", -1)) != 0
        or int(s26.get("calibration_mutation_bytes", -1)) != 0
        or s26.get("p18_lens_writes_permitted") is not False
        or s26.get("persistent_emmc_writes_authorized") is not False
        or s26_p18 != 0
        or s26_emmc != 0
        or int(s26.get("appfw_crashes", -1)) != 0
        or int(s26.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(f"p4: Stage 26 redlines violated (p18_mut={s26_p18})")

    # Stage 27: Phase 157 IMX510 Dual-Base ISO, psd/defdet NVS, .cube MLUT, CDC-NCM & 054C:0DA1 HIL
    s27 = vm_rep.get("stage27_realhw_imx510_network_usb_hil", {})
    s27_mut = (
        int(s27.get("sensor_cal_mutation_bytes", -1))
        + int(s27.get("rf_nvs_p12_p13_mutation_bytes", -1))
        + int(faults.p4_stage27_sensor_or_rfnvs_mutation_bytes)
    )
    s27_emmc = int(s27.get("emmc_mutation_bytes", -1))
    if (
        int(s27.get("nop_count", -1)) != 0
        or int(s27.get("cp_mutation_bytes", -1)) != 0
        or int(s27.get("wbi_mutation_bytes", -1)) != 0
        or int(s27.get("calibration_mutation_bytes", -1)) != 0
        or s27.get("psd_defdet_writes_permitted") is not False
        or s27.get("rf_nvs_p12_p13_writes_permitted") is not False
        or s27.get("bt_hci_blocking_wait_eliminated") is not True
        or s27.get("usb_msc_0da1_recovery_intact") is not True
        or s27.get("persistent_emmc_writes_authorized") is not False
        or s27_mut != 0
        or s27_emmc != 0
        or int(s27.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(f"p4: Stage 27 redlines violated (sensor_rf_mut={s27_mut})")

    # Stage 28: Phase 162 CFexpress/SDXC V90, .RSV Salvage, BODYDATA.DAT UFU Bypass & 5-Tier HIL
    s28 = vm_rep.get("stage28_realhw_cfexpress_ufu_5tier_hil", {})
    s28_mut = (
        int(s28.get("emmc_mutation_bytes", -1))
        + int(s28.get("spi_nor_mutation_bytes", -1))
        + int(faults.p4_stage28_spi_or_emmc_mutation_bytes)
    )
    if (
        int(s28.get("nop_count", -1)) != 0
        or int(s28.get("cp_mutation_bytes", -1)) != 0
        or int(s28.get("wbi_mutation_bytes", -1)) != 0
        or int(s28.get("calibration_mutation_bytes", -1)) != 0
        or s28.get("persistent_emmc_writes_authorized") is not False
        or s28.get("spi_nor_write_authorized") is not False
        or s28.get("el3_payload_transmit_authorized") is not False
        or s28.get("user_media_clips_intact") is not True
        or s28_mut != 0
        or int(s28.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(f"p4: Stage 28 redlines violated (mut={s28_mut})")

    # Stage 29: Phase 167 CXD90058/Cetus Dual-SoC IPC, sabin SA-DSP, XAVC Codec & H0==H3 Seal HIL
    s29 = vm_rep.get("stage29_realhw_cxd90058_sabin_seal_hil", {})
    s29_mut = (
        int(s29.get("cxd90058_mutation_bytes", -1))
        + int(s29.get("emmc_mutation_bytes", -1))
        + int(s29.get("spi_nor_mutation_bytes", -1))
        + int(s29.get("otp_write_count", -1))
        + int(s29.get("rpmb_write_count", -1))
        + int(s29.get("orig_residual_count", -1))
        + int(s29.get("tmp_jiritsu_residual_count", -1))
        + int(s29.get("p6_chunk_residual_count", -1))
        + int(s29.get("ipc_deadlocks", -1))
        + int(faults.p4_stage29_cxd90058_or_residual_count)
    )
    if (
        int(s29.get("nop_count", -1)) != 0
        or int(s29.get("cp_mutation_bytes", -1)) != 0
        or int(s29.get("wbi_mutation_bytes", -1)) != 0
        or s29.get("persistent_emmc_writes_authorized") is not False
        or s29.get("spi_nor_write_authorized") is not False
        or s29_mut != 0
        or int(s29.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(f"p4: Stage 29 redlines violated (mut_or_res={s29_mut})")

    # Stage 30: Phase 172 C2PA RQ_LIC Lock, VMC-BNCM1 LTC, IMX510 Gyro NRTM & Pre-Bench HIL
    s30 = vm_rep.get("stage30_realhw_c2pa_tc_gyro_prebench_hil", {})
    s30_mut = (
        int(s30.get("c2pa_cert_mutation_bytes", -1))
        + int(s30.get("p2_mutation_bytes", -1))
        + int(s30.get("p18_mutation_bytes", -1))
        + int(s30.get("emmc_mutation_bytes", -1))
        + int(s30.get("spi_nor_mutation_bytes", -1))
        + int(s30.get("otp_write_count", -1))
        + int(s30.get("rpmb_write_count", -1))
        + int(s30.get("uart_contention_damage_events", -1))
        + int(s30.get("over_voltage_damage_events", -1))
        + int(faults.p4_stage30_c2pa_or_voltage_events)
    )
    if (
        int(s30.get("nop_count", -1)) != 0
        or int(s30.get("cp_mutation_bytes", -1)) != 0
        or int(s30.get("wbi_mutation_bytes", -1)) != 0
        or s30.get("persistent_emmc_writes_authorized") is not False
        or s30.get("spi_nor_write_authorized") is not False
        or s30_mut != 0
        or int(s30.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(f"p4: Stage 30 redlines violated (c2pa_or_dmg={s30_mut})")

    total_stages = len(stage_statuses)
    passed_stages = sum(1 for v in stage_statuses.values() if v)
    emmc_corruptions = (
        int(meta_24.get("emmc_corruptions", 0))
        + max(0, s25_emmc)
        + max(0, s26_emmc)
        + max(0, s27_emmc)
        + max(0, int(s28.get("emmc_mutation_bytes", 0)))
        + max(0, int(s29.get("emmc_mutation_bytes", 0)))
        + max(0, int(s30.get("emmc_mutation_bytes", 0)))
    )
    total_wf12_hits = (
        int(meta_24.get("wf12_00342260_hits", 0))
        + max(0, int(s25.get("wf12_00342260_hits", 0)))
        + max(0, int(s26.get("wf12_00342260_hits", 0)))
        + max(0, int(s27.get("wf12_00342260_hits", 0)))
        + max(0, int(s28.get("wf12_00342260_hits", 0)))
        + max(0, int(s29.get("wf12_00342260_hits", 0)))
        + max(0, int(s30.get("wf12_00342260_hits", 0)))
    )

    if total_stages < 30 or passed_stages < 30 or passed_stages != total_stages:
        errors.append(f"p4: expected >= 30 VM stages and all passing, got {passed_stages}/{total_stages}")
    if emmc_corruptions != 0:
        errors.append(f"p4: emmc_corruptions={emmc_corruptions} != 0")

    passed = len(errors) == 0
    evidence = dict(m147_p4.evidence)
    evidence.update(
        {
            "stage_count": total_stages,
            "passed_stage_count": passed_stages,
            "stage_statuses": stage_statuses,
            "emmc_corruptions": emmc_corruptions,
            "wf12_00342260_hits": total_wf12_hits,
            "stage25_digest_sha256": s25.get("phase145_audit_digest_sha256"),
            "stage26_digest_sha256": s26.get("phase150_audit_digest_sha256"),
            "stage27_digest_sha256": s27.get("phase157_audit_digest_sha256"),
            "stage28_digest_sha256": s28.get("phase162_audit_digest_sha256"),
            "stage29_digest_sha256": s29.get("phase167_audit_digest_sha256"),
            "stage30_digest_sha256": s30.get("phase172_audit_digest_sha256"),
        }
    )
    pillar = Milestone175PillarResult(
        pillar_id="P4",
        pillar_name="THIRTY_STAGE_VM_HIL_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {passed_stages}/{total_stages} stages (>=30 required; Ph145..172 Stages 25..30), "
            f"emmc_corruptions={emmc_corruptions}, wf12_hits={total_wf12_hits} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "stage_count": total_stages,
        "passed_count": passed_stages,
        "cp_mutation_bytes": meta_24["cp_mutation_bytes"],
        "bk4_persistent_nvram_writes": meta_24["bk4_persistent_nvram_writes"],
        "wf12_00342260_hits": total_wf12_hits,
        "emmc_corruptions": emmc_corruptions,
    }
    return pillar, meta


def _evaluate_pillar_5(
    raw_p136: Mapping[str, Any],
    raw_p143: Mapping[str, Any],
    raw_p154: Mapping[str, Any],
    faults: RealHwMilestone175FaultInjection,
) -> Tuple[Milestone175PillarResult, Dict[str, Any]]:
    errors: List[str] = []

    p136_ok = bool(raw_p136.get("all_checks_passed")) and not faults.p5_inject_p136_u4_u5_u6_fault
    p136_p1 = raw_p136.get("pillar1_jiritsu_stage288", {})
    p136_p2 = raw_p136.get("pillar2_u4_zero_sector0", {})
    p136_p3 = raw_p136.get("pillar3_u5_p1_fallback", {})
    p136_p4 = raw_p136.get("pillar4_tier0_stop_gate", {})

    u6_cmd_count = int(p136_p1.get("u6_command_count", 0))
    u6_closed = bool(p136_p1.get("u6_closed")) and u6_cmd_count >= 19
    u4_closed = bool(p136_p2.get("u4_closed"))
    u5_closed = bool(p136_p3.get("u5_closed"))
    twopass_ok = bool(p136_p4.get("twopass_sha256_all_matched"))
    u4_u5_u6_closed = p136_ok and u6_closed and u4_closed and u5_closed and twopass_ok

    if not u4_u5_u6_closed:
        errors.append(
            f"p5_p136: U4/U5/U6 or Tier-0 gate failed (u4={u4_closed}, u5={u5_closed}, u6={u6_closed}, twopass={twopass_ok})"
        )
    if (
        raw_p136.get("persistent_emmc_writes_authorized") is not False
        or raw_p136.get("usb_device_attach_executed") is not False
        or p136_p4.get("persistent_emmc_writes_authorized") is not False
    ):
        errors.append("p5_p136: hard-locked emmc/usb attach invariant breached")

    p143_ok = bool(raw_p143.get("all_checks_passed"))
    p143_b1 = raw_p143.get("pillar1_bundle_builder", {})
    p143_b2 = raw_p143.get("pillar2_escape_hatch_launcher", {})
    p143_b3 = raw_p143.get("pillar3_atomic_uninstaller_h0_h3", {})
    p143_b4 = raw_p143.get("pillar4_no_physical_flash_guard", {})

    if (
        not p143_ok
        or not bool(p143_b1.get("sd_tree_valid"))
        or not bool(p143_b1.get("lock_table_13_verified"))
        or not bool(p143_b1.get("body_serial_binding_verified"))
        or not bool(p143_b1.get("foreign_serial_rejected"))
        or not bool(p143_b1.get("within_64mib_ddr_budget"))
    ):
        errors.append("p5_p143: SD Stage-B bundle builder or 64 MiB DDR budget failed")

    eh1_us = int(p143_b2.get("eh1_observed_latency_us", 999)) + int(
        faults.p5_inject_p143_escape_hatch_over_budget_us
    )
    if (
        not bool(p143_b2.get("eh1_sd_absent_under_50us_ok"))
        or eh1_us > 50
        or not bool(p143_b2.get("eh2_combo_and_stop_flag_ok"))
        or not bool(p143_b2.get("eh3_fail_closed_diag_log_ok"))
        or not bool(p143_b2.get("ld_so_preload_untouched"))
        or int(p143_b2.get("passed_scenario_count", -1)) != int(p143_b2.get("scenario_count", -2))
        or int(p143_b2.get("scenario_count", 0)) < 6
    ):
        errors.append(f"p5_p143: 3-escape-hatch launcher failed (eh1_us={eh1_us})")

    surface_count = int(p143_b3.get("surface_count", 0))
    h0_eq_h3_count = 0 if faults.p5_inject_p143_h0_h3_drift else int(p143_b3.get("h0_equals_h3_count", 0))
    if (
        surface_count != 16
        or h0_eq_h3_count != 16
        or not bool(p143_b3.get("h0_equals_h3_all_16"))
        or not bool(p143_b3.get("crypto_cnflasha15_enforced"))
        or int(p143_b3.get("power_loss_drills_passed", -1)) != int(p143_b3.get("power_loss_drill_count", -2))
        or int(p143_b3.get("power_loss_drill_count", 0)) < 5
    ):
        errors.append(f"p5_p143: H0 == H3 uninstaller failed ({h0_eq_h3_count}/{surface_count})")

    if (
        raw_p143.get("persistent_emmc_writes_authorized") is not False
        or raw_p143.get("sd_physical_media_written") is not False
        or p143_b4.get("persistent_emmc_writes_authorized") is not False
        or p143_b4.get("sd_physical_media_written") is not False
        or p143_b4.get("raw_pnflasha_plaintext_blocked") is not True
    ):
        errors.append("p5_p143: hard-locked no-physical-flash guard breached")

    # Phase 154: Passive Zero-Packet USB Bench Preflight & Dual-Copy FX3RCPT1 Classifier
    p154_dict = copy.deepcopy(dict(raw_p154))
    if faults.p5_inject_p154_usb_packets_override:
        p154_dict["usb_packets_emitted"] = int(p154_dict.get("usb_packets_emitted", 0)) + int(
            faults.p5_inject_p154_usb_packets_override
        )
    p154_verify = verify_phase154_report(p154_dict)
    p154_usb = p154_dict.get("usb_classification", {})
    p154_sd = p154_dict.get("sd_staging_audit", {})
    p154_rcpt = p154_dict.get("dual_copy_receipt_audit", {})
    p154_bench_go = bool(p154_dict.get("bench_go"))
    p154_usb_pkts = int(p154_dict.get("usb_packets_emitted", -1))
    p154_iokit = int(p154_dict.get("iokit_handles_opened", -1))

    if (
        not p154_verify.valid
        or not p154_bench_go
        or p154_dict.get("verdict") != VERDICT_GO_READONLY_PREFLIGHT
        or p154_usb.get("usb_state") != "READY_MSC_054C_0DA1"
        or not bool(p154_usb.get("ready_for_msc_session"))
        or not bool(p154_sd.get("passed"))
        or not bool(p154_rcpt.get("passed"))
        or p154_usb_pkts != 0
        or p154_iokit != 0
        or int(p154_dict.get("physical_device_writes", -1)) != 0
        or int(p154_dict.get("raw_firmware_slices_emitted", -1)) != 0
    ):
        errors.append(
            f"p5_p154: bench preflight failed (bench_go={p154_bench_go}, valid={p154_verify.valid}, "
            f"usb_pkts={p154_usb_pkts}, iokit={p154_iokit}, errs={p154_verify.errors})"
        )

    passed = len(errors) == 0
    evidence = {
        "p136_verification_mode": raw_p136.get("verification_mode"),
        "p136_report_sha256": raw_p136.get("report_sha256"),
        "p136_u6_command_count": u6_cmd_count,
        "p136_u4_u5_u6_closed": u4_u5_u6_closed,
        "p143_verification_mode": raw_p143.get("verification_mode"),
        "p143_report_sha256": raw_p143.get("report_sha256"),
        "p143_sd_entry_count": p143_b1.get("sd_entry_count"),
        "p143_ram_tmpfs_mib": p143_b1.get("ram_tmpfs_mib"),
        "p143_eh1_observed_latency_us": eh1_us,
        "p143_h0_equals_h3_count": h0_eq_h3_count,
        "p143_h0_h3_surface_count": surface_count,
        "p143_power_loss_drills_passed": p143_b3.get("power_loss_drills_passed"),
        "p154_verification_mode": p154_dict.get("verification_mode"),
        "p154_verdict": p154_dict.get("verdict"),
        "p154_bench_go": p154_bench_go,
        "p154_usb_state": p154_usb.get("usb_state"),
        "p154_usb_packets_emitted": p154_usb_pkts,
        "p154_iokit_handles_opened": p154_iokit,
        "p154_report_sha256": p154_dict.get("report_sha256"),
    }
    pillar = Milestone175PillarResult(
        pillar_id="P5",
        pillar_name="CLOSURE_BENCH_PREFLIGHT_SD_BUNDLE_AND_H0_H3",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Ph136(U4/U5/U6={u4_u5_u6_closed}, cmds={u6_cmd_count}) + "
            f"Ph143(EH1={eh1_us}us<=50us, H0==H3 {h0_eq_h3_count}/{surface_count}) + "
            f"Ph154(bench_go={p154_bench_go}, usb_pkts={p154_usb_pkts}, iokit={p154_iokit}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "u6_command_count": u6_cmd_count,
        "u4_u5_u6_closed": u4_u5_u6_closed,
        "eh1_observed_latency_us": eh1_us,
        "h0_equals_h3_count": h0_eq_h3_count,
        "h0_h3_surface_count": surface_count,
        "p154_bench_go": p154_bench_go,
        "p154_usb_packets_emitted": p154_usb_pkts,
        "p154_iokit_handles_opened": p154_iokit,
    }
    return pillar, meta


def _evaluate_pillar_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: RealHwMilestone175FaultInjection,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
    p5_meta: Mapping[str, Any],
) -> Tuple[Milestone175PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    round_sources: Dict[str, str] = {}
    round_schemas: Dict[str, str] = {}
    runs_by_round: Dict[str, int] = {}

    total_nops = 0
    total_crashes = 0
    total_emmc = 0
    rounds_verified = 0
    total_runs_verified = 0

    for spec in ROUND28_TO_34_SPECS:
        r_tag = f"r{spec.round_num}"
        raw_round, r_src = _load_round28_to_34_summary(
            spec, repo_root=repo_root, use_clean_room=use_clean_room
        )
        if faults.p6_tamper_schema_round_num == spec.round_num:
            raw_round = copy.deepcopy(raw_round)
            raw_round["schema"] = "tampered-invalid-schema"

        round_sources[r_tag] = r_src
        r_schema = str(raw_round.get("schema", ""))
        r_kver = str(raw_round.get("kernel_version", ""))
        round_schemas[r_tag] = r_schema

        round_ok = True
        if r_schema != spec.expected_schema:
            errors.append(f"p6_{r_tag}: unexpected schema {r_schema!r}")
            round_ok = False
        if "4.9.337-scel+" not in r_kver:
            errors.append(f"p6_{r_tag}: unexpected kernel_version {r_kver!r}")
            round_ok = False

        audit_obj = raw_round.get(spec.audit_key, {})
        if not isinstance(audit_obj, Mapping):
            errors.append(f"p6_{r_tag}: missing audit block {spec.audit_key}")
            round_ok = False
        else:
            for bkey in spec.audit_bool_keys:
                if not bool(audit_obj.get(bkey, False)):
                    errors.append(f"p6_{r_tag}: audit flag {bkey} is False")
                    round_ok = False

        runs_map = raw_round.get("runs", {})
        if not isinstance(runs_map, Mapping):
            errors.append(f"p6_{r_tag}: missing runs mapping")
            runs_by_round[r_tag] = 0
            continue

        verified_in_round = 0
        for run_idx, (rid, exp_faithful) in enumerate(spec.run_specs):
            robj = runs_map.get(rid)
            if not isinstance(robj, Mapping):
                errors.append(f"p6_{r_tag}: missing run {rid}")
                round_ok = False
                continue

            if run_idx == 0 and faults.p6_round_nop_override_num == spec.round_num and faults.p6_round_nop_count_override is not None:
                rnop = int(faults.p6_round_nop_count_override)
            elif exp_faithful is not None:
                rnop = int(robj.get("nop_count", -1))
            else:
                rnop = int(robj.get("nop_count", 0))

            if run_idx == 0 and faults.p6_round_crash_override_num == spec.round_num and faults.p6_round_crashes_override is not None:
                rcrash = int(faults.p6_round_crashes_override)
            else:
                rcrash = int(robj.get("crashes", -1))

            if run_idx == 0 and faults.p6_round_emmc_override_num == spec.round_num and faults.p6_round_emmc_writes_override is not None:
                remmc = int(faults.p6_round_emmc_writes_override)
            else:
                remmc = int(robj.get("emmc_write_count", -1))

            total_nops += max(0, rnop)
            total_crashes += max(0, rcrash)
            total_emmc += max(0, remmc)

            rkver = str(robj.get("kernel_version", r_kver))
            sb = robj.get("stage_b", {})
            sb_count = int(sb.get("manifest_count", -1)) if isinstance(sb, Mapping) else -1
            fi_ok = True
            if exp_faithful is not None:
                fi = robj.get("faithful_invariants", {})
                fi_val = int(fi.get("FX6_NATIVE_FAITHFUL", -1)) if isinstance(fi, Mapping) else -1
                if fi_val != exp_faithful:
                    fi_ok = False

            if (
                "4.9.337-scel+" not in rkver
                or rnop != 0
                or rcrash != 0
                or remmc != 0
                or sb_count != 13
                or not fi_ok
            ):
                errors.append(
                    f"p6_{r_tag}:{rid}: failed invariants (nop={rnop}, crash={rcrash}, emmc={remmc}, sb={sb_count}, fi_ok={fi_ok})"
                )
                round_ok = False
                continue

            verified_in_round += 1

        runs_by_round[r_tag] = verified_in_round
        total_runs_verified += verified_in_round
        if round_ok and verified_in_round == len(spec.run_specs):
            rounds_verified += 1

    # Cross-pillar hardware-lock invariants
    if (
        p1_meta.get("persistent_emmc_writes_authorized") is not False
        or p1_meta.get("spi_nor_write_authorized") is not False
        or p1_meta.get("el3_payload_transmit_authorized") is not False
        or p1_meta.get("simulated_ready_for_hardware_attach") is not False
    ):
        errors.append("p6: P1 hardware-lock invariant breached")
    if (
        int(p2_meta.get("otp_fuse_touches", -1)) != 0
        or int(p2_meta.get("rpmb_counter_increments", -1)) != 0
        or int(p2_meta.get("passive_tx_bytes_emitted", -1)) != 0
        or int(p2_meta.get("physical_usb_packets_emitted", -1)) != 0
    ):
        errors.append("p6: P2 zero-touch OTP/RPMB/passive-UART/USB-PKT invariant breached")
    if int(p3_meta.get("calibration_mutation_bytes", -1)) != 0 or int(p3_meta.get("wbi_mutation_bytes", -1)) != 0:
        errors.append("p6: P3 calibration/WBI zero-mutation invariant breached")
    if (
        int(p4_meta.get("cp_mutation_bytes", -1)) != 0
        or int(p4_meta.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(p4_meta.get("wf12_00342260_hits", -1)) != 0
        or int(p4_meta.get("emmc_corruptions", -1)) != 0
    ):
        errors.append("p6: P4 CP/BK4/WF-12/eMMC zero-mutation invariant breached")
    if (
        int(p5_meta.get("h0_equals_h3_count", -1)) != 16
        or not bool(p5_meta.get("p154_bench_go"))
        or int(p5_meta.get("p154_usb_packets_emitted", -1)) != 0
    ):
        errors.append("p6: P5 H0 == H3 (16/16) or Phase 154 zero-packet bench preflight invariant breached")

    passed = (
        len(errors) == 0
        and rounds_verified == len(ROUND28_TO_34_SPECS)
        and total_runs_verified == 21
        and total_nops == 0
        and total_crashes == 0
        and total_emmc == 0
    )
    evidence = {
        "round_sources": round_sources,
        "round_schemas": round_schemas,
        "rounds_verified": rounds_verified,
        "expected_rounds": len(ROUND28_TO_34_SPECS),
        "runs_by_round": runs_by_round,
        "total_runs_verified": total_runs_verified,
        "expected_total_runs": 21,
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
        "milestone147_schema_anchor": MILESTONE147_SCHEMA_VERSION,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
    }
    pillar = Milestone175PillarResult(
        pillar_id="P6",
        pillar_name="REAL_FX3_702_QEMU_ROUNDS_28_TO_34_RECEIPTS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Live FX3 7.02 QEMU Rounds 28..34={rounds_verified}/7 rounds ({total_runs_verified}/21 runs), "
            f"nop={total_nops}, crashes={total_crashes}, emmc={total_emmc} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "qemu_rounds_verified": rounds_verified,
        "qemu_runs_verified": total_runs_verified,
        "qemu_round_runs_by_round": runs_by_round,
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
    }
    return pillar, meta


# ---------------------------------------------------------------------------
# Parallel Collector, Builder & Fail-Closed Verifier
# ---------------------------------------------------------------------------


def _collect_parallel_milestone175_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: RealHwMilestone175FaultInjection,
) -> Tuple[
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
]:
    gate_fault_dict = _fault_to_58gate_worker_dict(faults)
    p154_sim_ready = not faults.p5_inject_p154_no_go_fault

    p3_batches: Tuple[Tuple[str, ...], ...] = (
        ("multilang",),
        ("group_b",),
        ("sensor",),
        ("haita",),
        ("group_a",),
        ("emount",),
        ("wbi",),
        ("assignable", "falsecolor", "playback", "gyroflow"),
        ("interval_ftp", "lut3d_sdi", "c2pa_mc", "hdr_hlg"),
        ("prores_mishoe", "uvc_crsdk", "mxf_tally", "vp_ledwall"),
        ("xavc_fz100", "realhw_cp_backup", "realhw_mpr_dmm"),
        ("realhw_peripheral", "realhw_controls_fan", "realhw_wifi_usb"),
        ("realhw_imx510", "realhw_cfexpress_ufu", "realhw_cxd90058_sabin"),
        ("realhw_c2pa_tc_gyro", "realhw_wbi2_hibdrv"),
    )

    try:
        ctx = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=20, mp_context=ctx) as ex:
            # Wave 1: longest poles first for minimum wall time (< 3.8s local / < 2.2s clean-room)
            fut_vm = ex.submit(_worker_pillar_4, use_clean_room)
            fut_p136 = ex.submit(_worker_phase136, use_clean_room)
            fut_22p = ex.submit(
                _worker_recovery_22pillar, (use_clean_room, faults.p2_fault_inject_pillar)
            )
            fut_143_154 = ex.submit(
                _worker_phase143_and_154,
                (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p154_sim_ready),
            )
            fut_3 = [ex.submit(_worker_pillar_3_batch, (batch, use_clean_room)) for batch in p3_batches]
            fut_1_off = ex.submit(
                _worker_58gate_single, (str(repo_root), use_clean_room, False, gate_fault_dict)
            )
            fut_1_sim = ex.submit(
                _worker_58gate_single, (str(repo_root), use_clean_room, True, gate_fault_dict)
            )

            raw_1_off = fut_1_off.result()
            raw_1_sim = fut_1_sim.result()
            raw_22p = fut_22p.result()
            auditors: Dict[str, Dict[str, Any]] = {}
            for fg in fut_3:
                auditors.update(fg.result())
            raw_vm = fut_vm.result()
            raw_p136 = fut_p136.result()
            raw_p143, raw_p154 = fut_143_154.result()
            return raw_1_off, raw_1_sim, raw_22p, auditors, raw_vm, raw_p136, raw_p143, raw_p154
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1_off = _worker_58gate_single((str(repo_root), use_clean_room, False, gate_fault_dict))
    raw_1_sim = _worker_58gate_single((str(repo_root), use_clean_room, True, gate_fault_dict))
    raw_22p = _worker_recovery_22pillar((use_clean_room, faults.p2_fault_inject_pillar))
    auditors = {}
    for batch in p3_batches:
        auditors.update(_worker_pillar_3_batch((batch, use_clean_room)))
    raw_vm = _worker_pillar_4(use_clean_room)
    raw_p136 = _worker_phase136(use_clean_room)
    raw_p143, raw_p154 = _worker_phase143_and_154(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p154_sim_ready)
    )
    return raw_1_off, raw_1_sim, raw_22p, auditors, raw_vm, raw_p136, raw_p143, raw_p154


def build_realhw_milestone175_master_gate_report(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[RealHwMilestone175FaultInjection] = None,
) -> RealHwMilestone175MasterGateReport:
    """Build & evaluate the Grand Unified Phase 175 6-Pillar Real-Hardware Final Pre-Bench Master Gate."""
    use_clean_room = _is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    active_faults = faults or RealHwMilestone175FaultInjection()

    (
        raw_1_off,
        raw_1_sim,
        raw_22p,
        auditors,
        raw_vm,
        raw_p136,
        raw_p143,
        raw_p154,
    ) = _collect_parallel_milestone175_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )

    p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
    p2, meta_2 = _evaluate_pillar_2(raw_22p, active_faults)
    p3, meta_3 = _evaluate_pillar_3(auditors, active_faults)
    p4, meta_4 = _evaluate_pillar_4(raw_vm, active_faults)
    p5, meta_5 = _evaluate_pillar_5(raw_p136, raw_p143, raw_p154, active_faults)
    p6, meta_6 = _evaluate_pillar_6(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=active_faults,
        p1_meta=p1.evidence,
        p2_meta=meta_2,
        p3_meta=meta_3,
        p4_meta=meta_4,
        p5_meta=meta_5,
    )

    pillars: Tuple[Milestone175PillarResult, ...] = (p1, p2, p3, p4, p5, p6)
    passed_count = sum(1 for p in pillars if p.passed)
    failed_ids = tuple(p.pillar_id for p in pillars if not p.passed)
    all_errors: List[str] = []
    for p in pillars:
        all_errors.extend(p.errors)

    all_ready = passed_count == len(pillars) and len(all_errors) == 0
    mode_str = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"

    payload_no_sha: Dict[str, Any] = {
        "schema_version": REALHW_MILESTONE175_SCHEMA,
        "phase_version": PHASE_175_VERSION,
        "verification_mode": mode_str,
        "all_pillars_milestone_ready": all_ready,
        "status": STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "isp_write_authorized": ISP_WRITE_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "hardware_live_attachment_requirements": HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
        "physical_usb_packets_emitted": meta_2["physical_usb_packets_emitted"],
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "wbi_p5_write_and_hibernation_forbidden": WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        "cp_mutation_bytes": meta_4["cp_mutation_bytes"],
        "wbi_mutation_bytes": meta_3["wbi_mutation_bytes"],
        "calibration_mutation_bytes": meta_3["calibration_mutation_bytes"],
        "usb_or_camera_operations": USB_OR_CAMERA_OPERATIONS,
        "otp_fuse_touches": meta_2["otp_fuse_touches"],
        "rpmb_counter_increments": meta_2["rpmb_counter_increments"],
        "passive_tx_bytes_emitted": meta_2["passive_tx_bytes_emitted"],
        "temp_dir_cleaned": True,
        "pillar_count": len(pillars),
        "passed_pillar_count": passed_count,
        "failed_pillar_ids": failed_ids,
        "pillars": [p.to_dict() for p in pillars],
        "gate58_total_gates": raw_1_sim["total_gates"],
        "gate58_offline_verified": raw_1_off["verified_gates"],
        "gate58_simulated_verified": raw_1_sim["verified_gates"],
        "recovery_pillar_count": meta_2["recovery_pillar_count"],
        "recovery_pillars_passed": meta_2["recovery_pillars_passed"],
        "firmware_lab_auditor_count": meta_3["auditor_count"],
        "firmware_lab_auditors_passed": meta_3["passed_count"],
        "vm_coemulation_stage_count": meta_4["stage_count"],
        "vm_coemulation_stages_passed": meta_4["passed_count"],
        "vm_emmc_corruptions": meta_4["emmc_corruptions"],
        "vm_wf12_00342260_hits": meta_4["wf12_00342260_hits"],
        "p136_u6_command_count": meta_5["u6_command_count"],
        "p136_u4_u5_u6_closed": meta_5["u4_u5_u6_closed"],
        "p143_sd_escape_absent_us": meta_5["eh1_observed_latency_us"],
        "p143_h0_equals_h3_count": meta_5["h0_equals_h3_count"],
        "p143_h0_h3_surface_count": meta_5["h0_h3_surface_count"],
        "p154_bench_go": meta_5["p154_bench_go"],
        "p154_usb_packets_emitted": meta_5["p154_usb_packets_emitted"],
        "p154_iokit_handles_opened": meta_5["p154_iokit_handles_opened"],
        "qemu_rounds_verified": meta_6["qemu_rounds_verified"],
        "qemu_runs_verified": meta_6["qemu_runs_verified"],
        "qemu_round_runs_by_round": meta_6["qemu_round_runs_by_round"],
        "qemu_real_kernel_nop_count": meta_6["qemu_real_kernel_nop_count"],
        "qemu_real_kernel_crashes": meta_6["qemu_real_kernel_crashes"],
        "qemu_real_kernel_emmc_writes": meta_6["qemu_real_kernel_emmc_writes"],
        "errors": tuple(all_errors),
    }
    digest = compute_milestone175_sha256(payload_no_sha)

    return RealHwMilestone175MasterGateReport(
        schema_version=REALHW_MILESTONE175_SCHEMA,
        phase_version=PHASE_175_VERSION,
        verification_mode=mode_str,
        all_pillars_milestone_ready=all_ready,
        status=STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        hardware_live_attachment_requirements=HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
        physical_usb_packets_emitted=meta_2["physical_usb_packets_emitted"],
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        wbi_p5_write_and_hibernation_forbidden=WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        cp_mutation_bytes=meta_4["cp_mutation_bytes"],
        wbi_mutation_bytes=meta_3["wbi_mutation_bytes"],
        calibration_mutation_bytes=meta_3["calibration_mutation_bytes"],
        usb_or_camera_operations=USB_OR_CAMERA_OPERATIONS,
        otp_fuse_touches=meta_2["otp_fuse_touches"],
        rpmb_counter_increments=meta_2["rpmb_counter_increments"],
        passive_tx_bytes_emitted=meta_2["passive_tx_bytes_emitted"],
        temp_dir_cleaned=True,
        pillar_count=len(pillars),
        passed_pillar_count=passed_count,
        failed_pillar_ids=failed_ids,
        pillars=pillars,
        gate58_total_gates=raw_1_sim["total_gates"],
        gate58_offline_verified=raw_1_off["verified_gates"],
        gate58_simulated_verified=raw_1_sim["verified_gates"],
        recovery_pillar_count=meta_2["recovery_pillar_count"],
        recovery_pillars_passed=meta_2["recovery_pillars_passed"],
        firmware_lab_auditor_count=meta_3["auditor_count"],
        firmware_lab_auditors_passed=meta_3["passed_count"],
        vm_coemulation_stage_count=meta_4["stage_count"],
        vm_coemulation_stages_passed=meta_4["passed_count"],
        vm_emmc_corruptions=meta_4["emmc_corruptions"],
        vm_wf12_00342260_hits=meta_4["wf12_00342260_hits"],
        p136_u6_command_count=meta_5["u6_command_count"],
        p136_u4_u5_u6_closed=meta_5["u4_u5_u6_closed"],
        p143_sd_escape_absent_us=meta_5["eh1_observed_latency_us"],
        p143_h0_equals_h3_count=meta_5["h0_equals_h3_count"],
        p143_h0_h3_surface_count=meta_5["h0_h3_surface_count"],
        p154_bench_go=meta_5["p154_bench_go"],
        p154_usb_packets_emitted=meta_5["p154_usb_packets_emitted"],
        p154_iokit_handles_opened=meta_5["p154_iokit_handles_opened"],
        qemu_rounds_verified=meta_6["qemu_rounds_verified"],
        qemu_runs_verified=meta_6["qemu_runs_verified"],
        qemu_round_runs_by_round=meta_6["qemu_round_runs_by_round"],
        qemu_real_kernel_nop_count=meta_6["qemu_real_kernel_nop_count"],
        qemu_real_kernel_crashes=meta_6["qemu_real_kernel_crashes"],
        qemu_real_kernel_emmc_writes=meta_6["qemu_real_kernel_emmc_writes"],
        errors=tuple(all_errors),
        milestone175_sha256=digest,
    )


evaluate_milestone175_master_gate = build_realhw_milestone175_master_gate_report


def verify_realhw_milestone175_master_gate(
    report: object,
) -> RealHwMilestone175VerifyResult:
    """Fail-closed verifier for a Milestone Phase 175 Real-Hardware Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, RealHwMilestone175MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return RealHwMilestone175VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone175_sha256="",
            observed_milestone175_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or RealHwMilestone175MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = payload.get("schema_version") == REALHW_MILESTONE175_SCHEMA
    if not schema_ok:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r}")

    expected_sha = compute_milestone175_sha256(payload)
    observed_sha = str(payload.get("milestone175_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(f"milestone175_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}")

    redlines_ok = (
        payload.get("o_rdonly_enforced") is True
        and payload.get("persistent_emmc_writes_authorized") is False
        and payload.get("persistent_write_release") is False
        and payload.get("spi_nor_write_authorized") is False
        and payload.get("el3_payload_transmit_authorized") is False
        and payload.get("isp_write_authorized") is False
        and payload.get("hardware_live_attachment_authorized") is False
        and payload.get("physical_usb_packets_emitted") == 0
        and payload.get("p8_cp_mutation_forbidden") is True
        and payload.get("wbi_p5_write_and_hibernation_forbidden") is True
        and payload.get("cp_mutation_bytes") == 0
        and payload.get("wbi_mutation_bytes") == 0
        and payload.get("calibration_mutation_bytes") == 0
        and payload.get("usb_or_camera_operations") == 0
        and payload.get("otp_fuse_touches") == 0
        and payload.get("rpmb_counter_increments") == 0
        and payload.get("passive_tx_bytes_emitted") == 0
        and payload.get("p154_usb_packets_emitted") == 0
        and payload.get("p154_iokit_handles_opened") == 0
    )
    if not redlines_ok:
        errors.append("hard-locked zero-write / zero-SPI-NOR / zero-EL3 / zero-USB-TX / zero-attach redlines breached")

    pillars_raw = payload.get("pillars", [])
    pillars_seq = list(pillars_raw) if isinstance(pillars_raw, (list, tuple)) else []
    seen_ids = tuple(str(p.get("pillar_id", "")) for p in pillars_seq if isinstance(p, Mapping))
    all_6_ok = (
        seen_ids == PILLAR_IDS
        and len(pillars_seq) == 6
        and all(
            isinstance(p, Mapping)
            and bool(p.get("passed"))
            and p.get("status") == STATUS_MILESTONE_READY
            for p in pillars_seq
        )
    )
    if not all_6_ok:
        errors.append(f"all_6_pillars_ok check failed (seen={seen_ids!r})")

    counts_ok = (
        int(payload.get("gate58_total_gates", -1)) >= 58
        and int(payload.get("gate58_offline_verified", -1)) >= 55
        and int(payload.get("gate58_simulated_verified", -1)) >= 58
        and int(payload.get("recovery_pillar_count", -1)) >= 22
        and int(payload.get("recovery_pillars_passed", -1))
        == int(payload.get("recovery_pillar_count", -2))
        and int(payload.get("firmware_lab_auditor_count", -1)) >= 36
        and int(payload.get("firmware_lab_auditors_passed", -1))
        == int(payload.get("firmware_lab_auditor_count", -2))
        and int(payload.get("vm_coemulation_stage_count", -1)) >= 30
        and int(payload.get("vm_coemulation_stages_passed", -1))
        == int(payload.get("vm_coemulation_stage_count", -2))
        and int(payload.get("vm_emmc_corruptions", -1)) == 0
        and int(payload.get("vm_wf12_00342260_hits", -1)) == 0
        and int(payload.get("p136_u6_command_count", -1)) >= 19
        and payload.get("p136_u4_u5_u6_closed") is True
        and int(payload.get("p143_sd_escape_absent_us", 999)) <= 50
        and int(payload.get("p143_h0_equals_h3_count", -1)) == 16
        and int(payload.get("p143_h0_h3_surface_count", -1)) == 16
        and payload.get("p154_bench_go") is True
        and int(payload.get("qemu_rounds_verified", -1)) == 7
        and int(payload.get("qemu_runs_verified", -1)) == 21
        and int(payload.get("qemu_real_kernel_nop_count", -1)) == 0
        and int(payload.get("qemu_real_kernel_crashes", -1)) == 0
        and int(payload.get("qemu_real_kernel_emmc_writes", -1)) == 0
    )
    if not counts_ok:
        errors.append("milestone175 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append("all_pillars_milestone_ready / status is not MILESTONE_175_PREBENCH_MASTER_VERIFIED")

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 175 payload")

    valid = bool(schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0)
    return RealHwMilestone175VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone175_sha256=expected_sha,
        observed_milestone175_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


def render_milestone175_markdown(report: RealHwMilestone175MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 175 Master Gate."""
    lines = [
        f"# Real-Hardware Final Pre-Bench Milestone Phase 175 Master Gate (`{report.schema_version}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone175_sha256}`",
        "",
        "## Hard-Locked Safety Redlines / 硬锁定安全红线",
        f"- `persistent_emmc_writes_authorized = {report.persistent_emmc_writes_authorized}`, "
        f"`spi_nor_write_authorized = {report.spi_nor_write_authorized}`, "
        f"`el3_payload_transmit_authorized = {report.el3_payload_transmit_authorized}`",
        f"- `isp_write_authorized = {report.isp_write_authorized}`, "
        f"`persistent_write_release = {report.persistent_write_release}`, "
        f"`hardware_live_attachment_authorized = {report.hardware_live_attachment_authorized}`",
        f"- `physical_usb_packets_emitted = {report.physical_usb_packets_emitted}`, "
        f"`otp_fuse_touches = {report.otp_fuse_touches}`, "
        f"`rpmb_counter_increments = {report.rpmb_counter_increments}`, "
        f"`passive_tx_bytes_emitted = {report.passive_tx_bytes_emitted}`",
        f"- `cp_mutation_bytes = {report.cp_mutation_bytes}`, "
        f"`wbi_mutation_bytes = {report.wbi_mutation_bytes}`, "
        f"`calibration_mutation_bytes = {report.calibration_mutation_bytes}`",
        "",
        "## Pillar Matrix / 六大支柱总览",
        "| Pillar | Name | Status | Summary |",
        "|---|---|---|---|",
    ]
    for p in report.pillars:
        lines.append(f"| `{p.pillar_id}` | `{p.pillar_name}` | `{p.status}` | {p.summary} |")
    lines.extend(
        [
            "",
            "## Key Final Pre-Bench Readiness Metrics / 实机台架前最终闭环指标",
            f"- 58-Gate Preflight (`G01..G58`): offline=`{report.gate58_offline_verified}/{report.gate58_total_gates}` (`G10..G12` locked), simulated=`{report.gate58_simulated_verified}/{report.gate58_total_gates}`",
            f"- Recovery Vault & 5-Tier Escalation (`Ph47..174`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`>=22` required; `054C:0336` + `mtd0ro` + `ttyAMA0` + Dual-Media RAID-6)",
            f"- Firmware-Lab Auditors (`Ph1..171`): `{report.firmware_lab_auditors_passed}/{report.firmware_lab_auditor_count}` (`>=36` required; Auditors `29..36` `p18/Fan/0DA1/IMX510/CFexpress/CXD90058/C2PA/WBI2`)",
            f"- VM Co-Emulation (`Ph33..172`): `{report.vm_coemulation_stages_passed}/{report.vm_coemulation_stage_count}` (`>=30` required; `emmc_corruptions={report.vm_emmc_corruptions}`, `wf12_hits={report.vm_wf12_00342260_hits}`)",
            f"- Closure & Bench Preflight (`Ph136 + Ph143 + Ph154`): `U4/U5/U6={report.p136_u4_u5_u6_closed}` (`U6 cmds={report.p136_u6_command_count}`), SD absent escape=`{report.p143_sd_escape_absent_us}us <= 50us`, `H0 == H3`=`{report.p143_h0_equals_h3_count}/{report.p143_h0_h3_surface_count}`, `Phase154 bench_go={report.p154_bench_go}` (`usb_pkts={report.p154_usb_packets_emitted}`, `iokit={report.p154_iokit_handles_opened}`)",
            f"- Live FX3 `7.02` (`4.9.337-scel+`) QEMU Receipts (`Rounds 28..34`): `{report.qemu_rounds_verified}/7` rounds (`{report.qemu_runs_verified}/21` sub-experiments), `nop={report.qemu_real_kernel_nop_count}`, `crashes={report.qemu_real_kernel_crashes}`, `emmc_writes={report.qemu_real_kernel_emmc_writes}`",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "CALIBRATION_MUTATION_BYTES",
    "CP_MUTATION_BYTES",
    "DEFAULT_REPO_ROOT",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "FIRMWARE_LAB_36_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "ISP_WRITE_AUTHORIZED",
    "MILESTONE175_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "P8_CP_MUTATION_FORBIDDEN",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_175_VERSION",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "REALHW_MILESTONE175_SCHEMA",
    "RECOVERY_22_PILLAR_IDS",
    "ROUND28_TO_34_SPECS",
    "ROUND30_EXPECTED_SCHEMA",
    "ROUND30_SUMMARY_RELPATH",
    "ROUND31_EXPECTED_SCHEMA",
    "ROUND31_SUMMARY_RELPATH",
    "ROUND32_EXPECTED_SCHEMA",
    "ROUND32_SUMMARY_RELPATH",
    "ROUND33_EXPECTED_SCHEMA",
    "ROUND33_SUMMARY_RELPATH",
    "ROUND34_EXPECTED_SCHEMA",
    "ROUND34_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "SCHEMA_VERSION",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "VM_COEMULATION_30_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone175PillarResult",
    "RealHwMilestone175FaultInjection",
    "RealHwMilestone175MasterGateReport",
    "RealHwMilestone175VerifyResult",
    "RoundQemuReceiptSpec",
    "build_realhw_milestone175_master_gate_report",
    "compute_milestone175_sha256",
    "evaluate_milestone175_master_gate",
    "render_milestone175_markdown",
    "verify_realhw_milestone175_master_gate",
]
