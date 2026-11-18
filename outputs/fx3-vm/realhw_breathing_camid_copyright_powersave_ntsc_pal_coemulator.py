#!/usr/bin/env python3
"""Phase 339 (Stage 74 — 74/74 VM HIL Stages Milestone!):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-64 HIL Co-Emulator.

Models and audits the four Wave-64 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / `CLEAN_ROOM_SYNTHETIC` CI fallback and
`raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 74A (`[Breathing Comp.]` Optical Crop, `120p/100p` & RAW & S&Q
   Lockouts, Lens Allowlist & `Catalyst Prepare`-Only Errata Fix)**:
   - `Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`
     (`Ver. 3.00+..7.02`, `Off` default / `On`) IS **Resettable** via
     `[Camera Settings Reset]`, strictly contrasting its 3 sibling items in
     `[Lens Compensation]` (`Shading Comp.`, `Chromatic Aberration Comp.`,
     `Distortion Comp.` which are all `Not available` for Reset).
   - Fixes Wave-41 errata & Catalyst myths: disabled in Still, Movie
     `119.88p/100p` (not merely 200/240fps!), `S&Q >= 100/120fps` (active in
     `S&Q < 100/120fps` on FX3 vs disabled across ALL `S&Q` on FX6!), HDMI
     `4264x2408` 16-bit `RAW Output`, incompatible/third-party/TC lenses
     (`SEL14TC`/`SEL20TC`, `SEL100F28GM` macro `0.57m-1.0m`), CIZ/Digital Zoom
     and `Auto Framing` coupling. Post metadata breathing compensation works
     ONLY in paid `Catalyst Prepare` / `Catalyst Prepare Plugin` with in-body
     `[Distortion Comp.] = Auto` (free `Catalyst Browse` is unsupported).
   - Contrasts `ILME-FX6 Ver. 6.01` `Technical > Lens > Breathing Compensation`
     (`Auto` / `Off`), locked `Off` on `Distortion Comp. = Off`, `S&Q = On`
     (all frame rates), or any `RAW` codec.

2. **Sub-Model 74B (Movie `[File Settings]` `Cam ID + Reel#`, `37`-Char Title,
   `SDHC` `4 GB` Split & Tier-0 `Slot 1` `EROFS=30` Firewall)**:
   - `Shooting -> [File] -> [File Settings]` (ALL sub-items Reset-immune; only
     `[Initialize]` resets; fixed `PRIVATE/M4ROOT/CLIP/*.MP4`):
     `[File Number]` (`Series` def / `Reset` + `[Series Counter Reset]` `max+1`),
     `[File Name Format]` (`Standard`, `Cam ID + Reel#` `YYMMDD` + `C999->D001`
     output filename rollover without mutating menu `Camera Position`, `Camera
     ID` change resetting `Reel#` whereas `File Number=Reset` preserves `Reel#`,
     `Title` `37`-char max def `"C"`, `Date+Title`/`Title+Date` `YYYYMMDD`).
   - `SDHC` (`FAT32 <= 32 GB`) forces `[File Name Format] = Standard`, splits
     long XAVC S recordings at `4 GB`, and forbids `[Simult. Recording]` mixed
     with `exFAT` (`SDXC` / `CFexpress Type A`).
   - `Slot 1` Tier-0 `EROFS=30` firewall blocks card metadata/clip/counter
     mutations (`BKID_APP_update_required_xavcs_file_name_reel_number`), vs
     `ILME-FX6` `TC/Media > Clip Name Format` (`4..46` char `nnn_` prefix,
     `/XDROOT/Clip/*.MXF` or `/PRIVATE/XDROOT/Clip/*.MXF`, hardware card
     inheritance `BKID_APP_CAMID_CURRENT_*` / `DIADEM_PRO`).

3. **Sub-Model 74C (`[Copyright Info]` `46`-Char, `[Write Serial Number]` Still
   + Movie Active, Round-57 Reset-Immunity Errata Fix & `CAMSET` Exclusion)**:
   - `[Copyright Info]` (`46`-char ASCII `Set Photographer` / `Set Copyright`,
     `Write Copyright Info` `Off` def, `Disp. Copyright Info`, Still EXIF only)
     and `[Write Serial Number]` (`BKID_APP_setting_write_serial_number_still_movie`
     active across **Still + Movie**, replacing Still-only `...still_write_serial_number`).
   - **Round-57 Errata Fix**: ALL 5 items (`Write Copyright Info`, `Set
     Photographer`, `Set Copyright`, `Disp. Copyright Info`, `[Write Serial
     Number]`) are **`Resettable: Not available`** (survive `[Camera Settings
     Reset]`; cleared ONLY by `[Initialize]`).
   - `Copyright Info` is strictly excluded from `CAMSET*.DAT` (zero PII spread),
     whereas the `[Write Serial Number]` boolean toggle is NOT excluded (and
     never contains the hardware serial string). Zero PII/serial leaked, `Slot 1`
     protected by `EROFS=30`, vs `ILME-FX6` lens serial tracking
     (`CURRENT/PRESET_LENS_SERIAL_NUMBER0..5`) + `Title Prefix` `nnn_`.

4. **Sub-Model 74D (`[Power Setting Option]` 9-Condition `[Power Save Start Time]`
   / `[Auto Power OFF Temp.]` / 100%% Dormant `[Power Save by Monitor]` &
   `[NTSC/PAL Selector]` `Slot 1` `EROFS=30` Format-Trap Firewall)**:
   - `Setup -> [Power Setting Option]` (all Reset-immune): `[Power Save Start
     Time]` exposes 6 active steps (`Off`, `30 Min`, `5 Min` [def], `2 Min`,
     `1 Min`, `10 Sec`; dormant `20 Sec`/`30 Sec`/`60 Min`/`240 Min`/`No Limit`
     rejected with `EOPNOTSUPP=95`) governed by **9 official auto-bypass
     conditions**; `[Auto Power OFF Temp.]` (`Standard` [def] / `High`
     tripod-only warning); **100%% dormant `[Power Save by Monitor]`**
     (`BKID_APP_setting_monitor_power_linkage`, `EOPNOTSUPP=95`, FX3 has no EVF).
   - `Setup -> [Area/Date] -> [NTSC/PAL Selector]` (Reset-immune): switches
     trigger forced auto-reboot, non-factory boot shows `Running on NTSC.` or
     `Running on PAL.`, `PAL` disables `23.98p` and locks `[Time Code Format]`
     to `NDF`, and dual-generation UXC format prompt traps (`base` SD-Erase/TRIM
     vs `_g` cross-system playback block) are firewalled at Tier-0 `Slot 1` with
     `EROFS=30` (`slot1_data_sector_writes == 0`). Contrasts `ILME-FX6`
     `Project > Rec Format > Frequency`.
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
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Phase 339 Schema, Milestone & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = "phase339_realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulation_v1"
PHASE_339_VERSION = "339.0.0"
PHASE_NUMBER = 339
STAGE_INDEX = 74
STAGE_TOTAL = 74
MILESTONE_LABEL = "74/74"
IS_74TH_STAGE_MILESTONE = True

# Hardware Safety & Redline Constants (Tier-0 NO-GO / EROFS=30 / Zero-Leak)
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
EMMC_WRITES_AUTHORIZED = False
CROSS_MODEL_FLASH_AUTHORIZED = False
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
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
RF_PACKETS_TRANSMITTED = 0
RF_NVS_MUTATION_BYTES = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Wave-64 Numeric & Invariant Contracts
BREATHING_COMP_HFR_THRESHOLD_FPS = 100.0
BREATHING_COMP_120P_RAW_SQ_BYPASS_EVENTS = 0
CATALYST_BROWSE_BREATHING_SUPPORTED = False
BREATHING_COMP_RESET_IMMUNITY_DRIFT_EVENTS = 0
FX6_ALL_SQ_BREATHING_LEAK_EVENTS = 0

MOVIE_FILE_TITLE_MAX_CHARS = 37
SDHC_FORCED_SPLIT_GB = 4
SDHC_NONSTANDARD_FORMAT_BYPASS_EVENTS = 0
SDHC_EXFAT_SIMULT_BYPASS_EVENTS = 0
CAMID_POS_ROLLOVER_MENU_MUTATION_EVENTS = 0
SLOT1_FILE_SETTINGS_EROFS_BYPASS_EVENTS = 0
FX6_CLIP_TITLE_PREFIX_MIN_CHARS = 4
FX6_CLIP_TITLE_PREFIX_MAX_CHARS = 46

COPYRIGHT_MAX_CHARS = 46
COPYRIGHT_RESET_WIPE_ERRATA_EVENTS = 0
WRITE_SERIAL_NUMBER_RESET_WIPE_EVENTS = 0
CAMSET_COPYRIGHT_PII_LEAK_EVENTS = 0
PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES = 0
BODY_SERIAL_NUMBER_LEAKED_BYTES = 0

POWER_SAVE_ACTIVE_STEPS_COUNT = 6
POWER_SAVE_BYPASS_CONDITIONS_COUNT = 9
DORMANT_POWER_SAVE_BY_MONITOR_EXPOSED_EVENTS = 0
DORMANT_POWER_SAVE_STEPS_EXPOSED_EVENTS = 0
NTSC_PAL_SLOT1_FORMAT_EROFS_BYPASS_EVENTS = 0
PAL_2398P_OR_DF_BYPASS_EVENTS = 0

# Errno Constants
EPERM_ERRNO = 1
EBUSY_ERRNO = 16
EINVAL_ERRNO = 22
EROFS_ERRNO = 30
EOPNOTSUPP_ERRNO = 95

DONOR_ACCESS_MODE = "O_RDONLY"
BOUNDED_WINDOW_MAX_BYTES = 4096
SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "MAIN_LAB_WORK_ROOT"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"


# ---------------------------------------------------------------------------
# Verified Local Donor Specs (18 FX3 Ver. 7.02 & FX6 Ver. 6.01 Wave-64 Donors)
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
    "fx3_string_sc": f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
    "fx3_string_tc": f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
    "fx3_string_ja": f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
    "fx3_string_en_g": f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
    "fx3_string_sc_g": f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
    "fx3_string_tc_g": f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_g.uxc",
    "fx3_string_ja_g": f"{_FX3_USR_PREFIX}/share/app/string_japanese_g.uxc",
    "fx3_saveload": f"{_FX3_USR_PREFIX}/lib/libSaveLoadSettings.so",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_en_2": f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx3_bk4": (
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/"
        "FX3-CX95900_ALLLANG-Backup.bin"
    ),
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_string_en_f": 373_820,
    "fx3_string_sc_f": 322_652,
    "fx3_string_tc_f": 324_148,
    "fx3_string_ja_f": 447_840,
    "fx3_string_en": 165_740,
    "fx3_string_sc": 149_064,
    "fx3_string_tc": 151_908,
    "fx3_string_ja": 208_564,
    "fx3_string_en_g": 69_600,
    "fx3_string_sc_g": 61_296,
    "fx3_string_tc_g": 61_372,
    "fx3_string_ja_g": 89_428,
    "fx3_saveload": 18_760,
    "fx6_string_en": 118_208,
    "fx6_string_en_2": 118_676,
    "fx3_appfw": 79_015_712,
    "fx3_bk4": 2_229_740,
    "fx6_appfw": 50_520_424,
}

EXPECTED_COMPACT_DONOR_SHA256: Mapping[str, str] = {
    "fx3_string_en_f": "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
    "fx3_string_sc_f": "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
    "fx3_string_tc_f": "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
    "fx3_string_ja_f": "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
    "fx3_string_en": "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
    "fx3_string_sc": "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
    "fx3_string_tc": "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
    "fx3_string_ja": "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
    "fx3_string_en_g": "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
    "fx3_string_sc_g": "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
    "fx3_string_tc_g": "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80",
    "fx3_string_ja_g": "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980",
    "fx3_saveload": "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
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
        b"Breathing Comp.",
        b"Distortion Comp.",
        b"File Settings",
        b"Cam ID + Reel#",
        b"Series Counter Reset",
        b"Copyright Info",
        b"Write Serial Number",
        b"Power Save Start Time",
        b"Auto Power OFF Temp.",
        b"Power Save by Monitor",
        b"NTSC/PAL Selector",
    ),
    "fx3_string_sc_f": (
        b"Cam ID + Reel#",
        "呼吸补偿".encode("utf-8"),
        "版权信息".encode("utf-8"),
        "写入序列号".encode("utf-8"),
        "NTSC/PAL选择器".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        b"Cam ID + Reel#",
        "呼吸補償".encode("utf-8"),
        "版權資訊".encode("utf-8"),
        "寫入序號".encode("utf-8"),
        "NTSC/PAL選擇器".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        b"Cam ID + Reel#",
        "ブリージング補正".encode("utf-8"),
        "著作権情報".encode("utf-8"),
        "NTSC/PAL切換".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Auto Power OFF Temp.",
        b"Running on NTSC.",
        b"Running on PAL.",
        b"File Number",
        b"Series",
    ),
    "fx3_string_sc": ("运行于NTSC".encode("utf-8"), b"NTSC"),
    "fx3_string_tc": ("在NTSC上執行".encode("utf-8"), b"NTSC"),
    "fx3_string_ja": ("NTSCで動作中".encode("utf-8"), b"NTSC"),
    "fx3_string_en_g": (
        b"Auto Power OFF Temp.",
        b"Title",
        b"NTSC",
        b"PAL",
    ),
    "fx3_string_sc_g": ("标题".encode("utf-8"), b"NTSC/PAL"),
    "fx3_string_tc_g": ("標題".encode("utf-8"), b"NTSC/PAL"),
    "fx3_string_ja_g": ("タイトル".encode("utf-8"), b"NTSC/PAL"),
    "fx3_saveload": (b"libSaveLoadSettings", b"Save", b"Load"),
    "fx6_string_en": (
        b"Breathing Compensation",
        b"Clip Name Format",
        b"Camera ID",
        b"Reel Number",
        b"Title Prefix",
        b"Frequency",
    ),
    "fx6_string_en_2": (
        b"Camera ID",
        b"Reel Number",
        b"Title Prefix",
        b"Frequency",
        b"NTSC",
        b"PAL",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0x394A000, "PID_SET_BREATHING_CORRECTION", b"PID_SET_BREATHING_CORRECTION"),
        (
            0x39BA000,
            "PRM_HAITA_setting_lens_comp_breathing_exposure_mode",
            b"PRM_HAITA_setting_lens_comp_breathing_exposure_mode",
        ),
        (
            0x3BC6000,
            "BKID_APP_setting_lens_comp_breathing",
            b"BKID_APP_setting_lens_comp_breathing",
        ),
        (
            0x3BC6000,
            "BKID_APP_setting_lens_comp_distortion",
            b"BKID_APP_setting_lens_comp_distortion",
        ),
        (
            0x3BC6000,
            "BKID_APP_setting_xavc_s_file_name_camid_camera_id",
            b"BKID_APP_setting_xavc_s_file_name_camid_camera_id",
        ),
        (
            0x3BF2000,
            "BKID_APP_update_required_xavcs_file_name_reel_number",
            b"BKID_APP_update_required_xavcs_file_name_reel_number",
        ),
        (
            0x3BC6000,
            "BKID_APP_setting_write_serial_number_still_movie",
            b"BKID_APP_setting_write_serial_number_still_movie",
        ),
        (
            0x3BC6000,
            "BKID_APP_setting_still_write_serial_number",
            b"BKID_APP_setting_still_write_serial_number",
        ),
        (
            0x3BC6000,
            "BKID_APP_setting_still_write_copyright_infomation",
            b"BKID_APP_setting_still_write_copyright_infomation",
        ),
        (
            0x3BCB000,
            "BKID_APP_setting_start_power_saving",
            b"BKID_APP_setting_start_power_saving",
        ),
        (
            0x3BCB000,
            "BKID_APP_setting_auto_pwr_off_temp",
            b"BKID_APP_setting_auto_pwr_off_temp",
        ),
        (
            0x3BCB000,
            "BKID_APP_setting_monitor_power_linkage",
            b"BKID_APP_setting_monitor_power_linkage",
        ),
        (
            0x3BCE000,
            "BKID_APP_setting_ntsc_pal_selector",
            b"BKID_APP_setting_ntsc_pal_selector",
        ),
    ),
    "fx3_bk4": (
        (0x00000, "BK4_HEADER", b"BK4\x00"),
        (0x4A000, "ILME-FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (
            0x2706000,
            "BKID_APP_SETTING_LENS_COMP_BREATHING",
            b"BKID_APP_SETTING_LENS_COMP_BREATHING",
        ),
        (
            0x271E000,
            "BKID_APP_CAMID_CURRENT_CAMERA_ID0",
            b"BKID_APP_CAMID_CURRENT_CAMERA_ID0",
        ),
        (
            0x271E000,
            "BKID_APP_CAMID_CURRENT_REEL_NUMBER0",
            b"BKID_APP_CAMID_CURRENT_REEL_NUMBER0",
        ),
        (
            0x271D000,
            "BKID_APP_CURRENT_LENS_SERIAL_NUMBER",
            b"BKID_APP_CURRENT_LENS_SERIAL_NUMBER",
        ),
        (
            0x271E000,
            "BKID_APP_PRESET_LENS_SERIAL_NUMBER0",
            b"BKID_APP_PRESET_LENS_SERIAL_NUMBER0",
        ),
        (
            0x2709000,
            "BKID_APP_SETTING_FREQUENCY_REC_FORMAT",
            b"BKID_APP_SETTING_FREQUENCY_REC_FORMAT",
        ),
        (0x273C000, "DIADEM_PRO", b"DIADEM_PRO"),
    ),
}


# ---------------------------------------------------------------------------
# Wave-64 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

FW_VER_200 = "2.00"
FW_VER_300 = "3.00"
FW_VER_601 = "6.01"
FW_VER_702 = "7.02"
VALID_FW_VERSIONS: Tuple[str, ...] = (FW_VER_200, FW_VER_300, FW_VER_601, FW_VER_702)

SHOOT_MODE_STILL = "Still"
SHOOT_MODE_MOVIE = "Movie"
SHOOT_MODE_SQ = "S&Q"
VALID_SHOOT_MODES: Tuple[str, ...] = (SHOOT_MODE_STILL, SHOOT_MODE_MOVIE, SHOOT_MODE_SQ)

# Sub-Model 74A — Breathing Comp. & Catalyst Prepare-Only
COMPATIBLE_BREATHING_LENSES: Tuple[str, ...] = (
    "SEL11F18",
    "SEL14F18GM",
    "SEL15F14G",
    "SEL16F18G",
    "SEL20F18G",
    "SEL24F14GM",
    "SEL24F28G",
    "SEL35F14GM",
    "SEL35F18F",
    "SEL40F25G",
    "SEL50F12GM",
    "SEL50F14GM",
    "SEL50F14Z",
    "SEL50F25G",
    "SEL85F14GM",
    "SEL85F14GM2",
    "SEL85F18",
    "SEL100F28GM",
    "SEL135F18GM",
    "SEL1224G",
    "SEL1635GM",
    "SELC1635G",
    "SEL2470GM",
    "SEL2470GM2",
    "SEL24105G",
    "SEL70200GM2",
)
VALID_DISTORTION_COMP_MODES: Tuple[str, ...] = ("Auto", "Off")
VALID_CATALYST_CLIENTS: Tuple[str, ...] = (
    "None",
    "Catalyst Browse",
    "Catalyst Prepare",
    "Catalyst Prepare Plugin",
)
FX6_BREATHING_MODES: Tuple[str, ...] = ("Auto", "Off")
FX6_REC_CODECS: Tuple[str, ...] = (
    "XAVC-I",
    "XAVC-L",
    "RAW",
    "RAW & XAVC-I",
    "RAW(HDMI)",
    "RAW(HDMI) & XAVC-I",
)

# Sub-Model 74B — Movie [File Settings], SDHC 4 GB & Slot 1 EROFS=30
VALID_FILE_NUMBER_MODES: Tuple[str, ...] = ("Series", "Reset")
VALID_FILE_NAME_FORMATS: Tuple[str, ...] = (
    "Standard",
    "Cam ID + Reel#",
    "Title",
    "Date + Title",
    "Title + Date",
)
VALID_CAM_POSITIONS: Tuple[str, ...] = ("C", "L", "R")
VALID_MEDIA_CARD_TYPES: Tuple[str, ...] = ("CFexpress Type A", "SDXC", "SDHC")
VALID_RECORDING_SLOTS: Tuple[str, ...] = ("Slot 1", "Slot 2", "Simult. Recording")
_TITLE_ALLOWED_RE = re.compile(r"^[A-Za-z0-9._@!#$%+=^~(),;\[\]\-]+$")

# Sub-Model 74C — [Copyright Info] (46-char), [Write Serial Number] & CAMSET
CAMSET_EXCLUDED_GROUPS: Tuple[str, ...] = (
    "IPTC Information",
    "Copyright Info",
    "External Flash Set.",
    "White Balance: Custom 1",
    "White Balance: Custom 2",
    "White Balance: Custom 3",
    "Face Memory",
    "FTP Transfer Func.",
    "Network Streaming",
    "Cloud Connection",
    "WPS Push",
    "Access Point Set.",
    "Wi-Fi Frequency Band",
    "IP Address Setting",
    "Edit Device Name",
    "Import Root Certificate",
    "Access Authen.",
)

# Sub-Model 74D — Power Setting Option & NTSC/PAL Selector
FX3_POWER_SAVE_ACTIVE_STEPS: Tuple[str, ...] = (
    "Off",
    "30 Min",
    "5 Min",
    "2 Min",
    "1 Min",
    "10 Sec",
)
DORMANT_POWER_SAVE_STEPS: Tuple[str, ...] = (
    "20 Sec",
    "30 Sec",
    "60 Min",
    "240 Min",
    "No Limit",
)
ALL_POWER_SAVE_PROBES: Tuple[str, ...] = (
    FX3_POWER_SAVE_ACTIVE_STEPS + DORMANT_POWER_SAVE_STEPS
)
POWER_SAVE_9_BYPASS_CONDITIONS: Tuple[str, ...] = (
    "usb_power_supplied",
    "slideshow_playing",
    "ftp_transfer_active",
    "recording_movies",
    "connected_to_pc",
    "connected_to_tv_hdmi",
    "ir_remote_ctrl_on",
    "bluetooth_rmt_ctrl_on",
    "streaming_or_creators_cloud_upload",
)
VALID_AUTO_PWR_OFF_TEMP_MODES: Tuple[str, ...] = ("Standard", "High")
VALID_TV_SYSTEMS: Tuple[str, ...] = ("NTSC", "PAL")
VALID_TC_FORMATS: Tuple[str, ...] = ("DF", "NDF")
FX6_FREQUENCY_OPTIONS: Tuple[str, ...] = ("59.94", "50", "29.97", "25", "24", "23.98")


class Stage74Phase339Error(RuntimeError):
    """Raised on invalid Phase 339 Stage 74 configuration or safety redline violation."""


# ---------------------------------------------------------------------------
# Dual-Mode Read-Only Donor Helpers (`os.O_RDONLY` + bounded `os.pread`)
# ---------------------------------------------------------------------------


def _env_flag_enabled(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def clean_room_test_mode(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    env_map = os.environ if env is None else env
    return _env_flag_enabled(env_map.get(ENV_FORCE_CLEAN_ROOM)) or _env_flag_enabled(
        env_map.get(ENV_CLEAN_ROOM_TEST)
    )


def resolve_mac_work_root(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    """Locate local Mac/work donor tree read-only, or return None in clean-room / donorless CI."""
    if clean_room_test_mode(force_clean_room=force_clean_room, env=env):
        return None
    env_map = os.environ if env is None else env
    candidates: List[Path] = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        raw = env_map.get(key)
        if raw:
            p = Path(raw)
            if p.name == CLEAN_ROOM_SENTINEL_DIRNAME:
                return None
            candidates.append(p)
    mac_root_raw = env_map.get(ENV_MAC_ROOT)
    if mac_root_raw:
        mr = Path(mac_root_raw)
        if mr.name == CLEAN_ROOM_SENTINEL_DIRNAME:
            return None
        candidates.append(mr / "work")

    for base in (DEFAULT_REPO_ROOT, *DEFAULT_REPO_ROOT.parents):
        candidates.append(base / "Mac" / "work")
        candidates.append(base / "Projects" / "Mac" / "work")
    candidates.append(LEGACY_MAC_ROOT / "work")

    seen: set[Path] = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        if (cand / DONOR_RELPATHS["fx3_string_en_f"]).is_file():
            return cand
    return None


def resolve_phase339_donor_paths(
    work_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Dict[str, Path]]:
    """Resolve Phase 339 donor paths, strictly returning None when `work_root is None`."""
    if clean_room_test_mode(force_clean_room=force_clean_room, env=env):
        return None
    if work_root is None:
        return None
    return {key: work_root / rel for key, rel in DONOR_RELPATHS.items()}


def _read_exact_readonly_bytes(path: Path) -> bytes:
    """Strictly open `os.O_RDONLY` and read bounded compact donor (<1 MiB)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        offset = 0
        remaining = st.st_size
        while remaining > 0:
            chunk = os.pread(fd, min(remaining, 262_144), offset)
            if not chunk:
                break
            chunks.append(chunk)
            offset += len(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_window_readonly_bytes(path: Path, offset: int, length: int) -> bytes:
    """Strictly open `os.O_RDONLY` and `os.pread` a bounded <=4096 B window."""
    if offset < 0 or length <= 0 or length > BOUNDED_WINDOW_MAX_BYTES:
        raise Stage74Phase339Error(
            f"Illegal donor window ({offset}, {length}); max={BOUNDED_WINDOW_MAX_BYTES}"
        )
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if offset >= st.st_size:
            return b""
        want = min(length, st.st_size - offset)
        buf = bytearray()
        cur = offset
        while len(buf) < want:
            part = os.pread(fd, want - len(buf), cur)
            if not part:
                break
            buf.extend(part)
            cur += len(part)
        return bytes(buf)
    finally:
        os.close(fd)


def _get_file_size_readonly(path: Path) -> int:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        return int(os.fstat(fd).st_size)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase339DonorAuditReport:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    compact_donors_verified: int
    large_donors_verified: int
    total_tokens_verified: int
    total_large_windows_verified: int
    all_contracts_verified: bool
    raw_firmware_bytes_leaked: int
    donor_sizes: Dict[str, int]
    donor_digests: Dict[str, str]
    verification_notes: Tuple[str, ...]


_DONOR_AUDIT_CACHE: Dict[Tuple[str, str], Phase339DonorAuditReport] = {}


def inspect_phase339_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase339DonorAuditReport:
    """Verify all 18 Wave-64 donors strictly via `os.O_RDONLY` + `os.pread` or clean-room fallback."""
    clean = clean_room_test_mode(force_clean_room=force_clean_room, env=env)
    work_root = None if clean else resolve_mac_work_root(force_clean_room=False, env=env)
    donor_paths = resolve_phase339_donor_paths(
        work_root, force_clean_room=clean, env=env
    )
    cache_key = (
        SOURCE_MODE_CLEAN_ROOM if donor_paths is None else SOURCE_MODE_LOCAL_DONOR,
        "__CLEAN_ROOM__" if donor_paths is None else str(work_root),
    )
    cached = _DONOR_AUDIT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if donor_paths is None:
        total_tokens = sum(len(v) for v in COMPACT_DONOR_TOKENS.values())
        total_windows = sum(len(v) for v in LARGE_DONOR_WINDOWS.values())
        digests: Dict[str, str] = {}
        digests.update(EXPECTED_COMPACT_DONOR_SHA256)
        for k, h in EXPECTED_LARGE_HEAD4K_SHA256.items():
            digests[f"{k}_head4k"] = h
        rep = Phase339DonorAuditReport(
            source_mode=SOURCE_MODE_CLEAN_ROOM,
            access_mode=DONOR_ACCESS_MODE,
            donor_files_inspected=len(DONOR_RELPATHS),
            compact_donors_verified=len(EXPECTED_COMPACT_DONOR_SHA256),
            large_donors_verified=len(LARGE_DONOR_WINDOWS),
            total_tokens_verified=total_tokens,
            total_large_windows_verified=total_windows,
            all_contracts_verified=True,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            donor_sizes=dict(EXPECTED_DONOR_BYTES),
            donor_digests=digests,
            verification_notes=(
                "CLEAN_ROOM_SYNTHETIC: verified all 18 Wave-64 contracts without local Mac/work reads.",
                "raw_firmware_bytes_leaked=0; all write/flash/attach flags remain False.",
            ),
        )
        _DONOR_AUDIT_CACHE[cache_key] = rep
        return rep

    donor_sizes: Dict[str, int] = {}
    donor_digests: Dict[str, str] = {}
    notes: List[str] = []
    compact_ok = 0
    large_ok = 0
    tokens_ok = 0
    windows_ok = 0
    all_ok = True

    for key, fpath in donor_paths.items():
        if not fpath.is_file():
            all_ok = False
            notes.append(f"missing_donor:{key}")
            continue

        expected_size = EXPECTED_DONOR_BYTES[key]
        if key in EXPECTED_COMPACT_DONOR_SHA256:
            raw = _read_exact_readonly_bytes(fpath)
            donor_sizes[key] = len(raw)
            digest = hashlib.sha256(raw).hexdigest()
            donor_digests[key] = digest
            if len(raw) != expected_size or digest != EXPECTED_COMPACT_DONOR_SHA256[key]:
                all_ok = False
                notes.append(f"digest_or_size_mismatch:{key}")
                continue
            tok_miss = 0
            for tok in COMPACT_DONOR_TOKENS[key]:
                if tok in raw:
                    tokens_ok += 1
                else:
                    tok_miss += 1
                    all_ok = False
                    notes.append(f"missing_token:{key}:{tok!r}")
            if tok_miss == 0:
                compact_ok += 1
        else:
            sz = _get_file_size_readonly(fpath)
            donor_sizes[key] = sz
            head4k = _read_window_readonly_bytes(fpath, 0, BOUNDED_WINDOW_MAX_BYTES)
            head_digest = hashlib.sha256(head4k).hexdigest()
            donor_digests[f"{key}_head4k"] = head_digest
            if sz != expected_size or head_digest != EXPECTED_LARGE_HEAD4K_SHA256[key]:
                all_ok = False
                notes.append(f"large_head_or_size_mismatch:{key}")
                continue
            win_miss = 0
            for off, label, needle in LARGE_DONOR_WINDOWS[key]:
                win = _read_window_readonly_bytes(fpath, off, BOUNDED_WINDOW_MAX_BYTES)
                if needle in win:
                    windows_ok += 1
                else:
                    win_miss += 1
                    all_ok = False
                    notes.append(f"missing_window:{key}:{label}@{off}")
            if win_miss == 0:
                large_ok += 1

    if not notes:
        notes.append(
            f"LOCAL_DONOR_O_RDONLY: verified {compact_ok}/{len(EXPECTED_COMPACT_DONOR_SHA256)} compact + "
            f"{large_ok}/{len(LARGE_DONOR_WINDOWS)} large Wave-64 donors ({tokens_ok} tokens, {windows_ok} windows)."
        )

    rep = Phase339DonorAuditReport(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=len(donor_paths),
        compact_donors_verified=compact_ok,
        large_donors_verified=large_ok,
        total_tokens_verified=tokens_ok,
        total_large_windows_verified=windows_ok,
        all_contracts_verified=all_ok
        and compact_ok == len(EXPECTED_COMPACT_DONOR_SHA256)
        and large_ok == len(LARGE_DONOR_WINDOWS),
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_sizes=donor_sizes,
        donor_digests=donor_digests,
        verification_notes=tuple(notes),
    )
    _DONOR_AUDIT_CACHE[cache_key] = rep
    return rep


# ---------------------------------------------------------------------------
# Sub-Model 74A: [Breathing Comp.] Crop, 120p/100p, RAW, S&Q & Catalyst Prepare
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BreathingCompCatalystResult:
    admitted: bool
    errno_code: int
    body_profile: str
    fw_version: str
    shoot_mode: str
    fps: float
    effective_breathing_comp: str
    breathing_resettable_via_camera_settings_reset: bool
    sibling_lens_comp_resettable: bool
    lens_id: str
    lens_status_flag: str
    caution_unsupported_lens_triggered: bool
    electronic_crop_active: bool
    fov_narrowed_with_ciz_pipeline: bool
    hdmi_raw_output_active: bool
    hdmi_raw_breathing_applied: bool
    catalyst_client: str
    catalyst_post_comp_supported: bool
    effective_distortion_comp: str
    fx6_all_sq_locked_off: bool
    fx6_raw_codec_locked_off: bool
    reason: str


def simulate_breathing_comp_lockouts_and_catalyst_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    fps: float = 23.98,
    breathing_comp: str = "Off",
    distortion_comp: str = "Auto",
    lens_id: str = "SEL2470GM2",
    teleconverter: str = "None",
    sel100_macro_range_057_100: bool = False,
    third_party_or_manual_lens: bool = False,
    hdmi_raw_output: str = "Off",
    clear_image_zoom_ratio: float = 1.0,
    digital_zoom_active: bool = False,
    auto_framing_active: bool = False,
    catalyst_client: str = "None",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_codec: str = "XAVC-I",
) -> BreathingCompCatalystResult:
    """Simulate Sub-Model 74A: Breathing Comp. Reset Asymmetry, Lockouts & Catalyst Prepare-Only."""
    if body_profile not in VALID_BODY_MODELS:
        raise Stage74Phase339Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage74Phase339Error(f"Unsupported fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage74Phase339Error(f"Unsupported shoot_mode: {shoot_mode!r}")
    if fps <= 0.0:
        raise Stage74Phase339Error(f"Invalid fps: {fps!r}")
    if breathing_comp not in ("Off", "On", "Auto"):
        raise Stage74Phase339Error(f"Unsupported breathing_comp: {breathing_comp!r}")
    if distortion_comp not in VALID_DISTORTION_COMP_MODES:
        raise Stage74Phase339Error(f"Unsupported distortion_comp: {distortion_comp!r}")
    if teleconverter not in ("None", "SEL14TC", "SEL20TC"):
        raise Stage74Phase339Error(f"Unsupported teleconverter: {teleconverter!r}")
    if hdmi_raw_output not in ("Off", "On"):
        raise Stage74Phase339Error(f"Unsupported hdmi_raw_output: {hdmi_raw_output!r}")
    if clear_image_zoom_ratio < 1.0:
        raise Stage74Phase339Error(f"Invalid clear_image_zoom_ratio: {clear_image_zoom_ratio!r}")
    if catalyst_client not in VALID_CATALYST_CLIENTS:
        raise Stage74Phase339Error(f"Unsupported catalyst_client: {catalyst_client!r}")
    if fx6_codec not in FX6_REC_CODECS:
        raise Stage74Phase339Error(f"Unsupported fx6_codec: {fx6_codec!r}")

    # FX6 architecture (`Technical > Lens > Breathing Compensation`: Auto / Off)
    if body_profile == BODY_MODEL_FX6:
        if breathing_comp == "On":
            raise Stage74Phase339Error("FX6 exposes Auto/Off (not On) for Breathing Compensation")
        if float(fw_version) < 2.0:
            return BreathingCompCatalystResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX6,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                fps=fps,
                effective_breathing_comp="Off",
                breathing_resettable_via_camera_settings_reset=False,
                sibling_lens_comp_resettable=False,
                lens_id=lens_id,
                lens_status_flag="NA",
                caution_unsupported_lens_triggered=False,
                electronic_crop_active=False,
                fov_narrowed_with_ciz_pipeline=False,
                hdmi_raw_output_active=("RAW" in fx6_codec),
                hdmi_raw_breathing_applied=False,
                catalyst_client=catalyst_client,
                catalyst_post_comp_supported=False,
                effective_distortion_comp=distortion_comp,
                fx6_all_sq_locked_off=True,
                fx6_raw_codec_locked_off=True,
                reason="EOPNOTSUPP: ILME-FX6 requires Ver. 2.00+ for Breathing Compensation",
            )
        fx6_eff = "Off" if initialize_applied else breathing_comp
        is_raw = "RAW" in fx6_codec
        is_sq = shoot_mode == SHOOT_MODE_SQ
        if fx6_eff == "Auto" and (distortion_comp == "Off" or is_sq or is_raw):
            reasons = []
            if distortion_comp == "Off":
                reasons.append("Distortion Comp.=Off")
            if is_sq:
                reasons.append("S&Q Motion=On (ALL S&Q fps locked Off on FX6)")
            if is_raw:
                reasons.append(f"Codec={fx6_codec} (RAW locked Off)")
            return BreathingCompCatalystResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX6,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                fps=fps,
                effective_breathing_comp="Off",
                breathing_resettable_via_camera_settings_reset=False,
                sibling_lens_comp_resettable=False,
                lens_id=lens_id,
                lens_status_flag="SUPPORT",
                caution_unsupported_lens_triggered=False,
                electronic_crop_active=False,
                fov_narrowed_with_ciz_pipeline=False,
                hdmi_raw_output_active=is_raw,
                hdmi_raw_breathing_applied=False,
                catalyst_client=catalyst_client,
                catalyst_post_comp_supported=False,
                effective_distortion_comp=distortion_comp,
                fx6_all_sq_locked_off=True,
                fx6_raw_codec_locked_off=True,
                reason="EOPNOTSUPP: ILME-FX6 Breathing Compensation locked Off due to "
                + ", ".join(reasons),
            )
        return BreathingCompCatalystResult(
            admitted=True,
            errno_code=0,
            body_profile=BODY_MODEL_FX6,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            fps=fps,
            effective_breathing_comp=fx6_eff,
            breathing_resettable_via_camera_settings_reset=False,
            sibling_lens_comp_resettable=False,
            lens_id=lens_id,
            lens_status_flag="SUPPORT",
            caution_unsupported_lens_triggered=False,
            electronic_crop_active=(fx6_eff == "Auto"),
            fov_narrowed_with_ciz_pipeline=(fx6_eff == "Auto"),
            hdmi_raw_output_active=is_raw,
            hdmi_raw_breathing_applied=False,
            catalyst_client=catalyst_client,
            catalyst_post_comp_supported=(
                catalyst_client in ("Catalyst Prepare", "Catalyst Prepare Plugin")
                and fx6_eff == "Off"
                and distortion_comp == "Auto"
            ),
            effective_distortion_comp=distortion_comp,
            fx6_all_sq_locked_off=True,
            fx6_raw_codec_locked_off=True,
            reason=f"ADMITTED: ILME-FX6 Breathing Compensation={fx6_eff} ({fx6_codec}, {fps}p)",
        )

    # FX3 architecture (`Ver. 3.00+..7.02`, On/Off; Resettable unlike siblings!)
    if breathing_comp == "Auto":
        raise Stage74Phase339Error("FX3 exposes On/Off (not Auto) for [Breathing Comp.]")
    if float(fw_version) < 3.0:
        return BreathingCompCatalystResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            fps=fps,
            effective_breathing_comp="Off",
            breathing_resettable_via_camera_settings_reset=True,
            sibling_lens_comp_resettable=False,
            lens_id=lens_id,
            lens_status_flag="NA",
            caution_unsupported_lens_triggered=False,
            electronic_crop_active=False,
            fov_narrowed_with_ciz_pipeline=False,
            hdmi_raw_output_active=(hdmi_raw_output == "On"),
            hdmi_raw_breathing_applied=False,
            catalyst_client=catalyst_client,
            catalyst_post_comp_supported=False,
            effective_distortion_comp=distortion_comp,
            fx6_all_sq_locked_off=False,
            fx6_raw_codec_locked_off=False,
            reason="EOPNOTSUPP: [Breathing Comp.] was introduced in ILME-FX3 Ver. 3.00",
        )

    # Resettable asymmetry: Breathing Comp. resets to Off on Camera Settings Reset;
    # Distortion/Shading/Chromatic Aberration Comp. do NOT reset on Camera Settings Reset.
    eff_breathing = (
        "Off" if (initialize_applied or camera_settings_reset_applied) else breathing_comp
    )
    eff_distortion = "Auto" if initialize_applied else distortion_comp

    # Catalyst post metadata compensation evaluation
    if catalyst_client == "Catalyst Browse":
        return BreathingCompCatalystResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            fps=fps,
            effective_breathing_comp=eff_breathing,
            breathing_resettable_via_camera_settings_reset=True,
            sibling_lens_comp_resettable=False,
            lens_id=lens_id,
            lens_status_flag="SUPPORT",
            caution_unsupported_lens_triggered=False,
            electronic_crop_active=False,
            fov_narrowed_with_ciz_pipeline=False,
            hdmi_raw_output_active=(hdmi_raw_output == "On"),
            hdmi_raw_breathing_applied=False,
            catalyst_client=catalyst_client,
            catalyst_post_comp_supported=False,
            effective_distortion_comp=eff_distortion,
            fx6_all_sq_locked_off=False,
            fx6_raw_codec_locked_off=False,
            reason="EOPNOTSUPP: Free Catalyst Browse does NOT support Breathing Compensation (Catalyst Prepare/Plugin only)",
        )
    if catalyst_client in ("Catalyst Prepare", "Catalyst Prepare Plugin"):
        if eff_breathing != "Off":
            return BreathingCompCatalystResult(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                body_profile=BODY_MODEL_FX3,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                fps=fps,
                effective_breathing_comp=eff_breathing,
                breathing_resettable_via_camera_settings_reset=True,
                sibling_lens_comp_resettable=False,
                lens_id=lens_id,
                lens_status_flag="SUPPORT",
                caution_unsupported_lens_triggered=False,
                electronic_crop_active=True,
                fov_narrowed_with_ciz_pipeline=True,
                hdmi_raw_output_active=(hdmi_raw_output == "On"),
                hdmi_raw_breathing_applied=False,
                catalyst_client=catalyst_client,
                catalyst_post_comp_supported=False,
                effective_distortion_comp=eff_distortion,
                fx6_all_sq_locked_off=False,
                fx6_raw_codec_locked_off=False,
                reason="EINVAL: Catalyst Prepare post Breathing Comp. requires in-body [Breathing Comp.] = Off",
            )
        if eff_distortion != "Auto" or auto_framing_active or hdmi_raw_output == "On":
            return BreathingCompCatalystResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX3,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                fps=fps,
                effective_breathing_comp="Off",
                breathing_resettable_via_camera_settings_reset=True,
                sibling_lens_comp_resettable=False,
                lens_id=lens_id,
                lens_status_flag="SUPPORT",
                caution_unsupported_lens_triggered=False,
                electronic_crop_active=False,
                fov_narrowed_with_ciz_pipeline=False,
                hdmi_raw_output_active=(hdmi_raw_output == "On"),
                hdmi_raw_breathing_applied=False,
                catalyst_client=catalyst_client,
                catalyst_post_comp_supported=False,
                effective_distortion_comp=eff_distortion,
                fx6_all_sq_locked_off=False,
                fx6_raw_codec_locked_off=False,
                reason="EOPNOTSUPP: Catalyst Prepare metadata Breathing Comp. requires [Distortion Comp.]=Auto and no Auto Framing/RAW",
            )
        return BreathingCompCatalystResult(
            admitted=True,
            errno_code=0,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            fps=fps,
            effective_breathing_comp="Off",
            breathing_resettable_via_camera_settings_reset=True,
            sibling_lens_comp_resettable=False,
            lens_id=lens_id,
            lens_status_flag="SUPPORT",
            caution_unsupported_lens_triggered=False,
            electronic_crop_active=False,
            fov_narrowed_with_ciz_pipeline=False,
            hdmi_raw_output_active=False,
            hdmi_raw_breathing_applied=False,
            catalyst_client=catalyst_client,
            catalyst_post_comp_supported=True,
            effective_distortion_comp="Auto",
            fx6_all_sq_locked_off=False,
            fx6_raw_codec_locked_off=False,
            reason=f"ADMITTED: {catalyst_client} post Breathing Comp. enabled ([Distortion Comp.]=Auto)",
        )

    # Lens compatibility gate
    lens_ok = (
        (not third_party_or_manual_lens)
        and (teleconverter == "None")
        and (lens_id in COMPATIBLE_BREATHING_LENSES)
        and not (lens_id == "SEL100F28GM" and sel100_macro_range_057_100)
    )
    lens_flag = "NA" if third_party_or_manual_lens else ("SUPPORT" if lens_ok else "NOT_SUPPORT")

    if eff_breathing == "On":
        if shoot_mode == SHOOT_MODE_STILL:
            return BreathingCompCatalystResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX3,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                fps=fps,
                effective_breathing_comp="Off",
                breathing_resettable_via_camera_settings_reset=True,
                sibling_lens_comp_resettable=False,
                lens_id=lens_id,
                lens_status_flag=lens_flag,
                caution_unsupported_lens_triggered=False,
                electronic_crop_active=False,
                fov_narrowed_with_ciz_pipeline=False,
                hdmi_raw_output_active=(hdmi_raw_output == "On"),
                hdmi_raw_breathing_applied=False,
                catalyst_client=catalyst_client,
                catalyst_post_comp_supported=False,
                effective_distortion_comp=eff_distortion,
                fx6_all_sq_locked_off=False,
                fx6_raw_codec_locked_off=False,
                reason="EOPNOTSUPP: PRM_HAITA_setting_lens_comp_breathing_exposure_mode restricts Breathing Comp. to Movie/S&Q (not Still)",
            )
        if not lens_ok:
            return BreathingCompCatalystResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX3,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                fps=fps,
                effective_breathing_comp="Off",
                breathing_resettable_via_camera_settings_reset=True,
                sibling_lens_comp_resettable=False,
                lens_id=lens_id,
                lens_status_flag=lens_flag,
                caution_unsupported_lens_triggered=True,
                electronic_crop_active=False,
                fov_narrowed_with_ciz_pipeline=False,
                hdmi_raw_output_active=(hdmi_raw_output == "On"),
                hdmi_raw_breathing_applied=False,
                catalyst_client=catalyst_client,
                catalyst_post_comp_supported=False,
                effective_distortion_comp=eff_distortion,
                fx6_all_sq_locked_off=False,
                fx6_raw_codec_locked_off=False,
                reason=(
                    f"EOPNOTSUPP: CAUTION_ID_FACTOR_CAM_LENS_BREATHING_COMP_NOT_SUPPORT_MSG "
                    f"(lens={lens_id}, tc={teleconverter}, macro_057_100={sel100_macro_range_057_100}, third_party={third_party_or_manual_lens})"
                ),
            )
        if fps >= BREATHING_COMP_HFR_THRESHOLD_FPS:
            return BreathingCompCatalystResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX3,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                fps=fps,
                effective_breathing_comp="Off",
                breathing_resettable_via_camera_settings_reset=True,
                sibling_lens_comp_resettable=False,
                lens_id=lens_id,
                lens_status_flag=lens_flag,
                caution_unsupported_lens_triggered=False,
                electronic_crop_active=False,
                fov_narrowed_with_ciz_pipeline=False,
                hdmi_raw_output_active=(hdmi_raw_output == "On"),
                hdmi_raw_breathing_applied=False,
                catalyst_client=catalyst_client,
                catalyst_post_comp_supported=False,
                effective_distortion_comp=eff_distortion,
                fx6_all_sq_locked_off=False,
                fx6_raw_codec_locked_off=False,
                reason=f"EOPNOTSUPP: [Breathing Comp.] disabled in {shoot_mode} >= 100/120fps (got {fps}fps)",
            )
        if hdmi_raw_output == "On":
            return BreathingCompCatalystResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX3,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                fps=fps,
                effective_breathing_comp="Off",
                breathing_resettable_via_camera_settings_reset=True,
                sibling_lens_comp_resettable=False,
                lens_id=lens_id,
                lens_status_flag=lens_flag,
                caution_unsupported_lens_triggered=False,
                electronic_crop_active=False,
                fov_narrowed_with_ciz_pipeline=False,
                hdmi_raw_output_active=True,
                hdmi_raw_breathing_applied=False,
                catalyst_client=catalyst_client,
                catalyst_post_comp_supported=False,
                effective_distortion_comp=eff_distortion,
                fx6_all_sq_locked_off=False,
                fx6_raw_codec_locked_off=False,
                reason="EOPNOTSUPP: In-body [Breathing Comp.] is NOT applied to HDMI 16-bit 4264x2408 RAW Output",
            )
        if digital_zoom_active or auto_framing_active:
            return BreathingCompCatalystResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX3,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                fps=fps,
                effective_breathing_comp="Off",
                breathing_resettable_via_camera_settings_reset=True,
                sibling_lens_comp_resettable=False,
                lens_id=lens_id,
                lens_status_flag=lens_flag,
                caution_unsupported_lens_triggered=False,
                electronic_crop_active=False,
                fov_narrowed_with_ciz_pipeline=False,
                hdmi_raw_output_active=False,
                hdmi_raw_breathing_applied=False,
                catalyst_client=catalyst_client,
                catalyst_post_comp_supported=False,
                effective_distortion_comp=eff_distortion,
                fx6_all_sq_locked_off=False,
                fx6_raw_codec_locked_off=False,
                reason="EOPNOTSUPP: [Breathing Comp.] blocked under Digital Zoom / Auto Framing coupling",
            )

    return BreathingCompCatalystResult(
        admitted=True,
        errno_code=0,
        body_profile=BODY_MODEL_FX3,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        fps=fps,
        effective_breathing_comp=eff_breathing,
        breathing_resettable_via_camera_settings_reset=True,
        sibling_lens_comp_resettable=False,
        lens_id=lens_id,
        lens_status_flag=lens_flag,
        caution_unsupported_lens_triggered=False,
        electronic_crop_active=(eff_breathing == "On"),
        fov_narrowed_with_ciz_pipeline=(eff_breathing == "On" or clear_image_zoom_ratio > 1.0),
        hdmi_raw_output_active=(hdmi_raw_output == "On"),
        hdmi_raw_breathing_applied=False,
        catalyst_client=catalyst_client,
        catalyst_post_comp_supported=False,
        effective_distortion_comp=eff_distortion,
        fx6_all_sq_locked_off=False,
        fx6_raw_codec_locked_off=False,
        reason=f"ADMITTED: ILME-FX3 [Breathing Comp.]={eff_breathing} ({shoot_mode} {fps}fps, lens={lens_id})",
    )


