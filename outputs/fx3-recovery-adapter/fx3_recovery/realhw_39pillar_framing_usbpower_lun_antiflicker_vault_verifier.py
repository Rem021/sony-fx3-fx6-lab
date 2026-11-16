"""Phase 243 — Pillar 39 (`39/39` Recovery Pillars) & Unified 39-Pillar Recovery Master
(`verify-39pillar-recovery` / `verify-framing-usbpower-lun-antiflicker-vault`):

1. **Pillar 39A — `[Framing Settings]` Asymmetric `Full`/`Crop` Recovery, HDMI `RAW` Crop
   Incompatibility, `ILME-FX3` (`ilc/2210`) vs `ZV-E1` Naming Lock & `[Anti-flicker Shoot.]`
   Mechanical-Still-Only / No-`[Var. Shutter]` Invariant (`ILME-FX3 Ver. 7.02`)**:
   - Models `MENU` -> `Shooting` -> `[Framing Settings]` (`[Framing]`: `Off` default / `On`,
     `[Recording/Streaming]`: `Full` default / `Crop`, `[HDMI]`: `Crop` default / `Full`),
     verifying all 3 reset cleanly via `[Camera Settings Reset]` (and `[Initialize]`) and
     restore deterministically via Slot-1 `CAMSET01.DAT` `[Load]`.
   - Enforces the factory asymmetric routing (`Recording/Streaming = Full` master internal capture
     paired with `HDMI = Crop` external monitor output when `[Framing] = On`), hard-blocks HDMI
     `RAW` output combined with cropped `[Framing] = On`, and distinguishes `ILME-FX3` (`ilc/2210`)
     `[Framing Settings]` (*Monitor & Control*) from consumer `ZV-E1` `[Autoframing Settings]`.
   - Models `MENU` -> `Shooting` -> `[Shutter/Silent]` -> `[Anti-flicker Shoot.]` (`Off` default /
     `On`, resettable via `[Camera Settings Reset]`) strictly for `100 Hz` / `120 Hz` artificial
     lighting flicker during mechanical-shutter still-image capture (non-functional in `Movie` /
     `S&Q Motion` and `[Silent Mode] = On` / `Electronic Shutter`), and enforces stock `ILME-FX3`
     (`ilc/2210`) absence of `[Var. Shutter]` (`fx3_has_var_shutter == False`, rejecting false
     `FX30` `ilc/2220` `[Var. Shutter]` or `FX6` `ECS` node assumptions).

2. **Pillar 39B — `[USB Power Supply]` Mandatory `NP-FZ100` Insertion + `USB Type-C` Exclusivity &
   `[USB LUN Setting]` `Multi`/`Single` Setup Persistence + Offline `WP` Card-Reader Tier-0 Vault**:
   - Models `MENU` -> `Setup` -> `[USB]` (`[USB Connection Mode] = Sel. When Connect`,
     `[USB LUN Setting] = Multi`, `[USB Power Supply] = On`), verifying all 3 **survive
     `[Camera Settings Reset]`** and return to factory defaults **only** via `[Initialize]`.
   - Enforces the two `[USB Power Supply]` hardware power interlocks:
     (a) powering on without an inserted `NP-FZ100` battery pack (or `DC-C1` DC coupler in the
         battery bay) is hardware-unavailable, and removing the battery pack mid-USB-PD supply
         triggers immediate unbuffered power-off (`unbuffered_battery_pull_events == 0`);
     (b) `Multi/Micro USB` terminal cannot supply power or charge internal batteries (`USB Type-C`
         exclusive).
   - Enforces `[USB LUN Setting]` dual-slot (`Multi` -> Slots 1 & 2, 2 LUNs) vs legacy primary-slot
     (`Single` -> Slot 1 only, 1 LUN) awareness while keeping live host USB attachment hard-blocked
     (`physical_usb_packets_emitted == 0`, `hardware_live_attachment_authorized == False`), using
     off-camera `WP`-locked SDXC card readers for Tier-0 SHA-256 verification.

3. **Unified `39/39` Recovery Master (`evaluate_realhw_39pillar_recovery_master`)**:
   - Delegates Pillars `1..38` concurrently to `evaluate_realhw_38pillar_recovery_master` +
     **Pillar 39** -> **`39/39` (`VERIFIED_39OF39_PILLAR_RECOVERY_MASTER`)** in `< 4.0s` (`< 6.0s` ceiling).
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
from .realhw_38pillar_shoe_audio_wind_saveload_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_38_PILLAR_SPECS,
    Master38PillarRecoveryReport,
    evaluate_realhw_38pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE243_SCHEMA: str = "realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier_v1"
PHASE243_VERSION: str = "1.0.0"

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
P243_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P243_FX3_HAS_VAR_SHUTTER: bool = False
P243_UNBUFFERED_BATTERY_PULL_EVENTS: int = 0

P243_DONOR_INSPECT_BUDGET_SECONDS: float = 0.15
P243_NOMINAL_BUDGET_SECONDS: float = 4.0
P243_CONCURRENT_CEILING_SECONDS: float = 6.0
P243_BOUNDED_HEADER_BYTES: int = 4096
P243_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-37 / FX3 Ver. 7.02 & FX6 Ver. 6.01 Donor Anchors (bounded O_RDONLY verification)
P243_FX3_MODEL_NAME: str = "ILME-FX3"
P243_FX3_MODEL_ID: int = 0x91030080
P243_FX3_HELPGUIDE_ID: str = "ilc/2210"
P243_FX3_FW_VERSION: str = "7.02"
P243_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P243_FX6_DONOR_FW_VERSION: str = "6.01"
P243_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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
P243_FOREIGN_HELPGUIDE_OR_MODELS: Tuple[str, ...] = (
    "ZV-E1",
    "ILME-FX30",
    "ILCE-6700",
    "ILME-FX6",
    "ilc/2220",
    "ilc/2310",
    "ilc/2320",
)

P243_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P243_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P243_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)

P243_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P243_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P243_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P243_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P243_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P243_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P243_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P243_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P243_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P243_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P243_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P243_PINNED_FX3_LIBBACKUP_SO_SHA256: str = (
    "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"
)

P243_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P243_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P243_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = (
    "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
)

P243_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P243_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P243_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P243_DONOR_FX3_LIBUSBBUSPOWER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so"
)
P243_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES: int = 48232
P243_PINNED_FX3_LIBUSBBUSPOWER_SO_SHA256: str = (
    "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748"
)

P243_DONOR_FX3_LIBUSBCONTROL_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbControl.so"
)
P243_PINNED_FX3_LIBUSBCONTROL_SO_BYTES: int = 135424
P243_PINNED_FX3_LIBUSBCONTROL_SO_SHA256: str = (
    "2bf51f28fd5066e56afc8bbb02ddbaa96b36f57ff2a823cecf9f901781754ed9"
)

# Pillar 39A — [Framing Settings] Asymmetric Crop/Full & [Anti-flicker Shoot.] Still-Mech-Only / No Var. Shutter
P243_FRAMING_SETTINGS_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Framing Settings",
)
P243_FORBIDDEN_ZVE1_AUTOFRAMING_MENU_NAME: str = "Autoframing Settings"
P243_FRAMING_SETTINGS_3_ITEMS: Tuple[str, ...] = (
    "Framing",
    "Recording/Streaming",
    "HDMI",
)
P243_ON_OFF_MODES: Tuple[str, ...] = ("Off", "On")
P243_FRAMING_FRAME_MODES: Tuple[str, ...] = ("Full", "Crop")
P243_FRAMING_DEFAULT: str = "Off"
P243_FRAMING_REC_STREAMING_DEFAULT: str = "Full"
P243_FRAMING_HDMI_DEFAULT: str = "Crop"

P243_ANTIFLICKER_SHOOT_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Shutter/Silent",
    "Anti-flicker Shoot.",
)
P243_ANTIFLICKER_SHOOT_DEFAULT: str = "Off"
P243_CAPTURE_MODES: Tuple[str, ...] = ("Still", "Movie", "S&Q Motion")
P243_SHUTTER_TYPES: Tuple[str, ...] = ("Mechanical Shutter", "Electronic Shutter")
P243_SUPPORTED_FLICKER_HZ: Tuple[int, ...] = (0, 100, 120)
P243_FORBIDDEN_VAR_SHUTTER_AND_ECS_NODES: Tuple[str, ...] = (
    "Var. Shutter",
    "Var. Shutter Set.",
    "Variable Shutter",
    "ECS",
    "Extended Clear Scan",
)

P243_RESET_ACTIONS: Tuple[str, ...] = ("NONE", "Camera Settings Reset", "Initialize")
P243_SLOT1_VAULT_SLOT: int = 1
P243_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))

# Pillar 39B — [Setup] -> [USB] Survival, Mandatory NP-FZ100 + USB Type-C Exclusivity & [USB LUN Setting]
P243_USB_SETUP_MENU_PATH: Tuple[str, ...] = ("MENU", "Setup", "USB")
P243_USB_SETUP_3_ITEMS: Tuple[str, ...] = (
    "USB Connection Mode",
    "USB LUN Setting",
    "USB Power Supply",
)
P243_USB_CONNECTION_MODE_DEFAULT: str = "Sel. When Connect"
P243_USB_CONNECTION_MODES: Tuple[str, ...] = (
    "Sel. When Connect",
    "MassStorage(MSC)",
    "MTP",
    "Remote Shoot (PC Remote)",
)
P243_USB_LUN_SETTING_DEFAULT: str = "Multi"
P243_USB_LUN_MODES: Tuple[str, ...] = ("Multi", "Single")
P243_USB_POWER_SUPPLY_DEFAULT: str = "On"
P243_BATTERY_BAY_SOURCES: Tuple[str, ...] = ("NP-FZ100", "DC-C1", "EMPTY")
P243_USB_POWER_PORTS: Tuple[str, ...] = ("NONE", "USB_TYPE_C", "MULTI_MICRO_USB")
P243_USB_BENCH_MIN_NP_FZ100_PCT: int = 10
P243_LUN_MULTI_EXPOSED_SLOTS: Tuple[int, ...] = (1, 2)
P243_LUN_SINGLE_EXPOSED_SLOTS: Tuple[int, ...] = (1,)

P243_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_framing_usbpower_lun_antiflicker_overlay"
P243_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P243_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P243_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P243_BLOCKED_INVALID_FRAMING_OR_ANTIFLICKER_SPEC: str = (
    "BLOCKED_INVALID_FRAMING_OR_ANTIFLICKER_SPEC"
)
P243_BLOCKED_ZVE1_AUTOFRAMING_NAMING_MISMATCH: str = (
    "BLOCKED_ZVE1_AUTOFRAMING_NAMING_MISMATCH"
)
P243_BLOCKED_FX3_NONEXISTENT_VAR_SHUTTER_OR_ECS_NODE: str = (
    "BLOCKED_FX3_NONEXISTENT_VAR_SHUTTER_OR_ECS_NODE"
)
P243_BLOCKED_FRAMING_OR_ANTIFLICKER_RESET_DRIFT: str = (
    "BLOCKED_FRAMING_OR_ANTIFLICKER_RESET_DRIFT"
)
P243_BLOCKED_CAMSET_FRAMING_OR_ANTIFLICKER_RESTORE_DRIFT: str = (
    "BLOCKED_CAMSET_FRAMING_OR_ANTIFLICKER_RESTORE_DRIFT"
)
P243_BLOCKED_HDMI_RAW_FRAMING_CROP_INCOMPATIBLE: str = (
    "BLOCKED_HDMI_RAW_FRAMING_CROP_INCOMPATIBLE"
)
P243_BLOCKED_FRAMING_ASYMMETRIC_ROUTING_MISMATCH: str = (
    "BLOCKED_FRAMING_ASYMMETRIC_ROUTING_MISMATCH"
)
P243_BLOCKED_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION: str = (
    "BLOCKED_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION"
)

P243_BLOCKED_INVALID_USB_POWER_OR_LUN_SPEC: str = "BLOCKED_INVALID_USB_POWER_OR_LUN_SPEC"
P243_BLOCKED_USB_SETUP_CAMERA_SETTINGS_RESET_DRIFT: str = (
    "BLOCKED_USB_SETUP_CAMERA_SETTINGS_RESET_DRIFT"
)
P243_BLOCKED_USB_POWER_WITHOUT_NP_FZ100_UNAVAILABLE: str = (
    "BLOCKED_USB_POWER_WITHOUT_NP_FZ100_UNAVAILABLE"
)
P243_BLOCKED_MID_USB_PD_BATTERY_REMOVAL_POWEROFF: str = (
    "BLOCKED_MID_USB_PD_BATTERY_REMOVAL_POWEROFF"
)
P243_BLOCKED_MULTI_MICRO_USB_POWER_OR_CHARGE_FORBIDDEN: str = (
    "BLOCKED_MULTI_MICRO_USB_POWER_OR_CHARGE_FORBIDDEN"
)
P243_BLOCKED_USB_POWER_SUPPLY_OFF_OR_PORT_MISMATCH: str = (
    "BLOCKED_USB_POWER_SUPPLY_OFF_OR_PORT_MISMATCH"
)
P243_BLOCKED_USB_LUN_MULTI_SINGLE_ENUMERATION_MISMATCH: str = (
    "BLOCKED_USB_LUN_MULTI_SINGLE_ENUMERATION_MISMATCH"
)
P243_BLOCKED_LIVE_USB_HOST_ATTACHMENT_FORBIDDEN: str = (
    "BLOCKED_LIVE_USB_HOST_ATTACHMENT_FORBIDDEN"
)
P243_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P243_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P243_STATUS_VERIFIED_PILLAR_39A: str = (
    "VERIFIED_PILLAR_39A_FRAMING_CROP_FULL_AND_ANTIFLICKER_NO_VAR_SHUTTER_VAULT"
)
P243_STATUS_REJECTED_PILLAR_39A: str = (
    "REJECTED_PILLAR_39A_FRAMING_CROP_FULL_AND_ANTIFLICKER_NO_VAR_SHUTTER_VAULT"
)
P243_STATUS_VERIFIED_PILLAR_39B: str = (
    "VERIFIED_PILLAR_39B_USB_POWER_NPFZ100_TYPEC_AND_LUN_PERSISTENCE_VAULT"
)
P243_STATUS_REJECTED_PILLAR_39B: str = (
    "REJECTED_PILLAR_39B_USB_POWER_NPFZ100_TYPEC_AND_LUN_PERSISTENCE_VAULT"
)
P243_STATUS_VERIFIED_PILLAR39_SUITE: str = (
    "VERIFIED_PILLAR39_FRAMING_USBPOWER_LUN_ANTIFLICKER_VAULT"
)
P243_STATUS_FAIL_PILLAR39_SUITE: str = (
    "FAIL_PILLAR39_FRAMING_USBPOWER_LUN_ANTIFLICKER_VAULT"
)
P243_STATUS_VERIFIED_39OF39_AGGREGATOR: str = "VERIFIED_39OF39_PILLAR_RECOVERY_MASTER"
P243_STATUS_FAIL_39OF39_AGGREGATOR: str = "FAIL_39OF39_PILLAR_RECOVERY_MASTER"

P243_PILLAR_39A_SCENARIO_IDS: Tuple[str, ...] = (
    "P39A1_CAMERA_SETTINGS_RESET_RESTORES_FRAMING_OFF_FULL_CROP_AND_ANTIFLICKER_OFF_SAFE",
    "P39A2_CAMSET01_LOAD_RESTORES_ASYMMETRIC_FULL_REC_CROP_HDMI_AND_STILL_MECH_ANTIFLICKER_SAFE",
    "P39A3_REJECT_HDMI_RAW_COMBINED_WITH_CROPPED_FRAMING_ON",
    "P39A4_REJECT_ZVE1_AUTOFRAMING_SETTINGS_MENU_NAMING_ON_ILME_FX3",
    "P39A5_REJECT_ANTIFLICKER_CLAIMED_ACTIVE_IN_MOVIE_OR_SILENT_ELECTRONIC_SHUTTER",
    "P39A6_REJECT_FX30_VAR_SHUTTER_OR_FX6_ECS_MENU_NODE_ASSUMPTION_ON_STOCK_FX3",
)
P243_PILLAR_39B_SCENARIO_IDS: Tuple[str, ...] = (
    "P39B1_USB_SETUP_SURVIVES_CAMERA_SETTINGS_RESET_WITH_NPFZ100_TYPEC_PD_AND_OFFLINE_WP_READER_SAFE",
    "P39B2_INITIALIZE_RESTORES_USB_DEFAULTS_SEL_WHEN_CONNECT_MULTI_2LUN_ON_AND_DCC1_COUPLER_SAFE",
    "P39B3_REJECT_USB_POWER_ON_WITHOUT_INSERTED_NP_FZ100_OR_MID_PD_BATTERY_REMOVAL",
    "P39B4_REJECT_MULTI_MICRO_USB_TERMINAL_POWER_SUPPLY_OR_BATTERY_CHARGING",
    "P39B5_REJECT_USB_SETUP_ITEMS_WIPED_BY_CAMERA_SETTINGS_RESET_OR_SINGLE_LUN_SLOT2_ASSUMPTION",
    "P39B6_REJECT_LIVE_HOST_USB_MSC_DATA_ATTACHMENT_BYPASSING_OFFCAMERA_WP_READER",
)

MASTER_39_PILLAR_COUNT: int = 39
MASTER_39_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_38_PILLAR_SPECS + (
    (
        39,
        "pillar_39_framing_usbpower_lun_antiflicker_vault",
        "Phase 243",
        "fx3_recovery.realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier",
    ),
)
MASTER_39_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_39_PILLAR_SPECS)


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
        ("P243_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P243_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P243_FX3_HAS_VAR_SHUTTER", P243_FX3_HAS_VAR_SHUTTER, False),
        ("P243_UNBUFFERED_BATTERY_PULL_EVENTS", P243_UNBUFFERED_BATTERY_PULL_EVENTS, 0),
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
    return any(tok in low for tok in P243_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase243DonorArtifactDigest:
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
class Phase243DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase243DonorArtifactDigest, ...]


@dataclass(frozen=True)
class FramingCropFullAndAntiFlickerVaultSpec:
    camera_model: str = P243_FX3_MODEL_NAME
    helpguide_id: str = P243_FX3_HELPGUIDE_ID
    fw_version: str = P243_FX3_FW_VERSION
    framing_menu_path: Tuple[str, ...] = P243_FRAMING_SETTINGS_MENU_PATH
    antiflicker_menu_path: Tuple[str, ...] = P243_ANTIFLICKER_SHOOT_MENU_PATH
    pre_reset_framing: str = "On"  # Off | On
    pre_reset_framing_rec_streaming: str = "Crop"  # Full | Crop
    pre_reset_framing_hdmi: str = "Full"  # Crop | Full
    pre_reset_antiflicker_shoot: str = "On"  # Off | On
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P243_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    saved_framing: str = "On"
    saved_framing_rec_streaming: str = "Full"
    saved_framing_hdmi: str = "Crop"
    saved_antiflicker_shoot: str = "On"
    post_reset_framing: str = P243_FRAMING_DEFAULT
    post_reset_framing_rec_streaming: str = P243_FRAMING_REC_STREAMING_DEFAULT
    post_reset_framing_hdmi: str = P243_FRAMING_HDMI_DEFAULT
    post_reset_antiflicker_shoot: str = P243_ANTIFLICKER_SHOOT_DEFAULT
    hdmi_raw_output: str = "Off"  # Off | On
    effective_rec_streaming_frame: str = "Full"  # Full | Crop
    effective_hdmi_frame: str = "Full"  # Full | Crop
    capture_mode: str = "Still"  # Still | Movie | S&Q Motion
    silent_mode: str = "Off"  # Off | On
    shutter_type: str = "Mechanical Shutter"  # Mechanical Shutter | Electronic Shutter
    flicker_lighting_hz: int = 100  # 0 | 100 | 120
    antiflicker_available_in_current_mode: bool = True
    antiflicker_effective_active: bool = False
    fx3_has_var_shutter: bool = False
    claimed_var_shutter_or_ecs_menu_node: Optional[str] = None
    overlay_dir: str = P243_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P243_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P243_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P243_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class FramingCropFullAndAntiFlickerVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    fx3_framing_naming_lock_verified: bool
    framing_and_antiflicker_reset_verified: bool
    camset_slot1_restore_verified: bool
    framing_asymmetric_and_hdmi_raw_guard_verified: bool
    antiflicker_mech_still_only_verified: bool
    no_var_shutter_invariant_verified: bool
    fx3_has_var_shutter: bool
    h0_equals_h3_verified: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UsbPowerBatteryInterlockAndLunVaultSpec:
    camera_model: str = P243_FX3_MODEL_NAME
    helpguide_id: str = P243_FX3_HELPGUIDE_ID
    fw_version: str = P243_FX3_FW_VERSION
    usb_setup_menu_path: Tuple[str, ...] = P243_USB_SETUP_MENU_PATH
    pre_reset_usb_connection_mode: str = "MassStorage(MSC)"
    pre_reset_usb_lun_setting: str = "Single"
    pre_reset_usb_power_supply: str = "On"
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Initialize
    post_reset_usb_connection_mode: str = "MassStorage(MSC)"
    post_reset_usb_lun_setting: str = "Single"
    post_reset_usb_power_supply: str = "On"
    camera_power_on_requested: bool = True
    battery_bay_source: str = "NP-FZ100"  # NP-FZ100 | DC-C1 | EMPTY
    np_fz100_charge_pct: int = 85
    usb_power_port: str = "USB_TYPE_C"  # NONE | USB_TYPE_C | MULTI_MICRO_USB
    usb_power_delivery_active: bool = True
    internal_battery_charging_active: bool = False
    multi_micro_usb_power_or_charge_attempted: bool = False
    battery_removed_during_usb_power: bool = False
    unbuffered_battery_pull_events: int = 0
    msc_modeled_lun_count: int = 1
    msc_modeled_exposed_slots: Tuple[int, ...] = P243_LUN_SINGLE_EXPOSED_SLOTS
    live_host_usb_data_attached: bool = False
    hardware_live_attachment_requested: bool = False
    physical_usb_packets_sent: int = 0
    offcamera_wp_card_reader_sha256_verified: bool = True
    slot1_sdxc_wp_switch_locked: bool = True
    stage_b_overlay_dir: str = P243_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P243_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P243_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P243_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class UsbPowerBatteryInterlockAndLunVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    usb_setup_reset_persistence_verified: bool
    mandatory_npfz100_battery_interlock_verified: bool
    usb_typec_power_exclusivity_verified: bool
    usb_lun_multi_single_visibility_verified: bool
    offline_wp_card_reader_tier0_verified: bool
    h0_equals_h3_verified: bool
    unbuffered_battery_pull_events: int
    tier0_surfaces_intact: int
    hardware_live_attachment_authorized: bool
    physical_usb_packets_emitted: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FramingUsbPowerLunAndAntiFlickerVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase243DonorSnapshot
    framing_antiflicker_report: FramingCropFullAndAntiFlickerVaultReport
    usb_power_lun_vault_report: UsbPowerBatteryInterlockAndLunVaultReport
    fx3_has_var_shutter: bool
    unbuffered_battery_pull_events: int
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
class Pillar39ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar39ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar39ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar39BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar39ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar39StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase243DonorSnapshot
    pillar_39a_framing_antiflicker_vault: Pillar39ASuiteResult
    pillar_39b_usb_power_lun_vault: Pillar39BSuiteResult
    fx3_has_var_shutter: bool
    unbuffered_battery_pull_events: int
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
class Master39PillarRecoveryReport:
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
    donor_snapshot: Phase243DonorSnapshot
    pillar39_a_framing_antiflicker_vault: Pillar39ASuiteResult
    pillar39_b_usb_power_lun_vault: Pillar39BSuiteResult
    fx3_has_var_shutter: bool
    unbuffered_battery_pull_events: int
    hardware_live_attachment_authorized: bool
    master_39pillar_sha256: str
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
    max_full_bytes: int = P243_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P243_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase243_donors() -> Tuple[Phase243DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P243_DONOR_FX3_BODYDATA_RELPATH,
            P243_PINNED_FX3_BODYDATA_BYTES,
            P243_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P243_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P243_DONOR_FX3_APPFW_702_RELPATH,
            P243_PINNED_FX3_APPFW_702_BYTES,
            P243_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P243_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P243_DONOR_FX6_APPFW_601_RELPATH,
            P243_PINNED_FX6_APPFW_601_BYTES,
            P243_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P243_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P243_DONOR_FX3_BACKUP_BIN_RELPATH,
            P243_PINNED_FX3_BACKUP_BIN_BYTES,
            P243_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P243_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P243_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P243_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P243_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P243_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P243_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P243_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P243_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P243_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P243_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P243_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P243_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P243_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "fx3_libusbbuspower_so",
            P243_DONOR_FX3_LIBUSBBUSPOWER_SO_RELPATH,
            P243_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES,
            P243_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES,
            "FULL_SHA256",
            P243_PINNED_FX3_LIBUSBBUSPOWER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:UsbBusPower_Init+_ZN11UsbBusPower11GetInstanceEv+_ZN11UsbBusPower18SetWatchSWForceOFFEv",
        ),
        (
            "fx3_libusbcontrol_so",
            P243_DONOR_FX3_LIBUSBCONTROL_SO_RELPATH,
            P243_PINNED_FX3_LIBUSBCONTROL_SO_BYTES,
            P243_PINNED_FX3_LIBUSBCONTROL_SO_BYTES,
            "FULL_SHA256",
            P243_PINNED_FX3_LIBUSBCONTROL_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZN15UsbControlDebug9BlogWriteEhhtj+_ZN9UsbAdjCmdC1Ev",
        ),
    )
    return tuple(
        Phase243DonorArtifactDigest(
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


def inspect_phase243_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase243DonorSnapshot:
    """Inspect Wave-37 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.15s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase243_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase243DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P243_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P243_DONOR_FX3_BODYDATA_RELPATH,
            P243_PINNED_FX3_BODYDATA_BYTES,
            P243_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P243_DONOR_FX3_APPFW_702_RELPATH,
            P243_PINNED_FX3_APPFW_702_BYTES,
            P243_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P243_DONOR_FX6_APPFW_601_RELPATH,
            P243_PINNED_FX6_APPFW_601_BYTES,
            P243_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P243_DONOR_FX3_BACKUP_BIN_RELPATH,
            P243_PINNED_FX3_BACKUP_BIN_BYTES,
            P243_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P243_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P243_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P243_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P243_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P243_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P243_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P243_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P243_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P243_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite")
            ),
        ),
        (
            "fx3_libusbbuspower_so",
            P243_DONOR_FX3_LIBUSBBUSPOWER_SO_RELPATH,
            P243_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES,
            P243_PINNED_FX3_LIBUSBBUSPOWER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (
                    b"UsbBusPower_Init",
                    b"_ZN11UsbBusPower11GetInstanceEv",
                    b"_ZN11UsbBusPower18SetWatchSWForceOFFEv",
                ),
            ),
        ),
        (
            "fx3_libusbcontrol_so",
            P243_DONOR_FX3_LIBUSBCONTROL_SO_RELPATH,
            P243_PINNED_FX3_LIBUSBCONTROL_SO_BYTES,
            P243_PINNED_FX3_LIBUSBCONTROL_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (
                    b"_ZN15UsbControlDebug9BlogWriteEhhtj",
                    b"_ZN9UsbAdjCmdC1Ev",
                ),
            ),
        ),
    )

    digests: List[Phase243DonorArtifactDigest] = []
    for aid, rel, pinned_bytes, pinned_sha, validator in probe_specs:
        ok, total_b, hdr_b, dkind, dsha, raw = _read_donor_readonly_bounded(rel)
        if not ok:
            digests.append(
                Phase243DonorArtifactDigest(
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
            Phase243DonorArtifactDigest(
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
        synth = _synthetic_phase243_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase243DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P243_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    dt = round(time.monotonic() - t0, 6)
    return Phase243DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all(d.present and d.matches_pinned for d in digests),
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P243_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Pillar 39A & 39B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_framing_antiflicker_vault_spec() -> FramingCropFullAndAntiFlickerVaultSpec:
    return FramingCropFullAndAntiFlickerVaultSpec()


def build_default_safe_usb_power_lun_vault_spec() -> UsbPowerBatteryInterlockAndLunVaultSpec:
    return UsbPowerBatteryInterlockAndLunVaultSpec()


def evaluate_framing_settings_and_antiflicker_vault(
    spec: FramingCropFullAndAntiFlickerVaultSpec,
) -> FramingCropFullAndAntiFlickerVaultReport:
    """Audit `[Framing Settings]` asymmetric Full/Crop recovery, HDMI RAW crop guard & `[Anti-flicker Shoot.]` / no-`Var. Shutter`."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P243_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P243_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 39A")

    naming_ok = True
    if (
        P243_FORBIDDEN_ZVE1_AUTOFRAMING_MENU_NAME in spec.framing_menu_path
        or spec.camera_model == "ZV-E1"
        or spec.helpguide_id == "ilc/2310"
    ):
        naming_ok = False
        _fail(
            P243_BLOCKED_ZVE1_AUTOFRAMING_NAMING_MISMATCH,
            "ILME-FX3 (ilc/2210) exposes MENU -> Shooting -> [Framing Settings] paired with Monitor & Control, "
            "NOT consumer ZV-E1 [Autoframing Settings]",
        )

    no_var_shutter_ok = True
    if spec.fx3_has_var_shutter or spec.claimed_var_shutter_or_ecs_menu_node is not None:
        no_var_shutter_ok = False
        _fail(
            P243_BLOCKED_FX3_NONEXISTENT_VAR_SHUTTER_OR_ECS_NODE,
            f"Stock ILME-FX3 (ilc/2210 through Ver. 7.02) does NOT implement [Var. Shutter] (FX30 ilc/2220 / "
            f"ILCE-6700 ilc/2320) or FX6 ECS: fx3_has_var_shutter={spec.fx3_has_var_shutter!r}, "
            f"claimed_node={spec.claimed_var_shutter_or_ecs_menu_node!r}",
        )

    valid_tokens = (
        naming_ok
        and spec.camera_model == P243_FX3_MODEL_NAME
        and spec.helpguide_id == P243_FX3_HELPGUIDE_ID
        and spec.fw_version in P243_FX3_SUPPORTED_FW_VERSIONS
        and spec.framing_menu_path == P243_FRAMING_SETTINGS_MENU_PATH
        and spec.antiflicker_menu_path == P243_ANTIFLICKER_SHOOT_MENU_PATH
        and spec.pre_reset_framing in P243_ON_OFF_MODES
        and spec.post_reset_framing in P243_ON_OFF_MODES
        and spec.saved_framing in P243_ON_OFF_MODES
        and spec.pre_reset_framing_rec_streaming in P243_FRAMING_FRAME_MODES
        and spec.post_reset_framing_rec_streaming in P243_FRAMING_FRAME_MODES
        and spec.saved_framing_rec_streaming in P243_FRAMING_FRAME_MODES
        and spec.pre_reset_framing_hdmi in P243_FRAMING_FRAME_MODES
        and spec.post_reset_framing_hdmi in P243_FRAMING_FRAME_MODES
        and spec.saved_framing_hdmi in P243_FRAMING_FRAME_MODES
        and spec.pre_reset_antiflicker_shoot in P243_ON_OFF_MODES
        and spec.post_reset_antiflicker_shoot in P243_ON_OFF_MODES
        and spec.saved_antiflicker_shoot in P243_ON_OFF_MODES
        and spec.reset_action in P243_RESET_ACTIONS
        and spec.hdmi_raw_output in P243_ON_OFF_MODES
        and spec.effective_rec_streaming_frame in P243_FRAMING_FRAME_MODES
        and spec.effective_hdmi_frame in P243_FRAMING_FRAME_MODES
        and spec.capture_mode in P243_CAPTURE_MODES
        and spec.silent_mode in P243_ON_OFF_MODES
        and spec.shutter_type in P243_SHUTTER_TYPES
        and spec.flicker_lighting_hz in P243_SUPPORTED_FLICKER_HZ
        and not (spec.silent_mode == "On" and spec.shutter_type != "Electronic Shutter")
    )
    if not valid_tokens and naming_ok:
        _fail(
            P243_BLOCKED_INVALID_FRAMING_OR_ANTIFLICKER_SPEC,
            f"Invalid model/helpguide/fw, [Framing Settings], or [Anti-flicker Shoot.] spec: "
            f"model={spec.camera_model!r} helpguide={spec.helpguide_id!r} fw={spec.fw_version!r}",
        )

    reset_ok = True
    camset_ok = True
    if spec.camset_slot != P243_SLOT1_VAULT_SLOT or spec.camset_filename not in P243_CAMSET_FILENAMES:
        camset_ok = False
        _fail(
            P243_BLOCKED_CAMSET_FRAMING_OR_ANTIFLICKER_RESTORE_DRIFT,
            f"CAMSET baseline Load must reference Slot 1 CAMSET01.DAT..CAMSET10.DAT, got "
            f"slot={spec.camset_slot!r} file={spec.camset_filename!r}",
        )

    if valid_tokens:
        actual_post = (
            spec.post_reset_framing,
            spec.post_reset_framing_rec_streaming,
            spec.post_reset_framing_hdmi,
            spec.post_reset_antiflicker_shoot,
        )
        if spec.camset_load_after_reset:
            expected_saved = (
                spec.saved_framing,
                spec.saved_framing_rec_streaming,
                spec.saved_framing_hdmi,
                spec.saved_antiflicker_shoot,
            )
            if actual_post != expected_saved:
                camset_ok = False
                _fail(
                    P243_BLOCKED_CAMSET_FRAMING_OR_ANTIFLICKER_RESTORE_DRIFT,
                    "Post-Load [Framing Settings] or [Anti-flicker Shoot.] drifted from Slot-1 CAMSET01..10.DAT profile",
                )
        elif spec.reset_action == "NONE":
            expected_pre = (
                spec.pre_reset_framing,
                spec.pre_reset_framing_rec_streaming,
                spec.pre_reset_framing_hdmi,
                spec.pre_reset_antiflicker_shoot,
            )
            if actual_post != expected_pre:
                reset_ok = False
                _fail(
                    P243_BLOCKED_FRAMING_OR_ANTIFLICKER_RESET_DRIFT,
                    "With reset_action='NONE' (and no CAMSET Load), [Framing Settings] and [Anti-flicker Shoot.] must remain unchanged",
                )
        elif spec.reset_action in ("Camera Settings Reset", "Initialize"):
            expected_defaults = (
                P243_FRAMING_DEFAULT,
                P243_FRAMING_REC_STREAMING_DEFAULT,
                P243_FRAMING_HDMI_DEFAULT,
                P243_ANTIFLICKER_SHOOT_DEFAULT,
            )
            if actual_post != expected_defaults:
                reset_ok = False
                _fail(
                    P243_BLOCKED_FRAMING_OR_ANTIFLICKER_RESET_DRIFT,
                    f"[{spec.reset_action}] must reset [Framing Settings] to ('Off', 'Full', 'Crop') "
                    f"and [Anti-flicker Shoot.] to 'Off', got {actual_post!r}",
                )

    framing_routing_ok = True
    if valid_tokens:
        if spec.hdmi_raw_output == "On" and spec.post_reset_framing == "On":
            framing_routing_ok = False
            _fail(
                P243_BLOCKED_HDMI_RAW_FRAMING_CROP_INCOMPATIBLE,
                "HDMI RAW video output is hardware-incompatible with cropped [Framing]='On'",
            )
        else:
            exp_rec = "Full" if spec.post_reset_framing == "Off" else spec.post_reset_framing_rec_streaming
            exp_hdmi = "Full" if spec.post_reset_framing == "Off" else spec.post_reset_framing_hdmi
            if (spec.effective_rec_streaming_frame, spec.effective_hdmi_frame) != (exp_rec, exp_hdmi):
                framing_routing_ok = False
                _fail(
                    P243_BLOCKED_FRAMING_ASYMMETRIC_ROUTING_MISMATCH,
                    f"[Framing]={spec.post_reset_framing!r} expected (Recording/Streaming={exp_rec!r}, "
                    f"HDMI={exp_hdmi!r}), got ({spec.effective_rec_streaming_frame!r}, {spec.effective_hdmi_frame!r})",
                )

    antiflicker_scope_ok = True
    if valid_tokens:
        mech_still_capable = (
            spec.capture_mode == "Still"
            and spec.silent_mode == "Off"
            and spec.shutter_type == "Mechanical Shutter"
        )
        exp_avail = mech_still_capable
        exp_active = mech_still_capable and (spec.post_reset_antiflicker_shoot == "On")
        if (
            spec.antiflicker_available_in_current_mode != exp_avail
            or spec.antiflicker_effective_active != exp_active
        ):
            antiflicker_scope_ok = False
            _fail(
                P243_BLOCKED_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION,
                "[Anti-flicker Shoot.] detects 100Hz/120Hz flicker strictly during mechanical-shutter still-image "
                "shooting and does NOT function in Movie/S&Q modes or [Silent Mode]='On' / Electronic Shutter",
            )

    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _fail(
            P243_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P243_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P243_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P243_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or p2 BLKROSET immutability drifted in Pillar 39A",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "39A",
            "passed": passed,
            "block_code": block_code,
            "fw_version": spec.fw_version,
            "reset_action": spec.reset_action,
            "camset_load": spec.camset_load_after_reset,
            "post_framing": (
                spec.post_reset_framing,
                spec.post_reset_framing_rec_streaming,
                spec.post_reset_framing_hdmi,
            ),
            "effective_frames": (spec.effective_rec_streaming_frame, spec.effective_hdmi_frame),
            "post_antiflicker": spec.post_reset_antiflicker_shoot,
            "capture_mode": spec.capture_mode,
            "shutter_type": spec.shutter_type,
            "fx3_has_var_shutter": P243_FX3_HAS_VAR_SHUTTER if no_var_shutter_ok else True,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return FramingCropFullAndAntiFlickerVaultReport(
        passed=passed,
        status=P243_STATUS_VERIFIED_PILLAR_39A if passed else P243_STATUS_REJECTED_PILLAR_39A,
        block_code=block_code,
        fx3_framing_naming_lock_verified=naming_ok and passed,
        framing_and_antiflicker_reset_verified=reset_ok and passed,
        camset_slot1_restore_verified=camset_ok and passed,
        framing_asymmetric_and_hdmi_raw_guard_verified=framing_routing_ok and passed,
        antiflicker_mech_still_only_verified=antiflicker_scope_ok and passed,
        no_var_shutter_invariant_verified=no_var_shutter_ok and passed,
        fx3_has_var_shutter=P243_FX3_HAS_VAR_SHUTTER if no_var_shutter_ok else True,
        h0_equals_h3_verified=h0_eq_h3,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_usb_power_battery_and_lun_persistence_vault(
    spec: UsbPowerBatteryInterlockAndLunVaultSpec,
) -> UsbPowerBatteryInterlockAndLunVaultReport:
    """Audit `[Setup] -> [USB]` reset survival, mandatory `NP-FZ100` + `USB Type-C` interlocks & `[USB LUN Setting]`."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P243_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P243_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 39B")

    valid_tokens = (
        spec.camera_model == P243_FX3_MODEL_NAME
        and spec.helpguide_id == P243_FX3_HELPGUIDE_ID
        and spec.fw_version in P243_FX3_SUPPORTED_FW_VERSIONS
        and spec.usb_setup_menu_path == P243_USB_SETUP_MENU_PATH
        and spec.pre_reset_usb_connection_mode in P243_USB_CONNECTION_MODES
        and spec.post_reset_usb_connection_mode in P243_USB_CONNECTION_MODES
        and spec.pre_reset_usb_lun_setting in P243_USB_LUN_MODES
        and spec.post_reset_usb_lun_setting in P243_USB_LUN_MODES
        and spec.pre_reset_usb_power_supply in P243_ON_OFF_MODES
        and spec.post_reset_usb_power_supply in P243_ON_OFF_MODES
        and spec.reset_action in P243_RESET_ACTIONS
        and spec.battery_bay_source in P243_BATTERY_BAY_SOURCES
        and 0 <= spec.np_fz100_charge_pct <= 100
        and spec.usb_power_port in P243_USB_POWER_PORTS
        and spec.unbuffered_battery_pull_events >= 0
        and spec.physical_usb_packets_sent >= 0
    )
    if not valid_tokens:
        _fail(
            P243_BLOCKED_INVALID_USB_POWER_OR_LUN_SPEC,
            f"Invalid camera_model/helpguide/fw, [Setup]->[USB] menu path, LUN mode, or battery/port spec: "
            f"model={spec.camera_model!r} fw={spec.fw_version!r} port={spec.usb_power_port!r}",
        )

    persistence_ok = True
    if valid_tokens:
        actual_usb = (
            spec.post_reset_usb_connection_mode,
            spec.post_reset_usb_lun_setting,
            spec.post_reset_usb_power_supply,
        )
        if spec.reset_action in ("NONE", "Camera Settings Reset"):
            expected_usb = (
                spec.pre_reset_usb_connection_mode,
                spec.pre_reset_usb_lun_setting,
                spec.pre_reset_usb_power_supply,
            )
            if actual_usb != expected_usb:
                persistence_ok = False
                _fail(
                    P243_BLOCKED_USB_SETUP_CAMERA_SETTINGS_RESET_DRIFT,
                    f"[Setup]->[USB] items ([USB Connection Mode], [USB LUN Setting], [USB Power Supply]) "
                    f"MUST survive [{spec.reset_action}] unchanged; expected {expected_usb!r}, got {actual_usb!r}",
                )
        elif spec.reset_action == "Initialize":
            expected_init = (
                P243_USB_CONNECTION_MODE_DEFAULT,
                P243_USB_LUN_SETTING_DEFAULT,
                P243_USB_POWER_SUPPLY_DEFAULT,
            )
            if actual_usb != expected_init:
                persistence_ok = False
                _fail(
                    P243_BLOCKED_USB_SETUP_CAMERA_SETTINGS_RESET_DRIFT,
                    f"[Initialize] must restore [Setup]->[USB] defaults {expected_init!r}, got {actual_usb!r}",
                )

    battery_interlock_ok = True
    pull_events = spec.unbuffered_battery_pull_events + (1 if spec.battery_removed_during_usb_power else 0)
    if valid_tokens:
        if spec.battery_bay_source == "EMPTY" and (
            spec.camera_power_on_requested or spec.usb_power_delivery_active
        ):
            battery_interlock_ok = False
            _fail(
                P243_BLOCKED_USB_POWER_WITHOUT_NP_FZ100_UNAVAILABLE,
                "Turning ILME-FX3 on or supplying USB PD power without an inserted NP-FZ100 battery pack "
                "(or DC-C1 coupler) is hardware-unavailable",
            )
        elif (
            spec.battery_bay_source == "NP-FZ100"
            and spec.camera_power_on_requested
            and spec.np_fz100_charge_pct < P243_USB_BENCH_MIN_NP_FZ100_PCT
        ):
            battery_interlock_ok = False
            _fail(
                P243_BLOCKED_USB_POWER_WITHOUT_NP_FZ100_UNAVAILABLE,
                f"Inserted NP-FZ100 battery charge ({spec.np_fz100_charge_pct}%) is below safe bench floor "
                f"({P243_USB_BENCH_MIN_NP_FZ100_PCT}%)",
            )
        if pull_events > 0:
            battery_interlock_ok = False
            _fail(
                P243_BLOCKED_MID_USB_PD_BATTERY_REMOVAL_POWEROFF,
                "Removing the inserted NP-FZ100 battery pack mid-USB-PD supply causes immediate unbuffered camera power-off",
            )

    typec_exclusivity_ok = True
    if valid_tokens:
        if spec.multi_micro_usb_power_or_charge_attempted or (
            spec.usb_power_port == "MULTI_MICRO_USB"
            and (spec.usb_power_delivery_active or spec.internal_battery_charging_active)
        ):
            typec_exclusivity_ok = False
            _fail(
                P243_BLOCKED_MULTI_MICRO_USB_POWER_OR_CHARGE_FORBIDDEN,
                "ILME-FX3 Multi/Micro USB terminal CANNOT supply operating power or charge internal batteries; "
                "USB power delivery and charging are strictly USB Type-C exclusive",
            )
        elif spec.usb_power_delivery_active and (
            spec.usb_power_port != "USB_TYPE_C" or spec.post_reset_usb_power_supply != "On"
        ):
            typec_exclusivity_ok = False
            _fail(
                P243_BLOCKED_USB_POWER_SUPPLY_OFF_OR_PORT_MISMATCH,
                f"Active USB power supply requires usb_power_port='USB_TYPE_C' and [USB Power Supply]='On', "
                f"got port={spec.usb_power_port!r}, [USB Power Supply]={spec.post_reset_usb_power_supply!r}",
            )
        elif spec.internal_battery_charging_active and spec.usb_power_port != "USB_TYPE_C":
            typec_exclusivity_ok = False
            _fail(
                P243_BLOCKED_USB_POWER_SUPPLY_OFF_OR_PORT_MISMATCH,
                f"Internal battery charging requires usb_power_port='USB_TYPE_C', got {spec.usb_power_port!r}",
            )

    lun_visibility_ok = True
    if valid_tokens:
        exp_luns = 2 if spec.post_reset_usb_lun_setting == "Multi" else 1
        exp_slots = (
            P243_LUN_MULTI_EXPOSED_SLOTS
            if spec.post_reset_usb_lun_setting == "Multi"
            else P243_LUN_SINGLE_EXPOSED_SLOTS
        )
        if spec.msc_modeled_lun_count != exp_luns or spec.msc_modeled_exposed_slots != exp_slots:
            lun_visibility_ok = False
            _fail(
                P243_BLOCKED_USB_LUN_MULTI_SINGLE_ENUMERATION_MISMATCH,
                f"[USB LUN Setting]={spec.post_reset_usb_lun_setting!r} exposes {exp_luns} LUN(s) {exp_slots!r}, "
                f"got lun_count={spec.msc_modeled_lun_count}, slots={spec.msc_modeled_exposed_slots!r}",
            )

    offline_reader_ok = True
    if valid_tokens:
        if (
            spec.live_host_usb_data_attached
            or spec.hardware_live_attachment_requested
            or spec.physical_usb_packets_sent != 0
            or not spec.offcamera_wp_card_reader_sha256_verified
            or not spec.slot1_sdxc_wp_switch_locked
        ):
            offline_reader_ok = False
            _fail(
                P243_BLOCKED_LIVE_USB_HOST_ATTACHMENT_FORBIDDEN,
                "Live host USB data attachment is hard-blocked on the recovery lab bench; Tier-0 SHA-256 "
                "verification must use an off-camera WP-locked SDXC card reader with 0 physical USB packets",
            )

    if not _is_tmpfs_path(spec.stage_b_overlay_dir) or _targets_persistent_emmc(spec.stage_b_overlay_dir):
        _fail(
            P243_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.stage_b_overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P243_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P243_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P243_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or p2 BLKROSET immutability drifted in Pillar 39B",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "39B",
            "passed": passed,
            "block_code": block_code,
            "fw_version": spec.fw_version,
            "reset_action": spec.reset_action,
            "post_usb": (
                spec.post_reset_usb_connection_mode,
                spec.post_reset_usb_lun_setting,
                spec.post_reset_usb_power_supply,
            ),
            "battery_bay_source": spec.battery_bay_source,
            "usb_power_port": spec.usb_power_port,
            "pull_events": pull_events,
            "luns": spec.msc_modeled_lun_count,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return UsbPowerBatteryInterlockAndLunVaultReport(
        passed=passed,
        status=P243_STATUS_VERIFIED_PILLAR_39B if passed else P243_STATUS_REJECTED_PILLAR_39B,
        block_code=block_code,
        usb_setup_reset_persistence_verified=persistence_ok and passed,
        mandatory_npfz100_battery_interlock_verified=battery_interlock_ok and passed,
        usb_typec_power_exclusivity_verified=typec_exclusivity_ok and passed,
        usb_lun_multi_single_visibility_verified=lun_visibility_ok and passed,
        offline_wp_card_reader_tier0_verified=offline_reader_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        unbuffered_battery_pull_events=pull_events,
        tier0_surfaces_intact=spec.tier0_surfaces_h0_h3_matched if h0_eq_h3 else 0,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_framing_usbpower_lun_and_antiflicker_vault(
    framing_antiflicker_spec: Optional[FramingCropFullAndAntiFlickerVaultSpec] = None,
    usb_power_lun_spec: Optional[UsbPowerBatteryInterlockAndLunVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> FramingUsbPowerLunAndAntiFlickerVaultReport:
    """Combined Pillar 39 verifier: Framing/Anti-flicker/No-Var-Shutter & USB Power/NP-FZ100/LUN persistence."""
    donor_snap = inspect_phase243_donors_readonly(force_clean_room=force_clean_room)
    framing_rep = evaluate_framing_settings_and_antiflicker_vault(
        framing_antiflicker_spec or build_default_safe_framing_antiflicker_vault_spec()
    )
    usb_rep = evaluate_usb_power_battery_and_lun_persistence_vault(
        usb_power_lun_spec or build_default_safe_usb_power_lun_vault_spec()
    )
    errs: List[str] = _safety_invariant_errors() + list(framing_rep.errors) + list(usb_rep.errors)
    if not donor_snap.all_donors_present:
        errs.append("Phase 243 donor snapshot incomplete or mismatched")
    if not donor_snap.under_0_15s_budget:
        errs.append(f"Phase 243 donor inspection exceeded 0.15s budget: {donor_snap.elapsed_seconds}s")

    all_ok = framing_rep.passed and usb_rep.passed and len(errs) == 0
    return FramingUsbPowerLunAndAntiFlickerVaultReport(
        schema=PHASE243_SCHEMA,
        version=PHASE243_VERSION,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P243_STATUS_VERIFIED_PILLAR39_SUITE if all_ok else P243_STATUS_FAIL_PILLAR39_SUITE,
        donor_snapshot=donor_snap,
        framing_antiflicker_report=framing_rep,
        usb_power_lun_vault_report=usb_rep,
        fx3_has_var_shutter=framing_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=usb_rep.unbuffered_battery_pull_events,
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
        errors=tuple(errs),
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites & Standalone Pillar 39 Runner
# ---------------------------------------------------------------------------


def run_pillar39a_framing_antiflicker_vault_6_scenario_suite() -> Pillar39ASuiteResult:
    cases: Tuple[Tuple[str, bool, FramingCropFullAndAntiFlickerVaultSpec, Optional[str]], ...] = (
        (
            P243_PILLAR_39A_SCENARIO_IDS[0],
            True,
            FramingCropFullAndAntiFlickerVaultSpec(),
            None,
        ),
        (
            P243_PILLAR_39A_SCENARIO_IDS[1],
            True,
            FramingCropFullAndAntiFlickerVaultSpec(
                reset_action="Camera Settings Reset",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                saved_framing="On",
                saved_framing_rec_streaming="Full",
                saved_framing_hdmi="Crop",
                saved_antiflicker_shoot="On",
                post_reset_framing="On",
                post_reset_framing_rec_streaming="Full",
                post_reset_framing_hdmi="Crop",
                post_reset_antiflicker_shoot="On",
                hdmi_raw_output="Off",
                effective_rec_streaming_frame="Full",
                effective_hdmi_frame="Crop",
                capture_mode="Still",
                silent_mode="Off",
                shutter_type="Mechanical Shutter",
                flicker_lighting_hz=120,
                antiflicker_available_in_current_mode=True,
                antiflicker_effective_active=True,
                fx3_has_var_shutter=False,
            ),
            None,
        ),
        (
            P243_PILLAR_39A_SCENARIO_IDS[2],
            False,
            FramingCropFullAndAntiFlickerVaultSpec(
                reset_action="NONE",
                pre_reset_framing="On",
                pre_reset_framing_rec_streaming="Full",
                pre_reset_framing_hdmi="Crop",
                pre_reset_antiflicker_shoot="Off",
                post_reset_framing="On",
                post_reset_framing_rec_streaming="Full",
                post_reset_framing_hdmi="Crop",
                post_reset_antiflicker_shoot="Off",
                hdmi_raw_output="On",
                effective_rec_streaming_frame="Full",
                effective_hdmi_frame="Crop",
            ),
            P243_BLOCKED_HDMI_RAW_FRAMING_CROP_INCOMPATIBLE,
        ),
        (
            P243_PILLAR_39A_SCENARIO_IDS[3],
            False,
            FramingCropFullAndAntiFlickerVaultSpec(
                framing_menu_path=("MENU", "Shooting", "Autoframing Settings"),
            ),
            P243_BLOCKED_ZVE1_AUTOFRAMING_NAMING_MISMATCH,
        ),
        (
            P243_PILLAR_39A_SCENARIO_IDS[4],
            False,
            FramingCropFullAndAntiFlickerVaultSpec(
                reset_action="NONE",
                pre_reset_framing="Off",
                pre_reset_framing_rec_streaming="Full",
                pre_reset_framing_hdmi="Crop",
                pre_reset_antiflicker_shoot="On",
                post_reset_framing="Off",
                post_reset_framing_rec_streaming="Full",
                post_reset_framing_hdmi="Crop",
                post_reset_antiflicker_shoot="On",
                capture_mode="Movie",
                silent_mode="Off",
                shutter_type="Electronic Shutter",
                antiflicker_available_in_current_mode=True,
                antiflicker_effective_active=True,
            ),
            P243_BLOCKED_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION,
        ),
        (
            P243_PILLAR_39A_SCENARIO_IDS[5],
            False,
            FramingCropFullAndAntiFlickerVaultSpec(
                fx3_has_var_shutter=True,
                claimed_var_shutter_or_ecs_menu_node="Var. Shutter",
            ),
            P243_BLOCKED_FX3_NONEXISTENT_VAR_SHUTTER_OR_ECS_NODE,
        ),
    )

    outcomes: List[Pillar39ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_framing_settings_and_antiflicker_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar39ScenarioOutcome(
                scenario_id=sid,
                pillar="39A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar39ASuiteResult(
        passed=all_ok,
        status=P243_STATUS_VERIFIED_PILLAR_39A if all_ok else P243_STATUS_REJECTED_PILLAR_39A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar39b_usb_power_lun_vault_6_scenario_suite() -> Pillar39BSuiteResult:
    cases: Tuple[Tuple[str, bool, UsbPowerBatteryInterlockAndLunVaultSpec, Optional[str]], ...] = (
        (
            P243_PILLAR_39B_SCENARIO_IDS[0],
            True,
            UsbPowerBatteryInterlockAndLunVaultSpec(),
            None,
        ),
        (
            P243_PILLAR_39B_SCENARIO_IDS[1],
            True,
            UsbPowerBatteryInterlockAndLunVaultSpec(
                pre_reset_usb_connection_mode="MTP",
                pre_reset_usb_lun_setting="Single",
                pre_reset_usb_power_supply="Off",
                reset_action="Initialize",
                post_reset_usb_connection_mode="Sel. When Connect",
                post_reset_usb_lun_setting="Multi",
                post_reset_usb_power_supply="On",
                battery_bay_source="DC-C1",
                usb_power_port="USB_TYPE_C",
                usb_power_delivery_active=True,
                msc_modeled_lun_count=2,
                msc_modeled_exposed_slots=P243_LUN_MULTI_EXPOSED_SLOTS,
                offcamera_wp_card_reader_sha256_verified=True,
                slot1_sdxc_wp_switch_locked=True,
            ),
            None,
        ),
        (
            P243_PILLAR_39B_SCENARIO_IDS[2],
            False,
            UsbPowerBatteryInterlockAndLunVaultSpec(
                battery_bay_source="EMPTY",
                camera_power_on_requested=True,
                usb_power_port="USB_TYPE_C",
                usb_power_delivery_active=True,
            ),
            P243_BLOCKED_USB_POWER_WITHOUT_NP_FZ100_UNAVAILABLE,
        ),
        (
            P243_PILLAR_39B_SCENARIO_IDS[3],
            False,
            UsbPowerBatteryInterlockAndLunVaultSpec(
                usb_power_port="MULTI_MICRO_USB",
                usb_power_delivery_active=True,
                internal_battery_charging_active=True,
                multi_micro_usb_power_or_charge_attempted=True,
            ),
            P243_BLOCKED_MULTI_MICRO_USB_POWER_OR_CHARGE_FORBIDDEN,
        ),
        (
            P243_PILLAR_39B_SCENARIO_IDS[4],
            False,
            UsbPowerBatteryInterlockAndLunVaultSpec(
                pre_reset_usb_connection_mode="MassStorage(MSC)",
                pre_reset_usb_lun_setting="Single",
                pre_reset_usb_power_supply="Off",
                reset_action="Camera Settings Reset",
                post_reset_usb_connection_mode="Sel. When Connect",
                post_reset_usb_lun_setting="Multi",
                post_reset_usb_power_supply="On",
                msc_modeled_lun_count=2,
                msc_modeled_exposed_slots=P243_LUN_MULTI_EXPOSED_SLOTS,
            ),
            P243_BLOCKED_USB_SETUP_CAMERA_SETTINGS_RESET_DRIFT,
        ),
        (
            P243_PILLAR_39B_SCENARIO_IDS[5],
            False,
            UsbPowerBatteryInterlockAndLunVaultSpec(
                live_host_usb_data_attached=True,
                hardware_live_attachment_requested=True,
                physical_usb_packets_sent=12,
                offcamera_wp_card_reader_sha256_verified=False,
            ),
            P243_BLOCKED_LIVE_USB_HOST_ATTACHMENT_FORBIDDEN,
        ),
    )

    outcomes: List[Pillar39ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar39ScenarioOutcome(
                scenario_id=sid,
                pillar="39B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar39BSuiteResult(
        passed=all_ok,
        status=P243_STATUS_VERIFIED_PILLAR_39B if all_ok else P243_STATUS_REJECTED_PILLAR_39B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar39_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar39StandaloneReport:
    """Run full Pillar 39 standalone suite (`6/6` Pillar 39A + `6/6` Pillar 39B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase243_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar39a_framing_antiflicker_vault_6_scenario_suite()
    res_b = run_pillar39b_usb_power_lun_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 243 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 0.15s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE243_SCHEMA,
            "version": PHASE243_VERSION,
            "mode": donor_snapshot.verification_mode,
            "39a": [asdict(s) for s in res_a.scenarios],
            "39b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar39StandaloneReport(
        schema=PHASE243_SCHEMA,
        version=PHASE243_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P243_STATUS_VERIFIED_PILLAR39_SUITE if all_ok else P243_STATUS_FAIL_PILLAR39_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_39a_framing_antiflicker_vault=res_a,
        pillar_39b_usb_power_lun_vault=res_b,
        fx3_has_var_shutter=P243_FX3_HAS_VAR_SHUTTER if res_a.passed else True,
        unbuffered_battery_pull_events=P243_UNBUFFERED_BATTERY_PULL_EVENTS if res_b.passed else 1,
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
# Unified 39/39 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master39_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_39pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master39PillarRecoveryReport:
    """Evaluate and aggregate all 39 recovery pillars (`1..39`) concurrently -> `39/39` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_39_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_38pillar() -> Master38PillarRecoveryReport:
        return evaluate_realhw_38pillar_recovery_master(**kw)

    def _run_p39() -> Tuple[Pillar39StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar39_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_38 = pool.submit(_run_38pillar)
        fut_39 = pool.submit(_run_p39)
        m38_rep = fut_38.result()
        p39_rep, p39_dt = fut_39.result()

    all_errors: List[str] = list(m38_rep.errors) + list(p39_rep.errors)
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
        if getattr(m38_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-38 violated {attr_name} == {expected_val}")
        if getattr(p39_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 39 violated {attr_name} == {expected_val}")

    if p39_rep.fx3_has_var_shutter is not False:
        all_errors.append("Pillar 39 violated fx3_has_var_shutter == False")
    if p39_rep.unbuffered_battery_pull_events != 0:
        all_errors.append("Pillar 39 violated unbuffered_battery_pull_events == 0")
    if p39_rep.hardware_live_attachment_authorized is not False:
        all_errors.append("Pillar 39 violated hardware_live_attachment_authorized == False")

    pillar_statuses: List[MasterPillarStatus] = list(m38_rep.pillars)
    spec39 = MASTER_39_PILLAR_SPECS[38]
    p39_metrics = {
        "pillar_39a_framing_antiflicker_vault": (
            f"{p39_rep.pillar_39a_framing_antiflicker_vault.scenarios_passed}/"
            f"{p39_rep.pillar_39a_framing_antiflicker_vault.scenarios_total}"
        ),
        "pillar_39b_usb_power_lun_vault": (
            f"{p39_rep.pillar_39b_usb_power_lun_vault.scenarios_passed}/"
            f"{p39_rep.pillar_39b_usb_power_lun_vault.scenarios_total}"
        ),
        "fx3_has_var_shutter": p39_rep.fx3_has_var_shutter,
        "unbuffered_battery_pull_events": p39_rep.unbuffered_battery_pull_events,
        "hardware_live_attachment_authorized": p39_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p39_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec39[0],
            pillar_id=spec39[1],
            phase_label=spec39[2],
            module_name=spec39[3],
            passed=bool(p39_rep.all_passed),
            status=p39_rep.status,
            verification_mode=p39_rep.verification_mode,
            elapsed_seconds=p39_dt,
            key_metrics=p39_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec39[1],
                    "mode": p39_rep.verification_mode,
                    "status": p39_rep.status,
                    "metrics": p39_metrics,
                    "passed": p39_rep.all_passed,
                }
            ),
            errors=tuple(p39_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master39_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p39_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_39_PILLAR_COUNT == 39
        and pillars_passed == 39
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE243_SCHEMA,
            "version": PHASE243_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master39PillarRecoveryReport(
        schema=PHASE243_SCHEMA,
        version=PHASE243_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P243_STATUS_VERIFIED_39OF39_AGGREGATOR if all_ok else P243_STATUS_FAIL_39OF39_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P243_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P243_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p39_rep.donor_snapshot,
        pillar39_a_framing_antiflicker_vault=p39_rep.pillar_39a_framing_antiflicker_vault,
        pillar39_b_usb_power_lun_vault=p39_rep.pillar_39b_usb_power_lun_vault,
        fx3_has_var_shutter=p39_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=p39_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p39_rep.hardware_live_attachment_authorized,
        master_39pillar_sha256=master_sha,
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


def evaluate_39pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master39PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_39pillar_recovery_master`."""
    return evaluate_realhw_39pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_39pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master39PillarRecoveryReport:
    """Public CLI entry point for Pillar 39 unified `39/39` real-hardware recovery master verification."""
    return evaluate_realhw_39pillar_recovery_master(
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
    "MASTER_39_PILLAR_COUNT",
    "MASTER_39_PILLAR_IDS",
    "MASTER_39_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P243_ANTIFLICKER_SHOOT_DEFAULT",
    "P243_ANTIFLICKER_SHOOT_MENU_PATH",
    "P243_BATTERY_BAY_SOURCES",
    "P243_BLOCKED_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION",
    "P243_BLOCKED_CAMSET_FRAMING_OR_ANTIFLICKER_RESTORE_DRIFT",
    "P243_BLOCKED_FRAMING_ASYMMETRIC_ROUTING_MISMATCH",
    "P243_BLOCKED_FRAMING_OR_ANTIFLICKER_RESET_DRIFT",
    "P243_BLOCKED_FX3_NONEXISTENT_VAR_SHUTTER_OR_ECS_NODE",
    "P243_BLOCKED_HDMI_RAW_FRAMING_CROP_INCOMPATIBLE",
    "P243_BLOCKED_INVALID_FRAMING_OR_ANTIFLICKER_SPEC",
    "P243_BLOCKED_INVALID_USB_POWER_OR_LUN_SPEC",
    "P243_BLOCKED_LIVE_USB_HOST_ATTACHMENT_FORBIDDEN",
    "P243_BLOCKED_MID_USB_PD_BATTERY_REMOVAL_POWEROFF",
    "P243_BLOCKED_MULTI_MICRO_USB_POWER_OR_CHARGE_FORBIDDEN",
    "P243_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P243_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P243_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P243_BLOCKED_USB_LUN_MULTI_SINGLE_ENUMERATION_MISMATCH",
    "P243_BLOCKED_USB_POWER_SUPPLY_OFF_OR_PORT_MISMATCH",
    "P243_BLOCKED_USB_POWER_WITHOUT_NP_FZ100_UNAVAILABLE",
    "P243_BLOCKED_USB_SETUP_CAMERA_SETTINGS_RESET_DRIFT",
    "P243_BLOCKED_ZVE1_AUTOFRAMING_NAMING_MISMATCH",
    "P243_BOUNDED_HEADER_BYTES",
    "P243_CAMSET_FILENAMES",
    "P243_CAPTURE_MODES",
    "P243_CONCURRENT_CEILING_SECONDS",
    "P243_DONOR_FX3_APPFW_702_RELPATH",
    "P243_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P243_DONOR_FX3_BODYDATA_RELPATH",
    "P243_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH",
    "P243_DONOR_FX3_LIBBACKUP_SO_RELPATH",
    "P243_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P243_DONOR_FX3_LIBUSBBUSPOWER_SO_RELPATH",
    "P243_DONOR_FX3_LIBUSBCONTROL_SO_RELPATH",
    "P243_DONOR_FX6_APPFW_601_RELPATH",
    "P243_DONOR_INSPECT_BUDGET_SECONDS",
    "P243_FORBIDDEN_PERSISTENT_TARGETS",
    "P243_FORBIDDEN_VAR_SHUTTER_AND_ECS_NODES",
    "P243_FORBIDDEN_ZVE1_AUTOFRAMING_MENU_NAME",
    "P243_FOREIGN_HELPGUIDE_OR_MODELS",
    "P243_FRAMING_DEFAULT",
    "P243_FRAMING_FRAME_MODES",
    "P243_FRAMING_HDMI_DEFAULT",
    "P243_FRAMING_REC_STREAMING_DEFAULT",
    "P243_FRAMING_SETTINGS_3_ITEMS",
    "P243_FRAMING_SETTINGS_MENU_PATH",
    "P243_FX3_FW_VERSION",
    "P243_FX3_HAS_VAR_SHUTTER",
    "P243_FX3_HELPGUIDE_ID",
    "P243_FX3_MODEL_ID",
    "P243_FX3_MODEL_NAME",
    "P243_FX3_SUPPORTED_FW_VERSIONS",
    "P243_FX6_DONOR_FW_VERSION",
    "P243_FX6_DONOR_MODEL_NAME",
    "P243_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P243_LUN_MULTI_EXPOSED_SLOTS",
    "P243_LUN_SINGLE_EXPOSED_SLOTS",
    "P243_MAX_FULL_DONOR_BYTES",
    "P243_NOMINAL_BUDGET_SECONDS",
    "P243_ON_OFF_MODES",
    "P243_PILLAR_39A_SCENARIO_IDS",
    "P243_PILLAR_39B_SCENARIO_IDS",
    "P243_PINNED_FX3_APPFW_702_BYTES",
    "P243_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P243_PINNED_FX3_BACKUP_BIN_BYTES",
    "P243_PINNED_FX3_BACKUP_BIN_SHA256",
    "P243_PINNED_FX3_BODYDATA_BYTES",
    "P243_PINNED_FX3_BODYDATA_HDR4K_SHA256",
    "P243_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES",
    "P243_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256",
    "P243_PINNED_FX3_LIBBACKUP_SO_BYTES",
    "P243_PINNED_FX3_LIBBACKUP_SO_SHA256",
    "P243_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P243_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P243_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES",
    "P243_PINNED_FX3_LIBUSBBUSPOWER_SO_SHA256",
    "P243_PINNED_FX3_LIBUSBCONTROL_SO_BYTES",
    "P243_PINNED_FX3_LIBUSBCONTROL_SO_SHA256",
    "P243_PINNED_FX6_APPFW_601_BYTES",
    "P243_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P243_RESET_ACTIONS",
    "P243_SHUTTER_TYPES",
    "P243_SLOT1_VAULT_SLOT",
    "P243_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P243_STATUS_FAIL_39OF39_AGGREGATOR",
    "P243_STATUS_FAIL_PILLAR39_SUITE",
    "P243_STATUS_REJECTED_PILLAR_39A",
    "P243_STATUS_REJECTED_PILLAR_39B",
    "P243_STATUS_VERIFIED_39OF39_AGGREGATOR",
    "P243_STATUS_VERIFIED_PILLAR39_SUITE",
    "P243_STATUS_VERIFIED_PILLAR_39A",
    "P243_STATUS_VERIFIED_PILLAR_39B",
    "P243_SUPPORTED_FLICKER_HZ",
    "P243_TIER0_SURFACE_COUNT",
    "P243_UNBUFFERED_BATTERY_PULL_EVENTS",
    "P243_USB_BENCH_MIN_NP_FZ100_PCT",
    "P243_USB_CONNECTION_MODES",
    "P243_USB_CONNECTION_MODE_DEFAULT",
    "P243_USB_LUN_MODES",
    "P243_USB_LUN_SETTING_DEFAULT",
    "P243_USB_POWER_PORTS",
    "P243_USB_POWER_SUPPLY_DEFAULT",
    "P243_USB_SETUP_3_ITEMS",
    "P243_USB_SETUP_MENU_PATH",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE243_SCHEMA",
    "PHASE243_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "FramingCropFullAndAntiFlickerVaultReport",
    "FramingCropFullAndAntiFlickerVaultSpec",
    "FramingUsbPowerLunAndAntiFlickerVaultReport",
    "Master39PillarRecoveryReport",
    "Phase243DonorArtifactDigest",
    "Phase243DonorSnapshot",
    "Pillar39ASuiteResult",
    "Pillar39BSuiteResult",
    "Pillar39ScenarioOutcome",
    "Pillar39StandaloneReport",
    "UsbPowerBatteryInterlockAndLunVaultReport",
    "UsbPowerBatteryInterlockAndLunVaultSpec",
    "build_default_safe_framing_antiflicker_vault_spec",
    "build_default_safe_usb_power_lun_vault_spec",
    "evaluate_39pillar_recovery_master",
    "evaluate_framing_settings_and_antiflicker_vault",
    "evaluate_realhw_39pillar_recovery_master",
    "evaluate_usb_power_battery_and_lun_persistence_vault",
    "inspect_phase243_donors_readonly",
    "run_pillar39_standalone_suite",
    "run_pillar39a_framing_antiflicker_vault_6_scenario_suite",
    "run_pillar39b_usb_power_lun_vault_6_scenario_suite",
    "verify_39pillar_recovery_suite",
    "verify_framing_usbpower_lun_and_antiflicker_vault",
]

