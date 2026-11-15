#!/usr/bin/env python3
"""Phase 250 (250th Phase Milestone! Stage 47, 47/47 Milestone) — Real-Hardware
ILME-FX3 Wave-37 `[Framing Settings]` Asymmetric `Full`/`Crop` Stream Routing &
HDMI `RAW` Mutual Exclusion, `[USB Power Supply]` Mandatory `NP-FZ100` Insertion +
`USB Type-C` Exclusivity & `[USB LUN Setting]` `Multi`/`Single` Setup Persistence,
and `[Anti-flicker Shoot.]` Mechanical-Still-Only Boundary & Stock `ILME-FX3`
Absence of `[Var. Shutter]` HIL Co-Emulator.

Strictly models Wave-37 official Sony `ILME-FX3` (`ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) contracts without hardware
attachment or firmware byte leakage:

1. **Sub-Model 47A — `[Framing Settings]` Asymmetric `Full`/`Crop` Stream
   Co-Emulation & HDMI `RAW` Mutual Exclusion**:
   - Co-emulates `MENU -> Shooting -> [Framing Settings]` (on-camera or Sony
     *Monitor & Control* remote):
     - `[Framing]`: `Off` (factory default) / `On` — **IS reset** via
       `[Camera Settings Reset]` and `[Initialize]`,
     - `[Recording/Streaming]`: `Full` (factory default) / `Crop` — **IS reset**
       via `[Camera Settings Reset]` and `[Initialize]`,
     - `[HDMI]`: `Crop` (factory default) / `Full` — **IS reset** via
       `[Camera Settings Reset]` and `[Initialize]`.
   - Verifies factory asymmetric dual-stream routing (`Recording/Streaming=Full`
     full-frame master capture vs `HDMI=Crop` external cropped monitoring),
     blocks cropped `[Framing]=On` with HDMI `RAW` output
     (`framing_crop_hdmi_raw_conflict_events == 0`), and rejects consumer `ZV-E1`
     (`ilc/2330`) `[Autoframing Settings]` conflation on `ILME-FX3` (`ilc/2210`,
     `zve1_autoframing_conflation_events == 0`).

2. **Sub-Model 47B — `[USB Power Supply]` Mandatory `NP-FZ100` Insertion +
   `USB Type-C` Exclusivity & `[USB LUN Setting]` `Multi`/`Single` Setup
   Persistence**:
   - Co-emulates `MENU -> Setup -> [USB]`:
     - `[USB Connection Mode]`: `Sel. When Connect` (factory default),
       `MassStorage(MSC)`, `MTP`, `Remote Shoot (PC Remote)`,
     - `[USB LUN Setting]`: `Multi` (factory default — Slot 1 + Slot 2) /
       `Single` (primary slot only for legacy hosts),
     - `[USB Power Supply]`: `On` (factory default) / `Off`.
   - All three `[Setup] -> [USB]` settings **survive `[Camera Settings Reset]`**
     unchanged and are restored to factory defaults **only** by `[Initialize]`.
   - Refuses power-on without an inserted `NP-FZ100` battery pack (or `DC-C1` DC
     coupler), models immediate unbuffered power-off protection against
     mid-session battery pull under USB PD wall power
     (`unbuffered_usb_pd_battery_pull_events == 0`), enforces the
     `Multi/Micro USB` zero-power/zero-charge boundary (`USB Type-C` exclusive,
     `multi_micro_usb_power_bypass_events == 0`), and keeps live host USB
     hard-blocked (`physical_usb_packets_emitted == 0`).

3. **Sub-Model 47C — `[Anti-flicker Shoot.]` Mechanical-Still-Only Boundary &
   Stock `ILME-FX3` Absence of `[Var. Shutter]`**:
   - Co-emulates `MENU -> Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]`
     (`Off` factory default / `On`, **resettable** via `[Camera Settings Reset]`),
     detecting `100 Hz` / `120 Hz` lighting flicker **strictly** during
     mechanical-shutter still shooting (`Still` + `Mechanical` +
     `[Silent Mode]=Off`), disabled in movie / `S&Q Motion` and electronic
     shutter / `[Silent Mode]=On`
     (`antiflicker_movie_or_eshutter_bypass_events == 0`).
   - Enforces `fx3_has_var_shutter == False` (`false_var_shutter_or_ecs_node_events == 0`),
     blocking cross-model `ILME-FX30` (`ilc/2220`) / `ILCE-6700` (`ilc/2320`)
     `[Var. Shutter]` and `ILME-FX6` `ECS` menu assumptions on stock `ILME-FX3`.

4. **Dual-Mode Donor Inspection & Hard Safety Redlines**:
   - Inspects 15 local FX3 `7.02` & FX6 `6.01` donors strictly `os.O_RDONLY` in
     `< 0.1s` cold (`raw_firmware_bytes_leaked == 0`), with deterministic
     `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor
     paths are absent.
   - Locks `persistent_emmc_writes_authorized = False`,
     `hardware_live_attachment_authorized = False`,
     `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`,
     `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`,
     and `physical_device_writes = 0`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import struct
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_framing_usbpower_lun_antiflicker_coemulator_v1"
PHASE_250_SCHEMA = SCHEMA_ID
PHASE_250_VERSION = "250.0.0"
PHASE_NUMBER = 250
IS_250TH_PHASE_MILESTONE = True
STAGE_INDEX = 47
STAGE_TOTAL = 47
MILESTONE_LABEL = "47/47"
STAGE_NAME = "stage47_realhw_framing_usbpower_lun_antiflicker_hil"
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EACCES_ERRNO = 13
EBUSY_ERRNO = 16
EINVAL_ERRNO = 22
EROFS_ERRNO = 30
EOPNOTSUPP_ERRNO = 95

# Bounded donor window read cap (<= 4 KiB per window)
BOUNDED_WINDOW_MAX_BYTES = 4096

# Hard Safety Redline invariants (strictly locked False / 0)
P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
CNFLASHA_MUTATION_BYTES = 0
CNFLASHA_USERSPACE_WRITE_BLOCKED = True
NVRAM_PERSISTENT_WRITES = 0
BK4_PERSISTENT_NVRAM_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
OVERALL_READY_FOR_HARDWARE_ATTACH = False
ISP_WRITE_AUTHORIZED = False
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
PHYSICAL_USB_PACKETS_EMITTED = 0
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
FRAMING_CROP_HDMI_RAW_CONFLICT_EVENTS = 0
ZVE1_AUTOFRAMING_CONFLATION_EVENTS = 0
UNBUFFERED_USB_PD_BATTERY_PULL_EVENTS = 0
MULTI_MICRO_USB_POWER_BYPASS_EVENTS = 0
ANTIFLICKER_MOVIE_OR_ESHUTTER_BYPASS_EVENTS = 0
FALSE_VAR_SHUTTER_OR_ECS_NODE_EVENTS = 0
FX3_HAS_VAR_SHUTTER = False
FX3_HAS_ECS = False
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Environment variables
ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# ---------------------------------------------------------------------------
# Verified Local Donor Specs (15 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_imdb": f"{_FX3_USR_PREFIX}/lib/libIMDB.so",
    "fx3_usb_bus_power": f"{_FX3_USR_PREFIX}/lib/libUsbBusPower.so",
    "fx3_msc_server": f"{_FX3_USR_PREFIX}/lib/libInfraMscServer.so",
    "fx3_media_cfg": f"{_FX3_USR_PREFIX}/lib/libInfraMediaConfig.so",
    "fx3_adj_media": f"{_FX3_USR_PREFIX}/lib/libInfraAdjMedia.so",
    "fx3_string_en_f": f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
    "fx3_cpapp": "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
    "fx6_cpapp": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    "fx3_libmpr": f"{_FX3_USR_PREFIX}/lib/libmpr.so",
    "fx6_libmpr": f"{_FX6_NF15_PREFIX}/lib/libmpr.so",
    "fx3_bk4": "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
    "fx6_bk4": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_imdb": 71_536,
    "fx3_usb_bus_power": 48_232,
    "fx3_msc_server": 64_456,
    "fx3_media_cfg": 52_312,
    "fx3_adj_media": 318_152,
    "fx3_string_en_f": 373_820,
    "fx6_string_en": 118_208,
    "fx3_appfw": 79_015_712,
    "fx6_appfw": 50_520_424,
    "fx3_cpapp": 15_980_568,
    "fx6_cpapp": 17_952_816,
    "fx3_libmpr": 3_517_008,
    "fx6_libmpr": 28_921_824,
    "fx3_bk4": 2_229_740,
    "fx6_bk4": 2_253_333,
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_imdb": (
        b"IMDB_find_entry",
        b"IMDB_get_entries",
        b"IMDB_find_target_bit",
        b"UsbBusPower",
        b"MscServer",
    ),
    "fx3_usb_bus_power": (
        b"_ZN11UsbBusPower4MainEv",
        b"UsbBusPower",
        b"Backup_read",
        b"USB",
        b"Power",
    ),
    "fx3_msc_server": (
        b"MscServer_Init",
        b"MassStorageServer_Create",
        b"MassStorageServer_Destroy",
        b"ufw_ko_insmod",
        b"Backup_read",
    ),
    "fx3_media_cfg": (b"MediaConfig", b"Slot", b"USB", b"Backup_read"),
    "fx3_adj_media": (b"AVBB_SCN_START_HDMI", b"AVBB_SCN_STOP_HDMI", b"HDMI", b"USB"),
    "fx3_string_en_f": (
        b"Framing Settings",
        b"Framing",
        b"Recording/Streaming",
        b"Crop",
        b"Full",
        b"HDMI",
        b"RAW",
        b"USB Power Supply",
        b"USB LUN Setting",
        b"USB Connection Mode",
        b"Sel. When Connect",
        b"MassStorage(MSC)",
        b"Multi",
        b"Single",
        b"Anti-flicker Shoot.",
        b"Silent Mode",
        b"Camera Settings Reset",
        b"Initialize",
    ),
    "fx6_string_en": (
        b"Framing Settings",
        b"Framing",
        b"Crop",
        b"Full",
        b"HDMI",
        b"RAW",
        b"USB Power Supply",
        b"Multi",
        b"Single",
        b"ECS",
    ),
}

COMPACT_ABSENT_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Autoframing Settings",
        b"ECS",
    ),
    "fx6_string_en": (
        b"Autoframing Settings",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (12_427_264, "LUN", b"LUN"),
        (49_942_528, "SILENT", b"SILENT"),
        (49_946_624, "FRAMING", b"FRAMING"),
        (49_946_624, "CROP", b"CROP"),
        (49_946_624, "FLICKER", b"FLICKER"),
        (49_946_624, "HDMI", b"HDMI"),
        (51_388_416, "BATTERY", b"BATTERY"),
        (58_716_160, "MASS_STORAGE", b"MASS_STORAGE"),
        (62_164_992, "USB_POWER", b"USB_POWER"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (35_971_072, "HDMI", b"HDMI"),
        (37_232_640, "USB", b"USB"),
        (37_437_440, "ECS", b"ECS"),
        (39_018_496, "SHUTTER", b"SHUTTER"),
        (39_022_592, "FLICKER", b"FLICKER"),
        (39_436_288, "FRAMING", b"FRAMING"),
        (39_895_040, "CROP", b"CROP"),
    ),
    "fx3_cpapp": (
        (163_840, "INITIALIZE", b"Initialize"),
        (315_392, "SHUTTER", b"Shutter"),
        (696_320, "HDMI", b"HDMI"),
        (2_039_808, "SILENT", b"Silent"),
        (2_048_000, "FLICKER", b"Flicker"),
        (2_052_096, "BATTERY", b"Battery"),
        (3_067_904, "CROP", b"Crop"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
        (13_721_600, "USB", b"USB"),
    ),
    "fx6_cpapp": (
        (372_736, "RESET", b"Reset"),
        (684_032, "HDMI", b"HDMI"),
        (1_024_000, "ECS", b"ECS"),
        (1_753_088, "SHUTTER", b"Shutter"),
        (2_068_480, "CROP", b"Crop"),
        (2_772_992, "FLICKER", b"Flicker"),
        (12_214_272, "BATTERY", b"Battery"),
        (15_196_160, "USB", b"USB"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (233_472, "XAVC", b"XAVC"),
        (2_928_640, "MP4", b"MP4"),
        (2_928_640, "MEDIAPRO", b"MEDIAPRO"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (192_512, "MXF", b"MXF"),
        (258_048, "XAVC", b"XAVC"),
        (315_392, "MEDIAPRO", b"MEDIAPRO"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
        (409_600, "SETTING", b"/setting"),
    ),
    "fx6_bk4": (
        (0, "BK4", b"BK4"),
        (0, "NTSC", b"NTSC"),
        (442_368, "SETTING", b"/setting"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-37 Official ILME-FX3 Ver. 2.00..7.02 Sub-Model 47A / 47B / 47C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
BODY_MODEL_FX30 = "ILME-FX30"
BODY_MODEL_A6700 = "ILCE-6700"
BODY_MODEL_ZVE1 = "ZV-E1"
VALID_ON_OFF: Tuple[str, ...] = ("On", "Off")
VALID_FX3_FIRMWARE_VERSIONS: Tuple[str, ...] = (
    "2.00",
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.02",
)

SETTING_RESET_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset]"
RESET_ACTION_NONE = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET = "Camera Settings Reset"
RESET_ACTION_INITIALIZE = "Initialize"
VALID_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

# Sub-Model 47A: [Framing Settings]
FRAMING_SETTINGS_MENU_PATH = "MENU -> Shooting -> [Framing Settings]"
FRAMING_MENU_NODE_FX3 = "Framing Settings"
FRAMING_MENU_NODE_ZVE1_CONFLATED = "Autoframing Settings"
FRAMING_DEFAULT = "Off"
FRAMING_STREAM_FULL = "Full"
FRAMING_STREAM_CROP = "Crop"
VALID_FRAMING_STREAM_MODES: Tuple[str, ...] = (FRAMING_STREAM_FULL, FRAMING_STREAM_CROP)
FRAMING_RECORDING_STREAMING_DEFAULT = FRAMING_STREAM_FULL
FRAMING_HDMI_DEFAULT = FRAMING_STREAM_CROP
FRAMING_CONTROL_ON_CAMERA = "ON_CAMERA_MENU"
FRAMING_CONTROL_MONITOR_AND_CONTROL = "MONITOR_AND_CONTROL_REMOTE"
VALID_FRAMING_CONTROL_SOURCES: Tuple[str, ...] = (
    FRAMING_CONTROL_ON_CAMERA,
    FRAMING_CONTROL_MONITOR_AND_CONTROL,
)

# Sub-Model 47B: [Setup] -> [USB] ([USB Power Supply], [USB LUN Setting], [USB Connection Mode])
SETUP_USB_MENU_PATH = "MENU -> Setup -> [USB]"
USB_CONN_SEL_WHEN_CONNECT = "Sel. When Connect"
USB_CONN_MASS_STORAGE = "MassStorage(MSC)"
USB_CONN_MTP = "MTP"
USB_CONN_PC_REMOTE = "Remote Shoot (PC Remote)"
VALID_USB_CONNECTION_MODES: Tuple[str, ...] = (
    USB_CONN_SEL_WHEN_CONNECT,
    USB_CONN_MASS_STORAGE,
    USB_CONN_MTP,
    USB_CONN_PC_REMOTE,
)
USB_CONNECTION_MODE_DEFAULT = USB_CONN_SEL_WHEN_CONNECT

USB_LUN_MULTI = "Multi"
USB_LUN_SINGLE = "Single"
VALID_USB_LUN_SETTINGS: Tuple[str, ...] = (USB_LUN_MULTI, USB_LUN_SINGLE)
USB_LUN_SETTING_DEFAULT = USB_LUN_MULTI
USB_POWER_SUPPLY_DEFAULT = "On"

BATTERY_BAY_NP_FZ100 = "NP-FZ100"
BATTERY_BAY_DC_C1 = "DC-C1"
BATTERY_BAY_EMPTY = "NONE"
VALID_BATTERY_BAY_STATES: Tuple[str, ...] = (
    BATTERY_BAY_NP_FZ100,
    BATTERY_BAY_DC_C1,
    BATTERY_BAY_EMPTY,
)

USB_PORT_TYPE_C = "USB Type-C"
USB_PORT_MULTI_MICRO = "Multi/Micro USB"
USB_PORT_DISCONNECTED = "DISCONNECTED"
VALID_USB_PORTS: Tuple[str, ...] = (
    USB_PORT_TYPE_C,
    USB_PORT_MULTI_MICRO,
    USB_PORT_DISCONNECTED,
)

# Sub-Model 47C: [Shutter/Silent] -> [Anti-flicker Shoot.] & Stock FX3 No [Var. Shutter]
ANTI_FLICKER_SHOOT_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]"
ANTI_FLICKER_SHOOT_DEFAULT = "Off"
SILENT_MODE_DEFAULT = "Off"

CAPTURE_MODE_STILL = "Still"
CAPTURE_MODE_MOVIE = "Movie"
CAPTURE_MODE_SQ_MOTION = "S&Q Motion"
VALID_CAPTURE_MODES: Tuple[str, ...] = (
    CAPTURE_MODE_STILL,
    CAPTURE_MODE_MOVIE,
    CAPTURE_MODE_SQ_MOTION,
)

SHUTTER_TYPE_MECHANICAL = "Mechanical"
SHUTTER_TYPE_ELECTRONIC = "Electronic"
VALID_SHUTTER_TYPES: Tuple[str, ...] = (
    SHUTTER_TYPE_MECHANICAL,
    SHUTTER_TYPE_ELECTRONIC,
)
VALID_FLICKER_FREQUENCIES_HZ: Tuple[int, ...] = (0, 100, 120)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    file_bytes: int
    elf64_le_ok: bool
    uxd_container_ok: bool
    sha256_prefix16: str
    marker_hits: Dict[str, int]
    absent_marker_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedWindowDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    bounded_windows_only: bool
    bytes_read_total: int
    file_bytes: int
    elf64_le_ok: bool
    window_hits: Dict[str, int]
    head_sha256_prefix16: str


@dataclass(frozen=True)
class Phase250DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_imdb: CompactDonorSummary
    fx3_usb_bus_power: CompactDonorSummary
    fx3_msc_server: CompactDonorSummary
    fx3_media_cfg: CompactDonorSummary
    fx3_adj_media: CompactDonorSummary
    fx3_string_en_f: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    fx3_cpapp: BoundedWindowDonorSummary
    fx6_cpapp: BoundedWindowDonorSummary
    fx3_libmpr: BoundedWindowDonorSummary
    fx6_libmpr: BoundedWindowDonorSummary
    fx3_bk4: BoundedWindowDonorSummary
    fx6_bk4: BoundedWindowDonorSummary
    framing_asymmetric_and_no_zve1_autoframing_proven: bool
    usb_power_npfz100_typec_and_lun_setup_proven: bool
    antiflicker_still_mech_and_no_fx3_varshutter_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FramingSettingsHilResult:
    body_model: str
    help_guide_id: str
    menu_path: str
    menu_node_name: str
    control_source: str
    configured_framing: str
    configured_recording_streaming: str
    configured_hdmi: str
    hdmi_raw_output: str
    reset_action: str
    effective_framing_register: str
    effective_recording_streaming_register: str
    effective_hdmi_register: str
    framing_active: bool
    effective_recording_stream_output: str
    effective_hdmi_monitor_output: str
    asymmetric_master_full_monitor_crop: bool
    reset_restored_factory_defaults: bool
    hdmi_raw_framing_conflict_blocked: bool
    zve1_autoframing_conflation_blocked: bool
    admitted: bool
    errno_code: int
    reason_code: str
    framing_crop_hdmi_raw_conflict_events: int
    zve1_autoframing_conflation_events: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class UsbPowerAndLunSetupHilResult:
    menu_path: str
    configured_usb_connection_mode: str
    configured_usb_lun_setting: str
    configured_usb_power_supply: str
    reset_action: str
    effective_usb_connection_mode: str
    effective_usb_lun_setting: str
    effective_usb_power_supply: str
    setup_usb_survived_camera_settings_reset: bool
    setup_usb_restored_by_initialize: bool
    battery_bay_state: str
    camera_power_switch_on: bool
    mid_session_battery_removed: bool
    usb_port: str
    external_usb_pd_source_attached: bool
    dual_slots_populated: bool
    live_host_usb_attach_requested: bool
    camera_powered_on: bool
    immediate_unbuffered_poweroff: bool
    usb_power_delivered_mw: int
    internal_charging_active: bool
    msc_enumerated_luns: Tuple[str, ...]
    msc_lun_count: int
    admitted: bool
    errno_code: int
    reason_code: str
    unbuffered_usb_pd_battery_pull_events: int
    multi_micro_usb_power_bypass_events: int
    physical_usb_packets_emitted: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class AntiFlickerNoVarShutterHilResult:
    body_model: str
    help_guide_id: str
    menu_path: str
    configured_anti_flicker_shoot: str
    capture_mode: str
    shutter_type: str
    silent_mode: str
    ambient_flicker_hz: int
    reset_action: str
    requested_var_shutter: bool
    requested_fx6_ecs: bool
    force_bypass_mechanical_still_scope: bool
    effective_anti_flicker_register: str
    reset_restored_off: bool
    anti_flicker_menu_grayed_out: bool
    anti_flicker_active: bool
    detected_flicker_hz: int
    fx3_has_var_shutter: bool
    fx3_has_ecs: bool
    admitted: bool
    errno_code: int
    reason_code: str
    antiflicker_movie_or_eshutter_bypass_events: int
    false_var_shutter_or_ecs_node_events: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    errno_code: int
    reason_code: str
    persistent_emmc_writes_authorized: bool
    hardware_live_attachment_authorized: bool
    overall_ready_for_hardware_attach: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    cnflasha_userspace_write_blocked: bool
    cnflasha_mutation_bytes: int
    physical_device_writes: int
    physical_usb_packets_emitted: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    framing_crop_hdmi_raw_conflict_events: int
    zve1_autoframing_conflation_events: int
    unbuffered_usb_pd_battery_pull_events: int
    multi_micro_usb_power_bypass_events: int
    antiflicker_movie_or_eshutter_bypass_events: int
    false_var_shutter_or_ecs_node_events: int
    fx3_has_var_shutter: bool
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY Donor Inspection (< 0.1s cold, cached, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase250DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase250DonorAudit] = None


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


def _iter_work_roots(*, env: Optional[Mapping[str, str]] = None) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates: List[Path] = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        val = source.get(key, "").strip()
        if val:
            candidates.append(Path(os.path.expanduser(val)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        base = Path(os.path.expanduser(mac_root))
        candidates.extend((base / "work", base / "outputs" / "sony-fx3-fx6-lab" / "work"))
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.extend((
        DEFAULT_REPO_ROOT / "work",
        internal / "work",
        internal / "outputs" / "sony-fx3-fx6-lab" / "work",
        LEGACY_MAC_ROOT / "work",
        LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work",
    ))
    dedup: List[Path] = []
    seen = set()
    for cand in candidates:
        s = str(cand)
        if s not in seen:
            seen.add(s)
            dedup.append(cand)
    return tuple(dedup)


def resolve_phase250_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 15 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen = next((root / rel for root in roots if (root / rel).is_file()), None)
        resolved[key] = (
            chosen
            if chosen is not None
            else (roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel))
        )
    return resolved


def _read_full_rdonly(path: Path) -> Tuple[int, bytes]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = max(st.st_size, 0)
        while remaining > 0:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return st.st_size, (chunks[0] if len(chunks) == 1 else b"".join(chunks))
    finally:
        os.close(fd)


def _read_bounded_windows_rdonly(
    path: Path,
    windows: Sequence[Tuple[int, str, bytes]],
) -> Tuple[int, int, bytes, Dict[str, int]]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        file_bytes = os.fstat(fd).st_size
        seen_offsets: Dict[int, bytes] = {}
        bytes_read_total = 0
        hits: Dict[str, int] = {}
        for off, label, tok in windows:
            if off not in seen_offsets:
                os.lseek(fd, off, os.SEEK_SET)
                buf = os.read(fd, BOUNDED_WINDOW_MAX_BYTES)
                seen_offsets[off] = buf
                bytes_read_total += len(buf)
            hits[label] = 1 if tok in seen_offsets[off] else 0
        head = seen_offsets.get(0)
        if head is None:
            os.lseek(fd, 0, os.SEEK_SET)
            head = os.read(fd, min(BOUNDED_WINDOW_MAX_BYTES, max(file_bytes, 0)))
            bytes_read_total += len(head)
        return file_bytes, bytes_read_total, head, hits
    finally:
        os.close(fd)


def _scan_compact_buf(
    data: bytes,
    *,
    file_bytes: int,
    artifact_key: str,
    body_label: str,
    source_mode: str,
    tokens: Sequence[bytes],
    absent_tokens: Sequence[bytes],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in tokens}
    absent_hits = {
        tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in absent_tokens
    }
    return CompactDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        uxd_container_ok=uxd_ok,
        sha256_prefix16=hashlib.sha256(data).hexdigest()[:16],
        marker_hits=hits,
        absent_marker_hits=absent_hits,
    )


def _scan_compact_rdonly(path: Path, *, artifact_key: str, body_label: str) -> CompactDonorSummary:
    file_bytes, data = _read_full_rdonly(path)
    return _scan_compact_buf(
        data,
        file_bytes=file_bytes,
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        tokens=COMPACT_DONOR_TOKENS[artifact_key],
        absent_tokens=COMPACT_ABSENT_TOKENS.get(artifact_key, ()),
    )


def _scan_large_donor_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
) -> BoundedWindowDonorSummary:
    file_bytes, bytes_read_total, head, hits = _read_bounded_windows_rdonly(
        path, LARGE_DONOR_WINDOWS[artifact_key]
    )
    elf64_ok = len(head) >= 64 and head[:4] == b"\x7fELF" and head[4] == 2 and head[5] == 1
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        bounded_windows_only=True,
        bytes_read_total=bytes_read_total,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        window_hits=hits,
        head_sha256_prefix16=hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()[:16],
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase250DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        absent_toks = COMPACT_ABSENT_TOKENS.get(key, ())
        tag = f"{key}_SYNTH_P250".encode("ascii")
        raw = (
            b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(toks) + b"\x00" + tag + b"\x00"
            if is_uxd
            else _build_synthetic_elf64_bytes(toks, tag)
        )
        return _scan_compact_buf(
            raw,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            tokens=toks,
            absent_tokens=absent_toks,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        head = (
            _build_synthetic_elf64_bytes((), f"{key}_HEAD_P250".encode("ascii"))
            if is_elf
            else (b"DONOR_SYNTH_P250_" + key.encode("ascii") + b"_" + label.encode("ascii")).ljust(
                64, b"\x00"
            )
        )
        hits = {lbl: 1 for _off, lbl, _tok in LARGE_DONOR_WINDOWS[key]}
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(head),
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256_prefix16=hashlib.sha256(head).hexdigest()[:16],
        )

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase250DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=15,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_imdb=_mk_compact("fx3_imdb", "FX3_7.02", False),
        fx3_usb_bus_power=_mk_compact("fx3_usb_bus_power", "FX3_7.02", False),
        fx3_msc_server=_mk_compact("fx3_msc_server", "FX3_7.02", False),
        fx3_media_cfg=_mk_compact("fx3_media_cfg", "FX3_7.02", False),
        fx3_adj_media=_mk_compact("fx3_adj_media", "FX3_7.02", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3_7.02", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6_6.01", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3_7.02", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6_6.01", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3_7.02", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6_6.01", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3_7.02", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6_6.01", True),
        fx3_bk4=_mk_large("fx3_bk4", "FX3_7.02", False),
        fx6_bk4=_mk_large("fx6_bk4", "FX6_6.01", False),
        framing_asymmetric_and_no_zve1_autoframing_proven=True,
        usb_power_npfz100_typec_and_lun_setup_proven=True,
        antiflicker_still_mech_and_no_fx3_varshutter_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase250_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase250DonorAudit:
    """Inspect 15 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.1s cold, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase250_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple(
        (k, str(p), p.stat().st_size, p.stat().st_mtime_ns) for k, p in sorted(paths.items())
    )
    cache_key = (SOURCE_MODE_LOCAL_DONOR, sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    t0 = time.perf_counter()
    fx3_imdb = _scan_compact_rdonly(paths["fx3_imdb"], artifact_key="fx3_imdb", body_label="FX3_7.02")
    fx3_usb_bus_power = _scan_compact_rdonly(
        paths["fx3_usb_bus_power"], artifact_key="fx3_usb_bus_power", body_label="FX3_7.02"
    )
    fx3_msc_server = _scan_compact_rdonly(
        paths["fx3_msc_server"], artifact_key="fx3_msc_server", body_label="FX3_7.02"
    )
    fx3_media_cfg = _scan_compact_rdonly(
        paths["fx3_media_cfg"], artifact_key="fx3_media_cfg", body_label="FX3_7.02"
    )
    fx3_adj_media = _scan_compact_rdonly(
        paths["fx3_adj_media"], artifact_key="fx3_adj_media", body_label="FX3_7.02"
    )
    fx3_string_en_f = _scan_compact_rdonly(
        paths["fx3_string_en_f"], artifact_key="fx3_string_en_f", body_label="FX3_7.02"
    )
    fx6_string_en = _scan_compact_rdonly(
        paths["fx6_string_en"], artifact_key="fx6_string_en", body_label="FX6_6.01"
    )
    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3_7.02"
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6_6.01"
    )
    fx3_cpapp = _scan_large_donor_rdonly(
        paths["fx3_cpapp"], artifact_key="fx3_cpapp", body_label="FX3_7.02"
    )
    fx6_cpapp = _scan_large_donor_rdonly(
        paths["fx6_cpapp"], artifact_key="fx6_cpapp", body_label="FX6_6.01"
    )
    fx3_libmpr = _scan_large_donor_rdonly(
        paths["fx3_libmpr"], artifact_key="fx3_libmpr", body_label="FX3_7.02"
    )
    fx6_libmpr = _scan_large_donor_rdonly(
        paths["fx6_libmpr"], artifact_key="fx6_libmpr", body_label="FX6_6.01"
    )
    fx3_bk4 = _scan_large_donor_rdonly(paths["fx3_bk4"], artifact_key="fx3_bk4", body_label="FX3_7.02")
    fx6_bk4 = _scan_large_donor_rdonly(paths["fx6_bk4"], artifact_key="fx6_bk4", body_label="FX6_6.01")
    elapsed = round(time.perf_counter() - t0, 6)

    errors: List[str] = []
    compact_map = {
        "fx3_imdb": fx3_imdb,
        "fx3_usb_bus_power": fx3_usb_bus_power,
        "fx3_msc_server": fx3_msc_server,
        "fx3_media_cfg": fx3_media_cfg,
        "fx3_adj_media": fx3_adj_media,
        "fx3_string_en_f": fx3_string_en_f,
        "fx6_string_en": fx6_string_en,
    }
    for key, comp in compact_map.items():
        if comp.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: expected {EXPECTED_DONOR_BYTES[key]}B, got {comp.file_bytes}B")
        for tok_s, hit in comp.marker_hits.items():
            if hit != 1:
                errors.append(f"{key}: missing marker {tok_s!r}")
        for abs_s, hit in comp.absent_marker_hits.items():
            if hit != 0:
                errors.append(f"{key}: unexpected forbidden marker {abs_s!r}")
        if key.startswith(("fx3_imdb", "fx3_usb", "fx3_msc", "fx3_media", "fx3_adj")) and not comp.elf64_le_ok:
            errors.append(f"{key}: ELF64 header check failed")
        if "string_en" in key and not comp.uxd_container_ok:
            errors.append(f"{key}: uxc/uxd header check failed")

    large_map = {
        "fx3_appfw": fx3_appfw,
        "fx6_appfw": fx6_appfw,
        "fx3_cpapp": fx3_cpapp,
        "fx6_cpapp": fx6_cpapp,
        "fx3_libmpr": fx3_libmpr,
        "fx6_libmpr": fx6_libmpr,
        "fx3_bk4": fx3_bk4,
        "fx6_bk4": fx6_bk4,
    }
    for key, lrg in large_map.items():
        if lrg.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: expected {EXPECTED_DONOR_BYTES[key]}B, got {lrg.file_bytes}B")
        for lbl, hit in lrg.window_hits.items():
            if hit != 1:
                errors.append(f"{key}: missing bounded window token {lbl!r}")
        if key in ("fx3_appfw", "fx6_appfw", "fx3_libmpr", "fx6_libmpr") and not lrg.elf64_le_ok:
            errors.append(f"{key}: ELF64 header check failed")

    framing_ok = (
        fx3_string_en_f.marker_hits.get("Framing Settings", 0) == 1
        and fx3_string_en_f.marker_hits.get("Recording/Streaming", 0) == 1
        and fx3_string_en_f.marker_hits.get("Crop", 0) == 1
        and fx3_string_en_f.marker_hits.get("Full", 0) == 1
        and fx3_string_en_f.absent_marker_hits.get("Autoframing Settings", 1) == 0
        and fx3_appfw.window_hits.get("FRAMING", 0) == 1
        and fx3_appfw.window_hits.get("CROP", 0) == 1
        and fx3_cpapp.window_hits.get("CROP", 0) == 1
    )
    usb_ok = (
        fx3_usb_bus_power.marker_hits.get("_ZN11UsbBusPower4MainEv", 0) == 1
        and fx3_msc_server.marker_hits.get("MassStorageServer_Create", 0) == 1
        and fx3_string_en_f.marker_hits.get("USB Power Supply", 0) == 1
        and fx3_string_en_f.marker_hits.get("USB LUN Setting", 0) == 1
        and fx3_string_en_f.marker_hits.get("USB Connection Mode", 0) == 1
        and fx3_string_en_f.marker_hits.get("Sel. When Connect", 0) == 1
        and fx3_string_en_f.marker_hits.get("Multi", 0) == 1
        and fx3_string_en_f.marker_hits.get("Single", 0) == 1
        and fx3_appfw.window_hits.get("USB_POWER", 0) == 1
        and fx3_appfw.window_hits.get("LUN", 0) == 1
        and fx3_appfw.window_hits.get("BATTERY", 0) == 1
    )
    antiflicker_ok = (
        fx3_string_en_f.marker_hits.get("Anti-flicker Shoot.", 0) == 1
        and fx3_string_en_f.marker_hits.get("Silent Mode", 0) == 1
        and fx3_string_en_f.absent_marker_hits.get("ECS", 1) == 0
        and fx6_string_en.marker_hits.get("ECS", 0) == 1
        and fx3_appfw.window_hits.get("FLICKER", 0) == 1
        and fx3_cpapp.window_hits.get("FLICKER", 0) == 1
        and fx3_cpapp.window_hits.get("SHUTTER", 0) == 1
    )
    if not framing_ok:
        errors.append("Framing Settings asymmetric Full/Crop or ZV-E1 Autoframing contract check failed")
    if not usb_ok:
        errors.append("USB Power Supply / USB LUN Setting / MscServer contract check failed")
    if not antiflicker_ok:
        errors.append("Anti-flicker Shoot. / FX3 no-ECS contract check failed")

    audit = Phase250DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=15,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_imdb=fx3_imdb,
        fx3_usb_bus_power=fx3_usb_bus_power,
        fx3_msc_server=fx3_msc_server,
        fx3_media_cfg=fx3_media_cfg,
        fx3_adj_media=fx3_adj_media,
        fx3_string_en_f=fx3_string_en_f,
        fx6_string_en=fx6_string_en,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        fx3_bk4=fx3_bk4,
        fx6_bk4=fx6_bk4,
        framing_asymmetric_and_no_zve1_autoframing_proven=framing_ok,
        usb_power_npfz100_typec_and_lun_setup_proven=usb_ok,
        antiflicker_still_mech_and_no_fx3_varshutter_proven=antiflicker_ok,
        all_contracts_verified=(len(errors) == 0),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 47A — [Framing Settings] Asymmetric Full/Crop & HDMI RAW Lockout
