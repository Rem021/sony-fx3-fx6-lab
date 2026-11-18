"""Grand Milestone Phase 295 — 6-Pillar Real-Hardware `ILME-FX3 Ver. 7.02` Master Gate (`realhw_milestone295_master_gate_v1`).

Unites ALL Wave 21–52+ Real-Hardware Main Track subsystems (Phases 134–294) and ALL
31+ live Sony ILME-FX3 `Ver. 7.02` (`Linux 4.9.337-scel+`) ARM64 QEMU Rehearsal
Rounds (`Rounds 28..58+`, `>= 93` sub-runs `r28a..r58c+`, and `>= 62` `< 50 KiB` /
`51,200 B` sanitized PNG receipts) into a single tamper-evident, fail-closed SHA-256
certificate executing in `< 5.0s` per mode across both `LOCAL_DONOR_O_RDONLY` and
`CLEAN_ROOM_SYNTHETIC` (`FX3_FX6_FORCE_CLEAN_ROOM=1`) while keeping
`verify-milestone-90/110/130/147/175/193/209/221/233/254/264` and all 10 bench
readiness preflights (`Ph186`..`Ph291`) 100% intact and forward-compatible via `>=`
lower bounds:

- `P1` (`SAFETY_124PLUS_GATE_REALHW_MASTER_PREFLIGHT`):
  Dynamically discovers the highest available `evaluate_<N>gate_preflight` in
  `fx3_safety` (`N >= 124`, baseline `evaluate_124gate_preflight` and auto-discovering
  `126+`), verifying `>= N - 3` passed offline (`3` Tier-0 hardware bench gates
  `G10..G12` fail-closed offline) and `N/N` passed in `--simulate-bench-dry-run`
  covering `G103..G124+` (Waves 42–52+), with `overall_ready_for_hardware_attach == False`,
  `persistent_emmc_writes_authorized == False`, `cross_model_flash_authorized == False`,
  `usb_packets_transmitted == 0`, and `raw_firmware_bytes_leaked == 0`.
- `P2` (`FIFTY_PLUS_PILLAR_RECOVERY_MASTER_VAULT`):
  Dynamically discovers the highest available
  `evaluate_realhw_<M>pillar_recovery_master` in `fx3_recovery` (`M >= 50`, baseline
  `evaluate_realhw_50pillar_recovery_master` and auto-discovering `51+`), verifying
  `M/M` passed (`all_passed == True`), `cnflasha_userspace_write_blocked == True`,
  `otp_fuse_touches == 0`, `rpmb_counter_increments == 0`,
  `passive_tx_bytes_emitted == 0`, `physical_usb_packets_emitted == 0`, and
  `raw_firmware_bytes_leaked == 0`.
- `P3` (`FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS`):
  Verifies all `>= 45` `fx3_firmware_lab` auditors plus dynamic discovery of any
  newly merged `46th+` `realhw_*_auditor.py`, locking `raw_firmware_bytes_leaked == 0`,
  `e_nd_actuator_tx_count == 0`, and `calibration_mutation_bytes == 0`.
- `P4` (`FIFTY_EIGHT_PLUS_STAGE_VM_HIL_COEMULATION`):
  Runs `fx3_vm_coemulation_suite` with all stages enabled (`>= 58` stages through
  `stage58` Wave-48, dynamically discovering `Stage 59+`), locking
  `raw_firmware_bytes_leaked == 0`, `physical_device_writes == 0`, and
  `emmc_corruptions == 0`.
- `P5` (`DECUPLE_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH291`):
  Verifies `Phase 136`, `Phase 143`, `Phase 154`, AND all `10/10` Physical Bench
  Readiness Verifiers (`Ph186`, `Ph204`, `Ph216`, `Ph227`, `Ph248`, `Ph261`,
  `Ph275` `file-settings-gamma-assist-focus-mag-and-videolight`, `Ph279`
  `usb-mode-hdmi-info-protect-and-network-reset`, `Ph284`
  `pp-scinetone-wb-metering-and-shutter-type`, AND `Ph291`
  `focus-area-zoom-dci4k-and-sensor-cleaning`) return
  `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` offline and
  `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` in simulated dry-run, with
  `overall_ready_for_hardware_attach == False`, `16/16 H0 == H3`, and
  `raw_firmware_bytes_leaked == 0`.
- `P6` (`REAL_FX3_702_QEMU_ROUNDS_28_TO_58_PLUS_AND_PNG_RECEIPTS`):
  Verifies `>= 31` live `ILME-FX3 Ver. 7.02` ARM64 QEMU rounds through `Round 58`
  (`r28..r58+`, dynamically discovering `r59+`), `>= 93` live sub-runs, `>= 62`
  sanitized PNG receipts (`< 51,200` bytes each), `16/16 H0 == H3`,
  `emmc_write_count == 0`, and `raw_firmware_bytes_leaked == 0`.
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
from .realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier import (  # noqa: E402
    evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness,
    verify_phase275_report,
)
from .realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier import (  # noqa: E402
    evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness,
    verify_phase291_report,
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
    RealHwMilestone254FaultInjection,
    _96GATE_EXTRA_FAULT_FIELDS,
    _check_vm_stage45_to_47_redlines,
    _effective_m233_faults,
    _evaluate_pillar_3 as _eval_m254_p3,
    _worker_phase248,
)
from .realhw_milestone264_master_gate import (  # noqa: E402
    MILESTONE264_SCHEMA_VERSION,
    ROUND28_TO_52_PNG_RECEIPTS,
    ROUND28_TO_52_SPECS,
    VM_COEMULATION_50_STAGE_KEYS,
    RealHwMilestone264FaultInjection,
    _102GATE_EXTRA_FAULT_FIELDS,
    _effective_m254_faults,
    _evaluate_pillar_4 as _eval_m264_p4,
    _evaluate_pillar_5 as _eval_m264_p5,
    _worker_phase261,
)
from .realhw_pp_scinetone_wb_metering_and_shutter_type_verifier import (  # noqa: E402
    evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness,
    verify_phase284_report,
)
from .realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier import (  # noqa: E402
    evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness,
    verify_phase279_report,
)
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_MILESTONE295_SCHEMA: str = "realhw_milestone295_master_gate_v1"
MILESTONE295_SCHEMA_VERSION: str = REALHW_MILESTONE295_SCHEMA
P295_SCHEMA: str = REALHW_MILESTONE295_SCHEMA
SCHEMA_VERSION: str = REALHW_MILESTONE295_SCHEMA
PHASE_295_VERSION: str = "295.0.0"
P295_VERSION: str = PHASE_295_VERSION

CROSS_MODEL_FLASH_AUTHORIZED: bool = False
PNG_MAX_SIZE_BYTES: int = PNG_MAX_SIZE_50KIB_BYTES  # 51,200 B (< 50 KiB BYOF PNG ceiling)
P295_PNG_MAX_SIZE_BYTES: int = PNG_MAX_SIZE_BYTES
P295_PHYSICAL_DEVICE_WRITES: int = PHYSICAL_DEVICE_WRITES
P295_RAW_FIRMWARE_BYTES_LEAKED: int = RAW_FIRMWARE_BYTES_LEAKED

STATUS_MILESTONE_READY: str = "MILESTONE_295_PREBENCH_MASTER_VERIFIED"
P295_STATUS_MILESTONE_READY: str = STATUS_MILESTONE_READY
P295_STATUS_FAIL_CLOSED: str = STATUS_FAIL_CLOSED

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_124PLUS_GATE_REALHW_MASTER_PREFLIGHT"),
    ("P2", "FIFTY_PLUS_PILLAR_RECOVERY_MASTER_VAULT"),
    ("P3", "FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS"),
    ("P4", "FIFTY_EIGHT_PLUS_STAGE_VM_HIL_COEMULATION"),
    ("P5", "DECUPLE_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH291"),
    ("P6", "REAL_FX3_702_QEMU_ROUNDS_28_TO_58_PLUS_AND_PNG_RECEIPTS"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)
P295_PILLAR_SPECS: Tuple[Tuple[str, str], ...] = PILLAR_SPECS
P295_PILLAR_IDS: Tuple[str, ...] = PILLAR_IDS

RECOVERY_50_PILLAR_IDS: Tuple[str, ...] = tuple(fx3_recovery.MASTER_50_PILLAR_IDS)

VM_COEMULATION_58_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_50_STAGE_KEYS,
    "stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil",
    "stage52_realhw_apsc_s35_face_eye_af_version_hil",
    "stage53_realhw_release_wo_card_audio_meter_copyright_hil",
    "stage54_realhw_file_settings_gamma_assist_tcub_hil",
    "stage55_realhw_focus_mag_datetime_videolight_hdmires_hil",
    "stage56_realhw_power_save_monitor_language_volume_delete_hil",
    "stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil",
    "stage58_realhw_pp_scinetone_creativelook_wb_metering_hil",
)

ROUND53_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round53-realhw-display-quality-bt-rmt-mymenu-qemu/summary.json"
)
ROUND54_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round54-realhw-diff-set-still-mv-custom-key-remain-shoot-qemu/summary.json"
)
ROUND55_SUMMARY_RELPATH: str = (
    "reports/2026-11-17-round55-realhw-auto-slow-shutter-hdmi-reccontrol-breathing/summary.json"
)
ROUND56_SUMMARY_RELPATH: str = (
    "reports/2026-11-17-round56-realhw-apsc-s35-face-eye-af-version-qemu/summary.json"
)
ROUND57_SUMMARY_RELPATH: str = (
    "reports/2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu/summary.json"
)
ROUND58_SUMMARY_RELPATH: str = (
    "reports/2026-11-17-round58-realhw-file-settings-gamma-assist-tcub-qemu/summary.json"
)

ROUND53_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round53-realhw-display-quality-bt-rmt-mymenu-qemu-v1"
)
ROUND54_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round54-realhw-diff-set-still-mv-custom-key-remain-shoot-qemu-v1"
)
ROUND55_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round55-realhw-auto-slow-shutter-hdmi-reccontrol-breathing-qemu-v1"
)
ROUND56_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round56-realhw-apsc-s35-face-eye-af-version-qemu-v1"
)
ROUND57_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu-v1"
)
ROUND58_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round58-realhw-file-settings-gamma-assist-tcub-qemu-v1"
)

ROUND28_TO_58_SPECS: Tuple[RoundQemuReceiptSpec, ...] = (
    *ROUND28_TO_52_SPECS,
    RoundQemuReceiptSpec(
        round_num=53,
        summary_relpath=ROUND53_SUMMARY_RELPATH,
        expected_schema=ROUND53_EXPECTED_SCHEMA,
        audit_key="r53_realhw_display_quality_bt_rmt_mymenu_audit",
        audit_bool_keys=(
            "all_3_runs_cnflasha_write_zero",
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r53a_display_quality_standard_high_battery_and_setup_survival_verified",
            "r53a_bt_rmt_ctrl_ir_sircs_lockout_and_network_reset_split_verified",
            "r53a_stageb_big6_sid_0a_exact_346686_pixels_verified",
            "r53b_mymenu_6ops_30items_and_camset01_slot1_ro_persist_verified",
            "r53c_wave39_integrated_stress_346686_pixels_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r53a_display_quality_bt_rmt_big6_schinese", 1),
            ("r53b_mymenu_6ops_camset_persist_guard", 1),
            ("r53c_wave39_integrated_stress_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=54,
        summary_relpath=ROUND54_SUMMARY_RELPATH,
        expected_schema=ROUND54_EXPECTED_SCHEMA,
        audit_key="r54_realhw_diff_set_still_mv_custom_key_remain_shoot_audit",
        audit_bool_keys=(
            "all_3_runs_cnflasha_write_zero",
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r54a_diff_set_8items_asymmetric_and_shutter_angle_override_verified",
            "r54a_stageb_big6_sid_0a_exact_346686_pixels_verified",
            "r54b_custom_key_dial_iso_ei_camset01_slot1_ro_persist_verified",
            "r54c_remain_shoot_still_buffer_evf_less_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r54a_diff_set_still_mv_shutter_angle_big6_schinese", 1),
            ("r54b_custom_key_dial_iso_ei_camset_persist_guard", 1),
            ("r54c_remain_shoot_evf_less_integrated_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=55,
        summary_relpath=ROUND55_SUMMARY_RELPATH,
        expected_schema=ROUND55_EXPECTED_SCHEMA,
        audit_key="r55_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_audit",
        audit_bool_keys=(
            "all_3_runs_cnflasha_write_zero",
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r55a_auto_slow_6locks_angle_disjoint_and_hdmi_nominal_verified",
            "r55a_stageb_big6_sid_0a_exact_346206_pixels_verified",
            "r55b_prerequisite_and_lockout_injections_blocked_fail_closed",
            "r55c_camreset_vs_initialize_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r55a_auto_slow_6locks_hdmi_reccontrol_big6_schinese", 1),
            ("r55b_prerequisite_lockout_injection_guard", 1),
            ("r55c_camreset_vs_initialize_h0_h3_integrated_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=56,
        summary_relpath=ROUND56_SUMMARY_RELPATH,
        expected_schema=ROUND56_EXPECTED_SCHEMA,
        audit_key="r56_realhw_apsc_s35_face_eye_af_version_audit",
        audit_bool_keys=(
            "all_3_runs_cnflasha_write_zero",
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r56a_apsc_s35_hd_4k_lockout_face_eye_af_version_readonly_verified",
            "r56a_stageb_big6_sid_0a_exact_346686_pixels_verified",
            "r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_blocked_fail_closed",
            "r56c_camreset_vs_face_memory_initialize_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r56a_apsc_s35_hd_face_eye_af_version_big6_schinese", 1),
            ("r56b_apsc_4k_raw_cleanhdmi_bodydata_flash_guard", 1),
            ("r56c_camreset_face_memory_initialize_h0_h3_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=57,
        summary_relpath=ROUND57_SUMMARY_RELPATH,
        expected_schema=ROUND57_EXPECTED_SCHEMA,
        audit_key="r57_realhw_release_wo_card_audio_meter_copyright_audit",
        audit_bool_keys=(
            "all_3_runs_cnflasha_write_zero",
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r57a_release_wo_card_lens_audio_5items_disp_copyright_verified",
            "r57a_stageb_big6_sid_0a_exact_346206_pixels_verified",
            "r57b_cardless_movie_lensless_v1_audio_copyright_guard_fail_closed",
            "r57c_camreset_vs_copyright_disp_initialize_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r57a_release_wo_card_lens_audio_meter_copyright_big6_schinese", 1),
            ("r57b_cardless_movie_v1_audio_spoof_copyright_guard", 1),
            ("r57c_camreset_copyright_disp_init_h0_h3_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=58,
        summary_relpath=ROUND58_SUMMARY_RELPATH,
        expected_schema=ROUND58_EXPECTED_SCHEMA,
        audit_key="r58_realhw_file_settings_gamma_assist_tcub_audit",
        audit_bool_keys=(
            "all_3_runs_cnflasha_write_zero",
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r58a_file_settings_camid_gamma_lut_autoreview_tcub_verified",
            "r58a_stageb_big6_sid_0a_exact_346686_pixels_verified",
            "r58b_slot1_dcim_leading_underscore_log_gamma_guard_fail_closed",
            "r58c_camreset_nonresettable_wave44_initialize_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r58a_file_settings_camid_gamma_assist_tcub_big6_schinese", 1),
            ("r58b_slot1_dcim_prefix_log_gamma_assist_guard", 1),
            ("r58c_camreset_file_gamma_tcub_init_h0_h3_big6_schinese", 1),
        ),
    ),
)

ROUND28_TO_58_PNG_RECEIPTS: Dict[int, Tuple[str, str]] = {
    **ROUND28_TO_52_PNG_RECEIPTS,
    53: (
        "reports/2026-11-15-round53-realhw-display-quality-bt-rmt-mymenu-qemu/assets/r53a-display-quality-btrmt-big6-schinese-alpha.png",
        "reports/2026-11-15-round53-realhw-display-quality-bt-rmt-mymenu-qemu/assets/r53a-display-quality-btrmt-big6-schinese-composited.png",
    ),
    54: (
        "reports/2026-11-15-round54-realhw-diff-set-still-mv-custom-key-remain-shoot-qemu/assets/r54a-diff-set-customkey-big6-schinese-alpha.png",
        "reports/2026-11-15-round54-realhw-diff-set-still-mv-custom-key-remain-shoot-qemu/assets/r54a-diff-set-customkey-big6-schinese-composited.png",
    ),
    55: (
        "reports/2026-11-17-round55-realhw-auto-slow-shutter-hdmi-reccontrol-breathing/assets/r55a-auto-slow-hdmi-reccontrol-big6-schinese-alpha.png",
        "reports/2026-11-17-round55-realhw-auto-slow-shutter-hdmi-reccontrol-breathing/assets/r55a-auto-slow-hdmi-reccontrol-big6-schinese-composited.png",
    ),
    56: (
        "reports/2026-11-17-round56-realhw-apsc-s35-face-eye-af-version-qemu/assets/r56a-apsc-s35-face-eye-af-big6-schinese-alpha.png",
        "reports/2026-11-17-round56-realhw-apsc-s35-face-eye-af-version-qemu/assets/r56a-apsc-s35-face-eye-af-big6-schinese-composited.png",
    ),
    57: (
        "reports/2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu/assets/r57a-release-wo-card-audio-meter-big6-schinese-alpha.png",
        "reports/2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu/assets/r57a-release-wo-card-audio-meter-big6-schinese-composited.png",
    ),
    58: (
        "reports/2026-11-17-round58-realhw-file-settings-gamma-assist-tcub-qemu/assets/r58a-file-settings-gamma-assist-big6-schinese-alpha.png",
        "reports/2026-11-17-round58-realhw-file-settings-gamma-assist-tcub-qemu/assets/r58a-file-settings-gamma-assist-big6-schinese-composited.png",
    ),
}

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_VM_STAGE_KEY_RE = re.compile(r"^stage(\d+)_")
_ROUND_DIR_RE = re.compile(r"-round(\d+)-")
_SAFETY_EVAL_RE = re.compile(r"^evaluate_(\d+)gate_preflight$")
_RECOVERY_EVAL_RE = re.compile(r"^evaluate_realhw_(\d+)pillar_recovery_master$")
_MASTER_REPORT_KEY_RE = re.compile(r"^master_(\d+)_report$")
_G_RESULT_KEY_RE = re.compile(r"^g(\d+)_result$")
_GATE_ID_NUM_RE = re.compile(r"^G(\d+)_")

_NEGATIVE_AUDIT_BOOL_KEYS: frozenset[str] = frozenset(
    {
        "fx3_has_var_shutter",
        "fx3_has_builtin_evf",
        "fx3_has_builtin_end_filter",
        "overall_ready_for_hardware_attach",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "isp_write_authorized",
        "cross_model_flash_authorized",
    }
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealHwMilestone295FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 Wave 42–52+ gates (G103..G124+) + persistent-write lock
    p1_apsc_s35_face_eye_af_kwargs: Optional[Mapping[str, Any]] = None
    p1_version_bodydata_kwargs: Optional[Mapping[str, Any]] = None
    p1_release_audio_disp_kwargs: Optional[Mapping[str, Any]] = None
    p1_copyright_info_kwargs: Optional[Mapping[str, Any]] = None
    p1_file_settings_kwargs: Optional[Mapping[str, Any]] = None
    p1_gamma_assist_tcub_kwargs: Optional[Mapping[str, Any]] = None
    p1_focus_mag_peaking_kwargs: Optional[Mapping[str, Any]] = None
    p1_area_datetime_videolight_hdmires_kwargs: Optional[Mapping[str, Any]] = None
    p1_power_save_monitor_language_kwargs: Optional[Mapping[str, Any]] = None
    p1_volume_4chmon_delete_confirm_kwargs: Optional[Mapping[str, Any]] = None
    p1_usb_mode_hdmi_info_kwargs: Optional[Mapping[str, Any]] = None
    p1_protect_and_network_reset_kwargs: Optional[Mapping[str, Any]] = None
    p1_pp_creativelook_dro_kwargs: Optional[Mapping[str, Any]] = None
    p1_wb_metering_kwargs: Optional[Mapping[str, Any]] = None
    p1_raw_heif_colorspace_kwargs: Optional[Mapping[str, Any]] = None
    p1_shutter_nr_drive_kwargs: Optional[Mapping[str, Any]] = None
    p1_focus_area_zoom_kwargs: Optional[Mapping[str, Any]] = None
    p1_iso_minss_flash_kwargs: Optional[Mapping[str, Any]] = None
    p1_dci4k_aspect_kwargs: Optional[Mapping[str, Any]] = None
    p1_custom_hold_camset_photo_kwargs: Optional[Mapping[str, Any]] = None
    p1_sensor_cleaning_ev_comp_kwargs: Optional[Mapping[str, Any]] = None
    p1_focus_mode_playback_rotate_kwargs: Optional[Mapping[str, Any]] = None
    p1_request_persistent_writes: bool = False

    # P2 >= 50-pillar recovery master + cnflasha RO + zero-touch redlines
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

    # P4 >= 58 VM HIL stages (Stages 51..58 + forward-compat 59+)
    p4_stage51_autoslow_hdmi_breathing_faults: int = 0
    p4_stage52_apsc_face_eye_version_faults: int = 0
    p4_stage53_release_audio_copyright_faults: int = 0
    p4_stage54_file_settings_gamma_tcub_faults: int = 0
    p4_stage55_focus_mag_videolight_hdmires_faults: int = 0
    p4_stage56_power_save_bklang_volume_delete_faults: int = 0
    p4_stage57_usb_mode_hdmi_protect_nw_reset_faults: int = 0
    p4_stage58_pp_scinetone_wb_metering_faults: int = 0
    p4_physical_device_writes_override: int = 0
    p4_raw_firmware_bytes_leaked_override: int = 0

    # P5 Decuple bench readiness preflights (Ph186..Ph291)
    p5_inject_p186_h0_h3_drift: bool = False
    p5_inject_p204_h0_h3_drift: bool = False
    p5_inject_p216_h0_h3_drift: bool = False
    p5_inject_p227_h0_h3_drift: bool = False
    p5_inject_p248_h0_h3_drift: bool = False
    p5_inject_p261_h0_h3_drift: bool = False
    p5_inject_p275_file_gamma_focusmag_vault_fault: bool = False
    p5_inject_p275_h0_h3_drift: bool = False
    p5_inject_p279_usb_hdmi_protect_nw_fault: bool = False
    p5_inject_p279_h0_h3_drift: bool = False
    p5_inject_p284_pp_wb_raw_shutter_fault: bool = False
    p5_inject_p284_h0_h3_drift: bool = False
    p5_inject_p291_focus_zoom_dci4k_clean_fault: bool = False
    p5_inject_p291_h0_h3_drift: bool = False
    p5_inject_p291_usb_packets_override: int = 0
    p5_inject_p291_passive_tx_bytes_override: int = 0

    # P6 Rounds 28..58+ live QEMU kernel rehearsal & < 50 KiB (51,200 B) PNG receipts
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

    # Optional upstream Milestone 264 fault injection pass-through
    m264_faults: Optional[RealHwMilestone264FaultInjection] = None


@dataclass(frozen=True)
class Milestone295PillarResult:
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
class RealHwMilestone295MasterGateReport:
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
    pillars: Tuple[Milestone295PillarResult, ...]
    gate124_total_gates: int
    gate124_offline_verified: int
    gate124_simulated_verified: int
    gate124_all_verified: bool
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
    milestone295_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class RealHwMilestone295VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone295_sha256: str
    observed_milestone295_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_milestone295_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `RealHwMilestone295MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone295_sha256", None)
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
    """Discover highest `evaluate_<N>gate_preflight` in `fx3_safety` (`N >= 124`)."""
    best_n = 0
    best_fn: Optional[Callable[..., Any]] = None
    for attr in dir(safety_mod):
        m = _SAFETY_EVAL_RE.match(attr)
        if not m:
            continue
        n_val = int(m.group(1))
        if n_val >= 124 and n_val > best_n:
            cand = getattr(safety_mod, attr, None)
            if callable(cand):
                best_n = n_val
                best_fn = cand
    if best_fn is not None:
        return best_n, best_fn
    return 124, fx3_safety.evaluate_124gate_preflight


def _discover_highest_recovery_master(
    recovery_mod: Any = fx3_recovery,
) -> Tuple[int, Callable[..., Any], Tuple[str, ...]]:
    """Discover highest `evaluate_realhw_<M>pillar_recovery_master` (`M >= 50`)."""
    best_m = 0
    best_fn: Optional[Callable[..., Any]] = None
    for attr in dir(recovery_mod):
        m = _RECOVERY_EVAL_RE.match(attr)
        if not m:
            continue
        m_val = int(m.group(1))
        if m_val >= 50 and m_val > best_m:
            cand = getattr(recovery_mod, attr, None)
            if callable(cand):
                best_m = m_val
                best_fn = cand
    if best_fn is None:
        best_m = 50
        best_fn = fx3_recovery.evaluate_realhw_50pillar_recovery_master
    ids_raw = getattr(recovery_mod, f"MASTER_{best_m}_PILLAR_IDS", None)
    if ids_raw is None:
        ids_raw = getattr(recovery_mod, "MASTER_50_PILLAR_IDS", RECOVERY_50_PILLAR_IDS)
    return best_m, best_fn, tuple(str(x) for x in ids_raw)


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 5.0s per mode)
# ---------------------------------------------------------------------------

_124GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_apsc_s35_face_eye_af_kwargs", "apsc_s35_face_eye_af_kwargs"),
    ("p1_version_bodydata_kwargs", "version_bodydata_kwargs"),
    ("p1_release_audio_disp_kwargs", "release_audio_disp_kwargs"),
    ("p1_copyright_info_kwargs", "copyright_info_kwargs"),
    ("p1_file_settings_kwargs", "file_settings_kwargs"),
    ("p1_gamma_assist_tcub_kwargs", "gamma_assist_tcub_kwargs"),
    ("p1_focus_mag_peaking_kwargs", "focus_mag_peaking_kwargs"),
    ("p1_area_datetime_videolight_hdmires_kwargs", "area_datetime_videolight_hdmires_kwargs"),
    ("p1_power_save_monitor_language_kwargs", "power_save_monitor_language_kwargs"),
    ("p1_volume_4chmon_delete_confirm_kwargs", "volume_4chmon_delete_confirm_kwargs"),
    ("p1_usb_mode_hdmi_info_kwargs", "usb_mode_hdmi_info_kwargs"),
    ("p1_protect_and_network_reset_kwargs", "protect_and_network_reset_kwargs"),
    ("p1_pp_creativelook_dro_kwargs", "pp_creativelook_dro_kwargs"),
    ("p1_wb_metering_kwargs", "wb_metering_kwargs"),
    ("p1_raw_heif_colorspace_kwargs", "raw_heif_colorspace_kwargs"),
    ("p1_shutter_nr_drive_kwargs", "shutter_nr_drive_kwargs"),
    ("p1_focus_area_zoom_kwargs", "focus_area_zoom_kwargs"),
    ("p1_iso_minss_flash_kwargs", "iso_minss_flash_kwargs"),
    ("p1_dci4k_aspect_kwargs", "dci4k_aspect_kwargs"),
    ("p1_custom_hold_camset_photo_kwargs", "custom_hold_camset_photo_kwargs"),
    ("p1_sensor_cleaning_ev_comp_kwargs", "sensor_cleaning_ev_comp_kwargs"),
    ("p1_focus_mode_playback_rotate_kwargs", "focus_mode_playback_rotate_kwargs"),
)


def _effective_m264_faults(
    faults: RealHwMilestone295FaultInjection,
) -> RealHwMilestone264FaultInjection:
    base = faults.m264_faults or RealHwMilestone264FaultInjection()
    need_186 = faults.p5_inject_p186_h0_h3_drift and not base.p5_inject_p186_h0_h3_drift
    need_204 = faults.p5_inject_p204_h0_h3_drift and not base.p5_inject_p204_h0_h3_drift
    need_216 = faults.p5_inject_p216_h0_h3_drift and not base.p5_inject_p216_h0_h3_drift
    need_227 = faults.p5_inject_p227_h0_h3_drift and not base.p5_inject_p227_h0_h3_drift
    need_248 = faults.p5_inject_p248_h0_h3_drift and not base.p5_inject_p248_h0_h3_drift
    need_261 = faults.p5_inject_p261_h0_h3_drift and not base.p5_inject_p261_h0_h3_drift
    need_p3 = (
        faults.p3_filesettings_tcregen_reclamp_guard_fault
        and not base.p3_filesettings_tcregen_reclamp_guard_fault
    )
    if need_186 or need_204 or need_216 or need_227 or need_248 or need_261 or need_p3:
        d = asdict(base)
        d["m254_faults"] = base.m254_faults
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
        if need_261:
            d["p5_inject_p261_h0_h3_drift"] = True
        if need_p3:
            d["p3_filesettings_tcregen_reclamp_guard_fault"] = True
        return RealHwMilestone264FaultInjection(**d)
    return base


def _fault_to_124gate_worker_dict(faults: RealHwMilestone295FaultInjection) -> Dict[str, Any]:
    m264_f = _effective_m264_faults(faults)
    m254_f = _effective_m254_faults(m264_f)
    m233_f = _effective_m233_faults(m254_f)
    m221_f = _effective_m221_faults(m233_f)
    m209_f = _effective_m209_faults(m221_f)
    m193_f = _effective_m193_faults(m209_f)
    out: Dict[str, Any] = {
        "p1_request_persistent_writes": bool(
            faults.p1_request_persistent_writes
            or m264_f.p1_request_persistent_writes
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
        val = getattr(m264_f, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    for src_attr, _ in _124GATE_EXTRA_FAULT_FIELDS:
        val = getattr(faults, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    return out


def _extract_nested_g_valid_and_g71_end_tx(rep: Any) -> Tuple[Dict[str, bool], int]:
    """Extract `g63..gN` nested validity flags + `g71` e-ND TX count generically."""
    nested_g_valid: Dict[str, bool] = {}
    g71_end_tx = -1

    # 1. Inspect `rep.gates` for every G63..G<N> gate verdict
    for gobj in getattr(rep, "gates", ()) or ():
        if isinstance(gobj, Mapping):
            gid = str(gobj.get("gate_id", ""))
            m = _GATE_ID_NUM_RE.match(gid)
            if m:
                gnum = int(m.group(1))
                if gnum >= 63:
                    nested_g_valid[f"g{gnum}"] = bool(gobj.get("passed"))

    # 2. Traverse nested `g<K>_result` / `master_<M>_report` dictionaries recursively
    def _walk(obj: Any) -> None:
        nonlocal g71_end_tx
        if obj is None:
            return
        if isinstance(obj, Mapping):
            for k, v in obj.items():
                ks = str(k)
                gm = _G_RESULT_KEY_RE.match(ks)
                if gm:
                    gnum = int(gm.group(1))
                    if gnum >= 63 and isinstance(v, Mapping):
                        tag = f"g{gnum}"
                        is_valid = v.get("valid") is True
                        nested_g_valid[tag] = (
                            nested_g_valid[tag] and is_valid
                            if tag in nested_g_valid
                            else is_valid
                        )
                        if gnum == 71:
                            guard = v.get("big6_noend_camset_slot1_guard", {})
                            if isinstance(guard, Mapping):
                                g71_end_tx = int(guard.get("e_nd_actuator_tx_count", 0))
                elif _MASTER_REPORT_KEY_RE.match(ks):
                    _walk(v)
        else:
            for attr in dir(obj):
                if _G_RESULT_KEY_RE.match(attr) or _MASTER_REPORT_KEY_RE.match(attr):
                    _walk(getattr(obj, attr, None))

    _walk(rep)
    return nested_g_valid, g71_end_tx


def _worker_124plus_gate_single(args: Tuple[str, bool, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, dry_run_sim, fault_dict = args
    repo_root = Path(repo_root_str)
    discovered_n, eval_fn = _discover_highest_safety_gate_evaluator()
    sig = inspect.signature(eval_fn)
    has_varkw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )

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
        *_124GATE_EXTRA_FAULT_FIELDS,
    ):
        val = fault_dict.get(src_attr)
        if val is not None and (has_varkw or dst_kw in sig.parameters):
            kwargs[dst_kw] = val

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
        "cross_model_flash_authorized": bool(
            s.get("cross_model_flash_authorized", False)
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


def _normalize_50plus_pillar_fault_id(
    fault_id: Optional[str],
    pillar_ids: Tuple[str, ...] = RECOVERY_50_PILLAR_IDS,
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


def _worker_recovery_50plus_pillar(args: Tuple[bool, Optional[str]]) -> Dict[str, Any]:
    use_clean_room, fault_pillar = args
    _, eval_fn, pillar_ids = _discover_highest_recovery_master()
    rep = eval_fn(
        force_clean_room=use_clean_room,
        fault_inject_pillar=_normalize_50plus_pillar_fault_id(fault_pillar, pillar_ids),
    )
    return rep.to_dict()


def _worker_pillar_4_295(use_clean_room: bool) -> Dict[str, Any]:
    return run_fx3_vm_coemulation_suite(CoEmulationConfig(force_clean_room=use_clean_room))


def _worker_phase275_279(
    args: Tuple[str, str, bool, Dict[str, Any], Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    fx6_str, fx3_str, use_clean_room, p275_faults, p279_faults = args
    fx6_dir = Path(fx6_str)
    fx3_dir = Path(fx3_str)

    rep275_off = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
    )
    kw275: Dict[str, Any] = {}
    if p275_faults.get("file_gamma_focusmag_vault"):
        kw275["expect_slot1_dcim_mutation_allowed"] = True
        kw275["expect_gamma_assist_active_under_log"] = True
        kw275["expect_focus_mag_allowed_in_raw"] = True
        kw275["expect_slot1_vault_delete_or_format_allowed"] = True
    if p275_faults.get("h0_h3_drift"):
        kw275["simulated_h0_h3_drifted_surfaces"] = 1
    rep275_sim = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw275,
    )

    rep279_off = evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
    )
    kw279: Dict[str, Any] = {}
    if p279_faults.get("usb_hdmi_protect_nw"):
        kw279["expect_usb_streaming_uvc"] = True
        kw279["expect_4k_hdmi_during_internal_log_or_pplut"] = True
        kw279["slot1_format_mode"] = "QUICK"
    if p279_faults.get("h0_h3_drift"):
        kw279["simulated_h0_h3_drifted_surfaces"] = 1
    rep279_sim = evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw279,
    )
    return rep275_off.to_dict(), rep275_sim.to_dict(), rep279_off.to_dict(), rep279_sim.to_dict()


def _worker_phase284_291(
    args: Tuple[str, str, bool, Dict[str, Any], Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    fx6_str, fx3_str, use_clean_room, p284_faults, p291_faults = args
    fx6_dir = Path(fx6_str)
    fx3_dir = Path(fx3_str)

    rep284_off = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
    )
    kw284: Dict[str, Any] = {}
    if p284_faults.get("pp_wb_raw_shutter"):
        kw284["expect_creative_look_or_dro_active_with_pp_or_log"] = True
        kw284["expect_metering_changes_cine_ei_iso"] = True
        kw284["expect_lossless_comp_raw"] = True
        kw284["expect_shutter_type_auto"] = True
    if p284_faults.get("h0_h3_drift"):
        kw284["simulated_h0_h3_drifted_surfaces"] = 1
    rep284_sim = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw284,
    )

    rep291_off = evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
    )
    kw291: Dict[str, Any] = {}
    if p291_faults.get("focus_zoom_dci4k_clean"):
        kw291["expect_tracking_focus_area_in_movie"] = True
        kw291["expect_24p_no_reboot"] = True
        kw291["sensor_cleaning_requested"] = True
        kw291["battery_soc_pct"] = 20.0
    if p291_faults.get("h0_h3_drift"):
        kw291["simulated_h0_h3_drifted_surfaces"] = 1
    rep291_sim = evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw291,
    )
    return rep284_off.to_dict(), rep284_sim.to_dict(), rep291_off.to_dict(), rep291_sim.to_dict()


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1..P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
) -> Milestone295PillarResult:
    errors: List[str] = []
    off_total = int(raw_off["total_gates"])
    off_ver = int(raw_off["verified_gates"])
    sim_total = int(raw_sim["total_gates"])
    sim_ver = int(raw_sim["verified_gates"])

    if (
        off_total < 124
        or off_ver < off_total - 3
        or off_ver != off_total - 3
        or int(raw_off["blocked_or_pending_gates"]) != 3
        or raw_off["overall_ready_for_hardware_attach"] is not False
        or raw_off["hardware_live_attachment_authorized"] is not False
        or raw_off.get("cross_model_flash_authorized") is not False
        or not bool(raw_off.get("offline_minus3_verified", False))
    ):
        errors.append(
            f"p1_offline: expected {off_total - 3}/{off_total} (>=121/124, 3 Tier-0 gates fail-closed) "
            f"and hardware_attach=False, got {off_ver}/{off_total}"
        )

    if (
        sim_total < 124
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
            f"p1_simulated: expected {sim_total}/{sim_total} (>=124/124) with all_n_gates_verified=True "
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
    if len(nested_sim) < (124 - 62):
        errors.append(
            f"p1: expected >=62 nested G63..G124+ gates, got {len(nested_sim)}"
        )

    passed = len(errors) == 0
    evidence = {
        "schema": raw_sim["schema"],
        "discovered_gate_count": int(raw_sim.get("discovered_gate_count", sim_total)),
        "offline_total_gates": off_total,
        "offline_verified_gates": off_ver,
        "simulated_total_gates": sim_total,
        "simulated_verified_gates": sim_ver,
        "all_124plus_gates_verified": bool(raw_sim.get("all_n_gates_verified", False)),
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
    return Milestone295PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_124PLUS_GATE_REALHW_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"124+-Gate Safety: offline={off_ver}/{off_total} (3 Tier-0 gates fail-closed), "
            f"simulated={sim_ver}/{sim_total} (G103..G{sim_total} Waves 42-52+, "
            f"cross_model_flash={raw_sim.get('cross_model_flash_authorized')}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    rec_50plus: Mapping[str, Any],
    faults: RealHwMilestone295FaultInjection,
) -> Tuple[Milestone295PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    p_count = int(rec_50plus.get("pillar_count", 0))
    p_passed = int(rec_50plus.get("pillars_passed", 0))
    rec_status = str(rec_50plus.get("status", ""))

    cnflasha_blocked = bool(rec_50plus.get("cnflasha_userspace_write_blocked", False)) and not bool(
        faults.p2_cnflasha_write_unblocked_fault
    )
    otp = (
        max(
            int(rec_50plus.get("otp_fuse_writes", 0) or 0),
            int(rec_50plus.get("otp_fuse_touches", -1)),
        )
        + int(faults.p2_otp_fuse_touches_override)
    )
    rpmb = int(rec_50plus.get("rpmb_counter_increments", -1)) + int(
        faults.p2_rpmb_counter_increments_override
    )
    ptx = int(rec_50plus.get("passive_tx_bytes_emitted", -1)) + int(
        faults.p2_passive_tx_bytes_override
    )
    usb_pkts = int(rec_50plus.get("physical_usb_packets_emitted", -1)) + int(
        faults.p2_physical_usb_packets_override
    )
    dev_writes = int(rec_50plus.get("physical_device_writes", -1)) + int(
        faults.p2_physical_device_writes_override
    )
    leaked = int(rec_50plus.get("raw_firmware_bytes_leaked", -1)) + int(
        faults.p2_raw_firmware_bytes_leaked_override
    )

    p50a = rec_50plus.get("pillar50_a_pp_scinetone_creativelook_dro_vault", {})
    p50b = rec_50plus.get("pillar50_b_wb_camset_exclusion_metering_vault", {})
    p50a_ok = True if p_count > 50 and not p50a else (isinstance(p50a, Mapping) and bool(p50a.get("passed")))
    p50b_ok = True if p_count > 50 and not p50b else (isinstance(p50b, Mapping) and bool(p50b.get("passed")))

    expected_status = f"VERIFIED_{p_count}OF{p_count}_PILLAR_RECOVERY_MASTER"
    status_ok = rec_status == expected_status and p_count >= 50 and p_passed == p_count
    pillars_seq = rec_50plus.get("pillars", ())
    pillars_items_ok = isinstance(pillars_seq, Sequence) and len(pillars_seq) >= 50 and all(
        isinstance(item, Mapping) and bool(item.get("passed")) for item in pillars_seq
    )

    if (
        not bool(rec_50plus.get("all_passed"))
        or not status_ok
        or not pillars_items_ok
        or p_count < 50
        or p_passed < 50
        or p_passed != p_count
        or not p50a_ok
        or not p50b_ok
    ):
        errors.append(
            f"p2_50plus_pillar: expected >=50/50 {expected_status}, "
            f"got {p_passed}/{p_count} (status={rec_status!r}, 50A={p50a_ok}, 50B={p50b_ok})"
        )

    zero_violation_keys = (
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
        "legacy_mf_assist_spoof_events",
        "still_movie_initial_mag_couplings",
        "movie_af_in_focus_mag_events",
        "hdmi_clean_feed_focus_mag_or_peaking_leak_pixels",
        "movie_sq_af_illuminator_fire_events",
        "legacy_datetime_setup_spoof_events",
        "unsolicited_rtc_timezone_jump_events",
        "mishoe_5v_overcurrent_events",
        "hdmi_res_log_internal_rec_2160p_bypass_events",
        "slot1_vault_mutation_events",
        "slot1_vault_folder_mutation_events",
        "slot1_vault_folder_mutation_bytes",
        "movie_custom_folder_or_title_overflow_events",
        "still_prefix_underscore_lead_or_len_violations",
        "gamma_assist_log_lockout_bypass_events",
        "gamma_assist_external_hdmi_leak_events",
        "tcub_camera_reset_wipe_or_format_violations",
        "e_nd_actuator_tx_count",
        "cardless_unrecorded_production_violations",
        "legacy_v1_audio_level_menu_spoof_events",
        "photographer_copyright_pii_leaked_bytes",
        "copyright_char_overflow_or_movie_mutation_events",
        "slot1_copyright_vault_mutation_bytes",
        "apsc_s35_4k_or_raw_bypass_events",
        "ai_unit_subject_recog_spoof_events",
        "hdmi_clean_feed_eye_frame_baked_pixels",
        "version_dialog_flash_writes",
        "slot1_bodydata_vault_mutation_bytes",
    )
    violations_nonzero = any(int(rec_50plus.get(vk, 0)) != 0 for vk in zero_violation_keys)

    if (
        cnflasha_blocked is not True
        or otp != 0
        or rpmb != 0
        or ptx != 0
        or usb_pkts != 0
        or dev_writes != 0
        or leaked != 0
        or violations_nonzero
        or rec_50plus.get("slot1_format_hard_locked", True) is not True
        or rec_50plus.get("fx3_has_var_shutter", False) is not False
        or rec_50plus.get("fx3_has_builtin_evf", False) is not False
        or rec_50plus.get("fx3_has_builtin_end_filter", False) is not False
        or rec_50plus.get("hardware_live_attachment_authorized", False) is not False
        or rec_50plus.get("el3_payload_transmit_authorized") is not False
        or rec_50plus.get("isp_write_authorized") is not False
        or rec_50plus.get("spi_nor_write_authorized") is not False
        or rec_50plus.get("persistent_emmc_writes_authorized") is not False
        or rec_50plus.get("persistent_write_release") is not False
    ):
        errors.append(
            f"p2_redlines: zero-touch / cnflasha RO invariant violated "
            f"(cnflasha_blocked={cnflasha_blocked}, otp={otp}, rpmb={rpmb}, ptx={ptx}, "
            f"usb_pkts={usb_pkts}, dev_writes={dev_writes}, leaked={leaked})"
        )

    passed = len(errors) == 0
    sha_key = f"master_{p_count}pillar_sha256"
    evidence = {
        "status": rec_status,
        "pillar_count": p_count,
        "pillars_passed": p_passed,
        "cnflasha_userspace_write_blocked": cnflasha_blocked,
        "fx3_has_builtin_evf": bool(rec_50plus.get("fx3_has_builtin_evf", False)),
        "fx3_has_var_shutter": bool(rec_50plus.get("fx3_has_var_shutter", False)),
        "fx3_has_builtin_end_filter": bool(rec_50plus.get("fx3_has_builtin_end_filter", False)),
        "slot1_format_hard_locked": bool(rec_50plus.get("slot1_format_hard_locked", True)),
        "pillar50_a_pp_scinetone_creativelook_dro_passed": p50a_ok,
        "pillar50_b_wb_camset_exclusion_metering_passed": p50b_ok,
        "otp_fuse_touches": otp,
        "rpmb_counter_increments": rpmb,
        "passive_tx_bytes_emitted": ptx,
        "physical_usb_packets_emitted": usb_pkts,
        "physical_device_writes": dev_writes,
        "raw_firmware_bytes_leaked": leaked,
        "master_recovery_sha256": str(
            rec_50plus.get(sha_key, rec_50plus.get("master_50pillar_sha256", ""))
        ),
    }
    pillar = Milestone295PillarResult(
        pillar_id="P2",
        pillar_name="FIFTY_PLUS_PILLAR_RECOVERY_MASTER_VAULT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"50+-Pillar Recovery ({rec_status}): {p_passed}/{p_count} (>=50 required; "
            f"Pillars 45..{p_count} ReleaseWoCard-Copyright/FileSettings-Gamma-TCUB/"
            f"FocusMag-VideoLight/PowerSave-4chAudio/USBMode-HDMIInfo-NWReset/"
            f"PP11-SCinetone-WB-Metering), cnflasha_ro={cnflasha_blocked}, OTP={otp}, "
            f"RPMB={rpmb}, passive_tx={ptx} {'PASS' if passed else 'FAIL_CLOSED'}"
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
    faults: RealHwMilestone295FaultInjection,
) -> Tuple[Milestone295PillarResult, Dict[str, Any]]:
    m264_f = _effective_m264_faults(faults)
    m254_p3, meta_45 = _eval_m254_p3(auditors, _effective_m254_faults(m264_f))
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
    pillar = Milestone295PillarResult(
        pillar_id="P3",
        pillar_name="FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {auditors_passed}/{auditors_total} auditors (>=45 required; "
            f"forward-compat 46+ dynamic discovery), e_nd_tx={end_tx}, cal_mut={cal_mut}B, "
            f"leaked={total_leaked}B {'PASS' if passed else 'FAIL_CLOSED'}"
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
    faults: RealHwMilestone295FaultInjection,
) -> Tuple[Milestone295PillarResult, Dict[str, Any]]:
    m264_f = _effective_m264_faults(faults)
    m264_p4, meta_50 = _eval_m264_p4(vm_rep, m264_f)
    errors: List[str] = [
        e for e in m264_p4.errors if not e.startswith("p4: expected >= 50 VM stages")
    ]
    stage_statuses: Dict[str, bool] = dict(m264_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_58_STAGE_KEYS[50:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if (
            not ok
            and f"p4: forward-compat VM stage {skey} failed" not in errors
            and f"p4: VM co-emulation {skey} failed" not in errors
        ):
            errors.append(f"p4: VM co-emulation {skey} failed")

    # Forward-compatible discovery of Stage 59+ keys
    for skey, sobj in sorted(vm_rep.items()):
        m = _VM_STAGE_KEY_RE.match(str(skey))
        if m and int(m.group(1)) >= 59 and skey not in stage_statuses and isinstance(sobj, Mapping):
            ok = bool(sobj.get("all_checks_passed"))
            stage_statuses[skey] = ok
            if not ok:
                errors.append(f"p4: forward-compat VM stage {skey} failed")

    stage51_to_58_specs: Tuple[Tuple[str, str, Tuple[str, ...], int], ...] = (
        (
            "stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil",
            "51/51",
            (
                "auto_slow_shutter_lockout_bypass_events",
                "auto_slow_shutter_angle_overlap_events",
                "breathing_comp_raw_or_240p_bypass_events",
                "hdmi_rec_ctrl_without_tc_violations",
            ),
            int(faults.p4_stage51_autoslow_hdmi_breathing_faults),
        ),
        (
            "stage52_realhw_apsc_s35_face_eye_af_version_hil",
            "52/52",
            (
                "ai_coprocessor_subject_spoof_events",
                "apsc_s35_4k_or_raw_bypass_events",
                "bodydata_flash_execution_events",
                "face_memory_camera_reset_wipe_events",
                "hdmi_clean_feed_eye_frame_baked_pixels",
            ),
            int(faults.p4_stage52_apsc_face_eye_version_faults),
        ),
        (
            "stage53_realhw_release_wo_card_audio_meter_copyright_hil",
            "53/53",
            (
                "camset_copyright_pii_leaked_bytes",
                "cardless_unrecorded_production_violations",
                "copyright_char_overflow_or_movie_mutation_events",
                "e_nd_actuator_tx_count",
                "hdmi_clean_feed_audio_meter_baked_pixels",
                "legacy_v1_audio_level_menu_spoof_events",
                "photographer_copyright_pii_leaked_bytes",
                "slot1_copyright_vault_mutation_bytes",
            ),
            int(faults.p4_stage53_release_audio_copyright_faults),
        ),
        (
            "stage54_realhw_file_settings_gamma_assist_tcub_hil",
            "54/54",
            (
                "gamma_assist_log_lockout_bypass_events",
                "hdmi_gamma_assist_baked_frames",
                "slot1_vault_folder_mutation_events",
                "still_prefix_leading_underscore_bypass_events",
                "tc_24p_or_pal_df_violation_events",
                "tcub_camera_settings_reset_wipe_events",
                "title_name_37char_overflow_events",
            ),
            int(faults.p4_stage54_file_settings_gamma_tcub_faults),
        ),
        (
            "stage55_realhw_focus_mag_datetime_videolight_hdmires_hil",
            "55/55",
            (
                "af_illuminator_movie_or_sq_fire_events",
                "creators_app_rtc_sync_jump_events",
                "hdmi_clean_feed_mag_or_peaking_leaked_pixels",
                "hdmi_log_1080p_downshift_bypass_events",
                "legacy_date_time_setup_spoof_events",
                "legacy_mf_assist_spoof_events",
                "mishoe_5v_900ma_overcurrent_events",
            ),
            int(faults.p4_stage55_focus_mag_videolight_hdmires_faults),
        ),
        (
            "stage56_realhw_power_save_monitor_language_volume_delete_hil",
            "56/56",
            (
                "bk_lang_offset_mismatch_events",
                "four_ch_headphone_routing_violations",
                "headless_hdmi_unexpected_sleep_events",
                "language_count_model_mismatch_events",
                "power_save_monitor_spoof_events",
                "slot1_vault_delete_events",
                "xlr_h1_speaker_feedback_guard_violations",
            ),
            int(faults.p4_stage56_power_save_bklang_volume_delete_faults),
        ),
        (
            "stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil",
            "57/57",
            (
                "fx3_native_uvc_spoof_events",
                "hdmi_clean_feed_override_violations",
                "hdmi_osd_or_clamp_bypass_events",
                "post_reset_airplane_off_rf_leak_events",
                "slot1_vault_format_or_delete_events",
                "tier0_usb_data_enumeration_violations",
            ),
            int(faults.p4_stage57_usb_mode_hdmi_protect_nw_reset_faults),
        ),
        (
            "stage58_realhw_pp_scinetone_creativelook_wb_metering_hil",
            "58/58",
            (
                "metering_spot_link_or_ciz_multi_bypass_events",
                "pp_creative_look_or_reset_wipe_misroute_events",
                "wb_cine_ei_auto_or_camset_custom_leak_events",
            ),
            int(faults.p4_stage58_pp_scinetone_wb_metering_faults),
        ),
    )

    extra_emmc = 0
    extra_wf12 = 0
    extra_end_tx = 0
    for skey, exp_milestone, fault_counters, injected in stage51_to_58_specs:
        sobj = vm_rep.get(skey, {})
        if isinstance(sobj, Mapping):
            extra_emmc += max(0, int(sobj.get("emmc_mutation_bytes", 0)))
            extra_wf12 += max(0, int(sobj.get("wf12_00342260_hits", 0)))
            extra_end_tx += max(0, int(sobj.get("e_nd_actuator_tx_count", 0)))
        counter_sum = injected + sum(
            int(sobj.get(ck, -1)) if isinstance(sobj, Mapping) else -1 for ck in fault_counters
        )
        milestone_ok = isinstance(sobj, Mapping) and sobj.get("milestone") == exp_milestone
        if not _check_vm_stage45_to_47_redlines(sobj) or counter_sum != 0 or not milestone_ok:
            errors.append(
                f"p4: {skey} redlines or milestone ({exp_milestone}) violated (fault_sum={counter_sum})"
            )
            stage_statuses[skey] = False

    vm_raw_leaked = int(meta_50.get("raw_firmware_bytes_leaked", 0)) + int(
        faults.p4_raw_firmware_bytes_leaked_override
    )
    vm_phys_writes = int(meta_50.get("physical_device_writes", 0)) + int(
        faults.p4_physical_device_writes_override
    )
    vm_stages_total = len(stage_statuses)
    vm_stages_passed = sum(1 for v in stage_statuses.values() if v)
    emmc_corruptions = int(meta_50.get("emmc_corruptions", 0)) + extra_emmc
    total_wf12_hits = int(meta_50.get("wf12_00342260_hits", 0)) + extra_wf12
    total_end_tx = int(meta_50.get("e_nd_actuator_tx_count", 0)) + extra_end_tx

    if not (vm_stages_passed >= 58 and vm_stages_passed == vm_stages_total):
        errors.append(
            f"p4: expected >= 58 VM stages and all passing, got {vm_stages_passed}/{vm_stages_total}"
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
    evidence = dict(m264_p4.evidence)
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
            "stage55_digest_sha256": vm_rep.get(
                "stage55_realhw_focus_mag_datetime_videolight_hdmires_hil", {}
            ).get("phase278_audit_digest_sha256"),
            "stage56_digest_sha256": vm_rep.get(
                "stage56_realhw_power_save_monitor_language_volume_delete_hil", {}
            ).get("phase281_audit_digest_sha256"),
            "stage57_digest_sha256": vm_rep.get(
                "stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil", {}
            ).get("phase285_audit_digest_sha256"),
            "stage58_digest_sha256": vm_rep.get(
                "stage58_realhw_pp_scinetone_creativelook_wb_metering_hil", {}
            ).get("phase289_audit_digest_sha256"),
            "stage58_milestone": vm_rep.get(
                "stage58_realhw_pp_scinetone_creativelook_wb_metering_hil", {}
            ).get("milestone"),
        }
    )
    pillar = Milestone295PillarResult(
        pillar_id="P4",
        pillar_name="FIFTY_EIGHT_PLUS_STAGE_VM_HIL_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {vm_stages_passed}/{vm_stages_total} stages (>=58 required; Stages 51..58 "
            f"AutoSlow-APSC-Copyright-FileSettings-FocusMag-PowerSave-USBMode-PP11SCinetone), "
            f"phys_writes={vm_phys_writes}, leaked={vm_raw_leaked}B, emmc_corruptions={emmc_corruptions} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_50)
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


def _check_4group_bench_verifier(
    *,
    tag: str,
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
    verify_fn: Callable[[Mapping[str, Any]], Any],
    cg_keys: Tuple[str, str, str, str],
    errors: List[str],
    extra_usb_override: int = 0,
    extra_passive_override: int = 0,
) -> Dict[str, Any]:
    off_dict = copy.deepcopy(dict(raw_off))
    v_off = verify_fn(off_dict)
    off_ready = bool(off_dict.get("overall_ready_for_hardware_attach", False))
    if (
        not v_off.valid
        or off_dict.get("go_no_go") != GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        or off_dict.get("hardware_live_attachment_authorized") is not False
        or off_ready is not False
        or off_dict.get("tier0_receipt_verified") is not False
        or not bool(off_dict.get("all_4_check_groups_passed"))
        or off_dict.get("sd_physical_media_written") is not False
        or int(off_dict.get("usb_packets_transmitted", -1)) != 0
        or int(off_dict.get("physical_usb_packets_emitted", -1)) != 0
        or int(off_dict.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(off_dict.get("passive_tx_bytes_emitted", -1)) != 0
    ):
        errors.append(
            f"p5_{tag}_off: expected {GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT} "
            f"(got {off_dict.get('go_no_go')}, valid={v_off.valid}, errs={v_off.errors})"
        )

    sim_dict = copy.deepcopy(dict(raw_sim))
    if extra_usb_override:
        sim_dict["usb_packets_transmitted"] = int(
            sim_dict.get("usb_packets_transmitted", 0)
        ) + int(extra_usb_override)
        sim_dict["physical_usb_packets_emitted"] = int(
            sim_dict.get("physical_usb_packets_emitted", 0)
        ) + int(extra_usb_override)
    if extra_passive_override:
        sim_dict["passive_tx_bytes_emitted"] = int(
            sim_dict.get("passive_tx_bytes_emitted", 0)
        ) + int(extra_passive_override)

    v_sim = verify_fn(sim_dict)
    sim_passed = int(sim_dict.get("check_groups_passed", -1))
    sim_pkts = max(
        int(sim_dict.get("usb_packets_transmitted", -1)),
        int(sim_dict.get("physical_usb_packets_emitted", -1)),
    )
    sim_leaked = int(sim_dict.get("raw_firmware_bytes_leaked", -1))
    sim_passive = int(sim_dict.get("passive_tx_bytes_emitted", -1))
    sim_h0_h3 = int(sim_dict.get("h0_equals_h3_count", -1))
    sim_ready = bool(sim_dict.get("overall_ready_for_hardware_attach", False))
    all_cgs_ok = all(
        isinstance(sim_dict.get(gk), Mapping) and bool(sim_dict[gk].get("passed"))
        for gk in cg_keys
    )

    if (
        not v_sim.valid
        or sim_dict.get("go_no_go") != GO_NO_GO_DRY_RUN_SIMULATED_READY
        or not bool(sim_dict.get("all_4_check_groups_passed"))
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
            f"p5_{tag}_sim: simulated dry-run failed "
            f"(go={sim_dict.get('go_no_go')}, groups={sim_passed}/4, valid={v_sim.valid}, errs={v_sim.errors})"
        )

    return {
        f"{tag}_offline_go_no_go": str(off_dict.get("go_no_go", "")),
        f"{tag}_offline_check_groups_passed": int(off_dict.get("check_groups_passed", 0)),
        f"{tag}_offline_report_verified": bool(v_off.valid),
        f"{tag}_sim_go_no_go": str(sim_dict.get("go_no_go", "")),
        f"{tag}_sim_check_groups_passed": sim_passed,
        f"{tag}_hardware_live_attachment_authorized": bool(
            sim_dict.get("hardware_live_attachment_authorized", True)
        ),
        f"{tag}_h0_equals_h3_count": sim_h0_h3,
        f"{tag}_sim_usb_packets_transmitted": sim_pkts,
        f"{tag}_sim_raw_firmware_bytes_leaked": sim_leaked,
        f"{tag}_sim_passive_tx_bytes_emitted": sim_passive,
        f"{tag}_sim_report_verified": bool(v_sim.valid),
        f"{tag}_sim_report_sha256": str(sim_dict.get("report_sha256", "")),
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
    faults: RealHwMilestone295FaultInjection,
) -> Tuple[Milestone295PillarResult, Dict[str, Any]]:
    m264_p5, meta_p5_264 = _eval_m264_p5(
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
        _effective_m264_faults(faults),
    )
    errors: List[str] = [
        e
        for e in m264_p5.errors
        if e != "p5: overall_ready_for_hardware_attach must remain False across all 6 verifiers"
    ]

    info_275 = _check_4group_bench_verifier(
        tag="p275",
        raw_off=raw_p275_off,
        raw_sim=raw_p275_sim,
        verify_fn=verify_phase275_report,
        cg_keys=(
            "check_group_a_cinema_slate_and_timecode",
            "check_group_b_gamma_assist_and_display_lut",
            "check_group_c_focus_mag_videolight_and_hdmi_res",
            "check_group_d_power_bklang_volume_delete_and_tier0",
        ),
        errors=errors,
    )
    info_279 = _check_4group_bench_verifier(
        tag="p279",
        raw_off=raw_p279_off,
        raw_sim=raw_p279_sim,
        verify_fn=verify_phase279_report,
        cg_keys=(
            "check_group_a_usb_connection_mode",
            "check_group_b_hdmi_info_clean_feed",
            "check_group_c_protect_vs_format_slot1",
            "check_group_d_reset_network_zero_rf_tier0",
        ),
        errors=errors,
    )
    info_284 = _check_4group_bench_verifier(
        tag="p284",
        raw_off=raw_p284_off,
        raw_sim=raw_p284_sim,
        verify_fn=verify_phase284_report,
        cg_keys=(
            "check_group_a_pp_scinetone_look_dro_log",
            "check_group_b_wb_cine_ei_custom13_metering",
            "check_group_c_raw_2option_hlg_adobergb_dsc",
            "check_group_d_shutter_type_5lockout_hip_tier0",
        ),
        errors=errors,
    )
    info_291 = _check_4group_bench_verifier(
        tag="p291",
        raw_off=raw_p291_off,
        raw_sim=raw_p291_sim,
        verify_fn=verify_phase291_report,
        cg_keys=(
            "check_group_a_focus_zoom_iso_flash",
            "check_group_b_dci4k_aspect_hold_camset_photo",
            "check_group_c_sensor_clean_ev_focus_playback",
            "check_group_d_physical_bench_and_tier0",
        ),
        errors=errors,
        extra_usb_override=faults.p5_inject_p291_usb_packets_override,
        extra_passive_override=faults.p5_inject_p291_passive_tx_bytes_override,
    )

    any_attach_ready = bool(
        meta_p5_264["overall_ready_for_hardware_attach"]
        or info_275.pop("_any_attach_ready")
        or info_279.pop("_any_attach_ready")
        or info_284.pop("_any_attach_ready")
        or info_291.pop("_any_attach_ready")
    )
    if any_attach_ready:
        errors.append("p5: overall_ready_for_hardware_attach must remain False across all 10 verifiers")

    passed = len(errors) == 0
    evidence = dict(m264_p5.evidence)
    evidence.update(info_275)
    evidence.update(info_279)
    evidence.update(info_284)
    evidence.update(info_291)
    evidence["overall_ready_for_hardware_attach"] = any_attach_ready

    pillar = Milestone295PillarResult(
        pillar_id="P5",
        pillar_name="DECUPLE_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH291",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"10/10 Bench Preflights: Ph186({meta_p5_264['p186_sim_gates_passed']}/4) + "
            f"Ph204({meta_p5_264['p204_sim_groups_passed']}/3) + "
            f"Ph216({meta_p5_264['p216_sim_checklists_passed']}/5) + "
            f"Ph227({meta_p5_264['p227_sim_check_groups_passed']}/3) + "
            f"Ph248({meta_p5_264['p248_sim_check_groups_passed']}/4) + "
            f"Ph261({meta_p5_264['p261_sim_check_groups_passed']}/4) + "
            f"Ph275({info_275['p275_sim_check_groups_passed']}/4) + "
            f"Ph279({info_279['p279_sim_check_groups_passed']}/4) + "
            f"Ph284({info_284['p284_sim_check_groups_passed']}/4) + "
            f"Ph291({info_291['p291_sim_check_groups_passed']}/4 H0==H3={info_291['p291_h0_equals_h3_count']}/16) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_p5_264)
    meta.update(info_275)
    meta.update(info_279)
    meta.update(info_284)
    meta.update(info_291)
    meta["overall_ready_for_hardware_attach"] = any_attach_ready
    return pillar, meta


def _evaluate_pillar_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: RealHwMilestone295FaultInjection,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
    p5_meta: Mapping[str, Any],
) -> Tuple[Milestone295PillarResult, Dict[str, Any]]:
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

    expected_rounds = len(ROUND28_TO_58_SPECS)
    expected_runs = sum(len(s.run_specs) for s in ROUND28_TO_58_SPECS)
    expected_pngs = sum(len(ROUND28_TO_58_PNG_RECEIPTS[s.round_num]) for s in ROUND28_TO_58_SPECS)

    for spec in ROUND28_TO_58_SPECS:
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

        png_pair = ROUND28_TO_58_PNG_RECEIPTS[spec.round_num]
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

    # Forward-compatible discovery of Round 59+ reports so newly merged QEMU rounds stay green
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
            if rnum >= 59 and (d / "summary.json").is_file():
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

    # Cross-pillar hardware-lock, 16/16 H0 == H3, zero eMMC & zero e-ND invariants
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
    ):
        errors.append(
            "p6: P5 H0==H3 (16/16) or 10/10 decuple bench preflight (Ph186..Ph291) invariant breached"
        )

    passed = (
        len(errors) == 0
        and rounds_verified >= 31
        and rounds_verified == expected_rounds
        and total_runs_verified >= 93
        and total_runs_verified == expected_runs
        and pngs_verified >= 62
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
        "h0_equals_h3_count": int(p5_meta.get("p291_h0_equals_h3_count", 0)),
        "emmc_write_count": total_emmc,
        "e_nd_actuator_tx_count": max(0, int(p1_meta.get("g71_e_nd_actuator_tx_count", 0)))
        + max(0, int(p4_meta.get("e_nd_actuator_tx_count", 0)))
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
        "milestone264_schema_anchor": MILESTONE264_SCHEMA_VERSION,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
    }
    pillar = Milestone295PillarResult(
        pillar_id="P6",
        pillar_name="REAL_FX3_702_QEMU_ROUNDS_28_TO_58_PLUS_AND_PNG_RECEIPTS",
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


def _collect_parallel_milestone295_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: RealHwMilestone295FaultInjection,
) -> Tuple[Any, ...]:
    m264_f = _effective_m264_faults(faults)
    m254_f = _effective_m254_faults(m264_f)
    m233_f = _effective_m233_faults(m254_f)
    m221_f = _effective_m221_faults(m233_f)
    m209_f = _effective_m209_faults(m221_f)
    m193_f = _effective_m193_faults(m209_f)
    gate_fault_dict = _fault_to_124gate_worker_dict(faults)
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
        "file_gamma_focusmag_vault": bool(faults.p5_inject_p275_file_gamma_focusmag_vault_fault),
        "h0_h3_drift": bool(faults.p5_inject_p275_h0_h3_drift),
    }
    p279_fault_dict = {
        "usb_hdmi_protect_nw": bool(faults.p5_inject_p279_usb_hdmi_protect_nw_fault),
        "h0_h3_drift": bool(faults.p5_inject_p279_h0_h3_drift),
    }
    p284_fault_dict = {
        "pp_wb_raw_shutter": bool(faults.p5_inject_p284_pp_wb_raw_shutter_fault),
        "h0_h3_drift": bool(faults.p5_inject_p284_h0_h3_drift),
    }
    p291_fault_dict = {
        "focus_zoom_dci4k_clean": bool(faults.p5_inject_p291_focus_zoom_dci4k_clean_fault),
        "h0_h3_drift": bool(faults.p5_inject_p291_h0_h3_drift),
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
        or m264_f.p2_fault_inject_pillar
        or m254_f.p2_fault_inject_pillar
        or m233_f.p2_fault_inject_pillar
        or m221_f.p2_fault_inject_pillar
        or m209_f.p2_fault_inject_pillar
        or m193_f.p2_fault_inject_pillar
    )

    try:
        # Execute 0.15s-budgeted #41..#45+ realhw auditors before fork() COW contention
        auditors: Dict[str, Dict[str, Any]] = dict(
            _worker_pillar_3_batch_233((p3_batches[0], use_clean_room))
        )
        ctx = mp.get_context("fork")
        pool_workers = min(8, max(4, mp.cpu_count() or 8))
        with ProcessPoolExecutor(max_workers=pool_workers, mp_context=ctx) as ex:
            fut_vm = ex.submit(_worker_pillar_4_295, use_clean_room)
            fut_1_off = ex.submit(
                _worker_124plus_gate_single,
                (str(repo_root), use_clean_room, False, gate_fault_dict),
            )
            fut_1_sim = ex.submit(
                _worker_124plus_gate_single,
                (str(repo_root), use_clean_room, True, gate_fault_dict),
            )
            fut_50p = ex.submit(_worker_recovery_50plus_pillar, (use_clean_room, eff_p2_fault))
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

            raw_1_off = fut_1_off.result()
            raw_1_sim = fut_1_sim.result()
            raw_50p = fut_50p.result()
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
            return (
                raw_1_off,
                raw_1_sim,
                raw_50p,
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
            )
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1_off = _worker_124plus_gate_single(
        (str(repo_root), use_clean_room, False, gate_fault_dict)
    )
    raw_1_sim = _worker_124plus_gate_single(
        (str(repo_root), use_clean_room, True, gate_fault_dict)
    )
    raw_50p = _worker_recovery_50plus_pillar((use_clean_room, eff_p2_fault))
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
    return (
        raw_1_off,
        raw_1_sim,
        raw_50p,
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
    )


def evaluate_realhw_milestone295_master_gate(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[RealHwMilestone295FaultInjection] = None,
    _raw_bundle_override: Optional[Tuple[Any, ...]] = None,
) -> RealHwMilestone295MasterGateReport:
    """Build & evaluate the Grand Milestone Phase 295 6-Pillar Real-Hardware Master Gate."""
    if force_clean_room is not None:
        use_clean_room = bool(force_clean_room)
    elif synthetic_clean_room is not None:
        use_clean_room = bool(synthetic_clean_room)
    else:
        use_clean_room = _is_forced_clean_room()

    active_faults = faults or RealHwMilestone295FaultInjection()

    bundle = _raw_bundle_override or _collect_parallel_milestone295_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )
    (
        raw_1_off,
        raw_1_sim,
        raw_50p,
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
    ) = bundle

    p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
    p2, meta_2 = _evaluate_pillar_2(raw_50p, active_faults)
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

    pillars: Tuple[Milestone295PillarResult, ...] = (p1, p2, p3, p4, p5, p6)
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
        + int(meta_5["p275_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p279_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p284_sim_raw_firmware_bytes_leaked"])
        + int(meta_5["p291_sim_raw_firmware_bytes_leaked"])
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
    )
    total_passive_tx = (
        int(meta_2["passive_tx_bytes"])
        + max(0, int(meta_5["p275_sim_passive_tx_bytes_emitted"]))
        + max(0, int(meta_5["p279_sim_passive_tx_bytes_emitted"]))
        + max(0, int(meta_5["p284_sim_passive_tx_bytes_emitted"]))
        + max(0, int(meta_5["p291_sim_passive_tx_bytes_emitted"]))
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
        int(meta_5["p275_h0_equals_h3_count"]),
        int(meta_5["p279_h0_equals_h3_count"]),
        int(meta_5["p284_h0_equals_h3_count"]),
        int(meta_5["p291_h0_equals_h3_count"]),
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
        "schema": REALHW_MILESTONE295_SCHEMA,
        "schema_version": REALHW_MILESTONE295_SCHEMA,
        "phase_version": PHASE_295_VERSION,
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
        "gate124_total_gates": raw_1_sim["total_gates"],
        "gate124_offline_verified": raw_1_off["verified_gates"],
        "gate124_simulated_verified": raw_1_sim["verified_gates"],
        "gate124_all_verified": bool(raw_1_sim.get("all_n_gates_verified", False)),
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
    digest = compute_milestone295_sha256(payload_no_sha)

    return RealHwMilestone295MasterGateReport(
        **common_fields,
        pillars=pillars,
        milestone295_sha256=digest,
    )


build_realhw_milestone295_master_gate_report = evaluate_realhw_milestone295_master_gate
evaluate_milestone_295_master_gate = evaluate_realhw_milestone295_master_gate
evaluate_milestone295_master_gate = evaluate_realhw_milestone295_master_gate


def verify_realhw_milestone295_master_gate(
    report: object,
) -> RealHwMilestone295VerifyResult:
    """Fail-closed verifier for a Grand Milestone Phase 295 Real-Hardware Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, RealHwMilestone295MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return RealHwMilestone295VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone295_sha256="",
            observed_milestone295_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or RealHwMilestone295MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = (
        payload.get("schema") == REALHW_MILESTONE295_SCHEMA
        and payload.get("schema_version") == REALHW_MILESTONE295_SCHEMA
    )
    if not schema_ok:
        errors.append(
            f"schema mismatch: schema={payload.get('schema')!r} schema_version={payload.get('schema_version')!r}"
        )

    expected_sha = compute_milestone295_sha256(payload)
    observed_sha = str(payload.get("milestone295_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(
            f"milestone295_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}"
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
    )
    if not redlines_ok:
        errors.append(
            "hard-locked zero-write / cnflasha-RO / zero-cross-model / zero-SPI-NOR / zero-EL3 / "
            "zero-USB-TX / zero-leak / zero-attach redlines breached"
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

    g_total = int(payload.get("gate124_total_gates", -1))
    g_off = int(payload.get("gate124_offline_verified", -1))
    g_sim = int(payload.get("gate124_simulated_verified", -1))
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
        g_total >= 124
        and g_off >= g_total - 3
        and g_off == g_total - 3
        and g_sim >= 124
        and g_sim == g_total
        and payload.get("gate124_all_verified") is True
        and rec_total >= 50
        and rec_passed == rec_total
        and aud_passed >= 45
        and aud_passed == aud_total
        and vm_passed >= 58
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
        and int(payload.get("h0_equals_h3_count", -1)) == 16
        and q_rounds_ver >= 31
        and q_rounds_ver == q_rounds_tot
        and q_runs_ver >= 93
        and q_runs_ver == q_runs_tot
        and q_pngs_ver >= 62
        and q_pngs_ver == q_pngs_tot
        and 0 < int(payload.get("qemu_png_max_bytes", -1)) < PNG_MAX_SIZE_50KIB_BYTES
        and int(payload.get("qemu_real_kernel_nop_count", -1)) == 0
        and int(payload.get("qemu_real_kernel_crashes", -1)) == 0
        and int(payload.get("qemu_real_kernel_emmc_writes", -1)) == 0
    )
    if not counts_ok:
        errors.append("milestone295 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append(
            "all_pillars_milestone_ready / status is not MILESTONE_295_PREBENCH_MASTER_VERIFIED"
        )

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 295 payload")

    valid = bool(
        schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0
    )
    return RealHwMilestone295VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone295_sha256=expected_sha,
        observed_milestone295_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


verify_milestone_295_master_gate = verify_realhw_milestone295_master_gate


def render_milestone295_markdown(report: RealHwMilestone295MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 295 Master Gate."""
    lines = [
        f"# Grand Milestone Phase 295 — Real-Hardware `ILME-FX3 Ver. 7.02` 6-Pillar Master Gate (`{report.schema}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone295_sha256}`",
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
            "## Key Grand Milestone Phase 295 Metrics / 实机总闭环核心指标",
            f"- 124+-Gate Preflight (`G01..G{report.gate124_total_gates}`): offline=`{report.gate124_offline_verified}/{report.gate124_total_gates}` (`G10..G12` locked), simulated=`{report.gate124_simulated_verified}/{report.gate124_total_gates}` (`gate124_all_verified={report.gate124_all_verified}`, `cross_model_flash={report.cross_model_flash_authorized}`)",
            f"- 50+-Pillar Recovery Master (`verify-{report.recovery_pillar_count}pillar-recovery`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`{report.recovery_status}`, `cnflasha_ro={report.cnflasha_userspace_write_blocked}`)",
            f"- 45+ Firmware-Lab Auditors (`auditors_passed >= 45`): `{report.auditors_passed}/{report.auditors_total}` (`raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`)",
            f"- 58+ Stage VM HIL Co-Emulation (`vm_stages_passed >= 58`): `{report.vm_stages_passed}/{report.vm_stages_total}` (`physical_device_writes={report.vm_physical_device_writes}`, `emmc_corruptions={report.vm_emmc_corruptions}`)",
            f"- Decuple (10/10) Bench Readiness Preflights (`Ph186..Ph291`): `Ph186={report.p186_offline_go_no_go}/{report.p186_sim_go_no_go}`, `Ph204={report.p204_offline_go_no_go}/{report.p204_sim_go_no_go}`, `Ph216={report.p216_offline_go_no_go}/{report.p216_sim_go_no_go}`, `Ph227={report.p227_offline_go_no_go}/{report.p227_sim_go_no_go}`, `Ph248={report.p248_offline_go_no_go}/{report.p248_sim_go_no_go}`, `Ph261={report.p261_offline_go_no_go}/{report.p261_sim_go_no_go}`, `Ph275={report.p275_offline_go_no_go}/{report.p275_sim_go_no_go}`, `Ph279={report.p279_offline_go_no_go}/{report.p279_sim_go_no_go}`, `Ph284={report.p284_offline_go_no_go}/{report.p284_sim_go_no_go}`, `Ph291={report.p291_offline_go_no_go}/{report.p291_sim_go_no_go}` (`H0==H3={report.h0_equals_h3_count}/16`)",
            f"- Live FX3 `7.02` (`4.9.337-scel+`) QEMU Receipts (`Rounds 28..58+`): `{report.qemu_rounds_verified}/{report.qemu_rounds_total}` rounds (`{report.qemu_runs_verified}/{report.qemu_runs_total}` sub-runs, `PNGs={report.qemu_png_receipts_verified}/{report.qemu_png_receipts_total}` max=`{report.qemu_png_max_bytes}B < 50KiB`), `nop={report.qemu_real_kernel_nop_count}`, `crashes={report.qemu_real_kernel_crashes}`, `emmc_writes={report.qemu_real_kernel_emmc_writes}`",
            "",
        ]
    )
    return "\n".join(lines)


def verify_milestone_295_cli(
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
    """Execute `verify-milestone-295` CLI supporting `--clean-room`/`--force-clean-room`/`--json`/`--out`."""
    if argv is not None:
        parser = argparse.ArgumentParser(prog="verify-milestone-295")
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

    rep = evaluate_realhw_milestone295_master_gate(
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
        markdown_out.write_text(render_milestone295_markdown(rep), encoding="utf-8")
    v_res = verify_realhw_milestone295_master_gate(rep.to_dict())
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
                f"gate124={rep.gate124_offline_verified}/{rep.gate124_simulated_verified} "
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
                f"h0_eq_h3={rep.h0_equals_h3_count}/16 "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
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
                f"milestone295_sha256={rep.milestone295_sha256[:16]}...\n"
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
    "MILESTONE295_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P8_CP_MUTATION_FORBIDDEN",
    "P295_PHYSICAL_DEVICE_WRITES",
    "P295_PILLAR_IDS",
    "P295_PILLAR_SPECS",
    "P295_PNG_MAX_SIZE_BYTES",
    "P295_RAW_FIRMWARE_BYTES_LEAKED",
    "P295_SCHEMA",
    "P295_STATUS_FAIL_CLOSED",
    "P295_STATUS_MILESTONE_READY",
    "P295_VERSION",
    "PASSIVE_TX_BYTES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_295_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "PNG_MAGIC_BYTES",
    "PNG_MAX_SIZE_50KIB_BYTES",
    "PNG_MAX_SIZE_BYTES",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_MILESTONE295_SCHEMA",
    "RECOVERY_50_PILLAR_IDS",
    "ROUND28_TO_58_PNG_RECEIPTS",
    "ROUND28_TO_58_SPECS",
    "ROUND53_EXPECTED_SCHEMA",
    "ROUND53_SUMMARY_RELPATH",
    "ROUND54_EXPECTED_SCHEMA",
    "ROUND54_SUMMARY_RELPATH",
    "ROUND55_EXPECTED_SCHEMA",
    "ROUND55_SUMMARY_RELPATH",
    "ROUND56_EXPECTED_SCHEMA",
    "ROUND56_SUMMARY_RELPATH",
    "ROUND57_EXPECTED_SCHEMA",
    "ROUND57_SUMMARY_RELPATH",
    "ROUND58_EXPECTED_SCHEMA",
    "ROUND58_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "RPMB_WRITES",
    "SCHEMA_VERSION",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "USB_PACKETS_TRANSMITTED",
    "VM_COEMULATION_58_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone295PillarResult",
    "RealHwMilestone295FaultInjection",
    "RealHwMilestone295MasterGateReport",
    "RealHwMilestone295VerifyResult",
    "build_realhw_milestone295_master_gate_report",
    "compute_milestone295_sha256",
    "evaluate_milestone295_master_gate",
    "evaluate_milestone_295_master_gate",
    "evaluate_realhw_milestone295_master_gate",
    "render_milestone295_markdown",
    "verify_milestone_295_cli",
    "verify_milestone_295_master_gate",
    "verify_realhw_milestone295_master_gate",
]
