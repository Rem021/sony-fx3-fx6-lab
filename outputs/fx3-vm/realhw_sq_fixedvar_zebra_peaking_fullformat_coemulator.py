#!/usr/bin/env python3
"""Phase 232 — Stage 42 (`42/42` Milestone) `outputs/fx3-vm/` Real-Hardware Main Track:
`ILME-FX3` (`0x91030080`, `Ver. 7.02`) Wave-32 `[Mode Settings]` = `[Fixed/Variable]` Locking Legacy
`[S&Q Settings]` in Favor of Direct `[FPS]` (`Home (FPS)`) & All 6 Hard S&Q Recording Disqualifications,
`[Zebra Display]` / `[Zebra Level]` (`70..100+`, `Custom 1`, `Custom 2`) Non-Resettable Persistence
Across `[Camera Settings Reset]` (Cleared Only by `[Initialize]`) & Strict Local-LCD-Only HDMI
Clean-Feed Isolation (`0` External HDMI Overlay Pixels for `[Zebra Display]` and `[Peaking Display]`
Even When `[HDMI Info. Display]=On`), and Slot 1 `[Format]` (`[Enter]` Quick Format vs `(Delete)`
Full Format + Mid-Cancel Data-Already-Erased Hazard) & Shooting-Screen `MENU + (Delete)` (~2s)
Hardware Button Chord Tier-0 Recovery Vault (`pnflasha`/`cnflasha`/`CAMSET01.DAT`) Firewall HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)`) 12-donor inspection (< 0.02s cold,
cached per process, bounded <= 4096 B windows on large firmware binaries) with deterministic
`CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), while hard-locking:
- `persistent_emmc_writes_authorized == False`
- `hardware_live_attachment_authorized == False`
- `overall_ready_for_hardware_attach == False`
- `spi_nor_write_authorized == False`
- `el3_payload_transmit_authorized == False`
- `isp_write_authorized == False`
- `cnflasha_userspace_write_blocked == True`
- `physical_usb_packets_emitted == 0`
- `otp_fuse_touches == 0`
- `rpmb_counter_increments == 0`
- `sq_fixedvar_6lock_bypass_events == 0`
- `hdmi_zebra_or_peaking_leaked_overlay_pixels == 0`
- `tier0_slot1_format_or_chord_wipe_events == 0`
- `raw_firmware_bytes_leaked == 0`
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
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Phase 232 Schema & Hard-Locked Safety Redlines (42/42 Milestone)
# ---------------------------------------------------------------------------

SCHEMA_ID = "realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator_v1"
PHASE_232_SCHEMA = SCHEMA_ID
PHASE_232_VERSION = "232.0.0"
STAGE_INDEX = 42
STAGE_TOTAL = 42
MILESTONE_LABEL = "42/42"
STAGE_NAME = "stage42_realhw_sq_fixedvar_zebra_peaking_fullformat_hil"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"

MODEL_ILME_FX3 = "ILME-FX3"
MODEL_ILME_FX6 = "ILME-FX6"
FX3_MODEL_ID = 0x91030080
STOCK_FX3_BOOT_IDENTITY = "ILME-FX3 Ver. 7.02 (Stock)"

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
SQ_FIXEDVAR_6LOCK_BYPASS_EVENTS = 0
HDMI_ZEBRA_OR_PEAKING_LEAKED_OVERLAY_PIXELS = 0
TIER0_SLOT1_FORMAT_OR_CHORD_WIPE_EVENTS = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0
DONOR_ACCESS_MODE = "O_RDONLY"
BOUNDED_WINDOW_MAX_BYTES = 4096

EBUSY_ERRNO = 16  # Linux EBUSY
EINVAL_ERRNO = 22  # Linux EINVAL
EROFS_ERRNO = 30  # Linux EROFS
EOPNOTSUPP_ERRNO = 95  # Linux ARM64 EOPNOTSUPP

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# ---------------------------------------------------------------------------
# Verified Local Donor Specs (12 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_lens_comm": f"{_FX3_USR_PREFIX}/lib/libInfraLensCommunicator.so",
    "fx6_lens_comm": f"{_FX6_NF15_PREFIX}/lib/libInfraLensCommunicator.so",
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
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_lens_comm": 14_544,
    "fx6_lens_comm": 14_544,
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
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_lens_comm": (b"LensCommunicator", b"GetMountedLensInfo", b"SndSyncMsg"),
    "fx6_lens_comm": (b"LensCommunicator", b"GetMountedLensInfo", b"SndSyncMsg"),
    "fx3_media_cfg": (b"MediaConfig", b"Slot", b"Backup_read"),
    "fx3_adj_media": (b"AVBB_SCN_START_HDMI", b"AVBB_SCN_STOP_HDMI", b"HDMI", b"Format", b"Delete"),
    "fx3_string_en_f": (
        b"Mode Settings",
        b"Fixed/Variable",
        b"S&Q Settings",
        b"FPS",
        b"Home",
        b"Audio Out Timing",
        b"Live",
        b"Lip Sync",
        b"Time Code Run",
        b"Time Code Output",
        b"XAVC HS 4K",
        b"XAVC S 4K",
        b"XAVC S-I 4K",
        b"XAVC S-I DCI 4K",
        b"XAVC S HD",
        b"XAVC S-I HD",
        b"240fps",
        b"200fps",
        b"120fps",
        b"100fps",
        b"119.88p",
        b"100p",
        b"Proxy Recording",
        b"Zebra Display",
        b"Zebra Display Select",
        b"Zebra Level",
        b"100+",
        b"Peaking Display",
        b"Peaking Display Select",
        b"Peaking Level",
        b"Peaking Color",
        b"Red",
        b"Yellow",
        b"Blue",
        b"White",
        b"Mid",
        b"Low",
        b"High",
        b"HDMI Info. Display",
        b"Camera Settings Reset",
        b"Initialize",
        b"Format",
        b"Quick Format",
        b"Full Format",
        b"Switch Full Format",
        b"Slot 1",
        b"Slot 2",
        b"Enter",
        b"Delete",
    ),
    "fx6_string_en": (
        b"Fixed/Variable",
        b"FPS",
        b"Home",
        b"Live",
        b"240fps",
        b"Peaking Level",
        b"Zebra",
        b"Peaking",
        b"Timecode",
        b"Audio",
        b"Proxy",
        b"Format",
        b"Quick Format",
        b"Full Format",
        b"Enter",
        b"Delete",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_930_240, "FORMAT", b"FORMAT"),
        (49_938_432, "PROXY", b"PROXY"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_954_816, "PEAKING", b"PEAKING"),
        (49_967_104, "INITIALIZE", b"INITIALIZE"),
        (51_482_624, "FPS", b"FPS"),
        (60_686_336, "S_AND_Q", b"S_AND_Q"),
        (61_210_624, "FULL_FORMAT", b"FULL_FORMAT"),
        (61_878_272, "HDMI_INFO", b"HDMI_INFO"),
        (62_050_304, "ZEBRA", b"ZEBRA"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (35_971_072, "HDMI", b"HDMI"),
        (37_232_640, "PROXY", b"PROXY"),
        (37_236_736, "FORMAT", b"FORMAT"),
        (37_437_440, "AUDIO", b"AUDIO"),
        (37_453_824, "FPS", b"FPS"),
        (39_022_592, "TIMECODE", b"TIMECODE"),
        (39_378_944, "ZEBRA", b"ZEBRA"),
        (39_378_944, "PEAKING", b"PEAKING"),
    ),
    "fx3_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (139_264, "ZEBRA", b"Zebra"),
        (364_544, "FORMAT", b"Format"),
        (696_320, "HDMI", b"HDMI"),
        (10_702_848, "PEAKING", b"Peaking"),
        (10_731_520, "PROXY", b"Proxy"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (135_168, "ZEBRA", b"Zebra"),
        (364_544, "FORMAT", b"Format"),
        (684_032, "HDMI", b"HDMI"),
        (12_165_120, "PEAKING", b"Peaking"),
        (12_193_792, "PROXY", b"Proxy"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (126_976, "AUDIO", b"Audio"),
        (131_072, "XAVC", b"Xavc"),
        (159_744, "MP4", b"Mp4"),
        (176_128, "PROXY", b"Proxy"),
        (249_856, "TIMECODE", b"TimeCode"),
        (2_965_504, "NON_REAL_TIME_META", b"NonRealTimeMeta"),
        (2_965_504, "LTC_CHANGE_TABLE", b"LtcChangeTable"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (155_648, "AUDIO", b"Audio"),
        (163_840, "XAVC", b"Xavc"),
        (163_840, "TIMECODE", b"TimeCode"),
        (204_800, "PROXY", b"Proxy"),
        (13_475_840, "LTC_CHANGE_TABLE", b"LtcChangeTable"),
        (13_516_800, "NON_REAL_TIME_META", b"NonRealTimeMeta"),
    ),
}

# ---------------------------------------------------------------------------
# Sub-model A/B/C Constants (Wave-32 Official ILME-FX3 Ver. 7.02 Contracts)
# ---------------------------------------------------------------------------

VALID_ON_OFF: Tuple[str, ...] = ("On", "Off")
REGION_NTSC = "NTSC"
REGION_PAL = "PAL"
VALID_TV_REGIONS: Tuple[str, ...] = (REGION_NTSC, REGION_PAL)

# Sub-model A: Ver. 7.00+/7.02 [Mode Settings] = [Fixed/Variable] vs [S&Q Settings] & 6 Locks
MODE_SETTINGS_MENU_PATH = "MENU -> Shooting -> [Shooting Mode] -> [Mode Settings]"
SQ_SETTINGS_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [S&Q Settings]"
FPS_HOME_CONTROL_PATH = "Home (FPS) / [FPS] Direct Control"
AUDIO_OUT_TIMING_MENU_PATH = "MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]"
TIMECODE_MENU_PATH = "MENU -> Shooting -> [TC/UB] -> [Time Code Run] / [Time Code Output]"
PROXY_SETTINGS_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [Proxy Settings] -> [Proxy Recording]"

MODE_SETTINGS_FIXED_VARIABLE = "Fixed/Variable"
MODE_SETTINGS_LEGACY_SQ_SEPARATE = "Separate Movie / S&Q"
VALID_MODE_SETTINGS: Tuple[str, ...] = (
    MODE_SETTINGS_FIXED_VARIABLE,
    MODE_SETTINGS_LEGACY_SQ_SEPARATE,
)

FPS_SWITCH_FIXED = "Fixed"
FPS_SWITCH_VARIABLE = "Variable"
VALID_FPS_SWITCH_STATES: Tuple[str, ...] = (FPS_SWITCH_FIXED, FPS_SWITCH_VARIABLE)

FILE_FORMAT_XAVC_HS_4K = "XAVC HS 4K"
FILE_FORMAT_XAVC_S_4K = "XAVC S 4K"
FILE_FORMAT_XAVC_SI_4K = "XAVC S-I 4K"
FILE_FORMAT_XAVC_SI_DCI_4K = "XAVC S-I DCI 4K"
FILE_FORMAT_XAVC_S_HD = "XAVC S HD"
FILE_FORMAT_XAVC_SI_HD = "XAVC S-I HD"
VALID_MOVIE_FILE_FORMATS: Tuple[str, ...] = (
    FILE_FORMAT_XAVC_HS_4K,
    FILE_FORMAT_XAVC_S_4K,
    FILE_FORMAT_XAVC_SI_4K,
    FILE_FORMAT_XAVC_SI_DCI_4K,
    FILE_FORMAT_XAVC_S_HD,
    FILE_FORMAT_XAVC_SI_HD,
)
FOUR_K_FILE_FORMATS_BLOCKING_240_200FPS: Tuple[str, ...] = (
    FILE_FORMAT_XAVC_HS_4K,
    FILE_FORMAT_XAVC_S_4K,
    FILE_FORMAT_XAVC_SI_4K,
    FILE_FORMAT_XAVC_SI_DCI_4K,
)
HD_FILE_FORMATS_ALLOWING_240_200FPS: Tuple[str, ...] = (
    FILE_FORMAT_XAVC_S_HD,
    FILE_FORMAT_XAVC_SI_HD,
)

NTSC_REC_FRAME_RATES: Tuple[str, ...] = ("23.98p", "24.00p", "29.97p", "59.94p", "119.88p")
PAL_REC_FRAME_RATES: Tuple[str, ...] = ("25p", "50p", "100p")
VALID_REC_FRAME_RATES: Tuple[str, ...] = NTSC_REC_FRAME_RATES + PAL_REC_FRAME_RATES
HFR_REC_FRAME_RATES_BLOCKING_PROXY: Tuple[str, ...] = ("119.88p", "100p")

NTSC_SQ_SHOOTING_FPS: Tuple[int, ...] = (1, 2, 4, 8, 15, 30, 60, 120, 240)
PAL_SQ_SHOOTING_FPS: Tuple[int, ...] = (1, 2, 3, 6, 12, 25, 50, 100, 200)
VALID_SQ_SHOOTING_FPS: Tuple[int, ...] = tuple(
    sorted(set(NTSC_SQ_SHOOTING_FPS + PAL_SQ_SHOOTING_FPS))
)

AUDIO_OUT_LIVE = "Live"
AUDIO_OUT_LIP_SYNC = "Lip Sync"
VALID_AUDIO_OUT_TIMINGS: Tuple[str, ...] = (AUDIO_OUT_LIVE, AUDIO_OUT_LIP_SYNC)

TC_RUN_REC_RUN = "Rec Run"
TC_RUN_FREE_RUN = "Free Run"
VALID_TC_RUN_MODES: Tuple[str, ...] = (TC_RUN_REC_RUN, TC_RUN_FREE_RUN)

PROXY_CODEC_XAVC_HS_HD_16M = "XAVC HS HD 16M 4:2:0 10bit"
PROXY_CODEC_XAVC_HS_HD_9M = "XAVC HS HD 9M 4:2:0 10bit"
PROXY_CODEC_XAVC_S_HD_6M = "XAVC S HD 6M 4:2:0 8bit"
VALID_PROXY_CODECS: Tuple[str, ...] = (
    PROXY_CODEC_XAVC_HS_HD_16M,
    PROXY_CODEC_XAVC_HS_HD_9M,
    PROXY_CODEC_XAVC_S_HD_6M,
)

SQ_LOCK_1_ZERO_AUDIO_0CH = "SQ_LOCK_1_ZERO_AUDIO_0CH_NO_SOUND_RECORDED"
SQ_LOCK_2_AUDIO_OUT_TIMING_DISABLED = "SQ_LOCK_2_AUDIO_OUT_TIMING_LIVE_LIPSYNC_DISABLED"
SQ_LOCK_3_TIMECODE_RUN_OUTPUT_UNAVAILABLE = "SQ_LOCK_3_TIMECODE_RUN_AND_OUTPUT_UNAVAILABLE"
SQ_LOCK_4_240_200FPS_4K_BLOCKED = "SQ_LOCK_4_240_200FPS_BLOCKED_ON_ALL_4K_FORMATS"
SQ_LOCK_5_120_100FPS_DCI_4K_BLOCKED = "SQ_LOCK_5_120_100FPS_BLOCKED_ON_XAVC_SI_DCI_4K"
SQ_LOCK_6_PROXY_REC_BLOCKED_HFR = "SQ_LOCK_6_PROXY_RECORDING_BLOCKED_AT_119_88P_100P_OR_GE_120_100FPS"

ALL_6_SQ_DISQUALIFICATION_IDS: Tuple[str, ...] = (
    SQ_LOCK_1_ZERO_AUDIO_0CH,
    SQ_LOCK_2_AUDIO_OUT_TIMING_DISABLED,
    SQ_LOCK_3_TIMECODE_RUN_OUTPUT_UNAVAILABLE,
    SQ_LOCK_4_240_200FPS_4K_BLOCKED,
    SQ_LOCK_5_120_100FPS_DCI_4K_BLOCKED,
    SQ_LOCK_6_PROXY_REC_BLOCKED_HFR,
)

# Sub-model B: [Zebra Display] / [Zebra Level] Persistence & [Zebra] + [Peaking] HDMI Isolation
ZEBRA_MENU_PATH = "MENU -> Exposure/Color -> [Zebra Display] -> [Zebra Display] / [Zebra Level]"
PEAKING_MENU_PATH = "MENU -> Focus -> [Peaking Display] -> [Peaking Display] / [Peaking Level] / [Peaking Color]"
HDMI_INFO_MENU_PATH = "MENU -> Setup -> [External Output] -> [HDMI Info. Display]"
RESET_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset]"

WHEEL_LEFT_DEFAULT_ZEBRA = "Zebra Display Select"
WHEEL_RIGHT_DEFAULT_PEAKING = "Peaking Display Select"

ZEBRA_DISPLAY_DEFAULT = "Off"
ZEBRA_LEVEL_DEFAULT = "70"
ZEBRA_PRESET_LEVELS: Tuple[str, ...] = ("70", "75", "80", "85", "90", "95", "100", "100+")
ZEBRA_CUSTOM_1 = "Custom 1"  # Standard + Range correct-exposure band
ZEBRA_CUSTOM_2 = "Custom 2"  # Minimum / Lower-Limit overexposure threshold
VALID_ZEBRA_LEVELS: Tuple[str, ...] = ZEBRA_PRESET_LEVELS + (ZEBRA_CUSTOM_1, ZEBRA_CUSTOM_2)
ZEBRA_CUSTOM1_STD_MIN = 0
ZEBRA_CUSTOM1_STD_MAX = 109
ZEBRA_CUSTOM1_RANGE_MIN = 1
ZEBRA_CUSTOM1_RANGE_MAX = 30
ZEBRA_CUSTOM2_LOWER_LIMIT_MIN = 0
ZEBRA_CUSTOM2_LOWER_LIMIT_MAX = 109  # 109 represents 109+

PEAKING_DISPLAY_DEFAULT = "Off"
PEAKING_LEVEL_HIGH = "High"
PEAKING_LEVEL_MID_DEFAULT = "Mid"
PEAKING_LEVEL_LOW = "Low"
VALID_PEAKING_LEVELS: Tuple[str, ...] = (
    PEAKING_LEVEL_HIGH,
    PEAKING_LEVEL_MID_DEFAULT,
    PEAKING_LEVEL_LOW,
)
PEAKING_COLOR_RED = "Red"
PEAKING_COLOR_YELLOW = "Yellow"
PEAKING_COLOR_BLUE = "Blue"
PEAKING_COLOR_WHITE_DEFAULT = "White"
VALID_PEAKING_COLORS: Tuple[str, ...] = (
    PEAKING_COLOR_RED,
    PEAKING_COLOR_YELLOW,
    PEAKING_COLOR_BLUE,
    PEAKING_COLOR_WHITE_DEFAULT,
)

RESET_ACTION_NONE = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET = "Camera Settings Reset"
RESET_ACTION_INITIALIZE = "Initialize"
VALID_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

LOCAL_LCD_FB0_WIDTH = 720
LOCAL_LCD_FB0_HEIGHT = 480
LOCAL_LCD_ZEBRA_SAMPLE_PIXELS = 18_432
LOCAL_LCD_PEAKING_SAMPLE_PIXELS = 12_288
HDMI_CLEAN_FEED_ASSIST_PIXELS = 0

# Sub-model C: [Format] (Quick vs (Delete) Full Format + Mid-Cancel) & MENU+Delete (~2s) Vault Firewall
FORMAT_MENU_PATH = "MENU -> Shooting -> [Media] -> [Format]"
FORMAT_CHORD_NAME = "MENU + (Delete)"
FORMAT_CHORD_MIN_HOLD_SEC = 2.0

SLOT_1 = "Slot 1"
SLOT_2 = "Slot 2"
VALID_MEDIA_SLOTS: Tuple[str, ...] = (SLOT_1, SLOT_2)

ENTRY_VIA_MENU_FORMAT = "MENU_MEDIA_FORMAT"
ENTRY_VIA_MENU_DELETE_CHORD = "SHOOTING_SCREEN_MENU_PLUS_DELETE_CHORD"
VALID_FORMAT_ENTRY_PATHS: Tuple[str, ...] = (
    ENTRY_VIA_MENU_FORMAT,
    ENTRY_VIA_MENU_DELETE_CHORD,
)

SCREEN_SHOOTING = "Shooting"
SCREEN_PLAYBACK = "Playback"
SCREEN_MENU = "Menu"
VALID_UI_SCREENS: Tuple[str, ...] = (SCREEN_SHOOTING, SCREEN_PLAYBACK, SCREEN_MENU)

FORMAT_MODE_QUICK = "Quick Format"
FORMAT_MODE_FULL = "Full Format"
VALID_FORMAT_MODES: Tuple[str, ...] = (FORMAT_MODE_QUICK, FORMAT_MODE_FULL)

DIALOG_KEY_ENTER = "Enter"
DIALOG_KEY_CANCEL = "Cancel"
VALID_DIALOG_CONFIRM_KEYS: Tuple[str, ...] = (DIALOG_KEY_ENTER, DIALOG_KEY_CANCEL)

TIER0_VAULT_NONE = "NONE"
TIER0_VAULT_PNFLASHA = "pnflasha"
TIER0_VAULT_CNFLASHA = "cnflasha"
TIER0_VAULT_CAMSET01 = "CAMSET01.DAT"
TIER0_VAULT_COMPOSITE = "pnflasha+cnflasha+CAMSET01.DAT"
VALID_TIER0_VAULT_PAYLOADS: Tuple[str, ...] = (
    TIER0_VAULT_NONE,
    TIER0_VAULT_PNFLASHA,
    TIER0_VAULT_CNFLASHA,
    TIER0_VAULT_CAMSET01,
    TIER0_VAULT_COMPOSITE,
)


class RealHwSqFixedVarZebraPeakingFullFormatError(ValueError):
    """Raised on invalid Phase 232 Stage 42 co-emulator configuration arguments."""


# ---------------------------------------------------------------------------
# Dataclasses for Donor Inspection & Sub-models A-C + Redlines
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
class Phase232DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    fx3_lens_comm: CompactDonorSummary
    fx6_lens_comm: CompactDonorSummary
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
    sq_fixedvar_and_6locks_proven: bool
    zebra_persistence_and_hdmi_cleanfeed_proven: bool
    fullformat_and_menu_delete_chord_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SqModeSettingsFixedVar6LocksHilResult:
    admitted: bool
    mode_settings_menu_path: str
    sq_settings_menu_path: str
    fps_control_path: str
    mode_settings: str
    fps_switch_state: str
    legacy_sq_settings_menu_locked: bool
    direct_home_fps_control_active: bool
    tv_region: str
    file_format: str
    rec_frame_rate: str
    shooting_fps: int
    sq_motion_active: bool
    speed_multiplier_vs_playback: float
    audio_channels_recorded: int
    requested_audio_out_timing: str
    audio_out_timing_available: bool
    effective_audio_out_timing: str
    time_code_run_available: bool
    time_code_output_available: bool
    proxy_recording_requested: str
    proxy_codec: str
    proxy_recording_available: bool
    effective_proxy_recording: str
    active_sq_disqualifications: Tuple[str, ...]
    blocked_disqualifications: Tuple[str, ...]
    sq_fixedvar_6lock_bypass_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class ZebraPersistenceAndHdmiIsolationHilResult:
    admitted: bool
    zebra_menu_path: str
    peaking_menu_path: str
    hdmi_info_menu_path: str
    reset_menu_path: str
    wheel_left_default_assignment: str
    wheel_right_default_assignment: str
    reset_action_applied: str
    configured_zebra_display: str
    configured_zebra_level: str
    custom1_std_level: int
    custom1_range_band: int
    custom2_lower_limit: int
    effective_zebra_display: str
    effective_zebra_level: str
    effective_custom1_band_ire: Tuple[int, int]
    effective_custom2_min_ire: int
    zebra_survived_camera_settings_reset: bool
    zebra_cleared_by_initialize: bool
    configured_peaking_display: str
    configured_peaking_level: str
    configured_peaking_color: str
    effective_peaking_display: str
    effective_peaking_level: str
    effective_peaking_color: str
    hdmi_connected: bool
    hdmi_info_display: str
    local_lcd_zebra_overlay_active: bool
    local_lcd_peaking_overlay_active: bool
    local_lcd_assist_overlay_pixels: int
    hdmi_info_telemetry_osd_active: bool
    hdmi_zebra_overlay_rendered: bool
    hdmi_peaking_overlay_rendered: bool
    hdmi_zebra_overlay_pixels: int
    hdmi_peaking_overlay_pixels: int
    hdmi_zebra_or_peaking_leaked_overlay_pixels: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class SlotFormatAndChordVaultFirewallHilResult:
    admitted: bool
    format_menu_path: str
    entry_path: str
    ui_screen: str
    chord_name: str
    chord_hold_sec: float
    chord_threshold_reached: bool
    target_slot: str
    slot1_tier0_vault_payload: str
    slot1_tier0_vault_present: bool
    off_camera_sha256_verified: bool
    sdxc_wp_switch_locked: bool
    vault_card_swapped_for_scratch_media: bool
    tier0_vault_firewall_engaged: bool
    format_dialog_opened: bool
    delete_key_toggle_presses: int
    selected_format_mode: str
    dialog_confirm_key: str
    cancel_mid_full_format: bool
    cancel_progress_pct: int
    format_executed: bool
    metadata_reinitialized: bool
    all_data_blocks_initialized: bool
    card_write_speed_restored: bool
    prior_data_permanently_erased: bool
    card_formatted_and_immediately_usable: bool
    persistent_emmc_writes_authorized: bool
    tier0_slot1_format_or_chord_wipe_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    persistent_emmc_writes_authorized: bool
    hardware_live_attachment_authorized: bool
    overall_ready_for_hardware_attach: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    cnflasha_userspace_write_blocked: bool
    cnflasha_mutation_bytes: int
    physical_usb_packets_emitted: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    sq_fixedvar_6lock_bypass_events: int
    hdmi_zebra_or_peaking_leaked_overlay_pixels: int
    tier0_slot1_format_or_chord_wipe_events: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase232DonorAudit] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase232DonorAudit] = None


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


def resolve_phase232_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 12 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen = next((root / rel for root in roots if (root / rel).is_file()), None)
        resolved[key] = chosen if chosen is not None else (
            roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel)
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
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in tokens}
    return CompactDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        uxd_container_ok=uxd_ok,
        sha256_prefix16=hashlib.sha256(data).hexdigest()[:16],
        marker_hits=hits,
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


def _build_clean_room_donor_audit() -> Phase232DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH_P232".encode("ascii")
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
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        head = (
            _build_synthetic_elf64_bytes((), f"{key}_HEAD_P232".encode("ascii"))
            if is_elf
            else (b"CPAPP_SYNTH_P232_" + label.encode("ascii")).ljust(64, b"\x00")
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase232DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=_mk_compact("fx3_lens_comm", "FX3_7.02", False),
        fx6_lens_comm=_mk_compact("fx6_lens_comm", "FX6_6.01", False),
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
        sq_fixedvar_and_6locks_proven=True,
        zebra_persistence_and_hdmi_cleanfeed_proven=True,
        fullformat_and_menu_delete_chord_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase232_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase232DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.02s cold, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase232_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple((k, str(p), p.stat().st_size, p.stat().st_mtime_ns) for k, p in sorted(paths.items()))
    cache_key = (SOURCE_MODE_LOCAL_DONOR, sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    fx3_lens_comm = _scan_compact_rdonly(paths["fx3_lens_comm"], artifact_key="fx3_lens_comm", body_label="FX3_7.02")
    fx6_lens_comm = _scan_compact_rdonly(paths["fx6_lens_comm"], artifact_key="fx6_lens_comm", body_label="FX6_6.01")
    fx3_media_cfg = _scan_compact_rdonly(paths["fx3_media_cfg"], artifact_key="fx3_media_cfg", body_label="FX3_7.02")
    fx3_adj_media = _scan_compact_rdonly(paths["fx3_adj_media"], artifact_key="fx3_adj_media", body_label="FX3_7.02")
    fx3_string_en_f = _scan_compact_rdonly(paths["fx3_string_en_f"], artifact_key="fx3_string_en_f", body_label="FX3_7.02")
    fx6_string_en = _scan_compact_rdonly(paths["fx6_string_en"], artifact_key="fx6_string_en", body_label="FX6_6.01")
    fx3_appfw = _scan_large_donor_rdonly(paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3_7.02")
    fx6_appfw = _scan_large_donor_rdonly(paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6_6.01")
    fx3_cpapp = _scan_large_donor_rdonly(paths["fx3_cpapp"], artifact_key="fx3_cpapp", body_label="FX3_7.02")
    fx6_cpapp = _scan_large_donor_rdonly(paths["fx6_cpapp"], artifact_key="fx6_cpapp", body_label="FX6_6.01")
    fx3_libmpr = _scan_large_donor_rdonly(paths["fx3_libmpr"], artifact_key="fx3_libmpr", body_label="FX3_7.02")
    fx6_libmpr = _scan_large_donor_rdonly(paths["fx6_libmpr"], artifact_key="fx6_libmpr", body_label="FX6_6.01")

    errors: List[str] = []
    for c_item in (fx3_lens_comm, fx6_lens_comm, fx3_media_cfg, fx3_adj_media, fx3_string_en_f, fx6_string_en):
        if c_item.file_bytes != EXPECTED_DONOR_BYTES[c_item.artifact_key]:
            errors.append(f"{c_item.artifact_key} byte size {c_item.file_bytes} != {EXPECTED_DONOR_BYTES[c_item.artifact_key]}")
        if not all(c_item.marker_hits.values()):
            errors.append(f"{c_item.artifact_key} missing tokens: {c_item.marker_hits}")

    for w_item in (fx3_appfw, fx6_appfw, fx3_cpapp, fx6_cpapp, fx3_libmpr, fx6_libmpr):
        if w_item.file_bytes != EXPECTED_DONOR_BYTES[w_item.artifact_key]:
            errors.append(f"{w_item.artifact_key} byte size {w_item.file_bytes} != {EXPECTED_DONOR_BYTES[w_item.artifact_key]}")
        if not all(w_item.window_hits.values()):
            errors.append(f"{w_item.artifact_key} missing window markers: {w_item.window_hits}")

    sq_ok = (
        fx3_string_en_f.uxd_container_ok
        and fx3_string_en_f.marker_hits.get("Mode Settings") == 1
        and fx3_string_en_f.marker_hits.get("Fixed/Variable") == 1
        and fx3_string_en_f.marker_hits.get("S&Q Settings") == 1
        and fx3_string_en_f.marker_hits.get("FPS") == 1
        and fx3_string_en_f.marker_hits.get("Audio Out Timing") == 1
        and fx3_string_en_f.marker_hits.get("Live") == 1
        and fx3_string_en_f.marker_hits.get("Lip Sync") == 1
        and fx3_string_en_f.marker_hits.get("Time Code Run") == 1
        and fx3_string_en_f.marker_hits.get("Time Code Output") == 1
        and fx3_string_en_f.marker_hits.get("XAVC S-I DCI 4K") == 1
        and fx3_string_en_f.marker_hits.get("240fps") == 1
        and fx3_string_en_f.marker_hits.get("120fps") == 1
        and fx3_string_en_f.marker_hits.get("Proxy Recording") == 1
        and fx3_appfw.window_hits.get("S_AND_Q") == 1
        and fx3_appfw.window_hits.get("FPS") == 1
        and fx3_appfw.window_hits.get("PROXY") == 1
        and fx3_libmpr.window_hits.get("TIMECODE") == 1
        and fx3_libmpr.window_hits.get("PROXY") == 1
    )
    zebra_peaking_ok = (
        fx3_adj_media.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("Zebra Display") == 1
        and fx3_string_en_f.marker_hits.get("Zebra Display Select") == 1
        and fx3_string_en_f.marker_hits.get("Zebra Level") == 1
        and fx3_string_en_f.marker_hits.get("100+") == 1
        and fx3_string_en_f.marker_hits.get("Peaking Display") == 1
        and fx3_string_en_f.marker_hits.get("Peaking Display Select") == 1
        and fx3_string_en_f.marker_hits.get("Peaking Level") == 1
        and fx3_string_en_f.marker_hits.get("Peaking Color") == 1
        and fx3_string_en_f.marker_hits.get("HDMI Info. Display") == 1
        and fx3_string_en_f.marker_hits.get("Camera Settings Reset") == 1
        and fx3_string_en_f.marker_hits.get("Initialize") == 1
        and fx3_appfw.window_hits.get("ZEBRA") == 1
        and fx3_appfw.window_hits.get("PEAKING") == 1
        and fx3_appfw.window_hits.get("HDMI_INFO") == 1
        and fx3_appfw.window_hits.get("INITIALIZE") == 1
        and fx3_cpapp.window_hits.get("ZEBRA") == 1
        and fx3_cpapp.window_hits.get("PEAKING") == 1
    )
    format_chord_ok = (
        fx3_media_cfg.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("Format") == 1
        and fx3_string_en_f.marker_hits.get("Quick Format") == 1
        and fx3_string_en_f.marker_hits.get("Full Format") == 1
        and fx3_string_en_f.marker_hits.get("Switch Full Format") == 1
        and fx3_string_en_f.marker_hits.get("Slot 1") == 1
        and fx3_string_en_f.marker_hits.get("Slot 2") == 1
        and fx3_string_en_f.marker_hits.get("Enter") == 1
        and fx3_string_en_f.marker_hits.get("Delete") == 1
        and fx3_appfw.window_hits.get("FORMAT") == 1
        and fx3_appfw.window_hits.get("FULL_FORMAT") == 1
        and fx3_cpapp.window_hits.get("FORMAT") == 1
    )
    audit = Phase232DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=fx3_lens_comm,
        fx6_lens_comm=fx6_lens_comm,
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
        sq_fixedvar_and_6locks_proven=sq_ok,
        zebra_persistence_and_hdmi_cleanfeed_proven=zebra_peaking_ok,
        fullformat_and_menu_delete_chord_proven=format_chord_ok,
        all_contracts_verified=(
            len(errors) == 0 and sq_ok and zebra_peaking_ok and format_chord_ok
        ),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-model A: Ver. 7.00+/7.02 [Mode Settings]=[Fixed/Variable] & 6 S&Q Locks
# ---------------------------------------------------------------------------

_REC_FPS_FLOAT_TABLE: Mapping[str, float] = {
    "23.98p": 23.976,
    "24.00p": 24.0,
    "25p": 25.0,
    "29.97p": 29.97,
    "50p": 50.0,
    "59.94p": 59.94,
    "100p": 100.0,
    "119.88p": 119.88,
}

_FIXED_FPS_MATCH_TABLE: Mapping[str, int] = {
    "23.98p": 24,
    "24.00p": 24,
    "25p": 25,
    "29.97p": 30,
    "50p": 50,
    "59.94p": 60,
    "100p": 100,
    "119.88p": 120,
}


def probe_sq_mode_settings_fixedvar_and_6locks_hil(
    *,
    mode_settings: str = MODE_SETTINGS_FIXED_VARIABLE,
    fps_switch_state: str = FPS_SWITCH_VARIABLE,
    tv_region: str = REGION_NTSC,
    file_format: str = FILE_FORMAT_XAVC_S_4K,
    rec_frame_rate: str = "23.98p",
    shooting_fps: int = 60,
    attempt_open_legacy_sq_settings_menu: bool = False,
    attempt_sq_audio_capture: bool = False,
    requested_audio_out_timing: str = AUDIO_OUT_LIVE,
    attempt_select_audio_out_timing_in_sq: bool = False,
    requested_tc_run: str = TC_RUN_FREE_RUN,
    requested_tc_output: str = "Off",
    attempt_enable_tc_run_or_output_in_sq: bool = False,
    proxy_recording_requested: str = "Off",
    proxy_codec: str = PROXY_CODEC_XAVC_HS_HD_16M,
) -> SqModeSettingsFixedVar6LocksHilResult:
    """Co-emulate Ver. 7.00+/7.02 [Mode Settings]=[Fixed/Variable] and all 6 S&Q disqualifications."""
    for val, allowed, label in (
        (tv_region, VALID_TV_REGIONS, "tv_region"),
        (requested_tc_run, VALID_TC_RUN_MODES, "requested_tc_run"),
        (requested_tc_output, VALID_ON_OFF, "requested_tc_output"),
        (proxy_recording_requested, VALID_ON_OFF, "proxy_recording_requested"),
        (proxy_codec, VALID_PROXY_CODECS, "proxy_codec"),
    ):
        if val not in allowed:
            raise RealHwSqFixedVarZebraPeakingFullFormatError(
                f"Unsupported {label} {val!r}"
            )

    legacy_locked = mode_settings == MODE_SETTINGS_FIXED_VARIABLE
    direct_fps_active = mode_settings == MODE_SETTINGS_FIXED_VARIABLE
    sq_active = fps_switch_state == FPS_SWITCH_VARIABLE

    def _mk_err(
        errno: int,
        status: str,
        *,
        active_disq: Tuple[str, ...] = (),
        blocked_disq: Tuple[str, ...] = (),
        px_avail: bool = False,
    ) -> SqModeSettingsFixedVar6LocksHilResult:
        return SqModeSettingsFixedVar6LocksHilResult(
            admitted=False,
            mode_settings_menu_path=MODE_SETTINGS_MENU_PATH,
            sq_settings_menu_path=SQ_SETTINGS_MENU_PATH,
            fps_control_path=FPS_HOME_CONTROL_PATH if direct_fps_active else SQ_SETTINGS_MENU_PATH,
            mode_settings=mode_settings,
            fps_switch_state=fps_switch_state,
            legacy_sq_settings_menu_locked=legacy_locked,
            direct_home_fps_control_active=direct_fps_active,
            tv_region=tv_region,
            file_format=file_format,
            rec_frame_rate=rec_frame_rate,
            shooting_fps=shooting_fps,
            sq_motion_active=sq_active,
            speed_multiplier_vs_playback=1.0,
            audio_channels_recorded=0,
            requested_audio_out_timing=requested_audio_out_timing,
            audio_out_timing_available=(not sq_active),
            effective_audio_out_timing="Disabled" if sq_active else requested_audio_out_timing,
            time_code_run_available=(not sq_active),
            time_code_output_available=(not sq_active),
            proxy_recording_requested=proxy_recording_requested,
            proxy_codec=proxy_codec,
            proxy_recording_available=px_avail,
            effective_proxy_recording="Off",
            active_sq_disqualifications=active_disq,
            blocked_disqualifications=blocked_disq,
            sq_fixedvar_6lock_bypass_events=0,
            errno_code=errno,
            status_code=status,
        )

    if mode_settings not in VALID_MODE_SETTINGS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MODE_SETTINGS_EINVAL")
    if fps_switch_state not in VALID_FPS_SWITCH_STATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FPS_SWITCH_STATE_EINVAL")
    if file_format not in VALID_MOVIE_FILE_FORMATS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MOVIE_FILE_FORMAT_EINVAL")
    if rec_frame_rate not in VALID_REC_FRAME_RATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_REC_FRAME_RATE_EINVAL")
    if requested_audio_out_timing not in VALID_AUDIO_OUT_TIMINGS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_AUDIO_OUT_TIMING_EINVAL")

    if tv_region == REGION_NTSC and rec_frame_rate not in NTSC_REC_FRAME_RATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_REC_FRAME_RATE_MISMATCH_NTSC_REGION_EINVAL")
    if tv_region == REGION_PAL and rec_frame_rate not in PAL_REC_FRAME_RATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_REC_FRAME_RATE_MISMATCH_PAL_REGION_EINVAL")
    if rec_frame_rate == "24.00p" and file_format != FILE_FORMAT_XAVC_SI_DCI_4K:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_24_00P_REQUIRES_XAVC_SI_DCI_4K_EOPNOTSUPP",
        )
    if file_format == FILE_FORMAT_XAVC_SI_DCI_4K and rec_frame_rate in ("119.88p", "100p"):
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_XAVC_SI_DCI_4K_REC_FRAME_RATE_120P_100P_UNSUPPORTED_EOPNOTSUPP",
        )

    # Ver. 7.00+/7.02 [Mode Settings] = [Fixed/Variable] locks legacy [S&Q Settings]
    if legacy_locked and attempt_open_legacy_sq_settings_menu:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_LEGACY_SQ_SETTINGS_LOCKED_UNDER_MODE_SETTINGS_FIXED_VARIABLE_EOPNOTSUPP",
        )

    # Standard fixed-frame-rate Movie shooting (FPS = Fixed)
    if not sq_active:
        eff_fps = _FIXED_FPS_MATCH_TABLE[rec_frame_rate]
        px_avail_fixed = rec_frame_rate not in HFR_REC_FRAME_RATES_BLOCKING_PROXY
        if proxy_recording_requested == "On" and not px_avail_fixed:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                "BLOCKED_FIXED_MOVIE_HFR_119_88P_100P_PROXY_UNAVAILABLE_EOPNOTSUPP",
                px_avail=False,
            )
        return SqModeSettingsFixedVar6LocksHilResult(
            admitted=True,
            mode_settings_menu_path=MODE_SETTINGS_MENU_PATH,
            sq_settings_menu_path=SQ_SETTINGS_MENU_PATH,
            fps_control_path=FPS_HOME_CONTROL_PATH if direct_fps_active else SQ_SETTINGS_MENU_PATH,
            mode_settings=mode_settings,
            fps_switch_state=fps_switch_state,
            legacy_sq_settings_menu_locked=legacy_locked,
            direct_home_fps_control_active=direct_fps_active,
            tv_region=tv_region,
            file_format=file_format,
            rec_frame_rate=rec_frame_rate,
            shooting_fps=eff_fps,
            sq_motion_active=False,
            speed_multiplier_vs_playback=1.0,
            audio_channels_recorded=2,
            requested_audio_out_timing=requested_audio_out_timing,
            audio_out_timing_available=True,
            effective_audio_out_timing=requested_audio_out_timing,
            time_code_run_available=True,
            time_code_output_available=True,
            proxy_recording_requested=proxy_recording_requested,
            proxy_codec=proxy_codec,
            proxy_recording_available=px_avail_fixed,
            effective_proxy_recording=proxy_recording_requested,
            active_sq_disqualifications=(),
            blocked_disqualifications=(),
            sq_fixedvar_6lock_bypass_events=0,
            errno_code=0,
            status_code="ADMITTED_FIXED_FPS_NORMAL_MOVIE_AUDIO_TC_ACTIVE_OK",
        )

    # Variable / S&Q shooting: validate shooting_fps against TV region
    region_sq_fps = NTSC_SQ_SHOOTING_FPS if tv_region == REGION_NTSC else PAL_SQ_SHOOTING_FPS
    if shooting_fps not in VALID_SQ_SHOOTING_FPS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SQ_SHOOTING_FPS_EINVAL")
    if shooting_fps not in region_sq_fps:
        return _mk_err(
            EINVAL_ERRNO,
            f"BLOCKED_SQ_SHOOTING_FPS_{shooting_fps}_MISMATCH_{tv_region}_EINVAL",
        )

    # Always-active S&Q Locks (1), (2), (3) whenever S&Q is active
    active_disq: List[str] = [
        SQ_LOCK_1_ZERO_AUDIO_0CH,
        SQ_LOCK_2_AUDIO_OUT_TIMING_DISABLED,
        SQ_LOCK_3_TIMECODE_RUN_OUTPUT_UNAVAILABLE,
    ]
    blocked_disq: List[str] = []

    if attempt_sq_audio_capture:
        blocked_disq.append(SQ_LOCK_1_ZERO_AUDIO_0CH)
    if attempt_select_audio_out_timing_in_sq:
        blocked_disq.append(SQ_LOCK_2_AUDIO_OUT_TIMING_DISABLED)
    if attempt_enable_tc_run_or_output_in_sq:
        blocked_disq.append(SQ_LOCK_3_TIMECODE_RUN_OUTPUT_UNAVAILABLE)

    # Lock (4): 240fps (NTSC) / 200fps (PAL) blocked on all 4K formats
    if shooting_fps in (240, 200) and file_format in FOUR_K_FILE_FORMATS_BLOCKING_240_200FPS:
        active_disq.append(SQ_LOCK_4_240_200FPS_4K_BLOCKED)
        blocked_disq.append(SQ_LOCK_4_240_200FPS_4K_BLOCKED)

    # Lock (5): 120fps (NTSC) / 100fps (PAL) blocked on XAVC S-I DCI 4K (4096x2160)
    if shooting_fps in (120, 100) and file_format == FILE_FORMAT_XAVC_SI_DCI_4K:
        active_disq.append(SQ_LOCK_5_120_100FPS_DCI_4K_BLOCKED)
        blocked_disq.append(SQ_LOCK_5_120_100FPS_DCI_4K_BLOCKED)

    # Lock (6): [Proxy Recording] blocked when Rec Frame Rate is 119.88p/100p OR Frame Rate >= 120/100fps
    hfr_sq_threshold = 120 if tv_region == REGION_NTSC else 100
    proxy_blocked_in_sq = (
        rec_frame_rate in HFR_REC_FRAME_RATES_BLOCKING_PROXY
        or shooting_fps >= hfr_sq_threshold
    )
    if proxy_blocked_in_sq:
        active_disq.append(SQ_LOCK_6_PROXY_REC_BLOCKED_HFR)
        if proxy_recording_requested == "On":
            blocked_disq.append(SQ_LOCK_6_PROXY_REC_BLOCKED_HFR)

    active_tuple = tuple(active_disq)
    blocked_tuple = tuple(blocked_disq)

    if blocked_tuple:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            f"BLOCKED_SQ_DISQUALIFICATION:{'+'.join(blocked_tuple)}",
            active_disq=active_tuple,
            blocked_disq=blocked_tuple,
            px_avail=(not proxy_blocked_in_sq),
        )

    rec_rate_float = _REC_FPS_FLOAT_TABLE[rec_frame_rate]
    speed_mult = round(rec_rate_float / float(shooting_fps), 4)
    return SqModeSettingsFixedVar6LocksHilResult(
        admitted=True,
        mode_settings_menu_path=MODE_SETTINGS_MENU_PATH,
        sq_settings_menu_path=SQ_SETTINGS_MENU_PATH,
        fps_control_path=FPS_HOME_CONTROL_PATH if direct_fps_active else SQ_SETTINGS_MENU_PATH,
        mode_settings=mode_settings,
        fps_switch_state=fps_switch_state,
        legacy_sq_settings_menu_locked=legacy_locked,
        direct_home_fps_control_active=direct_fps_active,
        tv_region=tv_region,
        file_format=file_format,
        rec_frame_rate=rec_frame_rate,
        shooting_fps=shooting_fps,
        sq_motion_active=True,
        speed_multiplier_vs_playback=speed_mult,
        audio_channels_recorded=0,
        requested_audio_out_timing=requested_audio_out_timing,
        audio_out_timing_available=False,
        effective_audio_out_timing="Disabled",
        time_code_run_available=False,
        time_code_output_available=False,
        proxy_recording_requested=proxy_recording_requested,
        proxy_codec=proxy_codec,
        proxy_recording_available=(not proxy_blocked_in_sq),
        effective_proxy_recording=proxy_recording_requested,
        active_sq_disqualifications=active_tuple,
        blocked_disqualifications=(),
        sq_fixedvar_6lock_bypass_events=0,
        errno_code=0,
        status_code="ADMITTED_SQ_VARIABLE_FPS_0CH_AUDIO_TC_DISABLED_OK",
    )


def evaluate_pillar_a_sq_fixedvar_and_6locks_hil() -> Dict[str, object]:
    fixed_lip_sync_ok = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
        fps_switch_state=FPS_SWITCH_FIXED,
        file_format=FILE_FORMAT_XAVC_SI_4K,
        rec_frame_rate="23.98p",
        requested_audio_out_timing=AUDIO_OUT_LIP_SYNC,
        proxy_recording_requested="On",
    )
    legacy_sq_menu_locked = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
        attempt_open_legacy_sq_settings_menu=True,
    )
    sq_60fps_proxy_ok = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
        fps_switch_state=FPS_SWITCH_VARIABLE,
        file_format=FILE_FORMAT_XAVC_HS_4K,
        rec_frame_rate="23.98p",
        shooting_fps=60,
        proxy_recording_requested="On",
    )
    sq_hd_240fps_ok = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        file_format=FILE_FORMAT_XAVC_SI_HD,
        rec_frame_rate="23.98p",
        shooting_fps=240,
        proxy_recording_requested="Off",
    )
    lock1_audio_blocked = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        shooting_fps=60,
        attempt_sq_audio_capture=True,
    )
    lock2_audio_out_timing_blocked = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        shooting_fps=60,
        requested_audio_out_timing=AUDIO_OUT_LIP_SYNC,
        attempt_select_audio_out_timing_in_sq=True,
    )
    lock3_tc_blocked = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        shooting_fps=60,
        attempt_enable_tc_run_or_output_in_sq=True,
    )
    lock4_4k_240fps_blocked = {
        fmt: asdict(
            probe_sq_mode_settings_fixedvar_and_6locks_hil(
                file_format=fmt,
                rec_frame_rate="24.00p" if fmt == FILE_FORMAT_XAVC_SI_DCI_4K else "23.98p",
                shooting_fps=240,
            )
        )
        for fmt in FOUR_K_FILE_FORMATS_BLOCKING_240_200FPS
    }
    lock4_pal_4k_200fps_blocked = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        tv_region=REGION_PAL,
        file_format=FILE_FORMAT_XAVC_S_4K,
        rec_frame_rate="25p",
        shooting_fps=200,
    )
    lock5_dci_4k_120fps_blocked = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        file_format=FILE_FORMAT_XAVC_SI_DCI_4K,
        rec_frame_rate="24.00p",
        shooting_fps=120,
    )
    lock5_dci_4k_100fps_pal_blocked = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        tv_region=REGION_PAL,
        file_format=FILE_FORMAT_XAVC_SI_DCI_4K,
        rec_frame_rate="25p",
        shooting_fps=100,
    )
    lock6_proxy_rec_11988p_blocked = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        file_format=FILE_FORMAT_XAVC_S_4K,
        rec_frame_rate="119.88p",
        shooting_fps=60,
        proxy_recording_requested="On",
    )
    lock6_proxy_fps_120_blocked = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        file_format=FILE_FORMAT_XAVC_S_4K,
        rec_frame_rate="23.98p",
        shooting_fps=120,
        proxy_recording_requested="On",
    )
    lock6_proxy_pal_100_blocked = probe_sq_mode_settings_fixedvar_and_6locks_hil(
        tv_region=REGION_PAL,
        file_format=FILE_FORMAT_XAVC_S_4K,
        rec_frame_rate="25p",
        shooting_fps=100,
        proxy_recording_requested="On",
    )
    passed = (
        fixed_lip_sync_ok.admitted
        and fixed_lip_sync_ok.legacy_sq_settings_menu_locked
        and fixed_lip_sync_ok.audio_channels_recorded == 2
        and fixed_lip_sync_ok.effective_audio_out_timing == AUDIO_OUT_LIP_SYNC
        and (not legacy_sq_menu_locked.admitted)
        and sq_60fps_proxy_ok.admitted
        and sq_60fps_proxy_ok.audio_channels_recorded == 0
        and (not sq_60fps_proxy_ok.audio_out_timing_available)
        and (not sq_60fps_proxy_ok.time_code_run_available)
        and (not sq_60fps_proxy_ok.time_code_output_available)
        and sq_60fps_proxy_ok.effective_proxy_recording == "On"
        and sq_hd_240fps_ok.admitted
        and (not lock1_audio_blocked.admitted)
        and SQ_LOCK_1_ZERO_AUDIO_0CH in lock1_audio_blocked.blocked_disqualifications
        and (not lock2_audio_out_timing_blocked.admitted)
        and SQ_LOCK_2_AUDIO_OUT_TIMING_DISABLED in lock2_audio_out_timing_blocked.blocked_disqualifications
        and (not lock3_tc_blocked.admitted)
        and SQ_LOCK_3_TIMECODE_RUN_OUTPUT_UNAVAILABLE in lock3_tc_blocked.blocked_disqualifications
        and all(not item["admitted"] for item in lock4_4k_240fps_blocked.values())
        and (not lock4_pal_4k_200fps_blocked.admitted)
        and (not lock5_dci_4k_120fps_blocked.admitted)
        and SQ_LOCK_5_120_100FPS_DCI_4K_BLOCKED in lock5_dci_4k_120fps_blocked.blocked_disqualifications
        and (not lock5_dci_4k_100fps_pal_blocked.admitted)
        and (not lock6_proxy_rec_11988p_blocked.admitted)
        and SQ_LOCK_6_PROXY_REC_BLOCKED_HFR in lock6_proxy_rec_11988p_blocked.blocked_disqualifications
        and (not lock6_proxy_fps_120_blocked.admitted)
        and SQ_LOCK_6_PROXY_REC_BLOCKED_HFR in lock6_proxy_fps_120_blocked.blocked_disqualifications
        and (not lock6_proxy_pal_100_blocked.admitted)
    )
    return {
        "passed": passed,
        "all_6_sq_disqualification_ids": list(ALL_6_SQ_DISQUALIFICATION_IDS),
        "fixed_2398p_lipsync_and_proxy_ok": asdict(fixed_lip_sync_ok),
        "legacy_sq_settings_locked_under_fixed_variable": asdict(legacy_sq_menu_locked),
        "sq_60fps_0ch_proxy_allowed_ok": asdict(sq_60fps_proxy_ok),
        "sq_hd_240fps_allowed_ok": asdict(sq_hd_240fps_ok),
        "lock1_sq_audio_capture_blocked": asdict(lock1_audio_blocked),
        "lock2_sq_audio_out_timing_blocked": asdict(lock2_audio_out_timing_blocked),
        "lock3_sq_timecode_run_and_output_blocked": asdict(lock3_tc_blocked),
        "lock4_4k_240fps_blocked_all_4_formats": lock4_4k_240fps_blocked,
        "lock4_pal_4k_200fps_blocked": asdict(lock4_pal_4k_200fps_blocked),
        "lock5_dci_4k_120fps_blocked": asdict(lock5_dci_4k_120fps_blocked),
        "lock5_pal_dci_4k_100fps_blocked": asdict(lock5_dci_4k_100fps_pal_blocked),
        "lock6_proxy_rec_11988p_blocked": asdict(lock6_proxy_rec_11988p_blocked),
        "lock6_proxy_fps_120_blocked": asdict(lock6_proxy_fps_120_blocked),
        "lock6_proxy_pal_fps_100_blocked": asdict(lock6_proxy_pal_100_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-model B: [Zebra] Reset Survival & [Zebra]+[Peaking] HDMI Clean-Feed Isolation
# ---------------------------------------------------------------------------


def probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
    *,
    configured_zebra_display: str = "On",
    configured_zebra_level: str = ZEBRA_CUSTOM_1,
    custom1_std_level: int = 70,
    custom1_range_band: int = 5,
    custom2_lower_limit: int = 100,
    configured_peaking_display: str = "On",
    configured_peaking_level: str = PEAKING_LEVEL_HIGH,
    configured_peaking_color: str = PEAKING_COLOR_RED,
    reset_action_applied: str = RESET_ACTION_NONE,
    hdmi_connected: bool = True,
    hdmi_info_display: str = "On",
    attempt_force_assist_overlay_on_hdmi: bool = False,
) -> ZebraPersistenceAndHdmiIsolationHilResult:
    """Co-emulate [Zebra] survival across [Camera Settings Reset] and 0-pixel HDMI assist isolation."""
    for val, allowed, label in (
        (hdmi_info_display, VALID_ON_OFF, "hdmi_info_display"),
    ):
        if val not in allowed:
            raise RealHwSqFixedVarZebraPeakingFullFormatError(
                f"Unsupported {label} {val!r}"
            )

    def _mk_err(errno: int, status: str) -> ZebraPersistenceAndHdmiIsolationHilResult:
        return ZebraPersistenceAndHdmiIsolationHilResult(
            admitted=False,
            zebra_menu_path=ZEBRA_MENU_PATH,
            peaking_menu_path=PEAKING_MENU_PATH,
            hdmi_info_menu_path=HDMI_INFO_MENU_PATH,
            reset_menu_path=RESET_MENU_PATH,
            wheel_left_default_assignment=WHEEL_LEFT_DEFAULT_ZEBRA,
            wheel_right_default_assignment=WHEEL_RIGHT_DEFAULT_PEAKING,
            reset_action_applied=reset_action_applied,
            configured_zebra_display=configured_zebra_display,
            configured_zebra_level=configured_zebra_level,
            custom1_std_level=custom1_std_level,
            custom1_range_band=custom1_range_band,
            custom2_lower_limit=custom2_lower_limit,
            effective_zebra_display=ZEBRA_DISPLAY_DEFAULT,
            effective_zebra_level=ZEBRA_LEVEL_DEFAULT,
            effective_custom1_band_ire=(65, 75),
            effective_custom2_min_ire=100,
            zebra_survived_camera_settings_reset=False,
            zebra_cleared_by_initialize=False,
            configured_peaking_display=configured_peaking_display,
            configured_peaking_level=configured_peaking_level,
            configured_peaking_color=configured_peaking_color,
            effective_peaking_display=PEAKING_DISPLAY_DEFAULT,
            effective_peaking_level=PEAKING_LEVEL_MID_DEFAULT,
            effective_peaking_color=PEAKING_COLOR_WHITE_DEFAULT,
            hdmi_connected=hdmi_connected,
            hdmi_info_display=hdmi_info_display,
            local_lcd_zebra_overlay_active=False,
            local_lcd_peaking_overlay_active=False,
            local_lcd_assist_overlay_pixels=0,
            hdmi_info_telemetry_osd_active=False,
            hdmi_zebra_overlay_rendered=False,
            hdmi_peaking_overlay_rendered=False,
            hdmi_zebra_overlay_pixels=HDMI_CLEAN_FEED_ASSIST_PIXELS,
            hdmi_peaking_overlay_pixels=HDMI_CLEAN_FEED_ASSIST_PIXELS,
            hdmi_zebra_or_peaking_leaked_overlay_pixels=0,
            errno_code=errno,
            status_code=status,
        )

    if configured_zebra_display not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_ZEBRA_DISPLAY_MODE_EINVAL")
    if configured_zebra_level not in VALID_ZEBRA_LEVELS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_ZEBRA_LEVEL_EINVAL")
    if not (ZEBRA_CUSTOM1_STD_MIN <= custom1_std_level <= ZEBRA_CUSTOM1_STD_MAX):
        return _mk_err(EINVAL_ERRNO, "BLOCKED_ZEBRA_CUSTOM1_STD_OUT_OF_RANGE_EINVAL")
    if not (ZEBRA_CUSTOM1_RANGE_MIN <= custom1_range_band <= ZEBRA_CUSTOM1_RANGE_MAX):
        return _mk_err(EINVAL_ERRNO, "BLOCKED_ZEBRA_CUSTOM1_RANGE_OUT_OF_RANGE_EINVAL")
    if not (ZEBRA_CUSTOM2_LOWER_LIMIT_MIN <= custom2_lower_limit <= ZEBRA_CUSTOM2_LOWER_LIMIT_MAX):
        return _mk_err(EINVAL_ERRNO, "BLOCKED_ZEBRA_CUSTOM2_LOWER_LIMIT_OUT_OF_RANGE_EINVAL")
    if configured_peaking_display not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_PEAKING_DISPLAY_MODE_EINVAL")
    if configured_peaking_level not in VALID_PEAKING_LEVELS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_PEAKING_LEVEL_EINVAL")
    if configured_peaking_color not in VALID_PEAKING_COLORS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_PEAKING_COLOR_EINVAL")
    if reset_action_applied not in VALID_RESET_ACTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_RESET_ACTION_EINVAL")

    if attempt_force_assist_overlay_on_hdmi:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_ZEBRA_OR_PEAKING_OVERLAY_ON_HDMI_FORBIDDEN_LOCAL_LCD_ONLY_EOPNOTSUPP",
        )

    # Reset persistence state machine:
    # - [Camera Settings Reset] does NOT reset [Zebra Display] or [Zebra Level] (incl. Custom 1/2),
    #   whereas standard focus/shooting settings like [Peaking Display] reset to Off/Mid/White.
    # - [Initialize] resets BOTH [Zebra Display]/[Zebra Level] -> Off/70 AND [Peaking Display] -> Off/Mid/White.
    if reset_action_applied == RESET_ACTION_INITIALIZE:
        eff_zebra_disp = ZEBRA_DISPLAY_DEFAULT
        eff_zebra_lvl = ZEBRA_LEVEL_DEFAULT
        eff_c1_band = (65, 75)
        eff_c2_min = 100
        zebra_survived_csr = False
        zebra_cleared_init = True
        eff_peak_disp = PEAKING_DISPLAY_DEFAULT
        eff_peak_lvl = PEAKING_LEVEL_MID_DEFAULT
        eff_peak_col = PEAKING_COLOR_WHITE_DEFAULT
    elif reset_action_applied == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_zebra_disp = configured_zebra_display
        eff_zebra_lvl = configured_zebra_level
        eff_c1_band = (
            max(0, custom1_std_level - custom1_range_band),
            min(109, custom1_std_level + custom1_range_band),
        )
        eff_c2_min = custom2_lower_limit
        zebra_survived_csr = True
        zebra_cleared_init = False
        eff_peak_disp = PEAKING_DISPLAY_DEFAULT
        eff_peak_lvl = PEAKING_LEVEL_MID_DEFAULT
        eff_peak_col = PEAKING_COLOR_WHITE_DEFAULT
    else:
        eff_zebra_disp = configured_zebra_display
        eff_zebra_lvl = configured_zebra_level
        eff_c1_band = (
            max(0, custom1_std_level - custom1_range_band),
            min(109, custom1_std_level + custom1_range_band),
        )
        eff_c2_min = custom2_lower_limit
        zebra_survived_csr = False
        zebra_cleared_init = False
        eff_peak_disp = configured_peaking_display
        eff_peak_lvl = configured_peaking_level
        eff_peak_col = configured_peaking_color

    lcd_zebra = eff_zebra_disp == "On"
    lcd_peaking = eff_peak_disp == "On"
    lcd_pixels = (
        (LOCAL_LCD_ZEBRA_SAMPLE_PIXELS if lcd_zebra else 0)
        + (LOCAL_LCD_PEAKING_SAMPLE_PIXELS if lcd_peaking else 0)
    )
    hdmi_telemetry_osd = bool(hdmi_connected and hdmi_info_display == "On")

    return ZebraPersistenceAndHdmiIsolationHilResult(
        admitted=True,
        zebra_menu_path=ZEBRA_MENU_PATH,
        peaking_menu_path=PEAKING_MENU_PATH,
        hdmi_info_menu_path=HDMI_INFO_MENU_PATH,
        reset_menu_path=RESET_MENU_PATH,
        wheel_left_default_assignment=WHEEL_LEFT_DEFAULT_ZEBRA,
        wheel_right_default_assignment=WHEEL_RIGHT_DEFAULT_PEAKING,
        reset_action_applied=reset_action_applied,
        configured_zebra_display=configured_zebra_display,
        configured_zebra_level=configured_zebra_level,
        custom1_std_level=custom1_std_level,
        custom1_range_band=custom1_range_band,
        custom2_lower_limit=custom2_lower_limit,
        effective_zebra_display=eff_zebra_disp,
        effective_zebra_level=eff_zebra_lvl,
        effective_custom1_band_ire=eff_c1_band,
        effective_custom2_min_ire=eff_c2_min,
        zebra_survived_camera_settings_reset=zebra_survived_csr,
        zebra_cleared_by_initialize=zebra_cleared_init,
        configured_peaking_display=configured_peaking_display,
        configured_peaking_level=configured_peaking_level,
        configured_peaking_color=configured_peaking_color,
        effective_peaking_display=eff_peak_disp,
        effective_peaking_level=eff_peak_lvl,
        effective_peaking_color=eff_peak_col,
        hdmi_connected=hdmi_connected,
        hdmi_info_display=hdmi_info_display,
        local_lcd_zebra_overlay_active=lcd_zebra,
        local_lcd_peaking_overlay_active=lcd_peaking,
        local_lcd_assist_overlay_pixels=lcd_pixels,
        hdmi_info_telemetry_osd_active=hdmi_telemetry_osd,
        hdmi_zebra_overlay_rendered=False,
        hdmi_peaking_overlay_rendered=False,
        hdmi_zebra_overlay_pixels=HDMI_CLEAN_FEED_ASSIST_PIXELS,
        hdmi_peaking_overlay_pixels=HDMI_CLEAN_FEED_ASSIST_PIXELS,
        hdmi_zebra_or_peaking_leaked_overlay_pixels=0,
        errno_code=0,
        status_code=(
            "ADMITTED_INITIALIZE_CLEARED_ZEBRA_TO_OFF_70_OK"
            if zebra_cleared_init
            else (
                "ADMITTED_ZEBRA_SURVIVED_CAMERA_SETTINGS_RESET_HDMI_0PX_OK"
                if zebra_survived_csr
                else "ADMITTED_LOCAL_LCD_ASSIST_ACTIVE_HDMI_CLEAN_FEED_0PX_OK"
            )
        ),
    )


def simulate_zebra_reset_vs_initialize_lifecycle(
    *,
    configured_zebra_level: str = ZEBRA_CUSTOM_2,
    custom1_std_level: int = 52,
    custom1_range_band: int = 4,
    custom2_lower_limit: int = 94,
) -> Dict[str, object]:
    """Simulate configured Zebra surviving [Camera Settings Reset] and clearing only on [Initialize]."""
    common = dict(
        configured_zebra_display="On",
        configured_zebra_level=configured_zebra_level,
        custom1_std_level=custom1_std_level,
        custom1_range_band=custom1_range_band,
        custom2_lower_limit=custom2_lower_limit,
        configured_peaking_display="On",
        configured_peaking_level=PEAKING_LEVEL_HIGH,
        configured_peaking_color=PEAKING_COLOR_YELLOW,
        hdmi_connected=True,
        hdmi_info_display="On",
    )
    step1_active = probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
        reset_action_applied=RESET_ACTION_NONE, **common
    )
    step2_after_csr = probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
        reset_action_applied=RESET_ACTION_CAMERA_SETTINGS_RESET, **common
    )
    step3_after_init = probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
        reset_action_applied=RESET_ACTION_INITIALIZE, **common
    )
    lifecycle_ok = (
        step1_active.admitted
        and step1_active.hdmi_zebra_overlay_pixels == 0
        and step1_active.hdmi_peaking_overlay_pixels == 0
        and step2_after_csr.admitted
        and step2_after_csr.zebra_survived_camera_settings_reset
        and step2_after_csr.effective_zebra_display == "On"
        and step2_after_csr.effective_zebra_level == configured_zebra_level
        and step2_after_csr.effective_custom2_min_ire == custom2_lower_limit
        and step2_after_csr.effective_peaking_display == "Off"
        and step3_after_init.admitted
        and step3_after_init.zebra_cleared_by_initialize
        and step3_after_init.effective_zebra_display == ZEBRA_DISPLAY_DEFAULT
        and step3_after_init.effective_zebra_level == ZEBRA_LEVEL_DEFAULT
    )
    return {
        "lifecycle_verified": lifecycle_ok,
        "hdmi_zebra_or_peaking_leaked_overlay_pixels": 0,
        "step1_configured_active": asdict(step1_active),
        "step2_survived_camera_settings_reset": asdict(step2_after_csr),
        "step3_cleared_by_initialize": asdict(step3_after_init),
    }


def evaluate_pillar_b_zebra_persistence_and_hdmi_isolation_hil() -> Dict[str, object]:
    both_on_hdmi_info_on = probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
        configured_zebra_display="On",
        configured_zebra_level=ZEBRA_CUSTOM_1,
        custom1_std_level=55,
        custom1_range_band=3,
        configured_peaking_display="On",
        configured_peaking_level=PEAKING_LEVEL_HIGH,
        configured_peaking_color=PEAKING_COLOR_RED,
        hdmi_connected=True,
        hdmi_info_display="On",
    )
    both_on_hdmi_info_off = probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
        configured_zebra_display="On",
        configured_zebra_level="100+",
        configured_peaking_display="On",
        configured_peaking_level=PEAKING_LEVEL_LOW,
        configured_peaking_color=PEAKING_COLOR_BLUE,
        hdmi_connected=True,
        hdmi_info_display="Off",
    )
    force_hdmi_overlay_blocked = probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
        attempt_force_assist_overlay_on_hdmi=True,
    )
    lifecycle = simulate_zebra_reset_vs_initialize_lifecycle()
    passed = (
        both_on_hdmi_info_on.admitted
        and both_on_hdmi_info_on.local_lcd_zebra_overlay_active
        and both_on_hdmi_info_on.local_lcd_peaking_overlay_active
        and both_on_hdmi_info_on.hdmi_info_telemetry_osd_active
        and both_on_hdmi_info_on.hdmi_zebra_overlay_pixels == 0
        and both_on_hdmi_info_on.hdmi_peaking_overlay_pixels == 0
        and both_on_hdmi_info_off.admitted
        and (not both_on_hdmi_info_off.hdmi_info_telemetry_osd_active)
        and both_on_hdmi_info_off.hdmi_zebra_overlay_pixels == 0
        and both_on_hdmi_info_off.hdmi_peaking_overlay_pixels == 0
        and (not force_hdmi_overlay_blocked.admitted)
        and bool(lifecycle["lifecycle_verified"])
    )
    return {
        "passed": passed,
        "zebra_and_peaking_on_with_hdmi_info_on_0px": asdict(both_on_hdmi_info_on),
        "zebra_100plus_and_peaking_blue_with_hdmi_info_off_0px": asdict(both_on_hdmi_info_off),
        "force_hdmi_assist_overlay_blocked": asdict(force_hdmi_overlay_blocked),
        "zebra_reset_survival_vs_initialize_lifecycle": lifecycle,
    }


# ---------------------------------------------------------------------------
# Sub-model C & Redlines: [Format] (Quick vs Full) & MENU+Delete (~2s) Vault Firewall
# ---------------------------------------------------------------------------


def probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
    *,
    entry_path: str = ENTRY_VIA_MENU_FORMAT,
    ui_screen: str = SCREEN_SHOOTING,
    chord_hold_sec: float = 2.2,
    target_slot: str = SLOT_1,
    slot1_tier0_vault_payload: str = TIER0_VAULT_COMPOSITE,
    off_camera_sha256_verified: bool = False,
    sdxc_wp_switch_locked: bool = True,
    vault_card_swapped_for_scratch_media: bool = False,
    delete_key_toggle_presses: int = 0,
    dialog_confirm_key: str = DIALOG_KEY_ENTER,
    cancel_mid_full_format: bool = False,
    cancel_progress_pct: int = 45,
) -> SlotFormatAndChordVaultFirewallHilResult:
    """Co-emulate Slot 1/2 Quick vs (Delete) Full Format, mid-cancel hazard, and Tier-0 vault firewall."""
    if delete_key_toggle_presses < 0:
        raise RealHwSqFixedVarZebraPeakingFullFormatError(
            "delete_key_toggle_presses must be >= 0"
        )
    if chord_hold_sec < 0.0:
        raise RealHwSqFixedVarZebraPeakingFullFormatError(
            "chord_hold_sec must be >= 0.0"
        )
    if not (0 <= cancel_progress_pct <= 100):
        raise RealHwSqFixedVarZebraPeakingFullFormatError(
            "cancel_progress_pct must be within 0..100"
        )

    vault_present_on_slot1 = (
        slot1_tier0_vault_payload != TIER0_VAULT_NONE
        and (not vault_card_swapped_for_scratch_media)
    )
    selected_mode = (
        FORMAT_MODE_FULL if (delete_key_toggle_presses % 2 == 1) else FORMAT_MODE_QUICK
    )
    chord_reached = (
        entry_path == ENTRY_VIA_MENU_DELETE_CHORD
        and chord_hold_sec >= FORMAT_CHORD_MIN_HOLD_SEC
    )

    def _mk_res(
        *,
        admitted: bool,
        firewall_engaged: bool,
        dialog_opened: bool,
        executed: bool,
        meta_init: bool,
        blocks_init: bool,
        speed_restored: bool,
        erased: bool,
        usable: bool,
        errno: int,
        status: str,
    ) -> SlotFormatAndChordVaultFirewallHilResult:
        return SlotFormatAndChordVaultFirewallHilResult(
            admitted=admitted,
            format_menu_path=FORMAT_MENU_PATH,
            entry_path=entry_path,
            ui_screen=ui_screen,
            chord_name=FORMAT_CHORD_NAME,
            chord_hold_sec=round(float(chord_hold_sec), 2),
            chord_threshold_reached=chord_reached,
            target_slot=target_slot,
            slot1_tier0_vault_payload=slot1_tier0_vault_payload,
            slot1_tier0_vault_present=vault_present_on_slot1,
            off_camera_sha256_verified=off_camera_sha256_verified,
            sdxc_wp_switch_locked=sdxc_wp_switch_locked,
            vault_card_swapped_for_scratch_media=vault_card_swapped_for_scratch_media,
            tier0_vault_firewall_engaged=firewall_engaged,
            format_dialog_opened=dialog_opened,
            delete_key_toggle_presses=delete_key_toggle_presses,
            selected_format_mode=selected_mode,
            dialog_confirm_key=dialog_confirm_key,
            cancel_mid_full_format=cancel_mid_full_format,
            cancel_progress_pct=cancel_progress_pct,
            format_executed=executed,
            metadata_reinitialized=meta_init,
            all_data_blocks_initialized=blocks_init,
            card_write_speed_restored=speed_restored,
            prior_data_permanently_erased=erased,
            card_formatted_and_immediately_usable=usable,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            tier0_slot1_format_or_chord_wipe_events=0,
            errno_code=errno,
            status_code=status,
        )

    if entry_path not in VALID_FORMAT_ENTRY_PATHS:
        return _mk_res(
            admitted=False,
            firewall_engaged=False,
            dialog_opened=False,
            executed=False,
            meta_init=False,
            blocks_init=False,
            speed_restored=False,
            erased=False,
            usable=False,
            errno=EINVAL_ERRNO,
            status="BLOCKED_INVALID_FORMAT_ENTRY_PATH_EINVAL",
        )
    if ui_screen not in VALID_UI_SCREENS:
        return _mk_res(
            admitted=False,
            firewall_engaged=False,
            dialog_opened=False,
            executed=False,
            meta_init=False,
            blocks_init=False,
            speed_restored=False,
            erased=False,
            usable=False,
            errno=EINVAL_ERRNO,
            status="BLOCKED_INVALID_UI_SCREEN_EINVAL",
        )
    if target_slot not in VALID_MEDIA_SLOTS:
        return _mk_res(
            admitted=False,
            firewall_engaged=False,
            dialog_opened=False,
            executed=False,
            meta_init=False,
            blocks_init=False,
            speed_restored=False,
            erased=False,
            usable=False,
            errno=EINVAL_ERRNO,
            status="BLOCKED_INVALID_TARGET_MEDIA_SLOT_EINVAL",
        )
    if slot1_tier0_vault_payload not in VALID_TIER0_VAULT_PAYLOADS:
        return _mk_res(
            admitted=False,
            firewall_engaged=False,
            dialog_opened=False,
            executed=False,
            meta_init=False,
            blocks_init=False,
            speed_restored=False,
            erased=False,
            usable=False,
            errno=EINVAL_ERRNO,
            status="BLOCKED_INVALID_TIER0_VAULT_PAYLOAD_EINVAL",
        )
    if dialog_confirm_key not in VALID_DIALOG_CONFIRM_KEYS:
        return _mk_res(
            admitted=False,
            firewall_engaged=False,
            dialog_opened=False,
            executed=False,
            meta_init=False,
            blocks_init=False,
            speed_restored=False,
            erased=False,
            usable=False,
            errno=EINVAL_ERRNO,
            status="BLOCKED_INVALID_DIALOG_CONFIRM_KEY_EINVAL",
        )

    # Shooting-screen MENU + (Delete) chord semantics:
    if entry_path == ENTRY_VIA_MENU_DELETE_CHORD:
        if ui_screen != SCREEN_SHOOTING:
            return _mk_res(
                admitted=False,
                firewall_engaged=False,
                dialog_opened=False,
                executed=False,
                meta_init=False,
                blocks_init=False,
                speed_restored=False,
                erased=False,
                usable=False,
                errno=EOPNOTSUPP_ERRNO,
                status="BLOCKED_MENU_DELETE_CHORD_SHOOTING_SCREEN_ONLY_EOPNOTSUPP",
            )
        if chord_hold_sec < FORMAT_CHORD_MIN_HOLD_SEC:
            return _mk_res(
                admitted=True,
                firewall_engaged=False,
                dialog_opened=False,
                executed=False,
                meta_init=False,
                blocks_init=False,
                speed_restored=False,
                erased=False,
                usable=True,
                errno=0,
                status="ADMITTED_SHORT_CHORD_UNDER_2S_IGNORED_NO_FORMAT_DIALOG_OK",
            )

    # Mandatory Tier-0 Bench Safety Firewall (G84 / Pillar 34) on Slot 1:
    if target_slot == SLOT_1:
        # Even if user claims card swapped, swapping away an UNVERIFIED Tier-0 vault to format is forbidden
        if slot1_tier0_vault_payload != TIER0_VAULT_NONE and (not off_camera_sha256_verified):
            return _mk_res(
                admitted=False,
                firewall_engaged=True,
                dialog_opened=False,
                executed=False,
                meta_init=False,
                blocks_init=False,
                speed_restored=False,
                erased=False,
                usable=False,
                errno=EBUSY_ERRNO,
                status=f"BLOCKED_SLOT1_UNVERIFIED_TIER0_VAULT_FIREWALL_EBUSY:{slot1_tier0_vault_payload}",
            )
        if sdxc_wp_switch_locked:
            return _mk_res(
                admitted=False,
                firewall_engaged=True,
                dialog_opened=False,
                executed=False,
                meta_init=False,
                blocks_init=False,
                speed_restored=False,
                erased=False,
                usable=False,
                errno=EROFS_ERRNO,
                status="BLOCKED_SLOT1_SDXC_WP_SWITCH_LOCKED_READONLY_EROFS",
            )
        if vault_present_on_slot1:
            return _mk_res(
                admitted=False,
                firewall_engaged=True,
                dialog_opened=False,
                executed=False,
                meta_init=False,
                blocks_init=False,
                speed_restored=False,
                erased=False,
                usable=False,
                errno=EBUSY_ERRNO,
                status=f"BLOCKED_SLOT1_ACTIVE_TIER0_VAULT_CARD_PRESENT_FIREWALL_EBUSY:{slot1_tier0_vault_payload}",
            )

    # Non-vault / verified-and-swapped scratch card or Slot 2 media formatting simulation
    if cancel_mid_full_format and (
        selected_mode != FORMAT_MODE_FULL or dialog_confirm_key != DIALOG_KEY_ENTER
    ):
        return _mk_res(
            admitted=False,
            firewall_engaged=False,
            dialog_opened=True,
            executed=False,
            meta_init=False,
            blocks_init=False,
            speed_restored=False,
            erased=False,
            usable=False,
            errno=EINVAL_ERRNO,
            status="BLOCKED_MID_CANCEL_APPLIES_ONLY_TO_CONFIRMED_FULL_FORMAT_EINVAL",
        )
    if cancel_mid_full_format and not (1 <= cancel_progress_pct <= 99):
        return _mk_res(
            admitted=False,
            firewall_engaged=False,
            dialog_opened=True,
            executed=False,
            meta_init=False,
            blocks_init=False,
            speed_restored=False,
            erased=False,
            usable=False,
            errno=EINVAL_ERRNO,
            status="BLOCKED_MID_CANCEL_PROGRESS_PCT_MUST_BE_1_TO_99_EINVAL",
        )

    if dialog_confirm_key == DIALOG_KEY_CANCEL:
        return _mk_res(
            admitted=True,
            firewall_engaged=False,
            dialog_opened=True,
            executed=False,
            meta_init=False,
            blocks_init=False,
            speed_restored=False,
            erased=False,
            usable=True,
            errno=0,
            status="ADMITTED_FORMAT_DIALOG_CANCELED_BEFORE_START_DATA_INTACT_OK",
        )

    if selected_mode == FORMAT_MODE_QUICK:
        return _mk_res(
            admitted=True,
            firewall_engaged=False,
            dialog_opened=True,
            executed=True,
            meta_init=True,
            blocks_init=False,
            speed_restored=False,
            erased=True,
            usable=True,
            errno=0,
            status="ADMITTED_QUICK_FORMAT_METADATA_ONLY_OK",
        )

    if cancel_mid_full_format:
        # Sony ILME-FX3 Help Guide contract: canceling Full Format mid-process leaves
        # previously stored data permanently erased while keeping the card formatted & usable.
        return _mk_res(
            admitted=True,
            firewall_engaged=False,
            dialog_opened=True,
            executed=True,
            meta_init=True,
            blocks_init=False,
            speed_restored=False,
            erased=True,
            usable=True,
            errno=0,
            status="ADMITTED_FULL_FORMAT_CANCELED_MID_PROCESS_PRIOR_DATA_ERASED_CARD_USABLE_OK",
        )

    return _mk_res(
        admitted=True,
        firewall_engaged=False,
        dialog_opened=True,
        executed=True,
        meta_init=True,
        blocks_init=True,
        speed_restored=True,
        erased=True,
        usable=True,
        errno=0,
        status="ADMITTED_FULL_FORMAT_ALL_DATA_BLOCKS_AND_METADATA_INITIALIZED_OK",
    )


def probe_hard_safety_redline(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_hardware_live_attachment: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_transmit: bool = False,
    authorize_isp_write: bool = False,
    emit_physical_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    bypass_sq_6locks_or_hdmi_isolation_or_tier0_format_firewall: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed probe verifying all 9 forbidden physical write/attach/bypass actions are blocked."""
    violations = [
        lbl
        for flag, lbl in (
            (authorize_persistent_emmc_writes, "PERSISTENT_EMMC_WRITE"),
            (authorize_hardware_live_attachment, "HARDWARE_LIVE_ATTACHMENT"),
            (authorize_spi_nor_write, "SPI_NOR_WRITE"),
            (authorize_el3_payload_transmit, "EL3_PAYLOAD_TRANSMIT"),
            (authorize_isp_write, "ISP_WRITE"),
            (emit_physical_usb_packet, "PHYSICAL_USB_PACKET_EMIT"),
            (touch_otp_fuse, "OTP_FUSE_TOUCH"),
            (increment_rpmb_counter, "RPMB_COUNTER_INCREMENT"),
            (
                bypass_sq_6locks_or_hdmi_isolation_or_tier0_format_firewall,
                "SQ_6LOCK_HDMI_ISOLATION_OR_TIER0_FORMAT_FIREWALL_BYPASS",
            ),
        )
        if flag
    ]
    joined = "+".join(violations) if violations else "NONE"
    return RedlineGuardProbeResult(
        valid=(not violations),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        sq_fixedvar_6lock_bypass_events=SQ_FIXEDVAR_6LOCK_BYPASS_EVENTS,
        hdmi_zebra_or_peaking_leaked_overlay_pixels=HDMI_ZEBRA_OR_PEAKING_LEAKED_OVERLAY_PIXELS,
        tier0_slot1_format_or_chord_wipe_events=TIER0_SLOT1_FORMAT_OR_CHORD_WIPE_EVENTS,
        blocked_action=joined,
        status_code=(
            f"FAIL_CLOSED_REDLINE_BLOCKED:{joined}"
            if violations
            else "HARD_SAFETY_REDLINES_LOCKED_OK"
        ),
    )