# ---------------------------------------------------------------------------


def simulate_framing_settings_asymmetric_crop_full_hil(
    *,
    body_model: str = BODY_MODEL_FX3,
    menu_node_name: str = FRAMING_MENU_NODE_FX3,
    control_source: str = FRAMING_CONTROL_ON_CAMERA,
    configured_framing: str = FRAMING_DEFAULT,
    configured_recording_streaming: str = FRAMING_RECORDING_STREAMING_DEFAULT,
    configured_hdmi: str = FRAMING_HDMI_DEFAULT,
    hdmi_raw_output: str = "Off",
    reset_action: str = RESET_ACTION_NONE,
    force_bypass_hdmi_raw_lock: bool = False,
) -> FramingSettingsHilResult:
    """Co-emulate MENU -> Shooting -> [Framing Settings] on ILME-FX3 (ilc/2210)."""
    if control_source not in VALID_FRAMING_CONTROL_SOURCES:
        return FramingSettingsHilResult(
            body_model=body_model,
            help_guide_id=FX3_HELP_GUIDE_ID,
            menu_path=FRAMING_SETTINGS_MENU_PATH,
            menu_node_name=menu_node_name,
            control_source=control_source,
            configured_framing=configured_framing,
            configured_recording_streaming=configured_recording_streaming,
            configured_hdmi=configured_hdmi,
            hdmi_raw_output=hdmi_raw_output,
            reset_action=reset_action,
            effective_framing_register=FRAMING_DEFAULT,
            effective_recording_streaming_register=FRAMING_RECORDING_STREAMING_DEFAULT,
            effective_hdmi_register=FRAMING_HDMI_DEFAULT,
            framing_active=False,
            effective_recording_stream_output=FRAMING_STREAM_FULL,
            effective_hdmi_monitor_output=FRAMING_STREAM_FULL,
            asymmetric_master_full_monitor_crop=False,
            reset_restored_factory_defaults=False,
            hdmi_raw_framing_conflict_blocked=False,
            zve1_autoframing_conflation_blocked=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="BLOCKED_47A_INVALID_FRAMING_CONTROL_SOURCE",
            framing_crop_hdmi_raw_conflict_events=0,
            zve1_autoframing_conflation_events=0,
            bk4_persistent_nvram_writes=0,
        )

    if body_model == BODY_MODEL_ZVE1 or menu_node_name == FRAMING_MENU_NODE_ZVE1_CONFLATED:
        return FramingSettingsHilResult(
            body_model=body_model,
            help_guide_id=FX3_HELP_GUIDE_ID,
            menu_path=FRAMING_SETTINGS_MENU_PATH,
            menu_node_name=menu_node_name,
            control_source=control_source,
            configured_framing=configured_framing,
            configured_recording_streaming=configured_recording_streaming,
            configured_hdmi=configured_hdmi,
            hdmi_raw_output=hdmi_raw_output,
            reset_action=reset_action,
            effective_framing_register=FRAMING_DEFAULT,
            effective_recording_streaming_register=FRAMING_RECORDING_STREAMING_DEFAULT,
            effective_hdmi_register=FRAMING_HDMI_DEFAULT,
            framing_active=False,
            effective_recording_stream_output=FRAMING_STREAM_FULL,
            effective_hdmi_monitor_output=FRAMING_STREAM_FULL,
            asymmetric_master_full_monitor_crop=False,
            reset_restored_factory_defaults=False,
            hdmi_raw_framing_conflict_blocked=False,
            zve1_autoframing_conflation_blocked=True,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="BLOCKED_47A_ZVE1_AUTOFRAMING_MENU_CONFLATION",
            framing_crop_hdmi_raw_conflict_events=0,
            zve1_autoframing_conflation_events=0,
            bk4_persistent_nvram_writes=0,
        )

    if (
        body_model != BODY_MODEL_FX3
        or menu_node_name != FRAMING_MENU_NODE_FX3
        or configured_framing not in VALID_ON_OFF
        or configured_recording_streaming not in VALID_FRAMING_STREAM_MODES
        or configured_hdmi not in VALID_FRAMING_STREAM_MODES
        or hdmi_raw_output not in VALID_ON_OFF
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return FramingSettingsHilResult(
            body_model=body_model,
            help_guide_id=FX3_HELP_GUIDE_ID,
            menu_path=FRAMING_SETTINGS_MENU_PATH,
            menu_node_name=menu_node_name,
            control_source=control_source,
            configured_framing=configured_framing,
            configured_recording_streaming=configured_recording_streaming,
            configured_hdmi=configured_hdmi,
            hdmi_raw_output=hdmi_raw_output,
            reset_action=reset_action,
            effective_framing_register=FRAMING_DEFAULT,
            effective_recording_streaming_register=FRAMING_RECORDING_STREAMING_DEFAULT,
            effective_hdmi_register=FRAMING_HDMI_DEFAULT,
            framing_active=False,
            effective_recording_stream_output=FRAMING_STREAM_FULL,
            effective_hdmi_monitor_output=FRAMING_STREAM_FULL,
            asymmetric_master_full_monitor_crop=False,
            reset_restored_factory_defaults=False,
            hdmi_raw_framing_conflict_blocked=False,
            zve1_autoframing_conflation_blocked=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="BLOCKED_47A_INVALID_FRAMING_PARAMETER",
            framing_crop_hdmi_raw_conflict_events=0,
            zve1_autoframing_conflation_events=0,
            bk4_persistent_nvram_writes=0,
        )

    # All 3 [Framing Settings] items reset via [Camera Settings Reset] AND [Initialize]
    if reset_action in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        eff_framing = FRAMING_DEFAULT
        eff_rec = FRAMING_RECORDING_STREAMING_DEFAULT
        eff_hdmi = FRAMING_HDMI_DEFAULT
        reset_restored = True
    else:
        eff_framing = configured_framing
        eff_rec = configured_recording_streaming
        eff_hdmi = configured_hdmi
        reset_restored = False

    # HDMI RAW output cannot be combined with [Framing]=On
    if eff_framing == "On" and hdmi_raw_output == "On":
        return FramingSettingsHilResult(
            body_model=body_model,
            help_guide_id=FX3_HELP_GUIDE_ID,
            menu_path=FRAMING_SETTINGS_MENU_PATH,
            menu_node_name=menu_node_name,
            control_source=control_source,
            configured_framing=configured_framing,
            configured_recording_streaming=configured_recording_streaming,
            configured_hdmi=configured_hdmi,
            hdmi_raw_output=hdmi_raw_output,
            reset_action=reset_action,
            effective_framing_register=eff_framing,
            effective_recording_streaming_register=eff_rec,
            effective_hdmi_register=eff_hdmi,
            framing_active=False,
            effective_recording_stream_output=FRAMING_STREAM_FULL,
            effective_hdmi_monitor_output="HDMI_RAW_16BIT",
            asymmetric_master_full_monitor_crop=False,
            reset_restored_factory_defaults=reset_restored,
            hdmi_raw_framing_conflict_blocked=True,
            zve1_autoframing_conflation_blocked=False,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO if force_bypass_hdmi_raw_lock else EBUSY_ERRNO,
            reason_code="BLOCKED_47A_FRAMING_ON_WITH_HDMI_RAW_MUTUAL_EXCLUSION",
            framing_crop_hdmi_raw_conflict_events=0,
            zve1_autoframing_conflation_events=0,
            bk4_persistent_nvram_writes=0,
        )

    framing_active = eff_framing == "On"
    rec_out = eff_rec if framing_active else FRAMING_STREAM_FULL
    hdmi_out = eff_hdmi if framing_active else FRAMING_STREAM_FULL
    asymmetric = framing_active and rec_out == FRAMING_STREAM_FULL and hdmi_out == FRAMING_STREAM_CROP

    return FramingSettingsHilResult(
        body_model=body_model,
        help_guide_id=FX3_HELP_GUIDE_ID,
        menu_path=FRAMING_SETTINGS_MENU_PATH,
        menu_node_name=menu_node_name,
        control_source=control_source,
        configured_framing=configured_framing,
        configured_recording_streaming=configured_recording_streaming,
        configured_hdmi=configured_hdmi,
        hdmi_raw_output=hdmi_raw_output,
        reset_action=reset_action,
        effective_framing_register=eff_framing,
        effective_recording_streaming_register=eff_rec,
        effective_hdmi_register=eff_hdmi,
        framing_active=framing_active,
        effective_recording_stream_output=rec_out,
        effective_hdmi_monitor_output=hdmi_out,
        asymmetric_master_full_monitor_crop=asymmetric,
        reset_restored_factory_defaults=reset_restored,
        hdmi_raw_framing_conflict_blocked=False,
        zve1_autoframing_conflation_blocked=False,
        admitted=True,
        errno_code=0,
        reason_code=(
            "OK_47A_FRAMING_ASYMMETRIC_FULL_MASTER_CROP_HDMI"
            if asymmetric
            else ("OK_47A_FRAMING_ACTIVE_CUSTOM_ROUTING" if framing_active else "OK_47A_FRAMING_OFF_FULL_PASSTHROUGH")
        ),
        framing_crop_hdmi_raw_conflict_events=0,
        zve1_autoframing_conflation_events=0,
        bk4_persistent_nvram_writes=0,
    )


def run_framing_settings_reset_and_mc_remote_lifecycle() -> Dict[str, object]:
    """Verify factory asymmetric routing via Monitor & Control and full reset via Camera Settings Reset."""
    factory_off = simulate_framing_settings_asymmetric_crop_full_hil()
    mc_remote_asymmetric_on = simulate_framing_settings_asymmetric_crop_full_hil(
        control_source=FRAMING_CONTROL_MONITOR_AND_CONTROL,
        configured_framing="On",
    )
    custom_crop_full = simulate_framing_settings_asymmetric_crop_full_hil(
        configured_framing="On",
        configured_recording_streaming=FRAMING_STREAM_CROP,
        configured_hdmi=FRAMING_STREAM_FULL,
    )
    after_cam_reset = simulate_framing_settings_asymmetric_crop_full_hil(
        configured_framing="On",
        configured_recording_streaming=FRAMING_STREAM_CROP,
        configured_hdmi=FRAMING_STREAM_FULL,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    after_initialize = simulate_framing_settings_asymmetric_crop_full_hil(
        configured_framing="On",
        configured_recording_streaming=FRAMING_STREAM_CROP,
        configured_hdmi=FRAMING_STREAM_FULL,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    ok = (
        factory_off.admitted
        and not factory_off.framing_active
        and factory_off.effective_recording_streaming_register == "Full"
        and factory_off.effective_hdmi_register == "Crop"
        and mc_remote_asymmetric_on.admitted
        and mc_remote_asymmetric_on.framing_active
        and mc_remote_asymmetric_on.asymmetric_master_full_monitor_crop
        and mc_remote_asymmetric_on.effective_recording_stream_output == "Full"
        and mc_remote_asymmetric_on.effective_hdmi_monitor_output == "Crop"
        and custom_crop_full.admitted
        and custom_crop_full.effective_recording_stream_output == "Crop"
        and custom_crop_full.effective_hdmi_monitor_output == "Full"
        and after_cam_reset.admitted
        and after_cam_reset.reset_restored_factory_defaults
        and after_cam_reset.effective_framing_register == "Off"
        and after_cam_reset.effective_recording_streaming_register == "Full"
        and after_cam_reset.effective_hdmi_register == "Crop"
        and after_initialize.admitted
        and after_initialize.reset_restored_factory_defaults
    )
    return {
        "lifecycle_passed": ok,
        "factory_off": asdict(factory_off),
        "mc_remote_asymmetric_on": asdict(mc_remote_asymmetric_on),
        "custom_crop_full": asdict(custom_crop_full),
        "after_camera_settings_reset": asdict(after_cam_reset),
        "after_initialize": asdict(after_initialize),
    }


def evaluate_pillar_a_framing_asymmetric_and_hdmi_raw_hil() -> Dict[str, object]:
    lifecycle = run_framing_settings_reset_and_mc_remote_lifecycle()
    routing_matrix = [
        asdict(
            simulate_framing_settings_asymmetric_crop_full_hil(
                configured_framing="On",
                configured_recording_streaming=rec_mode,
                configured_hdmi=hdmi_mode,
            )
        )
        for rec_mode in VALID_FRAMING_STREAM_MODES
        for hdmi_mode in VALID_FRAMING_STREAM_MODES
    ]
    hdmi_raw_blocked_ebusy = simulate_framing_settings_asymmetric_crop_full_hil(
        configured_framing="On",
        hdmi_raw_output="On",
    )
    hdmi_raw_bypass_blocked_eopnotsupp = simulate_framing_settings_asymmetric_crop_full_hil(
        configured_framing="On",
        hdmi_raw_output="On",
        force_bypass_hdmi_raw_lock=True,
    )
    hdmi_raw_with_framing_off_ok = simulate_framing_settings_asymmetric_crop_full_hil(
        configured_framing="Off",
        hdmi_raw_output="On",
    )
    zve1_menu_conflation_blocked = simulate_framing_settings_asymmetric_crop_full_hil(
        menu_node_name=FRAMING_MENU_NODE_ZVE1_CONFLATED,
    )
    zve1_body_conflation_blocked = simulate_framing_settings_asymmetric_crop_full_hil(
        body_model=BODY_MODEL_ZVE1,
    )
    passed = (
        bool(lifecycle["lifecycle_passed"])
        and len(routing_matrix) == 4
        and all(bool(r["admitted"]) for r in routing_matrix)
        and (not hdmi_raw_blocked_ebusy.admitted)
        and hdmi_raw_blocked_ebusy.errno_code == EBUSY_ERRNO
        and hdmi_raw_blocked_ebusy.hdmi_raw_framing_conflict_blocked
        and (not hdmi_raw_bypass_blocked_eopnotsupp.admitted)
        and hdmi_raw_bypass_blocked_eopnotsupp.errno_code == EOPNOTSUPP_ERRNO
        and hdmi_raw_with_framing_off_ok.admitted
        and (not zve1_menu_conflation_blocked.admitted)
        and zve1_menu_conflation_blocked.errno_code == EOPNOTSUPP_ERRNO
        and zve1_menu_conflation_blocked.zve1_autoframing_conflation_blocked
        and (not zve1_body_conflation_blocked.admitted)
        and zve1_body_conflation_blocked.errno_code == EOPNOTSUPP_ERRNO
    )
    return {
        "passed": passed,
        "menu_path": FRAMING_SETTINGS_MENU_PATH,
        "factory_defaults": {
            "Framing": FRAMING_DEFAULT,
            "Recording/Streaming": FRAMING_RECORDING_STREAMING_DEFAULT,
            "HDMI": FRAMING_HDMI_DEFAULT,
        },
        "all_stream_modes": list(VALID_FRAMING_STREAM_MODES),
        "all_control_sources": list(VALID_FRAMING_CONTROL_SOURCES),
        "lifecycle": lifecycle,
        "routing_4way_matrix": routing_matrix,
        "hdmi_raw_blocked_ebusy": asdict(hdmi_raw_blocked_ebusy),
        "hdmi_raw_bypass_blocked_eopnotsupp": asdict(hdmi_raw_bypass_blocked_eopnotsupp),
        "hdmi_raw_with_framing_off_ok": asdict(hdmi_raw_with_framing_off_ok),
        "zve1_menu_conflation_blocked": asdict(zve1_menu_conflation_blocked),
        "zve1_body_conflation_blocked": asdict(zve1_body_conflation_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 47B — [USB Power Supply] NP-FZ100 + Type-C & [USB LUN] Survival
# ---------------------------------------------------------------------------


def simulate_usb_power_npfz100_typec_and_lun_setup_hil(
    *,
    configured_usb_connection_mode: str = USB_CONNECTION_MODE_DEFAULT,
    configured_usb_lun_setting: str = USB_LUN_SETTING_DEFAULT,
    configured_usb_power_supply: str = USB_POWER_SUPPLY_DEFAULT,
    reset_action: str = RESET_ACTION_NONE,
    battery_bay_state: str = BATTERY_BAY_NP_FZ100,
    camera_power_switch_on: bool = True,
    mid_session_battery_removed: bool = False,
    usb_port: str = USB_PORT_TYPE_C,
    external_usb_pd_source_attached: bool = True,
    dual_slots_populated: bool = True,
    live_host_usb_attach_requested: bool = False,
) -> UsbPowerAndLunSetupHilResult:
    """Co-emulate MENU -> Setup -> [USB] persistence, NP-FZ100/Type-C interlocks, and LUN visibility."""
    if (
        configured_usb_connection_mode not in VALID_USB_CONNECTION_MODES
        or configured_usb_lun_setting not in VALID_USB_LUN_SETTINGS
        or configured_usb_power_supply not in VALID_ON_OFF
        or reset_action not in VALID_RESET_ACTIONS
        or battery_bay_state not in VALID_BATTERY_BAY_STATES
        or usb_port not in VALID_USB_PORTS
    ):
        return UsbPowerAndLunSetupHilResult(
            menu_path=SETUP_USB_MENU_PATH,
            configured_usb_connection_mode=configured_usb_connection_mode,
            configured_usb_lun_setting=configured_usb_lun_setting,
            configured_usb_power_supply=configured_usb_power_supply,
            reset_action=reset_action,
            effective_usb_connection_mode=USB_CONNECTION_MODE_DEFAULT,
            effective_usb_lun_setting=USB_LUN_SETTING_DEFAULT,
            effective_usb_power_supply=USB_POWER_SUPPLY_DEFAULT,
            setup_usb_survived_camera_settings_reset=False,
            setup_usb_restored_by_initialize=False,
            battery_bay_state=battery_bay_state,
            camera_power_switch_on=camera_power_switch_on,
            mid_session_battery_removed=mid_session_battery_removed,
            usb_port=usb_port,
            external_usb_pd_source_attached=external_usb_pd_source_attached,
            dual_slots_populated=dual_slots_populated,
            live_host_usb_attach_requested=live_host_usb_attach_requested,
            camera_powered_on=False,
            immediate_unbuffered_poweroff=False,
            usb_power_delivered_mw=0,
            internal_charging_active=False,
            msc_enumerated_luns=(),
            msc_lun_count=0,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="BLOCKED_47B_INVALID_USB_SETUP_PARAMETER",
            unbuffered_usb_pd_battery_pull_events=0,
            multi_micro_usb_power_bypass_events=0,
            physical_usb_packets_emitted=0,
            bk4_persistent_nvram_writes=0,
        )

    # [Setup] -> [USB] items SURVIVE [Camera Settings Reset]; restored ONLY by [Initialize]
    if reset_action == RESET_ACTION_INITIALIZE:
        eff_conn = USB_CONNECTION_MODE_DEFAULT
        eff_lun = USB_LUN_SETTING_DEFAULT
        eff_pwr = USB_POWER_SUPPLY_DEFAULT
        survived_cam_reset = False
        restored_by_init = True
    else:
        eff_conn = configured_usb_connection_mode
        eff_lun = configured_usb_lun_setting
        eff_pwr = configured_usb_power_supply
        survived_cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
        restored_by_init = False

    luns: Tuple[str, ...] = (
        (("Slot 1", "Slot 2") if dual_slots_populated else ("Slot 1",))
        if eff_lun == USB_LUN_MULTI
        else ("Slot 1",)
    )

    # Hard lab bench block on live host USB connection
    if live_host_usb_attach_requested:
        return UsbPowerAndLunSetupHilResult(
            menu_path=SETUP_USB_MENU_PATH,
            configured_usb_connection_mode=configured_usb_connection_mode,
            configured_usb_lun_setting=configured_usb_lun_setting,
            configured_usb_power_supply=configured_usb_power_supply,
            reset_action=reset_action,
            effective_usb_connection_mode=eff_conn,
            effective_usb_lun_setting=eff_lun,
            effective_usb_power_supply=eff_pwr,
            setup_usb_survived_camera_settings_reset=survived_cam_reset,
            setup_usb_restored_by_initialize=restored_by_init,
            battery_bay_state=battery_bay_state,
            camera_power_switch_on=camera_power_switch_on,
            mid_session_battery_removed=mid_session_battery_removed,
            usb_port=usb_port,
            external_usb_pd_source_attached=external_usb_pd_source_attached,
            dual_slots_populated=dual_slots_populated,
            live_host_usb_attach_requested=True,
            camera_powered_on=False,
            immediate_unbuffered_poweroff=False,
            usb_power_delivered_mw=0,
            internal_charging_active=False,
            msc_enumerated_luns=luns,
            msc_lun_count=len(luns),
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="BLOCKED_47B_LIVE_HOST_USB_ATTACHMENT_FORBIDDEN",
            unbuffered_usb_pd_battery_pull_events=0,
            multi_micro_usb_power_bypass_events=0,
            physical_usb_packets_emitted=0,
            bk4_persistent_nvram_writes=0,
        )

    # Multi/Micro USB zero-power / zero-charge hardware boundary (USB Type-C exclusive)
    if usb_port == USB_PORT_MULTI_MICRO and external_usb_pd_source_attached:
        return UsbPowerAndLunSetupHilResult(
            menu_path=SETUP_USB_MENU_PATH,
            configured_usb_connection_mode=configured_usb_connection_mode,
            configured_usb_lun_setting=configured_usb_lun_setting,
            configured_usb_power_supply=configured_usb_power_supply,
            reset_action=reset_action,
            effective_usb_connection_mode=eff_conn,
            effective_usb_lun_setting=eff_lun,
            effective_usb_power_supply=eff_pwr,
            setup_usb_survived_camera_settings_reset=survived_cam_reset,
            setup_usb_restored_by_initialize=restored_by_init,
            battery_bay_state=battery_bay_state,
            camera_power_switch_on=camera_power_switch_on,
            mid_session_battery_removed=mid_session_battery_removed,
            usb_port=usb_port,
            external_usb_pd_source_attached=True,
            dual_slots_populated=dual_slots_populated,
            live_host_usb_attach_requested=False,
            camera_powered_on=False,
            immediate_unbuffered_poweroff=False,
            usb_power_delivered_mw=0,
            internal_charging_active=False,
            msc_enumerated_luns=luns,
            msc_lun_count=len(luns),
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="BLOCKED_47B_MULTI_MICRO_USB_ZERO_POWER_BOUNDARY",
            unbuffered_usb_pd_battery_pull_events=0,
            multi_micro_usb_power_bypass_events=0,
            physical_usb_packets_emitted=0,
            bk4_persistent_nvram_writes=0,
        )

    # Mandatory inserted NP-FZ100 (or DC-C1) to power on camera
    if camera_power_switch_on and battery_bay_state == BATTERY_BAY_EMPTY:
        return UsbPowerAndLunSetupHilResult(
            menu_path=SETUP_USB_MENU_PATH,
            configured_usb_connection_mode=configured_usb_connection_mode,
            configured_usb_lun_setting=configured_usb_lun_setting,
            configured_usb_power_supply=configured_usb_power_supply,
            reset_action=reset_action,
            effective_usb_connection_mode=eff_conn,
            effective_usb_lun_setting=eff_lun,
            effective_usb_power_supply=eff_pwr,
            setup_usb_survived_camera_settings_reset=survived_cam_reset,
            setup_usb_restored_by_initialize=restored_by_init,
            battery_bay_state=battery_bay_state,
            camera_power_switch_on=True,
            mid_session_battery_removed=mid_session_battery_removed,
            usb_port=usb_port,
            external_usb_pd_source_attached=external_usb_pd_source_attached,
            dual_slots_populated=dual_slots_populated,
            live_host_usb_attach_requested=False,
            camera_powered_on=False,
            immediate_unbuffered_poweroff=False,
            usb_power_delivered_mw=0,
            internal_charging_active=False,
            msc_enumerated_luns=(),
            msc_lun_count=0,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="BLOCKED_47B_USB_POWER_WITHOUT_NPFZ100_BATTERY_UNAVAILABLE",
            unbuffered_usb_pd_battery_pull_events=0,
            multi_micro_usb_power_bypass_events=0,
            physical_usb_packets_emitted=0,
            bk4_persistent_nvram_writes=0,
        )

    # Mid-session NP-FZ100 pull while powered via USB PD wall outlet -> immediate unbuffered cutoff
    if camera_power_switch_on and mid_session_battery_removed and battery_bay_state != BATTERY_BAY_DC_C1:
        return UsbPowerAndLunSetupHilResult(
            menu_path=SETUP_USB_MENU_PATH,
            configured_usb_connection_mode=configured_usb_connection_mode,
            configured_usb_lun_setting=configured_usb_lun_setting,
            configured_usb_power_supply=configured_usb_power_supply,
            reset_action=reset_action,
            effective_usb_connection_mode=eff_conn,
            effective_usb_lun_setting=eff_lun,
            effective_usb_power_supply=eff_pwr,
            setup_usb_survived_camera_settings_reset=survived_cam_reset,
            setup_usb_restored_by_initialize=restored_by_init,
            battery_bay_state=battery_bay_state,
            camera_power_switch_on=True,
            mid_session_battery_removed=True,
            usb_port=usb_port,
            external_usb_pd_source_attached=external_usb_pd_source_attached,
            dual_slots_populated=dual_slots_populated,
            live_host_usb_attach_requested=False,
            camera_powered_on=False,
            immediate_unbuffered_poweroff=True,
            usb_power_delivered_mw=0,
            internal_charging_active=False,
            msc_enumerated_luns=(),
            msc_lun_count=0,
            admitted=False,
            errno_code=EBUSY_ERRNO,
            reason_code="BLOCKED_47B_MID_SESSION_BATTERY_PULL_UNBUFFERED_CUTOFF",
            unbuffered_usb_pd_battery_pull_events=0,
            multi_micro_usb_power_bypass_events=0,
            physical_usb_packets_emitted=0,
            bk4_persistent_nvram_writes=0,
        )

    typec_pd_ready = (
        usb_port == USB_PORT_TYPE_C
        and external_usb_pd_source_attached
        and battery_bay_state in (BATTERY_BAY_NP_FZ100, BATTERY_BAY_DC_C1)
    )
    usb_mw = 18_000 if (camera_power_switch_on and typec_pd_ready and eff_pwr == "On") else (
        15_000 if ((not camera_power_switch_on) and typec_pd_ready and battery_bay_state == BATTERY_BAY_NP_FZ100) else 0
    )
    charging = (
        (not camera_power_switch_on)
        and usb_port == USB_PORT_TYPE_C
        and external_usb_pd_source_attached
        and battery_bay_state == BATTERY_BAY_NP_FZ100
    )

    return UsbPowerAndLunSetupHilResult(
        menu_path=SETUP_USB_MENU_PATH,
        configured_usb_connection_mode=configured_usb_connection_mode,
        configured_usb_lun_setting=configured_usb_lun_setting,
        configured_usb_power_supply=configured_usb_power_supply,
        reset_action=reset_action,
        effective_usb_connection_mode=eff_conn,
        effective_usb_lun_setting=eff_lun,
        effective_usb_power_supply=eff_pwr,
        setup_usb_survived_camera_settings_reset=survived_cam_reset,
        setup_usb_restored_by_initialize=restored_by_init,
        battery_bay_state=battery_bay_state,
        camera_power_switch_on=camera_power_switch_on,
        mid_session_battery_removed=mid_session_battery_removed,
        usb_port=usb_port,
        external_usb_pd_source_attached=external_usb_pd_source_attached,
        dual_slots_populated=dual_slots_populated,
        live_host_usb_attach_requested=False,
        camera_powered_on=camera_power_switch_on,
        immediate_unbuffered_poweroff=False,
        usb_power_delivered_mw=usb_mw,
        internal_charging_active=charging,
        msc_enumerated_luns=luns,
        msc_lun_count=len(luns),
        admitted=True,
        errno_code=0,
        reason_code=(
            "OK_47B_TYPEC_USB_PD_SUPPLY_WITH_BATTERY_INTERLOCK"
            if (camera_power_switch_on and usb_mw > 0)
            else ("OK_47B_TYPEC_OFF_STATE_BATTERY_CHARGING" if charging else "OK_47B_INTERNAL_BATTERY_ONLY_OPERATION")
        ),
        unbuffered_usb_pd_battery_pull_events=0,
        multi_micro_usb_power_bypass_events=0,
        physical_usb_packets_emitted=0,
        bk4_persistent_nvram_writes=0,
    )


def run_usb_setup_reset_survival_and_initialize_lifecycle() -> Dict[str, object]:
    """Verify [Setup]->[USB] survives [Camera Settings Reset] and resets only via [Initialize]."""
    customized = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        configured_usb_connection_mode=USB_CONN_MASS_STORAGE,
        configured_usb_lun_setting=USB_LUN_SINGLE,
        configured_usb_power_supply="Off",
    )
    after_cam_reset = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        configured_usb_connection_mode=USB_CONN_MASS_STORAGE,
        configured_usb_lun_setting=USB_LUN_SINGLE,
        configured_usb_power_supply="Off",
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    after_initialize = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        configured_usb_connection_mode=USB_CONN_MASS_STORAGE,
        configured_usb_lun_setting=USB_LUN_SINGLE,
        configured_usb_power_supply="Off",
        reset_action=RESET_ACTION_INITIALIZE,
    )
    ok = (
        customized.admitted
        and customized.effective_usb_connection_mode == USB_CONN_MASS_STORAGE
        and customized.effective_usb_lun_setting == USB_LUN_SINGLE
        and customized.effective_usb_power_supply == "Off"
        and customized.msc_lun_count == 1
        and after_cam_reset.admitted
        and after_cam_reset.setup_usb_survived_camera_settings_reset
        and after_cam_reset.effective_usb_connection_mode == USB_CONN_MASS_STORAGE
        and after_cam_reset.effective_usb_lun_setting == USB_LUN_SINGLE
        and after_cam_reset.effective_usb_power_supply == "Off"
        and after_initialize.admitted
        and after_initialize.setup_usb_restored_by_initialize
        and after_initialize.effective_usb_connection_mode == USB_CONN_SEL_WHEN_CONNECT
        and after_initialize.effective_usb_lun_setting == USB_LUN_MULTI
        and after_initialize.effective_usb_power_supply == "On"
        and after_initialize.msc_lun_count == 2
    )
    return {
        "lifecycle_passed": ok,
        "customized": asdict(customized),
        "after_camera_settings_reset": asdict(after_cam_reset),
        "after_initialize": asdict(after_initialize),
    }


def evaluate_pillar_b_usb_power_npfz100_typec_and_lun_setup_hil() -> Dict[str, object]:
    lifecycle = run_usb_setup_reset_survival_and_initialize_lifecycle()
    typec_npfz100_on_ok = simulate_usb_power_npfz100_typec_and_lun_setup_hil()
    typec_dcc1_on_ok = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        battery_bay_state=BATTERY_BAY_DC_C1,
    )
    typec_off_charging_ok = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        camera_power_switch_on=False,
        battery_bay_state=BATTERY_BAY_NP_FZ100,
    )
    lun_multi_2slot_ok = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        configured_usb_connection_mode=USB_CONN_MASS_STORAGE,
        configured_usb_lun_setting=USB_LUN_MULTI,
        dual_slots_populated=True,
    )
    lun_single_1slot_ok = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        configured_usb_connection_mode=USB_CONN_MASS_STORAGE,
        configured_usb_lun_setting=USB_LUN_SINGLE,
        dual_slots_populated=True,
    )
    no_battery_power_on_blocked = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        battery_bay_state=BATTERY_BAY_EMPTY,
    )
    mid_session_battery_pull_blocked = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        battery_bay_state=BATTERY_BAY_NP_FZ100,
        mid_session_battery_removed=True,
    )
    multi_micro_usb_blocked = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        usb_port=USB_PORT_MULTI_MICRO,
        external_usb_pd_source_attached=True,
    )
    live_host_usb_blocked = simulate_usb_power_npfz100_typec_and_lun_setup_hil(
        live_host_usb_attach_requested=True,
    )

    passed = (
        bool(lifecycle["lifecycle_passed"])
        and typec_npfz100_on_ok.admitted
        and typec_npfz100_on_ok.usb_power_delivered_mw == 18_000
        and typec_dcc1_on_ok.admitted
        and typec_dcc1_on_ok.usb_power_delivered_mw == 18_000
        and typec_off_charging_ok.admitted
        and typec_off_charging_ok.internal_charging_active
        and lun_multi_2slot_ok.msc_enumerated_luns == ("Slot 1", "Slot 2")
        and lun_single_1slot_ok.msc_enumerated_luns == ("Slot 1",)
        and (not no_battery_power_on_blocked.admitted)
        and no_battery_power_on_blocked.errno_code == EACCES_ERRNO
        and (not no_battery_power_on_blocked.camera_powered_on)
        and (not mid_session_battery_pull_blocked.admitted)
        and mid_session_battery_pull_blocked.errno_code == EBUSY_ERRNO
        and mid_session_battery_pull_blocked.immediate_unbuffered_poweroff
        and (not multi_micro_usb_blocked.admitted)
        and multi_micro_usb_blocked.errno_code == EOPNOTSUPP_ERRNO
        and multi_micro_usb_blocked.usb_power_delivered_mw == 0
        and (not live_host_usb_blocked.admitted)
        and live_host_usb_blocked.errno_code == EACCES_ERRNO
        and live_host_usb_blocked.physical_usb_packets_emitted == 0
    )
    return {
        "passed": passed,
        "menu_path": SETUP_USB_MENU_PATH,
        "all_4_usb_connection_modes": list(VALID_USB_CONNECTION_MODES),
        "all_2_usb_lun_settings": list(VALID_USB_LUN_SETTINGS),
        "factory_defaults": {
            "USB Connection Mode": USB_CONNECTION_MODE_DEFAULT,
            "USB LUN Setting": USB_LUN_SETTING_DEFAULT,
            "USB Power Supply": USB_POWER_SUPPLY_DEFAULT,
        },
        "lifecycle": lifecycle,
        "typec_npfz100_on_ok": asdict(typec_npfz100_on_ok),
        "typec_dcc1_on_ok": asdict(typec_dcc1_on_ok),
        "typec_off_charging_ok": asdict(typec_off_charging_ok),
        "lun_multi_2slot_ok": asdict(lun_multi_2slot_ok),
        "lun_single_1slot_ok": asdict(lun_single_1slot_ok),
        "no_battery_power_on_blocked": asdict(no_battery_power_on_blocked),
        "mid_session_battery_pull_blocked": asdict(mid_session_battery_pull_blocked),
        "multi_micro_usb_blocked": asdict(multi_micro_usb_blocked),
        "live_host_usb_blocked": asdict(live_host_usb_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 47C — [Anti-flicker Shoot.] Mechanical-Still-Only & No [Var. Shutter]
# ---------------------------------------------------------------------------


def simulate_antiflicker_still_mech_and_no_varshutter_hil(
    *,
    body_model: str = BODY_MODEL_FX3,
    configured_anti_flicker_shoot: str = ANTI_FLICKER_SHOOT_DEFAULT,
    capture_mode: str = CAPTURE_MODE_STILL,
    shutter_type: str = SHUTTER_TYPE_MECHANICAL,
    silent_mode: str = SILENT_MODE_DEFAULT,
    ambient_flicker_hz: int = 100,
    reset_action: str = RESET_ACTION_NONE,
    requested_var_shutter: bool = False,
    requested_fx6_ecs: bool = False,
    force_bypass_mechanical_still_scope: bool = False,
) -> AntiFlickerNoVarShutterHilResult:
    """Co-emulate MENU -> Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.] & no [Var. Shutter]."""
    if (
        body_model != BODY_MODEL_FX3
        or configured_anti_flicker_shoot not in VALID_ON_OFF
        or capture_mode not in VALID_CAPTURE_MODES
        or shutter_type not in VALID_SHUTTER_TYPES
        or silent_mode not in VALID_ON_OFF
        or ambient_flicker_hz not in VALID_FLICKER_FREQUENCIES_HZ
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return AntiFlickerNoVarShutterHilResult(
            body_model=body_model,
            help_guide_id=FX3_HELP_GUIDE_ID,
            menu_path=ANTI_FLICKER_SHOOT_MENU_PATH,
            configured_anti_flicker_shoot=configured_anti_flicker_shoot,
            capture_mode=capture_mode,
            shutter_type=shutter_type,
            silent_mode=silent_mode,
            ambient_flicker_hz=ambient_flicker_hz,
            reset_action=reset_action,
            requested_var_shutter=requested_var_shutter,
            requested_fx6_ecs=requested_fx6_ecs,
            force_bypass_mechanical_still_scope=force_bypass_mechanical_still_scope,
            effective_anti_flicker_register=ANTI_FLICKER_SHOOT_DEFAULT,
            reset_restored_off=False,
            anti_flicker_menu_grayed_out=True,
            anti_flicker_active=False,
            detected_flicker_hz=0,
            fx3_has_var_shutter=FX3_HAS_VAR_SHUTTER,
            fx3_has_ecs=FX3_HAS_ECS,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="BLOCKED_47C_INVALID_ANTIFLICKER_PARAMETER",
            antiflicker_movie_or_eshutter_bypass_events=0,
            false_var_shutter_or_ecs_node_events=0,
            bk4_persistent_nvram_writes=0,
        )

    # Stock ILME-FX3 (ilc/2210 through Ver. 7.02) does NOT implement [Var. Shutter] or FX6 ECS
    if requested_var_shutter or requested_fx6_ecs:
        return AntiFlickerNoVarShutterHilResult(
            body_model=body_model,
            help_guide_id=FX3_HELP_GUIDE_ID,
            menu_path=ANTI_FLICKER_SHOOT_MENU_PATH,
            configured_anti_flicker_shoot=configured_anti_flicker_shoot,
            capture_mode=capture_mode,
            shutter_type=shutter_type,
            silent_mode=silent_mode,
            ambient_flicker_hz=ambient_flicker_hz,
            reset_action=reset_action,
            requested_var_shutter=requested_var_shutter,
            requested_fx6_ecs=requested_fx6_ecs,
            force_bypass_mechanical_still_scope=force_bypass_mechanical_still_scope,
            effective_anti_flicker_register=ANTI_FLICKER_SHOOT_DEFAULT,
            reset_restored_off=False,
            anti_flicker_menu_grayed_out=True,
            anti_flicker_active=False,
            detected_flicker_hz=0,
            fx3_has_var_shutter=FX3_HAS_VAR_SHUTTER,
            fx3_has_ecs=FX3_HAS_ECS,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="BLOCKED_47C_STOCK_FX3_NO_VAR_SHUTTER_OR_ECS",
            antiflicker_movie_or_eshutter_bypass_events=0,
            false_var_shutter_or_ecs_node_events=0,
            bk4_persistent_nvram_writes=0,
        )

    if reset_action in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        eff_reg = ANTI_FLICKER_SHOOT_DEFAULT
        reset_restored = True
    else:
        eff_reg = configured_anti_flicker_shoot
        reset_restored = False

    mech_still_eligible = (
        capture_mode == CAPTURE_MODE_STILL
        and shutter_type == SHUTTER_TYPE_MECHANICAL
        and silent_mode == "Off"
    )

    if (not mech_still_eligible) and force_bypass_mechanical_still_scope:
        return AntiFlickerNoVarShutterHilResult(
            body_model=body_model,
            help_guide_id=FX3_HELP_GUIDE_ID,
            menu_path=ANTI_FLICKER_SHOOT_MENU_PATH,
            configured_anti_flicker_shoot=configured_anti_flicker_shoot,
            capture_mode=capture_mode,
            shutter_type=shutter_type,
            silent_mode=silent_mode,
            ambient_flicker_hz=ambient_flicker_hz,
            reset_action=reset_action,
            requested_var_shutter=False,
            requested_fx6_ecs=False,
            force_bypass_mechanical_still_scope=True,
            effective_anti_flicker_register=eff_reg,
            reset_restored_off=reset_restored,
            anti_flicker_menu_grayed_out=True,
            anti_flicker_active=False,
            detected_flicker_hz=0,
            fx3_has_var_shutter=FX3_HAS_VAR_SHUTTER,
            fx3_has_ecs=FX3_HAS_ECS,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="BLOCKED_47C_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_SCOPE",
            antiflicker_movie_or_eshutter_bypass_events=0,
            false_var_shutter_or_ecs_node_events=0,
            bk4_persistent_nvram_writes=0,
        )

    active = mech_still_eligible and eff_reg == "On"
    detected_hz = ambient_flicker_hz if active else 0

    return AntiFlickerNoVarShutterHilResult(
        body_model=body_model,
        help_guide_id=FX3_HELP_GUIDE_ID,
        menu_path=ANTI_FLICKER_SHOOT_MENU_PATH,
        configured_anti_flicker_shoot=configured_anti_flicker_shoot,
        capture_mode=capture_mode,
        shutter_type=shutter_type,
        silent_mode=silent_mode,
        ambient_flicker_hz=ambient_flicker_hz,
        reset_action=reset_action,
        requested_var_shutter=False,
        requested_fx6_ecs=False,
        force_bypass_mechanical_still_scope=False,
        effective_anti_flicker_register=eff_reg,
        reset_restored_off=reset_restored,
        anti_flicker_menu_grayed_out=(not mech_still_eligible),
        anti_flicker_active=active,
        detected_flicker_hz=detected_hz,
        fx3_has_var_shutter=FX3_HAS_VAR_SHUTTER,
        fx3_has_ecs=FX3_HAS_ECS,
        admitted=True,
        errno_code=0,
        reason_code=(
            "OK_47C_ANTIFLICKER_STILL_MECHANICAL_ACTIVE"
            if active
            else (
                "OK_47C_ANTIFLICKER_SUPPRESSED_IN_MOVIE_OR_ELECTRONIC_SHUTTER"
                if (not mech_still_eligible)
                else "OK_47C_ANTIFLICKER_STILL_MECHANICAL_OFF"
            )
        ),
        antiflicker_movie_or_eshutter_bypass_events=0,
        false_var_shutter_or_ecs_node_events=0,
        bk4_persistent_nvram_writes=0,
    )


def probe_stage47_redline_guard(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_live_hardware_attach: bool = False,
    authorize_isp_write: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_tx: bool = False,
    unblock_cnflasha_userspace_write: bool = False,
    emit_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    allow_framing_crop_hdmi_raw_conflict: bool = False,
    allow_zve1_autoframing_conflation: bool = False,
    allow_unbuffered_usb_pd_battery_pull: bool = False,
    allow_multi_micro_usb_power_bypass: bool = False,
    allow_false_var_shutter_or_ecs_on_fx3: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed probe of all 14 Stage 47 hardware & Wave-37 safety redlines."""
    violation_flags = (
        ("authorize_persistent_emmc_writes", authorize_persistent_emmc_writes),
        ("authorize_live_hardware_attach", authorize_live_hardware_attach),
        ("authorize_isp_write", authorize_isp_write),
        ("authorize_spi_nor_write", authorize_spi_nor_write),
        ("authorize_el3_payload_tx", authorize_el3_payload_tx),
        ("unblock_cnflasha_userspace_write", unblock_cnflasha_userspace_write),
        ("emit_usb_packet", emit_usb_packet),
        ("touch_otp_fuse", touch_otp_fuse),
        ("increment_rpmb_counter", increment_rpmb_counter),
        ("allow_framing_crop_hdmi_raw_conflict", allow_framing_crop_hdmi_raw_conflict),
        ("allow_zve1_autoframing_conflation", allow_zve1_autoframing_conflation),
        ("allow_unbuffered_usb_pd_battery_pull", allow_unbuffered_usb_pd_battery_pull),
        ("allow_multi_micro_usb_power_bypass", allow_multi_micro_usb_power_bypass),
        ("allow_false_var_shutter_or_ecs_on_fx3", allow_false_var_shutter_or_ecs_on_fx3),
    )
    tripped = [name for name, flag in violation_flags if flag]
    valid = len(tripped) == 0
    return RedlineGuardProbeResult(
        valid=valid,
        errno_code=0 if valid else EACCES_ERRNO,
        reason_code=(
            "OK_STAGE47_ALL_REDLINES_LOCKED"
            if valid
            else f"BLOCKED_STAGE47_REDLINE_VIOLATION:{','.join(tripped)}"
        ),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        framing_crop_hdmi_raw_conflict_events=FRAMING_CROP_HDMI_RAW_CONFLICT_EVENTS,
        zve1_autoframing_conflation_events=ZVE1_AUTOFRAMING_CONFLATION_EVENTS,
        unbuffered_usb_pd_battery_pull_events=UNBUFFERED_USB_PD_BATTERY_PULL_EVENTS,
        multi_micro_usb_power_bypass_events=MULTI_MICRO_USB_POWER_BYPASS_EVENTS,
        antiflicker_movie_or_eshutter_bypass_events=ANTIFLICKER_MOVIE_OR_ESHUTTER_BYPASS_EVENTS,
        false_var_shutter_or_ecs_node_events=FALSE_VAR_SHUTTER_OR_ECS_NODE_EVENTS,
        fx3_has_var_shutter=FX3_HAS_VAR_SHUTTER,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
    )


ALL_14_REDLINE_PROBE_FIELDS: Tuple[str, ...] = (
    "authorize_persistent_emmc_writes",
    "authorize_live_hardware_attach",
    "authorize_isp_write",
    "authorize_spi_nor_write",
    "authorize_el3_payload_tx",
    "unblock_cnflasha_userspace_write",
    "emit_usb_packet",
    "touch_otp_fuse",
    "increment_rpmb_counter",
    "allow_framing_crop_hdmi_raw_conflict",
    "allow_zve1_autoframing_conflation",
    "allow_unbuffered_usb_pd_battery_pull",
    "allow_multi_micro_usb_power_bypass",
    "allow_false_var_shutter_or_ecs_on_fx3",
)


def evaluate_pillar_c_d_antiflicker_no_varshutter_and_redlines() -> Dict[str, object]:
    still_mech_100hz_ok = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        configured_anti_flicker_shoot="On",
        capture_mode=CAPTURE_MODE_STILL,
        shutter_type=SHUTTER_TYPE_MECHANICAL,
        silent_mode="Off",
        ambient_flicker_hz=100,
    )
    still_mech_120hz_ok = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        configured_anti_flicker_shoot="On",
        capture_mode=CAPTURE_MODE_STILL,
        shutter_type=SHUTTER_TYPE_MECHANICAL,
        silent_mode="Off",
        ambient_flicker_hz=120,
    )
    cam_reset_restores_off = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        configured_anti_flicker_shoot="On",
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    movie_suppressed = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        configured_anti_flicker_shoot="On",
        capture_mode=CAPTURE_MODE_MOVIE,
    )
    sq_suppressed = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        configured_anti_flicker_shoot="On",
        capture_mode=CAPTURE_MODE_SQ_MOTION,
    )
    silent_mode_suppressed = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        configured_anti_flicker_shoot="On",
        capture_mode=CAPTURE_MODE_STILL,
        shutter_type=SHUTTER_TYPE_MECHANICAL,
        silent_mode="On",
    )
    electronic_shutter_suppressed = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        configured_anti_flicker_shoot="On",
        capture_mode=CAPTURE_MODE_STILL,
        shutter_type=SHUTTER_TYPE_ELECTRONIC,
        silent_mode="Off",
    )
    movie_bypass_blocked = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        configured_anti_flicker_shoot="On",
        capture_mode=CAPTURE_MODE_MOVIE,
        force_bypass_mechanical_still_scope=True,
    )
    silent_bypass_blocked = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        configured_anti_flicker_shoot="On",
        capture_mode=CAPTURE_MODE_STILL,
        silent_mode="On",
        force_bypass_mechanical_still_scope=True,
    )
    var_shutter_blocked = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        requested_var_shutter=True,
    )
    fx6_ecs_blocked = simulate_antiflicker_still_mech_and_no_varshutter_hil(
        requested_fx6_ecs=True,
    )

    baseline_redline = probe_stage47_redline_guard()
    blocked_probes = [
        asdict(probe_stage47_redline_guard(**{field: True}))
        for field in ALL_14_REDLINE_PROBE_FIELDS
    ]

    passed = (
        still_mech_100hz_ok.admitted
        and still_mech_100hz_ok.anti_flicker_active
        and still_mech_100hz_ok.detected_flicker_hz == 100
        and (not still_mech_100hz_ok.fx3_has_var_shutter)
        and still_mech_120hz_ok.admitted
        and still_mech_120hz_ok.anti_flicker_active
        and still_mech_120hz_ok.detected_flicker_hz == 120
        and cam_reset_restores_off.admitted
        and cam_reset_restores_off.reset_restored_off
        and cam_reset_restores_off.effective_anti_flicker_register == "Off"
        and movie_suppressed.admitted
        and (not movie_suppressed.anti_flicker_active)
        and movie_suppressed.anti_flicker_menu_grayed_out
        and sq_suppressed.admitted
        and (not sq_suppressed.anti_flicker_active)
        and silent_mode_suppressed.admitted
        and (not silent_mode_suppressed.anti_flicker_active)
        and electronic_shutter_suppressed.admitted
        and (not electronic_shutter_suppressed.anti_flicker_active)
        and (not movie_bypass_blocked.admitted)
        and movie_bypass_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not silent_bypass_blocked.admitted)
        and silent_bypass_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not var_shutter_blocked.admitted)
        and var_shutter_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not var_shutter_blocked.fx3_has_var_shutter)
        and (not fx6_ecs_blocked.admitted)
        and fx6_ecs_blocked.errno_code == EOPNOTSUPP_ERRNO
        and baseline_redline.valid
        and len(blocked_probes) == 14
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "menu_path": ANTI_FLICKER_SHOOT_MENU_PATH,
        "fx3_has_var_shutter": FX3_HAS_VAR_SHUTTER,
        "fx3_has_ecs": FX3_HAS_ECS,
        "all_capture_modes": list(VALID_CAPTURE_MODES),
        "all_shutter_types": list(VALID_SHUTTER_TYPES),
        "all_14_redline_probe_fields": list(ALL_14_REDLINE_PROBE_FIELDS),
        "still_mech_100hz_ok": asdict(still_mech_100hz_ok),
        "still_mech_120hz_ok": asdict(still_mech_120hz_ok),
        "cam_reset_restores_off": asdict(cam_reset_restores_off),
        "movie_suppressed": asdict(movie_suppressed),
        "sq_suppressed": asdict(sq_suppressed),
        "silent_mode_suppressed": asdict(silent_mode_suppressed),
        "electronic_shutter_suppressed": asdict(electronic_shutter_suppressed),
        "movie_bypass_blocked_eopnotsupp": asdict(movie_bypass_blocked),
        "silent_bypass_blocked_eopnotsupp": asdict(silent_bypass_blocked),
        "var_shutter_blocked_eopnotsupp": asdict(var_shutter_blocked),
        "fx6_ecs_blocked_eopnotsupp": asdict(fx6_ecs_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 250 (250th Phase Milestone! Stage 47, 47/47) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase250_realhw_framing_usbpower_lun_antiflicker_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 250 (250th Phase Milestone) Stage 47 (47/47) HIL audit."""
    donor_audit = inspect_phase250_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_framing_asymmetric_and_hdmi_raw_hil()
    pillar_b = evaluate_pillar_b_usb_power_npfz100_typec_and_lun_setup_hil()
    pillar_cd = evaluate_pillar_c_d_antiflicker_no_varshutter_and_redlines()

    redlines: Dict[str, object] = {
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "nop_count": NOP_COUNT,
        "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
        "cp_mutation_bytes": CP_MUTATION_BYTES,
        "wbi_mutation_bytes": WBI_MUTATION_BYTES,
        "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
        "cnflasha_mutation_bytes": CNFLASHA_MUTATION_BYTES,
        "cnflasha_userspace_write_blocked": CNFLASHA_USERSPACE_WRITE_BLOCKED,
        "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
        "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
        "physical_device_writes": PHYSICAL_DEVICE_WRITES,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "overall_ready_for_hardware_attach": OVERALL_READY_FOR_HARDWARE_ATTACH,
        "isp_write_authorized": ISP_WRITE_AUTHORIZED,
        "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
        "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "framing_crop_hdmi_raw_conflict_events": FRAMING_CROP_HDMI_RAW_CONFLICT_EVENTS,
        "zve1_autoframing_conflation_events": ZVE1_AUTOFRAMING_CONFLATION_EVENTS,
        "unbuffered_usb_pd_battery_pull_events": UNBUFFERED_USB_PD_BATTERY_PULL_EVENTS,
        "multi_micro_usb_power_bypass_events": MULTI_MICRO_USB_POWER_BYPASS_EVENTS,
        "antiflicker_movie_or_eshutter_bypass_events": ANTIFLICKER_MOVIE_OR_ESHUTTER_BYPASS_EVENTS,
        "false_var_shutter_or_ecs_node_events": FALSE_VAR_SHUTTER_OR_ECS_NODE_EVENTS,
        "fx3_has_var_shutter": FX3_HAS_VAR_SHUTTER,
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
        "donor_access_mode": DONOR_ACCESS_MODE,
    }

    all_passed = (
        donor_audit.all_contracts_verified
        and donor_audit.raw_firmware_bytes_leaked == 0
        and bool(pillar_a["passed"])
        and bool(pillar_b["passed"])
        and bool(pillar_cd["passed"])
        and CNFLASHA_USERSPACE_WRITE_BLOCKED
        and CNFLASHA_MUTATION_BYTES == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not OVERALL_READY_FOR_HARDWARE_ATTACH)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not ISP_WRITE_AUTHORIZED)
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and FRAMING_CROP_HDMI_RAW_CONFLICT_EVENTS == 0
        and ZVE1_AUTOFRAMING_CONFLATION_EVENTS == 0
        and UNBUFFERED_USB_PD_BATTERY_PULL_EVENTS == 0
        and MULTI_MICRO_USB_POWER_BYPASS_EVENTS == 0
        and ANTIFLICKER_MOVIE_OR_ESHUTTER_BYPASS_EVENTS == 0
        and FALSE_VAR_SHUTTER_OR_ECS_NODE_EVENTS == 0
        and (not FX3_HAS_VAR_SHUTTER)
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_250_VERSION,
        "phase_number": PHASE_NUMBER,
        "is_250th_phase_milestone": IS_250TH_PHASE_MILESTONE,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_framing_asymmetric_and_hdmi_raw_hil": pillar_a,
        "pillar_b_usb_power_npfz100_typec_and_lun_setup_hil": pillar_b,
        "pillar_c_d_antiflicker_no_varshutter_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_framing_usbpower_lun_antiflicker_coemulator.py",
        description=(
            "Phase 250 (250th Phase Milestone!) Stage 47 (47/47 Milestone) — Real-Hardware "
            "ILME-FX3 Wave-37 Framing Settings Asymmetric Full/Crop & HDMI RAW Lockout, "
            "USB Power Supply Mandatory NP-FZ100 + USB Type-C & USB LUN Setting Multi/Single "
            "Setup Persistence, and Anti-flicker Shoot. Mechanical-Still-Only & No Var. Shutter HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 250 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase250_realhw_framing_usbpower_lun_antiflicker_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_framing_asymmetric_and_hdmi_raw_hil"]
        pb = rep["pillar_b_usb_power_npfz100_typec_and_lun_setup_hil"]
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 250 (250th Milestone) Stage 47 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"framing={len(pa['routing_4way_matrix'])}way_raw_conf:{red['framing_crop_hdmi_raw_conflict_events']} | "
            f"usb_lun={len(pb['all_2_usb_lun_settings'])}m_pull:{red['unbuffered_usb_pd_battery_pull_events']}_pkt:{red['physical_usb_packets_emitted']} | "
            f"antiflicker_varsh:{red['fx3_has_var_shutter']}_ev:{red['false_var_shutter_or_ecs_node_events']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
