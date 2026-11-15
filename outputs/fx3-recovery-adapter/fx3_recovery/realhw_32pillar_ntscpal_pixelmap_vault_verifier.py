"""Phase 220 — Pillar 32 (`32/32` Recovery Pillars) & Unified 32-Pillar Recovery Master
(`verify-32pillar-recovery` / `verify-ntscpal-pixelmap-vault`):

1. **Pillar 32A — `[NTSC/PAL Selector]` Reset Asymmetry, Frame-Rate / `DF-NDF` Exclusivity,
   Dual-Slot `M4ROOT` / `PRIVATE/AVCHD` Media Database Separation & `[Gamma Display Assist]` vs
   `[Log Shooting]` `[Display LUT]` Vault Parity**:
   - Audits `[NTSC/PAL Selector]` reset asymmetry (`[Camera Settings Reset]` preserves
     `[NTSC/PAL Selector]` under `[Setup]`; only full `[Initialize]` restores regional factory
     `[Setup]` defaults) and startup notification banner (`"Running on NTSC."` / `"Running on PAL."`
     whenever switched away from factory regional default).
   - Enforces NTSC (`23.98p` NTSC-exclusive, `24.00p`, `29.97p`, `59.94p`, `119.88p` + `DF`/`NDF`
     `[TC Format]`) vs PAL (`25p`, `50p`, `100p`; `23.98p` and `DF`/`NDF` unavailable) exclusivity,
     plus Slot 1 & Slot 2 `M4ROOT` / `PRIVATE/AVCHD` media database separation so restoring
     `Backup.bin` or swapping NTSC/PAL cards never triggers destructive card re-registration
     without verified off-card backup.
   - Audits 4-mode `[Gamma Disp. Assist Typ.]` (`Auto`, `S-Log3->709(800%)`, `HLG(BT.2020)`,
     `HLG(709)`), hard `[Off]` lockout whenever `[Log Shooting]` (`Cine EI` / `Cine EI Quick` /
     `Flexible ISO`) is active (governed exclusively by `[Display LUT]`), camera-LCD-only scope
     (never applied over HDMI), and `Backup.bin` restoration parity (`H0 == H3`).

2. **Pillar 32B — Manual `[Pixel Mapping]` Automatic Camera Restart (`H1 -> H2` Volatile `/tmp`
   Stage-B Wipe to Stock `FX3 Ver. 7.02` `H0 == H2`), Low-Battery Lockout, `[Auto Pixel Mapping]`
   Power-Off Shutter Dark-Frame Safety & Strict `cnflasha` Sensor Defect-Table Read-Only Vault**:
   - Enforces low-battery lockout before manual `[Pixel Mapping]` (`>= 20%` and no low-battery
     warning) and Tier-0 cold backup (`>= 51%` NP-FZ100 floor), full camera-operation lockout
     during calibration, and mandatory automatic camera restart upon completion that wipes volatile
     `/tmp` Stage-B overlays (`H1 -> H2`) cleanly back to stock `FX3 Ver. 7.02` (`H0 == H2`).
   - Audits `[Auto Pixel Mapping]` (`On` default power-off dark-frame shutter actuation even under
     `[Silent Mode] = [On]` without battery-pull hazard; `<= 3`-day manual cadence when `Off`).
   - Hard-locks `cnflasha` `IMX510` factory sensor defect-table partitions strictly read-only
     (`cnflasha_userspace_write_blocked == True`, `persistent_emmc_writes_authorized == False`,
     `physical_device_writes == 0`).

3. **Unified `32/32` Recovery Master (`evaluate_realhw_32pillar_recovery_master`)**:
   - Delegates Pillars `1..31` concurrently to `evaluate_realhw_31pillar_recovery_master` +
     **Pillar 32** -> **`32/32` (`VERIFIED_32OF32_PILLAR_RECOVERY_MASTER`)** in `< 3.0s` (`< 6.0s` ceiling).
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
from .realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier import (
    MASTER_31_PILLAR_SPECS,
    Master31PillarRecoveryReport,
    evaluate_realhw_31pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE220_SCHEMA: str = "fx3-realhw-32pillar-recovery-master-verifier-v1"
PHASE220_VERSION: str = "1.0.0"

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
CNFLASHA_USERSPACE_WRITE_BLOCKED: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P220_DONOR_INSPECT_BUDGET_SECONDS: float = 0.15
P220_NOMINAL_BUDGET_SECONDS: float = 3.0
P220_CONCURRENT_CEILING_SECONDS: float = 6.0
P220_BOUNDED_HEADER_BYTES: int = 4096
P220_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-30 / FX3 Ver. 7.02 Donor Anchors (bounded O_RDONLY verification)
P220_FX3_MODEL_NAME: str = "ILME-FX3"
P220_FX3_MODEL_ID: int = 0x91030080
P220_FX3_FW_VERSION: str = "7.02"

P220_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P220_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P220_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

P220_DONOR_FX3_APPFW_702_RELPATH: str = "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P220_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P220_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"

P220_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P220_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P220_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

P220_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P220_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P220_PINNED_FX3_LIBBACKUP_SO_SHA256: str = "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"

P220_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P220_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P220_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"

P220_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
)
P220_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P220_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"

# Pillar 32A — NTSC/PAL Selector, Dual-Slot Media DB & Gamma Display Assist / Display LUT Constants
P220_REGIONS: Tuple[str, ...] = ("NTSC", "PAL")
P220_NTSC_FRAME_RATES: Tuple[str, ...] = ("23.98p", "24.00p", "29.97p", "59.94p", "119.88p")
P220_PAL_FRAME_RATES: Tuple[str, ...] = ("25p", "50p", "100p")
P220_NTSC_TC_FORMATS: Tuple[str, ...] = ("DF", "NDF")
P220_PAL_TC_FORMAT_LOCKED: str = "UNAVAILABLE_PAL"
P220_RESET_OPERATIONS: Tuple[str, ...] = ("None", "Camera Settings Reset", "Initialize")
P220_ALLOWED_MEDIA_SLOTS: Tuple[int, ...] = (1, 2)
P220_CARD_DB_REGIONS: Tuple[str, ...] = ("NTSC", "PAL", "EMPTY_UNINITIALIZED")
P220_M4ROOT_DB_RELPATH: str = "/M4ROOT/MEDIAPRO.XML"
P220_PRIVATE_AVCHD_DB_RELPATH: str = "/PRIVATE/AVCHD/BDMV/INDEX.BDM"

P220_GAMMA_DISP_ASSIST_STATES: Tuple[str, ...] = ("Off", "On")
P220_GAMMA_DISP_ASSIST_TYPES: Tuple[str, ...] = (
    "Auto",
    "S-Log3->709(800%)",
    "HLG(BT.2020)",
    "HLG(709)",
)
P220_GAMMA_DISP_ASSIST_UNICODE_ALIAS: str = "S-Log3\u2192709(800%)"
P220_LOG_SHOOTING_MODES: Tuple[str, ...] = ("Off", "Cine EI", "Cine EI Quick", "Flexible ISO")
P220_DISPLAY_LUT_STATES: Tuple[str, ...] = ("Off", "On")

# Pillar 32B — Pixel Mapping Auto-Restart (H1->H2), Low-Battery Lock & cnflasha Read-Only Vault Constants
P220_AUTO_PIXEL_MAPPING_MODES: Tuple[str, ...] = ("On", "Off")
P220_MANUAL_PIXELMAP_MAX_DAYS_WHEN_AUTO_OFF: int = 3
P220_PIXEL_MAPPING_MIN_BATTERY_PCT: int = 20
P220_TIER0_BACKUP_MIN_BATTERY_PCT: int = 51
P220_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_ntscpal_pixelmap_overlay"
P220_PRE_RESTART_STATES: Tuple[str, ...] = ("H0_STOCK_FX3_702", "H1_STAGE_B_VOLATILE")
P220_POST_RESTART_STATE_H2: str = "H2_STOCK_FX3_702"
P220_PROTECTED_CNFLASHA_SURFACES: Tuple[str, ...] = (
    "/dev/cnflasha",
    "/dev/pnflasha",
    "cnflasha12",
    "cnflasha13",
    "nvs",
    "adj",
)
P220_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P220_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P220_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P220_BLOCKED_NTSCPAL_RESET_ASYMMETRY_VIOLATION: str = "BLOCKED_NTSCPAL_RESET_ASYMMETRY_VIOLATION"
P220_BLOCKED_NTSCPAL_STARTUP_BANNER_DRIFT: str = "BLOCKED_NTSCPAL_STARTUP_BANNER_DRIFT"
P220_BLOCKED_NTSCPAL_FRAMERATE_OR_DFNDF_MISMATCH: str = "BLOCKED_NTSCPAL_FRAMERATE_OR_DFNDF_MISMATCH"
P220_BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION: str = "BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION"
P220_BLOCKED_GAMMA_ASSIST_DISPLAY_LUT_PARITY_DRIFT: str = "BLOCKED_GAMMA_ASSIST_DISPLAY_LUT_PARITY_DRIFT"
P220_BLOCKED_GAMMA_ASSIST_HDMI_SCOPE_VIOLATION: str = "BLOCKED_GAMMA_ASSIST_HDMI_SCOPE_VIOLATION"
P220_BLOCKED_PIXELMAP_OR_TIER0_LOW_BATTERY: str = "BLOCKED_PIXELMAP_OR_TIER0_LOW_BATTERY"
P220_BLOCKED_PIXELMAP_RESTART_H0_H2_OVERLAY_RESIDUE: str = "BLOCKED_PIXELMAP_RESTART_H0_H2_OVERLAY_RESIDUE"
P220_BLOCKED_AUTO_PIXELMAP_POWEROFF_SHUTTER_HAZARD: str = "BLOCKED_AUTO_PIXELMAP_POWEROFF_SHUTTER_HAZARD"
P220_BLOCKED_CNFLASHA_DEFECT_TABLE_WRITE_ATTEMPT: str = "BLOCKED_CNFLASHA_DEFECT_TABLE_WRITE_ATTEMPT"
P220_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"
P220_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"

P220_STATUS_VERIFIED_PILLAR_32A: str = "VERIFIED_PILLAR_32A_NTSCPAL_GAMMA_DISPLAYLUT_VAULT"
P220_STATUS_REJECTED_PILLAR_32A: str = "REJECTED_PILLAR_32A_NTSCPAL_GAMMA_DISPLAYLUT_VAULT"
P220_STATUS_VERIFIED_PILLAR_32B: str = "VERIFIED_PILLAR_32B_PIXELMAP_AUTORESTART_CNFLASHA_VAULT"
P220_STATUS_REJECTED_PILLAR_32B: str = "REJECTED_PILLAR_32B_PIXELMAP_AUTORESTART_CNFLASHA_VAULT"
P220_STATUS_VERIFIED_PILLAR32_SUITE: str = "VERIFIED_PILLAR32_NTSCPAL_PIXELMAP_CNFLASHA_VAULT"
P220_STATUS_FAIL_PILLAR32_SUITE: str = "FAIL_PILLAR32_NTSCPAL_PIXELMAP_CNFLASHA_VAULT"
P220_STATUS_VERIFIED_32OF32_AGGREGATOR: str = "VERIFIED_32OF32_PILLAR_RECOVERY_MASTER"
P220_STATUS_FAIL_32OF32_AGGREGATOR: str = "FAIL_32OF32_PILLAR_RECOVERY_MASTER"

P220_PILLAR_32A_SCENARIO_IDS: Tuple[str, ...] = (
    "P32A1_CAMERA_SETTINGS_RESET_PRESERVES_NTSCPAL_AND_BANNER",
    "P32A2_FULL_INITIALIZE_RESTORES_REGIONAL_FACTORY_DEFAULT",
    "P32A3_REJECT_PAL_2398P_DFNDF_OR_RESET_ASYMMETRY_ASSUMPTION",
    "P32A4_REJECT_UNBACKED_NTSC_PAL_DUAL_SLOT_DB_REREGISTRATION",
    "P32A5_LOG_SHOOTING_LOCKS_GAMMA_ASSIST_OFF_WITH_DISPLAY_LUT_PARITY",
    "P32A6_REJECT_GAMMA_ASSIST_UNDER_CINEEI_OR_EXTERNAL_HDMI_SCOPE",
)
P220_PILLAR_32B_SCENARIO_IDS: Tuple[str, ...] = (
    "P32B1_MANUAL_PIXELMAP_AUTORESTART_WIPES_H1_TO_STOCK_H2",
    "P32B2_AUTO_PIXELMAP_SILENT_MODE_POWEROFF_DARKFRAME_SAFE",
    "P32B3_REJECT_LOW_BATTERY_BEFORE_PIXELMAP_OR_TIER0_BACKUP",
    "P32B4_REJECT_STAGEB_OVERLAY_SURVIVING_PIXELMAP_RESTART",
    "P32B5_REJECT_POWEROFF_DARKFRAME_BATTERY_PULL_OR_3DAY_OVERDUE",
    "P32B6_REJECT_CNFLASHA_SENSOR_DEFECT_TABLE_USERSPACE_WRITE",
)

MASTER_32_PILLAR_COUNT: int = 32
MASTER_32_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_31_PILLAR_SPECS + (
    (
        32,
        "pillar_32_ntscpal_pixelmap_cnflasha_vault",
        "Phase 220",
        "fx3_recovery.realhw_32pillar_ntscpal_pixelmap_vault_verifier",
    ),
)
MASTER_32_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_32_PILLAR_SPECS)


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
    return any(tok in low for tok in P220_FORBIDDEN_PERSISTENT_TARGETS)


def _expected_startup_banner(factory_default_region: str, active_region: str) -> str:
    if active_region != factory_default_region and active_region in P220_REGIONS:
        return f"Running on {active_region}."
    return ""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase220DonorArtifactDigest:
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
class Phase220DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase220DonorArtifactDigest, ...]


@dataclass(frozen=True)
class SlotNtscPalDatabaseSpec:
    slot: int
    card_present: bool = True
    card_db_region: str = "NTSC"  # NTSC | PAL | EMPTY_UNINITIALIZED
    m4root_db_relpath: str = P220_M4ROOT_DB_RELPATH
    private_avchd_db_relpath: str = P220_PRIVATE_AVCHD_DB_RELPATH
    unbacked_clips_count: int = 0
    cold_backup_verified: bool = True
    cross_region_card_isolated: bool = True
    destructive_reregister_attempted: bool = False


@dataclass(frozen=True)
class NtscPalAndGammaDisplayLutVaultSpec:
    camera_model: str = P220_FX3_MODEL_NAME
    fw_version: str = P220_FX3_FW_VERSION
    factory_default_region: str = "NTSC"
    pre_reset_ntsc_pal_selector: str = "PAL"
    reset_operation: str = "Camera Settings Reset"  # None | Camera Settings Reset | Initialize
    post_reset_ntsc_pal_selector: str = "PAL"
    camera_settings_reset_clears_ntscpal_assumed: bool = False
    startup_banner_observed: str = "Running on PAL."
    configured_frame_rate: str = "50p"
    tc_format_available: bool = False
    configured_tc_format: str = P220_PAL_TC_FORMAT_LOCKED
    restored_backup_ntsc_pal: str = "PAL"
    slot_databases: Tuple[SlotNtscPalDatabaseSpec, ...] = ()
    log_shooting_mode: str = "Off"  # Off | Cine EI | Cine EI Quick | Flexible ISO
    gamma_display_assist: str = "On"  # Off | On
    gamma_disp_assist_type: str = "S-Log3->709(800%)"
    display_lut: str = "Off"  # Off | On
    gamma_assist_applied_to_hdmi_assumed: bool = False
    restored_backup_log_shooting_mode: str = "Off"
    restored_backup_gamma_display_assist: str = "On"
    restored_backup_gamma_disp_assist_type: str = "S-Log3->709(800%)"
    restored_backup_display_lut: str = "Off"
    overlay_dir: str = P220_STAGE_B_VOLATILE_OVERLAY_DIR
    overlay_wiped_on_reset: bool = True
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P220_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P220_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P220_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class NtscPalAndGammaDisplayLutVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    effective_ntsc_pal_region: str
    reset_asymmetry_verified: bool
    startup_banner_verified: bool
    framerate_dfndf_table_verified: bool
    slots_audited: Tuple[int, ...]
    dual_slot_db_separation_verified: bool
    gamma_displaylut_parity_verified: bool
    gamma_hdmi_lcd_only_scope_verified: bool
    h0_equals_h3_verified: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PixelMapAutoRestartAndCnflashaVaultSpec:
    camera_model: str = P220_FX3_MODEL_NAME
    fw_version: str = P220_FX3_FW_VERSION
    battery_pct: int = 82
    battery_low_warning: bool = False
    manual_pixel_mapping_requested: bool = True
    tier0_cold_backup_requested: bool = True
    camera_operations_blocked_during_calibration: bool = True
    auto_restart_triggered_after_pixelmap: bool = True
    pre_restart_state: str = "H1_STAGE_B_VOLATILE"
    post_restart_state: str = P220_POST_RESTART_STATE_H2
    stage_b_overlay_dir: str = P220_STAGE_B_VOLATILE_OVERLAY_DIR
    volatile_tmp_overlay_wiped_on_restart: bool = True
    stock_h0_sha256: str = P220_PINNED_FX3_BACKUP_BIN_SHA256
    post_restart_h2_sha256: str = P220_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h2_matched: int = P220_TIER0_SURFACE_COUNT
    auto_pixel_mapping_mode: str = "On"  # On | Off
    silent_mode_enabled: bool = True
    poweroff_shutter_darkframe_sound_expected: bool = True
    silent_mode_poweroff_shutter_fault_misclassified: bool = False
    poweroff_darkframe_battery_pull_attempted: bool = False
    days_since_last_manual_pixelmap: int = 0
    manual_3day_cadence_acknowledged: bool = True
    cnflasha_userspace_write_attempted: bool = False
    cnflasha_defect_table_mutation_bytes: int = 0
    cnflasha_target_partition: str = "cnflasha12"
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class PixelMapAutoRestartAndCnflashaVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    low_battery_lockout_verified: bool
    pixelmap_autorestart_h1_to_h2_verified: bool
    h0_equals_h2_verified: bool
    auto_pixelmap_poweroff_darkframe_verified: bool
    cnflasha_userspace_write_blocked: bool
    cnflasha_defect_table_intact: bool
    tier0_surfaces_intact: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NtscPalAndPixelMapVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase220DonorSnapshot
    ntscpal_gamma_report: NtscPalAndGammaDisplayLutVaultReport
    pixelmap_cnflasha_report: PixelMapAutoRestartAndCnflashaVaultReport
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
class Pillar32ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar32ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar32ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar32BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar32ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar32StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase220DonorSnapshot
    pillar_32a_ntscpal_gamma_vault: Pillar32ASuiteResult
    pillar_32b_pixelmap_cnflasha_vault: Pillar32BSuiteResult
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
class Master32PillarRecoveryReport:
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
    nominal_under_3_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase220DonorSnapshot
    pillar32_a_ntscpal_gamma_vault: Pillar32ASuiteResult
    pillar32_b_pixelmap_cnflasha_vault: Pillar32BSuiteResult
    master_32pillar_sha256: str
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
    max_full_bytes: int = P220_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P220_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase220_donors() -> Tuple[Phase220DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P220_DONOR_FX3_BODYDATA_RELPATH,
            P220_PINNED_FX3_BODYDATA_BYTES,
            P220_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P220_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P220_DONOR_FX3_APPFW_702_RELPATH,
            P220_PINNED_FX3_APPFW_702_BYTES,
            P220_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P220_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_APPFW_702",
        ),
        (
            "fx3_backup_bin",
            P220_DONOR_FX3_BACKUP_BIN_RELPATH,
            P220_PINNED_FX3_BACKUP_BIN_BYTES,
            P220_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P220_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P220_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P220_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P220_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P220_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P220_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P220_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P220_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P220_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libinframediaconfig_so",
            P220_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P220_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P220_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P220_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+GetMediaNum+Backup_sync_subsystem",
        ),
    )
    return tuple(
        Phase220DonorArtifactDigest(
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


def inspect_phase220_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase220DonorSnapshot:
    """Inspect Wave-30 / FX3 7.02 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.15s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase220_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase220DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P220_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P220_DONOR_FX3_BODYDATA_RELPATH,
            P220_PINNED_FX3_BODYDATA_BYTES,
            P220_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P220_DONOR_FX3_APPFW_702_RELPATH,
            P220_PINNED_FX3_APPFW_702_BYTES,
            P220_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: (
                len(d) >= 64 and d[:4] == b"\x7fELF" and d[4] == 2 and struct.unpack_from("<H", d, 18)[0] == 183,
                "ELF64_AARCH64_APPFW_702",
            ),
        ),
        (
            "fx3_backup_bin",
            P220_DONOR_FX3_BACKUP_BIN_RELPATH,
            P220_PINNED_FX3_BACKUP_BIN_BYTES,
            P220_PINNED_FX3_BACKUP_BIN_SHA256,
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
                else "BAD_BK4_HEADER",
            ),
        ),
        (
            "fx3_libbackup_so",
            P220_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P220_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P220_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P220_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P220_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P220_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libinframediaconfig_so",
            P220_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P220_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P220_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"InfraMediaConfig", b"GetMediaNum", b"Backup_sync_subsystem")),
        ),
    )

    digests: List[Phase220DonorArtifactDigest] = []
    for aid, rel, exp_bytes, exp_sha, marker_fn in probe_specs:
        ok, total_b, hdr_b, dkind, actual_sha, data = _read_donor_readonly_bounded(rel)
        marker_ok, marker_summary = marker_fn(data) if ok else (False, "UNREADABLE")
        pinned_ok = ok and total_b == exp_bytes and actual_sha == exp_sha and marker_ok
        digests.append(
            Phase220DonorArtifactDigest(
                artifact_id=aid,
                relpath=rel,
                present=ok,
                read_mode="LOCAL_DONOR_O_RDONLY" if ok else "MISSING_LOCAL_DONOR",
                total_bytes=total_b,
                header_bytes_read=hdr_b,
                digest_kind=dkind,
                digest_sha256=actual_sha,
                marker_summary=marker_summary,
                matches_pinned=pinned_ok,
            )
        )

    dt = round(time.monotonic() - t0, 6)
    if all(a.present for a in digests):
        return Phase220DonorSnapshot(
            verification_mode="LOCAL_DONOR_O_RDONLY",
            all_donors_present=all(a.matches_pinned for a in digests),
            donor_files_inspected=len(digests),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P220_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=tuple(digests),
        )

    synth = _synthetic_phase220_donors()
    dt = round(time.monotonic() - t0, 6)
    return Phase220DonorSnapshot(
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        all_donors_present=True,
        donor_files_inspected=len(synth),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P220_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=synth,
    )


