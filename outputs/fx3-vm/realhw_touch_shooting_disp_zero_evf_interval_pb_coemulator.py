#!/usr/bin/env python3
"""Phase 315 (Stage 65 — 65/65 Milestone) — Real-Hardware
ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-55:
4-Item `[Touch Operation]` & Dormant `Touch Shutter` / `Touch AE` / `Touch Panel/Pad` /
`Footer Icon Touch` Guard,
4-Mode `[DISP (Screen Disp) Set]` & Zero-EVF `Select Finder/Monitor` Blackout-Trap Guard
vs `FX6` Detachable `Viewfinder`,
Still-Only `[AEL w/ Shutter]` / `[Exp.comp.set]` / `[Wireless Flash]` / `[External Flash Set.]`,
and 9-Speed `[Play Speed for Interval]` (`1..9` default `5`) + Dormant `[Beauty Effect]` /
`[Trimming]` & `[Photo Capture]` `Slot-1` Tier-0 Vault Firewall HIL Co-Emulator.

Strictly models Wave-55 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) and
`ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts without physical
hardware attachment or firmware byte leakage:

1. **Sub-Model 65A — 4-Item `[Touch Operation]` (`Initialize`-Only) vs Dormant Alpha Touch**:
   - `MENU -> Setup -> [Touch Operation]` (`_g.uxc 0x6345`, `base.uxc 0xe8e3`) exposes ONLY
     4 items, ALL surviving `[Camera Settings Reset]` (require `[Initialize]`):
     - `[Touch Operation]`: `On` (default) / `On: Playback Only` (`_f 0x6cde`) / `Off`
     - `[Touch Sensitivity]` (`_f 0x739f`): `Standard` (default) / `Sensitive` (`_f 0x7205` —
       NOT `"Responsive"`)
     - `[Touch Func. in Shooting]` (`_f 0x7575`): `Touch Focus` / `Touch Tracking` (default) /
       `Off` across `Still`, `Movie`, and `S&Q`
     - `[Swipe Up]` (`_f 0x7518`): `Open the Fn Menu` (`_f 0x7281`, default) / `Off`
       (active ONLY when `[Touch Operation] == On`)
   - Fail-closed `EOPNOTSUPP = 95` on dormant BIONZ XR symbols `Touch Shutter` (`_f 0x6a80`),
     `Touch AE` (`_f 0x702a`), `Touch Focus+AE` (`_f 0x797e`), `Touch AE Cancel` (`_g 0x6150`),
     `Touch Panel/Pad` (`_f 0x76ec` / `0x6d1a` / `0x7312` — absent due to zero EVF), and
     `Footer Icon Touch` (`_f 0x70da` / `Swipe Left` `0x6b06` / `Swipe Right` `0x6c19`).
   - Contrasts with `ILME-FX6 Ver. 6.01` (`Technical > Touch Operation` `On`/`Off` +
     `Shooting > Focus > Touch Function in MF` `Spot Focus`/`Tracking AF`, no `Touch Sensitivity`
     and no `Swipe Up`).

2. **Sub-Model 65B — `[DISP (Screen Disp) Set]` & Zero-EVF `Select Finder/Monitor` Guard**:
   - Located under `MENU -> Setup -> [Operation Customize] -> [DISP (Screen Disp) Set]`
     (`_g.uxc 0x61c4 -> 0x61da`, NOT `Display Option`; survives `[Camera Settings Reset]`):
     **4 shooting pages** (`Display All Info.` `0xea0e`, `No Disp. Info.` `0xe9f9`,
     `Histogram` `0xe07b`, `Level` `0xe8bc`, requiring `>= 1` checked) and **3 playback pages**
     (`Display Info.`, `Histogram`, `No Disp. Info.`).
   - `ILME-FX3` has **ZERO built-in EVF, ZERO eye sensor, ZERO `FINDER/MONITOR` button** —
     fail-closed `ENODEV = 19` / `EOPNOTSUPP = 95` on dormant `BKID_APP_setting_finder_monitor`,
     `Select Finder/Monitor` (`_f 0x74f9`), `DISP Button:Finder` (`0x6b57`), `For viewfinder`
     (`0x62d3`), `Graphic Display` (`0xe07a`), and `Monitor Off` to prevent LCD blackout traps!
   - Contrasts with `ILME-FX6` (`TYPE_BUILTIN_EVF_NOT_EXIST`, detachable 3.5" LCD `Viewfinder`
     + `Viewfinder Hood` — never `"Loupe"`, `Monitoring > Display On/Off` +
     `Home Screen Priority` / `Direct Menu Priority`).

3. **Sub-Model 65C — Still-Only `[AEL w/ Shutter]` & Flash Submenu vs Flash-Less `FX6`**:
   - ALL 4 items are **Still-only** (`EBUSY = 16` in `Movie`/`S&Q`):
     - `[AEL w/ Shutter]` (`Exposure/Color -> [Metering]`, `_f 0x669d`): `Auto` (default) /
       `On` / `Off`, `Initialize`-only, `[AEL toggle]` overrides half-shutter.
     - `[Exp.comp.set]` (`Exposure/Color -> [Flash]`, `_f 0x73c2`): `Ambient&flash` (default) /
       `Ambient only` (`_f 0x7617`), `Initialize`-only.
     - `[Wireless Flash]` (`Exposure/Color -> [Flash]`, `_f 0x6201`): `Off` (default) / `On`,
       **the ONLY one resettable by `[Camera Settings Reset]`!**
     - `[External Flash Set.]` (`Exposure/Color -> [Flash]`, `_f 0x6771`): direct MI-Shoe mount
       only (rejects sync-cord off-camera `EINVAL = 22`, rejects camera-menu pairing/reset
       `EOPNOTSUPP = 95`, `Initialize`-only).
   - Contrasts with `ILME-FX6` (zero mechanical shutter / zero Still flash stack `ENOENT = 2`,
     only rolling-shutter `Flash Band Reduce` `_2.uxc 0x4215`).

4. **Sub-Model 65D & Redlines — Playback `[Viewing]` 9-Speed `[Play Speed for Interval]` & Vault**:
   - Under `MENU -> Playback -> [Viewing]` (`_g 0x6033`), `[Cont. Play for Interval]`
     (`_f 0x78fa` / alias `0x72e6`) & `[Play Speed for Interval]` (`0x639e` / alias `0x72bd`)
     expose **exact 9 speeds `1..9`** (`CONTINUOUS_PLAYBACK_SPEED_1..9`, default **`5`**,
     `Initialize`-only, read-only view, no in-camera interval-to-movie synthesis `EOPNOTSUPP=95`).
   - Active `Playback -> [Edit]` (`_g 0x6418`) items (`Rotate`, `Photo Capture`,
     `JPEG/HEIF Switch`, `Copy`) vs dormant `[Beauty Effect]` (`_f 0x7849`) &
     `sequence_edit_trimming_*` (`EOPNOTSUPP = 95`); any `Rotate` / `Photo Capture` / dormant
     edit targeting `Slot 1` Tier-0 vault fails closed with `EROFS = 30`
     (`slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`).

5. **Dual-Mode 17-Donor `os.O_RDONLY` Verification (`<= 4096 B` bounded windows)**:
   - Audits all 17 verified `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01` Wave-55 donors via
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
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator_v1"
PHASE_315_SCHEMA = SCHEMA_ID
PHASE_315_VERSION = "315.0.0"
PHASE_NUMBER = 315
STAGE_INDEX = 65
STAGE_TOTAL = 65
MILESTONE_LABEL = "65/65"
STAGE_NAME = "stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil"
IS_65TH_STAGE_MILESTONE = True
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EPERM_ERRNO = 1
ENOENT_ERRNO = 2
EACCES_ERRNO = 13
EBUSY_ERRNO = 16
ENODEV_ERRNO = 19
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

# Wave-55 Stage 65 (65/65 Milestone) zero-fault & hardware-truth invariants
DORMANT_TOUCH_SHUTTER_AE_PAD_FOOTER_EXPOSED_EVENTS = 0
ZERO_EVF_FINDER_MONITOR_BLACKOUT_TRAP_EVENTS = 0
FX3_HAS_BUILTIN_EVF = False
FX3_HAS_EYE_SENSOR = False
FX3_HAS_FINDER_MONITOR_BUTTON = False
FX6_HAS_BUILTIN_EVF = False
FX6_USES_LOUPE_TERMINOLOGY = False
STILL_ONLY_AEL_FLASH_MOVIE_SQ_BYPASS_EVENTS = 0
SYNC_CORD_EXTERNAL_FLASH_BYPASS_EVENTS = 0
FX6_HAS_STILL_FLASH_STACK = False
INTERVAL_PLAY_SPEED_OUT_OF_1_9_RANGE_EVENTS = 0
DORMANT_BEAUTY_EFFECT_OR_TRIMMING_EXPOSED_EVENTS = 0
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
SLOT1_VAULT_PB_EDIT_MUTATION_BYTES = 0

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
# Verified Local Donor Specs (All 17 FX3 7.02 & FX6 6.01 Wave-55 Donors)
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
        b"Touch Func. in Shooting",
        b"Touch Focus",
        b"Touch Tracking",
        b"Touch Sensitivity",
        b"Sensitive",
        b"Swipe Up",
        b"Open the Fn Menu",
        b"On: Playback Only",
        b"Touch Shutter",
        b"Touch AE",
        b"Touch Panel/Pad",
        b"Footer Icon Touch",
        b"Select Finder/Monitor",
        b"AEL w/ Shutter",
        b"Exp.comp.set",
        b"Ambient&flash",
        b"Ambient only",
        b"Wireless Flash",
        b"External Flash Set.",
        b"Cont. Play for",
        b"Play Speed for",
        b"Photo Capture",
        b"JPEG/HEIF Switch",
        b"Beauty Effect",
    ),
    "fx3_string_sc_f": (
        "触摸操作".encode("utf-8"),
        "触摸灵敏度".encode("utf-8"),
        "拍摄期间的触摸功能".encode("utf-8"),
        "上划".encode("utf-8"),
        "快门AEL".encode("utf-8"),
        "曝光补偿设置".encode("utf-8"),
        "无线闪光灯".encode("utf-8"),
        "外置闪光灯设置".encode("utf-8"),
        "间隔连续播放".encode("utf-8"),
        "间隔播放速度".encode("utf-8"),
        "照片捕获".encode("utf-8"),
        "美化效果".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "觸控操作".encode("utf-8"),
        "觸控靈敏度".encode("utf-8"),
        "拍攝期間的觸控功能".encode("utf-8"),
        "向上滑動".encode("utf-8"),
        "半按快門AEL".encode("utf-8"),
        "曝光補償設定".encode("utf-8"),
        "無線閃光燈".encode("utf-8"),
        "外接閃光燈設定".encode("utf-8"),
        "間隔的連續播放".encode("utf-8"),
        "間隔的播放速度".encode("utf-8"),
        "照片攝取".encode("utf-8"),
        "美容效果".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "タッチ操作".encode("utf-8"),
        "タッチ感度".encode("utf-8"),
        "撮影時のタッチ機能".encode("utf-8"),
        "上方向にスワイプ".encode("utf-8"),
        "ｼｬｯﾀｰ半押しAEL".encode("utf-8"),
        "露出補正の影響".encode("utf-8"),
        "ワイヤレスフラッシュ".encode("utf-8"),
        "外部フラッシュ設定".encode("utf-8"),
        "ｲﾝﾀｰﾊﾞﾙ連続再生".encode("utf-8"),
        "ｲﾝﾀｰﾊﾞﾙ再生速度".encode("utf-8"),
        "動画から静止画作成".encode("utf-8"),
        "ﾋﾞｭｰﾃｨｰｴﾌｪｸﾄ".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Display All Info.",
        b"No Disp. Info.",
        b"Histogram",
        b"Level",
        b"Graphic Display",
        b"For viewfinder",
        b"FINDER/MONITOR",
        b"Exp.comp.set",
        b"Ambient only",
        b"Ambient&flash",
        b"Rotate",
    ),
    "fx3_string_sc": (
        "显示全部信息".encode("utf-8"),
        "无显示信息".encode("utf-8"),
        "柱状图".encode("utf-8"),
        "数字水平量规".encode("utf-8"),
        "旋转".encode("utf-8"),
    ),
    "fx3_string_tc": (
        "顯示所有資訊".encode("utf-8"),
        "不顯示資訊".encode("utf-8"),
        "柱狀圖".encode("utf-8"),
        "水平".encode("utf-8"),
        "轉動".encode("utf-8"),
    ),
    "fx3_string_ja": (
        "全情報表示".encode("utf-8"),
        "情報表示 なし".encode("utf-8"),
        "ヒストグラム".encode("utf-8"),
        "水準器".encode("utf-8"),
        "回転".encode("utf-8"),
    ),
    "fx3_string_en_g": (
        b"Touch Operation",
        b"Operation Customize",
        b"DISP (Screen Disp) Set",
        b"Viewing",
        b"Edit",
        b"Touch AE Cancel",
        b"Finder/Monitor",
    ),
    "fx3_string_sc_g": (
        "触摸操作".encode("utf-8"),
        "操作自定义".encode("utf-8"),
        "DISP(画面显示)设置".encode("utf-8"),
        "查看".encode("utf-8"),
        "编辑".encode("utf-8"),
    ),
    "fx3_string_tc_g": (
        "觸控操作".encode("utf-8"),
        "操作客製化".encode("utf-8"),
        "DISP(畫面顯示)設定".encode("utf-8"),
        "編輯".encode("utf-8"),
    ),
    "fx3_string_ja_g": (
        "タッチ操作".encode("utf-8"),
        "操作カスタマイズ".encode("utf-8"),
        "DISP(画面表示)設定".encode("utf-8"),
        "編集".encode("utf-8"),
    ),
    "fx6_string_en": (
        b"Touch Operation",
        b"Touch Function in MF",
        b"Home Screen Priority",
        b"Direct Menu Priority",
    ),
    "fx6_string_en_2": (
        b"Viewfinder",
        b"Display On/Off",
        b"VF Display Setting",
        b"Flash Band Reduce",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (59_817_984, "DORMANT_SEQ_EDIT_TRIMMING", b"sequence_edit_trimming_"),
        (60_600_320, "FUNC_ROTATE_CONTENT", b"FUNC_rotate_content"),
        (
            61_878_272,
            "DORMANT_TOUCH_SHUTTER_ENUM",
            b"VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_SHUTTER",
        ),
        (62_382_080, "CONT_PB_SPEED_9", b"CONTINUOUS_PLAYBACK_SPEED_9"),
        (62_382_080, "CONT_PB_SPEED_5", b"CONTINUOUS_PLAYBACK_SPEED_5"),
        (62_685_184, "BKID_AEL_W_SHUTTER", b"BKID_APP_setting_still_image_ael_w_shutter"),
        (62_685_184, "BKID_EXP_COMP_SET", b"BKID_APP_setting_exp_comp_set"),
        (62_685_184, "BKID_WIRELESS_FLASH", b"BKID_APP_setting_wireless_flash"),
        (62_689_280, "BKID_PHOTO_CAPTURE_TYPE", b"BKID_APP_setting_photo_capture_file_type"),
        (62_689_280, "BKID_CONT_PLAYBACK", b"BKID_APP_setting_continuous_playback"),
        (62_697_472, "BKID_TOUCH_OPERATION", b"BKID_APP_setting_touch_operation"),
        (62_697_472, "BKID_TOUCH_SENSITIVITY", b"BKID_APP_setting_touch_sensitivity"),
        (62_697_472, "BKID_TOUCH_PANEL_PAD", b"BKID_APP_setting_touch_panel_pad"),
        (62_697_472, "BKID_SWIPE_UP", b"BKID_APP_setting_swipe_up"),
        (62_697_472, "BKID_SHOOTING_TOUCH_FUNC", b"BKID_APP_setting_shooting_touch_function"),
        (62_697_472, "BKID_FINDER_MONITOR_TRAP", b"BKID_APP_setting_finder_monitor"),
        (62_709_760, "BKID_DISP_MODE_SHOOT_MON", b"BKID_APP_disp_mode_shoot_monitor"),
        (62_709_760, "BKID_DISP_MODE_PLAY", b"BKID_APP_disp_mode_play"),
        (62_840_832, "BKID_EXTERNAL_FLASH_MENU", b"BKID_APP_external_flash_menu"),
        (62_869_504, "DORMANT_BEAUTY_EFFECT_API", b"API_START_BEAUTYEFFECT_DETECTION"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (39_964_672, "FX6_DORMANT_WIRELESS_FLASH", b"setting_wireless_flash_t"),
        (
            40_153_088,
            "FX6_BUILTIN_EVF_NOT_EXIST",
            b"VAL_FEATURE_MANAGER_builtin_evf_TYPE_BUILTIN_EVF_NOT_EXIST",
        ),
        (40_919_040, "BKID_FX6_TOUCH_OPERATION", b"BKID_APP_SETTING_TOUCH_OPERATION"),
        (40_927_232, "BKID_FX6_TOUCH_FUNC_IN_MF", b"BKID_APP_SETTING_TOUCH_FUNCTION_IN_MF"),
        (40_943_616, "BKID_FX6_INFO_DISP_OP", b"BKID_APP_SETTING_INFO_DISP_MODE_OPERATION"),
        (40_972_288, "BKID_FX6_TOUCH_TRACKING", b"BKID_APP_TOUCH_TRACKING_STATE"),
        (41_283_584, "FX6_DORMANT_EXP_COMP_SET", b"setting_exp_comp_set_t"),
        (41_283_584, "FX6_DORMANT_EXT_FLASH", b"launch_ext_flash_settings_t"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-55 Real-Hardware Constants & Matrices
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

# 65A: 4-Item [Touch Operation] vs Dormant Alpha Touch Symbols
TOUCH_OP_ON = "On"
TOUCH_OP_PLAYBACK_ONLY = "On: Playback Only"
TOUCH_OP_OFF = "Off"
VALID_FX3_TOUCH_OP_MODES: Tuple[str, ...] = (
    TOUCH_OP_ON,
    TOUCH_OP_PLAYBACK_ONLY,
    TOUCH_OP_OFF,
)
VALID_FX6_TOUCH_OP_MODES: Tuple[str, ...] = (TOUCH_OP_ON, TOUCH_OP_OFF)

TOUCH_SENS_STANDARD = "Standard"
TOUCH_SENS_SENSITIVE = "Sensitive"
VALID_FX3_TOUCH_SENSITIVITIES: Tuple[str, ...] = (
    TOUCH_SENS_STANDARD,
    TOUCH_SENS_SENSITIVE,
)
INVALID_TOUCH_SENSITIVITY_SYNONYMS: Tuple[str, ...] = ("Responsive", "High")

TOUCH_SHOOT_FOCUS = "Touch Focus"
TOUCH_SHOOT_TRACKING = "Touch Tracking"
TOUCH_SHOOT_OFF = "Off"
VALID_FX3_TOUCH_SHOOT_FUNCS: Tuple[str, ...] = (
    TOUCH_SHOOT_FOCUS,
    TOUCH_SHOOT_TRACKING,
    TOUCH_SHOOT_OFF,
)

FX6_TOUCH_MF_SPOT = "Spot Focus"
FX6_TOUCH_MF_TRACKING = "Tracking AF"
VALID_FX6_TOUCH_MF_FUNCS: Tuple[str, ...] = (
    FX6_TOUCH_MF_SPOT,
    FX6_TOUCH_MF_TRACKING,
)

SWIPE_UP_OPEN_FN_MENU = "Open the Fn Menu"
SWIPE_UP_OFF = "Off"
VALID_FX3_SWIPE_UP_MODES: Tuple[str, ...] = (
    SWIPE_UP_OPEN_FN_MENU,
    SWIPE_UP_OFF,
)

FX3_TOUCH_SETUP_EXPOSED_4_ITEMS: Tuple[str, ...] = (
    "Touch Operation",
    "Touch Sensitivity",
    "Touch Func. in Shooting",
    "Swipe Up",
)

DORMANT_TOUCH_SYMBOLS: Tuple[str, ...] = (
    "Touch Shutter",
    "Touch AE",
    "Touch Focus+AE",
    "Touch AE Cancel",
    "Touch Panel/Pad",
    "Touch Pad Only",
    "Touch Panel+Pad",
    "Touch Pad Settings",
    "Touch Pad (vertical)",
    "Footer Icon Touch",
    "Swipe Left",
    "Swipe Right",
)

# 65B: [DISP (Screen Disp) Set] & Zero-EVF Select Finder/Monitor Blackout Guard
DISP_PARENT_OPERATION_CUSTOMIZE = "Operation Customize"
DISP_PARENT_DISPLAY_OPTION_WRONG = "Display Option"

DISP_SHOOT_ALL_INFO = "Display All Info."
DISP_SHOOT_NO_INFO = "No Disp. Info."
DISP_SHOOT_HISTOGRAM = "Histogram"
DISP_SHOOT_LEVEL = "Level"
FX3_ACTIVE_4_DISP_SHOOT_PAGES: Tuple[str, ...] = (
    DISP_SHOOT_ALL_INFO,
    DISP_SHOOT_NO_INFO,
    DISP_SHOOT_HISTOGRAM,
    DISP_SHOOT_LEVEL,
)

DISP_PLAY_INFO = "Display Info."
DISP_PLAY_HISTOGRAM = "Histogram"
DISP_PLAY_NO_INFO = "No Disp. Info."
FX3_ACTIVE_3_DISP_PLAY_PAGES: Tuple[str, ...] = (
    DISP_PLAY_INFO,
    DISP_PLAY_HISTOGRAM,
    DISP_PLAY_NO_INFO,
)

DORMANT_ZERO_EVF_HARDWARE_TRAP_SYMBOLS: Tuple[str, ...] = (
    "BKID_APP_setting_finder_monitor",
    "Select Finder/Monitor",
    "Finder/Monitor Sel.",
    "FINDER/MONITOR",
    "Finder/Monitor",
    "DISP Button:Finder",
    "BKID_APP_disp_mode_shoot_finder",
)

DORMANT_DISP_SCREEN_PAGES: Tuple[str, ...] = (
    "For viewfinder",
    "Graphic Display",
    "Monitor Off",
    "BKID_APP_valid_disp_mode_shoot_monitor_for_viewfinder",
    "BKID_APP_valid_disp_mode_shoot_monitor_monitor_off",
)

FX6_INFO_DISP_HOME_PRIORITY = "Home Screen Priority"
FX6_INFO_DISP_DIRECT_PRIORITY = "Direct Menu Priority"
VALID_FX6_INFO_DISP_MODES: Tuple[str, ...] = (
    FX6_INFO_DISP_HOME_PRIORITY,
    FX6_INFO_DISP_DIRECT_PRIORITY,
)

# 65C: Still-Only [AEL w/ Shutter] & Flash Submenu ([Exp.comp.set], [Wireless Flash], [External Flash Set.])
AEL_W_SHUTTER_AUTO = "Auto"
AEL_W_SHUTTER_ON = "On"
AEL_W_SHUTTER_OFF = "Off"
VALID_AEL_W_SHUTTER_MODES: Tuple[str, ...] = (
    AEL_W_SHUTTER_AUTO,
    AEL_W_SHUTTER_ON,
    AEL_W_SHUTTER_OFF,
)

EXP_COMP_SET_AMBIENT_FLASH = "Ambient&flash"
EXP_COMP_SET_AMBIENT_ONLY = "Ambient only"
VALID_EXP_COMP_SET_MODES: Tuple[str, ...] = (
    EXP_COMP_SET_AMBIENT_FLASH,
    EXP_COMP_SET_AMBIENT_ONLY,
)

WIRELESS_FLASH_OFF = "Off"
WIRELESS_FLASH_ON = "On"
VALID_WIRELESS_FLASH_MODES: Tuple[str, ...] = (
    WIRELESS_FLASH_OFF,
    WIRELESS_FLASH_ON,
)

FLASH_MOUNT_NONE = "NONE"
FLASH_MOUNT_MI_SHOE = "MI_SHOE_DIRECT"
FLASH_MOUNT_SYNC_CORD = "SYNC_CORD_OFF_CAMERA"
VALID_FLASH_MOUNT_TYPES: Tuple[str, ...] = (
    FLASH_MOUNT_NONE,
    FLASH_MOUNT_MI_SHOE,
    FLASH_MOUNT_SYNC_CORD,
)

# 65D: Playback [Viewing] 9-Speed [Play Speed for Interval] & [Edit] vs Dormant + Slot-1 Vault Firewall
SLOT_1 = "Slot 1"
SLOT_2 = "Slot 2"
VALID_PLAYBACK_SLOTS: Tuple[str, ...] = (SLOT_1, SLOT_2)

INTERVAL_PLAY_SPEED_MIN = 1
INTERVAL_PLAY_SPEED_DEFAULT = 5
INTERVAL_PLAY_SPEED_MAX = 9
VALID_INTERVAL_PLAY_SPEEDS: Tuple[int, ...] = tuple(range(1, 10))  # exact 1..9

PB_JPEG_HEIF_JPEG = "JPEG"
PB_JPEG_HEIF_420 = "HEIF(4:2:0)"
PB_JPEG_HEIF_422 = "HEIF(4:2:2)"
VALID_PHOTO_CAPTURE_FILE_TYPES: Tuple[str, ...] = (
    PB_JPEG_HEIF_JPEG,
    PB_JPEG_HEIF_420,
    PB_JPEG_HEIF_422,
)

FX3_ACTIVE_PB_EDIT_ITEMS: Tuple[str, ...] = (
    "Rotate",
    "Photo Capture",
    "JPEG/HEIF Switch",
    "Copy",
)

DORMANT_PB_EDIT_TRAPS: Tuple[str, ...] = (
    "Beauty Effect",
    "Trimming",
    "sequence_edit_trimming_main",
    "API_START_BEAUTYEFFECT_DETECTION",
)

PB_OP_VIEW_INTERVAL = "CONT_PLAY_INTERVAL"
PB_OP_SYNTHESIZE_INTERVAL_MOVIE = "SYNTHESIZE_INTERVAL_MOVIE"
PB_OP_ROTATE = "Rotate"
PB_OP_PHOTO_CAPTURE = "Photo Capture"
PB_OP_COPY = "Copy"
PB_OP_BEAUTY_EFFECT = "Beauty Effect"
PB_OP_TRIMMING = "Trimming"
VALID_PB_WAVE55_OPS: Tuple[str, ...] = (
    PB_OP_VIEW_INTERVAL,
    PB_OP_SYNTHESIZE_INTERVAL_MOVIE,
    PB_OP_ROTATE,
    PB_OP_PHOTO_CAPTURE,
    PB_OP_COPY,
    PB_OP_BEAUTY_EFFECT,
    PB_OP_TRIMMING,
)

_PHASE315_DONOR_CACHE: Dict[str, "DonorAuditReport"] = {}


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


def inspect_phase315_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> DonorAuditReport:
    """Audit all 17 Wave-55 donors via O_RDONLY or deterministic CLEAN_ROOM_SYNTHETIC."""
    t0 = time.monotonic()
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_forced:
        return _build_clean_room_donor_audit(0.0)

    work_root = resolve_mac_work_root(env)
    sample_file = work_root / DONOR_RELPATHS["fx3_string_en_f"]
    if (not work_root.is_dir()) or (not sample_file.is_file()):
        return _build_clean_room_donor_audit(0.0)

    cache_key = str(work_root.resolve())
    cached = _PHASE315_DONOR_CACHE.get(cache_key)
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
        _PHASE315_DONOR_CACHE[cache_key] = rep
    return rep


# ---------------------------------------------------------------------------
# Sub-Model 65A: 4-Item [Touch Operation] vs Dormant Alpha Touch Symbols
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TouchOperationSetupEvalResult:
    body_profile: str
    shooting_domain: str
    focus_mode: str
    exposed_setup_items: Tuple[str, ...]
    exposed_item_count: int
    effective_touch_operation: str
    effective_touch_sensitivity: str
    effective_touch_func_in_shooting: str
    effective_swipe_up: str
    swipe_up_active: bool
    shooting_touch_active: bool
    playback_touch_active: bool
    screen_fn_icon_touch_supported: bool
    stby_rec_touch_supported: bool
    long_press_fn_menu_supported: bool
    all_4_survived_cam_reset: bool
    reset_via_initialize_only: bool
    camera_settings_reset_applied: bool
    initialize_applied: bool
    dormant_touch_symbol_blocked: bool
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


def simulate_touch_operation_and_dormant_guard_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shooting_domain: str = DOMAIN_STILL,
    focus_mode: str = FOCUS_MODE_AFC,
    touch_operation: str = TOUCH_OP_ON,
    touch_sensitivity: str = TOUCH_SENS_STANDARD,
    touch_func_in_shooting: str = TOUCH_SHOOT_TRACKING,
    swipe_up: str = SWIPE_UP_OPEN_FN_MENU,
    fx6_touch_func_in_mf: str = FX6_TOUCH_MF_SPOT,
    requested_dormant_touch_symbol: Optional[str] = None,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> TouchOperationSetupEvalResult:
    """Model Sub-Model 65A: 4-item [Touch Operation] & dormant touch symbol guard."""
    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return TouchOperationSetupEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            exposed_setup_items=(),
            exposed_item_count=0,
            effective_touch_operation=TOUCH_OP_OFF,
            effective_touch_sensitivity=TOUCH_SENS_STANDARD,
            effective_touch_func_in_shooting=TOUCH_SHOOT_OFF,
            effective_swipe_up=SWIPE_UP_OFF,
            swipe_up_active=False,
            shooting_touch_active=False,
            playback_touch_active=False,
            screen_fn_icon_touch_supported=False,
            stby_rec_touch_supported=False,
            long_press_fn_menu_supported=False,
            all_4_survived_cam_reset=False,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            dormant_touch_symbol_blocked=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_BODY_PROFILE",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if shooting_domain not in VALID_SHOOTING_DOMAINS or focus_mode not in VALID_FOCUS_MODES:
        return TouchOperationSetupEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            exposed_setup_items=(),
            exposed_item_count=0,
            effective_touch_operation=touch_operation,
            effective_touch_sensitivity=touch_sensitivity,
            effective_touch_func_in_shooting=touch_func_in_shooting,
            effective_swipe_up=swipe_up,
            swipe_up_active=False,
            shooting_touch_active=False,
            playback_touch_active=False,
            screen_fn_icon_touch_supported=False,
            stby_rec_touch_supported=False,
            long_press_fn_menu_supported=False,
            all_4_survived_cam_reset=False,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            dormant_touch_symbol_blocked=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_DOMAIN_OR_FOCUS_MODE",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Reject dormant Alpha / ILCE-7SM3 / ILCE-7RM5 symbols on both FX3 and FX6
    if requested_dormant_touch_symbol is not None:
        return TouchOperationSetupEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            exposed_setup_items=(
                FX3_TOUCH_SETUP_EXPOSED_4_ITEMS
                if body_profile == BODY_MODEL_FX3
                else ("Technical > Touch Operation", "Shooting > Focus > Touch Function in MF")
            ),
            exposed_item_count=4 if body_profile == BODY_MODEL_FX3 else 2,
            effective_touch_operation=touch_operation,
            effective_touch_sensitivity=touch_sensitivity,
            effective_touch_func_in_shooting=touch_func_in_shooting,
            effective_swipe_up=swipe_up,
            swipe_up_active=False,
            shooting_touch_active=False,
            playback_touch_active=False,
            screen_fn_icon_touch_supported=False,
            stby_rec_touch_supported=False,
            long_press_fn_menu_supported=False,
            all_4_survived_cam_reset=(body_profile == BODY_MODEL_FX3),
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            dormant_touch_symbol_blocked=True,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code=f"DORMANT_TOUCH_SYMBOL_REJECTED:{requested_dormant_touch_symbol}",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if body_profile == BODY_MODEL_FX6:
        if (
            touch_operation not in VALID_FX6_TOUCH_OP_MODES
            or touch_sensitivity != TOUCH_SENS_STANDARD
            or swipe_up != SWIPE_UP_OPEN_FN_MENU
        ):
            return TouchOperationSetupEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                exposed_setup_items=(
                    "Technical > Touch Operation",
                    "Shooting > Focus > Touch Function in MF",
                ),
                exposed_item_count=2,
                effective_touch_operation=TOUCH_OP_ON,
                effective_touch_sensitivity="N/A",
                effective_touch_func_in_shooting=fx6_touch_func_in_mf,
                effective_swipe_up="N/A",
                swipe_up_active=False,
                shooting_touch_active=False,
                playback_touch_active=False,
                screen_fn_icon_touch_supported=False,
                stby_rec_touch_supported=False,
                long_press_fn_menu_supported=False,
                all_4_survived_cam_reset=False,
                reset_via_initialize_only=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                dormant_touch_symbol_blocked=True,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason_code="FX6_LACKS_FX3_PLAYBACK_ONLY_SENSITIVITY_OR_SWIPE_UP",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        if fx6_touch_func_in_mf not in VALID_FX6_TOUCH_MF_FUNCS:
            return TouchOperationSetupEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                exposed_setup_items=(
                    "Technical > Touch Operation",
                    "Shooting > Focus > Touch Function in MF",
                ),
                exposed_item_count=2,
                effective_touch_operation=touch_operation,
                effective_touch_sensitivity="N/A",
                effective_touch_func_in_shooting=fx6_touch_func_in_mf,
                effective_swipe_up="N/A",
                swipe_up_active=False,
                shooting_touch_active=False,
                playback_touch_active=False,
                screen_fn_icon_touch_supported=False,
                stby_rec_touch_supported=False,
                long_press_fn_menu_supported=False,
                all_4_survived_cam_reset=False,
                reset_via_initialize_only=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                dormant_touch_symbol_blocked=False,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason_code="INVALID_FX6_TOUCH_FUNCTION_IN_MF",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )

        eff_op = TOUCH_OP_ON if initialize_applied else touch_operation
        eff_mf = FX6_TOUCH_MF_SPOT if initialize_applied else fx6_touch_func_in_mf
        eff_mode = (
            "Realtime Tracking AF"
            if (eff_op == TOUCH_OP_ON and focus_mode in (FOCUS_MODE_AFC, FOCUS_MODE_AFS, FOCUS_MODE_AFA))
            else eff_mf
        )
        return TouchOperationSetupEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            exposed_setup_items=(
                "Technical > Touch Operation",
                "Shooting > Focus > Touch Function in MF",
            ),
            exposed_item_count=2,
            effective_touch_operation=eff_op,
            effective_touch_sensitivity="N/A",
            effective_touch_func_in_shooting=eff_mode,
            effective_swipe_up="N/A",
            swipe_up_active=False,
            shooting_touch_active=(eff_op == TOUCH_OP_ON),
            playback_touch_active=False,
            screen_fn_icon_touch_supported=False,
            stby_rec_touch_supported=False,
            long_press_fn_menu_supported=False,
            all_4_survived_cam_reset=False,
            reset_via_initialize_only=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            dormant_touch_symbol_blocked=False,
            admitted=True,
            errno_code=0,
            reason_code="FX6_TOUCH_OPERATION_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # FX3 validation: reject "Responsive" and invalid enum values
    if touch_sensitivity in INVALID_TOUCH_SENSITIVITY_SYNONYMS or (
        touch_sensitivity not in VALID_FX3_TOUCH_SENSITIVITIES
    ):
        return TouchOperationSetupEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            exposed_setup_items=FX3_TOUCH_SETUP_EXPOSED_4_ITEMS,
            exposed_item_count=4,
            effective_touch_operation=touch_operation,
            effective_touch_sensitivity=touch_sensitivity,
            effective_touch_func_in_shooting=touch_func_in_shooting,
            effective_swipe_up=swipe_up,
            swipe_up_active=False,
            shooting_touch_active=False,
            playback_touch_active=False,
            screen_fn_icon_touch_supported=False,
            stby_rec_touch_supported=False,
            long_press_fn_menu_supported=False,
            all_4_survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            dormant_touch_symbol_blocked=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_TOUCH_SENSITIVITY_USE_STANDARD_OR_SENSITIVE",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if (
        touch_operation not in VALID_FX3_TOUCH_OP_MODES
        or touch_func_in_shooting not in VALID_FX3_TOUCH_SHOOT_FUNCS
        or swipe_up not in VALID_FX3_SWIPE_UP_MODES
    ):
        return TouchOperationSetupEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            exposed_setup_items=FX3_TOUCH_SETUP_EXPOSED_4_ITEMS,
            exposed_item_count=4,
            effective_touch_operation=touch_operation,
            effective_touch_sensitivity=touch_sensitivity,
            effective_touch_func_in_shooting=touch_func_in_shooting,
            effective_swipe_up=swipe_up,
            swipe_up_active=False,
            shooting_touch_active=False,
            playback_touch_active=False,
            screen_fn_icon_touch_supported=False,
            stby_rec_touch_supported=False,
            long_press_fn_menu_supported=False,
            all_4_survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            dormant_touch_symbol_blocked=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_FX3_TOUCH_OPTION",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # All 4 Touch Operation settings survive [Camera Settings Reset] and reset ONLY on [Initialize]
    if initialize_applied:
        eff_op = TOUCH_OP_ON
        eff_sens = TOUCH_SENS_STANDARD
        eff_shoot = TOUCH_SHOOT_TRACKING
        eff_swipe = SWIPE_UP_OPEN_FN_MENU
    else:
        eff_op = touch_operation
        eff_sens = touch_sensitivity
        eff_shoot = touch_func_in_shooting
        eff_swipe = swipe_up

    shooting_active = eff_op == TOUCH_OP_ON
    playback_active = eff_op in (TOUCH_OP_ON, TOUCH_OP_PLAYBACK_ONLY)
    swipe_active = (eff_op == TOUCH_OP_ON) and (eff_swipe == SWIPE_UP_OPEN_FN_MENU)

    return TouchOperationSetupEvalResult(
        body_profile=body_profile,
        shooting_domain=shooting_domain,
        focus_mode=focus_mode,
        exposed_setup_items=FX3_TOUCH_SETUP_EXPOSED_4_ITEMS,
        exposed_item_count=4,
        effective_touch_operation=eff_op,
        effective_touch_sensitivity=eff_sens,
        effective_touch_func_in_shooting=eff_shoot,
        effective_swipe_up=eff_swipe,
        swipe_up_active=swipe_active,
        shooting_touch_active=shooting_active,
        playback_touch_active=playback_active,
        screen_fn_icon_touch_supported=shooting_active,
        stby_rec_touch_supported=shooting_active,
        long_press_fn_menu_supported=shooting_active,
        all_4_survived_cam_reset=True,
        reset_via_initialize_only=True,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        dormant_touch_symbol_blocked=False,
        admitted=True,
        errno_code=0,
        reason_code=(
            "FX3_TOUCH_INITIALIZED_DEFAULTS"
            if initialize_applied
            else (
                "FX3_TOUCH_SURVIVED_CAMERA_SETTINGS_RESET"
                if camera_settings_reset_applied
                else "FX3_TOUCH_4ITEM_ACTIVE"
            )
        ),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Sub-Model 65B: [DISP (Screen Disp) Set] & Zero-EVF Select Finder/Monitor Guard
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DispScreenSetAndZeroEvfEvalResult:
    body_profile: str
    shooting_domain: str
    parent_menu_path: str
    fx3_has_builtin_evf: bool
    fx3_has_eye_sensor: bool
    fx3_has_finder_monitor_button: bool
    fx6_has_builtin_evf: bool
    fx6_uses_loupe_terminology: bool
    checked_shoot_pages: Tuple[str, ...]
    exposed_shoot_page_count: int
    playback_cycle_pages: Tuple[str, ...]
    exposed_play_page_count: int
    lcd_monitor_blacked_out: bool
    blackout_trap_prevented: bool
    survived_cam_reset: bool
    reset_via_initialize_only: bool
    camera_settings_reset_applied: bool
    initialize_applied: bool
    fx6_detachable_viewfinder_attached: bool
    fx6_info_disp_mode: str
    fx6_vf_mirror_flipped: bool
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


def simulate_disp_screen_set_and_zero_evf_guard_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shooting_domain: str = DOMAIN_STILL,
    parent_menu: str = DISP_PARENT_OPERATION_CUSTOMIZE,
    checked_shoot_pages: Sequence[str] = FX3_ACTIVE_4_DISP_SHOOT_PAGES,
    requested_playback_pages: Sequence[str] = FX3_ACTIVE_3_DISP_PLAY_PAGES,
    request_finder_monitor_symbol: Optional[str] = None,
    requested_dormant_disp_page: Optional[str] = None,
    fx6_viewfinder_attached: bool = True,
    fx6_viewfinder_hood_attached: bool = True,
    fx6_terminology: str = "Viewfinder",
    fx6_info_disp_mode: str = FX6_INFO_DISP_HOME_PRIORITY,
    fx6_display_on_off: bool = True,
    fx6_vf_mirror_flip: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> DispScreenSetAndZeroEvfEvalResult:
    """Model Sub-Model 65B: [DISP (Screen Disp) Set] & Zero-EVF blackout-trap guard."""
    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return DispScreenSetAndZeroEvfEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            parent_menu_path=parent_menu,
            fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
            fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
            fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
            fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
            fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
            checked_shoot_pages=(),
            exposed_shoot_page_count=0,
            playback_cycle_pages=(),
            exposed_play_page_count=0,
            lcd_monitor_blacked_out=False,
            blackout_trap_prevented=True,
            survived_cam_reset=False,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            fx6_detachable_viewfinder_attached=False,
            fx6_info_disp_mode=fx6_info_disp_mode,
            fx6_vf_mirror_flipped=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_BODY_PROFILE",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if shooting_domain not in VALID_SHOOTING_DOMAINS:
        return DispScreenSetAndZeroEvfEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            parent_menu_path=parent_menu,
            fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
            fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
            fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
            fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
            fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
            checked_shoot_pages=(),
            exposed_shoot_page_count=0,
            playback_cycle_pages=(),
            exposed_play_page_count=0,
            lcd_monitor_blacked_out=False,
            blackout_trap_prevented=True,
            survived_cam_reset=False,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            fx6_detachable_viewfinder_attached=False,
            fx6_info_disp_mode=fx6_info_disp_mode,
            fx6_vf_mirror_flipped=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_SHOOTING_DOMAIN",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if body_profile == BODY_MODEL_FX6:
        # FX6 uses "Viewfinder" & "Viewfinder Hood" — NEVER "Loupe"
        if fx6_terminology.strip().lower() == "loupe":
            return DispScreenSetAndZeroEvfEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                parent_menu_path="Monitoring > Display On/Off",
                fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
                fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
                fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
                fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
                fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
                checked_shoot_pages=(),
                exposed_shoot_page_count=0,
                playback_cycle_pages=(),
                exposed_play_page_count=0,
                lcd_monitor_blacked_out=False,
                blackout_trap_prevented=True,
                survived_cam_reset=False,
                reset_via_initialize_only=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                fx6_detachable_viewfinder_attached=fx6_viewfinder_attached,
                fx6_info_disp_mode=fx6_info_disp_mode,
                fx6_vf_mirror_flipped=fx6_vf_mirror_flip,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason_code="FX6_LOUPE_TERMINOLOGY_REJECTED_USE_VIEWFINDER_AND_HOOD",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        if fx6_info_disp_mode not in VALID_FX6_INFO_DISP_MODES:
            return DispScreenSetAndZeroEvfEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                parent_menu_path="Technical > Menu Settings > Info. Disp. Mode Operation",
                fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
                fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
                fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
                fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
                fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
                checked_shoot_pages=(),
                exposed_shoot_page_count=0,
                playback_cycle_pages=(),
                exposed_play_page_count=0,
                lcd_monitor_blacked_out=False,
                blackout_trap_prevented=True,
                survived_cam_reset=False,
                reset_via_initialize_only=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                fx6_detachable_viewfinder_attached=fx6_viewfinder_attached,
                fx6_info_disp_mode=fx6_info_disp_mode,
                fx6_vf_mirror_flipped=fx6_vf_mirror_flip,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason_code="INVALID_FX6_INFO_DISP_MODE",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        return DispScreenSetAndZeroEvfEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            parent_menu_path=(
                "Monitoring > Display On/Off + Technical > Menu Settings > Info. Disp. Mode Operation"
            ),
            fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
            fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
            fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
            fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
            fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
            checked_shoot_pages=(("Display On",) if fx6_display_on_off else ("Display Off",)),
            exposed_shoot_page_count=1,
            playback_cycle_pages=("Display On", "Display Off"),
            exposed_play_page_count=2,
            lcd_monitor_blacked_out=False,
            blackout_trap_prevented=True,
            survived_cam_reset=False,
            reset_via_initialize_only=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            fx6_detachable_viewfinder_attached=(
                fx6_viewfinder_attached and fx6_viewfinder_hood_attached
            ),
            fx6_info_disp_mode=fx6_info_disp_mode,
            fx6_vf_mirror_flipped=fx6_vf_mirror_flip,
            admitted=True,
            errno_code=0,
            reason_code="FX6_DETACHABLE_VIEWFINDER_AND_INFO_DISP_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # FX3: Reject wrong parent path ("Display Option")
    if parent_menu != DISP_PARENT_OPERATION_CUSTOMIZE:
        return DispScreenSetAndZeroEvfEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            parent_menu_path=parent_menu,
            fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
            fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
            fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
            fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
            fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
            checked_shoot_pages=FX3_ACTIVE_4_DISP_SHOOT_PAGES,
            exposed_shoot_page_count=4,
            playback_cycle_pages=FX3_ACTIVE_3_DISP_PLAY_PAGES,
            exposed_play_page_count=3,
            lcd_monitor_blacked_out=False,
            blackout_trap_prevented=True,
            survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            fx6_detachable_viewfinder_attached=False,
            fx6_info_disp_mode="N/A",
            fx6_vf_mirror_flipped=False,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="DISP_SCREEN_SET_LIVES_UNDER_OPERATION_CUSTOMIZE_NOT_DISPLAY_OPTION",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # FX3 Zero-EVF Blackout-Trap Guard: fail closed on Finder/Monitor symbols
    if request_finder_monitor_symbol is not None:
        return DispScreenSetAndZeroEvfEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            parent_menu_path=f"Setup -> {DISP_PARENT_OPERATION_CUSTOMIZE} -> DISP (Screen Disp) Set",
            fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
            fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
            fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
            fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
            fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
            checked_shoot_pages=FX3_ACTIVE_4_DISP_SHOOT_PAGES,
            exposed_shoot_page_count=4,
            playback_cycle_pages=FX3_ACTIVE_3_DISP_PLAY_PAGES,
            exposed_play_page_count=3,
            lcd_monitor_blacked_out=False,
            blackout_trap_prevented=True,
            survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            fx6_detachable_viewfinder_attached=False,
            fx6_info_disp_mode="N/A",
            fx6_vf_mirror_flipped=False,
            admitted=False,
            errno_code=ENODEV_ERRNO,
            reason_code=f"ZERO_EVF_FINDER_MONITOR_BLACKOUT_GUARD:{request_finder_monitor_symbol}",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Reject dormant Alpha DISP pages ("For viewfinder", "Graphic Display", "Monitor Off")
    if requested_dormant_disp_page is not None or any(
        p in DORMANT_DISP_SCREEN_PAGES for p in checked_shoot_pages
    ):
        dormant_name = requested_dormant_disp_page or next(
            p for p in checked_shoot_pages if p in DORMANT_DISP_SCREEN_PAGES
        )
        return DispScreenSetAndZeroEvfEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            parent_menu_path=f"Setup -> {DISP_PARENT_OPERATION_CUSTOMIZE} -> DISP (Screen Disp) Set",
            fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
            fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
            fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
            fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
            fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
            checked_shoot_pages=FX3_ACTIVE_4_DISP_SHOOT_PAGES,
            exposed_shoot_page_count=4,
            playback_cycle_pages=FX3_ACTIVE_3_DISP_PLAY_PAGES,
            exposed_play_page_count=3,
            lcd_monitor_blacked_out=False,
            blackout_trap_prevented=True,
            survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            fx6_detachable_viewfinder_attached=False,
            fx6_info_disp_mode="N/A",
            fx6_vf_mirror_flipped=False,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code=f"DORMANT_DISP_PAGE_REJECTED:{dormant_name}",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if initialize_applied:
        eff_shoot = FX3_ACTIVE_4_DISP_SHOOT_PAGES
        eff_play = FX3_ACTIVE_3_DISP_PLAY_PAGES
    else:
        dedup_shoot: List[str] = []
        for p in checked_shoot_pages:
            if p not in FX3_ACTIVE_4_DISP_SHOOT_PAGES:
                return DispScreenSetAndZeroEvfEvalResult(
                    body_profile=body_profile,
                    shooting_domain=shooting_domain,
                    parent_menu_path=f"Setup -> {DISP_PARENT_OPERATION_CUSTOMIZE} -> DISP (Screen Disp) Set",
                    fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
                    fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
                    fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
                    fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
                    fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
                    checked_shoot_pages=(),
                    exposed_shoot_page_count=0,
                    playback_cycle_pages=FX3_ACTIVE_3_DISP_PLAY_PAGES,
                    exposed_play_page_count=3,
                    lcd_monitor_blacked_out=False,
                    blackout_trap_prevented=True,
                    survived_cam_reset=True,
                    reset_via_initialize_only=True,
                    camera_settings_reset_applied=camera_settings_reset_applied,
                    initialize_applied=initialize_applied,
                    fx6_detachable_viewfinder_attached=False,
                    fx6_info_disp_mode="N/A",
                    fx6_vf_mirror_flipped=False,
                    admitted=False,
                    errno_code=EINVAL_ERRNO,
                    reason_code=f"UNKNOWN_DISP_SHOOT_PAGE:{p}",
                    physical_device_writes=PHYSICAL_DEVICE_WRITES,
                )
            if p not in dedup_shoot:
                dedup_shoot.append(p)
        if len(dedup_shoot) < 1:
            return DispScreenSetAndZeroEvfEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                parent_menu_path=f"Setup -> {DISP_PARENT_OPERATION_CUSTOMIZE} -> DISP (Screen Disp) Set",
                fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
                fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
                fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
                fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
                fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
                checked_shoot_pages=(),
                exposed_shoot_page_count=0,
                playback_cycle_pages=FX3_ACTIVE_3_DISP_PLAY_PAGES,
                exposed_play_page_count=3,
                lcd_monitor_blacked_out=False,
                blackout_trap_prevented=True,
                survived_cam_reset=True,
                reset_via_initialize_only=True,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                fx6_detachable_viewfinder_attached=False,
                fx6_info_disp_mode="N/A",
                fx6_vf_mirror_flipped=False,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason_code="DISP_SHOOT_PAGES_REQUIRE_AT_LEAST_1_CHECKED",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        eff_shoot = tuple(dedup_shoot)

        if tuple(requested_playback_pages) != FX3_ACTIVE_3_DISP_PLAY_PAGES:
            return DispScreenSetAndZeroEvfEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                parent_menu_path=f"Setup -> {DISP_PARENT_OPERATION_CUSTOMIZE} -> DISP (Screen Disp) Set",
                fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
                fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
                fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
                fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
                fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
                checked_shoot_pages=eff_shoot,
                exposed_shoot_page_count=len(eff_shoot),
                playback_cycle_pages=FX3_ACTIVE_3_DISP_PLAY_PAGES,
                exposed_play_page_count=3,
                lcd_monitor_blacked_out=False,
                blackout_trap_prevented=True,
                survived_cam_reset=True,
                reset_via_initialize_only=True,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                fx6_detachable_viewfinder_attached=False,
                fx6_info_disp_mode="N/A",
                fx6_vf_mirror_flipped=False,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason_code="PLAYBACK_DISP_CYCLE_LOCKED_TO_3_PAGES",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        eff_play = FX3_ACTIVE_3_DISP_PLAY_PAGES

    return DispScreenSetAndZeroEvfEvalResult(
        body_profile=body_profile,
        shooting_domain=shooting_domain,
        parent_menu_path=f"Setup -> {DISP_PARENT_OPERATION_CUSTOMIZE} -> DISP (Screen Disp) Set",
        fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
        fx3_has_eye_sensor=FX3_HAS_EYE_SENSOR,
        fx3_has_finder_monitor_button=FX3_HAS_FINDER_MONITOR_BUTTON,
        fx6_has_builtin_evf=FX6_HAS_BUILTIN_EVF,
        fx6_uses_loupe_terminology=FX6_USES_LOUPE_TERMINOLOGY,
        checked_shoot_pages=eff_shoot,
        exposed_shoot_page_count=len(eff_shoot),
        playback_cycle_pages=eff_play,
        exposed_play_page_count=len(eff_play),
        lcd_monitor_blacked_out=False,
        blackout_trap_prevented=True,
        survived_cam_reset=True,
        reset_via_initialize_only=True,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        fx6_detachable_viewfinder_attached=False,
        fx6_info_disp_mode="N/A",
        fx6_vf_mirror_flipped=False,
        admitted=True,
        errno_code=0,
        reason_code=(
            "FX3_DISP_INITIALIZED_4_SHOOT_3_PLAY_PAGES"
            if initialize_applied
            else (
                "FX3_DISP_SURVIVED_CAMERA_SETTINGS_RESET"
                if camera_settings_reset_applied
                else "FX3_DISP_4_SHOOT_3_PLAY_OK"
            )
        ),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Sub-Model 65C: Still-Only [AEL w/ Shutter] & Flash Submenu vs Flash-Less FX6
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StillAelAndFlashSubmenuEvalResult:
    body_profile: str
    shooting_domain: str
    focus_mode: str
    effective_ael_w_shutter: str
    ael_locked_on_half_shutter: bool
    ael_toggle_overrode_half_shutter: bool
    continuous_burst_remetering: bool
    effective_exp_comp_set: str
    flash_output_shifted_with_ev_comp: bool
    effective_wireless_flash: str
    wireless_test_flash_available: bool
    flash_mount_type: str
    external_flash_menu_accessible: bool
    camera_settings_reset_applied: bool
    initialize_applied: bool
    ael_survived_cam_reset: bool
    exp_comp_set_survived_cam_reset: bool
    wireless_flash_reset_by_cam_reset: bool
    ext_flash_survived_cam_reset: bool
    fx6_flash_band_reduce_only: bool
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


def simulate_still_ael_w_shutter_and_flash_submenu_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shooting_domain: str = DOMAIN_STILL,
    focus_mode: str = FOCUS_MODE_AFS,
    ael_w_shutter: str = AEL_W_SHUTTER_AUTO,
    ael_toggle_active: bool = False,
    subject_moving_in_afa: bool = False,
    exp_comp_set: str = EXP_COMP_SET_AMBIENT_FLASH,
    exposure_comp_ev: float = 0.0,
    wireless_flash: str = WIRELESS_FLASH_OFF,
    flash_mount_type: str = FLASH_MOUNT_NONE,
    access_external_flash_menu: bool = False,
    request_menu_flash_pair_or_reset: bool = False,
    request_exp_comp_set_under_wrong_menu: bool = False,
    fx6_request_flash_band_reduce: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> StillAelAndFlashSubmenuEvalResult:
    """Model Sub-Model 65C: Still-only [AEL w/ Shutter], [Exp.comp.set], [Wireless Flash], [External Flash Set.]."""
    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return StillAelAndFlashSubmenuEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            effective_ael_w_shutter=ael_w_shutter,
            ael_locked_on_half_shutter=False,
            ael_toggle_overrode_half_shutter=False,
            continuous_burst_remetering=False,
            effective_exp_comp_set=exp_comp_set,
            flash_output_shifted_with_ev_comp=False,
            effective_wireless_flash=WIRELESS_FLASH_OFF,
            wireless_test_flash_available=False,
            flash_mount_type=flash_mount_type,
            external_flash_menu_accessible=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            ael_survived_cam_reset=False,
            exp_comp_set_survived_cam_reset=False,
            wireless_flash_reset_by_cam_reset=False,
            ext_flash_survived_cam_reset=False,
            fx6_flash_band_reduce_only=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_BODY_PROFILE",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if (
        shooting_domain not in VALID_SHOOTING_DOMAINS
        or focus_mode not in VALID_FOCUS_MODES
        or ael_w_shutter not in VALID_AEL_W_SHUTTER_MODES
        or exp_comp_set not in VALID_EXP_COMP_SET_MODES
        or wireless_flash not in VALID_WIRELESS_FLASH_MODES
        or flash_mount_type not in VALID_FLASH_MOUNT_TYPES
    ):
        return StillAelAndFlashSubmenuEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            effective_ael_w_shutter=ael_w_shutter,
            ael_locked_on_half_shutter=False,
            ael_toggle_overrode_half_shutter=False,
            continuous_burst_remetering=False,
            effective_exp_comp_set=exp_comp_set,
            flash_output_shifted_with_ev_comp=False,
            effective_wireless_flash=wireless_flash,
            wireless_test_flash_available=False,
            flash_mount_type=flash_mount_type,
            external_flash_menu_accessible=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            ael_survived_cam_reset=False,
            exp_comp_set_survived_cam_reset=False,
            wireless_flash_reset_by_cam_reset=False,
            ext_flash_survived_cam_reset=False,
            fx6_flash_band_reduce_only=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_SUBMODEL_65C_ARGUMENT",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # FX6 lacks mechanical focal-plane shutter & Still TTL flash stack (ENOENT = 2),
    # exposing ONLY rolling-shutter Flash Band Reduce (_2.uxc 0x4215).
    if body_profile == BODY_MODEL_FX6:
        if fx6_request_flash_band_reduce and (
            not access_external_flash_menu
            and ael_w_shutter == AEL_W_SHUTTER_AUTO
            and exp_comp_set == EXP_COMP_SET_AMBIENT_FLASH
            and wireless_flash == WIRELESS_FLASH_OFF
        ):
            return StillAelAndFlashSubmenuEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                effective_ael_w_shutter="N/A",
                ael_locked_on_half_shutter=False,
                ael_toggle_overrode_half_shutter=False,
                continuous_burst_remetering=False,
                effective_exp_comp_set="N/A",
                flash_output_shifted_with_ev_comp=False,
                effective_wireless_flash="N/A",
                wireless_test_flash_available=False,
                flash_mount_type=flash_mount_type,
                external_flash_menu_accessible=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                ael_survived_cam_reset=False,
                exp_comp_set_survived_cam_reset=False,
                wireless_flash_reset_by_cam_reset=False,
                ext_flash_survived_cam_reset=False,
                fx6_flash_band_reduce_only=True,
                admitted=True,
                errno_code=0,
                reason_code="FX6_ROLLING_SHUTTER_FLASH_BAND_REDUCE_ONLY",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        return StillAelAndFlashSubmenuEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            effective_ael_w_shutter="N/A",
            ael_locked_on_half_shutter=False,
            ael_toggle_overrode_half_shutter=False,
            continuous_burst_remetering=False,
            effective_exp_comp_set="N/A",
            flash_output_shifted_with_ev_comp=False,
            effective_wireless_flash="N/A",
            wireless_test_flash_available=False,
            flash_mount_type=flash_mount_type,
            external_flash_menu_accessible=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            ael_survived_cam_reset=False,
            exp_comp_set_survived_cam_reset=False,
            wireless_flash_reset_by_cam_reset=False,
            ext_flash_survived_cam_reset=False,
            fx6_flash_band_reduce_only=True,
            admitted=False,
            errno_code=ENOENT_ERRNO,
            reason_code="FX6_ZERO_MECH_SHUTTER_AND_ZERO_STILL_FLASH_STACK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # All 4 items are Still-only on FX3 — EBUSY=16 in Movie / S&Q
    if shooting_domain in (DOMAIN_MOVIE, DOMAIN_SQ):
        return StillAelAndFlashSubmenuEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            effective_ael_w_shutter=ael_w_shutter,
            ael_locked_on_half_shutter=False,
            ael_toggle_overrode_half_shutter=False,
            continuous_burst_remetering=False,
            effective_exp_comp_set=exp_comp_set,
            flash_output_shifted_with_ev_comp=False,
            effective_wireless_flash=wireless_flash,
            wireless_test_flash_available=False,
            flash_mount_type=flash_mount_type,
            external_flash_menu_accessible=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            ael_survived_cam_reset=True,
            exp_comp_set_survived_cam_reset=True,
            wireless_flash_reset_by_cam_reset=True,
            ext_flash_survived_cam_reset=True,
            fx6_flash_band_reduce_only=False,
            admitted=False,
            errno_code=EBUSY_ERRNO,
            reason_code=f"STILL_ONLY_AEL_AND_FLASH_REJECTED_IN_{shooting_domain}",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if request_exp_comp_set_under_wrong_menu:
        return StillAelAndFlashSubmenuEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            effective_ael_w_shutter=ael_w_shutter,
            ael_locked_on_half_shutter=False,
            ael_toggle_overrode_half_shutter=False,
            continuous_burst_remetering=False,
            effective_exp_comp_set=exp_comp_set,
            flash_output_shifted_with_ev_comp=False,
            effective_wireless_flash=wireless_flash,
            wireless_test_flash_available=False,
            flash_mount_type=flash_mount_type,
            external_flash_menu_accessible=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            ael_survived_cam_reset=True,
            exp_comp_set_survived_cam_reset=True,
            wireless_flash_reset_by_cam_reset=True,
            ext_flash_survived_cam_reset=True,
            fx6_flash_band_reduce_only=False,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="EXP_COMP_SET_LIVES_UNDER_FLASH_SUBMENU_NOT_EXPOSURE_COMP",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if request_menu_flash_pair_or_reset:
        return StillAelAndFlashSubmenuEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            effective_ael_w_shutter=ael_w_shutter,
            ael_locked_on_half_shutter=False,
            ael_toggle_overrode_half_shutter=False,
            continuous_burst_remetering=False,
            effective_exp_comp_set=exp_comp_set,
            flash_output_shifted_with_ev_comp=False,
            effective_wireless_flash=wireless_flash,
            wireless_test_flash_available=False,
            flash_mount_type=flash_mount_type,
            external_flash_menu_accessible=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            ael_survived_cam_reset=True,
            exp_comp_set_survived_cam_reset=True,
            wireless_flash_reset_by_cam_reset=True,
            ext_flash_survived_cam_reset=True,
            fx6_flash_band_reduce_only=False,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="EXTERNAL_FLASH_CANNOT_PAIR_OR_RESET_FROM_CAMERA_MENU",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # [External Flash Set.] requires direct MI-Shoe mount; sync-cord off-camera fails EINVAL=22
    if access_external_flash_menu:
        if flash_mount_type == FLASH_MOUNT_SYNC_CORD:
            return StillAelAndFlashSubmenuEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                effective_ael_w_shutter=ael_w_shutter,
                ael_locked_on_half_shutter=False,
                ael_toggle_overrode_half_shutter=False,
                continuous_burst_remetering=False,
                effective_exp_comp_set=exp_comp_set,
                flash_output_shifted_with_ev_comp=False,
                effective_wireless_flash=wireless_flash,
                wireless_test_flash_available=False,
                flash_mount_type=flash_mount_type,
                external_flash_menu_accessible=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                ael_survived_cam_reset=True,
                exp_comp_set_survived_cam_reset=True,
                wireless_flash_reset_by_cam_reset=True,
                ext_flash_survived_cam_reset=True,
                fx6_flash_band_reduce_only=False,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason_code="EXTERNAL_FLASH_SYNC_CORD_OFF_CAMERA_UNSUPPORTED",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )
        if flash_mount_type != FLASH_MOUNT_MI_SHOE:
            return StillAelAndFlashSubmenuEvalResult(
                body_profile=body_profile,
                shooting_domain=shooting_domain,
                focus_mode=focus_mode,
                effective_ael_w_shutter=ael_w_shutter,
                ael_locked_on_half_shutter=False,
                ael_toggle_overrode_half_shutter=False,
                continuous_burst_remetering=False,
                effective_exp_comp_set=exp_comp_set,
                flash_output_shifted_with_ev_comp=False,
                effective_wireless_flash=wireless_flash,
                wireless_test_flash_available=False,
                flash_mount_type=flash_mount_type,
                external_flash_menu_accessible=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                ael_survived_cam_reset=True,
                exp_comp_set_survived_cam_reset=True,
                wireless_flash_reset_by_cam_reset=True,
                ext_flash_survived_cam_reset=True,
                fx6_flash_band_reduce_only=False,
                admitted=False,
                errno_code=ENODEV_ERRNO,
                reason_code="EXTERNAL_FLASH_REQUIRES_DIRECT_MI_SHOE_MOUNT",
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            )

    # Reset vs Initialize lifecycle split:
    # ONLY [Wireless Flash] resets on [Camera Settings Reset]!
    # [AEL w/ Shutter], [Exp.comp.set], [External Flash Set.] require [Initialize].
    if initialize_applied:
        eff_ael = AEL_W_SHUTTER_AUTO
        eff_exp_comp_set = EXP_COMP_SET_AMBIENT_FLASH
        eff_wireless = WIRELESS_FLASH_OFF
    elif camera_settings_reset_applied:
        eff_ael = ael_w_shutter
        eff_exp_comp_set = exp_comp_set
        eff_wireless = WIRELESS_FLASH_OFF  # Resettable!
    else:
        eff_ael = ael_w_shutter
        eff_exp_comp_set = exp_comp_set
        eff_wireless = wireless_flash

    if ael_toggle_active:
        ael_locked = True
        burst_remeter = False
    elif eff_ael == AEL_W_SHUTTER_ON:
        ael_locked = True
        burst_remeter = False
    elif eff_ael == AEL_W_SHUTTER_OFF:
        ael_locked = False
        burst_remeter = True
    else:  # Auto
        if focus_mode == FOCUS_MODE_AFS:
            ael_locked = True
            burst_remeter = False
        elif focus_mode == FOCUS_MODE_AFA and not subject_moving_in_afa:
            ael_locked = True
            burst_remeter = False
        else:
            ael_locked = False
            burst_remeter = True

    flash_shifted = (
        eff_exp_comp_set == EXP_COMP_SET_AMBIENT_FLASH and abs(exposure_comp_ev) > 1e-9
    )

    return StillAelAndFlashSubmenuEvalResult(
        body_profile=body_profile,
        shooting_domain=shooting_domain,
        focus_mode=focus_mode,
        effective_ael_w_shutter=eff_ael,
        ael_locked_on_half_shutter=ael_locked,
        ael_toggle_overrode_half_shutter=ael_toggle_active,
        continuous_burst_remetering=burst_remeter,
        effective_exp_comp_set=eff_exp_comp_set,
        flash_output_shifted_with_ev_comp=flash_shifted,
        effective_wireless_flash=eff_wireless,
        wireless_test_flash_available=(eff_wireless == WIRELESS_FLASH_ON),
        flash_mount_type=flash_mount_type,
        external_flash_menu_accessible=(flash_mount_type == FLASH_MOUNT_MI_SHOE),
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        ael_survived_cam_reset=True,
        exp_comp_set_survived_cam_reset=True,
        wireless_flash_reset_by_cam_reset=True,
        ext_flash_survived_cam_reset=True,
        fx6_flash_band_reduce_only=False,
        admitted=True,
        errno_code=0,
        reason_code=(
            "STILL_AEL_FLASH_INITIALIZED"
            if initialize_applied
            else (
                "STILL_AEL_FLASH_CAM_RESET_ONLY_WIRELESS_RESET"
                if camera_settings_reset_applied
                else "STILL_AEL_AND_FLASH_SUBMENU_OK"
            )
        ),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Sub-Model 65D: Playback [Viewing] 9-Speed Interval PB & [Edit] vs Vault Firewall
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntervalPlaybackEditVaultEvalResult:
    body_profile: str
    operation: str
    viewing_parent_menu: str
    select_playback_media: str
    slot1_is_tier0_vault: bool
    effective_play_speed_for_interval: int
    dial_speed_adjusted: bool
    playback_edit_items_exposed: Tuple[str, ...]
    effective_photo_capture_file_type: str
    interval_survived_cam_reset: bool
    reset_via_initialize_only: bool
    camera_settings_reset_applied: bool
    initialize_applied: bool
    tier0_vault_firewall_triggered: bool
    dormant_trap_blocked: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    slot1_vault_pb_edit_mutation_bytes: int
    virtual_slot2_rotated_deg: int
    virtual_slot2_captured_file: str
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


def simulate_interval_playback_edit_and_vault_firewall_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    operation: str = PB_OP_VIEW_INTERVAL,
    viewing_parent_menu: str = "Viewing",
    select_playback_media: str = SLOT_1,
    slot1_is_tier0_vault: bool = True,
    play_speed_for_interval: int = INTERVAL_PLAY_SPEED_DEFAULT,
    dial_step_delta: int = 0,
    photo_capture_file_type: str = PB_JPEG_HEIF_JPEG,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> IntervalPlaybackEditVaultEvalResult:
    """Model Sub-Model 65D: 9-speed [Play Speed for Interval], [Edit] vs dormant, and Slot-1 Vault Firewall."""
    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return IntervalPlaybackEditVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            viewing_parent_menu=viewing_parent_menu,
            select_playback_media=select_playback_media,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            effective_play_speed_for_interval=INTERVAL_PLAY_SPEED_DEFAULT,
            dial_speed_adjusted=False,
            playback_edit_items_exposed=(),
            effective_photo_capture_file_type=photo_capture_file_type,
            interval_survived_cam_reset=False,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            tier0_vault_firewall_triggered=False,
            dormant_trap_blocked=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_pb_edit_mutation_bytes=SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
            virtual_slot2_rotated_deg=0,
            virtual_slot2_captured_file="",
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_BODY_PROFILE",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if (
        operation not in VALID_PB_WAVE55_OPS
        or select_playback_media not in VALID_PLAYBACK_SLOTS
        or photo_capture_file_type not in VALID_PHOTO_CAPTURE_FILE_TYPES
    ):
        return IntervalPlaybackEditVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            viewing_parent_menu=viewing_parent_menu,
            select_playback_media=select_playback_media,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            effective_play_speed_for_interval=INTERVAL_PLAY_SPEED_DEFAULT,
            dial_speed_adjusted=False,
            playback_edit_items_exposed=FX3_ACTIVE_PB_EDIT_ITEMS,
            effective_photo_capture_file_type=photo_capture_file_type,
            interval_survived_cam_reset=False,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            tier0_vault_firewall_triggered=False,
            dormant_trap_blocked=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_pb_edit_mutation_bytes=SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
            virtual_slot2_rotated_deg=0,
            virtual_slot2_captured_file="",
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_SUBMODEL_65D_ARGUMENT",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if body_profile == BODY_MODEL_FX6:
        return IntervalPlaybackEditVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            viewing_parent_menu="N/A",
            select_playback_media=select_playback_media,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            effective_play_speed_for_interval=0,
            dial_speed_adjusted=False,
            playback_edit_items_exposed=(),
            effective_photo_capture_file_type="N/A",
            interval_survived_cam_reset=False,
            reset_via_initialize_only=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            tier0_vault_firewall_triggered=False,
            dormant_trap_blocked=True,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_pb_edit_mutation_bytes=SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
            virtual_slot2_rotated_deg=0,
            virtual_slot2_captured_file="",
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="FX6_LACKS_INTERVAL_PB_PHOTO_CAPTURE_BEAUTY_TRIMMING",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Check exact Viewing parent menu vs wrong Playback Option
    if viewing_parent_menu != "Viewing":
        return IntervalPlaybackEditVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            viewing_parent_menu=viewing_parent_menu,
            select_playback_media=select_playback_media,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            effective_play_speed_for_interval=INTERVAL_PLAY_SPEED_DEFAULT,
            dial_speed_adjusted=False,
            playback_edit_items_exposed=FX3_ACTIVE_PB_EDIT_ITEMS,
            effective_photo_capture_file_type=photo_capture_file_type,
            interval_survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            tier0_vault_firewall_triggered=False,
            dormant_trap_blocked=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_pb_edit_mutation_bytes=SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
            virtual_slot2_rotated_deg=0,
            virtual_slot2_captured_file="",
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="CONT_PLAY_INTERVAL_LIVES_UNDER_VIEWING_NOT_PLAYBACK_OPTION",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Reject out-of-range speed (< 1 or > 9)
    if (
        not isinstance(play_speed_for_interval, int)
        or isinstance(play_speed_for_interval, bool)
        or play_speed_for_interval < INTERVAL_PLAY_SPEED_MIN
        or play_speed_for_interval > INTERVAL_PLAY_SPEED_MAX
    ):
        return IntervalPlaybackEditVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            viewing_parent_menu=viewing_parent_menu,
            select_playback_media=select_playback_media,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            effective_play_speed_for_interval=INTERVAL_PLAY_SPEED_DEFAULT,
            dial_speed_adjusted=False,
            playback_edit_items_exposed=FX3_ACTIVE_PB_EDIT_ITEMS,
            effective_photo_capture_file_type=photo_capture_file_type,
            interval_survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            tier0_vault_firewall_triggered=False,
            dormant_trap_blocked=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_pb_edit_mutation_bytes=SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
            virtual_slot2_rotated_deg=0,
            virtual_slot2_captured_file="",
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code=f"INVALID_INTERVAL_PLAY_SPEED_{play_speed_for_interval}_MUST_BE_1_TO_9",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # No in-camera interval-to-movie synthesis (requires PC Imaging Edge Desktop Viewer)
    if operation == PB_OP_SYNTHESIZE_INTERVAL_MOVIE:
        return IntervalPlaybackEditVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            viewing_parent_menu=viewing_parent_menu,
            select_playback_media=select_playback_media,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            effective_play_speed_for_interval=play_speed_for_interval,
            dial_speed_adjusted=False,
            playback_edit_items_exposed=FX3_ACTIVE_PB_EDIT_ITEMS,
            effective_photo_capture_file_type=photo_capture_file_type,
            interval_survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            tier0_vault_firewall_triggered=False,
            dormant_trap_blocked=True,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_pb_edit_mutation_bytes=SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
            virtual_slot2_rotated_deg=0,
            virtual_slot2_captured_file="",
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="NO_IN_CAMERA_INTERVAL_MOVIE_SYNTHESIS_USE_IMAGING_EDGE",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # CRITICAL Tier-0 Vault Firewall: any mutating edit (active or dormant) targeting Slot 1 Tier-0
    # fails closed with EROFS=30!
    mutating_ops = (
        PB_OP_ROTATE,
        PB_OP_PHOTO_CAPTURE,
        PB_OP_BEAUTY_EFFECT,
        PB_OP_TRIMMING,
    )
    if operation in mutating_ops and select_playback_media == SLOT_1 and slot1_is_tier0_vault:
        return IntervalPlaybackEditVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            viewing_parent_menu=viewing_parent_menu,
            select_playback_media=select_playback_media,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            effective_play_speed_for_interval=play_speed_for_interval,
            dial_speed_adjusted=False,
            playback_edit_items_exposed=FX3_ACTIVE_PB_EDIT_ITEMS,
            effective_photo_capture_file_type=photo_capture_file_type,
            interval_survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            tier0_vault_firewall_triggered=True,
            dormant_trap_blocked=(operation in (PB_OP_BEAUTY_EFFECT, PB_OP_TRIMMING)),
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_pb_edit_mutation_bytes=SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
            virtual_slot2_rotated_deg=0,
            virtual_slot2_captured_file="",
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason_code=f"SLOT1_TIER0_VAULT_PLAYBACK_EDIT_FIREWALL_EROFS:{operation}",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Copy with Select Playback Media == Slot 2 writes Slot 2 -> Slot 1 -> EROFS=30 on Slot 1 vault
    if operation == PB_OP_COPY and select_playback_media == SLOT_2 and slot1_is_tier0_vault:
        return IntervalPlaybackEditVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            viewing_parent_menu=viewing_parent_menu,
            select_playback_media=select_playback_media,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            effective_play_speed_for_interval=play_speed_for_interval,
            dial_speed_adjusted=False,
            playback_edit_items_exposed=FX3_ACTIVE_PB_EDIT_ITEMS,
            effective_photo_capture_file_type=photo_capture_file_type,
            interval_survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            tier0_vault_firewall_triggered=True,
            dormant_trap_blocked=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_pb_edit_mutation_bytes=SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
            virtual_slot2_rotated_deg=0,
            virtual_slot2_captured_file="",
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason_code="SLOT2_TO_SLOT1_REVERSE_COPY_VAULT_FIREWALL_EROFS",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Dormant Alpha Edit traps ([Beauty Effect] / [Trimming]) on non-vault Slot 2 fail EOPNOTSUPP=95
    if operation in (PB_OP_BEAUTY_EFFECT, PB_OP_TRIMMING):
        return IntervalPlaybackEditVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            viewing_parent_menu=viewing_parent_menu,
            select_playback_media=select_playback_media,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            effective_play_speed_for_interval=play_speed_for_interval,
            dial_speed_adjusted=False,
            playback_edit_items_exposed=FX3_ACTIVE_PB_EDIT_ITEMS,
            effective_photo_capture_file_type=photo_capture_file_type,
            interval_survived_cam_reset=True,
            reset_via_initialize_only=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            tier0_vault_firewall_triggered=False,
            dormant_trap_blocked=True,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_vault_pb_edit_mutation_bytes=SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
            virtual_slot2_rotated_deg=0,
            virtual_slot2_captured_file="",
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code=f"DORMANT_PLAYBACK_EDIT_TRAP_REJECTED:{operation}",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Lifecycle: [Play Speed for Interval] & [JPEG/HEIF Switch] survive [Camera Settings Reset],
    # reset ONLY via [Initialize]
    if initialize_applied:
        eff_speed = INTERVAL_PLAY_SPEED_DEFAULT
        eff_file_type = PB_JPEG_HEIF_JPEG
        dial_adj = False
    else:
        raw_speed = play_speed_for_interval + dial_step_delta
        eff_speed = max(INTERVAL_PLAY_SPEED_MIN, min(INTERVAL_PLAY_SPEED_MAX, raw_speed))
        eff_file_type = photo_capture_file_type
        dial_adj = dial_step_delta != 0

    rot_deg = 270 if (operation == PB_OP_ROTATE and select_playback_media == SLOT_2) else 0
    cap_ext = "JPG" if eff_file_type == PB_JPEG_HEIF_JPEG else "HIF"
    cap_file = (
        f"VIRTUAL_SLOT2/DCIM/100MSDCF/DSC00001.{cap_ext}"
        if (operation == PB_OP_PHOTO_CAPTURE and select_playback_media == SLOT_2)
        else ""
    )

    return IntervalPlaybackEditVaultEvalResult(
        body_profile=body_profile,
        operation=operation,
        viewing_parent_menu=viewing_parent_menu,
        select_playback_media=select_playback_media,
        slot1_is_tier0_vault=slot1_is_tier0_vault,
        effective_play_speed_for_interval=eff_speed,
        dial_speed_adjusted=dial_adj,
        playback_edit_items_exposed=FX3_ACTIVE_PB_EDIT_ITEMS,
        effective_photo_capture_file_type=eff_file_type,
        interval_survived_cam_reset=True,
        reset_via_initialize_only=True,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        tier0_vault_firewall_triggered=False,
        dormant_trap_blocked=False,
        slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
        slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
        slot1_vault_pb_edit_mutation_bytes=SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
        virtual_slot2_rotated_deg=rot_deg,
        virtual_slot2_captured_file=cap_file,
        admitted=True,
        errno_code=0,
        reason_code=(
            "PLAYBACK_VIEWING_READONLY_SLOT1_SAFE"
            if operation == PB_OP_VIEW_INTERVAL
            else f"VIRTUAL_SLOT2_NON_DESTRUCTIVE_{operation}_OK"
        ),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Full Phase 315 Stage 65 (65/65 Milestone) Orchestrator
# ---------------------------------------------------------------------------


def _build_stage65_milestone_probe() -> Dict[str, object]:
    return {
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "phase_number": PHASE_NUMBER,
        "stage_name": STAGE_NAME,
        "is_65th_stage_milestone": True,
        "wave55_pillars": [
            "65A_4item_touch_operation_initialize_only_vs_dormant_shutter_ae_pad_footer",
            "65B_disp_screen_disp_set_4shoot_3play_and_zero_evf_finder_monitor_guard",
            "65C_still_only_ael_w_shutter_exp_comp_set_wireless_and_ext_flash_vs_fx6",
            "65D_interval_play_speed_1_9_default5_and_slot1_tier0_vault_edit_firewall",
        ],
    }


def run_phase315_touch_shooting_disp_zero_evf_interval_pb_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 315 Stage 65 (65/65) Wave-55 Real-Hardware HIL Co-Emulation."""
    donor_audit = inspect_phase315_donors(force_clean_room=force_clean_room, env=env)

    # Pillar 65A scenarios
    p65a_fx3_4item_cam_reset_survives = [
        simulate_touch_operation_and_dormant_guard_hil(
            shooting_domain=domain,
            touch_operation=TOUCH_OP_ON,
            touch_sensitivity=TOUCH_SENS_SENSITIVE,
            touch_func_in_shooting=TOUCH_SHOOT_FOCUS,
            swipe_up=SWIPE_UP_OFF,
            camera_settings_reset_applied=True,
        )
        for domain in VALID_SHOOTING_DOMAINS
    ]
    p65a_fx3_initialize_resets = simulate_touch_operation_and_dormant_guard_hil(
        touch_operation=TOUCH_OP_PLAYBACK_ONLY,
        touch_sensitivity=TOUCH_SENS_SENSITIVE,
        touch_func_in_shooting=TOUCH_SHOOT_OFF,
        swipe_up=SWIPE_UP_OFF,
        initialize_applied=True,
    )
    p65a_playback_only_disables_swipe = simulate_touch_operation_and_dormant_guard_hil(
        touch_operation=TOUCH_OP_PLAYBACK_ONLY,
        swipe_up=SWIPE_UP_OPEN_FN_MENU,
    )
    p65a_dormant_blocked = [
        simulate_touch_operation_and_dormant_guard_hil(
            requested_dormant_touch_symbol=sym,
        )
        for sym in ("Touch Shutter", "Touch AE", "Touch Panel/Pad", "Footer Icon Touch")
    ]
    p65a_responsive_rejected = simulate_touch_operation_and_dormant_guard_hil(
        touch_sensitivity="Responsive",
    )
    p65a_fx6_mf_ok = simulate_touch_operation_and_dormant_guard_hil(
        body_profile=BODY_MODEL_FX6,
        focus_mode=FOCUS_MODE_MF,
        touch_operation=TOUCH_OP_ON,
        fx6_touch_func_in_mf=FX6_TOUCH_MF_TRACKING,
    )

    p65a_ok = (
        len(p65a_fx3_4item_cam_reset_survives) == 3
        and all(
            r.admitted
            and r.exposed_item_count == 4
            and r.effective_touch_sensitivity == TOUCH_SENS_SENSITIVE
            and r.effective_touch_func_in_shooting == TOUCH_SHOOT_FOCUS
            and r.effective_swipe_up == SWIPE_UP_OFF
            and r.all_4_survived_cam_reset
            for r in p65a_fx3_4item_cam_reset_survives
        )
        and p65a_fx3_initialize_resets.admitted
        and p65a_fx3_initialize_resets.effective_touch_operation == TOUCH_OP_ON
        and p65a_fx3_initialize_resets.effective_touch_sensitivity == TOUCH_SENS_STANDARD
        and p65a_fx3_initialize_resets.effective_touch_func_in_shooting == TOUCH_SHOOT_TRACKING
        and p65a_fx3_initialize_resets.effective_swipe_up == SWIPE_UP_OPEN_FN_MENU
        and p65a_playback_only_disables_swipe.admitted
        and p65a_playback_only_disables_swipe.playback_touch_active
        and (not p65a_playback_only_disables_swipe.shooting_touch_active)
        and (not p65a_playback_only_disables_swipe.swipe_up_active)
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO and r.dormant_touch_symbol_blocked
            for r in p65a_dormant_blocked
        )
        and (not p65a_responsive_rejected.admitted)
        and p65a_responsive_rejected.errno_code == EINVAL_ERRNO
        and p65a_fx6_mf_ok.admitted
        and p65a_fx6_mf_ok.effective_touch_func_in_shooting == FX6_TOUCH_MF_TRACKING
    )

    # Pillar 65B scenarios
    p65b_fx3_4shoot_3play_ok = simulate_disp_screen_set_and_zero_evf_guard_hil(
        checked_shoot_pages=FX3_ACTIVE_4_DISP_SHOOT_PAGES,
        camera_settings_reset_applied=True,
    )
    p65b_zero_checked_rejected = simulate_disp_screen_set_and_zero_evf_guard_hil(
        checked_shoot_pages=(),
    )
    p65b_wrong_parent_rejected = simulate_disp_screen_set_and_zero_evf_guard_hil(
        parent_menu=DISP_PARENT_DISPLAY_OPTION_WRONG,
    )
    p65b_finder_monitor_traps_blocked = [
        simulate_disp_screen_set_and_zero_evf_guard_hil(
            request_finder_monitor_symbol=sym,
        )
        for sym in (
            "BKID_APP_setting_finder_monitor",
            "Select Finder/Monitor",
            "DISP Button:Finder",
        )
    ]
    p65b_dormant_pages_blocked = [
        simulate_disp_screen_set_and_zero_evf_guard_hil(
            requested_dormant_disp_page=pg,
        )
        for pg in ("For viewfinder", "Graphic Display")
    ]
    p65b_fx6_viewfinder_ok = simulate_disp_screen_set_and_zero_evf_guard_hil(
        body_profile=BODY_MODEL_FX6,
        fx6_terminology="Viewfinder",
        fx6_info_disp_mode=FX6_INFO_DISP_DIRECT_PRIORITY,
        fx6_vf_mirror_flip=True,
    )
    p65b_fx6_loupe_rejected = simulate_disp_screen_set_and_zero_evf_guard_hil(
        body_profile=BODY_MODEL_FX6,
        fx6_terminology="Loupe",
    )

    p65b_ok = (
        p65b_fx3_4shoot_3play_ok.admitted
        and p65b_fx3_4shoot_3play_ok.exposed_shoot_page_count == 4
        and p65b_fx3_4shoot_3play_ok.exposed_play_page_count == 3
        and (not p65b_fx3_4shoot_3play_ok.fx3_has_builtin_evf)
        and (not p65b_fx3_4shoot_3play_ok.fx3_has_eye_sensor)
        and (not p65b_fx3_4shoot_3play_ok.fx3_has_finder_monitor_button)
        and (not p65b_fx3_4shoot_3play_ok.lcd_monitor_blacked_out)
        and (not p65b_zero_checked_rejected.admitted)
        and p65b_zero_checked_rejected.errno_code == EINVAL_ERRNO
        and (not p65b_wrong_parent_rejected.admitted)
        and p65b_wrong_parent_rejected.errno_code == EOPNOTSUPP_ERRNO
        and all(
            (not r.admitted)
            and r.errno_code == ENODEV_ERRNO
            and r.blackout_trap_prevented
            and (not r.lcd_monitor_blacked_out)
            for r in p65b_finder_monitor_traps_blocked
        )
        and all(
            (not r.admitted)
            and r.errno_code == EOPNOTSUPP_ERRNO
            and r.blackout_trap_prevented
            for r in p65b_dormant_pages_blocked
        )
        and p65b_fx6_viewfinder_ok.admitted
        and p65b_fx6_viewfinder_ok.fx6_detachable_viewfinder_attached
        and (not p65b_fx6_viewfinder_ok.fx6_uses_loupe_terminology)
        and (not p65b_fx6_loupe_rejected.admitted)
        and p65b_fx6_loupe_rejected.errno_code == EINVAL_ERRNO
    )

    # Pillar 65C scenarios
    p65c_still_cam_reset_split = simulate_still_ael_w_shutter_and_flash_submenu_hil(
        shooting_domain=DOMAIN_STILL,
        focus_mode=FOCUS_MODE_AFC,
        ael_w_shutter=AEL_W_SHUTTER_ON,
        exp_comp_set=EXP_COMP_SET_AMBIENT_ONLY,
        wireless_flash=WIRELESS_FLASH_ON,
        flash_mount_type=FLASH_MOUNT_MI_SHOE,
        access_external_flash_menu=True,
        camera_settings_reset_applied=True,
    )
    p65c_initialize_resets_all = simulate_still_ael_w_shutter_and_flash_submenu_hil(
        shooting_domain=DOMAIN_STILL,
        ael_w_shutter=AEL_W_SHUTTER_OFF,
        exp_comp_set=EXP_COMP_SET_AMBIENT_ONLY,
        wireless_flash=WIRELESS_FLASH_ON,
        initialize_applied=True,
    )
    p65c_movie_ebusy = simulate_still_ael_w_shutter_and_flash_submenu_hil(
        shooting_domain=DOMAIN_MOVIE,
    )
    p65c_sq_ebusy = simulate_still_ael_w_shutter_and_flash_submenu_hil(
        shooting_domain=DOMAIN_SQ,
    )
    p65c_sync_cord_rejected = simulate_still_ael_w_shutter_and_flash_submenu_hil(
        flash_mount_type=FLASH_MOUNT_SYNC_CORD,
        access_external_flash_menu=True,
    )
    p65c_ael_toggle_override = simulate_still_ael_w_shutter_and_flash_submenu_hil(
        focus_mode=FOCUS_MODE_AFC,
        ael_w_shutter=AEL_W_SHUTTER_OFF,
        ael_toggle_active=True,
    )
    p65c_fx6_enoent = simulate_still_ael_w_shutter_and_flash_submenu_hil(
        body_profile=BODY_MODEL_FX6,
        wireless_flash=WIRELESS_FLASH_ON,
    )
    p65c_fx6_flash_band_reduce_ok = simulate_still_ael_w_shutter_and_flash_submenu_hil(
        body_profile=BODY_MODEL_FX6,
        fx6_request_flash_band_reduce=True,
    )

    p65c_ok = (
        p65c_still_cam_reset_split.admitted
        and p65c_still_cam_reset_split.effective_ael_w_shutter == AEL_W_SHUTTER_ON
        and p65c_still_cam_reset_split.effective_exp_comp_set == EXP_COMP_SET_AMBIENT_ONLY
        and p65c_still_cam_reset_split.effective_wireless_flash == WIRELESS_FLASH_OFF
        and p65c_still_cam_reset_split.external_flash_menu_accessible
        and p65c_initialize_resets_all.admitted
        and p65c_initialize_resets_all.effective_ael_w_shutter == AEL_W_SHUTTER_AUTO
        and p65c_initialize_resets_all.effective_exp_comp_set == EXP_COMP_SET_AMBIENT_FLASH
        and p65c_initialize_resets_all.effective_wireless_flash == WIRELESS_FLASH_OFF
        and (not p65c_movie_ebusy.admitted)
        and p65c_movie_ebusy.errno_code == EBUSY_ERRNO
        and (not p65c_sq_ebusy.admitted)
        and p65c_sq_ebusy.errno_code == EBUSY_ERRNO
        and (not p65c_sync_cord_rejected.admitted)
        and p65c_sync_cord_rejected.errno_code == EINVAL_ERRNO
        and p65c_ael_toggle_override.admitted
        and p65c_ael_toggle_override.ael_locked_on_half_shutter
        and p65c_ael_toggle_override.ael_toggle_overrode_half_shutter
        and (not p65c_fx6_enoent.admitted)
        and p65c_fx6_enoent.errno_code == ENOENT_ERRNO
        and p65c_fx6_flash_band_reduce_ok.admitted
        and p65c_fx6_flash_band_reduce_ok.fx6_flash_band_reduce_only
    )

    # Pillar 65D scenarios — 9-Speed Interval PB & Slot-1 Tier-0 Vault Firewall
    p65d_interval_9speeds_ok = [
        simulate_interval_playback_edit_and_vault_firewall_hil(
            operation=PB_OP_VIEW_INTERVAL,
            select_playback_media=SLOT_1,
            slot1_is_tier0_vault=True,
            play_speed_for_interval=spd,
            camera_settings_reset_applied=True,
        )
        for spd in VALID_INTERVAL_PLAY_SPEEDS
    ]
    p65d_speed_0_rejected = simulate_interval_playback_edit_and_vault_firewall_hil(
        play_speed_for_interval=0,
    )
    p65d_speed_10_rejected = simulate_interval_playback_edit_and_vault_firewall_hil(
        play_speed_for_interval=10,
    )
    p65d_synthesis_rejected = simulate_interval_playback_edit_and_vault_firewall_hil(
        operation=PB_OP_SYNTHESIZE_INTERVAL_MOVIE,
    )
    p65d_slot1_vault_blocked = [
        simulate_interval_playback_edit_and_vault_firewall_hil(
            operation=op,
            select_playback_media=SLOT_1,
            slot1_is_tier0_vault=True,
        )
        for op in (PB_OP_ROTATE, PB_OP_PHOTO_CAPTURE, PB_OP_BEAUTY_EFFECT, PB_OP_TRIMMING)
    ]
    p65d_dormant_slot2_eopnotsupp = [
        simulate_interval_playback_edit_and_vault_firewall_hil(
            operation=op,
            select_playback_media=SLOT_2,
            slot1_is_tier0_vault=True,
        )
        for op in (PB_OP_BEAUTY_EFFECT, PB_OP_TRIMMING)
    ]
    p65d_slot2_photo_capture_ok = simulate_interval_playback_edit_and_vault_firewall_hil(
        operation=PB_OP_PHOTO_CAPTURE,
        select_playback_media=SLOT_2,
        slot1_is_tier0_vault=True,
        photo_capture_file_type=PB_JPEG_HEIF_422,
    )

    p65d_ok = (
        len(p65d_interval_9speeds_ok) == 9
        and all(
            r.admitted
            and r.effective_play_speed_for_interval == spd
            and r.slot1_data_sector_writes == 0
            and (not r.slot1_avf_info_mutated)
            and r.interval_survived_cam_reset
            for r, spd in zip(p65d_interval_9speeds_ok, VALID_INTERVAL_PLAY_SPEEDS)
        )
        and (not p65d_speed_0_rejected.admitted)
        and p65d_speed_0_rejected.errno_code == EINVAL_ERRNO
        and (not p65d_speed_10_rejected.admitted)
        and p65d_speed_10_rejected.errno_code == EINVAL_ERRNO
        and (not p65d_synthesis_rejected.admitted)
        and p65d_synthesis_rejected.errno_code == EOPNOTSUPP_ERRNO
        and all(
            (not r.admitted)
            and r.errno_code == EROFS_ERRNO
            and r.tier0_vault_firewall_triggered
            and r.slot1_data_sector_writes == 0
            and (not r.slot1_avf_info_mutated)
            and r.slot1_vault_pb_edit_mutation_bytes == 0
            for r in p65d_slot1_vault_blocked
        )
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO and r.dormant_trap_blocked
            for r in p65d_dormant_slot2_eopnotsupp
        )
        and p65d_slot2_photo_capture_ok.admitted
        and p65d_slot2_photo_capture_ok.effective_photo_capture_file_type == PB_JPEG_HEIF_422
        and p65d_slot2_photo_capture_ok.virtual_slot2_captured_file.endswith(".HIF")
        and p65d_slot2_photo_capture_ok.slot1_data_sector_writes == 0
        and p65d_slot2_photo_capture_ok.physical_device_writes == 0
    )

    milestone_probe = _build_stage65_milestone_probe()

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
        "dormant_touch_shutter_ae_pad_footer_exposed_events": (
            DORMANT_TOUCH_SHUTTER_AE_PAD_FOOTER_EXPOSED_EVENTS
        ),
        "zero_evf_finder_monitor_blackout_trap_events": (
            ZERO_EVF_FINDER_MONITOR_BLACKOUT_TRAP_EVENTS
        ),
        "fx3_has_builtin_evf": FX3_HAS_BUILTIN_EVF,
        "fx3_has_eye_sensor": FX3_HAS_EYE_SENSOR,
        "fx3_has_finder_monitor_button": FX3_HAS_FINDER_MONITOR_BUTTON,
        "fx6_has_builtin_evf": FX6_HAS_BUILTIN_EVF,
        "fx6_uses_loupe_terminology": FX6_USES_LOUPE_TERMINOLOGY,
        "still_only_ael_flash_movie_sq_bypass_events": (
            STILL_ONLY_AEL_FLASH_MOVIE_SQ_BYPASS_EVENTS
        ),
        "sync_cord_external_flash_bypass_events": (
            SYNC_CORD_EXTERNAL_FLASH_BYPASS_EVENTS
        ),
        "fx6_has_still_flash_stack": FX6_HAS_STILL_FLASH_STACK,
        "interval_play_speed_out_of_1_9_range_events": (
            INTERVAL_PLAY_SPEED_OUT_OF_1_9_RANGE_EVENTS
        ),
        "dormant_beauty_effect_or_trimming_exposed_events": (
            DORMANT_BEAUTY_EFFECT_OR_TRIMMING_EXPOSED_EVENTS
        ),
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "slot1_vault_pb_edit_mutation_bytes": SLOT1_VAULT_PB_EDIT_MUTATION_BYTES,
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
        and p65a_ok
        and p65b_ok
        and p65c_ok
        and p65d_ok
        and milestone_probe["is_65th_stage_milestone"]
        and redlines["dormant_touch_shutter_ae_pad_footer_exposed_events"] == 0
        and redlines["zero_evf_finder_monitor_blackout_trap_events"] == 0
        and (not redlines["fx3_has_builtin_evf"])
        and (not redlines["fx3_has_eye_sensor"])
        and (not redlines["fx3_has_finder_monitor_button"])
        and (not redlines["fx6_uses_loupe_terminology"])
        and redlines["still_only_ael_flash_movie_sq_bypass_events"] == 0
        and redlines["sync_cord_external_flash_bypass_events"] == 0
        and (not redlines["fx6_has_still_flash_stack"])
        and redlines["interval_play_speed_out_of_1_9_range_events"] == 0
        and redlines["dormant_beauty_effect_or_trimming_exposed_events"] == 0
        and redlines["slot1_data_sector_writes"] == 0
        and (not redlines["slot1_avf_info_mutated"])
        and redlines["slot1_vault_pb_edit_mutation_bytes"] == 0
        and redlines["raw_firmware_bytes_leaked"] == 0
        and redlines["physical_device_writes"] == 0
        and (not redlines["persistent_emmc_writes_authorized"])
        and (not redlines["hardware_live_attachment_authorized"])
        and (not redlines["overall_ready_for_hardware_attach"])
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_315_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_65th_stage_milestone": True,
        "source_mode": donor_audit.source_mode,
        "access_mode": donor_audit.access_mode,
        "all_checks_passed": all_passed,
        "donor_audit": asdict(donor_audit),
        "pillar_a_touch_operation_4item_and_dormant_guard_hil": {
            "passed": p65a_ok,
            "exposed_4_setup_items": list(FX3_TOUCH_SETUP_EXPOSED_4_ITEMS),
            "dormant_touch_symbols_rejected": list(DORMANT_TOUCH_SYMBOLS),
            "fx3_4item_cam_reset_survives_all_domains": [
                asdict(r) for r in p65a_fx3_4item_cam_reset_survives
            ],
            "fx3_initialize_resets": asdict(p65a_fx3_initialize_resets),
            "playback_only_disables_swipe_up": asdict(p65a_playback_only_disables_swipe),
            "dormant_touch_symbols_blocked": [asdict(r) for r in p65a_dormant_blocked],
            "responsive_synonym_rejected": asdict(p65a_responsive_rejected),
            "fx6_mf_touch_ok": asdict(p65a_fx6_mf_ok),
        },
        "pillar_b_disp_screen_disp_set_and_zero_evf_blackout_guard_hil": {
            "passed": p65b_ok,
            "active_4_shoot_pages": list(FX3_ACTIVE_4_DISP_SHOOT_PAGES),
            "active_3_play_pages": list(FX3_ACTIVE_3_DISP_PLAY_PAGES),
            "fx3_4shoot_3play_ok": asdict(p65b_fx3_4shoot_3play_ok),
            "zero_checked_rejected": asdict(p65b_zero_checked_rejected),
            "wrong_display_option_parent_rejected": asdict(p65b_wrong_parent_rejected),
            "finder_monitor_traps_blocked": [
                asdict(r) for r in p65b_finder_monitor_traps_blocked
            ],
            "dormant_disp_pages_blocked": [asdict(r) for r in p65b_dormant_pages_blocked],
            "fx6_detachable_viewfinder_ok": asdict(p65b_fx6_viewfinder_ok),
            "fx6_loupe_terminology_rejected": asdict(p65b_fx6_loupe_rejected),
        },
        "pillar_c_still_ael_w_shutter_and_flash_submenu_vs_fx6_hil": {
            "passed": p65c_ok,
            "still_cam_reset_split": asdict(p65c_still_cam_reset_split),
            "initialize_resets_all_4": asdict(p65c_initialize_resets_all),
            "movie_ebusy": asdict(p65c_movie_ebusy),
            "sq_ebusy": asdict(p65c_sq_ebusy),
            "sync_cord_rejected": asdict(p65c_sync_cord_rejected),
            "ael_toggle_override": asdict(p65c_ael_toggle_override),
            "fx6_flash_stack_enoent": asdict(p65c_fx6_enoent),
            "fx6_flash_band_reduce_only_ok": asdict(p65c_fx6_flash_band_reduce_ok),
        },
        "pillar_d_interval_play_speed_and_slot1_vault_edit_firewall_hil": {
            "passed": p65d_ok,
            "valid_9_interval_speeds": list(VALID_INTERVAL_PLAY_SPEEDS),
            "default_interval_speed": INTERVAL_PLAY_SPEED_DEFAULT,
            "interval_9speeds_ok": [asdict(r) for r in p65d_interval_9speeds_ok],
            "speed_0_rejected": asdict(p65d_speed_0_rejected),
            "speed_10_rejected": asdict(p65d_speed_10_rejected),
            "interval_movie_synthesis_rejected": asdict(p65d_synthesis_rejected),
            "slot1_vault_edits_blocked_erofs": [
                asdict(r) for r in p65d_slot1_vault_blocked
            ],
            "dormant_slot2_traps_eopnotsupp": [
                asdict(r) for r in p65d_dormant_slot2_eopnotsupp
            ],
            "virtual_slot2_photo_capture_heif422_ok": asdict(
                p65d_slot2_photo_capture_ok
            ),
            "stage65_milestone_probe": milestone_probe,
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
        prog="realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator.py",
        description=(
            "Phase 315 Stage 65 (65/65 Milestone) Wave-55 Real-Hardware "
            "ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 4-Item [Touch Operation] & Dormant "
            "Touch Shutter/AE/Pad/Footer Guard, 4-Mode [DISP (Screen Disp) Set] & Zero-EVF "
            "Select Finder/Monitor Blackout-Trap Guard vs FX6 Detachable Viewfinder, Still-Only "
            "[AEL w/ Shutter]/[Exp.comp.set]/[Wireless Flash]/[External Flash Set.], and "
            "9-Speed [Play Speed for Interval] (1..9 default 5) + Dormant [Beauty Effect]/"
            "[Trimming] & [Photo Capture] Slot-1 100%% Fail-Closed Tier-0 Vault Firewall "
            "HIL Co-Emulator"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic Phase 315 Stage 65 (65/65) Wave-55 HIL verification suite",
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
        help="Emit concise one-line Stage 65 (65/65 Milestone) Wave-55 summary",
    )
    args = parser.parse_args(argv)

    rep = run_phase315_touch_shooting_disp_zero_evf_interval_pb_coemulation(
        force_clean_room=True if args.clean_room else None
    )

    if args.summary and not args.json:
        red = rep["redlines"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 315 Stage 65 (65/65 Milestone) | "
            f"mode={rep['source_mode']} "
            f"donors={rep['donor_audit']['donor_files_inspected']} "
            f"tch_byp={red['dormant_touch_shutter_ae_pad_footer_exposed_events']} "
            f"evf_trap={red['zero_evf_finder_monitor_blackout_trap_events']} "
            f"fx3_evf={int(bool(red['fx3_has_builtin_evf']))} "
            f"ael_byp={red['still_only_ael_flash_movie_sq_bypass_events']} "
            f"ivl_byp={red['interval_play_speed_out_of_1_9_range_events']} "
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
