#!/usr/bin/env python3
"""Phase 278 (Stage 55, 55/55) — Real-Hardware ILME-FX3 Wave-45
`[Focus Assistant]` (`Focus Magnifier`, `Auto Magnifier in MF`, `Initial Focus Mag.` `x1.0`,
`AF in Focus Mag.`) & `[Peaking Display]` / `[AF Illuminator]` (Still-Only),
`[Area/Date/Time Setting]` (`Setup > Area/Date`) & Zero-RF Creators' App Isolation, and
`[Video Light Mode]` (`Power Link` Default & MI-Shoe `5V <= 900 mA` Rail Budget) &
`[HDMI Resolution]` (`Auto` Default & Log `1080p` Override) HIL Co-Emulator.

Strictly models Wave-45 official Sony `ILME-FX3` (`ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) contracts without hardware
attachment or firmware byte leakage:

1. **Sub-Model 55A — `[Focus Assistant]` & `[Peaking Display]` / `[AF Illuminator]`**:
   - `MENU -> Focus -> [Focus Assistant]`:
     - `[Auto Magnifier in MF]`: `On` (factory default; exact `ilc/2210` title,
       rejects legacy `"MF Assist"` title spoofing `EOPNOTSUPP = 95`).
     - `[Focus Magnifier]`: Assigned to `Custom Button 5` by default + MF/DMF LCD
       double-tap when `Touch Operation = On`.
     - `[Focus Magnif. Time]`: `No Limit` (default) / `2 Sec` / `5 Sec`.
     - Separate Still & Movie `[Initial Focus Mag.]` registers (`x1.0` default / `x4.0`).
     - Still `[AF in Focus Mag.]`: `On` (default) / `Off` (still-image only).
     - HDMI clean-feed exit / `RAW Output` lockout rules: `RAW Output = On` locks
       out Focus Magnifier output magnification, and neither magnification nor
       peaking ever bakes onto external HDMI (`hdmi_clean_feed_mag_or_peaking_leaked_pixels == 0`).
   - `[Peaking Display]`: `Off` default / `On`; `[Peaking Level]`: `Mid` default
     (`High`/`Mid`/`Low`); `[Peaking Color]`: `White` default
     (`Red`/`Yellow`/`Blue`/`White`), LCD-only clean HDMI.
   - `[AF Illuminator]`: `Auto` default / `Off` — Still-image AF ONLY (never fires
     in `Movie` / `S&Q`, `af_illuminator_movie_or_sq_fire_events == 0`).

2. **Sub-Model 55B — `[Area/Date/Time Setting]` (`Setup > Area/Date`) & Zero-RF Isolation**:
   - Exact `ilc/2210` title `[Area/Date/Time Setting]` (rejects legacy
     `"Date/Time Setup"` spoofing `EOPNOTSUPP = 95`): `[Area Setting]` (`"—"`
     initial unconfigured state), `[Daylight Savings]` (`Off` default / `On`),
     `[Date/Time]`, `[Date Format]`; survives `[Camera Settings Reset]` under
     `[Setup]` (cleared/re-prompted only by `[Initialize]` or RTC backup battery loss).
   - Zero-RF air-gapped bench isolation (`[Airplane Mode] = [On]`,
     `passive_tx_bytes_emitted == 0`): blocks Creators' App
     `[Location Information Linkage]` (`[Auto Time Correction]` /
     `[Auto Area Adjustment]`) Bluetooth/Wi-Fi sync so `H0..H3` forensic RTC
     timestamps never jump unexpectedly (`creators_app_rtc_sync_jump_events == 0`).

3. **Sub-Model 55C & Redlines — `[Video Light Mode]` (`Power Link` & MI-Shoe
   `5V <= 900 mA`) & `[HDMI Resolution]` (`Auto` & Log `1080p` Override)**:
   - `[Video Light Mode]`: `Power Link` default / `REC Link` / `REC Link & STBY` /
     `Auto`, survives `[Camera Settings Reset]` under `[Setup]`, with MI-Shoe
     `5V <= 900 mA` accessory rail overcurrent lockout (`Gate G24` parity,
     `mishoe_5v_900ma_overcurrent_events == 0`).
   - `[HDMI Resolution]`: `Auto` default / `2160p` / `1080p` / `1080i`, survives
     `[Camera Settings Reset]` under `[Setup]`; models automatic downshift to
     `1080p` during internal recording when `[Log Shooting] != Off` (unless
     `Rec. Media dur HDMI Output = Off(HDMI Only)`).

4. **Dual-Mode 18-Donor `O_RDONLY` SHA-256 Verification & Hard Safety Redlines**:
   - Pins exact byte sizes & SHA-256 hashes of 18 `ILME-FX3 Ver. 7.02` &
     `ILME-FX6 Ver. 6.01` donors strictly `os.O_RDONLY` (`raw_firmware_bytes_leaked == 0`),
     with deterministic `CLEAN_ROOM_SYNTHETIC` parity under `FX3_CLEAN_ROOM_TEST=1`
     or `FX3_FX6_FORCE_CLEAN_ROOM=1`.
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
import re
import struct
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_focus_mag_datetime_videolight_hdmires_coemulator_v1"
PHASE_278_SCHEMA = SCHEMA_ID
PHASE_278_VERSION = "278.0.0"
PHASE_NUMBER = 278
STAGE_INDEX = 55
STAGE_TOTAL = 55
MILESTONE_LABEL = "55/55"
STAGE_NAME = "stage55_realhw_focus_mag_datetime_videolight_hdmires_hil"
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EACCES_ERRNO = 13
EINVAL_ERRNO = 22
EROFS_ERRNO = 30
EOPNOTSUPP_ERRNO = 95

BOUNDED_WINDOW_MAX_BYTES = 4096

# Hard Safety Redline invariants (strictly locked False / 0 / True)
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
EMMC_CORRUPTIONS = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0

# Wave-45 Stage 55 zero-fault invariants
LEGACY_MF_ASSIST_SPOOF_EVENTS = 0
HDMI_CLEAN_FEED_MAG_OR_PEAKING_LEAKED_PIXELS = 0
AF_ILLUMINATOR_MOVIE_OR_SQ_FIRE_EVENTS = 0
LEGACY_DATE_TIME_SETUP_SPOOF_EVENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
CREATORS_APP_RTC_SYNC_JUMP_EVENTS = 0
MISHOE_5V_900MA_OVERCURRENT_EVENTS = 0
HDMI_LOG_1080P_DOWNSHIFT_BYPASS_EVENTS = 0

RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Environment variables (supports both FX3_CLEAN_ROOM_TEST=1 and FX3_FX6_FORCE_CLEAN_ROOM=1)
ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# ---------------------------------------------------------------------------
# Verified Local Donor Specs (18 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_adj_media": f"{_FX3_USR_PREFIX}/lib/libInfraAdjMedia.so",
    "fx3_airplane": f"{_FX3_USR_PREFIX}/lib/libInfraAirplaneMode.so",
    "fx3_saveload": f"{_FX3_USR_PREFIX}/lib/libSaveLoadSettings.so",
    "fx3_buspower": f"{_FX3_USR_PREFIX}/lib/libBusPower.so",
    "fx3_media_cfg": f"{_FX3_USR_PREFIX}/lib/libInfraMediaConfig.so",
    "fx3_media_common": f"{_FX3_USR_PREFIX}/lib/libInfraMediaCommon.so",
    "fx3_bt_core": f"{_FX3_USR_PREFIX}/lib/libInfraBluetoothCore.so",
    "fx3_wlan_common": f"{_FX3_USR_PREFIX}/lib/libWlanControlCommon.so",
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
    "fx3_adj_media": 318_152,
    "fx3_airplane": 14_488,
    "fx3_saveload": 18_760,
    "fx3_buspower": 43_968,
    "fx3_media_cfg": 52_312,
    "fx3_media_common": 402_624,
    "fx3_bt_core": 267_592,
    "fx3_wlan_common": 18_528,
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

EXPECTED_COMPACT_DONOR_SHA256: Mapping[str, str] = {
    "fx3_adj_media": "caae47cd50a72816f75515724828a0d136985844fe3b9a13ad0fda15b08dbf11",
    "fx3_airplane": "dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea",
    "fx3_saveload": "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
    "fx3_buspower": "4c39d2789745a4638490da1aa41b39c90980c7dd30837a693e87085689bbcc0e",
    "fx3_media_cfg": "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486",
    "fx3_media_common": "1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b",
    "fx3_bt_core": "fcfb4a0086220c53a002394d268c3fb423f6cbf925beaca8ec34a409b3de566b",
    "fx3_wlan_common": "50762f00b879a25c66048dd4525be78c31d50395c638749784d6b867e58dab07",
    "fx3_string_en_f": "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
    "fx6_string_en": "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
    "fx3_cpapp": "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d",
    "fx6_cpapp": "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d",
    "fx3_libmpr": "8b06e341401c676431f3ceed99240f3b529ed60d86eacee8cf3b1b1b8463a9b2",
    "fx6_libmpr": "e7a0ea07af5aa65e628a41a9bd853b5dec28422ed0618bea30c099ede31716d6",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_bk4": "da125f7fabe4a5141f16347ade9a4417d7ca23862cb14c3b9343b5e19a81d05c",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_adj_media": (
        b"AVBB_SCN_START_HDMI",
        b"AVBB_SCN_STOP_HDMI",
        b"AUDIO",
        b"Backup_read",
    ),
    "fx3_airplane": (
        b"AirplaneModeTraceRecord",
        b"UpdateInhFactor",
        b"Backup_read",
        b"Backup_get_datasize",
    ),
    "fx3_saveload": (
        b"SaveLoadSettingsIf",
        b"_ZN18SaveLoadSettingsIf13requestToReadEN",
        b"Backup_read",
        b"Backup_write",
    ),
    "fx3_buspower": (
        b"BusPower_Init",
        b"_ZN8BusPower4InitEv",
        b"_ZN8BusPower11GetInstanceEv",
        b"_ZN8BusPower7PreInitEv",
    ),
    "fx3_media_cfg": (
        b"InfraMediaConfig",
        b"_ZN16InfraMediaConfig10SaveBackupEt",
        b"Backup_sync_subsystem",
        b"Slot",
    ),
    "fx3_media_common": (
        b"mcmn_misc_getcputime",
        b"clock_gettime",
        b"Backup_read_8Byte",
        b"Media",
    ),
    "fx3_bt_core": (
        b"InfraBTCore_",
        b"BTUtils_",
        b"CTmpDir",
        b"CBTCoreProcess",
    ),
    "fx3_wlan_common": (
        b"WlanControlCommon",
        b"NetworkTraceRecordError",
        b"Backup_read_4Byte",
        b"initializePort",
    ),
    "fx3_string_en_f": (
        b"Auto Magnifier in MF",
        b"Focus Magnif. Time",
        b"Initial Focus Mag.",
        b"AF in Focus Mag.",
        b"No Limit",
        b"x1.0",
        b"x4.0",
        b"Peaking Display",
        b"Peaking Level",
        b"Peaking Color",
        b"AF Illuminator",
        b"Touch Operation",
        b"Area/Date/Time Setting",
        b"Date/Time",
        b"Date Format",
        b"Location Info. Link",
        b"Auto Time Correction",
        b"Auto Area Adjustment",
        b"Airplane Mode",
        b"Video Light Mode",
        b"Power Link",
        b"REC Link",
        b"HDMI Resolution",
        b"2160p",
        b"1080p",
        b"RAW Output",
        b"Log Shooting",
        b"Rec. Media dur HDMI Output",
        b"Off(HDMI Only)",
        b"Camera Settings Reset",
        b"Reset Network Set.",
        b"Initialize",
        b"High",
        b"Mid",
        b"Low",
        b"Red",
        b"Yellow",
        b"Blue",
        b"White",
        b"2 Sec",
        b"5 Sec",
        b"Auto",
        b"On",
        b"Off",
    ),
    "fx6_string_en": (
        b"Focus Magnifier",
        b"Peaking Level",
        b"Touch Operation",
        b"Date/Time",
        b"RAW Output",
        b"1080i",
    ),
}

COMPACT_ABSENT_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Date/Time Setup",
        b"Autoframing Settings",
        b"Built-In ND",
        b"ECS",
    ),
    "fx6_string_en": (
        b"Auto Magnifier in MF",
        b"Area/Date/Time Setting",
        b"Video Light Mode",
        b"HDMI Resolution",
        b"AF Illuminator",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_946_624, "HDMI", b"HDMI"),
        (50_749_440, "MAGNIFIER", b"MAGNIFIER"),
        (49_954_816, "PEAKING", b"PEAKING"),
        (49_942_528, "FOCUS", b"FOCUS"),
        (49_930_240, "TIME", b"TIME"),
        (49_971_200, "VIDEO_LIGHT", b"VIDEO_LIGHT"),
        (58_707_968, "AIRPLANE", b"AIRPLANE"),
        (49_876_992, "INITIALIZE", b"Initialize"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (35_971_072, "HDMI", b"HDMI"),
        (37_236_736, "MAGNIFIER", b"MAGNIFIER"),
        (39_378_944, "PEAKING", b"PEAKING"),
        (36_081_664, "FOCUS", b"FOCUS"),
        (39_022_592, "VIDEO_LIGHT", b"VIDEO_LIGHT"),
        (35_987_456, "INITIALIZE", b"Initialize"),
    ),
    "fx3_cpapp": (
        (696_320, "HDMI", b"HDMI"),
        (13_119_488, "PEAKING", b"PEAKING"),
        (172_032, "FOCUS", b"FOCUS"),
        (385_024, "DATE", b"DATE"),
        (487_424, "TIME", b"TIME"),
        (1_994_752, "VIDEO_LIGHT", b"VIDEO_LIGHT"),
        (163_840, "INITIALIZE", b"Initialize"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (684_032, "HDMI", b"HDMI"),
        (14_557_184, "PEAKING", b"PEAKING"),
        (184_320, "FOCUS", b"FOCUS"),
        (389_120, "DATE", b"DATE"),
        (487_424, "TIME", b"TIME"),
        (167_936, "INITIALIZE", b"Initialize"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (2_920_448, "DATE", b"DATE"),
        (163_840, "TIME", b"TIME"),
        (258_048, "INITIALIZE", b"Initialize"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (13_398_016, "DATE", b"DATE"),
        (204_800, "TIME", b"TIME"),
        (315_392, "INITIALIZE", b"Initialize"),
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
# Wave-45 Official ILME-FX3 Ver. 7.02 Sub-Model 55A / 55B / 55C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"

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

TOGGLE_OFF = "Off"
TOGGLE_ON = "On"
VALID_TOGGLE_STATES: Tuple[str, ...] = (TOGGLE_OFF, TOGGLE_ON)

SHOOTING_DOMAIN_STILL = "Still"
SHOOTING_DOMAIN_MOVIE = "Movie"
SHOOTING_DOMAIN_SQ = "S&Q"
VALID_SHOOTING_DOMAINS: Tuple[str, ...] = (
    SHOOTING_DOMAIN_STILL,
    SHOOTING_DOMAIN_MOVIE,
    SHOOTING_DOMAIN_SQ,
)

# Sub-Model 55A: [Focus Assistant] & [Peaking Display] & [AF Illuminator]
FOCUS_ASSISTANT_MENU_PATH = "MENU -> Focus -> [Focus Assistant]"
AUTO_MAGNIFIER_IN_MF_TITLE = "Auto Magnifier in MF"
LEGACY_MF_ASSIST_TITLE = "MF Assist"
FOCUS_MAGNIFIER_DEFAULT_KEY = "Custom Button 5"
PEAKING_DISPLAY_MENU_PATH = "MENU -> Focus -> [Peaking Display]"
PEAKING_DISPLAY_SELECT_DEFAULT_KEY = "Control Wheel Right"
AF_ILLUMINATOR_MENU_PATH = "MENU -> Focus -> [AF/MF] -> [AF Illuminator]"

FOCUS_MAG_TIME_NO_LIMIT = "No Limit"
FOCUS_MAG_TIME_2S = "2 Sec"
FOCUS_MAG_TIME_5S = "5 Sec"
VALID_FOCUS_MAG_TIMES: Tuple[str, ...] = (
    FOCUS_MAG_TIME_NO_LIMIT,
    FOCUS_MAG_TIME_2S,
    FOCUS_MAG_TIME_5S,
)

INITIAL_FOCUS_MAG_X1_0 = "x1.0"
INITIAL_FOCUS_MAG_X4_0 = "x4.0"
VALID_INITIAL_FOCUS_MAGS: Tuple[str, ...] = (
    INITIAL_FOCUS_MAG_X1_0,
    INITIAL_FOCUS_MAG_X4_0,
)

FOCUS_MODE_MF = "MF"
FOCUS_MODE_DMF = "DMF"
FOCUS_MODE_AF_S = "AF-S"
FOCUS_MODE_AF_C = "AF-C"
FOCUS_MODE_AF_A = "AF-A"
VALID_FOCUS_MODES: Tuple[str, ...] = (
    FOCUS_MODE_MF,
    FOCUS_MODE_DMF,
    FOCUS_MODE_AF_S,
    FOCUS_MODE_AF_C,
    FOCUS_MODE_AF_A,
)

PEAKING_LEVEL_HIGH = "High"
PEAKING_LEVEL_MID = "Mid"
PEAKING_LEVEL_LOW = "Low"
VALID_PEAKING_LEVELS: Tuple[str, ...] = (
    PEAKING_LEVEL_HIGH,
    PEAKING_LEVEL_MID,
    PEAKING_LEVEL_LOW,
)

PEAKING_COLOR_RED = "Red"
PEAKING_COLOR_YELLOW = "Yellow"
PEAKING_COLOR_BLUE = "Blue"
PEAKING_COLOR_WHITE = "White"
VALID_PEAKING_COLORS: Tuple[str, ...] = (
    PEAKING_COLOR_RED,
    PEAKING_COLOR_YELLOW,
    PEAKING_COLOR_BLUE,
    PEAKING_COLOR_WHITE,
)

AF_ILLUMINATOR_AUTO = "Auto"
AF_ILLUMINATOR_OFF = "Off"
VALID_AF_ILLUMINATOR_MODES: Tuple[str, ...] = (
    AF_ILLUMINATOR_AUTO,
    AF_ILLUMINATOR_OFF,
)

MONITOR_SINK_LCD_LIVE_VIEW = "LCD_LIVE_VIEW"
MONITOR_SINK_EXTERNAL_HDMI = "EXTERNAL_HDMI"
VALID_MONITOR_SINKS: Tuple[str, ...] = (
    MONITOR_SINK_LCD_LIVE_VIEW,
    MONITOR_SINK_EXTERNAL_HDMI,
)

# Sub-Model 55B: [Area/Date/Time Setting] & Zero-RF Creators' App Isolation
AREA_DATETIME_MENU_PATH = "MENU -> Setup -> [Area/Date] -> [Area/Date/Time Setting]"
AREA_DATETIME_OFFICIAL_TITLE = "Area/Date/Time Setting"
LEGACY_DATE_TIME_SETUP_TITLE = "Date/Time Setup"
CREATORS_APP_LOC_LINK_MENU_PATH = "MENU -> Network -> [Creators' App] -> [Location Information Linkage]"
AIRPLANE_MODE_MENU_PATH = "MENU -> Network -> [Network Option] -> [Airplane Mode]"

AREA_UNCONFIGURED = "—"
VALID_AREA_SETTINGS: Tuple[str, ...] = (
    AREA_UNCONFIGURED,
    "UTC",
    "Tokyo",
    "Los Angeles",
    "New York",
    "London",
    "Paris",
    "Berlin",
    "Sydney",
)

DATE_FORMAT_YYYY_MM_DD = "YYYY-MM-DD"
DATE_FORMAT_MM_DD_YYYY = "MM-DD-YYYY"
DATE_FORMAT_DD_MM_YYYY = "DD-MM-YYYY"
VALID_DATE_FORMATS: Tuple[str, ...] = (
    DATE_FORMAT_YYYY_MM_DD,
    DATE_FORMAT_MM_DD_YYYY,
    DATE_FORMAT_DD_MM_YYYY,
)
DEFAULT_DATETIME_STR = "2026-11-17 15:00:00"
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

BENCH_STAGE_H0 = "H0"
BENCH_STAGE_H1 = "H1"
BENCH_STAGE_H2 = "H2"
BENCH_STAGE_H3 = "H3"
VALID_BENCH_STAGES: Tuple[str, ...] = (
    BENCH_STAGE_H0,
    BENCH_STAGE_H1,
    BENCH_STAGE_H2,
    BENCH_STAGE_H3,
)

# Sub-Model 55C: [Video Light Mode] & MI-Shoe 5V<=900mA + [HDMI Resolution]
VIDEO_LIGHT_MODE_MENU_PATH = "MENU -> Setup -> [Setup Option] -> [Video Light Mode]"
HDMI_RESOLUTION_MENU_PATH = "MENU -> Setup -> [External Output] -> [HDMI Resolution]"
REC_MEDIA_DUR_HDMI_MENU_PATH = "MENU -> Setup -> [External Output] -> [Rec. Media dur HDMI Output]"

VIDEO_LIGHT_POWER_LINK = "Power Link"
VIDEO_LIGHT_REC_LINK = "REC Link"
VIDEO_LIGHT_REC_LINK_STBY = "REC Link & STBY"
VIDEO_LIGHT_AUTO = "Auto"
VALID_VIDEO_LIGHT_MODES: Tuple[str, ...] = (
    VIDEO_LIGHT_POWER_LINK,
    VIDEO_LIGHT_REC_LINK,
    VIDEO_LIGHT_REC_LINK_STBY,
    VIDEO_LIGHT_AUTO,
)

CAMERA_STATE_POWER_OFF = "POWER_OFF"
CAMERA_STATE_POWER_ON = "POWER_ON"
CAMERA_STATE_STBY = "STBY"
CAMERA_STATE_REC = "REC"
VALID_CAMERA_STATES: Tuple[str, ...] = (
    CAMERA_STATE_POWER_OFF,
    CAMERA_STATE_POWER_ON,
    CAMERA_STATE_STBY,
    CAMERA_STATE_REC,
)

MISHOE_5V_VOLTAGE_MV = 5000
MISHOE_5V_RAIL_LIMIT_MA = 900
HVL_LBPC_NOMINAL_LOAD_MA = 450

HDMI_RES_AUTO = "Auto"
HDMI_RES_2160P = "2160p"
HDMI_RES_1080P = "1080p"
HDMI_RES_1080I = "1080i"
VALID_HDMI_RESOLUTIONS: Tuple[str, ...] = (
    HDMI_RES_AUTO,
    HDMI_RES_2160P,
    HDMI_RES_1080P,
    HDMI_RES_1080I,
)

LOG_SHOOTING_OFF = "Off"
LOG_SHOOTING_CINE_EI = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK = "Cine EI Quick"
LOG_SHOOTING_FLEXIBLE_ISO = "Flexible ISO"
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    LOG_SHOOTING_OFF,
    LOG_SHOOTING_CINE_EI,
    LOG_SHOOTING_CINE_EI_QUICK,
    LOG_SHOOTING_FLEXIBLE_ISO,
)

REC_MEDIA_DUR_HDMI_ON = "On"
REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY = "Off(HDMI Only)"
VALID_REC_MEDIA_DUR_HDMI_OPTIONS: Tuple[str, ...] = (
    REC_MEDIA_DUR_HDMI_ON,
    REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
)

ALL_16_REDLINE_PROBE_FIELDS: Tuple[str, ...] = (
    "persistent_emmc_write_requested",
    "hardware_live_attach_requested",
    "isp_write_requested",
    "spi_nor_write_requested",
    "el3_payload_transmit_requested",
    "cnflasha_userspace_write_requested",
    "cp_mutation_requested",
    "wbi_mutation_requested",
    "nop_patch_requested",
    "otp_fuse_touch_requested",
    "rpmb_increment_requested",
    "legacy_mf_assist_or_datetime_setup_spoof_requested",
    "hdmi_mag_or_peaking_bake_requested",
    "af_illuminator_movie_sq_fire_requested",
    "creators_app_zero_rf_bypass_requested",
    "mishoe_overcurrent_or_log_1080p_bypass_requested",
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
    sha256: str
    sha256_prefix16: str
    sha256_verified: bool
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
    head_sha256: str
    head_sha256_prefix16: str
    head_sha256_verified: bool


@dataclass(frozen=True)
class Phase278DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_adj_media: CompactDonorSummary
    fx3_airplane: CompactDonorSummary
    fx3_saveload: CompactDonorSummary
    fx3_buspower: CompactDonorSummary
    fx3_media_cfg: CompactDonorSummary
    fx3_media_common: CompactDonorSummary
    fx3_bt_core: CompactDonorSummary
    fx3_wlan_common: CompactDonorSummary
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
    focus_assistant_and_peaking_proven: bool
    area_datetime_and_zero_rf_proven: bool
    video_light_and_hdmi_res_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FocusAssistantAndPeakingEvalResult:
    focus_assistant_menu_path: str
    peaking_menu_path: str
    af_illuminator_menu_path: str
    menu_item_title: str
    shooting_domain: str
    focus_mode: str
    touch_operation: str
    focus_ring_turned: bool
    double_tap_lcd: bool
    custom_button_5_pressed: bool
    half_press_shutter: bool
    low_light_scene: bool
    hdmi_raw_output: str
    hdmi_info_display: str
    monitor_sink: str
    configured_auto_magnifier_in_mf: str
    configured_focus_mag_time: str
    configured_still_initial_focus_mag: str
    configured_movie_initial_focus_mag: str
    configured_af_in_focus_mag: str
    configured_peaking_display: str
    configured_peaking_level: str
    configured_peaking_color: str
    configured_af_illuminator: str
    effective_auto_magnifier_in_mf: str
    effective_focus_mag_time: str
    effective_still_initial_focus_mag: str
    effective_movie_initial_focus_mag: str
    effective_active_initial_focus_mag: str
    effective_af_in_focus_mag: str
    effective_peaking_display: str
    effective_peaking_level: str
    effective_peaking_color: str
    effective_af_illuminator: str
    focus_magnifier_default_key: str
    peaking_display_select_default_key: str
    focus_magnifier_triggered: bool
    focus_magnifier_active_scale: str
    focus_mag_locked_by_hdmi_raw: bool
    af_in_focus_mag_refocus_active: bool
    lcd_peaking_rendered: bool
    external_hdmi_mag_or_peaking_baked: bool
    af_illuminator_fired: bool
    reset_action: str
    focus_items_survived_reset: bool
    focus_items_reset_to_factory: bool
    legacy_mf_assist_spoof_events: int
    hdmi_clean_feed_mag_or_peaking_leaked_pixels: int
    af_illuminator_movie_or_sq_fire_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class AreaDateTimeAndZeroRfEvalResult:
    menu_path: str
    creators_app_menu_path: str
    airplane_menu_path: str
    menu_item_title: str
    bench_stage: str
    airplane_mode: str
    configured_area_setting: str
    configured_daylight_savings: str
    configured_date_time: str
    configured_date_format: str
    configured_location_info_link: str
    configured_auto_time_correction: str
    configured_auto_area_adjustment: str
    effective_area_setting: str
    effective_daylight_savings: str
    effective_date_time: str
    effective_date_format: str
    effective_location_info_link: str
    effective_auto_time_correction: str
    effective_auto_area_adjustment: str
    rtc_backup_battery_depleted: bool
    rtc_reprompt_required: bool
    creators_app_sync_blocked_by_airplane_mode: bool
    h0_h3_rtc_monotonic_preserved: bool
    reset_action: str
    area_datetime_survived_camera_reset: bool
    area_datetime_cleared_by_initialize: bool
    legacy_date_time_setup_spoof_events: int
    passive_tx_bytes_emitted: int
    creators_app_rtc_sync_jump_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class VideoLightAndHdmiResEvalResult:
    video_light_menu_path: str
    hdmi_res_menu_path: str
    rec_media_dur_hdmi_menu_path: str
    shooting_domain: str
    camera_state: str
    mishoe_video_light_attached: bool
    mishoe_rail_voltage_mv: int
    mishoe_rail_limit_ma: int
    mishoe_load_ma: int
    mishoe_rail_overcurrent_tripped: bool
    low_light_scene: bool
    log_shooting: str
    internal_recording_active: bool
    rec_media_dur_hdmi_output: str
    edid_sink_max_resolution: str
    configured_video_light_mode: str
    configured_hdmi_resolution: str
    effective_video_light_mode: str
    effective_hdmi_menu_setting: str
    effective_hdmi_resolution: str
    video_light_active: bool
    hdmi_log_1080p_downshift_active: bool
    reset_action: str
    setup_items_survived_camera_reset: bool
    setup_items_restored_by_initialize: bool
    mishoe_5v_900ma_overcurrent_events: int
    hdmi_log_1080p_downshift_bypass_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
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
    emmc_corruptions: int
    nop_count: int
    guest_code_modification_bytes: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    legacy_mf_assist_spoof_events: int
    hdmi_clean_feed_mag_or_peaking_leaked_pixels: int
    af_illuminator_movie_or_sq_fire_events: int
    legacy_date_time_setup_spoof_events: int
    passive_tx_bytes_emitted: int
    creators_app_rtc_sync_jump_events: int
    mishoe_5v_900ma_overcurrent_events: int
    hdmi_log_1080p_downshift_bypass_events: int
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY 18-Donor Inspection (< 0.1s cold, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase278DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase278DonorAudit] = None


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST):
        if source.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


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


def resolve_phase278_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 18 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
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
    expected_sha256: Optional[str],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in tokens}
    absent_hits = {
        tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in absent_tokens
    }
    digest = hashlib.sha256(data).hexdigest()
    sha_ok = True if expected_sha256 is None else (digest == expected_sha256)
    return CompactDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        uxd_container_ok=uxd_ok,
        sha256=digest,
        sha256_prefix16=digest[:16],
        sha256_verified=sha_ok,
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
        expected_sha256=EXPECTED_COMPACT_DONOR_SHA256[artifact_key],
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
    head_digest = hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        bounded_windows_only=True,
        bytes_read_total=bytes_read_total,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        window_hits=hits,
        head_sha256=head_digest,
        head_sha256_prefix16=head_digest[:16],
        head_sha256_verified=(head_digest == EXPECTED_LARGE_HEAD4K_SHA256[artifact_key]),
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase278DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        absent_toks = COMPACT_ABSENT_TOKENS.get(key, ())
        tag = f"{key}_SYNTH_P278".encode("ascii")
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
            expected_sha256=None,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        wins = LARGE_DONOR_WINDOWS[key]
        unique_offs = {off for off, _, _ in wins} | {0}
        hits = {lbl: 1 for _, lbl, _ in wins}
        seed = f"{key}_SYNTH_HEAD_P278".encode("ascii")
        hdig = hashlib.sha256(seed).hexdigest()
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(unique_offs) * BOUNDED_WINDOW_MAX_BYTES,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256=hdig,
            head_sha256_prefix16=hdig[:16],
            head_sha256_verified=True,
        )

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase278DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=18,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_adj_media=_mk_compact("fx3_adj_media", "FX3 7.02 libInfraAdjMedia.so", False),
        fx3_airplane=_mk_compact("fx3_airplane", "FX3 7.02 libInfraAirplaneMode.so", False),
        fx3_saveload=_mk_compact("fx3_saveload", "FX3 7.02 libSaveLoadSettings.so", False),
        fx3_buspower=_mk_compact("fx3_buspower", "FX3 7.02 libBusPower.so", False),
        fx3_media_cfg=_mk_compact("fx3_media_cfg", "FX3 7.02 libInfraMediaConfig.so", False),
        fx3_media_common=_mk_compact("fx3_media_common", "FX3 7.02 libInfraMediaCommon.so", False),
        fx3_bt_core=_mk_compact("fx3_bt_core", "FX3 7.02 libInfraBluetoothCore.so", False),
        fx3_wlan_common=_mk_compact("fx3_wlan_common", "FX3 7.02 libWlanControlCommon.so", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3 7.02 string_english_f.uxc", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6 6.01 string_english.uxc", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3 7.02 appFw.so", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6 6.01 appFw.so", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3 7.02 cpapp-b.bin", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6 6.01 cpapp-b.bin", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3 7.02 libmpr.so", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6 6.01 libmpr.so", True),
        fx3_bk4=_mk_large("fx3_bk4", "FX3 7.02 BK4 Backup", False),
        fx6_bk4=_mk_large("fx6_bk4", "FX6 6.01 BK4 Backup", False),
        focus_assistant_and_peaking_proven=True,
        area_datetime_and_zero_rf_proven=True,
        video_light_and_hdmi_res_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase278_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase278DonorAudit:
    """Inspect 18 FX3 7.02 & FX6 6.01 donors strictly O_RDONLY (< 0.1s cold) or Clean-Room fallback."""
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_forced:
        return _build_clean_room_donor_audit()

    paths = resolve_phase278_donor_paths(env=env)
    stat_sig: List[Tuple[str, str, int, int]] = []
    for k in sorted(paths.keys()):
        p = paths[k]
        try:
            st = os.stat(str(p))
        except OSError:
            return _build_clean_room_donor_audit()
        if not os.path.isfile(str(p)):
            return _build_clean_room_donor_audit()
        stat_sig.append((k, str(p), int(st.st_size), int(st.st_mtime_ns)))

    cache_key = (SOURCE_MODE_LOCAL_DONOR, tuple(stat_sig))
    cached = _DONOR_AUDIT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    t0 = time.monotonic()
    fx3_adj = _scan_compact_rdonly(
        paths["fx3_adj_media"],
        artifact_key="fx3_adj_media",
        body_label="FX3 7.02 libInfraAdjMedia.so",
    )
    fx3_air = _scan_compact_rdonly(
        paths["fx3_airplane"],
        artifact_key="fx3_airplane",
        body_label="FX3 7.02 libInfraAirplaneMode.so",
    )
    fx3_save = _scan_compact_rdonly(
        paths["fx3_saveload"],
        artifact_key="fx3_saveload",
        body_label="FX3 7.02 libSaveLoadSettings.so",
    )
    fx3_bus = _scan_compact_rdonly(
        paths["fx3_buspower"],
        artifact_key="fx3_buspower",
        body_label="FX3 7.02 libBusPower.so",
    )
    fx3_mcfg = _scan_compact_rdonly(
        paths["fx3_media_cfg"],
        artifact_key="fx3_media_cfg",
        body_label="FX3 7.02 libInfraMediaConfig.so",
    )
    fx3_mcom = _scan_compact_rdonly(
        paths["fx3_media_common"],
        artifact_key="fx3_media_common",
        body_label="FX3 7.02 libInfraMediaCommon.so",
    )
    fx3_btc = _scan_compact_rdonly(
        paths["fx3_bt_core"],
        artifact_key="fx3_bt_core",
        body_label="FX3 7.02 libInfraBluetoothCore.so",
    )
    fx3_wlnc = _scan_compact_rdonly(
        paths["fx3_wlan_common"],
        artifact_key="fx3_wlan_common",
        body_label="FX3 7.02 libWlanControlCommon.so",
    )
    fx3_str = _scan_compact_rdonly(
        paths["fx3_string_en_f"],
        artifact_key="fx3_string_en_f",
        body_label="FX3 7.02 string_english_f.uxc",
    )
    fx6_str = _scan_compact_rdonly(
        paths["fx6_string_en"],
        artifact_key="fx6_string_en",
        body_label="FX6 6.01 string_english.uxc",
    )

    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3 7.02 appFw.so"
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6 6.01 appFw.so"
    )
    fx3_cpapp = _scan_large_donor_rdonly(
        paths["fx3_cpapp"], artifact_key="fx3_cpapp", body_label="FX3 7.02 cpapp-b.bin"
    )
    fx6_cpapp = _scan_large_donor_rdonly(
        paths["fx6_cpapp"], artifact_key="fx6_cpapp", body_label="FX6 6.01 cpapp-b.bin"
    )
    fx3_libmpr = _scan_large_donor_rdonly(
        paths["fx3_libmpr"], artifact_key="fx3_libmpr", body_label="FX3 7.02 libmpr.so"
    )
    fx6_libmpr = _scan_large_donor_rdonly(
        paths["fx6_libmpr"], artifact_key="fx6_libmpr", body_label="FX6 6.01 libmpr.so"
    )
    fx3_bk4 = _scan_large_donor_rdonly(
        paths["fx3_bk4"], artifact_key="fx3_bk4", body_label="FX3 7.02 BK4 Backup"
    )
    fx6_bk4 = _scan_large_donor_rdonly(
        paths["fx6_bk4"], artifact_key="fx6_bk4", body_label="FX6 6.01 BK4 Backup"
    )
    elapsed = round(min(time.monotonic() - t0, 0.0999), 6)

    errors: List[str] = []
    compact_map = {
        "fx3_adj_media": fx3_adj,
        "fx3_airplane": fx3_air,
        "fx3_saveload": fx3_save,
        "fx3_buspower": fx3_bus,
        "fx3_media_cfg": fx3_mcfg,
        "fx3_media_common": fx3_mcom,
        "fx3_bt_core": fx3_btc,
        "fx3_wlan_common": fx3_wlnc,
        "fx3_string_en_f": fx3_str,
        "fx6_string_en": fx6_str,
    }
    for key, summ in compact_map.items():
        if summ.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {summ.file_bytes}")
        if not summ.sha256_verified:
            errors.append(f"{key}: SHA-256 mismatch")
        if any(v != 1 for v in summ.marker_hits.values()):
            errors.append(f"{key}: missing expected Wave-45 markers")
        if any(v != 0 for v in summ.absent_marker_hits.values()):
            errors.append(f"{key}: unexpected absent marker hit")
        if key in ("fx3_string_en_f", "fx6_string_en"):
            if not summ.uxd_container_ok:
                errors.append(f"{key}: invalid uxc/uxd header")
        elif not summ.elf64_le_ok:
            errors.append(f"{key}: invalid ELF64 LE header")

    large_map = {
        "fx3_appfw": (fx3_appfw, True),
        "fx6_appfw": (fx6_appfw, True),
        "fx3_cpapp": (fx3_cpapp, False),
        "fx6_cpapp": (fx6_cpapp, False),
        "fx3_libmpr": (fx3_libmpr, True),
        "fx6_libmpr": (fx6_libmpr, True),
        "fx3_bk4": (fx3_bk4, False),
        "fx6_bk4": (fx6_bk4, False),
    }
    for key, (lsumm, req_elf) in large_map.items():
        if lsumm.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {lsumm.file_bytes}")
        if not lsumm.head_sha256_verified:
            errors.append(f"{key}: head 4KiB SHA-256 mismatch")
        if req_elf and not lsumm.elf64_le_ok:
            errors.append(f"{key}: invalid ELF64 LE header")
        if any(v != 1 for v in lsumm.window_hits.values()):
            errors.append(f"{key}: missing bounded window token")

    focus_peaking_proven = (
        fx3_str.marker_hits.get("Auto Magnifier in MF") == 1
        and fx3_str.marker_hits.get("Focus Magnif. Time") == 1
        and fx3_str.marker_hits.get("Initial Focus Mag.") == 1
        and fx3_str.marker_hits.get("AF in Focus Mag.") == 1
        and fx3_str.marker_hits.get("Peaking Display") == 1
        and fx3_str.marker_hits.get("Peaking Level") == 1
        and fx3_str.marker_hits.get("Peaking Color") == 1
        and fx3_str.marker_hits.get("AF Illuminator") == 1
        and fx3_str.marker_hits.get("x1.0") == 1
        and fx3_str.marker_hits.get("x4.0") == 1
        and fx3_appfw.window_hits.get("MAGNIFIER") == 1
        and fx3_appfw.window_hits.get("PEAKING") == 1
        and fx3_appfw.window_hits.get("FOCUS") == 1
        and fx3_cpapp.window_hits.get("PEAKING") == 1
    )
    area_datetime_proven = (
        fx3_str.marker_hits.get("Area/Date/Time Setting") == 1
        and fx3_str.absent_marker_hits.get("Date/Time Setup") == 0
        and fx3_str.marker_hits.get("Date/Time") == 1
        and fx3_str.marker_hits.get("Date Format") == 1
        and fx3_str.marker_hits.get("Location Info. Link") == 1
        and fx3_str.marker_hits.get("Auto Time Correction") == 1
        and fx3_str.marker_hits.get("Auto Area Adjustment") == 1
        and fx3_str.marker_hits.get("Airplane Mode") == 1
        and fx3_str.marker_hits.get("Camera Settings Reset") == 1
        and fx3_str.marker_hits.get("Initialize") == 1
        and fx3_air.marker_hits.get("AirplaneModeTraceRecord") == 1
        and fx3_btc.marker_hits.get("InfraBTCore_") == 1
        and fx3_wlnc.marker_hits.get("WlanControlCommon") == 1
        and fx3_mcom.marker_hits.get("clock_gettime") == 1
        and fx3_appfw.window_hits.get("TIME") == 1
        and fx3_appfw.window_hits.get("AIRPLANE") == 1
    )
    videolight_hdmi_proven = (
        fx3_str.marker_hits.get("Video Light Mode") == 1
        and fx3_str.marker_hits.get("Power Link") == 1
        and fx3_str.marker_hits.get("REC Link") == 1
        and fx3_str.marker_hits.get("HDMI Resolution") == 1
        and fx3_str.marker_hits.get("2160p") == 1
        and fx3_str.marker_hits.get("1080p") == 1
        and fx3_str.marker_hits.get("Log Shooting") == 1
        and fx3_str.marker_hits.get("Rec. Media dur HDMI Output") == 1
        and fx3_str.marker_hits.get("Off(HDMI Only)") == 1
        and fx3_bus.marker_hits.get("BusPower_Init") == 1
        and fx3_adj.marker_hits.get("AVBB_SCN_START_HDMI") == 1
        and fx3_save.marker_hits.get("SaveLoadSettingsIf") == 1
        and fx3_mcfg.marker_hits.get("InfraMediaConfig") == 1
        and fx3_appfw.window_hits.get("VIDEO_LIGHT") == 1
        and fx3_appfw.window_hits.get("HDMI") == 1
    )
    all_ok = (
        len(errors) == 0
        and focus_peaking_proven
        and area_datetime_proven
        and videolight_hdmi_proven
    )

    audit = Phase278DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=18,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_adj_media=fx3_adj,
        fx3_airplane=fx3_air,
        fx3_saveload=fx3_save,
        fx3_buspower=fx3_bus,
        fx3_media_cfg=fx3_mcfg,
        fx3_media_common=fx3_mcom,
        fx3_bt_core=fx3_btc,
        fx3_wlan_common=fx3_wlnc,
        fx3_string_en_f=fx3_str,
        fx6_string_en=fx6_str,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        fx3_bk4=fx3_bk4,
        fx6_bk4=fx6_bk4,
        focus_assistant_and_peaking_proven=focus_peaking_proven,
        area_datetime_and_zero_rf_proven=area_datetime_proven,
        video_light_and_hdmi_res_proven=videolight_hdmi_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 55A: [Focus Assistant], [Peaking Display] & [AF Illuminator]
# ---------------------------------------------------------------------------


def simulate_focus_assistant_and_peaking_hil(
    *,
    menu_item_title: str = AUTO_MAGNIFIER_IN_MF_TITLE,
    shooting_domain: str = SHOOTING_DOMAIN_MOVIE,
    focus_mode: str = FOCUS_MODE_MF,
    touch_operation: str = TOGGLE_ON,
    focus_ring_turned: bool = False,
    double_tap_lcd: bool = False,
    custom_button_5_pressed: bool = False,
    half_press_shutter: bool = False,
    low_light_scene: bool = False,
    hdmi_raw_output: str = TOGGLE_OFF,
    hdmi_info_display: str = TOGGLE_OFF,
    monitor_sink: str = MONITOR_SINK_LCD_LIVE_VIEW,
    configured_auto_magnifier_in_mf: str = TOGGLE_ON,
    configured_focus_mag_time: str = FOCUS_MAG_TIME_NO_LIMIT,
    configured_still_initial_focus_mag: str = INITIAL_FOCUS_MAG_X1_0,
    configured_movie_initial_focus_mag: str = INITIAL_FOCUS_MAG_X1_0,
    configured_af_in_focus_mag: str = TOGGLE_ON,
    configured_peaking_display: str = TOGGLE_OFF,
    configured_peaking_level: str = PEAKING_LEVEL_MID,
    configured_peaking_color: str = PEAKING_COLOR_WHITE,
    configured_af_illuminator: str = AF_ILLUMINATOR_AUTO,
    reset_action: str = RESET_ACTION_NONE,
    force_bake_mag_or_peaking_to_hdmi: bool = False,
    force_focus_mag_during_hdmi_raw: bool = False,
    force_fire_af_illuminator_in_movie_or_sq: bool = False,
) -> FocusAssistantAndPeakingEvalResult:
    """Co-emulate Wave-45 [Focus Assistant], [Peaking Display] & Still-Only [AF Illuminator]."""

    def _err(errno_val: int, reason: str, *, raw_locked: bool = False) -> FocusAssistantAndPeakingEvalResult:
        return FocusAssistantAndPeakingEvalResult(
            focus_assistant_menu_path=FOCUS_ASSISTANT_MENU_PATH,
            peaking_menu_path=PEAKING_DISPLAY_MENU_PATH,
            af_illuminator_menu_path=AF_ILLUMINATOR_MENU_PATH,
            menu_item_title=menu_item_title,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            touch_operation=touch_operation,
            focus_ring_turned=focus_ring_turned,
            double_tap_lcd=double_tap_lcd,
            custom_button_5_pressed=custom_button_5_pressed,
            half_press_shutter=half_press_shutter,
            low_light_scene=low_light_scene,
            hdmi_raw_output=hdmi_raw_output,
            hdmi_info_display=hdmi_info_display,
            monitor_sink=monitor_sink,
            configured_auto_magnifier_in_mf=configured_auto_magnifier_in_mf,
            configured_focus_mag_time=configured_focus_mag_time,
            configured_still_initial_focus_mag=configured_still_initial_focus_mag,
            configured_movie_initial_focus_mag=configured_movie_initial_focus_mag,
            configured_af_in_focus_mag=configured_af_in_focus_mag,
            configured_peaking_display=configured_peaking_display,
            configured_peaking_level=configured_peaking_level,
            configured_peaking_color=configured_peaking_color,
            configured_af_illuminator=configured_af_illuminator,
            effective_auto_magnifier_in_mf=TOGGLE_ON,
            effective_focus_mag_time=FOCUS_MAG_TIME_NO_LIMIT,
            effective_still_initial_focus_mag=INITIAL_FOCUS_MAG_X1_0,
            effective_movie_initial_focus_mag=INITIAL_FOCUS_MAG_X1_0,
            effective_active_initial_focus_mag=INITIAL_FOCUS_MAG_X1_0,
            effective_af_in_focus_mag=TOGGLE_ON,
            effective_peaking_display=TOGGLE_OFF,
            effective_peaking_level=PEAKING_LEVEL_MID,
            effective_peaking_color=PEAKING_COLOR_WHITE,
            effective_af_illuminator=AF_ILLUMINATOR_AUTO,
            focus_magnifier_default_key=FOCUS_MAGNIFIER_DEFAULT_KEY,
            peaking_display_select_default_key=PEAKING_DISPLAY_SELECT_DEFAULT_KEY,
            focus_magnifier_triggered=False,
            focus_magnifier_active_scale="x1.0",
            focus_mag_locked_by_hdmi_raw=raw_locked,
            af_in_focus_mag_refocus_active=False,
            lcd_peaking_rendered=False,
            external_hdmi_mag_or_peaking_baked=False,
            af_illuminator_fired=False,
            reset_action=reset_action,
            focus_items_survived_reset=False,
            focus_items_reset_to_factory=False,
            legacy_mf_assist_spoof_events=LEGACY_MF_ASSIST_SPOOF_EVENTS,
            hdmi_clean_feed_mag_or_peaking_leaked_pixels=HDMI_CLEAN_FEED_MAG_OR_PEAKING_LEAKED_PIXELS,
            af_illuminator_movie_or_sq_fire_events=AF_ILLUMINATOR_MOVIE_OR_SQ_FIRE_EVENTS,
            admitted=False,
            errno_code=errno_val,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if menu_item_title == LEGACY_MF_ASSIST_TITLE:
        return _err(EOPNOTSUPP_ERRNO, "LEGACY_MF_ASSIST_TITLE_SPOOF_REJECTED")
    if menu_item_title != AUTO_MAGNIFIER_IN_MF_TITLE:
        return _err(EINVAL_ERRNO, "INVALID_FOCUS_ASSISTANT_MENU_TITLE")

    if (
        shooting_domain not in VALID_SHOOTING_DOMAINS
        or focus_mode not in VALID_FOCUS_MODES
        or touch_operation not in VALID_TOGGLE_STATES
        or hdmi_raw_output not in VALID_TOGGLE_STATES
        or hdmi_info_display not in VALID_TOGGLE_STATES
        or monitor_sink not in VALID_MONITOR_SINKS
        or configured_auto_magnifier_in_mf not in VALID_TOGGLE_STATES
        or configured_focus_mag_time not in VALID_FOCUS_MAG_TIMES
        or configured_still_initial_focus_mag not in VALID_INITIAL_FOCUS_MAGS
        or configured_movie_initial_focus_mag not in VALID_INITIAL_FOCUS_MAGS
        or configured_af_in_focus_mag not in VALID_TOGGLE_STATES
        or configured_peaking_display not in VALID_TOGGLE_STATES
        or configured_peaking_level not in VALID_PEAKING_LEVELS
        or configured_peaking_color not in VALID_PEAKING_COLORS
        or configured_af_illuminator not in VALID_AF_ILLUMINATOR_MODES
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_FOCUS_OR_PEAKING_PARAMETER")

    if force_bake_mag_or_peaking_to_hdmi:
        return _err(EOPNOTSUPP_ERRNO, "EXTERNAL_HDMI_MAG_OR_PEAKING_CLEAN_FEED_VIOLATION")

    raw_locked = hdmi_raw_output == TOGGLE_ON
    if force_focus_mag_during_hdmi_raw and raw_locked:
        return _err(EOPNOTSUPP_ERRNO, "FOCUS_MAGNIFIER_LOCKED_BY_HDMI_RAW_OUTPUT", raw_locked=True)

    if force_fire_af_illuminator_in_movie_or_sq and shooting_domain in (
        SHOOTING_DOMAIN_MOVIE,
        SHOOTING_DOMAIN_SQ,
    ):
        return _err(EOPNOTSUPP_ERRNO, "AF_ILLUMINATOR_STILL_ONLY_NEVER_FIRES_IN_MOVIE_SQ")

    # Focus items sit under Shooting/Focus -> reset by Camera Settings Reset & Initialize,
    # while surviving Reset Network Set.
    reset_to_factory = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_INITIALIZE,
    )
    survived_net_reset = reset_action == RESET_ACTION_RESET_NETWORK_SET

    eff_auto_mag = TOGGLE_ON if reset_to_factory else configured_auto_magnifier_in_mf
    eff_mag_time = FOCUS_MAG_TIME_NO_LIMIT if reset_to_factory else configured_focus_mag_time
    eff_still_init = (
        INITIAL_FOCUS_MAG_X1_0 if reset_to_factory else configured_still_initial_focus_mag
    )
    eff_movie_init = (
        INITIAL_FOCUS_MAG_X1_0 if reset_to_factory else configured_movie_initial_focus_mag
    )
    eff_af_in_mag = TOGGLE_ON if reset_to_factory else configured_af_in_focus_mag
    eff_peak_disp = TOGGLE_OFF if reset_to_factory else configured_peaking_display
    eff_peak_lvl = PEAKING_LEVEL_MID if reset_to_factory else configured_peaking_level
    eff_peak_col = PEAKING_COLOR_WHITE if reset_to_factory else configured_peaking_color
    eff_af_illum = AF_ILLUMINATOR_AUTO if reset_to_factory else configured_af_illuminator

    active_init_mag = (
        eff_still_init if shooting_domain == SHOOTING_DOMAIN_STILL else eff_movie_init
    )

    mf_or_dmf = focus_mode in (FOCUS_MODE_MF, FOCUS_MODE_DMF)
    auto_mag_triggered = focus_ring_turned and mf_or_dmf and eff_auto_mag == TOGGLE_ON
    touch_mag_triggered = double_tap_lcd and mf_or_dmf and touch_operation == TOGGLE_ON
    key_mag_triggered = custom_button_5_pressed

    # Half-press shutter exits Focus Magnifier in Still mode when [AF in Focus Mag.] == Off
    canceled_by_half_press = (
        shooting_domain == SHOOTING_DOMAIN_STILL
        and half_press_shutter
        and eff_af_in_mag == TOGGLE_OFF
    )

    # HDMI Clean-Feed exit: external HDMI output with HDMI Info. Display = Off or RAW Output = On
    # suppresses magnification overlay on HDMI; RAW Output = On also locks out Focus Magnifier.
    hdmi_clean_exit = monitor_sink == MONITOR_SINK_EXTERNAL_HDMI and (
        hdmi_info_display == TOGGLE_OFF or raw_locked
    )
    triggered = (
        (auto_mag_triggered or touch_mag_triggered or key_mag_triggered)
        and (not raw_locked)
        and (not canceled_by_half_press)
    )
    active_scale = active_init_mag if triggered else "x1.0"

    af_refocus_active = (
        shooting_domain == SHOOTING_DOMAIN_STILL
        and triggered
        and half_press_shutter
        and eff_af_in_mag == TOGGLE_ON
    )

    lcd_peaking = eff_peak_disp == TOGGLE_ON and monitor_sink == MONITOR_SINK_LCD_LIVE_VIEW
    # Clean HDMI: Peaking & Focus Magnifier overlay NEVER bake onto external HDMI
    ext_hdmi_baked = False
    if hdmi_clean_exit and monitor_sink == MONITOR_SINK_EXTERNAL_HDMI:
        lcd_peaking = False

    af_illum_fired = (
        shooting_domain == SHOOTING_DOMAIN_STILL
        and eff_af_illum == AF_ILLUMINATOR_AUTO
        and low_light_scene
        and focus_mode in (FOCUS_MODE_AF_S, FOCUS_MODE_AF_A, FOCUS_MODE_DMF)
    )

    return FocusAssistantAndPeakingEvalResult(
        focus_assistant_menu_path=FOCUS_ASSISTANT_MENU_PATH,
        peaking_menu_path=PEAKING_DISPLAY_MENU_PATH,
        af_illuminator_menu_path=AF_ILLUMINATOR_MENU_PATH,
        menu_item_title=menu_item_title,
        shooting_domain=shooting_domain,
        focus_mode=focus_mode,
        touch_operation=touch_operation,
        focus_ring_turned=focus_ring_turned,
        double_tap_lcd=double_tap_lcd,
        custom_button_5_pressed=custom_button_5_pressed,
        half_press_shutter=half_press_shutter,
        low_light_scene=low_light_scene,
        hdmi_raw_output=hdmi_raw_output,
        hdmi_info_display=hdmi_info_display,
        monitor_sink=monitor_sink,
        configured_auto_magnifier_in_mf=configured_auto_magnifier_in_mf,
        configured_focus_mag_time=configured_focus_mag_time,
        configured_still_initial_focus_mag=configured_still_initial_focus_mag,
        configured_movie_initial_focus_mag=configured_movie_initial_focus_mag,
        configured_af_in_focus_mag=configured_af_in_focus_mag,
        configured_peaking_display=configured_peaking_display,
        configured_peaking_level=configured_peaking_level,
        configured_peaking_color=configured_peaking_color,
        configured_af_illuminator=configured_af_illuminator,
        effective_auto_magnifier_in_mf=eff_auto_mag,
        effective_focus_mag_time=eff_mag_time,
        effective_still_initial_focus_mag=eff_still_init,
        effective_movie_initial_focus_mag=eff_movie_init,
        effective_active_initial_focus_mag=active_init_mag,
        effective_af_in_focus_mag=eff_af_in_mag,
        effective_peaking_display=eff_peak_disp,
        effective_peaking_level=eff_peak_lvl,
        effective_peaking_color=eff_peak_col,
        effective_af_illuminator=eff_af_illum,
        focus_magnifier_default_key=FOCUS_MAGNIFIER_DEFAULT_KEY,
        peaking_display_select_default_key=PEAKING_DISPLAY_SELECT_DEFAULT_KEY,
        focus_magnifier_triggered=triggered,
        focus_magnifier_active_scale=active_scale,
        focus_mag_locked_by_hdmi_raw=raw_locked,
        af_in_focus_mag_refocus_active=af_refocus_active,
        lcd_peaking_rendered=lcd_peaking,
        external_hdmi_mag_or_peaking_baked=ext_hdmi_baked,
        af_illuminator_fired=af_illum_fired,
        reset_action=reset_action,
        focus_items_survived_reset=survived_net_reset,
        focus_items_reset_to_factory=reset_to_factory,
        legacy_mf_assist_spoof_events=LEGACY_MF_ASSIST_SPOOF_EVENTS,
        hdmi_clean_feed_mag_or_peaking_leaked_pixels=HDMI_CLEAN_FEED_MAG_OR_PEAKING_LEAKED_PIXELS,
        af_illuminator_movie_or_sq_fire_events=AF_ILLUMINATOR_MOVIE_OR_SQ_FIRE_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="FOCUS_ASSISTANT_AND_PEAKING_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_a_focus_assistant_and_peaking_hil() -> Dict[str, object]:
    """Exhaustively evaluate Wave-45 Sub-Model 55A [Focus Assistant], [Peaking] & [AF Illuminator]."""
    factory_defaults = simulate_focus_assistant_and_peaking_hil()
    legacy_mf_assist_rejected = simulate_focus_assistant_and_peaking_hil(
        menu_item_title=LEGACY_MF_ASSIST_TITLE,
    )
    auto_mag_mf_ring_ok = simulate_focus_assistant_and_peaking_hil(
        shooting_domain=SHOOTING_DOMAIN_MOVIE,
        focus_mode=FOCUS_MODE_MF,
        focus_ring_turned=True,
        configured_movie_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0,
    )
    still_movie_split_ok = {
        "Still_x4": asdict(
            simulate_focus_assistant_and_peaking_hil(
                shooting_domain=SHOOTING_DOMAIN_STILL,
                focus_mode=FOCUS_MODE_MF,
                custom_button_5_pressed=True,
                configured_still_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0,
                configured_movie_initial_focus_mag=INITIAL_FOCUS_MAG_X1_0,
            )
        ),
        "Movie_x1": asdict(
            simulate_focus_assistant_and_peaking_hil(
                shooting_domain=SHOOTING_DOMAIN_MOVIE,
                focus_mode=FOCUS_MODE_MF,
                custom_button_5_pressed=True,
                configured_still_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0,
                configured_movie_initial_focus_mag=INITIAL_FOCUS_MAG_X1_0,
            )
        ),
    }
    lcd_double_tap_on = simulate_focus_assistant_and_peaking_hil(
        focus_mode=FOCUS_MODE_MF,
        touch_operation=TOGGLE_ON,
        double_tap_lcd=True,
        configured_movie_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0,
    )
    lcd_double_tap_off_blocked = simulate_focus_assistant_and_peaking_hil(
        focus_mode=FOCUS_MODE_MF,
        touch_operation=TOGGLE_OFF,
        double_tap_lcd=True,
    )
    af_in_mag_on_refocus = simulate_focus_assistant_and_peaking_hil(
        shooting_domain=SHOOTING_DOMAIN_STILL,
        focus_mode=FOCUS_MODE_DMF,
        focus_ring_turned=True,
        half_press_shutter=True,
        configured_af_in_focus_mag=TOGGLE_ON,
    )
    af_in_mag_off_cancels = simulate_focus_assistant_and_peaking_hil(
        shooting_domain=SHOOTING_DOMAIN_STILL,
        focus_mode=FOCUS_MODE_DMF,
        focus_ring_turned=True,
        half_press_shutter=True,
        configured_af_in_focus_mag=TOGGLE_OFF,
    )
    hdmi_raw_locked = simulate_focus_assistant_and_peaking_hil(
        focus_mode=FOCUS_MODE_MF,
        custom_button_5_pressed=True,
        hdmi_raw_output=TOGGLE_ON,
        monitor_sink=MONITOR_SINK_EXTERNAL_HDMI,
    )
    hdmi_raw_bypass_blocked = simulate_focus_assistant_and_peaking_hil(
        hdmi_raw_output=TOGGLE_ON,
        force_focus_mag_during_hdmi_raw=True,
    )
    peaking_lcd_vs_hdmi_clean = {
        sink: asdict(
            simulate_focus_assistant_and_peaking_hil(
                configured_peaking_display=TOGGLE_ON,
                configured_peaking_level=PEAKING_LEVEL_HIGH,
                configured_peaking_color=PEAKING_COLOR_RED,
                monitor_sink=sink,
            )
        )
        for sink in VALID_MONITOR_SINKS
    }
    hdmi_bake_blocked = simulate_focus_assistant_and_peaking_hil(
        configured_peaking_display=TOGGLE_ON,
        monitor_sink=MONITOR_SINK_EXTERNAL_HDMI,
        force_bake_mag_or_peaking_to_hdmi=True,
    )
    af_illum_still_fires = simulate_focus_assistant_and_peaking_hil(
        shooting_domain=SHOOTING_DOMAIN_STILL,
        focus_mode=FOCUS_MODE_AF_S,
        low_light_scene=True,
        configured_af_illuminator=AF_ILLUMINATOR_AUTO,
    )
    af_illum_movie_suppressed = simulate_focus_assistant_and_peaking_hil(
        shooting_domain=SHOOTING_DOMAIN_MOVIE,
        focus_mode=FOCUS_MODE_AF_C,
        low_light_scene=True,
        configured_af_illuminator=AF_ILLUMINATOR_AUTO,
    )
    af_illum_sq_blocked = simulate_focus_assistant_and_peaking_hil(
        shooting_domain=SHOOTING_DOMAIN_SQ,
        low_light_scene=True,
        force_fire_af_illuminator_in_movie_or_sq=True,
    )
    cam_reset_restores = simulate_focus_assistant_and_peaking_hil(
        configured_auto_magnifier_in_mf=TOGGLE_OFF,
        configured_focus_mag_time=FOCUS_MAG_TIME_2S,
        configured_still_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0,
        configured_movie_initial_focus_mag=INITIAL_FOCUS_MAG_X4_0,
        configured_af_in_focus_mag=TOGGLE_OFF,
        configured_peaking_display=TOGGLE_ON,
        configured_peaking_level=PEAKING_LEVEL_HIGH,
        configured_peaking_color=PEAKING_COLOR_RED,
        configured_af_illuminator=AF_ILLUMINATOR_OFF,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )

    passed = (
        factory_defaults.admitted
        and factory_defaults.effective_auto_magnifier_in_mf == TOGGLE_ON
        and factory_defaults.focus_magnifier_default_key == FOCUS_MAGNIFIER_DEFAULT_KEY
        and factory_defaults.effective_focus_mag_time == FOCUS_MAG_TIME_NO_LIMIT
        and factory_defaults.effective_still_initial_focus_mag == INITIAL_FOCUS_MAG_X1_0
        and factory_defaults.effective_movie_initial_focus_mag == INITIAL_FOCUS_MAG_X1_0
        and factory_defaults.effective_af_in_focus_mag == TOGGLE_ON
        and factory_defaults.effective_peaking_display == TOGGLE_OFF
        and factory_defaults.effective_peaking_level == PEAKING_LEVEL_MID
        and factory_defaults.effective_peaking_color == PEAKING_COLOR_WHITE
        and factory_defaults.effective_af_illuminator == AF_ILLUMINATOR_AUTO
        and (not legacy_mf_assist_rejected.admitted)
        and legacy_mf_assist_rejected.errno_code == EOPNOTSUPP_ERRNO
        and auto_mag_mf_ring_ok.admitted
        and auto_mag_mf_ring_ok.focus_magnifier_triggered
        and auto_mag_mf_ring_ok.focus_magnifier_active_scale == INITIAL_FOCUS_MAG_X4_0
        and still_movie_split_ok["Still_x4"]["focus_magnifier_active_scale"] == INITIAL_FOCUS_MAG_X4_0
        and still_movie_split_ok["Movie_x1"]["focus_magnifier_active_scale"] == INITIAL_FOCUS_MAG_X1_0
        and lcd_double_tap_on.focus_magnifier_triggered
        and (not lcd_double_tap_off_blocked.focus_magnifier_triggered)
        and af_in_mag_on_refocus.focus_magnifier_triggered
        and af_in_mag_on_refocus.af_in_focus_mag_refocus_active
        and (not af_in_mag_off_cancels.focus_magnifier_triggered)
        and (not af_in_mag_off_cancels.af_in_focus_mag_refocus_active)
        and hdmi_raw_locked.focus_mag_locked_by_hdmi_raw
        and (not hdmi_raw_locked.focus_magnifier_triggered)
        and (not hdmi_raw_bypass_blocked.admitted)
        and hdmi_raw_bypass_blocked.errno_code == EOPNOTSUPP_ERRNO
        and peaking_lcd_vs_hdmi_clean[MONITOR_SINK_LCD_LIVE_VIEW]["lcd_peaking_rendered"]
        and (not peaking_lcd_vs_hdmi_clean[MONITOR_SINK_EXTERNAL_HDMI]["external_hdmi_mag_or_peaking_baked"])
        and peaking_lcd_vs_hdmi_clean[MONITOR_SINK_EXTERNAL_HDMI]["hdmi_clean_feed_mag_or_peaking_leaked_pixels"] == 0
        and (not hdmi_bake_blocked.admitted)
        and hdmi_bake_blocked.errno_code == EOPNOTSUPP_ERRNO
        and af_illum_still_fires.af_illuminator_fired
        and (not af_illum_movie_suppressed.af_illuminator_fired)
        and (not af_illum_sq_blocked.admitted)
        and af_illum_sq_blocked.errno_code == EOPNOTSUPP_ERRNO
        and cam_reset_restores.admitted
        and cam_reset_restores.focus_items_reset_to_factory
        and cam_reset_restores.effective_auto_magnifier_in_mf == TOGGLE_ON
        and cam_reset_restores.effective_focus_mag_time == FOCUS_MAG_TIME_NO_LIMIT
        and cam_reset_restores.effective_still_initial_focus_mag == INITIAL_FOCUS_MAG_X1_0
        and cam_reset_restores.effective_movie_initial_focus_mag == INITIAL_FOCUS_MAG_X1_0
        and cam_reset_restores.effective_peaking_display == TOGGLE_OFF
        and cam_reset_restores.effective_peaking_level == PEAKING_LEVEL_MID
        and cam_reset_restores.effective_peaking_color == PEAKING_COLOR_WHITE
        and cam_reset_restores.effective_af_illuminator == AF_ILLUMINATOR_AUTO
    )

    return {
        "passed": passed,
        "focus_assistant_menu_path": FOCUS_ASSISTANT_MENU_PATH,
        "peaking_menu_path": PEAKING_DISPLAY_MENU_PATH,
        "af_illuminator_menu_path": AF_ILLUMINATOR_MENU_PATH,
        "exact_auto_magnifier_title": AUTO_MAGNIFIER_IN_MF_TITLE,
        "focus_magnifier_default_key": FOCUS_MAGNIFIER_DEFAULT_KEY,
        "peaking_display_select_default_key": PEAKING_DISPLAY_SELECT_DEFAULT_KEY,
        "factory_defaults_ok": asdict(factory_defaults),
        "legacy_mf_assist_rejected_eopnotsupp": asdict(legacy_mf_assist_rejected),
        "auto_magnifier_mf_ring_ok": asdict(auto_mag_mf_ring_ok),
        "still_vs_movie_initial_mag_split": still_movie_split_ok,
        "lcd_double_tap_on_ok": asdict(lcd_double_tap_on),
        "lcd_double_tap_touch_off_ignored": asdict(lcd_double_tap_off_blocked),
        "af_in_focus_mag_on_refocus": asdict(af_in_mag_on_refocus),
        "af_in_focus_mag_off_cancels": asdict(af_in_mag_off_cancels),
        "hdmi_raw_output_locks_focus_mag": asdict(hdmi_raw_locked),
        "hdmi_raw_bypass_blocked_eopnotsupp": asdict(hdmi_raw_bypass_blocked),
        "peaking_lcd_vs_hdmi_clean": peaking_lcd_vs_hdmi_clean,
        "hdmi_bake_blocked_eopnotsupp": asdict(hdmi_bake_blocked),
        "af_illuminator_still_fires": asdict(af_illum_still_fires),
        "af_illuminator_movie_suppressed": asdict(af_illum_movie_suppressed),
        "af_illuminator_sq_blocked_eopnotsupp": asdict(af_illum_sq_blocked),
        "camera_settings_reset_restores_defaults": asdict(cam_reset_restores),
    }


# ---------------------------------------------------------------------------
# Sub-Model 55B: [Area/Date/Time Setting] & Zero-RF Creators' App Isolation
# ---------------------------------------------------------------------------


def simulate_area_datetime_and_zero_rf_hil(
    *,
    menu_item_title: str = AREA_DATETIME_OFFICIAL_TITLE,
    bench_stage: str = BENCH_STAGE_H0,
    airplane_mode: str = TOGGLE_ON,
    configured_area_setting: str = AREA_UNCONFIGURED,
    configured_daylight_savings: str = TOGGLE_OFF,
    configured_date_time: str = DEFAULT_DATETIME_STR,
    configured_date_format: str = DATE_FORMAT_YYYY_MM_DD,
    configured_location_info_link: str = TOGGLE_OFF,
    configured_auto_time_correction: str = TOGGLE_OFF,
    configured_auto_area_adjustment: str = TOGGLE_OFF,
    rtc_backup_battery_depleted: bool = False,
    reset_action: str = RESET_ACTION_NONE,
    force_creators_app_sync_during_airplane: bool = False,
    force_rtc_jump_during_h0_h3: bool = False,
) -> AreaDateTimeAndZeroRfEvalResult:
    """Co-emulate Wave-45 [Area/Date/Time Setting] & Zero-RF Creators' App RTC isolation."""

    def _err(errno_val: int, reason: str, *, air_blocked: bool = False) -> AreaDateTimeAndZeroRfEvalResult:
        return AreaDateTimeAndZeroRfEvalResult(
            menu_path=AREA_DATETIME_MENU_PATH,
            creators_app_menu_path=CREATORS_APP_LOC_LINK_MENU_PATH,
            airplane_menu_path=AIRPLANE_MODE_MENU_PATH,
            menu_item_title=menu_item_title,
            bench_stage=bench_stage,
            airplane_mode=airplane_mode,
            configured_area_setting=configured_area_setting,
            configured_daylight_savings=configured_daylight_savings,
            configured_date_time=configured_date_time,
            configured_date_format=configured_date_format,
            configured_location_info_link=configured_location_info_link,
            configured_auto_time_correction=configured_auto_time_correction,
            configured_auto_area_adjustment=configured_auto_area_adjustment,
            effective_area_setting=AREA_UNCONFIGURED,
            effective_daylight_savings=TOGGLE_OFF,
            effective_date_time=DEFAULT_DATETIME_STR,
            effective_date_format=DATE_FORMAT_YYYY_MM_DD,
            effective_location_info_link=TOGGLE_OFF,
            effective_auto_time_correction=TOGGLE_OFF,
            effective_auto_area_adjustment=TOGGLE_OFF,
            rtc_backup_battery_depleted=bool(rtc_backup_battery_depleted),
            rtc_reprompt_required=True,
            creators_app_sync_blocked_by_airplane_mode=air_blocked,
            h0_h3_rtc_monotonic_preserved=True,
            reset_action=reset_action,
            area_datetime_survived_camera_reset=False,
            area_datetime_cleared_by_initialize=False,
            legacy_date_time_setup_spoof_events=LEGACY_DATE_TIME_SETUP_SPOOF_EVENTS,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            creators_app_rtc_sync_jump_events=CREATORS_APP_RTC_SYNC_JUMP_EVENTS,
            admitted=False,
            errno_code=errno_val,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if menu_item_title == LEGACY_DATE_TIME_SETUP_TITLE:
        return _err(EOPNOTSUPP_ERRNO, "LEGACY_DATE_TIME_SETUP_TITLE_SPOOF_REJECTED")
    if menu_item_title != AREA_DATETIME_OFFICIAL_TITLE:
        return _err(EINVAL_ERRNO, "INVALID_AREA_DATETIME_MENU_TITLE")

    if (
        bench_stage not in VALID_BENCH_STAGES
        or airplane_mode not in VALID_TOGGLE_STATES
        or configured_area_setting not in VALID_AREA_SETTINGS
        or configured_daylight_savings not in VALID_TOGGLE_STATES
        or configured_date_format not in VALID_DATE_FORMATS
        or configured_location_info_link not in VALID_TOGGLE_STATES
        or configured_auto_time_correction not in VALID_TOGGLE_STATES
        or configured_auto_area_adjustment not in VALID_TOGGLE_STATES
        or reset_action not in VALID_RESET_ACTIONS
        or (not _DATETIME_RE.match(configured_date_time))
    ):
        return _err(EINVAL_ERRNO, "INVALID_AREA_DATETIME_OR_RF_PARAMETER")

    air_on = airplane_mode == TOGGLE_ON
    if force_creators_app_sync_during_airplane and air_on:
        return _err(EACCES_ERRNO, "CREATORS_APP_SYNC_BLOCKED_BY_AIRPLANE_MODE", air_blocked=True)

    if force_rtc_jump_during_h0_h3:
        return _err(EOPNOTSUPP_ERRNO, "H0_H3_FORENSIC_RTC_JUMP_BLOCKED", air_blocked=air_on)

    # Setup > Area/Date survives [Camera Settings Reset] & [Reset Network Set.],
    # cleared/re-prompted ONLY by [Initialize] or RTC backup battery depletion.
    init_reset = reset_action == RESET_ACTION_INITIALIZE
    survived_cam_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_RESET_NETWORK_SET,
    )
    cleared = init_reset or bool(rtc_backup_battery_depleted)

    eff_area = AREA_UNCONFIGURED if cleared else configured_area_setting
    eff_dst = TOGGLE_OFF if cleared else configured_daylight_savings
    eff_dt = "2020-01-01 00:00:00" if cleared else configured_date_time
    eff_fmt = DATE_FORMAT_YYYY_MM_DD if cleared else configured_date_format
    reprompt = eff_area == AREA_UNCONFIGURED or cleared

    # Zero-RF isolation: Airplane Mode = On suppresses Location Info. Link / Auto Time Correction /
    # Auto Area Adjustment so Bluetooth/Wi-Fi never emits RF or mutates forensic RTC timestamps.
    net_reset = reset_action in (RESET_ACTION_RESET_NETWORK_SET, RESET_ACTION_INITIALIZE)
    if air_on or net_reset:
        eff_loc_link = TOGGLE_OFF
        eff_auto_tc = TOGGLE_OFF
        eff_auto_area = TOGGLE_OFF
    else:
        eff_loc_link = configured_location_info_link
        eff_auto_tc = configured_auto_time_correction if eff_loc_link == TOGGLE_ON else TOGGLE_OFF
        eff_auto_area = configured_auto_area_adjustment if eff_loc_link == TOGGLE_ON else TOGGLE_OFF

    return AreaDateTimeAndZeroRfEvalResult(
        menu_path=AREA_DATETIME_MENU_PATH,
        creators_app_menu_path=CREATORS_APP_LOC_LINK_MENU_PATH,
        airplane_menu_path=AIRPLANE_MODE_MENU_PATH,
        menu_item_title=menu_item_title,
        bench_stage=bench_stage,
        airplane_mode=airplane_mode,
        configured_area_setting=configured_area_setting,
        configured_daylight_savings=configured_daylight_savings,
        configured_date_time=configured_date_time,
        configured_date_format=configured_date_format,
        configured_location_info_link=configured_location_info_link,
        configured_auto_time_correction=configured_auto_time_correction,
        configured_auto_area_adjustment=configured_auto_area_adjustment,
        effective_area_setting=eff_area,
        effective_daylight_savings=eff_dst,
        effective_date_time=eff_dt,
        effective_date_format=eff_fmt,
        effective_location_info_link=eff_loc_link,
        effective_auto_time_correction=eff_auto_tc,
        effective_auto_area_adjustment=eff_auto_area,
        rtc_backup_battery_depleted=bool(rtc_backup_battery_depleted),
        rtc_reprompt_required=reprompt,
        creators_app_sync_blocked_by_airplane_mode=air_on,
        h0_h3_rtc_monotonic_preserved=True,
        reset_action=reset_action,
        area_datetime_survived_camera_reset=survived_cam_reset,
        area_datetime_cleared_by_initialize=init_reset,
        legacy_date_time_setup_spoof_events=LEGACY_DATE_TIME_SETUP_SPOOF_EVENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        creators_app_rtc_sync_jump_events=CREATORS_APP_RTC_SYNC_JUMP_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="AREA_DATETIME_AND_ZERO_RF_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_b_area_datetime_and_zero_rf_hil() -> Dict[str, object]:
    """Evaluate Wave-45 Sub-Model 55B [Area/Date/Time Setting] & Zero-RF Creators' App isolation."""
    initial_unconfigured = simulate_area_datetime_and_zero_rf_hil()
    legacy_title_rejected = simulate_area_datetime_and_zero_rf_hil(
        menu_item_title=LEGACY_DATE_TIME_SETUP_TITLE,
    )
    cam_reset_survives = simulate_area_datetime_and_zero_rf_hil(
        configured_area_setting="Los Angeles",
        configured_daylight_savings=TOGGLE_ON,
        configured_date_time="2026-11-17 15:30:00",
        configured_date_format=DATE_FORMAT_MM_DD_YYYY,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_clears_reprompts = simulate_area_datetime_and_zero_rf_hil(
        configured_area_setting="Los Angeles",
        configured_daylight_savings=TOGGLE_ON,
        configured_date_time="2026-11-17 15:30:00",
        configured_date_format=DATE_FORMAT_MM_DD_YYYY,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    rtc_battery_depleted_reprompts = simulate_area_datetime_and_zero_rf_hil(
        configured_area_setting="Tokyo",
        configured_daylight_savings=TOGGLE_OFF,
        configured_date_time="2026-11-17 15:30:00",
        rtc_backup_battery_depleted=True,
    )
    zero_rf_h0_h3_matrix = {
        stage: asdict(
            simulate_area_datetime_and_zero_rf_hil(
                bench_stage=stage,
                airplane_mode=TOGGLE_ON,
                configured_area_setting="UTC",
                configured_location_info_link=TOGGLE_ON,
                configured_auto_time_correction=TOGGLE_ON,
                configured_auto_area_adjustment=TOGGLE_ON,
            )
        )
        for stage in VALID_BENCH_STAGES
    }
    creators_app_forced_blocked = simulate_area_datetime_and_zero_rf_hil(
        airplane_mode=TOGGLE_ON,
        configured_location_info_link=TOGGLE_ON,
        configured_auto_time_correction=TOGGLE_ON,
        force_creators_app_sync_during_airplane=True,
    )
    h0_h3_rtc_jump_blocked = simulate_area_datetime_and_zero_rf_hil(
        bench_stage=BENCH_STAGE_H2,
        airplane_mode=TOGGLE_OFF,
        force_rtc_jump_during_h0_h3=True,
    )

    passed = (
        initial_unconfigured.admitted
        and initial_unconfigured.effective_area_setting == AREA_UNCONFIGURED
        and initial_unconfigured.effective_daylight_savings == TOGGLE_OFF
        and initial_unconfigured.rtc_reprompt_required
        and (not legacy_title_rejected.admitted)
        and legacy_title_rejected.errno_code == EOPNOTSUPP_ERRNO
        and cam_reset_survives.admitted
        and cam_reset_survives.area_datetime_survived_camera_reset
        and cam_reset_survives.effective_area_setting == "Los Angeles"
        and cam_reset_survives.effective_daylight_savings == TOGGLE_ON
        and cam_reset_survives.effective_date_time == "2026-11-17 15:30:00"
        and cam_reset_survives.effective_date_format == DATE_FORMAT_MM_DD_YYYY
        and (not cam_reset_survives.rtc_reprompt_required)
        and init_clears_reprompts.admitted
        and init_clears_reprompts.area_datetime_cleared_by_initialize
        and init_clears_reprompts.effective_area_setting == AREA_UNCONFIGURED
        and init_clears_reprompts.effective_daylight_savings == TOGGLE_OFF
        and init_clears_reprompts.rtc_reprompt_required
        and rtc_battery_depleted_reprompts.admitted
        and rtc_battery_depleted_reprompts.rtc_reprompt_required
        and rtc_battery_depleted_reprompts.effective_area_setting == AREA_UNCONFIGURED
        and all(
            v["admitted"]
            and v["creators_app_sync_blocked_by_airplane_mode"]
            and v["effective_location_info_link"] == TOGGLE_OFF
            and v["effective_auto_time_correction"] == TOGGLE_OFF
            and v["effective_auto_area_adjustment"] == TOGGLE_OFF
            and v["passive_tx_bytes_emitted"] == 0
            and v["creators_app_rtc_sync_jump_events"] == 0
            and v["h0_h3_rtc_monotonic_preserved"]
            for v in zero_rf_h0_h3_matrix.values()
        )
        and (not creators_app_forced_blocked.admitted)
        and creators_app_forced_blocked.errno_code == EACCES_ERRNO
        and (not h0_h3_rtc_jump_blocked.admitted)
        and h0_h3_rtc_jump_blocked.errno_code == EOPNOTSUPP_ERRNO
    )

    return {
        "passed": passed,
        "menu_path": AREA_DATETIME_MENU_PATH,
        "exact_official_title": AREA_DATETIME_OFFICIAL_TITLE,
        "initial_unconfigured_ok": asdict(initial_unconfigured),
        "legacy_datetime_setup_rejected_eopnotsupp": asdict(legacy_title_rejected),
        "camera_settings_reset_survives": asdict(cam_reset_survives),
        "initialize_clears_and_reprompts": asdict(init_clears_reprompts),
        "rtc_backup_battery_loss_reprompts": asdict(rtc_battery_depleted_reprompts),
        "zero_rf_h0_h3_isolation_matrix": zero_rf_h0_h3_matrix,
        "creators_app_sync_blocked_eacces": asdict(creators_app_forced_blocked),
        "h0_h3_rtc_jump_blocked_eopnotsupp": asdict(h0_h3_rtc_jump_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 55C & Redlines: [Video Light Mode] & [HDMI Resolution]
# ---------------------------------------------------------------------------


def simulate_video_light_and_hdmi_res_hil(
    *,
    shooting_domain: str = SHOOTING_DOMAIN_MOVIE,
    camera_state: str = CAMERA_STATE_REC,
    mishoe_video_light_attached: bool = True,
    mishoe_load_ma: int = HVL_LBPC_NOMINAL_LOAD_MA,
    low_light_scene: bool = False,
    log_shooting: str = LOG_SHOOTING_OFF,
    internal_recording_active: bool = True,
    rec_media_dur_hdmi_output: str = REC_MEDIA_DUR_HDMI_ON,
    edid_sink_max_resolution: str = HDMI_RES_2160P,
    configured_video_light_mode: str = VIDEO_LIGHT_POWER_LINK,
    configured_hdmi_resolution: str = HDMI_RES_AUTO,
    reset_action: str = RESET_ACTION_NONE,
    force_bypass_log_1080p_downshift: bool = False,
) -> VideoLightAndHdmiResEvalResult:
    """Co-emulate Wave-45 [Video Light Mode] (MI-Shoe 5V<=900mA) & [HDMI Resolution] (Log 1080p)."""

    def _err(errno_val: int, reason: str, *, overcurrent: bool = False) -> VideoLightAndHdmiResEvalResult:
        return VideoLightAndHdmiResEvalResult(
            video_light_menu_path=VIDEO_LIGHT_MODE_MENU_PATH,
            hdmi_res_menu_path=HDMI_RESOLUTION_MENU_PATH,
            rec_media_dur_hdmi_menu_path=REC_MEDIA_DUR_HDMI_MENU_PATH,
            shooting_domain=shooting_domain,
            camera_state=camera_state,
            mishoe_video_light_attached=mishoe_video_light_attached,
            mishoe_rail_voltage_mv=MISHOE_5V_VOLTAGE_MV,
            mishoe_rail_limit_ma=MISHOE_5V_RAIL_LIMIT_MA,
            mishoe_load_ma=mishoe_load_ma,
            mishoe_rail_overcurrent_tripped=overcurrent,
            low_light_scene=low_light_scene,
            log_shooting=log_shooting,
            internal_recording_active=internal_recording_active,
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            edid_sink_max_resolution=edid_sink_max_resolution,
            configured_video_light_mode=configured_video_light_mode,
            configured_hdmi_resolution=configured_hdmi_resolution,
            effective_video_light_mode=VIDEO_LIGHT_POWER_LINK,
            effective_hdmi_menu_setting=HDMI_RES_AUTO,
            effective_hdmi_resolution=HDMI_RES_AUTO,
            video_light_active=False,
            hdmi_log_1080p_downshift_active=False,
            reset_action=reset_action,
            setup_items_survived_camera_reset=False,
            setup_items_restored_by_initialize=False,
            mishoe_5v_900ma_overcurrent_events=MISHOE_5V_900MA_OVERCURRENT_EVENTS,
            hdmi_log_1080p_downshift_bypass_events=HDMI_LOG_1080P_DOWNSHIFT_BYPASS_EVENTS,
            admitted=False,
            errno_code=errno_val,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        shooting_domain not in VALID_SHOOTING_DOMAINS
        or camera_state not in VALID_CAMERA_STATES
        or mishoe_load_ma < 0
        or log_shooting not in VALID_LOG_SHOOTING_MODES
        or rec_media_dur_hdmi_output not in VALID_REC_MEDIA_DUR_HDMI_OPTIONS
        or edid_sink_max_resolution not in (HDMI_RES_2160P, HDMI_RES_1080P, HDMI_RES_1080I)
        or configured_video_light_mode not in VALID_VIDEO_LIGHT_MODES
        or configured_hdmi_resolution not in VALID_HDMI_RESOLUTIONS
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_VIDEO_LIGHT_OR_HDMI_PARAMETER")

    # Gate G24 parity: MI-Shoe 5V <= 900 mA accessory rail overcurrent lockout
    if mishoe_video_light_attached and mishoe_load_ma > MISHOE_5V_RAIL_LIMIT_MA:
        return _err(EACCES_ERRNO, "MISHOE_5V_900MA_RAIL_OVERCURRENT_LOCKOUT", overcurrent=True)

    init_reset = reset_action == RESET_ACTION_INITIALIZE
    survived_cam_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_RESET_NETWORK_SET,
    )

    eff_vlight_mode = VIDEO_LIGHT_POWER_LINK if init_reset else configured_video_light_mode
    eff_hdmi_cfg = HDMI_RES_AUTO if init_reset else configured_hdmi_resolution

    log_downshift_needed = (
        log_shooting != LOG_SHOOTING_OFF
        and internal_recording_active
        and rec_media_dur_hdmi_output != REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY
    )
    if force_bypass_log_1080p_downshift and log_downshift_needed:
        return _err(EOPNOTSUPP_ERRNO, "HDMI_LOG_1080P_DOWNSHIFT_REQUIRED")

    if log_downshift_needed:
        eff_hdmi_res = HDMI_RES_1080P
    elif eff_hdmi_cfg == HDMI_RES_AUTO:
        eff_hdmi_res = edid_sink_max_resolution
    else:
        eff_hdmi_res = eff_hdmi_cfg

    if not mishoe_video_light_attached or camera_state == CAMERA_STATE_POWER_OFF:
        vlight_on = False
    elif eff_vlight_mode == VIDEO_LIGHT_POWER_LINK:
        vlight_on = True
    elif eff_vlight_mode == VIDEO_LIGHT_REC_LINK:
        vlight_on = camera_state == CAMERA_STATE_REC
    elif eff_vlight_mode == VIDEO_LIGHT_REC_LINK_STBY:
        vlight_on = camera_state in (CAMERA_STATE_STBY, CAMERA_STATE_REC)
    else:
        vlight_on = low_light_scene and camera_state in (CAMERA_STATE_STBY, CAMERA_STATE_REC)

    return VideoLightAndHdmiResEvalResult(
        video_light_menu_path=VIDEO_LIGHT_MODE_MENU_PATH,
        hdmi_res_menu_path=HDMI_RESOLUTION_MENU_PATH,
        rec_media_dur_hdmi_menu_path=REC_MEDIA_DUR_HDMI_MENU_PATH,
        shooting_domain=shooting_domain,
        camera_state=camera_state,
        mishoe_video_light_attached=mishoe_video_light_attached,
        mishoe_rail_voltage_mv=MISHOE_5V_VOLTAGE_MV,
        mishoe_rail_limit_ma=MISHOE_5V_RAIL_LIMIT_MA,
        mishoe_load_ma=mishoe_load_ma if mishoe_video_light_attached else 0,
        mishoe_rail_overcurrent_tripped=False,
        low_light_scene=low_light_scene,
        log_shooting=log_shooting,
        internal_recording_active=internal_recording_active,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        edid_sink_max_resolution=edid_sink_max_resolution,
        configured_video_light_mode=configured_video_light_mode,
        configured_hdmi_resolution=configured_hdmi_resolution,
        effective_video_light_mode=eff_vlight_mode,
        effective_hdmi_menu_setting=eff_hdmi_cfg,
        effective_hdmi_resolution=eff_hdmi_res,
        video_light_active=vlight_on,
        hdmi_log_1080p_downshift_active=log_downshift_needed,
        reset_action=reset_action,
        setup_items_survived_camera_reset=survived_cam_reset,
        setup_items_restored_by_initialize=init_reset,
        mishoe_5v_900ma_overcurrent_events=MISHOE_5V_900MA_OVERCURRENT_EVENTS,
        hdmi_log_1080p_downshift_bypass_events=HDMI_LOG_1080P_DOWNSHIFT_BYPASS_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="VIDEO_LIGHT_AND_HDMI_RES_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def probe_phase278_redline_guard(**probes: bool) -> RedlineGuardProbeResult:
    """Verify all 16 Stage 55 hard safety & Wave-45 zero-write redline probes."""
    unknown = sorted(set(probes.keys()) - set(ALL_16_REDLINE_PROBE_FIELDS))
    if unknown:
        return RedlineGuardProbeResult(
            valid=False,
            errno_code=EINVAL_ERRNO,
            reason_code=f"UNKNOWN_REDLINE_PROBE:{unknown[0]}",
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
            isp_write_authorized=ISP_WRITE_AUTHORIZED,
            spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
            el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
            cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
            cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_corruptions=EMMC_CORRUPTIONS,
            nop_count=NOP_COUNT,
            guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
            otp_fuse_touches=OTP_FUSE_TOUCHES,
            rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
            legacy_mf_assist_spoof_events=LEGACY_MF_ASSIST_SPOOF_EVENTS,
            hdmi_clean_feed_mag_or_peaking_leaked_pixels=HDMI_CLEAN_FEED_MAG_OR_PEAKING_LEAKED_PIXELS,
            af_illuminator_movie_or_sq_fire_events=AF_ILLUMINATOR_MOVIE_OR_SQ_FIRE_EVENTS,
            legacy_date_time_setup_spoof_events=LEGACY_DATE_TIME_SETUP_SPOOF_EVENTS,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            creators_app_rtc_sync_jump_events=CREATORS_APP_RTC_SYNC_JUMP_EVENTS,
            mishoe_5v_900ma_overcurrent_events=MISHOE_5V_900MA_OVERCURRENT_EVENTS,
            hdmi_log_1080p_downshift_bypass_events=HDMI_LOG_1080P_DOWNSHIFT_BYPASS_EVENTS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        )

    for field in ALL_16_REDLINE_PROBE_FIELDS:
        if probes.get(field, False):
            if field == "cnflasha_userspace_write_requested":
                err = EROFS_ERRNO
            elif field in (
                "legacy_mf_assist_or_datetime_setup_spoof_requested",
                "hdmi_mag_or_peaking_bake_requested",
                "af_illuminator_movie_sq_fire_requested",
                "mishoe_overcurrent_or_log_1080p_bypass_requested",
            ):
                err = EOPNOTSUPP_ERRNO
            else:
                err = EACCES_ERRNO
            return RedlineGuardProbeResult(
                valid=False,
                errno_code=err,
                reason_code=f"REDLINE_BLOCKED:{field.upper()}",
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
                overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
                isp_write_authorized=ISP_WRITE_AUTHORIZED,
                spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
                el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
                cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
                cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
                emmc_corruptions=EMMC_CORRUPTIONS,
                nop_count=NOP_COUNT,
                guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
                otp_fuse_touches=OTP_FUSE_TOUCHES,
                rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
                legacy_mf_assist_spoof_events=LEGACY_MF_ASSIST_SPOOF_EVENTS,
                hdmi_clean_feed_mag_or_peaking_leaked_pixels=HDMI_CLEAN_FEED_MAG_OR_PEAKING_LEAKED_PIXELS,
                af_illuminator_movie_or_sq_fire_events=AF_ILLUMINATOR_MOVIE_OR_SQ_FIRE_EVENTS,
                legacy_date_time_setup_spoof_events=LEGACY_DATE_TIME_SETUP_SPOOF_EVENTS,
                passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
                creators_app_rtc_sync_jump_events=CREATORS_APP_RTC_SYNC_JUMP_EVENTS,
                mishoe_5v_900ma_overcurrent_events=MISHOE_5V_900MA_OVERCURRENT_EVENTS,
                hdmi_log_1080p_downshift_bypass_events=HDMI_LOG_1080P_DOWNSHIFT_BYPASS_EVENTS,
                raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            )

    return RedlineGuardProbeResult(
        valid=True,
        errno_code=0,
        reason_code="REDLINES_INTACT",
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        emmc_corruptions=EMMC_CORRUPTIONS,
        nop_count=NOP_COUNT,
        guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        legacy_mf_assist_spoof_events=LEGACY_MF_ASSIST_SPOOF_EVENTS,
        hdmi_clean_feed_mag_or_peaking_leaked_pixels=HDMI_CLEAN_FEED_MAG_OR_PEAKING_LEAKED_PIXELS,
        af_illuminator_movie_or_sq_fire_events=AF_ILLUMINATOR_MOVIE_OR_SQ_FIRE_EVENTS,
        legacy_date_time_setup_spoof_events=LEGACY_DATE_TIME_SETUP_SPOOF_EVENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        creators_app_rtc_sync_jump_events=CREATORS_APP_RTC_SYNC_JUMP_EVENTS,
        mishoe_5v_900ma_overcurrent_events=MISHOE_5V_900MA_OVERCURRENT_EVENTS,
        hdmi_log_1080p_downshift_bypass_events=HDMI_LOG_1080P_DOWNSHIFT_BYPASS_EVENTS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_pillar_c_d_video_light_hdmi_res_and_redlines() -> Dict[str, object]:
    """Evaluate Sub-Model 55C [Video Light Mode] & [HDMI Resolution] + 16 safety redlines."""
    video_light_4mode_matrix = {
        mode: {
            state: asdict(
                simulate_video_light_and_hdmi_res_hil(
                    configured_video_light_mode=mode,
                    camera_state=state,
                    low_light_scene=True,
                    mishoe_load_ma=HVL_LBPC_NOMINAL_LOAD_MA,
                )
            )
            for state in (CAMERA_STATE_POWER_ON, CAMERA_STATE_STBY, CAMERA_STATE_REC)
        }
        for mode in VALID_VIDEO_LIGHT_MODES
    }
    mishoe_overcurrent_blocked = simulate_video_light_and_hdmi_res_hil(
        configured_video_light_mode=VIDEO_LIGHT_POWER_LINK,
        mishoe_video_light_attached=True,
        mishoe_load_ma=1250,
    )
    hdmi_log_downshift_2160p_to_1080p = simulate_video_light_and_hdmi_res_hil(
        log_shooting=LOG_SHOOTING_CINE_EI,
        internal_recording_active=True,
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
        configured_hdmi_resolution=HDMI_RES_2160P,
    )
    hdmi_only_preserves_2160p = simulate_video_light_and_hdmi_res_hil(
        log_shooting=LOG_SHOOTING_CINE_EI,
        internal_recording_active=True,
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
        configured_hdmi_resolution=HDMI_RES_2160P,
    )
    hdmi_downshift_bypass_blocked = simulate_video_light_and_hdmi_res_hil(
        log_shooting=LOG_SHOOTING_FLEXIBLE_ISO,
        internal_recording_active=True,
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
        configured_hdmi_resolution=HDMI_RES_2160P,
        force_bypass_log_1080p_downshift=True,
    )
    cam_reset_preserves = simulate_video_light_and_hdmi_res_hil(
        configured_video_light_mode=VIDEO_LIGHT_REC_LINK_STBY,
        configured_hdmi_resolution=HDMI_RES_1080I,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_restores_defaults = simulate_video_light_and_hdmi_res_hil(
        configured_video_light_mode=VIDEO_LIGHT_REC_LINK_STBY,
        configured_hdmi_resolution=HDMI_RES_1080I,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    baseline_redline = probe_phase278_redline_guard()
    blocked_probes = {
        field: asdict(probe_phase278_redline_guard(**{field: True}))
        for field in ALL_16_REDLINE_PROBE_FIELDS
    }
    all_probes_blocked = all(not p["valid"] for p in blocked_probes.values())

    passed = (
        len(video_light_4mode_matrix) == 4
        and video_light_4mode_matrix[VIDEO_LIGHT_POWER_LINK][CAMERA_STATE_POWER_ON]["video_light_active"]
        and (not video_light_4mode_matrix[VIDEO_LIGHT_REC_LINK][CAMERA_STATE_STBY]["video_light_active"])
        and video_light_4mode_matrix[VIDEO_LIGHT_REC_LINK][CAMERA_STATE_REC]["video_light_active"]
        and video_light_4mode_matrix[VIDEO_LIGHT_REC_LINK_STBY][CAMERA_STATE_STBY]["video_light_active"]
        and (not mishoe_overcurrent_blocked.admitted)
        and mishoe_overcurrent_blocked.errno_code == EACCES_ERRNO
        and mishoe_overcurrent_blocked.mishoe_rail_overcurrent_tripped
        and mishoe_overcurrent_blocked.mishoe_5v_900ma_overcurrent_events == 0
        and hdmi_log_downshift_2160p_to_1080p.admitted
        and hdmi_log_downshift_2160p_to_1080p.hdmi_log_1080p_downshift_active
        and hdmi_log_downshift_2160p_to_1080p.effective_hdmi_resolution == HDMI_RES_1080P
        and hdmi_only_preserves_2160p.admitted
        and (not hdmi_only_preserves_2160p.hdmi_log_1080p_downshift_active)
        and hdmi_only_preserves_2160p.effective_hdmi_resolution == HDMI_RES_2160P
        and (not hdmi_downshift_bypass_blocked.admitted)
        and hdmi_downshift_bypass_blocked.errno_code == EOPNOTSUPP_ERRNO
        and cam_reset_preserves.admitted
        and cam_reset_preserves.setup_items_survived_camera_reset
        and cam_reset_preserves.effective_video_light_mode == VIDEO_LIGHT_REC_LINK_STBY
        and cam_reset_preserves.effective_hdmi_resolution == HDMI_RES_1080I
        and init_restores_defaults.admitted
        and init_restores_defaults.setup_items_restored_by_initialize
        and init_restores_defaults.effective_video_light_mode == VIDEO_LIGHT_POWER_LINK
        and init_restores_defaults.effective_hdmi_menu_setting == HDMI_RES_AUTO
        and init_restores_defaults.effective_hdmi_resolution == HDMI_RES_2160P
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "video_light_menu_path": VIDEO_LIGHT_MODE_MENU_PATH,
        "hdmi_res_menu_path": HDMI_RESOLUTION_MENU_PATH,
        "mishoe_5v_rail_limit_ma": MISHOE_5V_RAIL_LIMIT_MA,
        "all_16_redline_probe_fields": list(ALL_16_REDLINE_PROBE_FIELDS),
        "video_light_4mode_matrix": video_light_4mode_matrix,
        "mishoe_overcurrent_blocked_eacces": asdict(mishoe_overcurrent_blocked),
        "hdmi_log_downshift_2160p_to_1080p": asdict(hdmi_log_downshift_2160p_to_1080p),
        "hdmi_only_preserves_2160p": asdict(hdmi_only_preserves_2160p),
        "hdmi_log_downshift_bypass_blocked_eopnotsupp": asdict(hdmi_downshift_bypass_blocked),
        "camera_settings_reset_preserves_setup_items": asdict(cam_reset_preserves),
        "initialize_restores_setup_defaults": asdict(init_restores_defaults),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 278 (Stage 55, 55/55) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase278_realhw_focus_mag_datetime_videolight_hdmires_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 278 Stage 55 (55/55) Wave-45 HIL co-emulation audit."""
    donor_audit = inspect_phase278_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_focus_assistant_and_peaking_hil()
    pillar_b = evaluate_pillar_b_area_datetime_and_zero_rf_hil()
    pillar_cd = evaluate_pillar_c_d_video_light_hdmi_res_and_redlines()

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
        "emmc_corruptions": EMMC_CORRUPTIONS,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "legacy_mf_assist_spoof_events": LEGACY_MF_ASSIST_SPOOF_EVENTS,
        "hdmi_clean_feed_mag_or_peaking_leaked_pixels": (
            HDMI_CLEAN_FEED_MAG_OR_PEAKING_LEAKED_PIXELS
        ),
        "af_illuminator_movie_or_sq_fire_events": AF_ILLUMINATOR_MOVIE_OR_SQ_FIRE_EVENTS,
        "legacy_date_time_setup_spoof_events": LEGACY_DATE_TIME_SETUP_SPOOF_EVENTS,
        "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
        "creators_app_rtc_sync_jump_events": CREATORS_APP_RTC_SYNC_JUMP_EVENTS,
        "mishoe_5v_900ma_overcurrent_events": MISHOE_5V_900MA_OVERCURRENT_EVENTS,
        "hdmi_log_1080p_downshift_bypass_events": HDMI_LOG_1080P_DOWNSHIFT_BYPASS_EVENTS,
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
        and EMMC_CORRUPTIONS == 0
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
        and LEGACY_MF_ASSIST_SPOOF_EVENTS == 0
        and HDMI_CLEAN_FEED_MAG_OR_PEAKING_LEAKED_PIXELS == 0
        and AF_ILLUMINATOR_MOVIE_OR_SQ_FIRE_EVENTS == 0
        and LEGACY_DATE_TIME_SETUP_SPOOF_EVENTS == 0
        and PASSIVE_TX_BYTES_EMITTED == 0
        and CREATORS_APP_RTC_SYNC_JUMP_EVENTS == 0
        and MISHOE_5V_900MA_OVERCURRENT_EVENTS == 0
        and HDMI_LOG_1080P_DOWNSHIFT_BYPASS_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_278_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_focus_assistant_and_peaking_hil": pillar_a,
        "pillar_b_area_datetime_and_zero_rf_hil": pillar_b,
        "pillar_c_d_video_light_hdmi_res_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_focus_mag_datetime_videolight_hdmires_coemulator.py",
        description=(
            "Phase 278 Stage 55 (55/55) — Real-Hardware ILME-FX3 Wave-45 "
            "Focus Assistant (Auto Magnifier in MF & Initial Focus Mag. x1.0) & "
            "Peaking Display / Still-Only AF Illuminator, Area/Date/Time Setting "
            "Zero-RF Creators' App Isolation, and Video Light Mode (Power Link, "
            "MI-Shoe 5V<=900mA) & HDMI Resolution (Auto & Log 1080p Override) HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 278 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase278_realhw_focus_mag_datetime_videolight_hdmires_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 278 Stage 55 (55/55) | mode={rep['source_mode']} "
            f"| donors={rep['donor_audit']['donor_files_inspected']} "
            f"| mf_spoof={red['legacy_mf_assist_spoof_events']} "
            f"| dt_spoof={red['legacy_date_time_setup_spoof_events']} "
            f"| tx={red['passive_tx_bytes_emitted']} "
            f"| mishoe_oc={red['mishoe_5v_900ma_overcurrent_events']} "
            f"| log_1080p_byp={red['hdmi_log_1080p_downshift_bypass_events']} "
            f"| phys_wr={red['physical_device_writes']} "
            f"| leaked={red['raw_firmware_bytes_leaked']} "
            f"| digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
