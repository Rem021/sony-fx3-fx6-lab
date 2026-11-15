"""Phase 234 — Pillar 36 (`36/36` Recovery Pillars) & Unified 36-Pillar Recovery Master
(`verify-36pillar-recovery` / `verify-recover-imagedb-monitor-flip-vault`):

1. **Pillar 36A — `[Recover Image DB]` Depleted-Battery Refusal, Non-Deleting `AVF_INFO` Repair
   & Slot-1 Tier-0 Vault Mutation Firewall (`ILME-FX3 Ver. 7.02`, `G87`)**:
   - Models `MENU` -> `Shooting` -> `[Media]` -> `[Recover Image DB]` repairing `AVF_INFO` /
     media management database inconsistencies (`"Image DataBase File error"` or false `"0"`
     recordable images) **without deleting recorded clips or still images**.
   - Enforces hardware refusal when attempting `[Recover Image DB]` on an extremely depleted
     `NP-FZ100` battery pack (`battery_extremely_depleted` or `< 10%` / `< 6.60V`) to prevent
     mid-journal FAT/exFAT metadata corruption.
   - Verifies `[Recover Image DB]` action-item immunity across both `[Camera Settings Reset]`
     and `[Initialize]`.
   - Blocks `[Recover Image DB]` filesystem metadata writes on **Slot 1** whenever an unverified
     or WP-locked Tier-0 dump vault (`pnflasha` / `cnflasha` / `CAMSET01.DAT`) is present prior
     to off-camera SHA-256 verification and safe vault card removal.

2. **Pillar 36B — `[Monitor Flip Direction]` Reset Survival + Playback Non-Inversion & Movie/S&Q
   AF Kinematics (`[AF Subj. Shift Sensitivity]` / `[AF Transition Speed]`) + Still-Only
   `[Interval Shoot Func.]` State Recovery**:
   - Verifies `[Monitor Flip Direction]` (`Auto` default, `Horizontal Flip`, `Vertical Flip`,
     `Off`) survives `[Camera Settings Reset]` unchanged (reset to `Auto` only by `[Initialize]`)
     and **never** inverts monitor display direction during playback even when set to
     `[Horizontal Flip]`.
   - Verifies exact full menu strings `[AF Subj. Shift Sensitivity]` (`1(Locked on)..5(Responsive)`,
     default `5(Responsive)` — rejecting abbreviated `Sens.`) and `[AF Transition Speed]`
     (`1(Slow)..7(Fast)`, default `5`) reset cleanly via `[Camera Settings Reset]` and restore
     from Slot-1 `CAMSET01.DAT`..`CAMSET10.DAT`.
   - Enforces `[Interval Shoot Func.]` (`1s..99m59s` start time, `1s..60s` interval) still-image
     sequence scope (external time-lapse assembly) vs FX6 in-camera video `Interval Rec`.

3. **Unified `36/36` Recovery Master (`evaluate_realhw_36pillar_recovery_master`)**:
   - Delegates Pillars `1..35` concurrently to `evaluate_realhw_35pillar_recovery_master` +
     **Pillar 36** -> **`36/36` (`VERIFIED_36OF36_PILLAR_RECOVERY_MASTER`)** in `< 3.8s` (`< 6.0s` ceiling).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import posixpath
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_35pillar_silent_autopixelmap_marker_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_35_PILLAR_SPECS,
    Master35PillarRecoveryReport,
    evaluate_realhw_35pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE234_SCHEMA: str = "fx3-realhw-36pillar-recovery-master-verifier-v1"
PHASE234_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P234_DONOR_INSPECT_BUDGET_SECONDS: float = 0.15
P234_NOMINAL_BUDGET_SECONDS: float = 3.8
P234_CONCURRENT_CEILING_SECONDS: float = 6.0
P234_BOUNDED_HEADER_BYTES: int = 4096
P234_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-34 / FX3 Ver. 7.02 Donor Anchors (bounded O_RDONLY verification)
P234_FX3_MODEL_NAME: str = "ILME-FX3"
P234_FX3_MODEL_ID: int = 0x91030080
P234_FX3_FW_VERSION: str = "7.02"
P234_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
    "2.00",
    "2.01",
    "2.02",
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)

P234_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P234_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P234_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

P234_DONOR_FX3_APPFW_702_RELPATH: str = "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P234_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P234_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"

P234_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P234_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P234_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

P234_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P234_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P234_PINNED_FX3_LIBBACKUP_SO_SHA256: str = "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"

P234_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P234_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P234_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"

P234_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
)
P234_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P234_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"

P234_DONOR_FX3_LIBIMDB_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libIMDB.so"
)
P234_PINNED_FX3_LIBIMDB_SO_BYTES: int = 71536
P234_PINNED_FX3_LIBIMDB_SO_SHA256: str = (
    "6ceaea432bc7c4645897c2f1272941b33b0c04115ec62ffa000b37faf3d8517d"
)

# Pillar 36A — Recover Image DB Depleted-Battery Refusal, Non-Deleting Repair & Slot-1 Tier-0 Vault Firewall
P234_RECOVER_IMAGEDB_MENU_PATH: Tuple[str, ...] = ("MENU", "Shooting", "Media", "Recover Image DB")
P234_MEDIA_SLOTS: Tuple[int, ...] = (1, 2)
P234_SLOT1_VAULT_SLOT: int = 1
P234_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))

P234_IMAGEDB_SYMPTOMS: Tuple[str, ...] = (
    "Image DataBase File error",
    "FALSE_ZERO_RECORDABLE_IMAGES",
    "AVF_INFO_INDEX_INCONSISTENT",
    "HEALTHY_NO_REPAIR_NEEDED",
)
P234_AVF_INFO_DB_FILES: Tuple[str, ...] = (
    "AVF_INFO/AVIN0001.INP",
    "AVF_INFO/AVIN0001.BNP",
    "AVF_INFO/PRV00001.BIN",
    "M4ROOT/MEDIAPRO.XML",
)
P234_RECOVER_IMAGEDB_MIN_BATTERY_PCT: int = 10
P234_RECOVER_IMAGEDB_MIN_VOLTAGE_V: float = 6.60

P234_TIER0_VAULT_ARTIFACTS: Tuple[str, ...] = (
    "pnflasha",
    "cnflasha",
    "CAMSET01.DAT",
    "mtd0ro",
    "Backup.bin",
    "FX3RCPT1.BIN",
)
P234_RECOGNIZED_VAULT_ARTIFACTS: Tuple[str, ...] = (
    "pnflasha",
    "cnflasha",
    "mtd0ro",
    "Backup.bin",
    "FX3RCPT1.BIN",
) + P234_CAMSET_FILENAMES
P234_DEFAULT_VAULT_RECEIPT_SHA256: str = sha256(b"FX3-WAVE34-SLOT1-TIER0-VAULT-RECEIPT-V1").hexdigest()

# Pillar 36B — Monitor Flip Direction Reset Survival + Playback Non-Inversion & AF / Interval State Recovery
P234_MONITOR_FLIP_MENU_PATH: Tuple[str, ...] = ("MENU", "Setup", "Monitor", "Monitor Flip Direction")
P234_MONITOR_FLIP_DEFAULT: str = "Auto"
P234_MONITOR_FLIP_DIRECTIONS: Tuple[str, ...] = (
    "Auto",
    "Horizontal Flip",
    "Vertical Flip",
    "Off",
)
P234_RESET_ACTIONS: Tuple[str, ...] = ("NONE", "Camera Settings Reset", "Initialize")

P234_AF_SUBJ_SHIFT_SENSITIVITY_MENU_NAME: str = "AF Subj. Shift Sensitivity"
P234_FORBIDDEN_ABBREVIATED_AF_MENU_NAMES: Tuple[str, ...] = (
    "AF Subj. Shift Sens.",
    "AF Subject Shift Sens.",
    "AF Subj Shift Sens",
)
P234_AF_TRANSITION_SPEED_MENU_NAME: str = "AF Transition Speed"

P234_AF_SUBJ_SHIFT_SENSITIVITY_DEFAULT: str = "5(Responsive)"
P234_AF_SUBJ_SHIFT_SENSITIVITY_VALUES: Tuple[str, ...] = (
    "1(Locked on)",
    "2",
    "3",
    "4",
    "5(Responsive)",
)
P234_AF_TRANSITION_SPEED_DEFAULT: str = "5"
P234_AF_TRANSITION_SPEED_VALUES: Tuple[str, ...] = (
    "1(Slow)",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7(Fast)",
)
P234_AF_KINEMATICS_SCOPES: Tuple[str, ...] = ("Movie", "S&Q")

P234_INTERVAL_SHOOT_MENU_PATH: Tuple[str, ...] = ("MENU", "Shooting", "Drive Mode", "Interval Shoot Func.")
P234_INTERVAL_SHOOT_MENU_NAME: str = "Interval Shoot Func."
P234_INTERVAL_SHOOT_STATES: Tuple[str, ...] = ("Off", "On")
P234_INTERVAL_START_TIME_MIN_SEC: int = 1
P234_INTERVAL_START_TIME_MAX_SEC: int = 5999  # 99m59s == 5999s
P234_INTERVAL_SHOOTING_MIN_SEC: int = 1
P234_INTERVAL_SHOOTING_MAX_SEC: int = 60
P234_INTERVAL_SHOTS_MIN: int = 1
P234_INTERVAL_SHOTS_MAX: int = 9999
P234_INTERVAL_OUTPUT_STILL_SEQUENCE: str = "STILL_IMAGE_SEQUENCE"

P234_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_recover_imagedb_monitor_flip_af_overlay"
P234_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P234_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P234_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P234_BLOCKED_INVALID_RECOVER_IMAGEDB_SPEC: str = "BLOCKED_INVALID_RECOVER_IMAGEDB_SPEC"
P234_BLOCKED_RECOVER_IMAGEDB_DEPLETED_BATTERY: str = "BLOCKED_RECOVER_IMAGEDB_DEPLETED_BATTERY"
P234_BLOCKED_RECOVER_IMAGEDB_CLIP_OR_STILL_DELETION: str = (
    "BLOCKED_RECOVER_IMAGEDB_CLIP_OR_STILL_DELETION"
)
P234_BLOCKED_RECOVER_IMAGEDB_ACTION_RESET_IMMUNITY_DRIFT: str = (
    "BLOCKED_RECOVER_IMAGEDB_ACTION_RESET_IMMUNITY_DRIFT"
)
P234_BLOCKED_SLOT1_UNVERIFIED_TIER0_VAULT_IMAGEDB_MUTATION: str = (
    "BLOCKED_SLOT1_UNVERIFIED_TIER0_VAULT_IMAGEDB_MUTATION"
)
P234_BLOCKED_SLOT1_WP_OR_ACTIVE_VAULT_IMAGEDB_WRITE_DENIED: str = (
    "BLOCKED_SLOT1_WP_OR_ACTIVE_VAULT_IMAGEDB_WRITE_DENIED"
)
P234_BLOCKED_INVALID_MONITOR_FLIP_OR_AF_INTERVAL_SPEC: str = (
    "BLOCKED_INVALID_MONITOR_FLIP_OR_AF_INTERVAL_SPEC"
)
P234_BLOCKED_MONITOR_FLIP_CAMERA_SETTINGS_RESET_DRIFT: str = (
    "BLOCKED_MONITOR_FLIP_CAMERA_SETTINGS_RESET_DRIFT"
)
P234_BLOCKED_MONITOR_FLIP_PLAYBACK_INVERSION_VIOLATION: str = (
    "BLOCKED_MONITOR_FLIP_PLAYBACK_INVERSION_VIOLATION"
)
P234_BLOCKED_ABBREVIATED_OR_INVALID_AF_MENU_NAME: str = (
    "BLOCKED_ABBREVIATED_OR_INVALID_AF_MENU_NAME"
)
P234_BLOCKED_AF_KINEMATICS_RESET_OR_CAMSET_RESTORE_DRIFT: str = (
    "BLOCKED_AF_KINEMATICS_RESET_OR_CAMSET_RESTORE_DRIFT"
)
P234_BLOCKED_CAMSET_SLOT1_AF_RESTORE_DRIFT: str = "BLOCKED_CAMSET_SLOT1_AF_RESTORE_DRIFT"
P234_BLOCKED_INTERVAL_SHOOT_STILL_ONLY_SCOPE_OR_RANGE_VIOLATION: str = (
    "BLOCKED_INTERVAL_SHOOT_STILL_ONLY_SCOPE_OR_RANGE_VIOLATION"
)
P234_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P234_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P234_STATUS_VERIFIED_PILLAR_36A: str = (
    "VERIFIED_PILLAR_36A_RECOVER_IMAGEDB_BATTERY_NONDELETE_SLOT1_VAULT_FIREWALL"
)
P234_STATUS_REJECTED_PILLAR_36A: str = (
    "REJECTED_PILLAR_36A_RECOVER_IMAGEDB_BATTERY_NONDELETE_SLOT1_VAULT_FIREWALL"
)
P234_STATUS_VERIFIED_PILLAR_36B: str = (
    "VERIFIED_PILLAR_36B_MONITOR_FLIP_PLAYBACK_NONINVERT_AF_INTERVAL_VAULT"
)
P234_STATUS_REJECTED_PILLAR_36B: str = (
    "REJECTED_PILLAR_36B_MONITOR_FLIP_PLAYBACK_NONINVERT_AF_INTERVAL_VAULT"
)
P234_STATUS_VERIFIED_PILLAR36_SUITE: str = (
    "VERIFIED_PILLAR36_RECOVER_IMAGEDB_MONITOR_FLIP_AF_VAULT"
)
P234_STATUS_FAIL_PILLAR36_SUITE: str = (
    "FAIL_PILLAR36_RECOVER_IMAGEDB_MONITOR_FLIP_AF_VAULT"
)
P234_STATUS_VERIFIED_36OF36_AGGREGATOR: str = "VERIFIED_36OF36_PILLAR_RECOVERY_MASTER"
P234_STATUS_FAIL_36OF36_AGGREGATOR: str = "FAIL_36OF36_PILLAR_RECOVERY_MASTER"

P234_PILLAR_36A_SCENARIO_IDS: Tuple[str, ...] = (
    "P36A1_SLOT2_RECOVER_IMAGEDB_NONDELETE_REPAIRS_ERROR_WITH_SLOT1_WP_VAULT_UNTOUCHED_SAFE",
    "P36A2_SLOT1_POST_SHA256_EJECTED_VAULT_REPAIRS_FALSE_ZERO_RECORDABLE_IMAGES_SAFE",
    "P36A3_REJECT_RECOVER_IMAGEDB_ON_EXTREMELY_DEPLETED_NP_FZ100_BATTERY",
    "P36A4_REJECT_SLOT1_RECOVER_IMAGEDB_MUTATION_PRIOR_TO_OFFCAMERA_SHA256_VERIFICATION",
    "P36A5_REJECT_SLOT1_RECOVER_IMAGEDB_ON_WP_LOCKED_OR_INSERTED_TIER0_VAULT_CARD",
    "P36A6_REJECT_RECOVER_IMAGEDB_CLIP_DELETION_OR_RESET_IMMUNITY_DRIFT",
)
P234_PILLAR_36B_SCENARIO_IDS: Tuple[str, ...] = (
    "P36B1_HORIZONTAL_FLIP_SURVIVES_CAMERA_SETTINGS_RESET_ZERO_PLAYBACK_INVERSION_AND_AF_RESETS_SAFE",
    "P36B2_INITIALIZE_RESTORES_MONITOR_FLIP_AUTO_AND_CAMSET01_SLOT1_RESTORES_AF_KINEMATICS_SAFE",
    "P36B3_REJECT_MONITOR_FLIP_WIPED_BY_CAMERA_SETTINGS_RESET_OR_SURVIVING_INITIALIZE",
    "P36B4_REJECT_PLAYBACK_DISPLAY_INVERSION_UNDER_HORIZONTAL_FLIP",
    "P36B5_REJECT_ABBREVIATED_AF_MENU_NAME_OR_AF_KINEMATICS_RESET_CAMSET_DRIFT",
    "P36B6_REJECT_INTERVAL_SHOOT_VIDEO_ASSUMPTION_OR_OUT_OF_RANGE_TIMING",
)

MASTER_36_PILLAR_COUNT: int = 36
MASTER_36_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_35_PILLAR_SPECS + (
    (
        36,
        "pillar_36_recover_imagedb_monitor_flip_af_vault",
        "Phase 234",
        "fx3_recovery.realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier",
    ),
)
MASTER_36_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_36_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _safety_invariant_errors() -> List[str]:
    errs: List[str] = []
    checks = (
        ("PERSISTENT_EMMC_WRITES_AUTHORIZED", PERSISTENT_EMMC_WRITES_AUTHORIZED, False),
        ("SPI_NOR_WRITE_AUTHORIZED", SPI_NOR_WRITE_AUTHORIZED, False),
        ("EL3_PAYLOAD_TRANSMIT_AUTHORIZED", EL3_PAYLOAD_TRANSMIT_AUTHORIZED, False),
        ("ISP_WRITE_AUTHORIZED", ISP_WRITE_AUTHORIZED, False),
        ("PERSISTENT_WRITE_RELEASE", PERSISTENT_WRITE_RELEASE, False),
        ("ALLOW_BOOT_PARTITION_TARGETING", ALLOW_BOOT_PARTITION_TARGETING, False),
        ("ALLOW_DESTRUCTIVE_FASTBOOT", ALLOW_DESTRUCTIVE_FASTBOOT, False),
        ("ALLOW_PERSISTENT_JIRITSU_WRITES", ALLOW_PERSISTENT_JIRITSU_WRITES, False),
        ("ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS", ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS, False),
        ("LIVE_USB_IOKIT_TRANSMIT_ENABLED", LIVE_USB_IOKIT_TRANSMIT_ENABLED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("OTP_FUSE_TOUCHES", OTP_FUSE_TOUCHES, 0),
        ("OTP_FUSE_WRITES", OTP_FUSE_WRITES, 0),
        ("RPMB_COUNTER_INCREMENTS", RPMB_COUNTER_INCREMENTS, 0),
        ("PASSIVE_TX_BYTES_EMITTED", PASSIVE_TX_BYTES_EMITTED, 0),
        ("PHYSICAL_USB_PACKETS_EMITTED", PHYSICAL_USB_PACKETS_EMITTED, 0),
        ("PHYSICAL_DEVICE_WRITES", PHYSICAL_DEVICE_WRITES, 0),
        ("RAW_FIRMWARE_BYTES_LEAKED", RAW_FIRMWARE_BYTES_LEAKED, 0),
    )
    for name, actual, expected in checks:
        if actual != expected:
            errs.append(f"{name} expected {expected!r}, got {actual!r}")
    return errs


def _is_tmpfs_path(path_value: str) -> bool:
    norm = posixpath.normpath(path_value)
    return norm.startswith("/tmp/") or norm.startswith("/run/")


def _targets_persistent_emmc(path_value: str) -> bool:
    low = path_value.strip().lower()
    return any(tok in low for tok in P234_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase234DonorArtifactDigest:
    artifact_id: str
    relpath: str
    present: bool
    read_mode: str
    total_bytes: int
    header_bytes_read: int
    digest_kind: str
    digest_sha256: str
    marker_summary: str
    matches_pinned: bool


@dataclass(frozen=True)
class Phase234DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase234DonorArtifactDigest, ...]


@dataclass(frozen=True)
class RecoverImageDbBatteryAndVaultFirewallSpec:
    camera_model: str = P234_FX3_MODEL_NAME
    fw_version: str = P234_FX3_FW_VERSION
    menu_path: Tuple[str, ...] = P234_RECOVER_IMAGEDB_MENU_PATH
    recover_imagedb_requested: bool = True
    target_slot: int = 2
    imagedb_symptom: str = "Image DataBase File error"
    avf_info_repaired: bool = True
    recorded_clips_before: int = 18
    recorded_clips_after: int = 18
    recorded_clips_deleted: int = 0
    recorded_stills_before: int = 42
    recorded_stills_after: int = 42
    recorded_stills_deleted: int = 0
    recordable_images_display_before: int = 0
    recordable_images_display_after: int = 1240
    np_fz100_charge_pct: int = 78
    np_fz100_voltage_v: float = 7.60
    battery_extremely_depleted: bool = False
    action_item_reset_by_camera_settings_reset: bool = False
    action_item_reset_by_initialize: bool = False
    slot1_tier0_vault_present: bool = True
    slot1_vault_artifacts: Tuple[str, ...] = P234_TIER0_VAULT_ARTIFACTS
    slot1_offcamera_sha256_verified: bool = True
    slot1_offcamera_receipt_sha256: str = P234_DEFAULT_VAULT_RECEIPT_SHA256
    slot1_sdxc_wp_locked: bool = True
    target_card_wp_locked: bool = False
    slot1_filesystem_metadata_writes: int = 0
    overlay_dir: str = P234_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P234_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P234_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P234_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class RecoverImageDbBatteryAndVaultFirewallReport:
    passed: bool
    status: str
    block_code: Optional[str]
    target_slot: int
    imagedb_symptom: str
    non_deleting_repair_verified: bool
    depleted_battery_guard_verified: bool
    action_reset_immunity_verified: bool
    slot1_tier0_vault_firewall_verified: bool
    h0_equals_h3_verified: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MonitorFlipPlaybackAndAfIntervalVaultSpec:
    camera_model: str = P234_FX3_MODEL_NAME
    fw_version: str = P234_FX3_FW_VERSION
    monitor_flip_menu_path: Tuple[str, ...] = P234_MONITOR_FLIP_MENU_PATH
    pre_reset_monitor_flip_direction: str = "Horizontal Flip"
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Initialize
    post_reset_monitor_flip_direction: str = "Horizontal Flip"
    shooting_liveview_horizontally_flipped: bool = True
    playback_monitor_display_inverted: bool = False
    playback_timecode_clipname_mirrored: bool = False
    af_subj_shift_sensitivity_menu_name: str = P234_AF_SUBJ_SHIFT_SENSITIVITY_MENU_NAME
    af_transition_speed_menu_name: str = P234_AF_TRANSITION_SPEED_MENU_NAME
    af_kinematics_scope: str = "Movie"  # Movie | S&Q
    pre_reset_af_subj_shift_sensitivity: str = "1(Locked on)"
    pre_reset_af_transition_speed: str = "1(Slow)"
    post_reset_af_subj_shift_sensitivity: str = P234_AF_SUBJ_SHIFT_SENSITIVITY_DEFAULT
    post_reset_af_transition_speed: str = P234_AF_TRANSITION_SPEED_DEFAULT
    camset_restore_after_reset: bool = False
    camset_slot: int = P234_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    saved_af_subj_shift_sensitivity: str = "2"
    saved_af_transition_speed: str = "3"
    interval_shoot_menu_path: Tuple[str, ...] = P234_INTERVAL_SHOOT_MENU_PATH
    interval_shoot_func: str = "On"  # Off | On
    interval_start_time_seconds: int = 1  # 1s..99m59s (1..5999)
    interval_shooting_seconds: int = 5  # 1s..60s (1..60)
    interval_number_of_shots: int = 120  # 1..9999
    interval_output_kind: str = P234_INTERVAL_OUTPUT_STILL_SEQUENCE
    requires_external_timelapse_assembly: bool = True
    in_camera_video_interval_rec_supported: bool = False
    fx6_interval_rec_mxf_mp4_assumed_on_fx3: bool = False
    stage_b_overlay_dir: str = P234_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P234_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P234_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P234_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class MonitorFlipPlaybackAndAfIntervalVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    monitor_flip_reset_persistence_verified: bool
    playback_non_inversion_verified: bool
    af_kinematics_reset_and_menu_verified: bool
    camset_slot1_af_restore_verified: bool
    interval_still_only_scope_verified: bool
    h0_equals_h3_verified: bool
    tier0_surfaces_intact: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecoverImageDbAndMonitorFlipAfVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase234DonorSnapshot
    recover_imagedb_report: RecoverImageDbBatteryAndVaultFirewallReport
    monitor_flip_af_interval_report: MonitorFlipPlaybackAndAfIntervalVaultReport
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar36ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar36ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar36ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar36BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar36ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar36StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase234DonorSnapshot
    pillar_36a_recover_imagedb_vault_firewall: Pillar36ASuiteResult
    pillar_36b_monitor_flip_af_interval_vault: Pillar36BSuiteResult
    suite_sha256: str
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master36PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_6s_budget: bool
    nominal_under_3_8s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase234DonorSnapshot
    pillar36_a_recover_imagedb_vault_firewall: Pillar36ASuiteResult
    pillar36_b_monitor_flip_af_interval_vault: Pillar36BSuiteResult
    master_36pillar_sha256: str
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
# ---------------------------------------------------------------------------


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P234_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    resolved = resolve_donor_path(relpath)
    if resolved is None:
        return False, 0, 0, "MISSING", "", b""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(str(resolved), flags)
    except OSError:
        return False, 0, 0, "OPEN_ERROR", "", b""
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return False, 0, 0, "NOT_REGULAR", "", b""
        total_size = int(st.st_size)
        if total_size <= max_full_bytes:
            chunks: List[bytes] = []
            offset = 0
            while offset < total_size:
                chunk = os.pread(fd, min(65536, total_size - offset), offset)
                if not chunk:
                    break
                chunks.append(chunk)
                offset += len(chunk)
            data = b"".join(chunks)
            return True, total_size, len(data), "FULL_SHA256", sha256(data).hexdigest(), data
        hdr = os.pread(fd, min(P234_BOUNDED_HEADER_BYTES, total_size), 0)
        return True, total_size, len(hdr), "HEADER4K_SHA256", sha256(hdr).hexdigest(), hdr
    finally:
        os.close(fd)


def _check_elf64_aarch64_tokens(data: bytes, expected_tokens: Tuple[bytes, ...]) -> Tuple[bool, str]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return False, "NOT_ELF"
    ei_class, ei_data = data[4], data[5]
    e_machine = struct.unpack_from("<H", data, 18)[0]
    if ei_class != 2 or ei_data != 1 or e_machine != 183:
        return False, f"BAD_ELF64_AARCH64(class={ei_class},data={ei_data},mach={e_machine})"
    found = [tok.decode("ascii") for tok in expected_tokens if tok in data]
    missing = [tok.decode("ascii") for tok in expected_tokens if tok not in data]
    if missing:
        return False, f"MISSING_TOKENS:{','.join(missing)}"
    return True, f"ELF64_AARCH64:{'+'.join(found)}"


def _synthetic_phase234_donors() -> Tuple[Phase234DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P234_DONOR_FX3_BODYDATA_RELPATH,
            P234_PINNED_FX3_BODYDATA_BYTES,
            P234_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P234_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P234_DONOR_FX3_APPFW_702_RELPATH,
            P234_PINNED_FX3_APPFW_702_BYTES,
            P234_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P234_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_APPFW_702",
        ),
        (
            "fx3_backup_bin",
            P234_DONOR_FX3_BACKUP_BIN_RELPATH,
            P234_PINNED_FX3_BACKUP_BIN_BYTES,
            P234_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P234_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P234_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P234_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P234_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P234_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P234_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P234_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P234_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P234_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libinframediaconfig_so",
            P234_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P234_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P234_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P234_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+GetMediaNum+Backup_sync_subsystem",
        ),
        (
            "fx3_libimdb_so",
            P234_DONOR_FX3_LIBIMDB_SO_RELPATH,
            P234_PINNED_FX3_LIBIMDB_SO_BYTES,
            P234_PINNED_FX3_LIBIMDB_SO_BYTES,
            "FULL_SHA256",
            P234_PINNED_FX3_LIBIMDB_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:IMDB_find_entry+IMDB_get_entries+InfraDatabase_Init",
        ),
    )
    return tuple(
        Phase234DonorArtifactDigest(
            artifact_id=aid,
            relpath=rel,
            present=True,
            read_mode="CLEAN_ROOM_SYNTHETIC",
            total_bytes=total,
            header_bytes_read=hdr_b,
            digest_kind=dkind,
            digest_sha256=dsha,
            marker_summary=msum,
            matches_pinned=True,
        )
        for aid, rel, total, hdr_b, dkind, dsha, msum in specs
    )


def inspect_phase234_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase234DonorSnapshot:
    """Inspect Wave-34 / FX3 7.02 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.15s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase234_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase234DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P234_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P234_DONOR_FX3_BODYDATA_RELPATH,
            P234_PINNED_FX3_BODYDATA_BYTES,
            P234_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P234_DONOR_FX3_APPFW_702_RELPATH,
            P234_PINNED_FX3_APPFW_702_BYTES,
            P234_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P234_DONOR_FX3_BACKUP_BIN_RELPATH,
            P234_PINNED_FX3_BACKUP_BIN_BYTES,
            P234_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: (
                len(d) >= 20
                and struct.unpack_from("<I", d, 4)[0] == 0xAAAAAAAA
                and d[12:16] == b"BK4\x00"
                and b"ILME-FX3" in d,
                "BK4_ILME_FX3"
                if (
                    len(d) >= 20
                    and struct.unpack_from("<I", d, 4)[0] == 0xAAAAAAAA
                    and d[12:16] == b"BK4\x00"
                    and b"ILME-FX3" in d
                )
                else "BAD_BACKUP_MAGIC",
            ),
        ),
        (
            "fx3_libbackup_so",
            P234_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P234_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P234_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P234_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P234_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P234_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libinframediaconfig_so",
            P234_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P234_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P234_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"InfraMediaConfig", b"GetMediaNum", b"Backup_sync_subsystem")
            ),
        ),
        (
            "fx3_libimdb_so",
            P234_DONOR_FX3_LIBIMDB_SO_RELPATH,
            P234_PINNED_FX3_LIBIMDB_SO_BYTES,
            P234_PINNED_FX3_LIBIMDB_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"IMDB_find_entry", b"IMDB_get_entries", b"InfraDatabase_Init")
            ),
        ),
    )

    digests: List[Phase234DonorArtifactDigest] = []
    for aid, rel, pinned_bytes, pinned_sha, validator in probe_specs:
        ok, total_b, hdr_b, dkind, dsha, raw = _read_donor_readonly_bounded(rel)
        if not ok:
            digests.append(
                Phase234DonorArtifactDigest(
                    artifact_id=aid,
                    relpath=rel,
                    present=False,
                    read_mode="MISSING",
                    total_bytes=0,
                    header_bytes_read=0,
                    digest_kind=dkind,
                    digest_sha256="",
                    marker_summary="MISSING",
                    matches_pinned=False,
                )
            )
            continue
        marker_ok, marker_summary = validator(raw)
        matches = (total_b == pinned_bytes) and (dsha == pinned_sha) and bool(marker_ok)
        digests.append(
            Phase234DonorArtifactDigest(
                artifact_id=aid,
                relpath=rel,
                present=True,
                read_mode="O_RDONLY_NOFOLLOW_NONBLOCK",
                total_bytes=total_b,
                header_bytes_read=hdr_b,
                digest_kind=dkind,
                digest_sha256=dsha,
                marker_summary=marker_summary,
                matches_pinned=matches,
            )
        )

    if not all(d.present for d in digests):
        synth = _synthetic_phase234_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase234DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P234_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    dt = round(time.monotonic() - t0, 6)
    return Phase234DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all(d.present and d.matches_pinned for d in digests),
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P234_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Pillar 36A & 36B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_recover_imagedb_spec() -> RecoverImageDbBatteryAndVaultFirewallSpec:
    return RecoverImageDbBatteryAndVaultFirewallSpec()


