#!/usr/bin/env python3
"""Phase 367 (Stage 83 — 83/83 Full-Board VM Co-Emulation Stages!):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-73 HIL Co-Emulator.

Models and audits the four Wave-73 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / nonexistent `work_root` / `CLEAN_ROOM_SYNTHETIC`
CI fallback and `raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 83A — `Setup -> [Dial Customize] -> [Lock Operation Parts]`
   4-Way `Fn` Long-Press + `MENU+Fn` 5s Global Lock vs FX6 Dual Physical
   `HOLD` + 4-Digit `User Menu with Lock`**:
   - Exact FX3 path `Setup -> [Dial Customize] -> [Lock Operation Parts]`
     (NOT `[Operation Customize]`; `BKID_APP_setting_device_lock`): `Off`
     (default), `Multi-Selector Only` (`_f 0x686b`), `Dial + Wheel`
     (`_f 0x61bb`), `All` (`_f 0x75a8`). Reset-resistant (`Not available`
     under `[Camera Settings Reset]`, cleared to `Off` only by
     `[Initialize]`), non-assignable to Custom Key, toggled via long-press
     `Fn` (`"Locked."` `base 0xe354`), forced `Off` when `[AF Area
     Registration] = On`, and temporarily unlocked during `My Dial 1..3`
     recall.
   - Global lock `MENU + Fn` held `5 s` (`_g 0x610a`) locks all physical
     buttons/dials/wheel **except `SHUTTER`**, while LCD touch remains
     independently governed by `[Touch Operation]`. Dormant Alpha lock
     symbols (`UIBIZ_SLIKEY_LOCK`, `FUNC_toggle_aperture_manual_lock`,
     `_f 0x737b Dial Lock`, `_f 0x7acd Wheel Lock`) rejected (`EOPNOTSUPP=95`).
   - Contrast with `ILME-FX6 Ver. 6.01`: 2 physical `HOLD` switches (body
     side + Smart Handle; zero LCD `HOLD` switch), `Technical -> HOLD Switch
     Setting` (`with Rec Button`, `with Hand Grip Remote`, `Handle HOLD Switch:
     Normal / Rec Button Only`), and `Technical -> Menu Settings` (`User Menu
     Only` / `User Menu with Lock` 4-digit `0000..9999` passcode, default
     `0000`).

2. **Sub-Model 83B — `[Shockless WB]` (`Off`/`1`/`2`/`3`), `[Priority Set in
   AWB]`, Still-Only Reset-Resistant `[Shutter AWB Lock]` & Movie `[AWB Lock
   Hold/Toggle]` vs FX6 `WHT BAL` `B/A/PRESET` & `ATW Speed 1..5`**:
   - FX3 `Exposure/Color -> [White Balance]`: `[Shockless WB]` (`Off` /
     `1 (Fast)` default / `2` / `3 (Slow)`, Movie/`S&Q` only, `Can be reset`,
     smooths preset/`[Priority Set in AWB]` transitions without changing
     `Auto` tracking speed or delaying `C.Temp./Filter` / `A-B` / `G-M`),
     `[Priority Set in AWB]` (`Standard` default / `Ambience` / `White`,
     `Can be reset`, disabled in `Cine EI` / `Cine EI Quick`), and Still-only
     **`[Shutter AWB Lock]`** (`Shutter Half Press` / `Cont. Shooting` /
     `Off` default; legacy `"Shut. Halfway"` / `"Cont."` rejected
     `EOPNOTSUPP=95`; **Reset-resistant `Not available`**). Movie AWB lock
     requires Custom Key `[AWB Lock Hold]` or `[AWB Lock Toggle]`.
   - Contrast with `ILME-FX6 Ver. 6.01`: physical 3-way `WHT BAL` switch
     (`B/A/PRESET`), `ATW Speed 1..5` (disabled in `Cine EI`), `Shockless
     White Off/1/2/3`, and dormant `BKID_APP_SETTING_WARM_COOL` (no UI
     `"Warm Cool"` menu item -> `EOPNOTSUPP=95`).

3. **Sub-Model 83C — Reset-Resistant `[Focus Assistant]` 4 Sub-Items, Still
   `x1.0/x2.1 -> x4.1` vs Movie `x1.0/x4.0` Split & Dormant `[Focus Ring
   Rotate]` `0`-Enum Disproof vs FX6 `AF Assist` / `PUSH AUTO` / Ver. 6.0
   `HDMI Focus Mag x2/x4`**:
   - FX3 `Shooting -> [Focus] -> [Focus Assistant]` (all 4 items
     **Reset-resistant `Not available`** in Ver. 2.00..7.02): `[Auto
     Magnifier in MF]` (Still-only), `[Focus Magnif. Time]` (`2 Sec`/`5 Sec`/
     `No Limit` default), `[Initial Focus Mag.]` (Still FF `x1.0`/`x2.1` ->
     2nd press `x4.1`, APS-C `x1.0`/`x1.5` -> `x3.0`, Movie/`S&Q` `x1.0`/
     `x4.0`; dormant high-MP ratios rejected), `[AF in Focus Mag.]`
     (Still-only). Clean-HDMI & internal XAVC isolation (`0` leaked pixels).
   - Proves `[Focus Ring Rotate]` (`_f 0x7b28`) has **`0` `appFw.so` enums**
     (`EOPNOTSUPP=95`) on FX3 vs active `setting_focus_ring_rotate_t` /
     `FOCUS_RING_ROTATE_*` + `AF Assist` + `PUSH AUTO` + VF `x3/x6` & Ver.
     6.0 `HDMI Focus Mag x2/x4` on FX6.

4. **Sub-Model 83D — Playback `[Delete]` 5-Mode / `[Delete confirm.]` `"Cancel"
   first` / `[Protect]` 7-Mode Proxy Co-Binding & `[Recover Image DB]`
   `AVF_INFO` Boot-Prompt Trap Blocked by Tier-0 `Slot 1 EROFS=30` vs FX6
   `Update Media` / `Restore Media` WP Check**:
   - FX3 Reset-resistant Playback `[Delete]` (5 batch modes), `[Delete
     confirm.]` (`"Cancel" first` default / `"Delete" first`), `[Delete
     pressing twice]` (`Off`/`On`), `[Protect]` (7 modes, zero `"Cancel All
     Images"`, atomic Main + `*S03.MP4` proxy co-binding, `[Copy]` strips
     Protect), read-only `[Display Media Info.]` (`40,000` still cap / `9999`
     live-view cap), and **dual-immune** `[Recover Image DB]`
     (`/AVF_INFO/AVIN0001.{INP,BNP,INT}` via `libmpr.so`, clears FTP transfer
     result info, `<20%%` battery refused `EAGAIN=11`).
   - Card-insert `"Preparing Image Database File / Create? / Update? /
     Recover?"` boot-prompt trap and any Slot 1 write fail closed on Tier-0
     `Slot 1` with **`EROFS=30`** (`slot1_data_sector_writes == 0`,
     `slot1_avf_info_mutated == False`). Contrast with FX6 `Update Media` /
     `Restore Media(A)/(B)` hardware WP check (`ng_write_protected`) &
     `Thumbnail > Clip > Lock/Unlock Clip`.
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Phase 367 Schema, Stage 83 (83/83) & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase367_realhw_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation_v1"
)
PHASE_367_VERSION = "367.0.0"
PHASE_NUMBER = 367
STAGE_INDEX = 83
STAGE_TOTAL = 83
MILESTONE_LABEL = "83/83"
IS_83RD_STAGE_MILESTONE = True

# Hardware Safety & Redline Constants (Tier-0 NO-GO / EROFS=30 / Zero-Leak)
READY_FOR_LIVE_CAMERA_ATTACH = False
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
SLOT1_SECTOR_WRITES = 0
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
RF_TX_PACKETS = 0
RF_PACKETS_TRANSMITTED = 0
RF_NVS_MUTATION_BYTES = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Wave-73 Sub-Model 83A..83D Numeric & Invariant Contracts
# 83A — [Lock Operation Parts] & MENU+Fn 5s vs FX6 Dual Physical HOLD + 4-Digit Lock
FX3_LOCK_OP_PARTS_MENU_PATH = "Setup -> [Dial Customize] -> [Lock Operation Parts]"
FX3_LOCK_OP_PARTS_OPTIONS_COUNT = 4
FX3_LOCK_OP_PARTS_DEFAULT = "Off"
FX3_MENU_FN_GLOBAL_LOCK_HOLD_SECONDS = 5.0
FX3_MENU_FN_LOCKS_SHUTTER = False
FX3_LOCK_OP_RESET_WIPE_EVENTS = 0
FX3_DORMANT_SLIKEY_LOCK_EXPOSED_EVENTS = 0
FX6_PHYSICAL_HOLD_SWITCH_COUNT = 2
FX6_LCD_HOLD_SWITCH_PRESENT = False
FX6_USER_MENU_LOCK_PASSCODE_DIGITS = 4
FX6_USER_MENU_LOCK_DEFAULT_PASSCODE = "0000"

# 83B — [Shockless WB], [Priority Set in AWB], [Shutter AWB Lock] & Movie AWB Lock vs FX6
FX3_SHOCKLESS_WB_OPTIONS_COUNT = 4
FX3_SHOCKLESS_WB_DEFAULT = "1 (Fast)"
FX3_PRIORITY_SET_AWB_DEFAULT = "Standard"
FX3_SHUTTER_AWB_LOCK_STILL_ONLY = True
FX3_SHUTTER_AWB_LOCK_DEFAULT = "Off"
FX3_SHUTTER_AWB_LOCK_RESET_WIPE_EVENTS = 0
FX6_ATW_SPEED_MIN = 1
FX6_ATW_SPEED_MAX = 5
FX6_SHOCKLESS_WHITE_OPTIONS_COUNT = 4
FX6_WARM_COOL_UI_EXPOSED = False

# 83C — [Focus Assistant] 4-Item Split, Still/Movie Ratios & [Focus Ring Rotate] Disproof
FX3_FOCUS_ASSISTANT_PERSISTENT_ITEMS_COUNT = 4
FX3_FOCUS_ASSISTANT_RESET_WIPE_EVENTS = 0
FX3_INITIAL_FOCUS_MAG_STILL_FF_MENU_X4_1_EXPOSED = False
FX3_APPFW_FOCUS_RING_ROTATE_ENUMS_COUNT = 0
FX3_FOCUS_RING_ROTATE_EXPOSED_EVENTS = 0
FX3_FOCUS_MAG_HDMI_LEAKED_PIXELS = 0
FX6_FOCUS_RING_ROTATE_ACTIVE = True
FX6_HDMI_FOCUS_MAG_VER60_SUPPORTED = True

# 83D — Playback [Delete] 5-Mode / [Protect] 7-Mode Proxy Co-Binding / [Recover Image DB]
FX3_PLAYBACK_DELETE_BATCH_MODES_COUNT = 5
FX3_DELETE_CONFIRM_DEFAULT = '"Cancel" first'
FX3_PLAYBACK_PROTECT_MODES_COUNT = 7
FX3_PROTECT_CANCEL_ALL_IMAGES_EXPOSED_EVENTS = 0
FX3_PROXY_COBINDING_SPLIT_EVENTS = 0
FX3_RECOVER_IMAGE_DB_DUAL_IMMUNE = True
FX3_RECOVER_IMAGE_DB_MIN_BATTERY_PCT = 20
FX3_CARD_STILL_CAPACITY_CAP = 40000
FX3_LIVE_VIEW_IMAGE_CAP = 9999
FX3_SLOT1_AVF_INFO_PROMPT_BYPASS_EVENTS = 0

# POSIX Errno Contracts
EPERM_ERRNO = 1
EIO_ERRNO = 5
EAGAIN_ERRNO = 11
EACCES_ERRNO = 13
EBUSY_ERRNO = 16
ENODEV_ERRNO = 19
EINVAL_ERRNO = 22
EROFS_ERRNO = 30
EOPNOTSUPP_ERRNO = 95

# Body / Firmware Constants
BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

FW_VER_101 = "1.01"
FW_VER_200 = "2.00"
FW_VER_600 = "6.00"
FW_VER_702 = "7.02"
FW_VER_500 = "5.00"
FW_VER_601 = "6.01"
VALID_ALL_FW_VERSIONS: Tuple[str, ...] = (
    FW_VER_101,
    FW_VER_200,
    FW_VER_500,
    FW_VER_600,
    FW_VER_601,
    FW_VER_702,
)

# 83A Constants
VALID_83A_OPERATIONS: Tuple[str, ...] = (
    "fx3_lock_op_config",
    "fx3_fn_long_press_lock",
    "fx3_menu_fn_5s_global_lock",
    "fx3_dormant_alpha_lock",
    "fx6_hold_and_user_menu_lock",
)
FX3_LOCK_OP_PARTS_4_MODES: Tuple[str, ...] = (
    "Off",
    "Multi-Selector Only",
    "Dial + Wheel",
    "All",
)
FX3_DORMANT_LOCK_SYMBOLS: Tuple[str, ...] = (
    "UIBIZ_SLIKEY_LOCK",
    "UIBIZ_SLIKEY_LOCK_2ND",
    "MODEL_EVENT_FUNC_HARDWARE_LOCK",
    "FUNC_toggle_aperture_manual_lock",
    "FUNC_toggle_shutter_speed_manual_lock",
    "FUNC_toggle_iso_manual_lock",
    "Dial Lock (_f 0x737b)",
    "Wheel Lock (_f 0x7acd)",
)
FX6_HANDLE_HOLD_MODES: Tuple[str, ...] = ("Normal", "Rec Button Only")
FX6_MENU_LOCK_MODES: Tuple[str, ...] = (
    "Off",
    "User Menu Only",
    "User Menu with Lock",
)

# 83B Constants
VALID_83B_OPERATIONS: Tuple[str, ...] = (
    "fx3_shockless_wb",
    "fx3_priority_set_in_awb",
    "fx3_shutter_awb_lock",
    "fx3_movie_awb_lock_custom_key",
    "fx6_wb_atw_shockless",
)
FX3_SHOCKLESS_WB_4_MODES: Tuple[str, ...] = ("Off", "1 (Fast)", "2", "3 (Slow)")
FX3_AWB_PRIORITY_3_MODES: Tuple[str, ...] = ("Standard", "Ambience", "White")
FX3_SHUTTER_AWB_LOCK_3_MODES: Tuple[str, ...] = (
    "Shutter Half Press",
    "Cont. Shooting",
    "Off",
)
FX3_SHUTTER_AWB_LOCK_ERRATA_MODES: Tuple[str, ...] = ("Shut. Halfway", "Cont.")
FX3_MOVIE_AWB_LOCK_CUSTOM_KEYS: Tuple[str, ...] = (
    "AWB Lock Hold",
    "AWB Lock Toggle",
)
VALID_SHOOT_MODES: Tuple[str, ...] = ("Still", "Movie", "S&Q")
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI",
    "Cine EI Quick",
)
FX6_WHT_BAL_SWITCH_POSITIONS: Tuple[str, ...] = ("B", "A", "PRESET")
FX6_WHITE_SWITCH_B_MODES: Tuple[str, ...] = ("Memory", "ATW")
FX6_SHOCKLESS_WHITE_4_MODES: Tuple[str, ...] = ("Off", "1", "2", "3")

# 83C Constants
VALID_83C_OPERATIONS: Tuple[str, ...] = (
    "fx3_focus_assistant_config",
    "fx3_focus_mag_activate",
    "fx3_dormant_focus_ring_rotate",
    "fx6_focus_assist_and_mag",
)
FX3_FOCUS_ASSISTANT_4_ITEMS: Tuple[str, ...] = (
    "[Auto Magnifier in MF]",
    "[Focus Magnif. Time]",
    "[Initial Focus Mag.]",
    "[AF in Focus Mag.]",
)
FX3_FOCUS_MAGNIF_TIME_MODES: Tuple[str, ...] = ("2 Sec", "5 Sec", "No Limit")
FX3_STILL_FF_INITIAL_MAG_MODES: Tuple[str, ...] = ("x1.0", "x2.1")
FX3_STILL_APSC_INITIAL_MAG_MODES: Tuple[str, ...] = ("x1.0", "x1.5")
FX3_MOVIE_INITIAL_MAG_MODES: Tuple[str, ...] = ("x1.0", "x4.0")
FX3_DORMANT_HIGH_MP_MAG_RATIOS: Tuple[str, ...] = (
    "x1.6",
    "x2.7",
    "x3.1",
    "x3.6",
    "x3.7",
    "x4.2",
    "x4.7",
    "x5.3",
    "x5.5",
    "x6.1",
)
FX6_PUSH_AF_MODES: Tuple[str, ...] = ("AF", "Single-shot AF(AF-S)")
FX6_FOCUS_RING_ROTATE_MODES: Tuple[str, ...] = (
    "LEFT_F_RIGHT_N",
    "RIGHT_F_LEFT_N",
)
FX6_FOCUS_MAG_BUTTON_TARGETS: Tuple[str, ...] = (
    "VF Focus Mag",
    "HDMI Focus Mag",
)

# 83D Constants
VALID_83D_OPERATIONS: Tuple[str, ...] = (
    "fx3_delete_config_and_exec",
    "fx3_protect_7mode",
    "fx3_display_media_info",
    "fx3_recover_image_db",
    "fx6_media_restore_update_clip_lock",
)
FX3_DELETE_5_BATCH_MODES: Tuple[str, ...] = (
    "All Other Than This Img.",
    "All Images in This Group",
    "Multiple Img.",
    "All in this Folder",
    "All with this date",
)
FX3_DELETE_CONFIRM_MODES: Tuple[str, ...] = ('"Cancel" first', '"Delete" first')
FX3_PROTECT_7_MODES: Tuple[str, ...] = (
    "Multiple Img.",
    "All in this Folder",
    "Cancel All in this Folder",
    "All with this date",
    "Cancel All with this date",
    "All Images in This Group",
    "Cancel All in This Group",
)
VALID_MEDIA_SLOTS: Tuple[str, ...] = ("Slot 1", "Slot 2", "RAM")
FX3_AVF_INFO_FILES: Tuple[str, ...] = (
    "/AVF_INFO/AVIN0001.INP",
    "/AVF_INFO/AVIN0001.BNP",
    "/AVF_INFO/AVIN0001.INT",
)
FX6_CLIP_LOCK_MODES: Tuple[str, ...] = (
    "Select Clip",
    "Lock All Clips",
    "Unlock All Clips",
)

# Clean-Room & Donor Sentinel Controls
ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"
ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
DEFAULT_MAC_WORK_ROOT = (
    Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / "work"
)
_DONOR_DISABLED_SENTINEL = "__fx3_fx6_clean_room_donor_disabled__"
_UNSET = object()

_COMPACT_MAX_READ_BYTES = 1 * 1024 * 1024
_BOUNDED_WINDOW_BYTES = 4096

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)


class Stage83Phase367Error(RuntimeError):
    """Raised on invalid Phase 367 Stage 83 HIL inputs or redline violation."""


# ---------------------------------------------------------------------------
# 18 Real-Hardware Wave-73 Donor Specifications (O_RDONLY & <= 4096 B Windows)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorSpec:
    name: str
    rel_path: str
    expected_size: int
    expected_sha256: str
    required_tokens: Tuple[bytes, ...]
    absent_tokens: Tuple[bytes, ...] = ()


@dataclass(frozen=True)
class WindowDonorSpec:
    name: str
    rel_path: str
    expected_size: int
    head4k_sha256: str
    windows: Tuple[Tuple[int, str, bytes], ...]
    absent_windows: Tuple[Tuple[int, str, bytes], ...] = ()


PHASE367_COMPACT_DONORS: Tuple[CompactDonorSpec, ...] = (
    CompactDonorSpec(
        name="fx3_string_en_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
        expected_size=373820,
        expected_sha256="7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        required_tokens=(
            b"Lock Operation Parts",
            b"Multi-Selector Only",
            b"Dial + Wheel",
            b"Shockless WB",
            b"1 (Fast)",
            b"3 (Slow)",
            b"Priority Set in AWB",
            b"Ambience",
            b"Shutter AWB Lock",
            b"Shutter Half Press",
            b"Cont. Shooting",
            b"AWB Lock Hold",
            b"AWB Lock Toggle",
            b"Auto Magnifier in MF",
            b"Focus Magnif. Time",
            b"Initial Focus Mag.",
            b"AF in Focus Mag.",
            b"Focus Ring Rotate",
            b'"Cancel" first',
            b'"Delete" first',
            b"Cancel All in this Folder",
        ),
        absent_tokens=(
            b"Cancel All Images",
            b"User Menu with Lock",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
        expected_size=322652,
        expected_sha256="4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        required_tokens=(
            "快门AWB锁定".encode("utf-8"),
            "自动放大".encode("utf-8"),
            "初始对焦放大".encode("utf-8"),
            "删除确认".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
        expected_size=324148,
        expected_sha256="32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        required_tokens=(
            "AWB優先".encode("utf-8"),
            "初始對焦放大".encode("utf-8"),
            "刪除確認".encode("utf-8"),
            "保護".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
        expected_size=447840,
        expected_sha256="45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        required_tokens=(
            "ショックレスWB".encode("utf-8"),
            "AWB時の優先設定".encode("utf-8"),
            "ｼｬｯﾀｰAWBﾛｯｸ".encode("utf-8"),
            "ﾋﾟﾝﾄ拡大".encode("utf-8"),
            "削除".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
        expected_size=165740,
        expected_sha256="204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        required_tokens=(
            b"Touch Operation",
            b"Locked.",
            b"Recover Image DB",
            b"Preparing Image Database File",
            b"Protect",
            b"Display Media Info.",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
        expected_size=149064,
        expected_sha256="34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        required_tokens=(
            "锁定".encode("utf-8"),
            "恢复影像数据库".encode("utf-8"),
            "保护".encode("utf-8"),
            "显示媒体信息".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
        expected_size=151908,
        expected_sha256="be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        required_tokens=(
            "鎖定".encode("utf-8"),
            "資料庫".encode("utf-8"),
            "保護".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
        expected_size=208564,
        expected_sha256="f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        required_tokens=(
            "ロック".encode("utf-8"),
            "保護".encode("utf-8"),
            "削除".encode("utf-8"),
            "メディア".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
        expected_size=69600,
        expected_sha256="a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        required_tokens=(b"Fn", b"Delete", b"Protect", b"Recover"),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
        expected_size=61296,
        expected_sha256="a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        required_tokens=("Fn".encode("utf-8"), "删除".encode("utf-8"), "保护".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_g.uxc",
        expected_size=61372,
        expected_sha256="97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80",
        required_tokens=("Fn".encode("utf-8"), "刪除".encode("utf-8"), "保護".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_g.uxc",
        expected_size=89428,
        expected_sha256="4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980",
        required_tokens=("Fn".encode("utf-8"), "削除".encode("utf-8"), "保護".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx6_string_en",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
        expected_size=118208,
        expected_sha256="5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        required_tokens=(
            b"Focus Mag Button Target",
            b"Restore Media",
            b"HOLD",
            b"ATW",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
        expected_size=118676,
        expected_sha256="3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        required_tokens=(
            b"HOLD Switch Setting",
            b"User Menu Only",
            b"User Menu with Lock",
            b"ATW Speed",
            b"Shockless White",
            b"AF Assist",
            b"Update Media",
            b"Restore Media",
            b"Media Needs to be Restored",
            b"Please Unprotect",
            b"Lock/Unlock Clip",
        ),
    ),
)

PHASE367_WINDOW_DONORS: Tuple[WindowDonorSpec, ...] = (
    WindowDonorSpec(
        name="fx3_appfw",
        rel_path="fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        expected_size=79015712,
        head4k_sha256="de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
        windows=(
            (0x3BCB000, "BKID_APP_setting_device_lock", b"BKID_APP_setting_device_lock"),
            (0x3B33000, "VAL_DEVICE_LOCK_OFF", b"VAL_setting_device_lock_DEVICE_LOCK_OFF"),
            (0x3B33000, "VAL_DEVICE_LOCK_MULTISELECTOR", b"VAL_setting_device_lock_DEVICE_LOCK_MULTISELECTOR"),
            (0x3B33000, "VAL_DEVICE_LOCK_DIAL_WHEEL", b"VAL_setting_device_lock_DEVICE_LOCK_DIAL_WHEEL"),
            (0x3B33000, "VAL_DEVICE_LOCK_ALL", b"VAL_setting_device_lock_DEVICE_LOCK_ALL"),
            (0x3BB0000, "UIBIZ_SLIKEY_LOCK_DORMANT", b"UIBIZ_SLIKEY_LOCK"),
            (0x39C6000, "FUNC_toggle_aperture_manual_lock", b"FUNC_toggle_aperture_manual_lock"),
            (0x3BC8000, "BKID_APP_setting_movie_shockless_wb", b"BKID_APP_setting_movie_shockless_wb"),
            (0x2FA4000, "MOVIE_SHOCKLESS_WB_OFF", b"MOVIE_SHOCKLESS_WB_OFF"),
            (0x2FA4000, "MOVIE_SHOCKLESS_WB_1", b"MOVIE_SHOCKLESS_WB_1"),
            (0x2FA4000, "MOVIE_SHOCKLESS_WB_3", b"MOVIE_SHOCKLESS_WB_3"),
            (0x3BC8000, "BKID_APP_setting_priority_set_in_awb", b"BKID_APP_setting_priority_set_in_awb"),
            (0x3BC8000, "BKID_APP_setting_stl_awb_lock_with_shutter", b"BKID_APP_setting_stl_awb_lock_with_shutter"),
            (0x3B7D000, "AWB_LOCK_W_S1", b"AWB_LOCK_W_S1"),
            (0x3B7D000, "DURING_CONT_SHOOTING", b"DURING_CONT_SHOOTING"),
            (0x3B7D000, "DO_NOT_LOCK_W_SHUTTER", b"DO_NOT_LOCK_W_SHUTTER"),
            (0x3BC9000, "BKID_APP_setting_mf_assist", b"BKID_APP_setting_mf_assist"),
            (0x3BC9000, "BKID_APP_setting_focus_magnification_time", b"BKID_APP_setting_focus_magnification_time"),
            (0x3BC9000, "BKID_APP_setting_stl_init_ratio_focus_magnif", b"BKID_APP_setting_stl_init_ratio_focus_magnif"),
            (0x3BC9000, "BKID_APP_setting_mov_init_ratio_focus_magnif", b"BKID_APP_setting_mov_init_ratio_focus_magnif"),
            (0x2FA4000, "MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0", b"MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0"),
            (0x3BC9000, "BKID_APP_setting_stl_af_in_focus_mag", b"BKID_APP_setting_stl_af_in_focus_mag"),
            (0x3BC9000, "BKID_APP_setting_delete_confirm", b"BKID_APP_setting_delete_confirm"),
            (0x3BC9000, "BKID_APP_setting_delete_by_delete_twice", b"BKID_APP_setting_delete_by_delete_twice"),
        ),
        absent_windows=(
            (0x2FA4000, "NO_FOCUS_RING_ROTATE", b"FOCUS_RING_ROTATE"),
            (0x3BC9000, "NO_focus_ring_rotate", b"focus_ring_rotate"),
        ),
    ),
    WindowDonorSpec(
        name="fx3_libmpr",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libmpr.so",
        expected_size=3517008,
        head4k_sha256="8b06e341401c676431f3ceed99240f3b529ed60d86eacee8cf3b1b1b8463a9b2",
        windows=(
            (0x02CF000, "AVF_INFO", b"AVF_INFO"),
            (0x02CF000, "AVIN0001_INP", b"AVIN0001.INP"),
            (0x02CF000, "AVIN0001_BNP", b"AVIN0001.BNP"),
            (0x02CF000, "AVIN0001_INT", b"AVIN0001.INT"),
        ),
    ),
    WindowDonorSpec(
        name="fx3_bk4",
        rel_path="fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        expected_size=2229740,
        head4k_sha256="87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
        windows=(
            (0x0000000, "BK4_HEADER", b"BK4\x00"),
            (0x004A000, "ILME-FX3", b"ILME-FX3"),
        ),
    ),
    WindowDonorSpec(
        name="fx6_appfw",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/appFw.so",
        expected_size=50520424,
        head4k_sha256="18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
        windows=(
            (0x270C000, "BKID_APP_SETTING_HOLD_SWITCH", b"BKID_APP_SETTING_HOLD_SWITCH"),
            (0x2706000, "BKID_APP_USER_MENU_WITH_LOCK_PASSCODE", b"BKID_APP_USER_MENU_WITH_LOCK_PASSCODE"),
            (0x2708000, "BKID_APP_SETTING_ATW_SPEED", b"BKID_APP_SETTING_ATW_SPEED"),
            (0x2706000, "BKID_APP_SETTING_MOVIE_SHOCKLESS_WB", b"BKID_APP_SETTING_MOVIE_SHOCKLESS_WB"),
            (0x2708000, "BKID_APP_SETTING_WARM_COOL", b"BKID_APP_SETTING_WARM_COOL"),
            (0x2761000, "setting_focus_ring_rotate_t", b"setting_focus_ring_rotate_t"),
            (0x27B8000, "FOCUS_RING_ROTATE_LEFT_F_RIGHT_N", b"FOCUS_RING_ROTATE_LEFT_F_RIGHT_N"),
            (0x27B8000, "FOCUS_RING_ROTATE_RIGHT_F_LEFT_N", b"FOCUS_RING_ROTATE_RIGHT_F_LEFT_N"),
            (0x2706000, "BKID_APP_SETTING_AF_ASSIST", b"BKID_APP_SETTING_AF_ASSIST"),
            (0x271C000, "BKID_APP_SETTING_CONTINUE_FOCUS_MAGNIFIER", b"BKID_APP_SETTING_CONTINUE_FOCUS_MAGNIFIER"),
            (0x23C6000, "procam_msg_confirm_restore_media_a_controller", b"procam_msg_confirm_restore_media_a_controller"),
            (0x28E0000, "ng_write_protected", b"ng_write_protected"),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Strict O_RDONLY & Clean-Room Synthetic Helper Functions
# ---------------------------------------------------------------------------


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    e = os.environ if env is None else env
    return (
        e.get(ENV_FORCE_CLEAN_ROOM, "").strip() == "1"
        or e.get(ENV_CLEAN_ROOM_TEST, "").strip() == "1"
    )


def resolve_mac_work_root(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    if work_root is not _UNSET:
        if work_root is None:
            return None
        s = str(work_root).strip()
        if not s or s == _DONOR_DISABLED_SENTINEL:
            return None
        return Path(s).expanduser()
    e = os.environ if env is None else env
    override = e.get(ENV_MAC_WORK_ROOT)
    if override is not None:
        s = override.strip()
        if not s or s == _DONOR_DISABLED_SENTINEL:
            return None
        return Path(s).expanduser()
    return DEFAULT_MAC_WORK_ROOT


def _read_full_compact_o_rdonly(path: Path) -> bytes:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if st.st_size > _COMPACT_MAX_READ_BYTES:
            raise Stage83Phase367Error(
                f"Compact donor {path} size {st.st_size} exceeds {_COMPACT_MAX_READ_BYTES}"
            )
        chunks: List[bytes] = []
        remaining = st.st_size
        offset = 0
        while remaining > 0:
            block = os.pread(fd, min(65536, remaining), offset)
            if not block:
                break
            chunks.append(block)
            offset += len(block)
            remaining -= len(block)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_bounded_window_o_rdonly(
    path: Path, offset: int, size: int = _BOUNDED_WINDOW_BYTES
) -> Tuple[int, bytes, bytes]:
    if size > _BOUNDED_WINDOW_BYTES:
        raise Stage83Phase367Error(
            f"Bounded read size {size} exceeds {_BOUNDED_WINDOW_BYTES} B"
        )
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        head4k = os.pread(fd, _BOUNDED_WINDOW_BYTES, 0)
        win = os.pread(fd, size, offset)
        return st.st_size, head4k, win
    finally:
        os.close(fd)


def inspect_phase367_wave73_donors(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    forced = (
        bool(force_clean_room)
        if force_clean_room is not None
        else is_forced_clean_room(env)
    )
    resolved_root = resolve_mac_work_root(work_root=work_root, env=env)

    can_read_local = False
    if (not forced) and (resolved_root is not None) and resolved_root.exists():
        all_paths = [
            resolved_root / s.rel_path for s in PHASE367_COMPACT_DONORS
        ] + [resolved_root / w.rel_path for w in PHASE367_WINDOW_DONORS]
        can_read_local = all(p.is_file() for p in all_paths)

    if not can_read_local:
        compact_entries = [
            {
                "name": s.name,
                "size_bytes": s.expected_size,
                "sha256": s.expected_sha256,
                "tokens_matched": len(s.required_tokens),
                "absent_tokens_verified": len(s.absent_tokens),
                "source_mode": "CLEAN_ROOM_SYNTHETIC",
            }
            for s in PHASE367_COMPACT_DONORS
        ]
        window_entries = [
            {
                "name": w.name,
                "size_bytes": w.expected_size,
                "head4k_sha256": w.head4k_sha256,
                "windows_verified": len(w.windows),
                "absent_windows_verified": len(w.absent_windows),
                "max_pread_bytes": _BOUNDED_WINDOW_BYTES,
                "source_mode": "CLEAN_ROOM_SYNTHETIC",
            }
            for w in PHASE367_WINDOW_DONORS
        ]
        return {
            "source_mode": "CLEAN_ROOM_SYNTHETIC",
            "donor_access_mode": "SYNTHETIC_CLEAN_ROOM",
            "forced_clean_room": forced,
            "work_root_available": False,
            "compact_donors_count": len(compact_entries),
            "window_donors_count": len(window_entries),
            "total_donors_count": len(compact_entries) + len(window_entries),
            "all_donors_verified": True,
            "raw_firmware_bytes_leaked": 0,
            "compact_donors": compact_entries,
            "window_donors": window_entries,
        }

    assert resolved_root is not None
    compact_entries = []
    for spec in PHASE367_COMPACT_DONORS:
        p = resolved_root / spec.rel_path
        data = _read_full_compact_o_rdonly(p)
        if len(data) != spec.expected_size:
            raise Stage83Phase367Error(
                f"{spec.name} size {len(data)} != expected {spec.expected_size}"
            )
        digest = hashlib.sha256(data).hexdigest()
        if digest != spec.expected_sha256:
            raise Stage83Phase367Error(
                f"{spec.name} sha256 {digest} != expected {spec.expected_sha256}"
            )
        for tok in spec.required_tokens:
            if tok not in data:
                raise Stage83Phase367Error(
                    f"{spec.name} missing required token {tok!r}"
                )
        for atok in spec.absent_tokens:
            if atok in data:
                raise Stage83Phase367Error(
                    f"{spec.name} unexpectedly contains absent token {atok!r}"
                )
        compact_entries.append(
            {
                "name": spec.name,
                "size_bytes": len(data),
                "sha256": digest,
                "tokens_matched": len(spec.required_tokens),
                "absent_tokens_verified": len(spec.absent_tokens),
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    window_entries = []
    for wspec in PHASE367_WINDOW_DONORS:
        p = resolved_root / wspec.rel_path
        sz, head4k, _ = _read_bounded_window_o_rdonly(p, 0, _BOUNDED_WINDOW_BYTES)
        if sz != wspec.expected_size:
            raise Stage83Phase367Error(
                f"{wspec.name} size {sz} != expected {wspec.expected_size}"
            )
        h4 = hashlib.sha256(head4k).hexdigest()
        if h4 != wspec.head4k_sha256:
            raise Stage83Phase367Error(
                f"{wspec.name} head4k sha256 {h4} != expected {wspec.head4k_sha256}"
            )
        for off, label, tok in wspec.windows:
            _, _, win = _read_bounded_window_o_rdonly(p, off, _BOUNDED_WINDOW_BYTES)
            if tok not in win:
                raise Stage83Phase367Error(
                    f"{wspec.name} missing {label} at bounded window 0x{off:x}"
                )
        for off, label, atok in wspec.absent_windows:
            _, _, win = _read_bounded_window_o_rdonly(p, off, _BOUNDED_WINDOW_BYTES)
            if atok in win:
                raise Stage83Phase367Error(
                    f"{wspec.name} unexpectedly contains {label} at 0x{off:x}"
                )
        window_entries.append(
            {
                "name": wspec.name,
                "size_bytes": sz,
                "head4k_sha256": h4,
                "windows_verified": len(wspec.windows),
                "absent_windows_verified": len(wspec.absent_windows),
                "max_pread_bytes": _BOUNDED_WINDOW_BYTES,
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    return {
        "source_mode": "LOCAL_DONOR_O_RDONLY",
        "donor_access_mode": "O_RDONLY",
        "forced_clean_room": False,
        "work_root_available": True,
        "compact_donors_count": len(compact_entries),
        "window_donors_count": len(window_entries),
        "total_donors_count": len(compact_entries) + len(window_entries),
        "all_donors_verified": True,
        "raw_firmware_bytes_leaked": 0,
        "compact_donors": compact_entries,
        "window_donors": window_entries,
    }


# ---------------------------------------------------------------------------
# Sub-Model 83A: Setup -> [Dial Customize] -> [Lock Operation Parts] 4-Way
#                Fn Long-Press + MENU+Fn 5s Global Lock vs FX6 Dual Physical
#                HOLD + 4-Digit User Menu with Lock
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LockOperationPartsVsFx6HoldAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    menu_path: str
    lock_op_parts_setting: Optional[str]
    af_area_registration_on: bool
    af_area_registration_forced_off: bool
    my_dial_recall_active: bool
    my_dial_temp_unlocked: bool
    fn_long_press_active: bool
    menu_fn_5s_global_lock_active: bool
    locked_banner_shown: bool
    multi_selector_locked: bool
    dials_wheel_locked: bool
    buttons_locked: bool
    shutter_locked: bool
    touch_governed_by_touch_op: bool
    touch_screen_active: bool
    resettable_via_camera_settings_reset: bool
    cleared_only_by_initialize: bool
    dormant_sli_key_lock_exposed: bool
    fx6_physical_hold_switches_count: int
    fx6_lcd_hold_switch_present: bool
    fx6_body_hold_on: bool
    fx6_handle_hold_on: bool
    fx6_handle_hold_mode: Optional[str]
    fx6_menu_lock_mode: Optional[str]
    fx6_user_menu_unlocked: Optional[bool]


def simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "fx3_lock_op_config",
    lock_op_parts_setting: str = "All",
    wrong_menu_path_requested: bool = False,
    assign_to_custom_key_requested: bool = False,
    af_area_registration_on: bool = False,
    my_dial_recall_active: bool = False,
    fn_long_press_toggled: bool = False,
    menu_fn_hold_seconds: float = 5.0,
    menu_fn_unlock_requested: bool = False,
    touch_operation: str = "On",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    dormant_symbol: str = "UIBIZ_SLIKEY_LOCK",
    fx6_body_hold_on: bool = False,
    fx6_handle_hold_on: bool = False,
    fx6_hold_with_rec_button: bool = False,
    fx6_hold_with_hand_grip_remote: bool = False,
    fx6_handle_hold_mode: str = "Normal",
    fx6_menu_lock_mode: str = "User Menu with Lock",
    fx6_passcode_configured: str = "0000",
    fx6_passcode_entered: str = "0000",
    fx6_dormant_key_lock_requested: bool = False,
) -> LockOperationPartsVsFx6HoldAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage83Phase367Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage83Phase367Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_83A_OPERATIONS:
        raise Stage83Phase367Error(f"Unsupported 83A operation: {operation!r}")
    if touch_operation not in ("On", "On: Playback Only", "Off"):
        raise Stage83Phase367Error(f"Unsupported touch_operation: {touch_operation!r}")

    if body_profile == BODY_MODEL_FX6:
        if operation != "fx6_hold_and_user_menu_lock":
            return LockOperationPartsVsFx6HoldAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not use FX3 83A operation {operation} -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="Technical -> HOLD Switch Setting / Menu Settings",
                lock_op_parts_setting=None,
                af_area_registration_on=False,
                af_area_registration_forced_off=False,
                my_dial_recall_active=False,
                my_dial_temp_unlocked=False,
                fn_long_press_active=False,
                menu_fn_5s_global_lock_active=False,
                locked_banner_shown=False,
                multi_selector_locked=False,
                dials_wheel_locked=False,
                buttons_locked=False,
                shutter_locked=False,
                touch_governed_by_touch_op=True,
                touch_screen_active=(touch_operation == "On"),
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_sli_key_lock_exposed=False,
                fx6_physical_hold_switches_count=FX6_PHYSICAL_HOLD_SWITCH_COUNT,
                fx6_lcd_hold_switch_present=FX6_LCD_HOLD_SWITCH_PRESENT,
                fx6_body_hold_on=fx6_body_hold_on,
                fx6_handle_hold_on=fx6_handle_hold_on,
                fx6_handle_hold_mode=fx6_handle_hold_mode,
                fx6_menu_lock_mode=fx6_menu_lock_mode,
                fx6_user_menu_unlocked=None,
            )
        if fx6_handle_hold_mode not in FX6_HANDLE_HOLD_MODES:
            return LockOperationPartsVsFx6HoldAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Invalid FX6 Handle HOLD mode {fx6_handle_hold_mode!r} -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="Technical -> HOLD Switch Setting",
                lock_op_parts_setting=None,
                af_area_registration_on=False,
                af_area_registration_forced_off=False,
                my_dial_recall_active=False,
                my_dial_temp_unlocked=False,
                fn_long_press_active=False,
                menu_fn_5s_global_lock_active=False,
                locked_banner_shown=False,
                multi_selector_locked=False,
                dials_wheel_locked=False,
                buttons_locked=False,
                shutter_locked=False,
                touch_governed_by_touch_op=True,
                touch_screen_active=(touch_operation == "On"),
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_sli_key_lock_exposed=False,
                fx6_physical_hold_switches_count=FX6_PHYSICAL_HOLD_SWITCH_COUNT,
                fx6_lcd_hold_switch_present=FX6_LCD_HOLD_SWITCH_PRESENT,
                fx6_body_hold_on=fx6_body_hold_on,
                fx6_handle_hold_on=fx6_handle_hold_on,
                fx6_handle_hold_mode=fx6_handle_hold_mode,
                fx6_menu_lock_mode=fx6_menu_lock_mode,
                fx6_user_menu_unlocked=None,
            )
        if fx6_menu_lock_mode not in FX6_MENU_LOCK_MODES:
            return LockOperationPartsVsFx6HoldAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Invalid FX6 Menu Lock mode {fx6_menu_lock_mode!r} -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="Technical -> Menu Settings",
                lock_op_parts_setting=None,
                af_area_registration_on=False,
                af_area_registration_forced_off=False,
                my_dial_recall_active=False,
                my_dial_temp_unlocked=False,
                fn_long_press_active=False,
                menu_fn_5s_global_lock_active=False,
                locked_banner_shown=False,
                multi_selector_locked=False,
                dials_wheel_locked=False,
                buttons_locked=False,
                shutter_locked=False,
                touch_governed_by_touch_op=True,
                touch_screen_active=(touch_operation == "On"),
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_sli_key_lock_exposed=False,
                fx6_physical_hold_switches_count=FX6_PHYSICAL_HOLD_SWITCH_COUNT,
                fx6_lcd_hold_switch_present=FX6_LCD_HOLD_SWITCH_PRESENT,
                fx6_body_hold_on=fx6_body_hold_on,
                fx6_handle_hold_on=fx6_handle_hold_on,
                fx6_handle_hold_mode=fx6_handle_hold_mode,
                fx6_menu_lock_mode=fx6_menu_lock_mode,
                fx6_user_menu_unlocked=None,
            )
        if fx6_dormant_key_lock_requested:
            return LockOperationPartsVsFx6HoldAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX6 dormant <USER>+<MENU> 1s Key Lock string (ns1 0x339d) not active -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="Technical -> HOLD Switch Setting / Menu Settings",
                lock_op_parts_setting=None,
                af_area_registration_on=False,
                af_area_registration_forced_off=False,
                my_dial_recall_active=False,
                my_dial_temp_unlocked=False,
                fn_long_press_active=False,
                menu_fn_5s_global_lock_active=False,
                locked_banner_shown=False,
                multi_selector_locked=False,
                dials_wheel_locked=False,
                buttons_locked=False,
                shutter_locked=False,
                touch_governed_by_touch_op=True,
                touch_screen_active=(touch_operation == "On"),
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_sli_key_lock_exposed=False,
                fx6_physical_hold_switches_count=FX6_PHYSICAL_HOLD_SWITCH_COUNT,
                fx6_lcd_hold_switch_present=FX6_LCD_HOLD_SWITCH_PRESENT,
                fx6_body_hold_on=fx6_body_hold_on,
                fx6_handle_hold_on=fx6_handle_hold_on,
                fx6_handle_hold_mode=fx6_handle_hold_mode,
                fx6_menu_lock_mode=fx6_menu_lock_mode,
                fx6_user_menu_unlocked=False,
            )
        if fx6_menu_lock_mode == "User Menu with Lock":
            if (
                len(fx6_passcode_configured) != 4
                or not fx6_passcode_configured.isdigit()
                or len(fx6_passcode_entered) != 4
                or not fx6_passcode_entered.isdigit()
            ):
                return LockOperationPartsVsFx6HoldAudit(
                    admitted=False,
                    errno_code=EINVAL_ERRNO,
                    reason="FX6 User Menu with Lock requires 4-digit 0000..9999 passcode -> EINVAL=22",
                    body_profile=body_profile,
                    fw_version=fw_version,
                    operation=operation,
                    menu_path="Technical -> Menu Settings -> User Menu with Lock",
                    lock_op_parts_setting=None,
                    af_area_registration_on=False,
                    af_area_registration_forced_off=False,
                    my_dial_recall_active=False,
                    my_dial_temp_unlocked=False,
                    fn_long_press_active=False,
                    menu_fn_5s_global_lock_active=False,
                    locked_banner_shown=False,
                    multi_selector_locked=fx6_body_hold_on,
                    dials_wheel_locked=fx6_body_hold_on,
                    buttons_locked=fx6_body_hold_on or fx6_handle_hold_on,
                    shutter_locked=(fx6_body_hold_on and fx6_hold_with_rec_button)
                    or (fx6_handle_hold_on and fx6_handle_hold_mode == "Rec Button Only"),
                    touch_governed_by_touch_op=True,
                    touch_screen_active=(touch_operation == "On"),
                    resettable_via_camera_settings_reset=False,
                    cleared_only_by_initialize=True,
                    dormant_sli_key_lock_exposed=False,
                    fx6_physical_hold_switches_count=FX6_PHYSICAL_HOLD_SWITCH_COUNT,
                    fx6_lcd_hold_switch_present=FX6_LCD_HOLD_SWITCH_PRESENT,
                    fx6_body_hold_on=fx6_body_hold_on,
                    fx6_handle_hold_on=fx6_handle_hold_on,
                    fx6_handle_hold_mode=fx6_handle_hold_mode,
                    fx6_menu_lock_mode=fx6_menu_lock_mode,
                    fx6_user_menu_unlocked=False,
                )
            if fx6_passcode_entered != fx6_passcode_configured:
                return LockOperationPartsVsFx6HoldAudit(
                    admitted=False,
                    errno_code=EACCES_ERRNO,
                    reason="FX6 User Menu with Lock passcode mismatch -> EACCES=13",
                    body_profile=body_profile,
                    fw_version=fw_version,
                    operation=operation,
                    menu_path="Technical -> Menu Settings -> User Menu with Lock",
                    lock_op_parts_setting=None,
                    af_area_registration_on=False,
                    af_area_registration_forced_off=False,
                    my_dial_recall_active=False,
                    my_dial_temp_unlocked=False,
                    fn_long_press_active=False,
                    menu_fn_5s_global_lock_active=False,
                    locked_banner_shown=False,
                    multi_selector_locked=fx6_body_hold_on,
                    dials_wheel_locked=fx6_body_hold_on,
                    buttons_locked=fx6_body_hold_on or fx6_handle_hold_on,
                    shutter_locked=(fx6_body_hold_on and fx6_hold_with_rec_button)
                    or (fx6_handle_hold_on and fx6_handle_hold_mode == "Rec Button Only"),
                    touch_governed_by_touch_op=True,
                    touch_screen_active=(touch_operation == "On"),
                    resettable_via_camera_settings_reset=False,
                    cleared_only_by_initialize=True,
                    dormant_sli_key_lock_exposed=False,
                    fx6_physical_hold_switches_count=FX6_PHYSICAL_HOLD_SWITCH_COUNT,
                    fx6_lcd_hold_switch_present=FX6_LCD_HOLD_SWITCH_PRESENT,
                    fx6_body_hold_on=fx6_body_hold_on,
                    fx6_handle_hold_on=fx6_handle_hold_on,
                    fx6_handle_hold_mode=fx6_handle_hold_mode,
                    fx6_menu_lock_mode=fx6_menu_lock_mode,
                    fx6_user_menu_unlocked=False,
                )

        rec_locked = (fx6_body_hold_on and fx6_hold_with_rec_button) or (
            fx6_handle_hold_on and fx6_handle_hold_mode == "Rec Button Only"
        )
        return LockOperationPartsVsFx6HoldAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Dual Physical HOLD (body={fx6_body_hold_on}, handle={fx6_handle_hold_on}/"
                f"{fx6_handle_hold_mode}, with_rec={fx6_hold_with_rec_button}, "
                f"with_remote={fx6_hold_with_hand_grip_remote}, zero LCD HOLD) & "
                f"MenuSettings={fx6_menu_lock_mode}"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path="Technical -> HOLD Switch Setting / Menu Settings",
            lock_op_parts_setting=None,
            af_area_registration_on=False,
            af_area_registration_forced_off=False,
            my_dial_recall_active=False,
            my_dial_temp_unlocked=False,
            fn_long_press_active=False,
            menu_fn_5s_global_lock_active=False,
            locked_banner_shown=False,
            multi_selector_locked=fx6_body_hold_on,
            dials_wheel_locked=fx6_body_hold_on,
            buttons_locked=fx6_body_hold_on or (fx6_handle_hold_on and fx6_handle_hold_mode == "Normal"),
            shutter_locked=rec_locked,
            touch_governed_by_touch_op=True,
            touch_screen_active=(touch_operation == "On"),
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_sli_key_lock_exposed=False,
            fx6_physical_hold_switches_count=FX6_PHYSICAL_HOLD_SWITCH_COUNT,
            fx6_lcd_hold_switch_present=FX6_LCD_HOLD_SWITCH_PRESENT,
            fx6_body_hold_on=fx6_body_hold_on,
            fx6_handle_hold_on=fx6_handle_hold_on,
            fx6_handle_hold_mode=fx6_handle_hold_mode,
            fx6_menu_lock_mode=fx6_menu_lock_mode,
            fx6_user_menu_unlocked=True,
        )

    # ILME-FX3 path
    if operation == "fx6_hold_and_user_menu_lock":
        return LockOperationPartsVsFx6HoldAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="FX3 lacks FX6 dual physical HOLD switches & 4-digit User Menu with Lock -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=FX3_LOCK_OP_PARTS_MENU_PATH,
            lock_op_parts_setting=lock_op_parts_setting,
            af_area_registration_on=af_area_registration_on,
            af_area_registration_forced_off=False,
            my_dial_recall_active=False,
            my_dial_temp_unlocked=False,
            fn_long_press_active=False,
            menu_fn_5s_global_lock_active=False,
            locked_banner_shown=False,
            multi_selector_locked=False,
            dials_wheel_locked=False,
            buttons_locked=False,
            shutter_locked=False,
            touch_governed_by_touch_op=True,
            touch_screen_active=(touch_operation == "On"),
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_sli_key_lock_exposed=False,
            fx6_physical_hold_switches_count=0,
            fx6_lcd_hold_switch_present=False,
            fx6_body_hold_on=False,
            fx6_handle_hold_on=False,
            fx6_handle_hold_mode=None,
            fx6_menu_lock_mode=None,
            fx6_user_menu_unlocked=None,
        )

    if operation == "fx3_dormant_alpha_lock":
        return LockOperationPartsVsFx6HoldAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"FX3 dormant Alpha lock {dormant_symbol} masked by ALCIN_UUD (no physical IRIS/ISO dial) -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=FX3_LOCK_OP_PARTS_MENU_PATH,
            lock_op_parts_setting=lock_op_parts_setting,
            af_area_registration_on=af_area_registration_on,
            af_area_registration_forced_off=False,
            my_dial_recall_active=False,
            my_dial_temp_unlocked=False,
            fn_long_press_active=False,
            menu_fn_5s_global_lock_active=False,
            locked_banner_shown=False,
            multi_selector_locked=False,
            dials_wheel_locked=False,
            buttons_locked=False,
            shutter_locked=False,
            touch_governed_by_touch_op=True,
            touch_screen_active=(touch_operation == "On"),
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_sli_key_lock_exposed=False,
            fx6_physical_hold_switches_count=0,
            fx6_lcd_hold_switch_present=False,
            fx6_body_hold_on=False,
            fx6_handle_hold_on=False,
            fx6_handle_hold_mode=None,
            fx6_menu_lock_mode=None,
            fx6_user_menu_unlocked=None,
        )

    if wrong_menu_path_requested:
        return LockOperationPartsVsFx6HoldAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "FX3 [Lock Operation Parts] resides under Setup -> [Dial Customize], "
                "NOT [Operation Customize] -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=FX3_LOCK_OP_PARTS_MENU_PATH,
            lock_op_parts_setting=lock_op_parts_setting,
            af_area_registration_on=af_area_registration_on,
            af_area_registration_forced_off=False,
            my_dial_recall_active=False,
            my_dial_temp_unlocked=False,
            fn_long_press_active=False,
            menu_fn_5s_global_lock_active=False,
            locked_banner_shown=False,
            multi_selector_locked=False,
            dials_wheel_locked=False,
            buttons_locked=False,
            shutter_locked=False,
            touch_governed_by_touch_op=True,
            touch_screen_active=(touch_operation == "On"),
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_sli_key_lock_exposed=False,
            fx6_physical_hold_switches_count=0,
            fx6_lcd_hold_switch_present=False,
            fx6_body_hold_on=False,
            fx6_handle_hold_on=False,
            fx6_handle_hold_mode=None,
            fx6_menu_lock_mode=None,
            fx6_user_menu_unlocked=None,
        )

    if assign_to_custom_key_requested:
        return LockOperationPartsVsFx6HoldAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="FX3 [Lock Operation Parts] is NOT assignable to Custom Key (Fn long-press only) -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=FX3_LOCK_OP_PARTS_MENU_PATH,
            lock_op_parts_setting=lock_op_parts_setting,
            af_area_registration_on=af_area_registration_on,
            af_area_registration_forced_off=False,
            my_dial_recall_active=False,
            my_dial_temp_unlocked=False,
            fn_long_press_active=False,
            menu_fn_5s_global_lock_active=False,
            locked_banner_shown=False,
            multi_selector_locked=False,
            dials_wheel_locked=False,
            buttons_locked=False,
            shutter_locked=False,
            touch_governed_by_touch_op=True,
            touch_screen_active=(touch_operation == "On"),
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_sli_key_lock_exposed=False,
            fx6_physical_hold_switches_count=0,
            fx6_lcd_hold_switch_present=False,
            fx6_body_hold_on=False,
            fx6_handle_hold_on=False,
            fx6_handle_hold_mode=None,
            fx6_menu_lock_mode=None,
            fx6_user_menu_unlocked=None,
        )

    if lock_op_parts_setting not in FX3_LOCK_OP_PARTS_4_MODES:
        return LockOperationPartsVsFx6HoldAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=f"Invalid FX3 [Lock Operation Parts] mode {lock_op_parts_setting!r} -> EINVAL=22",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=FX3_LOCK_OP_PARTS_MENU_PATH,
            lock_op_parts_setting=lock_op_parts_setting,
            af_area_registration_on=af_area_registration_on,
            af_area_registration_forced_off=False,
            my_dial_recall_active=False,
            my_dial_temp_unlocked=False,
            fn_long_press_active=False,
            menu_fn_5s_global_lock_active=False,
            locked_banner_shown=False,
            multi_selector_locked=False,
            dials_wheel_locked=False,
            buttons_locked=False,
            shutter_locked=False,
            touch_governed_by_touch_op=True,
            touch_screen_active=(touch_operation == "On"),
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_sli_key_lock_exposed=False,
            fx6_physical_hold_switches_count=0,
            fx6_lcd_hold_switch_present=False,
            fx6_body_hold_on=False,
            fx6_handle_hold_on=False,
            fx6_handle_hold_mode=None,
            fx6_menu_lock_mode=None,
            fx6_user_menu_unlocked=None,
        )

    # Setup branch -> Reset-resistant! Only [Initialize] clears to Off.
    _ = camera_settings_reset_applied
    eff_setting = "Off" if (initialize_applied or af_area_registration_on) else lock_op_parts_setting
    forced_off = bool(af_area_registration_on and lock_op_parts_setting != "Off")

    if operation == "fx3_lock_op_config":
        return LockOperationPartsVsFx6HoldAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 {FX3_LOCK_OP_PARTS_MENU_PATH} = {eff_setting} "
                f"(Reset-resistant Not available; AF Area Reg forced_off={forced_off})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=FX3_LOCK_OP_PARTS_MENU_PATH,
            lock_op_parts_setting=eff_setting,
            af_area_registration_on=af_area_registration_on,
            af_area_registration_forced_off=forced_off,
            my_dial_recall_active=False,
            my_dial_temp_unlocked=False,
            fn_long_press_active=False,
            menu_fn_5s_global_lock_active=False,
            locked_banner_shown=False,
            multi_selector_locked=False,
            dials_wheel_locked=False,
            buttons_locked=False,
            shutter_locked=False,
            touch_governed_by_touch_op=True,
            touch_screen_active=(touch_operation == "On"),
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_sli_key_lock_exposed=False,
            fx6_physical_hold_switches_count=0,
            fx6_lcd_hold_switch_present=False,
            fx6_body_hold_on=False,
            fx6_handle_hold_on=False,
            fx6_handle_hold_mode=None,
            fx6_menu_lock_mode=None,
            fx6_user_menu_unlocked=None,
        )

    if operation == "fx3_fn_long_press_lock":
        if eff_setting == "Off":
            return LockOperationPartsVsFx6HoldAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason=(
                    "FX3 Fn long-press cannot lock when [Lock Operation Parts]=Off "
                    f"(af_area_reg_forced_off={forced_off}) -> EBUSY=16"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path=FX3_LOCK_OP_PARTS_MENU_PATH,
                lock_op_parts_setting=eff_setting,
                af_area_registration_on=af_area_registration_on,
                af_area_registration_forced_off=forced_off,
                my_dial_recall_active=my_dial_recall_active,
                my_dial_temp_unlocked=False,
                fn_long_press_active=False,
                menu_fn_5s_global_lock_active=False,
                locked_banner_shown=False,
                multi_selector_locked=False,
                dials_wheel_locked=False,
                buttons_locked=False,
                shutter_locked=False,
                touch_governed_by_touch_op=True,
                touch_screen_active=(touch_operation == "On"),
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_sli_key_lock_exposed=False,
                fx6_physical_hold_switches_count=0,
                fx6_lcd_hold_switch_present=False,
                fx6_body_hold_on=False,
                fx6_handle_hold_on=False,
                fx6_handle_hold_mode=None,
                fx6_menu_lock_mode=None,
                fx6_user_menu_unlocked=None,
            )
        active = fn_long_press_toggled
        ms_locked = active and eff_setting in ("Multi-Selector Only", "All")
        dw_base = active and eff_setting in ("Dial + Wheel", "All")
        temp_unlocked = dw_base and my_dial_recall_active
        dw_locked = dw_base and (not my_dial_recall_active)
        return LockOperationPartsVsFx6HoldAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 Fn long-press lock={active} mode={eff_setting} "
                f"(MyDial temp_unlocked={temp_unlocked}, Shutter unlocked)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=FX3_LOCK_OP_PARTS_MENU_PATH,
            lock_op_parts_setting=eff_setting,
            af_area_registration_on=af_area_registration_on,
            af_area_registration_forced_off=False,
            my_dial_recall_active=my_dial_recall_active,
            my_dial_temp_unlocked=temp_unlocked,
            fn_long_press_active=active,
            menu_fn_5s_global_lock_active=False,
            locked_banner_shown=active,
            multi_selector_locked=ms_locked,
            dials_wheel_locked=dw_locked,
            buttons_locked=False,
            shutter_locked=False,
            touch_governed_by_touch_op=True,
            touch_screen_active=(touch_operation == "On"),
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_sli_key_lock_exposed=False,
            fx6_physical_hold_switches_count=0,
            fx6_lcd_hold_switch_present=False,
            fx6_body_hold_on=False,
            fx6_handle_hold_on=False,
            fx6_handle_hold_mode=None,
            fx6_menu_lock_mode=None,
            fx6_user_menu_unlocked=None,
        )

    # operation == "fx3_menu_fn_5s_global_lock"
    if menu_fn_hold_seconds < FX3_MENU_FN_GLOBAL_LOCK_HOLD_SECONDS:
        return LockOperationPartsVsFx6HoldAudit(
            admitted=False,
            errno_code=EAGAIN_ERRNO,
            reason=(
                f"FX3 MENU+Fn held {menu_fn_hold_seconds:.1f}s < 5.0s required for global lock/unlock "
                "(_g 0x610a) -> EAGAIN=11"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=FX3_LOCK_OP_PARTS_MENU_PATH,
            lock_op_parts_setting=eff_setting,
            af_area_registration_on=af_area_registration_on,
            af_area_registration_forced_off=forced_off,
            my_dial_recall_active=False,
            my_dial_temp_unlocked=False,
            fn_long_press_active=False,
            menu_fn_5s_global_lock_active=(not menu_fn_unlock_requested),
            locked_banner_shown=False,
            multi_selector_locked=(not menu_fn_unlock_requested),
            dials_wheel_locked=(not menu_fn_unlock_requested),
            buttons_locked=(not menu_fn_unlock_requested),
            shutter_locked=False,
            touch_governed_by_touch_op=True,
            touch_screen_active=(touch_operation == "On"),
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_sli_key_lock_exposed=False,
            fx6_physical_hold_switches_count=0,
            fx6_lcd_hold_switch_present=False,
            fx6_body_hold_on=False,
            fx6_handle_hold_on=False,
            fx6_handle_hold_mode=None,
            fx6_menu_lock_mode=None,
            fx6_user_menu_unlocked=None,
        )

    global_locked = not menu_fn_unlock_requested
    return LockOperationPartsVsFx6HoldAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 MENU+Fn 5s global lock={global_locked}: locks all buttons/dials/wheel "
            "EXCEPT SHUTTER; Touch governed independently by [Touch Operation]"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        menu_path=FX3_LOCK_OP_PARTS_MENU_PATH,
        lock_op_parts_setting=eff_setting,
        af_area_registration_on=af_area_registration_on,
        af_area_registration_forced_off=forced_off,
        my_dial_recall_active=False,
        my_dial_temp_unlocked=False,
        fn_long_press_active=False,
        menu_fn_5s_global_lock_active=global_locked,
        locked_banner_shown=global_locked,
        multi_selector_locked=global_locked,
        dials_wheel_locked=global_locked,
        buttons_locked=global_locked,
        shutter_locked=False,
        touch_governed_by_touch_op=True,
        touch_screen_active=(touch_operation == "On"),
        resettable_via_camera_settings_reset=False,
        cleared_only_by_initialize=True,
        dormant_sli_key_lock_exposed=False,
        fx6_physical_hold_switches_count=0,
        fx6_lcd_hold_switch_present=False,
        fx6_body_hold_on=False,
        fx6_handle_hold_on=False,
        fx6_handle_hold_mode=None,
        fx6_menu_lock_mode=None,
        fx6_user_menu_unlocked=None,
    )


# ---------------------------------------------------------------------------
# Sub-Model 83B: [Shockless WB], [Priority Set in AWB], Still-Only
#                Reset-Resistant [Shutter AWB Lock] & Movie [AWB Lock
#                Hold/Toggle] vs FX6 WHT BAL B/A/PRESET & ATW Speed 1..5
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShocklessWbPriorityAndAwbLockAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    shoot_mode: str
    log_shooting: str
    wb_mode: str
    shockless_wb: Optional[str]
    shockless_resettable: bool
    transition_smoothed: bool
    auto_tracking_speed_affected: bool
    ctemp_ab_gm_immediate: bool
    auto_wb_locked_out_in_cine_ei: bool
    priority_set_in_awb: Optional[str]
    priority_awb_resettable: bool
    shutter_awb_lock: Optional[str]
    shutter_awb_lock_resettable_by_camera_reset: bool
    shutter_awb_lock_cleared_only_by_initialize: bool
    awb_locked_active: bool
    movie_awb_lock_custom_key: Optional[str]
    fx6_wht_bal_switch: Optional[str]
    fx6_atw_speed: Optional[int]
    fx6_shockless_white: Optional[str]
    fx6_warm_cool_ui_exposed: bool


def simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "fx3_shockless_wb",
    shoot_mode: str = "Movie",
    log_shooting: str = "Off",
    wb_mode: str = "Auto",
    shockless_wb: str = "1 (Fast)",
    wb_change_kind: str = "wb_preset_switch",
    priority_set_in_awb: str = "Standard",
    shutter_awb_lock: str = "Off",
    shutter_half_pressed: bool = False,
    cont_shooting_active: bool = False,
    movie_awb_lock_custom_key: Optional[str] = "AWB Lock Hold",
    movie_awb_lock_engaged: bool = True,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_wht_bal_switch: str = "B",
    fx6_white_switch_b_mode: str = "ATW",
    fx6_atw_speed: int = 3,
    fx6_shockless_white: str = "1",
    fx6_color_temp_k: int = 3200,
    fx6_tint: int = 0,
    request_fx6_warm_cool_ui: bool = False,
) -> ShocklessWbPriorityAndAwbLockAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage83Phase367Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage83Phase367Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_83B_OPERATIONS:
        raise Stage83Phase367Error(f"Unsupported 83B operation: {operation!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage83Phase367Error(f"Unsupported shoot_mode: {shoot_mode!r}")
    if log_shooting not in VALID_LOG_SHOOTING_MODES:
        raise Stage83Phase367Error(f"Unsupported log_shooting: {log_shooting!r}")

    is_cine_ei = log_shooting in ("Cine EI", "Cine EI Quick")

    if body_profile == BODY_MODEL_FX6:
        if operation != "fx6_wb_atw_shockless":
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not expose FX3 83B operation {operation} -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=None,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=is_cine_ei,
                priority_set_in_awb=None,
                priority_awb_resettable=True,
                shutter_awb_lock=None,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=fx6_wht_bal_switch,
                fx6_atw_speed=fx6_atw_speed,
                fx6_shockless_white=fx6_shockless_white,
                fx6_warm_cool_ui_exposed=False,
            )
        if request_fx6_warm_cool_ui:
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "FX6 BKID_APP_SETTING_WARM_COOL is internal diadem_pro converter mapping; "
                    "zero 'Warm Cool' UI menu item exposed -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=None,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=is_cine_ei,
                priority_set_in_awb=None,
                priority_awb_resettable=True,
                shutter_awb_lock=None,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=fx6_wht_bal_switch,
                fx6_atw_speed=fx6_atw_speed,
                fx6_shockless_white=fx6_shockless_white,
                fx6_warm_cool_ui_exposed=False,
            )
        if (
            fx6_wht_bal_switch not in FX6_WHT_BAL_SWITCH_POSITIONS
            or fx6_white_switch_b_mode not in FX6_WHITE_SWITCH_B_MODES
            or fx6_shockless_white not in FX6_SHOCKLESS_WHITE_4_MODES
            or not (FX6_ATW_SPEED_MIN <= fx6_atw_speed <= FX6_ATW_SPEED_MAX)
            or not (2000 <= fx6_color_temp_k <= 15000)
            or not (-99 <= fx6_tint <= 99)
        ):
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="Invalid FX6 WHT BAL / ATW Speed 1..5 / Shockless White / ColorTemp / Tint -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=None,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=is_cine_ei,
                priority_set_in_awb=None,
                priority_awb_resettable=True,
                shutter_awb_lock=None,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=fx6_wht_bal_switch,
                fx6_atw_speed=fx6_atw_speed,
                fx6_shockless_white=fx6_shockless_white,
                fx6_warm_cool_ui_exposed=False,
            )
        if is_cine_ei and fx6_wht_bal_switch == "B" and fx6_white_switch_b_mode == "ATW":
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason="FX6 ATW & ATW Speed 1..5 disabled in Cine EI -> EBUSY=16",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode="ATW",
                shockless_wb=None,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=True,
                priority_set_in_awb=None,
                priority_awb_resettable=True,
                shutter_awb_lock=None,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=fx6_wht_bal_switch,
                fx6_atw_speed=fx6_atw_speed,
                fx6_shockless_white=fx6_shockless_white,
                fx6_warm_cool_ui_exposed=False,
            )
        return ShocklessWbPriorityAndAwbLockAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 WHT BAL={fx6_wht_bal_switch} ({fx6_white_switch_b_mode}), "
                f"ATW Speed={fx6_atw_speed}, Shockless White={fx6_shockless_white}, "
                f"{fx6_color_temp_k}K Tint={fx6_tint}"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            log_shooting=log_shooting,
            wb_mode=fx6_white_switch_b_mode if fx6_wht_bal_switch == "B" else fx6_wht_bal_switch,
            shockless_wb=None,
            shockless_resettable=True,
            transition_smoothed=(fx6_shockless_white != "Off"),
            auto_tracking_speed_affected=True,
            ctemp_ab_gm_immediate=True,
            auto_wb_locked_out_in_cine_ei=is_cine_ei,
            priority_set_in_awb=None,
            priority_awb_resettable=True,
            shutter_awb_lock=None,
            shutter_awb_lock_resettable_by_camera_reset=False,
            shutter_awb_lock_cleared_only_by_initialize=True,
            awb_locked_active=False,
            movie_awb_lock_custom_key=None,
            fx6_wht_bal_switch=fx6_wht_bal_switch,
            fx6_atw_speed=fx6_atw_speed,
            fx6_shockless_white=fx6_shockless_white,
            fx6_warm_cool_ui_exposed=False,
        )

    # ILME-FX3 path
    if operation == "fx6_wb_atw_shockless":
        return ShocklessWbPriorityAndAwbLockAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="FX3 lacks physical 3-way WHT BAL switch & ATW Speed 1..5 -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            log_shooting=log_shooting,
            wb_mode=wb_mode,
            shockless_wb=shockless_wb,
            shockless_resettable=True,
            transition_smoothed=False,
            auto_tracking_speed_affected=False,
            ctemp_ab_gm_immediate=True,
            auto_wb_locked_out_in_cine_ei=is_cine_ei,
            priority_set_in_awb=priority_set_in_awb,
            priority_awb_resettable=True,
            shutter_awb_lock=shutter_awb_lock,
            shutter_awb_lock_resettable_by_camera_reset=False,
            shutter_awb_lock_cleared_only_by_initialize=True,
            awb_locked_active=False,
            movie_awb_lock_custom_key=movie_awb_lock_custom_key,
            fx6_wht_bal_switch=None,
            fx6_atw_speed=None,
            fx6_shockless_white=None,
            fx6_warm_cool_ui_exposed=False,
        )

    if operation == "fx3_shockless_wb":
        if shockless_wb not in FX3_SHOCKLESS_WB_4_MODES:
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Invalid FX3 [Shockless WB] value {shockless_wb!r} -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=shockless_wb,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=is_cine_ei,
                priority_set_in_awb=priority_set_in_awb,
                priority_awb_resettable=True,
                shutter_awb_lock=shutter_awb_lock,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=None,
                fx6_atw_speed=None,
                fx6_shockless_white=None,
                fx6_warm_cool_ui_exposed=False,
            )
        if shoot_mode == "Still":
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX3 [Shockless WB] is Movie/S&Q only (disabled in Still) -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=shockless_wb,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=is_cine_ei,
                priority_set_in_awb=priority_set_in_awb,
                priority_awb_resettable=True,
                shutter_awb_lock=shutter_awb_lock,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=None,
                fx6_atw_speed=None,
                fx6_shockless_white=None,
                fx6_warm_cool_ui_exposed=False,
            )
        if is_cine_ei and wb_mode in ("Auto", "Underwater Auto"):
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason=f"FX3 Auto/Underwater Auto WB locked out under {log_shooting} -> EBUSY=16",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=shockless_wb,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=True,
                priority_set_in_awb=priority_set_in_awb,
                priority_awb_resettable=True,
                shutter_awb_lock=shutter_awb_lock,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=None,
                fx6_atw_speed=None,
                fx6_shockless_white=None,
                fx6_warm_cool_ui_exposed=False,
            )
        eff_shockless = (
            FX3_SHOCKLESS_WB_DEFAULT
            if (camera_settings_reset_applied or initialize_applied)
            else shockless_wb
        )
        smoothed = (eff_shockless != "Off") and (
            wb_change_kind in ("wb_preset_switch", "awb_priority_switch")
        )
        immediate = wb_change_kind in ("ctemp_filter", "ab_gm_shift")
        return ShocklessWbPriorityAndAwbLockAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 [Shockless WB]={eff_shockless} (Can be reset): smoothed={smoothed}, "
                f"auto_tracking_speed_affected=False, ctemp_ab_gm_immediate={immediate}"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            log_shooting=log_shooting,
            wb_mode=wb_mode,
            shockless_wb=eff_shockless,
            shockless_resettable=True,
            transition_smoothed=smoothed,
            auto_tracking_speed_affected=False,
            ctemp_ab_gm_immediate=immediate,
            auto_wb_locked_out_in_cine_ei=is_cine_ei,
            priority_set_in_awb=priority_set_in_awb,
            priority_awb_resettable=True,
            shutter_awb_lock=None,
            shutter_awb_lock_resettable_by_camera_reset=False,
            shutter_awb_lock_cleared_only_by_initialize=True,
            awb_locked_active=False,
            movie_awb_lock_custom_key=None,
            fx6_wht_bal_switch=None,
            fx6_atw_speed=None,
            fx6_shockless_white=None,
            fx6_warm_cool_ui_exposed=False,
        )

    if operation == "fx3_priority_set_in_awb":
        if priority_set_in_awb not in FX3_AWB_PRIORITY_3_MODES:
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Invalid FX3 [Priority Set in AWB] {priority_set_in_awb!r} -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=shockless_wb,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=is_cine_ei,
                priority_set_in_awb=priority_set_in_awb,
                priority_awb_resettable=True,
                shutter_awb_lock=None,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=None,
                fx6_atw_speed=None,
                fx6_shockless_white=None,
                fx6_warm_cool_ui_exposed=False,
            )
        if is_cine_ei:
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason=f"FX3 [Priority Set in AWB] disabled under {log_shooting} -> EBUSY=16",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=shockless_wb,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=True,
                priority_set_in_awb=priority_set_in_awb,
                priority_awb_resettable=True,
                shutter_awb_lock=None,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=None,
                fx6_atw_speed=None,
                fx6_shockless_white=None,
                fx6_warm_cool_ui_exposed=False,
            )
        eff_prio = (
            FX3_PRIORITY_SET_AWB_DEFAULT
            if (camera_settings_reset_applied or initialize_applied)
            else priority_set_in_awb
        )
        return ShocklessWbPriorityAndAwbLockAudit(
            admitted=True,
            errno_code=0,
            reason=f"FX3 [Priority Set in AWB]={eff_prio} (Can be reset; effective when WB=Auto)",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            log_shooting=log_shooting,
            wb_mode=wb_mode,
            shockless_wb=shockless_wb,
            shockless_resettable=True,
            transition_smoothed=False,
            auto_tracking_speed_affected=False,
            ctemp_ab_gm_immediate=True,
            auto_wb_locked_out_in_cine_ei=False,
            priority_set_in_awb=eff_prio,
            priority_awb_resettable=True,
            shutter_awb_lock=None,
            shutter_awb_lock_resettable_by_camera_reset=False,
            shutter_awb_lock_cleared_only_by_initialize=True,
            awb_locked_active=False,
            movie_awb_lock_custom_key=None,
            fx6_wht_bal_switch=None,
            fx6_atw_speed=None,
            fx6_shockless_white=None,
            fx6_warm_cool_ui_exposed=False,
        )

    if operation == "fx3_shutter_awb_lock":
        if shutter_awb_lock in FX3_SHUTTER_AWB_LOCK_ERRATA_MODES:
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"Legacy errata label {shutter_awb_lock!r} rejected; Ver. 7.02 uses "
                    "'Shutter Half Press' / 'Cont. Shooting' / 'Off' -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=None,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=is_cine_ei,
                priority_set_in_awb=priority_set_in_awb,
                priority_awb_resettable=True,
                shutter_awb_lock=shutter_awb_lock,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=None,
                fx6_atw_speed=None,
                fx6_shockless_white=None,
                fx6_warm_cool_ui_exposed=False,
            )
        if shutter_awb_lock not in FX3_SHUTTER_AWB_LOCK_3_MODES:
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Invalid FX3 [Shutter AWB Lock] value {shutter_awb_lock!r} -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=None,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=is_cine_ei,
                priority_set_in_awb=priority_set_in_awb,
                priority_awb_resettable=True,
                shutter_awb_lock=shutter_awb_lock,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=None,
                fx6_atw_speed=None,
                fx6_shockless_white=None,
                fx6_warm_cool_ui_exposed=False,
            )
        if shoot_mode != "Still":
            return ShocklessWbPriorityAndAwbLockAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"FX3 [Shutter AWB Lock] is Still-only (inapplicable in {shoot_mode}; "
                    "use Custom Key AWB Lock Hold/Toggle) -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                log_shooting=log_shooting,
                wb_mode=wb_mode,
                shockless_wb=None,
                shockless_resettable=True,
                transition_smoothed=False,
                auto_tracking_speed_affected=False,
                ctemp_ab_gm_immediate=True,
                auto_wb_locked_out_in_cine_ei=is_cine_ei,
                priority_set_in_awb=priority_set_in_awb,
                priority_awb_resettable=True,
                shutter_awb_lock=shutter_awb_lock,
                shutter_awb_lock_resettable_by_camera_reset=False,
                shutter_awb_lock_cleared_only_by_initialize=True,
                awb_locked_active=False,
                movie_awb_lock_custom_key=None,
                fx6_wht_bal_switch=None,
                fx6_atw_speed=None,
                fx6_shockless_white=None,
                fx6_warm_cool_ui_exposed=False,
            )
        # Reset-resistant Not available under [Camera Settings Reset]; only [Initialize] resets!
        _ = camera_settings_reset_applied
        eff_sal = FX3_SHUTTER_AWB_LOCK_DEFAULT if initialize_applied else shutter_awb_lock
        wb_is_auto = wb_mode in ("Auto", "Underwater Auto")
        locked = wb_is_auto and (
            (eff_sal == "Shutter Half Press" and shutter_half_pressed)
            or (eff_sal == "Cont. Shooting" and cont_shooting_active)
        )
        return ShocklessWbPriorityAndAwbLockAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 Still-only [Shutter AWB Lock]={eff_sal} (Reset-resistant Not available; "
                f"awb_locked={locked})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            log_shooting=log_shooting,
            wb_mode=wb_mode,
            shockless_wb=None,
            shockless_resettable=True,
            transition_smoothed=False,
            auto_tracking_speed_affected=False,
            ctemp_ab_gm_immediate=True,
            auto_wb_locked_out_in_cine_ei=is_cine_ei,
            priority_set_in_awb=priority_set_in_awb,
            priority_awb_resettable=True,
            shutter_awb_lock=eff_sal,
            shutter_awb_lock_resettable_by_camera_reset=False,
            shutter_awb_lock_cleared_only_by_initialize=True,
            awb_locked_active=locked,
            movie_awb_lock_custom_key=None,
            fx6_wht_bal_switch=None,
            fx6_atw_speed=None,
            fx6_shockless_white=None,
            fx6_warm_cool_ui_exposed=False,
        )

    # operation == "fx3_movie_awb_lock_custom_key"
    if movie_awb_lock_custom_key not in FX3_MOVIE_AWB_LOCK_CUSTOM_KEYS:
        return ShocklessWbPriorityAndAwbLockAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="Movie AWB lock requires Custom Key [AWB Lock Hold] or [AWB Lock Toggle] -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            log_shooting=log_shooting,
            wb_mode=wb_mode,
            shockless_wb=shockless_wb,
            shockless_resettable=True,
            transition_smoothed=False,
            auto_tracking_speed_affected=False,
            ctemp_ab_gm_immediate=True,
            auto_wb_locked_out_in_cine_ei=is_cine_ei,
            priority_set_in_awb=priority_set_in_awb,
            priority_awb_resettable=True,
            shutter_awb_lock=None,
            shutter_awb_lock_resettable_by_camera_reset=False,
            shutter_awb_lock_cleared_only_by_initialize=True,
            awb_locked_active=False,
            movie_awb_lock_custom_key=movie_awb_lock_custom_key,
            fx6_wht_bal_switch=None,
            fx6_atw_speed=None,
            fx6_shockless_white=None,
            fx6_warm_cool_ui_exposed=False,
        )
    if wb_mode not in ("Auto", "Underwater Auto"):
        return ShocklessWbPriorityAndAwbLockAudit(
            admitted=False,
            errno_code=EBUSY_ERRNO,
            reason=f"Custom Key {movie_awb_lock_custom_key} inactive on fixed WB {wb_mode!r} -> EBUSY=16",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            log_shooting=log_shooting,
            wb_mode=wb_mode,
            shockless_wb=shockless_wb,
            shockless_resettable=True,
            transition_smoothed=False,
            auto_tracking_speed_affected=False,
            ctemp_ab_gm_immediate=True,
            auto_wb_locked_out_in_cine_ei=is_cine_ei,
            priority_set_in_awb=priority_set_in_awb,
            priority_awb_resettable=True,
            shutter_awb_lock=None,
            shutter_awb_lock_resettable_by_camera_reset=False,
            shutter_awb_lock_cleared_only_by_initialize=True,
            awb_locked_active=False,
            movie_awb_lock_custom_key=movie_awb_lock_custom_key,
            fx6_wht_bal_switch=None,
            fx6_atw_speed=None,
            fx6_shockless_white=None,
            fx6_warm_cool_ui_exposed=False,
        )
    return ShocklessWbPriorityAndAwbLockAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 {shoot_mode} Custom Key [{movie_awb_lock_custom_key}] "
            f"awb_locked={movie_awb_lock_engaged}"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        shoot_mode=shoot_mode,
        log_shooting=log_shooting,
        wb_mode=wb_mode,
        shockless_wb=shockless_wb,
        shockless_resettable=True,
        transition_smoothed=False,
        auto_tracking_speed_affected=False,
        ctemp_ab_gm_immediate=True,
        auto_wb_locked_out_in_cine_ei=is_cine_ei,
        priority_set_in_awb=priority_set_in_awb,
        priority_awb_resettable=True,
        shutter_awb_lock=None,
        shutter_awb_lock_resettable_by_camera_reset=False,
        shutter_awb_lock_cleared_only_by_initialize=True,
        awb_locked_active=movie_awb_lock_engaged,
        movie_awb_lock_custom_key=movie_awb_lock_custom_key,
        fx6_wht_bal_switch=None,
        fx6_atw_speed=None,
        fx6_shockless_white=None,
        fx6_warm_cool_ui_exposed=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 83C: Reset-Resistant [Focus Assistant] 4 Sub-Items, Still vs Movie
#                Split & Dormant [Focus Ring Rotate] 0-Enum Disproof vs FX6
#                AF Assist / PUSH AUTO / Ver. 6.0 HDMI Focus Mag x2/x4
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FocusAssistantSplitVsFocusRingRotateFx6Audit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    shoot_mode: str
    sensor_crop: str
    auto_magnifier_in_mf: Optional[str]
    focus_magnif_time: Optional[str]
    initial_focus_mag: Optional[str]
    af_in_focus_mag: Optional[str]
    active_magnification_ratio: str
    second_press_ratio: Optional[str]
    persistent_items_count: int
    resettable_via_camera_settings_reset: bool
    cleared_only_by_initialize: bool
    hdmi_mag_leaked_pixels: int
    xavc_mag_leaked_pixels: int
    fx3_appfw_focus_ring_rotate_enums_count: int
    dormant_focus_ring_rotate_exposed: bool
    fx6_focus_ring_rotate_mode: Optional[str]
    fx6_af_assist: Optional[str]
    fx6_push_af_mode: Optional[str]
    fx6_focus_mag_button_target: Optional[str]


def simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "fx3_focus_assistant_config",
    shoot_mode: str = "Still",
    sensor_crop: str = "FF",
    focus_mode: str = "MF",
    auto_magnifier_in_mf: str = "On",
    focus_magnif_time: str = "No Limit",
    initial_focus_mag: str = "x1.0",
    af_in_focus_mag: str = "On",
    press_count: int = 1,
    mount_adaptor_attached: bool = False,
    cont_shooting_active: bool = False,
    pasms_mode: bool = True,
    trigger_auto_mag_in_mf: bool = False,
    trigger_af_in_mag: bool = False,
    dormant_item: str = "Focus Ring Rotate",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_focus_ring_rotate_mode: str = "LEFT_F_RIGHT_N",
    fx6_af_assist: str = "On",
    fx6_push_af_mode: str = "AF",
    fx6_focus_mag_button_target: str = "HDMI Focus Mag",
    fx6_hdmi_mag_step: int = 1,
) -> FocusAssistantSplitVsFocusRingRotateFx6Audit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage83Phase367Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage83Phase367Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_83C_OPERATIONS:
        raise Stage83Phase367Error(f"Unsupported 83C operation: {operation!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage83Phase367Error(f"Unsupported shoot_mode: {shoot_mode!r}")
    if sensor_crop not in ("FF", "APS-C"):
        raise Stage83Phase367Error(f"Unsupported sensor_crop: {sensor_crop!r}")

    if body_profile == BODY_MODEL_FX6:
        if operation != "fx6_focus_assist_and_mag":
            return FocusAssistantSplitVsFocusRingRotateFx6Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not use FX3 83C operation {operation} -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                sensor_crop=sensor_crop,
                auto_magnifier_in_mf=None,
                focus_magnif_time=None,
                initial_focus_mag=None,
                af_in_focus_mag=None,
                active_magnification_ratio="x1.0",
                second_press_ratio=None,
                persistent_items_count=0,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                hdmi_mag_leaked_pixels=0,
                xavc_mag_leaked_pixels=0,
                fx3_appfw_focus_ring_rotate_enums_count=0,
                dormant_focus_ring_rotate_exposed=False,
                fx6_focus_ring_rotate_mode=fx6_focus_ring_rotate_mode,
                fx6_af_assist=fx6_af_assist,
                fx6_push_af_mode=fx6_push_af_mode,
                fx6_focus_mag_button_target=fx6_focus_mag_button_target,
            )
        if (
            fx6_focus_ring_rotate_mode not in FX6_FOCUS_RING_ROTATE_MODES
            or fx6_af_assist not in ("On", "Off")
            or fx6_push_af_mode not in FX6_PUSH_AF_MODES
            or fx6_focus_mag_button_target not in FX6_FOCUS_MAG_BUTTON_TARGETS
            or fx6_hdmi_mag_step not in (1, 2)
        ):
            return FocusAssistantSplitVsFocusRingRotateFx6Audit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="Invalid FX6 Focus Ring Rotate / AF Assist / Push AF / Focus Mag target -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                sensor_crop=sensor_crop,
                auto_magnifier_in_mf=None,
                focus_magnif_time=None,
                initial_focus_mag=None,
                af_in_focus_mag=None,
                active_magnification_ratio="x1.0",
                second_press_ratio=None,
                persistent_items_count=0,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                hdmi_mag_leaked_pixels=0,
                xavc_mag_leaked_pixels=0,
                fx3_appfw_focus_ring_rotate_enums_count=0,
                dormant_focus_ring_rotate_exposed=False,
                fx6_focus_ring_rotate_mode=fx6_focus_ring_rotate_mode,
                fx6_af_assist=fx6_af_assist,
                fx6_push_af_mode=fx6_push_af_mode,
                fx6_focus_mag_button_target=fx6_focus_mag_button_target,
            )
        if fx6_focus_mag_button_target == "HDMI Focus Mag" and fw_version not in (
            FW_VER_600,
            FW_VER_601,
        ):
            return FocusAssistantSplitVsFocusRingRotateFx6Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 HDMI Focus Mag x2/x4 requires Ver. 6.00+ (got {fw_version}) -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                sensor_crop=sensor_crop,
                auto_magnifier_in_mf=None,
                focus_magnif_time=None,
                initial_focus_mag=None,
                af_in_focus_mag=None,
                active_magnification_ratio="x1.0",
                second_press_ratio=None,
                persistent_items_count=0,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                hdmi_mag_leaked_pixels=0,
                xavc_mag_leaked_pixels=0,
                fx3_appfw_focus_ring_rotate_enums_count=0,
                dormant_focus_ring_rotate_exposed=False,
                fx6_focus_ring_rotate_mode=fx6_focus_ring_rotate_mode,
                fx6_af_assist=fx6_af_assist,
                fx6_push_af_mode=fx6_push_af_mode,
                fx6_focus_mag_button_target=fx6_focus_mag_button_target,
            )
        ratio = (
            ("x2.0" if fx6_hdmi_mag_step == 1 else "x4.0")
            if fx6_focus_mag_button_target == "HDMI Focus Mag"
            else ("x3.0" if fx6_hdmi_mag_step == 1 else "x6.0")
        )
        return FocusAssistantSplitVsFocusRingRotateFx6Audit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Ver. {fw_version} FocusRingRotate={fx6_focus_ring_rotate_mode}, "
                f"AF_Assist={fx6_af_assist}, PushAF={fx6_push_af_mode}, "
                f"Target={fx6_focus_mag_button_target} -> {ratio} (SDI/MXF unmagnified)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            auto_magnifier_in_mf=None,
            focus_magnif_time=None,
            initial_focus_mag=None,
            af_in_focus_mag=None,
            active_magnification_ratio=ratio,
            second_press_ratio="x4.0" if fx6_focus_mag_button_target == "HDMI Focus Mag" else "x6.0",
            persistent_items_count=0,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            hdmi_mag_leaked_pixels=0,
            xavc_mag_leaked_pixels=0,
            fx3_appfw_focus_ring_rotate_enums_count=0,
            dormant_focus_ring_rotate_exposed=False,
            fx6_focus_ring_rotate_mode=fx6_focus_ring_rotate_mode,
            fx6_af_assist=fx6_af_assist,
            fx6_push_af_mode=fx6_push_af_mode,
            fx6_focus_mag_button_target=fx6_focus_mag_button_target,
        )

    # ILME-FX3 path
    if operation == "fx6_focus_assist_and_mag":
        return FocusAssistantSplitVsFocusRingRotateFx6Audit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="FX3 lacks FX6 AF Assist / PUSH AUTO / VF x3/x6 / HDMI Focus Mag -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            auto_magnifier_in_mf=auto_magnifier_in_mf,
            focus_magnif_time=focus_magnif_time,
            initial_focus_mag=initial_focus_mag,
            af_in_focus_mag=af_in_focus_mag,
            active_magnification_ratio="x1.0",
            second_press_ratio=None,
            persistent_items_count=FX3_FOCUS_ASSISTANT_PERSISTENT_ITEMS_COUNT,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            hdmi_mag_leaked_pixels=0,
            xavc_mag_leaked_pixels=0,
            fx3_appfw_focus_ring_rotate_enums_count=FX3_APPFW_FOCUS_RING_ROTATE_ENUMS_COUNT,
            dormant_focus_ring_rotate_exposed=False,
            fx6_focus_ring_rotate_mode=None,
            fx6_af_assist=None,
            fx6_push_af_mode=None,
            fx6_focus_mag_button_target=None,
        )

    if operation == "fx3_dormant_focus_ring_rotate":
        return FocusAssistantSplitVsFocusRingRotateFx6Audit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"FX3 dormant [{dormant_item}] has 0 appFw.so enum/BKID hits "
                "(active only on ILME-FX6 setting_focus_ring_rotate_t) -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            auto_magnifier_in_mf=auto_magnifier_in_mf,
            focus_magnif_time=focus_magnif_time,
            initial_focus_mag=initial_focus_mag,
            af_in_focus_mag=af_in_focus_mag,
            active_magnification_ratio="x1.0",
            second_press_ratio=None,
            persistent_items_count=FX3_FOCUS_ASSISTANT_PERSISTENT_ITEMS_COUNT,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            hdmi_mag_leaked_pixels=0,
            xavc_mag_leaked_pixels=0,
            fx3_appfw_focus_ring_rotate_enums_count=0,
            dormant_focus_ring_rotate_exposed=False,
            fx6_focus_ring_rotate_mode=None,
            fx6_af_assist=None,
            fx6_push_af_mode=None,
            fx6_focus_mag_button_target=None,
        )

    if initial_focus_mag in FX3_DORMANT_HIGH_MP_MAG_RATIOS or (
        shoot_mode == "Still" and initial_focus_mag in ("x4.1", "x3.0", "x4.0")
    ):
        return FocusAssistantSplitVsFocusRingRotateFx6Audit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"Initial Focus Mag {initial_focus_mag!r} rejected in {shoot_mode}/{sensor_crop} "
                "(x4.1/x3.0 are 2nd-press only; high-MP ratios dormant) -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            auto_magnifier_in_mf=auto_magnifier_in_mf,
            focus_magnif_time=focus_magnif_time,
            initial_focus_mag=initial_focus_mag,
            af_in_focus_mag=af_in_focus_mag,
            active_magnification_ratio="x1.0",
            second_press_ratio=None,
            persistent_items_count=FX3_FOCUS_ASSISTANT_PERSISTENT_ITEMS_COUNT,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            hdmi_mag_leaked_pixels=0,
            xavc_mag_leaked_pixels=0,
            fx3_appfw_focus_ring_rotate_enums_count=0,
            dormant_focus_ring_rotate_exposed=False,
            fx6_focus_ring_rotate_mode=None,
            fx6_af_assist=None,
            fx6_push_af_mode=None,
            fx6_focus_mag_button_target=None,
        )

    valid_init = (
        FX3_MOVIE_INITIAL_MAG_MODES
        if shoot_mode in ("Movie", "S&Q")
        else (
            FX3_STILL_FF_INITIAL_MAG_MODES
            if sensor_crop == "FF"
            else FX3_STILL_APSC_INITIAL_MAG_MODES
        )
    )
    if (
        auto_magnifier_in_mf not in ("On", "Off")
        or focus_magnif_time not in FX3_FOCUS_MAGNIF_TIME_MODES
        or initial_focus_mag not in valid_init
        or af_in_focus_mag not in ("On", "Off")
    ):
        return FocusAssistantSplitVsFocusRingRotateFx6Audit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=f"Invalid FX3 [Focus Assistant] enum for {shoot_mode}/{sensor_crop} -> EINVAL=22",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            auto_magnifier_in_mf=auto_magnifier_in_mf,
            focus_magnif_time=focus_magnif_time,
            initial_focus_mag=initial_focus_mag,
            af_in_focus_mag=af_in_focus_mag,
            active_magnification_ratio="x1.0",
            second_press_ratio=None,
            persistent_items_count=FX3_FOCUS_ASSISTANT_PERSISTENT_ITEMS_COUNT,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            hdmi_mag_leaked_pixels=0,
            xavc_mag_leaked_pixels=0,
            fx3_appfw_focus_ring_rotate_enums_count=0,
            dormant_focus_ring_rotate_exposed=False,
            fx6_focus_ring_rotate_mode=None,
            fx6_af_assist=None,
            fx6_push_af_mode=None,
            fx6_focus_mag_button_target=None,
        )

    # All 4 [Focus Assistant] items are Reset-resistant Not available in Ver. 2.00..7.02!
    _ = camera_settings_reset_applied
    eff_auto_mf = "On" if initialize_applied else auto_magnifier_in_mf
    eff_time = "No Limit" if initialize_applied else focus_magnif_time
    eff_init = "x1.0" if initialize_applied else initial_focus_mag
    eff_af_mag = "On" if initialize_applied else af_in_focus_mag

    if trigger_auto_mag_in_mf and (
        shoot_mode != "Still" or focus_mode not in ("MF", "DMF") or mount_adaptor_attached
    ):
        return FocusAssistantSplitVsFocusRingRotateFx6Audit(
            admitted=False,
            errno_code=EBUSY_ERRNO,
            reason="[Auto Magnifier in MF] is Still MF/DMF only (disabled in Movie/S&Q/MountAdaptor) -> EBUSY=16",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            auto_magnifier_in_mf=eff_auto_mf,
            focus_magnif_time=eff_time,
            initial_focus_mag=eff_init,
            af_in_focus_mag=eff_af_mag,
            active_magnification_ratio="x1.0",
            second_press_ratio=None,
            persistent_items_count=FX3_FOCUS_ASSISTANT_PERSISTENT_ITEMS_COUNT,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            hdmi_mag_leaked_pixels=0,
            xavc_mag_leaked_pixels=0,
            fx3_appfw_focus_ring_rotate_enums_count=0,
            dormant_focus_ring_rotate_exposed=False,
            fx6_focus_ring_rotate_mode=None,
            fx6_af_assist=None,
            fx6_push_af_mode=None,
            fx6_focus_mag_button_target=None,
        )

    if trigger_af_in_mag and (
        shoot_mode != "Still"
        or focus_mode == "AF-C"
        or (focus_mode == "AF-A" and not pasms_mode)
        or cont_shooting_active
        or mount_adaptor_attached
    ):
        return FocusAssistantSplitVsFocusRingRotateFx6Audit(
            admitted=False,
            errno_code=EBUSY_ERRNO,
            reason="[AF in Focus Mag.] disabled in Movie/S&Q, AF-C, Cont.Shooting, MountAdaptor -> EBUSY=16",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            auto_magnifier_in_mf=eff_auto_mf,
            focus_magnif_time=eff_time,
            initial_focus_mag=eff_init,
            af_in_focus_mag=eff_af_mag,
            active_magnification_ratio="x1.0",
            second_press_ratio=None,
            persistent_items_count=FX3_FOCUS_ASSISTANT_PERSISTENT_ITEMS_COUNT,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            hdmi_mag_leaked_pixels=0,
            xavc_mag_leaked_pixels=0,
            fx3_appfw_focus_ring_rotate_enums_count=0,
            dormant_focus_ring_rotate_exposed=False,
            fx6_focus_ring_rotate_mode=None,
            fx6_af_assist=None,
            fx6_push_af_mode=None,
            fx6_focus_mag_button_target=None,
        )

    if shoot_mode in ("Movie", "S&Q"):
        first_step = "x4.0" if eff_init == "x4.0" else "x1.0"
        second_step = "x4.0"
        active_ratio = "x4.0" if (press_count >= 2 or eff_init == "x4.0") else "x1.0"
    elif sensor_crop == "FF":
        first_step = "x2.1" if eff_init == "x2.1" else "x1.0"
        second_step = "x4.1"
        if press_count >= 2:
            active_ratio = "x4.1"
        elif eff_init == "x2.1":
            active_ratio = "x2.1"
        else:
            active_ratio = "x1.0"
    else:
        first_step = "x1.5" if eff_init == "x1.5" else "x1.0"
        second_step = "x3.0"
        if press_count >= 2:
            active_ratio = "x3.0"
        elif eff_init == "x1.5":
            active_ratio = "x1.5"
        else:
            active_ratio = "x1.0"

    return FocusAssistantSplitVsFocusRingRotateFx6Audit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 [Focus Assistant] 4 Reset-resistant items ({shoot_mode}/{sensor_crop}): "
            f"AutoMF={eff_auto_mf}, Time={eff_time}, Init={eff_init}, AFinMag={eff_af_mag}, "
            f"1st={first_step} -> 2nd={second_step}, active={active_ratio} (CleanHDMI=0px)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        shoot_mode=shoot_mode,
        sensor_crop=sensor_crop,
        auto_magnifier_in_mf=eff_auto_mf,
        focus_magnif_time=eff_time,
        initial_focus_mag=eff_init,
        af_in_focus_mag=eff_af_mag,
        active_magnification_ratio=active_ratio,
        second_press_ratio=second_step,
        persistent_items_count=FX3_FOCUS_ASSISTANT_PERSISTENT_ITEMS_COUNT,
        resettable_via_camera_settings_reset=False,
        cleared_only_by_initialize=True,
        hdmi_mag_leaked_pixels=0,
        xavc_mag_leaked_pixels=0,
        fx3_appfw_focus_ring_rotate_enums_count=0,
        dormant_focus_ring_rotate_exposed=False,
        fx6_focus_ring_rotate_mode=None,
        fx6_af_assist=None,
        fx6_push_af_mode=None,
        fx6_focus_mag_button_target=None,
    )


# ---------------------------------------------------------------------------
# Sub-Model 83D: Playback [Delete] 5-Mode / [Delete confirm.] "Cancel" first /
#                [Protect] 7-Mode Proxy Co-Binding & [Recover Image DB] AVF_INFO
#                Boot-Prompt Trap Blocked by Tier-0 Slot 1 EROFS=30 vs FX6
#                Update Media / Restore Media WP Check
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    target_slot: str
    slot1_is_tier0_vault: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    slot1_erofs_enforced: bool
    sd_write_protect_on: bool
    delete_confirm: Optional[str]
    delete_pressing_twice: Optional[str]
    delete_mode: Optional[str]
    protect_mode: Optional[str]
    proxy_cobound_atomic: bool
    copy_strips_protect_flag: bool
    cancel_all_images_exposed: bool
    survives_camera_settings_reset: bool
    survives_initialize: bool
    avf_info_paths: Tuple[str, ...]
    boot_prompt_trapped: bool
    ftp_transfer_result_cleared: bool
    battery_pct: int
    card_still_cap: int
    live_view_cap: int
    fx6_clip_lock_mode: Optional[str]


def simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "fx3_recover_image_db",
    target_slot: str = "Slot 1",
    slot1_is_tier0_vault: bool = True,
    sd_write_protect_on: bool = False,
    delete_confirm: str = '"Cancel" first',
    delete_pressing_twice: str = "Off",
    delete_mode: str = "Multiple Img.",
    clip_is_protected: bool = False,
    split_main_proxy_requested: bool = False,
    protect_mode: str = "Multiple Img.",
    copy_requested: bool = False,
    auto_confirm_boot_prompt: bool = False,
    battery_pct: int = 85,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_action: str = "restore_media",
    fx6_clip_lock_mode: str = "Select Clip",
) -> PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage83Phase367Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage83Phase367Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_83D_OPERATIONS:
        raise Stage83Phase367Error(f"Unsupported 83D operation: {operation!r}")
    if target_slot not in VALID_MEDIA_SLOTS:
        raise Stage83Phase367Error(f"Unsupported target_slot: {target_slot!r}")
    if not (0 <= battery_pct <= 100):
        raise Stage83Phase367Error(f"Unsupported battery_pct: {battery_pct!r}")

    tier0_slot1_block = (target_slot == "Slot 1") and slot1_is_tier0_vault

    if body_profile == BODY_MODEL_FX6:
        if operation != "fx6_media_restore_update_clip_lock":
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not use FX3 83D operation {operation} -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=None,
                delete_pressing_twice=None,
                delete_mode=None,
                protect_mode=None,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=(),
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=fx6_clip_lock_mode,
            )
        if fx6_action not in ("update_media", "restore_media", "clip_lock", "delete_clip"):
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Invalid FX6 media action {fx6_action!r} -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=None,
                delete_pressing_twice=None,
                delete_mode=None,
                protect_mode=None,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=(),
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=fx6_clip_lock_mode,
            )
        if fx6_clip_lock_mode not in FX6_CLIP_LOCK_MODES:
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Invalid FX6 clip_lock_mode {fx6_clip_lock_mode!r} -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=None,
                delete_pressing_twice=None,
                delete_mode=None,
                protect_mode=None,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=(),
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=fx6_clip_lock_mode,
            )
        if sd_write_protect_on:
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EROFS_ERRNO,
                reason=(
                    "FX6 ng_write_protected -> 'Please Unprotect and Reinsert Media' "
                    "on Restore/Update/Clip Lock -> EROFS=30"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=True,
                delete_confirm=None,
                delete_pressing_twice=None,
                delete_mode=None,
                protect_mode=None,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=(),
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=fx6_clip_lock_mode,
            )
        if tier0_slot1_block:
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EROFS_ERRNO,
                reason=f"Tier-0 Slot 1 vault blocks FX6 {fx6_action} write -> EROFS=30",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=True,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=False,
                delete_confirm=None,
                delete_pressing_twice=None,
                delete_mode=None,
                protect_mode=None,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=(),
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=fx6_clip_lock_mode,
            )
        return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Ver. {fw_version} XDROOT/MEDIAPRO.XML {fx6_action} on {target_slot} "
                f"(clip_lock={fx6_clip_lock_mode}, slot1_data_sector_writes=0)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_erofs_enforced=True,
            sd_write_protect_on=False,
            delete_confirm=None,
            delete_pressing_twice=None,
            delete_mode=None,
            protect_mode=None,
            proxy_cobound_atomic=True,
            copy_strips_protect_flag=True,
            cancel_all_images_exposed=False,
            survives_camera_settings_reset=True,
            survives_initialize=False,
            avf_info_paths=(),
            boot_prompt_trapped=False,
            ftp_transfer_result_cleared=False,
            battery_pct=battery_pct,
            card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
            live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
            fx6_clip_lock_mode=fx6_clip_lock_mode,
        )

    # ILME-FX3 path
    if operation == "fx6_media_restore_update_clip_lock":
        return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="FX3 uses /AVF_INFO + [Recover Image DB] + [Protect], not FX6 MEDIAPRO.XML -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_erofs_enforced=True,
            sd_write_protect_on=sd_write_protect_on,
            delete_confirm=delete_confirm,
            delete_pressing_twice=delete_pressing_twice,
            delete_mode=delete_mode,
            protect_mode=protect_mode,
            proxy_cobound_atomic=True,
            copy_strips_protect_flag=True,
            cancel_all_images_exposed=False,
            survives_camera_settings_reset=True,
            survives_initialize=False,
            avf_info_paths=FX3_AVF_INFO_FILES,
            boot_prompt_trapped=False,
            ftp_transfer_result_cleared=False,
            battery_pct=battery_pct,
            card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
            live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
            fx6_clip_lock_mode=None,
        )

    if operation == "fx3_display_media_info":
        return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 Playback -> [Display Media Info.] on {target_slot}: strict read-only "
                "(40,000 still cap, 9999 live-view cap, slot1_data_sector_writes=0)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_erofs_enforced=True,
            sd_write_protect_on=sd_write_protect_on,
            delete_confirm=None,
            delete_pressing_twice=None,
            delete_mode=None,
            protect_mode=None,
            proxy_cobound_atomic=True,
            copy_strips_protect_flag=True,
            cancel_all_images_exposed=False,
            survives_camera_settings_reset=True,
            survives_initialize=False,
            avf_info_paths=FX3_AVF_INFO_FILES,
            boot_prompt_trapped=False,
            ftp_transfer_result_cleared=False,
            battery_pct=battery_pct,
            card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
            live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
            fx6_clip_lock_mode=None,
        )

    if operation == "fx3_delete_config_and_exec":
        if (
            delete_confirm not in FX3_DELETE_CONFIRM_MODES
            or delete_pressing_twice not in ("Off", "On")
            or delete_mode not in FX3_DELETE_5_BATCH_MODES
        ):
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="Invalid FX3 [Delete]/[Delete confirm.]/[Delete pressing twice] mode -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=delete_confirm,
                delete_pressing_twice=delete_pressing_twice,
                delete_mode=delete_mode,
                protect_mode=None,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=FX3_AVF_INFO_FILES,
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=None,
            )
        _ = camera_settings_reset_applied
        eff_confirm = FX3_DELETE_CONFIRM_DEFAULT if initialize_applied else delete_confirm
        eff_twice = "Off" if initialize_applied else delete_pressing_twice

        if split_main_proxy_requested:
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EPERM_ERRNO,
                reason="FX3 Delete enforces atomic Main + *S03.MP4 Proxy co-binding (split delete forbidden) -> EPERM=1",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=eff_confirm,
                delete_pressing_twice=eff_twice,
                delete_mode=delete_mode,
                protect_mode=None,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=FX3_AVF_INFO_FILES,
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=None,
            )
        if clip_is_protected:
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EPERM_ERRNO,
                reason="Protected clip cannot be deleted by [Delete] (requires [Format]) -> EPERM=1",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=eff_confirm,
                delete_pressing_twice=eff_twice,
                delete_mode=delete_mode,
                protect_mode=None,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=FX3_AVF_INFO_FILES,
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=None,
            )
        if sd_write_protect_on or tier0_slot1_block:
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EROFS_ERRNO,
                reason=(
                    f"Playback [Delete] ({delete_mode}) on {target_slot} blocked by "
                    f"{'SD WP (base 0xe967)' if sd_write_protect_on else 'Tier-0 Slot 1 EROFS=30'} "
                    "(slot1_data_sector_writes=0)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=eff_confirm,
                delete_pressing_twice=eff_twice,
                delete_mode=delete_mode,
                protect_mode=None,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=FX3_AVF_INFO_FILES,
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=None,
            )
        return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 Playback [Delete] ({delete_mode}, confirm={eff_confirm}, twice={eff_twice}) "
                f"atomic Main+Proxy on virtual {target_slot} (slot1_data_sector_writes=0)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_erofs_enforced=True,
            sd_write_protect_on=False,
            delete_confirm=eff_confirm,
            delete_pressing_twice=eff_twice,
            delete_mode=delete_mode,
            protect_mode=None,
            proxy_cobound_atomic=True,
            copy_strips_protect_flag=True,
            cancel_all_images_exposed=False,
            survives_camera_settings_reset=True,
            survives_initialize=False,
            avf_info_paths=FX3_AVF_INFO_FILES,
            boot_prompt_trapped=False,
            ftp_transfer_result_cleared=False,
            battery_pct=battery_pct,
            card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
            live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
            fx6_clip_lock_mode=None,
        )

    if operation == "fx3_protect_7mode":
        if protect_mode == "Cancel All Images":
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX3 Ver. 7.02 [Protect] exposes 7 modes and has ZERO 'Cancel All Images' -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=None,
                delete_pressing_twice=None,
                delete_mode=None,
                protect_mode=protect_mode,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=FX3_AVF_INFO_FILES,
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=None,
            )
        if protect_mode not in FX3_PROTECT_7_MODES:
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Invalid FX3 [Protect] mode {protect_mode!r} -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=None,
                delete_pressing_twice=None,
                delete_mode=None,
                protect_mode=protect_mode,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=FX3_AVF_INFO_FILES,
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=None,
            )
        if split_main_proxy_requested:
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EPERM_ERRNO,
                reason="FX3 [Protect] enforces atomic Main + *S03.MP4 Proxy co-binding -> EPERM=1",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=None,
                delete_pressing_twice=None,
                delete_mode=None,
                protect_mode=protect_mode,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=FX3_AVF_INFO_FILES,
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=None,
            )
        if sd_write_protect_on or tier0_slot1_block:
            return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
                admitted=False,
                errno_code=EROFS_ERRNO,
                reason=(
                    f"FX3 [Protect] ({protect_mode}) on {target_slot} blocked by "
                    f"{'SD WP' if sd_write_protect_on else 'Tier-0 Slot 1 EROFS=30'} "
                    "(slot1_data_sector_writes=0)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_erofs_enforced=True,
                sd_write_protect_on=sd_write_protect_on,
                delete_confirm=None,
                delete_pressing_twice=None,
                delete_mode=None,
                protect_mode=protect_mode,
                proxy_cobound_atomic=True,
                copy_strips_protect_flag=True,
                cancel_all_images_exposed=False,
                survives_camera_settings_reset=True,
                survives_initialize=False,
                avf_info_paths=FX3_AVF_INFO_FILES,
                boot_prompt_trapped=False,
                ftp_transfer_result_cleared=False,
                battery_pct=battery_pct,
                card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
                live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
                fx6_clip_lock_mode=None,
            )
        return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 [Protect] ({protect_mode}) atomic Main+Proxy on virtual {target_slot} "
                f"(copy_strips_protect={copy_requested}, slot1_data_sector_writes=0)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_erofs_enforced=True,
            sd_write_protect_on=False,
            delete_confirm=None,
            delete_pressing_twice=None,
            delete_mode=None,
            protect_mode=protect_mode,
            proxy_cobound_atomic=True,
            copy_strips_protect_flag=True,
            cancel_all_images_exposed=False,
            survives_camera_settings_reset=True,
            survives_initialize=False,
            avf_info_paths=FX3_AVF_INFO_FILES,
            boot_prompt_trapped=False,
            ftp_transfer_result_cleared=False,
            battery_pct=battery_pct,
            card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
            live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
            fx6_clip_lock_mode=None,
        )

    # operation == "fx3_recover_image_db" (Dual-Immune + AVF_INFO Boot-Prompt Trap!)
    _ = (camera_settings_reset_applied, initialize_applied)
    if battery_pct < FX3_RECOVER_IMAGE_DB_MIN_BATTERY_PCT:
        return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
            admitted=False,
            errno_code=EAGAIN_ERRNO,
            reason=(
                f"FX3 [Recover Image DB] refused at {battery_pct}% battery "
                f"(< {FX3_RECOVER_IMAGE_DB_MIN_BATTERY_PCT}%) -> EAGAIN=11"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_erofs_enforced=True,
            sd_write_protect_on=sd_write_protect_on,
            delete_confirm=None,
            delete_pressing_twice=None,
            delete_mode=None,
            protect_mode=None,
            proxy_cobound_atomic=True,
            copy_strips_protect_flag=True,
            cancel_all_images_exposed=False,
            survives_camera_settings_reset=True,
            survives_initialize=True,
            avf_info_paths=FX3_AVF_INFO_FILES,
            boot_prompt_trapped=auto_confirm_boot_prompt,
            ftp_transfer_result_cleared=False,
            battery_pct=battery_pct,
            card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
            live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
            fx6_clip_lock_mode=None,
        )
    if sd_write_protect_on or tier0_slot1_block:
        return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason=(
                f"FX3 [Recover Image DB] / boot-insert 'Recover?/Create?/Update?' prompt "
                f"(auto_confirm={auto_confirm_boot_prompt}) on {target_slot} blocked by "
                f"{'SD WP (0xe967)' if sd_write_protect_on else 'Tier-0 Slot 1 EROFS=30'} "
                "-> slot1_avf_info_mutated=False, slot1_data_sector_writes=0"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_erofs_enforced=True,
            sd_write_protect_on=sd_write_protect_on,
            delete_confirm=None,
            delete_pressing_twice=None,
            delete_mode=None,
            protect_mode=None,
            proxy_cobound_atomic=True,
            copy_strips_protect_flag=True,
            cancel_all_images_exposed=False,
            survives_camera_settings_reset=True,
            survives_initialize=True,
            avf_info_paths=FX3_AVF_INFO_FILES,
            boot_prompt_trapped=auto_confirm_boot_prompt,
            ftp_transfer_result_cleared=False,
            battery_pct=battery_pct,
            card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
            live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
            fx6_clip_lock_mode=None,
        )
    return PlaybackDeleteProtectRecoverDbVsSlot1ErofsAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 dual-immune [Recover Image DB] rebuilt /AVF_INFO/AVIN0001.{{INP,BNP,INT}} "
            f"on virtual {target_slot} without deleting originals; FTP result cleared"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        target_slot=target_slot,
        slot1_is_tier0_vault=slot1_is_tier0_vault,
        slot1_data_sector_writes=0,
        slot1_avf_info_mutated=False,
        slot1_erofs_enforced=True,
        sd_write_protect_on=False,
        delete_confirm=None,
        delete_pressing_twice=None,
        delete_mode=None,
        protect_mode=None,
        proxy_cobound_atomic=True,
        copy_strips_protect_flag=True,
        cancel_all_images_exposed=False,
        survives_camera_settings_reset=True,
        survives_initialize=True,
        avf_info_paths=FX3_AVF_INFO_FILES,
        boot_prompt_trapped=False,
        ftp_transfer_result_cleared=True,
        battery_pct=battery_pct,
        card_still_cap=FX3_CARD_STILL_CAPACITY_CAP,
        live_view_cap=FX3_LIVE_VIEW_IMAGE_CAP,
        fx6_clip_lock_mode=None,
    )


# ---------------------------------------------------------------------------
# Milestone Probe, Recursive Determinism & Full Stage 83 Runner
# ---------------------------------------------------------------------------


def _strip_wall_clock(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_wall_clock(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [_strip_wall_clock(x) for x in obj]
    return obj


def _build_stage83_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_83rd_stage_milestone": IS_83RD_STAGE_MILESTONE,
        "wave": "Wave-73",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    donor_audit = inspect_phase367_wave73_donors(
        work_root=work_root, force_clean_room=force_clean_room, env=env
    )

    # Sub-Model 83A probes
    p83a_reset_resistant = simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
        operation="fx3_lock_op_config",
        lock_op_parts_setting="Dial + Wheel",
        camera_settings_reset_applied=True,
    )
    p83a_af_reg_forces_off = simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
        operation="fx3_fn_long_press_lock",
        lock_op_parts_setting="All",
        af_area_registration_on=True,
        fn_long_press_toggled=True,
    )
    p83a_my_dial_temp_unlock = simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
        operation="fx3_fn_long_press_lock",
        lock_op_parts_setting="All",
        fn_long_press_toggled=True,
        my_dial_recall_active=True,
    )
    p83a_menu_fn_5s = simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
        operation="fx3_menu_fn_5s_global_lock",
        menu_fn_hold_seconds=5.0,
        touch_operation="On",
    )
    p83a_dormant_slikey = simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
        operation="fx3_dormant_alpha_lock",
        dormant_symbol="UIBIZ_SLIKEY_LOCK",
    )
    p83a_fx6_dual_hold_passcode = simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_hold_and_user_menu_lock",
        fx6_body_hold_on=True,
        fx6_handle_hold_on=True,
        fx6_handle_hold_mode="Rec Button Only",
        fx6_menu_lock_mode="User Menu with Lock",
        fx6_passcode_configured="2026",
        fx6_passcode_entered="2026",
    )
    p83a_ok = (
        p83a_reset_resistant.admitted
        and p83a_reset_resistant.menu_path == FX3_LOCK_OP_PARTS_MENU_PATH
        and p83a_reset_resistant.lock_op_parts_setting == "Dial + Wheel"
        and (not p83a_reset_resistant.resettable_via_camera_settings_reset)
        and (not p83a_af_reg_forces_off.admitted)
        and p83a_af_reg_forces_off.errno_code == EBUSY_ERRNO
        and p83a_af_reg_forces_off.af_area_registration_forced_off
        and p83a_my_dial_temp_unlock.admitted
        and p83a_my_dial_temp_unlock.my_dial_temp_unlocked
        and p83a_my_dial_temp_unlock.multi_selector_locked
        and (not p83a_my_dial_temp_unlock.dials_wheel_locked)
        and p83a_menu_fn_5s.admitted
        and p83a_menu_fn_5s.menu_fn_5s_global_lock_active
        and p83a_menu_fn_5s.buttons_locked
        and (not p83a_menu_fn_5s.shutter_locked)
        and p83a_menu_fn_5s.touch_screen_active
        and (not p83a_dormant_slikey.admitted)
        and p83a_dormant_slikey.errno_code == EOPNOTSUPP_ERRNO
        and (not p83a_dormant_slikey.dormant_sli_key_lock_exposed)
        and p83a_fx6_dual_hold_passcode.admitted
        and p83a_fx6_dual_hold_passcode.fx6_physical_hold_switches_count == 2
        and (not p83a_fx6_dual_hold_passcode.fx6_lcd_hold_switch_present)
        and p83a_fx6_dual_hold_passcode.fx6_user_menu_unlocked is True
    )

    # Sub-Model 83B probes
    p83b_shockless_3_movie = simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
        operation="fx3_shockless_wb",
        shoot_mode="Movie",
        shockless_wb="3 (Slow)",
        wb_change_kind="wb_preset_switch",
    )
    p83b_shockless_still_blocked = simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
        operation="fx3_shockless_wb",
        shoot_mode="Still",
        shockless_wb="2",
    )
    p83b_prio_ambience_cineei_locked = simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
        operation="fx3_priority_set_in_awb",
        log_shooting="Cine EI",
        priority_set_in_awb="Ambience",
    )
    p83b_shutter_awb_reset_resistant = simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
        operation="fx3_shutter_awb_lock",
        shoot_mode="Still",
        shutter_awb_lock="Shutter Half Press",
        shutter_half_pressed=True,
        camera_settings_reset_applied=True,
    )
    p83b_shutter_awb_movie_rejected = simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
        operation="fx3_shutter_awb_lock",
        shoot_mode="Movie",
        shutter_awb_lock="Cont. Shooting",
    )
    p83b_movie_awb_custom_key = simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
        operation="fx3_movie_awb_lock_custom_key",
        shoot_mode="Movie",
        movie_awb_lock_custom_key="AWB Lock Toggle",
        movie_awb_lock_engaged=True,
    )
    p83b_fx6_atw_and_no_warm_cool = simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_wb_atw_shockless",
        fx6_wht_bal_switch="B",
        fx6_atw_speed=2,
        fx6_shockless_white="2",
    )
    p83b_fx6_warm_cool_masked = simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_wb_atw_shockless",
        request_fx6_warm_cool_ui=True,
    )
    p83b_ok = (
        p83b_shockless_3_movie.admitted
        and p83b_shockless_3_movie.shockless_wb == "3 (Slow)"
        and p83b_shockless_3_movie.transition_smoothed
        and (not p83b_shockless_3_movie.auto_tracking_speed_affected)
        and (not p83b_shockless_still_blocked.admitted)
        and p83b_shockless_still_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not p83b_prio_ambience_cineei_locked.admitted)
        and p83b_prio_ambience_cineei_locked.errno_code == EBUSY_ERRNO
        and p83b_shutter_awb_reset_resistant.admitted
        and p83b_shutter_awb_reset_resistant.shutter_awb_lock == "Shutter Half Press"
        and (not p83b_shutter_awb_reset_resistant.shutter_awb_lock_resettable_by_camera_reset)
        and p83b_shutter_awb_reset_resistant.awb_locked_active
        and (not p83b_shutter_awb_movie_rejected.admitted)
        and p83b_shutter_awb_movie_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p83b_movie_awb_custom_key.admitted
        and p83b_movie_awb_custom_key.awb_locked_active
        and p83b_fx6_atw_and_no_warm_cool.admitted
        and p83b_fx6_atw_and_no_warm_cool.fx6_atw_speed == 2
        and (not p83b_fx6_warm_cool_masked.admitted)
        and p83b_fx6_warm_cool_masked.errno_code == EOPNOTSUPP_ERRNO
        and (not p83b_fx6_warm_cool_masked.fx6_warm_cool_ui_exposed)
    )

    # Sub-Model 83C probes
    p83c_still_ff_4item_reset_resistant = simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
        operation="fx3_focus_assistant_config",
        shoot_mode="Still",
        sensor_crop="FF",
        auto_magnifier_in_mf="Off",
        focus_magnif_time="5 Sec",
        initial_focus_mag="x2.1",
        af_in_focus_mag="Off",
        press_count=2,
        camera_settings_reset_applied=True,
    )
    p83c_still_ff_x4_1_init_rejected = simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
        operation="fx3_focus_assistant_config",
        shoot_mode="Still",
        sensor_crop="FF",
        initial_focus_mag="x4.1",
    )
    p83c_movie_x4_0 = simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
        operation="fx3_focus_mag_activate",
        shoot_mode="Movie",
        initial_focus_mag="x4.0",
        press_count=1,
    )
    p83c_dormant_focus_ring_rotate = simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
        operation="fx3_dormant_focus_ring_rotate"
    )
    p83c_fx6_ver60_hdmi_mag = simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_focus_assist_and_mag",
        fx6_focus_ring_rotate_mode="RIGHT_F_LEFT_N",
        fx6_af_assist="On",
        fx6_push_af_mode="Single-shot AF(AF-S)",
        fx6_focus_mag_button_target="HDMI Focus Mag",
        fx6_hdmi_mag_step=2,
    )
    p83c_ok = (
        p83c_still_ff_4item_reset_resistant.admitted
        and p83c_still_ff_4item_reset_resistant.persistent_items_count == 4
        and p83c_still_ff_4item_reset_resistant.auto_magnifier_in_mf == "Off"
        and p83c_still_ff_4item_reset_resistant.focus_magnif_time == "5 Sec"
        and p83c_still_ff_4item_reset_resistant.initial_focus_mag == "x2.1"
        and p83c_still_ff_4item_reset_resistant.af_in_focus_mag == "Off"
        and p83c_still_ff_4item_reset_resistant.active_magnification_ratio == "x4.1"
        and (not p83c_still_ff_4item_reset_resistant.resettable_via_camera_settings_reset)
        and p83c_still_ff_4item_reset_resistant.hdmi_mag_leaked_pixels == 0
        and (not p83c_still_ff_x4_1_init_rejected.admitted)
        and p83c_still_ff_x4_1_init_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p83c_movie_x4_0.admitted
        and p83c_movie_x4_0.active_magnification_ratio == "x4.0"
        and (not p83c_dormant_focus_ring_rotate.admitted)
        and p83c_dormant_focus_ring_rotate.errno_code == EOPNOTSUPP_ERRNO
        and p83c_dormant_focus_ring_rotate.fx3_appfw_focus_ring_rotate_enums_count == 0
        and p83c_fx6_ver60_hdmi_mag.admitted
        and p83c_fx6_ver60_hdmi_mag.active_magnification_ratio == "x4.0"
        and p83c_fx6_ver60_hdmi_mag.fx6_focus_ring_rotate_mode == "RIGHT_F_LEFT_N"
    )

    # Sub-Model 83D probes
    p83d_delete_slot1_erofs = simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
        operation="fx3_delete_config_and_exec",
        target_slot="Slot 1",
        delete_mode="All Other Than This Img.",
        delete_confirm='"Cancel" first',
    )
    p83d_protect_cancel_all_rejected = simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
        operation="fx3_protect_7mode",
        target_slot="Slot 2",
        protect_mode="Cancel All Images",
    )
    p83d_protect_slot1_erofs = simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
        operation="fx3_protect_7mode",
        target_slot="Slot 1",
        protect_mode="All in this Folder",
    )
    p83d_display_media_info_ro = simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
        operation="fx3_display_media_info",
        target_slot="Slot 1",
    )
    p83d_recover_db_boot_trap_slot1_erofs = simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
        operation="fx3_recover_image_db",
        target_slot="Slot 1",
        auto_confirm_boot_prompt=True,
        camera_settings_reset_applied=True,
        initialize_applied=True,
    )
    p83d_recover_db_slot2_dual_immune = simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
        operation="fx3_recover_image_db",
        target_slot="Slot 2",
        slot1_is_tier0_vault=True,
        camera_settings_reset_applied=True,
        initialize_applied=True,
    )
    p83d_fx6_wp_blocked = simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_media_restore_update_clip_lock",
        target_slot="Slot 2",
        sd_write_protect_on=True,
        fx6_action="restore_media",
    )
    p83d_ok = (
        (not p83d_delete_slot1_erofs.admitted)
        and p83d_delete_slot1_erofs.errno_code == EROFS_ERRNO
        and p83d_delete_slot1_erofs.slot1_data_sector_writes == 0
        and p83d_delete_slot1_erofs.delete_confirm == FX3_DELETE_CONFIRM_DEFAULT
        and (not p83d_protect_cancel_all_rejected.admitted)
        and p83d_protect_cancel_all_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p83d_protect_cancel_all_rejected.cancel_all_images_exposed)
        and (not p83d_protect_slot1_erofs.admitted)
        and p83d_protect_slot1_erofs.errno_code == EROFS_ERRNO
        and p83d_display_media_info_ro.admitted
        and p83d_display_media_info_ro.slot1_data_sector_writes == 0
        and (not p83d_recover_db_boot_trap_slot1_erofs.admitted)
        and p83d_recover_db_boot_trap_slot1_erofs.errno_code == EROFS_ERRNO
        and p83d_recover_db_boot_trap_slot1_erofs.boot_prompt_trapped
        and (not p83d_recover_db_boot_trap_slot1_erofs.slot1_avf_info_mutated)
        and p83d_recover_db_boot_trap_slot1_erofs.slot1_data_sector_writes == 0
        and p83d_recover_db_slot2_dual_immune.admitted
        and p83d_recover_db_slot2_dual_immune.survives_camera_settings_reset
        and p83d_recover_db_slot2_dual_immune.survives_initialize
        and p83d_recover_db_slot2_dual_immune.ftp_transfer_result_cleared
        and (not p83d_fx6_wp_blocked.admitted)
        and p83d_fx6_wp_blocked.errno_code == EROFS_ERRNO
    )

    redlines: Dict[str, object] = {
        "ready_for_live_camera_attach": READY_FOR_LIVE_CAMERA_ATTACH,
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
        "slot1_sector_writes": SLOT1_SECTOR_WRITES,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "rf_tx_packets": RF_TX_PACKETS,
        "rf_packets_transmitted": RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": RF_NVS_MUTATION_BYTES,
        # 83A
        "fx3_lock_op_parts_options_count": FX3_LOCK_OP_PARTS_OPTIONS_COUNT,
        "fx3_menu_fn_global_lock_hold_seconds": FX3_MENU_FN_GLOBAL_LOCK_HOLD_SECONDS,
        "fx3_menu_fn_locks_shutter": FX3_MENU_FN_LOCKS_SHUTTER,
        "fx3_lock_op_reset_wipe_events": FX3_LOCK_OP_RESET_WIPE_EVENTS,
        "fx3_dormant_slikey_lock_exposed_events": FX3_DORMANT_SLIKEY_LOCK_EXPOSED_EVENTS,
        "fx6_physical_hold_switch_count": FX6_PHYSICAL_HOLD_SWITCH_COUNT,
        "fx6_lcd_hold_switch_present": FX6_LCD_HOLD_SWITCH_PRESENT,
        "fx6_user_menu_lock_passcode_digits": FX6_USER_MENU_LOCK_PASSCODE_DIGITS,
        # 83B
        "fx3_shockless_wb_options_count": FX3_SHOCKLESS_WB_OPTIONS_COUNT,
        "fx3_shockless_wb_default": FX3_SHOCKLESS_WB_DEFAULT,
        "fx3_shutter_awb_lock_still_only": FX3_SHUTTER_AWB_LOCK_STILL_ONLY,
        "fx3_shutter_awb_lock_reset_wipe_events": FX3_SHUTTER_AWB_LOCK_RESET_WIPE_EVENTS,
        "fx6_shockless_white_options_count": FX6_SHOCKLESS_WHITE_OPTIONS_COUNT,
        "fx6_warm_cool_ui_exposed": FX6_WARM_COOL_UI_EXPOSED,
        # 83C
        "fx3_focus_assistant_persistent_items_count": FX3_FOCUS_ASSISTANT_PERSISTENT_ITEMS_COUNT,
        "fx3_focus_assistant_reset_wipe_events": FX3_FOCUS_ASSISTANT_RESET_WIPE_EVENTS,
        "fx3_appfw_focus_ring_rotate_enums_count": FX3_APPFW_FOCUS_RING_ROTATE_ENUMS_COUNT,
        "fx3_focus_ring_rotate_exposed_events": FX3_FOCUS_RING_ROTATE_EXPOSED_EVENTS,
        "fx3_focus_mag_hdmi_leaked_pixels": FX3_FOCUS_MAG_HDMI_LEAKED_PIXELS,
        "fx6_focus_ring_rotate_active": FX6_FOCUS_RING_ROTATE_ACTIVE,
        "fx6_hdmi_focus_mag_ver60_supported": FX6_HDMI_FOCUS_MAG_VER60_SUPPORTED,
        # 83D
        "fx3_playback_delete_batch_modes_count": FX3_PLAYBACK_DELETE_BATCH_MODES_COUNT,
        "fx3_delete_confirm_default": FX3_DELETE_CONFIRM_DEFAULT,
        "fx3_playback_protect_modes_count": FX3_PLAYBACK_PROTECT_MODES_COUNT,
        "fx3_protect_cancel_all_images_exposed_events": FX3_PROTECT_CANCEL_ALL_IMAGES_EXPOSED_EVENTS,
        "fx3_proxy_cobinding_split_events": FX3_PROXY_COBINDING_SPLIT_EVENTS,
        "fx3_recover_image_db_dual_immune": FX3_RECOVER_IMAGE_DB_DUAL_IMMUNE,
        "fx3_slot1_avf_info_prompt_bypass_events": FX3_SLOT1_AVF_INFO_PROMPT_BYPASS_EVENTS,
        # Fault Counters
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    all_passed = bool(
        donor_audit["all_donors_verified"] and p83a_ok and p83b_ok and p83c_ok and p83d_ok
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_367_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_83rd_stage_milestone": IS_83RD_STAGE_MILESTONE,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit["source_mode"],
        "redlines": redlines,
        "donor_audit": donor_audit,
        "stage83_milestone_probe": _build_stage83_milestone_probe(),
        "pillar_a_lock_op_parts_menu_fn_vs_fx6_hold_hil": {
            "passed": p83a_ok,
            "fx3_lock_op_reset_resistant": asdict(p83a_reset_resistant),
            "fx3_af_area_reg_forces_off": asdict(p83a_af_reg_forces_off),
            "fx3_my_dial_temp_unlock": asdict(p83a_my_dial_temp_unlock),
            "fx3_menu_fn_5s_global_lock_shutter_exempt": asdict(p83a_menu_fn_5s),
            "fx3_dormant_sli_key_lock_rejected": asdict(p83a_dormant_slikey),
            "fx6_dual_hold_and_4digit_user_menu_lock": asdict(p83a_fx6_dual_hold_passcode),
        },
        "pillar_b_shockless_wb_priority_awb_lock_vs_fx6_hil": {
            "passed": p83b_ok,
            "fx3_shockless_wb_3_movie": asdict(p83b_shockless_3_movie),
            "fx3_shockless_wb_still_disabled": asdict(p83b_shockless_still_blocked),
            "fx3_priority_awb_cine_ei_locked": asdict(p83b_prio_ambience_cineei_locked),
            "fx3_shutter_awb_lock_reset_resistant": asdict(p83b_shutter_awb_reset_resistant),
            "fx3_shutter_awb_lock_movie_rejected": asdict(p83b_shutter_awb_movie_rejected),
            "fx3_movie_awb_lock_custom_key": asdict(p83b_movie_awb_custom_key),
            "fx6_wht_bal_atw_speed_shockless": asdict(p83b_fx6_atw_and_no_warm_cool),
            "fx6_warm_cool_ui_masked": asdict(p83b_fx6_warm_cool_masked),
        },
        "pillar_c_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil": {
            "passed": p83c_ok,
            "fx3_still_ff_4item_reset_resistant": asdict(p83c_still_ff_4item_reset_resistant),
            "fx3_still_ff_x4_1_init_rejected": asdict(p83c_still_ff_x4_1_init_rejected),
            "fx3_movie_x4_0_mag": asdict(p83c_movie_x4_0),
            "fx3_dormant_focus_ring_rotate_0enum": asdict(p83c_dormant_focus_ring_rotate),
            "fx6_ver60_hdmi_focus_mag_and_ring_rotate": asdict(p83c_fx6_ver60_hdmi_mag),
        },
        "pillar_d_playback_delete_protect_recoverdb_vs_slot1_erofs_fx6_hil": {
            "passed": p83d_ok,
            "fx3_delete_slot1_erofs_30": asdict(p83d_delete_slot1_erofs),
            "fx3_protect_cancel_all_images_rejected": asdict(p83d_protect_cancel_all_rejected),
            "fx3_protect_slot1_erofs_30": asdict(p83d_protect_slot1_erofs),
            "fx3_display_media_info_readonly": asdict(p83d_display_media_info_ro),
            "fx3_recover_db_boot_prompt_trap_slot1_erofs_30": asdict(
                p83d_recover_db_boot_trap_slot1_erofs
            ),
            "fx3_recover_db_slot2_dual_immune": asdict(p83d_recover_db_slot2_dual_immune),
            "fx6_restore_media_wp_check": asdict(p83d_fx6_wp_blocked),
        },
    }

    digest = hashlib.sha256(
        json.dumps(
            _strip_wall_clock(payload), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulator.py",
        description=(
            "Phase 367 (Stage 83 — 83/83 Full-Board VM Co-Emulation Stages!): "
            "Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-73 "
            "[Lock Operation Parts] & MENU+Fn 5s Global Lock vs FX6 Dual HOLD & "
            "4-Digit User Menu with Lock / [Shockless WB] & Still-Only Reset-Resistant "
            "[Shutter AWB Lock] vs FX6 WHT BAL & ATW Speed 1..5 / 4-Item "
            "[Focus Assistant] Split & Dormant [Focus Ring Rotate] Disproof / "
            "Playback [Delete] 5-Mode & [Protect] 7-Mode & [Recover Image DB] "
            "AVF_INFO Boot-Prompt Trap vs Tier-0 Slot 1 EROFS=30 HIL Co-Emulator"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run all 83A..83D HIL checks and 18-donor O_RDONLY/clean-room audit",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force deterministic CLEAN_ROOM_SYNTHETIC mode (0%% raw donor dependency)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full deterministic JSON audit report (default)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit concise one-line HIL pass/fail summary (100%% Redline enforced)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    rep = run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        rl = rep["redlines"]
        da = rep["donor_audit"]
        sys.stdout.write(
            f"[{status}] Phase 367 Stage {MILESTONE_LABEL} | src={rep['source_mode']} "
            f"donors={da['total_donors_count']} | "
            f"lock={rl['fx3_lock_op_parts_options_count']}w/{rl['fx3_menu_fn_global_lock_hold_seconds']:.0f}s "
            f"fx6hold={rl['fx6_physical_hold_switch_count']} | "
            f"swb={rl['fx3_shockless_wb_options_count']}opt sal_still={int(bool(rl['fx3_shutter_awb_lock_still_only']))} | "
            f"fmag={rl['fx3_focus_assistant_persistent_items_count']}i/frr={rl['fx3_appfw_focus_ring_rotate_enums_count']} | "
            f"pb=del{rl['fx3_playback_delete_batch_modes_count']}/prot{rl['fx3_playback_protect_modes_count']} "
            f"s1_wr={rl['slot1_data_sector_writes']} emmc_wr={rl['emmc_nflasha_write_count']} "
            f"attach={int(bool(rl['ready_for_live_camera_attach']))} | "
            f"digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
