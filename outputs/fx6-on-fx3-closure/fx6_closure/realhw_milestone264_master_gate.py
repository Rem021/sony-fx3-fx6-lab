"""Grand Milestone Phase 264 — 6-Pillar Real-Hardware `ILME-FX3 Ver. 7.02` Master Gate (`realhw_milestone264_master_gate_v1`).

Unites ALL Wave 21–43 Real-Hardware Main Track subsystems (Phases 134–263) and ALL
25+ live Sony ILME-FX3 `Ver. 7.02` (`Linux 4.9.337-scel+`) ARM64 QEMU Rehearsal
Rounds (`Rounds 28..52+`, including the 25th Real-HW / 75th Run Milestone `Round 52`
— `>= 75` sub-runs `r28a..r52c+` + `>= 50` `< 50 KiB` / `51,200 B` PNG receipts)
into a single tamper-evident, fail-closed certificate executing in `< 5.0s` per mode
across both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC`
(`FX3_FX6_FORCE_CLEAN_ROOM=1`) while keeping
`verify-milestone-90/110/130/147/175/193/209/221/233/254` and all 6 bench readiness
preflights (`Ph186`, `Ph204`, `Ph216`, `Ph227`, `Ph248`, `Ph261`) 100% intact and
forward-compatible via `>=` lower bounds:

- `P1` (`SAFETY_102GATE_REALHW_MASTER_PREFLIGHT`):
  Evaluates `fx3_safety.evaluate_102gate_preflight` (`>= 99/102` offline with `3`
  physical Tier-0 receipt gates `G10..G12` fail-closed; `>= 102/102` simulated dry-run
  `--simulate-bench-dry-run` with `all_102_gates_verified == True`), verifying
  `G97..G102` (Wave-39 `Display Quality`/`BT Rmt`/`My Menu`, Wave-40 `Diff Set`/`Custom
  Key`/`Remain Shoot` `100/100` Grand Milestone, Wave-41 `Auto Slow Shutter`/`HDMI REC
  Control`/`Breathing Comp.` `102/102`) with all hardware write/attach flags locked
  `False` and `usb_packets_transmitted == 0`.
- `P2` (`FORTY_FOUR_PILLAR_RECOVERY_MASTER_VAULT`):
  Verifies `>= 44` recovery pillars (`44/44`, `all_passed == True` via
  `fx3_recovery.evaluate_realhw_44pillar_recovery_master`), covering `Pillars 42..44`
  (Wave-40 `Diff Set`/`Custom Key`/`Remain Shoot`, Wave-41 `Auto Slow Shutter`/`HDMI
  REC Control`/`Breathing`, and Wave-42 `260th` Milestone `APS-C S35`/`Face-Eye AF`/
  `Version` read-only vault), locking `cnflasha_userspace_write_blocked == True`,
  `otp_fuse_touches == 0`, `rpmb_counter_increments == 0`,
  `passive_tx_bytes_emitted == 0`, `physical_usb_packets_emitted == 0`, and
  `raw_firmware_bytes_leaked == 0`.
- `P3` (`FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS`):
  Verifies all `>= 45` `fx3_firmware_lab` auditors plus dynamic discovery of any
  newly merged `46th+` `realhw_*_auditor.py`, locking `raw_firmware_bytes_leaked == 0`,
  `e_nd_actuator_tx_count == 0`, and `calibration_mutation_bytes == 0`.
- `P4` (`FIFTY_PLUS_STAGE_VM_HIL_COEMULATION`):
  Runs `fx3_vm_coemulation_suite` with Stages `1..50+` dynamically enabled (`>= 50`
  stages including `Stage 48` `LockOpParts`/`AudioTiming`/`ExpStep`, `Stage 49`
  `DisplayQuality`/`BTRmt`/`MyMenu`, and `50/50` Grand Milestone `Stage 50`
  `DiffSet`/`CustomKey`/`RemainShoot`, plus automatic discovery of `Stage 51+`),
  locking `raw_firmware_bytes_leaked == 0`, `physical_device_writes == 0`, and
  `emmc_corruptions == 0`.
- `P5` (`SEXTUPLE_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216_PH227_PH248_PH261`):
  Verifies `Phase 136`, `Phase 143`, `Phase 154`, AND all 6 Physical Bench Readiness
  Verifiers (`Ph186` card-insert, `Ph204` bench-cable-fan-slot1, `Ph216`
  hdmi-proxy-desqueeze-and-simult, `Ph227` pixelmap-ntscpal-powersave-and-autotemp,
  `Ph248` imagedb-touch-shoeaudio-and-lockop, AND `Ph261`
  `preflight-diffset-customkey-autoslow-and-apsc`) return
  `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` offline and
  `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` in simulated dry-run, with
  `overall_ready_for_hardware_attach == False`, `16/16 H0 == H3`, and `e_nd_tx == 0`.
- `P6` (`REAL_FX3_702_QEMU_ROUNDS_28_TO_52_PLUS_AND_PNG_RECEIPTS`):
  Verifies `>= 25` live `ILME-FX3 Ver. 7.02` ARM64 QEMU rounds through `25th` Real-HW /
  `75th` Run Milestone `Round 52` (`r28..r52+`, dynamically discovering any newly
  merged `r53+` rounds), `>= 75` live sub-runs, `>= 50` sanitized PNG receipts
  (`< 51,200` bytes each), `16/16 H0 == H3`, `emmc_write_count == 0`,
  `e_nd_actuator_tx_count == 0`, and `raw_firmware_bytes_leaked == 0`.
"""

from __future__ import annotations

import argparse
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

from fx3_recovery import (  # noqa: E402
    MASTER_44_PILLAR_IDS,
    evaluate_realhw_44pillar_recovery_master,
)
from fx3_safety import evaluate_102gate_preflight  # noqa: E402
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
from .realhw_diffset_customkey_autoslow_and_apsc_verifier import (  # noqa: E402
    evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness,
    verify_phase261_report,
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
    ROUND28_TO_50_PNG_RECEIPTS,
    ROUND28_TO_50_SPECS,
    VM_COEMULATION_47_STAGE_KEYS,
    RealHwMilestone254FaultInjection,
    _96GATE_EXTRA_FAULT_FIELDS,
    _check_vm_stage45_to_47_redlines,
    _effective_m233_faults,
    _evaluate_pillar_3 as _eval_m254_p3,
    _evaluate_pillar_4 as _eval_m254_p4,
    _evaluate_pillar_5 as _eval_m254_p5,
    _worker_phase248,
)
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_MILESTONE264_SCHEMA: str = "realhw_milestone264_master_gate_v1"
MILESTONE264_SCHEMA_VERSION: str = REALHW_MILESTONE264_SCHEMA
P264_SCHEMA: str = REALHW_MILESTONE264_SCHEMA
SCHEMA_VERSION: str = REALHW_MILESTONE264_SCHEMA
PHASE_264_VERSION: str = "264.0.0"
P264_VERSION: str = PHASE_264_VERSION

PNG_MAX_SIZE_BYTES: int = PNG_MAX_SIZE_50KIB_BYTES  # 51,200 B (< 50 KiB BYOF PNG ceiling)
P264_PNG_MAX_SIZE_BYTES: int = PNG_MAX_SIZE_BYTES
P264_PHYSICAL_DEVICE_WRITES: int = PHYSICAL_DEVICE_WRITES
P264_RAW_FIRMWARE_BYTES_LEAKED: int = RAW_FIRMWARE_BYTES_LEAKED

STATUS_MILESTONE_READY: str = "MILESTONE_264_PREBENCH_MASTER_VERIFIED"
P264_STATUS_MILESTONE_READY: str = STATUS_MILESTONE_READY
P264_STATUS_FAIL_CLOSED: str = STATUS_FAIL_CLOSED

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_102GATE_REALHW_MASTER_PREFLIGHT"),
    ("P2", "FORTY_FOUR_PILLAR_RECOVERY_MASTER_VAULT"),
    ("P3", "FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS"),
    ("P4", "FIFTY_PLUS_STAGE_VM_HIL_COEMULATION"),
    ("P5", "SEXTUPLE_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216_PH227_PH248_PH261"),
    ("P6", "REAL_FX3_702_QEMU_ROUNDS_28_TO_52_PLUS_AND_PNG_RECEIPTS"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)
P264_PILLAR_SPECS: Tuple[Tuple[str, str], ...] = PILLAR_SPECS
P264_PILLAR_IDS: Tuple[str, ...] = PILLAR_IDS

RECOVERY_44_PILLAR_IDS: Tuple[str, ...] = MASTER_44_PILLAR_IDS

VM_COEMULATION_50_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_47_STAGE_KEYS,
    "stage48_realhw_lock_op_parts_audio_timing_exp_step_hil",
    "stage49_realhw_display_quality_bt_rmt_mymenu_hil",
    "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil",
)

ROUND51_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round51-realhw-framing-usbpower-lun-antiflicker-qemu/summary.json"
)
ROUND52_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu/summary.json"
)

ROUND51_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round51-realhw-framing-usbpower-lun-antiflicker-qemu-v1"
)
ROUND52_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu-v1"
)

