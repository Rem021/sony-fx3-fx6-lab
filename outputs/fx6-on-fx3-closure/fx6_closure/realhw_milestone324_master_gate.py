"""Grand Milestone Phase 324 — Forward-Compatible 6-Pillar Real-Hardware `ILME-FX3 Ver. 7.02` Master Gate (`realhw_milestone324_master_gate_v1`).

Unites ALL Wave 21–61+ Real-Hardware Main Track subsystems (Phases 134–323) and ALL
38+ live Sony ILME-FX3 `Ver. 7.02` (`Linux 4.9.337-scel+`) ARM64 QEMU Rehearsal
Rounds (`Rounds 28..65+`, `>= 114` sub-runs `r28a..r65c+`, and `>= 76` `< 50 KiB` /
`51,200 B` sanitized PNG receipts, observed max `27,467 B`) into a single
tamper-evident, fail-closed SHA-256 certificate executing across both
`LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
while keeping `verify-milestone-90/110/130/147/175/193/209/221/233/254/264/295/311` and
all 14 bench readiness preflights (`Ph186..Ph321`) intact and forward-compatible via
`>=` lower bounds:

- `P1` (`SAFETY_142PLUS_GATE_REALHW_MASTER_PREFLIGHT`):
  Dynamically discovers the highest available `evaluate_<N>gate_preflight` in
  `fx3_safety` (`N >= 142`, baseline `evaluate_142gate_preflight` and auto-discovering
  `144, 146, ...`), verifying `== N - 3` passed offline (`3` Tier-0 hardware bench
  gates `G10..G12` fail-closed offline) and `N/N` passed in `--simulate-bench-dry-run`
  covering `G63..G142+` (Waves 21–61+), with `overall_ready_for_hardware_attach == False`,
  `persistent_emmc_writes_authorized == False`, `cross_model_flash_authorized == False`,
  `usb_packets_transmitted == 0`, and `raw_firmware_bytes_leaked == 0`.
- `P2` (`FIFTY_SIX_PLUS_PILLAR_RECOVERY_MASTER_VAULT`):
  Dynamically discovers the highest available
  `evaluate_realhw_<M>pillar_recovery_master` in `fx3_recovery` (`M >= 56`, baseline
  `evaluate_realhw_56pillar_recovery_master` and auto-discovering `57, 58, ...`),
  verifying `M/M` passed (`all_passed == True`), `cnflasha_userspace_write_blocked == True`,
  `otp_fuse_touches == 0`, `rpmb_counter_increments == 0`,
  `passive_tx_bytes_emitted == 0`, `physical_usb_packets_emitted == 0`, and
  `raw_firmware_bytes_leaked == 0`.
- `P3` (`FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS`):
  Verifies all `>= 45` `fx3_firmware_lab` auditors plus dynamic discovery of any
  newly merged `46th+` `realhw_*_auditor.py`, locking `raw_firmware_bytes_leaked == 0`,
  `e_nd_actuator_tx_count == 0`, and `calibration_mutation_bytes == 0`.
- `P4` (`SIXTY_SIX_PLUS_STAGE_VM_HIL_COEMULATION`):
  Runs `fx3_vm_coemulation_suite` with all stages enabled (`>= 66` stages through
  `stage66` Wave-56/57, dynamically discovering `Stage 67+`), locking
  `raw_firmware_bytes_leaked == 0`, `physical_device_writes == 0`, and
  `emmc_corruptions == 0`.
- `P5` (`TETRADECUPLE_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH321`):
  Verifies `Phase 136`, `Phase 143`, `Phase 154`, AND all `14/14` Physical Bench
  Readiness Verifiers (`Ph186`, `Ph204`, `Ph216`, `Ph227`, `Ph248`, `Ph261`,
  `Ph275`, `Ph279`, `Ph284`, `Ph291`, `Ph302`, `Ph307`, `Ph316`
  `bright-monitoring-shot-mark-big6-home-and-ssh-auth`, AND `Ph321`
  `rec-media-autoswitch-proxy-cloud-mymenu-and-ftpes`) return
  `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` offline and
  `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` in simulated dry-run, with
  `overall_ready_for_hardware_attach == False`, `16/16 H0 == H3`,
  `e_nd_actuator_tx_count == 0`, `rf_packets_transmitted == 0`,
  `usb_packets_transmitted == 0`, `slot1_data_sector_writes == 0`, and
  `raw_firmware_bytes_leaked == 0`.
- `P6` (`REAL_FX3_702_QEMU_ROUNDS_28_TO_65_PLUS_AND_PNG_RECEIPTS`):
  Verifies `>= 38` live `ILME-FX3 Ver. 7.02` ARM64 QEMU rounds through `Round 65+`
  (`r28..r65+`, dynamically discovering `r66+`), `>= 114` live sub-runs, `>= 76`
  sanitized PNG receipts (`< 51,200` bytes each; baseline max `<= 27,467 B`),
  `16/16 H0 == H3`, `emmc_write_count == 0`, and `raw_firmware_bytes_leaked == 0`.
"""

from __future__ import annotations

import argparse
import sys

sys.dont_write_bytecode = True

from concurrent.futures import ProcessPoolExecutor
import copy
from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
import multiprocessing as mp
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from .realhw_milestone295_master_gate import (
    _ensure_cross_package_paths,
    DEFAULT_REPO_ROOT,
)

_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

import fx3_recovery  # noqa: E402
import fx3_safety  # noqa: E402
from fx3_vm_coemulation_suite import (  # noqa: E402
    CoEmulationConfig,
    run_fx3_vm_coemulation_suite,
)

from .hardware_readiness_packet import _is_forced_clean_room  # noqa: E402
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
)
from .realhw_bench_cable_fan_and_slot1_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
)
from .realhw_bright_mon_shotmark_big6_home_and_ssh_auth_verifier import (  # noqa: E402
    evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight,
    verify_phase316_report,
)
from .realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_verifier import (  # noqa: E402
    evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight,
    verify_phase321_report,
)
from .realhw_milestone147_master_gate import _worker_phase136  # noqa: E402
from .realhw_milestone175_master_gate import (  # noqa: E402
    MILESTONE175_SCHEMA_VERSION,
    RoundQemuReceiptSpec,
)
from .realhw_milestone193_master_gate import (  # noqa: E402
    _66GATE_FAULT_FIELDS,
    MILESTONE193_SCHEMA_VERSION,
    PNG_MAGIC_BYTES,
    _load_round28_to_37_summary,
    _read_file_o_rdonly,
    _worker_phase143_154_186,
)
from .realhw_milestone209_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    E_ND_ACTUATOR_TX_COUNT,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    MILESTONE209_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    USB_OR_CAMERA_OPERATIONS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    _72GATE_EXTRA_FAULT_FIELDS,
    _effective_m193_faults,
    _worker_phase204,
)
from .realhw_milestone221_master_gate import (  # noqa: E402
    EMMC_WRITE_COUNT,
    MILESTONE221_SCHEMA_VERSION,
    OTP_FUSE_WRITES,
    PASSIVE_TX_BYTES,
    RPMB_WRITES,
    USB_PACKETS_TRANSMITTED,
    _78GATE_EXTRA_FAULT_FIELDS,
    _effective_m209_faults,
    _worker_phase216,
)
from .realhw_milestone233_master_gate import (  # noqa: E402
    FIRMWARE_LAB_45_AUDITOR_KEYS,
    MILESTONE233_SCHEMA_VERSION,
    PNG_MAX_SIZE_50KIB_BYTES,
    _90GATE_EXTRA_FAULT_FIELDS,
    _effective_m221_faults,
    _inspect_round_png_receipt_50kib,
    _worker_phase227,
    _worker_pillar_3_batch_233,
)
from .realhw_milestone254_master_gate import (  # noqa: E402
    AGENT_AUTO_FLASH_BLOCKED,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MILESTONE254_SCHEMA_VERSION,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    PHYSICAL_DEVICE_WRITES,
    _96GATE_EXTRA_FAULT_FIELDS,
    _check_vm_stage45_to_47_redlines,
    _effective_m233_faults,
    _worker_phase248,
)
from .realhw_milestone264_master_gate import (  # noqa: E402
    MILESTONE264_SCHEMA_VERSION,
    _102GATE_EXTRA_FAULT_FIELDS,
    _effective_m254_faults,
    _worker_phase261,
)
from .realhw_milestone295_master_gate import (  # noqa: E402
    CROSS_MODEL_FLASH_AUTHORIZED,
    MILESTONE295_SCHEMA_VERSION,
    PNG_MAX_SIZE_BYTES,
    RealHwMilestone295FaultInjection,
    _124GATE_EXTRA_FAULT_FIELDS,
    _MASTER_REPORT_KEY_RE,
    _RAW_BYTES_REPR_RE,
    _RECOVERY_EVAL_RE,
    _ROUND_DIR_RE,
    _SAFETY_EVAL_RE,
    _check_4group_bench_verifier,
    _effective_m264_faults,
    _evaluate_pillar_3 as _eval_m295_p3,
    _worker_phase275_279,
    _worker_phase284_291,
    _worker_pillar_4_295,
)
from .realhw_milestone311_master_gate import (  # noqa: E402
    MILESTONE311_SCHEMA_VERSION,
    ROUND28_TO_62_PNG_RECEIPTS,
    ROUND28_TO_62_SPECS,
    VM_COEMULATION_62_STAGE_KEYS,
    RealHwMilestone311FaultInjection,
    _134GATE_EXTRA_FAULT_FIELDS,
    _NEGATIVE_AUDIT_BOOL_KEYS as _M311_NEGATIVE_AUDIT_BOOL_KEYS,
    _effective_m295_faults as _effective_m295_from_m311,
    _evaluate_pillar_4 as _eval_m311_p4,
    _evaluate_pillar_5 as _eval_m311_p5,
    _extract_nested_g_valid_and_g71_end_tx,
    _fault_to_134gate_worker_dict,
    _worker_phase302_307,
)
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_MILESTONE324_SCHEMA: str = "realhw_milestone324_master_gate_v1"
MILESTONE324_SCHEMA_VERSION: str = REALHW_MILESTONE324_SCHEMA
P324_SCHEMA: str = REALHW_MILESTONE324_SCHEMA
SCHEMA_VERSION: str = REALHW_MILESTONE324_SCHEMA
PHASE_324_VERSION: str = "324.0.0"
P324_VERSION: str = PHASE_324_VERSION

P324_PNG_MAX_SIZE_BYTES: int = PNG_MAX_SIZE_BYTES
P324_BASELINE_PNG_MAX_OBSERVED_BYTES: int = 27_467
P324_PHYSICAL_DEVICE_WRITES: int = PHYSICAL_DEVICE_WRITES
P324_RAW_FIRMWARE_BYTES_LEAKED: int = RAW_FIRMWARE_BYTES_LEAKED

STATUS_MILESTONE_READY: str = "MILESTONE_324_PREBENCH_MASTER_VERIFIED"
P324_STATUS_MILESTONE_READY: str = STATUS_MILESTONE_READY
P324_STATUS_FAIL_CLOSED: str = STATUS_FAIL_CLOSED

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_142PLUS_GATE_REALHW_MASTER_PREFLIGHT"),
    ("P2", "FIFTY_SIX_PLUS_PILLAR_RECOVERY_MASTER_VAULT"),
    ("P3", "FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS"),
    ("P4", "SIXTY_SIX_PLUS_STAGE_VM_HIL_COEMULATION"),
    ("P5", "TETRADECUPLE_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH321"),
    ("P6", "REAL_FX3_702_QEMU_ROUNDS_28_TO_65_PLUS_AND_PNG_RECEIPTS"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)
P324_PILLAR_SPECS: Tuple[Tuple[str, str], ...] = PILLAR_SPECS
P324_PILLAR_IDS: Tuple[str, ...] = PILLAR_IDS

RECOVERY_56_PILLAR_IDS: Tuple[str, ...] = tuple(fx3_recovery.MASTER_56_PILLAR_IDS)

VM_COEMULATION_66_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_62_STAGE_KEYS,
    "stage63_realhw_lens_comp_af_illuminator_folder_rating_hil",
    "stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil",
    "stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil",
    "stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil",
)

ROUND63_SUMMARY_RELPATH: str = (
    "reports/2026-11-17-round63-realhw-still-raw-heif-colorspace-shuttertype-drive-qemu/summary.json"
)
ROUND64_SUMMARY_RELPATH: str = (
    "reports/2026-11-17-round64-milestone-focus-area-zoom-lever-iso-minss-flash-qemu/summary.json"
)
ROUND65_SUMMARY_RELPATH: str = (
    "reports/2026-11-17-round65-milestone-dci4k-aspect-recall-hold-camset-photocap-qemu/summary.json"
)

ROUND63_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round63-milestone-36realhw-still-raw-heif-colorspace-shuttertype-drive-qemu-v1"
)
ROUND64_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round64-milestone-37realhw-focus-area-zoom-lever-iso-minss-flash-qemu-v1"
)
ROUND65_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round65-milestone-38realhw-dci4k-aspect-recall-hold-camset-photocap-qemu-v1"
)

ROUND28_TO_65_SPECS: Tuple[RoundQemuReceiptSpec, ...] = (
    *ROUND28_TO_62_SPECS,
    RoundQemuReceiptSpec(
        round_num=63,
        summary_relpath=ROUND63_SUMMARY_RELPATH,
        expected_schema=ROUND63_EXPECTED_SCHEMA,
        audit_key="r63_realhw_still_raw_heif_colorspace_shutter_drive_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r63a_wave49_still_raw_heif_colorspace_shutter_drive_verified",
            "r63a_stageb_big6_sid_0a_ge_300k_pixels_verified",
            "r63b_still_raw_heif_colorspace_shutter_guard_fail_closed",
            "r63c_clean_unmount_still_reset_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r63a_still_raw_heif_colorspace_shutter_drive_big6_schinese", 1),
            ("r63b_still_raw_heif_colorspace_shutter_guard", 1),
            ("r63c_clean_unmount_still_reset_h0_h3_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=64,
        summary_relpath=ROUND64_SUMMARY_RELPATH,
        expected_schema=ROUND64_EXPECTED_SCHEMA,
        audit_key="r64_milestone_focus_area_zoom_lever_iso_minss_flash_audit",
        audit_bool_keys=(
            "power_of_two_grand_milestone",
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r64a_wave50_focus_zoom_iso_flash_verified",
            "r64a_stageb_big6_sid_0a_ge_300k_pixels_verified",
            "r64b_wave50_guard_fail_closed",
            "r64c_clean_unmount_wave50_reset_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r64a_focus_area_zoom_iso_flash_big6_schinese", 1),
            ("r64b_wave50_focus_zoom_iso_flash_guard", 1),
            ("r64c_clean_unmount_wave50_reset_h0_h3_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=65,
        summary_relpath=ROUND65_SUMMARY_RELPATH,
        expected_schema=ROUND65_EXPECTED_SCHEMA,
        audit_key="r65_milestone_dci4k_aspect_recall_hold_camset_photocap_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r65a_wave51_dci4k_aspect_camset_photocap_verified",
            "r65a_stageb_big6_sid_0a_ge_300k_pixels_verified",
            "r65b_wave51_guard_fail_closed",
            "r65c_clean_unmount_wave51_reset_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r65a_dci4k_aspect_camset_photocap_big6_schinese", 1),
            ("r65b_wave51_dci4k_aspect_camset_photocap_guard", 1),
            ("r65c_clean_unmount_wave51_reset_h0_h3_big6_schinese", 1),
        ),
    ),
)

ROUND28_TO_65_PNG_RECEIPTS: Dict[int, Tuple[str, str]] = {
    **ROUND28_TO_62_PNG_RECEIPTS,
    63: (
        "reports/2026-11-17-round63-realhw-still-raw-heif-colorspace-shuttertype-drive-qemu/assets/r63a-raw-heif-colorspace-shutter-4ch-big6-schinese-alpha.png",
        "reports/2026-11-17-round63-realhw-still-raw-heif-colorspace-shuttertype-drive-qemu/assets/r63a-raw-heif-colorspace-shutter-4ch-big6-schinese-composited.png",
    ),
    64: (
        "reports/2026-11-17-round64-milestone-focus-area-zoom-lever-iso-minss-flash-qemu/assets/r64a-focus-area-zoom-iso-flash-4ch-big6-schinese-alpha.png",
        "reports/2026-11-17-round64-milestone-focus-area-zoom-lever-iso-minss-flash-qemu/assets/r64a-focus-area-zoom-iso-flash-4ch-big6-schinese-composited.png",
    ),
    65: (
        "reports/2026-11-17-round65-milestone-dci4k-aspect-recall-hold-camset-photocap-qemu/assets/r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese-alpha.png",
        "reports/2026-11-17-round65-milestone-dci4k-aspect-recall-hold-camset-photocap-qemu/assets/r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese-composited.png",
    ),
}