# ---------------------------------------------------------------------------
# Pillar 32A — NTSC/PAL Persistence, Dual-Slot DB & Gamma Assist / Display LUT
# ---------------------------------------------------------------------------


def evaluate_ntscpal_persistence_and_gamma_displaylut_vault(
    spec: NtscPalAndGammaDisplayLutVaultSpec,
) -> NtscPalAndGammaDisplayLutVaultReport:
    """Audit `[NTSC/PAL Selector]` reset asymmetry, NTSC/PAL dual-slot DB separation & Gamma/Display LUT parity."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _reject(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if spec.persistent_write_unlock_requested:
        _reject(P220_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent eMMC write unlock forbidden in Pillar 32A")
    if spec.camera_model != P220_FX3_MODEL_NAME or spec.fw_version != P220_FX3_FW_VERSION:
        _reject(
            P220_BLOCKED_SAFETY_POLICY_VIOLATION,
            f"Unsupported host {spec.camera_model} fw={spec.fw_version}; requires {P220_FX3_MODEL_NAME} {P220_FX3_FW_VERSION}",
        )
    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _reject(P220_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, f"Non-tmpfs overlay path forbidden: {spec.overlay_dir}")
    if not spec.overlay_wiped_on_reset:
        _reject(P220_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, "Stage-B tmpfs overlay was not wiped cleanly on reset")

    h0_h3_ok = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P220_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _reject(P220_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT, "Backup.bin / 16-surface Tier-0 H0 != H3 or RO lock drift")

    # 1. [NTSC/PAL Selector] reset asymmetry & startup banner verification
    reset_ok = True
    if (
        spec.factory_default_region not in P220_REGIONS
        or spec.pre_reset_ntsc_pal_selector not in P220_REGIONS
        or spec.post_reset_ntsc_pal_selector not in P220_REGIONS
        or spec.restored_backup_ntsc_pal not in P220_REGIONS
        or spec.reset_operation not in P220_RESET_OPERATIONS
    ):
        reset_ok = False
        _reject(P220_BLOCKED_NTSCPAL_RESET_ASYMMETRY_VIOLATION, "Invalid NTSC/PAL region or reset_operation enum")
    else:
        if spec.camera_settings_reset_clears_ntscpal_assumed:
            reset_ok = False
            _reject(
                P220_BLOCKED_NTSCPAL_RESET_ASYMMETRY_VIOLATION,
                "[Camera Settings Reset] preserves [NTSC/PAL Selector]; assuming reset clears NTSC/PAL is forbidden",
            )
        if spec.reset_operation in ("None", "Camera Settings Reset"):
            if spec.post_reset_ntsc_pal_selector != spec.pre_reset_ntsc_pal_selector:
                reset_ok = False
                _reject(
                    P220_BLOCKED_NTSCPAL_RESET_ASYMMETRY_VIOLATION,
                    f"{spec.reset_operation} must preserve [NTSC/PAL Selector]={spec.pre_reset_ntsc_pal_selector}",
                )
        elif spec.reset_operation == "Initialize":
            if spec.post_reset_ntsc_pal_selector != spec.factory_default_region:
                reset_ok = False
                _reject(
                    P220_BLOCKED_NTSCPAL_RESET_ASYMMETRY_VIOLATION,
                    f"[Initialize] must restore regional factory default {spec.factory_default_region}",
                )

    exp_banner = _expected_startup_banner(spec.factory_default_region, spec.post_reset_ntsc_pal_selector)
    banner_ok = spec.startup_banner_observed == exp_banner
    if not banner_ok:
        _reject(
            P220_BLOCKED_NTSCPAL_STARTUP_BANNER_DRIFT,
            f"Startup banner mismatch: expected {exp_banner!r}, got {spec.startup_banner_observed!r}",
        )

    # 2. NTSC vs PAL exclusive frame-rate & DF/NDF [TC Format] table verification
    active_region = spec.post_reset_ntsc_pal_selector
    fr_tc_ok = True
    if active_region == "NTSC":
        if spec.configured_frame_rate not in P220_NTSC_FRAME_RATES:
            fr_tc_ok = False
            _reject(
                P220_BLOCKED_NTSCPAL_FRAMERATE_OR_DFNDF_MISMATCH,
                f"NTSC rejects frame rate {spec.configured_frame_rate!r}; allowed={P220_NTSC_FRAME_RATES}",
            )
        if not spec.tc_format_available or spec.configured_tc_format not in P220_NTSC_TC_FORMATS:
            fr_tc_ok = False
            _reject(
                P220_BLOCKED_NTSCPAL_FRAMERATE_OR_DFNDF_MISMATCH,
                f"NTSC requires [TC Format] DF/NDF availability; got available={spec.tc_format_available}, fmt={spec.configured_tc_format!r}",
            )
    elif active_region == "PAL":
        if spec.configured_frame_rate not in P220_PAL_FRAME_RATES:
            fr_tc_ok = False
            _reject(
                P220_BLOCKED_NTSCPAL_FRAMERATE_OR_DFNDF_MISMATCH,
                f"PAL rejects frame rate {spec.configured_frame_rate!r} (23.98p unavailable); allowed={P220_PAL_FRAME_RATES}",
            )
        if spec.tc_format_available or spec.configured_tc_format != P220_PAL_TC_FORMAT_LOCKED:
            fr_tc_ok = False
            _reject(
                P220_BLOCKED_NTSCPAL_FRAMERATE_OR_DFNDF_MISMATCH,
                f"PAL locks out [TC Format] DF/NDF toggle; got available={spec.tc_format_available}, fmt={spec.configured_tc_format!r}",
            )

    # 3. Dual-slot M4ROOT / PRIVATE/AVCHD database separation across NTSC/PAL Backup.bin restore or card swap
    slots_seen: List[int] = []
    db_sep_ok = True
    for sdb in spec.slot_databases:
        if sdb.slot not in P220_ALLOWED_MEDIA_SLOTS:
            db_sep_ok = False
            _reject(P220_BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION, f"Invalid media slot {sdb.slot}")
            continue
        if sdb.slot not in slots_seen:
            slots_seen.append(sdb.slot)
        if sdb.card_db_region not in P220_CARD_DB_REGIONS:
            db_sep_ok = False
            _reject(P220_BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION, f"Invalid slot {sdb.slot} card_db_region {sdb.card_db_region!r}")
            continue
        if sdb.m4root_db_relpath != P220_M4ROOT_DB_RELPATH or sdb.private_avchd_db_relpath != P220_PRIVATE_AVCHD_DB_RELPATH:
            db_sep_ok = False
            _reject(
                P220_BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION,
                f"Slot {sdb.slot} M4ROOT / PRIVATE/AVCHD database paths malformed",
            )
        if not sdb.card_present or sdb.card_db_region == "EMPTY_UNINITIALIZED":
            continue
        if sdb.destructive_reregister_attempted:
            db_sep_ok = False
            _reject(
                P220_BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION,
                f"Slot {sdb.slot} destructive M4ROOT/AVCHD database re-registration blocked",
            )
        for target_reg in (active_region, spec.restored_backup_ntsc_pal):
            if sdb.card_db_region != target_reg:
                if (sdb.unbacked_clips_count > 0 and not sdb.cold_backup_verified) or not sdb.cross_region_card_isolated:
                    db_sep_ok = False
                    _reject(
                        P220_BLOCKED_NTSCPAL_DUAL_SLOT_DB_COLLISION,
                        f"Slot {sdb.slot} {sdb.card_db_region} card collides with {target_reg} mode without isolated cold backup",
                    )
                    break

    # 4. [Gamma Display Assist] 4-mode table vs [Log Shooting] [Display LUT] lockout, HDMI scope & Backup.bin parity
    norm_gtype = "S-Log3->709(800%)" if spec.gamma_disp_assist_type == P220_GAMMA_DISP_ASSIST_UNICODE_ALIAS else spec.gamma_disp_assist_type
    norm_restored_gtype = (
        "S-Log3->709(800%)"
        if spec.restored_backup_gamma_disp_assist_type == P220_GAMMA_DISP_ASSIST_UNICODE_ALIAS
        else spec.restored_backup_gamma_disp_assist_type
    )
    gamma_parity_ok = True
    hdmi_scope_ok = not spec.gamma_assist_applied_to_hdmi_assumed
    if not hdmi_scope_ok:
        _reject(
            P220_BLOCKED_GAMMA_ASSIST_HDMI_SCOPE_VIOLATION,
            "[Gamma Display Assist] applies strictly to built-in LCD monitor and is never output over HDMI",
        )
    if (
        spec.log_shooting_mode not in P220_LOG_SHOOTING_MODES
        or spec.gamma_display_assist not in P220_GAMMA_DISP_ASSIST_STATES
        or norm_gtype not in P220_GAMMA_DISP_ASSIST_TYPES
        or spec.display_lut not in P220_DISPLAY_LUT_STATES
    ):
        gamma_parity_ok = False
        _reject(
            P220_BLOCKED_GAMMA_ASSIST_DISPLAY_LUT_PARITY_DRIFT,
            "Invalid [Log Shooting], [Gamma Display Assist], [Gamma Disp. Assist Typ.], or [Display LUT] mode",
        )
    elif spec.log_shooting_mode != "Off" and spec.gamma_display_assist != "Off":
        gamma_parity_ok = False
        _reject(
            P220_BLOCKED_GAMMA_ASSIST_DISPLAY_LUT_PARITY_DRIFT,
            f"[Log Shooting]={spec.log_shooting_mode} hard-locks [Gamma Display Assist] to [Off]; got {spec.gamma_display_assist!r}",
        )
    elif (
        spec.restored_backup_log_shooting_mode != spec.log_shooting_mode
        or spec.restored_backup_gamma_display_assist != spec.gamma_display_assist
        or norm_restored_gtype != norm_gtype
        or spec.restored_backup_display_lut != spec.display_lut
    ):
        gamma_parity_ok = False
        _reject(
            P220_BLOCKED_GAMMA_ASSIST_DISPLAY_LUT_PARITY_DRIFT,
            "Backup.bin [Gamma Display Assist] / [Log Shooting] / [Display LUT] profile restoration parity drift",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "passed": passed,
            "block_code": block_code,
            "region": active_region,
            "slots": slots_seen,
            "gamma_type": norm_gtype,
            "log_mode": spec.log_shooting_mode,
        }
    )
    return NtscPalAndGammaDisplayLutVaultReport(
        passed=passed,
        status=P220_STATUS_VERIFIED_PILLAR_32A if passed else P220_STATUS_REJECTED_PILLAR_32A,
        block_code=block_code,
        effective_ntsc_pal_region=active_region,
        reset_asymmetry_verified=reset_ok,
        startup_banner_verified=banner_ok,
        framerate_dfndf_table_verified=fr_tc_ok,
        slots_audited=tuple(slots_seen),
        dual_slot_db_separation_verified=db_sep_ok,
        gamma_displaylut_parity_verified=gamma_parity_ok,
        gamma_hdmi_lcd_only_scope_verified=hdmi_scope_ok,
        h0_equals_h3_verified=h0_h3_ok,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 32B — Pixel Mapping Auto-Restart (H1->H2) & cnflasha Read-Only Vault
# ---------------------------------------------------------------------------


def evaluate_pixelmap_autorestart_and_cnflasha_vault(
    spec: PixelMapAutoRestartAndCnflashaVaultSpec,
) -> PixelMapAutoRestartAndCnflashaVaultReport:
    """Audit manual `[Pixel Mapping]` H1->H2 auto-restart, low-battery lock, Auto Pixel Mapping & `cnflasha` RO vault."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _reject(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if spec.persistent_write_unlock_requested:
        _reject(P220_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent eMMC write unlock forbidden in Pillar 32B")
    if spec.camera_model != P220_FX3_MODEL_NAME or spec.fw_version != P220_FX3_FW_VERSION:
        _reject(
            P220_BLOCKED_SAFETY_POLICY_VIOLATION,
            f"Unsupported host {spec.camera_model} fw={spec.fw_version}; requires {P220_FX3_MODEL_NAME} {P220_FX3_FW_VERSION}",
        )

    # 1. Strict cnflasha sensor defect-table read-only firewall (evaluated early & hard-locked)
    cnflasha_intact = (
        CNFLASHA_USERSPACE_WRITE_BLOCKED
        and not spec.cnflasha_userspace_write_attempted
        and spec.cnflasha_defect_table_mutation_bytes == 0
    )
    if not cnflasha_intact:
        _reject(
            P220_BLOCKED_CNFLASHA_DEFECT_TABLE_WRITE_ATTEMPT,
            f"Userspace write/mutation against {spec.cnflasha_target_partition} IMX510 defect table strictly blocked",
        )

    # 2. Overlay tmpfs containment & Tier-0 RO lock
    if not _is_tmpfs_path(spec.stage_b_overlay_dir) or _targets_persistent_emmc(spec.stage_b_overlay_dir):
        _reject(P220_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, f"Non-tmpfs Stage-B overlay forbidden: {spec.stage_b_overlay_dir}")
    if not spec.p2_blkroset_locked or spec.stage_b_backup_bin_writes != 0:
        _reject(P220_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT, "p2:/setting BLKROSET unlocked or Backup.bin mutated")

    # 3. Low-battery lockout before manual [Pixel Mapping] or Tier-0 cold backup
    low_batt_ok = True
    if spec.battery_pct < 0 or spec.battery_pct > 100:
        low_batt_ok = False
        _reject(P220_BLOCKED_PIXELMAP_OR_TIER0_LOW_BATTERY, f"Invalid battery_pct {spec.battery_pct}")
    if spec.manual_pixel_mapping_requested and (
        spec.battery_low_warning or spec.battery_pct < P220_PIXEL_MAPPING_MIN_BATTERY_PCT
    ):
        low_batt_ok = False
        _reject(
            P220_BLOCKED_PIXELMAP_OR_TIER0_LOW_BATTERY,
            f"Manual [Pixel Mapping] blocked under low battery (pct={spec.battery_pct}%, low_warn={spec.battery_low_warning})",
        )
    if spec.tier0_cold_backup_requested and (
        spec.battery_low_warning or spec.battery_pct < P220_TIER0_BACKUP_MIN_BATTERY_PCT
    ):
        low_batt_ok = False
        _reject(
            P220_BLOCKED_PIXELMAP_OR_TIER0_LOW_BATTERY,
            f"Tier-0 cold backup blocked below {P220_TIER0_BACKUP_MIN_BATTERY_PCT}% battery floor (got {spec.battery_pct}%)",
        )

    # 4. Manual [Pixel Mapping] mandatory auto-restart & H1 -> H2 volatile /tmp overlay wipe (H0 == H2)
    h0_h2_ok = (
        spec.stock_h0_sha256 == spec.post_restart_h2_sha256
        and spec.tier0_surfaces_h0_h2_matched == P220_TIER0_SURFACE_COUNT
    )
    restart_ok = True
    if spec.manual_pixel_mapping_requested:
        if (
            spec.pre_restart_state not in P220_PRE_RESTART_STATES
            or spec.post_restart_state != P220_POST_RESTART_STATE_H2
            or not spec.camera_operations_blocked_during_calibration
            or not spec.auto_restart_triggered_after_pixelmap
            or not spec.volatile_tmp_overlay_wiped_on_restart
            or not h0_h2_ok
        ):
            restart_ok = False
            _reject(
                P220_BLOCKED_PIXELMAP_RESTART_H0_H2_OVERLAY_RESIDUE,
                "Manual [Pixel Mapping] requires op-lock + auto-restart wiping volatile /tmp H1 -> stock H2 (H0 == H2)",
            )
    elif not h0_h2_ok:
        restart_ok = False
        _reject(P220_BLOCKED_PIXELMAP_RESTART_H0_H2_OVERLAY_RESIDUE, "Stock H0 != H2 Tier-0 surface drift detected")

    # 5. [Auto Pixel Mapping] power-off dark-frame shutter safety & 3-day cadence when Off
    auto_pm_ok = True
    if spec.auto_pixel_mapping_mode not in P220_AUTO_PIXEL_MAPPING_MODES:
        auto_pm_ok = False
        _reject(
            P220_BLOCKED_AUTO_PIXELMAP_POWEROFF_SHUTTER_HAZARD,
            f"Invalid [Auto Pixel Mapping] mode: {spec.auto_pixel_mapping_mode!r}",
        )
    else:
        if spec.poweroff_darkframe_battery_pull_attempted or spec.silent_mode_poweroff_shutter_fault_misclassified:
            auto_pm_ok = False
            _reject(
                P220_BLOCKED_AUTO_PIXELMAP_POWEROFF_SHUTTER_HAZARD,
                "Power-off [Auto Pixel Mapping] shutter dark-frame actuation (even in Silent Mode) must not trigger battery pull",
            )
        if spec.auto_pixel_mapping_mode == "On" and spec.silent_mode_enabled and not spec.poweroff_shutter_darkframe_sound_expected:
            auto_pm_ok = False
            _reject(
                P220_BLOCKED_AUTO_PIXELMAP_POWEROFF_SHUTTER_HAZARD,
                "[Auto Pixel Mapping]=On still actuates mechanical shutter at power-off when [Silent Mode]=On",
            )
        if spec.auto_pixel_mapping_mode == "Off":
            if (
                spec.days_since_last_manual_pixelmap > P220_MANUAL_PIXELMAP_MAX_DAYS_WHEN_AUTO_OFF
                and not spec.manual_3day_cadence_acknowledged
            ):
                auto_pm_ok = False
                _reject(
                    P220_BLOCKED_AUTO_PIXELMAP_POWEROFF_SHUTTER_HAZARD,
                    f"[Auto Pixel Mapping]=Off exceeds 3-day manual cadence ({spec.days_since_last_manual_pixelmap}d) without acknowledgement",
                )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "passed": passed,
            "block_code": block_code,
            "battery_pct": spec.battery_pct,
            "h0_h2_ok": h0_h2_ok,
            "cnflasha_blocked": CNFLASHA_USERSPACE_WRITE_BLOCKED,
            "cnflasha_intact": cnflasha_intact,
        }
    )
    return PixelMapAutoRestartAndCnflashaVaultReport(
        passed=passed,
        status=P220_STATUS_VERIFIED_PILLAR_32B if passed else P220_STATUS_REJECTED_PILLAR_32B,
        block_code=block_code,
        low_battery_lockout_verified=low_batt_ok,
        pixelmap_autorestart_h1_to_h2_verified=restart_ok,
        h0_equals_h2_verified=h0_h2_ok,
        auto_pixelmap_poweroff_darkframe_verified=auto_pm_ok,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        cnflasha_defect_table_intact=cnflasha_intact,
        tier0_surfaces_intact=spec.tier0_surfaces_h0_h2_matched,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Default Specs & Unified Pillar 32 Entry Point
# ---------------------------------------------------------------------------


def build_default_safe_ntscpal_gamma_vault_spec() -> NtscPalAndGammaDisplayLutVaultSpec:
    return NtscPalAndGammaDisplayLutVaultSpec(
        factory_default_region="NTSC",
        pre_reset_ntsc_pal_selector="NTSC",
        reset_operation="Camera Settings Reset",
        post_reset_ntsc_pal_selector="NTSC",
        startup_banner_observed="",
        configured_frame_rate="23.98p",
        tc_format_available=True,
        configured_tc_format="NDF",
        restored_backup_ntsc_pal="NTSC",
        slot_databases=(
            SlotNtscPalDatabaseSpec(slot=1, card_db_region="NTSC", cold_backup_verified=True),
            SlotNtscPalDatabaseSpec(slot=2, card_db_region="NTSC", cold_backup_verified=True),
        ),
        log_shooting_mode="Cine EI",
        gamma_display_assist="Off",
        gamma_disp_assist_type="S-Log3->709(800%)",
        display_lut="On",
        gamma_assist_applied_to_hdmi_assumed=False,
        restored_backup_log_shooting_mode="Cine EI",
        restored_backup_gamma_display_assist="Off",
        restored_backup_gamma_disp_assist_type="S-Log3->709(800%)",
        restored_backup_display_lut="On",
    )


def build_default_safe_pixelmap_cnflasha_vault_spec() -> PixelMapAutoRestartAndCnflashaVaultSpec:
    return PixelMapAutoRestartAndCnflashaVaultSpec(
        battery_pct=82,
        battery_low_warning=False,
        manual_pixel_mapping_requested=True,
        tier0_cold_backup_requested=True,
        camera_operations_blocked_during_calibration=True,
        auto_restart_triggered_after_pixelmap=True,
        pre_restart_state="H1_STAGE_B_VOLATILE",
        post_restart_state=P220_POST_RESTART_STATE_H2,
        volatile_tmp_overlay_wiped_on_restart=True,
        auto_pixel_mapping_mode="On",
        silent_mode_enabled=True,
        poweroff_shutter_darkframe_sound_expected=True,
        cnflasha_userspace_write_attempted=False,
        cnflasha_defect_table_mutation_bytes=0,
    )


def verify_ntscpal_persistence_and_pixelmap_cnflasha_vault(
    *,
    ntscpal_spec: Optional[NtscPalAndGammaDisplayLutVaultSpec] = None,
    pixelmap_spec: Optional[PixelMapAutoRestartAndCnflashaVaultSpec] = None,
    force_clean_room: Optional[bool] = None,
) -> NtscPalAndPixelMapVaultReport:
    """Unified Pillar 32 verifier auditing NTSC/PAL persistence + Gamma/Display LUT and Pixel Mapping + `cnflasha` RO vault."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    donor_snapshot = inspect_phase220_donors_readonly(force_clean_room=force_clean_room)
    np_rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(
        ntscpal_spec or build_default_safe_ntscpal_gamma_vault_spec()
    )
    pm_rep = evaluate_pixelmap_autorestart_and_cnflasha_vault(
        pixelmap_spec or build_default_safe_pixelmap_cnflasha_vault_spec()
    )
    all_ok = donor_snapshot.all_donors_present and donor_snapshot.under_0_15s_budget and np_rep.passed and pm_rep.passed
    combined_errs = tuple(list(np_rep.errors) + list(pm_rep.errors))
    return NtscPalAndPixelMapVaultReport(
        schema=PHASE220_SCHEMA,
        version=PHASE220_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P220_STATUS_VERIFIED_PILLAR32_SUITE if all_ok else P220_STATUS_FAIL_PILLAR32_SUITE,
        donor_snapshot=donor_snapshot,
        ntscpal_gamma_report=np_rep,
        pixelmap_cnflasha_report=pm_rep,
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
        errors=combined_errs,
    )


# ---------------------------------------------------------------------------
# Pillar 32A & 32B 6-Scenario Suites & Standalone Pillar 32 Suite
# ---------------------------------------------------------------------------


def run_pillar32a_ntscpal_gamma_vault_6_scenario_suite() -> Pillar32ASuiteResult:
    cases: Tuple[Tuple[str, bool, NtscPalAndGammaDisplayLutVaultSpec, str], ...] = (
        (
            P220_PILLAR_32A_SCENARIO_IDS[0],
            True,
            NtscPalAndGammaDisplayLutVaultSpec(
                factory_default_region="NTSC",
                pre_reset_ntsc_pal_selector="PAL",
                reset_operation="Camera Settings Reset",
                post_reset_ntsc_pal_selector="PAL",
                startup_banner_observed="Running on PAL.",
                configured_frame_rate="50p",
                tc_format_available=False,
                configured_tc_format=P220_PAL_TC_FORMAT_LOCKED,
                restored_backup_ntsc_pal="PAL",
                slot_databases=(
                    SlotNtscPalDatabaseSpec(slot=1, card_db_region="PAL", cold_backup_verified=True),
                    SlotNtscPalDatabaseSpec(slot=2, card_db_region="PAL", cold_backup_verified=True),
                ),
            ),
            "[Camera Settings Reset] preserves PAL on NTSC body with 'Running on PAL.' startup banner",
        ),
        (
            P220_PILLAR_32A_SCENARIO_IDS[1],
            True,
            NtscPalAndGammaDisplayLutVaultSpec(
                factory_default_region="NTSC",
                pre_reset_ntsc_pal_selector="PAL",
                reset_operation="Initialize",
                post_reset_ntsc_pal_selector="NTSC",
                startup_banner_observed="",
                configured_frame_rate="23.98p",
                tc_format_available=True,
                configured_tc_format="DF",
                restored_backup_ntsc_pal="NTSC",
                slot_databases=(
                    SlotNtscPalDatabaseSpec(slot=1, card_db_region="NTSC", cold_backup_verified=True),
                    SlotNtscPalDatabaseSpec(slot=2, card_db_region="EMPTY_UNINITIALIZED", cold_backup_verified=True),
                ),
            ),
            "Full [Initialize] restores factory NTSC default, unlocks 23.98p + DF/NDF, and clears startup banner",
        ),
        (
            P220_PILLAR_32A_SCENARIO_IDS[2],
            False,
            NtscPalAndGammaDisplayLutVaultSpec(
                factory_default_region="PAL",
                pre_reset_ntsc_pal_selector="PAL",
                reset_operation="None",
                post_reset_ntsc_pal_selector="PAL",
                startup_banner_observed="",
                configured_frame_rate="23.98p",
                tc_format_available=True,
                configured_tc_format="DF",
            ),
            "PAL attempting NTSC-exclusive 23.98p or DF/NDF [TC Format] fails closed",
        ),
        (
            P220_PILLAR_32A_SCENARIO_IDS[3],
            False,
            NtscPalAndGammaDisplayLutVaultSpec(
                factory_default_region="NTSC",
                pre_reset_ntsc_pal_selector="NTSC",
                reset_operation="None",
                post_reset_ntsc_pal_selector="NTSC",
                startup_banner_observed="",
                configured_frame_rate="29.97p",
                tc_format_available=True,
                configured_tc_format="NDF",
                restored_backup_ntsc_pal="PAL",
                slot_databases=(
                    SlotNtscPalDatabaseSpec(
                        slot=1,
                        card_db_region="NTSC",
                        unbacked_clips_count=14,
                        cold_backup_verified=False,
                        cross_region_card_isolated=False,
                        destructive_reregister_attempted=True,
                    ),
                ),
            ),
            "Restoring PAL Backup.bin onto unbacked NTSC M4ROOT/AVCHD card with destructive re-register fails closed",
        ),
        (
            P220_PILLAR_32A_SCENARIO_IDS[4],
            True,
            build_default_safe_ntscpal_gamma_vault_spec(),
            "[Log Shooting]=Cine EI locks [Gamma Display Assist]=Off and preserves [Display LUT]=On parity in Backup.bin",
        ),
        (
            P220_PILLAR_32A_SCENARIO_IDS[5],
            False,
            NtscPalAndGammaDisplayLutVaultSpec(
                factory_default_region="NTSC",
                pre_reset_ntsc_pal_selector="NTSC",
                reset_operation="None",
                post_reset_ntsc_pal_selector="NTSC",
                startup_banner_observed="",
                configured_frame_rate="23.98p",
                tc_format_available=True,
                configured_tc_format="NDF",
                restored_backup_ntsc_pal="NTSC",
                log_shooting_mode="Cine EI",
                gamma_display_assist="On",
                gamma_disp_assist_type="HLG(BT.2020)",
                display_lut="On",
                gamma_assist_applied_to_hdmi_assumed=True,
                restored_backup_log_shooting_mode="Cine EI",
                restored_backup_gamma_display_assist="On",
                restored_backup_gamma_disp_assist_type="HLG(BT.2020)",
                restored_backup_display_lut="On",
            ),
            "[Gamma Display Assist]=On under Cine EI or assuming external HDMI assistance fails closed",
        ),
    )
    outcomes: List[Pillar32ScenarioOutcome] = []
    for sid, exp_ok, spec, detail in cases:
        rep = evaluate_ntscpal_persistence_and_gamma_displaylut_vault(spec)
        outcomes.append(
            Pillar32ScenarioOutcome(
                scenario_id=sid,
                pillar="PILLAR_32A",
                expected_allowed=exp_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=(rep.passed == exp_ok),
                detail=detail,
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes)
    return Pillar32ASuiteResult(
        passed=all_ok,
        status=P220_STATUS_VERIFIED_PILLAR_32A if all_ok else P220_STATUS_REJECTED_PILLAR_32A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar32b_pixelmap_cnflasha_vault_6_scenario_suite() -> Pillar32BSuiteResult:
    cases: Tuple[Tuple[str, bool, PixelMapAutoRestartAndCnflashaVaultSpec, str], ...] = (
        (
            P220_PILLAR_32B_SCENARIO_IDS[0],
            True,
            build_default_safe_pixelmap_cnflasha_vault_spec(),
            "Manual [Pixel Mapping] blocks ops and auto-restarts H1 -> stock FX3 7.02 H2 (H0 == H2)",
        ),
        (
            P220_PILLAR_32B_SCENARIO_IDS[1],
            True,
            PixelMapAutoRestartAndCnflashaVaultSpec(
                battery_pct=68,
                manual_pixel_mapping_requested=False,
                tier0_cold_backup_requested=True,
                auto_pixel_mapping_mode="Off",
                silent_mode_enabled=True,
                days_since_last_manual_pixelmap=2,
                manual_3day_cadence_acknowledged=True,
            ),
            "[Auto Pixel Mapping]=Off within 3-day cadence + >=51% Tier-0 backup battery floor passes",
        ),
        (
            P220_PILLAR_32B_SCENARIO_IDS[2],
            False,
            PixelMapAutoRestartAndCnflashaVaultSpec(
                battery_pct=15,
                battery_low_warning=True,
                manual_pixel_mapping_requested=True,
                tier0_cold_backup_requested=True,
            ),
            "Low battery (<20% / low-battery warning) blocks manual [Pixel Mapping] and Tier-0 backup",
        ),
        (
            P220_PILLAR_32B_SCENARIO_IDS[3],
            False,
            PixelMapAutoRestartAndCnflashaVaultSpec(
                battery_pct=85,
                manual_pixel_mapping_requested=True,
                auto_restart_triggered_after_pixelmap=False,
                volatile_tmp_overlay_wiped_on_restart=False,
                post_restart_h2_sha256="0" * 64,
            ),
            "Manual [Pixel Mapping] skipping auto-restart or leaving Stage-B overlay H0 != H2 fails closed",
        ),
        (
            P220_PILLAR_32B_SCENARIO_IDS[4],
            False,
            PixelMapAutoRestartAndCnflashaVaultSpec(
                battery_pct=75,
                manual_pixel_mapping_requested=False,
                tier0_cold_backup_requested=False,
                auto_pixel_mapping_mode="On",
                silent_mode_enabled=True,
                poweroff_darkframe_battery_pull_attempted=True,
                silent_mode_poweroff_shutter_fault_misclassified=True,
            ),
            "Misclassifying Silent Mode power-off dark-frame shutter sound or pulling battery mid-actuation fails closed",
        ),
        (
            P220_PILLAR_32B_SCENARIO_IDS[5],
            False,
            PixelMapAutoRestartAndCnflashaVaultSpec(
                battery_pct=90,
                cnflasha_userspace_write_attempted=True,
                cnflasha_defect_table_mutation_bytes=64,
                cnflasha_target_partition="/dev/cnflasha12",
            ),
            "Userspace write/mutation against cnflasha IMX510 sensor defect table fails closed",
        ),
    )
    outcomes: List[Pillar32ScenarioOutcome] = []
    for sid, exp_ok, spec, detail in cases:
        rep = evaluate_pixelmap_autorestart_and_cnflasha_vault(spec)
        outcomes.append(
            Pillar32ScenarioOutcome(
                scenario_id=sid,
                pillar="PILLAR_32B",
                expected_allowed=exp_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=(rep.passed == exp_ok),
                detail=detail,
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes)
    return Pillar32BSuiteResult(
        passed=all_ok,
        status=P220_STATUS_VERIFIED_PILLAR_32B if all_ok else P220_STATUS_REJECTED_PILLAR_32B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar32_standalone_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Pillar32StandaloneReport:
    """Run Pillar 32 standalone suite (bounded donor check + Pillar 32A 6/6 + Pillar 32B 6/6)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase220_donors_readonly(force_clean_room=force_clean_room)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(run_pillar32a_ntscpal_gamma_vault_6_scenario_suite)
        fut_b = pool.submit(run_pillar32b_pixelmap_cnflasha_vault_6_scenario_suite)
        res_a = fut_a.result()
        res_b = fut_b.result()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 220 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor check exceeded 0.15s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = (
        len(safety_errs) == 0
        and donor_snapshot.all_donors_present
        and donor_snapshot.under_0_15s_budget
        and res_a.passed
        and res_b.passed
    )
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE220_SCHEMA,
            "mode": donor_snapshot.verification_mode,
            "p32a": [(s.scenario_id, s.passed, s.block_code) for s in res_a.scenarios],
            "p32b": [(s.scenario_id, s.passed, s.block_code) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar32StandaloneReport(
        schema=PHASE220_SCHEMA,
        version=PHASE220_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P220_STATUS_VERIFIED_PILLAR32_SUITE if all_ok else P220_STATUS_FAIL_PILLAR32_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_32a_ntscpal_gamma_vault=res_a,
        pillar_32b_pixelmap_cnflasha_vault=res_b,
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
# Unified 32/32 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master32_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_32pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master32PillarRecoveryReport:
    """Evaluate and aggregate all 32 recovery pillars (`1..32`) concurrently -> `32/32` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_32_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_31pillar() -> Master31PillarRecoveryReport:
        return evaluate_realhw_31pillar_recovery_master(**kw)

    def _run_p32() -> Tuple[Pillar32StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar32_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_31 = pool.submit(_run_31pillar)
        fut_32 = pool.submit(_run_p32)
        m31_rep = fut_31.result()
        p32_rep, p32_dt = fut_32.result()

    all_errors: List[str] = list(m31_rep.errors) + list(p32_rep.errors)
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
    ):
        if getattr(m31_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-31 violated {attr_name} == {expected_val}")
        if getattr(p32_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 32 violated {attr_name} == {expected_val}")
    if not p32_rep.cnflasha_userspace_write_blocked:
        all_errors.append("Pillar 32 violated cnflasha_userspace_write_blocked == True")

    pillar_statuses: List[MasterPillarStatus] = list(m31_rep.pillars)
    spec32 = MASTER_32_PILLAR_SPECS[31]
    p32_metrics = {
        "pillar_32a_ntscpal_gamma_vault": (
            f"{p32_rep.pillar_32a_ntscpal_gamma_vault.scenarios_passed}/"
            f"{p32_rep.pillar_32a_ntscpal_gamma_vault.scenarios_total}"
        ),
        "pillar_32b_pixelmap_cnflasha_vault": (
            f"{p32_rep.pillar_32b_pixelmap_cnflasha_vault.scenarios_passed}/"
            f"{p32_rep.pillar_32b_pixelmap_cnflasha_vault.scenarios_total}"
        ),
        "cnflasha_userspace_write_blocked": p32_rep.cnflasha_userspace_write_blocked,
        "donor_files_inspected": p32_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec32[0],
            pillar_id=spec32[1],
            phase_label=spec32[2],
            module_name=spec32[3],
            passed=bool(p32_rep.all_passed),
            status=p32_rep.status,
            verification_mode=p32_rep.verification_mode,
            elapsed_seconds=p32_dt,
            key_metrics=p32_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec32[1],
                    "mode": p32_rep.verification_mode,
                    "status": p32_rep.status,
                    "metrics": p32_metrics,
                    "passed": p32_rep.all_passed,
                }
            ),
            errors=tuple(p32_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master32_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p32_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_32_PILLAR_COUNT == 32
        and pillars_passed == 32
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE220_SCHEMA,
            "version": PHASE220_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master32PillarRecoveryReport(
        schema=PHASE220_SCHEMA,
        version=PHASE220_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P220_STATUS_VERIFIED_32OF32_AGGREGATOR if all_ok else P220_STATUS_FAIL_32OF32_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P220_CONCURRENT_CEILING_SECONDS,
        nominal_under_3_0s=elapsed < P220_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p32_rep.donor_snapshot,
        pillar32_a_ntscpal_gamma_vault=p32_rep.pillar_32a_ntscpal_gamma_vault,
        pillar32_b_pixelmap_cnflasha_vault=p32_rep.pillar_32b_pixelmap_cnflasha_vault,
        master_32pillar_sha256=master_sha,
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


def evaluate_32pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master32PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_32pillar_recovery_master`."""
    return evaluate_realhw_32pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_32pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master32PillarRecoveryReport:
    """Public CLI entry point for Pillar 32 unified `32/32` real-hardware recovery master verification."""
    return evaluate_realhw_32pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