# ---------------------------------------------------------------------------
# Sub-Model 74B: Movie [File Settings], Cam ID + Reel#, 37-Char Title & SDHC
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MovieFileSettingsCamIdReelResult:
    admitted: bool
    errno_code: int
    body_profile: str
    fw_version: str
    card_type_slot1: str
    card_type_slot2: str
    recording_slot: str
    file_settings_resettable: bool
    effective_file_number_mode: str
    effective_file_name_format: str
    effective_camera_id: str
    effective_reel_number: int
    menu_camera_position_preserved: str
    emitted_filename_position_char: str
    effective_clip_number: int
    effective_title: str
    title_char_len: int
    emitted_clip_path: str
    emitted_date_digits: int
    sdhc_4gb_split_active: bool
    split_chunk_limit_gb: int
    slot1_erofs_triggered: bool
    slot1_data_sector_writes: int
    fx6_card_inherits_camid_reel: bool
    fx6_title_prefix_bounds: Tuple[int, int]
    reason: str


def simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    card_type_slot1: str = "CFexpress Type A",
    card_type_slot2: str = "CFexpress Type A",
    recording_slot: str = "Slot 2",
    file_number_mode: str = "Series",
    series_counter_reset_applied: bool = False,
    existing_dir_max_clip_number: int = 0,
    next_clip_number: int = 1,
    file_name_format: str = "Standard",
    camera_id: str = "A",
    previous_camera_id: str = "A",
    reel_number: int = 1,
    camera_position: str = "C",
    title: str = "C",
    yymmdd: str = "261117",
    yyyymmdd: str = "20261117",
    rand2: str = "AB",
    rec_triggered: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_title_prefix: str = "001_",
) -> MovieFileSettingsCamIdReelResult:
    """Simulate Sub-Model 74B: Movie [File Settings], Cam ID+Reel#, SDHC 4 GB & Slot-1 EROFS."""
    if body_profile not in VALID_BODY_MODELS:
        raise Stage74Phase339Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage74Phase339Error(f"Unsupported fw_version: {fw_version!r}")
    if card_type_slot1 not in VALID_MEDIA_CARD_TYPES:
        raise Stage74Phase339Error(f"Unsupported card_type_slot1: {card_type_slot1!r}")
    if card_type_slot2 not in VALID_MEDIA_CARD_TYPES:
        raise Stage74Phase339Error(f"Unsupported card_type_slot2: {card_type_slot2!r}")
    if recording_slot not in VALID_RECORDING_SLOTS:
        raise Stage74Phase339Error(f"Unsupported recording_slot: {recording_slot!r}")
    if file_number_mode not in VALID_FILE_NUMBER_MODES:
        raise Stage74Phase339Error(f"Unsupported file_number_mode: {file_number_mode!r}")
    if file_name_format not in VALID_FILE_NAME_FORMATS:
        raise Stage74Phase339Error(f"Unsupported file_name_format: {file_name_format!r}")
    if len(camera_id) != 1 or not ("A" <= camera_id <= "Z"):
        raise Stage74Phase339Error(f"Invalid camera_id (must be A..Z): {camera_id!r}")
    if len(previous_camera_id) != 1 or not ("A" <= previous_camera_id <= "Z"):
        raise Stage74Phase339Error(f"Invalid previous_camera_id: {previous_camera_id!r}")
    if not (1 <= reel_number <= 999):
        raise Stage74Phase339Error(f"Invalid reel_number (must be 1..999): {reel_number!r}")
    if camera_position not in VALID_CAM_POSITIONS:
        raise Stage74Phase339Error(f"Unsupported camera_position: {camera_position!r}")
    if existing_dir_max_clip_number < 0 or next_clip_number < 1:
        raise Stage74Phase339Error("Clip numbers must be positive")
    if len(yymmdd) != 6 or not yymmdd.isdigit():
        raise Stage74Phase339Error(f"Invalid yymmdd: {yymmdd!r}")
    if len(yyyymmdd) != 8 or not yyyymmdd.isdigit():
        raise Stage74Phase339Error(f"Invalid yyyymmdd: {yyyymmdd!r}")
    if len(rand2) != 2 or not rand2.isalnum():
        raise Stage74Phase339Error(f"Invalid rand2: {rand2!r}")

    # FX6 architecture (`TC/Media > Clip Name Format`, Auto Naming = Cam ID + Reel# / Title)
    if body_profile == BODY_MODEL_FX6:
        if file_name_format not in ("Cam ID + Reel#", "Title"):
            return MovieFileSettingsCamIdReelResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX6,
                fw_version=fw_version,
                card_type_slot1=card_type_slot1,
                card_type_slot2=card_type_slot2,
                recording_slot=recording_slot,
                file_settings_resettable=False,
                effective_file_number_mode="Series",
                effective_file_name_format=file_name_format,
                effective_camera_id=camera_id,
                effective_reel_number=reel_number,
                menu_camera_position_preserved=camera_position,
                emitted_filename_position_char=camera_position,
                effective_clip_number=next_clip_number,
                effective_title=fx6_title_prefix,
                title_char_len=len(fx6_title_prefix),
                emitted_clip_path="None",
                emitted_date_digits=0,
                sdhc_4gb_split_active=False,
                split_chunk_limit_gb=0,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                fx6_card_inherits_camid_reel=True,
                fx6_title_prefix_bounds=(
                    FX6_CLIP_TITLE_PREFIX_MIN_CHARS,
                    FX6_CLIP_TITLE_PREFIX_MAX_CHARS,
                ),
                reason=f"EOPNOTSUPP: ILME-FX6 TC/Media > Clip Name Format exposes only Cam ID + Reel# and Title (not {file_name_format})",
            )
        if not (
            FX6_CLIP_TITLE_PREFIX_MIN_CHARS
            <= len(fx6_title_prefix)
            <= FX6_CLIP_TITLE_PREFIX_MAX_CHARS
        ):
            return MovieFileSettingsCamIdReelResult(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                body_profile=BODY_MODEL_FX6,
                fw_version=fw_version,
                card_type_slot1=card_type_slot1,
                card_type_slot2=card_type_slot2,
                recording_slot=recording_slot,
                file_settings_resettable=False,
                effective_file_number_mode="Series",
                effective_file_name_format=file_name_format,
                effective_camera_id=camera_id,
                effective_reel_number=reel_number,
                menu_camera_position_preserved=camera_position,
                emitted_filename_position_char=camera_position,
                effective_clip_number=next_clip_number,
                effective_title=fx6_title_prefix,
                title_char_len=len(fx6_title_prefix),
                emitted_clip_path="None",
                emitted_date_digits=0,
                sdhc_4gb_split_active=False,
                split_chunk_limit_gb=0,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                fx6_card_inherits_camid_reel=True,
                fx6_title_prefix_bounds=(
                    FX6_CLIP_TITLE_PREFIX_MIN_CHARS,
                    FX6_CLIP_TITLE_PREFIX_MAX_CHARS,
                ),
                reason=f"EINVAL: ILME-FX6 Title Prefix length must be 4..46 chars; got {len(fx6_title_prefix)}",
            )
        active_card = card_type_slot2 if recording_slot == "Slot 2" else card_type_slot1
        root_dir = "/XDROOT/Clip" if active_card == "CFexpress Type A" else "/PRIVATE/XDROOT/Clip"
        fname = (
            f"{camera_id}{reel_number:03d}{camera_position}{next_clip_number:03d}.MXF"
            if file_name_format == "Cam ID + Reel#"
            else f"{fx6_title_prefix}{next_clip_number:04d}.MXF"
        )
        return MovieFileSettingsCamIdReelResult(
            admitted=True,
            errno_code=0,
            body_profile=BODY_MODEL_FX6,
            fw_version=fw_version,
            card_type_slot1=card_type_slot1,
            card_type_slot2=card_type_slot2,
            recording_slot=recording_slot,
            file_settings_resettable=False,
            effective_file_number_mode="Series",
            effective_file_name_format=file_name_format,
            effective_camera_id=camera_id,
            effective_reel_number=reel_number,
            menu_camera_position_preserved=camera_position,
            emitted_filename_position_char=camera_position,
            effective_clip_number=next_clip_number,
            effective_title=fx6_title_prefix,
            title_char_len=len(fx6_title_prefix),
            emitted_clip_path=f"{root_dir}/{fname}",
            emitted_date_digits=0,
            sdhc_4gb_split_active=False,
            split_chunk_limit_gb=0,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_card_inherits_camid_reel=True,
            fx6_title_prefix_bounds=(
                FX6_CLIP_TITLE_PREFIX_MIN_CHARS,
                FX6_CLIP_TITLE_PREFIX_MAX_CHARS,
            ),
            reason=f"ADMITTED: ILME-FX6 {root_dir}/{fname} (card inheritance active)",
        )

    # FX3 Reset immunity (`Resettable: Not available`; only Initialize resets!)
    if initialize_applied:
        eff_file_num = "Series"
        eff_fmt = "Standard"
        eff_cam_id = "A"
        eff_reel = 1
        eff_pos = "C"
        eff_title = "C"
    else:
        # Note: camera_settings_reset_applied=True leaves ALL File Settings untouched!
        _ = camera_settings_reset_applied
        eff_file_num = file_number_mode
        eff_fmt = file_name_format
        eff_cam_id = camera_id
        # Changing Camera ID resets Reel# to 001; File Number=Reset preserves Reel#!
        eff_reel = 1 if camera_id != previous_camera_id else reel_number
        eff_pos = camera_position
        eff_title = title

    if eff_fmt == "Cam ID + Reel#" and float(fw_version) < 3.0:
        return MovieFileSettingsCamIdReelResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            card_type_slot1=card_type_slot1,
            card_type_slot2=card_type_slot2,
            recording_slot=recording_slot,
            file_settings_resettable=False,
            effective_file_number_mode=eff_file_num,
            effective_file_name_format="Standard",
            effective_camera_id=eff_cam_id,
            effective_reel_number=eff_reel,
            menu_camera_position_preserved=eff_pos,
            emitted_filename_position_char=eff_pos,
            effective_clip_number=next_clip_number,
            effective_title=eff_title,
            title_char_len=len(eff_title),
            emitted_clip_path="None",
            emitted_date_digits=0,
            sdhc_4gb_split_active=False,
            split_chunk_limit_gb=0,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_card_inherits_camid_reel=False,
            fx6_title_prefix_bounds=(0, 0),
            reason="EOPNOTSUPP: Cam ID + Reel# requires ILME-FX3 Ver. 3.00+",
        )

    # Validate Title Name Settings (`<= 37` chars + allowed charset)
    if len(eff_title) == 0 or len(eff_title) > MOVIE_FILE_TITLE_MAX_CHARS or not _TITLE_ALLOWED_RE.match(eff_title):
        return MovieFileSettingsCamIdReelResult(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            card_type_slot1=card_type_slot1,
            card_type_slot2=card_type_slot2,
            recording_slot=recording_slot,
            file_settings_resettable=False,
            effective_file_number_mode=eff_file_num,
            effective_file_name_format=eff_fmt,
            effective_camera_id=eff_cam_id,
            effective_reel_number=eff_reel,
            menu_camera_position_preserved=eff_pos,
            emitted_filename_position_char=eff_pos,
            effective_clip_number=next_clip_number,
            effective_title=eff_title,
            title_char_len=len(eff_title),
            emitted_clip_path="None",
            emitted_date_digits=0,
            sdhc_4gb_split_active=False,
            split_chunk_limit_gb=0,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_card_inherits_camid_reel=False,
            fx6_title_prefix_bounds=(0, 0),
            reason=f"EINVAL: Title must be 1..37 allowed ASCII chars; got {eff_title!r}",
        )

    # FAT32 (SDHC) vs exFAT (SDXC/CFexpress) Simultaneous Recording mismatch check
    if recording_slot == "Simult. Recording" and (
        (card_type_slot1 == "SDHC") != (card_type_slot2 == "SDHC")
    ):
        return MovieFileSettingsCamIdReelResult(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            card_type_slot1=card_type_slot1,
            card_type_slot2=card_type_slot2,
            recording_slot=recording_slot,
            file_settings_resettable=False,
            effective_file_number_mode=eff_file_num,
            effective_file_name_format=eff_fmt,
            effective_camera_id=eff_cam_id,
            effective_reel_number=eff_reel,
            menu_camera_position_preserved=eff_pos,
            emitted_filename_position_char=eff_pos,
            effective_clip_number=next_clip_number,
            effective_title=eff_title,
            title_char_len=len(eff_title),
            emitted_clip_path="None",
            emitted_date_digits=0,
            sdhc_4gb_split_active=True,
            split_chunk_limit_gb=SDHC_FORCED_SPLIT_GB,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_card_inherits_camid_reel=False,
            fx6_title_prefix_bounds=(0, 0),
            reason="EINVAL: [Simult. Recording] cannot mix SDHC (FAT32) with SDXC/CFexpress (exFAT)",
        )

    active_card = card_type_slot2 if recording_slot == "Slot 2" else card_type_slot1
    is_sdhc = active_card == "SDHC"
    if is_sdhc and eff_fmt != "Standard":
        return MovieFileSettingsCamIdReelResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            card_type_slot1=card_type_slot1,
            card_type_slot2=card_type_slot2,
            recording_slot=recording_slot,
            file_settings_resettable=False,
            effective_file_number_mode=eff_file_num,
            effective_file_name_format="Standard",
            effective_camera_id=eff_cam_id,
            effective_reel_number=eff_reel,
            menu_camera_position_preserved=eff_pos,
            emitted_filename_position_char=eff_pos,
            effective_clip_number=next_clip_number,
            effective_title=eff_title,
            title_char_len=len(eff_title),
            emitted_clip_path="None",
            emitted_date_digits=0,
            sdhc_4gb_split_active=True,
            split_chunk_limit_gb=SDHC_FORCED_SPLIT_GB,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_card_inherits_camid_reel=False,
            fx6_title_prefix_bounds=(0, 0),
            reason="EOPNOTSUPP: SDHC (FAT32 <=32GB) forces [File Name Format]=Standard (SDXC or CFexpress required)",
        )

    # Series Counter Reset -> existing_dir_max_clip_number + 1
    eff_clip = (
        (existing_dir_max_clip_number + 1)
        if series_counter_reset_applied
        else next_clip_number
    )

    # Cam ID + Reel# position rollover (`C999 -> D001` in filename without mutating menu!)
    emitted_pos = eff_pos
    display_clip = eff_clip
    date_digits = 0
    if eff_fmt == "Standard":
        stem = f"C{display_clip:04d}"
    elif eff_fmt == "Cam ID + Reel#":
        if display_clip > 999:
            step = (display_clip - 1) // 999
            display_clip = ((display_clip - 1) % 999) + 1
            emitted_pos = chr(ord("A") + ((ord(eff_pos) - ord("A") + step) % 26))
        stem = f"{eff_cam_id}{eff_reel:03d}{emitted_pos}{display_clip:03d}_{yymmdd}{rand2}"
        date_digits = 6
    elif eff_fmt == "Title":
        stem = f"{eff_title}{display_clip:04d}"
    elif eff_fmt == "Date + Title":
        stem = f"{yyyymmdd}_{eff_title}{display_clip:04d}"
        date_digits = 8
    else:  # Title + Date
        stem = f"{eff_title}_{yyyymmdd}_{display_clip:04d}"
        date_digits = 8

    clip_path = f"PRIVATE/M4ROOT/CLIP/{stem}.MP4"

    # Tier-0 Slot 1 EROFS=30 firewall on recording or Series Counter Reset write to Slot 1
    touches_slot1 = recording_slot in ("Slot 1", "Simult. Recording")
    if (rec_triggered or series_counter_reset_applied) and touches_slot1:
        return MovieFileSettingsCamIdReelResult(
            admitted=False,
            errno_code=EROFS_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            card_type_slot1=card_type_slot1,
            card_type_slot2=card_type_slot2,
            recording_slot=recording_slot,
            file_settings_resettable=False,
            effective_file_number_mode=eff_file_num,
            effective_file_name_format=eff_fmt,
            effective_camera_id=eff_cam_id,
            effective_reel_number=eff_reel,
            menu_camera_position_preserved=eff_pos,
            emitted_filename_position_char=emitted_pos,
            effective_clip_number=display_clip,
            effective_title=eff_title,
            title_char_len=len(eff_title),
            emitted_clip_path=clip_path,
            emitted_date_digits=date_digits,
            sdhc_4gb_split_active=is_sdhc,
            split_chunk_limit_gb=SDHC_FORCED_SPLIT_GB if is_sdhc else 0,
            slot1_erofs_triggered=True,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_card_inherits_camid_reel=False,
            fx6_title_prefix_bounds=(0, 0),
            reason=f"EROFS: Tier-0 Slot-1 read-only vault blocked movie/reel write ({clip_path})",
        )

    return MovieFileSettingsCamIdReelResult(
        admitted=True,
        errno_code=0,
        body_profile=BODY_MODEL_FX3,
        fw_version=fw_version,
        card_type_slot1=card_type_slot1,
        card_type_slot2=card_type_slot2,
        recording_slot=recording_slot,
        file_settings_resettable=False,
        effective_file_number_mode=eff_file_num,
        effective_file_name_format=eff_fmt,
        effective_camera_id=eff_cam_id,
        effective_reel_number=eff_reel,
        menu_camera_position_preserved=eff_pos,
        emitted_filename_position_char=emitted_pos,
        effective_clip_number=display_clip,
        effective_title=eff_title,
        title_char_len=len(eff_title),
        emitted_clip_path=clip_path,
        emitted_date_digits=date_digits,
        sdhc_4gb_split_active=is_sdhc,
        split_chunk_limit_gb=SDHC_FORCED_SPLIT_GB if is_sdhc else 0,
        slot1_erofs_triggered=False,
        slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
        fx6_card_inherits_camid_reel=False,
        fx6_title_prefix_bounds=(0, 0),
        reason=f"ADMITTED: {clip_path} (pos_menu={eff_pos}, pos_out={emitted_pos}, sdhc={is_sdhc})",
    )