_NEGATIVE_AUDIT_BOOL_KEYS: frozenset[str] = _M311_NEGATIVE_AUDIT_BOOL_KEYS | frozenset(
    {
        "fx3_exposes_shading_auto_low",
        "fx6_has_switch_vh_af_area",
        "fx6_has_builtin_af_illuminator",
        "fx6_has_aperture_drive_pre_af_circ_color",
        "fx6_has_msdcf_or_star_rating",
        "fx3_has_eye_sensor",
        "fx3_has_finder_monitor_button",
        "fx6_uses_loupe_terminology",
        "fx6_has_still_flash_stack",
        "fx3_has_builtin_bnc_tc_in_out_switch",
        "fx3_bt_tc_link_present",
        "fx3_auto_framing_present",
        "fx3_bulb_timer_present",
        "fx3_auto_hdr_present",
        "fx3_in_camera_divide_extract_present",
        "fx3_physical_e_nd_present",
        "fx3_fan_control_max_present",
        "fx6_fan_control_max_present",
        "fx3_prioritize_rec_media_present",
        "fx3_movie_sort_recording_present",
        "fx3_mymenu_30_or_36_slots_only",
        "fx3_ftp_sftp_present",
        "fx3_ftp_active_mode_present",
        "fx3_ftp_transfer_jpeg_size_present",
        "fx3_in_body_focus_map_present",
        "fx3_uvc_streaming_present",
        "fx3_af_subj_shift_7_levels_present",
    }
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealHwMilestone324FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 Wave 58–61+ gates (G135..G142+) + persistent-write lock
    p1_bright_mon_shotmark_kwargs: Optional[Mapping[str, Any]] = None
    p1_tc_link_wifi_usblan_bulb_kwargs: Optional[Mapping[str, Any]] = None
    p1_big6_home_framing_interval_kwargs: Optional[Mapping[str, Any]] = None
    p1_tc_make_ssh_fan_kwargs: Optional[Mapping[str, Any]] = None
    p1_rec_media_autoswitch_proxy_kwargs: Optional[Mapping[str, Any]] = None
    p1_creators_cloud_mymenu_kwargs: Optional[Mapping[str, Any]] = None
    p1_ftp_ftpes_customwb_kwargs: Optional[Mapping[str, Any]] = None
    p1_movie_af_focusmap_marker_kwargs: Optional[Mapping[str, Any]] = None
    p1_request_persistent_writes: bool = False

    # P2 >= 56-pillar recovery master + cnflasha RO + zero-touch redlines
    p2_fault_inject_pillar: Optional[str] = None
    p2_cnflasha_write_unblocked_fault: bool = False
    p2_otp_fuse_touches_override: int = 0
    p2_rpmb_counter_increments_override: int = 0
    p2_passive_tx_bytes_override: int = 0
    p2_physical_usb_packets_override: int = 0
    p2_physical_device_writes_override: int = 0
    p2_raw_firmware_bytes_leaked_override: int = 0

    # P3 >= 45 firmware-lab auditors (#45 + forward-compat 46+)
    p3_filesettings_tcregen_reclamp_guard_fault: bool = False
    p3_raw_firmware_bytes_leaked_override: int = 0

    # P4 >= 66 VM HIL stages (Stages 63..66 + forward-compat 67+)
    p4_stage63_lens_comp_af_illum_folder_rating_faults: int = 0
    p4_stage64_switch_vh_stdadj_tcub_copy_faults: int = 0
    p4_stage65_touch_disp_zero_evf_interval_pb_faults: int = 0
    p4_stage66_dial_customize_mydial_fn_lut_embed_faults: int = 0
    p4_physical_device_writes_override: int = 0
    p4_raw_firmware_bytes_leaked_override: int = 0

    # P5 Tetradecuple 14/14 bench readiness preflights (Ph186..Ph321)
    p5_inject_p316_bright_mon_shotmark_big6_ssh_fault: bool = False
    p5_inject_p316_h0_h3_drift: bool = False
    p5_inject_p316_usb_packets_override: int = 0
    p5_inject_p316_passive_tx_bytes_override: int = 0
    p5_inject_p316_wireless_rf_packets_override: int = 0
    p5_inject_p321_rec_media_proxy_cloud_mymenu_ftpes_fault: bool = False
    p5_inject_p321_h0_h3_drift: bool = False
    p5_inject_p321_usb_packets_override: int = 0
    p5_inject_p321_passive_tx_bytes_override: int = 0
    p5_inject_p321_wireless_rf_packets_override: int = 0

    # P6 Rounds 28..65+ live QEMU kernel rehearsal & < 50 KiB PNG receipts
    p6_round_nop_override_num: Optional[int] = None
    p6_round_nop_count_override: Optional[int] = None
    p6_round_crash_override_num: Optional[int] = None
    p6_round_crashes_override: Optional[int] = None
    p6_round_emmc_override_num: Optional[int] = None
    p6_round_emmc_writes_override: Optional[int] = None
    p6_tamper_schema_round_num: Optional[int] = None
    p6_png_size_override_round_num: Optional[int] = None
    p6_png_size_override_bytes: Optional[int] = None
    p6_raw_firmware_bytes_leaked_override: int = 0

    # Optional upstream Milestone 311 fault injection pass-through
    m311_faults: Optional[RealHwMilestone311FaultInjection] = None


@dataclass(frozen=True)
class Milestone324PillarResult:
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
class RealHwMilestone324MasterGateReport:
    schema: str
    schema_version: str
    phase_version: str
    verification_mode: str
    all_pillars_milestone_ready: bool
    status: str
    o_rdonly_enforced: bool
    cnflasha_userspace_write_blocked: bool
    agent_auto_flash_blocked: bool
    cross_model_flash_authorized: bool
    overall_ready_for_hardware_attach: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    hardware_live_attachment_authorized: bool
    hardware_live_attachment_requirements: Tuple[str, ...]
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    e_nd_actuator_tx_count: int
    emmc_write_count: int
    rf_packets_transmitted: int
    slot1_data_sector_writes: int
    p8_cp_mutation_forbidden: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    cp_mutation_bytes: int
    wbi_mutation_bytes: int
    calibration_mutation_bytes: int
    usb_or_camera_operations: int
    otp_fuse_writes: int
    otp_fuse_touches: int
    rpmb_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes: int
    passive_tx_bytes_emitted: int
    temp_dir_cleaned: bool
    pillar_count: int
    passed_pillar_count: int
    failed_pillar_ids: Tuple[str, ...]
    pillars: Tuple[Milestone324PillarResult, ...]
    gate142_total_gates: int
    gate142_offline_verified: int
    gate142_simulated_verified: int
    gate142_all_verified: bool
    recovery_status: str
    recovery_pillar_count: int
    recovery_pillars_passed: int
    auditors_total: int
    auditors_passed: int
    firmware_lab_auditor_count: int
    firmware_lab_auditors_passed: int
    vm_stages_total: int
    vm_stages_passed: int
    vm_coemulation_stage_count: int
    vm_coemulation_stages_passed: int
    vm_physical_device_writes: int
    vm_raw_firmware_bytes_leaked: int
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
    p186_offline_go_no_go: str
    p186_sim_go_no_go: str
    p186_sim_gates_passed: int
    p186_card_insert_authorized: bool
    p186_h0_equals_h3_count: int
    p204_offline_go_no_go: str
    p204_sim_go_no_go: str
    p204_sim_groups_passed: int
    p204_hardware_live_attachment_authorized: bool
    p204_h0_equals_h3_count: int
    p204_e_nd_actuator_tx_count: int
    p216_offline_go_no_go: str
    p216_sim_go_no_go: str
    p216_sim_checklists_passed: int
    p216_hardware_live_attachment_authorized: bool
    p216_h0_equals_h3_count: int
    p227_offline_go_no_go: str
    p227_sim_go_no_go: str
    p227_sim_check_groups_passed: int
    p227_hardware_live_attachment_authorized: bool
    p227_h0_equals_h3_count: int
    p248_offline_go_no_go: str
    p248_sim_go_no_go: str
    p248_sim_check_groups_passed: int
    p248_hardware_live_attachment_authorized: bool
    p248_h0_equals_h3_count: int
    p261_offline_go_no_go: str
    p261_sim_go_no_go: str
    p261_sim_check_groups_passed: int
    p261_hardware_live_attachment_authorized: bool
    p261_h0_equals_h3_count: int
    p261_e_nd_uart_bytes_transmitted: int
    p275_offline_go_no_go: str
    p275_sim_go_no_go: str
    p275_sim_check_groups_passed: int
    p275_hardware_live_attachment_authorized: bool
    p275_h0_equals_h3_count: int
    p279_offline_go_no_go: str
    p279_sim_go_no_go: str
    p279_sim_check_groups_passed: int
    p279_hardware_live_attachment_authorized: bool
    p279_h0_equals_h3_count: int
    p284_offline_go_no_go: str
    p284_sim_go_no_go: str
    p284_sim_check_groups_passed: int
    p284_hardware_live_attachment_authorized: bool
    p284_h0_equals_h3_count: int
    p291_offline_go_no_go: str
    p291_sim_go_no_go: str
    p291_sim_check_groups_passed: int
    p291_hardware_live_attachment_authorized: bool
    p291_h0_equals_h3_count: int
    p302_offline_go_no_go: str
    p302_sim_go_no_go: str
    p302_sim_check_groups_passed: int
    p302_hardware_live_attachment_authorized: bool
    p302_h0_equals_h3_count: int
    p307_offline_go_no_go: str
    p307_sim_go_no_go: str
    p307_sim_check_groups_passed: int
    p307_hardware_live_attachment_authorized: bool
    p307_h0_equals_h3_count: int
    p307_wireless_rf_packets_emitted: int
    p307_slot1_data_sector_writes: int
    p316_offline_go_no_go: str
    p316_sim_go_no_go: str
    p316_sim_check_groups_passed: int
    p316_hardware_live_attachment_authorized: bool
    p316_h0_equals_h3_count: int
    p316_wireless_rf_packets_emitted: int
    p316_rf_packets_transmitted: int
    p316_e_nd_actuator_tx_count: int
    p316_slot1_data_sector_writes: int
    p321_offline_go_no_go: str
    p321_sim_go_no_go: str
    p321_sim_check_groups_passed: int
    p321_hardware_live_attachment_authorized: bool
    p321_h0_equals_h3_count: int
    p321_wireless_rf_packets_emitted: int
    p321_rf_packets_transmitted: int
    p321_e_nd_actuator_tx_count: int
    p321_slot1_data_sector_writes: int
    h0_equals_h3_count: int
    qemu_rounds_total: int
    qemu_rounds_verified: int
    qemu_runs_total: int
    qemu_runs_verified: int
    qemu_png_receipts_total: int
    qemu_png_receipts_verified: int
    qemu_png_max_bytes: int
    qemu_round_runs_by_round: Dict[str, int]
    qemu_real_kernel_nop_count: int
    qemu_real_kernel_crashes: int
    qemu_real_kernel_emmc_writes: int
    errors: Tuple[str, ...]
    milestone324_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class RealHwMilestone324VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone324_sha256: str
    observed_milestone324_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_milestone324_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `RealHwMilestone324MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone324_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------------------
# Dynamic Discovery Helpers (Forward-Compat >= Lower Bounds)
# ---------------------------------------------------------------------------


def _discover_highest_safety_gate_evaluator(
    safety_mod: Any = fx3_safety,
) -> Tuple[int, Callable[..., Any]]:
    """Discover highest `evaluate_<N>gate_preflight` in `fx3_safety` (`N >= 142`)."""
    best_n = 0
    best_fn: Optional[Callable[..., Any]] = None
    for attr in dir(safety_mod):
        m = _SAFETY_EVAL_RE.match(attr)
        if not m:
            continue
        n_val = int(m.group(1))
        if n_val >= 142 and n_val > best_n:
            cand = getattr(safety_mod, attr, None)
            if callable(cand):
                best_n = n_val
                best_fn = cand
    if best_fn is not None:
        return best_n, best_fn
    return 142, fx3_safety.evaluate_142gate_preflight


def _discover_highest_recovery_master(
    recovery_mod: Any = fx3_recovery,
) -> Tuple[int, Callable[..., Any], Tuple[str, ...]]:
    """Discover highest `evaluate_realhw_<M>pillar_recovery_master` (`M >= 56`)."""
    best_m = 0
    best_fn: Optional[Callable[..., Any]] = None
    for attr in dir(recovery_mod):
        m = _RECOVERY_EVAL_RE.match(attr)
        if not m:
            continue
        m_val = int(m.group(1))
        if m_val >= 56 and m_val > best_m:
            cand = getattr(recovery_mod, attr, None)
            if callable(cand):
                best_m = m_val
                best_fn = cand
    if best_fn is None:
        best_m = 56
        best_fn = fx3_recovery.evaluate_realhw_56pillar_recovery_master
    ids_raw = getattr(recovery_mod, f"MASTER_{best_m}_PILLAR_IDS", None)
    if ids_raw is None:
        ids_raw = getattr(recovery_mod, "MASTER_56_PILLAR_IDS", RECOVERY_56_PILLAR_IDS)
    return best_m, best_fn, tuple(str(x) for x in ids_raw)


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor)
# ---------------------------------------------------------------------------

_136GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_bright_mon_shotmark_kwargs", "bright_mon_shotmark_kwargs"),
    ("p1_tc_link_wifi_usblan_bulb_kwargs", "tc_link_wifi_usblan_bulb_kwargs"),
)
_138GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_big6_home_framing_interval_kwargs", "big6_home_framing_interval_kwargs"),
    ("p1_tc_make_ssh_fan_kwargs", "tc_make_ssh_fan_kwargs"),
)
_140GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_rec_media_autoswitch_proxy_kwargs", "rec_media_autoswitch_proxy_kwargs"),
    ("p1_creators_cloud_mymenu_kwargs", "creators_cloud_mymenu_kwargs"),
)
_142GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_ftp_ftpes_customwb_kwargs", "ftp_ftpes_customwb_kwargs"),
    ("p1_movie_af_focusmap_marker_kwargs", "movie_af_focusmap_marker_kwargs"),
)

_ALL_M324_P1_EXTRA_FIELDS: Tuple[Tuple[str, str], ...] = (
    *_136GATE_EXTRA_FAULT_FIELDS,
    *_138GATE_EXTRA_FAULT_FIELDS,
    *_140GATE_EXTRA_FAULT_FIELDS,
    *_142GATE_EXTRA_FAULT_FIELDS,
)


def _effective_m311_faults(
    faults: RealHwMilestone324FaultInjection,
) -> RealHwMilestone311FaultInjection:
    base = faults.m311_faults or RealHwMilestone311FaultInjection()
    need_p1 = faults.p1_request_persistent_writes and not base.p1_request_persistent_writes
    need_p3 = (
        faults.p3_filesettings_tcregen_reclamp_guard_fault
        and not base.p3_filesettings_tcregen_reclamp_guard_fault
    )
    if need_p1 or need_p3:
        d = asdict(base)
        if base.m295_faults is not None:
            d["m295_faults"] = base.m295_faults
        if need_p1:
            d["p1_request_persistent_writes"] = True
        if need_p3:
            d["p3_filesettings_tcregen_reclamp_guard_fault"] = True
        return RealHwMilestone311FaultInjection(**d)
    return base


def _fault_to_142gate_worker_dict(faults: RealHwMilestone324FaultInjection) -> Dict[str, Any]:
    m311_f = _effective_m311_faults(faults)
    out = _fault_to_134gate_worker_dict(m311_f)
    out["p1_request_persistent_writes"] = bool(
        out.get("p1_request_persistent_writes", False) or faults.p1_request_persistent_writes
    )
    for src_attr, _ in _ALL_M324_P1_EXTRA_FIELDS:
        val = getattr(faults, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    return out


def _build_master_140_chain_override(
    *,
    repo_root: Path,
    use_clean_room: bool,
    dry_run_sim: bool,
    req_persist: bool,
    fault_dict: Mapping[str, Any],
) -> Any:
    """Chain G1..G140 overrides cleanly when caller supplies pre-G141 fault kwargs."""
    up_to_134_kw: Dict[str, Any] = {}
    for src_attr, dst_kw in (
        *_66GATE_FAULT_FIELDS,
        *_72GATE_EXTRA_FAULT_FIELDS,
        *_78GATE_EXTRA_FAULT_FIELDS,
        *_90GATE_EXTRA_FAULT_FIELDS,
        *_96GATE_EXTRA_FAULT_FIELDS,
        *_102GATE_EXTRA_FAULT_FIELDS,
        *_124GATE_EXTRA_FAULT_FIELDS,
        *_134GATE_EXTRA_FAULT_FIELDS,
    ):
        val = fault_dict.get(src_attr)
        if val is not None:
            up_to_134_kw[dst_kw] = val

    m134_rep = fx3_safety.evaluate_134gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **up_to_134_kw,
    )
    kw136: Dict[str, Any] = {"master_134_override": m134_rep}
    for src_attr, dst_kw in _136GATE_EXTRA_FAULT_FIELDS:
        val = fault_dict.get(src_attr)
        if val is not None:
            kw136[dst_kw] = val
    m136_rep = fx3_safety.evaluate_136gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **kw136,
    )
    kw138: Dict[str, Any] = {"master_136_override": m136_rep}
    for src_attr, dst_kw in _138GATE_EXTRA_FAULT_FIELDS:
        val = fault_dict.get(src_attr)
        if val is not None:
            kw138[dst_kw] = val
    m138_rep = fx3_safety.evaluate_138gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **kw138,
    )
    kw140: Dict[str, Any] = {"master_138_override": m138_rep}
    for src_attr, dst_kw in _140GATE_EXTRA_FAULT_FIELDS:
        val = fault_dict.get(src_attr)
        if val is not None:
            kw140[dst_kw] = val
    return fx3_safety.evaluate_140gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **kw140,
    )


def _worker_142plus_gate_single(args: Tuple[str, bool, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, dry_run_sim, fault_dict = args
    repo_root = Path(repo_root_str)
    discovered_n, eval_fn = _discover_highest_safety_gate_evaluator()
    sig = inspect.signature(eval_fn)
    has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    req_persist = bool(fault_dict.get("p1_request_persistent_writes", False))

    kwargs: Dict[str, Any] = {"request_persistent_emmc_writes": req_persist}
    unsupported_upstream = False
    for src_attr, dst_kw in (
        *_66GATE_FAULT_FIELDS,
        *_72GATE_EXTRA_FAULT_FIELDS,
        *_78GATE_EXTRA_FAULT_FIELDS,
        *_90GATE_EXTRA_FAULT_FIELDS,
        *_96GATE_EXTRA_FAULT_FIELDS,
        *_102GATE_EXTRA_FAULT_FIELDS,
        *_124GATE_EXTRA_FAULT_FIELDS,
        *_134GATE_EXTRA_FAULT_FIELDS,
        *_136GATE_EXTRA_FAULT_FIELDS,
        *_138GATE_EXTRA_FAULT_FIELDS,
        *_140GATE_EXTRA_FAULT_FIELDS,
        *_142GATE_EXTRA_FAULT_FIELDS,
    ):
        val = fault_dict.get(src_attr)
        if val is not None:
            if has_varkw or dst_kw in sig.parameters:
                kwargs[dst_kw] = val
            else:
                unsupported_upstream = True

    if unsupported_upstream and "master_140_override" in sig.parameters:
        kwargs["master_140_override"] = _build_master_140_chain_override(
            repo_root=repo_root,
            use_clean_room=use_clean_room,
            dry_run_sim=dry_run_sim,
            req_persist=req_persist,
            fault_dict=fault_dict,
        )

    rep = eval_fn(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        **kwargs,
    )
    nested_g_valid, g71_end_tx = _extract_nested_g_valid_and_g71_end_tx(rep)
    s = rep.summary
    total_gates = int(s["total_gates"])
    offline_target = total_gates - 3
    offline_key = f"offline_{offline_target}_gates_verified"
    all_key = f"all_{total_gates}_gates_verified"
    chain_key = f"g13_to_g{total_gates}_all_passed"
    tail_key = f"g{total_gates - 1}_to_g{total_gates}_all_passed"

    return {
        "schema": rep.schema,
        "discovered_gate_count": discovered_n,
        "total_gates": total_gates,
        "verified_gates": int(s["verified_gates"]),
        "blocked_or_pending_gates": int(s["blocked_or_pending_gates"]),
        "offline_minus3_verified": bool(s.get(offline_key, False)),
        "all_n_gates_verified": bool(s.get(all_key, False)),
        "g13_to_gn_all_passed": bool(s.get(chain_key, False)),
        "gn_minus1_to_gn_all_passed": bool(s.get(tail_key, True)),
        "overall_ready_for_hardware_attach": bool(s["overall_ready_for_hardware_attach"]),
        "hardware_live_attachment_authorized": bool(
            s.get("hardware_live_attachment_authorized", False)
        ),
        "cross_model_flash_authorized": bool(s.get("cross_model_flash_authorized", False)),
        "agent_auto_flash_blocked": bool(s["agent_auto_flash_blocked"]),
        "human_hardware_attach_token": bool(s.get("human_hardware_attach_token", False)),
        "physical_flash_auto_exec_authorized": bool(
            s.get("physical_flash_auto_exec_authorized", False)
        ),
        "persistent_emmc_writes_authorized": bool(s["persistent_emmc_writes_authorized"]),
        "persistent_write_release": bool(s["persistent_write_release"]),
        "spi_nor_write_authorized": bool(s["spi_nor_write_authorized"]),
        "el3_payload_transmit_authorized": bool(s["el3_payload_transmit_authorized"]),
        "usb_packets_transmitted": int(s.get("usb_packets_transmitted", 0)),
        "physical_usb_packets_emitted": int(s.get("physical_usb_packets_emitted", 0)),
        "raw_firmware_bytes_leaked": int(s.get("raw_firmware_bytes_leaked", 0)),
        "g71_e_nd_actuator_tx_count": g71_end_tx,
        "nested_g_valid": nested_g_valid,
    }


def _normalize_56plus_pillar_fault_id(
    fault_id: Optional[str],
    pillar_ids: Tuple[str, ...] = RECOVERY_56_PILLAR_IDS,
) -> Optional[str]:
    if not fault_id:
        return None
    if fault_id in pillar_ids:
        return fault_id
    m = re.match(r"^pillar_(\d+)$", fault_id.strip().lower())
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(pillar_ids):
            return pillar_ids[idx]
    return fault_id


def _worker_recovery_56plus_pillar(args: Tuple[bool, Optional[str]]) -> Dict[str, Any]:
    use_clean_room, fault_pillar = args
    _, eval_fn, pillar_ids = _discover_highest_recovery_master()
    rep = eval_fn(
        force_clean_room=use_clean_room,
        fault_inject_pillar=_normalize_56plus_pillar_fault_id(fault_pillar, pillar_ids),
    )
    return rep.to_dict()


def _worker_phase316_321(
    args: Tuple[str, str, bool, Dict[str, Any], Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    fx6_str, fx3_str, use_clean_room, p316_faults, p321_faults = args
    fx6_dir = Path(fx6_str)
    fx3_dir = Path(fx3_str)

    rep316_off = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
    )
    kw316: Dict[str, Any] = {}
    if p316_faults.get("bright_mon_shotmark_big6_ssh"):
        kw316["dormant_divide_or_extract_requested"] = True
        kw316["wireless_rf_packets_emitted"] = 1
        kw316["e_nd_actuator_tx_count"] = 1
        kw316["shot_mark_write_requested"] = True
        kw316["shot_mark_slot"] = 1
    if p316_faults.get("h0_h3_drift"):
        kw316["simulated_h0_h3_drifted_surfaces"] = 1
    rep316_sim = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw316,
    )

    rep321_off = evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
    )
    kw321: Dict[str, Any] = {}
    if p321_faults.get("rec_media_proxy_cloud_mymenu_ftpes"):
        kw321["dormant_prioritize_rec_media_requested"] = True
        kw321["slot1_rec_write_requested"] = True
        kw321["wireless_rf_packets_emitted"] = 1
        kw321["e_nd_actuator_tx_count"] = 1
    if p321_faults.get("h0_h3_drift"):
        kw321["simulated_h0_h3_drifted_surfaces"] = 1
    rep321_sim = evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw321,
    )
    return (
        rep316_off.to_dict(),
        rep316_sim.to_dict(),
        rep321_off.to_dict(),
        rep321_sim.to_dict(),
    )


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1..P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
) -> Milestone324PillarResult:
    errors: List[str] = []
    off_total = int(raw_off["total_gates"])
    off_ver = int(raw_off["verified_gates"])
    sim_total = int(raw_sim["total_gates"])
    sim_ver = int(raw_sim["verified_gates"])

    if (
        off_total < 142
        or off_ver < off_total - 3
        or off_ver != off_total - 3
        or int(raw_off["blocked_or_pending_gates"]) != 3
        or raw_off["overall_ready_for_hardware_attach"] is not False
        or raw_off["hardware_live_attachment_authorized"] is not False
        or raw_off.get("cross_model_flash_authorized") is not False
        or not bool(raw_off.get("offline_minus3_verified", False))
    ):
        errors.append(
            f"p1_offline: expected {off_total - 3}/{off_total} (>=139/142, 3 Tier-0 gates fail-closed) "
            f"and hardware_attach=False, got {off_ver}/{off_total}"
        )

    if (
        sim_total < 142
        or sim_ver != sim_total
        or not bool(raw_sim.get("all_n_gates_verified", False))
        or not bool(raw_sim.get("g13_to_gn_all_passed", False))
        or not bool(raw_sim.get("gn_minus1_to_gn_all_passed", True))
        or raw_sim["overall_ready_for_hardware_attach"] is not False
        or raw_sim["hardware_live_attachment_authorized"] is not False
        or raw_sim.get("cross_model_flash_authorized") is not False
        or raw_sim["agent_auto_flash_blocked"] is not True
    ):
        errors.append(
            f"p1_simulated: expected {sim_total}/{sim_total} (>=142/142) with all_n_gates_verified=True "
            f"and hardware_attach=False, got {sim_ver}/{sim_total}"
        )

    for mode_tag, rmap in (("offline", raw_off), ("simulated", raw_sim)):
        if (
            rmap["persistent_emmc_writes_authorized"] is not False
            or rmap["persistent_write_release"] is not False
            or rmap["spi_nor_write_authorized"] is not False
            or rmap["el3_payload_transmit_authorized"] is not False
            or rmap.get("cross_model_flash_authorized", True) is not False
            or rmap.get("human_hardware_attach_token", False) is not False
            or rmap.get("physical_flash_auto_exec_authorized", False) is not False
            or int(rmap["usb_packets_transmitted"]) != 0
            or int(rmap["physical_usb_packets_emitted"]) != 0
            or int(rmap["raw_firmware_bytes_leaked"]) != 0
            or int(rmap["g71_e_nd_actuator_tx_count"]) != 0
        ):
            errors.append(
                f"p1_{mode_tag}: hard-locked zero-write / zero-cross-model-flash / zero-USB-TX / "
                f"zero-leak / zero-e-ND redline breached"
            )

    nested_sim: Mapping[str, bool] = raw_sim["nested_g_valid"]
    failed_gates = [g.upper() for g in sorted(nested_sim) if not nested_sim[g]]
    if failed_gates:
        errors.append(f"p1: real-hardware gates failed: {', '.join(failed_gates)}")
    if len(nested_sim) < (142 - 62):
        errors.append(
            f"p1: expected >=80 nested G63..G142+ gates, got {len(nested_sim)}"
        )

    passed = len(errors) == 0
    evidence = {
        "schema": raw_sim["schema"],
        "discovered_gate_count": int(raw_sim.get("discovered_gate_count", sim_total)),
        "offline_total_gates": off_total,
        "offline_verified_gates": off_ver,
        "simulated_total_gates": sim_total,
        "simulated_verified_gates": sim_ver,
        "all_142plus_gates_verified": bool(raw_sim.get("all_n_gates_verified", False)),
        "offline_ready_for_hardware_attach": raw_off["overall_ready_for_hardware_attach"],
        "simulated_ready_for_hardware_attach": raw_sim["overall_ready_for_hardware_attach"],
        "hardware_live_attachment_authorized": raw_sim["hardware_live_attachment_authorized"],
        "cross_model_flash_authorized": bool(raw_sim.get("cross_model_flash_authorized", True)),
        "agent_auto_flash_blocked": raw_sim["agent_auto_flash_blocked"],
        "persistent_emmc_writes_authorized": raw_sim["persistent_emmc_writes_authorized"],
        "spi_nor_write_authorized": raw_sim["spi_nor_write_authorized"],
        "el3_payload_transmit_authorized": raw_sim["el3_payload_transmit_authorized"],
        "usb_packets_transmitted": int(raw_sim["usb_packets_transmitted"]),
        "raw_firmware_bytes_leaked": int(raw_sim["raw_firmware_bytes_leaked"]),
        "g71_e_nd_actuator_tx_count": raw_sim["g71_e_nd_actuator_tx_count"],
        "g63_to_gn_valid": dict(nested_sim),
    }
    return Milestone324PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_142PLUS_GATE_REALHW_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"142+-Gate Safety: offline={off_ver}/{off_total} (3 Tier-0 gates fail-closed), "
            f"simulated={sim_ver}/{sim_total} (G63..G{sim_total} Waves 21-61+, "
            f"cross_model_flash={raw_sim.get('cross_model_flash_authorized')}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    rec_56plus: Mapping[str, Any],
    faults: RealHwMilestone324FaultInjection,
) -> Tuple[Milestone324PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    p_count = int(rec_56plus.get("pillar_count", 0))
    p_passed = int(rec_56plus.get("pillars_passed", 0))
    rec_status = str(rec_56plus.get("status", ""))

    cnflasha_blocked = bool(rec_56plus.get("cnflasha_userspace_write_blocked", False)) and not bool(
        faults.p2_cnflasha_write_unblocked_fault
    )
    otp = (
        max(
            int(rec_56plus.get("otp_fuse_writes", 0) or 0),
            int(rec_56plus.get("otp_fuse_touches", -1)),
        )
        + int(faults.p2_otp_fuse_touches_override)
    )
    rpmb = int(rec_56plus.get("rpmb_counter_increments", -1)) + int(
        faults.p2_rpmb_counter_increments_override
    )
    ptx = int(rec_56plus.get("passive_tx_bytes_emitted", -1)) + int(
        faults.p2_passive_tx_bytes_override
    )
    usb_pkts = int(rec_56plus.get("physical_usb_packets_emitted", -1)) + int(
        faults.p2_physical_usb_packets_override
    )
    dev_writes = int(rec_56plus.get("physical_device_writes", -1)) + int(
        faults.p2_physical_device_writes_override
    )
    leaked = int(rec_56plus.get("raw_firmware_bytes_leaked", -1)) + int(
        faults.p2_raw_firmware_bytes_leaked_override
    )

    p56_required_subkeys = (
        "pillar56_a_switch_vh_af_focus_limit_color_vault",
        "pillar56_b_exposure_std_tcub_reverse_copy_vault",
    )
    p55_optional_subkeys = (
        "pillar55_a_lens_comp_af_illuminator_vault",
        "pillar55_b_aperture_drive_folder_rating_vault",
    )
    sub_ok = True
    for sub_k in p56_required_subkeys:
        sub_obj = rec_56plus.get(sub_k, {})
        if p_count > 56 and not sub_obj:
            continue
        if not (isinstance(sub_obj, Mapping) and bool(sub_obj.get("passed"))):
            sub_ok = False
    for sub_k in p55_optional_subkeys:
        if sub_k in rec_56plus:
            sub_obj = rec_56plus.get(sub_k, {})
            if not (isinstance(sub_obj, Mapping) and bool(sub_obj.get("passed"))):
                sub_ok = False

    expected_status = f"VERIFIED_{p_count}OF{p_count}_PILLAR_RECOVERY_MASTER"
    status_ok = rec_status == expected_status and p_count >= 56 and p_passed == p_count
    pillars_seq = rec_56plus.get("pillars", ())
    pillars_items_ok = isinstance(pillars_seq, Sequence) and len(pillars_seq) >= 56 and all(
        isinstance(item, Mapping) and bool(item.get("passed")) for item in pillars_seq
    )

    if (
        not bool(rec_56plus.get("all_passed"))
        or not status_ok
        or not pillars_items_ok
        or p_count < 56
        or p_passed < 56
        or p_passed != p_count
        or not sub_ok
    ):
        errors.append(
            f"p2_56plus_pillar: expected >=56/56 {expected_status}, "
            f"got {p_passed}/{p_count} (status={rec_status!r}, p55_56_sub={sub_ok})"
        )

    zero_violation_keys = (
        # Pillars 45..54 zero-violation counters
        "double_log_or_lockout_bypass_events",
        "pplut_1080p_clamp_bypass_events",
        "pp_internal_reset_trap_violations",
        "fx6_baselook_confusion_events",
        "wb_cine_ei_awb_or_custom_setup_trap_events",
        "wb_custom_camset_exclusion_drift_events",
        "metering_desqueeze_or_cine_ei_base_iso_drift_events",
        "nouvc_spoof_events",
        "usb_host_data_enumeration_events",
        "hdmi_lcd_blanking_violations",
        "hdmi_log_1080_bypass_events",
        "slot1_protect_only_vault_violations",
        "slot1_vault_format_or_delete_events",
        "slot1_vault_mutation_bytes",
        "network_reset_zero_rf_violations",
        "legacy_power_save_monitor_spoof_events",
        "unsafe_power_save_sleep_interference_events",
        "bk_lang_parity_drift_events",
        "stage_b_4lang_uxc_ltt_drift_events",
        "xlrh1_acoustic_feedback_violations",
        "audio_mon_4ch_hdmi_confusion_events",
        "destructive_delete_confirm_drift_events",
        "slot1_vault_delete_events",
        "e_nd_actuator_tx_count",
        "af_area_reg_lock_or_reset_drift_events",
        "camset_cross_model_path_drift_events",
        "colorspace_adobergb_prefix_violations",
        "dci4k_long_gop_or_8k_violations",
        "dormant_lossless_raw_exposure_events",
        "electronic_silent_5lock_bypass_events",
        "ev_comp_range_or_cine_ei_lockout_violations",
        "exposure_step_or_dormant_reset_ev_drift_events",
        "flash_still_mech_gate_violations",
        "focus_mode_movie_clamp_or_dormant_drift_events",
        "fx6_handle_or_pos_display_conflation_events",
        "fx6_ibis_shake_conflation_events",
        "fx6_mechanical_shutter_conflation_events",
        "fx6_still_or_raw_conflation_events",
        "fx6_still_pipeline_conflation_events",
        "hdmi_raw_or_still_aspect_drift_events",
        "hlg_still_prereq_or_lockout_drift_events",
        "image_index_dormant_or_view_mode_drift_events",
        "iso_minss_or_cine_ei_lock_drift_events",
        "mishoe_pmic_5v_overcurrent_events",
        "movie_tracking_area_or_limit_violations",
        "nr_or_drive_burst_wall_violations",
        "photo_capture_dci4k_lockout_bypass_events",
        "priority_set_or_illuminator_gate_violations",
        "reboot_2400p_stage_b_wipe_violations",
        "reg_custom_hold_or_hlg_lock_drift_events",
        "sensor_cleaning_low_battery_bypass_events",
        "sensor_cleaning_no_power_off_violations",
        "shutter_type_auto_spoof_events",
        "slot1_camset_write_bytes",
        "slot1_data_sector_writes",
        "slot1_flash_videolight_imagedb_bytes",
        "slot1_focus_zoom_camset_mutation_bytes",
        "slot1_imagedb_or_burst_mutation_bytes",
        "slot1_photo_capture_write_bytes",
        "slot1_rotate_exif_mutation_bytes",
        "slot1_still_capture_or_sort_write_bytes",
        "xlrh1_zoom_or_hold_spoof_events",
        # Pillars 55..56 zero-violation counters
        "dormant_shading_auto_low_exposure_events",
        "lens_comp_lock_or_arw_conflation_events",
        "af_illuminator_gate_or_fx6_spoof_events",
        "aperture_drive_pre_af_shutter_reset_drift_events",
        "circ_focus_diagonal_or_color_drift_events",
        "focus_area_color_or_fx6_spoof_events",
        "folder_name_or_leading_underscore_violations",
        "slot1_folder_dir_mutation_bytes",
        "slot1_rating_avf_info_mutation_bytes",
        "switch_vh_af_lockout_or_coords_drift_events",
        "focus_limit_lt2_or_dormant_symbol_events",
        "exp_std_adj_mode_conflation_or_reset_drift_events",
        "bracket_settings_reset_or_fx6_spoof_events",
        "tcub_reset_wipe_or_format_lock_violations",
        "reverse_copy_slot2_to_slot1_bypass_events",
        "slot1_copy_avf_info_mutation_bytes",
    )
    violations_nonzero = any(int(rec_56plus.get(vk, 0)) != 0 for vk in zero_violation_keys)

    if (
        cnflasha_blocked is not True
        or otp != 0
        or rpmb != 0
        or ptx != 0
        or usb_pkts != 0
        or dev_writes != 0
        or leaked != 0
        or violations_nonzero
        or rec_56plus.get("slot1_format_hard_locked", True) is not True
        or rec_56plus.get("slot1_vault_erofs_ebusy_enforced", True) is not True
        or rec_56plus.get("fx3_has_var_shutter", False) is not False
        or rec_56plus.get("fx3_has_builtin_evf", False) is not False
        or rec_56plus.get("fx3_has_builtin_end_filter", False) is not False
        or rec_56plus.get("fx3_exposes_shading_auto_low", False) is not False
        or rec_56plus.get("fx3_has_physical_bnc_tc_port", False) is not False
        or rec_56plus.get("fx6_has_switch_vh_af_area", False) is not False
        or rec_56plus.get("fx6_has_builtin_af_illuminator", False) is not False
        or rec_56plus.get("fx6_has_aperture_drive_pre_af_circ_color", False) is not False
        or rec_56plus.get("fx6_has_msdcf_or_star_rating", False) is not False
        or rec_56plus.get("fx6_has_exp_std_adj", False) is not False
        or rec_56plus.get("fx6_has_focus_area_limit", False) is not False
        or rec_56plus.get("hardware_live_attachment_authorized", False) is not False
        or rec_56plus.get("el3_payload_transmit_authorized", False) is not False
        or rec_56plus.get("isp_write_authorized", False) is not False
        or rec_56plus.get("cross_model_flash_authorized", False) is not False
        or rec_56plus.get("overall_ready_for_hardware_attach", False) is not False
        or rec_56plus.get("fx3_has_physical_ev_reset_dial", False) is not False
        or rec_56plus.get("fx3_ui_exposes_lossless_raw", False) is not False
        or rec_56plus.get("fx3_ui_exposes_shutter_type_auto", False) is not False
        or rec_56plus.get("fx3_appfw_has_pro_camera_path", False) is not False
        or rec_56plus.get("xlrh1_has_rec_button", False) is not False
        or rec_56plus.get("xlrh1_has_zoom_hold_switch", False) is not False
        or rec_56plus.get("xlrh1_has_zoom_lever", False) is not False
        or rec_56plus.get("fx6_has_still_pipeline_present", False) is not False
        or rec_56plus.get("fx6_still_pipeline_present", False) is not False
        or rec_56plus.get("fx6_mechanical_shutter_present", False) is not False
    ):
        errors.append(
            "p2: cnflasha RO / zero-touch OTP-RPMB-passive-USB-eND / FX3-vs-FX6 boundary / "
            "Slot1 Tier0-RO redline breached"
        )

    passed = len(errors) == 0
    master_sha_key = f"master_{p_count}pillar_sha256"
    master_sha = rec_56plus.get(master_sha_key) or rec_56plus.get("master_56pillar_sha256")
    evidence = {
        "schema": rec_56plus.get("schema", ""),
        "status": rec_status,
        "pillar_count": p_count,
        "pillars_passed": p_passed,
        "all_passed": bool(rec_56plus.get("all_passed")),
        "cnflasha_userspace_write_blocked": cnflasha_blocked,
        "fx3_has_builtin_evf": rec_56plus.get("fx3_has_builtin_evf", False),
        "fx3_has_builtin_end_filter": rec_56plus.get("fx3_has_builtin_end_filter", False),
        "fx3_has_builtin_af_illuminator": rec_56plus.get("fx3_has_builtin_af_illuminator", True),
        "fx3_has_switch_vh_af_area": rec_56plus.get("fx3_has_switch_vh_af_area", True),
        "otp_fuse_writes": otp,
        "rpmb_writes": rpmb,
        "passive_tx_bytes": ptx,
        "physical_usb_packets_emitted": usb_pkts,
        "physical_device_writes": dev_writes,
        "raw_firmware_bytes_leaked": leaked,
        "master_recovery_sha256": master_sha,
    }
    pillar = Milestone324PillarResult(
        pillar_id="P2",
        pillar_name="FIFTY_SIX_PLUS_PILLAR_RECOVERY_MASTER_VAULT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Recovery Master {p_passed}/{p_count} pillars (>=56 required; Pillars 55..56 "
            f"ShadingComp-AFIlluminator-FolderRating-SwitchVH-ExpStdAdj-TCUB-ReverseCopySlot1), "
            f"cnflasha_ro={cnflasha_blocked}, OTP={otp}, RPMB={rpmb}, passive_tx={ptx} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "recovery_status": rec_status,
        "recovery_pillar_count": p_count,
        "recovery_pillars_passed": p_passed,
        "cnflasha_userspace_write_blocked": cnflasha_blocked,
        "otp_fuse_writes": otp,
        "rpmb_writes": rpmb,
        "passive_tx_bytes": ptx,
        "physical_usb_packets_emitted": usb_pkts,
        "physical_device_writes": dev_writes,
        "raw_firmware_bytes_leaked": leaked,
    }
    return pillar, meta


def _evaluate_pillar_3(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: RealHwMilestone324FaultInjection,
) -> Tuple[Milestone324PillarResult, Dict[str, Any]]:
    m311_f = _effective_m311_faults(faults)
    m295_f = m311_f.m295_faults or RealHwMilestone295FaultInjection()
    if m311_f.p3_filesettings_tcregen_reclamp_guard_fault and not m295_f.p3_filesettings_tcregen_reclamp_guard_fault:
        d = asdict(m295_f)
        d["p3_filesettings_tcregen_reclamp_guard_fault"] = True
        m295_f = RealHwMilestone295FaultInjection(**d)
    m295_p3, meta = _eval_m295_p3(auditors, m295_f)
    errors: List[str] = list(m295_p3.errors)
    extra_leak = int(faults.p3_raw_firmware_bytes_leaked_override)
    total_leaked = int(meta["raw_firmware_bytes_leaked"]) + extra_leak
    if extra_leak != 0:
        msg = f"p3: raw_firmware_bytes_leaked={total_leaked} != 0"
        if msg not in errors:
            errors.append(msg)
    evidence = dict(m295_p3.evidence)
    evidence["raw_firmware_bytes_leaked"] = total_leaked
    meta = dict(meta)
    meta["raw_firmware_bytes_leaked"] = total_leaked
    passed = (
        len(errors) == 0
        and int(meta["passed_count"]) >= 45
        and int(meta["passed_count"]) == int(meta["auditor_count"])
        and total_leaked == 0
        and int(meta["e_nd_actuator_tx_count"]) == 0
        and int(meta["calibration_mutation_bytes"]) == 0
    )
    pillar = Milestone324PillarResult(
        pillar_id="P3",
        pillar_name="FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=m295_p3.summary if extra_leak == 0 else f"p3 raw_firmware_bytes_leaked={total_leaked} FAIL_CLOSED",
        evidence=evidence,
        errors=tuple(errors),
    )
    return pillar, meta


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: RealHwMilestone324FaultInjection,
) -> Tuple[Milestone324PillarResult, Dict[str, Any]]:
    m311_f = _effective_m311_faults(faults)
    m311_p4, meta_62 = _eval_m311_p4(vm_rep, m311_f)
    errors: List[str] = [
        e for e in m311_p4.errors if not e.startswith("p4: expected >= 62 VM stages")
    ]
    stage_statuses: Dict[str, bool] = dict(m311_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_66_STAGE_KEYS[62:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if (
            not ok
            and f"p4: forward-compat VM stage {skey} failed" not in errors
            and f"p4: VM co-emulation {skey} failed" not in errors
        ):
            errors.append(f"p4: VM co-emulation {skey} failed")

    stage63_to_66_specs: Tuple[Tuple[str, str, str, Tuple[str, ...], int], ...] = (
        (
            "stage63_realhw_lens_comp_af_illuminator_folder_rating_hil",
            "63/63",
            "phase309_audit_digest_sha256",
            (
                "dormant_shading_auto_low_exposed_events",
                "steadyshot_active_distortion_bypass_events",
                "af_illuminator_non_afs_or_silent_fire_events",
                "initialize_only_af_reset_wipe_events",
                "diagonal_focus_point_wrap_events",
                "slot1_data_sector_writes",
                "slot1_vault_folder_or_rating_mutation_bytes",
            ),
            int(faults.p4_stage63_lens_comp_af_illum_folder_rating_faults),
        ),
        (
            "stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil",
            "64/64",
            "phase312_audit_digest_sha256",
            (
                "switch_vh_af_non_afc_or_invalid_pitch_bypass_events",
                "focus_area_limit_lt2_or_dormant_alpha_exposed_events",
                "exposure_std_adj_reset_wipe_or_missing_5th_mode_events",
                "bracket_movie_sq_or_fx6_bypass_events",
                "tc_format_2398p_24p_or_pal_df_violation_events",
                "slot1_data_sector_writes",
                "slot1_vault_copy_reverse_direction_mutation_bytes",
                "reverse_copy_slot2_to_slot1_vault_bypass_events",
            ),
            int(faults.p4_stage64_switch_vh_stdadj_tcub_copy_faults),
        ),
        (
            "stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil",
            "65/65",
            "phase315_audit_digest_sha256",
            (
                "dormant_touch_shutter_ae_pad_footer_exposed_events",
                "zero_evf_finder_monitor_blackout_trap_events",
                "still_only_ael_flash_movie_sq_bypass_events",
                "sync_cord_external_flash_bypass_events",
                "interval_play_speed_out_of_1_9_range_events",
                "dormant_beauty_effect_or_trimming_exposed_events",
                "slot1_data_sector_writes",
                "slot1_vault_pb_edit_mutation_bytes",
            ),
            int(faults.p4_stage65_touch_disp_zero_evf_interval_pb_faults),
        ),
        (
            "stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil",
            "66/66",
            "phase318_audit_digest_sha256",
            (
                "dormant_dial_setup_or_rear_dial_lr_exposed_events",
                "mydial_lock_override_failures",
                "fn_menu_still_movie_12x2_leak_events",
                "live_view_movie_sq_bypass_events",
                "grid_line_hdmi_clean_feed_leaked_pixels",
                "embed_lut_sd_sdhc_lock_bypass_events",
                "pplut_non_reset_or_metadata_confusion_events",
                "slot1_data_sector_writes",
                "slot1_vault_lut_mutation_bytes",
            ),
            int(faults.p4_stage66_dial_customize_mydial_fn_lut_embed_faults),
        ),
    )

    extra_emmc = 0
    extra_wf12 = 0
    for skey, exp_milestone, digest_key, fault_counters, injected in stage63_to_66_specs:
        sobj = vm_rep.get(skey, {})
        if isinstance(sobj, Mapping):
            extra_emmc += max(0, int(sobj.get("emmc_mutation_bytes", 0)))
            extra_wf12 += max(0, int(sobj.get("wf12_00342260_hits", 0)))
        counter_sum = injected + sum(
            int(sobj.get(ck, -1)) if isinstance(sobj, Mapping) else -1 for ck in fault_counters
        )
        milestone_ok = isinstance(sobj, Mapping) and sobj.get("milestone") == exp_milestone
        digest_val = sobj.get(digest_key, "") if isinstance(sobj, Mapping) else ""
        digest_ok = isinstance(digest_val, str) and len(digest_val) == 64
        avf_ok = isinstance(sobj, Mapping) and sobj.get("slot1_avf_info_mutated") is False
        if (
            not _check_vm_stage45_to_47_redlines(sobj)
            or not avf_ok
            or counter_sum != 0
            or not milestone_ok
            or not digest_ok
        ):
            errors.append(
                f"p4: {skey} redlines/milestone ({exp_milestone})/digest violated (fault_sum={counter_sum})"
            )
            stage_statuses[skey] = False

    # Enforce Zero-EVF flags on stage65 and 3-dial truth on stage66
    s65 = vm_rep.get("stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil", {})
    if isinstance(s65, Mapping) and any(
        s65.get(k, False) is not False
        for k in (
            "fx3_has_builtin_evf",
            "fx3_has_eye_sensor",
            "fx3_has_finder_monitor_button",
            "fx6_has_builtin_evf",
            "fx6_has_still_flash_stack",
        )
    ):
        errors.append("p4: stage65 Zero-EVF / still-flash FX3-vs-FX6 redline violated")
        stage_statuses["stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil"] = False

    s66 = vm_rep.get("stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil", {})
    if isinstance(s66, Mapping) and int(s66.get("fx3_physical_dial_count", -1)) != 3:
        errors.append("p4: stage66 fx3_physical_dial_count must equal 3")
        stage_statuses["stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil"] = False

    vm_raw_leaked = int(meta_62.get("raw_firmware_bytes_leaked", 0)) + int(
        faults.p4_raw_firmware_bytes_leaked_override
    )
    vm_phys_writes = int(meta_62.get("physical_device_writes", 0)) + int(
        faults.p4_physical_device_writes_override
    )
    vm_stages_total = len(stage_statuses)
    vm_stages_passed = sum(1 for v in stage_statuses.values() if v)
    emmc_corruptions = int(meta_62.get("emmc_corruptions", 0)) + extra_emmc
    total_wf12_hits = int(meta_62.get("wf12_00342260_hits", 0)) + extra_wf12
    total_end_tx = int(meta_62.get("e_nd_actuator_tx_count", 0))

    if not (vm_stages_passed >= 66 and vm_stages_passed == vm_stages_total):
        errors.append(
            f"p4: expected >= 66 VM stages and all passing, got {vm_stages_passed}/{vm_stages_total}"
        )
    if vm_raw_leaked != 0:
        msg = f"p4: raw_firmware_bytes_leaked={vm_raw_leaked} != 0"
        if msg not in errors:
            errors.append(msg)
    if vm_phys_writes != 0:
        msg = f"p4: physical_device_writes={vm_phys_writes} != 0"
        if msg not in errors:
            errors.append(msg)
    if emmc_corruptions != 0:
        msg = f"p4: emmc_corruptions={emmc_corruptions} != 0"
        if msg not in errors:
            errors.append(msg)

    passed = len(errors) == 0
    evidence = dict(m311_p4.evidence)
    evidence.update(
        {
            "vm_stages_total": vm_stages_total,
            "vm_stages_passed": vm_stages_passed,
            "stage_count": vm_stages_total,
            "passed_count": vm_stages_passed,
            "passed_stage_count": vm_stages_passed,
            "stage_statuses": stage_statuses,
            "raw_firmware_bytes_leaked": vm_raw_leaked,
            "physical_device_writes": vm_phys_writes,
            "emmc_corruptions": emmc_corruptions,
            "wf12_00342260_hits": total_wf12_hits,
            "e_nd_actuator_tx_count": total_end_tx,
            "stage63_digest_sha256": vm_rep.get(
                "stage63_realhw_lens_comp_af_illuminator_folder_rating_hil", {}
            ).get("phase309_audit_digest_sha256"),
            "stage64_digest_sha256": vm_rep.get(
                "stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil", {}
            ).get("phase312_audit_digest_sha256"),
            "stage65_digest_sha256": vm_rep.get(
                "stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil", {}
            ).get("phase315_audit_digest_sha256"),
            "stage66_digest_sha256": vm_rep.get(
                "stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil", {}
            ).get("phase318_audit_digest_sha256"),
            "stage66_milestone": vm_rep.get(
                "stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil", {}
            ).get("milestone"),
        }
    )
    pillar = Milestone324PillarResult(
        pillar_id="P4",
        pillar_name="SIXTY_SIX_PLUS_STAGE_VM_HIL_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {vm_stages_passed}/{vm_stages_total} stages (>=66 required; Stages 63..66 "
            f"ShadingComp-AFIllum-SwitchVH-ReverseCopy-ZeroEVF-DialCustomize-LUTEmbed), "
            f"phys_writes={vm_phys_writes}, leaked={vm_raw_leaked}B, emmc_corruptions={emmc_corruptions} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_62)
    meta.update(
        {
            "stage_count": vm_stages_total,
            "passed_count": vm_stages_passed,
            "raw_firmware_bytes_leaked": vm_raw_leaked,
            "physical_device_writes": vm_phys_writes,
            "emmc_corruptions": emmc_corruptions,
            "wf12_00342260_hits": total_wf12_hits,
            "e_nd_actuator_tx_count": total_end_tx,
        }
    )
    return pillar, meta


def _check_phase321_bench_verifier(
    *,
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
    errors: List[str],
    extra_usb_override: int = 0,
    extra_passive_override: int = 0,
) -> Dict[str, Any]:
    """Verify Phase 321 (14th preflight) offline & dry-run semantics cleanly."""
    off_dict = copy.deepcopy(dict(raw_off))
    v_off = verify_phase321_report(off_dict)
    off_ready = bool(off_dict.get("overall_ready_for_hardware_attach", False))
    if (
        not v_off.valid
        or off_dict.get("go_no_go") != GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        or off_dict.get("hardware_live_attachment_authorized") is not False
        or off_ready is not False
        or off_dict.get("tier0_receipt_verified") is not False
        or int(off_dict.get("check_groups_passed", -1)) != 4
        or int(off_dict.get("check_group_count", -1)) != 4
        or off_dict.get("sd_physical_media_written") is not False
        or int(off_dict.get("usb_packets_transmitted", -1)) != 0
        or int(off_dict.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(off_dict.get("passive_tx_bytes_emitted", -1)) != 0
    ):
        errors.append(
            f"p5_p321_off: expected {GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT} "
            f"(got {off_dict.get('go_no_go')}, valid={v_off.valid}, errs={v_off.errors})"
        )

    sim_dict = copy.deepcopy(dict(raw_sim))
    if extra_usb_override:
        sim_dict["usb_packets_transmitted"] = int(
            sim_dict.get("usb_packets_transmitted", 0)
        ) + int(extra_usb_override)
    if extra_passive_override:
        sim_dict["passive_tx_bytes_emitted"] = int(
            sim_dict.get("passive_tx_bytes_emitted", 0)
        ) + int(extra_passive_override)

    v_sim = verify_phase321_report(sim_dict)
    sim_passed = int(sim_dict.get("check_groups_passed", -1))
    sim_pkts = int(sim_dict.get("usb_packets_transmitted", -1))
    sim_leaked = int(sim_dict.get("raw_firmware_bytes_leaked", -1))
    sim_passive = int(sim_dict.get("passive_tx_bytes_emitted", -1))
    sim_h0_h3 = int(sim_dict.get("h0_equals_h3_count", -1))
    sim_ready = bool(sim_dict.get("overall_ready_for_hardware_attach", False))
    all_cgs_ok = all(
        isinstance(sim_dict.get(gk), Mapping) and bool(sim_dict[gk].get("passed"))
        for gk in ("check_group_a", "check_group_b", "check_group_c", "check_group_d")
    )

    if (
        not v_sim.valid
        or sim_dict.get("go_no_go") != GO_NO_GO_DRY_RUN_SIMULATED_READY
        or int(sim_dict.get("check_group_count", -1)) != 4
        or sim_passed != 4
        or not all_cgs_ok
        or not bool(sim_dict.get("tier0_receipt_verified"))
        or sim_dict.get("hardware_live_attachment_authorized") is not False
        or sim_ready is not False
        or sim_dict.get("sd_physical_media_written") is not False
        or sim_h0_h3 != 16
        or sim_pkts != 0
        or sim_leaked != 0
        or sim_passive != 0
        or sim_dict.get("persistent_emmc_writes_authorized") is not False
        or sim_dict.get("spi_nor_write_authorized") is not False
        or sim_dict.get("el3_payload_transmit_authorized") is not False
    ):
        errors.append(
            f"p5_p321_sim: simulated dry-run failed "
            f"(go={sim_dict.get('go_no_go')}, groups={sim_passed}/4, valid={v_sim.valid}, errs={v_sim.errors})"
        )

    return {
        "p321_offline_go_no_go": str(off_dict.get("go_no_go", "")),
        "p321_offline_check_groups_passed": int(off_dict.get("check_groups_passed", 0)),
        "p321_offline_report_verified": bool(v_off.valid),
        "p321_sim_go_no_go": str(sim_dict.get("go_no_go", "")),
        "p321_sim_check_groups_passed": sim_passed,
        "p321_hardware_live_attachment_authorized": bool(
            sim_dict.get("hardware_live_attachment_authorized", True)
        ),
        "p321_h0_equals_h3_count": sim_h0_h3,
        "p321_sim_usb_packets_transmitted": sim_pkts,
        "p321_sim_raw_firmware_bytes_leaked": sim_leaked,
        "p321_sim_passive_tx_bytes_emitted": sim_passive,
        "p321_sim_report_verified": bool(v_sim.valid),
        "p321_sim_report_sha256": str(sim_dict.get("report_sha256", "")),
        "_any_attach_ready": bool(off_ready or sim_ready),
    }


def _evaluate_pillar_5(
    raw_p136: Mapping[str, Any],
    raw_p143: Mapping[str, Any],
    raw_p154: Mapping[str, Any],
    raw_p186_off: Mapping[str, Any],
    raw_p186_sim: Mapping[str, Any],
    raw_p204_off: Mapping[str, Any],
    raw_p204_sim: Mapping[str, Any],
    raw_p216_off: Mapping[str, Any],
    raw_p216_sim: Mapping[str, Any],
    raw_p227_off: Mapping[str, Any],
    raw_p227_sim: Mapping[str, Any],
    raw_p248_off: Mapping[str, Any],
    raw_p248_sim: Mapping[str, Any],
    raw_p261_off: Mapping[str, Any],
    raw_p261_sim: Mapping[str, Any],
    raw_p275_off: Mapping[str, Any],
    raw_p275_sim: Mapping[str, Any],
    raw_p279_off: Mapping[str, Any],
    raw_p279_sim: Mapping[str, Any],
    raw_p284_off: Mapping[str, Any],
    raw_p284_sim: Mapping[str, Any],
    raw_p291_off: Mapping[str, Any],
    raw_p291_sim: Mapping[str, Any],
    raw_p302_off: Mapping[str, Any],
    raw_p302_sim: Mapping[str, Any],
    raw_p307_off: Mapping[str, Any],
    raw_p307_sim: Mapping[str, Any],
    raw_p316_off: Mapping[str, Any],
    raw_p316_sim: Mapping[str, Any],
    raw_p321_off: Mapping[str, Any],
    raw_p321_sim: Mapping[str, Any],
    faults: RealHwMilestone324FaultInjection,
) -> Tuple[Milestone324PillarResult, Dict[str, Any]]:
    m311_p5, meta_p5_311 = _eval_m311_p5(
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
        raw_p216_off,
        raw_p216_sim,
        raw_p227_off,
        raw_p227_sim,
        raw_p248_off,
        raw_p248_sim,
        raw_p261_off,
        raw_p261_sim,
        raw_p275_off,
        raw_p275_sim,
        raw_p279_off,
        raw_p279_sim,
        raw_p284_off,
        raw_p284_sim,
        raw_p291_off,
        raw_p291_sim,
        raw_p302_off,
        raw_p302_sim,
        raw_p307_off,
        raw_p307_sim,
        _effective_m311_faults(faults),
    )
    errors: List[str] = [
        e
        for e in m311_p5.errors
        if e != "p5: overall_ready_for_hardware_attach must remain False across all 12 verifiers"
    ]

    info_316 = _check_4group_bench_verifier(
        tag="p316",
        raw_off=raw_p316_off,
        raw_sim=raw_p316_sim,
        verify_fn=verify_phase316_report,
        cg_keys=(
            "check_group_a_bright_monitoring_lcd_shotmark",
            "check_group_b_zero_bt_tclink_wifi_usblan_airplane",
            "check_group_c_big6_home_manual_nd_framing_interval",
            "check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0",
        ),
        errors=errors,
        extra_usb_override=faults.p5_inject_p316_usb_packets_override,
        extra_passive_override=faults.p5_inject_p316_passive_tx_bytes_override,
    )
    p316_wrf = int(raw_p316_sim.get("wireless_rf_packets_emitted", -1)) + int(
        faults.p5_inject_p316_wireless_rf_packets_override
    )
    p316_rf = int(raw_p316_sim.get("rf_packets_transmitted", -1)) + int(
        faults.p5_inject_p316_wireless_rf_packets_override
    )
    p316_end = int(raw_p316_sim.get("e_nd_actuator_tx_count", -1))
    p316_slot1 = int(raw_p316_sim.get("slot1_data_sector_writes", -1))
    if (
        p316_wrf != 0
        or p316_rf != 0
        or p316_end != 0
        or p316_slot1 != 0
        or raw_p316_sim.get("rf_nvs_p12_p13_writes_authorized", True) is not False
        or raw_p316_sim.get("slot1_tier0_vault_mutated", True) is not False
    ):
        errors.append(
            f"p5_p316_zero_rf_end_slot1: wrf={p316_wrf}, rf={p316_rf}, e_nd={p316_end}, "
            f"slot1_writes={p316_slot1}, rf_nvs_auth={raw_p316_sim.get('rf_nvs_p12_p13_writes_authorized')}, "
            f"slot1_mutated={raw_p316_sim.get('slot1_tier0_vault_mutated')}"
        )

    info_321 = _check_phase321_bench_verifier(
        raw_off=raw_p321_off,
        raw_sim=raw_p321_sim,
        errors=errors,
        extra_usb_override=faults.p5_inject_p321_usb_packets_override,
        extra_passive_override=faults.p5_inject_p321_passive_tx_bytes_override,
    )
    p321_wrf = int(raw_p321_sim.get("wireless_rf_packets_emitted", -1)) + int(
        faults.p5_inject_p321_wireless_rf_packets_override
    )
    p321_rf = int(raw_p321_sim.get("rf_packets_transmitted", -1)) + int(
        faults.p5_inject_p321_wireless_rf_packets_override
    )
    p321_end = int(raw_p321_sim.get("e_nd_actuator_tx_count", -1))
    p321_slot1 = int(raw_p321_sim.get("slot1_data_sector_writes", -1))
    if (
        p321_wrf != 0
        or p321_rf != 0
        or p321_end != 0
        or p321_slot1 != 0
        or raw_p321_sim.get("rf_nvs_p12_p13_writes_authorized", True) is not False
        or raw_p321_sim.get("slot1_tier0_vault_mutated", True) is not False
    ):
        errors.append(
            f"p5_p321_zero_rf_end_slot1: wrf={p321_wrf}, rf={p321_rf}, e_nd={p321_end}, "
            f"slot1_writes={p321_slot1}, rf_nvs_auth={raw_p321_sim.get('rf_nvs_p12_p13_writes_authorized')}, "
            f"slot1_mutated={raw_p321_sim.get('slot1_tier0_vault_mutated')}"
        )

    any_attach_ready = bool(
        meta_p5_311["overall_ready_for_hardware_attach"]
        or info_316.pop("_any_attach_ready")
        or info_321.pop("_any_attach_ready")
    )
    if any_attach_ready:
        errors.append("p5: overall_ready_for_hardware_attach must remain False across all 14 verifiers")

    info_316["p316_wireless_rf_packets_emitted"] = p316_wrf
    info_316["p316_rf_packets_transmitted"] = p316_rf
    info_316["p316_e_nd_actuator_tx_count"] = p316_end
    info_316["p316_slot1_data_sector_writes"] = p316_slot1

    info_321["p321_wireless_rf_packets_emitted"] = p321_wrf
    info_321["p321_rf_packets_transmitted"] = p321_rf
    info_321["p321_e_nd_actuator_tx_count"] = p321_end
    info_321["p321_slot1_data_sector_writes"] = p321_slot1

    passed = len(errors) == 0
    evidence = dict(m311_p5.evidence)
    evidence.update(info_316)
    evidence.update(info_321)
    evidence["overall_ready_for_hardware_attach"] = any_attach_ready

    pillar = Milestone324PillarResult(
        pillar_id="P5",
        pillar_name="TETRADECUPLE_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH321",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"14/14 Bench Preflights: Ph186..Ph307(12/12) + "
            f"Ph316({info_316['p316_sim_check_groups_passed']}/4 H0==H3={info_316['p316_h0_equals_h3_count']}/16 RF={p316_rf}) + "
            f"Ph321({info_321['p321_sim_check_groups_passed']}/4 H0==H3={info_321['p321_h0_equals_h3_count']}/16 RF={p321_rf}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_p5_311)
    meta.update(info_316)
    meta.update(info_321)
    meta["overall_ready_for_hardware_attach"] = any_attach_ready
    return pillar, meta


def _evaluate_pillar_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: RealHwMilestone324FaultInjection,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
    p5_meta: Mapping[str, Any],
) -> Tuple[Milestone324PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    round_sources: Dict[str, str] = {}
    round_schemas: Dict[str, str] = {}
    runs_by_round: Dict[str, int] = {}
    png_sizes_by_asset: Dict[str, int] = {}
    png_sources_by_round: Dict[str, str] = {}

    total_nops = 0
    total_crashes = 0
    total_emmc = 0
    total_qemu_leaked = max(0, int(faults.p6_raw_firmware_bytes_leaked_override))
    rounds_verified = 0
    total_runs_verified = 0
    pngs_verified = 0
    max_png_bytes = 0

    expected_rounds = len(ROUND28_TO_65_SPECS)
    expected_runs = sum(len(s.run_specs) for s in ROUND28_TO_65_SPECS)
    expected_pngs = sum(len(ROUND28_TO_65_PNG_RECEIPTS[s.round_num]) for s in ROUND28_TO_65_SPECS)

    for spec in ROUND28_TO_65_SPECS:
        r_tag = f"r{spec.round_num}"
        raw_round, r_src = _load_round28_to_37_summary(
            spec, repo_root=repo_root, use_clean_room=use_clean_room
        )
        if faults.p6_tamper_schema_round_num == spec.round_num:
            raw_round = copy.deepcopy(raw_round)
            raw_round["schema"] = "tampered-invalid-schema"

        round_sources[r_tag] = r_src
        r_schema = str(raw_round.get("schema", ""))
        r_kver = str(raw_round.get("kernel_version", ""))
        round_schemas[r_tag] = r_schema
        r_leaked = max(0, int(raw_round.get("raw_firmware_bytes_leaked", 0)))
        total_qemu_leaked += r_leaked

        round_ok = True
        if r_schema != spec.expected_schema:
            errors.append(f"p6_{r_tag}: unexpected schema {r_schema!r}")
            round_ok = False
        if "4.9.337-scel+" not in r_kver:
            errors.append(f"p6_{r_tag}: unexpected kernel_version {r_kver!r}")
            round_ok = False
        if r_leaked != 0:
            errors.append(f"p6_{r_tag}: raw_firmware_bytes_leaked={r_leaked} != 0")
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

        png_pair = ROUND28_TO_65_PNG_RECEIPTS[spec.round_num]
        for png_idx, png_rel in enumerate(png_pair):
            png_ok, png_size, png_src = _inspect_round_png_receipt_50kib(
                png_rel, repo_root=repo_root, use_clean_room=use_clean_room
            )
            if (
                png_idx == 0
                and faults.p6_png_size_override_round_num == spec.round_num
                and faults.p6_png_size_override_bytes is not None
            ):
                png_size = int(faults.p6_png_size_override_bytes)
                png_ok = 0 < png_size < PNG_MAX_SIZE_50KIB_BYTES
            png_sizes_by_asset[Path(png_rel).name] = png_size
            png_sources_by_round[r_tag] = png_src
            if png_size > max_png_bytes:
                max_png_bytes = png_size
            if png_ok:
                pngs_verified += 1
            else:
                errors.append(
                    f"p6_{r_tag}: PNG receipt invalid or >= {PNG_MAX_SIZE_50KIB_BYTES}B ({png_rel}, size={png_size})"
                )
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

            if (
                run_idx == 0
                and faults.p6_round_nop_override_num == spec.round_num
                and faults.p6_round_nop_count_override is not None
            ):
                rnop = int(faults.p6_round_nop_count_override)
            elif exp_faithful is not None:
                rnop = int(robj.get("nop_count", -1))
            else:
                rnop = int(robj.get("nop_count") or 0)

            if (
                run_idx == 0
                and faults.p6_round_crash_override_num == spec.round_num
                and faults.p6_round_crashes_override is not None
            ):
                rcrash = int(faults.p6_round_crashes_override)
            else:
                rcrash = int(robj.get("crashes", -1))

            if (
                run_idx == 0
                and faults.p6_round_emmc_override_num == spec.round_num
                and faults.p6_round_emmc_writes_override is not None
            ):
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

    # Forward-compatible discovery of Round 66+ reports so newly merged QEMU rounds stay green
    reports_dir = repo_root / "reports"
    if reports_dir.is_dir():
        seen_extra_rounds: Dict[int, Path] = {}
        for d in sorted(reports_dir.iterdir()):
            if not d.is_dir() or d.is_symlink():
                continue
            m = _ROUND_DIR_RE.search(d.name)
            if not m:
                continue
            rnum = int(m.group(1))
            if rnum >= 66 and (d / "summary.json").is_file():
                seen_extra_rounds[rnum] = d

        for rnum, rdir in sorted(seen_extra_rounds.items()):
            r_tag = f"r{rnum}"
            sj_path = rdir / "summary.json"
            raw_round = json.loads(_read_file_o_rdonly(sj_path).decode("utf-8"))
            round_sources[r_tag] = "REPO_SUMMARY_O_RDONLY"
            r_schema = str(raw_round.get("schema", ""))
            r_kver = str(raw_round.get("kernel_version", ""))
            round_schemas[r_tag] = r_schema
            r_leaked = max(0, int(raw_round.get("raw_firmware_bytes_leaked", 0)))
            total_qemu_leaked += r_leaked
            round_ok = "4.9.337-scel+" in r_kver and r_leaked == 0
            if not round_ok:
                errors.append(f"p6_{r_tag}: forward-compat round kernel/leak check failed")

            for ak, av in raw_round.items():
                if ak.startswith(f"r{rnum}_") and ak.endswith("_audit") and isinstance(av, Mapping):
                    for bk, bv in av.items():
                        if isinstance(bv, bool):
                            if bk in _NEGATIVE_AUDIT_BOOL_KEYS:
                                if bv is not False:
                                    errors.append(f"p6_{r_tag}: forward-compat audit flag {bk} is True")
                                    round_ok = False
                            elif not bv:
                                errors.append(f"p6_{r_tag}: forward-compat audit flag {bk} is False")
                                round_ok = False

            png_files = sorted(p for p in rdir.rglob("*.png") if p.is_file() and not p.is_symlink())
            expected_pngs += len(png_files)
            for pfile in png_files:
                rel_p = pfile.relative_to(repo_root).as_posix()
                png_ok, png_size, png_src = _inspect_round_png_receipt_50kib(
                    rel_p, repo_root=repo_root, use_clean_room=use_clean_room
                )
                png_sizes_by_asset[pfile.name] = png_size
                png_sources_by_round[r_tag] = png_src
                if png_size > max_png_bytes:
                    max_png_bytes = png_size
                if png_ok:
                    pngs_verified += 1
                else:
                    errors.append(f"p6_{r_tag}: forward-compat PNG invalid ({rel_p})")
                    round_ok = False

            runs_map = raw_round.get("runs", {})
            run_items = list(runs_map.items()) if isinstance(runs_map, Mapping) else []
            expected_rounds += 1
            expected_runs += len(run_items)
            v_runs = 0
            for rid, robj in run_items:
                if not isinstance(robj, Mapping):
                    round_ok = False
                    continue
                rnop = int(robj.get("nop_count") or 0)
                rcrash = int(robj.get("crashes", -1))
                remmc = int(robj.get("emmc_write_count", -1))
                sb_count = int(robj.get("stage_b", {}).get("manifest_count", 13))
                total_nops += max(0, rnop)
                total_crashes += max(0, rcrash)
                total_emmc += max(0, remmc)
                if rnop == 0 and rcrash == 0 and remmc == 0 and sb_count == 13:
                    v_runs += 1
                else:
                    errors.append(f"p6_{r_tag}:{rid}: forward-compat run invariants failed")
                    round_ok = False
            runs_by_round[r_tag] = v_runs
            total_runs_verified += v_runs
            if round_ok and len(run_items) > 0 and v_runs == len(run_items):
                rounds_verified += 1

    if total_qemu_leaked != 0:
        errors.append(f"p6: QEMU raw_firmware_bytes_leaked={total_qemu_leaked} != 0")

    # Cross-pillar hardware-lock, 16/16 H0 == H3, zero eMMC, zero RF & zero e-ND invariants
    if (
        p1_meta.get("persistent_emmc_writes_authorized") is not False
        or p1_meta.get("spi_nor_write_authorized") is not False
        or p1_meta.get("el3_payload_transmit_authorized") is not False
        or p1_meta.get("cross_model_flash_authorized") is not False
        or p1_meta.get("simulated_ready_for_hardware_attach") is not False
        or p1_meta.get("hardware_live_attachment_authorized") is not False
        or int(p1_meta.get("g71_e_nd_actuator_tx_count", -1)) != 0
    ):
        errors.append("p6: P1 hardware-lock, cross-model-flash, or zero e-ND invariant breached")
    if (
        p2_meta.get("cnflasha_userspace_write_blocked") is not True
        or int(p2_meta.get("otp_fuse_writes", -1)) != 0
        or int(p2_meta.get("rpmb_writes", -1)) != 0
        or int(p2_meta.get("passive_tx_bytes", -1)) != 0
        or int(p2_meta.get("physical_usb_packets_emitted", -1)) != 0
        or int(p2_meta.get("physical_device_writes", -1)) != 0
        or int(p2_meta.get("raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append("p6: P2 cnflasha RO or zero-touch OTP/RPMB/passive-UART/USB-PKT invariant breached")
    if (
        int(p3_meta.get("calibration_mutation_bytes", -1)) != 0
        or int(p3_meta.get("wbi_mutation_bytes", -1)) != 0
        or int(p3_meta.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(p3_meta.get("e_nd_actuator_tx_count", -1)) != 0
    ):
        errors.append("p6: P3 calibration/WBI/raw-FW/zero-e-ND invariant breached")
    if (
        int(p4_meta.get("cp_mutation_bytes", -1)) != 0
        or int(p4_meta.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(p4_meta.get("wf12_00342260_hits", -1)) != 0
        or int(p4_meta.get("emmc_corruptions", -1)) != 0
        or int(p4_meta.get("physical_device_writes", -1)) != 0
        or int(p4_meta.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(p4_meta.get("e_nd_actuator_tx_count", -1)) != 0
    ):
        errors.append("p6: P4 CP/BK4/WF-12/eMMC/zero-device-write/zero-e-ND invariant breached")

    if (
        int(p5_meta.get("h0_equals_h3_count", -1)) != 16
        or p5_meta.get("overall_ready_for_hardware_attach") is not False
        or not bool(p5_meta.get("p154_bench_go"))
        or int(p5_meta.get("p186_sim_gates_passed", -1)) != 4
        or p5_meta.get("p186_card_insert_authorized") is not False
        or int(p5_meta.get("p204_sim_groups_passed", -1)) != 3
        or p5_meta.get("p204_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p204_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p204_e_nd_actuator_tx_count", -1)) != 0
        or int(p5_meta.get("p216_sim_checklists_passed", -1)) != 5
        or p5_meta.get("p216_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p216_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p216_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p216_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p227_sim_check_groups_passed", -1)) != 3
        or p5_meta.get("p227_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p227_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p227_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p227_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p248_sim_check_groups_passed", -1)) != 4
        or p5_meta.get("p248_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p248_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p248_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p248_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p261_sim_check_groups_passed", -1)) != 4
        or p5_meta.get("p261_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p261_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p261_e_nd_uart_bytes_transmitted", -1)) != 0
        or int(p5_meta.get("p261_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p261_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p275_sim_check_groups_passed", -1)) != 4
        or p5_meta.get("p275_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p275_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p275_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p275_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p279_sim_check_groups_passed", -1)) != 4
        or p5_meta.get("p279_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p279_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p279_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p279_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p284_sim_check_groups_passed", -1)) != 4
        or p5_meta.get("p284_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p284_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p284_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p284_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p291_sim_check_groups_passed", -1)) != 4
        or p5_meta.get("p291_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p291_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p291_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p291_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p291_sim_passive_tx_bytes_emitted", -1)) != 0
        or int(p5_meta.get("p302_sim_check_groups_passed", -1)) != 4
        or p5_meta.get("p302_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p302_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p302_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p302_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p302_sim_passive_tx_bytes_emitted", -1)) != 0
        or int(p5_meta.get("p307_sim_check_groups_passed", -1)) != 4
        or p5_meta.get("p307_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p307_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p307_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p307_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p307_sim_passive_tx_bytes_emitted", -1)) != 0
        or int(p5_meta.get("p307_wireless_rf_packets_emitted", -1)) != 0
        or int(p5_meta.get("p307_slot1_data_sector_writes", -1)) != 0
        or int(p5_meta.get("p316_sim_check_groups_passed", -1)) != 4
        or p5_meta.get("p316_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p316_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p316_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p316_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p316_sim_passive_tx_bytes_emitted", -1)) != 0
        or int(p5_meta.get("p316_wireless_rf_packets_emitted", -1)) != 0
        or int(p5_meta.get("p316_rf_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p316_e_nd_actuator_tx_count", -1)) != 0
        or int(p5_meta.get("p316_slot1_data_sector_writes", -1)) != 0
        or int(p5_meta.get("p321_sim_check_groups_passed", -1)) != 4
        or p5_meta.get("p321_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p321_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p321_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p321_sim_raw_firmware_bytes_leaked", -1)) != 0
        or int(p5_meta.get("p321_sim_passive_tx_bytes_emitted", -1)) != 0
        or int(p5_meta.get("p321_wireless_rf_packets_emitted", -1)) != 0
        or int(p5_meta.get("p321_rf_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p321_e_nd_actuator_tx_count", -1)) != 0
        or int(p5_meta.get("p321_slot1_data_sector_writes", -1)) != 0
    ):
        errors.append(
            "p6: P5 H0==H3 (16/16) or 14/14 tetradecuple bench preflight (Ph186..Ph321) invariant breached"
        )

    passed = (
        len(errors) == 0
        and rounds_verified >= 38
        and rounds_verified == expected_rounds
        and total_runs_verified >= 114
        and total_runs_verified == expected_runs
        and pngs_verified >= 76
        and pngs_verified == expected_pngs
        and 0 < max_png_bytes < PNG_MAX_SIZE_50KIB_BYTES
        and total_qemu_leaked == 0
        and total_nops == 0
        and total_crashes == 0
        and total_emmc == 0
    )
    max_round_num = 27 + expected_rounds
    evidence = {
        "round_sources": round_sources,
        "round_schemas": round_schemas,
        "rounds_verified": rounds_verified,
        "expected_rounds": expected_rounds,
        "runs_by_round": runs_by_round,
        "total_runs_verified": total_runs_verified,
        "expected_total_runs": expected_runs,
        "png_receipts_verified": pngs_verified,
        "expected_png_receipts": expected_pngs,
        "png_max_bytes": max_png_bytes,
        "png_max_ceiling_bytes": PNG_MAX_SIZE_50KIB_BYTES,
        "png_baseline_max_observed_bytes": P324_BASELINE_PNG_MAX_OBSERVED_BYTES,
        "png_sizes_by_asset": png_sizes_by_asset,
        "png_sources_by_round": png_sources_by_round,
        "h0_equals_h3_count": int(p5_meta.get("p321_h0_equals_h3_count", 0)),
        "emmc_write_count": total_emmc,
        "e_nd_actuator_tx_count": max(0, int(p1_meta.get("g71_e_nd_actuator_tx_count", 0)))
        + max(0, int(p4_meta.get("e_nd_actuator_tx_count", 0)))
        + max(0, int(p5_meta.get("p261_e_nd_uart_bytes_transmitted", 0)))
        + max(0, int(p5_meta.get("p316_e_nd_actuator_tx_count", 0)))
        + max(0, int(p5_meta.get("p321_e_nd_actuator_tx_count", 0))),
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
        "raw_firmware_bytes_leaked": total_qemu_leaked,
        "milestone175_schema_anchor": MILESTONE175_SCHEMA_VERSION,
        "milestone193_schema_anchor": MILESTONE193_SCHEMA_VERSION,
        "milestone209_schema_anchor": MILESTONE209_SCHEMA_VERSION,
        "milestone221_schema_anchor": MILESTONE221_SCHEMA_VERSION,
        "milestone233_schema_anchor": MILESTONE233_SCHEMA_VERSION,
        "milestone254_schema_anchor": MILESTONE254_SCHEMA_VERSION,
        "milestone264_schema_anchor": MILESTONE264_SCHEMA_VERSION,
        "milestone295_schema_anchor": MILESTONE295_SCHEMA_VERSION,
        "milestone311_schema_anchor": MILESTONE311_SCHEMA_VERSION,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
    }
    pillar = Milestone324PillarResult(
        pillar_id="P6",
        pillar_name="REAL_FX3_702_QEMU_ROUNDS_28_TO_65_PLUS_AND_PNG_RECEIPTS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Live FX3 7.02 QEMU Rounds 28..{max_round_num}={rounds_verified}/{expected_rounds} rounds "
            f"({total_runs_verified}/{expected_runs} runs, PNGs={pngs_verified}/{expected_pngs} "
            f"max={max_png_bytes}B < 50KiB), H0==H3=16/16, nop={total_nops}, crashes={total_crashes}, "
            f"emmc={total_emmc}, leaked={total_qemu_leaked}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "qemu_rounds_total": expected_rounds,
        "qemu_rounds_verified": rounds_verified,
        "qemu_runs_total": expected_runs,
        "qemu_runs_verified": total_runs_verified,
        "qemu_png_receipts_total": expected_pngs,
        "qemu_png_receipts_verified": pngs_verified,
        "qemu_png_max_bytes": max_png_bytes,
        "qemu_round_runs_by_round": runs_by_round,
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
        "qemu_raw_firmware_bytes_leaked": total_qemu_leaked,
    }
    return pillar, meta


# ---------------------------------------------------------------------------
# Parallel Collector, Builder, Fail-Closed Verifier & CLI
# ---------------------------------------------------------------------------


def _collect_parallel_milestone324_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: RealHwMilestone324FaultInjection,
) -> Tuple[Any, ...]:
    m311_f = _effective_m311_faults(faults)
    m295_f = _effective_m295_from_m311(m311_f)
    m264_f = _effective_m264_faults(m295_f)
    m254_f = _effective_m254_faults(m264_f)
    m233_f = _effective_m233_faults(m254_f)
    m221_f = _effective_m221_faults(m233_f)
    m209_f = _effective_m209_faults(m221_f)
    m193_f = _effective_m193_faults(m209_f)
    gate_fault_dict = _fault_to_142gate_worker_dict(faults)
    p154_sim_ready = not m193_f.p5_inject_p154_no_go_fault
    p186_fault_dict = {
        "inject_appledouble_fault": bool(m193_f.p5_inject_p186_appledouble_fault),
        "inject_h0_h3_drift": bool(m193_f.p5_inject_p186_h0_h3_drift),
        "inject_fw_below_204": bool(m193_f.p5_inject_p186_fw_below_204),
        "inject_single_device_collision": bool(m193_f.p5_inject_p186_single_device_collision),
    }
    p204_fault_dict = {
        "fan_auto1": bool(m209_f.p5_inject_p204_fan_auto1_fault),
        "always_off": bool(m209_f.p5_inject_p204_always_off_fault),
        "end_tx": bool(m209_f.p5_inject_p204_end_tx_fault),
        "camset_slot2": bool(m209_f.p5_inject_p204_camset_slot2_fault),
        "vmc_xlrh1_port": bool(m209_f.p5_inject_p204_vmc_xlrh1_port_fault),
        "h0_h3_drift": bool(m209_f.p5_inject_p204_h0_h3_drift),
    }
    p216_fault_dict = {
        "desqueeze_lock": bool(m221_f.p5_inject_p216_desqueeze_lock_fault),
        "hdmi_only_card_rec": bool(m221_f.p5_inject_p216_hdmi_only_card_rec_fault),
        "proxy_orphan": bool(m221_f.p5_inject_p216_proxy_orphan_fault),
        "title_38char": bool(m221_f.p5_inject_p216_title_38char_fault),
        "h0_h3_drift": bool(m221_f.p5_inject_p216_h0_h3_drift),
    }
    p227_fault_dict = {
        "pixelmap_lowbatt": bool(m233_f.p5_inject_p227_pixelmap_lowbatt_fault),
        "ntscpal_fps_conflict": bool(m233_f.p5_inject_p227_ntscpal_fps_conflict_fault),
        "powersave_p3_sleep": bool(m233_f.p5_inject_p227_powersave_p3_sleep_fault),
        "autotemp_no_tripod": bool(m233_f.p5_inject_p227_autotemp_no_tripod_fault),
        "h0_h3_drift": bool(m233_f.p5_inject_p227_h0_h3_drift),
    }
    p248_fault_dict = {
        "imagedb_slot1_vault": bool(m254_f.p5_inject_p248_imagedb_slot1_vault_fault),
        "touch_bench_tap": bool(m254_f.p5_inject_p248_touch_bench_tap_fault),
        "shoe_audio_sq_lockout": bool(m254_f.p5_inject_p248_shoe_audio_sq_lockout_fault),
        "lockop_destructive_chord": bool(m254_f.p5_inject_p248_lockop_destructive_chord_fault),
        "usb_power_no_battery": bool(m254_f.p5_inject_p248_usb_power_no_battery_fault),
        "h0_h3_drift": bool(m254_f.p5_inject_p248_h0_h3_drift),
    }
    p261_fault_dict = {
        "diffset_customkey_vault": bool(m264_f.p5_inject_p261_diffset_customkey_vault_fault),
        "autoslow_hdmi_rec_ctrl": bool(m264_f.p5_inject_p261_autoslow_hdmi_rec_ctrl_fault),
        "apsc_4k_or_bodydata_flash": bool(m264_f.p5_inject_p261_apsc_4k_or_bodydata_flash_fault),
        "end_uart_or_copyright_pii": bool(m264_f.p5_inject_p261_end_uart_or_copyright_pii_fault),
        "h0_h3_drift": bool(m264_f.p5_inject_p261_h0_h3_drift),
    }
    p275_fault_dict = {
        "file_gamma_focusmag_vault": bool(m295_f.p5_inject_p275_file_gamma_focusmag_vault_fault),
        "h0_h3_drift": bool(m295_f.p5_inject_p275_h0_h3_drift),
    }
    p279_fault_dict = {
        "usb_hdmi_protect_nw": bool(m295_f.p5_inject_p279_usb_hdmi_protect_nw_fault),
        "h0_h3_drift": bool(m295_f.p5_inject_p279_h0_h3_drift),
    }
    p284_fault_dict = {
        "pp_wb_raw_shutter": bool(m295_f.p5_inject_p284_pp_wb_raw_shutter_fault),
        "h0_h3_drift": bool(m295_f.p5_inject_p284_h0_h3_drift),
    }
    p291_fault_dict = {
        "focus_zoom_dci4k_clean": bool(m295_f.p5_inject_p291_focus_zoom_dci4k_clean_fault),
        "h0_h3_drift": bool(m295_f.p5_inject_p291_h0_h3_drift),
    }
    p302_fault_dict = {
        "lens_af_copy_evf": bool(m311_f.p5_inject_p302_lens_af_copy_evf_fault),
        "h0_h3_drift": bool(m311_f.p5_inject_p302_h0_h3_drift),
    }
    p307_fault_dict = {
        "dial_lut_ibis_rf_slot1": bool(m311_f.p5_inject_p307_dial_lut_ibis_rf_slot1_fault),
        "h0_h3_drift": bool(m311_f.p5_inject_p307_h0_h3_drift),
    }
    p316_fault_dict = {
        "bright_mon_shotmark_big6_ssh": bool(faults.p5_inject_p316_bright_mon_shotmark_big6_ssh_fault),
        "h0_h3_drift": bool(faults.p5_inject_p316_h0_h3_drift),
    }
    p321_fault_dict = {
        "rec_media_proxy_cloud_mymenu_ftpes": bool(
            faults.p5_inject_p321_rec_media_proxy_cloud_mymenu_ftpes_fault
        ),
        "h0_h3_drift": bool(faults.p5_inject_p321_h0_h3_drift),
    }

    p3_batches: Tuple[Tuple[str, ...], ...] = (
        (
            "realhw_fan_shutter_lut601_702",
            "realhw_big6_camset_vmcbncm1",
            "realhw_desqueeze_focusmap_shocklesswb",
            "realhw_hdmi_log1080_proxy_focusmag",
            "realhw_filesettings_shotmark_tcregen_reclamp",
            "discover_forward_compat_46plus",
        ),
        ("multilang",),
        ("realhw_peripheral", "realhw_controls_fan", "realhw_wifi_usb"),
        ("realhw_c2pa_tc_gyro", "realhw_wbi2_hibdrv"),
        ("group_b",),
        ("realhw_imx510",),
        ("realhw_cfexpress_ufu", "realhw_cxd90058_sabin"),
        ("assignable", "falsecolor", "playback", "gyroflow"),
        ("interval_ftp", "lut3d_sdi", "c2pa_mc", "hdr_hlg"),
        ("sensor",),
        ("haita",),
        ("group_a",),
        ("emount",),
        ("wbi",),
        ("prores_mishoe", "uvc_crsdk", "mxf_tally", "vp_ledwall"),
        ("realhw_hdmi_braw_wpa3", "realhw_emount_info3d"),
        ("xavc_fz100", "realhw_cp_backup", "realhw_mpr_dmm"),
        ("realhw_fx3a_xlrh1", "realhw_nouvc_dcc1_lut"),
    )

    eff_p2_fault = faults.p2_fault_inject_pillar or m311_f.p2_fault_inject_pillar

    auditors: Dict[str, Dict[str, Any]] = {}
    try:
        auditors.update(_worker_pillar_3_batch_233((p3_batches[0], use_clean_room)))
        ctx = mp.get_context("fork")
        pool_workers = min(8, max(4, mp.cpu_count() or 8))
        with ProcessPoolExecutor(max_workers=pool_workers, mp_context=ctx) as ex:
            fut_vm = ex.submit(_worker_pillar_4_295, use_clean_room)
            fut_1_off = ex.submit(
                _worker_142plus_gate_single,
                (str(repo_root), use_clean_room, False, gate_fault_dict),
            )
            fut_1_sim = ex.submit(
                _worker_142plus_gate_single,
                (str(repo_root), use_clean_room, True, gate_fault_dict),
            )
            fut_56p = ex.submit(_worker_recovery_56plus_pillar, (use_clean_room, eff_p2_fault))
            fut_p136 = ex.submit(_worker_phase136, use_clean_room)
            fut_143_154_186 = ex.submit(
                _worker_phase143_154_186,
                (
                    str(fx6_lib_dir),
                    str(fx3_modules_dir),
                    use_clean_room,
                    p154_sim_ready,
                    p186_fault_dict,
                ),
            )
            fut_3 = [
                ex.submit(_worker_pillar_3_batch_233, (batch, use_clean_room))
                for batch in p3_batches[1:]
            ]
            fut_204 = ex.submit(
                _worker_phase204,
                (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p204_fault_dict),
            )
            fut_216 = ex.submit(
                _worker_phase216,
                (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p216_fault_dict),
            )
            fut_227 = ex.submit(
                _worker_phase227,
                (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p227_fault_dict),
            )
            fut_248 = ex.submit(
                _worker_phase248,
                (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p248_fault_dict),
            )
            fut_261 = ex.submit(
                _worker_phase261,
                (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p261_fault_dict),
            )
            fut_275_279 = ex.submit(
                _worker_phase275_279,
                (
                    str(fx6_lib_dir),
                    str(fx3_modules_dir),
                    use_clean_room,
                    p275_fault_dict,
                    p279_fault_dict,
                ),
            )
            fut_284_291 = ex.submit(
                _worker_phase284_291,
                (
                    str(fx6_lib_dir),
                    str(fx3_modules_dir),
                    use_clean_room,
                    p284_fault_dict,
                    p291_fault_dict,
                ),
            )
            fut_302_307 = ex.submit(
                _worker_phase302_307,
                (
                    str(fx6_lib_dir),
                    str(fx3_modules_dir),
                    use_clean_room,
                    p302_fault_dict,
                    p307_fault_dict,
                ),
            )
            fut_316_321 = ex.submit(
                _worker_phase316_321,
                (
                    str(fx6_lib_dir),
                    str(fx3_modules_dir),
                    use_clean_room,
                    p316_fault_dict,
                    p321_fault_dict,
                ),
            )

            raw_1_off = fut_1_off.result()
            raw_1_sim = fut_1_sim.result()
            raw_56p = fut_56p.result()
            for fg in fut_3:
                auditors.update(fg.result())
            raw_vm = fut_vm.result()
            raw_p136 = fut_p136.result()
            raw_p143, raw_p154, raw_p186_off, raw_p186_sim = fut_143_154_186.result()
            raw_p204_off, raw_p204_sim = fut_204.result()
            raw_p216_off, raw_p216_sim = fut_216.result()
            raw_p227_off, raw_p227_sim = fut_227.result()
            raw_p248_off, raw_p248_sim = fut_248.result()
            raw_p261_off, raw_p261_sim = fut_261.result()
            raw_p275_off, raw_p275_sim, raw_p279_off, raw_p279_sim = fut_275_279.result()
            raw_p284_off, raw_p284_sim, raw_p291_off, raw_p291_sim = fut_284_291.result()
            raw_p302_off, raw_p302_sim, raw_p307_off, raw_p307_sim = fut_302_307.result()
            raw_p316_off, raw_p316_sim, raw_p321_off, raw_p321_sim = fut_316_321.result()
            return (
                raw_1_off,
                raw_1_sim,
                raw_56p,
                auditors,
                raw_vm,
                raw_p136,
                raw_p143,
                raw_p154,
                raw_p186_off,
                raw_p186_sim,
                raw_p204_off,
                raw_p204_sim,
                raw_p216_off,
                raw_p216_sim,
                raw_p227_off,
                raw_p227_sim,
                raw_p248_off,
                raw_p248_sim,
                raw_p261_off,
                raw_p261_sim,
                raw_p275_off,
                raw_p275_sim,
                raw_p279_off,
                raw_p279_sim,
                raw_p284_off,
                raw_p284_sim,
                raw_p291_off,
                raw_p291_sim,
                raw_p302_off,
                raw_p302_sim,
                raw_p307_off,
                raw_p307_sim,
                raw_p316_off,
                raw_p316_sim,
                raw_p321_off,
                raw_p321_sim,
            )
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1_off = _worker_142plus_gate_single(
        (str(repo_root), use_clean_room, False, gate_fault_dict)
    )
    raw_1_sim = _worker_142plus_gate_single(
        (str(repo_root), use_clean_room, True, gate_fault_dict)
    )
    raw_56p = _worker_recovery_56plus_pillar((use_clean_room, eff_p2_fault))
    auditors = {}
    for batch in p3_batches:
        auditors.update(_worker_pillar_3_batch_233((batch, use_clean_room)))
    raw_vm = _worker_pillar_4_295(use_clean_room)
    raw_p136 = _worker_phase136(use_clean_room)
    raw_p143, raw_p154, raw_p186_off, raw_p186_sim = _worker_phase143_154_186(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p154_sim_ready, p186_fault_dict)
    )
    raw_p204_off, raw_p204_sim = _worker_phase204(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p204_fault_dict)
    )
    raw_p216_off, raw_p216_sim = _worker_phase216(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p216_fault_dict)
    )
    raw_p227_off, raw_p227_sim = _worker_phase227(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p227_fault_dict)
    )
    raw_p248_off, raw_p248_sim = _worker_phase248(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p248_fault_dict)
    )
    raw_p261_off, raw_p261_sim = _worker_phase261(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p261_fault_dict)
    )
    raw_p275_off, raw_p275_sim, raw_p279_off, raw_p279_sim = _worker_phase275_279(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p275_fault_dict, p279_fault_dict)
    )
    raw_p284_off, raw_p284_sim, raw_p291_off, raw_p291_sim = _worker_phase284_291(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p284_fault_dict, p291_fault_dict)
    )
    raw_p302_off, raw_p302_sim, raw_p307_off, raw_p307_sim = _worker_phase302_307(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p302_fault_dict, p307_fault_dict)
    )
    raw_p316_off, raw_p316_sim, raw_p321_off, raw_p321_sim = _worker_phase316_321(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p316_fault_dict, p321_fault_dict)
    )
    return (
        raw_1_off,
        raw_1_sim,
        raw_56p,
        auditors,
        raw_vm,
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
        raw_p216_off,
        raw_p216_sim,
        raw_p227_off,
        raw_p227_sim,
        raw_p248_off,
        raw_p248_sim,
        raw_p261_off,
        raw_p261_sim,
        raw_p275_off,
        raw_p275_sim,
        raw_p279_off,
        raw_p279_sim,
        raw_p284_off,
        raw_p284_sim,
        raw_p291_off,
        raw_p291_sim,
        raw_p302_off,
        raw_p302_sim,
        raw_p307_off,
        raw_p307_sim,
        raw_p316_off,
        raw_p316_sim,
        raw_p321_off,
        raw_p321_sim,
    )


def evaluate_realhw_milestone324_master_gate(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    simulate_bench_dry_run: Optional[bool] = None,
    faults: Optional[RealHwMilestone324FaultInjection] = None,
    _raw_bundle_override: Optional[Tuple[Any, ...]] = None,
) -> RealHwMilestone324MasterGateReport:
    """Build & evaluate the Grand Milestone Phase 324 6-Pillar Real-Hardware Master Gate."""
    _ = simulate_bench_dry_run  # All pillars verify BOTH offline fail-closed and dry-run paths
    if force_clean_room is not None:
        use_clean_room = bool(force_clean_room)
    elif synthetic_clean_room is not None:
        use_clean_room = bool(synthetic_clean_room)
    else:
        use_clean_room = _is_forced_clean_room(
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
        )

    active_faults = faults or RealHwMilestone324FaultInjection()

    bundle = _raw_bundle_override or _collect_parallel_milestone324_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )
    (
        raw_1_off,
        raw_1_sim,
        raw_56p,
        auditors,
        raw_vm,
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
        raw_p216_off,
        raw_p216_sim,
        raw_p227_off,
        raw_p227_sim,
        raw_p248_off,
        raw_p248_sim,
        raw_p261_off,
        raw_p261_sim,
        raw_p275_off,
        raw_p275_sim,
        raw_p279_off,
        raw_p279_sim,
        raw_p284_off,
        raw_p284_sim,
        raw_p291_off,
        raw_p291_sim,
        raw_p302_off,
        raw_p302_sim,
        raw_p307_off,
        raw_p307_sim,
        raw_p316_off,
        raw_p316_sim,
        raw_p321_off,
        raw_p321_sim,
    ) = bundle

    p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
    p2, meta_2 = _evaluate_pillar_2(raw_56p, active_faults)
    p3, meta_3 = _evaluate_pillar_3(auditors, active_faults)
    p4, meta_4 = _evaluate_pillar_4(raw_vm, active_faults)
    p5, meta_5 = _evaluate_pillar_5(
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
        raw_p216_off,
        raw_p216_sim,
        raw_p227_off,
        raw_p227_sim,
        raw_p248_off,
        raw_p248_sim,
        raw_p261_off,
        raw_p261_sim,
        raw_p275_off,
        raw_p275_sim,
        raw_p279_off,
        raw_p279_sim,
        raw_p284_off,
        raw_p284_sim,
        raw_p291_off,
        raw_p291_sim,
        raw_p302_off,
        raw_p302_sim,
        raw_p307_off,
        raw_p307_sim,
        raw_p316_off,
        raw_p316_sim,
        raw_p321_off,
        raw_p321_sim,
        active_faults,
    )
    p1_meta = {
        "persistent_emmc_writes_authorized": raw_1_sim["persistent_emmc_writes_authorized"],
        "spi_nor_write_authorized": raw_1_sim["spi_nor_write_authorized"],
        "el3_payload_transmit_authorized": raw_1_sim["el3_payload_transmit_authorized"],
        "cross_model_flash_authorized": raw_1_sim.get("cross_model_flash_authorized", True),
        "simulated_ready_for_hardware_attach": raw_1_sim["overall_ready_for_hardware_attach"],
        "hardware_live_attachment_authorized": raw_1_sim["hardware_live_attachment_authorized"],
        "g71_e_nd_actuator_tx_count": raw_1_sim["g71_e_nd_actuator_tx_count"],
    }
    p6, meta_6 = _evaluate_pillar_6(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=active_faults,
        p1_meta=p1_meta,
        p2_meta=meta_2,
        p3_meta=meta_3,
        p4_meta=meta_4,
        p5_meta=meta_5,
    )

    pillars = (p1, p2, p3, p4, p5, p6)
    passed_count = sum(1 for p in pillars if p.passed)
    failed_ids = tuple(p.pillar_id for p in pillars if not p.passed)
    all_errors: List[str] = []
    for p in pillars:
        all_errors.extend(p.errors)
    all_ready = passed_count == 6 and len(failed_ids) == 0 and len(all_errors) == 0

    mode_str = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"
    total_raw_leaked = (
        int(raw_1_sim["raw_firmware_bytes_leaked"])
        + int(meta_2["raw_firmware_bytes_leaked"])
        + int(meta_3["raw_firmware_bytes_leaked"])
        + int(meta_4["raw_firmware_bytes_leaked"])
        + int(meta_5["p186_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p204_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p216_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p227_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p248_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p261_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p275_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p279_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p284_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p291_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p302_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p307_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p316_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p321_sim_raw_firmware_bytes_leaked"])
        + int(meta_6["qemu_raw_firmware_bytes_leaked"])
    )
    total_usb_pkts = (
        int(raw_1_sim["usb_packets_transmitted"])
        + int(meta_2["physical_usb_packets_emitted"])
        + int(meta_5["p186_sim_usb_packets_emitted"])
        + int(meta_5["p204_sim_usb_packets_emitted"])
        + int(meta_5["p216_sim_usb_packets_transmitted"])
        + int(meta_5["p227_sim_usb_packets_transmitted"])
        + int(meta_5["p248_sim_usb_packets_transmitted"])
        + int(meta_5["p261_sim_usb_packets_transmitted"])
        + int(meta_5["p275_sim_usb_packets_transmitted"])
        + int(meta_5["p279_sim_usb_packets_transmitted"])
        + int(meta_5["p284_sim_usb_packets_transmitted"])
        + int(meta_5["p291_sim_usb_packets_transmitted"])
        + int(meta_5["p302_sim_usb_packets_transmitted"])
        + int(meta_5["p307_sim_usb_packets_transmitted"])
        + int(meta_5["p316_sim_usb_packets_transmitted"])
        + int(meta_5["p321_sim_usb_packets_transmitted"])
    )
    total_passive_tx = (
        int(meta_2["passive_tx_bytes"])
        + max(0, int(meta_5["p275_sim_passive_tx_bytes_emitted"]))
        + max(0, int(meta_5["p279_sim_passive_tx_bytes_emitted"]))
        + max(0, int(meta_5["p284_sim_passive_tx_bytes_emitted"]))
        + max(0, int(meta_5["p291_sim_passive_tx_bytes_emitted"]))
        + max(0, int(meta_5["p302_sim_passive_tx_bytes_emitted"]))
        + max(0, int(meta_5["p307_sim_passive_tx_bytes_emitted"]))
        + max(0, int(meta_5["p316_sim_passive_tx_bytes_emitted"]))
        + max(0, int(meta_5["p321_sim_passive_tx_bytes_emitted"]))
    )
    total_phys_dev_writes = int(meta_2["physical_device_writes"]) + int(
        meta_4["physical_device_writes"]
    )
    total_end_tx = (
        max(0, int(p1.evidence["g71_e_nd_actuator_tx_count"]))
        + int(meta_3["e_nd_actuator_tx_count"])
        + int(meta_4["e_nd_actuator_tx_count"])
        + max(0, int(meta_5["p204_e_nd_actuator_tx_count"]))
        + max(0, int(meta_5["p261_e_nd_uart_bytes_transmitted"]))
        + max(0, int(meta_5["p316_e_nd_actuator_tx_count"]))
        + max(0, int(meta_5["p321_e_nd_actuator_tx_count"]))
    )
    total_rf_pkts = (
        max(0, int(meta_5["p307_wireless_rf_packets_emitted"]))
        + max(0, int(meta_5["p316_wireless_rf_packets_emitted"]))
        + max(0, int(meta_5["p316_rf_packets_transmitted"]))
        + max(0, int(meta_5["p321_wireless_rf_packets_emitted"]))
        + max(0, int(meta_5["p321_rf_packets_transmitted"]))
    )
    total_slot1_writes = (
        max(0, int(meta_5["p307_slot1_data_sector_writes"]))
        + max(0, int(meta_5["p316_slot1_data_sector_writes"]))
        + max(0, int(meta_5["p321_slot1_data_sector_writes"]))
    )
    min_h0_eq_h3 = min(
        int(meta_5["h0_equals_h3_count"]),
        int(meta_5["p186_h0_equals_h3_count"]),
        int(meta_5["p204_h0_equals_h3_count"]),
        int(meta_5["p216_h0_equals_h3_count"]),
        int(meta_5["p227_h0_equals_h3_count"]),
        int(meta_5["p248_h0_equals_h3_count"]),
        int(meta_5["p261_h0_equals_h3_count"]),
        int(meta_5["p275_h0_equals_h3_count"]),
        int(meta_5["p279_h0_equals_h3_count"]),
        int(meta_5["p284_h0_equals_h3_count"]),
        int(meta_5["p291_h0_equals_h3_count"]),
        int(meta_5["p302_h0_equals_h3_count"]),
        int(meta_5["p307_h0_equals_h3_count"]),
        int(meta_5["p316_h0_equals_h3_count"]),
        int(meta_5["p321_h0_equals_h3_count"]),
    )
    overall_ready_attach = bool(
        raw_1_off["overall_ready_for_hardware_attach"]
        or raw_1_sim["overall_ready_for_hardware_attach"]
        or meta_5["overall_ready_for_hardware_attach"]
    )
    cross_model_flash_auth = bool(
        raw_1_off.get("cross_model_flash_authorized", False)
        or raw_1_sim.get("cross_model_flash_authorized", False)
    )

    common_fields: Dict[str, Any] = {
        "schema": REALHW_MILESTONE324_SCHEMA,
        "schema_version": REALHW_MILESTONE324_SCHEMA,
        "phase_version": PHASE_324_VERSION,
        "verification_mode": mode_str,
        "all_pillars_milestone_ready": all_ready,
        "status": STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        "o_rdonly_enforced": True,
        "cnflasha_userspace_write_blocked": bool(meta_2["cnflasha_userspace_write_blocked"]),
        "agent_auto_flash_blocked": bool(raw_1_sim["agent_auto_flash_blocked"]),
        "cross_model_flash_authorized": cross_model_flash_auth,
        "overall_ready_for_hardware_attach": overall_ready_attach,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "isp_write_authorized": ISP_WRITE_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "hardware_live_attachment_requirements": HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
        "usb_packets_transmitted": total_usb_pkts,
        "physical_usb_packets_emitted": total_usb_pkts,
        "physical_device_writes": total_phys_dev_writes,
        "raw_firmware_bytes_leaked": total_raw_leaked,
        "e_nd_actuator_tx_count": total_end_tx,
        "emmc_write_count": int(meta_6["qemu_real_kernel_emmc_writes"]),
        "rf_packets_transmitted": total_rf_pkts,
        "slot1_data_sector_writes": total_slot1_writes,
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "wbi_p5_write_and_hibernation_forbidden": WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        "cp_mutation_bytes": meta_4["cp_mutation_bytes"],
        "wbi_mutation_bytes": meta_3["wbi_mutation_bytes"],
        "calibration_mutation_bytes": meta_3["calibration_mutation_bytes"],
        "usb_or_camera_operations": USB_OR_CAMERA_OPERATIONS,
        "otp_fuse_writes": meta_2["otp_fuse_writes"],
        "otp_fuse_touches": meta_2["otp_fuse_writes"],
        "rpmb_writes": meta_2["rpmb_writes"],
        "rpmb_counter_increments": meta_2["rpmb_writes"],
        "passive_tx_bytes": total_passive_tx,
        "passive_tx_bytes_emitted": total_passive_tx,
        "temp_dir_cleaned": True,
        "pillar_count": len(pillars),
        "passed_pillar_count": passed_count,
        "failed_pillar_ids": failed_ids,
        "gate142_total_gates": raw_1_sim["total_gates"],
        "gate142_offline_verified": raw_1_off["verified_gates"],
        "gate142_simulated_verified": raw_1_sim["verified_gates"],
        "gate142_all_verified": bool(raw_1_sim.get("all_n_gates_verified", False)),
        "recovery_status": meta_2["recovery_status"],
        "recovery_pillar_count": meta_2["recovery_pillar_count"],
        "recovery_pillars_passed": meta_2["recovery_pillars_passed"],
        "auditors_total": meta_3["auditor_count"],
        "auditors_passed": meta_3["passed_count"],
        "firmware_lab_auditor_count": meta_3["auditor_count"],
        "firmware_lab_auditors_passed": meta_3["passed_count"],
        "vm_stages_total": meta_4["stage_count"],
        "vm_stages_passed": meta_4["passed_count"],
        "vm_coemulation_stage_count": meta_4["stage_count"],
        "vm_coemulation_stages_passed": meta_4["passed_count"],
        "vm_physical_device_writes": meta_4["physical_device_writes"],
        "vm_raw_firmware_bytes_leaked": meta_4["raw_firmware_bytes_leaked"],
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
        "p186_offline_go_no_go": meta_5["p186_offline_go_no_go"],
        "p186_sim_go_no_go": meta_5["p186_sim_go_no_go"],
        "p186_sim_gates_passed": meta_5["p186_sim_gates_passed"],
        "p186_card_insert_authorized": meta_5["p186_card_insert_authorized"],
        "p186_h0_equals_h3_count": meta_5["p186_h0_equals_h3_count"],
        "p204_offline_go_no_go": meta_5["p204_offline_go_no_go"],
        "p204_sim_go_no_go": meta_5["p204_sim_go_no_go"],
        "p204_sim_groups_passed": meta_5["p204_sim_groups_passed"],
        "p204_hardware_live_attachment_authorized": meta_5[
            "p204_hardware_live_attachment_authorized"
        ],
        "p204_h0_equals_h3_count": meta_5["p204_h0_equals_h3_count"],
        "p204_e_nd_actuator_tx_count": meta_5["p204_e_nd_actuator_tx_count"],
        "p216_offline_go_no_go": meta_5["p216_offline_go_no_go"],
        "p216_sim_go_no_go": meta_5["p216_sim_go_no_go"],
        "p216_sim_checklists_passed": meta_5["p216_sim_checklists_passed"],
        "p216_hardware_live_attachment_authorized": meta_5[
            "p216_hardware_live_attachment_authorized"
        ],
        "p216_h0_equals_h3_count": meta_5["p216_h0_equals_h3_count"],
        "p227_offline_go_no_go": meta_5["p227_offline_go_no_go"],
        "p227_sim_go_no_go": meta_5["p227_sim_go_no_go"],
        "p227_sim_check_groups_passed": meta_5["p227_sim_check_groups_passed"],
        "p227_hardware_live_attachment_authorized": meta_5[
            "p227_hardware_live_attachment_authorized"
        ],
        "p227_h0_equals_h3_count": meta_5["p227_h0_equals_h3_count"],
        "p248_offline_go_no_go": meta_5["p248_offline_go_no_go"],
        "p248_sim_go_no_go": meta_5["p248_sim_go_no_go"],
        "p248_sim_check_groups_passed": meta_5["p248_sim_check_groups_passed"],
        "p248_hardware_live_attachment_authorized": meta_5[
            "p248_hardware_live_attachment_authorized"
        ],
        "p248_h0_equals_h3_count": meta_5["p248_h0_equals_h3_count"],
        "p261_offline_go_no_go": meta_5["p261_offline_go_no_go"],
        "p261_sim_go_no_go": meta_5["p261_sim_go_no_go"],
        "p261_sim_check_groups_passed": meta_5["p261_sim_check_groups_passed"],
        "p261_hardware_live_attachment_authorized": meta_5[
            "p261_hardware_live_attachment_authorized"
        ],
        "p261_h0_equals_h3_count": meta_5["p261_h0_equals_h3_count"],
        "p261_e_nd_uart_bytes_transmitted": meta_5["p261_e_nd_uart_bytes_transmitted"],
        "p275_offline_go_no_go": meta_5["p275_offline_go_no_go"],
        "p275_sim_go_no_go": meta_5["p275_sim_go_no_go"],
        "p275_sim_check_groups_passed": meta_5["p275_sim_check_groups_passed"],
        "p275_hardware_live_attachment_authorized": meta_5[
            "p275_hardware_live_attachment_authorized"
        ],
        "p275_h0_equals_h3_count": meta_5["p275_h0_equals_h3_count"],
        "p279_offline_go_no_go": meta_5["p279_offline_go_no_go"],
        "p279_sim_go_no_go": meta_5["p279_sim_go_no_go"],
        "p279_sim_check_groups_passed": meta_5["p279_sim_check_groups_passed"],
        "p279_hardware_live_attachment_authorized": meta_5[
            "p279_hardware_live_attachment_authorized"
        ],
        "p279_h0_equals_h3_count": meta_5["p279_h0_equals_h3_count"],
        "p284_offline_go_no_go": meta_5["p284_offline_go_no_go"],
        "p284_sim_go_no_go": meta_5["p284_sim_go_no_go"],
        "p284_sim_check_groups_passed": meta_5["p284_sim_check_groups_passed"],
        "p284_hardware_live_attachment_authorized": meta_5[
            "p284_hardware_live_attachment_authorized"
        ],
        "p284_h0_equals_h3_count": meta_5["p284_h0_equals_h3_count"],
        "p291_offline_go_no_go": meta_5["p291_offline_go_no_go"],
        "p291_sim_go_no_go": meta_5["p291_sim_go_no_go"],
        "p291_sim_check_groups_passed": meta_5["p291_sim_check_groups_passed"],
        "p291_hardware_live_attachment_authorized": meta_5[
            "p291_hardware_live_attachment_authorized"
        ],
        "p291_h0_equals_h3_count": meta_5["p291_h0_equals_h3_count"],
        "p302_offline_go_no_go": meta_5["p302_offline_go_no_go"],
        "p302_sim_go_no_go": meta_5["p302_sim_go_no_go"],
        "p302_sim_check_groups_passed": meta_5["p302_sim_check_groups_passed"],
        "p302_hardware_live_attachment_authorized": meta_5[
            "p302_hardware_live_attachment_authorized"
        ],
        "p302_h0_equals_h3_count": meta_5["p302_h0_equals_h3_count"],
        "p307_offline_go_no_go": meta_5["p307_offline_go_no_go"],
        "p307_sim_go_no_go": meta_5["p307_sim_go_no_go"],
        "p307_sim_check_groups_passed": meta_5["p307_sim_check_groups_passed"],
        "p307_hardware_live_attachment_authorized": meta_5[
            "p307_hardware_live_attachment_authorized"
        ],
        "p307_h0_equals_h3_count": meta_5["p307_h0_equals_h3_count"],
        "p307_wireless_rf_packets_emitted": meta_5["p307_wireless_rf_packets_emitted"],
        "p307_slot1_data_sector_writes": meta_5["p307_slot1_data_sector_writes"],
        "p316_offline_go_no_go": meta_5["p316_offline_go_no_go"],
        "p316_sim_go_no_go": meta_5["p316_sim_go_no_go"],
        "p316_sim_check_groups_passed": meta_5["p316_sim_check_groups_passed"],
        "p316_hardware_live_attachment_authorized": meta_5[
            "p316_hardware_live_attachment_authorized"
        ],
        "p316_h0_equals_h3_count": meta_5["p316_h0_equals_h3_count"],
        "p316_wireless_rf_packets_emitted": meta_5["p316_wireless_rf_packets_emitted"],
        "p316_rf_packets_transmitted": meta_5["p316_rf_packets_transmitted"],
        "p316_e_nd_actuator_tx_count": meta_5["p316_e_nd_actuator_tx_count"],
        "p316_slot1_data_sector_writes": meta_5["p316_slot1_data_sector_writes"],
        "p321_offline_go_no_go": meta_5["p321_offline_go_no_go"],
        "p321_sim_go_no_go": meta_5["p321_sim_go_no_go"],
        "p321_sim_check_groups_passed": meta_5["p321_sim_check_groups_passed"],
        "p321_hardware_live_attachment_authorized": meta_5[
            "p321_hardware_live_attachment_authorized"
        ],
        "p321_h0_equals_h3_count": meta_5["p321_h0_equals_h3_count"],
        "p321_wireless_rf_packets_emitted": meta_5["p321_wireless_rf_packets_emitted"],
        "p321_rf_packets_transmitted": meta_5["p321_rf_packets_transmitted"],
        "p321_e_nd_actuator_tx_count": meta_5["p321_e_nd_actuator_tx_count"],
        "p321_slot1_data_sector_writes": meta_5["p321_slot1_data_sector_writes"],
        "h0_equals_h3_count": min_h0_eq_h3,
        "qemu_rounds_total": meta_6["qemu_rounds_total"],
        "qemu_rounds_verified": meta_6["qemu_rounds_verified"],
        "qemu_runs_total": meta_6["qemu_runs_total"],
        "qemu_runs_verified": meta_6["qemu_runs_verified"],
        "qemu_png_receipts_total": meta_6["qemu_png_receipts_total"],
        "qemu_png_receipts_verified": meta_6["qemu_png_receipts_verified"],
        "qemu_png_max_bytes": meta_6["qemu_png_max_bytes"],
        "qemu_round_runs_by_round": meta_6["qemu_round_runs_by_round"],
        "qemu_real_kernel_nop_count": meta_6["qemu_real_kernel_nop_count"],
        "qemu_real_kernel_crashes": meta_6["qemu_real_kernel_crashes"],
        "qemu_real_kernel_emmc_writes": meta_6["qemu_real_kernel_emmc_writes"],
        "errors": tuple(all_errors),
    }
    payload_no_sha = {**common_fields, "pillars": [p.to_dict() for p in pillars]}
    digest = compute_milestone324_sha256(payload_no_sha)

    return RealHwMilestone324MasterGateReport(
        **common_fields,
        pillars=pillars,
        milestone324_sha256=digest,
    )


build_realhw_milestone324_master_gate_report = evaluate_realhw_milestone324_master_gate
evaluate_milestone_324_master_gate = evaluate_realhw_milestone324_master_gate
evaluate_milestone324_master_gate = evaluate_realhw_milestone324_master_gate


def verify_realhw_milestone324_master_gate(
    report: object,
) -> RealHwMilestone324VerifyResult:
    """Fail-closed verifier for a Grand Milestone Phase 324 Real-Hardware Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, RealHwMilestone324MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return RealHwMilestone324VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone324_sha256="",
            observed_milestone324_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or RealHwMilestone324MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = (
        payload.get("schema") == REALHW_MILESTONE324_SCHEMA
        and payload.get("schema_version") == REALHW_MILESTONE324_SCHEMA
        and payload.get("phase_version") == PHASE_324_VERSION
    )
    if not schema_ok:
        errors.append(
            f"schema mismatch: schema={payload.get('schema')!r} schema_version={payload.get('schema_version')!r}"
        )

    expected_sha = compute_milestone324_sha256(payload)
    observed_sha = str(payload.get("milestone324_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(
            f"milestone324_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}"
        )

    redlines_ok = (
        payload.get("o_rdonly_enforced") is True
        and payload.get("cnflasha_userspace_write_blocked") is True
        and payload.get("agent_auto_flash_blocked") is True
        and payload.get("cross_model_flash_authorized") is False
        and payload.get("overall_ready_for_hardware_attach") is False
        and payload.get("persistent_emmc_writes_authorized") is False
        and payload.get("persistent_write_release") is False
        and payload.get("spi_nor_write_authorized") is False
        and payload.get("el3_payload_transmit_authorized") is False
        and payload.get("isp_write_authorized") is False
        and payload.get("hardware_live_attachment_authorized") is False
        and payload.get("usb_packets_transmitted") == 0
        and payload.get("physical_usb_packets_emitted") == 0
        and payload.get("physical_device_writes") == 0
        and payload.get("raw_firmware_bytes_leaked") == 0
        and payload.get("e_nd_actuator_tx_count") == 0
        and payload.get("emmc_write_count") == 0
        and payload.get("rf_packets_transmitted") == 0
        and payload.get("slot1_data_sector_writes") == 0
        and payload.get("p8_cp_mutation_forbidden") is True
        and payload.get("wbi_p5_write_and_hibernation_forbidden") is True
        and payload.get("cp_mutation_bytes") == 0
        and payload.get("wbi_mutation_bytes") == 0
        and payload.get("calibration_mutation_bytes") == 0
        and payload.get("usb_or_camera_operations") == 0
        and payload.get("otp_fuse_writes") == 0
        and payload.get("otp_fuse_touches") == 0
        and payload.get("rpmb_writes") == 0
        and payload.get("rpmb_counter_increments") == 0
        and payload.get("passive_tx_bytes") == 0
        and payload.get("passive_tx_bytes_emitted") == 0
        and payload.get("p154_usb_packets_emitted") == 0
        and payload.get("p154_iokit_handles_opened") == 0
        and payload.get("p186_card_insert_authorized") is False
        and payload.get("p204_hardware_live_attachment_authorized") is False
        and payload.get("p204_e_nd_actuator_tx_count") == 0
        and payload.get("p216_hardware_live_attachment_authorized") is False
        and payload.get("p227_hardware_live_attachment_authorized") is False
        and payload.get("p248_hardware_live_attachment_authorized") is False
        and payload.get("p261_hardware_live_attachment_authorized") is False
        and payload.get("p261_e_nd_uart_bytes_transmitted") == 0
        and payload.get("p275_hardware_live_attachment_authorized") is False
        and payload.get("p279_hardware_live_attachment_authorized") is False
        and payload.get("p284_hardware_live_attachment_authorized") is False
        and payload.get("p291_hardware_live_attachment_authorized") is False
        and payload.get("p302_hardware_live_attachment_authorized") is False
        and payload.get("p307_hardware_live_attachment_authorized") is False
        and payload.get("p307_wireless_rf_packets_emitted") == 0
        and payload.get("p307_slot1_data_sector_writes") == 0
        and payload.get("p316_hardware_live_attachment_authorized") is False
        and payload.get("p316_wireless_rf_packets_emitted") == 0
        and payload.get("p316_rf_packets_transmitted") == 0
        and payload.get("p316_e_nd_actuator_tx_count") == 0
        and payload.get("p316_slot1_data_sector_writes") == 0
        and payload.get("p321_hardware_live_attachment_authorized") is False
        and payload.get("p321_wireless_rf_packets_emitted") == 0
        and payload.get("p321_rf_packets_transmitted") == 0
        and payload.get("p321_e_nd_actuator_tx_count") == 0
        and payload.get("p321_slot1_data_sector_writes") == 0
    )
    if not redlines_ok:
        errors.append(
            "hard-locked zero-write / cnflasha-RO / zero-cross-model / zero-SPI-NOR / zero-EL3 / "
            "zero-USB-TX / zero-RF / zero-Slot1 / zero-leak / zero-attach redlines breached"
        )

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

    g_total = int(payload.get("gate142_total_gates", -1))
    g_off = int(payload.get("gate142_offline_verified", -1))
    g_sim = int(payload.get("gate142_simulated_verified", -1))
    rec_total = int(payload.get("recovery_pillar_count", -1))
    rec_passed = int(payload.get("recovery_pillars_passed", -2))
    aud_total = int(payload.get("auditors_total", -1))
    aud_passed = int(payload.get("auditors_passed", -2))
    vm_total = int(payload.get("vm_stages_total", -1))
    vm_passed = int(payload.get("vm_stages_passed", -2))
    q_rounds_tot = int(payload.get("qemu_rounds_total", -1))
    q_rounds_ver = int(payload.get("qemu_rounds_verified", -2))
    q_runs_tot = int(payload.get("qemu_runs_total", -1))
    q_runs_ver = int(payload.get("qemu_runs_verified", -2))
    q_pngs_tot = int(payload.get("qemu_png_receipts_total", -1))
    q_pngs_ver = int(payload.get("qemu_png_receipts_verified", -2))

    counts_ok = (
        g_total >= 142
        and g_off >= g_total - 3
        and g_off == g_total - 3
        and g_sim >= 142
        and g_sim == g_total
        and payload.get("gate142_all_verified") is True
        and rec_total >= 56
        and rec_passed == rec_total
        and aud_passed >= 45
        and aud_passed == aud_total
        and vm_passed >= 66
        and vm_passed == vm_total
        and int(payload.get("vm_physical_device_writes", -1)) == 0
        and int(payload.get("vm_raw_firmware_bytes_leaked", -1)) == 0
        and int(payload.get("vm_emmc_corruptions", -1)) == 0
        and int(payload.get("vm_wf12_00342260_hits", -1)) == 0
        and int(payload.get("p136_u6_command_count", -1)) >= 19
        and payload.get("p136_u4_u5_u6_closed") is True
        and int(payload.get("p143_sd_escape_absent_us", 999)) <= 50
        and int(payload.get("p143_h0_equals_h3_count", -1)) == 16
        and int(payload.get("p143_h0_h3_surface_count", -1)) == 16
        and payload.get("p154_bench_go") is True
        and payload.get("p186_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p186_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p186_sim_gates_passed", -1)) >= 4
        and int(payload.get("p186_h0_equals_h3_count", -1)) == 16
        and payload.get("p204_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p204_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p204_sim_groups_passed", -1)) >= 3
        and int(payload.get("p204_h0_equals_h3_count", -1)) == 16
        and payload.get("p216_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p216_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p216_sim_checklists_passed", -1)) >= 5
        and int(payload.get("p216_h0_equals_h3_count", -1)) == 16
        and payload.get("p227_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p227_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p227_sim_check_groups_passed", -1)) >= 3
        and int(payload.get("p227_h0_equals_h3_count", -1)) == 16
        and payload.get("p248_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p248_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p248_sim_check_groups_passed", -1)) >= 4
        and int(payload.get("p248_h0_equals_h3_count", -1)) == 16
        and payload.get("p261_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p261_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p261_sim_check_groups_passed", -1)) >= 4
        and int(payload.get("p261_h0_equals_h3_count", -1)) == 16
        and payload.get("p275_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p275_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p275_sim_check_groups_passed", -1)) >= 4
        and int(payload.get("p275_h0_equals_h3_count", -1)) == 16
        and payload.get("p279_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p279_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p279_sim_check_groups_passed", -1)) >= 4
        and int(payload.get("p279_h0_equals_h3_count", -1)) == 16
        and payload.get("p284_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p284_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p284_sim_check_groups_passed", -1)) >= 4
        and int(payload.get("p284_h0_equals_h3_count", -1)) == 16
        and payload.get("p291_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p291_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p291_sim_check_groups_passed", -1)) >= 4
        and int(payload.get("p291_h0_equals_h3_count", -1)) == 16
        and payload.get("p302_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p302_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p302_sim_check_groups_passed", -1)) >= 4
        and int(payload.get("p302_h0_equals_h3_count", -1)) == 16
        and payload.get("p307_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p307_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p307_sim_check_groups_passed", -1)) >= 4
        and int(payload.get("p307_h0_equals_h3_count", -1)) == 16
        and payload.get("p316_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p316_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p316_sim_check_groups_passed", -1)) >= 4
        and int(payload.get("p316_h0_equals_h3_count", -1)) == 16
        and payload.get("p321_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p321_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p321_sim_check_groups_passed", -1)) >= 4
        and int(payload.get("p321_h0_equals_h3_count", -1)) == 16
        and int(payload.get("h0_equals_h3_count", -1)) == 16
        and q_rounds_ver >= 38
        and q_rounds_ver == q_rounds_tot
        and q_runs_ver >= 114
        and q_runs_ver == q_runs_tot
        and q_pngs_ver >= 76
        and q_pngs_ver == q_pngs_tot
        and 0 < int(payload.get("qemu_png_max_bytes", -1)) < PNG_MAX_SIZE_50KIB_BYTES
        and int(payload.get("qemu_real_kernel_nop_count", -1)) == 0
        and int(payload.get("qemu_real_kernel_crashes", -1)) == 0
        and int(payload.get("qemu_real_kernel_emmc_writes", -1)) == 0
    )
    if not counts_ok:
        errors.append("milestone324 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append(
            "all_pillars_milestone_ready / status is not MILESTONE_324_PREBENCH_MASTER_VERIFIED"
        )

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 324 payload")

    valid = bool(
        schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0
    )
    return RealHwMilestone324VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone324_sha256=expected_sha,
        observed_milestone324_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


verify_milestone_324_master_gate = verify_realhw_milestone324_master_gate


def render_milestone324_markdown(report: RealHwMilestone324MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 324 Master Gate."""
    lines = [
        f"# Grand Milestone Phase 324 — Real-Hardware `ILME-FX3 Ver. 7.02` 6-Pillar Master Gate (`{report.schema}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone324_sha256}`",
        "",
        "## Hard-Locked Safety Redlines / 硬锁定安全红线",
        f"- `overall_ready_for_hardware_attach = {report.overall_ready_for_hardware_attach}`, "
        f"`hardware_live_attachment_authorized = {report.hardware_live_attachment_authorized}`, "
        f"`cnflasha_userspace_write_blocked = {report.cnflasha_userspace_write_blocked}`, "
        f"`persistent_emmc_writes_authorized = {report.persistent_emmc_writes_authorized}`, "
        f"`cross_model_flash_authorized = {report.cross_model_flash_authorized}`, "
        f"`spi_nor_write_authorized = {report.spi_nor_write_authorized}`, "
        f"`el3_payload_transmit_authorized = {report.el3_payload_transmit_authorized}`",
        f"- `usb_packets_transmitted = {report.usb_packets_transmitted}`, "
        f"`physical_device_writes = {report.physical_device_writes}`, "
        f"`raw_firmware_bytes_leaked = {report.raw_firmware_bytes_leaked}`, "
        f"`e_nd_actuator_tx_count = {report.e_nd_actuator_tx_count}`, "
        f"`otp_fuse_touches = {report.otp_fuse_touches}`, "
        f"`rpmb_counter_increments = {report.rpmb_counter_increments}`, "
        f"`passive_tx_bytes_emitted = {report.passive_tx_bytes_emitted}`, "
        f"`rf_packets_transmitted = {report.rf_packets_transmitted}`, "
        f"`slot1_data_sector_writes = {report.slot1_data_sector_writes}`",
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
            "## Key Grand Milestone Phase 324 Metrics / 实机总闭环核心指标",
            f"- 142+-Gate Preflight (`G01..G{report.gate142_total_gates}`): offline=`{report.gate142_offline_verified}/{report.gate142_total_gates}` (`G10..G12` locked), simulated=`{report.gate142_simulated_verified}/{report.gate142_total_gates}` (`gate142_all_verified={report.gate142_all_verified}`, `cross_model_flash={report.cross_model_flash_authorized}`)",
            f"- 56+-Pillar Recovery Master (`verify-{report.recovery_pillar_count}pillar-recovery`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`{report.recovery_status}`, `cnflasha_ro={report.cnflasha_userspace_write_blocked}`)",
            f"- 45+ Firmware-Lab Auditors (`auditors_passed >= 45`): `{report.auditors_passed}/{report.auditors_total}` (`raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`)",
            f"- 66+ Stage VM HIL Co-Emulation (`vm_stages_passed >= 66`): `{report.vm_stages_passed}/{report.vm_stages_total}` (`physical_device_writes={report.vm_physical_device_writes}`, `emmc_corruptions={report.vm_emmc_corruptions}`)",
            f"- Tetradecuple (14/14) Bench Readiness Preflights (`Ph186..Ph321`): `Ph186={report.p186_offline_go_no_go}/{report.p186_sim_go_no_go}`, `Ph204={report.p204_offline_go_no_go}/{report.p204_sim_go_no_go}`, `Ph216={report.p216_offline_go_no_go}/{report.p216_sim_go_no_go}`, `Ph227={report.p227_offline_go_no_go}/{report.p227_sim_go_no_go}`, `Ph248={report.p248_offline_go_no_go}/{report.p248_sim_go_no_go}`, `Ph261={report.p261_offline_go_no_go}/{report.p261_sim_go_no_go}`, `Ph275={report.p275_offline_go_no_go}/{report.p275_sim_go_no_go}`, `Ph279={report.p279_offline_go_no_go}/{report.p279_sim_go_no_go}`, `Ph284={report.p284_offline_go_no_go}/{report.p284_sim_go_no_go}`, `Ph291={report.p291_offline_go_no_go}/{report.p291_sim_go_no_go}`, `Ph302={report.p302_offline_go_no_go}/{report.p302_sim_go_no_go}`, `Ph307={report.p307_offline_go_no_go}/{report.p307_sim_go_no_go}`, `Ph316={report.p316_offline_go_no_go}/{report.p316_sim_go_no_go}`, `Ph321={report.p321_offline_go_no_go}/{report.p321_sim_go_no_go}` (`H0==H3={report.h0_equals_h3_count}/16`)",
            f"- Live FX3 `7.02` (`4.9.337-scel+`) QEMU Receipts (`Rounds 28..65+`): `{report.qemu_rounds_verified}/{report.qemu_rounds_total}` rounds (`{report.qemu_runs_verified}/{report.qemu_runs_total}` sub-runs, `PNGs={report.qemu_png_receipts_verified}/{report.qemu_png_receipts_total}` max=`{report.qemu_png_max_bytes}B < 50KiB`), `nop={report.qemu_real_kernel_nop_count}`, `crashes={report.qemu_real_kernel_crashes}`, `emmc_writes={report.qemu_real_kernel_emmc_writes}`",
            "",
        ]
    )
    return "\n".join(lines)


def verify_milestone_324_cli(
    argv: Optional[Sequence[str]] = None,
    *,
    repo_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    simulate_bench_dry_run: Optional[bool] = None,
    json_output: bool = False,
    markdown_out: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> int:
    """Execute `verify-milestone-324` CLI supporting `--clean-room`/`--force-clean-room`/`--simulate-bench-dry-run`/`--json`/`--out`."""
    if argv is not None:
        parser = argparse.ArgumentParser(prog="verify-milestone-324")
        parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
        parser.add_argument("--fx6-lib-dir", type=Path, default=DEFAULT_FX6_DONOR_LIB_DIR)
        parser.add_argument("--fx3-modules-dir", type=Path, default=DEFAULT_FX3_MODULES_DIR)
        parser.add_argument(
            "--force-clean-room",
            "--clean-room",
            dest="force_clean_room",
            action="store_true",
        )
        parser.add_argument(
            "--simulate-bench-dry-run",
            "--simulate-ready-bench",
            dest="simulate_bench_dry_run",
            action="store_true",
        )
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--output", "--out", dest="output", type=Path, default=None)
        parser.add_argument("--markdown-out", type=Path, default=None)
        ns = parser.parse_args(list(argv))
        repo_root = ns.repo_root
        fx6_lib_dir = ns.fx6_lib_dir
        fx3_modules_dir = ns.fx3_modules_dir
        force_clean_room = True if ns.force_clean_room else None
        simulate_bench_dry_run = bool(ns.simulate_bench_dry_run)
        json_output = bool(ns.json)
        output_path = ns.output
        markdown_out = ns.markdown_out

    rep = evaluate_realhw_milestone324_master_gate(
        repo_root=repo_root or DEFAULT_REPO_ROOT,
        fx6_lib_dir=fx6_lib_dir or DEFAULT_FX6_DONOR_LIB_DIR,
        fx3_modules_dir=fx3_modules_dir or DEFAULT_FX3_MODULES_DIR,
        force_clean_room=force_clean_room,
        simulate_bench_dry_run=simulate_bench_dry_run,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone324_markdown(rep), encoding="utf-8")
    v_res = verify_realhw_milestone324_master_gate(rep.to_dict())
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
                f"gate142={rep.gate142_offline_verified}/{rep.gate142_simulated_verified} "
                f"recovery={rep.recovery_pillars_passed}/{rep.recovery_pillar_count} "
                f"cnflasha_ro={rep.cnflasha_userspace_write_blocked} "
                f"otp={rep.otp_fuse_touches} "
                f"rpmb={rep.rpmb_counter_increments} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"auditors={rep.auditors_passed}/{rep.auditors_total} "
                f"vm_stages={rep.vm_stages_passed}/{rep.vm_stages_total} "
                f"p186={rep.p186_offline_go_no_go}/{rep.p186_sim_go_no_go} "
                f"p204={rep.p204_offline_go_no_go}/{rep.p204_sim_go_no_go} "
                f"p216={rep.p216_offline_go_no_go}/{rep.p216_sim_go_no_go} "
                f"p227={rep.p227_offline_go_no_go}/{rep.p227_sim_go_no_go} "
                f"p248={rep.p248_offline_go_no_go}/{rep.p248_sim_go_no_go} "
                f"p261={rep.p261_offline_go_no_go}/{rep.p261_sim_go_no_go} "
                f"p275={rep.p275_offline_go_no_go}/{rep.p275_sim_go_no_go} "
                f"p279={rep.p279_offline_go_no_go}/{rep.p279_sim_go_no_go} "
                f"p284={rep.p284_offline_go_no_go}/{rep.p284_sim_go_no_go} "
                f"p291={rep.p291_offline_go_no_go}/{rep.p291_sim_go_no_go} "
                f"p302={rep.p302_offline_go_no_go}/{rep.p302_sim_go_no_go} "
                f"p307={rep.p307_offline_go_no_go}/{rep.p307_sim_go_no_go} "
                f"p316={rep.p316_offline_go_no_go}/{rep.p316_sim_go_no_go} "
                f"p321={rep.p321_offline_go_no_go}/{rep.p321_sim_go_no_go} "
                f"h0_eq_h3={rep.h0_equals_h3_count}/16 "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"rf_pkts={rep.rf_packets_transmitted} "
                f"slot1_writes={rep.slot1_data_sector_writes} "
                f"qemu={rep.qemu_rounds_verified}/{rep.qemu_rounds_total}({rep.qemu_runs_verified}/{rep.qemu_runs_total}) "
                f"pngs={rep.qemu_png_receipts_verified}/{rep.qemu_png_receipts_total}(max={rep.qemu_png_max_bytes}B) "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash_auth={rep.cross_model_flash_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_tx={rep.usb_packets_transmitted} "
                f"leaked={rep.raw_firmware_bytes_leaked} "
                f"milestone324_sha256={rep.milestone324_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 1


__all__ = [
    "AGENT_AUTO_FLASH_BLOCKED",
    "CALIBRATION_MUTATION_BYTES",
    "CNFLASHA_USERSPACE_WRITE_BLOCKED",
    "CP_MUTATION_BYTES",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "DEFAULT_REPO_ROOT",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "EMMC_WRITE_COUNT",
    "E_ND_ACTUATOR_TX_COUNT",
    "FIRMWARE_LAB_45_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "ISP_WRITE_AUTHORIZED",
    "MILESTONE324_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P8_CP_MUTATION_FORBIDDEN",
    "P324_BASELINE_PNG_MAX_OBSERVED_BYTES",
    "P324_PHYSICAL_DEVICE_WRITES",
    "P324_PILLAR_IDS",
    "P324_PILLAR_SPECS",
    "P324_PNG_MAX_SIZE_BYTES",
    "P324_RAW_FIRMWARE_BYTES_LEAKED",
    "P324_SCHEMA",
    "P324_STATUS_FAIL_CLOSED",
    "P324_STATUS_MILESTONE_READY",
    "P324_VERSION",
    "PASSIVE_TX_BYTES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_324_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "PNG_MAGIC_BYTES",
    "PNG_MAX_SIZE_50KIB_BYTES",
    "PNG_MAX_SIZE_BYTES",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_MILESTONE324_SCHEMA",
    "RECOVERY_56_PILLAR_IDS",
    "ROUND28_TO_65_PNG_RECEIPTS",
    "ROUND28_TO_65_SPECS",
    "ROUND63_EXPECTED_SCHEMA",
    "ROUND63_SUMMARY_RELPATH",
    "ROUND64_EXPECTED_SCHEMA",
    "ROUND64_SUMMARY_RELPATH",
    "ROUND65_EXPECTED_SCHEMA",
    "ROUND65_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "RPMB_WRITES",
    "SCHEMA_VERSION",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "USB_PACKETS_TRANSMITTED",
    "VM_COEMULATION_66_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone324PillarResult",
    "RealHwMilestone324FaultInjection",
    "RealHwMilestone324MasterGateReport",
    "RealHwMilestone324VerifyResult",
    "build_realhw_milestone324_master_gate_report",
    "compute_milestone324_sha256",
    "evaluate_milestone324_master_gate",
    "evaluate_milestone_324_master_gate",
    "evaluate_realhw_milestone324_master_gate",
    "render_milestone324_markdown",
    "verify_milestone_324_cli",
    "verify_milestone_324_master_gate",
    "verify_realhw_milestone324_master_gate",
]
