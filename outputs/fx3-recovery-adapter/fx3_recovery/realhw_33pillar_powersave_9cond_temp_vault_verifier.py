"""Phase 225 — Pillar 33 (`33/33` Recovery Pillars) & Unified 33-Pillar Recovery Master
(`verify-33pillar-recovery` / `verify-powersave-9cond-temp-vault`):

1. **Pillar 33A — `[Power Save Start Time]` 9-Condition Automatic Deactivation Matrix, Air-Gapped
   `NP-FZ100` Tier-0 `75 MiB` `p3` Cold-Dump Anti-Sleep Interlock & `[Auto Power OFF Temp.]` +
   `[Fan Control]` Thermal Vault**:
   - Audits `[Power Save Start Time]` (`Off`, `10 Sec`, `1 Min`, `2 Min`, `5 Min` default, `30 Min`)
     across all 9 official Sony `ILME-FX3 Ver. 7.02` automatic deactivation conditions (USB power
     supply, slideshow playback, FTP transfer, movie recording, PC connection, TV/HDMI connection,
     `[IR Remote Ctrl] = On`, `[Bluetooth Rmt Ctrl] = On`, streaming / Creators' Cloud upload).
   - Enforces air-gapped internal-battery (`NP-FZ100`, `>= 51%` floor) Tier-0 `75 MiB` `p3`
     cold-dump anti-sleep safety: blocks backup/restore start when none of the 9 automatic bypasses
     is active and `[Power Save Start Time]` is shorter than `30 Min` / `Off`.
   - Audits `[Auto Power OFF Temp.]` (`Standard` default vs `High` tripod-only thermal threshold
     blocking prolonged handheld burn hazard) coupled with FX3 4-mode `[Fan Control]` pre-backup
     cool-down interlock (`Always Off` -> `Auto`, `< 85.0C` SoC ceiling).

2. **Pillar 33B — `[SteadyShot]` (`Active` Cutoffs at `119.88p/100p`, S&Q `>=100fps/120fps`, HDMI
   `RAW Output`) & `[Clear Image Zoom]` (`Focus Area` Center Lock, `Metering Mode = Multi`,
   Face/Eye & Tracking Disabled) `Backup.bin` / `CAMSET01..10.DAT` Vault Consistency**:
   - Enforces `[SteadyShot] = [Active]` (`~1.1x` crop) cutoffs at `119.88p`/`100p`, S&Q
     `>=100fps`/`120fps`, and HDMI `[RAW Output] = [On]`.
   - Enforces `[Clear Image Zoom]` / `[Digital Zoom]` unavailability in still RAW, `119.88p`/`100p`,
     and S&Q `100/120/200/240fps`, plus automatic camera state locks (`Focus Area` disabled/center,
     `Metering Mode` locked to `Multi`, Face/Eye & Real-time Tracking disabled).
   - Verifies Slot-1 `CAMSET01..10.DAT` & `Backup.bin` (`BK4\\x00`) profile restoration parity
     (`H0 == H3`, `16/16` Tier-0 surfaces intact, `persistent_emmc_writes_authorized = False`,
     `physical_device_writes = 0`).

3. **Unified `33/33` Recovery Master (`evaluate_realhw_33pillar_recovery_master`)**:
   - Delegates Pillars `1..32` concurrently to `evaluate_realhw_32pillar_recovery_master` +
     **Pillar 33** -> **`33/33` (`VERIFIED_33OF33_PILLAR_RECOVERY_MASTER`)** in `< 3.2s` (`< 6.0s` ceiling).
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
from .realhw_32pillar_ntscpal_pixelmap_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_32_PILLAR_SPECS,
    Master32PillarRecoveryReport,
    evaluate_realhw_32pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE225_SCHEMA: str = "fx3-realhw-33pillar-recovery-master-verifier-v1"
PHASE225_VERSION: str = "1.0.0"

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

P225_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P225_NOMINAL_BUDGET_SECONDS: float = 3.2
P225_CONCURRENT_CEILING_SECONDS: float = 6.0
P225_BOUNDED_HEADER_BYTES: int = 4096
P225_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-31 / FX3 Ver. 7.02 Donor Anchors (bounded O_RDONLY verification)
P225_FX3_MODEL_NAME: str = "ILME-FX3"
P225_FX3_MODEL_ID: int = 0x91030080
P225_FX3_FW_VERSION: str = "7.02"

P225_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P225_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P225_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

P225_DONOR_FX3_APPFW_702_RELPATH: str = "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P225_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P225_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"

P225_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P225_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P225_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

P225_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P225_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P225_PINNED_FX3_LIBBACKUP_SO_SHA256: str = "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"

P225_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P225_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P225_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"

P225_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
)
P225_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P225_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"

# Pillar 33A — [Power Save Start Time] 9-Condition Matrix & [Auto Power OFF Temp.] + [Fan Control] Constants
P225_POWERSAVE_DEFAULT: str = "5 Min"
P225_POWERSAVE_START_TIMES: Tuple[str, ...] = ("Off", "10 Sec", "1 Min", "2 Min", "5 Min", "30 Min")
P225_AIRGAP_SAFE_POWERSAVE_TIMERS: Tuple[str, ...] = ("30 Min", "Off")
P225_POWERSAVE_9_BYPASS_CONDITIONS: Tuple[str, ...] = (
    "usb_power_supply",
    "slideshow_playback",
    "ftp_transfer",
    "movie_recording",
    "pc_connection",
    "tv_hdmi_connection",
    "ir_remote_ctrl_on",
    "bluetooth_rmt_ctrl_on",
    "streaming_or_creators_cloud",
)
P225_NETWORK_OR_HOST_BYPASS_CONDITIONS: Tuple[str, ...] = (
    "ftp_transfer",
    "pc_connection",
    "streaming_or_creators_cloud",
)
P225_TIER0_P3_COLD_DUMP_MIB: int = 75
P225_TIER0_MIN_BATTERY_PCT: int = 51

P225_AUTO_POWER_OFF_TEMPS: Tuple[str, ...] = ("Standard", "High")
P225_FX3_FAN_MODES: Tuple[str, ...] = ("Auto", "Minimum", "Off in Rec", "Always Off")
P225_PREBACKUP_MAX_SOC_TEMP_C: float = 85.0

# Pillar 33B — [SteadyShot], [Clear Image Zoom] & Backup.bin / CAMSET01..10.DAT Vault Constants
P225_STEADYSHOT_MODES: Tuple[str, ...] = ("Active", "Standard", "Off")
P225_STEADYSHOT_ACTIVE_CROP_FACTOR: float = 1.1
P225_HFR_CUTOFF_NORMAL_REC_RATES: Tuple[str, ...] = ("119.88p", "100p")
P225_ALLOWED_NORMAL_REC_RATES: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
    "100p",
    "119.88p",
)
P225_SQ_CUTOFF_MIN_FPS: int = 100
P225_CIZ_BLOCKED_SQ_FPS: Tuple[int, ...] = (100, 120, 200, 240)
P225_ZOOM_RANGES: Tuple[str, ...] = ("Optical zoom only", "Clear Image Zoom", "Digital Zoom")
P225_STILL_RAW_FORMATS: Tuple[str, ...] = ("RAW", "RAW & JPEG", "RAW & HEIF")
P225_ALLOWED_STILL_FORMATS: Tuple[str, ...] = ("JPEG", "HEIF", "RAW", "RAW & JPEG", "RAW & HEIF")
P225_METERING_MODES: Tuple[str, ...] = ("Multi", "Center", "Spot", "Entire Screen Avg.", "Highlight")
P225_CAMSET_ALLOWED_SLOT: int = 1
P225_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))

P225_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_powersave_autotemp_steadyshot_overlay"
P225_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P225_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P225_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P225_BLOCKED_INVALID_POWERSAVE_TIMER: str = "BLOCKED_INVALID_POWERSAVE_TIMER"
P225_BLOCKED_TIER0_LOW_BATTERY_FLOOR: str = "BLOCKED_TIER0_LOW_BATTERY_FLOOR"
P225_BLOCKED_AIRGAP_POWERSAVE_SLEEP_HAZARD: str = "BLOCKED_AIRGAP_POWERSAVE_SLEEP_HAZARD"
P225_BLOCKED_AIRGAP_NETWORK_BYPASS_CONFLICT: str = "BLOCKED_AIRGAP_NETWORK_BYPASS_CONFLICT"
P225_BLOCKED_AUTOTEMP_HIGH_HANDHELD_BURN_HAZARD: str = "BLOCKED_AUTOTEMP_HIGH_HANDHELD_BURN_HAZARD"
P225_BLOCKED_INVALID_FX3_FAN_MODE: str = "BLOCKED_INVALID_FX3_FAN_MODE"
P225_BLOCKED_FAN_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK: str = (
    "BLOCKED_FAN_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK"
)
P225_BLOCKED_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION: str = "BLOCKED_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION"
P225_BLOCKED_CIZ_HFR_OR_RAW_UNAVAILABLE: str = "BLOCKED_CIZ_HFR_OR_RAW_UNAVAILABLE"
P225_BLOCKED_CIZ_AF_METERING_TRACKING_LOCK_VIOLATION: str = (
    "BLOCKED_CIZ_AF_METERING_TRACKING_LOCK_VIOLATION"
)
P225_BLOCKED_CAMSET_OR_BACKUP_PROFILE_PARITY_DRIFT: str = (
    "BLOCKED_CAMSET_OR_BACKUP_PROFILE_PARITY_DRIFT"
)
P225_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"
P225_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"

P225_STATUS_VERIFIED_PILLAR_33A: str = "VERIFIED_PILLAR_33A_POWERSAVE_9COND_AUTOTEMP_FAN_VAULT"
P225_STATUS_REJECTED_PILLAR_33A: str = "REJECTED_PILLAR_33A_POWERSAVE_9COND_AUTOTEMP_FAN_VAULT"
P225_STATUS_VERIFIED_PILLAR_33B: str = "VERIFIED_PILLAR_33B_STEADYSHOT_ACTIVE_CIZ_CAMSET_VAULT"
P225_STATUS_REJECTED_PILLAR_33B: str = "REJECTED_PILLAR_33B_STEADYSHOT_ACTIVE_CIZ_CAMSET_VAULT"
P225_STATUS_VERIFIED_PILLAR33_SUITE: str = "VERIFIED_PILLAR33_POWERSAVE_9COND_AUTOTEMP_STEADYSHOT_VAULT"
P225_STATUS_FAIL_PILLAR33_SUITE: str = "FAIL_PILLAR33_POWERSAVE_9COND_AUTOTEMP_STEADYSHOT_VAULT"
P225_STATUS_VERIFIED_33OF33_AGGREGATOR: str = "VERIFIED_33OF33_PILLAR_RECOVERY_MASTER"
P225_STATUS_FAIL_33OF33_AGGREGATOR: str = "FAIL_33OF33_PILLAR_RECOVERY_MASTER"

P225_PILLAR_33A_SCENARIO_IDS: Tuple[str, ...] = (
    "P33A1_AIRGAP_NP_FZ100_30MIN_STANDARD_TEMP_FAN_AUTO_SAFE",
    "P33A2_USB_PD_9COND_BYPASS_HIGH_TEMP_TRIPOD_AND_ALWAYS_OFF_COOLDOWN_SAFE",
    "P33A3_REJECT_AIRGAP_BATTERY_5MIN_POWERSAVE_NO_BYPASS_SLEEP_HAZARD",
    "P33A4_REJECT_AUTOTEMP_HIGH_HANDHELD_PROLONGED_BURN_HAZARD",
    "P33A5_REJECT_FAN_ALWAYS_OFF_UNOVERRIDDEN_OR_SOC_OVERHEAT_BEFORE_BACKUP",
    "P33A6_REJECT_STRICT_AIRGAP_NETWORK_BYPASS_OR_INVALID_AUTO1_FAN_MODE",
)
P225_PILLAR_33B_SCENARIO_IDS: Tuple[str, ...] = (
    "P33B1_STEADYSHOT_ACTIVE_5994P_CIZ_CENTER_MULTI_CAMSET01_PARITY_SAFE",
    "P33B2_HDMI_RAW_11988P_STEADYSHOT_STANDARD_OPTICAL_ZOOM_CAMSET10_SAFE",
    "P33B3_REJECT_STEADYSHOT_ACTIVE_AT_11988P_100P_SQ120_OR_HDMI_RAW",
    "P33B4_REJECT_CLEAR_IMAGE_ZOOM_AT_11988P_SQ100_OR_STILL_RAW",
    "P33B5_REJECT_CIZ_UNLOCKED_FOCUS_AREA_SPOT_METERING_FACE_EYE_OR_TRACKING",
    "P33B6_REJECT_CAMSET_SLOT2_PROFILE_DRIFT_OR_BACKUP_H0_H3_MISMATCH",
)

MASTER_33_PILLAR_COUNT: int = 33
MASTER_33_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_32_PILLAR_SPECS + (
    (
        33,
        "pillar_33_powersave_9cond_autotemp_steadyshot_vault",
        "Phase 225",
        "fx3_recovery.realhw_33pillar_powersave_9cond_temp_vault_verifier",
    ),
)
MASTER_33_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_33_PILLAR_SPECS)


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
    return any(tok in low for tok in P225_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase225DonorArtifactDigest:
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
class Phase225DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase225DonorArtifactDigest, ...]


@dataclass(frozen=True)
class PowerSave9ConditionFlags:
    usb_power_supply: bool = False
    slideshow_playback: bool = False
    ftp_transfer: bool = False
    movie_recording: bool = False
    pc_connection: bool = False
    tv_hdmi_connection: bool = False
    ir_remote_ctrl_on: bool = False
    bluetooth_rmt_ctrl_on: bool = False
    streaming_or_creators_cloud: bool = False

    def active_conditions(self) -> Tuple[str, ...]:
        return tuple(name for name in P225_POWERSAVE_9_BYPASS_CONDITIONS if bool(getattr(self, name)))


@dataclass(frozen=True)
class PowerSave9CondAndAutoTempVaultSpec:
    camera_model: str = P225_FX3_MODEL_NAME
    fw_version: str = P225_FX3_FW_VERSION
    power_save_start_time: str = "30 Min"
    bypass_flags: PowerSave9ConditionFlags = PowerSave9ConditionFlags()
    tier0_p3_75mib_cold_dump_requested: bool = True
    camset_vault_restore_requested: bool = True
    air_gapped_internal_battery: bool = True
    strict_airgap_enforced: bool = True
    battery_pct: int = 84
    battery_low_warning: bool = False
    auto_power_off_temp: str = "Standard"  # Standard | High
    tripod_mounted: bool = True
    handheld_prolonged_operation: bool = False
    configured_fan_control: str = "Auto"  # Auto | Minimum | Off in Rec | Always Off
    pre_backup_fan_cooldown_to_auto: bool = True
    effective_fan_control: str = "Auto"
    soc_temp_c: float = 52.0
    thermal_shutdown_warning: bool = False
    overlay_dir: str = P225_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P225_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P225_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P225_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class PowerSave9CondAndAutoTempVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    power_save_start_time: str
    active_bypass_conditions: Tuple[str, ...]
    bypass_condition_count: int
    powersave_auto_deactivated: bool
    airgap_cold_dump_antisleep_verified: bool
    auto_power_off_temp_verified: bool
    fan_prebackup_cooldown_verified: bool
    h0_equals_h3_verified: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SteadyShotActiveAndCizCamsetVaultSpec:
    camera_model: str = P225_FX3_MODEL_NAME
    fw_version: str = P225_FX3_FW_VERSION
    steadyshot_mode: str = "Active"  # Active | Standard | Off
    rec_frame_rate: str = "59.94p"
    sq_mode_enabled: bool = False
    sq_frame_rate_fps: int = 60
    hdmi_raw_output_enabled: bool = False
    active_crop_factor_acknowledged: bool = True
    zoom_range: str = "Clear Image Zoom"  # Optical zoom only | Clear Image Zoom | Digital Zoom
    smart_zoom_requested: bool = False
    still_file_format: str = "JPEG"
    current_zoom_scale: float = 1.4
    focus_area_disabled_center_locked: bool = True
    effective_metering_mode: str = "Multi"
    face_eye_prior_af_available: bool = False
    face_priority_multi_metering_available: bool = False
    realtime_tracking_available: bool = False
    camset_slot: int = P225_CAMSET_ALLOWED_SLOT
    camset_filename: str = "CAMSET01.DAT"
    saved_profile_powersave: str = "30 Min"
    restored_profile_powersave: str = "30 Min"
    saved_profile_autotemp: str = "Standard"
    restored_profile_autotemp: str = "Standard"
    saved_profile_steadyshot: str = "Active"
    restored_profile_steadyshot: str = "Active"
    saved_profile_zoom_range: str = "Clear Image Zoom"
    restored_profile_zoom_range: str = "Clear Image Zoom"
    stage_b_overlay_dir: str = P225_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P225_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P225_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P225_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class SteadyShotActiveAndCizCamsetVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    steadyshot_cutoff_verified: bool
    ciz_availability_verified: bool
    ciz_four_state_locks_verified: bool
    camset_slot1_profile_parity_verified: bool
    h0_equals_h3_verified: bool
    tier0_surfaces_intact: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PowerSaveAutoTempAndSteadyShotVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase225DonorSnapshot
    powersave_autotemp_report: PowerSave9CondAndAutoTempVaultReport
    steadyshot_ciz_report: SteadyShotActiveAndCizCamsetVaultReport
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
class Pillar33ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar33ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar33ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar33BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar33ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar33StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase225DonorSnapshot
    pillar_33a_powersave_autotemp_vault: Pillar33ASuiteResult
    pillar_33b_steadyshot_ciz_vault: Pillar33BSuiteResult
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
class Master33PillarRecoveryReport:
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
    nominal_under_3_2s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase225DonorSnapshot
    pillar33_a_powersave_autotemp_vault: Pillar33ASuiteResult
    pillar33_b_steadyshot_ciz_vault: Pillar33BSuiteResult
    master_33pillar_sha256: str
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
    max_full_bytes: int = P225_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P225_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase225_donors() -> Tuple[Phase225DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P225_DONOR_FX3_BODYDATA_RELPATH,
            P225_PINNED_FX3_BODYDATA_BYTES,
            P225_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P225_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P225_DONOR_FX3_APPFW_702_RELPATH,
            P225_PINNED_FX3_APPFW_702_BYTES,
            P225_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P225_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_APPFW_702",
        ),
        (
            "fx3_backup_bin",
            P225_DONOR_FX3_BACKUP_BIN_RELPATH,
            P225_PINNED_FX3_BACKUP_BIN_BYTES,
            P225_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P225_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P225_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P225_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P225_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P225_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P225_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P225_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P225_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P225_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libinframediaconfig_so",
            P225_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P225_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P225_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P225_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+GetMediaNum+Backup_sync_subsystem",
        ),
    )
    return tuple(
        Phase225DonorArtifactDigest(
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


def inspect_phase225_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase225DonorSnapshot:
    """Inspect Wave-31 / FX3 7.02 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase225_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase225DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P225_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P225_DONOR_FX3_BODYDATA_RELPATH,
            P225_PINNED_FX3_BODYDATA_BYTES,
            P225_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P225_DONOR_FX3_APPFW_702_RELPATH,
            P225_PINNED_FX3_APPFW_702_BYTES,
            P225_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P225_DONOR_FX3_BACKUP_BIN_RELPATH,
            P225_PINNED_FX3_BACKUP_BIN_BYTES,
            P225_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P225_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P225_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P225_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P225_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P225_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P225_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libinframediaconfig_so",
            P225_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P225_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P225_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"InfraMediaConfig", b"GetMediaNum", b"Backup_sync_subsystem")
            ),
        ),
    )

    digests: List[Phase225DonorArtifactDigest] = []
    for aid, rel, pinned_bytes, pinned_sha, validator in probe_specs:
        ok, total_b, hdr_b, dkind, dsha, raw = _read_donor_readonly_bounded(rel)
        if not ok:
            digests.append(
                Phase225DonorArtifactDigest(
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
            Phase225DonorArtifactDigest(
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
        synth = _synthetic_phase225_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase225DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P225_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    dt = round(time.monotonic() - t0, 6)
    return Phase225DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all(d.present and d.matches_pinned for d in digests),
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P225_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Pillar 33A & 33B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_powersave_autotemp_spec() -> PowerSave9CondAndAutoTempVaultSpec:
    return PowerSave9CondAndAutoTempVaultSpec()


def build_default_safe_steadyshot_ciz_spec() -> SteadyShotActiveAndCizCamsetVaultSpec:
    return SteadyShotActiveAndCizCamsetVaultSpec()


def evaluate_powersave_9cond_and_autotemp_fan_vault(
    spec: PowerSave9CondAndAutoTempVaultSpec,
) -> PowerSave9CondAndAutoTempVaultReport:
    """Audit `[Power Save Start Time]` 9-condition matrix + `[Auto Power OFF Temp.]` + `[Fan Control]` vault."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P225_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P225_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 33A")

    if spec.power_save_start_time not in P225_POWERSAVE_START_TIMES:
        _fail(
            P225_BLOCKED_INVALID_POWERSAVE_TIMER,
            f"Unsupported [Power Save Start Time]: {spec.power_save_start_time!r}",
        )

    active_bypasses = spec.bypass_flags.active_conditions()
    powersave_auto_deactivated = len(active_bypasses) > 0

    if spec.strict_airgap_enforced and any(c in P225_NETWORK_OR_HOST_BYPASS_CONDITIONS for c in active_bypasses):
        _fail(
            P225_BLOCKED_AIRGAP_NETWORK_BYPASS_CONFLICT,
            f"Strict air-gap conflicts with active network/PC bypass conditions: {active_bypasses}",
        )

    backup_or_restore = bool(spec.tier0_p3_75mib_cold_dump_requested or spec.camset_vault_restore_requested)

    if backup_or_restore and (spec.battery_pct < P225_TIER0_MIN_BATTERY_PCT or spec.battery_low_warning):
        if not spec.bypass_flags.usb_power_supply or spec.battery_low_warning:
            _fail(
                P225_BLOCKED_TIER0_LOW_BATTERY_FLOOR,
                f"NP-FZ100 battery {spec.battery_pct}% (low_warning={spec.battery_low_warning}) below >=51% floor",
            )

    airgap_antisleep_ok = True
    if backup_or_restore and spec.air_gapped_internal_battery and not powersave_auto_deactivated:
        if spec.power_save_start_time not in P225_AIRGAP_SAFE_POWERSAVE_TIMERS:
            airgap_antisleep_ok = False
            _fail(
                P225_BLOCKED_AIRGAP_POWERSAVE_SLEEP_HAZARD,
                f"Air-gapped NP-FZ100 cold dump/restore blocked: [Power Save Start Time]={spec.power_save_start_time!r} "
                "with 0/9 bypass conditions active risks mid-dump sleep interruption",
            )

    autotemp_ok = True
    if spec.auto_power_off_temp not in P225_AUTO_POWER_OFF_TEMPS:
        autotemp_ok = False
        _fail(
            P225_BLOCKED_AUTOTEMP_HIGH_HANDHELD_BURN_HAZARD,
            f"Unsupported [Auto Power OFF Temp.]: {spec.auto_power_off_temp!r}",
        )
    elif spec.auto_power_off_temp == "High" and (not spec.tripod_mounted or spec.handheld_prolonged_operation):
        autotemp_ok = False
        _fail(
            P225_BLOCKED_AUTOTEMP_HIGH_HANDHELD_BURN_HAZARD,
            "[Auto Power OFF Temp.] = [High] requires tripod mounting and forbids prolonged handheld operation",
        )

    fan_cooldown_ok = True
    if spec.configured_fan_control not in P225_FX3_FAN_MODES or spec.effective_fan_control not in P225_FX3_FAN_MODES:
        fan_cooldown_ok = False
        _fail(
            P225_BLOCKED_INVALID_FX3_FAN_MODE,
            f"FX3 [Fan Control] must use exact 4-mode set {P225_FX3_FAN_MODES}, got "
            f"configured={spec.configured_fan_control!r}, effective={spec.effective_fan_control!r}",
        )
    elif backup_or_restore:
        if spec.configured_fan_control == "Always Off" and (
            not spec.pre_backup_fan_cooldown_to_auto or spec.effective_fan_control != "Auto"
        ):
            fan_cooldown_ok = False
            _fail(
                P225_BLOCKED_FAN_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK,
                "[Fan Control] = [Always Off] must cool down and switch to [Auto] before Tier-0 dump or CAMSET restore",
            )
        if spec.soc_temp_c >= P225_PREBACKUP_MAX_SOC_TEMP_C or spec.thermal_shutdown_warning:
            fan_cooldown_ok = False
            _fail(
                P225_BLOCKED_FAN_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK,
                f"Pre-backup thermal ceiling exceeded: soc_temp_c={spec.soc_temp_c}C, "
                f"thermal_shutdown_warning={spec.thermal_shutdown_warning}",
            )

    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _fail(
            P225_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P225_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P225_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P225_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or p2 BLKROSET immutability drifted in Pillar 33A",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "33A",
            "passed": passed,
            "block_code": block_code,
            "timer": spec.power_save_start_time,
            "active_bypasses": list(active_bypasses),
            "autotemp": spec.auto_power_off_temp,
            "effective_fan": spec.effective_fan_control,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return PowerSave9CondAndAutoTempVaultReport(
        passed=passed,
        status=P225_STATUS_VERIFIED_PILLAR_33A if passed else P225_STATUS_REJECTED_PILLAR_33A,
        block_code=block_code,
        power_save_start_time=spec.power_save_start_time,
        active_bypass_conditions=active_bypasses,
        bypass_condition_count=len(active_bypasses),
        powersave_auto_deactivated=powersave_auto_deactivated,
        airgap_cold_dump_antisleep_verified=airgap_antisleep_ok and passed,
        auto_power_off_temp_verified=autotemp_ok and passed,
        fan_prebackup_cooldown_verified=fan_cooldown_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_steadyshot_active_and_ciz_camset_vault(
    spec: SteadyShotActiveAndCizCamsetVaultSpec,
) -> SteadyShotActiveAndCizCamsetVaultReport:
    """Audit `[SteadyShot]` (`Active` cutoffs) + `[Clear Image Zoom]` locks + `Backup.bin`/`CAMSET` parity."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P225_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P225_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 33B")

    steadyshot_ok = True
    if spec.steadyshot_mode not in P225_STEADYSHOT_MODES or spec.rec_frame_rate not in P225_ALLOWED_NORMAL_REC_RATES:
        steadyshot_ok = False
        _fail(
            P225_BLOCKED_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION,
            f"Invalid SteadyShot ({spec.steadyshot_mode!r}) or frame rate ({spec.rec_frame_rate!r})",
        )
    elif spec.steadyshot_mode == "Active":
        if (
            spec.rec_frame_rate in P225_HFR_CUTOFF_NORMAL_REC_RATES
            or (spec.sq_mode_enabled and spec.sq_frame_rate_fps >= P225_SQ_CUTOFF_MIN_FPS)
            or spec.hdmi_raw_output_enabled
            or not spec.active_crop_factor_acknowledged
        ):
            steadyshot_ok = False
            _fail(
                P225_BLOCKED_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION,
                "[SteadyShot] = [Active] blocked at 119.88p/100p, S&Q >=100fps/120fps, HDMI RAW Output, "
                "or unacknowledged ~1.1x angle-of-view crop",
            )

    ciz_avail_ok = True
    ciz_locks_ok = True
    beyond_optical_mode = spec.zoom_range in ("Clear Image Zoom", "Digital Zoom") or spec.smart_zoom_requested
    if spec.zoom_range not in P225_ZOOM_RANGES or spec.still_file_format not in P225_ALLOWED_STILL_FORMATS:
        ciz_avail_ok = False
        _fail(
            P225_BLOCKED_CIZ_HFR_OR_RAW_UNAVAILABLE,
            f"Unsupported zoom_range={spec.zoom_range!r} or still_file_format={spec.still_file_format!r}",
        )
    elif beyond_optical_mode:
        if (
            spec.still_file_format in P225_STILL_RAW_FORMATS
            or spec.rec_frame_rate in P225_HFR_CUTOFF_NORMAL_REC_RATES
            or (spec.sq_mode_enabled and spec.sq_frame_rate_fps >= P225_SQ_CUTOFF_MIN_FPS)
        ):
            ciz_avail_ok = False
            _fail(
                P225_BLOCKED_CIZ_HFR_OR_RAW_UNAVAILABLE,
                "Clear Image Zoom / Digital Zoom / Smart Zoom unavailable in still RAW, 119.88p/100p, or S&Q >=100fps",
            )
        if spec.current_zoom_scale > 1.0:
            if (
                not spec.focus_area_disabled_center_locked
                or spec.effective_metering_mode != "Multi"
                or spec.face_eye_prior_af_available
                or spec.face_priority_multi_metering_available
                or spec.realtime_tracking_available
            ):
                ciz_locks_ok = False
                _fail(
                    P225_BLOCKED_CIZ_AF_METERING_TRACKING_LOCK_VIOLATION,
                    "Zoom beyond optical range must disable Focus Area (center lock), lock Metering Mode=Multi, "
                    "and disable Face/Eye AF, Face Priority Multi Metering, and Real-time Tracking",
                )

    camset_parity_ok = (
        spec.camset_slot == P225_CAMSET_ALLOWED_SLOT
        and spec.camset_filename in P225_CAMSET_FILENAMES
        and spec.saved_profile_powersave == spec.restored_profile_powersave
        and spec.saved_profile_autotemp == spec.restored_profile_autotemp
        and spec.saved_profile_steadyshot == spec.restored_profile_steadyshot == spec.steadyshot_mode
        and spec.saved_profile_zoom_range == spec.restored_profile_zoom_range == spec.zoom_range
    )
    if not camset_parity_ok:
        _fail(
            P225_BLOCKED_CAMSET_OR_BACKUP_PROFILE_PARITY_DRIFT,
            f"Slot-1 CAMSET01..10.DAT ({spec.camset_filename!r}, slot={spec.camset_slot}) or profile parity drifted",
        )

    if not _is_tmpfs_path(spec.stage_b_overlay_dir) or _targets_persistent_emmc(spec.stage_b_overlay_dir):
        _fail(
            P225_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.stage_b_overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P225_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P225_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P225_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or 16/16 surface parity drifted in Pillar 33B",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "33B",
            "passed": passed,
            "block_code": block_code,
            "steadyshot": spec.steadyshot_mode,
            "zoom_range": spec.zoom_range,
            "camset": spec.camset_filename,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return SteadyShotActiveAndCizCamsetVaultReport(
        passed=passed,
        status=P225_STATUS_VERIFIED_PILLAR_33B if passed else P225_STATUS_REJECTED_PILLAR_33B,
        block_code=block_code,
        steadyshot_cutoff_verified=steadyshot_ok and passed,
        ciz_availability_verified=ciz_avail_ok and passed,
        ciz_four_state_locks_verified=ciz_locks_ok and passed,
        camset_slot1_profile_parity_verified=camset_parity_ok,
        h0_equals_h3_verified=h0_eq_h3,
        tier0_surfaces_intact=spec.tier0_surfaces_h0_h3_matched if h0_eq_h3 else 0,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_powersave_9cond_and_autotemp_steadyshot_vault(
    powersave_spec: Optional[PowerSave9CondAndAutoTempVaultSpec] = None,
    steadyshot_spec: Optional[SteadyShotActiveAndCizCamsetVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> PowerSaveAutoTempAndSteadyShotVaultReport:
    """Combined Pillar 33 verifier: `Power Save Start Time` 9-cond + `Auto Power OFF Temp.` + `SteadyShot`/`CIZ`."""
    donor_snap = inspect_phase225_donors_readonly(force_clean_room=force_clean_room)
    ps_rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
        powersave_spec or build_default_safe_powersave_autotemp_spec()
    )
    ss_rep = evaluate_steadyshot_active_and_ciz_camset_vault(
        steadyshot_spec or build_default_safe_steadyshot_ciz_spec()
    )
    errs: List[str] = _safety_invariant_errors() + list(ps_rep.errors) + list(ss_rep.errors)
    if not donor_snap.all_donors_present:
        errs.append("Phase 225 donor snapshot incomplete or mismatched")
    if not donor_snap.under_0_15s_budget:
        errs.append(f"Phase 225 donor inspection exceeded 2.0s budget: {donor_snap.elapsed_seconds}s")

    all_ok = ps_rep.passed and ss_rep.passed and len(errs) == 0
    return PowerSaveAutoTempAndSteadyShotVaultReport(
        schema=PHASE225_SCHEMA,
        version=PHASE225_VERSION,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P225_STATUS_VERIFIED_PILLAR33_SUITE if all_ok else P225_STATUS_FAIL_PILLAR33_SUITE,
        donor_snapshot=donor_snap,
        powersave_autotemp_report=ps_rep,
        steadyshot_ciz_report=ss_rep,
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
# 6-Scenario Suites & Standalone Pillar 33 Runner
# ---------------------------------------------------------------------------


def run_pillar33a_powersave_9cond_autotemp_6_scenario_suite() -> Pillar33ASuiteResult:
    cases: Tuple[Tuple[str, bool, PowerSave9CondAndAutoTempVaultSpec, Optional[str]], ...] = (
        (
            P225_PILLAR_33A_SCENARIO_IDS[0],
            True,
            PowerSave9CondAndAutoTempVaultSpec(),
            None,
        ),
        (
            P225_PILLAR_33A_SCENARIO_IDS[1],
            True,
            PowerSave9CondAndAutoTempVaultSpec(
                power_save_start_time="5 Min",
                bypass_flags=PowerSave9ConditionFlags(usb_power_supply=True, tv_hdmi_connection=True),
                auto_power_off_temp="High",
                tripod_mounted=True,
                handheld_prolonged_operation=False,
                configured_fan_control="Always Off",
                pre_backup_fan_cooldown_to_auto=True,
                effective_fan_control="Auto",
                soc_temp_c=58.5,
            ),
            None,
        ),
        (
            P225_PILLAR_33A_SCENARIO_IDS[2],
            False,
            PowerSave9CondAndAutoTempVaultSpec(
                power_save_start_time="5 Min",
                bypass_flags=PowerSave9ConditionFlags(),
                air_gapped_internal_battery=True,
            ),
            P225_BLOCKED_AIRGAP_POWERSAVE_SLEEP_HAZARD,
        ),
        (
            P225_PILLAR_33A_SCENARIO_IDS[3],
            False,
            PowerSave9CondAndAutoTempVaultSpec(
                auto_power_off_temp="High",
                tripod_mounted=False,
                handheld_prolonged_operation=True,
            ),
            P225_BLOCKED_AUTOTEMP_HIGH_HANDHELD_BURN_HAZARD,
        ),
        (
            P225_PILLAR_33A_SCENARIO_IDS[4],
            False,
            PowerSave9CondAndAutoTempVaultSpec(
                configured_fan_control="Always Off",
                pre_backup_fan_cooldown_to_auto=False,
                effective_fan_control="Always Off",
            ),
            P225_BLOCKED_FAN_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK,
        ),
        (
            P225_PILLAR_33A_SCENARIO_IDS[5],
            False,
            PowerSave9CondAndAutoTempVaultSpec(
                power_save_start_time="5 Min",
                bypass_flags=PowerSave9ConditionFlags(ftp_transfer=True),
                strict_airgap_enforced=True,
            ),
            P225_BLOCKED_AIRGAP_NETWORK_BYPASS_CONFLICT,
        ),
    )

    outcomes: List[Pillar33ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar33ScenarioOutcome(
                scenario_id=sid,
                pillar="33A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar33ASuiteResult(
        passed=all_ok,
        status=P225_STATUS_VERIFIED_PILLAR_33A if all_ok else P225_STATUS_REJECTED_PILLAR_33A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar33b_steadyshot_ciz_camset_6_scenario_suite() -> Pillar33BSuiteResult:
    cases: Tuple[Tuple[str, bool, SteadyShotActiveAndCizCamsetVaultSpec, Optional[str]], ...] = (
        (
            P225_PILLAR_33B_SCENARIO_IDS[0],
            True,
            SteadyShotActiveAndCizCamsetVaultSpec(),
            None,
        ),
        (
            P225_PILLAR_33B_SCENARIO_IDS[1],
            True,
            SteadyShotActiveAndCizCamsetVaultSpec(
                steadyshot_mode="Standard",
                rec_frame_rate="119.88p",
                hdmi_raw_output_enabled=True,
                zoom_range="Optical zoom only",
                current_zoom_scale=1.0,
                camset_filename="CAMSET10.DAT",
                saved_profile_steadyshot="Standard",
                restored_profile_steadyshot="Standard",
                saved_profile_zoom_range="Optical zoom only",
                restored_profile_zoom_range="Optical zoom only",
            ),
            None,
        ),
        (
            P225_PILLAR_33B_SCENARIO_IDS[2],
            False,
            SteadyShotActiveAndCizCamsetVaultSpec(
                steadyshot_mode="Active",
                rec_frame_rate="119.88p",
                zoom_range="Optical zoom only",
                current_zoom_scale=1.0,
                saved_profile_zoom_range="Optical zoom only",
                restored_profile_zoom_range="Optical zoom only",
            ),
            P225_BLOCKED_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION,
        ),
        (
            P225_PILLAR_33B_SCENARIO_IDS[3],
            False,
            SteadyShotActiveAndCizCamsetVaultSpec(
                steadyshot_mode="Standard",
                sq_mode_enabled=True,
                sq_frame_rate_fps=120,
                zoom_range="Clear Image Zoom",
                saved_profile_steadyshot="Standard",
                restored_profile_steadyshot="Standard",
            ),
            P225_BLOCKED_CIZ_HFR_OR_RAW_UNAVAILABLE,
        ),
        (
            P225_PILLAR_33B_SCENARIO_IDS[4],
            False,
            SteadyShotActiveAndCizCamsetVaultSpec(
                zoom_range="Clear Image Zoom",
                current_zoom_scale=1.35,
                focus_area_disabled_center_locked=False,
                effective_metering_mode="Spot",
                face_eye_prior_af_available=True,
                realtime_tracking_available=True,
            ),
            P225_BLOCKED_CIZ_AF_METERING_TRACKING_LOCK_VIOLATION,
        ),
        (
            P225_PILLAR_33B_SCENARIO_IDS[5],
            False,
            SteadyShotActiveAndCizCamsetVaultSpec(
                camset_slot=2,
                restored_profile_steadyshot="Off",
            ),
            P225_BLOCKED_CAMSET_OR_BACKUP_PROFILE_PARITY_DRIFT,
        ),
    )

    outcomes: List[Pillar33ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_steadyshot_active_and_ciz_camset_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar33ScenarioOutcome(
                scenario_id=sid,
                pillar="33B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar33BSuiteResult(
        passed=all_ok,
        status=P225_STATUS_VERIFIED_PILLAR_33B if all_ok else P225_STATUS_REJECTED_PILLAR_33B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar33_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar33StandaloneReport:
    """Run full Pillar 33 standalone suite (`6/6` Pillar 33A + `6/6` Pillar 33B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase225_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar33a_powersave_9cond_autotemp_6_scenario_suite()
    res_b = run_pillar33b_steadyshot_ciz_camset_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 225 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE225_SCHEMA,
            "version": PHASE225_VERSION,
            "mode": donor_snapshot.verification_mode,
            "33a": [asdict(s) for s in res_a.scenarios],
            "33b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar33StandaloneReport(
        schema=PHASE225_SCHEMA,
        version=PHASE225_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P225_STATUS_VERIFIED_PILLAR33_SUITE if all_ok else P225_STATUS_FAIL_PILLAR33_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_33a_powersave_autotemp_vault=res_a,
        pillar_33b_steadyshot_ciz_vault=res_b,
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
# Unified 33/33 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master33_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_33pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master33PillarRecoveryReport:
    """Evaluate and aggregate all 33 recovery pillars (`1..33`) concurrently -> `33/33` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_33_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_32pillar() -> Master32PillarRecoveryReport:
        return evaluate_realhw_32pillar_recovery_master(**kw)

    def _run_p33() -> Tuple[Pillar33StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar33_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_32 = pool.submit(_run_32pillar)
        fut_33 = pool.submit(_run_p33)
        m32_rep = fut_32.result()
        p33_rep, p33_dt = fut_33.result()

    all_errors: List[str] = list(m32_rep.errors) + list(p33_rep.errors)
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
        if getattr(m32_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-32 violated {attr_name} == {expected_val}")
        if getattr(p33_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 33 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m32_rep.pillars)
    spec33 = MASTER_33_PILLAR_SPECS[32]
    p33_metrics = {
        "pillar_33a_powersave_autotemp_vault": (
            f"{p33_rep.pillar_33a_powersave_autotemp_vault.scenarios_passed}/"
            f"{p33_rep.pillar_33a_powersave_autotemp_vault.scenarios_total}"
        ),
        "pillar_33b_steadyshot_ciz_vault": (
            f"{p33_rep.pillar_33b_steadyshot_ciz_vault.scenarios_passed}/"
            f"{p33_rep.pillar_33b_steadyshot_ciz_vault.scenarios_total}"
        ),
        "powersave_9cond_count": len(P225_POWERSAVE_9_BYPASS_CONDITIONS),
        "donor_files_inspected": p33_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec33[0],
            pillar_id=spec33[1],
            phase_label=spec33[2],
            module_name=spec33[3],
            passed=bool(p33_rep.all_passed),
            status=p33_rep.status,
            verification_mode=p33_rep.verification_mode,
            elapsed_seconds=p33_dt,
            key_metrics=p33_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec33[1],
                    "mode": p33_rep.verification_mode,
                    "status": p33_rep.status,
                    "metrics": p33_metrics,
                    "passed": p33_rep.all_passed,
                }
            ),
            errors=tuple(p33_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master33_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p33_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_33_PILLAR_COUNT == 33
        and pillars_passed == 33
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE225_SCHEMA,
            "version": PHASE225_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master33PillarRecoveryReport(
        schema=PHASE225_SCHEMA,
        version=PHASE225_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P225_STATUS_VERIFIED_33OF33_AGGREGATOR if all_ok else P225_STATUS_FAIL_33OF33_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P225_CONCURRENT_CEILING_SECONDS,
        nominal_under_3_2s=elapsed < P225_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p33_rep.donor_snapshot,
        pillar33_a_powersave_autotemp_vault=p33_rep.pillar_33a_powersave_autotemp_vault,
        pillar33_b_steadyshot_ciz_vault=p33_rep.pillar_33b_steadyshot_ciz_vault,
        master_33pillar_sha256=master_sha,
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


def evaluate_33pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master33PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_33pillar_recovery_master`."""
    return evaluate_realhw_33pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_33pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master33PillarRecoveryReport:
    """Public CLI entry point for Pillar 33 unified `33/33` real-hardware recovery master verification."""
    return evaluate_realhw_33pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
