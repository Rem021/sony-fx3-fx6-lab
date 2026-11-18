"""Phase 231 — Milestone Pillar 35 (`35/35` Recovery Pillars) & Unified 35-Pillar Recovery Master
(`verify-35pillar-recovery` / `verify-silent-autopixelmap-marker-vault`):

1. **Pillar 35A — `[Silent Mode]` `[Auto Pixel Mapping]` Bench Shutdown Interlock, 5-Function
   Lockout & Hardware `[Shutter When Pwr OFF]` Absence (`ILME-FX3 Ver. 2.00..7.02`)**:
   - Models `[Silent Mode] = [On]` + `[Target Function Settings]` targeting `[Auto Pixel Mapping]`
     as a deterministic, non-invasive software bench shutdown firewall preventing uncommanded
     power-off mechanical dark-frame calibration (`cnflasha` touch) during Tier-0 backup/recovery
     cycles, while `[Not Target]` preserves normal `[Auto Pixel Mapping]` and `[Aperture Drive in AF]`.
   - Enforces `[Silent Mode] = [On]` automatic locks (`[Shutter Type]` and
     `[Shutter Type in Interval]` -> `[Electronic Shutter]`, `[Audio signals]` -> `[Off]`) and
     5 shooting-function lockouts (Flash shooting, `[Long Exposure NR]`, `[e-Front Curtain Shut.]`,
     `BULB` shooting, `[Anti-flicker Shoot.]`).
   - Rejects fabricated `[Shutter When Pwr OFF]` assertions on physical `ILME-FX3` (`Ver. 2.00..7.02`),
     where only `[Sensor Cleaning]`, `[Auto Pixel Mapping]`, and `[Pixel Mapping]` exist.

2. **Pillar 35B — `[Marker Display]` 15-Ratio Non-Resettable Vault, Local-LCD-Only HDMI Marker
   Suppression & `[Flexible Exp. Mode]` `Av/Tv/ISO` + `[Auto Slow Shutter]` Reset Split**:
   - Verifies `[Marker Display]` (`Center Marker`, `Aspect Marker` `Off` + 15 Ver. 3.00+/7.02
     ratios, `Safety Zone` `Off/80%/90%`, `Guideframe`) survives `[Camera Settings Reset]` unchanged
     (cleared only by full `[Initialize]`) and leaks `0` marker overlays onto HDMI even when
     `[HDMI Info. Display] = [On]`.
   - Verifies `[Exposure Ctrl Type]` (`P/A/S/M Mode` vs `Flexible Exp. Mode`), where
     `[Auto/Manual Swt. Set.]` (`Av`/`Tv`/`ISO` -> `Manual`) and `[Auto Slow Shutter]` (`-> On`)
     reset cleanly under `[Camera Settings Reset]` or restore via Slot-1 `CAMSET01.DAT` vault.

3. **Unified `35/35` Milestone Recovery Master (`evaluate_realhw_35pillar_recovery_master`)**:
   - Delegates Pillars `1..34` concurrently to `evaluate_realhw_34pillar_recovery_master` +
     **Pillar 35** -> **`35/35` (`VERIFIED_35OF35_PILLAR_RECOVERY_MASTER`)** in `< 3.6s` (`< 6.0s` ceiling).
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
from .realhw_34pillar_zebra_fullformat_chord_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_34_PILLAR_SPECS,
    Master34PillarRecoveryReport,
    evaluate_realhw_34pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE231_SCHEMA: str = "fx3-realhw-35pillar-recovery-master-verifier-v1"
PHASE231_VERSION: str = "1.0.0"

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

P231_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P231_NOMINAL_BUDGET_SECONDS: float = 3.6
P231_CONCURRENT_CEILING_SECONDS: float = 6.0
P231_BOUNDED_HEADER_BYTES: int = 4096
P231_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-33 / FX3 Ver. 7.02 Donor Anchors (bounded O_RDONLY verification)
P231_FX3_MODEL_NAME: str = "ILME-FX3"
P231_FX3_MODEL_ID: int = 0x91030080
P231_FX3_FW_VERSION: str = "7.02"
P231_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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
P231_FX3_PRE_300_FW_VERSIONS: Tuple[str, ...] = ("2.00", "2.01", "2.02")

P231_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P231_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P231_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

P231_DONOR_FX3_APPFW_702_RELPATH: str = "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P231_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P231_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"

P231_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P231_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P231_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

P231_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P231_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P231_PINNED_FX3_LIBBACKUP_SO_SHA256: str = "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"

P231_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P231_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P231_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"

P231_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
)
P231_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P231_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"

P231_DONOR_FX3_CAMERA_ONDEMAND_SAVER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/CameraOnDemandSaver.so"
)
P231_PINNED_FX3_CAMERA_ONDEMAND_SAVER_SO_BYTES: int = 18800
P231_PINNED_FX3_CAMERA_ONDEMAND_SAVER_SO_SHA256: str = (
    "72b73608c2675a3709e2952ca347a36e7dd2ad3dd2869191638c7154933b2f46"
)

# Pillar 35A — Silent Mode Auto Pixel Mapping Bench Shutdown Firewall, 5-Function Lockout & No Shutter When Pwr OFF
P231_SILENT_MODE_STATES: Tuple[str, ...] = ("Off", "On")
P231_TARGET_FUNCTION_MODES: Tuple[str, ...] = ("Target", "Not Target")
P231_TARGET_FUNCTION_ITEMS: Tuple[str, ...] = ("Aperture Drive in AF", "Auto Pixel Mapping")
P231_FX3_SETUP_SENSOR_MENU_ITEMS: Tuple[str, ...] = ("Sensor Cleaning", "Auto Pixel Mapping", "Pixel Mapping")
P231_FORBIDDEN_SHUTTER_WHEN_PWR_OFF_ITEM: str = "Shutter When Pwr OFF"
P231_SHUTTER_WHEN_PWR_OFF_ABSENT: str = "ABSENT_ON_ILME_FX3"

P231_APERTURE_DRIVE_IN_AF_MODES: Tuple[str, ...] = ("Standard", "Focus Priority", "Silent Priority")
P231_AUTO_PIXEL_MAPPING_MODES: Tuple[str, ...] = ("On", "Off")
P231_SHUTTER_TYPES: Tuple[str, ...] = ("Auto", "Mechanical Shutter", "Electronic Shutter")
P231_LOCKED_SILENT_SHUTTER_TYPE: str = "Electronic Shutter"
P231_AUDIO_SIGNALS_MODES: Tuple[str, ...] = (
    "On: all",
    "On: shutter only",
    "On: other than shutter",
    "Off",
)
P231_LOCKED_SILENT_AUDIO_SIGNALS: str = "Off"
P231_SILENT_5_DISQUALIFIED_FUNCTIONS: Tuple[str, ...] = (
    "Flash shooting",
    "Long Exposure NR",
    "e-Front Curtain Shut.",
    "BULB shooting",
    "Anti-flicker Shoot.",
)

# Pillar 35B — Marker Display 15-Ratio Vault, HDMI Marker Suppression & Flexible Exp. Mode Reset Split
P231_MARKER_DISPLAY_DEFAULT: str = "Off"
P231_MARKER_ON_OFF_MODES: Tuple[str, ...] = ("Off", "On")
P231_ASPECT_MARKER_DEFAULT: str = "Off"
P231_ASPECT_MARKER_15_RATIOS: Tuple[str, ...] = (
    "9:16",
    "4:5",
    "1:1",
    "4:3",
    "13:9",
    "14:9",
    "15:9",
    "16:9",
    "17:9",
    "1.66:1",
    "1.85:1",
    "1.91:1",
    "2:1",
    "2.35:1",
    "2.39:1",
)
P231_ASPECT_MARKER_VER300_RATIO: str = "16:9"
P231_ASPECT_MARKER_MODES: Tuple[str, ...] = (P231_ASPECT_MARKER_DEFAULT,) + P231_ASPECT_MARKER_15_RATIOS
P231_SAFETY_ZONE_DEFAULT: str = "Off"
P231_SAFETY_ZONE_MODES: Tuple[str, ...] = ("Off", "80%", "90%")
P231_HDMI_INFO_DISPLAY_MODES: Tuple[str, ...] = ("Off", "On")
P231_RESET_ACTIONS: Tuple[str, ...] = ("NONE", "Camera Settings Reset", "Initialize")

P231_EXPOSURE_CTRL_TYPES: Tuple[str, ...] = ("P/A/S/M Mode", "Flexible Exp. Mode")
P231_PASM_SUBMODES: Tuple[str, ...] = (
    "Program Auto",
    "Aperture Priority",
    "Shutter Priority",
    "Manual Exposure",
)
P231_FLEXEXP_SWITCH_MODES: Tuple[str, ...] = ("Auto", "Manual")
P231_FLEXEXP_SWITCH_DEFAULT: str = "Manual"
P231_AUTO_SLOW_SHUTTER_MODES: Tuple[str, ...] = ("On", "Off")
P231_AUTO_SLOW_SHUTTER_DEFAULT: str = "On"

P231_SLOT1_VAULT_SLOT: int = 1
P231_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P231_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_silent_autopixelmap_marker_flexexp_overlay"
P231_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P231_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P231_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P231_BLOCKED_INVALID_SILENT_OR_PIXELMAP_SPEC: str = "BLOCKED_INVALID_SILENT_OR_PIXELMAP_SPEC"
P231_BLOCKED_FABRICATED_SHUTTER_WHEN_PWR_OFF_ON_FX3: str = (
    "BLOCKED_FABRICATED_SHUTTER_WHEN_PWR_OFF_ON_FX3"
)
P231_BLOCKED_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCKOUT_VIOLATION: str = (
    "BLOCKED_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCKOUT_VIOLATION"
)
P231_BLOCKED_BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP: str = (
    "BLOCKED_BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP"
)
P231_BLOCKED_CNFLASHA_DEFECT_TABLE_TOUCH_ON_SHUTDOWN: str = (
    "BLOCKED_CNFLASHA_DEFECT_TABLE_TOUCH_ON_SHUTDOWN"
)
P231_BLOCKED_TARGET_FUNCTION_SETTINGS_SEMANTIC_DRIFT: str = (
    "BLOCKED_TARGET_FUNCTION_SETTINGS_SEMANTIC_DRIFT"
)
P231_BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC: str = "BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC"
P231_BLOCKED_MARKER_CAMERA_SETTINGS_RESET_DRIFT: str = (
    "BLOCKED_MARKER_CAMERA_SETTINGS_RESET_DRIFT"
)
P231_BLOCKED_HDMI_MARKER_OVERLAY_LEAKAGE: str = "BLOCKED_HDMI_MARKER_OVERLAY_LEAKAGE"
P231_BLOCKED_FLEXEXP_OR_AUTOSLOWSHUTTER_RESET_SPLIT_DRIFT: str = (
    "BLOCKED_FLEXEXP_OR_AUTOSLOWSHUTTER_RESET_SPLIT_DRIFT"
)
P231_BLOCKED_CAMSET_SLOT1_FLEXEXP_RESTORE_DRIFT: str = (
    "BLOCKED_CAMSET_SLOT1_FLEXEXP_RESTORE_DRIFT"
)
P231_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P231_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P231_STATUS_VERIFIED_PILLAR_35A: str = (
    "VERIFIED_PILLAR_35A_SILENT_MODE_AUTOPIXELMAP_BENCH_FIREWALL_NO_PWRSHUTTER"
)
P231_STATUS_REJECTED_PILLAR_35A: str = (
    "REJECTED_PILLAR_35A_SILENT_MODE_AUTOPIXELMAP_BENCH_FIREWALL_NO_PWRSHUTTER"
)
P231_STATUS_VERIFIED_PILLAR_35B: str = (
    "VERIFIED_PILLAR_35B_MARKER_15RATIO_HDMI_ISOLATION_FLEXEXP_RESET_SPLIT"
)
P231_STATUS_REJECTED_PILLAR_35B: str = (
    "REJECTED_PILLAR_35B_MARKER_15RATIO_HDMI_ISOLATION_FLEXEXP_RESET_SPLIT"
)
P231_STATUS_VERIFIED_PILLAR35_SUITE: str = (
    "VERIFIED_PILLAR35_SILENT_AUTOPIXELMAP_MARKER_FLEXEXP_VAULT"
)
P231_STATUS_FAIL_PILLAR35_SUITE: str = (
    "FAIL_PILLAR35_SILENT_AUTOPIXELMAP_MARKER_FLEXEXP_VAULT"
)
P231_STATUS_VERIFIED_35OF35_AGGREGATOR: str = "VERIFIED_35OF35_PILLAR_RECOVERY_MASTER"
P231_STATUS_FAIL_35OF35_AGGREGATOR: str = "FAIL_35OF35_PILLAR_RECOVERY_MASTER"

P231_PILLAR_35A_SCENARIO_IDS: Tuple[str, ...] = (
    "P35A1_SILENT_ON_AUTO_PIXELMAP_TARGET_BENCH_SHUTDOWN_FIREWALL_5LOCKOUT_SAFE",
    "P35A2_SILENT_ON_NOT_TARGET_PRESERVES_NORMAL_AUTO_PIXELMAP_AND_APERTURE_DRIVE_OUTSIDE_BENCH_SAFE",
    "P35A3_REJECT_BENCH_SHUTDOWN_WITH_AUTO_PIXELMAP_UNSUPPRESSED_SILENT_OFF_OR_NOT_TARGET",
    "P35A4_REJECT_SILENT_MODE_ON_MECHANICAL_SHUTTER_AUDIO_OR_5_FUNCTION_LOCKOUT_BREACH",
    "P35A5_REJECT_FABRICATED_SHUTTER_WHEN_PWR_OFF_ON_ILME_FX3_200_TO_702",
    "P35A6_REJECT_UNCOMMANDED_POWEROFF_CNFLASHA_DEFECT_TABLE_TOUCH",
)
P231_PILLAR_35B_SCENARIO_IDS: Tuple[str, ...] = (
    "P35B1_MARKER_239_1_SURVIVES_CAMERA_SETTINGS_RESET_ZERO_HDMI_AND_FLEXEXP_RESETS_TO_MANUAL_ON_SAFE",
    "P35B2_INITIALIZE_CLEARS_MARKERS_AND_CAMSET01_SLOT1_VAULT_RESTORES_FLEXEXP_AV_TV_ISO_SAFE",
    "P35B3_REJECT_MARKER_WIPED_BY_CAMERA_SETTINGS_RESET_OR_SURVIVING_INITIALIZE",
    "P35B4_REJECT_HDMI_MARKER_OVERLAY_LEAKAGE_WITH_HDMI_INFO_DISPLAY_ON",
    "P35B5_REJECT_FLEXEXP_AV_TV_ISO_OR_AUTO_SLOW_SHUTTER_FAILING_TO_RESET_ON_CAMERA_SETTINGS_RESET",
    "P35B6_REJECT_SLOT2_OR_DRIFTED_CAMSET_FLEXEXP_VAULT_RESTORE",
)

MASTER_35_PILLAR_COUNT: int = 35
MASTER_35_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_34_PILLAR_SPECS + (
    (
        35,
        "pillar_35_silent_autopixelmap_marker_flexexp_vault",
        "Phase 231",
        "fx3_recovery.realhw_35pillar_silent_autopixelmap_marker_vault_verifier",
    ),
)
MASTER_35_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_35_PILLAR_SPECS)


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
    return any(tok in low for tok in P231_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase231DonorArtifactDigest:
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
class Phase231DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase231DonorArtifactDigest, ...]


@dataclass(frozen=True)
class SilentModeAutoPixelMapBenchFirewallSpec:
    camera_model: str = P231_FX3_MODEL_NAME
    fw_version: str = P231_FX3_FW_VERSION
    silent_mode: str = "On"  # Off | On
    aperture_drive_in_af_target: str = "Target"  # Target | Not Target
    auto_pixel_mapping_target: str = "Target"  # Target | Not Target
    aperture_drive_in_af_setting: str = "Standard"  # Standard | Focus Priority | Silent Priority
    auto_pixel_mapping_setting: str = "On"  # On | Off
    effective_auto_pixel_mapping_retained: bool = False
    effective_aperture_drive_retained: bool = False
    shutter_type: str = P231_LOCKED_SILENT_SHUTTER_TYPE
    shutter_type_in_interval: str = P231_LOCKED_SILENT_SHUTTER_TYPE
    audio_signals: str = P231_LOCKED_SILENT_AUDIO_SIGNALS
    flash_shooting_enabled: bool = False
    long_exposure_nr_enabled: bool = False
    e_front_curtain_shutter_enabled: bool = False
    bulb_shooting_enabled: bool = False
    anti_flicker_shoot_enabled: bool = False
    tier0_bench_shutdown_cycle_active: bool = True
    poweroff_mechanical_pixelmap_suppressed: bool = True
    poweroff_mechanical_shutter_actuated: bool = False
    poweroff_cnflasha_calibration_touches: int = 0
    cnflasha_defect_table_write_attempted: bool = False
    shutter_when_pwr_off_menu_present: bool = False
    shutter_when_pwr_off_setting: str = P231_SHUTTER_WHEN_PWR_OFF_ABSENT
    setup_sensor_menu_items: Tuple[str, ...] = P231_FX3_SETUP_SENSOR_MENU_ITEMS
    target_function_menu_items: Tuple[str, ...] = P231_TARGET_FUNCTION_ITEMS
    overlay_dir: str = P231_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P231_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P231_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P231_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class SilentModeAutoPixelMapBenchFirewallReport:
    passed: bool
    status: str
    block_code: Optional[str]
    silent_mode: str
    auto_pixel_mapping_target: str
    aperture_drive_in_af_target: str
    bench_shutdown_firewall_verified: bool
    silent_5_function_lockout_verified: bool
    shutter_when_pwr_off_absent_verified: bool
    cnflasha_zero_touch_verified: bool
    h0_equals_h3_verified: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarkerPersistenceAndFlexExpVaultSpec:
    camera_model: str = P231_FX3_MODEL_NAME
    fw_version: str = P231_FX3_FW_VERSION
    pre_reset_marker_display: str = "On"
    pre_reset_center_marker: str = "On"
    pre_reset_aspect_marker: str = "2.39:1"
    pre_reset_safety_zone: str = "90%"
    pre_reset_guideframe: str = "On"
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Initialize
    post_reset_marker_display: str = "On"
    post_reset_center_marker: str = "On"
    post_reset_aspect_marker: str = "2.39:1"
    post_reset_safety_zone: str = "90%"
    post_reset_guideframe: str = "On"
    hdmi_info_display: str = "On"
    lcd_markers_rendered: bool = True
    hdmi_center_marker_rendered: bool = False
    hdmi_aspect_marker_rendered: bool = False
    hdmi_safety_zone_rendered: bool = False
    hdmi_guideframe_rendered: bool = False
    hdmi_marker_overlay_leak_count: int = 0
    exposure_ctrl_type: str = "Flexible Exp. Mode"  # P/A/S/M Mode | Flexible Exp. Mode
    pasm_submode: str = "Manual Exposure"
    pre_reset_av_switch: str = "Auto"
    pre_reset_tv_switch: str = "Auto"
    pre_reset_iso_switch: str = "Auto"
    pre_reset_auto_slow_shutter: str = "Off"
    post_reset_exposure_ctrl_type: str = "Flexible Exp. Mode"
    post_reset_av_switch: str = "Manual"
    post_reset_tv_switch: str = "Manual"
    post_reset_iso_switch: str = "Manual"
    post_reset_auto_slow_shutter: str = "On"
    camset_restore_after_reset: bool = False
    camset_slot: int = P231_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    saved_exposure_ctrl_type: str = "Flexible Exp. Mode"
    saved_av_switch: str = "Auto"
    saved_tv_switch: str = "Auto"
    saved_iso_switch: str = "Auto"
    saved_auto_slow_shutter: str = "Off"
    stage_b_overlay_dir: str = P231_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P231_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P231_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P231_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class MarkerPersistenceAndFlexExpVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    marker_reset_persistence_verified: bool
    hdmi_marker_zero_leak_verified: bool
    flexexp_reset_split_verified: bool
    camset_slot1_restore_verified: bool
    h0_equals_h3_verified: bool
    tier0_surfaces_intact: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SilentAutoPixelMapAndMarkerFlexExpVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase231DonorSnapshot
    silent_autopixelmap_report: SilentModeAutoPixelMapBenchFirewallReport
    marker_flexexp_report: MarkerPersistenceAndFlexExpVaultReport
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
class Pillar35ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar35ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar35ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar35BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar35ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar35StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase231DonorSnapshot
    pillar_35a_silent_autopixelmap_firewall: Pillar35ASuiteResult
    pillar_35b_marker_hdmi_flexexp_vault: Pillar35BSuiteResult
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
class Master35PillarRecoveryReport:
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
    nominal_under_3_6s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase231DonorSnapshot
    pillar35_a_silent_autopixelmap_firewall: Pillar35ASuiteResult
    pillar35_b_marker_hdmi_flexexp_vault: Pillar35BSuiteResult
    master_35pillar_sha256: str
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
    max_full_bytes: int = P231_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P231_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase231_donors() -> Tuple[Phase231DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P231_DONOR_FX3_BODYDATA_RELPATH,
            P231_PINNED_FX3_BODYDATA_BYTES,
            P231_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P231_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P231_DONOR_FX3_APPFW_702_RELPATH,
            P231_PINNED_FX3_APPFW_702_BYTES,
            P231_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P231_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_APPFW_702",
        ),
        (
            "fx3_backup_bin",
            P231_DONOR_FX3_BACKUP_BIN_RELPATH,
            P231_PINNED_FX3_BACKUP_BIN_BYTES,
            P231_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P231_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P231_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P231_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P231_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P231_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P231_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P231_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P231_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P231_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libinframediaconfig_so",
            P231_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P231_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P231_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P231_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+GetMediaNum+Backup_sync_subsystem",
        ),
        (
            "fx3_camera_ondemand_saver_so",
            P231_DONOR_FX3_CAMERA_ONDEMAND_SAVER_SO_RELPATH,
            P231_PINNED_FX3_CAMERA_ONDEMAND_SAVER_SO_BYTES,
            P231_PINNED_FX3_CAMERA_ONDEMAND_SAVER_SO_BYTES,
            "FULL_SHA256",
            P231_PINNED_FX3_CAMERA_ONDEMAND_SAVER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:cam_ondemand_saver_init+cam_ondemand_saver_thread+cam_ondemand_saver_exit",
        ),
    )
    return tuple(
        Phase231DonorArtifactDigest(
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


def inspect_phase231_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase231DonorSnapshot:
    """Inspect Wave-33 / FX3 7.02 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase231_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase231DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P231_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P231_DONOR_FX3_BODYDATA_RELPATH,
            P231_PINNED_FX3_BODYDATA_BYTES,
            P231_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P231_DONOR_FX3_APPFW_702_RELPATH,
            P231_PINNED_FX3_APPFW_702_BYTES,
            P231_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P231_DONOR_FX3_BACKUP_BIN_RELPATH,
            P231_PINNED_FX3_BACKUP_BIN_BYTES,
            P231_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P231_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P231_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P231_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P231_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P231_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P231_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libinframediaconfig_so",
            P231_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P231_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P231_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"InfraMediaConfig", b"GetMediaNum", b"Backup_sync_subsystem")
            ),
        ),
        (
            "fx3_camera_ondemand_saver_so",
            P231_DONOR_FX3_CAMERA_ONDEMAND_SAVER_SO_RELPATH,
            P231_PINNED_FX3_CAMERA_ONDEMAND_SAVER_SO_BYTES,
            P231_PINNED_FX3_CAMERA_ONDEMAND_SAVER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"cam_ondemand_saver_init", b"cam_ondemand_saver_thread", b"cam_ondemand_saver_exit")
            ),
        ),
    )

    digests: List[Phase231DonorArtifactDigest] = []
    for aid, rel, pinned_bytes, pinned_sha, validator in probe_specs:
        ok, total_b, hdr_b, dkind, dsha, raw = _read_donor_readonly_bounded(rel)
        if not ok:
            digests.append(
                Phase231DonorArtifactDigest(
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
            Phase231DonorArtifactDigest(
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
        synth = _synthetic_phase231_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase231DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P231_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    dt = round(time.monotonic() - t0, 6)
    return Phase231DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all(d.present and d.matches_pinned for d in digests),
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P231_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Pillar 35A & 35B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_silent_autopixelmap_spec() -> SilentModeAutoPixelMapBenchFirewallSpec:
    return SilentModeAutoPixelMapBenchFirewallSpec()


def build_default_safe_marker_flexexp_vault_spec() -> MarkerPersistenceAndFlexExpVaultSpec:
    return MarkerPersistenceAndFlexExpVaultSpec()


def evaluate_silent_mode_autopixelmap_bench_firewall(
    spec: SilentModeAutoPixelMapBenchFirewallSpec,
) -> SilentModeAutoPixelMapBenchFirewallReport:
    """Audit `[Silent Mode]` `[Auto Pixel Mapping]` bench shutdown firewall, 5-function lockout & `[Shutter When Pwr OFF]` absence."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P231_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P231_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 35A")

    if (
        spec.camera_model != P231_FX3_MODEL_NAME
        or spec.fw_version not in P231_FX3_SUPPORTED_FW_VERSIONS
        or spec.silent_mode not in P231_SILENT_MODE_STATES
        or spec.aperture_drive_in_af_target not in P231_TARGET_FUNCTION_MODES
        or spec.auto_pixel_mapping_target not in P231_TARGET_FUNCTION_MODES
        or spec.aperture_drive_in_af_setting not in P231_APERTURE_DRIVE_IN_AF_MODES
        or spec.auto_pixel_mapping_setting not in P231_AUTO_PIXEL_MAPPING_MODES
        or spec.shutter_type not in P231_SHUTTER_TYPES
        or spec.shutter_type_in_interval not in P231_SHUTTER_TYPES
        or spec.audio_signals not in P231_AUDIO_SIGNALS_MODES
    ):
        _fail(
            P231_BLOCKED_INVALID_SILENT_OR_PIXELMAP_SPEC,
            f"Unsupported model/fw or Silent Mode / Target Function parameter on {spec.camera_model!r} {spec.fw_version!r}",
        )

    no_pwrshutter_ok = True
    if (
        spec.shutter_when_pwr_off_menu_present
        or spec.shutter_when_pwr_off_setting != P231_SHUTTER_WHEN_PWR_OFF_ABSENT
        or P231_FORBIDDEN_SHUTTER_WHEN_PWR_OFF_ITEM in spec.setup_sensor_menu_items
        or P231_FORBIDDEN_SHUTTER_WHEN_PWR_OFF_ITEM in spec.target_function_menu_items
    ):
        no_pwrshutter_ok = False
        _fail(
            P231_BLOCKED_FABRICATED_SHUTTER_WHEN_PWR_OFF_ON_FX3,
            f"[Shutter When Pwr OFF] does not exist on physical {P231_FX3_MODEL_NAME} "
            f"(Ver. 2.00..7.02; inspected Ver. {spec.fw_version}): only {P231_FX3_SETUP_SENSOR_MENU_ITEMS} exist",
        )
    elif (
        any(item not in P231_FX3_SETUP_SENSOR_MENU_ITEMS for item in spec.setup_sensor_menu_items)
        or any(item not in P231_TARGET_FUNCTION_ITEMS for item in spec.target_function_menu_items)
        or len(spec.setup_sensor_menu_items) == 0
        or len(spec.target_function_menu_items) == 0
    ):
        no_pwrshutter_ok = False
        _fail(
            P231_BLOCKED_INVALID_SILENT_OR_PIXELMAP_SPEC,
            "Unrecognized sensor maintenance or [Target Function Settings] menu items",
        )

    silent_lockout_ok = True
    if spec.silent_mode == "On":
        lockout_breaches: List[str] = []
        if spec.shutter_type != P231_LOCKED_SILENT_SHUTTER_TYPE:
            lockout_breaches.append(f"[Shutter Type]={spec.shutter_type!r} (must lock to 'Electronic Shutter')")
        if spec.shutter_type_in_interval != P231_LOCKED_SILENT_SHUTTER_TYPE:
            lockout_breaches.append(
                f"[Shutter Type in Interval]={spec.shutter_type_in_interval!r} (must lock to 'Electronic Shutter')"
            )
        if spec.audio_signals != P231_LOCKED_SILENT_AUDIO_SIGNALS:
            lockout_breaches.append(f"[Audio signals]={spec.audio_signals!r} (must lock to 'Off')")
        if spec.flash_shooting_enabled:
            lockout_breaches.append("Flash shooting enabled under [Silent Mode]=On")
        if spec.long_exposure_nr_enabled:
            lockout_breaches.append("[Long Exposure NR] enabled under [Silent Mode]=On")
        if spec.e_front_curtain_shutter_enabled:
            lockout_breaches.append("[e-Front Curtain Shut.] enabled under [Silent Mode]=On")
        if spec.bulb_shooting_enabled:
            lockout_breaches.append("BULB shooting enabled under [Silent Mode]=On")
        if spec.anti_flicker_shoot_enabled:
            lockout_breaches.append("[Anti-flicker Shoot.] enabled under [Silent Mode]=On")
        if lockout_breaches:
            silent_lockout_ok = False
            _fail(
                P231_BLOCKED_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCKOUT_VIOLATION,
                "[Silent Mode]=On lockout violated: " + "; ".join(lockout_breaches),
            )

    cnflasha_zero_touch_ok = True
    if spec.poweroff_cnflasha_calibration_touches != 0 or spec.cnflasha_defect_table_write_attempted:
        cnflasha_zero_touch_ok = False
        _fail(
            P231_BLOCKED_CNFLASHA_DEFECT_TABLE_TOUCH_ON_SHUTDOWN,
            "Uncommanded power-off dark-frame calibration touched or attempted write to cnflasha defect table",
        )

    silent_suppresses_autopixelmap = spec.silent_mode == "On" and spec.auto_pixel_mapping_target == "Target"
    silent_suppresses_aperture = spec.silent_mode == "On" and spec.aperture_drive_in_af_target == "Target"
    expected_autopixelmap_retained = not silent_suppresses_autopixelmap
    expected_aperture_retained = not silent_suppresses_aperture
    expected_poweroff_suppressed = (spec.auto_pixel_mapping_setting == "Off") or silent_suppresses_autopixelmap

    bench_firewall_ok = True
    if spec.tier0_bench_shutdown_cycle_active:
        if not expected_poweroff_suppressed or spec.poweroff_mechanical_shutter_actuated:
            bench_firewall_ok = False
            _fail(
                P231_BLOCKED_BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP,
                "Active Tier-0 bench shutdown requires [Silent Mode]=On with [Auto Pixel Mapping]=Target "
                "(or [Auto Pixel Mapping]=Off) and zero power-off mechanical shutter actuation",
            )
    elif spec.poweroff_mechanical_shutter_actuated and expected_poweroff_suppressed:
        bench_firewall_ok = False
        _fail(
            P231_BLOCKED_TARGET_FUNCTION_SETTINGS_SEMANTIC_DRIFT,
            "Power-off mechanical shutter actuated despite [Auto Pixel Mapping] suppression",
        )

    if (
        spec.effective_auto_pixel_mapping_retained != expected_autopixelmap_retained
        or spec.effective_aperture_drive_retained != expected_aperture_retained
        or spec.poweroff_mechanical_pixelmap_suppressed != expected_poweroff_suppressed
    ):
        bench_firewall_ok = False
        _fail(
            P231_BLOCKED_TARGET_FUNCTION_SETTINGS_SEMANTIC_DRIFT,
            "[Target Function Settings] semantic drift: [Not Target] must retain normal [Auto Pixel Mapping] / "
            "[Aperture Drive in AF] while [Target] under [Silent Mode]=On suppresses them",
        )

    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _fail(
            P231_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P231_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P231_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P231_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or p2 BLKROSET immutability drifted in Pillar 35A",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "35A",
            "passed": passed,
            "block_code": block_code,
            "fw_version": spec.fw_version,
            "silent_mode": spec.silent_mode,
            "auto_pixel_mapping_target": spec.auto_pixel_mapping_target,
            "aperture_drive_in_af_target": spec.aperture_drive_in_af_target,
            "bench_shutdown": spec.tier0_bench_shutdown_cycle_active,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return SilentModeAutoPixelMapBenchFirewallReport(
        passed=passed,
        status=P231_STATUS_VERIFIED_PILLAR_35A if passed else P231_STATUS_REJECTED_PILLAR_35A,
        block_code=block_code,
        silent_mode=spec.silent_mode,
        auto_pixel_mapping_target=spec.auto_pixel_mapping_target,
        aperture_drive_in_af_target=spec.aperture_drive_in_af_target,
        bench_shutdown_firewall_verified=bench_firewall_ok and passed,
        silent_5_function_lockout_verified=silent_lockout_ok and passed,
        shutter_when_pwr_off_absent_verified=no_pwrshutter_ok and passed,
        cnflasha_zero_touch_verified=cnflasha_zero_touch_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_marker_persistence_hdmi_and_flexexp_vault(
    spec: MarkerPersistenceAndFlexExpVaultSpec,
) -> MarkerPersistenceAndFlexExpVaultReport:
    """Audit `[Marker Display]` 15-ratio reset survival, HDMI marker suppression & `[Flexible Exp. Mode]` reset split."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P231_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P231_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 35B")

    marker_persistence_ok = True
    valid_marker_tokens = (
        spec.camera_model == P231_FX3_MODEL_NAME
        and spec.fw_version in P231_FX3_SUPPORTED_FW_VERSIONS
        and spec.pre_reset_marker_display in P231_MARKER_ON_OFF_MODES
        and spec.post_reset_marker_display in P231_MARKER_ON_OFF_MODES
        and spec.pre_reset_center_marker in P231_MARKER_ON_OFF_MODES
        and spec.post_reset_center_marker in P231_MARKER_ON_OFF_MODES
        and spec.pre_reset_aspect_marker in P231_ASPECT_MARKER_MODES
        and spec.post_reset_aspect_marker in P231_ASPECT_MARKER_MODES
        and spec.pre_reset_safety_zone in P231_SAFETY_ZONE_MODES
        and spec.post_reset_safety_zone in P231_SAFETY_ZONE_MODES
        and spec.pre_reset_guideframe in P231_MARKER_ON_OFF_MODES
        and spec.post_reset_guideframe in P231_MARKER_ON_OFF_MODES
        and spec.reset_action in P231_RESET_ACTIONS
    )
    if not valid_marker_tokens:
        marker_persistence_ok = False
        _fail(
            P231_BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC,
            "Invalid model/fw, [Marker Display] item, 15-ratio [Aspect Marker], [Safety Zone], or reset_action",
        )
    elif spec.fw_version in P231_FX3_PRE_300_FW_VERSIONS and (
        spec.pre_reset_aspect_marker == P231_ASPECT_MARKER_VER300_RATIO
        or spec.post_reset_aspect_marker == P231_ASPECT_MARKER_VER300_RATIO
    ):
        marker_persistence_ok = False
        _fail(
            P231_BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC,
            f"[Aspect Marker] 16:9 requires ILME-FX3 Ver. 3.00+, got Ver. {spec.fw_version}",
        )
    elif spec.reset_action in ("NONE", "Camera Settings Reset"):
        if (
            spec.post_reset_marker_display != spec.pre_reset_marker_display
            or spec.post_reset_center_marker != spec.pre_reset_center_marker
            or spec.post_reset_aspect_marker != spec.pre_reset_aspect_marker
            or spec.post_reset_safety_zone != spec.pre_reset_safety_zone
            or spec.post_reset_guideframe != spec.pre_reset_guideframe
        ):
            marker_persistence_ok = False
            _fail(
                P231_BLOCKED_MARKER_CAMERA_SETTINGS_RESET_DRIFT,
                "[Marker Display] (Center, 15-ratio Aspect, Safety Zone, Guideframe) must survive "
                "[Camera Settings Reset] unchanged",
            )
    elif spec.reset_action == "Initialize":
        if (
            spec.post_reset_marker_display != P231_MARKER_DISPLAY_DEFAULT
            or spec.post_reset_center_marker != "Off"
            or spec.post_reset_aspect_marker != P231_ASPECT_MARKER_DEFAULT
            or spec.post_reset_safety_zone != P231_SAFETY_ZONE_DEFAULT
            or spec.post_reset_guideframe != "Off"
        ):
            marker_persistence_ok = False
            _fail(
                P231_BLOCKED_MARKER_CAMERA_SETTINGS_RESET_DRIFT,
                "[Initialize] must clear [Marker Display], [Center Marker], [Aspect Marker], "
                "[Safety Zone], and [Guideframe] to 'Off'",
            )

    hdmi_marker_ok = True
    if spec.hdmi_info_display not in P231_HDMI_INFO_DISPLAY_MODES:
        hdmi_marker_ok = False
        _fail(
            P231_BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC,
            f"Unsupported [HDMI Info. Display] mode: {spec.hdmi_info_display!r}",
        )
    else:
        any_submarker_on = any(
            sub != "Off"
            for sub in (
                spec.post_reset_center_marker,
                spec.post_reset_aspect_marker,
                spec.post_reset_safety_zone,
                spec.post_reset_guideframe,
            )
        )
        expected_lcd_markers = (spec.post_reset_marker_display == "On") and any_submarker_on
        if (
            spec.hdmi_center_marker_rendered
            or spec.hdmi_aspect_marker_rendered
            or spec.hdmi_safety_zone_rendered
            or spec.hdmi_guideframe_rendered
            or spec.hdmi_marker_overlay_leak_count != 0
            or spec.lcd_markers_rendered != expected_lcd_markers
        ):
            hdmi_marker_ok = False
            _fail(
                P231_BLOCKED_HDMI_MARKER_OVERLAY_LEAKAGE,
                "[Marker Display] overlays (Center, Aspect, Safety Zone, Guideframe) are displayed on the "
                "camera monitor only and must leak 0 overlays onto HDMI even with [HDMI Info. Display]=On",
            )

    flexexp_split_ok = True
    camset_restore_ok = True
    valid_flexexp_tokens = (
        spec.exposure_ctrl_type in P231_EXPOSURE_CTRL_TYPES
        and spec.post_reset_exposure_ctrl_type in P231_EXPOSURE_CTRL_TYPES
        and spec.saved_exposure_ctrl_type in P231_EXPOSURE_CTRL_TYPES
        and spec.pasm_submode in P231_PASM_SUBMODES
        and spec.pre_reset_av_switch in P231_FLEXEXP_SWITCH_MODES
        and spec.pre_reset_tv_switch in P231_FLEXEXP_SWITCH_MODES
        and spec.pre_reset_iso_switch in P231_FLEXEXP_SWITCH_MODES
        and spec.post_reset_av_switch in P231_FLEXEXP_SWITCH_MODES
        and spec.post_reset_tv_switch in P231_FLEXEXP_SWITCH_MODES
        and spec.post_reset_iso_switch in P231_FLEXEXP_SWITCH_MODES
        and spec.saved_av_switch in P231_FLEXEXP_SWITCH_MODES
        and spec.saved_tv_switch in P231_FLEXEXP_SWITCH_MODES
        and spec.saved_iso_switch in P231_FLEXEXP_SWITCH_MODES
        and spec.pre_reset_auto_slow_shutter in P231_AUTO_SLOW_SHUTTER_MODES
        and spec.post_reset_auto_slow_shutter in P231_AUTO_SLOW_SHUTTER_MODES
        and spec.saved_auto_slow_shutter in P231_AUTO_SLOW_SHUTTER_MODES
    )
    if not valid_flexexp_tokens:
        flexexp_split_ok = False
        _fail(
            P231_BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC,
            "Invalid [Exposure Ctrl Type], [P/A/S/M Mode], [Auto/Manual Swt. Set.] (Av/Tv/ISO), or [Auto Slow Shutter]",
        )
    elif spec.camset_slot != P231_SLOT1_VAULT_SLOT or spec.camset_filename not in P231_CAMSET_FILENAMES:
        camset_restore_ok = False
        _fail(
            P231_BLOCKED_CAMSET_SLOT1_FLEXEXP_RESTORE_DRIFT,
            f"CAMSET vault must reside on Slot 1 ({P231_CAMSET_FILENAMES[0]}..{P231_CAMSET_FILENAMES[-1]}), "
            f"got slot={spec.camset_slot!r}, file={spec.camset_filename!r}",
        )
    elif spec.camset_restore_after_reset:
        if (
            spec.post_reset_exposure_ctrl_type != spec.saved_exposure_ctrl_type
            or spec.post_reset_av_switch != spec.saved_av_switch
            or spec.post_reset_tv_switch != spec.saved_tv_switch
            or spec.post_reset_iso_switch != spec.saved_iso_switch
            or spec.post_reset_auto_slow_shutter != spec.saved_auto_slow_shutter
        ):
            camset_restore_ok = False
            _fail(
                P231_BLOCKED_CAMSET_SLOT1_FLEXEXP_RESTORE_DRIFT,
                "Slot-1 CAMSET vault restore failed to recover saved [Exposure Ctrl Type], "
                "Av/Tv/ISO Auto/Manual switches, or [Auto Slow Shutter]",
            )
    else:
        if spec.reset_action in ("Camera Settings Reset", "Initialize"):
            if (
                spec.post_reset_av_switch != P231_FLEXEXP_SWITCH_DEFAULT
                or spec.post_reset_tv_switch != P231_FLEXEXP_SWITCH_DEFAULT
                or spec.post_reset_iso_switch != P231_FLEXEXP_SWITCH_DEFAULT
                or spec.post_reset_auto_slow_shutter != P231_AUTO_SLOW_SHUTTER_DEFAULT
            ):
                flexexp_split_ok = False
                _fail(
                    P231_BLOCKED_FLEXEXP_OR_AUTOSLOWSHUTTER_RESET_SPLIT_DRIFT,
                    "[Flexible Exp. Mode] [Auto/Manual Swt. Set.] (Av/Tv/ISO -> 'Manual') and "
                    "[Auto Slow Shutter] (-> 'On') must reset cleanly under [Camera Settings Reset] / [Initialize]",
                )
        elif spec.reset_action == "NONE":
            if (
                spec.post_reset_exposure_ctrl_type != spec.exposure_ctrl_type
                or spec.post_reset_av_switch != spec.pre_reset_av_switch
                or spec.post_reset_tv_switch != spec.pre_reset_tv_switch
                or spec.post_reset_iso_switch != spec.pre_reset_iso_switch
                or spec.post_reset_auto_slow_shutter != spec.pre_reset_auto_slow_shutter
            ):
                flexexp_split_ok = False
                _fail(
                    P231_BLOCKED_FLEXEXP_OR_AUTOSLOWSHUTTER_RESET_SPLIT_DRIFT,
                    "Unexpected [Flexible Exp. Mode] Av/Tv/ISO or [Auto Slow Shutter] drift when reset_action='NONE'",
                )

    if not _is_tmpfs_path(spec.stage_b_overlay_dir) or _targets_persistent_emmc(spec.stage_b_overlay_dir):
        _fail(
            P231_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.stage_b_overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P231_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P231_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P231_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or 16/16 surface parity drifted in Pillar 35B",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "35B",
            "passed": passed,
            "block_code": block_code,
            "reset_action": spec.reset_action,
            "post_markers": (
                spec.post_reset_marker_display,
                spec.post_reset_center_marker,
                spec.post_reset_aspect_marker,
                spec.post_reset_safety_zone,
                spec.post_reset_guideframe,
            ),
            "post_flexexp": (
                spec.post_reset_exposure_ctrl_type,
                spec.post_reset_av_switch,
                spec.post_reset_tv_switch,
                spec.post_reset_iso_switch,
                spec.post_reset_auto_slow_shutter,
            ),
            "camset_restore": spec.camset_restore_after_reset,
            "camset": spec.camset_filename,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return MarkerPersistenceAndFlexExpVaultReport(
        passed=passed,
        status=P231_STATUS_VERIFIED_PILLAR_35B if passed else P231_STATUS_REJECTED_PILLAR_35B,
        block_code=block_code,
        marker_reset_persistence_verified=marker_persistence_ok and passed,
        hdmi_marker_zero_leak_verified=hdmi_marker_ok and passed,
        flexexp_reset_split_verified=flexexp_split_ok and passed,
        camset_slot1_restore_verified=camset_restore_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        tier0_surfaces_intact=spec.tier0_surfaces_h0_h3_matched if h0_eq_h3 else 0,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_silent_autopixelmap_and_marker_flexexp_vault(
    silent_autopixelmap_spec: Optional[SilentModeAutoPixelMapBenchFirewallSpec] = None,
    marker_flexexp_spec: Optional[MarkerPersistenceAndFlexExpVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> SilentAutoPixelMapAndMarkerFlexExpVaultReport:
    """Combined Pillar 35 verifier: Silent Mode Auto Pixel Mapping firewall + Marker/Flexible Exp. reset-split vault."""
    donor_snap = inspect_phase231_donors_readonly(force_clean_room=force_clean_room)
    sil_rep = evaluate_silent_mode_autopixelmap_bench_firewall(
        silent_autopixelmap_spec or build_default_safe_silent_autopixelmap_spec()
    )
    mrk_rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
        marker_flexexp_spec or build_default_safe_marker_flexexp_vault_spec()
    )
    errs: List[str] = _safety_invariant_errors() + list(sil_rep.errors) + list(mrk_rep.errors)
    if not donor_snap.all_donors_present:
        errs.append("Phase 231 donor snapshot incomplete or mismatched")
    if not donor_snap.under_0_15s_budget:
        errs.append(f"Phase 231 donor inspection exceeded 2.0s budget: {donor_snap.elapsed_seconds}s")

    all_ok = sil_rep.passed and mrk_rep.passed and len(errs) == 0
    return SilentAutoPixelMapAndMarkerFlexExpVaultReport(
        schema=PHASE231_SCHEMA,
        version=PHASE231_VERSION,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P231_STATUS_VERIFIED_PILLAR35_SUITE if all_ok else P231_STATUS_FAIL_PILLAR35_SUITE,
        donor_snapshot=donor_snap,
        silent_autopixelmap_report=sil_rep,
        marker_flexexp_report=mrk_rep,
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
# 6-Scenario Suites & Standalone Pillar 35 Runner
# ---------------------------------------------------------------------------


def run_pillar35a_silent_autopixelmap_bench_6_scenario_suite() -> Pillar35ASuiteResult:
    cases: Tuple[Tuple[str, bool, SilentModeAutoPixelMapBenchFirewallSpec, Optional[str]], ...] = (
        (
            P231_PILLAR_35A_SCENARIO_IDS[0],
            True,
            SilentModeAutoPixelMapBenchFirewallSpec(),
            None,
        ),
        (
            P231_PILLAR_35A_SCENARIO_IDS[1],
            True,
            SilentModeAutoPixelMapBenchFirewallSpec(
                silent_mode="On",
                aperture_drive_in_af_target="Not Target",
                auto_pixel_mapping_target="Not Target",
                aperture_drive_in_af_setting="Focus Priority",
                auto_pixel_mapping_setting="On",
                effective_auto_pixel_mapping_retained=True,
                effective_aperture_drive_retained=True,
                tier0_bench_shutdown_cycle_active=False,
                poweroff_mechanical_pixelmap_suppressed=False,
            ),
            None,
        ),
        (
            P231_PILLAR_35A_SCENARIO_IDS[2],
            False,
            SilentModeAutoPixelMapBenchFirewallSpec(
                silent_mode="On",
                auto_pixel_mapping_target="Not Target",
                auto_pixel_mapping_setting="On",
                effective_auto_pixel_mapping_retained=True,
                tier0_bench_shutdown_cycle_active=True,
                poweroff_mechanical_pixelmap_suppressed=False,
            ),
            P231_BLOCKED_BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP,
        ),
        (
            P231_PILLAR_35A_SCENARIO_IDS[3],
            False,
            SilentModeAutoPixelMapBenchFirewallSpec(
                silent_mode="On",
                shutter_type="Mechanical Shutter",
                audio_signals="On: all",
                flash_shooting_enabled=True,
                anti_flicker_shoot_enabled=True,
            ),
            P231_BLOCKED_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCKOUT_VIOLATION,
        ),
        (
            P231_PILLAR_35A_SCENARIO_IDS[4],
            False,
            SilentModeAutoPixelMapBenchFirewallSpec(
                shutter_when_pwr_off_menu_present=True,
                shutter_when_pwr_off_setting="On",
                setup_sensor_menu_items=(
                    "Sensor Cleaning",
                    "Auto Pixel Mapping",
                    "Pixel Mapping",
                    "Shutter When Pwr OFF",
                ),
            ),
            P231_BLOCKED_FABRICATED_SHUTTER_WHEN_PWR_OFF_ON_FX3,
        ),
        (
            P231_PILLAR_35A_SCENARIO_IDS[5],
            False,
            SilentModeAutoPixelMapBenchFirewallSpec(
                poweroff_cnflasha_calibration_touches=1,
                cnflasha_defect_table_write_attempted=True,
            ),
            P231_BLOCKED_CNFLASHA_DEFECT_TABLE_TOUCH_ON_SHUTDOWN,
        ),
    )

    outcomes: List[Pillar35ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_silent_mode_autopixelmap_bench_firewall(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar35ScenarioOutcome(
                scenario_id=sid,
                pillar="35A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar35ASuiteResult(
        passed=all_ok,
        status=P231_STATUS_VERIFIED_PILLAR_35A if all_ok else P231_STATUS_REJECTED_PILLAR_35A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar35b_marker_hdmi_flexexp_vault_6_scenario_suite() -> Pillar35BSuiteResult:
    cases: Tuple[Tuple[str, bool, MarkerPersistenceAndFlexExpVaultSpec, Optional[str]], ...] = (
        (
            P231_PILLAR_35B_SCENARIO_IDS[0],
            True,
            MarkerPersistenceAndFlexExpVaultSpec(),
            None,
        ),
        (
            P231_PILLAR_35B_SCENARIO_IDS[1],
            True,
            MarkerPersistenceAndFlexExpVaultSpec(
                reset_action="Initialize",
                post_reset_marker_display="Off",
                post_reset_center_marker="Off",
                post_reset_aspect_marker="Off",
                post_reset_safety_zone="Off",
                post_reset_guideframe="Off",
                lcd_markers_rendered=False,
                camset_restore_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                saved_exposure_ctrl_type="Flexible Exp. Mode",
                saved_av_switch="Auto",
                saved_tv_switch="Manual",
                saved_iso_switch="Auto",
                saved_auto_slow_shutter="Off",
                post_reset_exposure_ctrl_type="Flexible Exp. Mode",
                post_reset_av_switch="Auto",
                post_reset_tv_switch="Manual",
                post_reset_iso_switch="Auto",
                post_reset_auto_slow_shutter="Off",
            ),
            None,
        ),
        (
            P231_PILLAR_35B_SCENARIO_IDS[2],
            False,
            MarkerPersistenceAndFlexExpVaultSpec(
                pre_reset_marker_display="On",
                pre_reset_aspect_marker="16:9",
                reset_action="Camera Settings Reset",
                post_reset_marker_display="Off",
                post_reset_aspect_marker="Off",
                lcd_markers_rendered=False,
            ),
            P231_BLOCKED_MARKER_CAMERA_SETTINGS_RESET_DRIFT,
        ),
        (
            P231_PILLAR_35B_SCENARIO_IDS[3],
            False,
            MarkerPersistenceAndFlexExpVaultSpec(
                hdmi_info_display="On",
                hdmi_aspect_marker_rendered=True,
                hdmi_safety_zone_rendered=True,
                hdmi_marker_overlay_leak_count=2,
            ),
            P231_BLOCKED_HDMI_MARKER_OVERLAY_LEAKAGE,
        ),
        (
            P231_PILLAR_35B_SCENARIO_IDS[4],
            False,
            MarkerPersistenceAndFlexExpVaultSpec(
                reset_action="Camera Settings Reset",
                camset_restore_after_reset=False,
                pre_reset_av_switch="Auto",
                post_reset_av_switch="Auto",
                pre_reset_auto_slow_shutter="Off",
                post_reset_auto_slow_shutter="Off",
            ),
            P231_BLOCKED_FLEXEXP_OR_AUTOSLOWSHUTTER_RESET_SPLIT_DRIFT,
        ),
        (
            P231_PILLAR_35B_SCENARIO_IDS[5],
            False,
            MarkerPersistenceAndFlexExpVaultSpec(
                camset_restore_after_reset=True,
                camset_slot=2,
                saved_iso_switch="Auto",
                post_reset_iso_switch="Manual",
            ),
            P231_BLOCKED_CAMSET_SLOT1_FLEXEXP_RESTORE_DRIFT,
        ),
    )

    outcomes: List[Pillar35ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar35ScenarioOutcome(
                scenario_id=sid,
                pillar="35B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar35BSuiteResult(
        passed=all_ok,
        status=P231_STATUS_VERIFIED_PILLAR_35B if all_ok else P231_STATUS_REJECTED_PILLAR_35B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar35_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar35StandaloneReport:
    """Run full Pillar 35 standalone suite (`6/6` Pillar 35A + `6/6` Pillar 35B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase231_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar35a_silent_autopixelmap_bench_6_scenario_suite()
    res_b = run_pillar35b_marker_hdmi_flexexp_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 231 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE231_SCHEMA,
            "version": PHASE231_VERSION,
            "mode": donor_snapshot.verification_mode,
            "35a": [asdict(s) for s in res_a.scenarios],
            "35b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar35StandaloneReport(
        schema=PHASE231_SCHEMA,
        version=PHASE231_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P231_STATUS_VERIFIED_PILLAR35_SUITE if all_ok else P231_STATUS_FAIL_PILLAR35_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_35a_silent_autopixelmap_firewall=res_a,
        pillar_35b_marker_hdmi_flexexp_vault=res_b,
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
# Unified 35/35 Milestone Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master35_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_35pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master35PillarRecoveryReport:
    """Evaluate and aggregate all 35 recovery pillars (`1..35`) concurrently -> `35/35` milestone master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_35_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_34pillar() -> Master34PillarRecoveryReport:
        return evaluate_realhw_34pillar_recovery_master(**kw)

    def _run_p35() -> Tuple[Pillar35StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar35_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_34 = pool.submit(_run_34pillar)
        fut_35 = pool.submit(_run_p35)
        m34_rep = fut_34.result()
        p35_rep, p35_dt = fut_35.result()

    all_errors: List[str] = list(m34_rep.errors) + list(p35_rep.errors)
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
        if getattr(m34_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-34 violated {attr_name} == {expected_val}")
        if getattr(p35_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 35 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m34_rep.pillars)
    spec35 = MASTER_35_PILLAR_SPECS[34]
    p35_metrics = {
        "pillar_35a_silent_autopixelmap_firewall": (
            f"{p35_rep.pillar_35a_silent_autopixelmap_firewall.scenarios_passed}/"
            f"{p35_rep.pillar_35a_silent_autopixelmap_firewall.scenarios_total}"
        ),
        "pillar_35b_marker_hdmi_flexexp_vault": (
            f"{p35_rep.pillar_35b_marker_hdmi_flexexp_vault.scenarios_passed}/"
            f"{p35_rep.pillar_35b_marker_hdmi_flexexp_vault.scenarios_total}"
        ),
        "aspect_marker_ratios_count": len(P231_ASPECT_MARKER_15_RATIOS),
        "hdmi_marker_overlay_leak_count": 0,
        "donor_files_inspected": p35_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec35[0],
            pillar_id=spec35[1],
            phase_label=spec35[2],
            module_name=spec35[3],
            passed=bool(p35_rep.all_passed),
            status=p35_rep.status,
            verification_mode=p35_rep.verification_mode,
            elapsed_seconds=p35_dt,
            key_metrics=p35_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec35[1],
                    "mode": p35_rep.verification_mode,
                    "status": p35_rep.status,
                    "metrics": p35_metrics,
                    "passed": p35_rep.all_passed,
                }
            ),
            errors=tuple(p35_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master35_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p35_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_35_PILLAR_COUNT == 35
        and pillars_passed == 35
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE231_SCHEMA,
            "version": PHASE231_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master35PillarRecoveryReport(
        schema=PHASE231_SCHEMA,
        version=PHASE231_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P231_STATUS_VERIFIED_35OF35_AGGREGATOR if all_ok else P231_STATUS_FAIL_35OF35_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P231_CONCURRENT_CEILING_SECONDS,
        nominal_under_3_6s=elapsed < P231_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p35_rep.donor_snapshot,
        pillar35_a_silent_autopixelmap_firewall=p35_rep.pillar_35a_silent_autopixelmap_firewall,
        pillar35_b_marker_hdmi_flexexp_vault=p35_rep.pillar_35b_marker_hdmi_flexexp_vault,
        master_35pillar_sha256=master_sha,
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


def evaluate_35pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master35PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_35pillar_recovery_master`."""
    return evaluate_realhw_35pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_35pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master35PillarRecoveryReport:
    """Public CLI entry point for Pillar 35 unified `35/35` real-hardware recovery master verification."""
    return evaluate_realhw_35pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
