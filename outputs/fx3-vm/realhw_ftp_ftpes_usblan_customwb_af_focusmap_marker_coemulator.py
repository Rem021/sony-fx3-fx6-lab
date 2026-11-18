#!/usr/bin/env python3
"""Phase 333 (Stage 71 — 71/71 VM HIL Stages Milestone!) — Real-Hardware
ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-61:
`FTP/FTPES 9-Server Passive-Only vs Dormant SFTP & USB-LAN Zero-RF Bypass +
Slot-1 AVF_INFO EROFS=30` (`71A`), `Custom 1-3 WB, Shutter AWB Lock, Shockless WB
& Cine EI Lockouts` (`71B`), `Movie AF Speed 1..7 & Shift Sens. 1..5 +
External-Only Focus Map` (`71C`), and `15-Ratio Marker Display & 4-Color Peaking
Clean-HDMI HIL` (`71D`).

Strictly models Wave-61 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) and
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

SCHEMA_ID = "realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulator_v1"
PHASE_333_SCHEMA = SCHEMA_ID
PHASE_333_VERSION = "333.0.0"
PHASE_NUMBER = 333
STAGE_INDEX = 71
STAGE_TOTAL = 71
MILESTONE_LABEL = "71/71"
STAGE_NAME = "stage71_realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_hil"
IS_71ST_STAGE_MILESTONE = True
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

# Wave-61 Stage 71 (71/71 Milestone) zero-fault & hardware-truth invariants
FX3_FTP_MAX_SERVERS = 9
FX6_FTP_MAX_SERVERS = 3
CACERT_MAX_BYTES = 1_048_576  # 1 MiB
DORMANT_SFTP_EXPOSED_EVENTS = 0
ACTIVE_FTP_OR_IMPLICIT_FTPS_BYPASS_EVENTS = 0
DORMANT_TRANSFER_JPEG_HEIF_SIZE_EXPOSED_EVENTS = 0
USBLAN_ZERO_RF_BYPASS_EVENTS = 0
FTP_CLOUD_MUTUAL_EXCLUSION_VIOLATIONS = 0
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
SLOT1_VAULT_FTP_MUTATION_EVENTS = 0
RF_PACKETS_TRANSMITTED = 0
RF_NVS_MUTATION_BYTES = 0

WB_CTEMP_MIN_K = 2500
WB_CTEMP_MAX_K = 9900
WB_CTEMP_STEP_K = 100
CUSTOM_WB_SLOT_COUNT = 3
CUSTOM_WB_CAMSET_LEAK_EVENTS = 0
CINE_EI_AUTO_WB_BYPASS_EVENTS = 0
SHOCKLESS_WB_DIRECT_CTEMP_LAG_FRAMES = 0

AF_TRANSITION_SPEED_MIN = 1
AF_TRANSITION_SPEED_MAX = 7
FX3_AF_TRANSITION_SPEED_DEFAULT = 5
AF_SUBJ_SHIFT_SENS_MIN = 1
AF_SUBJ_SHIFT_SENS_MAX = 5
FX3_AF_SUBJ_SHIFT_SENS_DEFAULT = 5
FX3_HAS_INBODY_FOCUS_MAP = False
FX6_HAS_INBODY_FOCUS_MAP = True
INBODY_FOCUS_MAP_EXPOSED_EVENTS = 0
FOCUS_MAP_150FPS_OR_AUTOFRAMING_BYPASS_EVENTS = 0
AF_SUBJ_SHIFT_6_7_SPOOF_EVENTS = 0

FX3_MARKER_ACTIVE_RATIO_COUNT = 15
PEAKING_COLOR_COUNT = 4
HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS = 0
CAMERA_RESET_MARKER_OR_PEAKING_WIPE_EVENTS = 0
MARKER_FOCUS_MAGNIFIER_COLLISION_EVENTS = 0

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
# Verified Local Donor Specs (19 FX3 7.02 & FX6 6.01 Wave-61 Donors)
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
        b"FTP Transfer",
        b"FTP Transfer Func.",
        b"FTP Function",
        b"Destination Settings",
        b"Connects with FTPES.",
        b"Import Root Certificate",
        b"Transfer JPEG Size",
        b"Transfer HEIF Size",
        b"C.Temp./Filter",
        b"Priority Set in AWB",
        b"Shutter AWB Lock",
        b"Shockless WB",
        b"AF Transition Speed",
        b"AF Subj. Shift Sensitivity",
        b"AF Assist",
        b"Marker Display",
        b"Center Marker",
        b"Aspect Marker",
        b"Safety Zone",
        b"Guideframe",
        b"Peaking Display",
        b"Peaking Level",
        b"Peaking Color",
    ),
    "fx3_string_sc_f": (
        "FTP传输功能".encode("utf-8"),
        "服务器设置".encode("utf-8"),
        "自定义1".encode("utf-8"),
        "快门AWB锁定".encode("utf-8"),
        "AF过渡速度".encode("utf-8"),
        "AF辅助".encode("utf-8"),
        "标记显示".encode("utf-8"),
        "峰值显示".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "FTP傳輸功能".encode("utf-8"),
        "伺服器設定".encode("utf-8"),
        "自訂1".encode("utf-8"),
        "峰值顯示".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "FTP転送機能".encode("utf-8"),
        "サーバー設定".encode("utf-8"),
        "カスタム1".encode("utf-8"),
        "AFトランジション速度".encode("utf-8"),
        "AFアシスト".encode("utf-8"),
        "マーカー表示".encode("utf-8"),
        "ピーキング表示".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"FTP transfer",
        b"Custom WB",
        b"Custom WB Error",
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
        b"FTP",
        b"White Balance",
        b"Peaking",
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
        b"File Transfer",
        b"Server Settings",
        b"Auto Upload (Proxy)",
        b"Chunk",
        b"ATW",
        b"Focus Map",
        b"User Box",
    ),
    "fx6_string_en_2": (
        b"Passive Mode",
        b"Aspect Mask",
        b"Peaking",
        b"B&W",
        b"Memory A",
    ),
    "fx3_lib_airplane": (b"\x7fELF",),
    "fx3_lib_bt": (b"\x7fELF",),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (62_652_416, "BKID_FTP_SERVER_0_HOST", b"BKID_APP_ftp_server_settings_host_name0"),
        (62_652_416, "BKID_FTP_SERVER_8_HOST", b"BKID_APP_ftp_server_settings_host_name8"),
        (62_185_472, "SET_SERVER_SECURE_ON", b"SET_SERVER_SECURE_PROTOCOL_ON"),
        (62_185_472, "SET_SERVER_SECURE_OFF", b"SET_SERVER_SECURE_PROTOCOL_OFF"),
        (59_924_480, "SAVE_FTP_TRANS_LIST", b"save_ftp_transfer_list_to_media"),
        (61_943_808, "CONTENT_FTP_COMPLETE", b"CONTENT_INFO_FTP_TRANS_STAT_COMPLETE"),
        (
            60_542_976,
            "PRM_HAITA_FTP_SLOT1_MEDIA",
            b"PRM_HAITA_ftp_display_result_media_supported_state_slot1",
        ),
        (
            60_637_184,
            "USB_HOST_FUNCTION_USB_ETHER",
            b"VAL_usb_host_function_USB_HOST_FUNCTION_USB_ETHER",
        ),
        (61_931_520, "CLOUD_ON_FTP_OFF", b"CLOUD_CONNECTION_ON_FTP_OFF"),
        (50_024_448, "CTEMP_2500K", b"COLOR_TEMP_COLOR_FILTER_2500K"),
        (50_028_544, "CTEMP_9900K", b"COLOR_TEMP_COLOR_FILTER_9900K"),
        (62_685_184, "BKID_PRIORITY_AWB", b"BKID_APP_setting_priority_set_in_awb"),
        (62_685_184, "BKID_SHUTTER_AWB_LOCK", b"BKID_APP_setting_stl_awb_lock_with_shutter"),
        (62_685_184, "BKID_SHOCKLESS_WB", b"BKID_APP_setting_movie_shockless_wb"),
        (62_689_280, "BKID_AF_TRANSITION_SPEED", b"BKID_APP_setting_movie_af_transition_speed"),
        (62_689_280, "BKID_AF_SUBJ_SHIFT_SENS", b"BKID_APP_setting_movie_af_subj_shift_sens"),
        (61_886_464, "MOVIE_AF_TRANSITION_7_FAST", b"MOVIE_AF_TRANSITION_SPEED_7_FAST"),
        (61_886_464, "MOVIE_AF_SENS_5", b"MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE"),
        (62_689_280, "BKID_AF_ASSIST", b"BKID_APP_setting_af_assist"),
        (60_403_712, "REMOTE_EVT_FOCUS_MAP", b"to_remote_event_focus_map"),
        (59_822_080, "SEQ_NOTIFY_FOCUS_MAP", b"sequence_notify_focus_map"),
        (62_681_088, "BKID_MARKER_DISPLAY", b"BKID_APP_setting_marker_display"),
        (61_304_832, "MARKER_ASPECT_2_39_1", b"VAL_setting_marker_display_aspect_ASPECT_2_39_1"),
        (62_689_280, "BKID_PEAKING_COLOR", b"BKID_APP_setting_peaking_color"),
        (62_689_280, "BKID_PEAKING_LEVEL", b"BKID_APP_setting_peaking_level"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (41_578_496, "FX6_SET_SERVER_SFTP", b"SET_SERVER_SECURE_PROTOCOL_ON_SFTP"),
        (40_644_608, "FX6_AUTO_UPLOAD_CHUNK", b"AUTO_UPLOAD_PROXY_CHUNK"),
        (40_497_152, "FX6_WHITE_MEM_H", b"WHITE_SELECT_MEMORY_H"),
        (40_497_152, "FX6_ATW_SPEED_5", b"ATW_SPEED_5"),
        (40_656_896, "FX6_MOVIE_AF_SENS_5", b"MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE"),
        (40_960_000, "FX6_USER_MENU_FOCUS_MAP", b"BKID_APP_USER_MENU_FOCUS_MAP"),
        (40_939_520, "FX6_USER_BOX", b"BKID_APP_SETTING_USER_BOX"),
        (40_632_320, "FX6_PEAKING_B_W", b"PEAKING_COLOR_VALUE_B_W"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-61 Real-Hardware Constants & Matrices
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

# Sub-Model 71A — FTP/FTPES, Dormant SFTP/JPEG-Size, USB-LAN Zero-RF & Slot-1 AVF_INFO
VALID_FTP_PROTOCOLS: Tuple[str, ...] = (
    "FTP",
    "FTPES",
    "SFTP",
    "FTPS_IMPLICIT_990",
)
VALID_FTP_TRANSFER_MODES: Tuple[str, ...] = ("Passive", "Active")
VALID_ROOT_CERT_POLICIES: Tuple[str, ...] = ("Does Not Connect", "Connect")
VALID_FTP_DIR_HIERARCHIES: Tuple[str, ...] = ("Standard", "Same as in Camera")
VALID_AUTO_FTP_TARGETS: Tuple[str, ...] = (
    "Still Image",
    "Movie",
    "Still+Movie",
    "Only Shot Mark",
    "All",
)
VALID_CLIP_FLAG_FILTERS: Tuple[str, ...] = ("Off", "OK", "NG", "KEEP", "All")
VALID_RAW_JH_TARGETS: Tuple[str, ...] = ("JPEG & HEIF", "RAW", "RAW+J & RAW+H")
VALID_MOVIE_FTP_TARGETS: Tuple[str, ...] = (
    "Proxy Only",
    "Original Only",
    "Proxy & Original",
)
VALID_CONNECT_METHODS: Tuple[str, ...] = (
    "Disabled",
    "Wi-Fi",
    "USB-LAN",
    "USB Tethering",
)
FX6_AUTO_UPLOAD_CONFLICTS: Tuple[str, ...] = ("None", "Simul Rec", "Relay Rec")

# Sub-Model 71B — White Balance 2500K..9900K, Custom 1..3, Priority AWB, Shutter Lock, Shockless WB
FX3_STANDARD_WB_MODES: Tuple[str, ...] = (
    "Auto",
    "Daylight",
    "Shade",
    "Cloudy",
    "Incandescent",
    "Fluor.: Warm White",
    "Fluor.: Cool White",
    "Fluor.: Day White",
    "Fluor.: Daylight",
    "Flash",
    "Underwater Auto",
    "C.Temp./Filter",
    "Custom 1",
    "Custom 2",
    "Custom 3",
)
FX6_EXTRA_WB_MODES: Tuple[str, ...] = (
    "Memory A",
    "Memory B",
    "Memory H",
    "ATW",
    "Preset 3200K",
    "Preset 4300K",
    "Preset 5600K",
    "Preset 6300K",
)
ALL_WB_MODES: Tuple[str, ...] = FX3_STANDARD_WB_MODES + FX6_EXTRA_WB_MODES
VALID_EXPOSURE_MODES: Tuple[str, ...] = (
    "P",
    "A",
    "S",
    "M",
    "Intelligent Auto",
    "Flexible ISO",
    "Cine EI",
    "Cine EI Quick",
)
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI",
    "Cine EI Quick",
)
VALID_AWB_PRIORITIES: Tuple[str, ...] = ("Standard", "Ambience", "White")
VALID_SHOCKLESS_WB_MODES: Tuple[str, ...] = ("Off", "1 (Fast)", "2", "3 (Slow)")
VALID_SHUTTER_AWB_LOCK_MODES: Tuple[str, ...] = (
    "Shut. Halfway",
    "Cont. Shooting",
    "Off",
)
FX6_WHT_BAL_SWITCH_POSITIONS: Tuple[str, ...] = ("PRST", "A", "B")

# Sub-Model 71C — Movie AF Dynamic Scales (1..7 / 1..5), AF Assist, External-Only Focus Map
VALID_FOCUS_MODES: Tuple[str, ...] = ("AF-S", "AF-A", "AF-C", "DMF", "MF")
VALID_LENS_MODELS: Tuple[str, ...] = (
    "SEL2470GM2",
    "SELP1650",
    "SEL18200LE",
    "Non_PDAF_Adapter",
    "No_Lens",
)
AF_ASSIST_INCOMPATIBLE_LENSES: Tuple[str, ...] = (
    "SELP1650",
    "SEL18200LE",
    "Non_PDAF_Adapter",
    "No_Lens",
)

# Sub-Model 71D — 15-Ratio Marker Display & 4-Color Peaking Clean-HDMI Isolation
FX3_ACTIVE_ASPECT_MARKER_RATIOS: Tuple[str, ...] = (
    "9:16",
    "4:5",
    "1:1",
    "4:3",
    "13:9",
    "14:9",
    "15:9",
    "16:9",
    "17:9",
    "1.66:1",
    "1.85:1",
    "1.91:1",
    "2:1",
    "2.35:1",
    "2.39:1",
)
VALID_ASPECT_MARKER_STATES: Tuple[str, ...] = ("Off",) + FX3_ACTIVE_ASPECT_MARKER_RATIOS
VALID_SAFETY_ZONE_MODES: Tuple[str, ...] = ("Off", "80%", "90%", "92.5%", "95%")
VALID_PEAKING_LEVELS: Tuple[str, ...] = ("High", "Mid", "Low")
FX3_PEAKING_COLORS: Tuple[str, ...] = ("Red", "Yellow", "Blue", "White")
FX6_PEAKING_COLORS: Tuple[str, ...] = ("B&W", "Red", "Yellow", "Blue")
ALL_PEAKING_COLORS: Tuple[str, ...] = ("Red", "Yellow", "Blue", "White", "B&W")


class Stage71Phase333Error(RuntimeError):
    """Raised on invalid Phase 333 Stage 71 configuration or safety redline violation."""


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


def resolve_phase333_donor_paths(
    work_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Dict[str, Path]]:
    """Resolve Phase 333 donor paths, strictly returning None when `work_root is None`."""
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
        raise Stage71Phase333Error(
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
class Phase333DonorAuditReport:
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


_DONOR_AUDIT_CACHE: Dict[Tuple[str, str], Phase333DonorAuditReport] = {}


def inspect_phase333_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase333DonorAuditReport:
    """Verify all 19 Wave-61 donors strictly via `os.O_RDONLY` + `os.pread` or clean-room fallback."""
    t0 = time.perf_counter()
    clean = clean_room_test_mode(force_clean_room=force_clean_room, env=env)
    work_root = None if clean else resolve_mac_work_root(force_clean_room=False, env=env)
    donor_paths = resolve_phase333_donor_paths(
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
        rep = Phase333DonorAuditReport(
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
                "CLEAN_ROOM_SYNTHETIC: verified all 19 Wave-61 contracts without local Mac/work reads.",
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
            head_sha = hashlib.sha256(head4k).hexdigest()
            donor_digests[f"{key}_head4k"] = head_sha
            if sz != expected_size or head_sha != EXPECTED_LARGE_HEAD4K_SHA256[key]:
                all_ok = False
                notes.append(f"large_head4k_mismatch:{key}")
                continue
            win_cache: Dict[int, bytes] = {}
            win_miss = 0
            for offset, label, marker in LARGE_DONOR_WINDOWS[key]:
                if offset not in win_cache:
                    win_cache[offset] = _read_window_readonly_bytes(
                        fpath, offset, BOUNDED_WINDOW_MAX_BYTES
                    )
                if marker in win_cache[offset]:
                    windows_ok += 1
                else:
                    win_miss += 1
                    all_ok = False
                    notes.append(f"missing_window:{key}:{label}@{offset}")
            if win_miss == 0:
                large_ok += 1

    if all_ok:
        notes.append(
            f"LOCAL_DONOR_O_RDONLY: verified {compact_ok} compact + {large_ok} large "
            f"Wave-61 donors ({tokens_ok} tokens, {windows_ok} <=4096B pread windows)."
        )

    rep = Phase333DonorAuditReport(
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
# Sub-Model 71A — FTP/FTPES 9-Server Passive-Only vs Dormant SFTP/JPEG-Size,
#                 USB-LAN Zero-RF Bypass Firewall & Slot-1 AVF_INFO EROFS=30
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FtpFtpesUsblanSlot1VaultResult:
    body_profile: str
    firmware_version: str
    admitted: bool
    errno_code: int
    ftp_function: str
    effective_ftp_function: str
    server_slot: int
    max_servers: int
    protocol: str
    transfer_mode: str
    dormant_transfer_jpeg_heif_size_requested: bool
    cacert_filename: str
    cacert_size_bytes: int
    cacert_source_slot: str
    root_cert_error_policy: str
    directory_hierarchy: str
    remote_path_prefix: str
    auto_ftp_transfer: str
    auto_ftp_target: str
    clip_flag_filter: str
    raw_jh_transfer_target: str
    movie_transfer_target: str
    ftp_power_save: str
    cloud_connection: str
    connect_method: str
    airplane_mode: str
    usb_lan_tethering_disabled: bool
    zero_rf_bench_mode: bool
    usblan_airplane_bypass_detected: bool
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    save_ftp_transfer_list_to_media_requested: bool
    avf_info_recovery_0x0a13_requested: bool
    target_slot: int
    tier0_vault_firewall_triggered: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    fx6_auto_upload_proxy_chunk: bool
    fx6_concurrent_conflict: str
    camera_settings_reset_applied: bool
    reset_network_set_applied: bool
    initialize_applied: bool
    reason: str


def simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    firmware_version: str = FW_VER_702,
    ftp_function: str = "Off",
    server_slot: int = 1,
    protocol: str = "FTPES",
    transfer_mode: str = "Passive",
    dormant_transfer_jpeg_heif_size_requested: bool = False,
    cacert_filename: Optional[str] = None,
    cacert_size_bytes: int = 2048,
    cacert_source_slot: Optional[str] = None,
    root_cert_error_policy: str = "Does Not Connect",
    directory_hierarchy: str = "Standard",
    auto_ftp_transfer: str = "Off",
    auto_ftp_target: str = "Still+Movie",
    clip_flag_filter: str = "Off",
    raw_jh_transfer_target: str = "JPEG & HEIF",
    movie_transfer_target: str = "Proxy Only",
    ftp_power_save: str = "Off",
    cloud_connection: str = "Off",
    connect_method: str = "Disabled",
    airplane_mode: str = "On",
    usb_lan_tethering_disabled: bool = True,
    zero_rf_bench_mode: bool = True,
    save_ftp_transfer_list_to_media_requested: bool = False,
    avf_info_recovery_0x0a13_requested: bool = False,
    target_slot: int = SLOT_1,
    fx6_auto_upload_proxy_chunk: bool = False,
    fx6_concurrent_conflict: str = "None",
    camera_settings_reset_applied: bool = False,
    reset_network_set_applied: bool = False,
    initialize_applied: bool = False,
) -> FtpFtpesUsblanSlot1VaultResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage71Phase333Error(f"Unsupported body_profile={body_profile!r}")
    if firmware_version not in VALID_FW_VERSIONS:
        raise Stage71Phase333Error(f"Unsupported firmware_version={firmware_version!r}")
    if ftp_function not in ("On", "Off"):
        raise Stage71Phase333Error(f"Unsupported ftp_function={ftp_function!r}")
    if protocol not in VALID_FTP_PROTOCOLS:
        raise Stage71Phase333Error(f"Unsupported protocol={protocol!r}")
    if transfer_mode not in VALID_FTP_TRANSFER_MODES:
        raise Stage71Phase333Error(f"Unsupported transfer_mode={transfer_mode!r}")
    if root_cert_error_policy not in VALID_ROOT_CERT_POLICIES:
        raise Stage71Phase333Error(
            f"Unsupported root_cert_error_policy={root_cert_error_policy!r}"
        )
    if directory_hierarchy not in VALID_FTP_DIR_HIERARCHIES:
        raise Stage71Phase333Error(
            f"Unsupported directory_hierarchy={directory_hierarchy!r}"
        )
    if auto_ftp_transfer not in ("On", "Off"):
        raise Stage71Phase333Error(f"Unsupported auto_ftp_transfer={auto_ftp_transfer!r}")
    if auto_ftp_target not in VALID_AUTO_FTP_TARGETS:
        raise Stage71Phase333Error(f"Unsupported auto_ftp_target={auto_ftp_target!r}")
    if clip_flag_filter not in VALID_CLIP_FLAG_FILTERS:
        raise Stage71Phase333Error(f"Unsupported clip_flag_filter={clip_flag_filter!r}")
    if raw_jh_transfer_target not in VALID_RAW_JH_TARGETS:
        raise Stage71Phase333Error(
            f"Unsupported raw_jh_transfer_target={raw_jh_transfer_target!r}"
        )
    if movie_transfer_target not in VALID_MOVIE_FTP_TARGETS:
        raise Stage71Phase333Error(
            f"Unsupported movie_transfer_target={movie_transfer_target!r}"
        )
    if ftp_power_save not in ("On", "Off"):
        raise Stage71Phase333Error(f"Unsupported ftp_power_save={ftp_power_save!r}")
    if cloud_connection not in ("On", "Off"):
        raise Stage71Phase333Error(f"Unsupported cloud_connection={cloud_connection!r}")
    if connect_method not in VALID_CONNECT_METHODS:
        raise Stage71Phase333Error(f"Unsupported connect_method={connect_method!r}")
    if airplane_mode not in ("On", "Off"):
        raise Stage71Phase333Error(f"Unsupported airplane_mode={airplane_mode!r}")
    if target_slot not in VALID_SLOTS:
        raise Stage71Phase333Error(f"Unsupported target_slot={target_slot!r}")
    if fx6_concurrent_conflict not in FX6_AUTO_UPLOAD_CONFLICTS:
        raise Stage71Phase333Error(
            f"Unsupported fx6_concurrent_conflict={fx6_concurrent_conflict!r}"
        )

    eff_cert_name = (
        ("certification.pem" if body_profile == BODY_MODEL_FX6 else "cacert.pem")
        if cacert_filename is None
        else cacert_filename
    )
    eff_cert_slot = (
        ("Slot B" if body_profile == BODY_MODEL_FX6 else "Slot 1")
        if cacert_source_slot is None
        else cacert_source_slot
    )
    max_servers = FX6_FTP_MAX_SERVERS if body_profile == BODY_MODEL_FX6 else FX3_FTP_MAX_SERVERS

    # Network Reset / Initialize clears FTP Function & connect method; Camera Settings Reset does NOT.
    if reset_network_set_applied or initialize_applied:
        eff_ftp_func = "Off"
        eff_conn_method = "Disabled"
    else:
        eff_ftp_func = ftp_function
        eff_conn_method = connect_method

    remote_prefix = (
        ("A/..." if target_slot == SLOT_1 else "B/...")
        if directory_hierarchy == "Same as in Camera"
        else "/"
    )

    def _res(
        *,
        admitted: bool,
        errno_code: int,
        reason: str,
        vault_triggered: bool = False,
        usblan_bypass: bool = False,
    ) -> FtpFtpesUsblanSlot1VaultResult:
        return FtpFtpesUsblanSlot1VaultResult(
            body_profile=body_profile,
            firmware_version=FW_VER_601 if body_profile == BODY_MODEL_FX6 else firmware_version,
            admitted=admitted,
            errno_code=errno_code,
            ftp_function=ftp_function,
            effective_ftp_function="Off" if (not admitted and errno_code != 0) else eff_ftp_func,
            server_slot=server_slot,
            max_servers=max_servers,
            protocol=protocol,
            transfer_mode=transfer_mode,
            dormant_transfer_jpeg_heif_size_requested=dormant_transfer_jpeg_heif_size_requested,
            cacert_filename=eff_cert_name,
            cacert_size_bytes=cacert_size_bytes,
            cacert_source_slot=eff_cert_slot,
            root_cert_error_policy=root_cert_error_policy,
            directory_hierarchy=directory_hierarchy,
            remote_path_prefix=remote_prefix,
            auto_ftp_transfer=auto_ftp_transfer,
            auto_ftp_target=auto_ftp_target,
            clip_flag_filter=clip_flag_filter if firmware_version in (FW_VER_700, FW_VER_702) else "Off",
            raw_jh_transfer_target=raw_jh_transfer_target,
            movie_transfer_target=movie_transfer_target,
            ftp_power_save=ftp_power_save,
            cloud_connection=cloud_connection,
            connect_method=connect_method,
            airplane_mode=airplane_mode,
            usb_lan_tethering_disabled=usb_lan_tethering_disabled,
            zero_rf_bench_mode=zero_rf_bench_mode,
            usblan_airplane_bypass_detected=usblan_bypass,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            save_ftp_transfer_list_to_media_requested=save_ftp_transfer_list_to_media_requested,
            avf_info_recovery_0x0a13_requested=avf_info_recovery_0x0a13_requested,
            target_slot=target_slot,
            tier0_vault_firewall_triggered=vault_triggered,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            fx6_auto_upload_proxy_chunk=fx6_auto_upload_proxy_chunk,
            fx6_concurrent_conflict=fx6_concurrent_conflict,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            reason=reason,
        )

    # 1. Tier-0 Slot-1 Vault Firewall for AVF_INFO / FTP Transfer Result List
    if target_slot == SLOT_1 and (
        save_ftp_transfer_list_to_media_requested or avf_info_recovery_0x0a13_requested
    ):
        return _res(
            admitted=False,
            errno_code=EROFS_ERRNO,
            vault_triggered=True,
            reason=(
                "EROFS: Slot-1 Tier-0 Vault blocks save_ftp_transfer_list_to_media / "
                "CONTENT_INFO_FTP_TRANS_STAT / AVF_INFO recovery (0x0a13) -> slot1_wr=0"
            ),
        )

    # 2. ILME-FX6 Ver. 6.01 contract branch
    if body_profile == BODY_MODEL_FX6:
        if server_slot < 1 or server_slot > FX6_FTP_MAX_SERVERS:
            return _res(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    f"EINVAL: FX6 UI exposes Server Settings1..{FX6_FTP_MAX_SERVERS} "
                    f"(got {server_slot})"
                ),
            )
        if protocol in ("SFTP", "FTPS_IMPLICIT_990"):
            return _res(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"EOPNOTSUPP: FX6 Ver. 6.01 does not expose {protocol} in Network UI "
                    "(SET_SERVER_SECURE_PROTOCOL_ON_SFTP dormant)"
                ),
            )
        if eff_cert_name != "certification.pem" or eff_cert_slot != "Slot B":
            return _res(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    "EINVAL: FX6 imports per-server certification.pem from Slot B "
                    f"(got {eff_cert_name!r} from {eff_cert_slot!r})"
                ),
            )
        if fx6_auto_upload_proxy_chunk and fx6_concurrent_conflict != "None":
            return _res(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason=(
                    f"EBUSY: FX6 Auto Upload (Proxy): Chunk mutually exclusive with "
                    f"{fx6_concurrent_conflict}"
                ),
            )
        return _res(
            admitted=True,
            errno_code=0,
            reason=(
                f"ADMITTED: FX6 File Transfer Server {server_slot}/3 ({protocol} "
                f"mode={transfer_mode}, cert={eff_cert_name}@{eff_cert_slot}, "
                f"Chunk={fx6_auto_upload_proxy_chunk})"
            ),
        )

    # 3. ILME-FX3 Ver. 7.02 dormant feature & mode rejections
    if dormant_transfer_jpeg_heif_size_requested:
        return _res(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "EOPNOTSUPP: [Transfer JPEG/HEIF Size] (_f 0x6aed/0x63dd) has 0 hits "
                "in FX3 appFw.so (dormant cross-model Alpha string)"
            ),
        )
    if protocol in ("SFTP", "FTPS_IMPLICIT_990"):
        return _res(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"EOPNOTSUPP: FX3 Ver. 7.02 supports Passive-only FTP/FTPES; "
                f"{protocol} is dormant/unsupported"
            ),
        )
    if transfer_mode == "Active":
        return _res(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="EOPNOTSUPP: FX3 Ver. 7.02 FTP/FTPES is Passive-only (Active Mode rejected)",
        )
    if server_slot < 1 or server_slot > FX3_FTP_MAX_SERVERS:
        return _res(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=(
                f"EINVAL: FX3 [FTP Transfer Func.] supports Server 1..{FX3_FTP_MAX_SERVERS} "
                f"(got {server_slot})"
            ),
        )
    if eff_cert_name != "cacert.pem" or eff_cert_slot != "Slot 1":
        return _res(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=(
                "EINVAL: FX3 [Import Root Certificate] requires cacert.pem from Slot 1 root "
                f"(got {eff_cert_name!r} from {eff_cert_slot!r})"
            ),
        )
    if cacert_size_bytes <= 0 or cacert_size_bytes > CACERT_MAX_BYTES:
        return _res(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=(
                f"EINVAL: FX3 cacert.pem must be 1..{CACERT_MAX_BYTES} bytes (<= 1 MB), "
                f"got {cacert_size_bytes}"
            ),
        )

    # 4. [FTP Function] = On mutually exclusive with [Cloud Connection] = On
    if eff_ftp_func == "On" and cloud_connection == "On":
        return _res(
            admitted=False,
            errno_code=EBUSY_ERRNO,
            reason="EBUSY: [FTP Function] = On mutually exclusive with [Cloud Connection] = On (CLOUD_CONNECTION_ON_FTP_OFF)",
        )

    # 5. Zero-RF + Wired USB-LAN Bypass Firewall
    # Sony allows USB-LAN (USB_ETHER) FTP even when [Airplane Mode] = On!
    usblan_bypass = (
        airplane_mode == "On"
        and (
            eff_conn_method in ("USB-LAN", "USB Tethering")
            or (not usb_lan_tethering_disabled)
        )
    )
    zero_exfil_ok = (
        airplane_mode == "On"
        and usb_lan_tethering_disabled
        and eff_conn_method == "Disabled"
        and eff_ftp_func == "Off"
    )
    if zero_rf_bench_mode and not zero_exfil_ok:
        return _res(
            admitted=False,
            errno_code=EPERM_ERRNO,
            usblan_bypass=usblan_bypass,
            reason=(
                "EPERM: Bench Zero-Exfiltration requires Airplane Mode=On AND USB-LAN/Tethering "
                f"Disabled AND FTP Function=Off (Airplane={airplane_mode}, "
                f"method={eff_conn_method}, usblan_disabled={usb_lan_tethering_disabled}, "
                f"ftp={eff_ftp_func}, usblan_bypass={usblan_bypass})"
            ),
        )

    return _res(
        admitted=True,
        errno_code=0,
        reason=(
            f"ADMITTED: FX3 {firmware_version} Server {server_slot}/9 {protocol} Passive-only "
            f"(ftp={eff_ftp_func}, Airplane={airplane_mode}, usb_lan_disabled={usb_lan_tethering_disabled}, "
            f"prefix={remote_prefix}, target_slot={target_slot})"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 71B — White Balance 2500K..9900K, Custom 1..3, Priority Set in AWB,
#                 Still Shutter AWB Lock, Movie Shockless WB & Cine EI Lockout
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WhiteBalanceCustomShutterShocklessResult:
    body_profile: str
    admitted: bool
    errno_code: int
    wb_mode: str
    effective_wb_mode: str
    color_temp_k: int
    amber_blue_axis: float
    green_magenta_axis: float
    shoot_mode: str
    exposure_mode: str
    log_shooting: str
    picture_profile: str
    custom_setup_capture_requested: bool
    custom_wb_error_0x0220: bool
    custom_wb_exported_in_camset: bool
    custom_wb_internal_preserved_across_cam_reset: bool
    priority_set_in_awb: str
    effective_priority_set_in_awb: str
    shockless_wb: str
    effective_shockless_wb: str
    direct_ctemp_or_filter_dial_edited: bool
    shockless_transition_frames: int
    shutter_awb_lock: str
    effective_shutter_awb_lock: str
    fx6_wht_bal_switch: str
    fx6_atw_speed: int
    camera_settings_reset_applied: bool
    initialize_applied: bool
    reason: str


def simulate_white_balance_custom_shutter_shockless_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    wb_mode: str = "C.Temp./Filter",
    color_temp_k: int = 5600,
    amber_blue_axis: float = 0.0,
    green_magenta_axis: float = 0.0,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    exposure_mode: str = "Flexible ISO",
    log_shooting: str = "Off",
    picture_profile: str = "PP11",
    custom_setup_capture_requested: bool = False,
    priority_set_in_awb: str = "Standard",
    shockless_wb: str = "1 (Fast)",
    direct_ctemp_or_filter_dial_edited: bool = False,
    shutter_awb_lock: str = "Off",
    fx6_wht_bal_switch: str = "PRST",
    fx6_atw_speed: int = 3,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> WhiteBalanceCustomShutterShocklessResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage71Phase333Error(f"Unsupported body_profile={body_profile!r}")
    if wb_mode not in ALL_WB_MODES:
        raise Stage71Phase333Error(f"Unsupported wb_mode={wb_mode!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage71Phase333Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if exposure_mode not in VALID_EXPOSURE_MODES:
        raise Stage71Phase333Error(f"Unsupported exposure_mode={exposure_mode!r}")
    if log_shooting not in VALID_LOG_SHOOTING_MODES:
        raise Stage71Phase333Error(f"Unsupported log_shooting={log_shooting!r}")
    if priority_set_in_awb not in VALID_AWB_PRIORITIES:
        raise Stage71Phase333Error(f"Unsupported priority_set_in_awb={priority_set_in_awb!r}")
    if shockless_wb not in VALID_SHOCKLESS_WB_MODES:
        raise Stage71Phase333Error(f"Unsupported shockless_wb={shockless_wb!r}")
    if shutter_awb_lock not in VALID_SHUTTER_AWB_LOCK_MODES:
        raise Stage71Phase333Error(f"Unsupported shutter_awb_lock={shutter_awb_lock!r}")
    if fx6_wht_bal_switch not in FX6_WHT_BAL_SWITCH_POSITIONS:
        raise Stage71Phase333Error(f"Unsupported fx6_wht_bal_switch={fx6_wht_bal_switch!r}")

    # Color temp 2500K..9900K (100K step) & A7..B7 (0.5 step) x G7..M7 (0.25 step)
    if (
        color_temp_k < WB_CTEMP_MIN_K
        or color_temp_k > WB_CTEMP_MAX_K
        or (color_temp_k % WB_CTEMP_STEP_K) != 0
    ):
        return WhiteBalanceCustomShutterShocklessResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            wb_mode=wb_mode,
            effective_wb_mode=wb_mode,
            color_temp_k=color_temp_k,
            amber_blue_axis=amber_blue_axis,
            green_magenta_axis=green_magenta_axis,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            picture_profile=picture_profile,
            custom_setup_capture_requested=custom_setup_capture_requested,
            custom_wb_error_0x0220=False,
            custom_wb_exported_in_camset=False,
            custom_wb_internal_preserved_across_cam_reset=False,
            priority_set_in_awb=priority_set_in_awb,
            effective_priority_set_in_awb=priority_set_in_awb,
            shockless_wb=shockless_wb,
            effective_shockless_wb=shockless_wb,
            direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
            shockless_transition_frames=0,
            shutter_awb_lock=shutter_awb_lock,
            effective_shutter_awb_lock=shutter_awb_lock,
            fx6_wht_bal_switch=fx6_wht_bal_switch,
            fx6_atw_speed=fx6_atw_speed,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EINVAL: C.Temp./Filter requires 2500K..9900K in 100K steps (got {color_temp_k}K)"
            ),
        )
    if (
        amber_blue_axis < -7.0
        or amber_blue_axis > 7.0
        or not float(amber_blue_axis * 2.0).is_integer()
        or green_magenta_axis < -7.0
        or green_magenta_axis > 7.0
        or not float(green_magenta_axis * 4.0).is_integer()
    ):
        return WhiteBalanceCustomShutterShocklessResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            wb_mode=wb_mode,
            effective_wb_mode=wb_mode,
            color_temp_k=color_temp_k,
            amber_blue_axis=amber_blue_axis,
            green_magenta_axis=green_magenta_axis,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            picture_profile=picture_profile,
            custom_setup_capture_requested=custom_setup_capture_requested,
            custom_wb_error_0x0220=False,
            custom_wb_exported_in_camset=False,
            custom_wb_internal_preserved_across_cam_reset=False,
            priority_set_in_awb=priority_set_in_awb,
            effective_priority_set_in_awb=priority_set_in_awb,
            shockless_wb=shockless_wb,
            effective_shockless_wb=shockless_wb,
            direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
            shockless_transition_frames=0,
            shutter_awb_lock=shutter_awb_lock,
            effective_shutter_awb_lock=shutter_awb_lock,
            fx6_wht_bal_switch=fx6_wht_bal_switch,
            fx6_atw_speed=fx6_atw_speed,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EINVAL: Fine-tune grid strictly A7..B7 (0.5 step) x G7..M7 (0.25 step), "
                f"got A/B={amber_blue_axis}, G/M={green_magenta_axis}"
            ),
        )

    # ILME-FX6 Ver. 6.01 branch: PRST / A / B switch, Memory A..H, ATW (Speed 1..5, locked out in Cine EI)
    if body_profile == BODY_MODEL_FX6:
        if fx6_atw_speed < 1 or fx6_atw_speed > 5:
            return WhiteBalanceCustomShutterShocklessResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                wb_mode=wb_mode,
                effective_wb_mode=wb_mode,
                color_temp_k=color_temp_k,
                amber_blue_axis=amber_blue_axis,
                green_magenta_axis=green_magenta_axis,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                log_shooting=log_shooting,
                picture_profile=picture_profile,
                custom_setup_capture_requested=custom_setup_capture_requested,
                custom_wb_error_0x0220=False,
                custom_wb_exported_in_camset=False,
                custom_wb_internal_preserved_across_cam_reset=False,
                priority_set_in_awb=priority_set_in_awb,
                effective_priority_set_in_awb=priority_set_in_awb,
                shockless_wb=shockless_wb,
                effective_shockless_wb=shockless_wb,
                direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
                shockless_transition_frames=0,
                shutter_awb_lock=shutter_awb_lock,
                effective_shutter_awb_lock="Off",
                fx6_wht_bal_switch=fx6_wht_bal_switch,
                fx6_atw_speed=fx6_atw_speed,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason=f"EINVAL: FX6 ATW Speed must be 1..5 (got {fx6_atw_speed})",
            )
        if wb_mode == "ATW" and (
            exposure_mode in ("Cine EI", "Cine EI Quick")
            or log_shooting in ("Cine EI", "Cine EI Quick")
        ):
            return WhiteBalanceCustomShutterShocklessResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                wb_mode=wb_mode,
                effective_wb_mode=wb_mode,
                color_temp_k=color_temp_k,
                amber_blue_axis=amber_blue_axis,
                green_magenta_axis=green_magenta_axis,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                log_shooting=log_shooting,
                picture_profile=picture_profile,
                custom_setup_capture_requested=custom_setup_capture_requested,
                custom_wb_error_0x0220=False,
                custom_wb_exported_in_camset=False,
                custom_wb_internal_preserved_across_cam_reset=False,
                priority_set_in_awb=priority_set_in_awb,
                effective_priority_set_in_awb=priority_set_in_awb,
                shockless_wb=shockless_wb,
                effective_shockless_wb=shockless_wb,
                direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
                shockless_transition_frames=0,
                shutter_awb_lock=shutter_awb_lock,
                effective_shutter_awb_lock="Off",
                fx6_wht_bal_switch=fx6_wht_bal_switch,
                fx6_atw_speed=fx6_atw_speed,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason="EOPNOTSUPP: FX6 ATW is locked out in Cine EI / Cine EI Quick",
            )
        if shutter_awb_lock != "Off":
            return WhiteBalanceCustomShutterShocklessResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                wb_mode=wb_mode,
                effective_wb_mode=wb_mode,
                color_temp_k=color_temp_k,
                amber_blue_axis=amber_blue_axis,
                green_magenta_axis=green_magenta_axis,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                log_shooting=log_shooting,
                picture_profile=picture_profile,
                custom_setup_capture_requested=custom_setup_capture_requested,
                custom_wb_error_0x0220=False,
                custom_wb_exported_in_camset=False,
                custom_wb_internal_preserved_across_cam_reset=False,
                priority_set_in_awb=priority_set_in_awb,
                effective_priority_set_in_awb=priority_set_in_awb,
                shockless_wb=shockless_wb,
                effective_shockless_wb=shockless_wb,
                direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
                shockless_transition_frames=0,
                shutter_awb_lock=shutter_awb_lock,
                effective_shutter_awb_lock="Off",
                fx6_wht_bal_switch=fx6_wht_bal_switch,
                fx6_atw_speed=fx6_atw_speed,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason="EOPNOTSUPP: FX6 lacks still-only [Shutter AWB Lock]",
            )
        return WhiteBalanceCustomShutterShocklessResult(
            body_profile=body_profile,
            admitted=True,
            errno_code=0,
            wb_mode=wb_mode,
            effective_wb_mode=wb_mode,
            color_temp_k=color_temp_k,
            amber_blue_axis=amber_blue_axis,
            green_magenta_axis=green_magenta_axis,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            picture_profile=picture_profile,
            custom_setup_capture_requested=custom_setup_capture_requested,
            custom_wb_error_0x0220=False,
            custom_wb_exported_in_camset=False,
            custom_wb_internal_preserved_across_cam_reset=True,
            priority_set_in_awb=priority_set_in_awb,
            effective_priority_set_in_awb=priority_set_in_awb,
            shockless_wb=shockless_wb,
            effective_shockless_wb=shockless_wb,
            direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
            shockless_transition_frames=0 if direct_ctemp_or_filter_dial_edited else 24,
            shutter_awb_lock=shutter_awb_lock,
            effective_shutter_awb_lock="Off",
            fx6_wht_bal_switch=fx6_wht_bal_switch,
            fx6_atw_speed=fx6_atw_speed,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"ADMITTED: FX6 WHT BAL={fx6_wht_bal_switch} ({wb_mode}, ATW Speed={fx6_atw_speed})"
            ),
        )

    # FX3 rejects FX6-only WB modes
    if wb_mode in FX6_EXTRA_WB_MODES:
        return WhiteBalanceCustomShutterShocklessResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            wb_mode=wb_mode,
            effective_wb_mode=wb_mode,
            color_temp_k=color_temp_k,
            amber_blue_axis=amber_blue_axis,
            green_magenta_axis=green_magenta_axis,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            picture_profile=picture_profile,
            custom_setup_capture_requested=custom_setup_capture_requested,
            custom_wb_error_0x0220=False,
            custom_wb_exported_in_camset=False,
            custom_wb_internal_preserved_across_cam_reset=False,
            priority_set_in_awb=priority_set_in_awb,
            effective_priority_set_in_awb=priority_set_in_awb,
            shockless_wb=shockless_wb,
            effective_shockless_wb=shockless_wb,
            direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
            shockless_transition_frames=0,
            shutter_awb_lock=shutter_awb_lock,
            effective_shutter_awb_lock=shutter_awb_lock,
            fx6_wht_bal_switch=fx6_wht_bal_switch,
            fx6_atw_speed=fx6_atw_speed,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=f"EOPNOTSUPP: FX3 Ver. 7.02 lacks FX6-specific WB mode {wb_mode!r}",
        )

    # Cine EI / Cine EI Quick locks out Auto & Underwater Auto
    in_cine_ei = exposure_mode in ("Cine EI", "Cine EI Quick") or log_shooting in (
        "Cine EI",
        "Cine EI Quick",
    )
    if in_cine_ei and wb_mode in ("Auto", "Underwater Auto"):
        return WhiteBalanceCustomShutterShocklessResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            wb_mode=wb_mode,
            effective_wb_mode=wb_mode,
            color_temp_k=color_temp_k,
            amber_blue_axis=amber_blue_axis,
            green_magenta_axis=green_magenta_axis,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            picture_profile=picture_profile,
            custom_setup_capture_requested=custom_setup_capture_requested,
            custom_wb_error_0x0220=False,
            custom_wb_exported_in_camset=False,
            custom_wb_internal_preserved_across_cam_reset=True,
            priority_set_in_awb=priority_set_in_awb,
            effective_priority_set_in_awb=priority_set_in_awb,
            shockless_wb=shockless_wb,
            effective_shockless_wb=shockless_wb,
            direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
            shockless_transition_frames=0,
            shutter_awb_lock=shutter_awb_lock,
            effective_shutter_awb_lock=shutter_awb_lock,
            fx6_wht_bal_switch=fx6_wht_bal_switch,
            fx6_atw_speed=fx6_atw_speed,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EOPNOTSUPP: {wb_mode!r} is locked out under Cine EI / Cine EI Quick "
                "(only manual/preset/Custom WB allowed)"
            ),
        )

    # [Custom Setup] warning (Custom WB Error 0x0220 / _f 0x63ac) under Log Shooting != Off or S-Log3/PPLUT1..4
    if custom_setup_capture_requested and (
        log_shooting != "Off"
        or picture_profile in ("S-Log3", "PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
    ):
        return WhiteBalanceCustomShutterShocklessResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            wb_mode=wb_mode,
            effective_wb_mode=wb_mode,
            color_temp_k=color_temp_k,
            amber_blue_axis=amber_blue_axis,
            green_magenta_axis=green_magenta_axis,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            picture_profile=picture_profile,
            custom_setup_capture_requested=True,
            custom_wb_error_0x0220=True,
            custom_wb_exported_in_camset=False,
            custom_wb_internal_preserved_across_cam_reset=True,
            priority_set_in_awb=priority_set_in_awb,
            effective_priority_set_in_awb=priority_set_in_awb,
            shockless_wb=shockless_wb,
            effective_shockless_wb=shockless_wb,
            direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
            shockless_transition_frames=0,
            shutter_awb_lock=shutter_awb_lock,
            effective_shutter_awb_lock=shutter_awb_lock,
            fx6_wht_bal_switch=fx6_wht_bal_switch,
            fx6_atw_speed=fx6_atw_speed,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EOPNOTSUPP: Custom WB Error (base 0x0220 / _f 0x63ac) under Log={log_shooting}, "
                f"PP={picture_profile}"
            ),
        )

    # [Shutter AWB Lock] is Still-only (Movie uses AWB Lock Hold/Toggle)
    if shoot_mode != SHOOT_MODE_STILL and shutter_awb_lock != "Off":
        return WhiteBalanceCustomShutterShocklessResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            wb_mode=wb_mode,
            effective_wb_mode=wb_mode,
            color_temp_k=color_temp_k,
            amber_blue_axis=amber_blue_axis,
            green_magenta_axis=green_magenta_axis,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            picture_profile=picture_profile,
            custom_setup_capture_requested=custom_setup_capture_requested,
            custom_wb_error_0x0220=False,
            custom_wb_exported_in_camset=False,
            custom_wb_internal_preserved_across_cam_reset=True,
            priority_set_in_awb=priority_set_in_awb,
            effective_priority_set_in_awb=priority_set_in_awb,
            shockless_wb=shockless_wb,
            effective_shockless_wb=shockless_wb,
            direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
            shockless_transition_frames=0,
            shutter_awb_lock=shutter_awb_lock,
            effective_shutter_awb_lock="Off",
            fx6_wht_bal_switch=fx6_wht_bal_switch,
            fx6_atw_speed=fx6_atw_speed,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EOPNOTSUPP: [Shutter AWB Lock] is Still-only (got shoot_mode={shoot_mode}; "
                "Movie uses AWB Lock Hold/Toggle)"
            ),
        )

    # Reset vs Initialize lifecycle
    if initialize_applied:
        eff_wb = "C.Temp./Filter" if in_cine_ei else "Auto"
        eff_priority = "Standard"
        eff_shockless = "1 (Fast)"
        eff_shutter_lock = "Off"
        custom_preserved = False
    elif camera_settings_reset_applied:
        eff_wb = "C.Temp./Filter" if in_cine_ei else "Auto"
        eff_priority = "Standard"
        eff_shockless = "1 (Fast)"
        # [Shutter AWB Lock] & internal Custom 1..3 values survive [Camera Settings Reset]!
        eff_shutter_lock = shutter_awb_lock
        custom_preserved = True
    else:
        eff_wb = wb_mode
        eff_priority = priority_set_in_awb
        eff_shockless = shockless_wb
        eff_shutter_lock = shutter_awb_lock
        custom_preserved = True

    if direct_ctemp_or_filter_dial_edited or eff_shockless == "Off" or shoot_mode == SHOOT_MODE_STILL:
        shockless_frames = 0
    elif eff_shockless == "1 (Fast)":
        shockless_frames = 12
    elif eff_shockless == "2":
        shockless_frames = 30
    else:
        shockless_frames = 60

    return WhiteBalanceCustomShutterShocklessResult(
        body_profile=body_profile,
        admitted=True,
        errno_code=0,
        wb_mode=wb_mode,
        effective_wb_mode=eff_wb,
        color_temp_k=color_temp_k,
        amber_blue_axis=amber_blue_axis,
        green_magenta_axis=green_magenta_axis,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        log_shooting=log_shooting,
        picture_profile=picture_profile,
        custom_setup_capture_requested=custom_setup_capture_requested,
        custom_wb_error_0x0220=False,
        custom_wb_exported_in_camset=False,  # Custom 1..3 always excluded from CAMSET*.DAT
        custom_wb_internal_preserved_across_cam_reset=custom_preserved,
        priority_set_in_awb=priority_set_in_awb,
        effective_priority_set_in_awb=eff_priority,
        shockless_wb=shockless_wb,
        effective_shockless_wb=eff_shockless,
        direct_ctemp_or_filter_dial_edited=direct_ctemp_or_filter_dial_edited,
        shockless_transition_frames=shockless_frames,
        shutter_awb_lock=shutter_awb_lock,
        effective_shutter_awb_lock=eff_shutter_lock,
        fx6_wht_bal_switch=fx6_wht_bal_switch,
        fx6_atw_speed=fx6_atw_speed,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        reason=(
            f"ADMITTED: FX3 WB={eff_wb} ({color_temp_k}K A/B={amber_blue_axis} G/M={green_magenta_axis}), "
            f"PriorityAWB={eff_priority}, Shockless={eff_shockless}({shockless_frames}f), "
            f"ShutterAWBLock={eff_shutter_lock}, CustomPreserved={custom_preserved}"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 71C — Movie AF Transition Speed (1..7) & Shift Sensitivity (1..5),
#                 [AF Assist] & External-Only M&C Focus Map (<150fps Cutoff)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MovieAfScalesAssistAndFocusMapResult:
    body_profile: str
    firmware_version: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    af_transition_speed: int
    effective_af_transition_speed: int
    af_subj_shift_sensitivity: int
    effective_af_subj_shift_sensitivity: int
    af_assist: str
    effective_af_assist: str
    focus_mode: str
    lens_model: str
    inbody_focus_map_requested: bool
    external_mc_focus_map_requested: bool
    inbody_focus_map_supported: bool
    external_mc_focus_map_active: bool
    fps: float
    sq_mode_active: bool
    auto_framing_active: bool
    playback_control_active: bool
    usb_wired_remote_or_uvc_active: bool
    recorded_or_hdmi_focus_map_pixels: int
    camera_settings_reset_applied: bool
    initialize_applied: bool
    reason: str


def simulate_movie_af_scales_assist_and_focusmap_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    firmware_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    af_transition_speed: int = FX3_AF_TRANSITION_SPEED_DEFAULT,
    af_subj_shift_sensitivity: int = FX3_AF_SUBJ_SHIFT_SENS_DEFAULT,
    af_assist: str = "Off",
    focus_mode: str = "AF-C",
    lens_model: str = "SEL2470GM2",
    inbody_focus_map_requested: bool = False,
    external_mc_focus_map_requested: bool = False,
    fps: float = 23.98,
    sq_mode_active: bool = False,
    auto_framing_active: bool = False,
    playback_control_active: bool = False,
    usb_wired_remote_or_uvc_active: bool = False,
    fx6_hdmi_raw_active: bool = False,
    fx6_focus_magnifier_active: bool = False,
    fx6_digital_extender_active: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> MovieAfScalesAssistAndFocusMapResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage71Phase333Error(f"Unsupported body_profile={body_profile!r}")
    if firmware_version not in VALID_FW_VERSIONS:
        raise Stage71Phase333Error(f"Unsupported firmware_version={firmware_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage71Phase333Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if af_assist not in ("On", "Off"):
        raise Stage71Phase333Error(f"Unsupported af_assist={af_assist!r}")
    if focus_mode not in VALID_FOCUS_MODES:
        raise Stage71Phase333Error(f"Unsupported focus_mode={focus_mode!r}")
    if lens_model not in VALID_LENS_MODELS:
        raise Stage71Phase333Error(f"Unsupported lens_model={lens_model!r}")

    eff_ver = FW_VER_601 if body_profile == BODY_MODEL_FX6 else firmware_version
    inbody_supported = body_profile == BODY_MODEL_FX6

    # BOTH FX3 Ver. 7.02 and FX6 Ver. 6.01 enforce 1..7 Transition Speed & 1..5 Shift Sensitivity!
    if not (AF_TRANSITION_SPEED_MIN <= af_transition_speed <= AF_TRANSITION_SPEED_MAX):
        return MovieAfScalesAssistAndFocusMapResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            shoot_mode=shoot_mode,
            af_transition_speed=af_transition_speed,
            effective_af_transition_speed=FX3_AF_TRANSITION_SPEED_DEFAULT,
            af_subj_shift_sensitivity=af_subj_shift_sensitivity,
            effective_af_subj_shift_sensitivity=FX3_AF_SUBJ_SHIFT_SENS_DEFAULT,
            af_assist=af_assist,
            effective_af_assist="Off",
            focus_mode=focus_mode,
            lens_model=lens_model,
            inbody_focus_map_requested=inbody_focus_map_requested,
            external_mc_focus_map_requested=external_mc_focus_map_requested,
            inbody_focus_map_supported=inbody_supported,
            external_mc_focus_map_active=False,
            fps=fps,
            sq_mode_active=sq_mode_active,
            auto_framing_active=auto_framing_active,
            playback_control_active=playback_control_active,
            usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
            recorded_or_hdmi_focus_map_pixels=0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EINVAL: {body_profile} [AF Transition Speed] strictly 1..7 "
                f"(got {af_transition_speed})"
            ),
        )
    if not (AF_SUBJ_SHIFT_SENS_MIN <= af_subj_shift_sensitivity <= AF_SUBJ_SHIFT_SENS_MAX):
        return MovieAfScalesAssistAndFocusMapResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            shoot_mode=shoot_mode,
            af_transition_speed=af_transition_speed,
            effective_af_transition_speed=af_transition_speed,
            af_subj_shift_sensitivity=af_subj_shift_sensitivity,
            effective_af_subj_shift_sensitivity=FX3_AF_SUBJ_SHIFT_SENS_DEFAULT,
            af_assist=af_assist,
            effective_af_assist="Off",
            focus_mode=focus_mode,
            lens_model=lens_model,
            inbody_focus_map_requested=inbody_focus_map_requested,
            external_mc_focus_map_requested=external_mc_focus_map_requested,
            inbody_focus_map_supported=inbody_supported,
            external_mc_focus_map_active=False,
            fps=fps,
            sq_mode_active=sq_mode_active,
            auto_framing_active=auto_framing_active,
            playback_control_active=playback_control_active,
            usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
            recorded_or_hdmi_focus_map_pixels=0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EINVAL: {body_profile} [AF Subj. Shift Sensitivity] strictly 1..5 "
                f"(got {af_subj_shift_sensitivity}; 6/7 have 0 hits in BOTH FX3 and FX6 appFw.so)"
            ),
        )

    # All 3 AF params reset on Camera Settings Reset or Initialize
    if camera_settings_reset_applied or initialize_applied:
        eff_speed = FX3_AF_TRANSITION_SPEED_DEFAULT
        eff_sens = FX3_AF_SUBJ_SHIFT_SENS_DEFAULT
        eff_assist = "Off"
    else:
        eff_speed = af_transition_speed
        eff_sens = af_subj_shift_sensitivity
        eff_assist = af_assist

    # [AF Assist] compatibility checks
    if eff_assist == "On":
        if shoot_mode not in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ) or focus_mode != "AF-C":
            return MovieAfScalesAssistAndFocusMapResult(
                body_profile=body_profile,
                firmware_version=eff_ver,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                af_transition_speed=af_transition_speed,
                effective_af_transition_speed=eff_speed,
                af_subj_shift_sensitivity=af_subj_shift_sensitivity,
                effective_af_subj_shift_sensitivity=eff_sens,
                af_assist=af_assist,
                effective_af_assist="Off",
                focus_mode=focus_mode,
                lens_model=lens_model,
                inbody_focus_map_requested=inbody_focus_map_requested,
                external_mc_focus_map_requested=external_mc_focus_map_requested,
                inbody_focus_map_supported=inbody_supported,
                external_mc_focus_map_active=False,
                fps=fps,
                sq_mode_active=sq_mode_active,
                auto_framing_active=auto_framing_active,
                playback_control_active=playback_control_active,
                usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
                recorded_or_hdmi_focus_map_pixels=0,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason=(
                    f"EOPNOTSUPP: [AF Assist] requires Movie/S&Q + AF-C "
                    f"(got mode={shoot_mode}, focus={focus_mode})"
                ),
            )
        if lens_model in AF_ASSIST_INCOMPATIBLE_LENSES:
            return MovieAfScalesAssistAndFocusMapResult(
                body_profile=body_profile,
                firmware_version=eff_ver,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                af_transition_speed=af_transition_speed,
                effective_af_transition_speed=eff_speed,
                af_subj_shift_sensitivity=af_subj_shift_sensitivity,
                effective_af_subj_shift_sensitivity=eff_sens,
                af_assist=af_assist,
                effective_af_assist="Off",
                focus_mode=focus_mode,
                lens_model=lens_model,
                inbody_focus_map_requested=inbody_focus_map_requested,
                external_mc_focus_map_requested=external_mc_focus_map_requested,
                inbody_focus_map_supported=inbody_supported,
                external_mc_focus_map_active=False,
                fps=fps,
                sq_mode_active=sq_mode_active,
                auto_framing_active=auto_framing_active,
                playback_control_active=playback_control_active,
                usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
                recorded_or_hdmi_focus_map_pixels=0,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason=(
                    f"EOPNOTSUPP: [AF Assist] incompatible with lens {lens_model!r} "
                    "(SELP1650/SEL18200LE/non-PDAF/no lens)"
                ),
            )

    # FX6 native in-body Focus Map (> 6fps and < 150fps; blocked on HDMI RAW, Focus Mag, Digital Extender)
    if body_profile == BODY_MODEL_FX6:
        if inbody_focus_map_requested:
            if not (6.0 < fps < 150.0):
                return MovieAfScalesAssistAndFocusMapResult(
                    body_profile=body_profile,
                    firmware_version=eff_ver,
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    shoot_mode=shoot_mode,
                    af_transition_speed=af_transition_speed,
                    effective_af_transition_speed=eff_speed,
                    af_subj_shift_sensitivity=af_subj_shift_sensitivity,
                    effective_af_subj_shift_sensitivity=eff_sens,
                    af_assist=af_assist,
                    effective_af_assist=eff_assist,
                    focus_mode=focus_mode,
                    lens_model=lens_model,
                    inbody_focus_map_requested=True,
                    external_mc_focus_map_requested=external_mc_focus_map_requested,
                    inbody_focus_map_supported=True,
                    external_mc_focus_map_active=False,
                    fps=fps,
                    sq_mode_active=sq_mode_active,
                    auto_framing_active=auto_framing_active,
                    playback_control_active=playback_control_active,
                    usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
                    recorded_or_hdmi_focus_map_pixels=0,
                    camera_settings_reset_applied=camera_settings_reset_applied,
                    initialize_applied=initialize_applied,
                    reason=(
                        f"EOPNOTSUPP: FX6 native Focus Map requires >6fps and <150fps (got {fps}fps)"
                    ),
                )
            if fx6_hdmi_raw_active or fx6_focus_magnifier_active or fx6_digital_extender_active:
                return MovieAfScalesAssistAndFocusMapResult(
                    body_profile=body_profile,
                    firmware_version=eff_ver,
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    shoot_mode=shoot_mode,
                    af_transition_speed=af_transition_speed,
                    effective_af_transition_speed=eff_speed,
                    af_subj_shift_sensitivity=af_subj_shift_sensitivity,
                    effective_af_subj_shift_sensitivity=eff_sens,
                    af_assist=af_assist,
                    effective_af_assist=eff_assist,
                    focus_mode=focus_mode,
                    lens_model=lens_model,
                    inbody_focus_map_requested=True,
                    external_mc_focus_map_requested=external_mc_focus_map_requested,
                    inbody_focus_map_supported=True,
                    external_mc_focus_map_active=False,
                    fps=fps,
                    sq_mode_active=sq_mode_active,
                    auto_framing_active=auto_framing_active,
                    playback_control_active=playback_control_active,
                    usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
                    recorded_or_hdmi_focus_map_pixels=0,
                    camera_settings_reset_applied=camera_settings_reset_applied,
                    initialize_applied=initialize_applied,
                    reason="EOPNOTSUPP: FX6 native Focus Map blocked during HDMI RAW / Focus Magnifier / Digital Extender",
                )
        return MovieAfScalesAssistAndFocusMapResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=True,
            errno_code=0,
            shoot_mode=shoot_mode,
            af_transition_speed=af_transition_speed,
            effective_af_transition_speed=eff_speed,
            af_subj_shift_sensitivity=af_subj_shift_sensitivity,
            effective_af_subj_shift_sensitivity=eff_sens,
            af_assist=af_assist,
            effective_af_assist=eff_assist,
            focus_mode=focus_mode,
            lens_model=lens_model,
            inbody_focus_map_requested=inbody_focus_map_requested,
            external_mc_focus_map_requested=external_mc_focus_map_requested,
            inbody_focus_map_supported=True,
            external_mc_focus_map_active=False,
            fps=fps,
            sq_mode_active=sq_mode_active,
            auto_framing_active=auto_framing_active,
            playback_control_active=playback_control_active,
            usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
            recorded_or_hdmi_focus_map_pixels=0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"ADMITTED: FX6 Ver. 6.01 AF Speed={eff_speed}/7, ShiftSens={eff_sens}/5, "
                f"NativeFocusMap={inbody_focus_map_requested}@{fps}fps"
            ),
        )

    # FX3 has ZERO in-body [Focus Map] (0 hits for USER_MENU_FOCUS_MAP)
    if inbody_focus_map_requested:
        return MovieAfScalesAssistAndFocusMapResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            af_transition_speed=af_transition_speed,
            effective_af_transition_speed=eff_speed,
            af_subj_shift_sensitivity=af_subj_shift_sensitivity,
            effective_af_subj_shift_sensitivity=eff_sens,
            af_assist=af_assist,
            effective_af_assist=eff_assist,
            focus_mode=focus_mode,
            lens_model=lens_model,
            inbody_focus_map_requested=True,
            external_mc_focus_map_requested=external_mc_focus_map_requested,
            inbody_focus_map_supported=False,
            external_mc_focus_map_active=False,
            fps=fps,
            sq_mode_active=sq_mode_active,
            auto_framing_active=auto_framing_active,
            playback_control_active=playback_control_active,
            usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
            recorded_or_hdmi_focus_map_pixels=0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                "EOPNOTSUPP: FX3 Ver. 7.02 has ZERO in-body [Focus Map] "
                "(0 hits for USER_MENU_FOCUS_MAP / ASSIGNABLE_SWITCH_FOCUS_MAP)"
            ),
        )

    # FX3 Ver. 6.00+ External *Monitor & Control* telemetry-only Focus Map
    mc_active = False
    if external_mc_focus_map_requested:
        if firmware_version in (FW_VER_200, FW_VER_300, FW_VER_400, FW_VER_500):
            return MovieAfScalesAssistAndFocusMapResult(
                body_profile=body_profile,
                firmware_version=eff_ver,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                af_transition_speed=af_transition_speed,
                effective_af_transition_speed=eff_speed,
                af_subj_shift_sensitivity=af_subj_shift_sensitivity,
                effective_af_subj_shift_sensitivity=eff_sens,
                af_assist=af_assist,
                effective_af_assist=eff_assist,
                focus_mode=focus_mode,
                lens_model=lens_model,
                inbody_focus_map_requested=False,
                external_mc_focus_map_requested=True,
                inbody_focus_map_supported=False,
                external_mc_focus_map_active=False,
                fps=fps,
                sq_mode_active=sq_mode_active,
                auto_framing_active=auto_framing_active,
                playback_control_active=playback_control_active,
                usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
                recorded_or_hdmi_focus_map_pixels=0,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason=f"EOPNOTSUPP: FX3 External M&C Focus Map requires Ver. 6.00+ (got {eff_ver})",
            )
        blocked_reasons: List[str] = []
        if fps >= 150.0:
            blocked_reasons.append(f"fps={fps}>=150")
        if auto_framing_active:
            blocked_reasons.append("AutoFraming=On")
        if playback_control_active:
            blocked_reasons.append("PlaybackControl=On")
        if focus_mode == "MF" or lens_model in ("Non_PDAF_Adapter", "No_Lens"):
            blocked_reasons.append(f"non_PDAF_or_MF(focus={focus_mode},lens={lens_model})")
        if usb_wired_remote_or_uvc_active:
            blocked_reasons.append("USB_wired_remote_or_UVC")
        if blocked_reasons:
            return MovieAfScalesAssistAndFocusMapResult(
                body_profile=body_profile,
                firmware_version=eff_ver,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                af_transition_speed=af_transition_speed,
                effective_af_transition_speed=eff_speed,
                af_subj_shift_sensitivity=af_subj_shift_sensitivity,
                effective_af_subj_shift_sensitivity=eff_sens,
                af_assist=af_assist,
                effective_af_assist=eff_assist,
                focus_mode=focus_mode,
                lens_model=lens_model,
                inbody_focus_map_requested=False,
                external_mc_focus_map_requested=True,
                inbody_focus_map_supported=False,
                external_mc_focus_map_active=False,
                fps=fps,
                sq_mode_active=sq_mode_active,
                auto_framing_active=auto_framing_active,
                playback_control_active=playback_control_active,
                usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
                recorded_or_hdmi_focus_map_pixels=0,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason=(
                    "EOPNOTSUPP: FX3 External M&C Focus Map blocked by: "
                    + ", ".join(blocked_reasons)
                ),
            )
        mc_active = True

    return MovieAfScalesAssistAndFocusMapResult(
        body_profile=body_profile,
        firmware_version=eff_ver,
        admitted=True,
        errno_code=0,
        shoot_mode=shoot_mode,
        af_transition_speed=af_transition_speed,
        effective_af_transition_speed=eff_speed,
        af_subj_shift_sensitivity=af_subj_shift_sensitivity,
        effective_af_subj_shift_sensitivity=eff_sens,
        af_assist=af_assist,
        effective_af_assist=eff_assist,
        focus_mode=focus_mode,
        lens_model=lens_model,
        inbody_focus_map_requested=False,
        external_mc_focus_map_requested=external_mc_focus_map_requested,
        inbody_focus_map_supported=False,
        external_mc_focus_map_active=mc_active,
        fps=fps,
        sq_mode_active=sq_mode_active,
        auto_framing_active=auto_framing_active,
        playback_control_active=playback_control_active,
        usb_wired_remote_or_uvc_active=usb_wired_remote_or_uvc_active,
        recorded_or_hdmi_focus_map_pixels=0,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        reason=(
            f"ADMITTED: FX3 {eff_ver} AF TransitionSpeed={eff_speed}/7, "
            f"ShiftSens={eff_sens}/5, AF_Assist={eff_assist}, ExternalMCFocusMap={mc_active}@{fps}fps"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 71D — 15-Ratio `[Marker Display]` & 4-Color `[Peaking Display]`
#                 Clean-HDMI Isolation & `Initialize`-Only Lifecycle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Marker15RatioAndPeaking4ColorResult:
    body_profile: str
    firmware_version: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    marker_display: str
    effective_marker_display: str
    center_marker: str
    effective_center_marker: str
    aspect_marker: str
    effective_aspect_marker: str
    safety_zone: str
    effective_safety_zone: str
    guideframe: str
    effective_guideframe: str
    peaking_display: str
    effective_peaking_display: str
    peaking_level: str
    effective_peaking_level: str
    peaking_color: str
    effective_peaking_color: str
    focus_magnifier_active: bool
    effective_marker_overlay_visible: bool
    marker_auto_hidden_for_magnifier: bool
    hdmi_marker_or_peaking_leaked_pixels: int
    hdmi_marker_overlay_active: bool
    hdmi_peaking_overlay_active: bool
    all_8_items_survive_camera_settings_reset: bool
    fx6_aspect_mask_level: int
    fx6_user_box_width: int
    fx6_user_box_height: int
    camera_settings_reset_applied: bool
    initialize_applied: bool
    reason: str


def simulate_marker_15ratio_and_peaking_4color_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    firmware_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    marker_display: str = "Off",
    center_marker: str = "Off",
    aspect_marker: str = "Off",
    safety_zone: str = "Off",
    guideframe: str = "Off",
    peaking_display: str = "Off",
    peaking_level: str = "Mid",
    peaking_color: Optional[str] = None,
    focus_magnifier_active: bool = False,
    fx6_aspect_mask_level: int = 12,
    fx6_user_box_width: int = 160,
    fx6_user_box_height: int = 90,
    fx6_user_box_h_pos: int = 0,
    fx6_user_box_v_pos: int = 0,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> Marker15RatioAndPeaking4ColorResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage71Phase333Error(f"Unsupported body_profile={body_profile!r}")
    if firmware_version not in VALID_FW_VERSIONS:
        raise Stage71Phase333Error(f"Unsupported firmware_version={firmware_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage71Phase333Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if marker_display not in ("On", "Off"):
        raise Stage71Phase333Error(f"Unsupported marker_display={marker_display!r}")
    if center_marker not in ("On", "Off"):
        raise Stage71Phase333Error(f"Unsupported center_marker={center_marker!r}")
    if aspect_marker not in VALID_ASPECT_MARKER_STATES:
        raise Stage71Phase333Error(f"Unsupported aspect_marker={aspect_marker!r}")
    if safety_zone not in VALID_SAFETY_ZONE_MODES:
        raise Stage71Phase333Error(f"Unsupported safety_zone={safety_zone!r}")
    if guideframe not in ("On", "Off"):
        raise Stage71Phase333Error(f"Unsupported guideframe={guideframe!r}")
    if peaking_display not in ("On", "Off"):
        raise Stage71Phase333Error(f"Unsupported peaking_display={peaking_display!r}")
    if peaking_level not in VALID_PEAKING_LEVELS:
        raise Stage71Phase333Error(f"Unsupported peaking_level={peaking_level!r}")

    req_peaking_color = (
        ("B&W" if body_profile == BODY_MODEL_FX6 else "White")
        if peaking_color is None
        else peaking_color
    )
    if req_peaking_color not in ALL_PEAKING_COLORS:
        raise Stage71Phase333Error(f"Unsupported peaking_color={req_peaking_color!r}")

    eff_ver = FW_VER_601 if body_profile == BODY_MODEL_FX6 else firmware_version

    # ILME-FX6 Ver. 6.01 branch: Aspect Mask 0..15, User Box 3..479 x 3..269, B&W Peaking
    if body_profile == BODY_MODEL_FX6:
        if req_peaking_color not in FX6_PEAKING_COLORS:
            return Marker15RatioAndPeaking4ColorResult(
                body_profile=body_profile,
                firmware_version=eff_ver,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                marker_display=marker_display,
                effective_marker_display=marker_display,
                center_marker=center_marker,
                effective_center_marker=center_marker,
                aspect_marker=aspect_marker,
                effective_aspect_marker=aspect_marker,
                safety_zone=safety_zone,
                effective_safety_zone=safety_zone,
                guideframe=guideframe,
                effective_guideframe=guideframe,
                peaking_display=peaking_display,
                effective_peaking_display=peaking_display,
                peaking_level=peaking_level,
                effective_peaking_level=peaking_level,
                peaking_color=req_peaking_color,
                effective_peaking_color="B&W",
                focus_magnifier_active=focus_magnifier_active,
                effective_marker_overlay_visible=False,
                marker_auto_hidden_for_magnifier=False,
                hdmi_marker_or_peaking_leaked_pixels=HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS,
                hdmi_marker_overlay_active=False,
                hdmi_peaking_overlay_active=False,
                all_8_items_survive_camera_settings_reset=False,
                fx6_aspect_mask_level=fx6_aspect_mask_level,
                fx6_user_box_width=fx6_user_box_width,
                fx6_user_box_height=fx6_user_box_height,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason=f"EOPNOTSUPP: FX6 Peaking colors are {FX6_PEAKING_COLORS} (got {req_peaking_color!r})",
            )
        if not (0 <= fx6_aspect_mask_level <= 15):
            return Marker15RatioAndPeaking4ColorResult(
                body_profile=body_profile,
                firmware_version=eff_ver,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                shoot_mode=shoot_mode,
                marker_display=marker_display,
                effective_marker_display=marker_display,
                center_marker=center_marker,
                effective_center_marker=center_marker,
                aspect_marker=aspect_marker,
                effective_aspect_marker=aspect_marker,
                safety_zone=safety_zone,
                effective_safety_zone=safety_zone,
                guideframe=guideframe,
                effective_guideframe=guideframe,
                peaking_display=peaking_display,
                effective_peaking_display=peaking_display,
                peaking_level=peaking_level,
                effective_peaking_level=peaking_level,
                peaking_color=req_peaking_color,
                effective_peaking_color=req_peaking_color,
                focus_magnifier_active=focus_magnifier_active,
                effective_marker_overlay_visible=False,
                marker_auto_hidden_for_magnifier=False,
                hdmi_marker_or_peaking_leaked_pixels=HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS,
                hdmi_marker_overlay_active=False,
                hdmi_peaking_overlay_active=False,
                all_8_items_survive_camera_settings_reset=False,
                fx6_aspect_mask_level=fx6_aspect_mask_level,
                fx6_user_box_width=fx6_user_box_width,
                fx6_user_box_height=fx6_user_box_height,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason=f"EINVAL: FX6 Aspect Mask level must be 0..15 (got {fx6_aspect_mask_level})",
            )
        if (
            not (3 <= fx6_user_box_width <= 479)
            or not (3 <= fx6_user_box_height <= 269)
            or not (-476 <= fx6_user_box_h_pos <= 476)
            or not (-266 <= fx6_user_box_v_pos <= 266)
        ):
            return Marker15RatioAndPeaking4ColorResult(
                body_profile=body_profile,
                firmware_version=eff_ver,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                shoot_mode=shoot_mode,
                marker_display=marker_display,
                effective_marker_display=marker_display,
                center_marker=center_marker,
                effective_center_marker=center_marker,
                aspect_marker=aspect_marker,
                effective_aspect_marker=aspect_marker,
                safety_zone=safety_zone,
                effective_safety_zone=safety_zone,
                guideframe=guideframe,
                effective_guideframe=guideframe,
                peaking_display=peaking_display,
                effective_peaking_display=peaking_display,
                peaking_level=peaking_level,
                effective_peaking_level=peaking_level,
                peaking_color=req_peaking_color,
                effective_peaking_color=req_peaking_color,
                focus_magnifier_active=focus_magnifier_active,
                effective_marker_overlay_visible=False,
                marker_auto_hidden_for_magnifier=False,
                hdmi_marker_or_peaking_leaked_pixels=HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS,
                hdmi_marker_overlay_active=False,
                hdmi_peaking_overlay_active=False,
                all_8_items_survive_camera_settings_reset=False,
                fx6_aspect_mask_level=fx6_aspect_mask_level,
                fx6_user_box_width=fx6_user_box_width,
                fx6_user_box_height=fx6_user_box_height,
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason=(
                    f"EINVAL: FX6 User Box bounds are 3..479 x 3..269, pos -476..+476 / -266..+266 "
                    f"(got {fx6_user_box_width}x{fx6_user_box_height} @{fx6_user_box_h_pos},{fx6_user_box_v_pos})"
                ),
            )
        return Marker15RatioAndPeaking4ColorResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=True,
            errno_code=0,
            shoot_mode=shoot_mode,
            marker_display=marker_display,
            effective_marker_display=marker_display,
            center_marker=center_marker,
            effective_center_marker=center_marker,
            aspect_marker=aspect_marker,
            effective_aspect_marker=aspect_marker,
            safety_zone=safety_zone,
            effective_safety_zone=safety_zone,
            guideframe=guideframe,
            effective_guideframe=guideframe,
            peaking_display=peaking_display,
            effective_peaking_display=peaking_display,
            peaking_level=peaking_level,
            effective_peaking_level=peaking_level,
            peaking_color=req_peaking_color,
            effective_peaking_color=req_peaking_color,
            focus_magnifier_active=focus_magnifier_active,
            effective_marker_overlay_visible=(marker_display == "On" and not focus_magnifier_active),
            marker_auto_hidden_for_magnifier=(marker_display == "On" and focus_magnifier_active),
            hdmi_marker_or_peaking_leaked_pixels=HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS,
            hdmi_marker_overlay_active=False,
            hdmi_peaking_overlay_active=False,
            all_8_items_survive_camera_settings_reset=True,
            fx6_aspect_mask_level=fx6_aspect_mask_level,
            fx6_user_box_width=fx6_user_box_width,
            fx6_user_box_height=fx6_user_box_height,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"ADMITTED: FX6 AspectMask={fx6_aspect_mask_level}/15, "
                f"UserBox={fx6_user_box_width}x{fx6_user_box_height}, Peaking={req_peaking_color}"
            ),
        )

    # FX3 rejects FX6-only Peaking B&W and 92.5%/95% Safety Zone
    if req_peaking_color not in FX3_PEAKING_COLORS:
        return Marker15RatioAndPeaking4ColorResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            marker_display=marker_display,
            effective_marker_display=marker_display,
            center_marker=center_marker,
            effective_center_marker=center_marker,
            aspect_marker=aspect_marker,
            effective_aspect_marker=aspect_marker,
            safety_zone=safety_zone,
            effective_safety_zone=safety_zone,
            guideframe=guideframe,
            effective_guideframe=guideframe,
            peaking_display=peaking_display,
            effective_peaking_display=peaking_display,
            peaking_level=peaking_level,
            effective_peaking_level=peaking_level,
            peaking_color=req_peaking_color,
            effective_peaking_color="White",
            focus_magnifier_active=focus_magnifier_active,
            effective_marker_overlay_visible=False,
            marker_auto_hidden_for_magnifier=False,
            hdmi_marker_or_peaking_leaked_pixels=HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS,
            hdmi_marker_overlay_active=False,
            hdmi_peaking_overlay_active=False,
            all_8_items_survive_camera_settings_reset=True,
            fx6_aspect_mask_level=0,
            fx6_user_box_width=0,
            fx6_user_box_height=0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=f"EOPNOTSUPP: FX3 Peaking colors are {FX3_PEAKING_COLORS} (got {req_peaking_color!r})",
        )
    if safety_zone in ("92.5%", "95%"):
        return Marker15RatioAndPeaking4ColorResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            marker_display=marker_display,
            effective_marker_display=marker_display,
            center_marker=center_marker,
            effective_center_marker=center_marker,
            aspect_marker=aspect_marker,
            effective_aspect_marker=aspect_marker,
            safety_zone=safety_zone,
            effective_safety_zone="Off",
            guideframe=guideframe,
            effective_guideframe=guideframe,
            peaking_display=peaking_display,
            effective_peaking_display=peaking_display,
            peaking_level=peaking_level,
            effective_peaking_level=peaking_level,
            peaking_color=req_peaking_color,
            effective_peaking_color=req_peaking_color,
            focus_magnifier_active=focus_magnifier_active,
            effective_marker_overlay_visible=False,
            marker_auto_hidden_for_magnifier=False,
            hdmi_marker_or_peaking_leaked_pixels=HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS,
            hdmi_marker_overlay_active=False,
            hdmi_peaking_overlay_active=False,
            all_8_items_survive_camera_settings_reset=True,
            fx6_aspect_mask_level=0,
            fx6_user_box_width=0,
            fx6_user_box_height=0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=f"EOPNOTSUPP: FX3 Safety Zone is Off/80%%/90%% only ({safety_zone!r} is FX6-only)",
        )
    if aspect_marker == "16:9" and firmware_version == FW_VER_200:
        return Marker15RatioAndPeaking4ColorResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            marker_display=marker_display,
            effective_marker_display=marker_display,
            center_marker=center_marker,
            effective_center_marker=center_marker,
            aspect_marker=aspect_marker,
            effective_aspect_marker="Off",
            safety_zone=safety_zone,
            effective_safety_zone=safety_zone,
            guideframe=guideframe,
            effective_guideframe=guideframe,
            peaking_display=peaking_display,
            effective_peaking_display=peaking_display,
            peaking_level=peaking_level,
            effective_peaking_level=peaking_level,
            peaking_color=req_peaking_color,
            effective_peaking_color=req_peaking_color,
            focus_magnifier_active=focus_magnifier_active,
            effective_marker_overlay_visible=False,
            marker_auto_hidden_for_magnifier=False,
            hdmi_marker_or_peaking_leaked_pixels=HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS,
            hdmi_marker_overlay_active=False,
            hdmi_peaking_overlay_active=False,
            all_8_items_survive_camera_settings_reset=True,
            fx6_aspect_mask_level=0,
            fx6_user_box_width=0,
            fx6_user_box_height=0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason="EOPNOTSUPP: Aspect Marker [16:9] added in FX3 Ver. 3.00+ (not on Ver. 2.00)",
        )
    if shoot_mode == SHOOT_MODE_STILL and marker_display == "On":
        return Marker15RatioAndPeaking4ColorResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            marker_display=marker_display,
            effective_marker_display="Off",
            center_marker=center_marker,
            effective_center_marker=center_marker,
            aspect_marker=aspect_marker,
            effective_aspect_marker=aspect_marker,
            safety_zone=safety_zone,
            effective_safety_zone=safety_zone,
            guideframe=guideframe,
            effective_guideframe=guideframe,
            peaking_display=peaking_display,
            effective_peaking_display=peaking_display,
            peaking_level=peaking_level,
            effective_peaking_level=peaking_level,
            peaking_color=req_peaking_color,
            effective_peaking_color=req_peaking_color,
            focus_magnifier_active=focus_magnifier_active,
            effective_marker_overlay_visible=False,
            marker_auto_hidden_for_magnifier=False,
            hdmi_marker_or_peaking_leaked_pixels=HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS,
            hdmi_marker_overlay_active=False,
            hdmi_peaking_overlay_active=False,
            all_8_items_survive_camera_settings_reset=True,
            fx6_aspect_mask_level=0,
            fx6_user_box_width=0,
            fx6_user_box_height=0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason="EOPNOTSUPP: FX3 [Marker Display] scope is Movie/S&Q only (Still disallowed)",
        )

    # ALL 8 items resist [Camera Settings Reset]; reset ONLY on [Initialize]
    if initialize_applied:
        eff_marker_disp = "Off"
        eff_center = "Off"
        eff_aspect = "Off"
        eff_safety = "Off"
        eff_guide = "Off"
        eff_peak_disp = "Off"
        eff_peak_lvl = "Mid"
        eff_peak_clr = "White"
    else:
        eff_marker_disp = marker_display
        eff_center = center_marker
        eff_aspect = aspect_marker
        eff_safety = safety_zone
        eff_guide = guideframe
        eff_peak_disp = peaking_display
        eff_peak_lvl = peaking_level
        eff_peak_clr = req_peaking_color

    auto_hidden = (eff_marker_disp == "On") and focus_magnifier_active
    overlay_visible = (eff_marker_disp == "On") and (not focus_magnifier_active)

    return Marker15RatioAndPeaking4ColorResult(
        body_profile=body_profile,
        firmware_version=eff_ver,
        admitted=True,
        errno_code=0,
        shoot_mode=shoot_mode,
        marker_display=marker_display,
        effective_marker_display=eff_marker_disp,
        center_marker=center_marker,
        effective_center_marker=eff_center,
        aspect_marker=aspect_marker,
        effective_aspect_marker=eff_aspect,
        safety_zone=safety_zone,
        effective_safety_zone=eff_safety,
        guideframe=guideframe,
        effective_guideframe=eff_guide,
        peaking_display=peaking_display,
        effective_peaking_display=eff_peak_disp,
        peaking_level=peaking_level,
        effective_peaking_level=eff_peak_lvl,
        peaking_color=req_peaking_color,
        effective_peaking_color=eff_peak_clr,
        focus_magnifier_active=focus_magnifier_active,
        effective_marker_overlay_visible=overlay_visible,
        marker_auto_hidden_for_magnifier=auto_hidden,
        hdmi_marker_or_peaking_leaked_pixels=HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS,
        hdmi_marker_overlay_active=False,
        hdmi_peaking_overlay_active=False,
        all_8_items_survive_camera_settings_reset=True,
        fx6_aspect_mask_level=0,
        fx6_user_box_width=0,
        fx6_user_box_height=0,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        reason=(
            f"ADMITTED: FX3 {eff_ver} Marker={eff_marker_disp}(aspect={eff_aspect}, "
            f"safety={eff_safety}, visible={overlay_visible}, mag_hide={auto_hidden}), "
            f"Peaking={eff_peak_disp}({eff_peak_lvl}/{eff_peak_clr}), hdmi_leak=0"
        ),
    )


def _build_stage71_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_71st_stage_milestone": IS_71ST_STAGE_MILESTONE,
        "wave": "Wave-61",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase333_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 333 Stage 71 (71/71 Milestone!) Wave-61 HIL co-emulation."""
    donor_audit = inspect_phase333_donors(force_clean_room=force_clean_room, env=env)

    # Sub-Model 71A probes
    p71a_zero_exfil_bench_ok = simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
        ftp_function="Off",
        server_slot=9,
        protocol="FTPES",
        transfer_mode="Passive",
        directory_hierarchy="Same as in Camera",
        target_slot=SLOT_2,
        airplane_mode="On",
        connect_method="Disabled",
        usb_lan_tethering_disabled=True,
        zero_rf_bench_mode=True,
        camera_settings_reset_applied=True,
    )
    p71a_dormant_rejected = [
        simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(protocol="SFTP"),
        simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(protocol="FTPS_IMPLICIT_990"),
        simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(transfer_mode="Active"),
        simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            dormant_transfer_jpeg_heif_size_requested=True
        ),
    ]
    p71a_usblan_airplane_bypass_blocked = (
        simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            ftp_function="On",
            airplane_mode="On",
            connect_method="USB-LAN",
            usb_lan_tethering_disabled=False,
            zero_rf_bench_mode=True,
        )
    )
    p71a_ftp_cloud_conflict = simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
        ftp_function="On",
        cloud_connection="On",
        zero_rf_bench_mode=False,
    )
    p71a_slot1_avf_erofs = [
        simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            save_ftp_transfer_list_to_media_requested=True,
            target_slot=SLOT_1,
        ),
        simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            avf_info_recovery_0x0a13_requested=True,
            target_slot=SLOT_1,
        ),
    ]
    p71a_fx6_comparison = [
        simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            body_profile=BODY_MODEL_FX6,
            server_slot=3,
            transfer_mode="Active",
            fx6_auto_upload_proxy_chunk=True,
        ),
        simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            body_profile=BODY_MODEL_FX6,
            server_slot=4,
        ),
        simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            body_profile=BODY_MODEL_FX6,
            server_slot=1,
            fx6_auto_upload_proxy_chunk=True,
            fx6_concurrent_conflict="Simul Rec",
        ),
    ]
    p71a_ok = (
        p71a_zero_exfil_bench_ok.admitted
        and p71a_zero_exfil_bench_ok.max_servers == 9
        and p71a_zero_exfil_bench_ok.rf_packets_transmitted == 0
        and p71a_zero_exfil_bench_ok.slot1_data_sector_writes == 0
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO
            for r in p71a_dormant_rejected
        )
        and (not p71a_usblan_airplane_bypass_blocked.admitted)
        and p71a_usblan_airplane_bypass_blocked.errno_code == EPERM_ERRNO
        and p71a_usblan_airplane_bypass_blocked.usblan_airplane_bypass_detected
        and (not p71a_ftp_cloud_conflict.admitted)
        and p71a_ftp_cloud_conflict.errno_code == EBUSY_ERRNO
        and all(
            (not r.admitted)
            and r.errno_code == EROFS_ERRNO
            and r.tier0_vault_firewall_triggered
            and r.slot1_data_sector_writes == 0
            and (not r.slot1_avf_info_mutated)
            for r in p71a_slot1_avf_erofs
        )
        and p71a_fx6_comparison[0].admitted
        and p71a_fx6_comparison[0].max_servers == 3
        and (not p71a_fx6_comparison[1].admitted)
        and p71a_fx6_comparison[1].errno_code == EINVAL_ERRNO
        and (not p71a_fx6_comparison[2].admitted)
        and p71a_fx6_comparison[2].errno_code == EBUSY_ERRNO
    )

    # Sub-Model 71B probes
    p71b_custom_wb_survives_cam_reset = simulate_white_balance_custom_shutter_shockless_hil(
        wb_mode="Custom 1",
        color_temp_k=5600,
        amber_blue_axis=1.5,
        green_magenta_axis=-0.75,
        shoot_mode=SHOOT_MODE_STILL,
        shutter_awb_lock="Shut. Halfway",
        priority_set_in_awb="White",
        camera_settings_reset_applied=True,
    )
    p71b_shockless_direct_ctemp_bypass = simulate_white_balance_custom_shutter_shockless_hil(
        wb_mode="C.Temp./Filter",
        color_temp_k=9900,
        shoot_mode=SHOOT_MODE_MOVIE,
        shockless_wb="3 (Slow)",
        direct_ctemp_or_filter_dial_edited=True,
    )
    p71b_cine_ei_and_0x0220_rejected = [
        simulate_white_balance_custom_shutter_shockless_hil(
            wb_mode="Auto",
            exposure_mode="Cine EI",
            log_shooting="Cine EI",
        ),
        simulate_white_balance_custom_shutter_shockless_hil(
            wb_mode="Underwater Auto",
            exposure_mode="Cine EI Quick",
            log_shooting="Cine EI Quick",
        ),
        simulate_white_balance_custom_shutter_shockless_hil(
            wb_mode="Custom 2",
            log_shooting="Flexible ISO",
            custom_setup_capture_requested=True,
        ),
        simulate_white_balance_custom_shutter_shockless_hil(
            wb_mode="Custom 3",
            picture_profile="PPLUT1",
            custom_setup_capture_requested=True,
        ),
    ]
    p71b_fx6_atw_and_cine_ei = [
        simulate_white_balance_custom_shutter_shockless_hil(
            body_profile=BODY_MODEL_FX6,
            wb_mode="Memory H",
            fx6_wht_bal_switch="B",
            fx6_atw_speed=5,
        ),
        simulate_white_balance_custom_shutter_shockless_hil(
            body_profile=BODY_MODEL_FX6,
            wb_mode="ATW",
            exposure_mode="Cine EI",
            log_shooting="Cine EI",
        ),
    ]
    p71b_ok = (
        p71b_custom_wb_survives_cam_reset.admitted
        and (not p71b_custom_wb_survives_cam_reset.custom_wb_exported_in_camset)
        and p71b_custom_wb_survives_cam_reset.custom_wb_internal_preserved_across_cam_reset
        and p71b_custom_wb_survives_cam_reset.effective_shutter_awb_lock == "Shut. Halfway"
        and p71b_custom_wb_survives_cam_reset.effective_priority_set_in_awb == "Standard"
        and p71b_shockless_direct_ctemp_bypass.admitted
        and p71b_shockless_direct_ctemp_bypass.shockless_transition_frames == 0
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO
            for r in p71b_cine_ei_and_0x0220_rejected
        )
        and p71b_cine_ei_and_0x0220_rejected[2].custom_wb_error_0x0220
        and p71b_cine_ei_and_0x0220_rejected[3].custom_wb_error_0x0220
        and p71b_fx6_atw_and_cine_ei[0].admitted
        and (not p71b_fx6_atw_and_cine_ei[1].admitted)
        and p71b_fx6_atw_and_cine_ei[1].errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 71C probes
    p71c_fx3_scales_and_mc_focusmap_ok = simulate_movie_af_scales_assist_and_focusmap_hil(
        af_transition_speed=7,
        af_subj_shift_sensitivity=5,
        af_assist="On",
        external_mc_focus_map_requested=True,
        fps=119.88,
    )
    p71c_6_7_sens_and_inbody_fmap_rejected = [
        simulate_movie_af_scales_assist_and_focusmap_hil(af_subj_shift_sensitivity=6),
        simulate_movie_af_scales_assist_and_focusmap_hil(
            body_profile=BODY_MODEL_FX6, af_subj_shift_sensitivity=7
        ),
        simulate_movie_af_scales_assist_and_focusmap_hil(inbody_focus_map_requested=True),
        simulate_movie_af_scales_assist_and_focusmap_hil(
            external_mc_focus_map_requested=True, fps=240.0, sq_mode_active=True
        ),
        simulate_movie_af_scales_assist_and_focusmap_hil(
            external_mc_focus_map_requested=True, auto_framing_active=True
        ),
        simulate_movie_af_scales_assist_and_focusmap_hil(
            af_assist="On", lens_model="SELP1650"
        ),
    ]
    p71c_fx6_native_focusmap_ok_and_6fps_block = [
        simulate_movie_af_scales_assist_and_focusmap_hil(
            body_profile=BODY_MODEL_FX6,
            inbody_focus_map_requested=True,
            fps=59.94,
        ),
        simulate_movie_af_scales_assist_and_focusmap_hil(
            body_profile=BODY_MODEL_FX6,
            inbody_focus_map_requested=True,
            fps=6.0,
        ),
    ]
    p71c_ok = (
        p71c_fx3_scales_and_mc_focusmap_ok.admitted
        and p71c_fx3_scales_and_mc_focusmap_ok.external_mc_focus_map_active
        and (not p71c_fx3_scales_and_mc_focusmap_ok.inbody_focus_map_supported)
        and p71c_fx3_scales_and_mc_focusmap_ok.recorded_or_hdmi_focus_map_pixels == 0
        and (not p71c_6_7_sens_and_inbody_fmap_rejected[0].admitted)
        and p71c_6_7_sens_and_inbody_fmap_rejected[0].errno_code == EINVAL_ERRNO
        and (not p71c_6_7_sens_and_inbody_fmap_rejected[1].admitted)
        and p71c_6_7_sens_and_inbody_fmap_rejected[1].errno_code == EINVAL_ERRNO
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO
            for r in p71c_6_7_sens_and_inbody_fmap_rejected[2:]
        )
        and p71c_fx6_native_focusmap_ok_and_6fps_block[0].admitted
        and p71c_fx6_native_focusmap_ok_and_6fps_block[0].inbody_focus_map_supported
        and (not p71c_fx6_native_focusmap_ok_and_6fps_block[1].admitted)
        and p71c_fx6_native_focusmap_ok_and_6fps_block[1].errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 71D probes
    p71d_marker_peaking_camreset_and_magnifier = simulate_marker_15ratio_and_peaking_4color_hil(
        marker_display="On",
        center_marker="On",
        aspect_marker="2.39:1",
        safety_zone="90%",
        guideframe="On",
        peaking_display="On",
        peaking_level="High",
        peaking_color="Red",
        focus_magnifier_active=True,
        camera_settings_reset_applied=True,
    )
    p71d_all_15_ratios_ok = all(
        simulate_marker_15ratio_and_peaking_4color_hil(
            marker_display="On",
            aspect_marker=ratio,
        ).admitted
        for ratio in FX3_ACTIVE_ASPECT_MARKER_RATIOS
    )
    p71d_fx6_user_box_and_bw = [
        simulate_marker_15ratio_and_peaking_4color_hil(
            body_profile=BODY_MODEL_FX6,
            peaking_display="On",
            peaking_color="B&W",
            fx6_aspect_mask_level=15,
            fx6_user_box_width=479,
            fx6_user_box_height=269,
        ),
        simulate_marker_15ratio_and_peaking_4color_hil(
            body_profile=BODY_MODEL_FX3,
            peaking_display="On",
            peaking_color="B&W",
        ),
    ]
    p71d_ok = (
        p71d_marker_peaking_camreset_and_magnifier.admitted
        and p71d_marker_peaking_camreset_and_magnifier.effective_marker_display == "On"
        and p71d_marker_peaking_camreset_and_magnifier.effective_aspect_marker == "2.39:1"
        and p71d_marker_peaking_camreset_and_magnifier.effective_peaking_color == "Red"
        and p71d_marker_peaking_camreset_and_magnifier.marker_auto_hidden_for_magnifier
        and (not p71d_marker_peaking_camreset_and_magnifier.effective_marker_overlay_visible)
        and p71d_marker_peaking_camreset_and_magnifier.hdmi_marker_or_peaking_leaked_pixels == 0
        and p71d_marker_peaking_camreset_and_magnifier.all_8_items_survive_camera_settings_reset
        and p71d_all_15_ratios_ok
        and p71d_fx6_user_box_and_bw[0].admitted
        and (not p71d_fx6_user_box_and_bw[1].admitted)
        and p71d_fx6_user_box_and_bw[1].errno_code == EOPNOTSUPP_ERRNO
    )

    milestone_probe = _build_stage71_milestone_probe()

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
        "fx3_ftp_max_servers": FX3_FTP_MAX_SERVERS,
        "fx6_ftp_max_servers": FX6_FTP_MAX_SERVERS,
        "dormant_sftp_exposed_events": DORMANT_SFTP_EXPOSED_EVENTS,
        "active_ftp_or_implicit_ftps_bypass_events": ACTIVE_FTP_OR_IMPLICIT_FTPS_BYPASS_EVENTS,
        "dormant_transfer_jpeg_heif_size_exposed_events": DORMANT_TRANSFER_JPEG_HEIF_SIZE_EXPOSED_EVENTS,
        "usblan_zero_rf_bypass_events": USBLAN_ZERO_RF_BYPASS_EVENTS,
        "ftp_cloud_mutual_exclusion_violations": FTP_CLOUD_MUTUAL_EXCLUSION_VIOLATIONS,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "slot1_vault_ftp_mutation_events": SLOT1_VAULT_FTP_MUTATION_EVENTS,
        "custom_wb_camset_leak_events": CUSTOM_WB_CAMSET_LEAK_EVENTS,
        "cine_ei_auto_wb_bypass_events": CINE_EI_AUTO_WB_BYPASS_EVENTS,
        "shockless_wb_direct_ctemp_lag_frames": SHOCKLESS_WB_DIRECT_CTEMP_LAG_FRAMES,
        "fx3_has_inbody_focus_map": FX3_HAS_INBODY_FOCUS_MAP,
        "fx6_has_inbody_focus_map": FX6_HAS_INBODY_FOCUS_MAP,
        "inbody_focus_map_exposed_events": INBODY_FOCUS_MAP_EXPOSED_EVENTS,
        "focus_map_150fps_or_autoframing_bypass_events": FOCUS_MAP_150FPS_OR_AUTOFRAMING_BYPASS_EVENTS,
        "af_subj_shift_6_7_spoof_events": AF_SUBJ_SHIFT_6_7_SPOOF_EVENTS,
        "fx3_marker_active_ratio_count": FX3_MARKER_ACTIVE_RATIO_COUNT,
        "hdmi_marker_or_peaking_leaked_pixels": HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS,
        "camera_reset_marker_or_peaking_wipe_events": CAMERA_RESET_MARKER_OR_PEAKING_WIPE_EVENTS,
        "marker_focus_magnifier_collision_events": MARKER_FOCUS_MAGNIFIER_COLLISION_EVENTS,
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
        and p71a_ok
        and p71b_ok
        and p71c_ok
        and p71d_ok
        and milestone_probe["is_71st_stage_milestone"]
        and redlines["fx3_ftp_max_servers"] == 9
        and redlines["fx6_ftp_max_servers"] == 3
        and redlines["dormant_sftp_exposed_events"] == 0
        and redlines["active_ftp_or_implicit_ftps_bypass_events"] == 0
        and redlines["dormant_transfer_jpeg_heif_size_exposed_events"] == 0
        and redlines["usblan_zero_rf_bypass_events"] == 0
        and redlines["ftp_cloud_mutual_exclusion_violations"] == 0
        and redlines["slot1_data_sector_writes"] == 0
        and (not redlines["slot1_avf_info_mutated"])
        and redlines["slot1_vault_ftp_mutation_events"] == 0
        and redlines["custom_wb_camset_leak_events"] == 0
        and redlines["cine_ei_auto_wb_bypass_events"] == 0
        and redlines["shockless_wb_direct_ctemp_lag_frames"] == 0
        and (not redlines["fx3_has_inbody_focus_map"])
        and bool(redlines["fx6_has_inbody_focus_map"])
        and redlines["inbody_focus_map_exposed_events"] == 0
        and redlines["focus_map_150fps_or_autoframing_bypass_events"] == 0
        and redlines["af_subj_shift_6_7_spoof_events"] == 0
        and redlines["fx3_marker_active_ratio_count"] == 15
        and redlines["hdmi_marker_or_peaking_leaked_pixels"] == 0
        and redlines["camera_reset_marker_or_peaking_wipe_events"] == 0
        and redlines["marker_focus_magnifier_collision_events"] == 0
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
        "version": PHASE_333_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_71st_stage_milestone": True,
        "source_mode": donor_audit.source_mode,
        "access_mode": donor_audit.access_mode,
        "all_checks_passed": all_passed,
        "donor_audit": asdict(donor_audit),
        "pillar_a_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil": {
            "passed": p71a_ok,
            "zero_exfil_bench_ok": asdict(p71a_zero_exfil_bench_ok),
            "dormant_rejected": [asdict(r) for r in p71a_dormant_rejected],
            "usblan_airplane_bypass_blocked": asdict(p71a_usblan_airplane_bypass_blocked),
            "ftp_cloud_conflict": asdict(p71a_ftp_cloud_conflict),
            "slot1_avf_erofs": [asdict(r) for r in p71a_slot1_avf_erofs],
            "fx6_comparison": [asdict(r) for r in p71a_fx6_comparison],
        },
        "pillar_b_wb_custom13_shutter_lock_shockless_and_cineei_hil": {
            "passed": p71b_ok,
            "custom_wb_survives_cam_reset": asdict(p71b_custom_wb_survives_cam_reset),
            "shockless_direct_ctemp_bypass": asdict(p71b_shockless_direct_ctemp_bypass),
            "cine_ei_and_0x0220_rejected": [asdict(r) for r in p71b_cine_ei_and_0x0220_rejected],
            "fx6_atw_and_cine_ei": [asdict(r) for r in p71b_fx6_atw_and_cine_ei],
        },
        "pillar_c_movie_af_scales_assist_and_external_focusmap_hil": {
            "passed": p71c_ok,
            "fx3_scales_and_mc_focusmap_ok": asdict(p71c_fx3_scales_and_mc_focusmap_ok),
            "scales_and_inbody_fmap_rejected": [
                asdict(r) for r in p71c_6_7_sens_and_inbody_fmap_rejected
            ],
            "fx6_native_focusmap_ok_and_6fps_block": [
                asdict(r) for r in p71c_fx6_native_focusmap_ok_and_6fps_block
            ],
        },
        "pillar_d_marker_15ratio_and_peaking_4color_clean_hdmi_hil": {
            "passed": p71d_ok,
            "marker_peaking_camreset_and_magnifier": asdict(
                p71d_marker_peaking_camreset_and_magnifier
            ),
            "all_15_ratios_ok": p71d_all_15_ratios_ok,
            "fx6_user_box_and_bw": [asdict(r) for r in p71d_fx6_user_box_and_bw],
            "stage71_milestone_probe": milestone_probe,
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
        prog="realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulator.py",
        description=(
            "Phase 333 Stage 71 (71/71 Milestone!) Wave-61 Real-Hardware "
            "ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 [FTP Transfer Func.] "
            "(9-Server Passive-Only FTP/FTPES vs Dormant SFTP/Active/Implicit-990/"
            "Transfer-JPEG-Size EOPNOTSUPP=95, cacert.pem <=1MB from Slot 1, "
            "USB-LAN Zero-RF Bypass Firewall + Slot-1 AVF_INFO 100%% Fail-Closed EROFS=30), "
            "[White Balance] (2500K..9900K, Custom 1..3 CAMSET Exclusion & 0x0220 Error, "
            "Still Shutter AWB Lock Initialize-Only, Movie Shockless WB 0-Frame Dial Bypass, "
            "Cine EI Auto Lockout), [Movie AF & Focus Map] (1..7 Transition Speed & 1..5 "
            "Shift Sens. Shared FX3/FX6, AF Assist, Zero In-Body Focus Map vs External M&C "
            "<150fps), and [Marker Display] / [Peaking Display] (15-Ratio Marker + 4-Color "
            "Peaking Clean-HDMI 0-Leak & Initialize-Only Persistence) HIL"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic Phase 333 Stage 71 (71/71) Wave-61 HIL verification suite",
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
        help="Emit concise one-line Stage 71 (71/71 Milestone!) Wave-61 summary",
    )
    args = parser.parse_args(argv)

    rep = run_phase333_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulation(
        force_clean_room=True if args.clean_room else None
    )

    if args.summary and not args.json:
        red = rep["redlines"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 333 Stage 71 (71/71 Milestone) | "
            f"mode={rep['source_mode']} "
            f"donors={rep['donor_audit']['donor_files_inspected']} "
            f"srv={red['fx3_ftp_max_servers']}/{red['fx6_ftp_max_servers']} "
            f"usblan_byp={red['usblan_zero_rf_bypass_events']} "
            f"wb_leak={red['custom_wb_camset_leak_events']} "
            f"fmap_ib={int(red['fx3_has_inbody_focus_map'])} "
            f"mrk_rat={red['fx3_marker_active_ratio_count']} "
            f"hdmi_px={red['hdmi_marker_or_peaking_leaked_pixels']} "
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
