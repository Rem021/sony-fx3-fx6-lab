"""Grand Milestone Phase 209 — Unified 6-Pillar Real-Hardware `ILME-FX3 Ver. 7.02` Pre-Bench Master Gate (`realhw_milestone209_master_gate_v1`).

Unites ALL Wave 21–26 Real-Hardware Main Track subsystems (Phases 134–208) and ALL
13 live Sony ILME-FX3 `Ver. 7.02` (`Linux 4.9.337-scel+`) ARM64 QEMU Rehearsal
Rounds (`Rounds 28..40` — `39/39` sub-experiments + `26/26` `< 28 KiB` PNG receipts)
into a single tamper-evident, fail-closed certificate executing in `< 8.0s` across
both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
modes while keeping `verify-milestone-175`, `verify-milestone-193`,
`preflight-card-insert`, and `preflight-bench-cable-fan-slot1` 100% intact:

- `P1` (`SAFETY_72GATE_REALHW_MASTER_PREFLIGHT`):
  Evaluates `evaluate_72gate_preflight` (`>= 72` gates; `69/72` offline with `G10..G12`
  physical Tier-0 attach locked, `72/72` dry-run simulated with
  `overall_ready_for_hardware_attach == False`), explicitly auditing `G67..G72`
  (USB-LAN/RTMP, Creators' Cloud ClipFlag & anamorphic, 4-Mode `[Fan Control]`
  `Auto/Minimum/Off in Rec/Always Off` with zero `Auto1/Auto2` & `Always Off -> Auto`
  pre-backup guard, `6.01` vs `7.00/7.02` `p2:/setting` User LUT split & independent
  `[Speed]`/`[Angle]` shutter slots, `BIG6` `[Home (Lower Left)]` zero physical e-ND
  actuator & Slot-1 `CAMSET01..10.DAT` dual-media split, and `VMC-BNCM1` body-only
  `TC IN` `EXT-LK` + digital Type-A HDMI `TC OUT`).
- `P2` (`TWENTY_EIGHT_PILLAR_RECOVERY_FAN_PWM_SHUTTER_LUT_VAULT`):
  Verifies `>= 28` recovery pillars (`evaluate_28pillar_recovery_master`, `H0 == H3`),
  including Pillar 27 and Pillar 28 (`28A` 4-mode Fan PWM interlock `6/6` + `28B`
  `6.01/7.02` LUT split & independent Shutter vault `6/6`), locking `OTP == 0`,
  `RPMB == 0`, `passive_tx_bytes_emitted == 0`, and `physical_usb_packets_emitted == 0`.
- `P3` (`FORTY_TWO_FIRMWARE_LAB_REALBIN_AUDITORS`):
  Verifies `>= 42` `fx3_firmware_lab` auditors (`#1..#42`, forward-compatible with
  Auditor 43+), explicitly auditing `#41` (4-Mode Fan PWM, Shutter Speed/Angle &
  `6.01` vs `7.02` User LUT split) and `#42` (`BIG6` zero e-ND actuator, Slot-1
  `CAMSET` dual-media split & `VMC-BNCM1` `TC IN` / HDMI `TC OUT`), locking
  `raw_firmware_bytes_leaked == 0` and `e_nd_actuator_tx_count == 0`.
- `P4` (`THIRTY_SIX_STAGE_VM_HIL_COEMULATION`):
  Verifies `>= 36` `outputs/fx3-vm` heterogeneous AArch64 AP + ARM32 Thumb-2 Stock-CP
  co-emulation stages (`Stages 1..36`, forward-compatible with Stage 37+), explicitly
  auditing Stages `34..36`, locking `emmc_corruptions == 0`, `cp_mutation_bytes == 0`,
  `e_nd_actuator_tx_count == 0`, and `wf12_00342260_hits == 0`.
- `P5` (`CLOSURE_CARD_INSERT_AND_BENCH_CABLE_FAN_SLOT1_PREFLIGHT`):
  Verifies `Phase 136`, `Phase 143`, `Phase 154`, `Phase 186` (`preflight-card-insert`),
  AND `Phase 204` (`preflight-bench-cable-fan-slot1` across both offline
  `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` and simulated
  `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` modes with
  `hardware_live_attachment_authorized == False` and `16/16 H0 == H3`).
- `P6` (`REAL_FX3_702_QEMU_ROUNDS_28_TO_40_AND_PNG_RECEIPTS`):
  Verifies committed `O_RDONLY` receipts from ALL 13 Real-Hardware QEMU Rehearsal
  Rounds (`Rounds 28..40`, `39/39` sub-experiments `r28a..r40c` on unmodified FX3
  `7.02` `4.9.337-scel+`) and all `26/26` `< 28 KiB` PNG receipts (with deterministic
  clean-room synthesis when `FX3_FX6_FORCE_CLEAN_ROOM=1`), proving `crashes == 0`,
  `nop_count == 0`, and `emmc_write_count == 0`.
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

from fx3_firmware_lab.realhw_big6_noend_camset_slot1_and_vmcbncm1_auditor import (  # noqa: E402
    analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1,
    realhw_big6_noend_camset_slot1_and_vmcbncm1_report_to_dict,
)
from fx3_firmware_lab.realhw_fan_pwm_shutter_angle_and_lut_601_702_split_auditor import (  # noqa: E402
    analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split,
    realhw_fan_pwm_shutter_angle_and_lut_601_702_split_report_to_dict,
)
from fx3_recovery.realhw_28pillar_fan_pwm_shutter_lut_split_verifier import (  # noqa: E402
    MASTER_28_PILLAR_IDS,
    evaluate_28pillar_recovery_master,
)
from fx3_safety.realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard import (  # noqa: E402
    evaluate_72gate_preflight,
)

from .hardware_readiness_packet import _is_forced_clean_room  # noqa: E402
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
)
from .realhw_bench_cable_fan_and_slot1_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    run_bench_cable_fan_and_slot1_preflight,
    verify_phase204_report,
)
from .realhw_milestone147_master_gate import _worker_phase136  # noqa: E402
from .realhw_milestone175_master_gate import (  # noqa: E402
    MILESTONE175_SCHEMA_VERSION,
    RoundQemuReceiptSpec,
)
from .realhw_milestone193_master_gate import (  # noqa: E402
    _66GATE_FAULT_FIELDS,
    FIRMWARE_LAB_40_AUDITOR_KEYS,
    MILESTONE193_SCHEMA_VERSION,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_BYTES,
    ROUND28_TO_37_PNG_RECEIPTS,
    ROUND28_TO_37_SPECS,
    VM_COEMULATION_33_STAGE_KEYS,
    RealHwMilestone193FaultInjection,
    _evaluate_pillar_3 as _eval_m193_p3,
    _evaluate_pillar_4 as _eval_m193_p4,
    _evaluate_pillar_5 as _eval_m193_p5,
    _extract_gate_dict,
    _inspect_round_png_receipt,
    _load_round28_to_37_summary,
    _worker_phase143_154_186,
    _worker_pillar_3_batch as _m193_worker_pillar_3_batch,
)
from .stage_b_milestone110_master_gate import _worker_pillar_4  # noqa: E402
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_MILESTONE209_SCHEMA: str = "realhw_milestone209_master_gate_v1"
MILESTONE209_SCHEMA_VERSION: str = REALHW_MILESTONE209_SCHEMA
SCHEMA_VERSION: str = REALHW_MILESTONE209_SCHEMA
PHASE_209_VERSION: str = "209.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
E_ND_ACTUATOR_TX_COUNT: int = 0
P8_CP_MUTATION_FORBIDDEN: bool = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN: bool = True
CP_MUTATION_BYTES: int = 0
WBI_MUTATION_BYTES: int = 0
CALIBRATION_MUTATION_BYTES: int = 0
USB_OR_CAMERA_OPERATIONS: int = 0
OTP_FUSE_TOUCHES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0

STATUS_MILESTONE_READY: str = "MILESTONE_209_PREBENCH_MASTER_VERIFIED"
STATUS_FAIL_CLOSED: str = "FAIL_CLOSED"

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_72GATE_REALHW_MASTER_PREFLIGHT"),
    ("P2", "TWENTY_EIGHT_PILLAR_RECOVERY_FAN_PWM_SHUTTER_LUT_VAULT"),
    ("P3", "FORTY_TWO_FIRMWARE_LAB_REALBIN_AUDITORS"),
    ("P4", "THIRTY_SIX_STAGE_VM_HIL_COEMULATION"),
    ("P5", "CLOSURE_CARD_INSERT_AND_BENCH_CABLE_FAN_SLOT1_PREFLIGHT"),
    ("P6", "REAL_FX3_702_QEMU_ROUNDS_28_TO_40_AND_PNG_RECEIPTS"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)

RECOVERY_28_PILLAR_IDS: Tuple[str, ...] = MASTER_28_PILLAR_IDS

FIRMWARE_LAB_42_AUDITOR_KEYS: Tuple[str, ...] = (
    *FIRMWARE_LAB_40_AUDITOR_KEYS,
    "realhw_fan_pwm_shutter_angle_and_lut_601_702_split_audit",
    "realhw_big6_noend_camset_slot1_and_vmcbncm1_audit",
)

VM_COEMULATION_36_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_33_STAGE_KEYS,
    "stage34_realhw_nouvc_dcc1_lut_path_cineei_hil",
    "stage35_realhw_fan_pwm_shutter_angle_lut_split_hil",
    "stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil",
)

ROUND38_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round38-realhw-nouvc-dcc1-lut-path-cineei-qemu/summary.json"
)
ROUND39_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round39-realhw-fan-pwm-shutter-angle-lut-split-qemu/summary.json"
)
ROUND40_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round40-realhw-big6-noend-camset-slot1-vmcbncm1-tcin-qemu/summary.json"
)

ROUND38_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round38-realhw-nouvc-dcc1-lut-path-cineei-qemu-v1"
)
ROUND39_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round39-realhw-fan-pwm-shutter-angle-lut-split-qemu-v1"
)
ROUND40_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round40-realhw-big6-noend-camset-slot1-vmcbncm1-tcin-qemu-v1"
)

ROUND28_TO_40_SPECS: Tuple[RoundQemuReceiptSpec, ...] = (
    *ROUND28_TO_37_SPECS,
    RoundQemuReceiptSpec(
        round_num=38,
        summary_relpath=ROUND38_SUMMARY_RELPATH,
        expected_schema=ROUND38_EXPECTED_SCHEMA,
        audit_key="r38_realhw_nouvc_dcc1_lut_path_cineei_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r38a_nouvc_gadget_blocked_rc_minus_95_and_usblan_netstream_38mbps_verified",
            "r38a_usbpd_fz100_and_dcc1_65w_5a_interlock_verified",
            "r38a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r38b_dual_media_cube_path_asymmetry_17_33pt_63b_verified",
            "r38b_cineei_dual_base_800_12800_and_p2_zero_writes_verified",
            "r38c_rmtp1bt_bt42_masks_ir_gps_and_restores_on_off_verified",
            "r38c_creators_cloud_clipflag_zero_nvs_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r38a_nouvc_dcc1_pd_big6_schinese", 1),
            ("r38b_lut_path_cineei", None),
            ("r38c_rmtp1bt_clipflag_seal", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=39,
        summary_relpath=ROUND39_SUMMARY_RELPATH,
        expected_schema=ROUND39_EXPECTED_SCHEMA,
        audit_key="r39_realhw_fan_pwm_shutter_angle_lut_split_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r39a_fan_4mode_rejects_auto1_auto2_and_offinrec_standby_max_pwm_verified",
            "r39a_pre_backup_always_off_blocked_until_forced_auto_verified",
            "r39a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r39b_independent_shutter_speed_angle_zero_clobber_zero_drift_verified",
            "r39b_shutter_angle_64f_normal_vs_360deg_11988p_100p_sq_clamp_verified",
            "r39c_lut_601_vs_702_p2_erofs_firewall_and_tmp_overlay_16slots_verified",
            "r39c_stock_702_lut_headers_intact_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r39a_fan_pwm_offinrec_big6_schinese", 1),
            ("r39b_shutter_speed_angle_clamp", None),
            ("r39c_lut_601_vs_702_firewall", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=40,
        summary_relpath=ROUND40_SUMMARY_RELPATH,
        expected_schema=ROUND40_EXPECTED_SCHEMA,
        audit_key="r40_realhw_big6_noend_camset_slot1_vmcbncm1_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r40a_big6_6tile_and_home_lower_left_aperture_nd_verified",
            "r40a_zero_e_nd_actuator_tx_firewall_verified",
            "r40a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r40b_slot1_only_camset_10slot_dualmedia_path_split_verified",
            "r40b_mr_lockout_and_cross_model_dat_firewall_verified",
            "r40c_vmcbncm1_body_only_tcin_10s_ext_lk_and_xlrh1_bnc_blocks_verified",
            "r40c_hdmi_movie_tcout_sq_disabled_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r40a_big6_home_noend_schinese", 1),
            ("r40b_camset_slot1_dualmedia_split", None),
            ("r40c_vmcbncm1_tcin_hdmi_tcout", None),
        ),
    ),
)

ROUND28_TO_40_PNG_RECEIPTS: Dict[int, Tuple[str, str]] = {
    **ROUND28_TO_37_PNG_RECEIPTS,
    38: (
        "reports/2026-11-15-round38-realhw-nouvc-dcc1-lut-path-cineei-qemu/assets/r38a-nouvc-dcc1-pd-big6-schinese-alpha.png",
        "reports/2026-11-15-round38-realhw-nouvc-dcc1-lut-path-cineei-qemu/assets/r38a-nouvc-dcc1-pd-big6-schinese-composited.png",
    ),
    39: (
        "reports/2026-11-15-round39-realhw-fan-pwm-shutter-angle-lut-split-qemu/assets/r39a-fan-pwm-offinrec-big6-schinese-alpha.png",
        "reports/2026-11-15-round39-realhw-fan-pwm-shutter-angle-lut-split-qemu/assets/r39a-fan-pwm-offinrec-big6-schinese-composited.png",
    ),
    40: (
        "reports/2026-11-15-round40-realhw-big6-noend-camset-slot1-vmcbncm1-tcin-qemu/assets/r40a-big6-noend-schinese-alpha.png",
        "reports/2026-11-15-round40-realhw-big6-noend-camset-slot1-vmcbncm1-tcin-qemu/assets/r40a-big6-noend-schinese-composited.png",
    ),
}

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_VM_STAGE_KEY_RE = re.compile(r"^stage(\d+)_")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealHwMilestone209FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 Wave 25–26 gates (G67..G72) + persistent-write lock
    p1_usblan_rtmp_kwargs: Optional[Mapping[str, Any]] = None
    p1_clipflag_anamorphic_kwargs: Optional[Mapping[str, Any]] = None
    p1_fan_pwm_thermal_kwargs: Optional[Mapping[str, Any]] = None
    p1_lut_split_shutter_angle_kwargs: Optional[Mapping[str, Any]] = None
    p1_big6_camset_slot1_kwargs: Optional[Mapping[str, Any]] = None
    p1_vmcbncm1_tcin_hdmi_tcout_kwargs: Optional[Mapping[str, Any]] = None
    p1_request_persistent_writes: bool = False

    # P2 28-pillar recovery master + zero-touch redlines
    p2_fault_inject_pillar: Optional[str] = None
    p2_otp_fuse_touches_override: int = 0
    p2_rpmb_increments_override: int = 0
    p2_passive_tx_bytes_override: int = 0
    p2_physical_usb_packets_override: int = 0
    p2_physical_device_writes_override: int = 0
    p2_raw_firmware_bytes_leaked_override: int = 0

    # P3 >= 42 firmware-lab auditors (#41..#42 + zero-leak / zero-e-ND)
    p3_fan_shutter_lut_p2_mutation_override: int = 0
    p3_big6_camset_vmc_end_tx_override: int = 0
    p3_raw_firmware_bytes_leaked_override: int = 0

    # P4 >= 36 VM HIL stages (Stages 34..36)
    p4_stage34_nouvc_or_pd_faults: int = 0
    p4_stage35_thermal_or_lut_faults: int = 0
    p4_stage36_end_or_camset_or_vmc_faults: int = 0

    # P5 preflight-card-insert (Ph186) + preflight-bench-cable-fan-slot1 (Ph204)
    p5_inject_p186_h0_h3_drift: bool = False
    p5_inject_p204_fan_auto1_fault: bool = False
    p5_inject_p204_always_off_fault: bool = False
    p5_inject_p204_end_tx_fault: bool = False
    p5_inject_p204_camset_slot2_fault: bool = False
    p5_inject_p204_vmc_xlrh1_port_fault: bool = False
    p5_inject_p204_h0_h3_drift: bool = False
    p5_inject_p204_usb_packets_override: int = 0

    # P6 Rounds 28..40 live QEMU kernel rehearsal & PNG receipts
    p6_round_nop_override_num: Optional[int] = None
    p6_round_nop_count_override: Optional[int] = None
    p6_round_crash_override_num: Optional[int] = None
    p6_round_crashes_override: Optional[int] = None
    p6_round_emmc_override_num: Optional[int] = None
    p6_round_emmc_writes_override: Optional[int] = None
    p6_tamper_schema_round_num: Optional[int] = None
    p6_png_size_override_round_num: Optional[int] = None
    p6_png_size_override_bytes: Optional[int] = None

    # Optional upstream Milestone 193 fault injection pass-through
    m193_faults: Optional[RealHwMilestone193FaultInjection] = None


@dataclass(frozen=True)
class Milestone209PillarResult:
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
class RealHwMilestone209MasterGateReport:
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
    raw_firmware_bytes_leaked: int
    e_nd_actuator_tx_count: int
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
    pillars: Tuple[Milestone209PillarResult, ...]
    gate72_total_gates: int
    gate72_offline_verified: int
    gate72_simulated_verified: int
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
    qemu_rounds_verified: int
    qemu_runs_verified: int
    qemu_png_receipts_verified: int
    qemu_png_max_bytes: int
    qemu_round_runs_by_round: Dict[str, int]
    qemu_real_kernel_nop_count: int
    qemu_real_kernel_crashes: int
    qemu_real_kernel_emmc_writes: int
    errors: Tuple[str, ...]
    milestone209_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class RealHwMilestone209VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone209_sha256: str
    observed_milestone209_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_milestone209_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `RealHwMilestone209MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone209_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 8.0s)
# ---------------------------------------------------------------------------


_72GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_usblan_rtmp_kwargs", "usblan_rtmp_kwargs"),
    ("p1_clipflag_anamorphic_kwargs", "clipflag_anamorphic_kwargs"),
    ("p1_fan_pwm_thermal_kwargs", "fan_pwm_thermal_kwargs"),
    ("p1_lut_split_shutter_angle_kwargs", "lut_split_shutter_angle_kwargs"),
    ("p1_big6_camset_slot1_kwargs", "big6_camset_slot1_kwargs"),
    ("p1_vmcbncm1_tcin_hdmi_tcout_kwargs", "vmcbncm1_tcin_hdmi_tcout_kwargs"),
)


def _effective_m193_faults(
    faults: RealHwMilestone209FaultInjection,
) -> RealHwMilestone193FaultInjection:
    base = faults.m193_faults or RealHwMilestone193FaultInjection()
    if faults.p5_inject_p186_h0_h3_drift and not base.p5_inject_p186_h0_h3_drift:
        d = asdict(base)
        d["p5_inject_p186_h0_h3_drift"] = True
        return RealHwMilestone193FaultInjection(**d)
    return base


def _fault_to_72gate_worker_dict(faults: RealHwMilestone209FaultInjection) -> Dict[str, Any]:
    m193_f = _effective_m193_faults(faults)
    out: Dict[str, Any] = {
        "p1_request_persistent_writes": bool(
            faults.p1_request_persistent_writes or m193_f.p1_request_persistent_writes
        ),
    }
    for src_attr, _ in _66GATE_FAULT_FIELDS:
        val = getattr(m193_f, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    for src_attr, _ in _72GATE_EXTRA_FAULT_FIELDS:
        val = getattr(faults, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    return out


def _worker_72gate_single(args: Tuple[str, bool, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, dry_run_sim, fault_dict = args
    repo_root = Path(repo_root_str)
    kwargs: Dict[str, Any] = {
        "request_persistent_emmc_writes": bool(
            fault_dict.get("p1_request_persistent_writes", False)
        )
    }
    for src_attr, dst_kw in (*_66GATE_FAULT_FIELDS, *_72GATE_EXTRA_FAULT_FIELDS):
        if fault_dict.get(src_attr) is not None:
            kwargs[dst_kw] = fault_dict[src_attr]

    rep = evaluate_72gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated=dry_run_sim,
        **kwargs,
    )

    m70 = rep.master_70_report
    m68 = m70.get("master_68_report", {})
    m66 = m68.get("master_66_report", {})
    m64 = m66.get("master_64_report", {})
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
        ("g71", rep.g71_result),
        ("g72", rep.g72_result),
    ):
        nested_g_valid[tag] = isinstance(src, Mapping) and bool(src.get("valid", False))

    g71_guard = (
        rep.g71_result.get("big6_noend_camset_slot1_guard", {})
        if isinstance(rep.g71_result, Mapping)
        else {}
    )
    gates_brief = [_extract_gate_dict(g) for g in rep.gates]
    return {
        "schema": rep.schema,
        "verification_mode": rep.verification_mode,
        "total_gates": int(rep.summary.get("total_gates", len(gates_brief))),
        "verified_gates": int(rep.summary.get("verified_gates", 0)),
        "offline_69_gates_verified": bool(rep.offline_69_gates_verified),
        "all_72_gates_verified": bool(rep.all_72_gates_verified),
        "g13_to_g72_all_passed": bool(rep.g13_to_g72_all_passed),
        "g71_to_g72_all_passed": bool(rep.g71_to_g72_all_passed),
        "dry_run_rehearsal_only": bool(rep.dry_run_rehearsal_only),
        "overall_ready_for_hardware_attach": bool(rep.overall_ready_for_hardware_attach),
        "agent_auto_flash_blocked": bool(rep.agent_auto_flash_blocked),
        "el3_payload_transmit_authorized": bool(rep.el3_payload_transmit_authorized),
        "spi_nor_write_authorized": bool(rep.spi_nor_write_authorized),
        "persistent_emmc_writes_authorized": bool(rep.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep.persistent_write_release),
        "physical_usb_packets_emitted": int(rep.physical_usb_packets_emitted),
        "raw_firmware_bytes_leaked": int(rep.raw_firmware_bytes_leaked),
        "g71_e_nd_actuator_tx_count": int(g71_guard.get("e_nd_actuator_tx_count", -1)),
        "nested_g63_to_g72_valid": nested_g_valid,
        "gates_45_to_end": gates_brief[44:],
        "errors": list(rep.errors),
    }


def _worker_recovery_28pillar(args: Tuple[bool, Optional[str]]) -> Dict[str, Any]:
    use_clean_room, fault_pillar = args
    rep = evaluate_28pillar_recovery_master(
        force_clean_room=use_clean_room,
        fault_inject_pillar=fault_pillar,
    )
    p_by_num = {int(p.pillar_number): p for p in rep.pillars}
    p27_obj = p_by_num.get(27)
    p28_obj = p_by_num.get(28)
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
        "pillar27": asdict(p27_obj) if p27_obj is not None else {},
        "pillar28": asdict(p28_obj) if p28_obj is not None else {},
        "pillar28_a_fan_pwm_interlock": asdict(rep.pillar28_a_fan_pwm_interlock),
        "pillar28_b_lut_split_shutter_vault": asdict(rep.pillar28_b_lut_split_shutter_vault),
        "master_28pillar_sha256": rep.master_28pillar_sha256,
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


def _worker_pillar_3_batch_209(args: Tuple[Tuple[str, ...], bool]) -> Dict[str, Dict[str, Any]]:
    groups, clean_room = args
    merged: Dict[str, Dict[str, Any]] = {}
    wave25_26 = ("realhw_fan_shutter_lut601_702", "realhw_big6_camset_vmcbncm1")
    m193_groups = tuple(g for g in groups if g not in wave25_26)
    if m193_groups:
        merged.update(_m193_worker_pillar_3_batch((m193_groups, clean_room)))
    for g in groups:
        if g == "realhw_fan_shutter_lut601_702":
            merged["realhw_fan_pwm_shutter_angle_and_lut_601_702_split_audit"] = (
                realhw_fan_pwm_shutter_angle_and_lut_601_702_split_report_to_dict(
                    analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(
                        clean_room=clean_room
                    )
                )
            )
        elif g == "realhw_big6_camset_vmcbncm1":
            merged["realhw_big6_noend_camset_slot1_and_vmcbncm1_audit"] = (
                realhw_big6_noend_camset_slot1_and_vmcbncm1_report_to_dict(
                    analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(clean_room=clean_room)
                )
            )
    return merged


def _worker_phase204(
    args: Tuple[str, str, bool, Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    fx6_lib_dir_str, fx3_modules_dir_str, use_clean_room, p204_faults = args
    fx6_dir = Path(fx6_lib_dir_str)
    fx3_dir = Path(fx3_modules_dir_str)

    p204_off = run_bench_cable_fan_and_slot1_preflight(
        simulate_ready_bench=False,
        force_clean_room=use_clean_room,
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
    ).to_dict()

    sim_kwargs: Dict[str, Any] = {
        "simulate_ready_bench": True,
        "force_clean_room": use_clean_room,
        "fx6_lib_dir": fx6_dir,
        "fx3_modules_dir": fx3_dir,
    }
    if p204_faults.get("fan_auto1"):
        sim_kwargs["fan_mode"] = "Auto1"
    elif p204_faults.get("always_off"):
        sim_kwargs["fan_mode"] = "Always Off"
    if p204_faults.get("end_tx"):
        sim_kwargs["e_nd_actuator_tx_count"] = 1
    if p204_faults.get("camset_slot2"):
        sim_kwargs["camset_target_slot"] = 2
    if p204_faults.get("vmc_xlrh1_port"):
        sim_kwargs["vmc_bncm1_attached"] = True
        sim_kwargs["vmc_bncm1_port"] = "XLR_H1_HANDLE_MICRO_USB"
        sim_kwargs["vmc_bncm1_direction"] = "TC_IN"
    if p204_faults.get("h0_h3_drift"):
        sim_kwargs["inject_h0_h3_drift_surface"] = "p2"

    p204_sim = run_bench_cable_fan_and_slot1_preflight(**sim_kwargs).to_dict()
    return p204_off, p204_sim


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1 .. P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
) -> Milestone209PillarResult:
    errors: List[str] = []
    total_gates = int(raw_sim.get("total_gates", 0))
    offline_verified = int(raw_off.get("verified_gates", -1))
    sim_verified = int(raw_sim.get("verified_gates", -1))
    e_nd_tx = int(raw_sim.get("g71_e_nd_actuator_tx_count", -1))

    if total_gates < 72:
        errors.append(f"p1: total_gates expected >= 72, got {total_gates}")
    if (
        not raw_off.get("offline_69_gates_verified")
        or offline_verified < 69
        or offline_verified >= total_gates
    ):
        errors.append(
            f"p1: offline hardware-truth gates expected >= 69 and < {total_gates}, got {offline_verified}/{total_gates}"
        )
    if raw_off.get("all_72_gates_verified") or raw_off.get("overall_ready_for_hardware_attach"):
        errors.append("p1: offline mode must remain blocked for live hardware attach (G10..G12)")
    if (
        not raw_sim.get("all_72_gates_verified")
        or sim_verified < 72
        or sim_verified != total_gates
    ):
        errors.append(
            f"p1: simulated rehearsal gates expected >= 72 and == {total_gates}, got {sim_verified}/{total_gates}"
        )
    if not raw_sim.get("dry_run_rehearsal_only") or raw_sim.get("overall_ready_for_hardware_attach"):
        errors.append("p1: simulated 72-gate rehearsal must keep overall_ready_for_hardware_attach=False")
    if not raw_sim.get("g13_to_g72_all_passed") or not raw_sim.get("g71_to_g72_all_passed"):
        errors.append("p1: G13..G72 or G71..G72 safety guard gate blocked")
    if e_nd_tx != 0:
        errors.append(f"p1: G71 BIG6 e_nd_actuator_tx_count={e_nd_tx} != 0")

    nested = raw_sim.get("nested_g63_to_g72_valid", {})
    for gnum in range(63, 73):
        if not bool(nested.get(f"g{gnum}", False)):
            errors.append(f"p1: G{gnum} nested safety guard failed")

    g45_to_end = raw_sim.get("gates_45_to_end", ())
    if len(g45_to_end) < 28 or any(not bool(g.get("passed", False)) for g in g45_to_end):
        errors.append("p1: one or more G45..G72+ master gates failed in simulated rehearsal")

    for obj_name, obj in (("offline", raw_off), ("simulated", raw_sim)):
        if (
            obj.get("persistent_emmc_writes_authorized") is not False
            or obj.get("persistent_write_release") is not False
            or obj.get("spi_nor_write_authorized") is not False
            or obj.get("el3_payload_transmit_authorized") is not False
            or obj.get("agent_auto_flash_blocked") is not True
            or int(obj.get("physical_usb_packets_emitted", -1)) != 0
            or int(obj.get("raw_firmware_bytes_leaked", -1)) != 0
        ):
            errors.append(f"p1 ({obj_name}): hard-locked zero-write/SPI-NOR/EL3/USB-TX/leak guard breached")

    for err in raw_sim.get("errors", ()):
        errors.append(f"p1_72gate: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_sim.get("schema"),
        "verification_mode": raw_sim.get("verification_mode"),
        "total_gates": total_gates,
        "offline_verified_gates": offline_verified,
        "offline_ready_for_hardware_attach": raw_off.get("overall_ready_for_hardware_attach"),
        "simulated_verified_gates": sim_verified,
        "simulated_ready_for_hardware_attach": raw_sim.get("overall_ready_for_hardware_attach"),
        "g13_to_g72_all_passed": raw_sim.get("g13_to_g72_all_passed"),
        "g71_to_g72_all_passed": raw_sim.get("g71_to_g72_all_passed"),
        "g71_e_nd_actuator_tx_count": e_nd_tx,
        "nested_g63_to_g72_valid": dict(nested),
        "persistent_emmc_writes_authorized": raw_sim.get("persistent_emmc_writes_authorized"),
        "persistent_write_release": raw_sim.get("persistent_write_release"),
        "spi_nor_write_authorized": raw_sim.get("spi_nor_write_authorized"),
        "el3_payload_transmit_authorized": raw_sim.get("el3_payload_transmit_authorized"),
        "agent_auto_flash_blocked": raw_sim.get("agent_auto_flash_blocked"),
        "physical_usb_packets_emitted": int(raw_sim.get("physical_usb_packets_emitted", 0)),
        "raw_firmware_bytes_leaked": int(raw_sim.get("raw_firmware_bytes_leaked", 0)),
    }
    return Milestone209PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_72GATE_REALHW_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"72-Gate offline={offline_verified}/{total_gates} (G10..G12 locked) "
            f"sim={sim_verified}/{total_gates}, G13..G72={raw_sim.get('g13_to_g72_all_passed')}, "
            f"e_nd_tx={e_nd_tx} {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    raw_28p: Mapping[str, Any],
    faults: RealHwMilestone209FaultInjection,
) -> Tuple[Milestone209PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    if not raw_28p.get("all_passed"):
        errors.append(
            f"p2: evaluate_28pillar_recovery_master failed ({raw_28p.get('failed_pillars')})"
        )

    pillar_list = raw_28p.get("pillars", ())
    pillar_statuses: Dict[str, bool] = {}
    for pentry in pillar_list:
        if isinstance(pentry, Mapping):
            pid = str(pentry.get("pillar_id", ""))
            ok = bool(pentry.get("passed"))
            if pid:
                pillar_statuses[pid] = ok
                if not ok:
                    errors.append(f"p2: pillar {pid} failed ({pentry.get('errors')})")

    for expected_pid in MASTER_28_PILLAR_IDS:
        if not pillar_statuses.get(expected_pid, False):
            errors.append(f"p2: required recovery pillar missing or failed: {expected_pid}")

    total_pillars = len(pillar_statuses)
    passed_pillars = sum(1 for v in pillar_statuses.values() if v)
    if total_pillars < 28 or passed_pillars < 28 or passed_pillars != total_pillars:
        errors.append(
            f"p2: recovery pillars expected >= 28 and all passing, got {passed_pillars}/{total_pillars}"
        )

    p27 = raw_28p.get("pillar27", {})
    p28a = raw_28p.get("pillar28_a_fan_pwm_interlock", {})
    p28b = raw_28p.get("pillar28_b_lut_split_shutter_vault", {})
    if not bool(p27.get("passed", False)):
        errors.append("p2: Pillar 27 No-UVC/DC-C1/LUT-Path/RMT-P1BT recovery verifier failed")
    if not bool(p28a.get("passed", False)) or not bool(p28b.get("passed", False)):
        errors.append("p2: Pillar 28A (4-Mode Fan PWM) or Pillar 28B (6.01/7.02 LUT & Shutter H0==H3) failed")

    otp_touches = (
        int(raw_28p.get("otp_fuse_touches", 0))
        + int(raw_28p.get("otp_fuse_writes", 0))
        + int(faults.p2_otp_fuse_touches_override)
    )
    rpmb_incs = int(raw_28p.get("rpmb_counter_increments", 0)) + int(
        faults.p2_rpmb_increments_override
    )
    passive_tx = int(raw_28p.get("passive_tx_bytes_emitted", 0)) + int(
        faults.p2_passive_tx_bytes_override
    )
    phys_usb = int(raw_28p.get("physical_usb_packets_emitted", 0)) + int(
        faults.p2_physical_usb_packets_override
    )
    phys_writes = int(raw_28p.get("physical_device_writes", 0)) + int(
        faults.p2_physical_device_writes_override
    )
    leaked_fw = int(raw_28p.get("raw_firmware_bytes_leaked", 0)) + int(
        faults.p2_raw_firmware_bytes_leaked_override
    )

    if otp_touches != 0 or rpmb_incs != 0 or passive_tx != 0 or phys_usb != 0:
        errors.append(
            f"p2: zero-touch counters breached (otp={otp_touches}, rpmb={rpmb_incs}, tx={passive_tx}, usb={phys_usb})"
        )
    if phys_writes != 0 or leaked_fw != 0:
        errors.append(
            f"p2: physical_device_writes={phys_writes}, raw_fw_leaked={leaked_fw} must be 0"
        )

    if (
        raw_28p.get("el3_payload_transmit_authorized") is not False
        or raw_28p.get("isp_write_authorized") is not False
        or raw_28p.get("spi_nor_write_authorized") is not False
        or raw_28p.get("persistent_emmc_writes_authorized") is not False
        or raw_28p.get("persistent_write_release") is not False
        or raw_28p.get("live_usb_iokit_transmit_enabled") is not False
    ):
        errors.append("p2: hard-locked EL3/ISP/SPI-NOR/eMMC/IOKit write guard breached")

    for err in raw_28p.get("errors", ()):
        errors.append(f"p2_master: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_28p.get("schema"),
        "verification_mode": raw_28p.get("verification_mode"),
        "recovery_pillar_count": total_pillars,
        "recovery_pillars_passed": passed_pillars,
        "pillar_statuses": pillar_statuses,
        "master_28pillar_sha256": raw_28p.get("master_28pillar_sha256"),
        "otp_fuse_touches": otp_touches,
        "rpmb_counter_increments": rpmb_incs,
        "passive_tx_bytes_emitted": passive_tx,
        "physical_usb_packets_emitted": phys_usb,
        "physical_device_writes": phys_writes,
        "raw_firmware_bytes_leaked": leaked_fw,
        "el3_payload_transmit_authorized": raw_28p.get("el3_payload_transmit_authorized"),
        "isp_write_authorized": raw_28p.get("isp_write_authorized"),
        "spi_nor_write_authorized": raw_28p.get("spi_nor_write_authorized"),
        "persistent_emmc_writes_authorized": raw_28p.get("persistent_emmc_writes_authorized"),
    }
    pillar = Milestone209PillarResult(
        pillar_id="P2",
        pillar_name="TWENTY_EIGHT_PILLAR_RECOVERY_FAN_PWM_SHUTTER_LUT_VAULT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Recovery {passed_pillars}/{total_pillars} pillars (>=28 required; Pillars 27..28 "
            f"Fan-PWM-4Mode/LUT-6.01-vs-7.02/Shutter-H0==H3), "
            f"OTP={otp_touches}, RPMB={rpmb_incs}, usb_pkts={phys_usb} "
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
        "raw_firmware_bytes_leaked": leaked_fw,
    }
    return pillar, meta


def _evaluate_pillar_3(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: RealHwMilestone209FaultInjection,
) -> Tuple[Milestone209PillarResult, Dict[str, Any]]:
    m193_p3, meta_40 = _eval_m193_p3(auditors, _effective_m193_faults(faults))
    errors: List[str] = list(m193_p3.errors)
    auditor_statuses: Dict[str, bool] = dict(m193_p3.evidence["auditor_statuses"])
    auditor_sha256s: Dict[str, Optional[str]] = dict(m193_p3.evidence["auditor_sha256s"])

    # #41: 4-Mode Fan PWM, Independent Shutter Speed/Angle & 6.01 vs 7.02 LUT Binary Split
    a41 = auditors.get("realhw_fan_pwm_shutter_angle_and_lut_601_702_split_audit", {})
    a41_p2_mut = int(a41.get("p2_setting_mutation_bytes", -1)) + int(
        faults.p3_fan_shutter_lut_p2_mutation_override
    )
    a41_leak = int(a41.get("raw_firmware_bytes_leaked", -1))
    if (
        not bool(a41.get("all_checks_passed"))
        or a41.get("o_rdonly_enforced") is not True
        or a41.get("fan_4mode_and_prebackup_thermal_verified") is not True
        or a41.get("independent_shutter_speed_angle_verified") is not True
        or a41.get("lut_601_vs_702_binary_split_firewall_verified") is not True
        or a41.get("write_firewall_and_matrix_verified") is not True
        or a41.get("persistent_emmc_writes_authorized") is not False
        or a41.get("spi_nor_write_authorized") is not False
        or a41.get("el3_payload_transmit_authorized") is not False
        or int(a41.get("persistent_writes", -1)) != 0
        or int(a41.get("calibration_mutation_bytes", -1)) != 0
        or a41_p2_mut != 0
        or a41_leak != 0
    ):
        errors.append(
            f"p3: #41 realhw_fan_pwm_shutter_angle_and_lut_601_702_split_audit failed (p2_mut={a41_p2_mut})"
        )

    # #42: BIG6 Zero Physical e-ND Actuator, Slot-1 CAMSET Dual-Media Split & VMC-BNCM1 TC IN
    a42 = auditors.get("realhw_big6_noend_camset_slot1_and_vmcbncm1_audit", {})
    a42_end_tx = int(a42.get("e_nd_actuator_tx_count", -1)) + int(
        faults.p3_big6_camset_vmc_end_tx_override
    )
    a42_leak = int(a42.get("raw_firmware_bytes_leaked", -1))
    if (
        not bool(a42.get("all_checks_passed"))
        or a42.get("o_rdonly_enforced") is not True
        or a42.get("big6_6tile_and_zero_end_boundary_verified") is not True
        or a42.get("camset_slot1_dual_path_and_firewall_verified") is not True
        or a42.get("vmcbncm1_body_tcin_and_hdmi_tcout_verified") is not True
        or a42.get("zero_write_firewall_and_matrix_verified") is not True
        or a42.get("persistent_emmc_writes_authorized") is not False
        or a42.get("spi_nor_write_authorized") is not False
        or a42.get("el3_payload_transmit_authorized") is not False
        or int(a42.get("persistent_writes", -1)) != 0
        or int(a42.get("p2_setting_mutation_bytes", -1)) != 0
        or int(a42.get("calibration_mutation_bytes", -1)) != 0
        or a42_end_tx != 0
        or a42_leak != 0
    ):
        errors.append(
            f"p3: #42 realhw_big6_noend_camset_slot1_and_vmcbncm1_audit failed (e_nd_tx={a42_end_tx})"
        )

    for key in FIRMWARE_LAB_42_AUDITOR_KEYS[40:]:
        obj = auditors.get(key, {})
        ok = isinstance(obj, Mapping) and bool(obj.get("all_checks_passed"))
        auditor_statuses[key] = ok
        sha_val = (
            obj.get("report_sha256") or obj.get("audit_digest_sha256")
            if isinstance(obj, Mapping)
            else None
        )
        auditor_sha256s[key] = str(sha_val) if sha_val else None

    # Forward-compatible inclusion of any Wave 27+ auditor keys passed into `auditors`
    for key, obj in sorted(auditors.items()):
        if key not in auditor_statuses and key.endswith("_audit") and isinstance(obj, Mapping):
            ok = bool(obj.get("all_checks_passed"))
            auditor_statuses[key] = ok
            if not ok:
                errors.append(f"p3: forward-compat auditor {key} failed")

    total_count = len(auditor_statuses)
    passed_count = sum(1 for v in auditor_statuses.values() if v)
    total_cal_mut = max(
        int(meta_40["calibration_mutation_bytes"]),
        max(0, a41_p2_mut),
    )
    total_leaked = (
        int(meta_40["raw_firmware_bytes_leaked"])
        + max(0, a41_leak)
        + max(0, a42_leak)
        + int(faults.p3_raw_firmware_bytes_leaked_override)
    )

    if total_count < 42 or passed_count < 42 or passed_count != total_count:
        errors.append(
            f"p3: expected >= 42 auditors and all passing, got {passed_count}/{total_count}"
        )
    if total_leaked != 0:
        errors.append(f"p3: raw_firmware_bytes_leaked={total_leaked} != 0")
    if a42_end_tx != 0:
        errors.append(f"p3: e_nd_actuator_tx_count={a42_end_tx} != 0")

    passed = len(errors) == 0 and total_cal_mut == 0 and total_leaked == 0 and a42_end_tx == 0
    evidence = dict(m193_p3.evidence)
    evidence.update(
        {
            "auditor_count": total_count,
            "passed_auditor_count": passed_count,
            "auditor_statuses": auditor_statuses,
            "auditor_sha256s": auditor_sha256s,
            "calibration_mutation_bytes": total_cal_mut,
            "raw_firmware_bytes_leaked": total_leaked,
            "e_nd_actuator_tx_count": max(0, a42_end_tx),
        }
    )
    pillar = Milestone209PillarResult(
        pillar_id="P3",
        pillar_name="FORTY_TWO_FIRMWARE_LAB_REALBIN_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {passed_count}/{total_count} auditors (>=42 required; Auditors 41..42 "
            f"Fan-PWM-Shutter-LUT601v702/BIG6-NoEND-CAMSET-VMCBNCM1), "
            f"e_nd_tx={max(0, a42_end_tx)}, leaked={total_leaked}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "auditor_count": total_count,
        "passed_count": passed_count,
        "calibration_mutation_bytes": total_cal_mut,
        "bk4_persistent_nvram_writes": int(meta_40["bk4_persistent_nvram_writes"]),
        "wbi_mutation_bytes": int(meta_40["wbi_mutation_bytes"]),
        "raw_firmware_bytes_leaked": total_leaked,
        "e_nd_actuator_tx_count": max(0, a42_end_tx),
    }
    return pillar, meta


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: RealHwMilestone209FaultInjection,
) -> Tuple[Milestone209PillarResult, Dict[str, Any]]:
    m193_p4, meta_33 = _eval_m193_p4(vm_rep, _effective_m193_faults(faults))
    errors: List[str] = list(m193_p4.errors)
    stage_statuses: Dict[str, bool] = dict(m193_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_36_STAGE_KEYS[33:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if not ok:
            errors.append(f"p4: VM co-emulation {skey} failed")

    # Forward-compatible discovery of Stage 37+ keys as Wave 27+ modules merge
    for skey, sobj in sorted(vm_rep.items()):
        m = _VM_STAGE_KEY_RE.match(str(skey))
        if m and int(m.group(1)) >= 37 and skey not in stage_statuses and isinstance(sobj, Mapping):
            ok = bool(sobj.get("all_checks_passed"))
            stage_statuses[skey] = ok
            if not ok:
                errors.append(f"p4: forward-compat VM stage {skey} failed")

    # Stage 34: No-UVC Gadget, USB-PD vs DC-C1 >=65W/5A & Dual-Media .cube LUT Path HIL
    s34 = vm_rep.get("stage34_realhw_nouvc_dcc1_lut_path_cineei_hil", {})
    s34_mut = (
        int(s34.get("emmc_mutation_bytes", -1))
        + int(s34.get("spi_nor_mutation_bytes", -1))
        + int(s34.get("usb_phy_hang_events", -1))
        + int(s34.get("power_cut_brownout_events", -1))
        + int(s34.get("sensor_analog_gain_contamination_events", -1))
        + int(faults.p4_stage34_nouvc_or_pd_faults)
    )
    if (
        int(s34.get("nop_count", -1)) != 0
        or int(s34.get("cp_mutation_bytes", -1)) != 0
        or int(s34.get("wbi_mutation_bytes", -1)) != 0
        or int(s34.get("calibration_mutation_bytes", -1)) != 0
        or s34.get("persistent_emmc_writes_authorized") is not False
        or s34.get("spi_nor_write_authorized") is not False
        or s34.get("el3_payload_transmit_authorized") is not False
        or int(s34.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(s34.get("wf12_00342260_hits", -1)) != 0
        or s34_mut != 0
    ):
        errors.append(f"p4: Stage 34 redlines violated (nouvc_or_pd={s34_mut})")

    # Stage 35: 4-Mode Fan PWM, Shutter Speed/Angle & 6.01 vs 7.02 LUT Split HIL
    s35 = vm_rep.get("stage35_realhw_fan_pwm_shutter_angle_lut_split_hil", {})
    s35_mut = (
        int(s35.get("emmc_mutation_bytes", -1))
        + int(s35.get("spi_nor_mutation_bytes", -1))
        + int(s35.get("p2_setting_mutation_bytes", -1))
        + int(s35.get("thermal_runaway_events", -1))
        + int(s35.get("lut_color_solver_corruption_events", -1))
        + int(faults.p4_stage35_thermal_or_lut_faults)
    )
    if (
        int(s35.get("nop_count", -1)) != 0
        or int(s35.get("cp_mutation_bytes", -1)) != 0
        or int(s35.get("wbi_mutation_bytes", -1)) != 0
        or int(s35.get("calibration_mutation_bytes", -1)) != 0
        or s35.get("persistent_emmc_writes_authorized") is not False
        or s35.get("spi_nor_write_authorized") is not False
        or s35.get("el3_payload_transmit_authorized") is not False
        or int(s35.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(s35.get("wf12_00342260_hits", -1)) != 0
        or s35_mut != 0
    ):
        errors.append(f"p4: Stage 35 redlines violated (thermal_or_lut={s35_mut})")

    # Stage 36: BIG6 Zero e-ND Actuator, Slot-1 CAMSET Dual-Media & VMC-BNCM1 TC IN HIL
    s36 = vm_rep.get("stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil", {})
    s36_end_tx = int(s36.get("e_nd_actuator_tx_count", -1))
    s36_mut = (
        int(s36.get("emmc_mutation_bytes", -1))
        + int(s36.get("spi_nor_mutation_bytes", -1))
        + int(s36.get("slot1_fx3_camset_mutation_bytes", -1))
        + int(s36.get("p2_setting_mutation_bytes", -1))
        + int(s36.get("xlrh1_handle_usb_tc_miswire_damage_events", -1))
        + int(s36.get("bnc_tcout_reverse_drive_events", -1))
        + max(0, s36_end_tx)
        + int(faults.p4_stage36_end_or_camset_or_vmc_faults)
    )
    if (
        int(s36.get("nop_count", -1)) != 0
        or int(s36.get("cp_mutation_bytes", -1)) != 0
        or int(s36.get("wbi_mutation_bytes", -1)) != 0
        or int(s36.get("calibration_mutation_bytes", -1)) != 0
        or s36_end_tx != 0
        or s36.get("persistent_emmc_writes_authorized") is not False
        or s36.get("spi_nor_write_authorized") is not False
        or s36.get("el3_payload_transmit_authorized") is not False
        or int(s36.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(s36.get("wf12_00342260_hits", -1)) != 0
        or s36_mut != 0
    ):
        errors.append(f"p4: Stage 36 redlines violated (end_or_camset_or_vmc={s36_mut})")

    total_stages = len(stage_statuses)
    passed_stages = sum(1 for v in stage_statuses.values() if v)
    emmc_corruptions = (
        int(meta_33.get("emmc_corruptions", 0))
        + max(0, int(s34.get("emmc_mutation_bytes", 0)))
        + max(0, int(s35.get("emmc_mutation_bytes", 0)))
        + max(0, int(s36.get("emmc_mutation_bytes", 0)))
    )
    total_wf12_hits = (
        int(meta_33.get("wf12_00342260_hits", 0))
        + max(0, int(s34.get("wf12_00342260_hits", 0)))
        + max(0, int(s35.get("wf12_00342260_hits", 0)))
        + max(0, int(s36.get("wf12_00342260_hits", 0)))
    )

    if total_stages < 36 or passed_stages < 36 or passed_stages != total_stages:
        errors.append(
            f"p4: expected >= 36 VM stages and all passing, got {passed_stages}/{total_stages}"
        )
    if emmc_corruptions != 0:
        errors.append(f"p4: emmc_corruptions={emmc_corruptions} != 0")

    passed = len(errors) == 0
    evidence = dict(m193_p4.evidence)
    evidence.update(
        {
            "stage_count": total_stages,
            "passed_stage_count": passed_stages,
            "stage_statuses": stage_statuses,
            "emmc_corruptions": emmc_corruptions,
            "wf12_00342260_hits": total_wf12_hits,
            "stage34_digest_sha256": s34.get("phase194_audit_digest_sha256"),
            "stage35_digest_sha256": s35.get("phase200_audit_digest_sha256"),
            "stage36_digest_sha256": s36.get("phase202_audit_digest_sha256"),
            "stage36_e_nd_actuator_tx_count": max(0, s36_end_tx),
        }
    )
    pillar = Milestone209PillarResult(
        pillar_id="P4",
        pillar_name="THIRTY_SIX_STAGE_VM_HIL_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {passed_stages}/{total_stages} stages (>=36 required; Stages 34..36 "
            f"NoUVC-DCC1-LUT/FanPWM-Shutter-LUTSplit/BIG6-NoEND-CAMSET-VMC), "
            f"emmc_corruptions={emmc_corruptions}, wf12_hits={total_wf12_hits} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "stage_count": total_stages,
        "passed_count": passed_stages,
        "cp_mutation_bytes": int(meta_33["cp_mutation_bytes"]),
        "bk4_persistent_nvram_writes": int(meta_33["bk4_persistent_nvram_writes"]),
        "wf12_00342260_hits": total_wf12_hits,
        "emmc_corruptions": emmc_corruptions,
        "e_nd_actuator_tx_count": max(0, s36_end_tx),
    }
    return pillar, meta


def _evaluate_pillar_5(
    raw_p136: Mapping[str, Any],
    raw_p143: Mapping[str, Any],
    raw_p154: Mapping[str, Any],
    raw_p186_off: Mapping[str, Any],
    raw_p186_sim: Mapping[str, Any],
    raw_p204_off: Mapping[str, Any],
    raw_p204_sim: Mapping[str, Any],
    faults: RealHwMilestone209FaultInjection,
) -> Tuple[Milestone209PillarResult, Dict[str, Any]]:
    m193_p5, meta_p5_base = _eval_m193_p5(
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        _effective_m193_faults(faults),
    )
    errors: List[str] = list(m193_p5.errors)

    # Phase 204 offline physical-Tier0-receipt block mode
    p204_off_dict = copy.deepcopy(dict(raw_p204_off))
    v204_off = verify_phase204_report(p204_off_dict)
    if (
        not v204_off.valid
        or p204_off_dict.get("go_no_go") != GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        or p204_off_dict.get("hardware_live_attachment_authorized") is not False
        or p204_off_dict.get("all_3_check_groups_passed") is not False
        or int(p204_off_dict.get("physical_usb_packets_emitted", -1)) != 0
        or int(p204_off_dict.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(p204_off_dict.get("e_nd_actuator_tx_count", -1)) != 0
    ):
        errors.append(
            f"p5_p204_off: expected {GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT} "
            f"(got {p204_off_dict.get('go_no_go')}, valid={v204_off.valid}, errs={v204_off.errors})"
        )

    # Phase 204 simulated dry-run B1..B3 preflight mode
    p204_sim_dict = copy.deepcopy(dict(raw_p204_sim))
    if faults.p5_inject_p204_usb_packets_override:
        p204_sim_dict["physical_usb_packets_emitted"] = int(
            p204_sim_dict.get("physical_usb_packets_emitted", 0)
        ) + int(faults.p5_inject_p204_usb_packets_override)

    v204_sim = verify_phase204_report(p204_sim_dict)
    b1 = p204_sim_dict.get("check_group_1_power_cable_harness", {})
    b2 = p204_sim_dict.get("check_group_2_fan_thermal_and_big6", {})
    b3 = p204_sim_dict.get("check_group_3_slot1_lut_camset_vault", {})
    p204_sim_groups = int(p204_sim_dict.get("check_groups_passed", -1))
    p204_sim_pkts = int(p204_sim_dict.get("physical_usb_packets_emitted", -1))
    p204_sim_leaked = int(p204_sim_dict.get("raw_firmware_bytes_leaked", -1))
    p204_h0_h3 = int(p204_sim_dict.get("h0_equals_h3_count", -1))
    p204_end_tx = int(p204_sim_dict.get("e_nd_actuator_tx_count", -1))

    if (
        not v204_sim.valid
        or p204_sim_dict.get("go_no_go") != GO_NO_GO_DRY_RUN_SIMULATED_READY
        or not bool(p204_sim_dict.get("all_3_check_groups_passed"))
        or p204_sim_groups != 3
        or p204_sim_dict.get("hardware_live_attachment_authorized") is not False
        or not bool(b1.get("passed"))
        or not bool(b2.get("passed"))
        or not bool(b3.get("passed"))
        or p204_h0_h3 != 16
        or p204_end_tx != 0
        or p204_sim_pkts != 0
        or p204_sim_leaked != 0
        or p204_sim_dict.get("persistent_emmc_writes_authorized") is not False
        or p204_sim_dict.get("spi_nor_write_authorized") is not False
        or p204_sim_dict.get("el3_payload_transmit_authorized") is not False
    ):
        errors.append(
            f"p5_p204_sim: preflight-bench-cable-fan-slot1 failed "
            f"(go={p204_sim_dict.get('go_no_go')}, groups={p204_sim_groups}/3, "
            f"b1={b1.get('passed')}, b2={b2.get('passed')}, b3={b3.get('passed')}, errs={v204_sim.errors})"
        )

    passed = len(errors) == 0
    evidence = dict(m193_p5.evidence)
    evidence.update(
        {
            "p204_offline_go_no_go": p204_off_dict.get("go_no_go"),
            "p204_offline_groups_passed": p204_off_dict.get("check_groups_passed"),
            "p204_offline_report_verified": bool(v204_off.valid),
            "p204_sim_go_no_go": p204_sim_dict.get("go_no_go"),
            "p204_sim_groups_passed": p204_sim_groups,
            "p204_hardware_live_attachment_authorized": p204_sim_dict.get(
                "hardware_live_attachment_authorized"
            ),
            "p204_h0_equals_h3_count": p204_h0_h3,
            "p204_e_nd_actuator_tx_count": p204_end_tx,
            "p204_sim_usb_packets_emitted": p204_sim_pkts,
            "p204_sim_raw_firmware_bytes_leaked": p204_sim_leaked,
            "p204_sim_report_verified": bool(v204_sim.valid),
            "p204_sim_report_sha256": str(p204_sim_dict.get("report_sha256", "")),
        }
    )
    pillar = Milestone209PillarResult(
        pillar_id="P5",
        pillar_name="CLOSURE_CARD_INSERT_AND_BENCH_CABLE_FAN_SLOT1_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Ph136/143/154 + Ph186(card-insert sim={meta_p5_base['p186_sim_gates_passed']}/4) + "
            f"Ph204(cable-fan-slot1 off={p204_off_dict.get('check_groups_passed')}/3 "
            f"sim={p204_sim_groups}/3 H0==H3={p204_h0_h3}/16 e_nd_tx={p204_end_tx}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_p5_base)
    meta.update(
        {
            "p204_offline_go_no_go": str(p204_off_dict.get("go_no_go", "")),
            "p204_sim_go_no_go": str(p204_sim_dict.get("go_no_go", "")),
            "p204_sim_groups_passed": p204_sim_groups,
            "p204_hardware_live_attachment_authorized": bool(
                p204_sim_dict.get("hardware_live_attachment_authorized", True)
            ),
            "p204_h0_equals_h3_count": p204_h0_h3,
            "p204_e_nd_actuator_tx_count": p204_end_tx,
            "p204_sim_usb_packets_emitted": p204_sim_pkts,
            "p204_sim_raw_firmware_bytes_leaked": p204_sim_leaked,
        }
    )
    return pillar, meta


def _evaluate_pillar_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: RealHwMilestone209FaultInjection,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
    p5_meta: Mapping[str, Any],
) -> Tuple[Milestone209PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    round_sources: Dict[str, str] = {}
    round_schemas: Dict[str, str] = {}
    runs_by_round: Dict[str, int] = {}
    png_sizes_by_asset: Dict[str, int] = {}
    png_sources_by_round: Dict[str, str] = {}

    total_nops = 0
    total_crashes = 0
    total_emmc = 0
    rounds_verified = 0
    total_runs_verified = 0
    pngs_verified = 0
    max_png_bytes = 0

    for spec in ROUND28_TO_40_SPECS:
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

        png_pair = ROUND28_TO_40_PNG_RECEIPTS[spec.round_num]
        for png_idx, png_rel in enumerate(png_pair):
            png_ok, png_size, png_src = _inspect_round_png_receipt(
                png_rel, repo_root=repo_root, use_clean_room=use_clean_room
            )
            if (
                png_idx == 0
                and faults.p6_png_size_override_round_num == spec.round_num
                and faults.p6_png_size_override_bytes is not None
            ):
                png_size = int(faults.p6_png_size_override_bytes)
                png_ok = 0 < png_size < PNG_MAX_SIZE_BYTES
            png_sizes_by_asset[Path(png_rel).name] = png_size
            png_sources_by_round[r_tag] = png_src
            if png_size > max_png_bytes:
                max_png_bytes = png_size
            if png_ok:
                pngs_verified += 1
            else:
                errors.append(
                    f"p6_{r_tag}: PNG receipt invalid or >= {PNG_MAX_SIZE_BYTES}B ({png_rel}, size={png_size})"
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
                rnop = int(robj.get("nop_count", 0))

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

    # Cross-pillar hardware-lock invariants
    if (
        p1_meta.get("persistent_emmc_writes_authorized") is not False
        or p1_meta.get("spi_nor_write_authorized") is not False
        or p1_meta.get("el3_payload_transmit_authorized") is not False
        or p1_meta.get("simulated_ready_for_hardware_attach") is not False
        or int(p1_meta.get("g71_e_nd_actuator_tx_count", -1)) != 0
    ):
        errors.append("p6: P1 hardware-lock or zero e-ND invariant breached")
    if (
        int(p2_meta.get("otp_fuse_touches", -1)) != 0
        or int(p2_meta.get("rpmb_counter_increments", -1)) != 0
        or int(p2_meta.get("passive_tx_bytes_emitted", -1)) != 0
        or int(p2_meta.get("physical_usb_packets_emitted", -1)) != 0
        or int(p2_meta.get("raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append("p6: P2 zero-touch OTP/RPMB/passive-UART/USB-PKT/raw-FW invariant breached")
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
        or int(p4_meta.get("e_nd_actuator_tx_count", -1)) != 0
    ):
        errors.append("p6: P4 CP/BK4/WF-12/eMMC/zero-e-ND invariant breached")
    if (
        int(p5_meta.get("h0_equals_h3_count", -1)) != 16
        or not bool(p5_meta.get("p154_bench_go"))
        or int(p5_meta.get("p186_sim_gates_passed", -1)) != 4
        or p5_meta.get("p186_card_insert_authorized") is not False
        or int(p5_meta.get("p204_sim_groups_passed", -1)) != 3
        or p5_meta.get("p204_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p204_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p204_e_nd_actuator_tx_count", -1)) != 0
        or int(p5_meta.get("p204_sim_usb_packets_emitted", -1)) != 0
        or int(p5_meta.get("p204_sim_raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append(
            "p6: P5 H0==H3 (16/16), Phase 186 card-insert, or Phase 204 cable/fan/slot1 invariant breached"
        )

    passed = (
        len(errors) == 0
        and rounds_verified == len(ROUND28_TO_40_SPECS)
        and total_runs_verified == 39
        and pngs_verified == 26
        and 0 < max_png_bytes < PNG_MAX_SIZE_BYTES
        and total_nops == 0
        and total_crashes == 0
        and total_emmc == 0
    )
    evidence = {
        "round_sources": round_sources,
        "round_schemas": round_schemas,
        "rounds_verified": rounds_verified,
        "expected_rounds": len(ROUND28_TO_40_SPECS),
        "runs_by_round": runs_by_round,
        "total_runs_verified": total_runs_verified,
        "expected_total_runs": 39,
        "png_receipts_verified": pngs_verified,
        "expected_png_receipts": 26,
        "png_max_bytes": max_png_bytes,
        "png_max_ceiling_bytes": PNG_MAX_SIZE_BYTES,
        "png_sizes_by_asset": png_sizes_by_asset,
        "png_sources_by_round": png_sources_by_round,
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
        "milestone175_schema_anchor": MILESTONE175_SCHEMA_VERSION,
        "milestone193_schema_anchor": MILESTONE193_SCHEMA_VERSION,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }
    pillar = Milestone209PillarResult(
        pillar_id="P6",
        pillar_name="REAL_FX3_702_QEMU_ROUNDS_28_TO_40_AND_PNG_RECEIPTS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Live FX3 7.02 QEMU Rounds 28..40={rounds_verified}/13 rounds ({total_runs_verified}/39 runs, "
            f"PNGs={pngs_verified}/26 max={max_png_bytes}B < 28KiB), "
            f"nop={total_nops}, crashes={total_crashes}, emmc={total_emmc} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "qemu_rounds_verified": rounds_verified,
        "qemu_runs_verified": total_runs_verified,
        "qemu_png_receipts_verified": pngs_verified,
        "qemu_png_max_bytes": max_png_bytes,
        "qemu_round_runs_by_round": runs_by_round,
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
    }
    return pillar, meta


# ---------------------------------------------------------------------------
# Parallel Collector, Builder & Fail-Closed Verifier
# ---------------------------------------------------------------------------


def _collect_parallel_milestone209_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: RealHwMilestone209FaultInjection,
) -> Tuple[
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
]:
    m193_f = _effective_m193_faults(faults)
    gate_fault_dict = _fault_to_72gate_worker_dict(faults)
    p154_sim_ready = not m193_f.p5_inject_p154_no_go_fault
    p186_fault_dict = {
        "inject_appledouble_fault": bool(m193_f.p5_inject_p186_appledouble_fault),
        "inject_h0_h3_drift": bool(m193_f.p5_inject_p186_h0_h3_drift),
        "inject_fw_below_204": bool(m193_f.p5_inject_p186_fw_below_204),
        "inject_single_device_collision": bool(m193_f.p5_inject_p186_single_device_collision),
    }
    p204_fault_dict = {
        "fan_auto1": bool(faults.p5_inject_p204_fan_auto1_fault),
        "always_off": bool(faults.p5_inject_p204_always_off_fault),
        "end_tx": bool(faults.p5_inject_p204_end_tx_fault),
        "camset_slot2": bool(faults.p5_inject_p204_camset_slot2_fault),
        "vmc_xlrh1_port": bool(faults.p5_inject_p204_vmc_xlrh1_port_fault),
        "h0_h3_drift": bool(faults.p5_inject_p204_h0_h3_drift),
    }

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
        ("realhw_hdmi_braw_wpa3", "realhw_emount_info3d"),
        ("realhw_fx3a_xlrh1", "realhw_nouvc_dcc1_lut"),
        ("realhw_fan_shutter_lut601_702", "realhw_big6_camset_vmcbncm1"),
    )

    eff_p2_fault = faults.p2_fault_inject_pillar or m193_f.p2_fault_inject_pillar

    try:
        ctx = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=24, mp_context=ctx) as ex:
            fut_vm = ex.submit(_worker_pillar_4, use_clean_room)
            fut_p136 = ex.submit(_worker_phase136, use_clean_room)
            fut_28p = ex.submit(_worker_recovery_28pillar, (use_clean_room, eff_p2_fault))
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
            fut_204 = ex.submit(
                _worker_phase204,
                (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p204_fault_dict),
            )
            fut_3 = [
                ex.submit(_worker_pillar_3_batch_209, (batch, use_clean_room))
                for batch in p3_batches
            ]
            fut_1_off = ex.submit(
                _worker_72gate_single, (str(repo_root), use_clean_room, False, gate_fault_dict)
            )
            fut_1_sim = ex.submit(
                _worker_72gate_single, (str(repo_root), use_clean_room, True, gate_fault_dict)
            )

            raw_1_off = fut_1_off.result()
            raw_1_sim = fut_1_sim.result()
            raw_28p = fut_28p.result()
            auditors: Dict[str, Dict[str, Any]] = {}
            for fg in fut_3:
                auditors.update(fg.result())
            raw_vm = fut_vm.result()
            raw_p136 = fut_p136.result()
            raw_p143, raw_p154, raw_p186_off, raw_p186_sim = fut_143_154_186.result()
            raw_p204_off, raw_p204_sim = fut_204.result()
            return (
                raw_1_off,
                raw_1_sim,
                raw_28p,
                auditors,
                raw_vm,
                raw_p136,
                raw_p143,
                raw_p154,
                raw_p186_off,
                raw_p186_sim,
                raw_p204_off,
                raw_p204_sim,
            )
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1_off = _worker_72gate_single((str(repo_root), use_clean_room, False, gate_fault_dict))
    raw_1_sim = _worker_72gate_single((str(repo_root), use_clean_room, True, gate_fault_dict))
    raw_28p = _worker_recovery_28pillar((use_clean_room, eff_p2_fault))
    auditors = {}
    for batch in p3_batches:
        auditors.update(_worker_pillar_3_batch_209((batch, use_clean_room)))
    raw_vm = _worker_pillar_4(use_clean_room)
    raw_p136 = _worker_phase136(use_clean_room)
    raw_p143, raw_p154, raw_p186_off, raw_p186_sim = _worker_phase143_154_186(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p154_sim_ready, p186_fault_dict)
    )
    raw_p204_off, raw_p204_sim = _worker_phase204(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p204_fault_dict)
    )
    return (
        raw_1_off,
        raw_1_sim,
        raw_28p,
        auditors,
        raw_vm,
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
    )


def build_realhw_milestone209_master_gate_report(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[RealHwMilestone209FaultInjection] = None,
) -> RealHwMilestone209MasterGateReport:
    """Build & evaluate the Grand Milestone Phase 209 6-Pillar Real-Hardware Pre-Bench Master Gate."""
    use_clean_room = (
        _is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    )
    active_faults = faults or RealHwMilestone209FaultInjection()

    (
        raw_1_off,
        raw_1_sim,
        raw_28p,
        auditors,
        raw_vm,
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
    ) = _collect_parallel_milestone209_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )

    p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
    p2, meta_2 = _evaluate_pillar_2(raw_28p, active_faults)
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

    pillars: Tuple[Milestone209PillarResult, ...] = (p1, p2, p3, p4, p5, p6)
    passed_count = sum(1 for p in pillars if p.passed)
    failed_ids = tuple(p.pillar_id for p in pillars if not p.passed)
    all_errors: List[str] = []
    for p in pillars:
        all_errors.extend(p.errors)

    all_ready = passed_count == len(pillars) and len(all_errors) == 0
    mode_str = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"
    total_raw_leaked = (
        int(meta_2["raw_firmware_bytes_leaked"])
        + int(meta_3["raw_firmware_bytes_leaked"])
        + int(meta_5["p186_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p204_sim_raw_firmware_bytes_leaked"])
    )
    total_usb_pkts = (
        int(meta_2["physical_usb_packets_emitted"])
        + int(meta_5["p186_sim_usb_packets_emitted"])
        + int(meta_5["p204_sim_usb_packets_emitted"])
    )
    total_end_tx = (
        max(0, int(p1.evidence["g71_e_nd_actuator_tx_count"]))
        + int(meta_3["e_nd_actuator_tx_count"])
        + int(meta_4["e_nd_actuator_tx_count"])
        + max(0, int(meta_5["p204_e_nd_actuator_tx_count"]))
    )

    payload_no_sha: Dict[str, Any] = {
        "schema_version": REALHW_MILESTONE209_SCHEMA,
        "phase_version": PHASE_209_VERSION,
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
        "physical_usb_packets_emitted": total_usb_pkts,
        "raw_firmware_bytes_leaked": total_raw_leaked,
        "e_nd_actuator_tx_count": total_end_tx,
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
        "gate72_total_gates": raw_1_sim["total_gates"],
        "gate72_offline_verified": raw_1_off["verified_gates"],
        "gate72_simulated_verified": raw_1_sim["verified_gates"],
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
        "qemu_rounds_verified": meta_6["qemu_rounds_verified"],
        "qemu_runs_verified": meta_6["qemu_runs_verified"],
        "qemu_png_receipts_verified": meta_6["qemu_png_receipts_verified"],
        "qemu_png_max_bytes": meta_6["qemu_png_max_bytes"],
        "qemu_round_runs_by_round": meta_6["qemu_round_runs_by_round"],
        "qemu_real_kernel_nop_count": meta_6["qemu_real_kernel_nop_count"],
        "qemu_real_kernel_crashes": meta_6["qemu_real_kernel_crashes"],
        "qemu_real_kernel_emmc_writes": meta_6["qemu_real_kernel_emmc_writes"],
        "errors": tuple(all_errors),
    }
    digest = compute_milestone209_sha256(payload_no_sha)

    return RealHwMilestone209MasterGateReport(
        schema_version=REALHW_MILESTONE209_SCHEMA,
        phase_version=PHASE_209_VERSION,
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
        physical_usb_packets_emitted=total_usb_pkts,
        raw_firmware_bytes_leaked=total_raw_leaked,
        e_nd_actuator_tx_count=total_end_tx,
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
        gate72_total_gates=raw_1_sim["total_gates"],
        gate72_offline_verified=raw_1_off["verified_gates"],
        gate72_simulated_verified=raw_1_sim["verified_gates"],
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
        p186_offline_go_no_go=meta_5["p186_offline_go_no_go"],
        p186_sim_go_no_go=meta_5["p186_sim_go_no_go"],
        p186_sim_gates_passed=meta_5["p186_sim_gates_passed"],
        p186_card_insert_authorized=meta_5["p186_card_insert_authorized"],
        p186_h0_equals_h3_count=meta_5["p186_h0_equals_h3_count"],
        p204_offline_go_no_go=meta_5["p204_offline_go_no_go"],
        p204_sim_go_no_go=meta_5["p204_sim_go_no_go"],
        p204_sim_groups_passed=meta_5["p204_sim_groups_passed"],
        p204_hardware_live_attachment_authorized=meta_5[
            "p204_hardware_live_attachment_authorized"
        ],
        p204_h0_equals_h3_count=meta_5["p204_h0_equals_h3_count"],
        p204_e_nd_actuator_tx_count=meta_5["p204_e_nd_actuator_tx_count"],
        qemu_rounds_verified=meta_6["qemu_rounds_verified"],
        qemu_runs_verified=meta_6["qemu_runs_verified"],
        qemu_png_receipts_verified=meta_6["qemu_png_receipts_verified"],
        qemu_png_max_bytes=meta_6["qemu_png_max_bytes"],
        qemu_round_runs_by_round=meta_6["qemu_round_runs_by_round"],
        qemu_real_kernel_nop_count=meta_6["qemu_real_kernel_nop_count"],
        qemu_real_kernel_crashes=meta_6["qemu_real_kernel_crashes"],
        qemu_real_kernel_emmc_writes=meta_6["qemu_real_kernel_emmc_writes"],
        errors=tuple(all_errors),
        milestone209_sha256=digest,
    )


evaluate_milestone209_master_gate = build_realhw_milestone209_master_gate_report


def verify_realhw_milestone209_master_gate(
    report: object,
) -> RealHwMilestone209VerifyResult:
    """Fail-closed verifier for a Grand Milestone Phase 209 Real-Hardware Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, RealHwMilestone209MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return RealHwMilestone209VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone209_sha256="",
            observed_milestone209_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or RealHwMilestone209MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = payload.get("schema_version") == REALHW_MILESTONE209_SCHEMA
    if not schema_ok:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r}")

    expected_sha = compute_milestone209_sha256(payload)
    observed_sha = str(payload.get("milestone209_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(
            f"milestone209_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}"
        )

    redlines_ok = (
        payload.get("o_rdonly_enforced") is True
        and payload.get("persistent_emmc_writes_authorized") is False
        and payload.get("persistent_write_release") is False
        and payload.get("spi_nor_write_authorized") is False
        and payload.get("el3_payload_transmit_authorized") is False
        and payload.get("isp_write_authorized") is False
        and payload.get("hardware_live_attachment_authorized") is False
        and payload.get("physical_usb_packets_emitted") == 0
        and payload.get("raw_firmware_bytes_leaked") == 0
        and payload.get("e_nd_actuator_tx_count") == 0
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
        and payload.get("p186_card_insert_authorized") is False
        and payload.get("p204_hardware_live_attachment_authorized") is False
        and payload.get("p204_e_nd_actuator_tx_count") == 0
    )
    if not redlines_ok:
        errors.append(
            "hard-locked zero-write / zero-SPI-NOR / zero-EL3 / zero-USB-TX / zero-leak / zero-e-ND / zero-attach redlines breached"
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

    counts_ok = (
        int(payload.get("gate72_total_gates", -1)) >= 72
        and int(payload.get("gate72_offline_verified", -1)) >= 69
        and int(payload.get("gate72_simulated_verified", -1)) >= 72
        and int(payload.get("recovery_pillar_count", -1)) >= 28
        and int(payload.get("recovery_pillars_passed", -1))
        == int(payload.get("recovery_pillar_count", -2))
        and int(payload.get("firmware_lab_auditor_count", -1)) >= 42
        and int(payload.get("firmware_lab_auditors_passed", -1))
        == int(payload.get("firmware_lab_auditor_count", -2))
        and int(payload.get("vm_coemulation_stage_count", -1)) >= 36
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
        and payload.get("p186_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p186_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p186_sim_gates_passed", -1)) == 4
        and int(payload.get("p186_h0_equals_h3_count", -1)) == 16
        and payload.get("p204_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p204_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p204_sim_groups_passed", -1)) == 3
        and int(payload.get("p204_h0_equals_h3_count", -1)) == 16
        and int(payload.get("qemu_rounds_verified", -1)) == 13
        and int(payload.get("qemu_runs_verified", -1)) == 39
        and int(payload.get("qemu_png_receipts_verified", -1)) == 26
        and 0 < int(payload.get("qemu_png_max_bytes", -1)) < PNG_MAX_SIZE_BYTES
        and int(payload.get("qemu_real_kernel_nop_count", -1)) == 0
        and int(payload.get("qemu_real_kernel_crashes", -1)) == 0
        and int(payload.get("qemu_real_kernel_emmc_writes", -1)) == 0
    )
    if not counts_ok:
        errors.append("milestone209 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append(
            "all_pillars_milestone_ready / status is not MILESTONE_209_PREBENCH_MASTER_VERIFIED"
        )

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 209 payload")

    valid = bool(
        schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0
    )
    return RealHwMilestone209VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone209_sha256=expected_sha,
        observed_milestone209_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


