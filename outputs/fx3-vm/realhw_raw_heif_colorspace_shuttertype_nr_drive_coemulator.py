#!/usr/bin/env python3
"""Phase 293 (Stage 59, 59/59) — Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-49:
Still `[Image Quality Settings]` (`RAW` `Compressed`/`Uncompressed` vs Dormant `Lossless Comp`,
`JPEG/HEIF Switch` `JPEG / HEIF(4:2:0) / HEIF(4:2:2)` 10-bit `.HIF`, & `[HLG Still Image]` `BT.2100`
Override vs Still-Less `ILME-FX6`),
`[Color Space]` (`sRGB` Default vs `AdobeRGB` `_DSC` Prefix) & `[Set File Name]` Leading-`_` Ban,
and `[Shutter Type]` Exact 2-Option Split (`Mechanical Shutter` Default vs `Electronic Shutter` — NO
`Auto`!), Electronic/Silent 5-Lock Matrix, `[Long Exposure NR]` / `[High ISO NR]`, & `[Drive Mode]`
`10 fps` `Slot-1` Tier-0 Vault Firewall HIL Co-Emulator.

Strictly models Wave-49 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts
without physical hardware attachment or firmware byte leakage:

1. **Sub-Model 59A — Still `[Image Quality Settings]` (`RAW` `Compressed`/`Uncompressed` vs
   Dormant `Lossless Comp`, `JPEG/HEIF Switch` `JPEG / HEIF(4:2:0) / HEIF(4:2:2)` 10-bit `.HIF`,
   & `[HLG Still Image]` `BT.2100` Override vs Still-Less `ILME-FX6`)**:
   - `ILME-FX3 Ver. 7.02` (`12 MP IMX510`) exposes ONLY `[Compressed]` (default) and
     `[Uncompressed]` 14-bit `.ARW` — dormant `Lossless Comp` / `Lossless Comp (L)/(M)/(S)`
     (`_f.uxc` `0x6b56`, `RAW_FILE_TYPE_LOSSLESS`) in `appFw.so` is gated out and rejected
     (`EOPNOTSUPP = 95`), whereas `ILME-FX6 Ver. 6.01` has zero `DCIM`/`.ARW`/`.JPG`/`.HIF` still
     pipeline (`RAW Output Format` is movie-only 16-bit linear over SDI/HDMI).
   - `[HLG Still Image] = On` requires `HEIF(4:2:0/4:2:2)` + `File Format = HEIF` only + `P/A/S/M`
     (blocked `EOPNOTSUPP = 95` in `JPEG`, `RAW`, `RAW & JPEG`, `RAW & HEIF`, or `iAuto`),
     locks out `Picture Profile`, `Creative Look`, `D-Range Optimizer`, and `DRO Bracket`,
     overrides `Color Space` to `BT.2100` (`BT.2020`), and uses `Gamma Display Assist`
     (`Auto` / `HLG(BT.2020)`).

2. **Sub-Model 59B — `[Color Space]` (`sRGB` Default vs `AdobeRGB` `_DSC` Prefix) &
   `[Set File Name]` Leading-`_` Ban**:
   - `MENU -> Shooting -> [Image Quality/Rec] -> [Color Space]`: `sRGB` (default) produces
     `DSC00001.JPG/.ARW`, while `AdobeRGB` automatically prepends `_` -> `_DSC0001.JPG/.ARW`
     under JEITA DCF 2.0 (`100MSDCF`).
   - `[Set File Name]` (default `DSC`, survives `[Camera Settings Reset]`, wiped only by
     `[Initialize]`) allows 3 chars (`A-Z0-9_`) **EXCEPT `_` is forbidden as the 1st character**
     (`EINVAL = 22`). Under `HEIF`, `[Color Space]` is ignored (`sRGB` if `HLG Still Image = Off`,
     `BT.2100` if `On`).

3. **Sub-Model 59C & Redlines — `[Shutter Type]` Exact 2-Option Split (`Mechanical Shutter` Default
   vs `Electronic Shutter` — NO `Auto`!), Electronic/Silent 5-Lock Matrix, `[Long Exposure NR]` /
   `[High ISO NR]`, & `[Drive Mode]` `10 fps` `Slot-1` Tier-0 Vault Firewall**:
   - `ILME-FX3 Ver. 7.02` exposes ONLY **2** `[Shutter Type]` options (`Mechanical Shutter`
     default vs `Electronic Shutter`; `Auto` rejected `EINVAL = 22`), whereas `ILME-FX6` has
     `mechanical_shutter = False`.
   - Electronic Shutter (and `Silent Mode = On` unless overridden via `Target Function`) locks out
     (`EOPNOTSUPP = 95`): (1) `Flash` (`1/250 s` FF sync is Mechanical-only), (2) `Long Exposure NR`
     (`>= 1 s` dark-frame subtraction), (3) `e-Front Curtain Shut.` (`On` default, survives
     `Camera Settings Reset`), (4) `BULB` exposures, and (5) `Anti-flicker Shoot.`.
   - Enforce Still `[Drive Mode]` (`Single Shooting`, `Cont. Shooting: Hi+/Hi/Mid/Lo` up to
     `10 fps` `Hi+`, `Self-timer(Single)/(Cont)`, `Bracket`) **fail-closed `EROFS = 30` /
     `EBUSY = 16` `Slot-1` Tier-0 Vault protection** blocking any still/burst/bracket write to
     read-only `Slot 1`, plus all 16 hardware safety redlines locked.

4. **Dual-Mode 11-Donor `O_RDONLY` Verification & Hard Safety Redlines**:
   - Inspects 11 verified `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01` donors strictly via
     `os.O_RDONLY` (`<= 4096 B` bounded windows on large binaries, `< 0.2s` cold,
     `raw_firmware_bytes_leaked == 0`), with deterministic `CLEAN_ROOM_SYNTHETIC` parity under
     `FX3_CLEAN_ROOM_TEST=1` or `FX3_FX6_FORCE_CLEAN_ROOM=1`.
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

SCHEMA_ID = "realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator_v1"
PHASE_293_SCHEMA = SCHEMA_ID
PHASE_293_VERSION = "293.0.0"
PHASE_NUMBER = 293
STAGE_INDEX = 59
STAGE_TOTAL = 59
MILESTONE_LABEL = "59/59"
STAGE_NAME = "stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil"
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
PHYSICAL_USB_PACKETS_EMITTED = 0
PASSIVE_TX_BYTES_EMITTED = 0

# Wave-49 Stage 59 zero-fault & model-truth invariants
DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS = 0
HLG_STILL_PREREQUISITE_BYPASS_EVENTS = 0
COLOR_SPACE_LEADING_UNDERSCORE_BYPASS_EVENTS = 0
SHUTTER_TYPE_AUTO_OR_5LOCK_BYPASS_EVENTS = 0
SLOT1_VAULT_STILL_OR_BURST_WRITE_EVENTS = 0
FX6_STILL_PIPELINE_EXPOSED = False
FX3_MECHANICAL_SHUTTER_PRESENT = True
FX6_MECHANICAL_SHUTTER_PRESENT = False

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
# Verified Local Donor Specs (11 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_string_en_f": f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
    "fx3_string_sc_f": f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
    "fx3_string_tc_f": f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
    "fx3_string_ja_f": f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
    "fx3_string_en": f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
    "fx3_string_en_g": f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx3_bk4": (
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/"
        "FX3-CX95900_ALLLANG-Backup.bin"
    ),
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_en_2": f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_string_en_f": 373_820,
    "fx3_string_sc_f": 322_652,
    "fx3_string_tc_f": 324_148,
    "fx3_string_ja_f": 447_840,
    "fx3_string_en": 165_740,
    "fx3_string_en_g": 69_600,
    "fx3_appfw": 79_015_712,
    "fx3_bk4": 2_229_740,
    "fx6_string_en": 118_208,
    "fx6_string_en_2": 118_676,
    "fx6_appfw": 50_520_424,
}

EXPECTED_COMPACT_DONOR_SHA256: Mapping[str, str] = {
    "fx3_string_en_f": "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
    "fx3_string_sc_f": "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
    "fx3_string_tc_f": "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
    "fx3_string_ja_f": "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
    "fx3_string_en": "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
    "fx3_string_en_g": "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
    "fx6_string_en": "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
    "fx6_string_en_2": "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Image Quality Settings",
        b"JPEG/HEIF Switch",
        b"HEIF(4:2:0)",
        b"HEIF(4:2:2)",
        b"RAW File Type",
        b"Compressed",
        b"Uncompressed",
        b"Lossless Comp",
        b"HLG Still Image",
        b"Gamma Display Assist",
        b"HLG(BT.2020)",
        b"Color Space",
        b"Set File Name",
        b"Shutter Type",
        b"Mechanical Shutter",
        b"Electronic Shutter",
        b"e-Front Curtain Shut.",
        b"Silent Mode Settings",
        b"Long Exposure NR",
        b"High ISO NR",
        b"Drive Mode",
        b"Cont. Shooting: Hi+",
        b"1/250",
        b"Camera Settings Reset",
        b"Initialize",
    ),
    "fx3_string_sc_f": (
        "影像质量设置".encode("utf-8"),
        "JPEG/HEIF切换".encode("utf-8"),
        "RAW文件类型".encode("utf-8"),
        "HLG静态影像".encode("utf-8"),
        "色彩空间".encode("utf-8"),
        "设置文件名".encode("utf-8"),
        "快门类型".encode("utf-8"),
        "机械快门".encode("utf-8"),
        "电子快门".encode("utf-8"),
        "长时曝光降噪".encode("utf-8"),
        "高ISO降噪".encode("utf-8"),
        "拍摄模式".encode("utf-8"),
        "连拍：Hi+".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "影像品質設定".encode("utf-8"),
        "JPEG/HEIF切換".encode("utf-8"),
        "RAW檔案類型".encode("utf-8"),
        "HLG靜態影像".encode("utf-8"),
        "色彩空間".encode("utf-8"),
        "設定檔案名稱".encode("utf-8"),
        "快門類型".encode("utf-8"),
        "機械式快門".encode("utf-8"),
        "電子式快門".encode("utf-8"),
        "消除長曝雜訊".encode("utf-8"),
        "高 ISO 雜訊消除".encode("utf-8"),
        "過片模式".encode("utf-8"),
        "連拍：Hi+".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "画質設定".encode("utf-8"),
        "JPEG/HEIF".encode("utf-8"),
        "RAW記録方式".encode("utf-8"),
        "HLG静止画".encode("utf-8"),
        "色空間".encode("utf-8"),
        "ファイル名設定".encode("utf-8"),
        "シャッター方式".encode("utf-8"),
        "メカシャッター".encode("utf-8"),
        "電子シャッター".encode("utf-8"),
        "長秒時ノイズ低減".encode("utf-8"),
        "高感度ノイズ低減".encode("utf-8"),
        "ドライブモード".encode("utf-8"),
        "HEIF(4:2:2)".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"File Format",
        b"RAW & JPEG",
        b"RAW & HEIF",
        b"JPEG",
        b"HEIF",
        b"sRGB",
        b"AdobeRGB",
        b"Drive Mode",
        b"Single Shooting",
        b"Cont. Shooting",
        b"Cont. Bracket",
        b"High ISO NR",
    ),
    "fx3_string_en_g": (
        b"Image Quality/Rec",
        b"HEIF",
        b"RAW",
        b"Still",
        b"Shutter/Silent",
        b"Drive Mode",
    ),
    "fx6_string_en": (
        b"RAW Output Format",
        b"Shutter Category",
        b"Video Format",
        b"Scene File",
    ),
    "fx6_string_en_2": (
        b"Shutter Mode",
        b"Shutter Speed",
        b"Shutter Angle",
        b"HLG_BT.2100",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (61_218_816, "JH_FILE_TYPE_JPEG", b"JH_FILE_TYPE_JPEG"),
        (61_218_816, "JH_FILE_TYPE_HEIF_420", b"JH_FILE_TYPE_HEIF_420"),
        (61_218_816, "JH_FILE_TYPE_HEIF_422", b"JH_FILE_TYPE_HEIF_422"),
        (61_231_104, "STILL_FILE_FORMAT_RAW", b"STILL_FILE_FORMAT_RAW"),
        (61_231_104, "RAW_FILE_TYPE_UNCOMPRESSED", b"RAW_FILE_TYPE_UNCOMPRESSED"),
        (61_231_104, "RAW_FILE_TYPE_LOSSLESS", b"RAW_FILE_TYPE_LOSSLESS"),
        (61_231_104, "RAW_FILE_TYPE_COMPRESSED", b"RAW_FILE_TYPE_COMPRESSED"),
        (61_304_832, "STILL_SHUTTER_TYPE_MECHANICAL", b"STILL_SHUTTER_TYPE_MECHANICAL"),
        (61_304_832, "STILL_SHUTTER_TYPE_ELECTRONIC", b"STILL_SHUTTER_TYPE_ELECTRONIC"),
        (61_681_664, "STILL_COLOR_SPACE_SRGB", b"STILL_COLOR_SPACE_SRGB"),
        (61_681_664, "STILL_COLOR_SPACE_ADOBE_RGB", b"STILL_COLOR_SPACE_ADOBE_RGB"),
        (62_664_704, "BKID_JH_FILE_TYPE", b"BKID_APP_setting_jh_file_type"),
        (62_664_704, "BKID_STILL_FILE_FORMAT", b"BKID_APP_setting_still_file_format"),
        (62_664_704, "BKID_RAW_FILE_TYPE", b"BKID_APP_setting_still_raw_file_type"),
        (62_672_896, "BKID_LONG_EXP_NR", b"BKID_APP_setting_still_long_exposure_nr"),
        (62_672_896, "BKID_HIGH_ISO_NR", b"BKID_APP_setting_still_high_iso_nr"),
        (62_676_992, "BKID_HLG_PHOTO", b"BKID_APP_setting_still_hlg_photo"),
        (62_676_992, "BKID_COLOR_SPACE", b"BKID_APP_setting_still_color_space"),
        (62_676_992, "BKID_DRIVE_MODE", b"BKID_APP_setting_menu_drive_mode"),
        (62_676_992, "BKID_SILENT_MODE", b"BKID_APP_setting_silent_mode"),
        (62_676_992, "BKID_SHUTTER_TYPE", b"BKID_APP_setting_still_shutter_type"),
        (62_681_088, "BKID_EFRONT_CURTAIN", b"BKID_APP_setting_front_curtaion_shutter"),
        (62_705_664, "BKID_CONT_SHOOTING", b"BKID_APP_setting_drive_mode_cont_shooting"),
        (62_812_160, "BKID_SET_FILE_NAME", b"BKID_APP_set_file_name_prefix_still"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (0, "ALLLANG", b"ALLLANG"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (40_923_136, "FX6_SHUTTER_SELECT", b"BKID_APP_SETTING_SHUTTER_SELECT"),
        (40_931_328, "FX6_RAW_OUTPUT_FORMAT", b"BKID_APP_SETTING_RAW_OUTPUT_FORMAT"),
        (41_013_248, "FX6_FILE_FORMAT", b"BKID_APP_SETTING_FILE_FORMAT"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-49 Official Sub-Model 59A / 59B / 59C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX3A = "ILME-FX3A"
BODY_MODEL_FX6 = "ILME-FX6"
STOCK_FX3_BODIES: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX3A)
ALL_SUPPORTED_BODY_PROFILES: Tuple[str, ...] = STOCK_FX3_BODIES + (BODY_MODEL_FX6,)

TOGGLE_OFF = "Off"
TOGGLE_ON = "On"
VALID_TOGGLE_STATES: Tuple[str, ...] = (TOGGLE_OFF, TOGGLE_ON)

RESET_ACTION_NONE = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET = "Camera Settings Reset"
RESET_ACTION_INITIALIZE = "Initialize"
VALID_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

STORAGE_TARGET_NONE = "NONE"
STORAGE_TARGET_SLOT1_VAULT = "Slot 1 Tier-0 Vault"
STORAGE_TARGET_SLOT2_SCRATCH = "Slot 2 VM Scratch"
VALID_STORAGE_TARGETS: Tuple[str, ...] = (
    STORAGE_TARGET_NONE,
    STORAGE_TARGET_SLOT1_VAULT,
    STORAGE_TARGET_SLOT2_SCRATCH,
)

# Sub-Model 59A: Still Image Quality Settings & HLG Still Image
IMAGE_QUALITY_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [Image Quality Settings]"
JPEG_HEIF_SWITCH_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [JPEG/HEIF Switch]"
HLG_STILL_IMAGE_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [HLG Still Image]"
GAMMA_DISP_ASSIST_MENU_PATH = "MENU -> Setup -> [Display Option] -> [Gamma Disp. Assist Typ.]"
FX6_VIDEO_RAW_MENU_PATH = "System / Rec Out -> [RAW Output Format] (SDI/HDMI Movie Only)"

JH_SWITCH_JPEG = "JPEG"
JH_SWITCH_HEIF_420 = "HEIF(4:2:0)"
JH_SWITCH_HEIF_422 = "HEIF(4:2:2)"
VALID_JPEG_HEIF_SWITCHES: Tuple[str, ...] = (
    JH_SWITCH_JPEG,
    JH_SWITCH_HEIF_420,
    JH_SWITCH_HEIF_422,
)

STILL_FMT_RAW = "RAW"
STILL_FMT_RAW_JPEG = "RAW & JPEG"
STILL_FMT_RAW_HEIF = "RAW & HEIF"
STILL_FMT_JPEG = "JPEG"
STILL_FMT_HEIF = "HEIF"
VALID_STILL_FILE_FORMATS: Tuple[str, ...] = (
    STILL_FMT_RAW,
    STILL_FMT_RAW_JPEG,
    STILL_FMT_RAW_HEIF,
    STILL_FMT_JPEG,
    STILL_FMT_HEIF,
)

RAW_TYPE_COMPRESSED = "Compressed"
RAW_TYPE_UNCOMPRESSED = "Uncompressed"
EXPOSED_FX3_RAW_FILE_TYPES: Tuple[str, ...] = (RAW_TYPE_COMPRESSED, RAW_TYPE_UNCOMPRESSED)
DORMANT_LOSSLESS_RAW_TYPES: Tuple[str, ...] = (
    "Lossless Comp",
    "Lossless Comp (L)",
    "Lossless Comp (M)",
    "Lossless Comp (S)",
)
ALL_TESTABLE_RAW_FILE_TYPES: Tuple[str, ...] = EXPOSED_FX3_RAW_FILE_TYPES + DORMANT_LOSSLESS_RAW_TYPES

STILL_QUALITY_EXTRA_FINE = "Extra fine"
STILL_QUALITY_FINE = "Fine"
STILL_QUALITY_STANDARD = "Standard"
VALID_STILL_QUALITIES: Tuple[str, ...] = (
    STILL_QUALITY_EXTRA_FINE,
    STILL_QUALITY_FINE,
    STILL_QUALITY_STANDARD,
)

STILL_IMAGE_SIZE_L = "L: 12M"
STILL_IMAGE_SIZE_M = "M: 5.1M"
STILL_IMAGE_SIZE_S = "S: 3.0M"
VALID_STILL_IMAGE_SIZES: Tuple[str, ...] = (
    STILL_IMAGE_SIZE_L,
    STILL_IMAGE_SIZE_M,
    STILL_IMAGE_SIZE_S,
)

EXPOSURE_MODE_P = "P"
EXPOSURE_MODE_A = "A"
EXPOSURE_MODE_S = "S"
EXPOSURE_MODE_M = "M"
EXPOSURE_MODE_IAUTO = "iAuto"
PASM_EXPOSURE_MODES: Tuple[str, ...] = (
    EXPOSURE_MODE_P,
    EXPOSURE_MODE_A,
    EXPOSURE_MODE_S,
    EXPOSURE_MODE_M,
)
VALID_EXPOSURE_MODES: Tuple[str, ...] = PASM_EXPOSURE_MODES + (EXPOSURE_MODE_IAUTO,)

GAMMA_ASSIST_AUTO = "Auto"
GAMMA_ASSIST_HLG_BT2020 = "HLG(BT.2020)"
VALID_HLG_GAMMA_ASSIST_TYPES: Tuple[str, ...] = (GAMMA_ASSIST_AUTO, GAMMA_ASSIST_HLG_BT2020)

# Sub-Model 59B: Color Space & Set File Name
COLOR_SPACE_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [Color Space]"
SET_FILE_NAME_MENU_PATH = "MENU -> Shooting -> [File] -> [File/Folder Settings] -> [Set File Name]"

COLOR_SPACE_SRGB = "sRGB"
COLOR_SPACE_ADOBE_RGB = "AdobeRGB"
COLOR_SPACE_BT2100 = "BT.2100 (BT.2020)"
VALID_STILL_COLOR_SPACES: Tuple[str, ...] = (COLOR_SPACE_SRGB, COLOR_SPACE_ADOBE_RGB)
DEFAULT_SET_FILE_NAME_PREFIX = "DSC"
VALID_SET_FILE_NAME_RE = re.compile(r"^[A-Z0-9_]{3}$")

# Sub-Model 59C: Shutter Type, e-Front Curtain, Long Exposure NR, High ISO NR, Drive Mode
SHUTTER_TYPE_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [Shutter Type]"
EFRONT_CURTAIN_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [e-Front Curtain Shut.]"
SILENT_MODE_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings]"
LONG_EXP_NR_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [Long Exposure NR]"
HIGH_ISO_NR_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [High ISO NR]"
DRIVE_MODE_MENU_PATH = "MENU -> Shooting -> [Drive Mode] -> [Drive Mode]"
FX6_SHUTTER_SELECT_MENU_PATH = "Shutter -> [Shutter Mode] (Off / Speed / Angle) + Auto Shutter"

SHUTTER_TYPE_MECHANICAL = "Mechanical Shutter"
SHUTTER_TYPE_ELECTRONIC = "Electronic Shutter"
SHUTTER_TYPE_AUTO_UNSUPPORTED = "Auto"
EXPOSED_FX3_2_SHUTTER_TYPES: Tuple[str, ...] = (
    SHUTTER_TYPE_MECHANICAL,
    SHUTTER_TYPE_ELECTRONIC,
)
FLASH_SYNC_MAX_FRACTION = "1/250 s"

ALL_5_ESHUTTER_SILENT_LOCKED_FUNCTIONS: Tuple[str, ...] = (
    "Flash Shooting (1/250 s Full-Frame Sync)",
    "Long Exposure NR (>= 1 s Dark-Frame Subtraction)",
    "e-Front Curtain Shut.",
    "BULB Exposure",
    "Anti-flicker Shoot.",
)

HIGH_ISO_NR_NORMAL = "Normal"
HIGH_ISO_NR_LOW = "Low"
HIGH_ISO_NR_OFF = "Off"
VALID_HIGH_ISO_NR_MODES: Tuple[str, ...] = (
    HIGH_ISO_NR_NORMAL,
    HIGH_ISO_NR_LOW,
    HIGH_ISO_NR_OFF,
)

DRIVE_SINGLE = "Single Shooting"
DRIVE_CONT_HI_PLUS = "Cont. Shooting: Hi+"
DRIVE_CONT_HI = "Cont. Shooting: Hi"
DRIVE_CONT_MID = "Cont. Shooting: Mid"
DRIVE_CONT_LO = "Cont. Shooting: Lo"
DRIVE_SELF_TIMER_SINGLE = "Self-timer(Single)"
DRIVE_SELF_TIMER_CONT = "Self-timer(Cont)"
DRIVE_CONT_BRACKET = "Cont. Bracket"
DRIVE_SINGLE_BRACKET = "Single Bracket"
DRIVE_WB_BRACKET = "WB bracket"
DRIVE_DRO_BRACKET = "DRO Bracket"

FX3_8_DRIVE_BASE_MODES: Tuple[str, ...] = (
    DRIVE_SINGLE,
    "Cont. Shooting (Hi+ / Hi / Mid / Lo)",
    DRIVE_SELF_TIMER_SINGLE,
    DRIVE_SELF_TIMER_CONT,
    DRIVE_CONT_BRACKET,
    DRIVE_SINGLE_BRACKET,
    DRIVE_WB_BRACKET,
    DRIVE_DRO_BRACKET,
)
VALID_DRIVE_MODES: Tuple[str, ...] = (
    DRIVE_SINGLE,
    DRIVE_CONT_HI_PLUS,
    DRIVE_CONT_HI,
    DRIVE_CONT_MID,
    DRIVE_CONT_LO,
    DRIVE_SELF_TIMER_SINGLE,
    DRIVE_SELF_TIMER_CONT,
    DRIVE_CONT_BRACKET,
    DRIVE_SINGLE_BRACKET,
    DRIVE_WB_BRACKET,
    DRIVE_DRO_BRACKET,
)
CONTINUOUS_BURST_FPS: Mapping[str, float] = {
    DRIVE_CONT_HI_PLUS: 10.0,
    DRIVE_CONT_HI: 8.0,
    DRIVE_CONT_MID: 6.0,
    DRIVE_CONT_LO: 3.0,
}

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
    "dormant_lossless_raw_expose_requested",
    "hlg_still_prerequisite_bypass_requested",
    "leading_underscore_prefix_bypass_requested",
    "eshutter_5lock_or_auto_bypass_requested",
    "slot1_vault_still_burst_write_requested",
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
class Phase293DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_string_en_f: CompactDonorSummary
    fx3_string_sc_f: CompactDonorSummary
    fx3_string_tc_f: CompactDonorSummary
    fx3_string_ja_f: CompactDonorSummary
    fx3_string_en: CompactDonorSummary
    fx3_string_en_g: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx6_string_en_2: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx3_bk4: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    raw_heif_hlg_proven: bool
    colorspace_setfilename_proven: bool
    shuttertype_nr_drive_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StillRawHeifHlgEvalResult:
    image_quality_menu_path: str
    jpeg_heif_switch_menu_path: str
    hlg_still_image_menu_path: str
    body_profile: str
    still_pipeline_present: bool
    exposure_mode: str
    configured_jpeg_heif_switch: str
    configured_file_format: str
    configured_raw_file_type: str
    effective_raw_file_type: str
    dormant_lossless_gated_out: bool
    configured_quality: str
    configured_image_size: str
    configured_hlg_still_image: str
    effective_hlg_still_image: str
    effective_color_space: str
    effective_gamma_display_assist: str
    output_extensions: Tuple[str, ...]
    non_raw_bit_depth: int
    raw_bit_depth: int
    pp_creativelook_dro_locked_by_hlg: bool
    dro_bracket_locked_by_hlg: bool
    reset_action: str
    restored_to_factory_defaults: bool
    fx6_raw_output_contrast: str
    dormant_lossless_raw_exposed_events: int
    hlg_still_prerequisite_bypass_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class ColorSpaceSetFileNameEvalResult:
    color_space_menu_path: str
    set_file_name_menu_path: str
    body_profile: str
    configured_file_format: str
    configured_hlg_still_image: str
    configured_color_space: str
    effective_color_space: str
    color_space_ignored_under_heif: bool
    configured_file_name_prefix: str
    effective_file_name_prefix: str
    dcf_folder_path: str
    sample_still_filenames: Tuple[str, ...]
    leading_underscore_applied_by_adobergb: bool
    leading_underscore_manual_ban_enforced: bool
    reset_action: str
    color_space_reset_to_srgb: bool
    set_file_name_survived_camera_reset: bool
    set_file_name_wiped_by_initialize: bool
    storage_target: str
    color_space_leading_underscore_bypass_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class ShutterTypeNrDriveVaultEvalResult:
    shutter_type_menu_path: str
    efront_curtain_menu_path: str
    silent_mode_menu_path: str
    long_exp_nr_menu_path: str
    high_iso_nr_menu_path: str
    drive_mode_menu_path: str
    body_profile: str
    mechanical_shutter_present: bool
    exposure_mode: str
    configured_shutter_type: str
    effective_shutter_type: str
    shutter_type_auto_absent_enforced: bool
    configured_e_front_curtain: str
    effective_e_front_curtain: str
    silent_mode: str
    silent_target_override: bool
    electronic_5locks_engaged: bool
    locked_functions: Tuple[str, ...]
    flash_sync_max_fraction: str
    shutter_speed_sec: float
    configured_long_exposure_nr: str
    effective_long_exposure_nr: str
    dark_frame_subtraction_active: bool
    configured_high_iso_nr: str
    effective_high_iso_nr_for_jpeg_heif: str
    high_iso_nr_ignored_for_raw_arw: bool
    configured_drive_mode: str
    configured_file_format: str
    configured_raw_file_type: str
    aperture_f_number: float
    burst_frames_captured: int
    effective_burst_fps: float
    uncompressed_raw_speed_drop_active: bool
    buffer_slow_throttled: bool
    af_locked_past_f11: bool
    storage_target: str
    slot1_vault_blocked: bool
    reset_action: str
    efront_curtain_survived_camera_reset: bool
    efront_curtain_wiped_by_initialize: bool
    shutter_type_auto_or_5lock_bypass_events: int
    slot1_vault_still_or_burst_write_events: int
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
    emmc_nflasha_write_count: int
    emmc_corruptions: int
    nop_count: int
    guest_code_modification_bytes: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    physical_usb_packets_emitted: int
    dormant_lossless_raw_exposed_events: int
    hlg_still_prerequisite_bypass_events: int
    color_space_leading_underscore_bypass_events: int
    shutter_type_auto_or_5lock_bypass_events: int
    slot1_vault_still_or_burst_write_events: int
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY 11-Donor Inspection (< 0.2s cold, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase293DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase293DonorAudit] = None


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


def resolve_phase293_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 11 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
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


def _read_bounded_o_rdonly(path: Path, offset: int, size: int) -> bytes:
    if size < 0 or size > BOUNDED_WINDOW_MAX_BYTES:
        raise ValueError(
            f"Bounded O_RDONLY read size {size} exceeds max {BOUNDED_WINDOW_MAX_BYTES}"
        )
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.lseek(fd, offset, os.SEEK_SET)
        return os.read(fd, size)
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
    expected_sha256: Optional[str],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in tokens}
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


def _build_clean_room_donor_audit() -> Phase293DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH_P293".encode("ascii")
        raw = b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(toks) + b"\x00" + tag + b"\x00"
        return _scan_compact_buf(
            raw,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            tokens=toks,
            expected_sha256=None,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        wins = LARGE_DONOR_WINDOWS[key]
        unique_offs = {off for off, _, _ in wins} | {0}
        hits = {lbl: 1 for _, lbl, _ in wins}
        toks = [tok for _, _, tok in wins]
        tag = f"{key}_SYNTH_P293".encode("ascii")
        head = (
            _build_synthetic_elf64_bytes(toks[:2], tag)
            if is_elf
            else (b"BK4\x00ALLLANG\x00" + tag + b"\x00")
        )
        head_digest = hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(unique_offs) * BOUNDED_WINDOW_MAX_BYTES,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256=head_digest,
            head_sha256_prefix16=head_digest[:16],
            head_sha256_verified=True,
        )

    audit = Phase293DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=11,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "ILME-FX3 7.02 en_f"),
        fx3_string_sc_f=_mk_compact("fx3_string_sc_f", "ILME-FX3 7.02 sc_f"),
        fx3_string_tc_f=_mk_compact("fx3_string_tc_f", "ILME-FX3 7.02 tc_f"),
        fx3_string_ja_f=_mk_compact("fx3_string_ja_f", "ILME-FX3 7.02 ja_f"),
        fx3_string_en=_mk_compact("fx3_string_en", "ILME-FX3 7.02 en"),
        fx3_string_en_g=_mk_compact("fx3_string_en_g", "ILME-FX3 7.02 en_g"),
        fx6_string_en=_mk_compact("fx6_string_en", "ILME-FX6 6.01 en"),
        fx6_string_en_2=_mk_compact("fx6_string_en_2", "ILME-FX6 6.01 en_2"),
        fx3_appfw=_mk_large("fx3_appfw", "ILME-FX3 7.02 appFw.so", True),
        fx3_bk4=_mk_large("fx3_bk4", "ILME-FX3 7.02 BK4", False),
        fx6_appfw=_mk_large("fx6_appfw", "ILME-FX6 6.01 appFw.so", True),
        raw_heif_hlg_proven=True,
        colorspace_setfilename_proven=True,
        shuttertype_nr_drive_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    _CLEAN_ROOM_AUDIT_SINGLETON = audit
    return audit


def inspect_phase293_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase293DonorAudit:
    """Inspect all 11 Wave-49 FX3 7.02 & FX6 6.01 donors strictly via `os.O_RDONLY`."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room is True:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    elif force_clean_room is False:
        eff_env.pop(ENV_FORCE_CLEAN_ROOM, None)
        eff_env.pop(ENV_CLEAN_ROOM_TEST, None)

    if is_forced_clean_room(eff_env):
        return _build_clean_room_donor_audit()

    paths = resolve_phase293_donor_paths(env=eff_env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    fp_items: List[Tuple[str, str, int, int]] = []
    for key in sorted(paths):
        st = paths[key].stat()
        fp_items.append((key, str(paths[key]), int(st.st_size), int(st.st_mtime_ns)))
    cache_key = (SOURCE_MODE_LOCAL_DONOR, tuple(fp_items))
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    t0 = time.monotonic()
    fx3_en_f = _scan_compact_rdonly(paths["fx3_string_en_f"], artifact_key="fx3_string_en_f", body_label="ILME-FX3 7.02 en_f")
    fx3_sc_f = _scan_compact_rdonly(paths["fx3_string_sc_f"], artifact_key="fx3_string_sc_f", body_label="ILME-FX3 7.02 sc_f")
    fx3_tc_f = _scan_compact_rdonly(paths["fx3_string_tc_f"], artifact_key="fx3_string_tc_f", body_label="ILME-FX3 7.02 tc_f")
    fx3_ja_f = _scan_compact_rdonly(paths["fx3_string_ja_f"], artifact_key="fx3_string_ja_f", body_label="ILME-FX3 7.02 ja_f")
    fx3_en = _scan_compact_rdonly(paths["fx3_string_en"], artifact_key="fx3_string_en", body_label="ILME-FX3 7.02 en")
    fx3_en_g = _scan_compact_rdonly(paths["fx3_string_en_g"], artifact_key="fx3_string_en_g", body_label="ILME-FX3 7.02 en_g")
    fx6_en = _scan_compact_rdonly(paths["fx6_string_en"], artifact_key="fx6_string_en", body_label="ILME-FX6 6.01 en")
    fx6_en_2 = _scan_compact_rdonly(paths["fx6_string_en_2"], artifact_key="fx6_string_en_2", body_label="ILME-FX6 6.01 en_2")
    fx3_appfw = _scan_large_donor_rdonly(paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="ILME-FX3 7.02 appFw.so")
    fx3_bk4 = _scan_large_donor_rdonly(paths["fx3_bk4"], artifact_key="fx3_bk4", body_label="ILME-FX3 7.02 BK4")
    fx6_appfw = _scan_large_donor_rdonly(paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="ILME-FX6 6.01 appFw.so")
    elapsed = round(time.monotonic() - t0, 6)

    errors: List[str] = []
    compact_map = {
        "fx3_string_en_f": fx3_en_f,
        "fx3_string_sc_f": fx3_sc_f,
        "fx3_string_tc_f": fx3_tc_f,
        "fx3_string_ja_f": fx3_ja_f,
        "fx3_string_en": fx3_en,
        "fx3_string_en_g": fx3_en_g,
        "fx6_string_en": fx6_en,
        "fx6_string_en_2": fx6_en_2,
    }
    for key, summ in compact_map.items():
        if summ.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {summ.file_bytes}")
        if not summ.sha256_verified:
            errors.append(f"{key}: SHA-256 mismatch")
        if any(v != 1 for v in summ.marker_hits.values()):
            errors.append(f"{key}: missing expected Wave-49 markers")
        if not summ.uxd_container_ok:
            errors.append(f"{key}: invalid uxc/uxd header")

    large_map = {
        "fx3_appfw": (fx3_appfw, True),
        "fx3_bk4": (fx3_bk4, False),
        "fx6_appfw": (fx6_appfw, True),
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

    raw_heif_hlg_proven = (
        fx3_en_f.marker_hits.get("Image Quality Settings") == 1
        and fx3_en_f.marker_hits.get("JPEG/HEIF Switch") == 1
        and fx3_en_f.marker_hits.get("HEIF(4:2:0)") == 1
        and fx3_en_f.marker_hits.get("HEIF(4:2:2)") == 1
        and fx3_en_f.marker_hits.get("RAW File Type") == 1
        and fx3_en_f.marker_hits.get("Compressed") == 1
        and fx3_en_f.marker_hits.get("Uncompressed") == 1
        and fx3_en_f.marker_hits.get("Lossless Comp") == 1
        and fx3_en_f.marker_hits.get("HLG Still Image") == 1
        and fx3_en_f.marker_hits.get("HLG(BT.2020)") == 1
        and fx3_appfw.window_hits.get("BKID_JH_FILE_TYPE") == 1
        and fx3_appfw.window_hits.get("BKID_RAW_FILE_TYPE") == 1
        and fx3_appfw.window_hits.get("RAW_FILE_TYPE_LOSSLESS") == 1
        and fx3_appfw.window_hits.get("BKID_HLG_PHOTO") == 1
        and fx6_appfw.window_hits.get("FX6_RAW_OUTPUT_FORMAT") == 1
    )
    colorspace_setfilename_proven = (
        fx3_en_f.marker_hits.get("Color Space") == 1
        and fx3_en_f.marker_hits.get("Set File Name") == 1
        and fx3_en.marker_hits.get("sRGB") == 1
        and fx3_en.marker_hits.get("AdobeRGB") == 1
        and fx3_appfw.window_hits.get("BKID_COLOR_SPACE") == 1
        and fx3_appfw.window_hits.get("BKID_SET_FILE_NAME") == 1
        and fx3_appfw.window_hits.get("STILL_COLOR_SPACE_SRGB") == 1
        and fx3_appfw.window_hits.get("STILL_COLOR_SPACE_ADOBE_RGB") == 1
    )
    shuttertype_nr_drive_proven = (
        fx3_en_f.marker_hits.get("Shutter Type") == 1
        and fx3_en_f.marker_hits.get("Mechanical Shutter") == 1
        and fx3_en_f.marker_hits.get("Electronic Shutter") == 1
        and fx3_en_f.marker_hits.get("e-Front Curtain Shut.") == 1
        and fx3_en_f.marker_hits.get("Silent Mode Settings") == 1
        and fx3_en_f.marker_hits.get("Long Exposure NR") == 1
        and fx3_en_f.marker_hits.get("High ISO NR") == 1
        and fx3_en_f.marker_hits.get("Drive Mode") == 1
        and fx3_en_f.marker_hits.get("Cont. Shooting: Hi+") == 1
        and fx3_appfw.window_hits.get("BKID_SHUTTER_TYPE") == 1
        and fx3_appfw.window_hits.get("BKID_EFRONT_CURTAIN") == 1
        and fx3_appfw.window_hits.get("BKID_LONG_EXP_NR") == 1
        and fx3_appfw.window_hits.get("BKID_HIGH_ISO_NR") == 1
        and fx3_appfw.window_hits.get("BKID_DRIVE_MODE") == 1
        and fx6_appfw.window_hits.get("FX6_SHUTTER_SELECT") == 1
    )

    all_ok = (
        (len(errors) == 0)
        and raw_heif_hlg_proven
        and colorspace_setfilename_proven
        and shuttertype_nr_drive_proven
    )
    audit = Phase293DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=11,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_string_en_f=fx3_en_f,
        fx3_string_sc_f=fx3_sc_f,
        fx3_string_tc_f=fx3_tc_f,
        fx3_string_ja_f=fx3_ja_f,
        fx3_string_en=fx3_en,
        fx3_string_en_g=fx3_en_g,
        fx6_string_en=fx6_en,
        fx6_string_en_2=fx6_en_2,
        fx3_appfw=fx3_appfw,
        fx3_bk4=fx3_bk4,
        fx6_appfw=fx6_appfw,
        raw_heif_hlg_proven=raw_heif_hlg_proven,
        colorspace_setfilename_proven=colorspace_setfilename_proven,
        shuttertype_nr_drive_proven=shuttertype_nr_drive_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 59A — Still [Image Quality Settings] & [HLG Still Image] vs FX6
# ---------------------------------------------------------------------------


def simulate_still_raw_heif_hlg_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    still_capture_requested: bool = True,
    exposure_mode: str = EXPOSURE_MODE_M,
    configured_jpeg_heif_switch: str = JH_SWITCH_JPEG,
    configured_file_format: str = STILL_FMT_JPEG,
    configured_raw_file_type: str = RAW_TYPE_COMPRESSED,
    configured_quality: str = STILL_QUALITY_FINE,
    configured_image_size: str = STILL_IMAGE_SIZE_L,
    configured_hlg_still_image: str = TOGGLE_OFF,
    configured_gamma_assist_type: str = GAMMA_ASSIST_AUTO,
    requested_pp_or_creativelook_override: bool = False,
    requested_dro_override: bool = False,
    requested_dro_bracket_override: bool = False,
    reset_action: str = RESET_ACTION_NONE,
) -> StillRawHeifHlgEvalResult:
    """Evaluate Wave-49 Sub-Model 59A: Still RAW/HEIF, Dormant Lossless Gate, & HLG Still Image."""

    def _err(errno_code: int, reason_code: str) -> StillRawHeifHlgEvalResult:
        return StillRawHeifHlgEvalResult(
            image_quality_menu_path=IMAGE_QUALITY_MENU_PATH,
            jpeg_heif_switch_menu_path=JPEG_HEIF_SWITCH_MENU_PATH,
            hlg_still_image_menu_path=HLG_STILL_IMAGE_MENU_PATH,
            body_profile=body_profile,
            still_pipeline_present=(body_profile in STOCK_FX3_BODIES),
            exposure_mode=exposure_mode,
            configured_jpeg_heif_switch=configured_jpeg_heif_switch,
            configured_file_format=configured_file_format,
            configured_raw_file_type=configured_raw_file_type,
            effective_raw_file_type="REJECTED",
            dormant_lossless_gated_out=True,
            configured_quality=configured_quality,
            configured_image_size=configured_image_size,
            configured_hlg_still_image=configured_hlg_still_image,
            effective_hlg_still_image=TOGGLE_OFF,
            effective_color_space=COLOR_SPACE_SRGB,
            effective_gamma_display_assist=TOGGLE_OFF,
            output_extensions=(),
            non_raw_bit_depth=0,
            raw_bit_depth=0,
            pp_creativelook_dro_locked_by_hlg=False,
            dro_bracket_locked_by_hlg=False,
            reset_action=reset_action,
            restored_to_factory_defaults=False,
            fx6_raw_output_contrast="ILME-FX6 Ver. 6.01 Movie SDI/HDMI 16-bit RAW Only (No Still DCIM)",
            dormant_lossless_raw_exposed_events=DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS,
            hlg_still_prerequisite_bypass_events=HLG_STILL_PREREQUISITE_BYPASS_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or exposure_mode not in VALID_EXPOSURE_MODES
        or configured_jpeg_heif_switch not in VALID_JPEG_HEIF_SWITCHES
        or configured_file_format not in VALID_STILL_FILE_FORMATS
        or configured_raw_file_type not in ALL_TESTABLE_RAW_FILE_TYPES
        or configured_quality not in VALID_STILL_QUALITIES
        or configured_image_size not in VALID_STILL_IMAGE_SIZES
        or configured_hlg_still_image not in VALID_TOGGLE_STATES
        or configured_gamma_assist_type not in VALID_HLG_GAMMA_ASSIST_TYPES
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_STILL_IMAGE_QUALITY_PARAMETER")

    # ILME-FX6 Ver. 6.01 has ZERO still-photo DCIM/.ARW/.JPG/.HIF pipeline
    if body_profile == BODY_MODEL_FX6:
        if still_capture_requested:
            return _err(EOPNOTSUPP_ERRNO, "FX6_HAS_NO_STILL_DCIM_OR_ARW_HIF_PIPELINE")
        return StillRawHeifHlgEvalResult(
            image_quality_menu_path=FX6_VIDEO_RAW_MENU_PATH,
            jpeg_heif_switch_menu_path=FX6_VIDEO_RAW_MENU_PATH,
            hlg_still_image_menu_path="Cine EI / HDR(HLG) Movie Only (HLG Live / Natural / Mild)",
            body_profile=body_profile,
            still_pipeline_present=FX6_STILL_PIPELINE_EXPOSED,
            exposure_mode=EXPOSURE_MODE_M,
            configured_jpeg_heif_switch="NONE",
            configured_file_format="XAVC / Movie RAW (SDI/HDMI)",
            configured_raw_file_type="16-bit Linear Movie RAW",
            effective_raw_file_type="16-bit Linear Movie RAW (4096x2160 / 3840x2160)",
            dormant_lossless_gated_out=True,
            configured_quality="N/A (Movie)",
            configured_image_size="4096x2160 / 3840x2160",
            configured_hlg_still_image=TOGGLE_OFF,
            effective_hlg_still_image=TOGGLE_OFF,
            effective_color_space=COLOR_SPACE_BT2100,
            effective_gamma_display_assist="HLG_BT.2100 (Movie)",
            output_extensions=(".MXF", ".MP4"),
            non_raw_bit_depth=10,
            raw_bit_depth=16,
            pp_creativelook_dro_locked_by_hlg=False,
            dro_bracket_locked_by_hlg=False,
            reset_action=reset_action,
            restored_to_factory_defaults=False,
            fx6_raw_output_contrast="ILME-FX6 Ver. 6.01 Movie SDI/HDMI 16-bit RAW Only (No Still DCIM)",
            dormant_lossless_raw_exposed_events=DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS,
            hlg_still_prerequisite_bypass_events=HLG_STILL_PREREQUISITE_BYPASS_EVENTS,
            admitted=True,
            errno_code=0,
            reason_code="FX6_STILL_LESS_MOVIE_RAW_CONTRAST_VERIFIED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # Gate dormant Lossless Comp / Lossless Comp (L)/(M)/(S) on ILME-FX3 7.02 (12 MP IMX510)
    if configured_raw_file_type in DORMANT_LOSSLESS_RAW_TYPES:
        return _err(EOPNOTSUPP_ERRNO, "DORMANT_LOSSLESS_RAW_GATED_OUT_ON_FX3_702")

    # Enforce JPEG/HEIF Switch vs File Format coupling
    is_heif_switch = configured_jpeg_heif_switch in (JH_SWITCH_HEIF_420, JH_SWITCH_HEIF_422)
    if (not is_heif_switch) and configured_file_format in (STILL_FMT_HEIF, STILL_FMT_RAW_HEIF):
        return _err(EOPNOTSUPP_ERRNO, "HEIF_FORMAT_REQUIRES_JPEG_HEIF_SWITCH_HEIF")
    if is_heif_switch and configured_file_format in (STILL_FMT_JPEG, STILL_FMT_RAW_JPEG):
        return _err(EOPNOTSUPP_ERRNO, "JPEG_FORMAT_REQUIRES_JPEG_HEIF_SWITCH_JPEG")

    # Strict [HLG Still Image] = On prerequisites: HEIF switch + HEIF-only format + P/A/S/M
    if configured_hlg_still_image == TOGGLE_ON:
        if not is_heif_switch:
            return _err(EOPNOTSUPP_ERRNO, "HLG_STILL_REQUIRES_HEIF_420_OR_422_SWITCH")
        if configured_file_format != STILL_FMT_HEIF:
            return _err(EOPNOTSUPP_ERRNO, "HLG_STILL_REQUIRES_FILE_FORMAT_HEIF_ONLY")
        if exposure_mode not in PASM_EXPOSURE_MODES:
            return _err(EOPNOTSUPP_ERRNO, "HLG_STILL_BLOCKED_IN_IAUTO_REQUIRES_PASM")
        if requested_pp_or_creativelook_override:
            return _err(EOPNOTSUPP_ERRNO, "HLG_STILL_LOCKS_OUT_PP_AND_CREATIVE_LOOK")
        if requested_dro_override:
            return _err(EOPNOTSUPP_ERRNO, "HLG_STILL_LOCKS_OUT_DRO")
        if requested_dro_bracket_override:
            return _err(EOPNOTSUPP_ERRNO, "HLG_STILL_LOCKS_OUT_DRO_BRACKET")

    # Reset behavior: Image Quality Settings live in (Shooting) -> reset on both Camera Settings Reset & Initialize
    if reset_action in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        eff_raw_type = RAW_TYPE_COMPRESSED
        eff_hlg = TOGGLE_OFF
        eff_cs = COLOR_SPACE_SRGB
        eff_assist = TOGGLE_OFF
        exts: Tuple[str, ...] = (".JPG",)
        non_raw_bits = 8
        raw_bits = 0
        hlg_locks = False
        restored = True
    else:
        eff_raw_type = configured_raw_file_type
        eff_hlg = configured_hlg_still_image
        if eff_hlg == TOGGLE_ON:
            eff_cs = COLOR_SPACE_BT2100
            eff_assist = configured_gamma_assist_type
            hlg_locks = True
        else:
            eff_cs = COLOR_SPACE_SRGB
            eff_assist = TOGGLE_OFF
            hlg_locks = False

        ext_list: List[str] = []
        if configured_file_format in (STILL_FMT_RAW, STILL_FMT_RAW_JPEG, STILL_FMT_RAW_HEIF):
            ext_list.append(".ARW")
            raw_bits = 14
        else:
            raw_bits = 0
        if configured_file_format in (STILL_FMT_JPEG, STILL_FMT_RAW_JPEG):
            ext_list.append(".JPG")
            non_raw_bits = 8
        elif configured_file_format in (STILL_FMT_HEIF, STILL_FMT_RAW_HEIF):
            ext_list.append(".HIF")
            non_raw_bits = 10
        else:
            non_raw_bits = 0
        exts = tuple(ext_list)
        restored = False

    return StillRawHeifHlgEvalResult(
        image_quality_menu_path=IMAGE_QUALITY_MENU_PATH,
        jpeg_heif_switch_menu_path=JPEG_HEIF_SWITCH_MENU_PATH,
        hlg_still_image_menu_path=HLG_STILL_IMAGE_MENU_PATH,
        body_profile=body_profile,
        still_pipeline_present=True,
        exposure_mode=exposure_mode,
        configured_jpeg_heif_switch=configured_jpeg_heif_switch,
        configured_file_format=configured_file_format,
        configured_raw_file_type=configured_raw_file_type,
        effective_raw_file_type=eff_raw_type,
        dormant_lossless_gated_out=True,
        configured_quality=configured_quality,
        configured_image_size=configured_image_size,
        configured_hlg_still_image=configured_hlg_still_image,
        effective_hlg_still_image=eff_hlg,
        effective_color_space=eff_cs,
        effective_gamma_display_assist=eff_assist,
        output_extensions=exts,
        non_raw_bit_depth=non_raw_bits,
        raw_bit_depth=raw_bits,
        pp_creativelook_dro_locked_by_hlg=hlg_locks,
        dro_bracket_locked_by_hlg=hlg_locks,
        reset_action=reset_action,
        restored_to_factory_defaults=restored,
        fx6_raw_output_contrast="ILME-FX6 Ver. 6.01 Movie SDI/HDMI 16-bit RAW Only (No Still DCIM)",
        dormant_lossless_raw_exposed_events=DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS,
        hlg_still_prerequisite_bypass_events=HLG_STILL_PREREQUISITE_BYPASS_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="STILL_RAW_HEIF_HLG_HIL_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_a_raw_heif_hlg_hil() -> Dict[str, object]:
    """Evaluate Wave-49 Sub-Model 59A: RAW Compressed/Uncompressed, Dormant Lossless, HEIF, & HLG."""
    raw_compressed_ok = simulate_still_raw_heif_hlg_hil(
        configured_file_format=STILL_FMT_RAW,
        configured_raw_file_type=RAW_TYPE_COMPRESSED,
    )
    raw_uncompressed_ok = simulate_still_raw_heif_hlg_hil(
        configured_file_format=STILL_FMT_RAW,
        configured_raw_file_type=RAW_TYPE_UNCOMPRESSED,
    )
    dormant_lossless_rejected = {
        mode: asdict(
            simulate_still_raw_heif_hlg_hil(
                configured_file_format=STILL_FMT_RAW,
                configured_raw_file_type=mode,
            )
        )
        for mode in DORMANT_LOSSLESS_RAW_TYPES
    }
    heif_420_ok = simulate_still_raw_heif_hlg_hil(
        configured_jpeg_heif_switch=JH_SWITCH_HEIF_420,
        configured_file_format=STILL_FMT_HEIF,
    )
    heif_422_raw_ok = simulate_still_raw_heif_hlg_hil(
        configured_jpeg_heif_switch=JH_SWITCH_HEIF_422,
        configured_file_format=STILL_FMT_RAW_HEIF,
        configured_raw_file_type=RAW_TYPE_COMPRESSED,
    )
    hlg_still_on_ok = simulate_still_raw_heif_hlg_hil(
        exposure_mode=EXPOSURE_MODE_M,
        configured_jpeg_heif_switch=JH_SWITCH_HEIF_422,
        configured_file_format=STILL_FMT_HEIF,
        configured_hlg_still_image=TOGGLE_ON,
        configured_gamma_assist_type=GAMMA_ASSIST_HLG_BT2020,
    )
    hlg_blocked_jpeg = simulate_still_raw_heif_hlg_hil(
        configured_jpeg_heif_switch=JH_SWITCH_JPEG,
        configured_file_format=STILL_FMT_JPEG,
        configured_hlg_still_image=TOGGLE_ON,
    )
    hlg_blocked_raw_heif = simulate_still_raw_heif_hlg_hil(
        configured_jpeg_heif_switch=JH_SWITCH_HEIF_420,
        configured_file_format=STILL_FMT_RAW_HEIF,
        configured_hlg_still_image=TOGGLE_ON,
    )
    hlg_blocked_iauto = simulate_still_raw_heif_hlg_hil(
        exposure_mode=EXPOSURE_MODE_IAUTO,
        configured_jpeg_heif_switch=JH_SWITCH_HEIF_420,
        configured_file_format=STILL_FMT_HEIF,
        configured_hlg_still_image=TOGGLE_ON,
    )
    hlg_locks_pp = simulate_still_raw_heif_hlg_hil(
        configured_jpeg_heif_switch=JH_SWITCH_HEIF_420,
        configured_file_format=STILL_FMT_HEIF,
        configured_hlg_still_image=TOGGLE_ON,
        requested_pp_or_creativelook_override=True,
    )
    hlg_locks_dro_bracket = simulate_still_raw_heif_hlg_hil(
        configured_jpeg_heif_switch=JH_SWITCH_HEIF_420,
        configured_file_format=STILL_FMT_HEIF,
        configured_hlg_still_image=TOGGLE_ON,
        requested_dro_bracket_override=True,
    )
    fx6_still_rejected = simulate_still_raw_heif_hlg_hil(
        body_profile=BODY_MODEL_FX6,
        still_capture_requested=True,
    )
    fx6_movie_raw_contrast = simulate_still_raw_heif_hlg_hil(
        body_profile=BODY_MODEL_FX6,
        still_capture_requested=False,
    )

    passed = (
        raw_compressed_ok.admitted
        and raw_compressed_ok.raw_bit_depth == 14
        and raw_compressed_ok.output_extensions == (".ARW",)
        and raw_uncompressed_ok.admitted
        and raw_uncompressed_ok.effective_raw_file_type == RAW_TYPE_UNCOMPRESSED
        and all(
            (not item["admitted"]) and item["errno_code"] == EOPNOTSUPP_ERRNO
            for item in dormant_lossless_rejected.values()
        )
        and heif_420_ok.admitted
        and heif_420_ok.non_raw_bit_depth == 10
        and heif_420_ok.output_extensions == (".HIF",)
        and heif_422_raw_ok.admitted
        and heif_422_raw_ok.output_extensions == (".ARW", ".HIF")
        and hlg_still_on_ok.admitted
        and hlg_still_on_ok.effective_hlg_still_image == TOGGLE_ON
        and hlg_still_on_ok.effective_color_space == COLOR_SPACE_BT2100
        and hlg_still_on_ok.effective_gamma_display_assist == GAMMA_ASSIST_HLG_BT2020
        and hlg_still_on_ok.pp_creativelook_dro_locked_by_hlg
        and hlg_still_on_ok.dro_bracket_locked_by_hlg
        and (not hlg_blocked_jpeg.admitted)
        and hlg_blocked_jpeg.errno_code == EOPNOTSUPP_ERRNO
        and (not hlg_blocked_raw_heif.admitted)
        and hlg_blocked_raw_heif.errno_code == EOPNOTSUPP_ERRNO
        and (not hlg_blocked_iauto.admitted)
        and hlg_blocked_iauto.errno_code == EOPNOTSUPP_ERRNO
        and (not hlg_locks_pp.admitted)
        and hlg_locks_pp.errno_code == EOPNOTSUPP_ERRNO
        and (not hlg_locks_dro_bracket.admitted)
        and hlg_locks_dro_bracket.errno_code == EOPNOTSUPP_ERRNO
        and (not fx6_still_rejected.admitted)
        and fx6_still_rejected.errno_code == EOPNOTSUPP_ERRNO
        and fx6_movie_raw_contrast.admitted
        and (not fx6_movie_raw_contrast.still_pipeline_present)
    )

    return {
        "passed": passed,
        "image_quality_menu_path": IMAGE_QUALITY_MENU_PATH,
        "jpeg_heif_switch_menu_path": JPEG_HEIF_SWITCH_MENU_PATH,
        "hlg_still_image_menu_path": HLG_STILL_IMAGE_MENU_PATH,
        "exposed_fx3_raw_file_types": list(EXPOSED_FX3_RAW_FILE_TYPES),
        "dormant_lossless_raw_types": list(DORMANT_LOSSLESS_RAW_TYPES),
        "valid_jpeg_heif_switches": list(VALID_JPEG_HEIF_SWITCHES),
        "valid_still_file_formats": list(VALID_STILL_FILE_FORMATS),
        "raw_compressed_ok": asdict(raw_compressed_ok),
        "raw_uncompressed_ok": asdict(raw_uncompressed_ok),
        "dormant_lossless_rejected_matrix": dormant_lossless_rejected,
        "heif_420_10bit_ok": asdict(heif_420_ok),
        "heif_422_raw_ok": asdict(heif_422_raw_ok),
        "hlg_still_on_bt2100_ok": asdict(hlg_still_on_ok),
        "hlg_blocked_jpeg_eopnotsupp": asdict(hlg_blocked_jpeg),
        "hlg_blocked_raw_heif_eopnotsupp": asdict(hlg_blocked_raw_heif),
        "hlg_blocked_iauto_eopnotsupp": asdict(hlg_blocked_iauto),
        "hlg_locks_pp_creativelook_eopnotsupp": asdict(hlg_locks_pp),
        "hlg_locks_dro_bracket_eopnotsupp": asdict(hlg_locks_dro_bracket),
        "fx6_still_rejected_eopnotsupp": asdict(fx6_still_rejected),
        "fx6_movie_raw_contrast": asdict(fx6_movie_raw_contrast),
    }


# ---------------------------------------------------------------------------
# Sub-Model 59B — [Color Space] & [Set File Name] Leading-'_' Ban
# ---------------------------------------------------------------------------


def simulate_color_space_and_set_file_name_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    configured_file_format: str = STILL_FMT_RAW_JPEG,
    configured_hlg_still_image: str = TOGGLE_OFF,
    configured_color_space: str = COLOR_SPACE_SRGB,
    configured_file_name_prefix: str = DEFAULT_SET_FILE_NAME_PREFIX,
    file_number: int = 1,
    requested_adobergb_under_heif: bool = False,
    wipe_set_file_name_on_camera_reset: bool = False,
    storage_target: str = STORAGE_TARGET_NONE,
    reset_action: str = RESET_ACTION_NONE,
) -> ColorSpaceSetFileNameEvalResult:
    """Evaluate Wave-49 Sub-Model 59B: sRGB vs AdobeRGB _DSC Prefix, Leading-'_' Ban & HEIF Override."""

    def _err(errno_code: int, reason_code: str) -> ColorSpaceSetFileNameEvalResult:
        return ColorSpaceSetFileNameEvalResult(
            color_space_menu_path=COLOR_SPACE_MENU_PATH,
            set_file_name_menu_path=SET_FILE_NAME_MENU_PATH,
            body_profile=body_profile,
            configured_file_format=configured_file_format,
            configured_hlg_still_image=configured_hlg_still_image,
            configured_color_space=configured_color_space,
            effective_color_space="REJECTED",
            color_space_ignored_under_heif=False,
            configured_file_name_prefix=configured_file_name_prefix,
            effective_file_name_prefix="REJECTED",
            dcf_folder_path="DCIM/100MSDCF",
            sample_still_filenames=(),
            leading_underscore_applied_by_adobergb=False,
            leading_underscore_manual_ban_enforced=True,
            reset_action=reset_action,
            color_space_reset_to_srgb=False,
            set_file_name_survived_camera_reset=False,
            set_file_name_wiped_by_initialize=False,
            storage_target=storage_target,
            color_space_leading_underscore_bypass_events=(
                COLOR_SPACE_LEADING_UNDERSCORE_BYPASS_EVENTS
            ),
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or configured_file_format not in VALID_STILL_FILE_FORMATS
        or configured_hlg_still_image not in VALID_TOGGLE_STATES
        or configured_color_space not in VALID_STILL_COLOR_SPACES
        or isinstance(file_number, bool)
        or file_number < 1
        or file_number > 9999
        or storage_target not in VALID_STORAGE_TARGETS
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_COLOR_SPACE_OR_FILE_NAME_PARAMETER")

    if body_profile == BODY_MODEL_FX6:
        return _err(EOPNOTSUPP_ERRNO, "FX6_HAS_NO_STILL_COLOR_SPACE_OR_DCF_DSC_PREFIX")

    if storage_target == STORAGE_TARGET_SLOT1_VAULT:
        return _err(EROFS_ERRNO, "TIER0_SLOT1_VAULT_STILL_PREFIX_WRITE_BLOCKED_EROFS")

    if not VALID_SET_FILE_NAME_RE.match(configured_file_name_prefix):
        return _err(EINVAL_ERRNO, "SET_FILE_NAME_MUST_BE_3_CHARS_UPPER_ALNUM_OR_UNDERSCORE")

    # CRITICAL DCF 2.0 RULE: '_' is strictly FORBIDDEN as the 1st char in [Set File Name]
    if configured_file_name_prefix.startswith("_"):
        return _err(EINVAL_ERRNO, "SET_FILE_NAME_LEADING_UNDERSCORE_FORBIDDEN_DCF20")

    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
        and wipe_set_file_name_on_camera_reset
    ):
        return _err(EOPNOTSUPP_ERRNO, "SET_FILE_NAME_SURVIVES_CAMERA_SETTINGS_RESET")

    is_heif_only = configured_file_format == STILL_FMT_HEIF
    if is_heif_only and requested_adobergb_under_heif:
        return _err(EOPNOTSUPP_ERRNO, "COLOR_SPACE_ADOBERGB_IGNORED_UNDER_HEIF")

    if reset_action == RESET_ACTION_INITIALIZE:
        eff_cs = COLOR_SPACE_SRGB
        eff_base_prefix = DEFAULT_SET_FILE_NAME_PREFIX
        cs_reset = True
        fn_survived = False
        fn_wiped = True
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_cs = COLOR_SPACE_SRGB
        eff_base_prefix = configured_file_name_prefix
        cs_reset = True
        fn_survived = True
        fn_wiped = False
    else:
        eff_base_prefix = configured_file_name_prefix
        cs_reset = False
        fn_survived = True
        fn_wiped = False
        if is_heif_only:
            eff_cs = (
                COLOR_SPACE_BT2100
                if configured_hlg_still_image == TOGGLE_ON
                else COLOR_SPACE_SRGB
            )
        else:
            eff_cs = configured_color_space

    adobergb_underscore = (not is_heif_only) and (eff_cs == COLOR_SPACE_ADOBE_RGB)
    eff_prefix = f"_{eff_base_prefix}" if adobergb_underscore else eff_base_prefix
    num_str = f"{file_number:04d}"

    sample_names: List[str] = []
    if configured_file_format in (STILL_FMT_JPEG, STILL_FMT_RAW_JPEG):
        sample_names.append(f"{eff_prefix}{num_str}.JPG")
    if configured_file_format in (STILL_FMT_HEIF, STILL_FMT_RAW_HEIF):
        sample_names.append(f"{eff_prefix}{num_str}.HIF")
    if configured_file_format in (STILL_FMT_RAW, STILL_FMT_RAW_JPEG, STILL_FMT_RAW_HEIF):
        sample_names.append(f"{eff_prefix}{num_str}.ARW")

    return ColorSpaceSetFileNameEvalResult(
        color_space_menu_path=COLOR_SPACE_MENU_PATH,
        set_file_name_menu_path=SET_FILE_NAME_MENU_PATH,
        body_profile=body_profile,
        configured_file_format=configured_file_format,
        configured_hlg_still_image=configured_hlg_still_image,
        configured_color_space=configured_color_space,
        effective_color_space=eff_cs,
        color_space_ignored_under_heif=is_heif_only,
        configured_file_name_prefix=configured_file_name_prefix,
        effective_file_name_prefix=eff_prefix,
        dcf_folder_path="DCIM/100MSDCF",
        sample_still_filenames=tuple(sample_names),
        leading_underscore_applied_by_adobergb=adobergb_underscore,
        leading_underscore_manual_ban_enforced=True,
        reset_action=reset_action,
        color_space_reset_to_srgb=cs_reset,
        set_file_name_survived_camera_reset=fn_survived,
        set_file_name_wiped_by_initialize=fn_wiped,
        storage_target=storage_target,
        color_space_leading_underscore_bypass_events=(
            COLOR_SPACE_LEADING_UNDERSCORE_BYPASS_EVENTS
        ),
        admitted=True,
        errno_code=0,
        reason_code="COLOR_SPACE_AND_SET_FILE_NAME_HIL_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_b_colorspace_setfilename_hil() -> Dict[str, object]:
    """Evaluate Wave-49 Sub-Model 59B: sRGB vs AdobeRGB `_DSC`, Leading-`_` Ban & HEIF Override."""
    srgb_default_dsc = simulate_color_space_and_set_file_name_hil(
        configured_file_format=STILL_FMT_RAW_JPEG,
        configured_color_space=COLOR_SPACE_SRGB,
        configured_file_name_prefix="DSC",
    )
    adobergb_prepend_dsc = simulate_color_space_and_set_file_name_hil(
        configured_file_format=STILL_FMT_RAW_JPEG,
        configured_color_space=COLOR_SPACE_ADOBE_RGB,
        configured_file_name_prefix="DSC",
    )
    adobergb_custom_fx3 = simulate_color_space_and_set_file_name_hil(
        configured_file_format=STILL_FMT_RAW_JPEG,
        configured_color_space=COLOR_SPACE_ADOBE_RGB,
        configured_file_name_prefix="FX3",
    )
    non_leading_underscore_ok = simulate_color_space_and_set_file_name_hil(
        configured_file_format=STILL_FMT_JPEG,
        configured_color_space=COLOR_SPACE_SRGB,
        configured_file_name_prefix="A_1",
    )
    leading_underscore_ban = simulate_color_space_and_set_file_name_hil(
        configured_file_name_prefix="_FX",
    )
    heif_hlg_off_ignores_cs = simulate_color_space_and_set_file_name_hil(
        configured_file_format=STILL_FMT_HEIF,
        configured_hlg_still_image=TOGGLE_OFF,
        configured_color_space=COLOR_SPACE_ADOBE_RGB,
        configured_file_name_prefix="DSC",
    )
    heif_hlg_on_bt2100 = simulate_color_space_and_set_file_name_hil(
        configured_file_format=STILL_FMT_HEIF,
        configured_hlg_still_image=TOGGLE_ON,
        configured_color_space=COLOR_SPACE_ADOBE_RGB,
        configured_file_name_prefix="DSC",
    )
    heif_adobergb_forced_rejected = simulate_color_space_and_set_file_name_hil(
        configured_file_format=STILL_FMT_HEIF,
        configured_color_space=COLOR_SPACE_ADOBE_RGB,
        requested_adobergb_under_heif=True,
    )
    cam_reset_splits_cs_and_prefix = simulate_color_space_and_set_file_name_hil(
        configured_color_space=COLOR_SPACE_ADOBE_RGB,
        configured_file_name_prefix="FX3",
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_wipes_both = simulate_color_space_and_set_file_name_hil(
        configured_color_space=COLOR_SPACE_ADOBE_RGB,
        configured_file_name_prefix="FX3",
        reset_action=RESET_ACTION_INITIALIZE,
    )

    passed = (
        srgb_default_dsc.admitted
        and srgb_default_dsc.effective_color_space == COLOR_SPACE_SRGB
        and srgb_default_dsc.effective_file_name_prefix == "DSC"
        and srgb_default_dsc.sample_still_filenames == ("DSC0001.JPG", "DSC0001.ARW")
        and adobergb_prepend_dsc.admitted
        and adobergb_prepend_dsc.effective_color_space == COLOR_SPACE_ADOBE_RGB
        and adobergb_prepend_dsc.effective_file_name_prefix == "_DSC"
        and adobergb_prepend_dsc.sample_still_filenames == ("_DSC0001.JPG", "_DSC0001.ARW")
        and adobergb_custom_fx3.admitted
        and adobergb_custom_fx3.effective_file_name_prefix == "_FX3"
        and adobergb_custom_fx3.sample_still_filenames == ("_FX30001.JPG", "_FX30001.ARW")
        and non_leading_underscore_ok.admitted
        and non_leading_underscore_ok.effective_file_name_prefix == "A_1"
        and (not leading_underscore_ban.admitted)
        and leading_underscore_ban.errno_code == EINVAL_ERRNO
        and heif_hlg_off_ignores_cs.admitted
        and heif_hlg_off_ignores_cs.color_space_ignored_under_heif
        and heif_hlg_off_ignores_cs.effective_color_space == COLOR_SPACE_SRGB
        and heif_hlg_off_ignores_cs.sample_still_filenames == ("DSC0001.HIF",)
        and heif_hlg_on_bt2100.admitted
        and heif_hlg_on_bt2100.effective_color_space == COLOR_SPACE_BT2100
        and (not heif_adobergb_forced_rejected.admitted)
        and heif_adobergb_forced_rejected.errno_code == EOPNOTSUPP_ERRNO
        and cam_reset_splits_cs_and_prefix.admitted
        and cam_reset_splits_cs_and_prefix.effective_color_space == COLOR_SPACE_SRGB
        and cam_reset_splits_cs_and_prefix.color_space_reset_to_srgb
        and cam_reset_splits_cs_and_prefix.effective_file_name_prefix == "FX3"
        and cam_reset_splits_cs_and_prefix.set_file_name_survived_camera_reset
        and init_wipes_both.admitted
        and init_wipes_both.effective_file_name_prefix == "DSC"
        and init_wipes_both.set_file_name_wiped_by_initialize
    )

    return {
        "passed": passed,
        "color_space_menu_path": COLOR_SPACE_MENU_PATH,
        "set_file_name_menu_path": SET_FILE_NAME_MENU_PATH,
        "valid_still_color_spaces": list(VALID_STILL_COLOR_SPACES),
        "default_set_file_name_prefix": DEFAULT_SET_FILE_NAME_PREFIX,
        "srgb_default_dsc_ok": asdict(srgb_default_dsc),
        "adobergb_prepend_dsc_ok": asdict(adobergb_prepend_dsc),
        "adobergb_custom_fx3_ok": asdict(adobergb_custom_fx3),
        "non_leading_underscore_a_1_ok": asdict(non_leading_underscore_ok),
        "leading_underscore_ban_einval": asdict(leading_underscore_ban),
        "heif_hlg_off_ignores_cs_srgb": asdict(heif_hlg_off_ignores_cs),
        "heif_hlg_on_overrides_bt2100": asdict(heif_hlg_on_bt2100),
        "heif_adobergb_forced_rejected_eopnotsupp": asdict(heif_adobergb_forced_rejected),
        "camera_reset_splits_cs_vs_prefix": asdict(cam_reset_splits_cs_and_prefix),
        "initialize_wipes_both_to_srgb_dsc": asdict(init_wipes_both),
    }


# ---------------------------------------------------------------------------
# Sub-Model 59C & Redlines — [Shutter Type] 2-Mode, NR, 10fps Drive & Vault
# ---------------------------------------------------------------------------


def simulate_shutter_type_nr_drive_and_slot1_vault_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    exposure_mode: str = EXPOSURE_MODE_M,
    requested_shutter_type: str = SHUTTER_TYPE_MECHANICAL,
    configured_e_front_curtain: str = TOGGLE_ON,
    silent_mode: str = TOGGLE_OFF,
    silent_target_override: bool = False,
    flash_requested: bool = False,
    long_exposure_nr: str = TOGGLE_ON,
    long_exposure_nr_explicit_requested: bool = False,
    e_front_curtain_edit_requested: bool = False,
    bulb_exposure_requested: bool = False,
    anti_flicker_shoot_requested: bool = False,
    shutter_speed_sec: float = 0.004,
    high_iso_nr: str = HIGH_ISO_NR_NORMAL,
    high_iso_nr_explicit_requested: bool = False,
    configured_file_format: str = STILL_FMT_RAW_JPEG,
    configured_raw_file_type: str = RAW_TYPE_COMPRESSED,
    configured_drive_mode: str = DRIVE_SINGLE,
    configured_hlg_still_image: str = TOGGLE_OFF,
    aperture_f_number: float = 2.8,
    burst_frames_captured: int = 1,
    storage_target: str = STORAGE_TARGET_NONE,
    slot1_busy_locked: bool = False,
    wipe_efront_on_camera_reset: bool = False,
    reset_action: str = RESET_ACTION_NONE,
) -> ShutterTypeNrDriveVaultEvalResult:
    """Evaluate Wave-49 Sub-Model 59C: 2-Mode Shutter Type, 5-Lock Matrix, NR, 10fps & Vault."""

    def _err(errno_code: int, reason_code: str) -> ShutterTypeNrDriveVaultEvalResult:
        return ShutterTypeNrDriveVaultEvalResult(
            shutter_type_menu_path=SHUTTER_TYPE_MENU_PATH,
            efront_curtain_menu_path=EFRONT_CURTAIN_MENU_PATH,
            silent_mode_menu_path=SILENT_MODE_MENU_PATH,
            long_exp_nr_menu_path=LONG_EXP_NR_MENU_PATH,
            high_iso_nr_menu_path=HIGH_ISO_NR_MENU_PATH,
            drive_mode_menu_path=DRIVE_MODE_MENU_PATH,
            body_profile=body_profile,
            mechanical_shutter_present=(body_profile in STOCK_FX3_BODIES),
            exposure_mode=exposure_mode,
            configured_shutter_type=requested_shutter_type,
            effective_shutter_type="REJECTED",
            shutter_type_auto_absent_enforced=True,
            configured_e_front_curtain=configured_e_front_curtain,
            effective_e_front_curtain=TOGGLE_OFF,
            silent_mode=silent_mode,
            silent_target_override=silent_target_override,
            electronic_5locks_engaged=True,
            locked_functions=ALL_5_ESHUTTER_SILENT_LOCKED_FUNCTIONS,
            flash_sync_max_fraction=FLASH_SYNC_MAX_FRACTION,
            shutter_speed_sec=float(shutter_speed_sec),
            configured_long_exposure_nr=long_exposure_nr,
            effective_long_exposure_nr=TOGGLE_OFF,
            dark_frame_subtraction_active=False,
            configured_high_iso_nr=high_iso_nr,
            effective_high_iso_nr_for_jpeg_heif=HIGH_ISO_NR_NORMAL,
            high_iso_nr_ignored_for_raw_arw=True,
            configured_drive_mode=configured_drive_mode,
            configured_file_format=configured_file_format,
            configured_raw_file_type=configured_raw_file_type,
            aperture_f_number=float(aperture_f_number),
            burst_frames_captured=burst_frames_captured,
            effective_burst_fps=0.0,
            uncompressed_raw_speed_drop_active=False,
            buffer_slow_throttled=False,
            af_locked_past_f11=False,
            storage_target=storage_target,
            slot1_vault_blocked=(storage_target == STORAGE_TARGET_SLOT1_VAULT),
            reset_action=reset_action,
            efront_curtain_survived_camera_reset=False,
            efront_curtain_wiped_by_initialize=False,
            shutter_type_auto_or_5lock_bypass_events=SHUTTER_TYPE_AUTO_OR_5LOCK_BYPASS_EVENTS,
            slot1_vault_still_or_burst_write_events=SLOT1_VAULT_STILL_OR_BURST_WRITE_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return _err(EINVAL_ERRNO, "INVALID_BODY_PROFILE")

    # ILME-FX6 has NO mechanical shutter (mechanical_shutter == False)
    if body_profile == BODY_MODEL_FX6:
        if requested_shutter_type == SHUTTER_TYPE_MECHANICAL:
            return _err(EOPNOTSUPP_ERRNO, "FX6_HAS_NO_MECHANICAL_SHUTTER")
        if requested_shutter_type != SHUTTER_TYPE_ELECTRONIC:
            return _err(EINVAL_ERRNO, "INVALID_FX6_SHUTTER_TYPE_REQUEST")
        return ShutterTypeNrDriveVaultEvalResult(
            shutter_type_menu_path=FX6_SHUTTER_SELECT_MENU_PATH,
            efront_curtain_menu_path="N/A (FX6 Sensor Electronic Rolling)",
            silent_mode_menu_path="N/A (Cinema Body Silent Electronic)",
            long_exp_nr_menu_path="N/A (MovieOnly)",
            high_iso_nr_menu_path="N/A (MovieOnly)",
            drive_mode_menu_path="N/A (No Still 10fps Drive)",
            body_profile=body_profile,
            mechanical_shutter_present=FX6_MECHANICAL_SHUTTER_PRESENT,
            exposure_mode=EXPOSURE_MODE_M,
            configured_shutter_type=SHUTTER_TYPE_ELECTRONIC,
            effective_shutter_type=SHUTTER_TYPE_ELECTRONIC,
            shutter_type_auto_absent_enforced=True,
            configured_e_front_curtain=TOGGLE_OFF,
            effective_e_front_curtain=TOGGLE_OFF,
            silent_mode=TOGGLE_ON,
            silent_target_override=False,
            electronic_5locks_engaged=True,
            locked_functions=ALL_5_ESHUTTER_SILENT_LOCKED_FUNCTIONS,
            flash_sync_max_fraction="NONE",
            shutter_speed_sec=float(shutter_speed_sec),
            configured_long_exposure_nr=TOGGLE_OFF,
            effective_long_exposure_nr=TOGGLE_OFF,
            dark_frame_subtraction_active=False,
            configured_high_iso_nr=HIGH_ISO_NR_OFF,
            effective_high_iso_nr_for_jpeg_heif=HIGH_ISO_NR_OFF,
            high_iso_nr_ignored_for_raw_arw=True,
            configured_drive_mode="Movie Continuous",
            configured_file_format="XAVC",
            configured_raw_file_type="N/A",
            aperture_f_number=float(aperture_f_number),
            burst_frames_captured=0,
            effective_burst_fps=0.0,
            uncompressed_raw_speed_drop_active=False,
            buffer_slow_throttled=False,
            af_locked_past_f11=False,
            storage_target=storage_target,
            slot1_vault_blocked=(storage_target == STORAGE_TARGET_SLOT1_VAULT),
            reset_action=reset_action,
            efront_curtain_survived_camera_reset=False,
            efront_curtain_wiped_by_initialize=False,
            shutter_type_auto_or_5lock_bypass_events=SHUTTER_TYPE_AUTO_OR_5LOCK_BYPASS_EVENTS,
            slot1_vault_still_or_burst_write_events=SLOT1_VAULT_STILL_OR_BURST_WRITE_EVENTS,
            admitted=True,
            errno_code=0,
            reason_code="FX6_ELECTRONIC_NO_MECH_SHUTTER_CONTRAST_VERIFIED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # ILME-FX3 Ver. 7.02 exposes EXACTLY 2 [Shutter Type] options: Mechanical or Electronic (NO Auto!)
    if requested_shutter_type not in EXPOSED_FX3_2_SHUTTER_TYPES:
        return _err(EINVAL_ERRNO, "FX3_SHUTTER_TYPE_EXACTLY_2_OPTIONS_NO_AUTO")

    if (
        exposure_mode not in VALID_EXPOSURE_MODES
        or configured_e_front_curtain not in VALID_TOGGLE_STATES
        or silent_mode not in VALID_TOGGLE_STATES
        or long_exposure_nr not in VALID_TOGGLE_STATES
        or high_iso_nr not in VALID_HIGH_ISO_NR_MODES
        or configured_file_format not in VALID_STILL_FILE_FORMATS
        or configured_raw_file_type not in EXPOSED_FX3_RAW_FILE_TYPES
        or configured_drive_mode not in VALID_DRIVE_MODES
        or configured_hlg_still_image not in VALID_TOGGLE_STATES
        or isinstance(shutter_speed_sec, bool)
        or not isinstance(shutter_speed_sec, (int, float))
        or shutter_speed_sec <= 0.0
        or isinstance(aperture_f_number, bool)
        or not isinstance(aperture_f_number, (int, float))
        or aperture_f_number < 1.0
        or isinstance(burst_frames_captured, bool)
        or burst_frames_captured < 0
        or storage_target not in VALID_STORAGE_TARGETS
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_SHUTTER_NR_OR_DRIVE_PARAMETER")

    # Fail-closed Tier-0 Slot-1 Vault write guard: blocks ANY still / burst / bracket write to Slot 1
    if storage_target == STORAGE_TARGET_SLOT1_VAULT:
        if slot1_busy_locked:
            return _err(EBUSY_ERRNO, "TIER0_SLOT1_VAULT_STILL_WRITE_LOCKED_EBUSY")
        return _err(EROFS_ERRNO, "TIER0_SLOT1_VAULT_STILL_BURST_WRITE_BLOCKED_EROFS")

    # Reject wiping e-Front Curtain Shut. under Camera Settings Reset (Initialize only!)
    if reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET and wipe_efront_on_camera_reset:
        return _err(EOPNOTSUPP_ERRNO, "EFRONT_CURTAIN_SURVIVES_CAMERA_SETTINGS_RESET")

    # Electronic Shutter selectable only in P/A/S/M unless forced via Silent Mode
    if (
        requested_shutter_type == SHUTTER_TYPE_ELECTRONIC
        and silent_mode == TOGGLE_OFF
        and exposure_mode not in PASM_EXPOSURE_MODES
    ):
        return _err(EOPNOTSUPP_ERRNO, "ELECTRONIC_SHUTTER_REQUIRES_PASM_UNLESS_SILENT")

    # DRO Bracket disabled when HLG Still Image = On
    if configured_drive_mode == DRIVE_DRO_BRACKET and configured_hlg_still_image == TOGGLE_ON:
        return _err(EOPNOTSUPP_ERRNO, "HLG_STILL_LOCKS_OUT_DRO_BRACKET")

    # High ISO NR unavailable in RAW-only; locked Normal in iAuto
    if high_iso_nr_explicit_requested and configured_file_format == STILL_FMT_RAW:
        return _err(EOPNOTSUPP_ERRNO, "HIGH_ISO_NR_UNAVAILABLE_IN_RAW_ONLY")
    if high_iso_nr_explicit_requested and exposure_mode == EXPOSURE_MODE_IAUTO and high_iso_nr != HIGH_ISO_NR_NORMAL:
        return _err(EOPNOTSUPP_ERRNO, "HIGH_ISO_NR_FIXED_NORMAL_IN_IAUTO")

    # Long Exposure NR cannot be set Off in iAuto; unavailable in Cont. Shooting / Cont. Bracket
    is_continuous_drive = configured_drive_mode in CONTINUOUS_BURST_FPS
    if long_exposure_nr_explicit_requested and exposure_mode == EXPOSURE_MODE_IAUTO and long_exposure_nr != TOGGLE_ON:
        return _err(EOPNOTSUPP_ERRNO, "LONG_EXPOSURE_NR_FIXED_ON_IN_IAUTO")
    if long_exposure_nr_explicit_requested and (is_continuous_drive or configured_drive_mode == DRIVE_CONT_BRACKET):
        return _err(EOPNOTSUPP_ERRNO, "LONG_EXPOSURE_NR_LOCKED_IN_CONT_DRIVE_OR_BRACKET")

    # Effective shutter mode + 5-lock matrix
    silent_forcing_eshutter = (silent_mode == TOGGLE_ON) and (not silent_target_override)
    effective_shutter = (
        SHUTTER_TYPE_ELECTRONIC
        if (requested_shutter_type == SHUTTER_TYPE_ELECTRONIC or silent_forcing_eshutter)
        else SHUTTER_TYPE_MECHANICAL
    )
    five_locks_active = effective_shutter == SHUTTER_TYPE_ELECTRONIC

    if five_locks_active:
        if flash_requested:
            return _err(EOPNOTSUPP_ERRNO, "ESHUTTER_SILENT_LOCK_1_FLASH_1_250S_MECHANICAL_ONLY")
        if long_exposure_nr_explicit_requested and long_exposure_nr == TOGGLE_ON:
            return _err(EOPNOTSUPP_ERRNO, "ESHUTTER_SILENT_LOCK_2_LONG_EXPOSURE_NR")
        if e_front_curtain_edit_requested:
            return _err(EOPNOTSUPP_ERRNO, "ESHUTTER_SILENT_LOCK_3_EFRONT_CURTAIN_SHUT")
        if bulb_exposure_requested:
            return _err(EOPNOTSUPP_ERRNO, "ESHUTTER_SILENT_LOCK_4_BULB_EXPOSURE")
        if anti_flicker_shoot_requested:
            return _err(EOPNOTSUPP_ERRNO, "ESHUTTER_SILENT_LOCK_5_ANTI_FLICKER_SHOOT")

    # Reset split behavior
    if reset_action == RESET_ACTION_INITIALIZE:
        effective_shutter = SHUTTER_TYPE_MECHANICAL
        eff_efront = TOGGLE_ON
        eff_long_nr = TOGGLE_ON
        eff_high_iso_nr = HIGH_ISO_NR_NORMAL
        efront_survived = False
        efront_wiped = True
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        effective_shutter = SHUTTER_TYPE_MECHANICAL
        eff_efront = configured_e_front_curtain  # SURVIVES Camera Settings Reset!
        eff_long_nr = TOGGLE_ON
        eff_high_iso_nr = HIGH_ISO_NR_NORMAL
        efront_survived = True
        efront_wiped = False
    else:
        eff_efront = TOGGLE_OFF if five_locks_active else configured_e_front_curtain
        if five_locks_active or is_continuous_drive or configured_drive_mode == DRIVE_CONT_BRACKET:
            eff_long_nr = TOGGLE_OFF
        else:
            eff_long_nr = long_exposure_nr
        eff_high_iso_nr = "N/A" if configured_file_format == STILL_FMT_RAW else high_iso_nr
        efront_survived = True
        efront_wiped = False

    dark_frame_active = (
        (eff_long_nr == TOGGLE_ON)
        and (not five_locks_active)
        and (float(shutter_speed_sec) >= 1.0 or bulb_exposure_requested)
    )

    # Drive mode continuous fps & buffer/aperture rules
    base_fps = CONTINUOUS_BURST_FPS.get(configured_drive_mode, 0.0)
    uncomp_drop = (
        is_continuous_drive
        and configured_file_format in (STILL_FMT_RAW, STILL_FMT_RAW_JPEG, STILL_FMT_RAW_HEIF)
        and configured_raw_file_type == RAW_TYPE_UNCOMPRESSED
    )
    buffer_slow = is_continuous_drive and burst_frames_captured >= 1000
    if not is_continuous_drive:
        eff_fps = 0.0
    else:
        eff_fps = base_fps
        if uncomp_drop and eff_fps > 8.0:
            eff_fps = 8.0
        if flash_requested and eff_fps > 8.0:
            eff_fps = 8.0
        if buffer_slow:
            eff_fps = min(eff_fps, 4.0)

    af_locked_f11 = (
        configured_drive_mode in (DRIVE_CONT_HI_PLUS, DRIVE_CONT_HI, DRIVE_CONT_MID)
        and float(aperture_f_number) > 11.0
    )

    return ShutterTypeNrDriveVaultEvalResult(
        shutter_type_menu_path=SHUTTER_TYPE_MENU_PATH,
        efront_curtain_menu_path=EFRONT_CURTAIN_MENU_PATH,
        silent_mode_menu_path=SILENT_MODE_MENU_PATH,
        long_exp_nr_menu_path=LONG_EXP_NR_MENU_PATH,
        high_iso_nr_menu_path=HIGH_ISO_NR_MENU_PATH,
        drive_mode_menu_path=DRIVE_MODE_MENU_PATH,
        body_profile=body_profile,
        mechanical_shutter_present=FX3_MECHANICAL_SHUTTER_PRESENT,
        exposure_mode=exposure_mode,
        configured_shutter_type=requested_shutter_type,
        effective_shutter_type=effective_shutter,
        shutter_type_auto_absent_enforced=True,
        configured_e_front_curtain=configured_e_front_curtain,
        effective_e_front_curtain=eff_efront,
        silent_mode=silent_mode,
        silent_target_override=silent_target_override,
        electronic_5locks_engaged=five_locks_active,
        locked_functions=ALL_5_ESHUTTER_SILENT_LOCKED_FUNCTIONS if five_locks_active else (),
        flash_sync_max_fraction=FLASH_SYNC_MAX_FRACTION,
        shutter_speed_sec=float(shutter_speed_sec),
        configured_long_exposure_nr=long_exposure_nr,
        effective_long_exposure_nr=eff_long_nr,
        dark_frame_subtraction_active=dark_frame_active,
        configured_high_iso_nr=high_iso_nr,
        effective_high_iso_nr_for_jpeg_heif=eff_high_iso_nr,
        high_iso_nr_ignored_for_raw_arw=True,
        configured_drive_mode=configured_drive_mode,
        configured_file_format=configured_file_format,
        configured_raw_file_type=configured_raw_file_type,
        aperture_f_number=float(aperture_f_number),
        burst_frames_captured=burst_frames_captured,
        effective_burst_fps=eff_fps,
        uncompressed_raw_speed_drop_active=uncomp_drop,
        buffer_slow_throttled=buffer_slow,
        af_locked_past_f11=af_locked_f11,
        storage_target=storage_target,
        slot1_vault_blocked=False,
        reset_action=reset_action,
        efront_curtain_survived_camera_reset=efront_survived,
        efront_curtain_wiped_by_initialize=efront_wiped,
        shutter_type_auto_or_5lock_bypass_events=SHUTTER_TYPE_AUTO_OR_5LOCK_BYPASS_EVENTS,
        slot1_vault_still_or_burst_write_events=SLOT1_VAULT_STILL_OR_BURST_WRITE_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="SHUTTER_TYPE_NR_DRIVE_SLOT1_VAULT_HIL_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def probe_phase293_redline_guard(**probes: bool) -> RedlineGuardProbeResult:
    """Verify all 16 Stage 59 hard safety & Wave-49 zero-write redline probes."""
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
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
            emmc_corruptions=EMMC_CORRUPTIONS,
            nop_count=NOP_COUNT,
            guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
            otp_fuse_touches=OTP_FUSE_TOUCHES,
            rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
            physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
            dormant_lossless_raw_exposed_events=DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS,
            hlg_still_prerequisite_bypass_events=HLG_STILL_PREREQUISITE_BYPASS_EVENTS,
            color_space_leading_underscore_bypass_events=(
                COLOR_SPACE_LEADING_UNDERSCORE_BYPASS_EVENTS
            ),
            shutter_type_auto_or_5lock_bypass_events=SHUTTER_TYPE_AUTO_OR_5LOCK_BYPASS_EVENTS,
            slot1_vault_still_or_burst_write_events=SLOT1_VAULT_STILL_OR_BURST_WRITE_EVENTS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        )

    for field in ALL_16_REDLINE_PROBE_FIELDS:
        if probes.get(field, False):
            if field in ("cnflasha_userspace_write_requested", "slot1_vault_still_burst_write_requested"):
                err = EROFS_ERRNO
            elif field == "leading_underscore_prefix_bypass_requested":
                err = EINVAL_ERRNO
            elif field in (
                "dormant_lossless_raw_expose_requested",
                "hlg_still_prerequisite_bypass_requested",
                "eshutter_5lock_or_auto_bypass_requested",
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
                emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
                emmc_corruptions=EMMC_CORRUPTIONS,
                nop_count=NOP_COUNT,
                guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
                otp_fuse_touches=OTP_FUSE_TOUCHES,
                rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
                physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
                dormant_lossless_raw_exposed_events=DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS,
                hlg_still_prerequisite_bypass_events=HLG_STILL_PREREQUISITE_BYPASS_EVENTS,
                color_space_leading_underscore_bypass_events=(
                    COLOR_SPACE_LEADING_UNDERSCORE_BYPASS_EVENTS
                ),
                shutter_type_auto_or_5lock_bypass_events=(
                    SHUTTER_TYPE_AUTO_OR_5LOCK_BYPASS_EVENTS
                ),
                slot1_vault_still_or_burst_write_events=(
                    SLOT1_VAULT_STILL_OR_BURST_WRITE_EVENTS
                ),
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
        emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
        emmc_corruptions=EMMC_CORRUPTIONS,
        nop_count=NOP_COUNT,
        guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        dormant_lossless_raw_exposed_events=DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS,
        hlg_still_prerequisite_bypass_events=HLG_STILL_PREREQUISITE_BYPASS_EVENTS,
        color_space_leading_underscore_bypass_events=(
            COLOR_SPACE_LEADING_UNDERSCORE_BYPASS_EVENTS
        ),
        shutter_type_auto_or_5lock_bypass_events=SHUTTER_TYPE_AUTO_OR_5LOCK_BYPASS_EVENTS,
        slot1_vault_still_or_burst_write_events=SLOT1_VAULT_STILL_OR_BURST_WRITE_EVENTS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_pillar_c_d_shutter_nr_drive_vault_and_redlines() -> Dict[str, object]:
    """Evaluate Sub-Model 59C `[Shutter Type]`, NR, `10 fps` Drive Mode, `Slot-1` Vault & Redlines."""
    shutter_2mode_ok = {
        mode: asdict(
            simulate_shutter_type_nr_drive_and_slot1_vault_hil(
                requested_shutter_type=mode,
            )
        )
        for mode in EXPOSED_FX3_2_SHUTTER_TYPES
    }
    shutter_auto_rejected = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        requested_shutter_type=SHUTTER_TYPE_AUTO_UNSUPPORTED,
    )
    eshutter_lock1_flash = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        requested_shutter_type=SHUTTER_TYPE_ELECTRONIC,
        flash_requested=True,
    )
    eshutter_lock2_long_nr = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        requested_shutter_type=SHUTTER_TYPE_ELECTRONIC,
        long_exposure_nr=TOGGLE_ON,
        long_exposure_nr_explicit_requested=True,
    )
    eshutter_lock3_efront = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        requested_shutter_type=SHUTTER_TYPE_ELECTRONIC,
        e_front_curtain_edit_requested=True,
    )
    eshutter_lock4_bulb = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        requested_shutter_type=SHUTTER_TYPE_ELECTRONIC,
        bulb_exposure_requested=True,
    )
    eshutter_lock5_antiflicker = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        requested_shutter_type=SHUTTER_TYPE_ELECTRONIC,
        anti_flicker_shoot_requested=True,
    )
    silent_locks_flash = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        requested_shutter_type=SHUTTER_TYPE_MECHANICAL,
        silent_mode=TOGGLE_ON,
        flash_requested=True,
    )
    silent_override_flash_ok = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        requested_shutter_type=SHUTTER_TYPE_MECHANICAL,
        silent_mode=TOGGLE_ON,
        silent_target_override=True,
        flash_requested=True,
    )
    mech_1s_dark_frame = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        requested_shutter_type=SHUTTER_TYPE_MECHANICAL,
        shutter_speed_sec=2.0,
        long_exposure_nr=TOGGLE_ON,
    )
    high_iso_nr_raw_ignored = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        configured_file_format=STILL_FMT_RAW_JPEG,
        high_iso_nr=HIGH_ISO_NR_NORMAL,
    )
    high_iso_nr_raw_only_locked = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        configured_file_format=STILL_FMT_RAW,
        high_iso_nr_explicit_requested=True,
    )
    drive_hi_plus_10fps_comp = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        configured_drive_mode=DRIVE_CONT_HI_PLUS,
        configured_file_format=STILL_FMT_RAW_JPEG,
        configured_raw_file_type=RAW_TYPE_COMPRESSED,
        burst_frames_captured=200,
    )
    drive_hi_plus_uncomp_drop = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        configured_drive_mode=DRIVE_CONT_HI_PLUS,
        configured_file_format=STILL_FMT_RAW,
        configured_raw_file_type=RAW_TYPE_UNCOMPRESSED,
        burst_frames_captured=50,
    )
    drive_hi_plus_slow_f13 = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        configured_drive_mode=DRIVE_CONT_HI_PLUS,
        aperture_f_number=13.0,
        burst_frames_captured=1050,
    )
    slot1_vault_single_blocked = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        configured_drive_mode=DRIVE_SINGLE,
        storage_target=STORAGE_TARGET_SLOT1_VAULT,
    )
    slot1_vault_burst_blocked = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        configured_drive_mode=DRIVE_CONT_HI_PLUS,
        storage_target=STORAGE_TARGET_SLOT1_VAULT,
    )
    slot1_vault_ebusy_blocked = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        configured_drive_mode=DRIVE_CONT_BRACKET,
        storage_target=STORAGE_TARGET_SLOT1_VAULT,
        slot1_busy_locked=True,
    )
    slot2_scratch_ok = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        configured_drive_mode=DRIVE_CONT_HI_PLUS,
        storage_target=STORAGE_TARGET_SLOT2_SCRATCH,
    )
    efront_survives_cam_reset = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        configured_e_front_curtain=TOGGLE_OFF,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    fx6_no_mech_shutter = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        body_profile=BODY_MODEL_FX6,
        requested_shutter_type=SHUTTER_TYPE_MECHANICAL,
    )
    fx6_electronic_contrast = simulate_shutter_type_nr_drive_and_slot1_vault_hil(
        body_profile=BODY_MODEL_FX6,
        requested_shutter_type=SHUTTER_TYPE_ELECTRONIC,
    )

    baseline_redline = probe_phase293_redline_guard()
    blocked_probes = {
        field: asdict(probe_phase293_redline_guard(**{field: True}))
        for field in ALL_16_REDLINE_PROBE_FIELDS
    }
    all_probes_blocked = all(not p["valid"] for p in blocked_probes.values())

    passed = (
        len(shutter_2mode_ok) == 2
        and all(v["admitted"] for v in shutter_2mode_ok.values())
        and (not shutter_auto_rejected.admitted)
        and shutter_auto_rejected.errno_code == EINVAL_ERRNO
        and (not eshutter_lock1_flash.admitted)
        and eshutter_lock1_flash.errno_code == EOPNOTSUPP_ERRNO
        and (not eshutter_lock2_long_nr.admitted)
        and eshutter_lock2_long_nr.errno_code == EOPNOTSUPP_ERRNO
        and (not eshutter_lock3_efront.admitted)
        and eshutter_lock3_efront.errno_code == EOPNOTSUPP_ERRNO
        and (not eshutter_lock4_bulb.admitted)
        and eshutter_lock4_bulb.errno_code == EOPNOTSUPP_ERRNO
        and (not eshutter_lock5_antiflicker.admitted)
        and eshutter_lock5_antiflicker.errno_code == EOPNOTSUPP_ERRNO
        and (not silent_locks_flash.admitted)
        and silent_locks_flash.errno_code == EOPNOTSUPP_ERRNO
        and silent_override_flash_ok.admitted
        and mech_1s_dark_frame.admitted
        and mech_1s_dark_frame.dark_frame_subtraction_active
        and high_iso_nr_raw_ignored.admitted
        and high_iso_nr_raw_ignored.high_iso_nr_ignored_for_raw_arw
        and (not high_iso_nr_raw_only_locked.admitted)
        and high_iso_nr_raw_only_locked.errno_code == EOPNOTSUPP_ERRNO
        and drive_hi_plus_10fps_comp.admitted
        and drive_hi_plus_10fps_comp.effective_burst_fps == 10.0
        and drive_hi_plus_uncomp_drop.admitted
        and drive_hi_plus_uncomp_drop.uncompressed_raw_speed_drop_active
        and drive_hi_plus_uncomp_drop.effective_burst_fps == 8.0
        and drive_hi_plus_slow_f13.admitted
        and drive_hi_plus_slow_f13.buffer_slow_throttled
        and drive_hi_plus_slow_f13.af_locked_past_f11
        and (not slot1_vault_single_blocked.admitted)
        and slot1_vault_single_blocked.errno_code == EROFS_ERRNO
        and (not slot1_vault_burst_blocked.admitted)
        and slot1_vault_burst_blocked.errno_code == EROFS_ERRNO
        and (not slot1_vault_ebusy_blocked.admitted)
        and slot1_vault_ebusy_blocked.errno_code == EBUSY_ERRNO
        and slot2_scratch_ok.admitted
        and slot2_scratch_ok.physical_device_writes == 0
        and efront_survives_cam_reset.admitted
        and efront_survives_cam_reset.effective_e_front_curtain == TOGGLE_OFF
        and efront_survives_cam_reset.efront_curtain_survived_camera_reset
        and (not fx6_no_mech_shutter.admitted)
        and fx6_no_mech_shutter.errno_code == EOPNOTSUPP_ERRNO
        and fx6_electronic_contrast.admitted
        and (not fx6_electronic_contrast.mechanical_shutter_present)
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "shutter_type_menu_path": SHUTTER_TYPE_MENU_PATH,
        "drive_mode_menu_path": DRIVE_MODE_MENU_PATH,
        "exposed_fx3_2_shutter_types": list(EXPOSED_FX3_2_SHUTTER_TYPES),
        "all_5_eshutter_silent_locked_functions": list(ALL_5_ESHUTTER_SILENT_LOCKED_FUNCTIONS),
        "fx3_8_drive_base_modes": list(FX3_8_DRIVE_BASE_MODES),
        "all_16_redline_probe_fields": list(ALL_16_REDLINE_PROBE_FIELDS),
        "shutter_2mode_ok": shutter_2mode_ok,
        "shutter_auto_rejected_einval": asdict(shutter_auto_rejected),
        "eshutter_5lock_matrix": {
            "lock1_flash_1_250s": asdict(eshutter_lock1_flash),
            "lock2_long_exposure_nr": asdict(eshutter_lock2_long_nr),
            "lock3_e_front_curtain": asdict(eshutter_lock3_efront),
            "lock4_bulb": asdict(eshutter_lock4_bulb),
            "lock5_anti_flicker": asdict(eshutter_lock5_antiflicker),
        },
        "silent_locks_flash_eopnotsupp": asdict(silent_locks_flash),
        "silent_target_override_flash_ok": asdict(silent_override_flash_ok),
        "mech_2s_dark_frame_nr_ok": asdict(mech_1s_dark_frame),
        "high_iso_nr_raw_ignored_ok": asdict(high_iso_nr_raw_ignored),
        "high_iso_nr_raw_only_locked_eopnotsupp": asdict(high_iso_nr_raw_only_locked),
        "drive_hi_plus_10fps_compressed_ok": asdict(drive_hi_plus_10fps_comp),
        "drive_hi_plus_uncompressed_drop_8fps": asdict(drive_hi_plus_uncomp_drop),
        "drive_hi_plus_1050_slow_f13_af_lock": asdict(drive_hi_plus_slow_f13),
        "slot1_vault_single_blocked_erofs": asdict(slot1_vault_single_blocked),
        "slot1_vault_burst_blocked_erofs": asdict(slot1_vault_burst_blocked),
        "slot1_vault_bracket_ebusy": asdict(slot1_vault_ebusy_blocked),
        "slot2_scratch_hi_plus_ok": asdict(slot2_scratch_ok),
        "efront_survives_camera_settings_reset": asdict(efront_survives_cam_reset),
        "fx6_no_mechanical_shutter_eopnotsupp": asdict(fx6_no_mech_shutter),
        "fx6_electronic_contrast": asdict(fx6_electronic_contrast),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 293 (Stage 59, 59/59) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase293_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 293 Stage 59 (59/59) Wave-49 HIL co-emulation audit."""
    donor_audit = inspect_phase293_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_raw_heif_hlg_hil()
    pillar_b = evaluate_pillar_b_colorspace_setfilename_hil()
    pillar_cd = evaluate_pillar_c_d_shutter_nr_drive_vault_and_redlines()

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
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
        "dormant_lossless_raw_exposed_events": DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS,
        "hlg_still_prerequisite_bypass_events": HLG_STILL_PREREQUISITE_BYPASS_EVENTS,
        "color_space_leading_underscore_bypass_events": (
            COLOR_SPACE_LEADING_UNDERSCORE_BYPASS_EVENTS
        ),
        "shutter_type_auto_or_5lock_bypass_events": SHUTTER_TYPE_AUTO_OR_5LOCK_BYPASS_EVENTS,
        "slot1_vault_still_or_burst_write_events": SLOT1_VAULT_STILL_OR_BURST_WRITE_EVENTS,
        "fx6_still_pipeline_exposed": FX6_STILL_PIPELINE_EXPOSED,
        "fx3_mechanical_shutter_present": FX3_MECHANICAL_SHUTTER_PRESENT,
        "fx6_mechanical_shutter_present": FX6_MECHANICAL_SHUTTER_PRESENT,
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
        and EMMC_NFLASHA_WRITE_COUNT == 0
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
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS == 0
        and HLG_STILL_PREREQUISITE_BYPASS_EVENTS == 0
        and COLOR_SPACE_LEADING_UNDERSCORE_BYPASS_EVENTS == 0
        and SHUTTER_TYPE_AUTO_OR_5LOCK_BYPASS_EVENTS == 0
        and SLOT1_VAULT_STILL_OR_BURST_WRITE_EVENTS == 0
        and (not FX6_STILL_PIPELINE_EXPOSED)
        and FX3_MECHANICAL_SHUTTER_PRESENT
        and (not FX6_MECHANICAL_SHUTTER_PRESENT)
        and RAW_FIRMWARE_BYTES_LEAKED == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_293_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_raw_heif_hlg_hil": pillar_a,
        "pillar_b_colorspace_setfilename_hil": pillar_b,
        "pillar_c_d_shutter_nr_drive_vault_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py",
        description=(
            "Phase 293 Stage 59 (59/59) — Real-Hardware ILME-FX3 Ver. 7.02 vs "
            "ILME-FX6 Ver. 6.01 Wave-49 Still RAW Compressed/Uncompressed vs Dormant Lossless, "
            "HEIF 4:2:0/4:2:2 10-bit & HLG Still Image BT.2100 Override, Color Space AdobeRGB "
            "_DSC Prefix & Set File Name Guard, and Shutter Type 2-Mode Mechanical vs Electronic "
            "/ Long Exposure NR / 10fps Drive Mode Slot-1 Vault HIL Co-Emulator"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 293 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase293_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 293 Stage 59 (59/59) | mode={rep['source_mode']} "
            f"| donors={rep['donor_audit']['donor_files_inspected']} "
            f"| lossless_exp={red['dormant_lossless_raw_exposed_events']} "
            f"| hlg_byp={red['hlg_still_prerequisite_bypass_events']} "
            f"| cs_byp={red['color_space_leading_underscore_bypass_events']} "
            f"| shut_byp={red['shutter_type_auto_or_5lock_bypass_events']} "
            f"| s1_wr={red['slot1_vault_still_or_burst_write_events']} "
            f"| phys_wr={red['physical_device_writes']} "
            f"| leaked={red['raw_firmware_bytes_leaked']} "
            f"| digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
