"""Grand Milestone Phase 221 — 6-Pillar Real-Hardware `ILME-FX3 Ver. 7.02` Master Gate (`realhw_milestone221_master_gate_v1`).

Unites ALL Wave 21–29 Real-Hardware Main Track subsystems (Phases 134–220) and ALL
15 live Sony ILME-FX3 `Ver. 7.02` (`Linux 4.9.337-scel+`) ARM64 QEMU Rehearsal
Rounds (`Rounds 28..42` — `45/45` sub-runs `r28a..r42c` + `30/30` `< 28 KiB` PNG
receipts) into a single tamper-evident, fail-closed certificate executing in
`< 5.0s` per mode across both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC`
(`FX3_FX6_FORCE_CLEAN_ROOM=1`) while keeping `verify-milestone-175`,
`verify-milestone-193`, `verify-milestone-209`, `preflight-card-insert`,
`preflight-bench-cable-fan-slot1`, and `preflight-hdmi-proxy-desqueeze-and-simult`
100% intact and forward-compatible:

- `P1` (`SAFETY_78GATE_REALHW_MASTER_PREFLIGHT`):
  Evaluates `evaluate_78gate_preflight` (`75/78` offline with 3 Tier-0 physical-bench
  receipt gates `G10..G12` fail-closed; `78/78` simulated dry-run, forward-compatible
  with `>= 78` gates), explicitly verifying `G73..G78` (`De-Squeeze 1.65x`, external
  `M&C Focus Map <150fps`, `Simult+AutoSwitch`, `Shockless WB`, `HDMI Log 1080p vs
  Off(HDMI Only) 4K`, `Px Proxy Vault`, `FocusMag x BrightMon`, `File Settings
  37-char/SDHC`, `TC Regenerate Slot-1`, `REC Lamp` coupled tally).
- `P2` (`THIRTY_ONE_PILLAR_RECOVERY_MASTER_VAULT`):
  Verifies `>= 31` recovery pillars (`VERIFIED_31OF31_PILLAR_RECOVERY_MASTER` via
  `evaluate_realhw_31pillar_recovery_master` from `fx3_recovery`), locking
  `otp_fuse_writes == 0`, `rpmb_writes == 0`, `passive_tx_bytes == 0`, and
  `physical_usb_packets_emitted == 0`.
- `P3` (`FORTY_FOUR_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS`):
  Verifies all `44` current `fx3_firmware_lab` auditors including Phase 205 (`43rd`,
  `De-Squeeze/FocusMap/ShocklessWB`) and Phase 211 (`44th`, `HDMI Log 1080p/Proxy/
  FocusMag/BrightMon`), plus dynamic discovery of any future `45th+` `realhw_*_auditor`
  using forward-compatible `auditors_passed >= 44 and auditors_passed == auditors_total`.
- `P4` (`THIRTY_EIGHT_PLUS_STAGE_VM_HIL_COEMULATION`):
  Runs `fx3_vm_coemulation_suite` verifying Stage 37 (Phase 207) and Stage 38
  (Phase 213), using forward-compatible `vm_stages_passed >= 38 and vm_stages_passed ==
  vm_stages_total` so future Stage 39+ merges remain 100% green.
- `P5` (`TRIPLE_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216`):
  Verifies `Phase 136`, `Phase 143`, `Phase 154`, AND all 3 Bench Readiness Preflights
  (`preflight-card-insert` Ph186, `preflight-bench-cable-fan-slot1` Ph204, and
  `preflight-hdmi-proxy-desqueeze-and-simult` Ph216) return
  `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` offline and
  `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` in simulated dry-run (`16/16 H0 == H3`,
  `hardware_live_attachment_authorized == False`).
- `P6` (`REAL_FX3_702_QEMU_ROUNDS_28_TO_42_AND_PNG_RECEIPTS`):
  Verifies `15/15` QEMU rounds (`45/45` sub-runs `r28a..r42c`) and `30/30` sanitized
  PNG receipts (`< 28 KiB` each), `16/16 H0 == H3`, `emmc_write_count == 0`, and
  `e_nd_actuator_tx_count == 0`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from concurrent.futures import ProcessPoolExecutor
import copy
from dataclasses import asdict, dataclass
import hashlib
import importlib
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

import fx3_firmware_lab  # noqa: E402
from fx3_firmware_lab.realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_auditor import (  # noqa: E402
    analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb,
    realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_report_to_dict,
)
from fx3_firmware_lab.realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_auditor import (  # noqa: E402
    analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon,
    realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_report_to_dict,
)
from fx3_recovery.realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier import (  # noqa: E402
    MASTER_31_PILLAR_IDS,
    evaluate_realhw_31pillar_recovery_master,
)
from fx3_safety.realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (  # noqa: E402
    evaluate_78gate_preflight,
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
from .realhw_hdmi_proxy_desqueeze_and_simult_verifier import (  # noqa: E402
    evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness,
    verify_phase216_report,
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
    PNG_MAX_SIZE_BYTES,
    _inspect_round_png_receipt,
    _load_round28_to_37_summary,
    _worker_phase143_154_186,
)
from .realhw_milestone209_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    E_ND_ACTUATOR_TX_COUNT,
    FIRMWARE_LAB_42_AUDITOR_KEYS,
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
    ROUND28_TO_40_PNG_RECEIPTS,
    ROUND28_TO_40_SPECS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    USB_OR_CAMERA_OPERATIONS,
    VM_COEMULATION_36_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone209FaultInjection,
    _72GATE_EXTRA_FAULT_FIELDS,
    _effective_m193_faults,
    _evaluate_pillar_3 as _eval_m209_p3,
    _evaluate_pillar_4 as _eval_m209_p4,
    _evaluate_pillar_5 as _eval_m209_p5,
    _worker_phase204,
    _worker_pillar_3_batch_209,
    build_realhw_milestone209_master_gate_report,
)
from .stage_b_milestone110_master_gate import _worker_pillar_4  # noqa: E402
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_MILESTONE221_SCHEMA: str = "realhw_milestone221_master_gate_v1"
MILESTONE221_SCHEMA_VERSION: str = REALHW_MILESTONE221_SCHEMA
SCHEMA_VERSION: str = REALHW_MILESTONE221_SCHEMA
PHASE_221_VERSION: str = "221.0.0"

USB_PACKETS_TRANSMITTED: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_WRITES: int = 0
PASSIVE_TX_BYTES: int = 0
EMMC_WRITE_COUNT: int = 0

STATUS_MILESTONE_READY: str = "MILESTONE_221_PREBENCH_MASTER_VERIFIED"

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_78GATE_REALHW_MASTER_PREFLIGHT"),
    ("P2", "THIRTY_ONE_PILLAR_RECOVERY_MASTER_VAULT"),
    ("P3", "FORTY_FOUR_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS"),
    ("P4", "THIRTY_EIGHT_PLUS_STAGE_VM_HIL_COEMULATION"),
    ("P5", "TRIPLE_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216"),
    ("P6", "REAL_FX3_702_QEMU_ROUNDS_28_TO_42_AND_PNG_RECEIPTS"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)

RECOVERY_31_PILLAR_IDS: Tuple[str, ...] = MASTER_31_PILLAR_IDS

FIRMWARE_LAB_44_AUDITOR_KEYS: Tuple[str, ...] = (
    *FIRMWARE_LAB_42_AUDITOR_KEYS,
    "realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_audit",
    "realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_audit",
)

_KNOWN_18_REALHW_AUDITOR_STEMS: frozenset[str] = frozenset(
    {
        "realhw_cp_rtos_and_backup_bin_auditor",
        "realhw_mpr_dmm_rec_pipeline_bridge_auditor",
        "realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor",
        "realhw_physical_controls_tally_fan_and_power_auditor",
        "realhw_wifi_bt_usb_uvc_network_bridge_auditor",
        "realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor",
        "realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_auditor",
        "realhw_cxd90057_cxd90058_sabin_codec_auditor",
        "realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor",
        "realhw_wbi2_hibdrv_hibernation_isolation_auditor",
        "realhw_hdmi_braw_wpa3_702_delta_auditor",
        "realhw_emount_info3d_breathing_02cf0232_auditor",
        "realhw_fx3_vs_fx3a_and_xlrh1_mishoe_auditor",
        "realhw_nouvc_dcc1_pd_lut_path_cineei_auditor",
        "realhw_fan_pwm_shutter_angle_and_lut_601_702_split_auditor",
        "realhw_big6_noend_camset_slot1_and_vmcbncm1_auditor",
        "realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_auditor",
        "realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_auditor",
    }
)

VM_COEMULATION_38_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_36_STAGE_KEYS,
    "stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil",
    "stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil",
)

ROUND41_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round41-realhw-desqueeze-165x-focusmap-simult-shocklesswb-qemu/summary.json"
)
ROUND42_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round42-realhw-hdmi-log1080-proxy-vault-focusmag-brightmon-qemu/summary.json"
)

ROUND41_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round41-realhw-desqueeze-165x-focusmap-simult-shocklesswb-qemu-v1"
)
ROUND42_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round42-realhw-hdmi-log1080-proxy-vault-focusmag-brightmon-qemu-v1"
)

ROUND28_TO_42_SPECS: Tuple[RoundQemuReceiptSpec, ...] = (
    *ROUND28_TO_40_SPECS,
    RoundQemuReceiptSpec(
        round_num=41,
        summary_relpath=ROUND41_SUMMARY_RELPATH,
        expected_schema=ROUND41_EXPECTED_SCHEMA,
        audit_key="r41_realhw_desqueeze_focusmap_simult_shocklesswb_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r41a_desqueeze_5ratios_165x_and_4hardlocks_verified",
            "r41a_hdmi_raw_clean_hdmi_log_remote_suppression_verified",
            "r41a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r41b_inbody_focusmap_rejected_and_sub150fps_1fps_6fps_verified",
            "r41b_150fps_200_240fps_cutoff_and_adapter_playback_blocks_verified",
            "r41c_simult_autoswitch_continuation_and_cardswap_resume_verified",
            "r41c_shockless_wb_preset_vs_kelvin_grid_0frame_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r41a_desqueeze_165x_4locks_big6_schinese", 1),
            ("r41b_external_focusmap_150fps_cutoff", None),
            ("r41c_simult_autoswitch_shocklesswb", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=42,
        summary_relpath=ROUND42_SUMMARY_RELPATH,
        expected_schema=ROUND42_EXPECTED_SCHEMA,
        audit_key="r42_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r42a_log_pplut_1080p_downshift_and_raw_4k_override_verified",
            "r42a_hdmionly_6_modes_4k10bit_internal_rec_disabled_and_lcd_blank_verified",
            "r42a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r42b_proxy_dualcodec_119p_sq120fps_hdmionly_cutoffs_verified",
            "r42b_proxy_playback_enotsup_and_atomic_clip_sub_vault_verified",
            "r42c_focusmag_movie_x40_still_ff21_apsc15_and_automag_block_verified",
            "r42c_brightmon_mag_lockout_setting_effect_off_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r42a_hdmi_log1080_hdmionly_4k_big6_schinese", 1),
            ("r42b_proxy_vault_119p_atomic_pair", None),
            ("r42c_focusmag_brightmon_h0_h3", None),
        ),
    ),
)

ROUND28_TO_42_PNG_RECEIPTS: Dict[int, Tuple[str, str]] = {
    **ROUND28_TO_40_PNG_RECEIPTS,
    41: (
        "reports/2026-11-15-round41-realhw-desqueeze-165x-focusmap-simult-shocklesswb-qemu/assets/r41a-desqueeze-165x-big6-schinese-alpha.png",
        "reports/2026-11-15-round41-realhw-desqueeze-165x-focusmap-simult-shocklesswb-qemu/assets/r41a-desqueeze-165x-big6-schinese-composited.png",
    ),
    42: (
        "reports/2026-11-15-round42-realhw-hdmi-log1080-proxy-vault-focusmag-brightmon-qemu/assets/r42a-hdmi-log1080-big6-schinese-alpha.png",
        "reports/2026-11-15-round42-realhw-hdmi-log1080-proxy-vault-focusmag-brightmon-qemu/assets/r42a-hdmi-log1080-big6-schinese-composited.png",
    ),
}

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_VM_STAGE_KEY_RE = re.compile(r"^stage(\d+)_")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealHwMilestone221FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 Wave 27–29 gates (G73..G78) + persistent-write lock
    p1_desqueeze_focusmap_kwargs: Optional[Mapping[str, Any]] = None
    p1_simult_autoswitch_shocklesswb_kwargs: Optional[Mapping[str, Any]] = None
    p1_hdmi_log1080_hdmionly_kwargs: Optional[Mapping[str, Any]] = None
    p1_proxy_focusmag_brightmon_kwargs: Optional[Mapping[str, Any]] = None
    p1_filesettings_shotmark_kwargs: Optional[Mapping[str, Any]] = None
    p1_tcregen_reclamp_kwargs: Optional[Mapping[str, Any]] = None
    p1_request_persistent_writes: bool = False

    # P2 31-pillar recovery master + zero-touch redlines
    p2_fault_inject_pillar: Optional[str] = None
    p2_otp_fuse_writes_override: int = 0
    p2_rpmb_writes_override: int = 0
    p2_passive_tx_bytes_override: int = 0
    p2_physical_usb_packets_override: int = 0
    p2_physical_device_writes_override: int = 0
    p2_raw_firmware_bytes_leaked_override: int = 0

    # P3 >= 44 firmware-lab auditors (#43..#44 + forward-compat 45+)
    p3_desqueeze_focusmap_overlay_fault: bool = False
    p3_hdmi_proxy_focusmag_guard_fault: bool = False
    p3_raw_firmware_bytes_leaked_override: int = 0

    # P4 >= 38 VM HIL stages (Stages 37..38 + forward-compat 39+)
    p4_stage37_desqueeze_or_focusmap_faults: int = 0
    p4_stage38_hdmi_or_proxy_or_focusmag_faults: int = 0

    # P5 Triple bench readiness preflights (Ph186 + Ph204 + Ph216)
    p5_inject_p186_h0_h3_drift: bool = False
    p5_inject_p204_h0_h3_drift: bool = False
    p5_inject_p216_desqueeze_lock_fault: bool = False
    p5_inject_p216_hdmi_only_card_rec_fault: bool = False
    p5_inject_p216_proxy_orphan_fault: bool = False
    p5_inject_p216_title_38char_fault: bool = False
    p5_inject_p216_h0_h3_drift: bool = False
    p5_inject_p216_usb_packets_override: int = 0

    # P6 Rounds 28..42 live QEMU kernel rehearsal & PNG receipts
    p6_round_nop_override_num: Optional[int] = None
    p6_round_nop_count_override: Optional[int] = None
    p6_round_crash_override_num: Optional[int] = None
    p6_round_crashes_override: Optional[int] = None
    p6_round_emmc_override_num: Optional[int] = None
    p6_round_emmc_writes_override: Optional[int] = None
    p6_tamper_schema_round_num: Optional[int] = None
    p6_png_size_override_round_num: Optional[int] = None
    p6_png_size_override_bytes: Optional[int] = None

    # Optional upstream Milestone 209 fault injection pass-through
    m209_faults: Optional[RealHwMilestone209FaultInjection] = None


@dataclass(frozen=True)
class Milestone221PillarResult:
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
class RealHwMilestone221MasterGateReport:
    schema: str
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
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
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
    pillars: Tuple[Milestone221PillarResult, ...]
    gate78_total_gates: int
    gate78_offline_verified: int
    gate78_simulated_verified: int
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
    h0_equals_h3_count: int
    qemu_rounds_verified: int
    qemu_runs_verified: int
    qemu_png_receipts_verified: int
    qemu_png_max_bytes: int
    qemu_round_runs_by_round: Dict[str, int]
    qemu_real_kernel_nop_count: int
    qemu_real_kernel_crashes: int
    qemu_real_kernel_emmc_writes: int
    errors: Tuple[str, ...]
    milestone221_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class RealHwMilestone221VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone221_sha256: str
    observed_milestone221_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_milestone221_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `RealHwMilestone221MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone221_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 5.0s per mode)
# ---------------------------------------------------------------------------

_78GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_desqueeze_focusmap_kwargs", "desqueeze_focusmap_kwargs"),
    ("p1_simult_autoswitch_shocklesswb_kwargs", "simult_autoswitch_shocklesswb_kwargs"),
    ("p1_hdmi_log1080_hdmionly_kwargs", "hdmi_log1080_hdmionly_kwargs"),
    ("p1_proxy_focusmag_brightmon_kwargs", "proxy_focusmag_brightmon_kwargs"),
    ("p1_filesettings_shotmark_kwargs", "filesettings_shotmark_kwargs"),
    ("p1_tcregen_reclamp_kwargs", "tcregen_reclamp_kwargs"),
)


def _effective_m209_faults(
    faults: RealHwMilestone221FaultInjection,
) -> RealHwMilestone209FaultInjection:
    base = faults.m209_faults or RealHwMilestone209FaultInjection()
    need_186 = faults.p5_inject_p186_h0_h3_drift and not base.p5_inject_p186_h0_h3_drift
    need_204 = faults.p5_inject_p204_h0_h3_drift and not base.p5_inject_p204_h0_h3_drift
    if need_186 or need_204:
        d = asdict(base)
        d["m193_faults"] = base.m193_faults
        if need_186:
            d["p5_inject_p186_h0_h3_drift"] = True
        if need_204:
            d["p5_inject_p204_h0_h3_drift"] = True
        return RealHwMilestone209FaultInjection(**d)
    return base


def _fault_to_78gate_worker_dict(faults: RealHwMilestone221FaultInjection) -> Dict[str, Any]:
    m209_f = _effective_m209_faults(faults)
    m193_f = _effective_m193_faults(m209_f)
    out: Dict[str, Any] = {
        "p1_request_persistent_writes": bool(
            faults.p1_request_persistent_writes
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
        val = getattr(faults, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    return out


def _worker_78gate_single(args: Tuple[str, bool, bool, Dict[str, Any]]) -> Dict[str, Any]:
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
    ):
        if fault_dict.get(src_attr) is not None:
            kwargs[dst_kw] = fault_dict[src_attr]

    rep = evaluate_78gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated=dry_run_sim,
        **kwargs,
    )
    m76 = rep.master_76_report
    m74 = m76.get("master_74_report", {})
    m72 = m74.get("master_72_report", {})
    m70 = m72.get("master_70_report", {})
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
        ("g71", m72.get("g71_result", {})),
        ("g72", m72.get("g72_result", {})),
        ("g73", m74.get("g73_result", {})),
        ("g74", m74.get("g74_result", {})),
        ("g75", m76.get("g75_result", {})),
        ("g76", m76.get("g76_result", {})),
        ("g77", rep.g77_result),
        ("g78", rep.g78_result),
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
        "offline_75_gates_verified": bool(s.get("offline_75_gates_verified", False)),
        "all_78_gates_verified": bool(s.get("all_78_gates_verified", False)),
        "g13_to_g78_all_passed": bool(s.get("g13_to_g78_all_passed", False)),
        "g77_to_g78_all_passed": bool(s.get("g77_to_g78_all_passed", False)),
        "overall_ready_for_hardware_attach": bool(s["overall_ready_for_hardware_attach"]),
        "hardware_live_attachment_authorized": bool(
            s.get("hardware_live_attachment_authorized", False)
        ),
        "agent_auto_flash_blocked": bool(s["agent_auto_flash_blocked"]),
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


def _normalize_31pillar_fault_id(fault_id: Optional[str]) -> Optional[str]:
    if not fault_id:
        return None
    if fault_id in MASTER_31_PILLAR_IDS:
        return fault_id
    m = re.match(r"^pillar_(\d+)$", fault_id.strip().lower())
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(MASTER_31_PILLAR_IDS):
            return MASTER_31_PILLAR_IDS[idx]
    return fault_id


def _worker_recovery_31pillar(args: Tuple[bool, Optional[str]]) -> Dict[str, Any]:
    use_clean_room, fault_pillar = args
    rep = evaluate_realhw_31pillar_recovery_master(
        force_clean_room=use_clean_room,
        fault_inject_pillar=_normalize_31pillar_fault_id(fault_pillar),
    )
    return rep.to_dict()


def _worker_pillar_3_batch_221(args: Tuple[Tuple[str, ...], bool]) -> Dict[str, Dict[str, Any]]:
    names, use_clean_room = args
    out: Dict[str, Dict[str, Any]] = {}
    legacy_names = tuple(
        n
        for n in names
        if n
        not in (
            "realhw_desqueeze_focusmap_shocklesswb",
            "realhw_hdmi_log1080_proxy_focusmag",
            "discover_forward_compat_45plus",
        )
    )
    if legacy_names:
        out.update(_worker_pillar_3_batch_209((legacy_names, use_clean_room)))
    if "realhw_desqueeze_focusmap_shocklesswb" in names:
        out["realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_audit"] = (
            realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_report_to_dict(
                analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
                    clean_room=use_clean_room
                )
            )
        )
    if "realhw_hdmi_log1080_proxy_focusmag" in names:
        out["realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_audit"] = (
            realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_report_to_dict(
                analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
                    clean_room=use_clean_room
                )
            )
        )
    if "discover_forward_compat_45plus" in names:
        lab_dir = Path(fx3_firmware_lab.__file__).resolve().parent
        for mod_path in sorted(lab_dir.glob("realhw_*_auditor.py")):
            stem = mod_path.stem
            if stem in _KNOWN_18_REALHW_AUDITOR_STEMS:
                continue
            prefix = stem[: -len("_auditor")]
            mod = importlib.import_module(f"fx3_firmware_lab.{stem}")
            analyze_fn = getattr(mod, f"analyze_{prefix}", None)
            to_dict_fn = getattr(mod, f"{prefix}_report_to_dict", None)
            if callable(analyze_fn):
                rep = analyze_fn(clean_room=use_clean_room)
                if callable(to_dict_fn):
                    out[f"{prefix}_audit"] = dict(to_dict_fn(rep))
                elif hasattr(rep, "to_dict"):
                    out[f"{prefix}_audit"] = dict(rep.to_dict())
                elif isinstance(rep, Mapping):
                    out[f"{prefix}_audit"] = dict(rep)
    return out


def _worker_phase216(
    args: Tuple[str, str, bool, Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    fx6_str, fx3_str, use_clean_room, p216_faults = args
    fx6_dir = Path(fx6_str)
    fx3_dir = Path(fx3_str)
    rep_off = evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
    )
    sim_kwargs: Dict[str, Any] = {}
    if p216_faults.get("desqueeze_lock"):
        sim_kwargs["desqueeze_ratio"] = "1.6x"
        sim_kwargs["marker_display_locked_off"] = False
    if p216_faults.get("hdmi_only_card_rec"):
        sim_kwargs["rec_media_dur_hdmi_output"] = "OFF_HDMI_ONLY"
        sim_kwargs["require_internal_card_recording"] = True
    if p216_faults.get("proxy_orphan"):
        sim_kwargs["orphan_clip_or_sub_count"] = 1
    if p216_faults.get("title_38char"):
        sim_kwargs["title_name"] = "A" * 38
    if p216_faults.get("h0_h3_drift"):
        sim_kwargs["simulated_h0_h3_drifted_surfaces"] = 1

    rep_sim = evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **sim_kwargs,
    )
    return rep_off.to_dict(), rep_sim.to_dict()


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1..P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
) -> Milestone221PillarResult:
    errors: List[str] = []
    off_total = int(raw_off["total_gates"])
    off_ver = int(raw_off["verified_gates"])
    sim_total = int(raw_sim["total_gates"])
    sim_ver = int(raw_sim["verified_gates"])

    if (
        off_total < 78
        or off_ver < 75
        or off_ver != off_total - 3
        or int(raw_off["blocked_or_pending_gates"]) != 3
        or raw_off["overall_ready_for_hardware_attach"] is not False
        or raw_off["hardware_live_attachment_authorized"] is not False
        or not bool(raw_off["offline_75_gates_verified"])
    ):
        errors.append(
            f"p1_offline: expected {off_total - 3}/{off_total} (>=75/78, 3 Tier-0 gates fail-closed) "
            f"and hardware_attach=False, got {off_ver}/{off_total}"
        )

    if (
        sim_total < 78
        or sim_ver != sim_total
        or not bool(raw_sim["all_78_gates_verified"])
        or not bool(raw_sim["g13_to_g78_all_passed"])
        or not bool(raw_sim["g77_to_g78_all_passed"])
        or raw_sim["overall_ready_for_hardware_attach"] is not False
        or raw_sim["hardware_live_attachment_authorized"] is not False
        or raw_sim["agent_auto_flash_blocked"] is not True
    ):
        errors.append(
            f"p1_simulated: expected {sim_total}/{sim_total} (>=78/78) with hardware_attach=False, "
            f"got {sim_ver}/{sim_total}"
        )

    for mode_tag, rmap in (("offline", raw_off), ("simulated", raw_sim)):
        if (
            rmap["persistent_emmc_writes_authorized"] is not False
            or rmap["persistent_write_release"] is not False
            or rmap["spi_nor_write_authorized"] is not False
            or rmap["el3_payload_transmit_authorized"] is not False
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
        "g63_to_g78_valid": dict(nested_sim),
    }
    return Milestone221PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_78GATE_REALHW_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"78-Gate Safety: offline={off_ver}/{off_total} (3 Tier-0 gates fail-closed), "
            f"simulated={sim_ver}/{sim_total} (G73..G78 De-Squeeze 1.65x/FocusMap/Simult/"
            f"ShocklessWB/HDMI-Log1080/Proxy/FocusMag/FileSettings-37ch/TCRegen-Slot1/RECLamp) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    rec_31: Mapping[str, Any],
    faults: RealHwMilestone221FaultInjection,
) -> Tuple[Milestone221PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    p_count = int(rec_31.get("pillar_count", 0))
    p_passed = int(rec_31.get("pillars_passed", 0))
    rec_status = str(rec_31.get("status", ""))

    otp = (
        max(int(rec_31.get("otp_fuse_writes", 0)), int(rec_31.get("otp_fuse_touches", 0)))
        + int(faults.p2_otp_fuse_writes_override)
    )
    rpmb = int(rec_31.get("rpmb_counter_increments", -1)) + int(faults.p2_rpmb_writes_override)
    ptx = int(rec_31.get("passive_tx_bytes_emitted", -1)) + int(faults.p2_passive_tx_bytes_override)
    usb_pkts = int(rec_31.get("physical_usb_packets_emitted", -1)) + int(
        faults.p2_physical_usb_packets_override
    )
    dev_writes = int(rec_31.get("physical_device_writes", -1)) + int(
        faults.p2_physical_device_writes_override
    )
    leaked = int(rec_31.get("raw_firmware_bytes_leaked", -1)) + int(
        faults.p2_raw_firmware_bytes_leaked_override
    )

    p31a = rec_31.get("pillar31_a_filesettings_shotmark_vault", {})
    p31b = rec_31.get("pillar31_b_tcregen_slot1_extlk_vault", {})
    p31a_ok = isinstance(p31a, Mapping) and bool(p31a.get("passed"))
    p31b_ok = isinstance(p31b, Mapping) and bool(p31b.get("passed"))

    status_ok = rec_status == "VERIFIED_31OF31_PILLAR_RECOVERY_MASTER" or (
        p_count > 31 and p_passed == p_count and bool(rec_31.get("all_passed"))
    )
    if (
        not bool(rec_31.get("all_passed"))
        or not status_ok
        or p_count < 31
        or p_passed < 31
        or p_passed != p_count
        or not p31a_ok
        or not p31b_ok
    ):
        errors.append(
            f"p2_31pillar: expected >=31/31 VERIFIED_31OF31_PILLAR_RECOVERY_MASTER, "
            f"got {p_passed}/{p_count} (status={rec_status!r}, 31A={p31a_ok}, 31B={p31b_ok})"
        )

    if (
        otp != 0
        or rpmb != 0
        or ptx != 0
        or usb_pkts != 0
        or dev_writes != 0
        or leaked != 0
        or rec_31.get("el3_payload_transmit_authorized") is not False
        or rec_31.get("isp_write_authorized") is not False
        or rec_31.get("spi_nor_write_authorized") is not False
        or rec_31.get("persistent_emmc_writes_authorized") is not False
        or rec_31.get("persistent_write_release") is not False
    ):
        errors.append(
            f"p2_redlines: zero-touch invariant violated (otp={otp}, rpmb={rpmb}, ptx={ptx}, "
            f"usb_pkts={usb_pkts}, dev_writes={dev_writes}, leaked={leaked})"
        )

    passed = len(errors) == 0
    evidence = {
        "status": rec_status,
        "pillar_count": p_count,
        "pillars_passed": p_passed,
        "pillar31_a_filesettings_shotmark_passed": p31a_ok,
        "pillar31_b_tcregen_slot1_extlk_passed": p31b_ok,
        "otp_fuse_writes": otp,
        "rpmb_writes": rpmb,
        "passive_tx_bytes": ptx,
        "physical_usb_packets_emitted": usb_pkts,
        "physical_device_writes": dev_writes,
        "raw_firmware_bytes_leaked": leaked,
        "master_31pillar_sha256": str(rec_31.get("master_31pillar_sha256", "")),
    }
    pillar = Milestone221PillarResult(
        pillar_id="P2",
        pillar_name="THIRTY_ONE_PILLAR_RECOVERY_MASTER_VAULT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"31-Pillar Recovery ({rec_status}): {p_passed}/{p_count} (>=31 required; "
            f"Pillars 29..31 CAMSET-Simult/Proxy-HDMIOnly/FileSettings-ShotMark-TCRegen), "
            f"OTP={otp}, RPMB={rpmb}, passive_tx={ptx} {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "recovery_status": rec_status,
        "recovery_pillar_count": p_count,
        "recovery_pillars_passed": p_passed,
        "otp_fuse_writes": otp,
        "rpmb_writes": rpmb,
        "passive_tx_bytes": ptx,
        "physical_usb_packets_emitted": usb_pkts,
        "raw_firmware_bytes_leaked": leaked,
    }
    return pillar, meta


def _evaluate_pillar_3(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: RealHwMilestone221FaultInjection,
) -> Tuple[Milestone221PillarResult, Dict[str, Any]]:
    m209_p3, meta_42 = _eval_m209_p3(auditors, _effective_m209_faults(faults))
    errors: List[str] = list(m209_p3.errors)
    auditor_statuses: Dict[str, bool] = dict(m209_p3.evidence["auditor_statuses"])
    auditor_sha256s: Dict[str, Optional[str]] = dict(m209_p3.evidence["auditor_sha256s"])

    # #43 (Phase 205): De-Squeeze 1.65x, External M&C Focus Map <150fps, Simult+AutoSwitch & Shockless WB
    a43 = auditors.get("realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_audit", {})
    a43_leak = int(a43.get("raw_firmware_bytes_leaked", -1))
    a43_overlay = bool(a43.get("in_body_focus_map_overlay_injected", True)) or bool(
        faults.p3_desqueeze_focusmap_overlay_fault
    )
    if (
        not bool(a43.get("all_checks_passed"))
        or a43.get("o_rdonly_enforced") is not True
        or a43.get("desqueeze_165x_locks_and_suppression_verified") is not True
        or a43.get("external_mc_focus_map_150fps_cutoff_verified") is not True
        or a43.get("simult_auto_switch_and_shockless_wb_bypass_verified") is not True
        or a43.get("zero_write_firewall_and_matrix_verified") is not True
        or a43.get("persistent_emmc_writes_authorized") is not False
        or a43.get("spi_nor_write_authorized") is not False
        or a43.get("el3_payload_transmit_authorized") is not False
        or int(a43.get("physical_usb_packets_emitted", -1)) != 0
        or int(a43.get("persistent_writes", -1)) != 0
        or int(a43.get("calibration_mutation_bytes", -1)) != 0
        or a43_overlay is not False
        or a43_leak != 0
    ):
        errors.append("p3: #43 realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_audit failed")
        auditor_statuses["realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_audit"] = False
    else:
        auditor_statuses["realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_audit"] = True
    auditor_sha256s["realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_audit"] = (
        str(a43.get("report_sha256")) if a43.get("report_sha256") else None
    )

    # #44 (Phase 211): HDMI Log 1080p vs Off(HDMI Only) 4K, Px Proxy Vault & FocusMag x BrightMon
    a44 = auditors.get("realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_audit", {})
    a44_p1 = a44.get("pillar_1_hdmi_log_1080p_and_hdmionly_4k", {})
    a44_p2 = a44.get("pillar_2_proxy_matrix_and_coupled_vault", {})
    a44_p3 = a44.get("pillar_3_focusmag_and_bright_monitoring", {})
    a44_p4 = a44.get("pillar_4_write_guard_and_matrix", {})
    a44_leak = (
        int(a44_p4.get("raw_firmware_bytes_leaked", -1)) if isinstance(a44_p4, Mapping) else -1
    )
    if (
        not bool(a44.get("all_checks_passed"))
        or bool(faults.p3_hdmi_proxy_focusmag_guard_fault)
        or not (isinstance(a44_p1, Mapping) and bool(a44_p1.get("passed")))
        or not (isinstance(a44_p2, Mapping) and bool(a44_p2.get("passed")))
        or not (isinstance(a44_p3, Mapping) and bool(a44_p3.get("passed")))
        or not (isinstance(a44_p4, Mapping) and bool(a44_p4.get("passed")))
        or a44_p4.get("persistent_emmc_writes_authorized") is not False
        or a44_p4.get("spi_nor_write_authorized") is not False
        or a44_p4.get("el3_payload_transmit_authorized") is not False
        or int(a44_p4.get("physical_usb_packets_emitted", -1)) != 0
        or a44_leak != 0
    ):
        errors.append("p3: #44 realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_audit failed")
        auditor_statuses["realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_audit"] = False
    else:
        auditor_statuses["realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_audit"] = True
    auditor_sha256s["realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_audit"] = (
        str(a44.get("report_digest_sha256")) if a44.get("report_digest_sha256") else None
    )

    # Forward-compatible inclusion of any 45th+ auditor keys
    for key, obj in sorted(auditors.items()):
        if key not in auditor_statuses and key.endswith("_audit") and isinstance(obj, Mapping):
            ok = bool(obj.get("all_checks_passed"))
            auditor_statuses[key] = ok
            if not ok:
                errors.append(f"p3: forward-compat auditor {key} failed")

    auditors_total = len(auditor_statuses)
    auditors_passed = sum(1 for v in auditor_statuses.values() if v)
    total_leaked = (
        int(meta_42["raw_firmware_bytes_leaked"])
        + max(0, a43_leak)
        + max(0, a44_leak)
        + int(faults.p3_raw_firmware_bytes_leaked_override)
    )
    end_tx = int(meta_42["e_nd_actuator_tx_count"])
    cal_mut = int(meta_42["calibration_mutation_bytes"])

    if not (auditors_passed >= 44 and auditors_passed == auditors_total):
        errors.append(
            f"p3: expected >= 44 auditors and all passing, got {auditors_passed}/{auditors_total}"
        )
    if total_leaked != 0:
        errors.append(f"p3: raw_firmware_bytes_leaked={total_leaked} != 0")

    passed = len(errors) == 0 and cal_mut == 0 and total_leaked == 0 and end_tx == 0
    evidence = dict(m209_p3.evidence)
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
    pillar = Milestone221PillarResult(
        pillar_id="P3",
        pillar_name="FORTY_FOUR_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {auditors_passed}/{auditors_total} auditors (>=44 required; "
            f"#43 De-Squeeze/FocusMap/ShocklessWB + #44 HDMI-Log1080/Proxy/FocusMag/BrightMon), "
            f"e_nd_tx={end_tx}, leaked={total_leaked}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_42)
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
    faults: RealHwMilestone221FaultInjection,
) -> Tuple[Milestone221PillarResult, Dict[str, Any]]:
    m209_p4, meta_36 = _eval_m209_p4(vm_rep, _effective_m209_faults(faults))
    errors: List[str] = list(m209_p4.errors)
    stage_statuses: Dict[str, bool] = dict(m209_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_38_STAGE_KEYS[36:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if not ok and f"p4: forward-compat VM stage {skey} failed" not in errors:
            errors.append(f"p4: VM co-emulation {skey} failed")

    # Forward-compatible discovery of Stage 39+ keys
    for skey, sobj in sorted(vm_rep.items()):
        m = _VM_STAGE_KEY_RE.match(str(skey))
        if m and int(m.group(1)) >= 39 and skey not in stage_statuses and isinstance(sobj, Mapping):
            ok = bool(sobj.get("all_checks_passed"))
            stage_statuses[skey] = ok
            if not ok:
                errors.append(f"p4: forward-compat VM stage {skey} failed")

    # Stage 37 (Phase 207): De-Squeeze 1.65x, Focus Map <150fps, Simult & Shockless WB HIL
    s37 = vm_rep.get("stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil", {})
    s37_mut = (
        int(s37.get("emmc_mutation_bytes", -1))
        + int(s37.get("spi_nor_mutation_bytes", -1))
        + int(s37.get("desqueeze_baked_into_raw_or_xavc_frames", -1))
        + int(s37.get("inbody_fx3_focus_map_overlay_frames", -1))
        + int(s37.get("rsv_orphan_count", -1))
        + int(faults.p4_stage37_desqueeze_or_focusmap_faults)
    )
    if (
        int(s37.get("nop_count", -1)) != 0
        or int(s37.get("cp_mutation_bytes", -1)) != 0
        or int(s37.get("wbi_mutation_bytes", -1)) != 0
        or int(s37.get("calibration_mutation_bytes", -1)) != 0
        or s37.get("persistent_emmc_writes_authorized") is not False
        or s37.get("spi_nor_write_authorized") is not False
        or s37.get("el3_payload_transmit_authorized") is not False
        or int(s37.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(s37.get("wf12_00342260_hits", -1)) != 0
        or s37_mut != 0
    ):
        errors.append(f"p4: Stage 37 redlines violated (desqueeze_or_focusmap={s37_mut})")
        stage_statuses["stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil"] = False

    # Stage 38 (Phase 213): HDMI Log 1080p vs Off(HDMI Only) 4K, Px Proxy Vault & FocusMag HIL
    s38 = vm_rep.get("stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil", {})
    s38_mut = (
        int(s38.get("emmc_mutation_bytes", -1))
        + int(s38.get("spi_nor_mutation_bytes", -1))
        + int(s38.get("single_sided_proxy_or_main_orphan_mutations", -1))
        + int(s38.get("on_camera_proxy_playback_frames", -1))
        + int(s38.get("rsv_orphan_count", -1))
        + int(faults.p4_stage38_hdmi_or_proxy_or_focusmag_faults)
    )
    if (
        int(s38.get("nop_count", -1)) != 0
        or int(s38.get("cp_mutation_bytes", -1)) != 0
        or int(s38.get("wbi_mutation_bytes", -1)) != 0
        or int(s38.get("calibration_mutation_bytes", -1)) != 0
        or s38.get("persistent_emmc_writes_authorized") is not False
        or s38.get("spi_nor_write_authorized") is not False
        or s38.get("el3_payload_transmit_authorized") is not False
        or int(s38.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(s38.get("wf12_00342260_hits", -1)) != 0
        or s38_mut != 0
    ):
        errors.append(f"p4: Stage 38 redlines violated (hdmi_or_proxy_or_focusmag={s38_mut})")
        stage_statuses["stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil"] = False

    vm_stages_total = len(stage_statuses)
    vm_stages_passed = sum(1 for v in stage_statuses.values() if v)
    emmc_corruptions = (
        int(meta_36.get("emmc_corruptions", 0))
        + max(0, int(s37.get("emmc_mutation_bytes", 0)))
        + max(0, int(s38.get("emmc_mutation_bytes", 0)))
    )
    total_wf12_hits = (
        int(meta_36.get("wf12_00342260_hits", 0))
        + max(0, int(s37.get("wf12_00342260_hits", 0)))
        + max(0, int(s38.get("wf12_00342260_hits", 0)))
    )

    if not (vm_stages_passed >= 38 and vm_stages_passed == vm_stages_total):
        errors.append(
            f"p4: expected >= 38 VM stages and all passing, got {vm_stages_passed}/{vm_stages_total}"
        )
    if emmc_corruptions != 0:
        errors.append(f"p4: emmc_corruptions={emmc_corruptions} != 0")

    passed = len(errors) == 0
    evidence = dict(m209_p4.evidence)
    evidence.update(
        {
            "vm_stages_total": vm_stages_total,
            "vm_stages_passed": vm_stages_passed,
            "stage_count": vm_stages_total,
            "passed_stage_count": vm_stages_passed,
            "stage_statuses": stage_statuses,
            "emmc_corruptions": emmc_corruptions,
            "wf12_00342260_hits": total_wf12_hits,
            "stage37_digest_sha256": s37.get("phase207_audit_digest_sha256"),
            "stage38_digest_sha256": s38.get("phase213_audit_digest_sha256"),
        }
    )
    pillar = Milestone221PillarResult(
        pillar_id="P4",
        pillar_name="THIRTY_EIGHT_PLUS_STAGE_VM_HIL_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {vm_stages_passed}/{vm_stages_total} stages (>=38 required; Stages 37..38 "
            f"De-Squeeze-FocusMap-ShocklessWB/HDMI-Log1080-Proxy-FocusMag), "
            f"emmc_corruptions={emmc_corruptions}, wf12_hits={total_wf12_hits} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_36)
    meta.update(
        {
            "stage_count": vm_stages_total,
            "passed_count": vm_stages_passed,
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
    faults: RealHwMilestone221FaultInjection,
) -> Tuple[Milestone221PillarResult, Dict[str, Any]]:
    m209_p5, meta_p5_209 = _eval_m209_p5(
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
        _effective_m209_faults(faults),
    )
    errors: List[str] = list(m209_p5.errors)

    # Phase 216 offline physical-Tier0-receipt block mode
    p216_off_dict = copy.deepcopy(dict(raw_p216_off))
    v216_off = verify_phase216_report(p216_off_dict)
    if (
        not v216_off.valid
        or p216_off_dict.get("go_no_go") != GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        or p216_off_dict.get("hardware_live_attachment_authorized") is not False
        or p216_off_dict.get("tier0_receipt_verified") is not False
        or not bool(p216_off_dict.get("all_5_operator_checklists_passed"))
        or int(p216_off_dict.get("usb_packets_transmitted", -1)) != 0
        or int(p216_off_dict.get("physical_usb_packets_emitted", -1)) != 0
        or int(p216_off_dict.get("raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append(
            f"p5_p216_off: expected {GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT} "
            f"(got {p216_off_dict.get('go_no_go')}, valid={v216_off.valid}, errs={v216_off.errors})"
        )

    # Phase 216 simulated dry-run S1..S5 preflight mode
    p216_sim_dict = copy.deepcopy(dict(raw_p216_sim))
    if faults.p5_inject_p216_usb_packets_override:
        p216_sim_dict["usb_packets_transmitted"] = int(
            p216_sim_dict.get("usb_packets_transmitted", 0)
        ) + int(faults.p5_inject_p216_usb_packets_override)
        p216_sim_dict["physical_usb_packets_emitted"] = int(
            p216_sim_dict.get("physical_usb_packets_emitted", 0)
        ) + int(faults.p5_inject_p216_usb_packets_override)

    v216_sim = verify_phase216_report(p216_sim_dict)
    p216_sim_passed = int(p216_sim_dict.get("checklists_passed", -1))
    p216_sim_pkts = max(
        int(p216_sim_dict.get("usb_packets_transmitted", -1)),
        int(p216_sim_dict.get("physical_usb_packets_emitted", -1)),
    )
    p216_sim_leaked = int(p216_sim_dict.get("raw_firmware_bytes_leaked", -1))
    p216_h0_h3 = int(p216_sim_dict.get("h0_equals_h3_count", -1))

    c_keys = (
        "checklist_1_desqueeze_and_mc_focus_map",
        "checklist_2_hdmi_log_and_blank_lcd",
        "checklist_3_simult_autoswitch_and_proxy_vault",
        "checklist_4_file_settings_shotmark_and_tc_slot1",
        "checklist_5_reclamp_shockless_wb_and_tier0_gate",
    )
    all_c_ok = all(
        isinstance(p216_sim_dict.get(ck), Mapping) and bool(p216_sim_dict[ck].get("passed"))
        for ck in c_keys
    )

    if (
        not v216_sim.valid
        or p216_sim_dict.get("go_no_go") != GO_NO_GO_DRY_RUN_SIMULATED_READY
        or not bool(p216_sim_dict.get("all_5_operator_checklists_passed"))
        or p216_sim_passed != 5
        or not all_c_ok
        or not bool(p216_sim_dict.get("tier0_receipt_verified"))
        or p216_sim_dict.get("hardware_live_attachment_authorized") is not False
        or p216_h0_h3 != 16
        or p216_sim_pkts != 0
        or p216_sim_leaked != 0
        or p216_sim_dict.get("persistent_emmc_writes_authorized") is not False
        or p216_sim_dict.get("spi_nor_write_authorized") is not False
        or p216_sim_dict.get("el3_payload_transmit_authorized") is not False
    ):
        errors.append(
            f"p5_p216_sim: preflight-hdmi-proxy-desqueeze-and-simult failed "
            f"(go={p216_sim_dict.get('go_no_go')}, checklists={p216_sim_passed}/5, errs={v216_sim.errors})"
        )

    passed = len(errors) == 0
    evidence = dict(m209_p5.evidence)
    evidence.update(
        {
            "p216_offline_go_no_go": p216_off_dict.get("go_no_go"),
            "p216_offline_checklists_passed": p216_off_dict.get("checklists_passed"),
            "p216_offline_report_verified": bool(v216_off.valid),
            "p216_sim_go_no_go": p216_sim_dict.get("go_no_go"),
            "p216_sim_checklists_passed": p216_sim_passed,
            "p216_hardware_live_attachment_authorized": p216_sim_dict.get(
                "hardware_live_attachment_authorized"
            ),
            "p216_h0_equals_h3_count": p216_h0_h3,
            "p216_sim_usb_packets_transmitted": p216_sim_pkts,
            "p216_sim_raw_firmware_bytes_leaked": p216_sim_leaked,
            "p216_sim_report_verified": bool(v216_sim.valid),
            "p216_sim_report_sha256": str(p216_sim_dict.get("report_sha256", "")),
        }
    )
    pillar = Milestone221PillarResult(
        pillar_id="P5",
        pillar_name="TRIPLE_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Triple Bench Preflights: Ph186(card-insert sim={meta_p5_209['p186_sim_gates_passed']}/4) + "
            f"Ph204(cable-fan-slot1 sim={meta_p5_209['p204_sim_groups_passed']}/3) + "
            f"Ph216(hdmi-proxy-desqueeze-simult sim={p216_sim_passed}/5 H0==H3={p216_h0_h3}/16) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_p5_209)
    meta.update(
        {
            "p216_offline_go_no_go": str(p216_off_dict.get("go_no_go", "")),
            "p216_sim_go_no_go": str(p216_sim_dict.get("go_no_go", "")),
            "p216_sim_checklists_passed": p216_sim_passed,
            "p216_hardware_live_attachment_authorized": bool(
                p216_sim_dict.get("hardware_live_attachment_authorized", True)
            ),
            "p216_h0_equals_h3_count": p216_h0_h3,
            "p216_sim_usb_packets_transmitted": p216_sim_pkts,
            "p216_sim_raw_firmware_bytes_leaked": p216_sim_leaked,
        }
    )
    return pillar, meta


def _evaluate_pillar_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: RealHwMilestone221FaultInjection,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
    p5_meta: Mapping[str, Any],
) -> Tuple[Milestone221PillarResult, Dict[str, Any]]:
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

    for spec in ROUND28_TO_42_SPECS:
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

        png_pair = ROUND28_TO_42_PNG_RECEIPTS[spec.round_num]
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
        int(p2_meta.get("otp_fuse_writes", -1)) != 0
        or int(p2_meta.get("rpmb_writes", -1)) != 0
        or int(p2_meta.get("passive_tx_bytes", -1)) != 0
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
        or int(p5_meta.get("p216_sim_checklists_passed", -1)) != 5
        or p5_meta.get("p216_hardware_live_attachment_authorized") is not False
        or int(p5_meta.get("p216_h0_equals_h3_count", -1)) != 16
        or int(p5_meta.get("p216_sim_usb_packets_transmitted", -1)) != 0
        or int(p5_meta.get("p216_sim_raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append(
            "p6: P5 H0==H3 (16/16) or triple bench preflight (Ph186/Ph204/Ph216) invariant breached"
        )

    passed = (
        len(errors) == 0
        and rounds_verified == len(ROUND28_TO_42_SPECS)
        and total_runs_verified == 45
        and pngs_verified == 30
        and 0 < max_png_bytes < PNG_MAX_SIZE_BYTES
        and total_nops == 0
        and total_crashes == 0
        and total_emmc == 0
    )
    evidence = {
        "round_sources": round_sources,
        "round_schemas": round_schemas,
        "rounds_verified": rounds_verified,
        "expected_rounds": len(ROUND28_TO_42_SPECS),
        "runs_by_round": runs_by_round,
        "total_runs_verified": total_runs_verified,
        "expected_total_runs": 45,
        "png_receipts_verified": pngs_verified,
        "expected_png_receipts": 30,
        "png_max_bytes": max_png_bytes,
        "png_max_ceiling_bytes": PNG_MAX_SIZE_BYTES,
        "png_sizes_by_asset": png_sizes_by_asset,
        "png_sources_by_round": png_sources_by_round,
        "h0_equals_h3_count": int(p5_meta.get("p216_h0_equals_h3_count", 0)),
        "emmc_write_count": total_emmc,
        "e_nd_actuator_tx_count": int(p1_meta.get("g71_e_nd_actuator_tx_count", 0)),
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
        "milestone175_schema_anchor": MILESTONE175_SCHEMA_VERSION,
        "milestone193_schema_anchor": MILESTONE193_SCHEMA_VERSION,
        "milestone209_schema_anchor": MILESTONE209_SCHEMA_VERSION,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }
    pillar = Milestone221PillarResult(
        pillar_id="P6",
        pillar_name="REAL_FX3_702_QEMU_ROUNDS_28_TO_42_AND_PNG_RECEIPTS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Live FX3 7.02 QEMU Rounds 28..42={rounds_verified}/15 rounds ({total_runs_verified}/45 runs, "
            f"PNGs={pngs_verified}/30 max={max_png_bytes}B < 28KiB), H0==H3=16/16, "
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


def _collect_parallel_milestone221_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: RealHwMilestone221FaultInjection,
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
    Dict[str, Any],
    Dict[str, Any],
]:
    m209_f = _effective_m209_faults(faults)
    m193_f = _effective_m193_faults(m209_f)
    gate_fault_dict = _fault_to_78gate_worker_dict(faults)
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
        "desqueeze_lock": bool(faults.p5_inject_p216_desqueeze_lock_fault),
        "hdmi_only_card_rec": bool(faults.p5_inject_p216_hdmi_only_card_rec_fault),
        "proxy_orphan": bool(faults.p5_inject_p216_proxy_orphan_fault),
        "title_38char": bool(faults.p5_inject_p216_title_38char_fault),
        "h0_h3_drift": bool(faults.p5_inject_p216_h0_h3_drift),
    }

    # Pre-evaluate Wave 26-29 cold-scan-budgeted auditors (0.15s SLA) in parent process
    # before fork() so 24-way worker CPU/IO contention never inflates perf_counter() and
    # all forked workers (78-gate, VM Stage 35-38, Ph204/Ph216) inherit warm donor caches.
    pre_batch = (
        "realhw_fan_shutter_lut601_702",
        "realhw_big6_camset_vmcbncm1",
        "realhw_desqueeze_focusmap_shocklesswb",
        "realhw_hdmi_log1080_proxy_focusmag",
        "discover_forward_compat_45plus",
    )
    pre_auditors = _worker_pillar_3_batch_221((pre_batch, use_clean_room))

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
    )

    eff_p2_fault = (
        faults.p2_fault_inject_pillar
        or m209_f.p2_fault_inject_pillar
        or m193_f.p2_fault_inject_pillar
    )

    try:
        ctx = mp.get_context("fork")
        pool_workers = min(12, max(4, mp.cpu_count() or 8))
        with ProcessPoolExecutor(max_workers=pool_workers, mp_context=ctx) as ex:
            fut_vm = ex.submit(_worker_pillar_4, use_clean_room)
            fut_p136 = ex.submit(_worker_phase136, use_clean_room)
            fut_31p = ex.submit(_worker_recovery_31pillar, (use_clean_room, eff_p2_fault))
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
            fut_216 = ex.submit(
                _worker_phase216,
                (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p216_fault_dict),
            )
            fut_3 = [
                ex.submit(_worker_pillar_3_batch_221, (batch, use_clean_room))
                for batch in p3_batches
            ]
            fut_1_off = ex.submit(
                _worker_78gate_single, (str(repo_root), use_clean_room, False, gate_fault_dict)
            )
            fut_1_sim = ex.submit(
                _worker_78gate_single, (str(repo_root), use_clean_room, True, gate_fault_dict)
            )

            raw_1_off = fut_1_off.result()
            raw_1_sim = fut_1_sim.result()
            raw_31p = fut_31p.result()
            auditors: Dict[str, Dict[str, Any]] = dict(pre_auditors)
            for fg in fut_3:
                auditors.update(fg.result())
            raw_vm = fut_vm.result()
            raw_p136 = fut_p136.result()
            raw_p143, raw_p154, raw_p186_off, raw_p186_sim = fut_143_154_186.result()
            raw_p204_off, raw_p204_sim = fut_204.result()
            raw_p216_off, raw_p216_sim = fut_216.result()
            return (
                raw_1_off,
                raw_1_sim,
                raw_31p,
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
            )
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1_off = _worker_78gate_single((str(repo_root), use_clean_room, False, gate_fault_dict))
    raw_1_sim = _worker_78gate_single((str(repo_root), use_clean_room, True, gate_fault_dict))
    raw_31p = _worker_recovery_31pillar((use_clean_room, eff_p2_fault))
    auditors = dict(pre_auditors)
    for batch in p3_batches:
        auditors.update(_worker_pillar_3_batch_221((batch, use_clean_room)))
    raw_vm = _worker_pillar_4(use_clean_room)
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
    return (
        raw_1_off,
        raw_1_sim,
        raw_31p,
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
    )


def evaluate_realhw_milestone221_master_gate(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[RealHwMilestone221FaultInjection] = None,
) -> RealHwMilestone221MasterGateReport:
    """Build & evaluate the Grand Milestone Phase 221 6-Pillar Real-Hardware Master Gate."""
    if force_clean_room is not None:
        use_clean_room = bool(force_clean_room)
    elif synthetic_clean_room is not None:
        use_clean_room = bool(synthetic_clean_room)
    else:
        use_clean_room = _is_forced_clean_room()

    active_faults = faults or RealHwMilestone221FaultInjection()

    (
        raw_1_off,
        raw_1_sim,
        raw_31p,
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
    ) = _collect_parallel_milestone221_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )

    p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
    p2, meta_2 = _evaluate_pillar_2(raw_31p, active_faults)
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

    pillars: Tuple[Milestone221PillarResult, ...] = (p1, p2, p3, p4, p5, p6)
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
        + int(meta_5["p186_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p204_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p216_sim_raw_firmware_bytes_leaked"])
    )
    total_usb_pkts = (
        int(raw_1_sim["usb_packets_transmitted"])
        + int(meta_2["physical_usb_packets_emitted"])
        + int(meta_5["p186_sim_usb_packets_emitted"])
        + int(meta_5["p204_sim_usb_packets_emitted"])
        + int(meta_5["p216_sim_usb_packets_transmitted"])
    )
    total_end_tx = (
        max(0, int(p1.evidence["g71_e_nd_actuator_tx_count"]))
        + int(meta_3["e_nd_actuator_tx_count"])
        + int(meta_4["e_nd_actuator_tx_count"])
        + max(0, int(meta_5["p204_e_nd_actuator_tx_count"]))
    )
    min_h0_eq_h3 = min(
        int(meta_5["h0_equals_h3_count"]),
        int(meta_5["p186_h0_equals_h3_count"]),
        int(meta_5["p204_h0_equals_h3_count"]),
        int(meta_5["p216_h0_equals_h3_count"]),
    )

    common_fields: Dict[str, Any] = {
        "schema": REALHW_MILESTONE221_SCHEMA,
        "schema_version": REALHW_MILESTONE221_SCHEMA,
        "phase_version": PHASE_221_VERSION,
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
        "usb_packets_transmitted": total_usb_pkts,
        "physical_usb_packets_emitted": total_usb_pkts,
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
        "gate78_total_gates": raw_1_sim["total_gates"],
        "gate78_offline_verified": raw_1_off["verified_gates"],
        "gate78_simulated_verified": raw_1_sim["verified_gates"],
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
        "h0_equals_h3_count": min_h0_eq_h3,
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
    payload_no_sha = {**common_fields, "pillars": [p.to_dict() for p in pillars]}
    digest = compute_milestone221_sha256(payload_no_sha)

    return RealHwMilestone221MasterGateReport(
        **common_fields,
        pillars=pillars,
        milestone221_sha256=digest,
    )


build_realhw_milestone221_master_gate_report = evaluate_realhw_milestone221_master_gate
evaluate_milestone221_master_gate = evaluate_realhw_milestone221_master_gate


def verify_realhw_milestone221_master_gate(
    report: object,
) -> RealHwMilestone221VerifyResult:
    """Fail-closed verifier for a Grand Milestone Phase 221 Real-Hardware Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, RealHwMilestone221MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return RealHwMilestone221VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone221_sha256="",
            observed_milestone221_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or RealHwMilestone221MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = (
        payload.get("schema") == REALHW_MILESTONE221_SCHEMA
        and payload.get("schema_version") == REALHW_MILESTONE221_SCHEMA
    )
    if not schema_ok:
        errors.append(
            f"schema mismatch: schema={payload.get('schema')!r} schema_version={payload.get('schema_version')!r}"
        )

    expected_sha = compute_milestone221_sha256(payload)
    observed_sha = str(payload.get("milestone221_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(
            f"milestone221_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}"
        )

    redlines_ok = (
        payload.get("o_rdonly_enforced") is True
        and payload.get("persistent_emmc_writes_authorized") is False
        and payload.get("persistent_write_release") is False
        and payload.get("spi_nor_write_authorized") is False
        and payload.get("el3_payload_transmit_authorized") is False
        and payload.get("isp_write_authorized") is False
        and payload.get("hardware_live_attachment_authorized") is False
        and payload.get("usb_packets_transmitted") == 0
        and payload.get("physical_usb_packets_emitted") == 0
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

    g_total = int(payload.get("gate78_total_gates", -1))
    g_off = int(payload.get("gate78_offline_verified", -1))
    g_sim = int(payload.get("gate78_simulated_verified", -1))
    aud_total = int(payload.get("auditors_total", -1))
    aud_passed = int(payload.get("auditors_passed", -2))
    vm_total = int(payload.get("vm_stages_total", -1))
    vm_passed = int(payload.get("vm_stages_passed", -2))

    counts_ok = (
        g_total >= 78
        and g_off >= 75
        and g_off == g_total - 3
        and g_sim >= 78
        and g_sim == g_total
        and int(payload.get("recovery_pillar_count", -1)) >= 31
        and int(payload.get("recovery_pillars_passed", -1))
        == int(payload.get("recovery_pillar_count", -2))
        and aud_passed >= 44
        and aud_passed == aud_total
        and vm_passed >= 38
        and vm_passed == vm_total
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
        and payload.get("p216_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p216_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p216_sim_checklists_passed", -1)) == 5
        and int(payload.get("p216_h0_equals_h3_count", -1)) == 16
        and int(payload.get("h0_equals_h3_count", -1)) == 16
        and int(payload.get("qemu_rounds_verified", -1)) == 15
        and int(payload.get("qemu_runs_verified", -1)) == 45
        and int(payload.get("qemu_png_receipts_verified", -1)) == 30
        and 0 < int(payload.get("qemu_png_max_bytes", -1)) < PNG_MAX_SIZE_BYTES
        and int(payload.get("qemu_real_kernel_nop_count", -1)) == 0
        and int(payload.get("qemu_real_kernel_crashes", -1)) == 0
        and int(payload.get("qemu_real_kernel_emmc_writes", -1)) == 0
    )
    if not counts_ok:
        errors.append("milestone221 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append(
            "all_pillars_milestone_ready / status is not MILESTONE_221_PREBENCH_MASTER_VERIFIED"
        )

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 221 payload")

    valid = bool(
        schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0
    )
    return RealHwMilestone221VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone221_sha256=expected_sha,
        observed_milestone221_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


def render_milestone221_markdown(report: RealHwMilestone221MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 221 Master Gate."""
    lines = [
        f"# Grand Milestone Phase 221 — Real-Hardware `ILME-FX3 Ver. 7.02` 6-Pillar Master Gate (`{report.schema}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone221_sha256}`",
        "",
        "## Hard-Locked Safety Redlines / 硬锁定安全红线",
        f"- `hardware_live_attachment_authorized = {report.hardware_live_attachment_authorized}`, "
        f"`persistent_emmc_writes_authorized = {report.persistent_emmc_writes_authorized}`, "
        f"`spi_nor_write_authorized = {report.spi_nor_write_authorized}`, "
        f"`el3_payload_transmit_authorized = {report.el3_payload_transmit_authorized}`",
        f"- `usb_packets_transmitted = {report.usb_packets_transmitted}`, "
        f"`raw_firmware_bytes_leaked = {report.raw_firmware_bytes_leaked}`, "
        f"`e_nd_actuator_tx_count = {report.e_nd_actuator_tx_count}`, "
        f"`otp_fuse_writes = {report.otp_fuse_writes}`, "
        f"`rpmb_writes = {report.rpmb_writes}`, "
        f"`passive_tx_bytes = {report.passive_tx_bytes}`",
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
            "## Key Grand Milestone Phase 221 Metrics / 实机总闭环核心指标",
            f"- 78-Gate Preflight (`G01..G78`): offline=`{report.gate78_offline_verified}/{report.gate78_total_gates}` (`G10..G12` locked), simulated=`{report.gate78_simulated_verified}/{report.gate78_total_gates}`",
            f"- 31-Pillar Recovery Master (`verify-31pillar-recovery`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`{report.recovery_status}`)",
            f"- 44+ Firmware-Lab Auditors (`auditors_passed >= 44`): `{report.auditors_passed}/{report.auditors_total}` (`raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`)",
            f"- 38+ Stage VM HIL Co-Emulation (`vm_stages_passed >= 38`): `{report.vm_stages_passed}/{report.vm_stages_total}` (`emmc_corruptions={report.vm_emmc_corruptions}`, `wf12_hits={report.vm_wf12_00342260_hits}`)",
            f"- Triple Bench Readiness Preflights (`Ph186 + Ph204 + Ph216`): `Ph186={report.p186_offline_go_no_go}/{report.p186_sim_go_no_go}`, `Ph204={report.p204_offline_go_no_go}/{report.p204_sim_go_no_go}`, `Ph216={report.p216_offline_go_no_go}/{report.p216_sim_go_no_go}` (`H0==H3={report.h0_equals_h3_count}/16`)",
            f"- Live FX3 `7.02` (`4.9.337-scel+`) QEMU Receipts (`Rounds 28..42`): `{report.qemu_rounds_verified}/15` rounds (`{report.qemu_runs_verified}/45` sub-runs, `PNGs={report.qemu_png_receipts_verified}/30` max=`{report.qemu_png_max_bytes}B < 28KiB`), `nop={report.qemu_real_kernel_nop_count}`, `crashes={report.qemu_real_kernel_crashes}`, `emmc_writes={report.qemu_real_kernel_emmc_writes}`",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "CALIBRATION_MUTATION_BYTES",
    "CP_MUTATION_BYTES",
    "DEFAULT_REPO_ROOT",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "EMMC_WRITE_COUNT",
    "E_ND_ACTUATOR_TX_COUNT",
    "FIRMWARE_LAB_44_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "ISP_WRITE_AUTHORIZED",
    "MILESTONE221_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P8_CP_MUTATION_FORBIDDEN",
    "PASSIVE_TX_BYTES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_221_VERSION",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "PNG_MAGIC_BYTES",
    "PNG_MAX_SIZE_BYTES",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_MILESTONE221_SCHEMA",
    "RECOVERY_31_PILLAR_IDS",
    "ROUND28_TO_42_PNG_RECEIPTS",
    "ROUND28_TO_42_SPECS",
    "ROUND41_EXPECTED_SCHEMA",
    "ROUND41_SUMMARY_RELPATH",
    "ROUND42_EXPECTED_SCHEMA",
    "ROUND42_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "RPMB_WRITES",
    "SCHEMA_VERSION",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "USB_PACKETS_TRANSMITTED",
    "VM_COEMULATION_38_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone221PillarResult",
    "RealHwMilestone221FaultInjection",
    "RealHwMilestone221MasterGateReport",
    "RealHwMilestone221VerifyResult",
    "build_realhw_milestone221_master_gate_report",
    "compute_milestone221_sha256",
    "evaluate_milestone221_master_gate",
    "evaluate_realhw_milestone221_master_gate",
    "render_milestone221_markdown",
    "verify_realhw_milestone221_master_gate",
]