def render_milestone209_markdown(report: RealHwMilestone209MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 209 Master Gate."""
    lines = [
        f"# Grand Milestone Phase 209 — Real-Hardware `ILME-FX3 Ver. 7.02` Pre-Bench Master Gate (`{report.schema_version}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone209_sha256}`",
        "",
        "## Hard-Locked Safety Redlines / 硬锁定安全红线",
        f"- `persistent_emmc_writes_authorized = {report.persistent_emmc_writes_authorized}`, "
        f"`spi_nor_write_authorized = {report.spi_nor_write_authorized}`, "
        f"`el3_payload_transmit_authorized = {report.el3_payload_transmit_authorized}`",
        f"- `isp_write_authorized = {report.isp_write_authorized}`, "
        f"`persistent_write_release = {report.persistent_write_release}`, "
        f"`hardware_live_attachment_authorized = {report.hardware_live_attachment_authorized}`",
        f"- `physical_usb_packets_emitted = {report.physical_usb_packets_emitted}`, "
        f"`raw_firmware_bytes_leaked = {report.raw_firmware_bytes_leaked}`, "
        f"`e_nd_actuator_tx_count = {report.e_nd_actuator_tx_count}`, "
        f"`otp_fuse_touches = {report.otp_fuse_touches}`, "
        f"`rpmb_counter_increments = {report.rpmb_counter_increments}`",
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
            "## Key Grand Milestone Phase 209 Metrics / 实机台架前总闭环核心指标",
            f"- 72-Gate Preflight (`G01..G72`): offline=`{report.gate72_offline_verified}/{report.gate72_total_gates}` (`G10..G12` locked), simulated=`{report.gate72_simulated_verified}/{report.gate72_total_gates}`",
            f"- 28-Pillar Recovery & Vault Master (`Ph47..205`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`>=28` required; `H0 == H3`)",
            f"- 42 Firmware-Lab Auditors (`Ph1..203`): `{report.firmware_lab_auditors_passed}/{report.firmware_lab_auditor_count}` (`>=42` required; `e_nd_actuator_tx_count={report.e_nd_actuator_tx_count}`, `raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`)",
            f"- 36-Stage VM Co-Emulation (`Ph33..202`): `{report.vm_coemulation_stages_passed}/{report.vm_coemulation_stage_count}` (`>=36` required; `emmc_corruptions={report.vm_emmc_corruptions}`, `wf12_hits={report.vm_wf12_00342260_hits}`)",
            f"- Pre-Bench Card-Insert & Cable/Fan/Slot-1 (`Ph186 + Ph204`): `Phase186 sim={report.p186_sim_gates_passed}/4 ({report.p186_sim_go_no_go})`, `Phase204 off={report.p204_offline_go_no_go}`, `Phase204 sim={report.p204_sim_groups_passed}/3 ({report.p204_sim_go_no_go}, H0==H3={report.p204_h0_equals_h3_count}/16)`",
            f"- Live FX3 `7.02` (`4.9.337-scel+`) QEMU Receipts (`Rounds 28..40`): `{report.qemu_rounds_verified}/13` rounds (`{report.qemu_runs_verified}/39` sub-experiments, `PNGs={report.qemu_png_receipts_verified}/26` max=`{report.qemu_png_max_bytes}B < 28KiB`), `nop={report.qemu_real_kernel_nop_count}`, `crashes={report.qemu_real_kernel_crashes}`, `emmc_writes={report.qemu_real_kernel_emmc_writes}`",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "CALIBRATION_MUTATION_BYTES",
    "CP_MUTATION_BYTES",
    "DEFAULT_REPO_ROOT",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "E_ND_ACTUATOR_TX_COUNT",
    "FIRMWARE_LAB_42_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "ISP_WRITE_AUTHORIZED",
    "MILESTONE209_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "P8_CP_MUTATION_FORBIDDEN",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_209_VERSION",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "PNG_MAGIC_BYTES",
    "PNG_MAX_SIZE_BYTES",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_MILESTONE209_SCHEMA",
    "RECOVERY_28_PILLAR_IDS",
    "ROUND28_TO_40_PNG_RECEIPTS",
    "ROUND28_TO_40_SPECS",
    "ROUND38_EXPECTED_SCHEMA",
    "ROUND38_SUMMARY_RELPATH",
    "ROUND39_EXPECTED_SCHEMA",
    "ROUND39_SUMMARY_RELPATH",
    "ROUND40_EXPECTED_SCHEMA",
    "ROUND40_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "SCHEMA_VERSION",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "VM_COEMULATION_36_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone209PillarResult",
    "RealHwMilestone209FaultInjection",
    "RealHwMilestone209MasterGateReport",
    "RealHwMilestone209VerifyResult",
    "build_realhw_milestone209_master_gate_report",
    "compute_milestone209_sha256",
    "evaluate_milestone209_master_gate",
    "render_milestone209_markdown",
    "verify_realhw_milestone209_master_gate",
]
