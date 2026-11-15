"""Phase 110 — 6-Pillar Century+10 Master Gate (`stage_b_milestone110_master_gate_v1`).

Composes all six Milestone Phase 110 engineering & safety pillars (`P1 .. P6`) into a single
tamper-evident, fail-closed certificate executing in `< 2.5s` across both
`LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:

- `P1` (`SAFETY_32GATE_MASTER_PREFLIGHT`):
  Runs Phase 104 `pl_cantilever_dummybatt_and_32gate_guard.evaluate_32gate_preflight`
  (`G01..G32`), verifying `>= 29/32` offline hardware-truth block (`overall_ready_for_hardware_attach=False`)
  vs `>= 32/32` simulated rehearsal (`dry_run_rehearsal_only=True`, `persistent_emmc_writes_authorized=False`),
  covering `G21..G30` (XLR +48V, gimbal/laser/shutter, Magnus dew-point TEC, PMIC 5V 900 mA/USB-C droop,
  intake occlusion, tripod/housing heat, curtain shock, sub-zero/altitude, wireless TX EMI, 12h exFAT),
  plus `G31` (heavy PL-to-E cantilever bending-moment & 15mm LWS / clamp-on matte-box guard) and
  `G32` (14.8V/26V V-Mount -> NP-FZ100 dummy-battery >8.4V OVP crowbar & InfoLITHIUM NTC guard).
- `P2` (`TEN_PILLAR_RECOVERY_MASTER_SUITE`):
  Verifies all `>= 10` recovery & unbrick pillars (`Phases 47..106`):
  - Pillars 1..7 (`run_recovery_master_suite`): macOS USB transport guard, RP2040-Zero 1.8V `-DOPEN_DRAIN`
    bench fixture, init2 SD sentinel escape / WDT / FAT12+FAT16 swap, GF(256) P+Q 2-erasure/1-bitrot healer
    & cross-body `cnflasha` lock, `CXD90057` OTP/RPMB monotonic anti-rollback + `EXT_CSD` perm-WP block
    (`otp_fuse_touches == 0`, `rpmb_counter_increments == 0`), Tier-0..4 escalation ladder & passive 1.8V
    RX-only UART boot-stage decoder (`S0..S6`, `10/10` scenarios, `passive_tx_bytes_emitted == 0`).
  - Pillar 8 (`run_gpt_rpmb_and_rescue_bundle_suite`): CXD90057 15-partition GPT CRC32 heal, RPMB HMAC-SHA256
    replay guard (`rpmb_writes_emitted == 0`), and two-man offline SD rescue bundle.
  - Pillar 9 (`run_ramdisk_overlay_and_emmc_health_suite`): SVR4 `newc` cpio traversal/setuid/blk firewall,
    JEDEC `EXT_CSD [267..269]` Pre-EOL/`<=80%` wear & `[179]` `BOOT0` audit, and volatile `tmpfs`/`overlayfs`
    block-mount isolation.
  - Pillar 10 (`run_fdt_bootargs_and_kernel_suite`): FDT `0xd00dfeed` `/chosen/bootargs` (`ro` + `rootwait` +
    WDT active) & ARM64 `0x644d5241` FX3 `4.9.337-scel+` kernel Image verification with FX6 cross-SKU block.
- `P3` (`TWENTY_PLUS_FIRMWARE_LAB_AUDITORS`):
  Verifies `>= 20` `fx3_firmware_lab` auditors (`Phases 1..105`), forward-compatible with Phase 111+ auditors
  (`passed_auditor_count >= 20` and `passed_auditor_count == auditor_count`), including #1..#16 plus
  #17 (`metadata_gyro_catalyst_and_anamorphic_audit`, Phase 89), #18 (`interval_cache_and_ftp_audit`, Phase 93),
  #19 (`lut3d_cube_tetrahedral_and_sdi_hdmi_audit`, Phase 98), and #20 (`c2pa_lens_shading_and_mc_fleet_audit`,
  Phase 105).
- `P4` (`EIGHTEEN_PLUS_STAGE_VM_COEMULATION`):
  Verifies `>= 18` `outputs/fx3-vm` heterogeneous AArch64 AP + ARM32 Thumb-2 Stock-CP co-emulation stages
  (`Phases 33..107`), forward-compatible with Stage 19+ (`passed_stage_count >= 18` and
  `passed_stage_count == stage_count`), verifying `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`,
  `nvram_persistent_writes == 0`, `wf12_00342260_hits == 0`, `cnflasha_mutation_bytes == 0`,
  `private_key_reads == 0`, and `private_key_exports == 0`.
- `P5` (`REAL_KERNEL_R14_R17_R19_COMPLETE_UI_CLOSURES`):
  Verifies Round 14 (`18/18` 4-language x 3-surface pixel deltas `> 0`), Round 17 (`10/10` Status Check
  `0x2f..0x37,0x39` complete ring: `C(10,2)=45` pairwise pixel deltas `> 0` + `10`-step wrap-around +
  4-category 3-layer menu deltas + `WF-12 0x00342260` Tab 9 Network immunity), and Round 19 (`11/11` Full-Menu
  L1 shooting-mode rail: `C(11,2)=55` pairwise pixel deltas `> 0` + `11`-step wrap-around + `ZH-TW` Network vs
  `ZH-CN` delta `> 0` + `WF-12` `ZH-TW` immunity) on unmodified FX3 `7.02` kernel (`4.9.337-scel+`,
  `nop_count == 0`, `crashes == 0`, `13/13` Stage-B SHA-256).
- `P6` (`POST_TRIAL_H0_VS_H2_IMMUTABILITY_AND_HARDWARE_LOCK_PROOF`):
  Verifies Dossier v3 (`stage_b_release_dossier_v3`), Capstone 22-Gate (`stage_b_capstone_22gate_v1`),
  Milestone 90 (`stage_b_milestone90_master_gate_v1`), and `H0 == H2` 16-surface bit-for-bit post-trial
  immutability (`drifted_surface_count == 0`, `c2pa_rq_lic_intact == True`, `spacc_cnflasha_untouched == True`,
  `10/10` tamper scenarios) plus global hardware-lock invariants (`persistent_emmc_writes_authorized == False`,
  `otp_fuse_touches == 0`, `passive_tx_bytes_emitted == 0`).

Hard-Locked Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `P8_CP_MUTATION_FORBIDDEN = True`, `CP_MUTATION_BYTES = 0`
- `WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN = True`, `WBI_MUTATION_BYTES = 0`
- `CALIBRATION_MUTATION_BYTES = 0`, `USB_OR_CAMERA_OPERATIONS = 0`
- `OTP_FUSE_TOUCHES = 0`, `RPMB_COUNTER_INCREMENTS = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


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

from fx3_firmware_lab.c2pa_lens_shading_and_mc_fleet_auditor import (  # noqa: E402
    analyze_c2pa_lens_shading_and_mc_fleet,
    c2pa_lens_shading_and_mc_fleet_report_to_dict,
)
from fx3_firmware_lab.falsecolor_lpcm_tc_ub_auditor import (  # noqa: E402
    analyze_falsecolor_lpcm_tc_ub,
    falsecolor_lpcm_tc_ub_report_to_dict,
)
from fx3_firmware_lab.interval_cache_and_ftp_auditor import (  # noqa: E402
    analyze_interval_cache_and_ftp,
    interval_cache_and_ftp_report_to_dict,
)
from fx3_firmware_lab.lut3d_cube_tetrahedral_and_sdi_hdmi_auditor import (  # noqa: E402
    analyze_lut3d_cube_tetrahedral_and_sdi_hdmi,
    lut3d_cube_tetrahedral_and_sdi_hdmi_report_to_dict,
)
from fx3_firmware_lab.metadata_gyro_catalyst_and_anamorphic_auditor import (  # noqa: E402
    analyze_metadata_gyro_catalyst_and_anamorphic,
    metadata_gyro_catalyst_and_anamorphic_report_to_dict,
)
from fx3_firmware_lab.playback_shotmark_and_ae_auditor import (  # noqa: E402
    analyze_playback_shotmark_and_ae,
    evaluate_media_format_and_delete_firewall,
    playback_shotmark_and_ae_report_to_dict,
)
from fx3_recovery import (  # noqa: E402
    run_fdt_bootargs_and_kernel_suite,
    run_gpt_rpmb_and_rescue_bundle_suite,
    run_ramdisk_overlay_and_emmc_health_suite,
    run_recovery_master_suite,
)
from fx3_recovery.recovery_master_suite_and_uart_decoder import (  # noqa: E402
    PILLAR_IDS as RECOVERY_7_PILLAR_IDS,
)
from fx3_safety.pl_cantilever_dummybatt_and_32gate_guard import (  # noqa: E402
    evaluate_32gate_preflight,
)
from fx3_vm_coemulation_suite import (  # noqa: E402
    CoEmulationConfig,
    run_fx3_vm_coemulation_suite,
)

from .hardware_readiness_packet import _is_forced_clean_room  # noqa: E402
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
)
from .stage_b_capstone_22gate_verifier import (  # noqa: E402
    CAPSTONE_22GATE_SCHEMA_VERSION,
    DOMAIN_IDS as CAPSTONE_DOMAIN_IDS,
    STAGE_B_CAPSTONE_22GATE_SCHEMA,
    _build_clean_room_stage_b_manifest_items,
    _evaluate_domain_4,
    _worker_domain_2,
    _worker_domain_4_group,
)
from .stage_b_milestone90_master_gate import (  # noqa: E402
    FIRMWARE_LAB_16_AUDITOR_KEYS,
    MILESTONE90_SCHEMA_VERSION,
    PILLAR_IDS as MILESTONE90_PILLAR_IDS,
    STAGE_B_MILESTONE90_SCHEMA,
    VM_COEMULATION_13_STAGE_KEYS,
)
from .stage_b_post_trial_auditor import _read_file_o_rdonly  # noqa: E402
from .stage_b_ram_overlay_packager import STAGE_B_BK_LANG_SPECS  # noqa: E402
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402
from .stage_b_release_dossier_v3 import (  # noqa: E402
    DOSSIER_V3_SCHEMA_VERSION,
    PILLAR_IDS as DOSSIER_V3_PILLAR_IDS,
    ROUND14_4LANG_PAIRS,
    STAGE_B_RELEASE_DOSSIER_V3_SCHEMA,
    StageBReleaseDossierV3FaultInjection,
    _evaluate_pillar_e,
    _evaluate_pillar_f,
    _worker_pillar_b,
    _worker_pillar_f,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

STAGE_B_MILESTONE110_SCHEMA: str = "stage_b_milestone110_master_gate_v1"
MILESTONE110_SCHEMA_VERSION: str = STAGE_B_MILESTONE110_SCHEMA
SCHEMA_VERSION: str = STAGE_B_MILESTONE110_SCHEMA
PHASE_110_VERSION: str = "110.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P8_CP_MUTATION_FORBIDDEN: bool = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN: bool = True
CP_MUTATION_BYTES: int = 0
WBI_MUTATION_BYTES: int = 0
CALIBRATION_MUTATION_BYTES: int = 0
USB_OR_CAMERA_OPERATIONS: int = 0
OTP_FUSE_TOUCHES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0

STATUS_MILESTONE_READY: str = "MILESTONE_110_SIMULATION_READY"
STATUS_FAIL_CLOSED: str = "FAIL_CLOSED"

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_32GATE_MASTER_PREFLIGHT"),
    ("P2", "TEN_PILLAR_RECOVERY_MASTER_SUITE"),
    ("P3", "TWENTY_PLUS_FIRMWARE_LAB_AUDITORS"),
    ("P4", "EIGHTEEN_PLUS_STAGE_VM_COEMULATION"),
    ("P5", "REAL_KERNEL_R14_R17_R19_COMPLETE_UI_CLOSURES"),
    ("P6", "POST_TRIAL_H0_VS_H2_IMMUTABILITY_AND_HARDWARE_LOCK_PROOF"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)

RECOVERY_10_PILLAR_IDS: Tuple[str, ...] = (
    *RECOVERY_7_PILLAR_IDS,
    "gpt_rpmb_and_rescue_bundle_verifier",
    "ramdisk_overlay_and_emmc_health_verifier",
    "fdt_bootargs_and_kernel_verifier",
)

FIRMWARE_LAB_20_AUDITOR_KEYS: Tuple[str, ...] = (
    *FIRMWARE_LAB_16_AUDITOR_KEYS,
    "metadata_gyro_catalyst_and_anamorphic_audit",
    "interval_cache_and_ftp_audit",
    "lut3d_cube_tetrahedral_and_sdi_hdmi_audit",
    "c2pa_lens_shading_and_mc_fleet_audit",
)

VM_COEMULATION_18_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_13_STAGE_KEYS,
    "stage14_phase91_gyroflow_rtmd_anamorphic",
    "stage15_phase96_interval_cache_ftp_fan",
    "stage16_phase99_lut3d_subzero_sdi",
    "stage17_phase103_emi_exfat_endurance",
    "stage18_phase107_c2pa_shading_mcfleet_ovp",
)

# Round 17: Complete 10/10 Status Check Ring (0x2f..0x37, 0x39; C(10,2)=45 pairs)
ROUND17_SUMMARY_RELPATH: str = (
    "reports/2026-11-14-round17-fx6-on-fx3-status-fullsweep-audio/summary.json"
)
ROUND17_MULTITAB_SIDS: Tuple[str, ...] = (
    "0x2f",
    "0x30",
    "0x31",
    "0x32",
    "0x33",
    "0x34",
    "0x35",
    "0x36",
    "0x37",
    "0x39",
)
ROUND17_TAB_PRESENTERS: Tuple[str, ...] = (
    "34procam_touch_status_main_presenter",
    "36procam_touch_status_camera_presenter",
    "35procam_touch_status_audio_presenter",
    "37procam_touch_status_project_presenter",
    "40procam_touch_status_monitoring_presenter",
    "47procam_touch_status_assignable_button_presenter",
    "37procam_touch_status_battery_presenter",
    "35procam_touch_status_media_presenter",
    "37procam_touch_status_network_presenter",
    "43procam_touch_status_file_transfer_presenter",
)
ROUND17_RUN_SPECS: Tuple[Tuple[str, str, str], ...] = (
    ("r17a_status_tab6_schinese", "0x34", "schinese"),
    ("r17b_status_tab7_schinese", "0x35", "schinese"),
    ("r17c_status_tab8_schinese", "0x36", "schinese"),
    ("r17d_menu_3layer_audio_schinese", "0x11", "schinese"),
    ("r17e_status_tab9_network_schinese", "0x37", "schinese"),
    ("r17f_status_tab10_filetransfer_schinese", "0x39", "schinese"),
    ("r17g_status_wraparound_tab1_schinese", "0x2f", "schinese"),
)
ROUND17_RUN_IDS: Tuple[str, ...] = tuple(rid for rid, _, _ in ROUND17_RUN_SPECS)

# Round 19: Complete 11/11 Full-Menu L1 Rail (C(11,2)=55 pairs + 11-down wrap + TChinese WF-12)
ROUND19_SUMMARY_RELPATH: str = (
    "reports/2026-11-14-round19-fx6-on-fx3-menu-11cat-fullsweep/summary.json"
)
ROUND19_11CAT_SPECS: Tuple[Tuple[int, str, int], ...] = (
    (0, "User", 8),
    (1, "Shooting", 2),
    (2, "Project", 9),
    (3, "Paint/Look", 10),
    (4, "TC/Media", 12),
    (5, "Monitoring", 13),
    (6, "Audio", 14),
    (7, "Thumbnail", 15),
    (8, "Technical", 16),
    (9, "Network", 6),
    (10, "Maintenance", 17),
)
ROUND19_11CAT_NAMES: Tuple[str, ...] = tuple(name for _, name, _ in ROUND19_11CAT_SPECS)
ROUND19_11CAT_PAIR_KEYS: Tuple[str, ...] = tuple(
    f"{ROUND19_11CAT_NAMES[i].lower().replace('/', '_')}_vs_{ROUND19_11CAT_NAMES[j].lower().replace('/', '_')}"
    for i in range(len(ROUND19_11CAT_NAMES))
    for j in range(i + 1, len(ROUND19_11CAT_NAMES))
)
ROUND19_RUN_SPECS: Tuple[Tuple[str, str, str], ...] = (
    ("r19a_menu_3layer_user_schinese", "0x11", "schinese"),
    ("r19b_menu_3layer_thumbnail_schinese", "0x0f", "schinese"),
    ("r19c_menu_3layer_technical_schinese", "0x11", "schinese"),
    ("r19d_menu_3layer_wraparound_user_schinese", "0x11", "schinese"),
    ("r19e_menu_3layer_network_tchinese", "0x11", "tchinese"),
)
ROUND19_RUN_IDS: Tuple[str, ...] = tuple(rid for rid, _, _ in ROUND19_RUN_SPECS)

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Milestone110FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 faults (32-gate preflight, G21..G32)
    p1_pl_cantilever_kwargs: Optional[Mapping[str, Any]] = None
    p1_dummy_battery_kwargs: Optional[Mapping[str, Any]] = None
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

    # P2 faults (10-pillar recovery: OTP/RPMB, GF(256), init2, UART, GPT/RPMB, cpio/EXT_CSD, FDT/kernel)
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

    # P3 faults (>= 20 fx3_firmware_lab auditors, incl. #15..#20)
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

    # P4 faults (>= 18-stage VM co-emulation, Stages 10..18)
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

    # P5 faults (Round 14 18/18 + Round 17 10/10 Status C(10,2)=45 + Round 19 11/11 Menu C(11,2)=55)
    p5_round14_nop_count: int = 0
    p5_round14_zero_pair: bool = False
    p5_round17_nop_count: int = 0
    p5_round17_crashes: int = 0
    p5_round17_zero_tab_pair: Optional[str] = None
    p5_round17_zero_wraparound: bool = False
    p5_round17_manifest_count_override: Optional[int] = None
    p5_round19_nop_count: int = 0
    p5_round19_crashes: int = 0
    p5_round19_zero_cat_pair: Optional[str] = None
    p5_round19_zero_wraparound: bool = False
    p5_round19_zero_tchinese_delta: bool = False
    p5_round19_wf12_immune_override: Optional[int] = None
    p5_round19_manifest_count_override: Optional[int] = None

    # P6 faults (Dossier v3 + Capstone 22 + Milestone 90 + H0-vs-H2 16-surface drift / tamper)
    p6_drift_surface: Optional[str] = None
    p6_tamper_negative_control: bool = False


@dataclass(frozen=True)
class Milestone110PillarResult:
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
class StageBMilestone110MasterGateReport:
    schema_version: str
    phase_version: str
    verification_mode: str
    all_pillars_milestone_ready: bool
    status: str
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    hardware_live_attachment_authorized: bool
    hardware_live_attachment_requirements: Tuple[str, ...]
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
    pillars: Tuple[Milestone110PillarResult, ...]
    gate32_offline_verified: int
    gate32_simulated_verified: int
    recovery_pillar_count: int
    recovery_pillars_passed: int
    firmware_lab_auditor_count: int
    firmware_lab_auditors_passed: int
    vm_coemulation_stage_count: int
    vm_coemulation_stages_passed: int
    round14_positive_pairs: int
    round17_tabs_verified: int
    round17_pairwise_deltas_verified: int
    round17_runs_verified: int
    round19_categories_verified: int
    round19_pairwise_deltas_verified: int
    round19_runs_verified: int
    real_kernel_nop_count: int
    real_kernel_crashes: int
    h0_surface_count: int
    drifted_surface_count: int
    c2pa_rq_lic_intact: bool
    spacc_cnflasha_untouched: bool
    errors: Tuple[str, ...]
    milestone110_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class StageBMilestone110VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone110_sha256: str
    observed_milestone110_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic Digest & O_RDONLY Round 17 / Round 19 Loaders
# ---------------------------------------------------------------------------


def compute_milestone110_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `StageBMilestone110MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone110_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def _clean_room_languages_block() -> Dict[str, Any]:
    return {
        code: {
            "language_enum": f"0x{spec.enum_id:04x}",
            "bk4_language_id": spec.bk_id_hex,
            "bk4_language_val": f"0x{spec.bk_lang_value:02x}",
            "uxc_banks": {
                "font": spec.font_bank,
                "ns1_string": spec.ns1_bank,
                "ns2_string": spec.ns2_bank,
            },
        }
        for code, spec in STAGE_B_BK_LANG_SPECS.items()
    }


def _clean_room_faithful_block() -> Dict[str, int]:
    return {
        "FX6_NATIVE_FAITHFUL": 1,
        "subst_color": 0,
        "subst_image": 0,
        "forced_render": 0,
        "skipped_node": 0,
        "lock_bypass": 0,
    }


def _load_round17_summary(
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], str]:
    """Load Round 17 summary strictly via `os.O_RDONLY` when present, else clean-room synthetic."""
    summary_path = repo_root / ROUND17_SUMMARY_RELPATH
    if summary_path.is_file() and not summary_path.is_symlink():
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if isinstance(obj, dict):
            return obj, "REPO_SUMMARY_O_RDONLY"
    if not use_clean_room:
        raise FileNotFoundError(f"Missing Round 17 summary report: {summary_path}")

    manifest_items = _build_clean_room_stage_b_manifest_items()
    faithful = _clean_room_faithful_block()
    runs_block: Dict[str, Any] = {}
    for run_id, target_sid, lang_name in ROUND17_RUN_SPECS:
        runs_block[run_id] = {
            "run_id": run_id.replace("_", "-"),
            "round": 17,
            "lang": lang_name,
            "target_sid": target_sid,
            "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
            "nop_count": 0,
            "crashes": 0,
            "faithful_invariants": dict(faithful),
            "stage_b": {
                "stage": "B",
                "r17_enabled": True,
                "lang": lang_name,
                "manifest_count": 13,
                "manifest_items": list(manifest_items),
            },
        }

    pairs_block: Dict[str, Any] = {}
    for i in range(10):
        for j in range(i + 1, 10):
            pk = f"tab{i + 1}_vs_tab{j + 1}"
            pairs_block[pk] = {
                "sid_a": ROUND17_MULTITAB_SIDS[i],
                "sid_b": ROUND17_MULTITAB_SIDS[j],
                "diff_pixels": 40000 + (i * 10 + j) * 517,
                "strictly_positive": True,
            }

    wrap_diffs: Dict[str, int] = {"wrap_vs_tab1": 480}
    for idx in range(2, 11):
        wrap_diffs[f"wrap_vs_tab{idx}"] = 55000 + idx * 3100

    synthetic = {
        "schema": "fx6-on-fx3-round17-status-fullsweep-audio-v1",
        "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
        "languages": _clean_room_languages_block(),
        "status_check_multitab_contract": {
            "entry_infra_key": "0x7052",
            "step_next_infra_key": "0x0030",
            "step_prev_infra_key": "0x0003",
            "index_jump_infra_key": "0x0015",
            "carousel_tab_count": 10,
            "wrap_around_step_count": 10,
            "wrap_around_verified": True,
            "tabs_verified": [
                {
                    "tab_index": idx + 1,
                    "sid": sid,
                    "presenter": ROUND17_TAB_PRESENTERS[idx],
                }
                for idx, sid in enumerate(ROUND17_MULTITAB_SIDS)
            ],
        },
        "runs": runs_block,
        "r17_status_fullsweep_and_audio_audit": {
            "status_check_10tab_pairwise_schinese": {
                "tab_count": 10,
                "pair_count": 45,
                "all_45_tab_pairs_strictly_positive": True,
                "min_diff_pixels": 40517,
                "max_diff_pixels": 125000,
                "pairs": pairs_block,
            },
            "status_check_wraparound_proof": {
                "run_key": "r17g_status_wraparound_tab1_schinese",
                "step_count_down": 10,
                "target_sid": "0x2f",
                "diff_vs_r13a_tab1_pixels": 480,
                "wrap_diffs_vs_tabs1_to_10": wrap_diffs,
                "all_non_tab1_diffs_strictly_positive": True,
            },
            "menu_3layer_4cat_schinese_pairwise": {
                "pair_count": 6,
                "all_6_category_pairs_strictly_positive": True,
            },
            "wf12_00342260_network_tab_immunity": {
                "run_key": "r17e_status_tab9_network_schinese",
                "target_sid": "0x37",
                "p12_wlan": 1,
                "wf12_00342260_immune": 1,
                "airplane_bk4_hits": 0,
                "nop_count": 0,
                "crashes": 0,
            },
        },
    }
    return synthetic, "CLEAN_ROOM_SYNTHETIC"


def _load_round19_summary(
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], str]:
    """Load Round 19 summary strictly via `os.O_RDONLY` when present, else clean-room synthetic."""
    summary_path = repo_root / ROUND19_SUMMARY_RELPATH
    if summary_path.is_file() and not summary_path.is_symlink():
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if isinstance(obj, dict):
            return obj, "REPO_SUMMARY_O_RDONLY"
    if not use_clean_room:
        raise FileNotFoundError(f"Missing Round 19 summary report: {summary_path}")

    manifest_items = _build_clean_room_stage_b_manifest_items()
    faithful = _clean_room_faithful_block()
    runs_block: Dict[str, Any] = {}
    for run_id, target_sid, lang_name in ROUND19_RUN_SPECS:
        runs_block[run_id] = {
            "run_id": run_id.replace("_", "-"),
            "round": 19,
            "lang": lang_name,
            "target_sid": target_sid,
            "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
            "nop_count": 0,
            "crashes": 0,
            "faithful_invariants": dict(faithful),
            "stage_b": {
                "stage": "B",
                "r19_enabled": True,
                "lang": lang_name,
                "manifest_count": 13,
                "manifest_items": list(manifest_items),
            },
        }

    pairs_block: Dict[str, Any] = {}
    idx_pair = 0
    for pk in ROUND19_11CAT_PAIR_KEYS:
        pairs_block[pk] = {
            "diff_pixels": 1552 + idx_pair * 413,
            "strictly_positive": True,
        }
        idx_pair += 1

    wrap_diffs: Dict[str, int] = {"wrap_vs_user": 480}
    for idx, cname in enumerate(ROUND19_11CAT_NAMES[1:], start=1):
        norm = cname.lower().replace("/", "_")
        wrap_diffs[f"wrap_vs_{norm}"] = 2000 + idx * 4500

    synthetic = {
        "schema": "fx6-on-fx3-round19-menu-11cat-fullsweep-v1",
        "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
        "languages": _clean_room_languages_block(),
        "full_menu_l1_rail_contract": {
            "table_offset": "appFw.so+0x2924180",
            "entry_stride_bytes": 48,
            "rail_categories_visible_in_shooting_mode": [
                {"down_steps": ds, "category": cat, "cat_id": cid}
                for ds, cat, cid in ROUND19_11CAT_SPECS
            ],
            "skipped_categories_in_shooting_mode": [
                {"category": "Pan-Tilt", "cat_id": 11},
                {"category": "Service", "cat_id": 18},
            ],
        },
        "runs": runs_block,
        "r19_menu_11cat_fullsweep_audit": {
            "menu_11cat_schinese_pairwise": {
                "category_count": 11,
                "pair_count": 55,
                "categories": list(ROUND19_11CAT_NAMES),
                "all_55_category_pairs_strictly_positive": True,
                "min_diff_pixels": 1552,
                "max_diff_pixels": 165000,
                "pairs": pairs_block,
            },
            "menu_11down_wraparound_proof": {
                "run_key": "r19d_menu_3layer_wraparound_user_schinese",
                "step_count_down": 11,
                "cat_id": 8,
                "target_sid": "0x11",
                "diff_vs_r19a_user_pixels": 480,
                "wrap_diffs_vs_all_11_categories": wrap_diffs,
                "all_non_user_diffs_strictly_positive": True,
            },
            "network_tchinese_vs_schinese_delta": {
                "run_tchinese": "r19e_menu_3layer_network_tchinese",
                "run_schinese": "r18c_menu_3layer_network_schinese",
                "diff_pixels": 19652,
                "strictly_positive": True,
            },
            "wf12_00342260_network_tchinese_immunity": {
                "run_key": "r19e_menu_3layer_network_tchinese",
                "lang": "tchinese",
                "target_sid": "0x11",
                "menu_category": "Network",
                "p12_wlan": 1,
                "wf12_00342260_immune": 1,
                "airplane_bk4_hits": 0,
                "nop_count": 0,
                "crashes": 0,
            },
        },
    }
    return synthetic, "CLEAN_ROOM_SYNTHETIC"


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 2.5s Runtime)
# ---------------------------------------------------------------------------


def _worker_pillar_1(args: Tuple[str, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, fault_dict = args
    repo_root = Path(repo_root_str)
    req_persist = bool(fault_dict.get("p1_request_persistent_writes", False))

    kwargs: Dict[str, Any] = {
        "pl_cantilever_kwargs": fault_dict.get("p1_pl_cantilever_kwargs"),
        "dummy_battery_kwargs": fault_dict.get("p1_dummy_battery_kwargs"),
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

    rep_off = evaluate_32gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=False,
        **kwargs,
    )
    rep_sim = evaluate_32gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=True,
        **kwargs,
    )

    m30 = rep_sim.master_30_report
    m28 = m30.get("master_28_report", {})
    m26 = m28.get("master_26_report", {})
    m24 = m26.get("master_24_report", {})

    g25 = m26.get("g25_result", {})
    g26 = m26.get("g26_result", {})
    g27 = m28.get("g27_result", {})
    g28 = m28.get("g28_result", {})
    g29 = m30.get("g29_result", {})
    g30 = m30.get("g30_result", {})

    g31 = rep_sim.g31_result
    g32 = rep_sim.g32_result
    pl_guard = g31.get("pl_cantilever_guard", {})
    batt_fw = g32.get("dummy_battery_firewall", {})

    return {
        "schema": rep_sim.schema,
        "verification_mode": rep_sim.verification_mode,
        "total_gates": int(rep_sim.summary.get("total_gates", len(rep_sim.gates))),
        "offline_verified_gates": int(rep_off.summary.get("verified_gates", 0)),
        "offline_29_gates_verified": bool(rep_off.offline_29_gates_verified),
        "offline_all_32_gates_verified": bool(rep_off.all_32_gates_verified),
        "offline_ready_for_hw": bool(rep_off.overall_ready_for_hardware_attach),
        "sim_verified_gates": int(rep_sim.summary.get("verified_gates", 0)),
        "sim_all_32_gates_verified": bool(rep_sim.all_32_gates_verified),
        "sim_dry_run_rehearsal_only": bool(rep_sim.dry_run_rehearsal_only),
        "sim_ready_for_hw": bool(rep_sim.overall_ready_for_hardware_attach),
        "g13_to_g32_all_passed": bool(rep_sim.g13_to_g32_all_passed),
        "g31_to_g32_all_passed": bool(rep_sim.g31_to_g32_all_passed),
        "m24_all_passed": bool(m24.get("g13_to_g24_all_passed", False)),
        "g25_passed": bool(g25.get("valid", False)),
        "g26_passed": bool(g26.get("valid", False)),
        "g27_passed": bool(g27.get("valid", False)),
        "g28_passed": bool(g28.get("valid", False)),
        "g29_passed": bool(g29.get("valid", False)),
        "g30_passed": bool(g30.get("valid", False)),
        "g31_passed": bool(g31.get("valid", False)),
        "g31_status": str(g31.get("status", "")),
        "g31_cantilever_flange_safe": bool(pl_guard.get("cantilever_flange_safe", False)),
        "g31_pl_adapter_backfocus_safe": bool(pl_guard.get("pl_adapter_backfocus_safe", False)),
        "g31_mattebox_barrel_safe": bool(pl_guard.get("mattebox_barrel_safe", False)),
        "g32_passed": bool(g32.get("valid", False)),
        "g32_status": str(g32.get("status", "")),
        "g32_dummy_battery_voltage_safe": bool(batt_fw.get("dummy_battery_voltage_safe", False)),
        "g32_dtap_polarity_safe": bool(batt_fw.get("dtap_polarity_safe", False)),
        "g32_infolithium_auth_safe": bool(batt_fw.get("infolithium_auth_safe", False)),
        "persistent_emmc_writes_authorized": bool(rep_sim.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep_sim.persistent_write_release),
        "sim_errors": list(rep_sim.errors),
        "g31_errors": list(g31.get("errors", [])),
        "g32_errors": list(g32.get("errors", [])),
    }


def _worker_recovery_master(use_clean_room: bool) -> Dict[str, Any]:
    rep = run_recovery_master_suite(force_clean_room=use_clean_room)
    uart = rep.uart_decoder_suite
    return {
        "schema": rep.schema,
        "verification_mode": rep.verification_mode,
        "all_passed": bool(rep.all_passed),
        "status": str(rep.status),
        "pillar_count": int(rep.pillar_count),
        "pillars_passed": int(rep.pillars_passed),
        "pillar_statuses": {p.pillar_id: bool(p.passed) for p in rep.pillars},
        "uart_scenarios_total": int(uart.scenarios_total),
        "uart_scenarios_passed": int(uart.scenarios_passed),
        "uart_all_passed": bool(uart.passed),
        "passive_tx_bytes_emitted": int(rep.passive_tx_bytes_emitted),
        "physical_device_writes": int(rep.physical_device_writes),
        "persistent_emmc_writes_authorized": bool(rep.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep.persistent_write_release),
        "allow_boot_partition_targeting": bool(rep.allow_boot_partition_targeting),
        "allow_destructive_fastboot": bool(rep.allow_destructive_fastboot),
        "recovery_master_sha256": str(rep.recovery_master_sha256),
        "errors": list(rep.errors),
    }


def _worker_recovery_p8_p9_p10(use_clean_room: bool) -> Dict[str, Any]:
    p8 = run_gpt_rpmb_and_rescue_bundle_suite(force_clean_room=use_clean_room)
    p9 = run_ramdisk_overlay_and_emmc_health_suite(force_clean_room=use_clean_room)
    p10 = run_fdt_bootargs_and_kernel_suite(force_clean_room=use_clean_room)
    return {
        "p8_gpt_rpmb": {
            "schema": p8.schema,
            "all_passed": bool(p8.all_passed),
            "status": str(p8.status),
            "gpt_heal_backup_ok": bool(p8.gpt_heal_backup_from_primary.passed),
            "gpt_heal_primary_ok": bool(p8.gpt_heal_primary_from_backup.passed),
            "rpmb_authenticated_write_passed": bool(p8.rpmb_authenticated_write_passed),
            "sd_rescue_ok": bool(p8.sd_rescue_valid_report.passed),
            "stage_b_zero_rpmb_ok": bool(p8.stage_b_zero_rpmb_proof.passed),
            "otp_fuse_touches": int(p8.otp_fuse_touches),
            "rpmb_writes_emitted": int(p8.rpmb_writes_emitted),
            "passive_tx_bytes_emitted": int(p8.passive_tx_bytes_emitted),
            "physical_device_writes": int(p8.physical_device_writes),
            "persistent_emmc_writes_authorized": bool(p8.persistent_emmc_writes_authorized),
            "suite_sha256": str(p8.suite_sha256),
            "errors": list(p8.errors),
        },
        "p9_ramdisk_emmc_health": {
            "schema": p9.schema,
            "all_passed": bool(p9.all_passed),
            "status": str(p9.status),
            "stage_b_containment_ready": bool(p9.stage_b_containment_ready),
            "cpio_reject_traversal_passed": bool(p9.cpio_reject_traversal_passed),
            "cpio_reject_setuid_passed": bool(p9.cpio_reject_setuid_passed),
            "emmc_reject_pre_eol_urgent_passed": bool(p9.emmc_reject_pre_eol_urgent_passed),
            "emmc_reject_lifetime_gt80_passed": bool(p9.emmc_reject_lifetime_gt80_passed),
            "mount_reject_rw_mmcblk_passed": bool(p9.mount_reject_rw_mmcblk_passed),
            "otp_fuse_touches": int(p9.otp_fuse_touches),
            "passive_tx_bytes_emitted": int(p9.passive_tx_bytes_emitted),
            "physical_device_writes": int(p9.physical_device_writes),
            "persistent_emmc_writes_authorized": bool(p9.persistent_emmc_writes_authorized),
            "suite_sha256": str(p9.suite_sha256),
            "errors": list(p9.errors),
        },
        "p10_fdt_bootargs_kernel": {
            "schema": p10.schema,
            "all_passed": bool(p10.all_passed),
            "status": str(p10.status),
            "stage_b_boot_gate_ready": bool(p10.stage_b_boot_gate_ready),
            "bootargs_reject_rw_emmc_passed": bool(p10.bootargs_reject_rw_emmc_passed),
            "bootargs_reject_nowatchdog_passed": bool(p10.bootargs_reject_nowatchdog_passed),
            "kernel_reject_fx6_transplant_passed": bool(p10.kernel_reject_fx6_transplant_passed),
            "otp_fuse_touches": int(p10.otp_fuse_touches),
            "passive_tx_bytes_emitted": int(p10.passive_tx_bytes_emitted),
            "physical_device_writes": int(p10.physical_device_writes),
            "persistent_emmc_writes_authorized": bool(p10.persistent_emmc_writes_authorized),
            "suite_sha256": str(p10.suite_sha256),
            "errors": list(p10.errors),
        },
    }


def _worker_pillar_3_group(args: Tuple[str, bool]) -> Dict[str, Dict[str, Any]]:
    group, clean_room = args
    if group == "falsecolor":
        return {
            "falsecolor_lpcm_tc_ub_audit": falsecolor_lpcm_tc_ub_report_to_dict(
                analyze_falsecolor_lpcm_tc_ub(clean_room=clean_room)
            )
        }
    if group == "playback":
        return {
            "playback_shotmark_and_ae_audit": playback_shotmark_and_ae_report_to_dict(
                analyze_playback_shotmark_and_ae(clean_room=clean_room)
            )
        }
    if group == "gyroflow":
        return {
            "metadata_gyro_catalyst_and_anamorphic_audit": metadata_gyro_catalyst_and_anamorphic_report_to_dict(
                analyze_metadata_gyro_catalyst_and_anamorphic(clean_room=clean_room)
            )
        }
    if group == "interval_ftp":
        return {
            "interval_cache_and_ftp_audit": interval_cache_and_ftp_report_to_dict(
                analyze_interval_cache_and_ftp(clean_room=clean_room)
            )
        }
    if group == "lut3d_sdi":
        return {
            "lut3d_cube_tetrahedral_and_sdi_hdmi_audit": lut3d_cube_tetrahedral_and_sdi_hdmi_report_to_dict(
                analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(clean_room=clean_room)
            )
        }
    if group == "c2pa_mc":
        return {
            "c2pa_lens_shading_and_mc_fleet_audit": c2pa_lens_shading_and_mc_fleet_report_to_dict(
                analyze_c2pa_lens_shading_and_mc_fleet(clean_room=clean_room)
            )
        }
    return _worker_domain_4_group((group, clean_room))


def _worker_pillar_4(use_clean_room: bool) -> Dict[str, Any]:
    return run_fx3_vm_coemulation_suite(CoEmulationConfig(force_clean_room=use_clean_room))


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1 .. P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(raw_1: Mapping[str, Any]) -> Milestone110PillarResult:
    errors: List[str] = []
    total_gates = int(raw_1.get("total_gates", 0))
    if total_gates < 32:
        errors.append(f"p1: total_gates expected >= 32, got {total_gates}")
    if not raw_1["offline_29_gates_verified"] or raw_1["offline_verified_gates"] < 29:
        errors.append(
            f"p1: offline hardware-truth gates expected >= 29/{total_gates}, got {raw_1['offline_verified_gates']}/{total_gates}"
        )
    if raw_1["offline_all_32_gates_verified"] or raw_1["offline_ready_for_hw"]:
        errors.append("p1: offline mode must remain blocked for live hardware attach")
    if not raw_1["sim_all_32_gates_verified"] or raw_1["sim_verified_gates"] < 32:
        errors.append(
            f"p1: simulated rehearsal gates expected >= 32/{total_gates}, got {raw_1['sim_verified_gates']}/{total_gates}"
        )
    if not raw_1["sim_dry_run_rehearsal_only"] or raw_1["sim_ready_for_hw"]:
        errors.append("p1: simulated 32-gate rehearsal must keep overall_ready_for_hardware_attach=False")
    if not raw_1["g13_to_g32_all_passed"] or not raw_1["g31_to_g32_all_passed"]:
        errors.append("p1: G13..G32 or G31..G32 safety guard gate blocked")
    if not raw_1["m24_all_passed"]:
        errors.append("p1: G13..G24 foundation gate suite failed")
    for gk in ("g25", "g26", "g27", "g28", "g29", "g30"):
        if not raw_1.get(f"{gk}_passed", False):
            errors.append(f"p1: {gk.upper()} safety guard failed")
    if (
        not raw_1["g31_passed"]
        or not raw_1["g31_cantilever_flange_safe"]
        or not raw_1["g31_pl_adapter_backfocus_safe"]
        or not raw_1["g31_mattebox_barrel_safe"]
    ):
        errors.append(f"p1: G31 PL-to-E cantilever & 15mm LWS guard failed ({raw_1['g31_status']})")
    if (
        not raw_1["g32_passed"]
        or not raw_1["g32_dummy_battery_voltage_safe"]
        or not raw_1["g32_dtap_polarity_safe"]
        or not raw_1["g32_infolithium_auth_safe"]
    ):
        errors.append(f"p1: G32 Dummy-Battery >8.4V OVP & InfoLITHIUM firewall failed ({raw_1['g32_status']})")
    if raw_1["persistent_emmc_writes_authorized"] or raw_1["persistent_write_release"]:
        errors.append("p1: hard-locked persistent_emmc_writes_authorized / persistent_write_release breached")
    for err in raw_1["sim_errors"]:
        errors.append(f"p1_32gate: {err}")
    for err in raw_1["g31_errors"]:
        errors.append(f"p1_g31: {err}")
    for err in raw_1["g32_errors"]:
        errors.append(f"p1_g32: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_1["schema"],
        "verification_mode": raw_1["verification_mode"],
        "total_gates": total_gates,
        "offline_verified_gates": raw_1["offline_verified_gates"],
        "offline_ready_for_hardware_attach": raw_1["offline_ready_for_hw"],
        "simulated_verified_gates": raw_1["sim_verified_gates"],
        "simulated_ready_for_hardware_attach": raw_1["sim_ready_for_hw"],
        "g25_to_g30_passed": all(bool(raw_1.get(f"g{n}_passed", False)) for n in range(25, 31)),
        "g31_passed": raw_1["g31_passed"],
        "g31_status": raw_1["g31_status"],
        "g31_cantilever_flange_safe": raw_1["g31_cantilever_flange_safe"],
        "g31_pl_adapter_backfocus_safe": raw_1["g31_pl_adapter_backfocus_safe"],
        "g31_mattebox_barrel_safe": raw_1["g31_mattebox_barrel_safe"],
        "g32_passed": raw_1["g32_passed"],
        "g32_status": raw_1["g32_status"],
        "g32_dummy_battery_voltage_safe": raw_1["g32_dummy_battery_voltage_safe"],
        "g32_dtap_polarity_safe": raw_1["g32_dtap_polarity_safe"],
        "g32_infolithium_auth_safe": raw_1["g32_infolithium_auth_safe"],
        "persistent_emmc_writes_authorized": raw_1["persistent_emmc_writes_authorized"],
        "persistent_write_release": raw_1["persistent_write_release"],
    }
    return Milestone110PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_32GATE_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"32-Gate offline={raw_1['offline_verified_gates']}/{total_gates} "
            f"sim={raw_1['sim_verified_gates']}/{total_gates}, G31(PL-Cantilever)={raw_1['g31_passed']}, "
            f"G32(DummyBatt-OVP)={raw_1['g32_passed']} {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    raw_master: Mapping[str, Any],
    raw_p8_p10: Mapping[str, Any],
    raw_antirollback: Mapping[str, Any],
    raw_tier0_init2: Mapping[str, Any],
    faults: Milestone110FaultInjection,
) -> Tuple[Milestone110PillarResult, Dict[str, Any]]:
    errors: List[str] = []

    # Core 7-pillar recovery master + passive UART S0..S6
    if not raw_master.get("all_passed"):
        errors.append("p2: recovery master 7-pillar suite all_passed is False")
    if int(raw_master.get("pillars_passed", 0)) < 7:
        errors.append(
            f"p2: recovery master pillars_passed={raw_master.get('pillars_passed')} < 7"
        )
    if int(raw_master.get("uart_scenarios_passed", 0)) < 10 or not raw_master.get("uart_all_passed"):
        errors.append("p2: passive 1.8V RX-only UART S0..S6 decoder failed 10/10 scenarios")

    # Domain 2 OTP/RPMB/EXT_CSD + Pillar B GF(256)/init2 checks
    for err in raw_antirollback.get("errors", []):
        errors.append(f"p2_otp: {err}")
    for err in raw_tier0_init2.get("tier0_errors", []):
        errors.append(f"p2_tier0: {err}")
    for err in raw_tier0_init2.get("init2_errors", []):
        errors.append(f"p2_init2: {err}")
    if faults.p2_inject_gf256_quorum_loss:
        errors.append("p2_tier0: GF(256) 3-loss quorum failure exceeded P+Q parity bound (fail-closed)")
    if faults.p2_inject_cross_body_cnflasha_transplant or raw_tier0_init2.get(
        "cross_body_transplant_rejected_by_guard"
    ):
        errors.append("p2_tier0: cross-body cnflasha/C2PA transplant blocked")
    if faults.p2_inject_init2_escape_fault:
        errors.append("p2_init2: init2 SD sentinel escape or FAT12/FAT16 check failed (fail-closed)")

    # Pillars 8, 9, 10 (Phase 94, 101, 106)
    p8 = raw_p8_p10.get("p8_gpt_rpmb", {})
    p9 = raw_p8_p10.get("p9_ramdisk_emmc_health", {})
    p10 = raw_p8_p10.get("p10_fdt_bootargs_kernel", {})

    if not p8.get("all_passed") or not p8.get("stage_b_zero_rpmb_ok") or faults.p2_inject_gpt_both_corrupted:
        errors.append("p2_p8: GPT CRC32 healer or SD rescue bundle check failed")
    if not p8.get("rpmb_authenticated_write_passed") or faults.p2_inject_rpmb_replay_fault:
        errors.append("p2_p8: RPMB authenticated frame / replay guard failed")

    if not p9.get("all_passed") or not p9.get("stage_b_containment_ready") or faults.p2_inject_cpio_or_emmc_fault:
        errors.append("p2_p9: SVR4 newc cpio / EXT_CSD health / tmpfs isolation check failed")

    if not p10.get("all_passed") or not p10.get("stage_b_boot_gate_ready") or faults.p2_inject_fdt_or_kernel_fault:
        errors.append("p2_p10: FDT /chosen/bootargs or ARM64 4.9.337-scel+ kernel gate failed")

    # Zero-touch & zero-write invariants across all 10 pillars
    otp_touches = (
        int(raw_antirollback.get("otp_fuse_touches", 0))
        + int(p8.get("otp_fuse_touches", 0))
        + int(p9.get("otp_fuse_touches", 0))
        + int(p10.get("otp_fuse_touches", 0))
        + int(faults.p2_otp_fuse_touches_override)
    )
    rpmb_incs = (
        int(raw_antirollback.get("rpmb_counter_increments", 0))
        + int(p8.get("rpmb_writes_emitted", 0))
        + int(faults.p2_rpmb_increments_override)
    )
    passive_tx = (
        int(raw_master.get("passive_tx_bytes_emitted", 0))
        + int(p8.get("passive_tx_bytes_emitted", 0))
        + int(p9.get("passive_tx_bytes_emitted", 0))
        + int(p10.get("passive_tx_bytes_emitted", 0))
        + int(faults.p2_passive_tx_bytes_override)
    )
    phys_writes = (
        int(raw_master.get("physical_device_writes", 0))
        + int(p8.get("physical_device_writes", 0))
        + int(p9.get("physical_device_writes", 0))
        + int(p10.get("physical_device_writes", 0))
    )
    if otp_touches != 0:
        errors.append(f"p2: otp_fuse_touches={otp_touches} != 0")
    if rpmb_incs != 0:
        errors.append(f"p2: rpmb_counter_increments={rpmb_incs} != 0")
    if passive_tx != 0:
        errors.append(f"p2: passive_tx_bytes_emitted={passive_tx} != 0")
    if phys_writes != 0:
        errors.append(f"p2: physical_device_writes={phys_writes} != 0")

    if (
        raw_master.get("persistent_emmc_writes_authorized") is not False
        or raw_master.get("persistent_write_release") is not False
        or p8.get("persistent_emmc_writes_authorized") is not False
        or p9.get("persistent_emmc_writes_authorized") is not False
        or p10.get("persistent_emmc_writes_authorized") is not False
    ):
        errors.append("p2: hard-locked persistent_emmc_writes_authorized breached")

    pillar_statuses: Dict[str, bool] = {}
    for pid, ok in dict(raw_master.get("pillar_statuses", {})).items():
        pillar_statuses[str(pid)] = bool(ok)
    pillar_statuses["gpt_rpmb_and_rescue_bundle_verifier"] = bool(
        p8.get("all_passed") and not faults.p2_inject_gpt_both_corrupted and not faults.p2_inject_rpmb_replay_fault
    )
    pillar_statuses["ramdisk_overlay_and_emmc_health_verifier"] = bool(
        p9.get("all_passed") and not faults.p2_inject_cpio_or_emmc_fault
    )
    pillar_statuses["fdt_bootargs_and_kernel_verifier"] = bool(
        p10.get("all_passed") and not faults.p2_inject_fdt_or_kernel_fault
    )

    total_pillars = len(pillar_statuses)
    passed_pillars = sum(1 for v in pillar_statuses.values() if v)
    if total_pillars < 10 or passed_pillars < 10 or passed_pillars != total_pillars:
        errors.append(f"p2: recovery pillars expected >=10 and all passing, got {passed_pillars}/{total_pillars}")

    passed = len(errors) == 0
    evidence = {
        "verification_mode": raw_master.get("verification_mode"),
        "recovery_pillar_count": total_pillars,
        "recovery_pillars_passed": passed_pillars,
        "pillar_statuses": pillar_statuses,
        "uart_scenarios_passed": int(raw_master.get("uart_scenarios_passed", 0)),
        "uart_scenarios_total": int(raw_master.get("uart_scenarios_total", 0)),
        "otp_fuse_touches": otp_touches,
        "rpmb_counter_increments": rpmb_incs,
        "passive_tx_bytes_emitted": passive_tx,
        "physical_device_writes": phys_writes,
        "gold_pair_tier": raw_antirollback.get("gold_pair_tier"),
        "gf256_2_erasures_healed": bool(raw_tier0_init2.get("heal_2_erasures_passed", False)),
        "p8_gpt_rpmb_ok": pillar_statuses["gpt_rpmb_and_rescue_bundle_verifier"],
        "p9_ramdisk_emmc_health_ok": pillar_statuses["ramdisk_overlay_and_emmc_health_verifier"],
        "p10_fdt_bootargs_kernel_ok": pillar_statuses["fdt_bootargs_and_kernel_verifier"],
        "recovery_master_sha256": raw_master.get("recovery_master_sha256"),
        "p8_suite_sha256": p8.get("suite_sha256"),
        "p9_suite_sha256": p9.get("suite_sha256"),
        "p10_suite_sha256": p10.get("suite_sha256"),
    }
    pillar = Milestone110PillarResult(
        pillar_id="P2",
        pillar_name="TEN_PILLAR_RECOVERY_MASTER_SUITE",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Recovery {passed_pillars}/{total_pillars} pillars (Ph47..106), "
            f"UART S0..S6 {raw_master.get('uart_scenarios_passed')}/{raw_master.get('uart_scenarios_total')}, "
            f"OTP={otp_touches}, RPMB={rpmb_incs}, passive_tx={passive_tx}B "
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
    }
    return pillar, meta


def _evaluate_pillar_3(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: Milestone110FaultInjection,
) -> Tuple[Milestone110PillarResult, Dict[str, Any]]:
    # Baseline #1..#14 via _evaluate_domain_4 + #15..#16 + #17..#20 + any extra Phase 111+ *_audit keys
    from .stage_b_milestone90_master_gate import (
        Milestone90FaultInjection,
        _evaluate_pillar_3 as _eval_m90_p3,
    )

    m90_faults = Milestone90FaultInjection(
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
    )
    m90_p3, meta_16 = _eval_m90_p3(auditors, m90_faults)
    errors: List[str] = list(m90_p3.errors)
    auditor_statuses: Dict[str, bool] = dict(m90_p3.evidence["auditor_statuses"])
    auditor_sha256s: Dict[str, Optional[str]] = dict(m90_p3.evidence["auditor_sha256s"])

    # Auditor #17: Phase 89 Gyroflow/Catalyst RTMD, Anamorphic IBIS & IMX510 Rolling-Shutter
    a17 = auditors.get("metadata_gyro_catalyst_and_anamorphic_audit", {})
    a17_ok = isinstance(a17, Mapping) and bool(a17.get("all_checks_passed"))
    if not a17_ok:
        errors.append("p3: #17 metadata_gyro_catalyst_and_anamorphic_audit failed")
    a17_imu_mut = int(a17.get("imu_calibration_mutation_bytes", -1)) + int(
        faults.p3_imu_calibration_mutation_bytes
    )
    a17_cp_mut = int(a17.get("cp_mutation_bytes", -1))
    if a17_imu_mut != 0 or a17_cp_mut != 0:
        errors.append(f"p3: #17 imu_cal_mut={a17_imu_mut} or cp_mut={a17_cp_mut} != 0")
    if a17.get("persistent_emmc_writes_authorized") is not False:
        errors.append("p3: #17 breached persistent_emmc_writes_authorized")

    # Auditor #18: Phase 93 Interval Rec, Picture Cache DDR Ring & USB-LAN FTPS
    a18 = auditors.get("interval_cache_and_ftp_audit", {})
    a18_ok = isinstance(a18, Mapping) and bool(a18.get("all_checks_passed"))
    if not a18_ok:
        errors.append("p3: #18 interval_cache_and_ftp_audit failed")
    a18_cal = int(a18.get("calibration_mutation_bytes", -1))
    a18_emmc = int(a18.get("emmc_mutation_bytes", -1)) + int(faults.p3_emmc_mutation_bytes)
    if a18_cal != 0 or a18_emmc != 0:
        errors.append(f"p3: #18 cal_mut={a18_cal} or emmc_mut={a18_emmc} != 0")
    if a18.get("persistent_emmc_writes_authorized") is not False:
        errors.append("p3: #18 breached persistent_emmc_writes_authorized")

    # Auditor #19: Phase 98 Tetrahedral 3D-LUT, S-Log3 AVI InfoFrame & HDMI->12G-SDI
    a19 = auditors.get("lut3d_cube_tetrahedral_and_sdi_hdmi_audit", {})
    a19_ok = isinstance(a19, Mapping) and bool(a19.get("all_checks_passed"))
    if not a19_ok:
        errors.append("p3: #19 lut3d_cube_tetrahedral_and_sdi_hdmi_audit failed")
    a19_cal = int(a19.get("calibration_mutation_bytes", -1))
    a19_emmc = int(a19.get("emmc_mutation_bytes", -1))
    if a19_cal != 0 or a19_emmc != 0:
        errors.append(f"p3: #19 cal_mut={a19_cal} or emmc_mut={a19_emmc} != 0")
    if a19.get("persistent_emmc_writes_authorized") is not False:
        errors.append("p3: #19 breached persistent_emmc_writes_authorized")

    # Auditor #20: Phase 105 C2PA 2.1 cnflasha Key-Vault, E-Mount Lens Shading & 4-Cam MC Fleet
    a20 = auditors.get("c2pa_lens_shading_and_mc_fleet_audit", {})
    a20_ok = isinstance(a20, Mapping) and bool(a20.get("all_checks_passed"))
    if not a20_ok:
        errors.append("p3: #20 c2pa_lens_shading_and_mc_fleet_audit failed")
    a20_p4 = a20.get("pillar_4_factory_shading_immutability", {})
    a20_cal = int(a20_p4.get("calibration_mutation_bytes", -1)) + int(
        faults.p3_c2pa_shading_mutation_bytes
    )
    a20_emmc = int(a20_p4.get("emmc_mutation_bytes", -1))
    if a20_cal != 0 or a20_emmc != 0 or not bool(a20_p4.get("bit_exact_preservation_verified", False)):
        errors.append(f"p3: #20 factory shading immutability violated (cal={a20_cal}, emmc={a20_emmc})")
    if a20_p4.get("persistent_emmc_writes_authorized") is not False:
        errors.append("p3: #20 breached persistent_emmc_writes_authorized")

    for k, aobj in (
        ("metadata_gyro_catalyst_and_anamorphic_audit", a17),
        ("interval_cache_and_ftp_audit", a18),
        ("lut3d_cube_tetrahedral_and_sdi_hdmi_audit", a19),
        ("c2pa_lens_shading_and_mc_fleet_audit", a20),
    ):
        auditor_statuses[k] = isinstance(aobj, Mapping) and bool(aobj.get("all_checks_passed"))
        auditor_sha256s[k] = (
            str(aobj.get("report_sha256")) if isinstance(aobj, Mapping) and aobj.get("report_sha256") else None
        )

    # Forward-compatible discovery of any Phase 111+ *_audit entries
    for extra_k, extra_v in auditors.items():
        if extra_k not in auditor_statuses and extra_k.endswith("_audit") and isinstance(extra_v, Mapping):
            ok_extra = bool(extra_v.get("all_checks_passed", False))
            auditor_statuses[extra_k] = ok_extra
            auditor_sha256s[extra_k] = (
                str(extra_v.get("report_sha256")) if extra_v.get("report_sha256") else None
            )
            if not ok_extra:
                errors.append(f"p3: extra auditor {extra_k} failed")

    total_count = len(auditor_statuses)
    passed_count = sum(1 for v in auditor_statuses.values() if v)
    total_cal_mut = max(
        int(meta_16["calibration_mutation_bytes"]),
        max(0, a17_imu_mut),
        max(0, a18_cal),
        max(0, a19_cal),
        max(0, a20_cal),
    )

    if total_count < 20 or passed_count < 20 or passed_count != total_count:
        errors.append(
            f"p3: expected >= 20 auditors and all passing, got {passed_count}/{total_count}"
        )

    passed = len(errors) == 0 and total_cal_mut == 0
    evidence = dict(m90_p3.evidence)
    evidence.update(
        {
            "auditor_count": total_count,
            "passed_auditor_count": passed_count,
            "auditor_statuses": auditor_statuses,
            "auditor_sha256s": auditor_sha256s,
            "phase89_gyroflow_anamorphic_ok": a17_ok,
            "phase93_interval_cache_ftp_ok": a18_ok,
            "phase98_lut3d_sdi_hdmi_ok": a19_ok,
            "phase105_c2pa_shading_mc_ok": a20_ok,
            "calibration_mutation_bytes": total_cal_mut,
        }
    )
    pillar = Milestone110PillarResult(
        pillar_id="P3",
        pillar_name="TWENTY_PLUS_FIRMWARE_LAB_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {passed_count}/{total_count} auditors (>=20 required; incl. #17..#20), "
            f"cal_mut={total_cal_mut}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "auditor_count": total_count,
        "passed_count": passed_count,
        "calibration_mutation_bytes": total_cal_mut,
        "bk4_persistent_nvram_writes": int(meta_16["bk4_persistent_nvram_writes"]),
    }
    return pillar, meta


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: Milestone110FaultInjection,
) -> Tuple[Milestone110PillarResult, Dict[str, Any]]:
    from .stage_b_milestone90_master_gate import (
        Milestone90FaultInjection,
        _evaluate_pillar_4 as _eval_m90_p4,
    )

    m90_faults = Milestone90FaultInjection(
        p4_cp_mutation_bytes=faults.p4_cp_mutation_bytes,
        p4_bk4_persistent_nvram_writes=faults.p4_bk4_persistent_nvram_writes,
        p4_stage10_dropped_frames=faults.p4_stage10_dropped_frames,
        p4_stage11_nop_count=faults.p4_stage11_nop_count,
        p4_stage11_null_gpio_derefs=faults.p4_stage11_null_gpio_derefs,
        p4_stage12_uart_contention_events=faults.p4_stage12_uart_contention_events,
        p4_stage13_p1_emmc_format_attempt=faults.p4_stage13_p1_emmc_format_attempt,
        p4_stage13_p4_nd_motor_faults=faults.p4_stage13_p4_nd_motor_faults,
    )
    m90_p4, meta_13 = _eval_m90_p4(vm_rep, m90_faults)
    errors: List[str] = list(m90_p4.errors)
    stage_statuses: Dict[str, bool] = dict(m90_p4.evidence["stage_statuses"])

    # Stages 14..18 checks
    for skey in VM_COEMULATION_18_STAGE_KEYS[13:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if not ok:
            errors.append(f"p4: VM co-emulation {skey} failed")

    # Stage 14: Phase 91 Gyroflow / RTMD / Anamorphic IBIS
    s14 = vm_rep.get("stage14_phase91_gyroflow_rtmd_anamorphic", {})
    if int(s14.get("nop_count", -1)) != 0 or int(s14.get("cp_mutation_bytes", -1)) != 0 or int(
        s14.get("stock_cp_fault_count", -1)
    ) != 0:
        errors.append("p4: Stage 14 Gyroflow/Anamorphic redlines violated")

    # Stage 15: Phase 96 Interval / Picture Cache DDR / FTPS / Fan HIL
    s15 = vm_rep.get("stage15_phase96_interval_cache_ftp_fan", {})
    s15_wf12 = int(s15.get("wf12_00342260_hits", -1)) + int(faults.p4_stage15_wf12_hits)
    if int(s15.get("nop_count", -1)) != 0 or s15_wf12 != 0 or int(s15.get("emmc_partition_mutations", -1)) != 0:
        errors.append(f"p4: Stage 15 redlines violated (wf12_hits={s15_wf12})")

    # Stage 16: Phase 99 Tetrahedral 3D-LUT / Sub-Zero / HDMI->12G-SDI
    s16 = vm_rep.get("stage16_phase99_lut3d_subzero_sdi", {})
    s16_li = int(s16.get("lithium_plating_events", -1)) + int(faults.p4_stage16_lithium_plating_events)
    if (
        int(s16.get("nop_count", -1)) != 0
        or s16_li != 0
        or int(s16.get("sdi_transceiver_faults", -1)) != 0
        or int(s16.get("dropped_rec_triggers", -1)) != 0
    ):
        errors.append(f"p4: Stage 16 redlines violated (lithium_plating={s16_li})")

    # Stage 17: Phase 103 EMI / 12h exFAT / Zero-eMMC Churn
    s17 = vm_rep.get("stage17_phase103_emi_exfat_endurance", {})
    s17_sw = int(s17.get("emmc_sector_writes", -1)) + int(faults.p4_stage17_emmc_sector_writes)
    if (
        int(s17.get("nop_count", -1)) != 0
        or s17_sw != 0
        or int(s17.get("emmc_wear_level_increments", -1)) != 0
        or int(s17.get("cxd90057_gpio_damage_events", -1)) != 0
    ):
        errors.append(f"p4: Stage 17 redlines violated (emmc_sector_writes={s17_sw})")

    # Stage 18: Phase 107 C2PA cnflasha Firewall, E-Mount/PL Shading, 4-Cam MC Fleet & G31/G32 OVP
    s18 = vm_rep.get("stage18_phase107_c2pa_shading_mcfleet_ovp", {})
    s18_cn = int(s18.get("cnflasha_mutation_bytes", -1)) + int(faults.p4_stage18_cnflasha_mutation_bytes)
    s18_pk = int(s18.get("private_key_exports", -1)) + int(faults.p4_stage18_private_key_exports)
    if (
        int(s18.get("nop_count", -1)) != 0
        or s18_cn != 0
        or int(s18.get("private_key_reads", -1)) != 0
        or s18_pk != 0
        or int(s18.get("wf12_00342260_hits", -1)) != 0
        or int(s18.get("cxd90057_pmic_damage_events", -1)) != 0
        or int(s18.get("emount_flange_damage_events", -1)) != 0
        or s18.get("persistent_emmc_writes_authorized") is not False
    ):
        errors.append(
            f"p4: Stage 18 C2PA/MC-Fleet/OVP redlines violated (cnflasha_mut={s18_cn}, key_exports={s18_pk})"
        )

    # Forward-compatible discovery of Stage 19+ entries in vm_rep
    for skey, sval in vm_rep.items():
        if skey not in stage_statuses and skey.startswith("stage") and isinstance(sval, Mapping):
            ok_extra = bool(sval.get("all_checks_passed", False))
            stage_statuses[skey] = ok_extra
            if not ok_extra:
                errors.append(f"p4: extra VM stage {skey} failed")

    total_stages = len(stage_statuses)
    passed_stages = sum(1 for v in stage_statuses.values() if v)
    if total_stages < 18 or passed_stages < 18 or passed_stages != total_stages:
        errors.append(
            f"p4: expected >= 18 VM stages and all passing, got {passed_stages}/{total_stages}"
        )

    passed = len(errors) == 0
    evidence = dict(m90_p4.evidence)
    evidence.update(
        {
            "stage_count": total_stages,
            "passed_stage_count": passed_stages,
            "stage_statuses": stage_statuses,
            "stage14_digest_sha256": s14.get("phase91_audit_digest_sha256"),
            "stage15_wf12_00342260_hits": s15_wf12,
            "stage15_digest_sha256": s15.get("phase96_audit_digest_sha256"),
            "stage16_lithium_plating_events": s16_li,
            "stage16_digest_sha256": s16.get("phase99_audit_digest_sha256"),
            "stage17_emmc_sector_writes": s17_sw,
            "stage17_digest_sha256": s17.get("phase103_audit_digest_sha256"),
            "stage18_cnflasha_mutation_bytes": s18_cn,
            "stage18_private_key_exports": s18_pk,
            "stage18_digest_sha256": s18.get("phase107_audit_digest_sha256"),
        }
    )
    pillar = Milestone110PillarResult(
        pillar_id="P4",
        pillar_name="EIGHTEEN_PLUS_STAGE_VM_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {passed_stages}/{total_stages} stages (>=18 required; Stages 1..18), "
            f"cp_mut={meta_13['cp_mutation_bytes']}B, cnflasha_mut={s18_cn}B, key_exports={s18_pk} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "stage_count": total_stages,
        "passed_count": passed_stages,
        "cp_mutation_bytes": meta_13["cp_mutation_bytes"],
        "bk4_persistent_nvram_writes": meta_13["bk4_persistent_nvram_writes"],
    }
    return pillar, meta


def _verify_stage_b_manifest_and_faithful(
    robj: Mapping[str, Any],
    *,
    tag: str,
    expected_sid: str,
    expected_lang: str,
    manifest_override: Optional[int],
    errors: List[str],
) -> Tuple[int, int, int, bool]:
    nops = int(robj.get("nop_count", -1))
    crashes = int(robj.get("crashes", -1))
    if robj.get("target_sid") != expected_sid or robj.get("lang") != expected_lang:
        errors.append(
            f"{tag}: expected sid={expected_sid} lang={expected_lang}, "
            f"got sid={robj.get('target_sid')!r} lang={robj.get('lang')!r}"
        )
    fi = robj.get("faithful_invariants", {})
    if fi.get("FX6_NATIVE_FAITHFUL") != 1 or any(
        int(fi.get(k, -1)) != 0
        for k in ("subst_color", "subst_image", "forced_render", "skipped_node", "lock_bypass")
    ):
        errors.append(f"{tag}: failed FX6_NATIVE_FAITHFUL invariants")
    sb = robj.get("stage_b", {})
    mc = int(manifest_override) if manifest_override is not None else int(sb.get("manifest_count", -1))
    items = sb.get("manifest_items", [])
    if mc != 13 or len(items) != 13:
        errors.append(f"{tag}: Stage-B manifest count expected 13/13, got {mc}/{len(items)}")
    by_path = {
        str(it.get("guest_path")): str(it.get("sha256")) for it in items if isinstance(it, Mapping)
    }
    sha_ok = (
        by_path.get("/usr/lib/appFw.so") == FX6_APPFW_STAGE_B_SHA256
        and by_path.get("/usr/lib/libWlanResource.so") == FX6_WLAN_RSRC_P12_SHA256
    )
    return nops, crashes, mc, sha_ok


def _evaluate_pillar_5(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: Milestone110FaultInjection,
) -> Tuple[Milestone110PillarResult, Dict[str, Any]]:
    # 1. Round 14 (18/18 4-lang x 3-surface matrix)
    v3_faults = StageBReleaseDossierV3FaultInjection(
        pillar_e_nop_count=faults.p5_round14_nop_count,
        pillar_e_zero_pair_surface="status_check" if faults.p5_round14_zero_pair else None,
        pillar_e_zero_pair_name=ROUND14_4LANG_PAIRS[0] if faults.p5_round14_zero_pair else None,
    )
    pe, meta_r14 = _evaluate_pillar_e(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=v3_faults,
    )
    errors: List[str] = [e.replace("pillar_e", "p5_r14") for e in pe.errors]

    # 2. Round 17 (10/10 Status Check C(10,2)=45 pairs > 0 + wrap-around + WF-12 Tab 9 immunity)
    r17, r17_source = _load_round17_summary(repo_root=repo_root, use_clean_room=use_clean_room)
    r17_schema = str(r17.get("schema", ""))
    r17_kver = str(r17.get("kernel_version", ""))
    if r17_schema != "fx6-on-fx3-round17-status-fullsweep-audio-v1":
        errors.append(f"p5_r17: unexpected Round 17 schema {r17_schema!r}")
    if "4.9.337-scel+" not in r17_kver:
        errors.append(f"p5_r17: unexpected FX3 kernel_version {r17_kver!r}")

    r17_contract = r17.get("status_check_multitab_contract", {})
    r17_tabs = r17_contract.get("tabs_verified", [])
    r17_sids = tuple(str(t.get("sid", "")) for t in r17_tabs if isinstance(t, Mapping))
    if r17_sids != ROUND17_MULTITAB_SIDS or not bool(r17_contract.get("wrap_around_verified", False)):
        errors.append(
            f"p5_r17: Status Check 10-tab contract mismatch (sids={r17_sids!r}, wrap={r17_contract.get('wrap_around_verified')})"
        )

    r17_runs = r17.get("runs", {})
    r17_nops = int(faults.p5_round17_nop_count)
    r17_crashes = int(faults.p5_round17_crashes)
    r17_runs_verified = 0
    r17_sha_ok = True
    for run_id, expected_sid, expected_lang in ROUND17_RUN_SPECS:
        robj = r17_runs.get(run_id)
        if not isinstance(robj, Mapping):
            errors.append(f"p5_r17: missing Round 17 run {run_id}")
            continue
        rnop, rcrash, _, rsha = _verify_stage_b_manifest_and_faithful(
            robj,
            tag=f"p5_r17:{run_id}",
            expected_sid=expected_sid,
            expected_lang=expected_lang,
            manifest_override=faults.p5_round17_manifest_count_override,
            errors=errors,
        )
        r17_nops += rnop
        r17_crashes += rcrash
        r17_sha_ok = r17_sha_ok and rsha
        r17_runs_verified += 1
    if not r17_sha_ok:
        errors.append("p5_r17: Stage-B manifest SHA-256 mismatch for appFw.so or libWlanResource.so")
    if r17_nops != 0 or r17_crashes != 0:
        errors.append(f"p5_r17: real-kernel nop={r17_nops} or crash={r17_crashes} != 0")

    r17_audit = copy.deepcopy(r17.get("r17_status_fullsweep_and_audio_audit", {}))
    r17_pw_block = r17_audit.get("status_check_10tab_pairwise_schinese", {})
    r17_pairs = r17_pw_block.get("pairs", {})
    if faults.p5_round17_zero_tab_pair and faults.p5_round17_zero_tab_pair in r17_pairs:
        r17_pairs[faults.p5_round17_zero_tab_pair]["diff_pixels"] = 0
        r17_pairs[faults.p5_round17_zero_tab_pair]["strictly_positive"] = False

    r17_pos_pairs = 0
    for pk, ent in r17_pairs.items():
        if isinstance(ent, Mapping) and int(ent.get("diff_pixels", 0)) > 0 and bool(
            ent.get("strictly_positive", False)
        ):
            r17_pos_pairs += 1
        else:
            errors.append(f"p5_r17: 10-tab Status Check pair {pk} is not strictly positive")
    if int(r17_pw_block.get("pair_count", -1)) != 45 or r17_pos_pairs != 45:
        errors.append(f"p5_r17: 10-tab Status Check expected 45/45 positive pairs, got {r17_pos_pairs}")

    r17_wrap = r17_audit.get("status_check_wraparound_proof", {})
    r17_wrap_ok = (
        int(r17_wrap.get("step_count_down", 0)) == 10
        and str(r17_wrap.get("target_sid", "")) == "0x2f"
        and bool(r17_wrap.get("all_non_tab1_diffs_strictly_positive", False))
        and not faults.p5_round17_zero_wraparound
    )
    if not r17_wrap_ok:
        errors.append("p5_r17: Status Check 10-step wrap-around proof failed")

    r17_wf12 = r17_audit.get("wf12_00342260_network_tab_immunity", {})
    if (
        int(r17_wf12.get("p12_wlan", 0)) != 1
        or int(r17_wf12.get("wf12_00342260_immune", 0)) != 1
        or int(r17_wf12.get("airplane_bk4_hits", -1)) != 0
    ):
        errors.append("p5_r17: WF-12 0x00342260 Tab 9 Network immunity check failed")

    # 3. Round 19 (11/11 Full-Menu C(11,2)=55 pairs > 0 + 11-down wrap + TChinese WF-12 immunity)
    r19, r19_source = _load_round19_summary(repo_root=repo_root, use_clean_room=use_clean_room)
    r19_schema = str(r19.get("schema", ""))
    r19_kver = str(r19.get("kernel_version", ""))
    if r19_schema != "fx6-on-fx3-round19-menu-11cat-fullsweep-v1":
        errors.append(f"p5_r19: unexpected Round 19 schema {r19_schema!r}")
    if "4.9.337-scel+" not in r19_kver:
        errors.append(f"p5_r19: unexpected FX3 kernel_version {r19_kver!r}")

    r19_contract = r19.get("full_menu_l1_rail_contract", {})
    r19_cats = r19_contract.get("rail_categories_visible_in_shooting_mode", [])
    r19_cat_names = tuple(str(c.get("category", "")) for c in r19_cats if isinstance(c, Mapping))
    if r19_cat_names != ROUND19_11CAT_NAMES:
        errors.append(f"p5_r19: 11-category shooting rail mismatch: {r19_cat_names!r}")

    r19_runs = r19.get("runs", {})
    r19_nops = int(faults.p5_round19_nop_count)
    r19_crashes = int(faults.p5_round19_crashes)
    r19_runs_verified = 0
    r19_sha_ok = True
    for run_id, expected_sid, expected_lang in ROUND19_RUN_SPECS:
        robj = r19_runs.get(run_id)
        if not isinstance(robj, Mapping):
            errors.append(f"p5_r19: missing Round 19 run {run_id}")
            continue
        rnop, rcrash, _, rsha = _verify_stage_b_manifest_and_faithful(
            robj,
            tag=f"p5_r19:{run_id}",
            expected_sid=expected_sid,
            expected_lang=expected_lang,
            manifest_override=faults.p5_round19_manifest_count_override,
            errors=errors,
        )
        r19_nops += rnop
        r19_crashes += rcrash
        r19_sha_ok = r19_sha_ok and rsha
        r19_runs_verified += 1
    if not r19_sha_ok:
        errors.append("p5_r19: Stage-B manifest SHA-256 mismatch for appFw.so or libWlanResource.so")
    if r19_nops != 0 or r19_crashes != 0:
        errors.append(f"p5_r19: real-kernel nop={r19_nops} or crash={r19_crashes} != 0")

    r19_audit = copy.deepcopy(r19.get("r19_menu_11cat_fullsweep_audit", {}))
    r19_pw_block = r19_audit.get("menu_11cat_schinese_pairwise", {})
    r19_pairs = r19_pw_block.get("pairs", {})
    if faults.p5_round19_zero_cat_pair and faults.p5_round19_zero_cat_pair in r19_pairs:
        r19_pairs[faults.p5_round19_zero_cat_pair]["diff_pixels"] = 0
        r19_pairs[faults.p5_round19_zero_cat_pair]["strictly_positive"] = False

    r19_pos_pairs = 0
    for pk, ent in r19_pairs.items():
        if isinstance(ent, Mapping) and int(ent.get("diff_pixels", 0)) > 0 and bool(
            ent.get("strictly_positive", False)
        ):
            r19_pos_pairs += 1
        else:
            errors.append(f"p5_r19: 11-category Full-Menu pair {pk} is not strictly positive")
    if int(r19_pw_block.get("pair_count", -1)) != 55 or r19_pos_pairs != 55:
        errors.append(f"p5_r19: 11-category Full-Menu expected 55/55 positive pairs, got {r19_pos_pairs}")

    r19_wrap = r19_audit.get("menu_11down_wraparound_proof", {})
    r19_wrap_ok = (
        int(r19_wrap.get("step_count_down", 0)) == 11
        and int(r19_wrap.get("cat_id", -1)) == 8
        and bool(r19_wrap.get("all_non_user_diffs_strictly_positive", False))
        and not faults.p5_round19_zero_wraparound
    )
    if not r19_wrap_ok:
        errors.append("p5_r19: Full-Menu 11-down wrap-around proof failed")

    r19_tc = r19_audit.get("network_tchinese_vs_schinese_delta", {})
    r19_tc_px = 0 if faults.p5_round19_zero_tchinese_delta else int(r19_tc.get("diff_pixels", 0))
    if r19_tc_px <= 0 or (not faults.p5_round19_zero_tchinese_delta and not bool(r19_tc.get("strictly_positive", False))):
        errors.append("p5_r19: ZH-TW vs ZH-CN Network pixel delta is not strictly positive")

    r19_wf12 = r19_audit.get("wf12_00342260_network_tchinese_immunity", {})
    wf12_val = (
        int(faults.p5_round19_wf12_immune_override)
        if faults.p5_round19_wf12_immune_override is not None
        else int(r19_wf12.get("wf12_00342260_immune", 0))
    )
    if (
        int(r19_wf12.get("p12_wlan", 0)) != 1
        or wf12_val != 1
        or int(r19_wf12.get("airplane_bk4_hits", -1)) != 0
    ):
        errors.append(f"p5_r19: WF-12 0x00342260 ZH-TW Network immunity check failed (wf12={wf12_val})")

    total_nops = int(meta_r14["nop_count"]) + r17_nops + r19_nops
    total_crashes = r17_crashes + r19_crashes
    passed = (
        len(errors) == 0
        and pe.passed
        and len(r17_sids) == 10
        and r17_pos_pairs == 45
        and r17_wrap_ok
        and r17_runs_verified == len(ROUND17_RUN_SPECS)
        and len(r19_cat_names) == 11
        and r19_pos_pairs == 55
        and r19_wrap_ok
        and r19_runs_verified == len(ROUND19_RUN_SPECS)
        and total_nops == 0
        and total_crashes == 0
    )
    evidence = {
        "round14_positive_pairs": meta_r14["positive_pairs"],
        "round14_source": pe.evidence["round14_source"],
        "round17_source": r17_source,
        "round17_schema": r17_schema,
        "round17_kernel_version": r17_kver,
        "round17_tabs_verified": len(r17_sids),
        "round17_tab_sids": list(r17_sids),
        "round17_pairwise_deltas_verified": r17_pos_pairs,
        "round17_wraparound_verified": r17_wrap_ok,
        "round17_runs_verified": r17_runs_verified,
        "round17_nop_count": r17_nops,
        "round17_crashes": r17_crashes,
        "round17_wf12_immune": int(r17_wf12.get("wf12_00342260_immune", 0)),
        "round19_source": r19_source,
        "round19_schema": r19_schema,
        "round19_kernel_version": r19_kver,
        "round19_categories_verified": len(r19_cat_names),
        "round19_category_names": list(r19_cat_names),
        "round19_pairwise_deltas_verified": r19_pos_pairs,
        "round19_wraparound_verified": r19_wrap_ok,
        "round19_tchinese_vs_schinese_pixels": r19_tc_px,
        "round19_runs_verified": r19_runs_verified,
        "round19_nop_count": r19_nops,
        "round19_crashes": r19_crashes,
        "round19_wf12_immune": wf12_val,
        "real_kernel_nop_count": total_nops,
        "real_kernel_crashes": total_crashes,
    }
    pillar = Milestone110PillarResult(
        pillar_id="P5",
        pillar_name="REAL_KERNEL_R14_R17_R19_COMPLETE_UI_CLOSURES",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"R14 {meta_r14['positive_pairs']}/18 + R17 Status {len(r17_sids)}/10 ({r17_pos_pairs}/45 pairs>0, wrap={r17_wrap_ok}) "
            f"+ R19 Menu {len(r19_cat_names)}/11 ({r19_pos_pairs}/55 pairs>0, wrap={r19_wrap_ok}, WF12={wf12_val}), "
            f"nop={total_nops}, crash={total_crashes} {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "round14_positive_pairs": meta_r14["positive_pairs"],
        "round17_tabs_verified": len(r17_sids),
        "round17_pairwise_deltas_verified": r17_pos_pairs,
        "round17_runs_verified": r17_runs_verified,
        "round19_categories_verified": len(r19_cat_names),
        "round19_pairwise_deltas_verified": r19_pos_pairs,
        "round19_runs_verified": r19_runs_verified,
        "real_kernel_nop_count": total_nops,
        "real_kernel_crashes": total_crashes,
    }
    return pillar, meta


def _evaluate_pillar_6(
    raw_6: Mapping[str, Any],
    faults: Milestone110FaultInjection,
    *,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
) -> Tuple[Milestone110PillarResult, Dict[str, Any]]:
    v3_faults = StageBReleaseDossierV3FaultInjection(
        pillar_f_drift_surface=faults.p6_drift_surface,
        pillar_f_tamper_negative_control=faults.p6_tamper_negative_control,
    )
    pf, meta_f = _evaluate_pillar_f(raw_6, v3_faults)
    errors: List[str] = [e.replace("pillar_f", "p6") for e in pf.errors]
    if DOSSIER_V3_SCHEMA_VERSION != STAGE_B_RELEASE_DOSSIER_V3_SCHEMA or len(DOSSIER_V3_PILLAR_IDS) != 6:
        errors.append("p6: Dossier v3 anchor contract mismatch")
    if CAPSTONE_22GATE_SCHEMA_VERSION != STAGE_B_CAPSTONE_22GATE_SCHEMA or len(CAPSTONE_DOMAIN_IDS) != 7:
        errors.append("p6: Capstone 22-Gate anchor contract mismatch")
    if MILESTONE90_SCHEMA_VERSION != STAGE_B_MILESTONE90_SCHEMA or len(MILESTONE90_PILLAR_IDS) != 6:
        errors.append("p6: Milestone 90 anchor contract mismatch")

    # Cross-pillar hardware-lock invariants
    if (
        p1_meta.get("persistent_emmc_writes_authorized") is not False
        or p1_meta.get("simulated_ready_for_hardware_attach") is not False
    ):
        errors.append("p6: P1 hardware-lock invariant breached")
    if (
        int(p2_meta.get("otp_fuse_touches", -1)) != 0
        or int(p2_meta.get("rpmb_counter_increments", -1)) != 0
        or int(p2_meta.get("passive_tx_bytes_emitted", -1)) != 0
    ):
        errors.append("p6: P2 zero-touch OTP/RPMB/UART-TX invariant breached")
    if int(p3_meta.get("calibration_mutation_bytes", -1)) != 0:
        errors.append("p6: P3 calibration zero-mutation invariant breached")
    if (
        int(p4_meta.get("cp_mutation_bytes", -1)) != 0
        or int(p4_meta.get("bk4_persistent_nvram_writes", -1)) != 0
    ):
        errors.append("p6: P4 CP/BK4 zero-mutation invariant breached")

    passed = len(errors) == 0 and pf.passed
    evidence = dict(pf.evidence)
    evidence["dossier_v3_schema_anchor"] = DOSSIER_V3_SCHEMA_VERSION
    evidence["capstone_22gate_schema_anchor"] = CAPSTONE_22GATE_SCHEMA_VERSION
    evidence["milestone90_schema_anchor"] = MILESTONE90_SCHEMA_VERSION
    evidence["persistent_emmc_writes_authorized"] = PERSISTENT_EMMC_WRITES_AUTHORIZED
    evidence["otp_fuse_touches"] = int(p2_meta.get("otp_fuse_touches", 0))
    evidence["passive_tx_bytes_emitted"] = int(p2_meta.get("passive_tx_bytes_emitted", 0))

    pillar = Milestone110PillarResult(
        pillar_id="P6",
        pillar_name="POST_TRIAL_H0_VS_H2_IMMUTABILITY_AND_HARDWARE_LOCK_PROOF",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"DossierV3+Capstone22+M90 + H0==H2 {meta_f['h0_surface_count']}/16 surfaces "
            f"(drifted={meta_f['drifted_surface_count']}, C2PA={meta_f['c2pa_rq_lic_intact']}, "
            f"emmc_auth={PERSISTENT_EMMC_WRITES_AUTHORIZED}, otp={p2_meta.get('otp_fuse_touches', 0)}, "
            f"tx={p2_meta.get('passive_tx_bytes_emitted', 0)}B) {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    return pillar, meta_f


# ---------------------------------------------------------------------------
# Parallel Collector, Builder & Fail-Closed Verifier
# ---------------------------------------------------------------------------


def _fault_to_worker_dict(faults: Milestone110FaultInjection) -> Dict[str, Any]:
    return {
        "p1_pl_cantilever_kwargs": dict(faults.p1_pl_cantilever_kwargs)
        if faults.p1_pl_cantilever_kwargs is not None
        else None,
        "p1_dummy_battery_kwargs": dict(faults.p1_dummy_battery_kwargs)
        if faults.p1_dummy_battery_kwargs is not None
        else None,
        "p1_dewpoint_kwargs": dict(faults.p1_dewpoint_kwargs)
        if faults.p1_dewpoint_kwargs is not None
        else None,
        "p1_pmic_usbc_kwargs": dict(faults.p1_pmic_usbc_kwargs)
        if faults.p1_pmic_usbc_kwargs is not None
        else None,
        "p1_xlr_kwargs": dict(faults.p1_xlr_kwargs) if faults.p1_xlr_kwargs is not None else None,
        "p1_gimbal_kwargs": dict(faults.p1_gimbal_kwargs) if faults.p1_gimbal_kwargs is not None else None,
        "p1_rig_kwargs": dict(faults.p1_rig_kwargs) if faults.p1_rig_kwargs is not None else None,
        "p1_emount_kwargs": dict(faults.p1_emount_kwargs) if faults.p1_emount_kwargs is not None else None,
        "p1_power_failover_kwargs": dict(faults.p1_power_failover_kwargs)
        if faults.p1_power_failover_kwargs is not None
        else None,
        "p1_intake_fan_kwargs": dict(faults.p1_intake_fan_kwargs)
        if faults.p1_intake_fan_kwargs is not None
        else None,
        "p1_tripod_housing_kwargs": dict(faults.p1_tripod_housing_kwargs)
        if faults.p1_tripod_housing_kwargs is not None
        else None,
        "p1_sensor_curtain_kwargs": dict(faults.p1_sensor_curtain_kwargs)
        if faults.p1_sensor_curtain_kwargs is not None
        else None,
        "p1_subzero_altitude_kwargs": dict(faults.p1_subzero_altitude_kwargs)
        if faults.p1_subzero_altitude_kwargs is not None
        else None,
        "p1_wireless_tx_emi_kwargs": dict(faults.p1_wireless_tx_emi_kwargs)
        if faults.p1_wireless_tx_emi_kwargs is not None
        else None,
        "p1_longform_endurance_kwargs": dict(faults.p1_longform_endurance_kwargs)
        if faults.p1_longform_endurance_kwargs is not None
        else None,
        "p1_request_persistent_writes": bool(faults.p1_request_persistent_writes),
        "d2_otp_downgrade_version": faults.p2_otp_downgrade_version,
        "d2_inject_cross_sku_target": faults.p2_inject_cross_sku_target,
        "d2_inject_ext_csd_perm_wp": bool(faults.p2_inject_ext_csd_perm_wp),
        "p2_inject_cross_body_cnflasha_transplant": bool(
            faults.p2_inject_cross_body_cnflasha_transplant
        ),
    }


def _collect_parallel_milestone110_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: Milestone110FaultInjection,
) -> Tuple[
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
    Dict[str, Any],
]:
    fault_dict = _fault_to_worker_dict(faults)
    p3_groups = (
        "group_a",
        "group_b",
        "multilang",
        "sensor",
        "haita",
        "emount",
        "wbi",
        "assignable",
        "falsecolor",
        "playback",
        "gyroflow",
        "interval_ftp",
        "lut3d_sdi",
        "c2pa_mc",
    )

    try:
        ctx = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=14, mp_context=ctx) as ex:
            fut_1 = ex.submit(_worker_pillar_1, (str(repo_root), use_clean_room, fault_dict))
            fut_2m = ex.submit(_worker_recovery_master, use_clean_room)
            fut_2x = ex.submit(_worker_recovery_p8_p9_p10, use_clean_room)
            fut_2a = ex.submit(_worker_domain_2, (use_clean_room, fault_dict))
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
            fut_3 = [ex.submit(_worker_pillar_3_group, (g, use_clean_room)) for g in p3_groups]
            fut_4 = ex.submit(_worker_pillar_4, use_clean_room)
            fut_6 = ex.submit(
                _worker_pillar_f,
                (
                    str(fx6_lib_dir),
                    str(fx3_modules_dir),
                    use_clean_room,
                    faults.p6_drift_surface,
                ),
            )
            raw_1 = fut_1.result()
            raw_2m = fut_2m.result()
            raw_2x = fut_2x.result()
            raw_2a = fut_2a.result()
            raw_2b = fut_2b.result()
            auditors: Dict[str, Dict[str, Any]] = {}
            for fg in fut_3:
                auditors.update(fg.result())
            raw_4 = fut_4.result()
            raw_6 = fut_6.result()
            return raw_1, raw_2m, raw_2x, raw_2a, raw_2b, auditors, raw_4, raw_6
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1 = _worker_pillar_1((str(repo_root), use_clean_room, fault_dict))
    raw_2m = _worker_recovery_master(use_clean_room)
    raw_2x = _worker_recovery_p8_p9_p10(use_clean_room)
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
    for g in p3_groups:
        auditors.update(_worker_pillar_3_group((g, use_clean_room)))
    raw_4 = _worker_pillar_4(use_clean_room)
    raw_6 = _worker_pillar_f(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, faults.p6_drift_surface)
    )
    return raw_1, raw_2m, raw_2x, raw_2a, raw_2b, auditors, raw_4, raw_6


def build_stage_b_milestone110_master_gate_report(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[Milestone110FaultInjection] = None,
) -> StageBMilestone110MasterGateReport:
    """Build deterministic 6-Pillar Milestone Phase 110 Century+10 Master Gate report (`< 2.5s`)."""
    active_faults = faults if faults is not None else Milestone110FaultInjection()
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )

    raw_1, raw_2m, raw_2x, raw_2a, raw_2b, auditors, raw_4, raw_6 = (
        _collect_parallel_milestone110_results(
            repo_root=repo_root,
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
            use_clean_room=use_clean_room,
            faults=active_faults,
        )
    )

    p1 = _evaluate_pillar_1(raw_1)
    p2, meta_2 = _evaluate_pillar_2(raw_2m, raw_2x, raw_2a, raw_2b, active_faults)
    p3, meta_3 = _evaluate_pillar_3(auditors, active_faults)
    p4, meta_4 = _evaluate_pillar_4(raw_4, active_faults)
    p5, meta_5 = _evaluate_pillar_5(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )
    p6, meta_6 = _evaluate_pillar_6(
        raw_6,
        active_faults,
        p1_meta=p1.evidence,
        p2_meta=meta_2,
        p3_meta=meta_3,
        p4_meta=meta_4,
    )

    pillars: Tuple[Milestone110PillarResult, ...] = (p1, p2, p3, p4, p5, p6)
    passed_count = sum(1 for p in pillars if p.passed)
    failed_ids = tuple(p.pillar_id for p in pillars if not p.passed)
    all_errors: List[str] = []
    for p in pillars:
        all_errors.extend(p.errors)

    all_ready = passed_count == len(pillars) and len(all_errors) == 0
    mode_str = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"

    payload_no_sha: Dict[str, Any] = {
        "schema_version": STAGE_B_MILESTONE110_SCHEMA,
        "phase_version": PHASE_110_VERSION,
        "verification_mode": mode_str,
        "all_pillars_milestone_ready": all_ready,
        "status": STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "hardware_live_attachment_requirements": HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
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
        "gate32_offline_verified": raw_1["offline_verified_gates"],
        "gate32_simulated_verified": raw_1["sim_verified_gates"],
        "recovery_pillar_count": meta_2["recovery_pillar_count"],
        "recovery_pillars_passed": meta_2["recovery_pillars_passed"],
        "firmware_lab_auditor_count": meta_3["auditor_count"],
        "firmware_lab_auditors_passed": meta_3["passed_count"],
        "vm_coemulation_stage_count": meta_4["stage_count"],
        "vm_coemulation_stages_passed": meta_4["passed_count"],
        "round14_positive_pairs": meta_5["round14_positive_pairs"],
        "round17_tabs_verified": meta_5["round17_tabs_verified"],
        "round17_pairwise_deltas_verified": meta_5["round17_pairwise_deltas_verified"],
        "round17_runs_verified": meta_5["round17_runs_verified"],
        "round19_categories_verified": meta_5["round19_categories_verified"],
        "round19_pairwise_deltas_verified": meta_5["round19_pairwise_deltas_verified"],
        "round19_runs_verified": meta_5["round19_runs_verified"],
        "real_kernel_nop_count": meta_5["real_kernel_nop_count"],
        "real_kernel_crashes": meta_5["real_kernel_crashes"],
        "h0_surface_count": meta_6["h0_surface_count"],
        "drifted_surface_count": meta_6["drifted_surface_count"],
        "c2pa_rq_lic_intact": meta_6["c2pa_rq_lic_intact"],
        "spacc_cnflasha_untouched": meta_6["spacc_cnflasha_untouched"],
        "errors": tuple(all_errors),
    }
    digest = compute_milestone110_sha256(payload_no_sha)

    return StageBMilestone110MasterGateReport(
        schema_version=STAGE_B_MILESTONE110_SCHEMA,
        phase_version=PHASE_110_VERSION,
        verification_mode=mode_str,
        all_pillars_milestone_ready=all_ready,
        status=STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        hardware_live_attachment_requirements=HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
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
        gate32_offline_verified=raw_1["offline_verified_gates"],
        gate32_simulated_verified=raw_1["sim_verified_gates"],
        recovery_pillar_count=meta_2["recovery_pillar_count"],
        recovery_pillars_passed=meta_2["recovery_pillars_passed"],
        firmware_lab_auditor_count=meta_3["auditor_count"],
        firmware_lab_auditors_passed=meta_3["passed_count"],
        vm_coemulation_stage_count=meta_4["stage_count"],
        vm_coemulation_stages_passed=meta_4["passed_count"],
        round14_positive_pairs=meta_5["round14_positive_pairs"],
        round17_tabs_verified=meta_5["round17_tabs_verified"],
        round17_pairwise_deltas_verified=meta_5["round17_pairwise_deltas_verified"],
        round17_runs_verified=meta_5["round17_runs_verified"],
        round19_categories_verified=meta_5["round19_categories_verified"],
        round19_pairwise_deltas_verified=meta_5["round19_pairwise_deltas_verified"],
        round19_runs_verified=meta_5["round19_runs_verified"],
        real_kernel_nop_count=meta_5["real_kernel_nop_count"],
        real_kernel_crashes=meta_5["real_kernel_crashes"],
        h0_surface_count=meta_6["h0_surface_count"],
        drifted_surface_count=meta_6["drifted_surface_count"],
        c2pa_rq_lic_intact=meta_6["c2pa_rq_lic_intact"],
        spacc_cnflasha_untouched=meta_6["spacc_cnflasha_untouched"],
        errors=tuple(all_errors),
        milestone110_sha256=digest,
    )


def verify_stage_b_milestone110_master_gate(
    report: object,
) -> StageBMilestone110VerifyResult:
    """Fail-closed verifier for a Milestone Phase 110 Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, StageBMilestone110MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return StageBMilestone110VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone110_sha256="",
            observed_milestone110_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or StageBMilestone110MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = payload.get("schema_version") == STAGE_B_MILESTONE110_SCHEMA
    if not schema_ok:
        errors.append(f"unexpected schema_version={payload.get('schema_version')!r}")

    expected_sha = str(payload.get("milestone110_sha256", ""))
    observed_sha = compute_milestone110_sha256(payload)
    digest_matched = bool(expected_sha) and expected_sha == observed_sha
    if not digest_matched:
        errors.append(
            f"milestone110_sha256 mismatch: expected={expected_sha[:16]}.. observed={observed_sha[:16]}.."
        )

    redlines_ok = (
        payload.get("persistent_emmc_writes_authorized") is False
        and payload.get("persistent_write_release") is False
        and payload.get("hardware_live_attachment_authorized") is False
        and payload.get("o_rdonly_enforced") is True
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
        errors.append("hard-locked zero-write / zero-OTP / zero-TX / zero-attach redlines breached")

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
        int(payload.get("gate32_offline_verified", -1)) >= 29
        and int(payload.get("gate32_simulated_verified", -1)) >= 32
        and int(payload.get("recovery_pillar_count", -1)) >= 10
        and int(payload.get("recovery_pillars_passed", -1))
        == int(payload.get("recovery_pillar_count", -2))
        and int(payload.get("firmware_lab_auditor_count", -1)) >= 20
        and int(payload.get("firmware_lab_auditors_passed", -1))
        == int(payload.get("firmware_lab_auditor_count", -2))
        and int(payload.get("vm_coemulation_stage_count", -1)) >= 18
        and int(payload.get("vm_coemulation_stages_passed", -1))
        == int(payload.get("vm_coemulation_stage_count", -2))
        and int(payload.get("round14_positive_pairs", -1)) == 18
        and int(payload.get("round17_tabs_verified", -1)) == 10
        and int(payload.get("round17_pairwise_deltas_verified", -1)) == 45
        and int(payload.get("round17_runs_verified", -1)) == len(ROUND17_RUN_SPECS)
        and int(payload.get("round19_categories_verified", -1)) == 11
        and int(payload.get("round19_pairwise_deltas_verified", -1)) == 55
        and int(payload.get("round19_runs_verified", -1)) == len(ROUND19_RUN_SPECS)
        and int(payload.get("real_kernel_nop_count", -1)) == 0
        and int(payload.get("real_kernel_crashes", -1)) == 0
        and int(payload.get("h0_surface_count", -1)) == 16
        and int(payload.get("drifted_surface_count", -1)) == 0
        and payload.get("c2pa_rq_lic_intact") is True
        and payload.get("spacc_cnflasha_untouched") is True
    )
    if not counts_ok:
        errors.append("milestone110 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append("all_pillars_milestone_ready / status is not MILESTONE_110_SIMULATION_READY")

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 110 payload")

    valid = bool(schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0)
    return StageBMilestone110VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone110_sha256=expected_sha,
        observed_milestone110_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


def render_milestone110_markdown(report: StageBMilestone110MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 110 Master Gate."""
    lines = [
        f"# Stage-B Milestone Phase 110 Master Gate (`{report.schema_version}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone110_sha256}`",
        "",
        "## Hard-Locked Safety Redlines / 硬锁定安全红线",
        f"- `persistent_emmc_writes_authorized = {report.persistent_emmc_writes_authorized}`",
        f"- `persistent_write_release = {report.persistent_write_release}`",
        f"- `hardware_live_attachment_authorized = {report.hardware_live_attachment_authorized}`",
        f"- `otp_fuse_touches = {report.otp_fuse_touches}`, `rpmb_counter_increments = {report.rpmb_counter_increments}`, `passive_tx_bytes_emitted = {report.passive_tx_bytes_emitted}`",
        f"- `cp_mutation_bytes = {report.cp_mutation_bytes}`, `wbi_mutation_bytes = {report.wbi_mutation_bytes}`, `calibration_mutation_bytes = {report.calibration_mutation_bytes}`, `usb_or_camera_operations = {report.usb_or_camera_operations}`",
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
            "## Key Closure Metrics / 关键闭环指标",
            f"- 32-Gate Preflight (`G01..G32`): offline=`{report.gate32_offline_verified}/32` (blocked), simulated=`{report.gate32_simulated_verified}/32`",
            f"- Recovery Master Suite (`Ph47..106`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`>=10` pillars, UART `S0..S6`, `passive_tx={report.passive_tx_bytes_emitted}B`)",
            f"- Firmware-Lab Auditors: `{report.firmware_lab_auditors_passed}/{report.firmware_lab_auditor_count}` (`>=20` required)",
            f"- Full-Board Co-Emulation VM: `{report.vm_coemulation_stages_passed}/{report.vm_coemulation_stage_count}` (`>=18` required)",
            f"- Real FX3 `7.02` Kernel (`4.9.337-scel+`): Round 14 `{report.round14_positive_pairs}/18` + Round 17 Status `{report.round17_tabs_verified}/10` (`{report.round17_pairwise_deltas_verified}/45` pairs > 0) + Round 19 Menu `{report.round19_categories_verified}/11` (`{report.round19_pairwise_deltas_verified}/55` pairs > 0), `nop={report.real_kernel_nop_count}`, `crashes={report.real_kernel_crashes}`",
            f"- `H0 == H2` Immutability: `{report.h0_surface_count - report.drifted_surface_count}/{report.h0_surface_count}` zero drift (`c2pa_rq_lic_intact={report.c2pa_rq_lic_intact}`, `spacc_cnflasha_untouched={report.spacc_cnflasha_untouched}`)",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "CALIBRATION_MUTATION_BYTES",
    "CP_MUTATION_BYTES",
    "DEFAULT_REPO_ROOT",
    "FIRMWARE_LAB_20_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "MILESTONE110_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "P8_CP_MUTATION_FORBIDDEN",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_110_VERSION",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "RECOVERY_10_PILLAR_IDS",
    "ROUND17_MULTITAB_SIDS",
    "ROUND17_RUN_IDS",
    "ROUND17_RUN_SPECS",
    "ROUND17_SUMMARY_RELPATH",
    "ROUND19_11CAT_NAMES",
    "ROUND19_11CAT_PAIR_KEYS",
    "ROUND19_11CAT_SPECS",
    "ROUND19_RUN_IDS",
    "ROUND19_RUN_SPECS",
    "ROUND19_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "SCHEMA_VERSION",
    "STAGE_B_MILESTONE110_SCHEMA",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "VM_COEMULATION_18_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone110FaultInjection",
    "Milestone110PillarResult",
    "StageBMilestone110MasterGateReport",
    "StageBMilestone110VerifyResult",
    "build_stage_b_milestone110_master_gate_report",
    "compute_milestone110_sha256",
    "render_milestone110_markdown",
    "verify_stage_b_milestone110_master_gate",
]
