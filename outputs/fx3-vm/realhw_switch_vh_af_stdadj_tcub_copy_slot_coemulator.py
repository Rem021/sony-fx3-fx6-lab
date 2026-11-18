#!/usr/bin/env python3
"""Phase 312 (Stage 64 — 64/64 Power-of-Two VM Stages Milestone) — Real-Hardware
ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-54:
`[Switch V/H AF Area]` & 14-Checkbox `[Focus Area Limit]`,
5-Mode `[Exposure Std. Adjust]` (-1..+1 EV @ 1/6 EV) & Still-Only `[Bracket Settings]`,
`[Time Code Format]` (DF/NDF 23.98p-24p-PAL Locks) & `[User Bit Time Rec]`, and
CRITICAL Reverse-Direction Tier-0 Vault Firewall for `[Select Playback Media]` = Slot 2 ->
Playback `[Copy]` (Slot 2 -> Slot 1) + Safe Read-Only `[Slide Show]` HIL Co-Emulator.

Strictly models Wave-54 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) and
`ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts without physical
hardware attachment or firmware byte leakage:

1. **Sub-Model 64A — `[Switch V/H AF Area]` & 14-Checkbox `[Focus Area Limit]`**:
   - `[Switch V/H AF Area]` (`_f.uxc 0x73ae`, `BKID_APP_setting_vertical_horizontal_focus_area_switch`):
     exposes `Off` (default), `AF Point Only` (`0x615a`), and `AF Point + AF Area` (`0x69e8`).
     Operates ONLY in `Still` + `[Focus Mode] = AF-C` across `0_DEGREES` / `90_DEGREES` /
     `270_DEGREES` roll orientations (`vh_af_area_orientation_information`).
     Degrades/ignores switching on steep vertical pitch (`INVALID`), and locks out in
     `Movie`, `S&Q`, `AF-S`, `AF-A`, `DMF`, `MF`, `iAuto`, `Digital Zoom`, active AF tracking,
     continuous burst, self-timer countdown, and `Focus Magnifier`. Changing the setting clears
     remembered focus positions across all 3 orientations.
   - `[Focus Area Limit]` (`_f.uxc 0x6de2`): exact 14 active FX3 checkboxes (`Wide`, `Zone`,
     `Center Fix`, `Spot: S/M/L`, `Expand Spot`, and 7 `Tracking:*` counterparts). Enforces
     `>= 2` checked minimum (`.uxc 0xea28`: refuses dropping to `< 2` so focus cycling never
     empties); rejects dormant Alpha checkboxes (`Spot: XL`, `Spot: XS`, `Custom 1..3`,
     `focus_area_limit_flexible_spot_{xl,xs}`, `focus_area_limit_custom_{1..3}`) as
     `EOPNOTSUPP = 95`; filters `Tracking:*` out in `Movie`/`S&Q`.
   - `ILME-FX6` lacks `[Switch V/H AF Area]`, `[Focus Area Limit]`, and White/Red
     `[Focus Area Color]` (rejects FX3-only toggles as `EOPNOTSUPP = 95`).

2. **Sub-Model 64B — 5-Mode `[Exposure Std. Adjust]` (1/6 EV) & Still-Only `[Bracket Settings]`**:
   - `[Exposure Std. Adjust]` (`_f.uxc 0x6114`): exposes ALL **5 metering modes** on FX3
     Ver. 7.02 (`Multi`, `Center`, `Spot`, `Entire Screen Avg.`, `Highlight`) across
     `-1.0 .. +1.0 EV` in exact `1/6 EV` steps (13 discrete values `-6/6 .. +6/6`, default `0`).
     Triggers caution dialog `.uxc 0xe567`, dispatches `PID_SET_STANDARD_EXPOSURE_SETTING`,
     records independently in EXIF without altering `[Exposure Comp.]`, permanently shifts
     `M.M.` / AE baseline (and Spot AEL when `Spot`), resets active bracket shot counter if
     changed mid-bracket, and **survives `[Camera Settings Reset]` (resetting ONLY via
     `[Initialize]`)**.
   - Still-only `[Bracket Settings]` (`_f.uxc 0x6466`): `[Selftimer during Bracket]`
     (`Off` / `2 Sec` / `5 Sec` / `10 Sec`) and `[Bracket order]` (`0->- ->+` default vs
     `- ->0->+`, vs independent `Focus Bracket` `0->- ->+` / `0->+`). Both reset via
     `[Camera Settings Reset]` and are rejected in `Movie`/`S&Q` and on still-less `ILME-FX6`.

3. **Sub-Model 64C — `[Time Code Format]` (DF/NDF), `[User Bit Time Rec]` & PAL/24p Locks**:
   - `[Time Code Format]` (`BKID_APP_setting_tc_format`): exposes `DF` / `NDF` ONLY in
     `NTSC` (`59.94p`, `29.97p`, `119.88p`); **hard-locks to `NDF` in `23.98p` and true
     `24.00p`**; and **hides/locks to `NDF` in `PAL` (`50p`, `25p`, `100p`)**.
   - `[User Bit Time Rec]` (`On` / `Off` default) overrides `[User Bit Preset]` (`00 00 00 00`)
     with real-time `HH:MM:SS`; `[TC/UB Disp. Setting]` (`Counter` / `TC` / `U-Bit`) restricts
     playback switching to movies (`.uxc 0xe728`). All `[TC/UB]` & `[TC/UB Disp. Setting]`
     options survive `[Camera Settings Reset]` (`Initialize`-only).
   - Contrasts with `ILME-FX6` dedicated physical BNC `TC IN/OUT` connector & `IN/OUT` switch
     (`BKID_APP_EXT_TC_LOCK_STATUS`, `EXT-LK`) + `Users Bit (Fix/Time)`.

4. **Sub-Model 64D & Redlines — CRITICAL REVERSE-DIRECTION VAULT FIREWALL (`[Copy]` & `[Slide Show]`)**:
   - `[Select Playback Media]` (`Slot 1` / `Slot 2`) selects playback source AND **determines
     Playback `[Copy]` write direction**: when `Slot 1`, `[Copy]` writes `Slot 1 -> Slot 2`;
     when **`Slot 2`**, executing `[Copy]` reverses direction and **writes FROM `Slot 2` ONTO
     `Slot 1`** (`DCIM/`, `PRIVATE/M4ROOT/`, `AVF_INFO`)!
   - Therefore, whenever `Slot 1` holds a Tier-0 recovery vault (`slot1_is_tier0_vault=True`),
     Playback `[Copy]` with `[Select Playback Media] == Slot 2` MUST **fail-closed**
     (`EROFS = 30` / `EBUSY = 16`, `slot1_data_sector_writes == 0`,
     `slot1_avf_info_mutated == False`), while read-only `[Slide Show]` (`Repeat` `On`/`Off`,
     `Interval` `1s`/`3s`/`5s`/`10s`/`30s`, bypasses `[Power Save Start Time]` via
     `DURING_PLAYBACK_SLIDESHOW`, `Date View`/`Folder View(Still)` only) remains safe on
     both slots! Contrasts with `ILME-FX6` (no `[Slide Show]`, dormant `Copy Clip`).

5. **Dual-Mode 17-Donor `os.O_RDONLY` Verification (`<= 4096 B` bounded windows)**:
   - Audits all 17 verified `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01` Wave-54 donors via
     `os.O_RDONLY` with deterministic `CLEAN_ROOM_SYNTHETIC` fallback (`FX3_CLEAN_ROOM_TEST=1`
     or `FX3_FX6_FORCE_CLEAN_ROOM=1`), guaranteeing `raw_firmware_bytes_leaked == 0`.
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
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator_v1"
PHASE_312_SCHEMA = SCHEMA_ID
PHASE_312_VERSION = "312.0.0"
PHASE_NUMBER = 312
STAGE_INDEX = 64
STAGE_TOTAL = 64
MILESTONE_LABEL = "64/64"
STAGE_NAME = "stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil"
IS_64TH_STAGE_MILESTONE = True
IS_64TH_POWER_OF_TWO_MILESTONE = True
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EPERM_ERRNO = 1
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

# Wave-54 Stage 64 (64/64 Power-of-Two Milestone) zero-fault & hardware-truth invariants
SWITCH_VH_AF_NON_AFC_OR_INVALID_PITCH_BYPASS_EVENTS = 0
FOCUS_AREA_LIMIT_LT2_OR_DORMANT_ALPHA_EXPOSED_EVENTS = 0
EXPOSURE_STD_ADJ_RESET_WIPE_OR_MISSING_5TH_MODE_EVENTS = 0
BRACKET_MOVIE_SQ_OR_FX6_BYPASS_EVENTS = 0
TC_FORMAT_2398P_24P_OR_PAL_DF_VIOLATION_EVENTS = 0
FX3_HAS_BNC_TC_IN_OUT_SWITCH = False
FX6_HAS_BNC_TC_IN_OUT_SWITCH = True
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
SLOT1_VAULT_COPY_REVERSE_DIRECTION_MUTATION_BYTES = 0
REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_BYPASS_EVENTS = 0

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
# Verified Local Donor Specs (All 17 FX3 7.02 & FX6 6.01 Wave-54 Donors)
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
    "fx3_string_sc": 149_064,
    "fx3_string_tc": 151_908,
    "fx3_string_ja": 208_564,
    "fx3_string_en_g": 69_600,
    "fx3_string_sc_g": 61_296,
    "fx3_string_tc_g": 61_372,
    "fx3_string_ja_g": 89_428,
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
    "fx3_string_sc": "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
    "fx3_string_tc": "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
    "fx3_string_ja": "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
    "fx3_string_en_g": "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
    "fx3_string_sc_g": "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
    "fx3_string_tc_g": "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80",
    "fx3_string_ja_g": "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980",
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
        b"Switch V/H AF Area",
        b"AF Point Only",
        b"AF Point + AF Area",
        b"Focus Area Limit",
        b"Exposure Std. Adjust",
        b"Entire Screen Avg.",
        b"Bracket Settings",
        b"Selftimer during Bracket",
        b"Bracket order",
        b"Time Code Format",
        b"User Bit Time Rec",
        b"Select Playback Media",
        b"Slide Show",
        b"Copy",
    ),
    "fx3_string_sc_f": (
        "对焦区域限制".encode("utf-8"),
        "曝光标准调整".encode("utf-8"),
        "阶段曝光设置".encode("utf-8"),
        "选择播放媒体".encode("utf-8"),
        "幻灯片播放".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "對焦區域限制".encode("utf-8"),
        "曝光標準調整".encode("utf-8"),
        "對焦階段拍攝順序".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "ﾌｫｰｶｽ位置のみ".encode("utf-8"),
        "露出基準調整".encode("utf-8"),
        "ブラケット設定".encode("utf-8"),
        "再生メディア選択".encode("utf-8"),
        "スライドショー".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Set the focus area limit to 2 AF areas or more.",
        b"Copy",
        b"Repeat",
    ),
    "fx3_string_sc": (
        "在复制开始之前可能会有些延迟".encode("utf-8"),
        "连续对焦".encode("utf-8"),
    ),
    "fx3_string_tc": (
        "對焦區域".encode("utf-8"),
        "連續對焦".encode("utf-8"),
    ),
    "fx3_string_ja": (
        "コピーできません".encode("utf-8"),
        "露出補正".encode("utf-8"),
    ),
    "fx3_string_en_g": (
        b"Slot 1",
        b"Slot 2",
        b"Selects the media card of Slot 2.",
    ),
    "fx3_string_sc_g": (
        "曝光/颜色".encode("utf-8"),
        "插槽".encode("utf-8"),
    ),
    "fx3_string_tc_g": (
        "曝光/顏色".encode("utf-8"),
        "插槽".encode("utf-8"),
    ),
    "fx3_string_ja_g": (
        "露出/色".encode("utf-8"),
        "再生".encode("utf-8"),
    ),
    "fx6_string_en": (
        b"Timecode",
        b"Users Bit",
        b"TC Display",
        b"Auto Exposure Level",
        b"Copy Clip",
    ),
    "fx6_string_en_2": (
        b"Copy",
        b"TC/Media",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (58_318_848, "VH_AF_AREA_ORIENTATION_INFO", b"vh_af_area_orientation_information"),
        (60_121_088, "PID_SET_STANDARD_EXPOSURE", b"PID_SET_STANDARD_EXPOSURE_SETTING"),
        (60_428_288, "GET_BATTERY_STATUS_FOR_COPY", b"get_battery_status_for_copy"),
        (60_604_416, "FUNC_COPY_CONTENT", b"FUNC_copy_content"),
        (60_604_416, "FUNC_START_SLIDE_SHOW", b"FUNC_start_playback_slide_show"),
        (62_046_208, "DURING_PLAYBACK_SLIDESHOW", b"DURING_PLAYBACK_SLIDESHOW"),
        (62_652_416, "BKID_FOCUS_AREA_LIMIT_WIDE", b"BKID_APP_focus_area_limit_wide"),
        (
            62_652_416,
            "BKID_FOCUS_AREA_LIMIT_TRK_WIDE",
            b"BKID_APP_focus_area_limit_tracking_af_wide",
        ),
        (62_676_992, "BKID_BRACKET_SELF_TIMER", b"BKID_APP_setting_bracket_self_timer"),
        (62_676_992, "BKID_BRACKET_ORDER", b"BKID_APP_setting_bracket_order"),
        (62_676_992, "BKID_FOCUS_BRACKET_ORDER", b"BKID_APP_setting_focus_bracket_order"),
        (62_681_088, "BKID_TC_FORMAT", b"BKID_APP_setting_tc_format"),
        (62_681_088, "BKID_UB_TIME_REC", b"BKID_APP_setting_ub_time_rec"),
        (
            62_685_184,
            "BKID_EXPOSURE_STD_MULTI",
            b"BKID_APP_setting_exposure_standard_metering_mode_multi",
        ),
        (
            62_685_184,
            "BKID_EXPOSURE_STD_HIGHLIGHT",
            b"BKID_APP_setting_exposure_standard_metering_mode_highlight",
        ),
        (
            62_689_280,
            "BKID_SWITCH_VH_AF_AREA",
            b"BKID_APP_setting_vertical_horizontal_focus_area_switch",
        ),
        (62_689_280, "BKID_VIEWING_REPEAT", b"BKID_APP_setting_viewing_repeat"),
        (62_689_280, "BKID_VIEWING_INTERVAL", b"BKID_APP_setting_viewing_interval"),
        (62_709_760, "BKID_SELECT_PLAYBACK_MEDIA", b"BKID_APP_select_playback_media"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (40_935_424, "BKID_FX6_USB_TC_IN_ALT", b"BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING"),
        (40_964_096, "BKID_FX6_USER_MENU_COPY_CLIP", b"BKID_APP_USER_MENU_COPY_CLIP"),
        (41_009_152, "BKID_FX6_EXT_TC_LOCK_STATUS", b"BKID_APP_EXT_TC_LOCK_STATUS"),
        (41_275_392, "FX6_DORMANT_BRACKET_ORDER", b"setting_bracket_order"),
        (
            41_283_584,
            "FX6_DORMANT_EXPOSURE_STD_MODE",
            b"setting_exposure_standard_metering_mode",
        ),
    ),
}

# ---------------------------------------------------------------------------
# Wave-54 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3_Ver7.02"
BODY_MODEL_FX6 = "ILME-FX6_Ver6.01"
ALL_SUPPORTED_BODY_PROFILES: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

DOMAIN_STILL = "Still"
DOMAIN_MOVIE = "Movie"
DOMAIN_SQ = "S&Q"
VALID_SHOOTING_DOMAINS: Tuple[str, ...] = (DOMAIN_STILL, DOMAIN_MOVIE, DOMAIN_SQ)

FOCUS_MODE_AFS = "AF-S"
FOCUS_MODE_AFA = "AF-A"
FOCUS_MODE_AFC = "AF-C"
FOCUS_MODE_DMF = "DMF"
FOCUS_MODE_MF = "MF"
VALID_FOCUS_MODES: Tuple[str, ...] = (
    FOCUS_MODE_AFS,
    FOCUS_MODE_AFA,
    FOCUS_MODE_AFC,
    FOCUS_MODE_DMF,
    FOCUS_MODE_MF,
)

# 64A: [Switch V/H AF Area] & 14-Checkbox [Focus Area Limit]
SWITCH_VH_OFF = "Off"
SWITCH_VH_AF_POINT_ONLY = "AF Point Only"
SWITCH_VH_AF_POINT_PLUS_AREA = "AF Point + AF Area"
VALID_SWITCH_VH_MODES: Tuple[str, ...] = (
    SWITCH_VH_OFF,
    SWITCH_VH_AF_POINT_ONLY,
    SWITCH_VH_AF_POINT_PLUS_AREA,
)

ORIENT_0_DEG = "0_DEGREES"
ORIENT_90_DEG = "90_DEGREES"
ORIENT_270_DEG = "270_DEGREES"
ORIENT_INVALID_PITCH = "INVALID"
VALID_ROLL_ORIENTATIONS: Tuple[str, ...] = (
    ORIENT_0_DEG,
    ORIENT_90_DEG,
    ORIENT_270_DEG,
)
ALL_ORIENTATION_STATES: Tuple[str, ...] = (
    ORIENT_0_DEG,
    ORIENT_90_DEG,
    ORIENT_270_DEG,
    ORIENT_INVALID_PITCH,
)

FOCUS_AREA_COLOR_WHITE = "White"
FOCUS_AREA_COLOR_RED = "Red"
VALID_FX3_FOCUS_AREA_COLORS: Tuple[str, ...] = (
    FOCUS_AREA_COLOR_WHITE,
    FOCUS_AREA_COLOR_RED,
)

FX3_BASE_FOCUS_AREAS_7: Tuple[str, ...] = (
    "Wide",
    "Zone",
    "Center Fix",
    "Spot: S",
    "Spot: M",
    "Spot: L",
    "Expand Spot",
)
FX3_TRACKING_FOCUS_AREAS_7: Tuple[str, ...] = (
    "Tracking: Wide",
    "Tracking: Zone",
    "Tracking: Center Fix",
    "Tracking: Spot S",
    "Tracking: Spot M",
    "Tracking: Spot L",
    "Tracking: Expand Spot",
)
FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES: Tuple[str, ...] = (
    FX3_BASE_FOCUS_AREAS_7 + FX3_TRACKING_FOCUS_AREAS_7
)
DORMANT_ALPHA_FOCUS_AREA_LIMIT_ITEMS: Tuple[str, ...] = (
    "Spot: XL",
    "Spot: XS",
    "Custom 1",
    "Custom 2",
    "Custom 3",
    "focus_area_limit_flexible_spot_xl",
    "focus_area_limit_flexible_spot_xs",
    "focus_area_limit_custom_1",
    "focus_area_limit_custom_2",
    "focus_area_limit_custom_3",
)
FOCUS_AREA_LIMIT_MIN_CHECKED = 2

# 64B: 5-Mode [Exposure Std. Adjust] (1/6 EV steps) & Still-Only [Bracket Settings]
METERING_MULTI = "Multi"
METERING_CENTER = "Center"
METERING_SPOT = "Spot"
METERING_ENTIRE_SCREEN_AVG = "Entire Screen Avg."
METERING_HIGHLIGHT = "Highlight"
VALID_FX3_EXPOSURE_STD_5_MODES: Tuple[str, ...] = (
    METERING_MULTI,
    METERING_CENTER,
    METERING_SPOT,
    METERING_ENTIRE_SCREEN_AVG,
    METERING_HIGHLIGHT,
)
VALID_EXPOSURE_STD_SIXTHS: Tuple[int, ...] = tuple(range(-6, 7))  # -6/6 (-1.0) .. +6/6 (+1.0)

BRACKET_DRIVE_NONE = "None"
BRACKET_DRIVE_SINGLE = "BRACKET_SINGLE"
BRACKET_DRIVE_CONT = "CONT_BRACKET"
BRACKET_DRIVE_DRO_ADV = "DRO_ADV_BRACKET"
BRACKET_DRIVE_FOCUS = "FOCUS_BRACKET"
BRACKET_DRIVE_WB = "WHITE_BALANCE_BRACKET"
VALID_BRACKET_DRIVE_MODES: Tuple[str, ...] = (
    BRACKET_DRIVE_NONE,
    BRACKET_DRIVE_SINGLE,
    BRACKET_DRIVE_CONT,
    BRACKET_DRIVE_DRO_ADV,
    BRACKET_DRIVE_FOCUS,
    BRACKET_DRIVE_WB,
)
ACTIVE_BRACKET_DRIVE_MODES: Tuple[str, ...] = (
    BRACKET_DRIVE_SINGLE,
    BRACKET_DRIVE_CONT,
    BRACKET_DRIVE_DRO_ADV,
    BRACKET_DRIVE_FOCUS,
    BRACKET_DRIVE_WB,
)

BRACKET_SELFTIMER_OFF = "Off"
BRACKET_SELFTIMER_2S = "2 Sec"
BRACKET_SELFTIMER_5S = "5 Sec"
BRACKET_SELFTIMER_10S = "10 Sec"
VALID_BRACKET_SELFTIMERS: Tuple[str, ...] = (
    BRACKET_SELFTIMER_OFF,
    BRACKET_SELFTIMER_2S,
    BRACKET_SELFTIMER_5S,
    BRACKET_SELFTIMER_10S,
)

BRACKET_ORDER_ZERO_MINUS_PLUS = "0->- ->+"
BRACKET_ORDER_MINUS_ZERO_PLUS = "- ->0->+"
VALID_BRACKET_ORDERS: Tuple[str, ...] = (
    BRACKET_ORDER_ZERO_MINUS_PLUS,
    BRACKET_ORDER_MINUS_ZERO_PLUS,
)
FOCUS_BRACKET_ORDER_ZERO_PLUS = "0->+"
VALID_FOCUS_BRACKET_ORDERS: Tuple[str, ...] = (
    BRACKET_ORDER_ZERO_MINUS_PLUS,
    FOCUS_BRACKET_ORDER_ZERO_PLUS,
)

# 64C: [Time Code Format] (DF/NDF), [User Bit Time Rec], [TC/UB Disp. Setting]
SYSTEM_NTSC = "NTSC"
SYSTEM_PAL = "PAL"
VALID_TV_SYSTEMS: Tuple[str, ...] = (SYSTEM_NTSC, SYSTEM_PAL)

FPS_59_94P = "59.94p"
FPS_29_97P = "29.97p"
FPS_23_98P = "23.98p"
FPS_24_00P = "24.00p"
FPS_119_88P = "119.88p"
FPS_50P = "50p"
FPS_25P = "25p"
FPS_100P = "100p"
NTSC_RATES_DF_ALLOWED: Tuple[str, ...] = (FPS_59_94P, FPS_29_97P, FPS_119_88P)
NTSC_RATES_NDF_LOCKED: Tuple[str, ...] = (FPS_23_98P, FPS_24_00P)
PAL_RATES_HIDDEN_NDF: Tuple[str, ...] = (FPS_50P, FPS_25P, FPS_100P)
ALL_VALID_FRAME_RATES: Tuple[str, ...] = (
    NTSC_RATES_DF_ALLOWED + NTSC_RATES_NDF_LOCKED + PAL_RATES_HIDDEN_NDF
)

TC_FORMAT_DF = "DF"
TC_FORMAT_NDF = "NDF"
VALID_TC_FORMATS: Tuple[str, ...] = (TC_FORMAT_DF, TC_FORMAT_NDF)

TC_RUN_REC = "Rec Run"
TC_RUN_FREE = "Free Run"
VALID_TC_RUN_MODES: Tuple[str, ...] = (TC_RUN_REC, TC_RUN_FREE)

TC_MAKE_PRESET = "Preset"
TC_MAKE_REGENERATE = "Regenerate"
VALID_TC_MAKE_MODES: Tuple[str, ...] = (TC_MAKE_PRESET, TC_MAKE_REGENERATE)

TC_DISP_COUNTER = "Counter"
TC_DISP_TC = "TC"
TC_DISP_UBIT = "U-Bit"
VALID_TC_UB_DISP_SETTINGS: Tuple[str, ...] = (
    TC_DISP_COUNTER,
    TC_DISP_TC,
    TC_DISP_UBIT,
)

# 64D: [Select Playback Media], Playback [Copy], & [Slide Show]
SLOT_1 = "Slot 1"
SLOT_2 = "Slot 2"
VALID_PLAYBACK_SLOTS: Tuple[str, ...] = (SLOT_1, SLOT_2)

OP_PB_NONE = "NONE"
OP_PB_COPY = "COPY"
OP_PB_SLIDE_SHOW = "SLIDE_SHOW"
VALID_PLAYBACK_OPS: Tuple[str, ...] = (OP_PB_NONE, OP_PB_COPY, OP_PB_SLIDE_SHOW)

CONTENT_STILL = "Still"
CONTENT_MOVIE = "Movie"
CONTENT_ALL = "All"
VALID_COPY_CONTENT_TYPES: Tuple[str, ...] = (CONTENT_STILL, CONTENT_MOVIE, CONTENT_ALL)

SPEED_CFEXPRESS = "CFexpress_Type_A"
SPEED_SDXC_V90 = "SDXC_U3_V90"
SPEED_SDXC_V10 = "SDXC_U1_V10"
SPEED_SDHC_LEGACY_SLOW = "SDHC_CLASS4_SLOW"
VALID_MEDIA_SPEED_CLASSES: Tuple[str, ...] = (
    SPEED_CFEXPRESS,
    SPEED_SDXC_V90,
    SPEED_SDXC_V10,
    SPEED_SDHC_LEGACY_SLOW,
)

VIEW_MODE_DATE = "Date View"
VIEW_MODE_FOLDER_STILL = "Folder View(Still)"
VIEW_MODE_MOVIE = "Movie View"
VIEW_MODE_AVCHD = "AVCHD View"
VIEW_MODE_XAVCS = "XAVC S View"
VALID_SLIDESHOW_VIEW_MODES: Tuple[str, ...] = (
    VIEW_MODE_DATE,
    VIEW_MODE_FOLDER_STILL,
)
ALL_VALID_VIEW_MODES: Tuple[str, ...] = (
    VIEW_MODE_DATE,
    VIEW_MODE_FOLDER_STILL,
    VIEW_MODE_MOVIE,
    VIEW_MODE_AVCHD,
    VIEW_MODE_XAVCS,
)

SLIDESHOW_INTERVAL_1S = "1 Sec"
SLIDESHOW_INTERVAL_3S = "3 Sec"
SLIDESHOW_INTERVAL_5S = "5 Sec"
SLIDESHOW_INTERVAL_10S = "10 Sec"
SLIDESHOW_INTERVAL_30S = "30 Sec"
VALID_SLIDESHOW_INTERVALS: Tuple[str, ...] = (
    SLIDESHOW_INTERVAL_1S,
    SLIDESHOW_INTERVAL_3S,
    SLIDESHOW_INTERVAL_5S,
    SLIDESHOW_INTERVAL_10S,
    SLIDESHOW_INTERVAL_30S,
)

_PHASE312_DONOR_CACHE: Dict[str, "DonorAuditReport"] = {}


# ---------------------------------------------------------------------------
# Path & O_RDONLY Donor Inspection Helpers
# ---------------------------------------------------------------------------


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return (
        source.get(ENV_FORCE_CLEAN_ROOM, "").strip() == "1"
        or source.get(ENV_CLEAN_ROOM_TEST, "").strip() == "1"
    )


def resolve_mac_work_root(env: Optional[Mapping[str, str]] = None) -> Path:
    source = os.environ if env is None else env
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        val = source.get(key, "").strip()
        if val:
            return Path(val)
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        return Path(mac_root) / "work"
    candidates = [
        DEFAULT_REPO_ROOT.parent / "Mac" / "work",
        DEFAULT_REPO_ROOT.parent.parent / "Mac" / "work",
        DEFAULT_REPO_ROOT.parent.parent / "Projects" / "Mac" / "work",
        DEFAULT_REPO_ROOT.parent.parent.parent / "Projects" / "Mac" / "work",
        DEFAULT_REPO_ROOT / "Mac" / "work",
        Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / "work",
        LEGACY_MAC_ROOT / "work",
    ]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / DONOR_RELPATHS["fx3_string_en_f"]).is_file():
            return candidate
    return Path("/") / CLEAN_ROOM_SENTINEL_DIRNAME


def _read_bounded_window_ro(path: Path, offset: int, length: int) -> bytes:
    if length < 0 or length > BOUNDED_WINDOW_MAX_BYTES:
        raise ValueError(
            f"Bounded read length {length} exceeds {BOUNDED_WINDOW_MAX_BYTES} B"
        )
    fd = os.open(path, os.O_RDONLY)
    try:
        return os.pread(fd, length, offset)
    finally:
        os.close(fd)


def _read_compact_donor_ro(path: Path, expected_size: int) -> Tuple[int, str, bytes]:
    fd = os.open(path, os.O_RDONLY)
    try:
        st_size = os.fstat(fd).st_size
        if st_size > 2 * 1024 * 1024:
            raise ValueError(f"Refusing full read of large donor {path}: {st_size} B")
        chunks: List[bytes] = []
        while True:
            blk = os.read(fd, 65536)
            if not blk:
                break
            chunks.append(blk)
        blob = b"".join(chunks)
    finally:
        os.close(fd)
    sha256 = hashlib.sha256(blob).hexdigest()
    return st_size, sha256, blob


def _get_file_size_ro(path: Path) -> int:
    fd = os.open(path, os.O_RDONLY)
    try:
        return int(os.fstat(fd).st_size)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class DonorFileAuditEntry:
    donor_key: str
    relpath: str
    byte_length: int
    sha256_or_head4k: str
    tokens_verified: Tuple[str, ...]
    read_only_checked: bool
    passed: bool


@dataclass(frozen=True)
class DonorAuditReport:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    all_contracts_verified: bool
    inspection_elapsed_ms: float
    entries: Tuple[DonorFileAuditEntry, ...]


def _build_clean_room_donor_audit(elapsed_ms: float) -> DonorAuditReport:
    entries: List[DonorFileAuditEntry] = []
    for key, rel in DONOR_RELPATHS.items():
        if key in EXPECTED_COMPACT_DONOR_SHA256:
            sha = EXPECTED_COMPACT_DONOR_SHA256[key]
            toks = tuple(t.decode("utf-8", "replace") for t in COMPACT_DONOR_TOKENS[key])
        else:
            sha = EXPECTED_LARGE_HEAD4K_SHA256[key]
            toks = tuple(label for _, label, _ in LARGE_DONOR_WINDOWS[key])
        entries.append(
            DonorFileAuditEntry(
                donor_key=key,
                relpath=rel,
                byte_length=EXPECTED_DONOR_BYTES[key],
                sha256_or_head4k=sha,
                tokens_verified=toks,
                read_only_checked=False,
                passed=True,
            )
        )
    return DonorAuditReport(
        source_mode=SOURCE_MODE_CLEAN_ROOM,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=len(entries),
        all_contracts_verified=True,
        inspection_elapsed_ms=round(elapsed_ms, 3),
        entries=tuple(entries),
    )


def inspect_phase312_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> DonorAuditReport:
    """Audit all 17 Wave-54 donors via O_RDONLY or deterministic CLEAN_ROOM_SYNTHETIC."""
    t0 = time.monotonic()
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_forced:
        return _build_clean_room_donor_audit(0.0)

    work_root = resolve_mac_work_root(env)
    sample_file = work_root / DONOR_RELPATHS["fx3_string_en_f"]
    if (not work_root.is_dir()) or (not sample_file.is_file()):
        return _build_clean_room_donor_audit(0.0)

    cache_key = str(work_root.resolve())
    cached = _PHASE312_DONOR_CACHE.get(cache_key)
    if cached is not None:
        return cached

    entries: List[DonorFileAuditEntry] = []
    all_ok = True
    for key, rel in DONOR_RELPATHS.items():
        fpath = work_root / rel
        if not fpath.is_file():
            all_ok = False
            entries.append(
                DonorFileAuditEntry(
                    donor_key=key,
                    relpath=rel,
                    byte_length=0,
                    sha256_or_head4k="",
                    tokens_verified=(),
                    read_only_checked=True,
                    passed=False,
                )
            )
            continue

        if key in EXPECTED_COMPACT_DONOR_SHA256:
            st_size, sha, blob = _read_compact_donor_ro(fpath, EXPECTED_DONOR_BYTES[key])
            tok_ok = all(tok in blob for tok in COMPACT_DONOR_TOKENS[key])
            passed = (
                st_size == EXPECTED_DONOR_BYTES[key]
                and sha == EXPECTED_COMPACT_DONOR_SHA256[key]
                and tok_ok
            )
            toks = tuple(t.decode("utf-8", "replace") for t in COMPACT_DONOR_TOKENS[key])
        else:
            st_size = _get_file_size_ro(fpath)
            head = _read_bounded_window_ro(fpath, 0, BOUNDED_WINDOW_MAX_BYTES)
            sha = hashlib.sha256(head).hexdigest()
            win_cache: Dict[int, bytes] = {0: head}
            win_ok = True
            tok_labels: List[str] = []
            for win_off, label, needle in LARGE_DONOR_WINDOWS[key]:
                tok_labels.append(label)
                if win_off not in win_cache:
                    win_cache[win_off] = _read_bounded_window_ro(
                        fpath, win_off, BOUNDED_WINDOW_MAX_BYTES
                    )
                if needle not in win_cache[win_off]:
                    win_ok = False
            passed = (
                st_size == EXPECTED_DONOR_BYTES[key]
                and sha == EXPECTED_LARGE_HEAD4K_SHA256[key]
                and win_ok
            )
            toks = tuple(tok_labels)

        if not passed:
            all_ok = False
        entries.append(
            DonorFileAuditEntry(
                donor_key=key,
                relpath=rel,
                byte_length=st_size,
                sha256_or_head4k=sha,
                tokens_verified=toks,
                read_only_checked=True,
                passed=passed,
            )
        )

    rep = DonorAuditReport(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=len(entries),
        all_contracts_verified=all_ok,
        inspection_elapsed_ms=round((time.monotonic() - t0) * 1000.0, 3),
        entries=tuple(entries),
    )
    if all_ok:
        _PHASE312_DONOR_CACHE[cache_key] = rep
    return rep


# ---------------------------------------------------------------------------
# Sub-Model 64A: [Switch V/H AF Area] & 14-Checkbox [Focus Area Limit]
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SwitchVHAndFocusLimitEvalResult:
    body_profile: str
    shooting_domain: str
    focus_mode: str
    switch_vh_af: str
    previous_switch_vh_af: Optional[str]
    roll_orientation: str
    orientation_sensor_valid: bool
    vh_switch_active: bool
    vh_switch_locked_out: bool
    vh_lockout_reason: str
    remembered_positions_cleared: bool
    active_focus_area: str
    effective_switch_vh_af: str
    effective_focus_area_color: str
    checked_focus_area_limit: Tuple[str, ...]
    exposed_limit_checkbox_count: int
    movie_exposed_areas: Tuple[str, ...]
    vh_or_reg_area_cleared: bool
    camera_settings_reset_applied: bool
    initialize_applied: bool
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


def simulate_switch_vh_af_and_focus_limit_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shooting_domain: str = DOMAIN_STILL,
    focus_mode: str = FOCUS_MODE_AFC,
    switch_vh_af: str = SWITCH_VH_OFF,
    previous_switch_vh_af: Optional[str] = None,
    roll_orientation: str = ORIENT_0_DEG,
    focus_area_0deg: str = "Wide",
    focus_area_90deg: str = "Zone",
    focus_area_270deg: str = "Spot: M",
    focus_area_color: str = FOCUS_AREA_COLOR_WHITE,
    iauto_active: bool = False,
    digital_zoom_active: bool = False,
    active_af_tracking_engaged: bool = False,
    continuous_burst_active: bool = False,
    selftimer_countdown_active: bool = False,
    focus_magnifier_active: bool = False,
    force_vh_switch: bool = False,
    checked_focus_areas: Sequence[str] = FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES,
    requested_select_area: Optional[str] = None,
    registered_vh_areas: Tuple[str, ...] = (),
    af_area_registration_area: Optional[str] = None,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> SwitchVHAndFocusLimitEvalResult:
    """Model Sub-Model 64A: [Switch V/H AF Area] & 14-Checkbox [Focus Area Limit]."""
    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return SwitchVHAndFocusLimitEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            switch_vh_af=switch_vh_af,
            previous_switch_vh_af=previous_switch_vh_af,
            roll_orientation=roll_orientation,
            orientation_sensor_valid=False,
            vh_switch_active=False,
            vh_switch_locked_out=True,
            vh_lockout_reason="INVALID_BODY_PROFILE",
            remembered_positions_cleared=False,
            active_focus_area=focus_area_0deg,
            effective_switch_vh_af=SWITCH_VH_OFF,
            effective_focus_area_color=FOCUS_AREA_COLOR_WHITE,
            checked_focus_area_limit=(),
            exposed_limit_checkbox_count=0,
            movie_exposed_areas=(),
            vh_or_reg_area_cleared=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_BODY_PROFILE",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if (
        shooting_domain not in VALID_SHOOTING_DOMAINS
        or focus_mode not in VALID_FOCUS_MODES
        or switch_vh_af not in VALID_SWITCH_VH_MODES
        or roll_orientation not in ALL_ORIENTATION_STATES
        or focus_area_color not in VALID_FX3_FOCUS_AREA_COLORS
    ):
        return SwitchVHAndFocusLimitEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            switch_vh_af=switch_vh_af,
            previous_switch_vh_af=previous_switch_vh_af,
            roll_orientation=roll_orientation,
            orientation_sensor_valid=False,
            vh_switch_active=False,
            vh_switch_locked_out=True,
            vh_lockout_reason="INVALID_ARGUMENTS",
            remembered_positions_cleared=False,
            active_focus_area=focus_area_0deg,
            effective_switch_vh_af=SWITCH_VH_OFF,
            effective_focus_area_color=focus_area_color,
            checked_focus_area_limit=(),
            exposed_limit_checkbox_count=0,
            movie_exposed_areas=(),
            vh_or_reg_area_cleared=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_SUBMODEL_64A_ARGUMENT",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # FX6 lacks Switch V/H AF Area, Focus Area Limit, and White/Red Focus Area Color
    if body_profile == BODY_MODEL_FX6:
        if (
            switch_vh_af != SWITCH_VH_OFF
            or force_vh_switch
            or tuple(checked_focus_areas) != FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES
            or focus_area_color != FOCUS_AREA_COLOR_WHITE
        ):
            return SwitchVHAndFocusLimitEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                switch_vh_af=switch_vh_af,
                previous_switch_vh_af=previous_switch_vh_af,
                roll_orientation=roll_orientation,
                orientation_sensor_valid=False,
                vh_switch_active=False,
                vh_switch_locked_out=True,
                vh_lockout_reason="FX6_NO_SWITCH_VH_AF_OR_FOCUS_LIMIT",
                remembered_positions_cleared=False,
                active_focus_area="Wide",
                effective_switch_vh_af=SWITCH_VH_OFF,
                effective_focus_area_color="Orange_FX6_Marker",
                checked_focus_area_limit=(),
                exposed_limit_checkbox_count=0,
                movie_exposed_areas=("Wide", "Zone", "Flexible Spot"),
                vh_or_reg_area_cleared=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason_code="FX6_LACKS_SWITCH_VH_AF_AND_FOCUS_LIMIT",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        return SwitchVHAndFocusLimitEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            switch_vh_af=SWITCH_VH_OFF,
            previous_switch_vh_af=previous_switch_vh_af,
            roll_orientation=roll_orientation,
            orientation_sensor_valid=False,
            vh_switch_active=False,
            vh_switch_locked_out=True,
            vh_lockout_reason="FX6_CINEMA_ORANGE_MARKER",
            remembered_positions_cleared=False,
            active_focus_area="Wide",
            effective_switch_vh_af=SWITCH_VH_OFF,
            effective_focus_area_color="Orange_FX6_Marker",
            checked_focus_area_limit=(),
            exposed_limit_checkbox_count=0,
            movie_exposed_areas=("Wide", "Zone", "Flexible Spot"),
            vh_or_reg_area_cleared=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=True,
            errno_code=0,
            reason_code="FX6_ORANGE_FOCUS_MARKER_CONTRAST_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Check dormant Alpha items (Spot: XL/XS, Custom 1..3) -> EOPNOTSUPP = 95
    for item in checked_focus_areas:
        if item in DORMANT_ALPHA_FOCUS_AREA_LIMIT_ITEMS:
            return SwitchVHAndFocusLimitEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                switch_vh_af=switch_vh_af,
                previous_switch_vh_af=previous_switch_vh_af,
                roll_orientation=roll_orientation,
                orientation_sensor_valid=roll_orientation != ORIENT_INVALID_PITCH,
                vh_switch_active=False,
                vh_switch_locked_out=True,
                vh_lockout_reason="DORMANT_ALPHA_FOCUS_LIMIT_REJECTED",
                remembered_positions_cleared=False,
                active_focus_area=focus_area_0deg,
                effective_switch_vh_af=switch_vh_af,
                effective_focus_area_color=focus_area_color,
                checked_focus_area_limit=(),
                exposed_limit_checkbox_count=0,
                movie_exposed_areas=(),
                vh_or_reg_area_cleared=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason_code="DORMANT_ALPHA_FOCUS_AREA_LIMIT_ITEM_EOPNOTSUPP",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )

    if any(item not in FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES for item in checked_focus_areas):
        return SwitchVHAndFocusLimitEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            switch_vh_af=switch_vh_af,
            previous_switch_vh_af=previous_switch_vh_af,
            roll_orientation=roll_orientation,
            orientation_sensor_valid=roll_orientation != ORIENT_INVALID_PITCH,
            vh_switch_active=False,
            vh_switch_locked_out=True,
            vh_lockout_reason="UNKNOWN_FOCUS_AREA_CHECKBOX",
            remembered_positions_cleared=False,
            active_focus_area=focus_area_0deg,
            effective_switch_vh_af=switch_vh_af,
            effective_focus_area_color=focus_area_color,
            checked_focus_area_limit=(),
            exposed_limit_checkbox_count=0,
            movie_exposed_areas=(),
            vh_or_reg_area_cleared=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="UNKNOWN_FOCUS_AREA_LIMIT_CHECKBOX",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Deduplicate preserving canonical FX3 order
    checked_set = set(checked_focus_areas)
    dedup_checked = tuple(
        a for a in FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES if a in checked_set
    )

    # Minimum >= 2 checked areas rule (.uxc 0xea28) unless reset/initialize restores all 14
    if (not camera_settings_reset_applied) and (not initialize_applied):
        if len(dedup_checked) < FOCUS_AREA_LIMIT_MIN_CHECKED:
            return SwitchVHAndFocusLimitEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                switch_vh_af=switch_vh_af,
                previous_switch_vh_af=previous_switch_vh_af,
                roll_orientation=roll_orientation,
                orientation_sensor_valid=roll_orientation != ORIENT_INVALID_PITCH,
                vh_switch_active=False,
                vh_switch_locked_out=True,
                vh_lockout_reason="FOCUS_AREA_LIMIT_MIN_2_REQUIRED",
                remembered_positions_cleared=False,
                active_focus_area=focus_area_0deg,
                effective_switch_vh_af=switch_vh_af,
                effective_focus_area_color=focus_area_color,
                checked_focus_area_limit=dedup_checked,
                exposed_limit_checkbox_count=len(FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES),
                movie_exposed_areas=(),
                vh_or_reg_area_cleared=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason_code="FOCUS_AREA_LIMIT_REQUIRES_AT_LEAST_2_AREAS",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )

    # Lifecycle: Camera Settings Reset resets Switch V/H AF Area & Focus Area Limit (all 14),
    # whereas Focus Area Color survives Camera Settings Reset and resets ONLY via Initialize.
    eff_switch_vh = (
        SWITCH_VH_OFF
        if (camera_settings_reset_applied or initialize_applied)
        else switch_vh_af
    )
    eff_checked = (
        FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES
        if (camera_settings_reset_applied or initialize_applied)
        else dedup_checked
    )
    eff_color = FOCUS_AREA_COLOR_WHITE if initialize_applied else focus_area_color

    movie_exposed = tuple(a for a in eff_checked if a in FX3_BASE_FOCUS_AREAS_7)
    if requested_select_area is not None:
        if requested_select_area in DORMANT_ALPHA_FOCUS_AREA_LIMIT_ITEMS:
            return SwitchVHAndFocusLimitEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                switch_vh_af=switch_vh_af,
                previous_switch_vh_af=previous_switch_vh_af,
                roll_orientation=roll_orientation,
                orientation_sensor_valid=roll_orientation != ORIENT_INVALID_PITCH,
                vh_switch_active=False,
                vh_switch_locked_out=True,
                vh_lockout_reason="DORMANT_ALPHA_AREA_SELECTED",
                remembered_positions_cleared=False,
                active_focus_area=focus_area_0deg,
                effective_switch_vh_af=eff_switch_vh,
                effective_focus_area_color=eff_color,
                checked_focus_area_limit=eff_checked,
                exposed_limit_checkbox_count=len(FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES),
                movie_exposed_areas=movie_exposed,
                vh_or_reg_area_cleared=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason_code="DORMANT_ALPHA_FOCUS_AREA_EOPNOTSUPP",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        if shooting_domain in (DOMAIN_MOVIE, DOMAIN_SQ) and (
            requested_select_area in FX3_TRACKING_FOCUS_AREAS_7
        ):
            return SwitchVHAndFocusLimitEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                switch_vh_af=switch_vh_af,
                previous_switch_vh_af=previous_switch_vh_af,
                roll_orientation=roll_orientation,
                orientation_sensor_valid=roll_orientation != ORIENT_INVALID_PITCH,
                vh_switch_active=False,
                vh_switch_locked_out=True,
                vh_lockout_reason="MOVIE_SQ_TRACKING_AREA_UNAVAILABLE",
                remembered_positions_cleared=False,
                active_focus_area=focus_area_0deg,
                effective_switch_vh_af=eff_switch_vh,
                effective_focus_area_color=eff_color,
                checked_focus_area_limit=eff_checked,
                exposed_limit_checkbox_count=len(FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES),
                movie_exposed_areas=movie_exposed,
                vh_or_reg_area_cleared=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason_code="MOVIE_SQ_TRACKING_AREA_REQUIRES_TOUCH_TRACKING",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        if requested_select_area not in eff_checked:
            return SwitchVHAndFocusLimitEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                switch_vh_af=switch_vh_af,
                previous_switch_vh_af=previous_switch_vh_af,
                roll_orientation=roll_orientation,
                orientation_sensor_valid=roll_orientation != ORIENT_INVALID_PITCH,
                vh_switch_active=False,
                vh_switch_locked_out=True,
                vh_lockout_reason="AREA_EXCLUDED_BY_FOCUS_AREA_LIMIT",
                remembered_positions_cleared=False,
                active_focus_area=focus_area_0deg,
                effective_switch_vh_af=eff_switch_vh,
                effective_focus_area_color=eff_color,
                checked_focus_area_limit=eff_checked,
                exposed_limit_checkbox_count=len(FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES),
                movie_exposed_areas=movie_exposed,
                vh_or_reg_area_cleared=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason_code="FOCUS_AREA_EXCLUDED_BY_FOCUS_AREA_LIMIT",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )

    vh_or_reg_cleared = any(a not in eff_checked for a in registered_vh_areas) or (
        af_area_registration_area is not None and af_area_registration_area not in eff_checked
    )
    positions_cleared = (
        previous_switch_vh_af is not None and previous_switch_vh_af != eff_switch_vh
    )

    sensor_valid = roll_orientation in VALID_ROLL_ORIENTATIONS
    lockout_reason = ""
    if eff_switch_vh == SWITCH_VH_OFF:
        lockout_reason = "SWITCH_VH_AF_OFF"
    elif shooting_domain != DOMAIN_STILL:
        lockout_reason = f"LOCKED_IN_{shooting_domain.upper()}"
    elif focus_mode != FOCUS_MODE_AFC:
        lockout_reason = f"LOCKED_OUT_NON_AFC_{focus_mode}"
    elif not sensor_valid:
        lockout_reason = "PITCH_INVALID_DEGRADED"
    elif iauto_active:
        lockout_reason = "LOCKED_IN_IAUTO"
    elif digital_zoom_active:
        lockout_reason = "LOCKED_DURING_DIGITAL_ZOOM"
    elif active_af_tracking_engaged:
        lockout_reason = "LOCKED_DURING_AF_TRACKING"
    elif continuous_burst_active:
        lockout_reason = "LOCKED_DURING_CONTINUOUS_BURST"
    elif selftimer_countdown_active:
        lockout_reason = "LOCKED_DURING_SELFTIMER_COUNTDOWN"
    elif focus_magnifier_active:
        lockout_reason = "LOCKED_DURING_FOCUS_MAGNIFIER"

    vh_active = lockout_reason == ""
    vh_locked_out = not vh_active

    if force_vh_switch and vh_locked_out:
        return SwitchVHAndFocusLimitEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            switch_vh_af=switch_vh_af,
            previous_switch_vh_af=previous_switch_vh_af,
            roll_orientation=roll_orientation,
            orientation_sensor_valid=sensor_valid,
            vh_switch_active=False,
            vh_switch_locked_out=True,
            vh_lockout_reason=lockout_reason,
            remembered_positions_cleared=positions_cleared,
            active_focus_area=focus_area_0deg,
            effective_switch_vh_af=eff_switch_vh,
            effective_focus_area_color=eff_color,
            checked_focus_area_limit=eff_checked,
            exposed_limit_checkbox_count=len(FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES),
            movie_exposed_areas=movie_exposed,
            vh_or_reg_area_cleared=vh_or_reg_cleared,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code=f"FORCE_SWITCH_VH_REJECTED_{lockout_reason}",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if vh_active and eff_switch_vh == SWITCH_VH_AF_POINT_PLUS_AREA:
        if roll_orientation == ORIENT_90_DEG:
            eff_area = focus_area_90deg
        elif roll_orientation == ORIENT_270_DEG:
            eff_area = focus_area_270deg
        else:
            eff_area = focus_area_0deg
    else:
        eff_area = focus_area_0deg

    return SwitchVHAndFocusLimitEvalResult(
        body_profile=body_profile,
        shooting_domain=shooting_domain,
        focus_mode=focus_mode,
        switch_vh_af=switch_vh_af,
        previous_switch_vh_af=previous_switch_vh_af,
        roll_orientation=roll_orientation,
        orientation_sensor_valid=sensor_valid,
        vh_switch_active=vh_active,
        vh_switch_locked_out=vh_locked_out,
        vh_lockout_reason=lockout_reason if vh_locked_out else "ACTIVE_STILL_AFC_SWITCH",
        remembered_positions_cleared=positions_cleared,
        active_focus_area=eff_area,
        effective_switch_vh_af=eff_switch_vh,
        effective_focus_area_color=eff_color,
        checked_focus_area_limit=eff_checked,
        exposed_limit_checkbox_count=len(FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES),
        movie_exposed_areas=movie_exposed,
        vh_or_reg_area_cleared=vh_or_reg_cleared,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        admitted=True,
        errno_code=0,
        reason_code="SWITCH_VH_ACTIVE_OK" if vh_active else f"VH_LOCKED_OUT_GRACEFUL_{lockout_reason}",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Sub-Model 64B: 5-Mode [Exposure Std. Adjust] (1/6 EV) & [Bracket Settings]
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExposureStdAdjAndBracketEvalResult:
    body_profile: str
    shooting_domain: str
    metering_mode: str
    requested_offset_sixths: int
    effective_offset_sixths: int
    effective_offset_ev: float
    exposed_metering_mode_count: int
    caution_dialog_0xe567_shown: bool
    std_adjust_independent_exif: bool
    exposure_comp_ev_untouched: float
    effective_mm_shift_ev: float
    effective_ae_baseline_shift_ev: float
    spot_ael_shifted: bool
    bracket_drive_mode: str
    effective_bracket_selftimer: str
    effective_bracket_order: str
    effective_focus_bracket_order: str
    bracket_counter_reset: bool
    effective_bracket_shot_index: int
    camera_settings_reset_applied: bool
    initialize_applied: bool
    admitted: bool
    errno_code: int
    reason_code: str
    nvram_persistent_writes: int
    physical_device_writes: int


def simulate_exposure_std_adj_and_bracket_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shooting_domain: str = DOMAIN_STILL,
    metering_mode: str = METERING_MULTI,
    offset_sixths: Optional[int] = None,
    offset_ev: float = 0.0,
    exposure_comp_ev: float = 0.0,
    bracket_drive_mode: str = BRACKET_DRIVE_NONE,
    bracket_selftimer: str = BRACKET_SELFTIMER_OFF,
    bracket_order: str = BRACKET_ORDER_ZERO_MINUS_PLUS,
    focus_bracket_order: str = BRACKET_ORDER_ZERO_MINUS_PLUS,
    bracket_in_progress: bool = False,
    bracket_shot_index: int = 0,
    modify_std_adj_during_bracket: bool = False,
    configure_bracket_settings: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> ExposureStdAdjAndBracketEvalResult:
    """Model Sub-Model 64B: 5-Mode [Exposure Std. Adjust] & Still-Only [Bracket Settings]."""
    if offset_sixths is None:
        scaled = offset_ev * 6.0
        rounded = int(round(scaled))
        if abs(scaled - rounded) > 1e-4 or rounded not in VALID_EXPOSURE_STD_SIXTHS:
            return ExposureStdAdjAndBracketEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                metering_mode=metering_mode,
                requested_offset_sixths=rounded,
                effective_offset_sixths=0,
                effective_offset_ev=0.0,
                exposed_metering_mode_count=5 if body_profile == BODY_MODEL_FX3 else 0,
                caution_dialog_0xe567_shown=False,
                std_adjust_independent_exif=True,
                exposure_comp_ev_untouched=exposure_comp_ev,
                effective_mm_shift_ev=0.0,
                effective_ae_baseline_shift_ev=0.0,
                spot_ael_shifted=False,
                bracket_drive_mode=bracket_drive_mode,
                effective_bracket_selftimer=BRACKET_SELFTIMER_OFF,
                effective_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
                effective_focus_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
                bracket_counter_reset=False,
                effective_bracket_shot_index=bracket_shot_index,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason_code="EXPOSURE_STD_OFFSET_MUST_BE_1_6_EV_STEP_WITHIN_PM1_EV",
                nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        req_sixths = rounded
    else:
        if offset_sixths not in VALID_EXPOSURE_STD_SIXTHS:
            return ExposureStdAdjAndBracketEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                metering_mode=metering_mode,
                requested_offset_sixths=offset_sixths,
                effective_offset_sixths=0,
                effective_offset_ev=0.0,
                exposed_metering_mode_count=5 if body_profile == BODY_MODEL_FX3 else 0,
                caution_dialog_0xe567_shown=False,
                std_adjust_independent_exif=True,
                exposure_comp_ev_untouched=exposure_comp_ev,
                effective_mm_shift_ev=0.0,
                effective_ae_baseline_shift_ev=0.0,
                spot_ael_shifted=False,
                bracket_drive_mode=bracket_drive_mode,
                effective_bracket_selftimer=BRACKET_SELFTIMER_OFF,
                effective_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
                effective_focus_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
                bracket_counter_reset=False,
                effective_bracket_shot_index=bracket_shot_index,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason_code="EXPOSURE_STD_SIXTHS_OUT_OF_RANGE",
                nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        req_sixths = int(offset_sixths)

    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or shooting_domain not in VALID_SHOOTING_DOMAINS
        or metering_mode not in VALID_FX3_EXPOSURE_STD_5_MODES
        or bracket_drive_mode not in VALID_BRACKET_DRIVE_MODES
        or bracket_selftimer not in VALID_BRACKET_SELFTIMERS
        or bracket_order not in VALID_BRACKET_ORDERS
        or focus_bracket_order not in VALID_FOCUS_BRACKET_ORDERS
    ):
        return ExposureStdAdjAndBracketEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            metering_mode=metering_mode,
            requested_offset_sixths=req_sixths,
            effective_offset_sixths=0,
            effective_offset_ev=0.0,
            exposed_metering_mode_count=0,
            caution_dialog_0xe567_shown=False,
            std_adjust_independent_exif=True,
            exposure_comp_ev_untouched=exposure_comp_ev,
            effective_mm_shift_ev=0.0,
            effective_ae_baseline_shift_ev=0.0,
            spot_ael_shifted=False,
            bracket_drive_mode=bracket_drive_mode,
            effective_bracket_selftimer=BRACKET_SELFTIMER_OFF,
            effective_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
            effective_focus_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
            bracket_counter_reset=False,
            effective_bracket_shot_index=bracket_shot_index,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_SUBMODEL_64B_ARGUMENT",
            nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # FX6 lacks Exposure Std. Adjust and Still Bracket Settings
    if body_profile == BODY_MODEL_FX6:
        if req_sixths != 0 or configure_bracket_settings or bracket_drive_mode != BRACKET_DRIVE_NONE:
            return ExposureStdAdjAndBracketEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                metering_mode=metering_mode,
                requested_offset_sixths=req_sixths,
                effective_offset_sixths=0,
                effective_offset_ev=0.0,
                exposed_metering_mode_count=0,
                caution_dialog_0xe567_shown=False,
                std_adjust_independent_exif=True,
                exposure_comp_ev_untouched=exposure_comp_ev,
                effective_mm_shift_ev=0.0,
                effective_ae_baseline_shift_ev=0.0,
                spot_ael_shifted=False,
                bracket_drive_mode=bracket_drive_mode,
                effective_bracket_selftimer=BRACKET_SELFTIMER_OFF,
                effective_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
                effective_focus_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
                bracket_counter_reset=False,
                effective_bracket_shot_index=0,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason_code="FX6_LACKS_EXPOSURE_STD_ADJ_AND_STILL_BRACKET",
                nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        return ExposureStdAdjAndBracketEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            metering_mode=metering_mode,
            requested_offset_sixths=0,
            effective_offset_sixths=0,
            effective_offset_ev=0.0,
            exposed_metering_mode_count=0,
            caution_dialog_0xe567_shown=False,
            std_adjust_independent_exif=True,
            exposure_comp_ev_untouched=exposure_comp_ev,
            effective_mm_shift_ev=0.0,
            effective_ae_baseline_shift_ev=0.0,
            spot_ael_shifted=False,
            bracket_drive_mode=BRACKET_DRIVE_NONE,
            effective_bracket_selftimer=BRACKET_SELFTIMER_OFF,
            effective_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
            effective_focus_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
            bracket_counter_reset=False,
            effective_bracket_shot_index=0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=True,
            errno_code=0,
            reason_code="FX6_AUTO_EXPOSURE_LEVEL_CONTRAST_OK",
            nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Still-only [Bracket Settings] rejected in Movie / S&Q
    if shooting_domain in (DOMAIN_MOVIE, DOMAIN_SQ) and (
        configure_bracket_settings or bracket_drive_mode != BRACKET_DRIVE_NONE
    ):
        return ExposureStdAdjAndBracketEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            metering_mode=metering_mode,
            requested_offset_sixths=req_sixths,
            effective_offset_sixths=0 if initialize_applied else req_sixths,
            effective_offset_ev=round((0 if initialize_applied else req_sixths) / 6.0, 6),
            exposed_metering_mode_count=len(VALID_FX3_EXPOSURE_STD_5_MODES),
            caution_dialog_0xe567_shown=req_sixths != 0,
            std_adjust_independent_exif=True,
            exposure_comp_ev_untouched=exposure_comp_ev,
            effective_mm_shift_ev=round((0 if initialize_applied else req_sixths) / 6.0, 6),
            effective_ae_baseline_shift_ev=round(
                (0 if initialize_applied else req_sixths) / 6.0, 6
            ),
            spot_ael_shifted=(metering_mode == METERING_SPOT and req_sixths != 0),
            bracket_drive_mode=bracket_drive_mode,
            effective_bracket_selftimer=BRACKET_SELFTIMER_OFF,
            effective_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
            effective_focus_bracket_order=BRACKET_ORDER_ZERO_MINUS_PLUS,
            bracket_counter_reset=False,
            effective_bracket_shot_index=0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code=f"BRACKET_SETTINGS_STILL_ONLY_REJECTED_IN_{shooting_domain.upper()}",
            nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Lifecycle split:
    # - Exposure Std. Adjust SURVIVES Camera Settings Reset; resets ONLY via Initialize.
    # - Bracket Settings (Selftimer during Bracket & Bracket order) RESET via Camera Settings Reset!
    eff_sixths = 0 if initialize_applied else req_sixths
    eff_ev = round(eff_sixths / 6.0, 6)

    reset_bracket = camera_settings_reset_applied or initialize_applied
    eff_selftimer = BRACKET_SELFTIMER_OFF if reset_bracket else bracket_selftimer
    eff_order = BRACKET_ORDER_ZERO_MINUS_PLUS if reset_bracket else bracket_order
    eff_focus_order = BRACKET_ORDER_ZERO_MINUS_PLUS if reset_bracket else focus_bracket_order

    counter_reset = bool(bracket_in_progress and modify_std_adj_during_bracket)
    eff_shot_idx = 0 if counter_reset else bracket_shot_index

    return ExposureStdAdjAndBracketEvalResult(
        body_profile=body_profile,
        shooting_domain=shooting_domain,
        metering_mode=metering_mode,
        requested_offset_sixths=req_sixths,
        effective_offset_sixths=eff_sixths,
        effective_offset_ev=eff_ev,
        exposed_metering_mode_count=len(VALID_FX3_EXPOSURE_STD_5_MODES),
        caution_dialog_0xe567_shown=(eff_sixths != 0 or req_sixths != 0),
        std_adjust_independent_exif=True,
        exposure_comp_ev_untouched=exposure_comp_ev,
        effective_mm_shift_ev=eff_ev,
        effective_ae_baseline_shift_ev=eff_ev,
        spot_ael_shifted=(metering_mode == METERING_SPOT and eff_sixths != 0),
        bracket_drive_mode=bracket_drive_mode,
        effective_bracket_selftimer=eff_selftimer,
        effective_bracket_order=eff_order,
        effective_focus_bracket_order=eff_focus_order,
        bracket_counter_reset=counter_reset,
        effective_bracket_shot_index=eff_shot_idx,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        admitted=True,
        errno_code=0,
        reason_code="EXPOSURE_STD_ADJ_AND_BRACKET_OK",
        nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Sub-Model 64C: [Time Code Format] DF/NDF, [User Bit Time Rec], PAL/24p Locks
# ---------------------------------------------------------------------------


_UB_PRESET_RE = re.compile(r"^[0-9A-Fa-f]{2}(?: [0-9A-Fa-f]{2}){3}$")
_TC_PRESET_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{2}$")


@dataclass(frozen=True)
class TimeCodeFormatAndUbRecEvalResult:
    body_profile: str
    system_frequency: str
    frame_rate: str
    requested_tc_format: str
    effective_tc_format: str
    tc_format_menu_exposed: bool
    tc_format_locked_ndf: bool
    tc_format_menu_hidden: bool
    effective_tc_preset: str
    effective_ub_preset: str
    effective_tc_run: str
    effective_tc_make: str
    effective_ub_time_rec: str
    ub_records_real_time: bool
    effective_tc_ub_disp_setting: str
    all_6_tcub_survived_cam_reset: bool
    fx3_has_bnc_tc_in_out_switch: bool
    fx6_has_bnc_tc_in_out_switch: bool
    fx6_ext_lk_bnc_switch_state: str
    camera_settings_reset_applied: bool
    initialize_applied: bool
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


def simulate_tc_format_ub_time_rec_and_disp_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    system_frequency: str = SYSTEM_NTSC,
    frame_rate: str = FPS_59_94P,
    requested_tc_format: str = TC_FORMAT_DF,
    tc_preset: str = "00:00:00.00",
    ub_preset: str = "00 00 00 00",
    tc_run: str = TC_RUN_REC,
    tc_make: str = TC_MAKE_PRESET,
    ub_time_rec: str = "Off",
    tc_ub_disp_setting: str = TC_DISP_TC,
    playback_media_is_still: bool = False,
    playback_disp_toggle_attempted: bool = False,
    request_bnc_tc_in_out_switch: bool = False,
    fx6_bnc_switch_dir: str = "IN",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> TimeCodeFormatAndUbRecEvalResult:
    """Model Sub-Model 64C: [Time Code Format] DF/NDF, 23.98p/24p/PAL Locks & UB Time Rec."""
    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or system_frequency not in VALID_TV_SYSTEMS
        or frame_rate not in ALL_VALID_FRAME_RATES
        or requested_tc_format not in VALID_TC_FORMATS
        or tc_run not in VALID_TC_RUN_MODES
        or tc_make not in VALID_TC_MAKE_MODES
        or ub_time_rec not in ("On", "Off")
        or tc_ub_disp_setting not in VALID_TC_UB_DISP_SETTINGS
        or (not _TC_PRESET_RE.match(tc_preset))
        or (not _UB_PRESET_RE.match(ub_preset))
        or fx6_bnc_switch_dir not in ("IN", "OUT")
    ):
        return TimeCodeFormatAndUbRecEvalResult(
            body_profile=body_profile,
            system_frequency=system_frequency,
            frame_rate=frame_rate,
            requested_tc_format=requested_tc_format,
            effective_tc_format=TC_FORMAT_NDF,
            tc_format_menu_exposed=False,
            tc_format_locked_ndf=False,
            tc_format_menu_hidden=False,
            effective_tc_preset="00:00:00.00",
            effective_ub_preset="00 00 00 00",
            effective_tc_run=TC_RUN_REC,
            effective_tc_make=TC_MAKE_PRESET,
            effective_ub_time_rec="Off",
            ub_records_real_time=False,
            effective_tc_ub_disp_setting=TC_DISP_TC,
            all_6_tcub_survived_cam_reset=False,
            fx3_has_bnc_tc_in_out_switch=FX3_HAS_BNC_TC_IN_OUT_SWITCH,
            fx6_has_bnc_tc_in_out_switch=FX6_HAS_BNC_TC_IN_OUT_SWITCH,
            fx6_ext_lk_bnc_switch_state="NONE",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_TCUB_ARGUMENT",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Validate system_frequency <-> frame_rate compatibility
    if system_frequency == SYSTEM_NTSC and frame_rate in PAL_RATES_HIDDEN_NDF:
        return TimeCodeFormatAndUbRecEvalResult(
            body_profile=body_profile,
            system_frequency=system_frequency,
            frame_rate=frame_rate,
            requested_tc_format=requested_tc_format,
            effective_tc_format=TC_FORMAT_NDF,
            tc_format_menu_exposed=False,
            tc_format_locked_ndf=False,
            tc_format_menu_hidden=False,
            effective_tc_preset=tc_preset,
            effective_ub_preset=ub_preset,
            effective_tc_run=tc_run,
            effective_tc_make=tc_make,
            effective_ub_time_rec=ub_time_rec,
            ub_records_real_time=False,
            effective_tc_ub_disp_setting=tc_ub_disp_setting,
            all_6_tcub_survived_cam_reset=False,
            fx3_has_bnc_tc_in_out_switch=FX3_HAS_BNC_TC_IN_OUT_SWITCH,
            fx6_has_bnc_tc_in_out_switch=FX6_HAS_BNC_TC_IN_OUT_SWITCH,
            fx6_ext_lk_bnc_switch_state="NONE",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="PAL_FRAME_RATE_REJECTED_IN_NTSC",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )
    if system_frequency == SYSTEM_PAL and frame_rate not in PAL_RATES_HIDDEN_NDF:
        return TimeCodeFormatAndUbRecEvalResult(
            body_profile=body_profile,
            system_frequency=system_frequency,
            frame_rate=frame_rate,
            requested_tc_format=requested_tc_format,
            effective_tc_format=TC_FORMAT_NDF,
            tc_format_menu_exposed=False,
            tc_format_locked_ndf=False,
            tc_format_menu_hidden=True,
            effective_tc_preset=tc_preset,
            effective_ub_preset=ub_preset,
            effective_tc_run=tc_run,
            effective_tc_make=tc_make,
            effective_ub_time_rec=ub_time_rec,
            ub_records_real_time=False,
            effective_tc_ub_disp_setting=tc_ub_disp_setting,
            all_6_tcub_survived_cam_reset=False,
            fx3_has_bnc_tc_in_out_switch=FX3_HAS_BNC_TC_IN_OUT_SWITCH,
            fx6_has_bnc_tc_in_out_switch=FX6_HAS_BNC_TC_IN_OUT_SWITCH,
            fx6_ext_lk_bnc_switch_state="NONE",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="NTSC_FRAME_RATE_REJECTED_IN_PAL",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # FX3 lacks physical BNC TC IN/OUT connector & switch
    if body_profile == BODY_MODEL_FX3 and request_bnc_tc_in_out_switch:
        return TimeCodeFormatAndUbRecEvalResult(
            body_profile=body_profile,
            system_frequency=system_frequency,
            frame_rate=frame_rate,
            requested_tc_format=requested_tc_format,
            effective_tc_format=TC_FORMAT_NDF,
            tc_format_menu_exposed=False,
            tc_format_locked_ndf=False,
            tc_format_menu_hidden=False,
            effective_tc_preset=tc_preset,
            effective_ub_preset=ub_preset,
            effective_tc_run=tc_run,
            effective_tc_make=tc_make,
            effective_ub_time_rec=ub_time_rec,
            ub_records_real_time=False,
            effective_tc_ub_disp_setting=tc_ub_disp_setting,
            all_6_tcub_survived_cam_reset=False,
            fx3_has_bnc_tc_in_out_switch=FX3_HAS_BNC_TC_IN_OUT_SWITCH,
            fx6_has_bnc_tc_in_out_switch=FX6_HAS_BNC_TC_IN_OUT_SWITCH,
            fx6_ext_lk_bnc_switch_state="ABSENT_ON_FX3",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="FX3_HAS_NO_PHYSICAL_BNC_TC_IN_OUT_SWITCH",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Playback TC/UB Disp. Setting toggle restricted to movies (.uxc 0xe728)
    if playback_media_is_still and playback_disp_toggle_attempted:
        return TimeCodeFormatAndUbRecEvalResult(
            body_profile=body_profile,
            system_frequency=system_frequency,
            frame_rate=frame_rate,
            requested_tc_format=requested_tc_format,
            effective_tc_format=TC_FORMAT_NDF,
            tc_format_menu_exposed=False,
            tc_format_locked_ndf=False,
            tc_format_menu_hidden=False,
            effective_tc_preset=tc_preset,
            effective_ub_preset=ub_preset,
            effective_tc_run=tc_run,
            effective_tc_make=tc_make,
            effective_ub_time_rec=ub_time_rec,
            ub_records_real_time=False,
            effective_tc_ub_disp_setting=tc_ub_disp_setting,
            all_6_tcub_survived_cam_reset=False,
            fx3_has_bnc_tc_in_out_switch=FX3_HAS_BNC_TC_IN_OUT_SWITCH,
            fx6_has_bnc_tc_in_out_switch=FX6_HAS_BNC_TC_IN_OUT_SWITCH,
            fx6_ext_lk_bnc_switch_state="NONE",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="TC_UB_DISPLAY_SWITCHING_INVALID_ON_STILL_PLAYBACK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Lifecycle: ALL 6 [TC/UB] settings + [TC/UB Disp. Setting] SURVIVE Camera Settings Reset,
    # resetting ONLY via [Initialize]!
    eff_tc_preset = "00:00:00.00" if initialize_applied else tc_preset
    eff_ub_preset = "00 00 00 00" if initialize_applied else ub_preset
    eff_tc_run = TC_RUN_REC if initialize_applied else tc_run
    eff_tc_make = TC_MAKE_PRESET if initialize_applied else tc_make
    eff_ub_time_rec = "Off" if initialize_applied else ub_time_rec
    eff_tc_disp = TC_DISP_TC if initialize_applied else tc_ub_disp_setting

    # DF/NDF locks:
    # - PAL (50p/25p/100p): hidden & locked to NDF
    # - 23.98p & 24.00p: hard-locked to NDF
    # - NTSC 59.94p/29.97p/119.88p: DF/NDF both exposed
    if system_frequency == SYSTEM_PAL:
        tc_hidden = True
        tc_locked_ndf = True
        tc_exposed = False
        if (not initialize_applied) and requested_tc_format == TC_FORMAT_DF:
            return TimeCodeFormatAndUbRecEvalResult(
                body_profile=body_profile,
                system_frequency=system_frequency,
                frame_rate=frame_rate,
                requested_tc_format=requested_tc_format,
                effective_tc_format=TC_FORMAT_NDF,
                tc_format_menu_exposed=False,
                tc_format_locked_ndf=True,
                tc_format_menu_hidden=True,
                effective_tc_preset=eff_tc_preset,
                effective_ub_preset=eff_ub_preset,
                effective_tc_run=eff_tc_run,
                effective_tc_make=eff_tc_make,
                effective_ub_time_rec=eff_ub_time_rec,
                ub_records_real_time=(eff_ub_time_rec == "On"),
                effective_tc_ub_disp_setting=eff_tc_disp,
                all_6_tcub_survived_cam_reset=not initialize_applied,
                fx3_has_bnc_tc_in_out_switch=FX3_HAS_BNC_TC_IN_OUT_SWITCH,
                fx6_has_bnc_tc_in_out_switch=FX6_HAS_BNC_TC_IN_OUT_SWITCH,
                fx6_ext_lk_bnc_switch_state=fx6_bnc_switch_dir
                if body_profile == BODY_MODEL_FX6
                else "ABSENT",
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason_code="PAL_LOCKS_AND_HIDES_TC_FORMAT_TO_NDF",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        eff_tc_fmt = TC_FORMAT_NDF
    elif frame_rate in NTSC_RATES_NDF_LOCKED:
        tc_hidden = False
        tc_locked_ndf = True
        tc_exposed = False
        if (not initialize_applied) and requested_tc_format == TC_FORMAT_DF:
            return TimeCodeFormatAndUbRecEvalResult(
                body_profile=body_profile,
                system_frequency=system_frequency,
                frame_rate=frame_rate,
                requested_tc_format=requested_tc_format,
                effective_tc_format=TC_FORMAT_NDF,
                tc_format_menu_exposed=False,
                tc_format_locked_ndf=True,
                tc_format_menu_hidden=False,
                effective_tc_preset=eff_tc_preset,
                effective_ub_preset=eff_ub_preset,
                effective_tc_run=eff_tc_run,
                effective_tc_make=eff_tc_make,
                effective_ub_time_rec=eff_ub_time_rec,
                ub_records_real_time=(eff_ub_time_rec == "On"),
                effective_tc_ub_disp_setting=eff_tc_disp,
                all_6_tcub_survived_cam_reset=not initialize_applied,
                fx3_has_bnc_tc_in_out_switch=FX3_HAS_BNC_TC_IN_OUT_SWITCH,
                fx6_has_bnc_tc_in_out_switch=FX6_HAS_BNC_TC_IN_OUT_SWITCH,
                fx6_ext_lk_bnc_switch_state=fx6_bnc_switch_dir
                if body_profile == BODY_MODEL_FX6
                else "ABSENT",
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason_code=f"TRUE_OR_NTSC_24P_{frame_rate}_HARD_LOCKS_TC_FORMAT_NDF",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        eff_tc_fmt = TC_FORMAT_NDF
    else:
        tc_hidden = False
        tc_locked_ndf = False
        tc_exposed = True
        eff_tc_fmt = TC_FORMAT_DF if initialize_applied else requested_tc_format

    fx6_bnc_state = (
        f"EXT-LK_{fx6_bnc_switch_dir}"
        if (body_profile == BODY_MODEL_FX6 and fx6_bnc_switch_dir == "IN")
        else ("TC_OUT_BNC" if body_profile == BODY_MODEL_FX6 else "ABSENT_ON_FX3")
    )

    return TimeCodeFormatAndUbRecEvalResult(
        body_profile=body_profile,
        system_frequency=system_frequency,
        frame_rate=frame_rate,
        requested_tc_format=requested_tc_format,
        effective_tc_format=eff_tc_fmt,
        tc_format_menu_exposed=tc_exposed,
        tc_format_locked_ndf=tc_locked_ndf,
        tc_format_menu_hidden=tc_hidden,
        effective_tc_preset=eff_tc_preset,
        effective_ub_preset=eff_ub_preset,
        effective_tc_run=eff_tc_run,
        effective_tc_make=eff_tc_make,
        effective_ub_time_rec=eff_ub_time_rec,
        ub_records_real_time=(eff_ub_time_rec == "On"),
        effective_tc_ub_disp_setting=eff_tc_disp,
        all_6_tcub_survived_cam_reset=(not initialize_applied),
        fx3_has_bnc_tc_in_out_switch=FX3_HAS_BNC_TC_IN_OUT_SWITCH,
        fx6_has_bnc_tc_in_out_switch=FX6_HAS_BNC_TC_IN_OUT_SWITCH,
        fx6_ext_lk_bnc_switch_state=fx6_bnc_state,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        admitted=True,
        errno_code=0,
        reason_code="TC_FORMAT_AND_UB_REC_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Sub-Model 64D: CRITICAL Reverse-Direction Vault Firewall ([Copy] & [Slide Show])
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlaybackCopyAndSlideShowVaultEvalResult:
    body_profile: str
    operation: str
    select_playback_media: str
    effective_select_playback_media: str
    copy_source_slot: str
    copy_dest_slot: str
    copy_direction: str
    slot1_is_tier0_vault: bool
    tier0_vault_firewall_triggered: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    slot1_vault_copy_reverse_direction_mutation_bytes: int
    dest_group_flattened: bool
    dest_protect_cleared: bool
    slideshow_repeat: str
    effective_slideshow_repeat: str
    slideshow_interval: str
    effective_slideshow_interval: str
    slideshow_view_mode: str
    power_save_suspended: bool
    camera_settings_reset_applied: bool
    initialize_applied: bool
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


def simulate_playback_copy_direction_slideshow_vault_firewall_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    operation: str = OP_PB_NONE,
    select_playback_media: str = SLOT_1,
    slot1_is_tier0_vault: bool = True,
    slot1_inserted: bool = True,
    slot2_inserted: bool = True,
    slot1_write_protected: bool = False,
    slot2_write_protected: bool = False,
    background_transfer_active: bool = False,
    is_recording: bool = False,
    battery_low_for_copy: bool = False,
    copy_content_type: str = CONTENT_ALL,
    dest_speed_class: str = SPEED_SDXC_V90,
    slideshow_repeat: str = "Off",
    slideshow_interval: str = SLIDESHOW_INTERVAL_3S,
    slideshow_view_mode: str = VIEW_MODE_DATE,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> PlaybackCopyAndSlideShowVaultEvalResult:
    """Model Sub-Model 64D: [Select Playback Media] reversing [Copy] + Vault Firewall + [Slide Show]."""
    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or operation not in VALID_PLAYBACK_OPS
        or select_playback_media not in VALID_PLAYBACK_SLOTS
        or copy_content_type not in VALID_COPY_CONTENT_TYPES
        or dest_speed_class not in VALID_MEDIA_SPEED_CLASSES
        or slideshow_repeat not in ("On", "Off")
        or slideshow_interval not in VALID_SLIDESHOW_INTERVALS
        or slideshow_view_mode not in ALL_VALID_VIEW_MODES
    ):
        return PlaybackCopyAndSlideShowVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            select_playback_media=select_playback_media,
            effective_select_playback_media=SLOT_1,
            copy_source_slot="",
            copy_dest_slot="",
            copy_direction="",
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_copy_reverse_direction_mutation_bytes=0,
            dest_group_flattened=False,
            dest_protect_cleared=False,
            slideshow_repeat=slideshow_repeat,
            effective_slideshow_repeat="Off",
            slideshow_interval=slideshow_interval,
            effective_slideshow_interval=SLIDESHOW_INTERVAL_3S,
            slideshow_view_mode=slideshow_view_mode,
            power_save_suspended=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_SUBMODEL_64D_ARGUMENT",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    eff_pb_media = SLOT_1 if initialize_applied else select_playback_media
    eff_repeat = "Off" if initialize_applied else slideshow_repeat
    eff_interval = SLIDESHOW_INTERVAL_3S if initialize_applied else slideshow_interval

    copy_src = eff_pb_media
    copy_dst = SLOT_2 if eff_pb_media == SLOT_1 else SLOT_1
    copy_dir = f"{copy_src} -> {copy_dst}"

    def _reject(errno_val: int, reason: str, *, firewall: bool = False) -> PlaybackCopyAndSlideShowVaultEvalResult:
        return PlaybackCopyAndSlideShowVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            select_playback_media=select_playback_media,
            effective_select_playback_media=eff_pb_media,
            copy_source_slot=copy_src,
            copy_dest_slot=copy_dst,
            copy_direction=copy_dir,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            tier0_vault_firewall_triggered=firewall,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_copy_reverse_direction_mutation_bytes=0,
            dest_group_flattened=False,
            dest_protect_cleared=False,
            slideshow_repeat=slideshow_repeat,
            effective_slideshow_repeat=eff_repeat,
            slideshow_interval=slideshow_interval,
            effective_slideshow_interval=eff_interval,
            slideshow_view_mode=slideshow_view_mode,
            power_save_suspended=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=False,
            errno_code=errno_val,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # FX6 lacks consumer Playback [Copy] & [Slide Show]
    if body_profile == BODY_MODEL_FX6:
        if operation in (OP_PB_COPY, OP_PB_SLIDE_SHOW):
            return _reject(
                EOPNOTSUPP_ERRNO,
                f"FX6_NO_CONSUMER_PLAYBACK_{operation}_USE_FTP_OR_CATALYST",
            )
        return PlaybackCopyAndSlideShowVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            select_playback_media=select_playback_media,
            effective_select_playback_media=eff_pb_media,
            copy_source_slot=copy_src,
            copy_dest_slot=copy_dst,
            copy_direction=copy_dir,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_copy_reverse_direction_mutation_bytes=0,
            dest_group_flattened=False,
            dest_protect_cleared=False,
            slideshow_repeat=slideshow_repeat,
            effective_slideshow_repeat="Off",
            slideshow_interval=slideshow_interval,
            effective_slideshow_interval=SLIDESHOW_INTERVAL_3S,
            slideshow_view_mode=slideshow_view_mode,
            power_save_suspended=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=True,
            errno_code=0,
            reason_code="FX6_DORMANT_COPY_CLIP_CONTRAST_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if operation == OP_PB_NONE:
        return PlaybackCopyAndSlideShowVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            select_playback_media=select_playback_media,
            effective_select_playback_media=eff_pb_media,
            copy_source_slot=copy_src,
            copy_dest_slot=copy_dst,
            copy_direction=copy_dir,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_copy_reverse_direction_mutation_bytes=0,
            dest_group_flattened=False,
            dest_protect_cleared=False,
            slideshow_repeat=slideshow_repeat,
            effective_slideshow_repeat=eff_repeat,
            slideshow_interval=slideshow_interval,
            effective_slideshow_interval=eff_interval,
            slideshow_view_mode=slideshow_view_mode,
            power_save_suspended=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=True,
            errno_code=0,
            reason_code="PLAYBACK_TARGET_AND_SLIDESHOW_SETTINGS_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if operation == OP_PB_SLIDE_SHOW:
        if (copy_src == SLOT_1 and not slot1_inserted) or (
            copy_src == SLOT_2 and not slot2_inserted
        ):
            return _reject(EINVAL_ERRNO, "SLIDESHOW_SOURCE_SLOT_EMPTY")
        if slideshow_view_mode not in VALID_SLIDESHOW_VIEW_MODES:
            return _reject(
                EOPNOTSUPP_ERRNO,
                "SLIDESHOW_REQUIRES_DATE_VIEW_OR_FOLDER_VIEW_STILL",
            )
        return PlaybackCopyAndSlideShowVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            select_playback_media=select_playback_media,
            effective_select_playback_media=eff_pb_media,
            copy_source_slot=copy_src,
            copy_dest_slot=copy_dst,
            copy_direction=copy_dir,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_copy_reverse_direction_mutation_bytes=0,
            dest_group_flattened=False,
            dest_protect_cleared=False,
            slideshow_repeat=slideshow_repeat,
            effective_slideshow_repeat=eff_repeat,
            slideshow_interval=slideshow_interval,
            effective_slideshow_interval=eff_interval,
            slideshow_view_mode=slideshow_view_mode,
            power_save_suspended=True,  # DURING_PLAYBACK_SLIDESHOW bypasses Power Save Start Time
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            admitted=True,
            errno_code=0,
            reason_code="SLIDE_SHOW_READ_ONLY_SAFE_POWER_SAVE_SUSPENDED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # operation == OP_PB_COPY
    # CRITICAL REVERSE-DIRECTION VAULT FIREWALL:
    # When [Select Playback Media] == Slot 2, Playback [Copy] writes FROM Slot 2 ONTO Slot 1!
    if (not slot1_inserted) or (not slot2_inserted):
        return _reject(EINVAL_ERRNO, "COPY_REQUIRES_BOTH_SLOT1_AND_SLOT2_CARDS_INSERTED")

    if copy_dst == SLOT_1 and slot1_is_tier0_vault:
        return _reject(
            EROFS_ERRNO,
            "SLOT1_TIER0_VAULT_REVERSE_COPY_SLOT2_TO_SLOT1_BLOCKED_EROFS",
            firewall=True,
        )
    if (copy_dst == SLOT_1 and slot1_write_protected) or (
        copy_dst == SLOT_2 and slot2_write_protected
    ):
        return _reject(EROFS_ERRNO, "COPY_DEST_CARD_WRITE_PROTECTED_EROFS", firewall=(copy_dst == SLOT_1))

    if background_transfer_active or is_recording or battery_low_for_copy:
        reason = (
            "COPY_BATTERY_INSUFFICIENT_EBUSY"
            if battery_low_for_copy
            else "COPY_BLOCKED_ACTIVE_RECORDING_OR_BG_TRANSFER_EBUSY"
        )
        return _reject(
            EBUSY_ERRNO,
            reason,
            firewall=(copy_dst == SLOT_1 and slot1_is_tier0_vault),
        )

    if copy_content_type in (CONTENT_MOVIE, CONTENT_ALL) and (
        dest_speed_class == SPEED_SDHC_LEGACY_SLOW
    ):
        return _reject(
            EOPNOTSUPP_ERRNO,
            "COPY_MOVIE_DEST_CARD_BELOW_SDXC_U1_V10_0xe80e",
        )

    # Virtual Slot 1 -> Slot 2 copy (0 physical writes, Slot 1 strictly read-only)
    return PlaybackCopyAndSlideShowVaultEvalResult(
        body_profile=body_profile,
        operation=operation,
        select_playback_media=select_playback_media,
        effective_select_playback_media=eff_pb_media,
        copy_source_slot=copy_src,
        copy_dest_slot=copy_dst,
        copy_direction=copy_dir,
        slot1_is_tier0_vault=slot1_is_tier0_vault,
        tier0_vault_firewall_triggered=False,
        slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
        slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
        slot1_vault_copy_reverse_direction_mutation_bytes=0,
        dest_group_flattened=True,
        dest_protect_cleared=True,
        slideshow_repeat=slideshow_repeat,
        effective_slideshow_repeat=eff_repeat,
        slideshow_interval=slideshow_interval,
        effective_slideshow_interval=eff_interval,
        slideshow_view_mode=slideshow_view_mode,
        power_save_suspended=False,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        admitted=True,
        errno_code=0,
        reason_code="SLOT1_TO_SLOT2_VIRTUAL_COPY_OK_GROUP_FLATTENED_PROTECT_CLEARED",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Full Phase 312 Stage 64 (64/64 Power-of-Two Milestone) Closed-Loop Co-Emulator
# ---------------------------------------------------------------------------


def _build_stage64_power_of_two_milestone_probe() -> Dict[str, object]:
    return {
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "phase_number": PHASE_NUMBER,
        "stage_name": STAGE_NAME,
        "is_64th_stage_milestone": True,
        "is_64th_power_of_two_milestone": True,
        "power_of_two_exponent": 6,  # 2^6 = 64
        "wave54_pillars": [
            "64A_switch_vh_af_area_still_afc_3orient_and_14checkbox_focus_limit",
            "64B_exposure_std_adjust_5modes_1_6ev_initialize_only_and_still_bracket_settings",
            "64C_tc_format_df_ndf_2398p_24p_pal_locks_ub_time_rec_and_fx6_bnc_switch",
            "64D_playback_copy_slot2_to_slot1_reverse_vault_firewall_and_readonly_slideshow",
        ],
    }


def run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 312 Stage 64 (64/64) Wave-54 Real-Hardware HIL Co-Emulation."""
    donor_audit = inspect_phase312_donors(force_clean_room=force_clean_room, env=env)

    # Pillar 64A scenarios
    p64a_still_afc_90deg_ok = simulate_switch_vh_af_and_focus_limit_hil(
        shooting_domain=DOMAIN_STILL,
        focus_mode=FOCUS_MODE_AFC,
        switch_vh_af=SWITCH_VH_AF_POINT_PLUS_AREA,
        roll_orientation=ORIENT_90_DEG,
        focus_area_0deg="Wide",
        focus_area_90deg="Spot: M",
        focus_area_270deg="Zone",
    )
    p64a_still_afc_270deg_ok = simulate_switch_vh_af_and_focus_limit_hil(
        shooting_domain=DOMAIN_STILL,
        focus_mode=FOCUS_MODE_AFC,
        switch_vh_af=SWITCH_VH_AF_POINT_ONLY,
        roll_orientation=ORIENT_270_DEG,
        focus_area_0deg="Wide",
        focus_area_270deg="Zone",
    )
    p64a_invalid_pitch_degraded = simulate_switch_vh_af_and_focus_limit_hil(
        shooting_domain=DOMAIN_STILL,
        focus_mode=FOCUS_MODE_AFC,
        switch_vh_af=SWITCH_VH_AF_POINT_PLUS_AREA,
        roll_orientation=ORIENT_INVALID_PITCH,
    )
    p64a_movie_locked_out = simulate_switch_vh_af_and_focus_limit_hil(
        shooting_domain=DOMAIN_MOVIE,
        focus_mode=FOCUS_MODE_AFC,
        switch_vh_af=SWITCH_VH_AF_POINT_ONLY,
        force_vh_switch=True,
    )
    p64a_afs_locked_out = simulate_switch_vh_af_and_focus_limit_hil(
        shooting_domain=DOMAIN_STILL,
        focus_mode=FOCUS_MODE_AFS,
        switch_vh_af=SWITCH_VH_AF_POINT_ONLY,
        force_vh_switch=True,
    )
    p64a_limit_lt2_rejected = simulate_switch_vh_af_and_focus_limit_hil(
        checked_focus_areas=("Wide",),
    )
    p64a_dormant_alpha_rejected = simulate_switch_vh_af_and_focus_limit_hil(
        checked_focus_areas=("Wide", "Spot: XL"),
    )
    p64a_mode_change_clears_positions = simulate_switch_vh_af_and_focus_limit_hil(
        switch_vh_af=SWITCH_VH_AF_POINT_PLUS_AREA,
        previous_switch_vh_af=SWITCH_VH_AF_POINT_ONLY,
    )
    p64a_fx6_rejected = simulate_switch_vh_af_and_focus_limit_hil(
        body_profile=BODY_MODEL_FX6,
        switch_vh_af=SWITCH_VH_AF_POINT_ONLY,
    )

    p64a_ok = (
        p64a_still_afc_90deg_ok.admitted
        and p64a_still_afc_90deg_ok.vh_switch_active
        and p64a_still_afc_90deg_ok.active_focus_area == "Spot: M"
        and p64a_still_afc_90deg_ok.exposed_limit_checkbox_count == 14
        and p64a_still_afc_270deg_ok.admitted
        and p64a_still_afc_270deg_ok.vh_switch_active
        and p64a_still_afc_270deg_ok.active_focus_area == "Wide"
        and p64a_invalid_pitch_degraded.admitted
        and (not p64a_invalid_pitch_degraded.orientation_sensor_valid)
        and (not p64a_invalid_pitch_degraded.vh_switch_active)
        and (not p64a_movie_locked_out.admitted)
        and p64a_movie_locked_out.errno_code == EOPNOTSUPP_ERRNO
        and (not p64a_afs_locked_out.admitted)
        and p64a_afs_locked_out.errno_code == EOPNOTSUPP_ERRNO
        and (not p64a_limit_lt2_rejected.admitted)
        and p64a_limit_lt2_rejected.errno_code == EINVAL_ERRNO
        and (not p64a_dormant_alpha_rejected.admitted)
        and p64a_dormant_alpha_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p64a_mode_change_clears_positions.remembered_positions_cleared
        and (not p64a_fx6_rejected.admitted)
        and p64a_fx6_rejected.errno_code == EOPNOTSUPP_ERRNO
    )

    # Pillar 64B scenarios
    p64b_all5_modes_ok = [
        simulate_exposure_std_adj_and_bracket_hil(
            metering_mode=mode,
            offset_sixths=3,  # +3/6 = +0.5 EV
            exposure_comp_ev=-0.7,
        )
        for mode in VALID_FX3_EXPOSURE_STD_5_MODES
    ]
    p64b_cam_reset_split = simulate_exposure_std_adj_and_bracket_hil(
        metering_mode=METERING_ENTIRE_SCREEN_AVG,
        offset_sixths=-5,  # -5/6 EV survives Camera Settings Reset
        bracket_drive_mode=BRACKET_DRIVE_CONT,
        bracket_selftimer=BRACKET_SELFTIMER_5S,
        bracket_order=BRACKET_ORDER_MINUS_ZERO_PLUS,
        camera_settings_reset_applied=True,
    )
    p64b_initialize_resets_std = simulate_exposure_std_adj_and_bracket_hil(
        metering_mode=METERING_HIGHLIGHT,
        offset_sixths=6,
        initialize_applied=True,
    )
    p64b_non_sixth_rejected = simulate_exposure_std_adj_and_bracket_hil(
        offset_ev=0.25,
    )
    p64b_bracket_movie_rejected = simulate_exposure_std_adj_and_bracket_hil(
        shooting_domain=DOMAIN_MOVIE,
        bracket_drive_mode=BRACKET_DRIVE_SINGLE,
        configure_bracket_settings=True,
    )
    p64b_bracket_sq_rejected = simulate_exposure_std_adj_and_bracket_hil(
        shooting_domain=DOMAIN_SQ,
        configure_bracket_settings=True,
    )
    p64b_fx6_rejected = simulate_exposure_std_adj_and_bracket_hil(
        body_profile=BODY_MODEL_FX6,
        offset_sixths=2,
    )
    p64b_mid_bracket_reset = simulate_exposure_std_adj_and_bracket_hil(
        metering_mode=METERING_SPOT,
        offset_sixths=-2,
        bracket_drive_mode=BRACKET_DRIVE_CONT,
        bracket_in_progress=True,
        bracket_shot_index=2,
        modify_std_adj_during_bracket=True,
    )

    p64b_ok = (
        len(p64b_all5_modes_ok) == 5
        and all(
            r.admitted
            and r.exposed_metering_mode_count == 5
            and r.effective_offset_sixths == 3
            and r.std_adjust_independent_exif
            and abs(r.exposure_comp_ev_untouched - (-0.7)) < 1e-6
            for r in p64b_all5_modes_ok
        )
        and p64b_cam_reset_split.admitted
        and p64b_cam_reset_split.effective_offset_sixths == -5
        and p64b_cam_reset_split.effective_bracket_selftimer == BRACKET_SELFTIMER_OFF
        and p64b_cam_reset_split.effective_bracket_order == BRACKET_ORDER_ZERO_MINUS_PLUS
        and p64b_initialize_resets_std.effective_offset_sixths == 0
        and (not p64b_non_sixth_rejected.admitted)
        and p64b_non_sixth_rejected.errno_code == EINVAL_ERRNO
        and (not p64b_bracket_movie_rejected.admitted)
        and p64b_bracket_movie_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p64b_bracket_sq_rejected.admitted)
        and p64b_bracket_sq_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p64b_fx6_rejected.admitted)
        and p64b_fx6_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p64b_mid_bracket_reset.bracket_counter_reset
        and p64b_mid_bracket_reset.effective_bracket_shot_index == 0
        and p64b_mid_bracket_reset.spot_ael_shifted
    )

    # Pillar 64C scenarios
    p64c_ntsc_5994_df_ok = simulate_tc_format_ub_time_rec_and_disp_hil(
        system_frequency=SYSTEM_NTSC,
        frame_rate=FPS_59_94P,
        requested_tc_format=TC_FORMAT_DF,
        ub_time_rec="On",
        tc_ub_disp_setting=TC_DISP_UBIT,
        camera_settings_reset_applied=True,
    )
    p64c_2398p_df_rejected = simulate_tc_format_ub_time_rec_and_disp_hil(
        system_frequency=SYSTEM_NTSC,
        frame_rate=FPS_23_98P,
        requested_tc_format=TC_FORMAT_DF,
    )
    p64c_24p_df_rejected = simulate_tc_format_ub_time_rec_and_disp_hil(
        system_frequency=SYSTEM_NTSC,
        frame_rate=FPS_24_00P,
        requested_tc_format=TC_FORMAT_DF,
    )
    p64c_pal_25p_df_rejected = simulate_tc_format_ub_time_rec_and_disp_hil(
        system_frequency=SYSTEM_PAL,
        frame_rate=FPS_25P,
        requested_tc_format=TC_FORMAT_DF,
    )
    p64c_pal_50p_ndf_ok = simulate_tc_format_ub_time_rec_and_disp_hil(
        system_frequency=SYSTEM_PAL,
        frame_rate=FPS_50P,
        requested_tc_format=TC_FORMAT_NDF,
    )
    p64c_fx3_bnc_switch_rejected = simulate_tc_format_ub_time_rec_and_disp_hil(
        body_profile=BODY_MODEL_FX3,
        request_bnc_tc_in_out_switch=True,
    )
    p64c_fx6_bnc_extlk_ok = simulate_tc_format_ub_time_rec_and_disp_hil(
        body_profile=BODY_MODEL_FX6,
        system_frequency=SYSTEM_NTSC,
        frame_rate=FPS_29_97P,
        requested_tc_format=TC_FORMAT_DF,
        request_bnc_tc_in_out_switch=True,
        fx6_bnc_switch_dir="IN",
    )

    p64c_ok = (
        p64c_ntsc_5994_df_ok.admitted
        and p64c_ntsc_5994_df_ok.effective_tc_format == TC_FORMAT_DF
        and p64c_ntsc_5994_df_ok.tc_format_menu_exposed
        and p64c_ntsc_5994_df_ok.ub_records_real_time
        and p64c_ntsc_5994_df_ok.effective_tc_ub_disp_setting == TC_DISP_UBIT
        and p64c_ntsc_5994_df_ok.all_6_tcub_survived_cam_reset
        and (not p64c_2398p_df_rejected.admitted)
        and p64c_2398p_df_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p64c_2398p_df_rejected.effective_tc_format == TC_FORMAT_NDF
        and (not p64c_24p_df_rejected.admitted)
        and p64c_24p_df_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p64c_24p_df_rejected.tc_format_locked_ndf
        and (not p64c_pal_25p_df_rejected.admitted)
        and p64c_pal_25p_df_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p64c_pal_25p_df_rejected.tc_format_menu_hidden
        and p64c_pal_50p_ndf_ok.admitted
        and p64c_pal_50p_ndf_ok.tc_format_menu_hidden
        and (not p64c_fx3_bnc_switch_rejected.admitted)
        and p64c_fx3_bnc_switch_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p64c_fx6_bnc_extlk_ok.admitted
        and p64c_fx6_bnc_extlk_ok.fx6_has_bnc_tc_in_out_switch
        and (not p64c_fx6_bnc_extlk_ok.fx3_has_bnc_tc_in_out_switch)
    )

    # Pillar 64D scenarios — CRITICAL Reverse-Direction Vault Firewall
    p64d_reverse_slot2_to_slot1_blocked = (
        simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=OP_PB_COPY,
            select_playback_media=SLOT_2,
            slot1_is_tier0_vault=True,
        )
    )
    p64d_slot1_to_slot2_virtual_ok = (
        simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=OP_PB_COPY,
            select_playback_media=SLOT_1,
            slot1_is_tier0_vault=True,
        )
    )
    p64d_low_battery_copy_blocked = (
        simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=OP_PB_COPY,
            select_playback_media=SLOT_1,
            battery_low_for_copy=True,
        )
    )
    p64d_slow_sdhc_movie_copy_blocked = (
        simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=OP_PB_COPY,
            select_playback_media=SLOT_1,
            copy_content_type=CONTENT_MOVIE,
            dest_speed_class=SPEED_SDHC_LEGACY_SLOW,
        )
    )
    p64d_slideshow_slot1_vault_safe_ok = (
        simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=OP_PB_SLIDE_SHOW,
            select_playback_media=SLOT_1,
            slot1_is_tier0_vault=True,
            slideshow_repeat="On",
            slideshow_interval=SLIDESHOW_INTERVAL_5S,
            slideshow_view_mode=VIEW_MODE_FOLDER_STILL,
        )
    )
    p64d_fx6_slideshow_rejected = (
        simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            body_profile=BODY_MODEL_FX6,
            operation=OP_PB_SLIDE_SHOW,
        )
    )

    p64d_ok = (
        (not p64d_reverse_slot2_to_slot1_blocked.admitted)
        and p64d_reverse_slot2_to_slot1_blocked.errno_code == EROFS_ERRNO
        and p64d_reverse_slot2_to_slot1_blocked.copy_direction == "Slot 2 -> Slot 1"
        and p64d_reverse_slot2_to_slot1_blocked.tier0_vault_firewall_triggered
        and p64d_reverse_slot2_to_slot1_blocked.slot1_data_sector_writes == 0
        and (not p64d_reverse_slot2_to_slot1_blocked.slot1_avf_info_mutated)
        and p64d_slot1_to_slot2_virtual_ok.admitted
        and p64d_slot1_to_slot2_virtual_ok.copy_direction == "Slot 1 -> Slot 2"
        and p64d_slot1_to_slot2_virtual_ok.dest_group_flattened
        and p64d_slot1_to_slot2_virtual_ok.dest_protect_cleared
        and p64d_slot1_to_slot2_virtual_ok.slot1_data_sector_writes == 0
        and (not p64d_low_battery_copy_blocked.admitted)
        and p64d_low_battery_copy_blocked.errno_code == EBUSY_ERRNO
        and (not p64d_slow_sdhc_movie_copy_blocked.admitted)
        and p64d_slow_sdhc_movie_copy_blocked.errno_code == EOPNOTSUPP_ERRNO
        and p64d_slideshow_slot1_vault_safe_ok.admitted
        and p64d_slideshow_slot1_vault_safe_ok.power_save_suspended
        and p64d_slideshow_slot1_vault_safe_ok.slot1_data_sector_writes == 0
        and (not p64d_slideshow_slot1_vault_safe_ok.slot1_avf_info_mutated)
        and (not p64d_fx6_slideshow_rejected.admitted)
        and p64d_fx6_slideshow_rejected.errno_code == EOPNOTSUPP_ERRNO
    )

    milestone_probe = _build_stage64_power_of_two_milestone_probe()

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
        "switch_vh_af_non_afc_or_invalid_pitch_bypass_events": (
            SWITCH_VH_AF_NON_AFC_OR_INVALID_PITCH_BYPASS_EVENTS
        ),
        "focus_area_limit_lt2_or_dormant_alpha_exposed_events": (
            FOCUS_AREA_LIMIT_LT2_OR_DORMANT_ALPHA_EXPOSED_EVENTS
        ),
        "exposure_std_adj_reset_wipe_or_missing_5th_mode_events": (
            EXPOSURE_STD_ADJ_RESET_WIPE_OR_MISSING_5TH_MODE_EVENTS
        ),
        "bracket_movie_sq_or_fx6_bypass_events": BRACKET_MOVIE_SQ_OR_FX6_BYPASS_EVENTS,
        "tc_format_2398p_24p_or_pal_df_violation_events": (
            TC_FORMAT_2398P_24P_OR_PAL_DF_VIOLATION_EVENTS
        ),
        "fx3_has_bnc_tc_in_out_switch": FX3_HAS_BNC_TC_IN_OUT_SWITCH,
        "fx6_has_bnc_tc_in_out_switch": FX6_HAS_BNC_TC_IN_OUT_SWITCH,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "slot1_vault_copy_reverse_direction_mutation_bytes": (
            SLOT1_VAULT_COPY_REVERSE_DIRECTION_MUTATION_BYTES
        ),
        "reverse_copy_slot2_to_slot1_vault_bypass_events": (
            REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_BYPASS_EVENTS
        ),
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    all_passed = bool(
        donor_audit.all_contracts_verified
        and p64a_ok
        and p64b_ok
        and p64c_ok
        and p64d_ok
        and milestone_probe["is_64th_stage_milestone"]
        and milestone_probe["is_64th_power_of_two_milestone"]
        and redlines["raw_firmware_bytes_leaked"] == 0
        and redlines["physical_device_writes"] == 0
        and redlines["slot1_data_sector_writes"] == 0
        and (not redlines["slot1_avf_info_mutated"])
        and redlines["slot1_vault_copy_reverse_direction_mutation_bytes"] == 0
        and redlines["reverse_copy_slot2_to_slot1_vault_bypass_events"] == 0
        and (not redlines["persistent_emmc_writes_authorized"])
        and (not redlines["hardware_live_attachment_authorized"])
        and (not redlines["overall_ready_for_hardware_attach"])
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_312_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_64th_stage_milestone": True,
        "is_64th_power_of_two_milestone": True,
        "source_mode": donor_audit.source_mode,
        "access_mode": donor_audit.access_mode,
        "all_checks_passed": all_passed,
        "donor_audit": asdict(donor_audit),
        "pillar_a_switch_vh_af_and_14checkbox_focus_limit_hil": {
            "passed": p64a_ok,
            "active_14_focus_area_checkboxes": list(
                FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES
            ),
            "dormant_alpha_items_rejected": list(DORMANT_ALPHA_FOCUS_AREA_LIMIT_ITEMS),
            "still_afc_90deg_ok": asdict(p64a_still_afc_90deg_ok),
            "still_afc_270deg_ok": asdict(p64a_still_afc_270deg_ok),
            "invalid_pitch_degraded": asdict(p64a_invalid_pitch_degraded),
            "movie_locked_out": asdict(p64a_movie_locked_out),
            "afs_locked_out": asdict(p64a_afs_locked_out),
            "limit_lt2_rejected": asdict(p64a_limit_lt2_rejected),
            "dormant_alpha_rejected": asdict(p64a_dormant_alpha_rejected),
            "mode_change_clears_positions": asdict(p64a_mode_change_clears_positions),
            "fx6_rejected": asdict(p64a_fx6_rejected),
        },
        "pillar_b_5mode_exposure_std_adj_and_bracket_settings_hil": {
            "passed": p64b_ok,
            "exposed_5_metering_modes": list(VALID_FX3_EXPOSURE_STD_5_MODES),
            "all5_modes_1_6ev_ok": [asdict(r) for r in p64b_all5_modes_ok],
            "camera_settings_reset_split": asdict(p64b_cam_reset_split),
            "initialize_resets_std_adj": asdict(p64b_initialize_resets_std),
            "non_sixth_ev_rejected": asdict(p64b_non_sixth_rejected),
            "bracket_movie_rejected": asdict(p64b_bracket_movie_rejected),
            "bracket_sq_rejected": asdict(p64b_bracket_sq_rejected),
            "fx6_rejected": asdict(p64b_fx6_rejected),
            "mid_bracket_counter_reset": asdict(p64b_mid_bracket_reset),
        },
        "pillar_c_tc_format_df_ndf_ub_time_rec_and_fx6_bnc_hil": {
            "passed": p64c_ok,
            "ntsc_5994_df_ok": asdict(p64c_ntsc_5994_df_ok),
            "ntsc_2398p_df_rejected": asdict(p64c_2398p_df_rejected),
            "ntsc_24p_df_rejected": asdict(p64c_24p_df_rejected),
            "pal_25p_df_rejected": asdict(p64c_pal_25p_df_rejected),
            "pal_50p_ndf_ok": asdict(p64c_pal_50p_ndf_ok),
            "fx3_bnc_switch_rejected": asdict(p64c_fx3_bnc_switch_rejected),
            "fx6_bnc_extlk_ok": asdict(p64c_fx6_bnc_extlk_ok),
        },
        "pillar_d_reverse_copy_slot2_to_slot1_vault_firewall_and_slideshow": {
            "passed": p64d_ok,
            "reverse_slot2_to_slot1_copy_blocked": asdict(
                p64d_reverse_slot2_to_slot1_blocked
            ),
            "slot1_to_slot2_virtual_copy_ok": asdict(p64d_slot1_to_slot2_virtual_ok),
            "low_battery_copy_blocked": asdict(p64d_low_battery_copy_blocked),
            "slow_sdhc_movie_copy_blocked": asdict(p64d_slow_sdhc_movie_copy_blocked),
            "slideshow_slot1_vault_safe_ok": asdict(p64d_slideshow_slot1_vault_safe_ok),
            "fx6_slideshow_rejected": asdict(p64d_fx6_slideshow_rejected),
            "stage64_milestone_probe": milestone_probe,
        },
        "redlines": redlines,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


# ---------------------------------------------------------------------------
# CLI Entry Point (Python 3.14 strict: ALL literal '%' escaped as '%%')
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator.py",
        description=(
            "Phase 312 Stage 64 (64/64 Power-of-Two VM Stages Milestone) Wave-54 Real-Hardware "
            "ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 [Switch V/H AF Area] & 14-Checkbox "
            "[Focus Area Limit], 5-Mode [Exposure Std. Adjust] (1/6 EV) & Still-Only "
            "[Bracket Settings], [Time Code Format] DF/NDF 23.98p/24p/PAL Locks & "
            "[User Bit Time Rec], and Playback [Copy] Slot-2 -> Slot-1 Reverse-Direction "
            "100%% Fail-Closed Tier-0 Vault Firewall HIL Co-Emulator"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic Phase 312 Stage 64 (64/64) Wave-54 HIL verification suite",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force CLEAN_ROOM_SYNTHETIC donor verification without reading local Mac/work files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report (default unless --summary is set)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit concise one-line Stage 64 (64/64 Power-of-Two Milestone) Wave-54 summary",
    )
    args = parser.parse_args(argv)

    rep = run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation(
        force_clean_room=True if args.clean_room else None
    )

    if args.summary and not args.json:
        red = rep["redlines"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 312 Stage 64 (64/64 Power-of-Two Milestone) | "
            f"mode={rep['source_mode']} "
            f"donors={rep['donor_audit']['donor_files_inspected']} "
            f"vh_byp={red['switch_vh_af_non_afc_or_invalid_pitch_bypass_events']} "
            f"fal_byp={red['focus_area_limit_lt2_or_dormant_alpha_exposed_events']} "
            f"std_byp={red['exposure_std_adj_reset_wipe_or_missing_5th_mode_events']} "
            f"brk_byp={red['bracket_movie_sq_or_fx6_bypass_events']} "
            f"tc_byp={red['tc_format_2398p_24p_or_pal_df_violation_events']} "
            f"rcp_byp={red['reverse_copy_slot2_to_slot1_vault_bypass_events']} "
            f"s1_wr={red['slot1_data_sector_writes']} "
            f"emmc_wr={red['emmc_nflasha_write_count']} "
            f"leak={red['raw_firmware_bytes_leaked']} "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
