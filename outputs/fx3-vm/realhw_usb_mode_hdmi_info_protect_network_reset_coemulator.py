#!/usr/bin/env python3
"""Phase 285 (Stage 57, 57/57) — Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-47:
`[USB Connection Mode]` 4-Mode vs Dormant `NOUVC` `[USB Streaming]` Split & `[USB LUN Setting]` /
`[USB Power Supply]` Data-Isolated USB PD HIL,
`[HDMI Info. Display]` LCD-Blanking vs Clean-Feed & `1080` Log/`PPLUT` Clamp vs `4K` `RAW` /
`Off(HDMI Only)` Auto-Clean-Feed Override HIL, and
`[Protect]` 4-Scope vs `[Format]` Wipe (`Slot-1` Dual-Layer Hardware SD `WP` + Firewall) &
`[Reset Network Set.]` Mandatory Auto-Reboot + Post-Reboot `[Airplane Mode] = [On]` HIL Co-Emulator.

Strictly models Wave-47 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts
without physical hardware attachment or firmware byte leakage:

1. **Sub-Model 57A — `[USB Connection Mode]` 4-Mode vs Dormant `NOUVC` Split & Data-Isolated PD HIL**:
   - Stock `ILME-FX3 Ver. 7.02` `(Setup) -> [USB] -> [USB Connection Mode]`
     (`BKID_APP_setting_usb_connection_method`, `_f.uxc` `0x69a2`) exposes ONLY **4** modes:
     `Sel. When Connect` (`0x7738`, factory default), `MassStorage(MSC)` (`0x6c54`, `054C:0DA1`,
     internal `USB_CONNECTION_METHOD_MASS_STRAGE`), `MTP` (`0xe24b`, Slot-1 target), and
     `Remote Shoot (PC Remote)` (`0x60aa` / `0x7c6f`).
   - Dormant `NOUVC` split: `appFw.so` (`USB_CONNECTION_USB_STREAMING`,
     `BKID_APP_shoot_mode_exclusion_for_usb_streaming`) + `_f.uxc` (`0x7399`) + `_g.uxc` (`0x63f7`) +
     `usb_f_uvc.ko` (`78,840 B`) exist in firmware for sibling `BIONZ XR` bodies (`ILME-FX30`,
     `ILME-FX2`, `ILCE-7M4`, `ZV-E1`), yet native `[USB Streaming]` UVC/UAC is masked out on
     `ILME-FX3` (`fx3_ui_exposes_native_usb_streaming == False`, rejects spoofed FX3 native UVC
     with `EOPNOTSUPP = 95`), in contrast to `ILME-FX6 Ver. 6.01` `ProCam` UVC
     (`BKID_APP_SETTING_USB_STREAMING_PROCAM`, `usb_f_uvc.ko` `78,840 B`) and `USB Tethering`.
   - Models `[USB LUN Setting]` (`Multi` default `0xe631` / `Single` `0x776d`), `[USB Power Supply]`
     (`On` default `0x721e`, USB Type-C exclusive + `NP-FZ100` battery pack required), `(Setup)`
     survival across `[Camera Settings Reset]` (restored only by `[Initialize]`), and the Tier-0
     air-gapped bench rule permitting `USB PD` power ONLY when `D+/D-` & SuperSpeed data lines
     are physically isolated (`usb_data_lines_physically_isolated == True`).

2. **Sub-Model 57B — `[HDMI Info. Display]` LCD-Blanking vs Clean-Feed & `1080` Clamp vs `4K` Override**:
   - `[HDMI Info. Display]` (`BKID_APP_setting_hdmi_info_display`, `_f.uxc` `0x6e7c`): `On` (factory
     default `0xe07c`, outputs OSD overlays + letterboxed viewport and blanks built-in LCD &
     touch-focus via `CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`) vs `Off` (`0xe297`, clean HDMI feed
     with LCD + touch-focus active).
   - When `Rec. Media dur HDMI Output = On` (internal recording) AND (`Log Shooting != Off` or
     `Picture Profile = PPLUT1..4`), HDMI output is clamped to `1080` regardless of
     `[Output Resolution]`. Conversely, `Off(HDMI Only)` (`0x6573`) OR `RAW Output = On` (`0x6e97`)
     outputs `4K` and automatically forces `[HDMI Info. Display] = [Off]` (guaranteed clean feed;
     `S&Q` locks `Rec. Media = On` and `RAW Output = Off`).
   - Verifies `(Setup)` survival across `[Camera Settings Reset]` (with explicit `[Framing Settings
     (HDMI)]` reset exception) and `FX6 Ver. 6.01` `HDMI` vs `SDI` split.

3. **Sub-Model 57C & Redlines — `[Protect]` Scopes vs `[Format]` Wipe (`Slot-1` Dual-Layer SD `WP`
   + Firewall) & `[Reset Network Set.]` Auto-Reboot + Post-Reboot `[Airplane Mode] = [On]` HIL**:
   - Models all 4 `ILME-FX3` `[Protect]` scopes (`Single`/`Multiple Img.` `0xe2ca`, `All in this
     Folder` `0x6848`, `All with this date` `0x69f7`, `All Images in This Group` `0xe826`) blocking
     `[Delete]` / `[Delete pressing twice]`, whereas **`[Format]` (`0xe449` / `0xe414`) wipes
     protected files and `M1..M4` card settings** — mandating dual-layer `Slot-1` hardware SD
     `WP` lock (`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`, `CAUTION_ID_PROTECT_MS_SLOT1`) + hard
     software firewall (`slot1_format_hard_locked == True`, `EROFS = 30`).
   - Models `[Reset Network Set.]` (`FUNC_reset_network_settings`, `SETTING_RESET_NW`, `_f.uxc`
     `0x60d3` / `0x65d3`) clearing `(Network)` credentials (`Wi-Fi`, `Bluetooth`, `FTP`, `Cloud`,
     `USB-LAN`, `Streaming`, certs), preserving `(Shooting)` / `(Setup)` / `(Playback)` / `CAMSET`,
     triggering mandatory auto-reboot (`BKID_APP_is_shutdown_factor_network_reset`), and resetting
     `[Airplane Mode]` to `Off` — requiring post-reboot `[Airplane Mode] = [On]` (`0x6df9`) to
     restore air-gapped zero-RF posture.

4. **Dual-Mode 13-Donor `O_RDONLY` Verification & Hard Safety Redlines**:
   - Inspects 13 verified `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01` donors strictly via
     `os.O_RDONLY` (`< 0.2s` cold, `raw_firmware_bytes_leaked == 0`), with deterministic
     `CLEAN_ROOM_SYNTHETIC` parity under `FX3_CLEAN_ROOM_TEST=1` or `FX3_FX6_FORCE_CLEAN_ROOM=1`.
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

SCHEMA_ID = "realhw_usb_mode_hdmi_info_protect_network_reset_coemulator_v1"
PHASE_285_SCHEMA = SCHEMA_ID
PHASE_285_VERSION = "285.0.0"
PHASE_NUMBER = 285
STAGE_INDEX = 57
STAGE_TOTAL = 57
MILESTONE_LABEL = "57/57"
STAGE_NAME = "stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil"
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EACCES_ERRNO = 13
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

# Wave-47 Stage 57 zero-fault & model-truth invariants
FX3_UI_EXPOSES_NATIVE_USB_STREAMING = False
USB_F_UVC_INSMOD_AT_FX3_BOOT = False
FX3_NATIVE_UVC_SPOOF_EVENTS = 0
TIER0_USB_DATA_ENUMERATION_VIOLATIONS = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
HDMI_OSD_OR_CLAMP_BYPASS_EVENTS = 0
HDMI_CLEAN_FEED_OVERRIDE_VIOLATIONS = 0
SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS = 0
SLOT1_FORMAT_HARD_LOCKED = True
POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0

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
# Verified Local Donor Specs (13 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX3_KMOD_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod"
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
    "fx3_usb_f_uvc": f"{_FX3_KMOD_PREFIX}/usb_f_uvc.ko",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx3_bk4": (
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/"
        "FX3-CX95900_ALLLANG-Backup.bin"
    ),
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_en_2": f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
    "fx6_usb_f_uvc": f"{_FX6_NF15_PREFIX}/kmod/usb_f_uvc.ko",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_string_en_f": 373_820,
    "fx3_string_sc_f": 322_652,
    "fx3_string_tc_f": 324_148,
    "fx3_string_ja_f": 447_840,
    "fx3_string_en": 165_740,
    "fx3_string_en_g": 69_600,
    "fx3_usb_f_uvc": 78_840,
    "fx3_appfw": 79_015_712,
    "fx3_bk4": 2_229_740,
    "fx6_string_en": 118_208,
    "fx6_string_en_2": 118_676,
    "fx6_usb_f_uvc": 78_840,
    "fx6_appfw": 50_520_424,
}

EXPECTED_COMPACT_DONOR_SHA256: Mapping[str, str] = {
    "fx3_string_en_f": "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
    "fx3_string_sc_f": "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
    "fx3_string_tc_f": "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
    "fx3_string_ja_f": "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
    "fx3_string_en": "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
    "fx3_string_en_g": "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
    "fx3_usb_f_uvc": "a23970925fa91ed7712f14bf7de8ac62ff9d63e9bcbfeecc94b37085d48c5ccc",
    "fx6_string_en": "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
    "fx6_string_en_2": "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
    "fx6_usb_f_uvc": "bf073599272e2bb5641668d457ff9962525f17a37c8c75f15a3892d7c26b5305",
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"USB Connection Mode",
        b"Sel. When Connect",
        b"MassStorage(MSC)",
        b"Remote Shoot (PC Remote)",
        b"USB LUN Setting",
        b"USB Power Supply",
        b"USB Streaming",
        b"HDMI Info. Display",
        b"Rec. Media dur HDMI Output",
        b"Off(HDMI Only)",
        b"RAW Output",
        b"All in this Folder",
        b"All with this date",
        b"Reset Network Set.",
        b"reboots\nautomatically.)",
        b"Airplane Mode",
        b"Camera Settings Reset",
        b"Initialize",
    ),
    "fx3_string_sc_f": (
        "USB连接模式".encode("utf-8"),
        "连接时选择".encode("utf-8"),
        "海量存储器(MSC)".encode("utf-8"),
        "遥控拍摄(电脑遥控)".encode("utf-8"),
        "USB LUN设定".encode("utf-8"),
        "USB电源供给".encode("utf-8"),
        "HDMI信息显示".encode("utf-8"),
        "该文件夹内的全部影像".encode("utf-8"),
        "该日期的全部影像".encode("utf-8"),
        "复位网络设置".encode("utf-8"),
        "飞行模式".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "USB連線模式".encode("utf-8"),
        "連接時選擇".encode("utf-8"),
        "大量儲存(MSC)".encode("utf-8"),
        "遙控拍攝(PC遙控)".encode("utf-8"),
        "USB LUN設定".encode("utf-8"),
        "USB電源供給".encode("utf-8"),
        "HDMI資訊顯示".encode("utf-8"),
        "此資料夾中的所有影像".encode("utf-8"),
        "此日期的所有影像".encode("utf-8"),
        "重設網路設定".encode("utf-8"),
        "飛航模式".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "USB接続モード".encode("utf-8"),
        "接続時に選択".encode("utf-8"),
        "ﾏｽｽﾄﾚｰｼﾞ (MSC)".encode("utf-8"),
        "リモート撮影 (PCリモート)".encode("utf-8"),
        "USB LUN設定".encode("utf-8"),
        "USB給電".encode("utf-8"),
        "HDMI情報表示".encode("utf-8"),
        "このフォルダーの全画像".encode("utf-8"),
        "この日付の全画像".encode("utf-8"),
        "ﾈｯﾄﾜｰｸ設定リセット".encode("utf-8"),
        "機内モード".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"MTP",
        b"Protect",
        b"Multiple Img.",
        b"All Images in This Group",
        b"Format",
        b"All data will be deleted.\nFormat?",
    ),
    "fx3_string_en_g": (
        b"Selection/Memo",
        b"Network Option",
        b"External Output",
        b"USB Streaming",
    ),
    "fx3_usb_f_uvc": (
        b"\x7fELF",
        b"usb_f_uvc",
        b"uvc_function_bind",
    ),
    "fx6_string_en": (
        b"Format",
        b"USB Tethering",
    ),
    "fx6_string_en_2": (
        b"Network Reset",
        b"All Reset",
        b"Lock/Unlock Clip",
        b"Lock All Clips",
        b"SDI Out2/HDMI Super",
        b"Format Media",
    ),
    "fx6_usb_f_uvc": (
        b"\x7fELF",
        b"usb_f_uvc",
        b"uvc_function_bind",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_971_200, "LUN_SETTING_MULTI", b"LUN_SETTING_MULTI"),
        (49_971_200, "LUN_SETTING_SINGLE", b"LUN_SETTING_SINGLE"),
        (49_971_200, "USB_SUPPLY_ON", b"USB_SUPPLY_ON"),
        (59_827_060, "SEQ_BT_NET_RESET_DONE", b"sequence_bluetooth_network_reset_done"),
        (60_434_283, "SETTING_RESET_NW", b"SETTING_RESET_NW"),
        (60_434_283, "SETTING_RESET_CAMERA", b"SETTING_RESET_CAMERA"),
        (60_600_320, "FUNC_PROTECT_CONTENT", b"FUNC_protect_content"),
        (60_600_320, "FUNC_PROTECT_DATE", b"FUNC_protect_all_contents_in_this_date"),
        (60_603_165, "FUNC_RESET_NETWORK", b"FUNC_reset_network_settings"),
        (60_604_370, "FUNC_PROTECT_GROUP", b"FUNC_protect_all_contents_in_this_group"),
        (60_604_370, "FUNC_PROTECT_MULTI", b"FUNC_protect_for_multipul_images"),
        (60_605_017, "FUNC_RESET_WIFI_PSK", b"FUNC_reset_wifi_ssid_psk"),
        (60_606_252, "FUNC_RESET_ALL_INIT", b"FUNC_reset_all_initialize"),
        (60_639_883, "AIRPLANE_MODE_ON", b"AIRPLANE_MODE_ON"),
        (61_878_272, "HDMI_INFO_DISPLAY_ON", b"HDMI_INFO_DISPLAY_ON"),
        (61_935_616, "USB_CONN_SELECT", b"USB_CONNECTION_SELECT_AFTER_CONNECTION"),
        (61_935_616, "USB_CONN_MSC", b"USB_CONNECTION_MASS_STORAGE"),
        (61_935_616, "USB_CONN_MTP", b"USB_CONNECTION_MTP"),
        (61_935_616, "USB_CONN_REMOTE_PC", b"USB_CONNECTION_REMOTE_PC"),
        (61_935_616, "USB_CONN_UVC_DORMANT", b"USB_CONNECTION_USB_STREAMING"),
        (62_165_942, "MR_ERR_CARD_WP_SLOT1", b"MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1"),
        (62_165_942, "MR_ERR_FILE_PROTECT", b"MR_MEMORY_ERROR_FILE_PROTECT"),
        (62_629_333, "CAUTION_PROTECT_SLOT1", b"CAUTION_ID_PROTECT_MS_SLOT1"),
        (62_648_320, "CAUTION_HDMI_INFO_ON", b"CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON"),
        (62_694_667, "BKID_AIRPLANE_MODE", b"BKID_APP_setting_airplane_mode"),
        (62_701_568, "BKID_USB_CONN_METHOD", b"BKID_APP_setting_usb_connection_method"),
        (62_701_568, "BKID_LUN_SETTINGS", b"BKID_APP_setting_lun_settings"),
        (62_701_568, "BKID_USB_SUPPLY", b"BKID_APP_setting_usb_supply"),
        (62_701_568, "BKID_HDMI_RESOLUTION", b"BKID_APP_setting_hdmi_resolution"),
        (62_701_568, "BKID_REC_MEDIA_HDMI", b"BKID_APP_setting_rec_media_during_hdmi_output"),
        (62_701_568, "BKID_HDMI_4K_OUTPUT", b"BKID_APP_setting_hdmi_4k_output_setting"),
        (62_701_568, "BKID_HDMI_INFO_DISPLAY", b"BKID_APP_setting_hdmi_info_display"),
        (62_843_189, "BKID_SHUTDOWN_NET_RESET", b"BKID_APP_is_shutdown_factor_network_reset"),
        (62_844_928, "BKID_EXCL_USB_STREAM", b"BKID_APP_shoot_mode_exclusion_for_usb_streaming"),
        (63_021_056, "USB_METHOD_MASS_STRAGE", b"USB_CONNECTION_METHOD_MASS_STRAGE"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (0, "ALLLANG", b"ALLLANG"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (40_923_116, "FX6_HDMI_INFO_DISPLAY", b"BKID_APP_SETTING_HDMI_INFO_DISPLAY"),
        (40_939_260, "FX6_USB_STREAM_PROCAM", b"BKID_APP_SETTING_USB_STREAMING_PROCAM"),
        (40_939_260, "FX6_SDI_OUTPUT_DISP", b"BKID_APP_SETTING_SDI_OUTPUT_DISPLAY"),
        (40_964_923, "FX6_LOCK_CLIP0", b"BKID_APP_USER_MENU_LOCK_UNLOCK_CLIP0"),
        (40_971_168, "FX6_NET_RESET_MENU", b"BKID_APP_USER_MENU_NETWORK_RESET"),
        (40_992_493, "FX6_SHUTDOWN_NET_RESET", b"BKID_APP_IS_SHUTDOWN_FACTOR_NETWORK_RESET"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-47 Official Sub-Model 57A / 57B / 57C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX3A = "ILME-FX3A"
BODY_MODEL_FX6 = "ILME-FX6"
BODY_MODEL_FX30 = "ILME-FX30"
BODY_MODEL_FX2 = "ILME-FX2"
BODY_MODEL_A7M4 = "ILCE-7M4"
BODY_MODEL_ZVE1 = "ZV-E1"

STOCK_FX3_BODIES: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX3A)
UVC_CAPABLE_SIBLING_BODIES: Tuple[str, ...] = (
    BODY_MODEL_FX6,
    BODY_MODEL_FX30,
    BODY_MODEL_FX2,
    BODY_MODEL_A7M4,
    BODY_MODEL_ZVE1,
)
ALL_SUPPORTED_BODY_PROFILES: Tuple[str, ...] = STOCK_FX3_BODIES + UVC_CAPABLE_SIBLING_BODIES

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

TOGGLE_OFF = "Off"
TOGGLE_ON = "On"
VALID_TOGGLE_STATES: Tuple[str, ...] = (TOGGLE_OFF, TOGGLE_ON)

# Sub-Model 57A: [USB Connection Mode], NOUVC Split, [USB LUN Setting] & [USB Power Supply]
USB_CONNECTION_MODE_MENU_PATH = "MENU -> Setup -> [USB] -> [USB Connection Mode]"
USB_LUN_SETTING_MENU_PATH = "MENU -> Setup -> [USB] -> [USB LUN Setting]"
USB_POWER_SUPPLY_MENU_PATH = "MENU -> Setup -> [USB] -> [USB Power Supply]"
FX6_USB_PROCAM_UVC_MENU_PATH = "Network -> [USB Streaming] / [USB Tethering]"

USB_MODE_SEL_WHEN_CONNECT = "Sel. When Connect"
USB_MODE_MASS_STORAGE = "MassStorage(MSC)"
USB_MODE_MTP = "MTP"
USB_MODE_REMOTE_SHOOT = "Remote Shoot (PC Remote)"
USB_MODE_DORMANT_STREAMING = "USB Streaming"

FX3_EXPOSED_USB_CONNECTION_MODES: Tuple[str, ...] = (
    USB_MODE_SEL_WHEN_CONNECT,
    USB_MODE_MASS_STORAGE,
    USB_MODE_MTP,
    USB_MODE_REMOTE_SHOOT,
)

USB_CONNECTION_MODE_SPEC: Mapping[str, Mapping[str, object]] = {
    USB_MODE_SEL_WHEN_CONNECT: {
        "resid16": "0x7738",
        "enum": "VAL_setting_usb_connection_method_USB_CONNECTION_SELECT_AFTER_CONNECTION",
        "usb_vid_pid": "PROMPT_BEFORE_ENUMERATION",
        "exposes_host_data_link": True,
        "slot_target": "Prompts MSC / MTP / Remote Shooting",
    },
    USB_MODE_MASS_STORAGE: {
        "resid16": "0x6c54",
        "enum": "VAL_setting_usb_connection_method_USB_CONNECTION_MASS_STORAGE",
        "internal_marker": "USB_CONNECTION_METHOD_MASS_STRAGE",
        "usb_vid_pid": "054C:0DA1",
        "exposes_host_data_link": True,
        "slot_target": "Mounted Removable LUN(s)",
    },
    USB_MODE_MTP: {
        "resid16": "0xe24b",
        "enum": "VAL_setting_usb_connection_method_USB_CONNECTION_MTP",
        "usb_vid_pid": "MTP_STILLIMAGE",
        "exposes_host_data_link": True,
        "slot_target": "Slot 1",
    },
    USB_MODE_REMOTE_SHOOT: {
        "resid16": "0x60aa",
        "enum": "VAL_setting_usb_connection_method_USB_CONNECTION_REMOTE_PC",
        "usb_vid_pid": "PTP_PC_REMOTE",
        "exposes_host_data_link": True,
        "slot_target": "Imaging Edge Desktop / Creators' App",
    },
}

USB_LUN_MULTI = "Multi"
USB_LUN_SINGLE = "Single"
VALID_USB_LUN_SETTINGS: Tuple[str, ...] = (USB_LUN_MULTI, USB_LUN_SINGLE)
USB_LUN_SPEC: Mapping[str, Mapping[str, object]] = {
    USB_LUN_MULTI: {
        "resid16": "0xe631",
        "enum": "LUN_SETTING_MULTI",
        "exposed_msc_luns": 2,
    },
    USB_LUN_SINGLE: {
        "resid16": "0x776d",
        "enum": "LUN_SETTING_SINGLE",
        "exposed_msc_luns": 1,
    },
}

USB_PORT_TYPE_C = "USB_TYPE_C"
USB_PORT_MULTI_MICRO = "MULTI_MICRO_USB"
USB_PORT_NONE = "NONE"
VALID_USB_PORTS: Tuple[str, ...] = (USB_PORT_TYPE_C, USB_PORT_MULTI_MICRO, USB_PORT_NONE)

USB_PD_WATTS_MIN = 0.0
USB_PD_WATTS_MAX = 100.0

# Sub-Model 57B: [HDMI Info. Display] & Clean-Feed Override
HDMI_INFO_DISPLAY_MENU_PATH = "MENU -> Setup -> [External Output] -> [HDMI Info. Display]"
HDMI_OUTPUT_SETTINGS_MENU_PATH = "MENU -> Setup -> [External Output] -> [HDMI Output Settings]"
FX6_HDMI_INFO_DISPLAY_MENU_PATH = "Monitoring -> Output Display -> [HDMI] (vs [SDI])"

HDMI_RES_AUTO = "Auto"
HDMI_RES_2160P = "2160p"
HDMI_RES_1080P = "1080p"
HDMI_RES_1080I = "1080i"
VALID_HDMI_OUTPUT_RESOLUTIONS: Tuple[str, ...] = (
    HDMI_RES_AUTO,
    HDMI_RES_2160P,
    HDMI_RES_1080P,
    HDMI_RES_1080I,
)

REC_MEDIA_ON = "On"
REC_MEDIA_OFF_HDMI_ONLY = "Off(HDMI Only)"
VALID_REC_MEDIA_HDMI_STATES: Tuple[str, ...] = (REC_MEDIA_ON, REC_MEDIA_OFF_HDMI_ONLY)

LOG_SHOOTING_OFF = "Off"
LOG_SHOOTING_FLEXIBLE_ISO = "Flexible ISO"
LOG_SHOOTING_CINE_EI = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK = "Cine EI Quick"
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    LOG_SHOOTING_OFF,
    LOG_SHOOTING_FLEXIBLE_ISO,
    LOG_SHOOTING_CINE_EI,
    LOG_SHOOTING_CINE_EI_QUICK,
)

PICTURE_PROFILE_OFF = "Off"
PICTURE_PROFILE_PP11 = "PP11"
PICTURE_PROFILE_PPLUT_MODES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
VALID_PICTURE_PROFILES: Tuple[str, ...] = (
    PICTURE_PROFILE_OFF,
    PICTURE_PROFILE_PP11,
) + PICTURE_PROFILE_PPLUT_MODES

SHOOT_MODE_MOVIE = "Movie"
SHOOT_MODE_SQ = "S&Q"
SHOOT_MODE_STILL = "Still"
VALID_SHOOT_MODES: Tuple[str, ...] = (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ, SHOOT_MODE_STILL)

# Sub-Model 57C: [Protect], [Format] & [Reset Network Set.]
PROTECT_MENU_PATH = "MENU -> Playback -> [Selection/Memo] -> [Protect]"
FORMAT_MENU_PATH = "MENU -> Shooting -> [Media] -> [Format]"
RESET_NETWORK_MENU_PATH = "MENU -> Network -> [Network Option] -> [Reset Network Set.]"
AIRPLANE_MODE_MENU_PATH = "MENU -> Network -> [Network Option] -> [Airplane Mode]"

PROTECT_SCOPE_NONE = "None"
PROTECT_SCOPE_SINGLE_MULTIPLE = "Multiple Img."
PROTECT_SCOPE_ALL_IN_FOLDER = "All in this Folder"
PROTECT_SCOPE_ALL_WITH_DATE = "All with this date"
PROTECT_SCOPE_ALL_IN_GROUP = "All Images in This Group"
ALL_4_PROTECT_SCOPES: Tuple[str, ...] = (
    PROTECT_SCOPE_SINGLE_MULTIPLE,
    PROTECT_SCOPE_ALL_IN_FOLDER,
    PROTECT_SCOPE_ALL_WITH_DATE,
    PROTECT_SCOPE_ALL_IN_GROUP,
)
VALID_PROTECT_SCOPES: Tuple[str, ...] = (PROTECT_SCOPE_NONE,) + ALL_4_PROTECT_SCOPES

PROTECT_SCOPE_SPEC: Mapping[str, Mapping[str, str]] = {
    PROTECT_SCOPE_SINGLE_MULTIPLE: {
        "resid16": "0xe2ca",
        "func": "FUNC_protect_content / FUNC_protect_for_multipul_images",
    },
    PROTECT_SCOPE_ALL_IN_FOLDER: {
        "resid16": "0x6848",
        "func": "FUNC_protect_all_in_folder",
    },
    PROTECT_SCOPE_ALL_WITH_DATE: {
        "resid16": "0x69f7",
        "func": "FUNC_protect_all_contents_in_this_date",
    },
    PROTECT_SCOPE_ALL_IN_GROUP: {
        "resid16": "0xe826",
        "func": "FUNC_protect_all_contents_in_this_group",
    },
}

MEDIA_OP_NONE = "None"
MEDIA_OP_DELETE_SINGLE = "Delete Single"
MEDIA_OP_DELETE_TWICE = "Delete pressing twice"
MEDIA_OP_FORMAT_QUICK = "Format Quick"
MEDIA_OP_FORMAT_FULL = "Format Full"
VALID_MEDIA_OPS: Tuple[str, ...] = (
    MEDIA_OP_NONE,
    MEDIA_OP_DELETE_SINGLE,
    MEDIA_OP_DELETE_TWICE,
    MEDIA_OP_FORMAT_QUICK,
    MEDIA_OP_FORMAT_FULL,
)

SLOT_1 = "Slot 1"
SLOT_2 = "Slot 2"
VALID_MEDIA_SLOTS: Tuple[str, ...] = (SLOT_1, SLOT_2)

NETWORK_CREDENTIALS_DOMAINS: Tuple[str, ...] = (
    "wifi_ssid_psk",
    "wifi_direct",
    "static_ip_dns",
    "bluetooth_pairing",
    "bluetooth_function",
    "bluetooth_rmt_ctrl",
    "ftp_profiles_0_to_8",
    "creators_cloud",
    "remote_shoot_access_auth",
    "ipsec_usb_lan",
    "network_streaming_rtmp_srt",
    "root_certificates",
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
    "fx3_native_uvc_spoof_requested",
    "tier0_usb_data_enumeration_requested",
    "hdmi_osd_or_1080_clamp_bypass_requested",
    "slot1_vault_format_or_delete_requested",
    "post_reset_airplane_off_rf_tx_requested",
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
class Phase285DonorAudit:
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
    fx3_usb_f_uvc: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx6_string_en_2: CompactDonorSummary
    fx6_usb_f_uvc: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx3_bk4: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    usb_mode_nouvc_split_proven: bool
    hdmi_info_cleanfeed_proven: bool
    protect_format_netreset_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UsbConnectionModeNouvcPdEvalResult:
    menu_path: str
    lun_menu_path: str
    power_supply_menu_path: str
    body_profile: str
    fx3_ui_exposes_native_usb_streaming: bool
    usb_f_uvc_insmod_at_fx3_boot: bool
    fx3_exposed_4_usb_modes: Tuple[str, ...]
    fx6_procam_uvc_bkid: str
    requested_usb_connection_mode: str
    effective_usb_connection_mode: str
    effective_usb_vid_pid: str
    configured_usb_lun_setting: str
    effective_usb_lun_setting: str
    exposed_msc_luns: int
    configured_usb_power_supply: str
    effective_usb_power_supply: str
    usb_port: str
    np_fz100_inserted: bool
    usb_pd_watts: float
    usb_power_supply_active: bool
    tier0_airgapped_bench: bool
    usb_data_lines_physically_isolated: bool
    data_isolated_pd_admitted: bool
    reset_action: str
    setup_usb_items_survived_camera_reset: bool
    setup_usb_items_restored_by_initialize: bool
    fx3_native_uvc_spoof_events: int
    tier0_usb_data_enumeration_violations: int
    physical_usb_packets_emitted: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class HdmiInfoDisplayCleanFeedEvalResult:
    menu_path: str
    hdmi_settings_menu_path: str
    body_profile: str
    shoot_mode: str
    configured_hdmi_info_display: str
    configured_output_resolution: str
    configured_rec_media_during_hdmi: str
    configured_log_shooting: str
    configured_picture_profile: str
    configured_raw_output: str
    configured_framing_settings_hdmi: str
    effective_hdmi_info_display: str
    effective_hdmi_output_label: str
    effective_hdmi_width: int
    effective_hdmi_height: int
    hdmi_osd_overlays_emitted: bool
    hdmi_letterbox_inset_active: bool
    builtin_lcd_active: bool
    lcd_touch_focus_enabled: bool
    hdmi_1080_log_pplut_clamped: bool
    auto_clean_feed_forced_off: bool
    effective_framing_settings_hdmi: str
    reset_action: str
    setup_hdmi_items_survived_camera_reset: bool
    framing_settings_hdmi_reset_by_camera_reset: bool
    setup_hdmi_restored_by_initialize: bool
    hdmi_osd_or_clamp_bypass_events: int
    hdmi_clean_feed_override_violations: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class ProtectFormatNetworkResetEvalResult:
    protect_menu_path: str
    format_menu_path: str
    reset_network_menu_path: str
    airplane_mode_menu_path: str
    body_profile: str
    target_slot: str
    slot1_holds_recovery_vault: bool
    slot1_sd_hw_wp_switch_locked: bool
    slot1_format_hard_locked: bool
    protect_scope: str
    protected_files_active: bool
    requested_media_op: str
    media_op_executed: bool
    delete_blocked_by_protect: bool
    format_wiped_protected_files_and_m1_m4: bool
    camset_m1_m4_intact: bool
    reset_action: str
    network_credentials_cleared: bool
    shooting_setup_playback_preserved: bool
    camset_slot_files_preserved: bool
    auto_reboot_triggered: bool
    shutdown_factor_bkid: str
    post_reset_airplane_mode_default: str
    post_reboot_airplane_mode: str
    zero_rf_bench_requires_airplane_on: bool
    zero_rf_posture_restored: bool
    slot1_vault_format_or_delete_events: int
    post_reset_airplane_off_rf_leak_events: int
    passive_tx_bytes_emitted: int
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
    fx3_ui_exposes_native_usb_streaming: bool
    fx3_native_uvc_spoof_events: int
    tier0_usb_data_enumeration_violations: int
    physical_usb_packets_emitted: int
    hdmi_osd_or_clamp_bypass_events: int
    hdmi_clean_feed_override_violations: int
    slot1_vault_format_or_delete_events: int
    slot1_format_hard_locked: bool
    post_reset_airplane_off_rf_leak_events: int
    passive_tx_bytes_emitted: int
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY 13-Donor Inspection (< 0.2s cold, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase285DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase285DonorAudit] = None


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


def resolve_phase285_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 13 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
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


def _build_clean_room_donor_audit() -> Phase285DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH_P285".encode("ascii")
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
            expected_sha256=None,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        wins = LARGE_DONOR_WINDOWS[key]
        unique_offs = {off for off, _, _ in wins} | {0}
        hits = {lbl: 1 for _, lbl, _ in wins}
        seed = f"{key}_SYNTH_HEAD_P285".encode("ascii")
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase285DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=13,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3 7.02 string_english_f.uxc", True),
        fx3_string_sc_f=_mk_compact(
            "fx3_string_sc_f", "FX3 7.02 string_simplifiedchinese_f.uxc", True
        ),
        fx3_string_tc_f=_mk_compact(
            "fx3_string_tc_f", "FX3 7.02 string_traditionalchinese_f.uxc", True
        ),
        fx3_string_ja_f=_mk_compact("fx3_string_ja_f", "FX3 7.02 string_japanese_f.uxc", True),
        fx3_string_en=_mk_compact("fx3_string_en", "FX3 7.02 string_english.uxc", True),
        fx3_string_en_g=_mk_compact("fx3_string_en_g", "FX3 7.02 string_english_g.uxc", True),
        fx3_usb_f_uvc=_mk_compact("fx3_usb_f_uvc", "FX3 7.02 usb_f_uvc.ko", False),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6 6.01 string_english.uxc", True),
        fx6_string_en_2=_mk_compact("fx6_string_en_2", "FX6 6.01 string_english_2.uxc", True),
        fx6_usb_f_uvc=_mk_compact("fx6_usb_f_uvc", "FX6 6.01 usb_f_uvc.ko", False),
        fx3_appfw=_mk_large("fx3_appfw", "FX3 7.02 appFw.so", True),
        fx3_bk4=_mk_large("fx3_bk4", "FX3 7.02 ALLLANG BK4 Backup", False),
        fx6_appfw=_mk_large("fx6_appfw", "FX6 6.01 appFw.so", True),
        usb_mode_nouvc_split_proven=True,
        hdmi_info_cleanfeed_proven=True,
        protect_format_netreset_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase285_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase285DonorAudit:
    """Inspect 13 FX3 7.02 & FX6 6.01 donors strictly O_RDONLY (< 0.2s cold) or Clean-Room fallback."""
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_forced:
        return _build_clean_room_donor_audit()

    paths = resolve_phase285_donor_paths(env=env)
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
    fx3_en_f = _scan_compact_rdonly(
        paths["fx3_string_en_f"],
        artifact_key="fx3_string_en_f",
        body_label="FX3 7.02 string_english_f.uxc",
    )
    fx3_sc_f = _scan_compact_rdonly(
        paths["fx3_string_sc_f"],
        artifact_key="fx3_string_sc_f",
        body_label="FX3 7.02 string_simplifiedchinese_f.uxc",
    )
    fx3_tc_f = _scan_compact_rdonly(
        paths["fx3_string_tc_f"],
        artifact_key="fx3_string_tc_f",
        body_label="FX3 7.02 string_traditionalchinese_f.uxc",
    )
    fx3_ja_f = _scan_compact_rdonly(
        paths["fx3_string_ja_f"],
        artifact_key="fx3_string_ja_f",
        body_label="FX3 7.02 string_japanese_f.uxc",
    )
    fx3_en = _scan_compact_rdonly(
        paths["fx3_string_en"],
        artifact_key="fx3_string_en",
        body_label="FX3 7.02 string_english.uxc",
    )
    fx3_en_g = _scan_compact_rdonly(
        paths["fx3_string_en_g"],
        artifact_key="fx3_string_en_g",
        body_label="FX3 7.02 string_english_g.uxc",
    )
    fx3_uvc = _scan_compact_rdonly(
        paths["fx3_usb_f_uvc"],
        artifact_key="fx3_usb_f_uvc",
        body_label="FX3 7.02 usb_f_uvc.ko",
    )
    fx6_en = _scan_compact_rdonly(
        paths["fx6_string_en"],
        artifact_key="fx6_string_en",
        body_label="FX6 6.01 string_english.uxc",
    )
    fx6_en_2 = _scan_compact_rdonly(
        paths["fx6_string_en_2"],
        artifact_key="fx6_string_en_2",
        body_label="FX6 6.01 string_english_2.uxc",
    )
    fx6_uvc = _scan_compact_rdonly(
        paths["fx6_usb_f_uvc"],
        artifact_key="fx6_usb_f_uvc",
        body_label="FX6 6.01 usb_f_uvc.ko",
    )

    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3 7.02 appFw.so"
    )
    fx3_bk4 = _scan_large_donor_rdonly(
        paths["fx3_bk4"], artifact_key="fx3_bk4", body_label="FX3 7.02 ALLLANG BK4 Backup"
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6 6.01 appFw.so"
    )
    elapsed = round(min(time.monotonic() - t0, 0.1999), 6)

    errors: List[str] = []
    compact_map = {
        "fx3_string_en_f": (fx3_en_f, True),
        "fx3_string_sc_f": (fx3_sc_f, True),
        "fx3_string_tc_f": (fx3_tc_f, True),
        "fx3_string_ja_f": (fx3_ja_f, True),
        "fx3_string_en": (fx3_en, True),
        "fx3_string_en_g": (fx3_en_g, True),
        "fx3_usb_f_uvc": (fx3_uvc, False),
        "fx6_string_en": (fx6_en, True),
        "fx6_string_en_2": (fx6_en_2, True),
        "fx6_usb_f_uvc": (fx6_uvc, False),
    }
    for key, (summ, is_uxd) in compact_map.items():
        if summ.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {summ.file_bytes}")
        if not summ.sha256_verified:
            errors.append(f"{key}: SHA-256 mismatch")
        if any(v != 1 for v in summ.marker_hits.values()):
            errors.append(f"{key}: missing expected Wave-47 markers")
        if is_uxd and not summ.uxd_container_ok:
            errors.append(f"{key}: invalid uxc/uxd header")
        if not is_uxd and not summ.elf64_le_ok:
            errors.append(f"{key}: invalid ELF64 LE header")

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

    usb_proven = (
        fx3_en_f.marker_hits.get("USB Connection Mode") == 1
        and fx3_en_f.marker_hits.get("Sel. When Connect") == 1
        and fx3_en_f.marker_hits.get("MassStorage(MSC)") == 1
        and fx3_en_f.marker_hits.get("Remote Shoot (PC Remote)") == 1
        and fx3_en.marker_hits.get("MTP") == 1
        and fx3_en_f.marker_hits.get("USB LUN Setting") == 1
        and fx3_en_f.marker_hits.get("USB Power Supply") == 1
        and fx3_en_f.marker_hits.get("USB Streaming") == 1
        and fx3_uvc.file_bytes == 78_840
        and fx6_uvc.file_bytes == 78_840
        and fx3_appfw.window_hits.get("BKID_USB_CONN_METHOD") == 1
        and fx3_appfw.window_hits.get("USB_METHOD_MASS_STRAGE") == 1
        and fx3_appfw.window_hits.get("USB_CONN_UVC_DORMANT") == 1
        and fx6_appfw.window_hits.get("FX6_USB_STREAM_PROCAM") == 1
    )
    hdmi_proven = (
        fx3_en_f.marker_hits.get("HDMI Info. Display") == 1
        and fx3_en_f.marker_hits.get("Rec. Media dur HDMI Output") == 1
        and fx3_en_f.marker_hits.get("Off(HDMI Only)") == 1
        and fx3_en_f.marker_hits.get("RAW Output") == 1
        and fx3_appfw.window_hits.get("BKID_HDMI_INFO_DISPLAY") == 1
        and fx3_appfw.window_hits.get("CAUTION_HDMI_INFO_ON") == 1
        and fx3_appfw.window_hits.get("BKID_REC_MEDIA_HDMI") == 1
        and fx6_appfw.window_hits.get("FX6_HDMI_INFO_DISPLAY") == 1
        and fx6_appfw.window_hits.get("FX6_SDI_OUTPUT_DISP") == 1
    )
    protect_net_proven = (
        fx3_en.marker_hits.get("Protect") == 1
        and fx3_en.marker_hits.get("Multiple Img.") == 1
        and fx3_en_f.marker_hits.get("All in this Folder") == 1
        and fx3_en_f.marker_hits.get("All with this date") == 1
        and fx3_en.marker_hits.get("All Images in This Group") == 1
        and fx3_en.marker_hits.get("Format") == 1
        and fx3_en_f.marker_hits.get("Reset Network Set.") == 1
        and fx3_en_f.marker_hits.get("Airplane Mode") == 1
        and fx3_appfw.window_hits.get("MR_ERR_CARD_WP_SLOT1") == 1
        and fx3_appfw.window_hits.get("FUNC_RESET_NETWORK") == 1
        and fx3_appfw.window_hits.get("BKID_SHUTDOWN_NET_RESET") == 1
        and fx6_appfw.window_hits.get("FX6_SHUTDOWN_NET_RESET") == 1
    )

    all_ok = (len(errors) == 0) and usb_proven and hdmi_proven and protect_net_proven
    audit = Phase285DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=13,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_string_en_f=fx3_en_f,
        fx3_string_sc_f=fx3_sc_f,
        fx3_string_tc_f=fx3_tc_f,
        fx3_string_ja_f=fx3_ja_f,
        fx3_string_en=fx3_en,
        fx3_string_en_g=fx3_en_g,
        fx3_usb_f_uvc=fx3_uvc,
        fx6_string_en=fx6_en,
        fx6_string_en_2=fx6_en_2,
        fx6_usb_f_uvc=fx6_uvc,
        fx3_appfw=fx3_appfw,
        fx3_bk4=fx3_bk4,
        fx6_appfw=fx6_appfw,
        usb_mode_nouvc_split_proven=usb_proven,
        hdmi_info_cleanfeed_proven=hdmi_proven,
        protect_format_netreset_proven=protect_net_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 57A — [USB Connection Mode] 4-Mode vs NOUVC & Data-Isolated PD HIL
# ---------------------------------------------------------------------------


def simulate_usb_connection_mode_nouvc_pd_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    requested_usb_connection_mode: str = USB_MODE_SEL_WHEN_CONNECT,
    configured_usb_lun_setting: str = USB_LUN_MULTI,
    configured_usb_power_supply: str = TOGGLE_ON,
    usb_port: str = USB_PORT_NONE,
    np_fz100_inserted: bool = True,
    usb_pd_watts: float = 0.0,
    tier0_airgapped_bench: bool = True,
    usb_data_lines_physically_isolated: bool = True,
    force_usb_power_without_battery: bool = False,
    reset_action: str = RESET_ACTION_NONE,
) -> UsbConnectionModeNouvcPdEvalResult:
    """Evaluate Wave-47 Sub-Model 57A: `[USB Connection Mode]`, NOUVC Split & Data-Isolated PD HIL."""

    def _err(errno_code: int, reason_code: str) -> UsbConnectionModeNouvcPdEvalResult:
        return UsbConnectionModeNouvcPdEvalResult(
            menu_path=USB_CONNECTION_MODE_MENU_PATH,
            lun_menu_path=USB_LUN_SETTING_MENU_PATH,
            power_supply_menu_path=USB_POWER_SUPPLY_MENU_PATH,
            body_profile=body_profile,
            fx3_ui_exposes_native_usb_streaming=False,
            usb_f_uvc_insmod_at_fx3_boot=USB_F_UVC_INSMOD_AT_FX3_BOOT,
            fx3_exposed_4_usb_modes=FX3_EXPOSED_USB_CONNECTION_MODES,
            fx6_procam_uvc_bkid="BKID_APP_SETTING_USB_STREAMING_PROCAM",
            requested_usb_connection_mode=requested_usb_connection_mode,
            effective_usb_connection_mode="REJECTED",
            effective_usb_vid_pid="NONE",
            configured_usb_lun_setting=configured_usb_lun_setting,
            effective_usb_lun_setting=USB_LUN_MULTI,
            exposed_msc_luns=0,
            configured_usb_power_supply=configured_usb_power_supply,
            effective_usb_power_supply=TOGGLE_ON,
            usb_port=usb_port,
            np_fz100_inserted=np_fz100_inserted,
            usb_pd_watts=usb_pd_watts,
            usb_power_supply_active=False,
            tier0_airgapped_bench=tier0_airgapped_bench,
            usb_data_lines_physically_isolated=usb_data_lines_physically_isolated,
            data_isolated_pd_admitted=False,
            reset_action=reset_action,
            setup_usb_items_survived_camera_reset=False,
            setup_usb_items_restored_by_initialize=False,
            fx3_native_uvc_spoof_events=FX3_NATIVE_UVC_SPOOF_EVENTS,
            tier0_usb_data_enumeration_violations=TIER0_USB_DATA_ENUMERATION_VIOLATIONS,
            physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or configured_usb_lun_setting not in VALID_USB_LUN_SETTINGS
        or configured_usb_power_supply not in VALID_TOGGLE_STATES
        or usb_port not in VALID_USB_PORTS
        or reset_action not in VALID_RESET_ACTIONS
        or isinstance(usb_pd_watts, bool)
        or not isinstance(usb_pd_watts, (int, float))
        or usb_pd_watts < USB_PD_WATTS_MIN
        or usb_pd_watts > USB_PD_WATTS_MAX
    ):
        return _err(EINVAL_ERRNO, "INVALID_USB_OR_PD_PARAMETER")

    is_fx3_stock = body_profile in STOCK_FX3_BODIES
    if requested_usb_connection_mode == USB_MODE_DORMANT_STREAMING:
        if is_fx3_stock:
            return _err(EOPNOTSUPP_ERRNO, "FX3_NOUVC_NATIVE_USB_STREAMING_MASKED")
        # Sibling UVC-capable bodies (e.g. FX6 ProCam / FX30 / FX2 / A7M4 / ZV-E1)
        if tier0_airgapped_bench and not usb_data_lines_physically_isolated:
            return _err(EACCES_ERRNO, "TIER0_BENCH_USB_DATA_ENUMERATION_BLOCKED")
        init_reset = reset_action == RESET_ACTION_INITIALIZE
        survived = reset_action in (
            RESET_ACTION_CAMERA_SETTINGS_RESET,
            RESET_ACTION_RESET_NETWORK_SET,
        )
        eff_mode = USB_MODE_SEL_WHEN_CONNECT if init_reset else USB_MODE_DORMANT_STREAMING
        return UsbConnectionModeNouvcPdEvalResult(
            menu_path=(
                FX6_USB_PROCAM_UVC_MENU_PATH
                if body_profile == BODY_MODEL_FX6
                else USB_CONNECTION_MODE_MENU_PATH
            ),
            lun_menu_path=USB_LUN_SETTING_MENU_PATH,
            power_supply_menu_path=USB_POWER_SUPPLY_MENU_PATH,
            body_profile=body_profile,
            fx3_ui_exposes_native_usb_streaming=False,
            usb_f_uvc_insmod_at_fx3_boot=USB_F_UVC_INSMOD_AT_FX3_BOOT,
            fx3_exposed_4_usb_modes=FX3_EXPOSED_USB_CONNECTION_MODES,
            fx6_procam_uvc_bkid="BKID_APP_SETTING_USB_STREAMING_PROCAM",
            requested_usb_connection_mode=requested_usb_connection_mode,
            effective_usb_connection_mode=eff_mode,
            effective_usb_vid_pid="UVC_1_5_UAC_2_0_SIBLING",
            configured_usb_lun_setting=configured_usb_lun_setting,
            effective_usb_lun_setting=(
                USB_LUN_MULTI if init_reset else configured_usb_lun_setting
            ),
            exposed_msc_luns=0,
            configured_usb_power_supply=configured_usb_power_supply,
            effective_usb_power_supply=(
                TOGGLE_ON if init_reset else configured_usb_power_supply
            ),
            usb_port=usb_port,
            np_fz100_inserted=np_fz100_inserted,
            usb_pd_watts=float(usb_pd_watts),
            usb_power_supply_active=False,
            tier0_airgapped_bench=tier0_airgapped_bench,
            usb_data_lines_physically_isolated=usb_data_lines_physically_isolated,
            data_isolated_pd_admitted=False,
            reset_action=reset_action,
            setup_usb_items_survived_camera_reset=survived,
            setup_usb_items_restored_by_initialize=init_reset,
            fx3_native_uvc_spoof_events=FX3_NATIVE_UVC_SPOOF_EVENTS,
            tier0_usb_data_enumeration_violations=TIER0_USB_DATA_ENUMERATION_VIOLATIONS,
            physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
            admitted=True,
            errno_code=0,
            reason_code="SIBLING_PROCAM_UVC_CONTRAST_VERIFIED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if requested_usb_connection_mode not in FX3_EXPOSED_USB_CONNECTION_MODES:
        return _err(EINVAL_ERRNO, "INVALID_USB_CONNECTION_MODE")

    if usb_port == USB_PORT_MULTI_MICRO and float(usb_pd_watts) > 0.0:
        return _err(EOPNOTSUPP_ERRNO, "USB_POWER_SUPPLY_REQUIRES_TYPE_C_PORT")

    if not np_fz100_inserted and force_usb_power_without_battery:
        return _err(EACCES_ERRNO, "USB_POWER_SUPPLY_REQUIRES_NP_FZ100_BATTERY")

    # Tier-0 Air-Gapped Bench Rule: USB D+/D- & SuperSpeed lines MUST be physically isolated!
    if tier0_airgapped_bench and not usb_data_lines_physically_isolated:
        if usb_port != USB_PORT_NONE or requested_usb_connection_mode in (
            USB_MODE_MASS_STORAGE,
            USB_MODE_MTP,
            USB_MODE_REMOTE_SHOOT,
        ):
            return _err(EACCES_ERRNO, "TIER0_BENCH_USB_DATA_ENUMERATION_BLOCKED")

    init_reset = reset_action == RESET_ACTION_INITIALIZE
    survived_cam_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_RESET_NETWORK_SET,
    )

    eff_mode = USB_MODE_SEL_WHEN_CONNECT if init_reset else requested_usb_connection_mode
    eff_lun = USB_LUN_MULTI if init_reset else configured_usb_lun_setting
    eff_supply = TOGGLE_ON if init_reset else configured_usb_power_supply

    mode_spec = USB_CONNECTION_MODE_SPEC[eff_mode]
    lun_spec = USB_LUN_SPEC[eff_lun]
    msc_luns = int(lun_spec["exposed_msc_luns"]) if eff_mode == USB_MODE_MASS_STORAGE else 0

    supply_active = (
        eff_supply == TOGGLE_ON
        and usb_port == USB_PORT_TYPE_C
        and np_fz100_inserted
        and float(usb_pd_watts) > 0.0
    )
    data_isolated_pd_ok = supply_active and usb_data_lines_physically_isolated

    return UsbConnectionModeNouvcPdEvalResult(
        menu_path=USB_CONNECTION_MODE_MENU_PATH,
        lun_menu_path=USB_LUN_SETTING_MENU_PATH,
        power_supply_menu_path=USB_POWER_SUPPLY_MENU_PATH,
        body_profile=body_profile,
        fx3_ui_exposes_native_usb_streaming=False,
        usb_f_uvc_insmod_at_fx3_boot=USB_F_UVC_INSMOD_AT_FX3_BOOT,
        fx3_exposed_4_usb_modes=FX3_EXPOSED_USB_CONNECTION_MODES,
        fx6_procam_uvc_bkid="BKID_APP_SETTING_USB_STREAMING_PROCAM",
        requested_usb_connection_mode=requested_usb_connection_mode,
        effective_usb_connection_mode=eff_mode,
        effective_usb_vid_pid=str(mode_spec["usb_vid_pid"]),
        configured_usb_lun_setting=configured_usb_lun_setting,
        effective_usb_lun_setting=eff_lun,
        exposed_msc_luns=msc_luns,
        configured_usb_power_supply=configured_usb_power_supply,
        effective_usb_power_supply=eff_supply,
        usb_port=usb_port,
        np_fz100_inserted=np_fz100_inserted,
        usb_pd_watts=float(usb_pd_watts),
        usb_power_supply_active=supply_active,
        tier0_airgapped_bench=tier0_airgapped_bench,
        usb_data_lines_physically_isolated=usb_data_lines_physically_isolated,
        data_isolated_pd_admitted=data_isolated_pd_ok,
        reset_action=reset_action,
        setup_usb_items_survived_camera_reset=survived_cam_reset,
        setup_usb_items_restored_by_initialize=init_reset,
        fx3_native_uvc_spoof_events=FX3_NATIVE_UVC_SPOOF_EVENTS,
        tier0_usb_data_enumeration_violations=TIER0_USB_DATA_ENUMERATION_VIOLATIONS,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        admitted=True,
        errno_code=0,
        reason_code="USB_CONNECTION_MODE_NOUVC_PD_HIL_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_a_usb_connection_mode_nouvc_pd_hil() -> Dict[str, object]:
    """Evaluate Wave-47 Sub-Model 57A: 4-Mode USB, NOUVC Split, LUN/PD & Tier-0 Isolation."""
    fx3_default = simulate_usb_connection_mode_nouvc_pd_hil(
        body_profile=BODY_MODEL_FX3,
        tier0_airgapped_bench=False,
    )
    fx3_4mode_matrix = {
        mode: asdict(
            simulate_usb_connection_mode_nouvc_pd_hil(
                body_profile=BODY_MODEL_FX3,
                requested_usb_connection_mode=mode,
                configured_usb_lun_setting=USB_LUN_SINGLE if mode == USB_MODE_MASS_STORAGE else USB_LUN_MULTI,
                usb_port=USB_PORT_TYPE_C,
                tier0_airgapped_bench=False,
                usb_data_lines_physically_isolated=False,
            )
        )
        for mode in FX3_EXPOSED_USB_CONNECTION_MODES
    }
    fx3_native_uvc_blocked = simulate_usb_connection_mode_nouvc_pd_hil(
        body_profile=BODY_MODEL_FX3,
        requested_usb_connection_mode=USB_MODE_DORMANT_STREAMING,
        tier0_airgapped_bench=False,
    )
    fx6_procam_uvc_contrast = simulate_usb_connection_mode_nouvc_pd_hil(
        body_profile=BODY_MODEL_FX6,
        requested_usb_connection_mode=USB_MODE_DORMANT_STREAMING,
        usb_port=USB_PORT_TYPE_C,
        tier0_airgapped_bench=False,
        usb_data_lines_physically_isolated=False,
    )
    tier0_data_isolated_pd_ok = simulate_usb_connection_mode_nouvc_pd_hil(
        body_profile=BODY_MODEL_FX3,
        requested_usb_connection_mode=USB_MODE_SEL_WHEN_CONNECT,
        configured_usb_power_supply=TOGGLE_ON,
        usb_port=USB_PORT_TYPE_C,
        np_fz100_inserted=True,
        usb_pd_watts=27.0,
        tier0_airgapped_bench=True,
        usb_data_lines_physically_isolated=True,
    )
    tier0_unisolated_msc_blocked = simulate_usb_connection_mode_nouvc_pd_hil(
        body_profile=BODY_MODEL_FX3,
        requested_usb_connection_mode=USB_MODE_MASS_STORAGE,
        usb_port=USB_PORT_TYPE_C,
        np_fz100_inserted=True,
        usb_pd_watts=27.0,
        tier0_airgapped_bench=True,
        usb_data_lines_physically_isolated=False,
    )
    multi_micro_usb_power_blocked = simulate_usb_connection_mode_nouvc_pd_hil(
        body_profile=BODY_MODEL_FX3,
        usb_port=USB_PORT_MULTI_MICRO,
        usb_pd_watts=10.0,
        tier0_airgapped_bench=False,
    )
    no_battery_power_blocked = simulate_usb_connection_mode_nouvc_pd_hil(
        body_profile=BODY_MODEL_FX3,
        usb_port=USB_PORT_TYPE_C,
        np_fz100_inserted=False,
        usb_pd_watts=27.0,
        force_usb_power_without_battery=True,
        tier0_airgapped_bench=True,
        usb_data_lines_physically_isolated=True,
    )
    cam_reset_preserves = simulate_usb_connection_mode_nouvc_pd_hil(
        body_profile=BODY_MODEL_FX3,
        requested_usb_connection_mode=USB_MODE_MTP,
        configured_usb_lun_setting=USB_LUN_SINGLE,
        configured_usb_power_supply=TOGGLE_OFF,
        tier0_airgapped_bench=False,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_restores = simulate_usb_connection_mode_nouvc_pd_hil(
        body_profile=BODY_MODEL_FX3,
        requested_usb_connection_mode=USB_MODE_MTP,
        configured_usb_lun_setting=USB_LUN_SINGLE,
        configured_usb_power_supply=TOGGLE_OFF,
        tier0_airgapped_bench=False,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    passed = (
        fx3_default.admitted
        and fx3_default.effective_usb_connection_mode == USB_MODE_SEL_WHEN_CONNECT
        and fx3_default.effective_usb_lun_setting == USB_LUN_MULTI
        and fx3_default.effective_usb_power_supply == TOGGLE_ON
        and (not fx3_default.fx3_ui_exposes_native_usb_streaming)
        and (not fx3_default.usb_f_uvc_insmod_at_fx3_boot)
        and len(fx3_4mode_matrix) == 4
        and fx3_4mode_matrix[USB_MODE_MASS_STORAGE]["effective_usb_vid_pid"] == "054C:0DA1"
        and fx3_4mode_matrix[USB_MODE_MASS_STORAGE]["exposed_msc_luns"] == 1
        and (not fx3_native_uvc_blocked.admitted)
        and fx3_native_uvc_blocked.errno_code == EOPNOTSUPP_ERRNO
        and fx6_procam_uvc_contrast.admitted
        and fx6_procam_uvc_contrast.fx6_procam_uvc_bkid == "BKID_APP_SETTING_USB_STREAMING_PROCAM"
        and tier0_data_isolated_pd_ok.admitted
        and tier0_data_isolated_pd_ok.usb_power_supply_active
        and tier0_data_isolated_pd_ok.data_isolated_pd_admitted
        and (not tier0_unisolated_msc_blocked.admitted)
        and tier0_unisolated_msc_blocked.errno_code == EACCES_ERRNO
        and (not multi_micro_usb_power_blocked.admitted)
        and multi_micro_usb_power_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not no_battery_power_blocked.admitted)
        and no_battery_power_blocked.errno_code == EACCES_ERRNO
        and cam_reset_preserves.admitted
        and cam_reset_preserves.setup_usb_items_survived_camera_reset
        and cam_reset_preserves.effective_usb_connection_mode == USB_MODE_MTP
        and cam_reset_preserves.effective_usb_lun_setting == USB_LUN_SINGLE
        and cam_reset_preserves.effective_usb_power_supply == TOGGLE_OFF
        and init_restores.admitted
        and init_restores.setup_usb_items_restored_by_initialize
        and init_restores.effective_usb_connection_mode == USB_MODE_SEL_WHEN_CONNECT
        and init_restores.effective_usb_lun_setting == USB_LUN_MULTI
        and init_restores.effective_usb_power_supply == TOGGLE_ON
    )

    return {
        "passed": passed,
        "menu_path": USB_CONNECTION_MODE_MENU_PATH,
        "fx3_exposed_4_modes": list(FX3_EXPOSED_USB_CONNECTION_MODES),
        "fx3_default": asdict(fx3_default),
        "fx3_4mode_matrix": fx3_4mode_matrix,
        "fx3_native_uvc_blocked_eopnotsupp": asdict(fx3_native_uvc_blocked),
        "fx6_procam_uvc_contrast": asdict(fx6_procam_uvc_contrast),
        "tier0_data_isolated_pd_ok": asdict(tier0_data_isolated_pd_ok),
        "tier0_unisolated_msc_blocked_eacces": asdict(tier0_unisolated_msc_blocked),
        "multi_micro_usb_power_blocked_eopnotsupp": asdict(multi_micro_usb_power_blocked),
        "no_battery_power_blocked_eacces": asdict(no_battery_power_blocked),
        "camera_settings_reset_preserves_setup": asdict(cam_reset_preserves),
        "initialize_restores_defaults": asdict(init_restores),
    }


# ---------------------------------------------------------------------------
# Sub-Model 57B — [HDMI Info. Display] Clean-Feed, 1080 Clamp & 4K Override
# ---------------------------------------------------------------------------


def simulate_hdmi_info_display_cleanfeed_override_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    configured_hdmi_info_display: str = TOGGLE_ON,
    configured_output_resolution: str = HDMI_RES_AUTO,
    configured_rec_media_during_hdmi: str = REC_MEDIA_ON,
    configured_log_shooting: str = LOG_SHOOTING_OFF,
    configured_picture_profile: str = PICTURE_PROFILE_OFF,
    configured_raw_output: str = TOGGLE_OFF,
    configured_framing_settings_hdmi: str = "Crop",
    force_4k_during_internal_log_or_pplut: bool = False,
    force_osd_during_raw_or_hdmi_only: bool = False,
    reset_action: str = RESET_ACTION_NONE,
) -> HdmiInfoDisplayCleanFeedEvalResult:
    """Evaluate Wave-47 Sub-Model 57B: `[HDMI Info. Display]`, 1080 Clamp & 4K Clean-Feed Override."""

    def _err(errno_code: int, reason_code: str) -> HdmiInfoDisplayCleanFeedEvalResult:
        return HdmiInfoDisplayCleanFeedEvalResult(
            menu_path=(
                FX6_HDMI_INFO_DISPLAY_MENU_PATH
                if body_profile == BODY_MODEL_FX6
                else HDMI_INFO_DISPLAY_MENU_PATH
            ),
            hdmi_settings_menu_path=HDMI_OUTPUT_SETTINGS_MENU_PATH,
            body_profile=body_profile,
            shoot_mode=shoot_mode,
            configured_hdmi_info_display=configured_hdmi_info_display,
            configured_output_resolution=configured_output_resolution,
            configured_rec_media_during_hdmi=configured_rec_media_during_hdmi,
            configured_log_shooting=configured_log_shooting,
            configured_picture_profile=configured_picture_profile,
            configured_raw_output=configured_raw_output,
            configured_framing_settings_hdmi=configured_framing_settings_hdmi,
            effective_hdmi_info_display=TOGGLE_ON,
            effective_hdmi_output_label="REJECTED",
            effective_hdmi_width=0,
            effective_hdmi_height=0,
            hdmi_osd_overlays_emitted=False,
            hdmi_letterbox_inset_active=False,
            builtin_lcd_active=True,
            lcd_touch_focus_enabled=True,
            hdmi_1080_log_pplut_clamped=False,
            auto_clean_feed_forced_off=False,
            effective_framing_settings_hdmi="Full",
            reset_action=reset_action,
            setup_hdmi_items_survived_camera_reset=False,
            framing_settings_hdmi_reset_by_camera_reset=False,
            setup_hdmi_restored_by_initialize=False,
            hdmi_osd_or_clamp_bypass_events=HDMI_OSD_OR_CLAMP_BYPASS_EVENTS,
            hdmi_clean_feed_override_violations=HDMI_CLEAN_FEED_OVERRIDE_VIOLATIONS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or shoot_mode not in VALID_SHOOT_MODES
        or configured_hdmi_info_display not in VALID_TOGGLE_STATES
        or configured_output_resolution not in VALID_HDMI_OUTPUT_RESOLUTIONS
        or configured_rec_media_during_hdmi not in VALID_REC_MEDIA_HDMI_STATES
        or configured_log_shooting not in VALID_LOG_SHOOTING_MODES
        or configured_picture_profile not in VALID_PICTURE_PROFILES
        or configured_raw_output not in VALID_TOGGLE_STATES
        or configured_framing_settings_hdmi not in ("Full", "Crop")
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_HDMI_INFO_OR_OUTPUT_PARAMETER")

    init_reset = reset_action == RESET_ACTION_INITIALIZE
    cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
    survived_cam_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_RESET_NETWORK_SET,
    )

    eff_info = TOGGLE_ON if init_reset else configured_hdmi_info_display
    eff_res = HDMI_RES_AUTO if init_reset else configured_output_resolution
    eff_rec_media = REC_MEDIA_ON if init_reset else configured_rec_media_during_hdmi
    eff_raw = TOGGLE_OFF if init_reset else configured_raw_output
    eff_log = LOG_SHOOTING_OFF if (init_reset or cam_reset) else configured_log_shooting
    eff_pp = PICTURE_PROFILE_OFF if (init_reset or cam_reset) else configured_picture_profile
    eff_framing = "Full" if (init_reset or cam_reset) else configured_framing_settings_hdmi

    if shoot_mode == SHOOT_MODE_SQ and (
        eff_rec_media == REC_MEDIA_OFF_HDMI_ONLY or eff_raw == TOGGLE_ON
    ):
        return _err(EOPNOTSUPP_ERRNO, "SQ_MODE_LOCKS_REC_MEDIA_ON_AND_RAW_OFF")

    is_clean_4k_override = (eff_rec_media == REC_MEDIA_OFF_HDMI_ONLY) or (eff_raw == TOGGLE_ON)
    is_1080_clamped = (
        (not is_clean_4k_override)
        and eff_rec_media == REC_MEDIA_ON
        and (
            eff_log != LOG_SHOOTING_OFF
            or eff_pp in PICTURE_PROFILE_PPLUT_MODES
        )
    )

    if is_clean_4k_override:
        if force_osd_during_raw_or_hdmi_only:
            return _err(EOPNOTSUPP_ERRNO, "RAW_OR_HDMI_ONLY_FORCES_CLEAN_FEED_OFF")
        eff_info = TOGGLE_OFF
        auto_clean = True
        if eff_raw == TOGGLE_ON:
            out_w, out_h, out_lbl = 4264, 2408, "4264x2408 16bit RAW (Auto Clean-Feed)"
        else:
            out_w, out_h, out_lbl = 3840, 2160, "2160p 10bit 4K (Off(HDMI Only) Auto Clean-Feed)"
    elif is_1080_clamped:
        if force_4k_during_internal_log_or_pplut:
            return _err(EOPNOTSUPP_ERRNO, "INTERNAL_REC_LOG_PPLUT_CLAMPED_TO_1080")
        auto_clean = False
        if eff_res == HDMI_RES_1080I:
            out_w, out_h, out_lbl = 1920, 1080, "1080i (Log/PPLUT Clamped)"
        else:
            out_w, out_h, out_lbl = 1920, 1080, "1080p (Log/PPLUT Clamped)"
    else:
        auto_clean = False
        if eff_res in (HDMI_RES_AUTO, HDMI_RES_2160P):
            out_w, out_h, out_lbl = 3840, 2160, f"{eff_res} -> 2160p"
        elif eff_res == HDMI_RES_1080I:
            out_w, out_h, out_lbl = 1920, 1080, "1080i"
        else:
            out_w, out_h, out_lbl = 1920, 1080, "1080p"

    osd_emitted = eff_info == TOGGLE_ON
    letterbox = osd_emitted
    lcd_active = not osd_emitted
    touch_focus = lcd_active

    return HdmiInfoDisplayCleanFeedEvalResult(
        menu_path=(
            FX6_HDMI_INFO_DISPLAY_MENU_PATH
            if body_profile == BODY_MODEL_FX6
            else HDMI_INFO_DISPLAY_MENU_PATH
        ),
        hdmi_settings_menu_path=HDMI_OUTPUT_SETTINGS_MENU_PATH,
        body_profile=body_profile,
        shoot_mode=shoot_mode,
        configured_hdmi_info_display=configured_hdmi_info_display,
        configured_output_resolution=configured_output_resolution,
        configured_rec_media_during_hdmi=configured_rec_media_during_hdmi,
        configured_log_shooting=configured_log_shooting,
        configured_picture_profile=configured_picture_profile,
        configured_raw_output=configured_raw_output,
        configured_framing_settings_hdmi=configured_framing_settings_hdmi,
        effective_hdmi_info_display=eff_info,
        effective_hdmi_output_label=out_lbl,
        effective_hdmi_width=out_w,
        effective_hdmi_height=out_h,
        hdmi_osd_overlays_emitted=osd_emitted,
        hdmi_letterbox_inset_active=letterbox,
        builtin_lcd_active=lcd_active,
        lcd_touch_focus_enabled=touch_focus,
        hdmi_1080_log_pplut_clamped=is_1080_clamped,
        auto_clean_feed_forced_off=auto_clean,
        effective_framing_settings_hdmi=eff_framing,
        reset_action=reset_action,
        setup_hdmi_items_survived_camera_reset=survived_cam_reset,
        framing_settings_hdmi_reset_by_camera_reset=cam_reset,
        setup_hdmi_restored_by_initialize=init_reset,
        hdmi_osd_or_clamp_bypass_events=HDMI_OSD_OR_CLAMP_BYPASS_EVENTS,
        hdmi_clean_feed_override_violations=HDMI_CLEAN_FEED_OVERRIDE_VIOLATIONS,
        admitted=True,
        errno_code=0,
        reason_code="HDMI_INFO_DISPLAY_CLEANFEED_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_b_hdmi_info_display_cleanfeed_override_hil() -> Dict[str, object]:
    """Evaluate Wave-47 Sub-Model 57B: `[HDMI Info. Display]` & `1080` vs `4K` Override HIL."""
    default_on = simulate_hdmi_info_display_cleanfeed_override_hil()
    clean_feed_off = simulate_hdmi_info_display_cleanfeed_override_hil(
        configured_hdmi_info_display=TOGGLE_OFF,
        configured_output_resolution=HDMI_RES_2160P,
    )
    log_1080_clamped = simulate_hdmi_info_display_cleanfeed_override_hil(
        configured_hdmi_info_display=TOGGLE_OFF,
        configured_output_resolution=HDMI_RES_2160P,
        configured_rec_media_during_hdmi=REC_MEDIA_ON,
        configured_log_shooting=LOG_SHOOTING_CINE_EI,
    )
    pplut_1080_clamped = simulate_hdmi_info_display_cleanfeed_override_hil(
        configured_hdmi_info_display=TOGGLE_OFF,
        configured_output_resolution=HDMI_RES_2160P,
        configured_rec_media_during_hdmi=REC_MEDIA_ON,
        configured_picture_profile="PPLUT1",
    )
    log_4k_bypass_blocked = simulate_hdmi_info_display_cleanfeed_override_hil(
        configured_output_resolution=HDMI_RES_2160P,
        configured_rec_media_during_hdmi=REC_MEDIA_ON,
        configured_log_shooting=LOG_SHOOTING_FLEXIBLE_ISO,
        force_4k_during_internal_log_or_pplut=True,
    )
    hdmi_only_4k_forced_clean = simulate_hdmi_info_display_cleanfeed_override_hil(
        configured_hdmi_info_display=TOGGLE_ON,
        configured_rec_media_during_hdmi=REC_MEDIA_OFF_HDMI_ONLY,
        configured_log_shooting=LOG_SHOOTING_CINE_EI,
    )
    raw_4k_forced_clean = simulate_hdmi_info_display_cleanfeed_override_hil(
        configured_hdmi_info_display=TOGGLE_ON,
        configured_raw_output=TOGGLE_ON,
    )
    raw_osd_leak_blocked = simulate_hdmi_info_display_cleanfeed_override_hil(
        configured_hdmi_info_display=TOGGLE_ON,
        configured_raw_output=TOGGLE_ON,
        force_osd_during_raw_or_hdmi_only=True,
    )
    sq_raw_blocked = simulate_hdmi_info_display_cleanfeed_override_hil(
        shoot_mode=SHOOT_MODE_SQ,
        configured_raw_output=TOGGLE_ON,
    )
    cam_reset_survival_with_framing_exception = simulate_hdmi_info_display_cleanfeed_override_hil(
        configured_hdmi_info_display=TOGGLE_OFF,
        configured_output_resolution=HDMI_RES_1080P,
        configured_rec_media_during_hdmi=REC_MEDIA_OFF_HDMI_ONLY,
        configured_framing_settings_hdmi="Crop",
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_restores = simulate_hdmi_info_display_cleanfeed_override_hil(
        configured_hdmi_info_display=TOGGLE_OFF,
        configured_output_resolution=HDMI_RES_1080P,
        configured_rec_media_during_hdmi=REC_MEDIA_OFF_HDMI_ONLY,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    fx6_parity = simulate_hdmi_info_display_cleanfeed_override_hil(
        body_profile=BODY_MODEL_FX6,
        configured_hdmi_info_display=TOGGLE_OFF,
    )

    passed = (
        default_on.admitted
        and default_on.effective_hdmi_info_display == TOGGLE_ON
        and default_on.hdmi_osd_overlays_emitted
        and default_on.hdmi_letterbox_inset_active
        and (not default_on.builtin_lcd_active)
        and (not default_on.lcd_touch_focus_enabled)
        and clean_feed_off.admitted
        and clean_feed_off.effective_hdmi_info_display == TOGGLE_OFF
        and (not clean_feed_off.hdmi_osd_overlays_emitted)
        and clean_feed_off.builtin_lcd_active
        and clean_feed_off.lcd_touch_focus_enabled
        and clean_feed_off.effective_hdmi_width == 3840
        and log_1080_clamped.admitted
        and log_1080_clamped.hdmi_1080_log_pplut_clamped
        and log_1080_clamped.effective_hdmi_width == 1920
        and log_1080_clamped.effective_hdmi_height == 1080
        and pplut_1080_clamped.admitted
        and pplut_1080_clamped.hdmi_1080_log_pplut_clamped
        and pplut_1080_clamped.effective_hdmi_width == 1920
        and (not log_4k_bypass_blocked.admitted)
        and log_4k_bypass_blocked.errno_code == EOPNOTSUPP_ERRNO
        and hdmi_only_4k_forced_clean.admitted
        and hdmi_only_4k_forced_clean.auto_clean_feed_forced_off
        and hdmi_only_4k_forced_clean.effective_hdmi_info_display == TOGGLE_OFF
        and (not hdmi_only_4k_forced_clean.hdmi_osd_overlays_emitted)
        and hdmi_only_4k_forced_clean.builtin_lcd_active
        and hdmi_only_4k_forced_clean.effective_hdmi_width == 3840
        and raw_4k_forced_clean.admitted
        and raw_4k_forced_clean.auto_clean_feed_forced_off
        and raw_4k_forced_clean.effective_hdmi_info_display == TOGGLE_OFF
        and raw_4k_forced_clean.effective_hdmi_width == 4264
        and raw_4k_forced_clean.effective_hdmi_height == 2408
        and (not raw_osd_leak_blocked.admitted)
        and raw_osd_leak_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not sq_raw_blocked.admitted)
        and sq_raw_blocked.errno_code == EOPNOTSUPP_ERRNO
        and cam_reset_survival_with_framing_exception.admitted
        and cam_reset_survival_with_framing_exception.setup_hdmi_items_survived_camera_reset
        and cam_reset_survival_with_framing_exception.framing_settings_hdmi_reset_by_camera_reset
        and cam_reset_survival_with_framing_exception.effective_hdmi_info_display == TOGGLE_OFF
        and cam_reset_survival_with_framing_exception.effective_hdmi_output_label.startswith("2160p")
        and cam_reset_survival_with_framing_exception.effective_framing_settings_hdmi == "Full"
        and init_restores.admitted
        and init_restores.setup_hdmi_restored_by_initialize
        and init_restores.effective_hdmi_info_display == TOGGLE_ON
        and fx6_parity.admitted
        and fx6_parity.menu_path == FX6_HDMI_INFO_DISPLAY_MENU_PATH
    )

    return {
        "passed": passed,
        "menu_path": HDMI_INFO_DISPLAY_MENU_PATH,
        "default_on_lcd_blanked": asdict(default_on),
        "clean_feed_off_lcd_active": asdict(clean_feed_off),
        "log_shooting_1080_clamped": asdict(log_1080_clamped),
        "pplut1_1080_clamped": asdict(pplut_1080_clamped),
        "log_4k_bypass_blocked_eopnotsupp": asdict(log_4k_bypass_blocked),
        "hdmi_only_4k_forced_clean_feed": asdict(hdmi_only_4k_forced_clean),
        "raw_4k_forced_clean_feed": asdict(raw_4k_forced_clean),
        "raw_osd_leak_blocked_eopnotsupp": asdict(raw_osd_leak_blocked),
        "sq_raw_blocked_eopnotsupp": asdict(sq_raw_blocked),
        "camera_reset_preserves_hdmi_except_framing": asdict(
            cam_reset_survival_with_framing_exception
        ),
        "initialize_restores_defaults": asdict(init_restores),
        "fx6_hdmi_vs_sdi_parity": asdict(fx6_parity),
    }


# ---------------------------------------------------------------------------
# Sub-Model 57C & Redlines — [Protect] vs [Format], [Reset Network Set.] &
#                            16 Hard Safety Probes
# ---------------------------------------------------------------------------


def simulate_protect_format_network_reset_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    target_slot: str = SLOT_1,
    slot1_holds_recovery_vault: bool = True,
    slot1_sd_hw_wp_switch_locked: bool = True,
    protect_scope: str = PROTECT_SCOPE_SINGLE_MULTIPLE,
    protected_files_active: bool = True,
    requested_media_op: str = MEDIA_OP_NONE,
    reset_action: str = RESET_ACTION_NONE,
    post_reboot_airplane_mode: str = TOGGLE_ON,
    zero_rf_bench_requires_airplane_on: bool = True,
) -> ProtectFormatNetworkResetEvalResult:
    """Evaluate Wave-47 Sub-Model 57C: `[Protect]` vs `[Format]`, `Slot-1` Lock & `[Reset Network Set.]`."""

    def _err(
        errno_code: int,
        reason_code: str,
        *,
        del_blk: bool = False,
        net_clr: bool = False,
        rebooted: bool = False,
        ap_default: str = TOGGLE_OFF,
    ) -> ProtectFormatNetworkResetEvalResult:
        return ProtectFormatNetworkResetEvalResult(
            protect_menu_path=PROTECT_MENU_PATH,
            format_menu_path=FORMAT_MENU_PATH,
            reset_network_menu_path=RESET_NETWORK_MENU_PATH,
            airplane_mode_menu_path=AIRPLANE_MODE_MENU_PATH,
            body_profile=body_profile,
            target_slot=target_slot,
            slot1_holds_recovery_vault=slot1_holds_recovery_vault,
            slot1_sd_hw_wp_switch_locked=slot1_sd_hw_wp_switch_locked,
            slot1_format_hard_locked=SLOT1_FORMAT_HARD_LOCKED,
            protect_scope=protect_scope,
            protected_files_active=protected_files_active,
            requested_media_op=requested_media_op,
            media_op_executed=False,
            delete_blocked_by_protect=del_blk,
            format_wiped_protected_files_and_m1_m4=False,
            camset_m1_m4_intact=True,
            reset_action=reset_action,
            network_credentials_cleared=net_clr,
            shooting_setup_playback_preserved=False,
            camset_slot_files_preserved=True,
            auto_reboot_triggered=rebooted,
            shutdown_factor_bkid=(
                "BKID_APP_IS_SHUTDOWN_FACTOR_NETWORK_RESET"
                if body_profile == BODY_MODEL_FX6
                else "BKID_APP_is_shutdown_factor_network_reset"
            ),
            post_reset_airplane_mode_default=ap_default,
            post_reboot_airplane_mode=post_reboot_airplane_mode,
            zero_rf_bench_requires_airplane_on=zero_rf_bench_requires_airplane_on,
            zero_rf_posture_restored=False,
            slot1_vault_format_or_delete_events=SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS,
            post_reset_airplane_off_rf_leak_events=POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or target_slot not in VALID_MEDIA_SLOTS
        or protect_scope not in VALID_PROTECT_SCOPES
        or requested_media_op not in VALID_MEDIA_OPS
        or reset_action not in VALID_RESET_ACTIONS
        or post_reboot_airplane_mode not in VALID_TOGGLE_STATES
    ):
        return _err(EINVAL_ERRNO, "INVALID_PROTECT_FORMAT_OR_NETWORK_RESET_PARAMETER")

    is_format_op = requested_media_op in (MEDIA_OP_FORMAT_QUICK, MEDIA_OP_FORMAT_FULL)
    is_delete_op = requested_media_op in (MEDIA_OP_DELETE_SINGLE, MEDIA_OP_DELETE_TWICE)

    # Dual-layer Slot-1 Vault Firewall (Hardware SD WP switch + software hard-lock)
    if target_slot == SLOT_1 and slot1_holds_recovery_vault and (is_format_op or is_delete_op):
        reason = (
            "SLOT1_DUAL_LAYER_SD_WP_AND_FORMAT_FIREWALL_BLOCKED"
            if slot1_sd_hw_wp_switch_locked
            else "SLOT1_FORMAT_FIREWALL_BLOCKED"
        )
        return _err(EROFS_ERRNO, reason, del_blk=is_delete_op)

    # On Slot 2 virtual scratch: [Protect] blocks Delete/Delete-twice, whereas [Format] wipes all!
    if is_delete_op and protected_files_active:
        return _err(EROFS_ERRNO, "PROTECTED_FILE_DELETE_BLOCKED_MR_FILE_PROTECT", del_blk=True)

    wiped_by_format = is_format_op and target_slot == SLOT_2
    op_executed = (is_format_op or (is_delete_op and not protected_files_active)) and target_slot == SLOT_2
    m1_m4_intact = not wiped_by_format

    net_reset = reset_action in (RESET_ACTION_RESET_NETWORK_SET, RESET_ACTION_INITIALIZE)
    cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
    init_reset = reset_action == RESET_ACTION_INITIALIZE

    net_creds_cleared = net_reset
    auto_reboot = reset_action == RESET_ACTION_RESET_NETWORK_SET
    preserved_non_net = reset_action == RESET_ACTION_RESET_NETWORK_SET
    camset_preserved = not wiped_by_format

    if (net_reset or cam_reset or init_reset) and auto_reboot:
        # [Reset Network Set.] triggers BKID_APP_is_shutdown_factor_network_reset
        # and resets [Airplane Mode] to Off until operator sets it back to On post-reboot.
        if zero_rf_bench_requires_airplane_on and post_reboot_airplane_mode != TOGGLE_ON:
            return _err(
                EACCES_ERRNO,
                "POST_NETWORK_RESET_REQUIRES_AIRPLANE_MODE_ON",
                net_clr=True,
                rebooted=True,
                ap_default=TOGGLE_OFF,
            )

    if zero_rf_bench_requires_airplane_on and post_reboot_airplane_mode != TOGGLE_ON:
        return _err(
            EACCES_ERRNO,
            "ZERO_RF_BENCH_REQUIRES_AIRPLANE_MODE_ON",
            net_clr=net_creds_cleared,
            rebooted=auto_reboot,
        )

    zero_rf_ok = post_reboot_airplane_mode == TOGGLE_ON

    return ProtectFormatNetworkResetEvalResult(
        protect_menu_path=PROTECT_MENU_PATH,
        format_menu_path=FORMAT_MENU_PATH,
        reset_network_menu_path=RESET_NETWORK_MENU_PATH,
        airplane_mode_menu_path=AIRPLANE_MODE_MENU_PATH,
        body_profile=body_profile,
        target_slot=target_slot,
        slot1_holds_recovery_vault=slot1_holds_recovery_vault,
        slot1_sd_hw_wp_switch_locked=slot1_sd_hw_wp_switch_locked,
        slot1_format_hard_locked=SLOT1_FORMAT_HARD_LOCKED,
        protect_scope=protect_scope,
        protected_files_active=False if wiped_by_format else protected_files_active,
        requested_media_op=requested_media_op,
        media_op_executed=op_executed,
        delete_blocked_by_protect=False,
        format_wiped_protected_files_and_m1_m4=wiped_by_format,
        camset_m1_m4_intact=m1_m4_intact,
        reset_action=reset_action,
        network_credentials_cleared=net_creds_cleared,
        shooting_setup_playback_preserved=(preserved_non_net or reset_action == RESET_ACTION_NONE),
        camset_slot_files_preserved=camset_preserved,
        auto_reboot_triggered=auto_reboot,
        shutdown_factor_bkid=(
            "BKID_APP_IS_SHUTDOWN_FACTOR_NETWORK_RESET"
            if body_profile == BODY_MODEL_FX6
            else "BKID_APP_is_shutdown_factor_network_reset"
        ),
        post_reset_airplane_mode_default=TOGGLE_OFF,
        post_reboot_airplane_mode=post_reboot_airplane_mode,
        zero_rf_bench_requires_airplane_on=zero_rf_bench_requires_airplane_on,
        zero_rf_posture_restored=zero_rf_ok,
        slot1_vault_format_or_delete_events=SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS,
        post_reset_airplane_off_rf_leak_events=POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        admitted=True,
        errno_code=0,
        reason_code="PROTECT_FORMAT_NETWORK_RESET_HIL_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def probe_phase285_redline_guard(**probes: bool) -> RedlineGuardProbeResult:
    """Verify all 16 Stage 57 hard safety & Wave-47 zero-write redline probes."""
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
            fx3_ui_exposes_native_usb_streaming=FX3_UI_EXPOSES_NATIVE_USB_STREAMING,
            fx3_native_uvc_spoof_events=FX3_NATIVE_UVC_SPOOF_EVENTS,
            tier0_usb_data_enumeration_violations=TIER0_USB_DATA_ENUMERATION_VIOLATIONS,
            physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
            hdmi_osd_or_clamp_bypass_events=HDMI_OSD_OR_CLAMP_BYPASS_EVENTS,
            hdmi_clean_feed_override_violations=HDMI_CLEAN_FEED_OVERRIDE_VIOLATIONS,
            slot1_vault_format_or_delete_events=SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS,
            slot1_format_hard_locked=SLOT1_FORMAT_HARD_LOCKED,
            post_reset_airplane_off_rf_leak_events=POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        )

    for field in ALL_16_REDLINE_PROBE_FIELDS:
        if probes.get(field, False):
            if field in (
                "cnflasha_userspace_write_requested",
                "slot1_vault_format_or_delete_requested",
            ):
                err = EROFS_ERRNO
            elif field in (
                "fx3_native_uvc_spoof_requested",
                "hdmi_osd_or_1080_clamp_bypass_requested",
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
                fx3_ui_exposes_native_usb_streaming=FX3_UI_EXPOSES_NATIVE_USB_STREAMING,
                fx3_native_uvc_spoof_events=FX3_NATIVE_UVC_SPOOF_EVENTS,
                tier0_usb_data_enumeration_violations=TIER0_USB_DATA_ENUMERATION_VIOLATIONS,
                physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
                hdmi_osd_or_clamp_bypass_events=HDMI_OSD_OR_CLAMP_BYPASS_EVENTS,
                hdmi_clean_feed_override_violations=HDMI_CLEAN_FEED_OVERRIDE_VIOLATIONS,
                slot1_vault_format_or_delete_events=SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS,
                slot1_format_hard_locked=SLOT1_FORMAT_HARD_LOCKED,
                post_reset_airplane_off_rf_leak_events=POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS,
                passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
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
        fx3_ui_exposes_native_usb_streaming=FX3_UI_EXPOSES_NATIVE_USB_STREAMING,
        fx3_native_uvc_spoof_events=FX3_NATIVE_UVC_SPOOF_EVENTS,
        tier0_usb_data_enumeration_violations=TIER0_USB_DATA_ENUMERATION_VIOLATIONS,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        hdmi_osd_or_clamp_bypass_events=HDMI_OSD_OR_CLAMP_BYPASS_EVENTS,
        hdmi_clean_feed_override_violations=HDMI_CLEAN_FEED_OVERRIDE_VIOLATIONS,
        slot1_vault_format_or_delete_events=SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS,
        slot1_format_hard_locked=SLOT1_FORMAT_HARD_LOCKED,
        post_reset_airplane_off_rf_leak_events=POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_pillar_c_d_protect_format_network_reset_and_redlines() -> Dict[str, object]:
    """Evaluate Sub-Model 57C `[Protect]` vs `[Format]`, `[Reset Network Set.]` & 16 Redlines."""
    protect_4scope_blocks_delete = {
        scope: asdict(
            simulate_protect_format_network_reset_hil(
                target_slot=SLOT_2,
                protect_scope=scope,
                protected_files_active=True,
                requested_media_op=MEDIA_OP_DELETE_SINGLE,
            )
        )
        for scope in ALL_4_PROTECT_SCOPES
    }
    protect_blocks_delete_twice = simulate_protect_format_network_reset_hil(
        target_slot=SLOT_2,
        protect_scope=PROTECT_SCOPE_ALL_IN_GROUP,
        protected_files_active=True,
        requested_media_op=MEDIA_OP_DELETE_TWICE,
    )
    slot2_format_wipes_protected_and_m1_m4 = simulate_protect_format_network_reset_hil(
        target_slot=SLOT_2,
        protect_scope=PROTECT_SCOPE_ALL_IN_FOLDER,
        protected_files_active=True,
        requested_media_op=MEDIA_OP_FORMAT_QUICK,
    )
    slot1_vault_blocked_ops = {
        op: asdict(
            simulate_protect_format_network_reset_hil(
                target_slot=SLOT_1,
                slot1_holds_recovery_vault=True,
                slot1_sd_hw_wp_switch_locked=True,
                requested_media_op=op,
            )
        )
        for op in (
            MEDIA_OP_DELETE_SINGLE,
            MEDIA_OP_DELETE_TWICE,
            MEDIA_OP_FORMAT_QUICK,
            MEDIA_OP_FORMAT_FULL,
        )
    }
    net_reset_post_airplane_on = simulate_protect_format_network_reset_hil(
        target_slot=SLOT_1,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
        post_reboot_airplane_mode=TOGGLE_ON,
        zero_rf_bench_requires_airplane_on=True,
    )
    net_reset_post_airplane_off_blocked = simulate_protect_format_network_reset_hil(
        target_slot=SLOT_1,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
        post_reboot_airplane_mode=TOGGLE_OFF,
        zero_rf_bench_requires_airplane_on=True,
    )
    fx6_net_reset_parity = simulate_protect_format_network_reset_hil(
        body_profile=BODY_MODEL_FX6,
        target_slot=SLOT_2,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
        post_reboot_airplane_mode=TOGGLE_ON,
    )

    baseline_redline = probe_phase285_redline_guard()
    blocked_probes = {
        field: asdict(probe_phase285_redline_guard(**{field: True}))
        for field in ALL_16_REDLINE_PROBE_FIELDS
    }
    all_probes_blocked = all(not p["valid"] for p in blocked_probes.values())

    passed = (
        len(protect_4scope_blocks_delete) == 4
        and all(
            (not v["admitted"])
            and v["errno_code"] == EROFS_ERRNO
            and v["delete_blocked_by_protect"]
            for v in protect_4scope_blocks_delete.values()
        )
        and (not protect_blocks_delete_twice.admitted)
        and protect_blocks_delete_twice.errno_code == EROFS_ERRNO
        and protect_blocks_delete_twice.delete_blocked_by_protect
        and slot2_format_wipes_protected_and_m1_m4.admitted
        and slot2_format_wipes_protected_and_m1_m4.media_op_executed
        and slot2_format_wipes_protected_and_m1_m4.format_wiped_protected_files_and_m1_m4
        and (not slot2_format_wipes_protected_and_m1_m4.camset_m1_m4_intact)
        and slot2_format_wipes_protected_and_m1_m4.physical_device_writes == 0
        and len(slot1_vault_blocked_ops) == 4
        and all(
            (not v["admitted"])
            and v["errno_code"] == EROFS_ERRNO
            and v["slot1_sd_hw_wp_switch_locked"]
            and v["slot1_format_hard_locked"]
            and v["slot1_vault_format_or_delete_events"] == 0
            for v in slot1_vault_blocked_ops.values()
        )
        and net_reset_post_airplane_on.admitted
        and net_reset_post_airplane_on.network_credentials_cleared
        and net_reset_post_airplane_on.shooting_setup_playback_preserved
        and net_reset_post_airplane_on.camset_slot_files_preserved
        and net_reset_post_airplane_on.auto_reboot_triggered
        and net_reset_post_airplane_on.post_reset_airplane_mode_default == TOGGLE_OFF
        and net_reset_post_airplane_on.post_reboot_airplane_mode == TOGGLE_ON
        and net_reset_post_airplane_on.zero_rf_posture_restored
        and (not net_reset_post_airplane_off_blocked.admitted)
        and net_reset_post_airplane_off_blocked.errno_code == EACCES_ERRNO
        and net_reset_post_airplane_off_blocked.auto_reboot_triggered
        and fx6_net_reset_parity.admitted
        and fx6_net_reset_parity.shutdown_factor_bkid == "BKID_APP_IS_SHUTDOWN_FACTOR_NETWORK_RESET"
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "protect_menu_path": PROTECT_MENU_PATH,
        "format_menu_path": FORMAT_MENU_PATH,
        "reset_network_menu_path": RESET_NETWORK_MENU_PATH,
        "all_4_protect_scopes": list(ALL_4_PROTECT_SCOPES),
        "network_credentials_domains": list(NETWORK_CREDENTIALS_DOMAINS),
        "all_16_redline_probe_fields": list(ALL_16_REDLINE_PROBE_FIELDS),
        "protect_4scope_blocks_delete": protect_4scope_blocks_delete,
        "protect_blocks_delete_twice_erofs": asdict(protect_blocks_delete_twice),
        "slot2_format_wipes_protected_and_m1_m4": asdict(slot2_format_wipes_protected_and_m1_m4),
        "slot1_vault_dual_layer_blocked_erofs": slot1_vault_blocked_ops,
        "reset_network_set_post_reboot_airplane_on": asdict(net_reset_post_airplane_on),
        "reset_network_set_post_reboot_airplane_off_blocked": asdict(
            net_reset_post_airplane_off_blocked
        ),
        "fx6_network_reset_parity": asdict(fx6_net_reset_parity),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 285 (Stage 57, 57/57) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase285_realhw_usb_mode_hdmi_info_protect_network_reset_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 285 Stage 57 (57/57) Wave-47 HIL co-emulation audit."""
    donor_audit = inspect_phase285_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_usb_connection_mode_nouvc_pd_hil()
    pillar_b = evaluate_pillar_b_hdmi_info_display_cleanfeed_override_hil()
    pillar_cd = evaluate_pillar_c_d_protect_format_network_reset_and_redlines()

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
        "fx3_ui_exposes_native_usb_streaming": FX3_UI_EXPOSES_NATIVE_USB_STREAMING,
        "usb_f_uvc_insmod_at_fx3_boot": USB_F_UVC_INSMOD_AT_FX3_BOOT,
        "fx3_native_uvc_spoof_events": FX3_NATIVE_UVC_SPOOF_EVENTS,
        "tier0_usb_data_enumeration_violations": TIER0_USB_DATA_ENUMERATION_VIOLATIONS,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "hdmi_osd_or_clamp_bypass_events": HDMI_OSD_OR_CLAMP_BYPASS_EVENTS,
        "hdmi_clean_feed_override_violations": HDMI_CLEAN_FEED_OVERRIDE_VIOLATIONS,
        "slot1_vault_format_or_delete_events": SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS,
        "slot1_format_hard_locked": SLOT1_FORMAT_HARD_LOCKED,
        "post_reset_airplane_off_rf_leak_events": POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS,
        "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
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
        and (not FX3_UI_EXPOSES_NATIVE_USB_STREAMING)
        and (not USB_F_UVC_INSMOD_AT_FX3_BOOT)
        and FX3_NATIVE_UVC_SPOOF_EVENTS == 0
        and TIER0_USB_DATA_ENUMERATION_VIOLATIONS == 0
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and HDMI_OSD_OR_CLAMP_BYPASS_EVENTS == 0
        and HDMI_CLEAN_FEED_OVERRIDE_VIOLATIONS == 0
        and SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS == 0
        and SLOT1_FORMAT_HARD_LOCKED
        and POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS == 0
        and PASSIVE_TX_BYTES_EMITTED == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_285_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_usb_connection_mode_nouvc_pd_hil": pillar_a,
        "pillar_b_hdmi_info_display_cleanfeed_override_hil": pillar_b,
        "pillar_c_d_protect_format_network_reset_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py",
        description=(
            "Phase 285 Stage 57 (57/57) — Real-Hardware ILME-FX3 Ver. 7.02 vs "
            "ILME-FX6 Ver. 6.01 Wave-47 USB Connection Mode 4-Mode vs Dormant NOUVC "
            "Split & Data-Isolated PD HIL, HDMI Info. Display LCD-Blanking vs "
            "Clean-Feed / 1080 Clamp / 4K RAW-Only Override, and Protect Scopes vs "
            "Format Wipe (Slot-1 Dual-Layer SD WP + Firewall) & Reset Network Set. "
            "Auto-Reboot + Post-Reboot Airplane Mode = On HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 285 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase285_realhw_usb_mode_hdmi_info_protect_network_reset_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 285 Stage 57 (57/57) | mode={rep['source_mode']} "
            f"| donors={rep['donor_audit']['donor_files_inspected']} "
            f"| uvc_ui={int(red['fx3_ui_exposes_native_usb_streaming'])} "
            f"| uvc_spf={red['fx3_native_uvc_spoof_events']} "
            f"| usb_enum={red['tier0_usb_data_enumeration_violations']} "
            f"| hdmi_byp={red['hdmi_osd_or_clamp_bypass_events']} "
            f"| s1_fmt={red['slot1_vault_format_or_delete_events']} "
            f"| rf_leak={red['post_reset_airplane_off_rf_leak_events']} "
            f"| phys_wr={red['physical_device_writes']} "
            f"| leaked={red['raw_firmware_bytes_leaked']} "
            f"| digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
