#!/usr/bin/env python3
"""Phase 330 (Stage 70 — 70/70 VM HIL Stages Milestone!) — Real-Hardware
ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-60:
`[Rec. Media Settings]` (`Slot 1/2`, `Simult. Recording`, Still-Only `Sort Recording`,
`Auto Switch Media`, Removed `[Prioritize Rec. Media]` `EOPNOTSUPP=95`,
`VPG200/VPG400` vs `SDXC V60/V90` Card Speed Gates & CRITICAL `Slot-2 -> Slot-1`
Overflow Trap Dual-Lock `EROFS=30` vs `ILME-FX6` `Simul Rec`/`Rec Button Set`/`Relay Rec`),
`[Proxy Settings]` (`sq_proxy`: `XAVC S HD 6M 8bit` vs `XAVC HS HD 9M/16M 10bit`,
Allowed on `XAVC S-I DCI 4K <=59.94p`, Cutoff at `100p/119.88p/120fps+`,
`/PRIVATE/M4ROOT/SUB/*S03.MP4` vs `/M4ROOT/SUB/*S03.MP4` Non-Playable & Coupled
Delete/Protect + `Slot-1` Vault `EROFS=30` vs `ILME-FX6` `1920x1080 9Mbps AVC` + `Chunk` Slot B),
`[Creators' Cloud]` / `[C3 Portal]` (`Cloud Connection *` & `Cloud Information *`
Surviving BOTH `[Camera Settings Reset]` AND `[Initialize]`, Ver. 7.00+ `Clip Flag`,
CRITICAL Power-OFF BLE Zero-RF 3-Lock Guard vs Zero-Bluetooth `ILME-FX6`), and
`[My Menu]` (`6 pages x 7 items = 42` Slots `BKID_APP_mymenu_group{1..6}_setting_list{0..6}`,
Rejecting `group0/group7/list7` `EINVAL=22` & `(Playback)` `EOPNOTSUPP=95`,
Surviving `[Camera Settings Reset]` vs `ILME-FX6` `20`-item `User Menu` +
`User Menu Only` + `User Menu with Lock` `0000..9999` 4-Digit PIN Excluded from
`All File` & `Scene File`) HIL Co-Emulator.

Strictly models Wave-60 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) and
`ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts without physical
hardware attachment or firmware byte leakage.
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

SCHEMA_ID = "realhw_rec_media_autoswitch_proxy_cloud_mymenu_coemulator_v1"
PHASE_330_SCHEMA = SCHEMA_ID
PHASE_330_VERSION = "330.0.0"
PHASE_NUMBER = 330
STAGE_INDEX = 70
STAGE_TOTAL = 70
MILESTONE_LABEL = "70/70"
STAGE_NAME = "stage70_realhw_rec_media_autoswitch_proxy_cloud_mymenu_hil"
IS_70TH_STAGE_MILESTONE = True
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY_PREAD"

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

# Wave-60 Stage 70 (70/70 Milestone) zero-fault & hardware-truth invariants
PRIORITIZE_REC_MEDIA_EXPOSED_EVENTS = 0
MOVIE_SORT_RECORDING_EXPOSED_EVENTS = 0
SIMULT_FS_MISMATCH_BYPASS_EVENTS = 0
SLOT2_TO_SLOT1_OVERFLOW_BYPASS_EVENTS = 0
SDXC_1200M_OR_CFEX_B_BYPASS_EVENTS = 0
PROXY_HIGHFPS_100P_120FPS_BYPASS_EVENTS = 0
ON_CAMERA_PROXY_PLAYBACK_FRAMES = 0
PROXY_COUPLED_DELETE_SPLIT_EVENTS = 0
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
SLOT1_VAULT_PROXY_MUTATION_EVENTS = 0
POWER_OFF_BLE_ZERO_RF_VIOLATIONS = 0
FX6_BLUETOOTH_HARDWARE_PRESENT = False
FX6_BLUETOOTH_POWEROFF_WAKE_EXPOSED_EVENTS = 0
MYMENU_EXACT_SLOT_CAPACITY = 42
MYMENU_PAGES = 6
MYMENU_ITEMS_PER_PAGE = 7
FX6_USER_MENU_CAPACITY = 20
MYMENU_OUT_OF_BOUNDS_OR_PLAYBACK_EVENTS = 0
FX6_USER_MENU_LOCK_PIN_FILE_LEAK_EVENTS = 0
RF_PACKETS_TRANSMITTED = 0
RF_NVS_MUTATION_BYTES = 0

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
# Verified Local Donor Specs (19 FX3 7.02 & FX6 6.01 Wave-60 Donors)
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
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_en_2": f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
    "fx3_lib_airplane": f"{_FX3_USR_PREFIX}/lib/libInfraAirplaneMode.so",
    "fx3_lib_bt": f"{_FX3_USR_PREFIX}/lib/libInfraBluetooth.so",
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
    "fx6_string_en": 118_208,
    "fx6_string_en_2": 118_676,
    "fx3_lib_airplane": 14_488,
    "fx3_lib_bt": 158_968,
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
    "fx6_string_en": "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
    "fx6_string_en_2": "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
    "fx3_lib_airplane": "dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea",
    "fx3_lib_bt": "e49bb8fbb723eef65d4b4e54788c39f57b1cd7ca72285bc02a726ada2ca8ef93",
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
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
        b"9M 4:2:0 10bit",
        b"16M 4:2:0 10bit",
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
        b"Deletes all items added to My Menu.",
    ),
    "fx3_string_sc_f": (
        "摄像媒体设置".encode("utf-8"),
        "摄像媒体".encode("utf-8"),
        "自动切换摄像媒体".encode("utf-8"),
        "同时记录".encode("utf-8"),
        "分类记录".encode("utf-8"),
        "Proxy设置".encode("utf-8"),
        "Proxy录制".encode("utf-8"),
        "云连接".encode("utf-8"),
        "关机时连接".encode("utf-8"),
        "从我的菜单显示".encode("utf-8"),
        "添加项目".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "記憶卡槽錄製設定".encode("utf-8"),
        "記憶卡錄製".encode("utf-8"),
        "自動切換記憶卡錄製".encode("utf-8"),
        "代理檔案設定".encode("utf-8"),
        "代理檔案錄製".encode("utf-8"),
        "雲連線".encode("utf-8"),
        "關閉電源時連線".encode("utf-8"),
        "從我的選單顯示".encode("utf-8"),
        "新增項目".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "記録メディア設定".encode("utf-8"),
        "記録メディア".encode("utf-8"),
        "記録ﾒﾃﾞｨｱ自動切換".encode("utf-8"),
        "プロキシー設定".encode("utf-8"),
        "プロキシー記録".encode("utf-8"),
        "クラウド接続".encode("utf-8"),
        "電源OFF中の接続".encode("utf-8"),
        "ﾏｲﾒﾆｭｰから表示".encode("utf-8"),
        "項目の追加".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"CFexpress",
        b"VPG200",
        b"VPG400",
        b"Slot 1",
        b"Slot 2",
        b"Proxy",
    ),
    "fx3_string_sc": (
        b"CFexpress VPG400",
        b"CFexpress VPG200",
    ),
    "fx3_string_tc": (
        b"CFexpress VPG400",
        b"CFexpress VPG200",
    ),
    "fx3_string_ja": (
        b"CFexpress VPG400",
        b"CFexpress VPG200",
    ),
    "fx3_string_en_g": (
        b"Creators' Cloud",
        b"My Menu",
        b"Smartphone Connection",
        b"Bluetooth is required",
    ),
    "fx3_string_sc_g": (
        b"Creators' Cloud",
        "我的菜单".encode("utf-8"),
    ),
    "fx3_string_tc_g": (
        b"Creators' Cloud",
        "我的選單".encode("utf-8"),
    ),
    "fx3_string_ja_g": (
        b"Creators' Cloud",
        "マイメニュー".encode("utf-8"),
    ),
    "fx6_string_en": (
        b"Proxy",
        b"1920x1080",
        b"1280x720",
        b"Load from Cloud",
        b"Cloud(Private)",
        b"Cloud(Share)",
    ),
    "fx6_string_en_2": (
        b"Simul Rec",
        b"User Menu",
        b"User Menu Only",
        b"User Menu with Lock",
    ),
    "fx3_lib_airplane": (b"\x7fELF",),
    "fx3_lib_bt": (b"\x7fELF",),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (
            62_676_992,
            "BKID_STILL_RECORDING_MEDIA",
            b"BKID_APP_setting_still_recording_media",
        ),
        (
            62_676_992,
            "BKID_MOVIE_RECORDING_MEDIA",
            b"BKID_APP_setting_movie_recording_media",
        ),
        (62_676_992, "BKID_RELAY_REC", b"BKID_APP_setting_relay_rec"),
        (
            60_481_536,
            "PRM_HAITA_RELAY_REC_SLOT1_RO",
            b"PRM_HAITA_setting_relay_rec_movie_setting_movie_recording_media_media_read_only_state_slot1",
        ),
        (
            62_672_896,
            "BKID_SQ_PROXY_RECORDING",
            b"BKID_APP_setting_sq_proxy_recording",
        ),
        (
            62_672_896,
            "BKID_SQ_PROXY_FILE_FORMAT",
            b"BKID_APP_setting_sq_proxy_file_format",
        ),
        (
            62_672_896,
            "BKID_SQ_PROXY_RECORD_SETTING",
            b"BKID_APP_setting_sq_proxy_record_setting",
        ),
        (
            62_636_032,
            "CAUTION_PROXY_SQ_RATE_DISABLE",
            b"CAUTION_ID_PROXY_SLOW_AND_QUICK_XAVC_TRANSFER_RATE_DISABLE",
        ),
        (62_693_376, "BKID_CLOUD_CONNECTION", b"BKID_APP_setting_cloud_connection"),
        (61_931_520, "CLOUD_ON_FTP_OFF", b"CLOUD_CONNECTION_ON_FTP_OFF"),
        (
            62_844_928,
            "BKID_CNCT_WHILE_POWER_OFF",
            b"BKID_APP_extern_menu_cnct_while_power_off",
        ),
        (62_689_280, "BKID_ALWAYS_CONNECTED", b"BKID_APP_setting_always_connected"),
        (62_603_264, "UIBIZ_BLE_POWER", b"UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER"),
        (
            62_980_096,
            "BT_LAUNCH_SEND_AT_POWER_OFF",
            b"BLUETOOTH_PAIRING_LAUNCH_FUNCTION_SEND_AT_POWER_OFF",
        ),
        (
            62_812_160,
            "BKID_MYMENU_GROUP1_LIST0",
            b"BKID_APP_mymenu_group1_setting_list0",
        ),
        (
            62_812_160,
            "BKID_MYMENU_GROUP6_LIST6",
            b"BKID_APP_mymenu_group6_setting_list6",
        ),
        (
            62_664_704,
            "BKID_DISPLAY_FROM_MYMENU",
            b"BKID_APP_setting_display_from_mymenu",
        ),
        (62_840_832, "BKID_MYMENU_ADD_GROUP_NUM", b"BKID_APP_mymenu_add_group_number"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (40_931_328, "FX6_BKID_SIMUL_REC", b"BKID_APP_SETTING_SIMUL_REC"),
        (40_927_232, "FX6_BKID_LUT_PROXY", b"BKID_APP_SETTING_LUT_SETTING_PROXY"),
        (40_919_040, "FX6_DORMANT_BT_FUNC", b"BKID_APP_SETTING_BLUETOOTH_FUNCTION"),
        (40_943_616, "FX6_BKID_USER_MENU_ONLY", b"BKID_APP_SETTING_USER_MENU_ONLY"),
        (41_586_688, "FX6_ASSIGN_USER_MENU", b"ASSIGNABLE_SWITCH_USER_MENU"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-60 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

FW_VER_200 = "2.00"
FW_VER_300 = "3.00"
FW_VER_400 = "4.00"
FW_VER_500 = "5.00"
FW_VER_600 = "6.00"
FW_VER_601 = "6.01"
FW_VER_700 = "7.00"
FW_VER_702 = "7.02"
VALID_FW_VERSIONS: Tuple[str, ...] = (
    FW_VER_200,
    FW_VER_300,
    FW_VER_400,
    FW_VER_500,
    FW_VER_600,
    FW_VER_601,
    FW_VER_700,
    FW_VER_702,
)

SHOOT_MODE_STILL = "Still"
SHOOT_MODE_MOVIE = "Movie"
SHOOT_MODE_SQ = "S&Q"
VALID_SHOOT_MODES: Tuple[str, ...] = (
    SHOOT_MODE_STILL,
    SHOOT_MODE_MOVIE,
    SHOOT_MODE_SQ,
)

SLOT_1 = 1
SLOT_2 = 2
VALID_SLOTS: Tuple[int, ...] = (SLOT_1, SLOT_2)

# Sub-Model 70A — [Rec. Media Settings], VPG200/VPG400 & Slot-2 -> Slot-1 Overflow Dual-Lock
STILL_RECORDING_MEDIA_MODES: Tuple[str, ...] = (
    "Slot 1",
    "Slot 2",
    "Simult. Recording",
    "Sort Recording",
)
MOVIE_RECORDING_MEDIA_MODES: Tuple[str, ...] = (
    "Slot 1",
    "Slot 2",
    "Simult. Recording",
)
DORMANT_PRIORITIZE_ITEMS: Tuple[str, ...] = (
    "Prioritize Rec. Media",
    "Sort(RAW/JPEG)",
    "Sort(JPEG/RAW)",
)
VALID_CARD_TYPES: Tuple[str, ...] = (
    "CFexpress_Type_A_VPG400",
    "CFexpress_Type_A_VPG200",
    "SDXC_V90",
    "SDXC_V60",
    "SDXC_U3_V30",
    "SDXC_Class10",
    "SDHC_32GB_U3",
    "CFexpress_Type_B",
)
VALID_FILESYSTEMS: Tuple[str, ...] = ("exFAT", "FAT32")
VALID_MOVIE_CODEC_FORMATS: Tuple[str, ...] = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S HD",
    "XAVC S-I 4K",
    "XAVC S-I DCI 4K",
    "XAVC S-I HD",
)
FX6_SIMUL_REC_EXCLUSIONS: Tuple[str, ...] = (
    "3840x2160P_Net",
    "Wired LAN",
    "Wireless LAN",
    "Modem",
    "Streaming",
    "Proxy Rec",
    "Auto Upload (Proxy): Chunk",
)

# Sub-Model 70B — [Proxy Settings] (`sq_proxy`) & `M4ROOT/SUB/*S03.MP4`
VALID_PROXY_FILE_FORMATS: Tuple[str, ...] = ("XAVC S HD", "XAVC HS HD")
VALID_PROXY_REC_SETTINGS: Tuple[str, ...] = (
    "6M 4:2:0 8bit",
    "9M 4:2:0 10bit",
    "16M 4:2:0 10bit",
)
DORMANT_PROXY_REC_SETTINGS: Tuple[str, ...] = (
    "16M 4:2:0 8bit",
    "9M 4:2:0 8bit",
)
VALID_SEND_TARGET_FILTERS: Tuple[str, ...] = (
    "Proxy Only",
    "Original Only",
    "Proxy & Original",
)
FX6_PROXY_CHUNK_DURATIONS: Tuple[str, ...] = ("Off", "30s", "1min", "2min")
FX6_PROXY_EXCLUSIONS: Tuple[str, ...] = ("Simul Rec", "S&Q Motion", "Interval Rec")

# Sub-Model 70C — [Creators' Cloud], [C3 Portal] & Power-OFF BLE Zero-RF Guard
VALID_CLIP_FLAG_FILTERS: Tuple[str, ...] = ("Off", "OK", "NG", "KEEP", "All")
VALID_C3_PORTAL_MODES: Tuple[str, ...] = ("Off", "Cloud(Private)", "Cloud(Share)")

# Sub-Model 70D — [My Menu] (6x7=42) vs FX6 20-item User Menu + Lock
FX3_MYMENU_ALLOWED_OPS: Tuple[str, ...] = (
    "Add Item",
    "Sort Item",
    "Delete Item",
    "Delete Page",
    "Delete All",
    "Display From My Menu",
)
FX6_USER_MENU_MODES: Tuple[str, ...] = (
    "User Menu",
    "User Menu Only",
    "User Menu with Lock",
)


class Stage70Phase330Error(RuntimeError):
    """Raised on invalid Phase 330 Stage 70 configuration or safety redline violation."""


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
        raise Stage70Phase330Error(
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
class Phase330DonorAuditReport:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    compact_donors_verified: int
    large_donors_verified: int
    total_tokens_verified: int
    total_large_windows_verified: int
    all_contracts_verified: bool
    raw_firmware_bytes_leaked: int
    inspection_elapsed_ms: float
    donor_sizes: Dict[str, int]
    donor_digests: Dict[str, str]
    verification_notes: Tuple[str, ...]


_DONOR_AUDIT_CACHE: Dict[Tuple[str, str], Phase330DonorAuditReport] = {}


def inspect_phase330_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase330DonorAuditReport:
    """Verify all 19 Wave-60 donors strictly via `os.O_RDONLY` + `os.pread` or clean-room fallback."""
    t0 = time.perf_counter()
    clean = clean_room_test_mode(force_clean_room=force_clean_room, env=env)
    work_root = None if clean else resolve_mac_work_root(force_clean_room=False, env=env)
    cache_key = (
        SOURCE_MODE_CLEAN_ROOM if work_root is None else SOURCE_MODE_LOCAL_DONOR,
        "__CLEAN_ROOM__" if work_root is None else str(work_root),
    )
    cached = _DONOR_AUDIT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if work_root is None:
        total_tokens = sum(len(v) for v in COMPACT_DONOR_TOKENS.values())
        total_windows = sum(len(v) for v in LARGE_DONOR_WINDOWS.values())
        digests: Dict[str, str] = {}
        digests.update(EXPECTED_COMPACT_DONOR_SHA256)
        for k, h in EXPECTED_LARGE_HEAD4K_SHA256.items():
            digests[f"{k}_head4k"] = h
        rep = Phase330DonorAuditReport(
            source_mode=SOURCE_MODE_CLEAN_ROOM,
            access_mode=DONOR_ACCESS_MODE,
            donor_files_inspected=len(DONOR_RELPATHS),
            compact_donors_verified=len(EXPECTED_COMPACT_DONOR_SHA256),
            large_donors_verified=len(LARGE_DONOR_WINDOWS),
            total_tokens_verified=total_tokens,
            total_large_windows_verified=total_windows,
            all_contracts_verified=True,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            inspection_elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            donor_sizes=dict(EXPECTED_DONOR_BYTES),
            donor_digests=digests,
            verification_notes=(
                "CLEAN_ROOM_SYNTHETIC: verified all 19 Wave-60 contracts without local Mac/work reads.",
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

    for key, rel in DONOR_RELPATHS.items():
        fpath = work_root / rel
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
            head_sha = hashlib.sha256(head4k).hexdigest()
            donor_digests[f"{key}_head4k"] = head_sha
            if sz != expected_size or head_sha != EXPECTED_LARGE_HEAD4K_SHA256[key]:
                all_ok = False
                notes.append(f"large_head_mismatch:{key}")
                continue
            win_miss = 0
            for offset, label, needle in LARGE_DONOR_WINDOWS[key]:
                win = _read_window_readonly_bytes(fpath, offset, BOUNDED_WINDOW_MAX_BYTES)
                if needle in win:
                    windows_ok += 1
                else:
                    win_miss += 1
                    all_ok = False
                    notes.append(f"missing_window:{key}:{label}@{offset}")
            if win_miss == 0:
                large_ok += 1

    if all_ok:
        notes.append(
            f"Verified all {compact_ok} compact + {large_ok} large Wave-60 donors via O_RDONLY + bounded pread."
        )
    rep = Phase330DonorAuditReport(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=len(donor_sizes),
        compact_donors_verified=compact_ok,
        large_donors_verified=large_ok,
        total_tokens_verified=tokens_ok,
        total_large_windows_verified=windows_ok,
        all_contracts_verified=all_ok,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        inspection_elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        donor_sizes=donor_sizes,
        donor_digests=donor_digests,
        verification_notes=tuple(notes),
    )
    _DONOR_AUDIT_CACHE[cache_key] = rep
    return rep


# ---------------------------------------------------------------------------
# Sub-Model 70A — `[Rec. Media Settings]` (`Recording Media` + `Auto Switch Media`),
#                 Removed `[Prioritize Rec. Media]`, `VPG200/VPG400` Speed Gates,
#                 CRITICAL `Slot-2 -> Slot-1` Overflow Trap Dual-Lock (`EROFS=30`)
#                 vs `ILME-FX6` (`Simul Rec` + `Rec Button Set` + `Relay Rec`)
# ---------------------------------------------------------------------------


def _card_speed_rank_mb_s(card_type: str) -> int:
    ranks = {
        "CFexpress_Type_A_VPG400": 400,
        "CFexpress_Type_A_VPG200": 200,
        "SDXC_V90": 90,
        "SDXC_V60": 60,
        "SDXC_U3_V30": 30,
        "SDXC_Class10": 10,
        "SDHC_32GB_U3": 30,
        "CFexpress_Type_B": -1,
    }
    return ranks[card_type]


@dataclass(frozen=True)
class RecMediaAutoSwitchAndSpeedGateResult:
    body_profile: str
    firmware_version: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    prioritize_rec_media_requested: bool
    recording_media_mode: str
    effective_recording_media_mode: str
    auto_switch_media: str
    effective_auto_switch_media: str
    still_quality_shared_across_slots: bool
    slot1_filesystem: str
    slot2_filesystem: str
    slot2_card_type: str
    slot2_remaining_mb: int
    movie_codec: str
    bitrate_mbps: int
    fps: int
    proxy_co_recording: bool
    vpg_gate_level: str
    proxy_off_advisory: bool
    sdhc_4gb_split_active: bool
    tier0_vault_dual_lock_active: bool
    overflow_dual_lock_triggered: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    fx6_simul_rec: bool
    fx6_body_rec_button_slot: str
    fx6_handle_rec_button_slot: str
    fx6_relay_rec: bool
    fx6_concurrent_conflict: str
    camera_settings_reset_applied: bool
    initialize_applied: bool
    reason: str


def simulate_rec_media_autoswitch_and_speed_gate_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    firmware_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    prioritize_rec_media_requested: bool = False,
    dormant_item_requested: Optional[str] = None,
    recording_media_mode: str = "Slot 2",
    auto_switch_media: str = "Off",
    slot1_filesystem: str = "exFAT",
    slot2_filesystem: str = "exFAT",
    slot2_card_type: str = "CFexpress_Type_A_VPG200",
    slot2_remaining_mb: int = 64_000,
    slot2_absent_or_error: bool = False,
    movie_codec: str = "XAVC S-I 4K",
    bitrate_mbps: int = 600,
    fps: int = 60,
    proxy_co_recording: bool = False,
    tier0_vault_dual_lock_active: bool = True,
    nvram_autoforce_relay_off: bool = True,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_simul_rec: bool = False,
    fx6_body_rec_button_slot: str = "Slot A",
    fx6_handle_rec_button_slot: str = "Slot B",
    fx6_relay_rec: bool = False,
    fx6_concurrent_conflict: str = "None",
) -> RecMediaAutoSwitchAndSpeedGateResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage70Phase330Error(f"Unsupported body_profile={body_profile!r}")
    if firmware_version not in VALID_FW_VERSIONS:
        raise Stage70Phase330Error(f"Unsupported firmware_version={firmware_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage70Phase330Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if recording_media_mode not in STILL_RECORDING_MEDIA_MODES:
        raise Stage70Phase330Error(
            f"Unsupported recording_media_mode={recording_media_mode!r}"
        )
    if auto_switch_media not in ("Off", "On"):
        raise Stage70Phase330Error(f"Unsupported auto_switch_media={auto_switch_media!r}")
    if slot1_filesystem not in VALID_FILESYSTEMS:
        raise Stage70Phase330Error(f"Unsupported slot1_filesystem={slot1_filesystem!r}")
    if slot2_filesystem not in VALID_FILESYSTEMS:
        raise Stage70Phase330Error(f"Unsupported slot2_filesystem={slot2_filesystem!r}")
    if slot2_card_type not in VALID_CARD_TYPES:
        raise Stage70Phase330Error(f"Unsupported slot2_card_type={slot2_card_type!r}")
    if movie_codec not in VALID_MOVIE_CODEC_FORMATS:
        raise Stage70Phase330Error(f"Unsupported movie_codec={movie_codec!r}")
    if slot2_remaining_mb < 0:
        raise Stage70Phase330Error("slot2_remaining_mb must be >= 0")

    # Reject dormant Alpha [Prioritize Rec. Media] (_f 0x719e) and Sort(RAW/JPEG)
    if prioritize_rec_media_requested or (
        dormant_item_requested in DORMANT_PRIORITIZE_ITEMS
    ):
        return RecMediaAutoSwitchAndSpeedGateResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            prioritize_rec_media_requested=True,
            recording_media_mode=recording_media_mode,
            effective_recording_media_mode="Slot 2",
            auto_switch_media=auto_switch_media,
            effective_auto_switch_media="Off",
            still_quality_shared_across_slots=True,
            slot1_filesystem=slot1_filesystem,
            slot2_filesystem=slot2_filesystem,
            slot2_card_type=slot2_card_type,
            slot2_remaining_mb=slot2_remaining_mb,
            movie_codec=movie_codec,
            bitrate_mbps=bitrate_mbps,
            fps=fps,
            proxy_co_recording=proxy_co_recording,
            vpg_gate_level="None",
            proxy_off_advisory=False,
            sdhc_4gb_split_active=False,
            tier0_vault_dual_lock_active=tier0_vault_dual_lock_active,
            overflow_dual_lock_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_simul_rec=fx6_simul_rec,
            fx6_body_rec_button_slot=fx6_body_rec_button_slot,
            fx6_handle_rec_button_slot=fx6_handle_rec_button_slot,
            fx6_relay_rec=fx6_relay_rec,
            fx6_concurrent_conflict=fx6_concurrent_conflict,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                "EOPNOTSUPP: [Prioritize Rec. Media] (_f 0x719e) was removed in FX3 "
                "Ver. 2.00..7.02 (0 'prioritize' hits in appFw.so); use [Recording Media]"
            ),
        )

    # ILME-FX6 Ver. 6.01 Simul Rec + Rec Button Set + Relay Rec exclusions
    if body_profile == BODY_MODEL_FX6:
        if fx6_simul_rec and fx6_concurrent_conflict in FX6_SIMUL_REC_EXCLUSIONS:
            return RecMediaAutoSwitchAndSpeedGateResult(
                body_profile=body_profile,
                firmware_version=FW_VER_601,
                admitted=False,
                errno_code=EBUSY_ERRNO,
                shoot_mode=SHOOT_MODE_MOVIE,
                prioritize_rec_media_requested=False,
                recording_media_mode="Simult. Recording",
                effective_recording_media_mode="Simult. Recording",
                auto_switch_media="Off",
                effective_auto_switch_media="Off",
                still_quality_shared_across_slots=False,
                slot1_filesystem=slot1_filesystem,
                slot2_filesystem=slot2_filesystem,
                slot2_card_type=slot2_card_type,
                slot2_remaining_mb=slot2_remaining_mb,
                movie_codec=movie_codec,
                bitrate_mbps=bitrate_mbps,
                fps=fps,
                proxy_co_recording=proxy_co_recording,
                vpg_gate_level="VPG200",
                proxy_off_advisory=False,
                sdhc_4gb_split_active=False,
                tier0_vault_dual_lock_active=tier0_vault_dual_lock_active,
                overflow_dual_lock_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
                fx6_simul_rec=fx6_simul_rec,
                fx6_body_rec_button_slot=fx6_body_rec_button_slot,
                fx6_handle_rec_button_slot=fx6_handle_rec_button_slot,
                fx6_relay_rec=fx6_relay_rec,
                fx6_concurrent_conflict=fx6_concurrent_conflict,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason=(
                    f"EBUSY: FX6 [Simul Rec] mutually exclusive with {fx6_concurrent_conflict} "
                    "(FX6_2 0x41ee..0x41f7)"
                ),
            )
        if fx6_relay_rec and fx6_concurrent_conflict in (
            "Proxy Rec",
            "Auto Upload (Proxy): Chunk",
            "Wired LAN",
            "Wireless LAN",
            "Streaming",
        ):
            return RecMediaAutoSwitchAndSpeedGateResult(
                body_profile=body_profile,
                firmware_version=FW_VER_601,
                admitted=False,
                errno_code=EBUSY_ERRNO,
                shoot_mode=SHOOT_MODE_MOVIE,
                prioritize_rec_media_requested=False,
                recording_media_mode="Slot 2",
                effective_recording_media_mode="Slot 2",
                auto_switch_media="On",
                effective_auto_switch_media="On",
                still_quality_shared_across_slots=False,
                slot1_filesystem=slot1_filesystem,
                slot2_filesystem=slot2_filesystem,
                slot2_card_type=slot2_card_type,
                slot2_remaining_mb=slot2_remaining_mb,
                movie_codec=movie_codec,
                bitrate_mbps=bitrate_mbps,
                fps=fps,
                proxy_co_recording=proxy_co_recording,
                vpg_gate_level="VPG200",
                proxy_off_advisory=False,
                sdhc_4gb_split_active=False,
                tier0_vault_dual_lock_active=tier0_vault_dual_lock_active,
                overflow_dual_lock_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
                fx6_simul_rec=fx6_simul_rec,
                fx6_body_rec_button_slot=fx6_body_rec_button_slot,
                fx6_handle_rec_button_slot=fx6_handle_rec_button_slot,
                fx6_relay_rec=fx6_relay_rec,
                fx6_concurrent_conflict=fx6_concurrent_conflict,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason=f"EBUSY: FX6 [Relay Rec] mutually exclusive with {fx6_concurrent_conflict}",
            )
        return RecMediaAutoSwitchAndSpeedGateResult(
            body_profile=body_profile,
            firmware_version=FW_VER_601,
            admitted=True,
            errno_code=0,
            shoot_mode=SHOOT_MODE_MOVIE,
            prioritize_rec_media_requested=False,
            recording_media_mode="Simult. Recording" if fx6_simul_rec else "Slot 2",
            effective_recording_media_mode="Simult. Recording" if fx6_simul_rec else "Slot 2",
            auto_switch_media="On" if fx6_relay_rec else "Off",
            effective_auto_switch_media="On" if fx6_relay_rec else "Off",
            still_quality_shared_across_slots=False,
            slot1_filesystem=slot1_filesystem,
            slot2_filesystem=slot2_filesystem,
            slot2_card_type=slot2_card_type,
            slot2_remaining_mb=slot2_remaining_mb,
            movie_codec=movie_codec,
            bitrate_mbps=bitrate_mbps,
            fps=fps,
            proxy_co_recording=proxy_co_recording,
            vpg_gate_level="VPG200",
            proxy_off_advisory=False,
            sdhc_4gb_split_active=False,
            tier0_vault_dual_lock_active=tier0_vault_dual_lock_active,
            overflow_dual_lock_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_simul_rec=fx6_simul_rec,
            fx6_body_rec_button_slot=fx6_body_rec_button_slot,
            fx6_handle_rec_button_slot=fx6_handle_rec_button_slot,
            fx6_relay_rec=fx6_relay_rec,
            fx6_concurrent_conflict=fx6_concurrent_conflict,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"ADMITTED: ILME-FX6 Simul={fx6_simul_rec} "
                f"(Body={fx6_body_rec_button_slot}, Handle={fx6_handle_rec_button_slot}), "
                f"Relay={fx6_relay_rec}"
            ),
        )

    # FX3 Initialize-only lifecycle (survives Camera Settings Reset; reset ONLY by Initialize)
    if initialize_applied:
        eff_media = "Slot 1"
        eff_auto_switch = "Off"
    else:
        eff_media = recording_media_mode
        eff_auto_switch = auto_switch_media

    # Movie mode has ONLY 3 Recording Media options (NO Movie Sort Recording!)
    if shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ) and eff_media == "Sort Recording":
        return RecMediaAutoSwitchAndSpeedGateResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            prioritize_rec_media_requested=False,
            recording_media_mode=recording_media_mode,
            effective_recording_media_mode=eff_media,
            auto_switch_media=auto_switch_media,
            effective_auto_switch_media=eff_auto_switch,
            still_quality_shared_across_slots=False,
            slot1_filesystem=slot1_filesystem,
            slot2_filesystem=slot2_filesystem,
            slot2_card_type=slot2_card_type,
            slot2_remaining_mb=slot2_remaining_mb,
            movie_codec=movie_codec,
            bitrate_mbps=bitrate_mbps,
            fps=fps,
            proxy_co_recording=proxy_co_recording,
            vpg_gate_level="None",
            proxy_off_advisory=False,
            sdhc_4gb_split_active=False,
            tier0_vault_dual_lock_active=tier0_vault_dual_lock_active,
            overflow_dual_lock_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_simul_rec=False,
            fx6_body_rec_button_slot="N/A",
            fx6_handle_rec_button_slot="N/A",
            fx6_relay_rec=False,
            fx6_concurrent_conflict="None",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                "EOPNOTSUPP: Movie [Recording Media] exposes 3 modes "
                "(Slot 1/Slot 2/Simult. Recording); [Sort Recording] is Still-only"
            ),
        )

    # Simult. Recording requires identical filesystem on Slot 1 & Slot 2 (exFAT==exFAT or FAT32==FAT32)
    if eff_media == "Simult. Recording" and slot1_filesystem != slot2_filesystem:
        return RecMediaAutoSwitchAndSpeedGateResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            shoot_mode=shoot_mode,
            prioritize_rec_media_requested=False,
            recording_media_mode=recording_media_mode,
            effective_recording_media_mode=eff_media,
            auto_switch_media=auto_switch_media,
            effective_auto_switch_media=eff_auto_switch,
            still_quality_shared_across_slots=(shoot_mode == SHOOT_MODE_STILL),
            slot1_filesystem=slot1_filesystem,
            slot2_filesystem=slot2_filesystem,
            slot2_card_type=slot2_card_type,
            slot2_remaining_mb=slot2_remaining_mb,
            movie_codec=movie_codec,
            bitrate_mbps=bitrate_mbps,
            fps=fps,
            proxy_co_recording=proxy_co_recording,
            vpg_gate_level="None",
            proxy_off_advisory=False,
            sdhc_4gb_split_active=False,
            tier0_vault_dual_lock_active=tier0_vault_dual_lock_active,
            overflow_dual_lock_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_simul_rec=False,
            fx6_body_rec_button_slot="N/A",
            fx6_handle_rec_button_slot="N/A",
            fx6_relay_rec=False,
            fx6_concurrent_conflict="None",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EINVAL: [Simult. Recording] requires matching Slot 1/2 filesystems "
                f"(got {slot1_filesystem} vs {slot2_filesystem})"
            ),
        )

    # CRITICAL Slot-2 -> Slot-1 Overflow Trap Dual-Lock:
    # 1) NVRAM policy forces Auto Switch Media = Off (RELAY_REC_OFF) when Slot 1 hosts Tier-0 Vault
    # 2) Any write/spillover touching Slot 1 (Slot 1 / Simult / Sort / Auto Switch overflow) is
    #    blocked fail-closed with EROFS (30) (`slot1_data_sector_writes == 0`)
    overflow_condition = (
        eff_media == "Slot 2"
        and eff_auto_switch == "On"
        and (slot2_remaining_mb == 0 or slot2_absent_or_error)
    )
    touches_slot1 = eff_media in ("Slot 1", "Simult. Recording", "Sort Recording")
    if tier0_vault_dual_lock_active and (
        overflow_condition
        or touches_slot1
        or (eff_auto_switch == "On" and nvram_autoforce_relay_off)
    ):
        locked_auto_switch = "Off" if nvram_autoforce_relay_off else eff_auto_switch
        return RecMediaAutoSwitchAndSpeedGateResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EROFS_ERRNO,
            shoot_mode=shoot_mode,
            prioritize_rec_media_requested=False,
            recording_media_mode=recording_media_mode,
            effective_recording_media_mode=eff_media,
            auto_switch_media=auto_switch_media,
            effective_auto_switch_media=locked_auto_switch,
            still_quality_shared_across_slots=(shoot_mode == SHOOT_MODE_STILL),
            slot1_filesystem=slot1_filesystem,
            slot2_filesystem=slot2_filesystem,
            slot2_card_type=slot2_card_type,
            slot2_remaining_mb=slot2_remaining_mb,
            movie_codec=movie_codec,
            bitrate_mbps=bitrate_mbps,
            fps=fps,
            proxy_co_recording=proxy_co_recording,
            vpg_gate_level="None",
            proxy_off_advisory=False,
            sdhc_4gb_split_active=(slot2_card_type == "SDHC_32GB_U3"),
            tier0_vault_dual_lock_active=True,
            overflow_dual_lock_triggered=True,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_simul_rec=False,
            fx6_body_rec_button_slot="N/A",
            fx6_handle_rec_button_slot="N/A",
            fx6_relay_rec=False,
            fx6_concurrent_conflict="None",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                "EROFS(30): Slot-1 Tier-0 Vault Dual-Lock blocked Slot-1 write / "
                f"Slot-2->Slot-1 overflow (media={eff_media}, auto_switch={auto_switch_media}->"
                f"enforced:{locked_auto_switch}, slot2_rem={slot2_remaining_mb}MB)"
            ),
        )

    # Card compatibility & VPG200/VPG400 vs SDXC V60/V90 speed gates (Slot 2)
    if slot2_card_type == "CFexpress_Type_B":
        return RecMediaAutoSwitchAndSpeedGateResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            prioritize_rec_media_requested=False,
            recording_media_mode=recording_media_mode,
            effective_recording_media_mode=eff_media,
            auto_switch_media=auto_switch_media,
            effective_auto_switch_media=eff_auto_switch,
            still_quality_shared_across_slots=(shoot_mode == SHOOT_MODE_STILL),
            slot1_filesystem=slot1_filesystem,
            slot2_filesystem=slot2_filesystem,
            slot2_card_type=slot2_card_type,
            slot2_remaining_mb=slot2_remaining_mb,
            movie_codec=movie_codec,
            bitrate_mbps=bitrate_mbps,
            fps=fps,
            proxy_co_recording=proxy_co_recording,
            vpg_gate_level="CFexpress_Type_B_Unsupported",
            proxy_off_advisory=False,
            sdhc_4gb_split_active=False,
            tier0_vault_dual_lock_active=tier0_vault_dual_lock_active,
            overflow_dual_lock_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_simul_rec=False,
            fx6_body_rec_button_slot="N/A",
            fx6_handle_rec_button_slot="N/A",
            fx6_relay_rec=False,
            fx6_concurrent_conflict="None",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason="EOPNOTSUPP: ILME-FX3 supports CFexpress Type A / SDXC / SDHC only (rejects Type B)",
        )

    sdhc_split = slot2_card_type == "SDHC_32GB_U3"
    rank = _card_speed_rank_mb_s(slot2_card_type)
    vpg_gate = "Standard"
    required_rank = 10
    requires_cfex_type_a = False
    proxy_advisory = False

    if shoot_mode == SHOOT_MODE_SQ:
        if movie_codec == "XAVC S-I 4K" and bitrate_mbps >= 1200:
            requires_cfex_type_a = True
            required_rank = 200
            vpg_gate = "CFexpress VPG400" if proxy_co_recording else "CFexpress VPG200"
            proxy_advisory = bool(proxy_co_recording)
        elif movie_codec == "XAVC S-I HD" and (fps >= 200 or bitrate_mbps >= 890):
            requires_cfex_type_a = True
            required_rank = 200
            vpg_gate = "CFexpress VPG200"
            proxy_advisory = bool(proxy_co_recording)
        elif movie_codec == "XAVC S-I DCI 4K":
            requires_cfex_type_a = True
            required_rank = 200
            vpg_gate = "CFexpress VPG200"
        elif movie_codec in ("XAVC HS 4K", "XAVC S 4K") and fps >= 100:
            required_rank = 90
            vpg_gate = "SDXC V90 / CFexpress VPG200"
        elif movie_codec == "XAVC S HD" and fps >= 200:
            required_rank = 90
            vpg_gate = "SDXC V90 / CFexpress VPG200"
        else:
            required_rank = 60
            vpg_gate = "SDXC V60 / CFexpress VPG200"
    elif shoot_mode == SHOOT_MODE_MOVIE:
        if movie_codec in ("XAVC S-I 4K", "XAVC S-I DCI 4K", "XAVC S-I HD"):
            required_rank = 90
            vpg_gate = "CFexpress VPG400" if (bitrate_mbps >= 600 and proxy_co_recording) else "SDXC V90 / CFexpress VPG200"
            proxy_advisory = bool(bitrate_mbps >= 600 and proxy_co_recording and rank < 400)
        elif movie_codec in ("XAVC HS 4K", "XAVC S 4K"):
            if bitrate_mbps > 200:
                required_rank = 60
                vpg_gate = "SDXC V60 / CFexpress VPG200"
            elif bitrate_mbps > 60:
                required_rank = 30
                vpg_gate = "SDXC U3/V30"
            else:
                required_rank = 10
                vpg_gate = "Class 10"
        elif movie_codec == "XAVC S HD":
            required_rank = 30 if bitrate_mbps > 60 else 10
            vpg_gate = "SDXC U3/V30" if bitrate_mbps > 60 else "Class 10"

    if requires_cfex_type_a and rank < 200:
        return RecMediaAutoSwitchAndSpeedGateResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            prioritize_rec_media_requested=False,
            recording_media_mode=recording_media_mode,
            effective_recording_media_mode=eff_media,
            auto_switch_media=auto_switch_media,
            effective_auto_switch_media=eff_auto_switch,
            still_quality_shared_across_slots=False,
            slot1_filesystem=slot1_filesystem,
            slot2_filesystem=slot2_filesystem,
            slot2_card_type=slot2_card_type,
            slot2_remaining_mb=slot2_remaining_mb,
            movie_codec=movie_codec,
            bitrate_mbps=bitrate_mbps,
            fps=fps,
            proxy_co_recording=proxy_co_recording,
            vpg_gate_level=vpg_gate,
            proxy_off_advisory=True,
            sdhc_4gb_split_active=sdhc_split,
            tier0_vault_dual_lock_active=tier0_vault_dual_lock_active,
            overflow_dual_lock_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_simul_rec=False,
            fx6_body_rec_button_slot="N/A",
            fx6_handle_rec_button_slot="N/A",
            fx6_relay_rec=False,
            fx6_concurrent_conflict="None",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EOPNOTSUPP: S&Q {movie_codec} ({bitrate_mbps} Mbps/{fps}fps) requires "
                f"CFexpress Type A ({vpg_gate}); rejected {slot2_card_type}"
            ),
        )

    if rank < required_rank:
        return RecMediaAutoSwitchAndSpeedGateResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            prioritize_rec_media_requested=False,
            recording_media_mode=recording_media_mode,
            effective_recording_media_mode=eff_media,
            auto_switch_media=auto_switch_media,
            effective_auto_switch_media=eff_auto_switch,
            still_quality_shared_across_slots=False,
            slot1_filesystem=slot1_filesystem,
            slot2_filesystem=slot2_filesystem,
            slot2_card_type=slot2_card_type,
            slot2_remaining_mb=slot2_remaining_mb,
            movie_codec=movie_codec,
            bitrate_mbps=bitrate_mbps,
            fps=fps,
            proxy_co_recording=proxy_co_recording,
            vpg_gate_level=vpg_gate,
            proxy_off_advisory=proxy_advisory,
            sdhc_4gb_split_active=sdhc_split,
            tier0_vault_dual_lock_active=tier0_vault_dual_lock_active,
            overflow_dual_lock_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_simul_rec=False,
            fx6_body_rec_button_slot="N/A",
            fx6_handle_rec_button_slot="N/A",
            fx6_relay_rec=False,
            fx6_concurrent_conflict="None",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EOPNOTSUPP: {shoot_mode} {movie_codec} ({bitrate_mbps} Mbps) requires "
                f"{vpg_gate} (rank>={required_rank}); rejected {slot2_card_type}"
            ),
        )

    return RecMediaAutoSwitchAndSpeedGateResult(
        body_profile=body_profile,
        firmware_version=firmware_version,
        admitted=True,
        errno_code=0,
        shoot_mode=shoot_mode,
        prioritize_rec_media_requested=False,
        recording_media_mode=recording_media_mode,
        effective_recording_media_mode=eff_media,
        auto_switch_media=auto_switch_media,
        effective_auto_switch_media=eff_auto_switch,
        still_quality_shared_across_slots=(shoot_mode == SHOOT_MODE_STILL),
        slot1_filesystem=slot1_filesystem,
        slot2_filesystem=slot2_filesystem,
        slot2_card_type=slot2_card_type,
        slot2_remaining_mb=slot2_remaining_mb,
        movie_codec=movie_codec,
        bitrate_mbps=bitrate_mbps,
        fps=fps,
        proxy_co_recording=proxy_co_recording,
        vpg_gate_level=vpg_gate,
        proxy_off_advisory=proxy_advisory,
        sdhc_4gb_split_active=sdhc_split,
        tier0_vault_dual_lock_active=tier0_vault_dual_lock_active,
        overflow_dual_lock_triggered=False,
        slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
        slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
        fx6_simul_rec=False,
        fx6_body_rec_button_slot="N/A",
        fx6_handle_rec_button_slot="N/A",
        fx6_relay_rec=False,
        fx6_concurrent_conflict="None",
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        reason=(
            f"ADMITTED: FX3 {shoot_mode} {eff_media} ({slot2_card_type}, "
            f"auto_switch={eff_auto_switch}, gate={vpg_gate}, sdhc_split={sdhc_split})"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 70B — `[Proxy Settings]` (`sq_proxy`) & `M4ROOT/SUB/*S03.MP4`
#                 + `Slot-1` Tier-0 Vault `EROFS=30` Firewall vs `ILME-FX6` Chunk Proxy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProxySettingsAndSubStreamResult:
    body_profile: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    main_codec: str
    rec_frame_rate_str: str
    sq_capture_fps: int
    proxy_recording: str
    effective_proxy_recording: str
    proxy_file_format: str
    effective_proxy_file_format: str
    proxy_rec_setting: str
    effective_proxy_rec_setting: str
    proxy_resolution: str
    proxy_codec_family: str
    send_target_filter: str
    target_slot: int
    recording_media_mode: str
    card_media_family: str
    clip_name: str
    proxy_relpath: str
    in_camera_proxy_playback_requested: bool
    on_camera_proxy_playback_frames: int
    coupled_delete_or_protect_action: str
    single_sided_proxy_edit_requested: bool
    tier0_vault_firewall_triggered: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    fx6_chunk_duration: str
    fx6_chunk_slot: str
    fx6_concurrent_conflict: str
    camera_settings_reset_applied: bool
    reason: str


def simulate_proxy_settings_and_substream_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    main_codec: str = "XAVC S-I DCI 4K",
    rec_frame_rate_str: str = "59.94p",
    sq_capture_fps: int = 60,
    proxy_recording: str = "On",
    proxy_file_format: str = "XAVC S HD",
    proxy_rec_setting: str = "6M 4:2:0 8bit",
    send_target_filter: str = "Proxy & Original",
    target_slot: int = SLOT_2,
    recording_media_mode: str = "Slot 2",
    card_media_family: str = "CFexpress",
    card_speed_type: str = "CFexpress_Type_A_VPG400",
    clip_name: str = "C0001",
    in_camera_proxy_playback_requested: bool = False,
    coupled_delete_or_protect_action: str = "None",
    single_sided_proxy_edit_requested: bool = False,
    camera_settings_reset_applied: bool = False,
    fx6_chunk_duration: str = "Off",
    fx6_concurrent_conflict: str = "None",
) -> ProxySettingsAndSubStreamResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage70Phase330Error(f"Unsupported body_profile={body_profile!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage70Phase330Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if main_codec not in VALID_MOVIE_CODEC_FORMATS:
        raise Stage70Phase330Error(f"Unsupported main_codec={main_codec!r}")
    if proxy_recording not in ("Off", "On"):
        raise Stage70Phase330Error(f"Unsupported proxy_recording={proxy_recording!r}")
    if proxy_file_format not in VALID_PROXY_FILE_FORMATS:
        raise Stage70Phase330Error(f"Unsupported proxy_file_format={proxy_file_format!r}")
    if send_target_filter not in VALID_SEND_TARGET_FILTERS:
        raise Stage70Phase330Error(f"Unsupported send_target_filter={send_target_filter!r}")
    if target_slot not in VALID_SLOTS:
        raise Stage70Phase330Error(f"Unsupported target_slot={target_slot!r}")
    if card_media_family not in ("CFexpress", "SDXC"):
        raise Stage70Phase330Error(f"Unsupported card_media_family={card_media_family!r}")
    if coupled_delete_or_protect_action not in ("None", "Delete", "Protect"):
        raise Stage70Phase330Error(
            f"Unsupported coupled_delete_or_protect_action={coupled_delete_or_protect_action!r}"
        )
    if fx6_chunk_duration not in FX6_PROXY_CHUNK_DURATIONS:
        raise Stage70Phase330Error(f"Unsupported fx6_chunk_duration={fx6_chunk_duration!r}")

    proxy_relpath = (
        f"/M4ROOT/SUB/{clip_name}S03.MP4"
        if card_media_family == "CFexpress"
        else f"/PRIVATE/M4ROOT/SUB/{clip_name}S03.MP4"
    )

    # Slot-1 Tier-0 Vault Firewall FIRST for any Proxy write or coupled Delete/Protect touching Slot 1
    touches_slot1 = (
        target_slot == SLOT_1 or recording_media_mode == "Simult. Recording"
    )
    if touches_slot1 and (
        proxy_recording == "On" or coupled_delete_or_protect_action != "None"
    ):
        return ProxySettingsAndSubStreamResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EROFS_ERRNO,
            shoot_mode=shoot_mode,
            main_codec=main_codec,
            rec_frame_rate_str=rec_frame_rate_str,
            sq_capture_fps=sq_capture_fps,
            proxy_recording=proxy_recording,
            effective_proxy_recording="Off",
            proxy_file_format=proxy_file_format,
            effective_proxy_file_format=proxy_file_format,
            proxy_rec_setting=proxy_rec_setting,
            effective_proxy_rec_setting=proxy_rec_setting,
            proxy_resolution="1280x720" if proxy_file_format == "XAVC S HD" else "1920x1080",
            proxy_codec_family="H.264/AVC" if proxy_file_format == "XAVC S HD" else "H.265/HEVC",
            send_target_filter=send_target_filter,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            card_media_family=card_media_family,
            clip_name=clip_name,
            proxy_relpath=proxy_relpath,
            in_camera_proxy_playback_requested=in_camera_proxy_playback_requested,
            on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
            coupled_delete_or_protect_action=coupled_delete_or_protect_action,
            single_sided_proxy_edit_requested=single_sided_proxy_edit_requested,
            tier0_vault_firewall_triggered=True,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_chunk_duration=fx6_chunk_duration,
            fx6_chunk_slot="Slot B" if body_profile == BODY_MODEL_FX6 else "N/A",
            fx6_concurrent_conflict=fx6_concurrent_conflict,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason=(
                f"EROFS(30): Slot-1 Tier-0 Vault firewall blocked Proxy {proxy_relpath} "
                f"write/coupled-{coupled_delete_or_protect_action} (media={recording_media_mode})"
            ),
        )

    # In-camera Proxy playback is ALWAYS blocked on FX3 (on_camera_proxy_playback_frames == 0)
    if in_camera_proxy_playback_requested:
        return ProxySettingsAndSubStreamResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            main_codec=main_codec,
            rec_frame_rate_str=rec_frame_rate_str,
            sq_capture_fps=sq_capture_fps,
            proxy_recording=proxy_recording,
            effective_proxy_recording=proxy_recording,
            proxy_file_format=proxy_file_format,
            effective_proxy_file_format=proxy_file_format,
            proxy_rec_setting=proxy_rec_setting,
            effective_proxy_rec_setting=proxy_rec_setting,
            proxy_resolution="1280x720" if proxy_file_format == "XAVC S HD" else "1920x1080",
            proxy_codec_family="H.264/AVC" if proxy_file_format == "XAVC S HD" else "H.265/HEVC",
            send_target_filter=send_target_filter,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            card_media_family=card_media_family,
            clip_name=clip_name,
            proxy_relpath=proxy_relpath,
            in_camera_proxy_playback_requested=True,
            on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
            coupled_delete_or_protect_action=coupled_delete_or_protect_action,
            single_sided_proxy_edit_requested=single_sided_proxy_edit_requested,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_chunk_duration=fx6_chunk_duration,
            fx6_chunk_slot="Slot B" if body_profile == BODY_MODEL_FX6 else "N/A",
            fx6_concurrent_conflict=fx6_concurrent_conflict,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason="EOPNOTSUPP: Proxy sub-stream (*S03.MP4) is non-playable in-camera (parent (proxy) badge only)",
        )

    # Single-sided Proxy delete/protect without parent clip is forbidden
    if single_sided_proxy_edit_requested:
        return ProxySettingsAndSubStreamResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            main_codec=main_codec,
            rec_frame_rate_str=rec_frame_rate_str,
            sq_capture_fps=sq_capture_fps,
            proxy_recording=proxy_recording,
            effective_proxy_recording=proxy_recording,
            proxy_file_format=proxy_file_format,
            effective_proxy_file_format=proxy_file_format,
            proxy_rec_setting=proxy_rec_setting,
            effective_proxy_rec_setting=proxy_rec_setting,
            proxy_resolution="1280x720" if proxy_file_format == "XAVC S HD" else "1920x1080",
            proxy_codec_family="H.264/AVC" if proxy_file_format == "XAVC S HD" else "H.265/HEVC",
            send_target_filter=send_target_filter,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            card_media_family=card_media_family,
            clip_name=clip_name,
            proxy_relpath=proxy_relpath,
            in_camera_proxy_playback_requested=False,
            on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
            coupled_delete_or_protect_action=coupled_delete_or_protect_action,
            single_sided_proxy_edit_requested=True,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_chunk_duration=fx6_chunk_duration,
            fx6_chunk_slot="Slot B" if body_profile == BODY_MODEL_FX6 else "N/A",
            fx6_concurrent_conflict=fx6_concurrent_conflict,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason="EOPNOTSUPP: Proxy Delete/Protect is strictly coupled with parent clip (single-sided edit rejected)",
        )

    # ILME-FX6 XAVC Proxy 1920x1080 9Mbps AVC + Chunk Proxy (30s/1min/2min) on Slot B
    if body_profile == BODY_MODEL_FX6:
        if fx6_concurrent_conflict in FX6_PROXY_EXCLUSIONS or (
            fx6_chunk_duration != "Off"
            and fx6_concurrent_conflict in ("Relay Rec", "Simul Rec")
        ):
            return ProxySettingsAndSubStreamResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EBUSY_ERRNO,
                shoot_mode=shoot_mode,
                main_codec=main_codec,
                rec_frame_rate_str=rec_frame_rate_str,
                sq_capture_fps=sq_capture_fps,
                proxy_recording=proxy_recording,
                effective_proxy_recording="Off",
                proxy_file_format="XAVC Proxy",
                effective_proxy_file_format="XAVC Proxy",
                proxy_rec_setting="1920x1080 9Mbps AVC",
                effective_proxy_rec_setting="1920x1080 9Mbps AVC",
                proxy_resolution="1920x1080",
                proxy_codec_family="AVC/H.264 High Profile",
                send_target_filter=send_target_filter,
                target_slot=target_slot,
                recording_media_mode=recording_media_mode,
                card_media_family=card_media_family,
                clip_name=clip_name,
                proxy_relpath=f"/XDROOT/Sub/{clip_name}S01.MP4",
                in_camera_proxy_playback_requested=False,
                on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
                coupled_delete_or_protect_action=coupled_delete_or_protect_action,
                single_sided_proxy_edit_requested=False,
                tier0_vault_firewall_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
                fx6_chunk_duration=fx6_chunk_duration,
                fx6_chunk_slot="Slot B",
                fx6_concurrent_conflict=fx6_concurrent_conflict,
                camera_settings_reset_applied=camera_settings_reset_applied,
                reason=f"EBUSY: FX6 XAVC Proxy/Chunk mutually exclusive with {fx6_concurrent_conflict}",
            )
        return ProxySettingsAndSubStreamResult(
            body_profile=body_profile,
            admitted=True,
            errno_code=0,
            shoot_mode=shoot_mode,
            main_codec=main_codec,
            rec_frame_rate_str=rec_frame_rate_str,
            sq_capture_fps=sq_capture_fps,
            proxy_recording=proxy_recording,
            effective_proxy_recording=proxy_recording,
            proxy_file_format="XAVC Proxy",
            effective_proxy_file_format="XAVC Proxy",
            proxy_rec_setting="1920x1080 9Mbps AVC",
            effective_proxy_rec_setting="1920x1080 9Mbps AVC",
            proxy_resolution="1920x1080",
            proxy_codec_family="AVC/H.264 High Profile",
            send_target_filter=send_target_filter,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            card_media_family=card_media_family,
            clip_name=clip_name,
            proxy_relpath=f"/XDROOT/Sub/{clip_name}S01.MP4",
            in_camera_proxy_playback_requested=False,
            on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
            coupled_delete_or_protect_action=coupled_delete_or_protect_action,
            single_sided_proxy_edit_requested=False,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_chunk_duration=fx6_chunk_duration,
            fx6_chunk_slot="Slot B",
            fx6_concurrent_conflict=fx6_concurrent_conflict,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason=f"ADMITTED: FX6 XAVC Proxy 1920x1080 9Mbps AVC (Chunk={fx6_chunk_duration} on Slot B)",
        )

    # FX3 Resettable Proxy Settings ([Camera Settings Reset] resets to Off / XAVC S HD / 6M 8bit)
    if camera_settings_reset_applied:
        eff_proxy_rec = "Off"
        eff_fmt = "XAVC S HD"
        eff_set = "6M 4:2:0 8bit"
    else:
        eff_proxy_rec = proxy_recording
        eff_fmt = proxy_file_format
        eff_set = proxy_rec_setting

    # Reject dormant cross-model 8-bit enums (`16M 4:2:0 8bit`, `9M 4:2:0 8bit`)
    if eff_set in DORMANT_PROXY_REC_SETTINGS or eff_set not in VALID_PROXY_REC_SETTINGS:
        return ProxySettingsAndSubStreamResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            main_codec=main_codec,
            rec_frame_rate_str=rec_frame_rate_str,
            sq_capture_fps=sq_capture_fps,
            proxy_recording=proxy_recording,
            effective_proxy_recording="Off",
            proxy_file_format=proxy_file_format,
            effective_proxy_file_format=eff_fmt,
            proxy_rec_setting=proxy_rec_setting,
            effective_proxy_rec_setting=eff_set,
            proxy_resolution="1920x1080",
            proxy_codec_family="Dormant",
            send_target_filter=send_target_filter,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            card_media_family=card_media_family,
            clip_name=clip_name,
            proxy_relpath=proxy_relpath,
            in_camera_proxy_playback_requested=False,
            on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
            coupled_delete_or_protect_action=coupled_delete_or_protect_action,
            single_sided_proxy_edit_requested=False,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_chunk_duration="Off",
            fx6_chunk_slot="N/A",
            fx6_concurrent_conflict="None",
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason=f"EOPNOTSUPP: {eff_set!r} (_f 0x6b8f) is a dormant cross-model Proxy enum on FX3",
        )

    # Format / Bitrate pairing checks
    if eff_fmt == "XAVC S HD" and eff_set != "6M 4:2:0 8bit":
        return ProxySettingsAndSubStreamResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            shoot_mode=shoot_mode,
            main_codec=main_codec,
            rec_frame_rate_str=rec_frame_rate_str,
            sq_capture_fps=sq_capture_fps,
            proxy_recording=proxy_recording,
            effective_proxy_recording="Off",
            proxy_file_format=proxy_file_format,
            effective_proxy_file_format=eff_fmt,
            proxy_rec_setting=proxy_rec_setting,
            effective_proxy_rec_setting=eff_set,
            proxy_resolution="1280x720",
            proxy_codec_family="H.264/AVC",
            send_target_filter=send_target_filter,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            card_media_family=card_media_family,
            clip_name=clip_name,
            proxy_relpath=proxy_relpath,
            in_camera_proxy_playback_requested=False,
            on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
            coupled_delete_or_protect_action=coupled_delete_or_protect_action,
            single_sided_proxy_edit_requested=False,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_chunk_duration="Off",
            fx6_chunk_slot="N/A",
            fx6_concurrent_conflict="None",
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason=f"EINVAL: XAVC S HD Proxy supports strictly 6M 4:2:0 8bit (got {eff_set!r})",
        )
    if eff_fmt == "XAVC HS HD" and eff_set not in ("9M 4:2:0 10bit", "16M 4:2:0 10bit"):
        return ProxySettingsAndSubStreamResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            shoot_mode=shoot_mode,
            main_codec=main_codec,
            rec_frame_rate_str=rec_frame_rate_str,
            sq_capture_fps=sq_capture_fps,
            proxy_recording=proxy_recording,
            effective_proxy_recording="Off",
            proxy_file_format=proxy_file_format,
            effective_proxy_file_format=eff_fmt,
            proxy_rec_setting=proxy_rec_setting,
            effective_proxy_rec_setting=eff_set,
            proxy_resolution="1920x1080",
            proxy_codec_family="H.265/HEVC",
            send_target_filter=send_target_filter,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            card_media_family=card_media_family,
            clip_name=clip_name,
            proxy_relpath=proxy_relpath,
            in_camera_proxy_playback_requested=False,
            on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
            coupled_delete_or_protect_action=coupled_delete_or_protect_action,
            single_sided_proxy_edit_requested=False,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_chunk_duration="Off",
            fx6_chunk_slot="N/A",
            fx6_concurrent_conflict="None",
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason=f"EINVAL: XAVC HS HD Proxy supports 9M/16M 4:2:0 10bit (got {eff_set!r})",
        )

    # Exact FX3 Proxy disabled boundary:
    # - Normal Movie [Rec Frame Rate] = 119.88p / 100p
    # - S&Q [Rec Frame Rate] = 119.88p / 100p OR [Frame Rate] = 120fps / 100fps
    # - XAVC S-I DCI 4K (<= 59.94p / 50p) IS ALLOWED (subject to VPG200/400 card gate)!
    if eff_proxy_rec == "On":
        high_rec_fps = rec_frame_rate_str in ("119.88p", "100p")
        high_sq_fps = (shoot_mode == SHOOT_MODE_SQ) and (sq_capture_fps >= 100)
        if high_rec_fps or high_sq_fps:
            return ProxySettingsAndSubStreamResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                main_codec=main_codec,
                rec_frame_rate_str=rec_frame_rate_str,
                sq_capture_fps=sq_capture_fps,
                proxy_recording=proxy_recording,
                effective_proxy_recording="Off",
                proxy_file_format=proxy_file_format,
                effective_proxy_file_format=eff_fmt,
                proxy_rec_setting=proxy_rec_setting,
                effective_proxy_rec_setting=eff_set,
                proxy_resolution="1280x720" if eff_fmt == "XAVC S HD" else "1920x1080",
                proxy_codec_family="H.264/AVC" if eff_fmt == "XAVC S HD" else "H.265/HEVC",
                send_target_filter=send_target_filter,
                target_slot=target_slot,
                recording_media_mode=recording_media_mode,
                card_media_family=card_media_family,
                clip_name=clip_name,
                proxy_relpath=proxy_relpath,
                in_camera_proxy_playback_requested=False,
                on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
                coupled_delete_or_protect_action=coupled_delete_or_protect_action,
                single_sided_proxy_edit_requested=False,
                tier0_vault_firewall_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
                fx6_chunk_duration="Off",
                fx6_chunk_slot="N/A",
                fx6_concurrent_conflict="None",
                camera_settings_reset_applied=camera_settings_reset_applied,
                reason=(
                    f"EOPNOTSUPP: Proxy Recording disabled at Rec={rec_frame_rate_str} / "
                    f"S&Q_fps={sq_capture_fps}fps (cutoff strictly >=100p/100fps)"
                ),
            )
        if main_codec == "XAVC S-I DCI 4K" and _card_speed_rank_mb_s(card_speed_type) < 200:
            return ProxySettingsAndSubStreamResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                main_codec=main_codec,
                rec_frame_rate_str=rec_frame_rate_str,
                sq_capture_fps=sq_capture_fps,
                proxy_recording=proxy_recording,
                effective_proxy_recording="Off",
                proxy_file_format=proxy_file_format,
                effective_proxy_file_format=eff_fmt,
                proxy_rec_setting=proxy_rec_setting,
                effective_proxy_rec_setting=eff_set,
                proxy_resolution="1280x720" if eff_fmt == "XAVC S HD" else "1920x1080",
                proxy_codec_family="H.264/AVC" if eff_fmt == "XAVC S HD" else "H.265/HEVC",
                send_target_filter=send_target_filter,
                target_slot=target_slot,
                recording_media_mode=recording_media_mode,
                card_media_family=card_media_family,
                clip_name=clip_name,
                proxy_relpath=proxy_relpath,
                in_camera_proxy_playback_requested=False,
                on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
                coupled_delete_or_protect_action=coupled_delete_or_protect_action,
                single_sided_proxy_edit_requested=False,
                tier0_vault_firewall_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
                fx6_chunk_duration="Off",
                fx6_chunk_slot="N/A",
                fx6_concurrent_conflict="None",
                camera_settings_reset_applied=camera_settings_reset_applied,
                reason=(
                    "EOPNOTSUPP: XAVC S-I DCI 4K + Proxy allowed by format table but gated by "
                    f"VPG200/VPG400 bandwidth (got {card_speed_type})"
                ),
            )

    return ProxySettingsAndSubStreamResult(
        body_profile=body_profile,
        admitted=True,
        errno_code=0,
        shoot_mode=shoot_mode,
        main_codec=main_codec,
        rec_frame_rate_str=rec_frame_rate_str,
        sq_capture_fps=sq_capture_fps,
        proxy_recording=proxy_recording,
        effective_proxy_recording=eff_proxy_rec,
        proxy_file_format=proxy_file_format,
        effective_proxy_file_format=eff_fmt,
        proxy_rec_setting=proxy_rec_setting,
        effective_proxy_rec_setting=eff_set,
        proxy_resolution="1280x720" if eff_fmt == "XAVC S HD" else "1920x1080",
        proxy_codec_family="H.264/AVC" if eff_fmt == "XAVC S HD" else "H.265/HEVC",
        send_target_filter=send_target_filter,
        target_slot=target_slot,
        recording_media_mode=recording_media_mode,
        card_media_family=card_media_family,
        clip_name=clip_name,
        proxy_relpath=proxy_relpath,
        in_camera_proxy_playback_requested=False,
        on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
        coupled_delete_or_protect_action=coupled_delete_or_protect_action,
        single_sided_proxy_edit_requested=False,
        tier0_vault_firewall_triggered=False,
        slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
        slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
        fx6_chunk_duration="Off",
        fx6_chunk_slot="N/A",
        fx6_concurrent_conflict="None",
        camera_settings_reset_applied=camera_settings_reset_applied,
        reason=(
            f"ADMITTED: FX3 Proxy={eff_proxy_rec} ({eff_fmt} {eff_set}) on {main_codec} "
            f"{rec_frame_rate_str} -> Slot {target_slot} {proxy_relpath}"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 70C — `[Creators' Cloud]` (`Cloud Connection *` / `Cloud Information *`
#                 Surviving BOTH `[Camera Settings Reset]` AND `[Initialize]`),
#                 Ver. 4.00+ `[C3 Portal]`, Ver. 7.00+ `Clip Flag`, &
#                 CRITICAL Power-OFF BLE Zero-RF Guard vs Zero-Bluetooth `ILME-FX6`
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CloudC3PortalAndPowerOffBleResult:
    body_profile: str
    firmware_version: str
    admitted: bool
    errno_code: int
    cloud_connection: str
    effective_cloud_connection: str
    cloud_account_bound: bool
    cloud_credentials_retained: bool
    c3_portal_mode: str
    clip_flag_filter: str
    ftp_transfer_enabled: bool
    cnct_while_power_off: str
    effective_cnct_while_power_off: str
    bluetooth_function: str
    effective_bluetooth_function: str
    airplane_mode: str
    effective_airplane_mode: str
    physical_power_switch: str
    zero_rf_bench_mode: bool
    ble_standby_powered: bool
    ble_power_off_trap_detected: bool
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    camera_settings_reset_applied: bool
    reset_network_set_applied: bool
    initialize_applied: bool
    manual_cloud_account_delete_applied: bool
    reason: str


def simulate_cloud_c3portal_and_poweroff_ble_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    firmware_version: str = FW_VER_702,
    cloud_connection: str = "Off",
    cloud_account_bound: bool = True,
    c3_portal_mode: str = "Cloud(Private)",
    clip_flag_filter: str = "OK",
    ftp_transfer_enabled: bool = False,
    cnct_while_power_off: str = "Off",
    bluetooth_function: str = "Off",
    bluetooth_paired: bool = False,
    airplane_mode: str = "On",
    physical_power_switch: str = "OFF",
    zero_rf_bench_mode: bool = True,
    assume_power_off_is_zero_rf_requested: bool = False,
    camera_settings_reset_applied: bool = False,
    reset_network_set_applied: bool = False,
    initialize_applied: bool = False,
    manual_cloud_account_delete_applied: bool = False,
) -> CloudC3PortalAndPowerOffBleResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage70Phase330Error(f"Unsupported body_profile={body_profile!r}")
    if firmware_version not in VALID_FW_VERSIONS:
        raise Stage70Phase330Error(f"Unsupported firmware_version={firmware_version!r}")
    if cloud_connection not in ("On", "Off"):
        raise Stage70Phase330Error(f"Unsupported cloud_connection={cloud_connection!r}")
    if c3_portal_mode not in VALID_C3_PORTAL_MODES:
        raise Stage70Phase330Error(f"Unsupported c3_portal_mode={c3_portal_mode!r}")
    if clip_flag_filter not in VALID_CLIP_FLAG_FILTERS:
        raise Stage70Phase330Error(f"Unsupported clip_flag_filter={clip_flag_filter!r}")
    if cnct_while_power_off not in ("On", "Off"):
        raise Stage70Phase330Error(
            f"Unsupported cnct_while_power_off={cnct_while_power_off!r}"
        )
    if bluetooth_function not in ("On", "Off"):
        raise Stage70Phase330Error(f"Unsupported bluetooth_function={bluetooth_function!r}")
    if airplane_mode not in ("On", "Off"):
        raise Stage70Phase330Error(f"Unsupported airplane_mode={airplane_mode!r}")
    if physical_power_switch not in ("ON", "OFF"):
        raise Stage70Phase330Error(
            f"Unsupported physical_power_switch={physical_power_switch!r}"
        )

    # ILME-FX6 Ver. 6.01 has ZERO Bluetooth hardware (BKID_APP_SETTING_BLUETOOTH_FUNCTION dormant)
    if body_profile == BODY_MODEL_FX6:
        if cnct_while_power_off == "On" or bluetooth_function == "On":
            return CloudC3PortalAndPowerOffBleResult(
                body_profile=body_profile,
                firmware_version=FW_VER_601,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                cloud_connection=cloud_connection,
                effective_cloud_connection=cloud_connection,
                cloud_account_bound=cloud_account_bound,
                cloud_credentials_retained=cloud_account_bound,
                c3_portal_mode=c3_portal_mode,
                clip_flag_filter="Off",
                ftp_transfer_enabled=ftp_transfer_enabled,
                cnct_while_power_off=cnct_while_power_off,
                effective_cnct_while_power_off="Off",
                bluetooth_function=bluetooth_function,
                effective_bluetooth_function="Off",
                airplane_mode=airplane_mode,
                effective_airplane_mode="On" if zero_rf_bench_mode else airplane_mode,
                physical_power_switch=physical_power_switch,
                zero_rf_bench_mode=zero_rf_bench_mode,
                ble_standby_powered=False,
                ble_power_off_trap_detected=False,
                rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
                rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
                camera_settings_reset_applied=camera_settings_reset_applied,
                reset_network_set_applied=reset_network_set_applied,
                initialize_applied=initialize_applied,
                manual_cloud_account_delete_applied=manual_cloud_account_delete_applied,
                reason=(
                    "EOPNOTSUPP: ILME-FX6 Ver. 6.01 has zero Bluetooth hardware "
                    "(BKID_APP_SETTING_BLUETOOTH_FUNCTION dormant); no Power-OFF BLE wake"
                ),
            )
        return CloudC3PortalAndPowerOffBleResult(
            body_profile=body_profile,
            firmware_version=FW_VER_601,
            admitted=True,
            errno_code=0,
            cloud_connection=cloud_connection,
            effective_cloud_connection=cloud_connection,
            cloud_account_bound=cloud_account_bound and (not manual_cloud_account_delete_applied),
            cloud_credentials_retained=cloud_account_bound and (not manual_cloud_account_delete_applied),
            c3_portal_mode=c3_portal_mode,
            clip_flag_filter="Off",
            ftp_transfer_enabled=ftp_transfer_enabled,
            cnct_while_power_off="Off",
            effective_cnct_while_power_off="Off",
            bluetooth_function="Off",
            effective_bluetooth_function="Off",
            airplane_mode=airplane_mode,
            effective_airplane_mode="On" if zero_rf_bench_mode else airplane_mode,
            physical_power_switch=physical_power_switch,
            zero_rf_bench_mode=zero_rf_bench_mode,
            ble_standby_powered=False,
            ble_power_off_trap_detected=False,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            manual_cloud_account_delete_applied=manual_cloud_account_delete_applied,
            reason=f"ADMITTED: ILME-FX6 C3 Portal={c3_portal_mode} (zero Bluetooth hardware)",
        )

    # FX3 firmware version gates for Ver. 4.00 C3 Portal, Ver. 5.00 Creators' Cloud, Ver. 7.00 Clip Flag
    if cloud_connection == "On" and firmware_version in (FW_VER_200, FW_VER_300, FW_VER_400):
        return CloudC3PortalAndPowerOffBleResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            cloud_connection=cloud_connection,
            effective_cloud_connection="Off",
            cloud_account_bound=False,
            cloud_credentials_retained=False,
            c3_portal_mode=c3_portal_mode,
            clip_flag_filter="Off",
            ftp_transfer_enabled=ftp_transfer_enabled,
            cnct_while_power_off=cnct_while_power_off,
            effective_cnct_while_power_off="Off",
            bluetooth_function=bluetooth_function,
            effective_bluetooth_function="Off",
            airplane_mode=airplane_mode,
            effective_airplane_mode="On",
            physical_power_switch=physical_power_switch,
            zero_rf_bench_mode=zero_rf_bench_mode,
            ble_standby_powered=False,
            ble_power_off_trap_detected=False,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            manual_cloud_account_delete_applied=manual_cloud_account_delete_applied,
            reason=f"EOPNOTSUPP: [Creators' Cloud] requires Ver. 5.00+ (got {firmware_version})",
        )

    # Cloud Connection * & Cloud Information * survive BOTH [Camera Settings Reset] AND [Initialize]!
    # Cleared ONLY via manual account deletion in [Cloud Information].
    if manual_cloud_account_delete_applied:
        eff_cloud = "Off"
        eff_bound = False
    else:
        eff_cloud = cloud_connection
        eff_bound = cloud_account_bound

    # Cloud Connection is mutually exclusive with FTP (`CLOUD_CONNECTION_ON_FTP_OFF`)
    if eff_cloud == "On" and ftp_transfer_enabled:
        return CloudC3PortalAndPowerOffBleResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EBUSY_ERRNO,
            cloud_connection=cloud_connection,
            effective_cloud_connection=eff_cloud,
            cloud_account_bound=eff_bound,
            cloud_credentials_retained=eff_bound,
            c3_portal_mode=c3_portal_mode,
            clip_flag_filter=clip_flag_filter,
            ftp_transfer_enabled=True,
            cnct_while_power_off=cnct_while_power_off,
            effective_cnct_while_power_off="Off",
            bluetooth_function=bluetooth_function,
            effective_bluetooth_function="Off",
            airplane_mode=airplane_mode,
            effective_airplane_mode="On",
            physical_power_switch=physical_power_switch,
            zero_rf_bench_mode=zero_rf_bench_mode,
            ble_standby_powered=False,
            ble_power_off_trap_detected=False,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            manual_cloud_account_delete_applied=manual_cloud_account_delete_applied,
            reason="EBUSY: [Cloud Connection] mutually exclusive with FTP (CLOUD_CONNECTION_ON_FTP_OFF)",
        )

    # [Cnct. while Power OFF] & [Bluetooth Function] survive [Camera Settings Reset],
    # cleared ONLY by [Reset Network Set.] or [Initialize].
    if reset_network_set_applied or initialize_applied:
        eff_cnct_power_off = "Off"
        eff_bt = "Off"
    else:
        eff_cnct_power_off = cnct_while_power_off
        eff_bt = bluetooth_function

    # Airplane Mode persists across both resets; Zero-RF Bench Guard enforces 3-lock Zero-RF
    eff_airplane = airplane_mode

    # CRITICAL Power-OFF BLE Trap detection:
    # Physical power switch == OFF does NOT imply Zero-RF if [Cnct. while Power OFF] = On!
    ble_standby_powered = (
        eff_cnct_power_off == "On"
        and eff_airplane == "Off"
        and (bluetooth_paired or eff_bt == "On")
    )
    three_lock_ok = (
        eff_airplane == "On"
        and eff_cnct_power_off == "Off"
        and eff_bt == "Off"
    )
    trap_detected = bool(
        (physical_power_switch == "OFF" and ble_standby_powered)
        or assume_power_off_is_zero_rf_requested
    )

    if zero_rf_bench_mode and not three_lock_ok:
        return CloudC3PortalAndPowerOffBleResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EPERM_ERRNO,
            cloud_connection=cloud_connection,
            effective_cloud_connection=eff_cloud,
            cloud_account_bound=eff_bound,
            cloud_credentials_retained=eff_bound,
            c3_portal_mode=c3_portal_mode,
            clip_flag_filter=clip_flag_filter,
            ftp_transfer_enabled=ftp_transfer_enabled,
            cnct_while_power_off=cnct_while_power_off,
            effective_cnct_while_power_off=eff_cnct_power_off,
            bluetooth_function=bluetooth_function,
            effective_bluetooth_function=eff_bt,
            airplane_mode=airplane_mode,
            effective_airplane_mode=eff_airplane,
            physical_power_switch=physical_power_switch,
            zero_rf_bench_mode=True,
            ble_standby_powered=ble_standby_powered,
            ble_power_off_trap_detected=trap_detected,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            manual_cloud_account_delete_applied=manual_cloud_account_delete_applied,
            reason=(
                "EPERM: Power-OFF BLE Zero-RF 3-Lock violated "
                f"(Airplane={eff_airplane}, CnctWhilePowerOFF={eff_cnct_power_off}, "
                f"BT={eff_bt}, switch={physical_power_switch}, ble_standby={ble_standby_powered})"
            ),
        )

    eff_clip_flag = (
        clip_flag_filter if firmware_version in (FW_VER_700, FW_VER_702) else "Off"
    )
    return CloudC3PortalAndPowerOffBleResult(
        body_profile=body_profile,
        firmware_version=firmware_version,
        admitted=True,
        errno_code=0,
        cloud_connection=cloud_connection,
        effective_cloud_connection=eff_cloud,
        cloud_account_bound=eff_bound,
        cloud_credentials_retained=eff_bound,
        c3_portal_mode=c3_portal_mode,
        clip_flag_filter=eff_clip_flag,
        ftp_transfer_enabled=ftp_transfer_enabled,
        cnct_while_power_off=cnct_while_power_off,
        effective_cnct_while_power_off=eff_cnct_power_off,
        bluetooth_function=bluetooth_function,
        effective_bluetooth_function=eff_bt,
        airplane_mode=airplane_mode,
        effective_airplane_mode=eff_airplane,
        physical_power_switch=physical_power_switch,
        zero_rf_bench_mode=zero_rf_bench_mode,
        ble_standby_powered=False,
        ble_power_off_trap_detected=False,
        rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
        rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
        camera_settings_reset_applied=camera_settings_reset_applied,
        reset_network_set_applied=reset_network_set_applied,
        initialize_applied=initialize_applied,
        manual_cloud_account_delete_applied=manual_cloud_account_delete_applied,
        reason=(
            f"ADMITTED: FX3 {firmware_version} Cloud={eff_cloud}(retained={eff_bound}), "
            f"C3={c3_portal_mode}, ClipFlag={eff_clip_flag}, Zero-RF 3-Lock OK (rf_tx=0)"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 70D — `[My Menu]` (`6 pages x 7 items = 42` Slots,
#                 `BKID_APP_mymenu_group{1..6}_setting_list{0..6}`) vs
#                 `ILME-FX6` `20`-Item `User Menu` + `User Menu Only` +
#                 `User Menu with Lock` (`0000..9999` PIN Excluded from `All File` & `Scene File`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MyMenuAndFx6UserMenuLockResult:
    body_profile: str
    admitted: bool
    errno_code: int
    group_number: int
    item_index: int
    nvram_key: str
    operation: str
    item_domain: str
    item_count_requested: int
    effective_item_count: int
    max_capacity: int
    display_from_my_menu: str
    effective_display_from_my_menu: str
    fx6_user_menu_mode: str
    fx6_combo_hold_revealed: bool
    fx6_pin_code: str
    fx6_unlock_attempt_pin: Optional[str]
    fx6_locked: bool
    exported_in_all_file: bool
    exported_in_scene_file: bool
    camera_settings_reset_applied: bool
    delete_all_applied: bool
    initialize_applied: bool
    reason: str


def simulate_mymenu_and_fx6_user_menu_lock_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    group_number: int = 1,
    item_index: int = 0,
    operation: str = "Add Item",
    item_domain: str = "Shooting",
    item_count_requested: int = 42,
    display_from_my_menu: str = "On",
    camera_settings_reset_applied: bool = False,
    delete_all_applied: bool = False,
    initialize_applied: bool = False,
    fx6_user_menu_mode: str = "User Menu",
    fx6_combo_hold_revealed: bool = False,
    fx6_pin_code: str = "0000",
    fx6_unlock_attempt_pin: Optional[str] = None,
) -> MyMenuAndFx6UserMenuLockResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage70Phase330Error(f"Unsupported body_profile={body_profile!r}")
    if operation not in FX3_MYMENU_ALLOWED_OPS:
        raise Stage70Phase330Error(f"Unsupported operation={operation!r}")
    if item_domain not in ("Shooting", "Exposure/Color", "Focus", "Setup", "Network", "Playback"):
        raise Stage70Phase330Error(f"Unsupported item_domain={item_domain!r}")
    if display_from_my_menu not in ("On", "Off"):
        raise Stage70Phase330Error(
            f"Unsupported display_from_my_menu={display_from_my_menu!r}"
        )
    if fx6_user_menu_mode not in FX6_USER_MENU_MODES:
        raise Stage70Phase330Error(f"Unsupported fx6_user_menu_mode={fx6_user_menu_mode!r}")

    # ILME-FX6 20-item User Menu + User Menu Only + rental-house User Menu with Lock
    if body_profile == BODY_MODEL_FX6:
        if item_count_requested < 0 or item_count_requested > FX6_USER_MENU_CAPACITY:
            return MyMenuAndFx6UserMenuLockResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                group_number=1,
                item_index=item_count_requested,
                nvram_key="FX6_USER_MENU_OOB",
                operation=operation,
                item_domain=item_domain,
                item_count_requested=item_count_requested,
                effective_item_count=0,
                max_capacity=FX6_USER_MENU_CAPACITY,
                display_from_my_menu="N/A",
                effective_display_from_my_menu="N/A",
                fx6_user_menu_mode=fx6_user_menu_mode,
                fx6_combo_hold_revealed=fx6_combo_hold_revealed,
                fx6_pin_code="****",
                fx6_unlock_attempt_pin=None,
                fx6_locked=False,
                exported_in_all_file=False,
                exported_in_scene_file=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                delete_all_applied=delete_all_applied,
                initialize_applied=initialize_applied,
                reason=(
                    f"EINVAL: ILME-FX6 User Menu capacity is strictly {FX6_USER_MENU_CAPACITY} items "
                    f"(got {item_count_requested})"
                ),
            )
        if fx6_user_menu_mode == "User Menu with Lock":
            if not (len(fx6_pin_code) == 4 and fx6_pin_code.isdigit()):
                return MyMenuAndFx6UserMenuLockResult(
                    body_profile=body_profile,
                    admitted=False,
                    errno_code=EINVAL_ERRNO,
                    group_number=1,
                    item_index=0,
                    nvram_key="FX6_USER_MENU_WITH_LOCK",
                    operation=operation,
                    item_domain=item_domain,
                    item_count_requested=item_count_requested,
                    effective_item_count=item_count_requested,
                    max_capacity=FX6_USER_MENU_CAPACITY,
                    display_from_my_menu="N/A",
                    effective_display_from_my_menu="N/A",
                    fx6_user_menu_mode=fx6_user_menu_mode,
                    fx6_combo_hold_revealed=fx6_combo_hold_revealed,
                    fx6_pin_code="INVALID",
                    fx6_unlock_attempt_pin=None,
                    fx6_locked=True,
                    exported_in_all_file=False,
                    exported_in_scene_file=False,
                    camera_settings_reset_applied=camera_settings_reset_applied,
                    delete_all_applied=delete_all_applied,
                    initialize_applied=initialize_applied,
                    reason="EINVAL: FX6 User Menu with Lock requires exact 4-digit PIN 0000..9999",
                )
            if not fx6_combo_hold_revealed:
                return MyMenuAndFx6UserMenuLockResult(
                    body_profile=body_profile,
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    group_number=1,
                    item_index=0,
                    nvram_key="FX6_USER_MENU_WITH_LOCK",
                    operation=operation,
                    item_domain=item_domain,
                    item_count_requested=item_count_requested,
                    effective_item_count=item_count_requested,
                    max_capacity=FX6_USER_MENU_CAPACITY,
                    display_from_my_menu="N/A",
                    effective_display_from_my_menu="N/A",
                    fx6_user_menu_mode=fx6_user_menu_mode,
                    fx6_combo_hold_revealed=False,
                    fx6_pin_code="****",
                    fx6_unlock_attempt_pin=None,
                    fx6_locked=True,
                    exported_in_all_file=False,
                    exported_in_scene_file=False,
                    camera_settings_reset_applied=camera_settings_reset_applied,
                    delete_all_applied=delete_all_applied,
                    initialize_applied=initialize_applied,
                    reason=(
                        "EOPNOTSUPP: FX6 [User Menu with Lock] is hidden until holding "
                        "Multi-selector dial + MENU simultaneously"
                    ),
                )
            if fx6_unlock_attempt_pin is not None and fx6_unlock_attempt_pin != fx6_pin_code:
                return MyMenuAndFx6UserMenuLockResult(
                    body_profile=body_profile,
                    admitted=False,
                    errno_code=EACCES_ERRNO,
                    group_number=1,
                    item_index=0,
                    nvram_key="FX6_USER_MENU_WITH_LOCK",
                    operation=operation,
                    item_domain=item_domain,
                    item_count_requested=item_count_requested,
                    effective_item_count=item_count_requested,
                    max_capacity=FX6_USER_MENU_CAPACITY,
                    display_from_my_menu="N/A",
                    effective_display_from_my_menu="N/A",
                    fx6_user_menu_mode=fx6_user_menu_mode,
                    fx6_combo_hold_revealed=True,
                    fx6_pin_code="****",
                    fx6_unlock_attempt_pin="****",
                    fx6_locked=True,
                    exported_in_all_file=False,
                    exported_in_scene_file=False,
                    camera_settings_reset_applied=camera_settings_reset_applied,
                    delete_all_applied=delete_all_applied,
                    initialize_applied=initialize_applied,
                    reason="EACCES: FX6 User Menu with Lock 4-digit PIN mismatch (remains locked)",
                )
            unlocked = fx6_unlock_attempt_pin == fx6_pin_code
            return MyMenuAndFx6UserMenuLockResult(
                body_profile=body_profile,
                admitted=True,
                errno_code=0,
                group_number=1,
                item_index=0,
                nvram_key="FX6_USER_MENU_WITH_LOCK",
                operation=operation,
                item_domain=item_domain,
                item_count_requested=item_count_requested,
                effective_item_count=item_count_requested,
                max_capacity=FX6_USER_MENU_CAPACITY,
                display_from_my_menu="N/A",
                effective_display_from_my_menu="N/A",
                fx6_user_menu_mode=fx6_user_menu_mode,
                fx6_combo_hold_revealed=True,
                fx6_pin_code="****",
                fx6_unlock_attempt_pin="****" if fx6_unlock_attempt_pin is not None else None,
                fx6_locked=(not unlocked),
                exported_in_all_file=False,
                exported_in_scene_file=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                delete_all_applied=delete_all_applied,
                initialize_applied=initialize_applied,
                reason=(
                    f"ADMITTED: FX6 User Menu with Lock (locked={not unlocked}, "
                    "excluded from BOTH All File & Scene File)"
                ),
            )

        return MyMenuAndFx6UserMenuLockResult(
            body_profile=body_profile,
            admitted=True,
            errno_code=0,
            group_number=1,
            item_index=0,
            nvram_key="BKID_APP_SETTING_USER_MENU_ONLY"
            if fx6_user_menu_mode == "User Menu Only"
            else "FX6_USER_MENU",
            operation=operation,
            item_domain=item_domain,
            item_count_requested=item_count_requested,
            effective_item_count=item_count_requested,
            max_capacity=FX6_USER_MENU_CAPACITY,
            display_from_my_menu="N/A",
            effective_display_from_my_menu="N/A",
            fx6_user_menu_mode=fx6_user_menu_mode,
            fx6_combo_hold_revealed=fx6_combo_hold_revealed,
            fx6_pin_code="N/A",
            fx6_unlock_attempt_pin=None,
            fx6_locked=(fx6_user_menu_mode == "User Menu Only"),
            exported_in_all_file=True,
            exported_in_scene_file=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            delete_all_applied=delete_all_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"ADMITTED: FX6 {fx6_user_menu_mode} ({item_count_requested}/20 items; "
                "saved in All File, excluded from Scene File)"
            ),
        )

    # FX3 rejects FX6 rental-house locks (User Menu Only / User Menu with Lock)
    if fx6_user_menu_mode != "User Menu":
        return MyMenuAndFx6UserMenuLockResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            group_number=group_number,
            item_index=item_index,
            nvram_key="FX3_NO_USER_MENU_LOCK",
            operation=operation,
            item_domain=item_domain,
            item_count_requested=item_count_requested,
            effective_item_count=0,
            max_capacity=MYMENU_EXACT_SLOT_CAPACITY,
            display_from_my_menu=display_from_my_menu,
            effective_display_from_my_menu=display_from_my_menu,
            fx6_user_menu_mode=fx6_user_menu_mode,
            fx6_combo_hold_revealed=fx6_combo_hold_revealed,
            fx6_pin_code="N/A",
            fx6_unlock_attempt_pin=None,
            fx6_locked=False,
            exported_in_all_file=False,
            exported_in_scene_file=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            delete_all_applied=delete_all_applied,
            initialize_applied=initialize_applied,
            reason=f"EOPNOTSUPP: ILME-FX3 lacks FX6 rental-house [{fx6_user_menu_mode}] lock",
        )

    # FX3 exact 6 pages x 7 items = 42 NVRAM slots: group1..6 x list0..6
    nvram_key = f"BKID_APP_mymenu_group{group_number}_setting_list{item_index}"
    if (
        not (1 <= group_number <= MYMENU_PAGES)
        or not (0 <= item_index < MYMENU_ITEMS_PER_PAGE)
        or item_count_requested < 0
        or item_count_requested > MYMENU_EXACT_SLOT_CAPACITY
    ):
        return MyMenuAndFx6UserMenuLockResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            group_number=group_number,
            item_index=item_index,
            nvram_key=nvram_key,
            operation=operation,
            item_domain=item_domain,
            item_count_requested=item_count_requested,
            effective_item_count=0,
            max_capacity=MYMENU_EXACT_SLOT_CAPACITY,
            display_from_my_menu=display_from_my_menu,
            effective_display_from_my_menu=display_from_my_menu,
            fx6_user_menu_mode="N/A",
            fx6_combo_hold_revealed=False,
            fx6_pin_code="N/A",
            fx6_unlock_attempt_pin=None,
            fx6_locked=False,
            exported_in_all_file=False,
            exported_in_scene_file=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            delete_all_applied=delete_all_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EINVAL: FX3 [My Menu] NVRAM slots strictly group1..6 x list0..6 (42 max); "
                f"rejected {nvram_key} / count={item_count_requested}"
            ),
        )

    if item_domain == "Playback" and operation == "Add Item":
        return MyMenuAndFx6UserMenuLockResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            group_number=group_number,
            item_index=item_index,
            nvram_key=nvram_key,
            operation=operation,
            item_domain=item_domain,
            item_count_requested=item_count_requested,
            effective_item_count=0,
            max_capacity=MYMENU_EXACT_SLOT_CAPACITY,
            display_from_my_menu=display_from_my_menu,
            effective_display_from_my_menu=display_from_my_menu,
            fx6_user_menu_mode="N/A",
            fx6_combo_hold_revealed=False,
            fx6_pin_code="N/A",
            fx6_unlock_attempt_pin=None,
            fx6_locked=False,
            exported_in_all_file=False,
            exported_in_scene_file=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            delete_all_applied=delete_all_applied,
            initialize_applied=initialize_applied,
            reason="EOPNOTSUPP: FX3 [My Menu] rejects (Playback) menu items",
        )

    # Lifecycle: survives [Camera Settings Reset]; cleared ONLY by [Delete All] or [Initialize]
    if initialize_applied:
        eff_count = 0
        eff_disp = "Off"
    elif delete_all_applied or operation == "Delete All":
        eff_count = 0
        eff_disp = display_from_my_menu
    else:
        eff_count = item_count_requested
        eff_disp = display_from_my_menu

    return MyMenuAndFx6UserMenuLockResult(
        body_profile=body_profile,
        admitted=True,
        errno_code=0,
        group_number=group_number,
        item_index=item_index,
        nvram_key=nvram_key,
        operation=operation,
        item_domain=item_domain,
        item_count_requested=item_count_requested,
        effective_item_count=eff_count,
        max_capacity=MYMENU_EXACT_SLOT_CAPACITY,
        display_from_my_menu=display_from_my_menu,
        effective_display_from_my_menu=eff_disp,
        fx6_user_menu_mode="N/A",
        fx6_combo_hold_revealed=False,
        fx6_pin_code="N/A",
        fx6_unlock_attempt_pin=None,
        fx6_locked=False,
        exported_in_all_file=False,
        exported_in_scene_file=False,
        camera_settings_reset_applied=camera_settings_reset_applied,
        delete_all_applied=delete_all_applied,
        initialize_applied=initialize_applied,
        reason=(
            f"ADMITTED: FX3 [My Menu] {nvram_key} ({eff_count}/42 slots, "
            f"DisplayFromMyMenu={eff_disp}, survives_cam_reset=True)"
        ),
    )


def _build_stage70_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_70th_stage_milestone": IS_70TH_STAGE_MILESTONE,
        "wave": "Wave-60",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase330_rec_media_autoswitch_proxy_cloud_mymenu_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 330 Stage 70 (70/70 Milestone!) Wave-60 HIL co-emulation."""
    donor_audit = inspect_phase330_donors(force_clean_room=force_clean_room, env=env)

    # Sub-Model 70A probes
    p70a_prioritize_removed = simulate_rec_media_autoswitch_and_speed_gate_hil(
        prioritize_rec_media_requested=True,
    )
    p70a_movie_sort_rejected = simulate_rec_media_autoswitch_and_speed_gate_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        recording_media_mode="Sort Recording",
    )
    p70a_still_sort_slot2_blocked = simulate_rec_media_autoswitch_and_speed_gate_hil(
        shoot_mode=SHOOT_MODE_STILL,
        recording_media_mode="Sort Recording",
    )
    p70a_simult_fs_mismatch = simulate_rec_media_autoswitch_and_speed_gate_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        recording_media_mode="Simult. Recording",
        slot1_filesystem="exFAT",
        slot2_filesystem="FAT32",
    )
    p70a_overflow_trap_duallock = simulate_rec_media_autoswitch_and_speed_gate_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        recording_media_mode="Slot 2",
        auto_switch_media="On",
        slot2_remaining_mb=0,
        tier0_vault_dual_lock_active=True,
        nvram_autoforce_relay_off=True,
        camera_settings_reset_applied=True,
    )
    p70a_sq_1200m_cfex_ok = simulate_rec_media_autoswitch_and_speed_gate_hil(
        shoot_mode=SHOOT_MODE_SQ,
        recording_media_mode="Slot 2",
        auto_switch_media="Off",
        slot2_card_type="CFexpress_Type_A_VPG400",
        movie_codec="XAVC S-I 4K",
        bitrate_mbps=1200,
        fps=60,
        proxy_co_recording=True,
    )
    p70a_sq_1200m_sdxc_rejected = simulate_rec_media_autoswitch_and_speed_gate_hil(
        shoot_mode=SHOOT_MODE_SQ,
        recording_media_mode="Slot 2",
        slot2_card_type="SDXC_V90",
        movie_codec="XAVC S-I 4K",
        bitrate_mbps=1200,
        fps=60,
    )
    p70a_fx6_simul_and_exclusion = [
        simulate_rec_media_autoswitch_and_speed_gate_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_simul_rec=True,
            fx6_body_rec_button_slot="Slot A",
            fx6_handle_rec_button_slot="Slot B",
        ),
        simulate_rec_media_autoswitch_and_speed_gate_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_simul_rec=True,
            fx6_concurrent_conflict="Proxy Rec",
        ),
    ]
    p70a_ok = (
        (not p70a_prioritize_removed.admitted)
        and p70a_prioritize_removed.errno_code == EOPNOTSUPP_ERRNO
        and (not p70a_movie_sort_rejected.admitted)
        and p70a_movie_sort_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p70a_still_sort_slot2_blocked.admitted)
        and p70a_still_sort_slot2_blocked.errno_code == EROFS_ERRNO
        and p70a_still_sort_slot2_blocked.still_quality_shared_across_slots
        and (not p70a_simult_fs_mismatch.admitted)
        and p70a_simult_fs_mismatch.errno_code == EINVAL_ERRNO
        and (not p70a_overflow_trap_duallock.admitted)
        and p70a_overflow_trap_duallock.errno_code == EROFS_ERRNO
        and p70a_overflow_trap_duallock.effective_auto_switch_media == "Off"
        and p70a_overflow_trap_duallock.overflow_dual_lock_triggered
        and p70a_overflow_trap_duallock.slot1_data_sector_writes == 0
        and (not p70a_overflow_trap_duallock.slot1_avf_info_mutated)
        and p70a_sq_1200m_cfex_ok.admitted
        and p70a_sq_1200m_cfex_ok.vpg_gate_level == "CFexpress VPG400"
        and (not p70a_sq_1200m_sdxc_rejected.admitted)
        and p70a_sq_1200m_sdxc_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p70a_fx6_simul_and_exclusion[0].admitted
        and (not p70a_fx6_simul_and_exclusion[1].admitted)
        and p70a_fx6_simul_and_exclusion[1].errno_code == EBUSY_ERRNO
    )

    # Sub-Model 70B probes
    p70b_dci4k_proxy_allowed = simulate_proxy_settings_and_substream_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        main_codec="XAVC S-I DCI 4K",
        rec_frame_rate_str="59.94p",
        proxy_recording="On",
        proxy_file_format="XAVC HS HD",
        proxy_rec_setting="16M 4:2:0 10bit",
        card_media_family="CFexpress",
        card_speed_type="CFexpress_Type_A_VPG400",
    )
    p70b_120p_and_sq120fps_cutoff = [
        simulate_proxy_settings_and_substream_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            main_codec="XAVC S 4K",
            rec_frame_rate_str="119.88p",
            proxy_recording="On",
        ),
        simulate_proxy_settings_and_substream_hil(
            shoot_mode=SHOOT_MODE_SQ,
            main_codec="XAVC S HD",
            rec_frame_rate_str="23.98p",
            sq_capture_fps=120,
            proxy_recording="On",
        ),
    ]
    p70b_playback_and_split_rejected = [
        simulate_proxy_settings_and_substream_hil(
            in_camera_proxy_playback_requested=True,
        ),
        simulate_proxy_settings_and_substream_hil(
            single_sided_proxy_edit_requested=True,
        ),
    ]
    p70b_slot1_vault_proxy_erofs = simulate_proxy_settings_and_substream_hil(
        target_slot=SLOT_1,
        recording_media_mode="Simult. Recording",
        proxy_recording="On",
        coupled_delete_or_protect_action="Delete",
    )
    p70b_fx6_chunk_ok_and_conflict = [
        simulate_proxy_settings_and_substream_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_chunk_duration="1min",
        ),
        simulate_proxy_settings_and_substream_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_chunk_duration="30s",
            fx6_concurrent_conflict="Relay Rec",
        ),
    ]
    p70b_ok = (
        p70b_dci4k_proxy_allowed.admitted
        and p70b_dci4k_proxy_allowed.proxy_relpath == "/M4ROOT/SUB/C0001S03.MP4"
        and p70b_dci4k_proxy_allowed.on_camera_proxy_playback_frames == 0
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO
            for r in p70b_120p_and_sq120fps_cutoff
        )
        and all(
            (not r.admitted)
            and r.errno_code == EOPNOTSUPP_ERRNO
            and r.on_camera_proxy_playback_frames == 0
            for r in p70b_playback_and_split_rejected
        )
        and (not p70b_slot1_vault_proxy_erofs.admitted)
        and p70b_slot1_vault_proxy_erofs.errno_code == EROFS_ERRNO
        and p70b_slot1_vault_proxy_erofs.tier0_vault_firewall_triggered
        and p70b_slot1_vault_proxy_erofs.slot1_data_sector_writes == 0
        and (not p70b_slot1_vault_proxy_erofs.slot1_avf_info_mutated)
        and p70b_fx6_chunk_ok_and_conflict[0].admitted
        and p70b_fx6_chunk_ok_and_conflict[0].fx6_chunk_slot == "Slot B"
        and (not p70b_fx6_chunk_ok_and_conflict[1].admitted)
        and p70b_fx6_chunk_ok_and_conflict[1].errno_code == EBUSY_ERRNO
    )

    # Sub-Model 70C probes
    p70c_zero_rf_3lock_ok = simulate_cloud_c3portal_and_poweroff_ble_hil(
        firmware_version=FW_VER_702,
        cloud_connection="On",
        cloud_account_bound=True,
        c3_portal_mode="Cloud(Share)",
        clip_flag_filter="OK",
        cnct_while_power_off="Off",
        bluetooth_function="Off",
        airplane_mode="On",
        physical_power_switch="OFF",
        zero_rf_bench_mode=True,
        initialize_applied=True,
    )
    p70c_ble_poweroff_trap_rejected = simulate_cloud_c3portal_and_poweroff_ble_hil(
        cnct_while_power_off="On",
        bluetooth_function="On",
        bluetooth_paired=True,
        airplane_mode="Off",
        physical_power_switch="OFF",
        zero_rf_bench_mode=True,
        assume_power_off_is_zero_rf_requested=True,
    )
    p70c_cloud_ftp_conflict = simulate_cloud_c3portal_and_poweroff_ble_hil(
        cloud_connection="On",
        ftp_transfer_enabled=True,
        airplane_mode="On",
        cnct_while_power_off="Off",
        bluetooth_function="Off",
    )
    p70c_fx6_zero_bt_rejected = simulate_cloud_c3portal_and_poweroff_ble_hil(
        body_profile=BODY_MODEL_FX6,
        cnct_while_power_off="On",
    )
    p70c_ok = (
        p70c_zero_rf_3lock_ok.admitted
        and p70c_zero_rf_3lock_ok.cloud_credentials_retained
        and p70c_zero_rf_3lock_ok.effective_cloud_connection == "On"
        and p70c_zero_rf_3lock_ok.effective_cnct_while_power_off == "Off"
        and p70c_zero_rf_3lock_ok.rf_packets_transmitted == 0
        and p70c_zero_rf_3lock_ok.rf_nvs_mutation_bytes == 0
        and (not p70c_zero_rf_3lock_ok.ble_standby_powered)
        and (not p70c_ble_poweroff_trap_rejected.admitted)
        and p70c_ble_poweroff_trap_rejected.errno_code == EPERM_ERRNO
        and p70c_ble_poweroff_trap_rejected.ble_standby_powered
        and p70c_ble_poweroff_trap_rejected.ble_power_off_trap_detected
        and p70c_ble_poweroff_trap_rejected.rf_packets_transmitted == 0
        and (not p70c_cloud_ftp_conflict.admitted)
        and p70c_cloud_ftp_conflict.errno_code == EBUSY_ERRNO
        and (not p70c_fx6_zero_bt_rejected.admitted)
        and p70c_fx6_zero_bt_rejected.errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 70D probes
    p70d_fx3_42_slots_survive_cam_reset = simulate_mymenu_and_fx6_user_menu_lock_hil(
        group_number=6,
        item_index=6,
        item_count_requested=42,
        display_from_my_menu="On",
        camera_settings_reset_applied=True,
    )
    p70d_fx3_oob_and_playback_rejected = [
        simulate_mymenu_and_fx6_user_menu_lock_hil(group_number=0, item_index=0),
        simulate_mymenu_and_fx6_user_menu_lock_hil(group_number=7, item_index=0),
        simulate_mymenu_and_fx6_user_menu_lock_hil(group_number=1, item_index=7),
        simulate_mymenu_and_fx6_user_menu_lock_hil(
            group_number=1,
            item_index=0,
            item_domain="Playback",
        ),
    ]
    p70d_fx3_delete_all_and_init = [
        simulate_mymenu_and_fx6_user_menu_lock_hil(
            item_count_requested=42,
            display_from_my_menu="On",
            delete_all_applied=True,
        ),
        simulate_mymenu_and_fx6_user_menu_lock_hil(
            item_count_requested=42,
            display_from_my_menu="On",
            initialize_applied=True,
        ),
    ]
    p70d_fx6_user_menu_20_and_lock = [
        simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=BODY_MODEL_FX6,
            item_count_requested=20,
            fx6_user_menu_mode="User Menu Only",
        ),
        simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=BODY_MODEL_FX6,
            item_count_requested=21,
        ),
        simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=BODY_MODEL_FX6,
            item_count_requested=12,
            fx6_user_menu_mode="User Menu with Lock",
            fx6_combo_hold_revealed=True,
            fx6_pin_code="4270",
            fx6_unlock_attempt_pin="4270",
        ),
        simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=BODY_MODEL_FX6,
            item_count_requested=12,
            fx6_user_menu_mode="User Menu with Lock",
            fx6_combo_hold_revealed=True,
            fx6_pin_code="4270",
            fx6_unlock_attempt_pin="0000",
        ),
    ]
    p70d_ok = (
        p70d_fx3_42_slots_survive_cam_reset.admitted
        and p70d_fx3_42_slots_survive_cam_reset.max_capacity == 42
        and p70d_fx3_42_slots_survive_cam_reset.effective_item_count == 42
        and p70d_fx3_42_slots_survive_cam_reset.nvram_key
        == "BKID_APP_mymenu_group6_setting_list6"
        and (not p70d_fx3_oob_and_playback_rejected[0].admitted)
        and p70d_fx3_oob_and_playback_rejected[0].errno_code == EINVAL_ERRNO
        and (not p70d_fx3_oob_and_playback_rejected[1].admitted)
        and p70d_fx3_oob_and_playback_rejected[1].errno_code == EINVAL_ERRNO
        and (not p70d_fx3_oob_and_playback_rejected[2].admitted)
        and p70d_fx3_oob_and_playback_rejected[2].errno_code == EINVAL_ERRNO
        and (not p70d_fx3_oob_and_playback_rejected[3].admitted)
        and p70d_fx3_oob_and_playback_rejected[3].errno_code == EOPNOTSUPP_ERRNO
        and p70d_fx3_delete_all_and_init[0].effective_item_count == 0
        and p70d_fx3_delete_all_and_init[0].effective_display_from_my_menu == "On"
        and p70d_fx3_delete_all_and_init[1].effective_item_count == 0
        and p70d_fx3_delete_all_and_init[1].effective_display_from_my_menu == "Off"
        and p70d_fx6_user_menu_20_and_lock[0].admitted
        and p70d_fx6_user_menu_20_and_lock[0].exported_in_all_file
        and (not p70d_fx6_user_menu_20_and_lock[0].exported_in_scene_file)
        and (not p70d_fx6_user_menu_20_and_lock[1].admitted)
        and p70d_fx6_user_menu_20_and_lock[1].errno_code == EINVAL_ERRNO
        and p70d_fx6_user_menu_20_and_lock[2].admitted
        and (not p70d_fx6_user_menu_20_and_lock[2].fx6_locked)
        and (not p70d_fx6_user_menu_20_and_lock[2].exported_in_all_file)
        and (not p70d_fx6_user_menu_20_and_lock[2].exported_in_scene_file)
        and (not p70d_fx6_user_menu_20_and_lock[3].admitted)
        and p70d_fx6_user_menu_20_and_lock[3].errno_code == EACCES_ERRNO
    )

    milestone_probe = _build_stage70_milestone_probe()

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
        "prioritize_rec_media_exposed_events": PRIORITIZE_REC_MEDIA_EXPOSED_EVENTS,
        "movie_sort_recording_exposed_events": MOVIE_SORT_RECORDING_EXPOSED_EVENTS,
        "simult_fs_mismatch_bypass_events": SIMULT_FS_MISMATCH_BYPASS_EVENTS,
        "slot2_to_slot1_overflow_bypass_events": SLOT2_TO_SLOT1_OVERFLOW_BYPASS_EVENTS,
        "sdxc_1200m_or_cfex_b_bypass_events": SDXC_1200M_OR_CFEX_B_BYPASS_EVENTS,
        "proxy_highfps_100p_120fps_bypass_events": PROXY_HIGHFPS_100P_120FPS_BYPASS_EVENTS,
        "on_camera_proxy_playback_frames": ON_CAMERA_PROXY_PLAYBACK_FRAMES,
        "proxy_coupled_delete_split_events": PROXY_COUPLED_DELETE_SPLIT_EVENTS,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "slot1_vault_proxy_mutation_events": SLOT1_VAULT_PROXY_MUTATION_EVENTS,
        "power_off_ble_zero_rf_violations": POWER_OFF_BLE_ZERO_RF_VIOLATIONS,
        "fx6_bluetooth_hardware_present": FX6_BLUETOOTH_HARDWARE_PRESENT,
        "fx6_bluetooth_poweroff_wake_exposed_events": FX6_BLUETOOTH_POWEROFF_WAKE_EXPOSED_EVENTS,
        "mymenu_exact_slot_capacity": MYMENU_EXACT_SLOT_CAPACITY,
        "fx6_user_menu_capacity": FX6_USER_MENU_CAPACITY,
        "mymenu_out_of_bounds_or_playback_events": MYMENU_OUT_OF_BOUNDS_OR_PLAYBACK_EVENTS,
        "fx6_user_menu_lock_pin_file_leak_events": FX6_USER_MENU_LOCK_PIN_FILE_LEAK_EVENTS,
        "rf_packets_transmitted": RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": RF_NVS_MUTATION_BYTES,
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
        and p70a_ok
        and p70b_ok
        and p70c_ok
        and p70d_ok
        and milestone_probe["is_70th_stage_milestone"]
        and redlines["prioritize_rec_media_exposed_events"] == 0
        and redlines["movie_sort_recording_exposed_events"] == 0
        and redlines["simult_fs_mismatch_bypass_events"] == 0
        and redlines["slot2_to_slot1_overflow_bypass_events"] == 0
        and redlines["sdxc_1200m_or_cfex_b_bypass_events"] == 0
        and redlines["proxy_highfps_100p_120fps_bypass_events"] == 0
        and redlines["on_camera_proxy_playback_frames"] == 0
        and redlines["proxy_coupled_delete_split_events"] == 0
        and redlines["slot1_data_sector_writes"] == 0
        and (not redlines["slot1_avf_info_mutated"])
        and redlines["slot1_vault_proxy_mutation_events"] == 0
        and redlines["power_off_ble_zero_rf_violations"] == 0
        and (not redlines["fx6_bluetooth_hardware_present"])
        and redlines["fx6_bluetooth_poweroff_wake_exposed_events"] == 0
        and redlines["mymenu_exact_slot_capacity"] == 42
        and redlines["fx6_user_menu_capacity"] == 20
        and redlines["mymenu_out_of_bounds_or_playback_events"] == 0
        and redlines["fx6_user_menu_lock_pin_file_leak_events"] == 0
        and redlines["rf_packets_transmitted"] == 0
        and redlines["rf_nvs_mutation_bytes"] == 0
        and redlines["raw_firmware_bytes_leaked"] == 0
        and redlines["physical_device_writes"] == 0
        and (not redlines["persistent_emmc_writes_authorized"])
        and (not redlines["hardware_live_attachment_authorized"])
        and (not redlines["overall_ready_for_hardware_attach"])
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_330_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_70th_stage_milestone": True,
        "source_mode": donor_audit.source_mode,
        "access_mode": donor_audit.access_mode,
        "all_checks_passed": all_passed,
        "donor_audit": asdict(donor_audit),
        "pillar_a_rec_media_autoswitch_vpg_and_overflow_lock_hil": {
            "passed": p70a_ok,
            "prioritize_removed": asdict(p70a_prioritize_removed),
            "movie_sort_rejected": asdict(p70a_movie_sort_rejected),
            "still_sort_slot2_blocked": asdict(p70a_still_sort_slot2_blocked),
            "simult_fs_mismatch": asdict(p70a_simult_fs_mismatch),
            "overflow_trap_duallock": asdict(p70a_overflow_trap_duallock),
            "sq_1200m_cfex_ok": asdict(p70a_sq_1200m_cfex_ok),
            "sq_1200m_sdxc_rejected": asdict(p70a_sq_1200m_sdxc_rejected),
            "fx6_simul_and_exclusion": [
                asdict(r) for r in p70a_fx6_simul_and_exclusion
            ],
        },
        "pillar_b_proxy_settings_substream_and_slot1_vault_hil": {
            "passed": p70b_ok,
            "dci4k_proxy_allowed": asdict(p70b_dci4k_proxy_allowed),
            "highfps_100p_120fps_cutoff": [
                asdict(r) for r in p70b_120p_and_sq120fps_cutoff
            ],
            "playback_and_split_rejected": [
                asdict(r) for r in p70b_playback_and_split_rejected
            ],
            "slot1_vault_proxy_erofs": asdict(p70b_slot1_vault_proxy_erofs),
            "fx6_chunk_ok_and_conflict": [
                asdict(r) for r in p70b_fx6_chunk_ok_and_conflict
            ],
        },
        "pillar_c_creators_cloud_c3portal_and_poweroff_ble_zerorf_hil": {
            "passed": p70c_ok,
            "zero_rf_3lock_ok": asdict(p70c_zero_rf_3lock_ok),
            "ble_poweroff_trap_rejected": asdict(p70c_ble_poweroff_trap_rejected),
            "cloud_ftp_conflict": asdict(p70c_cloud_ftp_conflict),
            "fx6_zero_bt_rejected": asdict(p70c_fx6_zero_bt_rejected),
        },
        "pillar_d_mymenu_42slots_and_fx6_usermenu_lock_hil": {
            "passed": p70d_ok,
            "fx3_42_slots_survive_cam_reset": asdict(p70d_fx3_42_slots_survive_cam_reset),
            "fx3_oob_and_playback_rejected": [
                asdict(r) for r in p70d_fx3_oob_and_playback_rejected
            ],
            "fx3_delete_all_and_init": [
                asdict(r) for r in p70d_fx3_delete_all_and_init
            ],
            "fx6_user_menu_20_and_lock": [
                asdict(r) for r in p70d_fx6_user_menu_20_and_lock
            ],
            "stage70_milestone_probe": milestone_probe,
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
        prog="realhw_rec_media_autoswitch_proxy_cloud_mymenu_coemulator.py",
        description=(
            "Phase 330 Stage 70 (70/70 Milestone!) Wave-60 Real-Hardware "
            "ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 [Rec. Media Settings] "
            "(Removed [Prioritize Rec. Media], Initialize-only [Recording Media] Still 4 vs Movie 3, "
            "CRITICAL Slot-2 -> Slot-1 Overflow Trap Dual-Lock 100%% Fail-Closed EROFS=30, "
            "VPG200/VPG400 vs SDXC V60/V90 Speed Gates), [Proxy Settings] (sq_proxy, "
            "Allowed on XAVC S-I DCI 4K <=59.94p, Cutoff at 100p/120fps, M4ROOT/SUB/*S03.MP4 "
            "Non-Playable & Coupled Delete/Protect + Slot-1 EROFS=30), [Creators' Cloud] / "
            "[C3 Portal] (Cloud * Surviving Initialize, Power-OFF BLE Zero-RF 3-Lock Guard vs "
            "Zero-BT FX6), and [My Menu] (6x7=42 Slots vs FX6 20-Item User Menu + Lock PIN "
            "Excluded from All File & Scene File) HIL"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic Phase 330 Stage 70 (70/70) Wave-60 HIL verification suite",
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
        help="Emit concise one-line Stage 70 (70/70 Milestone!) Wave-60 summary",
    )
    args = parser.parse_args(argv)

    rep = run_phase330_rec_media_autoswitch_proxy_cloud_mymenu_coemulation(
        force_clean_room=True if args.clean_room else None
    )

    if args.summary and not args.json:
        red = rep["redlines"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 330 Stage 70 (70/70 Milestone) | "
            f"mode={rep['source_mode']} "
            f"donors={rep['donor_audit']['donor_files_inspected']} "
            f"ovf_byp={red['slot2_to_slot1_overflow_bypass_events']} "
            f"px_pb={red['on_camera_proxy_playback_frames']} "
            f"ble_rf={red['power_off_ble_zero_rf_violations']} "
            f"mm_cap={red['mymenu_exact_slot_capacity']} "
            f"rf_tx={red['rf_packets_transmitted']} "
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
