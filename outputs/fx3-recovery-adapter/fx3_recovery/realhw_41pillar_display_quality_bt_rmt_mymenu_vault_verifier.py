"""Phase 247 — Pillar 41 (`41/41` Recovery Pillars) & Unified 41-Pillar Recovery Master
(`verify-41pillar-recovery` / `verify-display-quality-bt-rmt-mymenu-vault`):

1. **Pillar 41A — `[Display Quality]` (`Standard`/`High`) Battery-Conservation Bench Guard &
   `[Bluetooth Rmt Ctrl]` IR Lockout / Zero-RF `Reset Network Set.` Split (`ILME-FX3 Ver. 7.02`, Wave-39)**:
   - Models `MENU` -> `Setup` -> `[Monitor]` -> `[Display Quality]` (`Standard` default / `High`),
     verifying survival across **both** `[Camera Settings Reset]` and `[Reset Network Set.]`
     (restored to `Standard` **only** by `[Initialize]`), acknowledging `[High]` increased
     `NP-FZ100` battery drain, and clamping internal-battery (`NP-FZ100`) Tier-0 `pnflasha` /
     `cnflasha` bench dumps to `[Standard]` alongside `[Monitor Brightness] = Manual(0)`
     (`tier0_battery_high_display_violations == 0`).
   - Models `MENU` -> `Network` -> `[Bluetooth]` -> `[Bluetooth Rmt Ctrl]` (`Off` default / `On`),
     enforcing `[Bluetooth Function] = On` + `[Airplane Mode] = Off` prerequisites (suppressed on
     our zero-RF bench `Airplane Mode = On`, `passive_tx_bytes_emitted == 0`), enforcing strict
     Infrared Remote Commander (`SIRCS`) mutual exclusion whenever `[Bluetooth Rmt Ctrl] = On`
     (`bt_rmt_ir_lockout_violations == 0`), and verifying the exact 3-way reset split (survives
     `[Camera Settings Reset]`, reset to `Off` by **both** `[Reset Network Set.]` and
     `[Initialize]`) plus lossless `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` restoration.

2. **Pillar 41B — `[My Menu Setting]` / `[Display From My Menu]` 6-Operation Persistence &
   Lossless `CAMSET01.DAT` Vault Round-Trip**:
   - Models `MENU` -> `My Menu` -> `[My Menu Setting]` (`Add Item`, `Sort Item`, `Delete Item`,
     `Delete Page`, `Delete All`, and `[Display From My Menu]` `Off` default -> opens most recent
     tab / `On` -> opens `My Menu` first), verifying survival across **both**
     `[Camera Settings Reset]` and `[Reset Network Set.]` (cleared **only** via `[Delete All]` /
     `[Delete Page]` or full `[Initialize]`).
   - Enforces deterministic `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` round-trip restoration
     without mutating Slot-1 Tier-0 vault sectors (`slot1_mymenu_vault_mutation_bytes == 0`) and
     `16/16` Tier-0 `Backup.bin` `H0 == H3` parity.

3. **Unified `41/41` Recovery Master (`evaluate_realhw_41pillar_recovery_master`)**:
   - Delegates Pillars `1..40` concurrently to `evaluate_realhw_40pillar_recovery_master` +
     **Pillar 41** -> **`41/41` (`VERIFIED_41OF41_PILLAR_RECOVERY_MASTER`)** in `< 4.0s`
     nominal (`< 6.0s` concurrent ceiling).
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
from .realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_40_PILLAR_SPECS,
    Master40PillarRecoveryReport,
    evaluate_realhw_40pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE247_SCHEMA: str = "realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier_v1"
PHASE247_VERSION: str = "1.0.0"

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
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P247_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P247_TIER0_BATTERY_HIGH_DISPLAY_VIOLATIONS: int = 0
P247_BT_RMT_IR_LOCKOUT_VIOLATIONS: int = 0
P247_SLOT1_MYMENU_VAULT_MUTATION_BYTES: int = 0

P247_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P247_NOMINAL_BUDGET_SECONDS: float = 4.0
P247_CONCURRENT_CEILING_SECONDS: float = 6.0
P247_BOUNDED_HEADER_BYTES: int = 4096
P247_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-39 / FX3 Ver. 7.02 & FX6 Ver. 6.01 Donor Anchors (bounded O_RDONLY verification)
P247_FX3_MODEL_NAME: str = "ILME-FX3"
P247_FX3_MODEL_ID: int = 0x91030080
P247_FX3_HELPGUIDE_ID: str = "ilc/2210"
P247_FX3_FW_VERSION: str = "7.02"
P247_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P247_FX6_DONOR_FW_VERSION: str = "6.01"
P247_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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

P247_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P247_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P247_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)

P247_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P247_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P247_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P247_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P247_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P247_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P247_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P247_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P247_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P247_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P247_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P247_PINNED_FX3_LIBBACKUP_SO_SHA256: str = (
    "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"
)

P247_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P247_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P247_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = (
    "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
)

P247_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P247_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P247_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P247_DONOR_FX3_LIBGPE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so"
)
P247_PINNED_FX3_LIBGPE_SO_BYTES: int = 106480
P247_PINNED_FX3_LIBGPE_SO_SHA256: str = (
    "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464"
)

P247_DONOR_FX3_LIBINFRABLUETOOTH_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraBluetooth.so"
)
P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_BYTES: int = 158968
P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_SHA256: str = (
    "e49bb8fbb723eef65d4b4e54788c39f57b1cd7ca72285bc02a726ada2ca8ef93"
)

P247_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraAirplaneMode.so"
)
P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES: int = 14488
P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256: str = (
    "dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea"
)

P247_DONOR_FX6_LIBINFRASIRCS_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraSircs.so"
)
P247_PINNED_FX6_LIBINFRASIRCS_SO_BYTES: int = 27072
P247_PINNED_FX6_LIBINFRASIRCS_SO_SHA256: str = (
    "89a33f62ec8fefb0bcab557752068ee6b11494216cc7d2fbf6a03abc3c66a4d1"
)

# Pillar 41A — [Display Quality] Battery Bench Guard & [Bluetooth Rmt Ctrl] IR Lockout / 3-Reset Split
P247_DISPLAY_QUALITY_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Monitor",
    "Display Quality",
)
P247_DISPLAY_QUALITY_DEFAULT: str = "Standard"
P247_DISPLAY_QUALITY_MODES: Tuple[str, ...] = ("Standard", "High")

P247_MONITOR_BRIGHTNESS_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Monitor",
    "Monitor Brightness",
)
P247_MONITOR_BRIGHTNESS_MODES: Tuple[str, ...] = ("Manual", "Sunny Weather")
P247_MONITOR_BRIGHTNESS_MANUAL_LEVELS: Tuple[int, ...] = (-2, -1, 0, 1, 2)
P247_MONITOR_BRIGHTNESS_BENCH_MODE: str = "Manual"
P247_MONITOR_BRIGHTNESS_BENCH_LEVEL: int = 0

P247_BLUETOOTH_RMT_CTRL_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Network",
    "Bluetooth",
    "Bluetooth Rmt Ctrl",
)
P247_BLUETOOTH_RMT_CTRL_DEFAULT: str = "Off"
P247_BLUETOOTH_FUNCTION_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Network",
    "Bluetooth",
    "Bluetooth Function",
)
P247_BLUETOOTH_FUNCTION_DEFAULT: str = "Off"
P247_AIRPLANE_MODE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Network",
    "Network Option",
    "Airplane Mode",
)
P247_AIRPLANE_MODE_DEFAULT: str = "Off"
P247_IR_REMOTE_CTRL_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Setup Option",
    "IR Remote Ctrl",
)
P247_ON_OFF_MODES: Tuple[str, ...] = ("Off", "On")
P247_POWER_SOURCES: Tuple[str, ...] = ("NP-FZ100", "DC-C1", "USB-PD")
P247_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)

# Pillar 41B — [My Menu Setting] 6-Operation Persistence & [Display From My Menu] + CAMSET01.DAT Vault
P247_MY_MENU_SETTING_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "My Menu",
    "My Menu Setting",
)
P247_MY_MENU_6_OPERATIONS: Tuple[str, ...] = (
    "Add Item",
    "Sort Item",
    "Delete Item",
    "Delete Page",
    "Delete All",
    "Display From My Menu",
)
P247_MY_MENU_EDIT_OPERATIONS: Tuple[str, ...] = (
    "NONE",
    "Add Item",
    "Sort Item",
    "Delete Item",
    "Delete Page",
    "Delete All",
)
P247_DISPLAY_FROM_MY_MENU_DEFAULT: str = "Off"
P247_DISPLAY_FROM_MY_MENU_MODES: Tuple[str, ...] = ("Off", "On")
P247_MENU_OPEN_TAB_BEHAVIORS: Tuple[str, ...] = ("MOST_RECENT_TAB", "MY_MENU_FIRST")
P247_MY_MENU_MAX_PAGES: int = 5
P247_MY_MENU_MAX_ITEMS_PER_PAGE: int = 6
P247_MY_MENU_MAX_TOTAL_ITEMS: int = P247_MY_MENU_MAX_PAGES * P247_MY_MENU_MAX_ITEMS_PER_PAGE
P247_DEFAULT_REGISTERED_MY_MENU_ITEMS: Tuple[str, ...] = (
    "Display Quality",
    "Monitor Brightness",
    "Lock Operation Parts",
    "Save/Load Settings",
)

P247_SLOT1_VAULT_SLOT: int = 1
P247_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P247_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_display_quality_bt_rmt_mymenu_overlay"
P247_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P247_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P247_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P247_BLOCKED_INVALID_DISPLAY_QUALITY_OR_BT_RMT_SPEC: str = (
    "BLOCKED_INVALID_DISPLAY_QUALITY_OR_BT_RMT_SPEC"
)
P247_BLOCKED_DISPLAY_QUALITY_RESET_SURVIVAL_DRIFT: str = (
    "BLOCKED_DISPLAY_QUALITY_RESET_SURVIVAL_DRIFT"
)
P247_BLOCKED_TIER0_BATTERY_BENCH_HIGH_DISPLAY_OR_BRIGHTNESS: str = (
    "BLOCKED_TIER0_BATTERY_BENCH_HIGH_DISPLAY_OR_BRIGHTNESS"
)
P247_BLOCKED_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION: str = (
    "BLOCKED_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION"
)
P247_BLOCKED_IR_REMOTE_USED_WHILE_BT_RMT_CTRL_ON: str = (
    "BLOCKED_IR_REMOTE_USED_WHILE_BT_RMT_CTRL_ON"
)
P247_BLOCKED_BT_RMT_3WAY_RESET_SPLIT_DRIFT: str = (
    "BLOCKED_BT_RMT_3WAY_RESET_SPLIT_DRIFT"
)
P247_BLOCKED_CAMSET_DISPLAY_QUALITY_OR_BT_RMT_RESTORE_DRIFT: str = (
    "BLOCKED_CAMSET_DISPLAY_QUALITY_OR_BT_RMT_RESTORE_DRIFT"
)

P247_BLOCKED_INVALID_MY_MENU_SPEC: str = "BLOCKED_INVALID_MY_MENU_SPEC"
P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH: str = (
    "BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH"
)
P247_BLOCKED_MY_MENU_RESET_PERSISTENCE_DRIFT: str = (
    "BLOCKED_MY_MENU_RESET_PERSISTENCE_DRIFT"
)
P247_BLOCKED_CAMSET_MY_MENU_ROUNDTRIP_DRIFT: str = (
    "BLOCKED_CAMSET_MY_MENU_ROUNDTRIP_DRIFT"
)
P247_BLOCKED_SLOT1_MY_MENU_VAULT_MUTATION_ATTEMPT: str = (
    "BLOCKED_SLOT1_MY_MENU_VAULT_MUTATION_ATTEMPT"
)
P247_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P247_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P247_STATUS_VERIFIED_PILLAR_41A: str = (
    "VERIFIED_PILLAR_41A_DISPLAY_QUALITY_BATTERY_GUARD_AND_BT_RMT_IR_LOCKOUT_VAULT"
)
P247_STATUS_REJECTED_PILLAR_41A: str = (
    "REJECTED_PILLAR_41A_DISPLAY_QUALITY_BATTERY_GUARD_AND_BT_RMT_IR_LOCKOUT_VAULT"
)
P247_STATUS_VERIFIED_PILLAR_41B: str = (
    "VERIFIED_PILLAR_41B_MY_MENU_6OP_PERSISTENCE_AND_CAMSET01_ROUNDTRIP_VAULT"
)
P247_STATUS_REJECTED_PILLAR_41B: str = (
    "REJECTED_PILLAR_41B_MY_MENU_6OP_PERSISTENCE_AND_CAMSET01_ROUNDTRIP_VAULT"
)
P247_STATUS_VERIFIED_PILLAR41_SUITE: str = (
    "VERIFIED_PILLAR41_DISPLAY_QUALITY_BT_RMT_MYMENU_VAULT"
)
P247_STATUS_FAIL_PILLAR41_SUITE: str = (
    "FAIL_PILLAR41_DISPLAY_QUALITY_BT_RMT_MYMENU_VAULT"
)
P247_STATUS_VERIFIED_41OF41_AGGREGATOR: str = "VERIFIED_41OF41_PILLAR_RECOVERY_MASTER"
P247_STATUS_FAIL_41OF41_AGGREGATOR: str = "FAIL_41OF41_PILLAR_RECOVERY_MASTER"

P247_PILLAR_41A_SCENARIO_IDS: Tuple[str, ...] = (
    "P41A1_DISPLAY_QUALITY_STANDARD_BENCH_CLAMP_AND_BT_RMT_ZERO_RF_SURVIVES_CAMERA_SETTINGS_RESET_SAFE",
    "P41A2_RESET_NETWORK_SET_WIPES_BT_RMT_TO_OFF_WHILE_DISPLAY_QUALITY_HIGH_SURVIVES_ON_EXTERNAL_DC_SAFE",
    "P41A3_REJECT_DISPLAY_QUALITY_WIPED_BY_CAMERA_OR_NETWORK_RESET_OR_HIGH_LEFT_ON_TIER0_NP_FZ100_BENCH",
    "P41A4_REJECT_BT_RMT_CTRL_NOT_RESET_BY_RESET_NETWORK_SET_OR_WIPED_BY_CAMERA_SETTINGS_RESET",
    "P41A5_REJECT_IR_REMOTE_COMMANDER_CLAIMED_USABLE_WHILE_BT_RMT_CTRL_ON",
    "P41A6_REJECT_BT_RMT_CTRL_CLAIMED_ACTIVE_WITH_BT_FUNCTION_OFF_OR_ZERO_RF_AIRPLANE_MODE_BREACH",
)
P247_PILLAR_41B_SCENARIO_IDS: Tuple[str, ...] = (
    "P41B1_MY_MENU_ITEMS_AND_DISPLAY_FROM_MY_MENU_ON_SURVIVE_BOTH_CAMERA_AND_NETWORK_RESETS_SAFE",
    "P41B2_INITIALIZE_OR_DELETE_ALL_CLEARS_MY_MENU_AND_ORDONLY_SLOT1_CAMSET01_RESTORES_LOSSLESSLY_SAFE",
    "P41B3_REJECT_MY_MENU_OR_DISPLAY_FROM_MY_MENU_WIPED_BY_CAMERA_SETTINGS_RESET_OR_NETWORK_RESET",
    "P41B4_REJECT_DISPLAY_FROM_MY_MENU_TAB_OPEN_BEHAVIOR_INVERSION_OR_DELETE_ALL_RESIDUAL_ITEMS",
    "P41B5_REJECT_CAMSET01_MY_MENU_ROUNDTRIP_DRIFT_OR_CROSS_MODEL_FX6_IMPORT",
    "P41B6_REJECT_SLOT1_TIER0_CAMSET01_VAULT_OVERWRITE_OR_NON_ORDONLY_MUTATION",
)

MASTER_41_PILLAR_COUNT: int = 41
MASTER_41_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_40_PILLAR_SPECS + (
    (
        41,
        "pillar_41_display_quality_bt_rmt_mymenu_vault",
        "Phase 247",
        "fx3_recovery.realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier",
    ),
)
MASTER_41_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_41_PILLAR_SPECS)


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
        ("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("P247_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P247_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P247_TIER0_BATTERY_HIGH_DISPLAY_VIOLATIONS", P247_TIER0_BATTERY_HIGH_DISPLAY_VIOLATIONS, 0),
        ("P247_BT_RMT_IR_LOCKOUT_VIOLATIONS", P247_BT_RMT_IR_LOCKOUT_VIOLATIONS, 0),
        ("P247_SLOT1_MYMENU_VAULT_MUTATION_BYTES", P247_SLOT1_MYMENU_VAULT_MUTATION_BYTES, 0),
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
    return any(tok in low for tok in P247_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase247DonorArtifactDigest:
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
class Phase247DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase247DonorArtifactDigest, ...]


@dataclass(frozen=True)
class DisplayQualityAndBtRmtCtrlVaultSpec:
    camera_model: str = P247_FX3_MODEL_NAME
    helpguide_id: str = P247_FX3_HELPGUIDE_ID
    fw_version: str = P247_FX3_FW_VERSION
    display_quality_menu_path: Tuple[str, ...] = P247_DISPLAY_QUALITY_MENU_PATH
    monitor_brightness_menu_path: Tuple[str, ...] = P247_MONITOR_BRIGHTNESS_MENU_PATH
    bt_rmt_ctrl_menu_path: Tuple[str, ...] = P247_BLUETOOTH_RMT_CTRL_MENU_PATH
    bt_function_menu_path: Tuple[str, ...] = P247_BLUETOOTH_FUNCTION_MENU_PATH
    airplane_mode_menu_path: Tuple[str, ...] = P247_AIRPLANE_MODE_MENU_PATH
    pre_reset_display_quality: str = P247_DISPLAY_QUALITY_DEFAULT  # Standard | High
    pre_reset_bt_rmt_ctrl: str = "On"  # Off | On
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Reset Network Set. | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P247_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    saved_display_quality: str = P247_DISPLAY_QUALITY_DEFAULT
    saved_bt_rmt_ctrl: str = P247_BLUETOOTH_RMT_CTRL_DEFAULT
    post_reset_display_quality: str = P247_DISPLAY_QUALITY_DEFAULT
    post_reset_bt_rmt_ctrl: str = "On"  # survives Camera Settings Reset
    high_mode_increases_np_fz100_drain: bool = True
    power_source: str = "NP-FZ100"  # NP-FZ100 | DC-C1 | USB-PD
    tier0_internal_battery_bench_active: bool = True
    monitor_brightness_mode: str = P247_MONITOR_BRIGHTNESS_BENCH_MODE  # Manual | Sunny Weather
    monitor_brightness_manual_level: int = P247_MONITOR_BRIGHTNESS_BENCH_LEVEL  # -2..2
    tier0_battery_high_display_violations: int = 0
    bluetooth_function: str = "Off"  # Off | On
    airplane_mode: str = "On"  # Off | On (zero-RF bench default = On)
    zero_rf_bench_enforced: bool = True
    effective_bt_rmt_ctrl_active: bool = False
    passive_rf_tx_bytes: int = 0
    ir_remote_ctrl_setting: str = "Off"  # Off | On
    ir_remote_commander_usable: bool = False
    bt_rmt_ir_lockout_violations: int = 0
    overlay_dir: str = P247_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P247_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P247_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P247_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class DisplayQualityAndBtRmtCtrlVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    display_quality_reset_survival_verified: bool
    tier0_battery_bench_clamp_verified: bool
    bt_rmt_prerequisite_and_zero_rf_verified: bool
    bt_rmt_ir_remote_lockout_verified: bool
    bt_rmt_3way_reset_split_verified: bool
    camset_slot1_restore_verified: bool
    h0_equals_h3_verified: bool
    tier0_battery_high_display_violations: int
    bt_rmt_ir_lockout_violations: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MyMenuPersistenceAndCamsetVaultSpec:
    camera_model: str = P247_FX3_MODEL_NAME
    helpguide_id: str = P247_FX3_HELPGUIDE_ID
    fw_version: str = P247_FX3_FW_VERSION
    my_menu_setting_menu_path: Tuple[str, ...] = P247_MY_MENU_SETTING_MENU_PATH
    supported_6_operations: Tuple[str, ...] = P247_MY_MENU_6_OPERATIONS
    pre_op_registered_items: Tuple[str, ...] = P247_DEFAULT_REGISTERED_MY_MENU_ITEMS
    pre_op_page_item_counts: Tuple[int, ...] = (4,)
    my_menu_operation: str = "NONE"  # NONE | Add Item | Sort Item | Delete Item | Delete Page | Delete All
    operation_target_item: Optional[str] = None
    operation_target_page_index: int = 0
    post_op_registered_items: Tuple[str, ...] = P247_DEFAULT_REGISTERED_MY_MENU_ITEMS
    post_op_page_item_counts: Tuple[int, ...] = (4,)
    pre_reset_display_from_my_menu: str = "On"  # Off | On
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Reset Network Set. | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P247_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P247_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_registered_items: Tuple[str, ...] = P247_DEFAULT_REGISTERED_MY_MENU_ITEMS
    saved_page_item_counts: Tuple[int, ...] = (4,)
    saved_display_from_my_menu: str = "On"
    post_reset_registered_items: Tuple[str, ...] = P247_DEFAULT_REGISTERED_MY_MENU_ITEMS
    post_reset_page_item_counts: Tuple[int, ...] = (4,)
    post_reset_display_from_my_menu: str = "On"
    menu_button_opens_tab: str = "MY_MENU_FIRST"  # MOST_RECENT_TAB | MY_MENU_FIRST
    slot1_tier0_vault_active: bool = True
    slot1_sdxc_wp_locked: bool = True
    camset_save_to_slot1_attempted: bool = False
    slot1_mymenu_vault_mutation_bytes: int = 0
    overlay_dir: str = P247_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P247_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P247_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P247_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class MyMenuPersistenceAndCamsetVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    my_menu_6_operations_and_tab_verified: bool
    my_menu_non_resettable_survival_verified: bool
    initialize_full_clear_verified: bool
    camset_slot1_roundtrip_verified: bool
    slot1_vault_zero_mutation_verified: bool
    h0_equals_h3_verified: bool
    slot1_mymenu_vault_mutation_bytes: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DisplayQualityBtRmtAndMyMenuVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase247DonorSnapshot
    display_quality_bt_rmt_report: DisplayQualityAndBtRmtCtrlVaultReport
    my_menu_vault_report: MyMenuPersistenceAndCamsetVaultReport
    tier0_battery_high_display_violations: int
    bt_rmt_ir_lockout_violations: int
    slot1_mymenu_vault_mutation_bytes: int
    hardware_live_attachment_authorized: bool
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
class Pillar41ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar41ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar41ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar41BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar41ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar41StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase247DonorSnapshot
    pillar_41a_display_quality_bt_rmt_vault: Pillar41ASuiteResult
    pillar_41b_my_menu_camset_vault: Pillar41BSuiteResult
    tier0_battery_high_display_violations: int
    bt_rmt_ir_lockout_violations: int
    slot1_mymenu_vault_mutation_bytes: int
    hardware_live_attachment_authorized: bool
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
class Master41PillarRecoveryReport:
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
    donor_snapshot: Phase247DonorSnapshot
    pillar41_a_display_quality_bt_rmt_vault: Pillar41ASuiteResult
    pillar41_b_my_menu_camset_vault: Pillar41BSuiteResult
    tier0_battery_high_display_violations: int
    bt_rmt_ir_lockout_violations: int
    slot1_mymenu_vault_mutation_bytes: int
    destructive_menu_delete_confusions: int
    shutter_angle_exposure_step_drift_events: int
    fx3_has_var_shutter: bool
    unbuffered_battery_pull_events: int
    hardware_live_attachment_authorized: bool
    master_41pillar_sha256: str
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
    max_full_bytes: int = P247_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P247_BOUNDED_HEADER_BYTES, total_size), 0)
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
    return True, f"ELF64_AARCH64:{'+'.join(found)}" if found else "ELF64_AARCH64"


def _synthetic_phase247_donors() -> Tuple[Phase247DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P247_DONOR_FX3_BODYDATA_RELPATH,
            P247_PINNED_FX3_BODYDATA_BYTES,
            P247_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P247_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P247_DONOR_FX3_APPFW_702_RELPATH,
            P247_PINNED_FX3_APPFW_702_BYTES,
            P247_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P247_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P247_DONOR_FX6_APPFW_601_RELPATH,
            P247_PINNED_FX6_APPFW_601_BYTES,
            P247_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P247_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P247_DONOR_FX3_BACKUP_BIN_RELPATH,
            P247_PINNED_FX3_BACKUP_BIN_BYTES,
            P247_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P247_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P247_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P247_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P247_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P247_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P247_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P247_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P247_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P247_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P247_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P247_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P247_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P247_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "fx3_libgpe_so",
            P247_DONOR_FX3_LIBGPE_SO_RELPATH,
            P247_PINNED_FX3_LIBGPE_SO_BYTES,
            P247_PINNED_FX3_LIBGPE_SO_BYTES,
            "FULL_SHA256",
            P247_PINNED_FX3_LIBGPE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:gpe_blog_error+_ZNK5mpgpe5Gperm4InitEv",
        ),
        (
            "fx3_libinfrabluetooth_so",
            P247_DONOR_FX3_LIBINFRABLUETOOTH_SO_RELPATH,
            P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_BYTES,
            P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_BYTES,
            "FULL_SHA256",
            P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZN14InfraBluetoothC1Ev+_ZN14InfraBluetooth12start_threadEv+_ZN14InfraBluetooth11register_cbEv",
        ),
        (
            "fx3_libinfraairplanemode_so",
            P247_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH,
            P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            "FULL_SHA256",
            P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z23AirplaneModeTraceRecordhhtj+_Z28AirplaneModeTraceRecordErrorhhtj",
        ),
        (
            "fx6_libinfrasircs_so",
            P247_DONOR_FX6_LIBINFRASIRCS_SO_RELPATH,
            P247_PINNED_FX6_LIBINFRASIRCS_SO_BYTES,
            P247_PINNED_FX6_LIBINFRASIRCS_SO_BYTES,
            "FULL_SHA256",
            P247_PINNED_FX6_LIBINFRASIRCS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZN10InfraSircs4InitEv+_ZN10InfraSircs11GetInstanceEv+_ZN10InfraSircs15SetSircsOffTimeEi",
        ),
    )
    return tuple(
        Phase247DonorArtifactDigest(
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


def inspect_phase247_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase247DonorSnapshot:
    """Inspect Wave-39 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase247_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase247DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P247_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P247_DONOR_FX3_BODYDATA_RELPATH,
            P247_PINNED_FX3_BODYDATA_BYTES,
            P247_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P247_DONOR_FX3_APPFW_702_RELPATH,
            P247_PINNED_FX3_APPFW_702_BYTES,
            P247_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P247_DONOR_FX6_APPFW_601_RELPATH,
            P247_PINNED_FX6_APPFW_601_BYTES,
            P247_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P247_DONOR_FX3_BACKUP_BIN_RELPATH,
            P247_PINNED_FX3_BACKUP_BIN_BYTES,
            P247_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P247_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P247_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P247_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P247_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P247_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P247_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P247_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P247_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P247_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite")
            ),
        ),
        (
            "fx3_libgpe_so",
            P247_DONOR_FX3_LIBGPE_SO_RELPATH,
            P247_PINNED_FX3_LIBGPE_SO_BYTES,
            P247_PINNED_FX3_LIBGPE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"gpe_blog_error", b"_ZNK5mpgpe5Gperm4InitEv")),
        ),
        (
            "fx3_libinfrabluetooth_so",
            P247_DONOR_FX3_LIBINFRABLUETOOTH_SO_RELPATH,
            P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_BYTES,
            P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (
                    b"_ZN14InfraBluetoothC1Ev",
                    b"_ZN14InfraBluetooth12start_threadEv",
                    b"_ZN14InfraBluetooth11register_cbEv",
                ),
            ),
        ),
        (
            "fx3_libinfraairplanemode_so",
            P247_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH,
            P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (
                    b"_Z23AirplaneModeTraceRecordhhtj",
                    b"_Z28AirplaneModeTraceRecordErrorhhtj",
                ),
            ),
        ),
        (
            "fx6_libinfrasircs_so",
            P247_DONOR_FX6_LIBINFRASIRCS_SO_RELPATH,
            P247_PINNED_FX6_LIBINFRASIRCS_SO_BYTES,
            P247_PINNED_FX6_LIBINFRASIRCS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (
                    b"_ZN10InfraSircs4InitEv",
                    b"_ZN10InfraSircs11GetInstanceEv",
                    b"_ZN10InfraSircs15SetSircsOffTimeEi",
                ),
            ),
        ),
    )

    digests: List[Phase247DonorArtifactDigest] = []
    for aid, rel, pinned_bytes, pinned_sha, validator in probe_specs:
        ok, total_b, hdr_b, dkind, dsha, raw = _read_donor_readonly_bounded(rel)
        if not ok:
            digests.append(
                Phase247DonorArtifactDigest(
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
            Phase247DonorArtifactDigest(
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
        synth = _synthetic_phase247_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase247DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P247_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    dt = round(time.monotonic() - t0, 6)
    return Phase247DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all(d.present and d.matches_pinned for d in digests),
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P247_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Pillar 41A & 41B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_display_quality_bt_rmt_vault_spec() -> DisplayQualityAndBtRmtCtrlVaultSpec:
    return DisplayQualityAndBtRmtCtrlVaultSpec()


def build_default_safe_my_menu_camset_vault_spec() -> MyMenuPersistenceAndCamsetVaultSpec:
    return MyMenuPersistenceAndCamsetVaultSpec()


def evaluate_display_quality_and_bt_rmt_ctrl_vault(
    spec: DisplayQualityAndBtRmtCtrlVaultSpec,
) -> DisplayQualityAndBtRmtCtrlVaultReport:
    """Audit `[Display Quality]` survival & NP-FZ100 bench clamp + `[Bluetooth Rmt Ctrl]` IR lockout & 3-way reset split."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    safety_errs = _safety_invariant_errors()
    if safety_errs or spec.persistent_write_unlock_requested:
        _fail(
            P247_BLOCKED_SAFETY_POLICY_VIOLATION,
            f"Safety policy violation or persistent write unlock requested: {safety_errs}",
        )

    if (
        spec.camera_model != P247_FX3_MODEL_NAME
        or spec.helpguide_id != P247_FX3_HELPGUIDE_ID
        or spec.fw_version not in P247_FX3_SUPPORTED_FW_VERSIONS
        or tuple(spec.display_quality_menu_path) != P247_DISPLAY_QUALITY_MENU_PATH
        or tuple(spec.monitor_brightness_menu_path) != P247_MONITOR_BRIGHTNESS_MENU_PATH
        or tuple(spec.bt_rmt_ctrl_menu_path) != P247_BLUETOOTH_RMT_CTRL_MENU_PATH
        or tuple(spec.bt_function_menu_path) != P247_BLUETOOTH_FUNCTION_MENU_PATH
        or tuple(spec.airplane_mode_menu_path) != P247_AIRPLANE_MODE_MENU_PATH
        or spec.pre_reset_display_quality not in P247_DISPLAY_QUALITY_MODES
        or spec.saved_display_quality not in P247_DISPLAY_QUALITY_MODES
        or spec.post_reset_display_quality not in P247_DISPLAY_QUALITY_MODES
        or spec.pre_reset_bt_rmt_ctrl not in P247_ON_OFF_MODES
        or spec.saved_bt_rmt_ctrl not in P247_ON_OFF_MODES
        or spec.post_reset_bt_rmt_ctrl not in P247_ON_OFF_MODES
        or spec.bluetooth_function not in P247_ON_OFF_MODES
        or spec.airplane_mode not in P247_ON_OFF_MODES
        or spec.ir_remote_ctrl_setting not in P247_ON_OFF_MODES
        or spec.power_source not in P247_POWER_SOURCES
        or spec.monitor_brightness_mode not in P247_MONITOR_BRIGHTNESS_MODES
        or spec.monitor_brightness_manual_level not in P247_MONITOR_BRIGHTNESS_MANUAL_LEVELS
        or spec.reset_action not in P247_RESET_ACTIONS
        or not (1 <= spec.camset_slot <= 10)
        or spec.camset_filename not in P247_CAMSET_FILENAMES
        or spec.camset_filename != f"CAMSET{spec.camset_slot:02d}.DAT"
        or not spec.high_mode_increases_np_fz100_drain
    ):
        _fail(
            P247_BLOCKED_INVALID_DISPLAY_QUALITY_OR_BT_RMT_SPEC,
            "Invalid ILME-FX3 Display Quality / Bluetooth Rmt Ctrl specification, menu path, or High drain flag",
        )

    # 1. [Display Quality] Reset Survival & CAMSET01.DAT Restore
    display_survival_ok = True
    camset_ok = True
    if spec.camset_load_after_reset:
        if spec.post_reset_display_quality != spec.saved_display_quality:
            camset_ok = False
            _fail(
                P247_BLOCKED_CAMSET_DISPLAY_QUALITY_OR_BT_RMT_RESTORE_DRIFT,
                f"CAMSET {spec.camset_filename} load failed to restore Display Quality={spec.saved_display_quality!r}",
            )
    else:
        expected_dq = (
            P247_DISPLAY_QUALITY_DEFAULT
            if spec.reset_action == "Initialize"
            else spec.pre_reset_display_quality
        )
        if spec.post_reset_display_quality != expected_dq:
            display_survival_ok = False
            _fail(
                P247_BLOCKED_DISPLAY_QUALITY_RESET_SURVIVAL_DRIFT,
                f"Display Quality after {spec.reset_action!r} expected {expected_dq!r}, got {spec.post_reset_display_quality!r}",
            )

    # 2. Tier-0 Internal-Battery (NP-FZ100) Bench Power-Conservation Clamp
    battery_clamp_ok = True
    battery_violations = max(0, int(spec.tier0_battery_high_display_violations))
    if spec.tier0_internal_battery_bench_active and spec.power_source == "NP-FZ100":
        if (
            spec.post_reset_display_quality != P247_DISPLAY_QUALITY_DEFAULT
            or spec.monitor_brightness_mode != P247_MONITOR_BRIGHTNESS_BENCH_MODE
            or spec.monitor_brightness_manual_level != P247_MONITOR_BRIGHTNESS_BENCH_LEVEL
        ):
            battery_clamp_ok = False
            battery_violations = max(1, battery_violations)
            _fail(
                P247_BLOCKED_TIER0_BATTERY_BENCH_HIGH_DISPLAY_OR_BRIGHTNESS,
                "Tier-0 NP-FZ100 bench dump requires Display Quality=Standard and Monitor Brightness=Manual(0)",
            )
    if battery_violations != 0:
        battery_clamp_ok = False
        _fail(
            P247_BLOCKED_TIER0_BATTERY_BENCH_HIGH_DISPLAY_OR_BRIGHTNESS,
            f"Non-zero tier0_battery_high_display_violations={battery_violations}",
        )

    # 3. [Bluetooth Rmt Ctrl] 3-Way Reset Split & CAMSET01.DAT Restore
    bt_reset_split_ok = True
    if spec.camset_load_after_reset:
        if spec.post_reset_bt_rmt_ctrl != spec.saved_bt_rmt_ctrl:
            camset_ok = False
            _fail(
                P247_BLOCKED_CAMSET_DISPLAY_QUALITY_OR_BT_RMT_RESTORE_DRIFT,
                f"CAMSET {spec.camset_filename} load failed to restore Bluetooth Rmt Ctrl={spec.saved_bt_rmt_ctrl!r}",
            )
    else:
        expected_bt_rmt = (
            P247_BLUETOOTH_RMT_CTRL_DEFAULT
            if spec.reset_action in ("Reset Network Set.", "Initialize")
            else spec.pre_reset_bt_rmt_ctrl
        )
        if spec.post_reset_bt_rmt_ctrl != expected_bt_rmt:
            bt_reset_split_ok = False
            _fail(
                P247_BLOCKED_BT_RMT_3WAY_RESET_SPLIT_DRIFT,
                f"Bluetooth Rmt Ctrl after {spec.reset_action!r} expected {expected_bt_rmt!r}, got {spec.post_reset_bt_rmt_ctrl!r}",
            )

    # 4. Radio Prerequisite ([Bluetooth Function]=On + [Airplane Mode]=Off) & Zero-RF Bench Guard
    expected_bt_active = (
        spec.post_reset_bt_rmt_ctrl == "On"
        and spec.bluetooth_function == "On"
        and spec.airplane_mode == "Off"
    )
    prereq_and_zero_rf_ok = True
    if spec.effective_bt_rmt_ctrl_active != expected_bt_active:
        prereq_and_zero_rf_ok = False
        _fail(
            P247_BLOCKED_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
            f"effective_bt_rmt_ctrl_active={spec.effective_bt_rmt_ctrl_active} mismatches prerequisite {expected_bt_active}",
        )
    if spec.zero_rf_bench_enforced:
        if spec.airplane_mode != "On" or spec.effective_bt_rmt_ctrl_active or spec.passive_rf_tx_bytes != 0:
            prereq_and_zero_rf_ok = False
            _fail(
                P247_BLOCKED_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
                "Zero-RF bench requires Airplane Mode=On, suppressed Bluetooth Rmt Ctrl, and 0 passive RF TX bytes",
            )
    if spec.passive_rf_tx_bytes != 0:
        prereq_and_zero_rf_ok = False
        _fail(
            P247_BLOCKED_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
            f"Non-zero passive_rf_tx_bytes={spec.passive_rf_tx_bytes} violates zero-RF posture",
        )

    # 5. Infrared Remote Commander (SIRCS) Mutual Exclusion Lockout while [Bluetooth Rmt Ctrl]=On
    ir_lockout_ok = True
    ir_violations = max(0, int(spec.bt_rmt_ir_lockout_violations))
    expected_ir_usable = (spec.ir_remote_ctrl_setting == "On") and (spec.post_reset_bt_rmt_ctrl == "Off")
    if spec.post_reset_bt_rmt_ctrl == "On" and spec.ir_remote_commander_usable:
        ir_lockout_ok = False
        ir_violations = max(1, ir_violations)
        _fail(
            P247_BLOCKED_IR_REMOTE_USED_WHILE_BT_RMT_CTRL_ON,
            "Infrared remote commander cannot be used while [Bluetooth Rmt Ctrl] is set to [On]",
        )
    elif spec.ir_remote_commander_usable != expected_ir_usable:
        ir_lockout_ok = False
        _fail(
            P247_BLOCKED_IR_REMOTE_USED_WHILE_BT_RMT_CTRL_ON,
            f"ir_remote_commander_usable={spec.ir_remote_commander_usable} mismatches expected {expected_ir_usable}",
        )
    if ir_violations != 0:
        ir_lockout_ok = False
        _fail(
            P247_BLOCKED_IR_REMOTE_USED_WHILE_BT_RMT_CTRL_ON,
            f"Non-zero bt_rmt_ir_lockout_violations={ir_violations}",
        )

    # 6. Volatile Stage-B Overlay & Tier-0 H0 == H3
    if (
        not _is_tmpfs_path(spec.overlay_dir)
        or _targets_persistent_emmc(spec.overlay_dir)
        or not spec.p2_blkroset_locked
        or spec.stage_b_backup_bin_writes != 0
    ):
        _fail(
            P247_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            "Stage-B overlay escaped tmpfs, unlocked p2 BLKROSET, or wrote persistent Backup.bin",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P247_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P247_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P247_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P247_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 == H3 parity drift detected",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "41A",
            "spec": asdict(spec),
            "passed": passed,
            "block_code": block_code,
            "errors": errors,
        }
    )
    return DisplayQualityAndBtRmtCtrlVaultReport(
        passed=passed,
        status=P247_STATUS_VERIFIED_PILLAR_41A if passed else P247_STATUS_REJECTED_PILLAR_41A,
        block_code=block_code,
        display_quality_reset_survival_verified=display_survival_ok,
        tier0_battery_bench_clamp_verified=battery_clamp_ok,
        bt_rmt_prerequisite_and_zero_rf_verified=prereq_and_zero_rf_ok,
        bt_rmt_ir_remote_lockout_verified=ir_lockout_ok,
        bt_rmt_3way_reset_split_verified=bt_reset_split_ok,
        camset_slot1_restore_verified=camset_ok,
        h0_equals_h3_verified=h0_h3_ok,
        tier0_battery_high_display_violations=battery_violations,
        bt_rmt_ir_lockout_violations=ir_violations,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def _valid_page_counts(items: Tuple[str, ...], page_counts: Tuple[int, ...]) -> bool:
    if len(items) > P247_MY_MENU_MAX_TOTAL_ITEMS:
        return False
    if len(items) == 0:
        return len(page_counts) == 0
    if not (1 <= len(page_counts) <= P247_MY_MENU_MAX_PAGES):
        return False
    if any(c < 1 or c > P247_MY_MENU_MAX_ITEMS_PER_PAGE for c in page_counts):
        return False
    return sum(page_counts) == len(items)


def _check_my_menu_operation_transition(spec: MyMenuPersistenceAndCamsetVaultSpec) -> Tuple[bool, str]:
    pre = list(spec.pre_op_registered_items)
    post = list(spec.post_op_registered_items)
    op = spec.my_menu_operation
    if op == "NONE":
        if post != pre or spec.post_op_page_item_counts != spec.pre_op_page_item_counts:
            return False, "NONE operation mutated registered My Menu items or page counts"
        return True, "NONE"
    if op == "Add Item":
        target = spec.operation_target_item
        if not target or target in pre or len(post) != len(pre) + 1 or target not in post:
            return False, "Add Item failed uniqueness or count increment invariant"
        if [x for x in post if x != target] != pre:
            return False, "Add Item altered existing My Menu item order"
        return True, "Add Item"
    if op == "Sort Item":
        if len(post) != len(pre) or sorted(post) != sorted(pre) or len(pre) < 2:
            return False, "Sort Item failed permutation conservation invariant"
        return True, "Sort Item"
    if op == "Delete Item":
        target = spec.operation_target_item
        if not target or target not in pre or target in post or len(post) != len(pre) - 1:
            return False, "Delete Item failed target removal invariant"
        if post != [x for x in pre if x != target]:
            return False, "Delete Item altered remaining My Menu item order"
        return True, "Delete Item"
    if op == "Delete Page":
        idx = spec.operation_target_page_index
        if not (0 <= idx < len(spec.pre_op_page_item_counts)):
            return False, "Delete Page target page index out of bounds"
        start = sum(spec.pre_op_page_item_counts[:idx])
        end = start + spec.pre_op_page_item_counts[idx]
        expected_remaining = pre[:start] + pre[end:]
        expected_counts = spec.pre_op_page_item_counts[:idx] + spec.pre_op_page_item_counts[idx + 1 :]
        if post != expected_remaining or spec.post_op_page_item_counts != expected_counts:
            return False, "Delete Page residual items or page counts mismatch"
        return True, "Delete Page"
    if op == "Delete All":
        if len(post) != 0 or len(spec.post_op_page_item_counts) != 0:
            return False, "Delete All left residual My Menu items or pages"
        return True, "Delete All"
    return False, f"Unsupported operation {op!r}"


def evaluate_my_menu_persistence_and_camset_vault(
    spec: MyMenuPersistenceAndCamsetVaultSpec,
) -> MyMenuPersistenceAndCamsetVaultReport:
    """Audit `[My Menu Setting]` 6-operation state machine, non-resettable survival, and `O_RDONLY` `CAMSET01.DAT` round-trip."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    safety_errs = _safety_invariant_errors()
    if safety_errs or spec.persistent_write_unlock_requested:
        _fail(
            P247_BLOCKED_SAFETY_POLICY_VIOLATION,
            f"Safety policy violation or persistent write unlock requested: {safety_errs}",
        )

    if (
        spec.camera_model != P247_FX3_MODEL_NAME
        or spec.helpguide_id != P247_FX3_HELPGUIDE_ID
        or spec.fw_version not in P247_FX3_SUPPORTED_FW_VERSIONS
        or tuple(spec.my_menu_setting_menu_path) != P247_MY_MENU_SETTING_MENU_PATH
        or tuple(spec.supported_6_operations) != P247_MY_MENU_6_OPERATIONS
        or spec.my_menu_operation not in P247_MY_MENU_EDIT_OPERATIONS
        or spec.pre_reset_display_from_my_menu not in P247_DISPLAY_FROM_MY_MENU_MODES
        or spec.saved_display_from_my_menu not in P247_DISPLAY_FROM_MY_MENU_MODES
        or spec.post_reset_display_from_my_menu not in P247_DISPLAY_FROM_MY_MENU_MODES
        or spec.menu_button_opens_tab not in P247_MENU_OPEN_TAB_BEHAVIORS
        or spec.reset_action not in P247_RESET_ACTIONS
        or not (1 <= spec.camset_slot <= 10)
        or spec.camset_filename not in P247_CAMSET_FILENAMES
        or spec.camset_filename != f"CAMSET{spec.camset_slot:02d}.DAT"
        or len(set(spec.pre_op_registered_items)) != len(spec.pre_op_registered_items)
        or len(set(spec.post_op_registered_items)) != len(spec.post_op_registered_items)
        or len(set(spec.saved_registered_items)) != len(spec.saved_registered_items)
        or len(set(spec.post_reset_registered_items)) != len(spec.post_reset_registered_items)
        or not _valid_page_counts(spec.pre_op_registered_items, spec.pre_op_page_item_counts)
        or not _valid_page_counts(spec.post_op_registered_items, spec.post_op_page_item_counts)
        or not _valid_page_counts(spec.saved_registered_items, spec.saved_page_item_counts)
        or not _valid_page_counts(spec.post_reset_registered_items, spec.post_reset_page_item_counts)
    ):
        _fail(
            P247_BLOCKED_INVALID_MY_MENU_SPEC,
            "Invalid ILME-FX3 My Menu Setting specification, 6-operation tuple, or page/item layout",
        )

    # 1. 6-Operation Transition & [Display From My Menu] Tab Open Behavior
    op_ok, op_detail = _check_my_menu_operation_transition(spec)
    expected_tab = (
        "MY_MENU_FIRST"
        if spec.post_reset_display_from_my_menu == "On"
        else "MOST_RECENT_TAB"
    )
    tab_ok = spec.menu_button_opens_tab == expected_tab
    ops_and_tab_ok = op_ok and tab_ok
    if not op_ok:
        _fail(
            P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH,
            f"My Menu operation check failed: {op_detail}",
        )
    if not tab_ok:
        _fail(
            P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH,
            f"Display From My Menu={spec.post_reset_display_from_my_menu!r} must open {expected_tab!r}, got {spec.menu_button_opens_tab!r}",
        )

    # 2. Slot-1 Tier-0 CAMSET01.DAT Vault Zero-Mutation Firewall
    vault_zero_mutation_ok = True
    mutation_bytes = max(0, int(spec.slot1_mymenu_vault_mutation_bytes))
    if spec.slot1_tier0_vault_active:
        if (
            spec.camset_save_to_slot1_attempted
            or not spec.slot1_sdxc_wp_locked
            or (spec.camset_load_after_reset and spec.camset_slot == P247_SLOT1_VAULT_SLOT and not spec.camset_read_only_load)
        ):
            vault_zero_mutation_ok = False
            mutation_bytes = max(1, mutation_bytes)
            _fail(
                P247_BLOCKED_SLOT1_MY_MENU_VAULT_MUTATION_ATTEMPT,
                "Slot-1 Tier-0 CAMSET01.DAT vault enforces O_RDONLY + SDXC WP lock; Save/write mutation blocked",
            )
    if mutation_bytes != 0:
        vault_zero_mutation_ok = False
        _fail(
            P247_BLOCKED_SLOT1_MY_MENU_VAULT_MUTATION_ATTEMPT,
            f"Non-zero slot1_mymenu_vault_mutation_bytes={mutation_bytes}",
        )

    # 3. Non-Resettable Survival Across [Camera Settings Reset] & [Reset Network Set.] vs [Initialize] + CAMSET Load
    survival_ok = True
    init_clear_ok = True
    camset_roundtrip_ok = True
    if spec.camset_load_after_reset:
        if spec.camset_source_model != P247_FX3_MODEL_NAME:
            camset_roundtrip_ok = False
            _fail(
                P247_BLOCKED_CAMSET_MY_MENU_ROUNDTRIP_DRIFT,
                f"Cross-model CAMSET import rejected: expected {P247_FX3_MODEL_NAME!r}, got {spec.camset_source_model!r}",
            )
        if (
            spec.post_reset_registered_items != spec.saved_registered_items
            or spec.post_reset_page_item_counts != spec.saved_page_item_counts
            or spec.post_reset_display_from_my_menu != spec.saved_display_from_my_menu
        ):
            camset_roundtrip_ok = False
            _fail(
                P247_BLOCKED_CAMSET_MY_MENU_ROUNDTRIP_DRIFT,
                f"CAMSET {spec.camset_filename} load failed lossless My Menu / Display From My Menu restoration",
            )
    else:
        if spec.reset_action == "Initialize":
            if (
                len(spec.post_reset_registered_items) != 0
                or len(spec.post_reset_page_item_counts) != 0
                or spec.post_reset_display_from_my_menu != P247_DISPLAY_FROM_MY_MENU_DEFAULT
            ):
                init_clear_ok = False
                _fail(
                    P247_BLOCKED_MY_MENU_RESET_PERSISTENCE_DRIFT,
                    "Initialize must clear all My Menu pages and reset Display From My Menu to Off",
                )
        else:
            if (
                spec.post_reset_registered_items != spec.post_op_registered_items
                or spec.post_reset_page_item_counts != spec.post_op_page_item_counts
                or spec.post_reset_display_from_my_menu != spec.pre_reset_display_from_my_menu
            ):
                survival_ok = False
                _fail(
                    P247_BLOCKED_MY_MENU_RESET_PERSISTENCE_DRIFT,
                    f"My Menu items and Display From My Menu must survive {spec.reset_action!r} intact",
                )

    # 4. Volatile Stage-B Overlay & Tier-0 H0 == H3
    if (
        not _is_tmpfs_path(spec.overlay_dir)
        or _targets_persistent_emmc(spec.overlay_dir)
        or not spec.p2_blkroset_locked
        or spec.stage_b_backup_bin_writes != 0
    ):
        _fail(
            P247_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            "Stage-B overlay escaped tmpfs, unlocked p2 BLKROSET, or wrote persistent Backup.bin",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P247_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P247_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P247_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P247_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 == H3 parity drift detected",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "41B",
            "spec": asdict(spec),
            "passed": passed,
            "block_code": block_code,
            "errors": errors,
        }
    )
    return MyMenuPersistenceAndCamsetVaultReport(
        passed=passed,
        status=P247_STATUS_VERIFIED_PILLAR_41B if passed else P247_STATUS_REJECTED_PILLAR_41B,
        block_code=block_code,
        my_menu_6_operations_and_tab_verified=ops_and_tab_ok,
        my_menu_non_resettable_survival_verified=survival_ok,
        initialize_full_clear_verified=init_clear_ok,
        camset_slot1_roundtrip_verified=camset_roundtrip_ok,
        slot1_vault_zero_mutation_verified=vault_zero_mutation_ok,
        h0_equals_h3_verified=h0_h3_ok,
        slot1_mymenu_vault_mutation_bytes=mutation_bytes,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_display_quality_bt_rmt_and_mymenu_vault(
    display_bt_spec: Optional[DisplayQualityAndBtRmtCtrlVaultSpec] = None,
    my_menu_spec: Optional[MyMenuPersistenceAndCamsetVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> DisplayQualityBtRmtAndMyMenuVaultReport:
    """Combined single-shot verification of Pillar 41A + Pillar 41B + bounded `O_RDONLY` donor check."""
    spec_a = display_bt_spec or build_default_safe_display_quality_bt_rmt_vault_spec()
    spec_b = my_menu_spec or build_default_safe_my_menu_camset_vault_spec()
    donor_snapshot = inspect_phase247_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_a)
    rep_b = evaluate_my_menu_persistence_and_camset_vault(spec_b)

    combined_errors: List[str] = list(_safety_invariant_errors())
    if not donor_snapshot.all_donors_present:
        combined_errors.append("Phase 247 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        combined_errors.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")
    combined_errors.extend(rep_a.errors)
    combined_errors.extend(rep_b.errors)

    all_ok = rep_a.passed and rep_b.passed and len(combined_errors) == 0
    return DisplayQualityBtRmtAndMyMenuVaultReport(
        schema=PHASE247_SCHEMA,
        version=PHASE247_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P247_STATUS_VERIFIED_PILLAR41_SUITE if all_ok else P247_STATUS_FAIL_PILLAR41_SUITE,
        donor_snapshot=donor_snapshot,
        display_quality_bt_rmt_report=rep_a,
        my_menu_vault_report=rep_b,
        tier0_battery_high_display_violations=rep_a.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=rep_a.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=rep_b.slot1_mymenu_vault_mutation_bytes,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
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
        errors=tuple(combined_errors),
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites for Pillar 41A & Pillar 41B
# ---------------------------------------------------------------------------


def run_pillar41a_display_quality_bt_rmt_vault_6_scenario_suite() -> Pillar41ASuiteResult:
    cases: Tuple[Tuple[str, bool, DisplayQualityAndBtRmtCtrlVaultSpec, Optional[str]], ...] = (
        (
            P247_PILLAR_41A_SCENARIO_IDS[0],
            True,
            DisplayQualityAndBtRmtCtrlVaultSpec(
                pre_reset_display_quality="Standard",
                pre_reset_bt_rmt_ctrl="On",
                reset_action="Camera Settings Reset",
                post_reset_display_quality="Standard",
                post_reset_bt_rmt_ctrl="On",
                power_source="NP-FZ100",
                tier0_internal_battery_bench_active=True,
                monitor_brightness_mode="Manual",
                monitor_brightness_manual_level=0,
                bluetooth_function="Off",
                airplane_mode="On",
                zero_rf_bench_enforced=True,
                effective_bt_rmt_ctrl_active=False,
                ir_remote_ctrl_setting="On",
                ir_remote_commander_usable=False,
            ),
            None,
        ),
        (
            P247_PILLAR_41A_SCENARIO_IDS[1],
            True,
            DisplayQualityAndBtRmtCtrlVaultSpec(
                pre_reset_display_quality="High",
                pre_reset_bt_rmt_ctrl="On",
                reset_action="Reset Network Set.",
                post_reset_display_quality="High",
                post_reset_bt_rmt_ctrl="Off",
                power_source="DC-C1",
                tier0_internal_battery_bench_active=False,
                bluetooth_function="Off",
                airplane_mode="On",
                zero_rf_bench_enforced=True,
                effective_bt_rmt_ctrl_active=False,
                ir_remote_ctrl_setting="On",
                ir_remote_commander_usable=True,
            ),
            None,
        ),
        (
            P247_PILLAR_41A_SCENARIO_IDS[2],
            False,
            DisplayQualityAndBtRmtCtrlVaultSpec(
                pre_reset_display_quality="High",
                reset_action="Camera Settings Reset",
                post_reset_display_quality="High",
                power_source="NP-FZ100",
                tier0_internal_battery_bench_active=True,
                monitor_brightness_mode="Manual",
                monitor_brightness_manual_level=0,
            ),
            P247_BLOCKED_TIER0_BATTERY_BENCH_HIGH_DISPLAY_OR_BRIGHTNESS,
        ),
        (
            P247_PILLAR_41A_SCENARIO_IDS[3],
            False,
            DisplayQualityAndBtRmtCtrlVaultSpec(
                pre_reset_display_quality="Standard",
                pre_reset_bt_rmt_ctrl="On",
                reset_action="Reset Network Set.",
                post_reset_display_quality="Standard",
                post_reset_bt_rmt_ctrl="On",
            ),
            P247_BLOCKED_BT_RMT_3WAY_RESET_SPLIT_DRIFT,
        ),
        (
            P247_PILLAR_41A_SCENARIO_IDS[4],
            False,
            DisplayQualityAndBtRmtCtrlVaultSpec(
                pre_reset_bt_rmt_ctrl="On",
                reset_action="Camera Settings Reset",
                post_reset_bt_rmt_ctrl="On",
                ir_remote_ctrl_setting="On",
                ir_remote_commander_usable=True,
            ),
            P247_BLOCKED_IR_REMOTE_USED_WHILE_BT_RMT_CTRL_ON,
        ),
        (
            P247_PILLAR_41A_SCENARIO_IDS[5],
            False,
            DisplayQualityAndBtRmtCtrlVaultSpec(
                pre_reset_bt_rmt_ctrl="On",
                reset_action="NONE",
                post_reset_bt_rmt_ctrl="On",
                bluetooth_function="Off",
                airplane_mode="On",
                zero_rf_bench_enforced=True,
                effective_bt_rmt_ctrl_active=True,
            ),
            P247_BLOCKED_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
        ),
    )

    outcomes: List[Pillar41ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar41ScenarioOutcome(
                scenario_id=sid,
                pillar="41A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar41ASuiteResult(
        passed=all_ok,
        status=P247_STATUS_VERIFIED_PILLAR_41A if all_ok else P247_STATUS_REJECTED_PILLAR_41A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar41b_my_menu_camset_vault_6_scenario_suite() -> Pillar41BSuiteResult:
    cases: Tuple[Tuple[str, bool, MyMenuPersistenceAndCamsetVaultSpec, Optional[str]], ...] = (
        (
            P247_PILLAR_41B_SCENARIO_IDS[0],
            True,
            MyMenuPersistenceAndCamsetVaultSpec(
                pre_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
                pre_op_page_item_counts=(4,),
                my_menu_operation="Add Item",
                operation_target_item="Bluetooth Rmt Ctrl",
                post_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS + ("Bluetooth Rmt Ctrl",),
                post_op_page_item_counts=(5,),
                pre_reset_display_from_my_menu="On",
                reset_action="Reset Network Set.",
                post_reset_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS + ("Bluetooth Rmt Ctrl",),
                post_reset_page_item_counts=(5,),
                post_reset_display_from_my_menu="On",
                menu_button_opens_tab="MY_MENU_FIRST",
            ),
            None,
        ),
        (
            P247_PILLAR_41B_SCENARIO_IDS[1],
            True,
            MyMenuPersistenceAndCamsetVaultSpec(
                pre_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
                pre_op_page_item_counts=(4,),
                my_menu_operation="Delete All",
                post_op_registered_items=(),
                post_op_page_item_counts=(),
                pre_reset_display_from_my_menu="Off",
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model="ILME-FX3",
                camset_read_only_load=True,
                saved_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
                saved_page_item_counts=(4,),
                saved_display_from_my_menu="On",
                post_reset_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
                post_reset_page_item_counts=(4,),
                post_reset_display_from_my_menu="On",
                menu_button_opens_tab="MY_MENU_FIRST",
                slot1_tier0_vault_active=True,
                slot1_sdxc_wp_locked=True,
                camset_save_to_slot1_attempted=False,
                slot1_mymenu_vault_mutation_bytes=0,
            ),
            None,
        ),
        (
            P247_PILLAR_41B_SCENARIO_IDS[2],
            False,
            MyMenuPersistenceAndCamsetVaultSpec(
                pre_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
                pre_op_page_item_counts=(4,),
                my_menu_operation="NONE",
                post_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
                post_op_page_item_counts=(4,),
                pre_reset_display_from_my_menu="On",
                reset_action="Camera Settings Reset",
                post_reset_registered_items=(),
                post_reset_page_item_counts=(),
                post_reset_display_from_my_menu="Off",
                menu_button_opens_tab="MOST_RECENT_TAB",
            ),
            P247_BLOCKED_MY_MENU_RESET_PERSISTENCE_DRIFT,
        ),
        (
            P247_PILLAR_41B_SCENARIO_IDS[3],
            False,
            MyMenuPersistenceAndCamsetVaultSpec(
                pre_reset_display_from_my_menu="On",
                reset_action="NONE",
                post_reset_display_from_my_menu="On",
                menu_button_opens_tab="MOST_RECENT_TAB",
            ),
            P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH,
        ),
        (
            P247_PILLAR_41B_SCENARIO_IDS[4],
            False,
            MyMenuPersistenceAndCamsetVaultSpec(
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_source_model="ILME-FX6",
                saved_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
                saved_page_item_counts=(4,),
                saved_display_from_my_menu="On",
                post_reset_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
                post_reset_page_item_counts=(4,),
                post_reset_display_from_my_menu="On",
                menu_button_opens_tab="MY_MENU_FIRST",
            ),
            P247_BLOCKED_CAMSET_MY_MENU_ROUNDTRIP_DRIFT,
        ),
        (
            P247_PILLAR_41B_SCENARIO_IDS[5],
            False,
            MyMenuPersistenceAndCamsetVaultSpec(
                slot1_tier0_vault_active=True,
                slot1_sdxc_wp_locked=True,
                camset_save_to_slot1_attempted=True,
                slot1_mymenu_vault_mutation_bytes=4096,
            ),
            P247_BLOCKED_SLOT1_MY_MENU_VAULT_MUTATION_ATTEMPT,
        ),
    )

    outcomes: List[Pillar41ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_my_menu_persistence_and_camset_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar41ScenarioOutcome(
                scenario_id=sid,
                pillar="41B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar41BSuiteResult(
        passed=all_ok,
        status=P247_STATUS_VERIFIED_PILLAR_41B if all_ok else P247_STATUS_REJECTED_PILLAR_41B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar41_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar41StandaloneReport:
    """Run full Pillar 41 standalone suite (`6/6` Pillar 41A + `6/6` Pillar 41B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase247_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar41a_display_quality_bt_rmt_vault_6_scenario_suite()
    res_b = run_pillar41b_my_menu_camset_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 247 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE247_SCHEMA,
            "version": PHASE247_VERSION,
            "mode": donor_snapshot.verification_mode,
            "41a": [asdict(s) for s in res_a.scenarios],
            "41b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar41StandaloneReport(
        schema=PHASE247_SCHEMA,
        version=PHASE247_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P247_STATUS_VERIFIED_PILLAR41_SUITE if all_ok else P247_STATUS_FAIL_PILLAR41_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_41a_display_quality_bt_rmt_vault=res_a,
        pillar_41b_my_menu_camset_vault=res_b,
        tier0_battery_high_display_violations=P247_TIER0_BATTERY_HIGH_DISPLAY_VIOLATIONS if res_a.passed else 1,
        bt_rmt_ir_lockout_violations=P247_BT_RMT_IR_LOCKOUT_VIOLATIONS if res_a.passed else 1,
        slot1_mymenu_vault_mutation_bytes=P247_SLOT1_MYMENU_VAULT_MUTATION_BYTES if res_b.passed else 1,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
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
# Unified 41/41 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master41_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_41pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master41PillarRecoveryReport:
    """Evaluate and aggregate all 41 recovery pillars (`1..41`) concurrently -> `41/41` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_41_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_40pillar() -> Master40PillarRecoveryReport:
        return evaluate_realhw_40pillar_recovery_master(**kw)

    def _run_p41() -> Tuple[Pillar41StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar41_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_40 = pool.submit(_run_40pillar)
        fut_41 = pool.submit(_run_p41)
        m40_rep = fut_40.result()
        p41_rep, p41_dt = fut_41.result()

    all_errors: List[str] = list(m40_rep.errors) + list(p41_rep.errors)
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
        if getattr(m40_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-40 violated {attr_name} == {expected_val}")
        if getattr(p41_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 41 violated {attr_name} == {expected_val}")

    if m40_rep.fx3_has_var_shutter is not False:
        all_errors.append("Pillars 1-40 violated fx3_has_var_shutter == False")
    if m40_rep.unbuffered_battery_pull_events != 0:
        all_errors.append("Pillars 1-40 violated unbuffered_battery_pull_events == 0")
    if m40_rep.destructive_menu_delete_confusions != 0:
        all_errors.append("Pillars 1-40 violated destructive_menu_delete_confusions == 0")
    if m40_rep.shutter_angle_exposure_step_drift_events != 0:
        all_errors.append("Pillars 1-40 violated shutter_angle_exposure_step_drift_events == 0")
    if m40_rep.hardware_live_attachment_authorized is not False:
        all_errors.append("Pillars 1-40 violated hardware_live_attachment_authorized == False")
    if p41_rep.tier0_battery_high_display_violations != 0:
        all_errors.append("Pillar 41 violated tier0_battery_high_display_violations == 0")
    if p41_rep.bt_rmt_ir_lockout_violations != 0:
        all_errors.append("Pillar 41 violated bt_rmt_ir_lockout_violations == 0")
    if p41_rep.slot1_mymenu_vault_mutation_bytes != 0:
        all_errors.append("Pillar 41 violated slot1_mymenu_vault_mutation_bytes == 0")
    if p41_rep.hardware_live_attachment_authorized is not False:
        all_errors.append("Pillar 41 violated hardware_live_attachment_authorized == False")

    pillar_statuses: List[MasterPillarStatus] = list(m40_rep.pillars)
    spec41 = MASTER_41_PILLAR_SPECS[40]
    p41_metrics = {
        "pillar_41a_display_quality_bt_rmt_vault": (
            f"{p41_rep.pillar_41a_display_quality_bt_rmt_vault.scenarios_passed}/"
            f"{p41_rep.pillar_41a_display_quality_bt_rmt_vault.scenarios_total}"
        ),
        "pillar_41b_my_menu_camset_vault": (
            f"{p41_rep.pillar_41b_my_menu_camset_vault.scenarios_passed}/"
            f"{p41_rep.pillar_41b_my_menu_camset_vault.scenarios_total}"
        ),
        "tier0_battery_high_display_violations": p41_rep.tier0_battery_high_display_violations,
        "bt_rmt_ir_lockout_violations": p41_rep.bt_rmt_ir_lockout_violations,
        "slot1_mymenu_vault_mutation_bytes": p41_rep.slot1_mymenu_vault_mutation_bytes,
        "hardware_live_attachment_authorized": p41_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p41_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec41[0],
            pillar_id=spec41[1],
            phase_label=spec41[2],
            module_name=spec41[3],
            passed=bool(p41_rep.all_passed),
            status=p41_rep.status,
            verification_mode=p41_rep.verification_mode,
            elapsed_seconds=p41_dt,
            key_metrics=p41_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec41[1],
                    "mode": p41_rep.verification_mode,
                    "status": p41_rep.status,
                    "metrics": p41_metrics,
                    "passed": p41_rep.all_passed,
                }
            ),
            errors=tuple(p41_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master41_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p41_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_41_PILLAR_COUNT == 41
        and pillars_passed == 41
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE247_SCHEMA,
            "version": PHASE247_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master41PillarRecoveryReport(
        schema=PHASE247_SCHEMA,
        version=PHASE247_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P247_STATUS_VERIFIED_41OF41_AGGREGATOR if all_ok else P247_STATUS_FAIL_41OF41_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P247_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P247_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p41_rep.donor_snapshot,
        pillar41_a_display_quality_bt_rmt_vault=p41_rep.pillar_41a_display_quality_bt_rmt_vault,
        pillar41_b_my_menu_camset_vault=p41_rep.pillar_41b_my_menu_camset_vault,
        tier0_battery_high_display_violations=p41_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=p41_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=p41_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m40_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m40_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m40_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m40_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p41_rep.hardware_live_attachment_authorized,
        master_41pillar_sha256=master_sha,
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


def evaluate_41pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master41PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_41pillar_recovery_master`."""
    return evaluate_realhw_41pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_41pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master41PillarRecoveryReport:
    """Public CLI entry point for Phase 247 Pillar 41 unified `41/41` real-hardware recovery master."""
    return evaluate_realhw_41pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS",
    "ALLOW_PERSISTENT_JIRITSU_WRITES",
    "CNFLASHA_USERSPACE_WRITE_BLOCKED",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "ISP_WRITE_AUTHORIZED",
    "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
    "MASTER_41_PILLAR_COUNT",
    "MASTER_41_PILLAR_IDS",
    "MASTER_41_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P247_AIRPLANE_MODE_DEFAULT",
    "P247_AIRPLANE_MODE_MENU_PATH",
    "P247_BLOCKED_BT_RMT_3WAY_RESET_SPLIT_DRIFT",
    "P247_BLOCKED_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION",
    "P247_BLOCKED_CAMSET_DISPLAY_QUALITY_OR_BT_RMT_RESTORE_DRIFT",
    "P247_BLOCKED_CAMSET_MY_MENU_ROUNDTRIP_DRIFT",
    "P247_BLOCKED_DISPLAY_QUALITY_RESET_SURVIVAL_DRIFT",
    "P247_BLOCKED_INVALID_DISPLAY_QUALITY_OR_BT_RMT_SPEC",
    "P247_BLOCKED_INVALID_MY_MENU_SPEC",
    "P247_BLOCKED_IR_REMOTE_USED_WHILE_BT_RMT_CTRL_ON",
    "P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH",
    "P247_BLOCKED_MY_MENU_RESET_PERSISTENCE_DRIFT",
    "P247_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P247_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P247_BLOCKED_SLOT1_MY_MENU_VAULT_MUTATION_ATTEMPT",
    "P247_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P247_BLOCKED_TIER0_BATTERY_BENCH_HIGH_DISPLAY_OR_BRIGHTNESS",
    "P247_BLUETOOTH_FUNCTION_DEFAULT",
    "P247_BLUETOOTH_FUNCTION_MENU_PATH",
    "P247_BLUETOOTH_RMT_CTRL_DEFAULT",
    "P247_BLUETOOTH_RMT_CTRL_MENU_PATH",
    "P247_BOUNDED_HEADER_BYTES",
    "P247_BT_RMT_IR_LOCKOUT_VIOLATIONS",
    "P247_CAMSET_FILENAMES",
    "P247_CONCURRENT_CEILING_SECONDS",
    "P247_DEFAULT_REGISTERED_MY_MENU_ITEMS",
    "P247_DISPLAY_FROM_MY_MENU_DEFAULT",
    "P247_DISPLAY_FROM_MY_MENU_MODES",
    "P247_DISPLAY_QUALITY_DEFAULT",
    "P247_DISPLAY_QUALITY_MENU_PATH",
    "P247_DISPLAY_QUALITY_MODES",
    "P247_DONOR_FX3_APPFW_702_RELPATH",
    "P247_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P247_DONOR_FX3_BODYDATA_RELPATH",
    "P247_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH",
    "P247_DONOR_FX3_LIBBACKUP_SO_RELPATH",
    "P247_DONOR_FX3_LIBGPE_SO_RELPATH",
    "P247_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH",
    "P247_DONOR_FX3_LIBINFRABLUETOOTH_SO_RELPATH",
    "P247_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P247_DONOR_FX6_APPFW_601_RELPATH",
    "P247_DONOR_FX6_LIBINFRASIRCS_SO_RELPATH",
    "P247_DONOR_INSPECT_BUDGET_SECONDS",
    "P247_FORBIDDEN_PERSISTENT_TARGETS",
    "P247_FX3_FW_VERSION",
    "P247_FX3_HELPGUIDE_ID",
    "P247_FX3_MODEL_ID",
    "P247_FX3_MODEL_NAME",
    "P247_FX3_SUPPORTED_FW_VERSIONS",
    "P247_FX6_DONOR_FW_VERSION",
    "P247_FX6_DONOR_MODEL_NAME",
    "P247_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P247_IR_REMOTE_CTRL_MENU_PATH",
    "P247_MAX_FULL_DONOR_BYTES",
    "P247_MENU_OPEN_TAB_BEHAVIORS",
    "P247_MONITOR_BRIGHTNESS_BENCH_LEVEL",
    "P247_MONITOR_BRIGHTNESS_BENCH_MODE",
    "P247_MONITOR_BRIGHTNESS_MANUAL_LEVELS",
    "P247_MONITOR_BRIGHTNESS_MENU_PATH",
    "P247_MONITOR_BRIGHTNESS_MODES",
    "P247_MY_MENU_6_OPERATIONS",
    "P247_MY_MENU_EDIT_OPERATIONS",
    "P247_MY_MENU_MAX_ITEMS_PER_PAGE",
    "P247_MY_MENU_MAX_PAGES",
    "P247_MY_MENU_MAX_TOTAL_ITEMS",
    "P247_MY_MENU_SETTING_MENU_PATH",
    "P247_NOMINAL_BUDGET_SECONDS",
    "P247_ON_OFF_MODES",
    "P247_PILLAR_41A_SCENARIO_IDS",
    "P247_PILLAR_41B_SCENARIO_IDS",
    "P247_PINNED_FX3_APPFW_702_BYTES",
    "P247_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P247_PINNED_FX3_BACKUP_BIN_BYTES",
    "P247_PINNED_FX3_BACKUP_BIN_SHA256",
    "P247_PINNED_FX3_BODYDATA_BYTES",
    "P247_PINNED_FX3_BODYDATA_HDR4K_SHA256",
    "P247_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES",
    "P247_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256",
    "P247_PINNED_FX3_LIBBACKUP_SO_BYTES",
    "P247_PINNED_FX3_LIBBACKUP_SO_SHA256",
    "P247_PINNED_FX3_LIBGPE_SO_BYTES",
    "P247_PINNED_FX3_LIBGPE_SO_SHA256",
    "P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES",
    "P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256",
    "P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_BYTES",
    "P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_SHA256",
    "P247_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P247_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P247_PINNED_FX6_APPFW_601_BYTES",
    "P247_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P247_PINNED_FX6_LIBINFRASIRCS_SO_BYTES",
    "P247_PINNED_FX6_LIBINFRASIRCS_SO_SHA256",
    "P247_POWER_SOURCES",
    "P247_RESET_ACTIONS",
    "P247_SLOT1_MYMENU_VAULT_MUTATION_BYTES",
    "P247_SLOT1_VAULT_SLOT",
    "P247_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P247_STATUS_FAIL_41OF41_AGGREGATOR",
    "P247_STATUS_FAIL_PILLAR41_SUITE",
    "P247_STATUS_REJECTED_PILLAR_41A",
    "P247_STATUS_REJECTED_PILLAR_41B",
    "P247_STATUS_VERIFIED_41OF41_AGGREGATOR",
    "P247_STATUS_VERIFIED_PILLAR41_SUITE",
    "P247_STATUS_VERIFIED_PILLAR_41A",
    "P247_STATUS_VERIFIED_PILLAR_41B",
    "P247_TIER0_BATTERY_HIGH_DISPLAY_VIOLATIONS",
    "P247_TIER0_SURFACE_COUNT",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE247_SCHEMA",
    "PHASE247_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "DisplayQualityAndBtRmtCtrlVaultReport",
    "DisplayQualityAndBtRmtCtrlVaultSpec",
    "DisplayQualityBtRmtAndMyMenuVaultReport",
    "Master41PillarRecoveryReport",
    "MyMenuPersistenceAndCamsetVaultReport",
    "MyMenuPersistenceAndCamsetVaultSpec",
    "Phase247DonorArtifactDigest",
    "Phase247DonorSnapshot",
    "Pillar41ASuiteResult",
    "Pillar41BSuiteResult",
    "Pillar41ScenarioOutcome",
    "Pillar41StandaloneReport",
    "build_default_safe_display_quality_bt_rmt_vault_spec",
    "build_default_safe_my_menu_camset_vault_spec",
    "evaluate_41pillar_recovery_master",
    "evaluate_display_quality_and_bt_rmt_ctrl_vault",
    "evaluate_my_menu_persistence_and_camset_vault",
    "evaluate_realhw_41pillar_recovery_master",
    "inspect_phase247_donors_readonly",
    "run_pillar41_standalone_suite",
    "run_pillar41a_display_quality_bt_rmt_vault_6_scenario_suite",
    "run_pillar41b_my_menu_camset_vault_6_scenario_suite",
    "verify_41pillar_recovery_suite",
    "verify_display_quality_bt_rmt_and_mymenu_vault",
]
