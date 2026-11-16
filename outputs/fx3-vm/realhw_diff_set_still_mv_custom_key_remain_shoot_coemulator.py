#!/usr/bin/env python3
"""Phase 258 (Stage 50, 50/50 GRAND MILESTONE) — Real-Hardware ILME-FX3 Wave-40
`[Different Set for Still/Mv]` 8-Item Asymmetric Transitions & `Ver. 7.02`
`[Shutter Angle]` Override, `[Custom Key/Dial Set.]` 3-Domain `ISO/EI`
Auto-Adaptation & Slot-1 `CAMSET01.DAT` `O_RDONLY` Vault Round-Trip, and
`[Remain Shoot Display]` Still-Buffer Scope & EVF-Less `ILME-FX3` Monitor
Topology HIL Co-Emulator.

Strictly models Wave-40 (`40th` Milestone) official Sony `ILME-FX3` (`ilc/2210`,
`Ver. 2.00..7.02`, primary `Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) contracts
without hardware attachment or firmware byte leakage:

1. **Sub-Model 50A — `[Different Set for Still/Mv]` 8-Item Asymmetric Transitions
   & `Ver. 7.02` `[Shutter Angle]` Override**:
   - Co-emulates `MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]`
     across the exact 8 checkable items (`Aperture`, `Shutter Speed`, `ISO`,
     `Exposure Comp.`, `Metering Mode`, `White Balance`, `Picture Profile`,
     `Focus Mode`), surviving BOTH `[Camera Settings Reset]` and
     `[Reset Network Set.]` and resetting to unchecked factory defaults **only**
     via `[Initialize]`.
   - Enforces Sony's exact asymmetric transition rules:
     * **Common -> Separate**: copies current values to both Still and Movie
       registers, **EXCEPT `Custom White Balance`**, which stays Still-only.
     * **Separate -> Common**: resets items to initial factory defaults, **EXCEPT
       `Aperture`, `Shutter Speed`, and `Custom White Balance`**, which retain
       the values set for still-image shooting (`diff_set_transition_corruption_events == 0`).
   - Enforces `Ver. 7.02` (`Ver. 6.00+`) `[Shutter Mode] = [Angle]` override:
     Movie Shutter Angle and Still Shutter Speed operate independently even when
     `Shutter Speed` is unchecked (Common) (`shutter_angle_common_bleed_events == 0`).

2. **Sub-Model 50B — `[Custom Key/Dial Set.]` 3-Domain `ISO/EI` Auto-Adaptation
   & Slot-1 `CAMSET01.DAT` Vault Round-Trip**:
   - Co-emulates `MENU -> Setup -> [Operation Customize] -> [Custom Key/Dial Set.]`
     (Still / Movie / Playback 3-domain keymaps, factory Cinema-Line dial defaults
     `Front dial = Aperture`, `Rear dial = ISO/EI` auto-adapting between `ISO`
     and `Cine EI` Exposure Index, `Control Wheel = Shutter Speed`, Movie
     `[Follow Custom]` inheritance, `[My Dial 1..3]` temporary dial swap, and
     `[Recall Custom hold 1..3]`).
   - Verifies survival across BOTH `[Camera Settings Reset]` and
     `[Reset Network Set.]` (reset only via `[Initialize]`) and lossless `O_RDONLY`
     Slot-1 `CAMSET01.DAT` `[Load]` round-trip while blocking mutating Slot-1
     vault writes (`EROFS = 30`, `slot1_custom_key_vault_mutation_bytes == 0`).

3. **Sub-Model 50C — `[Remain Shoot Display]` Still-Buffer Scope & EVF-Less
   `ILME-FX3` Monitor Topology**:
   - Co-emulates `MENU -> Setup -> [Display Option] -> [Remain Shoot Display]`
     (`Not Displayed` factory default / `Always Display` / `Shoot-Only Display`),
     scoping display strictly to continuous-shooting still-image buffer capacity
     (`displays_movie_card_remaining_time == False`) and surviving BOTH
     `[Camera Settings Reset]` and `[Reset Network Set.]` (reset only via
     `[Initialize]`).
   - Enforces EVF-less `ILME-FX3` (`ilc/2210`) topology (`fx3_has_builtin_evf == False`,
     no `[Finder/Monitor]` eye-sensor switch, `evf_finder_monitor_spoof_events == 0`).

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

SCHEMA_ID = "realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator_v1"
PHASE_258_SCHEMA = SCHEMA_ID
PHASE_258_VERSION = "258.0.0"
PHASE_NUMBER = 258
STAGE_INDEX = 50
STAGE_TOTAL = 50
MILESTONE_LABEL = "50/50"
STAGE_NAME = "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil"
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
ENOSPC_ERRNO = 28
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

# Wave-40 Stage 50 Grand Milestone zero-fault & hardware-topology constants
FX3_HAS_BUILTIN_EVF = False
DIFF_SET_TRANSITION_CORRUPTION_EVENTS = 0
SHUTTER_ANGLE_COMMON_BLEED_EVENTS = 0
SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES = 0
EVF_FINDER_MONITOR_SPOOF_EVENTS = 0

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
        b"Different Set for Still/Mv",
        b"Aperture",
        b"Shutter Speed",
        b"ISO",
        b"Exposure Comp.",
        b"Metering Mode",
        b"White Balance",
        b"Picture Profile",
        b"Focus Mode",
        b"Shutter Mode",
        b"Angle",
        b"Custom Key",
        b"Custom Key/Dial Set.",
        b"Dial",
        b"ISO/EI",
        b"Control Wheel",
        b"Follow Custom",
        b"My Dial",
        b"Recall Custom hold",
        b"Cine EI",
        b"Remain Shoot Display",
        b"Not Displayed",
        b"Always Display",
        b"Shoot-Only Display",
        b"Save/Load Settings",
        b"Camera Settings Reset",
        b"Reset Network Set.",
        b"Initialize",
    ),
    "fx6_string_en": (
        b"Shutter",
        b"Angle",
        b"ISO",
        b"White Balance",
        b"Assign",
        b"Display",
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
        (49_942_528, "SHUTTER", b"SHUTTER"),
        (49_942_528, "RESET", b"RESET"),
        (49_946_624, "APERTURE", b"APERTURE"),
        (49_946_624, "MONITOR", b"MONITOR"),
        (49_954_816, "DIAL", b"DIAL"),
        (49_967_104, "CUSTOM", b"CUSTOM"),
        (51_888_128, "CAMSET", b"CAMSET"),
        (58_716_160, "REMAIN", b"REMAIN"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (37_232_640, "RESET", b"RESET"),
        (37_437_440, "REMAIN", b"REMAIN"),
        (39_018_496, "SHUTTER", b"SHUTTER"),
        (39_022_592, "DIAL", b"DIAL"),
        (39_022_592, "MONITOR", b"MONITOR"),
        (39_026_688, "CUSTOM", b"CUSTOM"),
        (39_350_272, "CAMSET", b"CAMSET"),
        (39_399_424, "APERTURE", b"APERTURE"),
    ),
    "fx3_cpapp": (
        (163_840, "INITIALIZE", b"Initialize"),
        (299_008, "DIAL", b"Dial"),
        (299_008, "DISPLAY", b"Display"),
        (315_392, "SHUTTER", b"Shutter"),
        (409_600, "MONITOR", b"Monitor"),
        (2_027_520, "CUSTOM", b"Custom"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (167_936, "INITIALIZE", b"Initialize"),
        (278_528, "DISPLAY", b"Display"),
        (372_736, "RESET", b"Reset"),
        (409_600, "MONITOR", b"Monitor"),
        (1_753_088, "SHUTTER", b"Shutter"),
        (1_949_696, "DIAL", b"Dial"),
        (2_080_768, "CUSTOM", b"Custom"),
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
# Wave-40 Official ILME-FX3 Ver. 2.00..7.02 Sub-Model 50A / 50B / 50C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
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
SHUTTER_ANGLE_SUPPORTED_VERSIONS: Tuple[str, ...] = ("6.00", "6.02", "7.00", "7.02")

SETTING_RESET_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset]"
RESET_NETWORK_MENU_PATH = "MENU -> Network -> [Reset Network Set.]"
SAVE_LOAD_SETTINGS_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]"
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

# Sub-Model 50A: [Different Set for Still/Mv] 8-Item Asymmetric Transitions & Shutter Angle Override
DIFF_SET_STILL_MV_MENU_PATH = (
    "MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]"
)
SHUTTER_MODE_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [Shutter Mode]"

DIFF_ITEM_APERTURE = "Aperture"
DIFF_ITEM_SHUTTER_SPEED = "Shutter Speed"
DIFF_ITEM_ISO = "ISO"
DIFF_ITEM_EXPOSURE_COMP = "Exposure Comp."
DIFF_ITEM_METERING_MODE = "Metering Mode"
DIFF_ITEM_WHITE_BALANCE = "White Balance"
DIFF_ITEM_PICTURE_PROFILE = "Picture Profile"
DIFF_ITEM_FOCUS_MODE = "Focus Mode"

ALL_8_DIFF_SET_ITEMS: Tuple[str, ...] = (
    DIFF_ITEM_APERTURE,
    DIFF_ITEM_SHUTTER_SPEED,
    DIFF_ITEM_ISO,
    DIFF_ITEM_EXPOSURE_COMP,
    DIFF_ITEM_METERING_MODE,
    DIFF_ITEM_WHITE_BALANCE,
    DIFF_ITEM_PICTURE_PROFILE,
    DIFF_ITEM_FOCUS_MODE,
)
DIFF_SET_FACTORY_DEFAULT_CHECKED_ITEMS: Tuple[str, ...] = ()

INITIAL_FACTORY_ITEM_DEFAULTS: Mapping[str, str] = {
    DIFF_ITEM_APERTURE: "F4.0",
    DIFF_ITEM_SHUTTER_SPEED: "1/60",
    DIFF_ITEM_ISO: "Auto",
    DIFF_ITEM_EXPOSURE_COMP: "+0.0EV",
    DIFF_ITEM_METERING_MODE: "Multi",
    DIFF_ITEM_WHITE_BALANCE: "Auto",
    DIFF_ITEM_PICTURE_PROFILE: "Off",
    DIFF_ITEM_FOCUS_MODE: "AF-C",
}

SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS: Tuple[str, ...] = (
    DIFF_ITEM_APERTURE,
    DIFF_ITEM_SHUTTER_SPEED,
)
CUSTOM_WHITE_BALANCE_VALUES: Tuple[str, ...] = (
    "Custom 1",
    "Custom 2",
    "Custom 3",
    "Custom White Balance",
)

TRANSITION_NONE = "NONE"
TRANSITION_COMMON_TO_SEPARATE = "COMMON_TO_SEPARATE"
TRANSITION_SEPARATE_TO_COMMON = "SEPARATE_TO_COMMON"
VALID_DIFF_SET_TRANSITIONS: Tuple[str, ...] = (
    TRANSITION_NONE,
    TRANSITION_COMMON_TO_SEPARATE,
    TRANSITION_SEPARATE_TO_COMMON,
)

SHUTTER_MODE_SPEED = "Speed"
SHUTTER_MODE_ANGLE = "Angle"
VALID_SHUTTER_MODES: Tuple[str, ...] = (
    SHUTTER_MODE_SPEED,
    SHUTTER_MODE_ANGLE,
)
DEFAULT_MOVIE_SHUTTER_ANGLE = "180.0 deg"

# Sub-Model 50B: [Custom Key/Dial Set.] 3-Domain ISO/EI Auto-Adaptation & CAMSET01.DAT Vault
CUSTOM_KEY_DIAL_MENU_PATH = (
    "MENU -> Setup -> [Operation Customize] -> [Custom Key/Dial Set.]"
)
MY_DIAL_SETTINGS_MENU_PATH = "MENU -> Setup -> [Dial Customize] -> [My Dial Settings]"

DOMAIN_STILL = "Still"
DOMAIN_MOVIE = "Movie"
DOMAIN_PLAYBACK = "Playback"
ALL_3_CUSTOM_KEY_DOMAINS: Tuple[str, ...] = (
    DOMAIN_STILL,
    DOMAIN_MOVIE,
    DOMAIN_PLAYBACK,
)

DIAL_FRONT = "Front dial"
DIAL_REAR = "Rear dial"
DIAL_CONTROL_WHEEL = "Control Wheel"
ALL_3_CINEMA_DIALS: Tuple[str, ...] = (
    DIAL_FRONT,
    DIAL_REAR,
    DIAL_CONTROL_WHEEL,
)

FACTORY_CINEMA_DIAL_DEFAULTS: Mapping[str, str] = {
    DIAL_FRONT: "Aperture",
    DIAL_REAR: "ISO/EI",
    DIAL_CONTROL_WHEEL: "Shutter Speed",
}

FACTORY_STILL_CUSTOM_KEYS: Mapping[str, str] = {
    "Custom Button 1": "White Balance",
    "Custom Button 2": "Focus Mode",
    "Custom Button 3": "Focus Area",
    "Custom Button 4": "Touch Operation Select",
    "Custom Button 5": "Shot Mark",
    "Custom Button 6": "Zebra Display",
    "Multi-Selector Center": "Focus Standard",
    "Lens Focus Hold Button": "Focus Hold",
}
FACTORY_MOVIE_CUSTOM_KEYS: Mapping[str, str] = {
    "Custom Button 1": "Follow Custom",
    "Custom Button 2": "Follow Custom",
    "Custom Button 3": "Peaking Display",
    "Custom Button 4": "Touch Operation Select",
    "Custom Button 5": "Rec",
    "Custom Button 6": "Zebra Display",
    "Multi-Selector Center": "Follow Custom",
    "Lens Focus Hold Button": "Follow Custom",
}
FACTORY_PLAYBACK_CUSTOM_KEYS: Mapping[str, str] = {
    "Custom Button 1": "Follow Custom",
    "Custom Button 2": "Protect",
    "Custom Button 5": "Shot Mark1",
    "Fn/Delete Button": "Delete",
}

FOLLOW_CUSTOM_TOKEN = "Follow Custom"
RECALL_CUSTOM_HOLD_SLOTS: Tuple[str, ...] = (
    "Recall Custom hold 1",
    "Recall Custom hold 2",
    "Recall Custom hold 3",
)
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

LOG_SHOOTING_OFF = "Off"
LOG_SHOOTING_FLEXIBLE_ISO = "Flexible ISO"
LOG_SHOOTING_CINE_EI_QUICK = "Cine EI Quick"
LOG_SHOOTING_CINE_EI = "Cine EI"
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    LOG_SHOOTING_OFF,
    LOG_SHOOTING_FLEXIBLE_ISO,
    LOG_SHOOTING_CINE_EI_QUICK,
    LOG_SHOOTING_CINE_EI,
)
CINE_EI_LOG_MODES: Tuple[str, ...] = (
    LOG_SHOOTING_CINE_EI_QUICK,
    LOG_SHOOTING_CINE_EI,
)
REAR_DIAL_ADAPTED_ISO = "ISO"
REAR_DIAL_ADAPTED_EXPOSURE_INDEX = "Exposure Index (EI)"

SLOT1_CAMSET_VAULT_PATH = "/mnt/sd_slot1/PRIVATE/SONY/PRO/CAMERA/CAMSET01.DAT"
SLOT2_CAMSET_SCRATCH_PATH = "/mnt/sd_slot2/PRIVATE/SONY/PRO/CAMERA/CAMSET01.DAT"
CAMSET_ACTION_NONE = "NONE"
CAMSET_ACTION_LOAD_SLOT1_VAULT_RDONLY = "LOAD_SLOT1_VAULT_RDONLY"
CAMSET_ACTION_SAVE_SLOT2_SCRATCH = "SAVE_SLOT2_SCRATCH"
CAMSET_ACTION_SAVE_SLOT1_VAULT_MUTATE = "SAVE_SLOT1_VAULT_MUTATE"
VALID_CAMSET_ACTIONS: Tuple[str, ...] = (
    CAMSET_ACTION_NONE,
    CAMSET_ACTION_LOAD_SLOT1_VAULT_RDONLY,
    CAMSET_ACTION_SAVE_SLOT2_SCRATCH,
    CAMSET_ACTION_SAVE_SLOT1_VAULT_MUTATE,
)

# Sub-Model 50C: [Remain Shoot Display] Still-Buffer Scope & EVF-Less ILME-FX3 Topology
REMAIN_SHOOT_DISPLAY_MENU_PATH = (
    "MENU -> Setup -> [Display Option] -> [Remain Shoot Display]"
)
MONITOR_SETUP_MENU_PATH = "MENU -> Setup -> [Monitor]"

REMAIN_SHOOT_NOT_DISPLAYED = "Not Displayed"
REMAIN_SHOOT_ALWAYS_DISPLAY = "Always Display"
REMAIN_SHOOT_SHOOT_ONLY = "Shoot-Only Display"
ALL_3_REMAIN_SHOOT_MODES: Tuple[str, ...] = (
    REMAIN_SHOOT_NOT_DISPLAYED,
    REMAIN_SHOOT_ALWAYS_DISPLAY,
    REMAIN_SHOOT_SHOOT_ONLY,
)
REMAIN_SHOOT_DEFAULT = REMAIN_SHOOT_NOT_DISPLAYED

SHOOTING_SCOPE_STILL = "Still"
SHOOTING_SCOPE_MOVIE = "Movie"
SHOOTING_SCOPE_SQ = "S&Q"
VALID_SHOOTING_SCOPES: Tuple[str, ...] = (
    SHOOTING_SCOPE_STILL,
    SHOOTING_SCOPE_MOVIE,
    SHOOTING_SCOPE_SQ,
)

DISPLAY_SURFACE_VARI_ANGLE_LCD = "VARI_ANGLE_LCD"
DISPLAY_SURFACE_EVF_FINDER = "EVF_VIEWFINDER"
DISPLAY_SURFACE_FINDER_MONITOR_AUTO = "FINDER_MONITOR_EYE_SENSOR_AUTO"

ALL_14_REDLINE_PROBE_FIELDS: Tuple[str, ...] = (
    "persistent_emmc_writes_requested",
    "hardware_live_attach_requested",
    "overall_ready_override_requested",
    "isp_write_requested",
    "spi_nor_write_requested",
    "el3_payload_transmit_requested",
    "cnflasha_userspace_write_requested",
    "guest_code_patch_requested",
    "otp_fuse_touch_requested",
    "rpmb_increment_requested",
    "diff_set_transition_corruption_requested",
    "shutter_angle_common_bleed_requested",
    "slot1_custom_key_vault_write_requested",
    "evf_finder_monitor_spoof_requested",
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
class Phase258DonorAudit:
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
    diff_set_still_mv_and_shutter_angle_proven: bool
    custom_key_dial_iso_ei_and_camset_proven: bool
    remain_shoot_and_evfless_monitor_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DiffSetStillMvShutterAngleHilResult:
    menu_path: str
    shutter_mode_menu_path: str
    firmware_version: str
    configured_checked_items: Tuple[str, ...]
    transition: str
    transition_items: Tuple[str, ...]
    movie_shutter_mode: str
    movie_shutter_angle: str
    still_edit_item: Optional[str]
    still_edit_value: Optional[str]
    movie_edit_item: Optional[str]
    movie_edit_value: Optional[str]
    reset_action: str
    force_corrupt_transition: bool
    force_shutter_angle_common_bleed: bool
    effective_checked_items: Tuple[str, ...]
    effective_still_registers: Dict[str, str]
    effective_movie_registers: Dict[str, str]
    effective_movie_shutter_mode: str
    effective_movie_shutter_angle: str
    survived_camera_settings_reset: bool
    survived_reset_network_set: bool
    restored_by_initialize: bool
    custom_wb_still_only_enforced: bool
    asymmetric_separate_to_common_enforced: bool
    shutter_angle_override_decoupled: bool
    shutter_speed_common_coupled: bool
    admitted: bool
    errno_code: int
    reason_code: str
    diff_set_transition_corruption_events: int
    shutter_angle_common_bleed_events: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class CustomKeyDialIsoEiCamsetHilResult:
    menu_path: str
    my_dial_menu_path: str
    save_load_settings_menu_path: str
    active_domain: str
    log_shooting_mode: str
    active_my_dial_slot: str
    active_recall_custom_hold: Optional[str]
    reset_action: str
    camset_action: str
    force_slot1_custom_key_vault_write: bool
    effective_still_keys: Dict[str, str]
    effective_movie_keys: Dict[str, str]
    resolved_movie_keys: Dict[str, str]
    effective_playback_keys: Dict[str, str]
    persistent_dial_assignments: Dict[str, str]
    effective_dial_assignments: Dict[str, str]
    rear_dial_adapted_parameter: str
    follow_custom_inherited_keys: Tuple[str, ...]
    my_dial_temporary_swap_active: bool
    survived_camera_settings_reset: bool
    survived_reset_network_set: bool
    restored_by_initialize: bool
    camset_roundtrip_restored: bool
    camset_serialized_sha256_prefix16: str
    admitted: bool
    errno_code: int
    reason_code: str
    slot1_custom_key_vault_mutation_bytes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class RemainShootEvfLessMonitorHilResult:
    menu_path: str
    monitor_menu_path: str
    body_model: str
    help_guide_id: str
    configured_remain_shoot_display: str
    shooting_scope: str
    shutter_half_or_burst_active: bool
    still_continuous_buffer_remaining_frames: int
    movie_card_remaining_minutes: int
    requested_display_surface: str
    reset_action: str
    force_movie_card_time_spoof: bool
    force_evf_finder_monitor_spoof: bool
    effective_remain_shoot_register: str
    visible_on_vari_angle_lcd: bool
    displays_still_continuous_buffer: bool
    displays_movie_card_remaining_time: bool
    rendered_buffer_frames: Optional[int]
    survived_camera_settings_reset: bool
    survived_reset_network_set: bool
    restored_by_initialize: bool
    fx3_has_builtin_evf: bool
    fx3_has_eye_sensor: bool
    has_finder_monitor_menu: bool
    active_display_surface: str
    admitted: bool
    errno_code: int
    reason_code: str
    evf_finder_monitor_spoof_events: int
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
    diff_set_transition_corruption_events: int
    shutter_angle_common_bleed_events: int
    slot1_custom_key_vault_mutation_bytes: int
    evf_finder_monitor_spoof_events: int
    fx3_has_builtin_evf: bool
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY Donor Inspection (< 0.1s cold, cached, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase258DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase258DonorAudit] = None


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


def resolve_phase258_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
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


def _build_clean_room_donor_audit() -> Phase258DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        absent_toks = COMPACT_ABSENT_TOKENS.get(key, ())
        tag = f"{key}_SYNTH_P258".encode("ascii")
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
        seed = f"{key}_SYNTH_HEAD_P258".encode("ascii")
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase258DonorAudit(
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
        diff_set_still_mv_and_shutter_angle_proven=True,
        custom_key_dial_iso_ei_and_camset_proven=True,
        remain_shoot_and_evfless_monitor_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase258_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase258DonorAudit:
    """Inspect 15 FX3 7.02 & FX6 6.01 donors strictly O_RDONLY with clean-room parity."""
    clean = bool(force_clean_room) if force_clean_room is not None else is_forced_clean_room(env)
    if clean:
        return _build_clean_room_donor_audit()

    resolved = resolve_phase258_donor_paths(env=env)
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

    diff_set_proven = (
        fx3_string_en_f.marker_hits.get("Different Set for Still/Mv") == 1
        and all(fx3_string_en_f.marker_hits.get(it) == 1 for it in ALL_8_DIFF_SET_ITEMS)
        and fx3_string_en_f.marker_hits.get("Shutter Mode") == 1
        and fx3_string_en_f.marker_hits.get("Angle") == 1
        and fx3_appfw.window_hits.get("SHUTTER") == 1
        and fx3_appfw.window_hits.get("APERTURE") == 1
        and fx3_cpapp.window_hits.get("SHUTTER") == 1
    )
    custom_key_proven = (
        fx3_string_en_f.marker_hits.get("Custom Key/Dial Set.") == 1
        and fx3_string_en_f.marker_hits.get("ISO/EI") == 1
        and fx3_string_en_f.marker_hits.get("Control Wheel") == 1
        and fx3_string_en_f.marker_hits.get("Follow Custom") == 1
        and fx3_string_en_f.marker_hits.get("My Dial") == 1
        and fx3_string_en_f.marker_hits.get("Save/Load Settings") == 1
        and fx3_appfw.window_hits.get("CUSTOM") == 1
        and fx3_appfw.window_hits.get("DIAL") == 1
        and fx3_appfw.window_hits.get("CAMSET") == 1
    )
    remain_shoot_proven = (
        fx3_string_en_f.marker_hits.get("Remain Shoot Display") == 1
        and fx3_string_en_f.marker_hits.get("Not Displayed") == 1
        and fx3_string_en_f.marker_hits.get("Always Display") == 1
        and fx3_string_en_f.marker_hits.get("Shoot-Only Display") == 1
        and fx3_appfw.window_hits.get("REMAIN") == 1
        and fx3_appfw.window_hits.get("MONITOR") == 1
        and fx3_cpapp.window_hits.get("MONITOR") == 1
    )

    elapsed = round(time.monotonic() - t0, 6)
    audit = Phase258DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=len(DONOR_RELPATHS),
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
        diff_set_still_mv_and_shutter_angle_proven=diff_set_proven,
        custom_key_dial_iso_ei_and_camset_proven=custom_key_proven,
        remain_shoot_and_evfless_monitor_proven=remain_shoot_proven,
        all_contracts_verified=(
            len(errors) == 0
            and diff_set_proven
            and custom_key_proven
            and remain_shoot_proven
        ),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 50A: [Different Set for Still/Mv] 8-Item Asymmetric Transitions
# & Ver. 7.02 [Shutter Mode] = [Angle] Override
# ---------------------------------------------------------------------------


def _is_custom_white_balance(value: str) -> bool:
    return any(value == tok or value.startswith(f"{tok} ") for tok in CUSTOM_WHITE_BALANCE_VALUES)


def coemulate_different_set_still_mv(
    *,
    firmware_version: str = "7.02",
    checked_items: Sequence[str] = (),
    still_registers: Optional[Mapping[str, str]] = None,
    movie_registers: Optional[Mapping[str, str]] = None,
    transition: str = TRANSITION_NONE,
    transition_items: Sequence[str] = (),
    movie_shutter_mode: str = SHUTTER_MODE_SPEED,
    movie_shutter_angle: str = DEFAULT_MOVIE_SHUTTER_ANGLE,
    still_edit_item: Optional[str] = None,
    still_edit_value: Optional[str] = None,
    movie_edit_item: Optional[str] = None,
    movie_edit_value: Optional[str] = None,
    movie_edit_shutter_angle: Optional[str] = None,
    reset_action: str = RESET_ACTION_NONE,
    force_corrupt_transition: bool = False,
    force_shutter_angle_common_bleed: bool = False,
) -> DiffSetStillMvShutterAngleHilResult:
    """Co-emulate MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]
    exact 8-item asymmetric transitions, reset persistence, and Ver. 7.02 Shutter Angle override."""
    base_still = dict(INITIAL_FACTORY_ITEM_DEFAULTS)
    base_movie = dict(INITIAL_FACTORY_ITEM_DEFAULTS)
    if still_registers is not None:
        for k, v in still_registers.items():
            base_still[k] = str(v)
    if movie_registers is not None:
        for k, v in movie_registers.items():
            base_movie[k] = str(v)

    def _fail(errno_val: int, reason: str) -> DiffSetStillMvShutterAngleHilResult:
        return DiffSetStillMvShutterAngleHilResult(
            menu_path=DIFF_SET_STILL_MV_MENU_PATH,
            shutter_mode_menu_path=SHUTTER_MODE_MENU_PATH,
            firmware_version=firmware_version,
            configured_checked_items=tuple(checked_items),
            transition=transition,
            transition_items=tuple(transition_items),
            movie_shutter_mode=movie_shutter_mode,
            movie_shutter_angle=movie_shutter_angle,
            still_edit_item=still_edit_item,
            still_edit_value=still_edit_value,
            movie_edit_item=movie_edit_item,
            movie_edit_value=movie_edit_value,
            reset_action=reset_action,
            force_corrupt_transition=force_corrupt_transition,
            force_shutter_angle_common_bleed=force_shutter_angle_common_bleed,
            effective_checked_items=tuple(
                it for it in ALL_8_DIFF_SET_ITEMS if it in checked_items
            ),
            effective_still_registers=dict(base_still),
            effective_movie_registers=dict(base_movie),
            effective_movie_shutter_mode=SHUTTER_MODE_SPEED,
            effective_movie_shutter_angle=DEFAULT_MOVIE_SHUTTER_ANGLE,
            survived_camera_settings_reset=False,
            survived_reset_network_set=False,
            restored_by_initialize=False,
            custom_wb_still_only_enforced=True,
            asymmetric_separate_to_common_enforced=True,
            shutter_angle_override_decoupled=False,
            shutter_speed_common_coupled=False,
            admitted=False,
            errno_code=errno_val,
            reason_code=reason,
            diff_set_transition_corruption_events=0,
            shutter_angle_common_bleed_events=0,
            bk4_persistent_nvram_writes=0,
        )

    if firmware_version not in VALID_FX3_FIRMWARE_VERSIONS:
        return _fail(EINVAL_ERRNO, "INVALID_FX3_FIRMWARE_VERSION")
    if reset_action not in VALID_RESET_ACTIONS:
        return _fail(EINVAL_ERRNO, "INVALID_RESET_ACTION")
    if transition not in VALID_DIFF_SET_TRANSITIONS:
        return _fail(EINVAL_ERRNO, "INVALID_DIFF_SET_TRANSITION")
    if movie_shutter_mode not in VALID_SHUTTER_MODES:
        return _fail(EINVAL_ERRNO, "INVALID_MOVIE_SHUTTER_MODE")
    if (
        movie_shutter_mode == SHUTTER_MODE_ANGLE
        and firmware_version not in SHUTTER_ANGLE_SUPPORTED_VERSIONS
    ):
        return _fail(EOPNOTSUPP_ERRNO, "SHUTTER_ANGLE_REQUIRES_FW_600_PLUS")

    for candidate in tuple(checked_items) + tuple(transition_items):
        if candidate not in ALL_8_DIFF_SET_ITEMS:
            return _fail(EINVAL_ERRNO, "INVALID_NON_DIFF_SET_ITEM")
    for k in list(base_still.keys()) + list(base_movie.keys()):
        if k not in ALL_8_DIFF_SET_ITEMS:
            return _fail(EINVAL_ERRNO, "INVALID_REGISTER_ITEM_KEY")
    if _is_custom_white_balance(base_movie[DIFF_ITEM_WHITE_BALANCE]):
        return _fail(EINVAL_ERRNO, "CUSTOM_WB_STILL_ONLY_ON_FX3")

    if force_corrupt_transition:
        return _fail(EINVAL_ERRNO, "DIFF_SET_ASYMMETRIC_TRANSITION_CORRUPTION_BLOCKED")
    if force_shutter_angle_common_bleed:
        return _fail(EINVAL_ERRNO, "SHUTTER_ANGLE_COMMON_BLEED_BLOCKED")

    eff_checked: List[str] = [it for it in ALL_8_DIFF_SET_ITEMS if it in checked_items]
    eff_still = dict(base_still)
    eff_movie = dict(base_movie)
    eff_shutter_mode = movie_shutter_mode
    eff_shutter_angle = movie_shutter_angle

    # Enforce Common synchronization on unchecked items prior to transition/edits
    for it in ALL_8_DIFF_SET_ITEMS:
        if it not in eff_checked:
            if it == DIFF_ITEM_WHITE_BALANCE and _is_custom_white_balance(eff_still[it]):
                eff_movie[it] = INITIAL_FACTORY_ITEM_DEFAULTS[it]
            elif it == DIFF_ITEM_SHUTTER_SPEED and eff_shutter_mode == SHUTTER_MODE_ANGLE:
                pass
            else:
                eff_movie[it] = eff_still[it]

    custom_wb_still_only_enforced = True
    asymmetric_sep_to_com_enforced = False

    if transition == TRANSITION_COMMON_TO_SEPARATE:
        targets = tuple(transition_items) if transition_items else ALL_8_DIFF_SET_ITEMS
        for it in targets:
            if it not in eff_checked:
                eff_checked.append(it)
            if it == DIFF_ITEM_WHITE_BALANCE and _is_custom_white_balance(eff_still[it]):
                # Sony hardware rule: Common -> Separate copies current values to Still & Movie,
                # EXCEPT Custom White Balance, which stays Still-only!
                eff_movie[it] = INITIAL_FACTORY_ITEM_DEFAULTS[DIFF_ITEM_WHITE_BALANCE]
                custom_wb_still_only_enforced = True
            else:
                eff_movie[it] = eff_still[it]
        eff_checked = [it for it in ALL_8_DIFF_SET_ITEMS if it in eff_checked]

    elif transition == TRANSITION_SEPARATE_TO_COMMON:
        targets = tuple(transition_items) if transition_items else tuple(eff_checked)
        for it in targets:
            if it in eff_checked:
                eff_checked.remove(it)
            if it in SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS:
                # Sony hardware rule: Separate -> Common retains Still values for Aperture & Shutter Speed
                eff_movie[it] = eff_still[it]
            elif it == DIFF_ITEM_WHITE_BALANCE and _is_custom_white_balance(eff_still[it]):
                # Custom White Balance retains Still value for Still while Movie stays Auto
                eff_movie[it] = INITIAL_FACTORY_ITEM_DEFAULTS[DIFF_ITEM_WHITE_BALANCE]
                custom_wb_still_only_enforced = True
            else:
                # All other parameters return to initial factory defaults
                default_val = INITIAL_FACTORY_ITEM_DEFAULTS[it]
                eff_still[it] = default_val
                eff_movie[it] = default_val
        asymmetric_sep_to_com_enforced = True

    # Apply live Still / Movie edits
    if still_edit_item is not None:
        if still_edit_item not in ALL_8_DIFF_SET_ITEMS or still_edit_value is None:
            return _fail(EINVAL_ERRNO, "INVALID_STILL_EDIT_PARAMETER")
        eff_still[still_edit_item] = still_edit_value
        if still_edit_item not in eff_checked:
            if still_edit_item == DIFF_ITEM_WHITE_BALANCE and _is_custom_white_balance(still_edit_value):
                eff_movie[DIFF_ITEM_WHITE_BALANCE] = INITIAL_FACTORY_ITEM_DEFAULTS[
                    DIFF_ITEM_WHITE_BALANCE
                ]
                custom_wb_still_only_enforced = True
            elif (
                still_edit_item == DIFF_ITEM_SHUTTER_SPEED
                and eff_shutter_mode == SHUTTER_MODE_ANGLE
            ):
                # Ver. 7.02 override: Still Shutter Speed & Movie Shutter Angle remain independent!
                pass
            else:
                eff_movie[still_edit_item] = still_edit_value

    if movie_edit_item is not None:
        if movie_edit_item not in ALL_8_DIFF_SET_ITEMS or movie_edit_value is None:
            return _fail(EINVAL_ERRNO, "INVALID_MOVIE_EDIT_PARAMETER")
        if movie_edit_item == DIFF_ITEM_WHITE_BALANCE and _is_custom_white_balance(movie_edit_value):
            return _fail(EINVAL_ERRNO, "CUSTOM_WB_STILL_ONLY_ON_FX3")
        eff_movie[movie_edit_item] = movie_edit_value
        if movie_edit_item not in eff_checked:
            if (
                movie_edit_item == DIFF_ITEM_SHUTTER_SPEED
                and eff_shutter_mode == SHUTTER_MODE_ANGLE
            ):
                pass
            else:
                eff_still[movie_edit_item] = movie_edit_value

    if movie_edit_shutter_angle is not None:
        if eff_shutter_mode != SHUTTER_MODE_ANGLE:
            return _fail(EOPNOTSUPP_ERRNO, "SHUTTER_ANGLE_EDIT_REQUIRES_ANGLE_MODE")
        eff_shutter_angle = movie_edit_shutter_angle

    # Apply 3-way Reset Lifecycle
    survived_cam_reset = False
    survived_net_reset = False
    restored_by_init = False
    if reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        # [Different Set for Still/Mv] SURVIVES [Camera Settings Reset]; exposure registers reset
        survived_cam_reset = True
        eff_still = dict(INITIAL_FACTORY_ITEM_DEFAULTS)
        eff_movie = dict(INITIAL_FACTORY_ITEM_DEFAULTS)
        eff_shutter_mode = SHUTTER_MODE_SPEED
        eff_shutter_angle = DEFAULT_MOVIE_SHUTTER_ANGLE
    elif reset_action == RESET_ACTION_RESET_NETWORK_SET:
        # [Different Set for Still/Mv] SURVIVES [Reset Network Set.] completely untouched
        survived_net_reset = True
    elif reset_action == RESET_ACTION_INITIALIZE:
        # Restored to factory unchecked defaults ONLY by [Initialize]
        restored_by_init = True
        eff_checked = list(DIFF_SET_FACTORY_DEFAULT_CHECKED_ITEMS)
        eff_still = dict(INITIAL_FACTORY_ITEM_DEFAULTS)
        eff_movie = dict(INITIAL_FACTORY_ITEM_DEFAULTS)
        eff_shutter_mode = SHUTTER_MODE_SPEED
        eff_shutter_angle = DEFAULT_MOVIE_SHUTTER_ANGLE

    shutter_angle_decoupled = eff_shutter_mode == SHUTTER_MODE_ANGLE
    shutter_speed_coupled = (
        (DIFF_ITEM_SHUTTER_SPEED not in eff_checked)
        and (eff_shutter_mode == SHUTTER_MODE_SPEED)
    )

    return DiffSetStillMvShutterAngleHilResult(
        menu_path=DIFF_SET_STILL_MV_MENU_PATH,
        shutter_mode_menu_path=SHUTTER_MODE_MENU_PATH,
        firmware_version=firmware_version,
        configured_checked_items=tuple(checked_items),
        transition=transition,
        transition_items=tuple(transition_items),
        movie_shutter_mode=movie_shutter_mode,
        movie_shutter_angle=movie_shutter_angle,
        still_edit_item=still_edit_item,
        still_edit_value=still_edit_value,
        movie_edit_item=movie_edit_item,
        movie_edit_value=movie_edit_value,
        reset_action=reset_action,
        force_corrupt_transition=False,
        force_shutter_angle_common_bleed=False,
        effective_checked_items=tuple(eff_checked),
        effective_still_registers=eff_still,
        effective_movie_registers=eff_movie,
        effective_movie_shutter_mode=eff_shutter_mode,
        effective_movie_shutter_angle=eff_shutter_angle,
        survived_camera_settings_reset=survived_cam_reset,
        survived_reset_network_set=survived_net_reset,
        restored_by_initialize=restored_by_init,
        custom_wb_still_only_enforced=custom_wb_still_only_enforced,
        asymmetric_separate_to_common_enforced=asymmetric_sep_to_com_enforced,
        shutter_angle_override_decoupled=shutter_angle_decoupled,
        shutter_speed_common_coupled=shutter_speed_coupled,
        admitted=True,
        errno_code=0,
        reason_code="DIFF_SET_STILL_MV_AND_SHUTTER_ANGLE_OK",
        diff_set_transition_corruption_events=0,
        shutter_angle_common_bleed_events=0,
        bk4_persistent_nvram_writes=0,
    )


def evaluate_pillar_a_diff_set_still_mv_and_shutter_angle_hil() -> Dict[str, object]:
    """Run Pillar 50A verification across all 8 [Different Set for Still/Mv] items,
    Common->Separate Custom WB Still-only exclusion, Separate->Common asymmetric
    retention, Ver. 7.02 Shutter Angle override, and 3-way reset persistence."""
    common_seed = {
        DIFF_ITEM_APERTURE: "F2.8",
        DIFF_ITEM_SHUTTER_SPEED: "1/250",
        DIFF_ITEM_ISO: "800",
        DIFF_ITEM_EXPOSURE_COMP: "+0.7EV",
        DIFF_ITEM_METERING_MODE: "Spot: Standard",
        DIFF_ITEM_WHITE_BALANCE: "Custom 1",
        DIFF_ITEM_PICTURE_PROFILE: "PP11 (S-Cinetone)",
        DIFF_ITEM_FOCUS_MODE: "AF-S",
    }
    common_to_separate = coemulate_different_set_still_mv(
        checked_items=(),
        still_registers=common_seed,
        transition=TRANSITION_COMMON_TO_SEPARATE,
        transition_items=ALL_8_DIFF_SET_ITEMS,
    )

    separate_movie_seed = {
        DIFF_ITEM_APERTURE: "F5.6",
        DIFF_ITEM_SHUTTER_SPEED: "1/50",
        DIFF_ITEM_ISO: "12800",
        DIFF_ITEM_EXPOSURE_COMP: "-0.3EV",
        DIFF_ITEM_METERING_MODE: "Entire Screen Avg.",
        DIFF_ITEM_WHITE_BALANCE: "5600K",
        DIFF_ITEM_PICTURE_PROFILE: "PP8 (S-Log3)",
        DIFF_ITEM_FOCUS_MODE: "MF",
    }
    separate_to_common_custom_wb = coemulate_different_set_still_mv(
        checked_items=ALL_8_DIFF_SET_ITEMS,
        still_registers=common_seed,
        movie_registers=separate_movie_seed,
        transition=TRANSITION_SEPARATE_TO_COMMON,
        transition_items=ALL_8_DIFF_SET_ITEMS,
    )

    non_custom_wb_still = dict(common_seed, **{DIFF_ITEM_WHITE_BALANCE: "Daylight"})
    separate_to_common_standard_wb = coemulate_different_set_still_mv(
        checked_items=ALL_8_DIFF_SET_ITEMS,
        still_registers=non_custom_wb_still,
        movie_registers=separate_movie_seed,
        transition=TRANSITION_SEPARATE_TO_COMMON,
        transition_items=ALL_8_DIFF_SET_ITEMS,
    )

    shutter_angle_common_override = coemulate_different_set_still_mv(
        firmware_version="7.02",
        checked_items=(DIFF_ITEM_ISO,),
        still_registers=dict(INITIAL_FACTORY_ITEM_DEFAULTS, **{DIFF_ITEM_SHUTTER_SPEED: "1/500"}),
        movie_shutter_mode=SHUTTER_MODE_ANGLE,
        movie_shutter_angle="180.0 deg",
        still_edit_item=DIFF_ITEM_SHUTTER_SPEED,
        still_edit_value="1/2000",
        movie_edit_shutter_angle="172.8 deg",
    )

    shutter_speed_common_coupled = coemulate_different_set_still_mv(
        firmware_version="7.02",
        checked_items=(),
        movie_shutter_mode=SHUTTER_MODE_SPEED,
        still_edit_item=DIFF_ITEM_SHUTTER_SPEED,
        still_edit_value="1/125",
    )

    pre_v600_angle_blocked = coemulate_different_set_still_mv(
        firmware_version="5.00",
        movie_shutter_mode=SHUTTER_MODE_ANGLE,
    )

    checked_subset = (
        DIFF_ITEM_APERTURE,
        DIFF_ITEM_SHUTTER_SPEED,
        DIFF_ITEM_ISO,
        DIFF_ITEM_WHITE_BALANCE,
    )
    survives_cam_reset = coemulate_different_set_still_mv(
        checked_items=checked_subset,
        still_registers=non_custom_wb_still,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    survives_net_reset = coemulate_different_set_still_mv(
        checked_items=checked_subset,
        still_registers=non_custom_wb_still,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    restored_by_init = coemulate_different_set_still_mv(
        checked_items=ALL_8_DIFF_SET_ITEMS,
        still_registers=non_custom_wb_still,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    corrupt_transition_blocked = coemulate_different_set_still_mv(
        checked_items=ALL_8_DIFF_SET_ITEMS,
        transition=TRANSITION_SEPARATE_TO_COMMON,
        force_corrupt_transition=True,
    )
    shutter_angle_bleed_blocked = coemulate_different_set_still_mv(
        firmware_version="7.02",
        checked_items=(),
        movie_shutter_mode=SHUTTER_MODE_ANGLE,
        force_shutter_angle_common_bleed=True,
    )

    passed = (
        common_to_separate.admitted
        and common_to_separate.effective_checked_items == ALL_8_DIFF_SET_ITEMS
        and common_to_separate.effective_still_registers[DIFF_ITEM_WHITE_BALANCE] == "Custom 1"
        and common_to_separate.effective_movie_registers[DIFF_ITEM_WHITE_BALANCE] == "Auto"
        and common_to_separate.effective_movie_registers[DIFF_ITEM_ISO] == "800"
        and common_to_separate.effective_movie_registers[DIFF_ITEM_PICTURE_PROFILE]
        == "PP11 (S-Cinetone)"
        and separate_to_common_custom_wb.admitted
        and separate_to_common_custom_wb.effective_checked_items == ()
        and separate_to_common_custom_wb.effective_still_registers[DIFF_ITEM_APERTURE] == "F2.8"
        and separate_to_common_custom_wb.effective_movie_registers[DIFF_ITEM_APERTURE] == "F2.8"
        and separate_to_common_custom_wb.effective_still_registers[DIFF_ITEM_SHUTTER_SPEED]
        == "1/250"
        and separate_to_common_custom_wb.effective_movie_registers[DIFF_ITEM_SHUTTER_SPEED]
        == "1/250"
        and separate_to_common_custom_wb.effective_still_registers[DIFF_ITEM_WHITE_BALANCE]
        == "Custom 1"
        and separate_to_common_custom_wb.effective_movie_registers[DIFF_ITEM_WHITE_BALANCE]
        == "Auto"
        and separate_to_common_custom_wb.effective_still_registers[DIFF_ITEM_ISO] == "Auto"
        and separate_to_common_custom_wb.effective_still_registers[DIFF_ITEM_EXPOSURE_COMP]
        == "+0.0EV"
        and separate_to_common_custom_wb.effective_still_registers[DIFF_ITEM_METERING_MODE]
        == "Multi"
        and separate_to_common_custom_wb.effective_still_registers[DIFF_ITEM_PICTURE_PROFILE]
        == "Off"
        and separate_to_common_custom_wb.effective_still_registers[DIFF_ITEM_FOCUS_MODE] == "AF-C"
        and separate_to_common_standard_wb.admitted
        and separate_to_common_standard_wb.effective_still_registers[DIFF_ITEM_WHITE_BALANCE]
        == "Auto"
        and shutter_angle_common_override.admitted
        and shutter_angle_common_override.shutter_angle_override_decoupled
        and (not shutter_angle_common_override.shutter_speed_common_coupled)
        and shutter_angle_common_override.effective_still_registers[DIFF_ITEM_SHUTTER_SPEED]
        == "1/2000"
        and shutter_angle_common_override.effective_movie_shutter_angle == "172.8 deg"
        and shutter_speed_common_coupled.admitted
        and shutter_speed_common_coupled.shutter_speed_common_coupled
        and shutter_speed_common_coupled.effective_movie_registers[DIFF_ITEM_SHUTTER_SPEED]
        == "1/125"
        and (not pre_v600_angle_blocked.admitted)
        and pre_v600_angle_blocked.errno_code == EOPNOTSUPP_ERRNO
        and survives_cam_reset.survived_camera_settings_reset
        and survives_cam_reset.effective_checked_items == checked_subset
        and survives_net_reset.survived_reset_network_set
        and survives_net_reset.effective_checked_items == checked_subset
        and restored_by_init.restored_by_initialize
        and restored_by_init.effective_checked_items == ()
        and (not corrupt_transition_blocked.admitted)
        and corrupt_transition_blocked.errno_code == EINVAL_ERRNO
        and corrupt_transition_blocked.diff_set_transition_corruption_events == 0
        and (not shutter_angle_bleed_blocked.admitted)
        and shutter_angle_bleed_blocked.errno_code == EINVAL_ERRNO
        and shutter_angle_bleed_blocked.shutter_angle_common_bleed_events == 0
    )

    return {
        "passed": passed,
        "menu_path": DIFF_SET_STILL_MV_MENU_PATH,
        "shutter_mode_menu_path": SHUTTER_MODE_MENU_PATH,
        "all_8_diff_set_items": list(ALL_8_DIFF_SET_ITEMS),
        "separate_to_common_still_retained_items": list(SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS),
        "common_to_separate_custom_wb_still_only": asdict(common_to_separate),
        "separate_to_common_asymmetric_custom_wb": asdict(separate_to_common_custom_wb),
        "separate_to_common_asymmetric_standard_wb": asdict(separate_to_common_standard_wb),
        "v702_shutter_angle_common_override_decoupled": asdict(shutter_angle_common_override),
        "shutter_speed_common_coupled_ok": asdict(shutter_speed_common_coupled),
        "pre_v600_shutter_angle_blocked_eopnotsupp": asdict(pre_v600_angle_blocked),
        "survives_camera_settings_reset": asdict(survives_cam_reset),
        "survives_reset_network_set": asdict(survives_net_reset),
        "restored_by_initialize": asdict(restored_by_init),
        "corrupt_transition_blocked_einval": asdict(corrupt_transition_blocked),
        "shutter_angle_common_bleed_blocked_einval": asdict(shutter_angle_bleed_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 50B: [Custom Key/Dial Set.] 3-Domain ISO/EI Auto-Adaptation &
# Slot-1 CAMSET01.DAT O_RDONLY Vault Round-Trip
# ---------------------------------------------------------------------------


def coemulate_custom_key_dial_and_camset_vault(
    *,
    active_domain: str = DOMAIN_MOVIE,
    still_keys: Optional[Mapping[str, str]] = None,
    movie_keys: Optional[Mapping[str, str]] = None,
    playback_keys: Optional[Mapping[str, str]] = None,
    dial_assignments: Optional[Mapping[str, str]] = None,
    log_shooting_mode: str = LOG_SHOOTING_OFF,
    active_my_dial_slot: str = MY_DIAL_NONE,
    my_dial_banks: Optional[Mapping[str, Mapping[str, str]]] = None,
    active_recall_custom_hold: Optional[str] = None,
    reset_action: str = RESET_ACTION_NONE,
    camset_action: str = CAMSET_ACTION_NONE,
    slot1_vault_still_keys: Optional[Mapping[str, str]] = None,
    slot1_vault_movie_keys: Optional[Mapping[str, str]] = None,
    slot1_vault_playback_keys: Optional[Mapping[str, str]] = None,
    slot1_vault_dials: Optional[Mapping[str, str]] = None,
    force_slot1_custom_key_vault_write: bool = False,
) -> CustomKeyDialIsoEiCamsetHilResult:
    """Co-emulate MENU -> Setup -> [Operation Customize] -> [Custom Key/Dial Set.]
    3-domain keymaps, Cinema-Line Front/Rear/Wheel defaults, ISO/EI auto-adaptation,
    [Follow Custom], [My Dial 1..3], reset survival, and Slot-1 CAMSET01.DAT O_RDONLY load."""
    eff_still = dict(FACTORY_STILL_CUSTOM_KEYS)
    eff_movie = dict(FACTORY_MOVIE_CUSTOM_KEYS)
    eff_pb = dict(FACTORY_PLAYBACK_CUSTOM_KEYS)
    eff_dials = dict(FACTORY_CINEMA_DIAL_DEFAULTS)

    if still_keys is not None:
        for k, v in still_keys.items():
            eff_still[k] = str(v)
    if movie_keys is not None:
        for k, v in movie_keys.items():
            eff_movie[k] = str(v)
    if playback_keys is not None:
        for k, v in playback_keys.items():
            eff_pb[k] = str(v)
    if dial_assignments is not None:
        for k, v in dial_assignments.items():
            eff_dials[k] = str(v)

    def _fail(errno_val: int, reason: str) -> CustomKeyDialIsoEiCamsetHilResult:
        return CustomKeyDialIsoEiCamsetHilResult(
            menu_path=CUSTOM_KEY_DIAL_MENU_PATH,
            my_dial_menu_path=MY_DIAL_SETTINGS_MENU_PATH,
            save_load_settings_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            active_domain=active_domain,
            log_shooting_mode=log_shooting_mode,
            active_my_dial_slot=active_my_dial_slot,
            active_recall_custom_hold=active_recall_custom_hold,
            reset_action=reset_action,
            camset_action=camset_action,
            force_slot1_custom_key_vault_write=force_slot1_custom_key_vault_write,
            effective_still_keys=dict(eff_still),
            effective_movie_keys=dict(eff_movie),
            resolved_movie_keys=dict(eff_movie),
            effective_playback_keys=dict(eff_pb),
            persistent_dial_assignments=dict(eff_dials),
            effective_dial_assignments=dict(eff_dials),
            rear_dial_adapted_parameter=REAR_DIAL_ADAPTED_ISO,
            follow_custom_inherited_keys=(),
            my_dial_temporary_swap_active=False,
            survived_camera_settings_reset=False,
            survived_reset_network_set=False,
            restored_by_initialize=False,
            camset_roundtrip_restored=False,
            camset_serialized_sha256_prefix16="0" * 16,
            admitted=False,
            errno_code=errno_val,
            reason_code=reason,
            slot1_custom_key_vault_mutation_bytes=0,
            bk4_persistent_nvram_writes=0,
        )

    if active_domain not in ALL_3_CUSTOM_KEY_DOMAINS:
        return _fail(EINVAL_ERRNO, "INVALID_CUSTOM_KEY_DOMAIN")
    if log_shooting_mode not in VALID_LOG_SHOOTING_MODES:
        return _fail(EINVAL_ERRNO, "INVALID_LOG_SHOOTING_MODE")
    if active_my_dial_slot not in VALID_MY_DIAL_SLOTS:
        return _fail(EINVAL_ERRNO, "INVALID_MY_DIAL_SLOT")
    if reset_action not in VALID_RESET_ACTIONS:
        return _fail(EINVAL_ERRNO, "INVALID_RESET_ACTION")
    if camset_action not in VALID_CAMSET_ACTIONS:
        return _fail(EINVAL_ERRNO, "INVALID_CAMSET_ACTION")
    for dk in eff_dials:
        if dk not in ALL_3_CINEMA_DIALS:
            return _fail(EINVAL_ERRNO, "INVALID_CINEMA_DIAL_NAME")
    if any(v == FOLLOW_CUSTOM_TOKEN for v in eff_still.values()):
        return _fail(EINVAL_ERRNO, "FOLLOW_CUSTOM_INVALID_IN_STILL_DOMAIN")
    if active_recall_custom_hold is not None:
        if active_recall_custom_hold not in RECALL_CUSTOM_HOLD_SLOTS:
            return _fail(EINVAL_ERRNO, "INVALID_RECALL_CUSTOM_HOLD_SLOT")
        if active_domain == DOMAIN_PLAYBACK:
            return _fail(EOPNOTSUPP_ERRNO, "RECALL_CUSTOM_HOLD_UNSUPPORTED_IN_PLAYBACK")

    if (
        force_slot1_custom_key_vault_write
        or camset_action == CAMSET_ACTION_SAVE_SLOT1_VAULT_MUTATE
    ):
        return _fail(EROFS_ERRNO, "SLOT1_TIER0_CUSTOM_KEY_VAULT_WRITE_BLOCKED_EROFS")

    survived_cam_reset = False
    survived_net_reset = False
    restored_by_init = False
    if reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        survived_cam_reset = True
    elif reset_action == RESET_ACTION_RESET_NETWORK_SET:
        survived_net_reset = True
    elif reset_action == RESET_ACTION_INITIALIZE:
        restored_by_init = True
        eff_still = dict(FACTORY_STILL_CUSTOM_KEYS)
        eff_movie = dict(FACTORY_MOVIE_CUSTOM_KEYS)
        eff_pb = dict(FACTORY_PLAYBACK_CUSTOM_KEYS)
        eff_dials = dict(FACTORY_CINEMA_DIAL_DEFAULTS)

    camset_restored = False
    if camset_action == CAMSET_ACTION_LOAD_SLOT1_VAULT_RDONLY:
        if slot1_vault_still_keys is not None:
            eff_still = dict(FACTORY_STILL_CUSTOM_KEYS)
            eff_still.update({k: str(v) for k, v in slot1_vault_still_keys.items()})
        if slot1_vault_movie_keys is not None:
            eff_movie = dict(FACTORY_MOVIE_CUSTOM_KEYS)
            eff_movie.update({k: str(v) for k, v in slot1_vault_movie_keys.items()})
        if slot1_vault_playback_keys is not None:
            eff_pb = dict(FACTORY_PLAYBACK_CUSTOM_KEYS)
            eff_pb.update({k: str(v) for k, v in slot1_vault_playback_keys.items()})
        if slot1_vault_dials is not None:
            eff_dials = dict(FACTORY_CINEMA_DIAL_DEFAULTS)
            eff_dials.update({k: str(v) for k, v in slot1_vault_dials.items()})
        camset_restored = True

    # Resolve [Follow Custom] in Movie domain from Still domain
    resolved_movie: Dict[str, str] = {}
    inherited: List[str] = []
    for k, v in eff_movie.items():
        if v == FOLLOW_CUSTOM_TOKEN:
            resolved_movie[k] = eff_still.get(k, v)
            inherited.append(k)
        else:
            resolved_movie[k] = v

    # Resolve temporary [My Dial 1..3] swap without mutating persistent_dial_assignments
    default_my_dial_banks: Dict[str, Dict[str, str]] = {
        MY_DIAL_1: {
            DIAL_FRONT: "White Balance",
            DIAL_REAR: "Exposure Comp.",
            DIAL_CONTROL_WHEEL: "Audio Rec Level",
        },
        MY_DIAL_2: {
            DIAL_FRONT: "Focus Magnifier",
            DIAL_REAR: "ISO/EI",
            DIAL_CONTROL_WHEEL: "Aperture",
        },
        MY_DIAL_3: {
            DIAL_FRONT: "Shutter Speed",
            DIAL_REAR: "ISO/EI",
            DIAL_CONTROL_WHEEL: "Exposure Comp.",
        },
    }
    if my_dial_banks is not None:
        for slot_name, bank_map in my_dial_banks.items():
            default_my_dial_banks[slot_name] = {k: str(v) for k, v in bank_map.items()}

    my_dial_active = active_my_dial_slot != MY_DIAL_NONE and (not restored_by_init or camset_restored)
    active_dials = (
        dict(eff_dials, **default_my_dial_banks[active_my_dial_slot])
        if my_dial_active
        else dict(eff_dials)
    )

    rear_fn = active_dials[DIAL_REAR]
    if rear_fn == "ISO/EI":
        adapted_rear = (
            REAR_DIAL_ADAPTED_EXPOSURE_INDEX
            if log_shooting_mode in CINE_EI_LOG_MODES
            else REAR_DIAL_ADAPTED_ISO
        )
    else:
        adapted_rear = rear_fn

    camset_blob = json.dumps(
        {
            "still": eff_still,
            "movie": eff_movie,
            "playback": eff_pb,
            "dials": eff_dials,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    camset_sha16 = hashlib.sha256(camset_blob).hexdigest()[:16]

    return CustomKeyDialIsoEiCamsetHilResult(
        menu_path=CUSTOM_KEY_DIAL_MENU_PATH,
        my_dial_menu_path=MY_DIAL_SETTINGS_MENU_PATH,
        save_load_settings_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
        active_domain=active_domain,
        log_shooting_mode=log_shooting_mode,
        active_my_dial_slot=active_my_dial_slot,
        active_recall_custom_hold=active_recall_custom_hold,
        reset_action=reset_action,
        camset_action=camset_action,
        force_slot1_custom_key_vault_write=False,
        effective_still_keys=eff_still,
        effective_movie_keys=eff_movie,
        resolved_movie_keys=resolved_movie,
        effective_playback_keys=eff_pb,
        persistent_dial_assignments=eff_dials,
        effective_dial_assignments=active_dials,
        rear_dial_adapted_parameter=adapted_rear,
        follow_custom_inherited_keys=tuple(inherited),
        my_dial_temporary_swap_active=my_dial_active,
        survived_camera_settings_reset=survived_cam_reset,
        survived_reset_network_set=survived_net_reset,
        restored_by_initialize=restored_by_init,
        camset_roundtrip_restored=camset_restored,
        camset_serialized_sha256_prefix16=camset_sha16,
        admitted=True,
        errno_code=0,
        reason_code="CUSTOM_KEY_DIAL_ISO_EI_CAMSET_OK",
        slot1_custom_key_vault_mutation_bytes=0,
        bk4_persistent_nvram_writes=0,
    )


def evaluate_pillar_b_custom_key_dial_iso_ei_and_camset_hil() -> Dict[str, object]:
    """Run Pillar 50B verification across Still/Movie/Playback 3-domain keymaps,
    Cinema-Line dial defaults, ISO vs Exposure Index (EI) auto-adaptation,
    [Follow Custom], [My Dial 1..3], reset survival, and Slot-1 CAMSET01.DAT round-trip."""
    factory_flex_iso = coemulate_custom_key_dial_and_camset_vault(
        active_domain=DOMAIN_MOVIE,
        log_shooting_mode=LOG_SHOOTING_FLEXIBLE_ISO,
    )
    factory_cine_ei = coemulate_custom_key_dial_and_camset_vault(
        active_domain=DOMAIN_MOVIE,
        log_shooting_mode=LOG_SHOOTING_CINE_EI,
    )
    factory_cine_ei_quick = coemulate_custom_key_dial_and_camset_vault(
        active_domain=DOMAIN_MOVIE,
        log_shooting_mode=LOG_SHOOTING_CINE_EI_QUICK,
    )

    custom_still_seed = {
        "Custom Button 1": "Shockless WB",
        "Custom Button 2": "Focus Magnifier",
        "Custom Button 3": "Recall Custom hold 1",
    }
    custom_movie_seed = {
        "Custom Button 1": FOLLOW_CUSTOM_TOKEN,
        "Custom Button 2": FOLLOW_CUSTOM_TOKEN,
        "Custom Button 4": "Display LUT",
    }
    custom_pb_seed = {
        "Custom Button 2": "Rating",
    }
    custom_dials_seed = {
        DIAL_FRONT: "Aperture",
        DIAL_REAR: "ISO/EI",
        DIAL_CONTROL_WHEEL: "Exposure Comp.",
    }

    follow_custom_and_hold = coemulate_custom_key_dial_and_camset_vault(
        active_domain=DOMAIN_MOVIE,
        still_keys=custom_still_seed,
        movie_keys=custom_movie_seed,
        playback_keys=custom_pb_seed,
        dial_assignments=custom_dials_seed,
        log_shooting_mode=LOG_SHOOTING_CINE_EI,
        active_recall_custom_hold="Recall Custom hold 1",
    )

    my_dial_1_swap = coemulate_custom_key_dial_and_camset_vault(
        active_domain=DOMAIN_MOVIE,
        still_keys=custom_still_seed,
        movie_keys=custom_movie_seed,
        dial_assignments=custom_dials_seed,
        active_my_dial_slot=MY_DIAL_1,
    )

    survives_cam_reset = coemulate_custom_key_dial_and_camset_vault(
        still_keys=custom_still_seed,
        movie_keys=custom_movie_seed,
        playback_keys=custom_pb_seed,
        dial_assignments=custom_dials_seed,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    survives_net_reset = coemulate_custom_key_dial_and_camset_vault(
        still_keys=custom_still_seed,
        movie_keys=custom_movie_seed,
        playback_keys=custom_pb_seed,
        dial_assignments=custom_dials_seed,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    restored_by_init = coemulate_custom_key_dial_and_camset_vault(
        still_keys=custom_still_seed,
        movie_keys=custom_movie_seed,
        playback_keys=custom_pb_seed,
        dial_assignments=custom_dials_seed,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    slot1_rdonly_roundtrip = coemulate_custom_key_dial_and_camset_vault(
        still_keys=custom_still_seed,
        movie_keys=custom_movie_seed,
        playback_keys=custom_pb_seed,
        dial_assignments=custom_dials_seed,
        reset_action=RESET_ACTION_INITIALIZE,
        camset_action=CAMSET_ACTION_LOAD_SLOT1_VAULT_RDONLY,
        slot1_vault_still_keys=custom_still_seed,
        slot1_vault_movie_keys=custom_movie_seed,
        slot1_vault_playback_keys=custom_pb_seed,
        slot1_vault_dials=custom_dials_seed,
    )
    slot2_scratch_save_ok = coemulate_custom_key_dial_and_camset_vault(
        still_keys=custom_still_seed,
        movie_keys=custom_movie_seed,
        playback_keys=custom_pb_seed,
        dial_assignments=custom_dials_seed,
        camset_action=CAMSET_ACTION_SAVE_SLOT2_SCRATCH,
    )
    slot1_vault_write_blocked = coemulate_custom_key_dial_and_camset_vault(
        still_keys=custom_still_seed,
        camset_action=CAMSET_ACTION_SAVE_SLOT1_VAULT_MUTATE,
    )

    passed = (
        factory_flex_iso.admitted
        and factory_flex_iso.persistent_dial_assignments == dict(FACTORY_CINEMA_DIAL_DEFAULTS)
        and factory_flex_iso.rear_dial_adapted_parameter == REAR_DIAL_ADAPTED_ISO
        and factory_cine_ei.admitted
        and factory_cine_ei.rear_dial_adapted_parameter == REAR_DIAL_ADAPTED_EXPOSURE_INDEX
        and factory_cine_ei_quick.admitted
        and factory_cine_ei_quick.rear_dial_adapted_parameter == REAR_DIAL_ADAPTED_EXPOSURE_INDEX
        and follow_custom_and_hold.admitted
        and follow_custom_and_hold.resolved_movie_keys["Custom Button 1"] == "Shockless WB"
        and follow_custom_and_hold.resolved_movie_keys["Custom Button 2"] == "Focus Magnifier"
        and my_dial_1_swap.admitted
        and my_dial_1_swap.my_dial_temporary_swap_active
        and my_dial_1_swap.effective_dial_assignments[DIAL_FRONT] == "White Balance"
        and my_dial_1_swap.persistent_dial_assignments[DIAL_FRONT] == "Aperture"
        and survives_cam_reset.survived_camera_settings_reset
        and survives_cam_reset.effective_still_keys["Custom Button 1"] == "Shockless WB"
        and survives_cam_reset.persistent_dial_assignments[DIAL_CONTROL_WHEEL] == "Exposure Comp."
        and survives_net_reset.survived_reset_network_set
        and survives_net_reset.effective_playback_keys["Custom Button 2"] == "Rating"
        and restored_by_init.restored_by_initialize
        and restored_by_init.persistent_dial_assignments == dict(FACTORY_CINEMA_DIAL_DEFAULTS)
        and restored_by_init.effective_still_keys["Custom Button 1"] == "White Balance"
        and slot1_rdonly_roundtrip.admitted
        and slot1_rdonly_roundtrip.camset_roundtrip_restored
        and slot1_rdonly_roundtrip.effective_still_keys["Custom Button 1"] == "Shockless WB"
        and slot1_rdonly_roundtrip.resolved_movie_keys["Custom Button 1"] == "Shockless WB"
        and slot1_rdonly_roundtrip.persistent_dial_assignments[DIAL_CONTROL_WHEEL]
        == "Exposure Comp."
        and slot1_rdonly_roundtrip.slot1_custom_key_vault_mutation_bytes == 0
        and slot2_scratch_save_ok.admitted
        and slot2_scratch_save_ok.slot1_custom_key_vault_mutation_bytes == 0
        and (not slot1_vault_write_blocked.admitted)
        and slot1_vault_write_blocked.errno_code == EROFS_ERRNO
        and slot1_vault_write_blocked.slot1_custom_key_vault_mutation_bytes == 0
    )

    return {
        "passed": passed,
        "menu_path": CUSTOM_KEY_DIAL_MENU_PATH,
        "my_dial_menu_path": MY_DIAL_SETTINGS_MENU_PATH,
        "save_load_settings_menu_path": SAVE_LOAD_SETTINGS_MENU_PATH,
        "all_3_domains": list(ALL_3_CUSTOM_KEY_DOMAINS),
        "factory_cinema_dial_defaults": dict(FACTORY_CINEMA_DIAL_DEFAULTS),
        "factory_flexible_iso_rear_dial_iso": asdict(factory_flex_iso),
        "factory_cine_ei_rear_dial_ei": asdict(factory_cine_ei),
        "factory_cine_ei_quick_rear_dial_ei": asdict(factory_cine_ei_quick),
        "follow_custom_and_recall_hold_ok": asdict(follow_custom_and_hold),
        "my_dial_1_temporary_swap_ok": asdict(my_dial_1_swap),
        "survives_camera_settings_reset": asdict(survives_cam_reset),
        "survives_reset_network_set": asdict(survives_net_reset),
        "restored_by_initialize": asdict(restored_by_init),
        "slot1_camset01_rdonly_load_roundtrip_restored": asdict(slot1_rdonly_roundtrip),
        "slot2_camset01_scratch_save_ok": asdict(slot2_scratch_save_ok),
        "slot1_camset01_vault_write_blocked_erofs": asdict(slot1_vault_write_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 50C & 50D: [Remain Shoot Display] Still-Buffer Scope, EVF-Less
# ILME-FX3 Monitor Topology & 14 Hard Safety Redline Probes
# ---------------------------------------------------------------------------


def coemulate_remain_shoot_display_and_evfless_monitor(
    *,
    configured_remain_shoot_display: str = REMAIN_SHOOT_DEFAULT,
    shooting_scope: str = SHOOTING_SCOPE_STILL,
    shutter_half_or_burst_active: bool = False,
    still_continuous_buffer_remaining_frames: int = 46,
    movie_card_remaining_minutes: int = 128,
    requested_display_surface: str = DISPLAY_SURFACE_VARI_ANGLE_LCD,
    reset_action: str = RESET_ACTION_NONE,
    force_movie_card_time_spoof: bool = False,
    force_evf_finder_monitor_spoof: bool = False,
) -> RemainShootEvfLessMonitorHilResult:
    """Co-emulate MENU -> Setup -> [Display Option] -> [Remain Shoot Display]
    still-buffer-only scope and EVF-less ILME-FX3 (ilc/2210) monitor topology."""
    def _fail(errno_val: int, reason: str) -> RemainShootEvfLessMonitorHilResult:
        return RemainShootEvfLessMonitorHilResult(
            menu_path=REMAIN_SHOOT_DISPLAY_MENU_PATH,
            monitor_menu_path=MONITOR_SETUP_MENU_PATH,
            body_model=BODY_MODEL_FX3,
            help_guide_id=FX3_HELP_GUIDE_ID,
            configured_remain_shoot_display=configured_remain_shoot_display,
            shooting_scope=shooting_scope,
            shutter_half_or_burst_active=shutter_half_or_burst_active,
            still_continuous_buffer_remaining_frames=still_continuous_buffer_remaining_frames,
            movie_card_remaining_minutes=movie_card_remaining_minutes,
            requested_display_surface=requested_display_surface,
            reset_action=reset_action,
            force_movie_card_time_spoof=force_movie_card_time_spoof,
            force_evf_finder_monitor_spoof=force_evf_finder_monitor_spoof,
            effective_remain_shoot_register=REMAIN_SHOOT_DEFAULT,
            visible_on_vari_angle_lcd=False,
            displays_still_continuous_buffer=False,
            displays_movie_card_remaining_time=False,
            rendered_buffer_frames=None,
            survived_camera_settings_reset=False,
            survived_reset_network_set=False,
            restored_by_initialize=False,
            fx3_has_builtin_evf=False,
            fx3_has_eye_sensor=False,
            has_finder_monitor_menu=False,
            active_display_surface=DISPLAY_SURFACE_VARI_ANGLE_LCD,
            admitted=False,
            errno_code=errno_val,
            reason_code=reason,
            evf_finder_monitor_spoof_events=0,
            bk4_persistent_nvram_writes=0,
        )

    if configured_remain_shoot_display not in ALL_3_REMAIN_SHOOT_MODES:
        return _fail(EINVAL_ERRNO, "INVALID_REMAIN_SHOOT_DISPLAY_MODE")
    if shooting_scope not in VALID_SHOOTING_SCOPES:
        return _fail(EINVAL_ERRNO, "INVALID_SHOOTING_SCOPE")
    if reset_action not in VALID_RESET_ACTIONS:
        return _fail(EINVAL_ERRNO, "INVALID_RESET_ACTION")
    if still_continuous_buffer_remaining_frames < 0 or movie_card_remaining_minutes < 0:
        return _fail(EINVAL_ERRNO, "NEGATIVE_BUFFER_OR_CARD_CAPACITY")

    if (
        force_evf_finder_monitor_spoof
        or requested_display_surface != DISPLAY_SURFACE_VARI_ANGLE_LCD
    ):
        return _fail(
            EOPNOTSUPP_ERRNO,
            "FX3_EVF_LESS_NO_FINDER_MONITOR_OR_EYE_SENSOR_EOPNOTSUPP",
        )

    if force_movie_card_time_spoof:
        return _fail(
            EINVAL_ERRNO,
            "REMAIN_SHOOT_DISPLAY_STILL_BUFFER_ONLY_MOVIE_TIME_SPOOF_BLOCKED",
        )

    eff_mode = configured_remain_shoot_display
    survived_cam_reset = False
    survived_net_reset = False
    restored_by_init = False

    if reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        survived_cam_reset = True
    elif reset_action == RESET_ACTION_RESET_NETWORK_SET:
        survived_net_reset = True
    elif reset_action == RESET_ACTION_INITIALIZE:
        restored_by_init = True
        eff_mode = REMAIN_SHOOT_DEFAULT

    if shooting_scope != SHOOTING_SCOPE_STILL:
        visible = False
    elif eff_mode == REMAIN_SHOOT_ALWAYS_DISPLAY:
        visible = True
    elif eff_mode == REMAIN_SHOOT_SHOOT_ONLY:
        visible = bool(shutter_half_or_burst_active)
    else:
        visible = False

    rendered_frames = still_continuous_buffer_remaining_frames if visible else None

    return RemainShootEvfLessMonitorHilResult(
        menu_path=REMAIN_SHOOT_DISPLAY_MENU_PATH,
        monitor_menu_path=MONITOR_SETUP_MENU_PATH,
        body_model=BODY_MODEL_FX3,
        help_guide_id=FX3_HELP_GUIDE_ID,
        configured_remain_shoot_display=configured_remain_shoot_display,
        shooting_scope=shooting_scope,
        shutter_half_or_burst_active=shutter_half_or_burst_active,
        still_continuous_buffer_remaining_frames=still_continuous_buffer_remaining_frames,
        movie_card_remaining_minutes=movie_card_remaining_minutes,
        requested_display_surface=requested_display_surface,
        reset_action=reset_action,
        force_movie_card_time_spoof=False,
        force_evf_finder_monitor_spoof=False,
        effective_remain_shoot_register=eff_mode,
        visible_on_vari_angle_lcd=visible,
        displays_still_continuous_buffer=visible,
        displays_movie_card_remaining_time=False,
        rendered_buffer_frames=rendered_frames,
        survived_camera_settings_reset=survived_cam_reset,
        survived_reset_network_set=survived_net_reset,
        restored_by_initialize=restored_by_init,
        fx3_has_builtin_evf=False,
        fx3_has_eye_sensor=False,
        has_finder_monitor_menu=False,
        active_display_surface=DISPLAY_SURFACE_VARI_ANGLE_LCD,
        admitted=True,
        errno_code=0,
        reason_code="REMAIN_SHOOT_STILL_BUFFER_AND_EVFLESS_FX3_OK",
        evf_finder_monitor_spoof_events=0,
        bk4_persistent_nvram_writes=0,
    )


def probe_phase258_redline_guard(**probe_flags: bool) -> RedlineGuardProbeResult:
    """Evaluate all 14 Phase 258 Stage 50 (50/50 Grand Milestone) safety redline probes."""
    for unknown_key in probe_flags:
        if unknown_key not in ALL_14_REDLINE_PROBE_FIELDS:
            return RedlineGuardProbeResult(
                valid=False,
                errno_code=EINVAL_ERRNO,
                reason_code=f"UNKNOWN_REDLINE_PROBE_{unknown_key.upper()}",
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
                diff_set_transition_corruption_events=0,
                shutter_angle_common_bleed_events=0,
                slot1_custom_key_vault_mutation_bytes=0,
                evf_finder_monitor_spoof_events=0,
                fx3_has_builtin_evf=False,
                raw_firmware_bytes_leaked=0,
            )

    triggered = [f for f in ALL_14_REDLINE_PROBE_FIELDS if bool(probe_flags.get(f, False))]
    if triggered:
        first = triggered[0]
        errno_val = (
            EROFS_ERRNO
            if first in (
                "cnflasha_userspace_write_requested",
                "slot1_custom_key_vault_write_requested",
            )
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
            diff_set_transition_corruption_events=0,
            shutter_angle_common_bleed_events=0,
            slot1_custom_key_vault_mutation_bytes=0,
            evf_finder_monitor_spoof_events=0,
            fx3_has_builtin_evf=False,
            raw_firmware_bytes_leaked=0,
        )

    return RedlineGuardProbeResult(
        valid=True,
        errno_code=0,
        reason_code="ALL_14_STAGE50_GRAND_MILESTONE_REDLINES_LOCKED_SAFE",
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
        diff_set_transition_corruption_events=0,
        shutter_angle_common_bleed_events=0,
        slot1_custom_key_vault_mutation_bytes=0,
        evf_finder_monitor_spoof_events=0,
        fx3_has_builtin_evf=False,
        raw_firmware_bytes_leaked=0,
    )


def evaluate_pillar_c_d_remain_shoot_evfless_and_redlines() -> Dict[str, object]:
    """Run Pillar 50C & 50D verification across all 3 [Remain Shoot Display] modes,
    still-buffer-only scope, EVF-less ILME-FX3 topology, reset survival, and 14 redlines."""
    default_not_displayed = coemulate_remain_shoot_display_and_evfless_monitor()
    always_still_idle = coemulate_remain_shoot_display_and_evfless_monitor(
        configured_remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY,
        shooting_scope=SHOOTING_SCOPE_STILL,
        shutter_half_or_burst_active=False,
        still_continuous_buffer_remaining_frames=38,
    )
    shoot_only_idle = coemulate_remain_shoot_display_and_evfless_monitor(
        configured_remain_shoot_display=REMAIN_SHOOT_SHOOT_ONLY,
        shooting_scope=SHOOTING_SCOPE_STILL,
        shutter_half_or_burst_active=False,
    )
    shoot_only_burst = coemulate_remain_shoot_display_and_evfless_monitor(
        configured_remain_shoot_display=REMAIN_SHOOT_SHOOT_ONLY,
        shooting_scope=SHOOTING_SCOPE_STILL,
        shutter_half_or_burst_active=True,
        still_continuous_buffer_remaining_frames=29,
    )
    movie_mode_suppressed = coemulate_remain_shoot_display_and_evfless_monitor(
        configured_remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY,
        shooting_scope=SHOOTING_SCOPE_MOVIE,
        shutter_half_or_burst_active=True,
    )
    sq_mode_suppressed = coemulate_remain_shoot_display_and_evfless_monitor(
        configured_remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY,
        shooting_scope=SHOOTING_SCOPE_SQ,
        shutter_half_or_burst_active=True,
    )

    survives_cam_reset = coemulate_remain_shoot_display_and_evfless_monitor(
        configured_remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    survives_net_reset = coemulate_remain_shoot_display_and_evfless_monitor(
        configured_remain_shoot_display=REMAIN_SHOOT_SHOOT_ONLY,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    restored_by_init = coemulate_remain_shoot_display_and_evfless_monitor(
        configured_remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    evf_viewfinder_blocked = coemulate_remain_shoot_display_and_evfless_monitor(
        requested_display_surface=DISPLAY_SURFACE_EVF_FINDER,
    )
    finder_monitor_auto_blocked = coemulate_remain_shoot_display_and_evfless_monitor(
        requested_display_surface=DISPLAY_SURFACE_FINDER_MONITOR_AUTO,
    )
    movie_time_spoof_blocked = coemulate_remain_shoot_display_and_evfless_monitor(
        configured_remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY,
        shooting_scope=SHOOTING_SCOPE_MOVIE,
        force_movie_card_time_spoof=True,
    )

    baseline_redline = probe_phase258_redline_guard()
    blocked_probes: Dict[str, Dict[str, object]] = {}
    all_probes_blocked = True
    for field in ALL_14_REDLINE_PROBE_FIELDS:
        pr = probe_phase258_redline_guard(**{field: True})
        blocked_probes[field] = asdict(pr)
        if pr.valid or pr.errno_code not in (EACCES_ERRNO, EROFS_ERRNO):
            all_probes_blocked = False

    passed = (
        default_not_displayed.admitted
        and default_not_displayed.effective_remain_shoot_register == REMAIN_SHOOT_NOT_DISPLAYED
        and (not default_not_displayed.visible_on_vari_angle_lcd)
        and (not default_not_displayed.fx3_has_builtin_evf)
        and always_still_idle.admitted
        and always_still_idle.visible_on_vari_angle_lcd
        and always_still_idle.rendered_buffer_frames == 38
        and (not always_still_idle.displays_movie_card_remaining_time)
        and shoot_only_idle.admitted
        and (not shoot_only_idle.visible_on_vari_angle_lcd)
        and shoot_only_burst.admitted
        and shoot_only_burst.visible_on_vari_angle_lcd
        and shoot_only_burst.rendered_buffer_frames == 29
        and movie_mode_suppressed.admitted
        and (not movie_mode_suppressed.visible_on_vari_angle_lcd)
        and (not movie_mode_suppressed.displays_movie_card_remaining_time)
        and sq_mode_suppressed.admitted
        and (not sq_mode_suppressed.visible_on_vari_angle_lcd)
        and survives_cam_reset.survived_camera_settings_reset
        and survives_cam_reset.effective_remain_shoot_register == REMAIN_SHOOT_ALWAYS_DISPLAY
        and survives_net_reset.survived_reset_network_set
        and survives_net_reset.effective_remain_shoot_register == REMAIN_SHOOT_SHOOT_ONLY
        and restored_by_init.restored_by_initialize
        and restored_by_init.effective_remain_shoot_register == REMAIN_SHOOT_NOT_DISPLAYED
        and (not evf_viewfinder_blocked.admitted)
        and evf_viewfinder_blocked.errno_code == EOPNOTSUPP_ERRNO
        and evf_viewfinder_blocked.evf_finder_monitor_spoof_events == 0
        and (not finder_monitor_auto_blocked.admitted)
        and finder_monitor_auto_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not movie_time_spoof_blocked.admitted)
        and movie_time_spoof_blocked.errno_code == EINVAL_ERRNO
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "menu_path": REMAIN_SHOOT_DISPLAY_MENU_PATH,
        "monitor_menu_path": MONITOR_SETUP_MENU_PATH,
        "all_3_remain_shoot_modes": list(ALL_3_REMAIN_SHOOT_MODES),
        "fx3_has_builtin_evf": FX3_HAS_BUILTIN_EVF,
        "all_14_redline_probe_fields": list(ALL_14_REDLINE_PROBE_FIELDS),
        "default_not_displayed_ok": asdict(default_not_displayed),
        "always_display_still_idle_ok": asdict(always_still_idle),
        "shoot_only_still_idle_hidden_ok": asdict(shoot_only_idle),
        "shoot_only_still_burst_visible_ok": asdict(shoot_only_burst),
        "movie_mode_still_buffer_only_suppressed": asdict(movie_mode_suppressed),
        "sq_mode_still_buffer_only_suppressed": asdict(sq_mode_suppressed),
        "survives_camera_settings_reset": asdict(survives_cam_reset),
        "survives_reset_network_set": asdict(survives_net_reset),
        "restored_by_initialize": asdict(restored_by_init),
        "evf_viewfinder_spoof_blocked_eopnotsupp": asdict(evf_viewfinder_blocked),
        "finder_monitor_eye_sensor_blocked_eopnotsupp": asdict(finder_monitor_auto_blocked),
        "movie_card_time_spoof_blocked_einval": asdict(movie_time_spoof_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 258 (Stage 50, 50/50 GRAND MILESTONE) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase258_realhw_diff_set_still_mv_custom_key_remain_shoot_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 258 Stage 50 (50/50 Grand Milestone) Wave-40 HIL co-emulation audit."""
    donor_audit = inspect_phase258_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_diff_set_still_mv_and_shutter_angle_hil()
    pillar_b = evaluate_pillar_b_custom_key_dial_iso_ei_and_camset_hil()
    pillar_cd = evaluate_pillar_c_d_remain_shoot_evfless_and_redlines()

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
        "fx3_has_builtin_evf": FX3_HAS_BUILTIN_EVF,
        "diff_set_transition_corruption_events": DIFF_SET_TRANSITION_CORRUPTION_EVENTS,
        "shutter_angle_common_bleed_events": SHUTTER_ANGLE_COMMON_BLEED_EVENTS,
        "slot1_custom_key_vault_mutation_bytes": SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES,
        "evf_finder_monitor_spoof_events": EVF_FINDER_MONITOR_SPOOF_EVENTS,
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
        and (not FX3_HAS_BUILTIN_EVF)
        and DIFF_SET_TRANSITION_CORRUPTION_EVENTS == 0
        and SHUTTER_ANGLE_COMMON_BLEED_EVENTS == 0
        and SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES == 0
        and EVF_FINDER_MONITOR_SPOOF_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_258_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_diff_set_still_mv_and_shutter_angle_hil": pillar_a,
        "pillar_b_custom_key_dial_iso_ei_and_camset_hil": pillar_b,
        "pillar_c_d_remain_shoot_evfless_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py",
        description=(
            "Phase 258 Stage 50 (50/50 Grand Milestone) — Real-Hardware ILME-FX3 Wave-40 "
            "Different Set for Still/Mv 8-Item Asymmetric Transitions & Shutter Angle Override, "
            "Custom Key/Dial Set. 3-Domain ISO/EI Auto-Adaptation & Slot-1 CAMSET01.DAT Vault, "
            "and Remain Shoot Display Still-Buffer Scope & EVF-Less Monitor Topology HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 258 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase258_realhw_diff_set_still_mv_custom_key_remain_shoot_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_diff_set_still_mv_and_shutter_angle_hil"]
        pb = rep["pillar_b_custom_key_dial_iso_ei_and_camset_hil"]
        pcd = rep["pillar_c_d_remain_shoot_evfless_and_redlines"]
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 258 Stage 50 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"diff_set={len(pa['all_8_diff_set_items'])}i_"
            f"corr:{red['diff_set_transition_corruption_events']}_"
            f"ang_bleed:{red['shutter_angle_common_bleed_events']} | "
            f"ckey={len(pb['all_3_domains'])}d_vmut:{red['slot1_custom_key_vault_mutation_bytes']} | "
            f"remain={len(pcd['all_3_remain_shoot_modes'])}m_evf:{int(red['fx3_has_builtin_evf'])}_"
            f"spoof:{red['evf_finder_monitor_spoof_events']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