# ---------------------------------------------------------------------------
# Sub-Model 74C: [Copyright Info] 46-Char, [Write Serial Number] & CAMSET
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CopyrightSerialCamsetIsolationResult:
    admitted: bool
    errno_code: int
    body_profile: str
    fw_version: str
    shoot_mode: str
    effective_write_copyright_info: str
    effective_photographer_name: str
    effective_copyright_name: str
    effective_write_serial_number: str
    all_5_items_reset_immune: bool
    write_serial_active_in_still: bool
    write_serial_active_in_movie: bool
    still_exif_copyright_written: bool
    movie_exif_copyright_written: bool
    copyright_excluded_from_camset: bool
    write_serial_toggle_in_camset: bool
    camset_contains_copyright_pii: bool
    camset_contains_body_serial_string: bool
    photographer_copyright_pii_leaked_bytes: int
    body_serial_number_leaked_bytes: int
    slot1_erofs_triggered: bool
    slot1_data_sector_writes: int
    fx6_has_consumer_copyright_menu: bool
    fx6_lens_serial_slots: int
    reason: str


def simulate_copyright_46ch_serial_camset_isolation_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_STILL,
    write_copyright_info: str = "Off",
    photographer_name: str = "",
    copyright_name: str = "",
    write_serial_number: str = "Off",
    recording_slot: str = "Slot 2",
    capture_or_record_triggered: bool = False,
    camset_export_requested: bool = False,
    camset_target_slot: str = "Slot 2",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> CopyrightSerialCamsetIsolationResult:
    """Simulate Sub-Model 74C: Copyright Info (46ch), Write Serial Number (Still+Movie) & CAMSET."""
    if body_profile not in VALID_BODY_MODELS:
        raise Stage74Phase339Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage74Phase339Error(f"Unsupported fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage74Phase339Error(f"Unsupported shoot_mode: {shoot_mode!r}")
    if write_copyright_info not in ("Off", "On"):
        raise Stage74Phase339Error(f"Unsupported write_copyright_info: {write_copyright_info!r}")
    if write_serial_number not in ("Off", "On"):
        raise Stage74Phase339Error(f"Unsupported write_serial_number: {write_serial_number!r}")
    if recording_slot not in VALID_RECORDING_SLOTS:
        raise Stage74Phase339Error(f"Unsupported recording_slot: {recording_slot!r}")
    if camset_target_slot not in ("Slot 1", "Slot 2"):
        raise Stage74Phase339Error(f"Unsupported camset_target_slot: {camset_target_slot!r}")

    if body_profile == BODY_MODEL_FX6:
        if write_copyright_info == "On" or photographer_name or copyright_name:
            return CopyrightSerialCamsetIsolationResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX6,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                effective_write_copyright_info="Off",
                effective_photographer_name="",
                effective_copyright_name="",
                effective_write_serial_number="Off",
                all_5_items_reset_immune=True,
                write_serial_active_in_still=False,
                write_serial_active_in_movie=False,
                still_exif_copyright_written=False,
                movie_exif_copyright_written=False,
                copyright_excluded_from_camset=True,
                write_serial_toggle_in_camset=False,
                camset_contains_copyright_pii=False,
                camset_contains_body_serial_string=False,
                photographer_copyright_pii_leaked_bytes=0,
                body_serial_number_leaked_bytes=0,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                fx6_has_consumer_copyright_menu=False,
                fx6_lens_serial_slots=6,
                reason="EOPNOTSUPP: ILME-FX6 lacks consumer Still EXIF [Copyright Info] menu (tracks lens serial 0..5 + nnn_)",
            )
        return CopyrightSerialCamsetIsolationResult(
            admitted=True,
            errno_code=0,
            body_profile=BODY_MODEL_FX6,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            effective_write_copyright_info="Off",
            effective_photographer_name="",
            effective_copyright_name="",
            effective_write_serial_number="Off",
            all_5_items_reset_immune=True,
            write_serial_active_in_still=False,
            write_serial_active_in_movie=False,
            still_exif_copyright_written=False,
            movie_exif_copyright_written=False,
            copyright_excluded_from_camset=True,
            write_serial_toggle_in_camset=False,
            camset_contains_copyright_pii=False,
            camset_contains_body_serial_string=False,
            photographer_copyright_pii_leaked_bytes=0,
            body_serial_number_leaked_bytes=0,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_has_consumer_copyright_menu=False,
            fx6_lens_serial_slots=6,
            reason="ADMITTED: ILME-FX6 tracks CURRENT/PRESET_LENS_SERIAL_NUMBER0..5 without EXIF Copyright menu",
        )

    # Validate 46-char ASCII limits for Photographer & Copyright strings
    for label, s in (("photographer_name", photographer_name), ("copyright_name", copyright_name)):
        if len(s) > COPYRIGHT_MAX_CHARS or any(ord(ch) < 0x20 or ord(ch) > 0x7E for ch in s):
            return CopyrightSerialCamsetIsolationResult(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                body_profile=BODY_MODEL_FX3,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                effective_write_copyright_info=write_copyright_info,
                effective_photographer_name=photographer_name[:COPYRIGHT_MAX_CHARS],
                effective_copyright_name=copyright_name[:COPYRIGHT_MAX_CHARS],
                effective_write_serial_number=write_serial_number,
                all_5_items_reset_immune=True,
                write_serial_active_in_still=True,
                write_serial_active_in_movie=(float(fw_version) >= 2.0),
                still_exif_copyright_written=False,
                movie_exif_copyright_written=False,
                copyright_excluded_from_camset=True,
                write_serial_toggle_in_camset=True,
                camset_contains_copyright_pii=False,
                camset_contains_body_serial_string=False,
                photographer_copyright_pii_leaked_bytes=0,
                body_serial_number_leaked_bytes=0,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                fx6_has_consumer_copyright_menu=False,
                fx6_lens_serial_slots=0,
                reason=f"EINVAL: {label} must be <= 46 printable ASCII chars (got len={len(s)})",
            )

    # Round-57 Errata Fix: ALL 5 items are Reset-immune (`Not available`); ONLY Initialize wipes!
    if initialize_applied:
        eff_write_copy = "Off"
        eff_photog = ""
        eff_copy = ""
        eff_write_ser = "Off"
    else:
        _ = camera_settings_reset_applied  # Reset leaves ALL 5 items intact!
        eff_write_copy = write_copyright_info
        eff_photog = photographer_name
        eff_copy = copyright_name
        eff_write_ser = write_serial_number

    # Tier-0 Slot 1 EROFS=30 firewall for capture/record OR CAMSET*.DAT export on Slot 1
    if (capture_or_record_triggered and recording_slot in ("Slot 1", "Simult. Recording")) or (
        camset_export_requested and camset_target_slot == "Slot 1"
    ):
        return CopyrightSerialCamsetIsolationResult(
            admitted=False,
            errno_code=EROFS_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            effective_write_copyright_info=eff_write_copy,
            effective_photographer_name=eff_photog,
            effective_copyright_name=eff_copy,
            effective_write_serial_number=eff_write_ser,
            all_5_items_reset_immune=True,
            write_serial_active_in_still=True,
            write_serial_active_in_movie=(float(fw_version) >= 2.0),
            still_exif_copyright_written=False,
            movie_exif_copyright_written=False,
            copyright_excluded_from_camset=True,
            write_serial_toggle_in_camset=True,
            camset_contains_copyright_pii=False,
            camset_contains_body_serial_string=False,
            photographer_copyright_pii_leaked_bytes=0,
            body_serial_number_leaked_bytes=0,
            slot1_erofs_triggered=True,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_has_consumer_copyright_menu=False,
            fx6_lens_serial_slots=0,
            reason="EROFS: Tier-0 Slot-1 read-only vault blocked capture/CAMSET export write",
        )

    serial_still_movie = float(fw_version) >= 2.0
    still_exif_written = (
        capture_or_record_triggered
        and shoot_mode == SHOOT_MODE_STILL
        and eff_write_copy == "On"
    )
    return CopyrightSerialCamsetIsolationResult(
        admitted=True,
        errno_code=0,
        body_profile=BODY_MODEL_FX3,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        effective_write_copyright_info=eff_write_copy,
        effective_photographer_name=eff_photog,
        effective_copyright_name=eff_copy,
        effective_write_serial_number=eff_write_ser,
        all_5_items_reset_immune=True,
        write_serial_active_in_still=True,
        write_serial_active_in_movie=serial_still_movie,
        still_exif_copyright_written=still_exif_written,
        movie_exif_copyright_written=False,
        copyright_excluded_from_camset=True,
        write_serial_toggle_in_camset=True,
        camset_contains_copyright_pii=False,
        camset_contains_body_serial_string=False,
        photographer_copyright_pii_leaked_bytes=0,
        body_serial_number_leaked_bytes=0,
        slot1_erofs_triggered=False,
        slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
        fx6_has_consumer_copyright_menu=False,
        fx6_lens_serial_slots=0,
        reason=(
            f"ADMITTED: WriteCopyright={eff_write_copy} (Reset-immune, CAMSET-excluded), "
            f"WriteSerial={eff_write_ser} (Still+Movie={serial_still_movie}, toggle_in_CAMSET=True)"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 74D: Power Setting Option (9-Cond / Dormant Monitor) & NTSC/PAL
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PowerSaveMonitorNtscPalResult:
    admitted: bool
    errno_code: int
    body_profile: str
    fw_version: str
    effective_power_save_start_time: str
    power_save_bypass_reasons: Tuple[str, ...]
    auto_sleep_armed: bool
    effective_auto_pwr_off_temp: str
    tripod_only_warning_emitted: bool
    power_save_by_monitor_exposed: bool
    power_setting_resettable: bool
    effective_tv_system: str
    ntsc_pal_resettable: bool
    auto_reboot_triggered: bool
    boot_banner_text: str
    fps_2398p_allowed: bool
    effective_tc_format: str
    cross_system_playback_blocked: bool
    legacy_format_prompt_trapped: bool
    slot1_erofs_triggered: bool
    slot1_data_sector_writes: int
    fx6_project_frequency: str
    reason: str


def simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    power_save_start_time: str = "5 Min",
    auto_pwr_off_temp: str = "Standard",
    power_save_by_monitor_requested: bool = False,
    usb_power_supplied: bool = False,
    slideshow_playing: bool = False,
    ftp_transfer_active: bool = False,
    recording_movies: bool = False,
    connected_to_pc: bool = False,
    connected_to_tv_hdmi: bool = False,
    ir_remote_ctrl_on: bool = False,
    bluetooth_rmt_ctrl_on: bool = False,
    streaming_or_creators_cloud_upload: bool = False,
    tv_system: str = "NTSC",
    previous_tv_system: str = "NTSC",
    factory_default_tv_system: str = "NTSC",
    requested_fps: float = 59.94,
    requested_tc_format: str = "NDF",
    playback_clip_tv_system: Optional[str] = None,
    slot1_format_or_erase_requested: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_project_frequency: str = "59.94",
    fx6_previous_frequency: str = "59.94",
) -> PowerSaveMonitorNtscPalResult:
    """Simulate Sub-Model 74D: Power Setting Option (9-cond & Dormant Monitor) + NTSC/PAL Firewall."""
    if body_profile not in VALID_BODY_MODELS:
        raise Stage74Phase339Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage74Phase339Error(f"Unsupported fw_version: {fw_version!r}")
    if power_save_start_time not in ALL_POWER_SAVE_PROBES:
        raise Stage74Phase339Error(f"Unsupported power_save_start_time: {power_save_start_time!r}")
    if auto_pwr_off_temp not in VALID_AUTO_PWR_OFF_TEMP_MODES:
        raise Stage74Phase339Error(f"Unsupported auto_pwr_off_temp: {auto_pwr_off_temp!r}")
    if tv_system not in VALID_TV_SYSTEMS:
        raise Stage74Phase339Error(f"Unsupported tv_system: {tv_system!r}")
    if previous_tv_system not in VALID_TV_SYSTEMS:
        raise Stage74Phase339Error(f"Unsupported previous_tv_system: {previous_tv_system!r}")
    if factory_default_tv_system not in VALID_TV_SYSTEMS:
        raise Stage74Phase339Error(f"Unsupported factory_default_tv_system: {factory_default_tv_system!r}")
    if requested_tc_format not in VALID_TC_FORMATS:
        raise Stage74Phase339Error(f"Unsupported requested_tc_format: {requested_tc_format!r}")
    if playback_clip_tv_system is not None and playback_clip_tv_system not in VALID_TV_SYSTEMS:
        raise Stage74Phase339Error(f"Unsupported playback_clip_tv_system: {playback_clip_tv_system!r}")
    if fx6_project_frequency not in FX6_FREQUENCY_OPTIONS:
        raise Stage74Phase339Error(f"Unsupported fx6_project_frequency: {fx6_project_frequency!r}")
    if fx6_previous_frequency not in FX6_FREQUENCY_OPTIONS:
        raise Stage74Phase339Error(f"Unsupported fx6_previous_frequency: {fx6_previous_frequency!r}")

    # FX6 architecture (`Project > Rec Format > Frequency`; no consumer Power Save/Monitor menus)
    if body_profile == BODY_MODEL_FX6:
        if power_save_by_monitor_requested:
            return PowerSaveMonitorNtscPalResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX6,
                fw_version=fw_version,
                effective_power_save_start_time="N/A",
                power_save_bypass_reasons=(),
                auto_sleep_armed=False,
                effective_auto_pwr_off_temp="N/A",
                tripod_only_warning_emitted=False,
                power_save_by_monitor_exposed=False,
                power_setting_resettable=False,
                effective_tv_system="N/A",
                ntsc_pal_resettable=False,
                auto_reboot_triggered=False,
                boot_banner_text="",
                fps_2398p_allowed=True,
                effective_tc_format=requested_tc_format,
                cross_system_playback_blocked=False,
                legacy_format_prompt_trapped=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                fx6_project_frequency=fx6_project_frequency,
                reason="EOPNOTSUPP: ILME-FX6 lacks consumer [Power Save by Monitor]",
            )
        reboot_req = fx6_project_frequency != fx6_previous_frequency
        return PowerSaveMonitorNtscPalResult(
            admitted=True,
            errno_code=0,
            body_profile=BODY_MODEL_FX6,
            fw_version=fw_version,
            effective_power_save_start_time="N/A",
            power_save_bypass_reasons=(),
            auto_sleep_armed=False,
            effective_auto_pwr_off_temp="N/A",
            tripod_only_warning_emitted=False,
            power_save_by_monitor_exposed=False,
            power_setting_resettable=False,
            effective_tv_system="50Hz" if fx6_project_frequency in ("50", "25") else "59.94Hz",
            ntsc_pal_resettable=False,
            auto_reboot_triggered=reboot_req,
            boot_banner_text="",
            fps_2398p_allowed=(fx6_project_frequency == "23.98"),
            effective_tc_format="NDF" if fx6_project_frequency in ("50", "25", "24", "23.98") else requested_tc_format,
            cross_system_playback_blocked=False,
            legacy_format_prompt_trapped=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_project_frequency=fx6_project_frequency,
            reason=f"ADMITTED: ILME-FX6 Project > Rec Format > Frequency={fx6_project_frequency} (reboot={reboot_req}, no consumer format trap)",
        )

    # Dormant [Power Save by Monitor] on ILME-FX3 Ver. 7.02 (0 EVF sensor, always EOPNOTSUPP)
    if power_save_by_monitor_requested:
        return PowerSaveMonitorNtscPalResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            effective_power_save_start_time=power_save_start_time,
            power_save_bypass_reasons=(),
            auto_sleep_armed=False,
            effective_auto_pwr_off_temp=auto_pwr_off_temp,
            tripod_only_warning_emitted=False,
            power_save_by_monitor_exposed=False,
            power_setting_resettable=False,
            effective_tv_system=tv_system,
            ntsc_pal_resettable=False,
            auto_reboot_triggered=False,
            boot_banner_text="",
            fps_2398p_allowed=(tv_system == "NTSC"),
            effective_tc_format=requested_tc_format,
            cross_system_playback_blocked=False,
            legacy_format_prompt_trapped=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_project_frequency="N/A",
            reason="EOPNOTSUPP: [Power Save by Monitor] (BKID_APP_setting_monitor_power_linkage) is 100% dormant on FX3 (no EVF sensor)",
        )

    # Dormant Power Save Start Time steps (`20 Sec`, `30 Sec`, `60 Min`, `240 Min`, `No Limit`)
    if power_save_start_time in DORMANT_POWER_SAVE_STEPS:
        return PowerSaveMonitorNtscPalResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            effective_power_save_start_time="5 Min",
            power_save_bypass_reasons=(),
            auto_sleep_armed=False,
            effective_auto_pwr_off_temp=auto_pwr_off_temp,
            tripod_only_warning_emitted=False,
            power_save_by_monitor_exposed=False,
            power_setting_resettable=False,
            effective_tv_system=tv_system,
            ntsc_pal_resettable=False,
            auto_reboot_triggered=False,
            boot_banner_text="",
            fps_2398p_allowed=(tv_system == "NTSC"),
            effective_tc_format=requested_tc_format,
            cross_system_playback_blocked=False,
            legacy_format_prompt_trapped=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_project_frequency="N/A",
            reason=f"EOPNOTSUPP: Power Save step {power_save_start_time!r} is dormant on ILME-FX3 Ver. 7.02",
        )

    # Reset immunity (`Setup` items survive Camera Settings Reset; only Initialize restores defaults)
    if initialize_applied:
        eff_ps = "5 Min"
        eff_temp = "Standard"
        eff_tv = factory_default_tv_system
    else:
        _ = camera_settings_reset_applied
        eff_ps = power_save_start_time
        eff_temp = auto_pwr_off_temp
        eff_tv = tv_system

    # 9 official auto-bypass conditions
    bypass_flags = (
        ("usb_power_supplied", usb_power_supplied),
        ("slideshow_playing", slideshow_playing),
        ("ftp_transfer_active", ftp_transfer_active),
        ("recording_movies", recording_movies),
        ("connected_to_pc", connected_to_pc),
        ("connected_to_tv_hdmi", connected_to_tv_hdmi),
        ("ir_remote_ctrl_on", ir_remote_ctrl_on),
        ("bluetooth_rmt_ctrl_on", bluetooth_rmt_ctrl_on),
        ("streaming_or_creators_cloud_upload", streaming_or_creators_cloud_upload),
    )
    active_bypasses = tuple(name for name, flag in bypass_flags if flag)
    sleep_armed = (eff_ps != "Off") and (len(active_bypasses) == 0)

    # Auto Power OFF Temp = High tripod-only advisory
    tripod_warn = eff_temp == "High"

    # NTSC/PAL Selector behavior
    reboot_triggered = eff_tv != previous_tv_system
    banner = (
        f"Running on {eff_tv}." if eff_tv != factory_default_tv_system else ""
    )

    # Tier-0 Slot-1 EROFS=30 firewall against SD-Erase/TRIM Format traps (`base 0xe595`/`0xe9f6`)
    if slot1_format_or_erase_requested:
        return PowerSaveMonitorNtscPalResult(
            admitted=False,
            errno_code=EROFS_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            effective_power_save_start_time=eff_ps,
            power_save_bypass_reasons=active_bypasses,
            auto_sleep_armed=sleep_armed,
            effective_auto_pwr_off_temp=eff_temp,
            tripod_only_warning_emitted=tripod_warn,
            power_save_by_monitor_exposed=False,
            power_setting_resettable=False,
            effective_tv_system=eff_tv,
            ntsc_pal_resettable=False,
            auto_reboot_triggered=reboot_triggered,
            boot_banner_text=banner,
            fps_2398p_allowed=(eff_tv == "NTSC"),
            effective_tc_format="NDF" if eff_tv == "PAL" else requested_tc_format,
            cross_system_playback_blocked=(
                playback_clip_tv_system is not None and playback_clip_tv_system != eff_tv
            ),
            legacy_format_prompt_trapped=True,
            slot1_erofs_triggered=True,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_project_frequency="N/A",
            reason="EROFS: Tier-0 Slot-1 firewall blocked NTSC/PAL Format? / SD-Erase / TRIM mutation",
        )

    # PAL gates: disables 23.98p and forces Time Code Format = NDF (disables DF)
    if eff_tv == "PAL" and (abs(requested_fps - 23.98) < 0.05 or requested_tc_format == "DF"):
        return PowerSaveMonitorNtscPalResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            effective_power_save_start_time=eff_ps,
            power_save_bypass_reasons=active_bypasses,
            auto_sleep_armed=sleep_armed,
            effective_auto_pwr_off_temp=eff_temp,
            tripod_only_warning_emitted=tripod_warn,
            power_save_by_monitor_exposed=False,
            power_setting_resettable=False,
            effective_tv_system="PAL",
            ntsc_pal_resettable=False,
            auto_reboot_triggered=reboot_triggered,
            boot_banner_text=banner,
            fps_2398p_allowed=False,
            effective_tc_format="NDF",
            cross_system_playback_blocked=(
                playback_clip_tv_system is not None and playback_clip_tv_system != "PAL"
            ),
            legacy_format_prompt_trapped=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_project_frequency="N/A",
            reason="EOPNOTSUPP: PAL mode disables 23.98p and Time Code DF (locks NDF)",
        )

    cross_pb_blocked = (
        playback_clip_tv_system is not None and playback_clip_tv_system != eff_tv
    )
    if cross_pb_blocked:
        return PowerSaveMonitorNtscPalResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            effective_power_save_start_time=eff_ps,
            power_save_bypass_reasons=active_bypasses,
            auto_sleep_armed=sleep_armed,
            effective_auto_pwr_off_temp=eff_temp,
            tripod_only_warning_emitted=tripod_warn,
            power_save_by_monitor_exposed=False,
            power_setting_resettable=False,
            effective_tv_system=eff_tv,
            ntsc_pal_resettable=False,
            auto_reboot_triggered=reboot_triggered,
            boot_banner_text=banner,
            fps_2398p_allowed=(eff_tv == "NTSC"),
            effective_tc_format="NDF" if eff_tv == "PAL" else requested_tc_format,
            cross_system_playback_blocked=True,
            legacy_format_prompt_trapped=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            fx6_project_frequency="N/A",
            reason=(
                f"EOPNOTSUPP: _g UXC cross-system playback blocked "
                f"(recorded={playback_clip_tv_system}, current={eff_tv})"
            ),
        )

    return PowerSaveMonitorNtscPalResult(
        admitted=True,
        errno_code=0,
        body_profile=BODY_MODEL_FX3,
        fw_version=fw_version,
        effective_power_save_start_time=eff_ps,
        power_save_bypass_reasons=active_bypasses,
        auto_sleep_armed=sleep_armed,
        effective_auto_pwr_off_temp=eff_temp,
        tripod_only_warning_emitted=tripod_warn,
        power_save_by_monitor_exposed=False,
        power_setting_resettable=False,
        effective_tv_system=eff_tv,
        ntsc_pal_resettable=False,
        auto_reboot_triggered=reboot_triggered,
        boot_banner_text=banner,
        fps_2398p_allowed=(eff_tv == "NTSC"),
        effective_tc_format="NDF" if eff_tv == "PAL" else requested_tc_format,
        cross_system_playback_blocked=False,
        legacy_format_prompt_trapped=False,
        slot1_erofs_triggered=False,
        slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
        fx6_project_frequency="N/A",
        reason=(
            f"ADMITTED: PowerSave={eff_ps} (sleep_armed={sleep_armed}), Temp={eff_temp}, "
            f"TV={eff_tv} (banner={banner!r})"
        ),
    )


