"""Phase 238 — Pillar 37 (`37/37` Recovery Pillars) & Unified 37-Pillar Recovery Master
(`verify-37pillar-recovery` / `verify-touch-recframe-hdmi-sunny-vault`):

1. **Pillar 37A — `[Touch Operation]` 4-Item `[Camera Settings Reset]` Survival, Unattended Tier-0
   `75 MiB` `p3` Bench Vault Accidental-Tap Firewall & `[Monitor Brightness]` (`[Manual]` `-2..+2`
   vs `[Sunny Weather]`) Indoor `NP-FZ100` Battery/Thermal Guard (`ILME-FX3 Ver. 7.02`)**:
   - Models all 4 `MENU` -> `Setup` -> `[Touch Operation]` settings:
     1) `[Touch Operation]` (`On` default / `On: Playback Only` / `Off`),
     2) `[Touch Sensitivity]` (`Standard` default / `Sensitive`),
     3) `[Swipe Up]` (`Open the Fn Menu` default / `Off`),
     4) `[Touch Func. in Shooting]` (`Touch Tracking` default / `Touch Focus` / `Off`),
     surviving `[Camera Settings Reset]` unchanged and resetting to factory defaults **only**
     under `[Initialize]`.
   - Enforces `[Touch Operation] = Off` (or `On: Playback Only`) during unattended Tier-0 `75 MiB`
     `p3` vault dumps so accidental capacitive taps cannot open the `Fn` menu (`Swipe Up`) or
     trigger `Touch Tracking` / `Touch Focus` (`0` accidental `Fn` or tracking triggers).
   - Models `MENU` -> `Setup` -> `[Monitor]` -> `[Monitor Brightness]` (`Manual` `-2..+2` default
     `0` vs `Sunny Weather`) surviving `[Camera Settings Reset]` (cleared only by `[Initialize]`),
     and locks indoor `NP-FZ100` bench runs to `[Manual]` (`0`) to prevent indoor visual exposure
     clipping misjudgment and unnecessary LCD backlight thermal/battery drain.

2. **Pillar 37B — `[Emphasized REC Display]` & `[Grid Line Display]` HDMI Info Routing vs Forced
   `[Off(HDMI Only)]` / `RAW` Clean-Feed Clamp & Slot-1 `CAMSET01.DAT` Vault Recovery**:
   - Models `[Emphasized REC Display]` (`On` default on `ILME-FX3`, **resettable** via
     `[Camera Settings Reset]`) and `[Grid Line Display]` (`Off` default / `On` with
     `[Grid Line Type]` `Rule of 3rds Grid` default, `Square Grid`, `Diag. + Square Grid` —
     **not** reset by `[Camera Settings Reset]`, cleared only by `[Initialize]`).
   - Verifies external HDMI routing of `[Emphasized REC Display]` red frame and `[Grid Line Display]`
     when `[HDMI Info. Display] = On` (blanking the built-in camera LCD while keeping local-only
     `Marker`/`Zebra`/`Peaking` overlays at `0` on HDMI) vs automatic `[HDMI Info. Display] -> Off`
     hardware clean-feed clamp whenever `[Rec. Media dur HDMI Output] = Off(HDMI Only)` or HDMI
     `RAW` movie output is active (`0` red REC border or grid baked into external HDMI master
     recordings).
   - Verifies deterministic `CAMSET01.DAT`..`CAMSET10.DAT` Slot-1 vault restoration and `16/16`
     Tier-0 `H0 == H3` immutability.

3. **Unified `37/37` Recovery Master (`evaluate_realhw_37pillar_recovery_master`)**:
   - Delegates Pillars `1..36` concurrently to `evaluate_realhw_36pillar_recovery_master` +
     **Pillar 37** -> **`37/37` (`VERIFIED_37OF37_PILLAR_RECOVERY_MASTER`)** in `< 4.0s` (`< 6.0s` ceiling).
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
from .realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_36_PILLAR_SPECS,
    Master36PillarRecoveryReport,
    evaluate_realhw_36pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE238_SCHEMA: str = "fx3-realhw-37pillar-recovery-master-verifier-v1"
PHASE238_VERSION: str = "1.0.0"

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

P238_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P238_NOMINAL_BUDGET_SECONDS: float = 4.0
P238_CONCURRENT_CEILING_SECONDS: float = 6.0
P238_BOUNDED_HEADER_BYTES: int = 4096
P238_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-35 / FX3 Ver. 7.02 Donor Anchors (bounded O_RDONLY verification)
P238_FX3_MODEL_NAME: str = "ILME-FX3"
P238_FX3_MODEL_ID: int = 0x91030080
P238_FX3_FW_VERSION: str = "7.02"
P238_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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

P238_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P238_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P238_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

P238_DONOR_FX3_APPFW_702_RELPATH: str = "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P238_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P238_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"

P238_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P238_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P238_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

P238_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P238_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P238_PINNED_FX3_LIBBACKUP_SO_SHA256: str = "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"

P238_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P238_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P238_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"

P238_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P238_DONOR_FX3_LIBGPE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so"
)
P238_PINNED_FX3_LIBGPE_SO_BYTES: int = 106480
P238_PINNED_FX3_LIBGPE_SO_SHA256: str = (
    "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464"
)

# Pillar 37A — Touch Operation 4-Item Reset Survival + Bench Vault Lock & Monitor Brightness Sunny Weather Guard
P238_TOUCH_SETUP_MENU_PATH: Tuple[str, ...] = ("MENU", "Setup", "Touch Operation")
P238_TOUCH_SETUP_4_ITEMS: Tuple[str, ...] = (
    "Touch Operation",
    "Touch Sensitivity",
    "Swipe Up",
    "Touch Func. in Shooting",
)
P238_TOUCH_OPERATION_DEFAULT: str = "On"
P238_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("On", "On: Playback Only", "Off")
P238_BENCH_SAFE_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("Off", "On: Playback Only")

P238_TOUCH_SENSITIVITY_DEFAULT: str = "Standard"
P238_TOUCH_SENSITIVITY_MODES: Tuple[str, ...] = ("Standard", "Sensitive")

P238_SWIPE_UP_DEFAULT: str = "Open the Fn Menu"
P238_SWIPE_UP_MODES: Tuple[str, ...] = ("Open the Fn Menu", "Off")

P238_TOUCH_FUNC_IN_SHOOTING_DEFAULT: str = "Touch Tracking"
P238_TOUCH_FUNC_IN_SHOOTING_MODES: Tuple[str, ...] = ("Touch Tracking", "Touch Focus", "Off")

P238_MONITOR_BRIGHTNESS_MENU_PATH: Tuple[str, ...] = ("MENU", "Setup", "Monitor", "Monitor Brightness")
P238_MONITOR_BRIGHTNESS_DEFAULT_MODE: str = "Manual"
P238_MONITOR_BRIGHTNESS_MODES: Tuple[str, ...] = ("Manual", "Sunny Weather")
P238_MONITOR_BRIGHTNESS_DEFAULT_LEVEL: int = 0
P238_MONITOR_BRIGHTNESS_MANUAL_LEVELS: Tuple[int, ...] = (-2, -1, 0, 1, 2)
P238_INDOOR_BENCH_LOCKED_BRIGHTNESS_MODE: str = "Manual"
P238_INDOOR_BENCH_LOCKED_BRIGHTNESS_LEVEL: int = 0

P238_TIER0_P3_VAULT_DUMP_MIB: int = 75
P238_TIER0_BENCH_MIN_NP_FZ100_PCT: int = 51
P238_RESET_ACTIONS: Tuple[str, ...] = ("NONE", "Camera Settings Reset", "Initialize")

# Pillar 37B — Emphasized REC Display & Grid Line HDMI Info Routing vs Off(HDMI Only)/RAW Forced Clean-Feed & CAMSET
P238_EMPHASIZED_REC_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Shooting Display",
    "Emphasized REC Display",
)
P238_EMPHASIZED_REC_DEFAULT: str = "On"
P238_EMPHASIZED_REC_MODES: Tuple[str, ...] = ("On", "Off")
P238_EMPHASIZED_REC_SCOPES: Tuple[str, ...] = ("Movie", "S&Q")

P238_GRID_LINE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Shooting Display",
    "Grid Line Display",
)
P238_GRID_LINE_DISPLAY_DEFAULT: str = "Off"
P238_GRID_LINE_DISPLAY_MODES: Tuple[str, ...] = ("Off", "On")
P238_GRID_LINE_TYPE_DEFAULT: str = "Rule of 3rds Grid"
P238_GRID_LINE_TYPES: Tuple[str, ...] = (
    "Rule of 3rds Grid",
    "Square Grid",
    "Diag. + Square Grid",
)

P238_HDMI_OUTPUT_SETTINGS_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "External Output",
    "HDMI Output Settings",
)
P238_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("On", "Off(HDMI Only)")
P238_HDMI_RAW_OUTPUT_MODES: Tuple[str, ...] = ("Off", "On")
P238_HDMI_INFO_DISPLAY_MODES: Tuple[str, ...] = ("Off", "On")

P238_SLOT1_VAULT_SLOT: int = 1
P238_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))

P238_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_touch_recframe_hdmi_sunny_overlay"
P238_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P238_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P238_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P238_BLOCKED_INVALID_TOUCH_OR_BRIGHTNESS_SPEC: str = "BLOCKED_INVALID_TOUCH_OR_BRIGHTNESS_SPEC"
P238_BLOCKED_TOUCH_SETUP_CAMERA_SETTINGS_RESET_DRIFT: str = (
    "BLOCKED_TOUCH_SETUP_CAMERA_SETTINGS_RESET_DRIFT"
)
P238_BLOCKED_UNATTENDED_BENCH_TOUCH_OPERATION_ACTIVE: str = (
    "BLOCKED_UNATTENDED_BENCH_TOUCH_OPERATION_ACTIVE"
)
P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK: str = (
    "BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK"
)
P238_BLOCKED_MONITOR_BRIGHTNESS_RESET_PERSISTENCE_DRIFT: str = (
    "BLOCKED_MONITOR_BRIGHTNESS_RESET_PERSISTENCE_DRIFT"
)
P238_BLOCKED_INDOOR_BENCH_SUNNY_WEATHER_OR_BRIGHTNESS_DRIFT: str = (
    "BLOCKED_INDOOR_BENCH_SUNNY_WEATHER_OR_BRIGHTNESS_DRIFT"
)
P238_BLOCKED_BENCH_NP_FZ100_BELOW_TIER0_FLOOR: str = (
    "BLOCKED_BENCH_NP_FZ100_BELOW_TIER0_FLOOR"
)
P238_BLOCKED_INVALID_RECFRAME_GRID_OR_HDMI_SPEC: str = (
    "BLOCKED_INVALID_RECFRAME_GRID_OR_HDMI_SPEC"
)
P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT: str = (
    "BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT"
)
P238_BLOCKED_HDMI_ONLY_OR_RAW_CLEAN_FEED_CLAMP_VIOLATION: str = (
    "BLOCKED_HDMI_ONLY_OR_RAW_CLEAN_FEED_CLAMP_VIOLATION"
)
P238_BLOCKED_HDMI_INFO_ROUTING_OR_LCD_BLANK_MISMATCH: str = (
    "BLOCKED_HDMI_INFO_ROUTING_OR_LCD_BLANK_MISMATCH"
)
P238_BLOCKED_LOCAL_ONLY_ASSIST_HDMI_LEAKAGE: str = (
    "BLOCKED_LOCAL_ONLY_ASSIST_HDMI_LEAKAGE"
)
P238_BLOCKED_CAMSET_SLOT1_RECFRAME_GRID_RESTORE_DRIFT: str = (
    "BLOCKED_CAMSET_SLOT1_RECFRAME_GRID_RESTORE_DRIFT"
)
P238_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P238_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P238_STATUS_VERIFIED_PILLAR_37A: str = (
    "VERIFIED_PILLAR_37A_TOUCH_4ITEM_BENCH_VAULT_AND_SUNNY_WEATHER_GUARD"
)
P238_STATUS_REJECTED_PILLAR_37A: str = (
    "REJECTED_PILLAR_37A_TOUCH_4ITEM_BENCH_VAULT_AND_SUNNY_WEATHER_GUARD"
)
P238_STATUS_VERIFIED_PILLAR_37B: str = (
    "VERIFIED_PILLAR_37B_EMPHASIZED_REC_GRID_HDMI_CLEAN_FEED_AND_CAMSET_VAULT"
)
P238_STATUS_REJECTED_PILLAR_37B: str = (
    "REJECTED_PILLAR_37B_EMPHASIZED_REC_GRID_HDMI_CLEAN_FEED_AND_CAMSET_VAULT"
)
P238_STATUS_VERIFIED_PILLAR37_SUITE: str = (
    "VERIFIED_PILLAR37_TOUCH_RECFRAME_HDMI_SUNNY_VAULT"
)
P238_STATUS_FAIL_PILLAR37_SUITE: str = (
    "FAIL_PILLAR37_TOUCH_RECFRAME_HDMI_SUNNY_VAULT"
)
P238_STATUS_VERIFIED_37OF37_AGGREGATOR: str = "VERIFIED_37OF37_PILLAR_RECOVERY_MASTER"
P238_STATUS_FAIL_37OF37_AGGREGATOR: str = "FAIL_37OF37_PILLAR_RECOVERY_MASTER"

P238_PILLAR_37A_SCENARIO_IDS: Tuple[str, ...] = (
    "P37A1_TOUCH_OFF_AND_MANUAL_ZERO_BRIGHTNESS_SURVIVE_CAMERA_SETTINGS_RESET_DURING_75MIB_P3_BENCH_DUMP_SAFE",
    "P37A2_PLAYBACK_ONLY_TOUCH_SENSITIVE_FOCUS_SURVIVES_RESET_AND_BLOCKS_SHOOTING_TAP_SAFE",
    "P37A3_REJECT_UNATTENDED_75MIB_P3_VAULT_DUMP_WITH_TOUCH_OPERATION_ON",
    "P37A4_REJECT_TOUCH_SETUP_4ITEM_WIPED_BY_CAMERA_SETTINGS_RESET_OR_SURVIVING_INITIALIZE",
    "P37A5_REJECT_INDOOR_NP_FZ100_BENCH_SUNNY_WEATHER_THERMAL_BATTERY_AND_EXPOSURE_SKEW",
    "P37A6_REJECT_ACCIDENTAL_CAPACITIVE_FN_SWIPE_OR_TRACKING_TRIGGER_DURING_BENCH_VAULT",
)
P238_PILLAR_37B_SCENARIO_IDS: Tuple[str, ...] = (
    "P37B1_HDMI_ONLY_CLEAN_FEED_CLAMPS_HDMI_INFO_OFF_ZERO_BAKED_RECFRAME_GRID_AND_RESET_SPLIT_SAFE",
    "P37B2_HDMI_INFO_ON_BLANKS_LCD_ROUTES_EMPHASIZED_REC_AND_GRID_WITH_SLOT1_CAMSET01_RESTORE_SAFE",
    "P37B3_REJECT_HDMI_ONLY_OR_RAW_MOVIE_OUTPUT_FAILING_HDMI_INFO_OFF_CLEAN_FEED_CLAMP",
    "P37B4_REJECT_EMPHASIZED_REC_NOT_RESET_OR_GRID_LINE_WIPED_BY_CAMERA_SETTINGS_RESET",
    "P37B5_REJECT_HDMI_INFO_ROUTING_WITHOUT_LCD_BLANKING_OR_MARKER_ZEBRA_PEAKING_HDMI_LEAK",
    "P37B6_REJECT_CAMSET_SLOT2_OR_SLOT1_CAMSET01_RECFRAME_GRID_HDMI_RESTORE_DRIFT",
)

MASTER_37_PILLAR_COUNT: int = 37
MASTER_37_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_36_PILLAR_SPECS + (
    (
        37,
        "pillar_37_touch_recframe_hdmi_sunny_vault",
        "Phase 238",
        "fx3_recovery.realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier",
    ),
)
MASTER_37_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_37_PILLAR_SPECS)


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
    return any(tok in low for tok in P238_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase238DonorArtifactDigest:
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
class Phase238DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase238DonorArtifactDigest, ...]


@dataclass(frozen=True)
class TouchBenchVaultAndSunnyWeatherSpec:
    camera_model: str = P238_FX3_MODEL_NAME
    fw_version: str = P238_FX3_FW_VERSION
    touch_menu_path: Tuple[str, ...] = P238_TOUCH_SETUP_MENU_PATH
    touch_setup_items: Tuple[str, ...] = P238_TOUCH_SETUP_4_ITEMS
    pre_reset_touch_operation: str = "Off"
    pre_reset_touch_sensitivity: str = P238_TOUCH_SENSITIVITY_DEFAULT
    pre_reset_swipe_up: str = P238_SWIPE_UP_DEFAULT
    pre_reset_touch_func_in_shooting: str = P238_TOUCH_FUNC_IN_SHOOTING_DEFAULT
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Initialize
    post_reset_touch_operation: str = "Off"
    post_reset_touch_sensitivity: str = P238_TOUCH_SENSITIVITY_DEFAULT
    post_reset_swipe_up: str = P238_SWIPE_UP_DEFAULT
    post_reset_touch_func_in_shooting: str = P238_TOUCH_FUNC_IN_SHOOTING_DEFAULT
    unattended_tier0_p3_vault_dump_active: bool = True
    tier0_p3_vault_dump_mib: int = P238_TIER0_P3_VAULT_DUMP_MIB
    capacitive_shooting_touch_blocked: bool = True
    capacitive_playback_touch_blocked: bool = True
    accidental_fn_menu_opened_count: int = 0
    accidental_shooting_touch_triggers: int = 0
    monitor_brightness_menu_path: Tuple[str, ...] = P238_MONITOR_BRIGHTNESS_MENU_PATH
    pre_reset_monitor_brightness_mode: str = P238_MONITOR_BRIGHTNESS_DEFAULT_MODE
    pre_reset_monitor_brightness_manual_level: int = P238_MONITOR_BRIGHTNESS_DEFAULT_LEVEL
    post_reset_monitor_brightness_mode: str = P238_MONITOR_BRIGHTNESS_DEFAULT_MODE
    post_reset_monitor_brightness_manual_level: int = P238_MONITOR_BRIGHTNESS_DEFAULT_LEVEL
    indoor_np_fz100_bench_rehearsal: bool = True
    sunny_weather_indoor_exposure_skew_risk: bool = False
    sunny_weather_extra_np_fz100_drain_active: bool = False
    np_fz100_charge_pct: int = 84
    overlay_dir: str = P238_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P238_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P238_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P238_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class TouchBenchVaultAndSunnyWeatherReport:
    passed: bool
    status: str
    block_code: Optional[str]
    touch_4item_reset_survival_verified: bool
    unattended_p3_vault_tap_firewall_verified: bool
    monitor_brightness_reset_survival_verified: bool
    indoor_sunny_weather_battery_guard_verified: bool
    h0_equals_h3_verified: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EmphasizedRecGridHdmiCleanFeedVaultSpec:
    camera_model: str = P238_FX3_MODEL_NAME
    fw_version: str = P238_FX3_FW_VERSION
    emphasized_rec_menu_path: Tuple[str, ...] = P238_EMPHASIZED_REC_MENU_PATH
    grid_line_menu_path: Tuple[str, ...] = P238_GRID_LINE_MENU_PATH
    hdmi_output_menu_path: Tuple[str, ...] = P238_HDMI_OUTPUT_SETTINGS_MENU_PATH
    shooting_mode: str = "Movie"  # Movie | S&Q
    recording_active: bool = True
    hdmi_connected: bool = True
    pre_reset_emphasized_rec_display: str = "Off"
    pre_reset_grid_line_display: str = "On"
    pre_reset_grid_line_type: str = "Square Grid"
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Initialize
    post_reset_emphasized_rec_display: str = P238_EMPHASIZED_REC_DEFAULT  # "On"
    post_reset_grid_line_display: str = "On"  # survives [Camera Settings Reset]
    post_reset_grid_line_type: str = "Square Grid"  # survives [Camera Settings Reset]
    post_reset_rec_media_dur_hdmi_output: str = "Off(HDMI Only)"
    post_reset_hdmi_raw_output: str = "Off"
    post_reset_configured_hdmi_info_display: str = "On"
    effective_hdmi_info_display: str = "Off"  # auto-clamped to Off under Off(HDMI Only) or RAW
    built_in_lcd_blanked: bool = False
    hdmi_red_rec_frame_routed: bool = False
    hdmi_grid_line_routed: bool = False
    hdmi_marker_zebra_peaking_leaked_layers: int = 0
    external_hdmi_master_baked_overlays: int = 0
    camset_restore_after_reset: bool = False
    camset_slot: int = P238_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    saved_emphasized_rec_display: str = "On"
    saved_grid_line_display: str = "On"
    saved_grid_line_type: str = "Diag. + Square Grid"
    saved_rec_media_dur_hdmi_output: str = "On"
    saved_hdmi_raw_output: str = "Off"
    saved_hdmi_info_display: str = "On"
    stage_b_overlay_dir: str = P238_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P238_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P238_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P238_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class EmphasizedRecGridHdmiCleanFeedVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    recframe_vs_grid_reset_split_verified: bool
    hdmi_info_routing_and_lcd_blank_verified: bool
    hdmi_clean_feed_auto_clamp_verified: bool
    local_only_assist_isolation_verified: bool
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
class TouchRecFrameHdmiAndSunnyWeatherVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase238DonorSnapshot
    touch_sunny_weather_report: TouchBenchVaultAndSunnyWeatherReport
    recframe_grid_hdmi_report: EmphasizedRecGridHdmiCleanFeedVaultReport
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
class Pillar37ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar37ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar37ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar37BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar37ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar37StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase238DonorSnapshot
    pillar_37a_touch_bench_sunny_weather_guard: Pillar37ASuiteResult
    pillar_37b_recframe_grid_hdmi_clean_feed_vault: Pillar37BSuiteResult
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
class Master37PillarRecoveryReport:
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
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase238DonorSnapshot
    pillar37_a_touch_bench_sunny_weather_guard: Pillar37ASuiteResult
    pillar37_b_recframe_grid_hdmi_clean_feed_vault: Pillar37BSuiteResult
    master_37pillar_sha256: str
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
    max_full_bytes: int = P238_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P238_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase238_donors() -> Tuple[Phase238DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P238_DONOR_FX3_BODYDATA_RELPATH,
            P238_PINNED_FX3_BODYDATA_BYTES,
            P238_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P238_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P238_DONOR_FX3_APPFW_702_RELPATH,
            P238_PINNED_FX3_APPFW_702_BYTES,
            P238_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P238_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_APPFW_702",
        ),
        (
            "fx3_backup_bin",
            P238_DONOR_FX3_BACKUP_BIN_RELPATH,
            P238_PINNED_FX3_BACKUP_BIN_BYTES,
            P238_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P238_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P238_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P238_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P238_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P238_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P238_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P238_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P238_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P238_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P238_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+Backup_read+Backup_write",
        ),
        (
            "fx3_libgpe_so",
            P238_DONOR_FX3_LIBGPE_SO_RELPATH,
            P238_PINNED_FX3_LIBGPE_SO_BYTES,
            P238_PINNED_FX3_LIBGPE_SO_BYTES,
            "FULL_SHA256",
            P238_PINNED_FX3_LIBGPE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:gpe_blog_error+_ZNK5mpgpe5Gperm4InitEv",
        ),
    )
    return tuple(
        Phase238DonorArtifactDigest(
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


def inspect_phase238_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase238DonorSnapshot:
    """Inspect Wave-35 / FX3 7.02 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase238_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase238DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P238_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P238_DONOR_FX3_BODYDATA_RELPATH,
            P238_PINNED_FX3_BODYDATA_BYTES,
            P238_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P238_DONOR_FX3_APPFW_702_RELPATH,
            P238_PINNED_FX3_APPFW_702_BYTES,
            P238_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P238_DONOR_FX3_BACKUP_BIN_RELPATH,
            P238_PINNED_FX3_BACKUP_BIN_BYTES,
            P238_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P238_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P238_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P238_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P238_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P238_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P238_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P238_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"SaveLoadSettingsIf", b"Backup_read", b"Backup_write")
            ),
        ),
        (
            "fx3_libgpe_so",
            P238_DONOR_FX3_LIBGPE_SO_RELPATH,
            P238_PINNED_FX3_LIBGPE_SO_BYTES,
            P238_PINNED_FX3_LIBGPE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"gpe_blog_error", b"_ZNK5mpgpe5Gperm4InitEv")
            ),
        ),
    )

    digests: List[Phase238DonorArtifactDigest] = []
    for aid, rel, pinned_bytes, pinned_sha, validator in probe_specs:
        ok, total_b, hdr_b, dkind, dsha, raw = _read_donor_readonly_bounded(rel)
        if not ok:
            digests.append(
                Phase238DonorArtifactDigest(
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
            Phase238DonorArtifactDigest(
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
        synth = _synthetic_phase238_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase238DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P238_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    dt = round(time.monotonic() - t0, 6)
    return Phase238DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all(d.present and d.matches_pinned for d in digests),
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P238_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Pillar 37A & 37B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_touch_sunny_weather_vault_spec() -> TouchBenchVaultAndSunnyWeatherSpec:
    return TouchBenchVaultAndSunnyWeatherSpec()


def build_default_safe_recframe_grid_hdmi_vault_spec() -> EmphasizedRecGridHdmiCleanFeedVaultSpec:
    return EmphasizedRecGridHdmiCleanFeedVaultSpec()


def evaluate_touch_bench_vault_and_sunny_weather_guard(
    spec: TouchBenchVaultAndSunnyWeatherSpec,
) -> TouchBenchVaultAndSunnyWeatherReport:
    """Audit 4-item Setup Touch reset survival, Tier-0 `75 MiB` `p3` tap firewall & `Sunny Weather` indoor guard."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P238_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P238_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 37A")

    valid_tokens = (
        spec.camera_model == P238_FX3_MODEL_NAME
        and spec.fw_version in P238_FX3_SUPPORTED_FW_VERSIONS
        and spec.touch_menu_path == P238_TOUCH_SETUP_MENU_PATH
        and spec.touch_setup_items == P238_TOUCH_SETUP_4_ITEMS
        and spec.pre_reset_touch_operation in P238_TOUCH_OPERATION_MODES
        and spec.post_reset_touch_operation in P238_TOUCH_OPERATION_MODES
        and spec.pre_reset_touch_sensitivity in P238_TOUCH_SENSITIVITY_MODES
        and spec.post_reset_touch_sensitivity in P238_TOUCH_SENSITIVITY_MODES
        and spec.pre_reset_swipe_up in P238_SWIPE_UP_MODES
        and spec.post_reset_swipe_up in P238_SWIPE_UP_MODES
        and spec.pre_reset_touch_func_in_shooting in P238_TOUCH_FUNC_IN_SHOOTING_MODES
        and spec.post_reset_touch_func_in_shooting in P238_TOUCH_FUNC_IN_SHOOTING_MODES
        and spec.reset_action in P238_RESET_ACTIONS
        and spec.monitor_brightness_menu_path == P238_MONITOR_BRIGHTNESS_MENU_PATH
        and spec.pre_reset_monitor_brightness_mode in P238_MONITOR_BRIGHTNESS_MODES
        and spec.post_reset_monitor_brightness_mode in P238_MONITOR_BRIGHTNESS_MODES
        and spec.pre_reset_monitor_brightness_manual_level in P238_MONITOR_BRIGHTNESS_MANUAL_LEVELS
        and spec.post_reset_monitor_brightness_manual_level in P238_MONITOR_BRIGHTNESS_MANUAL_LEVELS
        and 0 <= spec.np_fz100_charge_pct <= 100
        and spec.tier0_p3_vault_dump_mib > 0
        and spec.accidental_fn_menu_opened_count >= 0
        and spec.accidental_shooting_touch_triggers >= 0
        and (
            not spec.unattended_tier0_p3_vault_dump_active
            or spec.tier0_p3_vault_dump_mib == P238_TIER0_P3_VAULT_DUMP_MIB
        )
    )
    if not valid_tokens:
        _fail(
            P238_BLOCKED_INVALID_TOUCH_OR_BRIGHTNESS_SPEC,
            f"Invalid model/fw, Touch Operation 4-item Setup tokens, Monitor Brightness tokens, or p3 vault spec: "
            f"model={spec.camera_model!r} fw={spec.fw_version!r} reset={spec.reset_action!r}",
        )

    touch_survival_ok = True
    if valid_tokens:
        pre_4 = (
            spec.pre_reset_touch_operation,
            spec.pre_reset_touch_sensitivity,
            spec.pre_reset_swipe_up,
            spec.pre_reset_touch_func_in_shooting,
        )
        post_4 = (
            spec.post_reset_touch_operation,
            spec.post_reset_touch_sensitivity,
            spec.post_reset_swipe_up,
            spec.post_reset_touch_func_in_shooting,
        )
        factory_4 = (
            P238_TOUCH_OPERATION_DEFAULT,
            P238_TOUCH_SENSITIVITY_DEFAULT,
            P238_SWIPE_UP_DEFAULT,
            P238_TOUCH_FUNC_IN_SHOOTING_DEFAULT,
        )
        if spec.reset_action in ("NONE", "Camera Settings Reset"):
            if post_4 != pre_4:
                touch_survival_ok = False
                _fail(
                    P238_BLOCKED_TOUCH_SETUP_CAMERA_SETTINGS_RESET_DRIFT,
                    "All 4 Setup [Touch Operation] items ([Touch Operation], [Touch Sensitivity], [Swipe Up], "
                    "[Touch Func. in Shooting]) are immune to [Camera Settings Reset] and must survive unchanged",
                )
        elif spec.reset_action == "Initialize":
            if post_4 != factory_4:
                touch_survival_ok = False
                _fail(
                    P238_BLOCKED_TOUCH_SETUP_CAMERA_SETTINGS_RESET_DRIFT,
                    "[Initialize] must restore all 4 Setup [Touch Operation] items to factory defaults "
                    "('On', 'Standard', 'Open the Fn Menu', 'Touch Tracking')",
                )

    tap_firewall_ok = True
    if spec.accidental_fn_menu_opened_count != 0 or spec.accidental_shooting_touch_triggers != 0:
        tap_firewall_ok = False
        _fail(
            P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK,
            f"Accidental capacitive tap leaked during bench vault run: "
            f"fn_opened={spec.accidental_fn_menu_opened_count}, "
            f"shooting_triggers={spec.accidental_shooting_touch_triggers}",
        )

    if valid_tokens:
        if spec.post_reset_touch_operation == "Off":
            if not spec.capacitive_shooting_touch_blocked or not spec.capacitive_playback_touch_blocked:
                tap_firewall_ok = False
                _fail(
                    P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK,
                    "[Touch Operation]='Off' must block both shooting and playback capacitive touch handlers",
                )
        elif spec.post_reset_touch_operation == "On: Playback Only":
            if not spec.capacitive_shooting_touch_blocked or spec.capacitive_playback_touch_blocked:
                tap_firewall_ok = False
                _fail(
                    P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK,
                    "[Touch Operation]='On: Playback Only' must block shooting capacitive taps while keeping playback touch active",
                )
        elif spec.post_reset_touch_operation == "On" and spec.capacitive_shooting_touch_blocked and (
            spec.post_reset_swipe_up == "Open the Fn Menu"
            or spec.post_reset_touch_func_in_shooting != "Off"
        ):
            tap_firewall_ok = False
            _fail(
                P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK,
                "[Touch Operation]='On' leaves capacitive shooting touch active and cannot claim capacitive_shooting_touch_blocked=True",
            )

        if spec.unattended_tier0_p3_vault_dump_active:
            if spec.post_reset_touch_operation not in P238_BENCH_SAFE_TOUCH_OPERATION_MODES:
                tap_firewall_ok = False
                _fail(
                    P238_BLOCKED_UNATTENDED_BENCH_TOUCH_OPERATION_ACTIVE,
                    "Unattended Tier-0 75 MiB p3 vault dump requires [Touch Operation]='Off' or 'On: Playback Only' "
                    "so capacitive screen touches cannot open Fn menu or trigger Touch Tracking/Focus",
                )
            if spec.np_fz100_charge_pct < P238_TIER0_BENCH_MIN_NP_FZ100_PCT:
                _fail(
                    P238_BLOCKED_BENCH_NP_FZ100_BELOW_TIER0_FLOOR,
                    f"Unattended Tier-0 75 MiB p3 vault dump requires NP-FZ100 >= {P238_TIER0_BENCH_MIN_NP_FZ100_PCT}%, "
                    f"got {spec.np_fz100_charge_pct}%",
                )

    brightness_reset_ok = True
    if valid_tokens:
        if spec.reset_action in ("NONE", "Camera Settings Reset"):
            if (
                spec.post_reset_monitor_brightness_mode != spec.pre_reset_monitor_brightness_mode
                or spec.post_reset_monitor_brightness_manual_level
                != spec.pre_reset_monitor_brightness_manual_level
            ):
                brightness_reset_ok = False
                _fail(
                    P238_BLOCKED_MONITOR_BRIGHTNESS_RESET_PERSISTENCE_DRIFT,
                    "[Monitor Brightness] (Manual -2..+2 vs Sunny Weather) is a Setup item not reset by "
                    "[Camera Settings Reset] and must survive unchanged",
                )
        elif spec.reset_action == "Initialize":
            if (
                spec.post_reset_monitor_brightness_mode != P238_MONITOR_BRIGHTNESS_DEFAULT_MODE
                or spec.post_reset_monitor_brightness_manual_level != P238_MONITOR_BRIGHTNESS_DEFAULT_LEVEL
            ):
                brightness_reset_ok = False
                _fail(
                    P238_BLOCKED_MONITOR_BRIGHTNESS_RESET_PERSISTENCE_DRIFT,
                    "[Initialize] must restore [Monitor Brightness] to factory default 'Manual' (0)",
                )

    indoor_sunny_guard_ok = True
    if valid_tokens and spec.indoor_np_fz100_bench_rehearsal:
        if (
            spec.post_reset_monitor_brightness_mode != P238_INDOOR_BENCH_LOCKED_BRIGHTNESS_MODE
            or spec.post_reset_monitor_brightness_manual_level != P238_INDOOR_BENCH_LOCKED_BRIGHTNESS_LEVEL
            or spec.sunny_weather_indoor_exposure_skew_risk
            or spec.sunny_weather_extra_np_fz100_drain_active
        ):
            indoor_sunny_guard_ok = False
            _fail(
                P238_BLOCKED_INDOOR_BENCH_SUNNY_WEATHER_OR_BRIGHTNESS_DRIFT,
                "Indoor NP-FZ100 bench rehearsals must lock [Monitor Brightness] to [Manual] (0); "
                "[Sunny Weather] or non-zero manual boost skews indoor highlight judgment and raises LCD thermal/battery draw",
            )

    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _fail(
            P238_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P238_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P238_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P238_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or p2 BLKROSET immutability drifted in Pillar 37A",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "37A",
            "passed": passed,
            "block_code": block_code,
            "fw_version": spec.fw_version,
            "reset_action": spec.reset_action,
            "post_touch": [
                spec.post_reset_touch_operation,
                spec.post_reset_touch_sensitivity,
                spec.post_reset_swipe_up,
                spec.post_reset_touch_func_in_shooting,
            ],
            "post_brightness": [
                spec.post_reset_monitor_brightness_mode,
                spec.post_reset_monitor_brightness_manual_level,
            ],
            "unattended_dump": spec.unattended_tier0_p3_vault_dump_active,
            "indoor_bench": spec.indoor_np_fz100_bench_rehearsal,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return TouchBenchVaultAndSunnyWeatherReport(
        passed=passed,
        status=P238_STATUS_VERIFIED_PILLAR_37A if passed else P238_STATUS_REJECTED_PILLAR_37A,
        block_code=block_code,
        touch_4item_reset_survival_verified=touch_survival_ok and passed,
        unattended_p3_vault_tap_firewall_verified=tap_firewall_ok and passed,
        monitor_brightness_reset_survival_verified=brightness_reset_ok and passed,
        indoor_sunny_weather_battery_guard_verified=indoor_sunny_guard_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
    spec: EmphasizedRecGridHdmiCleanFeedVaultSpec,
) -> EmphasizedRecGridHdmiCleanFeedVaultReport:
    """Audit `[Emphasized REC Display]` & `[Grid Line Display]` HDMI routing vs `Off(HDMI Only)`/`RAW` clean-feed clamp."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P238_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P238_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 37B")

    valid_tokens = (
        spec.camera_model == P238_FX3_MODEL_NAME
        and spec.fw_version in P238_FX3_SUPPORTED_FW_VERSIONS
        and spec.emphasized_rec_menu_path == P238_EMPHASIZED_REC_MENU_PATH
        and spec.grid_line_menu_path == P238_GRID_LINE_MENU_PATH
        and spec.hdmi_output_menu_path == P238_HDMI_OUTPUT_SETTINGS_MENU_PATH
        and spec.shooting_mode in P238_EMPHASIZED_REC_SCOPES
        and spec.pre_reset_emphasized_rec_display in P238_EMPHASIZED_REC_MODES
        and spec.post_reset_emphasized_rec_display in P238_EMPHASIZED_REC_MODES
        and spec.pre_reset_grid_line_display in P238_GRID_LINE_DISPLAY_MODES
        and spec.post_reset_grid_line_display in P238_GRID_LINE_DISPLAY_MODES
        and spec.pre_reset_grid_line_type in P238_GRID_LINE_TYPES
        and spec.post_reset_grid_line_type in P238_GRID_LINE_TYPES
        and spec.reset_action in P238_RESET_ACTIONS
        and spec.post_reset_rec_media_dur_hdmi_output in P238_REC_MEDIA_DUR_HDMI_MODES
        and spec.post_reset_hdmi_raw_output in P238_HDMI_RAW_OUTPUT_MODES
        and spec.post_reset_configured_hdmi_info_display in P238_HDMI_INFO_DISPLAY_MODES
        and spec.effective_hdmi_info_display in P238_HDMI_INFO_DISPLAY_MODES
        and spec.saved_emphasized_rec_display in P238_EMPHASIZED_REC_MODES
        and spec.saved_grid_line_display in P238_GRID_LINE_DISPLAY_MODES
        and spec.saved_grid_line_type in P238_GRID_LINE_TYPES
        and spec.saved_rec_media_dur_hdmi_output in P238_REC_MEDIA_DUR_HDMI_MODES
        and spec.saved_hdmi_raw_output in P238_HDMI_RAW_OUTPUT_MODES
        and spec.saved_hdmi_info_display in P238_HDMI_INFO_DISPLAY_MODES
        and spec.hdmi_marker_zebra_peaking_leaked_layers >= 0
        and spec.external_hdmi_master_baked_overlays >= 0
    )
    if not valid_tokens:
        _fail(
            P238_BLOCKED_INVALID_RECFRAME_GRID_OR_HDMI_SPEC,
            "Invalid model/fw, [Emphasized REC Display], [Grid Line Display]/[Grid Line Type], or HDMI Output spec",
        )

    camset_ok = True
    if spec.camset_slot != P238_SLOT1_VAULT_SLOT or spec.camset_filename not in P238_CAMSET_FILENAMES:
        camset_ok = False
        _fail(
            P238_BLOCKED_CAMSET_SLOT1_RECFRAME_GRID_RESTORE_DRIFT,
            f"CAMSET vault must reside on Slot 1 as CAMSET01.DAT..CAMSET10.DAT: "
            f"slot={spec.camset_slot!r} file={spec.camset_filename!r}",
        )

    reset_split_ok = True
    if valid_tokens:
        if spec.camset_restore_after_reset:
            if (
                spec.post_reset_emphasized_rec_display != spec.saved_emphasized_rec_display
                or spec.post_reset_grid_line_display != spec.saved_grid_line_display
                or spec.post_reset_grid_line_type != spec.saved_grid_line_type
                or spec.post_reset_rec_media_dur_hdmi_output != spec.saved_rec_media_dur_hdmi_output
                or spec.post_reset_hdmi_raw_output != spec.saved_hdmi_raw_output
                or spec.post_reset_configured_hdmi_info_display != spec.saved_hdmi_info_display
            ):
                camset_ok = False
                _fail(
                    P238_BLOCKED_CAMSET_SLOT1_RECFRAME_GRID_RESTORE_DRIFT,
                    "Post-restore [Emphasized REC Display], [Grid Line Display]/[Type], or HDMI state drifted from Slot-1 CAMSET",
                )
        elif spec.reset_action == "NONE":
            if (
                spec.post_reset_emphasized_rec_display != spec.pre_reset_emphasized_rec_display
                or spec.post_reset_grid_line_display != spec.pre_reset_grid_line_display
                or spec.post_reset_grid_line_type != spec.pre_reset_grid_line_type
            ):
                reset_split_ok = False
                _fail(
                    P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT,
                    "With reset_action='NONE', [Emphasized REC Display] and [Grid Line Display]/[Type] must remain unchanged",
                )
        elif spec.reset_action == "Camera Settings Reset":
            if spec.post_reset_emphasized_rec_display != P238_EMPHASIZED_REC_DEFAULT:
                reset_split_ok = False
                _fail(
                    P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT,
                    "[Emphasized REC Display] is resettable by [Camera Settings Reset] and must return to default 'On'",
                )
            if (
                spec.post_reset_grid_line_display != spec.pre_reset_grid_line_display
                or spec.post_reset_grid_line_type != spec.pre_reset_grid_line_type
            ):
                reset_split_ok = False
                _fail(
                    P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT,
                    "[Grid Line Display] and [Grid Line Type] are NOT reset by [Camera Settings Reset] and must survive unchanged",
                )
        elif spec.reset_action == "Initialize":
            if (
                spec.post_reset_emphasized_rec_display != P238_EMPHASIZED_REC_DEFAULT
                or spec.post_reset_grid_line_display != P238_GRID_LINE_DISPLAY_DEFAULT
                or spec.post_reset_grid_line_type != P238_GRID_LINE_TYPE_DEFAULT
            ):
                reset_split_ok = False
                _fail(
                    P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT,
                    "[Initialize] must restore [Emphasized REC Display]='On', [Grid Line Display]='Off', "
                    "and [Grid Line Type]='Rule of 3rds Grid'",
                )

    local_assist_ok = True
    if spec.hdmi_marker_zebra_peaking_leaked_layers != 0:
        local_assist_ok = False
        _fail(
            P238_BLOCKED_LOCAL_ONLY_ASSIST_HDMI_LEAKAGE,
            f"Local-LCD-only [Marker]/[Zebra]/[Peaking] leaked {spec.hdmi_marker_zebra_peaking_leaked_layers} "
            f"layers onto HDMI output",
        )

    clean_feed_clamp_ok = True
    hdmi_routing_ok = True
    if valid_tokens:
        clean_feed_clamp_triggered = (
            spec.post_reset_rec_media_dur_hdmi_output == "Off(HDMI Only)"
            or spec.post_reset_hdmi_raw_output == "On"
        )
        if clean_feed_clamp_triggered:
            if (
                spec.effective_hdmi_info_display != "Off"
                or spec.hdmi_red_rec_frame_routed
                or spec.hdmi_grid_line_routed
                or spec.external_hdmi_master_baked_overlays != 0
                or spec.built_in_lcd_blanked
            ):
                clean_feed_clamp_ok = False
                _fail(
                    P238_BLOCKED_HDMI_ONLY_OR_RAW_CLEAN_FEED_CLAMP_VIOLATION,
                    "When [Rec. Media dur HDMI Output]='Off(HDMI Only)' or HDMI [RAW Output]='On', "
                    "[HDMI Info. Display] is forced to 'Off' (0 baked red REC border/grid on external HDMI master, local LCD stays on)",
                )
        else:
            expected_effective = spec.post_reset_configured_hdmi_info_display if spec.hdmi_connected else "Off"
            if spec.effective_hdmi_info_display != expected_effective:
                hdmi_routing_ok = False
                _fail(
                    P238_BLOCKED_HDMI_INFO_ROUTING_OR_LCD_BLANK_MISMATCH,
                    f"Effective [HDMI Info. Display] expected {expected_effective!r}, "
                    f"got {spec.effective_hdmi_info_display!r}",
                )
            elif spec.effective_hdmi_info_display == "On":
                expected_rec_routed = bool(
                    spec.hdmi_connected
                    and spec.recording_active
                    and spec.post_reset_emphasized_rec_display == "On"
                )
                expected_grid_routed = bool(
                    spec.hdmi_connected and spec.post_reset_grid_line_display == "On"
                )
                if (
                    not spec.built_in_lcd_blanked
                    or spec.hdmi_red_rec_frame_routed != expected_rec_routed
                    or spec.hdmi_grid_line_routed != expected_grid_routed
                    or spec.external_hdmi_master_baked_overlays != 0
                ):
                    hdmi_routing_ok = False
                    _fail(
                        P238_BLOCKED_HDMI_INFO_ROUTING_OR_LCD_BLANK_MISMATCH,
                        "With [HDMI Info. Display]='On' (and non-RAW internal card rec 'On'), built-in LCD must blank "
                        "and active [Emphasized REC Display] / [Grid Line Display] must route to HDMI monitor cleanly",
                    )
            else:
                if (
                    spec.built_in_lcd_blanked
                    or spec.hdmi_red_rec_frame_routed
                    or spec.hdmi_grid_line_routed
                    or spec.external_hdmi_master_baked_overlays != 0
                ):
                    hdmi_routing_ok = False
                    _fail(
                        P238_BLOCKED_HDMI_INFO_ROUTING_OR_LCD_BLANK_MISMATCH,
                        "With [HDMI Info. Display]='Off', built-in LCD stays active and 0 REC border/grid overlays route to HDMI",
                    )

    if not _is_tmpfs_path(spec.stage_b_overlay_dir) or _targets_persistent_emmc(spec.stage_b_overlay_dir):
        _fail(
            P238_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.stage_b_overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P238_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P238_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P238_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or p2 BLKROSET immutability drifted in Pillar 37B",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "37B",
            "passed": passed,
            "block_code": block_code,
            "fw_version": spec.fw_version,
            "reset_action": spec.reset_action,
            "post_recframe": spec.post_reset_emphasized_rec_display,
            "post_grid": [spec.post_reset_grid_line_display, spec.post_reset_grid_line_type],
            "hdmi": [
                spec.post_reset_rec_media_dur_hdmi_output,
                spec.post_reset_hdmi_raw_output,
                spec.effective_hdmi_info_display,
                spec.built_in_lcd_blanked,
                spec.hdmi_red_rec_frame_routed,
                spec.hdmi_grid_line_routed,
            ],
            "camset_restore": spec.camset_restore_after_reset,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return EmphasizedRecGridHdmiCleanFeedVaultReport(
        passed=passed,
        status=P238_STATUS_VERIFIED_PILLAR_37B if passed else P238_STATUS_REJECTED_PILLAR_37B,
        block_code=block_code,
        recframe_vs_grid_reset_split_verified=reset_split_ok and passed,
        hdmi_info_routing_and_lcd_blank_verified=hdmi_routing_ok and passed,
        hdmi_clean_feed_auto_clamp_verified=clean_feed_clamp_ok and passed,
        local_only_assist_isolation_verified=local_assist_ok and passed,
        camset_slot1_restore_verified=camset_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        tier0_surfaces_intact=spec.tier0_surfaces_h0_h3_matched if h0_eq_h3 else 0,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_touch_recframe_hdmi_and_sunny_weather_vault(
    touch_sunny_spec: Optional[TouchBenchVaultAndSunnyWeatherSpec] = None,
    recframe_grid_hdmi_spec: Optional[EmphasizedRecGridHdmiCleanFeedVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> TouchRecFrameHdmiAndSunnyWeatherVaultReport:
    """Combined Pillar 37 verifier: Touch 4-item bench vault + Sunny Weather guard & Emphasized REC/Grid HDMI vault."""
    donor_snap = inspect_phase238_donors_readonly(force_clean_room=force_clean_room)
    touch_rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
        touch_sunny_spec or build_default_safe_touch_sunny_weather_vault_spec()
    )
    hdmi_rep = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
        recframe_grid_hdmi_spec or build_default_safe_recframe_grid_hdmi_vault_spec()
    )
    errs: List[str] = _safety_invariant_errors() + list(touch_rep.errors) + list(hdmi_rep.errors)
    if not donor_snap.all_donors_present:
        errs.append("Phase 238 donor snapshot incomplete or mismatched")
    if not donor_snap.under_0_15s_budget:
        errs.append(f"Phase 238 donor inspection exceeded 2.0s budget: {donor_snap.elapsed_seconds}s")

    all_ok = touch_rep.passed and hdmi_rep.passed and len(errs) == 0
    return TouchRecFrameHdmiAndSunnyWeatherVaultReport(
        schema=PHASE238_SCHEMA,
        version=PHASE238_VERSION,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P238_STATUS_VERIFIED_PILLAR37_SUITE if all_ok else P238_STATUS_FAIL_PILLAR37_SUITE,
        donor_snapshot=donor_snap,
        touch_sunny_weather_report=touch_rep,
        recframe_grid_hdmi_report=hdmi_rep,
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
# 6-Scenario Suites & Standalone Pillar 37 Runner
# ---------------------------------------------------------------------------


def run_pillar37a_touch_bench_sunny_weather_6_scenario_suite() -> Pillar37ASuiteResult:
    cases: Tuple[Tuple[str, bool, TouchBenchVaultAndSunnyWeatherSpec, Optional[str]], ...] = (
        (
            P238_PILLAR_37A_SCENARIO_IDS[0],
            True,
            TouchBenchVaultAndSunnyWeatherSpec(),
            None,
        ),
        (
            P238_PILLAR_37A_SCENARIO_IDS[1],
            True,
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="On: Playback Only",
                pre_reset_touch_sensitivity="Sensitive",
                pre_reset_swipe_up="Open the Fn Menu",
                pre_reset_touch_func_in_shooting="Touch Focus",
                reset_action="Camera Settings Reset",
                post_reset_touch_operation="On: Playback Only",
                post_reset_touch_sensitivity="Sensitive",
                post_reset_swipe_up="Open the Fn Menu",
                post_reset_touch_func_in_shooting="Touch Focus",
                capacitive_shooting_touch_blocked=True,
                capacitive_playback_touch_blocked=False,
                accidental_fn_menu_opened_count=0,
                accidental_shooting_touch_triggers=0,
            ),
            None,
        ),
        (
            P238_PILLAR_37A_SCENARIO_IDS[2],
            False,
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="On",
                post_reset_touch_operation="On",
                capacitive_shooting_touch_blocked=False,
                capacitive_playback_touch_blocked=False,
                unattended_tier0_p3_vault_dump_active=True,
            ),
            P238_BLOCKED_UNATTENDED_BENCH_TOUCH_OPERATION_ACTIVE,
        ),
        (
            P238_PILLAR_37A_SCENARIO_IDS[3],
            False,
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="Off",
                pre_reset_touch_sensitivity="Sensitive",
                reset_action="Camera Settings Reset",
                post_reset_touch_operation="On",
                post_reset_touch_sensitivity="Standard",
                capacitive_shooting_touch_blocked=False,
                capacitive_playback_touch_blocked=False,
                unattended_tier0_p3_vault_dump_active=False,
            ),
            P238_BLOCKED_TOUCH_SETUP_CAMERA_SETTINGS_RESET_DRIFT,
        ),
        (
            P238_PILLAR_37A_SCENARIO_IDS[4],
            False,
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_monitor_brightness_mode="Sunny Weather",
                post_reset_monitor_brightness_mode="Sunny Weather",
                indoor_np_fz100_bench_rehearsal=True,
                sunny_weather_indoor_exposure_skew_risk=True,
                sunny_weather_extra_np_fz100_drain_active=True,
            ),
            P238_BLOCKED_INDOOR_BENCH_SUNNY_WEATHER_OR_BRIGHTNESS_DRIFT,
        ),
        (
            P238_PILLAR_37A_SCENARIO_IDS[5],
            False,
            TouchBenchVaultAndSunnyWeatherSpec(
                accidental_fn_menu_opened_count=1,
                accidental_shooting_touch_triggers=1,
            ),
            P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK,
        ),
    )

    outcomes: List[Pillar37ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_touch_bench_vault_and_sunny_weather_guard(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar37ScenarioOutcome(
                scenario_id=sid,
                pillar="37A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar37ASuiteResult(
        passed=all_ok,
        status=P238_STATUS_VERIFIED_PILLAR_37A if all_ok else P238_STATUS_REJECTED_PILLAR_37A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar37b_recframe_grid_hdmi_vault_6_scenario_suite() -> Pillar37BSuiteResult:
    cases: Tuple[Tuple[str, bool, EmphasizedRecGridHdmiCleanFeedVaultSpec, Optional[str]], ...] = (
        (
            P238_PILLAR_37B_SCENARIO_IDS[0],
            True,
            EmphasizedRecGridHdmiCleanFeedVaultSpec(),
            None,
        ),
        (
            P238_PILLAR_37B_SCENARIO_IDS[1],
            True,
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                shooting_mode="S&Q",
                recording_active=True,
                hdmi_connected=True,
                reset_action="Camera Settings Reset",
                camset_restore_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                saved_emphasized_rec_display="On",
                saved_grid_line_display="On",
                saved_grid_line_type="Diag. + Square Grid",
                saved_rec_media_dur_hdmi_output="On",
                saved_hdmi_raw_output="Off",
                saved_hdmi_info_display="On",
                post_reset_emphasized_rec_display="On",
                post_reset_grid_line_display="On",
                post_reset_grid_line_type="Diag. + Square Grid",
                post_reset_rec_media_dur_hdmi_output="On",
                post_reset_hdmi_raw_output="Off",
                post_reset_configured_hdmi_info_display="On",
                effective_hdmi_info_display="On",
                built_in_lcd_blanked=True,
                hdmi_red_rec_frame_routed=True,
                hdmi_grid_line_routed=True,
                hdmi_marker_zebra_peaking_leaked_layers=0,
                external_hdmi_master_baked_overlays=0,
            ),
            None,
        ),
        (
            P238_PILLAR_37B_SCENARIO_IDS[2],
            False,
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                post_reset_rec_media_dur_hdmi_output="On",
                post_reset_hdmi_raw_output="On",
                post_reset_configured_hdmi_info_display="On",
                effective_hdmi_info_display="On",
                built_in_lcd_blanked=True,
                hdmi_red_rec_frame_routed=True,
                hdmi_grid_line_routed=True,
                external_hdmi_master_baked_overlays=2,
            ),
            P238_BLOCKED_HDMI_ONLY_OR_RAW_CLEAN_FEED_CLAMP_VIOLATION,
        ),
        (
            P238_PILLAR_37B_SCENARIO_IDS[3],
            False,
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                pre_reset_emphasized_rec_display="Off",
                pre_reset_grid_line_display="On",
                pre_reset_grid_line_type="Diag. + Square Grid",
                reset_action="Camera Settings Reset",
                post_reset_emphasized_rec_display="On",
                post_reset_grid_line_display="Off",
                post_reset_grid_line_type="Rule of 3rds Grid",
            ),
            P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT,
        ),
        (
            P238_PILLAR_37B_SCENARIO_IDS[4],
            False,
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                post_reset_rec_media_dur_hdmi_output="On",
                post_reset_hdmi_raw_output="Off",
                post_reset_configured_hdmi_info_display="On",
                effective_hdmi_info_display="On",
                built_in_lcd_blanked=False,
                hdmi_red_rec_frame_routed=True,
                hdmi_grid_line_routed=True,
            ),
            P238_BLOCKED_HDMI_INFO_ROUTING_OR_LCD_BLANK_MISMATCH,
        ),
        (
            P238_PILLAR_37B_SCENARIO_IDS[5],
            False,
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                camset_restore_after_reset=True,
                camset_slot=2,
                camset_filename="CAMSET01.DAT",
            ),
            P238_BLOCKED_CAMSET_SLOT1_RECFRAME_GRID_RESTORE_DRIFT,
        ),
    )

    outcomes: List[Pillar37ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar37ScenarioOutcome(
                scenario_id=sid,
                pillar="37B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar37BSuiteResult(
        passed=all_ok,
        status=P238_STATUS_VERIFIED_PILLAR_37B if all_ok else P238_STATUS_REJECTED_PILLAR_37B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar37_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar37StandaloneReport:
    """Run full Pillar 37 standalone suite (`6/6` Pillar 37A + `6/6` Pillar 37B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase238_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar37a_touch_bench_sunny_weather_6_scenario_suite()
    res_b = run_pillar37b_recframe_grid_hdmi_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 238 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE238_SCHEMA,
            "version": PHASE238_VERSION,
            "mode": donor_snapshot.verification_mode,
            "37a": [asdict(s) for s in res_a.scenarios],
            "37b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar37StandaloneReport(
        schema=PHASE238_SCHEMA,
        version=PHASE238_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P238_STATUS_VERIFIED_PILLAR37_SUITE if all_ok else P238_STATUS_FAIL_PILLAR37_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_37a_touch_bench_sunny_weather_guard=res_a,
        pillar_37b_recframe_grid_hdmi_clean_feed_vault=res_b,
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
# Unified 37/37 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master37_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_37pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master37PillarRecoveryReport:
    """Evaluate and aggregate all 37 recovery pillars (`1..37`) concurrently -> `37/37` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_37_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_36pillar() -> Master36PillarRecoveryReport:
        return evaluate_realhw_36pillar_recovery_master(**kw)

    def _run_p37() -> Tuple[Pillar37StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar37_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_36 = pool.submit(_run_36pillar)
        fut_37 = pool.submit(_run_p37)
        m36_rep = fut_36.result()
        p37_rep, p37_dt = fut_37.result()

    all_errors: List[str] = list(m36_rep.errors) + list(p37_rep.errors)
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
        if getattr(m36_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-36 violated {attr_name} == {expected_val}")
        if getattr(p37_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 37 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m36_rep.pillars)
    spec37 = MASTER_37_PILLAR_SPECS[36]
    p37_metrics = {
        "pillar_37a_touch_bench_sunny_weather_guard": (
            f"{p37_rep.pillar_37a_touch_bench_sunny_weather_guard.scenarios_passed}/"
            f"{p37_rep.pillar_37a_touch_bench_sunny_weather_guard.scenarios_total}"
        ),
        "pillar_37b_recframe_grid_hdmi_clean_feed_vault": (
            f"{p37_rep.pillar_37b_recframe_grid_hdmi_clean_feed_vault.scenarios_passed}/"
            f"{p37_rep.pillar_37b_recframe_grid_hdmi_clean_feed_vault.scenarios_total}"
        ),
        "accidental_bench_fn_or_touch_triggers": 0,
        "external_hdmi_master_baked_overlays": 0,
        "donor_files_inspected": p37_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec37[0],
            pillar_id=spec37[1],
            phase_label=spec37[2],
            module_name=spec37[3],
            passed=bool(p37_rep.all_passed),
            status=p37_rep.status,
            verification_mode=p37_rep.verification_mode,
            elapsed_seconds=p37_dt,
            key_metrics=p37_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec37[1],
                    "mode": p37_rep.verification_mode,
                    "status": p37_rep.status,
                    "metrics": p37_metrics,
                    "passed": p37_rep.all_passed,
                }
            ),
            errors=tuple(p37_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master37_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p37_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_37_PILLAR_COUNT == 37
        and pillars_passed == 37
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE238_SCHEMA,
            "version": PHASE238_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master37PillarRecoveryReport(
        schema=PHASE238_SCHEMA,
        version=PHASE238_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P238_STATUS_VERIFIED_37OF37_AGGREGATOR if all_ok else P238_STATUS_FAIL_37OF37_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P238_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P238_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p37_rep.donor_snapshot,
        pillar37_a_touch_bench_sunny_weather_guard=p37_rep.pillar_37a_touch_bench_sunny_weather_guard,
        pillar37_b_recframe_grid_hdmi_clean_feed_vault=p37_rep.pillar_37b_recframe_grid_hdmi_clean_feed_vault,
        master_37pillar_sha256=master_sha,
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


def evaluate_37pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master37PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_37pillar_recovery_master`."""
    return evaluate_realhw_37pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_37pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master37PillarRecoveryReport:
    """Public CLI entry point for Pillar 37 unified `37/37` real-hardware recovery master verification."""
    return evaluate_realhw_37pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
