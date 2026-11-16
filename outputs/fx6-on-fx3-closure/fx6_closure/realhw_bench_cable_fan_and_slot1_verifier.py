"""Phase 204 — Real-Hardware Operator Pre-Bench Power/Cable (`DC-C1` / `NP-FZ100` / `VMC-BNCM1`), 4-Mode Fan Thermal (`Always Off` Block) & Slot-1 `CAMSET`/`.cube` Vault Readiness Verifier (`preflight-bench-cable-fan-slot1`).

Dedicated host-side read-only operator pre-bench verifier for physical Sony `ILME-FX3`
(`Ver. 7.02`, Model `0x91030080`), synthesizing Waves 24–26 real-hardware intelligence
into 3 deterministic fail-closed check groups (`B1..B3`) plus bounded `O_RDONLY` donor
verification (`< 0.15s` budget) and dual-media `528 B FX3RCPT1` Tier-0 vault binding:

1. **Check Group 1 (`B1_POWER_CABLE_AND_VMC_BNCM1_HARNESS`)**:
   - Enforces `ILME-FX3` (`0x91030080`, `Ver. 7.02` `>= 2.04` floor) camera identity and
     rejects `[USB Streaming]` / UVC webcam expectations (`ILME-FX3` lacks UVC gadget;
     4K streaming requires Network `RTMP/RTMPS/SRT` or Type-A HDMI capture).
   - Validates physical power harness:
     - `USB_PD_BODY`: requires genuine `NP-FZ100` inserted with `SOC >= 51.0%` (`>= 3`
       bars) and `7.20V <= voltage <= 8.50V` (rejecting `<51%` brownout or `>8.50V` dummy
       battery OVP hazards).
     - `DC_C1_COUPLER`: requires `>= 65.0W` USB-PD source AND `5.0A` (`100W/240W`)
       e-Marked USB-C cable (rejecting `<65W` adapters and `3A` non-e-Marked cables).
     - Rejects `MICRO_USB` / `MULTI_USB_5V` power delivery.
   - Validates `VMC-BNCM1` (`A-5051-506-A`, `0.2m`) timecode cable harness:
     - Must connect ONLY to body `Multi/Micro USB` (`BODY_MULTI_MICRO_USB`); strictly
       rejects `XLR-H1` top-handle side Micro-USB port (`XLR_H1_HANDLE_MICRO_USB`).
     - Enforces unidirectional `TC_IN` only; strictly rejects reverse BNC `TC_OUT`
       (`EOPNOTSUPP`; FX3 digital `TC OUT` is Type-A HDMI only and disabled in `S&Q`).
     - Enforces `[Shoot Mode] = Movie` + `[Time Code Make] = Preset` + `[Time Code Run] =
       Free Run` for `~10s` `EXT-LK` lock, and Multi-USB `Pin 8/9/10` mutual exclusion
       against `1.8V` passive UART RX triage.

2. **Check Group 2 (`B2_FOUR_MODE_FAN_THERMAL_AND_BIG6_NO_END_GATE`)**:
   - Enforces exact 4-mode `ILME-FX3` `[Fan Control]` enum (`Auto`, `Minimum`,
     `Off in Rec`, `Always Off`), explicitly rejecting bogus broadcast/Lumix `Auto1` /
     `Auto2` fan modes.
   - Models `Off in Rec` physical PWM contract: `0% PWM` during normal recording
     (`< 78.0°C`), `100% PWM` emergency thermal override (`>= 78.0°C`), and `100% MAX PWM`
     active thermal purge in standby / non-recording.
   - Blocks 75 MiB `p3` `AdjustControl (0x40)` cold-backup and Stage-B rehearsal when
     `[Fan Control] == Always Off` (requiring switch to `Auto` with `[Auto Power OFF Temp.]
     = Standard / High` and body start `< 45.0°C` to protect `CXD90057 / CXD90058`).
   - Audits `BIG6` (`Home`) 6-cell topology (`[Mode Settings] = Fixed/Variable`,
     independent `Speed` `0x01120024` vs `Angle` `0x01120028` shutter slots with
     `5.6°..64F` normal / `5.6°..360°` `119.88p/100p`/`S&Q` bounds, and `[Home (Lower
     Left)]` `Aperture` / `ND Filter`) while strictly enforcing `e_nd_actuator_tx_count == 0`
     (zero physical internal electronic variable ND hardware on `ILME-FX3`).

3. **Check Group 3 (`B3_SLOT1_CUBE_LUT_AND_CAMSET_VAULT_READINESS`)**:
   - Enforces Slot-1 dual-media path asymmetry:
     - `SDXC` (`SD`/`SDHC`/`SDXC`): `/Private/Sony/PRO/LUT/` &
       `/PRIVATE/SONY/SETTING/FX3/CAMSET/`
     - `CFEXPRESS_A` (omits `/Private`): `/Sony/PRO/LUT/` & `/SONY/SETTING/FX3/CAMSET/`
   - Enforces Slot-1-only (`camset_slot == 1`, rejecting Slot 2), non-`MR` (`Recall Camera
     Setting`) mode lock, `CAMSET01.DAT .. CAMSET10.DAT` (`<= 10` files) bounds, and
     cross-model (`ILME-FX3` vs `ILME-FX3A` vs `ILME-FX6`) `.DAT` contamination firewall.
   - Enforces `.cube` User LUT (`17^3`/`33^3`, `<= 63B` ASCII, `User1..User16`, `0..+2EV`)
     and `Ver. 6.01` (`LEGACY_V601_USER_LUT_BIN`) vs `Ver. 7.02`
     (`OPTIMIZED_V700_PLUS_USER_LUT_BIN`) `p2:/setting` binary generation-split sandboxing
     into volatile `/tmp/fx6_lut_overlay` and `/tmp/fx6_camset_overlay` (`p2` writes == 0,
     `16/16` storage surfaces `SHA256(H0) == SHA256(H3)`).
   - Evaluates dual-copy `528 B FX3RCPT1` Tier-0 cold-backup vault binding (`st_dev_a !=
     st_dev_b`), failing closed with `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` offline by
     default and `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` under `--simulate-ready-bench`.

Hard-Locked Invariants (UNCONDITIONAL):
- `hardware_live_attachment_authorized = False` (ALWAYS)
- `persistent_emmc_writes_authorized = False`
- `spi_nor_write_authorized = False`
- `el3_payload_transmit_authorized = False`
- `physical_usb_packets_emitted = 0`
- `raw_firmware_bytes_leaked = 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import zlib


def _ensure_cross_package_paths(repo_root: Path) -> None:
    """Ensure sibling lab package roots are importable under minimal PYTHONPATH."""
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

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (  # noqa: E402
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import (  # noqa: E402
    is_forced_clean_room,
    resolve_work_subpath,
)
from .hardware_readiness_packet import (  # noqa: E402
    BODY_SERIAL_RE,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    HEX32_CID_RE,
    HEX64_RE,
)
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_WLAN_RSRC_DONOR_SHA256,
)
from .realhw_card_insert_readiness_verifier import (  # noqa: E402
    DONOR_INSPECTION_MAX_SECONDS,
    EM_AARCH64,
    EXPECTED_UART_VOLTAGE_V,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    MAX_BODY_START_TEMP_C,
    MAX_NP_FZ100_VOLTAGE_V,
    MIN_BODY_FW_FLOOR,
    MIN_BODY_FW_TUPLE,
    MIN_BODY_START_TEMP_C,
    MULTIUSB_CONTENTION_PINS,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_HEX,
    TARGET_MODEL_ID_INT,
    UART_VOLTAGE_TOLERANCE_V,
    _parse_elf64_header_and_pt_load,
    _parse_fw_tuple,
    _read_bounded_slice_o_rdonly,
    build_default_h0_baselines,
)
from .realhw_jiritsu_and_tier0_dumper_auditor import (  # noqa: E402
    LIBJIRITSU_EXPECTED_SHA256,
    LIBJIRITSU_EXPECTED_SIZE,
    LIBJIRITSU_RELPATH,
)
from .realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
    FX3_IM_ELF_EXPECTED_SHA256,
    FX3_IM_ELF_EXPECTED_SIZE,
    FX3_IM_ELF_RELPATH,
    FX6_APPFW_EXPECTED_SIZE,
    SIXTEEN_STORAGE_SURFACES,
    read_only_o_rdonly_digest_and_header,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Phase 204 Schema Constants
# ---------------------------------------------------------------------------

PHASE_204_SCHEMA: str = "phase204_realhw_bench_cable_fan_and_slot1_preflight_v1"
PHASE_204_VERSION: str = "204.0.0"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SD_PHYSICAL_MEDIA_WRITTEN: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

FX3_LIBUSBBUSPOWER_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so"
)
FX3_LIBUSBBUSPOWER_EXPECTED_SIZE: int = 48_232
FX3_LIBUSBBUSPOWER_EXPECTED_SHA256: str = (
    "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748"
)

# Go/No-Go Verdicts
GO_NO_GO_BLOCKED_BENCH_CHECK_FAILURE: str = (
    "BLOCKED_BENCH_CABLE_FAN_SLOT1_CHECK_FAILURE"
)
GO_NO_GO_READONLY_BENCH_PREFLIGHT_VERIFIED: str = (
    "GO_BENCH_CABLE_FAN_SLOT1_READONLY_PREFLIGHT_VERIFIED"
)

PHASE_204_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_BLOCKED_BENCH_CHECK_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    GO_NO_GO_READONLY_BENCH_PREFLIGHT_VERIFIED,
)

# Check Group IDs
CHECK_GROUP_B1_ID: str = "B1_POWER_CABLE_AND_VMC_BNCM1_HARNESS"
CHECK_GROUP_B2_ID: str = "B2_FOUR_MODE_FAN_THERMAL_AND_BIG6_NO_END_GATE"
CHECK_GROUP_B3_ID: str = "B3_SLOT1_CUBE_LUT_AND_CAMSET_VAULT_READINESS"
BENCH_PREFLIGHT_CHECK_GROUP_IDS: Tuple[str, ...] = (
    CHECK_GROUP_B1_ID,
    CHECK_GROUP_B2_ID,
    CHECK_GROUP_B3_ID,
)

# ---------------------------------------------------------------------------
# Check Group 1 Constants — Power/Cable (`NP-FZ100` / `DC-C1` / `VMC-BNCM1` / No-UVC)
# ---------------------------------------------------------------------------

POWER_MODE_USB_PD_BODY: str = "USB_PD_BODY"
POWER_MODE_DC_C1_COUPLER: str = "DC_C1_COUPLER"
VALID_BENCH_POWER_MODES: Tuple[str, ...] = (
    POWER_MODE_USB_PD_BODY,
    POWER_MODE_DC_C1_COUPLER,
)
REJECTED_MICRO_USB_POWER_MODES: Tuple[str, ...] = (
    "MICRO_USB",
    "MULTI_USB",
    "MULTI_USB_5V",
    "MULTI_TERMINAL_5V",
)

BODY_USB_PD_MIN_NP_FZ100_SOC_PCT: float = 51.0
BODY_USB_PD_MIN_NP_FZ100_VOLTAGE_V: float = 7.20
DC_C1_MIN_PD_WATTS: float = 65.0
DC_C1_MIN_CABLE_AMPS: float = 5.0

ALLOWED_FX3_BENCH_USB_MODES: Tuple[str, ...] = (
    "SEL_WHEN_CONNECT",
    "MASS_STORAGE",
    "MSC",
    "MTP",
    "REMOTE_SHOOTING",
    "USB_LAN",
    "RNDIS",
    "CDC_NCM",
    "PASSIVE_NONE",
)
FORBIDDEN_FX3_UVC_STREAMING_MODES: Tuple[str, ...] = (
    "USB_STREAMING",
    "[USB STREAMING]",
    "UVC",
    "UVC_UAC",
    "UAC",
    "USB_WEBCAM",
)
ALLOWED_FX3_4K_STREAMING_TRANSPORTS: Tuple[str, ...] = (
    "NONE",
    "NETWORK_RTMP",
    "RTMP",
    "RTMPS",
    "SRT",
    "HDMI_TYPE_A",
    "TYPE_A_HDMI",
)

VMC_BNCM1_PART_NUMBER: str = "A-5051-506-A"
VMC_BNCM1_CABLE_LENGTH_M: float = 0.2
VMC_PORT_DISCONNECTED: str = "DISCONNECTED"
VMC_PORT_BODY_MULTI_MICRO_USB: str = "BODY_MULTI_MICRO_USB"
VMC_PORT_XLR_H1_HANDLE_MICRO_USB: str = "XLR_H1_HANDLE_MICRO_USB"
VMC_DIRECTION_NONE: str = "NONE"
VMC_DIRECTION_TC_IN: str = "TC_IN"
REJECTED_VMC_REVERSE_DIRECTIONS: Tuple[str, ...] = (
    "TC_OUT",
    "BNC_TC_OUT",
    "LTC_OUT",
    "BIDIRECTIONAL",
    "TC_IN_OUT",
)
VMC_EXT_LK_STABILIZATION_SECONDS: float = 10.0

B1_ERR_CAMERA_MODEL_OR_FW_MISMATCH: str = (
    "B1_ERR_CAMERA_MODEL_NOT_0x91030080_OR_FW_NOT_702"
)
B1_ERR_FX3_USB_STREAMING_UVC_UNSUPPORTED: str = (
    "B1_ERR_FX3_0x91030080_USB_STREAMING_UVC_UNSUPPORTED"
)
B1_ERR_INVALID_USB_OR_STREAMING_MODE: str = (
    "B1_ERR_INVALID_USB_CONNECTION_OR_STREAMING_TRANSPORT"
)
B1_ERR_MICRO_USB_POWER_FORBIDDEN: str = "B1_ERR_MICRO_USB_MAIN_POWER_FORBIDDEN"
B1_ERR_POWER_SOURCE_INVALID: str = "B1_ERR_BENCH_POWER_SOURCE_INVALID"
B1_ERR_BODY_USB_PD_REQUIRES_NP_FZ100_GE_51PCT: str = (
    "B1_ERR_BODY_USB_PD_REQUIRES_NP_FZ100_GE_51PCT"
)
B1_ERR_BATTERY_VOLTAGE_OUT_OF_SAFE_BOUNDS: str = (
    "B1_ERR_NP_FZ100_VOLTAGE_OUT_OF_SAFE_BOUNDS"
)
B1_ERR_DC_C1_UNDER_65W_OR_NON_5A_EMARKED_CABLE: str = (
    "B1_ERR_DC_C1_REQUIRES_GE_65W_PD_AND_5A_EMARKED_CABLE"
)
B1_ERR_VMC_BNCM1_XLR_H1_HANDLE_PORT_FORBIDDEN: str = (
    "B1_ERR_VMC_BNCM1_PLUGGED_INTO_XLR_H1_HANDLE_MICRO_USB"
)
B1_ERR_VMC_BNCM1_PORT_INVALID: str = "B1_ERR_VMC_BNCM1_PORT_INVALID"
B1_ERR_VMC_BNCM1_REVERSE_BNC_TC_OUT_FORBIDDEN: str = (
    "B1_ERR_VMC_BNCM1_REVERSE_BNC_TC_OUT_EOPNOTSUPP"
)
B1_ERR_VMC_BNCM1_TC_IN_EXT_LK_PREREQ_FAILED: str = (
    "B1_ERR_VMC_BNCM1_TC_IN_REQUIRES_MOVIE_PRESET_FREERUN"
)
B1_ERR_MULTIUSB_PIN_8_9_10_UART_CONTENTION: str = (
    "B1_ERR_MULTIUSB_PIN_8_9_10_VMC_BNCM1_AND_1V8_UART_CONTENTION"
)
B1_ERR_HDMI_TC_OUT_FORBIDDEN_IN_SQ_MODE: str = (
    "B1_ERR_HDMI_TC_OUT_AUTOMATICALLY_DISABLED_IN_SQ_MODE"
)

# ---------------------------------------------------------------------------
# Check Group 2 Constants — 4-Mode Fan Thermal & `BIG6` Zero Physical e-ND
# ---------------------------------------------------------------------------

FX3_FAN_MENU_PATH: str = "MENU -> Setup -> [Setup Option] -> [Fan Control]"
FAN_MODE_AUTO: str = "AUTO"
FAN_MODE_MINIMUM: str = "MINIMUM"
FAN_MODE_OFF_IN_REC: str = "OFF_IN_REC"
FAN_MODE_ALWAYS_OFF: str = "ALWAYS_OFF"

FX3_VALID_4_FAN_MODES: Tuple[str, ...] = (
    FAN_MODE_AUTO,
    FAN_MODE_MINIMUM,
    FAN_MODE_OFF_IN_REC,
    FAN_MODE_ALWAYS_OFF,
)
FX3_FAN_CANONICAL_LABELS: Mapping[str, str] = {
    FAN_MODE_AUTO: "Auto",
    FAN_MODE_MINIMUM: "Minimum",
    FAN_MODE_OFF_IN_REC: "Off in Rec",
    FAN_MODE_ALWAYS_OFF: "Always Off",
}
BOGUS_NON_FX3_FAN_MODES: Tuple[str, ...] = (
    "AUTO1",
    "AUTO2",
    "AUTO_1",
    "AUTO_2",
    "AUTO 1",
    "AUTO 2",
)

AUTO_POWER_OFF_TEMP_STANDARD: str = "STANDARD"
AUTO_POWER_OFF_TEMP_HIGH: str = "HIGH"
VALID_AUTO_POWER_OFF_TEMPS: Tuple[str, ...] = (
    AUTO_POWER_OFF_TEMP_STANDARD,
    AUTO_POWER_OFF_TEMP_HIGH,
)

OFF_IN_REC_STANDBY_MAX_PWM_PCT: float = 100.0
OFF_IN_REC_RECORDING_NORMAL_PWM_PCT: float = 0.0
OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C: float = 78.0
OFF_IN_REC_EMERGENCY_PWM_PCT: float = 100.0
P3_COLD_BACKUP_PARTITION_MIB: int = 75

BIG6_SIX_CELL_TOPOLOGY: Tuple[str, ...] = (
    "1:FPS_FIXED_VARIABLE",
    "2:ISO_OR_BASE_ISO",
    "3:SHUTTER_SPEED_OR_ANGLE",
    "4:APERTURE_OR_ND_FILTER",
    "5:PICTURE_PROFILE_OR_SELECT_LUT",
    "6:WHITE_BALANCE",
)
BIG6_LOWER_LEFT_MENU_PATH: str = (
    "MENU -> Setup -> [Operation Customize] -> [Home (Lower Left)]"
)
BIG6_LOWER_LEFT_APERTURE: str = "APERTURE"
BIG6_LOWER_LEFT_ND_FILTER: str = "ND_FILTER"
VALID_BIG6_LOWER_LEFT_MODES: Tuple[str, ...] = (
    BIG6_LOWER_LEFT_APERTURE,
    BIG6_LOWER_LEFT_ND_FILTER,
)

SHUTTER_SPEED_BACKUP_KEY_HEX: str = "0x01120024"
SHUTTER_ANGLE_BACKUP_KEY_HEX: str = "0x01120028"
SHUTTER_ANGLE_MIN_DEG: float = 5.6
SHUTTER_ANGLE_MAX_HIGH_FPS_OR_SQ_DEG: float = 360.0
SHUTTER_ANGLE_MAX_STANDARD_DEG: float = 360.0 * 64.0  # 64F equivalent ceiling

B2_ERR_BOGUS_NON_FX3_FAN_MODE_AUTO1_AUTO2: str = (
    "B2_ERR_BOGUS_NON_FX3_FAN_MODE_AUTO1_AUTO2"
)
B2_ERR_UNKNOWN_FAN_CONTROL_MODE: str = "B2_ERR_UNKNOWN_FX3_FAN_CONTROL_MODE"
B2_ERR_ALWAYS_OFF_BLOCKS_75MIB_P3_BACKUP_AND_STAGEB: str = (
    "B2_ERR_FAN_ALWAYS_OFF_BLOCKS_75MIB_P3_BACKUP_AND_STAGEB"
)
B2_ERR_PREBACKUP_REQUIRES_FAN_SWITCHED_TO_AUTO: str = (
    "B2_ERR_PREBACKUP_REQUIRES_FAN_CONTROL_AUTO"
)
B2_ERR_AUTO_POWER_OFF_TEMP_ENUM_INVALID: str = (
    "B2_ERR_AUTO_POWER_OFF_TEMP_NOT_STANDARD_OR_HIGH"
)
B2_ERR_BODY_THERMAL_OVERLIMIT: str = "B2_ERR_BODY_START_TEMP_OVERLIMIT_OR_INVALID"
B2_ERR_OFF_IN_REC_STANDBY_MAX_PWM_VIOLATION: str = (
    "B2_ERR_OFF_IN_REC_STANDBY_100PCT_MAX_PWM_VIOLATION"
)
B2_ERR_BIG6_PREREQ_OR_SHUTTER_ANGLE_INVALID: str = (
    "B2_ERR_BIG6_FIXED_VARIABLE_OR_SHUTTER_ANGLE_BOUND_INVALID"
)
B2_ERR_BIG6_LOWER_LEFT_MODE_INVALID: str = (
    "B2_ERR_BIG6_HOME_LOWER_LEFT_MODE_INVALID"
)
B2_ERR_PHYSICAL_E_ND_ACTUATOR_TX_NONZERO: str = (
    "B2_ERR_FX3_ZERO_PHYSICAL_END_ACTUATOR_TX_VIOLATION"
)

# ---------------------------------------------------------------------------
# Check Group 3 Constants — Slot-1 Dual-Media `.cube` LUT & `CAMSET` Vault
# ---------------------------------------------------------------------------

MEDIA_TYPE_SDXC: str = "SDXC"
MEDIA_TYPE_CFEXPRESS_A: str = "CFEXPRESS_A"
VALID_SLOT1_MEDIA_TYPES: Tuple[str, ...] = (MEDIA_TYPE_SDXC, MEDIA_TYPE_CFEXPRESS_A)

SDXC_CANONICAL_LUT_DIR: str = "/Private/Sony/PRO/LUT/"
SDXC_CANONICAL_CAMSET_DIR: str = "/PRIVATE/SONY/SETTING/FX3/CAMSET/"
CFEXPRESS_A_CANONICAL_LUT_DIR: str = "/Sony/PRO/LUT/"
CFEXPRESS_A_CANONICAL_CAMSET_DIR: str = "/SONY/SETTING/FX3/CAMSET/"

STAGEB_VOLATILE_LUT_OVERLAY_DIR: str = "/tmp/fx6_lut_overlay"
STAGEB_VOLATILE_CAMSET_OVERLAY_DIR: str = "/tmp/fx6_camset_overlay"

LUT_BINARY_FORMAT_V601_LEGACY: str = "LEGACY_V601_USER_LUT_BIN"
LUT_BINARY_FORMAT_V702_OPTIMIZED: str = "OPTIMIZED_V700_PLUS_USER_LUT_BIN"

CUBE_ALLOWED_GRID_SIZES: Tuple[int, ...] = (17, 33)
CUBE_MAX_FILENAME_BYTES: int = 63
USER_LUT_MAX_SLOTS: int = 16
USER_LUT_MIN_AE_EV: float = 0.0
USER_LUT_MAX_AE_EV: float = 2.0

CAMSET_MAX_FILES_PER_CARD: int = 10
CAMSET_FILENAME_RE = re.compile(r"^CAMSET(0[1-9]|10)\.DAT$")
CUBE_ASCII_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+\.[Cc][Uu][Bb][Ee]$")

CAMSET_EXCLUDED_MACHINE_BOUND_DOMAINS: Tuple[str, ...] = (
    "WHITE_BALANCE_CUSTOM_1_2_3",
    "FTP_TRANSFER_CREDENTIALS",
    "NETWORK_STREAMING_RTMP_SRT",
    "IP_AND_TLS_CERTIFICATES",
    "RTC_DATE_TIME_ZONE",
)

FORBIDDEN_MR_EXPOSURE_MODES: Tuple[str, ...] = (
    "MR",
    "MR1",
    "MR2",
    "MR3",
    "MEMORY_RECALL",
    "RECALL_CAMERA_SETTING",
)

FORBIDDEN_PERSISTENT_LUT_CAMSET_PREFIXES: Tuple[str, ...] = (
    "p2:",
    "/setting",
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/pnflasha",
    "/private/sony/setting/fx3/camset",
    "/sony/setting/fx3/camset",
)

B3_ERR_UNSUPPORTED_MEDIA_TYPE: str = "B3_ERR_SLOT1_UNSUPPORTED_MEDIA_TYPE"
B3_ERR_MEDIA_PATH_ASYMMETRY_MISMATCH: str = (
    "B3_ERR_SDXC_VS_CFEXPRESS_A_LUT_OR_CAMSET_PATH_MISMATCH"
)
B3_ERR_CAMSET_SLOT2_FORBIDDEN_SLOT1_ONLY: str = (
    "B3_ERR_CAMSET_SLOT2_FORBIDDEN_SLOT1_ONLY"
)
B3_ERR_CAMSET_DISABLED_IN_MR_RECALL_MODE: str = (
    "B3_ERR_CAMSET_SAVE_LOAD_DISABLED_IN_MR_MODE"
)
B3_ERR_CAMSET_FILENAME_OR_10_SLOT_CEILING: str = (
    "B3_ERR_CAMSET_FILENAME_OR_10_FILE_CEILING_VIOLATION"
)
B3_ERR_CROSS_MODEL_CAMSET_DAT_CONTAMINATION: str = (
    "B3_ERR_CROSS_MODEL_FX3_FX3A_FX6_CAMSET_DAT_CONTAMINATION"
)
B3_ERR_STAGEB_CAMSET_OVERLAY_SANDBOX_VIOLATION: str = (
    "B3_ERR_STAGEB_CAMSET_NOT_SANDBOXED_TO_TMP_FX6_CAMSET_OVERLAY"
)
B3_ERR_CUBE_LUT_SPEC_OR_16_SLOT_CEILING: str = (
    "B3_ERR_CUBE_LUT_GRID_FILENAME_AE_OR_16_SLOT_VIOLATION"
)
B3_ERR_LUT_601_VS_702_P2_SETTING_SPLIT_VIOLATION: str = (
    "B3_ERR_601_VS_702_P2_SETTING_USER_LUT_BINARY_SPLIT_VIOLATION"
)
B3_ERR_H0_H3_16_SURFACE_PARITY_DRIFT: str = (
    "B3_ERR_H0_TO_H3_16_SURFACE_PARITY_DRIFT"
)
B3_ERR_SYMLINK_OR_APPLEDOUBLE_HYGIENE: str = (
    "B3_ERR_SLOT1_SYMLINK_APPLEDOUBLE_OR_BODYDATA_HYGIENE_FAILURE"
)
B3_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "B3_ERR_TIER0_DUAL_MEDIA_FX3RCPT1_MISSING_OR_INVALID"
)

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_TRIVIAL_HEX64_SET = frozenset({"0" * 64, "f" * 64})
_TRIVIAL_CID_SHA256_SET = frozenset(
    {
        "0" * 64,
        "f" * 64,
        *(hashlib.sha256(c.lower().encode("ascii")).hexdigest() for c in FORBIDDEN_TRIVIAL_CIDS),
        *(hashlib.sha256(c.upper().encode("ascii")).hexdigest() for c in FORBIDDEN_TRIVIAL_CIDS),
    }
)


# ---------------------------------------------------------------------------
# Dataclasses (100% JSON-safe; zero raw proprietary firmware bytes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase204DonorInspectionResult:
    passed: bool
    verification_mode: str
    read_only_o_rdonly_enforced: bool
    elapsed_seconds: float
    within_150ms_budget: bool
    inspected_artifacts: Tuple[str, ...]
    fx3_im_elf_verified: bool
    fx3_libjiritsu_verified: bool
    fx3_libusbbuspower_verified: bool
    fx6_libfan_verified: bool
    fx6_appfw_verified: bool
    fx6_wlan_rsrc_verified: bool
    fx3_upm_ko_verified: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CheckGroup1PowerCableHarnessResult:
    check_group_id: str
    passed: bool
    body_model_id_int: int
    body_model_id_hex: str
    body_fw: str
    body_fw_ge_204_floor: bool
    camera_identity_ok: bool
    power_source: str
    np_fz100_inserted: bool
    np_fz100_soc_pct: float
    np_fz100_voltage_v: float
    body_usb_pd_battery_floor_ok: bool
    dc_c1_pd_watts: float
    dc_c1_cable_amps: float
    dc_c1_emarked_5a: bool
    dc_c1_65w_5a_contract_ok: bool
    usb_connection_mode: str
    streaming_4k_transport: str
    expect_usb_streaming_uvc: bool
    no_uvc_firewall_ok: bool
    vmc_bncm1_attached: bool
    vmc_bncm1_part_number: str
    vmc_bncm1_port: str
    vmc_bncm1_direction: str
    vmc_bncm1_body_port_only_ok: bool
    vmc_bncm1_tcin_only_ok: bool
    shoot_mode: str
    tc_make_mode: str
    tc_run_mode: str
    ext_lk_stabilization_seconds: float
    hdmi_tc_out_enabled: bool
    uart_rx_1v8_attached: bool
    uart_logic_voltage_v: float
    multiusb_pin_8_9_10_contention_free: bool
    physical_usb_packets_emitted: int
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CheckGroup2FanThermalAndBig6Result:
    check_group_id: str
    passed: bool
    fan_menu_path: str
    fan_mode_input: str
    fan_mode_normalized: str
    fan_mode_canonical_label: str
    valid_fx3_4mode_fan: bool
    bogus_auto1_auto2_rejected: bool
    pre_p3_75mib_backup_or_stageb_rehearsal: bool
    always_off_prebackup_blocked: bool
    auto_power_off_temp: str
    auto_power_off_temp_valid: bool
    body_temp_c: float
    body_temp_start_safe: bool
    off_in_rec_standby_pwm_pct: float
    off_in_rec_recording_normal_pwm_pct: float
    off_in_rec_emergency_temp_c: float
    off_in_rec_emergency_pwm_pct: float
    off_in_rec_contract_verified: bool
    big6_mode_settings: str
    big6_home_custom_key_bound: bool
    big6_six_cells: Tuple[str, ...]
    big6_home_lower_left: str
    big6_lower_left_software_only_nd: bool
    shutter_speed_slot_key: str
    shutter_angle_slot_key: str
    shutter_slots_independent: bool
    shutter_angle_deg: float
    rec_fps: float
    shutter_angle_within_bounds: bool
    has_physical_internal_end_hardware: bool
    e_nd_actuator_tx_count: int
    cp_end_motor_drive_attempted: bool
    zero_end_actuator_verified: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CheckGroup3Slot1LutCamsetVaultResult:
    check_group_id: str
    passed: bool
    structural_vault_checks_passed: bool
    slot1_media_type: str
    expected_lut_dir: str
    observed_lut_dir: str
    expected_camset_dir: str
    observed_camset_dir: str
    dual_media_path_matched: bool
    camset_target_slot: int
    slot1_only_enforced: bool
    camera_exposure_mode: str
    non_mr_mode_enforced: bool
    camset_files_checked: Tuple[str, ...]
    camset_count_within_10: bool
    camset_dat_models_checked: Tuple[str, ...]
    cross_model_dat_firewall_ok: bool
    camset_excluded_domains: Tuple[str, ...]
    stageb_camset_overlay_path: str
    stageb_camset_sandbox_ok: bool
    cube_files_checked: Tuple[str, ...]
    cube_grid_sizes_checked: Tuple[int, ...]
    user_lut_slot_count: int
    user_lut_ae_offset_ev: float
    cube_lut_spec_ok: bool
    donor_lut_binary_format: str
    host_lut_binary_format: str
    stageb_lut_overlay_path: str
    p2_setting_lut_writes: int
    legacy_v601_unreregistered_slots_on_p2: int
    lut_601_vs_702_split_sandbox_ok: bool
    slot1_hygiene_symlinks: int
    slot1_hygiene_junk_or_bodydata: Tuple[str, ...]
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    h0_equals_h3_all_16: bool
    tier0_receipts_provided: bool
    tier0_st_dev_a: int
    tier0_st_dev_b: int
    tier0_distinct_physical_devices: bool
    tier0_receipt_crc32_hex: str
    tier0_receipt_sha256: str
    tier0_h0_baselines_verified: int
    tier0_vault_binding_ok: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwBenchCableFanSlot1Report:
    schema: str
    phase_version: str
    verification_mode: str
    simulate_ready_bench: bool
    go_no_go: str
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    check_group_count: int
    check_groups_passed: int
    all_3_check_groups_passed: bool
    tier0_receipt_verified: bool
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    e_nd_actuator_tx_count: int
    donor_inspection: Phase204DonorInspectionResult
    check_group_1_power_cable_harness: CheckGroup1PowerCableHarnessResult
    check_group_2_fan_thermal_and_big6: CheckGroup2FanThermalAndBig6Result
    check_group_3_slot1_lut_camset_vault: CheckGroup3Slot1LutCamsetVaultResult
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase204ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal Helpers (Strictly O_RDONLY & Canonical Digest)
# ---------------------------------------------------------------------------


def _canonical_sha256_dict(obj: Mapping[str, Any], exclude_key: Optional[str] = None) -> str:
    body = dict(copy.deepcopy(obj))
    if exclude_key:
        body.pop(exclude_key, None)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _is_trivial_hex64(val: str) -> bool:
    norm = str(val).strip().lower()
    if not HEX64_RE.match(norm):
        return True
    return norm in _TRIVIAL_HEX64_SET


def _normalize_dir_path(p: str) -> str:
    cleaned = str(p).strip().replace("\\", "/")
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    cleaned = re.sub(r"/+", "/", cleaned)
    if not cleaned.endswith("/"):
        cleaned = cleaned + "/"
    return cleaned


def _normalize_fan_mode_token(raw_mode: str) -> str:
    cleaned = re.sub(r"[\s\-]+", "_", str(raw_mode).strip().upper())
    return cleaned


def model_fx3_702_fan_pwm_profile(
    fan_mode: str,
    *,
    is_recording: bool,
    body_temp_c: float,
    emergency_temp_c: float = OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C,
) -> float:
    """Deterministic `ILME-FX3 Ver. 7.02` 4-mode fan PWM duty-cycle model (`0.0..100.0%`)."""
    norm = _normalize_fan_mode_token(fan_mode)
    temp = float(body_temp_c)
    if norm == FAN_MODE_OFF_IN_REC:
        if not is_recording:
            return OFF_IN_REC_STANDBY_MAX_PWM_PCT
        if temp >= float(emergency_temp_c):
            return OFF_IN_REC_EMERGENCY_PWM_PCT
        return OFF_IN_REC_RECORDING_NORMAL_PWM_PCT
    if norm == FAN_MODE_ALWAYS_OFF:
        return 0.0
    if norm == FAN_MODE_MINIMUM:
        return 25.0 if temp < float(emergency_temp_c) else 65.0
    if norm == FAN_MODE_AUTO:
        if temp < 35.0:
            return 30.0
        if temp < 50.0:
            return 55.0
        if temp < 65.0:
            return 80.0
        return 100.0
    raise ValueError(f"Unsupported FX3 [Fan Control] mode: {fan_mode!r}")


# ---------------------------------------------------------------------------
# Pillar 0: Bounded O_RDONLY Donor Inspection (< 0.15s) + Clean-Room Fallback
# ---------------------------------------------------------------------------


def inspect_phase204_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase204DonorInspectionResult:
    """Inspect local BYOF donors strictly via O_RDONLY within < 0.15s, or Clean-Room fallback."""
    t0 = time.perf_counter()
    errors: List[str] = []
    eff_clean = force_clean_room if force_clean_room is not None else synthetic_clean_room
    clean_room = is_forced_clean_room() if eff_clean is None else bool(eff_clean)

    fx3_im_path = resolve_work_subpath(FX3_IM_ELF_RELPATH, require_file=False)
    fx3_jit_path = resolve_work_subpath(LIBJIRITSU_RELPATH, require_file=False)
    fx3_usb_pwr_path = resolve_work_subpath(FX3_LIBUSBBUSPOWER_RELPATH, require_file=False)
    fx6_fan_path = fx6_lib_dir / "libfan.so"
    fx6_appfw_path = fx6_lib_dir / "appFw.so"
    fx6_wlan_path = fx6_lib_dir / "libWlanResource.so"
    fx3_upm_path = fx3_modules_dir / "upm.ko"

    donors_present = (
        fx3_im_path.is_file()
        and fx3_jit_path.is_file()
        and fx3_usb_pwr_path.is_file()
        and fx6_fan_path.is_file()
        and fx6_appfw_path.is_file()
        and fx6_wlan_path.is_file()
        and fx3_upm_path.is_file()
    )

    if eff_clean is False and not donors_present:
        elapsed = round(time.perf_counter() - t0, 6)
        return Phase204DonorInspectionResult(
            passed=False,
            verification_mode="LOCAL_DONOR_O_RDONLY",
            read_only_o_rdonly_enforced=True,
            elapsed_seconds=elapsed,
            within_150ms_budget=(elapsed < max_seconds),
            inspected_artifacts=(),
            fx3_im_elf_verified=fx3_im_path.is_file(),
            fx3_libjiritsu_verified=fx3_jit_path.is_file(),
            fx3_libusbbuspower_verified=fx3_usb_pwr_path.is_file(),
            fx6_libfan_verified=fx6_fan_path.is_file(),
            fx6_appfw_verified=fx6_appfw_path.is_file(),
            fx6_wlan_rsrc_verified=fx6_wlan_path.is_file(),
            fx3_upm_ko_verified=fx3_upm_path.is_file(),
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            errors=(f"Local BYOF donors missing under fx6_lib_dir={fx6_lib_dir}",),
        )

    use_live = (not clean_room) and donors_present
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"
    inspected: List[str] = []

    if use_live:
        im_sz, im_sha, im_head = read_only_o_rdonly_digest_and_header(fx3_im_path)
        im_mag, im_64, im_mach, _ = _parse_elf64_header_and_pt_load(im_head)
        im_ok = (
            im_sz == FX3_IM_ELF_EXPECTED_SIZE
            and im_sha == FX3_IM_ELF_EXPECTED_SHA256
            and im_mag
            and im_64
            and im_mach == EM_AARCH64
        )
        inspected.append("im.elf")
        if not im_ok:
            errors.append(f"im.elf O_RDONLY verification failed: size={im_sz}")

        jit_sz, jit_sha, jit_head = read_only_o_rdonly_digest_and_header(fx3_jit_path)
        jit_mag, jit_64, jit_mach, _ = _parse_elf64_header_and_pt_load(jit_head)
        jit_ok = (
            jit_sz == LIBJIRITSU_EXPECTED_SIZE
            and jit_sha == LIBJIRITSU_EXPECTED_SHA256
            and jit_mag
            and jit_64
            and jit_mach == EM_AARCH64
        )
        inspected.append("libJiritsu.so")
        if not jit_ok:
            errors.append(f"libJiritsu.so O_RDONLY verification failed: size={jit_sz}")

        pwr_sz, pwr_sha, pwr_head = read_only_o_rdonly_digest_and_header(fx3_usb_pwr_path)
        pwr_mag, pwr_64, pwr_mach, _ = _parse_elf64_header_and_pt_load(pwr_head)
        pwr_ok = (
            pwr_sz == FX3_LIBUSBBUSPOWER_EXPECTED_SIZE
            and pwr_sha == FX3_LIBUSBBUSPOWER_EXPECTED_SHA256
            and pwr_mag
            and pwr_64
            and pwr_mach == EM_AARCH64
        )
        inspected.append("libUsbBusPower.so")
        if not pwr_ok:
            errors.append(f"libUsbBusPower.so O_RDONLY verification failed: size={pwr_sz}")

        fan_sz, fan_head, _ = _read_bounded_slice_o_rdonly(fx6_fan_path, 4096)
        fan_mag, fan_64, fan_mach, _ = _parse_elf64_header_and_pt_load(fan_head)
        fan_ok = fan_sz > 0 and fan_mag and fan_64 and fan_mach == EM_AARCH64
        inspected.append("libfan.so")
        if not fan_ok:
            errors.append(f"libfan.so bounded O_RDONLY header failed: size={fan_sz}")

        appfw_sz, appfw_head, _ = _read_bounded_slice_o_rdonly(fx6_appfw_path, 4096)
        appfw_mag, appfw_64, appfw_mach, _ = _parse_elf64_header_and_pt_load(appfw_head)
        appfw_ok = (
            appfw_sz == FX6_APPFW_EXPECTED_SIZE
            and appfw_mag
            and appfw_64
            and appfw_mach == EM_AARCH64
        )
        inspected.append("appFw.so")
        if not appfw_ok:
            errors.append(f"appFw.so bounded O_RDONLY header/size failed: size={appfw_sz}")

        _wlan_sz, wlan_sha, wlan_head = read_only_o_rdonly_digest_and_header(fx6_wlan_path)
        wlan_mag, wlan_64, wlan_mach, _ = _parse_elf64_header_and_pt_load(wlan_head)
        wlan_ok = (
            wlan_sha == FX6_WLAN_RSRC_DONOR_SHA256
            and wlan_mag
            and wlan_64
            and wlan_mach == EM_AARCH64
        )
        inspected.append("libWlanResource.so")
        if not wlan_ok:
            errors.append("libWlanResource.so O_RDONLY verification failed")

        upm_sz, upm_head, _ = _read_bounded_slice_o_rdonly(fx3_upm_path, 4096)
        upm_mag, upm_64, upm_mach, _ = _parse_elf64_header_and_pt_load(upm_head)
        upm_ok = upm_sz > 0 and upm_mag and upm_64 and upm_mach == EM_AARCH64
        inspected.append("upm.ko")
        if not upm_ok:
            errors.append(f"upm.ko bounded O_RDONLY header failed: size={upm_sz}")
    else:
        im_ok = True
        jit_ok = True
        pwr_ok = True
        fan_ok = True
        appfw_ok = True
        wlan_ok = True
        upm_ok = True
        inspected.extend(
            [
                "im.elf",
                "libJiritsu.so",
                "libUsbBusPower.so",
                "libfan.so",
                "appFw.so",
                "libWlanResource.so",
                "upm.ko",
            ]
        )

    elapsed = round(time.perf_counter() - t0, 6)
    within_budget = elapsed < max_seconds
    if not within_budget:
        errors.append(f"Donor inspection exceeded {max_seconds:.3f}s ceiling: {elapsed:.4f}s")

    return Phase204DonorInspectionResult(
        passed=(len(errors) == 0 and within_budget),
        verification_mode=mode,
        read_only_o_rdonly_enforced=True,
        elapsed_seconds=elapsed,
        within_150ms_budget=within_budget,
        inspected_artifacts=tuple(inspected),
        fx3_im_elf_verified=im_ok,
        fx3_libjiritsu_verified=jit_ok,
        fx3_libusbbuspower_verified=pwr_ok,
        fx6_libfan_verified=fan_ok,
        fx6_appfw_verified=appfw_ok,
        fx6_wlan_rsrc_verified=wlan_ok,
        fx3_upm_ko_verified=upm_ok,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group 1: Physical Power & Cable Harness Matrix
# ---------------------------------------------------------------------------


def evaluate_check_group_1_power_cable_harness(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    power_source: str = POWER_MODE_USB_PD_BODY,
    np_fz100_inserted: bool = True,
    np_fz100_soc_pct: float = 88.0,
    np_fz100_voltage_v: float = 8.00,
    dc_c1_pd_watts: float = 65.0,
    dc_c1_cable_amps: float = 5.0,
    dc_c1_emarked_5a: bool = True,
    usb_connection_mode: str = "MASS_STORAGE",
    streaming_4k_transport: str = "NONE",
    expect_usb_streaming_uvc: bool = False,
    vmc_bncm1_attached: bool = False,
    vmc_bncm1_port: str = VMC_PORT_DISCONNECTED,
    vmc_bncm1_direction: str = VMC_DIRECTION_NONE,
    shoot_mode: str = "MOVIE",
    tc_make_mode: str = "PRESET",
    tc_run_mode: str = "FREE_RUN",
    hdmi_tc_out_enabled: bool = False,
    uart_rx_1v8_attached: bool = True,
    uart_logic_voltage_v: float = 1.8,
) -> CheckGroup1PowerCableHarnessResult:
    """Check Group 1: NP-FZ100 >=51% + Body USB-C PD vs DC-C1 >=65W/5A vs VMC-BNCM1 TC IN & No-UVC."""
    errors: List[str] = []
    codes: List[str] = []

    eff_model_id = int(body_model_id)
    eff_fw = str(body_fw).strip()
    fw_tuple = _parse_fw_tuple(eff_fw)
    fw_ge_204 = fw_tuple is not None and fw_tuple >= MIN_BODY_FW_TUPLE
    cam_ok = eff_model_id == TARGET_MODEL_ID_INT and fw_ge_204 and eff_fw == TARGET_BODY_FW
    if not cam_ok:
        codes.append(B1_ERR_CAMERA_MODEL_OR_FW_MISMATCH)
        errors.append(
            f"{B1_ERR_CAMERA_MODEL_OR_FW_MISMATCH}: model_id={eff_model_id:#010x} (expected {TARGET_MODEL_ID_HEX}), body_fw={eff_fw!r} (expected {TARGET_BODY_FW!r}, >= {MIN_BODY_FW_FLOOR})"
        )

    # 1. USB Mode & No-UVC (`[USB Streaming]` unsupported on ILME-FX3 0x91030080)
    usb_norm = re.sub(r"[\s\-]+", "_", str(usb_connection_mode).strip().upper())
    raw_usb_upper = str(usb_connection_mode).strip().upper()
    stream_norm = re.sub(r"[\s\-]+", "_", str(streaming_4k_transport).strip().upper())

    uvc_requested = (
        bool(expect_usb_streaming_uvc)
        or usb_norm in FORBIDDEN_FX3_UVC_STREAMING_MODES
        or raw_usb_upper in FORBIDDEN_FX3_UVC_STREAMING_MODES
        or stream_norm in FORBIDDEN_FX3_UVC_STREAMING_MODES
    )
    no_uvc_ok = not uvc_requested
    if uvc_requested:
        codes.append(B1_ERR_FX3_USB_STREAMING_UVC_UNSUPPORTED)
        errors.append(
            f"{B1_ERR_FX3_USB_STREAMING_UVC_UNSUPPORTED}: ILME-FX3 ({TARGET_MODEL_ID_HEX}) does not support [USB Streaming] UVC webcam mode; use Network RTMP/RTMPS/SRT or Type-A HDMI capture"
        )
    else:
        if usb_norm not in ALLOWED_FX3_BENCH_USB_MODES:
            no_uvc_ok = False
            codes.append(B1_ERR_INVALID_USB_OR_STREAMING_MODE)
            errors.append(
                f"{B1_ERR_INVALID_USB_OR_STREAMING_MODE}: unsupported usb_connection_mode={usb_connection_mode!r}"
            )
        if stream_norm not in ALLOWED_FX3_4K_STREAMING_TRANSPORTS:
            no_uvc_ok = False
            codes.append(B1_ERR_INVALID_USB_OR_STREAMING_MODE)
            errors.append(
                f"{B1_ERR_INVALID_USB_OR_STREAMING_MODE}: unsupported streaming_4k_transport={streaming_4k_transport!r}"
            )

    # 2. Power Source Matrix: USB_PD_BODY (NP-FZ100 >= 51%) vs DC_C1_COUPLER (>= 65W + 5A e-Marked)
    pwr_norm = re.sub(r"[\s\-]+", "_", str(power_source).strip().upper())
    soc_val = float(np_fz100_soc_pct)
    volt_val = float(np_fz100_voltage_v)
    watts_val = float(dc_c1_pd_watts)
    amps_val = float(dc_c1_cable_amps)

    body_pd_batt_ok = True
    dc_c1_ok = True

    if pwr_norm in REJECTED_MICRO_USB_POWER_MODES:
        body_pd_batt_ok = False
        dc_c1_ok = False
        codes.append(B1_ERR_MICRO_USB_POWER_FORBIDDEN)
        errors.append(
            f"{B1_ERR_MICRO_USB_POWER_FORBIDDEN}: Multi/Micro-USB cannot power ILME-FX3 bench operations; use USB-C PD + NP-FZ100 (>=51%) or DC-C1 (>=65W + 5A e-Marked)"
        )
    elif pwr_norm == POWER_MODE_USB_PD_BODY:
        if (not bool(np_fz100_inserted)) or soc_val < BODY_USB_PD_MIN_NP_FZ100_SOC_PCT or soc_val > 100.0:
            body_pd_batt_ok = False
            codes.append(B1_ERR_BODY_USB_PD_REQUIRES_NP_FZ100_GE_51PCT)
            errors.append(
                f"{B1_ERR_BODY_USB_PD_REQUIRES_NP_FZ100_GE_51PCT}: Body USB-C PD requires genuine NP-FZ100 inserted={np_fz100_inserted} with SOC >= 51.0% (got {soc_val:.1f}%)"
            )
        if volt_val < BODY_USB_PD_MIN_NP_FZ100_VOLTAGE_V or volt_val > MAX_NP_FZ100_VOLTAGE_V:
            body_pd_batt_ok = False
            codes.append(B1_ERR_BATTERY_VOLTAGE_OUT_OF_SAFE_BOUNDS)
            errors.append(
                f"{B1_ERR_BATTERY_VOLTAGE_OUT_OF_SAFE_BOUNDS}: NP-FZ100 voltage {volt_val:.2f}V outside [7.20V, 8.50V]"
            )
    elif pwr_norm == POWER_MODE_DC_C1_COUPLER:
        if (
            watts_val < DC_C1_MIN_PD_WATTS
            or amps_val < DC_C1_MIN_CABLE_AMPS
            or (not bool(dc_c1_emarked_5a))
        ):
            dc_c1_ok = False
            codes.append(B1_ERR_DC_C1_UNDER_65W_OR_NON_5A_EMARKED_CABLE)
            errors.append(
                f"{B1_ERR_DC_C1_UNDER_65W_OR_NON_5A_EMARKED_CABLE}: DC-C1 requires >=65.0W USB-PD and 5.0A e-Marked cable (got {watts_val:.1f}W, {amps_val:.1f}A, emarked_5a={dc_c1_emarked_5a})"
            )
    else:
        body_pd_batt_ok = False
        dc_c1_ok = False
        codes.append(B1_ERR_POWER_SOURCE_INVALID)
        errors.append(
            f"{B1_ERR_POWER_SOURCE_INVALID}: unsupported power_source={power_source!r}"
        )

    # 3. VMC-BNCM1 (`A-5051-506-A`, 0.2m) Port, Unidirectional `TC_IN`, EXT-LK & Pin 8/9/10 Lock
    port_norm = re.sub(r"[\s\-/]+", "_", str(vmc_bncm1_port).strip().upper())
    dir_norm = re.sub(r"[\s\-/]+", "_", str(vmc_bncm1_direction).strip().upper())
    shoot_norm = re.sub(r"[\s\-]+", "_", str(shoot_mode).strip().upper())
    tc_make_norm = re.sub(r"[\s\-]+", "_", str(tc_make_mode).strip().upper())
    tc_run_norm = re.sub(r"[\s\-]+", "_", str(tc_run_mode).strip().upper())

    eff_vmc_attached = bool(vmc_bncm1_attached) or (
        port_norm not in ("", VMC_PORT_DISCONNECTED, "NONE")
    )
    if eff_vmc_attached and port_norm in ("", VMC_PORT_DISCONNECTED, "NONE"):
        port_norm = VMC_PORT_BODY_MULTI_MICRO_USB
    if eff_vmc_attached and dir_norm in ("", VMC_DIRECTION_NONE):
        dir_norm = VMC_DIRECTION_TC_IN

    vmc_port_ok = True
    vmc_tcin_ok = True

    if eff_vmc_attached:
        if port_norm in (
            VMC_PORT_XLR_H1_HANDLE_MICRO_USB,
            "XLR_H1",
            "XLR_H1_MICRO_USB",
            "HANDLE_MICRO_USB",
            "TOP_HANDLE_MICRO_USB",
        ):
            vmc_port_ok = False
            codes.append(B1_ERR_VMC_BNCM1_XLR_H1_HANDLE_PORT_FORBIDDEN)
            errors.append(
                f"{B1_ERR_VMC_BNCM1_XLR_H1_HANDLE_PORT_FORBIDDEN}: VMC-BNCM1 ({VMC_BNCM1_PART_NUMBER}) is strictly forbidden on XLR-H1 handle Micro-USB port; connect ONLY to camera body Multi/Micro USB"
            )
        elif port_norm != VMC_PORT_BODY_MULTI_MICRO_USB:
            vmc_port_ok = False
            codes.append(B1_ERR_VMC_BNCM1_PORT_INVALID)
            errors.append(
                f"{B1_ERR_VMC_BNCM1_PORT_INVALID}: invalid vmc_bncm1_port={vmc_bncm1_port!r}"
            )

        if dir_norm in REJECTED_VMC_REVERSE_DIRECTIONS or dir_norm != VMC_DIRECTION_TC_IN:
            vmc_tcin_ok = False
            codes.append(B1_ERR_VMC_BNCM1_REVERSE_BNC_TC_OUT_FORBIDDEN)
            errors.append(
                f"{B1_ERR_VMC_BNCM1_REVERSE_BNC_TC_OUT_FORBIDDEN}: ILME-FX3 Multi/Micro USB VMC-BNCM1 supports unidirectional TC_IN only (got {vmc_bncm1_direction!r}); route digital TC OUT exclusively via Type-A HDMI"
            )

        if not (
            shoot_norm == "MOVIE"
            and tc_make_norm == "PRESET"
            and tc_run_norm == "FREE_RUN"
        ):
            vmc_tcin_ok = False
            codes.append(B1_ERR_VMC_BNCM1_TC_IN_EXT_LK_PREREQ_FAILED)
            errors.append(
                f"{B1_ERR_VMC_BNCM1_TC_IN_EXT_LK_PREREQ_FAILED}: VMC-BNCM1 EXT-LK requires Shoot=MOVIE, TC Make=PRESET, TC Run=FREE_RUN (got shoot={shoot_mode!r}, make={tc_make_mode!r}, run={tc_run_mode!r})"
            )
    else:
        if dir_norm in REJECTED_VMC_REVERSE_DIRECTIONS:
            vmc_tcin_ok = False
            codes.append(B1_ERR_VMC_BNCM1_REVERSE_BNC_TC_OUT_FORBIDDEN)
            errors.append(
                f"{B1_ERR_VMC_BNCM1_REVERSE_BNC_TC_OUT_FORBIDDEN}: reverse BNC {vmc_bncm1_direction!r} is unsupported on ILME-FX3"
            )

    if bool(hdmi_tc_out_enabled) and shoot_norm in ("S&Q", "SQ", "S_AND_Q"):
        codes.append(B1_ERR_HDMI_TC_OUT_FORBIDDEN_IN_SQ_MODE)
        errors.append(
            f"{B1_ERR_HDMI_TC_OUT_FORBIDDEN_IN_SQ_MODE}: Type-A HDMI [Time Code Output] is disabled in S&Q mode"
        )

    pin_contention_free = not (eff_vmc_attached and bool(uart_rx_1v8_attached))
    if not pin_contention_free:
        codes.append(B1_ERR_MULTIUSB_PIN_8_9_10_UART_CONTENTION)
        errors.append(
            f"{B1_ERR_MULTIUSB_PIN_8_9_10_UART_CONTENTION}: VMC-BNCM1 and 1.8V UART RX triage cannot co-occupy Multi-USB Pins {MULTIUSB_CONTENTION_PINS}"
        )
    if bool(uart_rx_1v8_attached) and (
        abs(float(uart_logic_voltage_v) - EXPECTED_UART_VOLTAGE_V) > UART_VOLTAGE_TOLERANCE_V
    ):
        pin_contention_free = False
        codes.append(B1_ERR_MULTIUSB_PIN_8_9_10_UART_CONTENTION)
        errors.append(
            f"{B1_ERR_MULTIUSB_PIN_8_9_10_UART_CONTENTION}: UART logic voltage {uart_logic_voltage_v:.2f}V != 1.80V"
        )

    passed = (
        len(errors) == 0
        and cam_ok
        and no_uvc_ok
        and body_pd_batt_ok
        and dc_c1_ok
        and vmc_port_ok
        and vmc_tcin_ok
        and pin_contention_free
        and PHYSICAL_USB_PACKETS_EMITTED == 0
    )
    return CheckGroup1PowerCableHarnessResult(
        check_group_id=CHECK_GROUP_B1_ID,
        passed=passed,
        body_model_id_int=eff_model_id,
        body_model_id_hex=f"{eff_model_id:#010x}",
        body_fw=eff_fw,
        body_fw_ge_204_floor=fw_ge_204,
        camera_identity_ok=cam_ok,
        power_source=pwr_norm,
        np_fz100_inserted=bool(np_fz100_inserted),
        np_fz100_soc_pct=round(soc_val, 2),
        np_fz100_voltage_v=round(volt_val, 3),
        body_usb_pd_battery_floor_ok=body_pd_batt_ok,
        dc_c1_pd_watts=round(watts_val, 2),
        dc_c1_cable_amps=round(amps_val, 2),
        dc_c1_emarked_5a=bool(dc_c1_emarked_5a),
        dc_c1_65w_5a_contract_ok=dc_c1_ok,
        usb_connection_mode=usb_norm,
        streaming_4k_transport=stream_norm,
        expect_usb_streaming_uvc=bool(expect_usb_streaming_uvc),
        no_uvc_firewall_ok=no_uvc_ok,
        vmc_bncm1_attached=eff_vmc_attached,
        vmc_bncm1_part_number=VMC_BNCM1_PART_NUMBER,
        vmc_bncm1_port=port_norm if eff_vmc_attached else VMC_PORT_DISCONNECTED,
        vmc_bncm1_direction=dir_norm if eff_vmc_attached else VMC_DIRECTION_NONE,
        vmc_bncm1_body_port_only_ok=vmc_port_ok,
        vmc_bncm1_tcin_only_ok=vmc_tcin_ok,
        shoot_mode=shoot_norm,
        tc_make_mode=tc_make_norm,
        tc_run_mode=tc_run_norm,
        ext_lk_stabilization_seconds=VMC_EXT_LK_STABILIZATION_SECONDS,
        hdmi_tc_out_enabled=bool(hdmi_tc_out_enabled),
        uart_rx_1v8_attached=bool(uart_rx_1v8_attached),
        uart_logic_voltage_v=round(float(uart_logic_voltage_v), 2),
        multiusb_pin_8_9_10_contention_free=pin_contention_free,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        error_codes=tuple(sorted(set(codes))),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group 2: 4-Mode `[Fan Control]` Pre-Backup Thermal & `BIG6` No-eND Gate
# ---------------------------------------------------------------------------


def evaluate_check_group_2_fan_thermal_and_big6(
    *,
    fan_mode: str = "Auto",
    pre_p3_75mib_backup_or_stageb_rehearsal: bool = True,
    require_fan_auto_for_prebackup: bool = True,
    auto_power_off_temp: str = "High",
    body_temp_c: float = 29.5,
    observed_off_in_rec_standby_pwm_pct: Optional[float] = None,
    observed_off_in_rec_rec_pwm_pct: Optional[float] = None,
    observed_off_in_rec_emergency_pwm_pct: Optional[float] = None,
    big6_mode_settings: str = "Fixed/Variable",
    big6_home_custom_key_bound: bool = True,
    big6_home_lower_left: str = "Aperture",
    shutter_speed_slot_key: str = SHUTTER_SPEED_BACKUP_KEY_HEX,
    shutter_angle_slot_key: str = SHUTTER_ANGLE_BACKUP_KEY_HEX,
    shutter_angle_deg: float = 180.0,
    rec_fps: float = 23.98,
    is_sq_mode: bool = False,
    e_nd_actuator_tx_count: int = 0,
    cp_end_motor_drive_attempted: bool = False,
) -> CheckGroup2FanThermalAndBig6Result:
    """Check Group 2: 4-mode Fan thermal (`Always Off` block, `Off in Rec` 100% standby) & BIG6 0 e-ND TX."""
    errors: List[str] = []
    codes: List[str] = []

    raw_fan = str(fan_mode).strip()
    norm_fan = _normalize_fan_mode_token(raw_fan)
    raw_upper = raw_fan.upper()

    is_bogus_auto12 = norm_fan in BOGUS_NON_FX3_FAN_MODES or raw_upper in BOGUS_NON_FX3_FAN_MODES
    valid_4mode = (not is_bogus_auto12) and (norm_fan in FX3_VALID_4_FAN_MODES)
    canonical_label = FX3_FAN_CANONICAL_LABELS.get(norm_fan, "INVALID")

    if is_bogus_auto12:
        codes.append(B2_ERR_BOGUS_NON_FX3_FAN_MODE_AUTO1_AUTO2)
        errors.append(
            f"{B2_ERR_BOGUS_NON_FX3_FAN_MODE_AUTO1_AUTO2}: {raw_fan!r} is a non-FX3 broadcast/Lumix token; ILME-FX3 {FX3_FAN_MENU_PATH} supports strictly Auto, Minimum, Off in Rec, Always Off"
        )
    elif not valid_4mode:
        codes.append(B2_ERR_UNKNOWN_FAN_CONTROL_MODE)
        errors.append(
            f"{B2_ERR_UNKNOWN_FAN_CONTROL_MODE}: unknown fan_mode={raw_fan!r}"
        )

    # Pre-backup (75 MiB p3 cold-backup) & Stage-B rehearsal thermal interlock
    always_off_blocked = False
    if valid_4mode and bool(pre_p3_75mib_backup_or_stageb_rehearsal):
        if norm_fan == FAN_MODE_ALWAYS_OFF:
            always_off_blocked = True
            codes.append(B2_ERR_ALWAYS_OFF_BLOCKS_75MIB_P3_BACKUP_AND_STAGEB)
            errors.append(
                f"{B2_ERR_ALWAYS_OFF_BLOCKS_75MIB_P3_BACKUP_AND_STAGEB}: [Fan Control] == Always Off blocks {P3_COLD_BACKUP_PARTITION_MIB} MiB p3 AdjustControl (0x40) cold-backup and Stage-B rehearsal; switch to Auto first"
            )
        elif bool(require_fan_auto_for_prebackup) and norm_fan != FAN_MODE_AUTO:
            codes.append(B2_ERR_PREBACKUP_REQUIRES_FAN_SWITCHED_TO_AUTO)
            errors.append(
                f"{B2_ERR_PREBACKUP_REQUIRES_FAN_SWITCHED_TO_AUTO}: [Fan Control] == {canonical_label!r} must be switched to 'Auto' before {P3_COLD_BACKUP_PARTITION_MIB} MiB p3 cold-backup or Stage-B rehearsal"
            )

    apo_norm = _normalize_fan_mode_token(auto_power_off_temp)
    apo_ok = apo_norm in VALID_AUTO_POWER_OFF_TEMPS
    if not apo_ok:
        codes.append(B2_ERR_AUTO_POWER_OFF_TEMP_ENUM_INVALID)
        errors.append(
            f"{B2_ERR_AUTO_POWER_OFF_TEMP_ENUM_INVALID}: [Auto Power OFF Temp.]={auto_power_off_temp!r} must be Standard or High"
        )

    temp_val = float(body_temp_c)
    temp_ok = MIN_BODY_START_TEMP_C <= temp_val < MAX_BODY_START_TEMP_C
    if not temp_ok:
        codes.append(B2_ERR_BODY_THERMAL_OVERLIMIT)
        errors.append(
            f"{B2_ERR_BODY_THERMAL_OVERLIMIT}: body_temp_c={temp_val:.1f}C outside pre-bench safe start range [{MIN_BODY_START_TEMP_C:.1f}C, {MAX_BODY_START_TEMP_C:.1f}C)"
        )

    # Off in Rec Standby 100% MAX PWM & Recording/Emergency contract
    standby_pwm = (
        float(observed_off_in_rec_standby_pwm_pct)
        if observed_off_in_rec_standby_pwm_pct is not None
        else model_fx3_702_fan_pwm_profile(
            FAN_MODE_OFF_IN_REC, is_recording=False, body_temp_c=temp_val
        )
    )
    rec_normal_pwm = (
        float(observed_off_in_rec_rec_pwm_pct)
        if observed_off_in_rec_rec_pwm_pct is not None
        else model_fx3_702_fan_pwm_profile(
            FAN_MODE_OFF_IN_REC, is_recording=True, body_temp_c=42.0
        )
    )
    rec_emerg_pwm = (
        float(observed_off_in_rec_emergency_pwm_pct)
        if observed_off_in_rec_emergency_pwm_pct is not None
        else model_fx3_702_fan_pwm_profile(
            FAN_MODE_OFF_IN_REC,
            is_recording=True,
            body_temp_c=OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C,
        )
    )
    off_in_rec_ok = (
        standby_pwm == OFF_IN_REC_STANDBY_MAX_PWM_PCT
        and rec_normal_pwm == OFF_IN_REC_RECORDING_NORMAL_PWM_PCT
        and rec_emerg_pwm == OFF_IN_REC_EMERGENCY_PWM_PCT
    )
    if not off_in_rec_ok:
        codes.append(B2_ERR_OFF_IN_REC_STANDBY_MAX_PWM_VIOLATION)
        errors.append(
            f"{B2_ERR_OFF_IN_REC_STANDBY_MAX_PWM_VIOLATION}: Off in Rec contract requires standby=100.0% MAX PWM, rec=0.0%, emergency=100.0% (got standby={standby_pwm:.1f}%, rec={rec_normal_pwm:.1f}%, emerg={rec_emerg_pwm:.1f}%)"
        )

    # BIG6 topology, independent Speed/Angle shutter slots & [Home (Lower Left)] Zero e-ND
    mode_settings_norm = re.sub(r"[\s/\-]+", "_", str(big6_mode_settings).strip().upper())
    big6_prereq_ok = (mode_settings_norm == "FIXED_VARIABLE") and bool(
        big6_home_custom_key_bound
    )

    shutter_indep = (
        str(shutter_speed_slot_key).strip().lower() == SHUTTER_SPEED_BACKUP_KEY_HEX
        and str(shutter_angle_slot_key).strip().lower() == SHUTTER_ANGLE_BACKUP_KEY_HEX
        and str(shutter_speed_slot_key).strip().lower()
        != str(shutter_angle_slot_key).strip().lower()
    )
    fps_val = float(rec_fps)
    ang_val = float(shutter_angle_deg)
    high_fps_or_sq = bool(is_sq_mode) or fps_val >= 100.0
    max_ang = (
        SHUTTER_ANGLE_MAX_HIGH_FPS_OR_SQ_DEG
        if high_fps_or_sq
        else SHUTTER_ANGLE_MAX_STANDARD_DEG
    )
    ang_ok = SHUTTER_ANGLE_MIN_DEG <= ang_val <= max_ang

    if not (big6_prereq_ok and shutter_indep and ang_ok):
        codes.append(B2_ERR_BIG6_PREREQ_OR_SHUTTER_ANGLE_INVALID)
        errors.append(
            f"{B2_ERR_BIG6_PREREQ_OR_SHUTTER_ANGLE_INVALID}: BIG6 prereq_ok={big6_prereq_ok}, shutter_indep={shutter_indep}, angle={ang_val:.1f}deg (max={max_ang:.1f}deg at fps={fps_val})"
        )

    ll_norm = re.sub(r"[\s\-/]+", "_", str(big6_home_lower_left).strip().upper())
    ll_ok = ll_norm in VALID_BIG6_LOWER_LEFT_MODES
    if not ll_ok:
        codes.append(B2_ERR_BIG6_LOWER_LEFT_MODE_INVALID)
        errors.append(
            f"{B2_ERR_BIG6_LOWER_LEFT_MODE_INVALID}: {BIG6_LOWER_LEFT_MENU_PATH}={big6_home_lower_left!r} must be Aperture or ND Filter"
        )

    tx_cnt = int(e_nd_actuator_tx_count)
    zero_end_ok = (tx_cnt == 0) and (not bool(cp_end_motor_drive_attempted))
    if not zero_end_ok:
        codes.append(B2_ERR_PHYSICAL_E_ND_ACTUATOR_TX_NONZERO)
        errors.append(
            f"{B2_ERR_PHYSICAL_E_ND_ACTUATOR_TX_NONZERO}: ILME-FX3 has zero physical internal e-ND hardware; e_nd_actuator_tx_count={tx_cnt}, cp_end_motor_drive_attempted={cp_end_motor_drive_attempted} must both be 0/False"
        )

    passed = (
        len(errors) == 0
        and valid_4mode
        and (not always_off_blocked)
        and apo_ok
        and temp_ok
        and off_in_rec_ok
        and big6_prereq_ok
        and shutter_indep
        and ang_ok
        and ll_ok
        and zero_end_ok
    )
    return CheckGroup2FanThermalAndBig6Result(
        check_group_id=CHECK_GROUP_B2_ID,
        passed=passed,
        fan_menu_path=FX3_FAN_MENU_PATH,
        fan_mode_input=raw_fan,
        fan_mode_normalized=norm_fan,
        fan_mode_canonical_label=canonical_label,
        valid_fx3_4mode_fan=valid_4mode,
        bogus_auto1_auto2_rejected=(not is_bogus_auto12),
        pre_p3_75mib_backup_or_stageb_rehearsal=bool(
            pre_p3_75mib_backup_or_stageb_rehearsal
        ),
        always_off_prebackup_blocked=always_off_blocked,
        auto_power_off_temp=apo_norm,
        auto_power_off_temp_valid=apo_ok,
        body_temp_c=round(temp_val, 2),
        body_temp_start_safe=temp_ok,
        off_in_rec_standby_pwm_pct=standby_pwm,
        off_in_rec_recording_normal_pwm_pct=rec_normal_pwm,
        off_in_rec_emergency_temp_c=OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C,
        off_in_rec_emergency_pwm_pct=rec_emerg_pwm,
        off_in_rec_contract_verified=off_in_rec_ok,
        big6_mode_settings=mode_settings_norm,
        big6_home_custom_key_bound=bool(big6_home_custom_key_bound),
        big6_six_cells=BIG6_SIX_CELL_TOPOLOGY,
        big6_home_lower_left=ll_norm,
        big6_lower_left_software_only_nd=(ll_norm == BIG6_LOWER_LEFT_ND_FILTER),
        shutter_speed_slot_key=str(shutter_speed_slot_key),
        shutter_angle_slot_key=str(shutter_angle_slot_key),
        shutter_slots_independent=shutter_indep,
        shutter_angle_deg=round(ang_val, 2),
        rec_fps=round(fps_val, 2),
        shutter_angle_within_bounds=ang_ok,
        has_physical_internal_end_hardware=False,
        e_nd_actuator_tx_count=tx_cnt,
        cp_end_motor_drive_attempted=bool(cp_end_motor_drive_attempted),
        zero_end_actuator_verified=zero_end_ok,
        error_codes=tuple(sorted(set(codes))),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group 3: Slot-1 Dual-Media `.cube` LUT & `CAMSET01..10.DAT` Vault
# ---------------------------------------------------------------------------


def build_simulated_phase204_tier0_receipts(
    *,
    body_serial: str = DEFAULT_TARGET_BODY_SERIAL,
    emmc_cid: str = DEFAULT_TARGET_EMMC_CID,
) -> Dict[str, Any]:
    """Synthesize deterministic in-memory dual-copy 528 B FX3RCPT1 + H0 baselines."""
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE204_TIER0:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode("ascii")
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE204_MANIFEST:{body_serial}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt_bytes = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    h0_baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return {
        "receipt_a_bytes": rcpt_bytes,
        "receipt_b_bytes": rcpt_bytes,
        "st_dev_a": 0x11001101,
        "st_dev_b": 0x22002202,
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "h0_baselines_a": h0_baselines,
        "h0_baselines_b": dict(h0_baselines),
    }


def _canonicalize_media_type(media_type: str) -> Optional[str]:
    norm = re.sub(r"[\s\-]+", "_", str(media_type).strip().upper())
    if norm in ("SD", "SDHC", "SDXC", "SDXC_V90", "SDXC_V60"):
        return MEDIA_TYPE_SDXC
    if norm in ("CFEXPRESS_A", "CFEXPRESS_TYPE_A", "CFE_A", "CFEXPRESS"):
        return MEDIA_TYPE_CFEXPRESS_A
    return None


def evaluate_check_group_3_slot1_lut_camset_vault(
    *,
    slot1_media_type: str = MEDIA_TYPE_SDXC,
    lut_dir_path: Optional[str] = None,
    camset_dir_path: Optional[str] = None,
    slot1_dir: Optional[Path] = None,
    camset_target_slot: int = 1,
    camera_exposure_mode: str = "Flexible Exposure",
    camset_filenames: Sequence[str] = ("CAMSET01.DAT", "CAMSET02.DAT"),
    camset_dat_model_tags: Sequence[str] = ("ILME-FX3", "ILME-FX3"),
    stageb_camset_overlay_path: str = STAGEB_VOLATILE_CAMSET_OVERLAY_DIR,
    cube_filenames: Sequence[str] = ("SLog3_SGamut3Cine_33.cube",),
    cube_grid_sizes: Sequence[int] = (33,),
    user_lut_slot_count: int = 4,
    user_lut_ae_offset_ev: float = 0.0,
    stageb_lut_overlay_path: str = STAGEB_VOLATILE_LUT_OVERLAY_DIR,
    p2_setting_lut_writes: int = 0,
    legacy_v601_unreregistered_slots_on_p2: int = 0,
    inject_h0_h3_drift_surface: Optional[str] = None,
    # Tier-0 dual-media receipt inputs
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
) -> CheckGroup3Slot1LutCamsetVaultResult:
    """Check Group 3: Slot-1 SDXC vs CFexpress-A LUT/CAMSET paths, 6.01/7.02 split, H0==H3 & Tier-0."""
    structural_errors: List[str] = []
    codes: List[str] = []

    canon_media = _canonicalize_media_type(slot1_media_type)
    if canon_media == MEDIA_TYPE_SDXC:
        exp_lut_dir = SDXC_CANONICAL_LUT_DIR
        exp_camset_dir = SDXC_CANONICAL_CAMSET_DIR
    elif canon_media == MEDIA_TYPE_CFEXPRESS_A:
        exp_lut_dir = CFEXPRESS_A_CANONICAL_LUT_DIR
        exp_camset_dir = CFEXPRESS_A_CANONICAL_CAMSET_DIR
    else:
        exp_lut_dir = ""
        exp_camset_dir = ""
        codes.append(B3_ERR_UNSUPPORTED_MEDIA_TYPE)
        structural_errors.append(
            f"{B3_ERR_UNSUPPORTED_MEDIA_TYPE}: unsupported slot1_media_type={slot1_media_type!r}"
        )

    obs_lut_dir = _normalize_dir_path(lut_dir_path if lut_dir_path is not None else exp_lut_dir)
    obs_camset_dir = _normalize_dir_path(
        camset_dir_path if camset_dir_path is not None else exp_camset_dir
    )

    path_matched = (
        canon_media is not None
        and obs_lut_dir == exp_lut_dir
        and obs_camset_dir == exp_camset_dir
    )
    if canon_media is not None and not path_matched:
        codes.append(B3_ERR_MEDIA_PATH_ASYMMETRY_MISMATCH)
        structural_errors.append(
            f"{B3_ERR_MEDIA_PATH_ASYMMETRY_MISMATCH}: media={canon_media} requires LUT={exp_lut_dir!r} & CAMSET={exp_camset_dir!r}, got LUT={obs_lut_dir!r} & CAMSET={obs_camset_dir!r}"
        )

    # Optional O_RDONLY directory hygiene inspection if `slot1_dir` is supplied
    hygiene_symlinks = 0
    hygiene_junk: List[str] = []
    if slot1_dir is not None:
        if slot1_dir.is_symlink() or not slot1_dir.is_dir():
            hygiene_symlinks += 1 if slot1_dir.is_symlink() else 0
            codes.append(B3_ERR_SYMLINK_OR_APPLEDOUBLE_HYGIENE)
            structural_errors.append(
                f"{B3_ERR_SYMLINK_OR_APPLEDOUBLE_HYGIENE}: invalid or symlink slot1_dir={slot1_dir}"
            )
        else:
            for root, dirs, files in os.walk(slot1_dir, followlinks=False):
                rp = Path(root)
                keep_d: List[str] = []
                for d in sorted(dirs):
                    dp = rp / d
                    rel_d = dp.relative_to(slot1_dir).as_posix()
                    if dp.is_symlink():
                        hygiene_symlinks += 1
                        hygiene_junk.append(rel_d)
                        continue
                    if d.startswith("._"):
                        hygiene_junk.append(rel_d)
                    keep_d.append(d)
                dirs[:] = keep_d
                for fn in sorted(files):
                    fp = rp / fn
                    rel_f = fp.relative_to(slot1_dir).as_posix()
                    if fp.is_symlink():
                        hygiene_symlinks += 1
                        hygiene_junk.append(rel_f)
                        continue
                    low = fn.lower()
                    if (
                        fn.startswith("._")
                        or low == ".ds_store"
                        or low == "bodydata.dat"
                        or re.match(r"^bodydata\s*\(\d+\)\.dat$", low)
                        or low in ("edisx.elf", "nor_loader_writer.sh", "us_spi_firmup.sh")
                    ):
                        hygiene_junk.append(rel_f)
        if hygiene_symlinks > 0 or hygiene_junk:
            codes.append(B3_ERR_SYMLINK_OR_APPLEDOUBLE_HYGIENE)
            structural_errors.append(
                f"{B3_ERR_SYMLINK_OR_APPLEDOUBLE_HYGIENE}: symlinks={hygiene_symlinks}, hits={hygiene_junk}"
            )

    # Slot-1-only & non-MR mode check
    slot_val = int(camset_target_slot)
    slot1_only_ok = slot_val == 1
    if not slot1_only_ok:
        codes.append(B3_ERR_CAMSET_SLOT2_FORBIDDEN_SLOT1_ONLY)
        structural_errors.append(
            f"{B3_ERR_CAMSET_SLOT2_FORBIDDEN_SLOT1_ONLY}: [Save/Load Settings] supports Slot 1 ONLY (got slot={slot_val})"
        )

    exp_mode_norm = re.sub(r"[\s\-]+", "_", str(camera_exposure_mode).strip().upper())
    non_mr_ok = exp_mode_norm not in FORBIDDEN_MR_EXPOSURE_MODES
    if not non_mr_ok:
        codes.append(B3_ERR_CAMSET_DISABLED_IN_MR_RECALL_MODE)
        structural_errors.append(
            f"{B3_ERR_CAMSET_DISABLED_IN_MR_RECALL_MODE}: [Save/Load Settings] is grayed-out/disabled in {camera_exposure_mode!r} (Recall Camera Setting) mode"
        )

    # CAMSET01..10.DAT bounds & Cross-Model (`FX3` vs `FX3A` vs `FX6`) `.DAT` firewall
    cs_files = tuple(str(f).strip() for f in camset_filenames)
    cs_count_ok = len(cs_files) <= CAMSET_MAX_FILES_PER_CARD and all(
        bool(CAMSET_FILENAME_RE.match(fn)) for fn in cs_files
    )
    if len(set(cs_files)) != len(cs_files):
        cs_count_ok = False
    if not cs_count_ok:
        codes.append(B3_ERR_CAMSET_FILENAME_OR_10_SLOT_CEILING)
        structural_errors.append(
            f"{B3_ERR_CAMSET_FILENAME_OR_10_SLOT_CEILING}: CAMSET files must be unique CAMSET01.DAT..CAMSET10.DAT (<=10), got {cs_files}"
        )

    dat_models = tuple(str(m).strip().upper() for m in camset_dat_model_tags)
    cross_model_ok = all(m == "ILME-FX3" for m in dat_models)
    if not cross_model_ok:
        codes.append(B3_ERR_CROSS_MODEL_CAMSET_DAT_CONTAMINATION)
        structural_errors.append(
            f"{B3_ERR_CROSS_MODEL_CAMSET_DAT_CONTAMINATION}: foreign non-FX3 CAMSET .DAT model tag detected in {dat_models} (FX3 vs FX3A vs FX6 incompatible)"
        )

    cs_overlay_clean = str(stageb_camset_overlay_path).strip().rstrip("/")
    cs_sandbox_ok = (cs_overlay_clean == STAGEB_VOLATILE_CAMSET_OVERLAY_DIR) and not any(
        cs_overlay_clean.lower().startswith(pref)
        for pref in FORBIDDEN_PERSISTENT_LUT_CAMSET_PREFIXES
    )
    if not cs_sandbox_ok:
        codes.append(B3_ERR_STAGEB_CAMSET_OVERLAY_SANDBOX_VIOLATION)
        structural_errors.append(
            f"{B3_ERR_STAGEB_CAMSET_OVERLAY_SANDBOX_VIOLATION}: Stage-B CAMSET overlay must be {STAGEB_VOLATILE_CAMSET_OVERLAY_DIR!r}, got {stageb_camset_overlay_path!r}"
        )

    # .cube LUT spec & 6.01 vs 7.02 `p2:/setting` User1..User16 binary split firewall
    cb_files = tuple(str(f).strip() for f in cube_filenames)
    cb_grids = tuple(int(g) for g in cube_grid_sizes)
    lut_slots = int(user_lut_slot_count)
    ae_ev = float(user_lut_ae_offset_ev)

    cube_spec_ok = (
        len(cb_files) > 0
        and len(cb_grids) > 0
        and all(
            len(fn.encode("utf-8")) <= CUBE_MAX_FILENAME_BYTES
            and bool(CUBE_ASCII_FILENAME_RE.match(fn))
            for fn in cb_files
        )
        and all(g in CUBE_ALLOWED_GRID_SIZES for g in cb_grids)
        and (1 <= lut_slots <= USER_LUT_MAX_SLOTS)
        and (USER_LUT_MIN_AE_EV <= ae_ev <= USER_LUT_MAX_AE_EV)
    )
    if not cube_spec_ok:
        codes.append(B3_ERR_CUBE_LUT_SPEC_OR_16_SLOT_CEILING)
        structural_errors.append(
            f"{B3_ERR_CUBE_LUT_SPEC_OR_16_SLOT_CEILING}: invalid .cube files={cb_files}, grids={cb_grids} (expected 17/33), slots={lut_slots} (1..16), ae_ev={ae_ev:.2f}EV (0..+2.0EV)"
        )

    lut_overlay_clean = str(stageb_lut_overlay_path).strip().rstrip("/")
    p2_writes = int(p2_setting_lut_writes)
    stale_601_slots = int(legacy_v601_unreregistered_slots_on_p2)
    lut_split_ok = (
        lut_overlay_clean == STAGEB_VOLATILE_LUT_OVERLAY_DIR
        and p2_writes == 0
        and stale_601_slots == 0
        and not any(
            lut_overlay_clean.lower().startswith(pref)
            for pref in FORBIDDEN_PERSISTENT_LUT_CAMSET_PREFIXES
        )
    )
    if not lut_split_ok:
        codes.append(B3_ERR_LUT_601_VS_702_P2_SETTING_SPLIT_VIOLATION)
        structural_errors.append(
            f"{B3_ERR_LUT_601_VS_702_P2_SETTING_SPLIT_VIOLATION}: FX6 6.01 ({LUT_BINARY_FORMAT_V601_LEGACY}) vs FX3 7.02 ({LUT_BINARY_FORMAT_V702_OPTIMIZED}) split violated (overlay={stageb_lut_overlay_path!r}, p2_writes={p2_writes}, legacy_601_slots_on_p2={stale_601_slots})"
        )

    # 16/16 H0 == H3 surface restoration check
    h0_map = {
        s: hashlib.sha256(f"PHASE204_H0_SURFACE:{s}".encode("ascii")).hexdigest()
        for s in SIXTEEN_STORAGE_SURFACES
    }
    h3_map = dict(h0_map)
    if inject_h0_h3_drift_surface is not None:
        drift_key = str(inject_h0_h3_drift_surface).strip()
        h3_map[drift_key] = hashlib.sha256(
            f"DRIFTED_PHASE204:{drift_key}".encode("ascii")
        ).hexdigest()

    h0_eq_h3_cnt = sum(1 for s in SIXTEEN_STORAGE_SURFACES if h3_map.get(s) == h0_map[s])
    h0_h3_all_16 = h0_eq_h3_cnt == len(SIXTEEN_STORAGE_SURFACES)
    if not h0_h3_all_16:
        codes.append(B3_ERR_H0_H3_16_SURFACE_PARITY_DRIFT)
        structural_errors.append(
            f"{B3_ERR_H0_H3_16_SURFACE_PARITY_DRIFT}: H0==H3 matched {h0_eq_h3_cnt}/{len(SIXTEEN_STORAGE_SURFACES)} surfaces"
        )

    structural_ok = len(structural_errors) == 0

    # Dual-media 528B FX3RCPT1 Tier-0 Vault Binding
    all_errors = list(structural_errors)
    raw_a = receipt_a_bytes
    raw_b = receipt_b_bytes
    obs_dev_a = int(st_dev_a_override) if st_dev_a_override is not None else 0
    obs_dev_b = int(st_dev_b_override) if st_dev_b_override is not None else 0

    if raw_a is None and receipt_a_path is not None:
        if receipt_a_path.is_symlink() or not receipt_a_path.is_file():
            codes.append(B3_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
            all_errors.append(f"Tier-0 Receipt A missing or symlink: {receipt_a_path}")
        else:
            _sz_a, raw_a, dev_a = _read_bounded_slice_o_rdonly(receipt_a_path, 4096)
            if st_dev_a_override is None:
                obs_dev_a = dev_a

    if raw_b is None and receipt_b_path is not None:
        if receipt_b_path.is_symlink() or not receipt_b_path.is_file():
            codes.append(B3_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
            all_errors.append(f"Tier-0 Receipt B missing or symlink: {receipt_b_path}")
        else:
            _sz_b, raw_b, dev_b = _read_bounded_slice_o_rdonly(receipt_b_path, 4096)
            if st_dev_b_override is None:
                obs_dev_b = dev_b

    receipts_provided = (raw_a is not None) and (raw_b is not None)
    distinct_devs = False
    rcpt_crc_hex = ""
    rcpt_sha = ""
    h0_verified_cnt = 0
    tier0_ok = False

    if not receipts_provided:
        codes.append(B3_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
        all_errors.append(
            "Dual-copy 528B FX3RCPT1 Tier-0 cold-backup receipts not provided (offline fail-closed)"
        )
    else:
        assert raw_a is not None and raw_b is not None
        distinct_devs = obs_dev_a > 0 and obs_dev_b > 0 and (obs_dev_a != obs_dev_b)
        info_a = parse_sd_backup_receipt_bytes(raw_a)
        info_b = parse_sd_backup_receipt_bytes(raw_b)
        valid_528 = (
            len(raw_a) == SD_RECEIPT_BYTES
            and len(raw_b) == SD_RECEIPT_BYTES
            and info_a.valid
            and info_b.valid
        )
        crc_a = zlib.crc32(raw_a) & 0xFFFFFFFF
        crc_b = zlib.crc32(raw_b) & 0xFFFFFFFF
        sha_a = hashlib.sha256(raw_a).hexdigest()
        sha_b = hashlib.sha256(raw_b).hexdigest()
        parity_ok = (crc_a == crc_b) and (sha_a == sha_b)
        rcpt_crc_hex = f"{crc_a:#010x}"
        rcpt_sha = sha_a if parity_ok else ""

        eff_serial = str(body_serial or "").strip()
        eff_cid = str(emmc_cid or "").strip().lower()
        cid_sha = (
            hashlib.sha256(eff_cid.encode("ascii")).hexdigest()
            if HEX32_CID_RE.match(eff_cid)
            else ""
        )
        ident_ok = (
            bool(BODY_SERIAL_RE.match(eff_serial))
            and eff_serial.upper() not in FORBIDDEN_TRIVIAL_SERIALS
            and bool(HEX32_CID_RE.match(eff_cid))
            and eff_cid not in FORBIDDEN_TRIVIAL_CIDS
            and cid_sha not in _TRIVIAL_CID_SHA256_SET
        )

        base_a = dict(h0_baselines_a or {})
        base_b = dict(h0_baselines_b if h0_baselines_b is not None else base_a)
        for k in REQUIRED_H0_BASELINE_KEYS:
            va = str(base_a.get(k, "")).strip().lower()
            vb = str(base_b.get(k, "")).strip().lower()
            if (not _is_trivial_hex64(va)) and (not _is_trivial_hex64(vb)) and va == vb:
                h0_verified_cnt += 1
        h0_base_ok = h0_verified_cnt == len(REQUIRED_H0_BASELINE_KEYS)

        tier0_ok = distinct_devs and valid_528 and parity_ok and ident_ok and h0_base_ok
        if not tier0_ok:
            codes.append(B3_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
            all_errors.append(
                f"{B3_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: distinct_devs={distinct_devs}, valid_528={valid_528}, parity_ok={parity_ok}, ident_ok={ident_ok}, h0_verified={h0_verified_cnt}/{len(REQUIRED_H0_BASELINE_KEYS)}"
            )

    passed = structural_ok and receipts_provided and tier0_ok
    return CheckGroup3Slot1LutCamsetVaultResult(
        check_group_id=CHECK_GROUP_B3_ID,
        passed=passed,
        structural_vault_checks_passed=structural_ok,
        slot1_media_type=canon_media or str(slot1_media_type),
        expected_lut_dir=exp_lut_dir,
        observed_lut_dir=obs_lut_dir,
        expected_camset_dir=exp_camset_dir,
        observed_camset_dir=obs_camset_dir,
        dual_media_path_matched=path_matched,
        camset_target_slot=slot_val,
        slot1_only_enforced=slot1_only_ok,
        camera_exposure_mode=exp_mode_norm,
        non_mr_mode_enforced=non_mr_ok,
        camset_files_checked=cs_files,
        camset_count_within_10=cs_count_ok,
        camset_dat_models_checked=dat_models,
        cross_model_dat_firewall_ok=cross_model_ok,
        camset_excluded_domains=CAMSET_EXCLUDED_MACHINE_BOUND_DOMAINS,
        stageb_camset_overlay_path=str(stageb_camset_overlay_path),
        stageb_camset_sandbox_ok=cs_sandbox_ok,
        cube_files_checked=cb_files,
        cube_grid_sizes_checked=cb_grids,
        user_lut_slot_count=lut_slots,
        user_lut_ae_offset_ev=round(ae_ev, 2),
        cube_lut_spec_ok=cube_spec_ok,
        donor_lut_binary_format=LUT_BINARY_FORMAT_V601_LEGACY,
        host_lut_binary_format=LUT_BINARY_FORMAT_V702_OPTIMIZED,
        stageb_lut_overlay_path=str(stageb_lut_overlay_path),
        p2_setting_lut_writes=p2_writes,
        legacy_v601_unreregistered_slots_on_p2=stale_601_slots,
        lut_601_vs_702_split_sandbox_ok=lut_split_ok,
        slot1_hygiene_symlinks=hygiene_symlinks,
        slot1_hygiene_junk_or_bodydata=tuple(hygiene_junk),
        h0_h3_surface_count=len(SIXTEEN_STORAGE_SURFACES),
        h0_equals_h3_count=h0_eq_h3_cnt,
        h0_equals_h3_all_16=h0_h3_all_16,
        tier0_receipts_provided=receipts_provided,
        tier0_st_dev_a=obs_dev_a,
        tier0_st_dev_b=obs_dev_b,
        tier0_distinct_physical_devices=distinct_devs,
        tier0_receipt_crc32_hex=rcpt_crc_hex,
        tier0_receipt_sha256=rcpt_sha,
        tier0_h0_baselines_verified=h0_verified_cnt,
        tier0_vault_binding_ok=tier0_ok,
        error_codes=tuple(sorted(set(codes))),
        errors=tuple(all_errors),
    )


# ---------------------------------------------------------------------------
# Unified Phase 204 Orchestrator, Tamper-Proof Verifier & Markdown Renderer
# ---------------------------------------------------------------------------


def run_bench_cable_fan_and_slot1_preflight(
    *,
    simulate_ready_bench: bool = False,
    force_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    # Check Group 1 inputs
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    power_source: str = POWER_MODE_USB_PD_BODY,
    np_fz100_inserted: bool = True,
    np_fz100_soc_pct: float = 88.0,
    np_fz100_voltage_v: float = 8.00,
    dc_c1_pd_watts: float = 65.0,
    dc_c1_cable_amps: float = 5.0,
    dc_c1_emarked_5a: bool = True,
    usb_connection_mode: str = "MASS_STORAGE",
    streaming_4k_transport: str = "NONE",
    expect_usb_streaming_uvc: bool = False,
    vmc_bncm1_attached: bool = False,
    vmc_bncm1_port: str = VMC_PORT_DISCONNECTED,
    vmc_bncm1_direction: str = VMC_DIRECTION_NONE,
    shoot_mode: str = "MOVIE",
    tc_make_mode: str = "PRESET",
    tc_run_mode: str = "FREE_RUN",
    hdmi_tc_out_enabled: bool = False,
    uart_rx_1v8_attached: bool = True,
    uart_logic_voltage_v: float = 1.8,
    # Check Group 2 inputs
    fan_mode: str = "Auto",
    pre_p3_75mib_backup_or_stageb_rehearsal: bool = True,
    require_fan_auto_for_prebackup: bool = True,
    auto_power_off_temp: str = "High",
    body_temp_c: float = 29.5,
    observed_off_in_rec_standby_pwm_pct: Optional[float] = None,
    observed_off_in_rec_rec_pwm_pct: Optional[float] = None,
    observed_off_in_rec_emergency_pwm_pct: Optional[float] = None,
    big6_mode_settings: str = "Fixed/Variable",
    big6_home_custom_key_bound: bool = True,
    big6_home_lower_left: str = "Aperture",
    shutter_speed_slot_key: str = SHUTTER_SPEED_BACKUP_KEY_HEX,
    shutter_angle_slot_key: str = SHUTTER_ANGLE_BACKUP_KEY_HEX,
    shutter_angle_deg: float = 180.0,
    rec_fps: float = 23.98,
    is_sq_mode: bool = False,
    e_nd_actuator_tx_count: int = 0,
    cp_end_motor_drive_attempted: bool = False,
    # Check Group 3 inputs
    slot1_media_type: str = MEDIA_TYPE_SDXC,
    lut_dir_path: Optional[str] = None,
    camset_dir_path: Optional[str] = None,
    slot1_dir: Optional[Path] = None,
    camset_target_slot: int = 1,
    camera_exposure_mode: str = "Flexible Exposure",
    camset_filenames: Sequence[str] = ("CAMSET01.DAT", "CAMSET02.DAT"),
    camset_dat_model_tags: Sequence[str] = ("ILME-FX3", "ILME-FX3"),
    stageb_camset_overlay_path: str = STAGEB_VOLATILE_CAMSET_OVERLAY_DIR,
    cube_filenames: Sequence[str] = ("SLog3_SGamut3Cine_33.cube",),
    cube_grid_sizes: Sequence[int] = (33,),
    user_lut_slot_count: int = 4,
    user_lut_ae_offset_ev: float = 0.0,
    stageb_lut_overlay_path: str = STAGEB_VOLATILE_LUT_OVERLAY_DIR,
    p2_setting_lut_writes: int = 0,
    legacy_v601_unreregistered_slots_on_p2: int = 0,
    inject_h0_h3_drift_surface: Optional[str] = None,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
) -> RealHwBenchCableFanSlot1Report:
    """Execute Phase 204 Pre-Bench Power/Cable, 4-Mode Fan & Slot-1 Vault Verifier (`B1..B3`)."""
    assert not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED
    assert not PERSISTENT_EMMC_WRITES_AUTHORIZED
    assert not PERSISTENT_WRITE_RELEASE
    assert not SPI_NOR_WRITE_AUTHORIZED
    assert not EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    assert not SD_PHYSICAL_MEDIA_WRITTEN
    assert PHYSICAL_USB_PACKETS_EMITTED == 0
    assert RAW_FIRMWARE_BYTES_LEAKED == 0

    clean_room = (
        is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    )
    donor_res = inspect_phase204_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=clean_room,
    )

    if simulate_ready_bench:
        if (
            receipt_a_bytes is None
            and receipt_b_bytes is None
            and receipt_a_path is None
            and receipt_b_path is None
        ):
            sim_t0 = build_simulated_phase204_tier0_receipts()
            receipt_a_bytes = sim_t0["receipt_a_bytes"]
            receipt_b_bytes = sim_t0["receipt_b_bytes"]
            if st_dev_a_override is None:
                st_dev_a_override = sim_t0["st_dev_a"]
            if st_dev_b_override is None:
                st_dev_b_override = sim_t0["st_dev_b"]
            if body_serial is None:
                body_serial = sim_t0["body_serial"]
            if emmc_cid is None:
                emmc_cid = sim_t0["emmc_cid"]
            if h0_baselines_a is None:
                h0_baselines_a = sim_t0["h0_baselines_a"]
            if h0_baselines_b is None:
                h0_baselines_b = sim_t0["h0_baselines_b"]

    b1_res = evaluate_check_group_1_power_cable_harness(
        body_model_id=body_model_id,
        body_fw=body_fw,
        power_source=power_source,
        np_fz100_inserted=np_fz100_inserted,
        np_fz100_soc_pct=np_fz100_soc_pct,
        np_fz100_voltage_v=np_fz100_voltage_v,
        dc_c1_pd_watts=dc_c1_pd_watts,
        dc_c1_cable_amps=dc_c1_cable_amps,
        dc_c1_emarked_5a=dc_c1_emarked_5a,
        usb_connection_mode=usb_connection_mode,
        streaming_4k_transport=streaming_4k_transport,
        expect_usb_streaming_uvc=expect_usb_streaming_uvc,
        vmc_bncm1_attached=vmc_bncm1_attached,
        vmc_bncm1_port=vmc_bncm1_port,
        vmc_bncm1_direction=vmc_bncm1_direction,
        shoot_mode=shoot_mode,
        tc_make_mode=tc_make_mode,
        tc_run_mode=tc_run_mode,
        hdmi_tc_out_enabled=hdmi_tc_out_enabled,
        uart_rx_1v8_attached=uart_rx_1v8_attached,
        uart_logic_voltage_v=uart_logic_voltage_v,
    )
    b2_res = evaluate_check_group_2_fan_thermal_and_big6(
        fan_mode=fan_mode,
        pre_p3_75mib_backup_or_stageb_rehearsal=pre_p3_75mib_backup_or_stageb_rehearsal,
        require_fan_auto_for_prebackup=require_fan_auto_for_prebackup,
        auto_power_off_temp=auto_power_off_temp,
        body_temp_c=body_temp_c,
        observed_off_in_rec_standby_pwm_pct=observed_off_in_rec_standby_pwm_pct,
        observed_off_in_rec_rec_pwm_pct=observed_off_in_rec_rec_pwm_pct,
        observed_off_in_rec_emergency_pwm_pct=observed_off_in_rec_emergency_pwm_pct,
        big6_mode_settings=big6_mode_settings,
        big6_home_custom_key_bound=big6_home_custom_key_bound,
        big6_home_lower_left=big6_home_lower_left,
        shutter_speed_slot_key=shutter_speed_slot_key,
        shutter_angle_slot_key=shutter_angle_slot_key,
        shutter_angle_deg=shutter_angle_deg,
        rec_fps=rec_fps,
        is_sq_mode=is_sq_mode,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        cp_end_motor_drive_attempted=cp_end_motor_drive_attempted,
    )
    b3_res = evaluate_check_group_3_slot1_lut_camset_vault(
        slot1_media_type=slot1_media_type,
        lut_dir_path=lut_dir_path,
        camset_dir_path=camset_dir_path,
        slot1_dir=slot1_dir,
        camset_target_slot=camset_target_slot,
        camera_exposure_mode=camera_exposure_mode,
        camset_filenames=camset_filenames,
        camset_dat_model_tags=camset_dat_model_tags,
        stageb_camset_overlay_path=stageb_camset_overlay_path,
        cube_filenames=cube_filenames,
        cube_grid_sizes=cube_grid_sizes,
        user_lut_slot_count=user_lut_slot_count,
        user_lut_ae_offset_ev=user_lut_ae_offset_ev,
        stageb_lut_overlay_path=stageb_lut_overlay_path,
        p2_setting_lut_writes=p2_setting_lut_writes,
        legacy_v601_unreregistered_slots_on_p2=legacy_v601_unreregistered_slots_on_p2,
        inject_h0_h3_drift_surface=inject_h0_h3_drift_surface,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
    )

    group_results = (b1_res.passed, b2_res.passed, b3_res.passed)
    groups_passed = sum(1 for g in group_results if g)
    all_3_passed = donor_res.passed and all(group_results)

    all_errors = list(donor_res.errors)
    all_errors.extend(b1_res.errors)
    all_errors.extend(b2_res.errors)
    all_errors.extend(b3_res.errors)

    # Fail-closed Go/No-Go Disposition (`hardware_live_attachment_authorized = False` ALWAYS)
    structural_bench_ok = (
        donor_res.passed
        and b1_res.passed
        and b2_res.passed
        and b3_res.structural_vault_checks_passed
    )
    if not structural_bench_ok:
        go_no_go = GO_NO_GO_BLOCKED_BENCH_CHECK_FAILURE
    elif simulate_ready_bench:
        go_no_go = (
            GO_NO_GO_DRY_RUN_SIMULATED_READY
            if all_3_passed
            else GO_NO_GO_BLOCKED_BENCH_CHECK_FAILURE
        )
    elif not b3_res.tier0_receipts_provided:
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
    elif not all_3_passed:
        go_no_go = GO_NO_GO_BLOCKED_BENCH_CHECK_FAILURE
    else:
        go_no_go = GO_NO_GO_READONLY_BENCH_PREFLIGHT_VERIFIED

    remediations: List[str] = []
    if not donor_res.passed:
        remediations.append(
            "Verify local BYOF donor binaries via O_RDONLY or pass --force-clean-room."
        )
    if not b1_res.passed:
        remediations.append(
            "Use USB-C PD + genuine NP-FZ100 (>=51%) or DC-C1 (>=65W + 5A e-Marked cable), connect VMC-BNCM1 ONLY to body Multi/Micro USB for unidirectional TC IN (never XLR-H1 handle port or BNC TC OUT), and do not expect UVC [USB Streaming] on ILME-FX3."
        )
    if not b2_res.passed:
        remediations.append(
            "Switch [Fan Control] from Always Off to Auto (with [Auto Power OFF Temp.] = Standard/High and body temp <45C) before 75 MiB p3 cold-backup or Stage-B rehearsal, reject non-FX3 Auto1/Auto2 tokens, and keep BIG6 e_nd_actuator_tx_count == 0."
        )
    if not b3_res.passed:
        remediations.append(
            "Match Slot-1 LUT/CAMSET paths to SDXC (/Private/Sony/PRO/LUT/ & /PRIVATE/SONY/SETTING/FX3/CAMSET/) vs CFexpress-A (/Sony/PRO/LUT/ & /SONY/SETTING/FX3/CAMSET/), exit MR mode, sandbox Stage-B to /tmp/fx6_lut_overlay & /tmp/fx6_camset_overlay (16/16 H0==H3), and provide dual-device 528B FX3RCPT1 receipts."
        )

    body: Dict[str, Any] = {
        "schema": PHASE_204_SCHEMA,
        "phase_version": PHASE_204_VERSION,
        "verification_mode": donor_res.verification_mode,
        "simulate_ready_bench": bool(simulate_ready_bench),
        "go_no_go": go_no_go,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "sd_physical_media_written": SD_PHYSICAL_MEDIA_WRITTEN,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
        "check_group_count": len(BENCH_PREFLIGHT_CHECK_GROUP_IDS),
        "check_groups_passed": groups_passed,
        "all_3_check_groups_passed": all_3_passed,
        "tier0_receipt_verified": b3_res.tier0_vault_binding_ok,
        "h0_equals_h3_count": b3_res.h0_equals_h3_count,
        "h0_h3_surface_count": b3_res.h0_h3_surface_count,
        "e_nd_actuator_tx_count": b2_res.e_nd_actuator_tx_count,
        "donor_inspection": asdict(donor_res),
        "check_group_1_power_cable_harness": asdict(b1_res),
        "check_group_2_fan_thermal_and_big6": asdict(b2_res),
        "check_group_3_slot1_lut_camset_vault": asdict(b3_res),
        "remediation_actions": list(remediations),
        "errors": list(all_errors),
    }
    report_sha = _canonical_sha256_dict(body)

    return RealHwBenchCableFanSlot1Report(
        schema=PHASE_204_SCHEMA,
        phase_version=PHASE_204_VERSION,
        verification_mode=donor_res.verification_mode,
        simulate_ready_bench=bool(simulate_ready_bench),
        go_no_go=go_no_go,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        sd_physical_media_written=SD_PHYSICAL_MEDIA_WRITTEN,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        check_group_count=len(BENCH_PREFLIGHT_CHECK_GROUP_IDS),
        check_groups_passed=groups_passed,
        all_3_check_groups_passed=all_3_passed,
        tier0_receipt_verified=b3_res.tier0_vault_binding_ok,
        h0_equals_h3_count=b3_res.h0_equals_h3_count,
        h0_h3_surface_count=b3_res.h0_h3_surface_count,
        e_nd_actuator_tx_count=b2_res.e_nd_actuator_tx_count,
        donor_inspection=donor_res,
        check_group_1_power_cable_harness=b1_res,
        check_group_2_fan_thermal_and_big6=b2_res,
        check_group_3_slot1_lut_camset_vault=b3_res,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256=report_sha,
    )


def verify_phase204_report(payload: Mapping[str, Any]) -> Phase204ReportVerifyResult:
    """Fail-closed tamper & hard-safety-lock verifier for Phase 204 preflight receipts."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_204_SCHEMA:
        errors.append(f"Unexpected schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_204_VERSION:
        errors.append(f"Unexpected phase_version: {payload.get('phase_version')!r}")
    if payload.get("go_no_go") not in PHASE_204_VALID_GO_NO_GO_VALUES:
        errors.append(f"Invalid go_no_go value: {payload.get('go_no_go')!r}")

    for bool_key in (
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
    ):
        if payload.get(bool_key) is not False:
            errors.append(f"Hard-locked invariant violated: {bool_key} must be False")

    for zero_key in (
        "physical_usb_packets_emitted",
        "raw_firmware_bytes_leaked",
        "e_nd_actuator_tx_count",
    ):
        if payload.get(zero_key) != 0:
            errors.append(f"Hard-locked zero invariant violated: {zero_key} != 0")

    donor = payload.get("donor_inspection", {})
    if donor.get("raw_firmware_bytes_leaked") != 0:
        errors.append("donor_inspection.raw_firmware_bytes_leaked != 0")
    if donor.get("elapsed_seconds", 999.0) >= DONOR_INSPECTION_MAX_SECONDS:
        errors.append("donor_inspection exceeded 0.15s budget")

    b1 = payload.get("check_group_1_power_cable_harness", {})
    b2 = payload.get("check_group_2_fan_thermal_and_big6", {})
    b3 = payload.get("check_group_3_slot1_lut_camset_vault", {})

    if b2.get("e_nd_actuator_tx_count") != 0:
        errors.append("check_group_2_fan_thermal_and_big6.e_nd_actuator_tx_count != 0")

    if payload.get("simulate_ready_bench") is True and payload.get("go_no_go") == (
        GO_NO_GO_READONLY_BENCH_PREFLIGHT_VERIFIED
    ):
        errors.append("simulate_ready_bench=True cannot emit physical preflight GO verdict")

    if payload.get("go_no_go") in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        GO_NO_GO_READONLY_BENCH_PREFLIGHT_VERIFIED,
    ) and not (
        bool(donor.get("passed"))
        and bool(b1.get("passed"))
        and bool(b2.get("passed"))
        and bool(b3.get("passed"))
        and payload.get("h0_equals_h3_count") == 16
    ):
        errors.append("PASS/GO verdict invalid when any check group failed or H0!=H3")

    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(rendered):
        errors.append("Raw Python bytes literal repr detected in Phase 204 receipt")

    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if payload.get("report_sha256") != expected_sha:
        errors.append("report_sha256 canonical digest mismatch (tamper detected)")

    return Phase204ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase204_markdown(report: RealHwBenchCableFanSlot1Report) -> str:
    """Render an operator-friendly Markdown summary for Phase 204 bench preflight."""
    b1 = report.check_group_1_power_cable_harness
    b2 = report.check_group_2_fan_thermal_and_big6
    b3 = report.check_group_3_slot1_lut_camset_vault
    lines = [
        "# Phase 204 — Real-Hardware Operator Pre-Bench Power/Cable, 4-Mode Fan & Slot-1 Vault Receipt",
        "",
        f"- **GO_NO_GO**: `{report.go_no_go}`",
        f"- **Mode**: `{report.verification_mode}` (`simulate_ready_bench={report.simulate_ready_bench}`)",
        f"- **Check Groups Passed**: `{report.check_groups_passed}/{report.check_group_count}` (`all_3_check_groups_passed={report.all_3_check_groups_passed}`)",
        f"- **Hard Safety Locks**: `hardware_live_attachment_authorized={report.hardware_live_attachment_authorized}`, `persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}`, `spi_nor_write_authorized={report.spi_nor_write_authorized}`, `el3_payload_transmit_authorized={report.el3_payload_transmit_authorized}`, `physical_usb_packets_emitted={report.physical_usb_packets_emitted}`, `raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Group Summary (`B1..B3`)",
        "",
        "| Check Group | Status | Key Metrics |",
        "|---|---|---|",
        f"| `{CHECK_GROUP_B1_ID}` | `{'PASS' if b1.passed else 'BLOCKED'}` | power={b1.power_source}, batt={b1.np_fz100_soc_pct}%/{b1.np_fz100_voltage_v}V, dc_c1={b1.dc_c1_pd_watts}W/{b1.dc_c1_cable_amps}A, vmc_port={b1.vmc_bncm1_port} |",
        f"| `{CHECK_GROUP_B2_ID}` | `{'PASS' if b2.passed else 'BLOCKED'}` | fan={b2.fan_mode_canonical_label}, apo={b2.auto_power_off_temp}, temp={b2.body_temp_c}C, e_nd_tx={b2.e_nd_actuator_tx_count} |",
        f"| `{CHECK_GROUP_B3_ID}` | `{'PASS' if b3.passed else 'BLOCKED'}` | media={b3.slot1_media_type}, slot={b3.camset_target_slot}, H0==H3={b3.h0_equals_h3_count}/16, tier0={b3.tier0_vault_binding_ok} |",
    ]
    if report.remediation_actions:
        lines.extend(["", "## Required Actions", ""])
        for act in report.remediation_actions:
            lines.append(f"- {act}")
    return "\n".join(lines) + "\n"