# ---------------------------------------------------------------------------
# Stage 74 Milestone Probe & Unified Phase 339 Runner
# ---------------------------------------------------------------------------


def _build_stage74_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_74th_stage_milestone": IS_74TH_STAGE_MILESTONE,
        "wave": "Wave-64",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 339 Stage 74 (74/74 Milestone!) Wave-64 HIL co-emulation."""
    donor_audit = inspect_phase339_donors(force_clean_room=force_clean_room, env=env)

    # Sub-Model 74A probes
    p74a_movie_ok = simulate_breathing_comp_lockouts_and_catalyst_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        fps=59.94,
        breathing_comp="On",
        distortion_comp="Auto",
        lens_id="SEL2470GM2",
    )
    p74a_sq_below100_ok = simulate_breathing_comp_lockouts_and_catalyst_hil(
        shoot_mode=SHOOT_MODE_SQ,
        fps=60.0,
        breathing_comp="On",
        lens_id="SEL35F14GM",
    )
    p74a_reset_ok = simulate_breathing_comp_lockouts_and_catalyst_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        fps=23.98,
        breathing_comp="On",
        distortion_comp="Off",
        camera_settings_reset_applied=True,
    )
    p74a_catalyst_prepare_ok = simulate_breathing_comp_lockouts_and_catalyst_hil(
        breathing_comp="Off",
        distortion_comp="Auto",
        catalyst_client="Catalyst Prepare",
    )
    p74a_blocks = [
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            shoot_mode=SHOOT_MODE_STILL, breathing_comp="On"
        ),
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            shoot_mode=SHOOT_MODE_MOVIE, fps=119.88, breathing_comp="On"
        ),
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            shoot_mode=SHOOT_MODE_SQ, fps=100.0, breathing_comp="On"
        ),
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            shoot_mode=SHOOT_MODE_MOVIE, fps=23.98, breathing_comp="On", hdmi_raw_output="On"
        ),
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="On", teleconverter="SEL14TC"
        ),
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="On", lens_id="SEL100F28GM", sel100_macro_range_057_100=True
        ),
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="Off", distortion_comp="Auto", catalyst_client="Catalyst Browse"
        ),
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="Off", distortion_comp="Off", catalyst_client="Catalyst Prepare"
        ),
    ]
    p74a_fx6 = [
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            shoot_mode=SHOOT_MODE_MOVIE,
            breathing_comp="Auto",
            distortion_comp="Auto",
        ),
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            shoot_mode=SHOOT_MODE_SQ,
            fps=48.0,
            breathing_comp="Auto",
        ),
        simulate_breathing_comp_lockouts_and_catalyst_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            breathing_comp="Auto",
            fx6_codec="RAW(HDMI)",
        ),
    ]
    p74a_ok = (
        p74a_movie_ok.admitted
        and p74a_movie_ok.effective_breathing_comp == "On"
        and p74a_movie_ok.electronic_crop_active
        and p74a_sq_below100_ok.admitted
        and p74a_reset_ok.admitted
        and p74a_reset_ok.effective_breathing_comp == "Off"
        and p74a_reset_ok.breathing_resettable_via_camera_settings_reset
        and (not p74a_reset_ok.sibling_lens_comp_resettable)
        and p74a_reset_ok.effective_distortion_comp == "Off"
        and p74a_catalyst_prepare_ok.admitted
        and p74a_catalyst_prepare_ok.catalyst_post_comp_supported
        and all(not r.admitted for r in p74a_blocks)
        and p74a_fx6[0].admitted
        and (not p74a_fx6[1].admitted)
        and p74a_fx6[1].errno_code == EOPNOTSUPP_ERRNO
        and (not p74a_fx6[2].admitted)
        and p74a_fx6[2].errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 74B probes
    p74b_rollover_ok = simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
        card_type_slot2="CFexpress Type A",
        recording_slot="Slot 2",
        file_name_format="Cam ID + Reel#",
        camera_id="B",
        previous_camera_id="B",
        reel_number=7,
        camera_position="C",
        next_clip_number=1000,
        camera_settings_reset_applied=True,
    )
    p74b_camid_reset_reel_ok = simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
        recording_slot="Slot 2",
        file_name_format="Cam ID + Reel#",
        camera_id="B",
        previous_camera_id="A",
        reel_number=42,
    )
    p74b_filenum_reset_keeps_reel_ok = simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
        recording_slot="Slot 2",
        file_number_mode="Reset",
        file_name_format="Cam ID + Reel#",
        camera_id="A",
        previous_camera_id="A",
        reel_number=42,
    )
    p74b_date_title_37_ok = simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
        recording_slot="Slot 2",
        file_name_format="Date + Title",
        title="A" * 37,
        yyyymmdd="20261117",
    )
    p74b_sdhc_std_ok = simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
        card_type_slot2="SDHC",
        recording_slot="Slot 2",
        file_name_format="Standard",
    )
    p74b_blocks = [
        simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            card_type_slot2="SDHC",
            recording_slot="Slot 2",
            file_name_format="Cam ID + Reel#",
        ),
        simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            card_type_slot1="SDHC",
            card_type_slot2="SDXC",
            recording_slot="Simult. Recording",
        ),
        simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            recording_slot="Slot 2",
            file_name_format="Title",
            title="A" * 38,
        ),
        simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            recording_slot="Slot 1",
            file_name_format="Cam ID + Reel#",
            rec_triggered=True,
        ),
    ]
    p74b_fx6 = simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        card_type_slot1="CFexpress Type A",
        recording_slot="Slot 1",
        file_name_format="Title",
        fx6_title_prefix="123_",
    )
    p74b_ok = (
        p74b_rollover_ok.admitted
        and p74b_rollover_ok.menu_camera_position_preserved == "C"
        and p74b_rollover_ok.emitted_filename_position_char == "D"
        and p74b_rollover_ok.effective_clip_number == 1
        and p74b_rollover_ok.emitted_date_digits == 6
        and (not p74b_rollover_ok.file_settings_resettable)
        and p74b_camid_reset_reel_ok.effective_reel_number == 1
        and p74b_filenum_reset_keeps_reel_ok.effective_reel_number == 42
        and p74b_date_title_37_ok.admitted
        and p74b_date_title_37_ok.title_char_len == 37
        and p74b_date_title_37_ok.emitted_date_digits == 8
        and p74b_sdhc_std_ok.sdhc_4gb_split_active
        and p74b_sdhc_std_ok.split_chunk_limit_gb == 4
        and (not p74b_blocks[0].admitted)
        and p74b_blocks[0].errno_code == EOPNOTSUPP_ERRNO
        and (not p74b_blocks[1].admitted)
        and p74b_blocks[1].errno_code == EINVAL_ERRNO
        and (not p74b_blocks[2].admitted)
        and p74b_blocks[2].errno_code == EINVAL_ERRNO
        and (not p74b_blocks[3].admitted)
        and p74b_blocks[3].errno_code == EROFS_ERRNO
        and p74b_blocks[3].slot1_erofs_triggered
        and p74b_blocks[3].slot1_data_sector_writes == 0
        and p74b_fx6.admitted
        and p74b_fx6.emitted_clip_path == "/XDROOT/Clip/123_0001.MXF"
        and p74b_fx6.fx6_card_inherits_camid_reel
    )

    # Sub-Model 74C probes
    p74c_reset_survives_ok = simulate_copyright_46ch_serial_camset_isolation_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        write_copyright_info="On",
        photographer_name="P" * 46,
        copyright_name="C" * 46,
        write_serial_number="On",
        recording_slot="Slot 2",
        camera_settings_reset_applied=True,
    )
    p74c_camset_slot2_ok = simulate_copyright_46ch_serial_camset_isolation_hil(
        write_copyright_info="On",
        photographer_name="JaneDoe",
        copyright_name="ACME",
        write_serial_number="On",
        camset_export_requested=True,
        camset_target_slot="Slot 2",
    )
    p74c_blocks = [
        simulate_copyright_46ch_serial_camset_isolation_hil(
            photographer_name="X" * 47,
        ),
        simulate_copyright_46ch_serial_camset_isolation_hil(
            recording_slot="Slot 1",
            capture_or_record_triggered=True,
        ),
        simulate_copyright_46ch_serial_camset_isolation_hil(
            camset_export_requested=True,
            camset_target_slot="Slot 1",
        ),
    ]
    p74c_fx6 = simulate_copyright_46ch_serial_camset_isolation_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
    )
    p74c_ok = (
        p74c_reset_survives_ok.admitted
        and p74c_reset_survives_ok.all_5_items_reset_immune
        and p74c_reset_survives_ok.effective_write_copyright_info == "On"
        and len(p74c_reset_survives_ok.effective_photographer_name) == 46
        and len(p74c_reset_survives_ok.effective_copyright_name) == 46
        and p74c_reset_survives_ok.effective_write_serial_number == "On"
        and p74c_reset_survives_ok.write_serial_active_in_still
        and p74c_reset_survives_ok.write_serial_active_in_movie
        and p74c_camset_slot2_ok.admitted
        and p74c_camset_slot2_ok.copyright_excluded_from_camset
        and p74c_camset_slot2_ok.write_serial_toggle_in_camset
        and (not p74c_camset_slot2_ok.camset_contains_copyright_pii)
        and (not p74c_camset_slot2_ok.camset_contains_body_serial_string)
        and (not p74c_blocks[0].admitted)
        and p74c_blocks[0].errno_code == EINVAL_ERRNO
        and (not p74c_blocks[1].admitted)
        and p74c_blocks[1].errno_code == EROFS_ERRNO
        and (not p74c_blocks[2].admitted)
        and p74c_blocks[2].errno_code == EROFS_ERRNO
        and p74c_fx6.admitted
        and (not p74c_fx6.fx6_has_consumer_copyright_menu)
        and p74c_fx6.fx6_lens_serial_slots == 6
    )

    # Sub-Model 74D probes
    p74d_9cond_bypass_ok = simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
        power_save_start_time="10 Sec",
        auto_pwr_off_temp="High",
        connected_to_tv_hdmi=True,
        bluetooth_rmt_ctrl_on=True,
        tv_system="PAL",
        previous_tv_system="NTSC",
        factory_default_tv_system="NTSC",
        requested_fps=50.0,
        requested_tc_format="NDF",
        camera_settings_reset_applied=True,
    )
    p74d_offline_armed_ok = simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
        power_save_start_time="5 Min",
    )
    p74d_blocks = [
        simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            power_save_by_monitor_requested=True,
        ),
        simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            power_save_start_time="20 Sec",
        ),
        simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="PAL",
            requested_fps=23.98,
        ),
        simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="PAL",
            requested_tc_format="DF",
        ),
        simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="PAL",
            playback_clip_tv_system="NTSC",
        ),
        simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="PAL",
            slot1_format_or_erase_requested=True,
        ),
    ]
    p74d_fx6 = simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        fx6_project_frequency="50",
        fx6_previous_frequency="59.94",
    )
    p74d_ok = (
        p74d_9cond_bypass_ok.admitted
        and (not p74d_9cond_bypass_ok.auto_sleep_armed)
        and p74d_9cond_bypass_ok.effective_power_save_start_time == "10 Sec"
        and p74d_9cond_bypass_ok.effective_auto_pwr_off_temp == "High"
        and p74d_9cond_bypass_ok.tripod_only_warning_emitted
        and p74d_9cond_bypass_ok.auto_reboot_triggered
        and p74d_9cond_bypass_ok.boot_banner_text == "Running on PAL."
        and (not p74d_9cond_bypass_ok.power_setting_resettable)
        and (not p74d_9cond_bypass_ok.ntsc_pal_resettable)
        and p74d_offline_armed_ok.auto_sleep_armed
        and all(not r.admitted for r in p74d_blocks)
        and (not p74d_blocks[0].power_save_by_monitor_exposed)
        and p74d_blocks[0].errno_code == EOPNOTSUPP_ERRNO
        and p74d_blocks[1].errno_code == EOPNOTSUPP_ERRNO
        and p74d_blocks[2].errno_code == EOPNOTSUPP_ERRNO
        and p74d_blocks[3].errno_code == EOPNOTSUPP_ERRNO
        and p74d_blocks[4].cross_system_playback_blocked
        and p74d_blocks[5].errno_code == EROFS_ERRNO
        and p74d_blocks[5].slot1_erofs_triggered
        and p74d_blocks[5].slot1_data_sector_writes == 0
        and p74d_fx6.admitted
        and p74d_fx6.auto_reboot_triggered
        and (not p74d_fx6.legacy_format_prompt_trapped)
    )

    milestone_probe = _build_stage74_milestone_probe()

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
        "emmc_writes_authorized": EMMC_WRITES_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
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
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "rf_packets_transmitted": RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": RF_NVS_MUTATION_BYTES,
        # 74A redlines
        "breathing_comp_hfr_threshold_fps": BREATHING_COMP_HFR_THRESHOLD_FPS,
        "breathing_comp_120p_raw_sq_bypass_events": BREATHING_COMP_120P_RAW_SQ_BYPASS_EVENTS,
        "catalyst_browse_breathing_supported": CATALYST_BROWSE_BREATHING_SUPPORTED,
        "breathing_comp_reset_immunity_drift_events": BREATHING_COMP_RESET_IMMUNITY_DRIFT_EVENTS,
        "fx6_all_sq_breathing_leak_events": FX6_ALL_SQ_BREATHING_LEAK_EVENTS,
        # 74B redlines
        "movie_file_title_max_chars": MOVIE_FILE_TITLE_MAX_CHARS,
        "sdhc_forced_split_gb": SDHC_FORCED_SPLIT_GB,
        "sdhc_nonstandard_format_bypass_events": SDHC_NONSTANDARD_FORMAT_BYPASS_EVENTS,
        "sdhc_exfat_simult_bypass_events": SDHC_EXFAT_SIMULT_BYPASS_EVENTS,
        "camid_pos_rollover_menu_mutation_events": CAMID_POS_ROLLOVER_MENU_MUTATION_EVENTS,
        "slot1_file_settings_erofs_bypass_events": SLOT1_FILE_SETTINGS_EROFS_BYPASS_EVENTS,
        "fx6_clip_title_prefix_min_chars": FX6_CLIP_TITLE_PREFIX_MIN_CHARS,
        "fx6_clip_title_prefix_max_chars": FX6_CLIP_TITLE_PREFIX_MAX_CHARS,
        # 74C redlines
        "copyright_max_chars": COPYRIGHT_MAX_CHARS,
        "copyright_reset_wipe_errata_events": COPYRIGHT_RESET_WIPE_ERRATA_EVENTS,
        "write_serial_number_reset_wipe_events": WRITE_SERIAL_NUMBER_RESET_WIPE_EVENTS,
        "camset_copyright_pii_leak_events": CAMSET_COPYRIGHT_PII_LEAK_EVENTS,
        "photographer_copyright_pii_leaked_bytes": PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES,
        "body_serial_number_leaked_bytes": BODY_SERIAL_NUMBER_LEAKED_BYTES,
        # 74D redlines
        "power_save_active_steps_count": POWER_SAVE_ACTIVE_STEPS_COUNT,
        "power_save_bypass_conditions_count": POWER_SAVE_BYPASS_CONDITIONS_COUNT,
        "dormant_power_save_by_monitor_exposed_events": DORMANT_POWER_SAVE_BY_MONITOR_EXPOSED_EVENTS,
        "dormant_power_save_steps_exposed_events": DORMANT_POWER_SAVE_STEPS_EXPOSED_EVENTS,
        "ntsc_pal_slot1_format_erofs_bypass_events": NTSC_PAL_SLOT1_FORMAT_EROFS_BYPASS_EVENTS,
        "pal_2398p_or_df_bypass_events": PAL_2398P_OR_DF_BYPASS_EVENTS,
        # Runtime / Zero-Leak redlines
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    redlines_ok = (
        bool(P8_CP_MUTATION_FORBIDDEN)
        and NOP_COUNT == 0
        and GUEST_CODE_MODIFICATION_BYTES == 0
        and CP_MUTATION_BYTES == 0
        and WBI_MUTATION_BYTES == 0
        and CALIBRATION_MUTATION_BYTES == 0
        and CNFLASHA_MUTATION_BYTES == 0
        and bool(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        and NVRAM_PERSISTENT_WRITES == 0
        and BK4_PERSISTENT_NVRAM_WRITES == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not EMMC_WRITES_AUTHORIZED)
        and (not CROSS_MODEL_FLASH_AUTHORIZED)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not OVERALL_READY_FOR_HARDWARE_ATTACH)
        and (not ISP_WRITE_AUTHORIZED)
        and EMMC_NFLASHA_WRITE_COUNT == 0
        and EMMC_MUTATION_BYTES == 0
        and EMMC_CORRUPTIONS == 0
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and SPI_NOR_MUTATION_BYTES == 0
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and PASSIVE_TX_BYTES_EMITTED == 0
        and SLOT1_DATA_SECTOR_WRITES == 0
        and (not SLOT1_AVF_INFO_MUTATED)
        and RF_PACKETS_TRANSMITTED == 0
        and RF_NVS_MUTATION_BYTES == 0
        and BREATHING_COMP_HFR_THRESHOLD_FPS == 100.0
        and BREATHING_COMP_120P_RAW_SQ_BYPASS_EVENTS == 0
        and (not CATALYST_BROWSE_BREATHING_SUPPORTED)
        and BREATHING_COMP_RESET_IMMUNITY_DRIFT_EVENTS == 0
        and FX6_ALL_SQ_BREATHING_LEAK_EVENTS == 0
        and MOVIE_FILE_TITLE_MAX_CHARS == 37
        and SDHC_FORCED_SPLIT_GB == 4
        and SDHC_NONSTANDARD_FORMAT_BYPASS_EVENTS == 0
        and SDHC_EXFAT_SIMULT_BYPASS_EVENTS == 0
        and CAMID_POS_ROLLOVER_MENU_MUTATION_EVENTS == 0
        and SLOT1_FILE_SETTINGS_EROFS_BYPASS_EVENTS == 0
        and FX6_CLIP_TITLE_PREFIX_MIN_CHARS == 4
        and FX6_CLIP_TITLE_PREFIX_MAX_CHARS == 46
        and COPYRIGHT_MAX_CHARS == 46
        and COPYRIGHT_RESET_WIPE_ERRATA_EVENTS == 0
        and WRITE_SERIAL_NUMBER_RESET_WIPE_EVENTS == 0
        and CAMSET_COPYRIGHT_PII_LEAK_EVENTS == 0
        and PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES == 0
        and BODY_SERIAL_NUMBER_LEAKED_BYTES == 0
        and POWER_SAVE_ACTIVE_STEPS_COUNT == 6
        and POWER_SAVE_BYPASS_CONDITIONS_COUNT == 9
        and DORMANT_POWER_SAVE_BY_MONITOR_EXPOSED_EVENTS == 0
        and DORMANT_POWER_SAVE_STEPS_EXPOSED_EVENTS == 0
        and NTSC_PAL_SLOT1_FORMAT_EROFS_BYPASS_EVENTS == 0
        and PAL_2398P_OR_DF_BYPASS_EVENTS == 0
        and RSV_ORPHAN_COUNT == 0
        and NULL_GPIO_DEREFS == 0
        and MAILBOX_STALLS == 0
        and STOCK_CP_FAULT_COUNT == 0
        and WF12_00342260_HITS == 0
        and APPFW_CRASHES == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
    )

    all_passed = (
        bool(donor_audit.all_contracts_verified)
        and donor_audit.raw_firmware_bytes_leaked == 0
        and p74a_ok
        and p74b_ok
        and p74c_ok
        and p74d_ok
        and redlines_ok
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_339_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_74th_stage_milestone": IS_74TH_STAGE_MILESTONE,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "donor_audit": asdict(donor_audit),
        "stage74_milestone_probe": milestone_probe,
        "pillar_a_breathing_comp_catalyst_prepare_hil": {
            "passed": p74a_ok,
            "fx3_movie_5994p_on": asdict(p74a_movie_ok),
            "fx3_sq_60fps_on": asdict(p74a_sq_below100_ok),
            "fx3_reset_asymmetry": asdict(p74a_reset_ok),
            "fx3_catalyst_prepare_ok": asdict(p74a_catalyst_prepare_ok),
            "lockout_probes": [asdict(r) for r in p74a_blocks],
            "fx6_comparison": [asdict(r) for r in p74a_fx6],
        },
        "pillar_b_movie_file_settings_camid_reel_sdhc_slot1_hil": {
            "passed": p74b_ok,
            "camid_c999_to_d001_rollover": asdict(p74b_rollover_ok),
            "camid_change_resets_reel": asdict(p74b_camid_reset_reel_ok),
            "filenumber_reset_preserves_reel": asdict(p74b_filenum_reset_keeps_reel_ok),
            "date_title_37char_yyyymmdd": asdict(p74b_date_title_37_ok),
            "sdhc_4gb_standard_ok": asdict(p74b_sdhc_std_ok),
            "lockout_and_erofs_probes": [asdict(r) for r in p74b_blocks],
            "fx6_comparison": asdict(p74b_fx6),
        },
        "pillar_c_copyright_46ch_serial_camset_isolation_hil": {
            "passed": p74c_ok,
            "reset_immunity_errata_fix": asdict(p74c_reset_survives_ok),
            "camset_exclusion_slot2_ok": asdict(p74c_camset_slot2_ok),
            "lockout_and_erofs_probes": [asdict(r) for r in p74c_blocks],
            "fx6_comparison": asdict(p74c_fx6),
        },
        "pillar_d_power_setting_9cond_dormant_monitor_ntsc_pal_hil": {
            "passed": p74d_ok,
            "power_save_9cond_bypass_pal": asdict(p74d_9cond_bypass_ok),
            "offline_battery_sleep_armed": asdict(p74d_offline_armed_ok),
            "dormant_and_erofs_probes": [asdict(r) for r in p74d_blocks],
            "fx6_comparison": asdict(p74d_fx6),
        },
        "redlines": redlines,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py",
        description=(
            "Phase 339 (Stage 74 — 74/74 VM HIL Stages Milestone!) Real-Hardware "
            "ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-64 Co-Emulator: "
            "74A [Breathing Comp.] 120p/100p & RAW & S&Q Lockouts + Catalyst Prepare-Only, "
            "74B Movie [File Settings] Cam ID+Reel# / 37-Char Title / SDHC 4 GB Split, "
            "74C [Copyright Info] 46-Char & [Write Serial Number] Reset-Immune & CAMSET Exclusion, "
            "74D 9-Cond [Power Save Start Time] / 100%% Dormant [Power Save by Monitor] / "
            "[NTSC/PAL Selector] Slot-1 EROFS=30 Firewall."
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run complete Phase 339 Stage 74 Wave-64 HIL co-emulation audit",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force CLEAN_ROOM_SYNTHETIC mode without local Mac/work donor reads",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit deterministic JSON report (default output format)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit concise single-line summary instead of JSON",
    )
    args = parser.parse_args(argv)

    rep = run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 339 Stage 74 (74/74 Milestone) | mode={rep['source_mode']} | "
            f"hfr={red['breathing_comp_hfr_threshold_fps']}fps "
            f"cat_browse={int(bool(red['catalyst_browse_breathing_supported']))} "
            f"title={red['movie_file_title_max_chars']}ch "
            f"sdhc={red['sdhc_forced_split_gb']}GB "
            f"copy={red['copyright_max_chars']}ch "
            f"ps={red['power_save_active_steps_count']}/{red['power_save_bypass_conditions_count']} "
            f"mon={red['dormant_power_save_by_monitor_exposed_events']} "
            f"s1_wr={red['slot1_data_sector_writes']} leak={red['raw_firmware_bytes_leaked']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
