"""Phase 147 — 6-Pillar Real-Hardware Bench Readiness Master Gate (`realhw_milestone147_master_gate_v1`).

Composes all six Milestone Phase 147 real-hardware readiness pillars (`P1 .. P6`)
across Phases 134–143 and live FX3 `7.02` (`4.9.337-scel+`) QEMU Rehearsal Rounds 28–29
into a single tamper-evident, fail-closed certificate executing in `< 3.0s` across both
`LOCAL_DONOR_O_RDONLY` (`os.O_RDONLY`) and `CLEAN_ROOM_SYNTHETIC` (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
modes:

- `P1` (`SAFETY_44GATE_REALHW_MASTER_PREFLIGHT`):
  Evaluates Phase 142 `evaluate_44gate_preflight` (`G01..G44`), verifying `>= 44` dry-run
  simulated gates pass (`dry_run_rehearsal_only=True`, `overall_ready_for_hardware_attach=False`)
  while offline hardware-truth mode enforces `41/44` (`G10..G12` physical attach/backup gates
  locked and `persistent_emmc_writes_authorized=False`), covering `G41` (VP LED-wall/strobe),
  `G42` (vehicle-rig IBIS), `G43` (`AdjustControl 0x40` / `libJiritsu.so` / `jbusy` / `p6`),
  and `G44` (`/dev/cnflasha15` SPACC, Tier-0 receipt, SD escape & `p1/p3` mutex).
- `P2` (`SEVENTEEN_PLUS_PILLAR_RECOVERY_AND_STREAMING_BACKUP`):
  Verifies all `>= 17` recovery pillars (`Phases 47..139`), extending the 13-pillar baseline
  with Phase 134 (`run_factory_cal_ibis_defectpixel_and_nvs_suite`, Pillar 14),
  Phase 138 (`run_secureboot_chain_and_partition_align_suite`, Pillar 15),
  Phase 139 (`run_realhw_ext2_installer_and_p1_rescue_suite`, Pillar 16: `/dev/cnflasha15`
  atomic installer with `/dev/pnflasha15` blocked), and Phase 139 streaming cold-backup client
  (`run_adjustcontrol_streaming_backup_suite`, Pillar 17: `AdjustControl (0x40)` `FX3RCPT1`
  16-surface SD streaming & `p6 <= 4 MiB` `FX3CHK1` sliding-window pull), locking
  `otp_fuse_touches == 0`, `rpmb_counter_increments == 0`, `passive_tx_bytes_emitted == 0`,
  `physical_device_writes == 0`, and `physical_usb_packets_emitted == 0`.
- `P3` (`TWENTY_EIGHT_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS`):
  Verifies all `>= 28` `fx3_firmware_lab` auditors (`Phases 1..140`), forward-compatible with
  Auditor 29+, adding #25 (`vp_ledwall_ecs_freed_and_artnet_audit`),
  #26 (`xavc_hevc_intra_aces_idt_and_fz100_audit`),
  #27 (`realhw_cp_rtos_and_backup_bin_audit`: `U2` `cpapp-b.bin` RTOS untouched &
  `U3` `Backup.bin` `819->840` `0xfa0080` Bank 0/1, `spi_nor_write_authorized=False`), and
  #28 (`realhw_mpr_dmm_rec_pipeline_bridge_audit`: `libmpr.so` 74 pass-through + `15` shimmed +
  `20` MAIN `DmmCfg.bin` pools), with `calibration_mutation_bytes == 0`.
- `P4` (`TWENTY_FOUR_PLUS_STAGE_VM_HIL_COEMULATION`):
  Verifies all `>= 24` `outputs/fx3-vm` heterogeneous AArch64 AP + ARM32 Thumb-2 Stock-CP
  co-emulation stages (`Phases 33..141`), forward-compatible with Stage 25+, adding Stages
  22 (`stage22_mxf_ptpv2_tally_monsoon_hil`), 23 (`stage23_vp_ledwall_freed_artnet_hil`), and
  24 (`stage24_realhw_preflash_dualboot_hil`, 4-state dual-boot + `p1` rescue), with
  `emmc_corruptions == 0`, `cp_mutation_bytes == 0`, `wf12_00342260_hits == 0`.
- `P5` (`CLOSURE_U4_U5_U6_AND_BYOF_SD_STAGEB_H0_H3`):
  Verifies `fx6_closure` Phase 136 (`run_phase136_realhw_jiritsu_tier0_audit`: `U6` 19-cmd
  disassembly + Stage-288 P0, `U4` Strategy-A `/dev/nflasha20 -> /dev/nflasha30` Zero-Sector0
  bridge, `U5` `p1` single-shot clear -> `p3` fallback, Tier-0 two-pass stop-gate) and
  Phase 143 (`run_phase143_sd_stageb_bundle_uninstaller_audit`: BYOF SD Stage-B bundle,
  `/usr/bin/im.elf` 3-escape-hatch wrapper with `47 us <= 50 us` SD-absent bypass, and
  `16/16` `SHA256(H0) == SHA256(H3)` clean factory uninstaller + 5 power-loss drills).
- `P6` (`REAL_FX3_702_QEMU_R28_R29_REHEARSAL_RECEIPTS`):
  Verifies committed live FX3 `7.02` (`4.9.337-scel+`) ARM64 kernel QEMU rehearsal receipts
  from Round 28 (`r28a..r28c` SD escape hatch + `libJit.so` probe + Strategy-A + Big-6) and
  Round 29 (`r29a..r29c` `/dev/cnflasha15` atomic installer + `libmpr.so` REC + rollback + `p1`
  oneshot clear) strictly via `os.O_RDONLY` when present (deterministic clean-room receipt
  validation when `FX3_FX6_FORCE_CLEAN_ROOM=1`), proving `crashes == 0`, `nop_count == 0`,
  and `emmc_write_count == 0`.

Hard-Locked Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
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

from fx3_firmware_lab.realhw_cp_rtos_and_backup_bin_auditor import (  # noqa: E402
    analyze_realhw_cp_rtos_and_backup_bin,
    realhw_cp_rtos_and_backup_bin_report_to_dict,
)
from fx3_firmware_lab.realhw_mpr_dmm_rec_pipeline_bridge_auditor import (  # noqa: E402
    analyze_realhw_mpr_dmm_rec_pipeline_bridge,
    realhw_mpr_dmm_rec_pipeline_bridge_report_to_dict,
)
from fx3_firmware_lab.vp_ledwall_ecs_freed_and_artnet_auditor import (  # noqa: E402
    analyze_vp_ledwall_ecs_freed_and_artnet,
    vp_ledwall_ecs_freed_and_artnet_report_to_dict,
)
from fx3_firmware_lab.xavc_hevc_intra_aces_idt_and_fz100_auditor import (  # noqa: E402
    analyze_xavc_hevc_intra_aces_idt_and_fz100,
    xavc_hevc_intra_aces_idt_and_fz100_report_to_dict,
)
from fx3_recovery import (  # noqa: E402
    run_adjustcontrol_streaming_backup_suite,
    run_factory_cal_ibis_defectpixel_and_nvs_suite,
    run_realhw_ext2_installer_and_p1_rescue_suite,
    run_secureboot_chain_and_partition_align_suite,
)
from fx3_safety.realhw_jiritsu_cnflasha_and_44gate_guard import (  # noqa: E402
    evaluate_44gate_preflight,
)

from .hardware_readiness_packet import _is_forced_clean_room  # noqa: E402
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
)
from .realhw_jiritsu_and_tier0_dumper_auditor import (  # noqa: E402
    run_phase136_realhw_jiritsu_tier0_audit,
)
from .realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    run_phase143_sd_stageb_bundle_uninstaller_audit,
)
from .stage_b_capstone_22gate_verifier import (  # noqa: E402
    _build_clean_room_stage_b_manifest_items,
    _worker_domain_2,
)
from .stage_b_milestone110_master_gate import (  # noqa: E402
    _clean_room_faithful_block,
    _worker_pillar_4,
    _worker_recovery_master,
    _worker_recovery_p8_p9_p10,
)
from .stage_b_milestone130_master_gate import (  # noqa: E402
    FIRMWARE_LAB_24_AUDITOR_KEYS,
    MILESTONE130_SCHEMA_VERSION,
    RECOVERY_13_PILLAR_IDS,
    VM_COEMULATION_21_STAGE_KEYS,
    Milestone130FaultInjection,
    _evaluate_pillar_2 as _eval_m130_p2,
    _evaluate_pillar_3 as _eval_m130_p3,
    _evaluate_pillar_4 as _eval_m130_p4,
    _fault_to_worker_dict as _m130_fault_to_worker_dict,
    _worker_pillar_3_group as _m130_worker_pillar_3_group,
    _worker_recovery_p11_to_p13,
)
from .stage_b_post_trial_auditor import _read_file_o_rdonly  # noqa: E402
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402
from .stage_b_release_dossier_v3 import _worker_pillar_b  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_MILESTONE147_SCHEMA: str = "realhw_milestone147_master_gate_v1"
MILESTONE147_SCHEMA_VERSION: str = REALHW_MILESTONE147_SCHEMA
SCHEMA_VERSION: str = REALHW_MILESTONE147_SCHEMA
PHASE_147_VERSION: str = "147.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
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

STATUS_MILESTONE_READY: str = "MILESTONE_147_BENCH_READINESS_VERIFIED"
STATUS_FAIL_CLOSED: str = "FAIL_CLOSED"

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_44GATE_REALHW_MASTER_PREFLIGHT"),
    ("P2", "SEVENTEEN_PLUS_PILLAR_RECOVERY_AND_STREAMING_BACKUP"),
    ("P3", "TWENTY_EIGHT_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS"),
    ("P4", "TWENTY_FOUR_PLUS_STAGE_VM_HIL_COEMULATION"),
    ("P5", "CLOSURE_U4_U5_U6_AND_BYOF_SD_STAGEB_H0_H3"),
    ("P6", "REAL_FX3_702_QEMU_R28_R29_REHEARSAL_RECEIPTS"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)

RECOVERY_17_PILLAR_IDS: Tuple[str, ...] = (
    *RECOVERY_13_PILLAR_IDS,
    "factory_cal_ibis_defectpixel_and_nvs_verifier",
    "secureboot_chain_and_partition_align_verifier",
    "realhw_ext2_installer_and_p1_rescue_verifier",
    "realhw_adjustcontrol_streaming_backup_client",
)

FIRMWARE_LAB_28_AUDITOR_KEYS: Tuple[str, ...] = (
    *FIRMWARE_LAB_24_AUDITOR_KEYS,
    "vp_ledwall_ecs_freed_and_artnet_audit",
    "xavc_hevc_intra_aces_idt_and_fz100_audit",
    "realhw_cp_rtos_and_backup_bin_audit",
    "realhw_mpr_dmm_rec_pipeline_bridge_audit",
)

VM_COEMULATION_24_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_21_STAGE_KEYS,
    "stage22_mxf_ptpv2_tally_monsoon_hil",
    "stage23_vp_ledwall_freed_artnet_hil",
    "stage24_realhw_preflash_dualboot_hil",
)

ROUND28_SUMMARY_RELPATH: str = (
    "reports/2026-11-14-round28-realhw-sd-dualboot-overlay-qemu-rehearsal/summary.json"
)
ROUND29_SUMMARY_RELPATH: str = (
    "reports/2026-11-14-round29-realhw-atomic-installer-mpr-rec-qemu-rehearsal/summary.json"
)

ROUND28_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round28-realhw-sd-dualboot-overlay-qemu-rehearsal-v1"
)
ROUND29_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round29-realhw-atomic-installer-mpr-rec-qemu-rehearsal-v1"
)

ROUND28_RUN_SPECS: Tuple[Tuple[str, int], ...] = (
    ("r28a_sd_escape_absent_stock_fx3", 0),
    ("r28b_sd_trigger_valid_jiritsu_and_stageb_big6", 1),
    ("r28c_sd_trigger_tampered_fail_closed_fallback", 0),
)
ROUND29_RUN_SPECS: Tuple[Tuple[str, int], ...] = (
    ("r29a_atomic_install_and_live_mpr_rec_big6", 1),
    ("r29b_fault_injected_midwrite_atomic_rollback", 0),
    ("r29c_p1_oneshot_mode_clear_and_p3_return", 0),
)

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_VM_STAGE_KEY_RE = re.compile(r"^stage(\d+)_")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealHwMilestone147FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 faults (44-gate preflight, G21..G44)
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

    # P2 faults (>= 17-pillar recovery, incl. Pillars 14..17)
    p2_otp_downgrade_version: Optional[str] = None
    p2_inject_cross_sku_target: Optional[str] = None
    p2_inject_ext_csd_perm_wp: bool = False
    p2_otp_fuse_touches_override: int = 0
    p2_rpmb_increments_override: int = 0
    p2_passive_tx_bytes_override: int = 0
    p2_inject_cross_body_cnflasha_transplant: bool = False
    p2_inject_gf256_quorum_loss: bool = False
    p2_inject_init2_escape_fault: bool = False
    p2_inject_gpt_both_corrupted: bool = False
    p2_inject_rpmb_replay_fault: bool = False
    p2_inject_cpio_or_emmc_fault: bool = False
    p2_inject_fdt_or_kernel_fault: bool = False
    p2_inject_ab_ota_fault: bool = False
    p2_inject_squashfs_hibdrv_fault: bool = False
    p2_inject_bootrom_bootpart_fault: bool = False
    p2_inject_factory_cal_fault: bool = False
    p2_inject_secureboot_align_fault: bool = False
    p2_inject_ext2_p1_rescue_fault: bool = False
    p2_inject_adjustcontrol_streaming_fault: bool = False
    p2_physical_usb_packets_override: int = 0

    # P3 faults (>= 28 fx3_firmware_lab auditors, incl. #25..#28)
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

    # P4 faults (>= 24-stage VM co-emulation, Stages 1..24)
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

    # P5 faults (Closure Phase 136 U4/U5/U6/Tier-0 + Phase 143 SD Bundle & H0 == H3)
    p5_inject_p136_u4_u5_u6_fault: bool = False
    p5_inject_p143_escape_hatch_over_budget_us: int = 0
    p5_inject_p143_h0_h3_drift: bool = False

    # P6 faults (Rounds 28 & 29 live QEMU kernel rehearsal receipts)
    p6_r28_nop_count_override: Optional[int] = None
    p6_r28_crashes_override: Optional[int] = None
    p6_r28_emmc_writes_override: Optional[int] = None
    p6_r29_nop_count_override: Optional[int] = None
    p6_r29_crashes_override: Optional[int] = None
    p6_r29_emmc_writes_override: Optional[int] = None
    p6_r29_tamper_schema: bool = False


@dataclass(frozen=True)
class Milestone147PillarResult:
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
class RealHwMilestone147MasterGateReport:
    schema_version: str
    phase_version: str
    verification_mode: str
    all_pillars_milestone_ready: bool
    status: str
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
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
    pillars: Tuple[Milestone147PillarResult, ...]
    gate44_total_gates: int
    gate44_offline_verified: int
    gate44_simulated_verified: int
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
    r28_runs_verified: int
    r29_runs_verified: int
    qemu_real_kernel_nop_count: int
    qemu_real_kernel_crashes: int
    qemu_real_kernel_emmc_writes: int
    errors: Tuple[str, ...]
    milestone147_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class RealHwMilestone147VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone147_sha256: str
    observed_milestone147_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic Digest & O_RDONLY Round 28 / Round 29 Loaders
# ---------------------------------------------------------------------------


def compute_milestone147_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `RealHwMilestone147MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone147_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def _load_round28_or_29_summary(
    round_num: int,
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], str]:
    """Load Round 28 or 29 QEMU rehearsal summary strictly via `os.O_RDONLY` or clean-room fallback."""
    if round_num not in (28, 29):
        raise ValueError(f"Unsupported round_num for Milestone 147 P6: {round_num}")
    relpath = ROUND28_SUMMARY_RELPATH if round_num == 28 else ROUND29_SUMMARY_RELPATH
    summary_path = repo_root / relpath
    if summary_path.is_file() and not summary_path.is_symlink():
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if isinstance(obj, dict):
            return obj, "REPO_SUMMARY_O_RDONLY"
    if not use_clean_room:
        raise FileNotFoundError(f"Missing round{round_num} summary report: {summary_path}")

    manifest_items = _build_clean_room_stage_b_manifest_items()
    kver = "Linux version 4.9.337-scel+ (clean-room-synthetic)"

    def _mk_run(run_id: str, faithful_val: int) -> Dict[str, Any]:
        faithful = _clean_room_faithful_block()
        faithful["FX6_NATIVE_FAITHFUL"] = faithful_val
        faithful["emmc_write_count"] = 0
        return {
            "run_id": run_id.replace("_", "-"),
            "round": round_num,
            "lang": "schinese",
            "kernel_version": kver,
            "nop_count": 0,
            "crashes": 0,
            "emmc_write_count": 0,
            "faithful_invariants": faithful,
            "stage_b": {
                "stage": "B",
                f"r{round_num}_enabled": True,
                "lang": "schinese",
                "manifest_count": 13,
                "manifest_items": list(manifest_items),
            },
        }

    if round_num == 28:
        runs = {rid: _mk_run(rid, exp_f) for rid, exp_f in ROUND28_RUN_SPECS}
        return (
            {
                "schema": ROUND28_EXPECTED_SCHEMA,
                "kernel_version": kver,
                "realhw_mechanisms_verified": {
                    "hardened_stage288_libjit": {
                        "elf_class": "ELF64",
                        "e_machine": 183,
                        "pt_load_align": "0x10000",
                        "sector0_magic": "8246",
                        "sector0_ver": "2.00",
                        "sector0_parts": 30,
                    },
                    "strategy_a_zero_sector0_bridge": {
                        "nflasha20_symlink_target": "/dev/nflasha30",
                        "nflasha30_symlink_target": "/dev/cnflasha30",
                        "opelog_fstype": "tmpfs",
                        "sector0_repartition": 0,
                        "emmc_write_count": 0,
                    },
                    "sd_card_reversible_dualboot_escape_hatch": {
                        "absent_mode": "STOCK_FX3_BYPASS",
                        "valid_mode": "STAGEB_SD_AUTHENTICATED",
                        "tampered_mode": "FAIL_CLOSED_STOCK_FX3_FALLBACK",
                        "observed_absent_verify_us": 47,
                    },
                },
                "runs": runs,
                "r28_realhw_escape_hatch_audit": {
                    "audit_id": "r28-realhw-sd-dualboot-libjit-strategy-a-3run-closure",
                    "total_runs": 3,
                    "all_3_runs_crashes_zero": True,
                    "all_3_runs_emmc_write_zero": True,
                    "r28a_stock_fx3_bypass_verified": True,
                    "r28b_libjit_probe_verified": True,
                    "r28b_strategy_a_bridge_verified": True,
                    "r28b_stageb_big6_verified": True,
                    "r28c_tamper_fail_closed_under_50ms": True,
                },
            },
            "CLEAN_ROOM_SYNTHETIC",
        )

    runs = {rid: _mk_run(rid, exp_f) for rid, exp_f in ROUND29_RUN_SPECS}
    return (
        {
            "schema": ROUND29_EXPECTED_SCHEMA,
            "kernel_version": kver,
            "realhw_mechanisms_verified": {
                "native_arm64_atomic_installer": {
                    "device": "/dev/cnflasha15",
                    "rejected_plaintext_device": "/dev/pnflasha15",
                    "ro_remount_erofs_verified": True,
                    "emmc_write_count": 0,
                },
                "fault_injected_atomic_rollback": {
                    "stock_sha256_restored": 1,
                    "atomic_rollback_verified": 1,
                    "emmc_write_count": 0,
                },
                "p1_oneshot_mode_clear_rescue": {
                    "first_line": "rm -f /setting/updater/mode* && sync",
                    "mode_files_remaining": 0,
                    "p3_untouched": 1,
                    "next_cold_boot_bank": "p3",
                    "emmc_write_count": 0,
                },
                "live_libmpr_ap_cp_shim": {
                    "libmpr_syms_resolved": 11,
                    "libmpr_syms_total": 11,
                    "mpr_rec_finalized": 1,
                    "rsv_orphan_count": 0,
                },
            },
            "runs": runs,
            "r29_realhw_atomic_installer_mpr_rec_audit": {
                "audit_id": "r29-realhw-atomic-installer-rollback-p1-rescue-mpr-rec-3run-closure",
                "total_runs": 3,
                "all_3_runs_crashes_zero": True,
                "all_3_runs_emmc_write_zero": True,
                "r29a_atomic_install_ok": True,
                "r29a_mpr_param_and_rec_finalized": True,
                "r29a_stageb_big6_verified": True,
                "r29b_midwrite_atomic_rollback_verified": True,
                "r29c_p1_oneshot_mode_clear_verified": True,
            },
        },
        "CLEAN_ROOM_SYNTHETIC",
    )


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 3.0s Runtime)
# ---------------------------------------------------------------------------


def _fault_to_m130_faults(faults: RealHwMilestone147FaultInjection) -> Milestone130FaultInjection:
    return Milestone130FaultInjection(
        p1_pl_cantilever_kwargs=faults.p1_pl_cantilever_kwargs,
        p1_dummy_battery_kwargs=faults.p1_dummy_battery_kwargs,
        p1_saltspray_haze_kwargs=faults.p1_saltspray_haze_kwargs,
        p1_followfocus_gimbal_kwargs=faults.p1_followfocus_gimbal_kwargs,
        p1_hdmi_aoc_kwargs=faults.p1_hdmi_aoc_kwargs,
        p1_cfexpress_media_kwargs=faults.p1_cfexpress_media_kwargs,
        p1_usbpd_uvc_kwargs=faults.p1_usbpd_uvc_kwargs,
        p1_multiterminal_ptp_kwargs=faults.p1_multiterminal_ptp_kwargs,
        p1_monsoon_mishoe_kwargs=faults.p1_monsoon_mishoe_kwargs,
        p1_cagetwist_xlrh1_kwargs=faults.p1_cagetwist_xlrh1_kwargs,
        p1_dewpoint_kwargs=faults.p1_dewpoint_kwargs,
        p1_pmic_usbc_kwargs=faults.p1_pmic_usbc_kwargs,
        p1_xlr_kwargs=faults.p1_xlr_kwargs,
        p1_gimbal_kwargs=faults.p1_gimbal_kwargs,
        p1_rig_kwargs=faults.p1_rig_kwargs,
        p1_emount_kwargs=faults.p1_emount_kwargs,
        p1_power_failover_kwargs=faults.p1_power_failover_kwargs,
        p1_intake_fan_kwargs=faults.p1_intake_fan_kwargs,
        p1_tripod_housing_kwargs=faults.p1_tripod_housing_kwargs,
        p1_sensor_curtain_kwargs=faults.p1_sensor_curtain_kwargs,
        p1_subzero_altitude_kwargs=faults.p1_subzero_altitude_kwargs,
        p1_wireless_tx_emi_kwargs=faults.p1_wireless_tx_emi_kwargs,
        p1_longform_endurance_kwargs=faults.p1_longform_endurance_kwargs,
        p1_request_persistent_writes=faults.p1_request_persistent_writes,
        p2_otp_downgrade_version=faults.p2_otp_downgrade_version,
        p2_inject_cross_sku_target=faults.p2_inject_cross_sku_target,
        p2_inject_ext_csd_perm_wp=faults.p2_inject_ext_csd_perm_wp,
        p2_otp_fuse_touches_override=faults.p2_otp_fuse_touches_override,
        p2_rpmb_increments_override=faults.p2_rpmb_increments_override,
        p2_passive_tx_bytes_override=faults.p2_passive_tx_bytes_override,
        p2_inject_cross_body_cnflasha_transplant=faults.p2_inject_cross_body_cnflasha_transplant,
        p2_inject_gf256_quorum_loss=faults.p2_inject_gf256_quorum_loss,
        p2_inject_init2_escape_fault=faults.p2_inject_init2_escape_fault,
        p2_inject_gpt_both_corrupted=faults.p2_inject_gpt_both_corrupted,
        p2_inject_rpmb_replay_fault=faults.p2_inject_rpmb_replay_fault,
        p2_inject_cpio_or_emmc_fault=faults.p2_inject_cpio_or_emmc_fault,
        p2_inject_fdt_or_kernel_fault=faults.p2_inject_fdt_or_kernel_fault,
        p2_inject_ab_ota_fault=faults.p2_inject_ab_ota_fault,
        p2_inject_squashfs_hibdrv_fault=faults.p2_inject_squashfs_hibdrv_fault,
        p2_inject_bootrom_bootpart_fault=faults.p2_inject_bootrom_bootpart_fault,
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
    )


def _fault_to_worker_dict(faults: RealHwMilestone147FaultInjection) -> Dict[str, Any]:
    d = _m130_fault_to_worker_dict(_fault_to_m130_faults(faults))
    for k in (
        "p1_vp_strobe_genlock_kwargs",
        "p1_vehiclerig_ibis_kwargs",
        "p1_jiritsu_service_kwargs",
        "p1_cnflasha_dualboot_kwargs",
    ):
        val = getattr(faults, k)
        d[k] = dict(val) if val is not None else None
    return d


def _worker_pillar_1(args: Tuple[str, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, fault_dict = args
    repo_root = Path(repo_root_str)
    req_persist = bool(fault_dict.get("p1_request_persistent_writes", False))

    kwargs: Dict[str, Any] = {
        "vp_strobe_genlock_kwargs": fault_dict.get("p1_vp_strobe_genlock_kwargs"),
        "vehiclerig_ibis_kwargs": fault_dict.get("p1_vehiclerig_ibis_kwargs"),
        "jiritsu_service_kwargs": fault_dict.get("p1_jiritsu_service_kwargs"),
        "cnflasha_dualboot_kwargs": fault_dict.get("p1_cnflasha_dualboot_kwargs"),
        "pl_cantilever_kwargs": fault_dict.get("p1_pl_cantilever_kwargs"),
        "dummy_battery_kwargs": fault_dict.get("p1_dummy_battery_kwargs"),
        "saltspray_haze_kwargs": fault_dict.get("p1_saltspray_haze_kwargs"),
        "followfocus_gimbal_kwargs": fault_dict.get("p1_followfocus_gimbal_kwargs"),
        "hdmi_aoc_kwargs": fault_dict.get("p1_hdmi_aoc_kwargs"),
        "cfexpress_media_kwargs": fault_dict.get("p1_cfexpress_media_kwargs"),
        "usbpd_uvc_kwargs": fault_dict.get("p1_usbpd_uvc_kwargs"),
        "multiterminal_ptp_kwargs": fault_dict.get("p1_multiterminal_ptp_kwargs"),
        "monsoon_mishoe_kwargs": fault_dict.get("p1_monsoon_mishoe_kwargs"),
        "cagetwist_xlrh1_kwargs": fault_dict.get("p1_cagetwist_xlrh1_kwargs"),
        "dewpoint_kwargs": fault_dict.get("p1_dewpoint_kwargs"),
        "pmic_usbc_kwargs": fault_dict.get("p1_pmic_usbc_kwargs"),
        "xlr_kwargs": fault_dict.get("p1_xlr_kwargs"),
        "gimbal_kwargs": fault_dict.get("p1_gimbal_kwargs"),
        "rig_kwargs": fault_dict.get("p1_rig_kwargs"),
        "emount_kwargs": fault_dict.get("p1_emount_kwargs"),
        "power_failover_kwargs": fault_dict.get("p1_power_failover_kwargs"),
        "intake_fan_kwargs": fault_dict.get("p1_intake_fan_kwargs"),
        "tripod_housing_kwargs": fault_dict.get("p1_tripod_housing_kwargs"),
        "sensor_curtain_kwargs": fault_dict.get("p1_sensor_curtain_kwargs"),
        "subzero_altitude_kwargs": fault_dict.get("p1_subzero_altitude_kwargs"),
        "wireless_tx_emi_kwargs": fault_dict.get("p1_wireless_tx_emi_kwargs"),
        "longform_endurance_kwargs": fault_dict.get("p1_longform_endurance_kwargs"),
        "request_persistent_emmc_writes": req_persist,
    }

    rep_off = evaluate_44gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=False,
        **kwargs,
    )
    rep_sim = evaluate_44gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=True,
        **kwargs,
    )

    m42 = rep_sim.master_42_report
    g41 = m42.get("g41_result", {})
    g42 = m42.get("g42_result", {})
    g43 = rep_sim.g43_result
    g44 = rep_sim.g44_result

    return {
        "schema": rep_sim.schema,
        "verification_mode": rep_sim.verification_mode,
        "total_gates": int(rep_sim.summary.get("total_gates", len(rep_sim.gates))),
        "offline_verified_gates": int(rep_off.summary.get("verified_gates", 0)),
        "offline_41_gates_verified": bool(rep_off.offline_41_gates_verified),
        "offline_all_44_gates_verified": bool(rep_off.all_44_gates_verified),
        "offline_ready_for_hw": bool(rep_off.overall_ready_for_hardware_attach),
        "sim_verified_gates": int(rep_sim.summary.get("verified_gates", 0)),
        "sim_all_44_gates_verified": bool(rep_sim.all_44_gates_verified),
        "sim_dry_run_rehearsal_only": bool(rep_sim.dry_run_rehearsal_only),
        "sim_ready_for_hw": bool(rep_sim.overall_ready_for_hardware_attach),
        "g13_to_g44_all_passed": bool(rep_sim.g13_to_g44_all_passed),
        "g43_to_g44_all_passed": bool(rep_sim.g43_to_g44_all_passed),
        "m42_g13_to_g42_all_passed": bool(m42.get("g13_to_g42_all_passed", False)),
        "m42_g41_to_g42_all_passed": bool(m42.get("g41_to_g42_all_passed", False)),
        "g41_passed": bool(g41.get("valid", False)),
        "g41_status": str(g41.get("status", "")),
        "g41_guard": dict(g41.get("vp_strobe_genlock_firewall", {})),
        "g42_passed": bool(g42.get("valid", False)),
        "g42_status": str(g42.get("status", "")),
        "g42_guard": dict(g42.get("vehiclerig_ibis_guard", {})),
        "g43_passed": bool(g43.get("valid", False)),
        "g43_status": str(g43.get("status", "")),
        "g43_guard": dict(g43.get("jiritsu_service_guard", {})),
        "g44_passed": bool(g44.get("valid", False)),
        "g44_status": str(g44.get("status", "")),
        "g44_guard": dict(g44.get("cnflasha_dualboot_guard", {})),
        "persistent_emmc_writes_authorized": bool(rep_sim.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep_sim.persistent_write_release),
        "sim_errors": list(rep_sim.errors),
        "g41_to_g44_errors": [
            *list(g41.get("errors", [])),
            *list(g42.get("errors", [])),
            *list(g43.get("errors", [])),
            *list(g44.get("errors", [])),
        ],
    }


def _worker_recovery_p14_to_p16(use_clean_room: bool) -> Dict[str, Any]:
    p14 = run_factory_cal_ibis_defectpixel_and_nvs_suite(force_clean_room=use_clean_room).to_dict()
    p15 = run_secureboot_chain_and_partition_align_suite(force_clean_room=use_clean_room).to_dict()
    p16 = run_realhw_ext2_installer_and_p1_rescue_suite(force_clean_room=use_clean_room).to_dict()
    return {
        "p14_factory_cal_ibis_nvs": p14,
        "p15_secureboot_partition_align": p15,
        "p16_realhw_ext2_p1_rescue": p16,
    }


def _worker_recovery_p17(use_clean_room: bool) -> Dict[str, Any]:
    return run_adjustcontrol_streaming_backup_suite(force_clean_room=use_clean_room).to_dict()


def _worker_pillar_3_group(args: Tuple[str, bool]) -> Dict[str, Dict[str, Any]]:
    group, clean_room = args
    if group == "vp_ledwall":
        return {
            "vp_ledwall_ecs_freed_and_artnet_audit": vp_ledwall_ecs_freed_and_artnet_report_to_dict(
                analyze_vp_ledwall_ecs_freed_and_artnet(clean_room=clean_room)
            )
        }
    if group == "xavc_fz100":
        return {
            "xavc_hevc_intra_aces_idt_and_fz100_audit": xavc_hevc_intra_aces_idt_and_fz100_report_to_dict(
                analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=clean_room)
            )
        }
    if group == "realhw_cp_backup":
        return {
            "realhw_cp_rtos_and_backup_bin_audit": realhw_cp_rtos_and_backup_bin_report_to_dict(
                analyze_realhw_cp_rtos_and_backup_bin(clean_room=clean_room)
            )
        }
    if group == "realhw_mpr_dmm":
        return {
            "realhw_mpr_dmm_rec_pipeline_bridge_audit": realhw_mpr_dmm_rec_pipeline_bridge_report_to_dict(
                analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=clean_room)
            )
        }
    return _m130_worker_pillar_3_group((group, clean_room))


def _worker_pillar_3_batch(args: Tuple[Tuple[str, ...], bool]) -> Dict[str, Dict[str, Any]]:
    groups, clean_room = args
    merged: Dict[str, Dict[str, Any]] = {}
    for g in groups:
        merged.update(_worker_pillar_3_group((g, clean_room)))
    return merged


def _worker_phase136(use_clean_room: bool) -> Dict[str, Any]:
    return run_phase136_realhw_jiritsu_tier0_audit(synthetic_clean_room=use_clean_room).to_dict()


def _worker_phase143(args: Tuple[str, str, bool]) -> Dict[str, Any]:
    fx6_lib_dir_str, fx3_modules_dir_str, use_clean_room = args
    return run_phase143_sd_stageb_bundle_uninstaller_audit(
        fx6_lib_dir=Path(fx6_lib_dir_str),
        fx3_modules_dir=Path(fx3_modules_dir_str),
        synthetic_clean_room=use_clean_room,
    ).to_dict()


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1 .. P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(raw_1: Mapping[str, Any]) -> Milestone147PillarResult:
    errors: List[str] = []
    total_gates = int(raw_1.get("total_gates", 0))
    offline_verified = int(raw_1.get("offline_verified_gates", -1))
    sim_verified = int(raw_1.get("sim_verified_gates", -1))

    if total_gates < 44:
        errors.append(f"p1: total_gates expected >= 44, got {total_gates}")
    if (
        not raw_1.get("offline_41_gates_verified")
        or offline_verified < 41
        or offline_verified >= total_gates
    ):
        errors.append(
            f"p1: offline hardware-truth gates expected >= 41 and < {total_gates}, got {offline_verified}/{total_gates}"
        )
    if raw_1.get("offline_all_44_gates_verified") or raw_1.get("offline_ready_for_hw"):
        errors.append("p1: offline mode must remain blocked for live hardware attach")
    if (
        not raw_1.get("sim_all_44_gates_verified")
        or sim_verified < 44
        or sim_verified != total_gates
    ):
        errors.append(
            f"p1: simulated rehearsal gates expected >= 44 and == {total_gates}, got {sim_verified}/{total_gates}"
        )
    if not raw_1.get("sim_dry_run_rehearsal_only") or raw_1.get("sim_ready_for_hw"):
        errors.append("p1: simulated 44-gate rehearsal must keep overall_ready_for_hardware_attach=False")
    if (
        not raw_1.get("g13_to_g44_all_passed")
        or not raw_1.get("g43_to_g44_all_passed")
        or not raw_1.get("m42_g13_to_g42_all_passed")
        or not raw_1.get("m42_g41_to_g42_all_passed")
    ):
        errors.append("p1: G13..G44, G43..G44, or G13..G42 safety guard gate blocked")

    guard_checks = (
        ("g41", ("arc_strobe_irradiance_safe", "multiterminal_genlock_safe", "ledwall_ecs_sync_safe")),
        ("g42", ("hardmount_wire_isolator_safe", "ibis_resonance_park_safe", "exterior_steel_tether_safe")),
        (
            "g43",
            (
                "electrical_power_safe",
                "jbusy_precheck_safe",
                "wire_framing_and_opcodes_safe",
                "elf_alignment_and_selfdelete_safe",
                "p6_quota_and_cleanup_safe",
                "constructor_unlinkat_self_delete_enabled",
            ),
        ),
        (
            "g44",
            (
                "tier0_cold_backup_safe",
                "spacc_boundary_and_flasher_safe",
                "sd_escape_hatch_safe",
                "p1_p3_mutex_and_uart_safe",
                "target_is_type5_flag1_encrypted",
            ),
        ),
    )
    for gk, subkeys in guard_checks:
        if not raw_1.get(f"{gk}_passed", False):
            errors.append(f"p1: {gk.upper()} safety guard failed ({raw_1.get(f'{gk}_status', '')})")
        sub = raw_1.get(f"{gk}_guard", {})
        if not isinstance(sub, Mapping) or not bool(sub.get("valid", False)):
            errors.append(f"p1: {gk.upper()} inner firewall/guard invalid")
        elif any(not bool(sub.get(sk, False)) for sk in subkeys):
            errors.append(f"p1: {gk.upper()} sub-invariant failed")

    g43g = raw_1.get("g43_guard", {})
    if int(g43g.get("elf_pt_load_align_bytes", -1)) != 65536 or int(g43g.get("p6_residual_files", -1)) != 0:
        errors.append("p1: G43 ELF 64 KiB PT_LOAD alignment or p6 zero-residual check failed")

    g44g = raw_1.get("g44_guard", {})
    if (
        g44g.get("target_block_device") != "/dev/cnflasha15"
        or g44g.get("modify_p1_in_transaction") is not False
        or g44g.get("modify_p3_in_transaction") is not False
        or float(g44g.get("sd_escape_bypass_latency_us", 999999.0)) > 50.0
    ):
        errors.append("p1: G44 /dev/cnflasha15, p1/p3 mutex, or <=50us SD escape invariant failed")

    if raw_1.get("persistent_emmc_writes_authorized") is not False or raw_1.get("persistent_write_release") is not False:
        errors.append("p1: hard-locked persistent_emmc_writes_authorized / persistent_write_release breached")
    for err in raw_1.get("sim_errors", ()):
        errors.append(f"p1_44gate: {err}")
    for err in raw_1.get("g41_to_g44_errors", ()):
        errors.append(f"p1_g41_g44: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_1.get("schema"),
        "verification_mode": raw_1.get("verification_mode"),
        "total_gates": total_gates,
        "offline_verified_gates": offline_verified,
        "offline_ready_for_hardware_attach": raw_1.get("offline_ready_for_hw"),
        "simulated_verified_gates": sim_verified,
        "simulated_ready_for_hardware_attach": raw_1.get("sim_ready_for_hw"),
        "m42_g13_to_g42_all_passed": raw_1.get("m42_g13_to_g42_all_passed"),
        "g41_passed": raw_1.get("g41_passed"),
        "g42_passed": raw_1.get("g42_passed"),
        "g43_passed": raw_1.get("g43_passed"),
        "g43_status": raw_1.get("g43_status"),
        "g44_passed": raw_1.get("g44_passed"),
        "g44_status": raw_1.get("g44_status"),
        "g43_to_g44_all_passed": raw_1.get("g43_to_g44_all_passed"),
        "g13_to_g44_all_passed": raw_1.get("g13_to_g44_all_passed"),
        "persistent_emmc_writes_authorized": raw_1.get("persistent_emmc_writes_authorized"),
        "persistent_write_release": raw_1.get("persistent_write_release"),
    }
    return Milestone147PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_44GATE_REALHW_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"44-Gate offline={offline_verified}/{total_gates} (G10..G12 locked) "
            f"sim={sim_verified}/{total_gates}, G41/42={raw_1.get('m42_g41_to_g42_all_passed')}, "
            f"G43(Jiritsu-0x40)={raw_1.get('g43_passed')}, G44(cnflasha15-DualBoot)={raw_1.get('g44_passed')} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    raw_master: Mapping[str, Any],
    raw_p8_p10: Mapping[str, Any],
    raw_p11_p13: Mapping[str, Any],
    raw_p14_p16: Mapping[str, Any],
    raw_p17: Mapping[str, Any],
    raw_antirollback: Mapping[str, Any],
    raw_tier0_init2: Mapping[str, Any],
    faults: RealHwMilestone147FaultInjection,
) -> Tuple[Milestone147PillarResult, Dict[str, Any]]:
    m130_p2, meta_13 = _eval_m130_p2(
        raw_master,
        raw_p8_p10,
        raw_p11_p13,
        raw_antirollback,
        raw_tier0_init2,
        _fault_to_m130_faults(faults),
    )
    errors: List[str] = list(m130_p2.errors)
    pillar_statuses: Dict[str, bool] = dict(m130_p2.evidence["pillar_statuses"])

    p14 = raw_p14_p16.get("p14_factory_cal_ibis_nvs", {})
    p15 = raw_p14_p16.get("p15_secureboot_partition_align", {})
    p16 = raw_p14_p16.get("p16_realhw_ext2_p1_rescue", {})
    p17 = raw_p17

    p14_ok = (
        isinstance(p14, Mapping)
        and bool(p14.get("all_passed"))
        and int(p14.get("factory_cal_mutation_bytes", -1)) == 0
        and int(p14.get("private_key_bytes_read", -1)) == 0
        and not faults.p2_inject_factory_cal_fault
    )
    p15_ok = (
        isinstance(p15, Mapping)
        and bool(p15.get("all_passed"))
        and bool(p15.get("secureboot_6_scenario_firewall", {}).get("passed"))
        and bool(p15.get("partition_align_6_scenario_firewall", {}).get("passed"))
        and int(p15.get("spacc_key_reads", -1)) == 0
        and not faults.p2_inject_secureboot_align_fault
    )
    p16_ok = (
        isinstance(p16, Mapping)
        and bool(p16.get("all_passed"))
        and bool(p16.get("pillar_a_ext2_installer_6_scenarios", {}).get("passed"))
        and bool(p16.get("pillar_b_p1_rescue_6_scenarios", {}).get("passed"))
        and bool(p16.get("pillar_c_tier0_lock_4_scenarios", {}).get("passed"))
        and not faults.p2_inject_ext2_p1_rescue_fault
    )
    p17_ok = (
        isinstance(p17, Mapping)
        and bool(p17.get("all_passed"))
        and bool(p17.get("pillar_a_wire_and_preflight_7_scenarios", {}).get("passed"))
        and bool(p17.get("pillar_b_dual_path_backup_6_scenarios", {}).get("passed"))
        and bool(p17.get("pillar_c_fake_iokit_regression_5_scenarios", {}).get("passed"))
        and p17.get("live_usb_iokit_transmit_enabled") is False
        and p17.get("allow_persistent_jiritsu_writes") is False
        and p17.get("allow_destructive_jiritsu_commands") is False
        and not faults.p2_inject_adjustcontrol_streaming_fault
    )

    if not p14_ok:
        errors.append("p2_p14: factory_cal_ibis_defectpixel_and_nvs_verifier failed")
    if not p15_ok:
        errors.append("p2_p15: secureboot_chain_and_partition_align_verifier failed")
    if not p16_ok:
        errors.append("p2_p16: realhw_ext2_installer_and_p1_rescue_verifier failed")
    if not p17_ok:
        errors.append("p2_p17: realhw_adjustcontrol_streaming_backup_client failed")

    for tag, obj in (("p2_p14", p14), ("p2_p15", p15), ("p2_p16", p16), ("p2_p17", p17)):
        if (
            obj.get("persistent_emmc_writes_authorized") is not False
            or obj.get("persistent_write_release") is not False
            or obj.get("allow_boot_partition_targeting") is not False
            or obj.get("allow_destructive_fastboot") is not False
        ):
            errors.append(f"{tag}: hard-locked zero-write/zero-bootpart/zero-fastboot flag breached")

    otp_touches = (
        int(meta_13["otp_fuse_touches"])
        + int(p14.get("otp_fuse_touches", 0))
        + int(p15.get("otp_fuse_touches", 0))
        + int(p15.get("otp_fuse_writes", 0))
        + int(p16.get("otp_fuse_touches", 0))
        + int(p16.get("otp_fuse_writes", 0))
        + int(p17.get("otp_fuse_touches", 0))
        + int(p17.get("otp_fuse_writes", 0))
    )
    rpmb_incs = int(meta_13["rpmb_counter_increments"])
    passive_tx = (
        int(meta_13["passive_tx_bytes_emitted"])
        + int(p14.get("passive_tx_bytes_emitted", 0))
        + int(p15.get("passive_tx_bytes_emitted", 0))
        + int(p16.get("passive_tx_bytes_emitted", 0))
        + int(p17.get("passive_tx_bytes_emitted", 0))
    )
    phys_writes = (
        int(m130_p2.evidence.get("physical_device_writes", 0))
        + int(p14.get("physical_device_writes", 0))
        + int(p15.get("physical_device_writes", 0))
        + int(p16.get("physical_device_writes", 0))
        + int(p17.get("physical_device_writes", 0))
    )
    phys_usb_bytes = int(p17.get("physical_usb_bytes_transmitted", 0)) + int(
        faults.p2_physical_usb_packets_override
    )

    if otp_touches != 0:
        errors.append(f"p2: otp_fuse_touches={otp_touches} != 0")
    if passive_tx != 0:
        errors.append(f"p2: passive_tx_bytes_emitted={passive_tx} != 0")
    if phys_writes != 0 or phys_usb_bytes != 0:
        errors.append(
            f"p2: physical_writes={phys_writes}, physical_usb_bytes={phys_usb_bytes} must both be 0"
        )

    pillar_statuses["factory_cal_ibis_defectpixel_and_nvs_verifier"] = p14_ok
    pillar_statuses["secureboot_chain_and_partition_align_verifier"] = p15_ok
    pillar_statuses["realhw_ext2_installer_and_p1_rescue_verifier"] = p16_ok
    pillar_statuses["realhw_adjustcontrol_streaming_backup_client"] = p17_ok

    # Forward-compatible support if extra recovery pillars (>= 18) are provided
    for extra_key, extra_val in raw_p14_p16.items():
        if extra_key not in (
            "p14_factory_cal_ibis_nvs",
            "p15_secureboot_partition_align",
            "p16_realhw_ext2_p1_rescue",
        ) and isinstance(extra_val, Mapping):
            extra_ok = bool(extra_val.get("all_passed"))
            pillar_statuses[extra_key] = extra_ok
            if not extra_ok:
                errors.append(f"p2_extra:{extra_key} failed")

    total_pillars = len(pillar_statuses)
    passed_pillars = sum(1 for v in pillar_statuses.values() if v)
    if total_pillars < 17 or passed_pillars < 17 or passed_pillars != total_pillars:
        errors.append(
            f"p2: recovery pillars expected >=17 and all passing, got {passed_pillars}/{total_pillars}"
        )

    passed = len(errors) == 0
    evidence = dict(m130_p2.evidence)
    evidence.update(
        {
            "recovery_pillar_count": total_pillars,
            "recovery_pillars_passed": passed_pillars,
            "pillar_statuses": pillar_statuses,
            "otp_fuse_touches": otp_touches,
            "rpmb_counter_increments": rpmb_incs,
            "passive_tx_bytes_emitted": passive_tx,
            "physical_device_writes": phys_writes,
            "physical_usb_bytes_transmitted": phys_usb_bytes,
            "p14_factory_cal_ok": p14_ok,
            "p15_secureboot_align_ok": p15_ok,
            "p16_ext2_p1_rescue_ok": p16_ok,
            "p17_adjustcontrol_streaming_ok": p17_ok,
            "p14_suite_sha256": p14.get("suite_sha256"),
            "p15_suite_sha256": p15.get("suite_sha256"),
            "p16_suite_sha256": p16.get("suite_sha256"),
            "p17_suite_sha256": p17.get("suite_sha256"),
        }
    )
    pillar = Milestone147PillarResult(
        pillar_id="P2",
        pillar_name="SEVENTEEN_PLUS_PILLAR_RECOVERY_AND_STREAMING_BACKUP",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Recovery {passed_pillars}/{total_pillars} pillars (Ph47..139; >=17 required), "
            f"SecureBoot+cnflasha15+FX3RCPT1/FX3CHK1 ok, "
            f"OTP={otp_touches}, RPMB={rpmb_incs}, usb_tx={phys_usb_bytes}B {'PASS' if passed else 'FAIL_CLOSED'}"
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
        "physical_usb_bytes_transmitted": phys_usb_bytes,
    }
    return pillar, meta


def _evaluate_pillar_3(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: RealHwMilestone147FaultInjection,
) -> Tuple[Milestone147PillarResult, Dict[str, Any]]:
    m130_p3, meta_24 = _eval_m130_p3(auditors, _fault_to_m130_faults(faults))
    errors: List[str] = list(m130_p3.errors)
    auditor_statuses: Dict[str, bool] = dict(m130_p3.evidence["auditor_statuses"])
    auditor_sha256s: Dict[str, Optional[str]] = dict(m130_p3.evidence["auditor_sha256s"])

    # #25: VP LED-Wall / ECS / FreeD / Art-Net
    a25 = auditors.get("vp_ledwall_ecs_freed_and_artnet_audit", {})
    a25_ok = isinstance(a25, Mapping) and bool(a25.get("all_checks_passed"))
    a25_pd = a25.get("pillar_d_zero_mutation_vp_guard", {})
    a25_cal = int(a25_pd.get("calibration_mutation_bytes", -1))
    a25_emmc = int(a25_pd.get("emmc_mutation_bytes", -1)) + int(faults.p3_vp_ledwall_emmc_mutation_bytes)
    if not a25_ok or a25_cal != 0 or a25_emmc != 0 or a25_pd.get("persistent_emmc_writes_authorized") is not False:
        errors.append(f"p3: #25 vp_ledwall_ecs_freed_and_artnet_audit failed (cal={a25_cal}, emmc={a25_emmc})")

    # #26: XAVC / HEVC Intra / ACES IDT / FZ100
    a26 = auditors.get("xavc_hevc_intra_aces_idt_and_fz100_audit", {})
    a26_ok = isinstance(a26, Mapping) and bool(a26.get("all_checks_passed"))
    a26_pd = a26.get("pillar_d_zero_mutation_guard", {})
    a26_cal = int(a26_pd.get("calibration_mutation_bytes", -1))
    a26_emmc = int(a26_pd.get("emmc_mutation_bytes", -1)) + int(faults.p3_xavc_fz100_emmc_mutation_bytes)
    if not a26_ok or a26_cal != 0 or a26_emmc != 0 or a26_pd.get("persistent_emmc_writes_authorized") is not False:
        errors.append(f"p3: #26 xavc_hevc_intra_aces_idt_and_fz100_audit failed (cal={a26_cal}, emmc={a26_emmc})")

    # #27: Phase 137 U2 cpapp-b.bin RTOS untouched & U3 Backup.bin 819->840 Bank 0/1
    a27 = auditors.get("realhw_cp_rtos_and_backup_bin_audit", {})
    a27_ok = isinstance(a27, Mapping) and bool(a27.get("all_checks_passed"))
    a27_p1 = a27.get("pillar1_cp_rtos_divergence", {})
    a27_p3 = a27.get("pillar3_backup_layout", {})
    a27_p4 = a27.get("pillar4_zero_flash_auth", {})
    a27_cal = int(a27_p4.get("calibration_mutation_bytes", -1))
    a27_emmc = int(a27_p4.get("emmc_mutation_bytes", -1))
    a27_spi = int(a27_p4.get("spi_nor_mutation_bytes", -1)) + int(faults.p3_realhw_cp_spi_mutation_bytes)
    if (
        not a27_ok
        or not bool(a27_p1.get("prefix_128k_identical"))
        or not bool(a27_p3.get("passed"))
        or a27_cal != 0
        or a27_emmc != 0
        or a27_spi != 0
        or a27.get("persistent_emmc_writes_authorized") is not False
        or a27.get("spi_nor_write_authorized") is not False
    ):
        errors.append(
            f"p3: #27 realhw_cp_rtos_and_backup_bin_audit failed (cal={a27_cal}, emmc={a27_emmc}, spi={a27_spi})"
        )

    # #28: Phase 140 libmpr.so (74 pass-through + 15 shimmed) + 20 MAIN DmmCfg.bin pools
    a28 = auditors.get("realhw_mpr_dmm_rec_pipeline_bridge_audit", {})
    a28_ok = isinstance(a28, Mapping) and bool(a28.get("all_checks_passed"))
    a28_p1 = a28.get("pillar1_libmpr_abi_diff", {})
    a28_p2 = a28.get("pillar2_dmm_topology", {})
    a28_p4 = a28.get("pillar4_uipc_record_lock", {})
    a28_cal = int(a28_p4.get("calibration_mutation_bytes", -1))
    a28_emmc = int(a28_p4.get("emmc_mutation_bytes", -1)) + int(faults.p3_realhw_mpr_bridge_emmc_mutation_bytes)
    dmm_units = int(a28_p2.get("fx3_dmmcfg", {}).get("target_20_units_present", -1))
    shim_syms = a28_p1.get("fx6_appfw_shim_required_symbols", ())
    if (
        not a28_ok
        or int(a28_p1.get("fx6_only_export_count", -1)) < 15
        or len(shim_syms) != 15
        or int(a28_p1.get("fx6_appfw_passthrough_count", -1)) < 12
        or a28_p1.get("direct_struct_dereference_blocked") is not True
        or dmm_units != 20
        or a28_cal != 0
        or a28_emmc != 0
        or a28.get("o_rdonly_enforced") is not True
        or a28.get("persistent_emmc_writes_authorized") is not False
    ):
        errors.append(
            f"p3: #28 realhw_mpr_dmm_rec_pipeline_bridge_audit failed (dmm_units={dmm_units}, shims={len(shim_syms)}, emmc={a28_emmc})"
        )

    for key, obj in (
        ("vp_ledwall_ecs_freed_and_artnet_audit", a25),
        ("xavc_hevc_intra_aces_idt_and_fz100_audit", a26),
        ("realhw_cp_rtos_and_backup_bin_audit", a27),
        ("realhw_mpr_dmm_rec_pipeline_bridge_audit", a28),
    ):
        auditor_statuses[key] = isinstance(obj, Mapping) and bool(obj.get("all_checks_passed"))
        sha_val = obj.get("report_sha256") or obj.get("audit_digest_sha256") if isinstance(obj, Mapping) else None
        auditor_sha256s[key] = str(sha_val) if sha_val else None

    # Forward-compatible scan of any Phase 148+ auditors present in `auditors`
    for extra_key, extra_obj in auditors.items():
        if extra_key not in auditor_statuses and isinstance(extra_obj, Mapping):
            extra_ok = bool(extra_obj.get("all_checks_passed"))
            auditor_statuses[extra_key] = extra_ok
            sha_val = extra_obj.get("report_sha256") or extra_obj.get("audit_digest_sha256")
            auditor_sha256s[extra_key] = str(sha_val) if sha_val else None
            if not extra_ok:
                errors.append(f"p3_extra: auditor {extra_key} failed")

    total_count = len(auditor_statuses)
    passed_count = sum(1 for v in auditor_statuses.values() if v)
    total_cal_mut = max(
        int(meta_24["calibration_mutation_bytes"]),
        max(0, a25_cal),
        max(0, a26_cal),
        max(0, a27_cal),
        max(0, a28_cal),
    )

    if total_count < 28 or passed_count < 28 or passed_count != total_count:
        errors.append(f"p3: expected >= 28 auditors and all passing, got {passed_count}/{total_count}")

    passed = len(errors) == 0 and total_cal_mut == 0
    evidence = dict(m130_p3.evidence)
    evidence.update(
        {
            "auditor_count": total_count,
            "passed_auditor_count": passed_count,
            "auditor_statuses": auditor_statuses,
            "auditor_sha256s": auditor_sha256s,
            "phase131_vp_ledwall_ok": a25_ok,
            "phase135_xavc_fz100_ok": a26_ok,
            "phase137_u2_u3_cp_backup_ok": a27_ok,
            "phase140_mpr_dmm_rec_bridge_ok": a28_ok,
            "calibration_mutation_bytes": total_cal_mut,
            "spi_nor_write_authorized": bool(a27.get("spi_nor_write_authorized", False)),
        }
    )
    pillar = Milestone147PillarResult(
        pillar_id="P3",
        pillar_name="TWENTY_EIGHT_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {passed_count}/{total_count} auditors (>=28 required; U2/U3/libmpr-15/DmmCfg-20), "
            f"cal_mut={total_cal_mut}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "auditor_count": total_count,
        "passed_count": passed_count,
        "calibration_mutation_bytes": total_cal_mut,
        "bk4_persistent_nvram_writes": int(meta_24["bk4_persistent_nvram_writes"]),
    }
    return pillar, meta


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: RealHwMilestone147FaultInjection,
) -> Tuple[Milestone147PillarResult, Dict[str, Any]]:
    m130_p4, meta_21 = _eval_m130_p4(vm_rep, _fault_to_m130_faults(faults))
    errors: List[str] = list(m130_p4.errors)
    stage_statuses: Dict[str, bool] = dict(m130_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_24_STAGE_KEYS[21:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if not ok:
            errors.append(f"p4: VM co-emulation {skey} failed")

    # Stage 22: MXF / PTPv2 / Tally / Monsoon HIL
    s22 = vm_rep.get("stage22_mxf_ptpv2_tally_monsoon_hil", {})
    s22_emmc = int(s22.get("emmc_mutation_bytes", -1)) + int(faults.p4_stage22_emmc_mutation_bytes)
    if (
        int(s22.get("nop_count", -1)) != 0
        or int(s22.get("cp_mutation_bytes", -1)) != 0
        or int(s22.get("wbi_mutation_bytes", -1)) != 0
        or int(s22.get("calibration_mutation_bytes", -1)) != 0
        or int(s22.get("nvram_persistent_writes", -1)) != 0
        or int(s22.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(s22.get("physical_device_writes", -1)) != 0
        or s22.get("persistent_emmc_writes_authorized") is not False
        or s22_emmc != 0
        or int(s22.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(f"p4: Stage 22 redlines violated (emmc_mut={s22_emmc})")

    # Stage 23: VP LED-Wall / FreeD / Art-Net HIL
    s23 = vm_rep.get("stage23_vp_ledwall_freed_artnet_hil", {})
    s23_emmc = int(s23.get("emmc_mutation_bytes", -1)) + int(faults.p4_stage23_emmc_mutation_bytes)
    if (
        int(s23.get("nop_count", -1)) != 0
        or int(s23.get("cp_mutation_bytes", -1)) != 0
        or int(s23.get("wbi_mutation_bytes", -1)) != 0
        or int(s23.get("calibration_mutation_bytes", -1)) != 0
        or int(s23.get("nvram_persistent_writes", -1)) != 0
        or int(s23.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(s23.get("physical_device_writes", -1)) != 0
        or s23.get("persistent_emmc_writes_authorized") is not False
        or s23_emmc != 0
        or int(s23.get("wf12_00342260_hits", -1)) != 0
        or int(s23.get("flash_split_band_frames", -1)) != 0
        or int(s23.get("cxd90057_pin_damage_events", -1)) != 0
        or int(s23.get("imx510_sensor_burn_events", -1)) != 0
        or int(s23.get("ibis_endstop_slam_events", -1)) != 0
        or int(s23.get("ibis_coil_thermal_runaway_events", -1)) != 0
    ):
        errors.append(f"p4: Stage 23 redlines violated (emmc_mut={s23_emmc})")

    # Stage 24: Phase 141 Real-HW Pre-Flash 4-State Dual-Boot HIL
    s24 = vm_rep.get("stage24_realhw_preflash_dualboot_hil", {})
    s24_emmc = int(s24.get("emmc_mutation_bytes", -1)) + int(faults.p4_stage24_emmc_mutation_bytes)
    s24_spi = int(s24.get("spi_nor_mutation_bytes", -1)) + int(faults.p4_stage24_spi_nor_mutation_bytes)
    s24_sec0 = int(s24.get("sector0_mutation_bytes", -1)) + int(faults.p4_stage24_sector0_mutation_bytes)
    s24_rsv = int(s24.get("rsv_orphan_count", -1)) + int(faults.p4_stage24_rsv_orphan_count)
    if (
        int(s24.get("nop_count", -1)) != 0
        or int(s24.get("cp_mutation_bytes", -1)) != 0
        or int(s24.get("wbi_mutation_bytes", -1)) != 0
        or int(s24.get("calibration_mutation_bytes", -1)) != 0
        or int(s24.get("nvram_persistent_writes", -1)) != 0
        or int(s24.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(s24.get("physical_device_writes", -1)) != 0
        or s24.get("persistent_emmc_writes_authorized") is not False
        or s24_emmc != 0
        or s24_spi != 0
        or s24_sec0 != 0
        or s24_rsv != 0
        or int(s24.get("wf12_00342260_hits", -1)) != 0
    ):
        errors.append(
            f"p4: Stage 24 redlines violated (emmc={s24_emmc}, spi={s24_spi}, sec0={s24_sec0}, rsv={s24_rsv})"
        )

    # Forward-compatible discovery of Stage 25+ keys
    for extra_key, extra_val in vm_rep.items():
        if (
            _VM_STAGE_KEY_RE.match(str(extra_key))
            and extra_key not in stage_statuses
            and isinstance(extra_val, Mapping)
        ):
            extra_ok = bool(extra_val.get("all_checks_passed"))
            stage_statuses[str(extra_key)] = extra_ok
            if not extra_ok:
                errors.append(f"p4_extra: VM stage {extra_key} failed")

    total_stages = len(stage_statuses)
    passed_stages = sum(1 for v in stage_statuses.values() if v)
    emmc_corruptions = (
        int(meta_21.get("emmc_flash_mutation_bytes", 0))
        + max(0, s22_emmc)
        + max(0, s23_emmc)
        + max(0, s24_emmc)
    )
    total_wf12_hits = (
        int(meta_21.get("wf12_00342260_hits", 0))
        + max(0, int(s22.get("wf12_00342260_hits", 0)))
        + max(0, int(s23.get("wf12_00342260_hits", 0)))
        + max(0, int(s24.get("wf12_00342260_hits", 0)))
    )

    if total_stages < 24 or passed_stages < 24 or passed_stages != total_stages:
        errors.append(f"p4: expected >= 24 VM stages and all passing, got {passed_stages}/{total_stages}")
    if emmc_corruptions != 0:
        errors.append(f"p4: emmc_corruptions={emmc_corruptions} != 0")

    passed = len(errors) == 0
    evidence = dict(m130_p4.evidence)
    evidence.update(
        {
            "stage_count": total_stages,
            "passed_stage_count": passed_stages,
            "stage_statuses": stage_statuses,
            "emmc_corruptions": emmc_corruptions,
            "wf12_00342260_hits": total_wf12_hits,
            "stage22_digest_sha256": s22.get("phase127_audit_digest_sha256"),
            "stage23_digest_sha256": s23.get("phase132_audit_digest_sha256"),
            "stage24_digest_sha256": s24.get("phase141_audit_digest_sha256"),
        }
    )
    pillar = Milestone147PillarResult(
        pillar_id="P4",
        pillar_name="TWENTY_FOUR_PLUS_STAGE_VM_HIL_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {passed_stages}/{total_stages} stages (>=24 required; 4-State Dual-Boot HIL), "
            f"emmc_corruptions={emmc_corruptions}, wf12_hits={total_wf12_hits} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "stage_count": total_stages,
        "passed_count": passed_stages,
        "cp_mutation_bytes": meta_21["cp_mutation_bytes"],
        "bk4_persistent_nvram_writes": meta_21["bk4_persistent_nvram_writes"],
        "wf12_00342260_hits": total_wf12_hits,
        "emmc_corruptions": emmc_corruptions,
    }
    return pillar, meta


def _evaluate_pillar_5(
    raw_p136: Mapping[str, Any],
    raw_p143: Mapping[str, Any],
    faults: RealHwMilestone147FaultInjection,
) -> Tuple[Milestone147PillarResult, Dict[str, Any]]:
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
    }
    pillar = Milestone147PillarResult(
        pillar_id="P5",
        pillar_name="CLOSURE_U4_U5_U6_AND_BYOF_SD_STAGEB_H0_H3",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Ph136(U4/U5/U6={u4_u5_u6_closed}, cmds={u6_cmd_count}) + "
            f"Ph143(EH1={eh1_us}us<=50us, H0==H3 {h0_eq_h3_count}/{surface_count}, "
            f"cnflasha15=True) {'PASS' if passed else 'FAIL_CLOSED'}"
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
    }
    return pillar, meta


def _evaluate_pillar_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: RealHwMilestone147FaultInjection,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
    p5_meta: Mapping[str, Any],
) -> Tuple[Milestone147PillarResult, Dict[str, Any]]:
    errors: List[str] = []

    r28, r28_source = _load_round28_or_29_summary(28, repo_root=repo_root, use_clean_room=use_clean_room)
    r29, r29_source = _load_round28_or_29_summary(29, repo_root=repo_root, use_clean_room=use_clean_room)

    if faults.p6_r29_tamper_schema:
        r29 = copy.deepcopy(r29)
        r29["schema"] = "tampered-invalid-schema"

    total_nops = 0
    total_crashes = 0
    total_emmc = 0

    # Round 28 verification
    r28_schema = str(r28.get("schema", ""))
    r28_kver = str(r28.get("kernel_version", ""))
    if r28_schema != ROUND28_EXPECTED_SCHEMA:
        errors.append(f"p6_r28: unexpected schema {r28_schema!r}")
    if "4.9.337-scel+" not in r28_kver:
        errors.append(f"p6_r28: unexpected kernel_version {r28_kver!r}")
    r28_audit = r28.get("r28_realhw_escape_hatch_audit", {})
    for bkey in (
        "all_3_runs_crashes_zero",
        "all_3_runs_emmc_write_zero",
        "r28a_stock_fx3_bypass_verified",
        "r28b_libjit_probe_verified",
        "r28b_strategy_a_bridge_verified",
        "r28b_stageb_big6_verified",
        "r28c_tamper_fail_closed_under_50ms",
    ):
        if not bool(r28_audit.get(bkey, False)):
            errors.append(f"p6_r28: audit flag {bkey} is False")

    r28_runs_map = r28.get("runs", {})
    r28_verified = 0
    for rid, exp_faithful in ROUND28_RUN_SPECS:
        robj = r28_runs_map.get(rid)
        if not isinstance(robj, Mapping):
            errors.append(f"p6_r28: missing run {rid}")
            continue
        rnop = (
            int(faults.p6_r28_nop_count_override)
            if faults.p6_r28_nop_count_override is not None
            else int(robj.get("nop_count", -1))
        )
        rcrash = (
            int(faults.p6_r28_crashes_override)
            if faults.p6_r28_crashes_override is not None
            else int(robj.get("crashes", -1))
        )
        remmc = (
            int(faults.p6_r28_emmc_writes_override)
            if faults.p6_r28_emmc_writes_override is not None
            else int(robj.get("emmc_write_count", -1))
        )
        total_nops += max(0, rnop)
        total_crashes += max(0, rcrash)
        total_emmc += max(0, remmc)
        fi = robj.get("faithful_invariants", {})
        sb = robj.get("stage_b", {})
        if (
            rnop != 0
            or rcrash != 0
            or remmc != 0
            or int(fi.get("FX6_NATIVE_FAITHFUL", -1)) != exp_faithful
            or int(sb.get("manifest_count", -1)) != 13
        ):
            errors.append(
                f"p6_r28:{rid}: failed invariants (nop={rnop}, crash={rcrash}, emmc={remmc}, faithful={fi.get('FX6_NATIVE_FAITHFUL')})"
            )
            continue
        r28_verified += 1

    # Round 29 verification
    r29_schema = str(r29.get("schema", ""))
    r29_kver = str(r29.get("kernel_version", ""))
    if r29_schema != ROUND29_EXPECTED_SCHEMA:
        errors.append(f"p6_r29: unexpected schema {r29_schema!r}")
    if "4.9.337-scel+" not in r29_kver:
        errors.append(f"p6_r29: unexpected kernel_version {r29_kver!r}")
    r29_audit = r29.get("r29_realhw_atomic_installer_mpr_rec_audit", {})
    for bkey in (
        "all_3_runs_crashes_zero",
        "all_3_runs_emmc_write_zero",
        "r29a_atomic_install_ok",
        "r29a_mpr_param_and_rec_finalized",
        "r29a_stageb_big6_verified",
        "r29b_midwrite_atomic_rollback_verified",
        "r29c_p1_oneshot_mode_clear_verified",
    ):
        if not bool(r29_audit.get(bkey, False)):
            errors.append(f"p6_r29: audit flag {bkey} is False")

    r29_runs_map = r29.get("runs", {})
    r29_verified = 0
    for rid, exp_faithful in ROUND29_RUN_SPECS:
        robj = r29_runs_map.get(rid)
        if not isinstance(robj, Mapping):
            errors.append(f"p6_r29: missing run {rid}")
            continue
        rnop = (
            int(faults.p6_r29_nop_count_override)
            if faults.p6_r29_nop_count_override is not None
            else int(robj.get("nop_count", -1))
        )
        rcrash = (
            int(faults.p6_r29_crashes_override)
            if faults.p6_r29_crashes_override is not None
            else int(robj.get("crashes", -1))
        )
        remmc = (
            int(faults.p6_r29_emmc_writes_override)
            if faults.p6_r29_emmc_writes_override is not None
            else int(robj.get("emmc_write_count", -1))
        )
        total_nops += max(0, rnop)
        total_crashes += max(0, rcrash)
        total_emmc += max(0, remmc)
        fi = robj.get("faithful_invariants", {})
        sb = robj.get("stage_b", {})
        if (
            rnop != 0
            or rcrash != 0
            or remmc != 0
            or int(fi.get("FX6_NATIVE_FAITHFUL", -1)) != exp_faithful
            or int(sb.get("manifest_count", -1)) != 13
        ):
            errors.append(
                f"p6_r29:{rid}: failed invariants (nop={rnop}, crash={rcrash}, emmc={remmc}, faithful={fi.get('FX6_NATIVE_FAITHFUL')})"
            )
            continue
        r29_verified += 1

    # Cross-pillar hardware-lock invariants
    if p1_meta.get("persistent_emmc_writes_authorized") is not False or p1_meta.get(
        "simulated_ready_for_hardware_attach"
    ) is not False:
        errors.append("p6: P1 hardware-lock invariant breached")
    if (
        int(p2_meta.get("otp_fuse_touches", -1)) != 0
        or int(p2_meta.get("rpmb_counter_increments", -1)) != 0
        or int(p2_meta.get("passive_tx_bytes_emitted", -1)) != 0
        or int(p2_meta.get("physical_usb_bytes_transmitted", -1)) != 0
    ):
        errors.append("p6: P2 zero-touch OTP/RPMB/passive-UART/USB-TX invariant breached")
    if int(p3_meta.get("calibration_mutation_bytes", -1)) != 0:
        errors.append("p6: P3 calibration zero-mutation invariant breached")
    if (
        int(p4_meta.get("cp_mutation_bytes", -1)) != 0
        or int(p4_meta.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(p4_meta.get("wf12_00342260_hits", -1)) != 0
        or int(p4_meta.get("emmc_corruptions", -1)) != 0
    ):
        errors.append("p6: P4 CP/BK4/WF-12/eMMC zero-mutation invariant breached")
    if int(p5_meta.get("h0_equals_h3_count", -1)) != 16:
        errors.append("p6: P5 H0 == H3 16/16 invariant breached")

    passed = (
        len(errors) == 0
        and r28_verified == len(ROUND28_RUN_SPECS)
        and r29_verified == len(ROUND29_RUN_SPECS)
        and total_nops == 0
        and total_crashes == 0
        and total_emmc == 0
    )
    evidence = {
        "r28_source": r28_source,
        "r28_schema": r28_schema,
        "r28_runs_verified": r28_verified,
        "r29_source": r29_source,
        "r29_schema": r29_schema,
        "r29_runs_verified": r29_verified,
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
        "milestone130_schema_anchor": MILESTONE130_SCHEMA_VERSION,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
    }
    pillar = Milestone147PillarResult(
        pillar_id="P6",
        pillar_name="REAL_FX3_702_QEMU_R28_R29_REHEARSAL_RECEIPTS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Live FX3 7.02 QEMU R28={r28_verified}/3 ({r28_source}), R29={r29_verified}/3 ({r29_source}), "
            f"nop={total_nops}, crashes={total_crashes}, emmc={total_emmc} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "r28_runs_verified": r28_verified,
        "r29_runs_verified": r29_verified,
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
    }
    return pillar, meta


# ---------------------------------------------------------------------------
# Parallel Collector, Builder & Fail-Closed Verifier
# ---------------------------------------------------------------------------


def _collect_parallel_milestone147_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: RealHwMilestone147FaultInjection,
) -> Tuple[
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
]:
    fault_dict = _fault_to_worker_dict(faults)
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
    )

    try:
        ctx = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=20, mp_context=ctx) as ex:
            # Submit heaviest tasks first so all long paths run concurrently in wave 1
            fut_5a = ex.submit(_worker_phase136, use_clean_room)
            fut_2m = ex.submit(_worker_recovery_master, use_clean_room)
            fut_4 = ex.submit(_worker_pillar_4, use_clean_room)
            fut_2b = ex.submit(
                _worker_pillar_b,
                (
                    use_clean_room,
                    {
                        "pillar_b_inject_cross_body_cnflasha_transplant": bool(
                            faults.p2_inject_cross_body_cnflasha_transplant
                        )
                    },
                ),
            )
            fut_3 = [ex.submit(_worker_pillar_3_batch, (batch, use_clean_room)) for batch in p3_batches]
            fut_2w = ex.submit(_worker_recovery_p17, use_clean_room)
            fut_5b = ex.submit(
                _worker_phase143,
                (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room),
            )
            fut_2z = ex.submit(_worker_recovery_p14_to_p16, use_clean_room)
            fut_1 = ex.submit(_worker_pillar_1, (str(repo_root), use_clean_room, fault_dict))
            fut_2y = ex.submit(_worker_recovery_p11_to_p13, use_clean_room)
            fut_2x = ex.submit(_worker_recovery_p8_p9_p10, use_clean_room)
            fut_2a = ex.submit(_worker_domain_2, (use_clean_room, fault_dict))

            raw_1 = fut_1.result()
            raw_2m = fut_2m.result()
            raw_2x = fut_2x.result()
            raw_2y = fut_2y.result()
            raw_2z = fut_2z.result()
            raw_2w = fut_2w.result()
            raw_2a = fut_2a.result()
            raw_2b = fut_2b.result()
            auditors: Dict[str, Dict[str, Any]] = {}
            for fg in fut_3:
                auditors.update(fg.result())
            raw_4 = fut_4.result()
            raw_5a = fut_5a.result()
            raw_5b = fut_5b.result()
            return (
                raw_1,
                raw_2m,
                raw_2x,
                raw_2y,
                raw_2z,
                raw_2w,
                raw_2a,
                raw_2b,
                auditors,
                raw_4,
                raw_5a,
                raw_5b,
            )
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1 = _worker_pillar_1((str(repo_root), use_clean_room, fault_dict))
    raw_2m = _worker_recovery_master(use_clean_room)
    raw_2x = _worker_recovery_p8_p9_p10(use_clean_room)
    raw_2y = _worker_recovery_p11_to_p13(use_clean_room)
    raw_2z = _worker_recovery_p14_to_p16(use_clean_room)
    raw_2w = _worker_recovery_p17(use_clean_room)
    raw_2a = _worker_domain_2((use_clean_room, fault_dict))
    raw_2b = _worker_pillar_b(
        (
            use_clean_room,
            {
                "pillar_b_inject_cross_body_cnflasha_transplant": bool(
                    faults.p2_inject_cross_body_cnflasha_transplant
                )
            },
        )
    )
    auditors = {}
    for batch in p3_batches:
        auditors.update(_worker_pillar_3_batch((batch, use_clean_room)))
    raw_4 = _worker_pillar_4(use_clean_room)
    raw_5a = _worker_phase136(use_clean_room)
    raw_5b = _worker_phase143((str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room))
    return raw_1, raw_2m, raw_2x, raw_2y, raw_2z, raw_2w, raw_2a, raw_2b, auditors, raw_4, raw_5a, raw_5b


def build_realhw_milestone147_master_gate_report(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[RealHwMilestone147FaultInjection] = None,
) -> RealHwMilestone147MasterGateReport:
    """Build & evaluate the unified Phase 147 6-Pillar Real-Hardware Bench Readiness Master Gate."""
    use_clean_room = _is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    active_faults = faults or RealHwMilestone147FaultInjection()

    (
        raw_1,
        raw_2m,
        raw_2x,
        raw_2y,
        raw_2z,
        raw_2w,
        raw_2a,
        raw_2b,
        auditors,
        raw_4,
        raw_5a,
        raw_5b,
    ) = _collect_parallel_milestone147_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )

    p1 = _evaluate_pillar_1(raw_1)
    p2, meta_2 = _evaluate_pillar_2(
        raw_2m, raw_2x, raw_2y, raw_2z, raw_2w, raw_2a, raw_2b, active_faults
    )
    p3, meta_3 = _evaluate_pillar_3(auditors, active_faults)
    p4, meta_4 = _evaluate_pillar_4(raw_4, active_faults)
    p5, meta_5 = _evaluate_pillar_5(raw_5a, raw_5b, active_faults)
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

    pillars: Tuple[Milestone147PillarResult, ...] = (p1, p2, p3, p4, p5, p6)
    passed_count = sum(1 for p in pillars if p.passed)
    failed_ids = tuple(p.pillar_id for p in pillars if not p.passed)
    all_errors: List[str] = []
    for p in pillars:
        all_errors.extend(p.errors)

    all_ready = passed_count == len(pillars) and len(all_errors) == 0
    mode_str = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"

    payload_no_sha: Dict[str, Any] = {
        "schema_version": REALHW_MILESTONE147_SCHEMA,
        "phase_version": PHASE_147_VERSION,
        "verification_mode": mode_str,
        "all_pillars_milestone_ready": all_ready,
        "status": STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "hardware_live_attachment_requirements": HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "wbi_p5_write_and_hibernation_forbidden": WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        "cp_mutation_bytes": meta_4["cp_mutation_bytes"],
        "wbi_mutation_bytes": WBI_MUTATION_BYTES,
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
        "gate44_total_gates": raw_1["total_gates"],
        "gate44_offline_verified": raw_1["offline_verified_gates"],
        "gate44_simulated_verified": raw_1["sim_verified_gates"],
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
        "r28_runs_verified": meta_6["r28_runs_verified"],
        "r29_runs_verified": meta_6["r29_runs_verified"],
        "qemu_real_kernel_nop_count": meta_6["qemu_real_kernel_nop_count"],
        "qemu_real_kernel_crashes": meta_6["qemu_real_kernel_crashes"],
        "qemu_real_kernel_emmc_writes": meta_6["qemu_real_kernel_emmc_writes"],
        "errors": tuple(all_errors),
    }
    digest = compute_milestone147_sha256(payload_no_sha)

    return RealHwMilestone147MasterGateReport(
        schema_version=REALHW_MILESTONE147_SCHEMA,
        phase_version=PHASE_147_VERSION,
        verification_mode=mode_str,
        all_pillars_milestone_ready=all_ready,
        status=STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        hardware_live_attachment_requirements=HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        wbi_p5_write_and_hibernation_forbidden=WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        cp_mutation_bytes=meta_4["cp_mutation_bytes"],
        wbi_mutation_bytes=WBI_MUTATION_BYTES,
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
        gate44_total_gates=raw_1["total_gates"],
        gate44_offline_verified=raw_1["offline_verified_gates"],
        gate44_simulated_verified=raw_1["sim_verified_gates"],
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
        r28_runs_verified=meta_6["r28_runs_verified"],
        r29_runs_verified=meta_6["r29_runs_verified"],
        qemu_real_kernel_nop_count=meta_6["qemu_real_kernel_nop_count"],
        qemu_real_kernel_crashes=meta_6["qemu_real_kernel_crashes"],
        qemu_real_kernel_emmc_writes=meta_6["qemu_real_kernel_emmc_writes"],
        errors=tuple(all_errors),
        milestone147_sha256=digest,
    )


def verify_realhw_milestone147_master_gate(
    report: object,
) -> RealHwMilestone147VerifyResult:
    """Fail-closed verifier for a Milestone Phase 147 Real-Hardware Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, RealHwMilestone147MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return RealHwMilestone147VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone147_sha256="",
            observed_milestone147_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or RealHwMilestone147MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = payload.get("schema_version") == REALHW_MILESTONE147_SCHEMA
    if not schema_ok:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r}")

    expected_sha = compute_milestone147_sha256(payload)
    observed_sha = str(payload.get("milestone147_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(f"milestone147_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}")

    redlines_ok = (
        payload.get("o_rdonly_enforced") is True
        and payload.get("persistent_emmc_writes_authorized") is False
        and payload.get("persistent_write_release") is False
        and payload.get("spi_nor_write_authorized") is False
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
    )
    if not redlines_ok:
        errors.append("hard-locked zero-write / zero-SPI-NOR / zero-USB-TX / zero-attach redlines breached")

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
        int(payload.get("gate44_total_gates", -1)) >= 44
        and int(payload.get("gate44_offline_verified", -1)) >= 41
        and int(payload.get("gate44_simulated_verified", -1)) >= 44
        and int(payload.get("recovery_pillar_count", -1)) >= 17
        and int(payload.get("recovery_pillars_passed", -1))
        == int(payload.get("recovery_pillar_count", -2))
        and int(payload.get("firmware_lab_auditor_count", -1)) >= 28
        and int(payload.get("firmware_lab_auditors_passed", -1))
        == int(payload.get("firmware_lab_auditor_count", -2))
        and int(payload.get("vm_coemulation_stage_count", -1)) >= 24
        and int(payload.get("vm_coemulation_stages_passed", -1))
        == int(payload.get("vm_coemulation_stage_count", -2))
        and int(payload.get("vm_emmc_corruptions", -1)) == 0
        and int(payload.get("vm_wf12_00342260_hits", -1)) == 0
        and int(payload.get("p136_u6_command_count", -1)) >= 19
        and payload.get("p136_u4_u5_u6_closed") is True
        and int(payload.get("p143_sd_escape_absent_us", 999)) <= 50
        and int(payload.get("p143_h0_equals_h3_count", -1)) == 16
        and int(payload.get("p143_h0_h3_surface_count", -1)) == 16
        and int(payload.get("r28_runs_verified", -1)) == len(ROUND28_RUN_SPECS)
        and int(payload.get("r29_runs_verified", -1)) == len(ROUND29_RUN_SPECS)
        and int(payload.get("qemu_real_kernel_nop_count", -1)) == 0
        and int(payload.get("qemu_real_kernel_crashes", -1)) == 0
        and int(payload.get("qemu_real_kernel_emmc_writes", -1)) == 0
    )
    if not counts_ok:
        errors.append("milestone147 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append("all_pillars_milestone_ready / status is not MILESTONE_147_BENCH_READINESS_VERIFIED")

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 147 payload")

    valid = bool(schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0)
    return RealHwMilestone147VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone147_sha256=expected_sha,
        observed_milestone147_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


def render_milestone147_markdown(report: RealHwMilestone147MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 147 Master Gate."""
    lines = [
        f"# Real-Hardware Bench Readiness Milestone Phase 147 Master Gate (`{report.schema_version}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone147_sha256}`",
        "",
        "## Hard-Locked Safety Redlines / 硬锁定安全红线",
        f"- `persistent_emmc_writes_authorized = {report.persistent_emmc_writes_authorized}`, "
        f"`spi_nor_write_authorized = {report.spi_nor_write_authorized}`, "
        f"`physical_usb_packets_emitted = {report.physical_usb_packets_emitted}`",
        f"- `persistent_write_release = {report.persistent_write_release}`, "
        f"`hardware_live_attachment_authorized = {report.hardware_live_attachment_authorized}`",
        f"- `otp_fuse_touches = {report.otp_fuse_touches}`, `rpmb_counter_increments = {report.rpmb_counter_increments}`, `passive_tx_bytes_emitted = {report.passive_tx_bytes_emitted}`",
        f"- `cp_mutation_bytes = {report.cp_mutation_bytes}`, `wbi_mutation_bytes = {report.wbi_mutation_bytes}`, `calibration_mutation_bytes = {report.calibration_mutation_bytes}`",
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
            "## Key Bench-Readiness Metrics / 实机就绪关键指标",
            f"- 44-Gate Preflight (`G01..G44`): offline=`{report.gate44_offline_verified}/{report.gate44_total_gates}` (`G10..G12` locked), simulated=`{report.gate44_simulated_verified}/{report.gate44_total_gates}`",
            f"- Recovery & Streaming Cold-Backup (`Ph47..139`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`>=17` required; `FX3RCPT1` + `FX3CHK1` + `/dev/cnflasha15`)",
            f"- Firmware-Lab Auditors (`Ph1..140`): `{report.firmware_lab_auditors_passed}/{report.firmware_lab_auditor_count}` (`>=28` required; `U2`, `U3`, `libmpr.so` 74+15, `DmmCfg.bin` 20 pools)",
            f"- VM Co-Emulation (`Ph33..141`): `{report.vm_coemulation_stages_passed}/{report.vm_coemulation_stage_count}` (`>=24` required; `emmc_corruptions={report.vm_emmc_corruptions}`, `wf12_hits={report.vm_wf12_00342260_hits}`)",
            f"- Closure (`Ph136 + Ph143`): `U4/U5/U6={report.p136_u4_u5_u6_closed}` (`U6 cmds={report.p136_u6_command_count}`), SD absent escape=`{report.p143_sd_escape_absent_us}us <= 50us`, `H0 == H3`=`{report.p143_h0_equals_h3_count}/{report.p143_h0_h3_surface_count}`",
            f"- Live FX3 `7.02` (`4.9.337-scel+`) QEMU Receipts: Round 28=`{report.r28_runs_verified}/3`, Round 29=`{report.r29_runs_verified}/3`, `nop={report.qemu_real_kernel_nop_count}`, `crashes={report.qemu_real_kernel_crashes}`, `emmc_writes={report.qemu_real_kernel_emmc_writes}`",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "CALIBRATION_MUTATION_BYTES",
    "CP_MUTATION_BYTES",
    "DEFAULT_REPO_ROOT",
    "FIRMWARE_LAB_28_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "MILESTONE147_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "P8_CP_MUTATION_FORBIDDEN",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_147_VERSION",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "REALHW_MILESTONE147_SCHEMA",
    "RECOVERY_17_PILLAR_IDS",
    "ROUND28_EXPECTED_SCHEMA",
    "ROUND28_RUN_SPECS",
    "ROUND28_SUMMARY_RELPATH",
    "ROUND29_EXPECTED_SCHEMA",
    "ROUND29_RUN_SPECS",
    "ROUND29_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "SCHEMA_VERSION",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "VM_COEMULATION_24_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone147PillarResult",
    "RealHwMilestone147FaultInjection",
    "RealHwMilestone147MasterGateReport",
    "RealHwMilestone147VerifyResult",
    "_load_round28_or_29_summary",
    "build_realhw_milestone147_master_gate_report",
    "compute_milestone147_sha256",
    "render_milestone147_markdown",
    "verify_realhw_milestone147_master_gate",
]