ROUND28_TO_52_SPECS: Tuple[RoundQemuReceiptSpec, ...] = (
    *ROUND28_TO_50_SPECS,
    RoundQemuReceiptSpec(
        round_num=51,
        summary_relpath=ROUND51_SUMMARY_RELPATH,
        expected_schema=ROUND51_EXPECTED_SCHEMA,
        audit_key="r51_realhw_framing_usbpower_lun_antiflicker_audit",
        audit_bool_keys=(
            "all_3_runs_cnflasha_write_zero",
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r51a_framing_settings_asymmetric_crop_hdmi_no_zve1_autoframing_and_raw_lockout_verified",
            "r51a_stageb_big6_sid_0a_exact_346686_pixels_verified",
            "r51b_usb_power_npfz100_typec_exclusive_and_usb_lun_camreset_survival_verified",
            "r51c_antiflicker_mech_still_only_and_no_var_shutter_guard_verified",
            "r51c_dlopen_libjit_and_16_h0_eq_h3_rollback_verified",
        ),
        run_specs=(
            ("r51a_framing_crop_hdmi_big6_schinese", 1),
            ("r51b_usb_power_npfz100_and_usb_lun_guard", 1),
            ("r51c_antiflicker_mech_still_no_var_shutter_h0_h3", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=52,
        summary_relpath=ROUND52_SUMMARY_RELPATH,
        expected_schema=ROUND52_EXPECTED_SCHEMA,
        audit_key="r52_realhw_lock_op_parts_audio_timing_exp_step_audit",
        audit_bool_keys=(
            "all_3_runs_cnflasha_write_zero",
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r52a_lock_op_parts_menu_fn_5s_chord_no_menu_delete_confusion_and_mydial_override_verified",
            "r52a_stageb_big6_sid_0a_exact_346686_pixels_verified",
            "r52b_audio_out_timing_vs_audio_signals_and_silent_mode_mute_guard_verified",
            "r52c_dlopen_libjit_and_16_h0_eq_h3_rollback_verified",
            "r52c_exposure_step_4domain_requantization_and_shutter_angle_constant_table_immunity_verified",
        ),
        run_specs=(
            ("r52a_lock_op_parts_mydial_big6_schinese", 1),
            ("r52b_audio_out_timing_vs_audio_signals_guard", 1),
            ("r52c_exposure_step_vs_shutter_angle_h0_h3", 1),
        ),
    ),
)

ROUND28_TO_52_PNG_RECEIPTS: Dict[int, Tuple[str, str]] = {
    **ROUND28_TO_50_PNG_RECEIPTS,
    51: (
        "reports/2026-11-15-round51-realhw-framing-usbpower-lun-antiflicker-qemu/assets/r51a-framing-crop-hdmi-big6-schinese-alpha.png",
        "reports/2026-11-15-round51-realhw-framing-usbpower-lun-antiflicker-qemu/assets/r51a-framing-crop-hdmi-big6-schinese-composited.png",
    ),
    52: (
        "reports/2026-11-15-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu/assets/r52a-lock-op-parts-mydial-big6-schinese-alpha.png",
        "reports/2026-11-15-round52-realhw-lock-op-parts-audio-timing-exp-step-qemu/assets/r52a-lock-op-parts-mydial-big6-schinese-composited.png",
    ),
}

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_VM_STAGE_KEY_RE = re.compile(r"^stage(\d+)_")
_ROUND_DIR_RE = re.compile(r"-round(\d+)-")
_NEGATIVE_AUDIT_BOOL_KEYS: frozenset[str] = frozenset(
    {
        "fx3_has_var_shutter",
        "fx3_has_builtin_evf",
        "overall_ready_for_hardware_attach",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "isp_write_authorized",
    }
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealHwMilestone264FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 Wave 39–41 gates (G97..G102) + persistent-write lock
    p1_display_quality_bt_rmt_kwargs: Optional[Mapping[str, Any]] = None
    p1_mymenu_camset_kwargs: Optional[Mapping[str, Any]] = None
    p1_diff_set_still_mv_kwargs: Optional[Mapping[str, Any]] = None
    p1_custom_key_remain_shoot_kwargs: Optional[Mapping[str, Any]] = None
    p1_auto_slow_shutter_breathing_kwargs: Optional[Mapping[str, Any]] = None
    p1_hdmi_reccontrol_4chaudio_kwargs: Optional[Mapping[str, Any]] = None
    p1_request_persistent_writes: bool = False

    # P2 >= 44-pillar recovery master + cnflasha RO + zero-touch redlines
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

    # P4 >= 50 VM HIL stages (Stages 48..50 + forward-compat 51+)
    p4_stage48_lock_op_audio_timing_exp_step_faults: int = 0
    p4_stage49_display_quality_bt_rmt_mymenu_faults: int = 0
    p4_stage50_diff_set_custom_key_remain_shoot_faults: int = 0
    p4_physical_device_writes_override: int = 0
    p4_raw_firmware_bytes_leaked_override: int = 0

    # P5 Sextuple bench readiness preflights (Ph186 + Ph204 + Ph216 + Ph227 + Ph248 + Ph261)
    p5_inject_p186_h0_h3_drift: bool = False
    p5_inject_p204_h0_h3_drift: bool = False
    p5_inject_p216_h0_h3_drift: bool = False
    p5_inject_p227_h0_h3_drift: bool = False
    p5_inject_p248_h0_h3_drift: bool = False
    p5_inject_p261_diffset_customkey_vault_fault: bool = False
    p5_inject_p261_autoslow_hdmi_rec_ctrl_fault: bool = False
    p5_inject_p261_apsc_4k_or_bodydata_flash_fault: bool = False
    p5_inject_p261_end_uart_or_copyright_pii_fault: bool = False
    p5_inject_p261_h0_h3_drift: bool = False
    p5_inject_p261_usb_packets_override: int = 0
    p5_inject_p261_end_uart_bytes_override: int = 0

    # P6 Rounds 28..52+ live QEMU kernel rehearsal & < 50 KiB (51,200 B) PNG receipts
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

    # Optional upstream Milestone 254 fault injection pass-through
    m254_faults: Optional[RealHwMilestone254FaultInjection] = None


@dataclass(frozen=True)
class Milestone264PillarResult:
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
class RealHwMilestone264MasterGateReport:
    schema: str
    schema_version: str
    phase_version: str
    verification_mode: str
    all_pillars_milestone_ready: bool
    status: str
    o_rdonly_enforced: bool
    cnflasha_userspace_write_blocked: bool
    agent_auto_flash_blocked: bool
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
    pillars: Tuple[Milestone264PillarResult, ...]
    gate102_total_gates: int
    gate102_offline_verified: int
    gate102_simulated_verified: int
    gate102_all_verified: bool
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
    milestone264_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class RealHwMilestone264VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone264_sha256: str
    observed_milestone264_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_milestone264_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `RealHwMilestone264MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone264_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 5.0s per mode)
# ---------------------------------------------------------------------------

_102GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_display_quality_bt_rmt_kwargs", "display_quality_bt_rmt_kwargs"),
    ("p1_mymenu_camset_kwargs", "mymenu_camset_kwargs"),
    ("p1_diff_set_still_mv_kwargs", "diff_set_still_mv_kwargs"),
    ("p1_custom_key_remain_shoot_kwargs", "custom_key_remain_shoot_kwargs"),
    ("p1_auto_slow_shutter_breathing_kwargs", "auto_slow_shutter_breathing_kwargs"),
    ("p1_hdmi_reccontrol_4chaudio_kwargs", "hdmi_reccontrol_4chaudio_kwargs"),
)


def _effective_m254_faults(
    faults: RealHwMilestone264FaultInjection,
) -> RealHwMilestone254FaultInjection:
    base = faults.m254_faults or RealHwMilestone254FaultInjection()
    need_186 = faults.p5_inject_p186_h0_h3_drift and not base.p5_inject_p186_h0_h3_drift
    need_204 = faults.p5_inject_p204_h0_h3_drift and not base.p5_inject_p204_h0_h3_drift
    need_216 = faults.p5_inject_p216_h0_h3_drift and not base.p5_inject_p216_h0_h3_drift
    need_227 = faults.p5_inject_p227_h0_h3_drift and not base.p5_inject_p227_h0_h3_drift
    need_248 = faults.p5_inject_p248_h0_h3_drift and not base.p5_inject_p248_h0_h3_drift
    need_p3 = (
        faults.p3_filesettings_tcregen_reclamp_guard_fault
        and not base.p3_filesettings_tcregen_reclamp_guard_fault
    )
    if need_186 or need_204 or need_216 or need_227 or need_248 or need_p3:
        d = asdict(base)
        d["m233_faults"] = base.m233_faults
        if need_186:
            d["p5_inject_p186_h0_h3_drift"] = True
        if need_204:
            d["p5_inject_p204_h0_h3_drift"] = True
        if need_216:
            d["p5_inject_p216_h0_h3_drift"] = True
        if need_227:
            d["p5_inject_p227_h0_h3_drift"] = True
        if need_248:
            d["p5_inject_p248_h0_h3_drift"] = True
        if need_p3:
            d["p3_filesettings_tcregen_reclamp_guard_fault"] = True
        return RealHwMilestone254FaultInjection(**d)
    return base


def _fault_to_102gate_worker_dict(faults: RealHwMilestone264FaultInjection) -> Dict[str, Any]:
    m254_f = _effective_m254_faults(faults)
    m233_f = _effective_m233_faults(m254_f)
    m221_f = _effective_m221_faults(m233_f)
    m209_f = _effective_m209_faults(m221_f)
    m193_f = _effective_m193_faults(m209_f)
    out: Dict[str, Any] = {
        "p1_request_persistent_writes": bool(
            faults.p1_request_persistent_writes
            or m254_f.p1_request_persistent_writes
            or m233_f.p1_request_persistent_writes
            or m221_f.p1_request_persistent_writes
            or m209_f.p1_request_persistent_writes
            or m193_f.p1_request_persistent_writes
        ),
    }
    for src_attr, _ in _66GATE_FAULT_FIELDS:
        val = getattr(m193_f, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    for src_attr, _ in _72GATE_EXTRA_FAULT_FIELDS:
        val = getattr(m209_f, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    for src_attr, _ in _78GATE_EXTRA_FAULT_FIELDS:
        val = getattr(m221_f, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    for src_attr, _ in _90GATE_EXTRA_FAULT_FIELDS:
        val = getattr(m233_f, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    for src_attr, _ in _96GATE_EXTRA_FAULT_FIELDS:
        val = getattr(m254_f, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    for src_attr, _ in _102GATE_EXTRA_FAULT_FIELDS:
        val = getattr(faults, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    return out


def _worker_102gate_single(args: Tuple[str, bool, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, dry_run_sim, fault_dict = args
    repo_root = Path(repo_root_str)
    kwargs: Dict[str, Any] = {
        "request_persistent_emmc_writes": bool(
            fault_dict.get("p1_request_persistent_writes", False)
        )
    }
    for src_attr, dst_kw in (
        *_66GATE_FAULT_FIELDS,
        *_72GATE_EXTRA_FAULT_FIELDS,
        *_78GATE_EXTRA_FAULT_FIELDS,
        *_90GATE_EXTRA_FAULT_FIELDS,
        *_96GATE_EXTRA_FAULT_FIELDS,
        *_102GATE_EXTRA_FAULT_FIELDS,
    ):
        if fault_dict.get(src_attr) is not None:
            kwargs[dst_kw] = fault_dict[src_attr]

    rep = evaluate_102gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        **kwargs,
    )
    m100 = rep.master_100_report
    m98 = m100.get("master_98_report", {}) if isinstance(m100, Mapping) else {}
    m96 = m98.get("master_96_report", {}) if isinstance(m98, Mapping) else {}
    m94 = m96.get("master_94_report", {}) if isinstance(m96, Mapping) else {}
    m92 = m94.get("master_92_report", {}) if isinstance(m94, Mapping) else {}
    m90 = m92.get("master_90_report", {}) if isinstance(m92, Mapping) else {}
    m88 = m90.get("master_88_report", {}) if isinstance(m90, Mapping) else {}
    m86 = m88.get("master_86_report", {}) if isinstance(m88, Mapping) else {}
    m84 = m86.get("master_84_report", {}) if isinstance(m86, Mapping) else {}
    m82 = m84.get("master_82_report", {}) if isinstance(m84, Mapping) else {}
    m80 = m82.get("master_80_report", {}) if isinstance(m82, Mapping) else {}
    m78 = m80.get("master_78_report", {}) if isinstance(m80, Mapping) else {}
    m76 = m78.get("master_76_report", {}) if isinstance(m78, Mapping) else {}
    m74 = m76.get("master_74_report", {}) if isinstance(m76, Mapping) else {}
    m72 = m74.get("master_72_report", {}) if isinstance(m74, Mapping) else {}
    m70 = m72.get("master_70_report", {}) if isinstance(m72, Mapping) else {}
    m68 = m70.get("master_68_report", {}) if isinstance(m70, Mapping) else {}
    m66 = m68.get("master_66_report", {}) if isinstance(m68, Mapping) else {}
    m64 = m66.get("master_64_report", {}) if isinstance(m66, Mapping) else {}

    nested_g_valid: Dict[str, bool] = {}
    for tag, src in (
        ("g63", m64.get("g63_result", {})),
        ("g64", m64.get("g64_result", {})),
        ("g65", m66.get("g65_result", {})),
        ("g66", m66.get("g66_result", {})),
        ("g67", m68.get("g67_result", {})),
        ("g68", m68.get("g68_result", {})),
        ("g69", m70.get("g69_result", {})),
        ("g70", m70.get("g70_result", {})),
        ("g71", m72.get("g71_result", {})),
        ("g72", m72.get("g72_result", {})),
        ("g73", m74.get("g73_result", {})),
        ("g74", m74.get("g74_result", {})),
        ("g75", m76.get("g75_result", {})),
        ("g76", m76.get("g76_result", {})),
        ("g77", m78.get("g77_result", {})),
        ("g78", m78.get("g78_result", {})),
        ("g79", m80.get("g79_result", {})),
        ("g80", m80.get("g80_result", {})),
        ("g81", m82.get("g81_result", {})),
        ("g82", m82.get("g82_result", {})),
        ("g83", m84.get("g83_result", {})),
        ("g84", m84.get("g84_result", {})),
        ("g85", m86.get("g85_result", {})),
        ("g86", m86.get("g86_result", {})),
        ("g87", m88.get("g87_result", {})),
        ("g88", m88.get("g88_result", {})),
        ("g89", m90.get("g89_result", {})),
        ("g90", m90.get("g90_result", {})),
        ("g91", m92.get("g91_result", {})),
        ("g92", m92.get("g92_result", {})),
        ("g93", m94.get("g93_result", {})),
        ("g94", m94.get("g94_result", {})),
        ("g95", m96.get("g95_result", {})),
        ("g96", m96.get("g96_result", {})),
        ("g97", m98.get("g97_result", {})),
        ("g98", m98.get("g98_result", {})),
        ("g99", m100.get("g99_result", {})),
        ("g100", m100.get("g100_result", {})),
        ("g101", rep.g101_result),
        ("g102", rep.g102_result),
    ):
        nested_g_valid[tag] = bool(isinstance(src, Mapping) and src.get("valid") is True)

    g71_guard = m72.get("g71_result", {}).get("big6_noend_camset_slot1_guard", {})
    g71_end_tx = (
        int(g71_guard.get("e_nd_actuator_tx_count", 0)) if isinstance(g71_guard, Mapping) else -1
    )
    s = rep.summary
    return {
        "schema": rep.schema,
        "total_gates": int(s["total_gates"]),
        "verified_gates": int(s["verified_gates"]),
        "blocked_or_pending_gates": int(s["blocked_or_pending_gates"]),
        "offline_99_gates_verified": bool(s.get("offline_99_gates_verified", False)),
        "all_102_gates_verified": bool(s.get("all_102_gates_verified", False)),
        "g13_to_g102_all_passed": bool(s.get("g13_to_g102_all_passed", False)),
        "g101_to_g102_all_passed": bool(s.get("g101_to_g102_all_passed", False)),
        "overall_ready_for_hardware_attach": bool(s["overall_ready_for_hardware_attach"]),
        "hardware_live_attachment_authorized": bool(
            s.get("hardware_live_attachment_authorized", False)
        ),
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


def _normalize_44pillar_fault_id(fault_id: Optional[str]) -> Optional[str]:
    if not fault_id:
        return None
    if fault_id in MASTER_44_PILLAR_IDS:
        return fault_id
    m = re.match(r"^pillar_(\d+)$", fault_id.strip().lower())
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(MASTER_44_PILLAR_IDS):
            return MASTER_44_PILLAR_IDS[idx]
    return fault_id


def _worker_recovery_44pillar(args: Tuple[bool, Optional[str]]) -> Dict[str, Any]:
    use_clean_room, fault_pillar = args
    rep = evaluate_realhw_44pillar_recovery_master(
        force_clean_room=use_clean_room,
        fault_inject_pillar=_normalize_44pillar_fault_id(fault_pillar),
    )
    return rep.to_dict()


def _worker_pillar_4_264(use_clean_room: bool) -> Dict[str, Any]:
    return run_fx3_vm_coemulation_suite(CoEmulationConfig(force_clean_room=use_clean_room))


def _worker_phase261(
    args: Tuple[str, str, bool, Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    fx6_str, fx3_str, use_clean_room, p261_faults = args
    fx6_dir = Path(fx6_str)
    fx3_dir = Path(fx3_str)
    rep_off = evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
    )
    sim_kwargs: Dict[str, Any] = {}
    if p261_faults.get("diffset_customkey_vault"):
        sim_kwargs["slot1_camset_custom_key_access_mode"] = "O_RDWR"
        sim_kwargs["expect_builtin_evf_or_finder_monitor_switch"] = True
    if p261_faults.get("autoslow_hdmi_rec_ctrl"):
        sim_kwargs["hdmi_time_code_output"] = "OFF"
        sim_kwargs["hdmi_rec_control"] = "ON"
        sim_kwargs["expect_auto_slow_shutter_with_shutter_angle"] = True
    if p261_faults.get("apsc_4k_or_bodydata_flash"):
        sim_kwargs["expect_apsc_s35_active_in_4k_or_raw"] = True
        sim_kwargs["slot1_bodydata_flash_requested"] = True
    if p261_faults.get("end_uart_or_copyright_pii"):
        sim_kwargs["simulated_e_nd_uart_bytes"] = 4
        sim_kwargs["write_copyright_info"] = "ON"
        sim_kwargs["photographer_text"] = "PII_LEAK_TEST"
    if p261_faults.get("h0_h3_drift"):
        sim_kwargs["simulated_h0_h3_drifted_surfaces"] = 1

    rep_sim = evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **sim_kwargs,
    )
    return rep_off.to_dict(), rep_sim.to_dict()


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1..P5)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
) -> Milestone264PillarResult:
    errors: List[str] = []
    off_total = int(raw_off["total_gates"])
    off_ver = int(raw_off["verified_gates"])
    sim_total = int(raw_sim["total_gates"])
    sim_ver = int(raw_sim["verified_gates"])

    if (
        off_total < 102
        or off_ver < 99
        or off_ver != off_total - 3
        or int(raw_off["blocked_or_pending_gates"]) != 3
        or raw_off["overall_ready_for_hardware_attach"] is not False
        or raw_off["hardware_live_attachment_authorized"] is not False
        or not bool(raw_off["offline_99_gates_verified"])
    ):
        errors.append(
            f"p1_offline: expected {off_total - 3}/{off_total} (>=99/102, 3 Tier-0 gates fail-closed) "
            f"and hardware_attach=False, got {off_ver}/{off_total}"
        )

    if (
        sim_total < 102
        or sim_ver != sim_total
        or not bool(raw_sim["all_102_gates_verified"])
        or not bool(raw_sim["g13_to_g102_all_passed"])
        or not bool(raw_sim["g101_to_g102_all_passed"])
        or raw_sim["overall_ready_for_hardware_attach"] is not False
        or raw_sim["hardware_live_attachment_authorized"] is not False
        or raw_sim["agent_auto_flash_blocked"] is not True
    ):
        errors.append(
            f"p1_simulated: expected {sim_total}/{sim_total} (>=102/102) with all_102_gates_verified=True "
            f"and hardware_attach=False, got {sim_ver}/{sim_total}"
        )

    for mode_tag, rmap in (("offline", raw_off), ("simulated", raw_sim)):
        if (
            rmap["persistent_emmc_writes_authorized"] is not False
            or rmap["persistent_write_release"] is not False
            or rmap["spi_nor_write_authorized"] is not False
            or rmap["el3_payload_transmit_authorized"] is not False
            or rmap.get("human_hardware_attach_token", False) is not False
            or rmap.get("physical_flash_auto_exec_authorized", False) is not False
            or int(rmap["usb_packets_transmitted"]) != 0
            or int(rmap["physical_usb_packets_emitted"]) != 0
            or int(rmap["raw_firmware_bytes_leaked"]) != 0
            or int(rmap["g71_e_nd_actuator_tx_count"]) != 0
        ):
            errors.append(
                f"p1_{mode_tag}: hard-locked zero-write / zero-USB-TX / zero-leak / zero-e-ND redline breached"
            )

    nested_sim: Mapping[str, bool] = raw_sim["nested_g_valid"]
    failed_gates = [g.upper() for g in sorted(nested_sim) if not nested_sim[g]]
    if failed_gates:
        errors.append(f"p1: real-hardware gates failed: {', '.join(failed_gates)}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_sim["schema"],
        "offline_total_gates": off_total,
        "offline_verified_gates": off_ver,
        "simulated_total_gates": sim_total,
        "simulated_verified_gates": sim_ver,
        "all_102_gates_verified": bool(raw_sim["all_102_gates_verified"]),
        "offline_ready_for_hardware_attach": raw_off["overall_ready_for_hardware_attach"],
        "simulated_ready_for_hardware_attach": raw_sim["overall_ready_for_hardware_attach"],
        "hardware_live_attachment_authorized": raw_sim["hardware_live_attachment_authorized"],
        "agent_auto_flash_blocked": raw_sim["agent_auto_flash_blocked"],
        "persistent_emmc_writes_authorized": raw_sim["persistent_emmc_writes_authorized"],
        "spi_nor_write_authorized": raw_sim["spi_nor_write_authorized"],
        "el3_payload_transmit_authorized": raw_sim["el3_payload_transmit_authorized"],
        "usb_packets_transmitted": int(raw_sim["usb_packets_transmitted"]),
        "raw_firmware_bytes_leaked": int(raw_sim["raw_firmware_bytes_leaked"]),
        "g71_e_nd_actuator_tx_count": raw_sim["g71_e_nd_actuator_tx_count"],
        "g63_to_g102_valid": dict(nested_sim),
    }
    return Milestone264PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_102GATE_REALHW_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"102-Gate Safety: offline={off_ver}/{off_total} (3 Tier-0 gates fail-closed), "
            f"simulated={sim_ver}/{sim_total} (G97..G102 DisplayQual-BTRmt/MyMenu-CAMSET/"
            f"DiffSet-ShutterAngle/CustomKey-RemainShoot/AutoSlow-Breathing/HDMIRecCtrl-4chAudio) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    rec_44: Mapping[str, Any],
    faults: RealHwMilestone264FaultInjection,
) -> Tuple[Milestone264PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    p_count = int(rec_44.get("pillar_count", 0))
    p_passed = int(rec_44.get("pillars_passed", 0))
    rec_status = str(rec_44.get("status", ""))

    cnflasha_blocked = bool(rec_44.get("cnflasha_userspace_write_blocked", False)) and not bool(
        faults.p2_cnflasha_write_unblocked_fault
    )
    otp = (
        max(int(rec_44.get("otp_fuse_writes", 0) or 0), int(rec_44.get("otp_fuse_touches", -1)))
        + int(faults.p2_otp_fuse_touches_override)
    )
    rpmb = int(rec_44.get("rpmb_counter_increments", -1)) + int(
        faults.p2_rpmb_counter_increments_override
    )
    ptx = int(rec_44.get("passive_tx_bytes_emitted", -1)) + int(faults.p2_passive_tx_bytes_override)
    usb_pkts = int(rec_44.get("physical_usb_packets_emitted", -1)) + int(
        faults.p2_physical_usb_packets_override
    )
    dev_writes = int(rec_44.get("physical_device_writes", -1)) + int(
        faults.p2_physical_device_writes_override
    )
    leaked = int(rec_44.get("raw_firmware_bytes_leaked", -1)) + int(
        faults.p2_raw_firmware_bytes_leaked_override
    )

    p44a = rec_44.get("pillar44_a_apsc_s35_face_eye_af_vault", {})
    p44b = rec_44.get("pillar44_b_version_readonly_bodydata_vault", {})
    p44a_ok = isinstance(p44a, Mapping) and bool(p44a.get("passed"))
    p44b_ok = isinstance(p44b, Mapping) and bool(p44b.get("passed"))

    status_ok = rec_status == "VERIFIED_44OF44_PILLAR_RECOVERY_MASTER" or (
        p_count > 44 and p_passed == p_count and bool(rec_44.get("all_passed"))
    )
    if (
        not bool(rec_44.get("all_passed"))
        or not status_ok
        or p_count < 44
        or p_passed < 44
        or p_passed != p_count
        or not p44a_ok
        or not p44b_ok
    ):
        errors.append(
            f"p2_44pillar: expected >=44/44 VERIFIED_44OF44_PILLAR_RECOVERY_MASTER, "
            f"got {p_passed}/{p_count} (status={rec_status!r}, 44A={p44a_ok}, 44B={p44b_ok})"
        )

    zero_violation_keys = (
        "apsc_s35_4k_or_raw_bypass_events",
        "ai_unit_subject_recog_spoof_events",
        "hdmi_clean_feed_eye_frame_baked_pixels",
        "version_dialog_flash_writes",
        "bodydata_flash_from_version_dialog_attempts",
        "slot1_bodydata_vault_mutation_bytes",
        "auto_slow_shutter_lockout_bypass_events",
        "auto_slow_shutter_angle_overlap_events",
        "breathing_comp_raw_or_240p_bypass_events",
        "hdmi_rec_ctrl_without_tc_violations",
        "slot1_hdmi_rec_vault_mutation_bytes",
        "diff_set_transition_corruption_events",
        "shutter_angle_common_bleed_events",
        "slot1_custom_key_vault_mutation_bytes",
        "evf_finder_monitor_spoof_events",
        "tier0_battery_high_display_violations",
        "bt_rmt_ir_lockout_violations",
        "slot1_mymenu_vault_mutation_bytes",
        "unbuffered_battery_pull_events",
        "destructive_menu_delete_confusions",
        "shutter_angle_exposure_step_drift_events",
    )
    violations_nonzero = any(int(rec_44.get(vk, 0)) != 0 for vk in zero_violation_keys)

    if (
        cnflasha_blocked is not True
        or otp != 0
        or rpmb != 0
        or ptx != 0
        or usb_pkts != 0
        or dev_writes != 0
        or leaked != 0
        or violations_nonzero
        or rec_44.get("fx3_has_var_shutter", False) is not False
        or rec_44.get("fx3_has_builtin_evf", False) is not False
        or rec_44.get("hardware_live_attachment_authorized", False) is not False
        or rec_44.get("el3_payload_transmit_authorized") is not False
        or rec_44.get("isp_write_authorized") is not False
        or rec_44.get("spi_nor_write_authorized") is not False
        or rec_44.get("persistent_emmc_writes_authorized") is not False
        or rec_44.get("persistent_write_release") is not False
    ):
        errors.append(
            f"p2_redlines: zero-touch / cnflasha RO invariant violated "
            f"(cnflasha_blocked={cnflasha_blocked}, otp={otp}, rpmb={rpmb}, ptx={ptx}, "
            f"usb_pkts={usb_pkts}, dev_writes={dev_writes}, leaked={leaked})"
        )

    passed = len(errors) == 0
    evidence = {
        "status": rec_status,
        "pillar_count": p_count,
        "pillars_passed": p_passed,
        "cnflasha_userspace_write_blocked": cnflasha_blocked,
        "fx3_has_builtin_evf": bool(rec_44.get("fx3_has_builtin_evf", False)),
        "fx3_has_var_shutter": bool(rec_44.get("fx3_has_var_shutter", False)),
        "pillar44_a_apsc_s35_face_eye_af_passed": p44a_ok,
        "pillar44_b_version_readonly_bodydata_passed": p44b_ok,
        "otp_fuse_touches": otp,
        "rpmb_counter_increments": rpmb,
        "passive_tx_bytes_emitted": ptx,
        "physical_usb_packets_emitted": usb_pkts,
        "physical_device_writes": dev_writes,
        "raw_firmware_bytes_leaked": leaked,
        "master_44pillar_sha256": str(rec_44.get("master_44pillar_sha256", "")),
    }
    pillar = Milestone264PillarResult(
        pillar_id="P2",
        pillar_name="FORTY_FOUR_PILLAR_RECOVERY_MASTER_VAULT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"44-Pillar Recovery ({rec_status}): {p_passed}/{p_count} (>=44 required; "
            f"Pillars 42..44 DiffSet-CustomKey/AutoSlow-HDMIRecCtrl/APSC-FaceEyeAF-VersionRO), "
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
    faults: RealHwMilestone264FaultInjection,
) -> Tuple[Milestone264PillarResult, Dict[str, Any]]:
    m254_p3, meta_45 = _eval_m254_p3(auditors, _effective_m254_faults(faults))
    errors: List[str] = list(m254_p3.errors)
    auditor_statuses: Dict[str, bool] = dict(m254_p3.evidence["auditor_statuses"])
    auditor_sha256s: Dict[str, Optional[str]] = dict(m254_p3.evidence["auditor_sha256s"])

    for key, obj in sorted(auditors.items()):
        if key not in auditor_statuses and key.endswith("_audit") and isinstance(obj, Mapping):
            ok = bool(obj.get("all_checks_passed"))
            auditor_statuses[key] = ok
            if not ok:
                errors.append(f"p3: forward-compat auditor {key} failed")

    auditors_total = len(auditor_statuses)
    auditors_passed = sum(1 for v in auditor_statuses.values() if v)
    total_leaked = int(meta_45["raw_firmware_bytes_leaked"]) + int(
        faults.p3_raw_firmware_bytes_leaked_override
    )
    end_tx = int(meta_45["e_nd_actuator_tx_count"])
    cal_mut = int(meta_45["calibration_mutation_bytes"])

    if not (auditors_passed >= 45 and auditors_passed == auditors_total):
        msg = f"p3: expected >= 45 auditors and all passing, got {auditors_passed}/{auditors_total}"
        if msg not in errors:
            errors.append(msg)
    if total_leaked != 0:
        msg = f"p3: raw_firmware_bytes_leaked={total_leaked} != 0"
        if msg not in errors:
            errors.append(msg)

    passed = len(errors) == 0 and cal_mut == 0 and total_leaked == 0 and end_tx == 0
    evidence = dict(m254_p3.evidence)
    evidence.update(
        {
            "auditors_total": auditors_total,
            "auditors_passed": auditors_passed,
            "auditor_count": auditors_total,
            "passed_auditor_count": auditors_passed,
            "auditor_statuses": auditor_statuses,
            "auditor_sha256s": auditor_sha256s,
            "raw_firmware_bytes_leaked": total_leaked,
        }
    )
    pillar = Milestone264PillarResult(
        pillar_id="P3",
        pillar_name="FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {auditors_passed}/{auditors_total} auditors (>=45 required; "
            f"forward-compat 46+ dynamic discovery), e_nd_tx={end_tx}, leaked={total_leaked}B "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_45)
    meta.update(
        {
            "auditor_count": auditors_total,
            "passed_count": auditors_passed,
            "raw_firmware_bytes_leaked": total_leaked,
        }
    )
    return pillar, meta


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: RealHwMilestone264FaultInjection,
) -> Tuple[Milestone264PillarResult, Dict[str, Any]]:
    m254_f = _effective_m254_faults(faults)
    m254_p4, meta_47 = _eval_m254_p4(vm_rep, m254_f)
    errors: List[str] = [
        e for e in m254_p4.errors if not e.startswith("p4: expected >= 47 VM stages")
    ]
    stage_statuses: Dict[str, bool] = dict(m254_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_50_STAGE_KEYS[47:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if (
            not ok
            and f"p4: forward-compat VM stage {skey} failed" not in errors
            and f"p4: VM co-emulation {skey} failed" not in errors
        ):
            errors.append(f"p4: VM co-emulation {skey} failed")

    # Forward-compatible discovery of Stage 51+ keys
    for skey, sobj in sorted(vm_rep.items()):
        m = _VM_STAGE_KEY_RE.match(str(skey))
        if m and int(m.group(1)) >= 51 and skey not in stage_statuses and isinstance(sobj, Mapping):
            ok = bool(sobj.get("all_checks_passed"))
            stage_statuses[skey] = ok
            if not ok:
                errors.append(f"p4: forward-compat VM stage {skey} failed")

    stage48_to_50_specs: Tuple[Tuple[str, Tuple[str, ...], int], ...] = (
        (
            "stage48_realhw_lock_op_parts_audio_timing_exp_step_hil",
            (
                "destructive_menu_delete_confusions",
                "slot1_vault_format_events",
                "silent_mode_audio_signal_leak_events",
                "shutter_angle_exposure_step_drift_events",
            ),
            int(faults.p4_stage48_lock_op_audio_timing_exp_step_faults),
        ),
        (
            "stage49_realhw_display_quality_bt_rmt_mymenu_hil",
            (
                "tier0_battery_high_display_violations",
                "passive_tx_bytes_emitted",
                "bt_rmt_ir_lockout_violations",
                "slot1_mymenu_vault_mutation_bytes",
            ),
            int(faults.p4_stage49_display_quality_bt_rmt_mymenu_faults),
        ),
        (
            "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil",
            (
                "diff_set_transition_corruption_events",
                "shutter_angle_common_bleed_events",
                "slot1_custom_key_vault_mutation_bytes",
                "evf_finder_monitor_spoof_events",
            ),
            int(faults.p4_stage50_diff_set_custom_key_remain_shoot_faults),
        ),
    )

    extra_emmc = 0
    extra_wf12 = 0
    for skey, fault_counters, injected in stage48_to_50_specs:
        sobj = vm_rep.get(skey, {})
        if isinstance(sobj, Mapping):
            extra_emmc += max(0, int(sobj.get("emmc_mutation_bytes", 0)))
            extra_wf12 += max(0, int(sobj.get("wf12_00342260_hits", 0)))
        counter_sum = injected + sum(
            int(sobj.get(ck, -1)) if isinstance(sobj, Mapping) else -1 for ck in fault_counters
        )
        s50_extra_ok = True
        if skey == "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil":
            s50_extra_ok = bool(
                isinstance(sobj, Mapping)
                and sobj.get("fx3_has_builtin_evf") is False
                and sobj.get("milestone") == "50/50"
            )
        if not _check_vm_stage45_to_47_redlines(sobj) or counter_sum != 0 or not s50_extra_ok:
            errors.append(f"p4: {skey} redlines violated (fault_sum={counter_sum})")
            stage_statuses[skey] = False

    vm_raw_leaked = int(meta_47.get("raw_firmware_bytes_leaked", 0)) + int(
        faults.p4_raw_firmware_bytes_leaked_override
    )
    vm_phys_writes = int(meta_47.get("physical_device_writes", 0)) + int(
        faults.p4_physical_device_writes_override
    )
    vm_stages_total = len(stage_statuses)
    vm_stages_passed = sum(1 for v in stage_statuses.values() if v)
    emmc_corruptions = int(meta_47.get("emmc_corruptions", 0)) + extra_emmc
    total_wf12_hits = int(meta_47.get("wf12_00342260_hits", 0)) + extra_wf12

    if not (vm_stages_passed >= 50 and vm_stages_passed == vm_stages_total):
        errors.append(
            f"p4: expected >= 50 VM stages and all passing, got {vm_stages_passed}/{vm_stages_total}"
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
    evidence = dict(m254_p4.evidence)
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
            "stage48_digest_sha256": vm_rep.get(
                "stage48_realhw_lock_op_parts_audio_timing_exp_step_hil", {}
            ).get("phase253_audit_digest_sha256"),
            "stage49_digest_sha256": vm_rep.get(
                "stage49_realhw_display_quality_bt_rmt_mymenu_hil", {}
            ).get("phase257_audit_digest_sha256"),
            "stage50_digest_sha256": vm_rep.get(
                "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil", {}
            ).get("phase258_audit_digest_sha256"),
            "stage50_milestone": vm_rep.get(
                "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil", {}
            ).get("milestone"),
            "stage50_fx3_has_builtin_evf": vm_rep.get(
                "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil", {}
            ).get("fx3_has_builtin_evf"),
        }
    )
    pillar = Milestone264PillarResult(
        pillar_id="P4",
        pillar_name="FIFTY_PLUS_STAGE_VM_HIL_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {vm_stages_passed}/{vm_stages_total} stages (>=50 required; Stages 48..50 "
            f"LockOp-AudioTiming-ExpStep/DisplayQual-BTRmt-MyMenu/DiffSet-CustomKey-RemainShoot), "
            f"phys_writes={vm_phys_writes}, leaked={vm_raw_leaked}B, emmc_corruptions={emmc_corruptions} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_47)
    meta.update(
        {
            "stage_count": vm_stages_total,
            "passed_count": vm_stages_passed,
            "raw_firmware_bytes_leaked": vm_raw_leaked,
            "physical_device_writes": vm_phys_writes,
            "emmc_corruptions": emmc_corruptions,
            "wf12_00342260_hits": total_wf12_hits,
        }
    )
    return pillar, meta


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
    faults: RealHwMilestone264FaultInjection,
) -> Tuple[Milestone264PillarResult, Dict[str, Any]]:
    m254_p5, meta_p5_254 = _eval_m254_p5(
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
        _effective_m254_faults(faults),
    )
    errors: List[str] = [
        e
        for e in m254_p5.errors
        if e != "p5: overall_ready_for_hardware_attach must remain False across all 5 verifiers"
    ]

    # Phase 261 offline physical-Tier0-receipt block mode
    p261_off_dict = copy.deepcopy(dict(raw_p261_off))
    v261_off = verify_phase261_report(p261_off_dict)
    p261_off_ready = bool(p261_off_dict.get("overall_ready_for_hardware_attach", False))
    if (
        not v261_off.valid
        or p261_off_dict.get("go_no_go") != GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        or p261_off_dict.get("hardware_live_attachment_authorized") is not False
        or p261_off_ready is not False
        or p261_off_dict.get("tier0_receipt_verified") is not False
        or not bool(p261_off_dict.get("all_4_check_groups_passed"))
        or p261_off_dict.get("sd_physical_media_written") is not False
        or int(p261_off_dict.get("usb_packets_transmitted", -1)) != 0
        or int(p261_off_dict.get("physical_usb_packets_emitted", -1)) != 0
        or int(p261_off_dict.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(p261_off_dict.get("e_nd_uart_bytes_transmitted", -1)) != 0
    ):
        errors.append(
            f"p5_p261_off: expected {GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT} "
            f"(got {p261_off_dict.get('go_no_go')}, valid={v261_off.valid}, errs={v261_off.errors})"
        )

    # Phase 261 simulated dry-run GA/GB/GC/GD preflight mode
    p261_sim_dict = copy.deepcopy(dict(raw_p261_sim))
    if faults.p5_inject_p261_usb_packets_override:
        p261_sim_dict["usb_packets_transmitted"] = int(
            p261_sim_dict.get("usb_packets_transmitted", 0)
        ) + int(faults.p5_inject_p261_usb_packets_override)
        p261_sim_dict["physical_usb_packets_emitted"] = int(
            p261_sim_dict.get("physical_usb_packets_emitted", 0)
        ) + int(faults.p5_inject_p261_usb_packets_override)
    if faults.p5_inject_p261_end_uart_bytes_override:
        p261_sim_dict["e_nd_uart_bytes_transmitted"] = int(
            p261_sim_dict.get("e_nd_uart_bytes_transmitted", 0)
        ) + int(faults.p5_inject_p261_end_uart_bytes_override)

    v261_sim = verify_phase261_report(p261_sim_dict)
    p261_sim_passed = int(p261_sim_dict.get("check_groups_passed", -1))
    p261_sim_pkts = max(
        int(p261_sim_dict.get("usb_packets_transmitted", -1)),
        int(p261_sim_dict.get("physical_usb_packets_emitted", -1)),
    )
    p261_sim_leaked = int(p261_sim_dict.get("raw_firmware_bytes_leaked", -1))
    p261_end_uart = int(p261_sim_dict.get("e_nd_uart_bytes_transmitted", -1))
    p261_slot1_mut = int(p261_sim_dict.get("slot1_custom_key_vault_mutation_bytes", -1))
    p261_pii_leaked = int(p261_sim_dict.get("photographer_copyright_pii_leaked_bytes", -1))
    p261_h0_h3 = int(p261_sim_dict.get("h0_equals_h3_count", -1))
    p261_sim_ready = bool(p261_sim_dict.get("overall_ready_for_hardware_attach", False))

    g261_keys = (
        "check_group_a_diffset_customkey_and_evfless",
        "check_group_b_autoslow_hdmi_rec_ctrl_and_breathing",
        "check_group_c_apsc_s35_face_eye_af_and_version",
        "check_group_d_release_wo_card_audio_copyright_and_tier0",
    )
    all_g261_ok = all(
        isinstance(p261_sim_dict.get(gk), Mapping) and bool(p261_sim_dict[gk].get("passed"))
        for gk in g261_keys
    )

    if (
        not v261_sim.valid
        or p261_sim_dict.get("go_no_go") != GO_NO_GO_DRY_RUN_SIMULATED_READY
        or not bool(p261_sim_dict.get("all_4_check_groups_passed"))
        or p261_sim_passed != 4
        or not all_g261_ok
        or not bool(p261_sim_dict.get("tier0_receipt_verified"))
        or p261_sim_dict.get("hardware_live_attachment_authorized") is not False
        or p261_sim_ready is not False
        or p261_sim_dict.get("sd_physical_media_written") is not False
        or p261_sim_dict.get("fx3_has_builtin_evf") is not False
        or p261_h0_h3 != 16
        or p261_sim_pkts != 0
        or p261_sim_leaked != 0
        or p261_end_uart != 0
        or p261_slot1_mut != 0
        or p261_pii_leaked != 0
        or p261_sim_dict.get("persistent_emmc_writes_authorized") is not False
        or p261_sim_dict.get("spi_nor_write_authorized") is not False
        or p261_sim_dict.get("el3_payload_transmit_authorized") is not False
    ):
        errors.append(
            f"p5_p261_sim: preflight-diffset-customkey-autoslow-and-apsc failed "
            f"(go={p261_sim_dict.get('go_no_go')}, groups={p261_sim_passed}/4, errs={v261_sim.errors})"
        )

    any_attach_ready = bool(
        meta_p5_254["overall_ready_for_hardware_attach"] or p261_off_ready or p261_sim_ready
    )
    if any_attach_ready:
        errors.append("p5: overall_ready_for_hardware_attach must remain False across all 6 verifiers")

    passed = len(errors) == 0
    evidence = dict(m254_p5.evidence)
    evidence.update(
        {
            "overall_ready_for_hardware_attach": any_attach_ready,
            "p261_offline_go_no_go": p261_off_dict.get("go_no_go"),
            "p261_offline_check_groups_passed": p261_off_dict.get("check_groups_passed"),
            "p261_offline_report_verified": bool(v261_off.valid),
            "p261_sim_go_no_go": p261_sim_dict.get("go_no_go"),
            "p261_sim_check_groups_passed": p261_sim_passed,
            "p261_fx3_has_builtin_evf": p261_sim_dict.get("fx3_has_builtin_evf"),
            "p261_hardware_live_attachment_authorized": p261_sim_dict.get(
                "hardware_live_attachment_authorized"
            ),
            "p261_h0_equals_h3_count": p261_h0_h3,
            "p261_e_nd_uart_bytes_transmitted": p261_end_uart,
            "p261_sim_usb_packets_transmitted": p261_sim_pkts,
            "p261_sim_raw_firmware_bytes_leaked": p261_sim_leaked,
            "p261_sim_report_verified": bool(v261_sim.valid),
            "p261_sim_report_sha256": str(p261_sim_dict.get("report_sha256", "")),
        }
    )
    pillar = Milestone264PillarResult(
        pillar_id="P5",
        pillar_name="SEXTUPLE_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216_PH227_PH248_PH261",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Sextuple Bench Preflights: Ph186(sim={meta_p5_254['p186_sim_gates_passed']}/4) + "
            f"Ph204(sim={meta_p5_254['p204_sim_groups_passed']}/3) + "
            f"Ph216(sim={meta_p5_254['p216_sim_checklists_passed']}/5) + "
            f"Ph227(sim={meta_p5_254['p227_sim_check_groups_passed']}/3) + "
            f"Ph248(sim={meta_p5_254['p248_sim_check_groups_passed']}/4) + "
            f"Ph261(diffset-customkey-autoslow-apsc sim={p261_sim_passed}/4 H0==H3={p261_h0_h3}/16) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_p5_254)
    meta.update(
        {
            "overall_ready_for_hardware_attach": any_attach_ready,
            "p261_offline_go_no_go": str(p261_off_dict.get("go_no_go", "")),
            "p261_sim_go_no_go": str(p261_sim_dict.get("go_no_go", "")),
            "p261_sim_check_groups_passed": p261_sim_passed,
            "p261_hardware_live_attachment_authorized": bool(
                p261_sim_dict.get("hardware_live_attachment_authorized", True)
            ),
            "p261_h0_equals_h3_count": p261_h0_h3,
            "p261_e_nd_uart_bytes_transmitted": p261_end_uart,
            "p261_sim_usb_packets_transmitted": p261_sim_pkts,
            "p261_sim_raw_firmware_bytes_leaked": p261_sim_leaked,
        }
    )
    return pillar, meta


def _evaluate_pillar_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: RealHwMilestone264FaultInjection,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
    p5_meta: Mapping[str, Any],
) -> Tuple[Milestone264PillarResult, Dict[str, Any]]:
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

    expected_rounds = len(ROUND28_TO_52_SPECS)
    expected_runs = sum(len(s.run_specs) for s in ROUND28_TO_52_SPECS)
    expected_pngs = sum(len(ROUND28_TO_52_PNG_RECEIPTS[s.round_num]) for s in ROUND28_TO_52_SPECS)

    for spec in ROUND28_TO_52_SPECS:
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

        png_pair = ROUND28_TO_52_PNG_RECEIPTS[spec.round_num]
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

    # Forward-compatible discovery of Round 53+ reports so newly merged QEMU rounds stay green
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
            if rnum >= 53 and (d / "summary.json").is_file():
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
                            is_neg = bk in _NEGATIVE_AUDIT_BOOL_KEYS or (
                                bk.startswith(("fx3_", "fx6_"))
                                and (
                                    bk.endswith(("_present", "_only", "_exposed", "_supported"))
                                    or "_has_" in bk
                                )
                            )
                            if is_neg:
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

    # Cross-pillar hardware-lock, 16/16 H0 == H3, zero eMMC & zero e-ND invariants
    if (
        p1_meta.get("persistent_emmc_writes_authorized") is not False
        or p1_meta.get("spi_nor_write_authorized") is not False
        or p1_meta.get("el3_payload_transmit_authorized") is not False
        or p1_meta.get("simulated_ready_for_hardware_attach") is not False
        or p1_meta.get("hardware_live_attachment_authorized") is not False
        or int(p1_meta.get("g71_e_nd_actuator_tx_count", -1)) != 0
    ):
        errors.append("p6: P1 hardware-lock or zero e-ND invariant breached")
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
    ):
        errors.append(
            "p6: P5 H0==H3 (16/16) or sextuple bench preflight (Ph186/Ph204/Ph216/Ph227/Ph248/Ph261) invariant breached"
        )

    passed = (
        len(errors) == 0
        and rounds_verified >= 25
        and rounds_verified == expected_rounds
        and total_runs_verified >= 75
        and total_runs_verified == expected_runs
        and pngs_verified >= 50
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
        "png_sizes_by_asset": png_sizes_by_asset,
        "png_sources_by_round": png_sources_by_round,
        "h0_equals_h3_count": int(p5_meta.get("p261_h0_equals_h3_count", 0)),
        "emmc_write_count": total_emmc,
        "e_nd_actuator_tx_count": int(p1_meta.get("g71_e_nd_actuator_tx_count", 0))
        + max(0, int(p5_meta.get("p261_e_nd_uart_bytes_transmitted", 0))),
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
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
    }
    pillar = Milestone264PillarResult(
        pillar_id="P6",
        pillar_name="REAL_FX3_702_QEMU_ROUNDS_28_TO_52_PLUS_AND_PNG_RECEIPTS",
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


def _collect_parallel_milestone264_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: RealHwMilestone264FaultInjection,
) -> Tuple[Any, ...]:
    m254_f = _effective_m254_faults(faults)
    m233_f = _effective_m233_faults(m254_f)
    m221_f = _effective_m221_faults(m233_f)
    m209_f = _effective_m209_faults(m221_f)
    m193_f = _effective_m193_faults(m209_f)
    gate_fault_dict = _fault_to_102gate_worker_dict(faults)
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
        "diffset_customkey_vault": bool(faults.p5_inject_p261_diffset_customkey_vault_fault),
        "autoslow_hdmi_rec_ctrl": bool(faults.p5_inject_p261_autoslow_hdmi_rec_ctrl_fault),
        "apsc_4k_or_bodydata_flash": bool(faults.p5_inject_p261_apsc_4k_or_bodydata_flash_fault),
        "end_uart_or_copyright_pii": bool(faults.p5_inject_p261_end_uart_or_copyright_pii_fault),
        "h0_h3_drift": bool(faults.p5_inject_p261_h0_h3_drift),
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

    eff_p2_fault = (
        faults.p2_fault_inject_pillar
        or m254_f.p2_fault_inject_pillar
        or m233_f.p2_fault_inject_pillar
        or m221_f.p2_fault_inject_pillar
        or m209_f.p2_fault_inject_pillar
        or m193_f.p2_fault_inject_pillar
    )

    try:
        # Execute 0.15s-budgeted #41..#45 realhw auditors before fork() COW contention
        auditors: Dict[str, Dict[str, Any]] = dict(
            _worker_pillar_3_batch_233((p3_batches[0], use_clean_room))
        )
        ctx = mp.get_context("fork")
        pool_workers = min(8, max(4, mp.cpu_count() or 8))
        with ProcessPoolExecutor(max_workers=pool_workers, mp_context=ctx) as ex:
            fut_vm = ex.submit(_worker_pillar_4_264, use_clean_room)
            fut_1_off = ex.submit(
                _worker_102gate_single, (str(repo_root), use_clean_room, False, gate_fault_dict)
            )
            fut_1_sim = ex.submit(
                _worker_102gate_single, (str(repo_root), use_clean_room, True, gate_fault_dict)
            )
            fut_44p = ex.submit(_worker_recovery_44pillar, (use_clean_room, eff_p2_fault))
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

            raw_1_off = fut_1_off.result()
            raw_1_sim = fut_1_sim.result()
            raw_44p = fut_44p.result()
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
            return (
                raw_1_off,
                raw_1_sim,
                raw_44p,
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
            )
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1_off = _worker_102gate_single((str(repo_root), use_clean_room, False, gate_fault_dict))
    raw_1_sim = _worker_102gate_single((str(repo_root), use_clean_room, True, gate_fault_dict))
    raw_44p = _worker_recovery_44pillar((use_clean_room, eff_p2_fault))
    auditors = {}
    for batch in p3_batches:
        auditors.update(_worker_pillar_3_batch_233((batch, use_clean_room)))
    raw_vm = _worker_pillar_4_264(use_clean_room)
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
    return (
        raw_1_off,
        raw_1_sim,
        raw_44p,
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
    )


def evaluate_realhw_milestone264_master_gate(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[RealHwMilestone264FaultInjection] = None,
    _raw_bundle_override: Optional[Tuple[Any, ...]] = None,
) -> RealHwMilestone264MasterGateReport:
    """Build & evaluate the Grand Milestone Phase 264 6-Pillar Real-Hardware Master Gate."""
    if force_clean_room is not None:
        use_clean_room = bool(force_clean_room)
    elif synthetic_clean_room is not None:
        use_clean_room = bool(synthetic_clean_room)
    else:
        use_clean_room = _is_forced_clean_room()

    active_faults = faults or RealHwMilestone264FaultInjection()

    bundle = _raw_bundle_override or _collect_parallel_milestone264_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )
    (
        raw_1_off,
        raw_1_sim,
        raw_44p,
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
    ) = bundle

    p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
    p2, meta_2 = _evaluate_pillar_2(raw_44p, active_faults)
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
        active_faults,
    )
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

    pillars: Tuple[Milestone264PillarResult, ...] = (p1, p2, p3, p4, p5, p6)
    passed_count = sum(1 for p in pillars if p.passed)
    failed_ids = tuple(p.pillar_id for p in pillars if not p.passed)
    all_errors: List[str] = []
    for p in pillars:
        all_errors.extend(p.errors)

    all_ready = passed_count == len(pillars) and len(all_errors) == 0
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
    )
    min_h0_eq_h3 = min(
        int(meta_5["h0_equals_h3_count"]),
        int(meta_5["p186_h0_equals_h3_count"]),
        int(meta_5["p204_h0_equals_h3_count"]),
        int(meta_5["p216_h0_equals_h3_count"]),
        int(meta_5["p227_h0_equals_h3_count"]),
        int(meta_5["p248_h0_equals_h3_count"]),
        int(meta_5["p261_h0_equals_h3_count"]),
    )
    overall_ready_attach = bool(
        raw_1_off["overall_ready_for_hardware_attach"]
        or raw_1_sim["overall_ready_for_hardware_attach"]
        or meta_5["overall_ready_for_hardware_attach"]
    )

    common_fields: Dict[str, Any] = {
        "schema": REALHW_MILESTONE264_SCHEMA,
        "schema_version": REALHW_MILESTONE264_SCHEMA,
        "phase_version": PHASE_264_VERSION,
        "verification_mode": mode_str,
        "all_pillars_milestone_ready": all_ready,
        "status": STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        "o_rdonly_enforced": True,
        "cnflasha_userspace_write_blocked": bool(meta_2["cnflasha_userspace_write_blocked"]),
        "agent_auto_flash_blocked": bool(raw_1_sim["agent_auto_flash_blocked"]),
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
        "passive_tx_bytes": meta_2["passive_tx_bytes"],
        "passive_tx_bytes_emitted": meta_2["passive_tx_bytes"],
        "temp_dir_cleaned": True,
        "pillar_count": len(pillars),
        "passed_pillar_count": passed_count,
        "failed_pillar_ids": failed_ids,
        "gate102_total_gates": raw_1_sim["total_gates"],
        "gate102_offline_verified": raw_1_off["verified_gates"],
        "gate102_simulated_verified": raw_1_sim["verified_gates"],
        "gate102_all_verified": bool(raw_1_sim["all_102_gates_verified"]),
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
    digest = compute_milestone264_sha256(payload_no_sha)

    return RealHwMilestone264MasterGateReport(
        **common_fields,
        pillars=pillars,
        milestone264_sha256=digest,
    )


build_realhw_milestone264_master_gate_report = evaluate_realhw_milestone264_master_gate
evaluate_milestone_264_master_gate = evaluate_realhw_milestone264_master_gate
evaluate_milestone264_master_gate = evaluate_realhw_milestone264_master_gate


def verify_realhw_milestone264_master_gate(
    report: object,
) -> RealHwMilestone264VerifyResult:
    """Fail-closed verifier for a Grand Milestone Phase 264 Real-Hardware Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, RealHwMilestone264MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return RealHwMilestone264VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone264_sha256="",
            observed_milestone264_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or RealHwMilestone264MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = (
        payload.get("schema") == REALHW_MILESTONE264_SCHEMA
        and payload.get("schema_version") == REALHW_MILESTONE264_SCHEMA
    )
    if not schema_ok:
        errors.append(
            f"schema mismatch: schema={payload.get('schema')!r} schema_version={payload.get('schema_version')!r}"
        )

    expected_sha = compute_milestone264_sha256(payload)
    observed_sha = str(payload.get("milestone264_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(
            f"milestone264_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}"
        )

    redlines_ok = (
        payload.get("o_rdonly_enforced") is True
        and payload.get("cnflasha_userspace_write_blocked") is True
        and payload.get("agent_auto_flash_blocked") is True
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
    )
    if not redlines_ok:
        errors.append(
            "hard-locked zero-write / cnflasha-RO / zero-SPI-NOR / zero-EL3 / zero-USB-TX / zero-leak / zero-attach redlines breached"
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

    g_total = int(payload.get("gate102_total_gates", -1))
    g_off = int(payload.get("gate102_offline_verified", -1))
    g_sim = int(payload.get("gate102_simulated_verified", -1))
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
        g_total >= 102
        and g_off >= 99
        and g_off == g_total - 3
        and g_sim >= 102
        and g_sim == g_total
        and payload.get("gate102_all_verified") is True
        and rec_total >= 44
        and rec_passed == rec_total
        and aud_passed >= 45
        and aud_passed == aud_total
        and vm_passed >= 50
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
        and int(payload.get("h0_equals_h3_count", -1)) == 16
        and q_rounds_ver >= 25
        and q_rounds_ver == q_rounds_tot
        and q_runs_ver >= 75
        and q_runs_ver == q_runs_tot
        and q_pngs_ver >= 50
        and q_pngs_ver == q_pngs_tot
        and 0 < int(payload.get("qemu_png_max_bytes", -1)) < PNG_MAX_SIZE_50KIB_BYTES
        and int(payload.get("qemu_real_kernel_nop_count", -1)) == 0
        and int(payload.get("qemu_real_kernel_crashes", -1)) == 0
        and int(payload.get("qemu_real_kernel_emmc_writes", -1)) == 0
    )
    if not counts_ok:
        errors.append("milestone264 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append(
            "all_pillars_milestone_ready / status is not MILESTONE_264_PREBENCH_MASTER_VERIFIED"
        )

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 264 payload")

    valid = bool(
        schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0
    )
    return RealHwMilestone264VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone264_sha256=expected_sha,
        observed_milestone264_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


verify_milestone_264_master_gate = verify_realhw_milestone264_master_gate


def render_milestone264_markdown(report: RealHwMilestone264MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 264 Master Gate."""
    lines = [
        f"# Grand Milestone Phase 264 — Real-Hardware `ILME-FX3 Ver. 7.02` 6-Pillar Master Gate (`{report.schema}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone264_sha256}`",
        "",
        "## Hard-Locked Safety Redlines / 硬锁定安全红线",
        f"- `overall_ready_for_hardware_attach = {report.overall_ready_for_hardware_attach}`, "
        f"`hardware_live_attachment_authorized = {report.hardware_live_attachment_authorized}`, "
        f"`cnflasha_userspace_write_blocked = {report.cnflasha_userspace_write_blocked}`, "
        f"`persistent_emmc_writes_authorized = {report.persistent_emmc_writes_authorized}`, "
        f"`spi_nor_write_authorized = {report.spi_nor_write_authorized}`, "
        f"`el3_payload_transmit_authorized = {report.el3_payload_transmit_authorized}`",
        f"- `usb_packets_transmitted = {report.usb_packets_transmitted}`, "
        f"`physical_device_writes = {report.physical_device_writes}`, "
        f"`raw_firmware_bytes_leaked = {report.raw_firmware_bytes_leaked}`, "
        f"`e_nd_actuator_tx_count = {report.e_nd_actuator_tx_count}`, "
        f"`otp_fuse_touches = {report.otp_fuse_touches}`, "
        f"`rpmb_counter_increments = {report.rpmb_counter_increments}`, "
        f"`passive_tx_bytes_emitted = {report.passive_tx_bytes_emitted}`",
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
            "## Key Grand Milestone Phase 264 Metrics / 实机总闭环核心指标",
            f"- 102-Gate Preflight (`G01..G102`): offline=`{report.gate102_offline_verified}/{report.gate102_total_gates}` (`G10..G12` locked), simulated=`{report.gate102_simulated_verified}/{report.gate102_total_gates}` (`all_102_gates_verified={report.gate102_all_verified}`)",
            f"- 44-Pillar Recovery Master (`verify-44pillar-recovery`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`{report.recovery_status}`, `cnflasha_ro={report.cnflasha_userspace_write_blocked}`)",
            f"- 45+ Firmware-Lab Auditors (`auditors_passed >= 45`): `{report.auditors_passed}/{report.auditors_total}` (`raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`)",
            f"- 50+ Stage VM HIL Co-Emulation (`vm_stages_passed >= 50`): `{report.vm_stages_passed}/{report.vm_stages_total}` (`physical_device_writes={report.vm_physical_device_writes}`, `emmc_corruptions={report.vm_emmc_corruptions}`)",
            f"- Sextuple Bench Readiness Preflights (`Ph186 + Ph204 + Ph216 + Ph227 + Ph248 + Ph261`): `Ph186={report.p186_offline_go_no_go}/{report.p186_sim_go_no_go}`, `Ph204={report.p204_offline_go_no_go}/{report.p204_sim_go_no_go}`, `Ph216={report.p216_offline_go_no_go}/{report.p216_sim_go_no_go}`, `Ph227={report.p227_offline_go_no_go}/{report.p227_sim_go_no_go}`, `Ph248={report.p248_offline_go_no_go}/{report.p248_sim_go_no_go}`, `Ph261={report.p261_offline_go_no_go}/{report.p261_sim_go_no_go}` (`H0==H3={report.h0_equals_h3_count}/16`, `p261_e_nd_uart={report.p261_e_nd_uart_bytes_transmitted}B`)",
            f"- Live FX3 `7.02` (`4.9.337-scel+`) QEMU Receipts (`Rounds 28..52+`): `{report.qemu_rounds_verified}/{report.qemu_rounds_total}` rounds (`{report.qemu_runs_verified}/{report.qemu_runs_total}` sub-runs, `PNGs={report.qemu_png_receipts_verified}/{report.qemu_png_receipts_total}` max=`{report.qemu_png_max_bytes}B < 50KiB`), `nop={report.qemu_real_kernel_nop_count}`, `crashes={report.qemu_real_kernel_crashes}`, `emmc_writes={report.qemu_real_kernel_emmc_writes}`",
            "",
        ]
    )
    return "\n".join(lines)


def verify_milestone_264_cli(
    argv: Optional[Sequence[str]] = None,
    *,
    repo_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    json_output: bool = False,
    markdown_out: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> int:
    """Execute `verify-milestone-264` CLI supporting `--clean-room`/`--force-clean-room`/`--json`/`--out`."""
    if argv is not None:
        parser = argparse.ArgumentParser(prog="verify-milestone-264")
        parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
        parser.add_argument("--fx6-lib-dir", type=Path, default=DEFAULT_FX6_DONOR_LIB_DIR)
        parser.add_argument("--fx3-modules-dir", type=Path, default=DEFAULT_FX3_MODULES_DIR)
        parser.add_argument(
            "--force-clean-room",
            "--clean-room",
            dest="force_clean_room",
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
        json_output = bool(ns.json)
        output_path = ns.output
        markdown_out = ns.markdown_out

    rep = evaluate_realhw_milestone264_master_gate(
        repo_root=repo_root or DEFAULT_REPO_ROOT,
        fx6_lib_dir=fx6_lib_dir or DEFAULT_FX6_DONOR_LIB_DIR,
        fx3_modules_dir=fx3_modules_dir or DEFAULT_FX3_MODULES_DIR,
        force_clean_room=True if force_clean_room else None,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone264_markdown(rep), encoding="utf-8")
    v_res = verify_realhw_milestone264_master_gate(rep.to_dict())
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
                f"gate102={rep.gate102_offline_verified}/{rep.gate102_simulated_verified} "
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
                f"p248_off={rep.p248_offline_go_no_go} "
                f"p248_sim={rep.p248_sim_go_no_go} "
                f"p261_off={rep.p261_offline_go_no_go} "
                f"p261_sim={rep.p261_sim_go_no_go} "
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
                f"milestone264_sha256={rep.milestone264_sha256[:16]}...\n"
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
    "DEFAULT_REPO_ROOT",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "EMMC_WRITE_COUNT",
    "E_ND_ACTUATOR_TX_COUNT",
    "FIRMWARE_LAB_45_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "ISP_WRITE_AUTHORIZED",
    "MILESTONE264_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P8_CP_MUTATION_FORBIDDEN",
    "P264_PHYSICAL_DEVICE_WRITES",
    "P264_PILLAR_IDS",
    "P264_PILLAR_SPECS",
    "P264_PNG_MAX_SIZE_BYTES",
    "P264_RAW_FIRMWARE_BYTES_LEAKED",
    "P264_SCHEMA",
    "P264_STATUS_FAIL_CLOSED",
    "P264_STATUS_MILESTONE_READY",
    "P264_VERSION",
    "PASSIVE_TX_BYTES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_264_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "PNG_MAGIC_BYTES",
    "PNG_MAX_SIZE_50KIB_BYTES",
    "PNG_MAX_SIZE_BYTES",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_MILESTONE264_SCHEMA",
    "RECOVERY_44_PILLAR_IDS",
    "ROUND28_TO_52_PNG_RECEIPTS",
    "ROUND28_TO_52_SPECS",
    "ROUND51_EXPECTED_SCHEMA",
    "ROUND51_SUMMARY_RELPATH",
    "ROUND52_EXPECTED_SCHEMA",
    "ROUND52_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "RPMB_WRITES",
    "SCHEMA_VERSION",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "USB_PACKETS_TRANSMITTED",
    "VM_COEMULATION_50_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone264PillarResult",
    "RealHwMilestone264FaultInjection",
    "RealHwMilestone264MasterGateReport",
    "RealHwMilestone264VerifyResult",
    "build_realhw_milestone264_master_gate_report",
    "compute_milestone264_sha256",
    "evaluate_milestone264_master_gate",
    "evaluate_milestone_264_master_gate",
    "evaluate_realhw_milestone264_master_gate",
    "render_milestone264_markdown",
    "verify_milestone_264_cli",
    "verify_milestone_264_master_gate",
    "verify_realhw_milestone264_master_gate",
]
