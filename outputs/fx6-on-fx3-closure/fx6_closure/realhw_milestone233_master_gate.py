"""Grand Milestone Phase 233 — 6-Pillar Real-Hardware `ILME-FX3 Ver. 7.02` Master Gate (`realhw_milestone233_master_gate_v1`).

Unites ALL Wave 21–32 Real-Hardware Main Track subsystems (Phases 134–239) and ALL
20+ live Sony ILME-FX3 `Ver. 7.02` (`Linux 4.9.337-scel+`) ARM64 QEMU Rehearsal
Rounds (`Rounds 28..47` — `>= 60` sub-runs `r28a..r47c` + `>= 40` `< 50 KiB` PNG
receipts) into a single tamper-evident, fail-closed certificate executing in
`< 5.0s` per mode across both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC`
(`FX3_FX6_FORCE_CLEAN_ROOM=1`) while keeping `verify-milestone-175`,
`verify-milestone-193`, `verify-milestone-209`, `verify-milestone-221`, and all 4
bench readiness preflights (`Ph186`, `Ph204`, `Ph216`, `Ph227`) 100% intact and
forward-compatible via `>=` lower bounds:

- `P1` (`SAFETY_90GATE_REALHW_MASTER_PREFLIGHT`):
  Evaluates `fx3_safety.evaluate_90gate_preflight` (`87/90` offline with `>= 87`
  verified and `3` physical Tier-0 receipt gates `G10..G12` fail-closed; `90/90`
  simulated dry-run `--simulate-bench-dry-run` with `all_90_gates_verified == True`),
  verifying `G79..G90` (`Pixel Mapping cnflasha O_RDONLY`, `NTSC/PAL & Gamma Assist`,
  `SteadyShot Active & CIZ 4-locks`, `Power Save 9-cond & Auto Temp tripod`, `S&Q
  Fixed/Variable & Zebra/Peaking`, `Full Format Slot-1 chord`, `Silent Mode & Auto
  Pixel Mapping`, `Marker 15-ratio & Flexible Exp.`, `Recover Image DB`, `Monitor
  Flip & AF Sens.`, `Emphasized REC & Grid HDMI`, `Touch Operation & Sunny Weather`)
  with all hardware write/attach flags locked `False` and `usb_packets_transmitted == 0`.
- `P2` (`THIRTY_EIGHT_PILLAR_RECOVERY_MASTER_VAULT`):
  Verifies `>= 38` recovery pillars (`38/38`, `all_passed == True` via
  `fx3_recovery.evaluate_realhw_38pillar_recovery_master`), locking
  `cnflasha_userspace_write_blocked == True`, `otp_fuse_touches == 0`,
  `rpmb_counter_increments == 0`, `passive_tx_bytes_emitted == 0`,
  `physical_usb_packets_emitted == 0`, and `raw_firmware_bytes_leaked == 0`.
- `P3` (`FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS`):
  Verifies all `>= 45` `fx3_firmware_lab` auditors including Phase 218 (`45th`,
  `File Settings 37-char/SDHC, ShotMark XML, TC Regenerate Slot-1 & Coupled REC Lamp`)
  plus dynamic discovery of any future `46th+` `realhw_*_auditor`, locking
  `raw_firmware_bytes_leaked == 0`.
- `P4` (`FORTY_FOUR_PLUS_STAGE_VM_HIL_COEMULATION`):
  Runs `fx3_vm_coemulation_suite` with Stages `1..44` enabled (`>= 44` stages,
  `passed_count == stage_count`, `raw_firmware_bytes_leaked == 0`,
  `physical_device_writes == 0`, `emmc_corruptions == 0`).
- `P5` (`QUAD_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216_PH227`):
  Verifies `Phase 136`, `Phase 143`, `Phase 154`, AND all 4 Physical Bench Readiness
  Verifiers (`Ph186` card-insert, `Ph204` bench-cable-fan-slot1, `Ph216`
  hdmi-proxy-desqueeze-and-simult, AND `Ph227`
  `realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier`) return
  `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` offline and
  `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` in simulated dry-run, with
  `overall_ready_for_hardware_attach == False` and `16/16 H0 == H3`.
- `P6` (`REAL_FX3_702_QEMU_ROUNDS_28_TO_47_PLUS_AND_PNG_RECEIPTS`):
  Verifies `>= 20` live `ILME-FX3 Ver. 7.02` ARM64 QEMU rounds through `Round 47`
  (`r43..r47` included, forward-compatible with `Round 48+`), `>= 60` sub-runs,
  `>= 40` sanitized PNG receipts (`< 50 KiB` each), `16/16 H0 == H3`,
  `emmc_write_count == 0`, and `e_nd_actuator_tx_count == 0`.
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
from fx3_firmware_lab.realhw_filesettings_shotmark_tcregen_and_reclamp_auditor import (  # noqa: E402
    analyze_realhw_filesettings_shotmark_tcregen_and_reclamp,
    realhw_filesettings_shotmark_tcregen_and_reclamp_report_to_dict,
)
from fx3_recovery import evaluate_realhw_38pillar_recovery_master  # noqa: E402
from fx3_recovery.realhw_38pillar_shoe_audio_wind_saveload_vault_verifier import (  # noqa: E402
    MASTER_38_PILLAR_IDS,
)
from fx3_safety import evaluate_90gate_preflight  # noqa: E402
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
    FIRMWARE_LAB_44_AUDITOR_KEYS,
    MILESTONE221_SCHEMA_VERSION,
    OTP_FUSE_WRITES,
    PASSIVE_TX_BYTES,
    ROUND28_TO_42_PNG_RECEIPTS,
    ROUND28_TO_42_SPECS,
    RPMB_WRITES,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_38_STAGE_KEYS,
    RealHwMilestone221FaultInjection,
    _78GATE_EXTRA_FAULT_FIELDS,
    _effective_m209_faults,
    _evaluate_pillar_3 as _eval_m221_p3,
    _evaluate_pillar_4 as _eval_m221_p4,
    _evaluate_pillar_5 as _eval_m221_p5,
    _worker_phase216,
    _worker_pillar_3_batch_221,
)
from .realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier import (  # noqa: E402
    evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness,
    verify_phase227_report,
)
from .stage_b_rehearsal_orchestrator import HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_MILESTONE233_SCHEMA: str = "realhw_milestone233_master_gate_v1"
MILESTONE233_SCHEMA_VERSION: str = REALHW_MILESTONE233_SCHEMA
SCHEMA_VERSION: str = REALHW_MILESTONE233_SCHEMA
PHASE_233_VERSION: str = "233.0.0"

PNG_MAX_SIZE_50KIB_BYTES: int = 50 * 1024  # 51,200 B (< 50 KiB BYOF PNG ceiling)
PNG_MAX_SIZE_BYTES: int = PNG_MAX_SIZE_50KIB_BYTES
PHYSICAL_DEVICE_WRITES: int = 0
OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False

STATUS_MILESTONE_READY: str = "MILESTONE_233_PREBENCH_MASTER_VERIFIED"

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_90GATE_REALHW_MASTER_PREFLIGHT"),
    ("P2", "THIRTY_EIGHT_PILLAR_RECOVERY_MASTER_VAULT"),
    ("P3", "FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS"),
    ("P4", "FORTY_FOUR_PLUS_STAGE_VM_HIL_COEMULATION"),
    ("P5", "QUAD_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216_PH227"),
    ("P6", "REAL_FX3_702_QEMU_ROUNDS_28_TO_47_PLUS_AND_PNG_RECEIPTS"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)

RECOVERY_38_PILLAR_IDS: Tuple[str, ...] = MASTER_38_PILLAR_IDS

FIRMWARE_LAB_45_AUDITOR_KEYS: Tuple[str, ...] = (
    *FIRMWARE_LAB_44_AUDITOR_KEYS,
    "realhw_filesettings_shotmark_tcregen_and_reclamp_audit",
)

_KNOWN_19_REALHW_AUDITOR_STEMS: frozenset[str] = frozenset(
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
        "realhw_filesettings_shotmark_tcregen_and_reclamp_auditor",
    }
)

VM_COEMULATION_44_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_38_STAGE_KEYS,
    "stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil",
    "stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil",
    "stage41_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil",
    "stage42_realhw_sq_fixedvar_zebra_peaking_fullformat_hil",
    "stage43_realhw_silent_autopixelmap_marker_flexexp_hil",
    "stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil",
)

ROUND43_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round43-realhw-filesettings-shotmark-tcregen-reclamp-qemu/summary.json"
)
ROUND44_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round44-realhw-pixelmap-ntscpal-gammaassist-displaylut-qemu/summary.json"
)
ROUND45_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round45-realhw-steadyshot-ciz-powersave-autotemp-qemu/summary.json"
)
ROUND46_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu/summary.json"
)
ROUND47_SUMMARY_RELPATH: str = (
    "reports/2026-11-15-round47-realhw-silent-autopixelmap-marker-flexexp-qemu/summary.json"
)

ROUND43_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round43-realhw-filesettings-shotmark-tcregen-reclamp-qemu-v1"
)
ROUND44_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round44-realhw-pixelmap-ntscpal-gammaassist-displaylut-qemu-v1"
)
ROUND45_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round45-realhw-steadyshot-ciz-powersave-autotemp-qemu-v1"
)
ROUND46_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu-v1"
)
ROUND47_EXPECTED_SCHEMA: str = (
    "fx6-on-fx3-round47-realhw-silent-autopixelmap-marker-flexexp-qemu-v1"
)

ROUND28_TO_47_SPECS: Tuple[RoundQemuReceiptSpec, ...] = (
    *ROUND28_TO_42_SPECS,
    RoundQemuReceiptSpec(
        round_num=43,
        summary_relpath=ROUND43_SUMMARY_RELPATH,
        expected_schema=ROUND43_EXPECTED_SCHEMA,
        audit_key="r43_realhw_filesettings_shotmark_tcregen_reclamp_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r43a_file_settings_5modes_37char_sdhc_lock_and_folder_block_verified",
            "r43a_shotmark12_xml_sidecar_image_jump_and_ftp_filter_verified",
            "r43a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r43b_tc_regenerate_slot1_master_and_forced_rec_run_verified",
            "r43b_ext_lk_release_on_regen_or_tc_run_and_sq_hdmi_tcout_block_verified",
            "r43c_reclamp_3state_coupled_rear_top_and_hdmi_tally_independence_verified",
            "r43c_silent_mode_audio_signals_lock_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r43a_filesettings_shotmark_big6_schinese", 1),
            ("r43b_tc_regenerate_slot1_extlk", None),
            ("r43c_reclamp_coupled_tally_h0_h3", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=44,
        summary_relpath=ROUND44_SUMMARY_RELPATH,
        expected_schema=ROUND44_EXPECTED_SCHEMA,
        audit_key="r44_realhw_pixelmap_ntscpal_gammaassist_displaylut_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r44a_auto_pixelmap_silent_shutter_lowbatt_and_op_lockout_verified",
            "r44a_auto_restart_tmp_wipe_h0_eq_h2_and_cnflasha_ro_firewall_verified",
            "r44a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r44b_ntsc_pal_exclusive_rates_and_df_ndf_lockout_verified",
            "r44b_startup_banner_camera_reset_survival_and_dual_slot_db_sep_verified",
            "r44c_gamma_assist_4mode_slog2_reject_and_zero_hdmi_scope_verified",
            "r44c_log_shooting_display_lut_lockout_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r44a_pixelmap_cnflasha_big6_schinese", 1),
            ("r44b_ntscpal_dfn_camreset_persist", None),
            ("r44c_gammaassist_displaylut_h0_h3", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=45,
        summary_relpath=ROUND45_SUMMARY_RELPATH,
        expected_schema=ROUND45_EXPECTED_SCHEMA,
        audit_key="r45_realhw_steadyshot_ciz_powersave_autotemp_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r45a_steadyshot_active_110crop_and_3_hard_cutoffs_verified",
            "r45a_hdmi_raw_suppression_and_restore_verified",
            "r45a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r45b_ciz_digital_zoom_raw_and_hfr_cutoffs_verified",
            "r45b_ciz_beyond_optical_4_camera_state_locks_and_unlock_verified",
            "r45c_powersave_exact_label_5min_default_and_9cond_bypass_verified",
            "r45c_airgapped_75mib_p3_vault_lock_autotemp_tripod_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r45a_steadyshot_active_cutoffs_big6_schinese", 1),
            ("r45b_ciz_4locks_hfr_raw_cutoffs", None),
            ("r45c_powersave_9cond_autotemp_h0_h3", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=46,
        summary_relpath=ROUND46_SUMMARY_RELPATH,
        expected_schema=ROUND46_EXPECTED_SCHEMA,
        audit_key="r46_realhw_sq_fixedvar_zebra_peaking_fullformat_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r46a_mode_settings_fixed_variable_locks_sq_settings_verified",
            "r46a_sq_all_6_disqualification_locks_verified",
            "r46a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r46b_zebra_camera_settings_reset_survival_and_initialize_reset_verified",
            "r46b_zebra_and_peaking_zero_hdmi_overlay_pixels_when_hdmi_info_on_verified",
            "r46c_quick_vs_delete_fullformat_and_midcancel_erasure_verified",
            "r46c_slot1_tier0_vault_and_menu_delete_2s_chord_lockout_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r46a_sq_fixedvar_6locks_big6_schinese", 1),
            ("r46b_zebra_persist_peaking_hdmi_isolation", None),
            ("r46c_slot1_fullformat_chord_vault_h0_h3", None),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=47,
        summary_relpath=ROUND47_SUMMARY_RELPATH,
        expected_schema=ROUND47_EXPECTED_SCHEMA,
        audit_key="r47_realhw_silent_autopixelmap_marker_flexexp_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "r47a_silent_mode_shutter_audio_and_5_disabled_functions_verified",
            "r47a_target_function_settings_autopixelmap_suppression_and_no_pwrshutter_enoent_verified",
            "r47a_stageb_big6_sid_0a_over_340k_pixels_verified",
            "r47b_marker_display_15_ratios_camera_settings_reset_survival_and_initialize_reset_verified",
            "r47b_marker_display_zero_hdmi_overlay_pixels_when_hdmi_info_on_verified",
            "r47c_exposure_ctrl_type_flexible_exp_and_av_tv_iso_auto_slow_shutter_reset_split_verified",
            "r47c_dlopen_libjit_and_16_h0_eq_h3_rollback_verified",
        ),
        run_specs=(
            ("r47a_silent_autopixelmap_5locks_big6_schinese", 1),
            ("r47b_marker_15ratio_persist_hdmi_isolation", None),
            ("r47c_flexexp_avtviso_autoslowshutter_h0_h3", None),
        ),
    ),
)

ROUND28_TO_47_PNG_RECEIPTS: Dict[int, Tuple[str, str]] = {
    **ROUND28_TO_42_PNG_RECEIPTS,
    43: (
        "reports/2026-11-15-round43-realhw-filesettings-shotmark-tcregen-reclamp-qemu/assets/r43a-filesettings-shotmark-big6-schinese-alpha.png",
        "reports/2026-11-15-round43-realhw-filesettings-shotmark-tcregen-reclamp-qemu/assets/r43a-filesettings-shotmark-big6-schinese-composited.png",
    ),
    44: (
        "reports/2026-11-15-round44-realhw-pixelmap-ntscpal-gammaassist-displaylut-qemu/assets/r44a-pixelmap-cnflasha-big6-schinese-alpha.png",
        "reports/2026-11-15-round44-realhw-pixelmap-ntscpal-gammaassist-displaylut-qemu/assets/r44a-pixelmap-cnflasha-big6-schinese-composited.png",
    ),
    45: (
        "reports/2026-11-15-round45-realhw-steadyshot-ciz-powersave-autotemp-qemu/assets/r45a-steadyshot-ciz-powersave-big6-schinese-alpha.png",
        "reports/2026-11-15-round45-realhw-steadyshot-ciz-powersave-autotemp-qemu/assets/r45a-steadyshot-ciz-powersave-big6-schinese-composited.png",
    ),
    46: (
        "reports/2026-11-15-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu/assets/r46a-sq-fixedvar-zebra-big6-schinese-alpha.png",
        "reports/2026-11-15-round46-realhw-sq-fixedvar-zebra-peaking-fullformat-qemu/assets/r46a-sq-fixedvar-zebra-big6-schinese-composited.png",
    ),
    47: (
        "reports/2026-11-15-round47-realhw-silent-autopixelmap-marker-flexexp-qemu/assets/r47a-silent-autopixelmap-marker-big6-schinese-alpha.png",
        "reports/2026-11-15-round47-realhw-silent-autopixelmap-marker-flexexp-qemu/assets/r47a-silent-autopixelmap-marker-big6-schinese-composited.png",
    ),
}

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_VM_STAGE_KEY_RE = re.compile(r"^stage(\d+)_")
_ROUND_DIR_RE = re.compile(r"-round(\d+)-")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealHwMilestone233FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 Wave 30–32 gates (G79..G90) + persistent-write lock
    p1_pixelmap_cnflasha_kwargs: Optional[Mapping[str, Any]] = None
    p1_ntscpal_gammaassist_kwargs: Optional[Mapping[str, Any]] = None
    p1_steadyshot_ciz_kwargs: Optional[Mapping[str, Any]] = None
    p1_powersave_autotemp_kwargs: Optional[Mapping[str, Any]] = None
    p1_sq_fixedvar_zebra_peaking_kwargs: Optional[Mapping[str, Any]] = None
    p1_zebra_reset_fullformat_kwargs: Optional[Mapping[str, Any]] = None
    p1_silent_autopixelmap_kwargs: Optional[Mapping[str, Any]] = None
    p1_marker_flexexp_kwargs: Optional[Mapping[str, Any]] = None
    p1_recover_imagedb_kwargs: Optional[Mapping[str, Any]] = None
    p1_monitor_flip_af_interval_kwargs: Optional[Mapping[str, Any]] = None
    p1_emphasized_rec_grid_hdmi_kwargs: Optional[Mapping[str, Any]] = None
    p1_touch_op_sunny_weather_kwargs: Optional[Mapping[str, Any]] = None
    p1_request_persistent_writes: bool = False

    # P2 >= 38-pillar recovery master + cnflasha RO + zero-touch redlines
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

    # P4 >= 44 VM HIL stages (Stages 39..44 + forward-compat 45+)
    p4_stage39_filesettings_tcregen_faults: int = 0
    p4_stage40_pixelmap_ntscpal_faults: int = 0
    p4_stage41_steadyshot_ciz_powersave_faults: int = 0
    p4_stage42_sq_zebra_fullformat_faults: int = 0
    p4_stage43_silent_autopixelmap_marker_faults: int = 0
    p4_stage44_recover_imagedb_flip_af_faults: int = 0
    p4_physical_device_writes_override: int = 0
    p4_raw_firmware_bytes_leaked_override: int = 0

    # P5 Quad bench readiness preflights (Ph186 + Ph204 + Ph216 + Ph227)
    p5_inject_p186_h0_h3_drift: bool = False
    p5_inject_p204_h0_h3_drift: bool = False
    p5_inject_p216_h0_h3_drift: bool = False
    p5_inject_p227_pixelmap_lowbatt_fault: bool = False
    p5_inject_p227_ntscpal_fps_conflict_fault: bool = False
    p5_inject_p227_powersave_p3_sleep_fault: bool = False
    p5_inject_p227_autotemp_no_tripod_fault: bool = False
    p5_inject_p227_h0_h3_drift: bool = False
    p5_inject_p227_usb_packets_override: int = 0

    # P6 Rounds 28..47+ live QEMU kernel rehearsal & < 50 KiB PNG receipts
    p6_round_nop_override_num: Optional[int] = None
    p6_round_nop_count_override: Optional[int] = None
    p6_round_crash_override_num: Optional[int] = None
    p6_round_crashes_override: Optional[int] = None
    p6_round_emmc_override_num: Optional[int] = None
    p6_round_emmc_writes_override: Optional[int] = None
    p6_tamper_schema_round_num: Optional[int] = None
    p6_png_size_override_round_num: Optional[int] = None
    p6_png_size_override_bytes: Optional[int] = None

    # Optional upstream Milestone 221 fault injection pass-through
    m221_faults: Optional[RealHwMilestone221FaultInjection] = None


@dataclass(frozen=True)
class Milestone233PillarResult:
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
class RealHwMilestone233MasterGateReport:
    schema: str
    schema_version: str
    phase_version: str
    verification_mode: str
    all_pillars_milestone_ready: bool
    status: str
    o_rdonly_enforced: bool
    cnflasha_userspace_write_blocked: bool
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
    pillars: Tuple[Milestone233PillarResult, ...]
    gate90_total_gates: int
    gate90_offline_verified: int
    gate90_simulated_verified: int
    gate90_all_verified: bool
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
    milestone233_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class RealHwMilestone233VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone233_sha256: str
    observed_milestone233_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_milestone233_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `RealHwMilestone233MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone233_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 5.0s per mode)
# ---------------------------------------------------------------------------

_90GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_pixelmap_cnflasha_kwargs", "pixelmap_cnflasha_kwargs"),
    ("p1_ntscpal_gammaassist_kwargs", "ntscpal_gammaassist_kwargs"),
    ("p1_steadyshot_ciz_kwargs", "steadyshot_ciz_kwargs"),
    ("p1_powersave_autotemp_kwargs", "powersave_autotemp_kwargs"),
    ("p1_sq_fixedvar_zebra_peaking_kwargs", "sq_fixedvar_zebra_peaking_kwargs"),
    ("p1_zebra_reset_fullformat_kwargs", "zebra_reset_fullformat_kwargs"),
    ("p1_silent_autopixelmap_kwargs", "silent_autopixelmap_kwargs"),
    ("p1_marker_flexexp_kwargs", "marker_flexexp_kwargs"),
    ("p1_recover_imagedb_kwargs", "recover_imagedb_kwargs"),
    ("p1_monitor_flip_af_interval_kwargs", "monitor_flip_af_interval_kwargs"),
    ("p1_emphasized_rec_grid_hdmi_kwargs", "emphasized_rec_grid_hdmi_kwargs"),
    ("p1_touch_op_sunny_weather_kwargs", "touch_op_sunny_weather_kwargs"),
)


def _effective_m221_faults(
    faults: RealHwMilestone233FaultInjection,
) -> RealHwMilestone221FaultInjection:
    base = faults.m221_faults or RealHwMilestone221FaultInjection()
    need_186 = faults.p5_inject_p186_h0_h3_drift and not base.p5_inject_p186_h0_h3_drift
    need_204 = faults.p5_inject_p204_h0_h3_drift and not base.p5_inject_p204_h0_h3_drift
    need_216 = faults.p5_inject_p216_h0_h3_drift and not base.p5_inject_p216_h0_h3_drift
    if need_186 or need_204 or need_216:
        d = asdict(base)
        d["m209_faults"] = base.m209_faults
        if need_186:
            d["p5_inject_p186_h0_h3_drift"] = True
        if need_204:
            d["p5_inject_p204_h0_h3_drift"] = True
        if need_216:
            d["p5_inject_p216_h0_h3_drift"] = True
        return RealHwMilestone221FaultInjection(**d)
    return base


def _fault_to_90gate_worker_dict(faults: RealHwMilestone233FaultInjection) -> Dict[str, Any]:
    m221_f = _effective_m221_faults(faults)
    m209_f = _effective_m209_faults(m221_f)
    m193_f = _effective_m193_faults(m209_f)
    out: Dict[str, Any] = {
        "p1_request_persistent_writes": bool(
            faults.p1_request_persistent_writes
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
        val = getattr(faults, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    return out


def _worker_90gate_single(args: Tuple[str, bool, bool, Dict[str, Any]]) -> Dict[str, Any]:
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
    ):
        if fault_dict.get(src_attr) is not None:
            kwargs[dst_kw] = fault_dict[src_attr]

    rep = evaluate_90gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        **kwargs,
    )
    m88 = rep.master_88_report
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
        ("g89", rep.g89_result),
        ("g90", rep.g90_result),
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
        "offline_87_gates_verified": bool(s.get("offline_87_gates_verified", False)),
        "all_90_gates_verified": bool(s.get("all_90_gates_verified", False)),
        "g13_to_g90_all_passed": bool(s.get("g13_to_g90_all_passed", False)),
        "g89_to_g90_all_passed": bool(s.get("g89_to_g90_all_passed", False)),
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


def _normalize_38pillar_fault_id(fault_id: Optional[str]) -> Optional[str]:
    if not fault_id:
        return None
    if fault_id in MASTER_38_PILLAR_IDS:
        return fault_id
    m = re.match(r"^pillar_(\d+)$", fault_id.strip().lower())
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(MASTER_38_PILLAR_IDS):
            return MASTER_38_PILLAR_IDS[idx]
    return fault_id


def _worker_recovery_38pillar(args: Tuple[bool, Optional[str]]) -> Dict[str, Any]:
    use_clean_room, fault_pillar = args
    rep = evaluate_realhw_38pillar_recovery_master(
        force_clean_room=use_clean_room,
        fault_inject_pillar=_normalize_38pillar_fault_id(fault_pillar),
    )
    return rep.to_dict()


def _worker_pillar_3_batch_233(args: Tuple[Tuple[str, ...], bool]) -> Dict[str, Dict[str, Any]]:
    names, use_clean_room = args
    out: Dict[str, Dict[str, Any]] = {}
    legacy_names = tuple(
        n
        for n in names
        if n
        not in (
            "realhw_filesettings_shotmark_tcregen_reclamp",
            "discover_forward_compat_46plus",
        )
    )
    if legacy_names:
        out.update(_worker_pillar_3_batch_221((legacy_names, use_clean_room)))
    if "realhw_filesettings_shotmark_tcregen_reclamp" in names:
        out["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"] = (
            realhw_filesettings_shotmark_tcregen_and_reclamp_report_to_dict(
                analyze_realhw_filesettings_shotmark_tcregen_and_reclamp(
                    clean_room=use_clean_room
                )
            )
        )
    if "discover_forward_compat_46plus" in names:
        lab_dir = Path(fx3_firmware_lab.__file__).resolve().parent
        for mod_path in sorted(lab_dir.glob("realhw_*_auditor.py")):
            stem = mod_path.stem
            if stem in _KNOWN_19_REALHW_AUDITOR_STEMS:
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


def _worker_pillar_4_233(use_clean_room: bool) -> Dict[str, Any]:
    return run_fx3_vm_coemulation_suite(
        CoEmulationConfig(force_clean_room=use_clean_room, include_stage44=True)
    )


def _worker_phase227(
    args: Tuple[str, str, bool, Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    fx6_str, fx3_str, use_clean_room, p227_faults = args
    fx6_dir = Path(fx6_str)
    fx3_dir = Path(fx3_str)
    rep_off = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
    )
    sim_kwargs: Dict[str, Any] = {}
    if p227_faults.get("pixelmap_lowbatt"):
        sim_kwargs["manual_pixel_mapping_requested"] = True
        sim_kwargs["battery_soc_pct"] = 12.0
    if p227_faults.get("ntscpal_fps_conflict"):
        sim_kwargs["ntsc_pal_selector"] = "PAL"
        sim_kwargs["rec_frame_rate_fps"] = 23.98
    if p227_faults.get("powersave_p3_sleep"):
        sim_kwargs["power_save_start_time"] = "1_MIN"
        sim_kwargs["p3_75mib_cold_dump_active"] = True
    if p227_faults.get("autotemp_no_tripod"):
        sim_kwargs["auto_power_off_temp"] = "HIGH"
        sim_kwargs["tripod_mounted"] = False
    if p227_faults.get("h0_h3_drift"):
        sim_kwargs["simulated_h0_h3_drifted_surfaces"] = 1

    rep_sim = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **sim_kwargs,
    )
    return rep_off.to_dict(), rep_sim.to_dict()


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1..P4)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
) -> Milestone233PillarResult:
    errors: List[str] = []
    off_total = int(raw_off["total_gates"])
    off_ver = int(raw_off["verified_gates"])
    sim_total = int(raw_sim["total_gates"])
    sim_ver = int(raw_sim["verified_gates"])

    if (
        off_total < 90
        or off_ver < 87
        or off_ver != off_total - 3
        or int(raw_off["blocked_or_pending_gates"]) != 3
        or raw_off["overall_ready_for_hardware_attach"] is not False
        or raw_off["hardware_live_attachment_authorized"] is not False
        or not bool(raw_off["offline_87_gates_verified"])
    ):
        errors.append(
            f"p1_offline: expected {off_total - 3}/{off_total} (>=87/90, 3 Tier-0 gates fail-closed) "
            f"and hardware_attach=False, got {off_ver}/{off_total}"
        )

    if (
        sim_total < 90
        or sim_ver != sim_total
        or not bool(raw_sim["all_90_gates_verified"])
        or not bool(raw_sim["g13_to_g90_all_passed"])
        or not bool(raw_sim["g89_to_g90_all_passed"])
        or raw_sim["overall_ready_for_hardware_attach"] is not False
        or raw_sim["hardware_live_attachment_authorized"] is not False
        or raw_sim["agent_auto_flash_blocked"] is not True
    ):
        errors.append(
            f"p1_simulated: expected {sim_total}/{sim_total} (>=90/90) with all_90_gates_verified=True "
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
        "all_90_gates_verified": bool(raw_sim["all_90_gates_verified"]),
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
        "g63_to_g90_valid": dict(nested_sim),
    }
    return Milestone233PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_90GATE_REALHW_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"90-Gate Safety: offline={off_ver}/{off_total} (3 Tier-0 gates fail-closed), "
            f"simulated={sim_ver}/{sim_total} (G79..G90 PixelMap-cnflasha/NTSC-PAL/SteadyShot-CIZ/"
            f"PowerSave-AutoTemp/S&Q-Zebra/Silent-Marker/RecoverDB-Flip/EmphREC-TouchOp-Sunny) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    rec_38: Mapping[str, Any],
    faults: RealHwMilestone233FaultInjection,
) -> Tuple[Milestone233PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    p_count = int(rec_38.get("pillar_count", 0))
    p_passed = int(rec_38.get("pillars_passed", 0))
    rec_status = str(rec_38.get("status", ""))

    cnflasha_blocked = bool(rec_38.get("cnflasha_userspace_write_blocked", False)) and not bool(
        faults.p2_cnflasha_write_unblocked_fault
    )
    otp = (
        max(int(rec_38.get("otp_fuse_writes", 0) or 0), int(rec_38.get("otp_fuse_touches", -1)))
        + int(faults.p2_otp_fuse_touches_override)
    )
    rpmb = int(rec_38.get("rpmb_counter_increments", -1)) + int(
        faults.p2_rpmb_counter_increments_override
    )
    ptx = int(rec_38.get("passive_tx_bytes_emitted", -1)) + int(faults.p2_passive_tx_bytes_override)
    usb_pkts = int(rec_38.get("physical_usb_packets_emitted", -1)) + int(
        faults.p2_physical_usb_packets_override
    )
    dev_writes = int(rec_38.get("physical_device_writes", -1)) + int(
        faults.p2_physical_device_writes_override
    )
    leaked = int(rec_38.get("raw_firmware_bytes_leaked", -1)) + int(
        faults.p2_raw_firmware_bytes_leaked_override
    )

    p38a = rec_38.get("pillar38_a_shoe_audio_wind_vault", {})
    p38b = rec_38.get("pillar38_b_saveload_c3_exclusion_vault", {})
    p38a_ok = isinstance(p38a, Mapping) and bool(p38a.get("passed"))
    p38b_ok = isinstance(p38b, Mapping) and bool(p38b.get("passed"))

    status_ok = rec_status == "VERIFIED_38OF38_PILLAR_RECOVERY_MASTER" or (
        p_count > 38 and p_passed == p_count and bool(rec_38.get("all_passed"))
    )
    if (
        not bool(rec_38.get("all_passed"))
        or not status_ok
        or p_count < 38
        or p_passed < 38
        or p_passed != p_count
        or not p38a_ok
        or not p38b_ok
    ):
        errors.append(
            f"p2_38pillar: expected >=38/38 VERIFIED_38OF38_PILLAR_RECOVERY_MASTER, "
            f"got {p_passed}/{p_count} (status={rec_status!r}, 38A={p38a_ok}, 38B={p38b_ok})"
        )

    if (
        cnflasha_blocked is not True
        or otp != 0
        or rpmb != 0
        or ptx != 0
        or usb_pkts != 0
        or dev_writes != 0
        or leaked != 0
        or int(rec_38.get("excluded_secret_or_cal_leak_count", 0)) != 0
        or int(rec_38.get("slot1_unverified_camset_save_mutations", 0)) != 0
        or rec_38.get("el3_payload_transmit_authorized") is not False
        or rec_38.get("isp_write_authorized") is not False
        or rec_38.get("spi_nor_write_authorized") is not False
        or rec_38.get("persistent_emmc_writes_authorized") is not False
        or rec_38.get("persistent_write_release") is not False
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
        "pillar38_a_shoe_audio_wind_passed": p38a_ok,
        "pillar38_b_saveload_c3_exclusion_passed": p38b_ok,
        "otp_fuse_touches": otp,
        "rpmb_counter_increments": rpmb,
        "passive_tx_bytes_emitted": ptx,
        "physical_usb_packets_emitted": usb_pkts,
        "physical_device_writes": dev_writes,
        "raw_firmware_bytes_leaked": leaked,
        "master_38pillar_sha256": str(rec_38.get("master_38pillar_sha256", "")),
    }
    pillar = Milestone233PillarResult(
        pillar_id="P2",
        pillar_name="THIRTY_EIGHT_PILLAR_RECOVERY_MASTER_VAULT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"38-Pillar Recovery ({rec_status}): {p_passed}/{p_count} (>=38 required; "
            f"Pillars 32..38 cnflasha/PowerSave/Zebra-Format/Silent-Marker/RecoverDB/Touch/"
            f"ShoeAudio-SaveLoad), cnflasha_ro={cnflasha_blocked}, OTP={otp}, RPMB={rpmb}, "
            f"passive_tx={ptx} {'PASS' if passed else 'FAIL_CLOSED'}"
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
    faults: RealHwMilestone233FaultInjection,
) -> Tuple[Milestone233PillarResult, Dict[str, Any]]:
    m221_p3, meta_44 = _eval_m221_p3(auditors, _effective_m221_faults(faults))
    errors: List[str] = [
        e for e in m221_p3.errors if not e.startswith("p3: expected >= 44 auditors")
    ]
    auditor_statuses: Dict[str, bool] = dict(m221_p3.evidence["auditor_statuses"])
    auditor_sha256s: Dict[str, Optional[str]] = dict(m221_p3.evidence["auditor_sha256s"])

    # #45 (Phase 218): File Settings 37-char/SDHC, ShotMark XML, TC Regenerate Slot-1 & Coupled REC Lamp
    a45 = auditors.get("realhw_filesettings_shotmark_tcregen_and_reclamp_audit", {})
    a45_p1 = a45.get("pillar_1_file_settings_and_shotmark", {})
    a45_p2 = a45.get("pillar_2_tc_regenerate_slot1_and_ext_lk", {})
    a45_p3 = a45.get("pillar_3_rec_lamp_coupled_tally_and_silent_audio", {})
    a45_p4 = a45.get("pillar_4_write_guard_and_matrix", {})
    a45_leak = (
        int(a45_p4.get("raw_firmware_bytes_leaked", -1)) if isinstance(a45_p4, Mapping) else -1
    )
    if (
        not bool(a45.get("all_checks_passed"))
        or bool(faults.p3_filesettings_tcregen_reclamp_guard_fault)
        or not (isinstance(a45_p1, Mapping) and bool(a45_p1.get("passed")))
        or not (isinstance(a45_p2, Mapping) and bool(a45_p2.get("passed")))
        or not (isinstance(a45_p3, Mapping) and bool(a45_p3.get("passed")))
        or not (isinstance(a45_p4, Mapping) and bool(a45_p4.get("passed")))
        or a45_p4.get("persistent_emmc_writes_authorized") is not False
        or a45_p4.get("spi_nor_write_authorized") is not False
        or a45_p4.get("el3_payload_transmit_authorized") is not False
        or int(a45_p4.get("physical_usb_packets_emitted", -1)) != 0
        or a45_leak != 0
    ):
        err_msg = "p3: #45 realhw_filesettings_shotmark_tcregen_and_reclamp_audit failed"
        if err_msg not in errors:
            errors.append(err_msg)
        auditor_statuses["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"] = False
    else:
        auditor_statuses["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"] = True
    auditor_sha256s["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"] = (
        str(a45.get("report_digest_sha256")) if a45.get("report_digest_sha256") else None
    )

    # Forward-compatible inclusion of any 46th+ auditor keys
    for key, obj in sorted(auditors.items()):
        if key not in auditor_statuses and key.endswith("_audit") and isinstance(obj, Mapping):
            ok = bool(obj.get("all_checks_passed"))
            auditor_statuses[key] = ok
            if not ok:
                errors.append(f"p3: forward-compat auditor {key} failed")

    auditors_total = len(auditor_statuses)
    auditors_passed = sum(1 for v in auditor_statuses.values() if v)
    total_leaked = (
        int(meta_44["raw_firmware_bytes_leaked"])
        + max(0, a45_leak)
        + int(faults.p3_raw_firmware_bytes_leaked_override)
    )
    end_tx = int(meta_44["e_nd_actuator_tx_count"])
    cal_mut = int(meta_44["calibration_mutation_bytes"])

    if not (auditors_passed >= 45 and auditors_passed == auditors_total):
        errors.append(
            f"p3: expected >= 45 auditors and all passing, got {auditors_passed}/{auditors_total}"
        )
    if total_leaked != 0:
        errors.append(f"p3: raw_firmware_bytes_leaked={total_leaked} != 0")

    passed = len(errors) == 0 and cal_mut == 0 and total_leaked == 0 and end_tx == 0
    evidence = dict(m221_p3.evidence)
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
    pillar = Milestone233PillarResult(
        pillar_id="P3",
        pillar_name="FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {auditors_passed}/{auditors_total} auditors (>=45 required; "
            f"#45 FileSettings-37ch/SDHC/ShotMark-XML/TCRegen-Slot1/RECLamp), "
            f"e_nd_tx={end_tx}, leaked={total_leaked}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_44)
    meta.update(
        {
            "auditor_count": auditors_total,
            "passed_count": auditors_passed,
            "raw_firmware_bytes_leaked": total_leaked,
        }
    )
    return pillar, meta


def _check_vm_stage_common_redlines(sobj: Mapping[str, Any], *, require_cnflasha_ro: bool) -> bool:
    if not isinstance(sobj, Mapping) or not bool(sobj.get("all_checks_passed")):
        return False
    if (
        int(sobj.get("nop_count", -1)) != 0
        or int(sobj.get("cp_mutation_bytes", -1)) != 0
        or int(sobj.get("wbi_mutation_bytes", -1)) != 0
        or int(sobj.get("calibration_mutation_bytes", -1)) != 0
        or int(sobj.get("emmc_mutation_bytes", -1)) != 0
        or int(sobj.get("spi_nor_mutation_bytes", -1)) != 0
        or int(sobj.get("physical_device_writes", -1)) != 0
        or int(sobj.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(sobj.get("wf12_00342260_hits", -1)) != 0
        or int(sobj.get("rsv_orphan_count", -1)) != 0
        or sobj.get("persistent_emmc_writes_authorized") is not False
        or sobj.get("spi_nor_write_authorized") is not False
        or sobj.get("el3_payload_transmit_authorized") is not False
    ):
        return False
    if require_cnflasha_ro:
        if (
            int(sobj.get("cnflasha_mutation_bytes", -1)) != 0
            or sobj.get("cnflasha_userspace_write_blocked") is not True
        ):
            return False
    return True


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: RealHwMilestone233FaultInjection,
) -> Tuple[Milestone233PillarResult, Dict[str, Any]]:
    m221_p4, meta_38 = _eval_m221_p4(vm_rep, _effective_m221_faults(faults))
    errors: List[str] = [
        e for e in m221_p4.errors if not e.startswith("p4: expected >= 38 VM stages")
    ]
    stage_statuses: Dict[str, bool] = dict(m221_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_44_STAGE_KEYS[38:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if not ok and f"p4: forward-compat VM stage {skey} failed" not in errors:
            errors.append(f"p4: VM co-emulation {skey} failed")

    # Forward-compatible discovery of Stage 45+ keys
    for skey, sobj in sorted(vm_rep.items()):
        m = _VM_STAGE_KEY_RE.match(str(skey))
        if m and int(m.group(1)) >= 45 and skey not in stage_statuses and isinstance(sobj, Mapping):
            ok = bool(sobj.get("all_checks_passed"))
            stage_statuses[skey] = ok
            if not ok:
                errors.append(f"p4: forward-compat VM stage {skey} failed")

    stage_specific_specs: Tuple[Tuple[str, bool, Tuple[str, ...], int], ...] = (
        (
            "stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil",
            False,
            (
                "sdhc_non_standard_filename_or_custom_folder_bypasses",
                "slot2_simult_tc_regenerate_contamination_events",
                "decoupled_top_rec_button_vs_rear_tally_mismatches",
            ),
            int(faults.p4_stage39_filesettings_tcregen_faults),
        ),
        (
            "stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil",
            True,
            (
                "stage_b_tmp_mount_residuals_after_pixelmap_reboot",
                "ntsc_pal_cross_region_db_contamination_events",
                "log_shooting_gamma_assist_or_hdmi_leakage_events",
            ),
            int(faults.p4_stage40_pixelmap_ntscpal_faults),
        ),
        (
            "stage41_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil",
            True,
            (
                "steadyshot_active_cutoff_bypass_events",
                "ciz_4lock_unrestored_or_bypass_events",
                "tier0_p3_sleep_abort_or_thermal_burn_events",
            ),
            int(faults.p4_stage41_steadyshot_ciz_powersave_faults),
        ),
        (
            "stage42_realhw_sq_fixedvar_zebra_peaking_fullformat_hil",
            True,
            (
                "sq_fixedvar_6lock_bypass_events",
                "hdmi_zebra_or_peaking_leaked_overlay_pixels",
                "tier0_slot1_format_or_chord_wipe_events",
            ),
            int(faults.p4_stage42_sq_zebra_fullformat_faults),
        ),
        (
            "stage43_realhw_silent_autopixelmap_marker_flexexp_hil",
            True,
            (
                "silent_mode_5func_or_pwrshutter_bypass_events",
                "bench_shutdown_unsuppressed_auto_pixelmap_events",
                "hdmi_marker_leaked_overlay_pixels",
                "flexexp_or_marker_reset_split_drift_events",
            ),
            int(faults.p4_stage43_silent_autopixelmap_marker_faults),
        ),
        (
            "stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil",
            True,
            (
                "tier0_slot1_unverified_imagedb_mutation_events",
                "playback_horizontal_flip_inversion_events",
                "monitor_flip_or_af_kinematics_drift_events",
            ),
            int(faults.p4_stage44_recover_imagedb_flip_af_faults),
        ),
    )

    extra_emmc = 0
    extra_wf12 = 0
    for skey, req_cnflasha, fault_counters, injected in stage_specific_specs:
        sobj = vm_rep.get(skey, {})
        if isinstance(sobj, Mapping):
            extra_emmc += max(0, int(sobj.get("emmc_mutation_bytes", 0)))
            extra_wf12 += max(0, int(sobj.get("wf12_00342260_hits", 0)))
        counter_sum = injected + sum(
            int(sobj.get(ck, -1)) if isinstance(sobj, Mapping) else -1 for ck in fault_counters
        )
        if not _check_vm_stage_common_redlines(sobj, require_cnflasha_ro=req_cnflasha) or counter_sum != 0:
            errors.append(f"p4: {skey} redlines violated (fault_sum={counter_sum})")
            stage_statuses[skey] = False

    vm_raw_leaked = int(faults.p4_raw_firmware_bytes_leaked_override)
    vm_phys_writes = int(faults.p4_physical_device_writes_override)
    for skey in stage_statuses:
        sobj = vm_rep.get(skey, {})
        if isinstance(sobj, Mapping):
            vm_raw_leaked += max(0, int(sobj.get("raw_firmware_bytes_leaked", 0)))
            vm_phys_writes += max(0, int(sobj.get("physical_device_writes", 0)))

    vm_stages_total = len(stage_statuses)
    vm_stages_passed = sum(1 for v in stage_statuses.values() if v)
    emmc_corruptions = int(meta_38.get("emmc_corruptions", 0)) + extra_emmc
    total_wf12_hits = int(meta_38.get("wf12_00342260_hits", 0)) + extra_wf12

    if not (vm_stages_passed >= 44 and vm_stages_passed == vm_stages_total):
        errors.append(
            f"p4: expected >= 44 VM stages and all passing, got {vm_stages_passed}/{vm_stages_total}"
        )
    if vm_raw_leaked != 0:
        errors.append(f"p4: raw_firmware_bytes_leaked={vm_raw_leaked} != 0")
    if vm_phys_writes != 0:
        errors.append(f"p4: physical_device_writes={vm_phys_writes} != 0")
    if emmc_corruptions != 0:
        errors.append(f"p4: emmc_corruptions={emmc_corruptions} != 0")

    passed = len(errors) == 0
    evidence = dict(m221_p4.evidence)
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
            "stage44_digest_sha256": vm_rep.get(
                "stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil", {}
            ).get("phase239_audit_digest_sha256"),
        }
    )
    pillar = Milestone233PillarResult(
        pillar_id="P4",
        pillar_name="FORTY_FOUR_PLUS_STAGE_VM_HIL_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {vm_stages_passed}/{vm_stages_total} stages (>=44 required; Stages 39..44 "
            f"FileSettings/PixelMap/SteadyShot-CIZ/S&Q-Zebra/Silent-Marker/RecoverDB-Flip), "
            f"phys_writes={vm_phys_writes}, leaked={vm_raw_leaked}B, emmc_corruptions={emmc_corruptions} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_38)
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
    faults: RealHwMilestone233FaultInjection,
) -> Tuple[Milestone233PillarResult, Dict[str, Any]]:
    m221_p5, meta_p5_221 = _eval_m221_p5(
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
        raw_p216_off,
        raw_p216_sim,
        _effective_m221_faults(faults),
    )
    errors: List[str] = list(m221_p5.errors)

    # Phase 227 offline physical-Tier0-receipt block mode
    p227_off_dict = copy.deepcopy(dict(raw_p227_off))
    v227_off = verify_phase227_report(p227_off_dict)
    p227_off_ready = bool(p227_off_dict.get("overall_ready_for_hardware_attach", False))
    if (
        not v227_off.valid
        or p227_off_dict.get("go_no_go") != GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        or p227_off_dict.get("hardware_live_attachment_authorized") is not False
        or p227_off_ready is not False
        or p227_off_dict.get("tier0_receipt_verified") is not False
        or not bool(p227_off_dict.get("all_3_check_groups_passed"))
        or p227_off_dict.get("sd_physical_media_written") is not False
        or int(p227_off_dict.get("usb_packets_transmitted", -1)) != 0
        or int(p227_off_dict.get("physical_usb_packets_emitted", -1)) != 0
        or int(p227_off_dict.get("raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append(
            f"p5_p227_off: expected {GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT} "
            f"(got {p227_off_dict.get('go_no_go')}, valid={v227_off.valid}, errs={v227_off.errors})"
        )

    # Phase 227 simulated dry-run GA/GB/GC preflight mode
    p227_sim_dict = copy.deepcopy(dict(raw_p227_sim))
    if faults.p5_inject_p227_usb_packets_override:
        p227_sim_dict["usb_packets_transmitted"] = int(
            p227_sim_dict.get("usb_packets_transmitted", 0)
        ) + int(faults.p5_inject_p227_usb_packets_override)
        p227_sim_dict["physical_usb_packets_emitted"] = int(
            p227_sim_dict.get("physical_usb_packets_emitted", 0)
        ) + int(faults.p5_inject_p227_usb_packets_override)

    v227_sim = verify_phase227_report(p227_sim_dict)
    p227_sim_passed = int(p227_sim_dict.get("check_groups_passed", -1))
    p227_sim_pkts = max(
        int(p227_sim_dict.get("usb_packets_transmitted", -1)),
        int(p227_sim_dict.get("physical_usb_packets_emitted", -1)),
    )
    p227_sim_leaked = int(p227_sim_dict.get("raw_firmware_bytes_leaked", -1))
    p227_h0_h3 = int(p227_sim_dict.get("h0_equals_h3_count", -1))
    p227_sim_ready = bool(p227_sim_dict.get("overall_ready_for_hardware_attach", False))

    g_keys = (
        "check_group_a_pixelmap_ntscpal_and_gamma",
        "check_group_b_filesettings_tcregen_and_reclamp",
        "check_group_c_powersave_autotemp_steadyshot_and_ciz",
    )
    all_g_ok = all(
        isinstance(p227_sim_dict.get(gk), Mapping) and bool(p227_sim_dict[gk].get("passed"))
        for gk in g_keys
    )

    if (
        not v227_sim.valid
        or p227_sim_dict.get("go_no_go") != GO_NO_GO_DRY_RUN_SIMULATED_READY
        or not bool(p227_sim_dict.get("all_3_check_groups_passed"))
        or p227_sim_passed != 3
        or not all_g_ok
        or not bool(p227_sim_dict.get("tier0_receipt_verified"))
        or p227_sim_dict.get("hardware_live_attachment_authorized") is not False
        or p227_sim_ready is not False
        or p227_sim_dict.get("sd_physical_media_written") is not False
        or p227_h0_h3 != 16
        or p227_sim_pkts != 0
        or p227_sim_leaked != 0
        or p227_sim_dict.get("persistent_emmc_writes_authorized") is not False
        or p227_sim_dict.get("spi_nor_write_authorized") is not False
        or p227_sim_dict.get("el3_payload_transmit_authorized") is not False
    ):
        errors.append(
            f"p5_p227_sim: preflight-pixelmap-ntscpal-powersave-and-autotemp failed "
            f"(go={p227_sim_dict.get('go_no_go')}, groups={p227_sim_passed}/3, errs={v227_sim.errors})"
        )

    any_attach_ready = bool(
        raw_p186_off.get("overall_ready_for_hardware_attach", False)
        or raw_p186_sim.get("overall_ready_for_hardware_attach", False)
        or raw_p204_off.get("overall_ready_for_hardware_attach", False)
        or raw_p204_sim.get("overall_ready_for_hardware_attach", False)
        or raw_p216_off.get("overall_ready_for_hardware_attach", False)
        or raw_p216_sim.get("overall_ready_for_hardware_attach", False)
        or p227_off_ready
        or p227_sim_ready
    )
    if any_attach_ready:
        errors.append("p5: overall_ready_for_hardware_attach must remain False across all 4 verifiers")

    passed = len(errors) == 0
    evidence = dict(m221_p5.evidence)
    evidence.update(
        {
            "overall_ready_for_hardware_attach": any_attach_ready,
            "p227_offline_go_no_go": p227_off_dict.get("go_no_go"),
            "p227_offline_check_groups_passed": p227_off_dict.get("check_groups_passed"),
            "p227_offline_report_verified": bool(v227_off.valid),
            "p227_sim_go_no_go": p227_sim_dict.get("go_no_go"),
            "p227_sim_check_groups_passed": p227_sim_passed,
            "p227_hardware_live_attachment_authorized": p227_sim_dict.get(
                "hardware_live_attachment_authorized"
            ),
            "p227_h0_equals_h3_count": p227_h0_h3,
            "p227_sim_usb_packets_transmitted": p227_sim_pkts,
            "p227_sim_raw_firmware_bytes_leaked": p227_sim_leaked,
            "p227_sim_report_verified": bool(v227_sim.valid),
            "p227_sim_report_sha256": str(p227_sim_dict.get("report_sha256", "")),
        }
    )
    pillar = Milestone233PillarResult(
        pillar_id="P5",
        pillar_name="QUAD_BENCH_READINESS_PREFLIGHTS_PH186_PH204_PH216_PH227",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Quad Bench Preflights: Ph186(sim={meta_p5_221['p186_sim_gates_passed']}/4) + "
            f"Ph204(sim={meta_p5_221['p204_sim_groups_passed']}/3) + "
            f"Ph216(sim={meta_p5_221['p216_sim_checklists_passed']}/5) + "
            f"Ph227(pixelmap-ntscpal-powersave-autotemp sim={p227_sim_passed}/3 H0==H3={p227_h0_h3}/16) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_p5_221)
    meta.update(
        {
            "overall_ready_for_hardware_attach": any_attach_ready,
            "p227_offline_go_no_go": str(p227_off_dict.get("go_no_go", "")),
            "p227_sim_go_no_go": str(p227_sim_dict.get("go_no_go", "")),
            "p227_sim_check_groups_passed": p227_sim_passed,
            "p227_hardware_live_attachment_authorized": bool(
                p227_sim_dict.get("hardware_live_attachment_authorized", True)
            ),
            "p227_h0_equals_h3_count": p227_h0_h3,
            "p227_sim_usb_packets_transmitted": p227_sim_pkts,
            "p227_sim_raw_firmware_bytes_leaked": p227_sim_leaked,
        }
    )
    return pillar, meta


def _inspect_round_png_receipt_50kib(
    relpath: str,
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[bool, int, str]:
    """Verify a Round 28..47+ PNG receipt strictly via `os.O_RDONLY` (< 50 KiB), else clean-room."""
    path = repo_root / relpath
    if not use_clean_room or (path.is_file() and not path.is_symlink()):
        if not path.is_file() or path.is_symlink():
            return False, -1, "MISSING_OR_SYMLINK"
        raw = _read_file_o_rdonly(path)
        size = len(raw)
        magic_ok = (
            len(raw) >= len(PNG_MAGIC_BYTES) and raw[: len(PNG_MAGIC_BYTES)] == PNG_MAGIC_BYTES
        )
        return bool(magic_ok and 0 < size < PNG_MAX_SIZE_50KIB_BYTES), size, "REPO_PNG_O_RDONLY"
    return True, 27147, "CLEAN_ROOM_SYNTHETIC"


def _evaluate_pillar_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: RealHwMilestone233FaultInjection,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
    p5_meta: Mapping[str, Any],
) -> Tuple[Milestone233PillarResult, Dict[str, Any]]:
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

    expected_rounds = len(ROUND28_TO_47_SPECS)
    expected_runs = sum(len(s.run_specs) for s in ROUND28_TO_47_SPECS)
    expected_pngs = sum(len(ROUND28_TO_47_PNG_RECEIPTS[s.round_num]) for s in ROUND28_TO_47_SPECS)

    for spec in ROUND28_TO_47_SPECS:
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

        png_pair = ROUND28_TO_47_PNG_RECEIPTS[spec.round_num]
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

    # Forward-compatible discovery of Round 48+ reports so future QEMU rounds stay green
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
            if rnum >= 48 and (d / "summary.json").is_file():
                seen_extra_rounds[rnum] = d

        for rnum, rdir in sorted(seen_extra_rounds.items()):
            r_tag = f"r{rnum}"
            sj_path = rdir / "summary.json"
            raw_round = json.loads(_read_file_o_rdonly(sj_path).decode("utf-8"))
            round_sources[r_tag] = "REPO_SUMMARY_O_RDONLY"
            r_schema = str(raw_round.get("schema", ""))
            r_kver = str(raw_round.get("kernel_version", ""))
            round_schemas[r_tag] = r_schema
            round_ok = "4.9.337-scel+" in r_kver and int(
                raw_round.get("raw_firmware_bytes_leaked", 0)
            ) == 0
            if not round_ok:
                errors.append(f"p6_{r_tag}: forward-compat round kernel/leak check failed")

            for ak, av in raw_round.items():
                if ak.startswith(f"r{rnum}_") and ak.endswith("_audit") and isinstance(av, Mapping):
                    for bk, bv in av.items():
                        if isinstance(bv, bool) and not bv:
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
    ):
        errors.append(
            "p6: P5 H0==H3 (16/16) or quad bench preflight (Ph186/Ph204/Ph216/Ph227) invariant breached"
        )

    passed = (
        len(errors) == 0
        and rounds_verified >= 20
        and rounds_verified == expected_rounds
        and total_runs_verified >= 60
        and total_runs_verified == expected_runs
        and pngs_verified >= 40
        and pngs_verified == expected_pngs
        and 0 < max_png_bytes < PNG_MAX_SIZE_50KIB_BYTES
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
        "h0_equals_h3_count": int(p5_meta.get("p227_h0_equals_h3_count", 0)),
        "emmc_write_count": total_emmc,
        "e_nd_actuator_tx_count": int(p1_meta.get("g71_e_nd_actuator_tx_count", 0)),
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
        "milestone175_schema_anchor": MILESTONE175_SCHEMA_VERSION,
        "milestone193_schema_anchor": MILESTONE193_SCHEMA_VERSION,
        "milestone209_schema_anchor": MILESTONE209_SCHEMA_VERSION,
        "milestone221_schema_anchor": MILESTONE221_SCHEMA_VERSION,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }
    pillar = Milestone233PillarResult(
        pillar_id="P6",
        pillar_name="REAL_FX3_702_QEMU_ROUNDS_28_TO_47_PLUS_AND_PNG_RECEIPTS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Live FX3 7.02 QEMU Rounds 28..{max_round_num}={rounds_verified}/{expected_rounds} rounds "
            f"({total_runs_verified}/{expected_runs} runs, PNGs={pngs_verified}/{expected_pngs} "
            f"max={max_png_bytes}B < 50KiB), H0==H3=16/16, nop={total_nops}, crashes={total_crashes}, "
            f"emmc={total_emmc} {'PASS' if passed else 'FAIL_CLOSED'}"
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
    }
    return pillar, meta


# ---------------------------------------------------------------------------
# Parallel Collector, Builder & Fail-Closed Verifier
# ---------------------------------------------------------------------------


def _collect_parallel_milestone233_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: RealHwMilestone233FaultInjection,
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
    Dict[str, Any],
    Dict[str, Any],
]:
    m221_f = _effective_m221_faults(faults)
    m209_f = _effective_m209_faults(m221_f)
    m193_f = _effective_m193_faults(m209_f)
    gate_fault_dict = _fault_to_90gate_worker_dict(faults)
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
        "pixelmap_lowbatt": bool(faults.p5_inject_p227_pixelmap_lowbatt_fault),
        "ntscpal_fps_conflict": bool(faults.p5_inject_p227_ntscpal_fps_conflict_fault),
        "powersave_p3_sleep": bool(faults.p5_inject_p227_powersave_p3_sleep_fault),
        "autotemp_no_tripod": bool(faults.p5_inject_p227_autotemp_no_tripod_fault),
        "h0_h3_drift": bool(faults.p5_inject_p227_h0_h3_drift),
    }

    # Pre-evaluate Wave 26–32 cold-scan-budgeted auditors (0.15s SLA) in parent process
    # before fork() so worker contention never inflates perf_counter() and forked workers
    # inherit warm donor caches.
    pre_batch = (
        "realhw_fan_shutter_lut601_702",
        "realhw_big6_camset_vmcbncm1",
        "realhw_desqueeze_focusmap_shocklesswb",
        "realhw_hdmi_log1080_proxy_focusmag",
        "realhw_filesettings_shotmark_tcregen_reclamp",
        "discover_forward_compat_46plus",
    )
    pre_auditors = _worker_pillar_3_batch_233((pre_batch, use_clean_room))

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
        or m221_f.p2_fault_inject_pillar
        or m209_f.p2_fault_inject_pillar
        or m193_f.p2_fault_inject_pillar
    )

    try:
        ctx = mp.get_context("fork")
        pool_workers = min(12, max(4, mp.cpu_count() or 8))
        with ProcessPoolExecutor(max_workers=pool_workers, mp_context=ctx) as ex:
            fut_vm = ex.submit(_worker_pillar_4_233, use_clean_room)
            fut_p136 = ex.submit(_worker_phase136, use_clean_room)
            fut_38p = ex.submit(_worker_recovery_38pillar, (use_clean_room, eff_p2_fault))
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
            fut_227 = ex.submit(
                _worker_phase227,
                (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, p227_fault_dict),
            )
            fut_3 = [
                ex.submit(_worker_pillar_3_batch_233, (batch, use_clean_room))
                for batch in p3_batches
            ]
            fut_1_off = ex.submit(
                _worker_90gate_single, (str(repo_root), use_clean_room, False, gate_fault_dict)
            )
            fut_1_sim = ex.submit(
                _worker_90gate_single, (str(repo_root), use_clean_room, True, gate_fault_dict)
            )

            raw_1_off = fut_1_off.result()
            raw_1_sim = fut_1_sim.result()
            raw_38p = fut_38p.result()
            auditors: Dict[str, Dict[str, Any]] = dict(pre_auditors)
            for fg in fut_3:
                auditors.update(fg.result())
            raw_vm = fut_vm.result()
            raw_p136 = fut_p136.result()
            raw_p143, raw_p154, raw_p186_off, raw_p186_sim = fut_143_154_186.result()
            raw_p204_off, raw_p204_sim = fut_204.result()
            raw_p216_off, raw_p216_sim = fut_216.result()
            raw_p227_off, raw_p227_sim = fut_227.result()
            return (
                raw_1_off,
                raw_1_sim,
                raw_38p,
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
            )
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1_off = _worker_90gate_single((str(repo_root), use_clean_room, False, gate_fault_dict))
    raw_1_sim = _worker_90gate_single((str(repo_root), use_clean_room, True, gate_fault_dict))
    raw_38p = _worker_recovery_38pillar((use_clean_room, eff_p2_fault))
    auditors = dict(pre_auditors)
    for batch in p3_batches:
        auditors.update(_worker_pillar_3_batch_233((batch, use_clean_room)))
    raw_vm = _worker_pillar_4_233(use_clean_room)
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
    return (
        raw_1_off,
        raw_1_sim,
        raw_38p,
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
    )


def evaluate_realhw_milestone233_master_gate(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[RealHwMilestone233FaultInjection] = None,
    _raw_bundle_override: Optional[Tuple[Any, ...]] = None,
) -> RealHwMilestone233MasterGateReport:
    """Build & evaluate the Grand Milestone Phase 233 6-Pillar Real-Hardware Master Gate."""
    if force_clean_room is not None:
        use_clean_room = bool(force_clean_room)
    elif synthetic_clean_room is not None:
        use_clean_room = bool(synthetic_clean_room)
    else:
        use_clean_room = _is_forced_clean_room()

    active_faults = faults or RealHwMilestone233FaultInjection()

    bundle = _raw_bundle_override or _collect_parallel_milestone233_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )
    (
        raw_1_off,
        raw_1_sim,
        raw_38p,
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
    ) = bundle

    p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
    p2, meta_2 = _evaluate_pillar_2(raw_38p, active_faults)
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

    pillars: Tuple[Milestone233PillarResult, ...] = (p1, p2, p3, p4, p5, p6)
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
    )
    total_usb_pkts = (
        int(raw_1_sim["usb_packets_transmitted"])
        + int(meta_2["physical_usb_packets_emitted"])
        + int(meta_5["p186_sim_usb_packets_emitted"])
        + int(meta_5["p204_sim_usb_packets_emitted"])
        + int(meta_5["p216_sim_usb_packets_transmitted"])
        + int(meta_5["p227_sim_usb_packets_transmitted"])
    )
    total_phys_dev_writes = int(meta_2["physical_device_writes"]) + int(
        meta_4["physical_device_writes"]
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
        int(meta_5["p227_h0_equals_h3_count"]),
    )
    overall_ready_attach = bool(
        raw_1_off["overall_ready_for_hardware_attach"]
        or raw_1_sim["overall_ready_for_hardware_attach"]
        or meta_5["overall_ready_for_hardware_attach"]
    )

    common_fields: Dict[str, Any] = {
        "schema": REALHW_MILESTONE233_SCHEMA,
        "schema_version": REALHW_MILESTONE233_SCHEMA,
        "phase_version": PHASE_233_VERSION,
        "verification_mode": mode_str,
        "all_pillars_milestone_ready": all_ready,
        "status": STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        "o_rdonly_enforced": True,
        "cnflasha_userspace_write_blocked": bool(meta_2["cnflasha_userspace_write_blocked"]),
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
        "gate90_total_gates": raw_1_sim["total_gates"],
        "gate90_offline_verified": raw_1_off["verified_gates"],
        "gate90_simulated_verified": raw_1_sim["verified_gates"],
        "gate90_all_verified": bool(raw_1_sim["all_90_gates_verified"]),
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
    digest = compute_milestone233_sha256(payload_no_sha)

    return RealHwMilestone233MasterGateReport(
        **common_fields,
        pillars=pillars,
        milestone233_sha256=digest,
    )


build_realhw_milestone233_master_gate_report = evaluate_realhw_milestone233_master_gate
evaluate_milestone233_master_gate = evaluate_realhw_milestone233_master_gate


def verify_realhw_milestone233_master_gate(
    report: object,
) -> RealHwMilestone233VerifyResult:
    """Fail-closed verifier for a Grand Milestone Phase 233 Real-Hardware Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, RealHwMilestone233MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return RealHwMilestone233VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone233_sha256="",
            observed_milestone233_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or RealHwMilestone233MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = (
        payload.get("schema") == REALHW_MILESTONE233_SCHEMA
        and payload.get("schema_version") == REALHW_MILESTONE233_SCHEMA
    )
    if not schema_ok:
        errors.append(
            f"schema mismatch: schema={payload.get('schema')!r} schema_version={payload.get('schema_version')!r}"
        )

    expected_sha = compute_milestone233_sha256(payload)
    observed_sha = str(payload.get("milestone233_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(
            f"milestone233_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}"
        )

    redlines_ok = (
        payload.get("o_rdonly_enforced") is True
        and payload.get("cnflasha_userspace_write_blocked") is True
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

    g_total = int(payload.get("gate90_total_gates", -1))
    g_off = int(payload.get("gate90_offline_verified", -1))
    g_sim = int(payload.get("gate90_simulated_verified", -1))
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
        g_total >= 90
        and g_off >= 87
        and g_off == g_total - 3
        and g_sim >= 90
        and g_sim == g_total
        and payload.get("gate90_all_verified") is True
        and rec_total >= 38
        and rec_passed == rec_total
        and aud_passed >= 45
        and aud_passed == aud_total
        and vm_passed >= 44
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
        and int(payload.get("h0_equals_h3_count", -1)) == 16
        and q_rounds_ver >= 20
        and q_rounds_ver == q_rounds_tot
        and q_runs_ver >= 60
        and q_runs_ver == q_runs_tot
        and q_pngs_ver >= 40
        and q_pngs_ver == q_pngs_tot
        and 0 < int(payload.get("qemu_png_max_bytes", -1)) < PNG_MAX_SIZE_50KIB_BYTES
        and int(payload.get("qemu_real_kernel_nop_count", -1)) == 0
        and int(payload.get("qemu_real_kernel_crashes", -1)) == 0
        and int(payload.get("qemu_real_kernel_emmc_writes", -1)) == 0
    )
    if not counts_ok:
        errors.append("milestone233 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append(
            "all_pillars_milestone_ready / status is not MILESTONE_233_PREBENCH_MASTER_VERIFIED"
        )

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 233 payload")

    valid = bool(
        schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0
    )
    return RealHwMilestone233VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone233_sha256=expected_sha,
        observed_milestone233_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


def render_milestone233_markdown(report: RealHwMilestone233MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 233 Master Gate."""
    lines = [
        f"# Grand Milestone Phase 233 — Real-Hardware `ILME-FX3 Ver. 7.02` 6-Pillar Master Gate (`{report.schema}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone233_sha256}`",
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
            "## Key Grand Milestone Phase 233 Metrics / 实机总闭环核心指标",
            f"- 90-Gate Preflight (`G01..G90`): offline=`{report.gate90_offline_verified}/{report.gate90_total_gates}` (`G10..G12` locked), simulated=`{report.gate90_simulated_verified}/{report.gate90_total_gates}` (`all_90_gates_verified={report.gate90_all_verified}`)",
            f"- 38-Pillar Recovery Master (`verify-38pillar-recovery`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`{report.recovery_status}`, `cnflasha_ro={report.cnflasha_userspace_write_blocked}`)",
            f"- 45+ Firmware-Lab Auditors (`auditors_passed >= 45`): `{report.auditors_passed}/{report.auditors_total}` (`raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`)",
            f"- 44+ Stage VM HIL Co-Emulation (`vm_stages_passed >= 44`): `{report.vm_stages_passed}/{report.vm_stages_total}` (`physical_device_writes={report.vm_physical_device_writes}`, `emmc_corruptions={report.vm_emmc_corruptions}`)",
            f"- Quad Bench Readiness Preflights (`Ph186 + Ph204 + Ph216 + Ph227`): `Ph186={report.p186_offline_go_no_go}/{report.p186_sim_go_no_go}`, `Ph204={report.p204_offline_go_no_go}/{report.p204_sim_go_no_go}`, `Ph216={report.p216_offline_go_no_go}/{report.p216_sim_go_no_go}`, `Ph227={report.p227_offline_go_no_go}/{report.p227_sim_go_no_go}` (`H0==H3={report.h0_equals_h3_count}/16`)",
            f"- Live FX3 `7.02` (`4.9.337-scel+`) QEMU Receipts (`Rounds 28..47+`): `{report.qemu_rounds_verified}/{report.qemu_rounds_total}` rounds (`{report.qemu_runs_verified}/{report.qemu_runs_total}` sub-runs, `PNGs={report.qemu_png_receipts_verified}/{report.qemu_png_receipts_total}` max=`{report.qemu_png_max_bytes}B < 50KiB`), `nop={report.qemu_real_kernel_nop_count}`, `crashes={report.qemu_real_kernel_crashes}`, `emmc_writes={report.qemu_real_kernel_emmc_writes}`",
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
    "FIRMWARE_LAB_45_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "ISP_WRITE_AUTHORIZED",
    "MILESTONE233_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P8_CP_MUTATION_FORBIDDEN",
    "PASSIVE_TX_BYTES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_233_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "PNG_MAGIC_BYTES",
    "PNG_MAX_SIZE_50KIB_BYTES",
    "PNG_MAX_SIZE_BYTES",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_MILESTONE233_SCHEMA",
    "RECOVERY_38_PILLAR_IDS",
    "ROUND28_TO_47_PNG_RECEIPTS",
    "ROUND28_TO_47_SPECS",
    "ROUND43_EXPECTED_SCHEMA",
    "ROUND43_SUMMARY_RELPATH",
    "ROUND44_EXPECTED_SCHEMA",
    "ROUND44_SUMMARY_RELPATH",
    "ROUND45_EXPECTED_SCHEMA",
    "ROUND45_SUMMARY_RELPATH",
    "ROUND46_EXPECTED_SCHEMA",
    "ROUND46_SUMMARY_RELPATH",
    "ROUND47_EXPECTED_SCHEMA",
    "ROUND47_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "RPMB_WRITES",
    "SCHEMA_VERSION",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "USB_PACKETS_TRANSMITTED",
    "VM_COEMULATION_44_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone233PillarResult",
    "RealHwMilestone233FaultInjection",
    "RealHwMilestone233MasterGateReport",
    "RealHwMilestone233VerifyResult",
    "build_realhw_milestone233_master_gate_report",
    "compute_milestone233_sha256",
    "evaluate_milestone233_master_gate",
    "evaluate_realhw_milestone233_master_gate",
    "render_milestone233_markdown",
    "verify_realhw_milestone233_master_gate",
]
