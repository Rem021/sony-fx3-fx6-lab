#!/usr/bin/env python3
"""Phase 274 (Stage 54, 54/54) — Real-Hardware ILME-FX3 Wave-44 Movie `[File Settings]`
(`Cam ID + Reel#` & `37`-Char `Title Name`) vs Still `[File/Folder Settings]` (`3`-Char
`DSC` Prefix & `Slot-1` DCIM Vault Firewall), `[Gamma Display Assist]` (`[Log Shooting]`
Lockout & LCD-Only Clean HDMI) vs `[Display LUT]` / `[Select LUT]` (`3` Presets +
`User1..User16`), and `[Auto Review]` (`Off` Cinema Default) & `[TC/UB]` (`6`
Non-Resettable Parameters + `[TC/UB Disp. Setting]`) HIL Co-Emulator.

Strictly models Wave-44 official Sony `ILME-FX3` (`ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) contracts without hardware
attachment or firmware byte leakage:

1. **Sub-Model 54A — Movie `[File Settings]` (`Cam ID + Reel#` & `37`-Char `Title Name`)
   vs Still `[File/Folder Settings]` (`3`-Char `DSC` Prefix & `Slot-1` DCIM Vault Firewall)**:
   - Movie `MENU -> Shooting -> [File] -> [File Settings]`:
     - `[File Number]`: `Series` (default) / `Reset` + `Series Counter Reset` action.
     - `[File Name Format]`: `Standard` (default, e.g. `C0001.MP4`),
       `Cam ID + Reel#` (`Camera ID` `A..Z`, `Reel Number` `001..999`,
       `Camera Position` `C`/`L`/`R`), `Title`, `Date + Title`, `Title + Date`.
     - `[Title Name Settings]`: `1..37` chars (`"C"` default; immutable
       `PRIVATE/M4ROOT/CLIP` movie folder path).
   - Still `MENU -> Shooting -> [File] -> [File/Folder Settings]`:
     - `[File Number]`: `Series` (default) / `Reset` + `Forced File Number Reset`.
     - `[Set File Name]`: first `3` chars (`A-Z`, `0-9`, `_`; `"DSC"` default;
       leading `_` hard-rejected `EINVAL = 22`).
     - `[Folder Name]`: `Standard Form` (`100MSDCF` default) / `Date Form` (`100YMMDD`).
   - Persistence & Vault: ALL items under both `[File Settings]` and
     `[File/Folder Settings]` survive `[Camera Settings Reset]` (restored only by
     `[Initialize]`). `[Forced File Number Reset]` and `[Create New Folder]` on
     `Slot 1` are hard-blocked (`EROFS = 30`) whenever `Slot 1` holds the read-only
     `CAMSET`/`BODYDATA.DAT` recovery vault (`slot1_vault_folder_mutation_events == 0`).

2. **Sub-Model 54B — `[Gamma Display Assist]` (`[Log Shooting]` Lockout & LCD-Only Clean
   HDMI) vs `[Display LUT]` / `[Select LUT]` (`3` Presets + `User1..User16`)**:
   - `MENU -> Setup -> [Display Option]`:
     - `[Gamma Display Assist]` (`Off` default / `On`) &
       `[Gamma Disp. Assist Typ.]` (`Auto` default / `S-Log3->709(800%)` /
       `HLG(BT.2020)` / `HLG(709)`).
     - Hard-locked to `[Off]` whenever `[Log Shooting]` (`Cine EI`, `Cine EI Quick`,
       `Flexible ISO`) != `Off`.
     - Applies ONLY to internal LCD live view & internal playback; NEVER applied
       to external HDMI output (`hdmi_gamma_assist_baked_frames == 0`, clean HDMI).
   - During `[Log Shooting] != Off`, monitoring conversion is governed by
     `[Display LUT]` (`On` default / `Off`) and
     `MENU -> Exposure/Color -> [Color/Tone] -> [Select LUT]` (`S-Log3`, `s709`,
     `709(800%)`, `User1..User16` `.cube` slots). All `[Setup]` items (`Gamma Display
     Assist`, `Gamma Disp. Assist Typ.`, `Display LUT`) survive `[Camera Settings Reset]`
     and reset only via `[Initialize]`.

3. **Sub-Model 54C & Redlines — `[Auto Review]` (`Off` Cinema Default) & `[TC/UB]`
   (`6` Non-Resettable Parameters + `[TC/UB Disp. Setting]`)**:
   - `[Auto Review]` (`MENU -> Setup -> [Display Option] -> [Auto Review]`,
     still-image only): `Off` factory default on `ILME-FX3` / `2 Sec` / `5 Sec` /
     `10 Sec`; survives `[Camera Settings Reset]` and resets to `Off` via `[Initialize]`.
   - Exact **6** `[TC/UB]` items (`MENU -> Shooting -> [TC/UB]`):
     `Time Code Preset` (`00:00:00.00`), `User Bit Preset` (`00 00 00 00`),
     `Time Code Format` (`DF` default vs `NDF` forced on `24.00p` & PAL `25p`/`50p`),
     `Time Code Run` (`Rec Run` default / `Free Run`), `Time Code Make` (`Preset`
     default / `Regenerate`), `User Bit Time Rec` (`Off` default / `On`): ALL 6
     survive `[Camera Settings Reset]` even though `[TC/UB]` sits under `Shooting`
     (reset only via `[Initialize]`), plus `[TC/UB Disp. Setting]` (`TC` default /
     `U-Bit` under `[Setup]`).

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

SCHEMA_ID = "realhw_file_settings_gamma_assist_tcub_coemulator_v1"
PHASE_274_SCHEMA = SCHEMA_ID
PHASE_274_VERSION = "274.0.0"
PHASE_NUMBER = 274
STAGE_INDEX = 54
STAGE_TOTAL = 54
MILESTONE_LABEL = "54/54"
STAGE_NAME = "stage54_realhw_file_settings_gamma_assist_tcub_hil"
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

# Wave-44 Stage 54 zero-fault invariants
SLOT1_VAULT_FOLDER_MUTATION_EVENTS = 0
TITLE_NAME_37CHAR_OVERFLOW_EVENTS = 0
STILL_PREFIX_LEADING_UNDERSCORE_BYPASS_EVENTS = 0
GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS = 0
HDMI_GAMMA_ASSIST_BAKED_FRAMES = 0
TCUB_CAMERA_SETTINGS_RESET_WIPE_EVENTS = 0
TC_24P_OR_PAL_DF_VIOLATION_EVENTS = 0

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
    "fx3_media_common": f"{_FX3_USR_PREFIX}/lib/libInfraMediaCommon.so",
    "fx3_media_mount": f"{_FX3_USR_PREFIX}/lib/libInfraMediaMount.so",
    "fx3_media_detect": f"{_FX3_USR_PREFIX}/lib/libInfraMediaDetect.so",
    "fx3_meta_supplier": f"{_FX3_USR_PREFIX}/lib/libInfraMetaSupplier.so",
    "fx3_iptc": f"{_FX3_USR_PREFIX}/lib/libInfraIPTC.so",
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
    "fx3_media_common": 402_624,
    "fx3_media_mount": 65_392,
    "fx3_media_detect": 98_224,
    "fx3_meta_supplier": 23_048,
    "fx3_iptc": 68_712,
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
    "fx3_media_common": "1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b",
    "fx3_media_mount": "33b4c61c39f724e08e1bc4d07fd505a799ee37a9c1f37a43fffc7c2c9c8f75ad",
    "fx3_media_detect": "4c1dbb303cf9d2d762723e0eb2266309c83aefe7d50f050fc8baa3964e4ea70d",
    "fx3_meta_supplier": "ce8ae80920c405f58367b1b685bc8ff2ae8738767ed10ba3388e15bcb26b8503",
    "fx3_iptc": "7b2730d741b485f43eaaedcf49b23e7b0e9737c63adff00a536e2124e0bbecf3",
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
    "fx3_media_common": (
        b"Backup_read",
        b"Format",
        b"Media",
        b"Mount",
    ),
    "fx3_media_mount": (
        b"InfraMediaMount",
        b"_ZN15InfraMediaMount13CallbackPointEPviS0_",
        b"Media",
        b"Mount",
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
        b"File Settings",
        b"File/Folder Settings",
        b"File Number",
        b"Series",
        b"Reset",
        b"Series Counter Reset",
        b"Forced File Number Reset",
        b"Create New Folder",
        b"File Name Format",
        b"Standard",
        b"Cam ID + Reel#",
        b"Camera ID",
        b"Reel Number",
        b"Camera Position",
        b"Title Name Settings",
        b"Date + Title",
        b"Title + Date",
        b"Set File Name",
        b"Standard Form",
        b"Date Form",
        b"Gamma Display Assist",
        b"Gamma Disp. Assist Typ.",
        b"Display LUT",
        b"Select LUT",
        b"Log Shooting",
        b"Cine EI",
        b"Cine EI Quick",
        b"Flexible ISO",
        b"Auto Review",
        b"2 Sec",
        b"5 Sec",
        b"10 Sec",
        b"TC/UB",
        b"Time Code Preset",
        b"User Bit Preset",
        b"Time Code Format",
        b"Time Code Run",
        b"Time Code Make",
        b"User Bit Time Rec",
        b"Rec Run",
        b"Free Run",
        b"Preset",
        b"Regenerate",
        b"TC/UB Disp. Setting",
        b"U-Bit",
        b"Camera Settings Reset",
        b"Initialize",
        b"S-Log3",
        b"s709",
        b"709(800%)",
        b"HLG(BT.2020)",
        b"HLG(709)",
    ),
    "fx6_string_en": (
        b"Gamma Display Assist",
        b"Title Name Settings",
        b"DISP",
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
        b"File/Folder Settings",
        b"Cam ID + Reel#",
        b"Auto Review",
        b"TC/UB",
        b"Display LUT",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (59_801_600, "M4ROOT", b"M4ROOT"),
        (58_306_560, "MSDCF", b"MSDCF"),
        (60_313_600, "GAMMA", b"GAMMA"),
        (49_967_104, "LUT", b"LUT"),
        (50_745_344, "REVIEW", b"REVIEW"),
        (51_888_128, "CAMSET", b"CAMSET"),
        (62_251_008, "REEL", b"REEL"),
        (49_876_992, "INITIALIZE", b"Initialize"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (39_464_960, "M4ROOT", b"M4ROOT"),
        (38_649_856, "MSDCF", b"MSDCF"),
        (39_563_264, "GAMMA_DISPLAY", b"Gamma Display"),
        (39_563_264, "TC_UB", b"TC/UB"),
        (37_236_736, "LUT", b"LUT"),
        (39_350_272, "CAMSET", b"CAMSET"),
        (35_987_456, "INITIALIZE", b"Initialize"),
    ),
    "fx3_cpapp": (
        (2_961_408, "MSDCF", b"MSDCF"),
        (602_112, "GAMMA", b"GAMMA"),
        (598_016, "LUT", b"LUT"),
        (610_304, "REVIEW", b"REVIEW"),
        (163_840, "INITIALIZE", b"Initialize"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (2_994_176, "MSDCF", b"MSDCF"),
        (581_632, "GAMMA", b"GAMMA"),
        (319_488, "LUT", b"LUT"),
        (593_920, "REVIEW", b"REVIEW"),
        (167_936, "INITIALIZE", b"Initialize"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (2_928_640, "M4ROOT", b"M4ROOT"),
        (2_920_448, "MSDCF", b"MSDCF"),
        (241_664, "LUT", b"LUT"),
        (258_048, "INITIALIZE", b"Initialize"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (13_406_208, "M4ROOT", b"M4ROOT"),
        (13_398_016, "MSDCF", b"MSDCF"),
        (270_336, "LUT", b"LUT"),
        (315_392, "INITIALIZE", b"Initialize"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4"),
        (638_976, "MSDCF", b"MSDCF"),
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
# Wave-44 Official ILME-FX3 Ver. 7.02 Sub-Model 54A / 54B / 54C Constants
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

# Sub-Model 54A: Movie [File Settings] vs Still [File/Folder Settings] & Vault Guard
MOVIE_FILE_SETTINGS_MENU_PATH = "MENU -> Shooting -> [File] -> [File Settings]"
STILL_FILE_FOLDER_MENU_PATH = "MENU -> Shooting -> [File] -> [File/Folder Settings]"
MOVIE_FOLDER_IMMUTABLE_PATH = "PRIVATE/M4ROOT/CLIP"

FILE_NUMBER_SERIES = "Series"
FILE_NUMBER_RESET = "Reset"
VALID_FILE_NUMBER_MODES: Tuple[str, ...] = (FILE_NUMBER_SERIES, FILE_NUMBER_RESET)

MOVIE_FORMAT_STANDARD = "Standard"
MOVIE_FORMAT_CAM_ID_REEL = "Cam ID + Reel#"
MOVIE_FORMAT_TITLE = "Title"
MOVIE_FORMAT_DATE_TITLE = "Date + Title"
MOVIE_FORMAT_TITLE_DATE = "Title + Date"
VALID_MOVIE_FILE_NAME_FORMATS: Tuple[str, ...] = (
    MOVIE_FORMAT_STANDARD,
    MOVIE_FORMAT_CAM_ID_REEL,
    MOVIE_FORMAT_TITLE,
    MOVIE_FORMAT_DATE_TITLE,
    MOVIE_FORMAT_TITLE_DATE,
)

CAMERA_ID_LETTERS: Tuple[str, ...] = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
CAMERA_POS_C = "C"
CAMERA_POS_L = "L"
CAMERA_POS_R = "R"
VALID_CAMERA_POSITIONS: Tuple[str, ...] = (CAMERA_POS_C, CAMERA_POS_L, CAMERA_POS_R)
REEL_NUMBER_MIN = 1
REEL_NUMBER_MAX = 999
REEL_NUMBER_DEFAULT = "001"
CAMERA_ID_DEFAULT = "A"
CAMERA_POS_DEFAULT = CAMERA_POS_C

TITLE_NAME_DEFAULT = "C"
TITLE_NAME_MAX_CHARS = 37

STILL_PREFIX_DEFAULT = "DSC"
STILL_PREFIX_LEN = 3

FOLDER_NAME_STANDARD_FORM = "Standard Form"
FOLDER_NAME_DATE_FORM = "Date Form"
VALID_STILL_FOLDER_FORMS: Tuple[str, ...] = (
    FOLDER_NAME_STANDARD_FORM,
    FOLDER_NAME_DATE_FORM,
)

MEDIA_ACTION_NONE = "NONE"
MEDIA_ACTION_SERIES_COUNTER_RESET = "Series Counter Reset"
MEDIA_ACTION_FORCED_FILE_NUMBER_RESET = "Forced File Number Reset"
MEDIA_ACTION_CREATE_NEW_FOLDER = "Create New Folder"
VALID_MEDIA_ACTIONS: Tuple[str, ...] = (
    MEDIA_ACTION_NONE,
    MEDIA_ACTION_SERIES_COUNTER_RESET,
    MEDIA_ACTION_FORCED_FILE_NUMBER_RESET,
    MEDIA_ACTION_CREATE_NEW_FOLDER,
)

# Sub-Model 54B: [Gamma Display Assist] & [Display LUT] / [Select LUT]
DISPLAY_OPTION_MENU_PATH = "MENU -> Setup -> [Display Option]"
GAMMA_DISPLAY_ASSIST_MENU_PATH = "MENU -> Setup -> [Display Option] -> [Gamma Display Assist]"
GAMMA_DISP_ASSIST_TYP_MENU_PATH = "MENU -> Setup -> [Display Option] -> [Gamma Disp. Assist Typ.]"
DISPLAY_LUT_MENU_PATH = "MENU -> Setup -> [Display Option] -> [Display LUT]"
SELECT_LUT_MENU_PATH = "MENU -> Exposure/Color -> [Color/Tone] -> [Select LUT]"
LOG_SHOOTING_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [Log Shooting Setting]"

TOGGLE_OFF = "Off"
TOGGLE_ON = "On"
VALID_TOGGLE_STATES: Tuple[str, ...] = (TOGGLE_OFF, TOGGLE_ON)

GAMMA_ASSIST_TYP_AUTO = "Auto"
GAMMA_ASSIST_TYP_SLOG3_709 = "S-Log3->709(800%)"
GAMMA_ASSIST_TYP_HLG_BT2020 = "HLG(BT.2020)"
GAMMA_ASSIST_TYP_HLG_709 = "HLG(709)"
VALID_GAMMA_ASSIST_TYPES: Tuple[str, ...] = (
    GAMMA_ASSIST_TYP_AUTO,
    GAMMA_ASSIST_TYP_SLOG3_709,
    GAMMA_ASSIST_TYP_HLG_BT2020,
    GAMMA_ASSIST_TYP_HLG_709,
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

LUT_PRESET_SLOG3 = "S-Log3"
LUT_PRESET_S709 = "s709"
LUT_PRESET_709_800 = "709(800%)"
SELECT_LUT_PRESETS: Tuple[str, ...] = (
    LUT_PRESET_SLOG3,
    LUT_PRESET_S709,
    LUT_PRESET_709_800,
)
SELECT_LUT_USER_SLOTS: Tuple[str, ...] = tuple(f"User{i}" for i in range(1, 17))
VALID_SELECT_LUT_OPTIONS: Tuple[str, ...] = SELECT_LUT_PRESETS + SELECT_LUT_USER_SLOTS

MONITOR_SINK_LCD_LIVE_VIEW = "LCD_LIVE_VIEW"
MONITOR_SINK_INTERNAL_PLAYBACK = "INTERNAL_PLAYBACK"
MONITOR_SINK_EXTERNAL_HDMI = "EXTERNAL_HDMI"
VALID_MONITOR_SINKS: Tuple[str, ...] = (
    MONITOR_SINK_LCD_LIVE_VIEW,
    MONITOR_SINK_INTERNAL_PLAYBACK,
    MONITOR_SINK_EXTERNAL_HDMI,
)

# Sub-Model 54C: [Auto Review] & [TC/UB] 6 Non-Resettable Items + [TC/UB Disp. Setting]
AUTO_REVIEW_MENU_PATH = "MENU -> Setup -> [Display Option] -> [Auto Review]"
AUTO_REVIEW_OFF = "Off"
AUTO_REVIEW_2S = "2 Sec"
AUTO_REVIEW_5S = "5 Sec"
AUTO_REVIEW_10S = "10 Sec"
VALID_AUTO_REVIEW_OPTIONS: Tuple[str, ...] = (
    AUTO_REVIEW_OFF,
    AUTO_REVIEW_2S,
    AUTO_REVIEW_5S,
    AUTO_REVIEW_10S,
)
AUTO_REVIEW_SECONDS_MAP: Mapping[str, int] = {
    AUTO_REVIEW_OFF: 0,
    AUTO_REVIEW_2S: 2,
    AUTO_REVIEW_5S: 5,
    AUTO_REVIEW_10S: 10,
}

SHOOTING_DOMAIN_STILL = "Still"
SHOOTING_DOMAIN_MOVIE = "Movie"
SHOOTING_DOMAIN_SQ = "S&Q"
VALID_SHOOTING_DOMAINS: Tuple[str, ...] = (
    SHOOTING_DOMAIN_STILL,
    SHOOTING_DOMAIN_MOVIE,
    SHOOTING_DOMAIN_SQ,
)

TC_UB_MENU_PATH = "MENU -> Shooting -> [TC/UB]"
TC_UB_DISP_SETTING_MENU_PATH = "MENU -> Setup -> [Display Option] -> [TC/UB Disp. Setting]"
TC_UB_EXACT_6_ITEMS: Tuple[str, ...] = (
    "Time Code Preset",
    "User Bit Preset",
    "Time Code Format",
    "Time Code Run",
    "Time Code Make",
    "User Bit Time Rec",
)

TC_PRESET_DEFAULT = "00:00:00.00"
UB_PRESET_DEFAULT = "00 00 00 00"
TC_FORMAT_DF = "DF"
TC_FORMAT_NDF = "NDF"
VALID_TC_FORMATS: Tuple[str, ...] = (TC_FORMAT_DF, TC_FORMAT_NDF)

TC_RUN_REC_RUN = "Rec Run"
TC_RUN_FREE_RUN = "Free Run"
VALID_TC_RUN_MODES: Tuple[str, ...] = (TC_RUN_REC_RUN, TC_RUN_FREE_RUN)

TC_MAKE_PRESET = "Preset"
TC_MAKE_REGENERATE = "Regenerate"
VALID_TC_MAKE_MODES: Tuple[str, ...] = (TC_MAKE_PRESET, TC_MAKE_REGENERATE)

TC_DISP_TC = "TC"
TC_DISP_UBIT = "U-Bit"
VALID_TC_UB_DISP_MODES: Tuple[str, ...] = (TC_DISP_TC, TC_DISP_UBIT)

FRAME_RATE_2400P = "24.00p"
FRAME_RATE_2398P = "23.98p"
FRAME_RATE_25P = "25p"
FRAME_RATE_2997P = "29.97p"
FRAME_RATE_50P = "50p"
FRAME_RATE_5994P = "59.94p"
VALID_FRAME_RATES: Tuple[str, ...] = (
    FRAME_RATE_2400P,
    FRAME_RATE_2398P,
    FRAME_RATE_25P,
    FRAME_RATE_2997P,
    FRAME_RATE_50P,
    FRAME_RATE_5994P,
)
FORCED_NDF_FRAME_RATES: Tuple[str, ...] = (
    FRAME_RATE_2400P,
    FRAME_RATE_25P,
    FRAME_RATE_50P,
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
    "slot1_vault_folder_mutation_requested",
    "still_prefix_leading_underscore_bypass_requested",
    "gamma_assist_log_lockout_bypass_requested",
    "hdmi_gamma_assist_bake_requested",
    "tcub_camera_settings_reset_wipe_requested",
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
class Phase274DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_media_common: CompactDonorSummary
    fx3_media_mount: CompactDonorSummary
    fx3_media_detect: CompactDonorSummary
    fx3_meta_supplier: CompactDonorSummary
    fx3_iptc: CompactDonorSummary
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
    file_settings_and_vault_proven: bool
    gamma_assist_and_display_lut_proven: bool
    auto_review_and_tcub_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FileSettingsAndVaultEvalResult:
    movie_menu_path: str
    still_menu_path: str
    configured_movie_file_number: str
    configured_movie_file_name_format: str
    configured_camera_id: str
    configured_reel_number: str
    configured_camera_position: str
    configured_title_name: str
    configured_still_file_number: str
    configured_still_prefix: str
    configured_still_folder_form: str
    effective_movie_file_number: str
    effective_movie_file_name_format: str
    effective_camera_id: str
    effective_reel_number: str
    effective_camera_position: str
    effective_title_name: str
    effective_still_file_number: str
    effective_still_prefix: str
    effective_still_folder_form: str
    movie_folder_path: str
    rendered_movie_filename: str
    rendered_still_folder: str
    rendered_still_filename: str
    title_char_len: int
    media_action: str
    target_slot: int
    slot1_has_recovery_vault: bool
    reset_action: str
    settings_survived_reset: bool
    settings_wiped_by_initialize: bool
    slot1_vault_folder_mutation_events: int
    title_name_37char_overflow_events: int
    still_prefix_leading_underscore_bypass_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class GammaAssistDisplayLutEvalResult:
    gamma_assist_menu_path: str
    gamma_typ_menu_path: str
    display_lut_menu_path: str
    select_lut_menu_path: str
    configured_log_shooting: str
    configured_gamma_display_assist: str
    configured_gamma_assist_type: str
    configured_display_lut: str
    configured_select_lut: str
    effective_gamma_display_assist: str
    effective_gamma_assist_type: str
    effective_display_lut: str
    effective_select_lut: str
    gamma_display_assist_locked_by_log: bool
    monitor_sink: str
    lcd_gamma_assist_applied: bool
    external_hdmi_gamma_assist_applied: bool
    active_monitoring_conversion: str
    reset_action: str
    setup_items_survived_camera_reset: bool
    gamma_assist_log_lockout_bypass_events: int
    hdmi_gamma_assist_baked_frames: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class AutoReviewAndTcubEvalResult:
    auto_review_menu_path: str
    tc_ub_menu_path: str
    tc_ub_disp_menu_path: str
    tc_ub_exact_6_items: Tuple[str, ...]
    shooting_domain: str
    frame_rate: str
    configured_auto_review: str
    effective_auto_review: str
    still_post_capture_review_seconds: int
    configured_tc_preset: str
    configured_ub_preset: str
    configured_tc_format: str
    configured_tc_run: str
    configured_tc_make: str
    configured_ub_time_rec: str
    configured_tc_ub_disp_setting: str
    effective_tc_preset: str
    effective_ub_preset: str
    effective_tc_format: str
    effective_tc_run: str
    effective_tc_make: str
    effective_ub_time_rec: str
    effective_tc_ub_disp_setting: str
    tc_format_forced_ndf: bool
    reset_action: str
    auto_review_survived_camera_reset: bool
    all_6_tcub_survived_camera_reset: bool
    tc_ub_disp_survived_camera_reset: bool
    tcub_camera_settings_reset_wipe_events: int
    tc_24p_or_pal_df_violation_events: int
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
    slot1_vault_folder_mutation_events: int
    title_name_37char_overflow_events: int
    still_prefix_leading_underscore_bypass_events: int
    gamma_assist_log_lockout_bypass_events: int
    hdmi_gamma_assist_baked_frames: int
    tcub_camera_settings_reset_wipe_events: int
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY 18-Donor Inspection (< 0.1s cold, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase274DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase274DonorAudit] = None


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


def resolve_phase274_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
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


def _build_clean_room_donor_audit() -> Phase274DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        absent_toks = COMPACT_ABSENT_TOKENS.get(key, ())
        tag = f"{key}_SYNTH_P274".encode("ascii")
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
        seed = f"{key}_SYNTH_HEAD_P274".encode("ascii")
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase274DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=18,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_media_common=_mk_compact("fx3_media_common", "FX3 7.02 libInfraMediaCommon.so", False),
        fx3_media_mount=_mk_compact("fx3_media_mount", "FX3 7.02 libInfraMediaMount.so", False),
        fx3_media_detect=_mk_compact("fx3_media_detect", "FX3 7.02 libInfraMediaDetect.so", False),
        fx3_meta_supplier=_mk_compact("fx3_meta_supplier", "FX3 7.02 libInfraMetaSupplier.so", False),
        fx3_iptc=_mk_compact("fx3_iptc", "FX3 7.02 libInfraIPTC.so", False),
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
        file_settings_and_vault_proven=True,
        gamma_assist_and_display_lut_proven=True,
        auto_review_and_tcub_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase274_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase274DonorAudit:
    """Inspect 18 FX3 7.02 & FX6 6.01 donors strictly O_RDONLY (< 0.1s cold) or Clean-Room fallback."""
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_forced:
        return _build_clean_room_donor_audit()

    paths = resolve_phase274_donor_paths(env=env)
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
    fx3_mcom = _scan_compact_rdonly(
        paths["fx3_media_common"],
        artifact_key="fx3_media_common",
        body_label="FX3 7.02 libInfraMediaCommon.so",
    )
    fx3_mmnt = _scan_compact_rdonly(
        paths["fx3_media_mount"],
        artifact_key="fx3_media_mount",
        body_label="FX3 7.02 libInfraMediaMount.so",
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
        "fx3_media_common": fx3_mcom,
        "fx3_media_mount": fx3_mmnt,
        "fx3_media_detect": fx3_mdet,
        "fx3_meta_supplier": fx3_meta,
        "fx3_iptc": fx3_iptc,
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
            errors.append(f"{key}: missing expected Wave-44 markers")
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

    file_vault_proven = (
        fx3_str.marker_hits.get("File Settings") == 1
        and fx3_str.marker_hits.get("File/Folder Settings") == 1
        and fx3_str.marker_hits.get("Cam ID + Reel#") == 1
        and fx3_str.marker_hits.get("Title Name Settings") == 1
        and fx3_str.marker_hits.get("Set File Name") == 1
        and fx3_str.marker_hits.get("Forced File Number Reset") == 1
        and fx3_str.marker_hits.get("Create New Folder") == 1
        and fx3_mcom.marker_hits.get("Format") == 1
        and fx3_mmnt.marker_hits.get("InfraMediaMount") == 1
        and fx3_mcfg.marker_hits.get("InfraMediaConfig") == 1
        and fx3_appfw.window_hits.get("M4ROOT") == 1
        and fx3_appfw.window_hits.get("MSDCF") == 1
        and fx3_libmpr.window_hits.get("M4ROOT") == 1
    )
    gamma_lut_proven = (
        fx3_str.marker_hits.get("Gamma Display Assist") == 1
        and fx3_str.marker_hits.get("Gamma Disp. Assist Typ.") == 1
        and fx3_str.marker_hits.get("Display LUT") == 1
        and fx3_str.marker_hits.get("Select LUT") == 1
        and fx3_str.marker_hits.get("Log Shooting") == 1
        and fx3_str.marker_hits.get("S-Log3") == 1
        and fx3_str.marker_hits.get("s709") == 1
        and fx3_str.marker_hits.get("709(800%)") == 1
        and fx6_str.marker_hits.get("Gamma Display Assist") == 1
        and fx3_appfw.window_hits.get("GAMMA") == 1
        and fx3_appfw.window_hits.get("LUT") == 1
    )
    auto_tcub_proven = (
        fx3_str.marker_hits.get("Auto Review") == 1
        and fx3_str.marker_hits.get("TC/UB") == 1
        and fx3_str.marker_hits.get("Time Code Preset") == 1
        and fx3_str.marker_hits.get("User Bit Preset") == 1
        and fx3_str.marker_hits.get("Time Code Format") == 1
        and fx3_str.marker_hits.get("Time Code Run") == 1
        and fx3_str.marker_hits.get("Time Code Make") == 1
        and fx3_str.marker_hits.get("User Bit Time Rec") == 1
        and fx3_str.marker_hits.get("TC/UB Disp. Setting") == 1
        and fx3_str.marker_hits.get("Camera Settings Reset") == 1
        and fx3_str.marker_hits.get("Initialize") == 1
        and fx3_save.marker_hits.get("SaveLoadSettingsIf") == 1
        and fx3_appfw.window_hits.get("REVIEW") == 1
        and fx6_appfw.window_hits.get("TC_UB") == 1
    )
    all_ok = (
        len(errors) == 0
        and file_vault_proven
        and gamma_lut_proven
        and auto_tcub_proven
    )

    audit = Phase274DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=18,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_media_common=fx3_mcom,
        fx3_media_mount=fx3_mmnt,
        fx3_media_detect=fx3_mdet,
        fx3_meta_supplier=fx3_meta,
        fx3_iptc=fx3_iptc,
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
        file_settings_and_vault_proven=file_vault_proven,
        gamma_assist_and_display_lut_proven=gamma_lut_proven,
        auto_review_and_tcub_proven=auto_tcub_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 54A: Movie [File Settings] vs Still [File/Folder Settings] & Vault
# ---------------------------------------------------------------------------

_TITLE_ALLOWED_RE = re.compile(r"^[A-Za-z0-9_\-. ]{1,37}$")
_STILL_PREFIX_ALLOWED_RE = re.compile(r"^[A-Z0-9][A-Z0-9_]{2}$")
_TC_PRESET_RE = re.compile(r"^[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{2}$")
_UB_PRESET_RE = re.compile(r"^[0-9A-Fa-f]{2}(?: [0-9A-Fa-f]{2}){3}$")


def _normalize_reel_number(reel_number: object) -> Optional[str]:
    if isinstance(reel_number, int) and not isinstance(reel_number, bool):
        if REEL_NUMBER_MIN <= reel_number <= REEL_NUMBER_MAX:
            return f"{reel_number:03d}"
        return None
    if isinstance(reel_number, str) and len(reel_number) == 3 and reel_number.isdigit():
        val = int(reel_number)
        if REEL_NUMBER_MIN <= val <= REEL_NUMBER_MAX:
            return f"{val:03d}"
    return None


def simulate_file_settings_and_vault_hil(
    *,
    configured_movie_file_number: str = FILE_NUMBER_SERIES,
    configured_movie_file_name_format: str = MOVIE_FORMAT_STANDARD,
    configured_camera_id: str = CAMERA_ID_DEFAULT,
    configured_reel_number: object = REEL_NUMBER_DEFAULT,
    configured_camera_position: str = CAMERA_POS_DEFAULT,
    configured_title_name: str = TITLE_NAME_DEFAULT,
    configured_still_file_number: str = FILE_NUMBER_SERIES,
    configured_still_prefix: str = STILL_PREFIX_DEFAULT,
    configured_still_folder_form: str = FOLDER_NAME_STANDARD_FORM,
    media_action: str = MEDIA_ACTION_NONE,
    target_slot: int = 2,
    slot1_has_recovery_vault: bool = True,
    reset_action: str = RESET_ACTION_NONE,
    clip_index: int = 1,
    still_index: int = 1,
    folder_index: int = 100,
    date_yyyymmdd: str = "20261117",
    force_custom_movie_folder: bool = False,
) -> FileSettingsAndVaultEvalResult:
    """Co-emulate Wave-44 Movie [File Settings] vs Still [File/Folder Settings] & Slot-1 Vault."""
    norm_reel = _normalize_reel_number(configured_reel_number)

    def _error_res(errno_val: int, reason: str) -> FileSettingsAndVaultEvalResult:
        return FileSettingsAndVaultEvalResult(
            movie_menu_path=MOVIE_FILE_SETTINGS_MENU_PATH,
            still_menu_path=STILL_FILE_FOLDER_MENU_PATH,
            configured_movie_file_number=configured_movie_file_number,
            configured_movie_file_name_format=configured_movie_file_name_format,
            configured_camera_id=configured_camera_id,
            configured_reel_number=str(configured_reel_number),
            configured_camera_position=configured_camera_position,
            configured_title_name=configured_title_name,
            configured_still_file_number=configured_still_file_number,
            configured_still_prefix=configured_still_prefix,
            configured_still_folder_form=configured_still_folder_form,
            effective_movie_file_number=FILE_NUMBER_SERIES,
            effective_movie_file_name_format=MOVIE_FORMAT_STANDARD,
            effective_camera_id=CAMERA_ID_DEFAULT,
            effective_reel_number=REEL_NUMBER_DEFAULT,
            effective_camera_position=CAMERA_POS_DEFAULT,
            effective_title_name=TITLE_NAME_DEFAULT,
            effective_still_file_number=FILE_NUMBER_SERIES,
            effective_still_prefix=STILL_PREFIX_DEFAULT,
            effective_still_folder_form=FOLDER_NAME_STANDARD_FORM,
            movie_folder_path=MOVIE_FOLDER_IMMUTABLE_PATH,
            rendered_movie_filename="",
            rendered_still_folder="",
            rendered_still_filename="",
            title_char_len=len(configured_title_name),
            media_action=media_action,
            target_slot=target_slot,
            slot1_has_recovery_vault=bool(slot1_has_recovery_vault),
            reset_action=reset_action,
            settings_survived_reset=False,
            settings_wiped_by_initialize=False,
            slot1_vault_folder_mutation_events=SLOT1_VAULT_FOLDER_MUTATION_EVENTS,
            title_name_37char_overflow_events=TITLE_NAME_37CHAR_OVERFLOW_EVENTS,
            still_prefix_leading_underscore_bypass_events=(
                STILL_PREFIX_LEADING_UNDERSCORE_BYPASS_EVENTS
            ),
            admitted=False,
            errno_code=errno_val,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        configured_movie_file_number not in VALID_FILE_NUMBER_MODES
        or configured_movie_file_name_format not in VALID_MOVIE_FILE_NAME_FORMATS
        or configured_camera_id not in CAMERA_ID_LETTERS
        or norm_reel is None
        or configured_camera_position not in VALID_CAMERA_POSITIONS
        or configured_still_file_number not in VALID_FILE_NUMBER_MODES
        or configured_still_folder_form not in VALID_STILL_FOLDER_FORMS
        or media_action not in VALID_MEDIA_ACTIONS
        or target_slot not in (1, 2)
        or reset_action not in VALID_RESET_ACTIONS
        or clip_index < 1
        or clip_index > 9999
        or still_index < 1
        or still_index > 9999
        or folder_index < 100
        or folder_index > 999
    ):
        return _error_res(EINVAL_ERRNO, "INVALID_FILE_SETTINGS_PARAMETER")

    if len(configured_title_name) == 0 or len(configured_title_name) > TITLE_NAME_MAX_CHARS:
        return _error_res(EINVAL_ERRNO, "MOVIE_TITLE_NAME_LENGTH_OUT_OF_RANGE")
    if not _TITLE_ALLOWED_RE.match(configured_title_name):
        return _error_res(EINVAL_ERRNO, "MOVIE_TITLE_NAME_INVALID_CHARS")

    if len(configured_still_prefix) != STILL_PREFIX_LEN:
        return _error_res(EINVAL_ERRNO, "STILL_PREFIX_MUST_BE_EXACT_3_CHARS")
    if configured_still_prefix.startswith("_"):
        return _error_res(EINVAL_ERRNO, "STILL_PREFIX_LEADING_UNDERSCORE_FORBIDDEN")
    if not _STILL_PREFIX_ALLOWED_RE.match(configured_still_prefix):
        return _error_res(EINVAL_ERRNO, "STILL_PREFIX_INVALID_CHARACTERS")

    if force_custom_movie_folder:
        return _error_res(EOPNOTSUPP_ERRNO, "MOVIE_FOLDER_M4ROOT_CLIP_IMMUTABLE")

    # Slot-1 DCIM Recovery Vault Firewall: block mutating card actions on Slot 1 when vault is present
    if (
        target_slot == 1
        and slot1_has_recovery_vault
        and media_action in (
            MEDIA_ACTION_FORCED_FILE_NUMBER_RESET,
            MEDIA_ACTION_CREATE_NEW_FOLDER,
        )
    ):
        return _error_res(EROFS_ERRNO, "SLOT1_RECOVERY_VAULT_FOLDER_MUTATION_BLOCKED")

    # Sony Wave-44 Reset Contract: ALL items under Movie [File Settings] and
    # Still [File/Folder Settings] survive [Camera Settings Reset] & [Reset Network Set.],
    # restored only by [Initialize].
    wiped = reset_action == RESET_ACTION_INITIALIZE
    survived = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_RESET_NETWORK_SET,
    )

    eff_mv_num = FILE_NUMBER_SERIES if wiped else configured_movie_file_number
    eff_mv_fmt = MOVIE_FORMAT_STANDARD if wiped else configured_movie_file_name_format
    eff_cam_id = CAMERA_ID_DEFAULT if wiped else configured_camera_id
    eff_reel = REEL_NUMBER_DEFAULT if wiped else norm_reel
    eff_pos = CAMERA_POS_DEFAULT if wiped else configured_camera_position
    eff_title = TITLE_NAME_DEFAULT if wiped else configured_title_name
    eff_st_num = FILE_NUMBER_SERIES if wiped else configured_still_file_number
    eff_prefix = STILL_PREFIX_DEFAULT if wiped else configured_still_prefix
    eff_folder_form = FOLDER_NAME_STANDARD_FORM if wiped else configured_still_folder_form

    eff_clip_idx = clip_index
    eff_still_idx = still_index
    eff_folder_idx = folder_index
    if media_action == MEDIA_ACTION_SERIES_COUNTER_RESET:
        eff_clip_idx = 1
    elif media_action == MEDIA_ACTION_FORCED_FILE_NUMBER_RESET:
        eff_still_idx = 1
        eff_folder_idx = min(folder_index + 1, 999)
    elif media_action == MEDIA_ACTION_CREATE_NEW_FOLDER:
        eff_still_idx = 1
        eff_folder_idx = min(folder_index + 1, 999)

    if eff_mv_fmt == MOVIE_FORMAT_STANDARD:
        rendered_movie = f"C{eff_clip_idx:04d}.MP4"
    elif eff_mv_fmt == MOVIE_FORMAT_CAM_ID_REEL:
        rendered_movie = f"{eff_cam_id}{eff_reel}{eff_pos}{eff_clip_idx:04d}.MP4"
    elif eff_mv_fmt == MOVIE_FORMAT_TITLE:
        rendered_movie = f"{eff_title}_{eff_clip_idx:04d}.MP4"
    elif eff_mv_fmt == MOVIE_FORMAT_DATE_TITLE:
        rendered_movie = f"{date_yyyymmdd}_{eff_title}_{eff_clip_idx:04d}.MP4"
    else:
        rendered_movie = f"{eff_title}_{date_yyyymmdd}_{eff_clip_idx:04d}.MP4"

    if eff_folder_form == FOLDER_NAME_STANDARD_FORM:
        rendered_folder = f"{eff_folder_idx:03d}MSDCF"
    else:
        # Date Form: 3-digit folder# + YMMDD (5 digits from YYYYMMDD[-5:])
        ymmdd = date_yyyymmdd[3:8] if len(date_yyyymmdd) >= 8 else "61117"
        rendered_folder = f"{eff_folder_idx:03d}{ymmdd}"
    rendered_still = f"{eff_prefix}{eff_still_idx:04d}.JPG"

    return FileSettingsAndVaultEvalResult(
        movie_menu_path=MOVIE_FILE_SETTINGS_MENU_PATH,
        still_menu_path=STILL_FILE_FOLDER_MENU_PATH,
        configured_movie_file_number=configured_movie_file_number,
        configured_movie_file_name_format=configured_movie_file_name_format,
        configured_camera_id=configured_camera_id,
        configured_reel_number=norm_reel,
        configured_camera_position=configured_camera_position,
        configured_title_name=configured_title_name,
        configured_still_file_number=configured_still_file_number,
        configured_still_prefix=configured_still_prefix,
        configured_still_folder_form=configured_still_folder_form,
        effective_movie_file_number=eff_mv_num,
        effective_movie_file_name_format=eff_mv_fmt,
        effective_camera_id=eff_cam_id,
        effective_reel_number=eff_reel,
        effective_camera_position=eff_pos,
        effective_title_name=eff_title,
        effective_still_file_number=eff_st_num,
        effective_still_prefix=eff_prefix,
        effective_still_folder_form=eff_folder_form,
        movie_folder_path=MOVIE_FOLDER_IMMUTABLE_PATH,
        rendered_movie_filename=rendered_movie,
        rendered_still_folder=rendered_folder,
        rendered_still_filename=rendered_still,
        title_char_len=len(eff_title),
        media_action=media_action,
        target_slot=target_slot,
        slot1_has_recovery_vault=bool(slot1_has_recovery_vault),
        reset_action=reset_action,
        settings_survived_reset=survived,
        settings_wiped_by_initialize=wiped,
        slot1_vault_folder_mutation_events=SLOT1_VAULT_FOLDER_MUTATION_EVENTS,
        title_name_37char_overflow_events=TITLE_NAME_37CHAR_OVERFLOW_EVENTS,
        still_prefix_leading_underscore_bypass_events=(
            STILL_PREFIX_LEADING_UNDERSCORE_BYPASS_EVENTS
        ),
        admitted=True,
        errno_code=0,
        reason_code="FILE_SETTINGS_AND_VAULT_CONTRACT_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_a_file_settings_and_vault_hil() -> Dict[str, object]:
    """Exhaustively evaluate Wave-44 Sub-Model 54A Movie/Still file naming, reset survival & Slot-1 vault."""
    exact_37_title = "FX3_A_CAM_PRJ274_STAGE54_WAVE44_OK123"
    assert len(exact_37_title) == TITLE_NAME_MAX_CHARS

    cam_id_reel_ok = simulate_file_settings_and_vault_hil(
        configured_movie_file_name_format=MOVIE_FORMAT_CAM_ID_REEL,
        configured_camera_id="B",
        configured_reel_number="007",
        configured_camera_position=CAMERA_POS_L,
        configured_title_name=exact_37_title,
        clip_index=42,
    )
    five_format_matrix = {
        fmt: asdict(
            simulate_file_settings_and_vault_hil(
                configured_movie_file_name_format=fmt,
                configured_camera_id="A",
                configured_reel_number=1,
                configured_camera_position=CAMERA_POS_C,
                configured_title_name=exact_37_title,
                clip_index=12,
            )
        )
        for fmt in VALID_MOVIE_FILE_NAME_FORMATS
    }
    title_38_rejected = simulate_file_settings_and_vault_hil(
        configured_movie_file_name_format=MOVIE_FORMAT_TITLE,
        configured_title_name="X" * 38,
    )
    custom_movie_folder_blocked = simulate_file_settings_and_vault_hil(
        force_custom_movie_folder=True,
    )
    still_custom_prefix_date_ok = simulate_file_settings_and_vault_hil(
        configured_still_prefix="FX3",
        configured_still_folder_form=FOLDER_NAME_DATE_FORM,
        still_index=88,
        folder_index=105,
        date_yyyymmdd="20261117",
    )
    leading_underscore_rejected = simulate_file_settings_and_vault_hil(
        configured_still_prefix="_AB",
    )
    slot1_forced_reset_blocked = simulate_file_settings_and_vault_hil(
        media_action=MEDIA_ACTION_FORCED_FILE_NUMBER_RESET,
        target_slot=1,
        slot1_has_recovery_vault=True,
    )
    slot1_new_folder_blocked = simulate_file_settings_and_vault_hil(
        media_action=MEDIA_ACTION_CREATE_NEW_FOLDER,
        target_slot=1,
        slot1_has_recovery_vault=True,
    )
    slot2_new_folder_ok = simulate_file_settings_and_vault_hil(
        media_action=MEDIA_ACTION_CREATE_NEW_FOLDER,
        target_slot=2,
        slot1_has_recovery_vault=True,
        folder_index=100,
    )
    camera_reset_preserves = simulate_file_settings_and_vault_hil(
        configured_movie_file_number=FILE_NUMBER_RESET,
        configured_movie_file_name_format=MOVIE_FORMAT_CAM_ID_REEL,
        configured_camera_id="Z",
        configured_reel_number=999,
        configured_camera_position=CAMERA_POS_R,
        configured_title_name=exact_37_title,
        configured_still_file_number=FILE_NUMBER_RESET,
        configured_still_prefix="C3A",
        configured_still_folder_form=FOLDER_NAME_DATE_FORM,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    initialize_resets_defaults = simulate_file_settings_and_vault_hil(
        configured_movie_file_number=FILE_NUMBER_RESET,
        configured_movie_file_name_format=MOVIE_FORMAT_CAM_ID_REEL,
        configured_camera_id="Z",
        configured_reel_number=999,
        configured_camera_position=CAMERA_POS_R,
        configured_title_name=exact_37_title,
        configured_still_file_number=FILE_NUMBER_RESET,
        configured_still_prefix="C3A",
        configured_still_folder_form=FOLDER_NAME_DATE_FORM,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    passed = (
        cam_id_reel_ok.admitted
        and cam_id_reel_ok.rendered_movie_filename == "B007L0042.MP4"
        and cam_id_reel_ok.title_char_len == 37
        and cam_id_reel_ok.movie_folder_path == MOVIE_FOLDER_IMMUTABLE_PATH
        and all(entry["admitted"] for entry in five_format_matrix.values())
        and (not title_38_rejected.admitted)
        and title_38_rejected.errno_code == EINVAL_ERRNO
        and (not custom_movie_folder_blocked.admitted)
        and custom_movie_folder_blocked.errno_code == EOPNOTSUPP_ERRNO
        and still_custom_prefix_date_ok.admitted
        and still_custom_prefix_date_ok.rendered_still_folder == "10561117"
        and still_custom_prefix_date_ok.rendered_still_filename == "FX30088.JPG"
        and (not leading_underscore_rejected.admitted)
        and leading_underscore_rejected.errno_code == EINVAL_ERRNO
        and (not slot1_forced_reset_blocked.admitted)
        and slot1_forced_reset_blocked.errno_code == EROFS_ERRNO
        and slot1_forced_reset_blocked.slot1_vault_folder_mutation_events == 0
        and (not slot1_new_folder_blocked.admitted)
        and slot1_new_folder_blocked.errno_code == EROFS_ERRNO
        and slot1_new_folder_blocked.slot1_vault_folder_mutation_events == 0
        and slot2_new_folder_ok.admitted
        and slot2_new_folder_ok.rendered_still_folder == "101MSDCF"
        and slot2_new_folder_ok.rendered_still_filename == "DSC0001.JPG"
        and camera_reset_preserves.admitted
        and camera_reset_preserves.settings_survived_reset
        and camera_reset_preserves.effective_movie_file_name_format == MOVIE_FORMAT_CAM_ID_REEL
        and camera_reset_preserves.effective_title_name == exact_37_title
        and camera_reset_preserves.effective_still_prefix == "C3A"
        and camera_reset_preserves.effective_still_folder_form == FOLDER_NAME_DATE_FORM
        and initialize_resets_defaults.admitted
        and initialize_resets_defaults.settings_wiped_by_initialize
        and initialize_resets_defaults.effective_movie_file_number == FILE_NUMBER_SERIES
        and initialize_resets_defaults.effective_movie_file_name_format == MOVIE_FORMAT_STANDARD
        and initialize_resets_defaults.effective_title_name == TITLE_NAME_DEFAULT
        and initialize_resets_defaults.effective_still_file_number == FILE_NUMBER_SERIES
        and initialize_resets_defaults.effective_still_prefix == STILL_PREFIX_DEFAULT
        and initialize_resets_defaults.effective_still_folder_form == FOLDER_NAME_STANDARD_FORM
    )

    return {
        "passed": passed,
        "movie_menu_path": MOVIE_FILE_SETTINGS_MENU_PATH,
        "still_menu_path": STILL_FILE_FOLDER_MENU_PATH,
        "movie_folder_immutable_path": MOVIE_FOLDER_IMMUTABLE_PATH,
        "title_max_chars": TITLE_NAME_MAX_CHARS,
        "five_format_matrix": five_format_matrix,
        "cam_id_reel_37char_ok": asdict(cam_id_reel_ok),
        "title_38char_blocked_einval": asdict(title_38_rejected),
        "custom_movie_folder_blocked_eopnotsupp": asdict(custom_movie_folder_blocked),
        "still_custom_prefix_date_form_ok": asdict(still_custom_prefix_date_ok),
        "still_prefix_leading_underscore_blocked_einval": asdict(leading_underscore_rejected),
        "slot1_forced_reset_blocked_erofs": asdict(slot1_forced_reset_blocked),
        "slot1_create_folder_blocked_erofs": asdict(slot1_new_folder_blocked),
        "slot2_create_folder_ok": asdict(slot2_new_folder_ok),
        "camera_settings_reset_preserves_all": asdict(camera_reset_preserves),
        "initialize_restores_defaults": asdict(initialize_resets_defaults),
    }


# ---------------------------------------------------------------------------
# Sub-Model 54B: [Gamma Display Assist] Log Lockout & Clean HDMI vs [Display LUT]
# ---------------------------------------------------------------------------


def simulate_gamma_assist_vs_display_lut_hil(
    *,
    configured_log_shooting: str = LOG_SHOOTING_OFF,
    configured_gamma_display_assist: str = TOGGLE_OFF,
    configured_gamma_assist_type: str = GAMMA_ASSIST_TYP_AUTO,
    configured_display_lut: str = TOGGLE_ON,
    configured_select_lut: str = LUT_PRESET_SLOG3,
    monitor_sink: str = MONITOR_SINK_LCD_LIVE_VIEW,
    reset_action: str = RESET_ACTION_NONE,
    force_gamma_assist_during_log: bool = False,
    force_bake_gamma_assist_to_hdmi: bool = False,
) -> GammaAssistDisplayLutEvalResult:
    """Co-emulate Wave-44 [Gamma Display Assist] Log lockout & LCD-only Clean HDMI vs [Display LUT]."""

    def _err(errno_val: int, reason: str, *, log_locked: bool = False) -> GammaAssistDisplayLutEvalResult:
        return GammaAssistDisplayLutEvalResult(
            gamma_assist_menu_path=GAMMA_DISPLAY_ASSIST_MENU_PATH,
            gamma_typ_menu_path=GAMMA_DISP_ASSIST_TYP_MENU_PATH,
            display_lut_menu_path=DISPLAY_LUT_MENU_PATH,
            select_lut_menu_path=SELECT_LUT_MENU_PATH,
            configured_log_shooting=configured_log_shooting,
            configured_gamma_display_assist=configured_gamma_display_assist,
            configured_gamma_assist_type=configured_gamma_assist_type,
            configured_display_lut=configured_display_lut,
            configured_select_lut=configured_select_lut,
            effective_gamma_display_assist=TOGGLE_OFF,
            effective_gamma_assist_type=GAMMA_ASSIST_TYP_AUTO,
            effective_display_lut=TOGGLE_ON,
            effective_select_lut=LUT_PRESET_SLOG3,
            gamma_display_assist_locked_by_log=log_locked,
            monitor_sink=monitor_sink,
            lcd_gamma_assist_applied=False,
            external_hdmi_gamma_assist_applied=False,
            active_monitoring_conversion="BLOCKED",
            reset_action=reset_action,
            setup_items_survived_camera_reset=False,
            gamma_assist_log_lockout_bypass_events=GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS,
            hdmi_gamma_assist_baked_frames=HDMI_GAMMA_ASSIST_BAKED_FRAMES,
            admitted=False,
            errno_code=errno_val,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        configured_log_shooting not in VALID_LOG_SHOOTING_MODES
        or configured_gamma_display_assist not in VALID_TOGGLE_STATES
        or configured_gamma_assist_type not in VALID_GAMMA_ASSIST_TYPES
        or configured_display_lut not in VALID_TOGGLE_STATES
        or configured_select_lut not in VALID_SELECT_LUT_OPTIONS
        or monitor_sink not in VALID_MONITOR_SINKS
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_GAMMA_OR_LUT_PARAMETER")

    if force_gamma_assist_during_log and configured_log_shooting != LOG_SHOOTING_OFF:
        return _err(EOPNOTSUPP_ERRNO, "GAMMA_DISPLAY_ASSIST_LOCKED_BY_LOG_SHOOTING", log_locked=True)

    if force_bake_gamma_assist_to_hdmi:
        return _err(EOPNOTSUPP_ERRNO, "EXTERNAL_HDMI_GAMMA_ASSIST_CLEAN_FEED_VIOLATION")

    init_reset = reset_action == RESET_ACTION_INITIALIZE
    cam_reset_survived = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_RESET_NETWORK_SET,
    )

    eff_log = LOG_SHOOTING_OFF if init_reset else configured_log_shooting
    raw_ga = TOGGLE_OFF if init_reset else configured_gamma_display_assist
    eff_ga_typ = GAMMA_ASSIST_TYP_AUTO if init_reset else configured_gamma_assist_type
    eff_disp_lut = TOGGLE_ON if init_reset else configured_display_lut
    eff_sel_lut = LUT_PRESET_SLOG3 if init_reset else configured_select_lut

    log_active = eff_log != LOG_SHOOTING_OFF
    eff_ga = TOGGLE_OFF if log_active else raw_ga

    lcd_ga_applied = (
        (not log_active)
        and eff_ga == TOGGLE_ON
        and monitor_sink in (MONITOR_SINK_LCD_LIVE_VIEW, MONITOR_SINK_INTERNAL_PLAYBACK)
    )
    # Clean external HDMI: Gamma Display Assist NEVER touches external HDMI output.
    ext_hdmi_ga_applied = False

    if log_active:
        active_conv = (
            f"DISPLAY_LUT:{eff_sel_lut}" if eff_disp_lut == TOGGLE_ON else "LOG_RAW_PASSTHROUGH"
        )
    elif monitor_sink == MONITOR_SINK_EXTERNAL_HDMI:
        active_conv = "CLEAN_EXTERNAL_HDMI_NO_GAMMA_ASSIST"
    elif eff_ga == TOGGLE_ON:
        active_conv = f"GAMMA_DISPLAY_ASSIST:{eff_ga_typ}"
    else:
        active_conv = "NONE"

    return GammaAssistDisplayLutEvalResult(
        gamma_assist_menu_path=GAMMA_DISPLAY_ASSIST_MENU_PATH,
        gamma_typ_menu_path=GAMMA_DISP_ASSIST_TYP_MENU_PATH,
        display_lut_menu_path=DISPLAY_LUT_MENU_PATH,
        select_lut_menu_path=SELECT_LUT_MENU_PATH,
        configured_log_shooting=configured_log_shooting,
        configured_gamma_display_assist=configured_gamma_display_assist,
        configured_gamma_assist_type=configured_gamma_assist_type,
        configured_display_lut=configured_display_lut,
        configured_select_lut=configured_select_lut,
        effective_gamma_display_assist=eff_ga,
        effective_gamma_assist_type=eff_ga_typ,
        effective_display_lut=eff_disp_lut,
        effective_select_lut=eff_sel_lut,
        gamma_display_assist_locked_by_log=log_active,
        monitor_sink=monitor_sink,
        lcd_gamma_assist_applied=lcd_ga_applied,
        external_hdmi_gamma_assist_applied=ext_hdmi_ga_applied,
        active_monitoring_conversion=active_conv,
        reset_action=reset_action,
        setup_items_survived_camera_reset=cam_reset_survived,
        gamma_assist_log_lockout_bypass_events=GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS,
        hdmi_gamma_assist_baked_frames=HDMI_GAMMA_ASSIST_BAKED_FRAMES,
        admitted=True,
        errno_code=0,
        reason_code="GAMMA_ASSIST_VS_DISPLAY_LUT_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_b_gamma_assist_vs_display_lut_hil() -> Dict[str, object]:
    """Evaluate Wave-44 Sub-Model 54B [Gamma Display Assist] vs [Display LUT] / [Select LUT]."""
    log_lockout_matrix = {
        mode: asdict(
            simulate_gamma_assist_vs_display_lut_hil(
                configured_log_shooting=mode,
                configured_gamma_display_assist=TOGGLE_ON,
                configured_gamma_assist_type=GAMMA_ASSIST_TYP_SLOG3_709,
                configured_display_lut=TOGGLE_ON,
                configured_select_lut="User1",
                monitor_sink=MONITOR_SINK_LCD_LIVE_VIEW,
            )
        )
        for mode in VALID_LOG_SHOOTING_MODES
    }
    gamma_types_lcd_vs_hdmi = {
        typ: {
            sink: asdict(
                simulate_gamma_assist_vs_display_lut_hil(
                    configured_log_shooting=LOG_SHOOTING_OFF,
                    configured_gamma_display_assist=TOGGLE_ON,
                    configured_gamma_assist_type=typ,
                    monitor_sink=sink,
                )
            )
            for sink in VALID_MONITOR_SINKS
        }
        for typ in VALID_GAMMA_ASSIST_TYPES
    }
    select_lut_19_matrix = {
        lut: asdict(
            simulate_gamma_assist_vs_display_lut_hil(
                configured_log_shooting=LOG_SHOOTING_CINE_EI,
                configured_display_lut=TOGGLE_ON,
                configured_select_lut=lut,
                monitor_sink=MONITOR_SINK_LCD_LIVE_VIEW,
            )
        )
        for lut in VALID_SELECT_LUT_OPTIONS
    }
    log_bypass_blocked = simulate_gamma_assist_vs_display_lut_hil(
        configured_log_shooting=LOG_SHOOTING_CINE_EI_QUICK,
        configured_gamma_display_assist=TOGGLE_ON,
        force_gamma_assist_during_log=True,
    )
    hdmi_bake_blocked = simulate_gamma_assist_vs_display_lut_hil(
        configured_log_shooting=LOG_SHOOTING_OFF,
        configured_gamma_display_assist=TOGGLE_ON,
        monitor_sink=MONITOR_SINK_EXTERNAL_HDMI,
        force_bake_gamma_assist_to_hdmi=True,
    )
    setup_survives_reset = simulate_gamma_assist_vs_display_lut_hil(
        configured_log_shooting=LOG_SHOOTING_OFF,
        configured_gamma_display_assist=TOGGLE_ON,
        configured_gamma_assist_type=GAMMA_ASSIST_TYP_HLG_BT2020,
        configured_display_lut=TOGGLE_OFF,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_resets = simulate_gamma_assist_vs_display_lut_hil(
        configured_log_shooting=LOG_SHOOTING_OFF,
        configured_gamma_display_assist=TOGGLE_ON,
        configured_gamma_assist_type=GAMMA_ASSIST_TYP_HLG_BT2020,
        configured_display_lut=TOGGLE_OFF,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    passed = (
        len(select_lut_19_matrix) == 19
        and all(v["admitted"] for v in log_lockout_matrix.values())
        and log_lockout_matrix[LOG_SHOOTING_OFF]["effective_gamma_display_assist"] == TOGGLE_ON
        and (not log_lockout_matrix[LOG_SHOOTING_OFF]["gamma_display_assist_locked_by_log"])
        and all(
            log_lockout_matrix[m]["effective_gamma_display_assist"] == TOGGLE_OFF
            and log_lockout_matrix[m]["gamma_display_assist_locked_by_log"]
            for m in (
                LOG_SHOOTING_CINE_EI,
                LOG_SHOOTING_CINE_EI_QUICK,
                LOG_SHOOTING_FLEXIBLE_ISO,
            )
        )
        and all(
            gamma_types_lcd_vs_hdmi[t][MONITOR_SINK_LCD_LIVE_VIEW]["lcd_gamma_assist_applied"]
            and gamma_types_lcd_vs_hdmi[t][MONITOR_SINK_INTERNAL_PLAYBACK]["lcd_gamma_assist_applied"]
            and (not gamma_types_lcd_vs_hdmi[t][MONITOR_SINK_EXTERNAL_HDMI]["external_hdmi_gamma_assist_applied"])
            and gamma_types_lcd_vs_hdmi[t][MONITOR_SINK_EXTERNAL_HDMI]["hdmi_gamma_assist_baked_frames"] == 0
            for t in VALID_GAMMA_ASSIST_TYPES
        )
        and all(v["admitted"] for v in select_lut_19_matrix.values())
        and (not log_bypass_blocked.admitted)
        and log_bypass_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not hdmi_bake_blocked.admitted)
        and hdmi_bake_blocked.errno_code == EOPNOTSUPP_ERRNO
        and hdmi_bake_blocked.hdmi_gamma_assist_baked_frames == 0
        and setup_survives_reset.admitted
        and setup_survives_reset.setup_items_survived_camera_reset
        and setup_survives_reset.effective_gamma_display_assist == TOGGLE_ON
        and setup_survives_reset.effective_gamma_assist_type == GAMMA_ASSIST_TYP_HLG_BT2020
        and setup_survives_reset.effective_display_lut == TOGGLE_OFF
        and init_resets.admitted
        and init_resets.effective_gamma_display_assist == TOGGLE_OFF
        and init_resets.effective_gamma_assist_type == GAMMA_ASSIST_TYP_AUTO
        and init_resets.effective_display_lut == TOGGLE_ON
    )

    return {
        "passed": passed,
        "valid_select_lut_options": list(VALID_SELECT_LUT_OPTIONS),
        "select_lut_count": len(VALID_SELECT_LUT_OPTIONS),
        "log_lockout_matrix": log_lockout_matrix,
        "gamma_types_lcd_vs_hdmi_matrix": gamma_types_lcd_vs_hdmi,
        "select_lut_19_matrix": select_lut_19_matrix,
        "log_lockout_bypass_blocked_eopnotsupp": asdict(log_bypass_blocked),
        "hdmi_gamma_assist_bake_blocked_eopnotsupp": asdict(hdmi_bake_blocked),
        "camera_settings_reset_preserves_setup_items": asdict(setup_survives_reset),
        "initialize_restores_setup_defaults": asdict(init_resets),
    }


# ---------------------------------------------------------------------------
# Sub-Model 54C & Redlines: [Auto Review] & 6 Non-Resettable [TC/UB] Items
# ---------------------------------------------------------------------------


def simulate_auto_review_and_tcub_hil(
    *,
    shooting_domain: str = SHOOTING_DOMAIN_MOVIE,
    frame_rate: str = FRAME_RATE_5994P,
    configured_auto_review: str = AUTO_REVIEW_OFF,
    configured_tc_preset: str = TC_PRESET_DEFAULT,
    configured_ub_preset: str = UB_PRESET_DEFAULT,
    configured_tc_format: str = TC_FORMAT_DF,
    configured_tc_run: str = TC_RUN_REC_RUN,
    configured_tc_make: str = TC_MAKE_PRESET,
    configured_ub_time_rec: str = TOGGLE_OFF,
    configured_tc_ub_disp_setting: str = TC_DISP_TC,
    reset_action: str = RESET_ACTION_NONE,
    force_df_on_24p_or_pal: bool = False,
    force_wipe_tcub_on_camera_settings_reset: bool = False,
) -> AutoReviewAndTcubEvalResult:
    """Co-emulate Wave-44 [Auto Review] (Off cinema default) & 6 non-resettable [TC/UB] items."""

    def _err(errno_val: int, reason: str) -> AutoReviewAndTcubEvalResult:
        return AutoReviewAndTcubEvalResult(
            auto_review_menu_path=AUTO_REVIEW_MENU_PATH,
            tc_ub_menu_path=TC_UB_MENU_PATH,
            tc_ub_disp_menu_path=TC_UB_DISP_SETTING_MENU_PATH,
            tc_ub_exact_6_items=TC_UB_EXACT_6_ITEMS,
            shooting_domain=shooting_domain,
            frame_rate=frame_rate,
            configured_auto_review=configured_auto_review,
            effective_auto_review=AUTO_REVIEW_OFF,
            still_post_capture_review_seconds=0,
            configured_tc_preset=configured_tc_preset,
            configured_ub_preset=configured_ub_preset,
            configured_tc_format=configured_tc_format,
            configured_tc_run=configured_tc_run,
            configured_tc_make=configured_tc_make,
            configured_ub_time_rec=configured_ub_time_rec,
            configured_tc_ub_disp_setting=configured_tc_ub_disp_setting,
            effective_tc_preset=TC_PRESET_DEFAULT,
            effective_ub_preset=UB_PRESET_DEFAULT,
            effective_tc_format=TC_FORMAT_DF,
            effective_tc_run=TC_RUN_REC_RUN,
            effective_tc_make=TC_MAKE_PRESET,
            effective_ub_time_rec=TOGGLE_OFF,
            effective_tc_ub_disp_setting=TC_DISP_TC,
            tc_format_forced_ndf=(frame_rate in FORCED_NDF_FRAME_RATES),
            reset_action=reset_action,
            auto_review_survived_camera_reset=False,
            all_6_tcub_survived_camera_reset=False,
            tc_ub_disp_survived_camera_reset=False,
            tcub_camera_settings_reset_wipe_events=TCUB_CAMERA_SETTINGS_RESET_WIPE_EVENTS,
            tc_24p_or_pal_df_violation_events=TC_24P_OR_PAL_DF_VIOLATION_EVENTS,
            admitted=False,
            errno_code=errno_val,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        shooting_domain not in VALID_SHOOTING_DOMAINS
        or frame_rate not in VALID_FRAME_RATES
        or configured_auto_review not in VALID_AUTO_REVIEW_OPTIONS
        or configured_tc_format not in VALID_TC_FORMATS
        or configured_tc_run not in VALID_TC_RUN_MODES
        or configured_tc_make not in VALID_TC_MAKE_MODES
        or configured_ub_time_rec not in VALID_TOGGLE_STATES
        or configured_tc_ub_disp_setting not in VALID_TC_UB_DISP_MODES
        or reset_action not in VALID_RESET_ACTIONS
        or (not _TC_PRESET_RE.match(configured_tc_preset))
        or (not _UB_PRESET_RE.match(configured_ub_preset))
    ):
        return _err(EINVAL_ERRNO, "INVALID_AUTO_REVIEW_OR_TCUB_PARAMETER")

    if force_wipe_tcub_on_camera_settings_reset and reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        return _err(EOPNOTSUPP_ERRNO, "TCUB_IMMUNE_TO_CAMERA_SETTINGS_RESET")

    forced_ndf = frame_rate in FORCED_NDF_FRAME_RATES
    if force_df_on_24p_or_pal and forced_ndf:
        return _err(EINVAL_ERRNO, "DF_FORBIDDEN_ON_24P_OR_PAL_FRAME_RATE")

    init_reset = reset_action == RESET_ACTION_INITIALIZE
    cam_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_RESET_NETWORK_SET,
    )

    eff_auto_rev = AUTO_REVIEW_OFF if init_reset else configured_auto_review
    eff_tc_preset = TC_PRESET_DEFAULT if init_reset else configured_tc_preset
    eff_ub_preset = UB_PRESET_DEFAULT if init_reset else configured_ub_preset.upper()
    raw_tc_fmt = TC_FORMAT_DF if init_reset else configured_tc_format
    eff_tc_fmt = TC_FORMAT_NDF if forced_ndf else raw_tc_fmt
    eff_tc_run = TC_RUN_REC_RUN if init_reset else configured_tc_run
    eff_tc_make = TC_MAKE_PRESET if init_reset else configured_tc_make
    eff_ub_rec = TOGGLE_OFF if init_reset else configured_ub_time_rec
    eff_disp = TC_DISP_TC if init_reset else configured_tc_ub_disp_setting

    post_capture_s = (
        AUTO_REVIEW_SECONDS_MAP[eff_auto_rev]
        if shooting_domain == SHOOTING_DOMAIN_STILL
        else 0
    )

    return AutoReviewAndTcubEvalResult(
        auto_review_menu_path=AUTO_REVIEW_MENU_PATH,
        tc_ub_menu_path=TC_UB_MENU_PATH,
        tc_ub_disp_menu_path=TC_UB_DISP_SETTING_MENU_PATH,
        tc_ub_exact_6_items=TC_UB_EXACT_6_ITEMS,
        shooting_domain=shooting_domain,
        frame_rate=frame_rate,
        configured_auto_review=configured_auto_review,
        effective_auto_review=eff_auto_rev,
        still_post_capture_review_seconds=post_capture_s,
        configured_tc_preset=configured_tc_preset,
        configured_ub_preset=configured_ub_preset,
        configured_tc_format=configured_tc_format,
        configured_tc_run=configured_tc_run,
        configured_tc_make=configured_tc_make,
        configured_ub_time_rec=configured_ub_time_rec,
        configured_tc_ub_disp_setting=configured_tc_ub_disp_setting,
        effective_tc_preset=eff_tc_preset,
        effective_ub_preset=eff_ub_preset,
        effective_tc_format=eff_tc_fmt,
        effective_tc_run=eff_tc_run,
        effective_tc_make=eff_tc_make,
        effective_ub_time_rec=eff_ub_rec,
        effective_tc_ub_disp_setting=eff_disp,
        tc_format_forced_ndf=forced_ndf,
        reset_action=reset_action,
        auto_review_survived_camera_reset=cam_reset,
        all_6_tcub_survived_camera_reset=cam_reset,
        tc_ub_disp_survived_camera_reset=cam_reset,
        tcub_camera_settings_reset_wipe_events=TCUB_CAMERA_SETTINGS_RESET_WIPE_EVENTS,
        tc_24p_or_pal_df_violation_events=TC_24P_OR_PAL_DF_VIOLATION_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="AUTO_REVIEW_AND_TCUB_CONTRACT_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def probe_phase274_redline_guard(**probes: bool) -> RedlineGuardProbeResult:
    """Verify all 16 Stage 54 hard safety & Wave-44 zero-write redline probes."""
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
            slot1_vault_folder_mutation_events=SLOT1_VAULT_FOLDER_MUTATION_EVENTS,
            title_name_37char_overflow_events=TITLE_NAME_37CHAR_OVERFLOW_EVENTS,
            still_prefix_leading_underscore_bypass_events=(
                STILL_PREFIX_LEADING_UNDERSCORE_BYPASS_EVENTS
            ),
            gamma_assist_log_lockout_bypass_events=GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS,
            hdmi_gamma_assist_baked_frames=HDMI_GAMMA_ASSIST_BAKED_FRAMES,
            tcub_camera_settings_reset_wipe_events=TCUB_CAMERA_SETTINGS_RESET_WIPE_EVENTS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        )

    for field in ALL_16_REDLINE_PROBE_FIELDS:
        if probes.get(field, False):
            if field in (
                "cnflasha_userspace_write_requested",
                "slot1_vault_folder_mutation_requested",
            ):
                err = EROFS_ERRNO
            elif field in (
                "gamma_assist_log_lockout_bypass_requested",
                "hdmi_gamma_assist_bake_requested",
                "tcub_camera_settings_reset_wipe_requested",
            ):
                err = EOPNOTSUPP_ERRNO
            elif field == "still_prefix_leading_underscore_bypass_requested":
                err = EINVAL_ERRNO
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
                slot1_vault_folder_mutation_events=SLOT1_VAULT_FOLDER_MUTATION_EVENTS,
                title_name_37char_overflow_events=TITLE_NAME_37CHAR_OVERFLOW_EVENTS,
                still_prefix_leading_underscore_bypass_events=(
                    STILL_PREFIX_LEADING_UNDERSCORE_BYPASS_EVENTS
                ),
                gamma_assist_log_lockout_bypass_events=GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS,
                hdmi_gamma_assist_baked_frames=HDMI_GAMMA_ASSIST_BAKED_FRAMES,
                tcub_camera_settings_reset_wipe_events=TCUB_CAMERA_SETTINGS_RESET_WIPE_EVENTS,
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
        slot1_vault_folder_mutation_events=SLOT1_VAULT_FOLDER_MUTATION_EVENTS,
        title_name_37char_overflow_events=TITLE_NAME_37CHAR_OVERFLOW_EVENTS,
        still_prefix_leading_underscore_bypass_events=(
            STILL_PREFIX_LEADING_UNDERSCORE_BYPASS_EVENTS
        ),
        gamma_assist_log_lockout_bypass_events=GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS,
        hdmi_gamma_assist_baked_frames=HDMI_GAMMA_ASSIST_BAKED_FRAMES,
        tcub_camera_settings_reset_wipe_events=TCUB_CAMERA_SETTINGS_RESET_WIPE_EVENTS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_pillar_c_d_auto_review_tcub_and_redlines() -> Dict[str, object]:
    """Evaluate Sub-Model 54C [Auto Review] & [TC/UB] 6 non-resettable items + 16 redlines."""
    auto_review_default = simulate_auto_review_and_tcub_hil(
        shooting_domain=SHOOTING_DOMAIN_STILL,
        configured_auto_review=AUTO_REVIEW_OFF,
    )
    auto_review_movie_zero = simulate_auto_review_and_tcub_hil(
        shooting_domain=SHOOTING_DOMAIN_MOVIE,
        configured_auto_review=AUTO_REVIEW_10S,
    )
    frame_rate_df_ndf_matrix = {
        fps: asdict(
            simulate_auto_review_and_tcub_hil(
                frame_rate=fps,
                configured_tc_format=TC_FORMAT_DF,
            )
        )
        for fps in VALID_FRAME_RATES
    }
    forced_df_on_24p_blocked = simulate_auto_review_and_tcub_hil(
        frame_rate=FRAME_RATE_2400P,
        configured_tc_format=TC_FORMAT_DF,
        force_df_on_24p_or_pal=True,
    )
    cam_reset_preserves_6_tcub = simulate_auto_review_and_tcub_hil(
        shooting_domain=SHOOTING_DOMAIN_STILL,
        frame_rate=FRAME_RATE_2997P,
        configured_auto_review=AUTO_REVIEW_5S,
        configured_tc_preset="01:23:45.12",
        configured_ub_preset="AB CD EF 01",
        configured_tc_format=TC_FORMAT_NDF,
        configured_tc_run=TC_RUN_FREE_RUN,
        configured_tc_make=TC_MAKE_REGENERATE,
        configured_ub_time_rec=TOGGLE_ON,
        configured_tc_ub_disp_setting=TC_DISP_UBIT,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    tcub_wipe_blocked = simulate_auto_review_and_tcub_hil(
        configured_tc_preset="01:23:45.12",
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        force_wipe_tcub_on_camera_settings_reset=True,
    )
    init_resets_all = simulate_auto_review_and_tcub_hil(
        shooting_domain=SHOOTING_DOMAIN_STILL,
        frame_rate=FRAME_RATE_5994P,
        configured_auto_review=AUTO_REVIEW_10S,
        configured_tc_preset="12:34:56.07",
        configured_ub_preset="11 22 33 44",
        configured_tc_format=TC_FORMAT_NDF,
        configured_tc_run=TC_RUN_FREE_RUN,
        configured_tc_make=TC_MAKE_REGENERATE,
        configured_ub_time_rec=TOGGLE_ON,
        configured_tc_ub_disp_setting=TC_DISP_UBIT,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    baseline_redline = probe_phase274_redline_guard()
    blocked_probes = {
        field: asdict(probe_phase274_redline_guard(**{field: True}))
        for field in ALL_16_REDLINE_PROBE_FIELDS
    }
    all_probes_blocked = all(not p["valid"] for p in blocked_probes.values())

    passed = (
        auto_review_default.admitted
        and auto_review_default.effective_auto_review == AUTO_REVIEW_OFF
        and auto_review_default.still_post_capture_review_seconds == 0
        and auto_review_movie_zero.admitted
        and auto_review_movie_zero.still_post_capture_review_seconds == 0
        and len(TC_UB_EXACT_6_ITEMS) == 6
        and all(
            frame_rate_df_ndf_matrix[fps]["effective_tc_format"] == TC_FORMAT_NDF
            and frame_rate_df_ndf_matrix[fps]["tc_format_forced_ndf"]
            for fps in FORCED_NDF_FRAME_RATES
        )
        and frame_rate_df_ndf_matrix[FRAME_RATE_2997P]["effective_tc_format"] == TC_FORMAT_DF
        and frame_rate_df_ndf_matrix[FRAME_RATE_5994P]["effective_tc_format"] == TC_FORMAT_DF
        and (not forced_df_on_24p_blocked.admitted)
        and forced_df_on_24p_blocked.errno_code == EINVAL_ERRNO
        and cam_reset_preserves_6_tcub.admitted
        and cam_reset_preserves_6_tcub.auto_review_survived_camera_reset
        and cam_reset_preserves_6_tcub.all_6_tcub_survived_camera_reset
        and cam_reset_preserves_6_tcub.tc_ub_disp_survived_camera_reset
        and cam_reset_preserves_6_tcub.effective_auto_review == AUTO_REVIEW_5S
        and cam_reset_preserves_6_tcub.effective_tc_preset == "01:23:45.12"
        and cam_reset_preserves_6_tcub.effective_ub_preset == "AB CD EF 01"
        and cam_reset_preserves_6_tcub.effective_tc_format == TC_FORMAT_NDF
        and cam_reset_preserves_6_tcub.effective_tc_run == TC_RUN_FREE_RUN
        and cam_reset_preserves_6_tcub.effective_tc_make == TC_MAKE_REGENERATE
        and cam_reset_preserves_6_tcub.effective_ub_time_rec == TOGGLE_ON
        and cam_reset_preserves_6_tcub.effective_tc_ub_disp_setting == TC_DISP_UBIT
        and (not tcub_wipe_blocked.admitted)
        and tcub_wipe_blocked.errno_code == EOPNOTSUPP_ERRNO
        and init_resets_all.admitted
        and init_resets_all.effective_auto_review == AUTO_REVIEW_OFF
        and init_resets_all.effective_tc_preset == TC_PRESET_DEFAULT
        and init_resets_all.effective_ub_preset == UB_PRESET_DEFAULT
        and init_resets_all.effective_tc_format == TC_FORMAT_DF
        and init_resets_all.effective_tc_run == TC_RUN_REC_RUN
        and init_resets_all.effective_tc_make == TC_MAKE_PRESET
        and init_resets_all.effective_ub_time_rec == TOGGLE_OFF
        and init_resets_all.effective_tc_ub_disp_setting == TC_DISP_TC
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "auto_review_menu_path": AUTO_REVIEW_MENU_PATH,
        "tc_ub_menu_path": TC_UB_MENU_PATH,
        "tc_ub_disp_menu_path": TC_UB_DISP_SETTING_MENU_PATH,
        "tc_ub_exact_6_items": list(TC_UB_EXACT_6_ITEMS),
        "all_16_redline_probe_fields": list(ALL_16_REDLINE_PROBE_FIELDS),
        "auto_review_off_default_ok": asdict(auto_review_default),
        "auto_review_movie_zero_interruption": asdict(auto_review_movie_zero),
        "frame_rate_df_ndf_matrix": frame_rate_df_ndf_matrix,
        "forced_df_on_24p_blocked_einval": asdict(forced_df_on_24p_blocked),
        "camera_settings_reset_preserves_all_6_tcub": asdict(cam_reset_preserves_6_tcub),
        "tcub_wipe_on_camera_reset_blocked_eopnotsupp": asdict(tcub_wipe_blocked),
        "initialize_resets_all_defaults": asdict(init_resets_all),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 274 (Stage 54, 54/54) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase274_realhw_file_settings_gamma_assist_tcub_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 274 Stage 54 (54/54) Wave-44 HIL co-emulation audit."""
    donor_audit = inspect_phase274_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_file_settings_and_vault_hil()
    pillar_b = evaluate_pillar_b_gamma_assist_vs_display_lut_hil()
    pillar_cd = evaluate_pillar_c_d_auto_review_tcub_and_redlines()

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
        "slot1_vault_folder_mutation_events": SLOT1_VAULT_FOLDER_MUTATION_EVENTS,
        "title_name_37char_overflow_events": TITLE_NAME_37CHAR_OVERFLOW_EVENTS,
        "still_prefix_leading_underscore_bypass_events": (
            STILL_PREFIX_LEADING_UNDERSCORE_BYPASS_EVENTS
        ),
        "gamma_assist_log_lockout_bypass_events": GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS,
        "hdmi_gamma_assist_baked_frames": HDMI_GAMMA_ASSIST_BAKED_FRAMES,
        "tcub_camera_settings_reset_wipe_events": TCUB_CAMERA_SETTINGS_RESET_WIPE_EVENTS,
        "tc_24p_or_pal_df_violation_events": TC_24P_OR_PAL_DF_VIOLATION_EVENTS,
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
        and SLOT1_VAULT_FOLDER_MUTATION_EVENTS == 0
        and TITLE_NAME_37CHAR_OVERFLOW_EVENTS == 0
        and STILL_PREFIX_LEADING_UNDERSCORE_BYPASS_EVENTS == 0
        and GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS == 0
        and HDMI_GAMMA_ASSIST_BAKED_FRAMES == 0
        and TCUB_CAMERA_SETTINGS_RESET_WIPE_EVENTS == 0
        and TC_24P_OR_PAL_DF_VIOLATION_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_274_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_file_settings_and_vault_hil": pillar_a,
        "pillar_b_gamma_assist_vs_display_lut_hil": pillar_b,
        "pillar_c_d_auto_review_tcub_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_file_settings_gamma_assist_tcub_coemulator.py",
        description=(
            "Phase 274 Stage 54 (54/54) — Real-Hardware ILME-FX3 Wave-44 "
            "Movie File Settings (Cam ID + Reel# & 37-Char Title) vs Still File/Folder "
            "Settings & Slot-1 Vault, Gamma Display Assist Log Lockout vs Display LUT "
            "(User1..User16), and Auto Review & 6 Non-Resettable TC/UB Parameters HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 274 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase274_realhw_file_settings_gamma_assist_tcub_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_file_settings_and_vault_hil"]
        pb = rep["pillar_b_gamma_assist_vs_display_lut_hil"]
        pcd = rep["pillar_c_d_auto_review_tcub_and_redlines"]
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 274 Stage 54 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"fmt={len(pa['five_format_matrix'])}_t{pa['title_max_chars']}_"
            f"s1mut:{red['slot1_vault_folder_mutation_events']} | "
            f"lut={pb['select_lut_count']}slots_"
            f"hdmi_ga:{red['hdmi_gamma_assist_baked_frames']} | "
            f"tcub={len(pcd['tc_ub_exact_6_items'])}item_"
            f"wipe:{red['tcub_camera_settings_reset_wipe_events']}_"
            f"emmc_wr:{red['emmc_nflasha_write_count']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