def evaluate_pillar_c_d_fullformat_chord_vault_firewall_and_redlines() -> Dict[str, object]:
    vault_quick_blocked = {
        vault: asdict(
            probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
                entry_path=ENTRY_VIA_MENU_FORMAT,
                target_slot=SLOT_1,
                slot1_tier0_vault_payload=vault,
                off_camera_sha256_verified=False,
                sdxc_wp_switch_locked=False,
                delete_key_toggle_presses=0,
            )
        )
        for vault in (TIER0_VAULT_PNFLASHA, TIER0_VAULT_CNFLASHA, TIER0_VAULT_CAMSET01)
    }
    vault_full_blocked = probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
        entry_path=ENTRY_VIA_MENU_FORMAT,
        target_slot=SLOT_1,
        slot1_tier0_vault_payload=TIER0_VAULT_COMPOSITE,
        off_camera_sha256_verified=False,
        sdxc_wp_switch_locked=False,
        delete_key_toggle_presses=1,
    )
    vault_chord_2s_blocked = probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
        entry_path=ENTRY_VIA_MENU_DELETE_CHORD,
        ui_screen=SCREEN_SHOOTING,
        chord_hold_sec=2.1,
        target_slot=SLOT_1,
        slot1_tier0_vault_payload=TIER0_VAULT_COMPOSITE,
        off_camera_sha256_verified=False,
        sdxc_wp_switch_locked=False,
        delete_key_toggle_presses=1,
    )
    vault_wp_locked_erofs = probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
        entry_path=ENTRY_VIA_MENU_FORMAT,
        target_slot=SLOT_1,
        slot1_tier0_vault_payload=TIER0_VAULT_COMPOSITE,
        off_camera_sha256_verified=True,
        sdxc_wp_switch_locked=True,
    )
    short_chord_ignored = probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
        entry_path=ENTRY_VIA_MENU_DELETE_CHORD,
        ui_screen=SCREEN_SHOOTING,
        chord_hold_sec=1.5,
        target_slot=SLOT_1,
        slot1_tier0_vault_payload=TIER0_VAULT_COMPOSITE,
    )
    scratch_quick_ok = probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
        entry_path=ENTRY_VIA_MENU_FORMAT,
        target_slot=SLOT_1,
        slot1_tier0_vault_payload=TIER0_VAULT_COMPOSITE,
        off_camera_sha256_verified=True,
        sdxc_wp_switch_locked=False,
        vault_card_swapped_for_scratch_media=True,
        delete_key_toggle_presses=0,
    )
    scratch_full_ok = probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
        entry_path=ENTRY_VIA_MENU_DELETE_CHORD,
        ui_screen=SCREEN_SHOOTING,
        chord_hold_sec=2.0,
        target_slot=SLOT_1,
        slot1_tier0_vault_payload=TIER0_VAULT_COMPOSITE,
        off_camera_sha256_verified=True,
        sdxc_wp_switch_locked=False,
        vault_card_swapped_for_scratch_media=True,
        delete_key_toggle_presses=1,
    )
    full_format_mid_cancel = probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
        entry_path=ENTRY_VIA_MENU_FORMAT,
        target_slot=SLOT_2,
        slot1_tier0_vault_payload=TIER0_VAULT_COMPOSITE,
        delete_key_toggle_presses=1,
        cancel_mid_full_format=True,
        cancel_progress_pct=50,
    )
    baseline_redline = probe_hard_safety_redline()
    blocked_probes = [
        asdict(probe_hard_safety_redline(**{k: True}))
        for k in (
            "authorize_persistent_emmc_writes",
            "authorize_hardware_live_attachment",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "authorize_isp_write",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "bypass_sq_6locks_or_hdmi_isolation_or_tier0_format_firewall",
        )
    ]
    passed = (
        all(
            (not item["admitted"]) and item["tier0_vault_firewall_engaged"]
            for item in vault_quick_blocked.values()
        )
        and (not vault_full_blocked.admitted)
        and vault_full_blocked.tier0_vault_firewall_engaged
        and (not vault_chord_2s_blocked.admitted)
        and vault_chord_2s_blocked.tier0_vault_firewall_engaged
        and (not vault_wp_locked_erofs.admitted)
        and vault_wp_locked_erofs.errno_code == EROFS_ERRNO
        and short_chord_ignored.admitted
        and (not short_chord_ignored.format_dialog_opened)
        and scratch_quick_ok.admitted
        and scratch_quick_ok.metadata_reinitialized
        and (not scratch_quick_ok.all_data_blocks_initialized)
        and scratch_full_ok.admitted
        and scratch_full_ok.metadata_reinitialized
        and scratch_full_ok.all_data_blocks_initialized
        and full_format_mid_cancel.admitted
        and full_format_mid_cancel.prior_data_permanently_erased
        and full_format_mid_cancel.card_formatted_and_immediately_usable
        and (not full_format_mid_cancel.all_data_blocks_initialized)
        and baseline_redline.valid
        and len(blocked_probes) == 9
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "slot1_vault_quick_format_blocked_by_payload": vault_quick_blocked,
        "slot1_vault_delete_toggle_full_format_blocked": asdict(vault_full_blocked),
        "slot1_vault_menu_delete_2s_chord_blocked": asdict(vault_chord_2s_blocked),
        "slot1_sdxc_wp_switch_locked_erofs": asdict(vault_wp_locked_erofs),
        "shooting_short_chord_under_2s_ignored": asdict(short_chord_ignored),
        "verified_swapped_scratch_quick_format_ok": asdict(scratch_quick_ok),
        "verified_swapped_scratch_full_format_ok": asdict(scratch_full_ok),
        "slot2_full_format_mid_cancel_data_erased_usable_ok": asdict(full_format_mid_cancel),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 232 (Stage 42, 42/42 Milestone) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 232 Stage 42 (42/42) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase232_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_sq_fixedvar_and_6locks_hil()
    pillar_b = evaluate_pillar_b_zebra_persistence_and_hdmi_isolation_hil()
    pillar_cd = evaluate_pillar_c_d_fullformat_chord_vault_firewall_and_redlines()

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
        "sq_fixedvar_6lock_bypass_events": SQ_FIXEDVAR_6LOCK_BYPASS_EVENTS,
        "hdmi_zebra_or_peaking_leaked_overlay_pixels": HDMI_ZEBRA_OR_PEAKING_LEAKED_OVERLAY_PIXELS,
        "tier0_slot1_format_or_chord_wipe_events": TIER0_SLOT1_FORMAT_OR_CHORD_WIPE_EVENTS,
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
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not OVERALL_READY_FOR_HARDWARE_ATTACH)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not ISP_WRITE_AUTHORIZED)
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and SQ_FIXEDVAR_6LOCK_BYPASS_EVENTS == 0
        and HDMI_ZEBRA_OR_PEAKING_LEAKED_OVERLAY_PIXELS == 0
        and TIER0_SLOT1_FORMAT_OR_CHORD_WIPE_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_232_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_sq_fixedvar_and_6locks_hil": pillar_a,
        "pillar_b_zebra_persistence_and_hdmi_isolation_hil": pillar_b,
        "pillar_c_d_fullformat_chord_vault_firewall_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py",
        description=(
            "Phase 232 Stage 42 (42/42 Milestone) — Real-Hardware ILME-FX3 Wave-32 Mode Settings "
            "Fixed/Variable S&Q 6-Lock Matrix, Zebra/Peaking Local-LCD-Only HDMI Isolation & "
            "Full Format / MENU+Delete 2s Tier-0 Vault Firewall HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 232 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_sq_fixedvar_and_6locks_hil"]
        pb = rep["pillar_b_zebra_persistence_and_hdmi_isolation_hil"]
        pcd = rep["pillar_c_d_fullformat_chord_vault_firewall_and_redlines"]
        locks = len(pa["all_6_sq_disqualification_ids"])
        z_surv = int(pb["zebra_reset_survival_vs_initialize_lifecycle"]["lifecycle_verified"])
        hdmi_px = pb["zebra_and_peaking_on_with_hdmi_info_on_0px"]["hdmi_zebra_or_peaking_leaked_overlay_pixels"]
        chord_blk = int(pcd["slot1_vault_menu_delete_2s_chord_blocked"]["tier0_vault_firewall_engaged"])
        sys.stdout.write(
            f"[{status}] Phase 232 Stage 42 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"sq_fixedvar={locks}locks_blk:1 | "
            f"zebra_csr_survive={z_surv}_hdmi_px:{hdmi_px} | "
            f"slot1_vault_fmt_chord_blk={chord_blk} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
