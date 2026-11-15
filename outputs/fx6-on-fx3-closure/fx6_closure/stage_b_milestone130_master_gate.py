"""Phase 130 — 6-Pillar Milestone Master Gate (`stage_b_milestone130_master_gate_v1`).

Composes all six Milestone Phase 130 engineering & safety pillars (`P1 .. P6`) into a single
tamper-evident, fail-closed certificate executing in `< 2.5s` across both
`LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:

- `P1` (`SAFETY_40GATE_MASTER_PREFLIGHT`):
  Runs Phase 129 `monsoon_mishoe_cagetwist_and_40gate_guard.evaluate_40gate_preflight`
  (`G01..G40`), verifying `>= 37/40` offline hardware-truth block (`overall_ready_for_hardware_attach=False`)
  vs `>= 40/40` simulated rehearsal (`dry_run_rehearsal_only=True`, `persistent_emmc_writes_authorized=False`),
  covering `G01..G32` plus `G33..G40` (salt-spray/alkali/haze, wireless follow-focus/gimbal CoG,
  HDMI AOC 5V backfeed, CFexpress VPG/NVMe thermal/door flush, USB-PD/UVC crossfeed, multi-terminal
  LTC/1.8V UART/PTP flash firewall, monsoon MI-Shoe rain/flap capillary, XLR-H1 whip shear & 1/4-20 cage twist).
- `P2` (`THIRTEEN_PLUS_PILLAR_RECOVERY_MASTER_SUITE`):
  Verifies all `>= 13` recovery & unbrick pillars (`Phases 47..124`):
  - Pillars 1..7 (`run_recovery_master_suite`): macOS USB transport guard, RP2040-Zero 1.8V `-DOPEN_DRAIN`
    bench fixture, init2 SD sentinel escape / WDT / FAT12+FAT16 swap, GF(256) P+Q 2-erasure/1-bitrot healer
    & cross-body `cnflasha` lock, `CXD90057` OTP/RPMB monotonic anti-rollback + `EXT_CSD` perm-WP block,
    Tier-0..4 escalation ladder & passive 1.8V RX-only UART boot-stage decoder (`S0..S6`, `10/10` scenarios).
  - Pillars 8..10 (`Phases 94/101/106`): GPT CRC32 + RPMB HMAC replay + SD rescue bundle, SVR4 `newc` cpio /
    JEDEC `EXT_CSD` Pre-EOL + `tmpfs`/`overlayfs` isolation, FDT `/chosen/bootargs` & ARM64 `4.9.337-scel+` kernel gate.
  - Pillar 11 (`Phase 113`, `run_ab_bank_and_interrupted_ota_suite`): Dual-bank A/B & interrupted `BODYDATA.DAT` OTA triage.
  - Pillar 12 (`Phase 119`, `run_squashfs_and_hibdrv_wbi_suite`): SquashFS 4.0 `hsqs` & Warp-Boot `hibdrv` WBI2 triage.
  - Pillar 13 (`Phase 124`, `run_bootrom_usb_and_emmc_bootpart_suite`): Mask-BootROM USB & JEDEC eMMC `BOOT0/BOOT1` triage.
  All while locking `otp_fuse_touches == 0`, `rpmb_counter_increments == 0`, `passive_tx_bytes_emitted == 0`,
  `wbi_partition_writes == 0`, `emmc_persistent_program_commands == 0`, and `physical_device_writes == 0`.
- `P3` (`TWENTY_FOUR_PLUS_FIRMWARE_LAB_AUDITORS`):
  Verifies `>= 24` `fx3_firmware_lab` auditors (`Phases 1..126`), forward-compatible with Phase 131+ auditors
  (`passed_auditor_count >= 24` and `passed_auditor_count == auditor_count`), including #1..#20 plus
  #21 (`hdr_hlg_bt2100_and_display_assist_audit`, Phase 111), #22 (`hdmi_raw_prores_breathing_and_mishoe_clock_audit`,
  Phase 116), #23 (`usb_uvc_uac_srt_and_crsdk_ptp_audit`, Phase 120), and #24 (`mxf_mp4_essence_ptpv2_and_tally_umd_audit`,
  Phase 126).
- `P4` (`TWENTY_ONE_PLUS_STAGE_VM_COEMULATION`):
  Verifies `>= 21` `outputs/fx3-vm` heterogeneous AArch64 AP + ARM32 Thumb-2 Stock-CP co-emulation stages
  (`Phases 33..121`), forward-compatible with Stage 22+ (`passed_stage_count >= 21` and
  `passed_stage_count == stage_count`), including Stages 1..18 plus Stage 19 (`stage19_phase112_hdr_hlg_fiz_gimbal`),
  Stage 20 (`stage20_proresraw_breathing_mishoe_hil`), and Stage 21 (`stage21_uvc_srt_crsdk_usbpd_hil`),
  verifying `wf12_00342260_hits == 0` and `emmc_flash_mutation_bytes == 0`.
- `P5` (`REAL_KERNEL_R14_R17_R19_R20_TO_R24_UI_CLOSURES`):
  Verifies Round 14 (`18/18` 4-language x 3-surface pairs `> 0`), Round 17 (`10/10` Status Check `45/45` pairs `> 0` +
  wrap-around + WF-12), Round 19 (`11/11` Full-Menu L1 `55/55` pairs `> 0` + wrap-around + ZH-TW WF-12), PLUS the five
  4-language (`EN/JA/ZH-CN/ZH-TW`) `12/12` dual-surface closures in Rounds 20 (`Network` + WF-12), 21 (`Audio`),
  22 (`Paint/Look` & `Camera`), 23 (`Monitoring`), and 24 (`Project`) -> `60/60` multilingual pairs strictly `> 0`
  on unmodified FX3 `7.02` kernel (`4.9.337-scel+`, `nop_count == 0`, `crashes == 0`, `13/13` Stage-B SHA-256).
- `P6` (`POST_TRIAL_H0_VS_H2_IMMUTABILITY_AND_HARDWARE_LOCK_PROOF`):
  Verifies Dossier v3 (`stage_b_release_dossier_v3`), Capstone 22-Gate (`stage_b_capstone_22gate_v1`),
  Milestone 90 (`stage_b_milestone90_master_gate_v1`), Milestone 110 (`stage_b_milestone110_master_gate_v1`),
  and `H0 == H2` 16-surface bit-for-bit post-trial immutability (`drifted_surface_count == 0`, `c2pa_rq_lic_intact == True`,
  `spacc_cnflasha_untouched == True`, `10/10` tamper scenarios) plus global hardware-lock invariants.

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

from fx3_firmware_lab.hdmi_raw_prores_breathing_and_mishoe_clock_auditor import (  # noqa: E402
    analyze_hdmi_raw_prores_breathing_and_mishoe_clock,
    hdmi_raw_prores_breathing_and_mishoe_clock_report_to_dict,
)
from fx3_firmware_lab.hdr_hlg_bt2100_and_display_assist_auditor import (  # noqa: E402
    analyze_hdr_hlg_bt2100_and_display_assist,
    hdr_hlg_bt2100_and_display_assist_report_to_dict,
)
from fx3_firmware_lab.mxf_mp4_essence_ptpv2_and_tally_umd_auditor import (  # noqa: E402
    analyze_mxf_mp4_essence_ptpv2_and_tally_umd,
    mxf_mp4_essence_ptpv2_and_tally_umd_report_to_dict,
)
from fx3_firmware_lab.usb_uvc_uac_srt_and_crsdk_ptp_auditor import (  # noqa: E402
    analyze_usb_uvc_uac_srt_and_crsdk_ptp,
    usb_uvc_uac_srt_and_crsdk_ptp_report_to_dict,
)
from fx3_recovery import (  # noqa: E402
    run_ab_bank_and_interrupted_ota_suite,
    run_bootrom_usb_and_emmc_bootpart_suite,
    run_squashfs_and_hibdrv_wbi_suite,
)
from fx3_safety.monsoon_mishoe_cagetwist_and_40gate_guard import (  # noqa: E402
    evaluate_40gate_preflight,
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
    _build_clean_room_stage_b_manifest_items,
    _worker_domain_2,
)
from .stage_b_milestone90_master_gate import MILESTONE90_SCHEMA_VERSION  # noqa: E402
from .stage_b_milestone110_master_gate import (  # noqa: E402
    FIRMWARE_LAB_20_AUDITOR_KEYS,
    MILESTONE110_SCHEMA_VERSION,
    RECOVERY_10_PILLAR_IDS,
    ROUND17_RUN_SPECS,
    ROUND19_RUN_SPECS,
    VM_COEMULATION_18_STAGE_KEYS,
    Milestone110FaultInjection,
    _clean_room_faithful_block,
    _clean_room_languages_block,
    _evaluate_pillar_2 as _eval_m110_p2,
    _evaluate_pillar_3 as _eval_m110_p3,
    _evaluate_pillar_4 as _eval_m110_p4,
    _evaluate_pillar_5 as _eval_m110_p5,
    _fault_to_worker_dict as _m110_fault_to_worker_dict,
    _verify_stage_b_manifest_and_faithful,
    _worker_pillar_3_group as _m110_worker_pillar_3_group,
    _worker_pillar_4,
    _worker_recovery_master,
    _worker_recovery_p8_p9_p10,
)
from .stage_b_post_trial_auditor import _read_file_o_rdonly  # noqa: E402
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402
from .stage_b_release_dossier_v3 import (  # noqa: E402
    DOSSIER_V3_SCHEMA_VERSION,
    ROUND14_4LANG_PAIRS,
    StageBReleaseDossierV3FaultInjection,
    _evaluate_pillar_f,
    _worker_pillar_b,
    _worker_pillar_f,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

STAGE_B_MILESTONE130_SCHEMA: str = "stage_b_milestone130_master_gate_v1"
MILESTONE130_SCHEMA_VERSION: str = STAGE_B_MILESTONE130_SCHEMA
SCHEMA_VERSION: str = STAGE_B_MILESTONE130_SCHEMA
PHASE_130_VERSION: str = "130.0.0"

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

STATUS_MILESTONE_READY: str = "MILESTONE_130_SIMULATION_READY"
STATUS_FAIL_CLOSED: str = "FAIL_CLOSED"

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_40GATE_MASTER_PREFLIGHT"),
    ("P2", "THIRTEEN_PLUS_PILLAR_RECOVERY_MASTER_SUITE"),
    ("P3", "TWENTY_FOUR_PLUS_FIRMWARE_LAB_AUDITORS"),
    ("P4", "TWENTY_ONE_PLUS_STAGE_VM_COEMULATION"),
    ("P5", "REAL_KERNEL_R14_R17_R19_R20_TO_R24_UI_CLOSURES"),
    ("P6", "POST_TRIAL_H0_VS_H2_IMMUTABILITY_AND_HARDWARE_LOCK_PROOF"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)

RECOVERY_13_PILLAR_IDS: Tuple[str, ...] = (
    *RECOVERY_10_PILLAR_IDS,
    "ab_bank_and_interrupted_ota_verifier",
    "squashfs_and_hibdrv_wbi_verifier",
    "bootrom_usb_and_emmc_bootpart_verifier",
)

FIRMWARE_LAB_24_AUDITOR_KEYS: Tuple[str, ...] = (
    *FIRMWARE_LAB_20_AUDITOR_KEYS,
    "hdr_hlg_bt2100_and_display_assist_audit",
    "hdmi_raw_prores_breathing_and_mishoe_clock_audit",
    "usb_uvc_uac_srt_and_crsdk_ptp_audit",
    "mxf_mp4_essence_ptpv2_and_tally_umd_audit",
)

VM_COEMULATION_21_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_18_STAGE_KEYS,
    "stage19_phase112_hdr_hlg_fiz_gimbal",
    "stage20_proresraw_breathing_mishoe_hil",
    "stage21_uvc_srt_crsdk_usbpd_hil",
)

ROUND20_24_4LANG_PAIR_KEYS: Tuple[str, ...] = (
    "english_vs_japanese",
    "english_vs_schinese",
    "english_vs_tchinese",
    "japanese_vs_schinese",
    "japanese_vs_tchinese",
    "schinese_vs_tchinese",
)


@dataclass(frozen=True)
class RoundClosureSpec:
    """Declarative specification for each 4-language 12/12 dual-surface empirical round (R20..R24)."""

    round_num: int
    round_key: str
    summary_relpath: str
    expected_schema: str
    audit_key: str
    green_bool_key: str
    pairs_bool_key: str
    menu_pairwise_key: str
    tab_pairwise_key: str
    matrix_key: str
    run_specs: Tuple[Tuple[str, str, str], ...]


ROUND20_SPEC = RoundClosureSpec(
    round_num=20,
    round_key="round20",
    summary_relpath="reports/2026-11-14-round20-fx6-on-fx3-network-4lang-wf12-closure/summary.json",
    expected_schema="fx6-on-fx3-round20-network-4lang-wf12-closure-v1",
    audit_key="r20_network_4lang_wf12_closure_audit",
    green_bool_key="all_8_cells_wf12_immune",
    pairs_bool_key="all_12_network_pairs_strictly_positive",
    menu_pairwise_key="network_3layer_menu_4lang_pairwise",
    tab_pairwise_key="status_tab9_network_4lang_pairwise",
    matrix_key="wf12_00342260_8cell_immunity_matrix",
    run_specs=(
        ("r20a_menu_3layer_network_english", "0x11", "english"),
        ("r20b_menu_3layer_network_japanese", "0x11", "japanese"),
        ("r20c_status_tab9_network_english", "0x37", "english"),
        ("r20d_status_tab9_network_japanese", "0x37", "japanese"),
        ("r20e_status_tab9_network_tchinese", "0x37", "tchinese"),
    ),
)

ROUND21_SPEC = RoundClosureSpec(
    round_num=21,
    round_key="round21",
    summary_relpath="reports/2026-11-14-round21-fx6-on-fx3-audio-4lang-dualsurface-closure/summary.json",
    expected_schema="fx6-on-fx3-round21-audio-4lang-dualsurface-closure-v1",
    audit_key="r21_audio_4lang_dualsurface_audit",
    green_bool_key="all_8_cells_stage_b_green",
    pairs_bool_key="all_12_audio_pairs_strictly_positive",
    menu_pairwise_key="audio_3layer_menu_4lang_pairwise",
    tab_pairwise_key="status_tab3_audio_4lang_pairwise",
    matrix_key="audio_8cell_matrix",
    run_specs=(
        ("r21a_menu_3layer_audio_english", "0x11", "english"),
        ("r21b_menu_3layer_audio_japanese", "0x11", "japanese"),
        ("r21c_menu_3layer_audio_tchinese", "0x11", "tchinese"),
        ("r21d_status_tab3_audio_english", "0x31", "english"),
        ("r21e_status_tab3_audio_japanese", "0x31", "japanese"),
        ("r21f_status_tab3_audio_tchinese", "0x31", "tchinese"),
    ),
)

ROUND22_SPEC = RoundClosureSpec(
    round_num=22,
    round_key="round22",
    summary_relpath="reports/2026-11-14-round22-fx6-on-fx3-paintlook-camera-4lang-closure/summary.json",
    expected_schema="fx6-on-fx3-round22-paintlook-camera-4lang-closure-v1",
    audit_key="r22_paintlook_camtab2_4lang_dualsurface_audit",
    green_bool_key="all_8_cells_stage_b_green",
    pairs_bool_key="all_12_paintlook_camtab2_pairs_strictly_positive",
    menu_pairwise_key="paintlook_3layer_menu_4lang_pairwise",
    tab_pairwise_key="status_tab2_camera_4lang_pairwise",
    matrix_key="paintlook_camtab2_8cell_matrix",
    run_specs=(
        ("r22a_menu_3layer_paintlook_english", "0x11", "english"),
        ("r22b_menu_3layer_paintlook_japanese", "0x11", "japanese"),
        ("r22c_menu_3layer_paintlook_tchinese", "0x11", "tchinese"),
        ("r22d_status_tab2_camera_english", "0x30", "english"),
        ("r22e_status_tab2_camera_tchinese", "0x30", "tchinese"),
    ),
)

ROUND23_SPEC = RoundClosureSpec(
    round_num=23,
    round_key="round23",
    summary_relpath="reports/2026-11-14-round23-fx6-on-fx3-monitoring-4lang-dualsurface-closure/summary.json",
    expected_schema="fx6-on-fx3-round23-monitoring-tab5-4lang-dualsurface-closure-v1",
    audit_key="r23_monitoring_tab5_4lang_dualsurface_audit",
    green_bool_key="all_8_cells_stage_b_green",
    pairs_bool_key="all_12_monitoring_tab5_pairs_strictly_positive",
    menu_pairwise_key="monitoring_3layer_menu_4lang_pairwise",
    tab_pairwise_key="status_tab5_monitoring_4lang_pairwise",
    matrix_key="monitoring_tab5_8cell_matrix",
    run_specs=(
        ("r23a_menu_3layer_monitoring_english", "0x11", "english"),
        ("r23b_menu_3layer_monitoring_tchinese", "0x11", "tchinese"),
        ("r23c_status_tab5_monitoring_english", "0x33", "english"),
        ("r23d_status_tab5_monitoring_japanese", "0x33", "japanese"),
        ("r23e_status_tab5_monitoring_tchinese", "0x33", "tchinese"),
    ),
)

ROUND24_SPEC = RoundClosureSpec(
    round_num=24,
    round_key="round24",
    summary_relpath="reports/2026-11-14-round24-fx6-on-fx3-project-4lang-dualsurface-closure/summary.json",
    expected_schema="fx6-on-fx3-round24-project-tab4-4lang-dualsurface-closure-v1",
    audit_key="r24_project_tab4_4lang_dualsurface_audit",
    green_bool_key="all_8_cells_stage_b_green",
    pairs_bool_key="all_12_project_tab4_pairs_strictly_positive",
    menu_pairwise_key="project_3layer_menu_4lang_pairwise",
    tab_pairwise_key="status_tab4_project_4lang_pairwise",
    matrix_key="project_tab4_8cell_matrix",
    run_specs=(
        ("r24a_menu_3layer_project_english", "0x11", "english"),
        ("r24b_menu_3layer_project_japanese", "0x11", "japanese"),
        ("r24c_menu_3layer_project_tchinese", "0x11", "tchinese"),
        ("r24d_status_tab4_project_english", "0x32", "english"),
        ("r24e_status_tab4_project_japanese", "0x32", "japanese"),
        ("r24f_status_tab4_project_tchinese", "0x32", "tchinese"),
    ),
)

ROUND20_TO_24_SPECS: Tuple[RoundClosureSpec, ...] = (
    ROUND20_SPEC,
    ROUND21_SPEC,
    ROUND22_SPEC,
    ROUND23_SPEC,
    ROUND24_SPEC,
)
ROUND20_TO_24_TOTAL_RUNS: int = sum(len(s.run_specs) for s in ROUND20_TO_24_SPECS)

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Milestone130FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 faults (40-gate preflight, G21..G40)
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

    # P2 faults (>=13-pillar recovery: P1..P10 + P11 A/B OTA, P12 SquashFS/hibdrv WBI2, P13 BootROM/BOOT0)
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

    # P3 faults (>= 24 fx3_firmware_lab auditors, incl. #21..#24)
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

    # P4 faults (>= 21-stage VM co-emulation, Stages 1..21)
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

    # P5 faults (R14 18/18 + R17 45/45 + R19 55/55 + R20..R24 60/60)
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
    p5_r20_to_r24_nop_count: int = 0
    p5_r20_to_r24_crashes: int = 0
    p5_r20_to_r24_zero_round: Optional[str] = None
    p5_r20_to_r24_zero_pair_name: Optional[str] = None
    p5_r20_to_r24_wf12_immune_override: Optional[int] = None
    p5_r20_to_r24_manifest_count_override: Optional[int] = None

    # P6 faults (Dossier v3 + Capstone 22 + M90 + M110 + H0-vs-H2 16-surface drift / tamper)
    p6_drift_surface: Optional[str] = None
    p6_tamper_negative_control: bool = False


@dataclass(frozen=True)
class Milestone130PillarResult:
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
class StageBMilestone130MasterGateReport:
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
    pillars: Tuple[Milestone130PillarResult, ...]
    gate40_offline_verified: int
    gate40_simulated_verified: int
    recovery_pillar_count: int
    recovery_pillars_passed: int
    firmware_lab_auditor_count: int
    firmware_lab_auditors_passed: int
    vm_coemulation_stage_count: int
    vm_coemulation_stages_passed: int
    vm_wf12_00342260_hits: int
    vm_emmc_flash_mutation_bytes: int
    round14_positive_pairs: int
    round17_tabs_verified: int
    round17_pairwise_deltas_verified: int
    round17_runs_verified: int
    round19_categories_verified: int
    round19_pairwise_deltas_verified: int
    round19_runs_verified: int
    round20_to_24_rounds_verified: int
    round20_to_24_positive_pairs: int
    round20_to_24_runs_verified: int
    real_kernel_nop_count: int
    real_kernel_crashes: int
    h0_surface_count: int
    drifted_surface_count: int
    c2pa_rq_lic_intact: bool
    spacc_cnflasha_untouched: bool
    errors: Tuple[str, ...]
    milestone130_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class StageBMilestone130VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone130_sha256: str
    observed_milestone130_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic Digest & O_RDONLY Round 20..24 Loaders
# ---------------------------------------------------------------------------


def compute_milestone130_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `StageBMilestone130MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone130_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def _load_round20_to_24_summary(
    spec: RoundClosureSpec,
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], str]:
    """Load a Round 20..24 summary strictly via `os.O_RDONLY` when present, else clean-room synthetic."""
    summary_path = repo_root / spec.summary_relpath
    if summary_path.is_file() and not summary_path.is_symlink():
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if isinstance(obj, dict):
            return obj, "REPO_SUMMARY_O_RDONLY"
    if not use_clean_room:
        raise FileNotFoundError(f"Missing {spec.round_key} summary report: {summary_path}")

    manifest_items = _build_clean_room_stage_b_manifest_items()
    faithful = _clean_room_faithful_block()
    runs_block: Dict[str, Any] = {}
    for run_id, target_sid, lang_name in spec.run_specs:
        runs_block[run_id] = {
            "run_id": run_id.replace("_", "-"),
            "round": spec.round_num,
            "lang": lang_name,
            "target_sid": target_sid,
            "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
            "nop_count": 0,
            "crashes": 0,
            "faithful_invariants": dict(faithful),
            "stage_b": {
                "stage": "B",
                f"r{spec.round_num}_enabled": True,
                "lang": lang_name,
                "manifest_count": 13,
                "manifest_items": list(manifest_items),
            },
        }

    def _mk_pairs(base_px: int) -> Dict[str, Any]:
        return {
            pk: {
                "diff_pixels": base_px + idx * 713,
                "strictly_positive": True,
            }
            for idx, pk in enumerate(ROUND20_24_4LANG_PAIR_KEYS)
        }

    matrix_rows: List[Dict[str, Any]] = []
    for surf in ("menu_3layer", "status_tab"):
        for lang_name in ("english", "japanese", "schinese", "tchinese"):
            matrix_rows.append(
                {
                    "surface": surf,
                    "lang": lang_name,
                    "p12_wlan": 1,
                    "wf12_00342260_immune": 1,
                    "airplane_bk4_hits": 0,
                    "nop_count": 0,
                    "crashes": 0,
                    "gpe_fb": 0,
                    "stage_b_manifest_count": 13,
                }
            )

    synthetic = {
        "schema": spec.expected_schema,
        "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
        "languages": _clean_room_languages_block(),
        "runs": runs_block,
        spec.audit_key: {
            "total_surfaces": 2,
            "total_languages": 4,
            "total_matrix_cells": 8,
            "total_multilingual_pairs": 12,
            spec.green_bool_key: True,
            spec.pairs_bool_key: True,
            spec.menu_pairwise_key: {"pairs": _mk_pairs(12000)},
            spec.tab_pairwise_key: {"pairs": _mk_pairs(28000)},
            spec.matrix_key: matrix_rows,
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

    rep_off = evaluate_40gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=False,
        **kwargs,
    )
    rep_sim = evaluate_40gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=True,
        **kwargs,
    )

    m38 = rep_sim.master_38_report
    m36 = m38.get("master_36_report", {})
    m34 = m36.get("master_34_report", {})
    m32 = m34.get("master_32_report", {})

    g33 = m34.get("g33_result", {})
    g34 = m34.get("g34_result", {})
    g35 = m36.get("g35_result", {})
    g36 = m36.get("g36_result", {})
    g37 = m38.get("g37_result", {})
    g38 = m38.get("g38_result", {})
    g39 = rep_sim.g39_result
    g40 = rep_sim.g40_result

    return {
        "schema": rep_sim.schema,
        "verification_mode": rep_sim.verification_mode,
        "total_gates": int(rep_sim.summary.get("total_gates", len(rep_sim.gates))),
        "offline_verified_gates": int(rep_off.summary.get("verified_gates", 0)),
        "offline_37_gates_verified": bool(rep_off.offline_37_gates_verified),
        "offline_all_40_gates_verified": bool(rep_off.all_40_gates_verified),
        "offline_ready_for_hw": bool(rep_off.overall_ready_for_hardware_attach),
        "sim_verified_gates": int(rep_sim.summary.get("verified_gates", 0)),
        "sim_all_40_gates_verified": bool(rep_sim.all_40_gates_verified),
        "sim_dry_run_rehearsal_only": bool(rep_sim.dry_run_rehearsal_only),
        "sim_ready_for_hw": bool(rep_sim.overall_ready_for_hardware_attach),
        "g13_to_g40_all_passed": bool(rep_sim.g13_to_g40_all_passed),
        "g39_to_g40_all_passed": bool(rep_sim.g39_to_g40_all_passed),
        "m32_g13_to_g32_all_passed": bool(m32.get("g13_to_g32_all_passed", False)),
        "m32_g31_to_g32_all_passed": bool(m32.get("g31_to_g32_all_passed", False)),
        "g33_passed": bool(g33.get("valid", False)),
        "g33_status": str(g33.get("status", "")),
        "g33_guard": dict(g33.get("saltspray_haze_firewall", {})),
        "g34_passed": bool(g34.get("valid", False)),
        "g34_status": str(g34.get("status", "")),
        "g34_guard": dict(g34.get("followfocus_gimbal_guard", {})),
        "g35_passed": bool(g35.get("valid", False)),
        "g35_status": str(g35.get("status", "")),
        "g35_guard": dict(g35.get("hdmi_aoc_5v_firewall", {})),
        "g36_passed": bool(g36.get("valid", False)),
        "g36_status": str(g36.get("status", "")),
        "g36_guard": dict(g36.get("cfexpress_vpg_door_guard", {})),
        "g37_passed": bool(g37.get("valid", False)),
        "g37_status": str(g37.get("status", "")),
        "g37_guard": dict(g37.get("usbpd_uvc_firewall", {})),
        "g38_passed": bool(g38.get("valid", False)),
        "g38_status": str(g38.get("status", "")),
        "g38_guard": dict(g38.get("multiterminal_ptp_guard", {})),
        "g39_passed": bool(g39.get("valid", False)),
        "g39_status": str(g39.get("status", "")),
        "g39_guard": dict(g39.get("monsoon_mishoe_firewall", {})),
        "g40_passed": bool(g40.get("valid", False)),
        "g40_status": str(g40.get("status", "")),
        "g40_guard": dict(g40.get("cagetwist_xlrh1_guard", {})),
        "persistent_emmc_writes_authorized": bool(rep_sim.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep_sim.persistent_write_release),
        "sim_errors": list(rep_sim.errors),
        "g33_to_g40_errors": [
            *list(g33.get("errors", [])),
            *list(g34.get("errors", [])),
            *list(g35.get("errors", [])),
            *list(g36.get("errors", [])),
            *list(g37.get("errors", [])),
            *list(g38.get("errors", [])),
            *list(g39.get("errors", [])),
            *list(g40.get("errors", [])),
        ],
    }


def _worker_recovery_p11_to_p13(use_clean_room: bool) -> Dict[str, Any]:
    p11 = run_ab_bank_and_interrupted_ota_suite(force_clean_room=use_clean_room)
    p12 = run_squashfs_and_hibdrv_wbi_suite(force_clean_room=use_clean_room)
    p13 = run_bootrom_usb_and_emmc_bootpart_suite(force_clean_room=use_clean_room)
    return {
        "p11_ab_ota": {
            "schema": p11.schema,
            "all_passed": bool(p11.all_passed),
            "status": str(p11.status),
            "otp_fuse_touches": int(p11.otp_fuse_touches),
            "passive_tx_bytes_emitted": int(p11.passive_tx_bytes_emitted),
            "physical_device_writes": int(p11.physical_device_writes),
            "persistent_emmc_writes_authorized": bool(p11.persistent_emmc_writes_authorized),
            "allow_boot_partition_targeting": bool(p11.allow_boot_partition_targeting),
            "allow_destructive_fastboot": bool(p11.allow_destructive_fastboot),
            "suite_sha256": str(p11.suite_sha256),
            "errors": list(p11.errors),
        },
        "p12_squashfs_hibdrv_wbi": {
            "schema": p12.schema,
            "all_passed": bool(p12.all_passed),
            "status": str(p12.status),
            "otp_fuse_touches": int(p12.otp_fuse_touches),
            "passive_tx_bytes_emitted": int(p12.passive_tx_bytes_emitted),
            "physical_device_writes": int(p12.physical_device_writes),
            "wbi_partition_writes": int(p12.wbi_partition_writes),
            "persistent_emmc_writes_authorized": bool(p12.persistent_emmc_writes_authorized),
            "allow_boot_partition_targeting": bool(p12.allow_boot_partition_targeting),
            "allow_destructive_fastboot": bool(p12.allow_destructive_fastboot),
            "suite_sha256": str(p12.suite_sha256),
            "errors": list(p12.errors),
        },
        "p13_bootrom_bootpart": {
            "schema": p13.schema,
            "all_passed": bool(p13.all_passed),
            "status": str(p13.status),
            "otp_fuse_touches": int(p13.otp_fuse_touches),
            "passive_tx_bytes_emitted": int(p13.passive_tx_bytes_emitted),
            "physical_device_writes": int(p13.physical_device_writes),
            "emmc_persistent_program_commands": int(p13.emmc_persistent_program_commands),
            "persistent_emmc_writes_authorized": bool(p13.persistent_emmc_writes_authorized),
            "allow_boot_partition_targeting": bool(p13.allow_boot_partition_targeting),
            "allow_destructive_fastboot": bool(p13.allow_destructive_fastboot),
            "suite_sha256": str(p13.suite_sha256),
            "errors": list(p13.errors),
        },
    }


def _worker_pillar_3_group(args: Tuple[str, bool]) -> Dict[str, Dict[str, Any]]:
    group, clean_room = args
    if group == "hdr_hlg":
        return {
            "hdr_hlg_bt2100_and_display_assist_audit": hdr_hlg_bt2100_and_display_assist_report_to_dict(
                analyze_hdr_hlg_bt2100_and_display_assist(clean_room=clean_room)
            )
        }
    if group == "prores_mishoe":
        return {
            "hdmi_raw_prores_breathing_and_mishoe_clock_audit": hdmi_raw_prores_breathing_and_mishoe_clock_report_to_dict(
                analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=clean_room)
            )
        }
    if group == "uvc_crsdk":
        return {
            "usb_uvc_uac_srt_and_crsdk_ptp_audit": usb_uvc_uac_srt_and_crsdk_ptp_report_to_dict(
                analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=clean_room)
            )
        }
    if group == "mxf_tally":
        return {
            "mxf_mp4_essence_ptpv2_and_tally_umd_audit": mxf_mp4_essence_ptpv2_and_tally_umd_report_to_dict(
                analyze_mxf_mp4_essence_ptpv2_and_tally_umd(clean_room=clean_room)
            )
        }
    return _m110_worker_pillar_3_group((group, clean_room))


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1 .. P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(raw_1: Mapping[str, Any]) -> Milestone130PillarResult:
    errors: List[str] = []
    total_gates = int(raw_1.get("total_gates", 0))
    if total_gates < 40:
        errors.append(f"p1: total_gates expected >= 40, got {total_gates}")
    if not raw_1["offline_37_gates_verified"] or raw_1["offline_verified_gates"] < 37:
        errors.append(
            f"p1: offline hardware-truth gates expected >= 37/{total_gates}, got {raw_1['offline_verified_gates']}/{total_gates}"
        )
    if raw_1["offline_all_40_gates_verified"] or raw_1["offline_ready_for_hw"]:
        errors.append("p1: offline mode must remain blocked for live hardware attach")
    if not raw_1["sim_all_40_gates_verified"] or raw_1["sim_verified_gates"] < 40:
        errors.append(
            f"p1: simulated rehearsal gates expected >= 40/{total_gates}, got {raw_1['sim_verified_gates']}/{total_gates}"
        )
    if not raw_1["sim_dry_run_rehearsal_only"] or raw_1["sim_ready_for_hw"]:
        errors.append("p1: simulated 40-gate rehearsal must keep overall_ready_for_hardware_attach=False")
    if (
        not raw_1["g13_to_g40_all_passed"]
        or not raw_1["g39_to_g40_all_passed"]
        or not raw_1["m32_g13_to_g32_all_passed"]
        or not raw_1["m32_g31_to_g32_all_passed"]
    ):
        errors.append("p1: G13..G40, G39..G40, or G13..G32 safety guard gate blocked")

    guard_checks = (
        ("g33", ("saltspray_duct_safe", "alkali_dust_filtration_safe", "glycol_haze_fouling_safe")),
        ("g34", ("hardstop_torque_safe", "rod_deflection_mesh_safe", "gimbal_cog_oscillation_safe")),
        ("g35", ("pin18_overcurrent_safe", "pin18_reverse_backfeed_safe", "hdmi_port_leverage_shear_safe")),
        ("g36", ("sustained_write_floor_safe", "nvme_thermal_throttle_safe", "door_open_flush_safe")),
        ("g37", ("usbc_trigger_cable_safe", "dual_power_crossfeed_safe", "uvc_thermal_saturation_safe")),
        ("g38", ("multiterminal_ltc_voltage_safe", "uart_1v8_rx_only_safe", "ptp_fw_flash_opcode_guard_safe")),
        ("g39", ("uncapped_mishoe_rain_safe", "gasketed_mishoe_accessory_safe", "side_port_flap_capillary_safe")),
        ("g40", ("xlr_h1_whip_shear_safe", "quarter20_thread_torque_safe", "asymmetric_cage_twist_ffd_safe")),
    )
    for gk, subkeys in guard_checks:
        if not raw_1.get(f"{gk}_passed", False):
            errors.append(f"p1: {gk.upper()} safety guard failed ({raw_1.get(f'{gk}_status', '')})")
        sub = raw_1.get(f"{gk}_guard", {})
        if not isinstance(sub, Mapping) or not bool(sub.get("valid", False)):
            errors.append(f"p1: {gk.upper()} inner firewall/guard invalid")
        elif any(not bool(sub.get(sk, False)) for sk in subkeys):
            errors.append(f"p1: {gk.upper()} sub-invariant failed")

    if raw_1["persistent_emmc_writes_authorized"] or raw_1["persistent_write_release"]:
        errors.append("p1: hard-locked persistent_emmc_writes_authorized / persistent_write_release breached")
    for err in raw_1["sim_errors"]:
        errors.append(f"p1_40gate: {err}")
    for err in raw_1["g33_to_g40_errors"]:
        errors.append(f"p1_g33_g40: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_1["schema"],
        "verification_mode": raw_1["verification_mode"],
        "total_gates": total_gates,
        "offline_verified_gates": raw_1["offline_verified_gates"],
        "offline_ready_for_hardware_attach": raw_1["offline_ready_for_hw"],
        "simulated_verified_gates": raw_1["sim_verified_gates"],
        "simulated_ready_for_hardware_attach": raw_1["sim_ready_for_hw"],
        "m32_g13_to_g32_all_passed": raw_1["m32_g13_to_g32_all_passed"],
        "g33_to_g38_all_passed": all(bool(raw_1.get(f"g{n}_passed", False)) for n in range(33, 39)),
        "g39_passed": raw_1["g39_passed"],
        "g39_status": raw_1["g39_status"],
        "g40_passed": raw_1["g40_passed"],
        "g40_status": raw_1["g40_status"],
        "g39_to_g40_all_passed": raw_1["g39_to_g40_all_passed"],
        "g13_to_g40_all_passed": raw_1["g13_to_g40_all_passed"],
        "persistent_emmc_writes_authorized": raw_1["persistent_emmc_writes_authorized"],
        "persistent_write_release": raw_1["persistent_write_release"],
    }
    return Milestone130PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_40GATE_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"40-Gate offline={raw_1['offline_verified_gates']}/{total_gates} "
            f"sim={raw_1['sim_verified_gates']}/{total_gates}, G33..G38={evidence['g33_to_g38_all_passed']}, "
            f"G39(Monsoon-MIShoe)={raw_1['g39_passed']}, G40(CageTwist-XLRH1)={raw_1['g40_passed']} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _to_m110_faults(faults: Milestone130FaultInjection) -> Milestone110FaultInjection:
    return Milestone110FaultInjection(
        p1_pl_cantilever_kwargs=faults.p1_pl_cantilever_kwargs,
        p1_dummy_battery_kwargs=faults.p1_dummy_battery_kwargs,
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
        p5_round14_nop_count=faults.p5_round14_nop_count,
        p5_round14_zero_pair=faults.p5_round14_zero_pair,
        p5_round17_nop_count=faults.p5_round17_nop_count,
        p5_round17_crashes=faults.p5_round17_crashes,
        p5_round17_zero_tab_pair=faults.p5_round17_zero_tab_pair,
        p5_round17_zero_wraparound=faults.p5_round17_zero_wraparound,
        p5_round17_manifest_count_override=faults.p5_round17_manifest_count_override,
        p5_round19_nop_count=faults.p5_round19_nop_count,
        p5_round19_crashes=faults.p5_round19_crashes,
        p5_round19_zero_cat_pair=faults.p5_round19_zero_cat_pair,
        p5_round19_zero_wraparound=faults.p5_round19_zero_wraparound,
        p5_round19_zero_tchinese_delta=faults.p5_round19_zero_tchinese_delta,
        p5_round19_wf12_immune_override=faults.p5_round19_wf12_immune_override,
        p5_round19_manifest_count_override=faults.p5_round19_manifest_count_override,
        p6_drift_surface=faults.p6_drift_surface,
        p6_tamper_negative_control=faults.p6_tamper_negative_control,
    )


def _evaluate_pillar_2(
    raw_master: Mapping[str, Any],
    raw_p8_p10: Mapping[str, Any],
    raw_p11_p13: Mapping[str, Any],
    raw_antirollback: Mapping[str, Any],
    raw_tier0_init2: Mapping[str, Any],
    faults: Milestone130FaultInjection,
) -> Tuple[Milestone130PillarResult, Dict[str, Any]]:
    m110_p2, meta_10 = _eval_m110_p2(
        raw_master,
        raw_p8_p10,
        raw_antirollback,
        raw_tier0_init2,
        _to_m110_faults(faults),
    )
    errors: List[str] = list(m110_p2.errors)
    pillar_statuses: Dict[str, bool] = dict(m110_p2.evidence["pillar_statuses"])

    p11 = raw_p11_p13.get("p11_ab_ota", {})
    p12 = raw_p11_p13.get("p12_squashfs_hibdrv_wbi", {})
    p13 = raw_p11_p13.get("p13_bootrom_bootpart", {})

    p11_ok = bool(p11.get("all_passed")) and not faults.p2_inject_ab_ota_fault
    p12_ok = bool(p12.get("all_passed")) and not faults.p2_inject_squashfs_hibdrv_fault
    p13_ok = bool(p13.get("all_passed")) and not faults.p2_inject_bootrom_bootpart_fault

    if not p11_ok:
        errors.append("p2_p11: dual-bank A/B & interrupted BODYDATA.DAT OTA triage verifier failed")
    if not p12_ok:
        errors.append("p2_p12: SquashFS 4.0 & Warp-Boot hibdrv WBI2 triage verifier failed")
    if not p13_ok:
        errors.append("p2_p13: Mask-BootROM USB & JEDEC eMMC BOOT0/BOOT1 triage verifier failed")

    for tag, obj in (("p2_p11", p11), ("p2_p12", p12), ("p2_p13", p13)):
        if (
            obj.get("persistent_emmc_writes_authorized") is not False
            or obj.get("allow_boot_partition_targeting") is not False
            or obj.get("allow_destructive_fastboot") is not False
        ):
            errors.append(f"{tag}: hard-locked zero-write/zero-bootpart/zero-fastboot flag breached")

    otp_touches = (
        int(meta_10["otp_fuse_touches"])
        + int(p11.get("otp_fuse_touches", 0))
        + int(p12.get("otp_fuse_touches", 0))
        + int(p13.get("otp_fuse_touches", 0))
    )
    rpmb_incs = int(meta_10["rpmb_counter_increments"])
    passive_tx = (
        int(meta_10["passive_tx_bytes_emitted"])
        + int(p11.get("passive_tx_bytes_emitted", 0))
        + int(p12.get("passive_tx_bytes_emitted", 0))
        + int(p13.get("passive_tx_bytes_emitted", 0))
    )
    phys_writes = (
        int(m110_p2.evidence.get("physical_device_writes", 0))
        + int(p11.get("physical_device_writes", 0))
        + int(p12.get("physical_device_writes", 0))
        + int(p13.get("physical_device_writes", 0))
    )
    wbi_writes = int(p12.get("wbi_partition_writes", -1))
    bootpart_cmds = int(p13.get("emmc_persistent_program_commands", -1))

    if otp_touches != 0:
        errors.append(f"p2: otp_fuse_touches={otp_touches} != 0")
    if passive_tx != 0:
        errors.append(f"p2: passive_tx_bytes_emitted={passive_tx} != 0")
    if phys_writes != 0 or wbi_writes != 0 or bootpart_cmds != 0:
        errors.append(
            f"p2: physical_writes={phys_writes}, wbi_writes={wbi_writes}, bootpart_cmds={bootpart_cmds} must all be 0"
        )

    pillar_statuses["ab_bank_and_interrupted_ota_verifier"] = p11_ok
    pillar_statuses["squashfs_and_hibdrv_wbi_verifier"] = p12_ok
    pillar_statuses["bootrom_usb_and_emmc_bootpart_verifier"] = p13_ok

    total_pillars = len(pillar_statuses)
    passed_pillars = sum(1 for v in pillar_statuses.values() if v)
    if total_pillars < 13 or passed_pillars < 13 or passed_pillars != total_pillars:
        errors.append(f"p2: recovery pillars expected >=13 and all passing, got {passed_pillars}/{total_pillars}")

    passed = len(errors) == 0
    evidence = dict(m110_p2.evidence)
    evidence.update(
        {
            "recovery_pillar_count": total_pillars,
            "recovery_pillars_passed": passed_pillars,
            "pillar_statuses": pillar_statuses,
            "otp_fuse_touches": otp_touches,
            "rpmb_counter_increments": rpmb_incs,
            "passive_tx_bytes_emitted": passive_tx,
            "physical_device_writes": phys_writes,
            "wbi_partition_writes": wbi_writes,
            "emmc_persistent_program_commands": bootpart_cmds,
            "p11_ab_ota_ok": p11_ok,
            "p12_squashfs_hibdrv_ok": p12_ok,
            "p13_bootrom_bootpart_ok": p13_ok,
            "p11_suite_sha256": p11.get("suite_sha256"),
            "p12_suite_sha256": p12.get("suite_sha256"),
            "p13_suite_sha256": p13.get("suite_sha256"),
        }
    )
    pillar = Milestone130PillarResult(
        pillar_id="P2",
        pillar_name="THIRTEEN_PLUS_PILLAR_RECOVERY_MASTER_SUITE",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Recovery {passed_pillars}/{total_pillars} pillars (Ph47..124; >=13 required), "
            f"UART S0..S6 {raw_master.get('uart_scenarios_passed')}/{raw_master.get('uart_scenarios_total')}, "
            f"OTP={otp_touches}, RPMB={rpmb_incs}, passive_tx={passive_tx}B {'PASS' if passed else 'FAIL_CLOSED'}"
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
    faults: Milestone130FaultInjection,
) -> Tuple[Milestone130PillarResult, Dict[str, Any]]:
    m110_p3, meta_20 = _eval_m110_p3(auditors, _to_m110_faults(faults))
    errors: List[str] = list(m110_p3.errors)
    auditor_statuses: Dict[str, bool] = dict(m110_p3.evidence["auditor_statuses"])
    auditor_sha256s: Dict[str, Optional[str]] = dict(m110_p3.evidence["auditor_sha256s"])

    # #21: HDR / HLG BT.2100 & Display Assist
    a21 = auditors.get("hdr_hlg_bt2100_and_display_assist_audit", {})
    a21_ok = isinstance(a21, Mapping) and bool(a21.get("all_checks_passed"))
    a21_p4 = a21.get("pillar_4_nrtm_smpte_ul_immutability", {})
    a21_cal = int(a21_p4.get("calibration_mutation_bytes", -1)) + int(faults.p3_hdr_nrtm_mutation_bytes)
    a21_emmc = int(a21_p4.get("emmc_mutation_bytes", -1))
    if not a21_ok or a21_cal != 0 or a21_emmc != 0 or a21_p4.get("persistent_emmc_writes_authorized") is not False:
        errors.append(f"p3: #21 hdr_hlg_bt2100_and_display_assist_audit failed (cal={a21_cal}, emmc={a21_emmc})")

    # #22: HDMI RAW / ProRes RAW / Breathing & MI-Shoe Clock
    a22 = auditors.get("hdmi_raw_prores_breathing_and_mishoe_clock_audit", {})
    a22_ok = isinstance(a22, Mapping) and bool(a22.get("all_checks_passed"))
    a22_p4 = a22.get("pillar_4_ob_clamp_preservation", {})
    a22_cal = int(a22_p4.get("ob_clamp_calibration_mutation_bytes", -1)) + int(faults.p3_ob_clamp_mutation_bytes)
    a22_emmc = int(a22_p4.get("emmc_mutation_bytes", -1))
    if not a22_ok or a22_cal != 0 or a22_emmc != 0 or a22_p4.get("persistent_emmc_writes_authorized") is not False:
        errors.append(f"p3: #22 hdmi_raw_prores_breathing_and_mishoe_clock_audit failed (ob_cal={a22_cal}, emmc={a22_emmc})")

    # #23: USB UVC/UAC, Wired SRT/RTMPS & CRSDK PTP Firewall
    a23 = auditors.get("usb_uvc_uac_srt_and_crsdk_ptp_audit", {})
    a23_ok = isinstance(a23, Mapping) and bool(a23.get("all_checks_passed"))
    a23_p4 = a23.get("pillar_4_zero_mutation_emmc_preservation", {})
    a23_cal = int(a23_p4.get("calibration_mutation_bytes", -1))
    a23_emmc = int(a23_p4.get("emmc_mutation_bytes", -1)) + int(faults.p3_uvc_crsdk_emmc_mutation_bytes)
    if not a23_ok or a23_cal != 0 or a23_emmc != 0 or a23_p4.get("persistent_emmc_writes_authorized") is not False:
        errors.append(f"p3: #23 usb_uvc_uac_srt_and_crsdk_ptp_audit failed (cal={a23_cal}, emmc={a23_emmc})")

    # #24: MXF/MP4 Essence, PTPv2/LTC Phase Sync & TSL UMD Tally
    a24 = auditors.get("mxf_mp4_essence_ptpv2_and_tally_umd_audit", {})
    a24_ok = isinstance(a24, Mapping) and bool(a24.get("all_checks_passed"))
    a24_pd = a24.get("pillar_d_zero_mutation_emmc_guard", {})
    a24_cal = int(a24_pd.get("calibration_mutation_bytes", -1))
    a24_emmc = int(a24_pd.get("emmc_mutation_bytes", -1)) + int(faults.p3_mxf_tally_emmc_mutation_bytes)
    if not a24_ok or a24_cal != 0 or a24_emmc != 0 or a24_pd.get("persistent_emmc_writes_authorized") is not False:
        errors.append(f"p3: #24 mxf_mp4_essence_ptpv2_and_tally_umd_audit failed (cal={a24_cal}, emmc={a24_emmc})")

    for key, obj in (
        ("hdr_hlg_bt2100_and_display_assist_audit", a21),
        ("hdmi_raw_prores_breathing_and_mishoe_clock_audit", a22),
        ("usb_uvc_uac_srt_and_crsdk_ptp_audit", a23),
        ("mxf_mp4_essence_ptpv2_and_tally_umd_audit", a24),
    ):
        auditor_statuses[key] = isinstance(obj, Mapping) and bool(obj.get("all_checks_passed"))
        auditor_sha256s[key] = (
            str(obj.get("report_sha256")) if isinstance(obj, Mapping) and obj.get("report_sha256") else None
        )

    total_count = len(auditor_statuses)
    passed_count = sum(1 for v in auditor_statuses.values() if v)
    total_cal_mut = max(
        int(meta_20["calibration_mutation_bytes"]),
        max(0, a21_cal),
        max(0, a22_cal),
        max(0, a23_cal),
        max(0, a24_cal),
    )

    if total_count < 24 or passed_count < 24 or passed_count != total_count:
        errors.append(
            f"p3: expected >= 24 auditors and all passing, got {passed_count}/{total_count}"
        )

    passed = len(errors) == 0 and total_cal_mut == 0
    evidence = dict(m110_p3.evidence)
    evidence.update(
        {
            "auditor_count": total_count,
            "passed_auditor_count": passed_count,
            "auditor_statuses": auditor_statuses,
            "auditor_sha256s": auditor_sha256s,
            "phase111_hdr_hlg_ok": a21_ok,
            "phase116_prores_breathing_ok": a22_ok,
            "phase120_uvc_srt_crsdk_ok": a23_ok,
            "phase126_mxf_ptpv2_tally_ok": a24_ok,
            "calibration_mutation_bytes": total_cal_mut,
        }
    )
    pillar = Milestone130PillarResult(
        pillar_id="P3",
        pillar_name="TWENTY_FOUR_PLUS_FIRMWARE_LAB_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {passed_count}/{total_count} auditors (>=24 required; incl. #21..#24), "
            f"cal_mut={total_cal_mut}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "auditor_count": total_count,
        "passed_count": passed_count,
        "calibration_mutation_bytes": total_cal_mut,
        "bk4_persistent_nvram_writes": int(meta_20["bk4_persistent_nvram_writes"]),
    }
    return pillar, meta


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: Milestone130FaultInjection,
) -> Tuple[Milestone130PillarResult, Dict[str, Any]]:
    m110_p4, meta_18 = _eval_m110_p4(vm_rep, _to_m110_faults(faults))
    errors: List[str] = list(m110_p4.errors)
    stage_statuses: Dict[str, bool] = dict(m110_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_21_STAGE_KEYS[18:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if not ok:
            errors.append(f"p4: VM co-emulation {skey} failed")

    # Stage 19: Phase 112 HDR HLG + Gamma Display Assist + FIZ + Gimbal + Duct/Salt HIL
    s19 = vm_rep.get("stage19_phase112_hdr_hlg_fiz_gimbal", {})
    s19_fiz = int(s19.get("fiz_gear_strip_events", -1)) + int(faults.p4_stage19_fiz_gear_strip_events)
    s19_burn = int(s19.get("display_assist_burn_in_frames", -1)) + int(
        faults.p4_stage19_display_assist_burn_in_frames
    )
    if (
        int(s19.get("nop_count", -1)) != 0
        or int(s19.get("cp_mutation_bytes", -1)) != 0
        or int(s19.get("wbi_mutation_bytes", -1)) != 0
        or int(s19.get("calibration_mutation_bytes", -1)) != 0
        or int(s19.get("nvram_persistent_writes", -1)) != 0
        or int(s19.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(s19.get("physical_device_writes", -1)) != 0
        or s19.get("persistent_emmc_writes_authorized") is not False
        or s19_burn != 0
        or int(s19.get("xavc_clean_feed_leakage_events", -1)) != 0
        or s19_fiz != 0
        or int(s19.get("ibis_coil_saturation_events", -1)) != 0
        or int(s19.get("duct_salt_haze_ingestion_damage_events", -1)) != 0
    ):
        errors.append(f"p4: Stage 19 redlines violated (fiz={s19_fiz}, burn_in={s19_burn})")

    # Stage 20: Phase 117 ProRes RAW + Focus Breathing + MI-Shoe + AOC/CFexpress HIL
    s20 = vm_rep.get("stage20_proresraw_breathing_mishoe_hil", {})
    s20_crop = int(s20.get("pl_breathing_stale_crop_frames", -1)) + int(
        faults.p4_stage20_pl_breathing_stale_crop_frames
    )
    s20_fuse = int(s20.get("sy1129_hdmi_fuse_damage_events", -1)) + int(
        faults.p4_stage20_sy1129_fuse_damage_events
    )
    if (
        int(s20.get("nop_count", -1)) != 0
        or int(s20.get("cp_mutation_bytes", -1)) != 0
        or int(s20.get("wbi_mutation_bytes", -1)) != 0
        or int(s20.get("calibration_mutation_bytes", -1)) != 0
        or int(s20.get("nvram_persistent_writes", -1)) != 0
        or int(s20.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(s20.get("physical_device_writes", -1)) != 0
        or s20.get("persistent_emmc_writes_authorized") is not False
        or int(s20.get("raw_lut_burn_in_frames", -1)) != 0
        or s20_crop != 0
        or int(s20.get("audio_pop_click_frames", -1)) != 0
        or s20_fuse != 0
        or int(s20.get("cfexpress_fat_corruption_events", -1)) != 0
    ):
        errors.append(f"p4: Stage 20 redlines violated (stale_crop={s20_crop}, sy1129_fuse={s20_fuse})")

    # Stage 21: Phase 121 UVC/UAC + Wired SRT + CRSDK PTP + USB-PD/UART HIL
    s21 = vm_rep.get("stage21_uvc_srt_crsdk_usbpd_hil", {})
    s21_emmc = int(s21.get("emmc_flash_mutation_bytes", -1)) + int(
        faults.p4_stage21_emmc_flash_mutation_bytes
    )
    s21_wf12 = int(s21.get("wf12_00342260_hits", -1)) + int(faults.p4_stage21_wf12_hits)
    s21_uart = int(s21.get("uart_tx_bytes", -1)) + int(faults.p4_stage21_uart_tx_bytes)
    if (
        int(s21.get("nop_count", -1)) != 0
        or int(s21.get("cp_mutation_bytes", -1)) != 0
        or int(s21.get("wbi_mutation_bytes", -1)) != 0
        or int(s21.get("calibration_mutation_bytes", -1)) != 0
        or int(s21.get("nvram_persistent_writes", -1)) != 0
        or int(s21.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(s21.get("physical_device_writes", -1)) != 0
        or s21.get("persistent_emmc_writes_authorized") is not False
        or s21_emmc != 0
        or s21_wf12 != 0
        or int(s21.get("cxd90057_pad_damage_events", -1)) != 0
        or int(s21.get("uvc_osd_burn_in_frames", -1)) != 0
        or int(s21.get("srt_dropped_gops", -1)) != 0
        or s21_uart != 0
    ):
        errors.append(
            f"p4: Stage 21 redlines violated (emmc_flash_mut={s21_emmc}, wf12_hits={s21_wf12}, uart_tx={s21_uart})"
        )

    total_wf12_hits = int(m110_p4.evidence.get("stage15_wf12_00342260_hits", 0)) + max(0, s21_wf12)
    total_emmc_mut = max(0, s21_emmc)

    total_stages = len(stage_statuses)
    passed_stages = sum(1 for v in stage_statuses.values() if v)
    if total_stages < 21 or passed_stages < 21 or passed_stages != total_stages:
        errors.append(
            f"p4: expected >= 21 VM stages and all passing, got {passed_stages}/{total_stages}"
        )

    passed = len(errors) == 0
    evidence = dict(m110_p4.evidence)
    evidence.update(
        {
            "stage_count": total_stages,
            "passed_stage_count": passed_stages,
            "stage_statuses": stage_statuses,
            "stage19_fiz_gear_strip_events": s19_fiz,
            "stage19_display_assist_burn_in_frames": s19_burn,
            "stage19_digest_sha256": s19.get("phase112_audit_digest_sha256"),
            "stage20_pl_breathing_stale_crop_frames": s20_crop,
            "stage20_sy1129_fuse_damage_events": s20_fuse,
            "stage20_digest_sha256": s20.get("phase117_audit_digest_sha256"),
            "stage21_emmc_flash_mutation_bytes": s21_emmc,
            "stage21_wf12_00342260_hits": s21_wf12,
            "stage21_uart_tx_bytes": s21_uart,
            "stage21_digest_sha256": s21.get("phase121_audit_digest_sha256"),
            "wf12_00342260_hits": total_wf12_hits,
            "emmc_flash_mutation_bytes": total_emmc_mut,
        }
    )
    pillar = Milestone130PillarResult(
        pillar_id="P4",
        pillar_name="TWENTY_ONE_PLUS_STAGE_VM_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {passed_stages}/{total_stages} stages (>=21 required; Stages 1..21), "
            f"cp_mut={meta_18['cp_mutation_bytes']}B, wf12_hits={total_wf12_hits}, "
            f"emmc_flash_mut={total_emmc_mut}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "stage_count": total_stages,
        "passed_count": passed_stages,
        "cp_mutation_bytes": meta_18["cp_mutation_bytes"],
        "bk4_persistent_nvram_writes": meta_18["bk4_persistent_nvram_writes"],
        "wf12_00342260_hits": total_wf12_hits,
        "emmc_flash_mutation_bytes": total_emmc_mut,
    }
    return pillar, meta


def _evaluate_pillar_5(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: Milestone130FaultInjection,
) -> Tuple[Milestone130PillarResult, Dict[str, Any]]:
    # 1. Rounds 14 + 17 + 19 via Milestone 110 P5 evaluator
    m110_p5, meta_110 = _eval_m110_p5(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=_to_m110_faults(faults),
    )
    errors: List[str] = list(m110_p5.errors)

    # 2. Rounds 20..24: Five 4-language (EN/JA/ZH-CN/ZH-TW) 12/12 dual-surface closures = 60/60 pairs
    r20_24_nops = int(faults.p5_r20_to_r24_nop_count)
    r20_24_crashes = int(faults.p5_r20_to_r24_crashes)
    r20_24_rounds_verified = 0
    r20_24_pos_pairs = 0
    r20_24_runs_verified = 0
    r20_24_details: Dict[str, Dict[str, Any]] = {}

    for spec in ROUND20_TO_24_SPECS:
        rep, source = _load_round20_to_24_summary(
            spec,
            repo_root=repo_root,
            use_clean_room=use_clean_room,
        )
        r_schema = str(rep.get("schema", ""))
        r_kver = str(rep.get("kernel_version", ""))
        if r_schema != spec.expected_schema:
            errors.append(f"p5_{spec.round_key}: unexpected schema {r_schema!r}")
        if "4.9.337-scel+" not in r_kver:
            errors.append(f"p5_{spec.round_key}: unexpected FX3 kernel_version {r_kver!r}")

        runs_map = rep.get("runs", {})
        round_runs_ok = 0
        round_sha_ok = True
        for run_id, expected_sid, expected_lang in spec.run_specs:
            robj = runs_map.get(run_id)
            if not isinstance(robj, Mapping):
                errors.append(f"p5_{spec.round_key}: missing run {run_id}")
                continue
            rnop, rcrash, _, rsha = _verify_stage_b_manifest_and_faithful(
                robj,
                tag=f"p5_{spec.round_key}:{run_id}",
                expected_sid=expected_sid,
                expected_lang=expected_lang,
                manifest_override=faults.p5_r20_to_r24_manifest_count_override,
                errors=errors,
            )
            r20_24_nops += rnop
            r20_24_crashes += rcrash
            round_sha_ok = round_sha_ok and rsha
            round_runs_ok += 1
            r20_24_runs_verified += 1
        if not round_sha_ok:
            errors.append(
                f"p5_{spec.round_key}: Stage-B manifest SHA-256 mismatch for appFw.so or libWlanResource.so"
            )

        audit = copy.deepcopy(rep.get(spec.audit_key, {}))
        if not bool(audit.get(spec.green_bool_key, False)):
            errors.append(f"p5_{spec.round_key}: {spec.green_bool_key} is False")
        if not bool(audit.get(spec.pairs_bool_key, False)):
            errors.append(f"p5_{spec.round_key}: {spec.pairs_bool_key} is False")

        round_pos_pairs = 0
        for surf_key in (spec.menu_pairwise_key, spec.tab_pairwise_key):
            sblock = audit.get(surf_key, {})
            pairs = sblock.get("pairs", {}) if isinstance(sblock, Mapping) else {}
            if (
                faults.p5_r20_to_r24_zero_round == spec.round_key
                and faults.p5_r20_to_r24_zero_pair_name
                and faults.p5_r20_to_r24_zero_pair_name in pairs
                and surf_key == spec.menu_pairwise_key
            ):
                pairs[faults.p5_r20_to_r24_zero_pair_name]["diff_pixels"] = 0
                pairs[faults.p5_r20_to_r24_zero_pair_name]["strictly_positive"] = False

            surf_pos = 0
            for pk in ROUND20_24_4LANG_PAIR_KEYS:
                ent = pairs.get(pk)
                if (
                    isinstance(ent, Mapping)
                    and int(ent.get("diff_pixels", 0)) > 0
                    and bool(ent.get("strictly_positive", False))
                ):
                    surf_pos += 1
                else:
                    errors.append(
                        f"p5_{spec.round_key}: {surf_key} pair {pk} is not strictly positive"
                    )
            round_pos_pairs += surf_pos
        r20_24_pos_pairs += round_pos_pairs

        matrix = audit.get(spec.matrix_key, [])
        if not isinstance(matrix, list) or len(matrix) != 8:
            errors.append(f"p5_{spec.round_key}: expected 8-cell matrix, got {len(matrix) if isinstance(matrix, list) else -1}")
        else:
            for idx, cell in enumerate(matrix):
                wf12_val = (
                    int(faults.p5_r20_to_r24_wf12_immune_override)
                    if (
                        faults.p5_r20_to_r24_wf12_immune_override is not None
                        and faults.p5_r20_to_r24_zero_round == spec.round_key
                        and idx == 0
                    )
                    else int(cell.get("wf12_00342260_immune", -1))
                )
                if (
                    wf12_val != 1
                    or int(cell.get("airplane_bk4_hits", -1)) != 0
                    or int(cell.get("nop_count", -1)) != 0
                    or int(cell.get("crashes", -1)) != 0
                    or int(cell.get("stage_b_manifest_count", -1)) != 13
                ):
                    errors.append(
                        f"p5_{spec.round_key}: 8-cell matrix item[{idx}] failed WF-12/BK4/manifest invariants"
                    )

        if round_runs_ok == len(spec.run_specs) and round_pos_pairs == 12:
            r20_24_rounds_verified += 1

        r20_24_details[spec.round_key] = {
            "source": source,
            "schema": r_schema,
            "runs_verified": round_runs_ok,
            "positive_pairs": round_pos_pairs,
        }

    if r20_24_nops != 0 or r20_24_crashes != 0:
        errors.append(f"p5_r20_r24: real-kernel nop={r20_24_nops} or crash={r20_24_crashes} != 0")

    total_nops = int(meta_110["real_kernel_nop_count"]) + r20_24_nops
    total_crashes = int(meta_110["real_kernel_crashes"]) + r20_24_crashes

    passed = (
        len(errors) == 0
        and r20_24_rounds_verified == len(ROUND20_TO_24_SPECS)
        and r20_24_pos_pairs == 60
        and r20_24_runs_verified == ROUND20_TO_24_TOTAL_RUNS
        and total_nops == 0
        and total_crashes == 0
    )
    evidence = dict(m110_p5.evidence)
    evidence.update(
        {
            "round20_to_24_rounds_verified": r20_24_rounds_verified,
            "round20_to_24_positive_pairs": r20_24_pos_pairs,
            "round20_to_24_runs_verified": r20_24_runs_verified,
            "round20_to_24_details": r20_24_details,
            "real_kernel_nop_count": total_nops,
            "real_kernel_crashes": total_crashes,
        }
    )
    pillar = Milestone130PillarResult(
        pillar_id="P5",
        pillar_name="REAL_KERNEL_R14_R17_R19_R20_TO_R24_UI_CLOSURES",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Real FX3 7.02 (4.9.337-scel+): R14 {meta_110['round14_positive_pairs']}/18 + "
            f"R17 {meta_110['round17_tabs_verified']}/10 ({meta_110['round17_pairwise_deltas_verified']}/45) + "
            f"R19 {meta_110['round19_categories_verified']}/11 ({meta_110['round19_pairwise_deltas_verified']}/55) + "
            f"R20..24 {r20_24_rounds_verified}/5 ({r20_24_pos_pairs}/60 pairs), "
            f"nop={total_nops}, crash={total_crashes} {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_110)
    meta.update(
        {
            "round20_to_24_rounds_verified": r20_24_rounds_verified,
            "round20_to_24_positive_pairs": r20_24_pos_pairs,
            "round20_to_24_runs_verified": r20_24_runs_verified,
            "real_kernel_nop_count": total_nops,
            "real_kernel_crashes": total_crashes,
        }
    )
    return pillar, meta


def _evaluate_pillar_6(
    raw_6: Mapping[str, Any],
    faults: Milestone130FaultInjection,
    *,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
) -> Tuple[Milestone130PillarResult, Dict[str, Any]]:
    v3_faults = StageBReleaseDossierV3FaultInjection(
        pillar_f_drift_surface=faults.p6_drift_surface,
        pillar_f_tamper_negative_control=faults.p6_tamper_negative_control,
    )
    pf, meta_f = _evaluate_pillar_f(raw_6, v3_faults)
    errors: List[str] = list(pf.errors)

    if p1_meta.get("persistent_emmc_writes_authorized") is not False or p1_meta.get(
        "simulated_ready_for_hardware_attach"
    ) is not False:
        errors.append("p6: P1 hardware-lock invariant breached")
    if (
        int(p2_meta.get("otp_fuse_touches", -1)) != 0
        or int(p2_meta.get("rpmb_counter_increments", -1)) != 0
        or int(p2_meta.get("passive_tx_bytes_emitted", -1)) != 0
    ):
        errors.append("p6: P2 zero-touch OTP/RPMB/passive-UART invariant breached")
    if int(p3_meta.get("calibration_mutation_bytes", -1)) != 0:
        errors.append("p6: P3 calibration zero-mutation invariant breached")
    if (
        int(p4_meta.get("cp_mutation_bytes", -1)) != 0
        or int(p4_meta.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(p4_meta.get("wf12_00342260_hits", -1)) != 0
        or int(p4_meta.get("emmc_flash_mutation_bytes", -1)) != 0
    ):
        errors.append("p6: P4 CP/BK4/WF-12/eMMC zero-mutation invariant breached")

    passed = len(errors) == 0 and pf.passed
    evidence = dict(pf.evidence)
    evidence["dossier_v3_schema_anchor"] = DOSSIER_V3_SCHEMA_VERSION
    evidence["capstone_22gate_schema_anchor"] = CAPSTONE_22GATE_SCHEMA_VERSION
    evidence["milestone90_schema_anchor"] = MILESTONE90_SCHEMA_VERSION
    evidence["milestone110_schema_anchor"] = MILESTONE110_SCHEMA_VERSION
    evidence["persistent_emmc_writes_authorized"] = PERSISTENT_EMMC_WRITES_AUTHORIZED
    evidence["otp_fuse_touches"] = int(p2_meta.get("otp_fuse_touches", 0))
    evidence["passive_tx_bytes_emitted"] = int(p2_meta.get("passive_tx_bytes_emitted", 0))

    pillar = Milestone130PillarResult(
        pillar_id="P6",
        pillar_name="POST_TRIAL_H0_VS_H2_IMMUTABILITY_AND_HARDWARE_LOCK_PROOF",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"DossierV3+Capstone22+M90+M110 + H0==H2 {meta_f['h0_surface_count']}/16 surfaces "
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


def _fault_to_worker_dict(faults: Milestone130FaultInjection) -> Dict[str, Any]:
    d = _m110_fault_to_worker_dict(_to_m110_faults(faults))
    for k in (
        "p1_saltspray_haze_kwargs",
        "p1_followfocus_gimbal_kwargs",
        "p1_hdmi_aoc_kwargs",
        "p1_cfexpress_media_kwargs",
        "p1_usbpd_uvc_kwargs",
        "p1_multiterminal_ptp_kwargs",
        "p1_monsoon_mishoe_kwargs",
        "p1_cagetwist_xlrh1_kwargs",
    ):
        val = getattr(faults, k)
        d[k] = dict(val) if val is not None else None
    return d


def _collect_parallel_milestone130_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: Milestone130FaultInjection,
) -> Tuple[
    Dict[str, Any],
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
        "hdr_hlg",
        "prores_mishoe",
        "uvc_crsdk",
        "mxf_tally",
    )

    try:
        ctx = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=16, mp_context=ctx) as ex:
            fut_1 = ex.submit(_worker_pillar_1, (str(repo_root), use_clean_room, fault_dict))
            fut_2m = ex.submit(_worker_recovery_master, use_clean_room)
            fut_2x = ex.submit(_worker_recovery_p8_p9_p10, use_clean_room)
            fut_2y = ex.submit(_worker_recovery_p11_to_p13, use_clean_room)
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
            raw_2y = fut_2y.result()
            raw_2a = fut_2a.result()
            raw_2b = fut_2b.result()
            auditors: Dict[str, Dict[str, Any]] = {}
            for fg in fut_3:
                auditors.update(fg.result())
            raw_4 = fut_4.result()
            raw_6 = fut_6.result()
            return raw_1, raw_2m, raw_2x, raw_2y, raw_2a, raw_2b, auditors, raw_4, raw_6
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1 = _worker_pillar_1((str(repo_root), use_clean_room, fault_dict))
    raw_2m = _worker_recovery_master(use_clean_room)
    raw_2x = _worker_recovery_p8_p9_p10(use_clean_room)
    raw_2y = _worker_recovery_p11_to_p13(use_clean_room)
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
    return raw_1, raw_2m, raw_2x, raw_2y, raw_2a, raw_2b, auditors, raw_4, raw_6


def build_stage_b_milestone130_master_gate_report(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[Milestone130FaultInjection] = None,
) -> StageBMilestone130MasterGateReport:
    """Build & evaluate the unified Phase 130 6-Pillar Milestone Master Gate certificate."""
    use_clean_room = _is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    active_faults = faults or Milestone130FaultInjection()

    (
        raw_1,
        raw_2m,
        raw_2x,
        raw_2y,
        raw_2a,
        raw_2b,
        auditors,
        raw_4,
        raw_6,
    ) = _collect_parallel_milestone130_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )

    p1 = _evaluate_pillar_1(raw_1)
    p2, meta_2 = _evaluate_pillar_2(raw_2m, raw_2x, raw_2y, raw_2a, raw_2b, active_faults)
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

    pillars: Tuple[Milestone130PillarResult, ...] = (p1, p2, p3, p4, p5, p6)
    passed_count = sum(1 for p in pillars if p.passed)
    failed_ids = tuple(p.pillar_id for p in pillars if not p.passed)
    all_errors: List[str] = []
    for p in pillars:
        all_errors.extend(p.errors)

    all_ready = passed_count == len(pillars) and len(all_errors) == 0
    mode_str = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"

    payload_no_sha: Dict[str, Any] = {
        "schema_version": STAGE_B_MILESTONE130_SCHEMA,
        "phase_version": PHASE_130_VERSION,
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
        "gate40_offline_verified": raw_1["offline_verified_gates"],
        "gate40_simulated_verified": raw_1["sim_verified_gates"],
        "recovery_pillar_count": meta_2["recovery_pillar_count"],
        "recovery_pillars_passed": meta_2["recovery_pillars_passed"],
        "firmware_lab_auditor_count": meta_3["auditor_count"],
        "firmware_lab_auditors_passed": meta_3["passed_count"],
        "vm_coemulation_stage_count": meta_4["stage_count"],
        "vm_coemulation_stages_passed": meta_4["passed_count"],
        "vm_wf12_00342260_hits": meta_4["wf12_00342260_hits"],
        "vm_emmc_flash_mutation_bytes": meta_4["emmc_flash_mutation_bytes"],
        "round14_positive_pairs": meta_5["round14_positive_pairs"],
        "round17_tabs_verified": meta_5["round17_tabs_verified"],
        "round17_pairwise_deltas_verified": meta_5["round17_pairwise_deltas_verified"],
        "round17_runs_verified": meta_5["round17_runs_verified"],
        "round19_categories_verified": meta_5["round19_categories_verified"],
        "round19_pairwise_deltas_verified": meta_5["round19_pairwise_deltas_verified"],
        "round19_runs_verified": meta_5["round19_runs_verified"],
        "round20_to_24_rounds_verified": meta_5["round20_to_24_rounds_verified"],
        "round20_to_24_positive_pairs": meta_5["round20_to_24_positive_pairs"],
        "round20_to_24_runs_verified": meta_5["round20_to_24_runs_verified"],
        "real_kernel_nop_count": meta_5["real_kernel_nop_count"],
        "real_kernel_crashes": meta_5["real_kernel_crashes"],
        "h0_surface_count": meta_6["h0_surface_count"],
        "drifted_surface_count": meta_6["drifted_surface_count"],
        "c2pa_rq_lic_intact": meta_6["c2pa_rq_lic_intact"],
        "spacc_cnflasha_untouched": meta_6["spacc_cnflasha_untouched"],
        "errors": tuple(all_errors),
    }
    digest = compute_milestone130_sha256(payload_no_sha)

    return StageBMilestone130MasterGateReport(
        schema_version=STAGE_B_MILESTONE130_SCHEMA,
        phase_version=PHASE_130_VERSION,
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
        gate40_offline_verified=raw_1["offline_verified_gates"],
        gate40_simulated_verified=raw_1["sim_verified_gates"],
        recovery_pillar_count=meta_2["recovery_pillar_count"],
        recovery_pillars_passed=meta_2["recovery_pillars_passed"],
        firmware_lab_auditor_count=meta_3["auditor_count"],
        firmware_lab_auditors_passed=meta_3["passed_count"],
        vm_coemulation_stage_count=meta_4["stage_count"],
        vm_coemulation_stages_passed=meta_4["passed_count"],
        vm_wf12_00342260_hits=meta_4["wf12_00342260_hits"],
        vm_emmc_flash_mutation_bytes=meta_4["emmc_flash_mutation_bytes"],
        round14_positive_pairs=meta_5["round14_positive_pairs"],
        round17_tabs_verified=meta_5["round17_tabs_verified"],
        round17_pairwise_deltas_verified=meta_5["round17_pairwise_deltas_verified"],
        round17_runs_verified=meta_5["round17_runs_verified"],
        round19_categories_verified=meta_5["round19_categories_verified"],
        round19_pairwise_deltas_verified=meta_5["round19_pairwise_deltas_verified"],
        round19_runs_verified=meta_5["round19_runs_verified"],
        round20_to_24_rounds_verified=meta_5["round20_to_24_rounds_verified"],
        round20_to_24_positive_pairs=meta_5["round20_to_24_positive_pairs"],
        round20_to_24_runs_verified=meta_5["round20_to_24_runs_verified"],
        real_kernel_nop_count=meta_5["real_kernel_nop_count"],
        real_kernel_crashes=meta_5["real_kernel_crashes"],
        h0_surface_count=meta_6["h0_surface_count"],
        drifted_surface_count=meta_6["drifted_surface_count"],
        c2pa_rq_lic_intact=meta_6["c2pa_rq_lic_intact"],
        spacc_cnflasha_untouched=meta_6["spacc_cnflasha_untouched"],
        errors=tuple(all_errors),
        milestone130_sha256=digest,
    )


def verify_stage_b_milestone130_master_gate(
    report: object,
) -> StageBMilestone130VerifyResult:
    """Fail-closed verifier for a Milestone Phase 130 Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, StageBMilestone130MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return StageBMilestone130VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone130_sha256="",
            observed_milestone130_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or StageBMilestone130MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = payload.get("schema_version") == STAGE_B_MILESTONE130_SCHEMA
    if not schema_ok:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r}")

    expected_sha = compute_milestone130_sha256(payload)
    observed_sha = str(payload.get("milestone130_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(f"milestone130_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}")

    redlines_ok = (
        payload.get("o_rdonly_enforced") is True
        and payload.get("persistent_emmc_writes_authorized") is False
        and payload.get("persistent_write_release") is False
        and payload.get("hardware_live_attachment_authorized") is False
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
        int(payload.get("gate40_offline_verified", -1)) >= 37
        and int(payload.get("gate40_simulated_verified", -1)) >= 40
        and int(payload.get("recovery_pillar_count", -1)) >= 13
        and int(payload.get("recovery_pillars_passed", -1))
        == int(payload.get("recovery_pillar_count", -2))
        and int(payload.get("firmware_lab_auditor_count", -1)) >= 24
        and int(payload.get("firmware_lab_auditors_passed", -1))
        == int(payload.get("firmware_lab_auditor_count", -2))
        and int(payload.get("vm_coemulation_stage_count", -1)) >= 21
        and int(payload.get("vm_coemulation_stages_passed", -1))
        == int(payload.get("vm_coemulation_stage_count", -2))
        and int(payload.get("vm_wf12_00342260_hits", -1)) == 0
        and int(payload.get("vm_emmc_flash_mutation_bytes", -1)) == 0
        and int(payload.get("round14_positive_pairs", -1)) == 18
        and int(payload.get("round17_tabs_verified", -1)) == 10
        and int(payload.get("round17_pairwise_deltas_verified", -1)) == 45
        and int(payload.get("round17_runs_verified", -1)) == len(ROUND17_RUN_SPECS)
        and int(payload.get("round19_categories_verified", -1)) == 11
        and int(payload.get("round19_pairwise_deltas_verified", -1)) == 55
        and int(payload.get("round19_runs_verified", -1)) == len(ROUND19_RUN_SPECS)
        and int(payload.get("round20_to_24_rounds_verified", -1)) == 5
        and int(payload.get("round20_to_24_positive_pairs", -1)) == 60
        and int(payload.get("round20_to_24_runs_verified", -1)) == ROUND20_TO_24_TOTAL_RUNS
        and int(payload.get("real_kernel_nop_count", -1)) == 0
        and int(payload.get("real_kernel_crashes", -1)) == 0
        and int(payload.get("h0_surface_count", -1)) == 16
        and int(payload.get("drifted_surface_count", -1)) == 0
        and payload.get("c2pa_rq_lic_intact") is True
        and payload.get("spacc_cnflasha_untouched") is True
    )
    if not counts_ok:
        errors.append("milestone130 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append("all_pillars_milestone_ready / status is not MILESTONE_130_SIMULATION_READY")

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 130 payload")

    valid = bool(schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0)
    return StageBMilestone130VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone130_sha256=expected_sha,
        observed_milestone130_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


def render_milestone130_markdown(report: StageBMilestone130MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 130 Master Gate."""
    lines = [
        f"# Stage-B Milestone Phase 130 Master Gate (`{report.schema_version}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone130_sha256}`",
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
            f"- 40-Gate Preflight (`G01..G40`): offline=`{report.gate40_offline_verified}/40` (blocked), simulated=`{report.gate40_simulated_verified}/40`",
            f"- Recovery Master Suite (`Ph47..124`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`>=13` pillars, UART `S0..S6`, `passive_tx={report.passive_tx_bytes_emitted}B`)",
            f"- Firmware-Lab Auditors: `{report.firmware_lab_auditors_passed}/{report.firmware_lab_auditor_count}` (`>=24` required)",
            f"- Full-Board Co-Emulation VM: `{report.vm_coemulation_stages_passed}/{report.vm_coemulation_stage_count}` (`>=21` required, `wf12_hits={report.vm_wf12_00342260_hits}`, `emmc_flash_mut={report.vm_emmc_flash_mutation_bytes}B`)",
            f"- Real FX3 `7.02` Kernel (`4.9.337-scel+`): R14 `{report.round14_positive_pairs}/18` + R17 Status `{report.round17_tabs_verified}/10` (`{report.round17_pairwise_deltas_verified}/45` pairs > 0) + R19 Menu `{report.round19_categories_verified}/11` (`{report.round19_pairwise_deltas_verified}/55` pairs > 0) + R20..R24 `{report.round20_to_24_rounds_verified}/5` rounds (`{report.round20_to_24_positive_pairs}/60` 4-lang pairs > 0), `nop={report.real_kernel_nop_count}`, `crashes={report.real_kernel_crashes}`",
            f"- `H0 == H2` Immutability: `{report.h0_surface_count - report.drifted_surface_count}/{report.h0_surface_count}` zero drift (`c2pa_rq_lic_intact={report.c2pa_rq_lic_intact}`, `spacc_cnflasha_untouched={report.spacc_cnflasha_untouched}`)",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "CALIBRATION_MUTATION_BYTES",
    "CP_MUTATION_BYTES",
    "DEFAULT_REPO_ROOT",
    "FIRMWARE_LAB_24_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "MILESTONE130_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "P8_CP_MUTATION_FORBIDDEN",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_130_VERSION",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "RECOVERY_13_PILLAR_IDS",
    "ROUND20_24_4LANG_PAIR_KEYS",
    "ROUND20_SPEC",
    "ROUND21_SPEC",
    "ROUND22_SPEC",
    "ROUND23_SPEC",
    "ROUND24_SPEC",
    "ROUND20_TO_24_SPECS",
    "ROUND20_TO_24_TOTAL_RUNS",
    "RPMB_COUNTER_INCREMENTS",
    "SCHEMA_VERSION",
    "STAGE_B_MILESTONE130_SCHEMA",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "VM_COEMULATION_21_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone130FaultInjection",
    "Milestone130PillarResult",
    "RoundClosureSpec",
    "StageBMilestone130MasterGateReport",
    "StageBMilestone130VerifyResult",
    "build_stage_b_milestone130_master_gate_report",
    "compute_milestone130_sha256",
    "render_milestone130_markdown",
    "verify_stage_b_milestone130_master_gate",
]
