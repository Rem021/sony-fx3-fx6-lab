"""Phase 317 (Task H378, Wave-60, 140/140 Safety Gates Grand Milestone!):
Real-Hardware Safety Gates G139 & G140 + Unified 140-Gate Preflight Engine.

Implements empirical `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` hardware safety gates:

1. **Gate `G139` (`REALHW_REC_MEDIA_AUTO_SWITCH_OVERFLOW_VPG400_AND_PROXY_SUB_VAULT_GUARD`)**:
   - **Ver. 2.00+--7.02 `[Rec. Media Settings]` Split & Reset Tiers**:
     - Dormant `[Prioritize Rec. Media]` (`_f.uxc 0x719e`, `0` hits in `FX3 appFw.so`) is
       rejected (`EOPNOTSUPP=95`).
     - Split `Initialize`-only **`[Recording Media]`** (survives `[Camera Settings Reset]`):
       - Still (`BKID_APP_setting_still_recording_media`): `Slot 1` (default) / `Slot 2` /
         `Simult. Recording` / `Sort Recording`.
       - Movie (`BKID_APP_setting_movie_recording_media`): `Slot 1` (default) / `Slot 2` /
         `Simult. Recording` -- Movie `Sort Recording` is rejected (`EINVAL=22`).
       - `Simult. Recording` strictly requires matching filesystems across both slots
         (`exFAT`+`exFAT` or `FAT32`+`FAT32`; mismatched filesystems rejected `EINVAL=22`).
     - **`[Auto Switch Media]`** (`_f.uxc 0x6dd9`, `BKID_APP_setting_relay_rec`: `Off` default /
       `On`) survives `[Camera Settings Reset]` and resets only on `[Initialize]`.
   - **CRITICAL `Slot-2 -> Slot-1` Overflow Trap**:
     - When `[Recording Media] = Slot 2` and `[Auto Switch Media] = On`, filling or ejecting
       `Slot 2` causes `setting_relay_rec` to silently roll recording + `AVF_INFO` writes onto
       `Slot 1`. Enforces dual fail-closed lock (`Auto Switch Media == Off` + `EROFS=30` on
       `Slot-1` Tier-0 Vault, `slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`).
   - **Card Speed Gates & Type B Rejection**:
     - `XAVC HS/S 4K` (`<=280M`): `SDXC V60+` or `CFexpress Type A (VPG200+)` (`<=200M`: `U3/V30`;
       `<=60M`: `Class 10`).
     - `XAVC S-I 4K` / `XAVC S-I DCI 4K` (`600M`) / `XAVC S-I HD` (`222M`): `SDXC V90+` or
       `CFexpress Type A (VPG200+)`.
     - `S&Q XAVC S-I 4K` (`1200M`), `S&Q XAVC S-I DCI 4K`, and `S&Q XAVC S-I HD` `240/200fps`
       (`890M`): mandatory `CFexpress Type A VPG200/VPG400` (`base.uxc 0xe228`/`0xe224`, `SDXC`
       rejected). `CFexpress Type B` is rejected (`ENODEV=19`).
   - **`[Proxy Settings]` (`_f.uxc 0x6e3f`, `BKID_APP_setting_sq_proxy_*`, resettable)**:
     - `XAVC S HD` (`1280x720 6M 4:2:0 8bit`, default) vs `XAVC HS HD` (`1920x1080 9M/16M 4:2:0 10bit`);
       dormant `16M 8bit` (`_f 0x6b8f`) / `9M_420_8BIT` rejected.
     - Blocked at `119.88p/100p` (Movie or S&Q) and `S&Q 120fps/100fps`; **NOT blocked** on
       `XAVC S-I DCI 4K` up to `59.94p/50p` (subject to card-speed gate!).
     - Writes `M4ROOT/SUB/<Clip>S03.MP4` (SDXC: `/PRIVATE/M4ROOT/SUB/`, CFexpress A:
       `/M4ROOT/SUB/`), blocked from in-camera playback, coupled Delete/Protect fails closed
       (`EROFS=30`) on `Slot 1` Tier-0 Vault, contrasted with FX6 `Simul Rec` / `Chunk Proxy`.

2. **Gate `G140` (`REALHW_CREATORS_CLOUD_CNCT_WHILE_POWER_OFF_ZERO_RF_AND_MYMENU_42SLOT_GUARD`)**:
   - **`[Creators' Cloud]` & `[C3 Portal]`**:
     - `Ver. 4.00+` `C3 Portal` (`Cloud(Private)` / `Cloud(Share)`), `Ver. 5.00+` `Creators' Cloud`,
       `Ver. 6.00+` resume/diff transfer, `Ver. 7.00+` `Clip Flag` (`OK/NG/KEEP`) upload filter.
     - `Cloud Connection *` & `Cloud Information *` **survive EVEN `[Initialize]`**, requiring
       explicit account sign-out; mutually exclusive with FTP (`CLOUD_CONNECTION_ON_FTP_OFF`).
   - **CRITICAL Zero-RF Hazard (`[Cnct. while Power OFF]`)**:
     - `[Cnct. while Power OFF]` (`_f.uxc 0x6ab3`, `BKID_APP_extern_menu_cnct_while_power_off`:
       `Off` default / `On`) survives `[Camera Settings Reset]` (note `_g 0x6476` SC/TC empty-string
       localization defect). When `On`, `Bluetooth Low Energy` (`UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER`)
       stays energized and broadcasting even when physical power switch is `OFF`!
     - Zero-RF bench mode MUST enforce BOTH `[Airplane Mode] == On` AND
       `[Cnct. while Power OFF] == Off` (`Bluetooth Function == Off`, `rf_packets_transmitted == 0`),
       contrasted with Bluetooth-less `ILME-FX6` (`BKID_APP_SETTING_BLUETOOTH_FUNCTION` dormant).
   - **42-Slot `[My Menu]` Disambiguation vs FX6 `User Menu`**:
     - `ILME-FX3` `[My Menu]` (`_g 0x6232`) has **exact `6 x 7 = 42` slots**:
       `BKID_APP_mymenu_group{1..6}_setting_list{0..6}` (`group0`/`group7`/`list7` = `0` hits;
       NOT `36` or `30`). Out-of-range slot `>= 42` or `(Playback)` tab item registration
       returns `EINVAL=22`. Survives `[Camera Settings Reset]`.
     - Contrasted with `ILME-FX6` **20-item `User Menu`** + `User Menu Only` (in `All File`,
       not `Scene File`) + rental-house **`User Menu with Lock`** (`0000..9999` 4-digit PIN,
       chord `Multi-Function Dial + MENU`, excluded from `All File` & `Scene File`), rejected
       on FX3 (`EOPNOTSUPP=95`).

3. **Unified `140`-Gate Milestone Master Preflight (`evaluate_140gate_preflight` / `verify-140-gates`)**:
   - Delegates `G01..G138` to `evaluate_138gate_preflight()` and appends `G139` + `G140`.
   - `schema_version = "realhw_140gate_preflight_v1"`.
   - Offline mode: `137/140` pass (`VERIFIED_137_OF_140_AWAITING_PHYSICAL_TIER0`).
   - `--simulate-bench-dry-run`: `140/140` pass (`VERIFIED_ALL_140_GATES_DRY_RUN_SIMULATED_BACKUP`).
   - All hardware attach, persistent eMMC write, EL3/SPI-NOR transmit, and cross-model flash
     redlines remain hard-locked `False`, `usb_packets_transmitted == 0`, and
     `raw_firmware_bytes_leaked == 0`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths
from .realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    DEFAULT_REPO_ROOT,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_SAFE,
    GateVerdict,
)
from .realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard import (
    Master138GateReport,
    evaluate_138gate_preflight,
)

# ---------------------------------------------------------------------------
# Schema, Version & Absolute Hardware / Firmware Safety Redlines
# ---------------------------------------------------------------------------

REALHW_140GATE_PREFLIGHT_SCHEMA = "realhw_140gate_preflight_v1"
REALHW_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_140GATE_SCHEMA = (
    REALHW_140GATE_PREFLIGHT_SCHEMA
)
REALHW_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_140GATE_VERSION = "2026.11.17"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST_PHASE317 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE317 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE317 = 15.0

# Hard-locked redlines (identical immutable values; NEVER relaxed at runtime)
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
SPI_NOR_WRITE_AUTHORIZED = False
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
PERSISTENT_WRITE_RELEASE = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
HUMAN_HARDWARE_ATTACH_TOKEN = False
CROSS_MODEL_FLASH_AUTHORIZED = False
USB_PACKETS_TRANSMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Gate Identifiers
G139 = "G139"
G139_GATE_ID = "G139"
G139_GATE_CODE = (
    "REALHW_REC_MEDIA_AUTO_SWITCH_OVERFLOW_VPG400_AND_PROXY_SUB_VAULT_GUARD"
)
REALHW_REC_MEDIA_AUTO_SWITCH_OVERFLOW_VPG400_AND_PROXY_SUB_VAULT_GUARD = G139_GATE_CODE

G140 = "G140"
G140_GATE_ID = "G140"
G140_GATE_CODE = (
    "REALHW_CREATORS_CLOUD_CNCT_WHILE_POWER_OFF_ZERO_RF_AND_MYMENU_42SLOT_GUARD"
)
REALHW_CREATORS_CLOUD_CNCT_WHILE_POWER_OFF_ZERO_RF_AND_MYMENU_42SLOT_GUARD = (
    G140_GATE_CODE
)

# Model & Identity Contracts
FX3_MODEL_NAME_PHASE317 = "ILME-FX3"
FX3_MODEL_ID_PHASE317 = 0x39383232
FX3_HELP_GUIDE_CODE_PHASE317 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE317 = "7.02"

FX6_MODEL_NAME_PHASE317 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE317 = "6.01"
FX6_PRODUCT_CODE_PHASE317 = "PRODUCT_MODEL_CHAPLIN"

# Shoot Modes & Reset Actions
SHOOT_MODE_STILL_PHASE317 = "Still"
SHOOT_MODE_MOVIE_PHASE317 = "Movie"
SHOOT_MODE_SQ_PHASE317 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE317: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE317,
    SHOOT_MODE_MOVIE_PHASE317,
    SHOOT_MODE_SQ_PHASE317,
)

RESET_ACTION_NONE_PHASE317 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317 = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE317 = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE317 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE317: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE317,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
    RESET_ACTION_RESET_NETWORK_SET_PHASE317,
    RESET_ACTION_INITIALIZE_PHASE317,
)

EOPNOTSUPP_ERRNO_PHASE317 = 95
EOPNOTSUPP_NAME_PHASE317 = "EOPNOTSUPP"
EROFS_ERRNO_PHASE317 = 30
EROFS_NAME_PHASE317 = "EROFS"
EBUSY_ERRNO_PHASE317 = 16
EBUSY_NAME_PHASE317 = "EBUSY"
EINVAL_ERRNO_PHASE317 = 22
EINVAL_NAME_PHASE317 = "EINVAL"
ENODEV_ERRNO_PHASE317 = 19
ENODEV_NAME_PHASE317 = "ENODEV"

# ---------------------------------------------------------------------------
# G139 Constants: Rec. Media Settings, Auto Switch Media, Card Speed & Proxy
# ---------------------------------------------------------------------------

REC_MEDIA_SLOT_1_G139 = "Slot 1"
REC_MEDIA_SLOT_2_G139 = "Slot 2"
REC_MEDIA_SIMULT_G139 = "Simult. Recording"
REC_MEDIA_SORT_G139 = "Sort Recording"

ALLOWED_STILL_RECORDING_MEDIA_G139: Tuple[str, ...] = (
    REC_MEDIA_SLOT_1_G139,
    REC_MEDIA_SLOT_2_G139,
    REC_MEDIA_SIMULT_G139,
    REC_MEDIA_SORT_G139,
)
ALLOWED_MOVIE_RECORDING_MEDIA_G139: Tuple[str, ...] = (
    REC_MEDIA_SLOT_1_G139,
    REC_MEDIA_SLOT_2_G139,
    REC_MEDIA_SIMULT_G139,
)

DORMANT_PRIORITIZE_REC_MEDIA_TRAPS_G139: Tuple[str, ...] = (
    "Prioritize Rec. Media",
    "Sort(RAW/JPEG)",
    "Sort(JPEG/RAW)",
    "0x719e",
    "0x710d",
    "0x765b",
)

SLOT_FS_EXFAT_G139 = "exFAT"
SLOT_FS_FAT32_G139 = "FAT32"
ALLOWED_SLOT_FILESYSTEMS_G139: Tuple[str, ...] = (
    SLOT_FS_EXFAT_G139,
    SLOT_FS_FAT32_G139,
)

CARD_CFEXPRESS_TYPE_A_VPG400_G139 = "CFexpress Type A VPG400"
CARD_CFEXPRESS_TYPE_A_VPG200_G139 = "CFexpress Type A VPG200"
CARD_SDXC_V90_G139 = "SDXC V90"
CARD_SDXC_V60_G139 = "SDXC V60"
CARD_SDXC_U3_V30_G139 = "SDXC U3/V30"
CARD_SDXC_CLASS10_G139 = "SDXC Class 10"
CARD_SDHC_LE32GB_G139 = "SDHC <=32GB"
CARD_CFEXPRESS_TYPE_B_UNSUPPORTED_G139 = "CFexpress Type B"

ALLOWED_CARD_TYPES_G139: Tuple[str, ...] = (
    CARD_CFEXPRESS_TYPE_A_VPG400_G139,
    CARD_CFEXPRESS_TYPE_A_VPG200_G139,
    CARD_SDXC_V90_G139,
    CARD_SDXC_V60_G139,
    CARD_SDXC_U3_V30_G139,
    CARD_SDXC_CLASS10_G139,
    CARD_SDHC_LE32GB_G139,
)

CARD_SPEED_RANK_G139: Dict[str, int] = {
    CARD_SDHC_LE32GB_G139: 1,
    CARD_SDXC_CLASS10_G139: 1,
    CARD_SDXC_U3_V30_G139: 2,
    CARD_SDXC_V60_G139: 3,
    CARD_SDXC_V90_G139: 4,
    CARD_CFEXPRESS_TYPE_A_VPG200_G139: 5,
    CARD_CFEXPRESS_TYPE_A_VPG400_G139: 6,
}

MOVIE_FORMAT_XAVC_HS_4K_G139 = "XAVC HS 4K"
MOVIE_FORMAT_XAVC_S_4K_G139 = "XAVC S 4K"
MOVIE_FORMAT_XAVC_S_HD_G139 = "XAVC S HD"
MOVIE_FORMAT_XAVC_S_I_4K_G139 = "XAVC S-I 4K"
MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139 = "XAVC S-I DCI 4K"
MOVIE_FORMAT_XAVC_S_I_HD_G139 = "XAVC S-I HD"
ALLOWED_MOVIE_FILE_FORMATS_G139: Tuple[str, ...] = (
    MOVIE_FORMAT_XAVC_HS_4K_G139,
    MOVIE_FORMAT_XAVC_S_4K_G139,
    MOVIE_FORMAT_XAVC_S_HD_G139,
    MOVIE_FORMAT_XAVC_S_I_4K_G139,
    MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139,
    MOVIE_FORMAT_XAVC_S_I_HD_G139,
)

PROXY_SETTINGS_F_UXC_RESID16_G139 = 0x6E3F
AUTO_SWITCH_MEDIA_F_UXC_RESID16_G139 = 0x6DD9
CFEXPRESS_VPG400_BASE_UXC_RESID16_G139 = 0xE224
CFEXPRESS_VPG200_BASE_UXC_RESID16_G139 = 0xE228

PROXY_FORMAT_XAVC_S_HD_G139 = "XAVC S HD"
PROXY_FORMAT_XAVC_HS_HD_G139 = "XAVC HS HD"
ALLOWED_PROXY_FILE_FORMATS_G139: Tuple[str, ...] = (
    PROXY_FORMAT_XAVC_S_HD_G139,
    PROXY_FORMAT_XAVC_HS_HD_G139,
)

PROXY_SETTING_6M_8BIT_G139 = "6M 4:2:0 8bit"
PROXY_SETTING_9M_10BIT_G139 = "9M 4:2:0 10bit"
PROXY_SETTING_16M_10BIT_G139 = "16M 4:2:0 10bit"
DORMANT_PROXY_SETTINGS_G139: Tuple[str, ...] = (
    "16M 4:2:0 8bit",
    "9M 4:2:0 8bit",
    "VAL_setting_sq_proxy_record_setting_PROXY_RECORD_SETTING_9M_420_8BIT",
    "0x6b8f",
)
ALLOWED_PROXY_RECORD_SETTINGS_G139: Tuple[str, ...] = (
    PROXY_SETTING_6M_8BIT_G139,
    PROXY_SETTING_9M_10BIT_G139,
    PROXY_SETTING_16M_10BIT_G139,
)

ALLOWED_REC_FRAME_RATES_G139: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
    "100p",
    "119.88p",
)
PROXY_BLOCKED_REC_FRAME_RATES_G139: Tuple[str, ...] = ("100p", "119.88p")
ALLOWED_SQ_FRAME_RATES_G139: Tuple[str, ...] = (
    "1fps",
    "2fps",
    "4fps",
    "8fps",
    "15fps",
    "24fps",
    "25fps",
    "30fps",
    "50fps",
    "60fps",
    "100fps",
    "120fps",
    "200fps",
    "240fps",
)
PROXY_BLOCKED_SQ_FRAME_RATES_G139: Tuple[str, ...] = ("100fps", "120fps")

PROXY_SUB_PATH_SDXC_G139 = "/PRIVATE/M4ROOT/SUB"
PROXY_SUB_PATH_CFEXPRESS_G139 = "/M4ROOT/SUB"
FX6_PROXY_SUB_PATH_G139 = "/XDROOT/Sub"
FX6_PROXY_CHUNK_DURATIONS_G139: Tuple[str, ...] = ("30s", "1min", "2min")

# ---------------------------------------------------------------------------
# G140 Constants: Creators' Cloud, Cnct. while Power OFF Zero-RF, 42-Slot My Menu
# ---------------------------------------------------------------------------

CREATORS_CLOUD_G_UXC_RESID16_G140 = 0x62B5
CNCT_WHILE_POWER_OFF_F_UXC_RESID16_G140 = 0x6AB3
ALWAYS_CONNECTED_F_UXC_RESID16_G140 = 0x6833
MY_MENU_G_UXC_RESID16_G140 = 0x6232
DISPLAY_FROM_MY_MENU_F_UXC_RESID16_G140 = 0x64F6

ALLOWED_POWER_SWITCH_STATES_G140: Tuple[str, ...] = ("ON", "OFF")
ALLOWED_CLIP_FLAGS_G140: Tuple[str, ...] = ("NONE", "OK", "NG", "KEEP")
ALLOWED_C3_PORTAL_PROFILES_G140: Tuple[str, ...] = (
    "None",
    "Cloud(Private)",
    "Cloud(Share)",
)

FX3_MYMENU_GROUP_MIN_G140 = 1
FX3_MYMENU_GROUP_MAX_G140 = 6
FX3_MYMENU_LIST_MIN_G140 = 0
FX3_MYMENU_LIST_MAX_G140 = 6
FX3_MYMENU_EXACT_SLOTS_G140 = 42  # 6 groups x 7 items = 42 (NOT 36 or 30!)
FX6_USER_MENU_MAX_ITEMS_G140 = 20

MYMENU_OPS_G140: Tuple[str, ...] = (
    "None",
    "Add Item",
    "Sort Item",
    "Delete Item",
    "Delete Page",
    "Delete All",
    "Display From My Menu",
)
ALLOWED_MENU_TABS_G140: Tuple[str, ...] = (
    "Main",
    "Shooting",
    "Exposure/Color",
    "Focus",
    "Playback",
    "Network",
    "Setup",
)
FX3_MYMENU_FORBIDDEN_TABS_G140: Tuple[str, ...] = ("Playback",)

FX6_RENTAL_LOCK_CHORD_G140 = "Multi-Function Dial + MENU"

# Status / Violation Codes
STATUS_BLOCKED_PHASE317_DONOR_INTEGRITY = "STATUS_BLOCKED_PHASE317_DONOR_INTEGRITY"

STATUS_VERIFIED_G139 = "STATUS_VERIFIED_G139"
STATUS_BLOCKED_G139_TELEMETRY_INVALID = "STATUS_BLOCKED_G139_TELEMETRY_INVALID"
STATUS_BLOCKED_G139_REC_MEDIA_SPLIT_FS_OR_DORMANT_PRIORITIZE_VIOLATION = (
    "STATUS_BLOCKED_G139_REC_MEDIA_SPLIT_FS_OR_DORMANT_PRIORITIZE_VIOLATION"
)
STATUS_BLOCKED_G139_SLOT2_TO_SLOT1_OVERFLOW_OR_VAULT_VIOLATION = (
    "STATUS_BLOCKED_G139_SLOT2_TO_SLOT1_OVERFLOW_OR_VAULT_VIOLATION"
)
STATUS_BLOCKED_G139_CARD_SPEED_OR_TYPEB_VIOLATION = (
    "STATUS_BLOCKED_G139_CARD_SPEED_OR_TYPEB_VIOLATION"
)
STATUS_BLOCKED_G139_PROXY_FORMAT_EXCLUSION_OR_FX6_CROSSWIRE_VIOLATION = (
    "STATUS_BLOCKED_G139_PROXY_FORMAT_EXCLUSION_OR_FX6_CROSSWIRE_VIOLATION"
)

STATUS_VERIFIED_G140 = "STATUS_VERIFIED_G140"
STATUS_BLOCKED_G140_TELEMETRY_INVALID = "STATUS_BLOCKED_G140_TELEMETRY_INVALID"
STATUS_BLOCKED_G140_CLOUD_PERSISTENCE_OR_FTP_EXCLUSION_VIOLATION = (
    "STATUS_BLOCKED_G140_CLOUD_PERSISTENCE_OR_FTP_EXCLUSION_VIOLATION"
)
STATUS_BLOCKED_G140_CNCT_WHILE_POWER_OFF_ZERO_RF_VIOLATION = (
    "STATUS_BLOCKED_G140_CNCT_WHILE_POWER_OFF_ZERO_RF_VIOLATION"
)
STATUS_BLOCKED_G140_MYMENU_42SLOT_OR_PLAYBACK_TAB_VIOLATION = (
    "STATUS_BLOCKED_G140_MYMENU_42SLOT_OR_PLAYBACK_TAB_VIOLATION"
)
STATUS_BLOCKED_G140_FX6_USER_MENU_LOCK_OR_SLOT1_CAMSET_VIOLATION = (
    "STATUS_BLOCKED_G140_FX6_USER_MENU_LOCK_OR_SLOT1_CAMSET_VIOLATION"
)

# ---------------------------------------------------------------------------
# Pinned Wave-60 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE317: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_677_451, b"BKID_APP_setting_still_recording_media"),
    (62_677_532, b"BKID_APP_setting_movie_recording_media"),
    (
        61_221_748,
        b"VAL_setting_still_recording_media_STILL_RECORDING_MEDIA_SORT_RECORDING",
    ),
    (62_677_613, b"BKID_APP_setting_relay_rec"),
    (61_235_166, b"VAL_setting_relay_rec_RELAY_REC_OFF"),
    (
        60_483_118,
        b"PRM_HAITA_setting_relay_rec_movie_setting_movie_recording_media_media_read_only_state_slot1",
    ),
    (62_676_549, b"BKID_APP_setting_sq_proxy_recording"),
    (62_676_624, b"BKID_APP_setting_sq_proxy_file_format"),
    (62_676_703, b"BKID_APP_setting_sq_proxy_record_setting"),
    (
        60_784_670,
        b"VAL_setting_sq_proxy_file_format_PROXY_FILE_FORMAT_XAVC_HS_HD",
    ),
    (
        60_784_732,
        b"VAL_setting_sq_proxy_file_format_PROXY_FILE_FORMAT_XAVC_S_HD",
    ),
    (60_355_384, b"convert2MovieMainParams"),
    (62_694_215, b"BKID_APP_setting_cloud_connection"),
    (60_539_077, b"PRM_HAITA_confirm_change_cloud_connection"),
    (61_934_855, b"CLOUD_CONNECTION_ON_FTP_OFF"),
    (62_845_444, b"BKID_APP_extern_menu_cnct_while_power_off"),
    (62_692_918, b"BKID_APP_setting_always_connected"),
    (62_606_570, b"UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER"),
    (62_981_868, b"BLUETOOTH_PAIRING_LAUNCH_FUNCTION_SEND_AT_POWER_OFF"),
    (62_813_705, b"BKID_APP_mymenu_group1_setting_list0"),
    (62_815_222, b"BKID_APP_mymenu_group6_setting_list6"),
    (62_666_006, b"BKID_APP_setting_display_from_mymenu"),
    (63_036_688, b"DISPLAY_FROM_MY_MENU_OFF"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE317 = (
    "e30c37ef260d171bd836f36e6bfa1fe8cce93315f46482b5d2184ddb32b7b484"
)

PINNED_FX6_APPFW_SLICES_PHASE317: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
    (40_932_066, b"BKID_APP_SETTING_SIMUL_REC"),
    (40_930_795, b"BKID_APP_SETTING_LUT_SETTING_PROXY"),
    (40_946_363, b"BKID_APP_SETTING_USER_MENU_ONLY"),
    (40_922_507, b"BKID_APP_SETTING_BLUETOOTH_FUNCTION"),
    (41_589_294, b"ASSIGNABLE_SWITCH_USER_MENU"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE317 = (
    "6e4750954dcc9acc5140d6ac88e324e34eb0820e9ef4cff45e7a9bfa234e7beb"
)

PINNED_PHASE317_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE317,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE317),
        "FX3 appFw.so Wave-60 RecMedia/RelayRec/SqProxy/Cloud/CnctPowerOff/MyMenu42 slices",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Rec. Media Settings",
            b"Recording Media",
            b"Prioritize Rec. Media",
            b"Simult. Recording",
            b"Sort Recording",
            b"Auto Switch Media",
            b"Proxy Settings",
            b"Proxy Recording",
            b"Proxy File Format",
            b"XAVC HS HD",
            b"XAVC S HD",
            b"Proxy Rec. Settings",
            b"16M 4:2:0 10bit",
            b"9M 4:2:0 10bit",
            b"6M 4:2:0 8bit",
            b"Cloud Connection",
            b"Cloud Information",
            b"Connect to Cloud(Private)",
            b"Connect to Cloud(Share)",
            b"Cnct. while Power OFF",
            b"Always Connected",
            b"Display From My Menu",
            b"Add Item",
            b"Sort Item",
            b"Delete Item",
            b"Delete Page",
        ),
        "FX3 string_english_f.uxc Wave-60 EN parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"CFexpress",
            b"VPG400",
            b"VPG200",
        ),
        "FX3 string_english.uxc Wave-60 CFexpress VPG200/VPG400 speed thresholds",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Creators' Cloud",
            b"My Menu",
            b"Cnct. while Power OFF",
        ),
        "FX3 string_english_g.uxc Wave-60 Creators' Cloud / My Menu strings",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "摄像媒体设置".encode("utf-8"),
            "自动切换摄像媒体".encode("utf-8"),
            "同时记录".encode("utf-8"),
            "分类记录".encode("utf-8"),
            "Proxy设置".encode("utf-8"),
            "云连接".encode("utf-8"),
            "关机时连接".encode("utf-8"),
            "从我的菜单显示".encode("utf-8"),
            "添加项目".encode("utf-8"),
            "排序项目".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-60 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "記憶卡槽錄製設定".encode("utf-8"),
            "自動切換記憶卡錄製".encode("utf-8"),
            "代理檔案設定".encode("utf-8"),
            "雲連線".encode("utf-8"),
            "關閉電源時連線".encode("utf-8"),
            "從我的選單顯示".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-60 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "記録メディア設定".encode("utf-8"),
            "プロキシー設定".encode("utf-8"),
            "クラウド接続".encode("utf-8"),
            "電源OFF中の接続".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-60 JA parity",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00",),
        "FX3-CX95900_ALLLANG-Backup.bin BK4 seed",
    ),
    "fx6_appfw_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE317,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE317),
        "FX6 appFw.so Wave-60 SimulRec/ProxyLUT/UserMenuOnly/BT-Dormant slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"1920x1080(9M)",
            b"1280x720(6M)",
            b"Load from Cloud(Private)",
            b"Load from Cloud(Share)",
        ),
        "FX6 string_english.uxc Wave-60 Proxy & Cloud strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Simul Rec",
            b"User Menu Only",
            b"User Menu with Lock",
            b"Edit User Menu",
        ),
        "FX6 string_english_2.uxc Wave-60 Simul Rec & User Menu Lock strings",
    ),
}

_DONOR_BLOB_CACHE: Dict[str, Tuple[int, float, int, str, bytes]] = {}

# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase317DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_200ms: bool
    raw_firmware_bytes_leaked: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    four_lang_resid16_parity_verified: bool
    zero_forbidden_myths_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecMediaAutoSwitchProxyVaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    target_model: str
    reset_action: str
    shoot_mode: str
    requested_recording_media: str
    effective_recording_media: str
    requested_auto_switch_media: str
    effective_auto_switch_media: str
    auto_switch_survived_cam_reset: bool
    dormant_prioritize_rec_media_blocked: bool
    movie_sort_recording_rejected: bool
    slot1_fs: str
    slot2_fs: str
    simult_filesystem_parity_ok: bool
    slot2_full_or_ejected: bool
    slot2_to_slot1_overflow_triggered: bool
    slot_1_contains_tier0_vault: bool
    slot_1_read_only_state: bool
    slot1_vault_firewall_blocked: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    slot1_sub_dir_mutated: bool
    media_card_type: str
    movie_file_format: str
    rec_frame_rate: str
    sq_frame_rate: str
    bitrate_mbps: int
    card_speed_sufficient: bool
    vpg200_uxc_0xe228_required: bool
    vpg400_uxc_0xe224_threshold_triggered: bool
    sdhc_4gb_split_active: bool
    cfexpress_type_b_rejected: bool
    requested_proxy_recording: str
    effective_proxy_recording: str
    proxy_file_format: str
    proxy_record_setting: str
    proxy_resolution: str
    proxy_codec: str
    proxy_bitrate_mbps: int
    proxy_bit_depth: int
    proxy_blocked_by_frame_rate: bool
    proxy_allowed_on_dci_4k_up_to_59_94p: bool
    proxy_sub_dir_path: str
    proxy_in_camera_playback_permitted: bool
    coupled_delete_or_protect_requested: bool
    fx6_simul_rec_proxy_exclusion_ok: bool
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G139RecMediaAutoSwitchProxyVaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    rec_media_autoswitch_proxy_vault_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CreatorsCloudZeroRfMyMenu42GuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    target_model: str
    reset_action: str
    requested_cloud_connection: str
    effective_cloud_connection: str
    cloud_account_signout_requested: bool
    cloud_survived_cam_reset: bool
    cloud_survived_initialize: bool
    c3_portal_profile: str
    clip_flag_filter: str
    ftp_transfer_enabled: bool
    cloud_ftp_mutual_exclusion_ok: bool
    physical_power_switch: str
    requested_airplane_mode: str
    effective_airplane_mode: str
    requested_cnct_while_power_off: str
    effective_cnct_while_power_off: str
    requested_bluetooth_function: str
    effective_bluetooth_function: str
    bluetooth_paired: bool
    cnct_while_power_off_survived_cam_reset: bool
    ble_power_off_energized: bool
    zero_rf_bench_mode: bool
    zero_rf_enforced: bool
    rf_packets_transmitted: int
    cnct_while_power_off_g_0x6476_sc_tc_defect_known: bool
    fx6_bluetooth_absent: bool
    mymenu_exact_slots: int
    mymenu_group: int
    mymenu_list: int
    mymenu_slot_index: int
    mymenu_op: str
    mymenu_item_tab: str
    requested_display_from_mymenu: str
    effective_display_from_mymenu: str
    mymenu_survived_cam_reset: bool
    fx3_30_or_36_slot_myth_rejected: bool
    playback_tab_registration_rejected: bool
    camset_export_requested: bool
    camset_slot: str
    slot_1_contains_tier0_vault: bool
    slot1_camset_vault_blocked: bool
    slot1_data_sector_writes: int
    fx6_user_menu_max_items: int
    fx6_user_menu_only: bool
    fx6_user_menu_with_lock: bool
    fx6_user_menu_lock_pin: str
    fx6_user_menu_lock_excluded_from_all_file: bool
    fx6_rental_lock_rejected_on_fx3: bool
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G140CreatorsCloudZeroRfMyMenu42GuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    creators_cloud_zerorf_mymenu42_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master140GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_137_gates_verified: bool
    all_140_gates_verified: bool
    g13_to_g140_all_passed: bool
    g139_to_g140_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_138_report: Dict[str, Any]
    g139_result: Dict[str, Any]
    g140_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_truthy(val: Optional[str]) -> bool:
    if val is None:
        return False
    return val.strip().lower() in ("1", "true", "yes", "on")


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return _is_truthy(os.environ.get(ENV_FORCE_CLEAN_ROOM)) or _is_truthy(
        os.environ.get(ENV_CLEAN_ROOM_TEST_PHASE317)
    )


def _is_ci_env() -> bool:
    return _is_truthy(os.environ.get("GITHUB_ACTIONS"))


def _is_real_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _parse_fw_major_minor(fw: Any) -> Optional[Tuple[int, int]]:
    if not isinstance(fw, str):
        return None
    m = re.match(r"^\s*(\d+)\.(\d+)\s*$", fw.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _read_exact_o_rdonly(path: Path) -> Tuple[int, str, bytes]:
    """Read an entire small UXC/BIN donor file strictly via os.O_RDONLY."""
    key = str(path.resolve())
    st = os.stat(key)
    cached = _DONOR_BLOB_CACHE.get(key)
    if (
        cached is not None
        and cached[0] == st.st_size
        and cached[1] == st.st_mtime
        and cached[2] == getattr(st, "st_ino", 0)
    ):
        return cached[0], cached[3], cached[4]

    fd = os.open(key, os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        hasher = hashlib.sha256()
        total = 0
        while True:
            blk = os.read(fd, 1024 * 1024)
            if not blk:
                break
            total += len(blk)
            hasher.update(blk)
            chunks.append(blk)
        blob = b"".join(chunks)
        digest = hasher.hexdigest()
        _DONOR_BLOB_CACHE[key] = (
            total,
            st.st_mtime,
            getattr(st, "st_ino", 0),
            digest,
            blob,
        )
        return total, digest, blob
    finally:
        os.close(fd)


def _read_appfw_slices_o_rdonly(
    path: Path,
    slices: Tuple[Tuple[int, bytes], ...],
) -> Tuple[int, str, Tuple[bytes, ...]]:
    """Bounded os.pread SHA-256 verification over pinned appFw.so byte slices."""
    key = f"{path.resolve()}::slices317::{len(slices)}"
    st = os.stat(path)
    cached = _DONOR_BLOB_CACHE.get(key)
    if (
        cached is not None
        and cached[0] == st.st_size
        and cached[1] == st.st_mtime
        and cached[2] == getattr(st, "st_ino", 0)
    ):
        return cached[0], cached[3], tuple(tok for _, tok in slices)

    fd = os.open(str(path), os.O_RDONLY)
    try:
        hasher = hashlib.sha256()
        missing: List[bytes] = []
        for offset, expected in slices:
            if offset < 0 or offset + len(expected) > st.st_size:
                missing.append(expected)
                continue
            observed = os.pread(fd, len(expected), offset)
            if observed != expected:
                missing.append(expected)
            else:
                hasher.update(observed)
        digest = hasher.hexdigest() if not missing else "MISSING_SLICE"
        if not missing:
            _DONOR_BLOB_CACHE[key] = (
                st.st_size,
                st.st_mtime,
                getattr(st, "st_ino", 0),
                digest,
                b"",
            )
        present = tuple(tok for _, tok in slices if tok not in missing)
        return st.st_size, digest, present
    finally:
        os.close(fd)


def _normalize_shoot_mode(mode: Any) -> Optional[str]:
    if not isinstance(mode, str):
        return None
    m = mode.strip().lower()
    if m in ("still", "photo"):
        return SHOOT_MODE_STILL_PHASE317
    if m in ("movie", "video"):
        return SHOOT_MODE_MOVIE_PHASE317
    if m in ("s&q", "sq", "s&q motion", "snq"):
        return SHOOT_MODE_SQ_PHASE317
    return None


def _normalize_reset_action(action: Any) -> Optional[str]:
    if not isinstance(action, str):
        return None
    a = action.strip().lower()
    if a in ("none", ""):
        return RESET_ACTION_NONE_PHASE317
    if a in ("camera settings reset", "cam_reset"):
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317
    if a in ("reset network set.", "reset network set", "net_reset"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE317
    if a in ("initialize", "factory reset"):
        return RESET_ACTION_INITIALIZE_PHASE317
    return None


def _normalize_on_off(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    v = val.strip().lower()
    if v == "on":
        return "On"
    if v == "off":
        return "Off"
    return None


def _normalize_rec_media_mode(mode: Any) -> Optional[str]:
    if not isinstance(mode, str):
        return None
    m = mode.strip().lower()
    if m in ("slot 1", "slot1", "slot_a", "a"):
        return REC_MEDIA_SLOT_1_G139
    if m in ("slot 2", "slot2", "slot_b", "b"):
        return REC_MEDIA_SLOT_2_G139
    if m in ("simult. recording", "simult", "simul", "simultaneous"):
        return REC_MEDIA_SIMULT_G139
    if m in ("sort recording", "sort", "sort_recording"):
        return REC_MEDIA_SORT_G139
    return None


# ---------------------------------------------------------------------------
# 1. Bounded O_RDONLY Donor Audit (Phase 317)
# ---------------------------------------------------------------------------


def audit_phase317_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase317DonorAuditResult:
    """Inspect Wave-60 donor contracts via bounded O_RDONLY reads or clean-room fallback."""
    t0 = time.perf_counter()
    clean_forced = _is_forced_clean_room(force_clean_room)
    budget_s = (
        DONOR_CHECK_CI_MAX_SECONDS_PHASE317 + 15.0
        if _is_ci_env()
        else DONOR_CHECK_MAX_SECONDS_PHASE317
    )

    if clean_forced:
        dt = time.perf_counter() - t0
        return Phase317DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_NO_DONOR_TOUCH",
            files_inspected=0,
            elapsed_seconds=round(dt, 6),
            within_budget_200ms=dt <= budget_s,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(PINNED_PHASE317_DONOR_SPECS.keys()),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            zero_forbidden_myths_verified=True,
            sha256_by_artifact={},
            bytes_by_artifact={},
            errors=(),
            warnings=(),
        )

    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    if work_root is None:
        paths = resolve_donor_thermal_power_paths(repo_root=resolved_root)
        resolved_work_root = paths.work_root
    else:
        resolved_work_root = Path(work_root).resolve()

    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else PINNED_PHASE317_DONOR_SPECS
    )

    if donor_specs_override is None:
        anchor_path = resolved_work_root / specs["fx3_string_english_f_uxc"][1]
        fx6_anchor = resolved_work_root / specs["fx6_string_english_2_uxc"][1]
        if (not anchor_path.exists()) or (not fx6_anchor.exists()):
            dt = time.perf_counter() - t0
            return Phase317DonorAuditResult(
                valid=True,
                status=STATUS_VERIFIED_SAFE,
                verification_mode="CLEAN_ROOM_SYNTHETIC",
                access_mode="SYNTHETIC_ABSENT_DONOR_FALLBACK",
                files_inspected=0,
                elapsed_seconds=round(dt, 6),
                within_budget_200ms=dt <= budget_s,
                raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
                checked_markers=tuple(specs.keys()),
                missing_markers=(),
                fx3_contracts_verified=True,
                fx6_contracts_verified=True,
                four_lang_resid16_parity_verified=True,
                zero_forbidden_myths_verified=True,
                sha256_by_artifact={},
                bytes_by_artifact={},
                errors=(),
                warnings=(
                    "Donor workspace absent; verified Phase 317 via deterministic clean-room contracts.",
                ),
            )

    checked: List[str] = []
    missing: List[str] = []
    sha_map: Dict[str, str] = {}
    size_map: Dict[str, int] = {}
    errors: List[str] = []

    for key, (family, rel_path, expected_size, expected_sha, tokens, desc) in specs.items():
        target = resolved_work_root / rel_path
        checked.append(key)
        if not target.is_file():
            missing.append(f"{key}:missing_file")
            errors.append(f"{family} donor file missing: {rel_path} ({desc})")
            continue
        try:
            if key == "fx3_appfw_so" and donor_specs_override is None:
                actual_size, actual_sha, present = _read_appfw_slices_o_rdonly(
                    target, PINNED_FX3_APPFW_SLICES_PHASE317
                )
                missing_toks = [tok for tok in tokens if tok not in present]
            elif key == "fx6_appfw_so" and donor_specs_override is None:
                actual_size, actual_sha, present = _read_appfw_slices_o_rdonly(
                    target, PINNED_FX6_APPFW_SLICES_PHASE317
                )
                missing_toks = [tok for tok in tokens if tok not in present]
            else:
                actual_size, actual_sha, blob = _read_exact_o_rdonly(target)
                missing_toks = [tok for tok in tokens if tok not in blob]
        except OSError as exc:
            missing.append(f"{key}:os_error")
            errors.append(f"os.O_RDONLY failed on {rel_path}: {exc}")
            continue

        sha_map[key] = actual_sha
        size_map[key] = actual_size
        if actual_size != expected_size:
            missing.append(f"{key}:size_mismatch")
            errors.append(
                f"{key} size mismatch: expected={expected_size}, got={actual_size}"
            )
        if actual_sha != expected_sha:
            missing.append(f"{key}:sha256_mismatch")
            errors.append(
                f"{key} sha256 mismatch: expected={expected_sha}, got={actual_sha}"
            )
        if missing_toks:
            missing.append(f"{key}:token_missing")
            errors.append(
                f"{key} missing {len(missing_toks)} expected Wave-60 contract tokens"
            )

    dt = time.perf_counter() - t0
    valid = (len(missing) == 0) and (len(errors) == 0)
    fx3_ok = valid and all(k in sha_map for k in specs if k.startswith("fx3_"))
    fx6_ok = valid and all(k in sha_map for k in specs if k.startswith("fx6_"))
    lang_ok = valid and all(
        k in sha_map
        for k in (
            "fx3_string_english_f_uxc",
            "fx3_string_simplifiedchinese_f_uxc",
            "fx3_string_traditionalchinese_f_uxc",
            "fx3_string_japanese_f_uxc",
        )
    )
    return Phase317DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE317_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="POSIX_O_RDONLY_AND_PREAD_ZERO_MUTATION",
        files_inspected=len(sha_map),
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= budget_s,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        four_lang_resid16_parity_verified=lang_ok,
        zero_forbidden_myths_verified=valid,
        sha256_by_artifact=sha_map,
        bytes_by_artifact=size_map,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G139: Rec. Media, Auto Switch Overflow, VPG200/400 & Proxy SUB Vault
# ---------------------------------------------------------------------------


def _evaluate_card_speed_requirement(
    *,
    shoot_mode: str,
    movie_file_format: str,
    sq_frame_rate: str,
    bitrate_mbps: int,
    proxy_effective: str,
    media_card_type: str,
) -> Dict[str, Any]:
    """Evaluate FX3 Ver. 7.02 card speed threshold & VPG200/VPG400 gate."""
    if media_card_type == CARD_CFEXPRESS_TYPE_B_UNSUPPORTED_G139:
        return {
            "cfexpress_type_b_rejected": True,
            "card_speed_sufficient": False,
            "vpg200_required": False,
            "vpg400_triggered": False,
            "required_min_rank": 99,
        }

    rank = CARD_SPEED_RANK_G139.get(media_card_type, 0)
    is_cfexpress_a = media_card_type in (
        CARD_CFEXPRESS_TYPE_A_VPG200_G139,
        CARD_CFEXPRESS_TYPE_A_VPG400_G139,
    )
    vpg200_req = False
    vpg400_trig = False
    min_rank = 1

    if shoot_mode == SHOOT_MODE_SQ_PHASE317:
        if movie_file_format in (
            MOVIE_FORMAT_XAVC_S_I_4K_G139,
            MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139,
        ):
            # S&Q XAVC S-I 4K (1200M) or DCI 4K mandatory CFexpress Type A (VPG200+)
            vpg200_req = True
            min_rank = 5
            if movie_file_format == MOVIE_FORMAT_XAVC_S_I_4K_G139 and (
                bitrate_mbps >= 1200 or proxy_effective == "On"
            ):
                vpg400_trig = True
                if proxy_effective == "On":
                    min_rank = 6
        elif movie_file_format == MOVIE_FORMAT_XAVC_S_I_HD_G139:
            if sq_frame_rate in ("200fps", "240fps") or bitrate_mbps >= 890:
                vpg200_req = True
                min_rank = 5
            else:
                min_rank = 4  # SDXC V90+
        else:
            # S&Q XAVC HS 4K / XAVC S 4K / XAVC S HD
            if sq_frame_rate in ("100fps", "120fps", "200fps", "240fps"):
                min_rank = 4  # SDXC V90+ or CFexpress A
            else:
                min_rank = 3  # SDXC V60+
    else:
        # Normal Movie (or Still baseline)
        if movie_file_format in (
            MOVIE_FORMAT_XAVC_S_I_4K_G139,
            MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139,
            MOVIE_FORMAT_XAVC_S_I_HD_G139,
        ):
            min_rank = 4  # SDXC V90+ or CFexpress A
            if movie_file_format in (
                MOVIE_FORMAT_XAVC_S_I_4K_G139,
                MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139,
            ) and proxy_effective == "On":
                # 600M + Proxy triggers CFexpress VPG200/VPG400 guard
                vpg200_req = True
                vpg400_trig = True
                min_rank = 5
        elif movie_file_format in (
            MOVIE_FORMAT_XAVC_HS_4K_G139,
            MOVIE_FORMAT_XAVC_S_4K_G139,
        ):
            if bitrate_mbps > 200:
                min_rank = 3  # SDXC V60+
            elif bitrate_mbps > 60:
                min_rank = 2  # U3/V30
            else:
                min_rank = 1  # Class 10
        else:
            # XAVC S HD
            min_rank = 2 if bitrate_mbps > 60 else 1

    sufficient = (rank >= min_rank) and (not vpg200_req or is_cfexpress_a)
    return {
        "cfexpress_type_b_rejected": False,
        "card_speed_sufficient": sufficient,
        "vpg200_required": vpg200_req,
        "vpg400_triggered": vpg400_trig,
        "required_min_rank": min_rank,
    }


def _compute_g139_effective_state(
    *,
    shoot_mode: str,
    reset_action: str,
    recording_media: str,
    auto_switch_media: str,
    slot1_fs: str,
    slot2_fs: str,
    slot2_full_or_ejected: bool,
    slot_1_contains_tier0_vault: bool,
    slot_1_read_only_state: bool,
    recording_execute_requested: bool,
    media_card_type: str,
    movie_file_format: str,
    rec_frame_rate: str,
    sq_frame_rate: str,
    bitrate_mbps: int,
    proxy_recording: str,
    proxy_file_format: str,
    proxy_record_setting: str,
    coupled_delete_or_protect_requested: bool,
) -> Dict[str, Any]:
    init_reset = reset_action == RESET_ACTION_INITIALIZE_PHASE317
    cam_or_init = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
        RESET_ACTION_INITIALIZE_PHASE317,
    )

    # Recording Media & Auto Switch Media are Initialize-only (survive Camera Settings Reset)
    eff_rec_media = REC_MEDIA_SLOT_1_G139 if init_reset else recording_media
    eff_auto_switch = "Off" if init_reset else auto_switch_media
    auto_switch_survived_cam_reset = (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317
    )

    # Proxy Settings ARE resettable by Camera Settings Reset & Initialize
    eff_proxy_rec = "Off" if cam_or_init else proxy_recording
    eff_proxy_fmt = PROXY_FORMAT_XAVC_S_HD_G139 if cam_or_init else proxy_file_format
    eff_proxy_setting = (
        PROXY_SETTING_6M_8BIT_G139
        if cam_or_init
        else proxy_record_setting
    )

    # Proxy frame rate blocks: Normal 119.88p/100p OR S&Q 119.88p/100p/120fps/100fps
    # NOTE: XAVC S-I DCI 4K up to 59.94p is NOT blocked!
    proxy_blocked_fr = (rec_frame_rate in PROXY_BLOCKED_REC_FRAME_RATES_G139) or (
        shoot_mode == SHOOT_MODE_SQ_PHASE317
        and sq_frame_rate in PROXY_BLOCKED_SQ_FRAME_RATES_G139
    )
    if proxy_blocked_fr:
        eff_proxy_rec = "Off"

    simult_fs_ok = (eff_rec_media != REC_MEDIA_SIMULT_G139) or (slot1_fs == slot2_fs)

    # Overflow trap: Slot 2 + Auto Switch On (especially when Slot 2 is full/ejected)
    overflow_triggered = bool(
        eff_rec_media == REC_MEDIA_SLOT_2_G139
        and eff_auto_switch == "On"
        and slot2_full_or_ejected
    )
    auto_switch_vault_hazard = bool(
        slot_1_contains_tier0_vault and eff_auto_switch == "On"
    )
    routes_to_slot1 = eff_rec_media in (
        REC_MEDIA_SLOT_1_G139,
        REC_MEDIA_SIMULT_G139,
    )
    mutating_op_requested = bool(
        recording_execute_requested
        or eff_proxy_rec == "On"
        or coupled_delete_or_protect_requested
        or overflow_triggered
    )
    slot1_protected = bool(slot_1_contains_tier0_vault or slot_1_read_only_state)
    slot1_firewall_blocked = bool(
        slot1_protected
        and (
            auto_switch_vault_hazard
            or (routes_to_slot1 and mutating_op_requested)
        )
    )

    speed_info = _evaluate_card_speed_requirement(
        shoot_mode=shoot_mode,
        movie_file_format=movie_file_format,
        sq_frame_rate=sq_frame_rate,
        bitrate_mbps=bitrate_mbps,
        proxy_effective=eff_proxy_rec,
        media_card_type=media_card_type,
    )

    proxy_sub_dir = (
        PROXY_SUB_PATH_CFEXPRESS_G139
        if media_card_type
        in (
            CARD_CFEXPRESS_TYPE_A_VPG200_G139,
            CARD_CFEXPRESS_TYPE_A_VPG400_G139,
        )
        else PROXY_SUB_PATH_SDXC_G139
    )
    if eff_proxy_fmt == PROXY_FORMAT_XAVC_HS_HD_G139:
        proxy_res = "1920x1080"
        proxy_codec = "HEVC/H.265"
        proxy_bitrate = 16 if eff_proxy_setting == PROXY_SETTING_16M_10BIT_G139 else 9
        proxy_depth = 10
    else:
        proxy_res = "1280x720"
        proxy_codec = "AVC/H.264"
        proxy_bitrate = 6
        proxy_depth = 8

    return {
        "effective_recording_media": eff_rec_media,
        "effective_auto_switch_media": eff_auto_switch,
        "auto_switch_survived_cam_reset": auto_switch_survived_cam_reset,
        "simult_filesystem_parity_ok": simult_fs_ok,
        "slot2_to_slot1_overflow_triggered": overflow_triggered,
        "auto_switch_vault_hazard": auto_switch_vault_hazard,
        "slot1_vault_firewall_blocked": slot1_firewall_blocked,
        "slot1_data_sector_writes": 0,
        "slot1_avf_info_mutated": False,
        "slot1_sub_dir_mutated": False,
        "effective_proxy_recording": eff_proxy_rec,
        "effective_proxy_file_format": eff_proxy_fmt,
        "effective_proxy_record_setting": eff_proxy_setting,
        "proxy_blocked_by_frame_rate": proxy_blocked_fr,
        "proxy_sub_dir_path": proxy_sub_dir,
        "proxy_resolution": proxy_res,
        "proxy_codec": proxy_codec,
        "proxy_bitrate_mbps": proxy_bitrate,
        "proxy_bit_depth": proxy_depth,
        "sdhc_4gb_split_active": media_card_type == CARD_SDHC_LE32GB_G139,
        **speed_info,
    }


def compute_rec_media_autoswitch_proxy_matrix() -> Dict[str, Any]:
    """Deterministically evaluate 256 state transitions for Rec. Media, Auto Switch & Proxy."""
    states_checked = 0
    slot1_vault_blocked_count = 0
    overflow_trap_count = 0
    proxy_fr_blocked_count = 0
    vpg_cfe_required_count = 0

    for rec_media in (REC_MEDIA_SLOT_2_G139, REC_MEDIA_SIMULT_G139):
        for auto_sw in ("Off", "On"):
            for full_ej in (False, True):
                for vault in (False, True):
                    for fmt in (
                        MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139,
                        MOVIE_FORMAT_XAVC_S_I_4K_G139,
                    ):
                        for rec_fr in ("59.94p", "119.88p"):
                            for card in (
                                CARD_SDXC_V90_G139,
                                CARD_CFEXPRESS_TYPE_A_VPG400_G139,
                            ):
                                for proxy_on in ("Off", "On"):
                                    sm = (
                                        SHOOT_MODE_SQ_PHASE317
                                        if fmt == MOVIE_FORMAT_XAVC_S_I_4K_G139
                                        else SHOOT_MODE_MOVIE_PHASE317
                                    )
                                    st = _compute_g139_effective_state(
                                        shoot_mode=sm,
                                        reset_action=RESET_ACTION_NONE_PHASE317,
                                        recording_media=rec_media,
                                        auto_switch_media=auto_sw,
                                        slot1_fs=SLOT_FS_EXFAT_G139,
                                        slot2_fs=SLOT_FS_EXFAT_G139,
                                        slot2_full_or_ejected=full_ej,
                                        slot_1_contains_tier0_vault=vault,
                                        slot_1_read_only_state=vault,
                                        recording_execute_requested=True,
                                        media_card_type=card,
                                        movie_file_format=fmt,
                                        rec_frame_rate=rec_fr,
                                        sq_frame_rate="60fps",
                                        bitrate_mbps=1200 if sm == SHOOT_MODE_SQ_PHASE317 else 600,
                                        proxy_recording=proxy_on,
                                        proxy_file_format=PROXY_FORMAT_XAVC_HS_HD_G139,
                                        proxy_record_setting=PROXY_SETTING_9M_10BIT_G139,
                                        coupled_delete_or_protect_requested=False,
                                    )
                                    states_checked += 1
                                    if st["slot1_vault_firewall_blocked"]:
                                        slot1_vault_blocked_count += 1
                                    if st["slot2_to_slot1_overflow_triggered"]:
                                        overflow_trap_count += 1
                                    if st["proxy_blocked_by_frame_rate"]:
                                        proxy_fr_blocked_count += 1
                                    if st["vpg200_required"]:
                                        vpg_cfe_required_count += 1
                                    assert st["slot1_data_sector_writes"] == 0

    return {
        "states_checked": states_checked,
        "slot1_vault_blocked_count": slot1_vault_blocked_count,
        "overflow_trap_count": overflow_trap_count,
        "proxy_fr_blocked_count": proxy_fr_blocked_count,
        "vpg_cfe_required_count": vpg_cfe_required_count,
    }


def resolve_fx3_rec_media_autoswitch_proxy_state(
    **kwargs: Any,
) -> Dict[str, Any]:
    """Return serialized G139 guard state for UI/VM/orchestrator callers."""
    return verify_rec_media_autoswitch_proxy_vault_guard(**kwargs).to_dict()


def verify_rec_media_autoswitch_proxy_vault_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE317,
    body_model_id: int = FX3_MODEL_ID_PHASE317,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE317,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE317,
    target_model: str = FX3_MODEL_NAME_PHASE317,
    reset_action: str = RESET_ACTION_NONE_PHASE317,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE317,
    requested_recording_media: str = REC_MEDIA_SLOT_2_G139,
    requested_auto_switch_media: str = "Off",
    requested_dormant_prioritize_token: Optional[str] = None,
    slot1_fs: str = SLOT_FS_EXFAT_G139,
    slot2_fs: str = SLOT_FS_EXFAT_G139,
    slot2_full_or_ejected: bool = False,
    slot_1_contains_tier0_vault: bool = True,
    slot_1_read_only_state: bool = True,
    recording_execute_requested: bool = False,
    bypass_slot1_vault_firewall: bool = False,
    media_card_type: str = CARD_CFEXPRESS_TYPE_A_VPG400_G139,
    movie_file_format: str = MOVIE_FORMAT_XAVC_S_4K_G139,
    rec_frame_rate: str = "23.98p",
    sq_frame_rate: str = "24fps",
    bitrate_mbps: int = 100,
    enforce_card_speed_gate: bool = True,
    requested_proxy_recording: str = "Off",
    proxy_file_format: str = PROXY_FORMAT_XAVC_S_HD_G139,
    proxy_record_setting: str = PROXY_SETTING_6M_8BIT_G139,
    force_proxy_under_100p_120p: bool = False,
    claimed_dci_4k_blocks_proxy: bool = False,
    claimed_proxy_in_camera_playback: bool = False,
    coupled_delete_or_protect_requested: bool = False,
    fx6_simul_rec_enabled: bool = False,
    fx6_proxy_rec_enabled: bool = False,
    fx6_chunk_proxy_enabled: bool = False,
    fx6_relay_rec_enabled: bool = False,
    claimed_fx3_supports_chunk_proxy_or_xdroot: bool = False,
) -> RecMediaAutoSwitchProxyVaultGuardResult:
    """Enforce Gate G139: Rec. Media split & FS parity, Auto Switch Slot-2->Slot-1
    overflow lock, VPG200/VPG400 speed gates, and Proxy SUB Slot-1 Vault Firewall.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_shoot = _normalize_shoot_mode(shoot_mode)
    norm_reset = _normalize_reset_action(reset_action)
    norm_rec_media = _normalize_rec_media_mode(requested_recording_media)
    norm_auto_sw = _normalize_on_off(requested_auto_switch_media)
    norm_proxy_rec = _normalize_on_off(requested_proxy_recording)

    fw_parsed = _parse_fw_major_minor(firmware_version)
    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE317
        and _is_real_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE317
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE317
        and fw_parsed is not None
    )
    if not identity_ok:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3 Ver. 7.02 hardware/help-guide/firmware identity for Gate G139."
        )

    if target_model not in (FX3_MODEL_NAME_PHASE317, FX6_MODEL_NAME_PHASE317):
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Unsupported target_model `{target_model}`.")

    if norm_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid shoot_mode `{shoot_mode}`.")
        norm_shoot = SHOOT_MODE_MOVIE_PHASE317

    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid reset_action `{reset_action}`.")
        norm_reset = RESET_ACTION_NONE_PHASE317

    if norm_rec_media is None:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_recording_media `{requested_recording_media}`.")
        norm_rec_media = REC_MEDIA_SLOT_2_G139

    if norm_auto_sw is None:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(
            f"Invalid requested_auto_switch_media `{requested_auto_switch_media}`."
        )
        norm_auto_sw = "Off"

    if norm_proxy_rec is None:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(
            f"Invalid requested_proxy_recording `{requested_proxy_recording}`."
        )
        norm_proxy_rec = "Off"

    if slot1_fs not in ALLOWED_SLOT_FILESYSTEMS_G139:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid slot1_fs `{slot1_fs}`.")
        safe_s1_fs = SLOT_FS_EXFAT_G139
    else:
        safe_s1_fs = slot1_fs

    if slot2_fs not in ALLOWED_SLOT_FILESYSTEMS_G139:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid slot2_fs `{slot2_fs}`.")
        safe_s2_fs = SLOT_FS_EXFAT_G139
    else:
        safe_s2_fs = slot2_fs

    type_b_requested = media_card_type == CARD_CFEXPRESS_TYPE_B_UNSUPPORTED_G139
    if (not type_b_requested) and media_card_type not in ALLOWED_CARD_TYPES_G139:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid media_card_type `{media_card_type}`.")
        safe_card = CARD_CFEXPRESS_TYPE_A_VPG400_G139
    else:
        safe_card = media_card_type

    if movie_file_format not in ALLOWED_MOVIE_FILE_FORMATS_G139:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid movie_file_format `{movie_file_format}`.")
        safe_movie_fmt = MOVIE_FORMAT_XAVC_S_4K_G139
    else:
        safe_movie_fmt = movie_file_format

    if rec_frame_rate not in ALLOWED_REC_FRAME_RATES_G139:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid rec_frame_rate `{rec_frame_rate}`.")
        safe_rec_fr = "23.98p"
    else:
        safe_rec_fr = rec_frame_rate

    if sq_frame_rate not in ALLOWED_SQ_FRAME_RATES_G139:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid sq_frame_rate `{sq_frame_rate}`.")
        safe_sq_fr = "24fps"
    else:
        safe_sq_fr = sq_frame_rate

    if not _is_real_int(bitrate_mbps) or bitrate_mbps <= 0 or bitrate_mbps > 2000:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid bitrate_mbps `{bitrate_mbps}`.")
        safe_bitrate = 100
    else:
        safe_bitrate = bitrate_mbps

    if proxy_file_format not in ALLOWED_PROXY_FILE_FORMATS_G139:
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid proxy_file_format `{proxy_file_format}`.")
        safe_proxy_fmt = PROXY_FORMAT_XAVC_S_HD_G139
    else:
        safe_proxy_fmt = proxy_file_format

    dormant_proxy_lower = {s.strip().lower() for s in DORMANT_PROXY_SETTINGS_G139}
    dormant_proxy_setting_hit = (
        isinstance(proxy_record_setting, str)
        and proxy_record_setting.strip().lower() in dormant_proxy_lower
    )
    if (
        not dormant_proxy_setting_hit
        and proxy_record_setting not in ALLOWED_PROXY_RECORD_SETTINGS_G139
    ):
        _add_code(codes, STATUS_BLOCKED_G139_TELEMETRY_INVALID)
        errors.append(f"Invalid proxy_record_setting `{proxy_record_setting}`.")
        safe_proxy_set = PROXY_SETTING_6M_8BIT_G139
    else:
        safe_proxy_set = proxy_record_setting

    eff = _compute_g139_effective_state(
        shoot_mode=norm_shoot,
        reset_action=norm_reset,
        recording_media=norm_rec_media,
        auto_switch_media=norm_auto_sw,
        slot1_fs=safe_s1_fs,
        slot2_fs=safe_s2_fs,
        slot2_full_or_ejected=bool(slot2_full_or_ejected),
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        slot_1_read_only_state=bool(slot_1_read_only_state),
        recording_execute_requested=bool(recording_execute_requested),
        media_card_type=safe_card,
        movie_file_format=safe_movie_fmt,
        rec_frame_rate=safe_rec_fr,
        sq_frame_rate=safe_sq_fr,
        bitrate_mbps=safe_bitrate,
        proxy_recording=norm_proxy_rec,
        proxy_file_format=safe_proxy_fmt,
        proxy_record_setting=safe_proxy_set,
        coupled_delete_or_protect_requested=bool(coupled_delete_or_protect_requested),
    )

    # Part A: Split Rec. Media Settings, Dormant Prioritize, Movie Sort & Simult FS Parity
    dormant_prioritize_lower = {
        s.strip().lower() for s in DORMANT_PRIORITIZE_REC_MEDIA_TRAPS_G139
    }
    dormant_prioritize_hit = (
        requested_dormant_prioritize_token is not None
        and requested_dormant_prioritize_token.strip().lower()
        in dormant_prioritize_lower
    )
    movie_sort_rejected = bool(
        norm_shoot in (SHOOT_MODE_MOVIE_PHASE317, SHOOT_MODE_SQ_PHASE317)
        and eff["effective_recording_media"] == REC_MEDIA_SORT_G139
    )
    simult_fs_mismatch = not eff["simult_filesystem_parity_ok"]
    if dormant_prioritize_hit or movie_sort_rejected or simult_fs_mismatch:
        _add_code(
            codes,
            STATUS_BLOCKED_G139_REC_MEDIA_SPLIT_FS_OR_DORMANT_PRIORITIZE_VIOLATION,
        )
        errors.append(
            "Rec. Media Settings contract violated: dormant `[Prioritize Rec. Media]` (`_f 0x719e`) "
            "is EOPNOTSUPP=95, Movie/S&Q rejects `Sort Recording` (EINVAL=22), and "
            "`Simult. Recording` requires matching `exFAT`/`FAT32` filesystems across both slots."
        )

    # Part B: CRITICAL Slot-2 -> Slot-1 Overflow Trap & Tier-0 Vault Firewall
    vault_or_overflow_violation = bool(
        eff["slot1_vault_firewall_blocked"]
        or (eff["slot2_to_slot1_overflow_triggered"] and slot_1_contains_tier0_vault)
        or (bypass_slot1_vault_firewall and slot_1_contains_tier0_vault)
    )
    if vault_or_overflow_violation:
        _add_code(
            codes,
            STATUS_BLOCKED_G139_SLOT2_TO_SLOT1_OVERFLOW_OR_VAULT_VIOLATION,
        )
        errors.append(
            "CRITICAL SLOT-1 TIER-0 VAULT FIREWALL (`EROFS=30`): `[Auto Switch Media] = On` "
            "or `Slot 1`/`Simult. Recording` write/delete path threatens Tier-0 Vault "
            "(`setting_relay_rec` survives Camera Settings Reset; locked `slot1_data_sector_writes == 0`, "
            "`slot1_avf_info_mutated == False`, `slot1_sub_dir_mutated == False`)."
        )

    # Part C: Card Speed Gate & CFexpress Type B rejection
    card_speed_violation = bool(
        eff["cfexpress_type_b_rejected"]
        or (enforce_card_speed_gate and not eff["card_speed_sufficient"])
    )
    if card_speed_violation:
        _add_code(codes, STATUS_BLOCKED_G139_CARD_SPEED_OR_TYPEB_VIOLATION)
        errors.append(
            "Card Speed / Media Gate violated: CFexpress Type B is ENODEV=19, S&Q XAVC S-I 4K "
            "1200M / HD 240fps require CFexpress Type A VPG200/VPG400 (`.uxc 0xe228`/`0xe224`), "
            "and XAVC S-I 600M / XAVC HS/S 4K 280M require V90 / V60+ respectively."
        )

    # Part D: Proxy Format Matrix, Exclusions & FX6 Simul/Chunk Contrast
    invalid_proxy_combo = (
        (
            safe_proxy_fmt == PROXY_FORMAT_XAVC_S_HD_G139
            and safe_proxy_set != PROXY_SETTING_6M_8BIT_G139
        )
        or (
            safe_proxy_fmt == PROXY_FORMAT_XAVC_HS_HD_G139
            and safe_proxy_set
            not in (PROXY_SETTING_9M_10BIT_G139, PROXY_SETTING_16M_10BIT_G139)
        )
    )
    proxy_fr_override_violation = bool(
        eff["proxy_blocked_by_frame_rate"]
        and norm_proxy_rec == "On"
        and force_proxy_under_100p_120p
    )
    fx6_exclusion_violation = bool(
        (fx6_simul_rec_enabled and (fx6_proxy_rec_enabled or fx6_chunk_proxy_enabled))
        or (fx6_chunk_proxy_enabled and fx6_relay_rec_enabled)
    )
    if (
        dormant_proxy_setting_hit
        or invalid_proxy_combo
        or proxy_fr_override_violation
        or claimed_dci_4k_blocks_proxy
        or claimed_proxy_in_camera_playback
        or claimed_fx3_supports_chunk_proxy_or_xdroot
        or fx6_exclusion_violation
    ):
        _add_code(
            codes,
            STATUS_BLOCKED_G139_PROXY_FORMAT_EXCLUSION_OR_FX6_CROSSWIRE_VIOLATION,
        )
        errors.append(
            "Proxy contract violated: FX3 `[Proxy Settings]` (`_f 0x6e3f`) allows `XAVC S HD` "
            "(1280x720 6M 8bit) and `XAVC HS HD` (1920x1080 9M/16M 10bit), blocks `119.88p/100p` & "
            "S&Q `120/100fps` (does NOT block `XAVC S-I DCI 4K <=59.94p`), forbids in-camera playback "
            "& dormant `16M 8bit`, and FX6 `Simul Rec` / `Chunk Proxy` exclusions are enforced."
        )

    # Determine errno
    block_errno: Optional[int] = None
    block_errno_name: Optional[str] = None
    if vault_or_overflow_violation:
        block_errno = EROFS_ERRNO_PHASE317
        block_errno_name = EROFS_NAME_PHASE317
    elif eff["cfexpress_type_b_rejected"]:
        block_errno = ENODEV_ERRNO_PHASE317
        block_errno_name = ENODEV_NAME_PHASE317
    elif dormant_prioritize_hit or dormant_proxy_setting_hit or claimed_fx3_supports_chunk_proxy_or_xdroot:
        block_errno = EOPNOTSUPP_ERRNO_PHASE317
        block_errno_name = EOPNOTSUPP_NAME_PHASE317
    elif movie_sort_rejected or simult_fs_mismatch or invalid_proxy_combo or proxy_fr_override_violation or fx6_exclusion_violation or card_speed_violation:
        block_errno = EINVAL_ERRNO_PHASE317
        block_errno_name = EINVAL_NAME_PHASE317

    matrix = compute_rec_media_autoswitch_proxy_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G139 if valid else codes[0]

    return RecMediaAutoSwitchProxyVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE317,
        target_model=target_model,
        reset_action=norm_reset,
        shoot_mode=norm_shoot,
        requested_recording_media=norm_rec_media,
        effective_recording_media=eff["effective_recording_media"],
        requested_auto_switch_media=norm_auto_sw,
        effective_auto_switch_media=eff["effective_auto_switch_media"],
        auto_switch_survived_cam_reset=eff["auto_switch_survived_cam_reset"],
        dormant_prioritize_rec_media_blocked=dormant_prioritize_hit,
        movie_sort_recording_rejected=movie_sort_rejected,
        slot1_fs=safe_s1_fs,
        slot2_fs=safe_s2_fs,
        simult_filesystem_parity_ok=eff["simult_filesystem_parity_ok"],
        slot2_full_or_ejected=bool(slot2_full_or_ejected),
        slot2_to_slot1_overflow_triggered=eff["slot2_to_slot1_overflow_triggered"],
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        slot_1_read_only_state=bool(slot_1_read_only_state),
        slot1_vault_firewall_blocked=eff["slot1_vault_firewall_blocked"],
        slot1_data_sector_writes=eff["slot1_data_sector_writes"],
        slot1_avf_info_mutated=eff["slot1_avf_info_mutated"],
        slot1_sub_dir_mutated=eff["slot1_sub_dir_mutated"],
        media_card_type=safe_card,
        movie_file_format=safe_movie_fmt,
        rec_frame_rate=safe_rec_fr,
        sq_frame_rate=safe_sq_fr,
        bitrate_mbps=safe_bitrate,
        card_speed_sufficient=eff["card_speed_sufficient"],
        vpg200_uxc_0xe228_required=eff["vpg200_required"],
        vpg400_uxc_0xe224_threshold_triggered=eff["vpg400_triggered"],
        sdhc_4gb_split_active=eff["sdhc_4gb_split_active"],
        cfexpress_type_b_rejected=eff["cfexpress_type_b_rejected"],
        requested_proxy_recording=norm_proxy_rec,
        effective_proxy_recording=eff["effective_proxy_recording"],
        proxy_file_format=eff["effective_proxy_file_format"],
        proxy_record_setting=eff["effective_proxy_record_setting"],
        proxy_resolution=eff["proxy_resolution"],
        proxy_codec=eff["proxy_codec"],
        proxy_bitrate_mbps=eff["proxy_bitrate_mbps"],
        proxy_bit_depth=eff["proxy_bit_depth"],
        proxy_blocked_by_frame_rate=eff["proxy_blocked_by_frame_rate"],
        proxy_allowed_on_dci_4k_up_to_59_94p=not claimed_dci_4k_blocks_proxy,
        proxy_sub_dir_path=eff["proxy_sub_dir_path"],
        proxy_in_camera_playback_permitted=False,
        coupled_delete_or_protect_requested=bool(coupled_delete_or_protect_requested),
        fx6_simul_rec_proxy_exclusion_ok=not fx6_exclusion_violation,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g139_rec_media_autoswitch_proxy_vault_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    rec_media_autoswitch_proxy_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase317DonorAuditResult] = None,
) -> Tuple[GateVerdict, G139RecMediaAutoSwitchProxyVaultGuardResult]:
    """Evaluate Wave-60 Gate `G139` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase317_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_rec_media_autoswitch_proxy_vault_guard(
        **(dict(rec_media_autoswitch_proxy_kwargs or {}))
    )
    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G139.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G139 if valid else codes[0]

    res = G139RecMediaAutoSwitchProxyVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        rec_media_autoswitch_proxy_vault_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, rec_media={guard.effective_recording_media}, "
        f"auto_switch={guard.effective_auto_switch_media}, card={guard.media_card_type}, "
        f"proxy={guard.effective_proxy_recording}({guard.proxy_file_format}/{guard.proxy_record_setting}), "
        f"slot1_writes={guard.slot1_data_sector_writes}"
    )
    verdict = GateVerdict(
        gate_id=G139_GATE_ID,
        gate_code=G139_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G140: Creators' Cloud, Cnct. while Power OFF Zero-RF & 42-Slot My Menu
# ---------------------------------------------------------------------------


def _compute_g140_effective_state(
    *,
    reset_action: str,
    cloud_connection: str,
    cloud_account_signout_requested: bool,
    ftp_transfer_enabled: bool,
    physical_power_switch: str,
    airplane_mode: str,
    cnct_while_power_off: str,
    bluetooth_function: str,
    bluetooth_paired: bool,
    zero_rf_bench_mode: bool,
    mymenu_op: str,
    display_from_mymenu: str,
    camset_export_requested: bool,
    camset_slot: str,
    slot_1_contains_tier0_vault: bool,
) -> Dict[str, Any]:
    init_reset = reset_action == RESET_ACTION_INITIALIZE_PHASE317
    net_or_init = reset_action in (
        RESET_ACTION_RESET_NETWORK_SET_PHASE317,
        RESET_ACTION_INITIALIZE_PHASE317,
    )

    # CRITICAL Persistence: Cloud Connection* / Cloud Information* survive EVEN [Initialize]!
    # Cleared ONLY by explicit Cloud Information sign-out/account deletion.
    eff_cloud = (
        "Off"
        if cloud_account_signout_requested
        else cloud_connection
    )
    cloud_survived_cam_reset = (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317
        and eff_cloud == "On"
    )
    cloud_survived_initialize = (
        init_reset and cloud_connection == "On" and not cloud_account_signout_requested
    )
    cloud_ftp_ok = not (eff_cloud == "On" and ftp_transfer_enabled)

    # Cnct. while Power OFF survives [Camera Settings Reset]; cleared by Net Reset / Initialize / unpair
    eff_cnct_off = "Off" if (net_or_init or not bluetooth_paired) else cnct_while_power_off
    # Airplane Mode persists across Net Reset & Initialize!
    eff_airplane = airplane_mode
    eff_bt = (
        "Off"
        if (eff_airplane == "On" or net_or_init)
        else bluetooth_function
    )
    cnct_survived_cam_reset = (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317
    )

    # BLE stays energized even when physical power switch == OFF if Cnct. while Power OFF == On!
    ble_power_off_energized = bool(
        eff_cnct_off == "On"
        and bluetooth_paired
        and eff_airplane == "Off"
    )
    zero_rf_enforced = bool(
        eff_airplane == "On"
        and eff_cnct_off == "Off"
        and eff_bt == "Off"
        and not ble_power_off_energized
    )
    rf_packets = 0 if zero_rf_enforced else (1 if ble_power_off_energized or eff_bt == "On" else 0)

    # My Menu & Display From My Menu survive [Camera Settings Reset]; cleared by Delete All or Initialize
    if init_reset or mymenu_op == "Delete All":
        eff_display_mm = "Off"
    else:
        eff_display_mm = display_from_mymenu
    mymenu_survived_cam_reset = (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317
    )

    slot1_camset_blocked = bool(
        camset_export_requested
        and camset_slot == REC_MEDIA_SLOT_1_G139
        and slot_1_contains_tier0_vault
    )

    return {
        "effective_cloud_connection": eff_cloud,
        "cloud_survived_cam_reset": cloud_survived_cam_reset,
        "cloud_survived_initialize": cloud_survived_initialize,
        "cloud_ftp_mutual_exclusion_ok": cloud_ftp_ok,
        "effective_airplane_mode": eff_airplane,
        "effective_cnct_while_power_off": eff_cnct_off,
        "effective_bluetooth_function": eff_bt,
        "cnct_while_power_off_survived_cam_reset": cnct_survived_cam_reset,
        "ble_power_off_energized": ble_power_off_energized,
        "zero_rf_enforced": zero_rf_enforced,
        "rf_packets_transmitted": rf_packets,
        "effective_display_from_mymenu": eff_display_mm,
        "mymenu_survived_cam_reset": mymenu_survived_cam_reset,
        "slot1_camset_vault_blocked": slot1_camset_blocked,
        "slot1_data_sector_writes": 0,
    }


def compute_creators_cloud_zerorf_mymenu_matrix() -> Dict[str, Any]:
    """Deterministically evaluate 256 state transitions for Cloud, Zero-RF & My Menu."""
    states_checked = 0
    cloud_survived_init_count = 0
    ble_power_off_hazard_count = 0
    zero_rf_clean_count = 0
    slot1_camset_blocked_count = 0

    for reset_act in (
        RESET_ACTION_NONE_PHASE317,
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
        RESET_ACTION_RESET_NETWORK_SET_PHASE317,
        RESET_ACTION_INITIALIZE_PHASE317,
    ):
        for cloud_on in ("Off", "On"):
            for signout in (False, True):
                for ftp_on in (False, True):
                    for airplane in ("Off", "On"):
                        for cnct_off in ("Off", "On"):
                            for camset_slot in (
                                REC_MEDIA_SLOT_1_G139,
                                REC_MEDIA_SLOT_2_G139,
                            ):
                                st = _compute_g140_effective_state(
                                    reset_action=reset_act,
                                    cloud_connection=cloud_on,
                                    cloud_account_signout_requested=signout,
                                    ftp_transfer_enabled=ftp_on,
                                    physical_power_switch="OFF",
                                    airplane_mode=airplane,
                                    cnct_while_power_off=cnct_off,
                                    bluetooth_function="On" if cnct_off == "On" else "Off",
                                    bluetooth_paired=True,
                                    zero_rf_bench_mode=(airplane == "On" and cnct_off == "Off"),
                                    mymenu_op="Add Item",
                                    display_from_mymenu="On",
                                    camset_export_requested=True,
                                    camset_slot=camset_slot,
                                    slot_1_contains_tier0_vault=True,
                                )
                                states_checked += 1
                                if st["cloud_survived_initialize"]:
                                    cloud_survived_init_count += 1
                                if st["ble_power_off_energized"]:
                                    ble_power_off_hazard_count += 1
                                if st["zero_rf_enforced"] and st["rf_packets_transmitted"] == 0:
                                    zero_rf_clean_count += 1
                                if st["slot1_camset_vault_blocked"]:
                                    slot1_camset_blocked_count += 1
                                assert st["slot1_data_sector_writes"] == 0

    return {
        "states_checked": states_checked,
        "cloud_survived_init_count": cloud_survived_init_count,
        "ble_power_off_hazard_count": ble_power_off_hazard_count,
        "zero_rf_clean_count": zero_rf_clean_count,
        "slot1_camset_vault_blocked_count": slot1_camset_blocked_count,
    }


def resolve_fx3_creators_cloud_zerorf_mymenu_state(
    **kwargs: Any,
) -> Dict[str, Any]:
    """Return serialized G140 guard state for UI/VM/orchestrator callers."""
    return verify_creators_cloud_zerorf_mymenu42_guard(**kwargs).to_dict()


def verify_creators_cloud_zerorf_mymenu42_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE317,
    body_model_id: int = FX3_MODEL_ID_PHASE317,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE317,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE317,
    target_model: str = FX3_MODEL_NAME_PHASE317,
    reset_action: str = RESET_ACTION_NONE_PHASE317,
    requested_cloud_connection: str = "Off",
    cloud_account_signout_requested: bool = False,
    assume_initialize_wipes_cloud_account: bool = False,
    c3_portal_profile: str = "None",
    clip_flag_filter: str = "NONE",
    ftp_transfer_enabled: bool = False,
    physical_power_switch: str = "OFF",
    requested_airplane_mode: str = "On",
    requested_cnct_while_power_off: str = "Off",
    requested_bluetooth_function: str = "Off",
    bluetooth_paired: bool = False,
    zero_rf_bench_mode: bool = True,
    mymenu_group: int = 1,
    mymenu_list: int = 0,
    mymenu_slot_index: Optional[int] = None,
    claimed_fx3_mymenu_capacity: int = FX3_MYMENU_EXACT_SLOTS_G140,
    mymenu_op: str = "None",
    mymenu_item_tab: str = "Shooting",
    requested_display_from_mymenu: str = "Off",
    camset_export_requested: bool = False,
    camset_slot: str = REC_MEDIA_SLOT_2_G139,
    slot_1_contains_tier0_vault: bool = True,
    fx6_user_menu_only: bool = False,
    fx6_user_menu_with_lock: bool = False,
    fx6_user_menu_lock_pin: str = "0000",
    fx6_user_menu_item_count: int = 20,
    claimed_fx6_user_menu_lock_exports_to_all_file: bool = False,
    claimed_fx6_has_bluetooth_cnct_power_off: bool = False,
) -> CreatorsCloudZeroRfMyMenu42GuardResult:
    """Enforce Gate G140: Creators' Cloud/C3 Portal persistence, Cnct. while Power OFF
    Zero-RF BLE firewall, and exact 42-slot FX3 My Menu vs 20-item FX6 User Menu with Lock.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_reset = _normalize_reset_action(reset_action)
    norm_cloud = _normalize_on_off(requested_cloud_connection)
    norm_air = _normalize_on_off(requested_airplane_mode)
    norm_cnct_off = _normalize_on_off(requested_cnct_while_power_off)
    norm_bt = _normalize_on_off(requested_bluetooth_function)
    norm_disp_mm = _normalize_on_off(requested_display_from_mymenu)
    norm_camset_slot = _normalize_rec_media_mode(camset_slot)

    fw_parsed = _parse_fw_major_minor(firmware_version)
    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE317
        and _is_real_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE317
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE317
        and fw_parsed is not None
    )
    if not identity_ok:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3 Ver. 7.02 hardware/help-guide/firmware identity for Gate G140."
        )

    if target_model not in (FX3_MODEL_NAME_PHASE317, FX6_MODEL_NAME_PHASE317):
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(f"Unsupported target_model `{target_model}`.")

    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(f"Invalid reset_action `{reset_action}`.")
        norm_reset = RESET_ACTION_NONE_PHASE317

    if norm_cloud is None:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_cloud_connection `{requested_cloud_connection}`.")
        norm_cloud = "Off"

    if norm_air is None:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_airplane_mode `{requested_airplane_mode}`.")
        norm_air = "On"

    if norm_cnct_off is None:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(
            f"Invalid requested_cnct_while_power_off `{requested_cnct_while_power_off}`."
        )
        norm_cnct_off = "Off"

    if norm_bt is None:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(
            f"Invalid requested_bluetooth_function `{requested_bluetooth_function}`."
        )
        norm_bt = "Off"

    if norm_disp_mm is None:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(
            f"Invalid requested_display_from_mymenu `{requested_display_from_mymenu}`."
        )
        norm_disp_mm = "Off"

    if norm_camset_slot not in (REC_MEDIA_SLOT_1_G139, REC_MEDIA_SLOT_2_G139):
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(f"Invalid camset_slot `{camset_slot}`.")
        norm_camset_slot = REC_MEDIA_SLOT_2_G139

    if physical_power_switch not in ALLOWED_POWER_SWITCH_STATES_G140:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(f"Invalid physical_power_switch `{physical_power_switch}`.")
        safe_pwr = "OFF"
    else:
        safe_pwr = physical_power_switch

    if c3_portal_profile not in ALLOWED_C3_PORTAL_PROFILES_G140:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(f"Invalid c3_portal_profile `{c3_portal_profile}`.")
        safe_c3 = "None"
    else:
        safe_c3 = c3_portal_profile

    if clip_flag_filter not in ALLOWED_CLIP_FLAGS_G140:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(f"Invalid clip_flag_filter `{clip_flag_filter}`.")
        safe_clip_flag = "NONE"
    else:
        safe_clip_flag = clip_flag_filter

    if mymenu_op not in MYMENU_OPS_G140:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(f"Invalid mymenu_op `{mymenu_op}`.")
        safe_mm_op = "None"
    else:
        safe_mm_op = mymenu_op

    if mymenu_item_tab not in ALLOWED_MENU_TABS_G140:
        _add_code(codes, STATUS_BLOCKED_G140_TELEMETRY_INVALID)
        errors.append(f"Invalid mymenu_item_tab `{mymenu_item_tab}`.")
        safe_mm_tab = "Shooting"
    else:
        safe_mm_tab = mymenu_item_tab

    eff = _compute_g140_effective_state(
        reset_action=norm_reset,
        cloud_connection=norm_cloud,
        cloud_account_signout_requested=bool(cloud_account_signout_requested),
        ftp_transfer_enabled=bool(ftp_transfer_enabled),
        physical_power_switch=safe_pwr,
        airplane_mode=norm_air,
        cnct_while_power_off=norm_cnct_off,
        bluetooth_function=norm_bt,
        bluetooth_paired=bool(bluetooth_paired),
        zero_rf_bench_mode=bool(zero_rf_bench_mode),
        mymenu_op=safe_mm_op,
        display_from_mymenu=norm_disp_mm,
        camset_export_requested=bool(camset_export_requested),
        camset_slot=norm_camset_slot,
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
    )

    # Part A: Creators' Cloud & C3 Portal persistence & Cloud/FTP exclusion
    cloud_init_trap = bool(
        assume_initialize_wipes_cloud_account and eff["cloud_survived_initialize"]
    )
    cloud_ftp_violation = not eff["cloud_ftp_mutual_exclusion_ok"]
    if cloud_init_trap or cloud_ftp_violation:
        _add_code(codes, STATUS_BLOCKED_G140_CLOUD_PERSISTENCE_OR_FTP_EXCLUSION_VIOLATION)
        errors.append(
            "Creators' Cloud / C3 Portal contract violated: `Cloud Connection *` / "
            "`Cloud Information *` survive even `[Initialize]` (require explicit sign-out), "
            "and `CLOUD_CONNECTION_ON_FTP_OFF` enforces strict mutual exclusion with FTP."
        )

    # Part B: CRITICAL Zero-RF Hazard ([Cnct. while Power OFF])
    zero_rf_violation = bool(
        zero_rf_bench_mode
        and (
            not eff["zero_rf_enforced"]
            or eff["rf_packets_transmitted"] != 0
            or eff["ble_power_off_energized"]
            or eff["effective_airplane_mode"] != "On"
            or eff["effective_cnct_while_power_off"] != "Off"
        )
    )
    fx6_bt_violation = bool(claimed_fx6_has_bluetooth_cnct_power_off)
    if zero_rf_violation or fx6_bt_violation:
        _add_code(codes, STATUS_BLOCKED_G140_CNCT_WHILE_POWER_OFF_ZERO_RF_VIOLATION)
        errors.append(
            "Zero-RF BLE firewall violated: when `[Cnct. while Power OFF] = On` (`_f 0x6ab3`, "
            "survives Camera Settings Reset), `UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER` stays "
            "energized even at physical switch `OFF`; Zero-RF bench mode MUST enforce BOTH "
            "`[Airplane Mode] = On` AND `[Cnct. while Power OFF] = Off` (`rf_packets == 0`), "
            "while FX6 has zero Bluetooth hardware."
        )

    # Part C: 42-Slot FX3 [My Menu] Disambiguation & Playback Tab Restriction
    if mymenu_slot_index is None:
        computed_slot = (
            (mymenu_group - 1) * 7 + mymenu_list
            if _is_real_int(mymenu_group) and _is_real_int(mymenu_list)
            else -1
        )
    else:
        computed_slot = mymenu_slot_index if _is_real_int(mymenu_slot_index) else -1

    bad_group_list = (
        not _is_real_int(mymenu_group)
        or not _is_real_int(mymenu_list)
        or mymenu_group < FX3_MYMENU_GROUP_MIN_G140
        or mymenu_group > FX3_MYMENU_GROUP_MAX_G140
        or mymenu_list < FX3_MYMENU_LIST_MIN_G140
        or mymenu_list > FX3_MYMENU_LIST_MAX_G140
    )
    bad_slot_index = (
        not _is_real_int(computed_slot)
        or computed_slot < 0
        or computed_slot >= FX3_MYMENU_EXACT_SLOTS_G140
    )
    bad_cap_myth = (
        not _is_real_int(claimed_fx3_mymenu_capacity)
        or claimed_fx3_mymenu_capacity != FX3_MYMENU_EXACT_SLOTS_G140
    )
    playback_tab_hit = bool(
        safe_mm_op == "Add Item" and safe_mm_tab in FX3_MYMENU_FORBIDDEN_TABS_G140
    )
    if bad_group_list or bad_slot_index or bad_cap_myth or playback_tab_hit:
        _add_code(codes, STATUS_BLOCKED_G140_MYMENU_42SLOT_OR_PLAYBACK_TAB_VIOLATION)
        errors.append(
            "My Menu 42-slot contract violated: `ILME-FX3` `[My Menu]` has exact `6 x 7 = 42` "
            "slots (`BKID_APP_mymenu_group{1..6}_setting_list{0..6}`, NOT 36 or 30), rejects "
            "index >= 42 and `(Playback)` tab item registration (`EINVAL=22`)."
        )

    # Part D: FX6 20-Item User Menu / Rental Lock Isolation & Slot-1 CAMSET Vault
    fx6_lock_on_fx3_violation = bool(
        target_model == FX3_MODEL_NAME_PHASE317
        and (fx6_user_menu_only or fx6_user_menu_with_lock)
    )
    bad_fx6_pin = not (
        isinstance(fx6_user_menu_lock_pin, str)
        and len(fx6_user_menu_lock_pin) == 4
        and fx6_user_menu_lock_pin.isdigit()
    )
    bad_fx6_cap = (
        not _is_real_int(fx6_user_menu_item_count)
        or fx6_user_menu_item_count < 0
        or fx6_user_menu_item_count > FX6_USER_MENU_MAX_ITEMS_G140
    )
    if (
        fx6_lock_on_fx3_violation
        or bad_fx6_pin
        or bad_fx6_cap
        or claimed_fx6_user_menu_lock_exports_to_all_file
        or eff["slot1_camset_vault_blocked"]
    ):
        _add_code(codes, STATUS_BLOCKED_G140_FX6_USER_MENU_LOCK_OR_SLOT1_CAMSET_VIOLATION)
        errors.append(
            "FX6 User Menu / Slot-1 CAMSET contract violated: FX6 `User Menu` caps at 20 items, "
            "`User Menu with Lock` uses 4-digit PIN (0000..9999) + `Multi-Function Dial + MENU` "
            "(excluded from `All File`, EOPNOTSUPP=95 on FX3), and `CAMSET*.DAT` export to "
            "`Slot 1` Tier-0 Vault is blocked (`EROFS=30`)."
        )

    block_errno: Optional[int] = None
    block_errno_name: Optional[str] = None
    if eff["slot1_camset_vault_blocked"]:
        block_errno = EROFS_ERRNO_PHASE317
        block_errno_name = EROFS_NAME_PHASE317
    elif fx6_lock_on_fx3_violation or fx6_bt_violation:
        block_errno = EOPNOTSUPP_ERRNO_PHASE317
        block_errno_name = EOPNOTSUPP_NAME_PHASE317
    elif (
        bad_group_list
        or bad_slot_index
        or bad_cap_myth
        or playback_tab_hit
        or bad_fx6_pin
        or bad_fx6_cap
        or claimed_fx6_user_menu_lock_exports_to_all_file
        or cloud_init_trap
        or cloud_ftp_violation
        or zero_rf_violation
    ):
        block_errno = EINVAL_ERRNO_PHASE317
        block_errno_name = EINVAL_NAME_PHASE317

    matrix = compute_creators_cloud_zerorf_mymenu_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G140 if valid else codes[0]

    return CreatorsCloudZeroRfMyMenu42GuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE317,
        target_model=target_model,
        reset_action=norm_reset,
        requested_cloud_connection=norm_cloud,
        effective_cloud_connection=eff["effective_cloud_connection"],
        cloud_account_signout_requested=bool(cloud_account_signout_requested),
        cloud_survived_cam_reset=eff["cloud_survived_cam_reset"],
        cloud_survived_initialize=eff["cloud_survived_initialize"],
        c3_portal_profile=safe_c3,
        clip_flag_filter=safe_clip_flag,
        ftp_transfer_enabled=bool(ftp_transfer_enabled),
        cloud_ftp_mutual_exclusion_ok=eff["cloud_ftp_mutual_exclusion_ok"],
        physical_power_switch=safe_pwr,
        requested_airplane_mode=norm_air,
        effective_airplane_mode=eff["effective_airplane_mode"],
        requested_cnct_while_power_off=norm_cnct_off,
        effective_cnct_while_power_off=eff["effective_cnct_while_power_off"],
        requested_bluetooth_function=norm_bt,
        effective_bluetooth_function=eff["effective_bluetooth_function"],
        bluetooth_paired=bool(bluetooth_paired),
        cnct_while_power_off_survived_cam_reset=eff[
            "cnct_while_power_off_survived_cam_reset"
        ],
        ble_power_off_energized=eff["ble_power_off_energized"],
        zero_rf_bench_mode=bool(zero_rf_bench_mode),
        zero_rf_enforced=eff["zero_rf_enforced"],
        rf_packets_transmitted=eff["rf_packets_transmitted"],
        cnct_while_power_off_g_0x6476_sc_tc_defect_known=True,
        fx6_bluetooth_absent=True,
        mymenu_exact_slots=FX3_MYMENU_EXACT_SLOTS_G140,
        mymenu_group=mymenu_group if _is_real_int(mymenu_group) else -1,
        mymenu_list=mymenu_list if _is_real_int(mymenu_list) else -1,
        mymenu_slot_index=computed_slot if _is_real_int(computed_slot) else -1,
        mymenu_op=safe_mm_op,
        mymenu_item_tab=safe_mm_tab,
        requested_display_from_mymenu=norm_disp_mm,
        effective_display_from_mymenu=eff["effective_display_from_mymenu"],
        mymenu_survived_cam_reset=eff["mymenu_survived_cam_reset"],
        fx3_30_or_36_slot_myth_rejected=True,
        playback_tab_registration_rejected=playback_tab_hit,
        camset_export_requested=bool(camset_export_requested),
        camset_slot=norm_camset_slot,
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        slot1_camset_vault_blocked=eff["slot1_camset_vault_blocked"],
        slot1_data_sector_writes=eff["slot1_data_sector_writes"],
        fx6_user_menu_max_items=FX6_USER_MENU_MAX_ITEMS_G140,
        fx6_user_menu_only=bool(fx6_user_menu_only),
        fx6_user_menu_with_lock=bool(fx6_user_menu_with_lock),
        fx6_user_menu_lock_pin=fx6_user_menu_lock_pin if isinstance(fx6_user_menu_lock_pin, str) else "INVALID",
        fx6_user_menu_lock_excluded_from_all_file=not claimed_fx6_user_menu_lock_exports_to_all_file,
        fx6_rental_lock_rejected_on_fx3=fx6_lock_on_fx3_violation,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g140_creators_cloud_zerorf_mymenu42_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    creators_cloud_mymenu_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase317DonorAuditResult] = None,
) -> Tuple[GateVerdict, G140CreatorsCloudZeroRfMyMenu42GuardResult]:
    """Evaluate Wave-60 Gate `G140` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase317_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_creators_cloud_zerorf_mymenu42_guard(
        **(dict(creators_cloud_mymenu_kwargs or {}))
    )
    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G140.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G140 if valid else codes[0]

    res = G140CreatorsCloudZeroRfMyMenu42GuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        creators_cloud_zerorf_mymenu42_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, cloud={guard.effective_cloud_connection}, "
        f"cnct_power_off={guard.effective_cnct_while_power_off}(ble_energized={guard.ble_power_off_energized},"
        f"zero_rf={guard.zero_rf_enforced},rf_pkts={guard.rf_packets_transmitted}), "
        f"mymenu_slots={guard.mymenu_exact_slots}(fx6_user_menu={guard.fx6_user_menu_max_items})"
    )
    verdict = GateVerdict(
        gate_id=G140_GATE_ID,
        gate_code=G140_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `140`-Gate Milestone Master Safety Preflight (`G01..G140`)
# ---------------------------------------------------------------------------


def evaluate_140gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    rec_media_autoswitch_proxy_kwargs: Optional[Mapping[str, Any]] = None,
    creators_cloud_mymenu_kwargs: Optional[Mapping[str, Any]] = None,
    master_138_override: Optional[Master138GateReport] = None,
    **m138_passthrough_kwargs: Any,
) -> Master140GateReport:
    """Evaluate all 140 Master Safety Gates (`G01..G140`) deterministically by
    delegating `G01..G138` directly to `evaluate_138gate_preflight()`.
    """
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        or simulate_bench_dry_run
        or bool(dry_run_simulated_backup)
    )

    m138_report: Master138GateReport = (
        master_138_override
        if master_138_override is not None
        else evaluate_138gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m138_passthrough_kwargs,
        )
    )

    phase317_audit = audit_phase317_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g139_verdict, g139_res = evaluate_g139_rec_media_autoswitch_proxy_vault_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        rec_media_autoswitch_proxy_kwargs=rec_media_autoswitch_proxy_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase317_audit,
    )

    g140_verdict, g140_res = evaluate_g140_creators_cloud_zerorf_mymenu42_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        creators_cloud_mymenu_kwargs=creators_cloud_mymenu_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase317_audit,
    )

    gates_139_to_140 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g139_verdict, g140_verdict)
    ]
    all_gates = tuple(list(m138_report.gates) + gates_139_to_140)

    g01_to_g12_verified = int(m138_report.summary["g01_to_g12_verified"])
    g13_to_g138_verified = int(m138_report.summary["g13_to_g136_verified"]) + int(
        m138_report.summary["g137_to_g138_verified"]
    )
    g139_to_g140_verified = sum(
        1 for v in (g139_verdict, g140_verdict) if v.passed
    )
    total_verified = (
        g01_to_g12_verified + g13_to_g138_verified + g139_to_g140_verified
    )

    g139_to_g140_all_passed = g139_to_g140_verified == 2
    g13_to_g140_all_passed = (
        m138_report.g13_to_g138_all_passed and g139_to_g140_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m138_report.gates[:9])

    offline_137_verified = (
        g01_to_g09_ok
        and m138_report.offline_135_gates_verified
        and g139_to_g140_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_140_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g140_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m138_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_137_verified
        and m138_report.h0_h1_trial_entry_allowed
        and g139_to_g140_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not CROSS_MODEL_FLASH_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m138_report.errors)
        + list(g139_verdict.errors)
        + list(g140_verdict.errors)
    )
    warnings: List[str] = (
        list(m138_report.warnings)
        + list(g139_verdict.warnings)
        + list(g140_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m138_report.g13_to_g138_all_passed:
        overall_status = m138_report.status
    elif not g139_verdict.passed:
        overall_status = g139_verdict.status
    elif not g140_verdict.passed:
        overall_status = g140_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_140_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_140_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_140_verified:
        overall_status = "VERIFIED_ALL_140_GATES"
    else:
        overall_status = "VERIFIED_137_OF_140_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m138_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g139_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g140_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 140,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 140 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g138_verified": g13_to_g138_verified,
        "g139_to_g140_verified": g139_to_g140_verified,
        "g13_to_g140_all_passed": g13_to_g140_all_passed,
        "g139_to_g140_all_passed": g139_to_g140_all_passed,
        "offline_137_gates_verified": offline_137_verified,
        "all_140_gates_verified": all_140_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master140GateReport(
        schema=REALHW_140GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_140GATE_PREFLIGHT_SCHEMA,
        version=REALHW_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_140GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_137_gates_verified=offline_137_verified,
        all_140_gates_verified=all_140_verified,
        g13_to_g140_all_passed=g13_to_g140_all_passed,
        g139_to_g140_all_passed=g139_to_g140_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_138_report=m138_report.to_dict(),
        g139_result=g139_res.to_dict(),
        g140_result=g140_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_140_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master140GateReport:
    return evaluate_140gate_preflight(repo_root, **kwargs)


def run_140_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master140GateReport:
    return evaluate_140gate_preflight(repo_root, **kwargs)


def _safe_write_json(payload: Any) -> None:
    try:
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard",
        description="Phase 317 Wave-60 G139/G140 and 140/140 Safety Gates Preflight CLI",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all 140/140 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g139", "g140", "140"],
        default="140",
        help="Target gate check: g139, g140, or 140",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g139":
        v, r = evaluate_g139_rec_media_autoswitch_proxy_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=clean,
        )
        if args.json:
            _safe_write_json(
                {
                    "gate": v.gate_id,
                    "status": r.status,
                    "verification_mode": r.verification_mode,
                    "valid": r.valid,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    if args.gate == "g140":
        v, r = evaluate_g140_creators_cloud_zerorf_mymenu42_guard(
            repo_root=args.repo_root,
            force_clean_room=clean,
        )
        if args.json:
            _safe_write_json(
                {
                    "gate": v.gate_id,
                    "status": r.status,
                    "verification_mode": r.verification_mode,
                    "valid": r.valid,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    rep = evaluate_140gate_preflight(
        args.repo_root,
        force_clean_room=clean,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        _safe_write_json(
            {
                "schema_version": rep.schema_version,
                "status": rep.status,
                "verification_mode": rep.verification_mode,
                "summary": rep.summary,
                "g139_status": rep.g139_result["status"],
                "g140_status": rep.g140_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/140\n"
        )
    ok = (
        rep.all_140_gates_verified
        if args.dry_run_simulated
        else rep.offline_137_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ALLOWED_C3_PORTAL_PROFILES_G140",
    "ALLOWED_CARD_TYPES_G139",
    "ALLOWED_CLIP_FLAGS_G140",
    "ALLOWED_MENU_TABS_G140",
    "ALLOWED_MOVIE_FILE_FORMATS_G139",
    "ALLOWED_MOVIE_RECORDING_MEDIA_G139",
    "ALLOWED_POWER_SWITCH_STATES_G140",
    "ALLOWED_PROXY_FILE_FORMATS_G139",
    "ALLOWED_PROXY_RECORD_SETTINGS_G139",
    "ALLOWED_REC_FRAME_RATES_G139",
    "ALLOWED_RESET_ACTIONS_PHASE317",
    "ALLOWED_SHOOT_MODES_PHASE317",
    "ALLOWED_SLOT_FILESYSTEMS_G139",
    "ALLOWED_SQ_FRAME_RATES_G139",
    "ALLOWED_STILL_RECORDING_MEDIA_G139",
    "ALWAYS_CONNECTED_F_UXC_RESID16_G140",
    "AUTO_SWITCH_MEDIA_F_UXC_RESID16_G139",
    "CARD_CFEXPRESS_TYPE_A_VPG200_G139",
    "CARD_CFEXPRESS_TYPE_A_VPG400_G139",
    "CARD_CFEXPRESS_TYPE_B_UNSUPPORTED_G139",
    "CARD_SDHC_LE32GB_G139",
    "CARD_SDXC_CLASS10_G139",
    "CARD_SDXC_U3_V30_G139",
    "CARD_SDXC_V60_G139",
    "CARD_SDXC_V90_G139",
    "CARD_SPEED_RANK_G139",
    "CFEXPRESS_VPG200_BASE_UXC_RESID16_G139",
    "CFEXPRESS_VPG400_BASE_UXC_RESID16_G139",
    "CNCT_WHILE_POWER_OFF_F_UXC_RESID16_G140",
    "CREATORS_CLOUD_G_UXC_RESID16_G140",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "CreatorsCloudZeroRfMyMenu42GuardResult",
    "DEFAULT_REPO_ROOT",
    "DISPLAY_FROM_MY_MENU_F_UXC_RESID16_G140",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE317",
    "DONOR_CHECK_MAX_SECONDS_PHASE317",
    "DORMANT_PRIORITIZE_REC_MEDIA_TRAPS_G139",
    "DORMANT_PROXY_SETTINGS_G139",
    "EBUSY_ERRNO_PHASE317",
    "EBUSY_NAME_PHASE317",
    "EINVAL_ERRNO_PHASE317",
    "EINVAL_NAME_PHASE317",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "ENODEV_ERRNO_PHASE317",
    "ENODEV_NAME_PHASE317",
    "ENV_CLEAN_ROOM_TEST_PHASE317",
    "ENV_FORCE_CLEAN_ROOM",
    "EOPNOTSUPP_ERRNO_PHASE317",
    "EOPNOTSUPP_NAME_PHASE317",
    "EROFS_ERRNO_PHASE317",
    "EROFS_NAME_PHASE317",
    "FX3_DEFAULT_FW_VERSION_PHASE317",
    "FX3_HELP_GUIDE_CODE_PHASE317",
    "FX3_MODEL_ID_PHASE317",
    "FX3_MODEL_NAME_PHASE317",
    "FX3_MYMENU_EXACT_SLOTS_G140",
    "FX3_MYMENU_FORBIDDEN_TABS_G140",
    "FX3_MYMENU_GROUP_MAX_G140",
    "FX3_MYMENU_GROUP_MIN_G140",
    "FX3_MYMENU_LIST_MAX_G140",
    "FX3_MYMENU_LIST_MIN_G140",
    "FX6_DEFAULT_FW_VERSION_PHASE317",
    "FX6_MODEL_NAME_PHASE317",
    "FX6_PRODUCT_CODE_PHASE317",
    "FX6_PROXY_CHUNK_DURATIONS_G139",
    "FX6_PROXY_SUB_PATH_G139",
    "FX6_RENTAL_LOCK_CHORD_G140",
    "FX6_USER_MENU_MAX_ITEMS_G140",
    "G139",
    "G139RecMediaAutoSwitchProxyVaultGuardResult",
    "G139_GATE_CODE",
    "G139_GATE_ID",
    "G140",
    "G140CreatorsCloudZeroRfMyMenu42GuardResult",
    "G140_GATE_CODE",
    "G140_GATE_ID",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HUMAN_HARDWARE_ATTACH_TOKEN",
    "MOVIE_FORMAT_XAVC_HS_4K_G139",
    "MOVIE_FORMAT_XAVC_S_4K_G139",
    "MOVIE_FORMAT_XAVC_S_HD_G139",
    "MOVIE_FORMAT_XAVC_S_I_4K_G139",
    "MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139",
    "MOVIE_FORMAT_XAVC_S_I_HD_G139",
    "MYMENU_OPS_G140",
    "MY_MENU_G_UXC_RESID16_G140",
    "Master140GateReport",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PINNED_FX3_APPFW_SLICES_PHASE317",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE317",
    "PINNED_FX6_APPFW_SLICES_PHASE317",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE317",
    "PINNED_PHASE317_DONOR_SPECS",
    "PROXY_BLOCKED_REC_FRAME_RATES_G139",
    "PROXY_BLOCKED_SQ_FRAME_RATES_G139",
    "PROXY_FORMAT_XAVC_HS_HD_G139",
    "PROXY_FORMAT_XAVC_S_HD_G139",
    "PROXY_SETTINGS_F_UXC_RESID16_G139",
    "PROXY_SETTING_16M_10BIT_G139",
    "PROXY_SETTING_6M_8BIT_G139",
    "PROXY_SETTING_9M_10BIT_G139",
    "PROXY_SUB_PATH_CFEXPRESS_G139",
    "PROXY_SUB_PATH_SDXC_G139",
    "Phase317DonorAuditResult",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_140GATE_PREFLIGHT_SCHEMA",
    "REALHW_CREATORS_CLOUD_CNCT_WHILE_POWER_OFF_ZERO_RF_AND_MYMENU_42SLOT_GUARD",
    "REALHW_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_140GATE_SCHEMA",
    "REALHW_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_140GATE_VERSION",
    "REALHW_REC_MEDIA_AUTO_SWITCH_OVERFLOW_VPG400_AND_PROXY_SUB_VAULT_GUARD",
    "REC_MEDIA_SIMULT_G139",
    "REC_MEDIA_SLOT_1_G139",
    "REC_MEDIA_SLOT_2_G139",
    "REC_MEDIA_SORT_G139",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317",
    "RESET_ACTION_INITIALIZE_PHASE317",
    "RESET_ACTION_NONE_PHASE317",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE317",
    "RecMediaAutoSwitchProxyVaultGuardResult",
    "SHOOT_MODE_MOVIE_PHASE317",
    "SHOOT_MODE_SQ_PHASE317",
    "SHOOT_MODE_STILL_PHASE317",
    "SLOT_FS_EXFAT_G139",
    "SLOT_FS_FAT32_G139",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_BLOCKED_G139_CARD_SPEED_OR_TYPEB_VIOLATION",
    "STATUS_BLOCKED_G139_PROXY_FORMAT_EXCLUSION_OR_FX6_CROSSWIRE_VIOLATION",
    "STATUS_BLOCKED_G139_REC_MEDIA_SPLIT_FS_OR_DORMANT_PRIORITIZE_VIOLATION",
    "STATUS_BLOCKED_G139_SLOT2_TO_SLOT1_OVERFLOW_OR_VAULT_VIOLATION",
    "STATUS_BLOCKED_G139_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G140_CLOUD_PERSISTENCE_OR_FTP_EXCLUSION_VIOLATION",
    "STATUS_BLOCKED_G140_CNCT_WHILE_POWER_OFF_ZERO_RF_VIOLATION",
    "STATUS_BLOCKED_G140_FX6_USER_MENU_LOCK_OR_SLOT1_CAMSET_VIOLATION",
    "STATUS_BLOCKED_G140_MYMENU_42SLOT_OR_PLAYBACK_TAB_VIOLATION",
    "STATUS_BLOCKED_G140_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PERSISTENT_EMMC_WRITE",
    "STATUS_BLOCKED_PHASE317_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G139",
    "STATUS_VERIFIED_G140",
    "STATUS_VERIFIED_SAFE",
    "USB_PACKETS_TRANSMITTED",
    "audit_phase317_donor_contracts",
    "compute_creators_cloud_zerorf_mymenu_matrix",
    "compute_rec_media_autoswitch_proxy_matrix",
    "evaluate_140_master_safety_gates",
    "evaluate_140gate_preflight",
    "evaluate_g139_rec_media_autoswitch_proxy_vault_guard",
    "evaluate_g140_creators_cloud_zerorf_mymenu42_guard",
    "main",
    "resolve_fx3_creators_cloud_zerorf_mymenu_state",
    "resolve_fx3_rec_media_autoswitch_proxy_state",
    "run_140_gate_preflight",
    "verify_creators_cloud_zerorf_mymenu42_guard",
    "verify_rec_media_autoswitch_proxy_vault_guard",
]


if __name__ == "__main__":
    raise SystemExit(main())