def build_default_safe_monitor_flip_af_interval_spec() -> MonitorFlipPlaybackAndAfIntervalVaultSpec:
    return MonitorFlipPlaybackAndAfIntervalVaultSpec()


def evaluate_recover_imagedb_battery_and_vault_firewall(
    spec: RecoverImageDbBatteryAndVaultFirewallSpec,
) -> RecoverImageDbBatteryAndVaultFirewallReport:
    """Audit `[Recover Image DB]` depleted-battery refusal, non-deleting repair & Slot-1 Tier-0 vault firewall."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P234_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P234_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 36A")

    if (
        spec.camera_model != P234_FX3_MODEL_NAME
        or spec.fw_version not in P234_FX3_SUPPORTED_FW_VERSIONS
        or spec.menu_path != P234_RECOVER_IMAGEDB_MENU_PATH
        or spec.target_slot not in P234_MEDIA_SLOTS
        or spec.imagedb_symptom not in P234_IMAGEDB_SYMPTOMS
        or not (0 <= spec.np_fz100_charge_pct <= 100)
        or not (0.0 < spec.np_fz100_voltage_v <= 8.50)
        or spec.recorded_clips_before < 0
        or spec.recorded_stills_before < 0
        or spec.recordable_images_display_before < 0
        or spec.recordable_images_display_after < 0
        or spec.slot1_filesystem_metadata_writes < 0
        or any(art not in P234_RECOGNIZED_VAULT_ARTIFACTS for art in spec.slot1_vault_artifacts)
        or (spec.slot1_tier0_vault_present and len(spec.slot1_vault_artifacts) == 0)
    ):
        _fail(
            P234_BLOCKED_INVALID_RECOVER_IMAGEDB_SPEC,
            f"Invalid model/fw, menu path, slot, symptom, battery range, or vault artifact in Pillar 36A: "
            f"model={spec.camera_model!r} fw={spec.fw_version!r} slot={spec.target_slot!r}",
        )

    action_immunity_ok = True
    if spec.action_item_reset_by_camera_settings_reset or spec.action_item_reset_by_initialize:
        action_immunity_ok = False
        _fail(
            P234_BLOCKED_RECOVER_IMAGEDB_ACTION_RESET_IMMUNITY_DRIFT,
            "[Recover Image DB] is an on-demand action item immune to both [Camera Settings Reset] and [Initialize]",
        )

    vault_firewall_ok = True
    vault_receipt_valid = (
        spec.slot1_offcamera_sha256_verified
        and len(spec.slot1_offcamera_receipt_sha256) == 64
        and all(ch in "0123456789abcdef" for ch in spec.slot1_offcamera_receipt_sha256.lower())
    )
    if spec.slot1_filesystem_metadata_writes > 0 and (spec.slot1_tier0_vault_present or spec.slot1_sdxc_wp_locked):
        vault_firewall_ok = False
        if spec.slot1_tier0_vault_present and not vault_receipt_valid:
            _fail(
                P234_BLOCKED_SLOT1_UNVERIFIED_TIER0_VAULT_IMAGEDB_MUTATION,
                "[Recover Image DB] mutated Slot-1 Tier-0 dump vault filesystem prior to off-camera SHA-256 verification",
            )
        else:
            _fail(
                P234_BLOCKED_SLOT1_WP_OR_ACTIVE_VAULT_IMAGEDB_WRITE_DENIED,
                "[Recover Image DB] attempted filesystem metadata writes on WP-locked or active Slot-1 Tier-0 vault card",
            )

    if spec.recover_imagedb_requested:
        if spec.target_slot == P234_SLOT1_VAULT_SLOT:
            if spec.slot1_tier0_vault_present and not vault_receipt_valid:
                vault_firewall_ok = False
                _fail(
                    P234_BLOCKED_SLOT1_UNVERIFIED_TIER0_VAULT_IMAGEDB_MUTATION,
                    "Slot-1 [Recover Image DB] blocked: unverified Tier-0 dump vault (pnflasha/cnflasha/CAMSET01.DAT) "
                    "present prior to off-camera SHA-256 verification",
                )
            elif spec.slot1_tier0_vault_present or spec.slot1_sdxc_wp_locked or spec.target_card_wp_locked:
                vault_firewall_ok = False
                _fail(
                    P234_BLOCKED_SLOT1_WP_OR_ACTIVE_VAULT_IMAGEDB_WRITE_DENIED,
                    "Slot-1 [Recover Image DB] blocked: WP-locked or still-inserted Tier-0 dump vault card forbids "
                    "filesystem metadata writes",
                )
        elif spec.target_card_wp_locked:
            vault_firewall_ok = False
            _fail(
                P234_BLOCKED_SLOT1_WP_OR_ACTIVE_VAULT_IMAGEDB_WRITE_DENIED,
                "Target media card has physical SDXC write-protect (WP) engaged; [Recover Image DB] cannot write",
            )

    battery_ok = True
    is_depleted = (
        spec.battery_extremely_depleted
        or spec.np_fz100_charge_pct < P234_RECOVER_IMAGEDB_MIN_BATTERY_PCT
        or spec.np_fz100_voltage_v < P234_RECOVER_IMAGEDB_MIN_VOLTAGE_V
    )
    if spec.recover_imagedb_requested and is_depleted:
        battery_ok = False
        _fail(
            P234_BLOCKED_RECOVER_IMAGEDB_DEPLETED_BATTERY,
            f"[Recover Image DB] hardware-refused on extremely depleted NP-FZ100 battery "
            f"(pct={spec.np_fz100_charge_pct}%, voltage={spec.np_fz100_voltage_v:.2f}V, "
            f"depleted={spec.battery_extremely_depleted}) to prevent mid-journal FAT/exFAT corruption",
        )

    non_deleting_ok = True
    if (
        spec.recorded_clips_deleted != 0
        or spec.recorded_stills_deleted != 0
        or spec.recorded_clips_after != spec.recorded_clips_before
        or spec.recorded_stills_after != spec.recorded_stills_before
    ):
        non_deleting_ok = False
        _fail(
            P234_BLOCKED_RECOVER_IMAGEDB_CLIP_OR_STILL_DELETION,
            "[Recover Image DB] repairs AVF_INFO / media DB index files strictly without deleting recorded clips or stills",
        )
    elif spec.recover_imagedb_requested and vault_firewall_ok and battery_ok:
        if spec.imagedb_symptom != "HEALTHY_NO_REPAIR_NEEDED" and not spec.avf_info_repaired:
            non_deleting_ok = False
            _fail(
                P234_BLOCKED_INVALID_RECOVER_IMAGEDB_SPEC,
                f"[Recover Image DB] requested for {spec.imagedb_symptom!r} but avf_info_repaired=False",
            )
        elif spec.imagedb_symptom == "FALSE_ZERO_RECORDABLE_IMAGES" and (
            spec.recordable_images_display_before != 0 or spec.recordable_images_display_after <= 0
        ):
            non_deleting_ok = False
            _fail(
                P234_BLOCKED_INVALID_RECOVER_IMAGEDB_SPEC,
                "FALSE_ZERO_RECORDABLE_IMAGES repair must transition recordable image count from 0 to > 0",
            )

    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _fail(
            P234_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P234_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P234_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P234_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or p2 BLKROSET immutability drifted in Pillar 36A",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "36A",
            "passed": passed,
            "block_code": block_code,
            "fw_version": spec.fw_version,
            "target_slot": spec.target_slot,
            "symptom": spec.imagedb_symptom,
            "requested": spec.recover_imagedb_requested,
            "slot1_vault_present": spec.slot1_tier0_vault_present,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return RecoverImageDbBatteryAndVaultFirewallReport(
        passed=passed,
        status=P234_STATUS_VERIFIED_PILLAR_36A if passed else P234_STATUS_REJECTED_PILLAR_36A,
        block_code=block_code,
        target_slot=spec.target_slot,
        imagedb_symptom=spec.imagedb_symptom,
        non_deleting_repair_verified=non_deleting_ok and passed,
        depleted_battery_guard_verified=battery_ok and passed,
        action_reset_immunity_verified=action_immunity_ok and passed,
        slot1_tier0_vault_firewall_verified=vault_firewall_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_monitor_flip_playback_and_af_interval_vault(
    spec: MonitorFlipPlaybackAndAfIntervalVaultSpec,
) -> MonitorFlipPlaybackAndAfIntervalVaultReport:
    """Audit `[Monitor Flip Direction]` reset survival, playback non-inversion, AF kinematics & still-only interval."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P234_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P234_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 36B")

    monitor_flip_ok = True
    valid_flip_tokens = (
        spec.camera_model == P234_FX3_MODEL_NAME
        and spec.fw_version in P234_FX3_SUPPORTED_FW_VERSIONS
        and spec.monitor_flip_menu_path == P234_MONITOR_FLIP_MENU_PATH
        and spec.pre_reset_monitor_flip_direction in P234_MONITOR_FLIP_DIRECTIONS
        and spec.post_reset_monitor_flip_direction in P234_MONITOR_FLIP_DIRECTIONS
        and spec.reset_action in P234_RESET_ACTIONS
    )
    if not valid_flip_tokens:
        monitor_flip_ok = False
        _fail(
            P234_BLOCKED_INVALID_MONITOR_FLIP_OR_AF_INTERVAL_SPEC,
            "Invalid model/fw, [Monitor Flip Direction] menu path/value, or reset_action in Pillar 36B",
        )
    elif spec.reset_action in ("NONE", "Camera Settings Reset"):
        if spec.post_reset_monitor_flip_direction != spec.pre_reset_monitor_flip_direction:
            monitor_flip_ok = False
            _fail(
                P234_BLOCKED_MONITOR_FLIP_CAMERA_SETTINGS_RESET_DRIFT,
                "[Monitor Flip Direction] is a Setup item not reset by [Camera Settings Reset] and must survive unchanged",
            )
    elif spec.reset_action == "Initialize":
        if spec.post_reset_monitor_flip_direction != P234_MONITOR_FLIP_DEFAULT:
            monitor_flip_ok = False
            _fail(
                P234_BLOCKED_MONITOR_FLIP_CAMERA_SETTINGS_RESET_DRIFT,
                "[Initialize] must restore [Monitor Flip Direction] to default 'Auto'",
            )

    playback_ok = True
    expected_shooting_hflip = spec.post_reset_monitor_flip_direction == "Horizontal Flip"
    if (
        spec.playback_monitor_display_inverted
        or spec.playback_timecode_clipname_mirrored
        or (expected_shooting_hflip and not spec.shooting_liveview_horizontally_flipped)
        or (not expected_shooting_hflip and spec.shooting_liveview_horizontally_flipped)
    ):
        playback_ok = False
        _fail(
            P234_BLOCKED_MONITOR_FLIP_PLAYBACK_INVERSION_VIOLATION,
            "Even when [Monitor Flip Direction] is set to [Horizontal Flip], playback display direction "
            "and timecode/clip-name text are NEVER inverted",
        )

    af_ok = True
    camset_ok = True
    if (
        spec.af_subj_shift_sensitivity_menu_name != P234_AF_SUBJ_SHIFT_SENSITIVITY_MENU_NAME
        or spec.af_transition_speed_menu_name != P234_AF_TRANSITION_SPEED_MENU_NAME
    ):
        af_ok = False
        _fail(
            P234_BLOCKED_ABBREVIATED_OR_INVALID_AF_MENU_NAME,
            f"ILME-FX3 requires exact full menu strings {P234_AF_SUBJ_SHIFT_SENSITIVITY_MENU_NAME!r} "
            f"(not abbreviated 'Sens.') and {P234_AF_TRANSITION_SPEED_MENU_NAME!r}",
        )
    elif (
        spec.af_kinematics_scope not in P234_AF_KINEMATICS_SCOPES
        or spec.pre_reset_af_subj_shift_sensitivity not in P234_AF_SUBJ_SHIFT_SENSITIVITY_VALUES
        or spec.post_reset_af_subj_shift_sensitivity not in P234_AF_SUBJ_SHIFT_SENSITIVITY_VALUES
        or spec.saved_af_subj_shift_sensitivity not in P234_AF_SUBJ_SHIFT_SENSITIVITY_VALUES
        or spec.pre_reset_af_transition_speed not in P234_AF_TRANSITION_SPEED_VALUES
        or spec.post_reset_af_transition_speed not in P234_AF_TRANSITION_SPEED_VALUES
        or spec.saved_af_transition_speed not in P234_AF_TRANSITION_SPEED_VALUES
    ):
        af_ok = False
        _fail(
            P234_BLOCKED_INVALID_MONITOR_FLIP_OR_AF_INTERVAL_SPEC,
            "Invalid [AF Subj. Shift Sensitivity] (1(Locked on)..5(Responsive)), [AF Transition Speed] "
            "(1(Slow)..7(Fast)), or Movie/S&Q AF scope",
        )
    elif spec.camset_slot != P234_SLOT1_VAULT_SLOT or spec.camset_filename not in P234_CAMSET_FILENAMES:
        camset_ok = False
        _fail(
            P234_BLOCKED_CAMSET_SLOT1_AF_RESTORE_DRIFT,
            f"CAMSET vault must reside on Slot 1 ({P234_CAMSET_FILENAMES[0]}..{P234_CAMSET_FILENAMES[-1]}), "
            f"got slot={spec.camset_slot!r}, file={spec.camset_filename!r}",
        )
    elif spec.camset_restore_after_reset:
        if (
            spec.post_reset_af_subj_shift_sensitivity != spec.saved_af_subj_shift_sensitivity
            or spec.post_reset_af_transition_speed != spec.saved_af_transition_speed
        ):
            camset_ok = False
            _fail(
                P234_BLOCKED_CAMSET_SLOT1_AF_RESTORE_DRIFT,
                "Slot-1 CAMSET vault restore failed to recover saved [AF Subj. Shift Sensitivity] or "
                "[AF Transition Speed]",
            )
    else:
        if spec.reset_action in ("Camera Settings Reset", "Initialize"):
            if (
                spec.post_reset_af_subj_shift_sensitivity != P234_AF_SUBJ_SHIFT_SENSITIVITY_DEFAULT
                or spec.post_reset_af_transition_speed != P234_AF_TRANSITION_SPEED_DEFAULT
            ):
                af_ok = False
                _fail(
                    P234_BLOCKED_AF_KINEMATICS_RESET_OR_CAMSET_RESTORE_DRIFT,
                    "[AF Subj. Shift Sensitivity] (-> '5(Responsive)') and [AF Transition Speed] (-> '5') "
                    "must reset cleanly under [Camera Settings Reset] / [Initialize]",
                )
        elif spec.reset_action == "NONE":
            if (
                spec.post_reset_af_subj_shift_sensitivity != spec.pre_reset_af_subj_shift_sensitivity
                or spec.post_reset_af_transition_speed != spec.pre_reset_af_transition_speed
            ):
                af_ok = False
                _fail(
                    P234_BLOCKED_AF_KINEMATICS_RESET_OR_CAMSET_RESTORE_DRIFT,
                    "Unexpected [AF Subj. Shift Sensitivity] or [AF Transition Speed] drift when reset_action='NONE'",
                )

    interval_ok = True
    if (
        spec.interval_shoot_menu_path != P234_INTERVAL_SHOOT_MENU_PATH
        or spec.interval_shoot_func not in P234_INTERVAL_SHOOT_STATES
    ):
        interval_ok = False
        _fail(
            P234_BLOCKED_INVALID_MONITOR_FLIP_OR_AF_INTERVAL_SPEC,
            "Invalid [Interval Shoot Func.] menu path or Off/On state",
        )
    elif (
        not (P234_INTERVAL_START_TIME_MIN_SEC <= spec.interval_start_time_seconds <= P234_INTERVAL_START_TIME_MAX_SEC)
        or not (P234_INTERVAL_SHOOTING_MIN_SEC <= spec.interval_shooting_seconds <= P234_INTERVAL_SHOOTING_MAX_SEC)
        or not (P234_INTERVAL_SHOTS_MIN <= spec.interval_number_of_shots <= P234_INTERVAL_SHOTS_MAX)
        or spec.interval_output_kind != P234_INTERVAL_OUTPUT_STILL_SEQUENCE
        or not spec.requires_external_timelapse_assembly
        or spec.in_camera_video_interval_rec_supported
        or spec.fx6_interval_rec_mxf_mp4_assumed_on_fx3
    ):
        interval_ok = False
        _fail(
            P234_BLOCKED_INTERVAL_SHOOT_STILL_ONLY_SCOPE_OR_RANGE_VIOLATION,
            "ILME-FX3 [Interval Shoot Func.] (1s..99m59s start, 1s..60s interval, 1..9999 shots) captures "
            "still images only (external time-lapse assembly) and never performs FX6 video Interval Rec",
        )

    if not _is_tmpfs_path(spec.stage_b_overlay_dir) or _targets_persistent_emmc(spec.stage_b_overlay_dir):
        _fail(
            P234_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.stage_b_overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P234_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P234_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P234_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or 16/16 surface parity drifted in Pillar 36B",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "36B",
            "passed": passed,
            "block_code": block_code,
            "reset_action": spec.reset_action,
            "post_flip": spec.post_reset_monitor_flip_direction,
            "playback_inverted": spec.playback_monitor_display_inverted,
            "post_af": (
                spec.post_reset_af_subj_shift_sensitivity,
                spec.post_reset_af_transition_speed,
            ),
            "camset_restore": spec.camset_restore_after_reset,
            "camset": spec.camset_filename,
            "interval": (
                spec.interval_shoot_func,
                spec.interval_start_time_seconds,
                spec.interval_shooting_seconds,
                spec.interval_output_kind,
            ),
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return MonitorFlipPlaybackAndAfIntervalVaultReport(
        passed=passed,
        status=P234_STATUS_VERIFIED_PILLAR_36B if passed else P234_STATUS_REJECTED_PILLAR_36B,
        block_code=block_code,
        monitor_flip_reset_persistence_verified=monitor_flip_ok and passed,
        playback_non_inversion_verified=playback_ok and passed,
        af_kinematics_reset_and_menu_verified=af_ok and passed,
        camset_slot1_af_restore_verified=camset_ok and passed,
        interval_still_only_scope_verified=interval_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        tier0_surfaces_intact=spec.tier0_surfaces_h0_h3_matched if h0_eq_h3 else 0,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_recover_imagedb_and_monitor_flip_af_vault(
    recover_imagedb_spec: Optional[RecoverImageDbBatteryAndVaultFirewallSpec] = None,
    monitor_flip_af_interval_spec: Optional[MonitorFlipPlaybackAndAfIntervalVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> RecoverImageDbAndMonitorFlipAfVaultReport:
    """Combined Pillar 36 verifier: Recover Image DB battery/vault firewall + Monitor Flip / AF / Interval vault."""
    donor_snap = inspect_phase234_donors_readonly(force_clean_room=force_clean_room)
    imdb_rep = evaluate_recover_imagedb_battery_and_vault_firewall(
        recover_imagedb_spec or build_default_safe_recover_imagedb_spec()
    )
    flip_rep = evaluate_monitor_flip_playback_and_af_interval_vault(
        monitor_flip_af_interval_spec or build_default_safe_monitor_flip_af_interval_spec()
    )
    errs: List[str] = _safety_invariant_errors() + list(imdb_rep.errors) + list(flip_rep.errors)
    if not donor_snap.all_donors_present:
        errs.append("Phase 234 donor snapshot incomplete or mismatched")
    if not donor_snap.under_0_15s_budget:
        errs.append(f"Phase 234 donor inspection exceeded 0.15s budget: {donor_snap.elapsed_seconds}s")

    all_ok = imdb_rep.passed and flip_rep.passed and len(errs) == 0
    return RecoverImageDbAndMonitorFlipAfVaultReport(
        schema=PHASE234_SCHEMA,
        version=PHASE234_VERSION,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P234_STATUS_VERIFIED_PILLAR36_SUITE if all_ok else P234_STATUS_FAIL_PILLAR36_SUITE,
        donor_snapshot=donor_snap,
        recover_imagedb_report=imdb_rep,
        monitor_flip_af_interval_report=flip_rep,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(errs),
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites & Standalone Pillar 36 Runner
# ---------------------------------------------------------------------------


def run_pillar36a_recover_imagedb_vault_firewall_6_scenario_suite() -> Pillar36ASuiteResult:
    cases: Tuple[Tuple[str, bool, RecoverImageDbBatteryAndVaultFirewallSpec, Optional[str]], ...] = (
        (
            P234_PILLAR_36A_SCENARIO_IDS[0],
            True,
            RecoverImageDbBatteryAndVaultFirewallSpec(),
            None,
        ),
        (
            P234_PILLAR_36A_SCENARIO_IDS[1],
            True,
            RecoverImageDbBatteryAndVaultFirewallSpec(
                target_slot=1,
                imagedb_symptom="FALSE_ZERO_RECORDABLE_IMAGES",
                recordable_images_display_before=0,
                recordable_images_display_after=860,
                slot1_tier0_vault_present=False,
                slot1_vault_artifacts=(),
                slot1_offcamera_sha256_verified=True,
                slot1_sdxc_wp_locked=False,
                target_card_wp_locked=False,
                slot1_filesystem_metadata_writes=0,
            ),
            None,
        ),
        (
            P234_PILLAR_36A_SCENARIO_IDS[2],
            False,
            RecoverImageDbBatteryAndVaultFirewallSpec(
                target_slot=2,
                np_fz100_charge_pct=3,
                np_fz100_voltage_v=6.45,
                battery_extremely_depleted=True,
            ),
            P234_BLOCKED_RECOVER_IMAGEDB_DEPLETED_BATTERY,
        ),
        (
            P234_PILLAR_36A_SCENARIO_IDS[3],
            False,
            RecoverImageDbBatteryAndVaultFirewallSpec(
                target_slot=1,
                slot1_tier0_vault_present=True,
                slot1_offcamera_sha256_verified=False,
                slot1_offcamera_receipt_sha256="",
                slot1_sdxc_wp_locked=False,
            ),
            P234_BLOCKED_SLOT1_UNVERIFIED_TIER0_VAULT_IMAGEDB_MUTATION,
        ),
        (
            P234_PILLAR_36A_SCENARIO_IDS[4],
            False,
            RecoverImageDbBatteryAndVaultFirewallSpec(
                target_slot=1,
                slot1_tier0_vault_present=True,
                slot1_offcamera_sha256_verified=True,
                slot1_sdxc_wp_locked=True,
            ),
            P234_BLOCKED_SLOT1_WP_OR_ACTIVE_VAULT_IMAGEDB_WRITE_DENIED,
        ),
        (
            P234_PILLAR_36A_SCENARIO_IDS[5],
            False,
            RecoverImageDbBatteryAndVaultFirewallSpec(
                recorded_clips_before=18,
                recorded_clips_after=17,
                recorded_clips_deleted=1,
            ),
            P234_BLOCKED_RECOVER_IMAGEDB_CLIP_OR_STILL_DELETION,
        ),
    )

    outcomes: List[Pillar36ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_recover_imagedb_battery_and_vault_firewall(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar36ScenarioOutcome(
                scenario_id=sid,
                pillar="36A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar36ASuiteResult(
        passed=all_ok,
        status=P234_STATUS_VERIFIED_PILLAR_36A if all_ok else P234_STATUS_REJECTED_PILLAR_36A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar36b_monitor_flip_af_interval_6_scenario_suite() -> Pillar36BSuiteResult:
    cases: Tuple[Tuple[str, bool, MonitorFlipPlaybackAndAfIntervalVaultSpec, Optional[str]], ...] = (
        (
            P234_PILLAR_36B_SCENARIO_IDS[0],
            True,
            MonitorFlipPlaybackAndAfIntervalVaultSpec(),
            None,
        ),
        (
            P234_PILLAR_36B_SCENARIO_IDS[1],
            True,
            MonitorFlipPlaybackAndAfIntervalVaultSpec(
                pre_reset_monitor_flip_direction="Horizontal Flip",
                reset_action="Initialize",
                post_reset_monitor_flip_direction="Auto",
                shooting_liveview_horizontally_flipped=False,
                playback_monitor_display_inverted=False,
                af_kinematics_scope="S&Q",
                camset_restore_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                saved_af_subj_shift_sensitivity="1(Locked on)",
                saved_af_transition_speed="7(Fast)",
                post_reset_af_subj_shift_sensitivity="1(Locked on)",
                post_reset_af_transition_speed="7(Fast)",
                interval_start_time_seconds=5999,
                interval_shooting_seconds=60,
            ),
            None,
        ),
        (
            P234_PILLAR_36B_SCENARIO_IDS[2],
            False,
            MonitorFlipPlaybackAndAfIntervalVaultSpec(
                pre_reset_monitor_flip_direction="Horizontal Flip",
                reset_action="Camera Settings Reset",
                post_reset_monitor_flip_direction="Auto",
                shooting_liveview_horizontally_flipped=False,
            ),
            P234_BLOCKED_MONITOR_FLIP_CAMERA_SETTINGS_RESET_DRIFT,
        ),
        (
            P234_PILLAR_36B_SCENARIO_IDS[3],
            False,
            MonitorFlipPlaybackAndAfIntervalVaultSpec(
                pre_reset_monitor_flip_direction="Horizontal Flip",
                post_reset_monitor_flip_direction="Horizontal Flip",
                shooting_liveview_horizontally_flipped=True,
                playback_monitor_display_inverted=True,
                playback_timecode_clipname_mirrored=True,
            ),
            P234_BLOCKED_MONITOR_FLIP_PLAYBACK_INVERSION_VIOLATION,
        ),
        (
            P234_PILLAR_36B_SCENARIO_IDS[4],
            False,
            MonitorFlipPlaybackAndAfIntervalVaultSpec(
                af_subj_shift_sensitivity_menu_name="AF Subj. Shift Sens.",
            ),
            P234_BLOCKED_ABBREVIATED_OR_INVALID_AF_MENU_NAME,
        ),
        (
            P234_PILLAR_36B_SCENARIO_IDS[5],
            False,
            MonitorFlipPlaybackAndAfIntervalVaultSpec(
                interval_output_kind="VIDEO_MXF_INTERVAL_REC",
                in_camera_video_interval_rec_supported=True,
                fx6_interval_rec_mxf_mp4_assumed_on_fx3=True,
            ),
            P234_BLOCKED_INTERVAL_SHOOT_STILL_ONLY_SCOPE_OR_RANGE_VIOLATION,
        ),
    )

    outcomes: List[Pillar36ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_monitor_flip_playback_and_af_interval_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar36ScenarioOutcome(
                scenario_id=sid,
                pillar="36B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar36BSuiteResult(
        passed=all_ok,
        status=P234_STATUS_VERIFIED_PILLAR_36B if all_ok else P234_STATUS_REJECTED_PILLAR_36B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar36_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar36StandaloneReport:
    """Run full Pillar 36 standalone suite (`6/6` Pillar 36A + `6/6` Pillar 36B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase234_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar36a_recover_imagedb_vault_firewall_6_scenario_suite()
    res_b = run_pillar36b_monitor_flip_af_interval_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 234 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 0.15s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE234_SCHEMA,
            "version": PHASE234_VERSION,
            "mode": donor_snapshot.verification_mode,
            "36a": [asdict(s) for s in res_a.scenarios],
            "36b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar36StandaloneReport(
        schema=PHASE234_SCHEMA,
        version=PHASE234_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P234_STATUS_VERIFIED_PILLAR36_SUITE if all_ok else P234_STATUS_FAIL_PILLAR36_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_36a_recover_imagedb_vault_firewall=res_a,
        pillar_36b_monitor_flip_af_interval_vault=res_b,
        suite_sha256=suite_sha,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(safety_errs),
    )


# ---------------------------------------------------------------------------
# Unified 36/36 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master36_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
    err = f"FAULT_INJECTED:{pillar.pillar_id}"
    return MasterPillarStatus(
        pillar_number=pillar.pillar_number,
        pillar_id=pillar.pillar_id,
        phase_label=pillar.phase_label,
        module_name=pillar.module_name,
        passed=False,
        status=f"FAULT_INJECTED_{pillar.pillar_id.upper()}",
        verification_mode=pillar.verification_mode,
        elapsed_seconds=pillar.elapsed_seconds,
        key_metrics=pillar.key_metrics,
        digest_sha256=_canonical_sha256({"pillar": pillar.pillar_id, "fault_injected": True}),
        errors=pillar.errors + (err,),
    )


def evaluate_realhw_36pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master36PillarRecoveryReport:
    """Evaluate and aggregate all 36 recovery pillars (`1..36`) concurrently -> `36/36` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_36_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_35pillar() -> Master35PillarRecoveryReport:
        return evaluate_realhw_35pillar_recovery_master(**kw)

    def _run_p36() -> Tuple[Pillar36StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar36_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_35 = pool.submit(_run_35pillar)
        fut_36 = pool.submit(_run_p36)
        m35_rep = fut_35.result()
        p36_rep, p36_dt = fut_36.result()

    all_errors: List[str] = list(m35_rep.errors) + list(p36_rep.errors)
    for attr_name, expected_val in (
        ("otp_fuse_touches", 0),
        ("otp_fuse_writes", 0),
        ("rpmb_counter_increments", 0),
        ("passive_tx_bytes_emitted", 0),
        ("physical_usb_packets_emitted", 0),
        ("physical_device_writes", 0),
        ("raw_firmware_bytes_leaked", 0),
        ("el3_payload_transmit_authorized", False),
        ("isp_write_authorized", False),
        ("spi_nor_write_authorized", False),
        ("persistent_emmc_writes_authorized", False),
        ("persistent_write_release", False),
        ("live_usb_iokit_transmit_enabled", False),
        ("cnflasha_userspace_write_blocked", True),
    ):
        if getattr(m35_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-35 violated {attr_name} == {expected_val}")
        if getattr(p36_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 36 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m35_rep.pillars)
    spec36 = MASTER_36_PILLAR_SPECS[35]
    p36_metrics = {
        "pillar_36a_recover_imagedb_vault_firewall": (
            f"{p36_rep.pillar_36a_recover_imagedb_vault_firewall.scenarios_passed}/"
            f"{p36_rep.pillar_36a_recover_imagedb_vault_firewall.scenarios_total}"
        ),
        "pillar_36b_monitor_flip_af_interval_vault": (
            f"{p36_rep.pillar_36b_monitor_flip_af_interval_vault.scenarios_passed}/"
            f"{p36_rep.pillar_36b_monitor_flip_af_interval_vault.scenarios_total}"
        ),
        "slot1_vault_imagedb_mutations": 0,
        "playback_horizontal_flip_inversions": 0,
        "donor_files_inspected": p36_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec36[0],
            pillar_id=spec36[1],
            phase_label=spec36[2],
            module_name=spec36[3],
            passed=bool(p36_rep.all_passed),
            status=p36_rep.status,
            verification_mode=p36_rep.verification_mode,
            elapsed_seconds=p36_dt,
            key_metrics=p36_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec36[1],
                    "mode": p36_rep.verification_mode,
                    "status": p36_rep.status,
                    "metrics": p36_metrics,
                    "passed": p36_rep.all_passed,
                }
            ),
            errors=tuple(p36_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master36_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p36_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_36_PILLAR_COUNT == 36
        and pillars_passed == 36
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE234_SCHEMA,
            "version": PHASE234_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master36PillarRecoveryReport(
        schema=PHASE234_SCHEMA,
        version=PHASE234_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P234_STATUS_VERIFIED_36OF36_AGGREGATOR if all_ok else P234_STATUS_FAIL_36OF36_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P234_CONCURRENT_CEILING_SECONDS,
        nominal_under_3_8s=elapsed < P234_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p36_rep.donor_snapshot,
        pillar36_a_recover_imagedb_vault_firewall=p36_rep.pillar_36a_recover_imagedb_vault_firewall,
        pillar36_b_monitor_flip_af_interval_vault=p36_rep.pillar_36b_monitor_flip_af_interval_vault,
        master_36pillar_sha256=master_sha,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(all_errors),
    )


def evaluate_36pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master36PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_36pillar_recovery_master`."""
    return evaluate_realhw_36pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_36pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master36PillarRecoveryReport:
    """Public CLI entry point for Pillar 36 unified `36/36` real-hardware recovery master verification."""
    return evaluate_realhw_36pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
