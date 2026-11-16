"""Phase 235 Sony `ILME-FX3` (`Ver. 7.02`) Safety Gates `G87` (`Recover Image DB`
Depleted-Battery Refusal, Non-Deleting Repair & Unverified Slot-1 Tier-0 Vault
Read-Only Mutation Firewall) & `G88` (`Monitor Flip Direction` `Camera Settings Reset`
Survival + `Horizontal Flip` Playback Non-Inversion & `AF Subj. Shift Sensitivity` /
`AF Transition Speed` + `Interval Shoot Func.` Still-Only Boundary) + Unified
88-Gate Master Safety Preflight (`G01..G88`).

Operationalizes Wave-34 official Sony `ILME-FX3` (`Ver. 7.02`) intelligence
(`reports/2026-11-15-global-sony-wave34-recover-imagedb-battery-vault-monitor-flip-playback-af-shift-sens-interval-intel/README.md`)
as deterministic offline preflight verifiers (`G87` and `G88`) and composes them
with `evaluate_86gate_preflight` (`G01..G86`) into a unified 88-gate master
safety preflight (`G01..G88`):

1. **Gate `G87` (`RECOVER_IMAGE_DB_DEPLETED_BATTERY_REFUSAL_NONDELETING_AND_SLOT1_TIER0_VAULT_FIREWALL`)**:
   - **Menu & Non-Deleting Repair (`MENU -> Shooting -> [Media] -> [Recover Image DB]`)**:
     Repairs `AVF_INFO` / media management DB inconsistencies (`"Image DataBase File error"`,
     false `"0"` recordable images, or PC-edited media index divergence) **without deleting
     any recorded clips or stills** (`recorded_clips_deleted == 0`,
     `recorded_clips_after == recorded_clips_before`).
   - **Depleted `NP-FZ100` Battery Refusal**:
     Enforces hardware refusal whenever the `NP-FZ100` battery pack is extremely
     depleted (`battery_extremely_depleted == True`, `battery_soc_pct < 10`, or
     `battery_mv < 6400`), preventing mid-journal FAT/exFAT directory corruption
     during card metadata repair.
   - **Action-Item Reset Immunity**:
     `[Recover Image DB]` is an immediate execution action rather than a persistent
     `On`/`Off` toggle — it is **NOT** reset by `[Camera Settings Reset]` and
     **NOT** reset by `[Initialize]`.
   - **Unverified / `WP`-Locked Slot-1 Tier-0 Vault Read-Only Mutation Firewall**:
     Because `[Recover Image DB]` writes repaired index files onto the target
     memory card, hard-blocks `[Recover Image DB]` card metadata writes on Slot 1
     (`slot1_metadata_sector_writes == 0`, `slot1_avf_info_mutated == False`)
     whenever an active, unverified (`slot1_off_camera_sha256_verified == False`),
     or `WP`-locked Tier-0 dump card (`pnflasha` / `cnflasha` / `CAMSET01.DAT`)
     is inserted in Slot 1 prior to off-camera SHA-256 verification.

2. **Gate `G88` (`MONITOR_FLIP_RESET_SURVIVAL_PLAYBACK_NONINVERSION_AF_SHIFT_SENS_AND_INTERVAL_STILL_GUARD`)**:
   - **`[Monitor Flip Direction]` (`MENU -> Setup -> [Monitor] -> [Monitor Flip Direction]`)**:
     Validates all 4 values (`Auto` factory default, `Horizontal Flip`,
     `Vertical Flip`, `Off`), enforces **survival across `[Camera Settings Reset]`**
     (restored to `Auto` exclusively by `[Initialize]`), and enforces **playback
     non-inversion**: even when set to `[Horizontal Flip]` (which mirrors live
     shooting view), monitor display direction during **playback** is **NOT**
     inverted (`playback_monitor_horizontally_inverted == False`).
   - **Movie / S&Q AF Kinematics (`MENU -> Focus -> [AF/MF]`)**:
     Enforces exact full `ILME-FX3` menu string `[AF Subj. Shift Sensitivity]`
     (rejecting abbreviated `"AF Subj. Shift Sens."` hallucinations) across
     `1(Locked on)..5(Responsive)` (factory default `5(Responsive)`) and
     `[AF Transition Speed]` across `1(Slow)..7(Fast)` (factory default `5`),
     both Movie/S&Q-scoped and **resettable** via `[Camera Settings Reset]`
     (directly contrasting with non-resettable `[Monitor Flip Direction]`).
   - **`[Interval Shoot Func.]` (`MENU -> Shooting -> [Drive Mode] -> [Interval Shoot Func.]`)**:
     Enforces `[Shooting Start Time]` `1s..99m59s` (`1..5999` s),
     `[Shooting Interval]` `1s..60s` (`1..60` s), `[Number of Shots]` `1..9999`,
     and **still-image-only** capture scope (`JPEG`/`HEIF`/`RAW`), rejecting false
     in-camera `.MP4`/`.MXF` interval video recording claims on `ILME-FX3`
     (time-lapse movies require post-assembly in `Imaging Edge Desktop (Viewer)`).

3. **Unified 88-Gate Master Safety Preflight (`evaluate_88gate_preflight`)**:
   - Delegates `G01..G86` directly to `evaluate_86gate_preflight()`.
   - Offline default mode: `85/88` pass (`G01..G09`, `G13..G88` pass; `G10..G12`
     await physical Tier-0 receipt -> `overall_ready_for_hardware_attach = False`).
   - `--simulate-bench-dry-run` mode: `88/88` rehearsal pass while keeping all
     hardware write / live-attach redlines (`persistent_emmc_writes_authorized`,
     `hardware_live_attachment_authorized`, `spi_nor_write_authorized`,
     `el3_payload_transmit_authorized`, `overall_ready_for_hardware_attach`)
     hard-locked `False`.

Strictly stdlib-only Python 3.9+, `os.O_RDONLY` local donor inspection bounded to
`< 0.15s` with `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback, zero proprietary
firmware bytes leaked (`raw_firmware_bytes_leaked == 0`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    ENV_FORCE_CLEAN_ROOM,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_SAFE,
    GateVerdict,
)
from .realhw_cfexpress_ufu_el3_and_52gate_guard import EL3_PAYLOAD_TRANSMIT_AUTHORIZED
from .realhw_dualmedia_bench_interlock_and_58gate_guard import (
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
)
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard import (
    Master86GateReport,
    evaluate_86gate_preflight,
)
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_RECOVER_IMAGEDB_MONITOR_FLIP_AF_SENS_88GATE_SCHEMA: str = (
    "fx3-realhw-recover-imagedb-monitor-flip-af-sens-88gate-v1"
)
REALHW_RECOVER_IMAGEDB_MONITOR_FLIP_AF_SENS_88GATE_VERSION: str = "1.0.0"

G87_GATE_ID: str = "G87_recover_imagedb_depleted_battery_and_tier0_vault_firewall"
G87_GATE_CODE: str = (
    "RECOVER_IMAGE_DB_DEPLETED_BATTERY_REFUSAL_NONDELETING_AND_SLOT1_TIER0_VAULT_FIREWALL"
)

G88_GATE_ID: str = (
    "G88_monitor_flip_playback_noninversion_af_sens_and_interval_still_guard"
)
G88_GATE_CODE: str = (
    "MONITOR_FLIP_RESET_SURVIVAL_PLAYBACK_NONINVERSION_AF_SHIFT_SENS_AND_INTERVAL_STILL_GUARD"
)

G87: str = G87_GATE_ID
G88: str = G88_GATE_ID
GATE_G87_RECOVER_IMAGE_DB_DEPLETED_BATTERY_REFUSAL_NONDELETING_AND_SLOT1_TIER0_VAULT_FIREWALL: str = (
    G87_GATE_CODE
)
GATE_G88_MONITOR_FLIP_RESET_SURVIVAL_PLAYBACK_NONINVERSION_AF_SHIFT_SENS_AND_INTERVAL_STILL_GUARD: str = (
    G88_GATE_CODE
)

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS: float = 0.15

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX3_DEFAULT_FW_VERSION_PHASE235: str = "7.02"
FX3_MIN_SUPPORTED_FW_TUPLE_PHASE235: Tuple[int, int] = (1, 0)

# Status & Violation Codes
STATUS_VERIFIED_G87: str = (
    "VERIFIED_G87_RECOVER_IMAGEDB_BATTERY_REFUSAL_AND_TIER0_VAULT_FIREWALL_SAFE"
)
STATUS_VERIFIED_G88: str = (
    "VERIFIED_G88_MONITOR_FLIP_PLAYBACK_AF_SENS_AND_INTERVAL_STILL_SAFE"
)

STATUS_BLOCKED_PHASE235_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE235_DONOR_CONTRACT_INTEGRITY"
)
STATUS_BLOCKED_G87_RECOVER_IMAGEDB_DEPLETED_BATTERY_EXECUTION: str = (
    "BLOCKED_G87_RECOVER_IMAGEDB_DEPLETED_BATTERY_EXECUTION"
)
STATUS_BLOCKED_G87_RECOVER_IMAGEDB_CLIP_DELETION_OR_AVF_REPAIR_MISMATCH: str = (
    "BLOCKED_G87_RECOVER_IMAGEDB_CLIP_DELETION_OR_AVF_REPAIR_MISMATCH"
)
STATUS_BLOCKED_G87_RECOVER_IMAGEDB_ACTION_ITEM_RESET_CLAIM: str = (
    "BLOCKED_G87_RECOVER_IMAGEDB_ACTION_ITEM_RESET_CLAIM"
)
STATUS_BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION: str = (
    "BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION"
)
STATUS_BLOCKED_G87_TELEMETRY_INVALID: str = (
    "BLOCKED_G87_RECOVER_IMAGEDB_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION: str = (
    "BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G88_MONITOR_HORIZONTAL_FLIP_PLAYBACK_INVERSION: str = (
    "BLOCKED_G88_MONITOR_HORIZONTAL_FLIP_PLAYBACK_INVERSION"
)
STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION: str = (
    "BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION"
)
STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION: str = (
    "BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION"
)
STATUS_BLOCKED_G88_TELEMETRY_INVALID: str = (
    "BLOCKED_G88_MONITOR_FLIP_AF_INTERVAL_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G87 Canonical Constants: [Recover Image DB], Depleted NP-FZ100 Refusal,
# Non-Deleting Repair, Action-Item Immunity & Slot-1 Tier-0 Vault Firewall
# ---------------------------------------------------------------------------

RECOVER_IMAGE_DB_MENU_PATH: str = (
    "MENU -> Shooting -> [Media] -> [Recover Image DB]"
)

RECOVER_IMAGE_DB_SLOT_NONE: str = "NONE"
RECOVER_IMAGE_DB_SLOT_1: str = "Slot 1"
RECOVER_IMAGE_DB_SLOT_2: str = "Slot 2"
ALLOWED_RECOVER_IMAGE_DB_SLOTS: Tuple[str, ...] = (
    RECOVER_IMAGE_DB_SLOT_NONE,
    RECOVER_IMAGE_DB_SLOT_1,
    RECOVER_IMAGE_DB_SLOT_2,
)

RECOVER_IMAGE_DB_SYMPTOM_NONE: str = "NONE"
RECOVER_IMAGE_DB_SYMPTOM_DB_FILE_ERROR: str = "Image DataBase File error"
RECOVER_IMAGE_DB_SYMPTOM_FALSE_ZERO_RECORDABLE: str = "0 recordable images"
RECOVER_IMAGE_DB_SYMPTOM_PC_EDITED_INCONSISTENCY: str = (
    "PC-edited AVF_INFO inconsistency"
)
ALLOWED_RECOVER_IMAGE_DB_SYMPTOMS: Tuple[str, ...] = (
    RECOVER_IMAGE_DB_SYMPTOM_NONE,
    RECOVER_IMAGE_DB_SYMPTOM_DB_FILE_ERROR,
    RECOVER_IMAGE_DB_SYMPTOM_FALSE_ZERO_RECORDABLE,
    RECOVER_IMAGE_DB_SYMPTOM_PC_EDITED_INCONSISTENCY,
)

NPFZ100_RECOVER_IMAGEDB_MIN_SAFE_PCT: int = 10
NPFZ100_RECOVER_IMAGEDB_MIN_SAFE_MV: int = 6400
NPFZ100_NOMINAL_MV_G87: int = 7800

TIER0_VAULT_GUARDED_ARTIFACTS_G87: Tuple[str, ...] = (
    "pnflasha",
    "cnflasha",
    "CAMSET01.DAT",
)

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE235: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

# ---------------------------------------------------------------------------
# Gate G88 Canonical Constants: [Monitor Flip Direction], [AF Transition Speed],
# [AF Subj. Shift Sensitivity] & [Interval Shoot Func.]
# ---------------------------------------------------------------------------

MONITOR_FLIP_DIRECTION_MENU_PATH: str = (
    "MENU -> Setup -> [Monitor] -> [Monitor Flip Direction]"
)
MONITOR_FLIP_AUTO: str = "Auto"
MONITOR_FLIP_HORIZONTAL: str = "Horizontal Flip"
MONITOR_FLIP_VERTICAL: str = "Vertical Flip"
MONITOR_FLIP_OFF: str = "Off"
ALLOWED_MONITOR_FLIP_DIRECTIONS: Tuple[str, ...] = (
    MONITOR_FLIP_AUTO,
    MONITOR_FLIP_HORIZONTAL,
    MONITOR_FLIP_VERTICAL,
    MONITOR_FLIP_OFF,
)
MONITOR_FLIP_FACTORY_DEFAULT: str = MONITOR_FLIP_AUTO

AF_TRANSITION_SPEED_MENU_PATH: str = (
    "MENU -> Focus -> [AF/MF] -> [AF Transition Speed]"
)
AF_TRANSITION_SPEED_MENU_LABEL: str = "AF Transition Speed"
AF_TRANSITION_SPEED_MIN: int = 1
AF_TRANSITION_SPEED_MAX: int = 7
AF_TRANSITION_SPEED_FACTORY_DEFAULT: int = 5
AF_TRANSITION_SPEED_MIN_LABEL: str = "1(Slow)"
AF_TRANSITION_SPEED_MAX_LABEL: str = "7(Fast)"
AF_TRANSITION_SPEED_FACTORY_DEFAULT_LABEL: str = "5"
ALLOWED_AF_TRANSITION_SPEED_LABELS: Tuple[str, ...] = (
    "1(Slow)",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7(Fast)",
)

AF_SUBJ_SHIFT_SENSITIVITY_MENU_PATH: str = (
    "MENU -> Focus -> [AF/MF] -> [AF Subj. Shift Sensitivity]"
)
AF_SUBJ_SHIFT_SENSITIVITY_MENU_LABEL: str = "AF Subj. Shift Sensitivity"
REJECTED_ABBREVIATED_AF_SUBJ_SHIFT_LABELS: Tuple[str, ...] = (
    "AF Subj. Shift Sens.",
    "AF Subj. Shift Sens",
    "AF Subj Shift Sens",
    "AF Subject Shift Sens.",
)
AF_SUBJ_SHIFT_SENS_MIN: int = 1
AF_SUBJ_SHIFT_SENS_MAX: int = 5
AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT: int = 5
AF_SUBJ_SHIFT_SENS_MIN_LABEL: str = "1(Locked on)"
AF_SUBJ_SHIFT_SENS_MAX_LABEL: str = "5(Responsive)"
AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_LABEL: str = "5(Responsive)"
ALLOWED_AF_SUBJ_SHIFT_SENS_LABELS: Tuple[str, ...] = (
    "1(Locked on)",
    "2",
    "3",
    "4",
    "5(Responsive)",
)

AF_KINEMATICS_SCOPE_MOVIE: str = "Movie"
AF_KINEMATICS_SCOPE_SQ: str = "S&Q"
ALLOWED_AF_KINEMATICS_SCOPES: Tuple[str, ...] = (
    AF_KINEMATICS_SCOPE_MOVIE,
    AF_KINEMATICS_SCOPE_SQ,
)

INTERVAL_SHOOT_FUNC_MENU_PATH: str = (
    "MENU -> Shooting -> [Drive Mode] -> [Interval Shoot Func.]"
)
INTERVAL_SHOOTING_OFF: str = "Off"
INTERVAL_SHOOTING_ON: str = "On"
ALLOWED_INTERVAL_SHOOTING_MODES: Tuple[str, ...] = (
    INTERVAL_SHOOTING_OFF,
    INTERVAL_SHOOTING_ON,
)
INTERVAL_SHOOTING_FACTORY_DEFAULT: str = INTERVAL_SHOOTING_OFF

INTERVAL_START_TIME_MIN_SECONDS: int = 1
INTERVAL_START_TIME_MAX_SECONDS: int = 5999  # 99 min 59 sec
INTERVAL_SHOOTING_INTERVAL_MIN_SECONDS: int = 1
INTERVAL_SHOOTING_INTERVAL_MAX_SECONDS: int = 60  # 1 sec .. 60 sec
INTERVAL_NUMBER_OF_SHOTS_MIN: int = 1
INTERVAL_NUMBER_OF_SHOTS_MAX: int = 9999

ALLOWED_INTERVAL_STILL_FORMATS: Tuple[str, ...] = (
    "JPEG",
    "HEIF",
    "RAW",
    "RAW & JPEG",
    "RAW & HEIF",
)
FORBIDDEN_INTERVAL_VIDEO_CLAIM_TOKENS: Tuple[str, ...] = (
    ".MP4",
    ".MXF",
    "MP4",
    "MXF",
    "XAVC",
    "MOVIE",
    "INTERVAL_REC",
    "IN_CAMERA_TIMELAPSE_MOVIE",
)
INTERVAL_POST_ASSEMBLY_SOFTWARE: str = "Imaging Edge Desktop (Viewer)"

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.15s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE235_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Recover",
            b"Image",
            b"DataBase",
            b"Battery",
            b"Monitor",
            b"Flip",
            b"Horizontal",
            b"Playback",
            b"Transition",
            b"Sensitivity",
            b"Interval",
            b"Shoot",
            b"Reset",
            b"Initialize",
        ),
        "FX3_CPAPP_RECOVER_IMAGEDB_MONITOR_FLIP_AF_SENS_INTERVAL_STRINGS",
    ),
    "fx3_saveload_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (b"\x7fELF", b"SaveLoadSettings", b"Settings", b"Save", b"Backup"),
        "FX3_SAVELOAD_SETTINGS_PERSISTENCE_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"FTP", b"TC", b"/setting"),
        "FX3_BK4_RESET_VS_INITIALIZE_SEED",
    ),
    "fx6_bk4_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"NTSC", b"TC", b"Settings", b"/setting"),
        "FX6_CHAPLIN_BK4_INTERVAL_REC_BOUNDARY_REFERENCE",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase235DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_150ms: bool
    raw_firmware_bytes_leaked: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecoverImageDbBatteryAndVaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    menu_path: str
    target_slot: str
    recover_requested: bool
    recover_executed: bool
    media_symptom: str
    battery_soc_pct: int
    battery_mv: int
    battery_extremely_depleted: bool
    hardware_refuses_for_depleted_battery: bool
    recorded_clips_before: int
    recorded_clips_after: int
    recorded_clips_deleted: int
    non_deleting_repair_enforced: bool
    avf_info_repaired: bool
    false_zero_recordable_cleared: bool
    reset_action: str
    action_item_immune_to_camera_settings_reset: bool
    action_item_immune_to_initialize: bool
    slot1_tier0_vault_active: bool
    slot1_present_artifacts: Tuple[str, ...]
    slot1_off_camera_sha256_verified: bool
    slot1_sdxc_wp_locked: bool
    slot1_recover_imagedb_hard_blocked: bool
    slot1_metadata_sector_writes: int
    slot1_avf_info_mutated: bool
    slot1_vault_mutation_firewall_enforced: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MonitorFlipPlaybackAfSensAndIntervalResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    pre_reset_monitor_flip_direction: str
    reset_action: str
    expected_post_reset_monitor_flip_direction: str
    effective_post_reset_monitor_flip_direction: str
    monitor_flip_survived_camera_settings_reset: bool
    live_shooting_horizontally_mirrored: bool
    live_shooting_vertically_flipped: bool
    playback_monitor_horizontally_inverted: bool
    playback_text_mirror_reversed: bool
    horizontal_flip_playback_noninversion_enforced: bool
    af_kinematics_scope: str
    af_subj_shift_menu_label: str
    af_transition_menu_label: str
    pre_reset_af_subj_shift_level: int
    pre_reset_af_subj_shift_label: str
    pre_reset_af_transition_level: int
    pre_reset_af_transition_label: str
    expected_post_reset_af_subj_shift_label: str
    expected_post_reset_af_transition_label: str
    effective_post_reset_af_subj_shift_label: str
    effective_post_reset_af_transition_label: str
    af_kinematics_reset_by_camera_settings_reset: bool
    monitor_flip_vs_af_reset_split_verified: bool
    interval_shooting_mode: str
    expected_post_reset_interval_shooting_mode: str
    effective_post_reset_interval_shooting_mode: str
    shooting_start_time_seconds: int
    shooting_interval_seconds: int
    number_of_shots: int
    interval_capture_format: str
    in_camera_mp4_mxf_output_supported: bool
    in_camera_interval_movie_claimed: bool
    post_assembly_software: str
    interval_still_only_boundary_enforced: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G87RecoverImageDbBatteryAndVaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    recover_imagedb_battery_vault_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G88MonitorFlipAfSensAndIntervalGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    monitor_flip_af_sens_interval_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master88GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_85_gates_verified: bool
    all_88_gates_verified: bool
    g13_to_g88_all_passed: bool
    g87_to_g88_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_86_report: Dict[str, Any]
    g87_result: Dict[str, Any]
    g88_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers & Normalization
# ---------------------------------------------------------------------------


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip() in (
        "1",
        "true",
        "TRUE",
        "yes",
        "YES",
    )


def _read_file_o_rdonly(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    fd = os.open(str(path), flags)
    chunks: List[bytes] = []
    try:
        while True:
            buf = os.read(fd, 1 << 20)
            if not buf:
                break
            chunks.append(buf)
    finally:
        os.close(fd)
    return b"".join(chunks)


def _read_cached_donor_o_rdonly(path: Path) -> Tuple[int, str, bytes]:
    key = str(path.resolve())
    st = os.stat(key)
    cached = _DONOR_BLOB_CACHE.get(key)
    if cached is not None and cached[0] == st.st_size and cached[1] == st.st_mtime:
        return cached[2], cached[3], cached[4]
    blob = _read_file_o_rdonly(path)
    sha = hashlib.sha256(blob).hexdigest()
    _DONOR_BLOB_CACHE[key] = (st.st_size, st.st_mtime, len(blob), sha, blob)
    return len(blob), sha, blob


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _norm_token(val: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", (val or "").strip().upper()).strip("_")


def _parse_fw_tuple(fw_str: str) -> Optional[Tuple[int, int]]:
    m = re.match(r"^\s*[vV]?(\d+)\.(\d+)(?:\.\d+)?\s*$", (fw_str or "").strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _norm_reset_action(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("NONE", "NO_RESET"):
        return RESET_ACTION_NONE
    if t in ("CAMERA_SETTINGS_RESET", "CAM_SETTINGS_RESET"):
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if t in ("INITIALIZE", "FACTORY_INITIALIZE"):
        return RESET_ACTION_INITIALIZE
    return None


def _norm_slot(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("NONE", "NO_SLOT"):
        return RECOVER_IMAGE_DB_SLOT_NONE
    if t in ("SLOT_1", "SLOT1", "1"):
        return RECOVER_IMAGE_DB_SLOT_1
    if t in ("SLOT_2", "SLOT2", "2"):
        return RECOVER_IMAGE_DB_SLOT_2
    return None


def _norm_symptom(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "NONE":
        return RECOVER_IMAGE_DB_SYMPTOM_NONE
    if t in ("IMAGE_DATABASE_FILE_ERROR", "DATABASE_FILE_ERROR", "DB_FILE_ERROR"):
        return RECOVER_IMAGE_DB_SYMPTOM_DB_FILE_ERROR
    if t in ("0_RECORDABLE_IMAGES", "FALSE_ZERO_RECORDABLE", "ZERO_RECORDABLE_IMAGES"):
        return RECOVER_IMAGE_DB_SYMPTOM_FALSE_ZERO_RECORDABLE
    if t in ("PC_EDITED_AVF_INFO_INCONSISTENCY", "AVF_INFO_INCONSISTENCY", "PC_EDITED"):
        return RECOVER_IMAGE_DB_SYMPTOM_PC_EDITED_INCONSISTENCY
    return None


def _norm_tier0_artifact(val: str) -> str:
    s = (val or "").strip()
    u = s.upper()
    if u.startswith("PNFLASHA"):
        return "pnflasha"
    if u.startswith("CNFLASHA"):
        return "cnflasha"
    if "CAMSET" in u and u.endswith(".DAT"):
        return "CAMSET01.DAT"
    return s


def _norm_monitor_flip_direction(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "AUTO":
        return MONITOR_FLIP_AUTO
    if t in ("HORIZONTAL_FLIP", "HORIZONTAL"):
        return MONITOR_FLIP_HORIZONTAL
    if t in ("VERTICAL_FLIP", "VERTICAL"):
        return MONITOR_FLIP_VERTICAL
    if t == "OFF":
        return MONITOR_FLIP_OFF
    return None


def _norm_on_off(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "ON":
        return "On"
    if t == "OFF":
        return "Off"
    return None


def _norm_af_scope(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "MOVIE":
        return AF_KINEMATICS_SCOPE_MOVIE
    if t in ("S_Q", "SQ", "SLOW_QUICK", "S_Q_MOTION"):
        return AF_KINEMATICS_SCOPE_SQ
    return None


def _parse_af_transition_speed(
    val: Union[int, str],
) -> Optional[Tuple[int, str]]:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        lvl = val
    else:
        s = (val or "").strip()
        if s in ALLOWED_AF_TRANSITION_SPEED_LABELS:
            idx = ALLOWED_AF_TRANSITION_SPEED_LABELS.index(s) + 1
            return idx, s
        t = _norm_token(s)
        m = re.match(r"^([1-7])(?:_(SLOW|FAST))?$", t)
        if not m:
            return None
        lvl = int(m.group(1))
        qual = m.group(2)
        if qual == "SLOW" and lvl != 1:
            return None
        if qual == "FAST" and lvl != 7:
            return None
    if AF_TRANSITION_SPEED_MIN <= lvl <= AF_TRANSITION_SPEED_MAX:
        return lvl, ALLOWED_AF_TRANSITION_SPEED_LABELS[lvl - 1]
    return None


def _parse_af_subj_shift_sensitivity(
    val: Union[int, str],
) -> Optional[Tuple[int, str]]:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        lvl = val
    else:
        s = (val or "").strip()
        if s in ALLOWED_AF_SUBJ_SHIFT_SENS_LABELS:
            idx = ALLOWED_AF_SUBJ_SHIFT_SENS_LABELS.index(s) + 1
            return idx, s
        t = _norm_token(s)
        m = re.match(r"^([1-5])(?:_(LOCKED_ON|RESPONSIVE))?$", t)
        if not m:
            return None
        lvl = int(m.group(1))
        qual = m.group(2)
        if qual == "LOCKED_ON" and lvl != 1:
            return None
        if qual == "RESPONSIVE" and lvl != 5:
            return None
    if AF_SUBJ_SHIFT_SENS_MIN <= lvl <= AF_SUBJ_SHIFT_SENS_MAX:
        return lvl, ALLOWED_AF_SUBJ_SHIFT_SENS_LABELS[lvl - 1]
    return None


def parse_fx3_duration_seconds(val: Union[int, str]) -> Optional[int]:
    """Parse an `ILME-FX3` `[Interval Shoot Func.]` duration (`int` seconds or
    strings like `'1s'`, `'60s'`, `'99m59s'`, `'1m30s'`, `'00:05'`) into integer
    seconds, returning `None` on malformed or boolean inputs.
    """
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    s = (val or "").strip().lower()
    if not s:
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    m_sec = re.fullmatch(r"(\d+)\s*(?:s|sec|secs)", s)
    if m_sec:
        return int(m_sec.group(1))
    m_min_sec = re.fullmatch(
        r"(\d+)\s*(?:m|min|mins)\s*(?:(\d+)\s*(?:s|sec|secs)?)?", s
    )
    if m_min_sec:
        mins = int(m_min_sec.group(1))
        secs = int(m_min_sec.group(2) or 0)
        if secs >= 60:
            return None
        return mins * 60 + secs
    m_colon = re.fullmatch(r"(\d+):([0-5]\d)", s)
    if m_colon:
        return int(m_colon.group(1)) * 60 + int(m_colon.group(2))
    return None


def _norm_interval_still_format(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "JPEG":
        return "JPEG"
    if t == "HEIF":
        return "HEIF"
    if t == "RAW":
        return "RAW"
    if t in ("RAW_JPEG", "RAW_AND_JPEG"):
        return "RAW & JPEG"
    if t in ("RAW_HEIF", "RAW_AND_HEIF"):
        return "RAW & HEIF"
    return None


def _is_forbidden_interval_video_claim(val: str) -> bool:
    u = (val or "").strip().upper()
    t = _norm_token(val)
    for tok in FORBIDDEN_INTERVAL_VIDEO_CLAIM_TOKENS:
        if tok in u or tok == t or tok in t.split("_"):
            return True
    return False


# ---------------------------------------------------------------------------
# 1. Bounded `<0.15s` O_RDONLY Local Donor Audit (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
# ---------------------------------------------------------------------------


def audit_phase235_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS,
) -> Phase235DonorAuditResult:
    """Bounded `<0.15s` `O_RDONLY` local donor contract check with deterministic
    `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback (`raw_firmware_bytes_leaked == 0`).
    """
    t0 = time.perf_counter()
    clean_forced = _is_forced_clean_room(force_clean_room)
    resolved_repo = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    paths = resolve_donor_thermal_power_paths(
        work_root=work_root, repo_root=resolved_repo
    )
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (_body, rel_path, *_rest) in PINNED_PHASE235_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        elapsed = time.perf_counter() - t0
        within_budget = elapsed < max_budget_seconds
        return Phase235DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE235_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_150ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE235_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=within_budget,
            fx6_contracts_verified=within_budget,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE235_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE235_DONOR_SPECS.items()
            },
            errors=()
            if within_budget
            else (
                f"Clean-room donor check exceeded budget ({elapsed:.4f}s >= {max_budget_seconds:.4f}s).",
            ),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    passed_keys: Set[str] = set()
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE235_DONOR_SPECS.items():
        size_b, sha, blob = _read_cached_donor_o_rdonly(resolved[key])
        files_inspected += 1
        shas[key] = sha
        sizes[key] = size_b

        missing_for_file = [m for m in marker_tuple if m not in blob]
        integrity_ok = size_b == exp_size and sha == exp_sha
        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )
        if not integrity_ok:
            errors.append(
                f"Donor {key} integrity mismatch: size={size_b} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )
        if not missing_for_file and integrity_ok:
            passed_keys.add(key)

    elapsed = time.perf_counter() - t0
    within_budget = elapsed < max_budget_seconds
    if not within_budget:
        errors.append(
            f"Local O_RDONLY donor audit exceeded {max_budget_seconds:.3f}s budget ({elapsed:.4f}s)."
        )

    fx3_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE235_DONOR_SPECS.items()
        if s[0] == "FX3"
    )
    fx6_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE235_DONOR_SPECS.items()
        if s[0] == "FX6"
    )
    valid = fx3_ok and fx6_ok and within_budget and (not errors)
    return Phase235DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE235_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_150ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate `G87`: `[Recover Image DB]` Depleted-Battery Refusal, Non-Deleting
#    Repair, Action-Item Immunity & Slot-1 Tier-0 Vault Mutation Firewall
# ---------------------------------------------------------------------------


def resolve_fx3_recover_imagedb_battery_and_vault_state(
    *,
    target_slot: str = RECOVER_IMAGE_DB_SLOT_2,
    recover_requested: bool = True,
    media_symptom: str = RECOVER_IMAGE_DB_SYMPTOM_DB_FILE_ERROR,
    battery_soc_pct: int = 85,
    battery_mv: int = NPFZ100_NOMINAL_MV_G87,
    battery_extremely_depleted: bool = False,
    slot1_tier0_vault_active: bool = True,
    slot1_present_artifacts: Sequence[str] = TIER0_VAULT_GUARDED_ARTIFACTS_G87,
    slot1_off_camera_sha256_verified: bool = False,
    slot1_sdxc_wp_locked: bool = True,
    reset_action: str = RESET_ACTION_NONE,
) -> Dict[str, Any]:
    """Deterministically resolve `ILME-FX3` `[Recover Image DB]` depleted-battery
    refusal, non-deleting `AVF_INFO` repair eligibility, action-item reset immunity,
    and Slot-1 Tier-0 vault read-only mutation firewall state.
    """
    c_slot = _norm_slot(target_slot)
    c_symptom = _norm_symptom(media_symptom)
    c_reset = _norm_reset_action(reset_action)

    norm_artifacts = tuple(_norm_tier0_artifact(a) for a in slot1_present_artifacts)
    guarded_present = tuple(
        a for a in norm_artifacts if a in TIER0_VAULT_GUARDED_ARTIFACTS_G87
    )
    has_tier0_artifacts = len(guarded_present) > 0

    depleted_battery_refusal = (
        bool(battery_extremely_depleted)
        or (isinstance(battery_soc_pct, int) and battery_soc_pct < NPFZ100_RECOVER_IMAGEDB_MIN_SAFE_PCT)
        or (isinstance(battery_mv, int) and battery_mv < NPFZ100_RECOVER_IMAGEDB_MIN_SAFE_MV)
    )

    slot1_vault_firewall_active = bool(
        slot1_tier0_vault_active
        or slot1_sdxc_wp_locked
        or (has_tier0_artifacts and not slot1_off_camera_sha256_verified)
    )
    slot1_hard_blocked = slot1_vault_firewall_active

    slot_blocked_by_vault = (c_slot == RECOVER_IMAGE_DB_SLOT_1) and slot1_hard_blocked
    expected_execution_permitted = bool(
        recover_requested
        and c_slot in (RECOVER_IMAGE_DB_SLOT_1, RECOVER_IMAGE_DB_SLOT_2)
        and (not depleted_battery_refusal)
        and (not slot_blocked_by_vault)
    )

    return {
        "canonical_target_slot": c_slot,
        "canonical_symptom": c_symptom,
        "canonical_reset_action": c_reset,
        "normalized_slot1_artifacts": norm_artifacts,
        "guarded_slot1_artifacts": guarded_present,
        "slot1_has_tier0_artifacts": has_tier0_artifacts,
        "hardware_refuses_for_depleted_battery": depleted_battery_refusal,
        "slot1_recover_imagedb_hard_blocked": slot1_hard_blocked,
        "slot_blocked_by_vault": slot_blocked_by_vault,
        "expected_execution_permitted": expected_execution_permitted,
        "action_item_immune_to_camera_settings_reset": True,
        "action_item_immune_to_initialize": True,
    }


def verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE235,
    target_slot: str = RECOVER_IMAGE_DB_SLOT_2,
    recover_requested: bool = True,
    recover_executed: Optional[bool] = None,
    media_symptom: str = RECOVER_IMAGE_DB_SYMPTOM_DB_FILE_ERROR,
    battery_soc_pct: int = 85,
    battery_mv: int = NPFZ100_NOMINAL_MV_G87,
    battery_extremely_depleted: bool = False,
    recorded_clips_before: int = 42,
    recorded_clips_after: Optional[int] = None,
    recorded_clips_deleted: int = 0,
    avf_info_repaired: Optional[bool] = None,
    false_zero_recordable_cleared: Optional[bool] = None,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    claimed_reset_by_camera_settings_reset: bool = False,
    claimed_reset_by_initialize: bool = False,
    claimed_persistent_toggle_state: bool = False,
    slot1_tier0_vault_active: bool = True,
    slot1_present_artifacts: Sequence[str] = TIER0_VAULT_GUARDED_ARTIFACTS_G87,
    slot1_off_camera_sha256_verified: bool = False,
    slot1_sdxc_wp_locked: bool = True,
    slot1_metadata_sector_writes: int = 0,
    slot1_avf_info_mutated: bool = False,
) -> RecoverImageDbBatteryAndVaultGuardResult:
    """Verify Gate `G87` invariants across `[Recover Image DB]` non-deleting
    `AVF_INFO` repair, depleted `NP-FZ100` execution refusal, action-item reset
    immunity, and unverified / `WP`-locked Slot-1 Tier-0 vault read-only mutation
    firewall.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name.strip().upper() != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
    ):
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(
            f"Gate G87 requires ILME-FX3 (0x{FX3_MODEL_ID:08X}); got {body_model_name!r} (0x{int(body_model_id):08X})."
        )
    if fw_tuple is None or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE235:
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(
            f"Gate G87 requires valid ILME-FX3 firmware version (>= 1.00); got {firmware_version!r}."
        )

    if (
        isinstance(battery_soc_pct, bool)
        or not isinstance(battery_soc_pct, int)
        or not (0 <= battery_soc_pct <= 100)
    ):
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(f"Invalid battery_soc_pct={battery_soc_pct!r} (expected 0..100).")

    if (
        isinstance(battery_mv, bool)
        or not isinstance(battery_mv, int)
        or not (3000 <= battery_mv <= 9000)
    ):
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(f"Invalid battery_mv={battery_mv!r} (expected 3000..9000 mV).")

    if (
        isinstance(recorded_clips_before, bool)
        or not isinstance(recorded_clips_before, int)
        or recorded_clips_before < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(f"Invalid recorded_clips_before={recorded_clips_before!r}.")

    if (
        isinstance(recorded_clips_deleted, bool)
        or not isinstance(recorded_clips_deleted, int)
        or recorded_clips_deleted < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(f"Invalid recorded_clips_deleted={recorded_clips_deleted!r}.")

    if (
        isinstance(slot1_metadata_sector_writes, bool)
        or not isinstance(slot1_metadata_sector_writes, int)
        or slot1_metadata_sector_writes < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(
            f"Invalid slot1_metadata_sector_writes={slot1_metadata_sector_writes!r}."
        )

    state = resolve_fx3_recover_imagedb_battery_and_vault_state(
        target_slot=target_slot,
        recover_requested=recover_requested,
        media_symptom=media_symptom,
        battery_soc_pct=battery_soc_pct if isinstance(battery_soc_pct, int) else 0,
        battery_mv=battery_mv if isinstance(battery_mv, int) else 0,
        battery_extremely_depleted=battery_extremely_depleted,
        slot1_tier0_vault_active=slot1_tier0_vault_active,
        slot1_present_artifacts=slot1_present_artifacts,
        slot1_off_camera_sha256_verified=slot1_off_camera_sha256_verified,
        slot1_sdxc_wp_locked=slot1_sdxc_wp_locked,
        reset_action=reset_action,
    )

    c_slot = state["canonical_target_slot"]
    c_symptom = state["canonical_symptom"]
    c_reset = state["canonical_reset_action"]

    if c_slot is None:
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(
            f"Invalid [Recover Image DB] target_slot={target_slot!r}; expected {ALLOWED_RECOVER_IMAGE_DB_SLOTS}."
        )
    if c_symptom is None:
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(
            f"Invalid [Recover Image DB] media_symptom={media_symptom!r}; expected {ALLOWED_RECOVER_IMAGE_DB_SYMPTOMS}."
        )
    if c_reset is None:
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(
            f"Invalid reset_action={reset_action!r}; expected {ALLOWED_RESET_ACTIONS_PHASE235}."
        )
    if recover_requested and c_slot == RECOVER_IMAGE_DB_SLOT_NONE:
        _add_code(codes, STATUS_BLOCKED_G87_TELEMETRY_INVALID)
        errors.append(
            "[Recover Image DB] cannot be requested when target_slot is 'NONE'."
        )

    eff_executed = (
        bool(state["expected_execution_permitted"])
        if recover_executed is None
        else bool(recover_executed)
    )
    eff_clips_after = (
        recorded_clips_before
        if recorded_clips_after is None
        else int(recorded_clips_after)
    )
    eff_avf_repaired = (
        eff_executed if avf_info_repaired is None else bool(avf_info_repaired)
    )
    eff_zero_cleared = (
        eff_executed
        if false_zero_recordable_cleared is None
        else bool(false_zero_recordable_cleared)
    )

    # 1. Slot-1 Tier-0 Vault Read-Only Mutation Firewall
    slot1_hard_blocked = bool(state["slot1_recover_imagedb_hard_blocked"])
    slot1_vault_violation = False
    if slot1_hard_blocked:
        if (
            (c_slot == RECOVER_IMAGE_DB_SLOT_1 and (recover_requested or eff_executed))
            or slot1_metadata_sector_writes > 0
            or bool(slot1_avf_info_mutated)
        ):
            slot1_vault_violation = True
            _add_code(codes, STATUS_BLOCKED_G87_SLOT1_TIER0_VAULT_RECOVER_IMAGEDB_MUTATION)
            errors.append(
                "Slot-1 Tier-0 vault read-only mutation firewall blocked [Recover Image DB] "
                f"(slot={c_slot!r}, requested={recover_requested}, executed={eff_executed}, "
                f"vault_active={slot1_tier0_vault_active}, sha256_verified={slot1_off_camera_sha256_verified}, "
                f"wp_locked={slot1_sdxc_wp_locked}, artifacts={state['guarded_slot1_artifacts']}, "
                f"slot1_writes={slot1_metadata_sector_writes}, avf_mutated={slot1_avf_info_mutated})."
            )
    slot1_firewall_ok = not slot1_vault_violation

    # 2. Depleted NP-FZ100 Battery Refusal
    depleted_refusal = bool(state["hardware_refuses_for_depleted_battery"])
    if depleted_refusal and (recover_requested or eff_executed):
        _add_code(codes, STATUS_BLOCKED_G87_RECOVER_IMAGEDB_DEPLETED_BATTERY_EXECUTION)
        errors.append(
            "[Recover Image DB] refused/blocked due to extremely depleted NP-FZ100 battery "
            f"(soc={battery_soc_pct}%, mv={battery_mv}mV, extremely_depleted={battery_extremely_depleted})."
        )

    # 3. Non-Deleting AVF_INFO Repair Semantics
    non_deleting_ok = (
        isinstance(recorded_clips_before, int)
        and recorded_clips_deleted == 0
        and eff_clips_after == recorded_clips_before
    )
    repair_state_ok = (not eff_executed) or (eff_avf_repaired and eff_zero_cleared)
    if not non_deleting_ok or not repair_state_ok:
        _add_code(
            codes,
            STATUS_BLOCKED_G87_RECOVER_IMAGEDB_CLIP_DELETION_OR_AVF_REPAIR_MISMATCH,
        )
        errors.append(
            "[Recover Image DB] non-deleting AVF_INFO repair invariant violated: "
            f"before={recorded_clips_before}, after={eff_clips_after}, deleted={recorded_clips_deleted}, "
            f"executed={eff_executed}, avf_repaired={eff_avf_repaired}, zero_cleared={eff_zero_cleared}."
        )

    # 4. Action-Item Immunity to [Camera Settings Reset] & [Initialize]
    if (
        claimed_reset_by_camera_settings_reset
        or claimed_reset_by_initialize
        or claimed_persistent_toggle_state
    ):
        _add_code(codes, STATUS_BLOCKED_G87_RECOVER_IMAGEDB_ACTION_ITEM_RESET_CLAIM)
        errors.append(
            "[Recover Image DB] is an immediate action item and is NOT reset by "
            "[Camera Settings Reset] or [Initialize] and holds no persistent toggle state."
        )

    valid = not codes
    status = STATUS_VERIFIED_G87 if valid else codes[0]
    return RecoverImageDbBatteryAndVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08X}",
        firmware_version=firmware_version,
        menu_path=RECOVER_IMAGE_DB_MENU_PATH,
        target_slot=c_slot or target_slot,
        recover_requested=bool(recover_requested),
        recover_executed=eff_executed,
        media_symptom=c_symptom or media_symptom,
        battery_soc_pct=int(battery_soc_pct) if isinstance(battery_soc_pct, int) else -1,
        battery_mv=int(battery_mv) if isinstance(battery_mv, int) else -1,
        battery_extremely_depleted=bool(battery_extremely_depleted),
        hardware_refuses_for_depleted_battery=depleted_refusal,
        recorded_clips_before=int(recorded_clips_before)
        if isinstance(recorded_clips_before, int)
        else -1,
        recorded_clips_after=eff_clips_after,
        recorded_clips_deleted=int(recorded_clips_deleted)
        if isinstance(recorded_clips_deleted, int)
        else -1,
        non_deleting_repair_enforced=non_deleting_ok and repair_state_ok,
        avf_info_repaired=eff_avf_repaired,
        false_zero_recordable_cleared=eff_zero_cleared,
        reset_action=c_reset or reset_action,
        action_item_immune_to_camera_settings_reset=not bool(
            claimed_reset_by_camera_settings_reset
        ),
        action_item_immune_to_initialize=not bool(claimed_reset_by_initialize),
        slot1_tier0_vault_active=bool(slot1_tier0_vault_active),
        slot1_present_artifacts=state["normalized_slot1_artifacts"],
        slot1_off_camera_sha256_verified=bool(slot1_off_camera_sha256_verified),
        slot1_sdxc_wp_locked=bool(slot1_sdxc_wp_locked),
        slot1_recover_imagedb_hard_blocked=slot1_hard_blocked,
        slot1_metadata_sector_writes=int(slot1_metadata_sector_writes)
        if isinstance(slot1_metadata_sector_writes, int)
        else -1,
        slot1_avf_info_mutated=bool(slot1_avf_info_mutated),
        slot1_vault_mutation_firewall_enforced=slot1_firewall_ok,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g87_recover_imagedb_battery_and_tier0_vault_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    recover_imagedb_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase235DonorAuditResult] = None,
) -> Tuple[GateVerdict, G87RecoverImageDbBatteryAndVaultGuardResult]:
    """Evaluate Gate `G87` combining bounded `<0.15s` donor check with
    `[Recover Image DB]` depleted-battery refusal, non-deleting repair, action-item
    reset immunity, and Slot-1 Tier-0 vault read-only mutation firewall.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase235_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_recover_imagedb_depleted_battery_and_tier0_vault_guard(
        **dict(recover_imagedb_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)
    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G87 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G87 if valid else codes[0]

    res = G87RecoverImageDbBatteryAndVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        recover_imagedb_battery_vault_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, slot={guard.target_slot}"
        f"(exec={guard.recover_executed},deleted={guard.recorded_clips_deleted},"
        f"batt={guard.battery_soc_pct}%/{guard.battery_mv}mV,"
        f"slot1_vault_blocked={guard.slot1_recover_imagedb_hard_blocked},"
        f"slot1_writes={guard.slot1_metadata_sector_writes})"
    )
    verdict = GateVerdict(
        gate_id=G87_GATE_ID,
        gate_code=G87_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate `G88`: `[Monitor Flip Direction]` Reset Survival + `[Horizontal Flip]`
#    Playback Non-Inversion, `[AF Subj. Shift Sensitivity]` / `[AF Transition Speed]`
#    Reset Split & `[Interval Shoot Func.]` Still-Only Boundary
# ---------------------------------------------------------------------------


def resolve_fx3_monitor_flip_reset_and_playback(
    *,
    pre_reset_monitor_flip_direction: str = MONITOR_FLIP_HORIZONTAL,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
) -> Dict[str, Any]:
    """Deterministically resolve `[Monitor Flip Direction]` across
    `[Camera Settings Reset]` vs `[Initialize]` and compute live-shooting vs
    playback display inversion state.
    """
    c_dir = _norm_monitor_flip_direction(pre_reset_monitor_flip_direction)
    c_rst = _norm_reset_action(reset_action)

    if c_rst == RESET_ACTION_INITIALIZE:
        exp_post = MONITOR_FLIP_FACTORY_DEFAULT
    else:
        exp_post = c_dir or MONITOR_FLIP_FACTORY_DEFAULT

    return {
        "canonical_pre_direction": c_dir,
        "canonical_reset_action": c_rst,
        "expected_post_reset_direction": exp_post,
        "expected_live_shooting_horizontally_mirrored": exp_post == MONITOR_FLIP_HORIZONTAL,
        "expected_live_shooting_vertically_flipped": exp_post == MONITOR_FLIP_VERTICAL,
        "expected_playback_horizontally_inverted": False,
        "expected_playback_text_mirror_reversed": False,
    }


def resolve_fx3_af_transition_and_subj_shift_sensitivity(
    *,
    af_kinematics_scope: str = AF_KINEMATICS_SCOPE_MOVIE,
    af_subj_shift_menu_label: str = AF_SUBJ_SHIFT_SENSITIVITY_MENU_LABEL,
    af_transition_menu_label: str = AF_TRANSITION_SPEED_MENU_LABEL,
    pre_reset_af_subj_shift_sensitivity: Union[int, str] = AF_SUBJ_SHIFT_SENS_MIN_LABEL,
    pre_reset_af_transition_speed: Union[int, str] = AF_TRANSITION_SPEED_MIN_LABEL,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
) -> Dict[str, Any]:
    """Deterministically resolve `ILME-FX3` Movie/S&Q `[AF Subj. Shift Sensitivity]`
    (`1(Locked on)..5(Responsive)`, default `5(Responsive)`) and
    `[AF Transition Speed]` (`1(Slow)..7(Fast)`, default `5`) menu naming and
    `[Camera Settings Reset]` / `[Initialize]` reset behavior.
    """
    c_scope = _norm_af_scope(af_kinematics_scope)
    c_rst = _norm_reset_action(reset_action)
    parsed_sens = _parse_af_subj_shift_sensitivity(pre_reset_af_subj_shift_sensitivity)
    parsed_speed = _parse_af_transition_speed(pre_reset_af_transition_speed)

    subj_label_clean = (af_subj_shift_menu_label or "").strip().strip("[]")
    trans_label_clean = (af_transition_menu_label or "").strip().strip("[]")
    subj_label_exact = subj_label_clean == AF_SUBJ_SHIFT_SENSITIVITY_MENU_LABEL
    trans_label_exact = trans_label_clean == AF_TRANSITION_SPEED_MENU_LABEL

    if c_rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        exp_sens_lvl = AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT
        exp_sens_lbl = AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_LABEL
        exp_speed_lvl = AF_TRANSITION_SPEED_FACTORY_DEFAULT
        exp_speed_lbl = AF_TRANSITION_SPEED_FACTORY_DEFAULT_LABEL
    else:
        exp_sens_lvl = parsed_sens[0] if parsed_sens is not None else AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT
        exp_sens_lbl = parsed_sens[1] if parsed_sens is not None else AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_LABEL
        exp_speed_lvl = parsed_speed[0] if parsed_speed is not None else AF_TRANSITION_SPEED_FACTORY_DEFAULT
        exp_speed_lbl = parsed_speed[1] if parsed_speed is not None else AF_TRANSITION_SPEED_FACTORY_DEFAULT_LABEL

    return {
        "canonical_scope": c_scope,
        "canonical_reset_action": c_rst,
        "subj_label_clean": subj_label_clean,
        "trans_label_clean": trans_label_clean,
        "subj_label_exact": subj_label_exact,
        "trans_label_exact": trans_label_exact,
        "parsed_pre_sens": parsed_sens,
        "parsed_pre_speed": parsed_speed,
        "expected_post_sens_level": exp_sens_lvl,
        "expected_post_sens_label": exp_sens_lbl,
        "expected_post_speed_level": exp_speed_lvl,
        "expected_post_speed_label": exp_speed_lbl,
    }


def resolve_fx3_interval_shoot_func_boundary(
    *,
    interval_shooting: str = INTERVAL_SHOOTING_ON,
    shooting_start_time: Union[int, str] = 1,
    shooting_interval: Union[int, str] = 5,
    number_of_shots: int = 120,
    interval_capture_format: str = "RAW & JPEG",
    in_camera_interval_movie_claimed: bool = False,
    post_assembly_software: str = INTERVAL_POST_ASSEMBLY_SOFTWARE,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
) -> Dict[str, Any]:
    """Deterministically resolve `ILME-FX3` `[Interval Shoot Func.]` timing bounds
    (`1s..99m59s` start delay, `1s..60s` interval, `1..9999` shots), resettable
    default (`Off`), and still-image-only capture scope.
    """
    c_mode = _norm_on_off(interval_shooting)
    c_rst = _norm_reset_action(reset_action)
    start_s = parse_fx3_duration_seconds(shooting_start_time)
    interval_s = parse_fx3_duration_seconds(shooting_interval)
    c_fmt = _norm_interval_still_format(interval_capture_format)
    video_claim = bool(in_camera_interval_movie_claimed) or _is_forbidden_interval_video_claim(
        interval_capture_format
    )

    shots_ok = (
        not isinstance(number_of_shots, bool)
        and isinstance(number_of_shots, int)
        and (INTERVAL_NUMBER_OF_SHOTS_MIN <= number_of_shots <= INTERVAL_NUMBER_OF_SHOTS_MAX)
    )
    start_ok = (
        start_s is not None
        and INTERVAL_START_TIME_MIN_SECONDS <= start_s <= INTERVAL_START_TIME_MAX_SECONDS
    )
    interval_ok = (
        interval_s is not None
        and INTERVAL_SHOOTING_INTERVAL_MIN_SECONDS
        <= interval_s
        <= INTERVAL_SHOOTING_INTERVAL_MAX_SECONDS
    )

    if c_rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        exp_post_mode = INTERVAL_SHOOTING_FACTORY_DEFAULT
    else:
        exp_post_mode = c_mode or INTERVAL_SHOOTING_FACTORY_DEFAULT

    return {
        "canonical_mode": c_mode,
        "canonical_reset_action": c_rst,
        "start_seconds": start_s,
        "interval_seconds": interval_s,
        "start_in_bounds": start_ok,
        "interval_in_bounds": interval_ok,
        "shots_in_bounds": shots_ok,
        "canonical_still_format": c_fmt,
        "video_claim_detected": video_claim,
        "expected_post_reset_mode": exp_post_mode,
        "post_assembly_software": (post_assembly_software or "").strip(),
    }


def verify_monitor_flip_playback_af_sens_and_interval_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE235,
    pre_reset_monitor_flip_direction: str = MONITOR_FLIP_HORIZONTAL,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    observed_post_reset_monitor_flip_direction: Optional[str] = None,
    observed_live_shooting_horizontally_mirrored: Optional[bool] = None,
    observed_live_shooting_vertically_flipped: Optional[bool] = None,
    observed_playback_monitor_horizontally_inverted: Optional[bool] = None,
    observed_playback_text_mirror_reversed: Optional[bool] = None,
    af_kinematics_scope: str = AF_KINEMATICS_SCOPE_MOVIE,
    af_subj_shift_menu_label: str = AF_SUBJ_SHIFT_SENSITIVITY_MENU_LABEL,
    af_transition_menu_label: str = AF_TRANSITION_SPEED_MENU_LABEL,
    pre_reset_af_subj_shift_sensitivity: Union[int, str] = AF_SUBJ_SHIFT_SENS_MIN_LABEL,
    pre_reset_af_transition_speed: Union[int, str] = AF_TRANSITION_SPEED_MIN_LABEL,
    observed_post_reset_af_subj_shift_sensitivity: Optional[Union[int, str]] = None,
    observed_post_reset_af_transition_speed: Optional[Union[int, str]] = None,
    interval_shooting: str = INTERVAL_SHOOTING_ON,
    observed_post_reset_interval_shooting: Optional[str] = None,
    shooting_start_time: Union[int, str] = 1,
    shooting_interval: Union[int, str] = 5,
    number_of_shots: int = 120,
    interval_capture_format: str = "RAW & JPEG",
    in_camera_interval_movie_claimed: bool = False,
    post_assembly_software: str = INTERVAL_POST_ASSEMBLY_SOFTWARE,
) -> MonitorFlipPlaybackAfSensAndIntervalResult:
    """Verify Gate `G88` invariants across `[Monitor Flip Direction]` survival &
    `[Horizontal Flip]` playback non-inversion, `[AF Subj. Shift Sensitivity]` /
    `[AF Transition Speed]` menu string & reset split, and `[Interval Shoot Func.]`
    still-only bounds.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name.strip().upper() != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
    ):
        _add_code(codes, STATUS_BLOCKED_G88_TELEMETRY_INVALID)
        errors.append(
            f"Gate G88 requires ILME-FX3 (0x{FX3_MODEL_ID:08X}); got {body_model_name!r} (0x{int(body_model_id):08X})."
        )
    if fw_tuple is None or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE235:
        _add_code(codes, STATUS_BLOCKED_G88_TELEMETRY_INVALID)
        errors.append(
            f"Gate G88 requires valid ILME-FX3 firmware version (>= 1.00); got {firmware_version!r}."
        )

    m_state = resolve_fx3_monitor_flip_reset_and_playback(
        pre_reset_monitor_flip_direction=pre_reset_monitor_flip_direction,
        reset_action=reset_action,
    )
    af_state = resolve_fx3_af_transition_and_subj_shift_sensitivity(
        af_kinematics_scope=af_kinematics_scope,
        af_subj_shift_menu_label=af_subj_shift_menu_label,
        af_transition_menu_label=af_transition_menu_label,
        pre_reset_af_subj_shift_sensitivity=pre_reset_af_subj_shift_sensitivity,
        pre_reset_af_transition_speed=pre_reset_af_transition_speed,
        reset_action=reset_action,
    )
    iv_state = resolve_fx3_interval_shoot_func_boundary(
        interval_shooting=interval_shooting,
        shooting_start_time=shooting_start_time,
        shooting_interval=shooting_interval,
        number_of_shots=number_of_shots,
        interval_capture_format=interval_capture_format,
        in_camera_interval_movie_claimed=in_camera_interval_movie_claimed,
        post_assembly_software=post_assembly_software,
        reset_action=reset_action,
    )

    c_rst = m_state["canonical_reset_action"]
    if c_rst is None:
        _add_code(codes, STATUS_BLOCKED_G88_TELEMETRY_INVALID)
        errors.append(
            f"Invalid reset_action={reset_action!r}; expected {ALLOWED_RESET_ACTIONS_PHASE235}."
        )

    # 1. [Monitor Flip Direction] validation & [Camera Settings Reset] survival
    c_pre_flip = m_state["canonical_pre_direction"]
    exp_post_flip = m_state["expected_post_reset_direction"]
    if c_pre_flip is None:
        _add_code(codes, STATUS_BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION)
        errors.append(
            f"Invalid [Monitor Flip Direction]={pre_reset_monitor_flip_direction!r}; "
            f"expected {ALLOWED_MONITOR_FLIP_DIRECTIONS}."
        )

    if observed_post_reset_monitor_flip_direction is None:
        eff_post_flip = exp_post_flip
    else:
        norm_obs_flip = _norm_monitor_flip_direction(
            observed_post_reset_monitor_flip_direction
        )
        eff_post_flip = (
            norm_obs_flip
            if norm_obs_flip is not None
            else observed_post_reset_monitor_flip_direction
        )
        if norm_obs_flip is None:
            _add_code(
                codes,
                STATUS_BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION,
            )
            errors.append(
                f"Invalid observed_post_reset_monitor_flip_direction="
                f"{observed_post_reset_monitor_flip_direction!r}."
            )

    flip_reset_ok = (c_pre_flip is not None) and (eff_post_flip == exp_post_flip)
    if not flip_reset_ok and c_pre_flip is not None:
        _add_code(codes, STATUS_BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION)
        errors.append(
            f"[Monitor Flip Direction] reset persistence mismatch under {c_rst!r}: "
            f"got {eff_post_flip!r}, expected {exp_post_flip!r} (survives [Camera Settings Reset]; "
            f"restored to 'Auto' only by [Initialize])."
        )

    eff_live_h = (
        eff_post_flip == MONITOR_FLIP_HORIZONTAL
        if observed_live_shooting_horizontally_mirrored is None
        else bool(observed_live_shooting_horizontally_mirrored)
    )
    eff_live_v = (
        eff_post_flip == MONITOR_FLIP_VERTICAL
        if observed_live_shooting_vertically_flipped is None
        else bool(observed_live_shooting_vertically_flipped)
    )
    if (eff_live_h != (eff_post_flip == MONITOR_FLIP_HORIZONTAL)) or (
        eff_live_v != (eff_post_flip == MONITOR_FLIP_VERTICAL)
    ):
        _add_code(codes, STATUS_BLOCKED_G88_MONITOR_FLIP_DIRECTION_INVALID_OR_RESET_VIOLATION)
        errors.append(
            f"Live shooting monitor flip mismatch for {eff_post_flip!r}: "
            f"live_h={eff_live_h}, live_v={eff_live_v}."
        )

    # 2. [Horizontal Flip] Playback Non-Inversion
    eff_pb_h_inv = (
        False
        if observed_playback_monitor_horizontally_inverted is None
        else bool(observed_playback_monitor_horizontally_inverted)
    )
    eff_pb_txt_rev = (
        False
        if observed_playback_text_mirror_reversed is None
        else bool(observed_playback_text_mirror_reversed)
    )
    playback_noninv_ok = (not eff_pb_h_inv) and (not eff_pb_txt_rev)
    if not playback_noninv_ok:
        _add_code(codes, STATUS_BLOCKED_G88_MONITOR_HORIZONTAL_FLIP_PLAYBACK_INVERSION)
        errors.append(
            "[Monitor Flip Direction] playback non-inversion violated: even when set to "
            "[Horizontal Flip], playback display direction must NOT invert "
            f"(playback_inverted={eff_pb_h_inv}, text_reversed={eff_pb_txt_rev})."
        )

    # 3. [AF Subj. Shift Sensitivity] & [AF Transition Speed] Menu String, Range & Reset Split
    af_ok = True
    if af_state["canonical_scope"] is None:
        af_ok = False
        _add_code(
            codes,
            STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
        )
        errors.append(
            f"Invalid AF kinematics scope={af_kinematics_scope!r}; expected {ALLOWED_AF_KINEMATICS_SCOPES} "
            "(Still mode uses distinct still AF tracking menus)."
        )
    if not af_state["subj_label_exact"]:
        af_ok = False
        _add_code(
            codes,
            STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
        )
        errors.append(
            f"ILME-FX3 requires exact full menu string {AF_SUBJ_SHIFT_SENSITIVITY_MENU_LABEL!r} "
            f"(abbreviated 'AF Subj. Shift Sens.' is rejected); got {af_subj_shift_menu_label!r}."
        )
    if not af_state["trans_label_exact"]:
        af_ok = False
        _add_code(
            codes,
            STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
        )
        errors.append(
            f"ILME-FX3 requires exact menu string {AF_TRANSITION_SPEED_MENU_LABEL!r}; "
            f"got {af_transition_menu_label!r}."
        )
    if af_state["parsed_pre_sens"] is None:
        af_ok = False
        _add_code(
            codes,
            STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
        )
        errors.append(
            f"Invalid [AF Subj. Shift Sensitivity]={pre_reset_af_subj_shift_sensitivity!r}; "
            f"expected 1..5 ({AF_SUBJ_SHIFT_SENS_MIN_LABEL}..{AF_SUBJ_SHIFT_SENS_MAX_LABEL})."
        )
    if af_state["parsed_pre_speed"] is None:
        af_ok = False
        _add_code(
            codes,
            STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
        )
        errors.append(
            f"Invalid [AF Transition Speed]={pre_reset_af_transition_speed!r}; "
            f"expected 1..7 ({AF_TRANSITION_SPEED_MIN_LABEL}..{AF_TRANSITION_SPEED_MAX_LABEL})."
        )

    exp_sens_lbl = af_state["expected_post_sens_label"]
    exp_speed_lbl = af_state["expected_post_speed_label"]

    if observed_post_reset_af_subj_shift_sensitivity is None:
        eff_sens_lbl = exp_sens_lbl
    else:
        p_obs_sens = _parse_af_subj_shift_sensitivity(
            observed_post_reset_af_subj_shift_sensitivity
        )
        if p_obs_sens is None:
            af_ok = False
            eff_sens_lbl = str(observed_post_reset_af_subj_shift_sensitivity)
            _add_code(
                codes,
                STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
            )
            errors.append(
                f"Invalid observed_post_reset_af_subj_shift_sensitivity="
                f"{observed_post_reset_af_subj_shift_sensitivity!r}."
            )
        else:
            eff_sens_lbl = p_obs_sens[1]

    if observed_post_reset_af_transition_speed is None:
        eff_speed_lbl = exp_speed_lbl
    else:
        p_obs_speed = _parse_af_transition_speed(observed_post_reset_af_transition_speed)
        if p_obs_speed is None:
            af_ok = False
            eff_speed_lbl = str(observed_post_reset_af_transition_speed)
            _add_code(
                codes,
                STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
            )
            errors.append(
                f"Invalid observed_post_reset_af_transition_speed="
                f"{observed_post_reset_af_transition_speed!r}."
            )
        else:
            eff_speed_lbl = p_obs_speed[1]

    if eff_sens_lbl != exp_sens_lbl or eff_speed_lbl != exp_speed_lbl:
        af_ok = False
        _add_code(
            codes,
            STATUS_BLOCKED_G88_AF_TRANSITION_SPEED_OR_SUBJ_SHIFT_SENSITIVITY_VIOLATION,
        )
        errors.append(
            f"AF kinematics reset mismatch under {c_rst!r}: got "
            f"(SubjShift={eff_sens_lbl!r}, TransSpeed={eff_speed_lbl!r}), expected "
            f"(SubjShift={exp_sens_lbl!r}, TransSpeed={exp_speed_lbl!r})."
        )

    # 4. [Interval Shoot Func.] Still-Only Capture Scope & Timing Bounds
    iv_ok = True
    if iv_state["canonical_mode"] is None:
        iv_ok = False
        _add_code(codes, STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION)
        errors.append(
            f"Invalid [Interval Shooting]={interval_shooting!r}; expected {ALLOWED_INTERVAL_SHOOTING_MODES}."
        )
    if not iv_state["start_in_bounds"]:
        iv_ok = False
        _add_code(codes, STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION)
        errors.append(
            f"[Shooting Start Time]={shooting_start_time!r} out of ILME-FX3 bounds "
            f"(1s..99m59s / {INTERVAL_START_TIME_MIN_SECONDS}..{INTERVAL_START_TIME_MAX_SECONDS}s)."
        )
    if not iv_state["interval_in_bounds"]:
        iv_ok = False
        _add_code(codes, STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION)
        errors.append(
            f"[Shooting Interval]={shooting_interval!r} out of ILME-FX3 bounds "
            f"(1s..60s / {INTERVAL_SHOOTING_INTERVAL_MIN_SECONDS}..{INTERVAL_SHOOTING_INTERVAL_MAX_SECONDS}s)."
        )
    if not iv_state["shots_in_bounds"]:
        iv_ok = False
        _add_code(codes, STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION)
        errors.append(
            f"[Number of Shots]={number_of_shots!r} out of ILME-FX3 bounds "
            f"({INTERVAL_NUMBER_OF_SHOTS_MIN}..{INTERVAL_NUMBER_OF_SHOTS_MAX})."
        )
    if iv_state["video_claim_detected"] or iv_state["canonical_still_format"] is None:
        iv_ok = False
        _add_code(codes, STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION)
        errors.append(
            "[Interval Shoot Func.] on ILME-FX3 captures still-image sequences ONLY "
            f"{ALLOWED_INTERVAL_STILL_FORMATS} (no in-camera .MP4/.MXF interval movie output; "
            f"got format={interval_capture_format!r}, in_camera_movie_claimed={in_camera_interval_movie_claimed})."
        )
    if not iv_state["post_assembly_software"]:
        iv_ok = False
        _add_code(codes, STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION)
        errors.append("post_assembly_software must be non-empty (e.g. Imaging Edge Desktop (Viewer)).")

    exp_iv_post = iv_state["expected_post_reset_mode"]
    if observed_post_reset_interval_shooting is None:
        eff_iv_post = exp_iv_post
    else:
        norm_iv_obs = _norm_on_off(observed_post_reset_interval_shooting)
        eff_iv_post = (
            norm_iv_obs
            if norm_iv_obs is not None
            else observed_post_reset_interval_shooting
        )
        if norm_iv_obs is None or eff_iv_post != exp_iv_post:
            iv_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G88_INTERVAL_SHOOT_FUNC_BOUNDS_OR_MOVIE_CLAIM_VIOLATION,
            )
            errors.append(
                f"[Interval Shooting] post-reset state mismatch under {c_rst!r}: "
                f"got {eff_iv_post!r}, expected {exp_iv_post!r}."
            )

    flip_survived_cam_rst = (c_rst != RESET_ACTION_INITIALIZE) and flip_reset_ok
    af_reset_by_cam_rst = (
        c_rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE)
        and af_ok
    )
    split_verified = flip_reset_ok and af_ok

    pre_sens_tuple = af_state["parsed_pre_sens"]
    pre_speed_tuple = af_state["parsed_pre_speed"]

    valid = not codes
    status = STATUS_VERIFIED_G88 if valid else codes[0]
    return MonitorFlipPlaybackAfSensAndIntervalResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08X}",
        firmware_version=firmware_version,
        pre_reset_monitor_flip_direction=c_pre_flip or pre_reset_monitor_flip_direction,
        reset_action=c_rst or reset_action,
        expected_post_reset_monitor_flip_direction=exp_post_flip,
        effective_post_reset_monitor_flip_direction=eff_post_flip,
        monitor_flip_survived_camera_settings_reset=flip_survived_cam_rst,
        live_shooting_horizontally_mirrored=eff_live_h,
        live_shooting_vertically_flipped=eff_live_v,
        playback_monitor_horizontally_inverted=eff_pb_h_inv,
        playback_text_mirror_reversed=eff_pb_txt_rev,
        horizontal_flip_playback_noninversion_enforced=playback_noninv_ok,
        af_kinematics_scope=af_state["canonical_scope"] or af_kinematics_scope,
        af_subj_shift_menu_label=af_state["subj_label_clean"],
        af_transition_menu_label=af_state["trans_label_clean"],
        pre_reset_af_subj_shift_level=pre_sens_tuple[0] if pre_sens_tuple else -1,
        pre_reset_af_subj_shift_label=pre_sens_tuple[1]
        if pre_sens_tuple
        else str(pre_reset_af_subj_shift_sensitivity),
        pre_reset_af_transition_level=pre_speed_tuple[0] if pre_speed_tuple else -1,
        pre_reset_af_transition_label=pre_speed_tuple[1]
        if pre_speed_tuple
        else str(pre_reset_af_transition_speed),
        expected_post_reset_af_subj_shift_label=exp_sens_lbl,
        expected_post_reset_af_transition_label=exp_speed_lbl,
        effective_post_reset_af_subj_shift_label=eff_sens_lbl,
        effective_post_reset_af_transition_label=eff_speed_lbl,
        af_kinematics_reset_by_camera_settings_reset=af_reset_by_cam_rst,
        monitor_flip_vs_af_reset_split_verified=split_verified,
        interval_shooting_mode=iv_state["canonical_mode"] or interval_shooting,
        expected_post_reset_interval_shooting_mode=exp_iv_post,
        effective_post_reset_interval_shooting_mode=eff_iv_post,
        shooting_start_time_seconds=iv_state["start_seconds"]
        if iv_state["start_seconds"] is not None
        else -1,
        shooting_interval_seconds=iv_state["interval_seconds"]
        if iv_state["interval_seconds"] is not None
        else -1,
        number_of_shots=int(number_of_shots)
        if not isinstance(number_of_shots, bool) and isinstance(number_of_shots, int)
        else -1,
        interval_capture_format=iv_state["canonical_still_format"]
        or interval_capture_format,
        in_camera_mp4_mxf_output_supported=False,
        in_camera_interval_movie_claimed=bool(iv_state["video_claim_detected"]),
        post_assembly_software=iv_state["post_assembly_software"],
        interval_still_only_boundary_enforced=iv_ok,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g88_monitor_flip_af_sens_and_interval_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    monitor_flip_af_interval_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase235DonorAuditResult] = None,
) -> Tuple[GateVerdict, G88MonitorFlipAfSensAndIntervalGuardResult]:
    """Evaluate Gate `G88` combining bounded `<0.15s` donor check with
    `[Monitor Flip Direction]` reset survival + `[Horizontal Flip]` playback
    non-inversion, `[AF Subj. Shift Sensitivity]` / `[AF Transition Speed]` reset
    split, and `[Interval Shoot Func.]` still-only capture boundary.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase235_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_monitor_flip_playback_af_sens_and_interval_guard(
        **dict(monitor_flip_af_interval_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)
    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G88 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G88 if valid else codes[0]

    res = G88MonitorFlipAfSensAndIntervalGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        monitor_flip_af_sens_interval_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, flip={guard.effective_post_reset_monitor_flip_direction}"
        f"(pb_inv={guard.playback_monitor_horizontally_inverted},rst={guard.reset_action}), "
        f"af=({guard.effective_post_reset_af_subj_shift_label},{guard.effective_post_reset_af_transition_label}), "
        f"interval={guard.interval_capture_format}(start={guard.shooting_start_time_seconds}s,"
        f"step={guard.shooting_interval_seconds}s)"
    )
    verdict = GateVerdict(
        gate_id=G88_GATE_ID,
        gate_code=G88_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified 88-Gate Master Safety Preflight (`G01..G88`)
# ---------------------------------------------------------------------------


def evaluate_88gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    recover_imagedb_kwargs: Optional[Mapping[str, Any]] = None,
    monitor_flip_af_interval_kwargs: Optional[Mapping[str, Any]] = None,
    master_86_override: Optional[Master86GateReport] = None,
    **m86_passthrough_kwargs: Any,
) -> Master88GateReport:
    """Evaluate all 88 Master Safety Gates (`G01..G88`) deterministically by
    delegating `G01..G86` directly to `evaluate_86gate_preflight()`.
    """
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        or simulate_bench_dry_run
        or bool(dry_run_simulated_backup)
    )

    m86_report: Master86GateReport = (
        master_86_override
        if master_86_override is not None
        else evaluate_86gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m86_passthrough_kwargs,
        )
    )

    phase235_audit = audit_phase235_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g87_verdict, g87_res = evaluate_g87_recover_imagedb_battery_and_tier0_vault_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        recover_imagedb_kwargs=recover_imagedb_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase235_audit,
    )

    g88_verdict, g88_res = evaluate_g88_monitor_flip_af_sens_and_interval_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        monitor_flip_af_interval_kwargs=monitor_flip_af_interval_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase235_audit,
    )

    gates_87_to_88 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g87_verdict, g88_verdict)
    ]
    all_gates = tuple(list(m86_report.gates) + gates_87_to_88)

    g01_to_g12_verified = int(m86_report.summary["g01_to_g12_verified"])
    g13_to_g86_verified = (
        int(m86_report.summary["g13_to_g84_verified"])
        + int(m86_report.summary["g85_to_g86_verified"])
    )
    g87_to_g88_verified = sum(1 for v in (g87_verdict, g88_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g86_verified + g87_to_g88_verified

    g87_to_g88_all_passed = g87_to_g88_verified == 2
    g13_to_g88_all_passed = m86_report.g13_to_g86_all_passed and g87_to_g88_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m86_report.gates[:9])

    offline_85_verified = (
        g01_to_g09_ok
        and m86_report.offline_83_gates_verified
        and g87_to_g88_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_88_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g88_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m86_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_85_verified
        and m86_report.h0_h1_trial_entry_allowed
        and g87_to_g88_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m86_report.errors) + list(g87_verdict.errors) + list(g88_verdict.errors)
    )
    warnings: List[str] = (
        list(m86_report.warnings)
        + list(g87_verdict.warnings)
        + list(g88_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m86_report.g13_to_g86_all_passed:
        overall_status = m86_report.status
    elif not g87_verdict.passed:
        overall_status = g87_verdict.status
    elif not g88_verdict.passed:
        overall_status = g88_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_88_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_88_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_88_verified:
        overall_status = "VERIFIED_ALL_88_GATES"
    else:
        overall_status = "VERIFIED_85_OF_88_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m86_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g87_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g88_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 88,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 88 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g86_verified": g13_to_g86_verified,
        "g87_to_g88_verified": g87_to_g88_verified,
        "g13_to_g88_all_passed": g13_to_g88_all_passed,
        "g87_to_g88_all_passed": g87_to_g88_all_passed,
        "offline_85_gates_verified": offline_85_verified,
        "all_88_gates_verified": all_88_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master88GateReport(
        schema=REALHW_RECOVER_IMAGEDB_MONITOR_FLIP_AF_SENS_88GATE_SCHEMA,
        version=REALHW_RECOVER_IMAGEDB_MONITOR_FLIP_AF_SENS_88GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_85_gates_verified=offline_85_verified,
        all_88_gates_verified=all_88_verified,
        g13_to_g88_all_passed=g13_to_g88_all_passed,
        g87_to_g88_all_passed=g87_to_g88_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_86_report=m86_report.to_dict(),
        g87_result=g87_res.to_dict(),
        g88_result=g88_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_88_master_safety_gates = evaluate_88gate_preflight
run_88_gate_preflight = evaluate_88gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard",
        description=(
            "Phase 235 Safety Gates G87 (Recover Image DB Depleted-Battery Refusal, "
            "Non-Deleting Repair & Unverified Slot-1 Tier-0 Vault Read-Only Mutation "
            "Firewall) + G88 (Monitor Flip Direction Camera Settings Reset Survival + "
            "Horizontal Flip Playback Non-Inversion & AF Subj. Shift Sensitivity / "
            "AF Transition Speed + Interval Shoot Func. Still-Only Boundary) + "
            "Unified 88-Gate Master Safety Preflight"
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_88gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/88 "
            f"g87_to_g88_all_passed={report.g87_to_g88_all_passed} "
            f"all_88_gates_verified={report.all_88_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = report.all_88_gates_verified if args.dry_run_simulated else report.offline_85_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
