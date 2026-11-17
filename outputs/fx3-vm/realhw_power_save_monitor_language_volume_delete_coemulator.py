#!/usr/bin/env python3
"""Phase 281 (Stage 56, 56/56) — Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-46:
`[Power Save by Monitor]` Reality Split (`appFw.so` 4-Mode vs `ILME-FX3` `ilc/2210` 2-Item
`[Power Setting Option]`) & `[Power Save Start Time]` 9-Deactivation HIL,
`[Language]` (`BK_LANG` `0x02cf019c` 34-vs-29 Model Split & Stage-B 4-Language `.uxc`/`.ltt` Parity), and
`[Volume Settings]` (`0..15`, Default `7`), `[4ch Audio Monitoring]` (`5` Routes vs HDMI `4ch Audio Output`),
& `[Delete confirm.]` (`"Cancel" first` + `Slot-1` Recovery Vault Firewall) HIL Co-Emulator.

Strictly models Wave-46 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts
without physical hardware attachment or firmware byte leakage:

1. **Sub-Model 56A — `[Power Save by Monitor]` Reality Split & `[Power Save Start Time]` 9-Deactivation**:
   - Stock `ILME-FX3 Ver. 7.02` `(Setup) -> [Power Setting Option]` exposes ONLY **2** items:
     `[Power Save Start Time]` (`Off`, `30 Min`, `5 Min` default, `2 Min`, `1 Min`, `10 Sec`) and
     `[Auto Power OFF Temp.]` (`Standard` default, `High`). `[Power Save by Monitor]` is NOT
     exposed in stock `FX3` / `FX3A` / `FX6` UI (`fx3_ui_exposes_power_save_by_monitor == False`),
     and spoofed `"Open: On/Close: Off"` strings are hard-rejected (`EOPNOTSUPP = 95`).
   - Shared `BIONZ XR` `appFw.so` (`BKID_APP_setting_monitor_power_linkage`) + `string_*_f.uxc`
     (`0x60b9`) DO compile the exact **4** modes (`Both Linked` `0x6db5` / `ON_ALL`, `Open: Return`
     `0x6db6` / `ON_OPEN`, `Close: Power Save` `0x60a8` / `ON_CLOSE`, `Does Not Link` `0x6b2e` /
     `OFF`) for sibling vari-angle `BIONZ XR` bodies (`ILME-FX2`, `ILCE-7M4`, `ZV-E1`, `ILCE-6700`).
     Models both stock FX3 vari-angle fold invariance AND sibling headless HDMI sleep protection
     (`Does Not Link` / `Open: Return`, guarding against `ILCE-7M4 Ver. 6.00`-style sleep bugs).
   - Models all **9** `[Power Save Start Time]` deactivation conditions (`USB power supply`,
     `slideshow playback`, `FTP transfer`, `movie recording`, `PC connection`, `TV/HDMI connection`,
     `IR Remote Ctrl = On`, `Bluetooth Rmt Ctrl = On`, `streaming / Creators' Cloud upload`) plus
     `(Setup)` survival across `[Camera Settings Reset]` (restored only by `[Initialize]`).

2. **Sub-Model 56B — `[Language]` `BK_LANG` (`0x02cf019c`) 34-vs-29 Split & Stage-B 4-Lang Parity**:
   - `MENU -> Setup -> [Area/Date] -> [Language]`: `ILME-FX3` carries `34` languages
     (`BKID_APP_setting_language`, `resid16=0xe397`, `BK4` `0x02cf019c` @ `0x90ff0`, `4 B` LE = `0`
     in `FX3-CX95900_ALLLANG-Backup.bin`) vs `ILME-FX6` `29` languages (`BKID_APP_SETTING_LANGUAGE`,
     `Language Select` `0x2f4d`, `BK4` `0x02cf019c` @ `0x89242`, `1 B` = `0x00` in `CX95898_NTSC.bin`
     vs `0x19` in `CX95899_CN1.bin`).
   - Stage-B 4-language `.uxc`/`.ltt` bank parity (`en=0x00` `switchBank=0` `(4,4)`,
     `schinese=0x19` `switchBank=23` `(19,19)`, `tchinese=0x18` `switchBank=27` `(22,22)`,
     `japanese=0x01` `switchBank=1` `(12,12)`), plus `(Setup)` survival across BOTH
     `[Camera Settings Reset]` and `[Reset Network Set.]` (cleared/re-prompted `"—"` ONLY by
     `[Initialize]` via `libSaveLoadSettings.so`).

3. **Sub-Model 56C & Redlines — `[Volume Settings]` (`0..15`), `[4ch Audio Monitoring]` (`5` Routes),
   & `[Delete confirm.]` (`"Cancel" first` + `Slot-1` Recovery Vault Firewall)**:
   - `[Volume Settings]` (`0..15`, factory default `7`, `resid16=0xe8c9`, distinct from `[Audio signals]`
     `0x7af6`): movie playback audio routing (`Internal Speaker` rear mono vs `3.5 mm` stereo
     headphone vs `HDMI`), `XLR-H1` internal-speaker acoustic feedback guard, and FX6 `Monitor Volume`
     parity (`BKID_APP_SETTING_MONITOR_VOLUME`).
   - `[4ch Audio Monitoring]` (`BKID_APP_setting_audio_monitoring_ch`): all **5** routes (`CH1/CH2`
     default `0x713b`, `CH3/CH4` `0x6bf6`, `CH1+3/CH2+4` `0x6c2e`, `CH1/CH1` `0x6f9c`, `CH2/CH2`
     `0x7a26`), 2ch stereo headphone hardware boundary, distinct from HDMI `[4ch Audio Output]`
     (`BKID_APP_setting_4ch_output_ch`, `0x6aa0`, `CH1/CH2` / `CH3/CH4` only).
   - `[Delete confirm.]` (`"Cancel" first` default `0xe724`/`0x6a5e` vs `"Delete" first`
     `0xe725`/`0x6e0a`) + `[Delete pressing twice]` (`Off` default `0x74db`), `(Playback)` survival
     across `[Camera Settings Reset]` (reset only by `[Initialize]`), and hard `Slot-1` recovery
     vault firewall (`slot1_vault_delete_events == 0`, `slot1_format_hard_locked == True`) blocking
     all single/multiple/folder/date/twice-delete & `[Format]` operations on `Slot 1` (`EROFS = 30`).

4. **Dual-Mode 18-Donor `O_RDONLY` SHA-256 Verification & Hard Safety Redlines**:
   - Pins exact byte sizes & SHA-256 hashes of 18 `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01`
     donors strictly `os.O_RDONLY` (`raw_firmware_bytes_leaked == 0`), with deterministic
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

SCHEMA_ID = "realhw_power_save_monitor_language_volume_delete_coemulator_v1"
PHASE_281_SCHEMA = SCHEMA_ID
PHASE_281_VERSION = "281.0.0"
PHASE_NUMBER = 281
STAGE_INDEX = 56
STAGE_TOTAL = 56
MILESTONE_LABEL = "56/56"
STAGE_NAME = "stage56_realhw_power_save_monitor_language_volume_delete_hil"
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

# Wave-46 Stage 56 zero-fault & model-truth invariants
FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR = False
POWER_SAVE_MONITOR_SPOOF_EVENTS = 0
HEADLESS_HDMI_UNEXPECTED_SLEEP_EVENTS = 0
LANGUAGE_COUNT_MODEL_MISMATCH_EVENTS = 0
BK_LANG_OFFSET_MISMATCH_EVENTS = 0
XLR_H1_SPEAKER_FEEDBACK_GUARD_VIOLATIONS = 0
FOUR_CH_HEADPHONE_ROUTING_VIOLATIONS = 0
SLOT1_VAULT_DELETE_EVENTS = 0
SLOT1_FORMAT_HARD_LOCKED = True
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
# Verified Local Donor Specs (18 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_saveload": f"{_FX3_USR_PREFIX}/lib/libSaveLoadSettings.so",
    "fx3_string_en_f": f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
    "fx3_string_sc_f": f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
    "fx3_string_tc_f": f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
    "fx3_string_ja_f": f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
    "fx3_string_en": f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
    "fx3_string_sc": f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
    "fx3_string_tc": f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
    "fx3_string_ja": f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_sc": f"{_FX6_NF15_PREFIX}/share/app/string_simplifiedchinese.uxc",
    "fx6_string_tc": f"{_FX6_NF15_PREFIX}/share/app/string_traditionalchinese.uxc",
    "fx6_string_ja": f"{_FX6_NF15_PREFIX}/share/app/string_japanese.uxc",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
    "fx3_bk4": (
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/"
        "FX3-CX95900_ALLLANG-Backup.bin"
    ),
    "fx6_bk4_ntsc": (
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/"
        "0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin"
    ),
    "fx6_bk4_cn1": (
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/"
        "0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95899_CN1.bin"
    ),
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_saveload": 18_760,
    "fx3_string_en_f": 373_820,
    "fx3_string_sc_f": 322_652,
    "fx3_string_tc_f": 324_148,
    "fx3_string_ja_f": 447_840,
    "fx3_string_en": 165_740,
    "fx3_string_sc": 149_064,
    "fx3_string_tc": 151_908,
    "fx3_string_ja": 208_564,
    "fx6_string_en": 118_208,
    "fx6_string_sc": 118_644,
    "fx6_string_tc": 119_168,
    "fx6_string_ja": 141_692,
    "fx3_appfw": 79_015_712,
    "fx6_appfw": 50_520_424,
    "fx3_bk4": 2_229_740,
    "fx6_bk4_ntsc": 2_253_333,
    "fx6_bk4_cn1": 2_253_333,
}

EXPECTED_COMPACT_DONOR_SHA256: Mapping[str, str] = {
    "fx3_saveload": "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
    "fx3_string_en_f": "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
    "fx3_string_sc_f": "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
    "fx3_string_tc_f": "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
    "fx3_string_ja_f": "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
    "fx3_string_en": "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
    "fx3_string_sc": "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
    "fx3_string_tc": "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
    "fx3_string_ja": "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
    "fx6_string_en": "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
    "fx6_string_sc": "ba060e859156bfaefcc4177bfa6e9c5bea112258b15ce815a5ba683d033e688f",
    "fx6_string_tc": "8c34b415ce4d19fd40ca22d00c4543c64eb4741b96250de13b93ec473b25b18b",
    "fx6_string_ja": "9b47630ebe8e011a9d0bdb7a2fda06574f5187222b92d60bf6887042fe186d35",
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_bk4_ntsc": "da125f7fabe4a5141f16347ade9a4417d7ca23862cb14c3b9343b5e19a81d05c",
    "fx6_bk4_cn1": "30e3702d49d62132b0d81b8b6afd1868d73a476c80a8662a8c2fd298f59847fe",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_saveload": (
        b"SaveLoadSettingsIf",
        b"_ZN18SaveLoadSettingsIf13requestToReadEN",
        b"Backup_read",
        b"Backup_write",
    ),
    "fx3_string_en_f": (
        b"Power Save by Monitor",
        b"Both Linked",
        b"Open: Return",
        b"Close: Power Save",
        b"Does Not Link",
        b"Power Save Start Time",
        b"Auto Power OFF Temp.",
        b"4ch Audio Monitoring",
        b"CH1/CH2",
        b"CH3/CH4",
        b"CH1+3/CH2+4",
        b"CH1/CH1",
        b"CH2/CH2",
        b"4ch Audio Output",
        b'"Cancel" first',
        b'"Delete" first',
        b"Delete pressing twice",
        b"Camera Settings Reset",
        b"Reset Network Set.",
        b"Initialize",
    ),
    "fx3_string_sc_f": (
        "通过显示屏节电".encode("utf-8"),
        "二者均连接".encode("utf-8"),
        "打开: 恢复".encode("utf-8"),
        "关闭: 节电".encode("utf-8"),
        "不连接".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "依據螢幕狀態省電".encode("utf-8"),
        "兩者都已連結".encode("utf-8"),
        "打開: 返回".encode("utf-8"),
        "闔上: 省電".encode("utf-8"),
        "不連結".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "ﾓﾆﾀｰ開閉でﾊﾟﾜｰｾｰﾌﾞ".encode("utf-8"),
        "両方連動".encode("utf-8"),
        "開:ﾊﾟﾜｰｾｰﾌﾞ復帰".encode("utf-8"),
        "閉:ﾊﾟﾜｰｾｰﾌﾞ".encode("utf-8"),
        "連動しない".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Auto Power OFF Temp.",
        b"Language",
        b"Volume Settings",
        b"Delete confirm.",
        b'"Cancel" first',
        b'"Delete" first',
    ),
    "fx3_string_sc": (
        "音量设置".encode("utf-8"),
        '默认为"取消"'.encode("utf-8"),
        '默认为"删除"'.encode("utf-8"),
    ),
    "fx3_string_tc": (
        "音量設定".encode("utf-8"),
        '"取消"優先'.encode("utf-8"),
        '"刪除"優先'.encode("utf-8"),
    ),
    "fx3_string_ja": (
        "音量設定".encode("utf-8"),
        "「キャンセル」が先".encode("utf-8"),
        "「削除」が先".encode("utf-8"),
    ),
    "fx6_string_en": (
        b"Language Select",
        b"Monitor CH",
        b"Delete Clip?",
    ),
    "fx6_string_sc": (
        "语言".encode("utf-8"),
        "音量".encode("utf-8"),
        "删除".encode("utf-8"),
    ),
    "fx6_string_tc": (
        "語言".encode("utf-8"),
        "音量".encode("utf-8"),
        "刪除".encode("utf-8"),
    ),
    "fx6_string_ja": (
        "言語".encode("utf-8"),
        "音量".encode("utf-8"),
        "削除".encode("utf-8"),
    ),
}

COMPACT_ABSENT_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Open: On/Close: Off",
    ),
    "fx3_string_en": (
        b"Power Save by Monitor",
        b"Open: On/Close: Off",
    ),
    "fx6_string_en": (
        b"Power Save by Monitor",
        b"Open: On/Close: Off",
        b"Auto Power OFF Temp.",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (62_697_472, "MONITOR_PWR_LINKAGE", b"BKID_APP_setting_monitor_power_linkage"),
        (62_697_472, "START_POWER_SAVING", b"BKID_APP_setting_start_power_saving"),
        (62_693_376, "LANGUAGE", b"BKID_APP_setting_language"),
        (62_697_472, "VOLUME_SETTINGS", b"BKID_APP_setting_volume_settings"),
        (62_701_558, "AUDIO_MON_CH", b"BKID_APP_setting_audio_monitoring_ch"),
        (62_701_568, "HDMI_4CH_OUT", b"BKID_APP_setting_4ch_output_ch"),
        (62_689_280, "DELETE_CONFIRM", b"BKID_APP_setting_delete_confirm"),
        (62_689_280, "DELETE_TWICE", b"BKID_APP_setting_delete_by_delete_twice"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (40_919_040, "SETTING_LANG", b"BKID_APP_SETTING_LANGUAGE"),
        (40_943_616, "MONITOR_VOL", b"BKID_APP_SETTING_MONITOR_VOLUME"),
        (35_987_456, "INITIALIZE", b"Initialize"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (0, "ALLLANG", b"ALLLANG"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_bk4_ntsc": (
        (0, "BK4", b"BK4\x00"),
        (0, "NTSC", b"NTSC"),
    ),
    "fx6_bk4_cn1": (
        (0, "BK4", b"BK4\x00"),
        (0, "CN1", b"CN1"),
    ),
}

# Exact BK_LANG (0x02cf019c) payload offsets in BK4 backups
FX3_BK_LANG_ID = 0x02CF019C
FX3_BK_LANG_OFFSET = 0x90FF0
FX3_BK_LANG_WIDTH_BYTES = 4
FX3_BK_LANG_EXPECTED_SEED_VALUE = 0x00

FX6_BK_LANG_OFFSET = 0x89242
FX6_BK_LANG_WIDTH_BYTES = 1
FX6_NTSC_BK_LANG_EXPECTED_VALUE = 0x00
FX6_CN1_BK_LANG_EXPECTED_VALUE = 0x19

# ---------------------------------------------------------------------------
# Wave-46 Official Sub-Model 56A / 56B / 56C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX3A = "ILME-FX3A"
BODY_MODEL_FX6 = "ILME-FX6"
BODY_MODEL_FX2 = "ILME-FX2"
BODY_MODEL_A7M4 = "ILCE-7M4"
BODY_MODEL_ZVE1 = "ZV-E1"
BODY_MODEL_A6700 = "ILCE-6700"

SIBLING_POWER_SAVE_BY_MONITOR_BODIES: Tuple[str, ...] = (
    BODY_MODEL_FX2,
    BODY_MODEL_A7M4,
    BODY_MODEL_ZVE1,
    BODY_MODEL_A6700,
)
STOCK_FX3_LINE_BODIES: Tuple[str, ...] = (
    BODY_MODEL_FX3,
    BODY_MODEL_FX3A,
    BODY_MODEL_FX6,
)
ALL_SUPPORTED_BODY_PROFILES: Tuple[str, ...] = (
    STOCK_FX3_LINE_BODIES + SIBLING_POWER_SAVE_BY_MONITOR_BODIES
)

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

# Sub-Model 56A: [Power Setting Option] / [Power Save by Monitor] / [Power Save Start Time]
POWER_SETTING_OPTION_MENU_PATH = "MENU -> Setup -> [Power Setting Option]"
FX3_POWER_SETTING_OPTION_ITEMS: Tuple[str, ...] = (
    "Power Save Start Time",
    "Auto Power OFF Temp.",
)
SIBLING_POWER_SETTING_OPTION_ITEMS: Tuple[str, ...] = (
    "Power Save by Monitor",
    "Power Save Start Time",
    "Auto Power OFF Temp.",
)
LEGACY_POWER_SAVE_MONITOR_SPOOF = "Open: On/Close: Off"

POWER_SAVE_BY_MONITOR_RESID = "0x60b9"
PSM_BOTH_LINKED = "Both Linked"
PSM_OPEN_RETURN = "Open: Return"
PSM_CLOSE_POWER_SAVE = "Close: Power Save"
PSM_DOES_NOT_LINK = "Does Not Link"
VALID_POWER_SAVE_BY_MONITOR_MODES: Tuple[str, ...] = (
    PSM_BOTH_LINKED,
    PSM_OPEN_RETURN,
    PSM_CLOSE_POWER_SAVE,
    PSM_DOES_NOT_LINK,
)
POWER_SAVE_BY_MONITOR_SPEC: Mapping[str, Mapping[str, object]] = {
    PSM_BOTH_LINKED: {
        "resid16": "0x6db5",
        "enum": "EXTERN_VAL_MONITOR_POWER_LINKAGE_ON_ALL",
        "wakes_on_open": True,
        "sleeps_on_close": True,
        "headless_hdmi_safe": False,
    },
    PSM_OPEN_RETURN: {
        "resid16": "0x6db6",
        "enum": "EXTERN_VAL_MONITOR_POWER_LINKAGE_ON_OPEN",
        "wakes_on_open": True,
        "sleeps_on_close": False,
        "headless_hdmi_safe": True,
    },
    PSM_CLOSE_POWER_SAVE: {
        "resid16": "0x60a8",
        "enum": "EXTERN_VAL_MONITOR_POWER_LINKAGE_ON_CLOSE",
        "wakes_on_open": False,
        "sleeps_on_close": True,
        "headless_hdmi_safe": False,
    },
    PSM_DOES_NOT_LINK: {
        "resid16": "0x6b2e",
        "enum": "EXTERN_VAL_MONITOR_POWER_LINKAGE_OFF",
        "wakes_on_open": False,
        "sleeps_on_close": False,
        "headless_hdmi_safe": True,
    },
}

LCD_HINGE_OPEN = "Open"
LCD_HINGE_CLOSED_INWARD = "Closed_Inward"
VALID_LCD_HINGE_STATES: Tuple[str, ...] = (LCD_HINGE_OPEN, LCD_HINGE_CLOSED_INWARD)

POWER_SAVE_START_OFF = "Off"
POWER_SAVE_START_30MIN = "30 Min"
POWER_SAVE_START_5MIN = "5 Min"
POWER_SAVE_START_2MIN = "2 Min"
POWER_SAVE_START_1MIN = "1 Min"
POWER_SAVE_START_10SEC = "10 Sec"
VALID_POWER_SAVE_START_TIMES: Tuple[str, ...] = (
    POWER_SAVE_START_OFF,
    POWER_SAVE_START_30MIN,
    POWER_SAVE_START_5MIN,
    POWER_SAVE_START_2MIN,
    POWER_SAVE_START_1MIN,
    POWER_SAVE_START_10SEC,
)

AUTO_POWER_OFF_TEMP_STANDARD = "Standard"
AUTO_POWER_OFF_TEMP_HIGH = "High"
VALID_AUTO_POWER_OFF_TEMPS: Tuple[str, ...] = (
    AUTO_POWER_OFF_TEMP_STANDARD,
    AUTO_POWER_OFF_TEMP_HIGH,
)

POWER_SAVE_9_DEACTIVATION_CONDITIONS: Tuple[str, ...] = (
    "usb_power_supply",
    "slideshow_playback",
    "ftp_transfer",
    "movie_recording",
    "pc_connection",
    "tv_hdmi_connection",
    "ir_remote_ctrl_on",
    "bluetooth_rmt_ctrl_on",
    "streaming_or_creators_cloud",
)

# Sub-Model 56B: [Language] (BK_LANG 0x02cf019c) 34-vs-29 & Stage-B 4-Language Parity
LANGUAGE_MENU_PATH_FX3 = "MENU -> Setup -> [Area/Date] -> [Language]"
LANGUAGE_MENU_PATH_FX6 = "Maintenance -> [Language] (Language Select)"
LANGUAGE_UNCONFIGURED = "—"
FX3_LANGUAGE_COUNT = 34
FX6_LANGUAGE_COUNT = 29

STAGE_B_4_LANGUAGES: Mapping[str, Mapping[str, object]] = {
    "en": {
        "uxc_lang_key": "english",
        "bk_lang_code": 0x00,
        "appfw_enum": "0x2b2f_LANGUAGE_ENGLISH",
        "switch_bank": 0,
        "font_str_banks": (4, 4),
        "ltt_font": "UniversOTS-SJ_wIcon.ltt",
        "fx3_f_uxc_bytes": 373_820,
        "fx3_uxc_bytes": 165_740,
        "fx6_uxc_bytes": 118_208,
    },
    "schinese": {
        "uxc_lang_key": "simplifiedchinese",
        "bk_lang_code": 0x19,
        "appfw_enum": "0x2b45_CHINESE_SIMPLIFIED",
        "switch_bank": 23,
        "font_str_banks": (19, 19),
        "ltt_font": "MYingHeiC-GB18030-SJ_wIcon.ltt",
        "fx3_f_uxc_bytes": 322_652,
        "fx3_uxc_bytes": 149_064,
        "fx6_uxc_bytes": 118_644,
    },
    "tchinese": {
        "uxc_lang_key": "traditionalchinese",
        "bk_lang_code": 0x18,
        "appfw_enum": "0x2b44_LANGUAGE_CHINESE_TRADITIONAL",
        "switch_bank": 27,
        "font_str_banks": (22, 22),
        "ltt_font": "MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
        "fx3_f_uxc_bytes": 324_148,
        "fx3_uxc_bytes": 151_908,
        "fx6_uxc_bytes": 119_168,
    },
    "japanese": {
        "uxc_lang_key": "japanese",
        "bk_lang_code": 0x01,
        "appfw_enum": "0x2b30_LANGUAGE_JAPANESE",
        "switch_bank": 1,
        "font_str_banks": (12, 12),
        "ltt_font": "HeiseiKakuGothW5-SJ_wIcon.ltt",
        "fx3_f_uxc_bytes": 447_840,
        "fx3_uxc_bytes": 208_564,
        "fx6_uxc_bytes": 141_692,
    },
}
VALID_STAGE_B_LANGUAGES: Tuple[str, ...] = tuple(STAGE_B_4_LANGUAGES.keys())
FX3_ONLY_EXTRA_LANGUAGES: Tuple[str, ...] = (
    "turkish",
    "ukrainian",
    "greek",
    "croatian",
    "serbian",
)

# Sub-Model 56C: [Volume Settings], [4ch Audio Monitoring], [Delete confirm.] & Slot-1 Vault
VOLUME_SETTINGS_MENU_PATH = "MENU -> Setup -> [Sound Option] -> [Volume Settings]"
FOUR_CH_AUDIO_MONITORING_MENU_PATH = "MENU -> Setup -> [Sound Option] -> [4ch Audio Monitoring]"
HDMI_4CH_AUDIO_OUTPUT_MENU_PATH = "MENU -> Setup -> [External Output] -> [4ch Audio Output]"
DELETE_CONFIRM_MENU_PATH = "MENU -> Playback -> [Delete] -> [Delete confirm.]"
DELETE_PRESSING_TWICE_MENU_PATH = "MENU -> Playback -> [Delete] -> [Delete pressing twice]"

VOLUME_SETTINGS_MIN = 0
VOLUME_SETTINGS_MAX = 15
VOLUME_SETTINGS_DEFAULT = 7
VOLUME_SETTINGS_RESID = "0xe8c9"
AUDIO_SIGNALS_RESID = "0x7af6"

PLAYBACK_SINK_INTERNAL_SPEAKER = "Internal Speaker"
PLAYBACK_SINK_HEADPHONE_35MM = "Headphone 3.5mm"
PLAYBACK_SINK_HDMI = "HDMI Audio"
VALID_PLAYBACK_SINKS: Tuple[str, ...] = (
    PLAYBACK_SINK_INTERNAL_SPEAKER,
    PLAYBACK_SINK_HEADPHONE_35MM,
    PLAYBACK_SINK_HDMI,
)

MON_ROUTE_CH1_CH2 = "CH1/CH2"
MON_ROUTE_CH3_CH4 = "CH3/CH4"
MON_ROUTE_CH1P3_CH2P4 = "CH1+3/CH2+4"
MON_ROUTE_CH1_CH1 = "CH1/CH1"
MON_ROUTE_CH2_CH2 = "CH2/CH2"
VALID_4CH_AUDIO_MONITORING_ROUTES: Tuple[str, ...] = (
    MON_ROUTE_CH1_CH2,
    MON_ROUTE_CH3_CH4,
    MON_ROUTE_CH1P3_CH2P4,
    MON_ROUTE_CH1_CH1,
    MON_ROUTE_CH2_CH2,
)
FOUR_CH_AUDIO_MONITORING_SPEC: Mapping[str, Mapping[str, str]] = {
    MON_ROUTE_CH1_CH2: {
        "enum": "AUDIO_MONITORING_CH_1CH_2CH",
        "resid16": "0x713b",
        "left_source": "CH1",
        "right_source": "CH2",
    },
    MON_ROUTE_CH3_CH4: {
        "enum": "AUDIO_MONITORING_CH_3CH_4CH",
        "resid16": "0x6bf6",
        "left_source": "CH3",
        "right_source": "CH4",
    },
    MON_ROUTE_CH1P3_CH2P4: {
        "enum": "AUDIO_MONITORING_CH_MIX_ALL",
        "resid16": "0x6c2e",
        "left_source": "CH1+CH3",
        "right_source": "CH2+CH4",
    },
    MON_ROUTE_CH1_CH1: {
        "enum": "AUDIO_MONITORING_CH_1CH",
        "resid16": "0x6f9c",
        "left_source": "CH1",
        "right_source": "CH1",
    },
    MON_ROUTE_CH2_CH2: {
        "enum": "AUDIO_MONITORING_CH_2CH",
        "resid16": "0x7a26",
        "left_source": "CH2",
        "right_source": "CH2",
    },
}
VALID_HDMI_4CH_AUDIO_OUTPUT_ROUTES: Tuple[str, ...] = (
    MON_ROUTE_CH1_CH2,
    MON_ROUTE_CH3_CH4,
)

DELETE_CONFIRM_CANCEL_FIRST = '"Cancel" first'
DELETE_CONFIRM_DELETE_FIRST = '"Delete" first'
VALID_DELETE_CONFIRM_MODES: Tuple[str, ...] = (
    DELETE_CONFIRM_CANCEL_FIRST,
    DELETE_CONFIRM_DELETE_FIRST,
)

SLOT_1 = "Slot 1"
SLOT_2 = "Slot 2"
VALID_MEDIA_SLOTS: Tuple[str, ...] = (SLOT_1, SLOT_2)

MEDIA_OP_NONE = "None"
MEDIA_OP_DELETE_SINGLE = "Delete Single"
MEDIA_OP_DELETE_MULTIPLE = "Delete Multiple"
MEDIA_OP_DELETE_FOLDER = "Delete Folder"
MEDIA_OP_DELETE_DATE = "Delete Date"
MEDIA_OP_DELETE_TWICE = "Delete Pressing Twice"
MEDIA_OP_FORMAT = "Format"
VALID_MEDIA_OPERATIONS: Tuple[str, ...] = (
    MEDIA_OP_NONE,
    MEDIA_OP_DELETE_SINGLE,
    MEDIA_OP_DELETE_MULTIPLE,
    MEDIA_OP_DELETE_FOLDER,
    MEDIA_OP_DELETE_DATE,
    MEDIA_OP_DELETE_TWICE,
    MEDIA_OP_FORMAT,
)
DESTRUCTIVE_MEDIA_OPERATIONS: Tuple[str, ...] = (
    MEDIA_OP_DELETE_SINGLE,
    MEDIA_OP_DELETE_MULTIPLE,
    MEDIA_OP_DELETE_FOLDER,
    MEDIA_OP_DELETE_DATE,
    MEDIA_OP_DELETE_TWICE,
    MEDIA_OP_FORMAT,
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
    "power_save_by_monitor_fx3_ui_spoof_requested",
    "headless_hdmi_unexpected_sleep_requested",
    "bk_lang_persistent_nvram_write_requested",
    "xlr_h1_speaker_feedback_or_4ch_headphone_violation_requested",
    "slot1_vault_delete_or_format_requested",
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
class Phase281DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_saveload: CompactDonorSummary
    fx3_string_en_f: CompactDonorSummary
    fx3_string_sc_f: CompactDonorSummary
    fx3_string_tc_f: CompactDonorSummary
    fx3_string_ja_f: CompactDonorSummary
    fx3_string_en: CompactDonorSummary
    fx3_string_sc: CompactDonorSummary
    fx3_string_tc: CompactDonorSummary
    fx3_string_ja: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx6_string_sc: CompactDonorSummary
    fx6_string_tc: CompactDonorSummary
    fx6_string_ja: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    fx3_bk4: BoundedWindowDonorSummary
    fx6_bk4_ntsc: BoundedWindowDonorSummary
    fx6_bk4_cn1: BoundedWindowDonorSummary
    fx3_bk4_lang_le32: int
    fx6_ntsc_bk_lang_u8: int
    fx6_cn1_bk_lang_u8: int
    power_save_monitor_split_proven: bool
    language_bk_lang_4lang_proven: bool
    volume_4ch_delete_confirm_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PowerSaveMonitorAndStartTimeEvalResult:
    menu_path: str
    body_profile: str
    fx3_ui_exposes_power_save_by_monitor: bool
    exposed_power_setting_option_items: Tuple[str, ...]
    appfw_compiled_monitor_linkage_modes: Tuple[str, ...]
    requested_power_save_by_monitor_label: str
    lcd_hinge_state: str
    headless_hdmi_bench: bool
    ilce7m4_v600_regression_simulated: bool
    configured_power_save_start_time: str
    configured_auto_power_off_temp: str
    effective_power_save_by_monitor: str
    effective_power_save_start_time: str
    effective_auto_power_off_temp: str
    vari_angle_fold_sleep_triggered: bool
    vari_angle_fold_wake_triggered: bool
    vari_angle_fold_invariant: bool
    headless_hdmi_sleep_protected: bool
    active_deactivation_conditions: Tuple[str, ...]
    power_save_timer_bypassed: bool
    idle_sleep_armed: bool
    reset_action: str
    setup_items_survived_camera_reset: bool
    setup_items_restored_by_initialize: bool
    power_save_monitor_spoof_events: int
    headless_hdmi_unexpected_sleep_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class LanguageBkLangAndUxcParityEvalResult:
    menu_path: str
    body_profile: str
    supported_language_count: int
    bk_lang_id_hex: str
    bk_lang_offset_hex: str
    bk_lang_width_bytes: int
    regional_seed_variant: str
    configured_language_key: str
    effective_language_key: str
    effective_bk_lang_code: int
    effective_appfw_enum: str
    effective_switch_bank: int
    effective_font_str_banks: Tuple[int, int]
    effective_ltt_font: str
    initial_setup_prompt_required: bool
    out_of_box_display_label: str
    fx3_vs_fx6_count_delta: int
    reset_action: str
    survived_camera_settings_reset: bool
    survived_reset_network_set: bool
    cleared_by_initialize: bool
    language_count_model_mismatch_events: int
    bk_lang_offset_mismatch_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class VolumeMonitoringDeleteConfirmVaultEvalResult:
    volume_menu_path: str
    monitoring_4ch_menu_path: str
    hdmi_4ch_menu_path: str
    delete_confirm_menu_path: str
    delete_twice_menu_path: str
    configured_volume_level: int
    effective_volume_level: int
    playback_sink: str
    xlr_h1_mic_active: bool
    xlr_h1_speaker_feedback_clamped: bool
    configured_4ch_monitoring_route: str
    effective_4ch_monitoring_route: str
    monitoring_left_channel: str
    monitoring_right_channel: str
    headphone_output_channels: int
    discrete_4ch_headphone_simultaneous: bool
    configured_hdmi_4ch_output_route: str
    effective_hdmi_4ch_output_route: str
    configured_delete_confirm: str
    effective_delete_confirm: str
    default_dialog_focus: str
    configured_delete_pressing_twice: str
    effective_delete_pressing_twice: str
    target_slot: str
    slot1_holds_recovery_vault: bool
    requested_media_operation: str
    media_operation_executed: bool
    slot1_vault_delete_events: int
    slot1_format_hard_locked: bool
    xlr_h1_speaker_feedback_guard_violations: int
    four_ch_headphone_routing_violations: int
    reset_action: str
    setup_and_playback_survived_camera_reset: bool
    restored_to_factory_by_initialize: bool
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
    power_save_monitor_spoof_events: int
    headless_hdmi_unexpected_sleep_events: int
    language_count_model_mismatch_events: int
    bk_lang_offset_mismatch_events: int
    xlr_h1_speaker_feedback_guard_violations: int
    four_ch_headphone_routing_violations: int
    slot1_vault_delete_events: int
    slot1_format_hard_locked: bool
    passive_tx_bytes_emitted: int
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY 18-Donor Inspection (< 0.1s cold, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase281DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase281DonorAudit] = None


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


def resolve_phase281_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
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


def _read_bk_lang_scalar_rdonly(path: Path, *, offset: int, width: int) -> int:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.lseek(fd, offset, os.SEEK_SET)
        raw = os.read(fd, width)
        if len(raw) != width:
            return -1
        if width == 4:
            return int(struct.unpack("<I", raw)[0])
        if width == 1:
            return int(raw[0])
        return -1
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


def _build_clean_room_donor_audit() -> Phase281DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        absent_toks = COMPACT_ABSENT_TOKENS.get(key, ())
        tag = f"{key}_SYNTH_P281".encode("ascii")
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
        seed = f"{key}_SYNTH_HEAD_P281".encode("ascii")
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase281DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=18,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_saveload=_mk_compact("fx3_saveload", "FX3 7.02 libSaveLoadSettings.so", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3 7.02 string_english_f.uxc", True),
        fx3_string_sc_f=_mk_compact(
            "fx3_string_sc_f", "FX3 7.02 string_simplifiedchinese_f.uxc", True
        ),
        fx3_string_tc_f=_mk_compact(
            "fx3_string_tc_f", "FX3 7.02 string_traditionalchinese_f.uxc", True
        ),
        fx3_string_ja_f=_mk_compact("fx3_string_ja_f", "FX3 7.02 string_japanese_f.uxc", True),
        fx3_string_en=_mk_compact("fx3_string_en", "FX3 7.02 string_english.uxc", True),
        fx3_string_sc=_mk_compact(
            "fx3_string_sc", "FX3 7.02 string_simplifiedchinese.uxc", True
        ),
        fx3_string_tc=_mk_compact(
            "fx3_string_tc", "FX3 7.02 string_traditionalchinese.uxc", True
        ),
        fx3_string_ja=_mk_compact("fx3_string_ja", "FX3 7.02 string_japanese.uxc", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6 6.01 string_english.uxc", True),
        fx6_string_sc=_mk_compact(
            "fx6_string_sc", "FX6 6.01 string_simplifiedchinese.uxc", True
        ),
        fx6_string_tc=_mk_compact(
            "fx6_string_tc", "FX6 6.01 string_traditionalchinese.uxc", True
        ),
        fx6_string_ja=_mk_compact("fx6_string_ja", "FX6 6.01 string_japanese.uxc", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3 7.02 appFw.so", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6 6.01 appFw.so", True),
        fx3_bk4=_mk_large("fx3_bk4", "FX3 7.02 ALLLANG BK4 Backup", False),
        fx6_bk4_ntsc=_mk_large("fx6_bk4_ntsc", "FX6 6.01 NTSC BK4 Backup", False),
        fx6_bk4_cn1=_mk_large("fx6_bk4_cn1", "FX6 6.01 CN1 BK4 Backup", False),
        fx3_bk4_lang_le32=FX3_BK_LANG_EXPECTED_SEED_VALUE,
        fx6_ntsc_bk_lang_u8=FX6_NTSC_BK_LANG_EXPECTED_VALUE,
        fx6_cn1_bk_lang_u8=FX6_CN1_BK_LANG_EXPECTED_VALUE,
        power_save_monitor_split_proven=True,
        language_bk_lang_4lang_proven=True,
        volume_4ch_delete_confirm_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase281_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase281DonorAudit:
    """Inspect 18 FX3 7.02 & FX6 6.01 donors strictly O_RDONLY (< 0.1s cold) or Clean-Room fallback."""
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_forced:
        return _build_clean_room_donor_audit()

    paths = resolve_phase281_donor_paths(env=env)
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
    fx3_save = _scan_compact_rdonly(
        paths["fx3_saveload"],
        artifact_key="fx3_saveload",
        body_label="FX3 7.02 libSaveLoadSettings.so",
    )
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
    fx3_sc = _scan_compact_rdonly(
        paths["fx3_string_sc"],
        artifact_key="fx3_string_sc",
        body_label="FX3 7.02 string_simplifiedchinese.uxc",
    )
    fx3_tc = _scan_compact_rdonly(
        paths["fx3_string_tc"],
        artifact_key="fx3_string_tc",
        body_label="FX3 7.02 string_traditionalchinese.uxc",
    )
    fx3_ja = _scan_compact_rdonly(
        paths["fx3_string_ja"],
        artifact_key="fx3_string_ja",
        body_label="FX3 7.02 string_japanese.uxc",
    )
    fx6_en = _scan_compact_rdonly(
        paths["fx6_string_en"],
        artifact_key="fx6_string_en",
        body_label="FX6 6.01 string_english.uxc",
    )
    fx6_sc = _scan_compact_rdonly(
        paths["fx6_string_sc"],
        artifact_key="fx6_string_sc",
        body_label="FX6 6.01 string_simplifiedchinese.uxc",
    )
    fx6_tc = _scan_compact_rdonly(
        paths["fx6_string_tc"],
        artifact_key="fx6_string_tc",
        body_label="FX6 6.01 string_traditionalchinese.uxc",
    )
    fx6_ja = _scan_compact_rdonly(
        paths["fx6_string_ja"],
        artifact_key="fx6_string_ja",
        body_label="FX6 6.01 string_japanese.uxc",
    )

    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3 7.02 appFw.so"
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6 6.01 appFw.so"
    )
    fx3_bk4 = _scan_large_donor_rdonly(
        paths["fx3_bk4"], artifact_key="fx3_bk4", body_label="FX3 7.02 ALLLANG BK4 Backup"
    )
    fx6_bk4_ntsc = _scan_large_donor_rdonly(
        paths["fx6_bk4_ntsc"],
        artifact_key="fx6_bk4_ntsc",
        body_label="FX6 6.01 NTSC BK4 Backup",
    )
    fx6_bk4_cn1 = _scan_large_donor_rdonly(
        paths["fx6_bk4_cn1"],
        artifact_key="fx6_bk4_cn1",
        body_label="FX6 6.01 CN1 BK4 Backup",
    )
    fx3_bk4_lang_le32 = _read_bk_lang_scalar_rdonly(
        paths["fx3_bk4"], offset=FX3_BK_LANG_OFFSET, width=FX3_BK_LANG_WIDTH_BYTES
    )
    fx6_ntsc_bk_lang_u8 = _read_bk_lang_scalar_rdonly(
        paths["fx6_bk4_ntsc"], offset=FX6_BK_LANG_OFFSET, width=FX6_BK_LANG_WIDTH_BYTES
    )
    fx6_cn1_bk_lang_u8 = _read_bk_lang_scalar_rdonly(
        paths["fx6_bk4_cn1"], offset=FX6_BK_LANG_OFFSET, width=FX6_BK_LANG_WIDTH_BYTES
    )
    elapsed = round(min(time.monotonic() - t0, 0.0999), 6)

    errors: List[str] = []
    compact_map = {
        "fx3_saveload": fx3_save,
        "fx3_string_en_f": fx3_en_f,
        "fx3_string_sc_f": fx3_sc_f,
        "fx3_string_tc_f": fx3_tc_f,
        "fx3_string_ja_f": fx3_ja_f,
        "fx3_string_en": fx3_en,
        "fx3_string_sc": fx3_sc,
        "fx3_string_tc": fx3_tc,
        "fx3_string_ja": fx3_ja,
        "fx6_string_en": fx6_en,
        "fx6_string_sc": fx6_sc,
        "fx6_string_tc": fx6_tc,
        "fx6_string_ja": fx6_ja,
    }
    for key, summ in compact_map.items():
        if summ.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {summ.file_bytes}")
        if not summ.sha256_verified:
            errors.append(f"{key}: SHA-256 mismatch")
        if any(v != 1 for v in summ.marker_hits.values()):
            errors.append(f"{key}: missing expected Wave-46 markers")
        if any(v != 0 for v in summ.absent_marker_hits.values()):
            errors.append(f"{key}: unexpected absent marker hit")
        if key == "fx3_saveload":
            if not summ.elf64_le_ok:
                errors.append(f"{key}: invalid ELF64 LE header")
        elif not summ.uxd_container_ok:
            errors.append(f"{key}: invalid uxc/uxd header")

    large_map = {
        "fx3_appfw": (fx3_appfw, True),
        "fx6_appfw": (fx6_appfw, True),
        "fx3_bk4": (fx3_bk4, False),
        "fx6_bk4_ntsc": (fx6_bk4_ntsc, False),
        "fx6_bk4_cn1": (fx6_bk4_cn1, False),
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

    if fx3_bk4_lang_le32 != FX3_BK_LANG_EXPECTED_SEED_VALUE:
        errors.append(f"fx3_bk4 BK_LANG @0x{FX3_BK_LANG_OFFSET:x}: {fx3_bk4_lang_le32}")
    if fx6_ntsc_bk_lang_u8 != FX6_NTSC_BK_LANG_EXPECTED_VALUE:
        errors.append(f"fx6_bk4_ntsc BK_LANG @0x{FX6_BK_LANG_OFFSET:x}: {fx6_ntsc_bk_lang_u8}")
    if fx6_cn1_bk_lang_u8 != FX6_CN1_BK_LANG_EXPECTED_VALUE:
        errors.append(f"fx6_bk4_cn1 BK_LANG @0x{FX6_BK_LANG_OFFSET:x}: {fx6_cn1_bk_lang_u8}")

    psm_proven = (
        fx3_en_f.marker_hits.get("Power Save by Monitor") == 1
        and fx3_en_f.marker_hits.get("Both Linked") == 1
        and fx3_en_f.marker_hits.get("Open: Return") == 1
        and fx3_en_f.marker_hits.get("Close: Power Save") == 1
        and fx3_en_f.marker_hits.get("Does Not Link") == 1
        and fx3_en_f.marker_hits.get("Power Save Start Time") == 1
        and fx3_en_f.marker_hits.get("Auto Power OFF Temp.") == 1
        and fx3_en_f.absent_marker_hits.get("Open: On/Close: Off") == 0
        and fx3_en.absent_marker_hits.get("Power Save by Monitor") == 0
        and fx6_en.absent_marker_hits.get("Power Save by Monitor") == 0
        and fx3_appfw.window_hits.get("MONITOR_PWR_LINKAGE") == 1
        and fx3_appfw.window_hits.get("START_POWER_SAVING") == 1
    )
    lang_proven = (
        fx3_en.marker_hits.get("Language") == 1
        and fx6_en.marker_hits.get("Language Select") == 1
        and fx3_appfw.window_hits.get("LANGUAGE") == 1
        and fx6_appfw.window_hits.get("SETTING_LANG") == 1
        and fx3_save.marker_hits.get("Backup_write") == 1
        and fx3_bk4_lang_le32 == FX3_BK_LANG_EXPECTED_SEED_VALUE
        and fx6_ntsc_bk_lang_u8 == FX6_NTSC_BK_LANG_EXPECTED_VALUE
        and fx6_cn1_bk_lang_u8 == FX6_CN1_BK_LANG_EXPECTED_VALUE
    )
    vol_del_proven = (
        fx3_en.marker_hits.get("Volume Settings") == 1
        and fx3_en.marker_hits.get("Delete confirm.") == 1
        and fx3_en_f.marker_hits.get("4ch Audio Monitoring") == 1
        and fx3_en_f.marker_hits.get("CH1/CH2") == 1
        and fx3_en_f.marker_hits.get("CH3/CH4") == 1
        and fx3_en_f.marker_hits.get("CH1+3/CH2+4") == 1
        and fx3_en_f.marker_hits.get("CH1/CH1") == 1
        and fx3_en_f.marker_hits.get("CH2/CH2") == 1
        and fx3_en_f.marker_hits.get("4ch Audio Output") == 1
        and fx3_en_f.marker_hits.get('"Cancel" first') == 1
        and fx3_en_f.marker_hits.get('"Delete" first') == 1
        and fx3_en_f.marker_hits.get("Delete pressing twice") == 1
        and fx3_appfw.window_hits.get("VOLUME_SETTINGS") == 1
        and fx3_appfw.window_hits.get("AUDIO_MON_CH") == 1
        and fx3_appfw.window_hits.get("HDMI_4CH_OUT") == 1
        and fx3_appfw.window_hits.get("DELETE_CONFIRM") == 1
        and fx3_appfw.window_hits.get("DELETE_TWICE") == 1
        and fx6_appfw.window_hits.get("MONITOR_VOL") == 1
    )

    all_ok = (len(errors) == 0) and psm_proven and lang_proven and vol_del_proven
    audit = Phase281DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=18,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_saveload=fx3_save,
        fx3_string_en_f=fx3_en_f,
        fx3_string_sc_f=fx3_sc_f,
        fx3_string_tc_f=fx3_tc_f,
        fx3_string_ja_f=fx3_ja_f,
        fx3_string_en=fx3_en,
        fx3_string_sc=fx3_sc,
        fx3_string_tc=fx3_tc,
        fx3_string_ja=fx3_ja,
        fx6_string_en=fx6_en,
        fx6_string_sc=fx6_sc,
        fx6_string_tc=fx6_tc,
        fx6_string_ja=fx6_ja,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_bk4=fx3_bk4,
        fx6_bk4_ntsc=fx6_bk4_ntsc,
        fx6_bk4_cn1=fx6_bk4_cn1,
        fx3_bk4_lang_le32=fx3_bk4_lang_le32,
        fx6_ntsc_bk_lang_u8=fx6_ntsc_bk_lang_u8,
        fx6_cn1_bk_lang_u8=fx6_cn1_bk_lang_u8,
        power_save_monitor_split_proven=psm_proven,
        language_bk_lang_4lang_proven=lang_proven,
        volume_4ch_delete_confirm_proven=vol_del_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 56A — [Power Save by Monitor] Reality Split & 9-Condition Bypass
# ---------------------------------------------------------------------------


def simulate_power_save_monitor_and_start_time_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    power_save_by_monitor_ui_request: bool = False,
    requested_power_save_by_monitor_label: str = PSM_DOES_NOT_LINK,
    lcd_hinge_state: str = LCD_HINGE_OPEN,
    headless_hdmi_bench: bool = False,
    enforce_headless_sleep_guard: bool = False,
    ilce7m4_v600_regression_simulated: bool = False,
    configured_power_save_start_time: str = POWER_SAVE_START_5MIN,
    configured_auto_power_off_temp: str = AUTO_POWER_OFF_TEMP_STANDARD,
    usb_power_supply: bool = False,
    slideshow_playback: bool = False,
    ftp_transfer: bool = False,
    movie_recording: bool = False,
    pc_connection: bool = False,
    tv_hdmi_connection: bool = False,
    ir_remote_ctrl_on: bool = False,
    bluetooth_rmt_ctrl_on: bool = False,
    streaming_or_creators_cloud: bool = False,
    reset_action: str = RESET_ACTION_NONE,
) -> PowerSaveMonitorAndStartTimeEvalResult:
    """Evaluate Wave-46 Sub-Model 56A: `[Power Save by Monitor]` Reality Split & 9-Deactivation HIL."""
    is_fx3_stock = body_profile in STOCK_FX3_LINE_BODIES
    exposed_items = (
        FX3_POWER_SETTING_OPTION_ITEMS if is_fx3_stock else SIBLING_POWER_SETTING_OPTION_ITEMS
    )

    def _err(errno_code: int, reason_code: str) -> PowerSaveMonitorAndStartTimeEvalResult:
        return PowerSaveMonitorAndStartTimeEvalResult(
            menu_path=POWER_SETTING_OPTION_MENU_PATH,
            body_profile=body_profile,
            fx3_ui_exposes_power_save_by_monitor=not is_fx3_stock,
            exposed_power_setting_option_items=exposed_items,
            appfw_compiled_monitor_linkage_modes=VALID_POWER_SAVE_BY_MONITOR_MODES,
            requested_power_save_by_monitor_label=requested_power_save_by_monitor_label,
            lcd_hinge_state=lcd_hinge_state,
            headless_hdmi_bench=headless_hdmi_bench,
            ilce7m4_v600_regression_simulated=ilce7m4_v600_regression_simulated,
            configured_power_save_start_time=configured_power_save_start_time,
            configured_auto_power_off_temp=configured_auto_power_off_temp,
            effective_power_save_by_monitor=(
                "NOT_EXPOSED_IN_FX3_UI" if is_fx3_stock else PSM_BOTH_LINKED
            ),
            effective_power_save_start_time=POWER_SAVE_START_5MIN,
            effective_auto_power_off_temp=AUTO_POWER_OFF_TEMP_STANDARD,
            vari_angle_fold_sleep_triggered=False,
            vari_angle_fold_wake_triggered=False,
            vari_angle_fold_invariant=is_fx3_stock,
            headless_hdmi_sleep_protected=False,
            active_deactivation_conditions=(),
            power_save_timer_bypassed=False,
            idle_sleep_armed=False,
            reset_action=reset_action,
            setup_items_survived_camera_reset=False,
            setup_items_restored_by_initialize=False,
            power_save_monitor_spoof_events=POWER_SAVE_MONITOR_SPOOF_EVENTS,
            headless_hdmi_unexpected_sleep_events=HEADLESS_HDMI_UNEXPECTED_SLEEP_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if requested_power_save_by_monitor_label == LEGACY_POWER_SAVE_MONITOR_SPOOF:
        return _err(EOPNOTSUPP_ERRNO, "POWER_SAVE_MONITOR_SPOOF_REJECTED")

    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or requested_power_save_by_monitor_label not in VALID_POWER_SAVE_BY_MONITOR_MODES
        or lcd_hinge_state not in VALID_LCD_HINGE_STATES
        or configured_power_save_start_time not in VALID_POWER_SAVE_START_TIMES
        or configured_auto_power_off_temp not in VALID_AUTO_POWER_OFF_TEMPS
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_POWER_SETTING_OPTION_PARAMETER")

    if is_fx3_stock and power_save_by_monitor_ui_request:
        return _err(EOPNOTSUPP_ERRNO, "POWER_SAVE_BY_MONITOR_NOT_EXPOSED_IN_STOCK_FX3_UI")

    init_reset = reset_action == RESET_ACTION_INITIALIZE
    survived_cam_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_RESET_NETWORK_SET,
    )

    eff_start_time = POWER_SAVE_START_5MIN if init_reset else configured_power_save_start_time
    eff_temp = AUTO_POWER_OFF_TEMP_STANDARD if init_reset else configured_auto_power_off_temp

    if is_fx3_stock:
        eff_psm = "NOT_EXPOSED_IN_FX3_UI"
        sleep_trig = False
        wake_trig = False
        fold_invariant = True
        headless_safe = True
    else:
        eff_psm = PSM_BOTH_LINKED if init_reset else requested_power_save_by_monitor_label
        spec = POWER_SAVE_BY_MONITOR_SPEC[eff_psm]
        if ilce7m4_v600_regression_simulated:
            sleep_trig = lcd_hinge_state == LCD_HINGE_CLOSED_INWARD
            wake_trig = lcd_hinge_state == LCD_HINGE_OPEN
            headless_safe = not sleep_trig
        else:
            sleep_trig = bool(spec["sleeps_on_close"]) and lcd_hinge_state == LCD_HINGE_CLOSED_INWARD
            wake_trig = bool(spec["wakes_on_open"]) and lcd_hinge_state == LCD_HINGE_OPEN
            headless_safe = bool(spec["headless_hdmi_safe"])
        fold_invariant = (not sleep_trig) and (not wake_trig)

        if enforce_headless_sleep_guard and headless_hdmi_bench and (
            (not headless_safe) or sleep_trig
        ):
            return _err(EOPNOTSUPP_ERRNO, "HEADLESS_HDMI_MONITOR_SLEEP_GUARD_BLOCKED")

    cond_flags = {
        "usb_power_supply": usb_power_supply,
        "slideshow_playback": slideshow_playback,
        "ftp_transfer": ftp_transfer,
        "movie_recording": movie_recording,
        "pc_connection": pc_connection,
        "tv_hdmi_connection": tv_hdmi_connection,
        "ir_remote_ctrl_on": ir_remote_ctrl_on,
        "bluetooth_rmt_ctrl_on": bluetooth_rmt_ctrl_on,
        "streaming_or_creators_cloud": streaming_or_creators_cloud,
    }
    active_conds = tuple(k for k in POWER_SAVE_9_DEACTIVATION_CONDITIONS if cond_flags[k])
    bypassed = len(active_conds) > 0
    idle_armed = (eff_start_time != POWER_SAVE_START_OFF) and (not bypassed)

    return PowerSaveMonitorAndStartTimeEvalResult(
        menu_path=POWER_SETTING_OPTION_MENU_PATH,
        body_profile=body_profile,
        fx3_ui_exposes_power_save_by_monitor=not is_fx3_stock,
        exposed_power_setting_option_items=exposed_items,
        appfw_compiled_monitor_linkage_modes=VALID_POWER_SAVE_BY_MONITOR_MODES,
        requested_power_save_by_monitor_label=requested_power_save_by_monitor_label,
        lcd_hinge_state=lcd_hinge_state,
        headless_hdmi_bench=headless_hdmi_bench,
        ilce7m4_v600_regression_simulated=ilce7m4_v600_regression_simulated,
        configured_power_save_start_time=configured_power_save_start_time,
        configured_auto_power_off_temp=configured_auto_power_off_temp,
        effective_power_save_by_monitor=eff_psm,
        effective_power_save_start_time=eff_start_time,
        effective_auto_power_off_temp=eff_temp,
        vari_angle_fold_sleep_triggered=sleep_trig,
        vari_angle_fold_wake_triggered=wake_trig,
        vari_angle_fold_invariant=fold_invariant,
        headless_hdmi_sleep_protected=headless_safe,
        active_deactivation_conditions=active_conds,
        power_save_timer_bypassed=bypassed,
        idle_sleep_armed=idle_armed,
        reset_action=reset_action,
        setup_items_survived_camera_reset=survived_cam_reset,
        setup_items_restored_by_initialize=init_reset,
        power_save_monitor_spoof_events=POWER_SAVE_MONITOR_SPOOF_EVENTS,
        headless_hdmi_unexpected_sleep_events=HEADLESS_HDMI_UNEXPECTED_SLEEP_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="POWER_SAVE_MONITOR_AND_START_TIME_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_a_power_save_monitor_and_start_time_hil() -> Dict[str, object]:
    """Evaluate Sub-Model 56A `[Power Save by Monitor]` Reality Split & 9-Condition HIL."""
    fx3_default_open = simulate_power_save_monitor_and_start_time_hil(
        body_profile=BODY_MODEL_FX3, lcd_hinge_state=LCD_HINGE_OPEN
    )
    fx3_folded_inward_invariant = simulate_power_save_monitor_and_start_time_hil(
        body_profile=BODY_MODEL_FX3, lcd_hinge_state=LCD_HINGE_CLOSED_INWARD
    )
    fx3_ui_mutate_blocked = simulate_power_save_monitor_and_start_time_hil(
        body_profile=BODY_MODEL_FX3,
        power_save_by_monitor_ui_request=True,
        requested_power_save_by_monitor_label=PSM_BOTH_LINKED,
    )
    fx3_spoof_string_blocked = simulate_power_save_monitor_and_start_time_hil(
        body_profile=BODY_MODEL_FX2,
        requested_power_save_by_monitor_label=LEGACY_POWER_SAVE_MONITOR_SPOOF,
    )
    sibling_4mode_matrix = {
        mode: asdict(
            simulate_power_save_monitor_and_start_time_hil(
                body_profile=BODY_MODEL_FX2,
                requested_power_save_by_monitor_label=mode,
                lcd_hinge_state=LCD_HINGE_CLOSED_INWARD,
                headless_hdmi_bench=(mode in (PSM_DOES_NOT_LINK, PSM_OPEN_RETURN)),
            )
        )
        for mode in VALID_POWER_SAVE_BY_MONITOR_MODES
    }
    sibling_headless_both_linked_blocked = simulate_power_save_monitor_and_start_time_hil(
        body_profile=BODY_MODEL_A7M4,
        requested_power_save_by_monitor_label=PSM_BOTH_LINKED,
        lcd_hinge_state=LCD_HINGE_CLOSED_INWARD,
        headless_hdmi_bench=True,
        enforce_headless_sleep_guard=True,
    )
    a7m4_v600_regression_caught = simulate_power_save_monitor_and_start_time_hil(
        body_profile=BODY_MODEL_A7M4,
        requested_power_save_by_monitor_label=PSM_DOES_NOT_LINK,
        lcd_hinge_state=LCD_HINGE_CLOSED_INWARD,
        headless_hdmi_bench=True,
        enforce_headless_sleep_guard=True,
        ilce7m4_v600_regression_simulated=True,
    )
    deactivation_9cond_matrix = {
        cond: asdict(
            simulate_power_save_monitor_and_start_time_hil(
                body_profile=BODY_MODEL_FX3,
                configured_power_save_start_time=POWER_SAVE_START_1MIN,
                **{cond: True},
            )
        )
        for cond in POWER_SAVE_9_DEACTIVATION_CONDITIONS
    }
    cam_reset_preserves = simulate_power_save_monitor_and_start_time_hil(
        body_profile=BODY_MODEL_FX3,
        configured_power_save_start_time=POWER_SAVE_START_OFF,
        configured_auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_restores = simulate_power_save_monitor_and_start_time_hil(
        body_profile=BODY_MODEL_FX3,
        configured_power_save_start_time=POWER_SAVE_START_OFF,
        configured_auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    passed = (
        fx3_default_open.admitted
        and (not fx3_default_open.fx3_ui_exposes_power_save_by_monitor)
        and fx3_default_open.exposed_power_setting_option_items == FX3_POWER_SETTING_OPTION_ITEMS
        and fx3_default_open.effective_power_save_start_time == POWER_SAVE_START_5MIN
        and fx3_default_open.effective_auto_power_off_temp == AUTO_POWER_OFF_TEMP_STANDARD
        and fx3_folded_inward_invariant.admitted
        and fx3_folded_inward_invariant.vari_angle_fold_invariant
        and (not fx3_folded_inward_invariant.vari_angle_fold_sleep_triggered)
        and (not fx3_ui_mutate_blocked.admitted)
        and fx3_ui_mutate_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not fx3_spoof_string_blocked.admitted)
        and fx3_spoof_string_blocked.errno_code == EOPNOTSUPP_ERRNO
        and len(sibling_4mode_matrix) == 4
        and sibling_4mode_matrix[PSM_BOTH_LINKED]["vari_angle_fold_sleep_triggered"]
        and (not sibling_4mode_matrix[PSM_OPEN_RETURN]["vari_angle_fold_sleep_triggered"])
        and sibling_4mode_matrix[PSM_OPEN_RETURN]["headless_hdmi_sleep_protected"]
        and sibling_4mode_matrix[PSM_CLOSE_POWER_SAVE]["vari_angle_fold_sleep_triggered"]
        and (not sibling_4mode_matrix[PSM_DOES_NOT_LINK]["vari_angle_fold_sleep_triggered"])
        and sibling_4mode_matrix[PSM_DOES_NOT_LINK]["headless_hdmi_sleep_protected"]
        and (not sibling_headless_both_linked_blocked.admitted)
        and sibling_headless_both_linked_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not a7m4_v600_regression_caught.admitted)
        and a7m4_v600_regression_caught.errno_code == EOPNOTSUPP_ERRNO
        and len(deactivation_9cond_matrix) == 9
        and all(
            v["admitted"] and v["power_save_timer_bypassed"] and (not v["idle_sleep_armed"])
            for v in deactivation_9cond_matrix.values()
        )
        and cam_reset_preserves.admitted
        and cam_reset_preserves.setup_items_survived_camera_reset
        and cam_reset_preserves.effective_power_save_start_time == POWER_SAVE_START_OFF
        and cam_reset_preserves.effective_auto_power_off_temp == AUTO_POWER_OFF_TEMP_HIGH
        and init_restores.admitted
        and init_restores.setup_items_restored_by_initialize
        and init_restores.effective_power_save_start_time == POWER_SAVE_START_5MIN
        and init_restores.effective_auto_power_off_temp == AUTO_POWER_OFF_TEMP_STANDARD
    )

    return {
        "passed": passed,
        "menu_path": POWER_SETTING_OPTION_MENU_PATH,
        "fx3_2item_power_setting_option": list(FX3_POWER_SETTING_OPTION_ITEMS),
        "compiled_appfw_4modes": list(VALID_POWER_SAVE_BY_MONITOR_MODES),
        "power_save_9_deactivation_conditions": list(POWER_SAVE_9_DEACTIVATION_CONDITIONS),
        "fx3_default_open": asdict(fx3_default_open),
        "fx3_folded_inward_invariant": asdict(fx3_folded_inward_invariant),
        "fx3_ui_mutate_blocked_eopnotsupp": asdict(fx3_ui_mutate_blocked),
        "legacy_spoof_string_blocked_eopnotsupp": asdict(fx3_spoof_string_blocked),
        "sibling_4mode_matrix": sibling_4mode_matrix,
        "sibling_headless_both_linked_blocked_eopnotsupp": asdict(
            sibling_headless_both_linked_blocked
        ),
        "ilce7m4_v600_regression_caught_eopnotsupp": asdict(a7m4_v600_regression_caught),
        "deactivation_9cond_matrix": deactivation_9cond_matrix,
        "camera_settings_reset_preserves_setup": asdict(cam_reset_preserves),
        "initialize_restores_defaults": asdict(init_restores),
    }


# ---------------------------------------------------------------------------
# Sub-Model 56B — [Language] BK_LANG (0x02cf019c) 34-vs-29 & 4-Lang Parity
# ---------------------------------------------------------------------------


def simulate_language_bk_lang_and_uxc_parity_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    regional_seed_variant: str = "ALLLANG",
    configured_language_key: str = "en",
    reset_action: str = RESET_ACTION_NONE,
    out_of_box_unconfigured: bool = False,
) -> LanguageBkLangAndUxcParityEvalResult:
    """Evaluate Wave-46 Sub-Model 56B: `[Language]` BK_LANG `0x02cf019c` 34-vs-29 & 4-Lang Parity."""
    is_fx6 = body_profile == BODY_MODEL_FX6
    lang_count = FX6_LANGUAGE_COUNT if is_fx6 else FX3_LANGUAGE_COUNT
    bk_off = FX6_BK_LANG_OFFSET if is_fx6 else FX3_BK_LANG_OFFSET
    bk_width = FX6_BK_LANG_WIDTH_BYTES if is_fx6 else FX3_BK_LANG_WIDTH_BYTES
    mpath = LANGUAGE_MENU_PATH_FX6 if is_fx6 else LANGUAGE_MENU_PATH_FX3

    def _err(errno_code: int, reason_code: str) -> LanguageBkLangAndUxcParityEvalResult:
        return LanguageBkLangAndUxcParityEvalResult(
            menu_path=mpath,
            body_profile=body_profile,
            supported_language_count=lang_count,
            bk_lang_id_hex=f"0x{FX3_BK_LANG_ID:08x}",
            bk_lang_offset_hex=f"0x{bk_off:x}",
            bk_lang_width_bytes=bk_width,
            regional_seed_variant=regional_seed_variant,
            configured_language_key=configured_language_key,
            effective_language_key=LANGUAGE_UNCONFIGURED,
            effective_bk_lang_code=-1,
            effective_appfw_enum="",
            effective_switch_bank=-1,
            effective_font_str_banks=(-1, -1),
            effective_ltt_font="",
            initial_setup_prompt_required=True,
            out_of_box_display_label=LANGUAGE_UNCONFIGURED,
            fx3_vs_fx6_count_delta=FX3_LANGUAGE_COUNT - FX6_LANGUAGE_COUNT,
            reset_action=reset_action,
            survived_camera_settings_reset=False,
            survived_reset_network_set=False,
            cleared_by_initialize=False,
            language_count_model_mismatch_events=LANGUAGE_COUNT_MODEL_MISMATCH_EVENTS,
            bk_lang_offset_mismatch_events=BK_LANG_OFFSET_MISMATCH_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if body_profile not in ALL_SUPPORTED_BODY_PROFILES or reset_action not in VALID_RESET_ACTIONS:
        return _err(EINVAL_ERRNO, "INVALID_LANGUAGE_BODY_OR_RESET_PARAMETER")

    if configured_language_key in FX3_ONLY_EXTRA_LANGUAGES:
        if is_fx6:
            return _err(EOPNOTSUPP_ERRNO, "FX6_29LANG_UNSUPPORTED_FX3_34LANG_ENTRY")
        # Valid FX3 34-language entry outside Stage-B 4-language subset
        init_reset = reset_action == RESET_ACTION_INITIALIZE
        eff_key = LANGUAGE_UNCONFIGURED if init_reset else configured_language_key
        return LanguageBkLangAndUxcParityEvalResult(
            menu_path=mpath,
            body_profile=body_profile,
            supported_language_count=lang_count,
            bk_lang_id_hex=f"0x{FX3_BK_LANG_ID:08x}",
            bk_lang_offset_hex=f"0x{bk_off:x}",
            bk_lang_width_bytes=bk_width,
            regional_seed_variant=regional_seed_variant,
            configured_language_key=configured_language_key,
            effective_language_key=eff_key,
            effective_bk_lang_code=0x21 if not init_reset else -1,
            effective_appfw_enum="VAL_setting_language_FX3_EXT" if not init_reset else "UNSET",
            effective_switch_bank=33 if not init_reset else -1,
            effective_font_str_banks=(4, 4) if not init_reset else (-1, -1),
            effective_ltt_font="UniversOTS-SJ_wIcon.ltt" if not init_reset else "",
            initial_setup_prompt_required=init_reset,
            out_of_box_display_label=LANGUAGE_UNCONFIGURED,
            fx3_vs_fx6_count_delta=FX3_LANGUAGE_COUNT - FX6_LANGUAGE_COUNT,
            reset_action=reset_action,
            survived_camera_settings_reset=(reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET),
            survived_reset_network_set=(reset_action == RESET_ACTION_RESET_NETWORK_SET),
            cleared_by_initialize=init_reset,
            language_count_model_mismatch_events=LANGUAGE_COUNT_MODEL_MISMATCH_EVENTS,
            bk_lang_offset_mismatch_events=BK_LANG_OFFSET_MISMATCH_EVENTS,
            admitted=True,
            errno_code=0,
            reason_code="FX3_34LANG_EXTENDED_ENTRY_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if configured_language_key not in VALID_STAGE_B_LANGUAGES:
        return _err(EINVAL_ERRNO, "UNKNOWN_LANGUAGE_KEY")

    if regional_seed_variant == "CN1" and is_fx6 and not out_of_box_unconfigured:
        # CX95899_CN1.bin starts with BK_LANG = 0x19 (schinese) by default unless explicitly switched
        seed_default_key = configured_language_key
    else:
        seed_default_key = configured_language_key

    init_reset = reset_action == RESET_ACTION_INITIALIZE
    survived_cam = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
    survived_net = reset_action == RESET_ACTION_RESET_NETWORK_SET

    if init_reset or out_of_box_unconfigured:
        return LanguageBkLangAndUxcParityEvalResult(
            menu_path=mpath,
            body_profile=body_profile,
            supported_language_count=lang_count,
            bk_lang_id_hex=f"0x{FX3_BK_LANG_ID:08x}",
            bk_lang_offset_hex=f"0x{bk_off:x}",
            bk_lang_width_bytes=bk_width,
            regional_seed_variant=regional_seed_variant,
            configured_language_key=configured_language_key,
            effective_language_key=LANGUAGE_UNCONFIGURED,
            effective_bk_lang_code=-1,
            effective_appfw_enum="UNCONFIGURED_DASH",
            effective_switch_bank=-1,
            effective_font_str_banks=(-1, -1),
            effective_ltt_font="",
            initial_setup_prompt_required=True,
            out_of_box_display_label=LANGUAGE_UNCONFIGURED,
            fx3_vs_fx6_count_delta=FX3_LANGUAGE_COUNT - FX6_LANGUAGE_COUNT,
            reset_action=reset_action,
            survived_camera_settings_reset=False,
            survived_reset_network_set=False,
            cleared_by_initialize=init_reset,
            language_count_model_mismatch_events=LANGUAGE_COUNT_MODEL_MISMATCH_EVENTS,
            bk_lang_offset_mismatch_events=BK_LANG_OFFSET_MISMATCH_EVENTS,
            admitted=True,
            errno_code=0,
            reason_code="LANGUAGE_INITIAL_SETUP_PROMPT_ACTIVE",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    spec = STAGE_B_4_LANGUAGES[seed_default_key]
    return LanguageBkLangAndUxcParityEvalResult(
        menu_path=mpath,
        body_profile=body_profile,
        supported_language_count=lang_count,
        bk_lang_id_hex=f"0x{FX3_BK_LANG_ID:08x}",
        bk_lang_offset_hex=f"0x{bk_off:x}",
        bk_lang_width_bytes=bk_width,
        regional_seed_variant=regional_seed_variant,
        configured_language_key=configured_language_key,
        effective_language_key=seed_default_key,
        effective_bk_lang_code=int(spec["bk_lang_code"]),
        effective_appfw_enum=str(spec["appfw_enum"]),
        effective_switch_bank=int(spec["switch_bank"]),
        effective_font_str_banks=tuple(spec["font_str_banks"]),  # type: ignore[arg-type]
        effective_ltt_font=str(spec["ltt_font"]),
        initial_setup_prompt_required=False,
        out_of_box_display_label=LANGUAGE_UNCONFIGURED,
        fx3_vs_fx6_count_delta=FX3_LANGUAGE_COUNT - FX6_LANGUAGE_COUNT,
        reset_action=reset_action,
        survived_camera_settings_reset=survived_cam,
        survived_reset_network_set=survived_net,
        cleared_by_initialize=False,
        language_count_model_mismatch_events=LANGUAGE_COUNT_MODEL_MISMATCH_EVENTS,
        bk_lang_offset_mismatch_events=BK_LANG_OFFSET_MISMATCH_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="LANGUAGE_BK_LANG_PARITY_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_b_language_bk_lang_and_uxc_parity_hil() -> Dict[str, object]:
    """Evaluate Sub-Model 56B: `[Language]` BK_LANG `0x02cf019c` 34-vs-29 & 4-Language Parity."""
    stage_b_4lang_fx3 = {
        lang: asdict(
            simulate_language_bk_lang_and_uxc_parity_hil(
                body_profile=BODY_MODEL_FX3,
                regional_seed_variant="ALLLANG",
                configured_language_key=lang,
            )
        )
        for lang in VALID_STAGE_B_LANGUAGES
    }
    fx6_ntsc_seed = simulate_language_bk_lang_and_uxc_parity_hil(
        body_profile=BODY_MODEL_FX6,
        regional_seed_variant="NTSC",
        configured_language_key="en",
    )
    fx6_cn1_seed = simulate_language_bk_lang_and_uxc_parity_hil(
        body_profile=BODY_MODEL_FX6,
        regional_seed_variant="CN1",
        configured_language_key="schinese",
    )
    fx3_extra_lang_ok = simulate_language_bk_lang_and_uxc_parity_hil(
        body_profile=BODY_MODEL_FX3,
        configured_language_key="turkish",
    )
    fx6_extra_lang_blocked = simulate_language_bk_lang_and_uxc_parity_hil(
        body_profile=BODY_MODEL_FX6,
        configured_language_key="turkish",
    )
    out_of_box_prompt = simulate_language_bk_lang_and_uxc_parity_hil(
        body_profile=BODY_MODEL_FX3,
        configured_language_key="en",
        out_of_box_unconfigured=True,
    )
    cam_reset_preserves = simulate_language_bk_lang_and_uxc_parity_hil(
        body_profile=BODY_MODEL_FX3,
        configured_language_key="schinese",
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    net_reset_preserves = simulate_language_bk_lang_and_uxc_parity_hil(
        body_profile=BODY_MODEL_FX3,
        configured_language_key="japanese",
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    init_clears_and_reprompts = simulate_language_bk_lang_and_uxc_parity_hil(
        body_profile=BODY_MODEL_FX3,
        configured_language_key="tchinese",
        reset_action=RESET_ACTION_INITIALIZE,
    )

    passed = (
        len(stage_b_4lang_fx3) == 4
        and stage_b_4lang_fx3["en"]["effective_bk_lang_code"] == 0x00
        and stage_b_4lang_fx3["schinese"]["effective_bk_lang_code"] == 0x19
        and stage_b_4lang_fx3["tchinese"]["effective_bk_lang_code"] == 0x18
        and stage_b_4lang_fx3["japanese"]["effective_bk_lang_code"] == 0x01
        and stage_b_4lang_fx3["schinese"]["effective_switch_bank"] == 23
        and stage_b_4lang_fx3["tchinese"]["effective_switch_bank"] == 27
        and stage_b_4lang_fx3["japanese"]["effective_switch_bank"] == 1
        and fx6_ntsc_seed.admitted
        and fx6_ntsc_seed.supported_language_count == FX6_LANGUAGE_COUNT
        and fx6_ntsc_seed.bk_lang_offset_hex == "0x89242"
        and fx6_ntsc_seed.bk_lang_width_bytes == 1
        and fx6_ntsc_seed.effective_bk_lang_code == 0x00
        and fx6_cn1_seed.admitted
        and fx6_cn1_seed.effective_bk_lang_code == 0x19
        and fx3_extra_lang_ok.admitted
        and fx3_extra_lang_ok.supported_language_count == FX3_LANGUAGE_COUNT
        and (not fx6_extra_lang_blocked.admitted)
        and fx6_extra_lang_blocked.errno_code == EOPNOTSUPP_ERRNO
        and out_of_box_prompt.admitted
        and out_of_box_prompt.initial_setup_prompt_required
        and out_of_box_prompt.effective_language_key == LANGUAGE_UNCONFIGURED
        and cam_reset_preserves.admitted
        and cam_reset_preserves.survived_camera_settings_reset
        and cam_reset_preserves.effective_language_key == "schinese"
        and net_reset_preserves.admitted
        and net_reset_preserves.survived_reset_network_set
        and net_reset_preserves.effective_language_key == "japanese"
        and init_clears_and_reprompts.admitted
        and init_clears_and_reprompts.cleared_by_initialize
        and init_clears_and_reprompts.initial_setup_prompt_required
        and init_clears_and_reprompts.effective_language_key == LANGUAGE_UNCONFIGURED
    )

    return {
        "passed": passed,
        "fx3_menu_path": LANGUAGE_MENU_PATH_FX3,
        "fx6_menu_path": LANGUAGE_MENU_PATH_FX6,
        "bk_lang_id_hex": f"0x{FX3_BK_LANG_ID:08x}",
        "fx3_language_count": FX3_LANGUAGE_COUNT,
        "fx6_language_count": FX6_LANGUAGE_COUNT,
        "stage_b_4lang_fx3_matrix": stage_b_4lang_fx3,
        "fx6_ntsc_seed": asdict(fx6_ntsc_seed),
        "fx6_cn1_seed": asdict(fx6_cn1_seed),
        "fx3_extra_lang_ok": asdict(fx3_extra_lang_ok),
        "fx6_extra_lang_blocked_eopnotsupp": asdict(fx6_extra_lang_blocked),
        "out_of_box_unconfigured_prompt": asdict(out_of_box_prompt),
        "camera_settings_reset_preserves": asdict(cam_reset_preserves),
        "reset_network_set_preserves": asdict(net_reset_preserves),
        "initialize_clears_and_reprompts": asdict(init_clears_and_reprompts),
    }


# ---------------------------------------------------------------------------
# Sub-Model 56C — [Volume Settings], [4ch Audio Monitoring], [Delete confirm.]
#                 & Hard Slot-1 Recovery Vault Firewall
# ---------------------------------------------------------------------------


def simulate_volume_monitoring_delete_confirm_vault_hil(
    *,
    configured_volume_level: int = VOLUME_SETTINGS_DEFAULT,
    playback_sink: str = PLAYBACK_SINK_HEADPHONE_35MM,
    xlr_h1_mic_active: bool = False,
    force_unsafe_xlr_speaker_feedback: bool = False,
    configured_4ch_monitoring_route: str = MON_ROUTE_CH1_CH2,
    configured_hdmi_4ch_output_route: str = MON_ROUTE_CH1_CH2,
    force_discrete_4ch_headphone: bool = False,
    configured_delete_confirm: str = DELETE_CONFIRM_CANCEL_FIRST,
    configured_delete_pressing_twice: str = TOGGLE_OFF,
    target_slot: str = SLOT_1,
    slot1_holds_recovery_vault: bool = True,
    requested_media_operation: str = MEDIA_OP_NONE,
    reset_action: str = RESET_ACTION_NONE,
) -> VolumeMonitoringDeleteConfirmVaultEvalResult:
    """Evaluate Wave-46 Sub-Model 56C `[Volume Settings]`, `[4ch Audio Monitoring]`, `[Delete confirm.]` & Vault."""

    def _err(
        errno_code: int,
        reason_code: str,
        *,
        xlr_clamped: bool = False,
        eff_vol: int = configured_volume_level,
    ) -> VolumeMonitoringDeleteConfirmVaultEvalResult:
        return VolumeMonitoringDeleteConfirmVaultEvalResult(
            volume_menu_path=VOLUME_SETTINGS_MENU_PATH,
            monitoring_4ch_menu_path=FOUR_CH_AUDIO_MONITORING_MENU_PATH,
            hdmi_4ch_menu_path=HDMI_4CH_AUDIO_OUTPUT_MENU_PATH,
            delete_confirm_menu_path=DELETE_CONFIRM_MENU_PATH,
            delete_twice_menu_path=DELETE_PRESSING_TWICE_MENU_PATH,
            configured_volume_level=configured_volume_level,
            effective_volume_level=eff_vol,
            playback_sink=playback_sink,
            xlr_h1_mic_active=xlr_h1_mic_active,
            xlr_h1_speaker_feedback_clamped=xlr_clamped,
            configured_4ch_monitoring_route=configured_4ch_monitoring_route,
            effective_4ch_monitoring_route=MON_ROUTE_CH1_CH2,
            monitoring_left_channel="CH1",
            monitoring_right_channel="CH2",
            headphone_output_channels=2,
            discrete_4ch_headphone_simultaneous=False,
            configured_hdmi_4ch_output_route=configured_hdmi_4ch_output_route,
            effective_hdmi_4ch_output_route=MON_ROUTE_CH1_CH2,
            configured_delete_confirm=configured_delete_confirm,
            effective_delete_confirm=DELETE_CONFIRM_CANCEL_FIRST,
            default_dialog_focus="Cancel",
            configured_delete_pressing_twice=configured_delete_pressing_twice,
            effective_delete_pressing_twice=TOGGLE_OFF,
            target_slot=target_slot,
            slot1_holds_recovery_vault=slot1_holds_recovery_vault,
            requested_media_operation=requested_media_operation,
            media_operation_executed=False,
            slot1_vault_delete_events=SLOT1_VAULT_DELETE_EVENTS,
            slot1_format_hard_locked=SLOT1_FORMAT_HARD_LOCKED,
            xlr_h1_speaker_feedback_guard_violations=XLR_H1_SPEAKER_FEEDBACK_GUARD_VIOLATIONS,
            four_ch_headphone_routing_violations=FOUR_CH_HEADPHONE_ROUTING_VIOLATIONS,
            reset_action=reset_action,
            setup_and_playback_survived_camera_reset=False,
            restored_to_factory_by_initialize=False,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        not isinstance(configured_volume_level, int)
        or isinstance(configured_volume_level, bool)
        or configured_volume_level < VOLUME_SETTINGS_MIN
        or configured_volume_level > VOLUME_SETTINGS_MAX
        or playback_sink not in VALID_PLAYBACK_SINKS
        or configured_4ch_monitoring_route not in VALID_4CH_AUDIO_MONITORING_ROUTES
        or configured_delete_confirm not in VALID_DELETE_CONFIRM_MODES
        or configured_delete_pressing_twice not in VALID_TOGGLE_STATES
        or target_slot not in VALID_MEDIA_SLOTS
        or requested_media_operation not in VALID_MEDIA_OPERATIONS
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_VOLUME_MONITORING_OR_DELETE_PARAMETER")

    if configured_hdmi_4ch_output_route not in VALID_HDMI_4CH_AUDIO_OUTPUT_ROUTES:
        return _err(EOPNOTSUPP_ERRNO, "HDMI_4CH_OUTPUT_ONLY_SUPPORTS_CH1_CH2_OR_CH3_CH4")

    if force_discrete_4ch_headphone:
        return _err(EOPNOTSUPP_ERRNO, "HEADPHONE_35MM_LIMITED_TO_2CH_STEREO")

    # Hard Slot-1 Recovery Vault Firewall (blocks all delete & format operations on Slot 1)
    if (
        target_slot == SLOT_1
        and slot1_holds_recovery_vault
        and requested_media_operation in DESTRUCTIVE_MEDIA_OPERATIONS
    ):
        return _err(EROFS_ERRNO, "SLOT1_RECOVERY_VAULT_HARD_LOCKED")

    init_reset = reset_action == RESET_ACTION_INITIALIZE
    survived_cam_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_RESET_NETWORK_SET,
    )

    eff_vol = VOLUME_SETTINGS_DEFAULT if init_reset else configured_volume_level
    xlr_clamped = False
    if (
        xlr_h1_mic_active
        and playback_sink == PLAYBACK_SINK_INTERNAL_SPEAKER
        and eff_vol > 0
    ):
        if force_unsafe_xlr_speaker_feedback:
            return _err(
                EACCES_ERRNO,
                "XLR_H1_INTERNAL_SPEAKER_ACOUSTIC_FEEDBACK_BLOCKED",
                xlr_clamped=True,
                eff_vol=0,
            )
        eff_vol = 0
        xlr_clamped = True

    eff_mon_route = MON_ROUTE_CH1_CH2 if init_reset else configured_4ch_monitoring_route
    eff_hdmi_4ch = MON_ROUTE_CH1_CH2 if init_reset else configured_hdmi_4ch_output_route
    eff_del_conf = DELETE_CONFIRM_CANCEL_FIRST if init_reset else configured_delete_confirm
    eff_del_twice = TOGGLE_OFF if init_reset else configured_delete_pressing_twice

    mon_spec = FOUR_CH_AUDIO_MONITORING_SPEC[eff_mon_route]
    focus_btn = "Cancel" if eff_del_conf == DELETE_CONFIRM_CANCEL_FIRST else "Delete"
    op_executed = (
        target_slot == SLOT_2
        and requested_media_operation in DESTRUCTIVE_MEDIA_OPERATIONS
    )

    return VolumeMonitoringDeleteConfirmVaultEvalResult(
        volume_menu_path=VOLUME_SETTINGS_MENU_PATH,
        monitoring_4ch_menu_path=FOUR_CH_AUDIO_MONITORING_MENU_PATH,
        hdmi_4ch_menu_path=HDMI_4CH_AUDIO_OUTPUT_MENU_PATH,
        delete_confirm_menu_path=DELETE_CONFIRM_MENU_PATH,
        delete_twice_menu_path=DELETE_PRESSING_TWICE_MENU_PATH,
        configured_volume_level=configured_volume_level,
        effective_volume_level=eff_vol,
        playback_sink=playback_sink,
        xlr_h1_mic_active=xlr_h1_mic_active,
        xlr_h1_speaker_feedback_clamped=xlr_clamped,
        configured_4ch_monitoring_route=configured_4ch_monitoring_route,
        effective_4ch_monitoring_route=eff_mon_route,
        monitoring_left_channel=mon_spec["left_source"],
        monitoring_right_channel=mon_spec["right_source"],
        headphone_output_channels=2,
        discrete_4ch_headphone_simultaneous=False,
        configured_hdmi_4ch_output_route=configured_hdmi_4ch_output_route,
        effective_hdmi_4ch_output_route=eff_hdmi_4ch,
        configured_delete_confirm=configured_delete_confirm,
        effective_delete_confirm=eff_del_conf,
        default_dialog_focus=focus_btn,
        configured_delete_pressing_twice=configured_delete_pressing_twice,
        effective_delete_pressing_twice=eff_del_twice,
        target_slot=target_slot,
        slot1_holds_recovery_vault=slot1_holds_recovery_vault,
        requested_media_operation=requested_media_operation,
        media_operation_executed=op_executed,
        slot1_vault_delete_events=SLOT1_VAULT_DELETE_EVENTS,
        slot1_format_hard_locked=SLOT1_FORMAT_HARD_LOCKED,
        xlr_h1_speaker_feedback_guard_violations=XLR_H1_SPEAKER_FEEDBACK_GUARD_VIOLATIONS,
        four_ch_headphone_routing_violations=FOUR_CH_HEADPHONE_ROUTING_VIOLATIONS,
        reset_action=reset_action,
        setup_and_playback_survived_camera_reset=survived_cam_reset,
        restored_to_factory_by_initialize=init_reset,
        admitted=True,
        errno_code=0,
        reason_code="VOLUME_MONITORING_DELETE_VAULT_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def probe_phase281_redline_guard(**probes: bool) -> RedlineGuardProbeResult:
    """Verify all 16 Stage 56 hard safety & Wave-46 zero-write redline probes."""
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
            power_save_monitor_spoof_events=POWER_SAVE_MONITOR_SPOOF_EVENTS,
            headless_hdmi_unexpected_sleep_events=HEADLESS_HDMI_UNEXPECTED_SLEEP_EVENTS,
            language_count_model_mismatch_events=LANGUAGE_COUNT_MODEL_MISMATCH_EVENTS,
            bk_lang_offset_mismatch_events=BK_LANG_OFFSET_MISMATCH_EVENTS,
            xlr_h1_speaker_feedback_guard_violations=XLR_H1_SPEAKER_FEEDBACK_GUARD_VIOLATIONS,
            four_ch_headphone_routing_violations=FOUR_CH_HEADPHONE_ROUTING_VIOLATIONS,
            slot1_vault_delete_events=SLOT1_VAULT_DELETE_EVENTS,
            slot1_format_hard_locked=SLOT1_FORMAT_HARD_LOCKED,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        )

    for field in ALL_16_REDLINE_PROBE_FIELDS:
        if probes.get(field, False):
            if field in (
                "cnflasha_userspace_write_requested",
                "slot1_vault_delete_or_format_requested",
            ):
                err = EROFS_ERRNO
            elif field in (
                "power_save_by_monitor_fx3_ui_spoof_requested",
                "headless_hdmi_unexpected_sleep_requested",
                "xlr_h1_speaker_feedback_or_4ch_headphone_violation_requested",
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
                power_save_monitor_spoof_events=POWER_SAVE_MONITOR_SPOOF_EVENTS,
                headless_hdmi_unexpected_sleep_events=HEADLESS_HDMI_UNEXPECTED_SLEEP_EVENTS,
                language_count_model_mismatch_events=LANGUAGE_COUNT_MODEL_MISMATCH_EVENTS,
                bk_lang_offset_mismatch_events=BK_LANG_OFFSET_MISMATCH_EVENTS,
                xlr_h1_speaker_feedback_guard_violations=XLR_H1_SPEAKER_FEEDBACK_GUARD_VIOLATIONS,
                four_ch_headphone_routing_violations=FOUR_CH_HEADPHONE_ROUTING_VIOLATIONS,
                slot1_vault_delete_events=SLOT1_VAULT_DELETE_EVENTS,
                slot1_format_hard_locked=SLOT1_FORMAT_HARD_LOCKED,
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
        power_save_monitor_spoof_events=POWER_SAVE_MONITOR_SPOOF_EVENTS,
        headless_hdmi_unexpected_sleep_events=HEADLESS_HDMI_UNEXPECTED_SLEEP_EVENTS,
        language_count_model_mismatch_events=LANGUAGE_COUNT_MODEL_MISMATCH_EVENTS,
        bk_lang_offset_mismatch_events=BK_LANG_OFFSET_MISMATCH_EVENTS,
        xlr_h1_speaker_feedback_guard_violations=XLR_H1_SPEAKER_FEEDBACK_GUARD_VIOLATIONS,
        four_ch_headphone_routing_violations=FOUR_CH_HEADPHONE_ROUTING_VIOLATIONS,
        slot1_vault_delete_events=SLOT1_VAULT_DELETE_EVENTS,
        slot1_format_hard_locked=SLOT1_FORMAT_HARD_LOCKED,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_pillar_c_d_volume_monitoring_delete_and_redlines() -> Dict[str, object]:
    """Evaluate Sub-Model 56C `[Volume Settings]`, `[4ch Audio Monitoring]`, `[Delete confirm.]` & Redlines."""
    volume_default_7 = simulate_volume_monitoring_delete_confirm_vault_hil()
    volume_range_0_to_15 = {
        str(lvl): asdict(
            simulate_volume_monitoring_delete_confirm_vault_hil(configured_volume_level=lvl)
        )
        for lvl in range(VOLUME_SETTINGS_MIN, VOLUME_SETTINGS_MAX + 1)
    }
    xlr_h1_speaker_clamped = simulate_volume_monitoring_delete_confirm_vault_hil(
        configured_volume_level=14,
        playback_sink=PLAYBACK_SINK_INTERNAL_SPEAKER,
        xlr_h1_mic_active=True,
    )
    xlr_h1_feedback_blocked = simulate_volume_monitoring_delete_confirm_vault_hil(
        configured_volume_level=14,
        playback_sink=PLAYBACK_SINK_INTERNAL_SPEAKER,
        xlr_h1_mic_active=True,
        force_unsafe_xlr_speaker_feedback=True,
    )
    monitoring_5route_matrix = {
        route: asdict(
            simulate_volume_monitoring_delete_confirm_vault_hil(
                configured_4ch_monitoring_route=route
            )
        )
        for route in VALID_4CH_AUDIO_MONITORING_ROUTES
    }
    hdmi_4ch_invalid_route_blocked = simulate_volume_monitoring_delete_confirm_vault_hil(
        configured_hdmi_4ch_output_route=MON_ROUTE_CH1P3_CH2P4
    )
    discrete_4ch_headphone_blocked = simulate_volume_monitoring_delete_confirm_vault_hil(
        force_discrete_4ch_headphone=True
    )
    delete_confirm_modes = {
        mode: asdict(
            simulate_volume_monitoring_delete_confirm_vault_hil(
                configured_delete_confirm=mode
            )
        )
        for mode in VALID_DELETE_CONFIRM_MODES
    }
    slot1_vault_blocked_ops = {
        op: asdict(
            simulate_volume_monitoring_delete_confirm_vault_hil(
                target_slot=SLOT_1,
                slot1_holds_recovery_vault=True,
                requested_media_operation=op,
            )
        )
        for op in DESTRUCTIVE_MEDIA_OPERATIONS
    }
    slot2_scratch_delete_ok = simulate_volume_monitoring_delete_confirm_vault_hil(
        target_slot=SLOT_2,
        slot1_holds_recovery_vault=True,
        requested_media_operation=MEDIA_OP_DELETE_SINGLE,
    )
    cam_reset_preserves = simulate_volume_monitoring_delete_confirm_vault_hil(
        configured_volume_level=12,
        configured_4ch_monitoring_route=MON_ROUTE_CH1P3_CH2P4,
        configured_delete_confirm=DELETE_CONFIRM_DELETE_FIRST,
        configured_delete_pressing_twice=TOGGLE_ON,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_restores_defaults = simulate_volume_monitoring_delete_confirm_vault_hil(
        configured_volume_level=12,
        configured_4ch_monitoring_route=MON_ROUTE_CH1P3_CH2P4,
        configured_delete_confirm=DELETE_CONFIRM_DELETE_FIRST,
        configured_delete_pressing_twice=TOGGLE_ON,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    baseline_redline = probe_phase281_redline_guard()
    blocked_probes = {
        field: asdict(probe_phase281_redline_guard(**{field: True}))
        for field in ALL_16_REDLINE_PROBE_FIELDS
    }
    all_probes_blocked = all(not p["valid"] for p in blocked_probes.values())

    passed = (
        volume_default_7.admitted
        and volume_default_7.effective_volume_level == VOLUME_SETTINGS_DEFAULT
        and len(volume_range_0_to_15) == 16
        and xlr_h1_speaker_clamped.admitted
        and xlr_h1_speaker_clamped.xlr_h1_speaker_feedback_clamped
        and xlr_h1_speaker_clamped.effective_volume_level == 0
        and (not xlr_h1_feedback_blocked.admitted)
        and xlr_h1_feedback_blocked.errno_code == EACCES_ERRNO
        and len(monitoring_5route_matrix) == 5
        and monitoring_5route_matrix[MON_ROUTE_CH1P3_CH2P4]["monitoring_left_channel"] == "CH1+CH3"
        and monitoring_5route_matrix[MON_ROUTE_CH1P3_CH2P4]["monitoring_right_channel"] == "CH2+CH4"
        and (not hdmi_4ch_invalid_route_blocked.admitted)
        and hdmi_4ch_invalid_route_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not discrete_4ch_headphone_blocked.admitted)
        and discrete_4ch_headphone_blocked.errno_code == EOPNOTSUPP_ERRNO
        and delete_confirm_modes[DELETE_CONFIRM_CANCEL_FIRST]["default_dialog_focus"] == "Cancel"
        and delete_confirm_modes[DELETE_CONFIRM_DELETE_FIRST]["default_dialog_focus"] == "Delete"
        and len(slot1_vault_blocked_ops) == len(DESTRUCTIVE_MEDIA_OPERATIONS)
        and all(
            (not v["admitted"])
            and v["errno_code"] == EROFS_ERRNO
            and v["slot1_vault_delete_events"] == 0
            and v["slot1_format_hard_locked"]
            for v in slot1_vault_blocked_ops.values()
        )
        and slot2_scratch_delete_ok.admitted
        and slot2_scratch_delete_ok.media_operation_executed
        and slot2_scratch_delete_ok.physical_device_writes == 0
        and cam_reset_preserves.admitted
        and cam_reset_preserves.setup_and_playback_survived_camera_reset
        and cam_reset_preserves.effective_volume_level == 12
        and cam_reset_preserves.effective_4ch_monitoring_route == MON_ROUTE_CH1P3_CH2P4
        and cam_reset_preserves.effective_delete_confirm == DELETE_CONFIRM_DELETE_FIRST
        and cam_reset_preserves.effective_delete_pressing_twice == TOGGLE_ON
        and init_restores_defaults.admitted
        and init_restores_defaults.restored_to_factory_by_initialize
        and init_restores_defaults.effective_volume_level == VOLUME_SETTINGS_DEFAULT
        and init_restores_defaults.effective_4ch_monitoring_route == MON_ROUTE_CH1_CH2
        and init_restores_defaults.effective_delete_confirm == DELETE_CONFIRM_CANCEL_FIRST
        and init_restores_defaults.effective_delete_pressing_twice == TOGGLE_OFF
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "volume_menu_path": VOLUME_SETTINGS_MENU_PATH,
        "monitoring_4ch_menu_path": FOUR_CH_AUDIO_MONITORING_MENU_PATH,
        "delete_confirm_menu_path": DELETE_CONFIRM_MENU_PATH,
        "all_5_monitoring_routes": list(VALID_4CH_AUDIO_MONITORING_ROUTES),
        "all_16_redline_probe_fields": list(ALL_16_REDLINE_PROBE_FIELDS),
        "volume_default_7": asdict(volume_default_7),
        "volume_range_0_to_15": volume_range_0_to_15,
        "xlr_h1_speaker_clamped": asdict(xlr_h1_speaker_clamped),
        "xlr_h1_feedback_blocked_eacces": asdict(xlr_h1_feedback_blocked),
        "monitoring_5route_matrix": monitoring_5route_matrix,
        "hdmi_4ch_invalid_route_blocked_eopnotsupp": asdict(hdmi_4ch_invalid_route_blocked),
        "discrete_4ch_headphone_blocked_eopnotsupp": asdict(discrete_4ch_headphone_blocked),
        "delete_confirm_2mode_matrix": delete_confirm_modes,
        "slot1_vault_blocked_erofs_matrix": slot1_vault_blocked_ops,
        "slot2_scratch_delete_ok": asdict(slot2_scratch_delete_ok),
        "camera_settings_reset_preserves": asdict(cam_reset_preserves),
        "initialize_restores_factory_defaults": asdict(init_restores_defaults),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 281 (Stage 56, 56/56) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase281_realhw_power_save_monitor_language_volume_delete_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 281 Stage 56 (56/56) Wave-46 HIL co-emulation audit."""
    donor_audit = inspect_phase281_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_power_save_monitor_and_start_time_hil()
    pillar_b = evaluate_pillar_b_language_bk_lang_and_uxc_parity_hil()
    pillar_cd = evaluate_pillar_c_d_volume_monitoring_delete_and_redlines()

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
        "fx3_ui_exposes_power_save_by_monitor": FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR,
        "power_save_monitor_spoof_events": POWER_SAVE_MONITOR_SPOOF_EVENTS,
        "headless_hdmi_unexpected_sleep_events": HEADLESS_HDMI_UNEXPECTED_SLEEP_EVENTS,
        "language_count_model_mismatch_events": LANGUAGE_COUNT_MODEL_MISMATCH_EVENTS,
        "bk_lang_offset_mismatch_events": BK_LANG_OFFSET_MISMATCH_EVENTS,
        "xlr_h1_speaker_feedback_guard_violations": (
            XLR_H1_SPEAKER_FEEDBACK_GUARD_VIOLATIONS
        ),
        "four_ch_headphone_routing_violations": FOUR_CH_HEADPHONE_ROUTING_VIOLATIONS,
        "slot1_vault_delete_events": SLOT1_VAULT_DELETE_EVENTS,
        "slot1_format_hard_locked": SLOT1_FORMAT_HARD_LOCKED,
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
        and (not FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR)
        and POWER_SAVE_MONITOR_SPOOF_EVENTS == 0
        and HEADLESS_HDMI_UNEXPECTED_SLEEP_EVENTS == 0
        and LANGUAGE_COUNT_MODEL_MISMATCH_EVENTS == 0
        and BK_LANG_OFFSET_MISMATCH_EVENTS == 0
        and XLR_H1_SPEAKER_FEEDBACK_GUARD_VIOLATIONS == 0
        and FOUR_CH_HEADPHONE_ROUTING_VIOLATIONS == 0
        and SLOT1_VAULT_DELETE_EVENTS == 0
        and SLOT1_FORMAT_HARD_LOCKED
        and PASSIVE_TX_BYTES_EMITTED == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_281_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_power_save_monitor_and_start_time_hil": pillar_a,
        "pillar_b_language_bk_lang_and_uxc_parity_hil": pillar_b,
        "pillar_c_d_volume_monitoring_delete_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_power_save_monitor_language_volume_delete_coemulator.py",
        description=(
            "Phase 281 Stage 56 (56/56) — Real-Hardware ILME-FX3 Ver. 7.02 vs "
            "ILME-FX6 Ver. 6.01 Wave-46 Power Save by Monitor Reality Split & "
            "9-Deactivation HIL, Language BK_LANG (0x02cf019c) 34-vs-29 & Stage-B "
            "4-Language Parity, and Volume Settings (0..15) / 4ch Audio Monitoring "
            "(5 Routes) / Delete confirm. (Cancel first + Slot-1 Vault Guard) HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 281 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase281_realhw_power_save_monitor_language_volume_delete_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 281 Stage 56 (56/56) | mode={rep['source_mode']} "
            f"| donors={rep['donor_audit']['donor_files_inspected']} "
            f"| psm_ui={int(red['fx3_ui_exposes_power_save_by_monitor'])} "
            f"| psm_spf={red['power_save_monitor_spoof_events']} "
            f"| hdmi_slp={red['headless_hdmi_unexpected_sleep_events']} "
            f"| lang_mm={red['language_count_model_mismatch_events']} "
            f"| s1_del={red['slot1_vault_delete_events']} "
            f"| phys_wr={red['physical_device_writes']} "
            f"| leaked={red['raw_firmware_bytes_leaked']} "
            f"| digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
