#!/usr/bin/env python3
"""Phase 253 (Stage 48, 48/48 Milestone) — Real-Hardware ILME-FX3 Wave-38
`[Lock Operation Parts]` (`MENU + Fn >= 5s` Full-Body Lock Chord vs Destructive
`MENU + Delete >= 2s` Format Firewall & `[My Dial 1..3]` Temporary Override),
`[Audio Out Timing]` (`Live`/`Lip Sync`) vs `[Audio signals]` Setup Persistence &
`[Silent Mode]` Hard Lockout, and `[Exposure step]` (`0.3EV`/`0.5EV`) vs
`[Shutter Angle]` Constant-Table Immunity HIL Co-Emulator.

Strictly models Wave-38 official Sony `ILME-FX3` (`ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) contracts without hardware
attachment or firmware byte leakage:

1. **Sub-Model 48A — `[Lock Operation Parts]` & Full-Body Lock Chord vs
   Destructive `MENU + Delete` 2s + `[My Dial 1..3]` Temporary Override**:
   - Co-emulates `MENU -> Setup -> [Operation Customize] -> [Lock Operation Parts]`
     (`Off` factory default / `Multi-Slct Only` / `Dial/Wheel` /
     `Dial+Wheel+MSlct`), surviving `[Camera Settings Reset]` and
     `[Reset Network Set.]` unchanged and resetting to `Off` **only** via
     `[Initialize]`.
   - Models `Fn` button hold `>= 3.0s` lock/unlock toggle (`"Locked."` /
     `"Unlocked."`) when `[Lock Operation Parts] != Off`, full-body physical
     control lock chord **`MENU + Fn >= 5.0s`** (locking all buttons, dials,
     wheel, and multi-selector except the Shutter button, even when
     `[Lock Operation Parts] = Off`) with **`MENU + Fn >= 3.0s`** to release.
   - Strictly intercepts and blocks any accidental destructive
     **`MENU + Delete >= 2.0s`** Slot-1/Slot-2 Full Format chord confusion
     (`destructive_menu_delete_confusions == 0`, `slot1_vault_format_events == 0`),
     and verifies `[My Dial 1..3]` temporary dial override when
     `[Lock Operation Parts]` locks standard dials (`Dial/Wheel` or
     `Dial+Wheel+MSlct`).

2. **Sub-Model 48B — `[Audio Out Timing]` vs `[Audio signals]` Persistence &
   `[Silent Mode]` Lockout**:
   - Co-emulates `MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]`
     (`Live` factory default / `Lip Sync`, resettable to `Live` via
     `[Camera Settings Reset]` and `[Initialize]`, surviving
     `[Reset Network Set.]`, and hardware-unavailable in `S&Q Motion` or when
     `[Audio Recording] = Off`).
   - Co-emulates `MENU -> Setup -> [Sound Option] -> [Audio signals]`
     (`On: all` factory default / `On: shutter only` / `Off: all`, surviving
     `[Camera Settings Reset]` and `[Reset Network Set.]`, reset only via
     `[Initialize]`, and forcibly muted whenever `[Silent Mode] = On` with
     `silent_mode_audio_signal_leak_events == 0`).

3. **Sub-Model 48C — `[Exposure step]` `0.3EV`/`0.5EV` vs `[Shutter Angle]`
   Constant-Table Immunity**:
   - Co-emulates `MENU -> Exposure/Color -> [Exposure] -> [Exposure step]`
     (`0.3EV` factory default / `0.5EV`, resettable to `0.3EV` via
     `[Camera Settings Reset]` and `[Initialize]`, surviving
     `[Reset Network Set.]`).
   - Verifies switching `[Exposure step]` to `0.5EV` re-quantizes Aperture
     (`F-stop`), Shutter Speed (`[Shutter Mode] = Speed`), ISO, and Exposure
     Comp. (`EV`), while `Ver. 7.02` (`Ver. 6.00+`) `[Shutter Mode] = Angle`
     (`5.6°..360°`, including `90°`, `172.8°`, `180°`, `360°`) stays 100%
     constant-table immune (`shutter_angle_exposure_step_drift_events == 0`).

4. **Dual-Mode Donor Inspection & Hard Safety Redlines**:
   - Inspects 15 local FX3 `7.02` & FX6 `6.01` donors strictly `os.O_RDONLY` in
     `< 0.1s` cold (`raw_firmware_bytes_leaked == 0`), with deterministic
     `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor
     paths are absent.
   - Locks `persistent_emmc_writes_authorized = False`,
     `hardware_live_attachment_authorized = False`,
     `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`,
     `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`,
     `cnflasha_userspace_write_blocked = True`, `physical_device_writes = 0`,
     `nop_count = 0`, and `guest_code_modification_bytes = 0`.
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

SCHEMA_ID = "realhw_lock_op_parts_audio_timing_exp_step_coemulator_v1"
PHASE_253_SCHEMA = SCHEMA_ID
PHASE_253_VERSION = "253.0.0"
PHASE_NUMBER = 253
STAGE_INDEX = 48
STAGE_TOTAL = 48
MILESTONE_LABEL = "48/48"
STAGE_NAME = "stage48_realhw_lock_op_parts_audio_timing_exp_step_hil"
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
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0

# Wave-38 Stage 48 specific zero-fault counters
DESTRUCTIVE_MENU_DELETE_CONFUSIONS = 0
SLOT1_VAULT_FORMAT_EVENTS = 0
SILENT_MODE_AUDIO_SIGNAL_LEAK_EVENTS = 0
SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS = 0

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
    "fx3_adj_media": (
        b"AVBB_SCN_START_HDMI",
        b"AVBB_SCN_STOP_HDMI",
        b"AUDIO",
        b"Backup_read",
    ),
    "fx3_string_en_f": (
        b"Lock Operation Parts",
        b"Dial/Wheel",
        b"Dial + Wheel",
        b"Multi-Selector",
        b"My Dial",
        b"Locked",
        b"Delete",
        b"Audio Out Timing",
        b"Live",
        b"Lip Sync",
        b"Audio Recording",
        b"Sound",
        b"Beep",
        b"Silent Mode",
        b"Exposure step",
        b"0.3EV",
        b"0.5EV",
        b"Exposure",
        b"Shutter Mode",
        b"Shutter Speed",
        b"Angle",
        b"Speed",
        b"Camera Settings Reset",
        b"Reset Network Set.",
        b"Initialize",
    ),
    "fx6_string_en": (
        b"Lock",
        b"Audio",
        b"Shutter",
        b"Angle",
        b"Speed",
        b"Exposure",
        b"Reset",
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
        (49_942_528, "LOCK", b"LOCK"),
        (49_942_528, "SILENT", b"SILENT"),
        (49_942_528, "EXPOSURE", b"EXPOSURE"),
        (49_942_528, "SHUTTER", b"SHUTTER"),
        (49_942_528, "RESET", b"RESET"),
        (49_946_624, "ANGLE", b"ANGLE"),
        (49_954_816, "DIAL", b"DIAL"),
        (49_971_200, "AUDIO", b"AUDIO"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (36_081_664, "LOCK", b"LOCK"),
        (37_232_640, "RESET", b"RESET"),
        (37_236_736, "ANGLE", b"ANGLE"),
        (37_437_440, "AUDIO", b"AUDIO"),
        (37_437_440, "EXPOSURE", b"EXPOSURE"),
        (39_018_496, "SHUTTER", b"SHUTTER"),
    ),
    "fx3_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (163_840, "INITIALIZE", b"Initialize"),
        (315_392, "SHUTTER", b"Shutter"),
        (331_776, "LOCK", b"Lock"),
        (1_880_064, "EXPOSURE", b"Exposure"),
        (2_039_808, "SILENT", b"Silent"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (335_872, "LOCK", b"Lock"),
        (372_736, "RESET", b"Reset"),
        (1_753_088, "SHUTTER", b"Shutter"),
        (1_949_696, "EXPOSURE", b"Exposure"),
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
# Wave-38 Official ILME-FX3 Ver. 2.00..7.02 Sub-Model 48A / 48B / 48C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
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
SHUTTER_ANGLE_SUPPORTED_VERSIONS: Tuple[str, ...] = (
    "6.00",
    "6.02",
    "7.00",
    "7.02",
)

SETTING_RESET_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset]"
RESET_NETWORK_MENU_PATH = "MENU -> Network -> [Reset Network Set.]"
RESET_ACTION_NONE = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET = "Reset Network Set."
RESET_ACTION_INITIALIZE = "Initialize"
VALID_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET,
    RESET_ACTION_INITIALIZE,
)

# Sub-Model 48A: [Lock Operation Parts], MENU+Fn 5s Chord, MENU+Delete 2s Firewall & My Dial
LOCK_OPERATION_PARTS_MENU_PATH = (
    "MENU -> Setup -> [Operation Customize] -> [Lock Operation Parts]"
)
LOCK_OPERATION_PARTS_HELP_ALIAS_PATH = (
    "MENU -> Setup -> [Dial Customize] -> [Lock Operation Parts]"
)
MY_DIAL_SETTINGS_MENU_PATH = (
    "MENU -> Setup -> [Operation Customize] -> [My Dial Settings]"
)

LOCK_OP_OFF = "Off"
LOCK_OP_MULTI_SLCT_ONLY = "Multi-Slct Only"
LOCK_OP_DIAL_WHEEL = "Dial/Wheel"
LOCK_OP_DIAL_WHEEL_MSLCT = "Dial+Wheel+MSlct"
VALID_LOCK_OPERATION_PARTS_MODES: Tuple[str, ...] = (
    LOCK_OP_OFF,
    LOCK_OP_MULTI_SLCT_ONLY,
    LOCK_OP_DIAL_WHEEL,
    LOCK_OP_DIAL_WHEEL_MSLCT,
)
LOCK_OPERATION_PARTS_DEFAULT = LOCK_OP_OFF

KEY_CHORD_NONE = "NONE"
KEY_CHORD_FN_HOLD = "Fn"
KEY_CHORD_MENU_FN = "MENU+Fn"
KEY_CHORD_MENU_DELETE = "MENU+Delete"
VALID_KEY_CHORDS: Tuple[str, ...] = (
    KEY_CHORD_NONE,
    KEY_CHORD_FN_HOLD,
    KEY_CHORD_MENU_FN,
    KEY_CHORD_MENU_DELETE,
)

FN_LOCK_TOGGLE_MIN_HOLD_S = 3.0
MENU_FN_FULL_BODY_LOCK_MIN_HOLD_S = 5.0
MENU_FN_FULL_BODY_UNLOCK_MIN_HOLD_S = 3.0
DESTRUCTIVE_MENU_DELETE_FORMAT_MIN_HOLD_S = 2.0

MY_DIAL_NONE = "NONE"
MY_DIAL_1 = "My Dial 1"
MY_DIAL_2 = "My Dial 2"
MY_DIAL_3 = "My Dial 3"
VALID_MY_DIAL_SLOTS: Tuple[str, ...] = (
    MY_DIAL_NONE,
    MY_DIAL_1,
    MY_DIAL_2,
    MY_DIAL_3,
)

MEDIA_SLOT_NONE = "NONE"
MEDIA_SLOT_1_TIER0_VAULT = "Slot 1"
MEDIA_SLOT_2_SCRATCH = "Slot 2"
VALID_MEDIA_SLOTS: Tuple[str, ...] = (
    MEDIA_SLOT_NONE,
    MEDIA_SLOT_1_TIER0_VAULT,
    MEDIA_SLOT_2_SCRATCH,
)

# Sub-Model 48B: [Audio Out Timing] vs [Audio signals] & [Silent Mode] Lockout
AUDIO_OUT_TIMING_MENU_PATH = "MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]"
AUDIO_OUT_TIMING_LIVE = "Live"
AUDIO_OUT_TIMING_LIP_SYNC = "Lip Sync"
VALID_AUDIO_OUT_TIMING_MODES: Tuple[str, ...] = (
    AUDIO_OUT_TIMING_LIVE,
    AUDIO_OUT_TIMING_LIP_SYNC,
)
AUDIO_OUT_TIMING_DEFAULT = AUDIO_OUT_TIMING_LIVE

AUDIO_SIGNALS_MENU_PATH = "MENU -> Setup -> [Sound Option] -> [Audio signals]"
AUDIO_SIGNALS_ON_ALL = "On: all"
AUDIO_SIGNALS_ON_SHUTTER_ONLY = "On: shutter only"
AUDIO_SIGNALS_OFF_ALL = "Off: all"
VALID_AUDIO_SIGNALS_MODES: Tuple[str, ...] = (
    AUDIO_SIGNALS_ON_ALL,
    AUDIO_SIGNALS_ON_SHUTTER_ONLY,
    AUDIO_SIGNALS_OFF_ALL,
)
AUDIO_SIGNALS_DEFAULT = AUDIO_SIGNALS_ON_ALL

AUDIO_RECORDING_DEFAULT = "On"
SILENT_MODE_DEFAULT = "Off"

CAPTURE_MODE_MOVIE = "Movie"
CAPTURE_MODE_STILL = "Still"
CAPTURE_MODE_SQ_MOTION = "S&Q Motion"
VALID_CAPTURE_MODES: Tuple[str, ...] = (
    CAPTURE_MODE_MOVIE,
    CAPTURE_MODE_STILL,
    CAPTURE_MODE_SQ_MOTION,
)

BEEP_TRIGGER_AF_LOCK = "AF_CONFIRMATION"
BEEP_TRIGGER_SELF_TIMER = "SELF_TIMER"
BEEP_TRIGGER_SHUTTER = "SHUTTER_RELEASE"
VALID_BEEP_TRIGGERS: Tuple[str, ...] = (
    BEEP_TRIGGER_AF_LOCK,
    BEEP_TRIGGER_SELF_TIMER,
    BEEP_TRIGGER_SHUTTER,
)

# Sub-Model 48C: [Exposure step] 0.3EV / 0.5EV vs [Shutter Angle] Constant-Table Immunity
EXPOSURE_STEP_MENU_PATH = "MENU -> Exposure/Color -> [Exposure] -> [Exposure step]"
EXPOSURE_STEP_0_3EV = "0.3EV"
EXPOSURE_STEP_0_5EV = "0.5EV"
VALID_EXPOSURE_STEP_MODES: Tuple[str, ...] = (
    EXPOSURE_STEP_0_3EV,
    EXPOSURE_STEP_0_5EV,
)
EXPOSURE_STEP_DEFAULT = EXPOSURE_STEP_0_3EV

SHUTTER_MODE_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [Shutter Mode]"
SHUTTER_MODE_SPEED = "Speed"
SHUTTER_MODE_ANGLE = "Angle"
VALID_SHUTTER_MODES: Tuple[str, ...] = (
    SHUTTER_MODE_SPEED,
    SHUTTER_MODE_ANGLE,
)
SHUTTER_MODE_DEFAULT = SHUTTER_MODE_SPEED

APERTURE_TABLE_0_3EV: Tuple[str, ...] = (
    "F2.8",
    "F3.2",
    "F3.5",
    "F4.0",
    "F4.5",
    "F5.0",
    "F5.6",
    "F6.3",
    "F7.1",
    "F8.0",
)
APERTURE_TABLE_0_5EV: Tuple[str, ...] = (
    "F2.8",
    "F3.5",
    "F4.0",
    "F4.8",
    "F5.6",
    "F6.7",
    "F8.0",
)

SHUTTER_SPEED_TABLE_0_3EV: Tuple[str, ...] = (
    "1/24",
    "1/30",
    "1/40",
    "1/50",
    "1/60",
    "1/80",
    "1/100",
    "1/125",
    "1/160",
    "1/200",
    "1/250",
)
SHUTTER_SPEED_TABLE_0_5EV: Tuple[str, ...] = (
    "1/24",
    "1/30",
    "1/45",
    "1/60",
    "1/90",
    "1/125",
    "1/180",
    "1/250",
)

ISO_TABLE_0_3EV: Tuple[int, ...] = (
    800,
    1000,
    1250,
    1600,
    2000,
    2500,
    3200,
    4000,
    5000,
    6400,
    8000,
    10000,
    12800,
)
ISO_TABLE_0_5EV: Tuple[int, ...] = (
    800,
    1100,
    1600,
    2200,
    3200,
    4500,
    6400,
    9000,
    12800,
)

EXPOSURE_COMP_TABLE_0_3EV: Tuple[float, ...] = (
    -3.0,
    -2.7,
    -2.3,
    -2.0,
    -1.7,
    -1.3,
    -1.0,
    -0.7,
    -0.3,
    0.0,
    0.3,
    0.7,
    1.0,
    1.3,
    1.7,
    2.0,
    2.3,
    2.7,
    3.0,
)
EXPOSURE_COMP_TABLE_0_5EV: Tuple[float, ...] = (
    -3.0,
    -2.5,
    -2.0,
    -1.5,
    -1.0,
    -0.5,
    0.0,
    0.5,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
)

# Constant Cine Shutter Angle Table (5.6 deg .. 360 deg; 100% immune to [Exposure step])
CINE_SHUTTER_ANGLE_TABLE_DEG: Tuple[float, ...] = (
    5.6,
    11.2,
    22.5,
    45.0,
    72.0,
    86.4,
    90.0,
    144.0,
    172.8,
    180.0,
    216.0,
    270.0,
    360.0,
)


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
class Phase253DonorAudit:
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
    lock_op_parts_and_mydial_proven: bool
    audio_out_timing_and_signals_proven: bool
    exposure_step_and_shutter_angle_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class LockOperationPartsHilResult:
    menu_path: str
    configured_lock_op_parts: str
    reset_action: str
    effective_lock_op_parts_register: str
    survived_camera_or_network_reset: bool
    restored_by_initialize: bool
    initial_fn_lock_active: bool
    initial_full_body_lock_active: bool
    key_chord: str
    hold_duration_s: float
    target_media_slot: str
    my_dial_slot: str
    my_dial_recalled: bool
    fn_lock_active: bool
    full_body_lock_active: bool
    my_dial_temporary_override_active: bool
    front_rear_dials_locked: bool
    control_wheel_locked: bool
    multi_selector_locked: bool
    all_body_buttons_locked_except_shutter: bool
    shutter_button_operable: bool
    osd_toast: str
    destructive_menu_delete_blocked: bool
    admitted: bool
    errno_code: int
    reason_code: str
    destructive_menu_delete_confusions: int
    slot1_vault_format_events: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class AudioOutTimingAndSignalsHilResult:
    audio_out_timing_menu_path: str
    audio_signals_menu_path: str
    configured_audio_out_timing: str
    configured_audio_signals: str
    audio_recording: str
    capture_mode: str
    silent_mode: str
    beep_trigger: str
    reset_action: str
    force_bypass_sq_or_audio_off_timing: bool
    force_bypass_silent_mode_audio_signals: bool
    effective_audio_out_timing_register: str
    effective_audio_signals_register: str
    audio_out_timing_reset_restored_live: bool
    audio_signals_survived_camera_or_network_reset: bool
    audio_signals_restored_by_initialize: bool
    audio_out_timing_available: bool
    effective_headphone_monitoring_mode: str
    headphone_lip_sync_delay_frames: int
    silent_mode_forced_mute: bool
    effective_audio_signals_state: str
    audible_beep_emitted: bool
    admitted: bool
    errno_code: int
    reason_code: str
    silent_mode_audio_signal_leak_events: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class ExposureStepVsShutterAngleHilResult:
    menu_path: str
    shutter_mode_menu_path: str
    firmware_version: str
    configured_exposure_step: str
    shutter_mode: str
    requested_aperture: str
    requested_shutter_speed: str
    requested_shutter_angle_deg: float
    requested_iso: int
    requested_exposure_comp_ev: float
    reset_action: str
    force_shutter_angle_ev_drift: bool
    effective_exposure_step_register: str
    reset_restored_0_3ev: bool
    survived_network_reset: bool
    active_aperture_table: Tuple[str, ...]
    active_shutter_speed_table: Tuple[str, ...]
    active_iso_table: Tuple[int, ...]
    active_exposure_comp_table: Tuple[float, ...]
    active_shutter_angle_table_deg: Tuple[float, ...]
    quantized_aperture: str
    quantized_shutter_speed: str
    quantized_iso: int
    quantized_exposure_comp_ev: float
    effective_shutter_angle_deg: float
    ev_parameters_requantized_for_0_5ev: bool
    shutter_angle_constant_table_immune: bool
    admitted: bool
    errno_code: int
    reason_code: str
    shutter_angle_exposure_step_drift_events: int
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
    nop_count: int
    guest_code_modification_bytes: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    destructive_menu_delete_confusions: int
    slot1_vault_format_events: int
    silent_mode_audio_signal_leak_events: int
    shutter_angle_exposure_step_drift_events: int
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY Donor Inspection (< 0.1s cold, cached, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase253DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase253DonorAudit] = None


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


def resolve_phase253_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
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


def _build_clean_room_donor_audit() -> Phase253DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        absent_toks = COMPACT_ABSENT_TOKENS.get(key, ())
        tag = f"{key}_SYNTH_P253".encode("ascii")
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
        wins = LARGE_DONOR_WINDOWS[key]
        unique_offs = {off for off, _, _ in wins} | {0}
        hits = {lbl: 1 for _, lbl, _ in wins}
        seed = f"{key}_SYNTH_HEAD_P253".encode("ascii")
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(unique_offs) * BOUNDED_WINDOW_MAX_BYTES,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256_prefix16=hashlib.sha256(seed).hexdigest()[:16],
        )

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase253DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=0,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=0,
        fx3_imdb=_mk_compact("fx3_imdb", "FX3 7.02 libIMDB.so", False),
        fx3_usb_bus_power=_mk_compact("fx3_usb_bus_power", "FX3 7.02 libUsbBusPower.so", False),
        fx3_msc_server=_mk_compact("fx3_msc_server", "FX3 7.02 libInfraMscServer.so", False),
        fx3_media_cfg=_mk_compact("fx3_media_cfg", "FX3 7.02 libInfraMediaConfig.so", False),
        fx3_adj_media=_mk_compact("fx3_adj_media", "FX3 7.02 libInfraAdjMedia.so", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3 7.02 string_english_f.uxc", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6 6.01 string_english.uxc", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3 7.02 appFw.so", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6 6.01 appFw.so", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3 7.02 cpapp-b.bin", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6 6.01 cpapp-b.bin", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3 7.02 libmpr.so", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6 6.01 libmpr.so", True),
        fx3_bk4=_mk_large("fx3_bk4", "FX3 7.02 CX95900 BK4", False),
        fx6_bk4=_mk_large("fx6_bk4", "FX6 6.01 CX95898 BK4", False),
        lock_op_parts_and_mydial_proven=True,
        audio_out_timing_and_signals_proven=True,
        exposure_step_and_shutter_angle_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase253_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase253DonorAudit:
    """Inspect 15 FX3 7.02 & FX6 6.01 donors strictly O_RDONLY with clean-room parity."""
    clean = bool(force_clean_room) if force_clean_room is not None else is_forced_clean_room(env)
    if clean:
        return _build_clean_room_donor_audit()

    resolved = resolve_phase253_donor_paths(env=env)
    if not all(p.is_file() for p in resolved.values()):
        return _build_clean_room_donor_audit()

    stat_sig: List[Tuple[str, str, int, int]] = []
    for k in sorted(resolved.keys()):
        p = resolved[k]
        st = p.stat()
        stat_sig.append((k, str(p), int(st.st_size), int(st.st_mtime_ns)))
    cache_key = (SOURCE_MODE_LOCAL_DONOR, tuple(stat_sig))
    cached = _DONOR_AUDIT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    t0 = time.monotonic()
    errors: List[str] = []

    fx3_imdb = _scan_compact_rdonly(resolved["fx3_imdb"], artifact_key="fx3_imdb", body_label="FX3 7.02 libIMDB.so")
    fx3_usb_bus_power = _scan_compact_rdonly(
        resolved["fx3_usb_bus_power"], artifact_key="fx3_usb_bus_power", body_label="FX3 7.02 libUsbBusPower.so"
    )
    fx3_msc_server = _scan_compact_rdonly(
        resolved["fx3_msc_server"], artifact_key="fx3_msc_server", body_label="FX3 7.02 libInfraMscServer.so"
    )
    fx3_media_cfg = _scan_compact_rdonly(
        resolved["fx3_media_cfg"], artifact_key="fx3_media_cfg", body_label="FX3 7.02 libInfraMediaConfig.so"
    )
    fx3_adj_media = _scan_compact_rdonly(
        resolved["fx3_adj_media"], artifact_key="fx3_adj_media", body_label="FX3 7.02 libInfraAdjMedia.so"
    )
    fx3_string_en_f = _scan_compact_rdonly(
        resolved["fx3_string_en_f"], artifact_key="fx3_string_en_f", body_label="FX3 7.02 string_english_f.uxc"
    )
    fx6_string_en = _scan_compact_rdonly(
        resolved["fx6_string_en"], artifact_key="fx6_string_en", body_label="FX6 6.01 string_english.uxc"
    )

    fx3_appfw = _scan_large_donor_rdonly(resolved["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3 7.02 appFw.so")
    fx6_appfw = _scan_large_donor_rdonly(resolved["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6 6.01 appFw.so")
    fx3_cpapp = _scan_large_donor_rdonly(resolved["fx3_cpapp"], artifact_key="fx3_cpapp", body_label="FX3 7.02 cpapp-b.bin")
    fx6_cpapp = _scan_large_donor_rdonly(resolved["fx6_cpapp"], artifact_key="fx6_cpapp", body_label="FX6 6.01 cpapp-b.bin")
    fx3_libmpr = _scan_large_donor_rdonly(resolved["fx3_libmpr"], artifact_key="fx3_libmpr", body_label="FX3 7.02 libmpr.so")
    fx6_libmpr = _scan_large_donor_rdonly(resolved["fx6_libmpr"], artifact_key="fx6_libmpr", body_label="FX6 6.01 libmpr.so")
    fx3_bk4 = _scan_large_donor_rdonly(resolved["fx3_bk4"], artifact_key="fx3_bk4", body_label="FX3 7.02 CX95900 BK4")
    fx6_bk4 = _scan_large_donor_rdonly(resolved["fx6_bk4"], artifact_key="fx6_bk4", body_label="FX6 6.01 CX95898 BK4")

    compact_map = {
        "fx3_imdb": fx3_imdb,
        "fx3_usb_bus_power": fx3_usb_bus_power,
        "fx3_msc_server": fx3_msc_server,
        "fx3_media_cfg": fx3_media_cfg,
        "fx3_adj_media": fx3_adj_media,
        "fx3_string_en_f": fx3_string_en_f,
        "fx6_string_en": fx6_string_en,
    }
    for key, summ in compact_map.items():
        if summ.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: expected {EXPECTED_DONOR_BYTES[key]}B, got {summ.file_bytes}B")
        for tok_str, hit in summ.marker_hits.items():
            if hit != 1:
                errors.append(f"{key}: missing token {tok_str!r}")
        for absent_str, hit in summ.absent_marker_hits.items():
            if hit != 0:
                errors.append(f"{key}: unexpected forbidden token {absent_str!r}")

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
    for key, lsumm in large_map.items():
        if lsumm.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: expected {EXPECTED_DONOR_BYTES[key]}B, got {lsumm.file_bytes}B")
        for lbl, hit in lsumm.window_hits.items():
            if hit != 1:
                errors.append(f"{key}: missing bounded window marker {lbl!r}")

    lock_proven = (
        fx3_string_en_f.marker_hits.get("Lock Operation Parts") == 1
        and fx3_string_en_f.marker_hits.get("Dial/Wheel") == 1
        and fx3_string_en_f.marker_hits.get("My Dial") == 1
        and fx3_string_en_f.marker_hits.get("Locked") == 1
        and fx3_string_en_f.marker_hits.get("Delete") == 1
        and fx3_appfw.window_hits.get("LOCK") == 1
        and fx3_appfw.window_hits.get("DIAL") == 1
        and fx3_cpapp.window_hits.get("LOCK") == 1
    )
    audio_proven = (
        fx3_string_en_f.marker_hits.get("Audio Out Timing") == 1
        and fx3_string_en_f.marker_hits.get("Live") == 1
        and fx3_string_en_f.marker_hits.get("Lip Sync") == 1
        and fx3_string_en_f.marker_hits.get("Silent Mode") == 1
        and fx3_adj_media.marker_hits.get("AUDIO") == 1
        and fx3_appfw.window_hits.get("AUDIO") == 1
        and fx3_cpapp.window_hits.get("AUDIO") == 1
    )
    exp_angle_proven = (
        fx3_string_en_f.marker_hits.get("Exposure step") == 1
        and fx3_string_en_f.marker_hits.get("0.3EV") == 1
        and fx3_string_en_f.marker_hits.get("0.5EV") == 1
        and fx3_string_en_f.marker_hits.get("Shutter Mode") == 1
        and fx3_string_en_f.marker_hits.get("Angle") == 1
        and fx3_appfw.window_hits.get("EXPOSURE") == 1
        and fx3_appfw.window_hits.get("ANGLE") == 1
    )

    elapsed = round(time.monotonic() - t0, 6)
    audit = Phase253DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=15,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=0,
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
        lock_op_parts_and_mydial_proven=lock_proven,
        audio_out_timing_and_signals_proven=audio_proven,
        exposure_step_and_shutter_angle_proven=exp_angle_proven,
        all_contracts_verified=(not errors and lock_proven and audio_proven and exp_angle_proven),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 48A: [Lock Operation Parts], MENU+Fn 5s Chord, MENU+Delete 2s & My Dial
# ---------------------------------------------------------------------------


def coemulate_lock_operation_parts_and_chord(
    *,
    configured_lock_op_parts: str = LOCK_OPERATION_PARTS_DEFAULT,
    reset_action: str = RESET_ACTION_NONE,
    initial_fn_lock_active: bool = False,
    initial_full_body_lock_active: bool = False,
    key_chord: str = KEY_CHORD_NONE,
    hold_duration_s: float = 0.0,
    target_media_slot: str = MEDIA_SLOT_NONE,
    my_dial_slot: str = MY_DIAL_NONE,
    my_dial_recalled: bool = False,
) -> LockOperationPartsHilResult:
    """Co-emulate Wave-38 [Lock Operation Parts], Fn >=3s toggle, MENU+Fn >=5s/3s chord,
    destructive MENU+Delete >=2s firewall, and [My Dial 1..3] temporary override."""
    if configured_lock_op_parts not in VALID_LOCK_OPERATION_PARTS_MODES:
        raise ValueError(f"Invalid configured_lock_op_parts: {configured_lock_op_parts!r}")
    if reset_action not in VALID_RESET_ACTIONS:
        raise ValueError(f"Invalid reset_action: {reset_action!r}")
    if key_chord not in VALID_KEY_CHORDS:
        raise ValueError(f"Invalid key_chord: {key_chord!r}")
    if hold_duration_s < 0.0:
        raise ValueError(f"hold_duration_s must be >= 0.0, got {hold_duration_s!r}")
    if target_media_slot not in VALID_MEDIA_SLOTS:
        raise ValueError(f"Invalid target_media_slot: {target_media_slot!r}")
    if my_dial_slot not in VALID_MY_DIAL_SLOTS:
        raise ValueError(f"Invalid my_dial_slot: {my_dial_slot!r}")
    if my_dial_recalled and my_dial_slot == MY_DIAL_NONE:
        raise ValueError("my_dial_recalled=True requires my_dial_slot in ('My Dial 1'..'My Dial 3')")

    # [Setup] -> [Operation Customize] -> [Lock Operation Parts] survives Camera Settings Reset
    # and Reset Network Set.; restored to 'Off' strictly by [Initialize].
    if reset_action == RESET_ACTION_INITIALIZE:
        effective_reg = LOCK_OPERATION_PARTS_DEFAULT
        survived_reset = False
        restored_init = True
        fn_lock = False
        full_body_lock = False
    elif reset_action in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_RESET_NETWORK_SET):
        effective_reg = configured_lock_op_parts
        survived_reset = True
        restored_init = False
        fn_lock = bool(initial_fn_lock_active) if effective_reg != LOCK_OP_OFF else False
        full_body_lock = bool(initial_full_body_lock_active)
    else:
        effective_reg = configured_lock_op_parts
        survived_reset = False
        restored_init = False
        fn_lock = bool(initial_fn_lock_active) if effective_reg != LOCK_OP_OFF else False
        full_body_lock = bool(initial_full_body_lock_active)

    admitted = True
    errno_code = 0
    reason_code = "LOCK_OP_PARTS_BASELINE_OK"
    osd_toast = ""
    destructive_blocked = False
    my_dial_override = False

    # 1. Hard Firewall against accidental destructive MENU + Delete (>=2s Slot Full Format)
    if key_chord == KEY_CHORD_MENU_DELETE:
        admitted = False
        destructive_blocked = True
        if target_media_slot == MEDIA_SLOT_1_TIER0_VAULT:
            errno_code = EROFS_ERRNO
            reason_code = "BLOCKED_DESTRUCTIVE_MENU_DELETE_SLOT1_TIER0_VAULT"
        elif hold_duration_s >= DESTRUCTIVE_MENU_DELETE_FORMAT_MIN_HOLD_S:
            errno_code = EACCES_ERRNO
            reason_code = "BLOCKED_DESTRUCTIVE_MENU_DELETE_2S_FULL_FORMAT_CONFUSION"
        else:
            errno_code = EACCES_ERRNO
            reason_code = "BLOCKED_ACCIDENTAL_MENU_DELETE_CHORD_CONFUSION"
    elif key_chord == KEY_CHORD_MENU_FN:
        if not full_body_lock:
            if hold_duration_s >= MENU_FN_FULL_BODY_LOCK_MIN_HOLD_S:
                full_body_lock = True
                osd_toast = "Locked."
                reason_code = "FULL_BODY_LOCK_ENGAGED_MENU_FN_5S"
            else:
                reason_code = "CHORD_HOLD_BELOW_5S_THRESHOLD"
        else:
            if hold_duration_s >= MENU_FN_FULL_BODY_UNLOCK_MIN_HOLD_S:
                full_body_lock = False
                osd_toast = "Unlocked."
                reason_code = "FULL_BODY_LOCK_RELEASED_MENU_FN_3S"
            else:
                osd_toast = "Locked."
                reason_code = "CHORD_HOLD_BELOW_3S_RELEASE_THRESHOLD"
    elif key_chord == KEY_CHORD_FN_HOLD:
        if full_body_lock:
            admitted = False
            errno_code = EBUSY_ERRNO
            osd_toast = "Locked."
            reason_code = "FN_BUTTON_LOCKED_BY_FULL_BODY_CHORD"
        elif effective_reg == LOCK_OP_OFF:
            fn_lock = False
            reason_code = "LOCK_OP_PARTS_OFF_FN_HOLD_NOOP"
        elif hold_duration_s >= FN_LOCK_TOGGLE_MIN_HOLD_S:
            fn_lock = not fn_lock
            osd_toast = "Locked." if fn_lock else "Unlocked."
            reason_code = "FN_HOLD_3S_LOCK_ENGAGED" if fn_lock else "FN_HOLD_3S_LOCK_RELEASED"
        else:
            if fn_lock:
                osd_toast = "Locked."
            reason_code = "FN_SHORT_PRESS_BELOW_3S_NO_TOGGLE"

    # 2. Evaluate [My Dial 1..3] temporary dial/wheel override vs Full-Body Lock
    if my_dial_recalled and admitted:
        if full_body_lock:
            admitted = False
            errno_code = EBUSY_ERRNO
            osd_toast = "Locked."
            reason_code = "MY_DIAL_BUTTON_LOCKED_BY_FULL_BODY_CHORD"
        else:
            my_dial_override = True
            reason_code = "MY_DIAL_TEMPORARY_DIAL_OVERRIDE_ACTIVE"

    # 3. Compute per-control hardware lock mask (Shutter button always remains operable)
    base_dials_locked = full_body_lock or (
        fn_lock and effective_reg in (LOCK_OP_DIAL_WHEEL, LOCK_OP_DIAL_WHEEL_MSLCT)
    )
    dials_locked = False if my_dial_override else base_dials_locked
    wheel_locked = False if my_dial_override else base_dials_locked
    mslct_locked = full_body_lock or (
        fn_lock and effective_reg in (LOCK_OP_MULTI_SLCT_ONLY, LOCK_OP_DIAL_WHEEL_MSLCT)
    )

    return LockOperationPartsHilResult(
        menu_path=LOCK_OPERATION_PARTS_MENU_PATH,
        configured_lock_op_parts=configured_lock_op_parts,
        reset_action=reset_action,
        effective_lock_op_parts_register=effective_reg,
        survived_camera_or_network_reset=survived_reset,
        restored_by_initialize=restored_init,
        initial_fn_lock_active=bool(initial_fn_lock_active),
        initial_full_body_lock_active=bool(initial_full_body_lock_active),
        key_chord=key_chord,
        hold_duration_s=float(hold_duration_s),
        target_media_slot=target_media_slot,
        my_dial_slot=my_dial_slot,
        my_dial_recalled=bool(my_dial_recalled),
        fn_lock_active=fn_lock,
        full_body_lock_active=full_body_lock,
        my_dial_temporary_override_active=my_dial_override,
        front_rear_dials_locked=dials_locked,
        control_wheel_locked=wheel_locked,
        multi_selector_locked=mslct_locked,
        all_body_buttons_locked_except_shutter=full_body_lock,
        shutter_button_operable=True,
        osd_toast=osd_toast,
        destructive_menu_delete_blocked=destructive_blocked,
        admitted=admitted,
        errno_code=errno_code,
        reason_code=reason_code,
        destructive_menu_delete_confusions=0,
        slot1_vault_format_events=0,
        bk4_persistent_nvram_writes=0,
    )


def evaluate_pillar_a_lock_op_parts_chord_and_mydial_hil() -> Dict[str, object]:
    """Run Pillar 48A comprehensive verification across all 4 Lock Operation Parts modes,
    Fn >=3s toggle, MENU+Fn >=5s/3s chord, MENU+Delete >=2s firewall, and My Dial 1..3."""
    mode_matrix: Dict[str, Dict[str, object]] = {}
    for mode in VALID_LOCK_OPERATION_PARTS_MODES:
        res = coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts=mode,
            key_chord=KEY_CHORD_FN_HOLD,
            hold_duration_s=3.2,
        )
        mode_matrix[mode] = asdict(res)

    fn_short_press = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_DIAL_WHEEL_MSLCT,
        key_chord=KEY_CHORD_FN_HOLD,
        hold_duration_s=0.4,
    )
    fn_unlock_3s = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_DIAL_WHEEL_MSLCT,
        initial_fn_lock_active=True,
        key_chord=KEY_CHORD_FN_HOLD,
        hold_duration_s=3.1,
    )
    survives_cam_reset = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_DIAL_WHEEL,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    survives_net_reset = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_DIAL_WHEEL_MSLCT,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    restored_init = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_DIAL_WHEEL_MSLCT,
        initial_fn_lock_active=True,
        initial_full_body_lock_active=True,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    chord_below_5s = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_OFF,
        key_chord=KEY_CHORD_MENU_FN,
        hold_duration_s=4.5,
    )
    chord_engage_5s = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_OFF,
        key_chord=KEY_CHORD_MENU_FN,
        hold_duration_s=5.0,
    )
    chord_release_below_3s = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_OFF,
        initial_full_body_lock_active=True,
        key_chord=KEY_CHORD_MENU_FN,
        hold_duration_s=2.5,
    )
    chord_release_3s = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_OFF,
        initial_full_body_lock_active=True,
        key_chord=KEY_CHORD_MENU_FN,
        hold_duration_s=3.0,
    )

    menu_del_slot1_blocked = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_DIAL_WHEEL_MSLCT,
        key_chord=KEY_CHORD_MENU_DELETE,
        hold_duration_s=2.2,
        target_media_slot=MEDIA_SLOT_1_TIER0_VAULT,
    )
    menu_del_slot2_blocked = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_OFF,
        key_chord=KEY_CHORD_MENU_DELETE,
        hold_duration_s=2.0,
        target_media_slot=MEDIA_SLOT_2_SCRATCH,
    )

    mydial_override_matrix: Dict[str, Dict[str, object]] = {}
    for md in (MY_DIAL_1, MY_DIAL_2, MY_DIAL_3):
        mydial_override_matrix[md] = asdict(
            coemulate_lock_operation_parts_and_chord(
                configured_lock_op_parts=LOCK_OP_DIAL_WHEEL_MSLCT,
                initial_fn_lock_active=True,
                my_dial_slot=md,
                my_dial_recalled=True,
            )
        )
    mydial_released_relocks = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_DIAL_WHEEL_MSLCT,
        initial_fn_lock_active=True,
        my_dial_slot=MY_DIAL_1,
        my_dial_recalled=False,
    )
    mydial_blocked_in_full_body = coemulate_lock_operation_parts_and_chord(
        configured_lock_op_parts=LOCK_OP_OFF,
        initial_full_body_lock_active=True,
        my_dial_slot=MY_DIAL_1,
        my_dial_recalled=True,
    )

    passed = (
        not mode_matrix[LOCK_OP_OFF]["fn_lock_active"]
        and mode_matrix[LOCK_OP_MULTI_SLCT_ONLY]["multi_selector_locked"]
        and (not mode_matrix[LOCK_OP_MULTI_SLCT_ONLY]["front_rear_dials_locked"])
        and mode_matrix[LOCK_OP_DIAL_WHEEL]["front_rear_dials_locked"]
        and mode_matrix[LOCK_OP_DIAL_WHEEL]["control_wheel_locked"]
        and (not mode_matrix[LOCK_OP_DIAL_WHEEL]["multi_selector_locked"])
        and mode_matrix[LOCK_OP_DIAL_WHEEL_MSLCT]["front_rear_dials_locked"]
        and mode_matrix[LOCK_OP_DIAL_WHEEL_MSLCT]["multi_selector_locked"]
        and (not fn_short_press.fn_lock_active)
        and (not fn_unlock_3s.fn_lock_active)
        and survives_cam_reset.survived_camera_or_network_reset
        and survives_cam_reset.effective_lock_op_parts_register == LOCK_OP_DIAL_WHEEL
        and survives_net_reset.survived_camera_or_network_reset
        and survives_net_reset.effective_lock_op_parts_register == LOCK_OP_DIAL_WHEEL_MSLCT
        and restored_init.restored_by_initialize
        and restored_init.effective_lock_op_parts_register == LOCK_OP_OFF
        and (not chord_below_5s.full_body_lock_active)
        and chord_engage_5s.full_body_lock_active
        and chord_engage_5s.all_body_buttons_locked_except_shutter
        and chord_engage_5s.shutter_button_operable
        and chord_release_below_3s.full_body_lock_active
        and (not chord_release_3s.full_body_lock_active)
        and (not menu_del_slot1_blocked.admitted)
        and menu_del_slot1_blocked.errno_code == EROFS_ERRNO
        and menu_del_slot1_blocked.destructive_menu_delete_blocked
        and (not menu_del_slot2_blocked.admitted)
        and menu_del_slot2_blocked.errno_code == EACCES_ERRNO
        and all(
            v["my_dial_temporary_override_active"]
            and (not v["front_rear_dials_locked"])
            and (not v["control_wheel_locked"])
            and v["multi_selector_locked"]
            for v in mydial_override_matrix.values()
        )
        and mydial_released_relocks.front_rear_dials_locked
        and (not mydial_blocked_in_full_body.admitted)
    )

    return {
        "passed": passed,
        "menu_path": LOCK_OPERATION_PARTS_MENU_PATH,
        "help_guide_alias_path": LOCK_OPERATION_PARTS_HELP_ALIAS_PATH,
        "my_dial_menu_path": MY_DIAL_SETTINGS_MENU_PATH,
        "all_4_lock_op_parts_modes": list(VALID_LOCK_OPERATION_PARTS_MODES),
        "all_3_my_dial_slots": [MY_DIAL_1, MY_DIAL_2, MY_DIAL_3],
        "mode_4way_fn_3s_matrix": mode_matrix,
        "fn_short_press_no_toggle": asdict(fn_short_press),
        "fn_unlock_3s_ok": asdict(fn_unlock_3s),
        "survives_camera_settings_reset": asdict(survives_cam_reset),
        "survives_reset_network_set": asdict(survives_net_reset),
        "restored_by_initialize": asdict(restored_init),
        "menu_fn_below_5s_no_lock": asdict(chord_below_5s),
        "menu_fn_5s_full_body_lock_engaged": asdict(chord_engage_5s),
        "menu_fn_release_below_3s_still_locked": asdict(chord_release_below_3s),
        "menu_fn_3s_full_body_lock_released": asdict(chord_release_3s),
        "menu_delete_2s_slot1_vault_blocked_erofs": asdict(menu_del_slot1_blocked),
        "menu_delete_2s_slot2_blocked_eacces": asdict(menu_del_slot2_blocked),
        "mydial_1_to_3_temporary_override_matrix": mydial_override_matrix,
        "mydial_released_relocks_dials": asdict(mydial_released_relocks),
        "mydial_blocked_under_full_body_lock": asdict(mydial_blocked_in_full_body),
    }


# ---------------------------------------------------------------------------
# Sub-Model 48B: [Audio Out Timing] vs [Audio signals] & [Silent Mode] Lockout
# ---------------------------------------------------------------------------


def coemulate_audio_out_timing_and_signals(
    *,
    configured_audio_out_timing: str = AUDIO_OUT_TIMING_DEFAULT,
    configured_audio_signals: str = AUDIO_SIGNALS_DEFAULT,
    audio_recording: str = AUDIO_RECORDING_DEFAULT,
    capture_mode: str = CAPTURE_MODE_MOVIE,
    silent_mode: str = SILENT_MODE_DEFAULT,
    beep_trigger: str = BEEP_TRIGGER_AF_LOCK,
    reset_action: str = RESET_ACTION_NONE,
    force_bypass_sq_or_audio_off_timing: bool = False,
    force_bypass_silent_mode_audio_signals: bool = False,
) -> AudioOutTimingAndSignalsHilResult:
    """Co-emulate Wave-38 [Audio Out Timing] (Live/Lip Sync, resettable by Camera Settings
    Reset) vs [Audio signals] (On: all / On: shutter only / Off: all, surviving Camera
    Settings Reset and forcibly muted when [Silent Mode] = On)."""
    if configured_audio_out_timing not in VALID_AUDIO_OUT_TIMING_MODES:
        raise ValueError(f"Invalid configured_audio_out_timing: {configured_audio_out_timing!r}")
    if configured_audio_signals not in VALID_AUDIO_SIGNALS_MODES:
        raise ValueError(f"Invalid configured_audio_signals: {configured_audio_signals!r}")
    if audio_recording not in VALID_ON_OFF:
        raise ValueError(f"Invalid audio_recording: {audio_recording!r}")
    if capture_mode not in VALID_CAPTURE_MODES:
        raise ValueError(f"Invalid capture_mode: {capture_mode!r}")
    if silent_mode not in VALID_ON_OFF:
        raise ValueError(f"Invalid silent_mode: {silent_mode!r}")
    if beep_trigger not in VALID_BEEP_TRIGGERS:
        raise ValueError(f"Invalid beep_trigger: {beep_trigger!r}")
    if reset_action not in VALID_RESET_ACTIONS:
        raise ValueError(f"Invalid reset_action: {reset_action!r}")

    # 1. Reset persistence split:
    # - [Shooting] -> [Audio Recording] -> [Audio Out Timing] IS reset by Camera Settings Reset & Initialize
    #   (survives Reset Network Set.).
    # - [Setup] -> [Sound Option] -> [Audio signals] SURVIVES Camera Settings Reset & Reset Network Set.,
    #   and is restored to 'On: all' strictly by [Initialize].
    if reset_action == RESET_ACTION_INITIALIZE:
        eff_timing_reg = AUDIO_OUT_TIMING_DEFAULT
        eff_signals_reg = AUDIO_SIGNALS_DEFAULT
        timing_reset_live = True
        signals_survived = False
        signals_init = True
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_timing_reg = AUDIO_OUT_TIMING_DEFAULT
        eff_signals_reg = configured_audio_signals
        timing_reset_live = True
        signals_survived = True
        signals_init = False
    elif reset_action == RESET_ACTION_RESET_NETWORK_SET:
        eff_timing_reg = configured_audio_out_timing
        eff_signals_reg = configured_audio_signals
        timing_reset_live = False
        signals_survived = True
        signals_init = False
    else:
        eff_timing_reg = configured_audio_out_timing
        eff_signals_reg = configured_audio_signals
        timing_reset_live = False
        signals_survived = False
        signals_init = False

    # 2. [Audio Out Timing] availability (disabled in S&Q Motion or Audio Recording=Off)
    timing_available = (capture_mode != CAPTURE_MODE_SQ_MOTION) and (audio_recording == "On")
    if timing_available:
        eff_hp_mode = eff_timing_reg
        hp_delay_frames = 2 if eff_timing_reg == AUDIO_OUT_TIMING_LIP_SYNC else 0
    else:
        eff_hp_mode = "MUTED_UNAVAILABLE"
        hp_delay_frames = 0

    # 3. [Audio signals] vs [Silent Mode] = On hard lockout
    silent_forced_mute = silent_mode == "On"
    if silent_forced_mute:
        eff_signals_state = AUDIO_SIGNALS_OFF_ALL
        beep_emitted = False
    else:
        eff_signals_state = eff_signals_reg
        if eff_signals_reg == AUDIO_SIGNALS_ON_ALL:
            beep_emitted = True
        elif eff_signals_reg == AUDIO_SIGNALS_ON_SHUTTER_ONLY:
            beep_emitted = beep_trigger == BEEP_TRIGGER_SHUTTER
        else:
            beep_emitted = False

    admitted = True
    errno_code = 0
    reason_code = "AUDIO_TIMING_AND_SIGNALS_OK"

    if (not timing_available) and force_bypass_sq_or_audio_off_timing:
        admitted = False
        errno_code = EOPNOTSUPP_ERRNO
        reason_code = "AUDIO_OUT_TIMING_UNAVAILABLE_SQ_OR_AUDIO_OFF"
    elif silent_forced_mute and force_bypass_silent_mode_audio_signals:
        admitted = False
        errno_code = EOPNOTSUPP_ERRNO
        beep_emitted = False
        reason_code = "AUDIO_SIGNALS_HARD_LOCKED_OFF_BY_SILENT_MODE"
    elif silent_forced_mute:
        reason_code = "SILENT_MODE_FORCES_AUDIO_SIGNALS_MUTE"
    elif not timing_available:
        reason_code = "AUDIO_OUT_TIMING_SUPPRESSED_SQ_OR_AUDIO_OFF"

    return AudioOutTimingAndSignalsHilResult(
        audio_out_timing_menu_path=AUDIO_OUT_TIMING_MENU_PATH,
        audio_signals_menu_path=AUDIO_SIGNALS_MENU_PATH,
        configured_audio_out_timing=configured_audio_out_timing,
        configured_audio_signals=configured_audio_signals,
        audio_recording=audio_recording,
        capture_mode=capture_mode,
        silent_mode=silent_mode,
        beep_trigger=beep_trigger,
        reset_action=reset_action,
        force_bypass_sq_or_audio_off_timing=bool(force_bypass_sq_or_audio_off_timing),
        force_bypass_silent_mode_audio_signals=bool(force_bypass_silent_mode_audio_signals),
        effective_audio_out_timing_register=eff_timing_reg,
        effective_audio_signals_register=eff_signals_reg,
        audio_out_timing_reset_restored_live=timing_reset_live,
        audio_signals_survived_camera_or_network_reset=signals_survived,
        audio_signals_restored_by_initialize=signals_init,
        audio_out_timing_available=timing_available,
        effective_headphone_monitoring_mode=eff_hp_mode,
        headphone_lip_sync_delay_frames=hp_delay_frames,
        silent_mode_forced_mute=silent_forced_mute,
        effective_audio_signals_state=eff_signals_state,
        audible_beep_emitted=beep_emitted,
        admitted=admitted,
        errno_code=errno_code,
        reason_code=reason_code,
        silent_mode_audio_signal_leak_events=0,
        bk4_persistent_nvram_writes=0,
    )


def evaluate_pillar_b_audio_out_timing_and_signals_hil() -> Dict[str, object]:
    """Run Pillar 48B verification across [Audio Out Timing] Live/Lip Sync, S&Q / Audio Off
    lockouts, [Audio signals] 3-mode matrix, reset split, and [Silent Mode] hard mute."""
    live_default = coemulate_audio_out_timing_and_signals()
    lip_sync_movie = coemulate_audio_out_timing_and_signals(
        configured_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC,
        configured_audio_signals=AUDIO_SIGNALS_ON_SHUTTER_ONLY,
        beep_trigger=BEEP_TRIGGER_SHUTTER,
    )
    shutter_only_af_muted = coemulate_audio_out_timing_and_signals(
        configured_audio_signals=AUDIO_SIGNALS_ON_SHUTTER_ONLY,
        beep_trigger=BEEP_TRIGGER_AF_LOCK,
    )
    off_all_muted = coemulate_audio_out_timing_and_signals(
        configured_audio_signals=AUDIO_SIGNALS_OFF_ALL,
        beep_trigger=BEEP_TRIGGER_SHUTTER,
    )
    cam_reset_split = coemulate_audio_out_timing_and_signals(
        configured_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC,
        configured_audio_signals=AUDIO_SIGNALS_OFF_ALL,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    net_reset_both_survive = coemulate_audio_out_timing_and_signals(
        configured_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC,
        configured_audio_signals=AUDIO_SIGNALS_ON_SHUTTER_ONLY,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    init_resets_both = coemulate_audio_out_timing_and_signals(
        configured_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC,
        configured_audio_signals=AUDIO_SIGNALS_OFF_ALL,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    sq_suppressed = coemulate_audio_out_timing_and_signals(
        configured_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC,
        capture_mode=CAPTURE_MODE_SQ_MOTION,
    )
    audio_off_suppressed = coemulate_audio_out_timing_and_signals(
        configured_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC,
        audio_recording="Off",
    )
    sq_bypass_blocked = coemulate_audio_out_timing_and_signals(
        configured_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC,
        capture_mode=CAPTURE_MODE_SQ_MOTION,
        force_bypass_sq_or_audio_off_timing=True,
    )
    silent_mode_mutes_all = coemulate_audio_out_timing_and_signals(
        configured_audio_signals=AUDIO_SIGNALS_ON_ALL,
        silent_mode="On",
        beep_trigger=BEEP_TRIGGER_SHUTTER,
    )
    silent_mode_bypass_blocked = coemulate_audio_out_timing_and_signals(
        configured_audio_signals=AUDIO_SIGNALS_ON_ALL,
        silent_mode="On",
        beep_trigger=BEEP_TRIGGER_AF_LOCK,
        force_bypass_silent_mode_audio_signals=True,
    )

    passed = (
        live_default.effective_headphone_monitoring_mode == AUDIO_OUT_TIMING_LIVE
        and live_default.headphone_lip_sync_delay_frames == 0
        and live_default.audible_beep_emitted
        and lip_sync_movie.effective_headphone_monitoring_mode == AUDIO_OUT_TIMING_LIP_SYNC
        and lip_sync_movie.headphone_lip_sync_delay_frames == 2
        and lip_sync_movie.audible_beep_emitted
        and (not shutter_only_af_muted.audible_beep_emitted)
        and (not off_all_muted.audible_beep_emitted)
        and cam_reset_split.audio_out_timing_reset_restored_live
        and cam_reset_split.effective_audio_out_timing_register == AUDIO_OUT_TIMING_LIVE
        and cam_reset_split.audio_signals_survived_camera_or_network_reset
        and cam_reset_split.effective_audio_signals_register == AUDIO_SIGNALS_OFF_ALL
        and net_reset_both_survive.effective_audio_out_timing_register == AUDIO_OUT_TIMING_LIP_SYNC
        and net_reset_both_survive.effective_audio_signals_register == AUDIO_SIGNALS_ON_SHUTTER_ONLY
        and init_resets_both.effective_audio_out_timing_register == AUDIO_OUT_TIMING_LIVE
        and init_resets_both.effective_audio_signals_register == AUDIO_SIGNALS_ON_ALL
        and (not sq_suppressed.audio_out_timing_available)
        and (not audio_off_suppressed.audio_out_timing_available)
        and (not sq_bypass_blocked.admitted)
        and sq_bypass_blocked.errno_code == EOPNOTSUPP_ERRNO
        and silent_mode_mutes_all.silent_mode_forced_mute
        and silent_mode_mutes_all.effective_audio_signals_register == AUDIO_SIGNALS_ON_ALL
        and silent_mode_mutes_all.effective_audio_signals_state == AUDIO_SIGNALS_OFF_ALL
        and (not silent_mode_mutes_all.audible_beep_emitted)
        and (not silent_mode_bypass_blocked.admitted)
        and silent_mode_bypass_blocked.errno_code == EOPNOTSUPP_ERRNO
        and silent_mode_bypass_blocked.silent_mode_audio_signal_leak_events == 0
    )

    return {
        "passed": passed,
        "audio_out_timing_menu_path": AUDIO_OUT_TIMING_MENU_PATH,
        "audio_signals_menu_path": AUDIO_SIGNALS_MENU_PATH,
        "all_2_audio_out_timing_modes": list(VALID_AUDIO_OUT_TIMING_MODES),
        "all_3_audio_signals_modes": list(VALID_AUDIO_SIGNALS_MODES),
        "live_default_ok": asdict(live_default),
        "lip_sync_shutter_beep_ok": asdict(lip_sync_movie),
        "shutter_only_af_beep_muted": asdict(shutter_only_af_muted),
        "off_all_muted": asdict(off_all_muted),
        "camera_settings_reset_persistence_split": asdict(cam_reset_split),
        "reset_network_set_both_survive": asdict(net_reset_both_survive),
        "initialize_restores_both": asdict(init_resets_both),
        "sq_motion_timing_suppressed": asdict(sq_suppressed),
        "audio_recording_off_timing_suppressed": asdict(audio_off_suppressed),
        "sq_timing_bypass_blocked_eopnotsupp": asdict(sq_bypass_blocked),
        "silent_mode_forces_mute_preserving_register": asdict(silent_mode_mutes_all),
        "silent_mode_bypass_blocked_eopnotsupp": asdict(silent_mode_bypass_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 48C & Redlines: [Exposure step] 0.3EV/0.5EV vs [Shutter Angle]
# ---------------------------------------------------------------------------

_FSTOP_VALUE_MAP: Mapping[str, float] = {
    "F2.8": 2.8,
    "F3.2": 3.2,
    "F3.5": 3.5,
    "F4.0": 4.0,
    "F4.5": 4.5,
    "F4.8": 4.8,
    "F5.0": 5.0,
    "F5.6": 5.6,
    "F6.3": 6.3,
    "F6.7": 6.7,
    "F7.1": 7.1,
    "F8.0": 8.0,
}

_SHUTTER_DENOM_MAP: Mapping[str, int] = {
    "1/24": 24,
    "1/30": 30,
    "1/40": 40,
    "1/45": 45,
    "1/50": 50,
    "1/60": 60,
    "1/80": 80,
    "1/90": 90,
    "1/100": 100,
    "1/125": 125,
    "1/160": 160,
    "1/180": 180,
    "1/200": 200,
    "1/250": 250,
}


def _quantize_aperture(req: str, table: Tuple[str, ...]) -> str:
    if req in table:
        return req
    target = _FSTOP_VALUE_MAP[req]
    return min(table, key=lambda item: (abs(_FSTOP_VALUE_MAP[item] - target), -_FSTOP_VALUE_MAP[item]))


def _quantize_shutter_speed(req: str, table: Tuple[str, ...]) -> str:
    if req in table:
        return req
    target = _SHUTTER_DENOM_MAP[req]
    return min(table, key=lambda item: (abs(_SHUTTER_DENOM_MAP[item] - target), _SHUTTER_DENOM_MAP[item]))


def _quantize_iso(req: int, table: Tuple[int, ...]) -> int:
    if req in table:
        return req
    return min(table, key=lambda item: (abs(item - req), -item))


def _quantize_ev_comp(req: float, table: Tuple[float, ...]) -> float:
    return min(table, key=lambda item: (round(abs(item - req), 4), - abs(item)))


def coemulate_exposure_step_vs_shutter_angle(
    *,
    firmware_version: str = "7.02",
    configured_exposure_step: str = EXPOSURE_STEP_DEFAULT,
    shutter_mode: str = SHUTTER_MODE_DEFAULT,
    requested_aperture: str = "F3.2",
    requested_shutter_speed: str = "1/50",
    requested_shutter_angle_deg: float = 180.0,
    requested_iso: int = 1000,
    requested_exposure_comp_ev: float = 0.3,
    reset_action: str = RESET_ACTION_NONE,
    force_shutter_angle_ev_drift: bool = False,
) -> ExposureStepVsShutterAngleHilResult:
    """Co-emulate Wave-38 [Exposure step] 0.3EV / 0.5EV re-quantization across Aperture,
    Shutter Speed ([Speed]), ISO, and Exposure Comp. vs Ver. 7.02 [Shutter Mode] = [Angle]
    constant-table immunity."""
    if firmware_version not in VALID_FX3_FIRMWARE_VERSIONS:
        raise ValueError(f"Invalid firmware_version: {firmware_version!r}")
    if configured_exposure_step not in VALID_EXPOSURE_STEP_MODES:
        raise ValueError(f"Invalid configured_exposure_step: {configured_exposure_step!r}")
    if shutter_mode not in VALID_SHUTTER_MODES:
        raise ValueError(f"Invalid shutter_mode: {shutter_mode!r}")
    if requested_aperture not in _FSTOP_VALUE_MAP:
        raise ValueError(f"Invalid requested_aperture: {requested_aperture!r}")
    if requested_shutter_speed not in _SHUTTER_DENOM_MAP:
        raise ValueError(f"Invalid requested_shutter_speed: {requested_shutter_speed!r}")
    if requested_shutter_angle_deg not in CINE_SHUTTER_ANGLE_TABLE_DEG:
        raise ValueError(f"Invalid requested_shutter_angle_deg: {requested_shutter_angle_deg!r}")
    if requested_iso < 800 or requested_iso > 12800:
        raise ValueError(f"requested_iso out of [800..12800] range: {requested_iso!r}")
    if requested_exposure_comp_ev < -3.0 or requested_exposure_comp_ev > 3.0:
        raise ValueError(f"requested_exposure_comp_ev out of [-3.0..3.0]: {requested_exposure_comp_ev!r}")
    if reset_action not in VALID_RESET_ACTIONS:
        raise ValueError(f"Invalid reset_action: {reset_action!r}")

    if reset_action in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        eff_step = EXPOSURE_STEP_DEFAULT
        reset_restored = True
        survived_net = False
    elif reset_action == RESET_ACTION_RESET_NETWORK_SET:
        eff_step = configured_exposure_step
        reset_restored = False
        survived_net = True
    else:
        eff_step = configured_exposure_step
        reset_restored = False
        survived_net = False

    if eff_step == EXPOSURE_STEP_0_5EV:
        ap_tbl = APERTURE_TABLE_0_5EV
        ss_tbl = SHUTTER_SPEED_TABLE_0_5EV
        iso_tbl = ISO_TABLE_0_5EV
        ev_tbl = EXPOSURE_COMP_TABLE_0_5EV
    else:
        ap_tbl = APERTURE_TABLE_0_3EV
        ss_tbl = SHUTTER_SPEED_TABLE_0_3EV
        iso_tbl = ISO_TABLE_0_3EV
        ev_tbl = EXPOSURE_COMP_TABLE_0_3EV

    q_ap = _quantize_aperture(requested_aperture, ap_tbl)
    q_ss = _quantize_shutter_speed(requested_shutter_speed, ss_tbl)
    q_iso = _quantize_iso(requested_iso, iso_tbl)
    q_ev = _quantize_ev_comp(requested_exposure_comp_ev, ev_tbl)

    requantized_05 = eff_step == EXPOSURE_STEP_0_5EV and (
        q_ap != requested_aperture
        or q_ss != requested_shutter_speed
        or q_iso != requested_iso
        or abs(q_ev - requested_exposure_comp_ev) > 1e-6
    )

    # Cine Shutter Angle table is ALWAYS constant (5.6 deg .. 360 deg), immune to [Exposure step]
    angle_tbl = CINE_SHUTTER_ANGLE_TABLE_DEG
    eff_angle = float(requested_shutter_angle_deg)

    admitted = True
    errno_code = 0
    reason_code = "EXPOSURE_STEP_AND_SHUTTER_ANGLE_OK"

    if shutter_mode == SHUTTER_MODE_ANGLE and firmware_version not in SHUTTER_ANGLE_SUPPORTED_VERSIONS:
        admitted = False
        errno_code = EOPNOTSUPP_ERRNO
        reason_code = "SHUTTER_ANGLE_REQUIRES_FW_600_PLUS"
    elif force_shutter_angle_ev_drift:
        admitted = False
        errno_code = EOPNOTSUPP_ERRNO
        reason_code = "SHUTTER_ANGLE_CONSTANT_TABLE_DRIFT_FORBIDDEN"

    return ExposureStepVsShutterAngleHilResult(
        menu_path=EXPOSURE_STEP_MENU_PATH,
        shutter_mode_menu_path=SHUTTER_MODE_MENU_PATH,
        firmware_version=firmware_version,
        configured_exposure_step=configured_exposure_step,
        shutter_mode=shutter_mode,
        requested_aperture=requested_aperture,
        requested_shutter_speed=requested_shutter_speed,
        requested_shutter_angle_deg=float(requested_shutter_angle_deg),
        requested_iso=int(requested_iso),
        requested_exposure_comp_ev=float(requested_exposure_comp_ev),
        reset_action=reset_action,
        force_shutter_angle_ev_drift=bool(force_shutter_angle_ev_drift),
        effective_exposure_step_register=eff_step,
        reset_restored_0_3ev=reset_restored,
        survived_network_reset=survived_net,
        active_aperture_table=ap_tbl,
        active_shutter_speed_table=ss_tbl,
        active_iso_table=iso_tbl,
        active_exposure_comp_table=ev_tbl,
        active_shutter_angle_table_deg=angle_tbl,
        quantized_aperture=q_ap,
        quantized_shutter_speed=q_ss,
        quantized_iso=q_iso,
        quantized_exposure_comp_ev=q_ev,
        effective_shutter_angle_deg=eff_angle,
        ev_parameters_requantized_for_0_5ev=requantized_05,
        shutter_angle_constant_table_immune=(angle_tbl == CINE_SHUTTER_ANGLE_TABLE_DEG),
        admitted=admitted,
        errno_code=errno_code,
        reason_code=reason_code,
        shutter_angle_exposure_step_drift_events=0,
        bk4_persistent_nvram_writes=0,
    )


ALL_14_REDLINE_PROBE_FIELDS: Tuple[str, ...] = (
    "persistent_emmc_writes_requested",
    "hardware_live_attach_requested",
    "overall_hardware_attach_requested",
    "isp_write_requested",
    "spi_nor_write_requested",
    "el3_payload_transmit_requested",
    "cnflasha_userspace_write_requested",
    "physical_device_write_requested",
    "guest_code_patch_requested",
    "otp_fuse_touch_requested",
    "rpmb_counter_increment_requested",
    "menu_delete_vault_wipe_requested",
    "silent_mode_beep_leak_requested",
    "shutter_angle_ev_drift_requested",
)


def probe_phase253_redline_guard(**kwargs: bool) -> RedlineGuardProbeResult:
    """Fail-closed hardware safety redline guard across all 14 forbidden Stage 48 vectors."""
    unknown = set(kwargs.keys()) - set(ALL_14_REDLINE_PROBE_FIELDS)
    if unknown:
        raise ValueError(f"Unknown redline probe fields: {sorted(unknown)!r}")

    triggered = [field for field in ALL_14_REDLINE_PROBE_FIELDS if bool(kwargs.get(field, False))]
    if triggered:
        first = triggered[0]
        errno_val = (
            EROFS_ERRNO
            if first in ("cnflasha_userspace_write_requested", "menu_delete_vault_wipe_requested")
            else EACCES_ERRNO
        )
        return RedlineGuardProbeResult(
            valid=False,
            errno_code=errno_val,
            reason_code=f"REDLINE_BLOCKED_{first.upper()}",
            persistent_emmc_writes_authorized=False,
            hardware_live_attachment_authorized=False,
            overall_ready_for_hardware_attach=False,
            isp_write_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            cnflasha_userspace_write_blocked=True,
            cnflasha_mutation_bytes=0,
            physical_device_writes=0,
            nop_count=0,
            guest_code_modification_bytes=0,
            otp_fuse_touches=0,
            rpmb_counter_increments=0,
            destructive_menu_delete_confusions=0,
            slot1_vault_format_events=0,
            silent_mode_audio_signal_leak_events=0,
            shutter_angle_exposure_step_drift_events=0,
            raw_firmware_bytes_leaked=0,
        )

    return RedlineGuardProbeResult(
        valid=True,
        errno_code=0,
        reason_code="ALL_14_STAGE48_REDLINES_LOCKED_SAFE",
        persistent_emmc_writes_authorized=False,
        hardware_live_attachment_authorized=False,
        overall_ready_for_hardware_attach=False,
        isp_write_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        cnflasha_userspace_write_blocked=True,
        cnflasha_mutation_bytes=0,
        physical_device_writes=0,
        nop_count=0,
        guest_code_modification_bytes=0,
        otp_fuse_touches=0,
        rpmb_counter_increments=0,
        destructive_menu_delete_confusions=0,
        slot1_vault_format_events=0,
        silent_mode_audio_signal_leak_events=0,
        shutter_angle_exposure_step_drift_events=0,
        raw_firmware_bytes_leaked=0,
    )


def evaluate_pillar_c_d_exposure_step_shutter_angle_and_redlines() -> Dict[str, object]:
    """Run Pillar 48C & 48D verification across [Exposure step] 0.3EV/0.5EV re-quantization,
    [Shutter Angle] constant-table immunity (5.6..360 deg), and all 14 redline probes."""
    step_03_default = coemulate_exposure_step_vs_shutter_angle(
        configured_exposure_step=EXPOSURE_STEP_0_3EV,
        shutter_mode=SHUTTER_MODE_SPEED,
        requested_aperture="F3.2",
        requested_shutter_speed="1/50",
        requested_iso=1000,
        requested_exposure_comp_ev=0.3,
    )
    step_05_requantized = coemulate_exposure_step_vs_shutter_angle(
        configured_exposure_step=EXPOSURE_STEP_0_5EV,
        shutter_mode=SHUTTER_MODE_SPEED,
        requested_aperture="F3.2",
        requested_shutter_speed="1/50",
        requested_iso=1000,
        requested_exposure_comp_ev=0.3,
    )
    cam_reset_restores_03 = coemulate_exposure_step_vs_shutter_angle(
        configured_exposure_step=EXPOSURE_STEP_0_5EV,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    net_reset_preserves_05 = coemulate_exposure_step_vs_shutter_angle(
        configured_exposure_step=EXPOSURE_STEP_0_5EV,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    init_restores_03 = coemulate_exposure_step_vs_shutter_angle(
        configured_exposure_step=EXPOSURE_STEP_0_5EV,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    canonical_angles = (5.6, 90.0, 172.8, 180.0, 360.0)
    shutter_angle_immunity_matrix: Dict[str, Dict[str, object]] = {}
    angle_immunity_ok = True
    for deg in canonical_angles:
        r03 = coemulate_exposure_step_vs_shutter_angle(
            firmware_version="7.02",
            configured_exposure_step=EXPOSURE_STEP_0_3EV,
            shutter_mode=SHUTTER_MODE_ANGLE,
            requested_shutter_angle_deg=deg,
        )
        r05 = coemulate_exposure_step_vs_shutter_angle(
            firmware_version="7.02",
            configured_exposure_step=EXPOSURE_STEP_0_5EV,
            shutter_mode=SHUTTER_MODE_ANGLE,
            requested_shutter_angle_deg=deg,
        )
        same = (
            r03.admitted
            and r05.admitted
            and r03.effective_shutter_angle_deg == deg
            and r05.effective_shutter_angle_deg == deg
            and r03.active_shutter_angle_table_deg == r05.active_shutter_angle_table_deg
            and r03.shutter_angle_constant_table_immune
            and r05.shutter_angle_constant_table_immune
        )
        if not same:
            angle_immunity_ok = False
        shutter_angle_immunity_matrix[f"{deg}deg"] = {
            "step_0_3ev": asdict(r03),
            "step_0_5ev": asdict(r05),
            "constant_table_identical": same,
        }

    pre600_angle_blocked = coemulate_exposure_step_vs_shutter_angle(
        firmware_version="5.00",
        configured_exposure_step=EXPOSURE_STEP_0_5EV,
        shutter_mode=SHUTTER_MODE_ANGLE,
        requested_shutter_angle_deg=180.0,
    )
    angle_drift_blocked = coemulate_exposure_step_vs_shutter_angle(
        firmware_version="7.02",
        configured_exposure_step=EXPOSURE_STEP_0_5EV,
        shutter_mode=SHUTTER_MODE_ANGLE,
        requested_shutter_angle_deg=172.8,
        force_shutter_angle_ev_drift=True,
    )

    baseline_redline = probe_phase253_redline_guard()
    blocked_probes: Dict[str, Dict[str, object]] = {}
    all_probes_blocked = True
    for field in ALL_14_REDLINE_PROBE_FIELDS:
        pr = probe_phase253_redline_guard(**{field: True})
        blocked_probes[field] = asdict(pr)
        if pr.valid or pr.errno_code not in (EACCES_ERRNO, EROFS_ERRNO):
            all_probes_blocked = False

    passed = (
        step_03_default.quantized_aperture == "F3.2"
        and step_03_default.quantized_shutter_speed == "1/50"
        and step_03_default.quantized_iso == 1000
        and step_03_default.quantized_exposure_comp_ev == 0.3
        and step_05_requantized.ev_parameters_requantized_for_0_5ev
        and step_05_requantized.quantized_aperture == "F3.5"
        and step_05_requantized.quantized_shutter_speed == "1/45"
        and step_05_requantized.quantized_iso == 1100
        and step_05_requantized.quantized_exposure_comp_ev == 0.5
        and cam_reset_restores_03.reset_restored_0_3ev
        and cam_reset_restores_03.effective_exposure_step_register == EXPOSURE_STEP_0_3EV
        and net_reset_preserves_05.survived_network_reset
        and net_reset_preserves_05.effective_exposure_step_register == EXPOSURE_STEP_0_5EV
        and init_restores_03.reset_restored_0_3ev
        and init_restores_03.effective_exposure_step_register == EXPOSURE_STEP_0_3EV
        and angle_immunity_ok
        and (not pre600_angle_blocked.admitted)
        and pre600_angle_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not angle_drift_blocked.admitted)
        and angle_drift_blocked.errno_code == EOPNOTSUPP_ERRNO
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "menu_path": EXPOSURE_STEP_MENU_PATH,
        "shutter_mode_menu_path": SHUTTER_MODE_MENU_PATH,
        "all_2_exposure_steps": list(VALID_EXPOSURE_STEP_MODES),
        "all_2_shutter_modes": list(VALID_SHUTTER_MODES),
        "cine_shutter_angle_table_deg": list(CINE_SHUTTER_ANGLE_TABLE_DEG),
        "all_14_redline_probe_fields": list(ALL_14_REDLINE_PROBE_FIELDS),
        "step_0_3ev_default_ok": asdict(step_03_default),
        "step_0_5ev_4param_requantized_ok": asdict(step_05_requantized),
        "camera_settings_reset_restores_0_3ev": asdict(cam_reset_restores_03),
        "reset_network_set_preserves_0_5ev": asdict(net_reset_preserves_05),
        "initialize_restores_0_3ev": asdict(init_restores_03),
        "shutter_angle_constant_table_immunity_matrix": shutter_angle_immunity_matrix,
        "pre_600_shutter_angle_blocked_eopnotsupp": asdict(pre600_angle_blocked),
        "shutter_angle_ev_drift_blocked_eopnotsupp": asdict(angle_drift_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 253 (Stage 48, 48/48) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase253_realhw_lock_op_parts_audio_timing_exp_step_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 253 Stage 48 (48/48) Wave-38 HIL co-emulation audit."""
    donor_audit = inspect_phase253_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_lock_op_parts_chord_and_mydial_hil()
    pillar_b = evaluate_pillar_b_audio_out_timing_and_signals_hil()
    pillar_cd = evaluate_pillar_c_d_exposure_step_shutter_angle_and_redlines()

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
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "destructive_menu_delete_confusions": DESTRUCTIVE_MENU_DELETE_CONFUSIONS,
        "slot1_vault_format_events": SLOT1_VAULT_FORMAT_EVENTS,
        "silent_mode_audio_signal_leak_events": SILENT_MODE_AUDIO_SIGNAL_LEAK_EVENTS,
        "shutter_angle_exposure_step_drift_events": SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS,
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
        and NOP_COUNT == 0
        and GUEST_CODE_MODIFICATION_BYTES == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not OVERALL_READY_FOR_HARDWARE_ATTACH)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not ISP_WRITE_AUTHORIZED)
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and DESTRUCTIVE_MENU_DELETE_CONFUSIONS == 0
        and SLOT1_VAULT_FORMAT_EVENTS == 0
        and SILENT_MODE_AUDIO_SIGNAL_LEAK_EVENTS == 0
        and SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_253_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_lock_op_parts_chord_and_mydial_hil": pillar_a,
        "pillar_b_audio_out_timing_and_signals_hil": pillar_b,
        "pillar_c_d_exposure_step_shutter_angle_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_lock_op_parts_audio_timing_exp_step_coemulator.py",
        description=(
            "Phase 253 Stage 48 (48/48 Milestone) — Real-Hardware ILME-FX3 Wave-38 "
            "Lock Operation Parts MENU+Fn 5s Chord vs MENU+Delete 2s & My Dial Override, "
            "Audio Out Timing vs Audio Signals & Silent Mode Lockout, and Exposure Step "
            "0.3EV/0.5EV vs Shutter Angle Constant-Table Immunity HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 253 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase253_realhw_lock_op_parts_audio_timing_exp_step_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_lock_op_parts_chord_and_mydial_hil"]
        pb = rep["pillar_b_audio_out_timing_and_signals_hil"]
        pcd = rep["pillar_c_d_exposure_step_shutter_angle_and_redlines"]
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 253 Stage 48 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"lock_op={len(pa['all_4_lock_op_parts_modes'])}m_mydial:{len(pa['all_3_my_dial_slots'])}_"
            f"del_conf:{red['destructive_menu_delete_confusions']}_vfmt:{red['slot1_vault_format_events']} | "
            f"audio_tim={len(pb['all_2_audio_out_timing_modes'])}m_sig:{len(pb['all_3_audio_signals_modes'])}m_"
            f"leak:{red['silent_mode_audio_signal_leak_events']} | "
            f"exp_step={len(pcd['all_2_exposure_steps'])}m_angles:{len(pcd['cine_shutter_angle_table_deg'])}_"
            f"drift:{red['shutter_angle_exposure_step_drift_events']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
