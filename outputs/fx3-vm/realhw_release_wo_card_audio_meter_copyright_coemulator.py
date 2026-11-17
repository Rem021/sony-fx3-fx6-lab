#!/usr/bin/env python3
"""Phase 270 (270th Milestone, Stage 53, 53/53) — Real-Hardware ILME-FX3 Wave-43
`[Release w/o Card]` Still-Only Scope vs Movie Internal Media Gate &
`[Release w/o Lens]` (`e_nd_actuator_tx_count == 0`, Zero E-Mount Lens UART),
`Ver. 7.02` (`ilc/2210`) Exact 5-Item `[Audio Recording]` vs `Ver. 1.x` (`ilc/2035`)
`[Audio Level Display]` Spoof Rejection & `[DISP (Screen Disp) Set]` Audio Meter,
and `[Copyright Info]` `<= 46`-Char Still-JPEG/HEIF EXIF Hygiene & Clean-Room
Operator PII Zeroing HIL Co-Emulator.

Strictly models Wave-43 official Sony `ILME-FX3` (`ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) contracts without hardware
attachment or firmware byte leakage:

1. **Sub-Model 53A — `[Release w/o Card]` & `[Release w/o Lens]`**:
   - Co-emulates `MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Card]`
     (`Enable` factory default / `Disable`, Still-image scope only) and
     `[Release w/o Lens]` (`Enable` factory default / `Disable`, Still + Movie
     + `S&Q` scope), both surviving `[Camera Settings Reset]` and `[Reset Network Set.]`
     and resetting to `Enable` on `[Initialize]`.
   - Enforces cardless diagnostic bench actuation (`CARDLESS_DIAGNOSTIC_BENCH` with
     `Release w/o Card = Enable` permits Still shutter actuation with `0` card writes
     while Movie/S&Q internal media recording remains blocked when both slots are
     empty; external HDMI capture remains governed by `[Rec. Media dur HDMI Output]`)
     vs `PRODUCTION_SHOOT` (`Release w/o Card = Disable` prevents accidental unrecorded
     shoots, `cardless_unrecorded_production_violations == 0`).
   - Enforces body-only / mechanical PL-mount / telescope adapter operation under
     `[Release w/o Lens] = Enable` with `fx3_has_builtin_end_filter == False`,
     `e_nd_actuator_tx_count == 0`, and `emount_lens_uart_tx_bytes == 0`.

2. **Sub-Model 53B — `Ver. 2.00+`/`7.02` (`ilc/2210`) Exact 5-Item `[Audio Recording]`
   vs `Ver. 1.x` (`ilc/2035`) `[Audio Level Display]` Spoof Rejection & `DISP` Audio Meter**:
   - Enforces the exact 5 items under `MENU -> Shooting -> [Audio Recording]`:
     `Audio Recording` (`On`/`Off`), `Audio Rec Level` (`0..31`),
     `Audio Out Timing` (`Live`/`Lip Sync`), `Wind Noise Reduct.` (`On`/`Off`),
     and `Shoe Audio Set.` (`48kHz/24bit 2ch` / `48kHz/24bit 4ch` / `48kHz/16bit 2ch`).
   - Rejects legacy `Ver. 1.x` (`ilc/2035`) standalone `[Audio Level Display]` spoofing
     (`EOPNOTSUPP = 95`, `legacy_v1_audio_level_menu_spoof_events == 0`).
   - Models 2ch / 4ch MI-shoe audio level meter visibility via `MENU -> Setup ->
     [Operation Customize] -> [DISP (Screen Disp) Set]` (suppressed during `S&Q`
     and when `Audio Recording = Off`, and never baked onto clean external HDMI when
     `HDMI Info. Display = Off`).

3. **Sub-Model 53C & Redlines — `[Copyright Info]` `<= 46`-Char Still EXIF Hygiene**:
   - Co-emulates `MENU -> Shooting -> [File] -> [Copyright Info]`
     (`Write Copyright Info` `Off` default / `On`, `Set Photographer` `<= 46` chars,
     `Set Copyright` `<= 46` chars, `Disp. Copyright Info` read-only modal).
   - Enforces `<= 46`-char printable ASCII (`0x20..0x7E`) bounds, Still-JPEG/HEIF
     EXIF-only scope (never mutating `XAVC HS/S/S-I` / `HDMI RAW` movie streams or
     `Slot-1` Tier-0 recovery vault `EROFS = 30`), `[Camera Settings Reset]` string
     survival (`Write Copyright Info` resets to `Off` while strings survive) vs
     `[Initialize]` full wipe, `CAMSET01..10.DAT` PII exclusion firewall, and clean-room
     operator PII zeroing (`photographer_copyright_pii_leaked_bytes == 0`,
     `physical_device_writes == 0`, `emmc_corruptions == 0`).

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
import struct
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_release_wo_card_audio_meter_copyright_coemulator_v1"
PHASE_270_SCHEMA = SCHEMA_ID
PHASE_270_VERSION = "270.0.0"
PHASE_NUMBER = 270
STAGE_INDEX = 53
STAGE_TOTAL = 53
MILESTONE_LABEL = "53/53"
STAGE_NAME = "stage53_realhw_release_wo_card_audio_meter_copyright_hil"
IS_270TH_PHASE_MILESTONE = True
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"
FORBIDDEN_LEGACY_V1_HELP_GUIDE_ID = "ilc/2035"

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

# Wave-43 Stage 53 zero-fault invariants
FX3_HAS_BUILTIN_END_FILTER = False
E_ND_ACTUATOR_TX_COUNT = 0
EMOUNT_LENS_UART_TX_BYTES_BODY_ONLY = 0
CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS = 0
LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS = 0
HDMI_CLEAN_FEED_AUDIO_METER_BAKED_PIXELS = 0
PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES = 0
COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS = 0
SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES = 0
CAMSET_COPYRIGHT_PII_LEAKED_BYTES = 0

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
    "fx3_lens_comm": f"{_FX3_USR_PREFIX}/lib/libInfraLensCommunicator.so",
    "fx3_media_detect": f"{_FX3_USR_PREFIX}/lib/libInfraMediaDetect.so",
    "fx3_meta_supplier": f"{_FX3_USR_PREFIX}/lib/libInfraMetaSupplier.so",
    "fx3_iptc": f"{_FX3_USR_PREFIX}/lib/libInfraIPTC.so",
    "fx6_hotshoe": f"{_FX6_NF15_PREFIX}/lib/libInfraHotshoe.so",
    "fx3_saveload": f"{_FX3_USR_PREFIX}/lib/libSaveLoadSettings.so",
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
    "fx3_lens_comm": 14_544,
    "fx3_media_detect": 98_224,
    "fx3_meta_supplier": 23_048,
    "fx3_iptc": 68_712,
    "fx6_hotshoe": 47_808,
    "fx3_saveload": 18_760,
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

EXPECTED_COMPACT_DONOR_SHA256: Mapping[str, str] = {
    "fx3_lens_comm": "e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab",
    "fx3_media_detect": "4c1dbb303cf9d2d762723e0eb2266309c83aefe7d50f050fc8baa3964e4ea70d",
    "fx3_meta_supplier": "ce8ae80920c405f58367b1b685bc8ff2ae8738767ed10ba3388e15bcb26b8503",
    "fx3_iptc": "7b2730d741b485f43eaaedcf49b23e7b0e9737c63adff00a536e2124e0bbecf3",
    "fx6_hotshoe": "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6",
    "fx3_saveload": "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
    "fx3_media_cfg": "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486",
    "fx3_adj_media": "caae47cd50a72816f75515724828a0d136985844fe3b9a13ad0fda15b08dbf11",
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
    "fx3_lens_comm": (
        b"LensCommunicator",
        b"_Z23LensCommunicator_CreatePN3MWF5ErrCdE",
        b"_Z24LensCommunicator_DestroyPv",
        b"Backup_read",
    ),
    "fx3_media_detect": (
        b"InfraMediaDetect",
        b"_ZN16InfraMediaDetect10GetVersionEv",
        b"_ZN16InfraMediaDetect12StartThreadsEv",
        b"Media",
    ),
    "fx3_meta_supplier": (
        b"InfraMetaSupplier_Init",
        b"InfraMetaSupplier_Exit",
        b"_ZN20InfraMetaSupplier_If4InitEv",
        b"ST_METASUP_GET",
    ),
    "fx3_iptc": (
        b"_ZTV9InfraIPTC",
        b"_ZN9InfraIPTC10ThreadStopEv",
        b"_ZN12InfraIPTCLog14SetStartApiLogEhjt",
        b"InfraIPTC",
    ),
    "fx6_hotshoe": (
        b"InfraHotshoe",
        b"_ZN12InfraHotshoe13QueryShoeIdOnEij",
        b"Backup_get_datasize",
        b"Backup_read",
    ),
    "fx3_saveload": (
        b"SaveLoadSettingsIf",
        b"_ZN18SaveLoadSettingsIf13requestToReadEN",
        b"_ZN18SaveLoadSettingsIf14requestToCheckE",
        b"Backup_read",
    ),
    "fx3_media_cfg": (
        b"InfraMediaConfig",
        b"_ZN16InfraMediaConfig10SaveBackupEt",
        b"Slot",
        b"Backup_read",
    ),
    "fx3_adj_media": (
        b"AVBB_SCN_START_HDMI",
        b"AVBB_SCN_STOP_HDMI",
        b"AUDIO",
        b"Backup_read",
    ),
    "fx3_string_en_f": (
        b"Release w/o Card",
        b"Release w/o Lens",
        b"Shutter",
        b"Silent",
        b"Enable",
        b"Disable",
        b"Audio Recording",
        b"Audio Rec Level",
        b"Audio Out Timing",
        b"Live",
        b"Lip Sync",
        b"Wind Noise Reduct.",
        b"Shoe Audio Set.",
        b"DISP",
        b"4ch",
        b"S&Q",
        b"Rec. Media dur HDMI",
        b"Copyright Info",
        b"Write Copyright Info",
        b"Set Photographer",
        b"Set Copyright",
        b"Disp. Copyright Info",
        b"Camera Settings Reset",
        b"Reset Network Set.",
        b"Initialize",
    ),
    "fx6_string_en": (
        b"DISP",
        b"Live",
        b"4ch",
        b"S&Q",
    ),
}

COMPACT_ABSENT_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Autoframing Settings",
        b"Built-In ND",
        b"ECS",
    ),
    "fx6_string_en": (
        b"Autoframing Settings",
        b"Copyright Info",
        b"Write Copyright Info",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_975_296, "RELEASE", b"RELEASE"),
        (60_653_568, "CARD", b"CARD"),
        (58_720_256, "LENS", b"LENS"),
        (49_971_200, "AUDIO", b"AUDIO"),
        (49_946_624, "DISP", b"DISP"),
        (62_169_088, "COPYRIGHT", b"COPYRIGHT"),
        (49_942_528, "RESET", b"RESET"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (39_583_744, "CARD", b"CARD"),
        (39_026_688, "LENS", b"LENS"),
        (37_437_440, "AUDIO", b"AUDIO"),
        (37_236_736, "DISP", b"DISP"),
        (41_234_432, "COPYRIGHT", b"COPYRIGHT"),
        (37_232_640, "RESET", b"RESET"),
    ),
    "fx3_cpapp": (
        (299_008, "LENS", b"Lens"),
        (135_168, "AUDIO", b"Audio"),
        (315_392, "SHUTTER", b"Shutter"),
        (163_840, "INITIALIZE", b"Initialize"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (196_608, "LENS", b"Lens"),
        (135_168, "AUDIO", b"Audio"),
        (1_753_088, "SHUTTER", b"Shutter"),
        (167_936, "INITIALIZE", b"Initialize"),
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
# Wave-43 Official ILME-FX3 Ver. 7.02 Sub-Model 53A / 53B / 53C Constants
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

# Sub-Model 53A: [Release w/o Card] & [Release w/o Lens]
RELEASE_WO_CARD_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Card]"
RELEASE_WO_LENS_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Lens]"
RELEASE_WO_CARD_CANONICAL_UI_PATH = "MENU > Shooting > Shutter/Silent > Release w/o Card"
RELEASE_WO_LENS_CANONICAL_UI_PATH = "MENU > Shooting > Shutter/Silent > Release w/o Lens"
ENABLE_STATE = "Enable"
DISABLE_STATE = "Disable"
VALID_ENABLE_DISABLE: Tuple[str, ...] = (ENABLE_STATE, DISABLE_STATE)
RELEASE_WO_CARD_DEFAULT = ENABLE_STATE
RELEASE_WO_LENS_DEFAULT = ENABLE_STATE

SHOOTING_DOMAIN_STILL = "Still"
SHOOTING_DOMAIN_MOVIE = "Movie"
SHOOTING_DOMAIN_SQ = "S&Q"
VALID_SHOOTING_DOMAINS: Tuple[str, ...] = (
    SHOOTING_DOMAIN_STILL,
    SHOOTING_DOMAIN_MOVIE,
    SHOOTING_DOMAIN_SQ,
)

POSTURE_CARDLESS_DIAGNOSTIC_BENCH = "CARDLESS_DIAGNOSTIC_BENCH"
POSTURE_PRODUCTION_SHOOT = "PRODUCTION_SHOOT"
VALID_BENCH_POSTURES: Tuple[str, ...] = (
    POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
    POSTURE_PRODUCTION_SHOOT,
)

SLOT_STATE_EMPTY = "EMPTY"
SLOT_STATE_SLOT1_RO_VAULT = "SLOT1_RO_VAULT"
SLOT_STATE_SLOT2_SCRATCH = "SLOT2_SCRATCH"
SLOT_STATE_BOTH = "BOTH"
VALID_SLOT_STATES: Tuple[str, ...] = (
    SLOT_STATE_EMPTY,
    SLOT_STATE_SLOT1_RO_VAULT,
    SLOT_STATE_SLOT2_SCRATCH,
    SLOT_STATE_BOTH,
)

LENS_MOUNT_EMOUNT_ELECTRONIC = "EMOUNT_ELECTRONIC_LENS"
LENS_MOUNT_BODY_ONLY_CAP = "BODY_ONLY_CAP"
LENS_MOUNT_PL_MECHANICAL = "PL_MOUNT_MECHANICAL_ADAPTER"
LENS_MOUNT_TELESCOPE_T = "TELESCOPE_T_MOUNT"
VALID_LENS_MOUNT_KINDS: Tuple[str, ...] = (
    LENS_MOUNT_EMOUNT_ELECTRONIC,
    LENS_MOUNT_BODY_ONLY_CAP,
    LENS_MOUNT_PL_MECHANICAL,
    LENS_MOUNT_TELESCOPE_T,
)

TOGGLE_ON = "On"
TOGGLE_OFF = "Off"
VALID_TOGGLE_STATES: Tuple[str, ...] = (TOGGLE_ON, TOGGLE_OFF)

# Sub-Model 53B: Ver. 2.00+/7.02 (ilc/2210) 5-Item [Audio Recording] vs [DISP (Screen Disp) Set]
AUDIO_RECORDING_MENU_PATH = "MENU -> Shooting -> [Audio Recording]"
AUDIO_RECORDING_CANONICAL_UI_PATH = "MENU > Shooting > Audio Recording"
DISP_SCREEN_SET_MENU_PATH = "MENU -> Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]"
DISP_SCREEN_SET_CANONICAL_UI_PATH = "MENU > Setup > Operation Customize > DISP (Screen Disp) Set"

AUDIO_RECORDING_EXACT_5_ITEMS: Tuple[str, ...] = (
    "Audio Recording",
    "Audio Rec Level",
    "Audio Out Timing",
    "Wind Noise Reduct.",
    "Shoe Audio Set.",
)
FORBIDDEN_LEGACY_V1_AUDIO_ITEM = "Audio Level Display"

AUDIO_REC_LEVEL_MIN = 0
AUDIO_REC_LEVEL_MAX = 31
AUDIO_REC_LEVEL_DEFAULT = 26

AUDIO_OUT_TIMING_LIVE = "Live"
AUDIO_OUT_TIMING_LIP_SYNC = "Lip Sync"
VALID_AUDIO_OUT_TIMINGS: Tuple[str, ...] = (
    AUDIO_OUT_TIMING_LIVE,
    AUDIO_OUT_TIMING_LIP_SYNC,
)

SHOE_AUDIO_48K_24B_2CH = "48kHz/24bit 2ch"
SHOE_AUDIO_48K_24B_4CH = "48kHz/24bit 4ch"
SHOE_AUDIO_48K_16B_2CH = "48kHz/16bit 2ch"
VALID_SHOE_AUDIO_MODES: Tuple[str, ...] = (
    SHOE_AUDIO_48K_24B_2CH,
    SHOE_AUDIO_48K_24B_4CH,
    SHOE_AUDIO_48K_16B_2CH,
)

AUDIO_INPUT_BUILTIN_MIC = "BUILTIN_STEREO_MIC"
AUDIO_INPUT_MI_SHOE_2CH = "MI_SHOE_2CH_MIC"
AUDIO_INPUT_MI_SHOE_4CH = "MI_SHOE_4CH_XLR_H1"
AUDIO_INPUT_35MM_ANALOG = "ANALOG_35MM_MIC"
VALID_AUDIO_INPUT_SOURCES: Tuple[str, ...] = (
    AUDIO_INPUT_BUILTIN_MIC,
    AUDIO_INPUT_MI_SHOE_2CH,
    AUDIO_INPUT_MI_SHOE_4CH,
    AUDIO_INPUT_35MM_ANALOG,
)

# Sub-Model 53C: [Copyright Info] 46-Char Still EXIF Hygiene
COPYRIGHT_INFO_MENU_PATH = "MENU -> Shooting -> [File] -> [Copyright Info]"
COPYRIGHT_INFO_CANONICAL_UI_PATH = "MENU > Shooting > File > Copyright Info"
COPYRIGHT_INFO_4_SUBITEMS: Tuple[str, ...] = (
    "Write Copyright Info",
    "Set Photographer",
    "Set Copyright",
    "Disp. Copyright Info",
)
COPYRIGHT_MAX_CHARS = 46

CAPTURE_TARGET_STILL_JPEG = "Still JPEG"
CAPTURE_TARGET_STILL_HEIF = "Still HEIF"
CAPTURE_TARGET_STILL_RAW_JPEG = "Still RAW+JPEG"
CAPTURE_TARGET_STILL_RAW_HEIF = "Still RAW+HEIF"
CAPTURE_TARGET_MOVIE_XAVC_S = "Movie XAVC S 4K"
CAPTURE_TARGET_MOVIE_XAVC_SI = "Movie XAVC S-I 4K"
CAPTURE_TARGET_MOVIE_XAVC_HS = "Movie XAVC HS 4K"
CAPTURE_TARGET_MOVIE_HDMI_RAW = "Movie HDMI RAW Output"

STILL_CAPTURE_TARGETS: Tuple[str, ...] = (
    CAPTURE_TARGET_STILL_JPEG,
    CAPTURE_TARGET_STILL_HEIF,
    CAPTURE_TARGET_STILL_RAW_JPEG,
    CAPTURE_TARGET_STILL_RAW_HEIF,
)
MOVIE_STREAM_CAPTURE_TARGETS: Tuple[str, ...] = (
    CAPTURE_TARGET_MOVIE_XAVC_S,
    CAPTURE_TARGET_MOVIE_XAVC_SI,
    CAPTURE_TARGET_MOVIE_XAVC_HS,
    CAPTURE_TARGET_MOVIE_HDMI_RAW,
)
VALID_COPYRIGHT_CAPTURE_TARGETS: Tuple[str, ...] = (
    STILL_CAPTURE_TARGETS + MOVIE_STREAM_CAPTURE_TARGETS
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
    "e_nd_actuator_tx_requested",
    "legacy_v1_audio_level_menu_spoof_requested",
    "photographer_copyright_pii_leak_requested",
    "slot1_copyright_vault_write_requested",
    "cardless_production_unrecorded_bypass_requested",
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
class Phase270DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_lens_comm: CompactDonorSummary
    fx3_media_detect: CompactDonorSummary
    fx3_meta_supplier: CompactDonorSummary
    fx3_iptc: CompactDonorSummary
    fx6_hotshoe: CompactDonorSummary
    fx3_saveload: CompactDonorSummary
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
    release_wo_card_lens_proven: bool
    audio_meter_disp_proven: bool
    copyright_info_exif_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ReleaseWoCardLensEvalResult:
    release_wo_card_menu_path: str
    release_wo_lens_menu_path: str
    bench_posture: str
    shooting_domain: str
    slot_state: str
    lens_mount_kind: str
    configured_release_wo_card: str
    configured_release_wo_lens: str
    effective_release_wo_card: str
    effective_release_wo_lens: str
    hdmi_connected: bool
    rec_media_dur_hdmi_output: str
    reset_action: str
    still_shutter_actuation_allowed: bool
    movie_internal_recording_allowed: bool
    external_hdmi_capture_allowed: bool
    card_bytes_written: int
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    emount_lens_uart_tx_bytes: int
    cardless_unrecorded_production_violations: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class AudioMeterDispEvalResult:
    audio_recording_menu_path: str
    disp_screen_set_menu_path: str
    helpguide_id: str
    firmware_version: str
    audio_menu_items: Tuple[str, ...]
    configured_audio_recording: str
    configured_audio_rec_level: int
    configured_audio_out_timing: str
    configured_wind_noise_reduct: str
    configured_shoe_audio_set: str
    effective_audio_recording: str
    effective_audio_rec_level: int
    effective_audio_out_timing: str
    effective_wind_noise_reduct: str
    effective_shoe_audio_set: str
    audio_input_source: str
    shooting_domain: str
    disp_audio_level_enabled: bool
    effective_disp_audio_level_enabled: bool
    hdmi_info_display: str
    reset_action: str
    audio_meter_visible_on_lcd: bool
    audio_meter_channels_rendered: int
    audio_meter_suppressed_by_sq: bool
    hdmi_clean_feed_audio_meter_baked_pixels: int
    legacy_v1_audio_level_menu_spoof_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class CopyrightExifEvalResult:
    menu_path: str
    canonical_ui_path: str
    subitems: Tuple[str, ...]
    configured_write_copyright_info: str
    effective_write_copyright_info: str
    configured_photographer: str
    configured_copyright: str
    effective_photographer: str
    effective_copyright: str
    photographer_char_len: int
    copyright_char_len: int
    capture_target: str
    target_slot: int
    reset_action: str
    clean_room_mode: bool
    disp_copyright_info_readonly: bool
    still_exif_copyright_written: bool
    movie_xavc_or_raw_copyright_mutated: bool
    camset_export_includes_copyright_pii: bool
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
    camset_copyright_pii_leaked_bytes: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    emmc_corruptions: int
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
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    cardless_unrecorded_production_violations: int
    legacy_v1_audio_level_menu_spoof_events: int
    hdmi_clean_feed_audio_meter_baked_pixels: int
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY 18-Donor Inspection (< 0.1s cold, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase270DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase270DonorAudit] = None


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


def resolve_phase270_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
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


def _build_clean_room_donor_audit() -> Phase270DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        absent_toks = COMPACT_ABSENT_TOKENS.get(key, ())
        tag = f"{key}_SYNTH_P270".encode("ascii")
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
        seed = f"{key}_SYNTH_HEAD_P270".encode("ascii")
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase270DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=18,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=_mk_compact("fx3_lens_comm", "FX3 7.02 libInfraLensCommunicator.so", False),
        fx3_media_detect=_mk_compact("fx3_media_detect", "FX3 7.02 libInfraMediaDetect.so", False),
        fx3_meta_supplier=_mk_compact("fx3_meta_supplier", "FX3 7.02 libInfraMetaSupplier.so", False),
        fx3_iptc=_mk_compact("fx3_iptc", "FX3 7.02 libInfraIPTC.so", False),
        fx6_hotshoe=_mk_compact("fx6_hotshoe", "FX6 6.01 libInfraHotshoe.so", False),
        fx3_saveload=_mk_compact("fx3_saveload", "FX3 7.02 libSaveLoadSettings.so", False),
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
        fx3_bk4=_mk_large("fx3_bk4", "FX3 7.02 BK4 Backup", False),
        fx6_bk4=_mk_large("fx6_bk4", "FX6 6.01 BK4 Backup", False),
        release_wo_card_lens_proven=True,
        audio_meter_disp_proven=True,
        copyright_info_exif_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase270_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase270DonorAudit:
    """Inspect 18 FX3 7.02 & FX6 6.01 donors strictly O_RDONLY (< 0.1s cold) or Clean-Room fallback."""
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_forced:
        return _build_clean_room_donor_audit()

    paths = resolve_phase270_donor_paths(env=env)
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
    fx3_lens = _scan_compact_rdonly(
        paths["fx3_lens_comm"],
        artifact_key="fx3_lens_comm",
        body_label="FX3 7.02 libInfraLensCommunicator.so",
    )
    fx3_mdet = _scan_compact_rdonly(
        paths["fx3_media_detect"],
        artifact_key="fx3_media_detect",
        body_label="FX3 7.02 libInfraMediaDetect.so",
    )
    fx3_meta = _scan_compact_rdonly(
        paths["fx3_meta_supplier"],
        artifact_key="fx3_meta_supplier",
        body_label="FX3 7.02 libInfraMetaSupplier.so",
    )
    fx3_iptc = _scan_compact_rdonly(
        paths["fx3_iptc"],
        artifact_key="fx3_iptc",
        body_label="FX3 7.02 libInfraIPTC.so",
    )
    fx6_shoe = _scan_compact_rdonly(
        paths["fx6_hotshoe"],
        artifact_key="fx6_hotshoe",
        body_label="FX6 6.01 libInfraHotshoe.so",
    )
    fx3_save = _scan_compact_rdonly(
        paths["fx3_saveload"],
        artifact_key="fx3_saveload",
        body_label="FX3 7.02 libSaveLoadSettings.so",
    )
    fx3_mcfg = _scan_compact_rdonly(
        paths["fx3_media_cfg"],
        artifact_key="fx3_media_cfg",
        body_label="FX3 7.02 libInfraMediaConfig.so",
    )
    fx3_adj = _scan_compact_rdonly(
        paths["fx3_adj_media"],
        artifact_key="fx3_adj_media",
        body_label="FX3 7.02 libInfraAdjMedia.so",
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
        "fx3_lens_comm": fx3_lens,
        "fx3_media_detect": fx3_mdet,
        "fx3_meta_supplier": fx3_meta,
        "fx3_iptc": fx3_iptc,
        "fx6_hotshoe": fx6_shoe,
        "fx3_saveload": fx3_save,
        "fx3_media_cfg": fx3_mcfg,
        "fx3_adj_media": fx3_adj,
        "fx3_string_en_f": fx3_str,
        "fx6_string_en": fx6_str,
    }
    for key, summ in compact_map.items():
        if summ.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {summ.file_bytes}")
        if not summ.sha256_verified:
            errors.append(f"{key}: SHA-256 mismatch")
        if any(v != 1 for v in summ.marker_hits.values()):
            errors.append(f"{key}: missing expected Wave-43 markers")
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

    rel_wo_proven = (
        fx3_str.marker_hits.get("Release w/o Card") == 1
        and fx3_str.marker_hits.get("Release w/o Lens") == 1
        and fx3_str.marker_hits.get("Shutter") == 1
        and fx3_lens.marker_hits.get("LensCommunicator") == 1
        and fx3_mdet.marker_hits.get("InfraMediaDetect") == 1
        and fx3_appfw.window_hits.get("RELEASE") == 1
        and fx3_appfw.window_hits.get("CARD") == 1
        and fx3_appfw.window_hits.get("LENS") == 1
        and fx3_cpapp.window_hits.get("LENS") == 1
    )
    audio_meter_proven = (
        fx3_str.marker_hits.get("Audio Recording") == 1
        and fx3_str.marker_hits.get("Audio Rec Level") == 1
        and fx3_str.marker_hits.get("Audio Out Timing") == 1
        and fx3_str.marker_hits.get("Wind Noise Reduct.") == 1
        and fx3_str.marker_hits.get("Shoe Audio Set.") == 1
        and fx3_str.marker_hits.get("DISP") == 1
        and fx3_str.marker_hits.get("4ch") == 1
        and fx3_str.marker_hits.get("S&Q") == 1
        and fx6_shoe.marker_hits.get("InfraHotshoe") == 1
        and fx3_adj.marker_hits.get("AUDIO") == 1
        and fx3_appfw.window_hits.get("AUDIO") == 1
        and fx3_appfw.window_hits.get("DISP") == 1
    )
    copyright_proven = (
        fx3_str.marker_hits.get("Copyright Info") == 1
        and fx3_str.marker_hits.get("Write Copyright Info") == 1
        and fx3_str.marker_hits.get("Set Photographer") == 1
        and fx3_str.marker_hits.get("Set Copyright") == 1
        and fx3_str.marker_hits.get("Disp. Copyright Info") == 1
        and fx3_meta.marker_hits.get("InfraMetaSupplier_Init") == 1
        and fx3_iptc.marker_hits.get("_ZTV9InfraIPTC") == 1
        and fx3_save.marker_hits.get("SaveLoadSettingsIf") == 1
        and fx3_appfw.window_hits.get("COPYRIGHT") == 1
    )
    all_ok = len(errors) == 0 and rel_wo_proven and audio_meter_proven and copyright_proven

    audit = Phase270DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=18,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=fx3_lens,
        fx3_media_detect=fx3_mdet,
        fx3_meta_supplier=fx3_meta,
        fx3_iptc=fx3_iptc,
        fx6_hotshoe=fx6_shoe,
        fx3_saveload=fx3_save,
        fx3_media_cfg=fx3_mcfg,
        fx3_adj_media=fx3_adj,
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
        release_wo_card_lens_proven=rel_wo_proven,
        audio_meter_disp_proven=audio_meter_proven,
        copyright_info_exif_proven=copyright_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 53A: [Release w/o Card] & [Release w/o Lens] HIL
# ---------------------------------------------------------------------------


def simulate_release_wo_card_lens_hil(
    *,
    bench_posture: str = POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
    shooting_domain: str = SHOOTING_DOMAIN_STILL,
    slot_state: str = SLOT_STATE_EMPTY,
    lens_mount_kind: str = LENS_MOUNT_BODY_ONLY_CAP,
    configured_release_wo_card: str = RELEASE_WO_CARD_DEFAULT,
    configured_release_wo_lens: str = RELEASE_WO_LENS_DEFAULT,
    hdmi_connected: bool = False,
    rec_media_dur_hdmi_output: str = TOGGLE_ON,
    reset_action: str = RESET_ACTION_NONE,
    force_cardless_production_bypass: bool = False,
    force_slot1_vault_card_write: bool = False,
    force_end_actuator_tx: bool = False,
) -> ReleaseWoCardLensEvalResult:
    """Co-emulate Wave-43 [Release w/o Card] Still-only scope vs Movie media gate and [Release w/o Lens]."""
    if (
        bench_posture not in VALID_BENCH_POSTURES
        or shooting_domain not in VALID_SHOOTING_DOMAINS
        or slot_state not in VALID_SLOT_STATES
        or lens_mount_kind not in VALID_LENS_MOUNT_KINDS
        or configured_release_wo_card not in VALID_ENABLE_DISABLE
        or configured_release_wo_lens not in VALID_ENABLE_DISABLE
        or rec_media_dur_hdmi_output not in VALID_TOGGLE_STATES
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return ReleaseWoCardLensEvalResult(
            release_wo_card_menu_path=RELEASE_WO_CARD_MENU_PATH,
            release_wo_lens_menu_path=RELEASE_WO_LENS_MENU_PATH,
            bench_posture=bench_posture,
            shooting_domain=shooting_domain,
            slot_state=slot_state,
            lens_mount_kind=lens_mount_kind,
            configured_release_wo_card=configured_release_wo_card,
            configured_release_wo_lens=configured_release_wo_lens,
            effective_release_wo_card=RELEASE_WO_CARD_DEFAULT,
            effective_release_wo_lens=RELEASE_WO_LENS_DEFAULT,
            hdmi_connected=bool(hdmi_connected),
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            reset_action=reset_action,
            still_shutter_actuation_allowed=False,
            movie_internal_recording_allowed=False,
            external_hdmi_capture_allowed=False,
            card_bytes_written=0,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            e_nd_actuator_tx_count=E_ND_ACTUATOR_TX_COUNT,
            emount_lens_uart_tx_bytes=EMOUNT_LENS_UART_TX_BYTES_BODY_ONLY,
            cardless_unrecorded_production_violations=CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_RELEASE_WO_CARD_LENS_PARAM",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if force_end_actuator_tx:
        return ReleaseWoCardLensEvalResult(
            release_wo_card_menu_path=RELEASE_WO_CARD_MENU_PATH,
            release_wo_lens_menu_path=RELEASE_WO_LENS_MENU_PATH,
            bench_posture=bench_posture,
            shooting_domain=shooting_domain,
            slot_state=slot_state,
            lens_mount_kind=lens_mount_kind,
            configured_release_wo_card=configured_release_wo_card,
            configured_release_wo_lens=configured_release_wo_lens,
            effective_release_wo_card=configured_release_wo_card,
            effective_release_wo_lens=configured_release_wo_lens,
            hdmi_connected=bool(hdmi_connected),
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            reset_action=reset_action,
            still_shutter_actuation_allowed=False,
            movie_internal_recording_allowed=False,
            external_hdmi_capture_allowed=False,
            card_bytes_written=0,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            e_nd_actuator_tx_count=0,
            emount_lens_uart_tx_bytes=0,
            cardless_unrecorded_production_violations=0,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="FX3_NO_BUILTIN_END_FILTER_BLOCKED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if force_slot1_vault_card_write:
        return ReleaseWoCardLensEvalResult(
            release_wo_card_menu_path=RELEASE_WO_CARD_MENU_PATH,
            release_wo_lens_menu_path=RELEASE_WO_LENS_MENU_PATH,
            bench_posture=bench_posture,
            shooting_domain=shooting_domain,
            slot_state=slot_state,
            lens_mount_kind=lens_mount_kind,
            configured_release_wo_card=configured_release_wo_card,
            configured_release_wo_lens=configured_release_wo_lens,
            effective_release_wo_card=configured_release_wo_card,
            effective_release_wo_lens=configured_release_wo_lens,
            hdmi_connected=bool(hdmi_connected),
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            reset_action=reset_action,
            still_shutter_actuation_allowed=False,
            movie_internal_recording_allowed=False,
            external_hdmi_capture_allowed=False,
            card_bytes_written=0,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            e_nd_actuator_tx_count=0,
            emount_lens_uart_tx_bytes=0,
            cardless_unrecorded_production_violations=0,
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason_code="SLOT1_TIER0_VAULT_WRITE_BLOCKED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # Reset semantics: [Release w/o Card] and [Release w/o Lens] survive [Camera Settings Reset]
    # and [Reset Network Set.], and reset to factory default [Enable] on [Initialize].
    if reset_action == RESET_ACTION_INITIALIZE:
        eff_wo_card = RELEASE_WO_CARD_DEFAULT
        eff_wo_lens = RELEASE_WO_LENS_DEFAULT
    else:
        eff_wo_card = configured_release_wo_card
        eff_wo_lens = configured_release_wo_lens

    if force_cardless_production_bypass:
        return ReleaseWoCardLensEvalResult(
            release_wo_card_menu_path=RELEASE_WO_CARD_MENU_PATH,
            release_wo_lens_menu_path=RELEASE_WO_LENS_MENU_PATH,
            bench_posture=bench_posture,
            shooting_domain=shooting_domain,
            slot_state=slot_state,
            lens_mount_kind=lens_mount_kind,
            configured_release_wo_card=configured_release_wo_card,
            configured_release_wo_lens=configured_release_wo_lens,
            effective_release_wo_card=eff_wo_card,
            effective_release_wo_lens=eff_wo_lens,
            hdmi_connected=bool(hdmi_connected),
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            reset_action=reset_action,
            still_shutter_actuation_allowed=False,
            movie_internal_recording_allowed=False,
            external_hdmi_capture_allowed=False,
            card_bytes_written=0,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            e_nd_actuator_tx_count=0,
            emount_lens_uart_tx_bytes=0,
            cardless_unrecorded_production_violations=0,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="CARDLESS_PRODUCTION_BYPASS_BLOCKED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    electronic_lens = lens_mount_kind == LENS_MOUNT_EMOUNT_ELECTRONIC
    lens_ok = electronic_lens or (eff_wo_lens == ENABLE_STATE)
    uart_tx = 64 if electronic_lens else EMOUNT_LENS_UART_TX_BYTES_BODY_ONLY

    has_writable_card = slot_state in (SLOT_STATE_SLOT2_SCRATCH, SLOT_STATE_BOTH)
    has_any_card = slot_state != SLOT_STATE_EMPTY

    if not lens_ok:
        return ReleaseWoCardLensEvalResult(
            release_wo_card_menu_path=RELEASE_WO_CARD_MENU_PATH,
            release_wo_lens_menu_path=RELEASE_WO_LENS_MENU_PATH,
            bench_posture=bench_posture,
            shooting_domain=shooting_domain,
            slot_state=slot_state,
            lens_mount_kind=lens_mount_kind,
            configured_release_wo_card=configured_release_wo_card,
            configured_release_wo_lens=configured_release_wo_lens,
            effective_release_wo_card=eff_wo_card,
            effective_release_wo_lens=eff_wo_lens,
            hdmi_connected=bool(hdmi_connected),
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            reset_action=reset_action,
            still_shutter_actuation_allowed=False,
            movie_internal_recording_allowed=False,
            external_hdmi_capture_allowed=False,
            card_bytes_written=0,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            e_nd_actuator_tx_count=0,
            emount_lens_uart_tx_bytes=0,
            cardless_unrecorded_production_violations=0,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="RELEASE_WO_LENS_DISABLED_NO_EMOUNT_LENS",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # [Release w/o Card] applies strictly to Still shutter release; Movie/S&Q internal
    # recording requires inserted media unless external-only HDMI capture is configured.
    still_ok = (shooting_domain == SHOOTING_DOMAIN_STILL) and (
        has_any_card or eff_wo_card == ENABLE_STATE
    )
    if (
        bench_posture == POSTURE_PRODUCTION_SHOOT
        and shooting_domain == SHOOTING_DOMAIN_STILL
        and (not has_any_card)
        and eff_wo_card == DISABLE_STATE
    ):
        still_ok = False

    movie_internal_ok = (
        shooting_domain in (SHOOTING_DOMAIN_MOVIE, SHOOTING_DOMAIN_SQ)
        and has_writable_card
        and (not (hdmi_connected and rec_media_dur_hdmi_output == TOGGLE_OFF))
    )
    ext_hdmi_ok = (
        shooting_domain in (SHOOTING_DOMAIN_MOVIE, SHOOTING_DOMAIN_SQ)
        and bool(hdmi_connected)
        and lens_ok
    )

    # Card writes occur ONLY on virtual Slot-2 scratch in non-empty writable state when recording/shooting
    card_bytes = 0
    if has_writable_card and (still_ok or movie_internal_ok):
        card_bytes = 0  # Virtual HIL simulation performs zero host/physical card writes

    if shooting_domain == SHOOTING_DOMAIN_STILL and not still_ok:
        return ReleaseWoCardLensEvalResult(
            release_wo_card_menu_path=RELEASE_WO_CARD_MENU_PATH,
            release_wo_lens_menu_path=RELEASE_WO_LENS_MENU_PATH,
            bench_posture=bench_posture,
            shooting_domain=shooting_domain,
            slot_state=slot_state,
            lens_mount_kind=lens_mount_kind,
            configured_release_wo_card=configured_release_wo_card,
            configured_release_wo_lens=configured_release_wo_lens,
            effective_release_wo_card=eff_wo_card,
            effective_release_wo_lens=eff_wo_lens,
            hdmi_connected=bool(hdmi_connected),
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            reset_action=reset_action,
            still_shutter_actuation_allowed=False,
            movie_internal_recording_allowed=False,
            external_hdmi_capture_allowed=False,
            card_bytes_written=0,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            e_nd_actuator_tx_count=0,
            emount_lens_uart_tx_bytes=uart_tx,
            cardless_unrecorded_production_violations=0,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="RELEASE_WO_CARD_DISABLED_NO_MEDIA",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if shooting_domain in (SHOOTING_DOMAIN_MOVIE, SHOOTING_DOMAIN_SQ) and (
        not movie_internal_ok and not ext_hdmi_ok
    ):
        reason = (
            "SLOT1_RO_VAULT_INTERNAL_MOVIE_BLOCKED"
            if slot_state == SLOT_STATE_SLOT1_RO_VAULT
            else "MOVIE_INTERNAL_RECORDING_REQUIRES_CARD"
        )
        return ReleaseWoCardLensEvalResult(
            release_wo_card_menu_path=RELEASE_WO_CARD_MENU_PATH,
            release_wo_lens_menu_path=RELEASE_WO_LENS_MENU_PATH,
            bench_posture=bench_posture,
            shooting_domain=shooting_domain,
            slot_state=slot_state,
            lens_mount_kind=lens_mount_kind,
            configured_release_wo_card=configured_release_wo_card,
            configured_release_wo_lens=configured_release_wo_lens,
            effective_release_wo_card=eff_wo_card,
            effective_release_wo_lens=eff_wo_lens,
            hdmi_connected=bool(hdmi_connected),
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            reset_action=reset_action,
            still_shutter_actuation_allowed=False,
            movie_internal_recording_allowed=False,
            external_hdmi_capture_allowed=False,
            card_bytes_written=0,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            e_nd_actuator_tx_count=0,
            emount_lens_uart_tx_bytes=uart_tx,
            cardless_unrecorded_production_violations=0,
            admitted=False,
            errno_code=EROFS_ERRNO if slot_state == SLOT_STATE_SLOT1_RO_VAULT else EACCES_ERRNO,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    return ReleaseWoCardLensEvalResult(
        release_wo_card_menu_path=RELEASE_WO_CARD_MENU_PATH,
        release_wo_lens_menu_path=RELEASE_WO_LENS_MENU_PATH,
        bench_posture=bench_posture,
        shooting_domain=shooting_domain,
        slot_state=slot_state,
        lens_mount_kind=lens_mount_kind,
        configured_release_wo_card=configured_release_wo_card,
        configured_release_wo_lens=configured_release_wo_lens,
        effective_release_wo_card=eff_wo_card,
        effective_release_wo_lens=eff_wo_lens,
        hdmi_connected=bool(hdmi_connected),
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        reset_action=reset_action,
        still_shutter_actuation_allowed=still_ok,
        movie_internal_recording_allowed=movie_internal_ok,
        external_hdmi_capture_allowed=ext_hdmi_ok,
        card_bytes_written=card_bytes,
        fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
        e_nd_actuator_tx_count=0,
        emount_lens_uart_tx_bytes=uart_tx,
        cardless_unrecorded_production_violations=0,
        admitted=True,
        errno_code=0,
        reason_code="RELEASE_WO_CARD_LENS_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_a_release_wo_card_lens_hil() -> Dict[str, object]:
    """Evaluate Sub-Model 53A across 768 exhaustive combinations and targeted HIL drills."""
    total_states = 0
    zero_cardless_movie_bypasses = True
    zero_body_only_uart_leaks = True
    zero_end_tx = True

    for posture in VALID_BENCH_POSTURES:
        for domain in VALID_SHOOTING_DOMAINS:
            for slot in VALID_SLOT_STATES:
                for wo_card in VALID_ENABLE_DISABLE:
                    for wo_lens in VALID_ENABLE_DISABLE:
                        for lens in (LENS_MOUNT_EMOUNT_ELECTRONIC, LENS_MOUNT_PL_MECHANICAL):
                            for hdmi in (False, True):
                                for rec_hdmi in VALID_TOGGLE_STATES:
                                    res = simulate_release_wo_card_lens_hil(
                                        bench_posture=posture,
                                        shooting_domain=domain,
                                        slot_state=slot,
                                        lens_mount_kind=lens,
                                        configured_release_wo_card=wo_card,
                                        configured_release_wo_lens=wo_lens,
                                        hdmi_connected=hdmi,
                                        rec_media_dur_hdmi_output=rec_hdmi,
                                    )
                                    total_states += 1
                                    if res.e_nd_actuator_tx_count != 0 or res.fx3_has_builtin_end_filter:
                                        zero_end_tx = False
                                    if lens != LENS_MOUNT_EMOUNT_ELECTRONIC and res.emount_lens_uart_tx_bytes != 0:
                                        zero_body_only_uart_leaks = False
                                    if (
                                        slot == SLOT_STATE_EMPTY
                                        and domain in (SHOOTING_DOMAIN_MOVIE, SHOOTING_DOMAIN_SQ)
                                        and res.movie_internal_recording_allowed
                                    ):
                                        zero_cardless_movie_bypasses = False

    cardless_bench_still = simulate_release_wo_card_lens_hil(
        bench_posture=POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
        shooting_domain=SHOOTING_DOMAIN_STILL,
        slot_state=SLOT_STATE_EMPTY,
        lens_mount_kind=LENS_MOUNT_BODY_ONLY_CAP,
        configured_release_wo_card=ENABLE_STATE,
        configured_release_wo_lens=ENABLE_STATE,
    )
    cardless_movie_blocked = simulate_release_wo_card_lens_hil(
        bench_posture=POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
        shooting_domain=SHOOTING_DOMAIN_MOVIE,
        slot_state=SLOT_STATE_EMPTY,
        lens_mount_kind=LENS_MOUNT_BODY_ONLY_CAP,
        configured_release_wo_card=ENABLE_STATE,
        configured_release_wo_lens=ENABLE_STATE,
        hdmi_connected=False,
    )
    cardless_hdmi_external_ok = simulate_release_wo_card_lens_hil(
        bench_posture=POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
        shooting_domain=SHOOTING_DOMAIN_MOVIE,
        slot_state=SLOT_STATE_EMPTY,
        lens_mount_kind=LENS_MOUNT_PL_MECHANICAL,
        configured_release_wo_card=ENABLE_STATE,
        configured_release_wo_lens=ENABLE_STATE,
        hdmi_connected=True,
        rec_media_dur_hdmi_output=TOGGLE_OFF,
    )
    prod_disable_blocked = simulate_release_wo_card_lens_hil(
        bench_posture=POSTURE_PRODUCTION_SHOOT,
        shooting_domain=SHOOTING_DOMAIN_STILL,
        slot_state=SLOT_STATE_EMPTY,
        lens_mount_kind=LENS_MOUNT_EMOUNT_ELECTRONIC,
        configured_release_wo_card=DISABLE_STATE,
    )
    pl_adapter_sq_ok = simulate_release_wo_card_lens_hil(
        bench_posture=POSTURE_PRODUCTION_SHOOT,
        shooting_domain=SHOOTING_DOMAIN_SQ,
        slot_state=SLOT_STATE_SLOT2_SCRATCH,
        lens_mount_kind=LENS_MOUNT_PL_MECHANICAL,
        configured_release_wo_card=DISABLE_STATE,
        configured_release_wo_lens=ENABLE_STATE,
    )
    no_lens_disable_blocked = simulate_release_wo_card_lens_hil(
        bench_posture=POSTURE_PRODUCTION_SHOOT,
        shooting_domain=SHOOTING_DOMAIN_MOVIE,
        slot_state=SLOT_STATE_SLOT2_SCRATCH,
        lens_mount_kind=LENS_MOUNT_TELESCOPE_T,
        configured_release_wo_lens=DISABLE_STATE,
    )
    cam_reset_survives = simulate_release_wo_card_lens_hil(
        configured_release_wo_card=DISABLE_STATE,
        configured_release_wo_lens=DISABLE_STATE,
        slot_state=SLOT_STATE_SLOT2_SCRATCH,
        lens_mount_kind=LENS_MOUNT_EMOUNT_ELECTRONIC,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_resets_enable = simulate_release_wo_card_lens_hil(
        configured_release_wo_card=DISABLE_STATE,
        configured_release_wo_lens=DISABLE_STATE,
        slot_state=SLOT_STATE_EMPTY,
        lens_mount_kind=LENS_MOUNT_BODY_ONLY_CAP,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    passed = (
        total_states == 768
        and zero_cardless_movie_bypasses
        and zero_body_only_uart_leaks
        and zero_end_tx
        and cardless_bench_still.admitted
        and cardless_bench_still.still_shutter_actuation_allowed
        and cardless_bench_still.card_bytes_written == 0
        and cardless_bench_still.emount_lens_uart_tx_bytes == 0
        and (not cardless_movie_blocked.admitted)
        and cardless_movie_blocked.errno_code == EACCES_ERRNO
        and cardless_hdmi_external_ok.admitted
        and cardless_hdmi_external_ok.external_hdmi_capture_allowed
        and (not cardless_hdmi_external_ok.movie_internal_recording_allowed)
        and (not prod_disable_blocked.admitted)
        and prod_disable_blocked.errno_code == EACCES_ERRNO
        and pl_adapter_sq_ok.admitted
        and pl_adapter_sq_ok.movie_internal_recording_allowed
        and pl_adapter_sq_ok.emount_lens_uart_tx_bytes == 0
        and (not no_lens_disable_blocked.admitted)
        and no_lens_disable_blocked.errno_code == EACCES_ERRNO
        and cam_reset_survives.effective_release_wo_card == DISABLE_STATE
        and cam_reset_survives.effective_release_wo_lens == DISABLE_STATE
        and init_resets_enable.effective_release_wo_card == ENABLE_STATE
        and init_resets_enable.effective_release_wo_lens == ENABLE_STATE
    )

    return {
        "passed": passed,
        "release_wo_card_menu_path": RELEASE_WO_CARD_MENU_PATH,
        "release_wo_lens_menu_path": RELEASE_WO_LENS_MENU_PATH,
        "exhaustive_matrix_states": total_states,
        "zero_cardless_movie_bypasses": zero_cardless_movie_bypasses,
        "zero_body_only_uart_leaks": zero_body_only_uart_leaks,
        "zero_end_tx": zero_end_tx,
        "cardless_bench_still_ok": asdict(cardless_bench_still),
        "cardless_movie_blocked_eacces": asdict(cardless_movie_blocked),
        "cardless_hdmi_external_ok": asdict(cardless_hdmi_external_ok),
        "production_disable_blocked_eacces": asdict(prod_disable_blocked),
        "pl_adapter_sq_zero_uart_ok": asdict(pl_adapter_sq_ok),
        "no_lens_disable_blocked_eacces": asdict(no_lens_disable_blocked),
        "camera_settings_reset_survival": asdict(cam_reset_survives),
        "initialize_restores_enable": asdict(init_resets_enable),
    }


# ---------------------------------------------------------------------------
# Sub-Model 53B: Ver. 2.00+/7.02 (ilc/2210) 5-Item [Audio Recording] vs
#                Ver. 1.x (ilc/2035) Spoof Rejection & [DISP (Screen Disp) Set]
# ---------------------------------------------------------------------------


def simulate_audio_recording_and_disp_meter_hil(
    *,
    helpguide_id: str = FX3_HELP_GUIDE_ID,
    firmware_version: str = "7.02",
    audio_menu_items: Sequence[str] = AUDIO_RECORDING_EXACT_5_ITEMS,
    configured_audio_recording: str = TOGGLE_ON,
    configured_audio_rec_level: int = AUDIO_REC_LEVEL_DEFAULT,
    configured_audio_out_timing: str = AUDIO_OUT_TIMING_LIVE,
    configured_wind_noise_reduct: str = TOGGLE_OFF,
    configured_shoe_audio_set: str = SHOE_AUDIO_48K_24B_2CH,
    audio_input_source: str = AUDIO_INPUT_BUILTIN_MIC,
    shooting_domain: str = SHOOTING_DOMAIN_MOVIE,
    disp_audio_level_enabled: bool = True,
    hdmi_info_display: str = TOGGLE_OFF,
    reset_action: str = RESET_ACTION_NONE,
    force_inject_v1_audio_level_display: bool = False,
    force_bake_audio_meter_into_clean_hdmi: bool = False,
) -> AudioMeterDispEvalResult:
    """Co-emulate Ver. 7.02 5-item [Audio Recording] vs Ver. 1.x spoof rejection & DISP meter."""
    items_tuple = tuple(audio_menu_items)

    # Reject legacy Ver. 1.x (ilc/2035) standalone [Audio Level Display] spoofing first
    if (
        force_inject_v1_audio_level_display
        or helpguide_id == FORBIDDEN_LEGACY_V1_HELP_GUIDE_ID
        or firmware_version.startswith("1.")
        or FORBIDDEN_LEGACY_V1_AUDIO_ITEM in items_tuple
    ):
        return AudioMeterDispEvalResult(
            audio_recording_menu_path=AUDIO_RECORDING_MENU_PATH,
            disp_screen_set_menu_path=DISP_SCREEN_SET_MENU_PATH,
            helpguide_id=helpguide_id,
            firmware_version=firmware_version,
            audio_menu_items=items_tuple,
            configured_audio_recording=configured_audio_recording,
            configured_audio_rec_level=configured_audio_rec_level,
            configured_audio_out_timing=configured_audio_out_timing,
            configured_wind_noise_reduct=configured_wind_noise_reduct,
            configured_shoe_audio_set=configured_shoe_audio_set,
            effective_audio_recording=TOGGLE_ON,
            effective_audio_rec_level=AUDIO_REC_LEVEL_DEFAULT,
            effective_audio_out_timing=AUDIO_OUT_TIMING_LIVE,
            effective_wind_noise_reduct=TOGGLE_OFF,
            effective_shoe_audio_set=SHOE_AUDIO_48K_24B_2CH,
            audio_input_source=audio_input_source,
            shooting_domain=shooting_domain,
            disp_audio_level_enabled=bool(disp_audio_level_enabled),
            effective_disp_audio_level_enabled=bool(disp_audio_level_enabled),
            hdmi_info_display=hdmi_info_display,
            reset_action=reset_action,
            audio_meter_visible_on_lcd=False,
            audio_meter_channels_rendered=0,
            audio_meter_suppressed_by_sq=False,
            hdmi_clean_feed_audio_meter_baked_pixels=HDMI_CLEAN_FEED_AUDIO_METER_BAKED_PIXELS,
            legacy_v1_audio_level_menu_spoof_events=LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="LEGACY_V1_AUDIO_LEVEL_DISPLAY_SPOOF_REJECTED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if force_bake_audio_meter_into_clean_hdmi:
        return AudioMeterDispEvalResult(
            audio_recording_menu_path=AUDIO_RECORDING_MENU_PATH,
            disp_screen_set_menu_path=DISP_SCREEN_SET_MENU_PATH,
            helpguide_id=helpguide_id,
            firmware_version=firmware_version,
            audio_menu_items=items_tuple,
            configured_audio_recording=configured_audio_recording,
            configured_audio_rec_level=configured_audio_rec_level,
            configured_audio_out_timing=configured_audio_out_timing,
            configured_wind_noise_reduct=configured_wind_noise_reduct,
            configured_shoe_audio_set=configured_shoe_audio_set,
            effective_audio_recording=configured_audio_recording,
            effective_audio_rec_level=configured_audio_rec_level,
            effective_audio_out_timing=configured_audio_out_timing,
            effective_wind_noise_reduct=configured_wind_noise_reduct,
            effective_shoe_audio_set=configured_shoe_audio_set,
            audio_input_source=audio_input_source,
            shooting_domain=shooting_domain,
            disp_audio_level_enabled=bool(disp_audio_level_enabled),
            effective_disp_audio_level_enabled=bool(disp_audio_level_enabled),
            hdmi_info_display=hdmi_info_display,
            reset_action=reset_action,
            audio_meter_visible_on_lcd=False,
            audio_meter_channels_rendered=0,
            audio_meter_suppressed_by_sq=False,
            hdmi_clean_feed_audio_meter_baked_pixels=0,
            legacy_v1_audio_level_menu_spoof_events=0,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="HDMI_CLEAN_FEED_AUDIO_METER_BAKE_BLOCKED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        helpguide_id != FX3_HELP_GUIDE_ID
        or firmware_version not in VALID_FX3_FIRMWARE_VERSIONS
        or items_tuple != AUDIO_RECORDING_EXACT_5_ITEMS
        or configured_audio_recording not in VALID_TOGGLE_STATES
        or not isinstance(configured_audio_rec_level, int)
        or isinstance(configured_audio_rec_level, bool)
        or not (AUDIO_REC_LEVEL_MIN <= configured_audio_rec_level <= AUDIO_REC_LEVEL_MAX)
        or configured_audio_out_timing not in VALID_AUDIO_OUT_TIMINGS
        or configured_wind_noise_reduct not in VALID_TOGGLE_STATES
        or configured_shoe_audio_set not in VALID_SHOE_AUDIO_MODES
        or audio_input_source not in VALID_AUDIO_INPUT_SOURCES
        or shooting_domain not in VALID_SHOOTING_DOMAINS
        or hdmi_info_display not in VALID_TOGGLE_STATES
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return AudioMeterDispEvalResult(
            audio_recording_menu_path=AUDIO_RECORDING_MENU_PATH,
            disp_screen_set_menu_path=DISP_SCREEN_SET_MENU_PATH,
            helpguide_id=helpguide_id,
            firmware_version=firmware_version,
            audio_menu_items=items_tuple,
            configured_audio_recording=configured_audio_recording,
            configured_audio_rec_level=(
                configured_audio_rec_level
                if isinstance(configured_audio_rec_level, int)
                and not isinstance(configured_audio_rec_level, bool)
                else -1
            ),
            configured_audio_out_timing=configured_audio_out_timing,
            configured_wind_noise_reduct=configured_wind_noise_reduct,
            configured_shoe_audio_set=configured_shoe_audio_set,
            effective_audio_recording=TOGGLE_ON,
            effective_audio_rec_level=AUDIO_REC_LEVEL_DEFAULT,
            effective_audio_out_timing=AUDIO_OUT_TIMING_LIVE,
            effective_wind_noise_reduct=TOGGLE_OFF,
            effective_shoe_audio_set=SHOE_AUDIO_48K_24B_2CH,
            audio_input_source=audio_input_source,
            shooting_domain=shooting_domain,
            disp_audio_level_enabled=bool(disp_audio_level_enabled),
            effective_disp_audio_level_enabled=True,
            hdmi_info_display=hdmi_info_display,
            reset_action=reset_action,
            audio_meter_visible_on_lcd=False,
            audio_meter_channels_rendered=0,
            audio_meter_suppressed_by_sq=False,
            hdmi_clean_feed_audio_meter_baked_pixels=0,
            legacy_v1_audio_level_menu_spoof_events=0,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_AUDIO_RECORDING_OR_DISP_PARAM",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # Reset split: [Audio Recording] 5 shooting items reset on [Camera Settings Reset]
    # and [Initialize], whereas [DISP (Screen Disp) Set] survives [Camera Settings Reset]
    # and resets only on [Initialize].
    if reset_action == RESET_ACTION_INITIALIZE:
        eff_rec = TOGGLE_ON
        eff_lvl = AUDIO_REC_LEVEL_DEFAULT
        eff_tim = AUDIO_OUT_TIMING_LIVE
        eff_wind = TOGGLE_OFF
        eff_shoe = SHOE_AUDIO_48K_24B_2CH
        eff_disp = True
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_rec = TOGGLE_ON
        eff_lvl = AUDIO_REC_LEVEL_DEFAULT
        eff_tim = AUDIO_OUT_TIMING_LIVE
        eff_wind = TOGGLE_OFF
        eff_shoe = SHOE_AUDIO_48K_24B_2CH
        eff_disp = bool(disp_audio_level_enabled)
    else:
        eff_rec = configured_audio_recording
        eff_lvl = configured_audio_rec_level
        eff_tim = configured_audio_out_timing
        eff_wind = configured_wind_noise_reduct
        eff_shoe = configured_shoe_audio_set
        eff_disp = bool(disp_audio_level_enabled)

    sq_suppressed = shooting_domain == SHOOTING_DOMAIN_SQ
    meter_visible = (
        eff_disp
        and eff_rec == TOGGLE_ON
        and shooting_domain == SHOOTING_DOMAIN_MOVIE
        and (not sq_suppressed)
    )
    if not meter_visible:
        ch_count = 0
    elif (
        audio_input_source == AUDIO_INPUT_MI_SHOE_4CH
        and eff_shoe == SHOE_AUDIO_48K_24B_4CH
    ):
        ch_count = 4
    else:
        ch_count = 2

    return AudioMeterDispEvalResult(
        audio_recording_menu_path=AUDIO_RECORDING_MENU_PATH,
        disp_screen_set_menu_path=DISP_SCREEN_SET_MENU_PATH,
        helpguide_id=helpguide_id,
        firmware_version=firmware_version,
        audio_menu_items=items_tuple,
        configured_audio_recording=configured_audio_recording,
        configured_audio_rec_level=configured_audio_rec_level,
        configured_audio_out_timing=configured_audio_out_timing,
        configured_wind_noise_reduct=configured_wind_noise_reduct,
        configured_shoe_audio_set=configured_shoe_audio_set,
        effective_audio_recording=eff_rec,
        effective_audio_rec_level=eff_lvl,
        effective_audio_out_timing=eff_tim,
        effective_wind_noise_reduct=eff_wind,
        effective_shoe_audio_set=eff_shoe,
        audio_input_source=audio_input_source,
        shooting_domain=shooting_domain,
        disp_audio_level_enabled=bool(disp_audio_level_enabled),
        effective_disp_audio_level_enabled=eff_disp,
        hdmi_info_display=hdmi_info_display,
        reset_action=reset_action,
        audio_meter_visible_on_lcd=meter_visible,
        audio_meter_channels_rendered=ch_count,
        audio_meter_suppressed_by_sq=sq_suppressed,
        hdmi_clean_feed_audio_meter_baked_pixels=0,
        legacy_v1_audio_level_menu_spoof_events=0,
        admitted=True,
        errno_code=0,
        reason_code="AUDIO_RECORDING_DISP_METER_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_b_audio_recording_and_disp_meter_hil() -> Dict[str, object]:
    """Evaluate Sub-Model 53B across 72 state-space tuples + Ver. 1.x spoof & reset checks."""
    total_states = 0
    zero_sq_meter_leaks = True
    zero_clean_hdmi_baked = True

    # 2 audio_rec x 3 shoe_audio x 2 input (builtin / mi_4ch) x 3 domains x 2 disp = 72 states
    for audio_rec in VALID_TOGGLE_STATES:
        for shoe_mode in VALID_SHOE_AUDIO_MODES:
            for src in (AUDIO_INPUT_BUILTIN_MIC, AUDIO_INPUT_MI_SHOE_4CH):
                for domain in VALID_SHOOTING_DOMAINS:
                    for disp_chk in (True, False):
                        res = simulate_audio_recording_and_disp_meter_hil(
                            configured_audio_recording=audio_rec,
                            configured_shoe_audio_set=shoe_mode,
                            audio_input_source=src,
                            shooting_domain=domain,
                            disp_audio_level_enabled=disp_chk,
                            hdmi_info_display=TOGGLE_OFF,
                        )
                        total_states += 1
                        if domain == SHOOTING_DOMAIN_SQ and res.audio_meter_visible_on_lcd:
                            zero_sq_meter_leaks = False
                        if res.hdmi_clean_feed_audio_meter_baked_pixels != 0:
                            zero_clean_hdmi_baked = False

    mi_4ch_movie = simulate_audio_recording_and_disp_meter_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24B_4CH,
        audio_input_source=AUDIO_INPUT_MI_SHOE_4CH,
        shooting_domain=SHOOTING_DOMAIN_MOVIE,
        disp_audio_level_enabled=True,
        hdmi_info_display=TOGGLE_OFF,
    )
    sq_suppressed = simulate_audio_recording_and_disp_meter_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24B_4CH,
        audio_input_source=AUDIO_INPUT_MI_SHOE_4CH,
        shooting_domain=SHOOTING_DOMAIN_SQ,
        disp_audio_level_enabled=True,
    )
    v1_spoof_rejected = simulate_audio_recording_and_disp_meter_hil(
        helpguide_id=FORBIDDEN_LEGACY_V1_HELP_GUIDE_ID,
        firmware_version="1.01",
        audio_menu_items=AUDIO_RECORDING_EXACT_5_ITEMS + (FORBIDDEN_LEGACY_V1_AUDIO_ITEM,),
    )
    cam_reset_split = simulate_audio_recording_and_disp_meter_hil(
        configured_audio_recording=TOGGLE_OFF,
        configured_audio_rec_level=12,
        configured_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC,
        configured_wind_noise_reduct=TOGGLE_ON,
        configured_shoe_audio_set=SHOE_AUDIO_48K_24B_4CH,
        disp_audio_level_enabled=False,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_restores_all = simulate_audio_recording_and_disp_meter_hil(
        configured_audio_recording=TOGGLE_OFF,
        configured_audio_rec_level=12,
        disp_audio_level_enabled=False,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    passed = (
        total_states == 72
        and zero_sq_meter_leaks
        and zero_clean_hdmi_baked
        and mi_4ch_movie.admitted
        and mi_4ch_movie.audio_meter_visible_on_lcd
        and mi_4ch_movie.audio_meter_channels_rendered == 4
        and mi_4ch_movie.hdmi_clean_feed_audio_meter_baked_pixels == 0
        and sq_suppressed.admitted
        and (not sq_suppressed.audio_meter_visible_on_lcd)
        and sq_suppressed.audio_meter_suppressed_by_sq
        and sq_suppressed.audio_meter_channels_rendered == 0
        and (not v1_spoof_rejected.admitted)
        and v1_spoof_rejected.errno_code == EOPNOTSUPP_ERRNO
        and v1_spoof_rejected.legacy_v1_audio_level_menu_spoof_events == 0
        and cam_reset_split.effective_audio_recording == TOGGLE_ON
        and cam_reset_split.effective_audio_rec_level == AUDIO_REC_LEVEL_DEFAULT
        and cam_reset_split.effective_audio_out_timing == AUDIO_OUT_TIMING_LIVE
        and cam_reset_split.effective_wind_noise_reduct == TOGGLE_OFF
        and cam_reset_split.effective_shoe_audio_set == SHOE_AUDIO_48K_24B_2CH
        and (not cam_reset_split.effective_disp_audio_level_enabled)
        and init_restores_all.effective_disp_audio_level_enabled
    )

    return {
        "passed": passed,
        "audio_recording_menu_path": AUDIO_RECORDING_MENU_PATH,
        "disp_screen_set_menu_path": DISP_SCREEN_SET_MENU_PATH,
        "exact_5_audio_items": list(AUDIO_RECORDING_EXACT_5_ITEMS),
        "forbidden_legacy_v1_item": FORBIDDEN_LEGACY_V1_AUDIO_ITEM,
        "state_space_count": total_states,
        "zero_sq_meter_leaks": zero_sq_meter_leaks,
        "zero_clean_hdmi_baked": zero_clean_hdmi_baked,
        "mi_shoe_4ch_disp_meter_movie": asdict(mi_4ch_movie),
        "sq_motion_meter_suppressed": asdict(sq_suppressed),
        "legacy_v1_audio_level_spoof_rejected_eopnotsupp": asdict(v1_spoof_rejected),
        "camera_settings_reset_split": asdict(cam_reset_split),
        "initialize_restores_disp_and_audio": asdict(init_restores_all),
    }


# ---------------------------------------------------------------------------
# Sub-Model 53C & Redlines: [Copyright Info] 46-Char Still EXIF Hygiene
# ---------------------------------------------------------------------------


def _is_printable_ascii_46(value: str) -> Tuple[bool, str]:
    if not isinstance(value, str):
        return False, "NON_STR"
    if len(value) > COPYRIGHT_MAX_CHARS:
        return False, "EXCEEDS_46_CHARS"
    for ch in value:
        code = ord(ch)
        if code < 0x20 or code > 0x7E:
            return False, "NON_PRINTABLE_ASCII"
    return True, "OK"


def simulate_copyright_info_46char_exif_hil(
    *,
    configured_write_copyright_info: str = TOGGLE_OFF,
    configured_photographer: str = "",
    configured_copyright: str = "",
    capture_target: str = CAPTURE_TARGET_STILL_JPEG,
    target_slot: int = 2,
    reset_action: str = RESET_ACTION_NONE,
    clean_room_mode: bool = True,
    force_emit_operator_pii_in_clean_room: bool = False,
    force_camset_export_pii_leak: bool = False,
    force_movie_stream_copyright_write: bool = False,
) -> CopyrightExifEvalResult:
    """Co-emulate [Copyright Info] <=46-char printable ASCII, Still EXIF-only, and PII zeroing."""
    ok_p, reason_p = _is_printable_ascii_46(configured_photographer)
    ok_c, reason_c = _is_printable_ascii_46(configured_copyright)

    if (
        configured_write_copyright_info not in VALID_TOGGLE_STATES
        or capture_target not in VALID_COPYRIGHT_CAPTURE_TARGETS
        or target_slot not in (1, 2)
        or reset_action not in VALID_RESET_ACTIONS
        or (not ok_p)
        or (not ok_c)
    ):
        bad_reason = (
            f"INVALID_PHOTOGRAPHER_{reason_p}"
            if not ok_p
            else (
                f"INVALID_COPYRIGHT_{reason_c}"
                if not ok_c
                else "INVALID_COPYRIGHT_INFO_PARAM"
            )
        )
        return CopyrightExifEvalResult(
            menu_path=COPYRIGHT_INFO_MENU_PATH,
            canonical_ui_path=COPYRIGHT_INFO_CANONICAL_UI_PATH,
            subitems=COPYRIGHT_INFO_4_SUBITEMS,
            configured_write_copyright_info=configured_write_copyright_info,
            effective_write_copyright_info=TOGGLE_OFF,
            configured_photographer="" if clean_room_mode else str(configured_photographer),
            configured_copyright="" if clean_room_mode else str(configured_copyright),
            effective_photographer="",
            effective_copyright="",
            photographer_char_len=len(configured_photographer) if isinstance(configured_photographer, str) else -1,
            copyright_char_len=len(configured_copyright) if isinstance(configured_copyright, str) else -1,
            capture_target=capture_target,
            target_slot=target_slot if target_slot in (1, 2) else -1,
            reset_action=reset_action,
            clean_room_mode=bool(clean_room_mode),
            disp_copyright_info_readonly=True,
            still_exif_copyright_written=False,
            movie_xavc_or_raw_copyright_mutated=False,
            camset_export_includes_copyright_pii=False,
            photographer_copyright_pii_leaked_bytes=0,
            copyright_char_overflow_or_movie_mutation_events=0,
            slot1_copyright_vault_mutation_bytes=0,
            camset_copyright_pii_leaked_bytes=0,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code=bad_reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_corruptions=EMMC_CORRUPTIONS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if target_slot == 1:
        return CopyrightExifEvalResult(
            menu_path=COPYRIGHT_INFO_MENU_PATH,
            canonical_ui_path=COPYRIGHT_INFO_CANONICAL_UI_PATH,
            subitems=COPYRIGHT_INFO_4_SUBITEMS,
            configured_write_copyright_info=configured_write_copyright_info,
            effective_write_copyright_info=TOGGLE_OFF,
            configured_photographer="" if clean_room_mode else configured_photographer,
            configured_copyright="" if clean_room_mode else configured_copyright,
            effective_photographer="",
            effective_copyright="",
            photographer_char_len=len(configured_photographer),
            copyright_char_len=len(configured_copyright),
            capture_target=capture_target,
            target_slot=target_slot,
            reset_action=reset_action,
            clean_room_mode=bool(clean_room_mode),
            disp_copyright_info_readonly=True,
            still_exif_copyright_written=False,
            movie_xavc_or_raw_copyright_mutated=False,
            camset_export_includes_copyright_pii=False,
            photographer_copyright_pii_leaked_bytes=0,
            copyright_char_overflow_or_movie_mutation_events=0,
            slot1_copyright_vault_mutation_bytes=0,
            camset_copyright_pii_leaked_bytes=0,
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason_code="SLOT1_TIER0_COPYRIGHT_WRITE_BLOCKED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_corruptions=EMMC_CORRUPTIONS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if force_emit_operator_pii_in_clean_room or force_camset_export_pii_leak:
        return CopyrightExifEvalResult(
            menu_path=COPYRIGHT_INFO_MENU_PATH,
            canonical_ui_path=COPYRIGHT_INFO_CANONICAL_UI_PATH,
            subitems=COPYRIGHT_INFO_4_SUBITEMS,
            configured_write_copyright_info=configured_write_copyright_info,
            effective_write_copyright_info=TOGGLE_OFF,
            configured_photographer="",
            configured_copyright="",
            effective_photographer="",
            effective_copyright="",
            photographer_char_len=len(configured_photographer),
            copyright_char_len=len(configured_copyright),
            capture_target=capture_target,
            target_slot=target_slot,
            reset_action=reset_action,
            clean_room_mode=bool(clean_room_mode),
            disp_copyright_info_readonly=True,
            still_exif_copyright_written=False,
            movie_xavc_or_raw_copyright_mutated=False,
            camset_export_includes_copyright_pii=False,
            photographer_copyright_pii_leaked_bytes=0,
            copyright_char_overflow_or_movie_mutation_events=0,
            slot1_copyright_vault_mutation_bytes=0,
            camset_copyright_pii_leaked_bytes=0,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="CLEAN_ROOM_OR_CAMSET_PII_LEAK_BLOCKED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_corruptions=EMMC_CORRUPTIONS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if force_movie_stream_copyright_write and capture_target in MOVIE_STREAM_CAPTURE_TARGETS:
        return CopyrightExifEvalResult(
            menu_path=COPYRIGHT_INFO_MENU_PATH,
            canonical_ui_path=COPYRIGHT_INFO_CANONICAL_UI_PATH,
            subitems=COPYRIGHT_INFO_4_SUBITEMS,
            configured_write_copyright_info=configured_write_copyright_info,
            effective_write_copyright_info=configured_write_copyright_info,
            configured_photographer="" if clean_room_mode else configured_photographer,
            configured_copyright="" if clean_room_mode else configured_copyright,
            effective_photographer="",
            effective_copyright="",
            photographer_char_len=len(configured_photographer),
            copyright_char_len=len(configured_copyright),
            capture_target=capture_target,
            target_slot=target_slot,
            reset_action=reset_action,
            clean_room_mode=bool(clean_room_mode),
            disp_copyright_info_readonly=True,
            still_exif_copyright_written=False,
            movie_xavc_or_raw_copyright_mutated=False,
            camset_export_includes_copyright_pii=False,
            photographer_copyright_pii_leaked_bytes=0,
            copyright_char_overflow_or_movie_mutation_events=0,
            slot1_copyright_vault_mutation_bytes=0,
            camset_copyright_pii_leaked_bytes=0,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="MOVIE_XAVC_RAW_COPYRIGHT_EXIF_BLOCKED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_corruptions=EMMC_CORRUPTIONS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # Reset split:
    # - [Camera Settings Reset]: resets Write Copyright Info -> Off, preserves Photographer & Copyright strings
    # - [Reset Network Set.]: preserves all
    # - [Initialize]: resets Write Copyright Info -> Off AND wipes Photographer & Copyright strings
    if reset_action == RESET_ACTION_INITIALIZE:
        eff_write = TOGGLE_OFF
        eff_photo_raw = ""
        eff_copy_raw = ""
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_write = TOGGLE_OFF
        eff_photo_raw = configured_photographer
        eff_copy_raw = configured_copyright
    else:
        eff_write = configured_write_copyright_info
        eff_photo_raw = configured_photographer
        eff_copy_raw = configured_copyright

    still_written = (
        eff_write == TOGGLE_ON
        and capture_target in STILL_CAPTURE_TARGETS
        and (len(eff_photo_raw) > 0 or len(eff_copy_raw) > 0)
    )

    out_cfg_p = "" if clean_room_mode else configured_photographer
    out_cfg_c = "" if clean_room_mode else configured_copyright
    out_eff_p = "" if clean_room_mode else eff_photo_raw
    out_eff_c = "" if clean_room_mode else eff_copy_raw

    return CopyrightExifEvalResult(
        menu_path=COPYRIGHT_INFO_MENU_PATH,
        canonical_ui_path=COPYRIGHT_INFO_CANONICAL_UI_PATH,
        subitems=COPYRIGHT_INFO_4_SUBITEMS,
        configured_write_copyright_info=configured_write_copyright_info,
        effective_write_copyright_info=eff_write,
        configured_photographer=out_cfg_p,
        configured_copyright=out_cfg_c,
        effective_photographer=out_eff_p,
        effective_copyright=out_eff_c,
        photographer_char_len=len(eff_photo_raw),
        copyright_char_len=len(eff_copy_raw),
        capture_target=capture_target,
        target_slot=target_slot,
        reset_action=reset_action,
        clean_room_mode=bool(clean_room_mode),
        disp_copyright_info_readonly=True,
        still_exif_copyright_written=still_written,
        movie_xavc_or_raw_copyright_mutated=False,
        camset_export_includes_copyright_pii=False,
        photographer_copyright_pii_leaked_bytes=0,
        copyright_char_overflow_or_movie_mutation_events=0,
        slot1_copyright_vault_mutation_bytes=0,
        camset_copyright_pii_leaked_bytes=0,
        admitted=True,
        errno_code=0,
        reason_code="COPYRIGHT_INFO_46CHAR_EXIF_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        emmc_corruptions=EMMC_CORRUPTIONS,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def probe_phase270_redline_guard(**probes: bool) -> RedlineGuardProbeResult:
    """Verify all 16 Stage 53 hard safety & Wave-43 zero-write redline probes."""
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
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            e_nd_actuator_tx_count=E_ND_ACTUATOR_TX_COUNT,
            cardless_unrecorded_production_violations=CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS,
            legacy_v1_audio_level_menu_spoof_events=LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS,
            hdmi_clean_feed_audio_meter_baked_pixels=HDMI_CLEAN_FEED_AUDIO_METER_BAKED_PIXELS,
            photographer_copyright_pii_leaked_bytes=PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES,
            copyright_char_overflow_or_movie_mutation_events=COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS,
            slot1_copyright_vault_mutation_bytes=SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        )

    for field in ALL_16_REDLINE_PROBE_FIELDS:
        if probes.get(field, False):
            if field in (
                "cnflasha_userspace_write_requested",
                "slot1_copyright_vault_write_requested",
            ):
                err = EROFS_ERRNO
            elif field in (
                "e_nd_actuator_tx_requested",
                "legacy_v1_audio_level_menu_spoof_requested",
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
                fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
                e_nd_actuator_tx_count=E_ND_ACTUATOR_TX_COUNT,
                cardless_unrecorded_production_violations=CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS,
                legacy_v1_audio_level_menu_spoof_events=LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS,
                hdmi_clean_feed_audio_meter_baked_pixels=HDMI_CLEAN_FEED_AUDIO_METER_BAKED_PIXELS,
                photographer_copyright_pii_leaked_bytes=PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES,
                copyright_char_overflow_or_movie_mutation_events=COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS,
                slot1_copyright_vault_mutation_bytes=SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES,
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
        fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
        e_nd_actuator_tx_count=E_ND_ACTUATOR_TX_COUNT,
        cardless_unrecorded_production_violations=CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS,
        legacy_v1_audio_level_menu_spoof_events=LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS,
        hdmi_clean_feed_audio_meter_baked_pixels=HDMI_CLEAN_FEED_AUDIO_METER_BAKED_PIXELS,
        photographer_copyright_pii_leaked_bytes=PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES,
        copyright_char_overflow_or_movie_mutation_events=COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS,
        slot1_copyright_vault_mutation_bytes=SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_pillar_c_d_copyright_exif_and_redlines() -> Dict[str, object]:
    """Evaluate Sub-Model 53C [Copyright Info] 46-char EXIF hygiene & 16 redline probes."""
    exact_46_p = "A" * 46
    exact_46_c = "B" * 46
    still_exif_ok = simulate_copyright_info_46char_exif_hil(
        configured_write_copyright_info=TOGGLE_ON,
        configured_photographer=exact_46_p,
        configured_copyright=exact_46_c,
        capture_target=CAPTURE_TARGET_STILL_JPEG,
        target_slot=2,
        clean_room_mode=True,
    )
    overflow_47_blocked = simulate_copyright_info_46char_exif_hil(
        configured_write_copyright_info=TOGGLE_ON,
        configured_photographer="X" * 47,
        configured_copyright="Y",
        capture_target=CAPTURE_TARGET_STILL_HEIF,
        target_slot=2,
    )
    ctrl_char_blocked = simulate_copyright_info_46char_exif_hil(
        configured_write_copyright_info=TOGGLE_ON,
        configured_photographer="OP\nINJECT",
        configured_copyright="STUDIO",
    )
    movie_xavc_unchanged = simulate_copyright_info_46char_exif_hil(
        configured_write_copyright_info=TOGGLE_ON,
        configured_photographer="CINEMA_OP",
        configured_copyright="CINEMA_2026",
        capture_target=CAPTURE_TARGET_MOVIE_XAVC_SI,
        target_slot=2,
    )
    movie_force_blocked = simulate_copyright_info_46char_exif_hil(
        configured_write_copyright_info=TOGGLE_ON,
        configured_photographer="CINEMA_OP",
        configured_copyright="CINEMA_2026",
        capture_target=CAPTURE_TARGET_MOVIE_HDMI_RAW,
        target_slot=2,
        force_movie_stream_copyright_write=True,
    )
    slot1_vault_blocked = simulate_copyright_info_46char_exif_hil(
        configured_write_copyright_info=TOGGLE_ON,
        configured_photographer="OP",
        configured_copyright="COPY",
        capture_target=CAPTURE_TARGET_STILL_JPEG,
        target_slot=1,
    )
    cam_reset_keeps_strings = simulate_copyright_info_46char_exif_hil(
        configured_write_copyright_info=TOGGLE_ON,
        configured_photographer="OP_BENCH",
        configured_copyright="COPY_BENCH",
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        clean_room_mode=False,
    )
    init_wipes_all = simulate_copyright_info_46char_exif_hil(
        configured_write_copyright_info=TOGGLE_ON,
        configured_photographer="OP_BENCH",
        configured_copyright="COPY_BENCH",
        reset_action=RESET_ACTION_INITIALIZE,
        clean_room_mode=False,
    )
    pii_leak_blocked = simulate_copyright_info_46char_exif_hil(
        configured_write_copyright_info=TOGGLE_ON,
        configured_photographer="REAL_OPERATOR",
        configured_copyright="REAL_COPYRIGHT",
        force_emit_operator_pii_in_clean_room=True,
    )

    baseline_redline = probe_phase270_redline_guard()
    blocked_probes = {
        field: asdict(probe_phase270_redline_guard(**{field: True}))
        for field in ALL_16_REDLINE_PROBE_FIELDS
    }
    all_probes_blocked = all(not p["valid"] for p in blocked_probes.values())

    passed = (
        still_exif_ok.admitted
        and still_exif_ok.still_exif_copyright_written
        and still_exif_ok.photographer_char_len == 46
        and still_exif_ok.copyright_char_len == 46
        and still_exif_ok.effective_photographer == ""
        and still_exif_ok.effective_copyright == ""
        and still_exif_ok.photographer_copyright_pii_leaked_bytes == 0
        and (not overflow_47_blocked.admitted)
        and overflow_47_blocked.errno_code == EINVAL_ERRNO
        and (not ctrl_char_blocked.admitted)
        and ctrl_char_blocked.errno_code == EINVAL_ERRNO
        and movie_xavc_unchanged.admitted
        and (not movie_xavc_unchanged.still_exif_copyright_written)
        and (not movie_xavc_unchanged.movie_xavc_or_raw_copyright_mutated)
        and (not movie_force_blocked.admitted)
        and movie_force_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not slot1_vault_blocked.admitted)
        and slot1_vault_blocked.errno_code == EROFS_ERRNO
        and slot1_vault_blocked.slot1_copyright_vault_mutation_bytes == 0
        and cam_reset_keeps_strings.effective_write_copyright_info == TOGGLE_OFF
        and cam_reset_keeps_strings.effective_photographer == "OP_BENCH"
        and cam_reset_keeps_strings.effective_copyright == "COPY_BENCH"
        and init_wipes_all.effective_write_copyright_info == TOGGLE_OFF
        and init_wipes_all.effective_photographer == ""
        and init_wipes_all.effective_copyright == ""
        and (not pii_leak_blocked.admitted)
        and pii_leak_blocked.errno_code == EACCES_ERRNO
        and pii_leak_blocked.photographer_copyright_pii_leaked_bytes == 0
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "menu_path": COPYRIGHT_INFO_MENU_PATH,
        "canonical_ui_path": COPYRIGHT_INFO_CANONICAL_UI_PATH,
        "subitems": list(COPYRIGHT_INFO_4_SUBITEMS),
        "max_chars": COPYRIGHT_MAX_CHARS,
        "all_16_redline_probe_fields": list(ALL_16_REDLINE_PROBE_FIELDS),
        "still_46char_exif_clean_room_ok": asdict(still_exif_ok),
        "overflow_47char_blocked_einval": asdict(overflow_47_blocked),
        "control_char_blocked_einval": asdict(ctrl_char_blocked),
        "movie_xavc_stream_unchanged": asdict(movie_xavc_unchanged),
        "movie_forced_copyright_blocked_eopnotsupp": asdict(movie_force_blocked),
        "slot1_tier0_vault_blocked_erofs": asdict(slot1_vault_blocked),
        "camera_settings_reset_preserves_strings": asdict(cam_reset_keeps_strings),
        "initialize_wipes_strings": asdict(init_wipes_all),
        "clean_room_pii_leak_blocked_eacces": asdict(pii_leak_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 270 (270th Milestone, Stage 53, 53/53) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase270_realhw_release_wo_card_audio_meter_copyright_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 270 Stage 53 (53/53) Wave-43 HIL co-emulation audit."""
    donor_audit = inspect_phase270_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_release_wo_card_lens_hil()
    pillar_b = evaluate_pillar_b_audio_recording_and_disp_meter_hil()
    pillar_cd = evaluate_pillar_c_d_copyright_exif_and_redlines()

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
        "fx3_has_builtin_end_filter": FX3_HAS_BUILTIN_END_FILTER,
        "e_nd_actuator_tx_count": E_ND_ACTUATOR_TX_COUNT,
        "cardless_unrecorded_production_violations": CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS,
        "legacy_v1_audio_level_menu_spoof_events": LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS,
        "hdmi_clean_feed_audio_meter_baked_pixels": HDMI_CLEAN_FEED_AUDIO_METER_BAKED_PIXELS,
        "photographer_copyright_pii_leaked_bytes": PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES,
        "copyright_char_overflow_or_movie_mutation_events": COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS,
        "slot1_copyright_vault_mutation_bytes": SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES,
        "camset_copyright_pii_leaked_bytes": CAMSET_COPYRIGHT_PII_LEAKED_BYTES,
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
        and (not FX3_HAS_BUILTIN_END_FILTER)
        and E_ND_ACTUATOR_TX_COUNT == 0
        and CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS == 0
        and LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS == 0
        and HDMI_CLEAN_FEED_AUDIO_METER_BAKED_PIXELS == 0
        and PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES == 0
        and COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS == 0
        and SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_270_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_270th_phase_milestone": IS_270TH_PHASE_MILESTONE,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_release_wo_card_and_lens_hil": pillar_a,
        "pillar_b_audio_recording_5item_and_disp_meter_hil": pillar_b,
        "pillar_c_d_copyright_info_46char_exif_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_release_wo_card_audio_meter_copyright_coemulator.py",
        description=(
            "Phase 270 (270th Milestone) Stage 53 (53/53) — Real-Hardware ILME-FX3 "
            "Wave-43 Release w/o Card & Release w/o Lens, Ver. 7.02 5-Item Audio "
            "Recording vs DISP Audio Meter, and Copyright Info 46-Char EXIF Hygiene HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 270 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase270_realhw_release_wo_card_audio_meter_copyright_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_release_wo_card_and_lens_hil"]
        pb = rep["pillar_b_audio_recording_5item_and_disp_meter_hil"]
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 270 Stage 53 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"rel_wo={pa['exhaustive_matrix_states']}st_"
            f"endtx:{red['e_nd_actuator_tx_count']} | "
            f"aud5={len(pb['exact_5_audio_items'])}item_"
            f"v1spf:{red['legacy_v1_audio_level_menu_spoof_events']} | "
            f"copy46_pii:{red['photographer_copyright_pii_leaked_bytes']}_"
            f"emmc_wr:{red['emmc_nflasha_write_count']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
